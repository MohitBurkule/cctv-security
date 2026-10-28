"""Every loiter/object rule must say *who* its alarm is about (Alarm.uid), so
`alarms.score(actor_aware=True)` can credit two overlapping same-label events
to the right people (docs/research/58 §4, round 2)."""
from __future__ import annotations

import pandas as pd
from test_rules_redesign import ZONES, _track, pacer, stander, walker

from cctvsec.eval.alarms import Alarm, TruthEvent, score
from cctvsec.eval.rules import (
    AbandonedObjectRule,
    AllOfRule,
    DisplacementLoiterRule,
    DwellRule,
    LearnedLoiterRule,
    PathLoiterRule,
    RevisitRule,
    ZoneDwellRule,
)


def _world():
    return pd.concat([_track("walker", walker()), _track("pacer", pacer()),
                      _track("stander", stander() + 50.0)], ignore_index=True)


def _check(alarms, allowed):
    assert alarms, "rule produced no alarms on the fixture"
    for a in alarms:
        assert isinstance(a, Alarm) and a.uid in allowed


def test_dwell_and_zone_dwell_emit_uid():
    df = _world()
    tags = {z["id"]: z["tag"] for z in ZONES}
    _check(DwellRule(threshold_s=20, speed_cap_mps=0.6).run(df, tags), {"pacer", "stander"})
    _check(ZoneDwellRule(threshold_s=20, speed_cap_mps=0.6).run(df, ZONES, {}), {"pacer", "stander"})


def test_path_loiter_emits_uid():
    # PathLoiterRule also fires on the walker (its documented transit bug,
    # docs/research/58 §4); the uid must still name whoever it fired on.
    out = PathLoiterRule(threshold_s=20).run(_world(), ZONES, {})
    _check(out, {"walker", "pacer", "stander"})
    assert {"pacer", "stander"} <= {a.uid for a in out}


def test_tick_rules_emit_uid():
    df = _world()
    _check(DisplacementLoiterRule(threshold_s=15).run(df, ZONES, {}), {"pacer", "stander"})
    _check(RevisitRule(min_revisits=1, min_clock_s=5).run(df, ZONES, {}), {"pacer"})
    _check(AllOfRule(rules=(DisplacementLoiterRule(threshold_s=15),)).run(df, ZONES, {}),
           {"pacer", "stander"})
    from cctvsec.eval.loiter_features import FEATURES
    n = len(FEATURES)
    learned = LearnedLoiterRule(weights=(0.0,) * n, bias=5.0, mean=(0.0,) * n, std=(1.0,) * n,
                                features=tuple(FEATURES), theta=0.5, min_clock_s=5)
    _check(learned.run(df, ZONES, {}), {"walker", "pacer", "stander"})


def test_abandoned_object_emits_owner():
    df = _track("owner", walker())
    out = AbandonedObjectRule().run({"bag": {"owner": "owner", "pos": [0.0, 0.0], "t_drop": 0.0}}, df)
    _check(out, {"owner"})


def test_uid_lifts_overlapping_event_recall():
    lab = "suspicious.loiter"
    truth = [TruthEvent(0.0, 60.0, lab, ("a",)), TruthEvent(5.0, 60.0, lab, ("b",))]
    alarms = [Alarm(t=10.0, label=lab, uid="b"), Alarm(t=12.0, label=lab, uid="a")]
    # actor_aware=False forces the old window-only number explicitly -- since
    # round 2, the bare default (actor_aware=None) auto-resolves to True here
    # because both alarms carry a uid, and would give true_positives == 2.
    assert score(truth, alarms, camera_hours=1.0, tolerance_s=30, actor_aware=False).true_positives == 1
    assert score(truth, alarms, camera_hours=1.0, tolerance_s=30, actor_aware=True).true_positives == 2
