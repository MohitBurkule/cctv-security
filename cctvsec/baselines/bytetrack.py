"""Minimal ByteTrack (Zhang et al., ECCV 2022) in numpy.

Two-stage association: high-score detections are matched to all tracks by IoU
with a Kalman-predicted box, then low-score detections rescue the tracks left
over. Unmatched high-score detections start tentative tracks that are confirmed
on their second hit. This is the published algorithm minus camera-motion
compensation and the per-sequence thresholds the leaderboard entries tune.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..eval.detection import iou_matrix


class _KF:
    """Constant-velocity Kalman filter on (cx, cy, a, h), as in SORT/ByteTrack."""

    _F = np.eye(8)
    _F[:4, 4:] = np.eye(4)
    _H = np.eye(4, 8)
    _I8 = np.eye(8)

    def __init__(self, xywh: Sequence[float]) -> None:
        x, y, w, h = xywh
        self.x = np.array([x + w / 2, y + h / 2, w / max(h, 1e-6), h, 0, 0, 0, 0], float)
        s = [2 * h / 20, 2 * h / 20, 1e-2, 2 * h / 20, 10 * h / 160, 10 * h / 160, 1e-5, 10 * h / 160]
        self.P = np.diag(np.square(s))

    # `predict` only ever needs the process-noise half of what used to be `_q()`
    # and `update` only the observation-noise half; computing (and `np.diag`-ing)
    # both every call, on every track, every frame, was half wasted work — this
    # is the dominant cost of `ByteTracker.update` on dense MOT20 sequences
    # (>100 tracks/frame). Same arithmetic, so results are bit-identical.
    def _process_noise(self) -> np.ndarray:
        h = self.x[3]
        return np.diag(np.square([h / 20, h / 20, 1e-2, h / 20, h / 160, h / 160, 1e-5, h / 160]))

    def _obs_noise(self) -> np.ndarray:
        h = self.x[3]
        return np.diag(np.square([h / 20, h / 20, 1e-1, h / 20]))

    def predict(self) -> None:
        q = self._process_noise()
        self.x = self._F @ self.x
        self.P = self._F @ self.P @ self._F.T + q

    def update(self, xywh: Sequence[float]) -> None:
        x, y, w, h = xywh
        z = np.array([x + w / 2, y + h / 2, w / max(h, 1e-6), h])
        r = self._obs_noise()
        S = self._H @ self.P @ self._H.T + r
        K = self.P @ self._H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (z - self._H @ self.x)
        self.P = (self._I8 - K @ self._H) @ self.P

    @property
    def xywh(self) -> list[float]:
        cx, cy, a, h = self.x[:4]
        w = a * h
        return [cx - w / 2, cy - h / 2, w, h]


class _Track:
    def __init__(self, box, score, tid):
        self.kf = _KF(box)
        self.score = score
        self.id = tid
        self.hits = 1
        self.lost = 0
        self.confirmed = False
        self.feat: np.ndarray | None = None


def _unit(e) -> np.ndarray:
    e = np.asarray(e, float)
    return e / (np.linalg.norm(e) + 1e-12)


def _match(tracks, boxes, thresh, gate: bool = False, app: np.ndarray | None = None,
           app_weight: float = 0.0, app_only: bool = False):
    if not tracks or not len(boxes):
        return [], list(range(len(tracks))), list(range(len(boxes)))
    t = np.array([tr.kf.xywh for tr in tracks]).reshape(-1, 4)
    iou = iou_matrix(t, np.asarray(boxes, float).reshape(-1, 4))
    if app is not None and app_only:
        # H46b: appearance-only cost (the (1-iou) geometry term dropped entirely);
        # the IoU >= thresh gate below is still applied post-solve, unchanged.
        r, c = linear_sum_assignment(app)
    elif app is not None and app_weight > 0:
        # H24: same solve-then-filter as the control, only the cost gains an appearance
        # term; IoU-infeasible pairs are still discarded after solving.
        r, c = linear_sum_assignment((1 - iou) + app_weight * app)
    elif gate:
        # docs/13 fix 2: forbid sub-threshold pairs *before* solving, so the solver
        # never spends a track on a pair that would be discarded afterwards.
        cost = -iou
        cost[iou < thresh] = 1e6
        r, c = linear_sum_assignment(cost)
    else:
        r, c = linear_sum_assignment(-iou)
    m = [(i, j) for i, j in zip(r, c) if iou[i, j] >= thresh]
    mi = {i for i, _ in m}
    mj = {j for _, j in m}
    return (m, [i for i in range(len(tracks)) if i not in mi],
            [j for j in range(len(boxes)) if j not in mj])


class ByteTracker:
    """`fixed=True` applies docs/13's proposed fix (high/low split at tau=0.6 and
    gate-before-solve); `gate` alone toggles only the latter. The default path is
    the original tracker, bit-identical (tests/test_experiments.py)."""

    def __init__(self, high: float | None = None, low: float = 0.1, new_track: float = 0.6,
                 match_iou: float = 0.2, low_iou: float = 0.5, max_lost: int = 30,
                 fixed: bool = False, gate: bool | None = None, app_weight: float = 0.0,
                 ema: float = 0.9, app_only: bool = False) -> None:
        high = (0.6 if fixed else 0.5) if high is None else high
        self.gate = fixed if gate is None else gate
        self.high, self.low, self.new = high, low, new_track
        self.match_iou, self.low_iou, self.max_lost = match_iou, low_iou, max_lost
        self.tracks: list[_Track] = []
        self._next = 1
        self.app_weight, self.ema, self.app_only = app_weight, ema, app_only

    def update(self, dets: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """dets: [{bbox: xywh, score}] -> confirmed tracks [{id, bbox, score}] this frame."""
        for t in self.tracks:
            t.kf.predict()
        hi = [d for d in dets if d["score"] >= self.high]
        lo = [d for d in dets if self.low <= d["score"] < self.high]
        app = self._app_cost(hi) if (self.app_weight > 0 or self.app_only) else None
        m1, left_t, left_d = _match(self.tracks, [d["bbox"] for d in hi], self.match_iou, self.gate,
                                    app, self.app_weight, self.app_only)
        for i, j in m1:
            self._hit(self.tracks[i], hi[j])
            self._feat(self.tracks[i], hi[j])
        rest = [self.tracks[i] for i in left_t]
        m2, _left2, _ = _match(rest, [d["bbox"] for d in lo], self.low_iou, self.gate)
        for i, j in m2:
            self._hit(rest[i], lo[j])
        matched = {id(self.tracks[i]) for i, _ in m1} | {id(rest[i]) for i, _ in m2}
        for t in self.tracks:
            if id(t) not in matched:
                t.lost += 1
        # Unconfirmed tracks die on their first miss; confirmed ones after max_lost.
        self.tracks = [t for t in self.tracks
                       if (t.confirmed and t.lost <= self.max_lost) or (not t.confirmed and t.lost == 0)]
        for j in left_d:
            if hi[j]["score"] >= self.new:
                self.tracks.append(_Track(hi[j]["bbox"], hi[j]["score"], self._next))
                self._feat(self.tracks[-1], hi[j])
                self._next += 1
        return [{"id": t.id, "bbox": t.kf.xywh, "score": t.score}
                for t in self.tracks if t.confirmed and t.lost == 0]

    def _app_cost(self, dets: Sequence[dict[str, Any]]) -> np.ndarray | None:
        """1 - cos(track EMA feature, det feature) in [0, 1]; 0 where either side has none."""
        if not self.tracks or not dets:
            return None
        tf = [t.feat for t in self.tracks]
        de = [d.get("emb") for d in dets]
        dim = next((len(x) for x in (*tf, *de) if x is not None), 0)
        if not dim:
            return None
        T = np.array([f if f is not None else np.zeros(dim) for f in tf])
        D = np.array([_unit(e) if e is not None else np.zeros(dim) for e in de])
        A = np.clip(1.0 - T @ D.T, 0.0, 1.0)
        A[[f is None for f in tf], :] = 0.0
        A[:, [e is None for e in de]] = 0.0
        return A

    def _feat(self, t: _Track, d: dict[str, Any]) -> None:
        e = d.get("emb")
        if e is None or (self.app_weight <= 0 and not self.app_only):
            return
        e = _unit(e)
        f = e if t.feat is None else self.ema * t.feat + (1 - self.ema) * e
        t.feat = f / (np.linalg.norm(f) + 1e-12)

    @staticmethod
    def _hit(t: _Track, d: dict[str, Any]) -> None:
        t.kf.update(d["bbox"])
        t.score = d["score"]
        t.hits += 1
        t.lost = 0
        t.confirmed = t.confirmed or t.hits >= 2


def track_sequence(dets_by_frame: dict[int, list[dict[str, Any]]], frames: Sequence[int],
                   **kw: Any) -> list[dict[str, Any]]:
    tracker = ByteTracker(**kw)
    out = []
    for f in frames:
        for t in tracker.update(dets_by_frame.get(f, [])):
            out.append({"frame": f, **t})
    return out
