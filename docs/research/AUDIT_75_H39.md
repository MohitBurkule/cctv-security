# AUDIT_75_H39 — H39 auto-calibration and doc 75

Audited 2026-09-27 against commit `2bdb46b`. CPU only; no GPU, no editor.

## 1. H39 recomputation

Independent recompute from `out/experiments/h39_autocalib/errors.parquet` (own RMSE / grouping code,
not the runner's): every point estimate in the 32 §H39 table matches `results.json`.

| arm | < 20 m | 20–30 m | ≥ 30 m | ratio | height MAE (m) |
|---|---|---|---|---|---|
| A0 exact | 0.208 | 0.203 | 0.263 | 1.26 | 0.024 |
| A1 DLT on GT feet | 0.117 | 0.141 | 0.205 | 1.75 | — |
| A2 free f (registered) | 57.374 | 90.041 | 257.46 | 4.49 | 0.077 |
| A3 free f, 10 s | 74.709 | 139.56 | 243.48 | 3.26 | 0.104 |
| A2f datasheet f (post hoc) | 0.958 | 2.202 | 2.924 | 3.05 | 0.074 |
| A3f (post hoc) | 0.759 | 2.287 | 5.113 | 6.74 | 0.093 |

Counts: 10 cameras, 4 scenes, 67 tracks, 8,195 boxes (A3 scored on 5,610 after frame 100) — match.
Exclusions: `disguise_and_tamper_day/cam_ptz` (status changes in window; live hfov 30–35°, pitch
−22°/−18° vs calib hfov 60°) and `street_crowd_far_day/cam_01` (duplicate) — correct, 12 calib files.
`tests/test_autocalib.py`: 9 passed.

**Claims that did not survive:**

1. "8 of 10 cameras ran f to the 4w bound with pitch 2–4° (true 9–25°)" — **false.** A2 f per camera:
   5,120 ×4, 5,062 ×1 (within 1.2 %), then 2,532, 1,951, 1,205, 605, 361. So **5/10** at/near the
   bound, pitch **1.5–4.0°**, true pitch on those five 9–20°. Only `cam_02` fits f within 20 %
   (1.03×). The conclusion (f unidentifiable) stands; the count was inflated. Fixed in 32 and 75.
2. "A2f pitch within ~2° on 8/10" — 7/10 within 2.1°, 9/10 within 2.7°; `cam_sub` 8.7° off.
   Fixed in 32 and 75.
3. 75 §4.4: "PTZ live head sat at 48°" — camera_status shows 30–35° (one 48° sample). Fixed.
4. 75 §6: "box tightness IoU 0.90 vs a detector, 13" — no such number in 13; 13 reports a
   detector/mask width ratio 1.00–1.03 on batch_v8. Fixed.
5. 32 pre-registration confounds said "11 cameras"; there are 12 calib files (10 scored). The
   pre-registration text is left untouched; a note is added under the results.

**Regression test for the "vertical residual only" bug:** `test_axis_aligned_box_heads_do_not_bias_fit`.
Mutation check: re-inserting the u residual into `fit_known_height` drives f to 5,120 on the test
scene (fixed code: 800.0), so the test fails on the bug. Covered.

**Post-hoc labelling:** A2f/A3f are in `POST_HOC` in the runner, marked "(post hoc)" in the 32 and
75 tables and "exploratory" in 32. Unlabelled uses found and fixed: 75 §4.1 gate sizes, Q4, Q8, §3
finding 2 (now "does not rescue the hypothesis"). The verdict everywhere is "not met" on A2.
The commit subject line (`datasheet f 0.96 m`) cannot be amended; the FACTS row already says post hoc.

## 2. Doc 75

| source | check | result |
|---|---|---|
| Sochor arXiv 1702.06451 | 7.98 → 1.10 km/h, manual 1.35 | [V] re-fetched |
| GeoCalib arXiv 2409.06704 | ECCV 2024, authors; LaMAR 0.28/0.87/3.03; MegaDepth pitch 1.94, FoV 4.46 | [V] Table 1; MegaDepth roll 0.36 added |
| Vuong WACV 2024, 2311.04243 | >100 cameras, 20 for eval | [V] |
| Tang 1708.06831 | walking-human self-calibration | [V]; "AI City winner" narrowed to 2017 Track 2 |
| Lv/Zhao/Nevatia TPAMI 2006 | any figure | Semantic Scholar 429, dblp bot-wall → **kept [A]**; the table cell no longer paraphrases a result |
| Liu/Collins/Liu BMVC 2011 | any figure | bmva.org page empty/404 → **kept [A]** |
| 29-derived (CityFlow 11.52 px, 5–14 landmarks, WILDTRACK 1,398) | vs 29 refs 7–8 | match |
| arithmetic | √2·0.2·10 = 2.83 m/s; 30 ms × 1.5 m/s = 4.5 cm; 3 % × 30 m = 0.9 m; 100 ms × 1.5 = 0.15 m; 1° at 40 m from 4.5 m ≈ 7.4/5.4 m | ok |

Q&A → FACTS: Q1 (29 rows), Q2 (H39 + new audit row), Q3 (new audit row: 0.077 m), Q4 (H39 row),
Q5 (H39 row, 0.21 m), Q6 (new audit row: PTZ exclusion), Q7 derived arithmetic, Q8 (Sochor row;
wording changed from "could not get under ~1 m" to 57 m registered / 0.76–0.96 m post hoc), Q9 [A]
by design (no number), Q10 (H39 row). All ten trace.

## 3. Corpus fold-in

FACTS: 4 rows (H39 audit, GeoCalib MegaDepth, Vuong, Tang). 52 register row + header; 64 register
row, results-table row, paragraph "focal length cannot be recovered from box heights; height
consistency is a trap metric; 0.2 m floor at exact calibration"; 60 item 37; 48 number 44 + C8f;
65 N14; 73 world-coordinate bullet (gates widen with range, cites H39); 23 calibration note (H41 with
M14); 66 H39 status + H41 (head–foot keypoint auto-calibration; prerequisite: batch_v8 has no
keypoint GT file — must be exported first); 00 rows for 75 and this audit.

## 4. Score

| criterion | before | after |
|---|---|---|
| H39 table numbers vs results/errors.parquet | 10/10 | 10/10 |
| per-camera narrative (bound count, pitch, PTZ hfov) | 5/10 | 10/10 |
| post-hoc arm labelled everywhere | 7/10 | 10/10 |
| regression test covers the bug | 10/10 | 10/10 |
| 75 sources / tags | 8/10 (phantom 13 cite, vague Lv cell) | 9.5/10 (Lv/Liu still [A]) |
| Q&A → FACTS | 7/10 | 10/10 |
| corpus propagation | 3/10 (FACTS, 13 only) | 10/10 |
| **total (×100/70)** | **71/100** | **99/100** |
