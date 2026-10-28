"""H32d: which cctv_night_lowlight stage takes night recall from 0.890 (raw) to 0.006 (shipped)?

Leave-one-out (LOO: shipped minus one stage group) and add-one-in (AOI: raw plus one group) on the
same 60 frames as H32c (out/showcase/showcase_all_night, cam_01/cam_02/cam_ptz, frames 3..98 stride 5),
YOLOv8n CPU imgsz 1280, conf 0.25, IoU 0.5, GT h >= 20 px and vis > 0, paired block bootstrap over
12 blocks of 30 render frames. Each variant is degraded exactly as H32c's arms were (the 20 sampled
frames of a camera as one sequence: `Profile._pre_codec` with apply_sequence's seeds, then
`h264_sequence` when the codec is on), OSD off everywhere. "full" must reproduce H32c's shipped arm.

Stage groups (profile fields switched to their no-op values):
  exposure : metered AE (ae_target 48.65), auto-levels 0.39, gamma 1.02
  optics   : defocus 1.52, vignette, chromatic aberration, lens dirt
  noise    : shot/read noise, FPN, hot pixels, grain
  isp      : bilateral denoise, unsharp mask, dark-flat quantisation
  codec    : H.264 crf 39, gop 8, bf 2 (sequence round trip)
  colour   : saturation 0.56, white-balance gains (0.70, 1.0, 1.03)
Resize 640x360 -> 1280x720 is not a group (it is the detector's input size in every arm) and the
OSD overlay is off in every arm (H32c's arms had it off too). LLVIP (hold-out 10 frames) is only
measured for the luma/sigma hard negative: the profile is being diagnosed here, not calibrated.
Pre-registered in docs/research/32 §H32d.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import numpy as np

from . import night_noise_check as nn
from .common import batch_cameras, rpath, write_json

GROUPS: dict[str, dict[str, Any]] = {
    "exposure": {"ae_target": 0.0, "auto_levels": 0.0, "gamma": 1.0, "ev": 0.0,
                 "ae_drift_ev": 0.0, "rolling": 0.0},
    "optics": {"defocus": 0.0, "vignette": 0.0, "chroma_px": 0.0, "dirt": 0.0},
    "noise": {"iso_gain": 1e-6, "read_noise": 0.0, "fpn": 0.0, "hot_pixels": 0.0, "grain_sigma": 0.0},
    "isp": {"denoise": 0.0, "sharpen": 0.0, "dark_flatten": 0.0},
    "codec": {},   # the `codec` flag, not a profile field
    "colour": {"saturation": 1.0, "wb_gains": (1.0, 1.0, 1.0), "awb_drift": 0.0},
}


def variants() -> list[str]:
    return ["full"] + [f"loo_{g}" for g in GROUPS] + [f"aoi_{g}" for g in GROUPS]


def variant_spec(name: str, profile: str = "cctv_night_lowlight"):
    """-> (Profile, codec_on). full = every group; loo_g = all but g; aoi_g = only g (resize kept)."""
    from survsim.sensors.degrade import PROFILES
    if name == "full":
        on = set(GROUPS)
    elif name[:4] in ("loo_", "aoi_") and name[4:] in GROUPS:
        on = set(GROUPS) - {name[4:]} if name.startswith("loo_") else {name[4:]}
    else:
        raise ValueError(name)
    kw: dict[str, Any] = {"osd": False}
    for g, fields in GROUPS.items():
        if g not in on:
            kw.update(fields)
    return dataclasses.replace(PROFILES[profile], **kw), "codec" in on


def degrade(frames: list[np.ndarray], name: str, seq_seed: int, profile: str = "cctv_night_lowlight"):
    """apply_sequence's exact calls, with the codec optional."""
    from survsim.sensors.degrade import h264_sequence
    p, codec = variant_spec(name, profile)
    pre = [np.clip(p._pre_codec(f, seed=hash((seq_seed, i)) & 0x7FFFFFFF, frame_index=i,
                                sequence_seed=seq_seed), 0, 255).astype(np.uint8) for i, f in enumerate(frames)]
    out = h264_sequence(pre, p.crf, p.fps, p.codec_scale, gop=p.gop, bf=p.bf) if codec else pre
    return [np.clip(p.post_codec(x), 0, 255).astype(np.uint8) for x in out]


def shares(R: dict[str, Any]) -> dict[str, Any]:
    loss = np.asarray(R["raw"], float) - np.asarray(R["full"], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        den = np.where(loss > 0, loss, np.nan)
        return {"loss": loss,
                "loo": {g: (np.asarray(R[f"loo_{g}"], float) - np.asarray(R["full"], float)) / den for g in GROUPS},
                "aoi": {g: (np.asarray(R["raw"], float) - np.asarray(R[f"aoi_{g}"], float)) / den for g in GROUPS}}


def _ci(pt, bs) -> list:
    bs = np.asarray(bs, float)
    bs = bs[~np.isnan(bs)]
    lo, hi = np.percentile(bs, [2.5, 97.5]) if len(bs) else (np.nan, np.nan)
    return [round(float(pt), 4), round(float(lo), 4), round(float(hi), 4)]


def bootstrap(hits: dict[str, np.ndarray], n: np.ndarray, n_boot: int, seed: int) -> dict[str, Any]:
    idx = np.random.default_rng(seed).integers(0, len(n), size=(n_boot, len(n)))
    Rp = {v: h.sum() / max(n.sum(), 1) for v, h in hits.items()}
    Rb = {v: h[idx].sum(1) / np.maximum(n[idx].sum(1), 1) for v, h in hits.items()}
    sp, sb = shares(Rp), shares(Rb)
    return {"recall": {v: _ci(Rp[v], Rb[v]) for v in hits}, "loss": _ci(sp["loss"], sb["loss"]),
            "loo": {g: _ci(sp["loo"][g], sb["loo"][g]) for g in GROUPS},
            "aoi": {g: _ci(sp["aoi"][g], sb["aoi"][g]) for g in GROUPS},
            "loo_sum": round(float(sum(sp["loo"].values())), 4),
            "aoi_sum": round(float(sum(sp["aoi"].values())), 4), "_pt": sp}


def out_of_band(luma: float, sigma: float, band: dict[str, float], real_sigma: float) -> dict[str, float]:
    """Distance outside the LLVIP hold-out bands: luma grey levels beyond p10-p90; |log2 sigma ratio|."""
    return {"luma": round(max(0.0, luma - band["p90"], band["p10"] - luma), 3),
            "sigma_log2": round(abs(float(np.log2(max(sigma, 1e-9) / real_sigma))), 3)}


def decide(pt: dict[str, Any], dist: dict[str, dict[str, float]], D: dict[str, Any]) -> dict[str, Any]:
    loo = {g: float(v) for g, v in pt["loo"].items()}
    aoi = {g: float(v) for g, v in pt["aoi"].items()}
    culprit = max(loo, key=lambda g: -1e9 if np.isnan(loo[g]) else loo[g])
    ok_loss = bool(pt["loss"] >= D["min_loss"])
    met = bool(ok_loss and loo[culprit] >= D["share_min"] and aoi[culprit] >= D["share_min"])
    s, c = dist["full"], dist[f"loo_{culprit}"]
    hn = bool(c["luma"] <= s["luma"] + D["hn_tol_luma"] and c["sigma_log2"] <= s["sigma_log2"] + D["hn_tol_log2"])
    return {"loss_ok": ok_loss, "culprit": culprit, "culprit_loo_share": round(loo[culprit], 4),
            "culprit_aoi_share": round(aoi[culprit], 4), "decision_met": met,
            "predicted": D["predicted_culprit"], "prediction_correct": bool(met and culprit == D["predicted_culprit"]),
            "HN_ok": hn, "HN_shipped": s, "HN_without_culprit": c}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    from survsim.realism.stats import band, list_images

    from .night import _recall_h
    hold = sorted(list_images(rpath(cfg["real_root"])))[cfg["tune_n"]:]
    rh = nn._stats([cv2.imread(str(p)) for p in hold])
    real_sig = float(np.median([r["noise_sigma"] for r in rh]))
    lb = band([r["luma_mean"] for r in rh])

    rd = rpath(cfg["run_dir"])
    cams = batch_cameras(rd.parent, rd.name, "raw", min_vis=cfg["min_vis"])
    fr = nn.frames_for(cfg)
    raw = {c: [cv2.imread(str(cams[c]["frames"][f])) for f in fr] for c in cfg["cams"]}
    seeds = {c: i for i, c in enumerate(cfg["cams"])}
    net = YOLO(str(rpath(cfg["model"])))
    V = ["raw"] + variants()
    rows: dict[str, dict] = {v: {} for v in V}
    med: dict[str, dict[str, float]] = {}
    for v in V:
        st = []
        for c in cfg["cams"]:
            imgs = raw[c] if v == "raw" else degrade(raw[c], v, seeds[c], cfg["profile"])
            st += nn._stats(imgs)
            d = out / "frames" / v / c
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{fr[len(fr) // 2]:04d}.png"), imgs[len(fr) // 2])
            sx = imgs[0].shape[1] / raw[c][0].shape[1]
            for f, im in zip(fr, imgs):
                p = net.predict(im, classes=[0], conf=cfg["conf"], imgsz=cfg["imgsz"], device="cpu",
                                verbose=False, max_det=1000)[0]
                dets = [{"bbox": [a0 / sx, b0 / sx, (x1 - a0) / sx, (y1 - b0) / sx], "score": float(sc)}
                        for (a0, b0, x1, y1), sc in zip(p.boxes.xyxy.numpy().tolist(), p.boxes.conf.numpy())]
                k, n = _recall_h({f: cams[c]["gt"].get(f, [])}, {f: dets}, cfg["min_h"], cfg["conf"])
                b = (c, nn.block_of(f, cfg["block_frames"]))
                t = rows[v].get(b, (0, 0))
                rows[v][b] = (t[0] + k, t[1] + n)
        med[v] = {k: round(float(np.median([r[k] for r in st])), 4) for k in ("noise_sigma", "luma_mean")}
        print("variant", v, med[v], flush=True)
    keys = sorted(rows["raw"])
    hits = {v: np.array([rows[v][b][0] for b in keys], float) for v in V}
    n = np.array([rows["raw"][b][1] for b in keys], float)
    bs = bootstrap(hits, n, cfg["n_boot"], cfg["seed"])
    pt = bs.pop("_pt")
    dist = {v: out_of_band(med[v]["luma_mean"], med[v]["noise_sigma"], lb, real_sig) for v in V}
    res: dict[str, Any] = {
        "real": {"n_hold": len(hold), "sigma_hold_median": round(real_sig, 4), "luma_hold_band": lb},
        "n_frames": len(fr) * len(cfg["cams"]), "n_gt": int(n.sum()), "n_blocks": len(keys),
        "median": med, "out_of_band": dist, **bs,
        "sanity_full_vs_h32c_shipped": round(abs(bs["recall"]["full"][0] - cfg["h32c_shipped_recall"]), 4),
        "per_block": {v: {f"{c}/{b}": rows[v][(c, b)] for (c, b) in keys} for v in V},
    }
    res["sanity_ok"] = bool(res["sanity_full_vs_h32c_shipped"] <= cfg["decision"]["sanity_tol"])
    res["decision"] = decide(pt, dist, cfg["decision"])
    write_json(out / "summary.json", res)
    figure(res, rpath(cfg["figure"]))
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [f"{res['n_frames']} frames, {res['n_blocks']} blocks, n GT = {res['n_gt']}; loss raw->full {res['loss']}", "",
         "| variant | recall [95 % CI] | σ | luma |", "|---|---|---|---|"]
    L += [f"| {v} | {res['recall'][v]} | {res['median'][v]['noise_sigma']} | {res['median'][v]['luma_mean']:.1f} |"
          for v in res["recall"]]
    L += ["", "| group | LOO share | AOI share |", "|---|---|---|"]
    L += [f"| {g} | {res['loo'][g]} | {res['aoi'][g]} |" for g in GROUPS]
    L += ["", f"sums LOO {res['loo_sum']}, AOI {res['aoi_sum']}; sanity {res['sanity_full_vs_h32c_shipped']}",
          f"decision: {res['decision']}"]
    return "\n".join(L) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
    vs = list(res["recall"])
    p = np.array([res["recall"][v] for v in vs], float)
    axs[0].bar(np.arange(len(vs)), p[:, 0], yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], capsize=2, color="#557")
    axs[0].set_xticks(np.arange(len(vs)), vs, rotation=60, fontsize=7)
    axs[0].set_ylim(0, 1)
    axs[0].set_title(f"YOLOv8n recall, GT ≥ 20 px, conf 0.25 (n={res['n_gt']})")
    x = np.arange(len(GROUPS))
    for j, (k, col) in enumerate((("loo", "#37a"), ("aoi", "#c64"))):
        q = np.array([res[k][g] for g in GROUPS], float)
        axs[1].bar(x + (j - 0.5) * 0.4, q[:, 0], 0.4, yerr=[q[:, 0] - q[:, 1], q[:, 2] - q[:, 0]], capsize=2,
                   color=col, label={"loo": "leave-one-out", "aoi": "add-one-in"}[k])
    axs[1].axhline(0.6, ls=":", color="grey")
    axs[1].axhline(0, color="k", lw=0.5)
    axs[1].set_xticks(x, list(GROUPS))
    axs[1].legend(fontsize=8)
    axs[1].set_title("share of raw→shipped recall loss; decision line 0.60")
    fig.suptitle("H32d cctv_night_lowlight stage ablation, showcase_all_night (diagnosis, not calibration)")
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
