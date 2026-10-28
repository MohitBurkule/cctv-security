"""The licence-compliant CC0 character stack (docs/research/47 option A).

Licence provenance in ground truth, clothing regions from skin weights, and the
gait (facing + ground speed) derived from a character's own walk clip.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from survsim.export.cc0_chars import gait_from_curves
from survsim.export.foot_slide import plan_slide
from survsim.gt.licences import (
    CESIUMMAN_ATTRIBUTION,
    character_licence,
    dataset_licences,
    licence_column,
    normalise_licence,
    person_licences,
)

CC0 = {"kind": "cc0", "license": "CC0-1.0", "author": "Quaternius"}
MH = {"kind": "metahuman", "walk": "/MetaHumanCharacter/.../AS_MH_Neutral_Walk_Loop_F"}
CESIUM = {"license": "CC-BY-4.0 (Khronos sample)"}


def test_normalise_licence_ids():
    assert normalise_licence("CC0-1.0") == "CC0-1.0"
    assert normalise_licence("CC-BY-4.0 (Khronos sample)") == "CC-BY-4.0"
    assert normalise_licence(None) == "LicenseRef-Unknown"
    assert normalise_licence("some EULA") == "LicenseRef-Unknown"


def test_all_cc0_set_is_commercially_usable():
    per = {f"p{i}": person_licences("man_hmnu", CC0) for i in range(3)}
    s = dataset_licences(per)
    assert s["commercial_ml_ok"] is True
    assert s["asset_licences"] == ["CC0-1.0"] and not s["attributions"]


def test_one_metahuman_poisons_the_set():
    per = {"a": person_licences("man_hmnu", CC0), "b": person_licences("MHB01", MH)}
    s = dataset_licences(per)
    assert s["commercial_ml_ok"] is False
    assert "LicenseRef-Epic-MetaHuman" in s["asset_licences"]
    # the MetaHuman locomotion clip is its own dependency
    assert any("AS_MH" in b for b in s["blocking_assets"])


def test_cesiumman_is_ok_but_emits_attribution():
    s = dataset_licences({"a": person_licences("CesiumMan", CESIUM)})
    assert s["commercial_ml_ok"] is True
    assert s["attributions"] == [CESIUMMAN_ATTRIBUTION]


def test_unknown_licence_is_not_ok_and_empty_is_not_ok():
    assert dataset_licences({"a": [character_licence("x", {"license": "?"})]})[
        "commercial_ml_ok"] is False
    assert dataset_licences({})["commercial_ml_ok"] is False


def test_licence_column_roundtrips_source_and_id():
    col = licence_column(person_licences("man_hmnu", CC0))
    assert col == "CC0-1.0|quaternius:man_hmnu"


def test_recorder_writes_asset_licences(tmp_path):
    import pandas as pd

    from survsim.core.loader import load_scenario
    from survsim.director.world import World
    from survsim.gt.writers import Recorder
    sc = load_scenario(Path("configs/scenarios/smoke_mock.yaml"))
    world, rec = World(sc), Recorder(sc, tmp_path)
    for _ in range(5):
        world.step()
        rec.add_world(world)
    rec.write(world)
    ids = pd.read_parquet(tmp_path / "gt" / "identities.parquet")
    if len(ids):
        assert ids["asset_licences"].str.startswith("LicenseRef-SurvSim-Procedural").all()
    meta = json.loads((tmp_path / "meta" / "licences.json").read_text())
    assert "commercial_ml_ok" in meta


# ------------------------------------------------------------------ gait


def _curves(fwd=(0.0, 1.0), speed_cms=150.0, L=1.0, n=240):
    """Synthetic in-place walk: each foot planted half the cycle, sliding backward."""
    t = np.linspace(0, L, n + 1)
    f = np.array(fwd) / np.linalg.norm(fwd)
    out = {"len_s": L, "t": t, "ref_height_cm": 175.0}
    for k, ph in (("foot_l", 0.0), ("foot_r", 0.5)):
        u = (t / L + ph) % 1.0
        # stance: u<0.5 moves back at speed; swing: returns forward, lifted
        s = np.where(u < 0.5, -speed_cms * L * (u - 0.25),
                     speed_cms * L * (u - 0.75) * 1.0)
        z = np.where(u < 0.5, 2.0, 2.0 + 15 * np.sin(math.pi * (u - 0.5) / 0.5))
        out[k] = np.c_[s * f[0], s * f[1], z]
        out[k + "_contact"] = z < z.min() + 2.0
    return out


@pytest.mark.parametrize("fwd,yaw", [((0, 1), -90.0), ((1, 0), 0.0), ((0, -1), 90.0)])
def test_gait_facing_and_speed_from_foot_curves(fwd, yaw):
    g = gait_from_curves(_curves(fwd))
    assert abs(((g["yaw_offset"] - yaw + 180) % 360) - 180) < 1e-6
    assert abs(g["ground_speed_mps"] - 1.5) < 0.05


def test_plan_slide_uses_the_characters_own_clip():
    c = _curves()
    v, n, fps = 1.5, 60, 10.0
    keys = [{"frame": f, "location": [f * v * 100 / fps, 0.0, 0.0]} for f in range(n)]

    def plan(rate):
        return [{"character": "q", "keys": keys, "yaws": [0.0] * n, "height_cm": 175.0,
                 "segments": [{"clip": "walk", "rate": rate, "start": 0, "end": n}]}]

    per = {"q": (c, -90.0, 175.0)}
    good = plan_slide(plan(1.0), fps, per_character=per)
    bad = plan_slide(plan(0.6), fps, per_character=per)
    assert good["stance_samples"] > 0
    assert good["slide_median_cms"] < 5.0 and bad["slide_median_cms"] > 30.0


# ------------------------------------------------------------------ regions

REBAKED = Path.home() / "data/assets/characters_rebake/man_fjHyMd5Wxw.glb"


@pytest.mark.skipif(not REBAKED.is_file(), reason="asset library not on this machine")
def test_region_paint_labels_every_clothing_region(tmp_path):
    from survsim.export.cc0_regions import (
        FOREARM,
        SHOES,
        THIGH,
        TOP,
        check_regions,
        decode,
        paint_file,
    )
    from survsim.export.gltf_normalize import read_accessor, read_glb
    frac = paint_file(REBAKED, tmp_path / "x.glb")
    assert not check_regions(frac)
    g, b = read_glb(tmp_path / "x.glb")
    prim = g["meshes"][0]["primitives"][0]
    col = read_accessor(g, b, prim["attributes"]["COLOR_0"], raw=True)
    codes = {decode(r / 255.0) for r in col[:, 0]}
    assert codes <= set(range(8))
    # the source is untouched (no COLOR_0 on the rebaked copy)
    g0, _ = read_glb(REBAKED)
    assert "COLOR_0" not in g0["meshes"][0]["primitives"][0]["attributes"]
    assert {TOP, THIGH, SHOES, FOREARM} <= {i for i, k in enumerate(frac) if frac[k] > 0}
