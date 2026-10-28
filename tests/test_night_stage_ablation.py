"""H32d plumbing (no detector, no ffmpeg, no data)."""
import numpy as np
import pytest

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments import night_stage_ablation as ns
from survsim.sensors.degrade import PROFILES


def test_config_frozen_and_registered():
    cfg = load_config("h32d_night_stage_ablation")
    D = cfg["decision"]
    assert RUNNERS[cfg["runner"]] == "night_stage_ablation"
    assert (D["share_min"], D["min_loss"], D["predicted_culprit"]) == (0.60, 0.10, "codec")
    assert (cfg["conf"], cfg["min_h"], cfg["block_frames"], cfg["stride"]) == (0.25, 20, 30, 5)
    assert len(range(cfg["frame_start"], cfg["frame_stop"], cfg["stride"])) * len(cfg["cams"]) == 60


def test_variant_specs():
    base = PROFILES["cctv_night_lowlight"]
    p, codec = ns.variant_spec("full")
    assert codec and not p.osd and p.ae_target == base.ae_target and p.crf == base.crf
    p, codec = ns.variant_spec("loo_codec")
    assert not codec and p.iso_gain == base.iso_gain
    p, codec = ns.variant_spec("aoi_exposure")
    assert not codec and p.ae_target == base.ae_target and p.defocus == 0 and p.iso_gain == 1e-6
    assert p.saturation == 1.0 and p.denoise == 0 and p.resolution == (1280, 720)
    p, _ = ns.variant_spec("loo_colour")
    assert p.wb_gains == (1.0, 1.0, 1.0) and p.saturation == 1.0 and p.defocus == base.defocus
    with pytest.raises(ValueError):
        ns.variant_spec("loo_osd")
    assert len(ns.variants()) == 1 + 2 * len(ns.GROUPS)


def test_all_off_is_identity_up_to_resize():
    """aoi_codec without the codec = pure resize, by construction."""
    from survsim.sensors.degrade import Profile
    img = np.random.default_rng(0).integers(0, 255, (36, 64, 3)).astype(np.uint8)
    p, _ = ns.variant_spec("aoi_codec")
    p = Profile(**{**p.__dict__, "resolution": None})
    x = p._pre_codec(img, seed=1, frame_index=0, sequence_seed=0)
    assert np.abs(x - img).max() < 1.01


def test_shares_bootstrap_decide():
    R = {"raw": 0.9, "full": 0.1, **{f"loo_{g}": 0.1 for g in ns.GROUPS}, **{f"aoi_{g}": 0.9 for g in ns.GROUPS}}
    R["loo_codec"], R["aoi_codec"] = 0.7, 0.3
    s = ns.shares(R)
    assert s["loo"]["codec"] == pytest.approx(0.75) and s["aoi"]["codec"] == pytest.approx(0.75)
    band = {"p10": 28.0, "p90": 39.0, "median": 33.0}
    assert ns.out_of_band(50.0, 0.34, band, 0.17) == {"luma": 11.0, "sigma_log2": 1.0}
    dist = {"full": {"luma": 11.0, "sigma_log2": 1.0}, "loo_codec": {"luma": 12.0, "sigma_log2": 1.0}}
    D = {"share_min": 0.6, "min_loss": 0.1, "predicted_culprit": "codec", "hn_tol_luma": 0.5, "hn_tol_log2": 0.05}
    d = ns.decide(s, dist, D)
    assert d["culprit"] == "codec" and d["decision_met"] and d["prediction_correct"] and not d["HN_ok"]
    hits = {k: np.array([8.0, 9.0]) for k in ["raw", "full"] + ns.variants()[1:]}
    hits["full"] = np.array([1.0, 1.0])
    b = ns.bootstrap(hits, np.array([10.0, 10.0]), 100, 0)
    assert b["recall"]["raw"][0] == pytest.approx(0.85) and b["loss"][0] == pytest.approx(0.75)
