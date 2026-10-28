"""`survsim dataset` on a tiny mock scenario and on a fake MOTChallenge tree."""
from __future__ import annotations

from pathlib import Path

import pytest

from survsim.datasets import build_dataset, from_motchallenge

SCENARIO = Path(__file__).resolve().parent.parent / "configs" / "scenarios" / "smoke_mock.yaml"


@pytest.mark.slow
def test_mock_dataset_manifest(tmp_path):
    pytest.importorskip("cv2")
    m = build_dataset([SCENARIO], 2, tmp_path, max_frames=5)
    assert m["synthetic_topdown"] is True
    assert [r["split"] for r in m["runs"]] == ["train", "test"]
    cam = next(iter(m["runs"][0]["cameras"].values()))
    assert len(cam["frames"]) == 5
    assert all((tmp_path / p).is_file() for p in cam["frames"].values())
    assert (tmp_path / m["runs"][0]["coco"]).is_file()


@pytest.mark.slow
def test_mock_dataset_manifest_records_commercial_ml_ok(tmp_path):
    """docs/research/47: the mock backend's own bodies are procedural (CC0-equivalent,
    LicenseRef-SurvSim-Procedural), so `survsim dataset` must record the set as
    usable for commercial ML rather than leaving licensing unrecorded."""
    pytest.importorskip("cv2")
    m = build_dataset([SCENARIO], 1, tmp_path, max_frames=3)
    assert m["commercial_ml_ok"] is True
    assert m["asset_licences"] == ["LicenseRef-SurvSim-Procedural"]
    assert m["runs"][0]["licences"]["commercial_ml_ok"] is True


def test_dataset_manifest_refuses_to_assume_ok_when_licences_json_is_missing(tmp_path, monkeypatch):
    """No licences.json at all (e.g. a hand-assembled or partially-copied set) must
    read as not commercial_ml_ok, never default to permissive."""
    from survsim.datasets.build import _read_licences

    lic = _read_licences(tmp_path, None, tmp_path / "runs" / "nope", "nope")
    assert lic["commercial_ml_ok"] is False
    assert lic["asset_licences"] == ["LicenseRef-Unknown"]


def test_motchallenge_wrapper(tmp_path):
    seq = tmp_path / "MOT" / "train" / "S-01"
    (seq / "gt").mkdir(parents=True)
    (seq / "gt" / "gt.txt").write_text("1,1,0,0,10,20,1,1,1\n")
    (seq / "seqinfo.ini").write_text("[Sequence]\nname=S-01\nimDir=img1\nframeRate=25\n"
                                     "seqLength=10\nimWidth=64\nimHeight=48\nimExt=.jpg\n")
    m = from_motchallenge(tmp_path / "MOT", tmp_path / "ds", max_frames=3)
    assert m["synthetic_topdown"] is False
    assert list(m["runs"][0]["cameras"]["S-01"]["frames"]) == ["1", "2", "3"]
    # MOT20 etc. are CC BY-NC-SA 3.0: internal validation only, never a sold-model number.
    assert m["commercial_ml_ok"] is False
