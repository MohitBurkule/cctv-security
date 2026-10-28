"""H32e: fit ONLY noise scale and CRF of cctv_night_lowlight to LLVIP night statistics, then measure recall.

Fit. Two knobs: s (H3g's noise std factor: iso_gain*s^2, read_noise*s, fpn*s) and the H.264 CRF. Every
other stage (exposure/luma, optics, ISP, colour) is the shipped value; OSD off in every arm. For each (s, crf)
on the declared grid the 60 detection frames are degraded (per camera as one sequence, apply_sequence) and the
median output noise sigma (Immerkaer, 720-line luma) and median blockiness (8x8 boundary/interior gradient,
native luma) are compared with the medians of the 15 LLVIP-visible TUNING frames:
    L(s, crf) = log2(sigma_out / sigma_tune)^2 + log2(blk_out / blk_tune)^2 ,  argmin over the grid.
The fitted pair is in-sample to the renders (and to the tuning frames) — labelled so.

Judge. Hold-out = the remaining LLVIP frames (10). Hard negative: of 13 fitted-output frames (evenly spaced
over the 60), count those with sigma AND blockiness both inside the hold-out p10-p90 bands; bar =
min(8, floor(13 * joint self-pass of the hold-out frames / 10)). Primary: YOLOv8n CPU recall, imgsz 1280,
conf 0.25, IoU 0.5, GT h >= 20 px and render-derived visibility > 0 (out/gt_vis_v2), paired block bootstrap
over 12 blocks of 30 render frames. Decision: R(fitted) >= 0.5 AND CI of R(fitted) - R(shipped) excludes 0
AND hard negative. Night penalty (reported, simulated render): R(raw) - R(fitted) with its paired CI.
LLVIP is non-commercial research data: measured only, never trained on or shipped.
Pre-registered in docs/research/32 §H32e.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import numpy as np

from . import night_noise_check as nn
from . import noise_recalibration as nr
from .common import batch_cameras, rpath, write_json

ARMS = ("raw", "shipped", "fitted")
KEYS = ("noise_sigma", "blockiness")


def fit_profile(s: float, crf: int, profile: str = "cctv_night_lowlight"):
    """Shipped profile, OSD off, noise level scaled by s (H3g) and CRF replaced; nothing else changes."""
    from survsim.sensors.degrade import PROFILES
    return dataclasses.replace(nr.scaled_profile(s, profile, PROFILES[profile].fps), crf=int(crf), osd=False)


def two_stats(img: np.ndarray) -> dict[str, float]:
    """The two fitted statistics exactly as survsim.realism.stats.frame_stats computes them."""
    import cv2

    from survsim.realism.stats import _resize, _to_bgr, blockiness, noise_sigma
    x = _to_bgr(img)
    blk = blockiness(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY))
    g = cv2.cvtColor(_resize(x), cv2.COLOR_BGR2GRAY).astype(np.float32)
    return {"noise_sigma": float(noise_sigma(g)), "blockiness": blk}


def loss(sig: float, blk: float, t_sig: float, t_blk: float) -> float:
    return float(np.log2(sig / t_sig) ** 2 + np.log2(blk / t_blk) ** 2)


def argmin_grid(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """cells: [{s, crf, loss, ...}] -> the minimum-loss cell (first on ties: grid order)."""
    return min(cells, key=lambda c: c["loss"])


def in_band(st: dict[str, float], bands: dict[str, dict[str, float]]) -> bool:
    return all(bands[k]["p10"] <= st[k] <= bands[k]["p90"] for k in KEYS)


def hn_bar(self_pass: int, n_hold: int, n_hn: int, bar_max: int) -> int:
    return int(min(bar_max, np.floor(n_hn * self_pass / max(n_hold, 1))))


def boot(rows: dict[str, dict], n_boot: int, seed: int) -> dict[str, Any]:
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
    out["delta_fitted_shipped"] = ci(R["fitted"][0] - R["shipped"][0], R["fitted"][1] - R["shipped"][1])
    out["night_penalty_raw_minus_fitted"] = ci(R["raw"][0] - R["fitted"][0], R["raw"][1] - R["fitted"][1])
    out["n_gt"], out["n_blocks"] = int(n.sum()), len(keys)
    return out


def decide(res: dict[str, Any], D: dict[str, Any]) -> dict[str, Any]:
    r = res["recall"]
    d = r["delta_fitted_shipped"]
    hn = res["hard_negative"]
    rec_ok = bool(r["fitted"][0] >= D["recall_min"] and d[1] > 0)
    hn_ok = bool(hn["n_in_band"] >= hn["bar"])
    return {"fitted_recall": r["fitted"], "delta_fitted_shipped": d, "recall_ok": rec_ok,
            "HN_in_band": hn["n_in_band"], "HN_bar": hn["bar"], "HN_ok": hn_ok,
            "decision_met": bool(rec_ok and hn_ok)}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    from survsim.realism.stats import band, list_images

    from .night import _recall_h
    real = sorted(list_images(rpath(cfg["real_root"])))
    tune, hold = real[:cfg["tune_n"]], real[cfg["tune_n"]:]
    st_t = [two_stats(cv2.imread(str(p))) for p in tune]
    st_h = [two_stats(cv2.imread(str(p))) for p in hold]
    tb = {k: band([x[k] for x in st_t]) for k in KEYS}
    hb = {k: band([x[k] for x in st_h]) for k in KEYS}
    self_pass = int(sum(in_band(x, hb) for x in st_h))
    bar = hn_bar(self_pass, len(hold), cfg["hn_frames"], cfg["decision"]["hn_bar_max"])

    cams = batch_cameras(rpath(cfg["batch_dir"]), cfg["run"], "raw", min_vis=cfg["min_vis"])
    fr = nn.frames_for(cfg)
    paths = {c: [cams[c]["frames"][f] for f in fr] for c in cfg["cams"]}
    seeds = {c: i for i, c in enumerate(cfg["cams"])}

    cells = []
    for s in cfg["s_grid"]:
        for crf in cfg["crf_grid"]:
            p = fit_profile(s, crf, cfg["profile"])
            st = [two_stats(im) for c in cfg["cams"] for im in nn._degrade(paths[c], p, seeds[c])]
            ms, mb = (float(np.median([x[k] for x in st])) for k in KEYS)
            cells.append({"s": s, "crf": crf, "sigma": round(ms, 4), "blk": round(mb, 4),
                          "loss": round(loss(ms, mb, tb["noise_sigma"]["median"], tb["blockiness"]["median"]), 5),
                          "tune_in_band": int(sum(in_band(x, tb) for x in st))})
            print("cell", cells[-1], flush=True)
    best = argmin_grid(cells)
    from survsim.sensors.degrade import PROFILES
    prof = {"shipped": fit_profile(1.0, PROFILES[cfg["profile"]].crf, cfg["profile"]),
            "fitted": fit_profile(best["s"], best["crf"], cfg["profile"])}

    imgs: dict[str, dict[str, list[np.ndarray]]] = {}
    for a in ARMS:
        imgs[a] = {c: ([cv2.imread(str(q)) for q in paths[c]] if a == "raw"
                       else nn._degrade(paths[c], prof[a], seeds[c])) for c in cfg["cams"]}
        for c in cfg["cams"]:
            d = out / "frames" / a / c
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{fr[len(fr) // 2]:04d}.png"), imgs[a][c][len(fr) // 2])
    st = {a: [two_stats(im) for c in cfg["cams"] for im in imgs[a][c]] for a in ARMS}
    med = {a: {k: round(float(np.median([x[k] for x in st[a]])), 4) for k in KEYS} for a in ARMS}

    net = YOLO(str(rpath(cfg["model"])))
    rows: dict[str, dict] = {a: {} for a in ARMS}
    for a in ARMS:
        for c in cfg["cams"]:
            sx = imgs[a][c][0].shape[1] / cv2.imread(str(paths[c][0])).shape[1]
            for f, im in zip(fr, imgs[a][c]):
                p = net.predict(im, classes=[0], conf=cfg["conf"], imgsz=cfg["imgsz"], device="cpu",
                                verbose=False, max_det=1000)[0]
                dets = [{"bbox": [a0 / sx, b0 / sx, (x1 - a0) / sx, (y1 - b0) / sx], "score": float(sc)}
                        for (a0, b0, x1, y1), sc in zip(p.boxes.xyxy.numpy().tolist(), p.boxes.conf.numpy())]
                k, n = _recall_h({f: cams[c]["gt"].get(f, [])}, {f: dets}, cfg["min_h"], cfg["conf"])
                b = (c, nn.block_of(f, cfg["block_frames"]))
                t = rows[a].get(b, (0, 0))
                rows[a][b] = (t[0] + k, t[1] + n)

    hn_idx = np.linspace(0, len(st["fitted"]) - 1, cfg["hn_frames"]).astype(int)
    hn_st = [st["fitted"][i] for i in hn_idx]
    res: dict[str, Any] = {
        "real": {"n_tune": len(tune), "n_hold": len(hold), "tune_band": tb, "hold_band": hb,
                 "hold_self_pass_joint": self_pass},
        "fit": {"best": best, "grid": cells, "s_grid": cfg["s_grid"], "crf_grid": cfg["crf_grid"],
                "label": "in-sample: fitted on the 60 detection frames vs the 15 LLVIP tuning frames"},
        "median": med, "n_frames": len(fr) * len(cfg["cams"]),
        "hard_negative": {"n_in_band": int(sum(in_band(x, hb) for x in hn_st)), "n": len(hn_st), "bar": bar,
                          "per_stat": {k: int(sum(hb[k]["p10"] <= x[k] <= hb[k]["p90"] for x in hn_st)) for k in KEYS},
                          "shipped_n_in_band": int(sum(in_band(st["shipped"][i], hb) for i in hn_idx))},
        "recall": boot(rows, cfg["n_boot"], cfg["seed"]),
        "per_block": {a: {f"{c}/{b}": v for (c, b), v in rows[a].items()} for a in ARMS},
    }
    res["decision"] = decide(res, cfg["decision"])
    write_json(out / "summary.json", res)
    figure(res, rpath(cfg["figure"]))
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    m, r, b = res["median"], res["recall"], res["fit"]["best"]
    L = [f"fitted s {b['s']}, crf {b['crf']} (loss {b['loss']}); n GT {r['n_gt']}, {r['n_blocks']} blocks", "",
         "| arm | σ | blockiness | recall [95 % CI] |", "|---|---|---|---|"]
    L += [f"| {a} | {m[a]['noise_sigma']} | {m[a]['blockiness']} | {r[a]} |" for a in ARMS]
    L += ["", (f"Δ fitted−shipped {r['delta_fitted_shipped']}; night penalty raw−fitted "
               f"{r['night_penalty_raw_minus_fitted']}"), f"HN {res['hard_negative']}", f"Decision: {res['decision']}"]
    return "\n".join(L) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    g = res["fit"]
    S, C = g["s_grid"], g["crf_grid"]
    Lm = np.array([[next(c["loss"] for c in g["grid"] if c["s"] == s and c["crf"] == q) for q in C] for s in S])
    im = ax[0].imshow(np.log10(Lm + 1e-4), origin="lower", aspect="auto", cmap="viridis")
    ax[0].set_xticks(range(len(C)), C)
    ax[0].set_yticks(range(len(S)), S)
    ax[0].set_xlabel("CRF")
    ax[0].set_ylabel("noise scale s")
    ax[0].plot(C.index(g["best"]["crf"]), S.index(g["best"]["s"]), "r*", ms=14)
    ax[0].set_title("fit loss log10 (vs LLVIP tuning-15)")
    fig.colorbar(im, ax=ax[0])
    hb = res["real"]["hold_band"]
    col = {"raw": "#4a7bd0", "shipped": "#d0694a", "fitted": "#3aa06b"}
    ax[1].add_patch(plt.Rectangle((hb["noise_sigma"]["p10"], hb["blockiness"]["p10"]),
                                  hb["noise_sigma"]["p90"] - hb["noise_sigma"]["p10"],
                                  hb["blockiness"]["p90"] - hb["blockiness"]["p10"], color="#999", alpha=.3,
                                  label="LLVIP hold-out p10–p90"))
    for a in ARMS:
        ax[1].plot(res["median"][a]["noise_sigma"], res["median"][a]["blockiness"], "o", color=col[a], ms=9, label=a)
    ax[1].set_xscale("log")
    ax[1].set_xlabel("noise σ (median)")
    ax[1].set_ylabel("blockiness (median)")
    ax[1].legend(fontsize=8)
    ax[1].set_title(f"HN: fitted {res['hard_negative']['n_in_band']}/13 in band (bar {res['hard_negative']['bar']})")
    r = res["recall"]
    y = [r[a][0] for a in ARMS]
    e = [[r[a][0] - r[a][1] for a in ARMS], [r[a][2] - r[a][0] for a in ARMS]]
    ax[2].bar(list(ARMS), y, yerr=e, color=[col[a] for a in ARMS], capsize=4)
    ax[2].axhline(0.5, ls=":", color="grey")
    ax[2].set_ylim(0, 1)
    ax[2].set_title(f"YOLOv8n recall ≥ 20 px (n={r['n_gt']}, render-vis GT)")
    fig.suptitle("H32e cctv_night_lowlight noise+CRF fit (LLVIP measure-only; simulated render)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
