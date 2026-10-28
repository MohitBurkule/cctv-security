"""fence_tailgate: the intruder follows a badged worker through the fence gate (H54)."""
import numpy as np
import pytest

from survsim.core.models import BehaviourSpec
from cctvsec.experiments import alarm_scale as AS
from survsim.generator.batch import SITE_TYPES


@pytest.fixture(scope="module")
def scene_spec():
    j = SITE_TYPES.index("perimeter_site")
    return AS._site_spec(j, 40 * 1000 + 3, {"duration_s": 300, "fps": 5}, ["fence_tailgate"])


def _run(spec, edit=None):
    sc = AS._compose_valid(spec.model_copy(deep=True)).scenario
    if edit:
        edit(sc)
    df, w = AS._simulate(sc)
    return sc, df, w


def _entries(df, uid, comp):
    g = df[df["uid"] == uid].sort_values("t")
    ins = np.array([comp.contains(np.array([x, y])) for x, y in zip(g["x"], g["y"])])
    k = np.flatnonzero(ins & ~np.r_[False, ins[:-1]])
    return g.iloc[k]


def test_tailgater_follows_through_gate(scene_spec):
    _sc, df, w = _run(scene_spec)
    rec = [r for r in w.sensor_log if r.get("event") == "tailgate"]
    assert len(rec) == 1
    r = rec[0]
    assert r["unbadged_uid"] == "p000" and w.roster[r["uid"]].spec.role == "worker"
    assert 0 < r["gap_s"] <= 10 and r["t_follower"] > r["t_leader"]
    comp = next(c for c in w.fences.components if r["door"].split(":", 1)[1] in c.zone_ids)
    e = _entries(df, "p000", comp)
    assert len(e) >= 1
    # through the gate, not over the fence; truth time = actual passage
    assert np.hypot(e["x"].iat[0] - comp.gate[0], e["y"].iat[0] - comp.gate[1]) <= 3.5
    assert abs(e["t"].iat[0] - r["t_follower"]) <= 0.4
    assert any(ev.label == "suspicious.access.tailgate" and ev.actors == ["p000"] for ev in w.events)


def test_tailgater_without_leader_never_enters(scene_spec):
    def drop_twin(sc):
        sc.population.hero = [p for p in sc.population.hero if p.id != "p001"]
    _sc, df, w = _run(scene_spec, drop_twin)
    assert not [r for r in w.sensor_log if r.get("event") == "tailgate"]
    g = df[df["uid"] == "p000"]
    assert not any(w.fences.inside_any(np.array([x, y])) for x, y in zip(g["x"], g["y"]))


def test_staff_escort_twin_walks_in_badged(scene_spec):
    def escort(sc):
        p = next(p for p in sc.population.hero if p.id == "p000")
        p.role = "worker"
        src = sc.population.hero[1].intent[0].model_extra.get("from")
        p.intent = [BehaviourSpec(type="transit", **{"from": src, "to": src}),
                    BehaviourSpec(type="staff_escort", target="p001", gap_m=1.2)]
    _sc, df, w = _run(scene_spec, escort)
    assert not [r for r in w.sensor_log if r.get("event") == "tailgate"]
    g = df[df["uid"] == "p000"]
    assert any(w.fences.inside_any(np.array([x, y])) for x, y in zip(g["x"], g["y"]))
    assert any(ev.label == "normal.maintenance.escort" for ev in w.events)
