"""H66: decoy flooding vs. the operator review queue (docs/research/100 T4; pre-registered in 32).

Discrete-event simulation of one 40-camera wall for 1 h per world. A decoy incident emits k loud,
high-scoring alarms 30-90 s before a real perimeter intrusion; the question is whether the intrusion
alarm is still *reviewed* in time. Hard-negative worlds hold a genuine incident plus an innocent,
badged staff perimeter crossing, so any decoy-aware policy pays a measured false-escalation cost.

Badge corroboration is drawn live per perimeter alarm (AUDIT_H63B: never cached per track).
Operator parameters are H22's verbatim. Every rate is a declared assumption.

    survsim experiment h66_decoy_flooding
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

POLICIES = ("fifo", "ranked", "escalate", "lane")
# alarm row: (t, cls, score, is_intrusion, corroborated, is_incident)


def make_world(i: int, k: int | None, cfg: dict[str, Any]) -> list[tuple]:
    """Alarms of world i. k = decoy size (0 = none); k = None -> hard-negative world."""
    w = cfg["world"]
    base = np.random.default_rng([int(cfg["seed"]), i])          # shared across arms (paired)
    dur, cams = w["duration_s"], w["cameras"]
    n_bg = base.poisson(w["bg_fa_per_cam_h"] * cams * dur / 3600.0)
    al = [(float(t), "per", float(base.beta(2, 5)), False, bool(base.random() < w["p_swipe"]), False)
          for t in base.uniform(0, dur, n_bg)]
    t_ev = float(base.uniform(*w["event_window_s"]))
    lead = float(base.uniform(*w["lead_s"]))
    detect = bool(base.random() < w["p_detect"])
    s_per = float(base.beta(5, 3))
    swipe = bool(base.random() < w["p_swipe"])
    if k is None:   # hard negative: genuine incident at t_ev, innocent badged crossing lead s later
        t_inc, n_inc = t_ev, int(w["hn_incident_k"])
        if detect:
            al.append((t_ev + lead, "per", s_per, False, swipe, False))
    else:
        t_inc, n_inc = t_ev - lead, k
        if detect:
            al.append((t_ev, "per", s_per, True, False, False))
    if n_inc:
        r = np.random.default_rng([int(cfg["seed"]), i, 7, n_inc])
        ts = t_inc + np.cumsum(r.exponential(w["incident_span_s"] / n_inc, n_inc)) - 0.0
        ts[0] = t_inc
        al += [(float(t), "inc", float(r.beta(8, 2)), False, False, True) for t in ts]
    return sorted(al, key=lambda a: a[0])


def _serve(alarms: list[tuple], policy: str, rng, op: dict, fatigued: bool, esc_win: float):
    """One operator queue. Returns {alarm index: (completion time, reviewed_ok)} and escalation count."""
    x = op["fatigue_review_x"] if fatigued else 1.0
    miss = op["miss_fatigued"] if fatigued else op["miss"]
    shape = 1.0 / op["review_cv"] ** 2
    scale = op["review_s"] * x / shape
    inc_t = [a[0] for a in alarms if a[5]]
    out, q, tf, n_esc = {}, [], 0.0, 0
    order = list(range(len(alarms))) + [None]

    def pop():
        esc = [j for j in q if j[1]]
        if esc:
            j = esc[0]
        elif policy == "ranked":
            j = max(q, key=lambda e: alarms[e[0]][2])
        else:
            j = q[0]
        q.remove(j)
        return j[0]

    for idx in order:
        t_next = alarms[idx][0] if idx is not None else np.inf
        while q and max(tf, alarms[q[0][0]][0]) <= t_next:
            j = pop()
            start = max(tf, alarms[j][0])
            tf = start + rng.gamma(shape, scale)
            out[j] = (tf, bool(rng.random() >= miss))
        if idx is None:
            break
        a = alarms[idx]
        esc = False
        if policy == "escalate" and a[1] == "per" and not a[4]:
            esc = any(ti <= a[0] <= ti + esc_win for ti in inc_t)
            n_esc += esc
        if esc:
            q.insert(sum(1 for e in q if e[1]), (idx, True))
        else:
            q.append((idx, False))
        if len(q) > op["bulk_ack_queue"]:
            q = [e for e in q if e[1] and op.get("escalated_exempt_bulk_ack", True)]  # bulk ack
    return out, n_esc


def simulate(alarms: list[tuple], policy: str, seed: list[int], op: dict, esc_win: float) -> dict:
    rng = np.random.default_rng(seed)
    fatigued = bool(rng.uniform(0, op["shift_h"]) > op["fatigue_after_h"])
    if policy == "lane":
        res = {}
        for cls in ("per", "inc"):
            sub = [j for j, a in enumerate(alarms) if (a[1] == "per") == (cls == "per")]
            o, _ = _serve([alarms[j] for j in sub], "fifo", rng, op, fatigued, esc_win)
            res.update({sub[j]: v for j, v in o.items()})
        n_esc = 0
    else:
        res, n_esc = _serve(alarms, policy, rng, op, fatigued, esc_win)
    m: dict[str, Any] = {"n_esc": n_esc}
    ii = [j for j, a in enumerate(alarms) if a[3]]
    for h in op["horizons_s"]:
        m[f"rec{h}"] = float(any(j in res and res[j][1] and res[j][0] - alarms[j][0] <= h for j in ii))
    inc = [j for j, a in enumerate(alarms) if a[5]]
    if inc:
        t0 = alarms[inc[0]][0]
        done = [res[j][0] for j in inc if j in res]
        m["inc_delay"] = (min(done) if done else 3600.0 + t0) - t0
    return m


def _world_job(args):
    i, cfg = args
    op, ew = cfg["operator"], cfg["escalate_window_s"]
    out = {}
    arms = [(f"k{k}", k) for k in cfg["decoy_k"]] + [("hn", None)]
    for name, k in arms:
        al = make_world(i, k, cfg)
        for pol in POLICIES:
            rs = [simulate(al, pol, [int(cfg["seed"]), i, s, 99], op, ew) for s in cfg["operator_seeds"]]
            out[(name, pol)] = {key: float(np.mean([r[key] for r in rs])) for key in rs[0]}
            out[(name, pol)]["has_int"] = float(any(a[3] for a in al))
    return out


def _holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    adj, run = {}, 0.0
    for r, (key, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - r) * p))
        adj[key] = run
    return adj


def summarise(worlds: list[dict], cfg: dict) -> dict[str, Any]:
    nb, n = int(cfg["n_boot"]), len(worlds)
    bi = np.random.default_rng(int(cfg["seed"])).integers(0, n, (nb, n))
    ks = [f"k{k}" for k in cfg["decoy_k"]]
    cam_h = cfg["world"]["cameras"] * cfg["world"]["duration_s"] / 3600.0

    def col(arm, pol, key):
        return np.array([w[(arm, pol)][key] for w in worlds])

    def ci(v):
        b = v[bi].mean(1)
        return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]

    res: dict[str, Any] = {"n_worlds": n, "operator_seeds": len(cfg["operator_seeds"]), "recall": {}}
    for arm in ks:
        for pol in POLICIES:
            for h in cfg["operator"]["horizons_s"]:
                v = col(arm, pol, f"rec{h}")
                res["recall"][f"{arm}/{pol}/@{h}"] = {"mean": float(v.mean()), "boot95": ci(v)}
    base = col("k0", "fifo", "rec300")
    drops, pd, rec, pr = {}, {}, {}, {}
    for arm in ks[1:]:
        d = base - col(arm, "fifo", "rec300")
        b = d[bi].mean(1)
        drops[arm] = {"drop": float(d.mean()), "boot95": ci(d)}
        pd[arm] = float((np.sum(b <= 0) + 1) / (nb + 1))
        e = col(arm, "escalate", "rec300") - base
        b = e[bi].mean(1)
        rec[arm] = {"diff": float(e.mean()), "boot95": ci(e)}
        pr[arm] = float((np.sum(b < -0.05) + 1) / (nb + 1))   # H0: escalate worse than fifo@0 by > 0.05
    for arm, p in _holm(pd).items():
        drops[arm].update(p_one_sided=pd[arm], p_holm=p)
    for arm, p in _holm(pr).items():
        rec[arm].update(p_one_sided=pr[arm], p_holm=p)
    res["fifo_drop"], res["escalate_vs_fifo0"] = drops, rec
    hn = {}
    for pol in POLICIES:
        esc = col("hn", pol, "n_esc")
        dl = col("hn", pol, "inc_delay")
        hn[pol] = {"esc_per_cam_h": float(esc.sum() / (n * cam_h)), "esc_boot95": [x / cam_h for x in ci(esc)],
                   "inc_delay_median_s": float(np.median(dl))}
    add = col("hn", "escalate", "inc_delay") - col("hn", "fifo", "inc_delay")
    b = np.median(add[bi], axis=1)
    hn["escalate_added_delay_median_s"] = float(np.median(add))
    hn["escalate_added_delay_boot95"] = [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]
    res["hard_negative"] = hn
    kmax = ks[-1]
    d1 = all(drops[a]["p_holm"] < 0.05 for a in ks[-2:]) and drops[kmax]["drop"] >= 0.20
    d2 = rec[kmax]["boot95"][0] >= -0.05
    d3 = hn["escalate"]["esc_per_cam_h"] <= 0.05 and hn["escalate_added_delay_median_s"] <= 30.0
    res["abandon"] = res["recall"]["k0/fifo/@300"]["mean"] < 0.5
    res["decision"] = {"1_drop": bool(d1), "2_escalate_recovers": bool(d2), "3_hard_negative_cost": bool(d3),
                       "met": bool(d1 and d2 and d3)}
    return res


def figure(res: dict, cfg: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ks = cfg["decoy_k"]
    cols = {"fifo": "#3a6ea5", "ranked": "#c7792b", "escalate": "#5b9a5b", "lane": "#777777"}
    for pol in POLICIES:
        m = np.array([res["recall"][f"k{k}/{pol}/@300"]["mean"] for k in ks])
        lo = np.array([res["recall"][f"k{k}/{pol}/@300"]["boot95"][0] for k in ks])
        hi = np.array([res["recall"][f"k{k}/{pol}/@300"]["boot95"][1] for k in ks])
        ax[0].errorbar(ks, m, yerr=[m - lo, hi - m], marker="o", capsize=3, label=pol, color=cols[pol])
    b0 = res["recall"]["k0/fifo/@300"]["mean"]
    ax[0].axhline(b0 - 0.05, ls=":", c="k", lw=0.8)
    ax[0].set_xlabel("decoy alarms k")
    ax[0].set_ylabel("operator-realised intrusion recall @300 s")
    ax[0].legend(fontsize=8)
    hn = res["hard_negative"]
    x = np.arange(len(POLICIES))
    ax[1].bar(x, [hn[p]["inc_delay_median_s"] for p in POLICIES], color=[cols[p] for p in POLICIES])
    ax[1].set_xticks(x, POLICIES)
    ax[1].set_ylabel("hard-neg incident 1st-review delay (median s)", fontsize=8)
    ax[1].set_title(f"escalations/cam-h: {hn['escalate']['esc_per_cam_h']:.3f}", fontsize=8)
    fig.suptitle("H66: decoy flooding vs operator queue (simulated, H22 operator)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(i, cfg) for i in range(int(cfg["n_worlds"]))]
    with ProcessPoolExecutor(int(cfg["workers"])) as ex:
        worlds = list(ex.map(_world_job, jobs, chunksize=20))
    res = summarise(worlds, cfg)
    res["config"] = cfg
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    fig = Path(cfg.get("figure", out / "fig_h66.png"))
    fig.parent.mkdir(parents=True, exist_ok=True)
    figure(res, cfg, fig)
    return res


def markdown_rows(res: dict, cfg: dict) -> str:
    rows = ["| k | " + " | ".join(POLICIES) + " |", "|---|" + "---|" * len(POLICIES)]
    for k in cfg["decoy_k"]:
        cells = []
        for p in POLICIES:
            r = res["recall"][f"k{k}/{p}/@300"]
            cells.append(f"{r['mean']:.3f} [{r['boot95'][0]:.3f}, {r['boot95'][1]:.3f}]")
        rows.append(f"| {k} | " + " | ".join(cells) + " |")
    return "\n".join(rows) + f"\n\ndecision: {res['decision']}\n"
