"""Per-person trailing-window track features for loiter rules (docs/research/58).

Everything here is computable from a tracker's output plus a site's zone map:
positions, speeds, the zone tag under the person, how many other people are
within 2 m, and the distance to the nearest entrance. Nothing reads behaviour
labels, archetypes, roles or absolute time - those are simulation artefacts a
real deployment does not have (58 §1 "forbidden features").

Features are sampled on a 1 s tick grid (`tick_s`) from the 5 Hz track and use
cumulative sums, so one person costs O(n) regardless of window length.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

ZONE_TAGS = ("gate", "queue", "restricted", "perimeter_fence", "public", "parking", "blindspot")
FEATURES = (
    "clock", "disp10", "disp30", "path30", "straight30", "mspeed30", "sspeed30",
    "stat30", "moving30", "rms30", "hent30", "turn30", "revisits60", "group", "dist_entrance",
) + tuple(f"tag_{t}" for t in ZONE_TAGS)

# Round-3 context ablation (58 §7): the zone *function* under the person, from
# the zone id with its `_k` suffix stripped. Not track-only - a product needs a
# site profile to supply it - so it is kept out of FEATURES.
ZONE_FUNCTIONS = ("entrance", "gateline", "platform", "reception", "lobby", "concourse", "street",
                  "open", "yard", "bays", "stage", "crowd", "fence_line", "restricted", "blindspot", "none")
CONTEXT_FEATURES = tuple(f"zf_{z}" for z in ZONE_FUNCTIONS)


def zone_function(zone_id) -> str:
    """`zone.entrance_2` -> `entrance`; missing / unknown -> `none`."""
    import re
    if zone_id is None or str(zone_id) in ("None", "nan", ""):
        return "none"
    f = re.sub(r"_\d+$", "", str(zone_id).removeprefix("zone."))
    return f if f in ZONE_FUNCTIONS else "none"


def add_context(table):
    """Add `CONTEXT_FEATURES` one-hot columns (in place) from the `zone` column."""
    zf = table["zone"].astype(str).map(zone_function).to_numpy(object)
    for z in ZONE_FUNCTIONS:
        table[f"zf_{z}"] = (zf == z).astype("float32")
    return table


@dataclass
class PersonFeatures:
    """Features of one track on its tick grid. `t` are the tick times."""

    uid: str
    t: np.ndarray
    f: dict[str, np.ndarray] = field(default_factory=dict)
    tag: np.ndarray | None = None          # zone tag per tick (object)
    zone: np.ndarray | None = None         # zone id per tick (object)
    allowed: np.ndarray | None = None      # bool: role authorised in this zone
    episode: np.ndarray | None = None      # dwell-episode id per tick (C2 clock)

    def matrix(self, names=FEATURES) -> np.ndarray:
        return np.column_stack([self.f[n] for n in names]).astype(float)


def _trail_idx(ts: np.ndarray, at: np.ndarray, w: float) -> np.ndarray:
    """Index of the first sample with t >= at - w (clamped to the track start)."""
    return np.searchsorted(ts, at - w - 1e-9, side="left")


def _wsum(cs: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Sum of x[lo:hi+1] from a cumulative sum with a leading 0."""
    return cs[hi + 1] - cs[lo]


def person_features(
    uid: str,
    ts: np.ndarray, xs: np.ndarray, ys: np.ndarray, sp: np.ndarray,
    zones: np.ndarray, tag_by_zone: dict, allowed_zones: set,
    group: np.ndarray | None = None,
    spawns: np.ndarray | None = None,
    tick_s: float = 1.0,
    depart_w_s: float = 10.0, depart_r_m: float = 4.0,
    stat_speed: float = 0.1,
) -> PersonFeatures:
    """Build `PersonFeatures` for one person (arrays sorted by t)."""
    ts = np.asarray(ts, float)
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    sp = np.asarray(sp, float)
    n = len(ts)
    # ticks: samples whose time lands on the tick grid (5 Hz -> every 5th)
    k = np.round(ts / tick_s, 6)
    idx = np.flatnonzero(np.abs(k - np.round(k)) < 1e-4)
    if len(idx) == 0:
        idx = np.array([n - 1])
    at = ts[idx]
    step = np.hypot(np.diff(xs, prepend=xs[0]), np.diff(ys, prepend=ys[0]))
    cs = {name: np.concatenate([[0.0], np.cumsum(v)]) for name, v in (
        ("step", step), ("sp", sp), ("sp2", sp * sp), ("stat", (sp < stat_speed).astype(float)),
        ("x", xs), ("y", ys), ("x2", xs * xs), ("y2", ys * ys))}
    # heading histogram (8 bins) of moving steps, and turning
    hd = np.arctan2(np.diff(ys, prepend=ys[0]), np.diff(xs, prepend=xs[0]))
    mv = step > 0.02
    b = ((hd + np.pi) / (2 * np.pi) * 8).astype(int) % 8
    hcs = np.zeros((n + 1, 8))
    hcs[1:] = np.cumsum(np.eye(8)[b] * mv[:, None], axis=0)
    dh = np.abs(np.angle(np.exp(1j * np.diff(hd, prepend=hd[0])))) * (mv & np.roll(mv, 1))
    ccs = np.concatenate([[0.0], np.cumsum(dh)])
    mcs = np.concatenate([[0.0], np.cumsum(mv.astype(float))])

    f: dict[str, np.ndarray] = {}
    lo10, lo30 = _trail_idx(ts, at, 10.0), _trail_idx(ts, at, 30.0)
    f["disp10"] = np.hypot(xs[idx] - xs[lo10], ys[idx] - ys[lo10])
    f["disp30"] = np.hypot(xs[idx] - xs[lo30], ys[idx] - ys[lo30])
    cnt = (idx - lo30 + 1).astype(float)
    f["path30"] = np.where(idx > lo30, cs["step"][idx + 1] - cs["step"][lo30 + 1], 0.0)
    f["straight30"] = f["disp30"] / np.maximum(f["path30"], 1e-3)
    m = _wsum(cs["sp"], lo30, idx) / cnt
    f["mspeed30"] = m
    f["sspeed30"] = np.sqrt(np.maximum(_wsum(cs["sp2"], lo30, idx) / cnt - m * m, 0.0))
    f["stat30"] = _wsum(cs["stat"], lo30, idx) / cnt
    f["moving30"] = _wsum(mcs, lo30, idx) / cnt
    mx, my = _wsum(cs["x"], lo30, idx) / cnt, _wsum(cs["y"], lo30, idx) / cnt
    f["rms30"] = np.sqrt(np.maximum(_wsum(cs["x2"], lo30, idx) / cnt - mx * mx
                                    + _wsum(cs["y2"], lo30, idx) / cnt - my * my, 0.0))
    h = hcs[idx + 1] - hcs[lo30]
    tot = h.sum(1, keepdims=True)
    p = np.where(tot > 0, h / np.maximum(tot, 1), 0)
    f["hent30"] = -(np.where(p > 0, p * np.log(np.where(p > 0, p, 1)), 0)).sum(1) / np.log(8)
    f["turn30"] = (ccs[idx + 1] - ccs[lo30]) / cnt
    # C2 clock: time since the last "departure" (net displacement over the
    # trailing depart_w_s exceeds depart_r_m). Evaluated on every sample.
    loW = _trail_idx(ts, ts, depart_w_s)
    dep = np.hypot(xs - xs[loW], ys - ys[loW]) > depart_r_m
    last = np.maximum.accumulate(np.where(dep, ts, ts[0]))
    f["clock"] = at - last[idx]
    episode = last[idx]
    f["revisits60"] = revisits(at, xs[idx], ys[idx], horizon_s=60.0)
    f["group"] = np.zeros(len(idx)) if group is None else np.asarray(group, float)[idx]
    if spawns is not None and len(spawns):
        d = np.hypot(xs[idx, None] - spawns[None, :, 0], ys[idx, None] - spawns[None, :, 1])
        f["dist_entrance"] = d.min(1)
    else:
        f["dist_entrance"] = np.full(len(idx), 99.0)
    zt = np.array([tag_by_zone.get(z) if z is not None else None for z in zones[idx]], dtype=object)
    for t in ZONE_TAGS:
        f[f"tag_{t}"] = (zt == t).astype(float)
    allowed = np.array([z in allowed_zones for z in zones[idx]], bool)
    return PersonFeatures(uid=uid, t=at, f=f, tag=zt, zone=zones[idx], allowed=allowed, episode=episode)


def revisits(t: np.ndarray, x: np.ndarray, y: np.ndarray, horizon_s: float = 60.0,
             r_in: float = 1.0, r_out: float = 2.0) -> np.ndarray:
    """Max over anchors of how many times the track came back to within `r_in`
    of an earlier tick position after having been more than `r_out` away from it
    (hysteresis), within the trailing horizon. Oscillation / pacing signature;
    zero for a standing person and for a walker. Horizon is in ticks (1 s grid)."""
    n = len(t)
    H = round(horizon_s)
    out = np.zeros(n)
    if n < 3:
        return out
    a = np.arange(n)
    state = np.zeros(n, int)      # last non-zero state per anchor
    count = np.zeros(n)           # returns so far per anchor
    for k in range(1, H + 1):
        j = a + k
        ok = j < n
        if not ok.any():
            break
        aa, jj = a[ok], j[ok]
        d = np.hypot(x[jj] - x[aa], y[jj] - y[aa])
        s = np.where(d <= r_in, 1, np.where(d > r_out, -1, 0))
        ret = (s == 1) & (state[aa] == -1)
        count[aa] += ret
        state[aa] = np.where(s != 0, s, state[aa])
        np.maximum.at(out, jj, count[aa])
    return out


def group_counts(ts: np.ndarray, xs: np.ndarray, ys: np.ndarray, radius_m: float = 2.0) -> np.ndarray:
    """Other people within `radius_m` at the same timestamp, for every row."""
    from scipy.spatial import cKDTree
    out = np.zeros(len(ts))
    key = np.round(ts * 1000).astype(np.int64)
    order = np.argsort(key, kind="stable")
    ks = key[order]
    cuts = np.flatnonzero(np.diff(ks)) + 1
    for g in np.split(order, cuts):
        if len(g) < 2:
            continue
        pts = np.column_stack([xs[g], ys[g]])
        nb = cKDTree(pts).query_ball_point(pts, radius_m, return_length=True)
        out[g] = np.asarray(nb) - 1
    return out


def first_per_episode(cond: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """Indices of the first True row of `cond` within each run of equal `keys`
    (rows ordered by episode, then time). One alarm per dwell episode."""
    idx = np.flatnonzero(cond)
    if len(idx) == 0:
        return idx
    k = keys[idx]
    first = np.ones(len(idx), bool)
    first[1:] = k[1:] != k[:-1]
    return idx[first]


def world_feature_table(world_df, zones: list[dict], role_by_uid: dict | None = None,
                        spawns=None, tick_s: float = 1.0):
    """All people's `PersonFeatures` as one tick-level DataFrame.

    Columns: uid, t, ep (episode key, unique per person+episode), allowed, tag,
    zone, then `FEATURES`. Rows are ordered by uid, then t."""
    import pandas as pd
    role_by_uid = role_by_uid or {}
    tag_by_zone = {z["id"]: z["tag"] for z in zones}
    roles_by_zone = {z["id"]: set(z.get("allowed_roles") or []) for z in zones}
    df = world_df.sort_values(["uid", "t"]) if not world_df.empty else world_df
    if df.empty:
        return pd.DataFrame(columns=["uid", "t", "ep", "allowed", "tag", "zone", *FEATURES])
    group = group_counts(df["t"].to_numpy(float), df["x"].to_numpy(float), df["y"].to_numpy(float))
    sp = np.asarray(spawns, float).reshape(-1, 2) if spawns is not None and len(spawns) else None
    parts = []
    uids = df["uid"].to_numpy(object)
    cuts = np.flatnonzero(uids[1:] != uids[:-1]) + 1
    arrs = {c: df[c].to_numpy() for c in ("t", "x", "y", "speed")}
    zon = df["zone"].to_numpy(object) if "zone" in df else np.full(len(df), None, object)
    for n_ep, (lo, hi) in enumerate(zip(np.r_[0, cuts], np.r_[cuts, len(df)])):
        uid = uids[lo]
        role = role_by_uid.get(uid)
        allowed_z = {z for z, r in roles_by_zone.items() if role is not None and role in r}
        pf = person_features(uid, arrs["t"][lo:hi], arrs["x"][lo:hi], arrs["y"][lo:hi],
                             arrs["speed"][lo:hi], zon[lo:hi], tag_by_zone, allowed_z,
                             group[lo:hi], sp, tick_s=tick_s)
        cols = {"uid": np.full(len(pf.t), uid, object), "t": pf.t,
                "ep": n_ep * 100000.0 + pf.episode, "allowed": pf.allowed,
                "tag": pf.tag, "zone": pf.zone}
        cols.update(pf.f)
        parts.append(pd.DataFrame(cols))
    return pd.concat(parts, ignore_index=True)
