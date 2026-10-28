"""Fast guard for tools/trackeval_parity.score(): every key it reads from
evaluate_mot must exist, and bridge-only keys (deta_mean/assa_mean, added by
2fdecd6) must not be looked up on TrackingResult (was KeyError 'deta_mean')."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def test_score_keys_exist_in_evaluate_mot_output():
    import trackeval_parity as tp

    from cctvsec.eval.tracking import evaluate_mot

    g = [{"frame": 1, "id": 1, "bbox": [0, 0, 10, 20]}]
    out = evaluate_mot(g, g).__dict__
    assert set(tp.KEYS) <= set(out)


def test_score_ignores_bridge_only_keys(monkeypatch):
    import trackeval_parity as tp

    fake = {"hota": 1.0, "deta": 1.0, "deta_mean": 1.0, "assa_mean": 1.0, "fragmentations": 0}
    monkeypatch.setattr(tp, "write_motchallenge", lambda *a, **k: None)
    monkeypatch.setattr(tp, "run_trackeval", lambda root: {"a": fake, "b": fake, "COMBINED": fake})
    g = [{"frame": 1, "id": 1, "bbox": [0, 0, 10, 20]}]
    res = tp.score({"a": (g, g), "b": (g, g)})
    assert "deta_mean" not in res["COMBINED"]["ours"]
    assert set(res["COMBINED"]["delta_ours"]) == {"hota", "deta"}
