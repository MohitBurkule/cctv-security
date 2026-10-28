"""Motion regressions: nobody starts stacked on a spawn point, nobody gets stuck.

The rendered street_crowd videos showed everyone appearing at one spot at t=0
and walkers pinned motionless at shared goals (zone centroids, exact exit
coordinates) where reciprocal avoidance let only one person ever "arrive".
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from survsim.core.loader import load_scenario
from survsim.director import planner
from survsim.director.world import World
from cctvsec.eval.motion_audit import audit
from survsim.gt.writers import Recorder

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def street_report(tmp_path_factory):
    out = tmp_path_factory.mktemp("street")
    sc = load_scenario(ROOT / "configs/scenarios/street_crowd.yaml")
    sc.duration_s = 60
    # Director + world GT only: the mock camera raster is irrelevant to motion
    # and is 95% of a full run's cost.
    world, rec = World(sc), Recorder(sc, out)
    for _ in range(sc.n_ticks):
        world.step()
        rec.add_world(world)
    world.finalise()
    rec.write(world)
    return audit(out)


def test_street_crowd_stuck_fraction_below_2pct(street_report):
    assert street_report["stuck_fraction"] < 0.02, street_report["episodes"]
    assert street_report["walk_stationary_fraction"] < 0.05


def test_walking_speeds_are_varied_and_realistic(street_report):
    sp = street_report["walking_speed"]
    assert sp["frac_in_0.8_1.8"] >= 0.9
    assert sp["std"] > 0.05          # not one constant speed


def test_population_is_prewarmed_not_stacked_at_t0(street_report):
    t0 = street_report["t0_clustering"]
    assert t0["n"] >= 3
    assert t0["frac_within_1m"] < 0.5
    assert t0["median_nn_m"] > 1.0


def test_generated_arrivals_are_staggered_and_heroes_keep_t0():
    sc = load_scenario(ROOT / "configs/scenarios/street_crowd.yaml")
    w = World(sc)
    heroes = {p.id for p in sc.population.hero}
    assert heroes <= set(w.agents)                        # scripted: present at t=0
    arrivals = [t for t, _ in w._pending]
    assert len(arrivals) >= 3 and len(set(np.round(arrivals, 1))) == len(arrivals)
    assert min(arrivals) > 0.0                            # warm-up consumed the past


def test_prewarm_is_deterministic():
    sc = load_scenario(ROOT / "configs/scenarios/street_crowd.yaml")
    a, b = World(sc), World(sc)
    assert a.agents.keys() == b.agents.keys()
    for uid in a.agents:
        assert np.allclose(a.agents[uid].pos, b.agents[uid].pos)


def test_head_on_pair_does_not_deadlock():
    """Two walkers on the same line in opposite directions must pass each other."""
    a, b = np.array([0.0, 0.0]), np.array([4.0, 0.0])
    ga, gb = np.array([8.0, 0.0]), np.array([-4.0, 0.0])
    for _ in range(100):
        va = planner.steer(a, ga, 1.2, b[None])
        vb = planner.steer(b, gb, 1.2, a[None])
        a, b = a + va * 0.1, b + vb * 0.1
    assert a[0] > 6.0 and b[0] < -2.0
