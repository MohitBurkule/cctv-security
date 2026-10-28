"""H70: alarm budgets at estate scale (pre-registered in docs/research/32 §H70).

Simulated 40-site / 400-camera estate, one calibration week then one test week, one shared K-operator FIFO
queue (H22 values). Schemes: (a) pooled theta for a global budget, (b) per-site theta for per-site budgets,
(c) global budget re-allocated across sites by a Lagrangian on recall vs FA. One random site drifts x3 at
test hour 84; a daily Poisson monitor must notice it. Every rate is a declared assumption, not a FACT.

    survsim experiment h70_alarm_budget_scale
"""
from __future__ import annotations

import heapq
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import norm, poisson

SCHEMES = ("a_pooled", "b_per_site", "c_realloc")
GRID = np.linspace(-3.0, 5.0, 801)


def _site_fa_curve(scores: np.ndarray, cam_h: float) -> np.ndarray:
    """FA/cam-h of one site's candidate scores at every GRID threshold."""
    s = np.sort(scores)
    return (len(s) - np.searchsorted(s, GRID, side="left")) / cam_h


def _theta_for(scores: np.ndarray, cam_h: float, fa: float) -> float:
    """Smallest theta whose FA/cam-h on these scores is <= fa (empirical quantile)."""
    n_allow = int(np.floor(fa * cam_h))
    if n_allow >= len(scores):
        return float(GRID[0])
    s = np.sort(scores)[::-1]
    return float(np.nextafter(s[n_allow], np.inf))


def calibrate(cal: list[np.ndarray], cfg: dict) -> dict[str, np.ndarray]:
    """theta per site for each scheme, and the calibration-week FA/cam-h each scheme expects."""
    cam_h = cfg["cams_per_site"] * cfg["week_h"]
    B, n = float(cfg["budget"]), len(cal)
    th_a = _theta_for(np.concatenate(cal), cam_h * n, B)
    th_b = np.array([_theta_for(c, cam_h, B) for c in cal])
    curves = np.stack([_site_fa_curve(c, cam_h) for c in cal])            # (sites, grid)
    rec = cfg["p_detect"] * norm.sf(GRID, cfg["intr_mu"], cfg["intr_sd"])
    w = cfg["intr_per_site_week"]

    def pick(lam):
        idx = np.argmax(w * rec[None, :] - lam * cfg["cams_per_site"] * cfg["week_h"] * curves, axis=1)
        return idx, curves[np.arange(n), idx].mean()

    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        _, fa = pick(mid)
        lo, hi = (lo, mid) if fa <= B else (mid, hi)
    idx, _ = pick(hi)
    th_c = GRID[idx]
    out = {"a_pooled": np.full(n, th_a), "b_per_site": th_b, "c_realloc": th_c}
    exp = {k: np.array([(c >= t).sum() / cam_h for c, t in zip(cal, v, strict=True)]) for k, v in out.items()}
    return {"theta": out, "expected": exp}


def make_world(i: int, cfg: dict, sigma: float) -> dict[str, Any]:
    r = np.random.default_rng([int(cfg["seed"]), i, round(sigma * 1000)])
    S, C, H = cfg["sites"], cfg["cams_per_site"], cfg["week_h"]
    delta = r.normal(0.0, sigma, S)
    lam = cfg["cand_per_cam_h"] * C

    def scores(s, hours, rate_x=1.0):
        return r.normal(cfg["bg_mu"] + delta[s], cfg["bg_sd"], r.poisson(lam * hours * rate_x))

    cal = [scores(s, H) for s in range(S)]
    drift = int(r.integers(S))
    days = []   # days[d][s] = (times_s, scores)
    for d in range(H // 24):
        row = []
        for s in range(S):
            t0 = d * 24.0
            if s == drift and t0 + 24 > cfg["drift_hour"]:
                a = max(t0, cfg["drift_hour"])
                parts = [(t0, a, 1.0), (a, t0 + 24, cfg["drift_x"])]
            else:
                parts = [(t0, t0 + 24, 1.0)]
            ts, sc = [], []
            for u, v, x in parts:
                if v > u:
                    k = r.poisson(lam * (v - u) * x)
                    ts.append(r.uniform(u, v, k) * 3600.0)
                    sc.append(r.normal(cfg["bg_mu"] + delta[s], cfg["bg_sd"], k))
            row.append((np.concatenate(ts), np.concatenate(sc)))
        days.append(row)
    n_int = r.poisson(cfg["intr_per_site_week"], S)
    intr = [(float(t), s, float(sc), bool(dt))
            for s in range(S) for t, sc, dt in zip(r.uniform(0, H * 3600.0, n_int[s]),
                                                   r.normal(cfg["intr_mu"], cfg["intr_sd"], n_int[s]),
                                                   r.random(n_int[s]) < cfg["p_detect"], strict=True)]
    return {"delta": delta, "cal": cal, "days": days, "drift": drift, "intr": intr}


def run_scheme(world: dict, calib: dict, scheme: str, cfg: dict) -> dict[str, Any]:
    """Apply a scheme over the test week with the daily monitor. Returns alarms and per-site counts."""
    S, C = cfg["sites"], cfg["cams_per_site"]
    th = calib["theta"][scheme].copy()
    exp = calib["expected"][scheme].copy()            # FA/cam-h the monitor expects per site
    fa_t, fa_count = [], np.zeros(S)
    flags = []                                          # (day, site or -1 for estate)
    intr = sorted(world["intr"])
    int_alarm = []
    for d, row in enumerate(world["days"]):
        t0, t1 = d * 86400.0, (d + 1) * 86400.0
        cnt = np.zeros(S)
        for s, (ts, sc) in enumerate(row):
            m = sc >= th[s]
            fa_t.append(ts[m])
            cnt[s] = m.sum()
        for t, s, sc, det in intr:
            if t0 <= t < t1 and det and sc >= th[s]:
                int_alarm.append(t)
        fa_count += cnt
        if scheme == "a_pooled":
            mu = exp.sum() * C * 24
            if poisson.sf(cnt.sum() - 1, mu) < cfg["monitor_p"]:
                flags.append((d, -1))
                sc_all = np.concatenate([sc for _, sc in row])
                th[:] = _theta_for(sc_all, S * C * 24, float(cfg["budget"]))
                exp[:] = float(cfg["budget"])
        else:
            for s in range(S):
                if poisson.sf(cnt[s] - 1, exp[s] * C * 24) < cfg["monitor_p"]:
                    flags.append((d, s))
                    target = float(cfg["budget"]) if scheme == "b_per_site" else float(exp[s])
                    th[s] = max(th[s], _theta_for(row[s][1], C * 24, target))
    return {"fa_times": np.sort(np.concatenate(fa_t)), "int_times": np.array(int_alarm),
            "fa_site": fa_count / (C * cfg["week_h"]), "flags": flags, "n_int": len(intr)}


def queue(fa_times: np.ndarray, int_times: np.ndarray, K: int, op: dict, seed: list[int],
          horizon: float, end_s: float) -> dict[str, float]:
    """K-server FIFO with bulk-ack (queue cleared when > bulk_ack_per_op*K). Returns hits and busy time."""
    rng = np.random.default_rng(seed)
    t = np.concatenate([fa_times, int_times])
    is_int = np.concatenate([np.zeros(len(fa_times), bool), np.ones(len(int_times), bool)])
    o = np.argsort(t, kind="stable")
    t, is_int = t[o], is_int[o]
    shape = 1.0 / op["review_cv"] ** 2
    svc = rng.gamma(shape, op["review_s"] / shape, len(t))
    ok = rng.random(len(t)) >= op["miss"]
    free = [0.0] * K
    q: list[int] = []
    head = 0
    hits, busy, cap = 0, 0.0, op["bulk_ack_per_op"] * K

    def dispatch(until):
        nonlocal head, hits, busy
        while head < len(q) and free[0] <= until:
            j = q[head]
            head += 1
            st = max(heapq.heappop(free), t[j])
            fin = st + svc[j]
            busy += min(fin, end_s) - min(st, end_s)
            heapq.heappush(free, fin)
            if is_int[j] and ok[j] and fin - t[j] <= horizon:
                hits += 1

    for j in range(len(t)):
        dispatch(t[j])
        q.append(j)
        if len(q) - head > cap:
            head = len(q)          # bulk ack: everything waiting is acknowledged unseen
    dispatch(np.inf)
    return {"hits": hits, "busy": busy}


def world_job(args) -> dict[str, Any]:
    i, cfg, sigma = args
    w = make_world(i, cfg, sigma)
    cal = calibrate(w["cal"], cfg)
    end_s = cfg["week_h"] * 3600.0
    B, out = float(cfg["budget"]), {"drift": w["drift"]}
    for sch in SCHEMES:
        r = run_scheme(w, cal, sch, cfg)
        nd = np.delete(r["fa_site"], w["drift"])
        drift_flag = [d for d, s in r["flags"] if s in (w["drift"], -1) and d >= cfg["drift_hour"] // 24]
        rec = {"n_int": r["n_int"], "worst_fa": float(nd.max()), "n_over_B": int((nd > B).sum()),
               "n_over_2B": int((nd > 2 * B).sum()), "drift_fa": float(r["fa_site"][w["drift"]]),
               "estate_fa": float(r["fa_site"].mean()),
               "noticed_24h": bool(any(d == cfg["drift_hour"] // 24 for d in drift_flag)),
               "false_flags": int(sum(1 for _, s in r["flags"] if s not in (w["drift"], -1))),
               "cal_theta_sd": float(np.std(cal["theta"][sch]))}
        for K in cfg["K"]:
            qq = queue(r["fa_times"], r["int_times"], int(K), cfg["operator"], [int(cfg["seed"]), i, int(K), 5],
                       float(cfg["horizon_s"]), end_s)
            rec[f"hits_K{K}"] = qq["hits"]
            rec[f"util_K{K}"] = qq["busy"] / (int(K) * end_s)
        out[sch] = rec
    return out


def _holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    adj, run = {}, 0.0
    for r, (key, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - r) * p))
        adj[key] = run
    return adj


def summarise(worlds: list[dict], cfg: dict) -> dict[str, Any]:
    n, nb = len(worlds), int(cfg["n_boot"])
    bi = np.random.default_rng(int(cfg["seed"])).integers(0, n, (nb, n))
    B = float(cfg["budget"])

    def arr(sch, key):
        return np.array([w[sch][key] for w in worlds], float)

    def ci(b):
        return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]

    ni = arr("a_pooled", "n_int")
    res: dict[str, Any] = {"n_worlds": n, "n_intrusions": int(ni.sum()), "schemes": {}}
    for sch in SCHEMES:
        d: dict[str, Any] = {}
        for K in cfg["K"]:
            h = arr(sch, f"hits_K{K}")
            d[f"recall300_K{K}"] = {"mean": float(h.sum() / ni.sum()), "boot95": ci(h[bi].sum(1) / ni[bi].sum(1))}
            u = arr(sch, f"util_K{K}")
            d[f"util_K{K}"] = {"mean": float(u.mean()), "boot95": ci(u[bi].mean(1))}
        for key in ("worst_fa", "n_over_B", "n_over_2B", "drift_fa", "estate_fa", "cal_theta_sd"):
            v = arr(sch, key)
            d[key] = {"mean": float(v.mean()), "boot95": ci(v[bi].mean(1)), "max": float(v.max())}
        d["frac_worlds_worst_le_2B"] = float((arr(sch, "worst_fa") <= 2 * B).mean())
        d["noticed_24h_frac"] = float(arr(sch, "noticed_24h").mean())
        d["false_flags_per_site_week"] = float(arr(sch, "false_flags").sum() / (n * (cfg["sites"] - 1)))
        res["schemes"][sch] = d
    diffs, ps = {}, {}
    for K in cfg["K"]:
        for other in ("b_per_site", "c_realloc"):
            ha, ho = arr("a_pooled", f"hits_K{K}"), arr(other, f"hits_K{K}")
            b = (ho[bi].sum(1) - ha[bi].sum(1)) / ni[bi].sum(1)
            key = f"{other}-a_pooled/K{K}"
            diffs[key] = {"diff": float((ho.sum() - ha.sum()) / ni.sum()), "boot95": ci(b)}
            if other == "c_realloc":
                ps[key] = float((np.sum(b <= 0) + 1) / (nb + 1))
    for k, p in _holm(ps).items():
        diffs[k].update(p_one_sided=ps[k], p_holm=p)
    res["recall_diff"] = diffs
    c = res["schemes"]["c_realloc"]
    k0 = f"c_realloc-a_pooled/K{cfg['K'][0]}"
    d1 = diffs[k0]["diff"] >= 0.05 and diffs[k0]["p_holm"] < 0.05
    d2 = c["frac_worlds_worst_le_2B"] >= 0.90
    d3 = c["noticed_24h_frac"] >= 0.90 and c["false_flags_per_site_week"] <= 0.05
    res["decision"] = {"D1_recall_gain": bool(d1), "D2_no_site_over_2B": bool(d2), "D3_drift_noticed": bool(d3),
                       "met": bool(d1 and d2 and d3)}
    return res


def figure(res: dict, cfg: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = res["primary"]
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    cols = ["#3a6ea5", "#c7792b", "#5b9a5b"]
    x = np.arange(len(SCHEMES))
    for j, K in enumerate(cfg["K"]):
        m = np.array([p["schemes"][s][f"recall300_K{K}"]["mean"] for s in SCHEMES])
        lo = np.array([p["schemes"][s][f"recall300_K{K}"]["boot95"][0] for s in SCHEMES])
        hi = np.array([p["schemes"][s][f"recall300_K{K}"]["boot95"][1] for s in SCHEMES])
        ax[0].bar(x + 0.35 * j, m, 0.35, yerr=[m - lo, hi - m], capsize=3, label=f"K={K}",
                  color=["#3a6ea5", "#9ab8d8"][j])
    ax[0].set_xticks(x + 0.17, ["(a) pooled", "(b) per-site", "(c) realloc"], fontsize=8)
    ax[0].set_ylabel("realised intrusion recall@300 s")
    ax[0].legend(fontsize=8)
    wf = [p["schemes"][s]["worst_fa"]["mean"] for s in SCHEMES]
    ax[1].bar(x, wf, color=cols)
    ax[1].axhline(cfg["budget"], c="k", ls=":", lw=0.8)
    ax[1].axhline(2 * cfg["budget"], c="r", ls=":", lw=0.8)
    ax[1].set_xticks(x, ["(a)", "(b)", "(c)"])
    ax[1].set_ylabel("worst non-drift site FA/cam-h (mean)", fontsize=8)
    ax[2].bar(x, [p["schemes"][s]["noticed_24h_frac"] for s in SCHEMES], color=cols)
    ax[2].axhline(0.9, c="k", ls=":", lw=0.8)
    ax[2].set_xticks(x, ["(a)", "(b)", "(c)"])
    ax[2].set_ylabel("x3 drift noticed within 24 h", fontsize=8)
    fig.suptitle(f"H70: alarm budgets, 40 sites / 400 cams (simulated, sigma_delta={cfg['sigma_delta']})",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor
    res: dict[str, Any] = {}
    for tag, sig in (("primary", cfg["sigma_delta"]), ("sensitivity", cfg["sigma_delta_sensitivity"])):
        jobs = [(i, cfg, float(sig)) for i in range(int(cfg["n_worlds"]))]
        with ProcessPoolExecutor(int(cfg["workers"])) as ex:
            worlds = list(ex.map(world_job, jobs))
        res[tag] = summarise(worlds, cfg)
        res[tag]["sigma_delta"] = sig
    res["decision"] = res["primary"]["decision"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    fig = Path(cfg.get("figure", out / "fig_h70.png"))
    fig.parent.mkdir(parents=True, exist_ok=True)
    figure(res, cfg, fig)
    return res


def markdown_rows(res: dict, cfg: dict) -> str:
    rows = ["| sigma | scheme | recall@300 K=2 | util K=2 | worst FA | sites > B | noticed |", "|---|" * 7]
    for tag in ("primary", "sensitivity"):
        for s in SCHEMES:
            d = res[tag]["schemes"][s]
            r = d["recall300_K2"]
            rows.append(f"| {res[tag]['sigma_delta']} | {s} | {r['mean']:.3f} [{r['boot95'][0]:.3f}, "
                        f"{r['boot95'][1]:.3f}] | {d['util_K2']['mean']:.3f} | {d['worst_fa']['mean']:.3f} | "
                        f"{d['n_over_B']['mean']:.1f} | {d['noticed_24h_frac']:.2f} |")
    return "\n".join(rows) + f"\n\ndecision: {res['decision']}\n"
