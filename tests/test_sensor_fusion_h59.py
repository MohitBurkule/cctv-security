"""H59: identity-switch noise stage for the H54 fusion pipeline."""
import numpy as np
import pandas as pd

from cctvsec.experiments import line_cross as LC
from cctvsec.experiments import load_config
from cctvsec.experiments import sensor_fusion as S


def _pair_df():
    t = np.round(np.arange(0, 10, 0.2), 1)
    a = pd.DataFrame({"t": t, "uid": "a", "x": t * 0.1, "y": 0.0})
    b = pd.DataFrame({"t": t, "uid": "b", "x": t * 0.1, "y": 1.0})
    c = pd.DataFrame({"t": t, "uid": "c", "x": 50.0, "y": 50.0})
    return pd.concat([a, b, c], ignore_index=True)


def test_close_pairs_exposure():
    cp, ts, ps = LC.close_pairs(_pair_df(), {"a", "b", "c"}, 2.0)
    assert {(u, v) for _, u, v in cp} == {("a", "b")}
    assert abs(ts - 150 * 0.2) < 1e-9 and abs(ps - 50 * 0.2) < 1e-9


def test_id_switch_swaps_labels_only_between_close_people():
    df = _pair_df()
    out, n = LC.id_switch(df, 1e9, 2.0, {"a", "b", "c"}, np.random.default_rng(0))
    assert n == 50                                   # p = 1 every tick: swap every tick
    assert (out["body"] == df["uid"]).all()          # bodies (true positions) untouched
    assert (out.loc[out["body"] == "c", "uid"] == "c").all()
    first = out[out["t"] == 0.0].set_index("body")["uid"]
    assert first["a"] == "b" and first["b"] == "a"
    none, n0 = LC.id_switch(df, 0.0, 2.0, {"a", "b", "c"}, np.random.default_rng(0))
    assert n0 == 0 and (none["uid"] == none["body"]).all()


def test_calibrate_h():
    ex = [{"track_s": 3600.0, "pair_s": 100.0}, {"track_s": 3600.0, "pair_s": 0.0}]
    h = S.calibrate_h(ex, 0.04)
    # expected swaps = h * pair_s = rho * track_s / 2
    assert abs(h * 100.0 - 0.04 * 7200 / 2) < 1e-9


def test_h59_config_keeps_h54():
    c54, c59 = load_config("h54_tailgate_fusion"), load_config("h59_idsw_fusion")
    for k in ("gate_log", "rf", "pids", "gate_counter", "noise", "arms", "n_clean", "recall"):
        assert c59[k] == c54[k]
    assert c59["h59"]["arms"]["benign"] == 0.0 and abs(c59["h59"]["rho_idsw_per_track_s"] - 83.4 / 1904.6) < 1e-5


def test_benign_reproduces_h54():
    cfg = load_config("h54_tailgate_fusion")
    w = {"mode": "recall", "kind": "tailgate", "i": 3}
    r0 = S.fuse_world_h54(w, cfg)
    r1 = S.fuse_world_h54(w, cfg, {"h": 0.0, "seed": 0, "r_m": 2.0})
    assert r0["fused"]["base"]["est"] == r1["fused"]["base"]["est"] and r1["n_swap"] == 0


def test_with_positions_is_additive_only(tmp_path):
    """`with_positions=False` (the default) must reproduce the exact result of
    every existing caller; `with_positions=True` (H62, docs/research/32) adds
    (est_pos, true_pos) to each kept alarm row and a `pos` to each truth event,
    without changing which alarms/events are present."""
    cfg = load_config("h54_tailgate_fusion")
    w = {"mode": "recall", "kind": "tailgate", "i": 3}
    h59 = {"h": 1e6, "seed": 0, "r_m": 2.0}  # force swaps, like AUDIT_H59's own probe
    plain = S.fuse_world_h54(w, cfg, h59)
    posed = S.fuse_world_h54(w, cfg, h59, with_positions=True)
    for arm in S.H54_ARMS:
        base_rows = [r[:4] for r in posed["fused"]["base"]["est"][arm]]
        assert base_rows == plain["fused"]["base"]["est"][arm]
        for row in posed["fused"]["base"]["est"][arm]:
            assert len(row) == 7  # ..., est_pos, actor_pos_now, body
            assert isinstance(row[5], dict)
    assert len(posed["truth"]) == len(plain["truth"])
    for ev in posed["truth"]:
        assert "pos" in ev
    if posed["truth"]:
        assert posed["truth"][0]["pos"] is None or isinstance(posed["truth"][0]["pos"], tuple)
