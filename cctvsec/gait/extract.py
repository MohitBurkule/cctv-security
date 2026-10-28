"""Measure how people actually walk, from real CCTV ground truth.

`director/crowd.py` models walking speed with a fundamental diagram whose
constants — a 1.34 m/s free speed and a 5.4 people/m² jam density — came from
the pedestrian literature, not from measurement. They are plausible and widely
cited, and they were still assumptions. A simulator whose crowds move at the
wrong speed produces motion statistics that no detector trained on it will
recognise in real footage, and nothing in a self-consistent test suite would
notice.

MOTChallenge ground truth lets us check. It gives per-person boxes at 25 fps
across crowded public scenes, which is enough to recover speed and local density
without any tracking of our own.

**The scale trick.** MOT annotations are in pixels and the sequences ship no
calibration, so metres have to come from somewhere. Each person's own bounding
box supplies it: a pedestrian is about 1.7 m tall, so their box height in pixels
is a ruler at their own depth. Using it per-detection rather than once per
sequence means perspective is absorbed automatically — someone at the back of
the scene has a small box and a correspondingly small metres-per-pixel, so their
speed comes out right without a homography.

What this cannot do, stated plainly:

  - **Cadence and gait style are not recoverable here.** MOT boxes are often
    interpolated between keyframes and are smoothed, so the vertical bob that
    carries step frequency is mostly annotation artefact. Extracting cadence
    needs pose estimation on the pixels, not boxes.
  - Stature varies (σ ≈ 7 cm), so any individual's speed carries roughly 4%
    scale error. This is fine for distributions, wrong for a single person.
  - Boxes that are occluded or clipped by the frame edge have the wrong height,
    which corrupts the ruler. Both are filtered out rather than corrected.
  - MOT20 is deliberately crowded, so free-flow speed is under-represented —
    the low-density end of the curve rests on fewer samples than the high end.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# Mean adult stature. The scale ruler; everything in metres depends on it.
ASSUMED_STATURE_M = 1.70

# A box must be mostly visible for its height to be a trustworthy ruler.
MIN_VISIBILITY = 0.8

# Speeds outside this range are annotation errors, identity switches or
# somebody on a bicycle — not walking. Keeping them would fatten the
# distribution's tails and drag the mean.
MIN_WALK_MPS, MAX_WALK_MPS = 0.05, 3.5


@dataclass
class GaitStats:
    """Measured walking statistics for a set of sequences."""

    n_tracks: int
    n_samples: int
    speed_mean: float
    speed_std: float
    speed_median: float
    speed_p05: float
    speed_p95: float
    density_mean: float
    sequences: list[str] = field(default_factory=list)
    # (density bin centre, mean speed, n) — the measured fundamental diagram.
    diagram: list[tuple[float, float, int]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_tracks": self.n_tracks, "n_samples": self.n_samples,
            "speed_mean": round(self.speed_mean, 3),
            "speed_std": round(self.speed_std, 3),
            "speed_median": round(self.speed_median, 3),
            "speed_p05": round(self.speed_p05, 3),
            "speed_p95": round(self.speed_p95, 3),
            "density_mean": round(self.density_mean, 3),
            "sequences": self.sequences,
            "diagram": [(round(d, 2), round(s, 3), n) for d, s, n in self.diagram],
            "note": ("speeds scaled by per-detection box height assuming "
                     f"{ASSUMED_STATURE_M} m stature; cadence is NOT recoverable "
                     "from MOT boxes — that needs pose estimation"),
        }


def _centre_and_scale(row: dict[str, Any]) -> tuple[np.ndarray, float]:
    """Ground-contact point in pixels, and metres per pixel at that depth."""
    x, y, w, h = row["bbox"]
    # The feet, not the centroid: a box centre moves when someone crouches or
    # raises an arm, but the ground contact point tracks actual translation.
    foot = np.array([x + w / 2.0, y + h])
    return foot, ASSUMED_STATURE_M / max(h, 1e-6)


def _is_usable(row: dict[str, Any], width: int, height: int, margin: int = 8) -> bool:
    """Reject boxes whose height is not a trustworthy ruler."""
    if row.get("visibility", 1.0) < MIN_VISIBILITY:
        return False
    x, y, w, h = row["bbox"]
    if h <= 1 or w <= 1:
        return False
    # Clipped at the frame edge: the true box extends past it, so the visible
    # height understates stature and inflates the speed.
    return not (x < margin or y < margin or x + w > width - margin or y + h > height - margin)


def local_density(feet: np.ndarray, scales: np.ndarray, radius_m: float = 3.0,
                  neighbour_feet: np.ndarray | None = None) -> np.ndarray:
    """People per m² around each person, measured at their own scale.

    Counting neighbours in a fixed *pixel* radius would make the far side of the
    scene look sparse purely because it is far away. The radius is converted to
    pixels per person, so density means the same thing everywhere in frame.

    `neighbour_feet` is who gets counted, and it must be *everyone annotated* —
    not just the people whose boxes are clean enough to measure speed from.
    Getting this wrong understates density by roughly an order of magnitude on a
    crowded sequence, because a crowd is crowded precisely in that most of its
    members are occluded by each other. The first run of this code reported
    MOT20 at 0.149 people/m² (free-flowing) while simultaneously measuring
    shuffling speeds — a contradiction that only made sense once the occluded
    majority was let back into the count.
    """
    n = len(feet)
    if n == 0:
        return np.zeros(0)
    others = feet if neighbour_feet is None else neighbour_feet
    if len(others) == 0:
        return np.zeros(n)

    out = np.zeros(n)
    d = np.linalg.norm(feet[:, None, :] - others[None, :, :], axis=-1)
    for i in range(n):
        radius_px = radius_m / max(scales[i], 1e-9)
        # -1 excludes the person themselves, who is always within their own radius.
        count = max(int((d[i] <= radius_px).sum()) - 1, 0)
        out[i] = count / (np.pi * radius_m ** 2)
    return out


def measure_sequence(rows: Sequence[dict[str, Any]], fps: float,
                     width: int, height: int,
                     smooth_frames: int = 5) -> tuple[np.ndarray, np.ndarray, int]:
    """Per-sample walking speed (m/s) and local density (people/m²).

    Speed is measured over `smooth_frames` rather than between adjacent frames.
    At 25 fps a single-frame displacement is a couple of pixels, so annotation
    jitter of ±1 px is a large fraction of the signal and produces a speed
    distribution dominated by noise.
    """
    by_frame: dict[int, list[dict]] = {}
    for r in rows:
        by_frame.setdefault(r["frame"], []).append(r)

    # Density per frame, computed once for every usable person in it.
    density_lookup: dict[tuple[int, Any], float] = {}
    for frame, people in by_frame.items():
        usable = [p for p in people if _is_usable(p, width, height)]
        if not usable:
            continue
        feet = np.array([_centre_and_scale(p)[0] for p in usable])
        scales = np.array([_centre_and_scale(p)[1] for p in usable])
        # Everyone annotated counts as a neighbour, occluded or not — they are
        # physically present and are what makes the space crowded.
        all_feet = np.array([_centre_and_scale(p)[0] for p in people])
        for person, dens in zip(usable, local_density(feet, scales, neighbour_feet=all_feet)):
            density_lookup[(frame, person["id"])] = float(dens)

    tracks: dict[Any, list[dict]] = {}
    for r in rows:
        tracks.setdefault(r["id"], []).append(r)

    speeds: list[float] = []
    densities: list[float] = []
    counted_tracks = 0

    for tid, track in tracks.items():
        track = sorted(track, key=lambda r: r["frame"])
        usable = [r for r in track if _is_usable(r, width, height)]
        if len(usable) <= smooth_frames:
            continue
        counted_tracks += 1

        for i in range(len(usable) - smooth_frames):
            a, b = usable[i], usable[i + smooth_frames]
            gap = b["frame"] - a["frame"]
            # A gap larger than the window means the track was interrupted;
            # treating it as continuous motion would invent a sprint.
            if gap <= 0 or gap > smooth_frames * 2:
                continue
            foot_a, scale_a = _centre_and_scale(a)
            foot_b, scale_b = _centre_and_scale(b)
            px = float(np.linalg.norm(foot_b - foot_a))
            metres = px * (scale_a + scale_b) / 2.0
            speed = metres / (gap / fps)
            if not (MIN_WALK_MPS <= speed <= MAX_WALK_MPS):
                continue
            speeds.append(speed)
            densities.append(density_lookup.get((a["frame"], tid), 0.0))

    return np.array(speeds), np.array(densities), counted_tracks


def fundamental_diagram(speeds: np.ndarray, densities: np.ndarray,
                        bins: Sequence[float] = (0, 0.3, 0.8, 1.5, 2.5, 4.0, 10.0),
                        min_samples: int = 30) -> list[tuple[float, float, int]]:
    """Mean speed per density band — the curve `speed_for_density` models."""
    out = []
    for low, high in itertools.pairwise(bins):
        mask = (densities >= low) & (densities < high)
        n = int(mask.sum())
        if n < min_samples:
            continue
        out.append(((low + high) / 2.0, float(speeds[mask].mean()), n))
    return out


def measure(seq_dirs: Sequence[Path], smooth_frames: int = 5) -> GaitStats:
    """Measure walking statistics across MOTChallenge sequences."""
    from cctvsec.eval.motchallenge import read_sequence

    all_speeds: list[np.ndarray] = []
    all_density: list[np.ndarray] = []
    names: list[str] = []
    tracks = 0

    for seq_dir in seq_dirs:
        seq_dir = Path(seq_dir)
        info = _read_seqinfo(seq_dir)
        seq = read_sequence(seq_dir)
        s, d, n = measure_sequence(seq.gt, info["fps"], info["width"],
                                   info["height"], smooth_frames)
        if len(s):
            all_speeds.append(s)
            all_density.append(d)
            names.append(seq_dir.name)
            tracks += n

    if not all_speeds:
        return GaitStats(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    speeds = np.concatenate(all_speeds)
    densities = np.concatenate(all_density)
    return GaitStats(
        n_tracks=tracks, n_samples=len(speeds),
        speed_mean=float(speeds.mean()), speed_std=float(speeds.std()),
        speed_median=float(np.median(speeds)),
        speed_p05=float(np.percentile(speeds, 5)),
        speed_p95=float(np.percentile(speeds, 95)),
        density_mean=float(densities.mean()),
        sequences=names,
        diagram=fundamental_diagram(speeds, densities),
    )


def _read_seqinfo(seq_dir: Path) -> dict[str, Any]:
    """Frame rate and image size, which the speed and density both need."""
    info = {"fps": 25.0, "width": 1920, "height": 1080}
    path = Path(seq_dir) / "seqinfo.ini"
    if not path.is_file():
        return info
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        try:
            if key == "frameRate":
                info["fps"] = float(value)
            elif key == "imWidth":
                info["width"] = int(value)
            elif key == "imHeight":
                info["height"] = int(value)
        except ValueError:
            continue
    return info
