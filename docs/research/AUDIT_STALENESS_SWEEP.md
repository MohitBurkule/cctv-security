# Staleness sweep v2 (2026-09-27, HEAD `827fb35`)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** 'No dedicated doc-consistency test exists' is no longer true — tests/test_docs_retired_claims.py and tests/test_docs_numbers_in_facts.py (AUDIT_65_V2, AUDIT_13_12).

Supersedes v1 (same day, after `94145fa`; its table is in git history). v2 covers the
facts that changed in `cfa9c2a..827fb35`: H19/H20/H22/H32/H33, docs 67–72, the Orin NX
re-sizing, H33's simulated worlds, AI City 2024 winner wording, BriefCam → Milestone
product names, and night realism vs LLVIP.

Scope: `docs/research/*.md` (excluding `71`, in progress, and 32's H34 section), `docs/1*.md`,
`CLAUDE.md`. Truth source: `FACTS_VERIFIED.md` plus the audited 32/69/AUDIT_* files.
Method as v1: a pattern script lists every hit; a value is **left** when it is already
historical, attributed to a commit, quoted as the error being corrected, or in an audit
file recording the correction; it is **fixed** when presented as current.

## Pattern → hits → fixed

| pattern (old form) | hits | fixed | where fixed / why left |
|---|---|---|---|
| "3/14 night" as current realism | 39 | 17 | fixed: 23:46/84, 30, 35, 40 (×2), 52 (×3), 59 (×3), 60 (×2), 65 (×2), 68:91, 00:208 — each now adds "vs day targets; 3/13 vis · 2/13 thermal vs LLVIP; raw renders luma 90". Left: docs/15 (source table), 69 (source), 61 (reviewer question), 67:65 / 68:405 / 52:400 (already qualified), audits |
| "3 NX" for 40 cams without compute | 7 | 2 | fixed 00:85, 00:200 → 4 NX (3 = decode ceiling). Left: 42/48/FACTS (already give 4 NX), AUDIT_43-47/67-69 |
| "18 streams" without decode qualifier | 9 | 3 | fixed R01:772, D07:851, D04:793 (bracketed note). Left: 38 (qualified), 48 (the correction), 61 (question), H01 (the trap itself), R01:1166 (already caveated), AUDIT_52-53 |
| "338 sites" | 0 | 0 | all hits say "simulated worlds" |
| SJTU / Yachiyo "winner" without "official" | 4 | 0 | FACTS, 42, R02 already say official winner 67.22 online / top-HOTA runner-up 71.94 |
| "23 identities" (H20) | 1 | 0 | only AUDIT_H19_H20 (the correction) |
| "0.228 → 0.249" (H20) | 2 | 0 | only AUDIT_H19_H20 |
| BriefCam "Review/Research/Respond" | 2 | 0 | only 72 / AUDIT_72, both as the corrected form |
| "GBM ≈ −33 %" | 0 live | 0 | only 67:107 and 00:115, both say "retired" |
| "GREW 79–86 % R1" | 7 | 4 | fixed 00:248, 40:765, FACTS:33, FACTS:111 → 77.7–79.4 R1 (86 was rank-10; 70). Left: 70 (the correction), AUDIT_01-16 |
| "LTCC 74.8" as a clothes-change score | 3 | 2 | fixed 54:211, 54:442 (protocol unstated, not CC; CC LTCC is CAL 40.1). Left: 70 (the correction) |
| stale register ranges (H1–H11/H16/H18/H20 as "all") | 16 | 6 | fixed 00:74 (H1–H34), 00:208, 00:218 (64 covers H1–H20, not H18), 52:210/215/517. Left: 64/66/AUDIT_64 (scope of that report is H1–H20 by design), 32:1111 and 61/57 (historical) |
| stale HEAD in headers | 3 | 2 | 52 (`cec3317` → `827fb35`, full re-trace hash kept), 60 (`7883c98` → `827fb35`). Left: 61 (quotes the old header as the objection) |
| stale test counts (881/859, ~860) | 9 | 4 | measured 920 collected / 896 selected at `827fb35`: docs/11:3, CLAUDE.md:21, 35:96/283. Left: 40/48/57/42 (attributed to `94145fa` or argue that counts prove nothing) |
| 00 header "~550k words" | 1 | 1 | → ~630k (`wc -w`, includes untracked 71) |
| 00 index missing 61–72 / new AUDIT files | 18 rows | 18 | word-count rows for 61–70, 72; audit rows AUDIT_61-63, 64, 65, H19_H20, H22_H33, H32, 72; header now 54 reports / 19 audit files. 71 left for its author |
| 42 time budgets excluding 67–72 | 3 headers | 3 | Day 2 ≈ 7¼ h (435 min incl. 67), Day 3 ≈ 6¾ h (405 min, new block 3d: 69 §7 + 32 §H32a/b + 72 §5) |

## docs/11 and CLAUDE.md

- docs/11: test headline → 920/896; degrade row → 7 profiles, `cctv_night_lowlight` /
  `cctv_thermal` flagged overfit (H32); new "Experiments framework" row (H1–H34, 29 configs).
- CLAUDE.md "Current state": adds the experiments framework and the two night profiles
  (overfit, renders luma 90); fast-test count updated.

## Not resolved

- docs/11 still says "14 % wider" MOT20 boxes; not in FACTS and not re-derived here.
- No dedicated doc-consistency test exists (`tests/test_docs*.py` absent); tests that read
  docs were run instead.
