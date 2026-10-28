"""H5: alarm scoring. DwellRule vs PathLoiterRule, default vs i-LIDS-compatible
scoring, pooled over the distinct batch_v6 worlds (day/night renders of one
simulation share one world, so each world is scored once)."""
from __future__ import annotations

import hashlib
import itertools
from pathlib import Path
from typing import Any

from .common import rpath


def _alarms(rule: dict[str, Any], run_dir: Path):
    from ..eval.rules import run_baseline, run_path_loiter_baseline
    if rule["kind"] == "dwell":
        return run_baseline(run_dir, threshold_s=rule["threshold_s"])
    return run_path_loiter_baseline(run_dir, threshold_s=rule["threshold_s"],
                                    radius_m=rule["radius_m"], reentry_gap_s=rule["reentry_gap_s"])


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from ..eval import alarms as A

    batch = rpath(cfg["batch_dir"])
    worlds, seen = [], {}
    for r in cfg["runs"]:
        h = hashlib.md5((batch / r / "gt" / "world.parquet").read_bytes()).hexdigest()
        if h in seen:
            continue
        seen[h] = r
        worlds.append(r)
    per_world = {}
    for r in worlds:
        rd = batch / r
        truth = [A.TruthEvent(e.t_start, e.t_end, "suspicious.loiter", e.actors)
                 for e in A.load_truth(rd) if e.label.startswith("suspicious.loiter")]
        per_world[r] = {"truth": truth, "hours": A.camera_hours_of(rd),
                        "alarms": {x["name"]: _alarms(x, rd) for x in cfg["rules"]}}
    rows = []
    for rule, mode, tol in itertools.product(cfg["rules"], cfg["scoring"], cfg["tolerances_s"]):
        tp = fn = fp = rep = 0
        hours, lat, per = 0.0, [], {}
        for r, w in per_world.items():
            s = A.score(w["truth"], w["alarms"][rule["name"]], camera_hours=w["hours"], tolerance_s=tol,
                        ilids_compat=(mode == "ilids_compat"))
            tp += s.true_positives; fn += s.false_negatives; fp += s.false_positives
            rep += s.repeat_alarms; hours += w["hours"]; lat += s.latencies_s
            per[r] = {"tp": s.true_positives, "fn": s.false_negatives, "fp": s.false_positives,
                      "alarms": len(w["alarms"][rule["name"]])}
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        fa_h = fp / hours if hours else float("inf")
        rows.append({"rule": rule["name"], "scoring": mode, "tolerance_s": tol,
                     "alarms": sum(len(w["alarms"][rule["name"]]) for w in per_world.values()),
                     "truth_events": tp + fn, "tp": tp, "fn": fn, "fp": fp, "repeats": rep,
                     "precision": round(p, 4), "recall": round(rc, 4),
                     "f1": round(2 * p * rc / (p + rc), 4) if p + rc else 0.0,
                     "camera_hours": round(hours, 4), "false_alarms_per_camera_hour": round(fa_h, 2),
                     "over_operator_budget_x": round(fa_h / A.DEFAULT_BUDGET_FA_PER_CAMERA_HOUR, 0),
                     "mean_latency_s": round(sum(lat) / len(lat), 1) if lat else None,
                     "per_world": per})
    return {"worlds": worlds, "rule_configs": cfg["rules"], "rows": rows,
            "budget_fa_per_camera_hour": A.DEFAULT_BUDGET_FA_PER_CAMERA_HOUR}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    lines = [f"worlds: {', '.join(res['worlds'])}", "",
             "| rule | scoring | tol s | alarms | truth | TP | FP | FN | precision | recall | FA/cam-h | x budget |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        lines.append(f"| {r['rule']} | {r['scoring']} | {r['tolerance_s']} | {r['alarms']} | "
                     f"{r['truth_events']} | {r['tp']} | {r['fp']} | {r['fn']} | {r['precision']:.3f} | "
                     f"{r['recall']:.3f} | {r['false_alarms_per_camera_hour']} | {r['over_operator_budget_x']:.0f} |")
    return "\n".join(lines) + "\n"
