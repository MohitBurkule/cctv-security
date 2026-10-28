"""Tests for measuring gait from reference mocap clips.

The headline result of this tool is a *refusal*, and that is what most of these
tests pin. Library animation clips are single-stride loops built for looping
playback, not for measurement: the Mixamo "Walking" clip is 1.4 s and contains
two step transitions. Any cadence computed from that is an artefact of where the
loop happens to start.

The other thing pinned here is the asymmetry metric. The first version compared
the positive and negative excursions of foot separation and returned exactly 0.0
for an unmistakable limp — a metric that cannot see the thing it exists to
measure. Asymmetry is now measured from step *timing*, because a limp is a
difference in how long each leg bears weight.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.measure_mocap_gait import MIN_TRANSITIONS, measure_clip


def _clip(name: str, n_frames: int, steps: float, fps: float = 30.0,
          duty: float = 0.5) -> dict:
    """A synthetic clip whose feet alternate `steps` times.

    `duty` is the fraction of each full cycle spent on the first half. 0.5 is a
    symmetric walk; 0.8 means one leg's half-cycle lasts four times as long as
    the other, which is what a pronounced limp looks like in timing.

    Built by walking a phase accumulator at two different rates rather than by
    perturbing a sine: a phase perturbation that vanishes at the zero crossings
    leaves the timing untouched, which is how the first version of this fixture
    silently tested nothing.
    """
    half_cycles = max(int(steps), 2)
    total = float(n_frames)
    # Alternate half-cycles get durations proportional to duty and 1-duty.
    weights = [duty if k % 2 == 0 else (1.0 - duty) for k in range(half_cycles)]
    scale = total / sum(weights)
    bounds, at = [], 0.0
    for w in weights:
        at += w * scale
        bounds.append(at)

    frames, k, start = [], 0, 0.0
    for i in range(n_frames):
        while k < len(bounds) - 1 and i >= bounds[k]:
            start = bounds[k]
            k += 1
        span = max(bounds[k] - start, 1e-6)
        local = (i - start) / span
        sep = np.sin(np.pi * local) * (1.0 if k % 2 == 0 else -1.0)
        frames.append({
            "foot_L": {"pos": [sep / 2, 0.0, 0.0], "rot": [0, 0, 0]},
            "foot_R": {"pos": [-sep / 2, 0.0, 0.0], "rot": [0, 0, 0]},
        })
    return {"name": name, "fps": fps, "n_frames": n_frames, "frames": frames}


def test_a_short_library_loop_is_refused_not_estimated() -> None:
    """The actual finding: a 1.4s single-stride loop cannot support a cadence."""
    result = measure_clip(_clip("Walking", n_frames=42, steps=2))

    assert result["reliable"] is False
    assert result["cadence_spm"] is None
    assert "too short" in result["reason"] or "transitions" in result["reason"]


def test_a_long_enough_clip_is_measured() -> None:
    result = measure_clip(_clip("Walking", n_frames=300, steps=10))
    assert result["reliable"] is True
    assert result["cadence_spm"] > 0


def test_cadence_scales_with_how_fast_the_feet_alternate() -> None:
    slow = measure_clip(_clip("slow", n_frames=300, steps=6))
    fast = measure_clip(_clip("fast", n_frames=300, steps=12))
    assert fast["cadence_spm"] > slow["cadence_spm"]


def test_a_symmetric_walk_has_near_zero_timing_asymmetry() -> None:
    result = measure_clip(_clip("Walking", n_frames=400, steps=12, duty=0.5))
    assert abs(result["asymmetry"]) < 0.05


def test_timing_asymmetry_detects_unequal_half_cycles() -> None:
    """The property the first, amplitude-based metric could not see at all."""
    even = measure_clip(_clip("even", n_frames=400, steps=12, duty=0.5))
    skewed = measure_clip(_clip("skewed", n_frames=400, steps=12, duty=0.8))
    assert abs(skewed["asymmetry"]) > abs(even["asymmetry"])


def test_the_refusal_threshold_is_stated_not_implicit() -> None:
    assert MIN_TRANSITIONS >= 4


def test_clip_metadata_is_reported_even_when_refused() -> None:
    """A refusal must still say what it looked at, or it cannot be debugged."""
    result = measure_clip(_clip("Walking", n_frames=42, steps=2))
    assert result["n_frames"] == 42
    assert result["duration_s"] == pytest.approx(1.4)
    assert result["n_transitions"] < MIN_TRANSITIONS
