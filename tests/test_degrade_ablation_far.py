"""H3f stage-ablation plumbing (no detector, no GPU, no ffmpeg)."""
import cv2
import numpy as np
import pytest

from cctvsec.experiments import degrade_ablation_far as da
from cctvsec.experiments import load_config
from survsim.sensors.degrade import PROFILES


def test_config_registered_and_frozen_fields():
    cfg = load_config("h3f_degrade_ablation")
    assert cfg["runner"] == "degrade_ablation_far"
    assert cfg["decision"]["predicted_culprit"] == "codec" and cfg["decision"]["share_min"] == 0.60
    assert cfg["decision"]["hn_max_drop"] == 0.05 and cfg["decision"]["primary_arm"] == "tiles_d"


def test_variants_switch_the_right_groups():
    full, codec = da.variant_spec("full")
    base = PROFILES["cctv_day_720p"]
    assert codec and full.defocus == base.defocus and full.crf == base.crf and not full.osd
    p, codec = da.variant_spec("loo_codec")
    assert not codec and p.denoise == base.denoise
    p, codec = da.variant_spec("aoi_isp")
    assert not codec and p.denoise == base.denoise and p.defocus == 0 and p.iso_gain == 1e-6 and p.ae_target == 0
    p, codec = da.variant_spec("loo_noise")
    assert codec and p.grain_sigma == 0 and p.denoise == base.denoise
    assert len(da.variants()) == 1 + 2 * len(da.GROUPS)
    with pytest.raises(ValueError):
        da.variant_spec("loo_resample")


def test_all_groups_off_is_near_identity_and_resample_is_identity():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, (720, 1280, 3)).astype(np.uint8)
    # by construction: batch_v8 renders are 1280x720, so the profile's resize is the identity
    assert np.array_equal(cv2.resize(img.astype(np.float32), (1280, 720), interpolation=cv2.INTER_AREA), img)
    p, _ = da.variant_spec("aoi_codec")          # every pre-codec group off
    x = p._pre_codec(img, seed=1, frame_index=0, sequence_seed=1)
    assert np.abs(x - img.astype(np.float32)).max() <= 1.0     # float rounding only


def test_shares_and_decision():
    R = {"raw": 0.9, "full": 0.3, **{f"loo_{g}": 0.3 for g in da.GROUPS}, **{f"aoi_{g}": 0.9 for g in da.GROUPS}}
    R["loo_codec"], R["aoi_codec"] = 0.75, 0.45        # codec: 0.45/0.6 = 0.75 both ways
    s = da.shares(R)
    assert s["loo"]["codec"] == pytest.approx(0.75) and s["aoi"]["codec"] == pytest.approx(0.75)
    D = {"share_min": 0.6, "min_loss": 0.1, "predicted_culprit": "codec"}
    d = da.decide(s, D)
    assert d["culprit"] == "codec" and d["decision_met"] and d["prediction_correct"]
    R["aoi_codec"] = 0.7                                 # alone it only explains 0.33: interaction, not met
    assert not da.decide(da.shares(R), D)["decision_met"]
    R2 = dict(R, full=0.85)                              # no loss to attribute
    assert not da.decide(da.shares(R2), D)["loss_ok"]


def test_bootstrap_shapes():
    rng = np.random.default_rng(0)
    n = np.full(20, 30.0)
    hits = {v: rng.binomial(30, 0.5, 20).astype(float) for v in ["raw", "shipped"] + da.variants()}
    hits["raw"] = np.full(20, 27.0)
    b = da.bootstrap(hits, n, 200, 0)
    assert b["recall"]["raw"] == [0.9, 0.9, 0.9]
    assert set(b["loo"]) == set(da.GROUPS) and len(b["aoi"]["codec"]) == 3
