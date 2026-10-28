"""The alarm architecture: turning an unusable classifier into a usable system.

`docs/14` measures a trajectory classifier at AUC 0.72 and precision 0.074 — 93%
of its alarms are false, because suspicious behaviour is 3.3% of the data. No
amount of model improvement fixes that; it is the base rate. The research corpus
(R03, R05, H02) says the same thing about deployed systems, and says what does
work:

1. **Raise the threshold**, accepting lost recall for precision.
2. **Corroborate** with an independent channel before escalating.
3. **Require persistence** — a real loiterer is still there twenty seconds later,
   a spurious classification usually is not.
4. **Use context** — the same behaviour matters at a substation gate at 03:00 and
   does not in a public concourse at lunchtime.
5. **Budget the alarms** and let the operator's capacity, not the model, set the
   operating point.

Each stage trades recall for precision. Stacking them is how a 7%-precision
detector becomes an alarm stream someone can actually work, and the cost in
missed events is explicit rather than hidden.

`AlarmPipeline.run()` reports what survived each stage, so the trade is visible
instead of buried in a single tuned number.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .alarms import Alarm, AlarmScore, TruthEvent, score


@dataclass
class Candidate:
    """A potential alarm before the architecture has had its say."""

    t: float
    uid: str
    label: str
    confidence: float
    camera: str | None = None
    zone: str | None = None
    corroborating: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"t": round(self.t, 2), "uid": self.uid, "label": self.label,
                "confidence": round(self.confidence, 3), "zone": self.zone,
                "corroborating": self.corroborating}


@dataclass
class StageReport:
    name: str
    kept: int
    dropped: int
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return {"stage": self.name, "kept": self.kept, "dropped": self.dropped,
                "rationale": self.rationale}


@dataclass
class AlarmPipeline:
    """Gates candidate alarms through the stages that make a system deployable."""

    threshold: float = 0.5
    # Persistence: a genuine dwell-based event survives across consecutive
    # windows; a one-off misclassification usually does not.
    persistence_windows: int = 2
    persistence_span_s: float = 60.0
    require_corroboration: bool = False
    corroboration_min: float = 0.5
    # Zones where an event is worth an operator's attention at all.
    priority_zones: tuple[str, ...] = ()
    # Hours in which the site is closed, so presence is itself informative.
    after_hours: tuple[float, float] | None = None
    # Hard ceiling from the operator's capacity, applied last.
    max_alarms_per_camera_hour: float | None = None

    def run(
        self,
        candidates: Sequence[Candidate],
        camera_hours: float,
        hour_of_day: Callable[[float], float] | None = None,
    ) -> tuple[list[Alarm], list[StageReport]]:
        stages: list[StageReport] = []
        current = list(candidates)

        def record(name: str, kept: list, rationale: str) -> list:
            stages.append(StageReport(name, len(kept), len(current) - len(kept), rationale))
            return kept

        current = record(
            "threshold",
            [c for c in current if c.confidence >= self.threshold],
            f"confidence >= {self.threshold}: trades recall for precision")

        if self.priority_zones:
            current = record(
                "zone_context",
                [c for c in current if c.zone in self.priority_zones],
                f"only zones {list(self.priority_zones)}: the same behaviour is not "
                "equally interesting everywhere")

        if self.after_hours and hour_of_day is not None:
            lo, hi = self.after_hours
            def closed(t: float) -> bool:
                h = hour_of_day(t)
                return h >= lo or h < hi if lo > hi else lo <= h < hi
            current = record("after_hours", [c for c in current if closed(c.t)],
                             f"only between {lo:02.0f}:00 and {hi:02.0f}:00")

        if self.persistence_windows > 1:
            current = record(
                "persistence",
                self._persistent(current),
                f"{self.persistence_windows} detections within {self.persistence_span_s:.0f}s: "
                "a real dwell event is still there later, a glitch is not")

        if self.require_corroboration:
            current = record(
                "corroboration",
                [c for c in current
                 if any(v >= self.corroboration_min for v in c.corroborating.values())],
                "a second independent channel must agree — the strongest single "
                "false-alarm reduction available, provided the nuisances really are "
                "independent")

        # De-duplicate: one event should produce one alarm, not a stream.
        current = record("deduplicate", self._first_per_event(current),
                         "one alarm per person-event, not one per window")

        alarms = [Alarm(t=c.t, label=c.label, camera=c.camera) for c in sorted(
            current, key=lambda c: c.t)]

        if self.max_alarms_per_camera_hour is not None and camera_hours > 0:
            cap = int(self.max_alarms_per_camera_hour * camera_hours)
            if len(alarms) > cap:
                # Keep the most confident, because that is what an operator with
                # limited capacity would want surfaced first.
                by_conf = sorted(current, key=lambda c: -c.confidence)[:cap]
                alarms = [Alarm(t=c.t, label=c.label, camera=c.camera)
                          for c in sorted(by_conf, key=lambda c: c.t)]
                stages.append(StageReport(
                    "operator_budget", len(alarms), len(current) - len(alarms),
                    f"capped at {self.max_alarms_per_camera_hour}/camera-hour: the "
                    "operator's capacity sets the operating point, not the model"))

        return alarms, stages

    def _persistent(self, candidates: Sequence[Candidate]) -> list[Candidate]:
        by_key: dict[tuple[str, str], list[Candidate]] = {}
        for c in candidates:
            by_key.setdefault((c.uid, c.label), []).append(c)

        kept: list[Candidate] = []
        for group in by_key.values():
            group.sort(key=lambda c: c.t)
            for i, c in enumerate(group):
                window = [g for g in group[i:] if g.t - c.t <= self.persistence_span_s]
                if len(window) >= self.persistence_windows:
                    kept.append(c)
        return kept

    @staticmethod
    def _first_per_event(candidates: Sequence[Candidate], gap_s: float = 120.0) -> list[Candidate]:
        by_key: dict[tuple[str, str], list[Candidate]] = {}
        for c in candidates:
            by_key.setdefault((c.uid, c.label), []).append(c)
        kept: list[Candidate] = []
        for group in by_key.values():
            group.sort(key=lambda c: c.t)
            last = -1e9
            for c in group:
                if c.t - last > gap_s:
                    kept.append(c)
                    last = c.t
        return kept


def compare_architectures(
    candidates: Sequence[Candidate],
    truth: Sequence[TruthEvent],
    camera_hours: float,
    variants: dict[str, AlarmPipeline],
    tolerance_s: float = 10.0,
    hour_of_day: Callable[[float], float] | None = None,
) -> dict[str, Any]:
    """Score several architectures on the same candidates.

    The comparison is the argument: a raw detector and the same detector behind a
    verification chain differ enormously in operator experience while the
    underlying model is unchanged.
    """
    out: dict[str, Any] = {}
    for name, pipeline in variants.items():
        alarms, stages = pipeline.run(candidates, camera_hours, hour_of_day)
        result: AlarmScore = score(truth, alarms, camera_hours=camera_hours,
                                   tolerance_s=tolerance_s)
        out[name] = {
            "alarms": len(alarms),
            "precision": round(result.precision, 4),
            "recall": round(result.recall, 4),
            "f1": round(result.f1, 4),
            "false_alarms_per_camera_hour": round(result.false_alarms_per_camera_hour, 4),
            "within_operator_budget": result.operator_verdict()["within_budget"],
            "stages": [s.as_dict() for s in stages],
        }
    return out
