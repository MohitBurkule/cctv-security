"""Tests for `tools/eval_recall.py`'s matching, which does not need YOLO or GPU."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.eval_recall import iou, match_frame


def test_iou_of_identical_boxes_is_one() -> None:
    box = [10.0, 10.0, 20.0, 40.0]
    assert iou(box, box) == 1.0


def test_higher_score_detection_gets_first_pick_of_overlapping_gt() -> None:
    """The COCO-style fix: score order, not GT-height order, decides matching.

    Two GT boxes side by side. One detection sits mostly on the tall GT (but
    below threshold there) and partially overlaps the short GT well enough to
    match it too; a second, higher-confidence detection matches the tall GT
    cleanly. Tallest-first GT matching would let the tall GT claim the
    ambiguous low-score detection before the high-score detection is
    considered; score-first matching must not let that happen.
    """
    tall = [0.0, 0.0, 20.0, 100.0]     # height 100 -> "120+"? no, 100 -> "60-120"
    short = [25.0, 0.0, 20.0, 30.0]    # height 30 -> "20-60"
    gts = [tall, short]

    # A low-score, poorly-placed detection that only weakly overlaps `tall`.
    weak_det = [5.0, 0.0, 20.0, 40.0]
    # A high-score detection that matches `tall` well.
    strong_det = [0.0, 0.0, 20.0, 100.0]

    dets = [weak_det, strong_det]
    scores = [0.1, 0.9]  # weak_det has the lower score

    tp, fp, gt_used = match_frame(gts, dets, scores, thr=0.5)

    # strong_det (processed first, by score) claims `tall`; weak_det then finds
    # `tall` already taken and its own IoU with `tall` is below threshold, so
    # it becomes a false positive rather than displacing the good match.
    assert gt_used[0] is True   # tall matched
    assert tp == 1
    assert fp == 1


def test_matching_is_indifferent_to_gt_order_now_that_it_is_score_driven() -> None:
    gts_a = [[0.0, 0.0, 20.0, 20.0], [50.0, 0.0, 20.0, 200.0]]
    gts_b = list(reversed(gts_a))
    dets = [[0.0, 0.0, 20.0, 20.0], [50.0, 0.0, 20.0, 200.0]]
    scores = [0.9, 0.5]

    tp_a, fp_a, _ = match_frame(gts_a, dets, scores)
    tp_b, fp_b, _ = match_frame(gts_b, dets, scores)
    assert (tp_a, fp_a) == (tp_b, fp_b) == (2, 0)


def test_all_detections_below_threshold_are_false_positives_not_matches() -> None:
    gts = [[0.0, 0.0, 20.0, 20.0]]
    dets = [[100.0, 100.0, 20.0, 20.0]]
    scores = [0.9]
    tp, fp, gt_used = match_frame(gts, dets, scores, thr=0.5)
    assert tp == 0
    assert fp == 1
    assert gt_used == [False]
