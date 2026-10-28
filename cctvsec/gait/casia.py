"""Measure how carrying a bag or wearing a coat changes gait — from real data.

`gait/signature.py` carries a `STYLE_EFFECTS` table describing what each walking
style does to cadence, step length, asymmetry and the rest. Those multipliers
were *argued*, not measured, and docs/11 records that honestly: no public
dataset gives per-style gait parameters for surveillance footage.

CASIA-B does, for two of the styles that matter most to us. It records 124
subjects walking under three conditions — **normal**, **carrying a bag**, and
**wearing a coat** — from 11 view angles. Because it is the *same people* in
every condition, the comparison is paired, which removes between-person
variation from the estimate entirely. That is a far stronger design than
comparing two populations, and it is exactly what our evasion taxonomy needs:
`weighted_asymmetry` (a heavy bag on one side) and the outfit-change techniques
assert gait degradations that can now be checked.

**What these silhouettes can and cannot support.** The frames are 64x64,
size-normalised and centred. That normalisation is deliberate in the dataset and
destructive for us: absolute stature, step length in metres, and body sway are
all removed by it. What survives is *temporal* and *shape* structure, so the
honest set of measurables is:

  - **cadence** — leg separation oscillates once per step, and the period is
    unaffected by spatial normalisation;
  - **relative leg spread** — stance width as a fraction of body width;
  - **silhouette asymmetry** — left/right imbalance, which is what carrying a
    weight on one side actually produces.

Anything reported in metres from this source would be invented, so nothing here
returns metres.

Layout: `output/<subject>/<cond>-<seq>/<view>/<subject>-<cond>-<seq>-<view>-<frame>.png`
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# CASIA-B was captured at 25 fps.
FPS = 25.0

# The side view. Gait is most visible perpendicular to the walking direction —
# at 000 or 180 degrees the subject walks toward or away from the camera and the
# legs barely separate horizontally, which is the same constraint that made 69%
# of MOT20 tracks unmeasurable (docs/14 §10).
SIDE_VIEW = "090"

CONDITIONS = {
    "nm": "normal",
    "bg": "carrying a bag",
    "cl": "wearing a coat",
}

# A silhouette pixel. The images are mostly binary but carry antialiasing.
THRESHOLD = 127

# Fraction of body height, measured from the feet, treated as "legs".
LEG_BAND = 0.35

MIN_FRAMES = 20


@dataclass
class SequenceGait:
    """Gait measurements for one subject under one condition, one view."""

    subject: str
    condition: str
    view: str
    cadence_spm: float
    leg_spread: float
    asymmetry: float
    n_frames: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject, "condition": self.condition,
            "view": self.view, "cadence_spm": round(self.cadence_spm, 2),
            "leg_spread": round(self.leg_spread, 4),
            "asymmetry": round(self.asymmetry, 4),
            "n_frames": self.n_frames,
        }


def _silhouette(path: Path) -> np.ndarray | None:
    import cv2
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    return None if img is None else (img > THRESHOLD)


def frame_features(mask: np.ndarray) -> tuple[float, float] | None:
    """Leg spread and left/right asymmetry for one silhouette.

    Both are expressed relative to the body, not in pixels, because the frames
    are size-normalised and a pixel has no fixed physical meaning.
    """
    rows = np.flatnonzero(mask.any(axis=1))
    if len(rows) < 8:
        return None
    top, bottom = int(rows[0]), int(rows[-1])
    height = bottom - top + 1

    body_cols = np.flatnonzero(mask.any(axis=0))
    if len(body_cols) < 2:
        return None
    body_width = float(body_cols[-1] - body_cols[0] + 1)

    # Legs: the lowest band of the body.
    leg_top = bottom - round(height * LEG_BAND)
    legs = mask[max(leg_top, top):bottom + 1, :]
    leg_cols = np.flatnonzero(legs.any(axis=0))
    if len(leg_cols) < 2:
        return None
    spread = float(leg_cols[-1] - leg_cols[0] + 1) / max(body_width, 1e-6)

    # Asymmetry: how much of the leg mass sits left versus right of the body
    # centre. Carrying a weight on one side shows up here.
    centre = (body_cols[0] + body_cols[-1]) / 2.0
    xs = np.flatnonzero(legs.any(axis=0))
    left = float((xs < centre).sum())
    right = float((xs > centre).sum())
    total = left + right
    asymmetry = (left - right) / total if total > 0 else 0.0
    return spread, asymmetry


def cadence_from_spread(spread: Sequence[float], fps: float = FPS) -> float:
    """Steps per minute, from the oscillation of leg separation.

    Leg spread peaks once per step — at each maximum the legs are furthest
    apart. Counting peaks is used rather than an FFT for the same reason as in
    `gait/cadence.py`: a short sequence has too few cycles for a resolved
    spectrum, and an FFT returns a confident peak for noise.
    """
    values = np.asarray(spread, dtype=float)
    if len(values) < MIN_FRAMES:
        return 0.0
    centred = values - values.mean()
    amplitude = float(np.abs(centred).max())
    if amplitude < 1e-6:
        return 0.0

    # Count upward zero crossings: one per full oscillation, i.e. one per step.
    crossings = 0
    for i in range(1, len(centred)):
        if centred[i - 1] <= 0 < centred[i]:
            crossings += 1
    duration_s = len(values) / fps
    return crossings / duration_s * 60.0 if duration_s > 0 else 0.0


def measure_sequence(frames_dir: Path, subject: str, condition: str,
                     view: str, fps: float = FPS) -> SequenceGait | None:
    """Measure one subject-condition-view sequence."""
    paths = sorted(Path(frames_dir).glob("*.png"))
    if len(paths) < MIN_FRAMES:
        return None

    spreads, asymmetries = [], []
    for path in paths:
        mask = _silhouette(path)
        if mask is None:
            continue
        got = frame_features(mask)
        if got is None:
            continue
        spreads.append(got[0])
        asymmetries.append(got[1])

    if len(spreads) < MIN_FRAMES:
        return None

    return SequenceGait(
        subject=subject, condition=condition, view=view,
        cadence_spm=cadence_from_spread(spreads, fps),
        leg_spread=float(np.mean(spreads)),
        # Mean over the cycle: instantaneous asymmetry swings with the stride,
        # so a single frame says nothing about a persistent imbalance.
        asymmetry=float(np.mean(asymmetries)),
        n_frames=len(spreads),
    )


def walk_dataset(root: Path, view: str = SIDE_VIEW,
                 max_subjects: int | None = None) -> list[SequenceGait]:
    """Measure every sequence in a CASIA-B tree at one view angle."""
    root = Path(root)
    base = root / "output" if (root / "output").is_dir() else root

    out: list[SequenceGait] = []
    for subject_dir in sorted(p for p in base.iterdir() if p.is_dir())[:max_subjects]:
        for seq_dir in sorted(p for p in subject_dir.iterdir() if p.is_dir()):
            condition = seq_dir.name.split("-")[0]
            if condition not in CONDITIONS:
                continue
            view_dir = seq_dir / view
            if not view_dir.is_dir():
                continue
            measured = measure_sequence(view_dir, subject_dir.name,
                                        condition, view)
            if measured is not None:
                out.append(measured)
    return out


def paired_effects(measurements: Sequence[SequenceGait],
                   ) -> dict[str, dict[str, Any]]:
    """Effect of each condition relative to that same subject walking normally.

    Paired within subject, which is the whole value of this dataset: it removes
    between-person variation, so what remains is the effect of the bag or the
    coat rather than of who happened to be wearing it.
    """
    by_subject: dict[str, dict[str, list[SequenceGait]]] = {}
    for m in measurements:
        by_subject.setdefault(m.subject, {}).setdefault(m.condition, []).append(m)

    ratios: dict[str, dict[str, list[float]]] = {}
    for conditions in by_subject.values():
        normal = conditions.get("nm")
        if not normal:
            continue
        base_cadence = float(np.mean([m.cadence_spm for m in normal]))
        base_spread = float(np.mean([m.leg_spread for m in normal]))
        base_asym = float(np.mean([m.asymmetry for m in normal]))
        if base_cadence <= 0 or base_spread <= 0:
            continue

        for condition, items in conditions.items():
            if condition == "nm":
                continue
            bucket = ratios.setdefault(condition, {"cadence": [], "spread": [],
                                                   "asymmetry_delta": []})
            bucket["cadence"].append(
                float(np.mean([m.cadence_spm for m in items])) / base_cadence)
            bucket["spread"].append(
                float(np.mean([m.leg_spread for m in items])) / base_spread)
            # Absolute delta, not a ratio: a normal walk's asymmetry is near
            # zero, and dividing by it produces noise.
            bucket["asymmetry_delta"].append(
                float(np.mean([m.asymmetry for m in items])) - base_asym)

    summary: dict[str, dict[str, Any]] = {}
    for condition, values in ratios.items():
        summary[condition] = {
            "label": CONDITIONS.get(condition, condition),
            "n_subjects": len(values["cadence"]),
            "cadence_ratio": round(float(np.mean(values["cadence"])), 4),
            "cadence_ratio_std": round(float(np.std(values["cadence"])), 4),
            "leg_spread_ratio": round(float(np.mean(values["spread"])), 4),
            "asymmetry_delta": round(float(np.mean(values["asymmetry_delta"])), 4),
            "asymmetry_delta_std": round(
                float(np.std(values["asymmetry_delta"])), 4),
        }
    return summary
