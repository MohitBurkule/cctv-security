"""M1: our HOTA/CLEAR/Identity match the reference TrackEval (docs/13 "TrackEval parity").

Skipped when TrackEval is not installed
(`pip install git+https://github.com/JonathonLuiten/TrackEval.git`).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(importlib.util.find_spec("trackeval") is None, reason="TrackEval not installed"),
]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _check(group, tol):
    import trackeval_parity as tp

    res = tp.score(group)
    for seq, r in res.items():
        for k, d in r["delta_ours"].items():
            assert abs(d) < tol, f"{seq}.{k}: ours {r['ours'][k]} vs TrackEval {r['trackeval'][k]}"


def test_edge_cases_match_trackeval_exactly():
    import trackeval_parity as tp

    _check(tp.edge_cases(), 1e-12)


def test_mot20_subset_matches_trackeval():
    import trackeval_parity as tp

    if not (ROOT / "out/datasets/mot20_sub/baselines/detections.json").is_file():
        pytest.skip("MOT20 subset cache (out/datasets/mot20_sub) not present")
    try:
        group = tp.mot20_subset()
    except FileNotFoundError as e:
        pytest.skip(f"MOT20 data missing: {e}")
    _check(group, 1e-9)
