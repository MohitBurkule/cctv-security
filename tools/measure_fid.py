"""Measure FID of our degradation pipeline against real CCTV, with its floor.

This answers a question docs/14 could only approximate with summary statistics:
does our degradation chain make an image *more* like real CCTV, or merely
dirtier? Summary statistics are a handful of scalars and can be satisfied by an
image that looks nothing like CCTV.

The experiment is deliberately arranged to isolate the degradation from the
renderer. Comparing our renders to real footage would tell us only that our
renderer is not photoreal — which we already know, and which would swamp any
signal about the imaging chain. Instead we take *real* frames, degrade them with
each profile, and score against a **disjoint** set of real frames. Content is
real on both sides, so the only thing varying is our degradation.

Two reference points make the numbers readable:

  - the **floor**: real against real, which is not zero at finite sample size;
  - **undegraded**: real frames passed through unchanged, which should sit at
    the floor. If it does not, the harness itself is biased and no profile
    result from it means anything.

Everything is held in memory. An earlier version wrote each degraded frame to
PNG and read it straight back, which made the sweep disk-bound for hours.

    .venv/bin/python tools/measure_fid.py [--n 1100] [--height 720]
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

# OpenCV parallelises some operations internally. Left alone, each worker
# process would spawn its own thread pool and they would fight for the same
# cores, which is slower than doing it single-threaded.
cv2.setNumThreads(1)

from survsim.realism.fid import (
    FID_MIN_SAMPLES, frechet_distance, inception_features_from_images,
)
from survsim.sensors.degrade import PROFILES, apply_profile

MOT_ROOT = Path.home() / "data" / "mot" / "extracted"


def real_frames(limit: int) -> list[Path]:
    """Real surveillance frames, spread across sequences rather than consecutive.

    Consecutive frames from one sequence are nearly identical, which collapses
    the feature covariance and produces a floor far below what an honest sample
    of the dataset gives — flattering every profile measured against it.
    """
    paths = sorted(MOT_ROOT.rglob("img1/*.jpg"))
    if not paths or len(paths) <= limit:
        return paths
    step = len(paths) / limit
    return [paths[int(i * step)] for i in range(limit)]


def _degrade_one(args: tuple) -> np.ndarray:
    """One frame through one profile. Module-level so it can be pickled."""
    img, profile, seed = args
    return apply_profile(img, profile, seed=seed)


def load(paths: list[Path], height: int) -> list[np.ndarray]:
    """Read and downscale to the resolution our cameras actually capture at."""
    out = []
    for p in paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        if height and img.shape[0] != height:
            scale = height / img.shape[0]
            img = cv2.resize(img, (int(round(img.shape[1] * scale)), height),
                             interpolation=cv2.INTER_AREA)
        out.append(img)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1100, help="frames per side")
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--out", type=Path, default=Path("out/fid.json"))
    args = ap.parse_args()

    frames = real_frames(args.n * 2)
    if len(frames) < 8:
        print(f"no real frames under {MOT_ROOT}")
        return 1

    # Disjoint halves: the reference set is never an input to the degraded set,
    # so a profile cannot score well by having seen the same images.
    reference_paths, source_paths = frames[0::2], frames[1::2]
    print(f"loading {len(reference_paths)} reference + {len(source_paths)} source "
          f"frames at {args.height}p", flush=True)

    reference = load(reference_paths, args.height)
    source = load(source_paths, args.height)

    ref_feat = inception_features_from_images(reference)
    print(f"reference features: {ref_feat.shape}", flush=True)

    # The floor is the UNDEGRADED comparison: reference frames against a
    # disjoint set of real frames passed through unchanged.
    #
    # It must be measured at the same sample size as everything else. Splitting
    # the reference set in half to get a floor is the obvious approach and it is
    # wrong: FID falls with sample count, so a 450-v-450 floor (30.50 here) sits
    # far above the 900-v-900 comparisons it is meant to calibrate, and the
    # undegraded pass then scored 0.42x its own floor — impossible, and the only
    # reason the error was visible at all.
    reliable = min(len(ref_feat), len(source)) >= FID_MIN_SAMPLES
    results = {"n_per_side": len(source), "height": args.height,
               "reliable": reliable, "profiles": {}}
    if not reliable:
        print(f"note: {min(len(ref_feat), len(source))} frames per side is below "
              f"{FID_MIN_SAMPLES}; the Inception covariance is rank-deficient, so "
              "treat absolute values as indicative and compare ratios only\n",
              flush=True)
    floor = None

    workers = max(1, (os.cpu_count() or 2) - 1)
    print(f"degrading on {workers} workers", flush=True)

    for profile in [None, *sorted(PROFILES)]:
        name = profile or "undegraded"
        if profile is None:
            degraded = source
        else:
            # Degradation, not FID, is the bottleneck: the denoise stage alone
            # is seconds per frame, and a single-threaded sweep took over half
            # an hour without finishing one profile. The frames are independent,
            # so this parallelises exactly.
            with ProcessPoolExecutor(max_workers=workers) as pool:
                degraded = list(pool.map(
                    _degrade_one,
                    ((img, profile, i) for i, img in enumerate(source)),
                    chunksize=8))
        feat = inception_features_from_images(degraded)
        value = frechet_distance(ref_feat, feat)
        if profile is None:
            # Real vs real at the working sample size: this is the floor.
            floor = value
            results["floor"] = round(value, 3)
        ratio = value / floor if floor else None
        results["profiles"][name] = {
            "fid": round(value, 3),
            "ratio_to_floor": round(ratio, 3) if ratio else None,
        }
        suffix = f"   x floor = {ratio:6.2f}" if ratio else "   (this is the floor)"
        print(f"  {name:<20} FID={value:9.2f}{suffix}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {args.out}")

    # Interpretation, stated rather than left to the reader. The ranking is the
    # useful output: which profile lands closest to real footage.
    ranked = sorted(((v["ratio_to_floor"], k)
                     for k, v in results["profiles"].items()
                     if v["ratio_to_floor"] is not None and k != "undegraded"),
                    key=lambda t: t[0])
    if ranked:
        print(f"\nclosest to real CCTV: {ranked[0][1]} "
              f"({ranked[0][0]:.2f}x the floor)")
        results["best_profile"] = ranked[0][1]

    # A profile scoring below the floor would mean degraded frames resemble real
    # footage more closely than real footage resembles itself, which is not
    # possible and indicates the estimate is dominated by sampling noise.
    below = [k for k, v in results["profiles"].items()
             if v["ratio_to_floor"] is not None and v["ratio_to_floor"] < 0.95]
    if below:
        print(f"WARNING: {below} scored below the real-vs-real floor, which is "
              "not physically meaningful — the estimate is noise-dominated. "
              "Increase --n.")
    args.out.write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
