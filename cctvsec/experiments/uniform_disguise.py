"""H63: uniformed intruder vs. appearance-role suppression and corroboration mismatch.

Pre-registered in docs/research/32 (H63). Reuses H54's cached worlds, tracker noise and simulated
badge / RF streams (all declared assumptions). The hostile actor of every recall world is a
`uniformed_intruder` (survsim.generator.narrative.uniformed_intruder_arc): appearance role "guard",
no roster entry, no badge, no registered tag. Arms differ only on guard-role alarms:

* C   keep;          (a) drop (looks like a guard);
* (b) keep iff NOT(badge +/-15 s AND registered RF within 8 m AND on roster);
* (c) (b) AND off the rostered patrol path (> 5 m for > 5 s).

    survsim experiment h63_uniform_mismatch
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from . import line_cross as LC
from . import sensor_fusion as SF

ARMS = ("C", "a", "b", "c")
TWINS = SF.H54_TWINS
UNIFORM_KINDS = ("patrol_guard", "incident")  # bodies wearing a guard uniform


def _route_dist(zones, gates, off: float):
    """Distance function to the rostered patrol path: fence rings + gate -> zone-centroid legs."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    polys = LC._polys(zones, {"restricted", "perimeter_fence"})
    geoms = []
    for _, p in polys:
        geoms.append(p.buffer(off, join_style=2).exterior)
        c = p.centroid
        if gates:
            g = min(gates, key=lambda q: Point(q).distance(p))
            geoms.append(LineString([tuple(g), (c.x, c.y)]))
    u = unary_union(geoms) if geoms else None
    return (lambda x, y: float(u.distance(Point(x, y)))) if u is not None else (lambda x, y: 0.0)


def _off_route_time(g, ta: float, dist, rc: dict) -> float | None:
    """Earliest time >= ta - lookback at which the track has been > off_m from the route for off_s."""
    tt, xx, yy = g["t"].to_numpy(float), g["x"].to_numpy(float), g["y"].to_numpy(float)
    m = (tt >= ta - rc["lookback_s"]) & (tt <= ta + 60.0)
    run0 = None
    for t, x, y in zip(tt[m], xx[m], yy[m]):
        if dist(x, y) > rc["off_m"]:
            run0 = t if run0 is None else run0
            if t - run0 >= rc["off_s"]:
                return max(float(t), ta)
        else:
            run0 = None
    return None


def fuse_world(w: dict, cfg: dict, h54: dict) -> dict[str, Any]:
    from survsim.sensors.rf import RfConfig, rssi_at
    i, mode, kind = w["i"], w["mode"], w.get("kind")
    ws = int(h54["world_seed"])
    if mode == "clean":
        meta, df = SF._regen_clean_h54(i, h54)
        kinds, actors, truth = meta["kinds"], [], []
        nrng = np.random.default_rng([ws, i, 0])
    else:
        meta, df = SF._regen_recall_h54(i, kind, h54)
        tk = set(h54["twin_kinds"])
        kinds = {u: (n if n in tk else "incident" if u in meta["actors"] else "commuter")
                 for u, n in meta["narratives"].items()}
        actors = list(meta["actors"])
        nrng = np.random.default_rng([ws, 100000 + i, SF.H54_KIND[kind][2]])
        st = LC._polys(meta["zones"], set(h54["sterile_tags"]))
        truth = []
        for a, t0 in meta["hostile_start"].items():
            g = df[(df["uid"].astype(str) == a) & (df["t"] >= t0 - 1e-9)].sort_values("t")
            if g.empty or not st:
                continue
            zi, _ = LC.zone_state(g["x"].to_numpy(float), g["y"].to_numpy(float), st)
            if (zi >= 0).any():
                truth.append({"t": float(g["t"].to_numpy()[np.argmax(zi >= 0)]), "actor": a})
    df = df[["t", "uid", "x", "y"]].copy()
    df["uid"] = df["uid"].astype(str)
    zones, gates = meta["zones"], meta["gates"]
    sterile = LC._polys(zones, set(h54["sterile_tags"]))
    tr = LC.add_noise(df, zones, meta["camera_hours"], nrng, h54["noise"], true_h=meta.get("true_h"))
    alarms = SF.alarms_with_tracks(tr, zones, h54, kinds)
    by = {u: g.sort_values("t") for u, g in df.groupby("uid", sort=False)}
    twins = sorted(u for u, k in kinds.items() if k in set(h54["twin_kinds"]) and u in by)
    trk = {u: g.sort_values("t") for u, g in tr.groupby("uid", sort=False) if u in {a[4] for a in alarms}}
    est = {u: SF.entries_xy(g["x"].to_numpy(float), g["y"].to_numpy(float), g["t"].to_numpy(float), sterile)
           if sterile else [] for u, g in trk.items()}
    ent = {u: SF.entries_xy(by[u]["x"].to_numpy(float), by[u]["y"].to_numpy(float),
                            by[u]["t"].to_numpy(float), sterile) if sterile else [] for u in twins}
    gl, rf = h54["gate_log"], h54["rf"]
    rc = RfConfig(path_loss_exponent=rf["path_loss_n"], shadowing_sigma_db=rf["shadow_db"])
    rng = np.random.default_rng([int(cfg["seed"]), i, SF.H54_KIND.get(kind or "", (0, 0, 0))[2]])
    carry = sorted(u for u in twins if rng.random() < rf["p_carry"])  # registered, rostered tags
    badges = [(t + rng.normal(0, gl["jitter_s"]), z) for u in twins for t, z, _, _ in ent[u]
              if rng.random() < gl["p_swipe"]]
    adv = {u: (by[u]["t"].to_numpy(float), by[u]["x"].to_numpy(float), by[u]["y"].to_numpy(float)) for u in carry}
    dist = _route_dist(zones, gates, cfg["route"]["ring_offset_m"])
    ro = cfg["role"]

    def rf_hit(ta, pos, rmax):
        ts = ta + np.arange(-rf["window_s"], rf["window_s"] + 1e-9, 1.0 / rf["advert_hz"])
        for u in carry:
            tt, xx, yy = adv[u]
            if tt[0] > ts[-1] or tt[-1] < ts[0]:
                continue
            for s_ in ts:
                k = int(np.argmin(np.abs(tt - s_)))
                if abs(tt[k] - s_) > 0.5 or rng.random() < rf["miss_p"]:
                    continue
                d = float(np.hypot(xx[k] - pos[0], yy[k] - pos[1]))
                if d <= rmax and rssi_at(d, rf["tx_dbm"], rc, rng) > rf["rssi_min_dbm"]:
                    return True
        return False

    role = {}
    kept: dict[str, list] = {a: [] for a in ARMS}
    for a in alarms:
        ta, base, u = float(a[0]), a[1], a[4]
        kd = kinds.get(base, "commuter") if a[2] != "ghost" else "ghost"
        if u not in role:
            p = ro["p_guard_given_uniform"] if kd in UNIFORM_KINDS else ro["p_guard_given_other"]
            role[u] = bool(rng.random() < p)
        g = trk[u]
        k = int(np.argmin(np.abs(g["t"].to_numpy(float) - ta)))
        pos = (float(g["x"].iat[k]), float(g["y"].iat[k]))
        cr = SF.crossing_for([(e[0], e[1]) for e in est.get(u, [])], ta)
        badge = cr is not None and any(zz == cr[1] and abs(tb - cr[0]) <= cfg["badge_window_s"] for tb, zz in badges)
        rfm = rf_hit(ta, pos, cfg["rf_radius_m"])
        # actor pos at alarm time (H62 dynamic reference) for position-keyed scoring
        apos = {}
        for act in actors:
            ag = by.get(act)
            if ag is not None:
                k2 = int(np.argmin(np.abs(ag["t"].to_numpy(float) - ta)))
                apos[act] = (float(ag["x"].iat[k2]), float(ag["y"].iat[k2]))
        row = [ta, base, a[2], kd, pos, apos]
        if not role[u]:
            if not (badge or rfm):  # H53 corroboration, identical in every arm
                for arm in ARMS:
                    kept[arm].append(row)
            continue
        mism = not (badge and rfm)  # on-roster check passes iff identified (every twin is on shift)
        kept["C"].append(row)
        if mism:
            kept["b"].append(row)
            t_off = _off_route_time(g, ta, dist, cfg["route"])
            if t_off is not None:
                kept["c"].append([t_off, *row[1:4], pos, apos])
    return {"mode": mode, "kind": kind, "i": i, "camera_hours": meta["camera_hours"], "truth": truth,
            "kept": kept, "n_kind": {k: sum(v == k for v in kinds.values()) for k in TWINS}}


def _job(args):
    return fuse_world(*args)


def _recall(ws, tol, r, bi):

    out = {}
    for arm in ARMS:
        ta_, tp_ = np.zeros(len(ws)), np.zeros(len(ws))
        for j, w in enumerate(ws):
            for e in w["truth"]:
                win = [x for x in w["kept"][arm] if e["t"] - 1e-9 <= x[0] <= e["t"] + tol]
                ta_[j] += any(x[1] == e["actor"] for x in win)
                tp_[j] += any(e["actor"] in x[5] and np.hypot(x[4][0] - x[5][e["actor"]][0],
                                                               x[4][1] - x[5][e["actor"]][1]) <= r for x in win)
        ev = np.array([len(w["truth"]) for w in ws], float)
        o = {}
        for nm, v in (("actor", ta_), ("pos", tp_)):
            bs = v[bi].sum(1) / np.maximum(ev[bi].sum(1), 1)
            o[nm] = {"recall": float(v.sum() / ev.sum()), "tp": int(v.sum()), "events": int(ev.sum()),
                     "boot95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}
        out[arm] = o
    return out


def summarise(res: list[dict], cfg: dict) -> dict[str, Any]:
    from .inference import garwood
    clean = [w for w in res if w["mode"] == "clean"]
    rec = [w for w in res if w["mode"] == "recall"]
    ch = np.array([w["camera_hours"] for w in clean])
    rng = np.random.default_rng(int(cfg["seed"]))
    nb = int(cfg["n_boot"])
    bc = rng.integers(0, len(clean), (nb, len(clean)))
    br = rng.integers(0, len(rec), (nb, len(rec)))
    out: dict[str, Any] = {"n_clean": len(clean), "n_recall": len(rec), "clean_cam_h": float(ch.sum()),
                           "n_kind": {k: int(sum(w["n_kind"][k] for w in clean)) for k in TWINS},
                           "recall": _recall(rec, cfg["tolerance_s"], cfg["pos_radius_m"], br)}
    for arm in ARMS:
        tot = np.array([len(w["kept"][arm]) for w in clean], float)
        tw = np.array([sum(1 for x in w["kept"][arm] if x[3] in TWINS) for w in clean], float)
        pg = np.array([sum(1 for x in w["kept"][arm] if x[3] == "patrol_guard") for w in clean], float)
        o = {}
        for nm, v in (("all", tot), ("twin", tw), ("patrol_guard", pg)):
            b = v[bc].sum(1) / ch[bc].sum(1)
            o[nm] = {"n": int(v.sum()), "per_cam_h": float(v.sum() / ch.sum()),
                     "garwood95": list(garwood(int(v.sum()), float(ch.sum()))),
                     "boot95": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]}
        out[f"fa_{arm}"] = o
    rb, ra = out["recall"]["b"]["actor"]["recall"], out["recall"]["a"]["actor"]["recall"]
    out["decision"] = {"b_recall_ge_0.8": rb >= 0.8, "b_twin_fa_le_0.05": out["fa_b"]["twin"]["per_cam_h"] <= 0.05,
                       "a_recall_le_0.1": ra <= 0.1}
    out["decision"]["met"] = all(out["decision"].values())
    return out


def figure(res: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    x = np.arange(len(ARMS))
    lab = ["C (no role)", "(a) role suppress", "(b) mismatch", "(c) (b)+route"]
    for off, nm, col in ((-0.18, "actor", "#3a6ea5"), (0.18, "pos", "#c7792b")):
        v = np.array([res["recall"][a][nm]["recall"] for a in ARMS])
        lo = np.array([res["recall"][a][nm]["boot95"][0] for a in ARMS])
        hi = np.array([res["recall"][a][nm]["boot95"][1] for a in ARMS])
        ax[0].bar(x + off, v, 0.36, yerr=[v - lo, hi - v], color=col, label=f"{nm}-keyed", capsize=3)
    ax[0].axhline(0.8, ls="--", c="k", lw=0.8)
    ax[0].axhline(0.1, ls=":", c="k", lw=0.8)
    ax[0].set_ylabel("uniformed-intruder recall@10 s")
    ax[0].legend(fontsize=8)
    for off, nm, col in ((-0.18, "all", "#777777"), (0.18, "twin", "#5b9a5b")):
        v = np.array([res[f"fa_{a}"][nm]["per_cam_h"] for a in ARMS])
        lo = np.array([res[f"fa_{a}"][nm]["boot95"][0] for a in ARMS])
        hi = np.array([res[f"fa_{a}"][nm]["boot95"][1] for a in ARMS])
        ax[1].bar(x + off, v, 0.36, yerr=[np.maximum(v - lo, 0), np.maximum(hi - v, 0)], color=col,
                  label=f"{nm} FA", capsize=3)
    ax[1].axhline(0.05, ls="--", c="k", lw=0.8)
    ax[1].set_ylabel("FA / camera-hour (676 clean worlds)")
    ax[1].legend(fontsize=8)
    for a_ in ax:
        a_.set_xticks(x, lab, fontsize=8)
    fig.suptitle("H63: uniformed intruder — appearance-role suppression vs corroboration mismatch (simulated sensors)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor
    h54 = yaml.safe_load(Path(cfg["h54_config"]).read_text())
    jobs = [({"mode": "clean", "i": i}, cfg, h54) for i in range(int(cfg["n_clean"]))]
    jobs += [({"mode": "recall", "kind": k, "i": i}, cfg, h54)
             for k in cfg["kinds"] for i in range(int(cfg["n_recall_per_kind"]))]
    with ProcessPoolExecutor(int(cfg["workers"])) as ex:
        res_w = list(ex.map(_job, jobs, chunksize=8))
    res = summarise(res_w, cfg)
    res["config"] = cfg
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    figure(res, out / "fig_h63.png")
    return res


if __name__ == "__main__":
    import sys
    c = yaml.safe_load(Path(sys.argv[1]).read_text())
    r = run(c, Path(sys.argv[2]))
    print(json.dumps({k: v for k, v in r.items() if k != "config"}, indent=1, default=float))
