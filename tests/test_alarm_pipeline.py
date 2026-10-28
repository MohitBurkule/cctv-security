"""Tests for the alarm architecture.

Each stage exists to trade recall for precision in a specific way, and the tests
pin both halves of that trade — a stage that only ever improved precision without
costing recall would be suspicious, not impressive.
"""

from __future__ import annotations

import pytest

from cctvsec.eval.alarms import TruthEvent
from cctvsec.eval.pipeline import AlarmPipeline, Candidate, compare_architectures


def _c(t, uid="p0", conf=0.9, zone="zone.gate", label="suspicious.loiter", **kw):
    return Candidate(t=t, uid=uid, label=label, confidence=conf, zone=zone, **kw)


# ---------------------------------------------------------------- thresholds


def test_threshold_drops_low_confidence_candidates() -> None:
    pipe = AlarmPipeline(threshold=0.8, persistence_windows=1)
    alarms, stages = pipe.run([_c(10, conf=0.9), _c(20, uid="p1", conf=0.3)], camera_hours=1)
    assert len(alarms) == 1
    assert stages[0].name == "threshold" and stages[0].dropped == 1


# --------------------------------------------------------------- persistence


def test_persistence_removes_one_off_misclassifications() -> None:
    """A real dwell event is still there later; a glitch is not."""
    pipe = AlarmPipeline(threshold=0.5, persistence_windows=2, persistence_span_s=60)
    candidates = [
        _c(10, uid="real"), _c(30, uid="real"),      # persists
        _c(15, uid="glitch"),                        # single sighting
    ]
    alarms, _ = pipe.run(candidates, camera_hours=1)
    assert len(alarms) == 1


def test_persistence_respects_its_time_window() -> None:
    """Two sightings an hour apart are not one persistent event."""
    pipe = AlarmPipeline(persistence_windows=2, persistence_span_s=30)
    alarms, _ = pipe.run([_c(10), _c(3600)], camera_hours=1)
    assert alarms == []


# ------------------------------------------------------------------- context


def test_zone_context_suppresses_uninteresting_places() -> None:
    pipe = AlarmPipeline(persistence_windows=1, priority_zones=("zone.restricted",))
    alarms, _ = pipe.run([_c(10, zone="zone.concourse"),
                          _c(20, uid="p1", zone="zone.restricted")], camera_hours=1)
    assert len(alarms) == 1


def test_after_hours_filter_uses_the_clock() -> None:
    """Presence in a closed site is itself informative."""
    pipe = AlarmPipeline(persistence_windows=1, after_hours=(22.0, 6.0))
    hour = lambda t: t / 3600.0
    alarms, _ = pipe.run([_c(23 * 3600, uid="night"), _c(13 * 3600, uid="noon")],
                         camera_hours=1, hour_of_day=hour)
    assert len(alarms) == 1


# ------------------------------------------------------------- corroboration


def test_corroboration_requires_a_second_channel() -> None:
    pipe = AlarmPipeline(persistence_windows=1, require_corroboration=True)
    alarms, _ = pipe.run([
        _c(10, uid="alone"),
        _c(20, uid="backed", corroborating={"rf": 0.8}),
    ], camera_hours=1)
    assert len(alarms) == 1


def test_weak_corroboration_does_not_count() -> None:
    pipe = AlarmPipeline(persistence_windows=1, require_corroboration=True,
                         corroboration_min=0.7)
    alarms, _ = pipe.run([_c(10, corroborating={"rf": 0.2})], camera_hours=1)
    assert alarms == []


# ------------------------------------------------------------ deduplication


def test_one_event_produces_one_alarm() -> None:
    """A stream of alarms for one loiterer is what makes operators stop looking."""
    pipe = AlarmPipeline(persistence_windows=1)
    alarms, _ = pipe.run([_c(t) for t in range(0, 60, 5)], camera_hours=1)
    assert len(alarms) == 1


def test_separate_events_are_not_merged() -> None:
    pipe = AlarmPipeline(persistence_windows=1)
    alarms, _ = pipe.run([_c(10), _c(900)], camera_hours=1)
    assert len(alarms) == 2


# ------------------------------------------------------------------- budget


def test_operator_budget_caps_the_stream_and_keeps_the_best() -> None:
    """Capacity sets the operating point, not the model."""
    pipe = AlarmPipeline(persistence_windows=1, max_alarms_per_camera_hour=2.0)
    candidates = [_c(t * 100, uid=f"p{t}", conf=0.5 + t * 0.05) for t in range(8)]
    alarms, stages = pipe.run(candidates, camera_hours=1.0)

    assert len(alarms) == 2
    assert any(s.name == "operator_budget" for s in stages)


def test_budget_is_not_applied_when_under_capacity() -> None:
    pipe = AlarmPipeline(persistence_windows=1, max_alarms_per_camera_hour=10.0)
    alarms, stages = pipe.run([_c(10), _c(900, uid="p1")], camera_hours=1.0)
    assert len(alarms) == 2
    assert not any(s.name == "operator_budget" for s in stages)


# -------------------------------------------------------------- architecture


def test_verification_chain_beats_the_raw_detector_on_precision() -> None:
    """The headline argument: same model, very different operator experience.

    One real loiterer persisting, plus a scatter of spurious one-off detections —
    the shape of output a 7%-precision classifier actually produces.
    """
    truth = [TruthEvent(t_start=100.0, t_end=200.0, label="suspicious.loiter")]
    candidates = (
        [_c(100 + i * 10, uid="real", conf=0.85, corroborating={"rf": 0.9})
         for i in range(6)]
        + [_c(300 + i * 137, uid=f"noise{i}", conf=0.55) for i in range(12)]
    )

    results = compare_architectures(
        candidates, truth, camera_hours=1.0,
        variants={
            "raw": AlarmPipeline(threshold=0.5, persistence_windows=1),
            "verified": AlarmPipeline(threshold=0.7, persistence_windows=2,
                                      persistence_span_s=60, require_corroboration=True),
        })

    assert results["raw"]["precision"] < results["verified"]["precision"]
    assert results["verified"]["precision"] == pytest.approx(1.0)
    assert (results["verified"]["false_alarms_per_camera_hour"]
            < results["raw"]["false_alarms_per_camera_hour"])


def test_the_trade_is_visible_not_hidden() -> None:
    """Every stage must report what it dropped, so the cost in recall is explicit."""
    truth = [TruthEvent(t_start=100.0, t_end=200.0, label="suspicious.loiter")]
    candidates = [_c(105, uid="real", conf=0.6)]

    results = compare_architectures(
        candidates, truth, camera_hours=1.0,
        variants={"strict": AlarmPipeline(threshold=0.95, persistence_windows=1)})

    strict = results["strict"]
    assert strict["recall"] == 0.0            # the trade genuinely costs detections
    assert strict["stages"][0]["dropped"] == 1
    assert "trades recall" in strict["stages"][0]["rationale"]
