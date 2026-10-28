"""Box-tightness gate: do our GT boxes sit where a person detector sees the person?

The measurement is docs/research/32 §H6(c) (cctvsec.experiments.diagnose),
made a pass/fail check: sample frames, match every GT box (>= 40 px tall,
visibility >= 0.7) to its best zero-shot YOLOv8n box, and report the median
IoU and the median top-edge offset (prediction - GT, / GT height).

Thresholds: FAIL if median IoU < 0.75 or |top offset| > 3 % of box height.
Hand-labelled MOT20-02 scores 0.797 / +1.1 % on the same measure; the
projected-hull GT used before mask-derived boxes scored 0.696 / +7.2 %.
The detector is a reference, not truth: a set it cannot see (night, heavy
degradation) fails on misses, so run this on raw day renders.

    python -m cctvsec.checks.box_tightness out/batch_v7/smoke_mock_day_tightgt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from survsim.checks.core import FAIL, PASS, SKIP, Check, format_table

MIN_IOU = 0.75
MAX_TOP = 0.03


def measure(set_dir: Path, n_frames: int = 30, seed: int = 0, min_h: float = 40.0,
            min_vis: float = 0.7, conf: float = 0.1, model: str = "yolov8n.pt",
            device: str = "cpu", overlays: Path | None = None) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    from ..experiments.common import batch_cameras
    from ..experiments.diagnose import _draw, box_agreement, summarise

    set_dir = Path(set_dir)
    cams = batch_cameras(set_dir.parent, set_dir.name, "raw")
    pool = [(cam, f, c["frames"][f], c["gt"][f]) for cam, c in cams.items()
            for f in sorted(c["frames"]) if f >= 1 and c["gt"].get(f)]
    if not pool:
        return {"n_gt": 0}
    rng = np.random.default_rng(seed)
    pick = [pool[i] for i in sorted(rng.choice(len(pool), min(n_frames, len(pool)), replace=False))]
    net = YOLO(model)
    recs = []
    for k, (cam, f, png, rows) in enumerate(pick):
        img = cv2.imread(str(png))
        rows = [r for r in rows if r["bbox"][3] >= min_h and r.get("vis", 1) >= min_vis]
        g = np.array([r["bbox"] for r in rows], float).reshape(-1, 4)
        p = net.predict(img, imgsz=1280, classes=[0], conf=conf, verbose=False, device=device)[0]
        xyxy = p.boxes.xyxy.cpu().numpy()
        pred = np.c_[xyxy[:, :2], xyxy[:, 2:] - xyxy[:, :2]] if len(xyxy) else np.zeros((0, 4))
        recs += box_agreement(g, pred)
        if overlays is not None:
            _draw(img, g, pred, Path(overlays) / f"{cam}_{f:04d}.jpg")
    return summarise(recs) if recs else {"n_gt": 0}


def check_box_tightness(summary: dict[str, Any], min_iou: float = MIN_IOU,
                        max_top: float = MAX_TOP) -> list[Check]:
    if not summary.get("n_gt"):
        return [Check("box_tightness", SKIP, detail="no GT boxes >= min_h / min_vis in sample")]
    iou = summary["iou_median"]
    top = (summary.get("d_top") or {}).get("median")
    return [
        Check("box_iou_vs_detector", PASS if iou >= min_iou else FAIL, iou, f">= {min_iou}",
              f"n={summary['n_gt']}, IoU>=.7 {summary['frac_iou_ge_0.7']}"),
        Check("box_top_offset", FAIL if top is None or abs(top) > max_top else PASS, top,
              f"|x| <= {max_top}", "detector top - GT top, / GT height"),
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("set_dir", type=Path, help="a rendered set: render/<cam>/NNNN.png + gt/mot_<cam>.txt")
    ap.add_argument("--frames", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--overlays", type=Path, default=None)
    a = ap.parse_args(argv)
    s = measure(a.set_dir, a.frames, a.seed, device=a.device, overlays=a.overlays)
    checks = check_box_tightness(s)
    print(format_table(checks))
    if a.json:
        a.json.write_text(json.dumps({"summary": s, "checks": [c.as_dict() for c in checks]}, indent=1))
    return 1 if any(c.failed for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
