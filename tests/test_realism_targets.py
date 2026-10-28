"""Tests for reference-free realism scoring.

The metric's job is to catch the giveaways of a synthetic frame — no sensor
noise, no compression blocking, implausibly crisp edges — without needing real
reference images. These tests pin that it catches them, and that it does not
claim more than it can support.
"""

from __future__ import annotations

import numpy as np
import pytest

from survsim.realism.fid import image_stats
from cctvsec.eval.realism_targets import (
    CCTV_DAY,
    CCTV_NIGHT_IR,
    Target,
    compare_profiles,
    score_image,
    score_profile,
)
from survsim.sensors.degrade import apply_profile


def _render(seed: int = 0, size: int = 256) -> np.ndarray:
    """A synthetic 'clean render': smooth gradients, zero sensor noise.

    Deliberately noise-free and free of hard edges, so the bilateral residual is
    ~0 and `noise_sigma` is unambiguously below anything a real sensor produces.
    """
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    base = 90 + 40 * np.sin(xx / 60.0 + seed) + 30 * np.cos(yy / 70.0)
    img = np.dstack([base, base * 0.95 + 10, base * 0.9 + 18])
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------- targets


def test_target_scores_one_inside_the_range() -> None:
    t = Target("x", 1.0, 5.0, "why")
    assert t.score(3.0) == 1.0
    assert t.score(1.0) == 1.0 and t.score(5.0) == 1.0


def test_target_decays_outside_rather_than_snapping_to_zero() -> None:
    """A near miss should score better than a wild miss."""
    t = Target("x", 1.0, 5.0, "why")
    assert 0.0 < t.score(6.0) < 1.0
    assert t.score(6.0) > t.score(9.0)
    assert t.score(100.0) == 0.0


# ------------------------------------------------- catching the synthetic tells


def test_a_clean_render_is_caught_as_synthetic() -> None:
    """Absent sensor noise is the clearest giveaway, and must be flagged by name.

    The composite score is deliberately *not* asserted here: decay outside a range
    is gentle, so a render can fail a diagnostic target and still score in the
    nineties. `out_of_range` is the actionable output.
    """
    stats = image_stats(_render())
    result = score_image(stats, CCTV_DAY)

    assert stats.noise_sigma < 1.0, "a clean render should have almost no noise"
    assert "noise_sigma" in result["out_of_range"]
    assert "laplacian_var" in result["out_of_range"]     # and it is too crisp


def test_degradation_improves_the_score() -> None:
    """The whole point of the sensor model: move the render toward real statistics."""
    render = _render()
    clean = score_image(image_stats(render), CCTV_DAY)["score"]
    degraded = score_image(image_stats(apply_profile(render, "cctv_day_720p", seed=1)),
                           CCTV_DAY)["score"]
    assert degraded > clean


def test_night_profile_is_scored_against_night_targets() -> None:
    """Daylight targets would fail a correct IR frame for being monochrome."""
    render = _render()
    ir = apply_profile(render, "cctv_night_ir", seed=2)
    stats = image_stats(ir)

    assert score_image(stats, CCTV_NIGHT_IR)["score"] > score_image(stats, CCTV_DAY)["score"]


def test_ir_output_is_effectively_monochrome() -> None:
    """Near-monochrome, not perfectly so: the codec adds chroma noise after the
    greyscale conversion, exactly as real IR footage shows."""
    ir = apply_profile(_render(), "cctv_night_ir", seed=3)
    colour = apply_profile(_render(), "cctv_day_720p", seed=3)
    assert image_stats(ir).saturation_mean < 20.0
    assert image_stats(ir).saturation_mean < image_stats(colour).saturation_mean


# -------------------------------------------------------------- honest limits


def test_targets_are_calibrated_from_measurement_not_assumption() -> None:
    """The daytime ranges came from 12 real frames, not from reasoning.

    The distinction is not cosmetic: the reasoned-out ranges were wrong in a
    specific direction (they assumed CCTV is blurry and clean), and tuning the
    degradation pipeline to them moved renders *further* from real footage.
    """
    noise = next(t for t in CCTV_DAY if t.name == "noise_sigma")
    assert "measured" in noise.rationale
    # Real frames carry crushed shadow and blown highlights; a clean render has
    # neither, and the calibrated ranges must allow for them.
    assert any(t.name == "clipped_fraction" for t in CCTV_DAY)
    assert any(t.name == "dark_fraction" for t in CCTV_DAY)


def test_real_frames_score_well_against_their_own_targets() -> None:
    """The calibration sanity check: the data the ranges came from must pass."""
    import glob

    import cv2

    paths = sorted(glob.glob("/home/mohit/data/real_cctv/*.jpg"))
    if len(paths) < 3:
        pytest.skip("reference frames not available on this machine")

    frames = [cv2.imread(p) for p in paths]
    result = score_profile([f for f in frames if f is not None], "cctv_day_720p")
    assert result["score"] > 0.9


def test_report_states_what_it_cannot_confirm() -> None:
    result = score_profile([apply_profile(_render(), "cctv_day_720p", seed=4)],
                           "cctv_day_720p")
    assert "cannot confirm realism" in result["interpretation"]


def test_clean_profile_is_not_scored_as_a_candidate() -> None:
    """The clean render is the input to degradation, not a contender for realism."""
    result = score_profile([_render()], "clean")
    assert result["score"] is None
    assert "not a candidate" in result["note"]


def test_every_target_explains_itself() -> None:
    for target in CCTV_DAY + CCTV_NIGHT_IR:
        assert len(target.rationale) > 15, target.name


# ------------------------------------------------------------------ comparison


def test_comparison_reports_what_gives_the_render_away() -> None:
    renders = [_render(i) for i in range(3)]
    result = compare_profiles({
        "clean": renders,
        "cctv_day_720p": [apply_profile(r, "cctv_day_720p", seed=i)
                          for i, r in enumerate(renders)],
    })
    verdict = result["verdict"]
    assert verdict["degradation_helps"] is True
    assert verdict["clean_failures"]          # names the failing statistics


def test_profile_report_lists_worst_statistics_to_fix() -> None:
    result = score_profile([_render(i) for i in range(2)], "cctv_day_720p")
    assert result["worst_statistics"]
    assert all(isinstance(name, str) for name, _ in result["worst_statistics"])
