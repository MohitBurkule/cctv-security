"""Tests for MOT / MTMC / ReID scoring.

The assertions encode the properties that make these metrics worth reporting:
MOTA punishes frame errors, IDF1 punishes identity inconsistency, HOTA separates
detection from association, and ReID must be scored separately across an
appearance change.
"""

from __future__ import annotations

import numpy as np
import pytest

from cctvsec.eval.tracking import (
    evaluate_mot,
    evaluate_mtmc,
    evaluate_reid,
    reid_by_epoch,
)


def _track(track_id, frames, x0=0.0, camera="cam_a"):
    return [{"frame": f, "id": track_id, "camera": camera,
             "bbox": [x0 + 5.0 * f, 10.0, 20.0, 60.0]} for f in frames]


# ------------------------------------------------------------------- MOT


def test_perfect_tracking_scores_one() -> None:
    gt = _track("a", range(10))
    pred = _track(1, range(10))
    r = evaluate_mot(gt, pred)
    assert r.mota == pytest.approx(1.0)
    assert r.idf1 == pytest.approx(1.0)
    assert r.id_switches == 0
    assert r.hota > 0.99


def test_missed_frames_reduce_mota_and_deta() -> None:
    gt = _track("a", range(10))
    pred = _track(1, range(5))
    r = evaluate_mot(gt, pred)
    assert r.misses == 5
    assert r.mota == pytest.approx(0.5)
    assert r.deta == pytest.approx(0.5)


def test_identity_switch_is_counted_and_hurts_idf1_more_than_mota() -> None:
    """One switch costs MOTA a single frame but halves identity consistency."""
    gt = _track("a", range(10))
    pred = _track(1, range(5)) + _track(2, range(5, 10))
    r = evaluate_mot(gt, pred)

    assert r.id_switches == 1
    assert r.mota == pytest.approx(0.9)      # 1 error in 10 frames
    assert r.idf1 < 0.75                     # identity was only half-consistent


def test_association_failure_shows_up_in_assa_not_deta() -> None:
    """HOTA's decomposition tells you which half to fix."""
    gt = _track("a", range(20))
    pred = [r for i in range(4)
            for r in _track(i, range(i * 5, (i + 1) * 5))]
    r = evaluate_mot(gt, pred)
    assert r.deta == pytest.approx(1.0)      # every frame detected
    assert r.assa < 0.4                      # but the identity kept breaking


def test_false_positives_are_counted() -> None:
    gt = _track("a", range(5))
    pred = _track(1, range(5)) + [
        {"frame": f, "id": 99, "camera": "cam_a", "bbox": [500.0, 500.0, 20.0, 60.0]}
        for f in range(5)
    ]
    r = evaluate_mot(gt, pred)
    assert r.false_positives == 5
    assert r.mota == pytest.approx(0.0)


def test_fragmentation_counts_track_resumption() -> None:
    """A person reappearing after an occlusion or blind spot."""
    gt = _track("a", range(10))
    pred = _track(1, [0, 1, 2, 7, 8, 9]) + _distractor(range(3, 7))
    r = evaluate_mot(gt, pred)
    assert r.fragmentations >= 1


def _distractor(frames) -> list[dict]:
    """A far-away prediction so gap frames are not prediction-empty."""
    return [{"frame": f, "id": 99, "bbox": [900.0, 900.0, 10.0, 10.0]} for f in frames]


def test_prediction_empty_gap_is_not_a_fragmentation_trackeval_quirk() -> None:
    """TrackEval skips frames with no predictions at all (clear.py `continue`),
    so a gap in which the tracker output nothing does not interrupt the run.
    We match the reference (tests/test_trackeval_parity.py), quirk included."""
    r = evaluate_mot(_track("a", range(10)), _track(1, [0, 1, 2, 7, 8, 9]))
    assert r.fragmentations == 0


def test_empty_prediction_scores_zero_without_crashing() -> None:
    r = evaluate_mot(_track("a", range(5)), [])
    assert r.mota <= 0.0 and r.idf1 == 0.0 and r.misses == 5


def test_a_gt_that_enters_unmatched_is_not_a_fragmentation() -> None:
    """A trajectory has to have been tracked once before its resumption counts.

    Frame 0: GT present, no prediction at all (e.g. it spawns off-camera and the
    tracker has not picked it up yet). Frame 1 onward: matched. That is a track
    *starting*, not an occlusion being bridged, so it must not cost a Frag.
    """
    gt = _track("a", range(5))
    pred = _track(1, range(1, 5))  # frame 0 unmatched, then continuously tracked
    r = evaluate_mot(gt, pred)
    assert r.fragmentations == 0


def test_fragmentation_still_counts_a_real_resumption() -> None:
    gt = _track("a", range(10))
    pred = _track(1, [0, 1, 2, 7, 8, 9]) + _distractor(range(3, 7))  # tracked, gap, tracked
    r = evaluate_mot(gt, pred)
    assert r.fragmentations == 1


def test_previous_frame_match_is_kept_over_a_marginally_cheaper_swap() -> None:
    """CLEAR-MOT matching: keep a still-valid match before running Hungarian.

    Two people are matched cleanly in frame 0. In frame 1 they have moved just
    close enough that swapping identities would score a hair higher on total
    IoU (0.667+0.667 swapped vs 0.6+0.6 kept) than keeping the existing
    matches (all boxes are 20x20; IoU(pred, gt) verified with `iou_matrix`).
    Re-solving from scratch every frame takes the swap and invents an identity
    switch; the standard procedure carries the previous frame's still-valid
    match forward first and does not swap.
    """
    gt = [
        {"frame": 0, "id": "A", "bbox": [0.0, 0.0, 20.0, 20.0]},
        {"frame": 0, "id": "B", "bbox": [9.0, 0.0, 20.0, 20.0]},
        {"frame": 1, "id": "A", "bbox": [5.0, 0.0, 20.0, 20.0]},
        {"frame": 1, "id": "B", "bbox": [4.0, 0.0, 20.0, 20.0]},
    ]
    pred = [
        {"frame": 0, "id": 1, "bbox": [0.0, 0.0, 20.0, 20.0]},
        {"frame": 0, "id": 2, "bbox": [9.0, 0.0, 20.0, 20.0]},
        {"frame": 1, "id": 1, "bbox": [0.0, 0.0, 20.0, 20.0]},
        {"frame": 1, "id": 2, "bbox": [9.0, 0.0, 20.0, 20.0]},
    ]
    r = evaluate_mot(gt, pred)
    assert r.id_switches == 0
    assert r.mota == pytest.approx(1.0)


def test_hota_worked_three_frame_example_from_report_26() -> None:
    """docs/research/26_MOT_DEEP_DIVE.md §6.4, reproduced exactly.

    Two people A, B seen in 3 frames. Frame 2: B is lost, A is (wrongly) given
    B's id, and a false positive is hallucinated. Frame 3: B reappears under
    A's old id. IoUs of the real matches are exactly 0.90, 0.80, 0.70, 0.85,
    0.60 by construction (same-size boxes, offset chosen algebraically), which
    is why the numbers below are exact rather than approximate.

    Before this fix the repo's DetA was detection *recall* (TP/(TP+FN)), which
    ignores the false positive; it reported DetA 0.833 and HOTA(single alpha)
    0.532. The paper's definition (DetA = TP/(TP+FN+FP)) gives 0.714 and 0.493.
    """

    def shifted(dx: float, x0: float = 0.0) -> list[float]:
        return [x0 + dx, 0.0, 10.0, 10.0]

    gt = [
        {"frame": 1, "id": "A", "bbox": [0.0, 0.0, 10.0, 10.0]},
        {"frame": 1, "id": "B", "bbox": [100.0, 0.0, 10.0, 10.0]},
        {"frame": 2, "id": "A", "bbox": [0.0, 0.0, 10.0, 10.0]},
        {"frame": 2, "id": "B", "bbox": [100.0, 0.0, 10.0, 10.0]},
        {"frame": 3, "id": "A", "bbox": [0.0, 0.0, 10.0, 10.0]},
        {"frame": 3, "id": "B", "bbox": [100.0, 0.0, 10.0, 10.0]},
    ]
    pred = [
        {"frame": 1, "id": 1, "bbox": shifted(10 / 19)},          # A, IoU 0.90
        {"frame": 1, "id": 2, "bbox": shifted(10 / 9, 100.0)},    # B, IoU 0.80
        {"frame": 2, "id": 2, "bbox": shifted(30 / 17)},          # A given B's id, IoU 0.70
        {"frame": 2, "id": 3, "bbox": [500.0, 500.0, 10.0, 10.0]},  # hallucinated FP
        {"frame": 3, "id": 2, "bbox": shifted(30 / 37)},          # A keeps id 2, IoU 0.85
        {"frame": 3, "id": 1, "bbox": shifted(2.5, 100.0)},       # B given A's old id, IoU 0.60
    ]
    r = evaluate_mot(gt, pred)

    assert r.mota == pytest.approx(0.3333, abs=1e-4)
    assert r.motp == pytest.approx(0.77, abs=1e-4)
    assert r.idf1 == pytest.approx(0.5, abs=1e-4)
    assert r.id_switches == 2
    assert r.fragmentations == 1

    # The HOTA-paper DetA/AssA/HOTA at alpha = 0.5, kept for continuity.
    assert r.deta == pytest.approx(0.7143, abs=1e-3)
    assert r.assa == pytest.approx(0.34, abs=1e-4)
    assert r.hota_at_05 == pytest.approx(0.4928, abs=1e-3)

    # `hota` is now the 19-alpha average (Eq. 16), which is strictly lower than
    # the single alpha=0.5 slice because loose matches drop out at high alpha.
    #
    # The by-construction IoUs (0.90, 0.80, 0.70, 0.85, 0.60) are exact-boundary
    # values for several of the 19 alpha thresholds. Before `_hota_multi_threshold`
    # compared `ious >= alpha` with an epsilon, float rounding in the box-area
    # arithmetic put an IoU that is conceptually exactly e.g. 0.90 at
    # 0.899999...94, which failed `>= 0.90` and silently dropped that alpha's
    # match — reported HOTA 0.392, hidden by this test's old ±0.03 tolerance.
    # With the epsilon this matches report 26 §6.4's hand-derived value tightly.
    assert r.hota < r.hota_at_05
    #
    # Superseded 2026-09-27 (M1 TrackEval parity): the reference TrackEval
    # compares at machine epsilon, so the 0.899999...94 IoU *does* fail the
    # alpha=0.90 threshold there and TrackEval reports 0.40047. We now match
    # the reference (tests/test_trackeval_parity.py) rather than the
    # exact-arithmetic hand derivation 0.4034.
    assert r.hota == pytest.approx(0.400468, abs=1e-5)


# ------------------------------------------------------------------ MTMC


def test_perfect_cross_camera_identity_has_no_handoff_gap() -> None:
    gt = _track("a", range(5), camera="cam_a") + _track("a", range(5), camera="cam_b")
    pred = _track(1, range(5), camera="cam_a") + _track(1, range(5), camera="cam_b")
    r = evaluate_mtmc(gt, pred)
    assert r["overall"]["idf1"] == pytest.approx(1.0)
    assert r["handoff_gap"] == pytest.approx(0.0, abs=1e-6)


def test_failing_the_handoff_looks_perfect_per_camera() -> None:
    """The exact failure MTMC exists to catch: great in each view, lost between them."""
    gt = _track("a", range(5), camera="cam_a") + _track("a", range(5), camera="cam_b")
    pred = _track(1, range(5), camera="cam_a") + _track(2, range(5), camera="cam_b")
    r = evaluate_mtmc(gt, pred)

    assert r["mean_single_camera_idf1"] == pytest.approx(1.0)
    assert r["overall"]["idf1"] < 0.75
    assert r["handoff_gap"] > 0.2


# ------------------------------------------------------------------ ReID


def test_reid_perfect_when_same_identity_is_most_similar() -> None:
    ids = np.array(["a", "a", "b", "b"])
    sim = np.array([
        [1.0, 0.9, 0.1, 0.1],
        [0.9, 1.0, 0.1, 0.1],
        [0.1, 0.1, 1.0, 0.9],
        [0.1, 0.1, 0.9, 1.0],
    ])
    r = evaluate_reid(ids, ids, sim, exclude=np.eye(4, dtype=bool))
    assert r.rank1 == pytest.approx(1.0)
    assert r.map_score > 0.99


def test_reid_chance_level_when_features_are_uninformative() -> None:
    ids = np.array(["a", "a", "b", "b"])
    sim = np.full((4, 4), 0.5)
    r = evaluate_reid(ids, ids, sim, exclude=np.eye(4, dtype=bool))
    assert r.rank1 < 1.0


def test_appearance_features_collapse_across_a_clothing_change() -> None:
    """The central result the simulator exists to measure.

    Two identities, two epochs each. Features encode *clothing*, so they cluster
    by outfit rather than by person: matching within an epoch is easy, matching
    across a change is worse than chance. Averaging the two would hide it.
    """
    # Two identities, two epochs each, two camera sightings per epoch so a
    # within-epoch match exists at all.
    uids = ["p1", "p1", "p1", "p1", "p2", "p2", "p2", "p2"]
    epochs = [0, 0, 1, 1, 0, 0, 1, 1]
    cameras = ["c1", "c2", "c1", "c2", "c1", "c2", "c1", "c2"]
    # The dominant axis is the coat colour; the small second component is the
    # person. Features are L2-normalised before matching, so identity has to be a
    # difference in *direction* — equal directions with different magnitudes would
    # collapse to the same unit vector and rank-1 would be a coin flip.
    feats = np.array([
        [1.0, 0.10], [1.0, 0.11],    # p1 epoch 0 - red coat
        [0.10, 1.0], [0.11, 1.0],    # p1 epoch 1 - swapped to blue
        [1.0, 0.40], [1.0, 0.41],    # p2 epoch 0 - also red
        [0.40, 1.0], [0.41, 1.0],    # p2 epoch 1 - also blue
    ])
    r = reid_by_epoch(feats, uids, epochs, cameras)

    # Within an epoch clothing colour is nearly sufficient; across the change it
    # points at the wrong person entirely.
    assert r["within_epoch"]["rank1"] > r["cross_epoch"]["rank1"]
    assert r["cross_epoch"]["rank1"] == pytest.approx(0.0)
    assert r["rank1_drop_across_appearance_change"] > 0.5


def test_shape_features_survive_a_clothing_change() -> None:
    """Height and build are what remain when clothing is unreliable."""
    uids = ["p1", "p1", "p2", "p2"]
    epochs = [0, 1, 0, 1]
    feats = np.array([
        [1.0, 0.0], [0.98, 0.0],     # p1 is tall in both epochs
        [0.0, 1.0], [0.0, 0.98],     # p2 is short in both
    ])
    r = reid_by_epoch(feats, uids, epochs)  # no camera constraint
    assert r["cross_epoch"]["rank1"] == pytest.approx(1.0)
    assert r["rank1_drop_across_appearance_change"] <= 0.0


def test_reid_handles_queries_with_no_valid_gallery_match() -> None:
    ids = np.array(["a", "b"])
    sim = np.array([[1.0, 0.2], [0.2, 1.0]])
    r = evaluate_reid(ids, ids, sim, exclude=np.eye(2, dtype=bool))
    assert r.n_queries == 0          # neither identity has a second instance


# --------------------------------------------------------- doc-count drift

