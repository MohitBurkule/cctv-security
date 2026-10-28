"""Mask-derived GT boxes (survsim.gt.mask_boxes) and the box-tightness gate."""
import json

import numpy as np
import pytest

from cctvsec.checks.box_tightness import check_box_tightness
from survsim.gt.mask_boxes import boxes_from_ids, build_tight_gt, decode_ids, encode_ids


@pytest.mark.parametrize("srgb", [False, True])
def test_decode_roundtrip_all_ids(srgb):
    ids = np.arange(216).reshape(12, 18)
    assert (decode_ids(encode_ids(ids, srgb=srgb)) == ids).all()


def test_box_is_tight_and_occlusion_truncated():
    idm = np.zeros((100, 200), int)
    idm[10:90, 20:40] = 1          # person 1: 80 px tall
    idm[30:95, 30:60] = 2          # person 2 in front, hides part of person 1
    b = boxes_from_ids(decode_ids(encode_ids(idm)))
    assert b[2]["bbox"] == (30.0, 30.0, 30.0, 65.0)
    assert b[1]["bbox"] == (20.0, 10.0, 20.0, 80.0)   # extent of what is still visible
    idm[:, 20:30] = 0                                  # left part occluded -> box shrinks
    assert boxes_from_ids(idm)[1]["bbox"][0] == 30.0


def test_noise_and_unknown_ids_dropped():
    idm = np.zeros((50, 50), int)
    idm[0, 0] = 7
    idm[10:20, 10:20] = 3
    assert set(boxes_from_ids(idm)) == {3}
    assert boxes_from_ids(idm, known={1}) == {}


def test_build_tight_gt(tmp_path):
    from PIL import Image
    run = tmp_path / "run"
    (run / "gt").mkdir(parents=True)
    (run / "meta").mkdir()
    (run / "meta" / "track_ids.json").write_text(json.dumps({"a": 1, "b": 2}))
    (run / "gt" / "mot_cam.txt").write_text("5,1,0,0,50,90,1,1,0.9\n5,2,100,0,10,10,1,1,0.5\n")
    (run / "gt" / "world.parquet").write_bytes(b"x")
    s = tmp_path / "set"
    (s / "mask" / "cam").mkdir(parents=True)
    idm = np.zeros((60, 120), int)
    idm[20:50, 10:20] = 1
    Image.fromarray(encode_ids(idm, srgb=True)).save(s / "mask" / "cam" / "0005.png")
    summ = build_tight_gt(s, run, {"a": 1, "b": 2})
    lines = (s / "gt" / "mot_cam.txt").read_text().splitlines()
    assert lines[0] == "5,1,10.00,20.00,10.00,30.00,1,1,0.900"
    assert lines[1].endswith(",0,1,0.000")            # no pixels -> ignored row
    assert (s / "gt" / "projected" / "mot_cam.txt").is_file()
    assert (s / "gt" / "world.parquet").is_file()
    assert summ["cameras"]["cam"]["mask_rows"] == 1


def test_tightness_thresholds():
    good = {"n_gt": 10, "iou_median": 0.8, "frac_iou_ge_0.7": 0.8, "d_top": {"median": 0.01}}
    assert not any(c.failed for c in check_box_tightness(good))
    loose = dict(good, d_top={"median": 0.072})         # H6(c) projected-hull GT
    assert [c.name for c in check_box_tightness(loose) if c.failed] == ["box_top_offset"]
    assert check_box_tightness(dict(good, iou_median=0.696))[0].failed


def test_blind_camera_gets_no_mask_only_rows(tmp_path):
    """Principle 2: a covered camera emits nothing, although the (tamper-free)
    render's ID mask still shows people there (showcase_all cam_02, docs/95)."""
    from PIL import Image
    run = tmp_path / "run"
    (run / "gt").mkdir(parents=True)
    (run / "meta").mkdir()
    (run / "meta" / "track_ids.json").write_text(json.dumps({"a": 1}))
    (run / "meta" / "scenario.resolved.json").write_text(json.dumps({"fps": 5}))
    (run / "gt" / "mot_cam.txt").write_text("")      # Director: blind -> no rows
    (run / "gt" / "camera_status.jsonl").write_text(
        json.dumps({"t": 1.0, "camera": "cam", "blind": True}) + "\n"
        + json.dumps({"t": 1.2, "camera": "cam", "blind": False}) + "\n")
    s = tmp_path / "set"
    (s / "mask" / "cam").mkdir(parents=True)
    idm = np.zeros((60, 120), int)
    idm[20:50, 10:20] = 1
    for f in (5, 6):
        Image.fromarray(encode_ids(idm, srgb=True)).save(s / "mask" / "cam" / f"{f:04d}.png")
    build_tight_gt(s, run, {"a": 1}, workers=1)
    frames = [ln.split(",")[0] for ln in (s / "gt" / "mot_cam.txt").read_text().splitlines()]
    assert frames == ["6"]
