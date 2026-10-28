"""H47 runner: scenario arms, statistics, gate parsing (32 §H47)."""
import numpy as np
import pytest

from cctvsec.experiments import evasion as ev


def test_arms_share_spawn_side_and_seed():
    c, w = ev.scenario("control", 1), ev.scenario("wall_hugging", 1)
    assert c["seed"] == w["seed"] == 1
    assert [s["pos"][0] for s in c["environment"]["spawn_points"]] == \
        [s["pos"][0] for s in w["environment"]["spawn_points"]]
    assert all(abs(s["pos"][1]) > 14 for s in w["environment"]["spawn_points"])
    assert ev.scenario("slow_deliberate", 1)["population"]["hero"][0]["gait"]["speed_mps"] < 1.0
    assert ev.run_of("hivis") == "control" and ev.run_of("crowd_cover") == "crowd_cover"


def test_bootstrap_detects_drop_and_not_null():
    rng = np.random.default_rng(0)
    ctrl = {(1, "a"): np.column_stack([rng.binomial(4, 0.8, 300), np.full(300, 4)]).astype(float)}
    low = {(1, "a"): np.column_stack([rng.binomial(4, 0.5, 300), np.full(300, 4)]).astype(float)}
    d = ev.bootstrap_delta(low, ctrl, 500)
    assert d["delta"] < -0.2 and d["hi"] < 0 and d["p_one_sided"] < 0.01
    same = ev.bootstrap_delta(ctrl, ctrl, 500)
    assert same["delta"] == 0 and same["lo"] <= 0 <= same["hi"]


def test_bootstrap_clip_vs_frame_cluster():
    """Frames within a clip perfectly correlated (clip-level coin flip broadcast to all
    frames): the frame-level bootstrap treats each frame as an independent draw and gives
    a too-narrow CI, while the clip-cluster bootstrap (the new default) correctly widens
    to reflect that there are really only a handful of independent clips (AUDIT_H47 §2)."""
    rng = np.random.default_rng(0)
    n_clips = 6
    ctrl, low = {}, {}
    for c in range(n_clips):
        ctrl[(c, "a")] = np.column_stack([np.full(200, 4), np.full(200, 4)]).astype(float)
        # each clip's hit rate is fixed per-clip (perfectly correlated frames within it)
        clip_tp = rng.choice([1, 4])
        low[(c, "a")] = np.column_stack([np.full(200, clip_tp), np.full(200, 4)]).astype(float)
    frame_ci = ev.bootstrap_delta(low, ctrl, 1000, cluster="frame")
    clip_ci = ev.bootstrap_delta(low, ctrl, 1000, cluster="clip")
    frame_width = frame_ci["hi"] - frame_ci["lo"]
    clip_width = clip_ci["hi"] - clip_ci["lo"]
    assert clip_width > 3 * frame_width
    assert clip_ci["delta"] == frame_ci["delta"]
    with pytest.raises(ValueError):
        ev.bootstrap_delta(low, ctrl, 10, cluster="bogus")


def test_holm_and_verdict():
    adj = ev.holm({"a": 0.01, "b": 0.02, "c": 0.5})
    assert np.isclose(adj["a"], 0.03) and np.isclose(adj["b"], 0.04) and adj["c"] == 0.5
    deltas = {"a": {"delta": -0.2}, "b": {"delta": -0.05}, "c": {"delta": -0.3}}
    v = ev.verdict(deltas, adj)
    assert v["counted"] == ["a"] and v["need"] == 2 and not v["met"]


def test_gate_and_visible_mot(tmp_path):
    (tmp_path / "check_render.txt").write_text("x\nPASS: 0 failed of 22 checks in 1s\n")
    assert ev.gate_passed(tmp_path)
    (tmp_path / "check_render.txt").write_text("FAIL: 1 failed of 22 checks\n")
    assert not ev.gate_passed(tmp_path)
    m = tmp_path / "mot.txt"
    m.write_text("1,1,10,10,5,30,1,1,1\n1,2,0,0,5,30,0,0,0\n")
    assert ev.read_visible_mot(m) == {1: [[10.0, 10.0, 5.0, 30.0]]}
    hits = ev.frame_hits(ev.read_visible_mot(m), {1: ([[10, 10, 5, 30]], [0.9])})
    assert hits == [(1, 1)]
