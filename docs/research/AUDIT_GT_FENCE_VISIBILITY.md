# AUDIT_GT_FENCE_VISIBILITY — effect of the fence-visibility fix on existing GT (2026-09-28)

> **Summary numbers superseded (2026-09-28, BUG_night_visibility_zero).** The table below multiplied the
> *mock painter's* column 9 (fences as opaque L x L blocks), not render visibility. Per-set status of
> column 9, from `write_render_visibility` against `boxes_mask.parquet`:
> * showcase_all_dusk / night: 684 of 2,672 conf-1 rows read exactly 0.000 and all 684 have mask pixels;
>   1,994 rows change (cam_01 1,031, cam_02 537, cam_ptz 426). With render visibility the fence correction
>   (not depth-tested mask, so vis x (1 - cover) is right) gives occluder=static 10 -> 470 and 0.5 crossings
>   4 -> 410 on cam_01+cam_02 (`out/gt_static_occ/*_v2`). Corrected GT: `out/gt_vis_v2/showcase_all_{dusk,night}`.
> * batch_v8 x 9: also mock column 9 (0–2 exact zeros per set, but 849–4,067 rows per set change, 344–2,317 by
>   > 0.1). No batch_v8 experiment (H3b/H3c/H3d, recall 0.696) filters on visibility: numbers unaffected.
> * sites (34 dirs, incl. the 27 demo sites) and sites_v2 (11): Director/mock GT, no ID mask rendered, so column 9
>   is the mock painter's by construction (1,463 / 5,569 and 228 / 1,678 rows exactly 0.000) and cannot be
>   re-derived from the render. H69 headline/SD/hard negative use all rows (unaffected); its post-hoc
>   vis >= 0.5 column is mock-based.
> * Re-scored: H32c raw recall 0.890 [0.829, 0.936] on 362 -> 0.766 [0.667, 0.850] on 449 (R79); shipped
>   0.006 -> 0.0045, matched 0.019 -> 0.016, decision unchanged (32 §H32c).
> * Double count fixed: `static_occlusion.correct_rows(depth_tested=...)` keeps vis when the ID mask was
>   depth-tested (`id_mask_depth_test` in render_result.json; absent -> not tested). No existing set records it.

Follow-up to `docs/BUG_gt_visibility_fences.md`. Question: which ground truth
already used by the demo and the experiments was wrong because static
occluders (fence/wall/hedge from `env_plan.json`) were invisible to GT, and does
any quoted number move?

## Method [V]

`survsim.gt.static_occlusion.correct_rows` run post hoc on every fixed camera of
every set with an `env_plan.json` (script: `out/gt_static_occ/fence_audit.py`,
inputs read-only, outputs `out/gt_static_occ/<set>/static_occlusion.parquet` +
`summary.json`, roll-up `out/gt_static_occ/all_summary.json`). PTZ cameras are
skipped (their calib is the configured pose; the head slews — principle 2).
Showcase and batch_v8 MOT is mask GT (`boxes_mask`), sites is Director GT; the
correction multiplies column 9 either way (the same rule `build_tight_gt` now
applies). No re-inference, no editor, no GPU.

Columns: rows = GT rows on fixed cameras; cover>0 = rows with `static_cover > 0`;
static = rows now labelled `occluder=static`; cross = rows vis_old ≥ 0.5 → vis < 0.5;
cross≥20 = of those, boxes ≥ 20 px tall (the only ones `usably_visible` and
`tools/eval_recall.py` count); alarm ev = suspicious/hostile events in
`events.jsonl`; lost = events whose actor has ≥ 1 frame where the best camera
drops from ≥ 0.5 to < 0.5 visible; all-lost = every frame of the event < 0.5.

`usably_visible` itself cannot flip: it is height-only and the correction
changes visibility, not boxes. What can flip is the new width rule
(`geometry.box_usable`); that column is "sliver" (h ≥ 20 but width fails).

| set | rows | cover>0 | static | cross | cross≥20 | sliver | alarm ev | lost | all-lost |
|---|---|---|---|---|---|---|---|---|---|
| showcase_all_dusk | 2176 | 498 (22.9 %) | 10 | 4 (0.18 %) | 4 | 60 | 6 | 1 | 0 |
| showcase_all_night | 2176 | 498 (22.9 %) | 10 | 4 (0.18 %) | 4 | 60 | 6 | 1 | 0 |
| batch_v8 disguise_and_tamper_day | 2527 | 0 | 0 | 0 | 0 | 19 | 8 | 0 | 0 |
| batch_v8 disguise_and_tamper_day_epochs | 5027 | 0 | 0 | 0 | 0 | 13 | 8 | 0 | 0 |
| batch_v8 disguise_and_tamper_night | 2527 | 0 | 0 | 0 | 0 | 19 | 8 | 0 | 0 |
| batch_v8 smoke_mock_day / night | 1572 each | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 |
| batch_v8 street_crowd_day / night | 7079 each | 0 | 0 | 0 | 0 | 5 | 2 | 0 | 0 |
| batch_v8 street_crowd_far_day / night | 7599 each | 0 | 0 | 0 | 0 | 289 | 2 | 0 | 0 |
| sites (34 dirs with GT) | 5569 | 1377 (24.7 %) | 438 | 325 (5.8 %) | 169 | 31 | 0 | – | – |

Per site (only those with cover > 0): 00 120/280 cover, 54 cross (all < 20 px);
05 36/36, 7 cross, 9 slivers; 07_s1259 160/172, 0 cross; 07_s5007 160/160, 17;
**09 80/80, 62 cross (77.5 %)**; 10 80/200, 53 (all < 20 px); 12 120/280, 49
(all < 20 px); 13 160/160, 0; 17 120/120, 25; 19 65/320, 26; 25 160/160, 0
(22 slivers); 27 16/80, 0; 30 60/280, 0; 31 40/240, 32. The other 20 sites
have no static cover. `07_perimeter_site_s5007` has GT but no render; the
demo's "27 sites" are a subset of these 34.

Every set has an `env_plan.json`; none lacks it. batch_v8's disguise sets carry
98 `fence_run` items and smoke 30 `hedge`s, and the fences are in view (3.6–13 %
of pixels have static depth), but no person is ever behind one; street_crowd
has no fence/wall/hedge.

## Showcase events

The one affected alarm event is `suspicious.access.intrusion` p000: 4 of 92
event frames lose ≥ 0.5 best-camera visibility (it stays visible in the other
88). Showcase alarm cards come from `ZoneDwellRule` / `line_cross` on GT
*world* tracks, not on visibility, so no card verdict, hit count or delay in
`docs/research/demo/INDEX.md` changes.

## Quoted numbers

* **batch_v8 recall 0.696 / P 0.879 (FACTS, docs/12)**, H24/H46 AssA, H26/H51/H52/H61
  dose and ablation AP, H71, H3b/H3c, box-aspect and crowd statistics: all
  batch_v8. **0 of 42,581 fixed-camera rows have any static cover**, so the
  GT they used is unchanged — delta 0 exactly, no cached detections needed.
  batch_v8 PTZ rows were not checked (a slewed head; the detector-recall
  table's cam_ptz is 13 GT boxes over 10 frames).
* Slivers: `eval_recall.py` gates on height only, so the new width rule does
  not enter 0.696. If it were applied, street_crowd_far (in the recall table)
  would drop 289 of 4,132 eval-eligible rows per set — a change of evaluation
  protocol, not of this fix's GT, so no FACTS number is restated.
* Showcase: alarm hit counts are world-track rules (above), unchanged. The
  segments that draw GT mask boxes (13, 14, 15) filter at visibility ≥ 0.9/0.95;
  the 4 crossing rows are p000 in cam_01/cam_02 and could only remove points
  from illustrative, clip-only numbers.
* Sites: only H69 used them; its post-fix re-score is already in
  `docs/research/32` "H69 · post-fix GT".

## Verdict

No FACTS row, docs/13 or demo INDEX number depends on corrected rows; no
qualifier and no RETIRED_CLAIMS row are needed. The fence bug is material for
the generated sites (5.8 % of rows cross 0.5, 77.5 % on site 09) and cosmetic
for the showcase (0.18 %); batch_v8 is clean. The PTZ camera of every set is
unchecked.

## PTZ (2026-09-28)

`static_occlusion.live_static` now projects fences through the per-frame live
pose read from `gt/camera_status.jsonl` (yaw/pitch/hfov per `t`, frame =
round(t x fps); position and roll from calib) instead of `calib/cam_ptz.json`,
which holds the configured pose. Re-run on showcase_all_dusk and
showcase_all_night cam_ptz (`out/gt_static_occ/fence_audit_ptz.py`,
`ptz_summary.json`; the two sets share geometry and give identical counts):
502 rows, 7 distinct live poses, 0 frames without a recorded pose. Configured
vs live pose: static_cover changes on 175 / 502 rows, corrected vis on 116,
occluder label on 17; rows with any static cover 154 -> 80, `occluder=static`
19 -> 8, rows crossing vis 0.5 3 -> 0. So the configured pose over-counted
fence cover on the PTZ; the live-pose correction removes every PTZ 0.5
crossing. Not checked: batch_v8 and sites PTZ rows (not re-run here); the live
pose is the Director's camera_status, not a pose read back from the render.
