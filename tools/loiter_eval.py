"""Loiter rule redesign (docs/research/58): regenerate H12 tracks, build a
disjoint training split, and score candidate loiter rules on the H12 worlds.

Worlds are rebuilt with `cctvsec.experiments.alarm_scale`'s own recipe
(`_site_spec`, `_compose_valid`, `innocent_people`, `_simulate`) - imported,
not copied - so the H12 split is the same 676 clean + 300 recall worlds.
`gen` checks each regenerated world against H12's cached dwell_25 alarm times.

    python tools/loiter_eval.py gen   --split h12   # 676 clean + 300 recall
    python tools/loiter_eval.py gen   --split train # seed 58: 150 clean + 300 recall
    python tools/loiter_eval.py feats --split train
    python tools/loiter_eval.py fit                  # tune on train only
    python tools/loiter_eval.py eval  --split h12    # the one registered evaluation
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os

# Round 2 (after the loiter-arc centroid-leak fix) writes to its own tree so the
# round-1 cache stays reproducible: H58_OUT=out/experiments/h58_round2.
OUT = ROOT / os.environ.get("H58_OUT", "out/experiments/h58_loiter_redesign")
H12 = ROOT / "out/experiments/h12_alarm_scale"
SPLITS = {"h12": {"seed": 12, "clean": 676, "recall": 300},
          "train": {"seed": 58, "clean": 150, "recall": 300}}


def split_cfg(split: str) -> dict[str, int]:
    """SPLITS entry; `train_s<N>` is an extra train split with world seed N
    (H23, 58 §8): 150 clean + 300 recall worlds, like `train`."""
    if split in SPLITS:
        return SPLITS[split]
    if split.startswith("train_s") and split[7:].isdigit():
        return {"seed": int(split[7:]), "clean": 150, "recall": 300}
    raise KeyError(split)


def h12_cfg() -> dict[str, Any]:
    return json.loads((H12 / "results.json").read_text())["config"]


# ------------------------------------------------------------------ generation

def _gen_job(args) -> dict[str, Any]:
    from cctvsec.experiments import alarm_scale as AS
    i, cfg, mode, split = args
    path = OUT / "tracks" / split / f"{mode}_{i:05d}.parquet"
    mpath = path.with_suffix(".json")
    if mpath.is_file():
        return json.loads(mpath.read_text())
    t0 = time.time()
    seed = int(cfg["seed"])
    rng = np.random.default_rng([seed, i, 11])
    if mode == "clean":
        spec = AS._site_spec(i, seed, cfg, [])
        scene = AS._compose_valid(spec)
        sc = scene.scenario
        sc.population.hero = []
        sc.population.warmup_s = float(cfg["warmup_s"])
        rate = float(rng.uniform(*cfg["arrivals_per_min"]))
        n = int(rng.poisson(rate * cfg["duration_s"] / 60.0))
        people = AS.innocent_people(sc.environment, rng, n, cfg["mix"], cfg["dur_s"])
        kinds = {p.id: k for p, k in people}
        df, w = AS._simulate(sc, [p for p, _ in people])
    else:
        mix = cfg["recall"]["incidents"][i % len(cfg["recall"]["incidents"])]
        spec = AS._site_spec(i, seed + 1, {**cfg, "duration_s": cfg["recall"]["duration_s"]}, mix)
        scene = AS._compose_valid(spec)
        sc = scene.scenario
        kinds = {a.person.id: a.narrative for a in scene.arcs}
        df, w = AS._simulate(sc)
    env = sc.model_dump(mode="json")["environment"]
    zones = [{"id": z["id"], "tag": z["tag"], "allowed_roles": z.get("allowed_roles") or [],
              "polygon": z["polygon"]} for z in env["zones"]]
    roles = {a.uid: a.spec.role for a in w.roster.values()}
    truth = [{"t_start": e.t_start, "t_end": e.t_end, "actors": list(e.actors), "label": e.label}
             for e in w.events if e.label.startswith("suspicious.loiter")]
    tags = {z["id"]: z["tag"] for z in zones}
    from cctvsec.eval.rules import DwellRule
    d25 = sorted(a.t for _, g in df.groupby("uid", sort=False)
                 for a in DwellRule(threshold_s=25).run(g.sort_values("t"), tags))
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.astype({"x": "float32", "y": "float32", "speed": "float32"})
    for c in ("uid", "zone", "label"):
        out[c] = out[c].astype("category")
    out.to_parquet(path, compression="zstd", index=False)
    meta = {"i": i, "mode": mode, "split": split, "name": sc.name, "cameras": len(sc.cameras),
            "duration_s": sc.duration_s, "camera_hours": len(sc.cameras) * sc.duration_s / 3600.0,
            "zones": zones, "roles": roles, "kinds": kinds, "truth": truth,
            "spawns": [list(p["pos"][:2]) for p in env["spawn_points"]],
            "dwell_25": d25, "seconds": round(time.time() - t0, 1)}
    mpath.write_text(json.dumps(meta))
    return meta


def cmd_gen(split: str, workers: int) -> None:
    from multiprocessing import get_context
    cfg = {**h12_cfg(), "seed": split_cfg(split)["seed"]}
    jobs = [(i, cfg, m, split) for m in ("clean", "recall") for i in range(split_cfg(split)[m])]
    ref = {}
    if split == "h12":
        for line in (H12 / "worlds.jsonl").read_text().splitlines():
            r = json.loads(line)
            ref[(r["mode"], r["i"])] = sorted(a["t"] for a in r["alarms"]["dwell_25"])
    bad = n = 0
    t0 = time.time()
    with get_context("fork").Pool(workers) as pool:
        for meta in pool.imap_unordered(_gen_job, jobs):
            n += 1
            key = (meta["mode"], meta["i"])
            if key in ref and not (len(ref[key]) == len(meta["dwell_25"])
                                   and np.allclose(ref[key], meta["dwell_25"])):
                bad += 1
                print("MISMATCH", key, flush=True)
            if n % 50 == 0:
                print(f"{n}/{len(jobs)} {time.time() - t0:.0f}s mismatches={bad}", flush=True)
    print(f"done {n} worlds, {bad} dwell_25 mismatches vs H12, {time.time() - t0:.0f}s", flush=True)


# ------------------------------------------------------------------ features

def _feat_job(args) -> str:
    from cctvsec.eval.loiter_features import world_feature_table
    split, mode, i = args
    src = OUT / "tracks" / split / f"{mode}_{i:05d}.parquet"
    dst = OUT / "feats" / split / f"{mode}_{i:05d}.parquet"
    if dst.is_file():
        return str(dst)
    meta = json.loads(src.with_suffix(".json").read_text())
    df = pd.read_parquet(src)
    for c in ("uid", "zone", "label"):
        df[c] = df[c].astype(object)
    df["zone"] = df["zone"].where(df["zone"].notna(), None)
    tab = world_feature_table(df, meta["zones"], meta["roles"], meta["spawns"])
    lab = df.set_index(["uid", "t"])["label"]
    tab["label"] = lab.reindex(pd.MultiIndex.from_arrays([tab["uid"], tab["t"]])).to_numpy()
    tab["kind"] = tab["uid"].map(meta["kinds"]).fillna("?")
    pos = np.zeros(len(tab), bool)
    late = np.zeros(len(tab), bool)
    for e in meta["truth"]:
        m = tab["uid"].isin(e["actors"]).to_numpy() & tab["label"].str.startswith("suspicious.loiter").to_numpy()
        dt = tab["t"].to_numpy() - e["t_start"]
        pos |= m & (dt >= 0) & (dt <= 30)
        late |= m & (dt > 30)
    tab["pos"], tab["late"] = pos, late & ~pos
    for c in ("uid", "tag", "zone", "label", "kind"):
        tab[c] = tab[c].astype(str).astype("category")
    num = [c for c in tab.columns if tab[c].dtype == np.float64 and c not in ("t", "ep")]
    tab[num] = tab[num].astype("float32")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tab.to_parquet(dst, compression="zstd", index=False)
    return str(dst)


def _worlds(split: str) -> list[tuple[str, int]]:
    return [(m, i) for m in ("clean", "recall") for i in range(split_cfg(split)[m])]


def cmd_feats(split: str, workers: int) -> None:
    from multiprocessing import get_context
    t0 = time.time()
    with get_context("fork").Pool(workers) as pool:
        for n, _ in enumerate(pool.imap_unordered(_feat_job, [(split, m, i) for m, i in _worlds(split)]), 1):
            if n % 100 == 0:
                print(f"feats {split} {n} {time.time() - t0:.0f}s", flush=True)
    print(f"feats {split} done {time.time() - t0:.0f}s", flush=True)


def load_split(split: str):
    """(tables concatenated with world column, metas by world index)."""
    tabs, metas = [], []
    for w, (m, i) in enumerate(_worlds(split)):
        t = pd.read_parquet(OUT / "feats" / split / f"{m}_{i:05d}.parquet")
        t["w"] = np.int32(w)
        tabs.append(t)
        meta = json.loads((OUT / "tracks" / split / f"{m}_{i:05d}.json").read_text())
        metas.append({k: meta[k] for k in ("i", "mode", "camera_hours", "truth", "kinds", "zones", "roles")})
    tab = pd.concat(tabs, ignore_index=True)
    for c in ("uid", "tag", "zone", "label", "kind"):
        tab[c] = tab[c].astype(str).astype("category")
    # one integer episode key across worlds (rows are contiguous per episode)
    tab["epk"] = pd.factorize(pd.Series(list(zip(tab["w"].to_numpy(), tab["ep"].to_numpy()))))[0]
    return tab, metas


# ------------------------------------------------------------------ scoring

def cap_per_uid(alarms: dict[int, list], k: int | None, uid_pos: int = 2) -> dict[int, list]:
    """H33c: keep only each uid's first `k` alarms per world, in time order
    (alarm tuples start with t; uid at `uid_pos`). k None = unchanged."""
    if k is None:
        return alarms
    out: dict[int, list] = {}
    for w, al in alarms.items():
        seen: dict[str, int] = {}
        keep = []
        for a in sorted(al, key=lambda x: x[0]):
            u = a[uid_pos]
            if seen.get(u, 0) < k:
                seen[u] = seen.get(u, 0) + 1
                keep.append(a)
        out[w] = keep
    return out


def alarms_by_world(rule, tab: pd.DataFrame, max_alarms_per_uid_per_world: int | None = None
                    ) -> dict[int, list[tuple[float, str]]]:
    """Batch `rule.fire` over the concatenated table (same alarms per world).
    `max_alarms_per_uid_per_world` (H33c) caps alarms per visitor; None = one per episode."""
    from cctvsec.eval.loiter_features import first_per_episode
    cond = rule.condition(tab) & ~tab["allowed"].to_numpy(bool)
    idx = first_per_episode(cond, tab["epk"].to_numpy())
    out: dict[int, list] = {}
    for w, t, k, u in zip(tab["w"].to_numpy()[idx], tab["t"].to_numpy()[idx], tab["kind"].to_numpy()[idx],
                          tab["uid"].to_numpy()[idx]):
        out.setdefault(int(w), []).append((float(t), str(k), str(u)))
    return cap_per_uid(out, max_alarms_per_uid_per_world)


def score_split(alarms: dict[int, list], metas: list[dict], seed: int = 58,
                actor_aware: bool = False) -> dict[str, Any]:
    """Alarms are (t, kind[, uid]) per world; `actor_aware` passes uid through."""
    from cctvsec.eval import alarms as A
    from cctvsec.experiments.inference import bootstrap_ratio, garwood, rule_of_three
    lab = "suspicious.loiter"
    res: dict[str, Any] = {}
    for mode in ("default", "ilids_compat"):
        for tol in (30, 10):
            per = []
            for w, m in enumerate(metas):
                truth = [A.TruthEvent(e["t_start"], e["t_end"] or e["t_start"], lab, tuple(e["actors"]))
                         for e in m["truth"]]
                al = [A.Alarm(t=a[0], label=lab, uid=(a[2] if len(a) > 2 else None))
                      for a in alarms.get(w, [])]
                s = A.score(truth, al, camera_hours=m["camera_hours"], tolerance_s=tol,
                            ilids_compat=(mode == "ilids_compat"), actor_aware=actor_aware)
                per.append((m["mode"], s.true_positives, s.false_negatives, s.false_positives,
                            m["camera_hours"], s.latencies_s))
            clean = [p for p in per if p[0] == "clean"]
            rec = [p for p in per if p[0] == "recall"]
            key = f"{mode}_tol{tol}"
            r: dict[str, Any] = {}
            if clean:
                k = int(sum(p[3] for p in clean))
                ch = sum(p[4] for p in clean)
                lo, hi = garwood(k, ch)
                blo, bhi = bootstrap_ratio([p[3] for p in clean], [p[4] for p in clean], seed=seed)
                r.update(fa=k, cam_h=round(ch, 2), fa_per_cam_h=k / ch, garwood95=[lo, hi],
                         cluster_boot95=[blo, bhi], rule_of_three=rule_of_three(ch) if k == 0 else None,
                         x_budget=k / ch / 0.001)
            if rec:
                tp = np.array([p[1] for p in rec], float)
                ev = tp + np.array([p[2] for p in rec], float)
                fp = np.array([p[3] for p in rec], float)
                rng = np.random.default_rng(seed)
                idx = rng.integers(0, len(rec), (2000, len(rec)))
                bs = tp[idx].sum(1) / np.maximum(ev[idx].sum(1), 1)
                bp = tp[idx].sum(1) / np.maximum(tp[idx].sum(1) + fp[idx].sum(1), 1)
                lat = [x for p in rec for x in p[5]]
                r.update(truth=int(ev.sum()), tp=int(tp.sum()), rec_fp=int(fp.sum()),
                         recall=float(tp.sum() / max(ev.sum(), 1)),
                         recall_boot95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                         precision=float(tp.sum() / max(tp.sum() + fp.sum(), 1)),
                         precision_boot95=[float(np.percentile(bp, 2.5)), float(np.percentile(bp, 97.5))],
                         rec_fa_per_cam_h=float(fp.sum() / sum(p[4] for p in rec)),
                         median_latency_s=float(np.median(lat)) if lat else None)
            res[key] = r
    causes: dict[str, int] = {}
    for w, m in enumerate(metas):
        if m["mode"] == "clean":
            for a in alarms.get(w, []):
                k = a[1]
                causes[k] = causes.get(k, 0) + 1
    res["clean_alarms_by_archetype"] = dict(sorted(causes.items(), key=lambda x: -x[1]))
    return res


# ------------------------------------------------------------------ raw-track rules

def _raw_job(args) -> tuple[int, dict[str, list]]:
    """H12 baselines (via alarm_scale's own helper) and C1 variants on 5 Hz tracks."""
    from cctvsec.eval.rules import ZoneDwellRule
    from cctvsec.experiments import alarm_scale as AS
    split, w, mode, i, specs = args
    src = OUT / "tracks" / split / f"{mode}_{i:05d}.parquet"
    meta = json.loads(src.with_suffix(".json").read_text())
    df = pd.read_parquet(src)
    for c in ("uid", "zone", "label"):
        df[c] = df[c].astype(object)
    df["zone"] = df["zone"].where(df["zone"].notna(), None)
    out = {}
    for name, sp in specs.items():
        if sp["kind"] in ("dwell", "path"):
            al = [(a["t"], meta["kinds"].get(a["uid"], "?"), a["uid"])
                  for a in AS._rule_alarms(sp, df, meta["zones"], meta["roles"])]
        else:
            rule = ZoneDwellRule(threshold_s=sp["threshold_s"], exempt_tags=tuple(sp["exempt_tags"]),
                                 exempt_zone_ids=tuple(sp["exempt_zone_ids"]))
            al = [(a.t, meta["kinds"].get(a.uid, "?"), a.uid)
                  for a in rule.run(df, meta["zones"], meta["roles"])]
        out[name] = al
    return w, out


def raw_alarms(split: str, specs: dict, workers: int) -> dict[str, dict[int, list]]:
    from multiprocessing import get_context
    jobs = [(split, w, m, i, specs) for w, (m, i) in enumerate(_worlds(split))]
    res: dict[str, dict[int, list]] = {k: {} for k in specs}
    with get_context("fork").Pool(workers) as pool:
        for w, out in pool.imap_unordered(_raw_job, jobs, chunksize=4):
            for k, v in out.items():
                res[k][w] = v
    return res


H12_RULES = {"dwell_25": {"name": "dwell_25", "kind": "dwell", "threshold_s": 25},
             "dwell_60": {"name": "dwell_60", "kind": "dwell", "threshold_s": 60},
             "path_loiter_25": {"name": "path_loiter_25", "kind": "path", "threshold_s": 25,
                                "radius_m": 4, "reentry_gap_s": 15}}
WAIT_ZONES = ("zone.gateline", "zone.platform", "zone.reception")


def c1_specs() -> dict[str, dict]:
    out = {}
    for th in (25, 40, 60):
        out[f"C1_zone_dwell_{th}"] = {"kind": "zone_dwell", "threshold_s": th, "exempt_tags": ["queue"],
                                      "exempt_zone_ids": []}
        out[f"C1_zone_dwell_{th}_waitzones"] = {"kind": "zone_dwell", "threshold_s": th,
                                                "exempt_tags": ["queue"], "exempt_zone_ids": list(WAIT_ZONES)}
    return out


# ------------------------------------------------------------------ candidates

LOG1P = ("clock", "disp10", "disp30", "path30", "rms30", "group", "dist_entrance", "revisits60")
GATE_TAGS = {"any": None, "gate": ("gate",), "watch": ("gate", "restricted", "perimeter_fence")}


def c2_grid():
    from cctvsec.eval.rules import DisplacementLoiterRule
    for th in (10, 15, 20, 25):
        for hi in (1.0, 0.5, 0.2, 0.05):
            for mm in (0.0, 0.5, 0.8):
                for gname, g in GATE_TAGS.items():
                    yield (f"C2_disp_T{th}_stat<={hi}_mov>={mm}_{gname}",
                           DisplacementLoiterRule(threshold_s=th, stat_hi=hi, min_moving=mm, zone_tags=g))


def c3_grid():
    from cctvsec.eval.rules import RevisitRule
    for k in (1, 2, 3, 4):
        for mc in (5, 10, 20):
            for gname, g in GATE_TAGS.items():
                yield f"C3_revisit_k{k}_clock>={mc}_{gname}", RevisitRule(min_revisits=k, min_clock_s=mc, zone_tags=g)


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 30):
    """L2 logistic regression by IRLS on standardised X, class-balanced weights."""
    mu, sd = X.mean(0), X.std(0)
    sd[sd < 1e-9] = 1.0
    Z = np.column_stack([(X - mu) / sd, np.ones(len(X))])
    sw = np.where(y == 1, 0.5 / max(y.mean(), 1e-9), 0.5 / max(1 - y.mean(), 1e-9))
    beta = np.zeros(Z.shape[1])
    R = l2 * np.eye(Z.shape[1])
    R[-1, -1] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(Z @ beta, -30, 30)))
        W = sw * p * (1 - p)
        g = Z.T @ (sw * (p - y)) + R @ beta
        H = (Z * W[:, None]).T @ Z + R
        step = np.linalg.solve(H, g)
        beta -= step
        if np.abs(step).max() < 1e-7:
            break
    return beta[:-1], float(beta[-1]), mu, sd


def learned_rule(tab: pd.DataFrame, feats: tuple[str, ...], seed: int = 58, max_neg: int = 1_500_000):
    from cctvsec.eval.rules import LearnedLoiterRule
    use = ~tab["late"].to_numpy(bool)
    y = tab["pos"].to_numpy(bool)[use].astype(float)
    X = np.array(tab.loc[use, list(feats)].to_numpy(float), copy=True)
    for j, f in enumerate(feats):
        if f in LOG1P:
            X[:, j] = np.log1p(np.maximum(X[:, j], 0))
    rng = np.random.default_rng(seed)
    neg = np.flatnonzero(y == 0)
    if len(neg) > max_neg:
        keep = np.r_[np.flatnonzero(y == 1), rng.choice(neg, max_neg, replace=False)]
        X, y = X[keep], y[keep]
    w, b, mu, sd = fit_logistic(X, y)
    return LearnedLoiterRule(weights=tuple(map(float, w)), bias=b, mean=tuple(map(float, mu)),
                             std=tuple(map(float, sd)), features=tuple(feats),
                             log1p=tuple(f for f in feats if f in LOG1P))


def _key(res):
    r = res["default_tol30"]
    return r["fa_per_cam_h"], r["recall"]


def cmd_fit(workers: int) -> None:
    """Tune every candidate on the train split only; write selection.json."""
    import dataclasses

    from cctvsec.eval.loiter_features import FEATURES
    from cctvsec.eval.rules import AllOfRule
    t0 = time.time()
    tab, metas = load_split("train")
    print(f"train table {tab.shape} {time.time() - t0:.0f}s pos={int(tab['pos'].sum())}", flush=True)
    rows = []

    def ev(name, rule, family, spec=None):
        r = score_split(alarms_by_world(rule, tab), metas)
        fa, rc = _key(r)
        rows.append({"name": name, "family": family, "fa_per_cam_h": fa, "recall": rc,
                     "precision": r["default_tol30"]["precision"], "rule": spec or _spec(rule)})
        return fa, rc

    for name, rule in c2_grid():
        ev(name, rule, "C2")
    for name, rule in c3_grid():
        ev(name, rule, "C3")
    print(f"C2/C3 grid done {time.time() - t0:.0f}s", flush=True)
    raw = raw_alarms("train", c1_specs(), workers)
    for name, al in raw.items():
        r = score_split(al, metas)
        fa, rc = _key(r)
        spec = {**H12_RULES, **c1_specs()}[name]
        rows.append({"name": name, "family": "C1" if name.startswith("C1") else "H12",
                     "fa_per_cam_h": fa, "recall": rc, "precision": r["default_tol30"]["precision"],
                     "rule": {"class": "raw", **spec}})
    print(f"raw rules done {time.time() - t0:.0f}s", flush=True)
    feat_sets = {"all": tuple(FEATURES), "no_entrance": tuple(f for f in FEATURES if f != "dist_entrance"),
                 "kinematic_only": tuple(f for f in FEATURES if not f.startswith("tag_") and f != "dist_entrance")}
    best_c2 = min((r for r in rows if r["family"] == "C2" and r["recall"] >= 0.85),
                  key=lambda r: r["fa_per_cam_h"], default=None)
    for fname, feats in feat_sets.items():
        base = learned_rule(tab, feats)
        p = base.score(tab)
        for mc in (5.0, 10.0, 15.0):
            for th in (0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999):
                rule = dataclasses.replace(base, theta=th, min_clock_s=mc)
                ev(f"C4_logit_{fname}_th{th}_clock>={mc}", rule, "C4")
                if best_c2 is not None and fname == "all":
                    g = _build(best_c2["rule"])
                    ev(f"C5_logit_{fname}_th{th}_clock>={mc}_AND_{best_c2['name']}",
                       AllOfRule(rules=(rule, g)), "C5")
        print(f"C4 {fname} done {time.time() - t0:.0f}s; p range {p.min():.3g}-{p.max():.3g}", flush=True)
    # C5: displacement AND revisit
    c3s = [r for r in rows if r["family"] == "C3" and r["recall"] >= 0.85]
    c2s = [r for r in rows if r["family"] == "C2" and r["recall"] >= 0.85]
    for a in sorted(c2s, key=lambda r: r["fa_per_cam_h"])[:5]:
        for b in sorted(c3s, key=lambda r: r["fa_per_cam_h"])[:5]:
            ev(f"C5_{a['name']}_AND_{b['name']}", AllOfRule(rules=(_build(a["rule"]), _build(b["rule"]))), "C5")
    ok = [r for r in rows if r["recall"] >= 0.85]
    best_by_family = {}
    for r in sorted(ok, key=lambda r: (r["fa_per_cam_h"], -r["recall"])):
        best_by_family.setdefault(r["family"], r)
    shipped = min(ok, key=lambda r: (r["fa_per_cam_h"], -r["recall"])) if ok else None
    sel = {"selected_on": "train (seed 58/59)", "constraint": "train recall@30s default >= 0.85",
           "shipped": shipped, "best_by_family": best_by_family,
           "grid": sorted(rows, key=lambda r: r["fa_per_cam_h"]),
           "train": {"clean_cam_h": sum(m["camera_hours"] for m in metas if m["mode"] == "clean"),
                     "truth_events": sum(len(m["truth"]) for m in metas)},
           "wall_s": round(time.time() - t0, 1)}
    (OUT / "selection.json").write_text(json.dumps(sel, indent=1, default=float))
    for f, r in best_by_family.items():
        print(f, r["name"], round(r["fa_per_cam_h"], 4), round(r["recall"], 3), flush=True)
    print("SHIPPED", shipped and shipped["name"], flush=True)


def _spec(rule) -> dict:
    import dataclasses
    d = {"class": type(rule).__name__}
    for f in dataclasses.fields(rule):
        v = getattr(rule, f.name)
        if f.name == "gate":
            v = _spec(v) if v is not None else None
        elif f.name == "rules":
            v = [_spec(x) for x in v]
        elif isinstance(v, tuple):
            v = list(v)
        d[f.name] = v
    return d


def _build(spec: dict):
    from cctvsec.eval import rules as R
    spec = dict(spec)
    cls = getattr(R, spec.pop("class"))
    if "gate" in spec and spec["gate"] is not None:
        spec["gate"] = _build(spec["gate"])
    if "rules" in spec:
        spec["rules"] = tuple(_build(x) for x in spec["rules"])
    return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in spec.items()})


# ------------------------------------------------------------------ evaluation

def cmd_eval(workers: int) -> None:
    """Score the train-selected rules once on the H12 worlds."""
    t0 = time.time()
    sel = json.loads((OUT / "selection.json").read_text())
    tab, metas = load_split("h12")
    clean_h = sum(m["camera_hours"] for m in metas if m["mode"] == "clean")
    print(f"h12 table {tab.shape} {time.time() - t0:.0f}s", flush=True)
    cands = {"SHIPPED " + sel["shipped"]["name"]: sel["shipped"]}
    for fam, r in sel["best_by_family"].items():
        cands.setdefault(f"best {fam} " + r["name"], r)
    raw_specs = {**H12_RULES, **c1_specs()}
    raw = raw_alarms("h12", raw_specs, workers)
    print(f"raw done {time.time() - t0:.0f}s", flush=True)
    results = {}
    for name, al in raw.items():
        results[name] = {"family": "C1" if name.startswith("C1") else "H12", **score_split(al, metas)}
    for name, r in cands.items():
        if r["rule"].get("class") == "raw":
            continue
        results[name] = {"family": r["family"], "train": {"fa_per_cam_h": r["fa_per_cam_h"], "recall": r["recall"]},
                         "rule": r["rule"], **score_split(alarms_by_world(_build(r["rule"]), tab), metas)}
    # Ceilings. (a) label oracle: alarm at each Director loiter episode start.
    oracle = {}
    for w, m in enumerate(metas):
        oracle[w] = [(e["t_start"], "loiter", e["actors"][0] if e["actors"] else None) for e in m["truth"]]
    results["ceiling_label_oracle"] = {"family": "ceiling", **score_split(oracle, metas)}
    twins = twin_rates(tab, metas, clean_h)
    out = {"experiment": "h58_loiter_redesign", "preregistration_commit": "0c0976f",
           "selection": {k: sel[k] for k in ("selected_on", "constraint", "shipped", "best_by_family")},
           "h12_clean_cam_h": clean_h, "results": results, "twins": twins,
           "wall_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float))
    (OUT / "results.md").write_text(markdown(out))
    print(markdown(out), flush=True)


def twin_rates(tab, metas, clean_h) -> dict:
    """(b) kinematic twins: clean hard-negative dwell episodes by kind and the
    zone tag of their first dwell tick. Smoke breaks are `Loiter` subclasses
    (same pace, same 3 m radius), so those in gate zones are the floor."""
    from cctvsec.experiments.inference import garwood
    lab = tab["label"].astype(str)
    clean_w = [w for w, m in enumerate(metas) if m["mode"] == "clean"]
    first = (tab[lab.str.startswith("normal.") & (lab != "normal.transit") & (tab["kind"] != "transit")
                 & tab["w"].isin(clean_w)]
             .groupby(["w", "uid"], observed=True)[["kind", "tag"]].first())
    twins = {}
    for kind, g in first.groupby("kind", observed=True):
        twins[str(kind)] = {"episodes": len(g), "per_cam_h": len(g) / clean_h,
                            "by_tag": g["tag"].astype(str).value_counts().to_dict()}
    sm = twins.get("smoke_break", {"by_tag": {}})
    for tagset in (("gate",), ("gate", "restricted", "perimeter_fence")):
        k = sum(v for t, v in sm["by_tag"].items() if t in tagset)
        lo, hi = garwood(k, clean_h)
        twins[f"smoke_break_in_{'+'.join(tagset)}"] = {"episodes": k, "per_cam_h": k / clean_h,
                                                       "garwood95": [lo, hi]}
    return twins


def cmd_twins() -> None:
    out = json.loads((OUT / "results.json").read_text())
    tab, metas = load_split("h12")
    out["twins"] = twin_rates(tab, metas, out["h12_clean_cam_h"])
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float))
    (OUT / "results.md").write_text(markdown(out))


def markdown(out: dict) -> str:
    L = [("| rule | family | FA (clean) | FA/cam-h | Garwood 95 % | world-boot 95 % | x budget | "
          "recall@30 [95 %] | precision@30 [95 %] | recall@10 | ilids FA/cam-h | median lat s | "
          "train FA/cam-h, recall |"),
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in sorted(out["results"].items(), key=lambda kv: kv[1]["default_tol30"]["fa_per_cam_h"]):
        d, i, d10 = r["default_tol30"], r["ilids_compat_tol30"], r["default_tol10"]
        tr = r.get("train")
        trs = f"{tr['fa_per_cam_h']:.4f}, {tr['recall']:.3f}" if tr else ""
        L.append(f"| {name} | {r['family']} | {d['fa']} | {d['fa_per_cam_h']:.4f} | "
                 f"{d['garwood95'][0]:.4f}-{d['garwood95'][1]:.4f} | {d['cluster_boot95'][0]:.4f}-"
                 f"{d['cluster_boot95'][1]:.4f} | {d['x_budget']:.0f} | {d['recall']:.3f} "
                 f"[{d['recall_boot95'][0]:.3f}, {d['recall_boot95'][1]:.3f}] | {d['precision']:.3f} "
                 f"[{d['precision_boot95'][0]:.3f}, {d['precision_boot95'][1]:.3f}] | {d10['recall']:.3f} | "
                 f"{i['fa_per_cam_h']:.4f} | {d['median_latency_s']} | "
                 f"{trs} |")
    L += ["", "clean alarms by archetype:"]
    for name, r in out["results"].items():
        L.append(f"- {name}: {r['clean_alarms_by_archetype']}")
    L += ["", "hard-negative episodes (clean, by kind / starting zone tag):"]
    for k, v in out["twins"].items():
        L.append(f"- {k}: {v}")
    return "\n".join(L) + "\n"



# ------------------------------------------------------------------ round 2

R1 = ROOT / "out/experiments/h58_loiter_redesign"


def cmd_round2(workers: int) -> None:
    """docs/research/58 "Round 2 after simulator fixes" (pre-registered there).

    Needs `gen`+`feats` for both splits under H58_OUT. Retrains C4 on the
    regenerated train split (round-1 shipped feature set, no dist_entrance;
    same theta x clock grid and train-recall >= 0.85 selection as round 1),
    then scores dwell_25, dwell_60, round-1 C2 (spec frozen), retrained C4,
    round-1 C4 (weights frozen, diagnostic) and the label oracle on the
    regenerated H12 worlds, window-only and actor_aware."""
    import dataclasses

    from cctvsec.eval.loiter_features import FEATURES
    assert OUT != R1, "set H58_OUT so round 2 does not overwrite round 1"
    t0 = time.time()
    sel1 = json.loads((R1 / "selection.json").read_text())
    c4_r1 = sel1["shipped"]
    c2_r1 = sel1["best_by_family"]["C2"]
    feats = tuple(f for f in FEATURES if f != "dist_entrance")
    assert tuple(c4_r1["rule"]["features"]) == feats
    tab, metas = load_split("train")
    base = learned_rule(tab, feats)
    grid = []
    for mc in (5.0, 10.0, 15.0):
        for th in (0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999):
            rule = dataclasses.replace(base, theta=th, min_clock_s=mc)
            fa, rc = _key(score_split(alarms_by_world(rule, tab), metas))
            grid.append({"theta": th, "min_clock_s": mc, "fa_per_cam_h": fa, "recall": rc, "rule": _spec(rule)})
    ok = [g for g in grid if g["recall"] >= 0.85]
    c4 = min(ok, key=lambda g: (g["fa_per_cam_h"], -g["recall"]))
    print(f"train refit: theta={c4['theta']} clock>={c4['min_clock_s']} "
          f"FA={c4['fa_per_cam_h']:.4f} recall={c4['recall']:.3f} {time.time() - t0:.0f}s", flush=True)
    del tab
    tab, metas = load_split("h12")
    clean_h = sum(m["camera_hours"] for m in metas if m["mode"] == "clean")
    raw = raw_alarms("h12", {k: H12_RULES[k] for k in ("dwell_25", "dwell_60")}, workers)
    alarms = {**raw,
              "C2 " + c2_r1["name"] + " (round-1 spec)": alarms_by_world(_build(c2_r1["rule"]), tab),
              "C4 retrained (round 2)": alarms_by_world(_build(c4["rule"]), tab),
              "C4 round-1 weights (frozen)": alarms_by_world(_build(c4_r1["rule"]), tab),
              "ceiling_label_oracle": {w: [(e["t_start"], "loiter", e["actors"][0] if e["actors"] else None)
                                           for e in m["truth"]] for w, m in enumerate(metas)}}
    results = {}
    for name, al in alarms.items():
        results[name] = {"window_only": score_split(al, metas),
                         "actor_aware": score_split(al, metas, actor_aware=True)}
    out = {"experiment": "h58_round2", "clean_cam_h": clean_h,
           "c4_refit": {k: c4[k] for k in ("theta", "min_clock_s", "fa_per_cam_h", "recall", "rule")},
           "c4_round1_train": {"fa_per_cam_h": c4_r1["fa_per_cam_h"], "recall": c4_r1["recall"]},
           "results": results, "twins": twin_rates(tab, metas, clean_h), "wall_s": round(time.time() - t0, 1)}
    (OUT / "round2_results.json").write_text(json.dumps(out, indent=1, default=float))
    L = ["| rule | scoring | FA/cam-h [Garwood 95 %] | recall@30 [95 %] | precision@30 [95 %] | recall@10 |",
         "|---|---|---|---|---|---|"]
    for name, rr in results.items():
        for sc, r in rr.items():
            d, d10 = r["default_tol30"], r["default_tol10"]
            L.append(f"| {name} | {sc} | {d['fa_per_cam_h']:.3f} [{d['garwood95'][0]:.3f}, {d['garwood95'][1]:.3f}] | "
                     f"{d['recall']:.3f} [{d['recall_boot95'][0]:.3f}, {d['recall_boot95'][1]:.3f}] | "
                     f"{d['precision']:.3f} [{d['precision_boot95'][0]:.3f}, {d['precision_boot95'][1]:.3f}] | "
                     f"{d10['recall']:.3f} |")
    L += ["", "clean alarms by archetype:"]
    L += [f"- {n}: {rr['window_only']['clean_alarms_by_archetype']}" for n, rr in results.items()]
    L += ["", "twins:"] + [f"- {k}: {v}" for k, v in out["twins"].items()]
    (OUT / "round2_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L), flush=True)


# ------------------------------------------------------------------ round 3

SEL_GRID = (0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999)
CLOCK_GRID = (5.0, 10.0, 15.0)
CURVE_GRID = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


def alarms_from_score(p: np.ndarray, tab: pd.DataFrame, theta: float, min_clock_s: float):
    """`alarms_by_world` for a tick rule whose condition is p >= theta and
    clock >= min_clock_s, with p precomputed (grid sweeps)."""
    from cctvsec.eval.loiter_features import first_per_episode
    cond = (p >= theta) & (tab["clock"].to_numpy() >= min_clock_s) & ~tab["allowed"].to_numpy(bool)
    idx = first_per_episode(cond, tab["epk"].to_numpy())
    out: dict[int, list] = {}
    for w, t, k, u in zip(tab["w"].to_numpy()[idx], tab["t"].to_numpy()[idx], tab["kind"].to_numpy()[idx],
                          tab["uid"].to_numpy()[idx]):
        out.setdefault(int(w), []).append((float(t), str(k), str(u)))
    return out


def _sub(alarms: dict, metas: list, ws) -> tuple[dict, list]:
    """Restrict a per-world alarm dict and metas to worlds `ws` (re-indexed)."""
    ws = list(ws)
    return {j: alarms.get(w, []) for j, w in enumerate(ws)}, [metas[w] for w in ws]


def _aa(alarms, metas) -> dict:
    """Actor-aware, 30 s, default mode (the round-3 primary metric)."""
    r = score_split(alarms, metas, actor_aware=True)
    d = r["default_tol30"]
    return {k: d[k] for k in ("fa", "cam_h", "fa_per_cam_h", "garwood95", "recall", "recall_boot95",
                              "precision", "precision_boot95", "median_latency_s")} | {
        "recall_tol10": r["default_tol10"]["recall"],
        "clean_alarms_by_archetype": r["clean_alarms_by_archetype"]}


def _select(p, tab, metas, ws, thetas=SEL_GRID) -> tuple[dict, list]:
    grid = []
    for mc in CLOCK_GRID:
        for th in thetas:
            al, m = _sub(alarms_from_score(p, tab, th, mc), metas, ws)
            d = score_split(al, m, actor_aware=True)["default_tol30"]
            grid.append({"theta": th, "min_clock_s": mc, "fa_per_cam_h": d["fa_per_cam_h"], "recall": d["recall"]})
    ok = [g for g in grid if g["recall"] >= 0.85]
    best = min(ok, key=lambda g: (g["fa_per_cam_h"], -g["recall"])) if ok else \
        max(grid, key=lambda g: (g["recall"], -g["fa_per_cam_h"]))
    return best, grid


def _reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> dict:
    b = np.minimum((p * bins).astype(int), bins - 1)
    ece = 0.0
    rows = []
    for k in range(bins):
        m = b == k
        if m.any():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
            rows.append([k / bins, int(m.sum()), float(p[m].mean()), float(y[m].mean())])
    return {"brier": float(np.mean((p - y) ** 2)), "ece10": float(ece), "bins": rows}


def cmd_round3(workers: int) -> None:
    """docs/research/58 §7 (pre-registered there, commit cec3317). Reuses the
    round-2 feature tables under H58_OUT; everything actor-aware."""
    import pickle

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.isotonic import IsotonicRegression

    from cctvsec.eval.loiter_features import CONTEXT_FEATURES, FEATURES, add_context
    from cctvsec.eval.rules import GBMLoiterRule
    assert OUT != R1, "set H58_OUT=out/experiments/h58_round2"
    t0 = time.time()
    feats = tuple(f for f in FEATURES if f != "dist_entrance")
    ctx = feats + CONTEXT_FEATURES
    r2 = json.loads((OUT / "round2_results.json").read_text())
    sel1 = json.loads((R1 / "selection.json").read_text())
    A1, A2 = _build(sel1["shipped"]["rule"]), _build(r2["c4_refit"]["rule"])

    tab, metas = load_split("train")
    add_context(tab)
    rng = np.random.default_rng(58)
    sel_w = []
    for mode in ("clean", "recall"):
        ws = [w for w, m in enumerate(metas) if m["mode"] == mode]
        sel_w += sorted(rng.permutation(ws)[: round(0.3 * len(ws))].tolist())
    sel_w = sorted(sel_w)
    fit_w = [w for w in range(len(metas)) if w not in set(sel_w)]
    in_sel = tab["w"].isin(sel_w).to_numpy()
    late = tab["late"].to_numpy(bool)
    y_all = tab["pos"].to_numpy(bool)
    print(f"train {tab.shape}; fit worlds {len(fit_w)}, select worlds {len(sel_w)} {time.time() - t0:.0f}s", flush=True)

    def fit(cols):
        m = ~in_sel & ~late
        X = tab.loc[m, list(cols)].to_numpy(np.float32)
        y = y_all[m].astype(int)
        neg = np.flatnonzero(y == 0)
        if len(neg) > 1_500_000:
            keep = np.r_[np.flatnonzero(y == 1), np.random.default_rng(58).choice(neg, 1_500_000, replace=False)]
            X, y = X[keep], y[keep]
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, max_leaf_nodes=31,
                                             class_weight="balanced", early_stopping=False, random_state=58)
        return clf.fit(X, y)

    tsel = tab[in_sel].copy()
    sel_ix = {w: j for j, w in enumerate(sel_w)}
    tsel["w"] = tsel["w"].map(sel_ix).astype(np.int32)
    msel = [metas[w] for w in sel_w]
    arms, models, train_sel = {}, {}, {}
    for name, cols in (("B", feats), ("D", ctx)):
        clf = fit(cols)
        p = clf.predict_proba(tsel[list(cols)].to_numpy(np.float32))[:, 1]
        best, grid = _select(p, tsel, msel, range(len(sel_w)))
        models[name] = clf
        arms[name] = GBMLoiterRule(model=clf, features=cols, theta=best["theta"], min_clock_s=best["min_clock_s"])
        train_sel[name] = {"selected": best, "grid": grid}
        print(f"{name}: select-fold {best} {time.time() - t0:.0f}s", flush=True)
        if name == "B":
            m = ~late[in_sel]
            iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p[m], y_all[in_sel][m])
            pc = iso.predict(p)
            best, grid = _select(pc, tsel, msel, range(len(sel_w)))
            arms["C"] = GBMLoiterRule(model=clf, features=cols, calibrator=iso, theta=best["theta"],
                                      min_clock_s=best["min_clock_s"])
            train_sel["C"] = {"selected": best, "grid": grid}
            print(f"C: select-fold {best} {time.time() - t0:.0f}s", flush=True)
    (OUT / "round3_models.pkl").write_bytes(pickle.dumps({"arms": arms}))
    del tab, tsel

    tab, metas = load_split("h12")
    add_context(tab)
    clean_h = sum(m["camera_hours"] for m in metas if m["mode"] == "clean")
    names = {"A1": "A1 logistic, round-1 weights frozen", "A2": "A2 logistic, round-2 retrained",
             "B": "B GBM (track-only)", "C": "C GBM + isotonic (track-only)",
             "D": "D GBM + zone-function context"}
    rules = {"A1": A1, "A2": A2, **arms}
    results = {}
    for k, rule in rules.items():
        results[k] = {"name": names[k], "rule": {"theta": rule.theta, "min_clock_s": rule.min_clock_s},
                      "train_select": train_sel.get(k, {}).get("selected"),
                      **_aa(alarms_by_world(rule, tab), metas)}
        print(k, round(results[k]["fa_per_cam_h"], 3), round(results[k]["recall"], 3), f"{time.time() - t0:.0f}s", flush=True)
    for k, ref in (("A1", r2["results"]["C4 round-1 weights (frozen)"]), ("A2", r2["results"]["C4 retrained (round 2)"])):
        d = ref["actor_aware"]["default_tol30"]
        results[k]["reproduces_round2"] = bool(d["fa"] == results[k]["fa"] and abs(d["recall"] - results[k]["recall"]) < 1e-12)
    # (a) decision
    ok = [k for k in ("A1", "A2") if results[k]["recall"] >= 0.80]
    a_win = min(ok, key=lambda k: results[k]["fa_per_cam_h"]) if ok else None
    shipped, why = a_win, "arm (a) decision rule"
    if a_win:
        lo = results[a_win]["garwood95"][0]
        clear = [k for k in ("B", "C") if results[k]["recall"] >= 0.80 and results[k]["garwood95"][1] < lo]
        if clear:
            shipped = min(clear, key=lambda k: results[k]["fa_per_cam_h"])
            why = f"GBM clears the bar (Garwood upper < {a_win} Garwood lower)"
    # (c) calibration + curves
    nl = ~tab["late"].to_numpy(bool)
    y = tab["pos"].to_numpy(bool)[nl].astype(float)
    praw = {k: arms[k].model.predict_proba(tab[list(arms[k].features)].to_numpy(np.float32))[:, 1] for k in ("B", "D")}
    pc = arms["C"].calibrator.predict(praw["B"])
    calib = {"C_calibrated": _reliability(pc[nl], y), "B_uncalibrated": _reliability(praw["B"][nl], y),
             "base_rate": float(y.mean())}
    pa1 = A1.score(tab)
    curves = {}
    raw_grid = tuple(sorted(set(CURVE_GRID) | set(SEL_GRID)))
    for k, p, mc, grid in (("C", pc, arms["C"].min_clock_s, CURVE_GRID), ("A1", pa1, A1.min_clock_s, CURVE_GRID),
                           ("B", praw["B"], arms["B"].min_clock_s, raw_grid),
                           ("D", praw["D"], arms["D"].min_clock_s, raw_grid)):
        pts = []
        for th in grid:
            r = _aa(alarms_from_score(p, tab, th, mc), metas)
            r.pop("clean_alarms_by_archetype")
            pts.append({"theta": th, "min_clock_s": mc, **r})
        curves[k] = pts
        print(f"curve {k} done {time.time() - t0:.0f}s", flush=True)

    def fa_at_080(k):
        ok = [q for q in curves[k] if q["recall"] >= 0.80]
        return min(ok, key=lambda q: q["fa_per_cam_h"]) if ok else None
    context = {"B_selected": {k: results["B"][k] for k in ("fa_per_cam_h", "garwood95", "recall", "recall_boot95")},
               "D_selected": {k: results["D"][k] for k in ("fa_per_cam_h", "garwood95", "recall", "recall_boot95")},
               "fa_ratio_selected": results["D"]["fa_per_cam_h"] / max(results["B"]["fa_per_cam_h"], 1e-12),
               "B_best_on_curve_recall>=0.80": fa_at_080("B"), "D_best_on_curve_recall>=0.80": fa_at_080("D"),
               "time_of_day": "not varied by the alarm_scale recipe: gain 0 by construction, untestable here"}
    out = {"experiment": "h58_round3", "preregistration_commit": "cec3317", "clean_cam_h": clean_h,
           "fold": {"select_worlds": sel_w, "fit_worlds": len(fit_w)},
           "results": results, "arm_a_winner": a_win, "shipped": shipped, "shipped_why": why,
           "calibration": calib, "curves": curves, "context": context,
           "twin_floor": r2["twins"]["smoke_break_in_gate"], "wall_s": round(time.time() - t0, 1)}
    (OUT / "round3_results.json").write_text(json.dumps(out, indent=1, default=float))
    L = ["| arm | θ, clock | FA/cam-h [Garwood 95 %] | recall@30 actor-aware [95 %] | precision [95 %] | recall@10 | select-fold FA, recall |",
         "|---|---|---|---|---|---|---|"]
    for k, r in results.items():
        ts = r["train_select"]
        L.append(f"| {r['name']} | {r['rule']['theta']}, {r['rule']['min_clock_s']} | {r['fa_per_cam_h']:.3f} "
                 f"[{r['garwood95'][0]:.3f}, {r['garwood95'][1]:.3f}] | {r['recall']:.3f} [{r['recall_boot95'][0]:.3f}, "
                 f"{r['recall_boot95'][1]:.3f}] | {r['precision']:.3f} [{r['precision_boot95'][0]:.3f}, "
                 f"{r['precision_boot95'][1]:.3f}] | {r['recall_tol10']:.3f} | "
                 + (f"{ts['fa_per_cam_h']:.3f}, {ts['recall']:.3f}" if ts else "—") + " |")
    L += ["", f"arm (a) winner: {a_win}; shipped: {shipped} ({why})",
          f"reproduces round 2: A1 {results['A1']['reproduces_round2']}, A2 {results['A2']['reproduces_round2']}", "",
          "calibration (H12 non-late ticks): " + json.dumps({k: (v if not isinstance(v, dict) else
                                                                {q: v[q] for q in ('brier', 'ece10')})
                                                           for k, v in calib.items()})]
    for k, pts in curves.items():
        L += ["", f"curve {k} (clock >= {pts[0]['min_clock_s']}):", "| θ | FA/cam-h [Garwood] | recall [95 %] | precision |",
              "|---|---|---|---|"]
        L += [f"| {q['theta']} | {q['fa_per_cam_h']:.3f} [{q['garwood95'][0]:.3f}, {q['garwood95'][1]:.3f}] | "
              f"{q['recall']:.3f} [{q['recall_boot95'][0]:.3f}, {q['recall_boot95'][1]:.3f}] | {q['precision']:.3f} |"
              for q in pts]
    L += ["", "context: " + json.dumps(context, default=float), "", "clean alarms by archetype:"]
    L += [f"- {k}: {r['clean_alarms_by_archetype']}" for k, r in results.items()]
    (OUT / "round3_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L), flush=True)


# ------------------------------------------------------------------ round 4 (58 §8)

H21_GRID = tuple(float(x) for x in np.round(np.geomspace(0.01, 0.5, 25), 5))
H21_SEEDS = (58, 59, 60, 61, 62)
H23_SEEDS = (58, 158, 258, 358, 458, 558, 658, 758, 858, 958)
A1_LO = 2.854  # A1's H12 Garwood lower bound (58 §7.2), the pre-registered bar


def stratified_fold(metas: list[dict], seed: int, frac: float = 0.3) -> list[int]:
    """Select-fold world indices, stratified by mode (round-3 recipe)."""
    rng = np.random.default_rng(seed)
    sel = []
    for mode in ("clean", "recall"):
        ws = [w for w, m in enumerate(metas) if m["mode"] == mode]
        sel += sorted(rng.permutation(ws)[: round(frac * len(ws))].tolist())
    return sorted(sel)


def clean_counts(alarms: dict, metas: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Per clean world: alarm count (all are false in a world with no truth) and cam-h."""
    ws = [w for w, m in enumerate(metas) if m["mode"] == "clean"]
    return (np.array([len(alarms.get(w, [])) for w in ws], float),
            np.array([metas[w]["camera_hours"] for w in ws], float))


def paired_world_diff(ka: np.ndarray, kb: np.ndarray, ch: np.ndarray, n_boot: int = 2000,
                      seed: int = 58) -> dict:
    """FA/cam-h of a minus b with a clean-world cluster bootstrap (paired)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ch), (n_boot, len(ch)))
    d = (ka[idx].sum(1) - kb[idx].sum(1)) / ch[idx].sum(1)
    return {"diff": float((ka.sum() - kb.sum()) / ch.sum()),
            "boot95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}


def seed_bootstrap(x, n_boot: int = 10000, seed: int = 23) -> dict:
    """Mean and percentile 95 % CI of the mean over seeds."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n_boot, len(x)))].mean(1)
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
            "boot95": [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]}


def h23_decision(rows: list[dict], a1_fa: float = 2.915) -> dict:
    """58 §8.1 H23 rules. rows: {"F": (fa, recall), "R": (fa, recall)} per seed.
    An arm with H12 recall < 0.80 loses its seed."""
    def ok(fr):
        return fr[1] >= 0.80

    r_wins = sum(ok(r["R"]) and (not ok(r["F"]) or r["R"][0] <= r["F"][0]) for r in rows)
    f_wins = sum(ok(r["F"]) and (not ok(r["R"]) or r["F"][0] < r["R"][0]) for r in rows)
    n = len(rows)
    policy = ("retrain" if r_wins >= 7 else "freeze" if f_wins >= 7 else "no-dominance")
    r_below = sum(ok(r["R"]) and r["R"][0] <= a1_fa for r in rows)
    luck = "lucky" if r_below <= 1 else "typical" if r_below >= 3 else "borderline"
    return {"n": n, "retrained_wins": int(r_wins), "frozen_wins": int(f_wins), "policy": policy,
            "retrained_at_or_below_A1": int(r_below), "A1": luck}


def _fit_gbm(tab, cols, rows_mask, y_all, seed):
    from sklearn.ensemble import HistGradientBoostingClassifier
    X = tab.loc[rows_mask, list(cols)].to_numpy(np.float32)
    y = y_all[rows_mask].astype(int)
    neg = np.flatnonzero(y == 0)
    if len(neg) > 1_500_000:
        keep = np.r_[np.flatnonzero(y == 1), np.random.default_rng(seed).choice(neg, 1_500_000, replace=False)]
        X, y = X[keep], y[keep]
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, max_leaf_nodes=31,
                                         class_weight="balanced", early_stopping=False, random_state=seed)
    return clf.fit(X, y)


def _sel_table(tab, sel_w):
    t = tab[tab["w"].isin(sel_w).to_numpy()].copy()
    t["w"] = t["w"].map({w: j for j, w in enumerate(sel_w)}).astype(np.int32)
    return t


def _row(al, metas):
    r = _aa(al, metas)
    r.pop("clean_alarms_by_archetype")
    return r


def cmd_h21(workers: int) -> None:
    """58 §8 H21: calibrated GBM (C) with θ on a calibrated-scale grid,
    selected on the round-3 select fold; 5 GBM seeds; scored on H12."""
    import pickle

    from sklearn.isotonic import IsotonicRegression

    from cctvsec.eval.loiter_features import FEATURES
    from cctvsec.eval.rules import GBMLoiterRule
    assert OUT != R1, "set H58_OUT=out/experiments/h58_round2"
    t0 = time.time()
    feats = tuple(f for f in FEATURES if f != "dist_entrance")
    tab, metas = load_split("train")
    sel_w = stratified_fold(metas, 58)
    r3 = json.loads((OUT / "round3_results.json").read_text())
    assert sel_w == r3["fold"]["select_worlds"], "select fold differs from round 3"
    in_sel = tab["w"].isin(sel_w).to_numpy()
    late = tab["late"].to_numpy(bool)
    y_all = tab["pos"].to_numpy(bool)
    tsel = _sel_table(tab, sel_w)
    msel = [metas[w] for w in sel_w]
    Xs = tsel[list(feats)].to_numpy(np.float32)
    arms: dict[str, dict] = {}
    for s in H21_SEEDS:
        clf = _fit_gbm(tab, feats, ~in_sel & ~late, y_all, s)
        p = clf.predict_proba(Xs)[:, 1]
        nl = ~late[in_sel]
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p[nl], y_all[in_sel][nl])
        bC, gC = _select(iso.predict(p), tsel, msel, range(len(sel_w)), thetas=H21_GRID)
        bB, _ = _select(p, tsel, msel, range(len(sel_w)))
        okC = any(g["recall"] >= 0.85 for g in gC)
        arms[f"C_s{s}"] = {"rule": GBMLoiterRule(model=clf, features=feats, calibrator=iso, theta=bC["theta"],
                                                 min_clock_s=bC["min_clock_s"]), "select": bC, "selectable": okC}
        arms[f"B_s{s}"] = {"rule": GBMLoiterRule(model=clf, features=feats, theta=bB["theta"],
                                                 min_clock_s=bB["min_clock_s"]), "select": bB, "selectable": True}
        print(f"seed {s}: C select {bC} (selectable={okC}); B select {bB} {time.time() - t0:.0f}s", flush=True)
    (OUT / "round4_h21_models.pkl").write_bytes(pickle.dumps({k: v["rule"] for k, v in arms.items()}))
    del tab, tsel
    tab, metas = load_split("h12")
    A1 = _build(json.loads((R1 / "selection.json").read_text())["shipped"]["rule"])
    al_a1 = alarms_by_world(A1, tab)
    a1 = _row(al_a1, metas)
    assert abs(a1["fa_per_cam_h"] - 2.915) < 5e-4, a1["fa_per_cam_h"]
    ka1, ch = clean_counts(al_a1, metas)
    results = {"A1": {"rule": {"theta": A1.theta, "min_clock_s": A1.min_clock_s}, **a1}}
    for k, v in arms.items():
        rule = v["rule"]
        al = alarms_by_world(rule, tab)
        r = _row(al, metas)
        kc, _ = clean_counts(al, metas)
        r["minus_A1"] = paired_world_diff(kc, ka1, ch)
        r["clears_bar"] = bool(v["selectable"] and r["recall"] >= 0.80 and r["garwood95"][1] < A1_LO)
        results[k] = {"rule": {"theta": rule.theta, "min_clock_s": rule.min_clock_s}, "select": v["select"],
                      "selectable": v["selectable"], **r}
        print(k, round(r["fa_per_cam_h"], 3), round(r["recall"], 3), r["clears_bar"], f"{time.time() - t0:.0f}s",
              flush=True)
    c_keys = [f"C_s{s}" for s in H21_SEEDS]
    n_clear = sum(results[k]["clears_bar"] for k in c_keys)
    prim = results["C_s58"]
    ships_c = n_clear >= 4 and prim["clears_bar"] and prim["minus_A1"]["boot95"][1] < 0
    out = {"experiment": "h58_round4_h21", "grid": H21_GRID, "seeds": H21_SEEDS, "results": results,
           "C_seeds_clearing_bar": n_clear, "ships": "C_s58" if ships_c else "A1",
           "C_fa_over_seeds": seed_bootstrap([results[k]["fa_per_cam_h"] for k in c_keys]),
           "C_recall_over_seeds": seed_bootstrap([results[k]["recall"] for k in c_keys]),
           "wall_s": round(time.time() - t0, 1)}
    (OUT / "round4_h21_results.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("C_seeds_clearing_bar", "ships", "C_fa_over_seeds")}, default=float))


def cmd_h23(workers: int) -> None:
    """58 §8 H23: frozen round-1 logistic weights vs logistic retrained on
    each of 10 train-split world seeds; both θ/clock-selected on that seed's
    select fold; scored on H12."""
    import dataclasses

    from cctvsec.eval.loiter_features import FEATURES
    assert OUT != R1, "set H58_OUT=out/experiments/h58_round2"
    t0 = time.time()
    feats = tuple(f for f in FEATURES if f != "dist_entrance")
    A1 = _build(json.loads((R1 / "selection.json").read_text())["shipped"]["rule"])
    rules: dict[int, dict] = {}
    for s in H23_SEEDS:
        split = "train" if s == 58 else f"train_s{s}"
        tab, metas = load_split(split)
        sel_w = stratified_fold(metas, s)
        in_sel = tab["w"].isin(sel_w).to_numpy()
        R = learned_rule(tab[~in_sel], feats, seed=s)
        tsel = _sel_table(tab, sel_w)
        msel = [metas[w] for w in sel_w]
        rows = {}
        for arm, base in (("F", A1), ("R", R)):
            best, grid = _select(base.score(tsel), tsel, msel, range(len(sel_w)))
            rows[arm] = {"rule": dataclasses.replace(base, theta=best["theta"], min_clock_s=best["min_clock_s"]),
                         "select": best, "selectable": any(g["recall"] >= 0.85 for g in grid)}
        rules[s] = rows
        print(f"seed {s}: F {rows['F']['select']} R {rows['R']['select']} {time.time() - t0:.0f}s", flush=True)
        del tab, tsel
    tab, metas = load_split("h12")
    per_seed = []
    for s, rows in rules.items():
        rec = {"seed": s}
        ks = {}
        for arm in ("F", "R"):
            al = alarms_by_world(rows[arm]["rule"], tab)
            r = _row(al, metas)
            ks[arm], ch = clean_counts(al, metas)
            rec[arm] = {"theta": rows[arm]["rule"].theta, "min_clock_s": rows[arm]["rule"].min_clock_s,
                        "select": rows[arm]["select"], "selectable": rows[arm]["selectable"], **r}
        if s == 58:
            rec["R"]["spec"] = _spec(rows["R"]["rule"])
        rec["R_minus_F"] = paired_world_diff(ks["R"], ks["F"], ch)
        rec["rel_gap"] = (rec["R"]["fa_per_cam_h"] - rec["F"]["fa_per_cam_h"]) / rec["F"]["fa_per_cam_h"]
        per_seed.append(rec)
        print(s, "F", round(rec["F"]["fa_per_cam_h"], 3), round(rec["F"]["recall"], 3),
              "R", round(rec["R"]["fa_per_cam_h"], 3), round(rec["R"]["recall"], 3), f"{time.time() - t0:.0f}s",
              flush=True)
    dec = h23_decision([{a: (r[a]["fa_per_cam_h"], r[a]["recall"]) for a in ("F", "R")} for r in per_seed])
    out = {"experiment": "h58_round4_h23", "seeds": H23_SEEDS, "per_seed": per_seed, "decision": dec,
           "F_fa": seed_bootstrap([r["F"]["fa_per_cam_h"] for r in per_seed]),
           "R_fa": seed_bootstrap([r["R"]["fa_per_cam_h"] for r in per_seed]),
           "F_recall": seed_bootstrap([r["F"]["recall"] for r in per_seed]),
           "R_recall": seed_bootstrap([r["R"]["recall"] for r in per_seed]),
           "R_minus_F": seed_bootstrap([r["R_minus_F"]["diff"] for r in per_seed]),
           "rel_gap": seed_bootstrap([r["rel_gap"] for r in per_seed]),
           "wall_s": round(time.time() - t0, 1)}
    (OUT / "round4_h23_results.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("decision", "R_minus_F", "rel_gap", "F_fa", "R_fa")}, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--split", default="h12")
    ap.add_argument("--workers", type=int, default=11)
    a = ap.parse_args()
    {"gen": lambda: cmd_gen(a.split, a.workers),
     "feats": lambda: cmd_feats(a.split, a.workers),
     "fit": lambda: cmd_fit(a.workers),
     "eval": lambda: cmd_eval(a.workers),
     "twins": cmd_twins,
     "round2": lambda: cmd_round2(a.workers),
     "round3": lambda: cmd_round3(a.workers),
     "h21": lambda: cmd_h21(a.workers),
     "h23": lambda: cmd_h23(a.workers)}[a.cmd]()
