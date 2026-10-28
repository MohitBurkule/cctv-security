"""H53 sensor-fusion runner: gates drop twin alarms, PIDS keeps intruders, adversary arms bite."""
import json

import numpy as np
import pandas as pd

from cctvsec.experiments import load_config
from cctvsec.experiments import sensor_fusion as S


def _world(tmp_path):
    d = tmp_path / "recall_tracks"
    d.mkdir(parents=True)
    t = np.arange(0, 300, 0.2)
    rows = []
    # twin enters the 10x10 zone at x=0 around t=20; intruder at t=200 (far apart in time and space)
    for uid, t_in in (("g000", 20.0), ("p1", 200.0)):
        x = np.where(t < t_in, -5 + (t - (t_in - 5)).clip(0), 0 + (t - t_in).clip(0, 5) + 0.01)
        y = np.full_like(t, 35.0 if uid == "p1" else 2.0)
        rows.append(pd.DataFrame({"t": t, "uid": uid, "x": x, "y": y}))
    pd.concat(rows).to_parquet(d / "probe_0000.parquet", index=False)
    meta = {"zones": [{"id": "zone.r", "tag": "restricted", "polygon": [[0, 0], [10, 0], [10, 40], [0, 40]]}],
            "actors": ["p1"], "narratives": {"g000": "patrol_guard", "p1": "probe"}}
    (d / "probe_0000.json").write_text(json.dumps(meta))
    return {"mode": "recall", "kind": "probe", "i": 0, "camera_hours": 1 / 12,
            "truth": [{"t": 200.0, "actor": "p1"}],
            "noisy": {"C": [[206.0, "p1", "person", "incident"], [26.0, "g000", "person", "patrol_guard"]]}}


def test_fusion_gates(tmp_path):
    cfg = load_config("h53_sensor_fusion")
    cfg["h40b_dir"] = str(tmp_path)
    cfg["gate_log"] = {**cfg["gate_log"], "p_swipe": 1.0}
    cfg["rf"] = {**cfg["rf"], "p_carry": 1.0, "miss_p": 0.0}
    cfg["pids"] = {**cfg["pids"], "p_detect": 1.0, "wind_per_zone_h": 0.0}
    r = S.fuse_world(_world(tmp_path), cfg, 300.0)["fused"]
    who = {v: {a: [x[1] for x in r[v]["alarms"][a]] for a in S.ARMS} for v in r}
    b = who["base"]
    assert b["C"] == ["p1", "g000"]
    assert b["C+a"] == ["p1"] and b["C+b"] == ["p1"] and b["C+c"] == ["p1"] and b["C+abc"] == ["p1"]
    # tailgate: badge just before the intruder and no PIDS -> the badge gate and the combined rule lose him
    assert "p1" not in who["tailgate"]["C+a"] and "p1" not in who["tailgate"]["C+abc"]
    # stolen tag: RF alone loses him, PIDS override keeps him under the combined rule
    assert "p1" not in who["stolen_tag"]["C+b"] and "p1" in who["stolen_tag"]["C+abc"]


def test_entries_and_crossing():
    from cctvsec.experiments.line_cross import _polys
    sterile = _polys([{"id": "z", "tag": "restricted", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}],
                     {"restricted"})
    g = pd.DataFrame({"t": [0, 1, 2, 3, 4], "x": [-1, 0.5, 2, 0.5, 0.5], "y": [0.5] * 5})
    e = S.entries(g, sterile)
    assert e == [(1.0, 0), (3.0, 0)]
    assert S.crossing_for(e, 3.5) == (3.0, 0) and S.crossing_for(e, 0.5) is None
