"""Read MOTChallenge data, and check our metrics against it.

Every headline number in `docs/14_FIRST_RESULTS.md` is produced by
`eval/tracking.evaluate_mot`. If MOTA, IDF1 or HOTA are subtly wrong there, the
conclusions drawn from them are wrong too, and nothing downstream would notice —
a tracking metric that is 10% off still looks like a plausible tracking metric.
Self-consistent tests cannot catch this: the inverted-pitch bug survived one.

So this module does two separable things:

  - reads MOT17/MOT20 ground truth and detection files, which are the standard
    format real surveillance benchmarks ship in; and
  - scores *known* perturbations of that ground truth, where the correct answer
    is derivable by hand rather than asserted by the same code being tested.

The second is the point. If we delete exactly 10% of the boxes, MOTA must fall
by exactly 0.10 and every miss must be counted; if we swap two identities once,
MOTA must barely move while IDF1 falls sharply. Those relationships come from
the metric definitions, not from our implementation, so disagreeing with them
means our implementation is wrong.

MOTChallenge ground-truth rows are:

    frame, id, bb_left, bb_top, bb_width, bb_height, conf, class, visibility

with 1-based frames, and `conf` acting as a *flag* in ground truth: 0 marks a
box the benchmark excludes from scoring. Honouring that flag matters — counting
the ignored boxes as misses silently depresses recall on every sequence.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# MOTChallenge class ids. Only pedestrians are scored; the rest are distractors
# the benchmark explicitly excludes, and treating them as people would generate
# false positives that are not the tracker's fault.
PEDESTRIAN = 1
SCORED_CLASSES = frozenset({PEDESTRIAN})


@dataclass(frozen=True)
class Sequence_:
    """One MOTChallenge sequence."""

    name: str
    root: Path
    gt: list[dict[str, Any]]
    frame_count: int
    image_dir: Path | None = None

    @property
    def image_paths(self) -> list[Path]:
        if self.image_dir is None or not self.image_dir.is_dir():
            return []
        return sorted(self.image_dir.glob("*.jpg")) or sorted(self.image_dir.glob("*.png"))


def parse_mot_rows(
    lines: Iterable[str],
    *,
    is_ground_truth: bool,
    min_visibility: float = 0.0,
) -> list[dict[str, Any]]:
    """Parse MOTChallenge CSV lines into our row dicts.

    Converts to the convention used everywhere else in the codebase: 0-based
    frame indices and `bbox` as (x, y, w, h). The 1-based frame numbering is a
    real trap — an off-by-one here shifts every prediction one frame from its
    ground truth and quietly halves the score.
    """
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        frame = int(float(parts[0]))
        uid = int(float(parts[1]))
        x, y, w, h = (float(v) for v in parts[2:6])
        conf = float(parts[6]) if len(parts) > 6 else 1.0

        if is_ground_truth:
            cls = int(float(parts[7])) if len(parts) > 7 else PEDESTRIAN
            visibility = float(parts[8]) if len(parts) > 8 else 1.0
            # conf==0 flags a box the benchmark excludes from scoring entirely.
            if conf == 0 or cls not in SCORED_CLASSES:
                continue
            if visibility < min_visibility:
                continue
        else:
            visibility = 1.0
            cls = PEDESTRIAN

        rows.append({
            "frame": frame - 1,          # MOT is 1-based; we are 0-based
            "id": uid,
            "bbox": (x, y, w, h),
            "score": conf,
            "visibility": visibility,
        })
    return rows


def read_sequence(seq_dir: Path, *, min_visibility: float = 0.0) -> Sequence_:
    """Read one sequence directory (`MOT17-02-SDP/` and the like)."""
    seq_dir = Path(seq_dir)
    gt_file = seq_dir / "gt" / "gt.txt"
    if not gt_file.is_file():
        raise FileNotFoundError(f"no ground truth at {gt_file}")

    gt = parse_mot_rows(gt_file.read_text().splitlines(),
                        is_ground_truth=True, min_visibility=min_visibility)
    img_dir = seq_dir / "img1"
    frames = max((r["frame"] for r in gt), default=-1) + 1
    return Sequence_(name=seq_dir.name, root=seq_dir, gt=gt,
                     frame_count=frames, image_dir=img_dir if img_dir.is_dir() else None)


def find_sequences(root: Path, split: str = "train") -> list[Path]:
    """Locate sequence directories under an extracted MOT download."""
    root = Path(root)
    candidates = sorted({p.parent.parent for p in root.rglob("gt/gt.txt")})
    if split:
        candidates = [c for c in candidates if split in str(c)] or candidates
    return candidates


# --------------------------------------------------------------- perturbations
#
# Each perturbation has a hand-derivable effect on the metrics, which is what
# makes it a test rather than a demonstration.


def drop_fraction(rows: Sequence[dict[str, Any]], fraction: float,
                  seed: int = 0) -> list[dict[str, Any]]:
    """Delete a fraction of detections at random — pure misses, no new errors."""
    rng = np.random.default_rng(seed)
    keep = rng.random(len(rows)) >= fraction
    return [dict(r) for r, k in zip(rows, keep) if k]


def add_false_positives(rows: Sequence[dict[str, Any]], count: int,
                        seed: int = 0, frame_count: int | None = None,
                        ) -> list[dict[str, Any]]:
    """Add boxes far from any real one, so they cannot accidentally match."""
    rng = np.random.default_rng(seed)
    out = [dict(r) for r in rows]
    frames = sorted({r["frame"] for r in rows}) or [0]
    for i in range(count):
        frame = int(frames[rng.integers(len(frames))]) if frame_count is None \
            else int(rng.integers(frame_count))
        # Placed well outside any plausible image region.
        out.append({"frame": frame, "id": 10_000_000 + i,
                    "bbox": (50_000.0 + 100 * i, 50_000.0, 20.0, 40.0),
                    "score": 0.9, "visibility": 1.0})
    return out


def swap_identities(rows: Sequence[dict[str, Any]], uid_a: Any, uid_b: Any,
                    at_frame: int) -> list[dict[str, Any]]:
    """Exchange two identities from a frame onward — the classic ID switch.

    Leaves every box exactly where it was, so detection quality is untouched and
    only the association half of the metrics may move.
    """
    out = []
    for r in rows:
        r = dict(r)
        if r["frame"] >= at_frame:
            if r["id"] == uid_a:
                r["id"] = uid_b
            elif r["id"] == uid_b:
                r["id"] = uid_a
        out.append(r)
    return out


def jitter_boxes(rows: Sequence[dict[str, Any]], pixels: float,
                 seed: int = 0) -> list[dict[str, Any]]:
    """Shift every box by a fixed magnitude — degrades MOTP, not MOTA."""
    rng = np.random.default_rng(seed)
    out = []
    for r in rows:
        x, y, w, h = r["bbox"]
        angle = rng.uniform(0, 2 * np.pi)
        out.append({**r, "bbox": (x + pixels * np.cos(angle),
                                  y + pixels * np.sin(angle), w, h)})
    return out
