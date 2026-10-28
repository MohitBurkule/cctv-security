"""H56: PTZ slew-to-alarm acquisition and second-alarm contention (pre-registered in docs/research/32).

A fixed camera alarms on a person; the VMS turns that detection into a world
estimate (with calibration error drawn from H39's datasheet-focal arm) and
slews the nearest PTZ to it. The PTZ is blind while slewing and zooming; the
target keeps walking. Acquisition is judged with the one definition of
visible, ``geometry.usably_visible``, against a Camera built at the PTZ's
*live* pose and zoom (principle 2), never against the commanded estimate.

    python -m cctvsec.experiments.ptz_slew [--out out/experiments/h56_ptz_slew]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from survsim.core.geometry import in_view, pixel_heights, usably_visible
from survsim.core.models import Camera, Capture, Mount, Optics

# ------------------------------------------------------------------ site

def fixed_cameras(cfg: dict[str, Any], rng: np.random.Generator) -> list[Camera]:
    s = cfg["site"]
    nx, ny = s["grid"]
    xs = (np.arange(nx) + 0.5) * s["w"] / nx
    ys = (np.arange(ny) + 0.5) * s["h"] / ny
    cams = []
    for i, (x, y) in enumerate((x, y) for y in ys for x in xs):
        cams.append(Camera(id=f"cam_{i:02d}", mount=Mount(pos=(float(x), float(y), s["cam_h"]),
                                                              yaw=float(rng.uniform(-180, 180)), pitch=s["cam_pitch"]),
                           optics=Optics(hfov_deg=s["cam_hfov"]), capture=Capture(res=tuple(s["res"]))))
    return cams


def ptz_camera(pos: tuple[float, float, float], yaw: float, pitch: float, hfov: float, res) -> Camera:
    return Camera(id="ptz", type="ptz", mount=Mount(pos=pos, yaw=yaw, pitch=pitch),
                  optics=Optics(hfov_deg=hfov), capture=Capture(res=tuple(res)))


def sample_targets(cams: list[Camera], cfg: dict[str, Any], rng: np.random.Generator, n: int):
    """n ground points visible (usably) to >= 1 fixed camera, with the nearest such camera and its distance."""
    s, hgt = cfg["site"], cfg["target"]["height_m"]
    out_p, out_c = [], []
    while len(out_p) < n:
        pts = np.c_[rng.uniform(0, s["w"], 4 * n), rng.uniform(0, s["h"], 4 * n), np.zeros(4 * n)]
        vis = np.stack([in_view(c, pts) & (pixel_heights(c, pts, hgt) >= 20.0) for c in cams], 1)
        pos = np.array([c.mount.pos for c in cams])
        dist = np.hypot(pts[:, None, 0] - pos[None, :, 0], pts[:, None, 1] - pos[None, :, 1])
        dist = np.where(vis, dist, np.inf)
        ok = np.isfinite(dist.min(1))
        for p, k in zip(pts[ok], dist[ok].argmin(1)):
            out_p.append(p)
            out_c.append(k)
    return np.array(out_p[:n]), np.array(out_c[:n])


def calib_error(p: np.ndarray, cam_xy: np.ndarray, arm: str, cfg: dict[str, Any], rng: np.random.Generator):
    """World-estimate error for one detection: range-dominated, RMSE r(d) (H39 datasheet-focal arm)."""
    c = cfg["calib"]
    d = float(np.hypot(*(p[:2] - cam_xy)))
    if arm == "exact":
        r = c["exact_rmse"]
    else:
        f = np.clip((d - c["near_m"]) / (c["far_m"] - c["near_m"]), 0.0, 1.0)
        r = c["near_rmse"] + f * (c["far_rmse"] - c["near_rmse"])
    k = c["lateral_ratio"]
    s_r = r / np.sqrt(1 + k * k)
    u = (p[:2] - cam_xy) / max(d, 1e-6)
    v = np.array([-u[1], u[0]])
    e = rng.normal(0, s_r) * u + rng.normal(0, k * s_r) * v
    return np.r_[p[:2] + e, 0.0], d


# ------------------------------------------------------------------ one alarm

def aim(ptz_pos, est, cfg):
    p = cfg["ptz"]
    dx, dy = est[0] - ptz_pos[0], est[1] - ptz_pos[1]
    rng_h = float(np.hypot(dx, dy))
    yaw = float(np.degrees(np.arctan2(dy, dx)))
    pitch = float(np.degrees(np.arctan2(p["aim_h_m"] - ptz_pos[2], rng_h)))
    slant = float(np.hypot(rng_h, ptz_pos[2] - p["aim_h_m"]))
    hfov = float(np.clip(np.degrees(2 * np.arctan(p["frame_w_m"] / 2 / slant)), p["hfov_min"], p["hfov_max"]))
    return yaw, pitch, hfov


def slew_time(pose0, pose1, cfg) -> float:
    dyaw = abs((pose1[0] - pose0[0] + 180) % 360 - 180)
    return max(dyaw, abs(pose1[1] - pose0[1])) / cfg["ptz"]["speed_dps"]


def acquire(ptz_pos, pose, t_ready, t_arrive, p0, vel, cfg) -> tuple[bool, float]:
    """(acquired within window, first acquire time rel. arrival). GT on the live camera at its reached pose."""
    win, dt, hgt = cfg["acquire_window_s"], cfg["tick_s"], cfg["target"]["height_m"]
    cam = ptz_camera(tuple(ptz_pos), pose[0], pose[1], pose[2], cfg["site"]["res"])
    t = t_ready
    while t <= t_arrive + win + 1e-9:
        pos = p0 + vel * (t - t_arrive)
        if usably_visible(cam, pos, person_height_m=hgt):
            return True, t - t_arrive
        t += dt
    return False, float("nan")


def home_pose(rng, cfg):
    return (float(rng.uniform(-180, 180)), cfg["ptz"]["home_pitch"], cfg["ptz"]["hfov_max"])


def run_seed(seed: int, cfg: dict[str, Any]) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    cams = fixed_cameras(cfg, rng)
    cam_xy = np.array([c.mount.pos[:2] for c in cams])
    pz, spd = cfg["ptz"], cfg["target"]["speed_mps"]
    rows: list[dict[str, Any]] = []
    # ---- independent alarms (no contention); common random numbers across arms
    n = int(cfg["n_alarms_indep"])
    pts, ck = sample_targets(cams, cfg, rng, n)
    for i in range(n):
        head = rng.uniform(0, 2 * np.pi)
        vel = spd * np.array([np.cos(head), np.sin(head), 0.0])
        home = home_pose(rng, cfg)
        err_seed = int(rng.integers(2**31))
        for calib in ("exact", "h39"):
            est, d = calib_error(pts[i], cam_xy[ck[i]], calib, cfg, np.random.default_rng(err_seed))
            for n_ptz, poles in cfg["ptz_arms"].items():
                poles3 = [(x, y, pz["h"]) for x, y in poles]
                j = int(np.argmin([np.hypot(est[0] - x, est[1] - y) for x, y, _ in poles3]))
                pose = aim(poles3[j], est, cfg)
                t_ready = pz["latency_s"] + slew_time(home, pose, cfg) + pz["zoom_s"]
                ok, _ = acquire(poles3[j], pose, t_ready, 0.0, pts[i], vel, cfg)
                rows.append({"mode": "indep", "seed": seed, "calib": calib, "n_ptz": int(n_ptz), "d": d,
                             "err_m": float(np.hypot(*(est[:2] - pts[i][:2]))), "t_ready": t_ready, "acq": ok})
    # ---- contention: Poisson alarms for contention_hours
    T = cfg["contention_hours"] * 3600.0
    lam = cfg["alarm_rate_per_h"] / 3600.0
    arr = np.cumsum(rng.exponential(1 / lam, int(3 * lam * T) + 50))
    arr = arr[arr < T]
    cpts, cck = sample_targets(cams, cfg, rng, len(arr))
    heads = rng.uniform(0, 2 * np.pi, len(arr))
    err_seeds = rng.integers(2**31, size=len(arr))
    homes = [home_pose(rng, cfg) for _ in cfg["ptz_arms"]["2"]]
    for calib in ("exact", "h39"):
        for n_ptz, poles in cfg["ptz_arms"].items():
            poles3 = [(x, y, pz["h"]) for x, y in poles]
            free = [0.0] * len(poles3)
            pose_now = list(homes[: len(poles3)])
            for a, t0 in enumerate(arr):
                vel = spd * np.array([np.cos(heads[a]), np.sin(heads[a]), 0.0])
                est, d = calib_error(cpts[a], cam_xy[cck[a]], calib, cfg, np.random.default_rng(int(err_seeds[a])))
                busy = all(f > t0 for f in free)
                cand = [k for k in range(len(poles3)) if free[k] <= t0]
                if cand:
                    j = min(cand, key=lambda k: np.hypot(est[0] - poles3[k][0], est[1] - poles3[k][1]))
                else:
                    j = int(np.argmin(free))
                t_start = max(t0, free[j])
                pose = aim(poles3[j], est, cfg)
                t_ready = t_start + pz["latency_s"] + slew_time(pose_now[j], pose, cfg) + pz["zoom_s"]
                ok, _ = acquire(poles3[j], pose, t_ready, t0, cpts[a], vel, cfg)
                free[j] = t_ready + pz["dwell_s"]
                pose_now[j] = pose
                rows.append({"mode": "contention", "seed": seed, "calib": calib, "n_ptz": int(n_ptz), "d": d,
                             "busy_at_arrival": busy, "acq": ok, "missed_second": busy and not ok})
    return {"seed": seed, "rows": rows}


# ------------------------------------------------------------------ stats

def seed_boot(per_seed_num: np.ndarray, per_seed_den: np.ndarray, n_boot: int, rng) -> list[float]:
    k = len(per_seed_num)
    idx = rng.integers(0, k, (n_boot, k))
    num, den = per_seed_num[idx].sum(1), per_seed_den[idx].sum(1)
    v = num / np.maximum(den, 1)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def summarise(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd
    df = pd.DataFrame(rows)
    brng = np.random.default_rng(int(cfg["seed"]))
    seeds = sorted(df.seed.unique())
    out: dict[str, Any] = {"acquire": {}, "contention": {}}
    ind = df[df["mode"] == "indep"]
    for (calib, n_ptz), g in ind.groupby(["calib", "n_ptz"]):
        key = f"{calib}_{n_ptz}ptz"
        out["acquire"][key] = {}
        for lo, hi in cfg["bins"]:
            b = g[(g.d > lo) & (g.d <= hi)] if lo > 0 else g[g.d <= hi]
            num = np.array([b[b.seed == s].acq.sum() for s in seeds], float)
            den = np.array([(b.seed == s).sum() for s in seeds], float)
            out["acquire"][key][f"{lo}-{hi}"] = {"rate": float(num.sum() / den.sum()), "n": int(den.sum()),
                                                  "ci95": seed_boot(num, den, cfg["n_boot"], brng),
                                                  "err_rmse_m": float(np.sqrt((b.err_m ** 2).mean()))}
    con = df[df["mode"] == "contention"]
    for (calib, n_ptz), g in con.groupby(["calib", "n_ptz"]):
        key = f"{calib}_{n_ptz}ptz"
        den = np.array([(g.seed == s).sum() for s in seeds], float)
        r = {"n_alarms": int(den.sum())}
        for col in ("missed_second", "busy_at_arrival", "acq"):
            num = np.array([g[g.seed == s][col].sum() for s in seeds], float)
            r[col] = {"rate": float(num.sum() / den.sum()), "ci95": seed_boot(num, den, cfg["n_boot"], brng)}
        out["contention"][key] = r
    a = out["acquire"]["h39_1ptz"]
    near, far = a[f"{cfg['bins'][0][0]}-{cfg['bins'][0][1]}"], a[f"{cfg['bins'][2][0]}-{cfg['bins'][2][1]}"]
    ms = out["contention"]["h39_1ptz"]["missed_second"]["rate"]
    out["decision"] = {"near_ge_0.9": near["rate"] >= 0.9, "far_le_0.6": far["rate"] <= 0.6,
                       "missed_second_ge_0.30": ms >= 0.30}
    out["decision"]["met"] = all(out["decision"].values())
    return out


def markdown_rows(body: dict[str, Any], cfg: dict[str, Any]) -> str:
    lines = ["| arm | " + " | ".join(f"acq@3s {lo}-{hi} m" for lo, hi in cfg["bins"]) + " | busy@arrival | missed_second |",
             "|---|" + "---|" * (len(cfg["bins"]) + 2)]
    for key, bins in body["acquire"].items():
        c = body["contention"][key]
        cells = [f"{v['rate']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] (n {v['n']})" for v in bins.values()]
        lines.append(f"| {key} | " + " | ".join(cells)
                     + f" | {c['busy_at_arrival']['rate']:.3f} | {c['missed_second']['rate']:.3f} "
                       f"[{c['missed_second']['ci95'][0]:.3f}, {c['missed_second']['ci95'][1]:.3f}] |")
    lines.append(f"\ndecision: {body['decision']}\n")
    return "\n".join(lines)


def figure(body: dict[str, Any], cfg: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
    labels = [f"{lo}-{hi if hi < 1000 else ''} m".replace("- m", "+ m") for lo, hi in cfg["bins"]]
    keys = list(body["acquire"])
    w = 0.8 / len(keys)
    for i, k in enumerate(keys):
        v = list(body["acquire"][k].values())
        r = np.array([x["rate"] for x in v])
        lo = r - np.array([x["ci95"][0] for x in v])
        hi = np.array([x["ci95"][1] for x in v]) - r
        ax1.bar(np.arange(len(v)) + i * w, r, w, yerr=[lo, hi], label=k, capsize=2)
    ax1.axhline(0.9, ls="--", c="k", lw=0.8)
    ax1.axhline(0.6, ls=":", c="k", lw=0.8)
    ax1.set_xticks(np.arange(len(labels)) + 0.4 - w / 2, labels)
    ax1.set_ylabel("acquired within 3 s")
    ax1.set_xlabel("distance from detecting fixed camera")
    ax1.set_ylim(0, 1.05)
    ax1.legend(fontsize=7)
    ax1.set_title("H56 slew-to-alarm acquisition")
    ks = list(body["contention"])
    r = np.array([body["contention"][k]["missed_second"]["rate"] for k in ks])
    ci = np.array([body["contention"][k]["missed_second"]["ci95"] for k in ks])
    ax2.bar(ks, r, yerr=[r - ci[:, 0], ci[:, 1] - r], capsize=3, color="tab:red")
    ax2.axhline(0.30, ls="--", c="k", lw=0.8)
    ax2.set_ylabel("share of alarms missed (all PTZs busy)")
    ax2.set_title(f"contention at {cfg['alarm_rate_per_h']:.0f} alarms/h")
    ax2.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import get_context
    seeds = [int(cfg["seed_base"]) + s for s in range(int(cfg["n_seeds"]))]
    with get_context("fork").Pool(min(len(seeds), int(cfg.get("workers", 8)))) as pool:
        res = pool.starmap(run_seed, [(s, cfg) for s in seeds])
    rows = [r for x in res for r in x["rows"]]
    import pandas as pd
    pd.DataFrame(rows).to_parquet(out / "alarms.parquet")
    body = summarise(rows, cfg)
    figure(body, cfg, out / "fig_h56.png")
    return body


def main() -> None:
    from cctvsec.experiments import _env, load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="h56_ptz_slew")
    ap.add_argument("--out", default="out/experiments/h56_ptz_slew")
    ap.add_argument("--n-seeds", type=int)
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.n_seeds:
        cfg["n_seeds"] = a.n_seeds
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    body = run(cfg, out)
    res = {"experiment": cfg["name"], "hypothesis": cfg["hypothesis"],
           "config": {k: v for k, v in cfg.items() if not k.startswith("_")}, "env": _env(),
           "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "wall_seconds": round(time.time() - t0, 1), **body}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (out / "row.md").write_text(markdown_rows(body, cfg))
    print(markdown_rows(body, cfg))


if __name__ == "__main__":
    main()
