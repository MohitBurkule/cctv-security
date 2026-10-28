"""Tests for measuring gait style effects from CASIA-B silhouettes.

CASIA-B is the dataset that turns STYLE_EFFECTS from argued into measured for
two styles, because it records the SAME people walking normally, with a bag, and
in a coat. Paired within subject, so between-person variation cancels.

The silhouettes are 64x64, size-normalised and centred, and that normalisation
is destructive: stature, step length in metres and body sway do not survive it.
So the tests pin what is measurable and, just as importantly, that nothing is
reported in metres — a number in metres from this source would be invented.
"""

from __future__ import annotations

import numpy as np
import pytest

from cctvsec.gait.casia import (
    CONDITIONS,
    FPS,
    SIDE_VIEW,
    SequenceGait,
    cadence_from_spread,
    frame_features,
    paired_effects,
)
from survsim.gait.signature import MEASURED_STYLES, STYLE_EFFECTS


def _silhouette(leg_gap: int = 10, lean: int = 0, size: int = 64) -> np.ndarray:
    """A crude standing figure: torso block over two legs."""
    mask = np.zeros((size, size), dtype=bool)
    centre = size // 2 + lean
    mask[10:40, centre - 8:centre + 8] = True            # torso
    mask[40:62, centre - leg_gap // 2 - 2:centre - leg_gap // 2 + 2] = True
    mask[40:62, centre + leg_gap // 2 - 2:centre + leg_gap // 2 + 2] = True
    return mask


# --------------------------------------------------------------- features


def test_wider_legs_give_a_larger_leg_spread() -> None:
    narrow = frame_features(_silhouette(leg_gap=4))
    wide = frame_features(_silhouette(leg_gap=20))
    assert narrow is not None and wide is not None
    assert wide[0] > narrow[0]


def test_a_symmetric_figure_has_near_zero_asymmetry() -> None:
    _spread, asym = frame_features(_silhouette(leg_gap=12))
    assert abs(asym) < 0.2


def test_an_empty_silhouette_is_refused_rather_than_guessed() -> None:
    assert frame_features(np.zeros((64, 64), dtype=bool)) is None


def test_a_near_empty_silhouette_is_refused() -> None:
    mask = np.zeros((64, 64), dtype=bool)
    mask[30:33, 30:33] = True
    assert frame_features(mask) is None


# ---------------------------------------------------------------- cadence


def test_a_known_oscillation_gives_the_expected_cadence() -> None:
    """Leg spread peaks once per step, so one oscillation is one step."""
    steps_per_second = 2.0                       # 120 steps/min
    n = 100
    t = np.arange(n) / FPS
    signal = 0.5 + 0.2 * np.sin(2 * np.pi * steps_per_second * t)

    assert cadence_from_spread(signal, FPS) == pytest.approx(120.0, abs=10.0)


def test_a_flat_signal_yields_no_cadence() -> None:
    """A standing person must not be reported as walking."""
    assert cadence_from_spread(np.full(60, 0.5), FPS) == 0.0


def test_too_few_frames_yields_no_cadence() -> None:
    assert cadence_from_spread([0.1, 0.9, 0.1], FPS) == 0.0


# ------------------------------------------------------- paired effects


def _seq(subject, condition, cadence, spread=1.0, asym=0.0):
    return SequenceGait(subject=subject, condition=condition, view=SIDE_VIEW,
                        cadence_spm=cadence, leg_spread=spread,
                        asymmetry=asym, n_frames=50)


def test_effects_are_measured_against_the_same_person_walking_normally() -> None:
    """Pairing within subject is the whole value of this dataset."""
    data = [_seq("a", "nm", 100.0, 1.0, 0.0), _seq("a", "bg", 120.0, 1.0, 0.05),
            _seq("b", "nm", 50.0, 1.0, 0.0), _seq("b", "bg", 60.0, 1.0, 0.05)]
    effects = paired_effects(data)

    # Both subjects sped up by 20% despite very different absolute cadences.
    assert effects["bg"]["cadence_ratio"] == pytest.approx(1.2, rel=1e-6)
    assert effects["bg"]["n_subjects"] == 2


def test_a_subject_with_no_normal_baseline_is_skipped() -> None:
    """Without a baseline there is nothing to measure an effect against."""
    data = [_seq("a", "nm", 100.0), _seq("a", "bg", 120.0), _seq("b", "bg", 99.0)]
    assert paired_effects(data)["bg"]["n_subjects"] == 1


def test_asymmetry_is_reported_as_a_delta_not_a_ratio() -> None:
    """A normal walk's asymmetry is near zero; dividing by it produces noise."""
    data = [_seq("a", "nm", 100.0, 1.0, 0.001), _seq("a", "bg", 100.0, 1.0, 0.041)]
    effects = paired_effects(data)

    assert "asymmetry_delta" in effects["bg"]
    assert effects["bg"]["asymmetry_delta"] == pytest.approx(0.040, abs=1e-6)


def test_no_measurements_produce_no_effects_rather_than_zeros() -> None:
    assert paired_effects([]) == {}


def test_the_three_conditions_are_the_ones_casia_b_records() -> None:
    assert set(CONDITIONS) == {"nm", "bg", "cl"}


def test_the_side_view_is_used_because_gait_needs_lateral_motion() -> None:
    """At 000 or 180 degrees the legs barely separate horizontally."""
    assert SIDE_VIEW == "090"


# ------------------------------------------ what the measurement changed


def test_measured_styles_are_marked_as_such() -> None:
    """A reader should be able to tell which rows carry evidence."""
    assert {"normal", "carrying_bag", "heavy_coat"} <= MEASURED_STYLES
    assert "limp_L" not in MEASURED_STYLES, "a limp is still argued, not measured"


def test_a_bag_makes_the_walk_asymmetric_but_a_coat_does_not() -> None:
    """The dissociation measured across 123-124 subjects (docs/14 §13).

    This is the empirical basis for gait surviving a clothing change: a coat
    alters appearance while leaving the symmetry of the walk untouched
    (-0.0001, z=-0.1), whereas a bag genuinely alters gait (+0.040, z=+9.9).
    So "wearing something different" and "carrying something" are different
    evasions, not one.
    """
    bag = STYLE_EFFECTS["carrying_bag"]["asymmetry"]
    coat = STYLE_EFFECTS["heavy_coat"]["asymmetry"]

    assert bag > 0.02, "a bag on one side makes the walk lopsided"
    assert coat == pytest.approx(0.0, abs=1e-6), "a coat does not"


def test_both_encumbrances_raise_cadence_and_shorten_the_step() -> None:
    """Measured: restricted movement means quicker, shorter steps."""
    for style in ("carrying_bag", "heavy_coat"):
        assert STYLE_EFFECTS[style]["cadence"] > 1.0
        assert STYLE_EFFECTS[style]["step"] < 1.0
