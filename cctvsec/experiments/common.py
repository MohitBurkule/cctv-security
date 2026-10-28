"""Shared plumbing for `survsim experiment`: batch_v6 discovery, GT pairing,
YOLO dataset export, height-banded detection scoring, GPU accounting.

Frame pairing (verified by `tools/check_render.py`, "gt_frame_coverage ... offset 0"):
render PNG index *i* is world tick *i*, which is MOT frame *i*. Frame 0 has no GT.
"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[2]
COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog",
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
    "teddy bear", "hair drier", "toothbrush"]


# Path variables usable in experiment configs, with their defaults (repo-relative).
# SURVSIM_MOT20_SUBSET: the docs/13 MOT20 subset dataset dir (manifest.json +
# baselines/results_all.json); build it with `survsim dataset` or copy it there.
PATH_VAR_DEFAULTS = {"SURVSIM_MOT20_SUBSET": "out/datasets/mot20_sub"}


def rpath(p: str | Path) -> Path:
    """Resolve a config path: ~ and $VARS expanded (PATH_VAR_DEFAULTS fill unset ones),
    relative paths are relative to the repo root."""
    s = str(p)
    for k, v in PATH_VAR_DEFAULTS.items():
        s = s.replace(f"${{{k}}}", os.environ.get(k, v)).replace(f"${k}", os.environ.get(k, v))
    p = Path(os.path.expanduser(os.path.expandvars(s)))
    return p if p.is_absolute() else REPO / p


def read_mot_rows(path: Path) -> dict[int, list[dict[str, Any]]]:
    """MOT frame -> target rows (conf==1, class==1), with id, xywh bbox, visibility."""
    from survsim.datasets.build import read_gt
    targets, _ = read_gt(path)
    out: dict[int, list] = {}
    for r in targets:
        out.setdefault(r["frame"], []).append(r)
    return out


def batch_cameras(batch: Path, run: str, source: str = "raw", gt_subdir: str | None = None,
                  min_vis: float | None = None) -> dict[str, dict[str, Any]]:
    """cam -> {frames: {mot_frame: png}, gt: {mot_frame: rows}} for one batch run.

    source = "raw" (render/<cam>/NNNN.png) or "degraded" (video/degraded/<cam>/NNNN.png).
    gt_subdir: read labels from gt/<gt_subdir>/mot_<cam>.txt (e.g. "amodal") instead of
    the visible (mask-derived) gt/mot_<cam>.txt. min_vis: drop rows whose MOT col 9
    (visibility) is below it -- the rows are removed, not turned into ignore regions.
    """
    rd = Path(batch) / run
    base = rd / "render" if source == "raw" else rd / "video" / "degraded"
    out = {}
    if not base.is_dir():
        return out
    for cam in sorted(p for p in base.iterdir() if p.is_dir()):
        gtp = rd / "gt" / (gt_subdir or "") / f"mot_{cam.name}.txt"
        if not gtp.is_file():
            continue
        frames = {int(p.stem): p for p in cam.glob("*.png") if p.stem.isdigit()}
        gt = read_mot_rows(gtp)
        if min_vis is not None:
            gt = {f: [r for r in rows if r["vis"] >= min_vis] for f, rows in gt.items()}
        out[cam.name] = {"frames": frames, "gt": gt}
    return out


# ------------------------------------------------------------------ YOLO export

def _label_lines(rows, w, h, min_h: float = 4.0) -> list[str]:
    lines = []
    for r in rows:
        x, y, bw, bh = r["bbox"]
        x0, y0 = max(x, 0.0), max(y, 0.0)
        x1, y1 = min(x + bw, w), min(y + bh, h)
        if y1 - y0 < min_h or x1 - x0 < 1:
            continue
        lines.append(f"0 {(x0 + x1) / 2 / w:.6f} {(y0 + y1) / 2 / h:.6f} "
                     f"{(x1 - x0) / w:.6f} {(y1 - y0) / h:.6f}")
    return lines


def export_item(root: Path, split: str, name: str, img: Path, rows, w: int, h: int) -> None:
    """Symlink an image into a YOLO tree and write its label file."""
    ip = root / "images" / split / f"{name}{img.suffix}"
    lp = root / "labels" / split / f"{name}.txt"
    ip.parent.mkdir(parents=True, exist_ok=True)
    lp.parent.mkdir(parents=True, exist_ok=True)
    if ip.is_symlink() or ip.exists():
        ip.unlink()
    ip.symlink_to(Path(img).resolve())
    lp.write_text("\n".join(_label_lines(rows, w, h)))


def write_data_yaml(root: Path) -> Path:
    import yaml
    p = root / "data.yaml"
    p.write_text(yaml.safe_dump({"path": str(root), "train": "images/train", "val": "images/val",
                                 "names": dict(enumerate(COCO_NAMES))}))
    return p


# ------------------------------------------------------------------ scoring

HEIGHT_BANDS = ((0, 20), (20, 40), (40, 80), (80, 160), (160, 1e9))


def band_name(lo, hi) -> str:
    return f"{int(lo)}-{int(hi)}" if hi < 1e8 else f"{int(lo)}+"


def match_frame(gt: np.ndarray, pred: np.ndarray, scores: np.ndarray, thr: float = 0.5):
    """Greedy score-ordered IoU matching. Returns (gt_matched bool[M], pred_matched bool[N])."""
    from ..eval.detection import iou_matrix
    gm = np.zeros(len(gt), bool)
    pm = np.zeros(len(pred), bool)
    if len(gt) == 0 or len(pred) == 0:
        return gm, pm
    iou = iou_matrix(pred, gt)
    for i in np.argsort(-scores):
        cand = np.where(~gm & (iou[i] >= thr))[0]
        if len(cand):
            j = cand[np.argmax(iou[i, cand])]
            gm[j] = True
            pm[i] = True
    return gm, pm


def recall_by_height(gt_by_key: dict, pred_by_key: dict, conf: float = 0.25, thr: float = 0.5,
                     bands=HEIGHT_BANDS, ignore_by_key: dict | None = None) -> dict[str, Any]:
    """Recall per GT height band and overall precision at one operating point.

    Predictions matching an ignore region (IoU>=0.5) are neither TP nor FP (MOTChallenge)."""
    from ..eval.detection import iou_matrix
    hit = {b: [0, 0] for b in bands}
    tp = fp = 0
    for k, rows in gt_by_key.items():
        g = np.array([r["bbox"] for r in rows], float).reshape(-1, 4)
        preds = [d for d in pred_by_key.get(k, []) if d["score"] >= conf]
        p = np.array([d["bbox"] for d in preds], float).reshape(-1, 4)
        s = np.array([d["score"] for d in preds], float)
        gm, pm = match_frame(g, p, s, thr)
        if ignore_by_key and ignore_by_key.get(k) and len(p):
            ig = np.array([r["bbox"] for r in ignore_by_key[k]], float)
            pm = pm | (iou_matrix(p, ig).max(axis=1) >= 0.5)
            fp += int((~pm).sum())
            tp += int(gm.sum())
        else:
            tp += int(gm.sum())
            fp += int((~pm).sum())
        for (lo, hi) in bands:
            sel = (g[:, 3] >= lo) & (g[:, 3] < hi)
            hit[(lo, hi)][0] += int(gm[sel].sum())
            hit[(lo, hi)][1] += int(sel.sum())
    # frames with predictions but no GT rows
    for k, preds in pred_by_key.items():
        if k not in gt_by_key:
            fp += sum(1 for d in preds if d["score"] >= conf)
    n_gt = sum(v[1] for v in hit.values())
    return {"conf": conf, "iou": thr, "recall": round(tp / max(1, n_gt), 4),
            "precision": round(tp / max(1, tp + fp), 4), "tp": tp, "fp": fp, "n_gt": n_gt,
            "recall_by_height": {band_name(*b): {"recall": (round(v[0] / v[1], 4) if v[1] else None),
                                                 "n": v[1]} for b, v in hit.items()}}


def ap50_by_height(keys, gt_by_key, ign_by_key, pred_by_key, bands=HEIGHT_BANDS,
                   thr: float = 0.5) -> dict[str, Any]:
    """AP50 per GT height band, COCO-style (101-point interpolation), in numpy.

    Every prediction is matched once, greedily in score order, against *all* GT
    of its frame (then against ignore regions). For band b: a prediction matched
    to an in-band GT is a TP; one matched to an out-of-band GT or an ignore
    region is disregarded; an unmatched one is an FP only if its own height lies
    in b (COCO's area-range convention). The "all" entry is checked against
    pycocotools in tests/test_experiments.py.
    """
    from ..eval.detection import iou_matrix
    recs = []   # (score, pred_h, matched_gt_h or -1 (FP) or -2 (ignored))
    gt_h = []
    for k in keys:
        rows = gt_by_key.get(k, [])
        g = np.array([r["bbox"] for r in rows], float).reshape(-1, 4)
        gt_h += list(g[:, 3])
        preds = sorted(pred_by_key.get(k, []), key=lambda d: -d["score"])
        if not preds:
            continue
        p = np.array([d["bbox"] for d in preds], float)
        iou = iou_matrix(p, g) if len(g) else np.zeros((len(p), 0))
        ig = ign_by_key.get(k) if ign_by_key else None
        iig = (iou_matrix(p, np.array([r["bbox"] for r in ig], float)).max(axis=1)
               if ig else np.zeros(len(p)))
        used = np.zeros(len(g), bool)
        for i, d in enumerate(preds):
            m = -1.0
            if len(g):
                cand = np.where(~used & (iou[i] >= thr))[0]
                if len(cand):
                    j = cand[np.argmax(iou[i, cand])]
                    used[j] = True
                    m = g[j, 3]
            if m < 0 and iig[i] >= thr:
                m = -2.0
            recs.append((d["score"], p[i, 3], m))
    gt_h = np.array(gt_h)
    arr = np.array(recs, float).reshape(-1, 3)
    arr = arr[np.argsort(-arr[:, 0], kind="stable")]
    out = {}
    for lo, hi in [(0, 1e12), *bands]:
        n = int(((gt_h >= lo) & (gt_h < hi)).sum())
        name = "all" if hi == 1e12 and lo == 0 else band_name(lo, hi)
        if n == 0:
            out[name] = {"n": 0}
            continue
        m = arr[:, 2]
        tp = (m >= lo) & (m < hi)
        fp = (m == -1) & (arr[:, 1] >= lo) & (arr[:, 1] < hi)
        keep = tp | fp
        ctp, cfp = np.cumsum(tp[keep]), np.cumsum(fp[keep])
        rec = ctp / n
        prec = ctp / np.maximum(ctp + cfp, 1e-9)
        prec = np.maximum.accumulate(prec[::-1])[::-1] if len(prec) else prec
        rs = np.linspace(0, 1, 101)
        idx = np.searchsorted(rec, rs, side="left")
        ap = float(np.mean([prec[i] if i < len(prec) else 0.0 for i in idx]))
        out[name] = {"AP50": round(ap, 4), "n": n}
    return out


# ------------------------------------------------------------------ accounting

@contextmanager
def gpu_meter(record: dict[str, Any], key: str):
    """Wall time and peak torch-allocated VRAM (MiB) of a block."""
    import torch
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    try:
        yield
    finally:
        record[key] = {"seconds": round(time.time() - t0, 1),
                       "peak_vram_mib": (round(torch.cuda.max_memory_allocated() / 2**20)
                                         if torch.cuda.is_available() else None)}


def wait_for_gpu(min_free_mib: int = 2560, poll_s: int = 60, max_wait_s: int = 600) -> dict[str, Any]:
    """Free cached VRAM, then wait (bounded) until the GPU has `min_free_mib` free.

    The GPU is shared with an Unreal editor that may be rendering; starting an
    arm into an almost-full card OOMs half-way through. Returns what was seen."""
    import torch
    if not torch.cuda.is_available():
        return {"gpu": None}
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    t0 = time.time()
    while True:
        free = torch.cuda.mem_get_info()[0] // 2**20
        if free >= min_free_mib or time.time() - t0 >= max_wait_s:
            return {"free_mib": int(free), "waited_s": round(time.time() - t0)}
        time.sleep(poll_s)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str))
