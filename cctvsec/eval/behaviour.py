"""A learned behaviour classifier, and an honest comparison against the rule.

The dwell rule in `eval/rules.py` is what every vendor ships first, and on our
data it behaves exactly as the field reports: it fires on the intruder *and* on
the commuter waiting for a train, because they dwell for the same time. The
question this module answers is whether a model with access to richer trajectory
features can separate them — and if so, at what cost in false alarms.

Features are deliberately **trajectory-only**: dwell time, speed statistics, path
tortuosity, direction changes, zone revisits, distance to sensitive assets.
Nothing about appearance is used, and that is a design constraint rather than an
oversight. The evasion generator produces matched pairs where clothing carries no
label information, so any model reading appearance would be learning a shortcut
that does not transfer — and, in deployment, would amount to profiling.

The classifier is regularised logistic regression in pure NumPy. That is not a
limitation to apologise for: with a few hundred trajectory segments and ten
features, a linear model is the honest choice, its weights can be read and
argued with, and it gives a floor that a deep model has to beat to justify itself.

Splitting is by **identity**, never by segment. The same person appearing in both
train and test lets the model memorise them, which inflates the score and hides
the fact that it has learned nothing generalisable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

FEATURE_NAMES = (
    "duration_s",
    "dwell_fraction",        # share of time nearly stationary
    "mean_speed",
    "speed_std",
    "max_speed",
    "path_tortuosity",       # path length over net displacement
    "direction_changes",
    "radius_of_gyration",    # how tightly the track is clustered
    "zone_revisits",
    "n_zones_visited",
)


@dataclass
class Segment:
    """One person's trajectory over a window, with its truth label."""

    uid: str
    label: str
    t_start: float
    t_end: float
    xy: np.ndarray                      # Nx2 positions
    speeds: np.ndarray
    zones: list[str | None] = field(default_factory=list)
    hard_negative: bool = False

    @property
    def is_suspicious(self) -> bool:
        return self.label.startswith(("suspicious", "hostile"))


def extract_features(seg: Segment, still_speed: float = 0.35) -> np.ndarray:
    """Trajectory descriptors. No appearance, by design."""
    xy = np.asarray(seg.xy, dtype=float).reshape(-1, 2)
    speeds = np.asarray(seg.speeds, dtype=float).ravel()
    duration = max(seg.t_end - seg.t_start, 1e-6)

    if len(xy) < 2:
        return np.zeros(len(FEATURE_NAMES))

    steps = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    path_length = float(steps.sum())
    net = float(np.linalg.norm(xy[-1] - xy[0]))
    # Tortuosity: a straight crossing is ~1, pacing in a circle is large. This is
    # the feature that most cleanly separates "waiting" from "patrolling a spot".
    tortuosity = path_length / max(net, 0.5)

    heading = np.arctan2(np.diff(xy[:, 1]), np.diff(xy[:, 0]))
    turns = np.abs(np.diff(heading))
    turns = np.minimum(turns, 2 * np.pi - turns)
    direction_changes = float((turns > np.radians(45)).sum()) / max(len(turns), 1)

    centroid = xy.mean(axis=0)
    gyration = float(np.sqrt(((xy - centroid) ** 2).sum(axis=1).mean()))

    zones = [z for z in seg.zones if z]
    revisits = 0
    seen: set[str] = set()
    previous = None
    for z in zones:
        if z != previous:
            if z in seen:
                revisits += 1
            seen.add(z)
            previous = z

    return np.array([
        duration,
        float((speeds < still_speed).mean()) if speeds.size else 0.0,
        float(speeds.mean()) if speeds.size else 0.0,
        float(speeds.std()) if speeds.size else 0.0,
        float(speeds.max()) if speeds.size else 0.0,
        tortuosity,
        direction_changes,
        gyration,
        float(revisits),
        float(len(seen)),
    ])


def segments_from_world(world_df, window_s: float = 30.0, step_s: float = 15.0,
                        min_points: int = 5) -> list[Segment]:
    """Cut `world.parquet` into overlapping per-person windows."""
    segments: list[Segment] = []
    for uid, person in world_df.sort_values(["uid", "t"]).groupby("uid", sort=False):
        t = person["t"].to_numpy()
        if len(t) < min_points:
            continue
        start, end = float(t.min()), float(t.max())
        cursor = start
        while cursor < end:
            window = person[(person["t"] >= cursor) & (person["t"] < cursor + window_s)]
            cursor += step_s
            if len(window) < min_points:
                continue
            labels = window["label"].tolist()
            # The window's label is its most severe behaviour: a window containing
            # a tamper is a tamper window even if most of it is walking.
            label = max(labels, key=lambda x: (x.startswith(("suspicious", "hostile")),
                                               labels.count(x)))
            segments.append(Segment(
                uid=str(uid), label=str(label),
                t_start=float(window["t"].min()), t_end=float(window["t"].max()),
                xy=window[["x", "y"]].to_numpy(),
                speeds=window["speed"].to_numpy(),
                zones=window["zone"].tolist(),
            ))
    return segments


# --------------------------------------------------------------- classifier


@dataclass
class BehaviourClassifier:
    """Regularised logistic regression with standardised features."""

    l2: float = 1.0
    lr: float = 0.15
    epochs: int = 600
    weights: np.ndarray | None = None
    bias: float = 0.0
    mean_: np.ndarray | None = None
    std_: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> BehaviourClassifier:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        self.mean_ = x.mean(axis=0)
        # Features live on wildly different scales (seconds vs fractions), so an
        # unstandardised fit is dominated by whichever has the largest units.
        self.std_ = np.maximum(x.std(axis=0), 1e-6)
        xs = (x - self.mean_) / self.std_

        n, d = xs.shape
        self.weights = np.zeros(d)
        self.bias = 0.0
        # Class weighting: suspicious behaviour is rare by construction, and an
        # unweighted fit would simply predict "normal" for everything.
        pos = max(float(y.sum()), 1.0)
        neg = max(float(len(y) - y.sum()), 1.0)
        sample_w = np.where(y > 0.5, neg / pos, 1.0)

        for _ in range(self.epochs):
            p = _sigmoid(xs @ self.weights + self.bias)
            err = (p - y) * sample_w
            grad_w = xs.T @ err / n + self.l2 * self.weights / n
            grad_b = float(err.mean())
            self.weights -= self.lr * grad_w
            self.bias -= self.lr * grad_b
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.weights is None or self.mean_ is None or self.std_ is None:
            raise RuntimeError("classifier is not fitted")
        xs = (np.asarray(x, dtype=float) - self.mean_) / self.std_
        return _sigmoid(xs @ self.weights + self.bias)

    def importance(self) -> dict[str, float]:
        """Standardised weights — readable, and arguable with a domain expert."""
        if self.weights is None:
            return {}
        return {name: round(float(w), 4)
                for name, w in sorted(zip(FEATURE_NAMES, self.weights),
                                      key=lambda kv: -abs(kv[1]))}


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


# ------------------------------------------------------------------ protocol


def split_by_identity(segments: Sequence[Segment], test_fraction: float = 0.3,
                      seed: int = 0) -> tuple[list[Segment], list[Segment]]:
    """Split so no identity appears in both halves.

    Splitting by segment instead lets the model memorise individuals and inflates
    every score — the single most common way a behaviour result is accidentally
    meaningless.
    """
    uids = sorted({s.uid for s in segments})
    rng = np.random.default_rng(seed)
    rng.shuffle(uids)
    n_test = max(1, round(len(uids) * test_fraction))
    test_ids = set(uids[:n_test])
    return ([s for s in segments if s.uid not in test_ids],
            [s for s in segments if s.uid in test_ids])


def evaluate_classifier(
    model: BehaviourClassifier,
    segments: Sequence[Segment],
    threshold: float = 0.5,
    camera_hours: float = 1.0,
) -> dict[str, Any]:
    """Score a classifier in operational terms, not just accuracy."""
    if not segments:
        return {"n": 0}
    x = np.stack([extract_features(s) for s in segments])
    y = np.array([s.is_suspicious for s in segments], dtype=float)
    p = model.predict_proba(x)
    pred = p >= threshold

    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)

    hard = [s for s in segments if s.hard_negative]
    hard_fp = sum(bool(pred[i]) for i, s in enumerate(segments) if s.hard_negative)

    # With no positives (or no negatives) every metric here is undefined. Returning
    # AUC 0.5 silently would look like an honest chance-level result rather than
    # "this evaluation could not be performed", which is a very different message.
    degenerate = bool(y.sum() == 0 or y.sum() == len(y))

    return {
        "n": len(segments),
        "n_suspicious": int(y.sum()),
        "degenerate": degenerate,
        "degenerate_reason": (
            None if not degenerate else
            "test split contains only one class, so AUC and precision are undefined; "
            "generate more scenes to get more distinct suspicious identities"
        ),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4),
        "false_alarms": fp,
        "false_alarms_per_camera_hour": round(fp / max(camera_hours, 1e-9), 3),
        # The number that matters: how often it fires on innocent people who look
        # the same to a dwell rule.
        "hard_negative_false_alarm_rate": round(hard_fp / len(hard), 4) if hard else None,
        "auc": round(_auc(y, p), 4),
    }


def _auc(y: np.ndarray, scores: np.ndarray) -> float:
    pos, neg = scores[y == 1], scores[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order), dtype=float)
    ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def compare_with_dwell_rule(segments: Sequence[Segment], dwell_threshold_s: float = 30.0,
                            still_speed: float = 0.35) -> dict[str, Any]:
    """The floor a learned model must beat: dwell time alone."""
    y = np.array([s.is_suspicious for s in segments], dtype=float)
    pred = np.array([
        (extract_features(s, still_speed)[1] * (s.t_end - s.t_start)) >= dwell_threshold_s
        for s in segments
    ])
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "rule": f"dwell >= {dwell_threshold_s}s",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4),
        "false_alarms": fp,
    }
