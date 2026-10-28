"""cctvsec command line: evaluation, experiments and baselines on top of survsim."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(add_completion=False, help="CCTV analytics, evaluation and experiments")
console = Console()


@app.command("eval")
def eval_alarms(
    run_dir: Path,
    threshold_s: float = typer.Option(60.0, help="dwell threshold for the baseline rule"),
    tolerance_s: float = typer.Option(10.0, help="i-LIDS detection window"),
    cameras_per_operator: int = typer.Option(500),
    actor_aware: bool | None = typer.Option(
        None,
        "--actor-aware/--window-only",
        help="Require alarms to name an event's actor (default: auto -- on if any "
        "alarm carries a uid). --window-only forces the old, actor-blind matching.",
    ),
) -> None:
    """Score the baseline dwell rule against truth, in operational terms."""
    from .eval import alarms as alarm_eval
    from .eval.rules import run_baseline

    truth = [e for e in alarm_eval.load_truth(run_dir) if e.label.startswith("suspicious.loiter")]
    # The baseline emits a generic loiter label; match truth at the same granularity.
    truth = [
        alarm_eval.TruthEvent(e.t_start, e.t_end, "suspicious.loiter", e.actors) for e in truth
    ]
    raised = run_baseline(run_dir, threshold_s=threshold_s)
    hours = alarm_eval.camera_hours_of(run_dir)
    result = alarm_eval.score(
        truth, raised, camera_hours=hours, tolerance_s=tolerance_s, actor_aware=actor_aware
    )

    t = Table("metric", "value")
    t.add_row("truth events", str(result.true_positives + result.false_negatives))
    t.add_row("alarms raised", str(len(raised)))
    t.add_row("detected (within tolerance)", str(result.true_positives))
    t.add_row("missed", str(result.false_negatives))
    t.add_row("false alarms", str(result.false_positives))
    t.add_row("bystander hits", str(result.bystander_hits))
    t.add_row("precision / recall / F1",
              f"{result.precision:.2f} / {result.recall:.2f} / {result.f1:.2f}")
    if result.window_only_recall is not None:
        t.add_row("recall (window-only)", f"{result.window_only_recall:.2f}")
    if result.latencies_s:
        t.add_row("mean latency", f"{result.mean_latency_s:.1f} s")
    console.print(t)

    if (
        result.window_only_recall is not None
        and abs(result.window_only_recall - result.recall) > 0.05
    ):
        total_truth = result.true_positives + result.false_negatives
        window_hits = round(result.window_only_recall * total_truth)
        actor_hits = result.true_positives
        diff = window_hits - actor_hits
        console.print(
            f"[yellow]note:[/] {diff} of {window_hits} window-only hits were on a "
            "different person than the event"
        )

    verdict = result.operator_verdict(cameras_per_operator)
    console.print(
        f"[bold]false alarms/camera-hour[/] {verdict['false_alarms_per_camera_hour']:.4f}  "
        f"(budget {verdict['budget_per_camera_hour']:.6f} at "
        f"{cameras_per_operator} cameras/operator)"
    )
    if verdict["within_budget"]:
        console.print("[green]within operator budget[/]")
    else:
        console.print(
            f"[red]over budget by {verdict['over_budget_factor']}x[/] — "
            f"{verdict['false_alarms_per_operator_hour']:.1f} alarms/hour reach one operator"
        )


@app.command("alarm-cards")
def alarm_cards(
    run_dir: Path,
    mode: str = typer.Option("sim", help="sim (may read gt/) or real (no GT-derived field)"),
    threshold_s: float = typer.Option(25.0, help="dwell threshold for the baseline rule"),
    tolerance_s: float = typer.Option(10.0, help="i-LIDS detection window (sim mode)"),
    alarms_file: Path | None = typer.Option(None, "--alarms", help="alarms JSONL (t,label,camera,uid,"
                                            "track_id[,score,theta,rank_in_queue,verdict,reason_code,t_verdict]"
                                            " -- e.g. H22's alarms_scored.jsonl); default: baseline rule"),
    out: Path | None = typer.Option(None, help="output dir (default <run_dir>/alarm_cards_<mode>)"),
    operator_id: str = typer.Option("operator-0"),
    salt_file: Path | None = typer.Option(None, help="per-site secret salt (32 random bytes); never commit"),
    init_salt: bool = typer.Option(False, "--init-salt", help="create --salt-file with 32 random bytes"),
    insecure_default_salt: bool = typer.Option(False, "--insecure-default-salt",
                                               help="allow the public default salt in mode=real"),
    config: Path | None = typer.Option(None, help="scenario YAML for config_hash "
                                       "(default: meta/scenario.resolved.json)"),
    model: Path | None = typer.Option(None, help="model checkpoint for model_hash"),
) -> None:
    """Alarm cards + hash-chained evidence log + anchored head for a run (H60, docs/research/86 §7)."""
    import json as _json
    import os
    import secrets

    from .eval import alarm_card as ac
    from .eval import alarms as alarm_eval
    from .eval import evidence_pack as ep
    from .eval.rules import run_baseline

    if init_salt:
        if salt_file is None:
            raise typer.BadParameter("--init-salt needs --salt-file")
        if salt_file.exists():
            raise typer.BadParameter(f"{salt_file} exists; refusing to overwrite a site salt")
        salt_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(salt_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(32))
        console.print(f"wrote 32-byte salt to {salt_file} (keep it out of git: *.salt is ignored)")
    if salt_file is not None:
        raw = salt_file.read_bytes()
        if len(raw) < 32:
            raise typer.BadParameter(f"{salt_file}: salt must be >= 32 bytes, got {len(raw)}")
        salt = raw.hex()
    elif mode == "real" and not insecure_default_salt:
        console.print("[red]mode=real refuses the public default salt[/] (a small operator roster is "
                      "reversible by enumeration): pass --salt-file (create with --init-salt) or "
                      "--insecure-default-salt")
        raise typer.Exit(2)
    else:
        salt = ep.DEFAULT_SALT

    track_ids: dict[int, str] = {}
    runner: dict[int, ac.RunnerFields] = {}
    rows: list[dict] = []
    if alarms_file is not None:
        rows = [_json.loads(x) for x in alarms_file.read_text().splitlines() if x.strip()]
        raised = [alarm_eval.Alarm(float(r["t"]), r["label"], r.get("camera"), r.get("uid"))
                  for r in rows]
        track_ids = {i: str(r["track_id"]) for i, r in enumerate(rows) if r.get("track_id")}
        runner = {i: ac.RunnerFields(r.get("score"), r.get("theta"), r.get("rank_in_queue"))
                  for i, r in enumerate(rows)
                  if any(r.get(k) is not None for k in ("score", "theta", "rank_in_queue"))}
    else:
        raised = sorted(run_baseline(run_dir, threshold_s=threshold_s), key=lambda a: a.t)
    truth, eids = None, None
    if mode == "sim":
        evs = [_json.loads(x) for x in (run_dir / "gt" / "events.jsonl").read_text().splitlines()
               if x.strip()]
        truth = [alarm_eval.TruthEvent(float(r["t_start"]), float(r["t_end"] if r["t_end"] is not None
                 else r["t_start"]), r["label"], tuple(r.get("actors", []))) for r in evs]
        eids = [r["event_id"] for r in evs]
    cards = ac.build_cards(run_dir, raised, mode=mode, runner=runner, track_ids=track_ids,
                           truth=truth, event_ids=eids, tolerance_s=tolerance_s,
                           config_path=config, model_path=model)
    out = out or run_dir / f"alarm_cards_{mode}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "cards.jsonl").write_text("".join(_json.dumps(c, sort_keys=True) + "\n" for c in cards))
    # Decisions: an alarms file's own verdicts (e.g. H22's simulated operator) win; else sim =
    # a GT-oracle operator (dispatch hits/late, dismiss the rest); real = every alarm escalated
    # for human review -- the generator never invents a verdict there.
    decisions = []
    for i, c in enumerate(cards):
        r = rows[i] if rows else {}
        if r.get("verdict") in ep.VERDICTS:
            decisions.append((r["verdict"], r.get("reason_code"), float(r.get("t_verdict", c["t"]))))
        elif mode == "sim" and c["gt_match"]["verdict"] in ("hit", "late"):
            decisions.append(("dispatch", None, c["t"] + 30.0))
        elif mode == "sim":
            decisions.append(("dismiss", "no_threat", c["t"] + 30.0))
        else:
            decisions.append(("escalate", None, c["t"]))
    entries = ep.chain(cards, decisions, operator_id, salt)
    head = ep.write_pack(out, entries)
    ok, _bad = ep.verify(out / "evidence_log.jsonl")
    cards_ok, _bad_card = ep.verify_cards(out / "evidence_log.jsonl", out / "cards.jsonl")
    ok = ok and cards_ok
    leaks = ac.leak_count(cards, ac.gt_values(run_dir)) if mode == "real" else None
    filled = {k: sum(1 for c in cards if c.get(k) is not None)
              for k in ("score", "theta", "rank_in_queue", "model_hash")}
    summary = {"mode": mode, "n_alarms": len(raised), "n_cards": len(cards), "chain_head": head["chain_head"],
               "n_records": head["n_records"], "chain_ok": ok, "leak_count": leaks,
               "salt": "file" if salt_file is not None else "public-default", "filled": filled,
               "clip_hash_emitted": sum(1 for c in cards if c["clip_hash"] != ac.CLIP_NOT_EMITTED)}
    (out / "summary.json").write_text(_json.dumps(summary, indent=2))
    console.print(summary)
    print(f"ANCHOR THIS HEAD out of band: {head['chain_head']} n_records={head['n_records']}")
    if leaks:
        raise typer.Exit(1)


@app.command("audit-motion")
def audit_motion(
    run_dir: Path,
    out: Path | None = typer.Option(None, help="JSON path (default <run_dir>/motion_audit.json)"),
    min_stuck_s: float = typer.Option(3.0),
) -> None:
    """Audit GT motion: stuck episodes and their causes, walking speeds, t=0 clustering."""
    import json

    from .eval.motion_audit import audit, table

    report = audit(run_dir, min_stuck_s=min_stuck_s)
    path = out or run_dir / "motion_audit.json"
    path.write_text(json.dumps(report, indent=2))
    console.print(table(report))
    worst = sorted(report["episodes"], key=lambda e: -e["dur_s"])[:10]
    if worst:
        t = Table("uid", "t_start", "dur_s", "label", "cause")
        for e in worst:
            t.add_row(e["uid"], str(e["t_start"]), str(e["dur_s"]), e["label"], e["cause"])
        console.print(t)
    console.print(f"written {path}")


@app.command()
def experiment(
    name: str = typer.Argument(..., help="config name in cctvsec/experiments/configs (or a YAML path)"),
    out: Path | None = typer.Option(None, help="default out/experiments/<name>"),
    arm: list[str] = typer.Option(None, help="detection runners: only these arms (repeatable)"),
) -> None:
    """Run a seeded, config-driven experiment; writes results.json + row.md."""
    from .experiments import run_experiment

    res = run_experiment(name, out, arms=arm or None)
    console.print(f"[green]experiment[/] {res['experiment']} done in "
                  f"{res['wall_seconds_this_invocation']} s")


@app.command()
def baseline(
    dataset_dir: Path,
    task: str = typer.Option("all", help="det|mot|reid|all"),
    model: str = typer.Option("yolo11n.pt"),
    imgsz: int = typer.Option(1280),
    out: Path | None = typer.Option(None),
    allow_noncommercial: bool = typer.Option(
        False, "--allow-noncommercial",
        help="compute numbers even when the dataset manifest's commercial_ml_ok is false "
             "(docs/research/47) — internal evidence only, never a reported product number"),
) -> None:
    """Detection (YOLO, COCO mAP), MOT (ByteTrack -> MOTA/IDF1/HOTA), ReID (rank-1/mAP)."""
    from .baselines.run import NonCommercialDatasetError, markdown, run_baselines

    if task not in ("det", "mot", "reid", "all"):
        raise typer.BadParameter("task must be det|mot|reid|all")
    try:
        res = run_baselines(dataset_dir, task, out, model, imgsz, allow_noncommercial)
    except NonCommercialDatasetError as e:
        console.print(f"[red]refused[/]: {e}")
        raise typer.Exit(1) from e
    console.print(markdown(res))


@app.command()
def demo(
    out: Path = typer.Option(Path("out/demo")),
    scenes: int = typer.Option(4),
    duration_s: float = typer.Option(120.0),
    seed: int = typer.Option(0),
    engine: str = typer.Option("mock"),
) -> None:
    """Run the whole pipeline end to end and report which stages hold up."""
    from .demo import run_demo

    result = run_demo(out, n_scenes=scenes, duration_s=duration_s, seed=seed, engine=engine)

    t = Table("stage", "result")
    for name, payload in result.stages.items():
        if isinstance(payload, dict):
            summary = ", ".join(f"{k}={v}" for k, v in list(payload.items())[:4])
        elif isinstance(payload, list):
            summary = "; ".join(str(x) for x in payload[:2])
        else:
            summary = str(payload)
        t.add_row(name, summary[:96])
    console.print(t)

    if result.failures:
        console.print("[red]failed stages[/]")
        for failure in result.failures:
            console.print(f"  {failure}")
    else:
        console.print("[green]every stage completed[/]")
    console.print(f"report written to {out / 'demo_report.json'}")


if __name__ == "__main__":
    app()
