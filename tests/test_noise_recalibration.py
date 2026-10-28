"""H3g plumbing (no detector, no ffmpeg, no data)."""
import numpy as np
import pytest

from cctvsec.experiments import load_config
from cctvsec.experiments import noise_recalibration as nr
from survsim.sensors.degrade import PROFILES


def test_config_frozen():
    cfg = load_config("h3g_noise_recalibration")
    D = cfg["decision"]
    assert cfg["runner"] == "noise_recalibration" and 1.0 in cfg["s_grid"]
    assert (D["noise_ratio_min"], D["far_recall_min"], D["near_max_drop"], D["hn_min_frames"]) == (2.0, 0.6, 0.05, 8)


def test_scaled_profile_touches_only_noise_level():
    base = PROFILES["cctv_day_720p"]
    p = nr.scaled_profile(0.5)
    assert p.iso_gain == pytest.approx(base.iso_gain / 4) and p.read_noise == pytest.approx(base.read_noise / 2)
    for f in ("defocus", "denoise", "sharpen", "crf", "gop", "bf", "grain_sigma", "ae_target", "vignette"):
        assert getattr(p, f) == getattr(base, f)
    assert nr.input_sigma(p) == pytest.approx(nr.input_sigma(nr.scaled_profile(1.0)) / 2)


def test_scale_scales_sensor_noise_std():
    from survsim.sensors.degrade import sensor_noise
    img = np.full((200, 200, 3), 128.0, np.float32)
    sd = [np.std(sensor_noise(img, np.random.default_rng(0), nr.scaled_profile(s).iso_gain,
                              nr.scaled_profile(s).read_noise, 0, 0)) for s in (1.0, 0.5)]
    assert sd[1] / sd[0] == pytest.approx(0.5, rel=0.05)


def test_fit_scale_interp_and_clamp():
    g, v = [0.0, 0.5, 1.0], [1.0, 3.0, 5.0]
    assert nr.fit_scale(g, v, 4.0) == {"s": pytest.approx(0.75), "clamped": None}
    assert nr.fit_scale(g, v, 0.5)["clamped"] == "low" and nr.fit_scale(g, v, 9)["s"] == 1.0


def test_in_band_and_decide():
    band = {k: (0.0, 1.0) for k in nr.REALISM_KEYS}
    st = [{k: 0.5 for k in nr.REALISM_KEYS}] * 9 + [{**{k: 0.5 for k in nr.REALISM_KEYS}, "blockiness": 2.0}] * 3
    c = nr.in_band_count(st, band)
    assert c["n_all3"] == 9 and c["per_stat"]["blockiness"] == 9
    D = load_config("h3g_noise_recalibration")["decision"]
    res = {"noise": {"ratio_shipped_over_real": 2.5}, "far": {"tiles_d": {"matched": [0.65, 0.5, 0.8]}},
           "near": {"full_1280": {"drop_raw_matched": [0.04]}, "tiles_d": {"drop_raw_matched": [0.0]}},
           "realism_hn": {"matched": c}}
    d = nr.decide(res, D)
    assert d["decision_met"] and d["hyp_noise_ge_2x"] and d["HN_realism_ok"]
    res["near"]["full_1280"]["drop_raw_matched"] = [0.06]
    assert not nr.decide(res, D)["decision_met"]
