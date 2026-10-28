"""Round 4 (docs/research/58 §8): H21 grid / H23 decision helpers in tools/loiter_eval.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_spec = importlib.util.spec_from_file_location(
    "loiter_eval", Path(__file__).resolve().parents[1] / "tools" / "loiter_eval.py")
LE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LE)


def test_h21_grid_is_25_log_points_on_calibrated_scale():
    g = LE.H21_GRID
    assert len(g) == 25 and g[0] == 0.01 and g[-1] == 0.5
    r = np.diff(np.log(g))
    assert np.allclose(r, r[0], rtol=1e-2)


def test_split_cfg_extra_train_seeds():
    assert LE.split_cfg("train")["seed"] == 58
    assert LE.split_cfg("train_s158") == {"seed": 158, "clean": 150, "recall": 300}
    with pytest.raises(KeyError):
        LE.split_cfg("bogus")


def test_stratified_fold_matches_round3_recipe():
    metas = [{"mode": "clean"}] * 150 + [{"mode": "recall"}] * 300
    sel = LE.stratified_fold(metas, 58)
    assert len(sel) == 45 + 90 and sel == sorted(sel)
    assert LE.stratified_fold(metas, 58) == sel and LE.stratified_fold(metas, 59) != sel


def test_paired_world_diff_zero_for_identical_arms():
    k = np.array([1.0, 0, 3, 2])
    ch = np.ones(4)
    d = LE.paired_world_diff(k, k, ch)
    assert d["diff"] == 0 and d["boot95"] == [0.0, 0.0]
    d = LE.paired_world_diff(k + 1, k, ch)
    assert d["diff"] == 1 and d["boot95"] == [1.0, 1.0]


def test_h23_decision_rules():
    # retrained wins 7/10 -> retrain; a recall < 0.80 arm loses its seed
    rows = [{"F": (3.0, 0.82), "R": (2.8, 0.82)}] * 7 + [{"F": (2.5, 0.82), "R": (2.8, 0.82)}] * 3
    d = LE.h23_decision(rows)
    assert d["policy"] == "retrain" and d["retrained_wins"] == 7 and d["A1"] == "typical"
    rows = [{"F": (3.0, 0.82), "R": (2.0, 0.79)}] * 10
    d = LE.h23_decision(rows)
    assert d["policy"] == "freeze" and d["retrained_at_or_below_A1"] == 0 and d["A1"] == "lucky"
    rows = [{"F": (3.0, 0.82), "R": (2.9, 0.82)}] * 5 + [{"F": (2.9, 0.82), "R": (3.0, 0.82)}] * 5
    assert LE.h23_decision(rows)["policy"] == "no-dominance"
