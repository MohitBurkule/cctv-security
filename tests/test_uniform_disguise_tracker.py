import numpy as np
import pandas as pd

from cctvsec.experiments import uniform_disguise_tracker as T


def test_guard_keep_rules():
    k = T.guard_keep(False, [], 100.0, 30.0)
    assert k == {"C": True, "a": False, "b": True, "s": True, "g": True}
    assert not T.guard_keep(True, [], 100.0, 30.0)["b"]
    old = T.guard_keep(False, [10.0], 100.0, 30.0)  # stale history: sticky suppresses, grace keeps
    assert old["b"] and not old["s"] and old["g"]
    new = T.guard_keep(False, [90.0], 100.0, 30.0)
    assert not new["s"] and not new["g"]
    assert T.guard_keep(False, [150.0], 100.0, 30.0)["s"]  # future corroboration is not history


def test_role_keyed_by_track_birth_body():
    tr = pd.DataFrame({"t": [0.0, 1.0, 0.0, 1.0], "uid": ["g#0", "g#0", "x#0", "x#0"],
                       "body": ["g", "i", "i", "g"], "src": ["person"] * 4})
    kinds = {"g": "patrol_guard", "i": "commuter"}
    r = T.track_roles(tr, kinds, {"p_guard_given_uniform": 1.0, "p_guard_given_other": 0.0},
                      np.random.default_rng(0))
    assert r == {"g#0": True, "x#0": False}  # swap after birth does not change the cached role


def test_holm():
    h = T.holm({"b": 0.01, "s": 0.04, "g": 0.03})
    assert h["b"] == 0.03 and h["g"] == 0.06 and h["s"] == 0.06


def test_keep_sets_nested_for_any_grace():
    """AUDIT_H63B: b keeps a superset of g, g of s, for every grace window, so
    'live >= grace >= sticky' recall (and FA) holds by construction, not by measurement."""
    rng = np.random.default_rng(0)
    for _ in range(500):
        hist = sorted(rng.uniform(0, 200, rng.integers(0, 4)).tolist())
        ta, live, gs = float(rng.uniform(0, 200)), bool(rng.random() < 0.3), float(rng.uniform(0, 300))
        k = T.guard_keep(live, hist, ta, gs)
        assert k["s"] <= k["g"] <= k["b"]
