"""H11: zero-shot detector recall by box height, day vs night vs night+cctv_night_ir
on batch_v7 (A), and whether fine-tuning on night-IR-degraded synthetic helps a
real dark sequence, MOT20-05 (B; colour night street, not IR)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import (
    batch_cameras,
    export_item,
    gpu_meter,
    match_frame,
    recall_by_height,
    rpath,
    wait_for_gpu,
    write_data_yaml,
    write_json,
)
from .tracking import boot_ci, boot_p_two_sided, detect_paths


def _frames(cfg):
    return list(range(cfg["frame_start"], cfg["max_frame"] + 1, cfg["stride"]))


def build_ir(cfg, out: Path) -> dict[str, dict[int, str]]:
    """Degrade night runs' sub-sampled frames with cctv_night_ir, per camera sequence."""
    import cv2

    from survsim.sensors.degrade import apply_sequence
    res = {}
    for run in cfg["night_runs"]:
        for cam, c in batch_cameras(rpath(cfg["batch_dir"]), run, "raw").items():
            d = out / "ir" / f"{run}__{cam}"
            fr = [f for f in _frames(cfg) if f in c["frames"]]
            if not (d.is_dir() and len(list(d.glob("*.png"))) == len(fr)):
                d.mkdir(parents=True, exist_ok=True)
                imgs = [cv2.imread(str(c["frames"][f])) for f in fr]
                for f, im in zip(fr, apply_sequence(imgs, cfg["ir_profile"], sequence_seed=cfg["seed"])):
                    cv2.imwrite(str(d / f"{f:04d}.png"), im)
            res[f"{run}/{cam}"] = {f: str(d / f"{f:04d}.png") for f in fr}
    return res


def _ir_scale(png, cfg) -> float:
    import cv2
    return cfg["ir_width"] / cv2.imread(str(png)).shape[1]


def _recall_h(gt_rows, dets, min_h, conf, thr=0.5):
    k = n = 0
    for f, rows in gt_rows.items():
        g = np.array([r["bbox"] for r in rows], float).reshape(-1, 4)
        p = [d for d in dets.get(f, []) if d["score"] >= conf]
        pb = np.array([d["bbox"] for d in p], float).reshape(-1, 4)
        gm, _ = match_frame(g, pb, np.array([d["score"] for d in p]), thr)
        sel = g[:, 3] >= min_h
        k += int(gm[sel].sum())
        n += int(sel.sum())
    return k, n


def part_a(cfg, out: Path) -> dict[str, Any]:
    batch = rpath(cfg["batch_dir"])
    ir = build_ir(cfg, out)
    per_cam: dict[str, Any] = {}
    pooled_in: dict[str, tuple[dict, dict]] = {"day": ({}, {}), "night": ({}, {}), "night_ir": ({}, {})}
    for run in cfg["day_runs"]:
        nrun = run.replace("_day", "_night")
        cams_d = batch_cameras(batch, run, "raw")
        cams_n = batch_cameras(batch, nrun, "raw")
        for cam in cams_d:
            if cam not in cams_n:
                continue
            fr = [f for f in _frames(cfg) if f in cams_d[cam]["frames"]]
            gt = {f: cams_d[cam]["gt"].get(f, []) for f in fr}
            gtn = {f: cams_n[cam]["gt"].get(f, []) for f in fr}
            dcache = rpath(cfg["det_cache"])
            dd = detect_paths(cfg["model"], {f: str(cams_d[cam]["frames"][f]) for f in fr},
                              dcache / f"{run}__{cam}.json", cfg["imgsz"], cfg["det_conf"])
            dn = detect_paths(cfg["model"], {f: str(cams_n[cam]["frames"][f]) for f in fr},
                              dcache / f"{nrun}__{cam}.json", cfg["imgsz"], cfg["det_conf"])
            di = detect_paths(cfg["model"], ir[f"{nrun}/{cam}"], out / "dets_ir" / f"{nrun}__{cam}.json",
                              cfg["imgsz"], cfg["det_conf"])
            # Renders are mixed 1280/1920 wide; the IR profile outputs 1280x720.
            # Map IR detections back to render pixels so every arm shares GT and bands.
            s = _ir_scale(cams_n[cam]["frames"][fr[0]], cfg)
            di = {f: [{**d, "bbox": [v / s for v in d["bbox"]]} for d in v] for f, v in di.items()}
            row = {"ir_scale": round(s, 4)}
            for arm, g, d in (("day", gt, dd), ("night", gtn, dn), ("night_ir", gtn, di)):
                k, n = _recall_h(g, d, cfg["min_h"], cfg["op_conf"])
                row[arm] = {"tp": k, "n": n, "recall": round(k / n, 4) if n else None}
                for f in fr:
                    pooled_in[arm][0][(run, cam, f)] = g[f]
                    pooled_in[arm][1][(run, cam, f)] = d.get(f, [])
            per_cam[f"{run.rsplit('_', 1)[0]}/{cam}"] = row
    pooled = {arm: recall_by_height(g, p, conf=cfg["op_conf"]) for arm, (g, p) in pooled_in.items()}
    valid = [v for v in per_cam.values() if v["day"]["n"] and v["night"]["n"]]
    contrasts = {}
    for a, b in (("night", "day"), ("night_ir", "night"), ("night_ir", "day")):
        d = [v[a]["recall"] - v[b]["recall"] for v in valid if v[a]["n"]]
        contrasts[f"{a}_minus_{b}"] = {**boot_ci(d), "p": round(boot_p_two_sided(d), 4)}
    return {"per_camera": per_cam, "pooled": pooled, "paired_by_camera_recall_h_ge_min": contrasts,
            "n_cameras_with_targets": len(valid)}


# ------------------------------------------------------------------ part B

def _mot05(cfg):
    from survsim.datasets.build import read_gt
    root = rpath(cfg["mot20_root"]) / "train" / cfg["real_seq"]
    tg, ig = read_gt(root / "gt" / "gt.txt")
    fr = list(range(1, cfg["real_frames"] + 1, cfg["real_stride"]))
    G, I = {}, {}
    for r in tg:
        if r["frame"] in fr:
            G.setdefault(r["frame"], []).append(r)
    for r in ig:
        if r["frame"] in fr:
            I.setdefault(r["frame"], []).append(r)
    return fr, {f: str(root / "img1" / f"{f:06d}.jpg") for f in fr}, G, I


def _frame_recs(fr, G, I, P, thr=0.5):
    from ..eval.detection import iou_matrix
    recs = {}
    for f in fr:
        g = np.array([r["bbox"] for r in G.get(f, [])], float).reshape(-1, 4)
        preds = sorted(P.get(f, []), key=lambda d: -d["score"])
        rr = []
        if preds:
            p = np.array([d["bbox"] for d in preds], float)
            iou = iou_matrix(p, g) if len(g) else np.zeros((len(p), 0))
            ig = I.get(f)
            iig = iou_matrix(p, np.array([r["bbox"] for r in ig], float)).max(1) if ig else np.zeros(len(p))
            used = np.zeros(len(g), bool)
            for i, d in enumerate(preds):
                m = 0
                cand = np.where(~used & (iou[i] >= thr))[0] if len(g) else []
                if len(cand):
                    used[cand[np.argmax(iou[i, cand])]] = True
                    m = 1
                elif iig[i] >= thr:
                    m = -1
                if m >= 0:
                    rr.append((d["score"], m))
        recs[f] = (np.array(rr, float).reshape(-1, 2), len(g))
    return recs


def _ap(recs, frames) -> float:
    arr = np.concatenate([recs[f][0] for f in frames])
    n = sum(recs[f][1] for f in frames)
    if n == 0:
        return 0.0
    arr = arr[np.argsort(-arr[:, 0], kind="stable")]
    tp = np.cumsum(arr[:, 1])
    fp = np.cumsum(1 - arr[:, 1])
    rec, prec = tp / n, tp / np.maximum(tp + fp, 1e-9)
    prec = np.maximum.accumulate(prec[::-1])[::-1] if len(prec) else prec
    idx = np.searchsorted(rec, np.linspace(0, 1, 101), side="left")
    return float(np.mean([prec[i] if i < len(prec) else 0.0 for i in idx]))


def _train(cfg, name, imgs: dict[str, tuple[str, list, int, int]], work: Path, rec) -> Path:
    from ultralytics import YOLO
    root = work / name / "yolo_data"
    keys = sorted(imgs)
    for k in keys:
        png, rows, w, h = imgs[k]
        export_item(root, "train", k, Path(png), rows, w, h)
    for k in keys[:: max(1, len(keys) // 20)]:
        png, rows, w, h = imgs[k]
        export_item(root, "val", k, Path(png), rows, w, h)
    write_data_yaml(root)
    t = cfg["train"]
    rec["train_images"] = len(keys)
    with gpu_meter(rec, "train_cost"):
        YOLO(str(rpath(cfg["model"]))).train(
            data=str(root / "data.yaml"), epochs=t["epochs"], imgsz=t["imgsz"], batch=t["batch"],
            seed=cfg["seed"], deterministic=True, workers=2, project=str((work / name).resolve()), name="train",
            exist_ok=True, plots=False, val=False, verbose=False, patience=0, amp=True)
    return work / name / "train" / "weights" / "last.pt"


def part_b(cfg, out: Path) -> dict[str, Any]:
    fr, paths, G, I = _mot05(cfg)
    ir = build_ir(cfg, out)
    batch = rpath(cfg["batch_dir"])
    sets: dict[str, dict] = {"ft_night_ir": {}, "ft_night_raw": {}}
    for run in cfg["night_runs"]:
        for cam, c in batch_cameras(batch, run, "raw").items():
            first = next(iter(ir[f"{run}/{cam}"].values()))
            s = _ir_scale(c["frames"][int(Path(first).stem)], cfg)
            W, H = round(1280 / s), round(720 / s)
            for f, png in ir[f"{run}/{cam}"].items():
                rows = c["gt"].get(f, [])
                sets["ft_night_ir"][f"{run}__{cam}__{f:04d}"] = (
                    png, [{**r, "bbox": [v * s for v in r["bbox"]]} for r in rows], 1280, 720)
                sets["ft_night_raw"][f"{run}__{cam}__{f:04d}"] = (str(c["frames"][f]), rows, W, H)
    arms: dict[str, Any] = {"zero_shot": {"weights": cfg["model"]}}
    for name, imgs in sets.items():
        rec: dict[str, Any] = {"gpu_wait": wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=900)}
        w = out / "work" / name / "train" / "weights" / "last.pt"
        if not w.is_file():
            w = _train(cfg, name, imgs, out / "work", rec)
        arms[name] = {"weights": str(w), **rec}
    recs = {}
    for name, a in arms.items():
        a["eval"] = {}
        for sz in cfg["eval_imgsz"]:
            P = detect_paths(a["weights"], paths, out / "dets_mot05" / f"{name}_{sz}.json", sz, cfg["ap_conf"])
            recs[(name, sz)] = _frame_recs(fr, G, I, P)
            a["eval"][str(sz)] = {"AP50": round(_ap(recs[(name, sz)], fr), 4),
                                  "recall_at_op": recall_by_height(G, P, conf=cfg["op_conf"], ignore_by_key=I)}
    rng = np.random.default_rng(cfg["seed"])
    boots = [rng.choice(fr, len(fr)) for _ in range(cfg["n_boot"])]
    contrasts = {}
    for sz in cfg["eval_imgsz"]:
        for a, b in (("ft_night_ir", "zero_shot"), ("ft_night_raw", "zero_shot"), ("ft_night_ir", "ft_night_raw")):
            d = np.array([_ap(recs[(a, sz)], bb) - _ap(recs[(b, sz)], bb) for bb in boots])
            contrasts[f"{a}_minus_{b}@{sz}"] = {
                "dAP50": round(_ap(recs[(a, sz)], fr) - _ap(recs[(b, sz)], fr), 4),
                "lo": round(float(np.quantile(d, .025)), 4), "hi": round(float(np.quantile(d, .975)), 4)}
    n_gt = sum(len(v) for v in G.values())
    return {"real_seq": cfg["real_seq"], "frames": len(fr), "n_gt": n_gt, "arms": arms,
            "contrasts_boot_over_frames": contrasts}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    res: dict[str, Any] = {"gpu_wait": wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=900)}
    res["A"] = part_a(cfg, out)
    write_json(out / "partial_A.json", res["A"])
    res["B"] = part_b(cfg, out)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    A = res["A"]
    L = ["| arm | recall | precision | " + " | ".join(f"R {b}" for b in A["pooled"]["day"]["recall_by_height"]) + " |",
         "|---|---|---|" + "---|" * len(A["pooled"]["day"]["recall_by_height"])]
    for arm, r in A["pooled"].items():
        L.append(f"| {arm} | {r['recall']:.3f} | {r['precision']:.3f} | " + " | ".join(
            (f"{v['recall']:.3f} (n={v['n']})" if v["recall"] is not None else "–")
            for v in r["recall_by_height"].values()) + " |")
    L += ["", "```", json.dumps(A["paired_by_camera_recall_h_ge_min"], indent=1), "```", "",
          "| arm | imgsz | AP50 MOT20-05 | recall@op |", "|---|---|---|---|"]
    for n, a in res["B"]["arms"].items():
        for sz, e in a["eval"].items():
            L.append(f"| {n} | {sz} | {e['AP50']:.4f} | {e['recall_at_op']['recall']:.4f} |")
    L += ["", "```", json.dumps(res["B"]["contrasts_boot_over_frames"], indent=1), "```"]
    return "\n".join(L) + "\n"
