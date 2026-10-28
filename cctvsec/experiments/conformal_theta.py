"""H33: conformal risk control for A1's threshold (docs/research/66 H33,
pre-registered in docs/research/32).

A1 (58 §7.2: frozen round-1 logistic weights, clock >= 5 s) fires once per
dwell episode, at the first eligible tick whose probability reaches θ. So in a
clean world the alarm count at θ is the number of episodes whose *peak*
eligible probability is >= θ, and the whole FA-vs-θ curve of a world is its
sorted list of episode peaks. θ is chosen on a calibration half of the 676
clean H12 worlds, by (a) the plug-in quantile and (b) conformal risk control
(Angelopoulos et al. 2022), and scored on the other half.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .inference import garwood

A1_THETA = 0.95


# ------------------------------------------------------------------ pure core

def counts_at(peaks: list[np.ndarray], theta: np.ndarray, uids: list | None = None,
              cap: int | None = None) -> np.ndarray:
    """k[i, j] = # episodes of world i with peak >= theta[j]. With `cap` (H33c,
    max_alarms_per_uid_per_world) and per-episode `uids`, each visitor counts at
    most `cap` alarms: k = sum_u min(cap, #episodes of u with peak >= θ)."""
    theta = np.atleast_1d(np.asarray(theta, float))
    out = np.empty((len(peaks), len(theta)))
    for i, pk in enumerate(peaks):
        s = np.sort(top_per_uid(pk, uids[i], cap) if cap is not None else np.asarray(pk, float))
        out[i] = len(s) - np.searchsorted(s, theta, side="left")
    return out


def top_per_uid(pk, uids, cap: int) -> np.ndarray:
    """Each uid's `cap` highest peaks: min(cap, #{peaks of u >= θ}) = #{top-cap peaks of u >= θ}."""
    pk = np.asarray(pk, float)
    if len(pk) == 0:
        return pk
    u = np.asarray(uids)
    o = np.lexsort((-pk, u))
    us = u[o]
    start = np.r_[True, us[1:] != us[:-1]]
    rank = np.arange(len(o)) - np.maximum.accumulate(np.where(start, np.arange(len(o)), 0))
    return pk[o][rank < cap]


def candidates(peaks: list[np.ndarray]) -> np.ndarray:
    """Every θ at which some calibration world's count changes, plus 1.0
    (never alarms unless p == 1)."""
    allp = np.concatenate([np.asarray(p, float) for p in peaks] + [np.array([1.0])])
    return np.unique(allp)


def choose_plain(peaks, camh, alpha: float, uids=None, cap=None) -> float:
    """Smallest θ with pooled calibration FA/cam-h <= alpha."""
    th = candidates(peaks)
    fa = counts_at(peaks, th, uids, cap).sum(0) / float(np.sum(camh))
    ok = np.flatnonzero(fa <= alpha)
    return float(th[ok[0]]) if len(ok) else float(np.nextafter(1.0, 2.0))


def fixed_B(spec: dict[str, Any]) -> float:
    """H33b: a per-world FA/cam-h bound fixed *before* calibration, from the
    world generator alone: A1 fires at most once per dwell episode and (stated
    cap) at most once per arriving visitor, so k_i <= arrivals_i. Arrivals are
    Poisson(rate_max * duration); take its 1 - tail quantile and divide by the
    smallest camera-hours a world can have. Losses above B are clipped (and
    counted), so the guarantee is exact for min(L, B).

    AUDIT_H33B: the per-visitor cap is an assumption, not enforced — A1 alarms once
    per dwell *episode* and one visitor can open several (up to 21 in H12), so B is
    not an a-priori bound on L itself; only min(L, B) is controlled exactly."""
    from scipy.stats import poisson
    lam = float(spec["arrivals_per_min_max"]) * float(spec["duration_s"]) / 60.0
    return float(poisson.ppf(1.0 - float(spec["tail"]), lam)) / float(spec["min_camera_hours"])


def choose_crc(peaks, camh, alpha: float, B: float | None = None, mode: str = "empirical",
               uids=None, cap=None) -> dict[str, Any]:
    """Conformal risk control on per-world loss L_i(θ) = k_i(θ)/camh_i
    (monotone non-increasing in θ): smallest θ with
    n/(n+1) mean L + B/(n+1) <= alpha. Infeasible -> θ just above 1 (never alarm).

    mode="empirical" (H33/H42/H45, kept for reproducibility): B defaults to the
    largest calibration loss at the lowest candidate — data-derived, so the CRC
    guarantee is only *approximate*. mode="real": B is required and must be
    fixed in advance (see fixed_B); L is clipped at B, making the guarantee
    exact for min(L, B) (Angelopoulos et al. 2022 need L <= B known a priori)."""
    camh = np.asarray(camh, float)
    th = candidates(peaks)
    L = counts_at(peaks, th, uids, cap) / camh[:, None]
    n = len(camh)
    n_clipped = 0
    if mode == "real":
        if B is None:
            raise ValueError("mode='real' needs B fixed before seeing calibration data")
        n_clipped = int((L[:, 0] > B).sum())
        L = np.minimum(L, B)
    elif mode != "empirical":
        raise ValueError(mode)
    elif B is None:
        B = float(L[:, 0].max())
    r = n / (n + 1) * L.mean(0) + B / (n + 1)
    ok = np.flatnonzero(r <= alpha)
    feasible = bool(len(ok))
    return {"theta": float(th[ok[0]]) if feasible else float(np.nextafter(1.0, 2.0)),
            "B": float(B), "floor": float(B) / (n + 1), "feasible": feasible, "mode": mode,
            "n_clipped": n_clipped}


def heldout_fa(peaks, camh, theta: float, n_boot: int = 2000, seed: int = 33,
               uids=None, cap=None) -> dict[str, Any]:
    k = counts_at(peaks, [theta], uids, cap)[:, 0]
    camh = np.asarray(camh, float)
    lo, hi = garwood(int(k.sum()), float(camh.sum()))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(k), (n_boot, len(k)))
    b = k[idx].sum(1) / camh[idx].sum(1)
    return {"fa": int(k.sum()), "cam_h": float(camh.sum()), "fa_per_cam_h": float(k.sum() / camh.sum()),
            "per_world_mean": float((k / camh).mean()), "garwood95": [lo, hi],
            "boot95": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]}


def decide(crc_exceed: int, plain_exceed: int) -> str:
    if crc_exceed >= 3:
        return "refuted"
    if crc_exceed <= 1 and plain_exceed >= 3:
        return "supported"
    return "inconclusive"


# ------------------------------------------------------------------ data

def build(cfg: dict[str, Any]) -> dict[str, Any]:
    """Per clean world: episode peak A1 probabilities over eligible ticks;
    per recall world: eligible ticks (w, epk, t, uid, p) for recall at any θ."""
    from .operator_queue import _le
    LE = _le()
    A1 = LE._build(json.loads((LE.R1 / "selection.json").read_text())["shipped"]["rule"])
    tab, metas = LE.load_split("h12")
    p = A1.score(tab)
    elig = (tab["clock"].to_numpy() >= A1.min_clock_s) & ~tab["allowed"].to_numpy(bool)
    w = tab["w"].to_numpy()
    ep = tab["epk"].to_numpy()
    clean_ws = [i for i, m in enumerate(metas) if m["mode"] == "clean"]
    peaks: dict[int, list] = {i: [] for i in clean_ws}
    puid: dict[int, list] = {i: [] for i in clean_ws}
    sel = elig & np.isin(w, clean_ws)
    import pandas as pd
    g = pd.DataFrame({"w": w[sel], "ep": ep[sel], "p": p[sel],
                      "u": tab["uid"].astype(str).to_numpy()[sel]}).groupby(["w", "ep"])
    df, du = g["p"].max(), g["u"].first()
    for (wi, e), v in df.items():
        peaks[int(wi)].append(float(v))
        puid[int(wi)].append(str(du[(wi, e)]))
    nvis = tab[np.isin(w, clean_ws)].groupby("w", observed=True)["uid"].nunique()
    rsel = elig & ~np.isin(w, clean_ws)
    rec = {"w": w[rsel].tolist(), "ep": ep[rsel].tolist(), "t": tab["t"].to_numpy()[rsel].tolist(),
           "uid": tab["uid"].astype(str).to_numpy()[rsel].tolist(), "p": p[rsel].tolist()}
    return {"a1_min_clock_s": A1.min_clock_s, "a1_theta": A1.theta,
            "clean": [{"w": i, "camh": metas[i]["camera_hours"], "peaks": peaks[i], "uids": puid[i],
                       "n_visitors": int(nvis.get(i, 0))} for i in clean_ws],
            "recall_ticks": rec,
            "recall_metas": {str(i): m for i, m in enumerate(metas) if m["mode"] == "recall"}}


def recall_at(data: dict, theta: float, cache: dict, cap: int | None = None) -> dict[str, Any]:
    key = f"{theta:.12g}" + ("" if cap is None else f"/cap{cap}")
    if key in cache:
        return cache[key]
    from .operator_queue import _le
    LE = _le()
    r = data["recall_ticks"]
    p = np.asarray(r["p"])
    m = p >= theta
    seen: set = set()
    ws = sorted(int(k) for k in data["recall_metas"])
    remap = {w: j for j, w in enumerate(ws)}
    alarms: dict[int, list] = {}
    for wi, e, t, u in zip(np.asarray(r["w"])[m], np.asarray(r["ep"])[m], np.asarray(r["t"])[m],
                           np.asarray(r["uid"])[m]):
        if e in seen:
            continue
        seen.add(e)
        alarms.setdefault(remap[int(wi)], []).append((float(t), "", str(u)))
    metas = [data["recall_metas"][str(w)] for w in ws]
    alarms = LE.cap_per_uid(alarms, cap)
    sc = LE.score_split(alarms, metas, seed=33, actor_aware=True)
    d = sc["default_tol30"]
    cache[key] = {"recall": d["recall"], "recall_boot95": d["recall_boot95"]}
    if cap is not None or data.get("_h33c"):
        il = sc["ilids_compat_tol30"]
        cache[key] |= {"tp": d["tp"], "truth": d["truth"], "median_latency_s": d["median_latency_s"],
                       "ilids_recall": il["recall"], "n_alarms": sum(len(v) for v in alarms.values())}
    return cache[key]


def _seed_ci(x, n_boot=10000, seed=33):
    x = np.asarray(x, float)
    m = x[np.random.default_rng(seed).integers(0, len(x), (n_boot, len(x)))].mean(1)
    return {"mean": float(x.mean()), "boot95": [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    if cfg.get("caps"):
        return run_h33c(cfg, out)
    cache_p = out / "data.json"
    if cache_p.is_file():
        data = json.loads(cache_p.read_text())
    else:
        data = build(cfg)
        cache_p.write_text(json.dumps(data))
    clean = data["clean"]
    peaks = [np.asarray(c["peaks"]) for c in clean]
    camh = np.array([c["camh"] for c in clean])
    rcache: dict = {}
    full = heldout_fa(peaks, camh, A1_THETA)
    cells: dict[str, Any] = {}
    Bfix = fixed_B(cfg["fixed_B"]) if cfg.get("fixed_B") else None
    arms = ("grid", "plain", "crc") + (("crc_fixed",) if Bfix is not None else ())
    for alpha in cfg["alphas"]:
        rows = []
        for s in cfg["split_seeds"]:
            perm = np.random.default_rng([33, s]).permutation(len(clean))
            nc = round(cfg["calib_frac"] * len(clean))
            ci, ti = perm[:nc], perm[nc:]
            pc, pt = [peaks[i] for i in ci], [peaks[i] for i in ti]
            crc = choose_crc(pc, camh[ci], alpha)
            thetas = {"grid": A1_THETA, "plain": choose_plain(pc, camh[ci], alpha), "crc": crc["theta"]}
            row = {"seed": s, "crc_B": crc["B"], "crc_floor": crc["floor"], "crc_feasible": crc["feasible"]}
            if Bfix is not None:
                cf = choose_crc(pc, camh[ci], alpha, B=Bfix, mode="real")
                thetas["crc_fixed"] = cf["theta"]
                row |= {"crc_fixed_feasible": cf["feasible"], "crc_fixed_clipped": cf["n_clipped"]}
            for arm, th in thetas.items():
                tf = heldout_fa(pt, camh[ti], th)
                row[arm] = {"theta": th, **tf, "exceed": tf["fa_per_cam_h"] > alpha,
                            **recall_at(data, th, rcache)}
            rows.append(row)
        summ = {}
        for arm in arms:
            summ[arm] = {"exceed": int(sum(r[arm]["exceed"] for r in rows)),
                         "heldout_fa": _seed_ci([r[arm]["fa_per_cam_h"] for r in rows]),
                         "recall": _seed_ci([r[arm]["recall"] for r in rows]),
                         "theta_range": [min(r[arm]["theta"] for r in rows), max(r[arm]["theta"] for r in rows)]}
        summ["recall_cost_crc_minus_plain"] = _seed_ci([r["crc"]["recall"] - r["plain"]["recall"] for r in rows])
        summ["decision"] = decide(summ["crc"]["exceed"], summ["plain"]["exceed"])
        if Bfix is not None:
            summ["recall_cost_fixed_minus_empirical"] = _seed_ci(
                [r["crc_fixed"]["recall"] - r["crc"]["recall"] for r in rows])
            summ["h33b"] = decide_h33b(summ["crc_fixed"]["exceed"], summ["recall_cost_fixed_minus_empirical"]["mean"],
                                      all(r["crc_fixed"]["theta"] >= r["crc"]["theta"] for r in rows))
        cells[str(alpha)] = {"summary": summ, "seeds": rows}
    res = {"a1_full_h12": full, "cells": cells}
    if Bfix is not None:
        res["fixed_B"] = {"B": Bfix, "spec": cfg["fixed_B"], "floor_n338": Bfix / 339}
        if cfg.get("figure"):
            figure(res, Path(cfg["figure"]))
    return res


def decide_h33b(exceed: int, cost_mean: float, more_conservative: bool) -> str:
    """H33b: supported iff fixed-B θ >= empirical-B θ on every split, fixed-B
    exceeds α on 0/10 splits and mean recall cost vs empirical B <= 0.02."""
    if exceed >= 1:
        return "refuted"
    return "supported" if more_conservative and cost_mean >= -0.02 else "partial"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    al = [a for a in res["cells"] if "crc_fixed" in res["cells"][a]["summary"]]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for arm, c in (("plain", "#999999"), ("crc", "#1f77b4"), ("crc_fixed", "#d62728")):
        fa = [res["cells"][a]["summary"][arm]["heldout_fa"]["mean"] for a in al]
        rc = [res["cells"][a]["summary"][arm]["recall"]["mean"] for a in al]
        lab = {"plain": "plug-in", "crc": "CRC, empirical B", "crc_fixed": f"CRC, fixed B={res['fixed_B']['B']:g}"}[arm]
        ax[0].plot([float(a) for a in al], fa, "o-", color=c, label=lab)
        ax[1].plot(fa, rc, "o-", color=c, label=lab)
    xs = [float(a) for a in al]
    ax[0].plot(xs, xs, "k--", lw=0.8, label="target α")
    ax[0].set_xlabel("target α (FA/cam-h)"); ax[0].set_ylabel("held-out FA/cam-h (mean of 10 splits)")
    ax[1].set_xlabel("held-out FA/cam-h"); ax[1].set_ylabel("recall (actor-aware, 30 s)")
    ax[0].legend(fontsize=7); ax[0].set_title("H33b: FA vs target"); ax[1].set_title("recall vs FA")
    fig.tight_layout(); path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=130); plt.close(fig)


def markdown_rows(body: dict[str, Any], cfg: dict[str, Any]) -> str:
    if cfg.get("caps"):
        return markdown_h33c(body)
    L = ["| α | arm | θ range | exceed /10 | test FA/cam-h mean [seed 95 %] | recall mean [95 %] |",
         "|---|---|---|---|---|---|"]
    for a, c in body["cells"].items():
        s = c["summary"]
        for arm in [k for k in ("grid", "plain", "crc", "crc_fixed") if k in s]:
            x = s[arm]
            L.append(f"| {a} | {arm} | {x['theta_range'][0]:.4f}–{x['theta_range'][1]:.4f} | {x['exceed']} | "
                     f"{x['heldout_fa']['mean']:.3f} [{x['heldout_fa']['boot95'][0]:.3f}, {x['heldout_fa']['boot95'][1]:.3f}] | "
                     f"{x['recall']['mean']:.3f} [{x['recall']['boot95'][0]:.3f}, {x['recall']['boot95'][1]:.3f}] |")
        rc = s["recall_cost_crc_minus_plain"]
        L.append(f"| {a} | crc − plain recall | | decision **{s['decision']}** | | "
                 f"{rc['mean']:+.3f} [{rc['boot95'][0]:+.3f}, {rc['boot95'][1]:+.3f}] |")
        if "h33b" in s:
            rf = s["recall_cost_fixed_minus_empirical"]
            L.append(f"| {a} | crc_fixed − crc recall | | H33b **{s['h33b']}** | | "
                     f"{rf['mean']:+.3f} [{rf['boot95'][0]:+.3f}, {rf['boot95'][1]:+.3f}] |")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ H33c: per-visitor cap

def decide_h33c(fa_cut: float, cost_mean: float, exceed: int, clipped: int) -> str:
    """H33c (32 §H33c): supported iff equal-θ FA cut >= 20 %, recall cost <= 0.02,
    0/10 exceed and no calibration world clipped; refuted if any exceed or cost > 0.05."""
    if exceed >= 1 or cost_mean < -0.05:
        return "refuted"
    return "supported" if fa_cut >= 0.20 and cost_mean >= -0.02 and clipped == 0 else "partial"


def run_h33c(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    cache_p = out / "data.json"
    if cache_p.is_file():
        data = json.loads(cache_p.read_text())
    else:
        data = build(cfg)
        cache_p.write_text(json.dumps(data))
    data["_h33c"] = True
    clean = data["clean"]
    peaks = [np.asarray(c["peaks"]) for c in clean]
    uids = [c["uids"] for c in clean]
    camh = np.array([c["camh"] for c in clean])
    B1 = fixed_B(cfg["fixed_B"])
    arms = {name: {"cap": a.get("cap"), "B": B1 * float(a.get("B_mult", 1.0)),
                   "B_valid": bool(a.get("B_valid", False))} for name, a in cfg["caps"].items()}
    ref = cfg.get("reference_arm", "uncapped")
    rc: dict = {}
    # episode structure (clean): episodes per visitor, max alarms/world under each cap at θ = 0
    epv = [np.unique(u, return_counts=True)[1] for u in uids if len(u)]
    allc = np.concatenate(epv) if epv else np.array([0])
    struct = {"max_episodes_per_visitor": int(allc.max()),
              "share_eligible_episodes_from_multi_episode_visitors": float(allc[allc > 1].sum() / allc.sum()),
              "max_visitors_per_world": int(max(c["n_visitors"] for c in clean)),
              "B_visitors": float(B1 * cfg["fixed_B"]["min_camera_hours"]),
              "max_L_at_theta0": {n: float((counts_at(peaks, [0.0], uids, a["cap"])[:, 0] / camh).max())
                                  for n, a in arms.items()}}
    cells: dict[str, Any] = {}
    for alpha in cfg["alphas"]:
        rows = []
        for s in cfg["split_seeds"]:
            perm = np.random.default_rng([33, s]).permutation(len(clean))
            nc = round(cfg["calib_frac"] * len(clean))
            ci, ti = perm[:nc], perm[nc:]
            pc, pt = [peaks[i] for i in ci], [peaks[i] for i in ti]
            uc, ut = [uids[i] for i in ci], [uids[i] for i in ti]
            row: dict[str, Any] = {"seed": s}
            for name, a in arms.items():
                cf = choose_crc(pc, camh[ci], alpha, B=a["B"], mode="real", uids=uc, cap=a["cap"])
                th = cf["theta"]
                tf = heldout_fa(pt, camh[ti], th, uids=ut, cap=a["cap"])
                row[name] = {"theta": th, "feasible": cf["feasible"], "clipped": cf["n_clipped"], **tf,
                             "exceed": tf["fa_per_cam_h"] > alpha,
                             "per_world_mean_exceed": tf["per_world_mean"] > alpha,
                             **recall_at(data, th, rc, cap=a["cap"])}
            th_ref = row[ref]["theta"]
            row["equal_theta"] = {}
            for name, a in arms.items():   # cap only, at the reference arm's θ
                tf = heldout_fa(pt, camh[ti], th_ref, uids=ut, cap=a["cap"])
                r = recall_at(data, th_ref, rc, cap=a["cap"])
                row["equal_theta"][name] = {"fa_per_cam_h": tf["fa_per_cam_h"], "recall": r["recall"],
                                            "tp": r["tp"], "ilids_recall": r["ilids_recall"],
                                            "median_latency_s": r["median_latency_s"]}
            rows.append(row)
        summ: dict[str, Any] = {}
        for name in arms:
            summ[name] = {"exceed": int(sum(r[name]["exceed"] for r in rows)),
                          "per_world_mean_exceed": int(sum(r[name]["per_world_mean_exceed"] for r in rows)),
                          "clipped_total": int(sum(r[name]["clipped"] for r in rows)),
                          "heldout_fa": _seed_ci([r[name]["fa_per_cam_h"] for r in rows]),
                          "recall": _seed_ci([r[name]["recall"] for r in rows]),
                          "ilids_recall": _seed_ci([r[name]["ilids_recall"] for r in rows]),
                          "median_latency_s": _seed_ci([r[name]["median_latency_s"] for r in rows]),
                          "theta_range": [min(r[name]["theta"] for r in rows), max(r[name]["theta"] for r in rows)],
                          "theta_median": float(np.median([r[name]["theta"] for r in rows]))}
            if name != ref:
                summ[name]["recall_cost_vs_ref"] = _seed_ci([r[name]["recall"] - r[ref]["recall"] for r in rows])
                summ[name]["fa_cut_equal_theta"] = _seed_ci(
                    [1 - r["equal_theta"][name]["fa_per_cam_h"] / r["equal_theta"][ref]["fa_per_cam_h"] for r in rows])
                summ[name]["tp_dropped_equal_theta"] = _seed_ci(
                    [r["equal_theta"][ref]["tp"] - r["equal_theta"][name]["tp"] for r in rows])
                summ[name]["latency_delta_equal_theta"] = _seed_ci(
                    [r["equal_theta"][name]["median_latency_s"] - r["equal_theta"][ref]["median_latency_s"]
                     for r in rows])
                summ[name]["decision"] = decide_h33c(summ[name]["fa_cut_equal_theta"]["mean"],
                                                     summ[name]["recall_cost_vs_ref"]["mean"],
                                                     summ[name]["exceed"], summ[name]["clipped_total"])
        cells[str(alpha)] = {"summary": summ, "seeds": rows}
    # full-H12 numbers at each arm's median θ (the certified points)
    a0 = str(cfg.get("primary_alpha", cfg["alphas"][-1]))
    points = {}
    for name, a in arms.items():
        th = cells[a0]["summary"][name]["theta_median"]
        points[name] = {"theta": th, **heldout_fa(peaks, camh, th, uids=uids, cap=a["cap"]),
                        **recall_at(data, th, rc, cap=a["cap"])}
    res = {"arms": arms, "structure": struct, "cells": cells, "points_full_h12": points}
    if cfg.get("figure"):
        figure_h33c(res, Path(cfg["figure"]))
    return res


def figure_h33c(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    al = list(res["cells"])
    cols = {"uncapped": "#1f77b4", "capped1": "#d62728", "capped2": "#2ca02c"}
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for name in res["arms"]:
        fa = [res["cells"][a]["summary"][name]["heldout_fa"]["mean"] for a in al]
        rcl = [res["cells"][a]["summary"][name]["recall"]["mean"] for a in al]
        lab = f"{name} (B={res['arms'][name]['B']:g}{'' if res['arms'][name]['B_valid'] else ', not a bound'})"
        ax[0].plot([float(a) for a in al], fa, "o-", color=cols.get(name), label=lab)
        ax[1].plot(fa, rcl, "o-", color=cols.get(name), label=lab)
    xs = [float(a) for a in al]
    ax[0].plot(xs, xs, "k--", lw=0.8, label="target α")
    ax[0].set_xlabel("target α (FA/cam-h)"); ax[0].set_ylabel("held-out FA/cam-h (mean of 10 splits)")
    ax[1].set_xlabel("held-out FA/cam-h"); ax[1].set_ylabel("recall (actor-aware, 30 s)")
    ax[0].legend(fontsize=7); ax[0].set_title("H33c: CRC θ, fixed B, per-visitor cap"); ax[1].set_title("recall vs FA")
    fig.tight_layout(); path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=130); plt.close(fig)


def markdown_h33c(res: dict[str, Any]) -> str:
    L = ["| α | arm | B | θ range | exceed /10 | clipped | test FA/cam-h [seed 95 %] | recall [95 %] | i-LIDS recall |",
         "|---|---|---|---|---|---|---|---|---|"]
    for a, c in res["cells"].items():
        for name, x in c["summary"].items():
            L.append(f"| {a} | {name} | {res['arms'][name]['B']:g} | {x['theta_range'][0]:.4f}–{x['theta_range'][1]:.4f} | "
                     f"{x['exceed']} | {x['clipped_total']} | {x['heldout_fa']['mean']:.3f} "
                     f"[{x['heldout_fa']['boot95'][0]:.3f}, {x['heldout_fa']['boot95'][1]:.3f}] | "
                     f"{x['recall']['mean']:.3f} [{x['recall']['boot95'][0]:.3f}, {x['recall']['boot95'][1]:.3f}] | "
                     f"{x['ilids_recall']['mean']:.3f} |")
    return "\n".join(L) + "\n"
