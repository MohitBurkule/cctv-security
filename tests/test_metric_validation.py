"""Check our tracking metrics against effects derivable from their definitions.

Every headline number in docs/14 comes out of `evaluate_mot`. A metric that is
quietly 10% wrong still looks like a plausible metric, and a self-consistent
test cannot catch it — the inverted-pitch bug survived exactly that kind of
test. So these tests never ask "does the implementation agree with itself". They
construct a perturbation whose effect follows from the *definition* of the
metric, and check the implementation reproduces it.

MOTA = 1 - (FN + FP + IDSW) / n_gt. That identity is the lever: drop 10% of
boxes and MOTA must fall by 0.10, not "by about a tenth".

The ground truth used here is synthetic but MOT-formatted, so the tests run in
CI with no download. `test_motchallenge_real_data.py` runs the same checks
against real MOT17 when it is present.
"""

from __future__ import annotations

import numpy as np
import pytest

from cctvsec.eval.motchallenge import (
    add_false_positives,
    drop_fraction,
    jitter_boxes,
    parse_mot_rows,
    swap_identities,
)
from cctvsec.eval.tracking import evaluate_mot


def _synthetic(n_people: int = 10, n_frames: int = 50) -> list[dict]:
    """People walking in straight lines, well separated so matching is unambiguous."""
    rows = []
    for uid in range(n_people):
        for frame in range(n_frames):
            rows.append({
                "frame": frame, "id": uid,
                "bbox": (100.0 * uid, 5.0 * frame, 30.0, 70.0),
                "score": 1.0, "visibility": 1.0,
            })
    return rows


# ------------------------------------------------------------------ parsing


def test_frames_are_converted_from_one_based_to_zero_based() -> None:
    """An off-by-one here shifts every prediction one frame and halves the score."""
    rows = parse_mot_rows(["1,3,10,20,30,40,1,1,1.0"], is_ground_truth=True)
    assert rows[0]["frame"] == 0
    assert rows[0]["id"] == 3
    assert rows[0]["bbox"] == (10.0, 20.0, 30.0, 40.0)


def test_ground_truth_conf_zero_marks_an_excluded_box() -> None:
    """Scoring them as misses silently depresses recall on every sequence."""
    lines = ["1,1,10,20,30,40,1,1,1.0", "1,2,10,20,30,40,0,1,1.0"]
    assert len(parse_mot_rows(lines, is_ground_truth=True)) == 1
    # In a detection file the same column is a real confidence, not a flag.
    assert len(parse_mot_rows(lines, is_ground_truth=False)) == 2


def test_non_pedestrian_classes_are_excluded() -> None:
    lines = ["1,1,10,20,30,40,1,1,1.0",     # pedestrian
             "1,2,10,20,30,40,1,7,1.0",     # static person — a distractor
             "1,3,10,20,30,40,1,3,1.0"]     # car
    rows = parse_mot_rows(lines, is_ground_truth=True)
    assert len(rows) == 1
    assert rows[0]["id"] == 1


def test_visibility_filter_is_applied_only_to_ground_truth() -> None:
    lines = ["1,1,10,20,30,40,1,1,0.1", "1,2,10,20,30,40,1,1,0.9"]
    assert len(parse_mot_rows(lines, is_ground_truth=True, min_visibility=0.5)) == 1
    assert len(parse_mot_rows(lines, is_ground_truth=True)) == 2


def test_malformed_and_comment_lines_are_skipped_not_crashed_on() -> None:
    rows = parse_mot_rows(["# header", "", "1,1,10,20,30,40,1,1,1.0", "garbage,x"],
                          is_ground_truth=True)
    assert len(rows) == 1


# ----------------------------------------------------- the perfect tracker


def test_ground_truth_scored_against_itself_is_perfect() -> None:
    """The one self-consistency check worth having: it pins the scale's top end."""
    gt = _synthetic()
    r = evaluate_mot(gt, gt)

    assert r.mota == pytest.approx(1.0)
    assert r.idf1 == pytest.approx(1.0)
    assert r.hota == pytest.approx(1.0)
    assert r.id_switches == 0
    assert r.misses == 0
    assert r.false_positives == 0


def test_an_empty_tracker_scores_zero_and_misses_everything() -> None:
    gt = _synthetic()
    r = evaluate_mot(gt, [])
    assert r.misses == len(gt)
    assert r.mota == pytest.approx(0.0)
    assert r.idf1 == pytest.approx(0.0)


# ------------------------------------------------- MOTA follows its definition


@pytest.mark.parametrize("fraction", [0.1, 0.25, 0.5])
def test_dropping_a_fraction_of_boxes_costs_exactly_that_much_mota(fraction) -> None:
    """MOTA = 1 - (FN+FP+IDSW)/n_gt, so pure misses cost their own fraction.

    Checked against the definition rather than against a recorded value, so it
    catches an implementation that is internally consistent but wrong.
    """
    gt = _synthetic(n_people=20, n_frames=50)
    pred = drop_fraction(gt, fraction, seed=1)
    r = evaluate_mot(gt, pred)

    dropped = len(gt) - len(pred)
    assert r.misses == dropped
    assert r.false_positives == 0
    assert r.id_switches == 0
    assert r.mota == pytest.approx(1.0 - dropped / len(gt), abs=1e-6)


def test_false_positives_cost_mota_in_the_same_currency_as_misses() -> None:
    """MOTA weights FP and FN equally — a fact operators are often surprised by."""
    gt = _synthetic(n_people=10, n_frames=20)
    n_fp = 37
    r = evaluate_mot(gt, add_false_positives(gt, n_fp, seed=2))

    assert r.false_positives == n_fp
    assert r.misses == 0
    assert r.mota == pytest.approx(1.0 - n_fp / len(gt), abs=1e-6)


def test_mota_can_go_negative_when_false_positives_exceed_the_ground_truth() -> None:
    """Not a bug, and clamping it to zero would hide a catastrophic tracker."""
    gt = _synthetic(n_people=2, n_frames=5)
    r = evaluate_mot(gt, add_false_positives(gt, len(gt) * 2, seed=3))
    assert r.mota < 0.0


# ------------------------------------------- detection versus association


def test_an_identity_swap_barely_moves_mota_but_hurts_idf1() -> None:
    """The single most important property of the metric pair.

    Every box is in the right place, so detection is untouched; only the names
    are wrong. MOTA charges one frame for the switch, IDF1 charges for the
    entire mislabelled remainder of both tracks. A system evaluated on MOTA
    alone would report an identity-swapping tracker as near-perfect — which is
    exactly why MTMC work reports IDF1.
    """
    gt = _synthetic(n_people=10, n_frames=60)
    pred = swap_identities(gt, 0, 1, at_frame=30)
    r = evaluate_mot(gt, pred)

    assert r.misses == 0 and r.false_positives == 0
    assert r.mota > 0.99, "detection is untouched, so MOTA should barely move"
    assert r.idf1 < 0.95, "half of two tracks is mislabelled"
    assert r.assa < r.deta, "the damage is associative, not detective"


def test_hota_splits_into_detection_and_association_accuracy() -> None:
    """HOTA's whole selling point: it says *which* half is failing."""
    gt = _synthetic(n_people=8, n_frames=40)

    missing = evaluate_mot(gt, drop_fraction(gt, 0.3, seed=4))
    swapped = evaluate_mot(gt, swap_identities(gt, 0, 1, at_frame=20))

    # Dropping boxes is a detection failure; swapping names is an association one.
    assert missing.deta < 0.95
    assert swapped.deta > missing.deta
    assert swapped.assa < missing.assa or swapped.assa < 1.0


def test_hota_lies_between_its_two_components() -> None:
    """HOTA is the geometric mean of DetA and AssA, so it cannot exceed both."""
    gt = _synthetic(n_people=6, n_frames=30)
    r = evaluate_mot(gt, drop_fraction(swap_identities(gt, 0, 1, 15), 0.2, seed=5))
    assert min(r.deta, r.assa) - 1e-9 <= r.hota <= max(r.deta, r.assa) + 1e-9


# ---------------------------------------------------- localisation vs. count


def test_small_jitter_costs_precision_but_not_detection() -> None:
    """MOTP measures where the boxes are; MOTA measures whether they exist."""
    gt = _synthetic(n_people=10, n_frames=30)
    clean = evaluate_mot(gt, gt)
    nudged = evaluate_mot(gt, jitter_boxes(gt, pixels=4.0, seed=6))

    assert nudged.motp < clean.motp, "localisation got worse"
    assert nudged.mota == pytest.approx(clean.mota, abs=1e-6), "still detected"


def test_jitter_large_enough_to_break_the_iou_threshold_becomes_a_miss() -> None:
    """Past the IoU threshold a box stops counting as the same object at all."""
    gt = _synthetic(n_people=10, n_frames=30)
    r = evaluate_mot(gt, jitter_boxes(gt, pixels=200.0, seed=7))
    assert r.misses > 0
    assert r.mota < 0.5


# ------------------------------------------------------------ sanity bounds


@pytest.mark.parametrize("seed", range(5))
def test_metrics_stay_inside_their_definitional_ranges(seed: int) -> None:
    """Fuzzed degradation must never produce an out-of-range score."""
    rng = np.random.default_rng(seed)
    gt = _synthetic(n_people=8, n_frames=25)
    pred = drop_fraction(gt, float(rng.uniform(0, 0.6)), seed=seed)
    pred = add_false_positives(pred, int(rng.integers(0, 20)), seed=seed)
    if len(gt) > 0:
        pred = swap_identities(pred, 0, 1, at_frame=int(rng.integers(1, 25)))
    r = evaluate_mot(gt, pred)

    for name in ("idf1", "idp", "idr", "hota", "deta", "assa", "motp"):
        value = getattr(r, name)
        assert 0.0 <= value <= 1.0, f"{name}={value} out of range"
    assert r.mota <= 1.0
    assert r.misses >= 0 and r.false_positives >= 0
