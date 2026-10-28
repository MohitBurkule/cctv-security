# Audit of 58 and 32 §H10 v2, H12–H16 (2026-09-27, HEAD `90b6310`)

Method as `AUDIT_52-53.md`: every number traced to a committed results JSON
under `out/experiments/` and, where the JSON holds the raw arrays, recomputed
in the venv (scipy): Garwood exact Poisson CIs from counts and camera-hours;
exact permutation p over C(10,5) = 252 splits; sign-flip p over 2^5; percentile
bootstrap (20,000) of differences and of the difference of differences;
Spearman ρ with 20,000-permutation p and pair bootstrap; paired per-sequence
bootstrap for H16 zero-shot. World-bootstrap recall CIs were not re-drawn
(per-world hits are not in the JSON); they were checked for consistency with
tp/360. Tolerance: ±1 in the last quoted digit (bootstrap: MC noise).
Pre-registrations were compared with configs, `tools/loiter_eval.py` and the
git timeline.

## Scores

| Doc | Checkable claims | Correct before | After fixes |
|---|---|---|---|
| 58 (rounds 1 + 2) | ~95 | 87 (≈ 9.2/10) | all (58 fixed in place) |
| 32 §H10 v2, H12–H16 | ~150 | 145 (≈ 9.7/10) | 5 left for the coordinator (below; 32 not edited) |

Every headline rate, CI, p and ratio recomputes. The errors are in
bookkeeping prose (grid sizes, a vacuous reproduction check, pair counts),
two over-reaching verdict sentences, and one erratum in frozen pre-reg text.

## Claim table

| # | Claim (doc) | Recomputed from | Verdict |
|---|---|---|---|
| 1 | H12: 676 worlds, 3,002.0 cam-h, 338 site-h, 0 truth events, 0 invalid | `h12…/results.json` `clean` | ✓ |
| 2 | H12 FA table: 8 rows of counts, rates, Garwood, cluster-bootstrap, /site-h, ×budget (lower) | Garwood recomputed from counts ÷ 3,002 | ✓ all 8 rows exact |
| 3 | H12 recall table (tp/360, CIs, precision, FA/cam-h, latency) | `recall[]` | ✓ |
| 4 | H12 transit 54 % / 31 % of path_loiter raw alarms; dwell ≥ 90 % commute+queue; ilids lowers FAs 7–59 %; 3.6–4.9 orders; lower bounds 4,100–87,000×; per-site-h 8.9×; cluster CI ~3× Garwood; wall 99 min, 54 CPU-ks | same | ✓ (53.9 %, 31.0 %, 90.8 %, 7.4–59.0 %, log10 3.66–4.94, 4,143, 8.88, 2.95×) |
| 5 | "3,000 camera-hours" claims | JSON 3,002.0 | ✓ everywhere in 58 (3,002 / 3,002.0); 32 l.986 rounds to 3,000 (cosmetic) |
| 6 | H12 "74,989 innocent people (transit 41,150; …)" | `clean.people` 74,989; archetype counts sum to **75,071** | ⚠ JSON-internal inconsistency (82 people); the doc copies both faithfully. Worth a note in 32 |
| 7 | H13 ρ(mean\|z\|, AP) = −0.60 [−0.78, −0.20], perm p = 0.005, n = 20; in-band ρ = +0.10 [−0.40, 0.51], p = 0.67 | 20 sources | ✓ (ρ −0.5985, p 0.0054; boot [−0.77, −0.19] = MC noise) |
| 8 | H13 table (20 rows), median train 63 s, wall 80 min | sources | ✓ |
| 9 | H13 "degraded … closer *and* better in 7 of the 8 same-scene raw/degraded pairs" | same (batch, run) pairs | ✗ **6 pairs, 5 of them closer and better** (v5 disguise_night degraded is better but *farther*, 7.96 vs 6.64) |
| 10 | H13 "every arm below zero-shot (0.276) except four street_crowd sources" | AP column | ⚠ three exceed 0.276 (0.312, 0.305, 0.288); the fourth (v7 street_crowd_day raw 0.2757) ties it |
| 11 | H14 arm means/sd, both primaries (+0.0107 [0.0096, 0.0118]; +0.0089 [0.0066, 0.0111]), perm p 0.0079 = 2/252, Holm reject | arm arrays | ✓ exact |
| 12 | H14 secondaries (sign-flip 0.44 / 0.0625; unpaired 0.0079) and "all 5 paired tight−loose (300) positive" | diffs | ✓ |
| 13 | H14 label-bug caveat vs h14b status | h14b complete (15 arms, 02:32) | ✓ consistent: bug section points to h14b; h14b fixed mix_100/300 = +0.0121/+0.0095, fix moved arms +0.0014 (5/5 seeds +) and +0.0006 (mixed) — recomputed. ⚠ §H14 *Conclusion* itself has no pointer; a reader quoting "+0.011/+0.009" from H14 misses it |
| 14 | H16 pre-reg (arms, seeds 0–4, Holm over two, mix_0 copied from H14, 8 recall runs every 10th frame, 600 MOT20 frames) vs configs | configs in JSON | ✓ no undeclared deviation |
| 15 | H16 zero-shot table (16 numbers), yolov8n@640 = 0.281, paired recall diff +0.025 [+0.009, +0.042] / +0.028 [+0.006, +0.053] | `models`, per-sequence recall (24) | ✓ (recomputed [0.0087, 0.0418] / [0.0064, 0.0533]) |
| 16 | H16 "equal at 1280 (−0.003 AP, +0.005 AP50)" | 0.7084 − 0.7025 | ✗ **+0.006** AP50 (0.0059) |
| 17 | H16 dose table, gains, CIs, p; diff-of-gains −0.0030 [−0.0049, −0.0010], +0.0074 [+0.0049, +0.0097]; AP75 0.467 vs 0.512; −0.028 fine-tuned | arm arrays | ✓ (−0.0275 rounds to −0.028) |
| 18 | H10 v2 table and distractor ranking | `cues` | ✓ (gait same-epoch mAP 0.9999 printed 1.000) |
| 19 | 58 R1 pre-reg: "0.0455 FA/cam-h … 60 FA/1,000 cam-h" | 0.0455 × 1,000 | ✗ **45.5 FA/1,000 cam-h** (threshold itself right; erratum added, frozen text kept) |
| 20 | 58 R1 pre-reg timing: `0c0976f` 21:51 before `e750ba8` 22:06 and results `070cf97` 23:30; H12 finished 21:36 | git log | ✓ |
| 21 | 58 R1 pre-reg arms vs run (C1 zone tags + allowed-roles, C2, C3, C4 IRLS, 3 feature sets, forbidden features, train seeds 58/59, selection rule, H12 scored once) | `tools/loiter_eval.py`, `rules.py` | ✓ no undeclared deviation |
| 22 | 58 §2 "0 of 976 differ from H12" | `gen.log` + recount | ✓ |
| 23 | 58 §2 grid: "192 C2, 36 C3, 12 C1 (+3 baselines), 81 C4, 27 C4∧C2, 25 C2∧C3" | `selection.json` grid (294 rows) + code | ✗ **144 C2, 6 C1, 0 C2∧C3**, no baselines in the train grid (C3 best 0.797 < 0.85, so the C2∧C3 loop had no input). Fixed |
| 24 | 58 §2 3.29 M rows, 10,250 positives, wall 10 min, shipped train 3.00 / 0.883 | `fit.log` | ✓ |
| 25 | 58 §3 table (all 11 rows: FA, Garwood, ×budget, recall/precision CIs, @10, ilids, causes) | `results.json` | ✓ every cell |
| 26 | 58 §3 1.56× / 2.06×, cluster 2.76–3.06, precision 0.331 / 0.583 | same | ✓ |
| 27 | "no-entrance model beat the all-feature model on train" | grid | ⚠ true but by 3.001 vs 3.008 — a tie. Qualified |
| 28 | 58 §4 33,904 episodes, rates 3.81/2.50/2.49/2.50, 3,027 gate smoke breaks = 1.008 [0.973, 1.045], 9,706 + 6,776, 3,570 alarms, 5.1k of 8.8k, transit 19,240 → 0 / 20, weights on stat/moving/gate | `twins`, archetypes, weights | ✓ |
| 29 | 58 §4 "pacing-only rule … falls under 0.80 recall on train (C3, and C2 with a stationary ceiling)" | grid | ✗ C3 peaks 0.797 ✓, but C2 with stat ceiling ≤ 0.5 reaches **0.828** (above 0.80, below the 0.85 constraint). Fixed |
| 30 | 58 §5 ~2,900× (lower 2,854×), ~870× at floor, 0.47 vs 0.13 | arithmetic | ✓ (874×) but window-only; superseded note added pointing to §6.2 |
| 31 | 58 R2 pre-reg `24eec9c` 00:37 after the fix `473ace3` 00:14 and before results `44e34f5` 01:46; spec (C2 frozen, C4 refit same grid, round-1 features, frozen diagnostic, oracle, twin floor, both scorings) | git log, `cmd_round2` | ✓ no undeclared deviation |
| 32 | **"0/676 clean worlds changed"** | round-1 vs round-2 `tracks/h12/clean_*.json` dwell_25, sorted, allclose | ✓ **0/676** (and 0/676 vs H12 `worlds.jsonl`); clean FA counts identical (8,751; 26,849) |
| 33 | "230/300 recall worlds differ" | same | ✓ |
| 34 | "0/450 train … differ from round 1" | same, train split | ✗ **0/150 train clean, 237/300 train recall differ**. The `gen` mismatch check only has an H12 reference, so its "0 mismatches" on train compared nothing. Fixed |
| 35 | 58 §6.2 table (6 rows × both scorings) and refit θ 0.9 / clock 10 / train 3.95, 0.858 | `round2_results.json` | ✓ every cell; Garwood recomputed from 11,243 / 8,751 / 26,849 |
| 36 | P1–P4 statements: 0.853 → 0.831 (−0.02); 0.733 → 0.367; 1.60×; 2.3× recall at 0.62× FA, 4× precision; twin 1.008 | same | ✓ (2.26, 0.623, 4.08) |
| 37 | "The retrain transferred worse (3.95 train → 3.75 H12)" … "the drop is train-split variance in θ selection" | same | ✗ it did not transfer worse (H12 < train in both rounds); the refit is worse *on train*; the cause is untested and the train recall worlds also changed (237/300). Rewritten as untested |
| 38 | Verdict "only rule whose recall survives actor-aware scoring" | same | ✗ the frozen round-1 C4 also survives (0.825) at lower FA (2.915). Rewritten: pre-registered candidate; learned family is the only surviving one; frozen weights flagged for a next round, not swapped post hoc |
| 39 | ~82× target, ~3,700× budget | 3.745/0.0455, 3.745/0.001 | ✓ (82.3, 3,745) |
| 40 | "twin floor ~830× at recall 0.83" | 1.008 × 0.831 / 0.001 | ✗ **~840×** (838). Fixed |
| 41 | Operator load "≈ 1.25 operators at 40 cams × 30 s/check" (42 l.83, 57 B15, 48 l.576; not in 58/32) | 3.745 × 40 × 30 / 3600 | ✓ 1.248 |

## Corrections made to 58 (this commit)

1. §1 pre-reg: erratum "[sic: 45.5 FA/1,000 cam-h]" after "60 FA/1,000 cam-h"; frozen text otherwise kept.
2. §2 grid sizes: 144 C2 / 6 C1 / 0 C2∧C3, total 294 (bracketed correction after the original line).
3. §3 entrance ablation qualified as a tie (3.001 vs 3.008).
4. §4 "under 0.80" → misses the 0.85 constraint (C3 0.797, stat-ceiling C2 0.828).
5. §5 superseded-by-§6 note (window-only recall; actor-aware 10 s recall 0.097 / 0.000).
6. §6.2 regeneration: "0/450 train" → 0/150 train clean, 237/300 train recall; vacuous check explained.
7. §6.2 P3: transfer wording and the untested θ-variance explanation.
8. §6.2 verdict: "only rule" claim; frozen round-1 weights noted.
9. §6.2 verdict: twin floor ~830× → ~840× (0.838).

## 32 discrepancies for the coordinator (32 not edited — owned by X5)

| file:line | old | new |
|---|---|---|
| docs/research/32_EXPERIMENTS_LOG.md:1052 | "closer *and* better in 7 of the 8 same-scene raw/degraded pairs present" | "closer *and* better in 5 of the 6 same-(batch, run) raw/degraded pairs present (v5 disguise_and_tamper_night degraded is better but farther, 7.96 vs 6.64)" |
| docs/research/32_EXPERIMENTS_LOG.md:1061 | "(0.276 on MOT20-02) except four street_crowd sources" | "(0.276 on MOT20-02) except three street_crowd sources (0.312, 0.305, 0.288; v7 street_crowd_day raw ties at 0.2757)" |
| docs/research/32_EXPERIMENTS_LOG.md:1203 | "equal at 1280 (−0.003 AP, +0.005 AP50)" | "equal at 1280 (−0.003 AP, +0.006 AP50)" |
| docs/research/32_EXPERIMENTS_LOG.md:1092 (H14 Conclusion) | "…matching H7's +0.010–0.011." (no bug pointer) | append: "(mix arms used stretched disguise labels — see the label-geometry section; fixed re-run h14b: +0.0121 / +0.0095, §H16)" |
| docs/research/32_EXPERIMENTS_LOG.md:948 | "74,989 innocent people (transit 41,150; …)" | keep, add "(archetype counts sum to 75,071 in the JSON; 82-person internal mismatch in `h12_alarm_scale/results.json`, not investigated)" |
| docs/research/32_EXPERIMENTS_LOG.md:986 (cosmetic) | "With 3,000 camera-hours" | "With 3,002 camera-hours" |

No discrepancy found in 32 §H10 v2, §H12 tables, §H14 tables, §H16 pre-reg or
dose tables; no undeclared pre-registration deviation in H12–H16 or 58.

## Not re-derived
World-bootstrap recall/precision CIs in 58 and H12 (per-world hit lists not
stored in the JSON; point values = tp/360 verified). H13 image-statistics z
values (taken from the JSON, not recomputed from frames).
