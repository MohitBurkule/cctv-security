"""Tests for the learned behaviour classifier.

The properties that make the result trustworthy rather than merely high: the
features must capture the right geometry, the split must not leak identities, the
model must beat the dwell rule it is meant to replace, and it must be measured on
the hard negatives that a dwell rule cannot separate.
"""

from __future__ import annotations

import numpy as np
import pytest

from cctvsec.eval.behaviour import (
    FEATURE_NAMES,
    BehaviourClassifier,
    Segment,
    compare_with_dwell_rule,
    evaluate_classifier,
    extract_features,
    split_by_identity,
)


def _walk(uid="w", n=40, label="normal.transit") -> Segment:
    """A straight crossing at a steady pace."""
    xy = np.stack([np.linspace(0, 40, n), np.zeros(n)], axis=1)
    return Segment(uid=uid, label=label, t_start=0.0, t_end=float(n),
                   xy=xy, speeds=np.full(n, 1.3), zones=["zone.open"] * n)


def _pace(uid="p", n=40, label="suspicious.loiter.pace") -> Segment:
    """Pacing back and forth inside a small area — a loiterer."""
    t = np.linspace(0, 4 * np.pi, n)
    xy = np.stack([np.sin(t) * 3.0, np.cos(t) * 2.0], axis=1)
    return Segment(uid=uid, label=label, t_start=0.0, t_end=float(n),
                   xy=xy, speeds=np.full(n, 0.45), zones=["zone.gate"] * n)


def _wait(uid="q", n=40) -> Segment:
    """Standing still for the same duration — the innocent look-alike."""
    xy = np.tile(np.array([5.0, 5.0]), (n, 1)) + np.random.default_rng(0).normal(0, 0.05, (n, 2))
    return Segment(uid=uid, label="normal.commute_wait", t_start=0.0, t_end=float(n),
                   xy=xy, speeds=np.full(n, 0.05), zones=["zone.gate"] * n,
                   hard_negative=True)


# ------------------------------------------------------------------ features


def test_feature_vector_has_the_declared_length() -> None:
    assert len(extract_features(_walk())) == len(FEATURE_NAMES)


def test_tortuosity_separates_pacing_from_crossing() -> None:
    """A straight crossing is ~1; pacing in a loop is much larger."""
    walk = extract_features(_walk())[FEATURE_NAMES.index("path_tortuosity")]
    pace = extract_features(_pace())[FEATURE_NAMES.index("path_tortuosity")]
    assert walk < 1.5
    assert pace > walk * 3


def test_dwell_fraction_is_high_for_someone_standing_still() -> None:
    idx = FEATURE_NAMES.index("dwell_fraction")
    assert extract_features(_wait())[idx] > 0.9
    assert extract_features(_walk())[idx] < 0.1


def test_radius_of_gyration_distinguishes_clustered_from_spread_tracks() -> None:
    idx = FEATURE_NAMES.index("radius_of_gyration")
    assert extract_features(_wait())[idx] < extract_features(_walk())[idx]


def test_degenerate_segment_does_not_crash() -> None:
    seg = Segment("x", "normal", 0.0, 0.0, np.zeros((1, 2)), np.zeros(1))
    assert extract_features(seg).shape == (len(FEATURE_NAMES),)


# --------------------------------------------------------------------- split


def test_split_never_puts_one_identity_in_both_halves() -> None:
    """Splitting by segment lets the model memorise people and inflates every score."""
    segs = [_walk(uid=f"u{i}") for i in range(10)] + [_pace(uid=f"u{i}") for i in range(10)]
    train, test = split_by_identity(segs, test_fraction=0.3, seed=1)

    assert train and test
    assert not ({s.uid for s in train} & {s.uid for s in test})


def test_split_is_deterministic() -> None:
    segs = [_walk(uid=f"u{i}") for i in range(12)]
    a = split_by_identity(segs, seed=5)[1]
    b = split_by_identity(segs, seed=5)[1]
    assert [s.uid for s in a] == [s.uid for s in b]


# ---------------------------------------------------------------- classifier


def _dataset(n: int = 24):
    segs = []
    for i in range(n):
        segs.append(_walk(uid=f"walk{i}"))
        segs.append(_wait(uid=f"wait{i}"))
        segs.append(_pace(uid=f"pace{i}"))
    return segs


def test_classifier_learns_to_separate_pacing_from_normal_behaviour() -> None:
    segs = _dataset()
    train, test = split_by_identity(segs, test_fraction=0.3, seed=2)
    x = np.stack([extract_features(s) for s in train])
    y = np.array([s.is_suspicious for s in train], dtype=float)

    model = BehaviourClassifier().fit(x, y)
    result = evaluate_classifier(model, test, camera_hours=1.0)

    assert result["auc"] > 0.9
    assert result["recall"] > 0.7


def test_classifier_beats_the_dwell_rule_on_hard_negatives() -> None:
    """The point of the exercise.

    The waiting commuter and the pacing loiterer both occupy the gate for the same
    time, so a dwell rule fires on both. Trajectory shape separates them.
    """
    segs = _dataset()
    train, test = split_by_identity(segs, test_fraction=0.35, seed=3)
    x = np.stack([extract_features(s) for s in train])
    y = np.array([s.is_suspicious for s in train], dtype=float)
    model = BehaviourClassifier().fit(x, y)

    learned = evaluate_classifier(model, test)
    rule = compare_with_dwell_rule(test, dwell_threshold_s=25.0)

    assert rule["precision"] < 0.75          # the rule cannot tell them apart
    assert learned["precision"] > rule["precision"]
    assert learned["hard_negative_false_alarm_rate"] is not None


def test_feature_importance_is_readable() -> None:
    segs = _dataset()
    x = np.stack([extract_features(s) for s in segs])
    y = np.array([s.is_suspicious for s in segs], dtype=float)
    model = BehaviourClassifier().fit(x, y)

    importance = model.importance()
    assert set(importance) == set(FEATURE_NAMES)
    # Trajectory shape should matter more than raw duration, which is what the
    # dwell rule already uses and cannot separate on.
    assert abs(importance["path_tortuosity"]) > abs(importance["duration_s"])


def test_unfitted_classifier_refuses_to_predict() -> None:
    with pytest.raises(RuntimeError, match="not fitted"):
        BehaviourClassifier().predict_proba(np.zeros((1, len(FEATURE_NAMES))))


def test_rare_positives_do_not_collapse_to_predicting_normal() -> None:
    """Without class weighting the model would simply answer 'normal' every time."""
    segs = [_walk(uid=f"w{i}") for i in range(40)] + [_pace(uid=f"p{i}") for i in range(4)]
    x = np.stack([extract_features(s) for s in segs])
    y = np.array([s.is_suspicious for s in segs], dtype=float)
    model = BehaviourClassifier().fit(x, y)
    assert (model.predict_proba(x) >= 0.5).sum() > 0


def test_false_alarm_rate_is_reported_per_camera_hour() -> None:
    segs = _dataset(6)
    x = np.stack([extract_features(s) for s in segs])
    y = np.array([s.is_suspicious for s in segs], dtype=float)
    model = BehaviourClassifier().fit(x, y)

    result = evaluate_classifier(model, segs, camera_hours=0.5)
    assert result["false_alarms_per_camera_hour"] == pytest.approx(
        result["false_alarms"] / 0.5)
