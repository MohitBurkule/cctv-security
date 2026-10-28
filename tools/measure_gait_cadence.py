"""Measure real walking cadence from CCTV, using pose estimation.

`tools/` because it needs a GPU and a model download; the logic it drives lives
in `survsim/gait/cadence.py` and is unit-tested without either.

Keypoints come from torchvision's Keypoint R-CNN and are attached to the
benchmark's *ground-truth* tracks by IoU rather than to a tracker of our own.
That matters: using our own tracker would mean a single identity switch silently
splices two people's legs into one gait signal, and the resulting cadence would
be wrong in a way nothing downstream could detect. The ground truth already
knows who is who, so the measurement is about gait and not about tracking.

    .venv/bin/python tools/measure_gait_cadence.py [--frames 300] [--seq MOT20-01]

Expect most tracks to be refused. That is correct behaviour, not a failure:
cadence needs two confident ankles and roughly lateral motion, and a crowded
scene supplies neither for most people. The coverage figure is reported so the
refusal rate is visible rather than hidden.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from cctvsec.eval.detection import iou_matrix
from cctvsec.eval.motchallenge import find_sequences, read_sequence
from survsim.gait.cadence import measure_track, summarise

MOT_ROOT = Path.home() / "data" / "mot" / "extracted"


def detect_keypoints(image_paths, batch: int = 4, score_threshold: float = 0.75):
    """Per-frame person keypoints and boxes from Keypoint R-CNN."""
    import cv2
    import torch
    from torchvision.models.detection import (
        KeypointRCNN_ResNet50_FPN_Weights, keypointrcnn_resnet50_fpn,
    )
    from torchvision.transforms import functional as F

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = keypointrcnn_resnet50_fpn(
        weights=KeypointRCNN_ResNet50_FPN_Weights.COCO_V1,
        box_score_thresh=score_threshold)
    model.eval().to(device)
    print(f"keypoint model on {device}", flush=True)

    per_frame = {}
    with torch.no_grad():
        for start in range(0, len(image_paths), batch):
            chunk = image_paths[start:start + batch]
            tensors, indices = [], []
            for offset, path in enumerate(chunk):
                img = cv2.imread(str(path))
                if img is None:
                    continue
                tensors.append(F.to_tensor(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).to(device))
                indices.append(start + offset)
            if not tensors:
                continue
            for frame_idx, out in zip(indices, model(tensors)):
                boxes = out["boxes"].cpu().numpy()
                kps = out["keypoints"].cpu().numpy()          # (N, 17, 3)
                scores = out["keypoints_scores"].cpu().numpy()
                # torchvision puts a visibility flag in kps[..., 2]; replace it
                # with the per-keypoint score, which is what we threshold on.
                kps = kps.copy()
                if scores.size:
                    kps[..., 2] = 1.0 / (1.0 + np.exp(-scores))   # logits -> 0..1
                per_frame[frame_idx] = (boxes, kps)
            if start % 40 == 0:
                print(f"  {start}/{len(image_paths)}", flush=True)
    return per_frame


def attach_to_tracks(gt_rows, per_frame, iou_threshold: float = 0.4):
    """Assign detected keypoints to ground-truth identities, by IoU."""
    gt_by_frame = defaultdict(list)
    for row in gt_rows:
        gt_by_frame[int(row["frame"])].append(row)

    tracks = defaultdict(list)
    for frame, (boxes, kps) in per_frame.items():
        gts = gt_by_frame.get(frame, [])
        if not gts or len(boxes) == 0:
            continue
        # torchvision boxes are xyxy; ours are xywh.
        det_xywh = np.array([[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in boxes])
        gt_xywh = np.array([g["bbox"] for g in gts], dtype=float)
        ious = iou_matrix(det_xywh, gt_xywh)

        for gi, gt in enumerate(gts):
            di = int(np.argmax(ious[:, gi]))
            if ious[di, gi] >= iou_threshold:
                tracks[gt["id"]].append((frame, kps[di]))
    return tracks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--seq", default=None)
    ap.add_argument("--out", type=Path, default=Path("out/gait_cadence.json"))
    args = ap.parse_args()

    seq_dirs = find_sequences(MOT_ROOT)
    if args.seq:
        seq_dirs = [d for d in seq_dirs if d.name == args.seq]
    if not seq_dirs:
        print(f"no sequences under {MOT_ROOT}")
        return 1

    seq = read_sequence(seq_dirs[0])
    images = seq.image_paths[:args.frames]
    if not images:
        print(f"{seq.name}: no images")
        return 1

    fps = 25.0
    info = seq_dirs[0] / "seqinfo.ini"
    if info.is_file():
        for line in info.read_text().splitlines():
            if line.startswith("frameRate"):
                fps = float(line.split("=")[1])

    print(f"{seq.name}: {len(images)} frames at {fps} fps", flush=True)
    per_frame = detect_keypoints(images)
    gt = [r for r in seq.gt if r["frame"] < len(images)]
    tracks = attach_to_tracks(gt, per_frame)
    print(f"{len(tracks)} ground-truth tracks received keypoints", flush=True)

    cycles = []
    for tid, entries in tracks.items():
        entries.sort(key=lambda e: e[0])
        result = measure_track([k for _, k in entries], fps)
        if result is not None:
            cycles.append(result)

    report = summarise(cycles)
    report["sequence"] = seq.name
    report["n_tracks_with_keypoints"] = len(tracks)
    report["coverage"] = round(len(cycles) / max(len(tracks), 1), 3)

    print("\n" + json.dumps(report, indent=2))
    print(f"\n{len(cycles)} of {len(tracks)} tracks supported a cadence estimate "
          "— most refusals are people walking toward the camera or with "
          "occluded ankles, which is expected in a crowd")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"summary": report, "cycles": [c.as_dict() for c in cycles]}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
