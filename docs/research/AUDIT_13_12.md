# AUDIT_13_12 — docs/13 (baselines) and docs/12 (engine notes) vs FACTS / RETIRED_CLAIMS

Date 2026-09-27. Scope: `docs/13_BASELINES.md`, `docs/12_UNREALCV_ENGINE_NOTES.md`.
Neither doc had number coverage in the doc tests. docs/13 had ~25 appended H one-liners.

**Score: docs/13 74 → 95 / 100; docs/12 88 → 94 / 100.**

## Retired or unqualified forms found (all fixed)

| # | doc | what it said | fix |
|---|---|---|---|
| 1 | 13 §Results | "IDF1 0.54 / HOTA 0.55" as the current ByteTrack numbers: the retired pre-fix single-α HOTA (R16 form, which the regex missed because of rounding) | now 0.559 / 0.443 (TrackEval parity), with the old figure marked retired |
| 2 | 13 §Results | H16 fine-tune "0.459 vs 0.486 AP", with no step caveat | noted as same steps for both detectors; YOLO26n dose gains marked unequal-step (R52) |
| 3 | 13 §TrackEval parity | "H17's tracking deltas", no unequal-step caveat (R53 intent) | caveat added |
| 4 | 13 §Loiter round 1/2 | "(shipped)" on round-1 2.92, "retrained, shipped" 3.75 and "Ship it", all stated as current (R19/R48 intent) | relabelled round 1 / superseded; points to 58 §8.4 operator-budget trade-off |
| 5 | 13 §Loiter round 3 | "(shipped)" on A1 (R48: the ship point is an operator-budget choice) | relabelled A1 |
| 6 | 13 H25 one-liner | "+0.0127 AP dose gain" stated without the unequal-step caveat (R51 intent; the regex misses 0.0127) | summary row says vs a 6-epoch arm (unequal steps, H26) |
| 7 | 13 H9b table | pre-parity scorer, not marked | marked pre-parity |
| 8 | 13 H32b | "12 cameras": only 9 have GT ≥ 40 px (611 boxes; FACTS, 32 §H32b) | corrected in the summary |
| 9 | 13 H34 | "catches dusk and dirt" omitted codec 3 (6/12 detected, per FACTS) | summary gives 6/12 |
| 10 | 12 §batch_v6 | "0.666 / 0.824" with no note (re-scored 0.665 / 0.823 with score-order matching, per docs/13 and FACTS) | annotated |
| 11 | 12 §batch_v6 | "docs/15 has no real night reference yet": stale since H32 (LLVIP) | dated, points to FACTS realism row (3/13 vis · 2/13 thermal) |

Not found in either doc: 3/14 night, −0.609 as a night penalty (H11 appears only in the
summary, marked as a sensor-model sensitivity), "18 streams", "A1 ships", "INT8 not faster",
h14b +0.0121 as the dose gain. HOTA 0.434 appears only on lines that say pre-parity.
The registry scan reports 0 hits on both docs, before and after.

## Structure (docs/13)

Methodology (dataset, metrics, meaning, gap protocol) stays first, followed by the
baseline Results and the evaluator and tracker engineering sections. The appended one-liners
for H20, H21/H23, H42, H22, H45, H33, H34, H40, H40b, H53, H32b (a table with no header row),
H25, H26, H38 and H39 are removed. They are replaced by a single **Experiments summary**
table at the end: H → dataset → metric → result [CI] → verdict → 32 §. There are 24 rows,
including H9b, H11, H12, H16, H17, H58 r3 and M1. The narrative sections were edited and now
point to that table, so no result is stated twice.

## Numbers

* **Summary table:** all decimals are in FACTS except five. H16's +0.042 / +0.028 /
  +0.0092 / +0.0169 come verbatim from 32 §H16. 0.4428 is TrackEval-parity HOTA (FACTS 0.443).
  Each is allowlisted with its source.
* **Derived / cited (allowlisted with derivation):** 0.0455 = 4.55 / 100.
  0.5224 ≈ 0.5060 + 0.0163. 0.4005 is from AUDIT_M1_PARITY:56. 2009.07736 is an arXiv id,
  and 0.899999 is illustrative.
* **Misses: 137 decimals in docs/13 are neither in FACTS nor derivable.** They are recorded
  engineering measurements: the profiling table, before/after tables for the HOTA and
  eval_recall fixes, the ilids example, the loiter round 1/2 tables, TrackEval before/after,
  box-aspect medians and the H24 table. They are allowlisted as **RATCHET, not verified**, so
  the test catches any *new* unsourced decimal. They are not claimed as verified. Next step:
  key-match them against their `results.json` files. A bulk value-match against `out/` was
  tried and rejected as evidence, because 3-dp values collide by chance.
* One unverifiable number was removed rather than allowlisted: MOT20-01
  "mota=0.4223 …" in the profiling paragraph (pre-parity, no source).
* **docs/12:** its headline batch numbers are in FACTS: v4 0.758 / 0.577, v7 0.652 / 0.665 /
  0.814 / 0.823, v8 0.696 / 0.879 / 0.676 / 0.857 / 0.664 / 0.819, tightness 0.876–0.932, and
  amodal 0.879–0.914. About 295 other decimals (per-camera recall, VRAM, timings, foot slide)
  are engine-log measurements, not covered by a test. v5 "excl. far 0.734" and v6
  "excl. far 0.725" have no FACTS row.

## Tests

* `tests/test_docs_numbers_in_facts.py` now scans `docs/13_BASELINES.md`. A new test
  requires exactly one "Experiments summary" and no `**… (Hn, 2026-…)**` one-liners.
* `tests/test_docs_retired_claims.py` already scanned `docs/**/*.md` (rglob), which includes
  docs/12 and docs/13. A new test pins that coverage.
* Both files pass (9 tests).

## Environment note

During this audit the root filesystem hit 100 % full (ENOSPC), and a concurrent writer left
`FACTS_VERIFIED.md` with ~40 tail rows missing in the working tree (not this audit's change;
not committed here; restore from `git show HEAD:docs/research/FACTS_VERIFIED.md` + that
writer's added H53 audit row).
