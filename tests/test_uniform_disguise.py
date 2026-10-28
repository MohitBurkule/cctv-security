import numpy as np
import pandas as pd

from cctvsec.experiments import uniform_disguise as U
from survsim.generator import narrative


def test_uniformed_intruder_is_intrusion_motion_with_guard_role():
    assert narrative.UNIFORMED_INTRUDER_ROLE == "guard"
    assert narrative.uniformed_intruder_arc.__doc__


def test_off_route_needs_a_sustained_streak():
    zones = [{"id": "r", "tag": "restricted", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]]}]
    dist = U._route_dist(zones, [[10, -1]], 1.0)
    rc = {"off_m": 5.0, "off_s": 5.0, "lookback_s": 30.0}
    t = np.arange(0, 20, 0.2)
    on = pd.DataFrame({"t": t, "x": np.full_like(t, 10.0), "y": np.linspace(-1, 10, len(t))})  # gate->centre leg
    assert U._off_route_time(on, 10.0, dist, rc) is None
    off = pd.DataFrame({"t": t, "x": np.full_like(t, 15.0), "y": np.full_like(t, 14.0)})
    assert U._off_route_time(off, 10.0, dist, rc) == 10.0
