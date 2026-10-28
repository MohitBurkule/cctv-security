"""H70b: per-site drift monitoring done fairly (pre-registered in docs/research/32 §H70b).

Every monitor is per site (AUDIT_H70 §4: H70's pooled-vs-per-site contrast was monitor granularity). Compares
the daily Poisson count check under pooled-theta vs per-site-theta baselines, and a CUSUM on hourly counts,
across drift sizes; the diurnal pattern (2x day/night, same mean) is the hard negative. Analytic daily-check
power is reported next to the simulation. Simulated; every rate is a declared assumption.

    survsim experiment h70b_drift_monitor_scale
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import optimize, stats

H = 168


def site_rates(delta: np.ndarray, cfg: dict) -> dict[str, np.ndarray]:
    """Expected alarms/h per site under the two theta schemes."""
    C, cand, mu, B = cfg["cams_per_site"], cfg["cand_per_cam_h"], cfg["bg_mu"], cfg["budget"]
    f = lambda th: float(np.mean(cand * stats.norm.sf(th, mu + delta, cfg["bg_sd"]))) - B
    th = optimize.brentq(f, -10, 10)
    return {"pooled": C * cand * stats.norm.sf(th, mu + delta, cfg["bg_sd"]),
            "per_site": np.full(delta.shape, C * B)}


def diurnal(cfg: dict) -> np.ndarray:
    hod = np.arange(H) % 24
    lo, hi = cfg["day_hours"]
    r = float(cfg["day_night_ratio"])
    day = (hod >= lo) & (hod < hi)
    m = np.where(day, r, 1.0)
    return m / m.mean()


def daily_crit(lam_day: np.ndarray, p: float) -> np.ndarray:
    """Smallest count c with P(Poisson(lam_day) >= c) < p."""
    return stats.poisson.isf(p, lam_day) + 1


def daily_flags(x: np.ndarray, lam: np.ndarray, p: float) -> np.ndarray:
    """x (S, H) hourly counts, lam (S,) baseline/h -> bool (S, H) flag at the last hour of each day."""
    S = x.shape[0]
    d = x.reshape(S, -1, 24).sum(2)
    fl = d >= daily_crit(24 * lam, p)[:, None]
    out = np.zeros_like(x, dtype=bool)
    out[:, 23::24] = fl
    return out


def cusum_k(lam: np.ndarray, shift: float) -> np.ndarray:
    return lam * (shift - 1) / np.log(shift)


def cusum_flags(x: np.ndarray, k: np.ndarray, h: np.ndarray) -> np.ndarray:
    """x (S, T), k (S, T) or (S, 1), h (S,): flags with reset."""
    S, T = x.shape
    k = np.broadcast_to(k, (S, T))
    s = np.zeros(S)
    out = np.zeros((S, T), dtype=bool)
    for t in range(T):
        s = np.maximum(0.0, s + x[:, t] - k[:, t])
        f = s > h
        out[:, t] = f
        s[f] = 0.0
    return out


def cusum_h(lam_t: np.ndarray, k: np.ndarray, n: int, week_fa: float, rng) -> np.ndarray:
    """Per-site h so P(any flag in a null week at baseline lam_t (S, H)) = week_fa."""
    S = lam_t.shape[0]
    k = np.broadcast_to(k, (S, H))
    x = rng.poisson(np.broadcast_to(lam_t[:, None, :], (S, n, H)))
    s = np.zeros((S, n))
    mx = np.zeros((S, n))
    for t in range(H):
        s = np.maximum(0.0, s + x[:, :, t] - k[:, t][:, None])
        mx = np.maximum(mx, s)
    return np.quantile(mx, 1 - week_fa, axis=1)


def first_after(flags: np.ndarray, onset: np.ndarray) -> np.ndarray:
    """Delay (hours of drifted data) to first flag at/after onset; inf if none."""
    t = np.arange(flags.shape[1])[None, :]
    ok = flags & (t >= onset[:, None])
    first = np.where(ok.any(1), ok.argmax(1), np.inf)
    return first + 1 - onset


def world_job(args) -> dict[str, Any]:
    wid, seed, cfg = args
    rng = np.random.default_rng([int(cfg["seed"]), seed, wid])
    S = int(cfg["sites"])
    delta = rng.normal(0, cfg["sigma_delta"], S)
    rates = site_rates(delta, cfg)
    pat = {"flat": np.ones(H), "diurnal": diurnal(cfg)}
    p, shift, sizes = float(cfg["monitor_p"]), float(cfg["cusum_shift"]), [float(d) for d in cfg["drift_sizes"]]
    out: dict[str, Any] = {"seed": seed, "world": wid}
    for scheme, lam in rates.items():
        for pname, m in pat.items():
            cal = rng.poisson(lam[:, None] * m[None, :])
            lam_hat = np.maximum(cal.mean(1), 1e-3)
            hod_hat = np.maximum(cal.reshape(S, 7, 24).mean(1), 1e-3)
            lam_hod = np.tile(hod_hat, 7)
            k_flat = cusum_k(lam_hat, shift)[:, None]
            h_flat = cusum_h(np.repeat(lam_hat[:, None], H, 1), k_flat, cfg["cusum_null_weeks"],
                             cfg["cusum_week_fa"], rng)
            k_hod = cusum_k(lam_hod, shift)
            h_hod = cusum_h(lam_hod, k_hod, cfg["cusum_null_weeks"], cfg["cusum_week_fa"], rng)
            mons = {"daily": lambda x, lh=lam_hat: daily_flags(x, lh, p),
                    "cusum": lambda x, k=k_flat, h=h_flat: cusum_flags(x, k, h),
                    "cusum_hod": lambda x, k=k_hod, h=h_hod: cusum_flags(x, k, h)}
            base = lam[:, None] * m[None, :]
            null = rng.poisson(base)
            key = f"{scheme}|{pname}"
            out[key] = {"ff": {n: float(f(null).sum()) / S for n, f in mons.items()}, "det48": {}, "delay": {}}
            for d in sizes:
                onset = rng.integers(cfg["onset_lo"], cfg["onset_hi"], S)
                mult = np.where(np.arange(H)[None, :] >= onset[:, None], d, 1.0)
                x = rng.poisson(base * mult)
                for n, f in mons.items():
                    dl = first_after(f(x), onset)
                    out[key]["det48"].setdefault(n, {})[str(d)] = float((dl <= 48).mean())
                    out[key]["delay"].setdefault(n, {})[str(d)] = [float(v) for v in dl]
    return out


def analytic_daily(lam: float, d: float, p: float, max_checks: int = 7) -> dict[str, float]:
    """Exact daily-check detection with onset phase uniform over the day (known baseline lam)."""
    c = daily_crit(np.array([24 * lam]), p)[0]
    p_full = stats.poisson.sf(c - 1, 24 * lam * d)
    det48, delays, probs = 0.0, [], []
    for f in range(1, 25):
        p1 = stats.poisson.sf(c - 1, lam * (24 + f * (d - 1)))
        det48 += (1 - (1 - p1) * (1 - p_full)) / 24
        miss = 1.0
        for j in range(max_checks):
            pj = p1 if j == 0 else p_full
            delays.append(f + 24 * j)
            probs.append(miss * pj / 24)
            miss *= 1 - pj
    order = np.argsort(delays)
    dl, pr = np.array(delays)[order], np.cumsum(np.array(probs)[order])
    med = float(dl[np.searchsorted(pr, 0.5)]) if pr[-1] >= 0.5 else float("inf")
    return {"det48": float(det48), "median_delay_h": med,
            "null_ff_site_week": float(7 * stats.poisson.sf(c - 1, 24 * lam))}


def _boot(x: np.ndarray, rng, n: int) -> np.ndarray:
    idx = rng.integers(0, len(x), (n, len(x)))
    return x[idx].mean(1)


def _holm(ps: dict[str, float]) -> dict[str, float]:
    ks = sorted(ps, key=ps.get)
    out, run = {}, 0.0
    for i, k in enumerate(ks):
        run = max(run, min(1.0, (len(ks) - i) * ps[k]))
        out[k] = run
    return out


def summarise(worlds: list[dict], cfg: dict) -> dict[str, Any]:
    rng = np.random.default_rng(int(cfg["seed"]) + 1)
    nb = int(cfg["n_boot"])
    sizes = [str(float(d)) for d in cfg["drift_sizes"]]
    keys = [k for k in worlds[0] if "|" in k]
    res: dict[str, Any] = {"n_worlds": len(worlds), "sites_per_world": int(cfg["sites"])}

    def ci(v):
        b = _boot(v, rng, nb)
        return {"mean": float(v.mean()), "ci": [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))]}

    for key in keys:
        r: dict[str, Any] = {}
        for mon in ("daily", "cusum", "cusum_hod"):
            m = {"false_flags_site_week": ci(np.array([w[key]["ff"][mon] for w in worlds]))}
            for d in sizes:
                det = np.array([w[key]["det48"][mon][d] for w in worlds])
                dl = np.concatenate([w[key]["delay"][mon][d] for w in worlds])
                fin = dl[np.isfinite(dl)]
                m[d] = {"det48": ci(det), "median_delay_h": float(np.median(dl)) if np.isfinite(np.median(dl))
                        else None, "median_delay_detected_h": float(np.median(fin)) if len(fin) else None,
                        "detected_in_week": float(np.isfinite(dl).mean())}
            r[mon] = m
        res[key] = r
    # C2: pooled - per_site daily det48, TOST per size, Holm.
    tost, diffs = {}, {}
    for d in sizes:
        v = np.array([w["pooled|flat"]["det48"]["daily"][d] - w["per_site|flat"]["det48"]["daily"][d]
                      for w in worlds])
        b = _boot(v, rng, nb)
        diffs[d] = {"diff": float(v.mean()), "ci": [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))]}
        tost[d] = float(max((b >= 0.05).mean(), (b <= -0.05).mean(), 1.0 / nb))
    holm = _holm(tost)
    for d in sizes:
        diffs[d]["p_tost_holm"] = holm[d]
    res["C2_pooled_minus_per_site_daily"] = diffs
    # CUSUM pooled vs per-site too (reported)
    res["cusum_pooled_minus_per_site"] = {
        d: float(np.mean([w["pooled|flat"]["det48"]["cusum"][d] - w["per_site|flat"]["det48"]["cusum"][d]
                          for w in worlds])) for d in sizes}
    lam0 = float(cfg["cams_per_site"] * cfg["budget"])
    res["analytic_daily_lam5"] = {d: analytic_daily(lam0, float(d), float(cfg["monitor_p"])) for d in sizes}
    ps = res["per_site|flat"]
    c1 = ps["cusum"]["1.5"]["det48"]["mean"] >= 0.8 and ps["cusum"]["false_flags_site_week"]["mean"] <= 0.02
    c2 = all(diffs[d]["p_tost_holm"] < 0.05 for d in sizes)
    c3 = res["per_site|diurnal"]["cusum"]["false_flags_site_week"]["mean"] <= 0.02
    res["analytic_vs_sim_daily_det48_maxabs"] = float(max(
        abs(res["analytic_daily_lam5"][d]["det48"] - ps["daily"][d]["det48"]["mean"]) for d in sizes))
    res["decision"] = {"C1_cusum_x1.5_48h": bool(c1), "C2_scheme_irrelevant": bool(c2),
                       "C3_diurnal_not_flagged": bool(c3), "met": bool(c1 and c2 and c3)}
    return res


def figure(res: dict, cfg: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sizes = [str(float(d)) for d in cfg["drift_sizes"]]
    x = [float(d) for d in sizes]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    an = res["analytic_daily_lam5"]
    ax[0].plot(x, [an[d]["det48"] for d in sizes], "k-", lw=2, label="daily, analytic (lam=5/h)")
    ax[1].plot(x, [an[d]["median_delay_h"] for d in sizes], "k-", lw=2, label="daily, analytic (lam=5/h)")
    sty = {("per_site", "daily"): ("C0", "o", "-"), ("pooled", "daily"): ("C0", "s", "--"),
           ("per_site", "cusum"): ("C3", "o", "-"), ("pooled", "cusum"): ("C3", "s", "--")}
    for (sch, mon), (c, mk, ls) in sty.items():
        r = res[f"{sch}|flat"][mon]
        m = [r[d]["det48"]["mean"] for d in sizes]
        lo = [m[i] - r[d]["det48"]["ci"][0] for i, d in enumerate(sizes)]
        hi = [r[d]["det48"]["ci"][1] - m[i] for i, d in enumerate(sizes)]
        ax[0].errorbar(x, m, yerr=[lo, hi], color=c, marker=mk, ls=ls, label=f"{mon}, {sch} theta (sim)")
        dl = [r[d]["median_delay_h"] if r[d]["median_delay_h"] is not None else np.nan for d in sizes]
        ax[1].plot(x, dl, color=c, marker=mk, ls=ls, label=f"{mon}, {sch} theta (sim)")
    ax[0].axhline(0.8, c="grey", ls=":", lw=0.8)
    ax[0].set(xlabel="drift size (x rate)", ylabel="detected within 48 h", ylim=(-0.02, 1.02))
    ax[1].set(xlabel="drift size (x rate)", ylabel="median detection delay (h, inf if <50 % in week)", yscale="log")
    ax[0].legend(fontsize=7)
    ax[1].legend(fontsize=7)
    fig.suptitle("H70b: per-site drift monitors, 40 sites x 200 worlds (simulated, sigma_delta=0.3)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(w, s, cfg) for s in range(int(cfg["n_seeds"])) for w in range(int(cfg["worlds_per_seed"]))]
    with ProcessPoolExecutor(int(cfg["workers"])) as ex:
        worlds = list(ex.map(world_job, jobs))
    res = summarise(worlds, cfg)
    per_seed = {}
    for s in range(int(cfg["n_seeds"])):
        ws = [w for w in worlds if w["seed"] == s]
        per_seed[s] = {"cusum_x1.5_det48": float(np.mean([w["per_site|flat"]["det48"]["cusum"]["1.5"] for w in ws])),
                       "diurnal_cusum_ff": float(np.mean([w["per_site|diurnal"]["ff"]["cusum"] for w in ws]))}
    res["per_seed"] = per_seed
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    fig = Path(cfg.get("figure", out / "fig_h70b.png"))
    fig.parent.mkdir(parents=True, exist_ok=True)
    figure(res, cfg, fig)
    return res


def markdown_rows(res: dict, cfg: dict) -> str:
    sizes = [str(float(d)) for d in cfg["drift_sizes"]]
    rows = ["| theta | pattern | monitor | false flags/site-wk | " + " | ".join(f"det48 x{d}" for d in sizes) + " |",
            "|---" * (4 + len(sizes)) + "|"]
    for key in ("per_site|flat", "pooled|flat", "per_site|diurnal", "pooled|diurnal"):
        for mon in ("daily", "cusum", "cusum_hod"):
            r = res[key][mon]
            cells = " | ".join(f"{r[d]['det48']['mean']:.3f}" for d in sizes)
            rows.append(f"| {key.replace('|', ' | ')} | {mon} | {r['false_flags_site_week']['mean']:.3f} | {cells} |")
    rows.append("| analytic | flat, lam 5/h | daily | " + f"{res['analytic_daily_lam5'][sizes[0]]['null_ff_site_week']:.4f} | "
                + " | ".join(f"{res['analytic_daily_lam5'][d]['det48']:.3f}" for d in sizes) + " |")
    return "\n".join(rows) + f"\n\nDecision: {res['decision']}\n"
