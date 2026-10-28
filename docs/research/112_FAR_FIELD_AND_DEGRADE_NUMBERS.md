# 112 · Far-field and degrade numbers: one reconciliation table

*2026-09-28. Every recall / precision / latency number quoted for far-field detection and the degrade
profiles in `32` §H3–§H3g and §H32c, `FACTS_VERIFIED.md` and AUDIT_H3B/C/D/E/F/G and AUDIT_H32C, in one
table. Numbers differ because the arm, denominator, frame set, conf, stream or licence differ — not because
any is wrong. Where this file disagrees with FACTS, FACTS wins. Detector: zero-shot COCO YOLOv8n throughout;
IoU 0.5 matching.*

**Legend.** cam: far = cam_02/03 of batch_v6/v8 `street_crowd_far`; near = cam_01. Denominator: "all" = GT ≥ 13 px
(smaller = ignore); "≥ 20" = usably visible rows (principle 5); "≥ 80" = large people. Stream: raw / shipped
(`cctv_day_720p` or `cctv_night_lowlight` as shipped) / matched (noise std factor refit) / LOO / AOI (H3f
ablation variants) / pooled (all three sources: day raw, night raw, day degraded). Licence: **CC0** = batch_v8 Quaternius,
`commercial_ml_ok` (customer-safe); **MH-eng** = batch_v6 MetaHuman, engineering evidence only, never an ML
benchmark; **MOT20-m** = MOT20 non-commercial, measure only; **LLVIP-m** = LLVIP non-commercial, measure only.
Status: FACTS = stated in FACTS_VERIFIED as-is; qualified = in FACTS but must carry the qualifier named;
R-id = retired phrasing around it; by construction = true by design, not a finding. Latency is desktop RTX 2070
Max-Q shared with the Unreal editor: quote ratios, never absolutes as deployment numbers.

## 1 · The table

| # | number | CI (95 %) | exp | arm | cam | denom | frames | conf | stream | data | status | allowed sentence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.021 | – | H3 | full_640 | far | all | 594 | 0.25 | pooled | MH-eng | qualified (MH-eng) | "On MetaHuman engineering renders, far recall at 640 was 0.021." |
| 2 | 0.405 | – | H3 | full_1280 | far | all | 594 | 0.25 | pooled | MH-eng | qualified (MH-eng) | "…0.405 at 1280 (MetaHuman, engineering-only; CC0 gives 0.402)." |
| 3 | 0.629 | – | H3 | sahi_320x240 (2.0×) | far | all | 594 | 0.25 | pooled | MH-eng | qualified (MH-eng; replicated by #16) | "H3's MetaHuman 0.629 replicates on CC0 as 0.643 (all rows)." Never alone as a customer number. |
| 4 | 0.209 | – | H3 | sahi_320x240 | far | all | 198 (degraded third) | 0.25 | shipped | MH-eng | qualified (lower bound, AUDIT_H3F) | "Degraded far recall on MetaHuman renders was 0.209 — a lower bound." |
| 5 | 156.2 vs 21.4 ms (7×) | – | H3 | tiles vs 640 | far | – | 594 | – | – | MH-eng | qualified (shared GPU) | "about 7× the compute on a shared laptop GPU" |
| 6 | 0.025 | [0.016, 0.035] | H3b | full_640 | far | all | 594 | 0.25 | pooled | CC0 | FACTS; R77 phrasing | "under 3 % far recall at 640 on all rows of CC0 renders, conf 0.25" |
| 7 | 0.060 | [0.040, 0.081] | H3b | full_640 | far | ≥ 20 (20–40) | 594 | 0.25 | pooled | CC0 | FACTS | "6 % on the usably visible rows" |
| 8 | 0.007 | [0.003, 0.012] | H3b | full_640 | far | 13–20 | 594 | 0.25 | pooled | CC0 | FACTS (D1 could not fail) | Only as the D1 bin; not usably visible. |
| 9 | 0.402 | [0.329, 0.476] | H3b / H3c | full_1280 | far | all | 594 | 0.25 | pooled | CC0 | FACTS; say "all rows" | "0.402 on all rows ≥ 13 px" — never bare. |
| 10 | 0.491 | [0.378, 0.609] (H3b, 10-frame blocks); [0.311, 0.670] (H3c, 30-frame) | H3b / H3c | full_1280 | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS (primary) | "far recall at 1280 is 0.491 on ≥ 20 px CC0 rows, conf 0.25" — quote the H3c CI. |
| 11 | 0.346 | [0.279, 0.415] | H3b | tiled_2x2 704×396 (0.91× native) | far | all | 594 | 0.25 | pooled | CC0 | FACTS; R72 | "H3b's 0.91× tiles do not beat 1280 — a statement about that arm". |
| 12 | 0.401 | – | H3b | tiled_2x2 | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS | as #11 |
| 13 | +0.376 | [0.307, 0.448] | H3b | 1280 − 640 | far | all | 594 | 0.25 | pooled | CC0 | FACTS | D2 only. |
| 14 | +0.431 / +0.341 | [0.330, 0.538] / [0.249, 0.438] | H3b audit | 1280 / tiled − 640 | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS | "on usably visible rows D1–D3 hold too" |
| 15 | +0.046 | [0.026, 0.069] | H3b | tiled − 640 | near | all | 297 | 0.25 | pooled | CC0 | FACTS (HN fails) | "tiling is not a far-only effect" |
| 16 | 0.643 | – | H3c | tiles_2p0x 320×240 | far | all | 594 | 0.25 | pooled | CC0 | FACTS | "H3's 0.629 replicates on CC0: 0.643 on all rows." |
| 17 | 0.681 | [0.521, 0.830] | H3c | tiles_2p0x | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS (primary) | "2.0× tiles reach 0.681 on ≥ 20 px CC0 rows, at 6–7× the 1280 compute, near FPs up." |
| 18 | +0.190 | [+0.119, +0.265] | H3c | 2.0× − 1280 | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS | "tiles add 19 points over 1280 on CC0 renders" |
| 19 | +0.155 | [+0.048, +0.289] | H3c audit | 2.0× − 1280 | far | ≥ 20 | 198 | 0.25 | pooled | CC0 | FACTS (re-run) | Only with "on the 198-frame re-run". |
| 20 | 0.632 / +0.141 | [0.479, 0.779] / [+0.083, +0.195] | H3c | tiles_1p5x | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS (HN fails) | 1.5× arm reported, not recommended. |
| 21 | 0.043 (pass) / 0.087 (fail) | – | H3c / audit | 2.0× near AP50 drop | near | all | 297 / 198 | AP | pooled | CC0 | FACTS, "marginal" | "the near HN passes by 0.007 on the full set and fails on the audit subset" |
| 22 | 0.931 → 0.625 (FP 36 → 300) | – | H3c audit | 1280 → 2.0× near precision | near | all | 198 | 0.25 | pooled | CC0 | FACTS | "tiles with plain NMS multiply near false positives" |
| 23 | 0.769 / 0.815 / 0.723 | – | H3c audit | far precision 1280 / 2.0× / 1.5× | far | ≥ 20 | 198 | 0.25 | pooled | CC0 | FACTS | "the far gain is not NMS double counting" |
| 24 | 19.3 / 143.3 ms; 18.1 / 114.1 re-time → 6–7× | – | H3c / audit | 1280 / 2.0× | – | – | 891 / 198 | – | – | CC0 | FACTS, ratio only | "6–7×, shared GPU" |
| 25 | 14.0 / 13.3 / 39.4 ms; 15.5 / 16.9 / 55.4 re-run | – | H3b / audit | 640 / 1280 / tiled | – | – | 891 | – | – | CC0 | FACTS, unstable | "640 is not faster than 1280 on this shared GPU" |
| 26 | 0.024 / 0.178 / 0.135 | – | H3c | 1280 / 2.0× / 1.5× | far | ≥ 20 | 198 (degraded third) | 0.25 | shipped | CC0 | qualified (lower bound) | per-stream only, with "lower bound" |
| 27 | 0.000 / 0.024 / 0.001 | – | H3b | 640 / 1280 / tiled | far | all | 198 (degraded third) | 0.25 | shipped | CC0 | qualified (lower bound) | not comparable to #4 (different tile arm) |
| 28 | 0.682 | [0.521, 0.829] | H3d | 2.0× + tile-border (d) | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS | "the border rule keeps far recall on CC0 renders" (R74 scope) |
| 29 | 0.492 / 0.061 | [0.312, 0.671] / – | H3d | full_1280 / full_640 (CPU fp32) | far | ≥ 20 | 594 | 0.25 | pooled | CC0 | FACTS | 0.492 is #10 re-run on CPU; 0.061 is #7 re-run on CPU. |
| 30 | 133 vs 146 near FP (d vs 1280); 979 for (a) | [86, 188] / [85, 212] | H3d | (d) / 1280 / (a) | near | all | 297 | 0.25 | pooled | CC0 | FACTS | "133 near FPs vs 146 at 1280, on renders" |
| 31 | 0.973 vs 0.944 | – | H3d | near AP50 (d) vs 1280 | near | all | 297 | AP | pooled | CC0 | FACTS | renders only (H3e contradicts on MOT20) |
| 32 | 0.592; FP 42 vs cap 74 | [0.409, 0.766] | H3d audit | every tile arm / (d) | far / near | ≥ 20 / all | 594 / 297 | **0.4** | pooled | CC0 | FACTS | "at conf 0.4 no tile arm reaches 0.65" |
| 33 | 0.295 (tiles) / 0.055 (1280) | [0.180, 0.372] | H3d audit | tile arms / 1280 | far | ≥ 20 | 198 (degraded third) | 0.25 | shipped | CC0 | qualified (lower bound) | "about 30 % far recall on the degraded stream — a lower bound" |
| 34 | +0.136 (0.667 → 0.803) | [+0.022, +0.293] | H3d | (e) far-ROI vs 640 | near | 13–40 | 297 | 0.25 | pooled | CC0 | FACTS (HN fails) | "the ROI gate is not far-only" |
| 35 | 0.486 / 0.231 / 0.507 / 0.389 | [0.423, 0.606] / – / [0.453, 0.603] / [0.308, 0.534] | H3e | 1280 / 640 / (a) / (d) | MOT20 | ≥ 20 | 300 | 0.25 | real | MOT20-m | FACTS | "on real MOT20 crowds keep 1280" |
| 36 | −0.118 | [−0.146, −0.067] | H3e | (d) − (a) | MOT20 | ≥ 20 | 300 | 0.25 | real | MOT20-m | FACTS; R74 | "the border rule deletes real people" |
| 37 | 0.802 (render 0.864) | [0.769, 0.824] | H3e | FP cut (d) vs (a) | MOT20 | – | 300 | 0.25 | real | MOT20-m | FACTS | "still removes 80 % of the tile FPs" |
| 38 | −0.079 (~41 people/frame) | [−0.093, −0.067] | H3e audit | (d) − (a), sparsest quartile | MOT20 | ≥ 20 | 300 | 0.25 | real | MOT20-m | FACTS, post-hoc | "even in the sparsest quarter" |
| 39 | 0.383 (7,122 / 18,598) | – | H3e | deleted boxes that were TPs | MOT20 | – | 300 | 0.25 | real | MOT20-m | FACTS, post-hoc | label post-hoc |
| 40 | 0.684 / 0.572 / 0.449 | – | H3e | AP50 1280 / (d) / (a) | MOT20 | ≥ 20 | 300 | AP | real | MOT20-m | FACTS | MOT20 only; renders go the other way (#31) |
| 41 | 0.924 → 0.324 | – | H3f | tiles (d) raw → shipped | far | ≥ 20 (n 145) | 50 | 0.25 | raw / shipped | CC0 | FACTS (half frames) | "shipped profile takes far tile recall 0.924 → 0.324" |
| 42 | 0.892 / 0.309, loss 0.583 | [0.838, 0.946] / [0.219, 0.393] / [0.487, 0.688] | H3f audit | tiles (d) | far | ≥ 20 | 100 | 0.25 | raw / shipped | CC0 | FACTS | registered-frame check |
| 43 | 0.662 → 0.069 | [0.506, 0.857] / [0.000, 0.146] | H3f | full_1280 | far | ≥ 20 | 50 | 0.25 | raw / shipped | CC0 | FACTS | secondary arm |
| 44 | 0.621 (LOO) / 0.299 (AOI) | [0.423, 0.804] / [0.173, 0.430] | H3f | noise share, tiles (d) | far | ≥ 20 | 50 | 0.25 | LOO / AOI | CC0 | FACTS; R75 | "largest single lever; alone about 0.3 of the loss — interaction with blur and codec" |
| 45 | 0.184 / 0.218 | [0.063, 0.294] / [0.119, 0.357] | H3f | codec share | far | ≥ 20 | 50 | 0.25 | LOO / AOI | CC0 | FACTS | "the codec prior was wrong" |
| 46 | 0.982 → 0.772, drop 0.210 | [0.168, 0.257] | H3f | full_1280 | near | ≥ 80 (n 442) | 99 | 0.25 | raw / shipped | CC0 | FACTS (HN fails) | "costs a 1280 detector a fifth of large near people" |
| 47 | 0.387 vs 0.263 (1.47×) | – | H3g | σ shipped vs real | – | – | 48 renders / 12 real | – | shipped | CC0 + MOT-m | FACTS, estimator-referred (R76) | "reads 1.47× real on one estimator" |
| 48 | 0.607 vs 0.324 | [0.513, 0.713] | H3g | tiles (d) matched vs shipped | far | ≥ 20 | 50 | 0.25 | matched | CC0 | FACTS, not a validated profile | "matched noise recovers about half the far loss" |
| 49 | 0.283 | [0.175, 0.421] | H3g | full_1280 matched | far | ≥ 20 | 50 | 0.25 | matched | CC0 | FACTS | secondary |
| 50 | 0.084 (shipped 0.210) | [0.064, 0.106] | H3g | full_1280 near drop, matched | near | ≥ 80 | 99 | 0.25 | matched | CC0 | FACTS | "decision not met: near cost still 0.084" |
| 51 | 1/12 (real 4/12) | – | H3g | HN joint band | – | – | 12 | – | matched | CC0 + MOT-m | by construction (uninformative) | say "blockiness 2/12 vs real 8/12" instead |
| 52 | 0.766 | [0.667, 0.850] | H32c | full_1280 | showcase night (3 cams) | ≥ 20, render-visible (449) | 60 | 0.25 | raw | CC0 render + LLVIP-m ref | FACTS; R79 | "0.766 raw on the 449 render-visible GT" |
| 52a | 0.890 (old GT) | [0.829, 0.936] | H32c | full_1280 | showcase night | ≥ 20, mock vis > 0 (362) | 60 | 0.25 | raw | CC0 + LLVIP-m | retired as headline (R79); mock visibility, cannot be rebuilt for sites | never alone; only as "0.890 on the 362 mock-visibility rows" |
| 53 | 0.0045 (old GT 0.006 [0.000, 0.016]) | [0.000, 0.013] | H32c | full_1280 | showcase night | ≥ 20, 449 (old 362) | 60 | 0.25 | shipped | CC0 + LLVIP-m | FACTS; R78, R79 | "broken for detection, not a night penalty" |
| 54 | 0.016; Δ +0.011 (old GT 0.019; Δ +0.014) | [0.003, 0.028]; [−0.003, +0.027] | H32c | matched (s 0.710, partially matched) | showcase night | ≥ 20, 449 (old 362) | 60 | 0.25 | matched | CC0 + LLVIP-m | FACTS; R78 | "still collapses with noise partially matched" |
| 55 | 2.21× (1.57× vs tuning-15) | – | H32c | σ shipped / hold-out | – | – | 60 + 10 | – | shipped | LLVIP-m | FACTS (thin) | "≥ 1.5× on either denominator, thinly" |
| 56 | luma 50.8 vs 33.0 (raw 76.2); 0.59 of gap, 0.64 predicted | – | H32c | luma | – | – | 60 + 10 | – | shipped | LLVIP-m | by construction (AE target 48.65) | "still brighter than real night, as the AE target was set" |
| 57 | HN 0/13 in luma band | – | H32c | matched luma | – | – | 13 | – | matched | LLVIP-m | by construction | predicted by AE target > band p90 |
| 58 | AOI 0.988 / LOO 0.184 (449 GT: 0.988 / 0.199) | [0.963, 1.005] / [0.118, 0.248] | H32d | noise stage | showcase night | ≥ 20, 362 and 449 | 60 | 0.25 | stage ablation | CC0 + LLVIP-m | FACTS; R80; shares move ≤ 0.02 on 449 | "noise alone erases people" |
| 59 | codec AOI 0.744 (449 GT: 0.749) | [0.692, 0.799] | H32d | crf 39 on 2×-upsampled 640×360 | showcase night | ≥ 20 | 60 | 0.25 | stage ablation | CC0 + LLVIP-m | FACTS | "crf 39 alone removes three quarters" — with the upsample |
| 60 | pair LOO 0.978 (449 GT: 0.977) | [0.941, 1.013] | H32d | noise + codec | showcase night | ≥ 20 | 60 | 0.25 | post hoc pair | CC0 + LLVIP-m | FACTS (post hoc, AUDIT_H32D) | "two redundant killers" — say post hoc |
| 61 | minor stages each ≤ 7 % (upper CI ≤ 11 %) | isp AOI [0.034, 0.097] | H32d | exposure/optics/isp/colour | showcase night | ≥ 20 | 60 | 0.25 | stage ablation | CC0 + LLVIP-m | FACTS; R80 | never "innocent" |
| 62 | noise stage σ 3.3× hold-out (shipped output 2.21×) | – | H32d | aoi_noise σ 0.558 | – | – | 60 + 10 | – | stage alone | LLVIP-m | FACTS | label "noise stage alone"; the shipped profile is 2.21× |
| 63 | H32e fitted night | 0.018 [0.005, 0.029] | H32e | fit noise scale + CRF to LLVIP tuning-15 (s 0.7, crf 39) | – | – | – | – | pre-registered, run | LLVIP-m | decision not met; HN 2/13 | "fitted keeps crf 39; not a night penalty" |

**63 rows (+ 52a).**

## 2 · Which number to say when

1. Far recall at 1280 → **0.491 [0.311, 0.670]**, ≥ 20 px, CC0, conf 0.25 (H3c). Never 0.402 without "all rows"; never 0.405 without "MetaHuman, engineering-only".
2. Far recall at 640 → "under 3 % on all rows, 6 % on ≥ 20 px, CC0 renders, conf 0.25" (0.025 / 0.060). Say "blind" only with "on CC0 renders" (R77).
3. Tiling far recall → **0.681 [0.521, 0.830]** ≥ 20 px CC0 (H3c), with "6–7× compute, shared GPU, near FPs up" in the same breath. All-rows form: 0.643.
4. Tiles vs 1280 gain → **+0.190 [+0.119, +0.265]**; +0.155 only with "198-frame re-run".
5. 0.629 → only as "H3's MetaHuman number, replicated on CC0 as 0.643".
6. H3b's 0.346 tiled → only with "0.91× native tiles, a different arm" (R72).
7. Tile merge → "tile-border rule: 133 near FPs vs 146 at 1280 on CC0 renders; on MOT20 it deletes people, −0.118" (R74).
8. Conf 0.4 → "every tile arm 0.592, below the 0.65 bar"; any 0.681-class number is conf 0.25 only.
9. Day degraded far → "about 30 % (0.295 tiles), a lower bound — profile over-harsh" (AUDIT_H3F); never as a CCTV estimate.
10. What kills degraded recall → "sensor noise is the largest lever (LOO 0.621) but alone about 0.3 (AOI 0.299); interaction with blur and codec" (R75).
11. Noise recalibration → "1.47× real on one estimator; matched noise 0.324 → 0.607 far tiles; near 1280 cost still 0.084; coupled, not a fix" (R76).
12. Night → "0.766 → 0.0045 on the 449 render-visible GT, on visible people: the profile is broken for detection; night penalty unmeasured" (R78, R79). 0.890 / 0.006 only as "the old 362-row mock-visibility GT".
13. Why night collapses → "two redundant killers: noise alone (AOI 0.988) and crf 39 on a 2×-upsampled render (0.744); the pair recovers 0.978, post hoc; other stages each ≤ 7 %, not innocent" (H32d, R80). Noise-stage 3.3× only with "stage alone; shipped output 2.21×". H32e: "pre-registered, no result".

## 3 · Cross-doc contradictions found (65 v2 §0/§2, 103, 105, 106, 108, 111, 00_INDEX) and fixes

| # | contradiction | where | fix applied |
|---|---|---|---|
| C1 | Far-field paragraph set "under 3 %" (all rows, 0.025) against "49 % at ≥ 20 px" — two denominators in one comparison; the ≥ 20 px value at 640 is 6 % (0.060 / 0.061 in 106/108). | 65 v2 §0, 103 §2, 105 Q27 | Added "on all rows; 6 % on ≥ 20 px" to the 640 clause in all three copies. |
| C2 | "about 30 % survives the degraded stream" read as a fraction surviving, and without the lower-bound qualifier that 65 v2 §0's next bullet (AUDIT_H3F) requires. | 65 v2 §0, 103 §2, 105 Q27 | Now "about 30 % far recall on the degraded stream (a lower bound, AUDIT_H3F)". |
| C3 | 65 v2 §2 item 13 quotes H3's 0.021 / 0.405 / 0.629 "at 7× latency" bare, while 105 Q24 and 65 v2 §0 say 0.629 is MetaHuman engineering-only and the tiling cost is 6–7×. | 65 v2 §2 | Item 13 now labels H3 MetaHuman engineering-only and gives the CC0 H3c numbers (0.491 / 0.681 on ≥ 20 px, 6–7×). |
| C4 | Night luma "90 vs 34" (H32, 103 §2 night item 2) vs H32c "76.2 vs 33.0" — different render sets, not a contradiction, but read as one. | 103 §2 | Added the H32c showcase values with their scope. |

No contradiction found in 106 or 108 (0.491 → 0.681, 0.061, 6–7× all match #10/#17/#29/#24), 111 (+0.155 carries "on re-run"), or 00_INDEX (no far-field numbers).

## 4 · Night, one paragraph (H32 → H32d, H3g)

**Night (audited, one paragraph; H32, H32a/b, H32c, H32d, H3g):** Our night detection penalty is unmeasured: the profiles tuned to LLVIP overfit (2/13 and 3/13 in band on hold-out, H32a) and our renders are not dark (luma 90 vs a real median 34), so no recall drop we have is a night penalty (H32b branch B3; R47).
The shipped low-light profile is broken for detection, not a pessimistic estimate: on 60 night frames it takes YOLOv8n from 0.766 raw (449 render-visible GT, R79) to 0.0045, on people clearly visible in the raw render, while still brighter than real night (H32c, AUDIT_H32C; R78).
The cause is two redundant killers, not the whole chain (H32d, AUDIT_H32D): the noise stage alone erases people (AOI share 0.988) and crf 39 alone, on a 2×-upsampled 640×360 render, removes three quarters (0.744); removing both recovers 0.978 of the loss, either alone at most a fifth; exposure, blur, denoise and colour are minor (each ≤ 7 %, R80).
Those shares were registered on the 362-row mock-visibility GT and move ≤ 0.02 on the 449-row GT (AUDIT_H32D).
The output reads 2.21× the LLVIP hold-out noise (noise stage alone 3.3×), yet noise off is 30× below real, so the fix is less noise and a lower CRF, judged on hold-out; H32e, run: fitting only noise scale and CRF to LLVIP tuning frames keeps crf 39 (s 0.7); fitted recall 0.018 [0.005, 0.029] and the hard negative fails (2/13 in band, bar 7), so the decision is not met and raw minus fitted is not a night penalty.
The day stream shows the same stage coupling (H3g: 1.47× real noise; matched noise recovers about half the far loss but pushes blockiness out of band; R76).
LLVIP is non-commercial and only measures; a real night number needs owned night footage.
