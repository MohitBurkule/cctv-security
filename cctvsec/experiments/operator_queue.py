"""H22: operator-in-the-loop alarm queue (docs/research/66, pre-registered in 32).

Replays the round-3 loiter alarm streams (A1 shipped rule, dwell_25, and a
hypothetical rule at the kinematic-twin floor) from the H12 worlds onto one
operator watching a 40-camera wall, and measures how much of the model's
recall a simulated operator actually realises.

Stages:
1. `streams` (cached to <out>/streams.json): per H12 world, every alarm as
   (t, uid, score, event) where `event` is the truth-event index the alarm
   hits under `eval.alarms.score`'s actor-aware 30 s matching (or -1). The
   model recall recomputed from these tags must equal round 3's.
2. `simulate`: worlds are shuffled (per operator seed) and laid end to end so
   that 40 camera-streams run concurrently (world k starts at the cumulative
   camera-seconds of worlds < k divided by 40). One operator, FIFO or
   score-ranked queue, gamma review times, fatigue after `fatigue_after_h` of
   each shift, bulk-acknowledge (queue cleared) when the queue exceeds N.
3. H60 slice 2: `run` also writes `<out>/alarms_scored.jsonl` — one row per alarm
   of operator seed 0 in every arm/queue cell (alarm key, score, θ, rank at
   arrival, the simulated operator's verdict) for `survsim alarm-cards --alarms`.
   The trace only records; it draws no random numbers, so results are unchanged.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

LAB = "suspicious.loiter"


# ------------------------------------------------------------------ matching

def tag_alarms(truth: list[dict], alarms: list[tuple[float, str]], tol: float = 30.0) -> list[int]:
    """Truth-event index each alarm hits, replicating `eval.alarms.score`
    (actor-aware, default mode): alarms in time order, first event whose
    window [t_start, t_start + tol] contains the alarm and whose actors include
    the uid. Repeats keep their event index (they are real sightings of the
    loiterer); the model's recall counts each event once."""
    order = sorted(range(len(alarms)), key=lambda i: alarms[i][0])
    out = [-1] * len(alarms)
    for i in order:
        t, uid = alarms[i]
        for j, ev in enumerate(truth):
            if ev["actors"] and uid not in ev["actors"]:
                continue
            if ev["t_start"] <= t <= ev["t_start"] + tol:
                out[i] = j
                break
    return out


# ------------------------------------------------------------------ streams

def _le():
    os.environ.setdefault("H58_OUT", "out/experiments/h58_round2")
    root = Path(__file__).resolve().parents[2]
    if str(root / "tools") not in sys.path:
        sys.path.insert(0, str(root / "tools"))
    import loiter_eval as LE
    return LE


def build_streams(cfg: dict[str, Any], workers: int = 6) -> dict[str, Any]:
    from ..eval.loiter_features import first_per_episode
    LE = _le()
    A1 = LE._build(json.loads((LE.R1 / "selection.json").read_text())["shipped"]["rule"])
    tab, metas = LE.load_split("h12")
    p = A1.score(tab)
    cond = A1.condition(tab) & ~tab["allowed"].to_numpy(bool)
    idx = first_per_episode(cond, tab["epk"].to_numpy())
    w_arr, t_arr, u_arr = tab["w"].to_numpy(), tab["t"].to_numpy(), tab["uid"].to_numpy()
    a1: dict[int, list] = {}
    for i in idx:
        a1.setdefault(int(w_arr[i]), []).append((float(t_arr[i]), str(u_arr[i]), float(p[i])))
    dw = LE.raw_alarms("h12", {"dwell_25": LE.H12_RULES["dwell_25"]}, workers)["dwell_25"]
    # rank key for dwell alarms: A1's probability for that person at the alarm tick
    keys = {(w, a[2]) for w, al in dw.items() for a in al}
    sub = tab.loc[[(w, u) in keys for w, u in zip(w_arr, u_arr)] if keys else [], ["w", "uid", "t"]]
    sub = sub.assign(p=p[sub.index.to_numpy()])
    look = {k: (g["t"].to_numpy(), g["p"].to_numpy())
            for k, g in sub.groupby([sub["w"].astype(int), sub["uid"].astype(str)], observed=True)}
    dwell: dict[int, list] = {}
    for w, al in dw.items():
        for t, _, u in al:
            ts, ps = look.get((int(w), str(u)), (np.array([]), np.array([])))
            j = int(np.searchsorted(ts, t, side="right")) - 1
            dwell.setdefault(int(w), []).append((float(t), str(u), float(ps[j]) if j >= 0 else 0.0))
    worlds = []
    for w, m in enumerate(metas):
        truth = [{"t_start": e["t_start"], "actors": list(e["actors"])} for e in m["truth"]]
        rec = {"mode": m["mode"], "camera_hours": m["camera_hours"], "n_truth": len(truth), "arms": {}}
        for name, src in (("A1", a1), ("dwell_25", dwell)):
            al = sorted(src.get(w, []))
            ev = tag_alarms(truth, [(a[0], a[1]) for a in al])
            rec["arms"][name] = [[a[0], a[2], e] for a, e in zip(al, ev)]
        worlds.append(rec)
    return {"worlds": worlds, "a1_rule": {"theta": A1.theta, "min_clock_s": A1.min_clock_s}}


def model_metrics(worlds: list[dict], arm: str) -> dict[str, float]:
    """Model recall / FA per cam-h from tagged streams (default mode: repeats are FPs)."""
    tp = ev = fp = 0
    ch = 0.0
    for w in worlds:
        al = w["arms"][arm]
        hit = {a[2] for a in al if a[2] >= 0}
        if w["mode"] == "recall":
            tp += len(hit)
            ev += w["n_truth"]
        else:
            fp += len(al)
            ch += w["camera_hours"]
    return {"recall": tp / max(ev, 1), "fa_per_cam_h": fp / ch if ch else 0.0, "truth": ev, "tp": tp}


def add_twin_floor(worlds: list[dict], rate: float) -> None:
    """Hypothetical arm: A1's alarms with false alarms thinned (lowest score
    first, globally) until the clean-world rate equals `rate`; true alarms
    untouched, so recall = A1's. Recall-world FPs are thinned at the same
    score cut."""
    clean_fp = sorted(a[1] for w in worlds if w["mode"] == "clean" for a in w["arms"]["A1"])
    ch = sum(w["camera_hours"] for w in worlds if w["mode"] == "clean")
    keep = round(rate * ch)
    cut = clean_fp[len(clean_fp) - keep] if 0 < keep <= len(clean_fp) else -np.inf
    for w in worlds:
        w["arms"]["twin_floor"] = [a for a in w["arms"]["A1"] if a[2] >= 0 or a[1] >= cut]
    return float(cut)


# ------------------------------------------------------------------ operator

def simulate(worlds: list[dict], arm: str, policy: str, seed: int, op: dict[str, Any],
             trace: list[dict] | None = None) -> dict[str, Any]:
    """One operator shift sequence. Returns per-world realised counts and utilisation.

    Realised at horizon H: an alarm that hits a truth event is *taken up for
    review* within H seconds of being raised, and the operator recognises it
    (probability 1 - miss, higher when fatigued). An event counts once.

    ``trace`` (optional list) receives one dict per alarm: world, index in the
    world's stream, local t, score, rank_in_queue at arrival (1 = next to be
    taken under `policy`), verdict (dispatch = true alarm recognised; dismiss =
    reviewed and not recognised/false; bulk_ack = cleared unreviewed) and
    t_verdict (local). It never touches the RNG."""
    rng = np.random.default_rng(seed)
    n_cams = op["cameras"]
    order = rng.permutation(len(worlds))
    start = np.zeros(len(worlds))
    acc = 0.0
    for k in order:
        start[k] = acc / n_cams
        acc += worlds[k]["camera_hours"] * 3600.0
    total_s = acc / n_cams
    ev = []  # (wall t, score, world, event, index in world stream)
    for k, w in enumerate(worlds):
        for n, (t, s, e) in enumerate(w["arms"][arm]):
            ev.append((start[k] + t, s, k, e, n))
    ev.sort()
    shift = op["shift_h"] * 3600.0
    fat = op["fatigue_after_h"] * 3600.0
    mean, cv = op["review_s"], op["review_cv"]
    shape = 1.0 / cv**2
    horizons = op["horizons_s"]
    realised = {h: set() for h in horizons}
    queue: list[tuple[float, float, int, int, int]] = []  # (raise t, score, world, event, n)
    rec: dict[tuple[int, int], dict] = {}
    busy = 0.0
    n_ops = int(op.get("operators", 1))
    free = [0.0] * n_ops  # per-operator time free; they share one queue
    n_bulk = n_bulk_dropped = n_reviewed = 0
    i = 0

    def take(now: float):
        nonlocal busy, n_reviewed
        if policy == "ranked":
            j = max(range(len(queue)), key=lambda q: (queue[q][1], -queue[q][0]))
        else:
            j = 0
        t0, _s, k, e, n = queue.pop(j)
        fatigued = (now % shift) >= fat
        dur = rng.gamma(shape, mean * (op["fatigue_review_x"] if fatigued else 1.0) / shape)
        miss = op["miss_fatigued"] if fatigued else op["miss"]
        seen = rng.random() >= miss
        if e >= 0 and seen:
            for h in horizons:
                if now - t0 <= h:
                    realised[h].add((k, e))
        if trace is not None:
            r = rec[(k, n)]
            r["verdict"] = "dispatch" if (e >= 0 and seen) else "dismiss"
            r["reason_code"] = None if r["verdict"] == "dispatch" else "no_threat"
            r["t_verdict"] = float(now + dur - start[k])
        busy += dur
        n_reviewed += 1
        free[free.index(min(free))] = now + dur

    while i < len(ev) or queue:
        nxt = ev[i][0] if i < len(ev) else np.inf
        if queue and min(free) <= nxt:
            take(min(free))  # every queued alarm arrived at or before the free time
            continue
        t, s, k, e, n = ev[i]
        i += 1
        if trace is not None:
            rank = (len(queue) + 1 if policy != "ranked" else
                    1 + sum(1 for q in queue if (q[1], -q[0]) > (s, -t)))
            rec[(k, n)] = r = {"world": int(k), "index": int(n), "t": float(t - start[k]),
                               "score": float(s), "rank_in_queue": int(rank),
                               "queue_len_at_arrival": len(queue)}
            trace.append(r)
        queue.append((t, s, k, e, n))
        if len(queue) > op["bulk_ack_queue"]:
            if trace is not None:
                for q in queue:
                    rec[(q[2], q[4])].update(verdict="bulk_ack", reason_code=None,
                                             t_verdict=float(t - start[q[2]]))
            n_bulk += 1
            n_bulk_dropped += len(queue)
            queue.clear()
        if queue:
            free = [max(f, t) for f in free]
    per_world = {h: np.zeros(len(worlds)) for h in horizons}
    for h in horizons:
        for k, _ in realised[h]:
            per_world[h][k] += 1
    return {"per_world": {str(h): per_world[h].tolist() for h in horizons},
            "utilisation": min(busy / (total_s * n_ops), 1.0), "wall_h": total_s / 3600, "alarms": len(ev),
            "alarms_per_h": len(ev) / (total_s / 3600), "reviewed": n_reviewed,
            "bulk_acks": n_bulk, "bulk_dropped": n_bulk_dropped}


def _boot(num: np.ndarray, den: np.ndarray, rec_idx: np.ndarray, n_boot: int, seed: int) -> list[float]:
    """World-cluster bootstrap of sum(num)/sum(den) over recall worlds (num: seeds x worlds)."""
    rng = np.random.default_rng(seed)
    b = rng.choice(rec_idx, (n_boot, len(rec_idx)))
    vals = num[:, b].sum(axis=(0, 2)) / np.maximum(den[b].sum(1) * num.shape[0], 1)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    if "operating_points" in cfg:  # H45
        return run_points(cfg, out)
    cache = out / "streams.json"
    if cache.is_file():
        st = json.loads(cache.read_text())
    else:
        st = build_streams(cfg, int(cfg.get("workers", 6)))
        cache.write_text(json.dumps(st))
    worlds = st["worlds"]
    cut = add_twin_floor(worlds, float(cfg["twin_floor_fa_per_cam_h"]))
    op = cfg["operator"]
    a1_theta = st.get("a1_rule", {}).get("theta")
    # θ per arm: A1 and twin_floor fire at A1's θ (twin_floor additionally drops false
    # alarms below a score cut); dwell_25 is a dwell rule with no θ (score is A1's p, rank only).
    thetas = {"A1": a1_theta, "twin_floor": a1_theta, "dwell_25": None}
    scored: list[dict] = []
    den = np.array([w["n_truth"] if w["mode"] == "recall" else 0 for w in worlds], float)
    rec_idx = np.flatnonzero(np.array([w["mode"] == "recall" for w in worlds]))
    results: dict[str, Any] = {"model": {a: model_metrics(worlds, a) for a in cfg["arms"]}, "cells": {}}
    for arm in cfg["arms"]:
        for pol in cfg["policies"]:
            tr: list[dict] = []
            sims = [simulate(worlds, arm, pol, s, op, trace=tr if j == 0 else None)
                    for j, s in enumerate(cfg["operator_seeds"])]
            for r in tr:
                r.update(key=f"h22/{arm}/{pol}/seed{cfg['operator_seeds'][0]}/w{r['world']}/{r['index']}",
                         arm=arm, policy=pol, operator_seed=cfg["operator_seeds"][0], label=LAB,
                         theta=thetas.get(arm), score_cut=cut if arm == "twin_floor" and np.isfinite(cut) else None)
            scored += tr
            cell: dict[str, Any] = {"utilisation": [s["utilisation"] for s in sims],
                                    "alarms_per_h": sims[0]["alarms_per_h"], "wall_h": sims[0]["wall_h"],
                                    "bulk_acks_mean": float(np.mean([s["bulk_acks"] for s in sims])),
                                    "bulk_dropped_frac": float(np.mean([s["bulk_dropped"] / max(s["alarms"], 1)
                                                                        for s in sims])), "horizons": {}}
            for h in op["horizons_s"]:
                num = np.array([s["per_world"][str(h)] for s in sims])
                per_seed = (num.sum(1) / den.sum()).tolist()
                pooled = float(num.sum() / (den.sum() * len(sims)))
                cell["horizons"][str(h)] = {
                    "realised_recall": pooled, "boot95": _boot(num, den, rec_idx, 2000, 22),
                    "per_seed": per_seed, "seed_range": [min(per_seed), max(per_seed)],
                    "fraction_of_model": pooled / max(results["model"][arm]["recall"], 1e-9),
                    "_num": num.tolist()}
            u = np.array(cell["utilisation"])
            cell["utilisation_mean"] = float(u.mean())
            cell["utilisation_range"] = [float(u.min()), float(u.max())]
            results["cells"][f"{arm}/{pol}"] = cell
    # paired ranked - FIFO, same seeds, world-cluster bootstrap
    rng_seed = 23
    results["ranked_minus_fifo"] = {}
    for arm in cfg["arms"]:
        for h in op["horizons_s"]:
            a = np.array(results["cells"][f"{arm}/fifo"]["horizons"][str(h)]["_num"])
            b = np.array(results["cells"][f"{arm}/ranked"]["horizons"][str(h)]["_num"])
            d = b - a
            rng = np.random.default_rng(rng_seed)
            bi = rng.choice(rec_idx, (2000, len(rec_idx)))
            vals = d[:, bi].sum(axis=(0, 2)) / np.maximum(den[bi].sum(1) * d.shape[0], 1)
            results["ranked_minus_fifo"][f"{arm}@{h}"] = {
                "diff": float(d.sum() / (den.sum() * d.shape[0])),
                "boot95": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
                "seeds_positive": int((d.sum(1) > 0).sum()), "seeds_negative": int((d.sum(1) < 0).sum())}
    for c in results["cells"].values():
        for hv in c["horizons"].values():
            hv.pop("_num")
    (out / "alarms_scored.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in scored))
    prim = results["cells"][f"{cfg['primary']['arm']}/{cfg['primary']['policy']}"]["horizons"][
        str(cfg["primary"]["horizon_s"])]
    bar = cfg["primary"]["fraction"] * results["model"][cfg["primary"]["arm"]]["recall"]
    results["decision"] = {"bar": bar, "realised": prim["realised_recall"], "boot95": prim["boot95"],
                           "supported": prim["boot95"][1] < bar,
                           "refuted": prim["boot95"][0] >= bar}
    results["decision"]["branch"] = ("supported" if results["decision"]["supported"] else
                                     "refuted" if results["decision"]["refuted"] else "inconclusive")
    results["n_worlds"] = len(worlds)
    results["clean_cam_h"] = float(sum(w["camera_hours"] for w in worlds if w["mode"] == "clean"))
    return results


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    if "operating_points" in cfg:
        return markdown_points(res)
    L = [("| arm | model FA/cam-h | model recall | alarms/h (40 cams) | queue | utilisation | "
          "realised @30 s [95 %] | realised @5 min [95 %] | bulk-dropped |"), "|---|---|---|---|---|---|---|---|---|"]
    for k, c in res["cells"].items():
        arm, pol = k.split("/")
        m = res["model"][arm]
        h30, h300 = c["horizons"]["30"], c["horizons"]["300"]
        L.append(f"| {arm} | {m['fa_per_cam_h']:.3f} | {m['recall']:.3f} | {c['alarms_per_h']:.0f} | {pol} | "
                 f"{c['utilisation_mean']:.2f} | {h30['realised_recall']:.3f} [{h30['boot95'][0]:.3f}, "
                 f"{h30['boot95'][1]:.3f}] | {h300['realised_recall']:.3f} [{h300['boot95'][0]:.3f}, "
                 f"{h300['boot95'][1]:.3f}] | {c['bulk_dropped_frac']:.2f} |")
    L += ["", "| ranked − FIFO | Δ realised recall | 95 % | seeds +/− |", "|---|---|---|---|"]
    for k, d in res["ranked_minus_fifo"].items():
        L.append(f"| {k} | {d['diff']:+.3f} | [{d['boot95'][0]:+.3f}, {d['boot95'][1]:+.3f}] | "
                 f"{d['seeds_positive']}/{d['seeds_negative']} |")
    for k, d in res.get("paired_extra", {}).items():
        L.append(f"| {k} | {d['diff']:+.3f} | [{d['boot95'][0]:+.3f}, {d['boot95'][1]:+.3f}] | "
                 f"{d['seeds_positive']}/{d['seeds_negative']} |")
    L.append(f"\ndecision: {res['decision']}")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ H45 operating points

def build_point_streams(points: dict[str, float], point_caps: dict[str, int] | None = None) -> dict[str, Any]:
    """H45: A1's frozen weights at several θ (clock unchanged) on the H12
    worlds, tagged exactly as `build_streams` tags A1. `point_caps` (H45c) gives
    a point max_alarms_per_uid_per_world; absent = one alarm per episode."""
    import dataclasses

    from ..eval.loiter_features import first_per_episode
    LE = _le()
    A1 = LE._build(json.loads((LE.R1 / "selection.json").read_text())["shipped"]["rule"])
    tab, metas = LE.load_split("h12")
    p = A1.score(tab)
    w_arr, t_arr, u_arr = tab["w"].to_numpy(), tab["t"].to_numpy(), tab["uid"].to_numpy()
    srcs = {}
    for name, th in points.items():
        rule = dataclasses.replace(A1, theta=float(th))
        cond = rule.condition(tab) & ~tab["allowed"].to_numpy(bool)
        d: dict[int, list] = {}
        for i in first_per_episode(cond, tab["epk"].to_numpy()):
            d.setdefault(int(w_arr[i]), []).append((float(t_arr[i]), str(u_arr[i]), float(p[i])))
        srcs[name] = LE.cap_per_uid(d, (point_caps or {}).get(name), uid_pos=1)
    worlds = []
    for w, m in enumerate(metas):
        truth = [{"t_start": e["t_start"], "actors": list(e["actors"])} for e in m["truth"]]
        rec = {"mode": m["mode"], "camera_hours": m["camera_hours"], "n_truth": len(truth), "arms": {}}
        for name, src in srcs.items():
            al = sorted(src.get(w, []))
            ev = tag_alarms(truth, [(a[0], a[1]) for a in al])
            rec["arms"][name] = [[a[0], a[2], e] for a, e in zip(al, ev)]
        worlds.append(rec)
    out = {"worlds": worlds, "points": dict(points), "min_clock_s": A1.min_clock_s}
    if point_caps:
        out["point_caps"] = dict(point_caps)
    return out


def _paired(a: np.ndarray, b: np.ndarray, den: np.ndarray, rec_idx: np.ndarray, seed: int) -> dict[str, Any]:
    """b − a realised recall (seeds x worlds), same seeds, world-cluster bootstrap."""
    d = b - a
    rng = np.random.default_rng(seed)
    bi = rng.choice(rec_idx, (2000, len(rec_idx)))
    vals = d[:, bi].sum(axis=(0, 2)) / np.maximum(den[bi].sum(1) * d.shape[0], 1)
    return {"diff": float(d.sum() / (den.sum() * d.shape[0])),
            "boot95": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
            "seeds_positive": int((d.sum(1) > 0).sum()), "seeds_negative": int((d.sum(1) < 0).sum())}


def run_points(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    pts = cfg["operating_points"]
    cache = out / "point_streams.json"
    caps = cfg.get("point_caps")
    st = json.loads(cache.read_text()) if cache.is_file() else None
    if not (st and st["points"] == pts and st.get("point_caps") == caps):
        st = build_point_streams(pts, caps)
        cache.write_text(json.dumps(st))
    worlds = st["worlds"]
    den = np.array([w["n_truth"] if w["mode"] == "recall" else 0 for w in worlds], float)
    rec_idx = np.flatnonzero(np.array([w["mode"] == "recall" for w in worlds]))
    ref = cfg.get("reference", "A1")
    hs = cfg["operator"]["horizons_s"]
    res: dict[str, Any] = {"model": {a: model_metrics(worlds, a) for a in pts}, "cells": {}, "vs_ref": {}}
    nums: dict[str, np.ndarray] = {}
    for n_ops in cfg["operator_counts"]:
        op = {**cfg["operator"], "operators": n_ops}
        for arm in pts:
            for pol in cfg["policies"]:
                sims = [simulate(worlds, arm, pol, s, op) for s in cfg["operator_seeds"]]
                key = f"{arm}/{pol}/{n_ops}"
                u = np.array([s["utilisation"] for s in sims])
                cell: dict[str, Any] = {"arm": arm, "policy": pol, "operators": n_ops,
                                        "utilisation_mean": float(u.mean()),
                                        "utilisation_range": [float(u.min()), float(u.max())],
                                        "alarms_per_h": sims[0]["alarms_per_h"],
                                        "bulk_acks_mean": float(np.mean([s["bulk_acks"] for s in sims])),
                                        "bulk_dropped_frac": float(np.mean([s["bulk_dropped"] / max(s["alarms"], 1)
                                                                            for s in sims])), "horizons": {}}
                for h in hs:
                    num = np.array([s["per_world"][str(h)] for s in sims])
                    nums[f"{key}@{h}"] = num
                    per_seed = (num.sum(1) / den.sum()).tolist()
                    cell["horizons"][str(h)] = {
                        "realised_recall": float(num.sum() / (den.sum() * len(sims))),
                        "boot95": _boot(num, den, rec_idx, 2000, 45), "seed_range": [min(per_seed), max(per_seed)],
                        "fraction_of_model": float(num.sum() / (den.sum() * len(sims)))
                        / max(res["model"][arm]["recall"], 1e-9)}
                res["cells"][key] = cell
        for arm in pts:
            if arm == ref:
                continue
            for pol in cfg["policies"]:
                for h in hs:
                    res["vs_ref"][f"{arm}-{ref}/{pol}/{n_ops}@{h}"] = _paired(
                        nums[f"{ref}/{pol}/{n_ops}@{h}"], nums[f"{arm}/{pol}/{n_ops}@{h}"], den, rec_idx, 46)
        if cfg.get("paired_extra"):  # H45b: an extra paired contrast, e.g. certified vs H45 conformal
            xa, xb = cfg["paired_extra"]
            for pol in cfg["policies"]:
                for h in hs:
                    res.setdefault("paired_extra", {})[f"{xa}-{xb}/{pol}/{n_ops}@{h}"] = _paired(
                        nums[f"{xb}/{pol}/{n_ops}@{h}"], nums[f"{xa}/{pol}/{n_ops}@{h}"], den, rec_idx, 46)
    # decision (pre-registered, one operator, 5 min)
    pr = cfg["primary"]
    H, n1 = pr["horizon_s"], 1
    a_ok, b_ok, detail = True, True, {}
    for pol in cfg["policies"]:
        dp = res["vs_ref"][f"{pr['pooled']}-{ref}/{pol}/{n1}@{H}"]
        dc = res["vs_ref"][f"{pr['conformal']}-{ref}/{pol}/{n1}@{H}"]
        u_ref = res["cells"][f"{ref}/{pol}/{n1}"]["utilisation_mean"]
        u_c = res["cells"][f"{pr['conformal']}/{pol}/{n1}"]["utilisation_mean"]
        cut = 1 - u_c / u_ref
        a = -pr["pooled_band"] <= dp["boot95"][0] and dp["boot95"][1] <= pr["pooled_band"]
        b = dc["boot95"][0] >= -pr["conformal_max_loss"] and cut >= pr["util_cut"]
        detail[pol] = {"pooled_within_band": a, "conformal_ok": b, "conformal_util_cut": cut}
        a_ok &= a
        b_ok &= b
    cross = {}
    for pol in cfg["policies"]:
        cross[pol] = next((n for n in cfg["operator_counts"]
                           if res["vs_ref"][f"{pr['pooled']}-{ref}/{pol}/{n}@{H}"]["boot95"][0] > 0), None)
    res["decision"] = {"a_pooled_not_realised": a_ok, "b_conformal_ok": b_ok, "hypothesis_met": a_ok and b_ok,
                       "detail": detail, "pooled_beats_ref_at_operators": cross}
    res["n_worlds"] = len(worlds)
    return res


def markdown_points(res: dict[str, Any]) -> str:
    L = [("| point | model FA/cam-h | model recall | ops | queue | alarms/h | utilisation | "
          "realised @30 s [95 %] | realised @5 min [95 %] | bulk-dropped |"), "|---|---|---|---|---|---|---|---|---|---|"]
    for c in res["cells"].values():
        m = res["model"][c["arm"]]
        h30, h300 = c["horizons"]["30"], c["horizons"]["300"]
        L.append(f"| {c['arm']} | {m['fa_per_cam_h']:.3f} | {m['recall']:.3f} | {c['operators']} | {c['policy']} | "
                 f"{c['alarms_per_h']:.0f} | {c['utilisation_mean']:.2f} | {h30['realised_recall']:.3f} "
                 f"[{h30['boot95'][0]:.3f}, {h30['boot95'][1]:.3f}] | {h300['realised_recall']:.3f} "
                 f"[{h300['boot95'][0]:.3f}, {h300['boot95'][1]:.3f}] | {c['bulk_dropped_frac']:.2f} |")
    L += ["", "| point − A1 / queue / ops @ horizon | Δ realised | 95 % | seeds +/− |", "|---|---|---|---|"]
    for k, d in res["vs_ref"].items():
        L.append(f"| {k} | {d['diff']:+.3f} | [{d['boot95'][0]:+.3f}, {d['boot95'][1]:+.3f}] | "
                 f"{d['seeds_positive']}/{d['seeds_negative']} |")
    for k, d in res.get("paired_extra", {}).items():
        L.append(f"| {k} | {d['diff']:+.3f} | [{d['boot95'][0]:+.3f}, {d['boot95'][1]:+.3f}] | "
                 f"{d['seeds_positive']}/{d['seeds_negative']} |")
    L.append(f"\ndecision: {res['decision']}")
    return "\n".join(L) + "\n"
