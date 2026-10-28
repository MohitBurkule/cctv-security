"""Detection scoring, stratified.

Pure NumPy so it runs without torch or pycocotools.

The headline metric is AP, computed the standard COCO way (greedy IoU matching,
101-point interpolated precision-recall). What differs is that everything can be
recomputed *per difficulty stratum*, because a single averaged AP over
surveillance footage hides the only thing that matters: whether the system works
on the small, occluded, badly-lit people who make up most of a real scene.

Also reported is **FPPI** — false positives per image — and its translation into
false alarms per camera-hour, which is the number a control room actually cares
about (`fppi * fps * 3600`). A detector at 0.1 FPPI on 25 fps footage generates
9,000 false alarms per camera-hour, and that arithmetic is what separates a good
benchmark score from an unusable product (R01, R03).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


def iou_matrix(pred: np.ndarray, gt: np.ndarray) -> np.ndarray:
    """IoU between Nx4 and Mx4 boxes in xywh."""
    if len(pred) == 0 or len(gt) == 0:
        return np.zeros((len(pred), len(gt)))
    px0, py0 = pred[:, 0][:, None], pred[:, 1][:, None]
    px1, py1 = px0 + pred[:, 2][:, None], py0 + pred[:, 3][:, None]
    gx0, gy0 = gt[:, 0][None, :], gt[:, 1][None, :]
    gx1, gy1 = gx0 + gt[:, 2][None, :], gy0 + gt[:, 3][None, :]

    iw = np.clip(np.minimum(px1, gx1) - np.maximum(px0, gx0), 0, None)
    ih = np.clip(np.minimum(py1, gy1) - np.maximum(py0, gy0), 0, None)
    inter = iw * ih
    union = (pred[:, 2] * pred[:, 3])[:, None] + (gt[:, 2] * gt[:, 3])[None, :] - inter
    return np.where(union > 0, inter / np.maximum(union, 1e-9), 0.0)


@dataclass
class DetectionResult:
    ap: float
    precision: float
    recall: float
    n_gt: int
    n_pred: int
    true_positives: int
    false_positives: int
    false_negatives: int
    n_images: int
    fps: float = 25.0
    per_stratum: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def fppi(self) -> float:
        return self.false_positives / self.n_images if self.n_images else float("inf")

    @property
    def false_alarms_per_camera_hour(self) -> float:
        """The operational translation of FPPI. Usually a sobering number."""
        return self.fppi * self.fps * 3600.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ap": round(self.ap, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "n_gt": self.n_gt, "n_pred": self.n_pred,
            "tp": self.true_positives, "fp": self.false_positives, "fn": self.false_negatives,
            "fppi": round(self.fppi, 4),
            "false_alarms_per_camera_hour": round(self.false_alarms_per_camera_hour, 1),
            "per_stratum": self.per_stratum,
        }


def _average_precision(scores: np.ndarray, matched: np.ndarray, n_gt: int) -> float:
    """101-point interpolated AP, as COCO defines it."""
    if n_gt == 0 or len(scores) == 0:
        return 0.0
    order = np.argsort(-scores)
    tp = np.cumsum(matched[order])
    fp = np.cumsum(1 - matched[order])
    recall = tp / n_gt
    precision = tp / np.maximum(tp + fp, 1e-9)
    # Make precision monotonically decreasing, then sample at fixed recalls.
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    return float(np.mean(np.interp(np.linspace(0, 1, 101), recall, precision, left=1.0, right=0.0)))


def evaluate(
    gt_by_image: dict[Any, Sequence[dict[str, Any]]],
    pred_by_image: dict[Any, Sequence[dict[str, Any]]],
    iou_threshold: float = 0.5,
    fps: float = 25.0,
    stratify: str | None = "height_bucket",
    ignore_unusable: bool = True,
) -> DetectionResult:
    """Score predictions against ground truth.

    `ignore_unusable` drops annotations below the detectable pixel height from the
    recall denominator instead of counting them as misses. Scoring a detector
    against people it physically cannot resolve measures the camera placement, not
    the detector — those cases belong in the rig report.
    """
    all_scores: list[float] = []
    all_matched: list[int] = []
    strata_records: dict[str, dict[str, list]] = {}
    n_gt = tp = fp = 0
    images = set(gt_by_image) | set(pred_by_image)

    for image in images:
        gts = list(gt_by_image.get(image, []))
        if ignore_unusable:
            gts = [g for g in gts
                   if g.get("difficulty", {}).get("height_bucket") != "unusable"]
        preds = sorted(pred_by_image.get(image, []), key=lambda p: -float(p.get("score", 1.0)))

        gt_boxes = np.array([g["bbox"] for g in gts], dtype=float).reshape(-1, 4)
        pred_boxes = np.array([p["bbox"] for p in preds], dtype=float).reshape(-1, 4)
        ious = iou_matrix(pred_boxes, gt_boxes)

        claimed: set[int] = set()
        for pi, pred in enumerate(preds):
            score = float(pred.get("score", 1.0))
            best_j, best_iou = -1, iou_threshold
            for gj in range(len(gts)):
                if gj in claimed or ious[pi, gj] < best_iou:
                    continue
                best_iou, best_j = ious[pi, gj], gj
            hit = best_j >= 0
            if hit:
                claimed.add(best_j)
                tp += 1
            else:
                fp += 1
            all_scores.append(score)
            all_matched.append(int(hit))

            if stratify and hit:
                key = gts[best_j].get("difficulty", {}).get(stratify, "unknown")
                rec = strata_records.setdefault(key, {"scores": [], "matched": [], "n_gt": 0})
                rec["scores"].append(score)
                rec["matched"].append(1)

        for gj, gt in enumerate(gts):
            n_gt += 1
            if stratify:
                key = gt.get("difficulty", {}).get(stratify, "unknown")
                rec = strata_records.setdefault(key, {"scores": [], "matched": [], "n_gt": 0})
                rec["n_gt"] += 1
                if gj not in claimed:
                    rec["scores"].append(0.0)
                    rec["matched"].append(0)

    scores = np.array(all_scores, dtype=float)
    matched = np.array(all_matched, dtype=int)
    per_stratum = {
        key: {
            "n_gt": rec["n_gt"],
            "recall": round(sum(rec["matched"]) / rec["n_gt"], 4) if rec["n_gt"] else 0.0,
            "ap": round(_average_precision(np.array(rec["scores"]), np.array(rec["matched"]),
                                           rec["n_gt"]), 4),
        }
        for key, rec in sorted(strata_records.items())
    }

    return DetectionResult(
        ap=_average_precision(scores, matched, n_gt),
        precision=tp / max(tp + fp, 1),
        recall=tp / max(n_gt, 1),
        n_gt=n_gt, n_pred=len(scores),
        true_positives=tp, false_positives=fp, false_negatives=max(n_gt - tp, 0),
        n_images=max(len(images), 1), fps=fps, per_stratum=per_stratum,
    )


def group_by_image(annotations: Iterable[dict[str, Any]]) -> dict[Any, list[dict[str, Any]]]:
    out: dict[Any, list[dict[str, Any]]] = {}
    for ann in annotations:
        out.setdefault(ann["image_id"], []).append(ann)
    return out


def evaluate_coco(
    coco: dict[str, Any],
    predictions: Iterable[dict[str, Any]],
    iou_threshold: float = 0.5,
    fps: float = 25.0,
) -> DetectionResult:
    """Score predictions in COCO results format against an exported COCO set."""
    return evaluate(
        group_by_image(coco["annotations"]),
        group_by_image(predictions),
        iou_threshold=iou_threshold,
        fps=fps,
    )
