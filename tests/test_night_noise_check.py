"""H32c plumbing (no detector, no ffmpeg, no data)."""
import pytest

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments import night_noise_check as nn
from survsim.sensors.degrade import PROFILES


def test_config_frozen_and_registered():
    cfg = load_config("h32c_night_noise")
    D = cfg["decision"]
    assert RUNNERS[cfg["runner"]] == "night_noise_check" and 1.0 in cfg["s_grid"]
    assert (D["noise_ratio_min"], D["recall_delta_min"], D["hn_min_frames"]) == (1.5, 0.10, 8)
    assert len(nn.frames_for(cfg)) * len(cfg["cams"]) <= 60 and cfg["hn_frames"] == 13
    assert (cfg["conf"], cfg["min_h"], cfg["block_frames"]) == (0.25, 20, 30)


def test_arm_profile_only_noise_and_osd():
    base = PROFILES["cctv_night_lowlight"]
    p = nn.arm_profile(0.5)
    assert not p.osd and p.fps == base.fps
    assert p.iso_gain == pytest.approx(base.iso_gain / 4) and p.read_noise == pytest.approx(base.read_noise / 2)
    for f in ("ae_target", "auto_levels", "gamma", "denoise", "crf", "grain_sigma", "defocus", "wb_gains"):
        assert getattr(p, f) == getattr(base, f)


def test_luma_gap_and_blocks():
    g = nn.luma_gap(90.0, 50.0, 34.0, 48.65)
    assert g["closed_measured"] == pytest.approx(40 / 56, abs=1e-3)
    assert g["closed_by_construction_ae"] == pytest.approx((90 - 48.65) / 56, abs=1e-3)
    assert [nn.block_of(f, 30) for f in (1, 30, 31, 98)] == [0, 0, 1, 3]


def test_block_boot_and_decide():
    rows = {"raw": {("a", 0): (8, 10), ("a", 1): (9, 10)}, "shipped": {("a", 0): (2, 10), ("a", 1): (3, 10)},
            "matched": {("a", 0): (6, 10), ("a", 1): (7, 10)}}
    r = nn.block_boot(rows, 200, 0)
    assert r["matched"][0] == pytest.approx(0.65) and r["delta_matched_shipped"][0] == pytest.approx(0.4)
    res = {"recall": r, "noise": {"ratio_shipped_over_real": 1.2}, "hard_negative": {"n_in_band": 3}}
    d = nn.decide(res, {"noise_ratio_min": 1.5, "recall_delta_min": 0.1, "hn_min_frames": 8})
    assert d["decision_met"] and not d["hyp_noise_met"] and not d["HN_ok"]
