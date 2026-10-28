"""Tests for alarm scoring — especially the timing rules that differ from academia."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest

from cctvsec.eval.alarms import DEFAULT_BUDGET_FA_PER_CAMERA_HOUR, Alarm, TruthEvent, score
from cctvsec.eval.rules import DwellRule, PathLoiterRule
from survsim.simulator import Simulator

SMOKE = Path(__file__).parent.parent / "configs" / "scenarios" / "smoke_mock.yaml"
ONE_EVENT = [TruthEvent(t_start=100.0, t_end=160.0, label="suspicious.loiter")]


def test_alarm_inside_tolerance_counts_as_detection() -> None:
    result = score(ONE_EVENT, [Alarm(t=105.0, label="suspicious.loiter")], camera_hours=1.0)
    assert result.true_positives == 1
    assert result.false_positives == 0
    assert result.latencies_s == [5.0]


def test_late_alarm_is_a_false_alarm_not_a_detection() -> None:
    """The i-LIDS rule: an alarm after the tolerance window has no operational value.

    Frame-level AUC would score this as a success, which is why it flatters
    systems that are useless in a control room.
    """
    result = score(
        ONE_EVENT, [Alarm(t=140.0, label="suspicious.loiter")],
        camera_hours=1.0, tolerance_s=10.0,
    )
    assert result.true_positives == 0
    assert result.false_negatives == 1
    assert result.false_positives == 1


def test_repeat_alarms_on_one_event_are_penalised() -> None:
    """A system that fires continuously must not score perfectly."""
    alarms = [Alarm(t=101.0 + i, label="suspicious.loiter") for i in range(5)]
    result = score(ONE_EVENT, alarms, camera_hours=1.0)
    assert result.true_positives == 1
    assert result.repeat_alarms == 4
    assert result.false_positives == 4
    assert result.precision == 0.2


def test_false_alarm_rate_uses_camera_hours() -> None:
    alarms = [Alarm(t=float(10 * i), label="suspicious.loiter") for i in range(1, 7)]
    result = score([], alarms, camera_hours=2.0)
    assert result.false_positives == 6
    assert result.false_alarms_per_camera_hour == 3.0


def test_operator_verdict_exposes_the_research_deployment_gap() -> None:
    """Six false alarms per camera-hour is a normal research operating point.

    Against 500 cameras and one operator it is thousands of times over budget;
    reporting that ratio is the point of this metric.
    """
    result = score([], [Alarm(t=float(i), label="x") for i in range(6)], camera_hours=1.0)
    verdict = result.operator_verdict(cameras_per_operator=500)
    assert verdict["within_budget"] is False
    assert verdict["over_budget_factor"] > 1000
    assert verdict["false_alarms_per_operator_hour"] == 3000.0


def test_operator_budget_constant_matches_the_default_verdict() -> None:
    """The module docstring used to say ~0.005; the code's own A/K/H gives 0.001.

    docs/research/28_BEHAVIOUR_SCENE_DEEP_DIVE.md §7.1 derives the same 5x
    discrepancy and flags it as a documentation bug, not a formula bug: the
    default budget really is 4 nuisance alarms / (500 cameras * 8h shift).
    This pins the named constant to that formula and to what
    `operator_verdict`'s default actually reports.
    """
    assert DEFAULT_BUDGET_FA_PER_CAMERA_HOUR == pytest.approx(4.0 / (500 * 8.0))
    assert DEFAULT_BUDGET_FA_PER_CAMERA_HOUR == pytest.approx(0.001)

    result = score(ONE_EVENT, [Alarm(t=102.0, label="suspicious.loiter")], camera_hours=100.0)
    verdict = result.operator_verdict()
    assert verdict["budget_per_camera_hour"] == pytest.approx(DEFAULT_BUDGET_FA_PER_CAMERA_HOUR)


def test_perfect_system_is_within_budget() -> None:
    result = score(ONE_EVENT, [Alarm(t=102.0, label="suspicious.loiter")], camera_hours=100.0)
    assert result.operator_verdict()["within_budget"] is True
    assert result.f1 == 1.0


def test_labels_must_match_to_count() -> None:
    result = score(ONE_EVENT, [Alarm(t=101.0, label="hostile.tamper.camera")], camera_hours=1.0)
    assert result.true_positives == 0
    assert result.false_positives == 1


# ------------------------------------------------------------------ ilids_compat


def test_default_mode_penalises_every_repeat() -> None:
    """Default (ilids_compat=False) behaviour is unchanged from before this option existed."""
    alarms = [Alarm(t=101.0 + i, label="suspicious.loiter") for i in range(5)]
    result = score(ONE_EVENT, alarms, camera_hours=1.0, ilids_compat=False)
    assert result.true_positives == 1
    assert result.false_positives == 4
    assert result.repeat_alarms == 4


def test_ilids_compat_ignores_repeats_inside_the_matched_window() -> None:
    """i-LIDS 'disregards' repeat detections on an event already credited."""
    alarms = [Alarm(t=101.0 + i, label="suspicious.loiter") for i in range(5)]
    result = score(ONE_EVENT, alarms, camera_hours=1.0, ilids_compat=True)
    assert result.true_positives == 1
    assert result.false_positives == 0
    assert result.repeat_alarms == 4  # still counted for diagnostics, just not penalised
    assert result.precision == 1.0


def test_ilids_compat_coalesces_false_positives_within_five_seconds() -> None:
    """'Only one false positive alarm will be logged every five seconds.'"""
    alarms = [Alarm(t=float(t), label="suspicious.loiter") for t in (200, 202, 204, 230, 231)]
    result = score([], alarms, camera_hours=1.0, ilids_compat=True, fa_coalesce_s=5.0)
    # (200, 202, 204) coalesce to one; (230, 231) coalesce to one: 2 total.
    assert result.false_positives == 2


def test_ilids_compat_default_off_keeps_existing_numbers() -> None:
    """The flag must default to False so nothing already reported moves."""
    alarms = [Alarm(t=float(t), label="suspicious.loiter") for t in (200, 202, 204)]
    result = score([], alarms, camera_hours=1.0)
    assert result.false_positives == 3


# ------------------------------------------------------------------ actor_aware
#
# docs/research/58 §4: `alarms.score` matches actor-blind, so when two events of
# the same label start within `tolerance_s` of each other (e.g. a disguise_swap
# "scan" loiter and a plain loiter both starting near t=0), the earlier one steals
# the match and the second person's alarm is scored as a repeat — capping the best
# possible recall at 0.90 even for a label oracle that alarms at every event start.


def test_window_only_scoring_caps_recall_below_one() -> None:
    """Reproduces the H12/H58 ceiling: two same-label events close together, one
    alarm each, and window-only matching only credits one of them. This used to
    be the *default* behaviour (docs/13 round 1); round 2 made actor-aware
    matching the default whenever alarms carry uids, so this now requires the
    explicit override."""
    truth = [
        TruthEvent(t_start=100.0, t_end=160.0, label="suspicious.loiter", actors=("a",)),
        TruthEvent(t_start=103.0, t_end=163.0, label="suspicious.loiter", actors=("b",)),
    ]
    alarms = [
        Alarm(t=100.0, label="suspicious.loiter", uid="a"),
        Alarm(t=103.0, label="suspicious.loiter", uid="b"),
    ]
    result = score(truth, alarms, camera_hours=1.0, tolerance_s=30.0, actor_aware=False)
    assert result.true_positives == 1
    assert result.false_negatives == 1
    assert result.repeat_alarms == 1


def test_default_is_now_actor_aware_when_alarms_carry_uids() -> None:
    """Round 2: `actor_aware=None` (the default) auto-resolves to True as soon as
    any alarm has a uid, which is the opposite of round 1's `default False`."""
    truth = [
        TruthEvent(t_start=100.0, t_end=160.0, label="suspicious.loiter", actors=("a",)),
        TruthEvent(t_start=103.0, t_end=163.0, label="suspicious.loiter", actors=("b",)),
    ]
    alarms = [
        Alarm(t=100.0, label="suspicious.loiter", uid="a"),
        Alarm(t=103.0, label="suspicious.loiter", uid="b"),
    ]
    result = score(truth, alarms, camera_hours=1.0, tolerance_s=30.0)
    assert result.true_positives == 2
    assert result.false_negatives == 0
    assert result.repeat_alarms == 0
    # The old, window-only number is still available alongside it.
    assert result.window_only_recall == pytest.approx(0.5)


def test_default_is_window_only_when_no_alarm_has_a_uid() -> None:
    """Auto mode falls back to window-only (the pre-round-2 behaviour) when no
    alarm names an actor, so a rule that never emits uid is unaffected."""
    result = score(ONE_EVENT, [Alarm(t=105.0, label="suspicious.loiter")], camera_hours=1.0)
    assert result.true_positives == 1
    assert result.window_only_recall == 1.0


def test_actor_aware_lets_both_simultaneous_events_be_hit() -> None:
    """Same scenario, `actor_aware=True`: each alarm is matched to its own actor's
    event instead of both competing for the one event whose window it falls in."""
    truth = [
        TruthEvent(t_start=100.0, t_end=160.0, label="suspicious.loiter", actors=("a",)),
        TruthEvent(t_start=103.0, t_end=163.0, label="suspicious.loiter", actors=("b",)),
    ]
    alarms = [
        Alarm(t=100.0, label="suspicious.loiter", uid="a"),
        Alarm(t=103.0, label="suspicious.loiter", uid="b"),
    ]
    result = score(truth, alarms, camera_hours=1.0, tolerance_s=30.0, actor_aware=True)
    assert result.true_positives == 2
    assert result.false_negatives == 0
    assert result.repeat_alarms == 0


def test_actor_aware_falls_back_to_window_only_without_uid() -> None:
    """An alarm with no uid (a rule that never emits actor identity) must not
    regress under actor_aware=True — it keeps matching on the window alone."""
    result = score(ONE_EVENT, [Alarm(t=105.0, label="suspicious.loiter")],
                    camera_hours=1.0, actor_aware=True)
    assert result.true_positives == 1
    assert result.false_positives == 0


def test_default_auto_mode_matches_explicit_actor_aware_true_when_uids_present() -> None:
    """`actor_aware=None` (the default) must be bit-identical to an explicit
    `actor_aware=True` once any alarm carries a uid -- this is the auto-mode
    contract, not the round-1 "default is False" contract this test used to
    check."""
    truth = [
        TruthEvent(t_start=100.0, t_end=160.0, label="suspicious.loiter", actors=("a",)),
        TruthEvent(t_start=103.0, t_end=163.0, label="suspicious.loiter", actors=("b",)),
    ]
    alarms = [
        Alarm(t=100.0, label="suspicious.loiter", uid="a"),
        Alarm(t=103.0, label="suspicious.loiter", uid="b"),
    ]
    default_result = score(truth, alarms, camera_hours=1.0, tolerance_s=30.0)
    explicit_on = score(truth, alarms, camera_hours=1.0, tolerance_s=30.0, actor_aware=True)
    assert default_result.as_dict() == explicit_on.as_dict()


def test_default_auto_mode_matches_explicit_actor_aware_false_without_uids() -> None:
    """Without any uid on any alarm, auto mode must equal explicit
    `actor_aware=False` (window-only) -- the pre-round-2 default."""
    default_result = score(ONE_EVENT, [Alarm(t=105.0, label="suspicious.loiter")], camera_hours=1.0)
    explicit_off = score(
        ONE_EVENT, [Alarm(t=105.0, label="suspicious.loiter")], camera_hours=1.0, actor_aware=False
    )
    assert default_result.as_dict() == explicit_off.as_dict()


def test_bystander_hits_counts_alarms_on_the_wrong_person() -> None:
    """An alarm that lands in an event's window but names a uid that is not one
    of that event's actors is a bystander hit, not a true positive -- CLAUDE.md
    principle 4: an alarm on the wrong person is not a hit."""
    truth = [TruthEvent(t_start=100.0, t_end=160.0, label="suspicious.loiter", actors=("a",))]
    alarms = [Alarm(t=105.0, label="suspicious.loiter", uid="c")]  # bystander, not "a"
    result = score(truth, alarms, camera_hours=1.0, tolerance_s=30.0, actor_aware=True)
    assert result.true_positives == 0
    assert result.false_negatives == 1
    assert result.bystander_hits == 1
    # Window-only would have credited it -- that gap is exactly what the note is for.
    assert result.window_only_recall == 1.0


def test_bystander_hits_is_zero_when_no_actors_are_recorded() -> None:
    """An event with no `actors` recorded cannot have a bystander hit -- there is
    no ground truth to say the alarm is on the wrong person."""
    result = score(ONE_EVENT, [Alarm(t=105.0, label="suspicious.loiter", uid="anyone")],
                    camera_hours=1.0)
    assert result.bystander_hits == 0


# --------------------------------------------------------------- baseline rule


def test_dwell_rule_cannot_separate_loiterer_from_commuter(tmp_path: Path) -> None:
    """The headline result: perfect tracking, and the rule still cannot tell them apart.

    Both people stand in the same gate zone for the same 25 s. Any rule keyed on
    dwell time alone must either alarm on both or neither — which is exactly the
    nuisance-alarm problem that behaviour analytics exists to solve.
    """
    import json

    import pandas as pd

    sim = Simulator.from_yaml(SMOKE, engine="mock")
    sim.record(tmp_path, topdown_video=False)

    world = pd.read_parquet(tmp_path / "gt" / "world.parquet")
    scenario = json.loads((tmp_path / "meta" / "scenario.resolved.json").read_text())
    tags = {z["id"]: z["tag"] for z in scenario["environment"]["zones"]}

    alarms = DwellRule(threshold_s=15.0).run(world, tags)
    assert len(alarms) >= 2, "rule should fire on both the intruder and the commuter"

    truth = [
        TruthEvent(t_start=float(r["t_start"]), t_end=float(r["t_end"]),
                   label="suspicious.loiter")
        for r in (json.loads(x) for x in
                  (tmp_path / "gt" / "events.jsonl").read_text().splitlines() if x.strip())
        if r["label"].startswith("suspicious.loiter")
    ]
    result = score(truth, alarms, camera_hours=2 * 60 / 3600, tolerance_s=10.0)
    assert result.false_positives >= 1
    assert result.precision < 1.0


# --------------------------------------------------------------- PathLoiterRule
#
# These use synthetic tracks shaped like the `disguise_and_tamper` hero and the
# `worker_1` hard negative rather than re-running that 240 s scenario (~3 min in
# the mock backend — too slow to be part of the regular suite). The shapes were
# picked to reproduce the actual failure diagnosed on a real `survsim run` of
# `configs/scenarios/disguise_and_tamper.yaml`:
#   - the hero *paces* (speed well above any "stationary" cap) but never moves
#     more than a few metres from where the pacing started;
#   - `world.zone_of` now resolves overlapping zone polygons to the *smallest*
#     containing one, so a worker standing inside the (smaller) restricted zone
#     is correctly reported as being in the restricted zone, not the (larger)
#     enclosing public zone. (It used to return "first match in config order",
#     which silently hid the restricted-zone tag — see docs/11 "Bugs found".)
#     `PathLoiterRule` trusts `world_df["zone"]` directly for its role exemption;
#   - the worker is authorised in that zone (`allowed_roles: [worker, guard]`),
#     which is what a naive dwell-time rule with no context cannot express.
# Numbers measured on the real scenario (seed 11, tolerance_s=30):
#   DwellRule(threshold_s=60)        -> 0 alarms  (recall 0.0 on both loiter events)
#   PathLoiterRule(threshold_s=25)   -> recall 1.0, hero caught, worker never fires


def _pacing_track(uid: str, t0: float, n: float, dt: float = 0.1, zone: str | None = None) -> pd.DataFrame:
    """A person pacing back and forth over a ~3 m stretch — high instantaneous
    speed, bounded displacement, like `intruder_a`'s `suspicious.loiter.pace`."""
    import numpy as np

    ts = t0 + np.arange(n) * dt
    # Triangle wave across 3 m, at ~1.4 m/s (matches the hero's gait speed).
    period = 2 * 3.0 / 1.4
    phase = ((ts - t0) % period) / period
    x = np.where(phase < 0.5, phase * 2, 2 - phase * 2) * 3.0
    return pd.DataFrame(
        {"uid": uid, "t": ts, "x": x, "y": np.zeros(len(ts)), "zone": zone, "speed": 1.4}
    )


def _idle_track(uid: str, t0: float, n: float, x: float, y: float, dt: float = 0.1,
                zone: str | None = None) -> pd.DataFrame:
    """A person standing still, like the authorised `worker_1` `commute_wait`."""
    import numpy as np

    ts = t0 + np.arange(n) * dt
    return pd.DataFrame(
        {"uid": uid, "t": ts, "x": x, "y": y, "zone": zone, "speed": 0.0}
    )


_TEST_ZONES = [
    {"id": "zone.yard", "tag": "public", "polygon": [[-30, -30], [30, -30], [30, 30], [-30, 30]],
     "allowed_roles": []},
    {"id": "zone.substation", "tag": "restricted",
     "polygon": [[-28, 10], [-16, 10], [-16, 24], [-28, 24]], "allowed_roles": ["worker", "guard"]},
]


def test_dwell_rule_misses_the_pacing_hero() -> None:
    """The naive baseline's speed cap and exact-zone-tag match miss a pacer."""
    tags = {z["id"]: z["tag"] for z in _TEST_ZONES}
    hero = _pacing_track("intruder_a", t0=0.0, n=800)  # 80 s of pacing
    alarms = DwellRule(threshold_s=60.0).run(hero, tags)
    assert alarms == [], "the naive dwell rule should not catch a pacer at all"


def test_path_loiter_rule_catches_the_pacing_hero_and_spares_the_worker() -> None:
    """The headline fix: hero caught, authorised worker is not (regression for item 2)."""
    hero = _pacing_track("intruder_a", t0=0.0, n=800)  # 80 s of pacing, radius ~3 m
    # inside zone.substation — the `zone` column is what `World.zone_of` (smallest
    # containing zone) would have written; PathLoiterRule now trusts it directly.
    worker = _idle_track("worker_1", t0=0.0, n=1200, x=-20.0, y=15.0, zone="zone.substation")

    role_by_uid = {"intruder_a": "intruder", "worker_1": "worker"}
    rule = PathLoiterRule(threshold_s=25.0, radius_m=4.0, reentry_gap_s=15.0)

    hero_alarms = rule.run(hero, _TEST_ZONES, role_by_uid)
    worker_alarms = rule.run(worker, _TEST_ZONES, role_by_uid)

    assert len(hero_alarms) >= 1, "the pacing hero must be caught"
    assert worker_alarms == [], "the authorised worker in the restricted zone must not fire"


def test_street_crowd_far_has_20_60px_bucket() -> None:
    """docs/research/23 §9.2: `street_crowd` people are 60-200 px tall, leaving
    the 20-60 px bucket (the one report 18 says decides detector/tracker/ReID
    choices on real low-resolution CCTV) empty. `street_crowd_far` mounts the
    same crowd's cameras higher/farther so that bucket is populated."""
    far = Path(__file__).parent.parent / "configs" / "scenarios" / "street_crowd_far.yaml"
    sim = Simulator.from_yaml(far, engine="mock")
    with TemporaryDirectory() as tmp:
        sim.record(tmp, topdown_video=False)
        heights = []
        for mot in Path(tmp, "gt").glob("mot_*.txt"):
            for line in mot.read_text().splitlines():
                if not line.strip():
                    continue
                cols = line.split(",")
                heights.append(float(cols[5]))

    heights_arr = pd.Series(heights, dtype=float)
    assert len(heights_arr) > 0
    frac = ((heights_arr >= 20) & (heights_arr <= 60)).mean()
    assert 0.30 <= frac <= 0.60, f"20-60px bucket is {frac:.2%} of {len(heights_arr)} GT boxes"


def test_path_loiter_rule_still_fires_on_an_unauthorised_idle_dwell() -> None:
    """The role exemption must be scoped to the actual zone, not a blanket pass."""
    role_by_uid = {"passer_by": "commuter"}
    # Same spot (zone.substation) as the authorised worker, but a role that isn't
    # in that zone's allowed_roles — the exemption must not be a blanket pass.
    idle = _idle_track("passer_by", t0=0.0, n=1200, x=-20.0, y=15.0, zone="zone.substation")
    rule = PathLoiterRule(threshold_s=25.0, radius_m=4.0, reentry_gap_s=15.0)
    alarms = rule.run(idle, _TEST_ZONES, role_by_uid)
    assert len(alarms) >= 1


# ------------------------------------------------------------- World.zone_of


def test_zone_of_resolves_nested_zones_to_the_smallest_one() -> None:
    """Regression for item 1: a person standing in a small zone nested inside a
    larger one must be reported as being in the small zone, regardless of which
    one is declared first in `environment.zones`.

    `zone.store` sits fully inside `zone.yard` (a real config shape — see
    `configs/scenarios/smoke_mock.yaml` and `disguise_and_tamper.yaml`'s
    `zone.substation` inside `zone.yard`). Declaring the small zone *before* the
    large one exercises `zone_of` under either declaration order.
    """
    from survsim.core.models import Environment, Population, Scenario, Waypoint, Zone
    from survsim.director.world import World

    small = Zone(id="zone.small", tag="restricted",
                 polygon=[(-2, -2), (2, -2), (2, 2), (-2, 2)])
    large = Zone(id="zone.large", tag="public",
                 polygon=[(-20, -20), (20, -20), (20, 20), (-20, 20)])

    for order_name, zones in (("small_first", [small, large]), ("large_first", [large, small])):
        env = Environment(id="e", zones=zones,
                          spawn_points=[Waypoint(id="spawn.a", pos=(-15.0, 0.0, 0.0))],
                          exits=[Waypoint(id="exit.a", pos=(15.0, 0.0, 0.0))])
        scenario = Scenario(name="s", seed=1, duration_s=10, fps=5,
                            environment=env, population=Population(hero=[]))
        world = World(scenario)
        assert world.zone_of(np.array([0.0, 0.0])) == "zone.small", order_name
        assert world.zone_of(np.array([10.0, 10.0])) == "zone.large", order_name
        assert world.zone_of(np.array([100.0, 100.0])) is None, order_name


# ------------------------------------------------------------- loiter-arc jitter
#
# docs/research/58 "Simulator fixes this exposed": `loiter_arc` walked to the
# exact zone centroid while innocent destinations elsewhere (e.g. Transit) get
# `world.sample_goal`'s seeded jitter — a leak the forbidden-feature list for the
# H58 study had to exclude "distance to the zone centroid" to avoid. `Loiter.begin`
# (and therefore `SmokeBreak` and `CommuteWait`, both subclasses) now samples its
# destination the same way, so distance-to-zone-centre carries no label.


def _make_gate_world(seed: int = 1):
    from survsim.core.models import Environment, Person, Population, Scenario, Waypoint, Zone
    from survsim.director.world import Agent, World

    zone = Zone(id="zone.gate", tag="gate", polygon=[(8, -3), (14, -3), (14, 3), (8, 3)])
    env = Environment(id="e", zones=[zone],
                       spawn_points=[Waypoint(id="spawn.a", pos=(0.0, 0.0, 0.0))],
                       exits=[Waypoint(id="exit.a", pos=(-10.0, 0.0, 0.0))])
    scenario = Scenario(name="s", seed=seed, duration_s=600, fps=5,
                         environment=env, population=Population(hero=[]))
    world = World(scenario)
    person = Person(id="p")
    agent = Agent(spec=person, pos=np.array([0.0, 0.0]))
    world.agents["p"] = agent
    return world, agent, world.resolve_point("zone.gate")


def _dwell_centre_distances(behaviour_cls, world, agent, centroid, n: int) -> list[float]:
    out = []
    for _ in range(n):
        b = behaviour_cls({"zone": "zone.gate", "dur_s": 30.0, "activity": "pace"})
        b.begin(0.0, agent, world)
        out.append(float(np.hypot(b._centre[0] - centroid[0], b._centre[1] - centroid[1])))
    return out


def test_loiter_and_commute_wait_destination_jitter_is_indistinguishable() -> None:
    from scipy.stats import ks_2samp

    from survsim.director.behaviours import CommuteWait, Loiter

    world, agent, centroid = _make_gate_world(seed=7)
    loiter_d = _dwell_centre_distances(Loiter, world, agent, centroid, 200)
    commute_d = _dwell_centre_distances(CommuteWait, world, agent, centroid, 200)

    # The leak this guards against: walking straight to the centroid makes every
    # distance exactly 0.0, which would trivially "pass" a naive mean comparison
    # but is visibly degenerate — assert some spread exists on both sides first.
    assert max(loiter_d) > 0.1
    assert max(commute_d) > 0.1

    _stat, p = ks_2samp(loiter_d, commute_d)
    assert p > 0.05, f"loiter vs commute_wait destination distributions differ (KS p={p})"


def test_loiter_destination_sampling_is_deterministic() -> None:
    from survsim.director.behaviours import Loiter

    world_a, agent_a, centroid = _make_gate_world(seed=42)
    world_b, agent_b, _ = _make_gate_world(seed=42)

    seq_a = _dwell_centre_distances(Loiter, world_a, agent_a, centroid, 25)
    seq_b = _dwell_centre_distances(Loiter, world_b, agent_b, centroid, 25)
    assert seq_a == seq_b
