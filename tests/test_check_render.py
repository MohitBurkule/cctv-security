"""Tests for the render verifier.

This tool exists because Movie Render Queue reported success=True and wrote 50
correctly-sized PNGs that were entirely black. Every signal short of the pixels
said the render worked. So the verifier's job is to distinguish "a file exists"
from "a picture exists", and these tests build each failure mode deliberately —
a verifier that cannot tell them apart is worth nothing.
"""

from __future__ import annotations

import cv2
import numpy as np

from tools.check_render import inspect


def _write(tmp_path, frames):
    for i, f in enumerate(frames):
        cv2.imwrite(str(tmp_path / f"f.{i:04d}.png"), f)
    return tmp_path


def _lit(seed=0, shift=0):
    rng = np.random.default_rng(seed)
    img = rng.integers(40, 200, (64, 96, 3), dtype=np.uint8)
    return np.roll(img, shift, axis=1)


def test_a_real_render_passes(tmp_path) -> None:
    _write(tmp_path, [_lit(0, s) for s in (0, 10, 20)])
    assert inspect(tmp_path)["verdict"] == "ok"


def test_all_black_frames_are_caught(tmp_path) -> None:
    """The exact failure that shipped as 'success=True' three times."""
    _write(tmp_path, [np.zeros((64, 96, 3), np.uint8) for _ in range(3)])
    report = inspect(tmp_path)

    assert report["verdict"] == "black"
    assert report["unique_values"] == 1
    assert "shader" in report["reason"]


def test_a_flat_colour_is_distinguished_from_black(tmp_path) -> None:
    """Different cause, different fix: camera in geometry, or no lights."""
    flat = np.full((64, 96, 3), 120, np.uint8)
    _write(tmp_path, [flat, flat])
    assert inspect(tmp_path)["verdict"] == "uniform"


def test_lit_but_frozen_frames_are_caught(tmp_path) -> None:
    """A render with no animation bound looks fine frame by frame."""
    frame = _lit(1)
    _write(tmp_path, [frame, frame, frame])
    report = inspect(tmp_path)

    assert report["verdict"] == "static"
    assert report["first_last_diff"] < 0.5


def test_an_empty_directory_is_reported_not_crashed_on(tmp_path) -> None:
    assert inspect(tmp_path)["verdict"] == "missing"


def test_undecodable_files_are_reported(tmp_path) -> None:
    (tmp_path / "f.0000.png").write_text("not an image")
    assert inspect(tmp_path)["verdict"] == "unreadable"


def test_resolution_is_reported_as_width_height(tmp_path) -> None:
    _write(tmp_path, [_lit(0, s) for s in (0, 12)])
    assert inspect(tmp_path)["resolution"] == [96, 64]


def test_only_ok_is_a_pass(tmp_path) -> None:
    """A caller gating on this must not treat 'black' as success."""
    _write(tmp_path, [np.zeros((64, 96, 3), np.uint8)] * 2)
    assert inspect(tmp_path)["verdict"] != "ok"


# ------------------------------------------------- multi-camera rig checks


def test_identical_camera_views_are_caught(tmp_path) -> None:
    """The silent failure checksums cannot see.

    MRQ ignores a job's camera unless the sequence has a camera cut track, so
    every camera renders the same view. The files still differ by AA noise, so
    a checksum comparison passes while an eight-camera rig is really one.
    """
    from tools.check_render import compare_cameras

    frame = _lit(3)
    for cam in ("cam_01", "cam_02"):
        d = tmp_path / cam
        d.mkdir()
        _write(d, [frame, frame, frame])

    report = compare_cameras(tmp_path)
    assert report["verdict"] == "duplicate_views"
    assert ("cam_01", "cam_02") in report["duplicates"]
    assert "CameraCutTrack" in report["reason"]


def test_genuinely_different_views_pass(tmp_path) -> None:
    from tools.check_render import compare_cameras

    for cam, seed in (("cam_01", 1), ("cam_02", 99)):
        d = tmp_path / cam
        d.mkdir()
        _write(d, [_lit(seed, s) for s in (0, 8, 16)])

    assert compare_cameras(tmp_path)["verdict"] == "ok"


def test_a_single_camera_rig_is_not_flagged(tmp_path) -> None:
    from tools.check_render import compare_cameras

    d = tmp_path / "cam_01"
    d.mkdir()
    _write(d, [_lit(0, s) for s in (0, 5)])
    assert compare_cameras(tmp_path)["verdict"] == "single_camera"
