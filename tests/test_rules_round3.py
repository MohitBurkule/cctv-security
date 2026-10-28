"""Round 3 (docs/research/58 §7): GBM rule and zone-function context features."""
from __future__ import annotations

import numpy as np
from test_rules_redesign import ZONES, _track, pacer, walker

from cctvsec.eval.loiter_features import (
    CONTEXT_FEATURES,
    FEATURES,
    add_context,
    world_feature_table,
    zone_function,
)
from cctvsec.eval.rules import GBMLoiterRule


class _Const:
    """Stand-in classifier: p = the named column (keeps the test sklearn-free)."""

    def __init__(self, j):
        self.j = j

    def predict_proba(self, X):
        p = np.clip(X[:, self.j], 0, 1)
        return np.column_stack([1 - p, p])


def test_zone_function_strips_suffix_and_handles_missing():
    assert zone_function("zone.entrance_2") == "entrance"
    assert zone_function("zone.fence_line") == "fence_line"
    assert zone_function("zone.restricted_0") == "restricted"
    assert zone_function(None) == "none" and zone_function("nan") == "none"
    assert zone_function("zone.mystery") == "none"


def test_context_is_one_hot_and_not_a_track_feature():
    tab = add_context(world_feature_table(_track("a", pacer(), zone="zone.platform"), ZONES))
    m = tab[list(CONTEXT_FEATURES)].to_numpy()
    assert (m.sum(1) == 1).all() and (tab["zf_platform"] == 1).all()
    # context needs a site profile: it must never leak into the track-only set
    assert not set(CONTEXT_FEATURES) & set(FEATURES)


def test_gbm_rule_fires_once_per_episode_and_respects_clock():
    tab = world_feature_table(_track("a", pacer()), ZONES)
    feats = ("moving30",)
    r = GBMLoiterRule(model=_Const(0), features=feats, theta=0.5, min_clock_s=5)
    assert len(r.fire(tab)) == 1
    assert GBMLoiterRule(model=_Const(0), features=feats, theta=0.5, min_clock_s=10**6).fire(tab) == []
    # a straight walker has a clock that never builds
    assert GBMLoiterRule(model=_Const(0), features=feats, theta=0.0, min_clock_s=5).fire(
        world_feature_table(_track("w", walker()), ZONES)) == []


def test_gbm_rule_adds_context_on_demand_and_applies_calibrator():
    tab = world_feature_table(_track("a", pacer(), zone="zone.platform"), ZONES)

    class Flip:
        def predict(self, p):
            return 1 - p

    r = GBMLoiterRule(model=_Const(1), features=("clock", "zf_platform"), theta=0.5, min_clock_s=5)
    assert len(r.fire(tab)) == 1 and "zf_platform" not in tab
    r.calibrator = Flip()
    assert r.fire(tab) == []
