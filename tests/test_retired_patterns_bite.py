"""AUDIT_GUARD_RAILS: each tonight's-row pattern (R64-R80) must catch plausible
unqualified phrasings and must not flag the qualified phrasing the docs use."""

from __future__ import annotations

import functools

import pytest
from test_docs_retired_claims import is_exempt, load_registry


@functools.lru_cache(maxsize=1)
def _rows() -> dict:
    return {r["id"]: r for r in load_registry()}


def _flagged(rid: str, line: str) -> bool:
    r = _rows()[rid]
    return bool(r["pattern"].search(line)) and not is_exempt(line, r)


BAD = [
    ("R64", "H63b shows naive suppression rises to 0.249"),
    ("R64", "the live rule's drop comes from the base detector"),
    ("R65", "escalation restores recall to 0.689"),
    ("R65", "H66 decision met: escalate@16 recovers recall"),
    ("R66", "0.162 duty cycle"),
    ("R66", "the naive catch rate equals the 16% duty cycle"),
    ("R67", "recall is detector-limited across all sites"),
    ("R67", "H70 shows the scheme is detector-limited"),
    ("R68", "H69's low-recall sites are real detector failure"),
    ("R68", "low-recall sites are real detector failure on visible, usable targets"),
    ("R69", "H70b C1 met"),
    ("R69", "the CUSUM passes C1 comfortably"),
    ("R70", "renders don't rank like MOT20"),
    ("R70", "H71: renders do not rank configs the way MOT20 does"),
    ("R71", "H71: match_iou and max_lost flip"),
    ("R71", "tracker knobs flip sign between renders and MOT20"),
    ("R72", "H3b tiles are a 1.8× upscale"),
    ("R72", "tiling gives a ~1.8x upscale"),
    ("R73", "6/14 realism stats in band"),
    ("R73", "6/14 stats land in band on real street frames"),
    ("R74", "the tile-border rule costs no recall"),
    ("R74", "the border rule is safe: sparse scenes only"),
    ("R75", "noise is what erases far people"),
    ("R75", "sensor noise is the culprit for far misses"),
    ("R76", "Reading (H32 pattern)"),
    ("R76", "H3g is a second instance of the H32 overfit"),
    ("R77", "the far cameras are effectively blind at 640"),
    ("R77", "far people are blind to the detector"),
    ("R78", "shipped night recall is a pessimistic outlier"),
    ("R78", "matching noise alone buys nothing at night"),
    ("R80", "darkness, blur and denoise are innocent"),
    ("R80", "the profile injects ≈ 3× real-night noise"),
]
GOOD = [
    ("R64", "H63b's 0.249 is a caching artefact (AUDIT_H63B)"),
    ("R65", "escalation recovers 0.689 only with a bulk-ack exemption chosen after registration"),
    ("R66", "T: calling 0.162 a duty cycle (R66)"),
    ("R67", "recall is detector-limited by construction (one declared score model)"),
    ("R68", "H69's low sites are not shown to be detector failure (AUDIT_H69)"),
    ("R69", "H70b C1 met only marginally (0.0198 on a 0.02 bar)"),
    ("R70", "renders do not rank like MOT20 is inconclusive: MOT20 cannot rank itself"),
    ("R71", "H71: with MOT20-01 in, no flip is measurable (AUDIT_H71)"),
    ("R72", "704×396 tiles are 0.91× native, not a 1.8× upscale (R72)"),
    ("R73", "6/14 realism stats in band, in-sample on the swept camera"),
    ("R74", "the tile-border rule costs no recall only on sparse CC0 renders"),
    ("R75", "noise is the culprit only in interaction with blur and codec"),
    ("R76", "H3g is not a second instance of H32; coupling, not overfit (AUDIT_H3G)"),
    ("R77", "far cameras look blind at 640 on sparse CC0 renders at conf 0.25"),
    ("R78", "not a pessimistic outlier: the night profile is broken for detection (AUDIT_H32C)"),
    ("R80", "exposure, blur and denoise are minor (each ≤ 7 %, AUDIT_H32D)"),
]


@pytest.mark.parametrize("rid,line", BAD)
def test_bad_sentence_caught(rid, line):
    assert _flagged(rid, line), f"{rid} misses: {line}"


@pytest.mark.parametrize("rid,line", GOOD)
def test_good_sentence_passes(rid, line):
    assert not _flagged(rid, line), f"{rid} false-positive: {line}"
