"""H32c: is cctv_night_lowlight also over-noised, how much of the "renders are not dark" luma gap
does it close, and does matching its noise to real night CCTV recover person recall?

(1) Noise and luma. Same estimator as H3g (`survsim.realism.stats.frame_stats`: Immerkaer
MAD-of-Laplacian ``noise_sigma`` and ``luma_mean``, 8-bit luma at 720 lines) on the LLVIP visible
hold-out frames (last 10 of 25 sorted; the first 15 were the H32 tuning set), on the raw night
showcase render and on the profile's output. LLVIP is non-commercial research data: measured only,
never trained on or shipped.

(2) Noise-matched arm. Exactly H3g's refit (`noise_recalibration.scaled_profile`): one std factor s
on the noise stage (iso_gain*s^2, read_noise*s, fpn*s), everything else untouched, OSD off in both
shipped and matched arms so the arms differ only in noise level. s is fitted (grid + linear interp,
`noise_recalibration.fit_scale`) so the median output sigma on the detection frames equals the median
sigma of the 15 LLVIP *tuning* frames; the ratio and the luma band are read on the hold-out 10.

(3) Recall. YOLOv8n CPU, imgsz 1280, conf 0.25, IoU 0.5, GT rows h >= 20 px and MOT visibility > 0,
on <= 60 frames of out/showcase/showcase_all_night (3 cameras x 20 frames, stride 5). 95 % CI from a
paired block bootstrap over 30-render-frame blocks per camera. Pre-registered in docs/research/32 §H32c.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import numpy as np

from . import noise_recalibration as nr
from .common import batch_cameras, rpath, write_json

ARMS = ("raw", "shipped", "matched")


def arm_profile(s: float, profile: str = "cctv_night_lowlight"):
    """The shipped profile at its own fps with OSD off; noise level scaled by s (H3g's refit)."""
    from survsim.sensors.degrade import PROFILES
    return dataclasses.replace(nr.scaled_profile(s, profile, PROFILES[profile].fps), osd=False)


def frames_for(cfg: dict[str, Any]) -> list[int]:
    return list(range(cfg["frame_start"], cfg["frame_stop"], cfg["stride"]))


def block_of(f: int, block_frames: int) -> int:
    return (f - 1) // block_frames


def luma_gap(raw: float, prof: float, real: float, ae_target: float) -> dict[str, float]:
    """Fraction of the raw-real luma gap closed: measured, and predicted by the AE target alone."""
    g = raw - real
    return {"gap_raw": round(g, 2), "gap_profile": round(prof - real, 2),
            "closed_measured": round((raw - prof) / g, 3) if g else float("nan"),
            "closed_by_construction_ae": round((raw - ae_target) / g, 3) if g else float("nan")}


def block_boot(rows: dict[str, dict[tuple, tuple[int, int]]], n_boot: int, seed: int) -> dict[str, Any]:
    """rows[arm][(cam, block)] = (tp, n). Paired resampling of blocks; recall per arm + matched-shipped."""
    keys = sorted(rows["raw"])
    k = {a: np.array([rows[a][b][0] for b in keys], float) for a in rows}
    n = np.array([rows["raw"][b][1] for b in keys], float)
    idx = np.random.default_rng(seed).integers(0, len(keys), (n_boot, len(keys)))
    nb = np.maximum(n[idx].sum(1), 1)
    R = {a: (k[a].sum() / max(n.sum(), 1), k[a][idx].sum(1) / nb) for a in k}

    def ci(p, b):
        lo, hi = np.quantile(b, [.025, .975])
        return [round(float(p), 4), round(float(lo), 4), round(float(hi), 4)]
    out: dict[str, Any] = {a: ci(*R[a]) for a in R}
    out["delta_matched_shipped"] = ci(R["matched"][0] - R["shipped"][0], R["matched"][1] - R["shipped"][1])
    out["delta_raw_shipped"] = ci(R["raw"][0] - R["shipped"][0], R["raw"][1] - R["shipped"][1])
    out["n_gt"], out["n_blocks"] = int(n.sum()), len(keys)
    return out


def decide(res: dict[str, Any], D: dict[str, Any]) -> dict[str, Any]:
    d = res["recall"]["delta_matched_shipped"]
    hn = res["hard_negative"]["n_in_band"]
    return {"hyp_noise_ratio": res["noise"]["ratio_shipped_over_real"],
            "hyp_noise_met": bool(res["noise"]["ratio_shipped_over_real"] >= D["noise_ratio_min"]),
            "delta": d, "decision_met": bool(d[0] >= D["recall_delta_min"] and d[1] > 0),
            "HN_luma_frames": hn, "HN_ok": bool(hn >= D["hn_min_frames"])}


def _stats(imgs) -> list[dict[str, float]]:
    from survsim.realism.stats import frame_stats
    return [{k: float(getattr(frame_stats(im), k)) for k in ("noise_sigma", "luma_mean")} for im in imgs]


def _degrade(paths: list[Path], p, seed: int) -> list[np.ndarray]:
    import cv2

    from survsim.sensors.degrade import apply_sequence
    return [np.clip(x, 0, 255).astype(np.uint8)
            for x in apply_sequence([cv2.imread(str(q)) for q in paths], p, sequence_seed=seed)]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    from survsim.realism.stats import band, list_images

    from .night import _recall_h
    real = sorted(list_images(rpath(cfg["real_root"])))
    tune, hold = real[:cfg["tune_n"]], real[cfg["tune_n"]:]
    rt, rh = (_stats([cv2.imread(str(p)) for p in ps]) for ps in (tune, hold))
    real_sig_tune = float(np.median([r["noise_sigma"] for r in rt]))
    real_sig = float(np.median([r["noise_sigma"] for r in rh]))
    real_luma = [r["luma_mean"] for r in rh]
    lb = band(real_luma)

    rd = rpath(cfg["run_dir"])
    cams = batch_cameras(rd.parent, rd.name, "raw", min_vis=cfg["min_vis"])
    fr = frames_for(cfg)
    paths = {c: [cams[c]["frames"][f] for f in fr] for c in cfg["cams"]}
    seeds = {c: i for i, c in enumerate(cfg["cams"])}

    # fit s on the detection frames (grid), target = LLVIP tuning-frame median sigma
    grid_sig = []
    for s in cfg["s_grid"]:
        p = arm_profile(s, cfg["profile"])
        grid_sig.append(float(np.median([r["noise_sigma"] for c in cfg["cams"]
                                         for r in _stats(_degrade(paths[c], p, seeds[c]))])))
    fit = nr.fit_scale(cfg["s_grid"], grid_sig, real_sig_tune)
    scale = {"raw": None, "shipped": 1.0, "matched": fit["s"]}

    imgs: dict[str, dict[str, list[np.ndarray]]] = {}
    for a in ARMS:
        imgs[a] = {}
        for c in cfg["cams"]:
            imgs[a][c] = ([cv2.imread(str(q)) for q in paths[c]] if a == "raw"
                          else _degrade(paths[c], arm_profile(scale[a], cfg["profile"]), seeds[c]))
            d = out / "frames" / a / c
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{fr[len(fr) // 2]:04d}.png"), imgs[a][c][len(fr) // 2])
    st = {a: [r for c in cfg["cams"] for r in _stats(imgs[a][c])] for a in ARMS}
    med = {a: {k: round(float(np.median([r[k] for r in st[a]])), 4) for k in ("noise_sigma", "luma_mean")}
           for a in ARMS}

    net = YOLO(str(rpath(cfg["model"])))
    rows: dict[str, dict] = {a: {} for a in ARMS}
    for a in ARMS:
        for c in cfg["cams"]:
            sx = imgs[a][c][0].shape[1] / cv2.imread(str(paths[c][0])).shape[1]
            per: dict[int, tuple[int, int]] = {}
            for f, im in zip(fr, imgs[a][c]):
                p = net.predict(im, classes=[0], conf=cfg["conf"], imgsz=cfg["imgsz"], device="cpu",
                                verbose=False, max_det=1000)[0]
                dets = [{"bbox": [a0 / sx, b0 / sx, (x1 - a0) / sx, (y1 - b0) / sx], "score": float(sc)}
                        for (a0, b0, x1, y1), sc in zip(p.boxes.xyxy.numpy().tolist(), p.boxes.conf.numpy())]
                per[f] = _recall_h({f: cams[c]["gt"].get(f, [])}, {f: dets}, cfg["min_h"], cfg["conf"])
            for f, (k, n) in per.items():
                b = (c, block_of(f, cfg["block_frames"]))
                t = rows[a].get(b, (0, 0))
                rows[a][b] = (t[0] + k, t[1] + n)

    allm = st["matched"]
    hn_idx = np.linspace(0, len(allm) - 1, cfg["hn_frames"]).astype(int)
    hn_l = [allm[i]["luma_mean"] for i in hn_idx]
    res: dict[str, Any] = {
        "real": {"n_tune": len(tune), "n_hold": len(hold), "sigma_tune_median": round(real_sig_tune, 4),
                 "sigma_hold_median": round(real_sig, 4), "luma_hold_band": lb,
                 "luma_self_pass": int(sum(lb["p10"] <= x <= lb["p90"] for x in real_luma))},
        "fit": {**fit, "grid": cfg["s_grid"], "sigma_out": [round(v, 4) for v in grid_sig]},
        "median": med, "n_frames": len(fr) * len(cfg["cams"]),
        "noise": {"ratio_shipped_over_real": round(med["shipped"]["noise_sigma"] / real_sig, 3),
                  "ratio_raw_over_real": round(med["raw"]["noise_sigma"] / real_sig, 3),
                  "ratio_matched_over_real": round(med["matched"]["noise_sigma"] / real_sig, 3)},
        "luma": {a: luma_gap(med["raw"]["luma_mean"], med[a]["luma_mean"], lb["median"],
                             arm_profile(1.0, cfg["profile"]).ae_target) for a in ("shipped", "matched")},
        "hard_negative": {"n_in_band": int(sum(lb["p10"] <= x <= lb["p90"] for x in hn_l)),
                          "n": len(hn_l), "luma": [round(x, 2) for x in hn_l]},
        "recall": block_boot(rows, cfg["n_boot"], cfg["seed"]),
        "per_block": {a: {f"{c}/{b}": v for (c, b), v in rows[a].items()} for a in ARMS},
    }
    res["decision"] = decide(res, cfg["decision"])
    write_json(out / "summary.json", res)
    figure(res, rpath(cfg["figure"]))
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    m, r = res["median"], res["recall"]
    L = ["| arm | σ (median) | luma (median) | recall [95 % CI] |", "|---|---|---|---|",
         (f"| LLVIP vis hold-out (measure-only) | {res['real']['sigma_hold_median']} | "
          f"{res['real']['luma_hold_band']['median']:.1f} | - |")]
    L += [f"| {a} | {m[a]['noise_sigma']} | {m[a]['luma_mean']:.1f} | {r[a][0]} [{r[a][1]}, {r[a][2]}] |"
          for a in ARMS]
    return "\n".join(L) + f"\n\nDecision: {res['decision']}\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    lab = ["LLVIP\n(hold-out)", "raw", "shipped", "matched"]
    col = ["#555555", "#4a7bd0", "#d0694a", "#3aa06b"]
    sig = [res["real"]["sigma_hold_median"]] + [res["median"][a]["noise_sigma"] for a in ARMS]
    lum = [res["real"]["luma_hold_band"]["median"]] + [res["median"][a]["luma_mean"] for a in ARMS]
    ax[0].bar(lab, sig, color=col)
    ax[0].set_title("noise σ (MAD-of-Laplacian, 720p luma)")
    ax[1].bar(lab, lum, color=col)
    b = res["real"]["luma_hold_band"]
    ax[1].axhspan(b["p10"], b["p90"], color="#999999", alpha=.25, label="LLVIP p10–p90")
    ax[1].set_title("mean luma")
    ax[1].legend(fontsize=8)
    r = res["recall"]
    y = [r[a][0] for a in ARMS]
    e = [[r[a][0] - r[a][1] for a in ARMS], [r[a][2] - r[a][0] for a in ARMS]]
    ax[2].bar(list(ARMS), y, yerr=e, color=col[1:], capsize=4)
    ax[2].set_ylim(0, 1)
    ax[2].set_title(f"YOLOv8n recall, h≥20 px (n={r['n_gt']})")
    fig.suptitle("H32c night noise check — showcase_all_night vs LLVIP (measure-only)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
