"""H3b runner (far_field_cc0): registration, blocks, paired bootstrap, decision, licence gate."""
import json

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments.far_field_cc0 import block_bootstrap, check_licence, decide, make_blocks


def test_registered_and_config():
    cfg = load_config("h3b_far_field_cc0")
    assert RUNNERS[cfg["runner"]] == "far_field_cc0"
    assert cfg["batch_dir"] == "out/batch_v8" and cfg["require_commercial_ml_ok"]
    assert [m["name"] for m in cfg["methods"]] == ["full_640", "full_1280", "tiled_2x2"]


def test_tiled_2x2_is_two_by_two():
    from cctvsec.experiments.farfield import tiles
    cfg = load_config("h3b_far_field_cc0")
    t = cfg["methods"][2]
    assert len(tiles(1280, 720, *t["tile"], t["overlap"])) == 4


def test_blocks_stay_within_stream():
    keys = [("a", f) for f in range(25)] + [("b", f) for f in range(5)]
    bl = make_blocks(keys, 10)
    assert [len(b) for b in bl] == [10, 10, 5, 5]
    assert all(len({k[0] for k in b}) == 1 for b in bl)


def _counts(hit):
    return {("s", i): {"hit": [h, 0], "n": [1, 0], "tp": h, "fp": 0} for i, h in enumerate(hit)}


def test_bootstrap_paired_delta_and_empty_band():
    base = _counts([0] * 20)
    better = _counts([1] * 20)
    r = block_bootstrap({"full_640": base, "x": better}, make_blocks(list(base), 5), 200, 0, 2)
    assert r["recall"]["full_640"][0][0] == 0.0 and r["recall"]["x"][0][0] == 1.0
    assert r["delta_vs_full_640"]["x"][-1] == [1.0, 1.0, 1.0]
    assert r["recall"]["x"][1][0] is None          # empty band reported as missing, not 0
    assert r["n"] == [20, 0, 20]


def test_decide_hard_negative_can_fail():
    far = {"recall": {"full_640": [[0.01, 0, 0.02]]},
           "delta_vs_full_640": {"full_1280": [[0.4, 0.3, 0.5]], "tiled_2x2": [[0.3, 0.2, 0.4]]}}
    near_gain = {"delta_vs_full_640": {"tiled_2x2": [[0.05, 0.02, 0.07]]}}
    near_flat = {"delta_vs_full_640": {"tiled_2x2": [[0.0, -0.02, 0.02]]}}
    lat = {"full_640": 14, "tiled_2x2": 40}
    d = decide({"far": far, "near": near_gain}, lat)
    assert d["decision_met"] and not d["HN_near_tiling_no_gain"]
    assert decide({"far": far, "near": near_flat}, lat)["HN_near_tiling_no_gain"]
    assert not decide({"far": far, "near": near_flat}, {"full_640": 14, "tiled_2x2": 20})["decision_met"]


def test_licence_gate(tmp_path):
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "licences.json").write_text(json.dumps({"commercial_ml_ok": True}))
    (tmp_path / "mh").mkdir()
    (tmp_path / "mh" / "licences.json").write_text(json.dumps({"commercial_ml_ok": False}))
    assert check_licence(tmp_path, ["ok", "mh", "missing"]) == {"ok": True, "mh": False, "missing": False}
