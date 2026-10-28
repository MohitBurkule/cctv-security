"""Tests for the detection/tracking baseline.

The baseline exists to give our own numbers a reference point, so the thing that
matters is that it speaks the same dialect as our evaluators. torchvision emits
boxes as (x1, y1, x2, y2); everything in this codebase uses (x, y, w, h). That
mismatch does not crash — it produces IoUs near zero and an AP near zero, which
reads as a bad detector rather than a bug, and would quietly make every
comparison meaningless.

The model itself is not tested here (weights are a 160 MB download); the
conversion and the tracker are, since those are ours.
"""

from __future__ import annotations

import pytest

from cctvsec.eval.tracking import evaluate_mot
from cctvsec.models.detector import (
    COCO_PERSON,
    DetectorConfig,
    assign_track_ids_by_iou,
)

torch = pytest.importorskip("torch", reason="torch not installed")


def _dets(frame: int, boxes: list[tuple[float, float, float, float]],
          score: float = 0.9) -> list[dict]:
    return [{"frame": frame, "bbox": b, "score": score} for b in boxes]


# ----------------------------------------------------------------- config


def test_person_class_is_the_coco_index_not_argmax() -> None:
    """Taking argmax across all 91 classes would report handbags as people."""
    assert COCO_PERSON == 1


def test_score_threshold_is_low_so_average_precision_has_its_tail() -> None:
    """AP integrates over the precision-recall curve; a high cut truncates it."""
    assert DetectorConfig().score_threshold <= 0.1


# ---------------------------------------------------------------- tracker


def test_a_person_walking_steadily_keeps_one_identity() -> None:
    rows = []
    for f in range(20):
        rows += _dets(f, [(10.0 + 2 * f, 50.0, 30.0, 70.0)])
    tracked = assign_track_ids_by_iou(rows)

    assert len({r["id"] for r in tracked}) == 1


def test_two_separated_people_get_two_identities() -> None:
    rows = []
    for f in range(15):
        rows += _dets(f, [(10.0 + f, 50.0, 30.0, 70.0),
                          (500.0 + f, 50.0, 30.0, 70.0)])
    tracked = assign_track_ids_by_iou(rows)
    assert len({r["id"] for r in tracked}) == 2


def test_a_teleporting_box_starts_a_new_identity() -> None:
    """No IoU overlap means no evidence it is the same person."""
    rows = _dets(0, [(10.0, 10.0, 30.0, 70.0)]) + \
        _dets(1, [(900.0, 600.0, 30.0, 70.0)])
    assert len({r["id"] for r in assign_track_ids_by_iou(rows)}) == 2


def test_a_short_gap_is_bridged_but_a_long_one_is_not() -> None:
    """max_age is what separates a brief occlusion from a departure."""
    near = _dets(0, [(10.0, 10.0, 30.0, 70.0)]) + _dets(3, [(12.0, 10.0, 30.0, 70.0)])
    far = _dets(0, [(10.0, 10.0, 30.0, 70.0)]) + _dets(40, [(12.0, 10.0, 30.0, 70.0)])

    assert len({r["id"] for r in assign_track_ids_by_iou(near, max_age=5)}) == 1
    assert len({r["id"] for r in assign_track_ids_by_iou(far, max_age=5)}) == 2


def test_every_detection_is_assigned_exactly_one_identity() -> None:
    """Dropping detections here would silently depress recall downstream."""
    rows = []
    for f in range(10):
        rows += _dets(f, [(10.0 + f, 20.0, 30.0, 70.0),
                          (200.0 - f, 20.0, 30.0, 70.0),
                          (400.0, 20.0 + f, 30.0, 70.0)])
    tracked = assign_track_ids_by_iou(rows)

    assert len(tracked) == len(rows)
    assert all("id" in r for r in tracked)


def test_one_identity_is_not_assigned_twice_in_a_frame() -> None:
    """A track cannot be two places at once; that would corrupt IDF1."""
    rows = []
    for f in range(8):
        rows += _dets(f, [(10.0 + f, 20.0, 40.0, 80.0),
                          (25.0 + f, 20.0, 40.0, 80.0)])   # heavily overlapping
    tracked = assign_track_ids_by_iou(rows)

    for frame in {r["frame"] for r in tracked}:
        ids = [r["id"] for r in tracked if r["frame"] == frame]
        assert len(ids) == len(set(ids))


def test_empty_input_produces_empty_output() -> None:
    assert assign_track_ids_by_iou([]) == []


# ------------------------------------------- it is scoreable end to end


def test_baseline_tracks_are_scoreable_against_ground_truth() -> None:
    """The integration check: our tracker's output feeds our evaluator.

    Perfect detections through the baseline tracker must score perfectly. If
    box conventions or key names disagree anywhere along that path, this drops
    to zero rather than erroring.
    """
    gt = []
    for f in range(25):
        gt.append({"frame": f, "id": 7, "bbox": (10.0 + 3 * f, 40.0, 30.0, 70.0)})
        gt.append({"frame": f, "id": 9, "bbox": (600.0 - 2 * f, 40.0, 30.0, 70.0)})

    dets = [{"frame": r["frame"], "bbox": r["bbox"], "score": 0.99} for r in gt]
    result = evaluate_mot(gt, assign_track_ids_by_iou(dets))

    assert result.mota == pytest.approx(1.0)
    assert result.idf1 == pytest.approx(1.0)
    assert result.id_switches == 0
