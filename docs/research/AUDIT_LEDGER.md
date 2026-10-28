# AUDIT_LEDGER · Every correction made on 2026-09-27, in one table

**What changed after the 10:20 ledger (v1, 125 rows), for a reader who saw that version.**
Sixteen more audits landed through 18:54: H47 (evasion, now has a clip-cluster CI), 83/H56 (PTZ
slew), 82 (a meta-audit of this ledger itself), H51/H52 (equal-step dose and label-ablation,
both now *done*, not open), H54/H59 + a dedicated reconciliation (tailgate fusion vs identity
switches — H54's 0.685 recall and H59's 0.10 are the same fused decision scored two different
ways, not a contradiction), 84/85 (defence-context sourcing), 86/H60/87/88 (evidence-pack schema,
alarm-card leak/chain, security drills, coding-drill reference bugs), H43 (PTQ-calibration leg
done, QAT deferred to H43b), H33b (the CRC bound B=123.5 is not a valid a-priori bound), and 90
(a mislabelled θ operating point in the interview script itself). 43 new rows (15 headline / 20
supporting / 8 cosmetic) land below under four new themes plus the existing eight; the table
totalled 168 rows at that pass. R56–R61 were already added to `RETIRED_CLAIMS.md` ahead of this
file catching up.

**What changed after the 18:54 pass (168 rows), through the evening close.** Six more audits:
AUDIT_02_03 (docs/02–03 resynced against `survsim/director/behaviours.py`, §15), AUDIT_H43BC
(H43b QAT and H43c learned-range export both done, not met — one canonical edge sentence now
placed identically in five docs, §11 Q3–Q4), AUDIT_H46 (the w=4 appearance-weight argmax does not
survive a Holm correction across its own 5-arm sweep — a garden-of-forking-paths finding deferred
to H46b, §3 T24–T25), AUDIT_H46B (H46b's independent cross-validation of w is genuinely held-out,
no peeking — this is what actually clears the bar H46 could not certify; `fig_h46b.png`
generated, the tracker recommendation written as one explicit sentence, §3 T26–T27), and AUDIT_91
(two exposition errors — doubled sign-flip floors, a CRC θ point mix-up — and two glossary
mislabels in the round-9 statistics interview doc itself, §16). H59's tailgater reconciliation
(FU4–FU7, §9) and H47's frame-vs-clip bootstrap were already in the 18:54 pass; H47's
`bootstrap_delta` is now also fixed in code to resample clips by default (`492d377`). 10 new rows
(2 headline / 7 supporting / 1 cosmetic) land in §11, §3 and new §16; the table now totals 178
rows.

**For the interview reader ("show me your process").** On 2026-09-27 I audited my own corpus 27 times.
Each audit recomputed a result from its `results.json` or re-fetched a primary source, then fixed
the text in place. This file lists every correction as one row: what I had claimed, what is
actually true, the evidence, where the fix went, the regex row in `RETIRED_CLAIMS.md` that now
stops the old form from coming back, and how much it matters. Almost all the numbers survived
recomputation. What did not survive was the prose around them: comparisons at unequal optimiser
steps, confidence intervals from n = 3, "robust" and "proved" on results that were not
significant, and a ship decision that was really a staffing choice. The honest headline is the
table and the list of open items at the end, not a score.

Built from the 27 AUDIT files written today (listed in §14) and `git log --since="2026-09-27 04:00"`
(101 commits). Severity: **headline** means it changes a number or verdict I would say out loud.
**supporting** means it changes a figure, caveat or method line behind a headline. **cosmetic**
means wording, units or rounding. The "fixed in" column names the docs by number (32 = experiments
log, 58 = loiter, 64 = report, 60 = cheat sheet, 48 = numbers box, 65 = rehearsal, 66 = backlog,
FACTS = `FACTS_VERIFIED.md`).

## 1. Dose gain and optimiser steps (sim-to-real detection)

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| D1 | h14b dose gain +0.0121 [0.0111, 0.0130] AP is the synthetic-data effect | +0.004–0.005 AP at equal steps (+0.0041 at 100, +0.0045 at 300 frames), neither Holm-significant. The +0.0121 compared arms trained for unequal numbers of steps | H26 `h26_dose_fixedstep/results.json`; `dbd21c4`, AUDIT_H26 `7d481e0` | 19 docs incl. FACTS, 00, 23, 42, 52, 60, 64, 65, 68, 74, 78, 79, 80 | R51 | headline |
| D2 | "about 60 % of the h14b gain was more steps" | the decomposition is not clean. A third to a half of h14b's gain survives at equal steps (34 % / 47 %) | AUDIT_H26 §1 | 32 §H26 | — | headline |
| D3 | h14b gain "came mostly from" / "came from" extra steps; H26 "proved" it | it compared unequal steps; a third to a half survives. H26 is n.s. and H51 is still open. The pitch line is now "the experiment that made me retract my own earlier number" | AUDIT_NARRATIVE_POST_H26 #19–20, `50c76a7` | 42, 52, 68 Q18, 79 Q26 | — | headline |
| D4 | "reliably buys" list included H37 (forensic) and H47 (evasion) | nothing measured for either → listed under "not yet measured, no number" | AUDIT_NARRATIVE_POST_H26 #16 | 52, 60 #11, 64 §4, 79 Q26 | R54 | headline |
| D5 | H16 YOLO26n +0.0092 / +0.0169 quoted as current gains | uses the same unequal-step arms as h14b | AUDIT_NARRATIVE_POST_H26 §2 | 32 §H16, 52, 64, 65, 23, 48, 60, 73, 13 | R52 | supporting |
| D6 | H17 HOTA +0.0103 quoted as the tracking gain from synthetic data | unequal-step (and pre-parity scorer, T3) | AUDIT_NARRATIVE_POST_H26 §2; AUDIT_M1_PARITY #3 | 32 §H17, FACTS, 64, 68, 79, 78, 73, 13 | R53 | supporting |
| D7 | H26 real-only 0.4911 is "+0.0054 above h14b's 0.4857" | 0.4857 is h14b **seed 0**. The seed-paired step effect is +0.0049 [+0.0031, +0.0068] | AUDIT_H26 §1 | 32 | — | supporting |
| D8 | 1,000-frame arm images "seen 1–2×" | 800 images seen 2×, 500 padded duplicates seen 4× | AUDIT_H26 §1 | 32 | — | supporting |
| D9 | "each real frame seen ~2× instead of ~12×" | per list image ~2.8× vs 12×; per unique MOT20-01 frame ~14× vs 60× | AUDIT_H26 | 32 | — | cosmetic |
| D10 | H26 "450 steps" in every arm | realised iterations 456 / 452 / 450 (ultralytics rounds up the last partial batch) | AUDIT_H26 | 32 | — | cosmetic |
| D11 | the step confound "overstates" H7, H14b, H15, H25 | H15's and H25's primaries are within-dose, equal-list contrasts, so they are unaffected. H16 had been omitted | AUDIT_H26 | 32 | — | supporting |
| D12 | H25 "explains H15's null" | "consistent with" it: H15 ran at dose 300, H25 at dose 100 | AUDIT_H25, `1c56b28` | 32, 64, 48, 52, 60, 65 | R36 | supporting |
| D13 | H25: 447 noisy boxes = 3.9 %; "real labels dominate the loss" | seed 0 only and per step. Seeds 1–2 give 4.2 % / 4.0 %; unique-box share 16.9 % | AUDIT_H25 | 32 | — | cosmetic |
| D14 | H25 "+0.0127 AP dose gain" (docs/13) | measured against a 6-epoch arm, so unequal steps (H26) | AUDIT_13_12 #6 | docs/13 | (R51 intent) | supporting |
| D15 | H19 "the fixes change nothing" | nothing measurable: +0.0044 at native resolution, 3/3 seeds positive | AUDIT_H19_H20 | 32 | — | cosmetic |
| D16 | H19 "372 s/seed" | 252–372 s (mean 304). The 372 was seed 0 only | AUDIT_H19_H20 | 32 | — | cosmetic |
| D17 | H20 "23 distinct identities" | its own parts sum to 28; the true count cannot be recovered | AUDIT_H19_H20 | 32, 65 | R04 | supporting |
| D18 | H20 ReID "barely moves real pixels (0.228 → 0.249)" | 0.243 query-weighted; id-mean 0.239 → 0.261. Each per-seed CI spans 0 | AUDIT_H19_H20 | 32, FACTS | R10 | supporting |
| D19 | H20 13 held-out ids; table cells a single statistic | 9 ids cross-camera, 12 cross-time. Point = query-weighted, CI = id-mean bootstrap (now labelled) | AUDIT_H19_H20 | 32 | — | supporting |
| D20 | H20 "1.34 GB peak"; held-out = unseen people | 1,346 MiB. Held out by scene, not provably by appearance (`loiterer_200` appears in both) | AUDIT_H19_H20 | 32 | — | cosmetic |
| D21 | H38 "95 % bootstrap CI" on INT8 loss | n = 3, so the percentile interval is the min–max range | AUDIT_H38 `9cb23b6` | 32, 13, 38, 68, FACTS | — | supporting |
| D22 | H38 "ORT CPU INT8 was not faster than FP16" | unsupported: the same graph varies 4.7× from contention, so no speed comparison can be made | AUDIT_H38 | 32, 13, 68 | R46 | headline |
| D23 | 68 Q10 "site footage is not needed for calibration" | the calibration source (off-site real vs synthetic) did not matter; on-site calibration is untested | AUDIT_H38 | 68 | R46 | supporting |
| D24 | H38 AP50 falls "≤ 0.004", AP75 "0.024–0.040" | ≤ 0.0042; 0.025–0.040 | AUDIT_H38 | 32, 38 | — | cosmetic |
| D25 | H38 results section in 32 | lost from HEAD by the concurrent rewrite `5108fc9`; restored | AUDIT_H38 §0 | 32 | — | supporting |
| D26 | H51/H26 dose gain called "not significant after Holm" with no marker | +0.0042 / +0.0051 AP at equal steps, 10 paired seeds, both Holm p 0.0039 — significant; "n.s." is true only of H26's 5 seeds | AUDIT_H51; `385f363` | 32 §H51, 52, 60, 64, 65 v2, 46, 82, FACTS | R57 | headline |
| D27 | H51 "size unchanged from H26"; corollary "with the v7 pool, 300 iterations beat 450" | close_mosaic and warm-up length also changed between H26/H51 (mosaic on) and h14b/H15 (mosaic off) — not a steps-only comparison; the "300 beats 450" corollary removed as an overclaim | AUDIT_H51 §3 | 32, 46, 52, 60, 64, 65 v2 | — | supporting |
| D28 | H15 v8_vis_300 vs H51 dose300 called "nominally the same recipe" | different: H15's args.yaml has close_mosaic 10 (mosaic closes from epoch 0 under ultralytics 8.4.163); H26/H51 set close_mosaic 0 (mosaic always on) | AUDIT_H51 | 32 | — | supporting |
| D29 | H52 "wrong boxes fall below real-only"; "duplicating real frames does nothing" | shuffled-labels arm is nominally below real-only but Holm n.s. (0.129); the real x10 (dup) arm shares real-only's 60 unique images and step count, so it controls list construction/epoch count, not diversity | AUDIT_H52 | 32 §H52, FACTS | — | supporting |
| D30 | H52 "(a) minus (c) below the noise floor" stated as a clean result; masked-people arm's "about 70% of the gain" read as clean background | (a) minus (c) is exploratory (unadjusted sign-flip p 0.057, never in the registered family); the masked arm's GT boxes are Telea-inpainted, leaving smooth blurred box-shaped patches a detector can learn as "background" — a cue real MOT20 never shows (H61 registered to retest with silhouette masks, not inpainting) | AUDIT_H52 §2 | 32 §H52, 66, FACTS | — | supporting |

## 2. Night

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| N1 | night realism "3/14 `cctv_night_ir`" as current | measured against day targets. Against LLVIP: 3/13 vis · 2/13 thermal; raw renders have luma 90 | H32 step 0 JSON; AUDIT_67-69, STALENESS v2, AUDIT_79 | 17 lines in 23/30/35/40/52/59/60/65/68/00; FACTS realism row | R02 (widened by AUDIT_79) | headline |
| N2 | H11 −0.609 = "night costs 0.609 recall" | a sensor-model sensitivity, not an estimate of the night penalty (see H32b) | AUDIT_79, `84ccb39` | 12 hits in 64/66/69/79, FACTS H11 row | R47 | headline |
| N3 | H32a lowlight / thermal profiles "realistic" (9/13, 10/13) | hold-out 2/13 and 3/13: overfit, not met | `1acb9bd`; AUDIT_H32 | 32, 13, FACTS | — | headline |
| N4 | H32b ran "on CPU, GPU held by X8" | ran on GPU (`B.device` "0") | AUDIT_H32 | 32 | — | cosmetic |
| N5 | H32b "all 12 batch_v8 night cameras" | 9 have GT ≥ 40 px (611 boxes) | AUDIT_H32; AUDIT_13_12 #8 | 32, docs/13 | — | supporting |
| N6 | night penalty range "−0.47 to −0.84" | YOLOv8n only; YOLO26n −0.38 to −0.89 | AUDIT_H32 | 32 | — | cosmetic |
| N7 | thermal recall as measured | an upper bound: heat is painted from the render mask, which is also the GT source | AUDIT_H32 §3 | 32 | — | supporting |
| N8 | profile "random search ≈ 20–35 draws" | unrecorded (no search log committed) | AUDIT_H32 | 32 | — | cosmetic |
| N9 | LLVIP 0.965 / 0.908 "even for detectors pre-trained on colour" | YOLOv5 trained per modality on LLVIP's own train split | arXiv 2108.10831; AUDIT_67-69 | 69 §4, Q&A 2 | — | supporting |
| N10 | "night numbers were a sensor-model artefact"; "conformal per band holds the budget" | hedged: H33 is not per band and is simulated | AUDIT_67-69 #11 | 69 | — | supporting |
| N11 | "raw YOLOv8n 0.938 on LLVIP" (78 opener) | 0.938 is on our undegraded night renders; no night penalty can be quoted | AUDIT_78 #2 | 78 | — | headline |
| N12 | "night 0.15–0.22 real" (69 Q&A 4); "two orders of magnitude" | two medians, not a band; ~60× | AUDIT_67-69 | 69 | — | cosmetic |
| N13 | docs/12 "no real night reference yet" | stale since H32 (LLVIP) | AUDIT_13_12 #11 | docs/12 | — | cosmetic |
| N14 | 79 Q25 "what holds: thermal Δ" | on our sensor model only | AUDIT_79 | 79 | — | supporting |

## 3. Tracking, HOTA and ReID

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| T1 | ByteTrack MOT20 HOTA 0.434 / IDF1 0.549 / hota_at_05 0.539 | TrackEval parity: 0.443 / 0.559 / 0.537, max \|Δ\| 1e-15. The +0.0086 comes from the scorer alone | `5571631`; re-run in AUDIT_M1_PARITY `ce75003` | 17 docs + docs/13 | R41–R43 | headline |
| T2 | 65 D10 "validated against TrackEval on real MOT20" (before M1) | false when written; true only after `5571631` | AUDIT_65 #1 | 65 | R23 | headline |
| T3 | H9 / H17 deltas quoted as TrackEval numbers | pre-parity; the deltas have not been recomputed | AUDIT_M1_PARITY #3 | 32, 73, FACTS, 64, 68, 78 | — | supporting |
| T4 | docs/13 "IDF1 0.54 / HOTA 0.55" current | retired pre-fix figure → 0.559 / 0.443 | AUDIT_13_12 #1 | docs/13 | R16 (rounding missed) | supporting |
| T5 | 73 "synthetic helps tracking only through detection" (general) | synthetic *data* helped only via DetA (H17). An appearance *model* helps association on real MOT20-02 (+0.0139 AssA) | H24 `2fdecd6`; AUDIT_H24 | 73, 64, 52, 60, 48, 65, 23, 79 | — | headline |
| T6 | H24 "appearance never lowered AssA" | never lowered the **mean**. Per checkpoint it did (OSNet s1 −0.0049, HSV s4 −0.0032) | AUDIT_H24 | FACTS | R49 | supporting |
| T7 | H24 MOT20 "CI > 0 in all three" arms | bootstrap over 5 checkpoints. Exact sign-flip p is 0.19 / 0.125 / 0.0625, none < 0.05 | AUDIT_H24 | 32, 66, 73, 48 | — | supporting |
| T8 | H24 GT-box arm "keeps most of the gain → association" | point estimate +0.0137, CI spans 0 | AUDIT_H24 | 32 | — | supporting |
| T9 | H24 night arm (73 §6) run | silently dropped; now disclosed → H46 | AUDIT_H24 | 32, 73, 66 | — | supporting |
| T10 | H24 DetA "moves ≤ 0.003" | holds for the OSNet α-mean only (HSV +0.0051) | AUDIT_H24 | 32 | — | cosmetic |
| T11 | 68 Q17 H17 "entirely via DetA, AssA did not move" | AssA −0.0051 (CI spans 0), 3/5 seeds | AUDIT_67-69 #8 | 68 | — | supporting |
| T12 | MOTSynth "IDF1 53.8 vs 58.1, down 4.3, same shape as H17" | compares no-ReID with ReID. Like for like the gain is +1.7 IDF1 | arXiv 2108.09518 Table 6; AUDIT_70_73 | 73 §2, §3.1, Q1 | R01 | supporting |
| T13 | 73 "12 cameras"; 5.4 people/frame | 11 cameras. 5.4 is per occupied frame (5.05 per rendered frame) | box_aspect re-run bit-exact; AUDIT_70_73 | 73, FACTS | — | cosmetic |
| T14 | H9 cam_sub 0.83 vs 0.51 is the MOT20-amodal mechanism | it is our own loose v7 GT; the MOT20 case is [A] | AUDIT_70_73 #6 | 73 | — | supporting |
| T15 | CAL "about half the CC score is the head" [V] | our inference [INF]; CAL's authors read it as body-shape gain | arXiv 2204.06890 Table 6 | 70, FACTS | R14 | supporting |
| T16 | DeepGaitV2-P3D "2.9 GFLOPs per sequence" | per silhouette image, backbone only (~90 per 30-frame sequence [INF]) | arXiv 2303.03301 fn 2 | 70 §5 | R13 | supporting |
| T17 | "300 ids ÷ 16 bodies ≈ 19"; "3–6 points per paper" | 460 ids → ~29; 1.9–5.9 | AUDIT_70_73 | 70 | R35 | cosmetic |
| T18 | PRCC→LTCC "45-point drop" | the drop is within PRCC (55.2 vs 100); LTCC is a separate dataset | AUDIT_67-69 #4 | 68 Q5 | — | supporting |
| T19 | GREW "79–86 % R1"; LTCC 74.8 as CC | 77.7–79.4 R1 (86 was rank-10); 74.8 has an unstated protocol and CC is 40.1 | STALENESS v2 | 00, 40, 54, FACTS | R07, R08 | supporting |
| T20 | H39 "8/10 cameras ran f to the bound" | 5/10. Pitch was 1.5–4.0°; f is unidentifiable either way | `errors.parquet`; AUDIT_75_H39 | 32, 75 | — | supporting |
| T21 | H39 A2f "pitch within ~2° on 8/10"; PTZ at 48° | 7/10 within 2.1°; PTZ at 30–35° | AUDIT_75_H39 | 32, 75 | — | cosmetic |
| T22 | 75 "box tightness IoU 0.90 vs a detector (13)" | no such number exists; 13 has a width ratio of 1.00–1.03 | AUDIT_75_H39 | 75 | — | supporting |
| T23 | H39 datasheet-f 0.96 m quoted as the result | post hoc; the registered verdict is "not met" (57 m) | AUDIT_75_H39 | 75 §3/§4.1, Q4, Q8 | — | headline |
| T24 | H46 "both clear H24's +0.02 bar" / "Hypothesis (a) -- met" for the argmax w=4 appearance weight | true of w=4's own CI, but w=4 is selected post hoc from a 5-arm sweep with no multiplicity correction -- recomputed Holm across the 5 w-vs-control comparisons, w=4's p (0.0249) exceeds its Holm threshold (0.010), so it does not survive; verdict deferred to H46b's independent cross-validation (R62) | AUDIT_H46 S2 | 32 SH46, FACTS, 66, 13, 73 | R62 | headline |
| T25 | H46 per-w table reports DAssA/DIDSW only | DDetA/DHOTA exist in results.json (rise, never fall, at every w on both sets) but were absent from the published table -- added | AUDIT_H46 S1 | 32 SH46 | -- | supporting |
| T26 | H46b's tracker recommendation (w ~ 8, cross-validated, +0.05 AssA held-out) was implied by the numbers but never written as one explicit, quotable line; `fig_h46b.png` was referenced by name in 32 SH46b/13 since the results landed but never generated or committed | sentence now placed in 73 S3 (primary), 60 item 37, 48, 65 v2 item 22, 79 Q24/round-up, 23, 66; figure generated at docs/research/figures/fig_h46b.png (3-panel: DAssA vs w, DIDSW vs w, night-arm CI bars) | AUDIT_H46B S5, S6 | 73, 60, 48, 65 v2, 79, 23, 66, figures/fig_h46b.png | -- | supporting |
| T27 | H46b cross-validation ("held-out DAssA +0.0479/+0.0570") suspected of reusing the same data for selection and evaluation (H46's garden-of-forking-paths problem recurring) | traced `_cross_validate`: w* is chosen independently on each set's own sweep, then evaluated on the *other* set -- genuinely held-out, no peeking found; this is the real fix to H46's problem, correctly credited to H46b not H46 in 32/13/66 | AUDIT_H46B S2 | (no doc error found) | -- | supporting |

## 4. Loiter θ, conformal and the operator

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| L1 | "A1 ships (θ 0.95)" as a single point | an operator-budget choice among A1 2.915/0.825, pooled 5.033/0.894 and conformal ≈ 2.15/0.78. H45 measured it: 1 operator → conformal θ 0.9629 ranked (0.621 realised); ≥ 2 → A1 ranked; never pooled | H42 `0b4f5d9`, H45 `85e6b18`; AUDIT_H42, AUDIT_H45 | 58 §8.4, 52, 60, 64, 65, 74, 78, 79, docs/13 | R48 | headline |
| L2 | 78 opener: CRC "held its target on 10/10 splits **versus 6** for plug-in" | the plug-in *exceeded* α in 6/10. CRC bounds expected per-world FA, not a per-split cap | H33 results; AUDIT_78 #1, AUDIT_H22_H33 | 78 | — | headline |
| L3 | H33 "10/10" read as the guarantee | the guarantee is on per-world expectation; 10/10 is an observed frequency | AUDIT_H22_H33 | 32 | — | supporting |
| L4 | H33 α 0.001 plain θ = 1 "never alarms" | θ ≈ 0.999996; 0–1 FA per split | AUDIT_H22_H33 | 32 | R27 | cosmetic |
| L5 | H33 B = 84, floor 0.248 | 84–89 across splits; floor 0.248–0.263 | AUDIT_H22_H33 | 32, 67, 74 | — | cosmetic |
| L6 | H33 "also supported at α = 1 and 2" | the exceed rule holds; the ship clause fails at α = 1 | AUDIT_H22_H33 | 32 | — | supporting |
| L7 | H22 ~79 wall-hours; twin floor 0 % bulk-acked | 80.6 h; 0.2 % (0.6 per seed) | AUDIT_H22_H33 | 32, FACTS | R25, R26 | cosmetic |
| L8 | H22 "keeps 62 % (58–65 %)" | 58–65 % is the CI; seed range 58–67 % | AUDIT_H22_H33 | 32 | — | cosmetic |
| L9 | "the operator is the bottleneck" (74) | a hypothesis from an invented-parameter queue; H22 is inconclusive | AUDIT_74 #4 | 74 | — | headline |
| L10 | H42 pooled θ 0.9 is "the stable operating point" | a coarse-grid artefact (a fine grid would pick ≈ 0.94). The zero spread is partly by construction (LOFO pools share 8/9 folds) | AUDIT_H42 | 32, 58 | — | supporting |
| L11 | H45 "θ 0.962851, the modal CRC draw" | the most permissive of 10 distinct draws (each count 1) | AUDIT_H45 | 32, 58, 66, FACTS | — | supporting |
| L12 | H45 2-op conformal vs A1 "≈ tie" | a small consistent loss: −0.022, CI excludes 0, 0/10 seeds up | AUDIT_H45 | 32, 58 §8.5 | — | supporting |
| L13 | H23 select fold "~106 events … flips on one or two events" | 102–113 events; only seed 558's one-event margin is known | AUDIT_ROUND4 | 58 §8.2 | R44 | cosmetic |
| L14 | H21 "one grid step moves FA by 0.9" | across different seed models (3.114–3.145 vs 2.250) | AUDIT_ROUND4 | 58 | R45 | cosmetic |
| L15 | H23 frozen F = the shipped A1 | F re-selects θ and equals A1 on only 3/10 seeds. The "lucky" count compares R with 2.915 | AUDIT_ROUND4 | 58 §8.2, 32 | — | supporting |
| L16 | "zone context −21 % FA" (vs A1) | −20.7 % vs GBM arm B; P8 (≥ 25 %) failed; needs a per-site profile | AUDIT_67-69 #6 (AUDIT_65 #5 recurrence), AUDIT_78 #4, AUDIT_79 | 65, 67, 68, 78, 79 | — | headline |
| L17 | "GBM ≈ −33 % FA at recall 0.80" | no source exists; track-only GBM was +6.8 % vs A1 | AUDIT_67-69 #1 | 67 | R03 | headline |
| L18 | 68 "at 10 s dwell_25 falls to 0.125" | window-only; actor-aware is 0.367 | AUDIT_67-69 #7 | 68 | (R18 family) | cosmetic |
| L19 | H34 1,440 FA / 24 cam-h | valid only at one check per minute (the run evaluates 12.5/s) | AUDIT_H34 | 32, 68, FACTS | — | supporting |
| L20 | H34 "emb threshold above every post-shift window" and "codec moves stats most" | single windows crossed it; codec moves stats least, blur breaks the ranking | AUDIT_H34 | 32 | — | supporting |
| L21 | H34 z_cal 9.2 FA/24 cam-h as a rate; "4,320 windows to certify" | 14 fires = 1 of 162 independent windows (one event); 4,314 | AUDIT_H34 | 32, 68, FACTS | — | supporting |
| L22 | "0.001 is uncertifiable" | FACTS wording: infeasible | AUDIT_78 #6 | 78 | — | cosmetic |
| L23 | 65 F6 "it is paired" (h14b p 0.0079) | an exact unpaired permutation test; the paired n = 5 floor is 0.0625 | AUDIT_65 #2 | 65 | — | supporting |
| L24 | "0.001" quoted bare as a false-alarm-budget standard, or "x over budget" | it is *our* assumed operator budget (A = 4 alarms/shift, K = 500 cameras, H = 8 h, 28 §6); external anchors differ: PIDS ~1/zone/day is [A]; NPCC 3 false calls/rolling 12 months [V] is a different, post-verification quantity | AUDIT_81 §4 | 100+ lines across 58, 60, 65 v2, 68, 74, 76, 77, 78, 79, 52, 48 (32/03/66/71 excluded) | R56 | headline |
| L25 | pooled 5.033 FA/cam-h read as "~205 alarms/h"; conformal 2.10-2.22 as "~92/h"; "20-40x over the lenient end" | ~200/h; ~86/h; ~18-42x | AUDIT_81 §2 | 81 | -- | cosmetic |
| L26 | H33b B = 123.5 called "a valid a-priori bound"; "0 worlds clipped, so the guarantee applies to the unclipped loss" | B's derivation needs <=1 A1 alarm per visitor, which is unenforced (up to 21 eligible episodes for one visitor; 13.7% of visitors with an eligible episode have >1, supplying 53% of all eligible episodes) -- not a valid a-priori bound on L. The CRC guarantee is exact only for the clipped loss min(L, 123.5); on this sample min(L,B) = L (max 89), so the numbers hold, but that is an empirical fact about the sample, not part of the guarantee | AUDIT_H33B §2 | 32 §H33b, 48, 58, 60, 65 v2, 66, 74, 78, FACTS | R60 | headline |
| L27 | H33b/H45b certified ship point quoted as "~0.9635 (~2.22/0.784)" [INF]; "staffing table not expected to change" | measured (H45b, `h45b_operator_points_fixedB`): theta 0.963436 on all 676 worlds = 2.187 FA/cam-h / 0.783; 1-operator realises 0.617 ranked (vs H45's 0.621 at theta 0.962851, -0.004); ship rule (1 operator -> conformal ranked, >= 2 -> A1) unchanged | AUDIT_H33B §3 | 32 §H33b, FACTS | -- | supporting |

## 5. Edge, line-crossing and fusion

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| E1 | 40 cams need "3 NX" | 4 NX with compute (3 is the decode-only ceiling) | FACTS 38 row; STALENESS v2 | 00 | R05 | supporting |
| E2 | 74 drill 1 "4 × NX, 1 hot spare" | that is 40 cams with no spare → 5 NX; fleet 100 | AUDIT_74 #1 | 74 | — | supporting |
| E3 | 74 drill 2 PAR + CLIP on the NX | over budget → site server on keyframe crops [A] | AUDIT_74 #2 | 74 | — | supporting |
| E4 | "training pipeline refuses a set without licences.json" | no such gate exists: "should refuse; manual today" | AUDIT_74 #4 | 74 | R54 family | headline |
| E5 | H40 noise model "declared" | assumed | AUDIT_76_H40 | 32, 76, 74 | — | supporting |
| E6 | H40 arm C excludes door props | the code excludes gate/queue zones only (undisclosed); cannot change the verdict | AUDIT_76_H40 | 32 | — | supporting |
| E7 | 76 Q8 "a lower bound on the people-only component" | optimistic for a real fence | AUDIT_76_H40 | 76 | — | supporting |
| E8 | H40b noise-free residue "all commuters pressed against a fence" | all wildlife (1.84/cam-h) | AUDIT_H40B | 32, 76 | R50 | supporting |
| E9 | H40b "remaining misses are tracker fragments" | rule 10.1 pts + context 4.7 + noise 7.0; stitching alone cannot reach 0.9 | AUDIT_H40B | 32, 76, 66 H50 | R50 | headline |
| E10 | "a role-blind rule cannot remove" twin FA | a gate exemption can; what it cannot do is separate guard from intruder inside | AUDIT_H40B | 32, 76 | — | supporting |
| E11 | 76 hard-negatives "Fence climb" row | overwritten by an edit; restored | AUDIT_H40B | 76 | — | cosmetic |
| E12 | "context and a second sensor" is the answer (78 opener) | retired (unmeasured), then reinstated in qualified form: removes 99 % of authorised-crosser FA (0.488 → 0.0047), recall 0.782 → 0.758, sensors simulated, matched on true tracks, a tailgater defeats it | H53 `4e32862`; AUDIT_78 #3, AUDIT_H53 | 78, 32, 37, 52, 60, 64, 74, 76, FACTS | R55 | headline |
| E13 | H53 "recall cost 2–4 points", "robust" | 2.3 combined. The JSON's `robust` is false. The ≥ 0.782 bar is a registration design flaw | AUDIT_H53 | 32, 66 | — | supporting |
| E14 | "fusion can fix it" (65 v2 Q2) | untested at the time → now H53's qualified result | AUDIT_65_V2 | 65 v2 | R54 | supporting |
| E15 | 79 Q1 "detection dominates ingest compute" | an estimate, not profiled | AUDIT_79 | 79 | — | supporting |
| E16 | 72 vendor claims (UMD, Alta NL, BriefCam R/R/R, Coram/Spot pricing, Ambarella VLM) | 7 [X]: BriefCam is Investigator / Rapid Review / Protect / Insights | fetches in AUDIT_72 | 72 | R12, R40 | supporting |
| E17 | H47 evasion crowd_cover -0.201 [-0.210, -0.192], Holm p 0.003 quoted as the headline CI/significance | that CI/p is frame-level (frames of a 30 s, 10 fps clip are strongly autocorrelated, so it is too narrow); the clip-cluster (paired, 4 clips) CI is [-0.254, -0.154], and the smallest one-sided p reachable at 4 clips is 1/16 = 0.0625 -- direction and size are not in doubt (every clip <= -0.136; verdict NOT MET either way), but "Holm p 0.003" must not be quoted as the significance | AUDIT_H47 §2 | 32, FACTS, 50, 66, 52, 64, 60, 65 v2, 79, 48, 74 | -- | headline |
| E18 | H47 "hood_up" treated as testing a real hood; untested techniques (umbrella, carried object, crouch/crawl, face_away) listed only as "not tested" | hood is a colour proxy only (`face_cover` RGB paint over hair/skin, no hood geometry) -- "a dark head colour does nothing"; "untested is not no effect" now stated wherever H47 is quoted (they are H55's registered arms) | AUDIT_H47 §3 | 32, 50, 52, 64, FACTS, 48, 65 v2, 79 | -- | supporting |
| E19 | H47 editor VRAM peak "5.18 GB"; "both detectors agree on every sign"; 66 "evasion halves exposure" | peak is 5,593 MB (hivis s3), not 5,176 MB (dark_lowcontrast s2); detectors agree only on every effect whose CI excludes 0 (dark: YOLO26n +0.003 vs YOLOv8n -0.001); "halves exposure" corrected to -43% | AUDIT_H47 §1, §4 | 32, 66 | -- | supporting |

## 6. Law and standards

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| W1 | Art 22B special category: "explicit consent or contract/legal necessity" | (contract *or* required by law) **and** Art 9(2)(g); Art 6(1)(ea) barred | DUAA s.80 text; AUDIT_67-69 #2 | 67 §5 Q4 | — | headline |
| W2 | 74 "Art 22" loosely | Arts 22A–D inserted by DUAA s.80, in force 5 Feb 2026 (SI 2026/82); human-decision box added | AUDIT_74 #5 | 74 | — | supporting |
| W3 | JSP 936 "expects in-service monitoring" | not a quoted clause → [A] | AUDIT_67-69 #12 | 68 Q14 | — | supporting |
| W4 | SAPIENT "capability reduced" state | not a state: `StatusReport` coverage / `NOT_DETECTING` | AUDIT_65 #6; recurred AUDIT_67-69 #9 | 65, 68 | — | supporting |
| W5 | PSTI missing from drills | added, with its consumer-SKU scope | AUDIT_74 #5 | 74 | — | cosmetic |
| W6 | 65 D8 MetaHuman renders "quarantined, not used for any result" | H1–H8 and 0.758 used batch_v4/v6. Internal engineering evidence only | AUDIT_65 #3 | 65 | — | headline |
| W7 | "~3,000×" budget ratio | ~2,900× | AUDIT_67-69 #10 | 67 | (R30 family) | cosmetic |
| W8 | 85 Q10: a proposed customer push "would be a DEFCON 658/Cyber Essentials breach" | stated as a legal determination, which 85 §0.3 forbids -> reworded "could breach the company's ... obligations" | AUDIT_84_85 §3 | 85 | -- | supporting |
| W9 | 85 five AI ethics principles, ITAR/EAR US-origin reach, Cyber Essentials Plus, vetting sponsorship all tagged [A] | [V]: ASR Annex A (Human-Centricity, Responsibility, Understanding, Bias and Harm Mitigation, Reliability); 15 CFR 734.3(a)(2)/(3) and 22 CFR 120.51 (LII text) on US-origin reach and deemed reexport; NCSC "the same protections, but with more rigorous, independent technical testing" for CE+; NSV "set by the departmental authority responsible for the post" for sponsorship | AUDIT_84_85 §2 | 85 | -- | supporting |
| W10 | 85 DEFCON 658 cited at a URL slug that now 404s | live at the `-cyber-flow-down` slug (edition 10/17, updated 13 Dec 2022); source line annotated | AUDIT_84_85 §1 | 85 | -- | cosmetic |

## 7. Company facts (the vendor)

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| C1 | ">£5 m revenue … contractors across Europe and the US" | tail not returned on re-fetch → dropped | mavencp.com release; AUDIT_78 | 78 | — | supporting |
| C2 | "designed to perform in challenging environments…" in quotes | a summary, not a quote → de-quoted | AUDIT_78 | 78 | — | cosmetic |
| C3 | "Likely [A]" architecture guesses (backbone, event camera, GPUs, slew-to-cue) | removed; unknowns turned into questions | AUDIT_78 §5 | 78 | — | headline |
| C4 | "your Ukraine set" | a trade-press [A] claim about sensitive data → removed | AUDIT_78 §5 | 78 | — | headline |
| C5 | director commentary ("unexplained") | removed; background only | public registry; AUDIT_78 | 78 | — | cosmetic |
| C6 | "Sovereign solutions" attributed to /our-work/ | the source is /what-we-offer/ | AUDIT_78 | 78 | — | cosmetic |
| C7 | 78 30/60/90 "M1 remainder: evaluator parity" | parity is done; what remains is profiling + manifest hashes | AUDIT_78 §4 | 78 | — | supporting |

## 8. Engine, ground truth and process

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| G1 | wildlife never exported as "person" | the `survsim dataset` path ignores it (class 8). The demo `coco.from_camera_rows` path did not filter → fixed in code | AUDIT_H40B §4; `3377ea2` | `survsim/gt/coco.py` | — | supporting |
| G2 | `test_fence_stops…` exercises the fence | vacuous: the loiter agent never moved (0 clamps) → fixed | AUDIT_H40B §3; `3377ea2` | tests | — | supporting |
| G3 | TrackEval parity regression test | asserts 1e-3, while the measured value is 1e-15 → recommended 1e-9. **Now 1e-9 / 1e-12** (`4b9534d`); `score()` KeyError 'deta_mean' from `2fdecd6` fixed, re-run max \|Δ\| 9.99e-16 | AUDIT_M1_PARITY #1 | closed | — | supporting |
| G4 | FACTS row count 282 / 279 | 318 → 320 → 324 by script (rows land concurrently) | AUDIT_79, AUDIT_H24, AUDIT_NARRATIVE | FACTS header/footer | — | cosmetic |
| G5 | FACTS H38 row | glued onto the batch_v8 row → split | AUDIT_H38 | FACTS | — | cosmetic |
| G6 | H24 / 66 / 32 content | reverted by a concurrent-index race (`84ccb39`) → restored | `a9dee60`, `0233291`, `82faa11` | 13, 32, 66 | — | supporting |
| G7 | "no doc-consistency test exists" | two exist now (§9) | AUDIT_65_V2, AUDIT_79 | tests | — | supporting |
| G8 | docs/12 batch_v6 "0.666 / 0.824" | re-scored 0.665 / 0.823 (score-order matching) | AUDIT_13_12 #10 | docs/12 | — | cosmetic |
| G9 | docs/13 loiter "(shipped)" labels | round-1 / superseded; A1 relabelled (see L1) | AUDIT_13_12 #4–5 | docs/13 | R19, R48 | supporting |
| G10 | 65 D6 v6 vs v7 recall gap "can't be reconciled" | cast, scenes and a label bug all differ at once, so no single cause can be isolated | AUDIT_65 #4 | 65 | — | supporting |
| G11 | 82 audit narrative framed the h14b retraction as "proof the number was wrong" (Q1, Q20) | h14b was a correct measurement of a confounded comparison; H26 shows the claim unsupported (+0.004-0.005, n.s.), not that the gain is zero -- reworded away from "retraction as proof of wrongness" | AUDIT_82 §3 | 82 | -- | cosmetic |
| G12 | 82/46 "the fix retracted the headline everywhere" | only in the 19 docs that stated it as current; 32 keeps it as the historical h14b result | AUDIT_82 §3 | 82, 46 | -- | supporting |
| G13 | FACTS row count stated as 324 | HEAD actually had 339 (10 process rows had landed); now 350 | AUDIT_82 §5 | FACTS | -- | cosmetic |
| G14 | 84/85 4-hour prep path summed to 250 min against a stated 240; `42` Day 2 summed to 450 against a stated 435 | trimmed step 13 (`17` system design overview) from 20 to 10 min, restoring 240; `42` Day 2 block 10b cut, header corrected to 445 | AUDIT_84_85 §5 | 84, 85, 42 | -- | cosmetic |

**Counts (§1–§12, 168 rows):** headline 40 · supporting 87 · cosmetic 41.



## 9. Fusion, twins and identity switches

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| FU1 | H54 est/true C+abc "19 alarms" quoted for both matchings | true matching leaves 18 alarms (0.9913 vs est 0.9908, both within CI) | AUDIT_H54 §1 | 32 §H54, FACTS, 66 | -- | cosmetic |
| FU2 | H54 "estimated matching costs almost nothing"; the pre-registered ~90% prediction "was wrong" | 99.1% is an upper bound under a benign (no-IDSW) noise model -- the noise model never swaps identity between two people; the prediction was wrong in the optimistic direction; H24 measured real ByteTrack+OSNet IDSW at 87.0-92.6 per MOT20-02 run, tested by H59 | AUDIT_H54 §2 | 32 §H54, 66, FACTS | -- | headline |
| FU3 | H54 gate counter "follows through within seconds"; "counts every inward passage" | median gap 3.0 s, but 12/86 truth-event gaps exceed 10 s and 3/89 are unlogged; the counter counts only twins + incident actors (never commuters or wildlife), with an excess window taken from PIDS's [-30, +5] s | AUDIT_H54 §3 | 32 §H54 | -- | supporting |
| FU4 | H59: suspicion that the identity-switch hazard never reaches fusion scoring, since twin-removal reads 99.1% under both benign and calibrated noise | traced code plus an empirical rerun (1,322 forced swaps at extreme hazard; 1 of 2 resulting alarms scored under a swapped label); the registered rate produces non-zero swaps at every world/arm/seed (157.6 / 472.7 per track-h, matching the calibration target) -- twin-removal insensitivity is structural (position-gated matching), not a hazard that never fires | AUDIT_H59 §1 | 32 §H59, 00 | -- | headline |
| FU5 | H59 IDSW-rate arithmetic (83.4/1,904.6 = 157.6/track-h, stress 3x) and the "H24's 87-93 IDSW/MOT20-02 run" cross-reference | arithmetic exact, recomputed from `h24_reid_assoc/results.json`; the "87-93" figure elsewhere is a *different* H24 measurement (real MOT20-02 validation, range 87-108) from the batch_v8 rate (83.4 mean) H59 actually calibrated to -- a doc cross-reference ambiguity, not a calibration error; using the higher real rate would only strengthen H59's "not met" verdict | AUDIT_H59 §2 | 32 §H59 | -- | supporting |
| FU6 | H54's 0.685 tailgater recall (gate counter, GT identities) and H59's 0.10 (actor-aware, calibrated ID-switch noise) quoted unqualified or as if contradictory | reconciled: `C` alone (no fusion leg at all) collapses identically to `C+abcg` under calibrated noise (0.108 vs 0.100) -- the collapse happens before any fusion leg runs, so it is an actor-aware scoring-denominator artefact (the alarm is credited to the swapped uid), not a fusion break; label-agnostic (window-only) recall recomputed at 0.828 (`C`) / 0.739 (`C+abcg`) -- the fused decision itself is still largely correct; a real system would score by position/time | AUDIT_TAILGATER_RECONCILIATION | 32 §H59, 13, 48, 52, 60, 64, 65 v2, 74, 76, 78, 84, 90 | R61 | headline |
| FU7 | 90 Drill-1 walkthrough: "better than the looser theta 0.95 point, which floods the queue" | backwards: A1's theta 0.95 is the *stricter* point (120 alarms/h); it is pooled theta 0.9 that floods the queue (205 alarms/h, only 0.504 realised) -- `90` was internally self-contradicting against its own later, correct statement of the same fact | AUDIT_90 | 90 | -- | headline |

## 10. Evidence pack, alarm cards and security

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| EV1 | 86: "NIST's 'role-appropriate' transparency"; Adebayo's saliency findings attributed to Grad-CAM/integrated gradients by name | NIST's actual phrase is "tailored to the role or knowledge of AI actors"; Adebayo's "independent of the model and the data-generating process" describes *some* methods generally, not those two by name -- reworded: saliency is not evidence, and passing the checks would not make it an explanation of one alarm | AUDIT_86 §1 | 86 | -- | supporting |
| EV2 | 86 §7 "SurvSim can fill today" schema tags (alarm_id, camera_id, track_uid, zone_id, box_xyxy, score/theta/rank, camera_health preset, i_lids_delay_s, gt_match verdicts all marked fillable) | over-tagged against the code: no alarm carries an id; no single alarm carries both camera and uid set; zone_id/i_lids_delay_s/per-alarm gt_match verdicts require a join or are not emitted at all; box is `left,top,w,h` not xyxy -- retagged fillable/partial/join/gap/not-emitted per field | AUDIT_86 §3 | 86 §7 | -- | headline |
| EV3 | ISO/IEC 42001 and ISO/IEC 27001 tagged [A] | [V]: BS ISO/IEC 42001:2023 (31 Dec 2023, superseded by BS EN ISO/IEC 42001:2026, no technical differences); ISO/IEC 27001:2022, certifies organisations not products; JSP 441 stays [A] (unreachable) | AUDIT_86 §2 | 86 | -- | supporting |
| EV4 | H60 alarm-card leak guard `gt_values` "checks every GT uid, event id, zone and identities cell" | shipped guard omitted zone names (would not have caught a zone leak) -- fixed; `verify()` accepted a rehashed reason-less dismiss and did not refuse tail truncation without an anchored head -- both fixed (`expected_head=`); NaN was silently accepted by canonical JSON, now refused | AUDIT_H60 | 32 §H60, 86 §7, 66, 74, 63, 65 v2, FACTS, 00 | -- | headline |
| EV5 | H60 "deleting a record fails at the gap"; per-field "abandon if" prediction "held" | imprecise: only *middle* deletion is caught this way -- tail truncation needs an anchored head; the "abandon if" clause literally triggers only for GT-rule alarms today -- real mode is a guard only, no tracker-sourced alarm or runner score is carded yet | AUDIT_H60 §3 | 32 §H60 | -- | supporting |
| EV6 | 87 Q5: leak guard "greps by value for every GT uid, event id, zone name and identities cell" | the shipped guard has no `identities.parquet` check (that check was AUDIT_H60's manual check, not code) and its needles are whole quoted strings only, so a value inside a longer string is missed -- both closed later in `e3f7e13` | AUDIT_87 §1 | 87 Q5 | -- | headline |
| EV7 | 87 Q7 (and 63 B2): "the pack detects changes after the card is written" | overclaim: `verify()` only checks `evidence_log.jsonl`; nothing recomputes `card_sha256` against `cards.jsonl`, so a card can be edited in place undetected -- closed later in `e3f7e13` (`verify_cards`) | AUDIT_87 §1 | 87 Q7, 63 B2 | -- | headline |
| EV8 | "tamper-proof" and bare "compliant" used affirmatively (12 "the compliant set"; 47 "Recommended compliant character stack") | reworded to "licence-compliant (CC0)"; R58 added to flag `tamper-proof`/bare `compliant` unless negated, quoted, licence-qualified, a third-party category, a red flag or a URL | AUDIT_87 §3 | 12, 47 | R58 | supporting |
| EV9 | 88 coding-drill references: Drill 3 assignment solved then filtered by `max_cost` (the very gating trap the drill warns about); Drill 6 DLT claimed parity with survsim's normalised Hartley DLT using an unnormalised reference; Drill 7's continuity bonus used the last-*ever* pred id instead of the previous *scored* frame (wrong MOTA/IDSW: -0.33/0 vs the correct -0.67/1) | all three fixed in `drills/drills.py` with new regression tests (12 -> 19 passing); the old "matches survsim exactly" tests had passed only because their toy examples were too clean to separate the buggy and correct versions -- a candidate who learned from the old file would have reproduced the bug in the room | AUDIT_88 | drills/drills.py, tests/test_coding_drills.py, 88 | -- | headline |

## 11. Quantisation

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| Q1 | 60 item 37 / 66 row 15b: "H43 TensorRT INT8 on an Orin (or QAT) is backlog, not registered" | stale: the PTQ-calibration leg (Percentile vs MinMax vs Entropy) is done and not met (recovery 0.415 corpus-wide / 0.424 h14b-only, both < 0.50 bar; 0/5 checkpoints regressed vs MinMax); QAT ran end-to-end on only 1/5 checkpoints (recovery 0.072, misses both the PTQ and QAT bars) and is deferred to H43b (full 5-checkpoint run); TensorRT-on-a-real-Orin remains backlog | AUDIT_H43 | 60 item 37, 66 row 15b/15c | -- | headline |
| Q2 | H43's n=5 bootstrap CI labelled "bootstrap" (contrast AUDIT_H38's n=3, which required "range" instead) | correctly distinct: at n=5 an all-identical resample has p = (1/5)^5 = 0.00032 much less than 2.5%, so the percentile CI is not forced to the sample min/max the way n=3's was -- H43's "bootstrap" label is accurate, not mislabelled | AUDIT_H43 | 32, FACTS, 38, 60 | -- | cosmetic |
| Q3 | 60 item 37: H43b/H43c QAT status stale -- described only the H43 PTQ leg and "(66)" deferral to H43b, with no outcome | H43b (full 5-checkpoint QAT) done, not met (recovery 0.366/0.334 < 0.50/0.80 bars); H43c (learned-range QDQ export) done, not met (recovery 0.439, still < 0.50); one canonical edge sentence now placed identically in 38 S2.5 row 13, 68 Q10, 60 item 37, 65 v2 S0 item 8, 77 #3 | AUDIT_H43BC S2 | 60 item 37, 38, 65 v2, 68, 77, FACTS | -- | headline |
| Q4 | 32/FACTS/38/65 v2 "the [QAT] shortfall is attributed to the QAT recipe (150 iterations), not the export path" stated as a flat conclusion | an inference from one data point -- no longer-QAT arm exists anywhere in the corpus; hedged as *inferred*, not itself measured, with a proposed follow-up H43d | AUDIT_H43BC S1, S2 | 32 SH43c, FACTS, 38, 65 v2 | -- | supporting |

## 12. PTZ and calibration

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| P1 | H56 "CPU 8 s" wall time | `results.json` `wall_seconds` 10.0; reruns 7-10 s | AUDIT_83_H56 §1 | 32 §H56 | -- | cosmetic |
| P2 | 83/32: "shorter/closer PTZ, same 6 m frame, larger angular error" explains the near-range 2-PTZ drop | wrong geometry: a closer PTZ sees a 6 m frame at a *wider* angle, and a fixed metric error and a fixed metric frame both scale as 1/range, so their ratio does not change; the exact arm also drops (0.967 -> 0.938 near) -- cause now stated as untested | AUDIT_83_H56 §2 | 83, 32 | -- | supporting |
| P3 | H56 missed_second 37% attributed to optics ("far-field misses from a 6 m frame against ~3 m range error") | it is a queueing number: busy-at-arrival 0.382 is close to missed 0.369, driven by the assumed 10 s dwell against a 3 s window and FIFO policy, not by optics; the optics explanation stays untested (now registered as H57) | AUDIT_83_H56 §2 | 83, 32, FACTS, 64 | -- | headline |
| P4 | 83: "auto-tracking is not standardised in ONVIF" | [X]: ONVIF spec §5.3.6 `MoveAndStartTracking` standardises the move-then-track hand-off (GeoLocation/preset/PTZVector, optional ObjectID); only the tracker itself is vendor-specific | AUDIT_83_H56 §3 | 83, FACTS | -- | supporting |
| P5 | 83/32: "PTZ <= 20 m leg held" stated as a plain pass | met on the point estimate only; the seed-cluster CI [0.872, 0.936] spans the 0.9 bar | AUDIT_83_H56 §1 | 32 §H56 | -- | supporting |
| P6 | `ptz_slew` (H56) missing from `RUNNERS`; `survsim experiment h56_ptz_slew` failed | registered; 39/39 experiment tests pass | AUDIT_83_H56 §5 | survsim/experiments/__init__.py | -- | supporting |

## 13. Process

**How a claim gets into FACTS.** A number enters `FACTS_VERIFIED.md` only with a source. That is
either a committed `results.json` (hash cited) that an audit recomputed independently in `.venv`, or a
primary page fetched in the session (URL and date cited). Derived numbers carry their arithmetic.
Pre-registration comes first (32, commit before run). The verdict follows the registered rule even
when it hurts (H24 missed by 0.0006; H53 missed its recall leg).

**How a claim gets retired.** The audit fixes every live occurrence in place and adds a row to
`RETIRED_CLAIMS.md`. The row holds a regex, the correct form, the retiring audit, allowed files and an
"exempt if line has" regex. A retired value may appear only as the "before" of a stated correction.
AUDIT_79 removed the bare "was" exemption because it let stale lines through. A retired phrase can
come back only in an exact qualified form (R55, reinstated after H53).

**What the two doc tests enforce.**
* `tests/test_docs_retired_claims.py`: every row's regex runs over `docs/**/*.md` + `CLAUDE.md`. A hit
  fails unless it is on an allowed file or an exempt line. Fixtures prove stale lines fire and
  corrected lines pass. A pin test keeps docs/12 and docs/13 in scope.
* `tests/test_docs_numbers_in_facts.py`: every decimal in 60, 65 v2 and docs/13 must appear in
  FACTS or in `facts_derived_allowlist.txt` with its derivation. docs/13's 137 engineering decimals
  are allowlisted as **RATCHET, not verified**: new unsourced decimals fail, old ones are not
  claimed.

**Honest list of what is still unverified or open.**
* Hypotheses open: **H36** (full LLVIP fit, needs download sign-off), **H41** (keypoint
  auto-calibration; batch_v8 has no keypoint GT), **H43b** (QAT, full 5-checkpoint corpus —
  pre-registered in 32/66, running; the PTQ-calibration leg is done, not met, §11), **TensorRT
  INT8 on a real Orin** (still backlog; H43's no-Jetson accuracy result does not touch it),
  **H44** (certify drift monitor, ≥ 4,314 windows), **H46** (ReID weight sweep + night arm),
  **H48** (real SOC review times; the whole ship table rests on an invented operator), **H29**
  (300 ids ÷ 16 bodies decomposition, [INF] only), **H61** (label-vs-image ablation with
  silhouette masks, not inpainting — H52's masked arm has a learnable inpainting artefact, §1),
  **H62** (position/time-keyed alarm scoring pre-registered but not run — the fix H59/the
  tailgater reconciliation implies, §9). Also H37, H49, H50, H55 (evasion, ≥ 10 clips), H57
  (PTZ far-field-miss optics, §12), H58 (occlusion on the PTZ path). H51, H52, H54, H47(evasion)
  and H33b are now **done** (§1, §9, §11) — no longer open.
* Evidence-pack gaps carried forward from §10, not yet closed: **the evidence-log head is
  unsigned** — no RFC 3161 timestamp or signature on `head.json`, only "ANCHOR THIS HEAD out of
  band" printed by the CLI (AUDIT_87 Q3); **the operator-id salt is a public CLI default**
  (`survsim-h60`), not per-site and not stored anywhere, so a small roster is reversible by
  enumeration (AUDIT_H60 §2, still doc-only — H60 slice 2 backlog item).
* Pre-parity numbers not recomputed: the H9 and H17 deltas (T3).
* Unreconciled: H26 dose100 0.4952 < h14b mix_100 0.4983; H15 v8_vis_300 0.4981 vs H26 0.4956
  (AUDIT_H26 §3).
* [A] items: Orin NX per-camera budget with PAR/ReID (only the decode figure is [V]); JSP 936 monitoring
  clause; KAIST MR figures; 69 §1–2 vendor physics; Lv/Nevatia 2006 and Liu BMVC 2011; PRCC/LTCC and
  MEVID licence pages; NPSA PIDS definitions; UMD, Ambarella, Pritch TPAMI, Milestone search; MOT20
  "high and steep" geometry; 72 §2.3 index size with thumbnails; stature SD ~7 cm; H23 select-fold
  margins; H32 search draws; MetaHuman wardrobe and `nav/goto` in the engine (CLAUDE.md).
  HSE ALARP pages and Def Stan 05-138 Issue 4 are [X] (unreachable).
* docs/13: 137 RATCHET decimals not yet key-matched to their `results.json`. docs/12: ~295 engine-log
  decimals have no test. docs/11 "14 % wider" not re-derived.
* The TrackEval parity test tolerance is still 1e-3 (G3).

## 14. Cross-audit reconciliation (2026-09-27)

Contradictions between audit files, each resolved by a dated "Superseded" note at the top of the
older file. Bodies are left as the historical record.

| older audit | what it says | later truth | note added |
|---|---|---|---|
| AUDIT_52-53, AUDIT_64, AUDIT_61-63 | agree on HOTA 0.434 / h14b +0.0121 / H17 +0.0103 as current | pre-parity (M1) and unequal-step (H26) | yes |
| AUDIT_65 (v1) | N-table "matches" 0.0121, 0.434, HOTA +0.0103, 3/14; A1 ships | R41, R51, R53, R02, R48; 65 v2 and AUDIT_65_V2 replace it | yes |
| AUDIT_STALENESS_SWEEP v2 | "no dedicated doc-consistency test exists" | two exist | yes |
| AUDIT_H22_H33 | 58 §8 ship = "θ by CRC, ranked" | 58 §8.4 table (H45) | yes |
| AUDIT_ROUND4 | H21 `ships` A1 | ship point = operator budget (R48, H45) | yes |
| AUDIT_H42 | pooled/conformal loads "bracketed [INF], not measured" | measured by H45 | yes |
| AUDIT_H25 | H25 "clean gain +0.0127" read as the dose gain | unequal step (H26, AUDIT_13_12 #6) | yes |
| AUDIT_67-69, AUDIT_70_73, AUDIT_74 | H17 AssA/DetA and h14b +0.0121 cited as [V] matches | pre-parity / unequal-step | yes |
| AUDIT_78 | #3 "context and a second sensor" retired | reinstated in qualified form (R55, AUDIT_H53) | top note (the row already said so) |
| AUDIT_79 | H24 "run in progress"; FACTS 318 | H24 done (not met); FACTS 324 | yes |
| AUDIT_H34 | FACTS count 282 | 324 | yes |
| AUDIT_H40B | coco wildlife gap and vacuous fence test "not fixed" | fixed in `3377ea2` | yes |
| AUDIT_65_V2 | "H53 running, no result" | H53 reported (AUDIT_H53) | yes |
| AUDIT_M1_PARITY | "historical AUDIT files left as-is" | notes now added (this pass) | no (policy statement, still true of bodies) |

## 15. docs/02 and docs/03 vs code (2026-09-27, AUDIT_02_03)

`docs/02_ARCHITECTURE.md` and `docs/03_BEHAVIOUR_CATALOG.md` — the two "design intent" docs an
interviewer is likely to open — were stale against `survsim/director/behaviours.py`: 03 listed
`vendor`/`worker_patrol`/`graffiti_vandalism`/`mass_rush`/`drone_intrusion`/`assault_weapon_like`/
`push_over_barrier`, several with no matching `REGISTRY` class or under an old name, and omitted the
H54 `fence_tailgate`/`staff_escort` twin entirely. 02 never named fences, appearance epochs, the
alarm-card/evidence-pack/TrackEval eval components, the experiments framework, the 7 degrade profiles
(nor that the two night ones are LLVIP-overfit), the licence gate, or CLAUDE.md's principles list, and
still described the `unreal` backend as "UnrealCV+ over TCP" — the claim CLAUDE.md itself retracted.
Fixed in place (docs only); both docs now carry a "last verified against code" line. See AUDIT_02_03.

## 16. Statistics interview doc (2026-09-27, AUDIT_91)

`91_MOCK_INTERVIEW_ROUND9_STATISTICS.md` (round-9 mock interview on pre-registration, bootstrap
units, sign-flip floors, Holm vs Bonferroni, conformal B and garden of forking paths) audited
against the ten audits it cites; every H-number claim traced to its source audit's own table.

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| S1 | 91 Q4: n=5 one-sided sign-flip floor 2/32; n=6 floor 2/64 = 0.03125 | the one-sided floor uses 1 extreme sign vector out of 2^n, not 2 (2 is the two-sided numerator): n=5 -> 1/32=0.03125, n=6 -> 1/64=0.015625 | AUDIT_91 §1, §5 | 91 | -- | supporting |
| S2 | 91 Q7 follow-up: theta 0.9629 (fixed, invalid) -> 0.9618 (capped, valid); FA/recall 2.19/0.784 -> 2.20/0.789 | 0.9629 is H45's original pre-B-fix ship point, not H33b's certified "fixed, invalid" point (theta 0.963436); corrected to 0.9634 -> 0.9618, FA/recall 2.19/0.783 -> 2.20/0.789 (pooled-vs-pooled, not pooled-vs-held-out-mean) | AUDIT_91 §1, §5 | 91 | -- | supporting |
| S3 | 91 glossary: "Bootstrap sign-flip p for mean(x)==0" left as an unnamed "`holm()`-adjacent" placeholder | the actual function is `boot_p_two_sided()` in `tracking.py:39` -- named | AUDIT_91 §3, §5 | 91 | -- | cosmetic |
| S4 | 91 glossary: `bootstrap_delta()` labelled "clip-cluster paired bootstrap (frames within seed×camera)" | self-contradictory label; the function's own docstring resamples frames within a stratum -- exactly the frame-level bootstrap AUDIT_H47 §2 found too narrow for clip-clustered evasion data; relabelled, and the clip-cluster CI used in AUDIT_H47 noted as having no named function (now closed in code: H47 `bootstrap_delta` fixed to resample clips by default, `492d377`) | AUDIT_91 §3, §5 | 91 | -- | supporting |

## 17. H43d QAT thread closed (2026-09-27, AUDIT_H43D)

`AUDIT_H43D.md` recomputed every H43d number (per-checkpoint AP75 recovery 0.331/0.531/0.782/
0.077/−0.500, pooled 0.374 vs H43c's 0.439, the AP-loss met/miss split, and the `qat_fp32`
no-degradation confound) against `out/experiments/h43d_qat_more_iters/results.json` — all match.
The recovery split tracks the checkpoint recipe exactly: `h14b`/mixed-data checkpoints improved
with more iterations, `H51`/equal-steps checkpoints got worse — confirmed against
`results.json["config"]["checkpoints"]`, not an unverified pattern-match on two numbers.

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| U1 | `32` §H43d decision line read "hypothesis not supported" | tightened to "hypothesis refuted — recovery fell, it did not rise", matching `66`/`38`'s wording for the same result | AUDIT_H43D §1 | 32 | -- | supporting |
| U2 | QAT-story clause ("longer QAT does not help and hurts two checkpoints — remaining loss is INT8 quantisation of this architecture, not the fine-tune") missing from `38` §2.5, `68` Q10, `65` v2 §0/§4, `77` #3, `78` | clause added identically wherever the QAT story is told; H43e (TensorRT INT8 on real Jetson hardware) added to `66` as the only remaining edge item | AUDIT_H43D §1–2, commit `27a9f88` | 38, 68, 65 v2, 77, 78, 66 | -- | headline |

## 18. Evening staleness pass on doc 78 (2026-09-27, AUDIT_78_EVENING)

`removed-vendor-doc.md` audited against the current evening's results (65 v2, 32, 38, 58,
73, 84, FACTS_VERIFIED) — ten findings, nine fixed in place, one flagged not actioned.

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| V1 | 90-second opener's tailgater/H59 sentence paraphrased `65` v2 §1a | rewritten byte-identical to `65` v2 §1a | AUDIT_78_EVENING #1 | 78 | -- | cosmetic |
| V2 | Tracker product section named no recommendation | added ByteTrack + OSNet-ImageNet at w ≈ 8, cross-validated (H24/H46b), with IDSW cost stated and never appearance-only | AUDIT_78_EVENING #2 | 78 | -- | headline |
| V3 | New tracker sentence carried no caveat | added the H46b night-arm caveat (ΔAssA CI still touches zero) next to it — not a met/positive result | AUDIT_78_EVENING #3 | 78 | -- | supporting |
| V4 | Edge/H38 line omitted H43/H43c entirely | added Percentile/QAT recovery (~41–44 %, below the 50 % bar) and flagged H43d as running (closed the same evening by AUDIT_H43D, §17) | AUDIT_78_EVENING #4 | 78 | -- | headline |
| V5 | [vendor product] §1.5 stated the H54 tailgater 0.685 recall bare, no H59 caveat (RETIRED_CLAIMS R61 violation) | added the H59 ID-switch collapse to 0.10 and the label-agnostic 0.83/0.74 reconciliation | AUDIT_78_EVENING #6 | 78 | R61 | headline |
| V6 | [vendor product]'s H34 drift line said "registered, runner uncommitted, no number" | H34 has run and is inconclusive; replaced with the real PSI/KS/z_cal/embedding numbers | AUDIT_78_EVENING #7 | 78 | -- | supporting |

`/tmp` was 12 GB at the time of this audit, over the stated budget, but nothing in it was clearly
safe to delete without risking another session's or VM's data — flagged, not deleted
(AUDIT_78_EVENING #10).

**Counts (§1–§18, 184 rows):** headline 44 · supporting 97 · cosmetic 43.

## 19. H62 position/time scoring audit (2026-09-27, AUDIT_H62)

`AUDIT_H62.md` recomputed every number in 32 §H62 and the task brief directly from
`out/experiments/h62_position_time_score/results_calibrated.json`/`results_benign.json` — all match exactly
(recall 0.685/0.715/0.725 at r=1/2/3 m, false-credit 14.8/31.3/49.3 %, C alone 0.108/0.828/0.792, C+abc
0.010/0.066, benign C+abcg 0.701 vs 0.711). Confirmed the static-vs-dynamic actor-position deviation is
stated everywhere H62 is quoted (13/60/65v2/48/66/FACTS — none claims the static call produced the headline
numbers). Verdict unchanged: partially met. Added `docs/research/figures/fig_h62.png` (copied from the
`out/` figure) and referenced it from 32 §H62 and `docs/13`. Proposed a code follow-up (`alarms.score`
should optionally accept a time-varying `actor_pos`, not implemented) and a condensed principle-4 sentence
for a human to apply to CLAUDE.md (neither edit made by this audit, per scope). 96/100.

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| W1 | `66`'s H62 status note described the mode without a static/dynamic caveat | added a code follow-up note distinguishing the eval script's dynamic per-alarm reference from `alarms.score`'s own static `actor_pos` | AUDIT_H62 §2–3 | 66 | -- | supporting |
| W2 | 32 §H62's proposed principle-4 wording had no condensed form for a CLAUDE.md-style edit | recommended a ~45-word condensed sentence preserving every number claim | AUDIT_H62 §4 | AUDIT_H62 (not applied to CLAUDE.md) | -- | supporting |
| W3 | `docs/13`'s H62 row had no figure reference | added `fig_h62.png` line to the figure list; figure copied into `docs/research/figures/` | AUDIT_H62 §5 | 13, 32 | -- | cosmetic |

**Counts (§1–§19, 187 rows):** headline 44 · supporting 99 · cosmetic 44.

## 20. H37 forensic-search recall audit (2026-09-27, AUDIT_H37)

`AUDIT_H37.md` recomputed every number in `32` §H37 directly from `out/experiments/h37_forensic_mock/results.json`
— all match exactly. Found and fixed one imprecise claim propagated through six docs: "the abandon condition
(CI includes 0 at both noise levels) triggers" is true only at 10 % attribute noise (CI [−0.033, +0.009]); at
zero noise the CI [+0.0001, +0.0008] technically excludes zero (a mechanical floor — pooled is a strict
superset of epoch's candidate set per query, so the diff can never be negative). The **not-met** verdict is
unaffected — the diff is two orders of magnitude below the pre-registered 0.15 bar at both noise levels
regardless of CI framing. Added the missing mechanism explanation: relevant-set sizes over the 1,363 scored
queries have mean 2.67, median 2.0, max 9 — every one ≤ 10 — so recall@10 is a ceiling metric for this
design by construction (137/1,500 queries had an empty relevant set and were dropped, confirmed by direct
recomputation). The pooling trap itself is confirmed real at unit-test level; it just cannot register as a
population recall@10 gap at this identity:attribute-vocabulary ratio. Filed **H37b** (`66`, not run):
recall@1/MRR or a larger identity pool, plus the CLIP arms once renders exist. Corrected six stale "H37 has
no number" / "pre-registered, not run" mentions (`60` #11, `65` v2 §2/§4/§10, `78` ReconSphere block + don't-claim
line, `79` Q2 hedge/critique/whiteboard-quote) to state the mock-slice result while keeping the CLIP-arm
caveat. 100/100.

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| X1 | `32` §H37 rounded diffs to "+0.000" and stated the abandon condition flatly for both noise levels | exact diffs +0.0004/−0.0118; abandon-condition wording holds only at 10 % noise, magnitude bar fails at both | AUDIT_H37 §1, §4 F1 | 32 | -- | headline |
| X2 | No doc stated the relevant-set-size distribution or why the reason the trap doesn't register at recall@10 | added mean 2.67/median 2.0/max 9 histogram and the ceiling-effect mechanism; explains the 137 unscored queries | AUDIT_H37 §1, §3 | 32 | -- | headline |
| X3 | `66` §H37 status + summary row repeated the imprecise abandon-condition framing, no follow-up hypothesis | corrected framing; added **H37b** (recall@1/MRR or larger identity pool, CLIP arms) | AUDIT_H37 §4 F3–F4 | 66 | -- | headline |
| X4 | `FACTS_VERIFIED.md` H37 row used rounded diffs and the same imprecise sentence | corrected to 4-dp diffs; added relevant-set-size finding and H37b reference | AUDIT_H37 §4 F5 | FACTS_VERIFIED | -- | supporting |
| X5 | `72` §3 prose gave the diffs with no explanation of the null population result | added ceiling-effect explanation; "design-level claim stands, expectation about a recall@10 win does not" | AUDIT_H37 §4 F6 | 72 | -- | supporting |
| X6 | `60`/`65` v2/`78`/`79` (6 locations) still said H37 "has no number" / "is pre-registered, not run" after the mock slice ran | corrected to "mock slice ran, not met, ceiling effect; CLIP arms still design-level" in every location | AUDIT_H37 §4 F7 | 60, 65 v2, 78, 79 | -- | headline |
| X7 | `65` v2 §4's six open gaps omitted forensic-search evaluation despite the CLIP/journey/footfall metrics remaining unrun | added a seventh gap item | AUDIT_H37 §4 F8 | 65 v2 | -- | supporting |

## §21 · AUDIT_H63 (uniformed intruder vs. corroboration mismatch)

`32` §H63 was already accurate and precise on first write (registration error correctly
attributed, caveats correctly stated); this audit's rows are fold-in placements, not
corrections.

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| Y1 | `60`'s 40-number sheet had no H63 entry | added, replacing item 14 (MOTSynth, the weakest external-only anchor) | AUDIT_H63 §4 | 60 | -- | supporting |
| Y2 | `65` v2 §6 pointed at `99` for the uniform answer's numbers without giving them inline | added the 0.027 / 0.745 [0.694, 0.794] / 96 % / 0.018 numbers to the one-liner | AUDIT_H63 §4 | 65 v2 | -- | cosmetic |
| Y3 | `78` §1.5 ([vendor product]) had no uniformed-intruder tie-in despite it being the corroboration-vs-appearance case the section argues for | added one sentence linking H63 to [vendor product]'s multi-sensor pitch | AUDIT_H63 §4 | 78 | -- | supporting |
| Y4 | `66`'s H63 backlog entry had no realism/error-rate follow-up filed | added **H63b** (rostered-hours realism + role-classifier error sweep), not registered | AUDIT_H63 §4 | 66 | -- | supporting |

**Counts (§1–§21, 200 rows):** headline 50 · supporting 105 · cosmetic 45. (Recounted by AUDIT_FINAL_CONSISTENCY from the table rows; an earlier pass stated 198 / 47 / 46.)

## §22 · AUDIT_DEMO_REEL_V2 (v2 reel captions and doc text, 2026-09-28)

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| Z1 | reel: w=8 held-out ΔAssA +0.0479 MOT20-02; guard card cites H53/H54 99 % / 0.685 / "clothing does nothing" (H47); tuning card "θ per camera/zone"; detector and operator unlabelled | w=8 held-out +0.0570 (day), shipped w=1; uniform answer is H63 0.027 → 0.745; 0.685 needs GT-ids/H59 qualifier; shipped θ policy pooled (H42); detector trained on MOT20-01 (NC); operator invented (H22) | AUDIT_DEMO_REEL_V2 (21 rows: 6 FIX, 2 UNLABELLED) | README_v2, 96, INDEX (text); mp4 captions owed by reel owner | -- | headline |
| Z2 | H63b: pre-reg predates results; b's 0.040 drop is "the base detector's"; naive 0.028 → 0.249 "works by accident"; sticky +0.001 "(31 hits)"; (4) grace > sticky, live best; body/pos within 0.006 | pre-reg and results in one commit (be425c0), precedence unevidenced; C is role-dependent — with per-alarm role b drops 0.007, naive stays 0.027 (role-caching artefact); drop gap 0.0007 ≈ 2 hits; nesting b ⊇ g ⊇ s makes (4) true by construction for any grace; C gap 0.007; 3-seed rerun reproduces (b drop 0.049, not met) | AUDIT_H63B | 32, FACTS | R64 | major |
| Z3 | H66: decision met; coincidence escalation restores FIFO recall 0.486 → 0.689 at k = 16 at 0 s hard-negative cost | recovery needs a bulk-ack exemption added after pre-reg (without: 0.538, (2) fails → not met); escalation oracle-clean in recall worlds; 0 s added delay structural; ranked uses stand-in scores; Holm p at bootstrap floor; 100 × 3 rerun reproduces direction | AUDIT_H66 | 32, FACTS | R65 | major |
| Z4 | 101/102 mocks: "every number is in FACTS"; 101 Q4 H26/H51 equal-step gain quoted for the batch_v7 `mix_300_s0` checkpoint; 102 P13 "n.s., H26" vs 101 Q4 "Holm-significant (H51)"; 102 P7 "label-agnostic 0.83"; 101 Q18 / 102 closing uniform-rule numbers without GT-role / role-redraw qualifier; 102 P1 realised 0.618 without "ranked" | θ 0.9618 lives in 65 v2 §0 (FACTS has H33c range 0.9599–0.9628); H26/H51 arms are batch_v8; n.s. at 5 seeds (H26), Holm-significant at 10 (H51); no 0.83 in FACTS — H62 position/time 0.715 at 2 m with 31.3 % false-credit; 0.745 is GT-role keyed, tracker-keyed loss 0.007 needs AUDIT_H63B role-redraw qualifier | AUDIT_MOCKS_101_102 | 101, 102 | -- | supporting |
| Z5 | H64: "a single PTZ is a ~16 % duty-cycle sensor"; timed intruder never caught under either tour; recon at N = 3 flagged 0.000; dwell rule vs commuter wait | 0.162 = 0.775 × 27.5/132 identity (duty cycle 0.152); both timed zeros by construction of registered geometry (labelled in 32/FACTS); fixed recon 0 by construction (≤ 412 s < tau), random 0.05–0.10; tau plug-in on declared LogNormal, not H33 conformal nor engine commute_wait; naive arm fair (uniform phase); E_random depends on random-dwell floor (> 10 s ⇒ 0); 500 × 3 rerun reproduces NOT met | AUDIT_H64 | 32, FACTS | R66 | supporting |
| Z6 | 103: "+0.0479 held-out" paired with "ΔIDSW +15.80 at w=8"; "a design choice holds on real footage / proven on one real site"; "does not help association (H17)"; StrongSORT/BoT-SORT [LIT] without URL; "−0.47 to −0.84" | +0.0479 is w=16 (day → MOT20-02), IDSW +33.4 at w=16; +0.0570 is w=8 (MOT20-02 → day); shipped w=1; one sequence, 5 checkpoints; H17 pre-parity n.s.; [LIT] URLs from FACTS; −0.470 to −0.835 | AUDIT_103 | 103 | -- | supporting |
| Z7 | reel segments 10–19: H46b in-sample argmaxes (+0.0613 / +0.0486) as the result; H33c "ship point" / "shipped … conformal threshold" beside H42 "pooled SHIPPED"; "most common night false alarm is wildlife"; pooled θ "same rate every time"; tamper look not said to be post in VO; 19 unlabelled "8 of ∞" | in-sample argmax (held-out w=8 → day +0.0570); pooled θ (H42) is the shipped selection policy, H33c is the certified point; wildlife = all noise-free naive FA in simulated worlds only (H40b); pooled rate equal by construction (AUDIT_H42); tamper looks emulated in post | segment frames + ffprobe, FACTS H46b/H33c/H42/H40b | INDEX 10/19, README_v2 VO 10/11/13/14/16/17/18; captions owed to director (AUDIT_DEMO_REEL_V2 §Segments 10–19) | — | medium |
| Z8 | H70: "recall is detector-limited"; D3 drift noticed 1.0 vs pooled 0.133; "per-site governance, not recall" takeaway | detector-limited by construction (one score model); D3 easy by design (×2 caught 0.97, ×1.5 0.32 [derived]); 0.133 is estate-total monitor granularity, not pooled θ; σ_δ matched to interim H69 in a different unit; worst 1.622 = 3.2 B consistent; operator = H22 minus fatigue; 10 × 3 rerun: NOT met every seed, D2 passes on 1 of 3 | AUDIT_H70 | 32, FACTS | R67 | supporting |
| Z9 | H69: per-site recall 0.00–0.97 read as detector failure "with visible, usable targets"; FA budget 3600 /cam-h; frame-bootstrap CIs on 30 correlated frames; constant 4.5 m camera height; interview sentence "same detector ranges from 0 to 0.97" | 05 = 8 right-edge sliver rows, 09/17 = people behind fence railings (GT vis misses railings); 3600 is tighter than the docs/13 conf 0.25 FP rate (6150), H69b fraction 0.415–0.535 at every budget, < 1200 unresolvable at 30 frames; block bootstrap SD 0.354 [0.209, 0.433], hard negative still fails 12/16; height hard-coded in tools/infinite_sites.py (design); site 21 gated after the run, unpinned re-scan gives N = 17 | AUDIT_H69 | 32, FACTS | R68 | headline |
| Z10 | H70b: "C1 met" (CUSUM ×1.5 0.996 at 0.020 false flags/site-week); C2 pooled-θ cost −0.147; "hour-of-day baseline fixes it"; "CUSUM halves delay" | C1 marginal: false-flag CI straddles 0.02, σ_δ 0.15 re-run 0.0206 fails; h not fitted on test data; C2 set by σ_δ (−0.034 at 0.15 passes, −0.384 at 0.6); hour-of-day CUSUM pre-registered but 0.032 still above bar; delay halves at ×1.5, more at ×2/×3, not at ×1.25; analytic curve correct; H70 "×2 or more" is one-check scope | AUDIT_H70B | 32, FACTS, 65 v2 | R69 | headline |
| Z11 | Demo segments 20–25, 28: on-screen captions, INDEX rows, README_v2 VO checked against FACTS and R65–R69 | every number in FACTS; R65/R66/R67 qualifiers present on screen; no H69/H70b claim shown; VO 20 lacked the as-registered 0.538 and the simulated/invented-operator label (fixed); 3 cosmetic caption items owed | AUDIT_DEMO_REEL_V2 (Segments 20–28) | demo README_v2, AUDIT_DEMO_REEL_V2 | R65 | demo |
| Z12 | H71: "D1 NOT met — renders do not rank configs like MOT20"; "match_iou and max_lost flip"; "10 day sequences"; MOT20-01 in real scoring | Inconclusive: MOT20 split-half ρ ≈ +0.02 (no stable real order), spread 0.0174; MOT20-01 is the detector's training sequence (without it ρ −0.2222, same reading); max_lost does not flip without it; 12 render seqs; w > 0 helps on both, level differs (HOTA/grid-averaged vs H46b AssA) — R70, R71, AUDIT_H71 | still unverified: any real ordering (needs more real sequences) |
| Z13 | H3b: "decision met; H3 holds on CC0"; "tiling (≈1.8× upscale) does not carry over"; far "all" recall incl. 13–20 px; 10-frame blocks | Holds, with qualifiers: 65 % of far GT is < 20 px (not usably visible) — on ≥ 20 px rows D1–D3 still hold (Δ +0.431 / +0.341); H3b tiles are 0.91× native (downscaled) vs H3 2.0×, so "tiled < 1280" is about the arm; 30-frame blocks change no decision; HN failure honestly reported; latency unstable (re-run 15.5 / 16.9 / 55.4 ms) — R72, AUDIT_H3B | still unverified: 320×240 tiling on CC0 (H3 arm), degraded-stream cause |

## §23 · AUDIT_LEAKAGE (train/tune vs score overlap on real footage, 2026-09-28)

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| Z14 | real-footage numbers are scored on data no model or threshold saw; realism 6/14 "on 60 real street frames"; H32a hold-out independent of the tune set | 11 CLEAN / 6 OVERLAP / 1 UNKNOWN (AUDIT_LEAKAGE §2). Detector training = MOT20-01 1–60 only; all detection/association headlines on MOT20-02 (different view) are clean. H71 re-scored on MOT20-01 61–300: ρ −0.0200 [−0.4136, +0.4670], MOT20-01 HOTA Δ −0.0010, still inconclusive. H46b +0.0486 in-sample (held-out +0.0479). H32a hold-out = one LLVIP scene sharing 3 tune frames (leak favours the fit; still fails). Realism 6/14 is in-sample on the tuning camera's UE renders | cached `out/experiments/h71/dets,emb`; configs `h14b`, `h38`, `h43_qat`, `h32_night_profiles`; `degrade.py` L727–742 | FACTS (H71, H46, H46b, H32a, realism rows), 65 v2 §0 item 21, 103 §2 | R73 | supporting |

## §24 · AUDIT_H3C (H3's exact tiling arm on CC0, 2026-09-28)

| # | claimed | true | evidence | fixed in | R-id | severity |
|---|---|---|---|---|---|---|
| Z15 | H3c: decision met; near HN passes (AP50 drop 0.043); "tiling is not a far-field-only effect"; "~7× latency" | runner/config frozen and unchanged; decision holds on a 198-frame re-run (+0.155 [+0.048, +0.289]); far precision 0.769 / 0.815 / 0.723 (no double counting); near FP 36 → 300 for 2.0× (precision 0.931 → 0.625) and subset near AP50 drop 0.087 (HN marginal, fails on subset); re-time 6.3× on a busy GPU (idle untestable) → "6–7×" | AUDIT_H3C, re-run of `far_field_h3c` with `max_frames_per_stream: 22` | 32 §H3c, FACTS, 65 v2 §0 item 21, 103 §2 | — | supporting |

| Z16 | Fence-visibility fix (BUG_gt_visibility_fences) might move existing GT numbers (batch_v8 recall 0.696, H51/H52, showcase alarm counts) | post-hoc `correct_rows` on every fixed camera: batch_v8 0 / 42,581 rows with static cover (delta 0); showcase 498 / 2,176 covered, 4 cross 0.5, 1 intrusion event loses 4 / 92 frames, alarm rules use world tracks; sites 325 / 5,569 cross (site 09 62 / 80). No quoted number moves; PTZ cams unchecked | `AUDIT_GT_FENCE_VISIBILITY.md`, `out/gt_static_occ/all_summary.json` | this audit | — | none |
| Z17 | Z16 left every PTZ camera unchecked (fence cover projected through the configured, not live, pose) | `live_static` uses per-frame camera_status pose; showcase dusk/night cam_ptz: static_cover changes on 175 / 502 rows, static-labelled 19 -> 8, vis-0.5 crossings 3 -> 0, 0 pose_unknown frames; batch_v8/sites PTZ not re-run | `AUDIT_GT_FENCE_VISIBILITY.md` "PTZ", `out/gt_static_occ/ptz_summary.json`, `tests/test_gt_static_occlusion_ptz.py` | BUG_gt_visibility_fences | — | none |
| Z18 | Mocks 102/105 written before R68–R73, H3c and the fence-GT fix | 8 fixes (105 Q3 w=16/w=8 conflation, unverified ledger counts, 68/65 retirement counts, railings 'need modelling', H70b marginal); 105 Part 7 Q21–Q26 added | `AUDIT_MOCKS_102_105_R2.md` | 102, 105 |
| Z19 | H3d decision (cap re-base? AP50 rise? robustness) | cap 292 was registered (not a re-base); runner unchanged; pass is conf-0.25 pooled point only (far CI low 0.521; conf 0.4 far 0.592 all arms; degraded far 0.295); (b) fails cap at 0.4, (d) holds; AP50 rise = 640 large-person + tile small-person recall. Nothing retired; 65 v2 / 103 H3c eight-fold sentences qualified | `AUDIT_H3D.md` | 32, FACTS, 65 v2, 103 | — | none |
| Z20 | H3e (block slip? 0.383 labelled? "sparse scenes only" a density rule? MOT20-01? AP50 vs H3c/H71? HN reason?) | order/freeze clean; 12 blocks computed by frozen code, no CI change; 0.383 reproduces, labelled post-hoc; MOT20-01 excluded; AP50 statement MOT20-only (renders: tiles beat 1280); HN passes for the wrong reason (now labelled in FACTS); density check: (d)−(a) −0.079 in sparsest quartile, within-sequence quartiles flat → not a measured density rule, gate threshold unmeasured. R74 retires unscoped "(d) costs no recall"; one far-field paragraph (H3b→H3e) replaces piecemeal lines | `AUDIT_H3E.md` | 32, FACTS, RETIRED, 65 v2, 103, 105, pocket | R74 | medium |
| Z21 | 106 compute/cost model (numbers vs FACTS, assumptions declared, arithmetic, A11 INT8, H70 R67 caveat) | 8 fixes: H56 0.367→0.369, estate ~94→~93, 10 s clip declared A12, A11 says H38/H43 measured AP not speed, H45c ≥2-op misreading (x2), probe 6 R67 qualifier, ~30 operators labelled a staffing choice; arithmetic otherwise reproduces | `AUDIT_106.md` | 106 |
| Z22 | H3f (post-hoc frames_every/groups_subset? LOO vs AOI? primary arm? resample? HN reach) | half the registered frames (other half's ablation dets absent, shares not recomputable; 100-frame loss 0.583 vs 0.600, stable); noise LOO CI crosses 0.60; NOT met correctly scored on tiles_d; 'noise is what erases far people' corrected to interaction (R75); resample labelled by construction; degraded-stream numbers qualified as lower bounds (H3b, H3d, H32b rows; 65 item 21) | `AUDIT_H3F.md` | 32, FACTS, 65 |
| Z23 | Cross-doc consistency of the day-of set (README, 65 §0, 101–110, 93, drills, pocket, pack): "ledger 219 (47 headline in the first 198)"; 65 §0 skips item 22; "73 retired" in 101/102/105/108; 107 "39 segment files", pack "21 pp" | recount 200 rows in §1–§21 (50 headline) + Z1–Z23 = 223; 65 §0 renumbered 23→22 and every pointer fixed; 75 retired everywhere (R75 = AUDIT_H3F); 41 segments done; pack 22 pp; 13 verbatim sentences match; 0 broken paths | `AUDIT_FINAL_CONSISTENCY.md` | 65 v2, 101, 102, 104, 105, 107, 108, 110, README, LEDGER counts, pack + pocket | — | cosmetic |
| Z24 | Demo segments 19b, 36–41 (+04/09 re-check): on-screen captions, INDEX rows, README_v2 VO against FACTS and R72–R75 | every number in FACTS or labelled clip-only; 04/09 final on-screen counts match INDEX (484/230/2 of 1,091; 5/620/590 of 1,632); 19b end card "14 site types" vs 36 "13" (generator vs gate-passing, INDEX note added, caption owed); VO 38 implied a density gate (R74, fixed); VO 41 did not say track = GT, fence simulated, operator mocked (fixed); 38 title far-recall line lacks "sparse CC0" (caption owed) | `AUDIT_DEMO_REEL_V2.md` | INDEX, README_v2 | 19b end card, 38 title card (director) | cosmetic |
| Z25 | H3g (ratio vs texture? in-sample fit? 50 frames? unreachable HN? H32 pattern?) | ratio 1.47 is estimator-referred on different scenes (s = 0 floor 0.119), labelled not a pure sensor ratio; s fitted in-sample on the 12 HN frames; far comparison paired on H3f's scored 50 frames (half H3f's registered 100); joint HN unreachable (real 4/12) → uninformative as registered, 1/12 vs 4/12 post-hoc; 'H32 pattern' reworded to coupling (R76); 65 item 21 and 103 §2 one line each | `AUDIT_H3G.md` | 32, FACTS, RETIRED, 65 v2, 103 | R76 | medium |
| Z26 | Guard rails: do R64–R76 patterns catch unqualified phrasings; does the numbers test cover the day-of set? | exemption column was never consulted (fixed for R64+); 12 of 13 rows missed ≥ 1 of 2 plausible bad sentences, tightened (all 28 now caught, 14 qualified pass); new R77 (far cameras "blind" unqualified), 106 row qualified; numbers test adds 93, 101–104, drills READMEs (17 allowlisted) | AUDIT_GUARD_RAILS |
| Z27 | H32c (runner frozen? 2.21× denominator/estimator? noise matched? recall collapse real? luma by construction?) | runner/config/test identical 361bb5c→c7d073a; 2.21× vs hold-out as registered, 1.57× vs tuning-15, not texture-floor (s = 0 floor 0.0056) but estimator-referred; matched arm only partially matched (1.45× hold-out); frames checked: people visible in raw, dark blobs after profile → profile broken for detection, not a pessimistic outlier; luma 0.64 vs 0.59 labelled by construction | `AUDIT_H32C.md` | 32, FACTS, RETIRED, 65 v2, 103 | R78 | high |
| Z28 | Director row 44: showcase_all_night static_occlusion vis_old 0.00 on visibly unoccluded people | [V] not night, not the mask, not PTZ keying, not the audit script: MOT col 9 was the mock painter's visible_frac (fence = opaque L x L box); 456/459 cam_01 zero rows had mask pixels, 4/5 crops show the person unoccluded (5th behind fence, render vis 0.999); dusk identical. Fix: col 9 from render visibility. v2: 1568/2176 rows change, 625 zero->positive; H32c GT 362 -> 449 | `docs/BUG_night_visibility_zero.md` | 32 §H32c, FACTS H32c, docs/11 | — | medium |
| Z29 | Which FACTS render sets carry the mock painter's MOT column 9, and does any number move? | [V] all: showcase dusk/night (684 zero rows with mask pixels), batch_v8 x 9 (849–4,067 rows/set differ from render vis), sites/sites_v2 (no ID mask, not re-derivable). Only H32c filtered on vis: re-scored on 449 GT, raw 0.890 → 0.766 [0.667, 0.850] (outside CI, R79), shipped/matched/decision unchanged. H3b–H3d, H69 headline unaffected (all rows). Double-count fix: correct_rows skips (1 − cover) for depth-tested masks | `AUDIT_GT_FENCE_VISIBILITY.md`, `docs/BUG_night_visibility_zero.md` | 32, FACTS, RETIRED, 65 v2, 103, 105, 107, 108, 110–112 | R79 | medium |
| Z30 | H32d (runner frozen? redundancy measured? ≤ 6 % robust? 2× upsample? 449-row GT? 3× vs 2.21×?) | [V] runner/config identical 1713d6c→21cea36, re-run reproduces every block; pair noise+codec LOO 0.978, AOI 0.959 (redundant, post hoc); minor stages upper CI to 0.097 ("innocent" retired, R80); upsample by design, codec wording qualified; 449-row GT moves shares ≤ 0.02; 3.3× is noise-only arm, shipped 2.21× | `AUDIT_H32D.md` | 32, FACTS, RETIRED, 65 v2, 103, 105, 112 | R80 | low |
| Z31 | Demo segments 44, 48–50: every number vs FACTS/112/R75–R80 | [V] no retired claim on screen; 5 FIX: seg48 redundancy needs 'post hoc', codec needs 2×-upsample qualifier, 'not re-run' hides the 449 share re-score; seg50 counts sourced from AUDIT_GT_FENCE_VISIBILITY; README_v2 're-ran' → 're-scored'. INDEX/README_v2 fixed; 3 caption strings owed (AUDIT_DEMO_REEL_V2 §Segments 44, 48–50) |
| Z32 | 101 Part 3 (segs 19b, 36–50): numbers vs FACTS/112/113, overclaims, fallback ids | [V] fallback ids all right; tile rule 'not shipped', night on 449 GT, console mock-up all correct; 8 FIX: Q4 depth-tested mask overclaimed as general + batch_v8 'no rows change', Q1 13 vs 7 shown, Q2, Q7 sparsest quartile post hoc, Q11 real-run stages explicit, sources for 1,994/62-of-80, stale reel times in the 3-min pick; 104/107 pick synced (AUDIT_101_PART3) |
| Z33 | 2026-09-28 final consistency R2: reel 1194.5 s/44 seg (rebuild pending), 3-minute timestamps in 101, ledger 233, H32e results sentence in 65/103/105/107/112/104; 14 fixes (AUDIT_FINAL_CONSISTENCY_R2) | fixed |
