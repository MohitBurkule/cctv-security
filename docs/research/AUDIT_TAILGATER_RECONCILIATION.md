# AUDIT_TAILGATER_RECONCILIATION · reconciling H54's 0.685 with H59's 0.10

Audited 2026-09-27 against `docs/research/32_EXPERIMENTS_LOG.md` §H54/§H59, `AUDIT_H54.md`, `AUDIT_H59.md`,
`AUDIT_90.md`'s "H54/H59 tailgater nuance" watch item, `out/experiments/h59_idsw_fusion/results.json` and
`fused_worlds.jsonl`, `survsim/eval/alarms.py` (`AlarmScore.window_only_recall`).

## 1. Re-verified attribution: C alone vs C+abcg, calibrated arm

From `results.json` (`calibrated` block): `C` (no fusion leg at all) tailgater recall@10 = **0.108
[0.079, 0.139]**; `C+abcg` (H54's gate people counter) = **0.100 [0.071, 0.131]**. The two are the same
within CI — the collapse from H54's benign-noise 0.685 happens *before* any fusion leg runs, exactly as
AUDIT_H59 attributed it: a label swap mid-track reassigns an already-caught detection to the wrong `uid`,
and `alarms.score`'s actor-aware matching (default since round 2, docs/13 principle 4) scores that as a
miss against the true actor, regardless of which fusion arm is in play. Confirmed, not just re-quoted.

## 2. Label-agnostic (position/time) recall, computed from the same cached alarms

`alarms.score` already computes a second number every call, `AlarmScore.window_only_recall` — recall under
label + timing only, ignoring `uid` entirely. Re-scoring the 100 generated tailgate worlds' calibrated-arm
alarms (`out/experiments/h59_idsw_fusion/fused_worlds.jsonl`, both `C` and `C+abcg`, all 10 noise seeds) with
this window-only match instead of the actor-aware default:

| fusion arm | actor-aware recall@10 (registered) | window-only (label-agnostic) recall@10 |
|---|---|---|
| C | 0.108 | **0.828** |
| C+abcg | 0.100 | **0.739** |

Feasible within the 30-minute window because the run was already cached (`fused_worlds.jsonl`, 15 MB) — no
rerun of the simulator was needed, only a rescoring pass. Reading: under realistic ID-switch noise, the
*fused decision* is still correct on the large majority of tailgate worlds (0.74–0.83 recall by position and
time); the actor-aware *scorer* — doing exactly what it is designed to do, penalise an alarm credited to the
wrong identity — turns that into 0.10. The gate counter (`C+abcg`) still costs some real recall relative to
`C` alone even label-agnostic (0.739 vs 0.828, consistent with H54's own benign-arm C+abcg cost), but nothing
like the reported 0.685 → 0.10 collapse, which is almost entirely the swapped-label scoring artefact.

## 3. Reconciled sentence (added to 32 §H59, mirrored elsewhere)

> With GT identities a gate counter catches the tailgater at 0.685 (H54); under realistic ID switches the
> actor-aware *score* drops to 0.10 because the alarm is credited to the swapped label — the fusion decision
> itself is unchanged (label-agnostic recall recomputed at 0.83 alone / 0.74 with the counter); a real system
> would score by position/time.

Added as a "Reading for the interview" paragraph in `32_EXPERIMENTS_LOG.md` §H59 (end of section, before
H60), and mirrored (one sentence, same numbers, form varying to fit each doc's style) in:
`76_INTRUSION_BEHAVIOURS_BEYOND_LOITER.md`, `removed-vendor-doc.md` (the R55-canonical fusion
sentence, extended within R55's allowed form — the extension does not remove any of R55's required markers:
H53, "simulated", "tailgat"), `65_DRESS_REHEARSAL_V2.md` (5 occurrences), `74_SYSTEM_DESIGN_DRILLS.md`,
`48_MOCK_INTERVIEW_ROUND2.md`, `60_ONE_PAGE_CHEAT_SHEET.md` (item 40), `90_MOCK_INTERVIEW_ROUND8_FULL_RUN.md`
(resolving AUDIT_90's watch item), and three additional docs the new registry row (§4) surfaced that quote
the same 0.685 tailgater number unqualified: `13_BASELINES.md`, `52_SURVSIM_TECHNICAL_BRIEF.md`,
`64_TECHNICAL_REPORT_SIM2REAL_AND_ALARMS.md`, `84_COLD_READ_REVIEW_V3.md`.

## 4. Registry

Added `RETIRED_CLAIMS.md` row **R61**: flags any line stating the tailgater 0.685 recall without an
H59/ID-switch/actor-aware/label-agnostic marker on the same line. Every occurrence found across
`docs/**/*.md` and `CLAUDE.md` was fixed (13 lines across 9 files); `tests/test_docs_retired_claims.py`
passes (6/6) after the fixes.

## 5. Backlog

Added **H62** to `66_HYPOTHESIS_BACKLOG.md`: pre-registers position/time-keyed (window-only or
uid-tolerant-within-radius) alarm scoring as the default when alarm identities come from a tracker/ReID
pipeline rather than ground truth, using template `49` §12. Not run — pre-registration only, per this task's
scope (no code changes to `survsim/`).

## Numbers for reuse

* Calibrated-arm actor-aware tailgater recall@10: **C 0.108, C+abcg 0.100** (results.json, re-verified).
* Calibrated-arm label-agnostic (window-only) tailgater recall@10, computed here: **C 0.828, C+abcg 0.739**.
* H54 benign-noise (GT identities) tailgater recall@10 with the gate counter: **0.685** (unchanged, not
  retired — the number itself is correct; only unqualified reuse is now flagged).
