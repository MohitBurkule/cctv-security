"""H53: late fusion of the H40b line-cross alarm (arm C) with simulated non-video sensors.

Pre-registered in docs/research/32 (H53). Reads H40b's cached worlds and noisy
arm-C alarms and adds three simulated sensor streams, every parameter of which
is a declared assumption (config h53_sensor_fusion):

* (a) gate access log - authorised twins badge at the gate when they enter;
* (b) RF tag          - twins carry a registered BLE tag (survsim.sensors.rf path loss);
* (c) PIDS            - fence vibration on every non-gate crossing, plus wind nuisance.

Arms: C, C+a (drop on badge), C+b (drop on tag), C+c (keep only on PIDS),
C+abc (drop iff (a or b) and not c). Adversary variants on the recall worlds:
tailgate (a badge just before the intruder, entry through the open gate, no
PIDS) and stolen_tag (the intruder carries a registered tag).

    survsim experiment h53_sensor_fusion
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import line_cross as LC

ARMS = ("C", "C+a", "C+b", "C+c", "C+abc")
VARIANTS = ("base", "tailgate", "stolen_tag")


# ------------------------------------------------------------------ geometry on true tracks

def entries(g: pd.DataFrame, sterile) -> list[tuple[float, int]]:
    """(time, fenced-zone index) of every outside->inside transition on one true track."""
    zi, _ = LC.zone_state(g["x"].to_numpy(float), g["y"].to_numpy(float), sterile)
    ins = zi >= 0
    prev = np.r_[False, ins[:-1]]
    t = g["t"].to_numpy(float)
    return [(float(t[k]), int(zi[k])) for k in np.flatnonzero(ins & ~prev)]


def crossing_for(ent: list[tuple[float, int]], t_alarm: float) -> tuple[float, int] | None:
    """The last entry at or before the alarm."""
    c = [e for e in ent if e[0] <= t_alarm + 1e-9]
    return c[-1] if c else None


# ------------------------------------------------------------------ sensors

def badge_log(twin_entries: dict[str, list], cfg: dict, rng: np.random.Generator) -> list[tuple[float, int]]:
    g = cfg["gate_log"]
    out = []
    for _, ent in sorted(twin_entries.items()):
        for t, z in ent:
            if rng.random() < g["p_swipe"]:
                out.append((t + rng.normal(0, g["jitter_s"]), z))
    return out


def pids_log(breach_entries: dict[str, list], n_zones: int, dur_s: float, t0: float, cfg: dict,
             rng: np.random.Generator) -> list[tuple[float, int]]:
    p = cfg["pids"]
    out = []
    for _, ent in sorted(breach_entries.items()):
        for t, z in ent:
            if rng.random() < p["p_detect"]:
                out.append((t - rng.uniform(*p["lead_s"]), z))
    for _ in range(int(rng.poisson(p["wind_per_zone_h"] * n_zones * dur_s / 3600.0))):
        out.append((t0 + rng.uniform(0, dur_s), int(rng.integers(n_zones))))
    return out


def rf_match(t_alarm: float, pos_alarm: np.ndarray, holders: dict[str, pd.DataFrame], cfg: dict,
             rng: np.random.Generator) -> bool:
    """Any registered-tag advert within +/-window with RSSI (at the alarmed track) above threshold."""
    from survsim.sensors.rf import RfConfig, rssi_at
    r = cfg["rf"]
    rc = RfConfig(path_loss_exponent=r["path_loss_n"], shadowing_sigma_db=r["shadow_db"])
    ts = t_alarm + np.arange(-r["window_s"], r["window_s"] + 1e-9, 1.0 / r["advert_hz"])
    for _, g in sorted(holders.items()):
        tt = g["t"].to_numpy(float)
        if tt[0] > ts[-1] or tt[-1] < ts[0]:
            continue
        for s in ts:
            k = int(np.argmin(np.abs(tt - s)))
            if abs(tt[k] - s) > 0.5 or rng.random() < r["miss_p"]:
                continue
            d = float(np.hypot(g["x"].iat[k] - pos_alarm[0], g["y"].iat[k] - pos_alarm[1]))
            if rssi_at(d, r["tx_dbm"], rc, rng) > r["rssi_min_dbm"]:
                return True
    return False


# ------------------------------------------------------------------ per world

def _load(cfg: dict, w: dict) -> tuple[dict, pd.DataFrame]:
    d = Path(cfg["h40b_dir"])
    p = d / "clean_tracks" / f"clean_{w['i']:05d}" if w["mode"] == "clean" else \
        d / "recall_tracks" / f"{w['kind']}_{w['i']:04d}"
    meta = json.loads(p.with_suffix(".json").read_text())
    df = pd.read_parquet(p.with_suffix(".parquet"))
    df["uid"] = df["uid"].astype(str)
    return meta, df


def fuse_world(w: dict, cfg: dict, dur_clean_s: float) -> dict[str, Any]:
    meta, df = _load(cfg, w)
    sterile = LC._polys(meta["zones"], set(cfg["sterile_tags"]))
    twin_k = set(cfg["twin_kinds"])
    if w["mode"] == "clean":
        kinds = meta.get("kinds", {})
        actors: list[str] = []
        dur = dur_clean_s
    else:
        nar = meta.get("narratives", {})
        kinds = {u: (n if n in twin_k else "incident" if u in meta["actors"] else "commuter")
                 for u, n in nar.items()}
        actors = list(meta["actors"])
        dur = float(df["t"].max() - df["t"].min())
    t0 = float(df["t"].min())
    by = {u: g.sort_values("t") for u, g in df.groupby("uid", sort=False)}
    alarms = w["noisy"][cfg["base_arm"]]
    need = {u for u, k in kinds.items() if k in twin_k} | set(actors) | {a[1] for a in alarms}
    ent = {u: entries(by[u], sterile) if u in by and sterile else [] for u in need}
    twins = sorted(u for u, k in kinds.items() if k in twin_k and u in by)
    code = {"clean": 0, "intrusion": 1, "probe": 2, "climb": 3}[w.get("kind", "clean")]
    out: dict[str, Any] = {}
    for vi, var in enumerate(VARIANTS if w["mode"] == "recall" else ("base",)):
        rng = np.random.default_rng([int(cfg["seed"]), int(w["i"]), code, vi])
        carry = {u for u in twins if rng.random() < cfg["rf"]["p_carry"]}
        badges = badge_log({u: ent[u] for u in twins}, cfg, rng)
        breach = {u: ent[u] for u in actors}
        if var == "tailgate":
            breach = {}
            for u in actors:
                for t, z in ent[u]:
                    badges.append((t - rng.uniform(*cfg["adversary"]["tailgate_lead_s"]), z))
        if var == "stolen_tag":
            carry |= set(actors) & set(by)
        pids = pids_log(breach, max(len(sterile), 1), dur, t0, cfg, rng)
        holders = {u: by[u] for u in sorted(carry)}
        kept: dict[str, list] = {a: [] for a in ARMS}
        flags = []
        gl, pc = cfg["gate_log"], cfg["pids"]
        for a in alarms:
            ta, base = float(a[0]), a[1]
            cr = crossing_for(ent.get(base, []), ta)
            ma = mb = mc = False
            if cr is not None:
                tc, z = cr
                ma = any(zz == z and abs(tb - tc) <= gl["window_s"] for tb, zz in badges)
                mc = any(zz == z and tc - pc["window_before_s"] <= tp <= tc + pc["window_after_s"]
                         for tp, zz in pids)
            if base in by and holders:
                g = by[base]
                k = int(np.argmin(np.abs(g["t"].to_numpy(float) - ta)))
                mb = rf_match(ta, np.array([g["x"].iat[k], g["y"].iat[k]]),
                              holders, cfg, rng)
            keep = {"C": True, "C+a": not ma, "C+b": not mb, "C+c": mc, "C+abc": not ((ma or mb) and not mc)}
            for arm, k_ in keep.items():
                if k_:
                    kept[arm].append(a)
            flags.append([ma, mb, mc])
        out[var] = {"alarms": kept, "flags": flags}
    return {"mode": w["mode"], "kind": w.get("kind"), "i": w["i"], "camera_hours": w["camera_hours"],
            "truth": w["truth"], "fused": out}


def _job(args):
    return fuse_world(*args)


# ------------------------------------------------------------------ scoring

def summarise(res_w: list[dict], cfg: dict) -> dict[str, Any]:
    from .inference import garwood
    nb, seed = int(cfg["n_boot"]), int(cfg["seed"])
    twin_k = set(cfg["twin_kinds"])
    clean = [w for w in res_w if w["mode"] == "clean"]
    rec = [w for w in res_w if w["mode"] == "recall"]
    ch = np.array([w["camera_hours"] for w in clean])
    rng = np.random.default_rng(seed)
    bc = rng.integers(0, len(clean), (nb, len(clean)))
    br = rng.integers(0, len(rec), (nb, len(rec)))
    out: dict[str, Any] = {"clean_cam_h": float(ch.sum()), "n_clean": len(clean), "n_recall": len(rec)}
    c_twin = None
    for arm in ARMS:
        al = [w["fused"]["base"]["alarms"][arm] for w in clean]
        tw = np.array([sum(1 for a in x if a[3] in twin_k) for x in al], float)
        pk = {k: int(sum(1 for x in al for a in x if a[3] == k)) for k in twin_k}
        tot = np.array([len(x) for x in al], float)
        prim = tot - tw
        if arm == "C":
            c_twin = tw
        tb = tw[bc].sum(1) / ch[bc].sum(1)
        rem = 1 - tw[bc].sum(1) / np.maximum(c_twin[bc].sum(1), 1e-9)
        r: dict[str, Any] = {
            "twin_fa": int(tw.sum()), "twin_fa_per_cam_h": float(tw.sum() / ch.sum()),
            "twin_garwood95": list(garwood(int(tw.sum()), ch.sum())),
            "twin_boot95": [float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))],
            "twin_by_kind_per_cam_h": {k: v / ch.sum() for k, v in pk.items()},
            "twin_removed": float(1 - tw.sum() / max(c_twin.sum(), 1e-9)),
            "twin_removed_boot95": [float(np.percentile(rem, 2.5)), float(np.percentile(rem, 97.5))],
            "total_fa_per_cam_h": float(tot.sum() / ch.sum()),
            "primary_fa": int(prim.sum()), "primary_fa_per_cam_h": float(prim.sum() / ch.sum())}
        for var in VARIANTS:
            for tol in cfg["tolerances_s"]:
                sc = []
                for w in rec:
                    ww = {"truth": w["truth"], "camera_hours": w["camera_hours"],
                          "fz": {"x": w["fused"][var]["alarms"][arm]}}
                    sc.append(LC.score_world(ww, "fz", "x", tol))
                sc = np.array(sc, float)
                tp, ev, fp = sc[:, 0], sc[:, 0] + sc[:, 1], sc[:, 2]
                bs = tp[br].sum(1) / np.maximum(ev[br].sum(1), 1)
                r[f"recall_{var}_tol{int(tol)}"] = {
                    "tp": int(tp.sum()), "events": int(ev.sum()), "recall": float(tp.sum() / max(ev.sum(), 1)),
                    "boot95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                    "rec_world_fp": int(fp.sum())}
        out[arm] = r
    f = out["C+abc"]
    tgt = float(cfg["target_twin_fa"]) * 0.1
    ok_fa = f["twin_fa_per_cam_h"] <= tgt
    rc = f["recall_base_tol10"]["recall"]
    ok_r = rc >= float(cfg["target_recall"]) - 1e-12
    out["decision"] = {"twin_fa_ok": bool(ok_fa), "recall_ok": bool(ok_r), "met": bool(ok_fa and ok_r),
                       "robust": bool(ok_fa and ok_r and f["twin_boot95"][1] <= tgt),
                       "recall_loss_vs_C": float(out["C"]["recall_base_tol10"]["recall"] - rc),
                       "secondary_loss_le_0.02": bool(out["C"]["recall_base_tol10"]["recall"] - rc <= 0.02)}
    return out


def table(res: dict) -> str:
    L = [("| arm | twin FA/cam-h [world-boot 95 %] | removed [95 %] | patrol / maint | total clean FA/cam-h | "
          "recall@10 [95 %] | recall@30 | tailgate @10 | stolen_tag @10 |"), "|---|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        r = res[arm]
        b = r["recall_base_tol10"]
        L.append(f"| {arm} | {r['twin_fa_per_cam_h']:.4f} [{r['twin_boot95'][0]:.4f}, {r['twin_boot95'][1]:.4f}] | "
                 f"{100 * r['twin_removed']:.1f} % [{100 * r['twin_removed_boot95'][0]:.1f}, "
                 f"{100 * r['twin_removed_boot95'][1]:.1f}] | "
                 f"{r['twin_by_kind_per_cam_h'].get('patrol_guard', 0):.4f} / "
                 f"{r['twin_by_kind_per_cam_h'].get('maintenance_visit', 0):.4f} | {r['total_fa_per_cam_h']:.4f} | "
                 f"{b['recall']:.3f} [{b['boot95'][0]:.3f}, {b['boot95'][1]:.3f}] | "
                 f"{r['recall_base_tol30']['recall']:.3f} | {r['recall_tailgate_tol10']['recall']:.3f} | "
                 f"{r['recall_stolen_tag_tol10']['recall']:.3f} |")
    L += ["", f"decision: {res['decision']}"]
    return "\n".join(L) + "\n"


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    if cfg.get("h59"):
        return run_h59(cfg, out)
    if cfg.get("h54"):
        return run_h54(cfg, out)
    t0 = time.time()
    h12 = json.loads(Path(cfg["h12_results"]).read_text())["config"]
    dur = float(h12["duration_s"])
    worlds = [json.loads(line) for line in (Path(cfg["h40b_dir"]) / "worlds.jsonl").read_text().splitlines()]
    if cfg.get("limit"):
        worlds = [w for w in worlds if w["mode"] == "recall"][: cfg["limit"]] + \
                 [w for w in worlds if w["mode"] == "clean"][: cfg["limit"]]
    with get_context("fork").Pool(int(cfg.get("workers", 6))) as pool:
        res_w = list(pool.imap(_job, [(w, cfg, dur) for w in worlds], chunksize=4))
    (out / "fused_worlds.jsonl").write_text("\n".join(json.dumps(w) for w in res_w))
    body = summarise(res_w, cfg)
    (out / "table.md").write_text(table(body))
    print(table(body), flush=True)
    body["wall_s"] = round(time.time() - t0, 1)
    return body


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    if cfg.get("h59"):
        return table_h59(res)
    return table_h54(res) if cfg.get("h54") else table(res)


def figure(res: dict[str, Any], path: Path) -> None:
    """fig_h53: twin FA/cam-h (log) and recall@10 per arm, with adversary recall."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    x = np.arange(len(ARMS))
    fa = [res[a]["twin_fa_per_cam_h"] for a in ARMS]
    lo = [res[a]["twin_boot95"][0] for a in ARMS]
    hi = [res[a]["twin_boot95"][1] for a in ARMS]
    a1.bar(x, fa, color="#4a6fa5", yerr=[np.subtract(fa, lo), np.subtract(hi, fa)], capsize=3)
    a1.axhline(0.0488, color="#b04a4a", ls="--", lw=1, label="90 % removal target")
    a1.set_yscale("log")
    a1.set_xticks(x, ARMS)
    a1.set_ylabel("twin FA / camera-hour (clean worlds)")
    a1.legend(frameon=False, fontsize=8)
    w = 0.27
    for k, (var, col) in enumerate((("base", "#4a6fa5"), ("tailgate", "#c9a227"), ("stolen_tag", "#8a8a8a"))):
        r = [res[a][f"recall_{var}_tol10"] for a in ARMS]
        v = [q["recall"] for q in r]
        a2.bar(x + (k - 1) * w, v, w, color=col, label=var,
               yerr=[[q["recall"] - q["boot95"][0] for q in r], [q["boot95"][1] - q["recall"] for q in r]], capsize=2)
    a2.axhline(0.782, color="#b04a4a", ls="--", lw=1, label="arm C 0.782")
    a2.set_xticks(x, ARMS)
    a2.set_ylim(0, 1)
    a2.set_ylabel("recall@10 s (300 recall worlds)")
    a2.legend(frameon=False, fontsize=8, ncol=2)
    fig.suptitle("H53: late fusion of line-cross C with gate log (a), RF tag (b), PIDS (c) — simulated sensors",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


# ====================================================================== H54
# Generated fence-gate tailgate (`fence_tailgate`) + staff_escort twin, and
# alarm->sensor association on the alarm's *estimated* (noisy-track) crossing
# and position, with H53's true-track association kept as the control.

H54_ARMS = ("C", "C+a", "C+b", "C+c", "C+abc", "C+abcg")
MATCHES = ("true", "est")
H54_TWINS = ("patrol_guard", "maintenance_visit", "staff_pair")


def entries_xy(x: np.ndarray, y: np.ndarray, t: np.ndarray, sterile) -> list[tuple[float, int, float, float]]:
    """(t, zone, x, y) of every outside->inside transition of one track (arrays sorted by t)."""
    zi, _ = LC.zone_state(x, y, sterile)
    ins = zi >= 0
    k = np.flatnonzero(ins & ~np.r_[False, ins[:-1]])
    return [(float(t[j]), int(zi[j]), float(x[j]), float(y[j])) for j in k]


def _simulate_pairs(scenario, extra, pairs: list[tuple[str, str]]):
    """AS._simulate, but each staff_escort arrives 1 s after its partner (a pair walks in together)."""
    from survsim.director.world import World

    class _W(World):
        def _generated_people(self):
            return list(extra)

        def _spawn_agents(self):
            super()._spawn_agents()
            at = {a.uid: tt for tt, a in self._pending}
            lead_of = {e: ld for ld, e in pairs}
            self._pending = [(at[lead_of[a.uid]] + 1.0 if lead_of.get(a.uid) in at else tt, a)
                             for tt, a in self._pending]
            self._pending.sort(key=lambda z: z[0])

    w = _W(scenario)
    rows = []
    for _ in range(scenario.n_ticks):
        w.step()
        for a in w.agents.values():
            rows.append((w.t, a.uid, float(a.pos[0]), float(a.pos[1])))
    w.finalise()
    return pd.DataFrame(rows, columns=["t", "uid", "x", "y"]), w


def _gates(w) -> list[list[float]]:
    return [[float(c.gate[0]), float(c.gate[1])] for c in w.fences.components]


def _regen_clean_h54(i: int, cfg: dict) -> tuple[dict, pd.DataFrame]:
    """H40b clean world i (same H12 seed/recipe, same twin/wildlife stream [40, i, 41]) plus staff
    pairs (maintenance_visit worker + staff_escort) from a new stream [54, i, 42]."""
    from survsim.director.population import random_animal, random_person
    from survsim.generator import narrative
    from . import alarm_scale as AS
    rg = cfg["clean_regen"]
    path = Path(rg["cache"]) / f"clean_{i:05d}"
    if path.with_suffix(".json").is_file():
        return json.loads(path.with_suffix(".json").read_text()), pd.read_parquet(path.with_suffix(".parquet"))
    h12 = json.loads(Path(rg["h12_results"]).read_text())["config"]
    seed = int(h12["seed"])
    rng = np.random.default_rng([seed, i, 11])
    sc = AS._compose_valid(AS._site_spec(i, seed, h12, [])).scenario
    sc.population.hero = []
    sc.population.warmup_s = float(h12["warmup_s"])
    rate = float(rng.uniform(*h12["arrivals_per_min"]))
    n = int(rng.poisson(rate * h12["duration_s"] / 60.0))
    people = AS.innocent_people(sc.environment, rng, n, h12["mix"], h12["dur_s"])
    kinds = {p.id: "commuter" for p, _ in people}
    env = sc.environment
    tw = np.random.default_rng([int(cfg["world_seed"]), i, 41])
    hours = float(h12["duration_s"]) / 3600.0
    extra = []
    for j in range(int(tw.poisson(rg["patrol_per_h"] * hours))):
        per = random_person(f"g{j:03d}", tw, role="guard")
        per.intent = narrative.patrol_guard(env, tw)
        kinds[per.id] = "patrol_guard"
        extra.append(per)
    for j in range(int(tw.poisson(rg["maintenance_per_h"] * hours))):
        per = random_person(f"m{j:03d}", tw, role="worker")
        per.intent = narrative.maintenance_visit(env, tw)
        kinds[per.id] = "maintenance_visit"
        extra.append(per)
    for j in range(int(tw.poisson(rg["wildlife_per_h"] * hours))):
        per = random_animal(f"w{j:03d}", tw)
        per.intent = narrative.wildlife(env, tw, dur=float(tw.uniform(*rg["wildlife_dur_s"])))
        kinds[per.id] = "wildlife"
        extra.append(per)
    sp = np.random.default_rng([int(cfg["seed"]), i, 42])
    pairs = []
    if any(z.tag == "restricted" for z in env.zones):
        for j in range(int(sp.poisson(rg["staff_pair_per_h"] * hours))):
            lead = random_person(f"s{j:03d}a", sp, role="worker")
            lead.intent = narrative.maintenance_visit(env, sp)
            src = (lead.intent[0].model_extra or {}).get("from")
            esc = random_person(f"s{j:03d}b", sp, role="worker")
            esc.intent = narrative.staff_escort(env, sp, lead.id, src)
            kinds[lead.id] = kinds[esc.id] = "staff_pair"
            extra += [lead, esc]
            pairs.append((lead.id, esc.id))
    df, w = _simulate_pairs(sc, [p for p, _ in people] + extra, pairs)
    zones = [{"id": z.id, "tag": z.tag, "polygon": [list(p[:2]) for p in z.polygon]} for z in env.zones]
    meta = {"i": i, "name": sc.name, "camera_hours": len(sc.cameras) * sc.duration_s / 3600.0,
            "zones": zones, "kinds": kinds, "gates": _gates(w), "pairs": pairs,
            "true_h": {a.uid: a.height_m for a in w.roster.values() if a.object_class != "person"}}
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path.with_suffix(".parquet"), index=False)
    path.with_suffix(".json").write_text(json.dumps(meta))
    return meta, df


H54_KIND = {"intrusion": (0, ["zone_intrusion"], 1), "probe": (1, ["perimeter_probe"], 2),
            "climb": (2, ["fence_climb"], 3), "tailgate": (3, ["fence_tailgate"], 4)}
HOSTILE_NARR = ("zone_intrusion", "perimeter_probe", "fence_climb", "fence_tailgate")


def _regen_recall_h54(i: int, kind: str, cfg: dict) -> tuple[dict, pd.DataFrame]:
    """H40b recall world (same seeds) or a new fence_tailgate world (seed offset 3)."""
    from survsim.generator.batch import SITE_TYPES
    from . import alarm_scale as AS
    path = Path(cfg["recall_cache"]) / f"{kind}_{i:04d}"
    if path.with_suffix(".json").is_file():
        return json.loads(path.with_suffix(".json").read_text()), pd.read_parquet(path.with_suffix(".parquet"))
    off, inc, _ = H54_KIND[kind]
    base = {"duration_s": cfg["recall"]["duration_s"], "fps": 5}
    j = i if kind == "intrusion" else 6 * i + SITE_TYPES.index("perimeter_site")
    spec = AS._site_spec(j, int(cfg["world_seed"]) * 1000 + off, base, inc)
    scene = AS._compose_valid(spec)
    sc = scene.scenario
    df, w = AS._simulate(sc)
    zones = [{"id": z.id, "tag": z.tag, "polygon": [list(p[:2]) for p in z.polygon]} for z in sc.environment.zones]
    actors = [a.person.id for a in scene.arcs if a.narrative in HOSTILE_NARR]
    start: dict[str, float] = {}
    for e in w.events:
        if e.label.split(".")[0] in ("suspicious", "hostile"):
            for a in e.actors:
                if a in actors:
                    start[a] = min(start.get(a, 1e18), e.t_start)
    meta = {"i": i, "kind": kind, "name": sc.name, "site": spec.site.type,
            "camera_hours": len(sc.cameras) * sc.duration_s / 3600.0, "zones": zones,
            "actors": actors, "hostile_start": start, "gates": _gates(w),
            "narratives": {a.person.id: a.narrative for a in scene.arcs},
            "tailgate_log": [r for r in w.sensor_log if r.get("event") == "tailgate"],
            "true_h": {a.uid: a.height_m for a in w.roster.values() if a.object_class != "person"}}
    path.parent.mkdir(parents=True, exist_ok=True)
    df[["t", "uid", "x", "y"]].to_parquet(path.with_suffix(".parquet"), index=False)
    path.with_suffix(".json").write_text(json.dumps(meta))
    return meta, df[["t", "uid", "x", "y"]]


def alarms_with_tracks(tr: pd.DataFrame, zones, cfg, kinds) -> list[tuple]:
    """LC.world_alarms for the base arm, keeping the alarmed *track* id: (t, base, src, kind, track)."""
    sterile = LC._polys(zones, set(cfg["sterile_tags"]))
    context = LC._polys(zones, set(cfg["context_tags"]))
    out: list[tuple] = []
    if not sterile or tr.empty:
        return out
    zi, depth = LC.zone_state(tr["x"].to_numpy(), tr["y"].to_numpy(), sterile)
    tr = tr.assign(zi=zi, depth=depth).sort_values(["uid", "t"], kind="stable")
    for u, g in tr.groupby("uid", sort=False):
        if (g["zi"].to_numpy() < 0).all():
            continue
        al = LC.track_alarms(g["t"].to_numpy(), g["zi"].to_numpy(), g["depth"].to_numpy(), g["h"].to_numpy(),
                             g["x"].to_numpy(), g["y"].to_numpy(), context, cfg["arms"])
        base, src = g["base"].iat[0], g["src"].iat[0]
        if "body" in g:  # H59: label = claimed identity (scored); kind = body on the track at the alarm
            gt_, gb = g["t"].to_numpy(float), g["body"].to_numpy()
            for tt in al[cfg["base_arm"]]:
                b = str(gb[int(np.argmin(np.abs(gt_ - tt)))])
                kd = "ghost" if src == "ghost" else (kinds or {}).get(b, "commuter")
                out.append((tt, base, src, kd, u, b))
            continue
        kd = "ghost" if src == "ghost" else (kinds or {}).get(base, "commuter")
        out += [(tt, base, src, kd, u) for tt in al[cfg["base_arm"]]]
    return out


def _near_gate(x: float, y: float, gates, r: float) -> bool:
    return any(np.hypot(x - g[0], y - g[1]) <= r for g in gates)


def fuse_world_h54(
    w: dict, cfg: dict, h59: dict | None = None, with_positions: bool = False
) -> dict[str, Any]:
    """H54 fusion of one world. `h59` = {"h": swap hazard per close-pair-second, "seed": noise seed,
    "r_m": swap radius} adds the H59 identity-switch stage (h = 0 and seed 0 reproduce H54).

    `with_positions` (default False, no change to any existing caller/result) additionally
    attaches, to every kept alarm, the estimated track position at alarm time and the true
    body's position at that same instant, plus the true actor's position at each truth event's
    start -- for docs/research/32 H62's position/time scoring, which needs positions that H54/H59's
    own cached `fused_worlds.jsonl` never stored."""
    from survsim.sensors.rf import RfConfig, rssi_at
    i, mode, kind = w["i"], w["mode"], w.get("kind")
    ws = int(cfg["world_seed"])
    if mode == "clean":
        meta, df = _regen_clean_h54(i, cfg)
        kinds = meta["kinds"]
        actors: list[str] = []
        nrng = np.random.default_rng([ws, i, 0])
        truth: list[dict] = []
    else:
        meta, df = _regen_recall_h54(i, kind, cfg)
        nar = meta["narratives"]
        tk = set(cfg["twin_kinds"])
        kinds = {u: (n if n in tk else "incident" if u in meta["actors"] else "commuter") for u, n in nar.items()}
        actors = list(meta["actors"])
        nrng = np.random.default_rng([ws, 100000 + i, H54_KIND[kind][2]])
        sterile0 = LC._polys(meta["zones"], set(cfg["sterile_tags"]))
        truth = []
        for a, t0 in meta["hostile_start"].items():
            g = df[(df["uid"].astype(str) == a) & (df["t"] >= t0 - 1e-9)].sort_values("t")
            if g.empty or not sterile0:
                continue
            zi, _ = LC.zone_state(g["x"].to_numpy(float), g["y"].to_numpy(float), sterile0)
            if (zi >= 0).any():
                truth.append({"t": float(g["t"].to_numpy()[np.argmax(zi >= 0)]), "actor": a})
    df = df[["t", "uid", "x", "y"]].copy()
    df["uid"] = df["uid"].astype(str)
    zones, gates = meta["zones"], meta["gates"]
    sterile = LC._polys(zones, set(cfg["sterile_tags"]))
    n_swap = 0
    src_df = df
    if h59 is not None:
        sd = int(h59.get("seed", 0))
        if sd:
            key = [ws, i, 0] if mode == "clean" else [ws, 100000 + i, H54_KIND[kind][2]]
            nrng = np.random.default_rng([*key, sd])
        persons = set(df["uid"].unique()) - set((meta.get("true_h") or {}).keys())
        src_df, n_swap = LC.id_switch(df, float(h59["h"]), float(h59["r_m"]), persons,
                                      np.random.default_rng([59, ws, i, H54_KIND.get(kind or "", (0, 0, 0))[2], sd]),
                                      cp=h59.get("cp"))
    tr = LC.add_noise(src_df, zones, meta["camera_hours"], nrng, cfg["noise"], true_h=meta.get("true_h"))
    alarms = alarms_with_tracks(tr, zones, cfg, kinds)
    by = {u: g.sort_values("t") for u, g in df.groupby("uid", sort=False)}
    tw_k = set(cfg["twin_kinds"])
    twins = sorted(u for u, k in kinds.items() if k in tw_k and u in by)
    people = sorted(set(twins) | (set(actors) & set(by)))

    def ent_of(g):
        return entries_xy(g["x"].to_numpy(float), g["y"].to_numpy(float), g["t"].to_numpy(float), sterile) \
            if sterile else []
    ent = {u: ent_of(by[u]) for u in set(people) | {a[1] for a in alarms if a[1] in by}}
    trk = {u: g for u, g in tr.groupby("uid", sort=False) if u in {a[4] for a in alarms}}
    est = {u: ent_of(g.sort_values("t")) for u, g in trk.items()}
    gl, pc, gc, rf = cfg["gate_log"], cfg["pids"], cfg["gate_counter"], cfg["rf"]
    rc = RfConfig(path_loss_exponent=rf["path_loss_n"], shadowing_sigma_db=rf["shadow_db"])
    dur = float(df["t"].max() - df["t"].min())
    t0 = float(df["t"].min())
    variants = ("base",) if mode == "clean" or kind == "tailgate" else ("base", "stolen_tag")
    out: dict[str, Any] = {}
    for vi, var in enumerate(variants):
        rng = np.random.default_rng([int(cfg["seed"]), i, H54_KIND.get(kind or "", (0, 0, 0))[2], vi])
        carry = {u for u in twins if rng.random() < rf["p_carry"]}
        if var == "stolen_tag":
            carry |= set(actors) & set(by)
        badges = [(t + rng.normal(0, gl["jitter_s"]), z) for u in twins for t, z, _, _ in ent[u]
                  if rng.random() < gl["p_swipe"]]
        pids = []
        for u in actors:
            for t, z, x, y in ent.get(u, []):
                if not _near_gate(x, y, gates, gc["gate_r_m"]) and rng.random() < pc["p_detect"]:
                    pids.append((t - rng.uniform(*pc["lead_s"]), z))
        for _ in range(int(rng.poisson(pc["wind_per_zone_h"] * max(len(sterile), 1) * dur / 3600.0))):
            pids.append((t0 + rng.uniform(0, dur), int(rng.integers(max(len(sterile), 1)))))
        counted = [(t, z) for u in people for t, z, x, y in ent.get(u, [])
                   if _near_gate(x, y, gates, gc["gate_r_m"]) and rng.random() < gc["p_count"]]
        excess = [(t, z) for t, z in counted
                  if sum(1 for tt, zz in counted if zz == z and abs(tt - t) <= gc["window_s"])
                  > sum(1 for tb, zb in badges if zb == z and abs(tb - t) <= gc["window_s"])]
        holders = {u: by[u] for u in sorted(carry)}
        adv = {u: (g["t"].to_numpy(float), g["x"].to_numpy(float), g["y"].to_numpy(float))
               for u, g in holders.items()}

        def rf_hit(ta, pos, adv=adv, rng=rng):
            ts = ta + np.arange(-rf["window_s"], rf["window_s"] + 1e-9, 1.0 / rf["advert_hz"])
            for u in sorted(adv):
                tt, xx, yy = adv[u]
                if tt[0] > ts[-1] or tt[-1] < ts[0]:
                    continue
                for s_ in ts:
                    k = int(np.argmin(np.abs(tt - s_)))
                    if abs(tt[k] - s_) > 0.5 or rng.random() < rf["miss_p"]:
                        continue
                    if rssi_at(float(np.hypot(xx[k] - pos[0], yy[k] - pos[1])), rf["tx_dbm"], rc, rng) \
                            > rf["rssi_min_dbm"]:
                        return True
            return False

        res: dict[str, dict[str, list]] = {}
        for m in (("est",) if h59 is not None else MATCHES):
            kept: dict[str, list] = {a: [] for a in H54_ARMS}
            for a in alarms:
                ta, base, trk_u = float(a[0]), a[1], a[4]
                if m == "true":
                    cr = crossing_for([(e[0], e[1]) for e in ent.get(base, [])], ta)
                    g = by.get(base)
                else:
                    cr = crossing_for([(e[0], e[1]) for e in est.get(trk_u, [])], ta)
                    g = trk[trk_u]
                ma = mc = mg = False
                if cr is not None:
                    tc, z = cr
                    ma = any(zz == z and abs(tb - tc) <= gl["window_s"] for tb, zz in badges)
                    mc = any(zz == z and tc - pc["window_before_s"] <= tp <= tc + pc["window_after_s"]
                             for tp, zz in pids)
                    mg = any(zz == z and tc - pc["window_before_s"] <= tp <= tc + pc["window_after_s"]
                             for tp, zz in excess)
                mb = False
                if g is not None and adv:
                    tt = g["t"].to_numpy(float)
                    k = int(np.argmin(np.abs(tt - ta)))
                    mb = rf_hit(ta, (float(g["x"].iat[k]), float(g["y"].iat[k])))
                keep = {"C": True, "C+a": not ma, "C+b": not mb, "C+c": mc,
                        "C+abc": not ((ma or mb) and not mc), "C+abcg": not ((ma or mb) and not (mc or mg))}
                row = list(a[:4])
                if with_positions:
                    # est_pos: where the *alarmed track* (possibly mislabelled by an id
                    # switch) reports itself at alarm time. actor_pos_now: where the true
                    # offending actor (`actors`, dynamically tracked, not a frozen
                    # event-start snapshot) actually is at that same instant -- a moving
                    # actor can be several metres from their own event-start position by
                    # the time an alarm fires inside a 10 s tolerance window, so anchoring
                    # to t_start (as `TruthEvent.actor_pos` does) is the wrong reference
                    # for this per-alarm check (docs/research/32 H62 caveat).
                    est_pos = None
                    if g is not None and not g.empty:
                        tt = g["t"].to_numpy(float)
                        k = int(np.argmin(np.abs(tt - ta)))
                        est_pos = (float(g["x"].iat[k]), float(g["y"].iat[k]))
                    actor_pos_now = {}
                    for act in actors:
                        ag = by.get(act)
                        if ag is not None and not ag.empty:
                            tt2 = ag["t"].to_numpy(float)
                            k2 = int(np.argmin(np.abs(tt2 - ta)))
                            actor_pos_now[act] = (float(ag["x"].iat[k2]), float(ag["y"].iat[k2]))
                    body = a[5] if len(a) > 5 else None
                    row = row + [est_pos, actor_pos_now, body]
                for arm, k_ in keep.items():
                    if k_:
                        kept[arm].append(row)
            res[m] = kept
        out[var] = res
    if with_positions:
        for ev in truth:
            g = by.get(ev["actor"])
            ev["pos"] = None
            if g is not None and not g.empty:
                tt = g["t"].to_numpy(float)
                k = int(np.argmin(np.abs(tt - ev["t"])))
                ev["pos"] = (float(g["x"].iat[k]), float(g["y"].iat[k]))
    return {"mode": mode, "kind": kind, "i": i, "camera_hours": meta["camera_hours"], "truth": truth,
            "n_alarms_C": len(alarms), "tailgate_log": meta.get("tailgate_log", []),
            "n_kind": {k: sum(v == k for v in kinds.values()) for k in (*H54_TWINS, "wildlife")},
            "alarms_C": [list(a[:4]) for a in alarms], "fused": out, "n_swap": n_swap}


def _job54(args):
    return fuse_world_h54(*args)


def summarise_h54(res_w: list[dict], cfg: dict) -> dict[str, Any]:
    from .inference import garwood
    nb, seed = int(cfg["n_boot"]), int(cfg["seed"])
    clean = [w for w in res_w if w["mode"] == "clean"]
    base = [w for w in res_w if w["mode"] == "recall" and w["kind"] != "tailgate"]
    tg = [w for w in res_w if w["mode"] == "recall" and w["kind"] == "tailgate"]
    ch = np.array([w["camera_hours"] for w in clean])
    rng = np.random.default_rng(seed)
    bc = rng.integers(0, len(clean), (nb, len(clean)))
    br = rng.integers(0, max(len(base), 1), (nb, len(base)))
    bt = rng.integers(0, max(len(tg), 1), (nb, len(tg)))
    out: dict[str, Any] = {"clean_cam_h": float(ch.sum()), "n_clean": len(clean), "n_recall": len(base),
                           "n_tailgate": len(tg),
                           "n_kind": {k: int(sum(w["n_kind"].get(k, 0) for w in clean)) for k in (*H54_TWINS, "wildlife")},
                           "tailgate_truth_events": sum(len(w["truth"]) for w in tg),
                           "tailgate_logged": sum(len(w["tailgate_log"]) for w in tg),
                           "tailgate_gap_s": [r["gap_s"] for w in tg for r in w["tailgate_log"]]}

    def rec(ws, bi, var, m, arm, tol):
        sc = []
        for w in ws:
            al = w["fused"][var][m][arm] if var in w["fused"] else []
            sc.append(LC.score_world({"truth": w["truth"], "camera_hours": w["camera_hours"], "fz": {"x": al}},
                                     "fz", "x", tol))
        sc = np.array(sc, float).reshape(-1, 3)
        tp, ev = sc[:, 0], sc[:, 0] + sc[:, 1]
        bs = tp[bi].sum(1) / np.maximum(ev[bi].sum(1), 1)
        return {"tp": int(tp.sum()), "events": int(ev.sum()), "recall": float(tp.sum() / max(ev.sum(), 1)),
                "boot95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                "rec_world_fp": int(sc[:, 2].sum())}

    for m in MATCHES:
        c_tw = c_tw53 = None
        for arm in H54_ARMS:
            al = [w["fused"]["base"][m][arm] for w in clean]
            tw = np.array([sum(1 for a in x if a[3] in H54_TWINS) for x in al], float)
            tw53 = np.array([sum(1 for a in x if a[3] in ("patrol_guard", "maintenance_visit")) for x in al], float)
            if arm == "C":
                c_tw, c_tw53 = tw, tw53
            tb = tw[bc].sum(1) / ch[bc].sum(1)
            rem = 1 - tw[bc].sum(1) / np.maximum(c_tw[bc].sum(1), 1e-9)
            tot = np.array([len(x) for x in al], float)
            r: dict[str, Any] = {
                "twin_fa": int(tw.sum()), "twin_fa_per_cam_h": float(tw.sum() / ch.sum()),
                "twin_garwood95": list(garwood(int(tw.sum()), ch.sum())),
                "twin_boot95": [float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))],
                "twin_removed": float(1 - tw.sum() / max(c_tw.sum(), 1e-9)),
                "twin_removed_boot95": [float(np.percentile(rem, 2.5)), float(np.percentile(rem, 97.5))],
                "twin_removed_h53kinds": float(1 - tw53.sum() / max(c_tw53.sum(), 1e-9)),
                "twin_by_kind_per_cam_h": {k: sum(1 for x in al for a in x if a[3] == k) / ch.sum()
                                           for k in H54_TWINS},
                "total_fa_per_cam_h": float(tot.sum() / ch.sum()),
                "primary_fa": int((tot - tw).sum())}
            for tol in cfg["tolerances_s"]:
                r[f"recall_base_tol{int(tol)}"] = rec(base, br, "base", m, arm, tol)
                r[f"recall_tailgate_tol{int(tol)}"] = rec(tg, bt, "base", m, arm, tol)
            r["recall_stolen_tag_tol10"] = rec(base, br, "stolen_tag", m, arm, 10)
            out[f"{m}_{arm}"] = r
    e = out["est_C+abc"]
    loss = out["est_C"]["recall_base_tol10"]["recall"] - e["recall_base_tol10"]["recall"]
    tg_abc = e["recall_tailgate_tol10"]["recall"]
    tg_g = out["est_C+abcg"]["recall_tailgate_tol10"]["recall"]
    ok = {"removal_ge_0.90": e["twin_removed"] >= 0.90, "recall_loss_le_0.03": loss <= 0.03 + 1e-12,
          "tailgate_gate_ge_0.6": tg_g >= 0.6, "tailgate_nogate_lt_0.6": tg_abc < 0.6}
    out["decision"] = {**{k: bool(v) for k, v in ok.items()}, "met": bool(all(ok.values())),
                       "recall_loss_vs_C": float(loss), "tailgate_C+abc": tg_abc, "tailgate_C+abcg": tg_g,
                       "robust_removal": bool(e["twin_removed_boot95"][0] >= 0.90)}
    return out


def table_h54(res: dict) -> str:
    L = [("| match | arm | twin FA/cam-h [boot 95 %] | removed [95 %] | removed (H53 kinds) | recall@10 base [95 %] "
          "| loss vs C | tailgater @10 [95 %] | stolen_tag @10 |"), "|---|---|---|---|---|---|---|---|---|"]
    for m in MATCHES:
        c = res[f"{m}_C"]["recall_base_tol10"]["recall"]
        for arm in H54_ARMS:
            r = res[f"{m}_{arm}"]
            b, t = r["recall_base_tol10"], r["recall_tailgate_tol10"]
            L.append(f"| {m} | {arm} | {r['twin_fa_per_cam_h']:.4f} [{r['twin_boot95'][0]:.4f}, "
                     f"{r['twin_boot95'][1]:.4f}] | {100 * r['twin_removed']:.1f} % "
                     f"[{100 * r['twin_removed_boot95'][0]:.1f}, {100 * r['twin_removed_boot95'][1]:.1f}] | "
                     f"{100 * r['twin_removed_h53kinds']:.1f} % | {b['recall']:.3f} [{b['boot95'][0]:.3f}, "
                     f"{b['boot95'][1]:.3f}] | {c - b['recall']:+.3f} | {t['recall']:.3f} [{t['boot95'][0]:.3f}, "
                     f"{t['boot95'][1]:.3f}] | {r['recall_stolen_tag_tol10']['recall']:.3f} |")
    L += ["", (f"clean {res['n_clean']} worlds {res['clean_cam_h']:.0f} cam-h, agents {res['n_kind']}; "
               f"recall {res['n_recall']}; tailgate worlds {res['n_tailgate']} (truth {res['tailgate_truth_events']}, "
               f"logged tailgates {res['tailgate_logged']})"), f"decision: {res['decision']}"]
    return "\n".join(L) + "\n"


def run_h54(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    t0 = time.time()
    r = cfg["recall"]
    jobs = [({"mode": "recall", "kind": k, "i": i}, cfg) for k in ("tailgate", "intrusion", "probe", "climb")
            for i in range(int(r[f"n_{k}"]))]
    jobs += [({"mode": "clean", "i": i}, cfg) for i in range(int(cfg["n_clean"]))]
    if cfg.get("limit"):
        jobs = [j for j in jobs if j[0]["i"] < int(cfg["limit"])]
    res_w = []
    with get_context("fork").Pool(int(cfg.get("workers", 6))) as pool:
        for n, w in enumerate(pool.imap_unordered(_job54, jobs, chunksize=1), 1):
            res_w.append(w)
            if n % 50 == 0:
                print(f"h54 {n}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    res_w.sort(key=lambda w: (w["mode"], w.get("kind") or "", w["i"]))
    (out / "fused_worlds.jsonl").write_text("\n".join(json.dumps(w) for w in res_w))
    body = summarise_h54(res_w, cfg)
    (out / "table.md").write_text(table_h54(body))
    print(table_h54(body), flush=True)
    body["wall_s"] = round(time.time() - t0, 1)
    return body


def figure_h54(res: dict[str, Any], path: Path) -> None:
    """fig_h54: twin-FA removal and recall (base, tailgater) per arm, true vs estimated matching."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
    x = np.arange(len(H54_ARMS))
    w = 0.38
    for k, (m, col) in enumerate((("true", "#8a8a8a"), ("est", "#4a6fa5"))):
        rr = [res[f"{m}_{a}"] for a in H54_ARMS]
        v = [100 * r["twin_removed"] for r in rr]
        axs[0].bar(x + (k - 0.5) * w, v, w, color=col, label=f"{m} matching",
                   yerr=[[v_ - 100 * r["twin_removed_boot95"][0] for v_, r in zip(v, rr)],
                         [100 * r["twin_removed_boot95"][1] - v_ for v_, r in zip(v, rr)]], capsize=2)
        for ax, key in ((axs[1], "recall_base_tol10"), (axs[2], "recall_tailgate_tol10")):
            q = [r[key] for r in rr]
            ax.bar(x + (k - 0.5) * w, [z["recall"] for z in q], w, color=col, label=f"{m} matching",
                   yerr=[[z["recall"] - z["boot95"][0] for z in q], [z["boot95"][1] - z["recall"] for z in q]],
                   capsize=2)
    axs[0].axhline(90, color="#b04a4a", ls="--", lw=1, label="90 % bar")
    axs[0].set_ylabel("twin FA removed vs C (%)")
    axs[0].set_ylim(0, 105)
    c = res["est_C"]["recall_base_tol10"]["recall"]
    axs[1].axhline(c - 0.03, color="#b04a4a", ls="--", lw=1, label="C − 0.03")
    axs[1].set_ylabel("recall@10 s (300 base worlds)")
    axs[2].axhline(0.6, color="#b04a4a", ls="--", lw=1, label="0.6 bar")
    axs[2].set_ylabel("recall@10 s, generated tailgater")
    for ax in axs:
        ax.set_xticks(x, H54_ARMS, fontsize=8)
        ax.legend(frameon=False, fontsize=7)
    axs[1].set_ylim(0, 1)
    axs[2].set_ylim(0, 1)
    fig.suptitle("H54: fence-gate tailgate + estimated-position fusion (g = gate people counter) — simulated sensors",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


# ====================================================================== H59
# H54 fusion under an identity-switch noise stage calibrated to H24 (docs/research/32 H59).

H59_ARMS = ("benign", "calibrated", "stress")


def _load_world_h54(w: dict, cfg: dict) -> tuple[dict, pd.DataFrame]:
    if w["mode"] == "clean":
        return _regen_clean_h54(w["i"], cfg)
    return _regen_recall_h54(w["i"], w["kind"], cfg)


def exposure_h59(w: dict, cfg: dict) -> dict[str, Any]:
    """Person track-seconds and close-pair-seconds (< r_m) of one world, from true positions."""
    meta, df = _load_world_h54(w, cfg)
    df = df[["t", "uid", "x", "y"]].copy()
    df["uid"] = df["uid"].astype(str)
    persons = set(df["uid"].unique()) - set((meta.get("true_h") or {}).keys())
    cp, track_s, pair_s = LC.close_pairs(df, persons, float(cfg["h59"]["r_m"]))
    return {**w, "track_s": track_s, "pair_s": pair_s, "cp": cp}


def calibrate_h(exps: list[dict], rho: float) -> float:
    """Hazard per close-pair-second so that E[IDSW] / person track-second = rho (2 IDSW per swap)."""
    ts = sum(e["track_s"] for e in exps)
    ps = sum(e["pair_s"] for e in exps)
    return rho * ts / (2.0 * ps) if ps > 0 else 0.0


def fuse_world_h59(w: dict, cfg: dict, hs: dict[str, float]) -> dict[str, Any]:
    e = exposure_h59(w, cfg)
    out = {"mode": w["mode"], "kind": w.get("kind"), "i": w["i"], "track_s": e["track_s"], "arms": {}}
    for arm, h in hs.items():
        runs = []
        for sd in range(int(cfg["h59"]["n_seeds"])):
            r = fuse_world_h54(w, cfg, {"h": h, "seed": sd, "r_m": cfg["h59"]["r_m"], "cp": e["cp"]})
            runs.append({k: r[k] for k in ("camera_hours", "truth", "fused", "n_swap", "n_alarms_C")})
        out["arms"][arm] = runs
    return out


def _job59e(args):
    e = exposure_h59(*args)
    e.pop("cp")
    return e


def _job59(args):
    return fuse_world_h59(*args)


def summarise_h59(res_w: list[dict], cfg: dict) -> dict[str, Any]:
    nb, seed = int(cfg["n_boot"]), int(cfg["h59"]["boot_seed"])
    clean = [w for w in res_w if w["mode"] == "clean"]
    base = [w for w in res_w if w["mode"] == "recall" and w["kind"] != "tailgate"]
    tg = [w for w in res_w if w["mode"] == "recall" and w["kind"] == "tailgate"]
    rng = np.random.default_rng(seed)
    bc = rng.integers(0, len(clean), (nb, len(clean)))
    br = rng.integers(0, max(len(base), 1), (nb, len(base)))
    bt = rng.integers(0, max(len(tg), 1), (nb, len(tg)))
    ts_all = sum(w["track_s"] for w in res_w)
    out: dict[str, Any] = {"n_clean": len(clean), "n_recall": len(base), "n_tailgate": len(tg),
                           "person_track_s": ts_all}

    def rec_arr(ws, arm_n, arm):  # per world: tp, events summed over seeds
        a = np.zeros((len(ws), 2))
        for j, w in enumerate(ws):
            for r in w["arms"][arm_n]:
                s_ = LC.score_world({"truth": r["truth"], "camera_hours": r["camera_hours"],
                                     "fz": {"x": r["fused"]["base"]["est"][arm]}}, "fz", "x", 10)
                a[j] += (s_[0], s_[0] + s_[1])
        return a

    def ci(a, bi):
        v = a[bi].sum(1)
        return v

    for an in cfg["h59"]["arms"]:
        swaps = sum(r["n_swap"] for w in res_w for r in w["arms"][an])
        ns = int(cfg["h59"]["n_seeds"])
        o: dict[str, Any] = {"hazard_per_pair_s": cfg["h59"]["_h"][an], "swap_events": swaps,
                             "idsw_per_track_h": 2.0 * swaps / (ns * ts_all) * 3600.0 if ts_all else 0.0}
        tw_c = None
        rb_c = None
        for arm in H54_ARMS:
            tw = np.array([sum(1 for r in w["arms"][an] for a in r["fused"]["base"]["est"][arm] if a[3] in H54_TWINS)
                           for w in clean], float)
            if arm == "C":
                tw_c = tw
            rem = 1 - ci(tw, bc) / np.maximum(ci(tw_c, bc), 1e-9)
            rb, rt = rec_arr(base, an, arm), rec_arr(tg, an, arm)
            if arm == "C":
                rb_c = rb
            rbs = ci(rb[:, :1], br)[:, 0] / np.maximum(ci(rb[:, 1:], br)[:, 0], 1)
            loss = ci(rb_c[:, :1], br)[:, 0] / np.maximum(ci(rb_c[:, 1:], br)[:, 0], 1) - rbs
            rts = ci(rt[:, :1], bt)[:, 0] / np.maximum(ci(rt[:, 1:], bt)[:, 0], 1)
            pct = (lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))])
            rc = float(rb[:, 0].sum() / max(rb[:, 1].sum(), 1))
            o[arm] = {"twin_fa": int(tw.sum()), "twin_removed": float(1 - tw.sum() / max(tw_c.sum(), 1e-9)),
                      "twin_removed_boot95": pct(rem),
                      "recall_base_tol10": rc, "recall_base_boot95": pct(rbs),
                      "recall_loss_vs_C": float(rb_c[:, 0].sum() / max(rb_c[:, 1].sum(), 1) - rc),
                      "recall_loss_boot95": pct(loss),
                      "recall_tailgate_tol10": float(rt[:, 0].sum() / max(rt[:, 1].sum(), 1)),
                      "recall_tailgate_boot95": pct(rts)}
        out[an] = o
    b, c, s3 = out.get("benign"), out.get("calibrated"), out.get("stress")
    if b and c and s3:
        ok = {"calib_removal_le_0.97": c["C+abc"]["twin_removed"] <= 0.97,
              "stress_removal_le_0.90": s3["C+abc"]["twin_removed"] <= 0.90,
              "calib_recall_loss_ge_0.03": c["C+abc"]["recall_loss_vs_C"] >= 0.03 - 1e-12,
              "calib_tailgate_abcg_lt_0.6": c["C+abcg"]["recall_tailgate_tol10"] < 0.6}
        sens = {leg: {"d_twin_removed": c[leg]["twin_removed"] - b[leg]["twin_removed"],
                      "d_recall": c[leg]["recall_base_tol10"] - b[leg]["recall_base_tol10"],
                      "d_loss_vs_C": c[leg]["recall_loss_vs_C"] - b[leg]["recall_loss_vs_C"],
                      "d_tailgate": c[leg]["recall_tailgate_tol10"] - b[leg]["recall_tailgate_tol10"]}
                for leg in ("C+a", "C+b", "C+c", "C+abcg")}
        most = max(("C+a", "C+b", "C+c"), key=lambda k: abs(sens[k]["d_twin_removed"]) + abs(sens[k]["d_loss_vs_C"]))
        out["decision"] = {**{k: bool(v) for k, v in ok.items()}, "met": bool(all(ok.values())),
                           "leg_sensitivity": sens, "most_sensitive_leg": most}
    return out


def table_h59(res: dict) -> str:
    L = [("| noise arm | IDSW/track-h | fusion arm | twin removed [95 %] | recall@10 [95 %] | loss vs C [95 %] | "
          "tailgater @10 [95 %] |"), "|---|---|---|---|---|---|---|"]
    for an in H59_ARMS:
        if an not in res:
            continue
        o = res[an]
        for arm in H54_ARMS:
            r = o[arm]
            L.append(f"| {an} | {o['idsw_per_track_h']:.1f} | {arm} | {100 * r['twin_removed']:.1f} % "
                     f"[{100 * r['twin_removed_boot95'][0]:.1f}, {100 * r['twin_removed_boot95'][1]:.1f}] | "
                     f"{r['recall_base_tol10']:.3f} [{r['recall_base_boot95'][0]:.3f}, {r['recall_base_boot95'][1]:.3f}] | "
                     f"{r['recall_loss_vs_C']:+.3f} [{r['recall_loss_boot95'][0]:+.3f}, {r['recall_loss_boot95'][1]:+.3f}] | "
                     f"{r['recall_tailgate_tol10']:.3f} [{r['recall_tailgate_boot95'][0]:.3f}, "
                     f"{r['recall_tailgate_boot95'][1]:.3f}] |")
    L += ["", f"decision: {res.get('decision')}"]
    return "\n".join(L) + "\n"


def run_h59(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    t0 = time.time()
    r = cfg["recall"]
    ws = [{"mode": "recall", "kind": k, "i": i} for k in ("tailgate", "intrusion", "probe", "climb")
          for i in range(int(r[f"n_{k}"]))]
    ws += [{"mode": "clean", "i": i} for i in range(int(cfg["n_clean"]))]
    if cfg.get("limit"):
        ws = [w for w in ws if w["i"] < int(cfg["limit"])]
    hc = cfg["h59"]
    with get_context("fork").Pool(int(cfg.get("workers", 6))) as pool:
        exps = list(pool.imap_unordered(_job59e, [(w, cfg) for w in ws], chunksize=2))
        h = calibrate_h(exps, float(hc["rho_idsw_per_track_s"]))
        hs = {an: h * float(m) for an, m in hc["arms"].items()}
        hc["_h"] = hs
        print(f"h59 exposure: track_s {sum(e['track_s'] for e in exps):.0f} pair_s "
              f"{sum(e['pair_s'] for e in exps):.0f} -> h {h:.4f}/pair-s {hs}", flush=True)
        res_w = []
        for n, w in enumerate(pool.imap_unordered(_job59, [(w, cfg, hs) for w in ws], chunksize=1), 1):
            res_w.append(w)
            if n % 50 == 0:
                print(f"h59 {n}/{len(ws)} {time.time() - t0:.0f}s", flush=True)
    res_w.sort(key=lambda w: (w["mode"], w.get("kind") or "", w["i"]))
    with (out / "fused_worlds.jsonl").open("w") as f:
        for w in res_w:
            f.write(json.dumps(w) + "\n")
    body = summarise_h59(res_w, cfg)
    body["exposure"] = {"person_track_s": sum(e["track_s"] for e in exps),
                        "close_pair_s": sum(e["pair_s"] for e in exps), "h_calibrated": h, "h": hs}
    (out / "table.md").write_text(table_h59(body))
    print(table_h59(body), flush=True)
    try:
        figure_h59(body, out / "fig_h59.png")
    except (OSError, ValueError, KeyError) as ex:  # figure must not lose the run
        print("figure failed", ex, flush=True)
    body["wall_s"] = round(time.time() - t0, 1)
    return body


def figure_h59(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
    x = np.arange(len(H54_ARMS))
    wd = 0.27
    cols = {"benign": "#8a8a8a", "calibrated": "#4a6fa5", "stress": "#b04a4a"}
    for k, an in enumerate(H59_ARMS):
        if an not in res:
            continue
        o = res[an]
        lab = f"{an} ({o['idsw_per_track_h']:.0f} IDSW/track-h)"
        for ax, key, bk, sc in ((axs[0], "twin_removed", "twin_removed_boot95", 100),
                                (axs[1], "recall_base_tol10", "recall_base_boot95", 1),
                                (axs[2], "recall_tailgate_tol10", "recall_tailgate_boot95", 1)):
            v = np.array([o[a][key] for a in H54_ARMS]) * sc
            lo = np.array([o[a][bk][0] for a in H54_ARMS]) * sc
            hi = np.array([o[a][bk][1] for a in H54_ARMS]) * sc
            ax.bar(x + (k - 1) * wd, v, wd, color=cols[an], label=lab,
                   yerr=[np.maximum(v - lo, 0), np.maximum(hi - v, 0)], capsize=2)
    axs[0].axhline(97, color="k", ls="--", lw=0.8, label="97 % / 90 % bars")
    axs[0].axhline(90, color="k", ls="--", lw=0.8)
    axs[0].set_ylabel("twin FA removed vs C (%)")
    axs[0].set_ylim(0, 105)
    axs[1].set_ylabel("recall@10 s (300 base worlds)")
    axs[2].axhline(0.6, color="k", ls="--", lw=0.8, label="0.6 bar")
    axs[2].set_ylabel("recall@10 s, generated tailgater")
    for ax in axs:
        ax.set_xticks(x, H54_ARMS, fontsize=8)
        ax.legend(frameon=False, fontsize=7)
    axs[1].set_ylim(0, 1)
    axs[2].set_ylim(0, 1)
    fig.suptitle("H59: H54 fusion under H24-calibrated identity switches (est matching, 10 noise seeds)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
