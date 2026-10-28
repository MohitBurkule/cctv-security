"""Scoring photorealism without a reference image set.

FID needs real CCTV frames to compare against, and those are not always
obtainable — licensing, network, or simply not having a matching site. But the
*statistics* of real CCTV are documented, and a render can be scored against
those directly.

Each target below is a plausible range for real surveillance footage, taken from
the imaging-chain analysis in the research corpus (R04) and from what the physics
implies. They are ranges, not point values, because a rainy 4CIF camera at night
and a clean 1080p camera at noon are both "real" and sit in very different places.

What this does and does not tell you:

* It **catches the giveaways** — a render with zero sensor noise, no compression
  blocking and implausibly crisp edges is obviously synthetic, and that shows up
  immediately without any reference set.
* It **cannot confirm realism**. Matching every marginal statistic is necessary,
  not sufficient; an image can have correct noise and blocking and still look
  wrong in ways only a perceptual metric or a human catches.

So a high score here means "no obvious tells", and FID against real frames
remains the stronger measure once such frames are available.

Read `out_of_range` before the composite score. Scoring decays gently outside a
range so that a near miss is not treated like a wild one, which means a render
can fail a diagnostic target and still score in the nineties. The list of failing
statistics is the actionable output; the scalar is only for ranking.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from survsim.realism.fid import ImageStats, image_stats


@dataclass(frozen=True)
class Target:
    """An acceptable range for one statistic, with why it takes that value."""

    name: str
    low: float
    high: float
    rationale: str
    weight: float = 1.0

    def score(self, value: float) -> float:
        """1.0 inside the range, decaying outside it rather than snapping to 0."""
        if self.low <= value <= self.high:
            return 1.0
        span = max(self.high - self.low, 1e-6)
        distance = (self.low - value) if value < self.low else (value - self.high)
        return float(max(0.0, 1.0 - distance / span))


# Daytime CCTV at a decent bitrate. A clean render fails `noise_sigma` and
# `blockiness` immediately, which is exactly the point.
# CALIBRATED from 12 real MOTChallenge surveillance frames via
# tools/calibrate_targets.py, replacing ranges I had reasoned out from the
# imaging chain. The measurement corrected me in a specific direction: real CCTV
# is *noisier and sharper* than I assumed, carries crushed shadows and blown
# highlights a well-exposed render lacks, and my invented ranges had pushed the
# degradation pipeline to make images softer and cleaner than reality.
#
# These frames skew modern and well-exposed, so they describe this reference set
# rather than all CCTV; a legacy 4CIF estate would sit elsewhere.
CCTV_DAY = (
    Target("noise_sigma", 2.0, 4.5,
           "measured on real frames: sensor noise survives compression", weight=2.0),
    Target("blockiness", 0.9, 1.36,
           "H.264 boundary discontinuity, measured", weight=1.5),
    Target("edge_density", 0.049, 0.118,
           "real footage keeps more edge detail than a heavy-handed blur allows",
           weight=1.5),
    Target("laplacian_var", 80.0, 982.0,
           "wide: sharpness varies hugely across real cameras"),
    Target("saturation_mean", 14.0, 108.0, "muted but not monochrome"),
    Target("luma_mean", 55.0, 162.0, "auto-exposure holds a mid grey"),
    Target("luma_std", 29.7, 68.7, "measured contrast spread"),
    Target("dark_fraction", 0.0, 0.063,
           "real frames contain crushed shadow; a clean render has none"),
    Target("clipped_fraction", 0.0, 0.043,
           "real frames contain blown highlights; a clean render has none"),
    Target("hf_energy", 0.232, 0.532,
           "now calibrated against real frames rather than guessed", weight=0.5),
)

# Night IR: monochrome, high gain, illuminator falloff.
CCTV_NIGHT_IR = (
    Target("noise_sigma", 3.0, 14.0, "high gain amplifies read noise", weight=2.0),
    Target("blockiness", 1.0, 3.0, "low-light noise costs the codec bitrate", weight=1.5),
    # Not exactly zero: the greyscale conversion happens before the codec, and
    # H.264 chroma quantisation reintroduces a little colour noise afterwards -
    # which real IR footage also shows.
    Target("saturation_mean", 0.0, 18.0,
           "IR-cut filter lifted: near-monochrome, bar codec chroma noise", weight=2.0),
    Target("luma_mean", 25.0, 110.0, "illuminator lights the near field only"),
    Target("dark_fraction", 0.10, 0.70,
           "the far field is black because IR LEDs cannot reach it", weight=1.5),
    Target("edge_density", 0.005, 0.09, "noise and softness bury fine detail"),
)

PROFILE_TARGETS: dict[str, tuple[Target, ...]] = {
    "clean": (),                       # deliberately unscored: it is the input
    "cctv_day_720p": CCTV_DAY,
    "cctv_legacy_sd": CCTV_DAY,
    "cctv_fog_day": CCTV_DAY,
    "cctv_night_ir": CCTV_NIGHT_IR,
}


def score_image(stats: ImageStats, targets: Sequence[Target]) -> dict[str, Any]:
    """Score one image's statistics against a target set."""
    values = {k: v for k, v in zip(ImageStats.keys(), stats.as_vector())}
    per_stat: dict[str, dict[str, Any]] = {}
    total = weight_sum = 0.0

    for target in targets:
        if target.name not in values:
            continue
        value = float(values[target.name])
        s = target.score(value)
        per_stat[target.name] = {
            "value": round(value, 3),
            "range": [target.low, target.high],
            "score": round(s, 3),
            "in_range": target.low <= value <= target.high,
            "why": target.rationale,
        }
        total += s * target.weight
        weight_sum += target.weight

    failures = [k for k, v in per_stat.items() if not v["in_range"]]
    return {
        "score": round(total / weight_sum, 4) if weight_sum else None,
        "per_statistic": per_stat,
        "out_of_range": failures,
        "n_targets": len(per_stat),
    }


def score_profile(images: Iterable[np.ndarray], profile: str) -> dict[str, Any]:
    """Score a set of images rendered under one degradation profile."""
    targets = PROFILE_TARGETS.get(profile)
    if not targets:
        return {"profile": profile, "score": None,
                "note": "no targets defined; 'clean' is the input, not a candidate"}

    stats = [image_stats(img) for img in images]
    if not stats:
        return {"profile": profile, "score": None, "note": "no images"}

    scored = [score_image(s, targets) for s in stats]
    mean = float(np.mean([s["score"] for s in scored]))
    # Count how often each statistic fails, so the report says what to fix.
    failure_counts: dict[str, int] = {}
    for s in scored:
        for name in s["out_of_range"]:
            failure_counts[name] = failure_counts.get(name, 0) + 1

    return {
        "profile": profile,
        "score": round(mean, 4),
        "n_images": len(stats),
        "worst_statistics": sorted(failure_counts.items(), key=lambda kv: -kv[1])[:5],
        "detail": scored[0]["per_statistic"],
        "interpretation": (
            "high score means no obvious synthetic tells; it cannot confirm realism, "
            "for which FID against real frames is the stronger measure"
        ),
    }


def compare_profiles(images_by_profile: dict[str, Sequence[np.ndarray]]) -> dict[str, Any]:
    """Score several profiles and confirm degradation moves output toward realism."""
    results = {p: score_profile(imgs, p) for p, imgs in images_by_profile.items()}
    scored = {p: r["score"] for p, r in results.items() if r.get("score") is not None}

    verdict = None
    if "clean" in images_by_profile and scored:
        # The clean render scored against CCTV targets is the baseline to beat.
        clean_as_cctv = score_profile(images_by_profile["clean"], "cctv_day_720p")
        best = max(scored.values())
        verdict = {
            "clean_scored_as_cctv": clean_as_cctv["score"],
            "best_degraded": round(best, 4),
            "degradation_helps": best > (clean_as_cctv["score"] or 0.0),
            "clean_failures": clean_as_cctv["worst_statistics"],
        }

    return {"profiles": results, "verdict": verdict}
