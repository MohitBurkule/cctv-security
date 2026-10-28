# AUDIT_101_PART3 — adversarial audit of 101 Part 3 (segments 19b, 36–50; commit b7c7eca)

Every number checked against FACTS_VERIFIED.md, 112, 113, RETIRED_CLAIMS (R65–R80) and demo/INDEX.md (read-only).
All 25 fallbacks cite the right retired id. Tile-border rule is answered "not shipped" (Q6); night numbers are on the
449-row GT (Q16, Q20); the console is called a mock-up (Q9). Fixes applied in place.

| Q | Finding | Verdict |
|---|---|---|
| preamble | "Numbers are FACTS_VERIFIED figures": seg 50 counts (1,994 / 684) and seg 37 62/80 are not in FACTS | FIX: sources named (AUDIT_GT_FENCE_VISIBILITY, INDEX) |
| Q1 | "so 13 are shown" on 19b: 19b shows 7 new types; 13 is segment 36 | FIX |
| Q2 | "13 layouts render cleanly": one gate-passing seed per type | FIX (qualified) |
| Q4 | "the ID mask now respects the scene depth test": shown on one site 09 re-render only; no existing set records it. "batch_v8 has no rows that change": its column 9 changes (849–4,067 rows/set); what holds is 0/42,581 cross 0.5 with static cover and no batch_v8 experiment filters on visibility | FIX (worst) |
| Q7 | "lowest MOT20 densities measured": −0.079 is the sparsest quartile, post hoc | FIX |
| Q11 | ten stages: map and card built for this alarm; only detection (cached) and evidence verify are real code runs | FIX (made explicit) |
| Q19 | 1,994 rows sourced | FIX (with preamble) |
| 3-min pick | reel times 12:28 / 10:13 stale after the 19b insert; README_v2 gives 26 at 13:14, 20 at 11:01; 48 and 50 are separate files, not in the reel | FIX |
| Q3, Q5, Q6, Q8–Q10, Q12–Q18, Q20–Q25 | numbers match FACTS/112/113; qualifiers present (R65, R66, R70, R74–R80) | OK |

Count: 8 FIX. Propagated: 104 chat-prep row and 107 §1 now carry the 26 / 20 / 50 (+48) pick; 110 §3 names no
segments (unchanged).
