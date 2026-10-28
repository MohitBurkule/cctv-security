"""Tests for `alarms.score(position_radius_m=...)` -- the H62 position/time
scoring mode (docs/research/32 H62, from AUDIT_TAILGATER_RECONCILIATION).

Unlike `actor_aware`, this mode never reads `Alarm.uid` / `TruthEvent.actors`:
a hit requires only that the alarm lands in the i-LIDS window AND that its
`pos` is within `position_radius_m` of the true actor's `actor_pos`. It is
therefore immune to a tracker relabelling which uid a spatially-unchanged
alarm carries -- the case H59 showed collapses `actor_aware` recall.
"""
from cctvsec.eval.alarms import Alarm, TruthEvent, score

EVENT = TruthEvent(
    t_start=100.0,
    t_end=110.0,
    label="suspicious.loiter",
    actors=("p001",),
    actor_pos={"p001": (10.0, 0.0)},
)


def test_swapped_label_correct_position_is_a_hit():
    """The alarm's uid is swapped to a bystander's, but its estimated position
    still tracks the true offending actor -- position_time credits it; the
    actor-aware default does not (this is exactly H59's collapse)."""
    alarm = Alarm(t=105.0, label="suspicious.loiter", uid="p002", pos=(10.2, 0.1))
    result = score(
        [EVENT], [alarm], camera_hours=1.0, tolerance_s=10.0,
        actor_aware=True, position_radius_m=2.0,
    )
    assert result.true_positives == 0  # actor-aware: uid p002 not in actors -> miss
    assert result.position_time_recall == 1.0


def test_correct_label_wrong_position_is_a_miss():
    """The alarm's uid is correct (actor-aware would credit it) but its
    estimated position is nowhere near the true actor -- e.g. a stale or
    mis-associated track -- so position_time must not credit it."""
    alarm = Alarm(t=105.0, label="suspicious.loiter", uid="p001", pos=(500.0, 500.0))
    result = score(
        [EVENT], [alarm], camera_hours=1.0, tolerance_s=10.0,
        actor_aware=True, position_radius_m=2.0,
    )
    assert result.true_positives == 1  # actor-aware: uid matches -> hit
    assert result.position_time_recall == 0.0


def test_radius_boundary():
    just_in = Alarm(t=105.0, label="suspicious.loiter", pos=(11.9, 0.0))
    just_out = Alarm(t=105.0, label="suspicious.loiter", pos=(12.1, 0.0))
    r_in = score([EVENT], [just_in], camera_hours=1.0, tolerance_s=10.0, position_radius_m=2.0)
    r_out = score([EVENT], [just_out], camera_hours=1.0, tolerance_s=10.0, position_radius_m=2.0)
    assert r_in.position_time_recall == 1.0
    assert r_out.position_time_recall == 0.0


def test_missing_position_degrades_gracefully_not_a_crash():
    alarm = Alarm(t=105.0, label="suspicious.loiter", uid="p001")  # no pos
    result = score(
        [EVENT], [alarm], camera_hours=1.0, tolerance_s=10.0, position_radius_m=2.0
    )
    assert result.position_time_recall == 0.0


def test_bystander_within_radius_flags_false_credit():
    ev = TruthEvent(
        t_start=100.0, t_end=110.0, label="suspicious.loiter", actors=("p001",),
        actor_pos={"p001": (10.0, 0.0)}, bystander_pos={"p003": (10.5, 0.0)},
    )
    alarm = Alarm(t=105.0, label="suspicious.loiter", pos=(10.2, 0.0))
    result = score([ev], [alarm], camera_hours=1.0, tolerance_s=10.0, position_radius_m=2.0)
    assert result.position_time_recall == 1.0
    assert result.position_time_false_credit_rate == 1.0


def test_no_bystander_data_leaves_false_credit_rate_none():
    alarm = Alarm(t=105.0, label="suspicious.loiter", pos=(10.2, 0.0))
    result = score([EVENT], [alarm], camera_hours=1.0, tolerance_s=10.0, position_radius_m=2.0)
    assert result.position_time_recall == 1.0
    assert result.position_time_false_credit_rate is None


def test_position_time_never_perturbs_default_scoring():
    """Passing position_radius_m must not change true_positives/recall/etc.
    when a caller does not read the new fields."""
    alarm = Alarm(t=105.0, label="suspicious.loiter", uid="p001", pos=(10.0, 0.0))
    without = score([EVENT], [alarm], camera_hours=1.0, tolerance_s=10.0, actor_aware=True)
    with_pt = score(
        [EVENT], [alarm], camera_hours=1.0, tolerance_s=10.0, actor_aware=True,
        position_radius_m=2.0,
    )
    assert without.true_positives == with_pt.true_positives
    assert without.recall == with_pt.recall
    assert without.false_positives == with_pt.false_positives
