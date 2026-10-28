"""Tests for COCO export and stratified detection scoring."""

from __future__ import annotations

import json

import numpy as np
import pytest

from cctvsec.eval.detection import evaluate, evaluate_coco, iou_matrix
from survsim.gt.coco import COCO_KEYPOINTS, HEIGHT_BUCKETS, CocoBuilder, bucket_of, from_camera_rows

# ------------------------------------------------------------------ export


def test_builder_emits_valid_coco_structure(tmp_path) -> None:
    b = CocoBuilder()
    img = b.add_image("cam_a", 0, 1280, 720)
    b.add_person(img, "p0", (10, 20, 30, 90), px_height=90)
    data = json.loads(b.write(tmp_path / "c.json").read_text())

    assert {"images", "annotations", "categories", "info"} <= set(data)
    assert data["categories"][0]["keypoints"] == list(COCO_KEYPOINTS)
    assert data["annotations"][0]["bbox"] == [10.0, 20.0, 30.0, 90.0]
    assert data["annotations"][0]["area"] == 2700.0


def test_same_camera_frame_reuses_one_image_id() -> None:
    b = CocoBuilder()
    a = b.add_image("cam_a", 5, 640, 480)
    assert b.add_image("cam_a", 5, 640, 480) == a
    assert b.add_image("cam_b", 5, 640, 480) != a


def test_track_ids_are_stable_per_identity() -> None:
    b = CocoBuilder()
    img = b.add_image("c", 0, 640, 480)
    first = b.add_person(img, "alice", (0, 0, 10, 30))["track_id"]
    second = b.add_person(img, "alice", (5, 0, 10, 30))["track_id"]
    other = b.add_person(img, "bob", (50, 0, 10, 30))["track_id"]
    assert first == second != other


def test_occlusion_is_derived_from_visible_versus_amodal() -> None:
    """Half the person hidden behind a railing should read as ~0.5 occluded."""
    b = CocoBuilder()
    img = b.add_image("c", 0, 640, 480)
    ann = b.add_person(img, "p", (0, 0, 20, 50), amodal_bbox=(0, 0, 20, 100))
    assert ann["occlusion"] == pytest.approx(0.5, abs=1e-6)
    assert ann["difficulty"]["occlusion_bucket"] == "heavy"


def test_no_amodal_box_means_no_claimed_occlusion() -> None:
    b = CocoBuilder()
    img = b.add_image("c", 0, 640, 480)
    assert b.add_person(img, "p", (0, 0, 20, 50))["occlusion"] == 0.0


def test_height_buckets_follow_the_detectability_boundary() -> None:
    assert bucket_of(15.0, HEIGHT_BUCKETS) == "unusable"   # below ~20 px
    assert bucket_of(25.0, HEIGHT_BUCKETS) == "tiny"
    assert bucket_of(200.0, HEIGHT_BUCKETS) == "large"


def test_keypoints_are_flattened_with_visibility_flags() -> None:
    b = CocoBuilder()
    img = b.add_image("c", 0, 640, 480)
    kp = np.zeros((17, 3))
    kp[0] = (100, 50, 2)      # visible
    kp[1] = (110, 55, 1)      # occluded but labelled
    ann = b.add_person(img, "p", (0, 0, 40, 120), keypoints=kp)

    assert len(ann["keypoints"]) == 17 * 3
    assert ann["num_keypoints"] == 2
    assert ann["keypoints"][:3] == [100.0, 50.0, 2]


def test_usable_fraction_flags_an_unresolvable_set() -> None:
    b = CocoBuilder()
    img = b.add_image("c", 0, 640, 480)
    for i in range(8):
        b.add_person(img, f"p{i}", (0, 0, 5, 10), px_height=10)   # all too small
    b.add_person(img, "big", (0, 0, 40, 120), px_height=120)
    assert b.usable_fraction() == pytest.approx(1 / 9, abs=1e-3)


def test_from_camera_rows_converts_backend_output() -> None:
    rows = [{
        "frame": 3, "camera": "cam_a", "uid": "p0", "bbox": (10, 10, 20, 60),
        "px_height": 60, "fill_ratio": 0.5, "mask_area_px": 600, "label": "suspicious.loiter",
    }]
    b = from_camera_rows(rows, resolution=(1280, 720))
    ann = b.annotations[0]
    assert ann["behaviour"] == "suspicious.loiter"
    assert "amodal_bbox" in ann and ann["occlusion"] > 0


def test_from_camera_rows_skips_wildlife_rows_by_default() -> None:
    # MOT class 8 / consider 0 (survsim/gt/writers.py._mot_class, distinguished by
    # object_class="animal") is an ignore region, never a scoring target -- the
    # same treatment `survsim dataset` gives it (IGNORE_CLASSES in
    # survsim/datasets/build.py). Exporting it as COCO "person" would silently
    # teach a detector to find wildlife (CLAUDE.md principle 1).
    rows = [
        {"frame": 1, "camera": "cam_a", "uid": "p0", "bbox": (10, 10, 20, 60),
         "px_height": 60, "object_class": "person"},
        {"frame": 1, "camera": "cam_a", "uid": "fox0", "bbox": (50, 50, 15, 10),
         "px_height": 10, "object_class": "animal"},
    ]
    b = from_camera_rows(rows, resolution=(1280, 720))
    assert len(b.annotations) == 1
    assert b.annotations[0]["uid"] == "p0"

    b_all = from_camera_rows(rows, resolution=(1280, 720), include_non_person=True)
    assert len(b_all.annotations) == 2


# ------------------------------------------------------------------- iou


def test_iou_of_identical_boxes_is_one() -> None:
    a = np.array([[0, 0, 10, 10]], dtype=float)
    assert iou_matrix(a, a)[0, 0] == pytest.approx(1.0)


def test_iou_of_disjoint_boxes_is_zero() -> None:
    a = np.array([[0, 0, 10, 10]], dtype=float)
    b = np.array([[50, 50, 10, 10]], dtype=float)
    assert iou_matrix(a, b)[0, 0] == 0.0


def test_iou_handles_empty_inputs() -> None:
    assert iou_matrix(np.zeros((0, 4)), np.ones((2, 4))).shape == (0, 2)


# -------------------------------------------------------------- evaluation


def _gt(bbox, bucket="medium"):
    return {"bbox": bbox, "difficulty": {"height_bucket": bucket}}


def test_perfect_predictions_score_one() -> None:
    gt = {1: [_gt([0, 0, 20, 60])]}
    pred = {1: [{"bbox": [0, 0, 20, 60], "score": 0.9}]}
    r = evaluate(gt, pred)
    assert r.recall == 1.0 and r.precision == 1.0
    assert r.ap > 0.99


def test_missed_detection_is_a_false_negative() -> None:
    r = evaluate({1: [_gt([0, 0, 20, 60])]}, {1: []})
    assert r.false_negatives == 1 and r.recall == 0.0


def test_one_prediction_cannot_claim_two_ground_truths() -> None:
    gt = {1: [_gt([0, 0, 20, 60]), _gt([1, 1, 20, 60])]}
    pred = {1: [{"bbox": [0, 0, 20, 60], "score": 0.9}]}
    r = evaluate(gt, pred)
    assert r.true_positives == 1 and r.false_negatives == 1


def test_unresolvable_people_are_excluded_from_recall() -> None:
    """Scoring a detector on people it cannot physically resolve measures the rig."""
    gt = {1: [_gt([0, 0, 4, 12], bucket="unusable"), _gt([0, 0, 20, 60])]}
    pred = {1: [{"bbox": [0, 0, 20, 60], "score": 0.9}]}

    strict = evaluate(gt, pred, ignore_unusable=False)
    fair = evaluate(gt, pred, ignore_unusable=True)
    assert strict.recall == 0.5
    assert fair.recall == 1.0 and fair.n_gt == 1


def test_stratified_results_expose_where_it_fails() -> None:
    """An averaged AP hides that the detector only works on close-up people."""
    gt = {
        1: [_gt([0, 0, 100, 300], "large")],
        2: [_gt([0, 0, 12, 36], "tiny")],
    }
    pred = {1: [{"bbox": [0, 0, 100, 300], "score": 0.95}], 2: []}
    r = evaluate(gt, pred)

    assert r.per_stratum["large"]["recall"] == 1.0
    assert r.per_stratum["tiny"]["recall"] == 0.0


def test_fppi_translates_into_alarms_per_camera_hour() -> None:
    """The arithmetic that separates a benchmark score from a usable product."""
    gt = {i: [] for i in range(10)}
    pred = {i: [{"bbox": [0, 0, 10, 10], "score": 0.5}] for i in range(10)}
    r = evaluate(gt, pred, fps=25.0)

    assert r.fppi == 1.0
    assert r.false_alarms_per_camera_hour == pytest.approx(90000.0)


def test_evaluate_coco_round_trips_a_built_dataset() -> None:
    b = CocoBuilder()
    img = b.add_image("cam", 0, 640, 480)
    b.add_person(img, "p0", (10, 10, 30, 90), px_height=90)
    data = b.to_dict()

    preds = [{"image_id": img, "bbox": [10, 10, 30, 90], "score": 0.8}]
    assert evaluate_coco(data, preds).recall == 1.0
