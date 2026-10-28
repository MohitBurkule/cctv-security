"""A person-detection baseline, so our numbers have something to sit against.

`eval/detection.py` can score a detector, but until now nothing had actually run
one. That leaves two questions open that matter more than they sound:

  - **Is the evaluation right?** A scorer with a coordinate-convention bug
    produces plausible AP values forever. Running a known-good detector on a
    known benchmark and getting a sane number is the cheapest available check.
  - **What is a normal score on this kind of footage?** Reporting "our
    simulator yields AP 0.62" means nothing without knowing that a standard
    detector gets roughly that on real crowded CCTV. Half the value of a
    baseline is calibrating the reader's expectations.

Faster R-CNN with a ResNet-50 FPN backbone is used deliberately rather than
something stronger: it is the reference detector of the period, its COCO
weights are what most people start from, and a baseline should be the obvious
default rather than a tuned entry.

The weights download on first use (~160 MB). Everything here degrades to a
clear error when torch is absent rather than pretending.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# COCO class index for "person". The model predicts 91 classes and we want one;
# taking argmax over all of them would report handbags as people.
COCO_PERSON = 1


@dataclass
class DetectorConfig:
    score_threshold: float = 0.05     # low: AP needs the tail, not just confident hits
    batch_size: int = 4
    device: str | None = None         # None -> cuda when available
    max_detections: int = 300


class PersonDetector:
    """COCO-pretrained Faster R-CNN, restricted to people.

    Kept deliberately thin: this is a reference point, not a component of the
    simulator. Nothing in `survsim` depends on it.
    """

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.cfg = config or DetectorConfig()
        self._model = None
        self._device = None

    def _load(self):
        if self._model is not None:
            return self._model
        import torch
        from torchvision.models.detection import (
            FasterRCNN_ResNet50_FPN_Weights,
            fasterrcnn_resnet50_fpn,
        )

        device = self.cfg.device or ("cuda" if torch.cuda.is_available() else "cpu")
        weights = FasterRCNN_ResNet50_FPN_Weights.COCO_V1
        model = fasterrcnn_resnet50_fpn(weights=weights,
                                        box_score_thresh=self.cfg.score_threshold)
        model.eval().to(device)
        self._model, self._device = model, device
        return model

    @property
    def device(self) -> str:
        self._load()
        return str(self._device)

    def detect(self, image_paths: Sequence[Path],
               progress: bool = False) -> list[dict[str, Any]]:
        """Detect people, returning rows in the format our evaluators expect.

        Boxes come out of torchvision as (x1, y1, x2, y2) and are converted to
        (x, y, w, h) here. Every consumer in this codebase uses xywh, and a
        silent mismatch would not crash — it would just produce IoUs near zero
        and an AP near zero that looks like a bad detector rather than a bug.
        """
        import cv2
        import torch
        from torchvision.transforms import functional as F

        model = self._load()
        rows: list[dict[str, Any]] = []
        paths = list(image_paths)

        with torch.no_grad():
            for start in range(0, len(paths), self.cfg.batch_size):
                chunk = paths[start:start + self.cfg.batch_size]
                images, indices = [], []
                for offset, path in enumerate(chunk):
                    img = cv2.imread(str(path))
                    if img is None:
                        continue
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    images.append(F.to_tensor(rgb).to(self._device))
                    indices.append(start + offset)
                if not images:
                    continue

                for frame_idx, output in zip(indices, model(images)):
                    keep = output["labels"] == COCO_PERSON
                    boxes = output["boxes"][keep].cpu().numpy()
                    scores = output["scores"][keep].cpu().numpy()
                    order = np.argsort(-scores)[:self.cfg.max_detections]
                    for i in order:
                        x1, y1, x2, y2 = boxes[i]
                        rows.append({
                            "frame": frame_idx,
                            "bbox": (float(x1), float(y1),
                                     float(x2 - x1), float(y2 - y1)),
                            "score": float(scores[i]),
                        })
                if progress:
                    print(f"  {min(start + self.cfg.batch_size, len(paths))}"
                          f"/{len(paths)} frames", flush=True)
        return rows


def assign_track_ids_by_iou(rows: Sequence[dict[str, Any]],
                            iou_threshold: float = 0.3,
                            max_age: int = 5) -> list[dict[str, Any]]:
    """A deliberately minimal IoU tracker, to make detections scoreable as tracks.

    This is the weakest defensible tracker: greedy IoU association with a short
    memory, no motion model, no appearance. That is the point — it establishes
    the floor. If a real tracker cannot beat this on our data, our data is not
    exercising tracking at all.
    """
    from cctvsec.eval.detection import iou_matrix

    by_frame: dict[int, list[dict]] = {}
    for r in rows:
        by_frame.setdefault(int(r["frame"]), []).append(r)

    out: list[dict[str, Any]] = []
    # track id -> (last frame seen, box)
    active: dict[int, tuple[int, tuple[float, float, float, float]]] = {}
    next_id = 0

    for frame in sorted(by_frame):
        dets = by_frame[frame]
        live = {tid: box for tid, (last, box) in active.items()
                if frame - last <= max_age}

        assigned: dict[int, int] = {}
        if live and dets:
            tids = list(live)
            ious = iou_matrix(np.array([d["bbox"] for d in dets]),
                              np.array([live[t] for t in tids]))
            # Greedy by descending IoU. Optimal assignment would be better; the
            # point of this baseline is to be the obvious thing, not the good one.
            pairs = sorted(((ious[i, j], i, j)
                            for i in range(len(dets)) for j in range(len(tids))),
                           reverse=True)
            used_d, used_t = set(), set()
            for score, i, j in pairs:
                if score < iou_threshold or i in used_d or j in used_t:
                    continue
                assigned[i] = tids[j]
                used_d.add(i); used_t.add(j)

        for i, det in enumerate(dets):
            tid = assigned.get(i)
            if tid is None:
                tid = next_id
                next_id += 1
            active[tid] = (frame, det["bbox"])
            out.append({**det, "id": tid})

    return out
