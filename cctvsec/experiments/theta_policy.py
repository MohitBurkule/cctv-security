"""H42: θ-selection policy for the frozen A1 loiter weights (docs/research/66
H42, pre-registered in docs/research/32).

Round 4 (58 §8.2) found that one ~106-event select fold decides whether A1
ships at θ 0.9 or 0.95. H42 compares four ways of choosing (θ, clock) from the
select folds of the 10 H23 train splits — per-fold (round-4 control), pooled
leave-one-fold-out, conformal risk control (H33) on the pooled clean worlds,
and pooled with a 0.80 recall floor on a fine grid — by the between-draw
spread of the H12 FA/cam-h each choice realises.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

FOLD_SEEDS = (58, 158, 258, 358, 458, 558, 658, 758, 858, 958)
SEL_GRID = (0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999)
FINE_GRID = tuple(round(0.85 + 0.01 * i, 2) for i in range(15))
CLOCKS = (5.0, 10.0, 15.0)
POLICIES = ("per_fold", "pooled", "crc", "pooled_floor")


# ------------------------------------------------------------------ pure core

def pick(stats: list[dict], thetas, recall_min: float) -> dict[str, Any]:
    """Round-4 `_select` on summed counts. stats rows: theta, clock, fa, cam_h,
    tp, truth (already summed over the folds in use). Min FA/cam-h among
    points with recall >= recall_min (ties -> higher recall); none -> max recall."""
    rows = [dict(r, fa_per_cam_h=r["fa"] / r["cam_h"], recall=r["tp"] / max(r["truth"], 1))
            for r in stats if any(abs(r["theta"] - t) < 1e-9 for t in thetas)]
    ok = [r for r in rows if r["recall"] >= recall_min]
    best = (min(ok, key=lambda g: (g["fa_per_cam_h"], -g["recall"], g["theta"])) if ok else
            max(rows, key=lambda g: (g["recall"], -g["fa_per_cam_h"])))
    return {"theta": best["theta"], "min_clock_s": best["clock"], "select_fa_per_cam_h": best["fa_per_cam_h"],
            "select_recall": best["recall"], "feasible": bool(ok)}


def pool(fold_stats: list[list[dict]]) -> list[dict]:
    """Sum grid counts over folds (same grid order in every fold)."""
    out = []
    for rows in zip(*fold_stats):
        r0 = rows[0]
        out.append({"theta": r0["theta"], "clock": r0["clock"],
                    **{k: sum(r[k] for r in rows) for k in ("fa", "cam_h", "tp", "truth")}})
    return out


def choose(policy: str, folds: list[dict], alpha: float = 2.915) -> dict[str, Any]:
    """folds: per-fold {"grid": [...], "peaks": [[...]], "camh": [...]}; a
    single fold for per_fold, the 9 kept folds for pooled policies."""
    if policy == "crc":
        from .conformal_theta import choose_crc
        peaks = [np.asarray(p, float) for f in folds for p in f["peaks"]]
        camh = [c for f in folds for c in f["camh"]]
        c = choose_crc(peaks, camh, alpha)
        return {"theta": c["theta"], "min_clock_s": 5.0, "feasible": c["feasible"], "crc_floor": c["floor"]}
    stats = pool([f["grid"] for f in folds])
    if policy in ("per_fold", "pooled"):
        return pick(stats, SEL_GRID, 0.85)
    if policy == "pooled_floor":
        return pick(stats, FINE_GRID, 0.80)
    raise ValueError(policy)


def draws(policy: str, folds: list[dict], alpha: float = 2.915) -> list[dict]:
    """10 draws: fold i alone (per_fold) or all folds but i (pooled, LOFO)."""
    if policy == "per_fold":
        return [choose(policy, [f], alpha) for f in folds]
    return [choose(policy, folds[:i] + folds[i + 1:], alpha) for i in range(len(folds))]


def spread(x) -> dict[str, float]:
    x = np.asarray(x, float)
    return {"min": float(x.min()), "max": float(x.max()), "range": float(x.max() - x.min()),
            "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0, "mean": float(x.mean())}


def ratio(a: float, b: float) -> float:
    return float("inf") if b == 0 else a / b


def decide(summ: dict[str, dict]) -> dict[str, Any]:
    """Pre-registered: (b) or (c) cuts range and SD >= 2x vs per-fold and has
    recall >= 0.80 in >= 9/10 draws. Shipped policy: smallest range (then SD,
    then modal FA) among policies with >= 9/10 recall-OK draws."""
    base = summ["per_fold"]["fa"]
    ok = {}
    for p in POLICIES:
        s = summ[p]
        s["range_cut"] = ratio(base["range"], s["fa"]["range"])
        s["sd_cut"] = ratio(base["sd"], s["fa"]["sd"])
        s["recall_ok"] = s["recall_ge_080"] >= 9
        ok[p] = s["recall_ok"]
    met = [p for p in ("pooled", "crc") if ok[p] and summ[p]["range_cut"] >= 2 and summ[p]["sd_cut"] >= 2]
    strict = [p for p in ("pooled", "crc") if ok[p] and summ[p]["range_cut"] >= 4]
    cands = [p for p in POLICIES if ok[p]]
    ship = min(cands, key=lambda p: (summ[p]["fa"]["range"], summ[p]["fa"]["sd"], summ[p]["modal"]["fa_per_cam_h"])) \
        if cands else None
    return {"hypothesis_met": bool(met), "met_by": met, "met_quarter_by": strict, "shipped_policy": ship}


# ------------------------------------------------------------------ data

def _le():
    from .operator_queue import _le as f
    return f()


def fold_stats(seed: int) -> dict[str, Any]:
    LE = _le()
    A1 = LE._build(json.loads((LE.R1 / "selection.json").read_text())["shipped"]["rule"])
    split = "train" if seed == 58 else f"train_s{seed}"
    tab, metas = LE.load_split(split)
    sel_w = LE.stratified_fold(metas, seed)
    tsel = LE._sel_table(tab, sel_w)
    msel = [metas[w] for w in sel_w]
    del tab
    p = A1.score(tsel)
    grid = []
    for mc in CLOCKS:
        for th in sorted(set(SEL_GRID) | set(FINE_GRID)):
            d = LE.score_split(LE.alarms_from_score(p, tsel, th, mc), msel, actor_aware=True)["default_tol30"]
            grid.append({"theta": th, "clock": mc, "fa": d["fa"], "cam_h": d["cam_h"], "tp": d["tp"],
                         "truth": d["truth"]})
    elig = (tsel["clock"].to_numpy() >= A1.min_clock_s) & ~tsel["allowed"].to_numpy(bool)
    import pandas as pd
    w = tsel["w"].to_numpy()
    clean = [i for i, m in enumerate(msel) if m["mode"] == "clean"]
    df = pd.DataFrame({"w": w[elig], "ep": tsel["epk"].to_numpy()[elig], "p": p[elig]}).groupby(["w", "ep"])["p"].max()
    peaks: dict[int, list] = {i: [] for i in clean}
    for (wi, _), v in df.items():
        if int(wi) in peaks:
            peaks[int(wi)].append(float(v))
    return {"seed": seed, "n_select_worlds": len(sel_w), "events": grid[0]["truth"], "grid": grid,
            "peaks": [peaks[i] for i in clean], "camh": [msel[i]["camera_hours"] for i in clean]}


def _job(seed):
    return fold_stats(seed)


class H12:
    """A1 scores on the H12 worlds; per-(θ, clock) evaluation with caching."""

    def __init__(self):
        LE = _le()
        self.LE = LE
        A1 = LE._build(json.loads((LE.R1 / "selection.json").read_text())["shipped"]["rule"])
        self.tab, self.metas = LE.load_split("h12")
        self.p = A1.score(self.tab)
        self.cache: dict = {}

    def eval(self, theta: float, clock: float) -> dict[str, Any]:
        key = (round(theta, 12), clock)
        if key not in self.cache:
            from cctvsec.eval import alarms as A
            al = self.LE.alarms_from_score(self.p, self.tab, theta, clock)
            r = self.LE._row(al, self.metas)
            kc, ch = self.LE.clean_counts(al, self.metas)
            tp, ev = [], []
            for w, m in enumerate(self.metas):
                if m["mode"] != "recall":
                    continue
                truth = [A.TruthEvent(e["t_start"], e["t_end"] or e["t_start"], "suspicious.loiter", tuple(e["actors"]))
                         for e in m["truth"]]
                s = A.score(truth, [A.Alarm(t=a[0], label="suspicious.loiter", uid=a[2]) for a in al.get(w, [])],
                            camera_hours=m["camera_hours"], tolerance_s=30, actor_aware=True)
                tp.append(s.true_positives)
                ev.append(s.true_positives + s.false_negatives)
            self.cache[key] = (r, kc, ch, np.array(tp, float), np.array(ev, float))
        return self.cache[key]


def paired(h12: H12, a: tuple, b: tuple, n_boot: int = 2000, seed: int = 42) -> dict[str, Any]:
    _, ka, ch, tpa, ev = h12.eval(*a)
    _, kb, _, tpb, _ = h12.eval(*b)
    fa = h12.LE.paired_world_diff(ka, kb, ch, n_boot=n_boot, seed=seed)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ev), (n_boot, len(ev)))
    d = (tpa[idx].sum(1) - tpb[idx].sum(1)) / ev[idx].sum(1)
    return {"fa_diff": fa["diff"], "fa_boot95": fa["boot95"],
            "recall_diff": float((tpa.sum() - tpb.sum()) / ev.sum()),
            "recall_boot95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor
    out.mkdir(parents=True, exist_ok=True)
    cp = out / "fold_stats.json"
    seeds = tuple(cfg.get("fold_seeds", FOLD_SEEDS))
    if cp.is_file():
        folds = json.loads(cp.read_text())
    else:
        with ProcessPoolExecutor(int(cfg.get("workers", 3))) as ex:
            folds = list(ex.map(_job, seeds))
        cp.write_text(json.dumps(folds))
    alpha = float(cfg["alpha"])
    h12 = H12()
    a1_pt = (0.95, 5.0)
    a1 = h12.eval(*a1_pt)[0]
    body: dict[str, Any] = {"events_per_fold": [f["events"] for f in folds],
                            "pooled_events": int(sum(f["events"] for f in folds)),
                            "A1": {"theta": 0.95, "min_clock_s": 5.0, **a1}, "policies": {}}
    summ = {}
    for pol in POLICIES:
        rows = []
        for s, c in zip(seeds, draws(pol, folds, alpha)):
            r = h12.eval(c["theta"], c["min_clock_s"])[0]
            rows.append({"held_out_fold": s, **c, "fa_per_cam_h": r["fa_per_cam_h"], "garwood95": r["garwood95"],
                         "recall": r["recall"], "recall_boot95": r["recall_boot95"]})
        pts = [(r["theta"], r["min_clock_s"]) for r in rows]
        modal = max(set(pts), key=lambda x: (pts.count(x), -x[0]))
        mr = h12.eval(*modal)[0]
        s = {"theta": spread([r["theta"] for r in rows]), "fa": spread([r["fa_per_cam_h"] for r in rows]),
             "recall": spread([r["recall"] for r in rows]),
             "recall_ge_080": int(sum(r["recall"] >= 0.80 for r in rows)),
             "points": {f"{t:.6g}@{c:g}": pts.count((t, c)) for t, c in sorted(set(pts))},
             "modal": {"theta": modal[0], "min_clock_s": modal[1], "fa_per_cam_h": mr["fa_per_cam_h"],
                       "garwood95": mr["garwood95"], "recall": mr["recall"], "recall_boot95": mr["recall_boot95"],
                       "minus_A1": paired(h12, modal, a1_pt, n_boot=int(cfg.get("n_boot", 2000)))}}
        summ[pol] = s
        body["policies"][pol] = {"draws": rows}
    dec = decide(summ)
    for pol in POLICIES:
        body["policies"][pol]["summary"] = summ[pol]
    body["decision"] = dec
    _fig(body, out)
    return body


def _fig(body: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    cols = ["#4C6EF5", "#12B886", "#F59F00", "#E64980"]
    for i, pol in enumerate(POLICIES):
        d = body["policies"][pol]["draws"]
        x = i + np.linspace(-0.15, 0.15, len(d))
        ax[0].scatter(x, [r["fa_per_cam_h"] for r in d], color=cols[i], s=22)
        ax[1].scatter(x, [r["recall"] for r in d], color=cols[i], s=22)
    for a, lab, ref in ((ax[0], "H12 FA / camera-hour", 2.915), (ax[1], "H12 recall (actor-aware, 30 s)", 0.80)):
        a.axhline(ref, color="grey", ls="--", lw=1)
        a.set_xticks(range(len(POLICIES)), ["per-fold", "pooled\nLOFO", "CRC α=2.915\nLOFO", "pooled+floor\nLOFO"])
        a.set_ylabel(lab)
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("H42: θ-selection policy for frozen A1 — 10 draws each")
    fig.tight_layout()
    fig.savefig(out / "fig_h42.png", dpi=130)
    plt.close(fig)


def markdown_rows(body: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = ["| policy | θ@clock (draws) | H12 FA range [min–max] | FA SD | range cut | recall range | recall ≥ 0.80 |",
         "|---|---|---|---|---|---|---|"]
    for pol in POLICIES:
        s = body["policies"][pol]["summary"]
        pts = ", ".join(f"{k} ×{v}" for k, v in s["points"].items())
        L.append(f"| {pol} | {pts} | {s['fa']['range']:.3f} [{s['fa']['min']:.3f}–{s['fa']['max']:.3f}] | "
                 f"{s['fa']['sd']:.3f} | {s['range_cut']:.3g}× | {s['recall']['min']:.3f}–{s['recall']['max']:.3f} | "
                 f"{s['recall_ge_080']}/10 |")
    d = body["decision"]
    L.append(f"\nDecision: hypothesis met = **{d['hypothesis_met']}** (by {d['met_by']}; ≤ ¼ by {d['met_quarter_by']}); "
             f"shipped policy **{d['shipped_policy']}**.\n")
    return "\n".join(L) + "\n"
