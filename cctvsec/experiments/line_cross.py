"""H40: sterile-zone line-crossing rule on the H12 clean worlds and intruder worlds.

Pre-registered in docs/research/32 (H40). Arms are cumulative:

* N  naive     - every outside->inside transition (and a track first seen inside).
* A  +gating   - track age and median height at the crossing.
* B  +dir/dwell- inward crossing, penetration depth and continuous dwell inside.
* C  +context  - crossings near gate/queue zones excluded.

Tracks get a declared tracker-noise model (jitter, fragmentation, ghost tracks
with heights) before any rule sees them; scoring is actor-aware with the i-LIDS
timing rule (`cctvsec.eval.alarms.score`).

    python -m cctvsec.experiments.line_cross [--out out/experiments/h40_line_cross]

H40b (config h40b_line_cross): the same four arms and noise model on worlds
regenerated with the fenced simulator (fences.py), crossing intrusions, a
fence_climb recall kind, and patrol/maintenance twins + wildlife added to the
clean worlds from a separate seed stream. Primary clean FA excludes alarms on
the authorised twins (reported per kind); non-person tracks are measured at
their true height (+ the person height_sd) instead of the person prior.

    survsim experiment h40b_line_cross
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LABEL = "intrusion.line_cross"
ARMS = ("N", "A", "B", "C")


# ------------------------------------------------------------------ geometry

def _polys(zones: list[dict], tags) -> list[tuple[str, Any]]:
    from shapely.geometry import Polygon
    return [(z["id"], Polygon(z["polygon"])) for z in zones if z["tag"] in tags and len(z["polygon"]) >= 3]


def zone_state(x: np.ndarray, y: np.ndarray, sterile) -> tuple[np.ndarray, np.ndarray]:
    """(index of the sterile zone containing each point or -1, depth inside it in metres)."""
    import shapely
    zi = np.full(len(x), -1, int)
    depth = np.zeros(len(x))
    for k, (_, p) in enumerate(sterile):
        m = shapely.contains_xy(p, x, y) & (zi < 0)
        if m.any():
            zi[m] = k
            depth[m] = shapely.distance(p.boundary, shapely.points(x[m], y[m]))
    return zi, depth


def near_context(x: float, y: float, context, dist_m: float) -> bool:
    from shapely.geometry import Point
    pt = Point(x, y)
    return any(p.distance(pt) <= dist_m for _, p in context)


# ------------------------------------------------------------------ rules

def track_alarms(t, zi, depth, h, x, y, context, arms_cfg) -> dict[str, list[float]]:
    """Alarm times per arm for one track (arrays sorted by t)."""
    out: dict[str, list[float]] = {a: [] for a in ARMS}
    inside = zi >= 0
    if not inside.any():
        return out
    prev = np.r_[False, inside[:-1]]
    entries = np.flatnonzero(inside & ~prev)
    A, B, C = arms_cfg["A"], arms_cfg["B"], arms_cfg["C"]
    for i in entries:
        out["N"].append(float(t[i]))
        if t[i] - t[0] < A["min_age_s"] or np.median(h[: i + 1]) < A["min_height_m"]:
            continue
        out["A"].append(float(t[i]))
        if i == 0:
            continue                      # never seen outside: not an inward crossing
        j = i
        while j < len(t) and zi[j] == zi[i]:
            if depth[j] >= B["min_depth_m"] and t[j] - t[i] >= B["min_dwell_s"]:
                break
            j += 1
        if j >= len(t) or zi[j] != zi[i]:
            continue
        out["B"].append(float(t[j]))
        if not near_context(float(x[i]), float(y[i]), context, C["context_m"]):
            out["C"].append(float(t[j]))
    return out


# ------------------------------------------------------------------ tracker model

def _true_height(mu: np.ndarray, uids: np.ndarray, starts: np.ndarray, true_h: dict | None,
                 sd: float, rng: np.random.Generator) -> np.ndarray:
    """H40b: a non-person track (wildlife) is measured at its own height, not
    drawn from the person prior. Draws for person tracks are unchanged."""
    if not true_h:
        return mu
    first = uids[starts]
    extra = rng.normal(0, sd, len(first))
    return np.array([true_h[u] + e if u in true_h else m for u, m, e in zip(first, mu, extra)])


def add_noise(df: pd.DataFrame, zones: list[dict], cam_h: float, rng: np.random.Generator,
              nz: dict[str, Any], dt: float = 0.2, true_h: dict | None = None) -> pd.DataFrame:
    """Jitter, fragment, give heights, add ghost tracks. Returns t, uid, base, src, x, y, h."""
    df = df.sort_values(["uid", "t"], kind="stable")
    uid = df["uid"].astype(str).to_numpy()
    t = df["t"].to_numpy(float)
    n = len(df)
    x = df["x"].to_numpy(float) + rng.normal(0, nz["jitter_m"], n)
    y = df["y"].to_numpy(float) + rng.normal(0, nz["jitter_m"], n)
    starts = np.r_[True, uid[1:] != uid[:-1]]
    tid = np.cumsum(starts) - 1
    mu = rng.normal(nz["height_mu"], nz["height_sd"], tid[-1] + 1 if n else 0)
    h = (mu[tid] if n else np.zeros(0)) + rng.normal(0, nz["height_tick_sd"], n)
    if true_h and n:
        mu2 = _true_height(mu, uid, starts, true_h, nz["height_sd"], np.random.default_rng(rng.integers(2**63)))
        h = h - mu[tid] + mu2[tid]
    # fragmentation: a Bernoulli break per tick at rate frag_rate_per_s
    brk = (rng.random(n) < nz["frag_rate_per_s"] * dt) & ~starts
    seg = np.zeros(n, int)
    for s, e in zip(np.flatnonzero(starts), np.r_[np.flatnonzero(starts)[1:], n]):
        seg[s:e] = np.cumsum(brk[s:e])
    tr = pd.DataFrame({"t": t, "uid": [f"{u}#{k}" for u, k in zip(uid, seg)], "base": uid,
                       "src": np.where(seg > 0, "fragment", "person"), "x": x, "y": y, "h": h})
    if "body" in df:  # H59: identity-switched input; keep the physical body under each label
        tr["body"] = df["body"].astype(str).to_numpy()
    # ghosts
    pts = np.array([p for z in zones for p in z["polygon"]], float)
    lo, hi = pts.min(0) - 5, pts.max(0) + 5
    tmax = float(t.max()) if n else 0.0
    tmin = float(t.min()) if n else 0.0
    rows = []
    for g in range(int(rng.poisson(nz["ghost_per_cam_h"] * cam_h))):
        d = rng.uniform(*nz["ghost_dur_s"])
        t0 = round(rng.uniform(tmin, max(tmin, tmax - d)) / dt) * dt
        k = max(1, round(d / dt))
        p0 = rng.uniform(lo, hi)
        ang = rng.uniform(0, 2 * np.pi)
        v = rng.uniform(*nz["ghost_speed"]) * np.array([np.cos(ang), np.sin(ang)])
        hh = rng.uniform(0.2, 0.8) if rng.random() < nz["ghost_wildlife_p"] else rng.uniform(0.3, 2.2)
        tt = t0 + dt * np.arange(k)
        rows.append(pd.DataFrame({"t": tt, "uid": f"ghost{g}", "base": f"ghost{g}", "src": "ghost",
                                  **({"body": f"ghost{g}"} if "body" in df else {}),
                                  "x": p0[0] + v[0] * (tt - t0) + rng.normal(0, nz["jitter_m"], k),
                                  "y": p0[1] + v[1] * (tt - t0) + rng.normal(0, nz["jitter_m"], k),
                                  "h": hh + rng.normal(0, 0.05, k)}))
    return pd.concat([tr, *rows], ignore_index=True) if rows else tr


def close_pairs(df: pd.DataFrame, persons: set, r_m: float) -> tuple[list, float, float]:
    """H59: every (t, uid_a, uid_b) with two people < r_m apart; also person track-seconds and
    close-pair-seconds (dt = median tick)."""
    d = df[df["uid"].astype(str).isin(persons)].sort_values(["t", "uid"], kind="stable")
    if d.empty:
        return [], 0.0, 0.0
    tt = np.unique(d["t"].to_numpy(float))
    dt = float(np.median(np.diff(tt))) if len(tt) > 1 else 0.2
    if r_m <= 0:
        return [], len(d) * dt, 0.0
    from scipy.spatial import cKDTree
    t = d["t"].to_numpy(float)
    u = d["uid"].astype(str).to_numpy()
    tk = np.round(t / dt).astype(np.int64)
    # ticks placed far apart on a third axis, so only same-tick pairs fall within r_m
    pts = np.c_[d["x"].to_numpy(float), d["y"].to_numpy(float), tk * (1e3 * r_m + 1e6)]
    pr = cKDTree(pts).query_pairs(r_m, output_type="ndarray")
    if len(pr):
        pr = np.sort(pr, axis=1)                   # rows are (t, uid)-sorted: a < b keeps uid order
        pr = pr[np.lexsort((pr[:, 1], pr[:, 0]))]
        pr = pr[np.argsort(t[pr[:, 0]], kind="stable")]
    out = [(float(t[a]), u[a], u[b]) for a, b in pr]
    return out, len(d) * dt, len(out) * dt


def id_switch(df: pd.DataFrame, h_per_s: float, r_m: float, persons: set, rng: np.random.Generator,
              cp: list | None = None) -> tuple[pd.DataFrame, int]:
    """H59 identity-switch stage (on true positions, before add_noise). Each close pair (< r_m) swaps
    its two track labels with probability h*dt per tick; from then on label A follows body B and vice
    versa. Returns (df with uid = label and body = true uid, number of swap events)."""
    df = df.copy()
    df["uid"] = df["uid"].astype(str)
    df["body"] = df["uid"]
    if h_per_s <= 0:
        return df, 0
    if cp is None:
        cp, _, _ = close_pairs(df, persons, r_m)
    if not cp:
        return df, 0
    tt = np.unique(df["t"].to_numpy(float))
    dt = float(np.median(np.diff(tt))) if len(tt) > 1 else 0.2
    hit = rng.random(len(cp)) < min(1.0, h_per_s * dt)
    ev = [c for c, k in zip(cp, hit) if k]
    lab = {u: u for u in df["body"].unique()}      # body -> label currently on it
    seq: dict[str, list] = {}                      # body -> [(t_event, label from then on)]
    for te, a, b in ev:
        lab[a], lab[b] = lab[b], lab[a]
        seq.setdefault(a, []).append((te, lab[a]))
        seq.setdefault(b, []).append((te, lab[b]))
    t = df["t"].to_numpy(float)
    body = df["body"].to_numpy()
    label = body.copy()
    for u, chg in seq.items():
        rows = np.flatnonzero(body == u)
        rows = rows[np.argsort(t[rows], kind="stable")]
        k = np.searchsorted(t[rows], np.array([c[0] for c in chg]) - 1e-9, side="left")
        for j, (kk, (_, lb)) in enumerate(zip(k, chg)):
            end = k[j + 1] if j + 1 < len(k) else len(rows)
            label[rows[kk:end]] = lb
    df["uid"] = label
    return df, len(ev)


def clean_tracks(df: pd.DataFrame, nz: dict[str, Any], rng: np.random.Generator,
                 true_h: dict | None = None) -> pd.DataFrame:
    """Noise-free variant: true positions, one track per person, true-ish heights."""
    df = df.sort_values(["uid", "t"], kind="stable")
    uid = df["uid"].astype(str).to_numpy()
    starts = np.r_[True, uid[1:] != uid[:-1]]
    tid = np.cumsum(starts) - 1
    mu = rng.normal(nz["height_mu"], nz["height_sd"], tid[-1] + 1) if len(df) else np.zeros(0)
    if true_h and len(df):
        mu = np.asarray(_true_height(mu, uid, starts, true_h, nz["height_sd"],
                                     np.random.default_rng(rng.integers(2**63))))
    return pd.DataFrame({"t": df["t"].to_numpy(float), "uid": uid, "base": uid, "src": "person",
                         "x": df["x"].to_numpy(float), "y": df["y"].to_numpy(float),
                         "h": mu[tid] if len(df) else np.zeros(0)})


def world_alarms(tr: pd.DataFrame, zones, cfg, kinds: dict | None = None
                 ) -> dict[str, list[tuple[float, str, str, str]]]:
    """Per arm: (t, base uid, track source, population kind of the base uid)."""
    sterile = _polys(zones, set(cfg["sterile_tags"]))
    context = _polys(zones, set(cfg["context_tags"]))
    out: dict[str, list] = {a: [] for a in ARMS}
    if not sterile or tr.empty:
        return out
    zi, depth = zone_state(tr["x"].to_numpy(), tr["y"].to_numpy(), sterile)
    tr = tr.assign(zi=zi, depth=depth).sort_values(["uid", "t"], kind="stable")
    for u, g in tr.groupby("uid", sort=False):
        if (g["zi"].to_numpy() < 0).all():
            continue
        al = track_alarms(g["t"].to_numpy(), g["zi"].to_numpy(), g["depth"].to_numpy(), g["h"].to_numpy(),
                          g["x"].to_numpy(), g["y"].to_numpy(), context, cfg["arms"])
        base, src = g["base"].iat[0], g["src"].iat[0]
        kind = "ghost" if src == "ghost" else (kinds or {}).get(base, "commuter")
        for a, ts in al.items():
            out[a] += [(tt, base, src, kind) for tt in ts]
    return out


# ------------------------------------------------------------------ worlds

TWIN_KINDS = ("patrol_guard", "maintenance_visit")


def _regen_clean(i: int, cfg: dict) -> tuple[dict, pd.DataFrame]:
    """H40b: rebuild H12 clean world i with the fenced simulator (same H12 seed,
    same recipe as tools/loiter_eval.py `_gen_job`), plus patrol/maintenance
    twins and wildlife drawn from a *separate* stream so the commuter
    population is the H12 one."""
    from survsim.core.models import BehaviourSpec as B
    from survsim.director.population import random_animal, random_person
    from survsim.generator import narrative
    from . import alarm_scale as AS
    rg = cfg["clean_regen"]
    d = Path(rg["cache"])
    path = d / f"clean_{i:05d}"
    if path.with_suffix(".json").is_file():
        return json.loads(path.with_suffix(".json").read_text()), pd.read_parquet(path.with_suffix(".parquet"))
    h12 = json.loads(Path(rg["h12_results"]).read_text())["config"]
    seed = int(h12["seed"])
    rng = np.random.default_rng([seed, i, 11])
    spec = AS._site_spec(i, seed, h12, [])
    scene = AS._compose_valid(spec)
    sc = scene.scenario
    sc.population.hero = []
    sc.population.warmup_s = float(h12["warmup_s"])
    rate = float(rng.uniform(*h12["arrivals_per_min"]))
    n = int(rng.poisson(rate * h12["duration_s"] / 60.0))
    people = AS.innocent_people(sc.environment, rng, n, h12["mix"], h12["dur_s"])
    kinds = {p.id: "commuter" for p, _ in people}
    env = sc.environment
    tw = np.random.default_rng([int(cfg["seed"]), i, 41])
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
    _ = B
    df, w = AS._simulate(sc, [p for p, _ in people] + extra)
    zones = [{"id": z.id, "tag": z.tag, "polygon": [list(p[:2]) for p in z.polygon]} for z in env.zones]
    meta = {"i": i, "name": sc.name, "camera_hours": len(sc.cameras) * sc.duration_s / 3600.0,
            "zones": zones, "kinds": kinds,
            "true_h": {a.uid: a.height_m for a in w.roster.values() if a.object_class != "person"},
            "classes": {a.uid: a.object_class for a in w.roster.values() if a.object_class != "person"}}
    path.parent.mkdir(parents=True, exist_ok=True)
    df[["t", "uid", "x", "y"]].to_parquet(path.with_suffix(".parquet"), index=False)
    path.with_suffix(".json").write_text(json.dumps(meta))
    return meta, df[["t", "uid", "x", "y"]]


def _clean_job(args):
    i, cfg = args
    if cfg.get("clean_regen"):
        meta, df = _regen_clean(i, cfg)
    else:
        d = Path(cfg["clean_dir"])
        meta = json.loads((d / f"clean_{i:05d}.json").read_text())
        df = pd.read_parquet(d / f"clean_{i:05d}.parquet", columns=["t", "uid", "x", "y"])
    kinds, th = meta.get("kinds"), meta.get("true_h")
    rng = np.random.default_rng([int(cfg["seed"]), i, 0])
    noisy = world_alarms(add_noise(df, meta["zones"], meta["camera_hours"], rng, cfg["noise"], true_h=th),
                         meta["zones"], cfg, kinds)
    free = world_alarms(clean_tracks(df, cfg["noise"], rng, true_h=th), meta["zones"], cfg, kinds)
    return {"mode": "clean", "i": i, "camera_hours": meta["camera_hours"], "truth": [],
            "noisy": noisy, "free": free,
            "n_kind": {k: sum(v == k for v in (kinds or {}).values())
                       for k in ("commuter", *TWIN_KINDS, "wildlife")}}


def _recall_job(args):
    from . import alarm_scale as AS
    i, kind, cfg, cache = args
    seed = int(cfg["seed"])
    path = Path(cache) / f"{kind}_{i:04d}"
    if path.with_suffix(".json").is_file():
        meta = json.loads(path.with_suffix(".json").read_text())
        df = pd.read_parquet(path.with_suffix(".parquet"))
    else:
        from survsim.generator.batch import SITE_TYPES
        base = {"duration_s": cfg["recall"]["duration_s"], "fps": 5}
        j = i if kind == "intrusion" else 6 * i + SITE_TYPES.index("perimeter_site")
        inc = {"intrusion": ["zone_intrusion"], "probe": ["perimeter_probe"], "climb": ["fence_climb"]}[kind]
        spec = AS._site_spec(j, seed * 1000 + {"intrusion": 0, "probe": 1, "climb": 2}[kind], base, inc)
        scene = AS._compose_valid(spec)
        sc = scene.scenario
        df, w = AS._simulate(sc)
        zones = [{"id": z.id, "tag": z.tag, "polygon": [list(p[:2]) for p in z.polygon]}
                 for z in sc.environment.zones]
        actors = [a.person.id for a in scene.arcs
                  if a.narrative in ("zone_intrusion", "perimeter_probe", "fence_climb")]
        start = {}
        for e in w.events:
            if e.label.split(".")[0] in ("suspicious", "hostile"):
                for a in e.actors:
                    if a in actors:
                        start[a] = min(start.get(a, 1e18), e.t_start)
        meta = {"i": i, "kind": kind, "name": sc.name, "site": spec.site.type,
                "camera_hours": len(sc.cameras) * sc.duration_s / 3600.0, "zones": zones,
                "actors": actors, "hostile_start": start,
                "narratives": {a.person.id: a.narrative for a in scene.arcs},
                "true_h": {a.uid: a.height_m for a in w.roster.values() if a.object_class != "person"}}
        path.parent.mkdir(parents=True, exist_ok=True)
        df[["t", "uid", "x", "y"]].to_parquet(path.with_suffix(".parquet"), index=False)
        path.with_suffix(".json").write_text(json.dumps(meta))
    # truth: first tick inside a sterile zone at/after the hostile phase starts (true positions)
    sterile = _polys(meta["zones"], set(cfg["sterile_tags"]))
    truth = []
    for a, t0 in meta["hostile_start"].items():
        g = df[(df["uid"].astype(str) == a) & (df["t"] >= t0 - 1e-9)].sort_values("t")
        if g.empty or not sterile:
            continue
        zi, _ = zone_state(g["x"].to_numpy(float), g["y"].to_numpy(float), sterile)
        if (zi >= 0).any():
            truth.append({"t": float(g["t"].to_numpy()[np.argmax(zi >= 0)]), "actor": a})
    rng = np.random.default_rng([seed, 100000 + i, {"intrusion": 1, "probe": 2, "climb": 3}[kind]])
    nar = meta.get("narratives", {})
    kinds = {u: (n if n in TWIN_KINDS else "incident" if u in meta["actors"] else "commuter")
             for u, n in nar.items()}
    th = meta.get("true_h")
    noisy = world_alarms(add_noise(df, meta["zones"], meta["camera_hours"], rng, cfg["noise"], true_h=th),
                         meta["zones"], cfg, kinds)
    free = world_alarms(clean_tracks(df, cfg["noise"], rng, true_h=th), meta["zones"], cfg, kinds)
    return {"mode": "recall", "kind": kind, "i": i, "site": meta["site"], "camera_hours": meta["camera_hours"],
            "truth": truth, "n_actors": len(meta["actors"]), "noisy": noisy, "free": free}


# ------------------------------------------------------------------ scoring

def score_world(w: dict, variant: str, arm: str, tol: float):
    from ..eval import alarms as AL
    truth = [AL.TruthEvent(e["t"], e["t"] + tol, LABEL, (e["actor"],)) for e in w["truth"]]
    al = [AL.Alarm(t=a[0], label=LABEL, uid=a[1]) for a in w[variant][arm]]
    s = AL.score(truth, al, camera_hours=w["camera_hours"], tolerance_s=tol, actor_aware=True)
    return s.true_positives, s.false_negatives, s.false_positives


def summarise(worlds: list[dict], cfg: dict) -> dict[str, Any]:
    from .inference import bootstrap_ratio, garwood, rule_of_three
    nb, seed, budget = int(cfg["n_boot"]), int(cfg["seed"]), float(cfg["budget_fa_per_cam_h"])
    clean = [w for w in worlds if w["mode"] == "clean"]
    rec = [w for w in worlds if w["mode"] == "recall"]
    ch = np.array([w["camera_hours"] for w in clean])
    rng = np.random.default_rng(seed)
    boot_c = rng.integers(0, len(clean), (nb, len(clean)))
    boot_r = rng.integers(0, len(rec), (nb, len(rec)))
    res: dict[str, Any] = {"clean_cam_h": float(ch.sum()), "n_clean": len(clean), "n_recall": len(rec),
                           "recall_truth_events": sum(len(w["truth"]) for w in rec),
                           "recall_actors_never_inside": sum(w["n_actors"] - len(w["truth"]) for w in rec)}
    for variant in ("noisy", "free"):
        fa_by_arm = {}
        for arm in ARMS:
            # Primary FA excludes alarms on the authorised patrol/maintenance
            # twins (H40b reports those separately); wildlife stays in.
            fa = np.array([sum(1 for a in w[variant][arm] if len(a) < 4 or a[3] not in TWIN_KINDS)
                           for w in clean], float)
            fa_by_arm[arm] = fa
            k = int(fa.sum())
            lo, hi = garwood(k, ch.sum())
            blo, bhi = bootstrap_ratio(fa, ch, n_boot=nb, seed=seed)
            src: dict[str, int] = {}
            by_kind: dict[str, int] = {}
            for w in clean:
                for a in w[variant][arm]:
                    if len(a) < 4 or a[3] not in TWIN_KINDS:
                        src[a[2]] = src.get(a[2], 0) + 1
                    kd = a[3] if len(a) > 3 else "commuter"
                    by_kind[kd] = by_kind.get(kd, 0) + 1
            twin_fa = {}
            for kd in (*TWIN_KINDS, "wildlife"):
                kk = by_kind.get(kd, 0)
                glo, ghi = garwood(kk, ch.sum())
                twin_fa[kd] = {"fa": kk, "fa_per_cam_h": kk / ch.sum(), "garwood95": [glo, ghi],
                               "n_agents": int(sum(w.get("n_kind", {}).get(kd, 0) for w in clean))}
            r = {"fa": k, "fa_per_cam_h": k / ch.sum(), "garwood95": [lo, hi], "cluster_boot95": [blo, bhi],
                 "x_budget": k / ch.sum() / budget, "rule_of_three": rule_of_three(ch.sum()) if k == 0 else None,
                 "clean_fa_by_source": src, "clean_fa_by_kind": by_kind, "twin_fa": twin_fa,
                 "fa_incl_twins_per_cam_h": sum(by_kind.values()) / ch.sum()}
            for tol in cfg["tolerances_s"]:
                for sub, ws, bi in (("all", rec, boot_r),) + tuple(
                        (kd, [w for w in rec if w["kind"] == kd], None)
                        for kd in ("intrusion", "probe", "climb") if any(w["kind"] == kd for w in rec)):
                    sc = np.array([score_world(w, variant, arm, tol) for w in ws], float).reshape(-1, 3)
                    tp, fn, fp = sc[:, 0], sc[:, 1], sc[:, 2]
                    ev = tp + fn
                    if bi is None:
                        bi = np.random.default_rng(seed).integers(0, len(ws), (nb, len(ws)))
                    bs = tp[bi].sum(1) / np.maximum(ev[bi].sum(1), 1)
                    r[f"recall_{sub}_tol{int(tol)}"] = {
                        "tp": int(tp.sum()), "events": int(ev.sum()), "recall": float(tp.sum() / max(ev.sum(), 1)),
                        "boot95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                        "rec_world_fp": int(fp.sum()),
                        "rec_fa_per_cam_h": float(fp.sum() / sum(w["camera_hours"] for w in ws)),
                        "rec_twin_fa": int(sum(1 for w in ws for a in w[variant][arm]
                                               if len(a) > 3 and a[3] in TWIN_KINDS))}
            res[f"{variant}_{arm}"] = r
        n, c = fa_by_arm["N"], fa_by_arm["C"]
        bn, bc = n[boot_c].sum(1), c[boot_c].sum(1)
        ratio = bn / np.maximum(bc, 1e-9)
        res[f"{variant}_ratio_N_over_C"] = {"point": float(n.sum() / max(c.sum(), 1e-9)),
                                            "boot95": [float(np.percentile(ratio, 2.5)),
                                                       float(np.percentile(ratio, 97.5))]}
    th = cfg["thresholds"]
    nN, rC = res["noisy_N"], res["noisy_C"]["recall_all_tol10"]
    rt = res["noisy_ratio_N_over_C"]
    i_ = nN["x_budget"] >= th["naive_x_budget"] and nN["garwood95"][0] >= th["naive_x_budget"] * budget
    ii = rt["point"] >= th["fa_ratio"]
    iii = rC["recall"] >= th["recall"]
    res["decision"] = {"i_naive_over_10x": bool(i_), "ii_ratio_ge_5": bool(ii), "iii_recall_ge_0.9": bool(iii),
                       "met": bool(i_ and ii and iii),
                       "robust": bool(i_ and ii and iii and rt["boot95"][0] >= th["fa_ratio"]
                                      and rC["boot95"][0] >= th["recall"])}
    if "fa_max" in th:
        # H40b: full rule (C) recall@10 >= recall AND primary clean FA/cam-h <= fa_max.
        fC = res["noisy_C"]
        ok_r, ok_f = rC["recall"] >= th["recall"], fC["fa_per_cam_h"] <= th["fa_max"]
        res["decision_h40b"] = {"recall_ok": bool(ok_r), "fa_ok": bool(ok_f), "met": bool(ok_r and ok_f),
                                "robust": bool(ok_r and ok_f and rC["boot95"][0] >= th["recall"]
                                               and fC["cluster_boot95"][1] <= th["fa_max"])}
    return res


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    t0 = time.time()
    cache = out / "recall_tracks"
    jobs_c = [(i, cfg) for i in range(int(cfg["n_clean"]))]
    jobs_r = [(i, "intrusion", cfg, str(cache)) for i in range(int(cfg["recall"]["n_intrusion"]))] + \
             [(i, "probe", cfg, str(cache)) for i in range(int(cfg["recall"]["n_probe"]))] + \
             [(i, "climb", cfg, str(cache)) for i in range(int(cfg["recall"].get("n_climb", 0)))]
    worlds = []
    with get_context("fork").Pool(int(cfg.get("workers", 8))) as pool:
        for n, w in enumerate(pool.imap_unordered(_recall_job, jobs_r), 1):
            worlds.append(w)
            if n % 50 == 0:
                print(f"recall {n}/{len(jobs_r)} {time.time() - t0:.0f}s", flush=True)
        for n, w in enumerate(pool.imap_unordered(_clean_job, jobs_c, chunksize=4), 1):
            worlds.append(w)
            if n % 100 == 0:
                print(f"clean {n}/{len(jobs_c)} {time.time() - t0:.0f}s", flush=True)
    worlds.sort(key=lambda w: (w["mode"], w.get("kind", ""), w["i"]))
    (out / "worlds.jsonl").write_text("\n".join(json.dumps(w) for w in worlds))
    body = summarise(worlds, cfg)
    body["wall_s"] = round(time.time() - t0, 1)
    return body


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [("| arm | tracks | clean FA | FA/cam-h [Garwood 95 %] | world-boot 95 % | x budget | "
          "recall@10 [95 %] | recall@30 [95 %] | per-kind recall@10 | recall-world FA/cam-h | clean FA by source | "
          "twin FA/cam-h patrol / maint / wildlife |"),
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for variant in ("noisy", "free"):
        for arm in ARMS:
            r = res[f"{variant}_{arm}"]
            a10, a30 = r["recall_all_tol10"], r["recall_all_tol30"]
            L.append(f"| {arm} | {variant} | {r['fa']} | {r['fa_per_cam_h']:.3f} [{r['garwood95'][0]:.3f}, "
                     f"{r['garwood95'][1]:.3f}] | {r['cluster_boot95'][0]:.3f}-{r['cluster_boot95'][1]:.3f} | "
                     f"{r['x_budget']:.0f} | {a10['recall']:.3f} [{a10['boot95'][0]:.3f}, {a10['boot95'][1]:.3f}] | "
                     f"{a30['recall']:.3f} [{a30['boot95'][0]:.3f}, {a30['boot95'][1]:.3f}] | "
                     + " / ".join(f"{kd} {r[f'recall_{kd}_tol10']['recall']:.3f}"
                                  for kd in ("intrusion", "probe", "climb") if f"recall_{kd}_tol10" in r)
                     + f" | {a10['rec_fa_per_cam_h']:.2f} | {r['clean_fa_by_source']} | "
                     + " / ".join(f"{r['twin_fa'][k]['fa_per_cam_h']:.3f}"
                                  for k in ("patrol_guard", "maintenance_visit", "wildlife")) + " |")
    rt, rf = res["noisy_ratio_N_over_C"], res["free_ratio_N_over_C"]
    L += ["", (f"clean cam-h {res['clean_cam_h']:.1f} ({res['n_clean']} worlds); recall worlds {res['n_recall']}, "
               f"truth events {res['recall_truth_events']}, actors never inside a sterile zone "
               f"{res['recall_actors_never_inside']}"),
          (f"FA ratio N/C noisy {rt['point']:.2f} [{rt['boot95'][0]:.2f}, {rt['boot95'][1]:.2f}]; "
           f"noise-free {rf['point']:.2f}"),
          f"decision: {res['decision']}"] + ([f"decision_h40b: {res['decision_h40b']}"]
                                              if "decision_h40b" in res else [])
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    import argparse

    from cctvsec.experiments import load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="h40_line_cross")
    ap.add_argument("--out", default="out/experiments/h40_line_cross")
    ap.add_argument("--n-clean", type=int)
    ap.add_argument("--n-recall", type=int)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    if a.n_clean is not None:
        cfg["n_clean"] = a.n_clean
    if a.n_recall is not None:
        cfg["recall"] = {**cfg["recall"], "n_intrusion": a.n_recall, "n_probe": a.n_recall}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    body = run(cfg, out)
    res = {"experiment": cfg["name"], "hypothesis": cfg["hypothesis"],
           "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
           "finished": time.strftime("%Y-%m-%d %H:%M:%S"), **body}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    (out / "row.md").write_text(markdown_rows(body, cfg))
    print(markdown_rows(body, cfg), flush=True)


if __name__ == "__main__":
    main()
