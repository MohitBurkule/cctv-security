"""Tests for measuring real walking statistics from CCTV ground truth.

The failure mode here is not a crash, it is a plausible wrong number. Speeds are
recovered by using each person's bounding box as a ruler, and every step of that
— the stature assumption, perspective, occlusion, frame-edge clipping — can bias
the result while leaving it looking like a walking speed.

So these tests build ground truth where the true speed is known by construction
and check it is recovered, then check each bias source is actually rejected.
The real-data tests at the end are skipped without MOT20.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from survsim.director.crowd import JAM_DENSITY_PER_M2, speed_for_density
from cctvsec.gait.extract import (
    ASSUMED_STATURE_M,
    MIN_VISIBILITY,
    GaitStats,
    fundamental_diagram,
    local_density,
    measure,
    measure_sequence,
)

W, H = 1920, 1080
FPS = 25.0


def _walker(track_id: int, speed_px_per_frame: float, box_h: float = 170.0,
            n_frames: int = 50, x0: float = 400.0, y0: float = 500.0,
            visibility: float = 1.0) -> list[dict]:
    """A person crossing the frame horizontally at a known pixel speed.

    Horizontal motion on purpose: it is perpendicular to the camera axis, so it
    is the one direction image-plane displacement measures without
    foreshortening.
    """
    rows = []
    for f in range(n_frames):
        rows.append({
            "frame": f, "id": track_id,
            "bbox": (x0 + speed_px_per_frame * f, y0, box_h / 3.0, box_h),
            "visibility": visibility, "score": 1.0,
        })
    return rows


# ------------------------------------------------------- speed recovery


def test_a_known_speed_is_recovered() -> None:
    """With a 170 px box and 1.7 m stature, 1 px = 1 cm exactly."""
    # 5 px/frame at 25 fps = 125 px/s = 1.25 m/s at this scale.
    rows = _walker(1, speed_px_per_frame=5.0, box_h=170.0)
    speeds, _, tracks = measure_sequence(rows, FPS, W, H)

    assert tracks == 1
    assert speeds.mean() == pytest.approx(1.25, abs=0.02)


def test_scale_follows_box_height_so_perspective_is_absorbed() -> None:
    """Someone further away has a smaller box AND moves fewer pixels.

    Both halve together, so the recovered metric speed must be unchanged. If it
    is not, distant people would be measured as walking slower purely for being
    distant.
    """
    near = measure_sequence(_walker(1, 6.0, box_h=200.0), FPS, W, H)[0]
    far = measure_sequence(_walker(2, 3.0, box_h=100.0), FPS, W, H)[0]
    assert near.mean() == pytest.approx(far.mean(), rel=0.02)


def test_stature_assumption_scales_the_answer_linearly() -> None:
    """Stated so the 4% per-person error from stature variation is explicit."""
    rows = _walker(1, 5.0, box_h=170.0)
    speed = measure_sequence(rows, FPS, W, H)[0].mean()
    assert speed == pytest.approx(1.25 * (ASSUMED_STATURE_M / 1.70), abs=0.02)


def test_frame_rate_is_honoured() -> None:
    rows = _walker(1, 5.0)
    fast = measure_sequence(rows, 50.0, W, H)[0].mean()
    slow = measure_sequence(rows, 25.0, W, H)[0].mean()
    assert fast == pytest.approx(2 * slow, rel=0.02)


# ------------------------------------------------------- rejecting bias


def test_occluded_boxes_are_rejected_because_their_height_is_wrong() -> None:
    """An occluded box understates stature, which inflates the speed."""
    rows = _walker(1, 5.0, visibility=MIN_VISIBILITY - 0.2)
    speeds, _, tracks = measure_sequence(rows, FPS, W, H)
    assert tracks == 0
    assert len(speeds) == 0


def test_boxes_clipped_at_the_frame_edge_are_rejected() -> None:
    """The true box extends past the edge, so the visible height is too short.

    The walker stays behind the edge for the whole clip; a speed slow enough to
    keep it there is still well above the walking floor, so any sample that
    appears would be the edge filter failing rather than the speed filter
    working.
    """
    rows = _walker(1, 0.5, x0=-60.0, n_frames=50)
    assert all(r["bbox"][0] < 0 for r in rows), "walker must stay clipped"
    assert len(measure_sequence(rows, FPS, W, H)[0]) == 0


def test_a_walker_emerging_from_the_edge_is_measured_once_fully_visible() -> None:
    """The complement: the filter must not discard a whole track for one bad frame."""
    rows = _walker(1, 5.0, x0=-50.0, n_frames=50)
    speeds, _, tracks = measure_sequence(rows, FPS, W, H)
    assert tracks == 1
    assert speeds.mean() == pytest.approx(1.25, abs=0.02)


def test_implausible_speeds_are_filtered_out() -> None:
    """Identity switches teleport a box and would otherwise read as a sprint."""
    rows = _walker(1, 500.0, box_h=170.0, x0=10.0)
    speeds, _, _ = measure_sequence(rows, FPS, W, H)
    assert len(speeds) == 0, "a 125 m/s 'walk' must not be counted"


def test_a_gap_in_a_track_is_not_measured_as_motion() -> None:
    """Treating an interrupted track as continuous invents a sprint."""
    rows = _walker(1, 5.0, n_frames=10)
    for r in rows[5:]:
        r["frame"] += 500          # long gap, then resumes far away
        r["bbox"] = (5000.0, 500.0, 56.0, 170.0)
    speeds, _, _ = measure_sequence(rows, FPS, W, H)
    assert all(s < 3.5 for s in speeds)


def test_a_stationary_person_contributes_no_walking_speed() -> None:
    rows = _walker(1, 0.0)
    speeds, _, _ = measure_sequence(rows, FPS, W, H)
    assert len(speeds) == 0, "zero motion is below the walking floor"


# ------------------------------------------------------------- density


def test_density_counts_neighbours_at_the_right_physical_scale() -> None:
    scale = ASSUMED_STATURE_M / 170.0                   # m per px
    radius_px = 3.0 / scale
    feet = np.array([[0.0, 0.0], [radius_px * 0.5, 0.0], [radius_px * 2.0, 0.0]])
    scales = np.full(3, scale)

    d = local_density(feet, scales, radius_m=3.0)
    # Person 0 has exactly one neighbour inside 3 m.
    assert d[0] == pytest.approx(1.0 / (np.pi * 9.0), rel=1e-6)


def test_density_counts_occluded_people_too() -> None:
    """The bug that made a crowded sequence read as free-flowing.

    A crowd is crowded precisely because its members occlude each other. Counting
    only the cleanly-visible ones understated MOT20 density by roughly an order
    of magnitude, and produced the contradiction of shuffling speeds at
    free-flow density.
    """
    scale = ASSUMED_STATURE_M / 170.0
    near = np.array([[10.0 * i, 0.0] for i in range(20)])
    feet = np.array([[0.0, 0.0]])
    scales = np.array([scale])

    counted_all = local_density(feet, scales, neighbour_feet=near)[0]
    counted_self_only = local_density(feet, scales)[0]
    assert counted_all > counted_self_only
    assert counted_all == pytest.approx(19 / (np.pi * 9.0), rel=1e-6)


def test_density_is_never_negative_for_a_lone_person() -> None:
    d = local_density(np.array([[0.0, 0.0]]), np.array([0.01]))
    assert d[0] == 0.0


def test_empty_input_is_handled() -> None:
    assert len(local_density(np.zeros((0, 2)), np.zeros(0))) == 0
    speeds, _dens, tracks = measure_sequence([], FPS, W, H)
    assert len(speeds) == 0 and tracks == 0


# ------------------------------------------------- the fundamental diagram


def test_diagram_bins_only_report_well_populated_bands() -> None:
    """A band with three samples is noise and must not appear as a data point."""
    speeds = np.concatenate([np.full(100, 1.2), np.full(3, 0.2)])
    dens = np.concatenate([np.full(100, 0.1), np.full(3, 3.0)])
    out = fundamental_diagram(speeds, dens, min_samples=30)
    assert len(out) == 1
    assert out[0][1] == pytest.approx(1.2)


def test_our_model_reproduces_the_shape_measured_from_real_crowds() -> None:
    """The check that validates `speed_for_density` against real footage.

    Measured on 206k samples from MOT20 (see docs/14). Absolute speed is not
    compared — image-plane measurement foreshortens motion along the camera
    axis — but the *shape* is scale-free and therefore comparable.
    """
    measured = [(0.15, 0.642), (0.55, 0.555), (1.15, 0.475), (2.00, 0.411)]
    base_d, base_s = measured[0]
    ours_base = speed_for_density(1.34, base_d)

    for density, speed in measured:
        measured_ratio = speed / base_s
        model_ratio = speed_for_density(1.34, density) / ours_base
        assert abs(measured_ratio - model_ratio) < 0.10, (
            f"at {density}/m^2 the model shape departs from measurement")


def test_jam_density_is_a_parameter_not_a_buried_constant() -> None:
    """It was measured at 4.53 on MOT20; the default stays at the literature 5.4."""
    assert JAM_DENSITY_PER_M2 == 5.4
    tighter = speed_for_density(1.34, 2.0, jam_density=4.53)
    looser = speed_for_density(1.34, 2.0, jam_density=5.4)
    assert tighter < looser


def test_speed_never_goes_negative_whatever_the_jam_density() -> None:
    assert speed_for_density(1.34, 50.0, jam_density=4.53) > 0.0


# ------------------------------------------------------------- real data


MOT_ROOT = Path.home() / "data" / "mot" / "extracted"
_SEQS = sorted(MOT_ROOT.glob("MOT20/train/MOT20-*")) if MOT_ROOT.is_dir() else []


@pytest.mark.skipif(not _SEQS, reason="MOT20 not downloaded")
def test_real_measurement_produces_a_monotonic_fundamental_diagram() -> None:
    """Real people really do slow down as it gets busier — our core assumption."""
    stats = measure(_SEQS[:1])
    assert isinstance(stats, GaitStats)
    assert stats.n_samples > 1000

    diagram = [(d, s) for d, s, n in stats.diagram if n >= 500]
    if len(diagram) >= 2:
        speeds = [s for _, s in diagram]
        assert speeds[0] > speeds[-1], "speed should fall as density rises"


@pytest.mark.skipif(not _SEQS, reason="MOT20 not downloaded")
def test_real_measurement_reports_its_caveats() -> None:
    """The cadence limitation must travel with the numbers, not live in a doc."""
    note = measure(_SEQS[:1]).as_dict()["note"]
    assert "cadence" in note and "pose estimation" in note
