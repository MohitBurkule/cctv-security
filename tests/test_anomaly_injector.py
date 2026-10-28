"""Tests for rate-controlled anomaly injection.

The point of the injector is that the base rate becomes a stated parameter rather
than an accident of how many incidents the scenario author typed. These tests pin
that the rate is honoured, that rarity is preserved rather than quietly inflated,
and that hard negatives scale alongside the positives.
"""

from __future__ import annotations

import itertools

import pytest

from survsim.core.models import BehaviourSpec, Person
from survsim.director.anomaly import (
    INJECTABLE,
    AnomalyInjector,
    apply_to_people,
)


def _uids(n: int) -> list[str]:
    return [f"p{i:02d}" for i in range(n)]


def _points() -> dict[str, list[str]]:
    return {
        "zones": ["zone.gate", "zone.open"],
        "restricted": ["zone.restricted"],
        "exits": ["exit.a", "exit.b"],
        "cameras": ["cam_00", "cam_01"],
    }


# ------------------------------------------------------------------- rate


def test_event_count_tracks_the_requested_rate() -> None:
    """Ten times the rate should give roughly ten times the events."""
    low = AnomalyInjector(rate_per_camera_hour=0.5, seed=1).schedule(
        duration_s=3600, n_cameras=4, available_uids=_uids(200))[0]
    high = AnomalyInjector(rate_per_camera_hour=5.0, seed=1).schedule(
        duration_s=3600, n_cameras=4, available_uids=_uids(200))[0]

    low_real = [e for e in low if not e.is_benign_twin]
    high_real = [e for e in high if not e.is_benign_twin]
    assert len(high_real) > len(low_real) * 3


def test_report_states_the_denominator() -> None:
    """Precision means nothing without the camera-hours it was measured over."""
    _, report = AnomalyInjector(rate_per_camera_hour=1.0, seed=2).schedule(
        duration_s=1800, n_cameras=6, available_uids=_uids(100))
    assert report["camera_hours"] == pytest.approx(3.0)
    assert report["expected_events"] == pytest.approx(3.0, abs=0.01)


def test_rarity_is_preserved_rather_than_inflated() -> None:
    """A short scenario at a realistic rate should contain nothing, and say so.

    Bumping the rate to avoid an empty run would destroy the only number that
    makes a precision figure interpretable.
    """
    events, report = AnomalyInjector(rate_per_camera_hour=0.01, seed=3).schedule(
        duration_s=60, n_cameras=1, available_uids=_uids(50))

    assert [e for e in events if not e.is_benign_twin] == []
    assert "fewer than one event" in report["note"]


def test_events_are_separated_in_time() -> None:
    """Incidents landing on top of each other stop being rare events."""
    events, _ = AnomalyInjector(rate_per_camera_hour=40.0, seed=4,
                                min_separation_s=30.0).schedule(
        duration_s=600, n_cameras=8, available_uids=_uids(300))
    times = sorted(e.t for e in events if not e.is_benign_twin)
    assert all(b - a >= 30.0 for a, b in itertools.pairwise(times))


def test_scheduling_is_deterministic() -> None:
    a = AnomalyInjector(rate_per_camera_hour=2.0, seed=7).schedule(
        1800, 4, _uids(100))[0]
    b = AnomalyInjector(rate_per_camera_hour=2.0, seed=7).schedule(
        1800, 4, _uids(100))[0]
    assert [(e.t, e.kind) for e in a] == [(e.t, e.kind) for e in b]


# --------------------------------------------------------- hard negatives


def test_hard_negatives_scale_with_positives() -> None:
    events, report = AnomalyInjector(rate_per_camera_hour=3.0, seed=5,
                                     hard_negative_ratio=3.0).schedule(
        duration_s=3600, n_cameras=4, available_uids=_uids(300))

    positives = [e for e in events if not e.is_benign_twin]
    twins = [e for e in events if e.is_benign_twin]
    assert positives and twins
    assert len(twins) >= len(positives) * 2
    assert report["hard_negatives"] == len(twins)


def test_each_injectable_event_declares_a_benign_look_alike() -> None:
    """An event with no innocent counterpart cannot be scored for precision."""
    for kind, spec in INJECTABLE.items():
        assert spec["benign_twin"], kind
        assert 0.0 <= spec["severity"] <= 1.0


def test_actors_are_not_double_booked() -> None:
    """One person cannot be in two incidents at once."""
    events, _ = AnomalyInjector(rate_per_camera_hour=20.0, seed=6).schedule(
        duration_s=3600, n_cameras=4, available_uids=_uids(60))
    used = [uid for e in events for uid in e.actors]
    assert len(used) == len(set(used))


# ------------------------------------------------------------- application


def test_events_are_spliced_into_intent_timelines() -> None:
    people = {uid: Person(id=uid, intent=[
        BehaviourSpec(type="transit", to="exit.a")]) for uid in _uids(40)}
    events, _ = AnomalyInjector(rate_per_camera_hour=8.0, seed=8).schedule(
        duration_s=3600, n_cameras=4, available_uids=list(people))

    applied = apply_to_people(events, people, _points(), seed=1)
    assert applied > 0
    changed = [p for p in people.values() if len(p.intent) > 1]
    assert changed


def test_actors_still_leave_the_scene_afterwards() -> None:
    """An injected incident must not strand someone mid-scenario."""
    people = {uid: Person(id=uid, intent=[
        BehaviourSpec(type="transit", to="exit.a")]) for uid in _uids(30)}
    events, _ = AnomalyInjector(rate_per_camera_hour=8.0, seed=9).schedule(
        duration_s=3600, n_cameras=4, available_uids=list(people))
    apply_to_people(events, people, _points(), seed=2)

    for person in people.values():
        if len(person.intent) > 1:
            assert person.intent[-1].type == "transit"


def test_benign_twins_are_marked_as_hard_negatives() -> None:
    people = {uid: Person(id=uid, intent=[
        BehaviourSpec(type="transit", to="exit.a")]) for uid in _uids(40)}
    events, _ = AnomalyInjector(rate_per_camera_hour=8.0, seed=10).schedule(
        duration_s=3600, n_cameras=4, available_uids=list(people))
    apply_to_people(events, people, _points(), seed=3)

    twin_uids = {uid for e in events if e.is_benign_twin for uid in e.actors}
    marked = [uid for uid in twin_uids if people[uid].hard_negative_for]
    assert marked, "innocent look-alikes must be labelled so precision is measurable"


def test_camera_tamper_is_skipped_when_no_cameras_are_known() -> None:
    """Better to schedule nothing than to emit a step referencing a missing camera."""
    people = {uid: Person(id=uid, intent=[BehaviourSpec(type="transit", to="exit.a")])
              for uid in _uids(20)}
    injector = AnomalyInjector(rate_per_camera_hour=30.0, seed=11,
                               allowed=("camera_tamper",))
    events, _ = injector.schedule(3600, 4, list(people))
    points = {**_points(), "cameras": []}

    apply_to_people(events, people, points, seed=4)
    for person in people.values():
        assert all(s.type != "camera_tamper" for s in person.intent)
