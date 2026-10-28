"""H37 (mock-only slice): forensic attribute+time+place search recall, and the
appearance-epoch pooling trap (docs/research/72 §3, 66 H37, AUDIT_72).

Generates seeded *mock* worlds directly (no Director/backend, no renders): each
world is a set of identities with GT appearance epochs (colour x garment) and a
schedule of zone-visit segments, mirroring what `survsim/gt/writers.py` records
in `identities.parquet` (one row per epoch) and `world.parquet` (per-tick zone
occupancy) for a real run. This is the "mock backend (attribute oracle + noise)"
arm the H37 pre-registration budgets for CPU now; the CLIP arms (C/D) need
renders and are explicitly out of scope here.

Two indexes are built from the *same* GT:
  (A) pooled per track  -- one attribute set per uid, union over its epochs.
      A query matches a uid if the pooled set contains the query attribute AND
      the uid has *any* zone visit overlapping the window -- the visit's own
      epoch is not checked, which is the trap: a visit that happened under a
      *different* outfit still counts as a hit.
  (B) per epoch-segment  -- one entry per (uid, epoch). A query matches an
      entry only if that epoch's own attribute matches AND that epoch's visits
      (not the uid's other epochs) overlap the window.

Both are queried by exact attribute+place match, ranked by dwell (overlap
seconds with the query window, descending), top 10. Ground truth relevance is
always computed per-epoch (72 §3.1: "attribute in their active epoch").
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .inference import bootstrap_mean_diff

COLOURS = ["red", "blue", "black"]
GARMENTS = ["hoodie", "jacket"]
ZONES = ["gate", "yard", "dock"]


# --------------------------------------------------------------------- worlds

def gen_world(seed: int, n_identities: int, duration_s: float, changer_frac: float) -> dict[str, Any]:
    """One seeded mock world: identities with GT appearance epochs and visit segments."""
    rng = np.random.default_rng(seed)
    identities = []
    n_changers = max(1, round(n_identities * changer_frac))
    changer = np.zeros(n_identities, bool)
    changer[rng.choice(n_identities, n_changers, replace=False)] = True
    for i in range(n_identities):
        uid = f"p{seed:03d}_{i:02d}"
        c0, g0 = rng.choice(COLOURS), rng.choice(GARMENTS)
        epochs = [{"epoch": 0, "t_from": 0.0, "t_to": duration_s, "colour": str(c0), "garment": str(g0)}]
        if changer[i]:
            t_change = float(rng.uniform(0.25, 0.75) * duration_s)
            epochs[0]["t_to"] = t_change
            c1, g1 = c0, g0
            while c1 == c0 and g1 == g0:  # force a real change
                c1, g1 = rng.choice(COLOURS), rng.choice(GARMENTS)
            epochs.append({"epoch": 1, "t_from": t_change, "t_to": duration_s,
                           "colour": str(c1), "garment": str(g1)})
        # visit schedule: a handful of non-overlapping zone dwells across the run
        n_seg = int(rng.integers(4, 8))
        cuts = np.sort(rng.uniform(0, duration_s, n_seg * 2))
        segments = []
        for k in range(n_seg):
            t_in, t_out = float(cuts[2 * k]), float(cuts[2 * k + 1])
            if t_out - t_in < 5:
                continue
            zone = str(rng.choice(ZONES))
            e = next(ep["epoch"] for ep in epochs if ep["t_from"] <= t_in < ep["t_to"])
            segments.append({"t_in": t_in, "t_out": t_out, "zone": zone, "epoch": e})
        identities.append({"uid": uid, "epochs": epochs, "segments": segments})
    return {"seed": seed, "duration_s": duration_s, "identities": identities}


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


# -------------------------------------------------------------------- queries

def build_queries(world: dict[str, Any], n: int, rng: np.random.Generator,
                  boundary_frac: float) -> list[dict[str, Any]]:
    """Attribute+time+place queries, >= boundary_frac with a boundary in the window."""
    idents = world["identities"]
    changers = [p for p in idents if len(p["epochs"]) > 1]
    queries = []
    n_boundary_target = round(n * boundary_frac)
    for i in range(n):
        want_boundary = i < n_boundary_target and changers
        anchor = rng.choice(changers if want_boundary else idents)
        if want_boundary:
            t_change = anchor["epochs"][0]["t_to"]
            pad = float(rng.uniform(60, 300))
            t1, t2 = max(0.0, t_change - pad), min(world["duration_s"], t_change + pad)
            ep = anchor["epochs"][0] if rng.random() < 0.5 else anchor["epochs"][-1]
        else:
            seg = anchor["segments"][int(rng.integers(0, len(anchor["segments"])))] \
                if anchor["segments"] else None
            if seg is None:
                continue
            t1 = max(0.0, seg["t_in"] - float(rng.uniform(0, 120)))
            t2 = min(world["duration_s"], seg["t_out"] + float(rng.uniform(0, 120)))
            ep = next(e for e in anchor["epochs"] if e["epoch"] == seg["epoch"])
        zone = str(rng.choice(ZONES))
        queries.append({"colour": ep["colour"], "garment": ep["garment"], "zone": zone,
                        "t1": t1, "t2": t2, "has_boundary": bool(want_boundary)})
    return queries


# -------------------------------------------------------------------- indexes

def _apply_noise(colour: str, garment: str, flip_p: float, rng: np.random.Generator) -> tuple[str, str]:
    if flip_p and rng.random() < flip_p:
        colour = str(rng.choice([c for c in COLOURS if c != colour]))
    if flip_p and rng.random() < flip_p:
        garment = str(rng.choice([g for g in GARMENTS if g != garment]))
    return colour, garment


def build_pooled_index(world: dict[str, Any], flip_p: float, seed: int) -> dict[str, dict[str, Any]]:
    """(A) pooled per track: attribute is a union set over the uid's epochs,
    with segments carrying no epoch attribute of their own -- any zone visit
    can be matched by any pooled attribute the person ever wore."""
    rng = np.random.default_rng(seed)
    idx = {}
    for p in world["identities"]:
        pooled = {_apply_noise(e["colour"], e["garment"], flip_p, rng) for e in p["epochs"]}
        idx[p["uid"]] = {"attrs": pooled, "segments": p["segments"]}
    return idx


def build_epoch_index(world: dict[str, Any], flip_p: float, seed: int) -> list[dict[str, Any]]:
    """(B) one entry per (uid, epoch): attribute and segments both scoped to
    that epoch only."""
    rng = np.random.default_rng(seed)
    entries = []
    for p in world["identities"]:
        for e in p["epochs"]:
            c, g = _apply_noise(e["colour"], e["garment"], flip_p, rng)
            segs = [s for s in p["segments"] if s["epoch"] == e["epoch"]]
            entries.append({"uid": p["uid"], "epoch": e["epoch"], "colour": c, "garment": g, "segments": segs})
    return entries


def _dwell(segments: list[dict[str, Any]], zone: str, t1: float, t2: float) -> float:
    return sum(_overlap(s["t_in"], s["t_out"], t1, t2) for s in segments if s["zone"] == zone)


def retrieve_pooled(idx: dict[str, dict[str, Any]], q: dict[str, Any], k: int = 10) -> list[str]:
    cand = []
    for uid, entry in idx.items():
        if (q["colour"], q["garment"]) not in entry["attrs"]:
            continue
        dwell = _dwell(entry["segments"], q["zone"], q["t1"], q["t2"])
        if dwell > 0:
            cand.append((dwell, uid))
    cand.sort(key=lambda x: (-x[0], x[1]))
    return [uid for _, uid in cand[:k]]


def retrieve_epoch(entries: list[dict[str, Any]], q: dict[str, Any], k: int = 10) -> list[str]:
    cand = []
    for e in entries:
        if e["colour"] != q["colour"] or e["garment"] != q["garment"]:
            continue
        dwell = _dwell(e["segments"], q["zone"], q["t1"], q["t2"])
        if dwell > 0:
            cand.append((dwell, e["uid"]))
    # a track counts once even if two of its epochs both matched (recall@10 is uid-level)
    seen: set[str] = set()
    out = []
    for dwell, uid in sorted(cand, key=lambda x: (-x[0], x[1])):
        if uid in seen:
            continue
        seen.add(uid)
        out.append(uid)
        if len(out) == k:
            break
    return out


def ground_truth_relevant(world: dict[str, Any], q: dict[str, Any]) -> set[str]:
    """R = uids with the query attribute active in an epoch that visited the
    query zone inside the query window (72 §3.1)."""
    rel = set()
    for p in world["identities"]:
        for e in p["epochs"]:
            if e["colour"] != q["colour"] or e["garment"] != q["garment"]:
                continue
            if _dwell([s for s in p["segments"] if s["epoch"] == e["epoch"]], q["zone"], q["t1"], q["t2"]) > 0:
                rel.add(p["uid"])
                break
    return rel


# --------------------------------------------------------------------- scoring

def recall_precision_at_k(top: list[str], relevant: set[str], k: int = 10) -> tuple[float, float]:
    if not relevant:
        return float("nan"), float("nan")
    hit = len(set(top) & relevant)
    return hit / len(relevant), hit / k


def run_condition(worlds: list[dict[str, Any]], queries_by_world: list[list[dict[str, Any]]],
                  flip_p: float, seed: int) -> dict[str, list[float]]:
    """Per-query recall@10/precision@10 for both arms, over all worlds."""
    out: dict[str, list[float]] = {"pooled_recall": [], "epoch_recall": [], "pooled_prec": [], "epoch_prec": [],
                                    "has_boundary": []}
    for wi, (world, qs) in enumerate(zip(worlds, queries_by_world)):
        pooled_idx = build_pooled_index(world, flip_p, seed * 1000 + wi)
        epoch_idx = build_epoch_index(world, flip_p, seed * 1000 + wi + 1)
        for q in qs:
            rel = ground_truth_relevant(world, q)
            if not rel:
                continue
            pr, pp = recall_precision_at_k(retrieve_pooled(pooled_idx, q), rel)
            er, ep = recall_precision_at_k(retrieve_epoch(epoch_idx, q), rel)
            out["pooled_recall"].append(pr)
            out["epoch_recall"].append(er)
            out["pooled_prec"].append(pp)
            out["epoch_prec"].append(ep)
            out["has_boundary"].append(q["has_boundary"])
    return out


def _summ(a: list[float], b: list[float], seed: int) -> dict[str, Any]:
    a, b = np.asarray(a, float), np.asarray(b, float)
    lo, hi = bootstrap_mean_diff(a, b, n_boot=10000, seed=seed)
    return {"pooled_mean": round(float(a.mean()), 4), "epoch_mean": round(float(b.mean()), 4),
            "diff_epoch_minus_pooled": round(float(b.mean() - a.mean()), 4),
            "diff_boot95": [round(lo, 4), round(hi, 4)], "n": len(a)}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    seed = int(cfg.get("seed", 0))
    n_worlds = int(cfg["n_worlds"])
    n_identities = int(cfg["n_identities"])
    duration_s = float(cfg["duration_s"])
    changer_frac = float(cfg["changer_frac"])
    n_queries_per_world = int(cfg["n_queries_per_world"])
    boundary_frac = float(cfg["boundary_frac"])
    noise_levels = cfg["noise_levels"]

    worlds = [gen_world(seed * 10_000 + w, n_identities, duration_s, changer_frac) for w in range(n_worlds)]
    q_rng = np.random.default_rng(seed)
    queries_by_world = [build_queries(w, n_queries_per_world, q_rng, boundary_frac) for w in worlds]

    n_boundary = sum(q["has_boundary"] for qs in queries_by_world for q in qs)
    n_total_q = sum(len(qs) for qs in queries_by_world)
    frac_changers = float(np.mean([len(p["epochs"]) > 1 for w in worlds for p in w["identities"]]))

    res: dict[str, Any] = {
        "n_worlds": n_worlds, "n_identities_per_world": n_identities,
        "frac_identities_with_clothing_change": round(frac_changers, 4),
        "n_queries_total": n_total_q, "n_queries_with_boundary": n_boundary,
        "frac_queries_with_boundary": round(n_boundary / max(1, n_total_q), 4),
        "noise_levels": {},
    }

    for flip_p in noise_levels:
        m = run_condition(worlds, queries_by_world, flip_p, seed)
        n_scored = len(m["pooled_recall"])
        boundary_mask = np.array(m["has_boundary"], bool)
        cell = {
            "n_queries_scored": n_scored,
            "recall_at_10": _summ(m["pooled_recall"], m["epoch_recall"], seed),
            "precision_at_10": _summ(m["pooled_prec"], m["epoch_prec"], seed),
        }
        if boundary_mask.any():
            cell["recall_at_10_boundary_subset"] = _summ(
                list(np.array(m["pooled_recall"])[boundary_mask]),
                list(np.array(m["epoch_recall"])[boundary_mask]), seed)
        res["noise_levels"][str(flip_p)] = cell

    primary = res["noise_levels"][str(noise_levels[0])]["recall_at_10"]
    res["hypothesis_check"] = {
        "H37_mock_slice": "uid recall@10 is >= 0.15 lower when attributes are pooled per track "
                          "than per epoch-segmented track",
        "diff_epoch_minus_pooled": primary["diff_epoch_minus_pooled"],
        "diff_boot95": primary["diff_boot95"],
        "met": bool(primary["diff_epoch_minus_pooled"] >= 0.15 and primary["diff_boot95"][0] > 0),
    }
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    header = (f"{res['n_worlds']} mock worlds x {res['n_identities_per_world']} identities "
              f"({res['frac_identities_with_clothing_change']:.0%} with a clothing change); "
              f"{res['n_queries_total']} queries, {res['frac_queries_with_boundary']:.0%} with an epoch "
              "boundary inside the window.")
    L = [header, "",
         "| noise (attr flip) | metric | pooled mean | per-epoch mean | epoch - pooled [95% boot] | n |",
         "|---|---|---|---|---|---|"]
    for noise, cell in res["noise_levels"].items():
        for metric in ("recall_at_10", "precision_at_10"):
            v = cell[metric]
            L.append(f"| {noise} | {metric} | {v['pooled_mean']:.3f} | {v['epoch_mean']:.3f} | "
                     f"{v['diff_epoch_minus_pooled']:+.3f} [{v['diff_boot95'][0]:+.3f}, {v['diff_boot95'][1]:+.3f}] "
                     f"| {v['n']} |")
        if "recall_at_10_boundary_subset" in cell:
            v = cell["recall_at_10_boundary_subset"]
            L.append(f"| {noise} | recall_at_10 (boundary subset) | {v['pooled_mean']:.3f} | "
                     f"{v['epoch_mean']:.3f} | {v['diff_epoch_minus_pooled']:+.3f} "
                     f"[{v['diff_boot95'][0]:+.3f}, {v['diff_boot95'][1]:+.3f}] | {v['n']} |")
    h = res["hypothesis_check"]
    verdict = (f"**H37 mock slice: {'met' if h['met'] else 'not met'}** "
              f"(epoch - pooled = {h['diff_epoch_minus_pooled']:+.3f} "
              f"[{h['diff_boot95'][0]:+.3f}, {h['diff_boot95'][1]:+.3f}] vs bar >= 0.15 with CI lower bound > 0).")
    L += ["", verdict]
    return "\n".join(L) + "\n"
