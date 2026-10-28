"""H12: loiter-rule false alarms at scale on hard-negative-only mock worlds,
plus recall on worlds with generated loiterers.

Worlds come from the scene generator (site types, footprints, entrances,
camera placement); people are replaced by a staggered stream of *innocent*
arcs whose dwell looks like loitering to a rule (commute waits, queues, phone
stops, smoke breaks) plus ordinary transit. Only `World.step` runs - no
backend, no rendering - and the per-tick world rows the Recorder would write
(t, uid, x, y, speed, zone, label) are rebuilt in memory, so the rules see
exactly what `run_baseline` / `run_path_loiter_baseline` would read from
world.parquet.

Camera-hours follow `alarms.camera_hours_of`: n_cameras x duration. Alarms are
site-level (the rules run on world tracks), so a site-hour rate is reported
beside the camera-hour one.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .inference import bootstrap_ratio, garwood, rule_of_three

ARCHETYPES = ("transit", "commute_wait", "queue", "phone_stop", "smoke_break")


# ------------------------------------------------------------------ world recipe

def _site_spec(i: int, seed: int, cfg: dict[str, Any], incidents: list[str]):
    from survsim.generator.batch import SITE_TYPES
    from survsim.generator.spec import CameraPlan, IncidentPlan, PopulationPlan, SceneSpec, SiteSpec
    rng = np.random.default_rng([seed, i, 7])
    site = SITE_TYPES[i % len(SITE_TYPES)]
    extent = float(rng.uniform(50, 130))
    return SceneSpec(
        name=f"h12_{i:05d}_{site}", seed=seed * 100000 + i, duration_s=float(cfg["duration_s"]),
        fps=float(cfg["fps"]), engine="mock",
        site=SiteSpec(type=site, footprint_m=(extent, extent * 0.75), entrances=int(rng.integers(1, 6)),
                      restricted_zones=1 + i % 3, blind_spots=1 + i % 2),
        cameras=CameraPlan(count=int(rng.integers(4, 15)), target_coverage=0.55),
        population=PopulationPlan(count=int(rng.integers(12, 51)), evasion_techniques_per_actor=1 + i % 3),
        incidents=[IncidentPlan(type=m) for m in incidents])  # type: ignore[arg-type]


def _compose_valid(spec, max_repairs: int = 4):
    """compose + the same axis repair `generate_batch` uses."""
    from survsim.generator.compose import compose
    scene = compose(spec)
    for _ in range(max_repairs):
        if scene.valid:
            break
        if any("coverage" in x for x in scene.issues):
            spec.cameras.count = min(spec.cameras.count + 3, 40)
            spec.cameras.target_coverage = max(0.3, spec.cameras.target_coverage - 0.08)
        if any("blind" in x.lower() for x in scene.issues):
            spec.site.blind_spots = max(1, spec.site.blind_spots)
            spec.site.footprint_m = (spec.site.footprint_m[0] * 1.15, spec.site.footprint_m[1] * 1.15)
        scene = compose(spec)
    return scene


def _point_in(env, tags, rng, jitter):
    zs = [z for z in env.zones if z.tag in tags] or [z for z in env.zones if z.tag == "public"]
    z = zs[int(rng.integers(len(zs)))]
    xs, ys = zip(*z.polygon)
    return [float(np.clip(np.mean(xs) + rng.uniform(-jitter, jitter), min(xs), max(xs))),
            float(np.clip(np.mean(ys) + rng.uniform(-jitter, jitter), min(ys), max(ys)))]


def innocent_people(env, rng, n: int, mix: dict[str, float], dur: dict[str, list[float]]):
    """n innocent people: (Person, archetype). Hard negatives for loitering by design."""
    from survsim.core.models import BehaviourSpec as B
    from survsim.director.population import random_person
    ents = [w.id for w in env.spawn_points]
    exits = [w.id for w in env.exits]
    names = list(mix)
    p = np.array([mix[k] for k in names], float)
    p /= p.sum()
    out = []
    for j in range(n):
        kind = names[int(rng.choice(len(names), p=p))]
        per = random_person(f"n{j:04d}", rng, role="commuter")
        src, dst = str(rng.choice(ents)), str(rng.choice(exits))
        d = float(rng.uniform(*dur[kind])) if kind in dur else 0.0
        if kind == "transit":
            mid = _point_in(env, ("public",), rng, 15.0)
            steps = [B(type="transit", **{"from": src, "to": mid}), B(type="transit", to=dst)]
        elif kind == "commute_wait":
            pt = _point_in(env, ("queue", "gate"), rng, 3.0)
            steps = [B(type="transit", **{"from": src, "to": pt}),
                     B(type="commute_wait", zone=pt, dur_s=d, activity="idle"), B(type="transit", to=dst)]
        elif kind == "queue":
            pt = _point_in(env, ("queue", "gate"), rng, 2.0)
            steps = [B(type="transit", **{"from": src, "to": pt}),
                     B(type="queue", head=pt, dur_s=d), B(type="transit", to=dst)]
        elif kind == "phone_stop":
            pt = _point_in(env, ("public",), rng, 15.0)
            steps = [B(type="transit", **{"from": src, "to": pt}),
                     B(type="commute_wait", zone=pt, dur_s=d, activity="idle", note="phone_call"),
                     B(type="transit", to=dst)]
        else:  # smoke_break: pacing within 3 m, the loiterer's motion signature
            pt = _point_in(env, ("public", "gate"), rng, 10.0)
            steps = [B(type="transit", **{"from": src, "to": pt}),
                     B(type="smoke_break", zone=pt, dur_s=d, activity="pace", radius_m=3.0),
                     B(type="transit", to=dst)]
        per.intent = steps
        per.hard_negative_for = [] if kind == "transit" else ["loiter"]
        out.append((per, kind))
    return out


def _simulate(scenario, extra_people=None):
    """Run World.step only; return world rows as a DataFrame and the World."""
    import pandas as pd

    from survsim.director.world import World

    class _W(World):
        def _generated_people(self):
            return list(extra_people or [])

    w = _W(scenario)
    rows = []
    for _ in range(scenario.n_ticks):
        w.step()
        for a in w.agents.values():
            rows.append((w.t, a.uid, float(a.pos[0]), float(a.pos[1]),
                         float(np.hypot(a.vel[0], a.vel[1])), a.label))
    w.finalise()
    df = pd.DataFrame(rows, columns=["t", "uid", "x", "y", "speed", "label"])
    z = zones_of(w, df["x"].to_numpy(), df["y"].to_numpy())
    df["zone"] = pd.Series(list(z), index=df.index, dtype=object)
    return df, w


def zones_of(world, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Vectorised `World.zone_of`: the smallest containing zone (same order, same tie-break)."""
    import shapely
    out = np.full(len(xs), None, dtype=object)
    free = np.ones(len(xs), bool)
    for zid, poly in world._zone_order:
        hit = free & shapely.contains_xy(poly, xs, ys)
        out[hit] = zid
        free &= ~hit
    return out


def _p90(d: np.ndarray) -> float:
    """np.percentile(d, 90) (linear), via one sort - ~10x cheaper on short arrays."""
    s = np.sort(d)
    pos = 0.9 * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return float(s[lo] + (s[hi] - s[lo]) * (pos - lo))


def path_loiter_fast(rule, ts, xs, ys, zs, role, roles_by_zone) -> list[float]:
    """`PathLoiterRule.run` for one person, step for step, with a cheaper p90.

    tests/test_experiments.py checks it returns the same alarm times as the rule."""
    alarms: list[float] = []
    wt: list[float] = []
    wxy: list[tuple[float, float]] = []
    dwell_start = outside_since = None
    fired = False
    for t, x, y, zid in zip(ts, xs, ys, zs):
        roles = roles_by_zone.get(zid, []) if zid is not None else []
        if role is not None and role in roles:
            wt, wxy, dwell_start, outside_since, fired = [], [], None, None, False
            continue
        wt.append(t)
        wxy.append((x, y))
        while wt and t - wt[0] > rule.window_s:
            wt.pop(0)
            wxy.pop(0)
        if dwell_start is None:
            dwell_start = t
        pts = np.asarray(wxy)
        c = pts.mean(axis=0)
        spread = _p90(np.linalg.norm(pts - c, axis=1)) if len(pts) else 0.0
        if spread <= rule.radius_m:
            outside_since = None
        else:
            if outside_since is None:
                outside_since = t
            if t - outside_since > rule.reentry_gap_s:
                wt, wxy, dwell_start, outside_since, fired = [t], [(x, y)], t, None, False
                continue
        if t - dwell_start >= rule.threshold_s and not fired:
            alarms.append(float(t))
            fired = True
    return alarms


def _rule_alarms(rule, df, zones, roles):
    """Per-uid alarms (both rules are per-person, so this equals one pooled run)."""
    from ..eval.rules import DwellRule, PathLoiterRule
    tags = {z["id"]: z["tag"] for z in zones}
    out = []
    for uid, g in df.groupby("uid", sort=False):
        g = g.sort_values("t")
        if rule["kind"] == "dwell":
            ts = [a.t for a in DwellRule(threshold_s=rule["threshold_s"]).run(g, tags)]
        else:
            r = PathLoiterRule(threshold_s=rule["threshold_s"], radius_m=rule["radius_m"],
                               reentry_gap_s=rule["reentry_gap_s"])
            ts = path_loiter_fast(r, g["t"].to_numpy(float), g["x"].to_numpy(float),
                                  g["y"].to_numpy(float), g["zone"].to_numpy(object), roles.get(uid),
                                  {z["id"]: (z.get("allowed_roles") or []) for z in zones})
        for t in ts:
            lab = g.loc[(g["t"] - t).abs().idxmin(), "label"]
            out.append({"t": t, "uid": uid, "behaviour_label": lab})
    return out


def _world_job(args) -> dict[str, Any]:
    i, cfg, mode = args
    t0 = time.time()
    seed = int(cfg["seed"])
    rng = np.random.default_rng([seed, i, 11])
    if mode == "clean":
        spec = _site_spec(i, seed, cfg, [])
        scene = _compose_valid(spec)
        sc = scene.scenario
        sc.population.hero = []
        sc.population.warmup_s = float(cfg["warmup_s"])
        rate = float(rng.uniform(*cfg["arrivals_per_min"]))
        n = int(rng.poisson(rate * cfg["duration_s"] / 60.0))
        people = innocent_people(sc.environment, rng, n, cfg["mix"], cfg["dur_s"])
        kinds = {p.id: k for p, k in people}
        df, w = _simulate(sc, [p for p, _ in people])
    else:
        mix = cfg["recall"]["incidents"][i % len(cfg["recall"]["incidents"])]
        spec = _site_spec(i, seed + 1, {**cfg, "duration_s": cfg["recall"]["duration_s"]}, mix)
        scene = _compose_valid(spec)
        sc = scene.scenario
        kinds = {a.person.id: a.narrative for a in scene.arcs}
        df, w = _simulate(sc)
    env = sc.model_dump(mode="json")["environment"]
    zones = env["zones"]
    roles = {a.uid: a.spec.role for a in w.roster.values()}
    truth = [{"t_start": e.t_start, "t_end": e.t_end, "actors": list(e.actors)}
             for e in w.events if e.label.startswith("suspicious.loiter")]
    return {"i": i, "mode": mode, "name": sc.name, "valid": scene.valid, "cameras": len(sc.cameras), "duration_s": sc.duration_s,
            "camera_hours": len(sc.cameras) * sc.duration_s / 3600.0, "people": int(df["uid"].nunique()),
            "kinds": {k: sum(1 for v in kinds.values() if v == k) for k in set(kinds.values())},
            "truth": truth,
            "alarms": {r["name"]: [{**a, "kind": kinds.get(a["uid"], "?")}
                                   for a in _rule_alarms(r, df, zones, roles)] for r in cfg["rules"]},
            "seconds": round(time.time() - t0, 2)}


def _score(worlds, rule, mode, tol):
    from ..eval import alarms as A
    lab = "suspicious.loiter"
    out = []
    for w in worlds:
        truth = [A.TruthEvent(e["t_start"], e["t_end"] or e["t_start"], lab, tuple(e["actors"]))
                 for e in w["truth"]]
        al = [A.Alarm(t=a["t"], label=lab) for a in w["alarms"][rule]]
        s = A.score(truth, al, camera_hours=w["camera_hours"], tolerance_s=tol,
                    ilids_compat=(mode == "ilids_compat"))
        out.append((s.true_positives, s.false_negatives, s.false_positives, s.latencies_s))
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    workers = int(cfg.get("workers", 11))
    cache = out / "worlds.jsonl"
    done = {}
    if cache.is_file():
        for line in cache.read_text().splitlines():
            r = json.loads(line)
            done[(r["mode"], r["i"])] = r
    t0 = time.time()
    with get_context("fork").Pool(workers) as pool, cache.open("a") as fh:
        for mode, target in (("clean", cfg["target_camera_hours"]), ("recall", None)):
            n_max = cfg["max_worlds"] if mode == "clean" else cfg["recall"]["n_worlds"]
            have = sorted((r for (m, _), r in done.items() if m == mode), key=lambda r: r["i"])
            hours = sum(r["camera_hours"] for r in have)
            i = max((r["i"] for r in have), default=-1) + 1
            # Fixed stopping rule: worlds in index order until the camera-hour target.
            while i < n_max and (target is None or hours < target):
                chunk = list(range(i, min(i + workers * 4, n_max)))
                for r in pool.imap(_world_job, [(j, cfg, mode) for j in chunk]):
                    if target is not None and hours >= target:
                        break
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    done[(mode, r["i"])] = r
                    hours += r["camera_hours"]
                i = chunk[-1] + 1
    gen_s = round(time.time() - t0, 1)
    clean = sorted((r for (m, _), r in done.items() if m == "clean"), key=lambda r: r["i"])
    rec = sorted((r for (m, _), r in done.items() if m == "recall"), key=lambda r: r["i"])
    budget = float(cfg["budget_fa_per_camera_hour"])
    cam_h = sum(w["camera_hours"] for w in clean)
    site_h = sum(w["duration_s"] for w in clean) / 3600.0
    fa_rows = []
    for rule in cfg["rules"]:
        for mode in cfg["scoring"]:
            sc = _score(clean, rule["name"], mode, cfg["tolerance_s"])
            fp = [s[2] for s in sc]
            k = int(sum(fp))
            lo, hi = garwood(k, cam_h)
            blo, bhi = bootstrap_ratio(fp, [w["camera_hours"] for w in clean], seed=int(cfg["seed"]))
            causes: dict[str, int] = {}
            beh: dict[str, int] = {}
            for w in clean:
                for a in w["alarms"][rule["name"]]:
                    causes[a["kind"]] = causes.get(a["kind"], 0) + 1
                    beh[a["behaviour_label"]] = beh.get(a["behaviour_label"], 0) + 1
            rate = k / cam_h
            fa_rows.append({
                "rule": rule["name"], "scoring": mode, "false_alarms": k, "camera_hours": round(cam_h, 2),
                "fa_per_camera_hour": round(rate, 5), "garwood95": [round(lo, 5), round(hi, 5)],
                "cluster_bootstrap95": [round(blo, 5), round(bhi, 5)],
                "rule_of_three_upper": round(rule_of_three(cam_h), 6) if k == 0 else None,
                "fa_per_site_hour": round(k / site_h, 3), "x_budget": round(rate / budget, 1),
                "x_budget_lower95": round(lo / budget, 1),
                "worlds_with_fa": int(sum(1 for f in fp if f)),
                "raw_alarms_by_archetype": dict(sorted(causes.items(), key=lambda x: -x[1])),
                "raw_alarms_by_behaviour_label": dict(sorted(beh.items(), key=lambda x: -x[1]))})
    rec_rows = []
    rng = np.random.default_rng(int(cfg["seed"]))
    for rule in cfg["rules"]:
        for mode in cfg["scoring"]:
            for tol in cfg["recall"]["tolerances_s"]:
                sc = _score(rec, rule["name"], mode, tol)
                tp = np.array([s[0] for s in sc], float)
                ev = np.array([s[0] + s[1] for s in sc], float)
                fp = np.array([s[2] for s in sc], float)
                ch = np.array([w["camera_hours"] for w in rec])
                recall = tp.sum() / max(ev.sum(), 1)
                idx = rng.integers(0, len(sc), (2000, len(sc)))
                bs = tp[idx].sum(1) / np.maximum(ev[idx].sum(1), 1)
                pr = tp.sum() / max(tp.sum() + fp.sum(), 1)
                bp = tp[idx].sum(1) / np.maximum(tp[idx].sum(1) + fp[idx].sum(1), 1)
                lat = [x for s in sc for x in s[3]]
                rec_rows.append({"rule": rule["name"], "scoring": mode, "tolerance_s": tol,
                                 "truth_events": int(ev.sum()), "tp": int(tp.sum()), "fp": int(fp.sum()),
                                 "recall": round(float(recall), 4),
                                 "recall_boot95": [round(float(np.percentile(bs, 2.5)), 4),
                                                   round(float(np.percentile(bs, 97.5)), 4)],
                                 "precision": round(float(pr), 4),
                                 "precision_boot95": [round(float(np.percentile(bp, 2.5)), 4),
                                                      round(float(np.percentile(bp, 97.5)), 4)],
                                 "fa_per_camera_hour": round(float(fp.sum() / ch.sum()), 3),
                                 "median_latency_s": round(float(np.median(lat)), 1) if lat else None})
    kinds: dict[str, int] = {}
    for w in clean:
        for k, v in w["kinds"].items():
            kinds[k] = kinds.get(k, 0) + v
    return {"clean": {"worlds": len(clean), "camera_hours": round(cam_h, 2), "site_hours": round(site_h, 2),
                      "people": int(sum(w["people"] for w in clean)), "archetype_counts": kinds,
                      "truth_loiter_events": int(sum(len(w["truth"]) for w in clean)),
                      "invalid_worlds": int(sum(not w["valid"] for w in clean)),
                      "sites": sorted({w["name"].split("_", 2)[2] for w in clean}),
                      "cpu_seconds": round(sum(w["seconds"] for w in clean), 1)},
            "recall_worlds": {"worlds": len(rec), "camera_hours": round(sum(w["camera_hours"] for w in rec), 2),
                              "truth_loiter_events": int(sum(len(w["truth"]) for w in rec))},
            "generation_wall_s_this_invocation": gen_s, "fa": fa_rows, "recall": rec_rows,
            "budget_fa_per_camera_hour": budget}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    c = res["clean"]
    L = [(f"clean worlds: {c['worlds']}, {c['camera_hours']} camera-h, {c['site_hours']} site-h, "
          f"{c['people']} people, truth loiter events {c['truth_loiter_events']}, archetypes {c['archetype_counts']}"),
         "", ("| rule | scoring | FA | FA/cam-h | Garwood 95 % | world-bootstrap 95 % | FA/site-h | x budget "
              "(lower 95 %) | worlds with FA | top causes (raw alarms) |"), "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["fa"]:
        top = ", ".join(f"{k} {v}" for k, v in list(r["raw_alarms_by_archetype"].items())[:3])
        L.append(f"| {r['rule']} | {r['scoring']} | {r['false_alarms']} | {r['fa_per_camera_hour']} | "
                 f"{r['garwood95'][0]}-{r['garwood95'][1]} | {r['cluster_bootstrap95'][0]}-"
                 f"{r['cluster_bootstrap95'][1]} | {r['fa_per_site_hour']} | {r['x_budget']} "
                 f"({r['x_budget_lower95']}) | {r['worlds_with_fa']}/{c['worlds']} | {top} |")
    rw = res["recall_worlds"]
    L += ["", (f"recall worlds: {rw['worlds']}, {rw['camera_hours']} camera-h, {rw['truth_loiter_events']} "
               "truth loiter events"), "",
          ("| rule | scoring | tol s | truth | TP | FP | recall [95 % world bootstrap] | precision [95 %] | "
           "FA/cam-h | median latency s |"), "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["recall"]:
        L.append(f"| {r['rule']} | {r['scoring']} | {r['tolerance_s']} | {r['truth_events']} | {r['tp']} | "
                 f"{r['fp']} | {r['recall']:.3f} [{r['recall_boot95'][0]:.3f}, {r['recall_boot95'][1]:.3f}] | "
                 f"{r['precision']:.3f} [{r['precision_boot95'][0]:.3f}, {r['precision_boot95'][1]:.3f}] | "
                 f"{r['fa_per_camera_hour']} | {r['median_latency_s']} |")
    return "\n".join(L) + "\n"
