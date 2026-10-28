"""H40 line-crossing rule arms (cctvsec/experiments/line_cross.py)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from cctvsec.experiments import line_cross as LC
from cctvsec.experiments import load_config

ZONES = [{"id": "zone.r", "tag": "restricted", "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
         {"id": "zone.g", "tag": "gate", "polygon": [[-6, 8], [-0.5, 8], [-0.5, 12], [-6, 12]]}]
CFG = {"sterile_tags": ["restricted", "perimeter_fence"], "context_tags": ["gate", "queue"],
       "arms": {"A": {"min_age_s": 2.0, "min_height_m": 1.2}, "B": {"min_depth_m": 1.5, "min_dwell_s": 5.0},
                "C": {"context_m": 4.0}}}


def _track(uid, xs, ys, h=1.7, dt=0.2):
    t = np.arange(len(xs)) * dt
    return pd.DataFrame({"t": t, "uid": uid, "base": uid, "src": "person", "x": xs, "y": ys, "h": h})


def test_arms_are_cumulative_filters():
    # intruder: walks in from the south far from the gate, goes 4 m deep, stays 20 s
    n_out, n_in = 30, 100
    intr = _track("p0", np.full(n_out + n_in, 5.0), np.r_[np.linspace(-3, -0.1, n_out), np.full(n_in, 4.0)])
    # corner cut: in and out within 1 s
    cut = _track("p1", np.linspace(-2, 3, 40), np.full(40, 9.8))
    # ghost: short, small, appears inside
    ghost = _track("g", np.full(5, 5.0), np.full(5, 5.0), h=0.4)
    # near-gate entrant: first inside tick (3, 7) is 3.6 m from the gate zone, dwells deep
    gate = _track("p2", np.r_[np.linspace(-3, -0.1, 30), np.full(100, 3.0)], np.full(130, 9.0) - np.r_[np.zeros(30), np.full(100, 2.0)])
    al = LC.world_alarms(pd.concat([intr, cut, ghost, gate]), ZONES, CFG)
    who = {a: sorted({x[1] for x in v}) for a, v in al.items()}
    assert who["N"] == ["g", "p0", "p1", "p2"]
    assert who["A"] == ["p0", "p1", "p2"]            # ghost removed by age/height
    assert who["B"] == ["p0", "p2"]                  # corner cut has no dwell
    assert who["C"] == ["p0"]                        # gate-adjacent crossing excluded
    tB = next(x[0] for x in al["B"] if x[1] == "p0")
    assert 5.0 + n_out * 0.2 - 0.2 <= tB <= 10 + n_out * 0.2   # dwell satisfied, inside the 10 s window


def test_noise_model_is_seeded_and_adds_ghosts_and_fragments():
    df = pd.DataFrame({"t": np.tile(np.arange(0, 600, 0.2), 2), "uid": np.repeat(["a", "b"], 3000),
                       "x": 1.0, "y": 1.0})
    nz = load_config("h40_line_cross")["noise"]
    a = LC.add_noise(df, ZONES, 2.0, np.random.default_rng(1), nz)
    b = LC.add_noise(df, ZONES, 2.0, np.random.default_rng(1), nz)
    pd.testing.assert_frame_equal(a, b)
    assert (a["src"] == "ghost").any() and (a["src"] == "fragment").any()
    assert set(a.loc[a["src"] != "ghost", "base"]) == {"a", "b"}


def test_h40_config_loads():
    cfg = load_config("h40_line_cross")
    assert cfg["runner"] == "line_cross" and cfg["n_clean"] == 676
    assert cfg["thresholds"] == {"naive_x_budget": 10, "fa_ratio": 5, "recall": 0.9}
