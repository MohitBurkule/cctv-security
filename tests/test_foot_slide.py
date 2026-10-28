"""Foot slide metric and heading shaping (survsim/export/foot_slide.py)."""
import itertools

from survsim.export.anim_plan import heading
from survsim.export.foot_slide import (
    clip_stance_speed_mps,
    limit_turn_rate,
    load_curves,
    plan_slide,
)

C = load_curves()


def _walker(speed_mps, rate, fps=10.0, n=80, h=175.0):
    keys = [{"frame": f, "location": [f * speed_mps * 100 / fps, 0.0, 0.0]} for f in range(n)]
    return [{"keys": keys, "yaws": [0.0] * n, "height_cm": h,
             "segments": [{"clip": "walk", "rate": rate, "start": 0, "end": n}]}]


def test_matched_rate_slides_far_less_than_mismatched():
    v = 1.83 * 175 / 160            # calibrated clip speed for a 1.75 m person at rate 1
    good = plan_slide(_walker(v, 1.0), 10.0, C)["slide_median_cms"]
    bad = plan_slide(_walker(v, 0.6), 10.0, C)["slide_median_cms"]
    assert good < 15.0 and bad > 3 * good


def test_clip_curve_is_an_in_place_walk():
    assert 1.5 < clip_stance_speed_mps(C) < 2.0


def test_turn_in_place_is_rate_limited_and_reaches_the_target():
    y = [0.0] * 5 + [180.0] * 20
    out = limit_turn_rate(y, list(range(25)), 10.0, max_dps=120.0)
    steps = [abs(b - a) for a, b in itertools.pairwise(out)]
    assert max(steps) <= 12.0 + 1e-6 and abs(out[-1] - 180.0) < 1e-6


def test_heading_turns_in_place_only_when_stationary():
    keys = [{"frame": f, "location": [0.0, 0.0, 0.0]} for f in range(10)]
    keys += [{"frame": 10 + f, "location": [0.0, -f * 12.0, 0.0]} for f in range(10)]
    segs = [{"clip": "idle", "start": 0, "end": 10}, {"clip": "walk", "start": 10, "end": 20}]
    h = heading(keys, segs, 10.0)
    assert all(abs(b - a) <= 12.0 + 1e-6 for a, b in itertools.pairwise(h[:10]))
