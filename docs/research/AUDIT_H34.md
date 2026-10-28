# AUDIT_H34 · Label-free drift monitor (32 §H34)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** the FACTS count 282 quoted in Propagated is stale — 324 (AUDIT_79, AUDIT_NARRATIVE_POST_H26).

Audited 2026-09-27 against `cf33bb2` / `61194d2` (32 as committed; 71 not touched — another agent
is editing it). Method as AUDIT_H25: every number in 32's H34 pre-registration and results, and in
68 Q14, recomputed in Python from `out/experiments/h34_drift_monitor/results.json` (`arms`,
`thresholds`, `recall`, `recall_drop`, `correlation`, `verdict`, `config`); method claims checked
against `survsim/experiments/drift_monitor.py` and `spearman` / `rule_of_three` in
`survsim/experiments/inference.py`; `figures/fig_h34.png` inspected.

## 1. Recomputed

| # | claim (32 / 68) | recomputed | result |
|---|---|---|---|
| 1 | PSI (3 thresholds) and KS fire on 100 % of null evaluations | 2,988 / 2,988 each; 216/216 independent windows | match |
| 2 | 1,440 FA / 24 cam-h | `fa_rate_per_eval` 1.0 × `evals_per_24h` 1,440 — valid only at **one evaluation per minute**; stated in the pre-registration but not in the results table, verdict or 68 Q14 | **imprecise** → cadence stated in all three (the run itself evaluates 12.5/s = 1.08 M/24 cam-h) |
| 3 | z_cal 14 / 2,196 → 9.2 | 14/2,196 × 1,440 = 9.18 | match |
| 4 | z_cal delays dusk 3/1/0, dirt 2-3 7/3, codec 3 11 samples | medians over detecting cams identical | match |
| 5 | misses blur ×3, codec 1-2, dirt 1 | detected_cams 0,0,0 / 4,4 / 0 (< 5 of 9) | match; codec 1-2 near-miss (4/9) **added** |
| 6 | emb 0 null fires, ro3 upper 26.6 | 0/2,196; −ln 0.05 / 162 × 1,440 = 26.63 | match |
| 7 | emb 0/12 detected | `conditions_detected` 0 | match |
| 8 | ρ PSI 0.49 [−0.15, 0.84] p 0.11; KS −0.13 [−0.68, 0.46] p 0.69; z_cal 0.61 [−0.08, 0.98] p 0.04; emb 0.61 [0.07, 0.91] p 0.04; n = 12 | same to 2 d.p. (0.4895, −0.1329, 0.6084, 0.6084) | match |
| 9 | "Bootstrap CI + permutation p" | percentile bootstrap, condition pairs resampled, 4,000 draws; two-sided rank permutation, 10,000 | **imprecise** → method stated under the table and in FACTS |
| 10 | verdict INCONCLUSIVE | per-arm (a)/(b)/(c) flags re-derived; no arm passes all; REFUTED excluded (emb passes b, z_cal/emb pass c) | match |
| 11 | deviations: z_cal extra arm; disguise_and_tamper_day cams → cam_gate/sub/yard | config `cams` map as stated; PTZ excluded | match |
| 12 | 9 cams, 12 conditions, window 13 ≈ 1 s, reference = samples 0..49 | 13/12.5 = 1.04 s; 50/12.5 = 4 s | match |
| 13 | recall clean 0.492 and 12 condition values | all match (61/124 … 45/124) | match; n_gt 124 (one box = 0.008) **added** |
| 14 | "162 independent null windows" | 162 for z_cal/emb (seed-1 + pre-shift), 216 for PSI/KS | **imprecise** → both stated |
| 15 | certifying needs ≥ 4,320 windows | zero-event rule of three: −ln 0.05 × 1,440 = 4,314 (3 × 1,440 = 4,320 is the approximation) | **imprecise** → 4,314 |
| 16 | "emb threshold sits above every post-shift window mean" | threshold 5.40 > every condition's mean score (max 4.10), but single windows crossed it on 1–2 cams (dusk 3, codec 2-3, dirt 2-3) | **wrong as worded** → corrected in place |
| 17 | "codec shift moves the statistics most while costing the least recall" | z_cal post-shift means: dusk 121/303/790, dirt 3 111 ≫ codec 27/49/65; blur (13–15, recall cost up to 0.43) is the main rank breaker | **wrong** → corrected in place |
| 18 | 68: "AE drift and people walking through the frame are enough to trip them" | pre-registered mechanism is sampling bias (E[PSI] ≈ 0.87 > 0.25); the figure shows null PSI ≈ 5–6, so both act | **incomplete** → both stated |
| 19 | 68: embedding "gave none"; "Spearman 0.61" | no certifiable bound or CI given; z_cal CI crosses 0 | **imprecise** → ≤ 26.6 and both CIs added |
| 20 | 68: z_cal caught dusk and dirt "within about 0.6 s" | max 7 samples / 12.5 = 0.56 s | match |
| 21 | z_cal 9.2 as a rate | 14 fires collapse to **1 of 162** independent windows (clustered); independent rate 8.9 | **omission** → "one event, point estimate" added in 32, 68, FACTS |

## 2. Interpretation carried to the corpus

Image-statistic PSI/KS monitors are useless per camera without calibration; a calibrated
mean-shift score catches exposure/dirt/heavy compression but not blur; the embedding arm's
null-max threshold buys zero false triggers at zero sensitivity, and 162 windows cannot certify
it below 26.6/24 cam-h. Propagated as "inconclusive, no validated threshold" everywhere; the
follow-up is H44 (66): ≥ 4,314 independent stationary windows, quantile thresholds, and
detection-rate / track-length arms that should see blur.

## 3. Score

21 claims checked: 12 match, 7 imprecise/omitted (fixed or added), 2 wrong (fixed in 32 in place).
**Score 15.5 / 21 (74 %)** — every number in results.json was quoted correctly; the defects were the
unstated one-check-per-minute cadence behind 1,440, the missing CI method, and two interpretive
sentences (emb threshold, codec threat) that the per-camera data contradict.

Propagated: 32 §H34 (in place), 68 Q14 + scoring row, FACTS_VERIFIED (3 H34 rows, count 282),
52 §4.4 register + status, 64 register + "Drift without labels" paragraph, 60 #37/#39 + not-to-say
#6, 48 C8f + #46, 65 N16, 74 Drill 3 failure-mode row, 23 drift row, 66 (H34 done, H44 new),
77 weak answer #5 partially closed, 00 index.
