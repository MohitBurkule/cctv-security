"""H54 runner: generated tailgater loses to badge/RF gates, the gate counter keeps him; est vs true matching."""
import numpy as np

from cctvsec.experiments import load_config
from cctvsec.experiments import sensor_fusion as S


def test_entries_xy():
    from cctvsec.experiments.line_cross import _polys
    sterile = _polys([{"id": "z", "tag": "restricted", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}], {"restricted"})
    e = S.entries_xy(np.array([-1, 0.5, 2, 0.5]), np.array([0.5] * 4), np.arange(4.0), sterile)
    assert [(t, z) for t, z, _, _ in e] == [(1.0, 0), (3.0, 0)] and e[0][2:] == (0.5, 0.5)


def test_h54_config_keeps_h53():
    c53, c54 = load_config("h53_sensor_fusion"), load_config("h54_tailgate_fusion")
    assert not c53.get("h54") and c54["h54"]
    for k in ("gate_log", "rf", "pids"):
        assert c54[k] == c53[k]


def test_tailgate_world_gates(tmp_path):
    cfg = load_config("h54_tailgate_fusion")
    cfg["recall_cache"] = str(tmp_path / "rec")
    cfg["gate_log"] = {**cfg["gate_log"], "p_swipe": 1.0}
    cfg["rf"] = {**cfg["rf"], "p_carry": 1.0, "miss_p": 0.0}
    cfg["gate_counter"] = {**cfg["gate_counter"], "p_count": 1.0}
    cfg["pids"] = {**cfg["pids"], "wind_per_zone_h": 0.0}
    r = S.fuse_world_h54({"mode": "recall", "kind": "tailgate", "i": 0}, cfg)
    assert r["tailgate_log"] and r["truth"]
    actor = r["truth"][0]["actor"]
    for m in S.MATCHES:
        f = r["fused"]["base"][m]
        who = {a: [x[1] for x in f[a]] for a in S.H54_ARMS}
        assert actor in who["C"]
        # badge (and the leader's tag) hide the tailgater; no fence PIDS on a gate entry
        assert actor not in who["C+a"] and actor not in who["C+abc"] and actor not in who["C+c"]
        # the gate counter sees two bodies on one badge
        assert actor in who["C+abcg"]
