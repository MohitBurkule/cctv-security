"""Tests for appearance epochs, PTZ/tamper, population generation and rig analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from survsim.core.appearance import AppearanceState
from survsim.core.loader import load_scenario
from survsim.core.models import Camera, Mount, Person
from survsim.core.rng import RngHub
from survsim.director import rig as rig_tools
from survsim.director.camera_director import CameraDirector
from survsim.director.population import expand_generator, random_person, split_of
from survsim.simulator import Simulator

SCENARIO = Path(__file__).parent.parent / "configs" / "scenarios" / "disguise_and_tamper.yaml"


# ------------------------------------------------------------------ appearance


def test_removing_a_jacket_changes_the_appearance_hash() -> None:
    person = Person(id="p", outfit={"top": "tshirt", "outer": "rain_jacket"})
    state = AppearanceState.from_person(person)
    before = state.hash

    assert state.apply({"outer": "none"}, t=10.0) is True
    assert state.hash != before
    assert state.epoch == 1
    assert state.outfit.outer is None


def test_no_op_change_does_not_advance_the_epoch() -> None:
    """Only a real appearance difference should start a new epoch."""
    state = AppearanceState.from_person(Person(id="p", outfit={"top": "tshirt"}))
    assert state.apply({"top": "tshirt"}, t=5.0) is False
    assert state.epoch == 0


def test_mask_hides_the_face() -> None:
    state = AppearanceState.from_person(Person(id="p"))
    assert state.face_visible is True
    state.apply({"face": {"mask": True}}, t=1.0)
    assert state.face_visible is False


def test_dominant_colour_prefers_the_outer_layer() -> None:
    person = Person(
        id="p",
        outfit={"top": "tshirt", "outer": "rain_jacket",
                "colours": {"top": "#ffffff", "outer": "#000000"}},
    )
    state = AppearanceState.from_person(person)
    assert state.dominant_colour == "#000000"
    state.apply({"outer": "none"}, t=1.0)
    assert state.dominant_colour == "#ffffff"


# ------------------------------------------------------------- camera director


def _ptz_camera() -> Camera:
    return Camera(
        id="ptz", type="ptz", mount=Mount(pos=(0.0, 0.0, 8.0), yaw=0.0, pitch=-20.0),
        optics={"hfov_deg": [3.0, 60.0]}, capture={"res": (1920, 1080), "fps": 10},
        ptz={"speed_dps": 40.0, "patrol": [{"preset": "a", "dwell_s": 5.0},
                                           {"preset": "b", "dwell_s": 5.0}]},
        presets={"a": {"yaw": -60.0, "pitch": -20.0}, "b": {"yaw": 60.0, "pitch": -20.0}},
    )


def test_ptz_slews_at_its_mechanical_rate() -> None:
    """The head must not teleport between presets — the travel time is the blind window."""
    director = CameraDirector([_ptz_camera()])
    dt = 0.1
    director.step(0.0, dt)
    after_one_tick = abs(director.states["ptz"].yaw)
    assert after_one_tick <= 40.0 * dt + 1e-6


def test_ptz_visits_both_presets() -> None:
    director = CameraDirector([_ptz_camera()])
    seen = []
    t, dt = 0.0, 0.1
    for _ in range(400):
        director.step(t, dt)
        seen.append(director.states["ptz"].yaw)
        t += dt
    assert min(seen) < -50.0 and max(seen) > 50.0


def test_cover_tamper_blinds_the_camera_but_spray_does_not() -> None:
    cam = Camera(id="c", mount=Mount(pos=(0.0, 0.0, 4.0)))
    director = CameraDirector([cam])
    director.tamper("c", "spray", t=1.0)
    assert director.states["c"].blind is False
    director.tamper("c", "cover", t=2.0)
    assert director.states["c"].blind is True


def test_tilt_tamper_invalidates_the_stored_pose() -> None:
    """A knocked camera keeps streaming, so calibration silently stops matching."""
    cam = Camera(id="c", mount=Mount(pos=(0.0, 0.0, 4.0), yaw=10.0, pitch=-15.0))
    director = CameraDirector([cam])
    director.tamper("c", "tilt", t=1.0)
    live = director.live_camera("c")
    assert live.mount.pitch != cam.mount.pitch
    assert director.states["c"].blind is False


def test_unknown_tamper_kind_rejected() -> None:
    director = CameraDirector([Camera(id="c", mount=Mount(pos=(0.0, 0.0, 4.0)))])
    with pytest.raises(ValueError, match="unknown tamper kind"):
        director.tamper("c", "banana", t=0.0)


# ------------------------------------------------------------------ population


def test_generated_people_are_deterministic_and_varied() -> None:
    def sample() -> list[Person]:
        rng = RngHub(3)("population")
        return [random_person(f"p{i}", rng) for i in range(60)]

    a, b = sample(), sample()
    assert [p.body.height_m for p in a] == [p.body.height_m for p in b]

    # Diversity is the property that makes synthetic data transfer, so assert it.
    assert len({p.body.skin_tone for p in a}) >= 6
    assert len({p.outfit.colours["top"] for p in a}) >= 50
    heights = [p.body.height_m for p in a]
    assert 1.15 <= min(heights) and max(heights) <= 2.05
    assert all(0.6 <= p.gait.speed_mps <= 1.8 for p in a)


def test_identity_split_is_stable_and_disjoint() -> None:
    ids = [f"person_{i:04d}" for i in range(500)]
    splits = {i: split_of(i) for i in ids}
    assert splits == {i: split_of(i) for i in ids}
    assert set(splits.values()) <= {"train", "val", "test"}
    assert 0.6 < sum(v == "train" for v in splits.values()) / len(ids) < 0.95


def test_generator_template_binds_scenario_points() -> None:
    rng = RngHub(1)("population")
    people = expand_generator(
        {"template": "commute_wait_negative", "count": 3, "dur_s": [30, 60]},
        rng,
        {"zones": ["zone.gate_A"], "spawns": ["spawn.north"], "exits": ["exit.south"]},
    )
    assert len(people) == 3
    assert all(p.hard_negative_for == ["loiter"] for p in people)
    wait = people[0].intent[1]
    assert wait.type == "commute_wait"
    assert 30.0 <= (wait.model_extra or {})["dur_s"] <= 60.0


def test_unknown_template_rejected() -> None:
    with pytest.raises(KeyError, match="unknown template"):
        expand_generator({"template": "nope"}, RngHub(0)("x"), {})


# ------------------------------------------------------------------------ rig


def test_coverage_finds_the_designed_blind_spot() -> None:
    s = load_scenario(SCENARIO)
    report = rig_tools.summary(s.cameras, s.environment, cell_m=1.0)

    assert 0.0 < report["blind_fraction"] < 1.0
    spots = report["blind_spots"]
    assert spots, "a four-camera rig over this yard must leave gaps"

    # The scenario stages its outfit change inside zone.blindspot_A, so that zone
    # must genuinely be unobserved. Check the cells themselves rather than a region
    # centroid: a blind area usually extends past the zone edge, which drags the
    # centroid outside the polygon even when the zone is fully blind.
    grid = rig_tools.coverage(s.cameras, s.environment, cell_m=1.0)
    zone = s.environment.zone("zone.blindspot_A")
    poly = np.array(zone.polygon)
    xs = (grid.xs >= poly[:, 0].min()) & (grid.xs <= poly[:, 0].max())
    ys = (grid.ys >= poly[:, 1].min()) & (grid.ys <= poly[:, 1].max())
    seen_in_zone = grid.count()[np.ix_(ys, xs)]
    assert seen_in_zone.size > 0
    assert seen_in_zone.max() == 0, (
        "zone.blindspot_A is covered by a camera, so the disguise scenario would "
        "be observed and cross-epoch ReID could not be tested there"
    )


def test_overlap_matrix_is_self_consistent() -> None:
    s = load_scenario(SCENARIO)
    grid = rig_tools.coverage(s.cameras, s.environment, cell_m=2.0)
    _ids, m = rig_tools.overlap_matrix(grid)
    assert np.allclose(np.diag(m), 1.0)
    assert ((m >= 0.0) & (m <= 1.0)).all()


def test_transit_priors_bracket_the_nominal_walk() -> None:
    s = load_scenario(SCENARIO)
    grid = rig_tools.coverage(s.cameras, s.environment, cell_m=2.0)
    priors = rig_tools.transit_priors(s.cameras, grid)
    assert priors
    for v in priors.values():
        assert v["t_min_s"] <= v["t_nominal_s"] <= v["t_max_s"]


# ----------------------------------------------------------------- end to end


@pytest.mark.slow
def test_disguise_scenario_records_two_epochs(tmp_path: Path) -> None:
    import pandas as pd

    sim = Simulator.from_yaml(SCENARIO, engine="mock")
    sim.record(tmp_path, topdown_video=False)
    ids = pd.read_parquet(tmp_path / "gt" / "identities.parquet")

    intruder = ids[ids["uid"] == "intruder_a"].sort_values("epoch")
    assert len(intruder) == 2, "the outfit change should have opened a second epoch"
    assert intruder.iloc[0]["appearance_hash"] != intruder.iloc[1]["appearance_hash"]
    assert bool(intruder.iloc[0]["face_visible"]) and not bool(intruder.iloc[1]["face_visible"])
    # Soft biometrics survive the disguise and are the only cross-epoch cue.
    assert intruder.iloc[0]["height_m"] == intruder.iloc[1]["height_m"]


@pytest.mark.slow
def test_blinded_camera_stops_reporting_detections(tmp_path: Path) -> None:
    """After a cover tamper the camera must produce no ground truth at all."""
    s = load_scenario(SCENARIO)
    for cam in s.cameras:
        cam.tamper = [{"t": 30.0, "kind": "cover"}] if cam.id == "cam_gate" else []
    s.duration_s = 60.0

    sim = Simulator(s)
    sim.record(tmp_path, topdown_video=False)

    rows = [
        line.split(",") for line in
        (tmp_path / "gt" / "mot_cam_gate.txt").read_text().splitlines() if line
    ]
    frames = [int(r[0]) for r in rows]
    assert frames, "camera saw nothing even before the tamper"
    assert max(frames) <= 30.0 * s.fps + 1
