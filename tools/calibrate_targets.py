"""Derive realism targets from real CCTV frames instead of assumptions.

The first version of `eval/realism_targets.py` used ranges I reasoned out from
the imaging chain. Measured against twelve real MOTChallenge surveillance frames,
those ranges turned out to be wrong in a specific and instructive direction: they
pushed the degradation pipeline to make images *softer and cleaner* than real
CCTV, so tuning to them moved the renders slightly further from reality
(distance 0.471 clean vs 0.487 after "improvement").

Real footage is noisier and has more edge detail than I assumed — it is shot at
higher bitrates than the legacy-4CIF mental model, and it contains crushed
shadows and blown highlights that a well-exposed render simply does not have.

This script measures the real frames and prints target ranges derived from their
actual distribution, so the targets become evidence rather than opinion.

    .venv/bin/python tools/calibrate_targets.py ~/data/real_cctv
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import cv2
import numpy as np

from survsim.realism.fid import ImageStats, image_stats

# Statistics worth pinning, with how much slack to allow around the observed
# spread. Percentile bounds are widened because twelve frames is a small sample
# and an over-tight range would reject legitimate variation.
SLACK = 0.35


def main(folder: str) -> int:
    paths = sorted(glob.glob(str(Path(folder) / "*.jpg"))
                   + glob.glob(str(Path(folder) / "*.png")))
    images = [cv2.imread(p) for p in paths]
    images = [im for im in images if im is not None]
    if len(images) < 3:
        print(f"need at least 3 reference frames, found {len(images)}")
        return 1

    print(f"calibrating from {len(images)} real frames\n")
    stats = [image_stats(im) for im in images]
    keys = ImageStats.keys()
    matrix = np.stack([s.as_vector() for s in stats])

    print(f"{'statistic':20s} {'min':>10s} {'p25':>10s} {'median':>10s} "
          f"{'p75':>10s} {'max':>10s}   suggested range")
    for i, key in enumerate(keys):
        col = matrix[:, i]
        lo, hi = float(np.percentile(col, 10)), float(np.percentile(col, 90))
        span = max(hi - lo, abs(float(np.median(col))) * 0.2, 1e-6)
        suggested = (max(0.0, lo - span * SLACK), hi + span * SLACK)
        print(f"{key:20s} {col.min():10.3f} {np.percentile(col,25):10.3f} "
              f"{np.median(col):10.3f} {np.percentile(col,75):10.3f} "
              f"{col.max():10.3f}   ({suggested[0]:.3f}, {suggested[1]:.3f})")

    print("\nPaste the suggested ranges into CCTV_DAY in eval/realism_targets.py.")
    print("Note these come from MOTChallenge sequences, which skew toward modern,")
    print("well-exposed cameras; a legacy 4CIF estate would sit elsewhere, so the")
    print("ranges describe *this* reference set rather than all CCTV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "~/data/real_cctv"))
