# AUDIT_64 · Technical report 64 (sim2real dose, realism screen, loiter alarm floor)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** the H14b/H16 (+0.0121, +0.0092/+0.0169) and H17 (HOTA +0.0103) rows 'match' their JSONs but are unequal-step (AUDIT_H26, R51–R53); H17 is also pre-parity (AUDIT_M1_PARITY).

Audited 2026-09-27 against commit `d4e5023` (report) and `bcbe9d2` (round 3),
method as AUDIT_52-53: every number recomputed from `out/experiments/*/results.json`
with a flatten-and-match script (value rounded to the quoted precision, JSON path
recorded), figures opened with PIL and inspected, citations fetched.

## 1. Numbers (spot-check: 25 claims required, 96 checked)

| group | claims checked | source paths | result |
|---|---|---|---|
| H1 (0.276, 0.152 ± 0.025, 0.491 ± 0.003, 0.472 ± 0.005, 120–160 px 0.242 → 0.009, ≥ 240 px 0.955 → 0.908) | 11 | `h1_sim2real` `seed_summary`, `ap_by_height` | all match |
| H2/H3 (0.093, 0.188, 0.281; 0.021, 0.405, 0.629, 0.209) | 7 | `h2_degradation`, `h1_sim2real` mot20_sub, `h3_farfield` | match |
| H4/H6/H8/H10b (0.219/0.148, 0.444/0.245, 0.512/0.186; 0.221 ± 0.008, 0.197; 0.478 → 0.004; 0.083 [0.015, 0.354], 0.746, 0.845, 8.5, 157) | 17 | respective JSONs | match (H8 0.935 is from 32 l.399, not the JSON) |
| H7 (+0.010/+0.011, +0.000, −0.007) | 4 | `h7_mixing` AP means minus mix_0 0.4859 | match (+0.0103, +0.0115, +0.0002, −0.0067) |
| H9 (−0.171 [−0.251, −0.086], p 0.0002, night −0.006 [−0.053, 0.033], 4/24 det-limited, pooled +0.0005 / −0.0057) | 8 | `h9_tracking` `analysis`, `pooled` | match (the ±0.0005/−0.0057 are *pooled* HOTA, not the per-sequence means +0.0004/+0.0008 — text says "pooled", correct) |
| H11 (−0.020, −0.609 [−0.710, −0.519], −0.192, −0.303) | 6 | `h11_night` | match |
| H13 (ρ −0.60 [−0.78, −0.20], p 0.005, in-band +0.10 [−0.40, 0.51]; "three sources reach zero-shot") | 8 | `h13_realism_transfer` | match (APs 0.312, 0.305, 0.288 above 0.276; 0.2757 just below) |
| H14b/H16 (+0.0121 [0.0111, 0.0130], +0.0095 [0.0084, 0.0106], p 0.0079, 0.4862 sd 0.0006; +0.0092 [0.0075, 0.0109], +0.0169 [0.0147, 0.0190], 0.459) | 14 | `contrasts.primary` | match |
| H15 (−0.0005 [−0.0012, +0.0001], p 0.31) | 4 | `contrasts.secondary[0]` | match |
| H17 (HOTA +0.0103 [+0.0008, +0.0197], DetA +0.0342 [+0.0299, +0.0397], AssA −0.0051 [−0.0257, +0.0140], MOTA +0.0326, IDF1 +0.0128 [+0.0021, +0.0227], IDSW +11 [−0.2, +19.6], per-seed diffs) | 14 | `h17_tracking_transfer` | match |
| H18 (+0.0099 [+0.0067, +0.0144], −0.0014 [−0.0045, +0.0013], −0.0303 [−0.0513, −0.0172], zero-shot 0.335/0.442/0.501) | 12 | `h18_farreal_v2` | match |
| H12 (6.01, 4.55, 20.7, 87.4, Garwood and cluster CIs, 3,002 cam-h, 74,989 people; 4,476–87,106×; 3.6–4.9 orders) | 16 | `h12_alarm_scale.fa[*]` | match |
| H58 r2/r3 (A1 2.915 [2.854, 2.977] / 0.825 [0.789, 0.862] / P 0.329; A2 3.745 / 0.831; B 3.114 / 0.842; D 2.468; ECE 0.0018 vs 0.0194; C curve 1.951 @ 0.803; D curve 1.803 @ 0.803; twin floor 1.008 [0.973, 1.045], 3,027 episodes; dwell_25 0.733 → 0.367) | 16 | `round2_results.json`, `round3_results.json` | match |

**No numeric error found.** All deviations were provenance or framing (§4).

## 2. Figures

All five PNGs load with PIL (RGBA; 1500×570, 900×600, 1800×570, 1125×720,
1200×540; pixel std 34–62, non-blank) and were inspected visually. Data checks:
Fig. 1 points equal H7 means, H14b/H16 diffs and boot95 CIs; 1b bars equal H1
seed means, whiskers ±1.96 sd (title says so; right edge of the title is
clipped — cosmetic). Fig. 2 ρ/CI/p in title match; 20 points. Fig. 3 bars
consistent with H3/H18 JSON. Fig. 4 curves match `round3_results.json.curves`
(A1 11, B 16, C 11, D 16 points; D's θ 0.999 point = 3 alarms = 0.001 FA/cam-h
at recall 0.031, which sits on the budget line — now stated in the caption).
Fig. 5 shares and FA labels match H12. **No regeneration needed.**

## 3. Citations (10 fetched from arxiv.org/abs, 2026-09-27)

2108.09518 MOTSynth · 2112.09290 PeopleSansPeople · 1804.06516 Tremblay DR ·
1710.10710 Hinterstoisser · 2203.06026 ImageNet classes in FID · 2110.06864
ByteTrack · 2003.09003 MOT20 · 1610.01983 Driving in the Matrix · 2402.02108
Synthetic-to-Real Video Person Re-ID · 2310.04416 Alice Benchmarks. **All 10
resolve to the titles cited.** Quoted figures inside those papers were not
re-verified here (they were in docs/24 and 30).

## 4. Hypothesis-table coverage and fixes applied

Table 1 covers H1–H18 plus H58 r1–r3; every verdict agrees with 32/58. H19/H20
are pre-registered only (`11f81d2`) and correctly absent. Fixes (commit `bba2265`,
+22/−12 lines):

1. H58 row and Table 2: results commits added (`070cf97`, `44e34f5`, **`bcbe9d2`**);
   the shipped-rule row previously cited only the pre-registration `cec3317`.
2. Round 3 bullet: A1's clock stated as ≥ 5 s with the 58 §7.1 erratum; A1
   replaces the round-2 retrain (A2 3.745).
3. C's selected row flagged as a declared deviation; the C 1.951 / B 2.224 curve
   points flagged as read off H12 = round-4 candidates, not results (also in §8c).
4. D: P8 (≥ 25 %) failure stated explicitly (20.7 %), and the need for a per-site
   zone profile; D row added to Table 2.
5. Round-1 recall 0.867 labelled window-only.
6. Fig. 4 caption: D's budget-touching point at recall 0.031.

## 5. Score

| criterion | before | after |
|---|---|---|
| numeric accuracy (96/96) | 10/10 | 10/10 |
| figure fidelity | 9/10 | 9.5/10 (title clip remains) |
| provenance | 7/10 | 10/10 |
| claim discipline (test-set-picked points, deviations) | 7/10 | 9.5/10 |
| citations | 10/10 | 10/10 |
| coverage vs 32/58 | 9/10 | 10/10 |
| **total** | **87/100** | **97/100** |
