"""H3g: is cctv_day_720p's sensor noise too strong, and does matching it to real CCTV recover far recall?

Stage 1 (estimate + refit, no detector). Noise estimator: Immerkaer (1996) MAD-of-Laplacian,
exactly `survsim.realism.stats.noise_sigma` (3x3 Laplacian-difference kernel, mean-|r| form
sigma = sqrt(pi/2) * mean|r| / 6, over the flattest 50 % of pixels by smoothed Sobel magnitude),
on 8-bit luma after resizing to 720 lines (`frame_stats`). It is applied identically to the 12 real
day CCTV frames (~/data/real_cctv, MOT16/17/20 -- non-commercial: measured only), to raw renders
and to the profile's output. Output-referred sigma is in 0-255 luma units.

Refit: only the noise stage is scaled, by one factor s on the noise *standard deviation*:
iso_gain -> iso_gain * s^2 and read_noise, fpn -> * s (sensor variance g*x + rn^2 scales by s^2;
grain_sigma is a correlation length, not a level, and is left alone). Blur (optics), ISP, exposure
and codec are untouched. s is chosen so the median output sigma on short degraded render sequences
(full chain, sequence codec) equals the median real-frame sigma, by linear interpolation on a fixed
grid of s; it is clamped to the grid ends (and says so) if the target lies outside.

Stage 2 (detect): the matched profile re-degrades the far cameras (H3f's 50 frames) and the near
camera (H3d's 99 cached frames), YOLOv8n CPU, H3f's arms (full_1280, tiles_d) and scoring. Raw and
shipped detections reuse the H3d cache. Pre-registered in docs/research/32 §H3g.
"""
from __future__ import annotations

import dataclasses
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from . import degrade_ablation_far as da
from . import far_field_cc0 as base
from .common import batch_cameras, rpath, write_json
from .far_field_h3c import collapse

REALISM_KEYS = ("noise_sigma", "lap_var_log10", "blockiness")   # noise / blur / blockiness


def scaled_profile(s: float, profile: str = "cctv_day_720p", fps: float = 12.5):
    """Shipped profile (OSD off) with only the noise-stage level scaled by s (std units)."""
    from survsim.sensors.degrade import PROFILES
    p = PROFILES[profile]
    return dataclasses.replace(p, osd=False, fps=fps, iso_gain=max(p.iso_gain * s * s, 1e-6),
                               read_noise=p.read_noise * s, fpn=p.fpn * s)


def input_sigma(p, x: float = 128.0) -> float:
    """Profile-unit noise level: per-pixel sensor std at signal x before grain/ISP/codec (DN)."""
    return float(np.sqrt(max(p.iso_gain, 0.0) * x + p.read_noise ** 2 + p.fpn ** 2))


def degrade(paths: list[Path], p, seq_seed: int, keep: list[int]) -> dict[int, np.ndarray]:
    """Same calls as degrade_ablation_far.degrade_stream (and survsim/video.py), any Profile."""
    import cv2

    from survsim.sensors.degrade import h264_sequence
    n = max(keep) + 1
    frames = [np.clip(p._pre_codec(cv2.imread(str(paths[i])), seed=hash((seq_seed, i)) & 0x7FFFFFFF,
                                   frame_index=i, sequence_seed=seq_seed), 0, 255).astype(np.uint8)
              for i in range(n)]
    frames = h264_sequence(frames, p.crf, p.fps, p.codec_scale, gop=p.gop, bf=p.bf)
    ks = set(keep)
    return {i: np.clip(f, 0, 255).astype(np.uint8) for i, f in enumerate(frames) if i in ks}


def stats_of(imgs) -> list[dict[str, float]]:
    from survsim.realism.stats import frame_stats
    return [{k: float(getattr(frame_stats(im), k)) for k in REALISM_KEYS} for im in imgs]


def fit_scale(grid: list[float], sig: list[float], target: float) -> dict[str, Any]:
    """Linear interpolation of s where sigma_out(s) = target; clamped at the grid ends."""
    g, v = np.asarray(grid, float), np.asarray(sig, float)
    o = np.argsort(v)
    if target <= v.min():
        return {"s": float(g[np.argmin(v)]), "clamped": "low"}
    if target >= v.max():
        return {"s": float(g[np.argmax(v)]), "clamped": "high"}
    return {"s": float(np.interp(target, v[o], g[o])), "clamped": None}


def in_band_count(stats: list[dict], band: dict[str, tuple[float, float]]) -> dict[str, Any]:
    per = [all(band[k][0] <= s[k] <= band[k][1] for k in REALISM_KEYS) for s in stats]
    return {"n_all3": int(sum(per)), "n": len(per),
            "per_stat": {k: int(sum(band[k][0] <= s[k] <= band[k][1] for s in stats)) for k in REALISM_KEYS}}


def recall_ci(G, I, preds: dict[str, dict], blocks, bands, split, cfg) -> dict[str, list]:
    cc = collapse({v: base.frame_counts(G, I, preds[v], bands, cfg["op_conf"], cfg["iou"]) for v in preds}, split)
    hits = {v: np.array([sum(cc[v][k]["hit"][1] for k in b) for b in blocks], float) for v in preds}
    n = np.array([sum(cc[next(iter(preds))][k]["n"][1] for k in b) for b in blocks], float)
    rng = np.random.default_rng(cfg["seed"])
    idx = rng.integers(0, len(n), size=(cfg["n_boot"], len(n)))
    R = {v: (h.sum() / n.sum(), h[idx].sum(1) / n[idx].sum(1)) for v, h in hits.items()}
    out = {v: da._ci(*R[v]) for v in R}
    out["drop_raw_matched"] = da._ci(R["raw"][0] - R["matched"][0], R["raw"][1] - R["matched"][1])
    out["n_gt"] = int(n.sum())
    return out


def decide(res: dict[str, Any], D: dict[str, Any]) -> dict[str, Any]:
    far = res["far"]["tiles_d"]["matched"][0]
    near = {a: res["near"][a]["drop_raw_matched"][0] for a in da.ARMS}
    ratio = res["noise"]["ratio_shipped_over_real"]
    hn = res["realism_hn"]["matched"]["n_all3"]
    return {"hyp_noise_ge_2x": bool(ratio >= D["noise_ratio_min"]), "ratio": round(ratio, 3),
            "far_tiles_matched": far, "far_ok": bool(far >= D["far_recall_min"]),
            "near_drop": near, "near_ok": bool(all(v < D["near_max_drop"] for v in near.values())),
            "decision_met": bool(far >= D["far_recall_min"] and all(v < D["near_max_drop"] for v in near.values())),
            "HN_realism_ok": bool(hn >= D["hn_min_frames"]), "HN_realism_frames": hn}


def _degrade_job(args):
    import cv2
    rdir, seq_seed, keep, out, s, profile, fps = args
    out = Path(out)
    if all((out / f"{i:04d}.png").is_file() for i in keep):
        return f"{out} cached"
    out.mkdir(parents=True, exist_ok=True)
    for i, x in degrade(sorted(Path(rdir).glob("*.png")), scaled_profile(s, profile, fps), seq_seed, keep).items():
        cv2.imwrite(str(out / f"{i:04d}.png"), x)
    return f"{out} done"


def _detect_job(args):
    import torch
    torch.set_num_threads(args[-1])
    cfg, fdir, keep, cache = args[:4]
    da.detect_dir(cfg, Path(fdir), keep, Path(cache))
    return cache


def estimate(cfg: dict[str, Any], batch: Path) -> dict[str, Any]:
    """Stage 1: sigma on real / raw / shipped, the s-grid curve, the fit (all CPU, no detector)."""
    from multiprocessing import Pool

    import cv2
    real = [cv2.imread(str(p)) for p in sorted(Path(cfg["real_dir"]).expanduser().glob("*.jpg"))]
    real_st = stats_of(real)
    sig_real = [s["noise_sigma"] for s in real_st]
    rd = batch / cfg["run"] / "render"
    cams = sorted(cfg["seq_seeds"])
    fk = list(range(cfg["fit_frames"]))
    jobs = [(str(rd / c), cfg["seq_seeds"][c], fk, s, cfg["profile"], cfg["fps"])
            for s in cfg["s_grid"] for c in cams]

    with Pool(cfg["workers"]) as pool:
        outs = pool.map(_fit_job, jobs)
    curve = []
    for s in cfg["s_grid"]:
        v = [x for j, o in zip(jobs, outs) if j[3] == s for x in o]
        curve.append(float(np.median(v)))
    raw = [cv2.imread(str(sorted((rd / c).glob("*.png"))[i])) for c in cams for i in fk]
    sig_raw = [s["noise_sigma"] for s in stats_of(raw)]
    target = float(np.median(sig_real))
    fit = fit_scale(cfg["s_grid"], curve, target)
    shipped = curve[cfg["s_grid"].index(1.0)]
    pm, ps = scaled_profile(fit["s"], cfg["profile"]), scaled_profile(1.0, cfg["profile"])
    band = {k: tuple(float(x) for x in np.percentile([s[k] for s in real_st], [10, 90])) for k in REALISM_KEYS}
    return {"estimator": "Immerkaer MAD-of-Laplacian, flattest 50 % (survsim.realism.stats.noise_sigma), luma @720p",
            "sigma_real_per_frame": [round(x, 3) for x in sig_real], "sigma_real_median": round(target, 3),
            "sigma_raw_render_median": round(float(np.median(sig_raw)), 3),
            "sigma_shipped_median": round(shipped, 3),
            "ratio_shipped_over_real": shipped / target,
            "s_grid": cfg["s_grid"], "sigma_out_by_s": [round(x, 3) for x in curve], "fit": fit,
            "shipped_units": {"iso_gain": ps.iso_gain, "read_noise": ps.read_noise, "fpn": ps.fpn,
                              "input_sigma_at_128": round(input_sigma(ps), 3)},
            "matched_units": {"iso_gain": round(pm.iso_gain, 4), "read_noise": round(pm.read_noise, 4),
                              "fpn": round(pm.fpn, 4), "input_sigma_at_128": round(input_sigma(pm), 3)},
            "real_band_p10_p90": band, "_real_stats": real_st}


def _fit_job(j):
    from survsim.realism.stats import frame_stats
    fr = degrade(sorted(Path(j[0]).glob("*.png")), scaled_profile(j[3], j[4], j[5]), j[1], j[2])
    return [float(frame_stats(x).noise_sigma) for x in fr.values()]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import Pool

    import cv2
    batch = rpath(cfg["batch_dir"])
    rn = cfg["run"]
    lic = base.check_licence(batch, [rn])
    if not all(lic.values()):
        raise RuntimeError(f"licence check failed: {lic}")
    est = estimate(cfg, batch)
    real_st = est.pop("_real_stats")
    s = est["fit"]["s"]
    write_json(Path(out) / "estimate.json", est)
    print("estimate", est["sigma_real_median"], est["sigma_shipped_median"], est["fit"], flush=True)
    raw = batch_cameras(batch, rn, "raw")
    h3d, fdir, ddir = rpath(cfg["h3d_dets_dir"]), rpath(cfg["frames_dir"]), rpath(cfg["dets_dir"])
    keep = {c: [f for f in sorted(raw[c]["frames"]) if f >= 1 and f % cfg["stride"] == cfg["offset"]]
            [::cfg["frames_every"]] for c in cfg["far_cams"]}
    nc = cfg["near_cam"]
    hr_near = pickle.loads((h3d / f"{rn}__raw__{nc}.pkl").read_bytes())
    hd_near = pickle.loads((h3d / f"{rn}__degraded__{nc}.pkl").read_bytes())
    keep[nc] = [f for f in sorted(hr_near) if f in hd_near]
    rd = batch / rn / "render"
    with Pool(min(cfg["workers"], len(keep))) as pool:
        for m in pool.imap_unordered(_degrade_job, [(str(rd / c), cfg["seq_seeds"][c], keep[c], str(fdir / c), s,
                                                     cfg["profile"], cfg["fps"]) for c in keep]):
            print("degrade", m, flush=True)
    with Pool(cfg["det_workers"]) as pool:
        for m in pool.imap_unordered(_detect_job, [(cfg, str(fdir / c), keep[c], str(ddir / f"matched__{c}.pkl"),
                                                    cfg["torch_threads"]) for c in keep]):
            print("detect", m, flush=True)
    bands = [tuple(b) for b in cfg["bands"]]
    mh = cfg["min_gt_height"]
    res: dict[str, Any] = {"licence_commercial_ml_ok": lic, "noise": est, "far": {}, "near": {}}
    for scope, cams, min_px, blk in (("far", cfg["far_cams"], cfg["primary_min_px"], cfg["block_sampled"]),
                                     ("near", [nc], cfg["hn_min_px"], cfg["hn_block_sampled"])):
        dets: dict[str, dict] = {}
        for c in cams:
            hr = pickle.loads((h3d / f"{rn}__raw__{c}.pkl").read_bytes())
            hd = pickle.loads((h3d / f"{rn}__degraded__{c}.pkl").read_bytes())
            hm = pickle.loads((ddir / f"matched__{c}.pkl").read_bytes())
            for v, d in (("raw", hr), ("shipped", hd), ("matched", hm)):
                dets.setdefault(v, {}).update({(c, f): d[f] for f in keep[c]})
        ks = sorted(dets["raw"])
        G = {k: [r for r in raw[k[0]]["gt"].get(k[1], []) if r["bbox"][3] >= mh] for k in ks}
        I = {k: [r for r in raw[k[0]]["gt"].get(k[1], []) if r["bbox"][3] < mh] for k in ks}
        split = next(i for i, b in enumerate(cfg["bands"]) if b[0] >= min_px)
        blocks = base.make_blocks(ks, blk)
        res[scope]["n_frames"], res[scope]["n_blocks"], res[scope]["min_px"] = len(ks), len(blocks), min_px
        for arm in da.ARMS:
            preds = {v: {k: da.arm_preds(d, cfg)[arm] for k, d in dv.items()} for v, dv in dets.items()}
            res[scope][arm] = recall_ci(G, I, preds, blocks, bands, split, cfg)
    # hard negative: realism stats of the matched output, 12 frames (4 per camera, evenly spaced)
    pick = {c: keep[c][:: max(1, len(keep[c]) // 4)][:4] for c in sorted(keep)}
    mt = [cv2.imread(str(fdir / c / f"{f:04d}.png")) for c in pick for f in pick[c]]
    sh = [cv2.imread(str(batch / rn / "video" / "degraded" / c / f"{f:04d}.png")) for c in pick for f in pick[c]]
    band = {k: tuple(v) for k, v in est["real_band_p10_p90"].items()}
    res["realism_hn"] = {"frames": {c: pick[c] for c in pick}, "matched": in_band_count(stats_of(mt), band),
                         "shipped": in_band_count(stats_of(sh), band),
                         "real_self": in_band_count(real_st, band)}
    res["decision"] = decide(res, cfg["decision"])
    if cfg.get("figure"):
        figure(res, rpath(cfg["figure"]))
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    e = res["noise"]
    L = [(f"noise sigma (luma, {e['estimator']}): real median {e['sigma_real_median']}, raw render "
          f"{e['sigma_raw_render_median']}, shipped {e['sigma_shipped_median']}, ratio {e['ratio_shipped_over_real']:.3f}"),
         f"fit {e['fit']}; curve s {e['s_grid']} -> {e['sigma_out_by_s']}",
         f"shipped units {e['shipped_units']}; matched units {e['matched_units']}", ""]
    for scope in ("far", "near"):
        r = res[scope]
        L += [f"**{scope}** ({r['n_frames']} frames, {r['n_blocks']} blocks, GT >= {r['min_px']} px)", "",
              "| arm | n GT | raw | shipped | matched | drop raw->matched |", "|---|---|---|---|---|---|"]
        L += [f"| {a} | {r[a]['n_gt']} | {r[a]['raw']} | {r[a]['shipped']} | {r[a]['matched']} | "
              f"{r[a]['drop_raw_matched']} |" for a in da.ARMS]
        L += [""]
    L += [f"realism HN: {res['realism_hn']}", f"decision: {res['decision']}"]
    return "\n".join(L) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e = res["noise"]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    axs[0].plot(e["s_grid"], e["sigma_out_by_s"], "o-", color="#37a", label="profile output (renders)")
    axs[0].axhline(e["sigma_real_median"], color="#c64", label="real CCTV median (12)")
    axs[0].axhline(e["sigma_raw_render_median"], color="grey", ls=":", label="raw render")
    axs[0].axvline(e["fit"]["s"], color="k", lw=0.6, ls="--", label=f"fit s={e['fit']['s']:.2f}")
    axs[0].set_xlabel("noise std scale s (1 = shipped)")
    axs[0].set_ylabel("MAD-of-Laplacian sigma (luma)")
    axs[0].legend(fontsize=8)
    labels, vals = [], []
    for scope in ("far", "near"):
        for a in da.ARMS:
            for v in ("raw", "shipped", "matched"):
                labels.append(f"{scope} {a}\n{v}")
                vals.append(res[scope][a][v])
    p = np.array(vals, float)
    cols = {"raw": "#888", "shipped": "#c64", "matched": "#3a7"}
    axs[1].bar(range(len(p)), p[:, 0], yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], capsize=2,
               color=[cols[lb.split("\n")[1]] for lb in labels])
    axs[1].set_xticks(range(len(p)), labels, rotation=70, fontsize=6)
    axs[1].axhline(0.6, ls=":", color="grey")
    axs[1].set_ylim(0, 1.05)
    axs[1].set_title("recall (far GT>=20 px, near GT>=80 px), conf 0.25, 95% block CI")
    fig.suptitle("H3g cctv_day_720p noise recalibrated to real CCTV (YOLOv8n, CPU)")
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
