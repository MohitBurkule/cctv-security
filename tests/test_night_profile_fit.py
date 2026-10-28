"""H32e plumbing (no detector, no ffmpeg, no LLVIP)."""
import numpy as np
import pytest

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments import night_profile_fit as nf
from survsim.sensors.degrade import PROFILES


def test_config_frozen_and_registered():
    cfg = load_config("h32e_night_profile_fit")
    assert RUNNERS[cfg["runner"]] == "night_profile_fit"
    assert cfg["decision"] == {"recall_min": 0.5, "hn_bar_max": 8}
    assert (cfg["conf"], cfg["min_h"], cfg["block_frames"], cfg["tune_n"], cfg["hn_frames"]) == (0.25, 20, 30, 15, 13)
    assert cfg["s_grid"] == [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
    assert cfg["crf_grid"] == [23, 26, 29, 32, 35, 39]
    assert cfg["batch_dir"] == "out/gt_vis_v2"
    assert len(range(cfg["frame_start"], cfg["frame_stop"], cfg["stride"])) * len(cfg["cams"]) == 60


def test_fit_profile_changes_only_noise_and_crf():
    base = PROFILES["cctv_night_lowlight"]
    p = nf.fit_profile(0.5, 29)
    assert p.crf == 29 and not p.osd
    assert p.iso_gain == pytest.approx(base.iso_gain * 0.25) and p.read_noise == pytest.approx(base.read_noise * 0.5)
    assert p.fpn == pytest.approx(base.fpn * 0.5)
    for f in ("ae_target", "gamma", "defocus", "denoise", "sharpen", "saturation", "wb_gains", "grain_sigma",
              "auto_levels", "resolution", "gop", "bf"):
        assert getattr(p, f) == getattr(base, f), f
    s = nf.fit_profile(1.0, base.crf)
    assert s.iso_gain == base.iso_gain and s.crf == base.crf


def test_loss_argmin_bands_bar():
    assert nf.loss(0.2, 1.5, 0.2, 1.5) == 0
    assert nf.loss(0.4, 1.5, 0.2, 1.5) == pytest.approx(1.0)
    cells = [{"s": 1, "crf": 39, "loss": 2.0}, {"s": .5, "crf": 29, "loss": .1}, {"s": .4, "crf": 29, "loss": .1}]
    assert nf.argmin_grid(cells) == {"s": .5, "crf": 29, "loss": .1}
    b = {k: {"p10": 1.0, "p90": 2.0, "median": 1.5} for k in nf.KEYS}
    assert nf.in_band({"noise_sigma": 1.5, "blockiness": 1.0}, b)
    assert not nf.in_band({"noise_sigma": 1.5, "blockiness": 2.1}, b)
    assert nf.hn_bar(8, 10, 13, 8) == 8 and nf.hn_bar(5, 10, 13, 8) == 6 and nf.hn_bar(10, 10, 13, 8) == 8


def test_two_stats_matches_frame_stats():
    from survsim.realism.stats import frame_stats
    img = np.random.default_rng(0).integers(0, 255, (360, 640, 3)).astype(np.uint8)
    a, f = nf.two_stats(img), frame_stats(img)
    assert a["noise_sigma"] == pytest.approx(f.noise_sigma) and a["blockiness"] == pytest.approx(f.blockiness)


def test_boot_and_decide():
    rows = {"raw": {("c", 0): (9, 10), ("c", 1): (8, 10)}, "shipped": {("c", 0): (0, 10), ("c", 1): (1, 10)},
            "fitted": {("c", 0): (6, 10), ("c", 1): (7, 10)}}
    r = nf.boot(rows, 200, 0)
    assert r["fitted"][0] == pytest.approx(0.65) and r["night_penalty_raw_minus_fitted"][0] == pytest.approx(0.2)
    res = {"recall": r, "hard_negative": {"n_in_band": 7, "bar": 8}}
    d = nf.decide(res, {"recall_min": 0.5})
    assert d["recall_ok"] and not d["HN_ok"] and not d["decision_met"]
    res["hard_negative"]["n_in_band"] = 8
    assert nf.decide(res, {"recall_min": 0.5})["decision_met"]
