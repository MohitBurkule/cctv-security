"""H3: far-field people. Recall by GT box height for YOLOv8n at imgsz 640,
imgsz 1280 and SAHI-style slicing (full frame + overlapping upscaled tiles,
merged with NMS), with per-frame latency and peak VRAM as the cost."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from .common import ap50_by_height, batch_cameras, recall_by_height, rpath, write_json


def tiles(w: int, h: int, tw: int, th: int, overlap: float) -> list[tuple[int, int, int, int]]:
    """Overlapping tile origins covering a w x h frame (last tile flush to the edge)."""
    def starts(n, t):
        if t >= n:
            return [0]
        step = max(1, int(t * (1 - overlap)))
        s = list(range(0, n - t, step))
        return s + [n - t]
    return [(x, y, tw, th) for y in starts(h, th) for x in starts(w, tw)]


def _boxes(p, dx=0.0, dy=0.0):
    xyxy = p.boxes.xyxy.cpu().numpy()
    sc = p.boxes.conf.cpu().numpy()
    return [[a + dx, b + dy, c + dx, d + dy, s] for (a, b, c, d), s in zip(xyxy, sc)]


def predict(model, img: np.ndarray, method: dict[str, Any], conf: float) -> list[dict]:
    import torch
    from torchvision.ops import nms

    kw = {"classes": [0], "conf": conf, "verbose": False, "half": True, "max_det": 300}
    out = []
    if method.get("full", True):
        out += _boxes(model.predict(img, imgsz=method["imgsz"], **kw)[0])
    if method.get("tile"):
        tw, th = method["tile"]
        ts = tiles(img.shape[1], img.shape[0], tw, th, method.get("overlap", 0.2))
        crops = [img[y:y + th, x:x + tw] for x, y, _, _ in ts]
        for (x, y, _, _), p in zip(ts, model.predict(crops, imgsz=method.get("tile_imgsz", 640), **kw)):
            out += _boxes(p, x, y)
        if out:
            a = torch.tensor(out, dtype=torch.float32)
            keep = nms(a[:, :4], a[:, 4], method.get("nms_iou", 0.5)).numpy()
            out = [out[i] for i in keep]
    return [{"bbox": [b[0], b[1], b[2] - b[0], b[3] - b[1]], "score": float(b[4])} for b in out]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import cv2
    import torch
    from ultralytics import YOLO

    model = YOLO(str(rpath(cfg["model"])))
    batch = rpath(cfg["batch_dir"])
    bands = [tuple(b) for b in cfg["bands"]]
    min_h = cfg["min_gt_height"]
    # collect frames once
    items = []   # (key, png, targets, ignore)
    for src in cfg["sources"]:
        for run_name in src["runs"]:
            for cam, c in batch_cameras(batch, run_name, src["source"]).items():
                if cfg.get("cameras") and cam not in cfg["cameras"]:
                    continue
                for f in sorted(c["frames"]):
                    if f < 1 or f % cfg["stride"]:
                        continue
                    rows = c["gt"].get(f, [])
                    tg = [r for r in rows if r["bbox"][3] >= min_h]
                    ig = [r for r in rows if r["bbox"][3] < min_h]
                    items.append((f"{run_name}/{src['source']}/{cam}", f, c["frames"][f], tg, ig))
    res: dict[str, Any] = {"n_frames": len(items), "n_gt": sum(len(i[3]) for i in items), "methods": {}}
    for meth in cfg["methods"]:
        preds: dict = {}
        torch.cuda.reset_peak_memory_stats()
        # warm-up so the first call's CUDA init is not billed to latency
        predict(model, cv2.imread(str(items[0][2])), meth, cfg["det_conf"])
        t_inf = 0.0
        for key, f, png, _, _ in items:
            img = cv2.imread(str(png))
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            preds[(key, f)] = predict(model, img, meth, cfg["det_conf"])
            torch.cuda.synchronize()
            t_inf += time.perf_counter() - t0
        G = {(k, f): tg for k, f, _, tg, _ in items}
        I = {(k, f): ig for k, f, _, _, ig in items}
        keys = list(G)
        r = {"method": meth,
             "ms_per_frame": round(1000 * t_inf / len(items), 1),
             "peak_vram_mib": round(torch.cuda.max_memory_allocated() / 2**20),
             "ap_by_height": ap50_by_height(keys, G, I, preds, bands),
             "per_source": {}}
        for thr in cfg["iou_thresholds"]:
            r[f"recall_iou{thr}"] = recall_by_height(G, preds, conf=cfg["op_conf"], thr=thr,
                                                     bands=bands, ignore_by_key=I)
        for src_key in sorted({k.rsplit("/", 1)[0] for k, _ in keys}):
            sub = {k: v for k, v in G.items() if k[0].startswith(src_key + "/")}
            r["per_source"][src_key] = recall_by_height(
                sub, {k: v for k, v in preds.items() if k in sub}, conf=cfg["op_conf"],
                thr=cfg["iou_thresholds"][0], bands=bands, ignore_by_key=I)
        res["methods"][meth["name"]] = r
        write_json(out / "partial.json", res)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    bands = [tuple(b) for b in cfg["bands"]]
    from .common import band_name
    bn = [band_name(*b) for b in bands]
    thr = cfg["iou_thresholds"][0]
    lines = [(f"{res['n_frames']} frames, {res['n_gt']} GT people >= {cfg['min_gt_height']} px; "
             f"recall at conf {cfg['op_conf']}, IoU {thr}"), "",
             "| method | " + " | ".join(f"R {b}px" for b in bn) + " | R all | P | ms/frame | VRAM MiB |",
             "|---|" + "---|" * (len(bn) + 4)]
    for name, r in res["methods"].items():
        rr = r[f"recall_iou{thr}"]
        cells = [f"{rr['recall_by_height'][b]['recall']:.3f}" if rr['recall_by_height'][b]['recall']
                 is not None else "-" for b in bn]
        lines.append(f"| {name} | " + " | ".join(cells) +
                     f" | {rr['recall']:.3f} | {rr['precision']:.3f} | {r['ms_per_frame']} | {r['peak_vram_mib']} |")
    return "\n".join(lines) + "\n"
