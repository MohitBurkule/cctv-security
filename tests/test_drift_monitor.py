"""H34 drift-monitor scoring primitives (cctvsec/experiments/drift_monitor.py)."""
import numpy as np

from cctvsec.experiments import drift_monitor as dm
from survsim.sensors.degrade import PROFILES


def test_psi_zero_for_identical_and_large_for_shift():
    rng = np.random.default_rng(0)
    ref = rng.normal(size=2000)
    assert dm.psi(ref, ref) < 1e-9
    assert dm.psi(ref, rng.normal(size=2000)) < 0.05
    assert dm.psi(ref, rng.normal(2.0, 1.0, size=2000)) > 1.0


def test_small_window_psi_is_noise_dominated():
    # the pre-registered P1 mechanism: 13 iid samples vs 50, 10 bins -> PSI far above 0.25
    rng = np.random.default_rng(1)
    vals = [dm.psi(rng.normal(size=50), rng.normal(size=13)) for _ in range(200)]
    assert np.median(vals) > 0.25


def test_score_series_alignment_and_trigger_delay():
    x = np.zeros((40, 2))
    x[:, 0] = np.random.default_rng(2).normal(size=40) * 0.1
    x[20:, 1] = 5.0
    x[:20, 1] = np.random.default_rng(3).normal(size=20) * 0.1
    s = dm.score_series(x, (0, 10), 4, "z")
    assert np.isnan(s[:13]).all() and not np.isnan(s[13:]).any()
    d = dm.first_delay(dm.triggers(s, 10.0), 20)
    assert d is not None and d <= 3
    ks = dm.score_series(x, (0, 10), 4, "ks")
    assert dm.first_delay(dm.triggers(ks, 0.01, lower_is_alarm=True), 20) is not None


def test_emb_score_scale_invariant():
    rng = np.random.default_rng(4)
    r, w = rng.normal(size=(50, 8)), rng.normal(size=(13, 8)) + 1
    assert abs(dm.emb_score(r, w) - dm.emb_score(10 * r, 10 * w)) < 1e-9


def test_shifted_profile_and_recall_frames():
    base = PROFILES["cctv_day_720p"]
    p = dm.shifted_profile(base, {"ev": -2.0, "iso_mult": 2.0})
    assert p.ev == -2.0 and p.iso_gain == base.iso_gain * 2 and p.crf == base.crf
    assert isinstance(dm.shifted_profile(base, {"crf": 40.0}).crf, int)
    rf = dm.recall_frames(["a", "b", "c"], 23, 75, 150)
    assert sum(len(v) for v in rf.values()) == 23
    assert all(75 <= s < 150 for v in rf.values() for s in v)
    assert all(len(set(v)) == len(v) for v in rf.values())


def test_per_24h():
    assert dm.per_24h(1 / 1440) == 1.0


def test_stream_cams_per_run_map_and_unreadable_frame_guard(tmp_path):
    import pytest
    cfg = {"runs": ["a", "b"], "cams": {"a": ["cam_01"], "b": ["cam_gate", "cam_sub"]}}
    assert dm.stream_cams(cfg) == ["a/cam_01", "b/cam_gate", "b/cam_sub"]
    assert dm.stream_cams({"runs": ["a"], "cams": ["c1", "c2"]}) == ["a/c1", "a/c2"]
    spec = {"cache": str(tmp_path / "x.npz"), "base_profile": "cctv_day_720p", "params": None,
            "paths": [str(tmp_path / "missing.png")], "seed": 0}
    with pytest.raises(FileNotFoundError, match="unreadable"):
        dm.stream_job(spec)


def test_h34_config_streams_exist_on_disk():
    from cctvsec.experiments import load_config
    from cctvsec.experiments.common import rpath
    cfg = load_config("h34_drift_monitor")
    root = rpath(cfg["batch"])
    if not root.is_dir():
        import pytest
        pytest.skip("batch not present")
    for cam in dm.stream_cams(cfg):
        r, c = cam.split("/")
        assert (root / r / "render" / c).is_dir(), cam
