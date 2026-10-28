"""Loiter rule redesign (docs/research/58): displacement clock, revisit rule,
zone semantics, and that batch firing equals `run`."""
from __future__ import annotations

import numpy as np
import pandas as pd

from cctvsec.eval.loiter_features import first_per_episode, revisits, world_feature_table
from cctvsec.eval.rules import (
    DisplacementLoiterRule,
    LearnedLoiterRule,
    PathLoiterRule,
    RevisitRule,
    ZoneDwellRule,
)

ZONES = [{"id": "zone.entrance_0", "tag": "gate", "polygon": [], "allowed_roles": ["guard"]},
         {"id": "zone.platform", "tag": "queue", "polygon": [], "allowed_roles": []}]


def _track(uid, xy, zone="zone.entrance_0", fps=5.0):
    xy = np.asarray(xy, float)
    t = np.arange(1, len(xy) + 1) / fps
    v = np.r_[0.0, np.hypot(*np.diff(xy, axis=0).T) * fps]
    return pd.DataFrame({"t": t, "uid": uid, "x": xy[:, 0], "y": xy[:, 1], "speed": v, "zone": zone})


def walker(n=600, v=1.3, fps=5.0):
    return np.column_stack([np.arange(n) * v / fps, np.zeros(n)])


def stander(n=600):
    return np.zeros((n, 2))


def pacer(n=600, half=1.5, v=0.45, fps=5.0):
    s = (np.arange(n) * v / fps) % (4 * half)
    x = np.where(s < 2 * half, s - half, 3 * half - s)
    return np.column_stack([x, np.zeros(n)])


def test_path_loiter_15_fires_on_a_straight_walker_the_h12_bug():
    # Documents why the rule was redesigned: its clock only resets after
    # reentry_gap_s of continuous movement, so threshold <= gap fires on transit.
    a = PathLoiterRule(threshold_s=15, radius_m=4, reentry_gap_s=15).run(_track("w", walker()), ZONES)
    assert len(a) >= 1


def test_displacement_clock_never_fires_on_a_walker():
    assert DisplacementLoiterRule(threshold_s=10).run(_track("w", walker()), ZONES) == []


def test_displacement_rule_fires_once_on_a_pacer_and_band_rejects_a_stander():
    rule = DisplacementLoiterRule(threshold_s=20, stat_hi=0.5)
    assert len(rule.run(_track("p", pacer()), ZONES)) == 1
    assert rule.run(_track("s", stander()), ZONES) == []
    assert len(DisplacementLoiterRule(threshold_s=20).run(_track("s", stander()), ZONES)) == 1


def test_clock_restarts_after_moving_on():
    xy = np.r_[stander(300), walker(100) + [0, 0], stander(300) + [26, 0]]
    a = DisplacementLoiterRule(threshold_s=20).run(_track("s", xy), ZONES)
    assert len(a) == 2 and a[1].t > 80


def test_zone_gate_and_allowed_role():
    rule = DisplacementLoiterRule(threshold_s=20, zone_tags=("gate",))
    assert rule.run(_track("p", pacer(), zone="zone.platform"), ZONES) == []
    assert len(rule.run(_track("p", pacer()), ZONES)) == 1
    assert rule.run(_track("p", pacer()), ZONES, {"p": "guard"}) == []


def test_revisit_counts_oscillation_not_standing_or_walking():
    t = np.arange(120.0)
    x = 1.5 * np.sign(np.sin(2 * np.pi * t / 12))
    assert revisits(t, x, np.zeros_like(t)).max() >= 3
    assert revisits(t, np.zeros_like(t), np.zeros_like(t)).max() == 0
    assert revisits(t, t * 1.3, np.zeros_like(t)).max() == 0
    rule = RevisitRule(min_revisits=2)
    assert len(rule.run(_track("p", pacer()), ZONES)) == 1
    assert rule.run(_track("s", stander()), ZONES) == []


def test_zone_dwell_rule_exempts_wait_zones_and_roles():
    stand = _track("s", stander())
    assert len(ZoneDwellRule(threshold_s=25, exempt_tags=()).run(stand, ZONES)) == 1
    assert ZoneDwellRule(threshold_s=25, exempt_zone_ids=("zone.entrance_0",)).run(stand, ZONES) == []
    assert ZoneDwellRule(threshold_s=25).run(stand, ZONES, {"s": "guard"}) == []


def test_batch_fire_on_concatenated_table_equals_run():
    df = pd.concat([_track("a", pacer()), _track("b", stander()), _track("c", walker())])
    rule = DisplacementLoiterRule(threshold_s=15)
    tab = world_feature_table(df, ZONES)
    assert sorted(rule.fire(tab)) == [a.t for a in rule.run(df, ZONES)]
    cond = rule.condition(tab) & ~tab["allowed"].to_numpy(bool)
    idx = first_per_episode(cond, pd.factorize(tab["ep"])[0])
    assert sorted(tab["t"].to_numpy()[idx]) == sorted(rule.fire(tab))


def test_features_never_read_behaviour_labels():
    df = _track("a", pacer())
    tab0 = world_feature_table(df, ZONES)
    tab1 = world_feature_table(df.assign(label="suspicious.loiter.pace"), ZONES)
    pd.testing.assert_frame_equal(tab0, tab1)


def test_learned_rule_scores_and_gates():
    tab = world_feature_table(_track("a", pacer()), ZONES)
    r = LearnedLoiterRule(weights=(1.0,), bias=0.0, mean=(0.0,), std=(1.0,), features=("moving30",),
                          theta=0.6, min_clock_s=5)
    assert len(r.fire(tab)) == 1
    r.gate = DisplacementLoiterRule(threshold_s=10**6)
    assert r.fire(tab) == []
