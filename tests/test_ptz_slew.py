"""H56 PTZ slew-to-alarm runner (cctvsec/experiments/ptz_slew.py)."""
from __future__ import annotations

import numpy as np

from survsim.core.geometry import usably_visible
from cctvsec.experiments import load_config
from cctvsec.experiments import ptz_slew as P


def test_aim_puts_estimate_in_frame_and_framing_matches():
    cfg = load_config("h56_ptz_slew")
    pole = (0.0, 0.0, 10.0)
    for est in ([40.0, 0.0, 0.0], [-30.0, 25.0, 0.0], [5.0, -80.0, 0.0]):
        yaw, pitch, hfov = P.aim(pole, np.array(est), cfg)
        cam = P.ptz_camera(pole, yaw, pitch, hfov, cfg["site"]["res"])
        assert usably_visible(cam, np.array(est))          # exact aim always acquires a static target
        off = np.array(est) + np.array([-np.sin(np.radians(yaw)), np.cos(np.radians(yaw)), 0]) * 5.0
        assert not usably_visible(cam, off)                # 5 m lateral is outside a 6 m frame


def test_calib_error_rmse_follows_distance_and_is_range_dominated():
    cfg = load_config("h56_ptz_slew")
    rng = np.random.default_rng(0)
    cam = np.array([0.0, 0.0])
    for d, want in ((10.0, 0.96), (40.0, 2.92)):
        e = np.array([P.calib_error(np.array([d, 0.0, 0.0]), cam, "h39", cfg, rng)[0][:2] - [d, 0] for _ in range(4000)])
        assert abs(np.sqrt((e ** 2).sum(1).mean()) - want) < 0.08 * want
        assert e[:, 0].std() > 2.5 * e[:, 1].std()        # error along the line of sight


def test_seed_is_deterministic_and_contention_is_worse_with_one_ptz():
    cfg = load_config("h56_ptz_slew")
    cfg.update(n_alarms_indep=20, contention_hours=0.25)
    a, b = P.run_seed(3, cfg), P.run_seed(3, cfg)
    assert a["rows"] == b["rows"]
    body = P.summarise(a["rows"] + P.run_seed(4, cfg)["rows"], {**cfg, "n_boot": 50})
    c = body["contention"]
    assert c["h39_1ptz"]["busy_at_arrival"]["rate"] > c["h39_2ptz"]["busy_at_arrival"]["rate"]
