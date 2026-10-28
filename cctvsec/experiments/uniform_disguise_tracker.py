"""H63b: does the H63 corroboration-mismatch rule survive tracker-fed identities?

Pre-registered in docs/research/32 (H63b). H63 scored the rule on GT identities (H54 noise, no ID
switches). Here identities come from a tracker model: the H59 identity-switch stage (swaps between
people < 2 m apart, hazard calibrated to H24's ByteTrack+OSNet-ImageNet IDSW rate) followed by the
H40b fragmentation/jitter stage, so a track id can carry another body after a swap and a new id after
a break. Role (appearance "guard") and corroboration are keyed by *track id*:

* role      drawn once per track id from the body at the track's first tick (cached, as a tracker would);
* live      badge at this crossing (+/-15 s) AND registered RF within 8 m of the track at the alarm;
* history   the track id was corroborated (badge AND RF) at any earlier crossing of that id.
  Breaks start a new id (history lost); swaps carry history onto the wrong body.

Rule variants on guard-role alarms (non-guard alarms: H53 drop iff badge or RF, every arm):
  C keep; a drop; b keep iff NOT live (H63 rule as-is); s keep iff NOT (live OR history) (sticky);
  g keep iff NOT (live OR history within grace_s) -- the mitigation (short grace window).

    survsim experiment h63b_uniform_tracker
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from . import line_cross as LC
from . import sensor_fusion as SF

ARMS = ("C", "a", "b", "s", "g")
RULES = ("b", "s", "g")  # Holm family
TWINS = SF.H54_TWINS
UNIFORM_KINDS = ("patrol_guard", "incident")


def guard_keep(live: bool, hist_t: list[float], ta: float, grace_s: float) -> dict[str, bool]:
    """Keep decision per arm for a guard-role alarm. hist_t = times the track id was corroborated."""
    prior = [t for t in hist_t if t <= ta + 1e-9]
    recent = any(ta - t <= grace_s for t in prior)
    return {"C": True, "a": False, "b": not live, "s": not (live or bool(prior)),
            "g": not (live or recent)}


def track_roles(tr, kinds: dict, ro: dict, rng: np.random.Generator) -> dict[str, bool]:
    """Role per track id, drawn once from the body on the track at its first tick (sorted ids)."""
    first = tr.sort_values("t", kind="stable").groupby("uid", sort=True).first()
    col = "body" if "body" in first else "base"
    out = {}
    for u, row in first.iterrows():
        kd = "ghost" if row["src"] == "ghost" else kinds.get(str(row[col]), "commuter")
        p = ro["p_guard_given_uniform"] if kd in UNIFORM_KINDS else ro["p_guard_given_other"]
        out[str(u)] = bool(rng.random() < p)
    return out


def fuse_world(w: dict, cfg: dict, h54: dict, h: float, sd: int) -> dict[str, Any]:
    from survsim.sensors.rf import RfConfig, rssi_at
    i, mode, kind = w["i"], w["mode"], w.get("kind")
    ws = int(h54["world_seed"])
    kc = SF.H54_KIND.get(kind or "", (0, 0, 0))[2]
    if mode == "clean":
        meta, df = SF._regen_clean_h54(i, h54)
        kinds, actors, truth = meta["kinds"], [], []
        key = [ws, i, 0]
    else:
        meta, df = SF._regen_recall_h54(i, kind, h54)
        tk = set(h54["twin_kinds"])
        kinds = {u: (n if n in tk else "incident" if u in meta["actors"] else "commuter")
                 for u, n in meta["narratives"].items()}
        actors = list(meta["actors"])
        key = [ws, 100000 + i, kc]
        st = LC._polys(meta["zones"], set(h54["sterile_tags"]))
        truth = []
        for a, t0 in meta["hostile_start"].items():
            g = df[(df["uid"].astype(str) == a) & (df["t"] >= t0 - 1e-9)].sort_values("t")
            if g.empty or not st:
                continue
            zi, _ = LC.zone_state(g["x"].to_numpy(float), g["y"].to_numpy(float), st)
            if (zi >= 0).any():
                truth.append({"t": float(g["t"].to_numpy()[np.argmax(zi >= 0)]), "actor": a})
    nrng = np.random.default_rng([*key, sd] if sd else key)
    df = df[["t", "uid", "x", "y"]].copy()
    df["uid"] = df["uid"].astype(str)
    zones = meta["zones"]
    sterile = LC._polys(zones, set(h54["sterile_tags"]))
    persons = set(df["uid"].unique()) - set((meta.get("true_h") or {}).keys())
    src, n_swap = LC.id_switch(df, h, float(cfg["tracker"]["r_m"]), persons,
                               np.random.default_rng([63, ws, i, kc, sd]))
    tr = LC.add_noise(src, zones, meta["camera_hours"], nrng, h54["noise"], true_h=meta.get("true_h"))
    alarms = SF.alarms_with_tracks(tr, zones, h54, kinds)
    by = {u: g.sort_values("t") for u, g in df.groupby("uid", sort=False)}
    twins = sorted(u for u, k in kinds.items() if k in set(h54["twin_kinds"]) and u in by)
    al_ids = {a[4] for a in alarms}
    trk = {u: g.sort_values("t") for u, g in tr.groupby("uid", sort=False) if u in al_ids}
    est = {u: SF.entries_xy(g["x"].to_numpy(float), g["y"].to_numpy(float), g["t"].to_numpy(float), sterile)
           if sterile else [] for u, g in trk.items()}
    ent = {u: SF.entries_xy(by[u]["x"].to_numpy(float), by[u]["y"].to_numpy(float),
                            by[u]["t"].to_numpy(float), sterile) if sterile else [] for u in twins}
    gl, rf = h54["gate_log"], h54["rf"]
    rc = RfConfig(path_loss_exponent=rf["path_loss_n"], shadowing_sigma_db=rf["shadow_db"])
    rng = np.random.default_rng([int(cfg["seed"]), i, kc])  # sensor streams: identical across tracker arms
    carry = sorted(u for u in twins if rng.random() < rf["p_carry"])
    badges = [(t + rng.normal(0, gl["jitter_s"]), z) for u in twins for t, z, _, _ in ent[u]
              if rng.random() < gl["p_swipe"]]
    adv = {u: (by[u]["t"].to_numpy(float), by[u]["x"].to_numpy(float), by[u]["y"].to_numpy(float)) for u in carry}
    rrng = np.random.default_rng([int(cfg["seed"]), i, kc, 7, sd])
    role = track_roles(tr[tr["uid"].isin(al_ids)], kinds, cfg["role"], rrng) if alarms else {}

    def rf_hit(ta, pos):
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
                if d <= cfg["rf_radius_m"] and rssi_at(d, rf["tx_dbm"], rc, rng) > rf["rssi_min_dbm"]:
                    return True
        return False

    def badge_at(tc, z):
        return any(zz == z and abs(tb - tc) <= cfg["badge_window_s"] for tb, zz in badges)

    hist: dict[str, list[float]] = {}

    def history(u):  # times at which track id u was corroborated at one of its own crossings
        if u not in hist:
            hist[u] = [float(tc) for tc, z, x, y in est.get(u, []) if badge_at(tc, z) and rf_hit(tc, (x, y))]
        return hist[u]

    kept: dict[str, list] = {a: [] for a in ARMS}
    for a in sorted(alarms, key=lambda q: (q[0], q[4])):
        ta, base, u = float(a[0]), a[1], a[4]
        body = a[5] if len(a) > 5 else base
        kd = a[3]
        g = trk[u]
        k = int(np.argmin(np.abs(g["t"].to_numpy(float) - ta)))
        pos = (float(g["x"].iat[k]), float(g["y"].iat[k]))
        cr = SF.crossing_for([(e[0], e[1]) for e in est.get(u, [])], ta)
        badge = cr is not None and badge_at(cr[0], cr[1])
        rfm = rf_hit(ta, pos)
        apos = {}
        for act in actors:
            ag = by.get(act)
            if ag is not None:
                k2 = int(np.argmin(np.abs(ag["t"].to_numpy(float) - ta)))
                apos[act] = (float(ag["x"].iat[k2]), float(ag["y"].iat[k2]))
        row = [ta, base, body, kd, pos, apos]
        if not role.get(u, False):
            if not (badge or rfm):
                for arm in ARMS:
                    kept[arm].append(row)
            continue
        keep = guard_keep(badge and rfm, history(u), ta, float(cfg["grace_s"]))
        for arm in ARMS:
            if keep[arm]:
                kept[arm].append(row)
    return {"mode": mode, "kind": kind, "i": i, "camera_hours": meta["camera_hours"], "truth": truth,
            "kept": kept, "n_swap": int(n_swap), "n_alarms": len(alarms)}


def _job(args):
    w, cfg, h54, hs = args
    out = {"mode": w["mode"], "kind": w.get("kind"), "i": w["i"], "arms": {}}
    for an, h in hs.items():
        out["arms"][an] = [fuse_world(w, cfg, h54, h, sd) for sd in range(int(cfg["tracker"]["n_seeds"]))]
    return out


def _hits(run: dict, arm: str, tol: float, r: float) -> np.ndarray:
    """(events, body-keyed hits, label-keyed hits, position-keyed hits) for one world run."""
    v = np.zeros(4)
    for e in run["truth"]:
        win = [x for x in run["kept"][arm] if e["t"] - 1e-9 <= x[0] <= e["t"] + tol]
        v += [1, any(x[2] == e["actor"] for x in win), any(x[1] == e["actor"] for x in win),
              any(e["actor"] in x[5] and np.hypot(x[4][0] - x[5][e["actor"]][0],
                                                  x[4][1] - x[5][e["actor"]][1]) <= r for x in win)]
    return v


def holm(p: dict[str, float]) -> dict[str, float]:
    ks = sorted(p, key=p.get)
    m, out, run = len(ks), {}, 0.0
    for j, k in enumerate(ks):
        run = max(run, min(1.0, (m - j) * p[k]))
        out[k] = run
    return out


def summarise(res_w: list[dict], cfg: dict) -> dict[str, Any]:
    tol, r = float(cfg["tolerance_s"]), float(cfg["pos_radius_m"])
    ans = list(cfg["tracker"]["arms"])
    rec = sorted([w for w in res_w if w["mode"] == "recall"], key=lambda w: (w["kind"], w["i"]))
    cln = sorted([w for w in res_w if w["mode"] == "clean"], key=lambda w: w["i"])
    rng = np.random.default_rng(int(cfg["boot_seed"]))
    nb = int(cfg["n_boot"])
    br = rng.integers(0, len(rec), (nb, len(rec)))
    bc = rng.integers(0, len(cln), (nb, len(cln)))
    ch = np.array([w["arms"][ans[0]][0]["camera_hours"] for w in cln]) * int(cfg["tracker"]["n_seeds"])
    out: dict[str, Any] = {"n_recall_worlds": len(rec), "n_clean_worlds": len(cln),
                           "clean_cam_h_x_seeds": float(ch.sum()), "arms": {}}
    H = {}  # (an, arm) -> per-world [events, body, label, pos]
    for an in ans:
        swaps = sum(run["n_swap"] for w in res_w for run in w["arms"][an])
        o: dict[str, Any] = {"swap_events": int(swaps), "rules": {}}
        for arm in ARMS:
            M = np.array([sum(_hits(run, arm, tol, r) for run in w["arms"][an]) for w in rec])
            H[(an, arm)] = M
            rr = {}
            for j, nm in ((1, "body"), (2, "label"), (3, "pos")):
                bs = M[br, j].sum(1) / np.maximum(M[br, 0].sum(1), 1)
                rr[nm] = {"recall": float(M[:, j].sum() / M[:, 0].sum()), "hits": int(M[:, j].sum()),
                          "boot95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}
            tw = np.array([sum(sum(1 for x in run["kept"][arm] if x[3] in TWINS) for run in w["arms"][an])
                           for w in cln], float)
            b = tw[bc].sum(1) / ch[bc].sum(1)
            rr["twin_fa"] = {"n": int(tw.sum()), "per_cam_h": float(tw.sum() / ch.sum()),
                             "boot95": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]}
            rr["events"] = int(M[:, 0].sum())
            o["rules"][arm] = rr
        out["arms"][an] = o
    # paired drop gt -> tracker (body-keyed), clip bootstrap; one-sided p for drop > 0; Holm over RULES
    ref, tk = ans[0], ans[-1]
    p, drops = {}, {}
    for arm in RULES:
        A, B = H[(ref, arm)], H[(tk, arm)]
        d = A[br, 1].sum(1) / A[br, 0].sum(1) - B[br, 1].sum(1) / B[br, 0].sum(1)
        pt = float(A[:, 1].sum() / A[:, 0].sum() - B[:, 1].sum() / B[:, 0].sum())
        p[arm] = float((np.sum(d <= 0) + 1) / (nb + 1))
        drops[arm] = {"drop": pt, "boot95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}
    ph = holm(p)
    for arm in RULES:
        drops[arm].update(p_one_sided=p[arm], p_holm=ph[arm])
    out["drop_gt_to_tracker_body"] = drops
    gs = H[(tk, "g")][:, 1].sum() - H[(tk, "s")][:, 1].sum()
    out["decision"] = {
        "b_drop_ge_min_and_sig": drops["b"]["drop"] >= cfg["min_drop"] and ph["b"] < cfg["alpha"],
        "b_twin_fa_le_0.05": out["arms"][tk]["rules"]["b"]["twin_fa"]["per_cam_h"] <= 0.05,
        "s_drop_gt_b_drop": drops["s"]["drop"] > drops["b"]["drop"],
        "g_recovers_over_s": bool(gs > 0),
    }
    out["decision"]["met"] = all(out["decision"].values())
    return out


def figure(res: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ans = list(res["arms"])
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    x = np.arange(len(ARMS))
    lab = ["C", "(a) suppress", "(b) live", "(s) sticky", "(g) grace"]
    cols = ["#3a6ea5", "#c7792b"]
    for j, an in enumerate(ans):
        off = (j - 0.5) * 0.38
        R = res["arms"][an]["rules"]
        v = np.array([R[a]["body"]["recall"] for a in ARMS])
        lo = np.array([R[a]["body"]["boot95"][0] for a in ARMS])
        hi = np.array([R[a]["body"]["boot95"][1] for a in ARMS])
        ax[0].bar(x + off, v, 0.36, yerr=[v - lo, hi - v], color=cols[j], label=f"{an} identities", capsize=3)
        v = np.array([R[a]["twin_fa"]["per_cam_h"] for a in ARMS])
        lo = np.array([R[a]["twin_fa"]["boot95"][0] for a in ARMS])
        hi = np.array([R[a]["twin_fa"]["boot95"][1] for a in ARMS])
        ax[1].bar(x + off, v, 0.36, yerr=[np.maximum(v - lo, 0), np.maximum(hi - v, 0)], color=cols[j],
                  label=f"{an} identities", capsize=3)
    ax[0].set_ylabel("uniformed-intruder recall@10 s (body-keyed)")
    ax[1].set_ylabel("twin FA / camera-hour")
    ax[1].axhline(0.05, ls="--", c="k", lw=0.8)
    for a_ in ax:
        a_.set_xticks(x, lab, fontsize=8)
        a_.legend(fontsize=8)
    fig.suptitle("H63b: corroboration mismatch keyed by track id, GT vs OSNet-calibrated ID switches "
                 "(simulated sensors, 10 seeds)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    t0 = time.time()
    h54 = yaml.safe_load(Path(cfg["h54_config"]).read_text())
    tc = cfg["tracker"]
    h = float(tc["h59_h_bytetrack"]) * float(tc["idsw_osnet"]) / float(tc["idsw_bytetrack"])
    hs = {an: h * float(m) for an, m in tc["arms"].items()}
    ws = [{"mode": "recall", "kind": k, "i": i} for k in cfg["kinds"] for i in range(int(cfg["n_recall_per_kind"]))]
    ws += [{"mode": "clean", "i": i} for i in range(int(cfg["n_clean"]))]
    res_w = []
    with get_context("fork").Pool(int(cfg["workers"])) as pool:
        for n, r in enumerate(pool.imap_unordered(_job, [(w, cfg, h54, hs) for w in ws], chunksize=1), 1):
            res_w.append(r)
            if n % 50 == 0:
                print(f"h63b {n}/{len(ws)} {time.time() - t0:.0f}s", flush=True)
    res = summarise(res_w, cfg)
    res["hazard_per_pair_s"] = hs
    res["wall_s"] = time.time() - t0
    res["config"] = cfg
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    figure(res, out / "fig_h63b.png")
    return res


if __name__ == "__main__":
    import sys
    c = yaml.safe_load(Path(sys.argv[1]).read_text())
    r = run(c, Path(sys.argv[2]))
    print(json.dumps({k: v for k, v in r.items() if k != "config"}, indent=1, default=float))
