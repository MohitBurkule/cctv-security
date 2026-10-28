"""H32a/H32b: are the night profiles in band against real LLVIP night frames,
and what zero-shot person recall do they give on batch_v8 night renders?

H32a scores the 13 docs/15 image stats of each profile's output (30 frames of
one night camera) against LLVIP visible and thermal bands. The first
``tune_n`` LLVIP frames (sorted) were the only ones looked at while tuning, and
the band that counts is the one from the remaining hold-out frames.
LLVIP is non-commercial research, so it is used for measurement only and
nothing is trained on it.

H32b runs zero-shot detectors over raw / cctv_night_ir / cctv_night_lowlight /
cctv_thermal versions of the same night frames. It reports pooled recall
(h >= min_h) with a camera-cluster bootstrap CI, and the paired pooled Δ vs raw.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import batch_cameras, rpath, wait_for_gpu, write_json
from .night import _recall_h

STATS = ("noise_sigma", "lap_var_log10", "mtf_ratio", "edge_width", "luma_mean", "rms_contrast",
         "dynamic_range", "luma_skew", "hist_entropy", "chroma_mean", "cast_a", "cast_b", "blockiness")


def in_band(real: dict[str, dict], synth: dict[str, float]) -> dict[str, bool]:
    """Per stat: synthetic median inside the real p10..p90 (inclusive)."""
    return {k: bool(real[k]["p10"] <= synth[k] <= real[k]["p90"]) for k in STATS}


def split_real(paths: list[Path], tune_n: int) -> tuple[list[Path], list[Path]]:
    ps = sorted(paths)
    return ps[:tune_n], ps[tune_n:]


def _bands(paths) -> dict[str, dict]:
    import cv2

    from survsim.realism.stats import band, frame_stats
    rows = [frame_stats(cv2.imread(str(p))).as_dict() for p in paths]
    return {k: band(r[k] for r in rows) for k in STATS}


def _masks_for(frames: dict[int, Path], run_dir: Path, cam: str) -> dict[int, Path]:
    return {f: run_dir / "mask" / cam / p.name for f, p in frames.items()}


def degrade_cam(frames: list[Path], masks: list[Path], profile: str, seed: int) -> list[np.ndarray]:
    import cv2

    from survsim.sensors.degrade import apply_sequence
    imgs = [cv2.imread(str(p)) for p in frames]
    ms = [cv2.imread(str(m), cv2.IMREAD_UNCHANGED) if m.is_file() else None for m in masks]
    return list(apply_sequence(imgs, profile, sequence_seed=seed, masks=ms))


def realism(cfg, out: Path) -> dict[str, Any]:
    from survsim.realism.stats import frame_stats, list_images
    rs = cfg["realism"]
    root = rpath(rs["real_root"])
    res: dict[str, Any] = {"real": {}, "synthetic": {}}
    bands = {}
    for mod, sub in rs["modalities"].items():
        tune, hold = split_real(list_images(root / sub), rs["tune_n"])
        bands[mod] = {"tune": _bands(tune), "hold": _bands(hold)}
        res["real"][mod] = {"n_tune": len(tune), "n_hold": len(hold), **bands[mod]}
    run_dir = rpath(cfg["batch_dir"]) / rs["run"]
    allf = sorted((run_dir / "render" / rs["cam"]).glob("*.png"))
    idx = np.linspace(0, len(allf) - 1, rs["n"]).astype(int)
    frames = [allf[i] for i in idx]
    masks = [run_dir / "mask" / rs["cam"] / p.name for p in frames]
    for prof in ["raw", *cfg["profiles"]]:
        import cv2
        imgs = ([cv2.imread(str(p)) for p in frames] if prof == "raw"
                else degrade_cam(frames, masks, prof, cfg["seed"]))
        if prof != "raw":
            d = out / "realism_frames" / prof
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / frames[len(frames) // 2].name), imgs[len(imgs) // 2])
        rows = [frame_stats(im).as_dict() for im in imgs]
        med = {k: float(np.median([r[k] for r in rows])) for k in STATS}
        rec: dict[str, Any] = {"median": med}
        for mod in bands:
            for split in ("tune", "hold"):
                ib = in_band(bands[mod][split], med)
                rec[f"{mod}_{split}"] = {"count": sum(ib.values()), "in_band": ib}
        res["synthetic"][prof] = rec
    tg = cfg["targets"]
    res["verdict"] = {p: {"modality": m, "target": t, "hold": res["synthetic"][p][f"{m}_hold"]["count"],
                          "tune": res["synthetic"][p][f"{m}_tune"]["count"],
                          "met": res["synthetic"][p][f"{m}_hold"]["count"] >= t,
                          "overfit_flag": res["synthetic"][p][f"{m}_tune"]["count"]
                          - res["synthetic"][p][f"{m}_hold"]["count"] > 2}
                      for p, (m, t) in ((p, tuple(v)) for p, v in tg.items())}
    return res


def _detect(model: str, paths: dict[int, str], cache: Path, imgsz: int, conf: float, device) -> dict:
    if cache.is_file():
        return {int(k): v for k, v in json.loads(cache.read_text()).items()}
    from ultralytics import YOLO
    net = YOLO(str(rpath(model)))
    out: dict[int, list] = {}
    fr = sorted(paths)
    for i in range(0, len(fr), 4):
        ch = fr[i:i + 4]
        for f, p in zip(ch, net.predict([paths[f] for f in ch], classes=[0], conf=conf, imgsz=imgsz,
                                        verbose=False, half=device != "cpu", device=device, max_det=1000)):
            out[f] = [{"bbox": [float(a), float(b), float(x - a), float(y - b)], "score": float(s)}
                      for (a, b, x, y), s in zip(p.boxes.xyxy.cpu().numpy(), p.boxes.conf.cpu().numpy())]
    write_json(cache, out)
    return out


def cluster_boot(per_cam: dict[str, dict[str, tuple[int, int]]], arms: list[str], base: str,
                 n: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Pooled recall per arm and pooled Δ vs ``base``, 95 % CI by resampling cameras (paired)."""
    cams = [c for c in per_cam if per_cam[c][base][1] > 0]
    k = np.array([[per_cam[c][a][0] for a in arms] for c in cams], float)
    m = np.array([[per_cam[c][a][1] for a in arms] for c in cams], float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(cams), (n, len(cams)))
    rec = k[idx].sum(1) / np.maximum(m[idx].sum(1), 1)         # (n, arms)
    point = k.sum(0) / np.maximum(m.sum(0), 1)
    bi = arms.index(base)
    out: dict[str, Any] = {"n_cameras": len(cams)}
    for j, a in enumerate(arms):
        q = np.quantile(rec[:, j], [.025, .975])
        d = rec[:, j] - rec[:, bi]
        qd = np.quantile(d, [.025, .975])
        out[a] = {"recall": round(float(point[j]), 4), "lo": round(float(q[0]), 4), "hi": round(float(q[1]), 4),
                  "tp": int(k[:, j].sum()), "n": int(m[:, j].sum()),
                  f"delta_vs_{base}": {"d": round(float(point[j] - point[bi]), 4),
                                       "lo": round(float(qd[0]), 4), "hi": round(float(qd[1]), 4)}}
    return out


def recall(cfg, out: Path) -> dict[str, Any]:
    import cv2
    gpu = wait_for_gpu(cfg["min_free_mib"], poll_s=30, max_wait_s=cfg.get("gpu_wait_s", 300))
    device = 0 if gpu.get("free_mib", 0) >= cfg["min_free_mib"] else "cpu"
    batch = rpath(cfg["batch_dir"])
    arms = ["raw", *cfg["profiles"]]
    fr_all = list(range(cfg["frame_start"], cfg["max_frame"] + 1, cfg["stride"]))
    per_model: dict[str, Any] = {}
    n_frames = 0
    for model in cfg["models"]:
        mname = Path(model).stem
        per_cam: dict[str, dict[str, tuple[int, int]]] = {}
        for run in cfg["night_runs"]:
            for cam, c in batch_cameras(batch, run, "raw").items():
                fr = [f for f in fr_all if f in c["frames"]]
                gt = {f: c["gt"].get(f, []) for f in fr}
                key = f"{run}/{cam}"
                if mname == Path(cfg["models"][0]).stem:
                    n_frames += len(fr)
                row = {}
                for arm in arms:
                    if arm == "raw":
                        paths = {f: str(c["frames"][f]) for f in fr}
                    else:
                        d = out / "frames" / arm / f"{run}__{cam}"
                        paths = {f: str(d / f"{f:04d}.png") for f in fr}
                        if not all(Path(p).is_file() for p in paths.values()):
                            d.mkdir(parents=True, exist_ok=True)
                            ms = _masks_for({f: c["frames"][f] for f in fr}, batch / run, cam)
                            imgs = degrade_cam([c["frames"][f] for f in fr], [ms[f] for f in fr], arm, cfg["seed"])
                            for f, im in zip(fr, imgs):
                                cv2.imwrite(paths[f], im)
                    dets = _detect(model, paths, out / "dets" / mname / arm / f"{run}__{cam}.json",
                                   cfg["imgsz"], cfg["det_conf"], device)
                    if arm != "raw":   # profiles output 1280x720; map back to render pixels
                        s = cv2.imread(paths[fr[0]]).shape[1] / cv2.imread(str(c["frames"][fr[0]])).shape[1]
                        dets = {f: [{**d, "bbox": [v / s for v in d["bbox"]]} for d in v] for f, v in dets.items()}
                    row[arm] = _recall_h(gt, dets, cfg["min_h"], cfg["op_conf"])
                per_cam[key] = row
        per_model[mname] = {"per_camera": {k: {a: {"tp": v[a][0], "n": v[a][1]} for a in arms}
                                           for k, v in per_cam.items()},
                            "pooled": cluster_boot(per_cam, arms, "raw", cfg["n_boot"], cfg["seed"])}
    return {"device": str(device), "gpu": gpu, "frames_per_arm": n_frames, "models": per_model}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    res = {"A": realism(cfg, out)}
    write_json(out / "partial_A.json", res["A"])
    res["B"] = recall(cfg, out)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    A = res["A"]
    L = ["| profile | vis tune | vis hold-out | IR tune | IR hold-out |", "|---|---|---|---|---|"]
    for p, r in A["synthetic"].items():
        L.append(f"| {p} | {r['vis_tune']['count']}/13 | {r['vis_hold']['count']}/13 | "
                 f"{r['ir_tune']['count']}/13 | {r['ir_hold']['count']}/13 |")
    L += ["", "| model | arm | recall [95% CI] | Δ vs raw [95% CI] |", "|---|---|---|---|"]
    for m, v in res["B"]["models"].items():
        for a, r in v["pooled"].items():
            if a == "n_cameras":
                continue
            d = r["delta_vs_raw"]
            L.append(f"| {m} | {a} | {r['recall']:.3f} [{r['lo']:.3f}, {r['hi']:.3f}] | "
                     f"{d['d']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}] |")
    return "\n".join(L) + "\n"
