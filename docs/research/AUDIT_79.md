# AUDIT_79 · Mock interview round 5 (`79`, `f0fc845`) and the FACTS fixes it found

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** H24 has since reported (not met by 0.0006, AUDIT_H24); the FACTS count is 324 (AUDIT_NARRATIVE_POST_H26).

**Score: 7 → 9 / 10.** Numbers were clean; the losses were status, one missing
weak answer and five overclaims an the vendor ML lead would push on.

## 1. FACTS inconsistencies raised by 79
| Issue | Fix |
|---|---|
| Header 282 rows, footer 279 | Recounted by script (data rows in the 17 `\| Fact \|` tables): **318** at commit time (315 when counted; H42 and H24 rows landed concurrently). Both lines now say 318 |
| Realism row stated "3/14 `cctv_night_ir`" as current; only a bare "was" in the old test exemption saved it | Row now states the current value explicitly (3/13 vis · 2/13 thermal vs LLVIP) and calls 3/14 retired (R02). R02's pattern widened from `3/14 night` to `3/14[^\n]{0,25}night`, which the old row would have hit |
| H11 row: −0.609 with no pointer to H32b | Row now says "sensor-model sensitivity only, not a night-penalty estimate: see H32b" |
| −0.609 not in the registry | **R47** added (a negative lookahead: −0.609 / "cost(s) 0.609" on a line without sensor.model / not a night-penalty / not one / simulation-only / H32) |
| H22 twin-floor 0.2 % bulk-acked quoted by 79 Q22 but absent from FACTS | Added to the H22 row (source AUDIT_H22_H33) |

**Test.** `\bwas\b` removed from `MARKER`; a line saying "was" is now exempt only if
it carries the correct value. Two stale fixtures (bare-"was" 3/14, unqualified
−0.609) and two OK fixtures added. **New hits the tightening exposed (17):**
R47 ×12 (13, 48, 64 ×3, 66, 69 ×3, 79) — of which 13's and 48's were false
positives removed by requiring a minus or "cost"; R20 ×3 (15, 35, 52), R16 (46),
R19 (46), R07 (79), R11 (FACTS). All fixed in place by adding the correct value or
an explicit marker. 5/5 tests pass.

## 2. Audit of 79
**Numbers → FACTS.** Every decimal, ratio and percentage grep-checked. Missing:
0.2 % (added), 0.02 % (72's [INF], labelled as such, fine), 74.8 (red-flag only, R08).

**Traps vs RETIRED_CLAIMS.** Q7 = R46 ✔ · Q8 = R46 ✔ · Q9 (18 streams = decode
ceiling, 4 NX; R31) ✔ · Q23 = R16/R41–R43 ✔ · Q25 = R02 + new R47 ✔.

**Weak answers vs 77 §4.** 79's six covered 77 #1 (via Q13), #3 (Q6–Q9), #4, #5-drift,
but not #5-night; Q25 added as #7, and a cross-check paragraph maps all five (77 #2,
render ROI, is not drilled in round 5 — pointed to 68).

**H24 / H37 status.** H24 is running now: "not run" / "pre-registration only" changed to
"run in progress, no result" (intro, Q24, critique #2). H37 "pre-registered, not run" is correct.

**Overclaims fixed (ML-lead lens).**
1. Q1 "Detection dominates ingest compute" → estimate from 72/43, not profiled.
2. Q5 "embedding ranks harm well" → ρ CI above zero on n = 12.
3. Q14 D's −20.7 % stated without P8 (≥ 25 %) failing → now stated.
4. Q17 "false product decision" → "unsupported".
5. Q21 "load set what the operator caught" → scoped to the simulated queue.
6. Q25 "what holds: thermal Δ" → "on our sensor model only".
