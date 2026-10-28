"""H39 auto-calibration geometry: recovery on synthetic people, gauge, DLT, bootstrap."""
import json
from pathlib import Path

import numpy as np
import pytest

from cctvsec.experiments import autocalib as ac


def _scene(f=800.0, pitch=20.0, roll=0.0, h=5.0, n=300, person=1.7, seed=0):
    rng = np.random.default_rng(seed)
    K = np.array([[f, 0, 640], [0, f, 360], [0, 0, 1.0]])
    R = ac.rot_tilt(pitch, roll)
    C = np.array([0, 0, h])
    G = np.c_[rng.uniform(-8, 8, n), rng.uniform(6, 35, n), np.zeros(n)]
    foot = ac.project(K, R, C, G)
    head = ac.project(K, R, C, G + [0, 0, person])
    ok = (foot[:, 1] < 718) & (head[:, 1] > 2) & (foot[:, 0] > 2) & (foot[:, 0] < 1278)
    return K, R, C, G[ok], foot[ok], head[ok]


def test_rot_tilt_positive_pitch_looks_down():
    R = ac.rot_tilt(30, 0)
    assert R[2, 2] < 0            # optical axis has a downward world component
    assert np.isclose(np.degrees(np.arcsin(-R[2, 2])), 30)


def test_fit_recovers_exact_camera_with_true_height():
    _K, _R, _C, _G, foot, head = _scene()
    fit = ac.fit_known_height(foot, head, (1280, 720), 1.7)
    assert fit["f"] == pytest.approx(800, rel=0.01)
    assert fit["pitch"] == pytest.approx(20, abs=0.2)
    assert fit["h"] == pytest.approx(5.0, rel=0.01)


def test_height_prior_bias_is_a_scale_error():
    """A 5 % too-tall prior scales camera height (and hence all ground distances) by ~5 %."""
    _K, _R, _C, _G, foot, head = _scene()
    fit = ac.fit_known_height(foot, head, (1280, 720), 1.7 * 1.05)
    assert fit["h"] == pytest.approx(5.0 * 1.05, rel=0.01)


def test_heights_from_boxes_recovers_person_height():
    K, R, C, _G, foot, head = _scene(person=1.55)
    assert np.allclose(ac.heights_from_boxes(K, R, C, foot, head), 1.55, atol=1e-6)


def test_auto_to_world_with_true_params_matches_calib_homography():
    root = Path("out/batch_v8/street_crowd_day/calib/cam_01.json")
    if not root.is_file():
        pytest.skip("batch_v8 not present")
    c = json.loads(root.read_text())
    K, R, t = (np.array(c[k], float) for k in ("K", "R", "t"))
    C = -R.T @ t
    fit = {"f": K[0, 0], "pitch": float(np.degrees(np.arcsin(-R[2, 2]))), "roll": 0.0, "h": C[2]}
    Ka, Ra, Ca = ac.auto_to_world(fit, (1280, 720), ac.heading_deg(R), C[:2])
    assert np.allclose(Ra, R, atol=1e-9)
    uv = np.array([[640.0, 600.0], [200.0, 500.0]])
    H0 = np.linalg.inv(K @ np.c_[R[:, 0], R[:, 1], t])
    assert np.allclose(ac.backproject_ground(Ka, Ra, Ca, uv)[:, :2], ac.apply_h(H0, uv), atol=1e-6)


def test_dlt_recovers_homography():
    _K, _R, _C, G, foot, _head = _scene()
    H = ac.dlt_homography(foot, G[:, :2])
    assert np.allclose(ac.apply_h(H, foot), G[:, :2], atol=1e-6)


def test_bootstrap_bins_and_ratio():
    rng = np.random.default_rng(1)
    dist = rng.uniform(0, 50, 2000)
    err = 0.02 * dist
    track = rng.integers(0, 40, 2000).astype(str)
    r = ac.bin_rmse_boot(err, dist, track, [0, 10, 20, 30, 1000], 200, 0)
    assert r["near_lt20"]["rmse"] < r["far_ge30"]["rmse"]
    assert r["ratio_far_near"]["ci95"][0] <= r["ratio_far_near"]["rmse"] <= r["ratio_far_near"]["ci95"][1]


def test_axis_aligned_box_heads_do_not_bias_fit():
    """Regression: a box's top-centre shares the foot's u. The fit must use v only; the first
    version fitted u too and drove f to its bound on every batch_v8 camera."""
    _K, _R, _C, _G, foot, head = _scene(pitch=25.0)
    head = np.c_[foot[:, 0], head[:, 1]]
    fit = ac.fit_known_height(foot, head, (1280, 720), 1.7)
    assert fit["f"] == pytest.approx(800, rel=0.02)


def test_fixed_focal_fit():
    _K, _R, _C, _G, foot, head = _scene()
    fit = ac.fit_known_height(foot, head, (1280, 720), 1.7, f_fixed=800.0)
    assert fit["f"] == 800.0 and fit["pitch"] == pytest.approx(20, abs=0.1)
