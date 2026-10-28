"""H3c runner: exact H3 arm, native scales, >=20 px collapse, decision and hard negative."""
from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments.far_field_h3c import collapse, decide_h3c, native_scale


def test_config_is_h3_arm_exactly():
    cfg = load_config("h3c_tiling_arms")
    assert RUNNERS[cfg["runner"]] == "far_field_h3c"
    m = {x["name"]: x for x in cfg["methods"]}
    assert cfg["methods"][0]["name"] == "full_1280"
    h3 = {x["name"]: x for x in load_config("h3_farfield")["methods"]}["sahi_320x240"]
    a = m["tiles_2p0x_320x240"]
    for k in ("imgsz", "tile", "overlap", "tile_imgsz"):
        assert a[k] == h3[k]
    assert native_scale(a["tile"][0]) == 2.0
    assert abs(native_scale(m["tiles_1p5x_427x320"]["tile"][0]) - 1.5) < 0.01
    assert cfg["block"] == 30 and cfg["primary_min_px"] == 20


def test_collapse_ge20():
    c = {"a": {("s", 0): {"hit": [1, 2, 3, 0], "n": [4, 5, 6, 1], "tp": 6, "fp": 0}}}
    assert collapse(c, 1)["a"][("s", 0)]["hit"] == [1, 5] and collapse(c, 1)["a"][("s", 0)]["n"] == [4, 12]


def _res(d, ap):
    return {"far": {"primary_ge20": {"delta_vs_full_1280": {"tiles_2p0x_320x240": d,
                                                            "tiles_1p5x_427x320": [0, 0, 0]}}},
            "near": {"ap50_all": {"full_1280": {"AP50": 0.9}, "tiles_2p0x_320x240": {"AP50": ap},
                                  "tiles_1p5x_427x320": {"AP50": 0.9}}}}


def test_decision_and_hard_negative():
    assert decide_h3c(_res([0.06, 0.01, 0.1], 0.9), {})["decision_met"]
    assert not decide_h3c(_res([0.06, -0.01, 0.1], 0.9), {})["decision_met"]   # CI touches 0
    assert not decide_h3c(_res([0.04, 0.01, 0.1], 0.9), {})["decision_met"]    # below margin
    assert not decide_h3c(_res([0.06, 0.01, 0.1], 0.84), {})["HN_near_ap50_drop_ok"]["tiles_2p0x_320x240"]
