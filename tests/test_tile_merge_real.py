"""H3e helpers on synthetic numbers (no detector, no MOT20 needed)."""
import pytest

from cctvsec.experiments import RUNNERS
from cctvsec.experiments import tile_merge_real as tr


def test_registered():
    assert RUNNERS["tile_merge_real"] == "tile_merge_real"


def test_fp_cut_boot_point_and_ci():
    keys = [("s", i) for i in range(60)]
    blocks = [keys[:30], keys[30:]]
    cut = tr.fp_cut_boot({k: 4 for k in keys}, {k: 1 for k in keys}, blocks, 200, 0)
    assert cut[0] == pytest.approx(0.75) and cut[1] == pytest.approx(0.75) and cut[2] == pytest.approx(0.75)


def test_decision_thresholds():
    cfg = {"decision": {"fp_cut_min": 0.5, "recall_max_drop": 0.02, "hn_max_gain": 0.0}}
    res = {"fp_cut_d_vs_a": [0.6, 0.5, 0.7], "recall_delta_d_minus_a_all": [-0.01, -0.02, 0.0],
           "hn_ge80_delta_d_minus_1280": [0.01, -0.01, 0.03]}
    d = tr.decide_h3e(res, cfg)
    assert d["decision_met"] and not d["HN_tiles_not_better_ge80"]
    res["recall_delta_d_minus_a_all"] = [-0.03, -0.05, 0.0]
    assert not tr.decide_h3e(res, cfg)["decision_met"]
