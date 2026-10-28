"""H39: ground-plane auto-calibration from pedestrians (docs/research/66 H39,
pre-registered in docs/research/32, discussed in docs/research/75).

Arms per camera: A0 the exact calib homography, A1 a DLT homography fitted to GT
foot correspondences, A2 a known-height auto-calibration (f, pitch, roll, camera
height from box tops given box feet and one mean height), A3 the same on the
first 10 s only. Yaw and ground position come from the install record (calib),
never from per-person GT. Metric: world-position RMSE by distance bin with a
bootstrap over tracks, and per-track height error.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, write_json

ARMS = ("A0_exact", "A1_gt_foot", "A2_auto_all", "A3_auto_10s", "A2f_datasheet_f", "A3f_datasheet_f_10s")
POST_HOC = ("A2f_datasheet_f", "A3f_datasheet_f_10s")   # added after the free-f degeneracy was seen

# camera frame (x right, y down, z forward) from a yaw-0 world frame looking along +Y
_R0 = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])


# ------------------------------------------------------------------ pure geometry

def rot_tilt(pitch_deg: float, roll_deg: float) -> np.ndarray:
    """World(yaw 0)->camera rotation for a camera tilted DOWN by pitch_deg, rolled by roll_deg."""
    p, r = np.radians(pitch_deg), np.radians(roll_deg)
    rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    rz = np.array([[np.cos(r), -np.sin(r), 0], [np.sin(r), np.cos(r), 0], [0, 0, 1]])
    return rz @ rx @ _R0


def backproject_ground(K: np.ndarray, R: np.ndarray, C: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Pixels (N,2) -> points on z=0 (N,3) for camera centre C, world->cam R."""
    d = (R.T @ np.linalg.solve(K, np.c_[uv, np.ones(len(uv))].T)).T
    s = -C[2] / d[:, 2]
    return C + s[:, None] * d


def project(K: np.ndarray, R: np.ndarray, C: np.ndarray, X: np.ndarray) -> np.ndarray:
    pc = (R @ (X - C).T).T
    uv = (K @ pc.T).T
    return uv[:, :2] / uv[:, 2:3]


def heights_from_boxes(K, R, C, foot_uv, head_uv) -> np.ndarray:
    """Height of the vertical segment standing on the foot's ground point whose top lies
    on the head ray (closest point of the head ray to that vertical line)."""
    G = backproject_ground(K, R, C, foot_uv)
    d = (R.T @ np.linalg.solve(K, np.c_[head_uv, np.ones(len(head_uv))].T)).T
    # minimise |C + s d - (G + z e3)| over s, z
    out = np.empty(len(G))
    e3 = np.array([0.0, 0.0, 1.0])
    for i in range(len(G)):
        A = np.c_[d[i], -e3]
        sz, *_ = np.linalg.lstsq(A, G[i] - C, rcond=None)
        out[i] = sz[1]
    return out


def fit_known_height(foot_uv: np.ndarray, head_uv: np.ndarray, size: tuple[int, int],
                     prior_h: float, f_fixed: float | None = None) -> dict[str, float]:
    """Fit (f,) pitch, roll, camera height so a person of prior_h standing on each box foot
    projects its head onto the box top row. Vertical residual only: an axis-aligned box's
    top-centre shares the bottom-centre's u, so a u residual measures box geometry, not the
    head, and drags f to infinity. Multi-start, soft-L1. f_fixed = datasheet focal length."""
    from scipy.optimize import least_squares
    w, hgt = size
    cx, cy = w / 2.0, hgt / 2.0
    fu, fv, hv = foot_uv[:, 0] - cx, foot_uv[:, 1] - cy, head_uv[:, 1]

    def resid(p):
        f, pitch, roll, ch = (f_fixed, *p) if f_fixed else p
        R = rot_tilt(pitch, roll)
        d = np.c_[fu / f, fv / f, np.ones_like(fu)] @ R       # rays in world (R^T d)
        s = -ch / d[:, 2]
        G = s[:, None] * d                                     # ground point minus C (z = -ch)
        Hc = (G + np.array([0.0, 0.0, prior_h])) @ R.T         # head in camera frame
        r = f * Hc[:, 1] / Hc[:, 2] + cy - hv
        bad = ~np.isfinite(r) | (s <= 0) | (Hc[:, 2] <= 0)
        r[bad] = 1e3
        return r

    best = None
    f0s = (None,) if f_fixed else (0.5 * w, 0.9 * w, 1.5 * w)
    for f0 in f0s:
        for p0 in (8.0, 20.0, 35.0):
            for h0 in (3.0, 8.0):
                x0 = [p0, 0.0, h0] if f_fixed else [f0, p0, 0.0, h0]
                lo = [0.5, -15, 0.5] if f_fixed else [0.2 * w, 0.5, -15, 0.5]
                hi = [80, 15, 40] if f_fixed else [4 * w, 80, 15, 40]
                r = least_squares(resid, x0, loss="soft_l1", f_scale=3.0, bounds=(lo, hi), max_nfev=2000)
                if best is None or r.cost < best.cost:
                    best = r
    f, pitch, roll, ch = (f_fixed, *best.x) if f_fixed else best.x
    return {"f": float(f), "pitch": float(pitch), "roll": float(roll), "h": float(ch),
            "cost": float(best.cost), "n": len(foot_uv)}


def heading_deg(R_world: np.ndarray) -> float:
    """Compass heading of the optical axis (world->cam R; row 2 = axis in world)."""
    a = R_world[2]
    return float(np.degrees(np.arctan2(a[1], a[0])))


def auto_to_world(fit: dict[str, float], size, heading: float, pos_xy) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """K, world->cam R, centre C in the site frame from a fit + install record."""
    w, hgt = size
    K = np.array([[fit["f"], 0, w / 2.0], [0, fit["f"], hgt / 2.0], [0, 0, 1.0]])
    # local frame looks along +Y; rotate so +Y maps onto the heading
    yaw = np.radians(heading - 90.0)
    Rz = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    R = rot_tilt(fit["pitch"], fit["roll"]) @ Rz.T
    C = np.array([pos_xy[0], pos_xy[1], fit["h"]])
    return K, R, C


def dlt_homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Hartley-normalised DLT, src px -> dst metres (3x3)."""
    def norm(p):
        m = p.mean(0)
        s = np.sqrt(2) / np.mean(np.linalg.norm(p - m, axis=1))
        return np.array([[s, 0, -s * m[0]], [0, s, -s * m[1]], [0, 0, 1]])
    Ts, Td = norm(src), norm(dst)
    a = (Ts @ np.c_[src, np.ones(len(src))].T).T
    b = (Td @ np.c_[dst, np.ones(len(dst))].T).T
    rows = []
    for (x, y, _), (u, v, _) in zip(a, b):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.asarray(rows))
    Hn = vt[-1].reshape(3, 3)
    H = np.linalg.solve(Td, Hn @ Ts)
    return H / H[2, 2]


def apply_h(H: np.ndarray, uv: np.ndarray) -> np.ndarray:
    p = (H @ np.c_[uv, np.ones(len(uv))].T).T
    return p[:, :2] / p[:, 2:3]


def bin_rmse_boot(err: np.ndarray, dist: np.ndarray, track: np.ndarray, bins, n_boot: int,
                  seed: int) -> dict[str, Any]:
    """RMSE per distance bin, pooled <20 m, and far/near ratio; percentile bootstrap over tracks."""
    labels = [f"{bins[i]}-{bins[i + 1]}" for i in range(len(bins) - 1)]
    b = np.digitize(dist, bins) - 1
    tracks, tinv = np.unique(track, return_inverse=True)
    nT, nB = len(tracks), len(labels)
    # per-track sums of squared error and counts, per bin (+ near <20, far >=30)
    groups = [b == i for i in range(nB)] + [dist < 20, dist >= 30]
    sse = np.zeros((nT, len(groups)))
    cnt = np.zeros((nT, len(groups)))
    for g, m in enumerate(groups):
        np.add.at(sse[:, g], tinv[m], err[m] ** 2)
        np.add.at(cnt[:, g], tinv[m], 1)

    def stat(idx):
        s, c = sse[idx].sum(0), cnt[idx].sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.sqrt(s / c)
        return np.r_[r, r[-1] / r[-2]]

    point = stat(np.arange(nT))
    rng = np.random.default_rng(seed)
    bs = np.array([stat(rng.integers(0, nT, nT)) for _ in range(n_boot)])
    lo, hi = np.nanpercentile(bs, 2.5, axis=0), np.nanpercentile(bs, 97.5, axis=0)
    names = labels + ["near_lt20", "far_ge30", "ratio_far_near"]
    ncount = list(cnt.sum(0).astype(int)) + [None]
    return {n: {"rmse": _r(point[i]), "ci95": [_r(lo[i]), _r(hi[i])], "n_boxes": ncount[i]}
            for i, n in enumerate(names)}


def _r(x) -> float | None:
    return None if not np.isfinite(x) else round(float(x), 3)


# ------------------------------------------------------------------ data

def camera_rows(scene_dir: Path, cfg: dict[str, Any]):
    import pandas as pd
    w = pd.read_parquet(scene_dir / "gt/world.parquet")[["frame", "uid", "x", "y"]]
    b = pd.read_parquet(scene_dir / "gt/boxes_mask.parquet")
    ids = pd.read_parquet(scene_dir / "gt/identities.parquet").groupby("uid")["height_m"].first()
    status: dict[str, list[dict]] = {}
    with open(scene_dir / "gt/camera_status.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            status.setdefault(r["camera"], []).append(r)
    last = int(b.frame.max())
    for cal in sorted((scene_dir / "calib").glob("*.json")):
        c = json.loads(cal.read_text())
        cid = c["camera_id"]
        st = [s for s in status.get(cid, []) if s["t"] <= last / c["fps"] + 1e-6]
        keys = {(s["yaw"], s["pitch"], s["hfov_deg"], s["tamper"], s["blind"]) for s in st}
        reason = None
        if len(keys) > 1:
            reason = "pose/hfov/tamper changes in window (principle 2)"
        elif keys and next(iter(keys))[2] != c["hfov_deg"]:
            reason = "live hfov differs from calib (principle 2)"
        bb = b[b.camera == cid]
        bb = bb[bb.mask_bbox.map(lambda v: v is not None and len(v) == 4)]
        W, Hh = c["resolution"]
        box = np.stack(bb.mask_bbox.values) if len(bb) else np.zeros((0, 4))
        m = ((bb.visibility >= cfg["min_visibility"]).values & (box[:, 3] >= cfg["min_height_px"])
             & (box[:, 0] >= cfg["border_px"]) & (box[:, 1] >= cfg["border_px"])
             & (box[:, 0] + box[:, 2] <= W - cfg["border_px"])
             & (box[:, 1] + box[:, 3] <= Hh - cfg["border_px"]))
        sel = bb[m].assign(bx=box[m, 0], by=box[m, 1], bw=box[m, 2], bh=box[m, 3])
        sel = sel.merge(w, on=["frame", "uid"], how="inner")
        sel["height_true"] = sel.uid.map(ids).astype(float)
        yield cid, c, sel, reason


# ------------------------------------------------------------------ runner

def scene_gt_sig(scene_dir: Path) -> str:
    import hashlib
    return hashlib.sha1((scene_dir / "gt/world.parquet").read_bytes()).hexdigest()[:12]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import pandas as pd
    batch = rpath(cfg["batch_dir"])
    seen: dict[str, str] = {}
    cams, excluded, frames = {}, {}, []
    for scene in cfg["scenes"]:
        for cid, c, sel, reason in camera_rows(batch / scene, cfg):
            key = f"{scene}/{cid}"
            sig = json.dumps([c["K"], c["R"], c["t"]]) + scene_gt_sig(batch / scene)
            if reason is None and sig in seen:
                reason = f"duplicate of {seen[sig]} (same pose and GT)"
            if reason:
                excluded[key] = reason
                continue
            seen[sig] = key
            if len(sel) < 30:
                excluded[key] = f"only {len(sel)} usable boxes"
                continue
            K, R, t = (np.array(c[k], float) for k in ("K", "R", "t"))
            C = -R.T @ t
            size = tuple(c["resolution"])
            foot = np.c_[sel.bx + sel.bw / 2, sel.by + sel.bh]
            head = np.c_[sel.bx + sel.bw / 2, sel.by]
            truth = sel[["x", "y"]].to_numpy()
            short = (sel.frame <= cfg["short_window_last_frame"]).to_numpy()
            est: dict[str, np.ndarray] = {}
            hts: dict[str, np.ndarray] = {}
            H0 = np.linalg.inv(K @ np.c_[R[:, 0], R[:, 1], t])
            est["A0_exact"] = apply_h(H0, foot)
            hts["A0_exact"] = heights_from_boxes(K, R, C, foot, head)
            H1 = dlt_homography(foot, truth)
            est["A1_gt_foot"] = apply_h(H1, foot)
            hts["A1_gt_foot"] = np.full(len(sel), np.nan)
            fits = {}
            allm = np.ones(len(sel), bool)
            for arm, mask, ff in (("A2_auto_all", allm, None), ("A3_auto_10s", short, None),
                                  ("A2f_datasheet_f", allm, K[0, 0]),
                                  ("A3f_datasheet_f_10s", short, K[0, 0])):
                fit = fit_known_height(foot[mask], head[mask], size, cfg["prior_height_m"], ff)
                Ka, Ra, Ca = auto_to_world(fit, size, heading_deg(R), C[:2])
                est[arm] = backproject_ground(Ka, Ra, Ca, foot)[:, :2]
                hts[arm] = heights_from_boxes(Ka, Ra, Ca, foot, head)
                fits[arm] = {k: round(v, 3) for k, v in fit.items()}
            true_pitch = float(np.degrees(np.arcsin(-R[2, 2])))
            cams[key] = {"n_boxes": len(sel), "n_boxes_first10s": int(short.sum()),
                         "true": {"f": round(float(K[0, 0]), 1), "pitch": round(true_pitch, 2),
                                  "h": round(float(C[2]), 2)},
                         "fits": fits}
            dist = np.linalg.norm(truth - C[:2], axis=1)
            for arm in ARMS:
                err = np.linalg.norm(est[arm] - truth, axis=1)
                frames.append(pd.DataFrame({
                    "arm": arm, "cam": key, "track": key + "/" + sel.uid.astype(str),
                    "frame": sel.frame.to_numpy(), "dist": dist, "err": err,
                    "h_est": hts[arm], "h_true": sel.height_true.to_numpy(),
                    "scored": (~short) if arm.startswith("A3") else True}))
            print(key, len(sel), fits["A2_auto_all"], cams[key]["true"], flush=True)
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(out / "errors.parquet")
    per_arm, heights = {}, {}
    for arm in ARMS:
        d = df[(df.arm == arm) & df.scored]
        per_arm[arm] = bin_rmse_boot(d.err.to_numpy(), d.dist.to_numpy(), d.track.to_numpy(),
                                     cfg["distance_bins"], cfg["n_boot"], cfg["seed"])
        if d.h_est.notna().any():
            tr = d.groupby("track").agg(h=("h_est", "median"), t=("h_true", "first"))
            e = tr.h - tr.t
            heights[arm] = {"tracks": len(tr), "mae_m": round(float(e.abs().mean()), 3),
                            "mean_signed_m": round(float(e.mean()), 3),
                            "median_abs_m": round(float(e.abs().median()), 3)}
    pop = df[df.arm == "A0_exact"].groupby("track").h_true.first()
    th = cfg["thresholds"]
    a2 = per_arm["A2_auto_all"]
    near, ratio = a2["near_lt20"], a2["ratio_far_near"]
    decision = {
        "near_met": near["rmse"] is not None and near["rmse"] <= th["near_rmse_m"],
        "ratio_met": ratio["rmse"] is not None and ratio["rmse"] >= th["far_ratio"],
        "robust": (near["ci95"][1] or 9e9) <= th["near_rmse_m"] and (ratio["ci95"][0] or 0) >= th["far_ratio"],
        "short_vs_all": _r(per_arm["A3_auto_10s"]["near_lt20"]["rmse"] / near["rmse"]),
    }
    decision["h39_met"] = decision["near_met"] and decision["ratio_met"]
    decision["secondary_met"] = decision["short_vs_all"] is not None and decision["short_vs_all"] <= th["short_vs_all"]
    res = {"cameras": cams, "excluded": excluded, "rmse": per_arm, "heights": heights,
           "population_height_mean_m": round(float(pop.mean()), 3), "n_tracks": len(pop),
           "decision": decision}
    write_json(out / "summary.json", res)
    _figure(df, cfg, out / "fig_h39.png")
    return res


def _figure(df, cfg, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    edges = np.arange(0, 70, 5)
    for arm, col in zip(ARMS, ("#555555", "#1f77b4", "#d62728", "#ff7f0e", "#2ca02c", "#9467bd")):
        d = df[(df.arm == arm) & df.scored]
        b = np.digitize(d.dist, edges)
        xs, ys = [], []
        for i in np.unique(b):
            m = b == i
            if m.sum() >= 20:
                xs.append(edges[i - 1] + 2.5)
                ys.append(np.sqrt(np.mean(d.err[m] ** 2)))
        ax[0].plot(xs, ys, "o-", color=col, label=arm, ms=3)
        if arm in ("A2_auto_all", "A2f_datasheet_f"):
            ax[1].scatter(d.dist, d.err, s=1, alpha=0.15, color=col)
    ax[0].axhline(0.5, ls=":", color="k")
    ax[0].set(xlabel="ground distance from camera (m)", ylabel="world RMSE (m)", yscale="log",
              title="H39: foot-point world error by range")
    ax[0].legend(fontsize=8)
    ax[1].set(xlabel="ground distance from camera (m)", ylabel="|error| (m)", title="A2 (red) / A2f (green) per box",
              yscale="log")
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    bins = [k for k in next(iter(res["rmse"].values()))]
    lines = ["| arm | " + " | ".join(bins) + " |", "|---" * (len(bins) + 1) + "|"]
    for arm, r in res["rmse"].items():
        cells = []
        for k in bins:
            v = r[k]
            cells.append("—" if v["rmse"] is None else f"{v['rmse']} [{v['ci95'][0]}, {v['ci95'][1]}]"
                         + (f" n={v['n_boxes']}" if v["n_boxes"] else ""))
        lines.append(f"| {arm} | " + " | ".join(cells) + " |")
    lines += ["", "| arm | tracks | height MAE (m) | mean signed (m) |", "|---|---|---|---|"]
    for arm, h in res["heights"].items():
        lines.append(f"| {arm} | {h['tracks']} | {h['mae_m']} | {h['mean_signed_m']} |")
    lines += ["", "| camera | boxes | true f / pitch / h | A2 f / pitch / h | A3 | A2f (f fixed) pitch / roll / h |",
              "|---|---|---|---|---|---|"]
    for k, c in res["cameras"].items():
        t, a2, a3, af = (c["true"], c["fits"]["A2_auto_all"], c["fits"]["A3_auto_10s"],
                         c["fits"]["A2f_datasheet_f"])
        lines.append(f"| {k} | {c['n_boxes']} | {t['f']} / {t['pitch']} / {t['h']} | "
                     f"{a2['f']:.0f} / {a2['pitch']:.1f} / {a2['h']:.2f} | "
                     f"{a3['f']:.0f} / {a3['pitch']:.1f} / {a3['h']:.2f} | "
                     f"{af['pitch']:.1f} / {af['roll']:.1f} / {af['h']:.2f} |")
    lines += ["", f"excluded: {res['excluded']}", (f"population mean height {res['population_height_mean_m']} m "
              f"over {res['n_tracks']} tracks; decision: {res['decision']}")]
    return "\n".join(lines) + "\n"
