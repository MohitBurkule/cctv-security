"""H40b: intrusions really cross, fences stop innocents, twins and wildlife.

docs/research/32 §H40 measured the old mock intruders stopping at the zone
edge, fence_cut/climb never crossing and commuters walking straight through
restricted polygons. These pin the fixes (principles 1 and 3, CLAUDE.md).
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from survsim.core.models import (
    BehaviourSpec,
    Environment,
    Person,
    Population,
    Prop,
    Scenario,
    Waypoint,
    Zone,
)
from survsim.director.population import random_animal
from survsim.director.world import World

YARD = [(10, -6), (26, -6), (26, 6), (10, 6)]
POLY = Polygon(YARD)


def _env(gate: bool = True) -> Environment:
    props = [Prop(id="asset_0", type="cabinet", pos=(18.0, 0.0, 0.0)),
             Prop(id="fence_seg_0", type="fence_panel", pos=(18.0, -6.0, 0.0), cuttable=True)]
    if gate:
        props.append(Prop(id="gate.yard", type="gate", pos=(10.0, 0.0, 0.0)))
    return Environment(
        id="e",
        zones=[Zone(id="zone.open", tag="public", polygon=[(-60, -60), (60, -60), (60, 60), (-60, 60)]),
               Zone(id="zone.yard", tag="restricted", polygon=YARD, allowed_roles=["worker", "guard"])],
        spawn_points=[Waypoint(id="spawn.a", pos=(-20.0, 0.0, 0.0))],
        exits=[Waypoint(id="exit.a", pos=(45.0, 0.0, 0.0))],
        props=props)


def _world(people: list[Person]) -> World:
    return World(Scenario(name="s", seed=3, duration_s=600, fps=5, environment=_env(),
                          population=Population(hero=people)))


def _trace(world: World, uid: str, ticks: int) -> tuple[np.ndarray, list[str]]:
    xy, labels = [], []
    for _ in range(ticks):
        world.step()
        a = world.roster[uid]
        xy.append(a.pos.copy())
        labels.append(a.label)
    return np.array(xy), labels


def _depth(xy: np.ndarray) -> np.ndarray:
    return np.array([POLY.boundary.distance(Point(*p)) if POLY.contains(Point(*p)) else 0.0 for p in xy])


# ------------------------------------------------------------ intrusions cross

@pytest.mark.parametrize("spec", [
    {"type": "zone_intrusion", "zone": "zone.yard", "dur_s": 10.0},
    {"type": "fence_cut", "segment": "fence_seg_0", "dur_s": 10.0, "dwell_s": 10.0},
    {"type": "fence_climb", "segment": "fence_seg_0", "climb_s": 6.0, "dwell_s": 10.0},
])
def test_intruder_crosses_and_gets_at_least_3m_inside_then_leaves(spec):
    p = Person(id="x", role="intruder",
               intent=[BehaviourSpec(**spec), BehaviourSpec(type="transit", to="exit.a")])
    w = _world([p])
    w.agents["x"].pos = np.array([18.0, -15.0])
    xy, labels = _trace(w, "x", 1500)
    d = _depth(xy)
    assert d.max() >= 3.0, f"{spec['type']} only reached {d.max():.2f} m inside"
    inside = np.flatnonzero(d > 0)
    # it went in and came out again: a post-cross arc, not a stop at the edge
    assert inside.size and inside[-1] < len(xy) - 1 and d[inside[-1] + 1] == 0.0
    # the label that ground truth records is the hostile one for the whole crossing
    assert labels[inside[0]].startswith(("suspicious.access.intrusion", "hostile."))


def test_fence_climb_crossing_happens_at_the_end_of_the_climb():
    p = Person(id="x", role="intruder",
               intent=[BehaviourSpec(type="fence_climb", segment="fence_seg_0", climb_s=10.0)])
    w = _world([p])
    w.agents["x"].pos = np.array([18.0, -8.0])
    xy, _ = [], None
    postures = []
    for _ in range(200):
        w.step()
        xy.append(w.agents["x"].pos.copy())
        postures.append(w.agents["x"].posture)
    xy = np.array(xy)
    climbing = [i for i, s in enumerate(postures) if s == "climbing"]
    assert len(climbing) >= 40                          # ~10 s at 5 fps
    first_in = int(np.argmax(_depth(xy) > 0))
    assert first_in > climbing[0] + 0.5 * len(climbing)  # feet land late in the climb


# ------------------------------------------------------------ fences

def test_commuter_routes_round_a_fenced_zone_and_still_arrives():
    p = Person(id="c", intent=[BehaviourSpec(type="transit", to="exit.a")])
    w = _world([p])
    w.agents["c"].pos = np.array([-5.0, 0.0])
    xy, _ = _trace(w, "c", 600)
    assert _depth(xy).max() == 0.0, "an unauthorised walker entered the fenced zone"
    assert np.linalg.norm(xy[-1] - np.array([45.0, 0.0])) < 3.5


def test_fence_stops_a_behaviour_that_steers_straight_in():
    # loiter asks for a point inside the fence and (activity="pace") actually
    # walks there -- unlike the default "idle" activity, which sets speed to 0
    # and never moves, so a fence bug could hide behind an agent that was never
    # clamped in the first place. The literal [18.0, 0.0] goal (not a zone id)
    # is resolved exactly, with no jitter (World.sample_goal), so the planned
    # centre is known precisely and is provably inside the fenced polygon.
    p = Person(id="c", intent=[BehaviourSpec(type="loiter", zone=[18.0, 0.0], dur_s=60.0,
                                             activity="pace")])
    w = _world([p])
    w.agents["c"].pos = np.array([0.0, 0.0])
    xy, _ = _trace(w, "c", 200)
    behaviour = w.agents["c"].current
    assert behaviour is not None, "loiter should still be running at trace end"
    planned = np.asarray(behaviour._centre)
    assert POLY.contains(Point(*planned)), "the loiter target must be inside the fence for this test to mean anything"
    assert (xy != np.array([0.0, 0.0])).any(), "the agent never moved -- clamping was never exercised"
    # Principle 1 (CLAUDE.md): truth is what happened, not what was planned.
    # The recorded position must be the actual, clamped position -- never the
    # planned (fenced) goal the behaviour steered towards.
    assert _depth(xy).max() == 0.0, "an unauthorised walker entered the fenced zone"
    actual = xy[-1]
    assert np.linalg.norm(actual - planned) > 2.0, (
        "recorded ground truth matched the planned goal instead of the clamped position"
    )


def test_unfenced_zone_is_walkable():
    env = _env()
    env.zones[1].fenced = False
    p = Person(id="c", intent=[BehaviourSpec(type="transit", to="exit.a")])
    w = World(Scenario(name="s", seed=3, duration_s=600, fps=5, environment=env,
                       population=Population(hero=[p])))
    w.agents["c"].pos = np.array([-5.0, 0.0])
    xy, _ = _trace(w, "c", 400)
    assert _depth(xy).max() > 0.0


# ------------------------------------------------------------ hard-negative twins

def _twin_trace(spec: dict, role: str, ticks: int = 2500):
    p = Person(id="t", role=role, intent=[BehaviourSpec(**spec), BehaviourSpec(type="transit", to="exit.a")])
    w = _world([p])
    w.agents["t"].pos = np.array([0.0, -15.0])
    xy, labels = _trace(w, "t", ticks)
    return w, xy, labels


@pytest.mark.parametrize("spec,role", [
    ({"type": "patrol_guard", "check_s": 5.0}, "guard"),
    ({"type": "maintenance_visit", "zone": "zone.yard", "dur_s": 30.0}, "worker"),
])
def test_twins_enter_through_the_gate_and_never_carry_an_intrusion_label(spec, role):
    w, xy, labels = _twin_trace(spec, role)
    d = _depth(xy)
    assert d.max() > 1.5, "the twin should really go inside (it is a hard negative)"
    first_in = xy[int(np.argmax(d > 0))]
    assert np.linalg.norm(first_in - np.array([10.0, 0.0])) < 2.5, "entered away from the gate"
    assert all(lb.startswith("normal.") or lb == "normal.idle" for lb in labels)
    assert not any(e.label.startswith(("suspicious", "hostile")) for e in w.events)


def test_twins_are_not_line_cross_truth():
    """The H40 runner's truth is 'first sterile-zone tick after a hostile phase'.
    A twin has no hostile phase, so it can only ever be a false alarm."""
    w, xy, _ = _twin_trace({"type": "patrol_guard", "check_s": 5.0}, "guard")
    hostile = [e for e in w.events if e.label.split(".")[0] in ("suspicious", "hostile") and "t" in e.actors]
    assert _depth(xy).max() > 0 and not hostile


def test_patrol_walks_the_fence_line():
    _, xy, _ = _twin_trace({"type": "patrol_guard", "check_s": 5.0}, "guard")
    near = [POLY.exterior.distance(Point(*p)) < 1.6 and not POLY.contains(Point(*p)) for p in xy]
    assert sum(near) > 5 * 20, "a patrol spends most of its round along the fence, outside it"


# ------------------------------------------------------------ wildlife

def test_wildlife_is_small_fast_erratic_non_person_and_crosses_fences(tmp_path):
    from survsim.gt.writers import Recorder
    a = random_animal("w0", np.random.default_rng(1))
    a.intent = [BehaviourSpec(type="wildlife", zone="zone.yard", dur_s=40.0, top_mps=4.0, exit="exit.a")]
    w = _world([a])
    w.agents["w0"].pos = np.array([18.0, -10.0])
    rec = Recorder(w.scenario, tmp_path)
    xy, labels = [], []
    for _ in range(250):
        w.step()
        if "w0" in w.agents:
            rec.add_world(w)
            xy.append(w.agents["w0"].pos.copy())
            labels.append(w.agents["w0"].label)
    xy = np.array(xy)
    agent = w.roster["w0"]
    assert agent.object_class == "animal" and agent.height_m < 1.0
    assert {r["object_class"] for r in rec.world_rows} == {"animal"}
    assert rec._mot_class("w0") == "0,8"                   # MOT: not considered, "distractor"
    assert "distractor.wildlife" in labels
    sp = np.linalg.norm(np.diff(xy, axis=0), axis=1) * 5.0
    assert sp.max() > 2.0, "fast"
    hd = np.arctan2(*np.diff(xy, axis=0).T[::-1])
    assert np.abs(np.diff(np.unwrap(hd[sp[:len(hd)] > 0.2]))).max() > 1.0, "erratic"
    assert _depth(xy).max() > 0.0, "animals go under fences"


# ------------------------------------------------------------ generator arcs

def _scene(incident: str, site: str = "perimeter_site", seed: int = 5):
    from survsim.generator.compose import compose
    from survsim.generator.spec import CameraPlan, IncidentPlan, PopulationPlan, SceneSpec, SiteSpec
    return compose(SceneSpec(name="t", seed=seed, duration_s=120, fps=5,
                             site=SiteSpec(type=site, footprint_m=(80, 60), entrances=2, restricted_zones=1),
                             cameras=CameraPlan(count=10, target_coverage=0.3),
                             population=PopulationPlan(count=6, wildlife=2),
                             incidents=[IncidentPlan(type=incident)]))  # type: ignore[arg-type]


def test_generator_has_a_climb_arc_with_a_patrol_twin():
    s = _scene("fence_climb")
    hostile = next(a for a in s.arcs if a.intent == "hostile")
    assert "fence_climb" in hostile.phases
    twin = next(a for a in s.arcs if a.narrative == "patrol_guard")
    assert twin.person.role == "guard" and "patrol_guard" in twin.phases
    assert sum(a.narrative == "wildlife" for a in s.arcs) == 2
    assert all(a.person.identity.get("class") == "animal" for a in s.arcs if a.narrative == "wildlife")


def test_probe_arc_no_longer_falls_back_to_recon_without_fence_panels():
    s = _scene("perimeter_probe", site="office_building")
    hostile = next(a for a in s.arcs if a.intent == "hostile")
    assert hostile.phases[1:3] == ["perimeter_probe", "fence_cut"], hostile.phases


def test_intrusion_twin_is_an_authorised_maintenance_visit():
    s = _scene("zone_intrusion", site="office_building")
    twin = next(a for a in s.arcs if a.person.hard_negative_for == ["zone_intrusion"])
    assert twin.narrative == "maintenance_visit" and twin.person.role == "worker"


def test_perimeter_site_compound_is_fenced_with_a_gate_and_deep_enough():
    s = _scene("fence_cut")
    env = s.scenario.environment
    comp = next(z for z in env.zones if z.id == "zone.compound")
    strip = next(z for z in env.zones if z.id == "zone.fence_line")
    assert Polygon(comp.polygon).contains(Polygon(strip.polygon).representative_point())
    assert Polygon(comp.polygon).buffer(-3.5).area > 0
    assert any(p.type == "gate" for p in env.props)
