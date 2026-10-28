"""Does corroboration actually beat a better detector?

The multi-sensor argument is simple arithmetic: require two independent sensors to
agree and the false-alarm rate multiplies down while detection only degrades
linearly. A camera at 0.05 false alarms per hour AND-gated with an RF sensor at
0.1 gives 0.005 — a tenfold improvement no detector upgrade would deliver.

That arithmetic is also the trap. It holds **only if the nuisances are
independent**, and in the field they usually are not: wind moves vegetation *and*
rattles fences, rain degrades the camera *and* triggers the microphone, a lorry
shakes the fence sensor *and* appears in view. With correlated nuisance the AND
gate collapses toward the single-sensor rate while you have still paid for two
sensors and lost detections to the gate.

So `fuse()` takes a correlation term and reports both numbers, and
`independence_penalty()` quantifies how much of the promised gain evaporates. The
honest version of the multi-sensor pitch is: corroboration is powerful *if you can
show the failure modes are uncorrelated*, and that is an empirical claim about a
specific site, not a property of having two sensors.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SensorChannel:
    """One detection channel's measured operating point."""

    name: str
    p_detect: float                 # probability of catching a real event
    false_alarms_per_hour: float

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "p_detect": round(self.p_detect, 4),
                "false_alarms_per_hour": round(self.false_alarms_per_hour, 4)}


@dataclass
class FusionResult:
    mode: str
    p_detect: float
    false_alarms_per_hour: float
    channels: list[str]
    correlation: float = 0.0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "channels": self.channels,
                "p_detect": round(self.p_detect, 4),
                "false_alarms_per_hour": round(self.false_alarms_per_hour, 5),
                "correlation": round(self.correlation, 3), "notes": self.notes}


def fuse(
    channels: Sequence[SensorChannel],
    mode: str = "and",
    window_s: float = 10.0,
    correlation: float = 0.0,
) -> FusionResult:
    """Combine channels by requiring agreement (AND) or either (OR).

    `correlation` in [0, 1] is the share of each channel's nuisance that is driven
    by a common cause. At 0 the channels are independent and the AND gate delivers
    the textbook multiplicative reduction; at 1 every nuisance is shared and the
    gate delivers nothing.

    The AND coincidence rate accounts for the matching window: two independent
    Poisson streams only collide when one fires within `window_s` of the other.
    """
    if not channels:
        return FusionResult("none", 0.0, 0.0, [], correlation, ["no channels"])

    names = [c.name for c in channels]
    notes: list[str] = []

    if mode == "or":
        p_detect = 1.0 - float(np.prod([1.0 - c.p_detect for c in channels]))
        fa = float(sum(c.false_alarms_per_hour for c in channels))
        notes.append("OR raises detection but adds the false-alarm rates — usually the "
                     "wrong trade for an operator already near their alarm budget")
        return FusionResult("or", p_detect, fa, names, correlation, notes)

    # AND: every channel must fire for the same event.
    p_detect = float(np.prod([c.p_detect for c in channels]))

    window_h = window_s / 3600.0
    independent_rate = channels[0].false_alarms_per_hour
    for c in channels[1:]:
        # Coincidence rate of two Poisson processes within the window.
        independent_rate = independent_rate * c.false_alarms_per_hour * window_h * 2.0

    # The correlated share fires together by construction, so it survives the gate
    # at the rate of the weakest (lowest-rate) channel.
    common_rate = correlation * min(c.false_alarms_per_hour for c in channels)
    fa = (1.0 - correlation) * independent_rate + common_rate

    if correlation > 0.3:
        notes.append(
            f"correlation {correlation:.2f}: most nuisance is shared (weather, wind, "
            "vehicles), so the AND gate cannot suppress it — verify independence on "
            "site before claiming the fused rate")
    notes.append(f"AND costs detection: {p_detect:.3f} vs best single channel "
                 f"{max(c.p_detect for c in channels):.3f}")
    return FusionResult("and", p_detect, fa, names, correlation, notes)


def independence_penalty(channels: Sequence[SensorChannel], correlation: float,
                         window_s: float = 10.0) -> dict[str, Any]:
    """How much of the promised fusion gain the correlation destroys."""
    ideal = fuse(channels, "and", window_s, correlation=0.0)
    actual = fuse(channels, "and", window_s, correlation=correlation)
    best_single = min(c.false_alarms_per_hour for c in channels)

    promised = best_single - ideal.false_alarms_per_hour
    delivered = best_single - actual.false_alarms_per_hour
    return {
        "best_single_channel_fa_per_hour": round(best_single, 5),
        "ideal_fused_fa_per_hour": round(ideal.false_alarms_per_hour, 5),
        "actual_fused_fa_per_hour": round(actual.false_alarms_per_hour, 5),
        "gain_realised_fraction": round(delivered / promised, 4) if promised > 0 else 0.0,
        "correlation": correlation,
    }


# --------------------------------------------------------------- association


def associate_rf_to_tracks(
    rf_detections: Iterable[dict[str, Any]],
    track_positions: dict[str, np.ndarray],
    sniffer_positions: dict[str, np.ndarray],
    max_error_m: float = 12.0,
) -> dict[str, Any]:
    """Match RF MACs to visual tracks by comparing estimated and actual range.

    This is the concrete version of "a unified multi-sensor picture": if a MAC's
    RSSI-implied distance from a sniffer matches a visual track's distance from
    that same sniffer, they are plausibly the same person.

    Accuracy is reported against the ground-truth mapping, which no real
    deployment has — that is precisely why this experiment needs a simulator.
    """
    votes: dict[str, dict[str, int]] = {}
    truth: dict[str, str] = {}

    for det in rf_detections:
        mac = det["mac"]
        sniffer = sniffer_positions.get(det["sniffer"])
        if sniffer is None:
            continue
        if det.get("uid_truth"):
            truth[mac] = det["uid_truth"]
        est = float(det["est_distance_m"])
        for uid, pos in track_positions.items():
            actual = float(np.linalg.norm(np.asarray(sniffer)[:2] - np.asarray(pos)[:2]))
            if abs(actual - est) <= max_error_m:
                votes.setdefault(mac, {})
                votes[mac][uid] = votes[mac].get(uid, 0) + 1

    assignment = {mac: max(cand, key=cand.get) for mac, cand in votes.items() if cand}
    scored = [(mac, uid) for mac, uid in assignment.items() if mac in truth]
    correct = sum(uid == truth[mac] for mac, uid in scored)

    return {
        "n_macs": len(votes),
        "n_assigned": len(assignment),
        "n_scored": len(scored),
        "accuracy": round(correct / len(scored), 4) if scored else 0.0,
        "assignment": assignment,
    }
