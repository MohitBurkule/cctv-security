"""Metric paths of the baseline harness on tiny synthetic fixtures (no GPU, no model)."""
from __future__ import annotations

import json

import numpy as np
import pytest

from cctvsec.baselines.bytetrack import track_sequence
from cctvsec.baselines.run import (
    NonCommercialDatasetError,
    eval_det,
    eval_mot,
    markdown,
    reid_protocol,
    run_baselines,
)
from survsim.datasets.build import load_manifest, read_gt, split_for_seed
from cctvsec.eval.tracking import evaluate_mot, evaluate_reid

pytest.importorskip("pycocotools")


def _walkers(n_frames=20):
    # two people walking right, one row per frame each
    return [{"frame": f, "id": i, "bbox": [10 + 5 * f + 200 * i, 50, 30, 80], "vis": 1.0}
            for f in range(1, n_frames + 1) for i in (1, 2)]


def _dataset(tmp_path, rows, ignore_rows=()):
    lines = [f"{r['frame']},{r['id']},{','.join(map(str, r['bbox']))},1,1,1.0" for r in rows]
    lines += [f"{r['frame']},99,{','.join(map(str, r['bbox']))},0,8,1.0" for r in ignore_rows]
    (tmp_path / "gt.txt").write_text("\n".join(lines))
    frames = sorted({r["frame"] for r in rows})
    m = {"kind": "test", "synthetic_topdown": True, "runs": [{"name": "r", "cameras": {"c": {
        "gt": "gt.txt", "fps": 10.0, "resolution": [640, 480],
        "frames": {str(f): f"{f}.jpg" for f in frames}}}}]}
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    return load_manifest(tmp_path)


def test_read_gt_splits_targets_and_ignore(tmp_path):
    (tmp_path / "g.txt").write_text("1,1,0,0,10,20,1,1,0.9\n1,2,0,0,10,20,0,8,1\n1,3,0,0,10,20,1,5,1\n")
    t, ig = read_gt(tmp_path / "g.txt")
    assert [r["id"] for r in t] == [1] and [r["id"] for r in ig] == [2]


def test_split_is_by_seed():
    assert [split_for_seed(i, 4) for i in range(4)] == ["train", "train", "val", "test"]
    assert split_for_seed(0, 1) == "test"


def test_perfect_detections_score_ap_one(tmp_path):
    rows = _walkers()
    m = _dataset(tmp_path, rows)
    dets = {"r/c": {}}
    for r in rows:
        dets["r/c"].setdefault(r["frame"], []).append({"bbox": r["bbox"], "score": 0.9})
    res = eval_det(m, dets)
    assert res["all"]["AP50"] == pytest.approx(1.0, abs=1e-3)
    assert res["operating_point"]["precision"] == 1.0


def test_detection_on_ignore_region_is_not_a_false_positive(tmp_path):
    rows = _walkers(5)
    ignore = [{"frame": f, "bbox": [500, 300, 30, 80]} for f in range(1, 6)]
    m = _dataset(tmp_path, rows, ignore)
    dets = {"r/c": {}}
    for r in rows + [dict(i, id=0) for i in ignore]:
        dets["r/c"].setdefault(r["frame"], []).append({"bbox": r["bbox"], "score": 0.9})
    assert eval_det(m, dets)["all"]["AP50"] == pytest.approx(1.0, abs=1e-3)


def test_bytetrack_keeps_identities_and_scores_perfectly(tmp_path):
    rows = _walkers()
    dets = {}
    for r in rows:
        dets.setdefault(r["frame"], []).append({"bbox": r["bbox"], "score": 0.9})
    tracks = track_sequence(dets, range(1, 21))
    res = evaluate_mot(rows, tracks)
    assert res.id_switches == 0
    assert res.idf1 > 0.9          # first frame is lost to confirmation
    m = _dataset(tmp_path, rows)
    assert eval_mot(m, {"r/c": dets})["all"]["id_switches"] == 0


def test_bytetrack_low_score_detections_bridge_a_dip():
    dets = {f: [{"bbox": [10 + 5 * f, 50, 30, 80], "score": 0.3 if 8 <= f <= 10 else 0.9}]
            for f in range(1, 21)}
    ids = {t["id"] for t in track_sequence(dets, range(1, 21))}
    assert len(ids) == 1
    frames = {t["frame"] for t in track_sequence(dets, range(1, 21))}
    assert {8, 9, 10} <= frames          # the second, low-score stage held the track


def test_reid_protocol_cross_camera_and_cross_time():
    items = [("a", "c1", 1, "", None, 10), ("a", "c2", 1, "", None, 10),
             ("b", "c1", 1, "", None, 10), ("b", "c2", 1, "", None, 10)]
    pids, excl, mode = reid_protocol(items)
    assert mode == "cross-camera" and excl[0, 2] and not excl[0, 1]
    feats = np.array([[1, 0], [1, 0.1], [0, 1], [0.1, 1]], float)
    res = evaluate_reid(pids, pids, feats @ feats.T, exclude=excl | np.eye(4, dtype=bool))
    assert res.rank1 == 1.0
    single = [("a", "c", 1, "", None, 10), ("a", "c", 100, "", None, 10), ("a", "c", 3, "", None, 10)]
    _, ex, mode = reid_protocol(single)
    assert mode.startswith("cross-time") and ex[0, 2] and not ex[0, 1]


def test_markdown_flags_synthetic():
    r = {"dataset": "/x/ds", "synthetic_topdown": True, "n_sequences": 1, "n_frames": 1,
         "detector": "y", "imgsz": 640}
    assert "synthetic_topdown" in markdown(r)


def test_markdown_prints_internal_evidence_only_banner_when_noncommercial():
    r = {"dataset": "/x/ds", "synthetic_topdown": False, "n_sequences": 1, "n_frames": 1,
         "detector": "y", "imgsz": 640, "commercial_ml_ok": False,
         "asset_licences": ["LicenseRef-Epic-MetaHuman"]}
    out = markdown(r)
    assert "INTERNAL EVIDENCE ONLY" in out
    assert "LicenseRef-Epic-MetaHuman" in out


def test_markdown_omits_banner_when_commercial_ml_ok():
    r = {"dataset": "/x/ds", "synthetic_topdown": False, "n_sequences": 1, "n_frames": 1,
         "detector": "y", "imgsz": 640, "commercial_ml_ok": True, "asset_licences": ["CC0-1.0"]}
    assert "INTERNAL EVIDENCE ONLY" not in markdown(r)


def test_run_baselines_refuses_noncommercial_dataset_without_flag(tmp_path):
    """docs/research/47: a dataset built from non-commercial/unlicensed assets
    (e.g. MetaHuman, or MOT20) must not silently produce baseline numbers."""
    m = {"kind": "test", "synthetic_topdown": False, "commercial_ml_ok": False,
         "asset_licences": ["LicenseRef-Epic-MetaHuman"], "runs": []}
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(NonCommercialDatasetError):
        run_baselines(tmp_path, "det")


def test_run_baselines_allow_noncommercial_flag_permits_it(tmp_path):
    m = {"kind": "test", "synthetic_topdown": False, "commercial_ml_ok": False,
         "asset_licences": ["LicenseRef-Epic-MetaHuman"], "runs": []}
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    res = run_baselines(tmp_path, "det", allow_noncommercial=True)
    assert res["commercial_ml_ok"] is False
    assert res["n_sequences"] == 0
