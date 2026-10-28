"""Run the detection/tracking baseline on real CCTV and report what it scores.

Two purposes, both about trust rather than about the detector:

  - **Validate the evaluators end-to-end.** `eval/detection.py` and
    `eval/tracking.py` have been checked against their definitions on
    constructed data. Running a genuinely good detector over real footage and
    getting a sane AP is the complementary check: a coordinate-convention bug
    would show up here as a near-zero AP that looks like a bad detector.
  - **Give our own numbers a reference point.** "AP 0.62 on our data" is
    uninterpretable until you know what the same detector scores on real
    crowded CCTV.

    .venv/bin/python tools/run_baseline.py [--frames 200] [--seq MOT20-01]

Expect a *low* AP on MOT20 and do not treat it as a bug: the sequences are
extremely crowded, most people are heavily occluded, and a COCO-pretrained
detector with no fine-tuning is out of domain. That is the honest baseline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cctvsec.eval.detection import evaluate
from cctvsec.eval.motchallenge import find_sequences, read_sequence
from cctvsec.eval.tracking import evaluate_mot
from cctvsec.models.detector import (
    DetectorConfig, PersonDetector, assign_track_ids_by_iou,
)

MOT_ROOT = Path.home() / "data" / "mot" / "extracted"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=200)
    ap.add_argument("--seq", default=None, help="sequence name, e.g. MOT20-01")
    ap.add_argument("--out", type=Path, default=Path("out/baseline.json"))
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

    detector = PersonDetector(DetectorConfig())
    print(f"{seq.name}: {len(images)} frames on {detector.device}")

    preds = detector.detect(images, progress=True)
    print(f"  {len(preds)} detections")

    # Ground truth restricted to the frames actually run, or every unrun frame
    # would count as a total miss and drive recall to nearly zero.
    gt = [r for r in seq.gt if r["frame"] < len(images)]
    print(f"  {len(gt)} ground-truth boxes in those frames")

    det_result = evaluate(_by_frame(gt), _by_frame(preds), stratify=None)
    print("\ndetection:")
    for k, v in det_result.as_dict().items():
        print(f"  {k:<24} {v}")

    tracked = assign_track_ids_by_iou(preds)
    track_result = evaluate_mot(gt, tracked)
    print("\ntracking (greedy IoU baseline — the floor, not a good tracker):")
    for k, v in track_result.as_dict().items():
        print(f"  {k:<24} {v}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "sequence": seq.name, "frames": len(images),
        "n_detections": len(preds), "n_gt": len(gt),
        "detection": det_result.as_dict(),
        "tracking": track_result.as_dict(),
        "note": ("COCO-pretrained Faster R-CNN with no fine-tuning, on a "
                 "deliberately crowded benchmark; a low AP here is the honest "
                 "out-of-domain baseline, not a defect"),
    }, indent=2))
    print(f"\nwrote {args.out}")
    return 0


def _by_frame(rows):
    out: dict[int, list] = {}
    for r in rows:
        out.setdefault(int(r["frame"]), []).append(r)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
