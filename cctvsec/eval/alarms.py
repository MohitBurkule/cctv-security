"""Event-level scoring in the form security evaluation actually uses.

Two things here differ from the academic default, and both come straight from the
research dossiers:

1. **A late alarm is a false alarm.** The i-LIDS protocol credits a detection only
   if it fires within a tolerance window of the event start (10 s by convention).
   Frame-level AUC, the usual academic metric, cannot express this at all: an alarm
   raised after the intruder has gone scores as a hit.

2. **The operating point is alarms per camera-hour, not FPPI.** Research systems
   are routinely tuned near 6 false alarms per camera-hour; a 500-camera estate
   with one operator, absorbing 4 nuisance alarms per 8-hour shift before they
   start being ignored, can afford roughly `DEFAULT_BUDGET_FA_PER_CAMERA_HOUR`
   (0.001) per camera-hour. That gap of three-plus orders of magnitude is why a
   detector that looks excellent on a benchmark is unusable on a site, and it is
   the number a simulator should report by default.

Repeat alarms on an event already detected count as false positives, not free
extra credit — otherwise a system that fires continuously scores perfectly.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_TOLERANCE_S = 10.0
DEFAULT_FA_COALESCE_S = 5.0

#: `operator_verdict`'s default budget: A = 4 nuisance alarms an operator can
#: absorb per shift before starting to ignore the system, K = 500 cameras per
#: operator, H = 8-hour shift. B = A / (K * H) = 4 / (500 * 8) = 0.001 false
#: alarms per camera-hour. docs/research/28_BEHAVIOUR_SCENE_DEEP_DIVE.md §7.1
#: derives the same number from this module's own A/K/H and flags that the
#: module docstring used to say "roughly 0.005" -- a 5x error in the text, not
#: in the formula, now fixed to match what the code actually computes.
DEFAULT_BUDGET_A_PER_SHIFT = 4.0
DEFAULT_BUDGET_CAMERAS_PER_OPERATOR = 500
DEFAULT_BUDGET_SHIFT_HOURS = 8.0
DEFAULT_BUDGET_FA_PER_CAMERA_HOUR = (
    DEFAULT_BUDGET_A_PER_SHIFT / (DEFAULT_BUDGET_CAMERAS_PER_OPERATOR * DEFAULT_BUDGET_SHIFT_HOURS)
)


@dataclass(frozen=True)
class Alarm:
    t: float
    label: str
    camera: str | None = None
    uid: str | None = None
    #: estimated (x, y) position of the alarmed track at alarm time, metres. Only
    #: required for `scoring="position_time"` (docs/research/32 H62); `None`
    #: elsewhere is unaffected.
    pos: tuple[float, float] | None = None


@dataclass(frozen=True)
class TruthEvent:
    t_start: float
    t_end: float
    label: str
    actors: tuple[str, ...] = ()
    hard_negative: bool = False
    #: true (x, y) position of the offending actor(s) at `t_start`, metres, keyed
    #: by uid. Only required for `position_radius_m` scoring.
    actor_pos: dict[str, tuple[float, float]] | None = None
    #: (x, y) positions of other people (not offending) present near this event
    #: at `t_start`, keyed by uid. Used only to report the false-credit rate for
    #: `position_radius_m` scoring -- a hit whose radius also contains a
    #: bystander is credited (position_time does not require identity) but
    #: flagged as ambiguous.
    bystander_pos: dict[str, tuple[float, float]] | None = None


@dataclass
class AlarmScore:
    true_positives: int
    false_negatives: int
    false_positives: int
    repeat_alarms: int
    latencies_s: list[float]
    camera_hours: float
    by_label: dict[str, dict[str, int]]
    bystander_hits: int = 0
    window_only_recall: float | None = None
    #: recall under `position_radius_m` scoring (docs/research/32 H62): a hit
    #: iff the alarm's estimated position at alarm time is within the radius of
    #: the true offending actor's position, independent of the alarm's `uid` --
    #: label-swap-proof by construction. `None` unless `position_radius_m` was
    #: passed to `score()`.
    position_time_recall: float | None = None
    #: of `position_time` hits, the fraction whose radius also contained a
    #: bystander (`TruthEvent.bystander_pos`) -- an ambiguous attribution the
    #: position-only rule cannot resolve on its own. `None` unless
    #: `position_radius_m` was passed and at least one position_time hit
    #: occurred with bystander data available.
    position_time_false_credit_rate: float | None = None

    @property
    def recall(self) -> float:
        total = self.true_positives + self.false_negatives
        return self.true_positives / total if total else 0.0

    @property
    def precision(self) -> float:
        raised = self.true_positives + self.false_positives
        return self.true_positives / raised if raised else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def false_alarms_per_camera_hour(self) -> float:
        return self.false_positives / self.camera_hours if self.camera_hours else float("inf")

    @property
    def mean_latency_s(self) -> float:
        return sum(self.latencies_s) / len(self.latencies_s) if self.latencies_s else float("nan")

    def operator_verdict(
        self, cameras_per_operator: int = DEFAULT_BUDGET_CAMERAS_PER_OPERATOR
    ) -> dict[str, Any]:
        """Translate the rate into the only question a control room asks.

        The tolerance below is the widely cited figure that operators begin
        ignoring a system after a handful of bad alarms per shift; see
        `DEFAULT_BUDGET_*` above for where the numbers come from.
        """
        per_hour_for_operator = self.false_alarms_per_camera_hour * cameras_per_operator
        budget_per_camera_hour = DEFAULT_BUDGET_A_PER_SHIFT / (
            cameras_per_operator * DEFAULT_BUDGET_SHIFT_HOURS
        )
        return {
            "cameras_per_operator": cameras_per_operator,
            "false_alarms_per_camera_hour": round(self.false_alarms_per_camera_hour, 5),
            "false_alarms_per_operator_hour": round(per_hour_for_operator, 2),
            "budget_per_camera_hour": round(budget_per_camera_hour, 6),
            "within_budget": self.false_alarms_per_camera_hour <= budget_per_camera_hour,
            "over_budget_factor": (
                round(self.false_alarms_per_camera_hour / budget_per_camera_hour, 1)
                if budget_per_camera_hour
                else float("inf")
            ),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "true_positives": self.true_positives,
            "false_negatives": self.false_negatives,
            "false_positives": self.false_positives,
            "repeat_alarms": self.repeat_alarms,
            "bystander_hits": self.bystander_hits,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "window_only_recall": (
                round(self.window_only_recall, 4) if self.window_only_recall is not None else None
            ),
            "position_time_recall": (
                round(self.position_time_recall, 4) if self.position_time_recall is not None else None
            ),
            "position_time_false_credit_rate": (
                round(self.position_time_false_credit_rate, 4)
                if self.position_time_false_credit_rate is not None
                else None
            ),
            "f1": round(self.f1, 4),
            "mean_latency_s": round(self.mean_latency_s, 3) if self.latencies_s else None,
            "camera_hours": round(self.camera_hours, 4),
            "false_alarms_per_camera_hour": round(self.false_alarms_per_camera_hour, 5),
            "by_label": self.by_label,
            "operator_verdict": self.operator_verdict(),
        }


def score(
    truth: Iterable[TruthEvent],
    alarms: Iterable[Alarm],
    camera_hours: float,
    tolerance_s: float = DEFAULT_TOLERANCE_S,
    labels: set[str] | None = None,
    ilids_compat: bool = False,
    fa_coalesce_s: float = DEFAULT_FA_COALESCE_S,
    actor_aware: bool | None = None,
    position_radius_m: float | None = None,
) -> AlarmScore:
    """Score alarms against truth with the i-LIDS timing rule.

    An alarm matches an event when the labels agree and it lands between the event
    start and `tolerance_s` after it. Each event can be detected once.

    `actor_aware` (default `None`, meaning **auto**: `True` if any alarm carries a
    `uid`, else `False`) additionally requires the alarm's `uid` to be one of the
    event's `actors` before it can match. Without it (or when no alarm has a
    `uid`), matching is window-only: two events with the same label whose windows
    overlap (e.g. a `disguise_swap` scan loiter starting within `tolerance_s` of
    an unrelated plain loiter) let only the earlier one be matched, and the
    second alarm for the second person is scored as a repeat -- capping recall at
    well below 1.0 even for a label oracle (docs/research/58 §4). An alarm with
    no `uid` (e.g. a rule that never emits actor identity) falls back to the
    window-only rule for that alarm, so `actor_aware=True` never regresses a rule
    that does not carry actor identity. Since round 2 (docs/13), an alarm on the
    wrong person is not a hit: **actor-aware matching is now the default**
    whenever alarms carry uids, and callers that want the old, window-only
    number can still get it by passing `actor_aware=False` explicitly, or by
    reading `AlarmScore.window_only_recall`, which this function always fills in
    alongside the resolved result so both numbers are available in one call.

    `ilids_compat` (default False, so existing numbers do not move) switches on
    two things the i-LIDS protocol itself does that SurvSim's default scoring is
    harsher than (docs/research/19 §5.1 "Divergence to fix"):

    `position_radius_m` (default `None`) additionally scores a **third, position/time**
    mode alongside whichever of the two above is resolved (docs/research/32 H62,
    from AUDIT_TAILGATER_RECONCILIATION): a hit iff the alarm lands in the
    event's `[t_start, t_start + tolerance_s]` window (same as window-only --
    label plus timing) AND its `pos` is within `position_radius_m` metres of the
    event's true offending actor position (`TruthEvent.actor_pos`). It never
    consults `uid`, so a tracker's identity switch cannot cost it a hit the way
    it costs `actor_aware` one (H59): the alarm is scored on where and when it
    fired, not on which label a possibly-swapped track carried. The result is
    reported in `AlarmScore.position_time_recall` and is never used to resolve
    `resolved_actor_aware` or the primary `recall` property -- it is purely an
    additional, opt-in number a caller must read explicitly, exactly like
    `window_only_recall`. Alarms or events missing position data are treated as
    non-matching for this mode only (so passing `position_radius_m` for alarms
    with no `pos` degrades gracefully to 0 position_time hits, not a crash).
    `AlarmScore.position_time_false_credit_rate` is the fraction of
    position_time hits for which `TruthEvent.bystander_pos` also has a person
    within the radius -- i.e. the position rule alone could not tell the true
    actor from a nearby bystander at that hit (`None` if no bystander data was
    supplied for any hit).

    1. **Repeats inside an already-matched event's window do not count as false
       positives at all.** i-LIDS "disregards" them; SurvSim's default mode
       penalises them (`repeat_alarms`) so a chattering system does not score
       perfectly, which is the right choice operationally but is not the i-LIDS
       number.
    2. **False positives closer together than `fa_coalesce_s` (5 s by the i-LIDS
       convention) are logged as one.** "Where a system false alarms several
       times in quick succession, only one false positive alarm will be logged
       every five seconds."
    """
    truth_list = [e for e in truth if labels is None or e.label in labels]
    alarm_list = sorted(
        (a for a in alarms if labels is None or a.label in labels), key=lambda a: a.t
    )

    # Auto mode: actor-aware matching is the default whenever any alarm carries a
    # uid to be actor-aware about; otherwise there is nothing to gain from it, and
    # it stays window-only, matching the pre-round-2 numbers exactly.
    resolved_actor_aware = (
        any(a.uid is not None for a in alarm_list) if actor_aware is None else actor_aware
    )

    def _match(use_actor_aware: bool) -> tuple[dict[int, float], int, int]:
        matched: dict[int, float] = {}
        repeats = 0
        false_positives = 0
        last_fa_t: dict[str, float] = {}  # per label, for fa_coalesce_s

        for alarm in alarm_list:
            hit = None
            for i, ev in enumerate(truth_list):
                if ev.label != alarm.label:
                    continue
                if (
                    use_actor_aware
                    and alarm.uid is not None
                    and ev.actors
                    and alarm.uid not in ev.actors
                ):
                    continue
                if ev.t_start <= alarm.t <= ev.t_start + tolerance_s:
                    hit = i
                    break
            if hit is None:
                # Includes alarms that are "correct but late": real event, missed window.
                if ilids_compat:
                    last = last_fa_t.get(alarm.label)
                    if last is not None and alarm.t - last < fa_coalesce_s:
                        continue
                    last_fa_t[alarm.label] = alarm.t
                false_positives += 1
            elif hit in matched:
                repeats += 1
                if not ilids_compat:
                    false_positives += 1
            else:
                matched[hit] = alarm.t - truth_list[hit].t_start
        return matched, repeats, false_positives

    matched, repeats, false_positives = _match(resolved_actor_aware)

    # Bystander hits: alarms that land inside a matching event's detection window
    # (label + timing) but name a uid that is not one of that event's actors --
    # i.e. an alarm on the wrong person, which docs/13 says is not a hit even
    # though window-only matching would have credited it.
    bystander_hits = 0
    for alarm in alarm_list:
        if alarm.uid is None:
            continue
        for ev in truth_list:
            if ev.label != alarm.label or not ev.actors:
                continue
            if ev.t_start <= alarm.t <= ev.t_start + tolerance_s and alarm.uid not in ev.actors:
                bystander_hits += 1
                break

    # Always compute the window-only recall too, so a report can show both
    # numbers even when actor-aware matching is the one actually used.
    if resolved_actor_aware:
        window_only_matched, _, _ = _match(False)
        window_only_recall = (
            len(window_only_matched) / len(truth_list) if truth_list else 0.0
        )
    else:
        window_only_recall = len(matched) / len(truth_list) if truth_list else 0.0

    by_label: dict[str, dict[str, int]] = {}
    for i, ev in enumerate(truth_list):
        row = by_label.setdefault(ev.label, {"truth": 0, "detected": 0})
        row["truth"] += 1
        row["detected"] += int(i in matched)

    position_time_recall = None
    position_time_false_credit_rate = None
    if position_radius_m is not None:
        import math

        pt_matched: dict[int, float] = {}
        fc_eligible = 0
        fc_hits = 0
        for alarm in alarm_list:
            if alarm.pos is None:
                continue
            best: tuple[int, float] | None = None
            for i, ev in enumerate(truth_list):
                if ev.label != alarm.label or not ev.actor_pos:
                    continue
                if not (ev.t_start <= alarm.t <= ev.t_start + tolerance_s):
                    continue
                d = min(
                    math.hypot(alarm.pos[0] - p[0], alarm.pos[1] - p[1])
                    for p in ev.actor_pos.values()
                )
                if d <= position_radius_m and (best is None or i < best[0]):
                    best = (i, d)
            if best is None:
                continue
            i, _d = best
            if i in pt_matched:
                continue
            pt_matched[i] = alarm.t - truth_list[i].t_start
            ev = truth_list[i]
            if ev.bystander_pos:
                fc_eligible += 1
                if any(
                    math.hypot(alarm.pos[0] - p[0], alarm.pos[1] - p[1]) <= position_radius_m
                    for p in ev.bystander_pos.values()
                ):
                    fc_hits += 1
        position_time_recall = len(pt_matched) / len(truth_list) if truth_list else 0.0
        position_time_false_credit_rate = fc_hits / fc_eligible if fc_eligible else None

    return AlarmScore(
        true_positives=len(matched),
        false_negatives=len(truth_list) - len(matched),
        false_positives=false_positives,
        repeat_alarms=repeats,
        latencies_s=list(matched.values()),
        camera_hours=camera_hours,
        by_label=by_label,
        bystander_hits=bystander_hits,
        window_only_recall=window_only_recall,
        position_time_recall=position_time_recall,
        position_time_false_credit_rate=position_time_false_credit_rate,
    )


# ------------------------------------------------------------------- run helpers


def load_truth(run_dir: Path, labels_prefix: str | None = None) -> list[TruthEvent]:
    path = Path(run_dir) / "gt" / "events.jsonl"
    out: list[TruthEvent] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if labels_prefix and not row["label"].startswith(labels_prefix):
            continue
        out.append(
            TruthEvent(
                t_start=float(row["t_start"]),
                t_end=float(row["t_end"] if row["t_end"] is not None else row["t_start"]),
                label=row["label"],
                actors=tuple(row.get("actors", [])),
            )
        )
    return out


def camera_hours_of(run_dir: Path) -> float:
    """Total observed camera time, which is the denominator of the alarm rate."""
    scenario = json.loads((Path(run_dir) / "meta" / "scenario.resolved.json").read_text())
    n_cams = max(1, len(scenario.get("cameras", [])))
    return n_cams * float(scenario.get("duration_s", 0.0)) / 3600.0


def load_alarms(path: Path) -> list[Alarm]:
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    return [
        Alarm(t=float(r["t"]), label=r["label"], camera=r.get("camera"), uid=r.get("uid"))
        for r in rows
    ]
