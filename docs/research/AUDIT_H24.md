# AUDIT_H24 · ReID appearance in ByteTrack association (32 §H24)

Audited 2026-09-27 against `4095a4c` (pre-registration, 07:09) and `2fdecd6` (results, 09:01;
code, 32 results, FACTS, 66, 13). Method as AUDIT_H42: every number recomputed in Python from
`out/experiments/h24_reid_assoc/results.json` — per-sequence × checkpoint `scores`, averaged
independently of the runner, then checked against `analysis` — and method claims checked against
`survsim/experiments/reid_assoc.py` and `survsim/baselines/bytetrack.py` (`app_weight` path).

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| MOT20-02 ByteTrack AssA 0.5060 / HOTA 0.5268 / IDSW 92.6 | mean of 5 checkpoints: 0.5060 / 0.5268 / 92.6 | match |
| OSNet-ImageNet ΔAssA +0.0139 [+0.0018, +0.0268] | 0.5199 − 0.5060; per ckpt +0.015, −0.0049, +0.0186, +0.039, +0.0019 | match |
| ΔHOTA +0.0085, ΔIDSW −5.6 | +0.0085; −11, −3, 0, −15, +1 → −5.6 | match |
| HSV ΔAssA +0.0163; OSNet-H20 +0.0154 | 0.5224 − 0.5060; 0.5214 − 0.5060 | match |
| "CI > 0 in all three" MOT20 arms | percentile bootstrap over **5 checkpoints**; exact sign-flip p 0.1875 / 0.125 / 0.0625 (floor) | **qualified** — no arm significant at 0.05 by the exact test; stated in 32/66/73/48 |
| batch_v8 ByteTrack AssA 0.5197 / HOTA 0.4831 | COMBINED means 0.5197 / 0.4831 | match — but the registered ΔAssA is per-sequence mean (baseline 0.4248 → 0.4442); table basis now stated | minor |
| OSNet ΔAssA +0.0194 [+0.0004, +0.0439]; bar +0.02 missed by 0.0006 | per-seq mean 0.4442 − 0.4248 = 0.0194; `two_way_boot` (12 seq × 5 ckpt, 10 000, seed 0) | match |
| ΔHOTA +0.0125, ΔIDSW −0.98 / seq | +0.0125 [+0.0009, +0.0297]; −0.9833 | match |
| HSV and H20 batch_v8 CIs span 0 | HSV +0.0123 [−0.0054, +0.0395]; H20 (held-out disguise, 4 seq) +0.0147 [−0.0044, +0.0568] | match |
| street_crowd_day +0.0267 | `assa_mean_dense` +0.0267 [+0.0055, +0.0600] | match |
| GT-box arm +0.0137 "keeps most of the gain → association" | +0.0137 [−0.0011, +0.0312] | **qualified** — point estimate supports it, CI spans 0; stated |
| "DetA moves ≤ 0.003" | OSNet α-mean ΔDetA +0.0025 MOT20 / +0.0017 batch; at α 0.5 +0.0048 / +0.0040; HSV MOT20 α-mean +0.0051 | **imprecise** → scoped to OSNet α-mean in 32 |
| pooled COMBINED +0.0338 [+0.0251, +0.0431] labelled exploratory | `assa_mean_combined`; 32 says "not the pre-registered statistic" | match |
| verdict uses the registered statistic | `analyse()` decision: `batch_v8.assa_mean` ≥ 0.02 and lo > 0; MOT20 lo ≥ −0.005 → met = false all arms | match |
| TrackEval-bridge scoring | `trackeval_score` → `trackeval_bridge.run_trackeval` for every arm | match |
| Deviation: H20 retrain hit 300 s cap at 8/12 epochs | `weights/osnet_h20_s0.json`: `epochs_run` 8, 333.8 s (epoch 7 began at 296.5 s) | match |
| Deviation: w = 1 untuned | config `app_weight` 1.0 for every embedding; registered as a confound | match |
| Deviation: no night arm | 73 §6 recommended one; config runs day only; 32 results never said it was dropped | **imprecise** (omission) → stated in 32 audit para, 73 §6 status, H46 |
| Pre-reg clarification "after commit (before any run)" | clarification text first appears in `2fdecd6` (09:01), after `results.json` (08:57); the code also first committed there | **qualified** — "before any run" unverifiable from git; the registered "IoU ≥ 0.2 … never create a match IoU forbids" already implies solve-then-filter, so the test is unchanged |
| FACTS "Appearance never lowered AssA" | arm means never negative; per checkpoint OSNet s1 −0.0049, HSV s4 −0.0032 on MOT20-02 | **wrong** as worded → "never lowered mean AssA" (FACTS; R49) |
| H20 arm leakage handled | `arm_sequences.osnet_h20.batch_v8 = [disguise_and_tamper_day]` in the decision statistic | match |
| wall 6,338 s | `wall_seconds_this_invocation` 6338.4 | match |

## 2. Corpus fold-in

73's "synthetic helps tracking only through detection" (§0 line 4, §3.1, Q1) was written before
H24 and read as a general claim about tracking. H24 separates two things: synthetic *data* helped
only via DetA (H17), but an appearance *model* helps association on real MOT20-02 too (~+0.015
AssA, fewer ID switches; GT-box arm shows it is association). Revised in 73 (§0 note, §3.1
correction, §6 status); written into 64 (register row + §4 paragraph), 52 (register row), 60 #37
and never-say #6, 48 (C8h + #41d), 65 (N4b), 23 M3 (reference tracker = ByteTrack + ImageNet
OSNet, w untuned), 79 (intro, Q24, weak-answer #2 — were "no result yet"), FACTS (row fixed + audit
row + data-vs-model row; count 318 → 320), 66 (H24 audit + decision, H46 w-sweep + night arm),
RETIRED_CLAIMS R49, 00 index.

## 3. Score

22 claims checked: 15 match, 1 minor (batch_v8 table is COMBINED, verdict is per-sequence),
3 qualified (MOT20 "CI > 0" on n = 5 with sign-flip p ≥ 0.0625; GT-box CI spans 0; clarification
timing unverifiable), 2 imprecise (DetA ≤ 0.003 scope; night arm silently dropped), 1 wrong
("never lowered AssA"). Scoring match 1, minor/qualified/imprecise ½, wrong 0: **Score 18 / 22
(82 %)**. Every number recomputes; the verdict (not met, by 0.0006) is correct and the pooled
statistic is correctly kept out of it. The defects are in how strongly the MOT20 rise and the
GT-box arm were worded, and in one undisclosed omission.
