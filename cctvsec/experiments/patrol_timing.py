"""H64: PTZ-tour timing exploitation vs. randomised tours (docs/research/100 T8; pre-registered in 32).

One fence of P segments watched only by one PTZ with one preset per segment. A naive intruder crosses
whenever it arrives; a timed intruder watches N departures of the dome from its segment and crosses 1 s
after the last. Hard negative: the timed intruder's recon is a long dwell at the approach, which an innocent
commuter wait also is; a dwell rule is calibrated on separate innocent-only worlds and frozen.
Every rate is a declared assumption.

    survsim experiment h64_patrol_timing
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

TOURS = ("fixed", "random")


def tour(kind: str, rng, w: dict) -> list[tuple[int, float, float]]:
    """Stationary intervals (preset, t0, t1) over [0, horizon]."""
    P, slew, horizon = int(w["presets"]), float(w["slew_s"]), float(w["horizon_s"])
    out: list[tuple[int, float, float]] = []
    if kind == "fixed":
        d, per = float(w["dwell_s"]), P * (float(w["dwell_s"]) + slew)
        t = -float(rng.uniform(0, per))
        p = 0
        while t < horizon:
            out.append((p, t, t + d))
            t += d + slew
            p = (p + 1) % P
    else:
        p, t = int(rng.integers(P)), 0.0
        while t < horizon:
            d = float(rng.uniform(*w["random_dwell_s"]))
            out.append((p, t, t + d))
            t += d + slew
            p = int((p + 1 + rng.integers(P - 1)) % P)      # uniform over the other P-1
    return out


def caught(iv, seg: int, s: float, c: float, min_ov: float) -> bool:
    return any(p == seg and min(t1, s + c) - max(t0, s) >= min_ov for p, t0, t1 in iv)


def timed_start(iv, seg: int, t_a: float, n: int) -> float:
    deps = [t1 for p, _, t1 in iv if p == seg and t1 > t_a]
    return deps[n - 1] + 1.0


def world(block: int, i: int, cfg: dict) -> dict[str, Any]:
    w = cfg["world"]
    rng = np.random.default_rng([int(cfg["seed"]), block, i])
    seg = int(rng.integers(w["presets"]))
    t_a = float(rng.uniform(*w["arrive_s"]))
    c = float(rng.uniform(*w["cross_s"]))
    s_naive = t_a + float(rng.uniform(*w["naive_delay_s"]))
    u_det = float(rng.random())
    vis = bool(rng.random() < w["p_vis"])
    det = u_det < w["p_det"]
    m: dict[str, Any] = {"vis": vis}
    for kind in TOURS:
        iv = tour(kind, np.random.default_rng([int(cfg["seed"]), block, i, 1 + TOURS.index(kind)]), w)
        m[f"{kind}/naive"] = float(det and caught(iv, seg, s_naive, c, w["min_overlap_s"]))
        for n in cfg["n_sweep"]:
            s = timed_start(iv, seg, t_a, n)
            m[f"{kind}/timed{n}"] = float(det and caught(iv, seg, s, c, w["min_overlap_s"]))
            m[f"{kind}/dwell{n}"] = s - t_a + c
    return m


def innocent_dwells(block: int, i: int, cfg: dict) -> np.ndarray:
    h = cfg["hard_negative"]
    rng = np.random.default_rng([int(cfg["seed"]), block, i, 77])
    n = rng.poisson(h["rate_per_h"] * cfg["world"]["duration_s"] / 3600.0)
    return h["median_s"] * np.exp(h["sigma"] * rng.standard_normal(n))


def calibrate_tau(cfg: dict) -> float:
    blk = int(cfg["calibration_block"])
    d = np.sort(np.concatenate([innocent_dwells(blk, i, cfg) for i in range(int(cfg["n_calibration"]))]))
    cam_h = int(cfg["n_calibration"]) * cfg["world"]["duration_s"] / 3600.0
    budget = cfg["hard_negative"]["fa_per_cam_h"]
    for tau in d:                                           # smallest observed value meeting the budget
        if np.sum(d >= tau) / cam_h <= budget:
            return float(tau)
    return float(d[-1] + 1)


def _block_job(args):
    b, cfg = args
    tau = cfg["_tau"]
    rows = []
    for i in range(int(cfg["worlds_per_block"])):
        m = world(b, i, cfg)
        for n in cfg["n_sweep"]:
            for kind in TOURS:
                m[f"{kind}/recon{n}"] = float(m["vis"] and m[f"{kind}/dwell{n}"] >= tau)
        m["fa"] = float(np.sum(innocent_dwells(b, i, cfg) >= tau))
        m["block"] = b
        rows.append(m)
    return rows


def _holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    adj, run = {}, 0.0
    for r, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - r) * p))
        adj[k] = run
    return adj


def summarise(rows: list[dict], cfg: dict) -> dict[str, Any]:
    n, nb = len(rows), int(cfg["n_boot"])
    bi = np.random.default_rng(int(cfg["seed"]) + 1).integers(0, n, (nb, n))
    N = int(cfg["n_primary"])

    def col(k):
        return np.array([r[k] for r in rows], float)

    def st(v):
        b = v[bi].mean(1)
        return {"mean": float(v.mean()), "boot95": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]}, b

    res: dict[str, Any] = {"n_worlds": n, "tau_s": cfg["_tau"], "catch": {}, "recon": {}}
    for kind in TOURS:
        res["catch"][f"{kind}/naive"] = st(col(f"{kind}/naive"))[0]
        for m in cfg["n_sweep"]:
            res["catch"][f"{kind}/timed{m}"] = st(col(f"{kind}/timed{m}"))[0]
            res["recon"][f"{kind}/N{m}"] = st(col(f"{kind}/recon{m}"))[0]
            res["recon"][f"{kind}/N{m}"]["median_dwell_s"] = float(np.median(col(f"{kind}/dwell{m}")))
    ef = col("fixed/naive") - col(f"fixed/timed{N}")
    er = col("random/naive") - col(f"random/timed{N}")
    s_ef, b_ef = st(ef)
    s_er, _b_er = st(er)
    s_d, b_d = st(er - 0.5 * ef)
    s_rr, b_rr = st(col(f"fixed/recon{N}"))
    p = {"T1": float((np.sum(b_ef <= 0.10) + 1) / (nb + 1)),
         "T2": float((np.sum(b_d >= 0) + 1) / (nb + 1)),
         "T3": float((np.sum(b_rr <= 0.5) + 1) / (nb + 1))}
    ph = _holm(p)
    fa, _b_fa = st(col("fa"))                                  # 1 approach camera, 1 h -> per cam-h
    res.update(E_fixed=s_ef, E_random=s_er, E_random_minus_half_E_fixed=s_d, recon_recall_primary=s_rr,
               innocent_fa_per_cam_h=fa, p_one_sided=p, p_holm=ph)
    blocks = sorted({r["block"] for r in rows})
    res["per_block"] = {
        "E_fixed": [float(np.mean([r["fixed/naive"] - r[f"fixed/timed{N}"] for r in rows if r["block"] == b]))
                    for b in blocks],
        "E_random": [float(np.mean([r["random/naive"] - r[f"random/timed{N}"] for r in rows if r["block"] == b]))
                     for b in blocks]}
    res["abandon"] = res["catch"]["fixed/naive"]["mean"] < 0.10
    d = {"T1": ph["T1"] < 0.05, "T2": ph["T2"] < 0.05, "T3": ph["T3"] < 0.05, "fa": fa["mean"] <= 0.6}
    d["met"] = all(d.values())
    res["decision"] = {k: bool(v) for k, v in d.items()}
    return res


def figure(res: dict, cfg: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ns = cfg["n_sweep"]
    col = {"fixed": "#3a6ea5", "random": "#c7792b"}
    for kind in TOURS:
        nv = res["catch"][f"{kind}/naive"]
        ax[0].axhline(nv["mean"], color=col[kind], ls=":", lw=1, label=f"{kind} tour, naive")
        m = np.array([res["catch"][f"{kind}/timed{k}"]["mean"] for k in ns])
        lo = np.array([res["catch"][f"{kind}/timed{k}"]["boot95"][0] for k in ns])
        hi = np.array([res["catch"][f"{kind}/timed{k}"]["boot95"][1] for k in ns])
        ax[0].errorbar(ns, m, yerr=[m - lo, hi - m], marker="o", capsize=3, color=col[kind],
                       label=f"{kind} tour, timed")
        r = [res["recon"][f"{kind}/N{k}"]["mean"] for k in ns]
        ax[1].plot(ns, r, marker="o", color=col[kind], label=f"{kind} tour")
    ax[0].set_xlabel("PTZ departures watched before crossing (N)")
    ax[0].set_ylabel("P(intruder caught)")
    ax[0].legend(fontsize=7)
    ax[1].axhline(0.5, ls=":", c="k", lw=0.8)
    ax[1].set_xlabel("N")
    ax[1].set_ylabel(f"recon flagged (dwell >= {res['tau_s']:.0f} s)")
    ax[1].set_title(f"innocent FA {res['innocent_fa_per_cam_h']['mean']:.2f} /cam-h", fontsize=8)
    ax[1].set_ylim(0, 1)
    ax[1].legend(fontsize=7)
    fig.suptitle("H64: PTZ-tour timing exploitation (simulated, 6-preset fence)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor
    cfg = dict(cfg, _tau=calibrate_tau(cfg))
    with ProcessPoolExecutor(int(cfg["workers"])) as ex:
        rows = [r for blk in ex.map(_block_job, [(b, cfg) for b in range(int(cfg["n_blocks"]))]) for r in blk]
    res = summarise(rows, cfg)
    res["config"] = cfg
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    fig = Path(cfg.get("figure", out / "fig_h64.png"))
    fig.parent.mkdir(parents=True, exist_ok=True)
    figure(res, cfg, fig)
    return res


def markdown_rows(res: dict, cfg: dict) -> str:
    rows = ["| tour | naive | " + " | ".join(f"timed N={n}" for n in cfg["n_sweep"]) + " |",
            "|---|---|" + "---|" * len(cfg["n_sweep"])]
    for kind in TOURS:
        f = [res["catch"][f"{kind}/naive"]] + [res["catch"][f"{kind}/timed{n}"] for n in cfg["n_sweep"]]
        rows.append(f"| {kind} | " + " | ".join(
            f"{r['mean']:.3f} [{r['boot95'][0]:.3f}, {r['boot95'][1]:.3f}]" for r in f) + " |")
    return "\n".join(rows) + f"\n\ndecision: {res['decision']}\n"
