# 13 — Detection / MOT / ReID baselines

"Models and methodologies on our data": one command turns SurvSim runs into a
dataset, a second scores off-the-shelf models on it. The same code scores real
MOT20, which is the reference row every synthetic number is read against.

```bash
source .venv/bin/activate
# synthetic (mock silhouettes until renders exist)
survsim dataset configs/scenarios/smoke_mock.yaml --seeds 3 --out out/ds_mock
# with Unreal renders (tools/render_run.py layout: <dir>/<run>/<cam>/0000.png)
survsim dataset SCEN.yaml --seeds 3 --frames-dir out/renders --profile cctv_day_720p --out out/ds
# real reference
survsim dataset --mot ~/data/mot/extracted/MOT20 --max-frames 0 --out out/ds_mot20
survsim baseline out/ds_mot20 --task all      # det | mot | reid | all
```
Results: `<dataset>/baselines/results_<task>.{json,md}`; detections are cached
in `detections.json` so re-scoring does not re-run the model.

## Dataset construction
* Each scenario runs once per seed on the mock backend; per-camera MOT GT
  (`gt/mot_<cam>.txt`) and a COCO file are packaged with a `manifest.json`.
* **Splits are by seed**, never by frame (neighbouring frames are near
  duplicates; a frame split leaks test into train): last seed = test,
  second-last = val (≥3 seeds), rest = train. Baselines here are zero-shot, so
  they score every split; the splits exist for the first fine-tune.
* Render frame index *i* (0-based PNG) is MOT frame *i+1*. When `--frames-dir`
  is given, frames are degraded with `sensors.degrade.apply_profile(img,
  profile, camera=cam)`, seeded per run/frame.
* Without renders, frames are grey canvases with painted silhouettes at the GT
  boxes, and the manifest says `synthetic_topdown: true`. **Any number on such a
  dataset measures the plumbing, not a model** — the markdown header says so.
* GT convention is MOTChallenge: targets are `conf==1, class==1`; classes 2/7/8/12
  (on vehicle, static person, distractor, reflection) are ignore regions.

## Metrics
* **Detection** — YOLO11n (COCO-pretrained, person class, imgsz 1280, conf ≥
  0.01). COCO AP@[.5:.95], AP50, AP75, AR via pycocotools with `maxDets=1000`
  (MOT20 frames hold >100 people; COCO's default 100 silently caps recall) and
  ignore regions as `iscrowd`. Plus an operating point at conf 0.25: precision,
  recall, and **false alarms per camera-hour** (`eval.detection`), the number an
  operator actually lives with.
* **MOT** — ByteTrack (numpy re-implementation, `baselines/bytetrack.py`: Kalman
  on cx,cy,a,h; high/low two-stage IoU association; no camera-motion
  compensation; `max_lost` = 1 s) over the cached detections, predictions on
  ignore regions dropped as MOTChallenge does, scored by the validated
  `eval.tracking.evaluate_mot` (MOTA, IDF1, HOTA/DetA/AssA). "all" concatenates
  sequences (frame-offset, id-namespaced).
* **ReID** — GT crops (height ≥ 48 px, visibility ≥ 0.6, ≤ 4 well-spaced crops
  per identity per camera, ≤ 4000 total), OSNet x1.0 via torchreid with
  **ImageNet** weights (no ReID training; ResNet50-ImageNet is the fallback).
  Protocol: *cross-camera* when identities span cameras (same-camera gallery
  excluded); otherwise *cross-time*: same-camera entries < 5 s from the query
  excluded. Rank-1/5, mAP via `eval.tracking.evaluate_reid`. Identities never
  cross runs.

## What a number does and does not mean
* These are zero-shot, generic models. They set a floor, not a ceiling.
* MOT20 numbers here are **not** leaderboard-comparable: private detector, no
  CMC, no per-sequence tuning, train split scored (it is our reference, not a
  benchmark submission). A leaderboard ByteTrack uses a MOT-trained YOLOX-X.
* Single-camera MOT20 ReID is cross-time only — an easier problem than
  cross-camera re-identification.

## Real-vs-synthetic gap protocol
1. Same models, same thresholds, same code, same metric definitions.
2. Report synthetic next to real, per task; the quantity of interest is the
   **gap** (synthetic − real), at matched pixel-height distributions where
   possible (`gt/coco` height buckets).
3. A synthetic set that is much *easier* than real (gap ≫ 0) is not realistic
   enough to evaluate on; one much *harder* signals a rendering artefact before
   it signals a hard scenario. Look at failures before believing either.
4. A number is only reported if `synthetic_topdown` is false.

## Results (2026-09-26, RTX 2070 8 GB)

| Dataset | Det AP | AP50 | AP75 | MOT (MOTA/IDF1/HOTA) | ReID (rank-1/rank-5/mAP) |
|---|---|---|---|---|---|
| smoke_mock, 3 seeds x 2 cams x 300 frames (**synthetic_topdown: plumbing only**) | 0.008 | 0.012 | 0.010 | 0.000/0.000/0.000 (YOLO finds nothing in silhouettes) | 0.156/0.672/0.279 (OSNet-ImageNet, cross-camera, 9 ids) |
| **MOT20-01/MOT20-02, first 300 frames each** (real, subset) — **old** (pre-fix DetA/matching) | 0.348 | 0.730 | 0.293 | 0.463/0.538/0.545 | 0.186/0.341/0.231 (OSNet-ImageNet, cross-time, 105 ids) |
| **MOT20-01/MOT20-02, first 300 frames each** (real, subset) — **new, pre-parity** (§"HOTA/MOTA fix" below; superseded by the TrackEval-parity row) | 0.348 | 0.730 | 0.293 | 0.466/0.549/0.434 (hota_at_05 0.539) | 0.186/0.341/0.231 (OSNet-ImageNet, cross-time, 105 ids) |
| **MOT20-01/MOT20-02, first 300 frames each** — **TrackEval-parity** (§"TrackEval parity (M1)", 2026-09-27; use this row) | 0.348 | 0.730 | 0.293 | 0.466/0.559/**0.443** (hota_at_05 0.537) | 0.186/0.341/0.231 |

Detector re-baseline, detection only (2026-09-27, H16 in
`docs/research/32_EXPERIMENTS_LOG.md`, `out/experiments/h16_yolo26_zeroshot`):
same MOT20 subset, same harness, COCO weights, no fine-tuning.

| Detector | imgsz | Det AP | AP50 | AP75 | R / P @ conf 0.25 | batch_v7 recall (all / <20 px / 20–40 px) |
|---|---|---|---|---|---|---|
| YOLO11n (row above) | 1280 | 0.348 | 0.730 | 0.293 | 0.609 / 0.838 | – |
| YOLOv8n | 640 | 0.281 | 0.618 | 0.216 | 0.402 / 0.906 | 0.573 / 0.015 / 0.175 |
| YOLOv8n | 1280 | 0.338 | 0.703 | 0.288 | 0.571 / 0.832 | 0.824 / 0.547 / 0.707 |
| **YOLO26n** | 640 | 0.255 | 0.567 | 0.195 | 0.272 / 0.958 | 0.608 / 0.065 / 0.236 |
| **YOLO26n** | 1280 | 0.335 | 0.708 | 0.276 | 0.571 / 0.869 | 0.853 / 0.645 / 0.748 |

YOLO26n is *not* better than YOLOv8n on dense real MOT20 (−0.026 AP at 640,
−0.003 at 1280) but recalls more small synthetic people (+0.025 / +0.028
mean per-sequence recall, paired 95 % CIs exclude 0). Fine-tuned on 60 real
frames with the recipe tuned for yolov8n it is also lower (0.459 vs 0.486 AP,
same steps for both detectors), see H16. H16's synthetic *dose* gains for
YOLO26n compared unequal optimiser steps (the h14b confound; no equal-step
YOLO26n run exists, H26) — see the Experiments summary.

The mock row looks as expected: a COCO detector finds nothing in flat
silhouettes. It shows that the harness runs end to end. It says nothing about
how well a model performs.

The MOT20 row is a **subset, not the reference row**: MOT20-01 and MOT20-02
only, first 300 frames of each (600 frames total, not the full 8,931-frame
train split). A full-sequence run at `out/ds_mot20` (`--max-frames 0`, all 4
sequences) was started and killed after 2.5 h; a repeat attempt (2026-09-26,
this time with detections already cached) was killed again after 1 h 26 min at
95% CPU, still with no results file — still not practical, tracked as a
follow-up, not done here.

**What was actually slow, corrected (2026-09-26).** The original diagnosis above
— "association/HOTA is O(n²) per frame and that's the bottleneck" — is **wrong**
and was never measured, only assumed. Profiling `track_sequence` +
`eval.tracking.evaluate_mot` directly on the cached full-MOT20 detections
(`ds_mot20/baselines/detections.json`, all 4 train sequences, 8,931 frames,
`avg boxes/frame` 46–195) shows both are already fast:

| stage | before (this pass) | after | s / 100 frames (after) |
|---|---|---|---|
| `ByteTracker` (`baselines/bytetrack.py`) | 64.6 s / 8,931 frames | 55.7 s | 0.624 |
| `evaluate_mot` (`eval/tracking.py`) | 6.0 s / 8,931 frames | 6.3 s | 0.070 |
| **combined** | 70.6 s | **62.0 s** | **0.694** |

That is ~62 s for the *entire* MOT20 train split — nowhere near 20 minutes, let
alone the 1 h 26 min the killed `--task all` run burned. So the remaining time
is not in the code this pass touched. `run_baselines(..., "all")` also runs
`eval_det` (`pycocotools` COCO mAP over all 8,931 frames) and the ReID stage
(`_embedder()` + per-identity crop extraction and an OSNet-ImageNet forward
pass over up to 4,000 real JPEG crops, `baselines/run.py`) — those two were not
independently profiled in this pass, but by elimination one or both of them is
where the 1 h 26 min actually went; likely ReID, since it does real image I/O
and a CNN forward pass per crop with no cached fast path (`eval_det` and
`eval_mot` both operate on already-cached detections/JSON). **Next step:**
time `eval_det`/reid separately on the full set the same way, and cache ReID
crops instead of decoding full-resolution JPEGs and pytorch-tracing OSNet fresh.

The optimisations landed here (survsim/eval/tracking.py, baselines/bytetrack.py)
still stand on their own merits — a ~14% cut to the numpy ByteTracker's inner
loop (splitting `_KF._q()` into `_process_noise()`/`_obs_noise()` so `predict`
and `update` each compute only the half they use, instead of both every call)
and `Counter.update` in place of per-box dict increments in `evaluate_mot` —
verified metric-bit-identical against the pre-change values on this same
cached full-MOT20 detection set (per-sequence MOTA/IDF1/HOTA unchanged; the
example values once quoted here were pre-parity and are not re-derived) and against every existing test fixture. Detections
for the full set remain cached (`detections.json`, ~9k frames, 228 MB) so a
future pass can reuse them without re-running YOLO.

Detection AP50 0.73 / AP 0.35 for zero-shot YOLO11n on MOT20 is in the
right ballpark from memory: published MOT20 numbers for a COCO-pretrained
YOLO-family detector (no MOT20 fine-tuning) typically land around AP50
~0.6-0.8 and full COCO AP ~0.3-0.4 given MOT20's very dense, often heavily
occluded crowds (100+ people/frame push recall and AP75 down hard) — so the
harness's zero-shot number here is not surprising, though this is an
approximate recollection, not a citation to a specific paper. The current
(TrackEval-parity) IDF1 0.559 / HOTA 0.443 from the numpy ByteTrack
re-implementation (this paragraph originally quoted the retired pre-fix
single-α HOTA) are well below what tuned, MOT20-trained trackers on the
leaderboard report (ByteTrack MOT17 63.1 HOTA), consistent with §"What a number does and does
not mean" above: no CMC, no MOT-trained detector, no per-sequence tuning.


## Alarm scoring: `ilids_compat` and the loiter rule (2026-09-26)

Two fixes to `survsim/eval/`, diagnosed against a real `survsim run` of
`configs/scenarios/disguise_and_tamper.yaml` (seed 11, mock backend).

### `ilids_compat`

docs/research/19 §5.1 "Divergence to fix": SurvSim's `score()` counted every
repeat alarm on an already-detected event as an extra false positive, and gave
every unmatched alarm its own false positive, both harsher than the i-LIDS
protocol itself ("disregards" in-window repeats; coalesces false positives
closer together than 5 s into one). `score()` now takes `ilids_compat: bool =
False` (default keeps every number already reported unchanged) and
`fa_coalesce_s: float = 5.0`.

Same input — an event at `t_start=100`, a true hit, then 4 rapid repeats, plus
a chatter of 5 unmatched false alarms 2 s apart:

| Mode | true_positives | false_positives | precision |
|---|---|---|---|
| default (`ilids_compat=False`) | 1 | 4 (repeats) + 5 (chatter, no coalescing) = 9 | 0.100 |
| `ilids_compat=True` | 1 | 0 (repeats) + 2 (chatter coalesced to one FA per 5 s) = 2 | 0.333 |

Tests: `tests/test_eval.py::test_default_mode_penalises_every_repeat`,
`test_ilids_compat_ignores_repeats_inside_the_matched_window`,
`test_ilids_compat_coalesces_false_positives_within_five_seconds`,
`test_ilids_compat_default_off_keeps_existing_numbers`.

### Loiter rule: hero missed, worker at risk of a false positive

Running `configs/scenarios/disguise_and_tamper.yaml` end to end and reading
`gt/world.parquet` / `gt/events.jsonl` directly (rather than assuming the
config's stated intent matches what the behaviour engine actually did — CLAUDE.md
principle 1) turned up two compounding bugs in the naive `DwellRule` baseline:

1. **The hero's recorded loiter event is in `zone.yard` (tag `public`), not
   `zone.gate_A` (tag `gate`) as the scenario config's intent says.** The
   intruder's `pace` loiter drifts outside the nominal zone polygon while
   pacing, and `DwellRule` only watches `zone_tags=("gate", "restricted",
   "perimeter_fence")` — `public` is not in that list, so the rule cannot see
   the event at all, regardless of speed.
2. **`World.zone_of` resolves overlapping zone polygons by "first match in
   config order".** `zone.substation` (restricted, `allowed_roles: [worker,
   guard]`) is nested inside the much larger `zone.yard` (public), which is
   listed first, so the worker's `world.parquet` rows say `zone.yard` even
   though the worker is standing inside `zone.substation`. Any rule that reads
   `world_df["zone"]` directly inherits this and can never apply the
   restricted zone's `allowed_roles` exemption.

Measured on the real run (seed 11, `tolerance_s=30`, both loiter events —
`loiterer_200` at t=35.6 and `intruder_a` at t=63.3):

| Rule | alarms | true_positives | false_positives | precision | recall |
|---|---|---|---|---|---|
| `DwellRule(threshold_s=60)` (naive baseline, unchanged) | 0 | 0 | 0 | 0.000 | 0.000 |
| `PathLoiterRule(threshold_s=25, radius_m=4, reentry_gap_s=15)` | 15 | 2 | 13 | 0.133 | 1.000 |

`PathLoiterRule` (`survsim/eval/rules.py`) fixes both bugs without touching
`World.zone_of` (other consumers — MOT export, coverage analysis — depend on
its current behaviour):

* **Displacement radius instead of an instantaneous speed cap and exact zone
  tag match.** Loitering is "hasn't gone anywhere over a trailing window", not
  "zone tag unchanged AND speed <= 0.5 m/s this tick" — the latter breaks the
  instant either technicality does, even though the person never moved. The
  rule tracks the 90th-percentile distance from the running centroid over
  `window_s` seconds (report 19 §2.1's `spread(g)`) and a re-entry tolerance
  (`reentry_gap_s`) so a brief step outside the radius does not reset the
  dwell clock.
* **Its own smallest-containing-zone lookup**, computed straight from the
  scenario's zone polygons (smallest area wins on overlap) rather than from
  `world_df["zone"]`, so it is not fooled by bug 2 above.
* **Role/context exemption**: an actor whose role appears in the zone's
  `allowed_roles` is never flagged while inside that zone. On this run, that
  keeps `worker_1` (role `worker`, standing inside `zone.substation`, whose
  `allowed_roles` is `[worker, guard]`) alarm-free at every threshold tested
  (15/20/25/30 s) — confirmed directly: `PathLoiterRule.run` on `worker_1`'s
  track alone returns no alarms at `threshold_s=25`, and on `intruder_a`'s
  track alone returns alarms at t=69.7/95.2/174.3/207.6 (the first inside the
  30 s tolerance window of the real t=63.3 event).

Recall goes from 0/2 to 2/2; the 13 false positives (mostly the hard-negative
`commute_wait_negative` generators and `tailgater_1`) are the honest,
documented residual — a pure dwell-radius rule cannot separate a real loiterer
from an innocent person who is also simply standing still for a while without
more context (revisit count, corroboration), which is the whole point of
report 19's hard-negative pairing (principle 3). `PathLoiterRule` is a better
floor, not a finished behaviour classifier.

Regression tests (synthetic tracks shaped like the real hero/worker, not a
240 s re-run — see comment in `tests/test_eval.py` for why):
`test_dwell_rule_misses_the_pacing_hero`,
`test_path_loiter_rule_catches_the_pacing_hero_and_spares_the_worker`,
`test_path_loiter_rule_still_fires_on_an_unauthorised_idle_dwell`.

## HOTA/MOTA fix, alarm budget, and eval_recall matching (2026-09-26)

Three fixes prompted by `docs/research/26_MOT_DEEP_DIVE.md` (HOTA/MOTA
derivations and the report's own audit of this repo's evaluator),
`docs/research/28_BEHAVIOUR_SCENE_DEEP_DIVE.md` §7.1 (the alarm budget
arithmetic), and `docs/research/25_DETECTION_DEEP_DIVE.md` §7.1 (the
tallest-first matching note on `tools/eval_recall.py`).

### `survsim/eval/tracking.py`: DetA, the 19-alpha HOTA average, and MOTA matching

Report 26 §8.2 found that `evaluate_mot`'s `deta` was detection *recall*
(`TP/(TP+FN)`), not the HOTA paper's `DetA = TP/(TP+FN+FP)` (arXiv 2009.07736,
Eq. 18) — false positives never touched it — and that `hota` was a single
`alpha=0.5` slice, not the paper's mean over 19 thresholds (Eq. 16). Both are
now fixed: `deta`/`assa`/the new `hota_at_05` field report the alpha=0.5
slice with the corrected DetA formula, and `hota` is the mean of
`sqrt(DetA_alpha * AssA_alpha)` over alpha in {0.05, ..., 0.95}, each alpha
re-matched at its own IoU threshold.

On the report's own worked three-frame example (`tests/test_tracking_eval.py
::test_hota_worked_three_frame_example_from_report_26`, exact IoUs by
construction):

| | before | after (definition) |
|---|---|---|
| DetA | 0.833 (recall) | **0.714** |
| HOTA (alpha=0.5) | 0.532 | **0.493** (now `hota_at_05`) |
| HOTA (19-alpha mean) | not computed | **~0.38-0.40** |
| MOTA / IDF1 | 0.333 / 0.500 | unchanged (already correct) |

**Float-boundary correction (2026-09-26).** `_hota_multi_threshold` (and
`_match_frame_with_continuity`) compared IoU to the alpha threshold with a bare
`>=`. An IoU that is conceptually exactly one of the 19 alpha values —
including this worked example's algebraically-constructed 0.90/0.80/0.70 —
lands at e.g. `0.899999999...4` after box-area float arithmetic and fails
`>= 0.90`, silently dropping that alpha's match. Both comparisons now use a
`1e-9` epsilon. On this worked example that moves the 19-alpha HOTA from an
unstable ~0.38-0.40 (masked by the old test's ±0.03 tolerance) to a value that
matches report 26 §6.4's hand derivation exactly: **0.4034**. Re-run on the
cached MOT20-01/MOT20-02 detections below (`ds_mot20_sub`) with the epsilon:
**no change** (pre-parity HOTA 0.4342 all, hota_at_05 0.5393, identical to three decimal
places) — real-detector boxes essentially never land exactly on an alpha
boundary, so the bug was only ever visible on the exact-IoU-by-construction
worked example, not on this real-data row.

Also implemented the standard MOTChallenge/CLEAR-MOT matching procedure — a
still-valid previous-frame match is kept before Hungarian solves the rest —
and fixed a fragmentation edge case (a GT that enters unmatched and is picked
up later was wrongly counted as a fragmentation on its first-ever match). On
the cached MOT20-01/MOT20-02 detections (`ds_mot20_sub`, ByteTrack, no
re-detection, `survsim.baselines.run.run_baselines(..., task="mot")`):

| metric | old | new |
|---|---|---|
| MOTA (all) | 0.4632 | 0.4662 |
| IDF1 (all) | 0.5377 | 0.5494 |
| id_switches (all) | 194 | 114 |
| fragmentations (all) | 570 | 295 |
| HOTA (all) | 0.5448 (single alpha=0.5, recall-DetA) | 0.4342 (19-alpha mean) / `hota_at_05` 0.5394 — pre-parity; 0.4428 / 0.5372 after M1 |

The id_switches/fragmentations drop is mostly the matching-continuity fix
(fewer near-tie swaps counted as switches on MOT20's dense crowds); MOTA/IDF1
move slightly because the matches feeding them changed. HOTA moves down
because it is now a genuine 19-threshold average instead of one lenient slice
— this was always the intended reading, not a regression in tracking quality.
`docs/13`'s Results table above has been updated with both rows, labelled.

### `survsim/eval/alarms.py`: the docstring's 0.005 vs the code's 0.001

Report 28 §7.1 found the module docstring said the 500-camera/one-operator
budget was "roughly 0.005" false alarms per camera-hour, while
`operator_verdict`'s own formula (`4 nuisance alarms / (500 cameras * 8h
shift)`) computes 0.001 — a 5x mismatch between prose and code, not a bug in
the formula. Fixed the docstring to say 0.001 and named the formula's inputs
as module constants (`DEFAULT_BUDGET_A_PER_SHIFT = 4.0`,
`DEFAULT_BUDGET_CAMERAS_PER_OPERATOR = 500`, `DEFAULT_BUDGET_SHIFT_HOURS =
8.0`, `DEFAULT_BUDGET_FA_PER_CAMERA_HOUR = A/(K*H) = 0.001`) instead of bare
literals inside `operator_verdict`. Test:
`tests/test_eval.py::test_operator_budget_constant_matches_the_default_verdict`.

### `tools/eval_recall.py`: score-order matching, not tallest-GT-first

Report 25 §7.1 noted the tool matched GT boxes tallest-first, each claiming
its best-IoU unused detection — not COCO's score-ordered matching, so a
low-confidence detection on a tall person could claim a match before a
high-confidence detection on a shorter person was even considered. Matching
is now COCO-style: detections are processed in descending score order, each
claiming its best-IoU unused GT box (factored into `match_frame()`, tested in
`tests/test_eval_recall.py` without needing YOLO).

Re-ran the tool (new matching, same cached renders/GT, no re-render) on all 8
`out/batch_v6` sets, `--n 10`, same as docs/12's existing table:

| set | old (tallest-first) | new (score-order) |
|---|---|---|
| smoke_mock day | cam_01 0.828, cam_02 0.182 | cam_01 0.828, cam_02 0.182 |
| smoke_mock night | cam_01 0.690, cam_02 0.318 | cam_01 0.690, cam_02 0.318 |
| street_crowd day | 0.936, 0.808, 0.853 | **0.923**, 0.808, 0.853 |
| street_crowd night | 0.949, 0.705, 0.773 | 0.949, 0.705, 0.773 |
| disguise day | gate 0.853, ptz 0.769, sub 0.833, yard 0.289 | unchanged |
| disguise night | gate 0.735, ptz 0.846, sub 0.833, yard 0.0 | unchanged |
| street_crowd_far day | 0.949, 0.0, 0.065 | unchanged |
| street_crowd_far night | 0.962, 0.0, 0.032 | unchanged |
| **all** | 0.666 / 0.824 (excl. far: 0.725) | **0.665 / 0.823** (excl. far: 0.723) |

Only one camera-set changed at all (`street_crowd day cam_01`, 73/78 -> 72/78
matched, one fewer TP): these scenes are sparse enough that score-order and
tallest-first rarely disagree, unlike the crowded MOT20 regime the fix is
really aimed at. The pooled numbers move by <0.002, well inside the "single
operating point on ten frames" noise report 25 §7.1 already flags — the fix
is correct and worth having, but it does not change any conclusion already
drawn from docs/12's table.

### ByteTrack fixes: implemented behind a flag, measured, **not adopted** (H9b)

Report 26 §8.1 proposed two changes to `survsim/baselines/bytetrack.py`:
(1) split high/low detections at tau = 0.6 (the paper's value, Zhang et al.
2021, arXiv 2110.06864) instead of 0.5; (2) gate before solving —
`cost[iou < threshold] = 1e6` before `linear_sum_assignment` in both
association rounds, as `eval/tracking.py` already does.

Both are now in the code as options: `ByteTracker(fixed=True)` (tau 0.6 + gate),
`gate=True` (gate only), `high=0.6` (tau only). **The default path is the
original tracker, bit-identical** — verified against the pre-change file on
150 frames of each MOT20 sequence (identical track lists) and pinned by
`tests/test_experiments.py::test_bytetrack_default_path_is_the_original_algorithm`.

Scored with the pre-parity `evaluate_mot` (both arms the same code, so the
deltas are internally consistent; not recomputed after M1).

Pre-registered test (docs/research/32 H9b; adopt only if pooled HOTA rises on
*both* datasets without IDF1 falling > 0.005), yolov8n@1280 detections, same
detections for every variant:

| dataset | variant | HOTA | AssA | IDF1 | IDsw |
|---|---|---|---|---|---|
| MOT20-01/02 (300 fr each) | original | 0.4266 | 0.5820 | 0.5467 | 110 |
| | fixed (tau 0.6 + gate) | 0.4271 | 0.5809 | 0.5427 | 96 |
| | gate only | 0.4213 | 0.5622 | 0.5315 | 116 |
| | tau 0.6 only | 0.4282 | 0.5855 | 0.5452 | 96 |
| batch_v7 (24 seqs) | original | 0.5383 | 0.6739 | 0.7211 | 141 |
| | fixed | 0.5326 | 0.6642 | 0.7204 | 135 |
| | gate only | 0.5302 | 0.6539 | 0.7127 | 143 |
| | tau 0.6 only | 0.5411 | 0.6852 | 0.7300 | 131 |

**Verdict: not adopted.** The combined fix is +0.0005 HOTA on MOT20 and −0.0057
on batch_v7 (per-sequence paired CIs include 0 on both). The parts disagree:
gate-before-solve alone is *worse* on both datasets (batch_v7 −0.0045 [−0.0095,
−0.0005]), tau 0.6 alone is slightly better on both (+0.0016 MOT20, +0.003
batch_v7, inside noise). The gate is correct for an *evaluator* (it must not
waste a GT on a sub-threshold pair) but, for this tracker's IoU-only
association, it did not improve tracking. A tau-only default would need its own
pre-registered run. CMC and ReID remain documented gaps (module docstring).



## Loiter rule redesign (2026-09-26, h58)

Full account: `docs/research/58_LOITER_RULE_REDESIGN.md` (pre-registered,
commit `0c0976f`). New rules in `survsim/eval/rules.py`: `ZoneDwellRule`
(C1, zone/role exemptions), `DisplacementLoiterRule` (C2, clock resets on
net displacement > 4 m in 10 s — fixes path_loiter's transit bug),
`RevisitRule` (C3), `LearnedLoiterRule` (C4, logistic on
`survsim/eval/loiter_features.py`), `AllOfRule` (C5). Tuned on a disjoint
seed-58 split, scored once on the same 3,002 H12 clean camera-hours
(regenerated, 0/976 worlds differ).

| rule | FA/cam-h [Garwood] | recall@30 | precision@30 |
|---|---|---|---|
| dwell_25 (H12) | 6.01 [5.92, 6.10] | 0.900 (window-only; actor-aware 0.367) | 0.182 |
| dwell_60 (H12) | 4.55 [4.48, 4.63] | 0.156 | 0.067 |
| **LearnedLoiterRule (round 1)** | **2.92 [2.85, 2.98]** | **0.867** | **0.331** |
| kinematic-twin floor | ≈ 1.0 × recall | — | — |

Pre-registered target (≤ 0.0455, 100× below dwell_60) **failed, as
predicted**: smoke breaks are `Loiter` subclasses pacing in gate zones
(1.01/cam-h), so no track-only rule can go below ~1,000× our assumed budget on these
worlds. Reproduce: `python tools/loiter_eval.py {gen,feats,fit,eval}`.

### Simulator fixes this exposed, now landed (2026-09-27)

Two of the report's "Simulator fixes this exposed" items are fixed in
`survsim/director/behaviours.py` and `survsim/eval/alarms.py` (docs/11 items
19–20):

1. **`loiter_arc` no longer walks to the exact zone centroid.** `Loiter.begin`
   (and therefore `CommuteWait`, `SmokeBreak`) now samples its dwell target
   with `world.sample_goal`, the same seeded jitter every other destination
   in the simulator gets, instead of `world.resolve_point`'s exact centroid.
   "Distance to zone centroid" no longer needs to be a hand-excluded
   forbidden feature — it is no longer a leak by construction. This changes
   ground truth positions (not just labels), so **H12/H58's cached numbers
   above have not been rerun and should not be assumed still exact.** The
   dwell-time distributions and archetype mix are unchanged, so a rerun is
   expected to move the numbers by a small amount (jittered dwell points are
   still inside the same zone, and the retry logic keeps the pacing radius
   inside it too) rather than qualitatively, but this is not verified. A
   rerun of the full `tools/loiter_eval.py eval` (3,002 + ~360 event
   camera-hours, ~10 min) is pending; do not quote updated FA/cam-h or recall
   numbers for this fix without doing it.
2. **`alarms.score` gained `actor_aware` (default `False`, opt-in).** This
   directly targets the §4 finding that the label oracle's ceiling recall is
   0.90, not 1.0, because two same-label events starting within
   `tolerance_s` compete for one match. With `actor_aware=True` and alarms
   carrying a `uid`, both can be hit. **Not rerun on H12/H58** — none of the
   rules in `survsim/eval/rules.py` currently emit a `uid` on the alarms they
   produce (`rules.py` is out of scope for this change), so turning
   `actor_aware=True` today would have *no effect* on any cached H12/H58
   number: every alarm has `uid=None` and falls back to window-only matching.
   (Since done: see "Round 2" below.) Realising the recall-ceiling fix needed `rules.py` changed to carry the
   acting person's `uid` on each `Alarm` first, then a rerun with
   `actor_aware=True`; both are pending.

### Round 2 after the fixes (2026-09-27)

Rules now emit `Alarm.uid`; rerun on regenerated worlds with
`tools/loiter_eval.py round2` (`H58_OUT=out/experiments/h58_round2`), full
account in report 58 §6. Clean worlds were unchanged by the centroid fix
(0/676 differ, so every FA/cam-h is identical); 230/300 recall worlds changed.

| rule | FA/cam-h [Garwood] | recall@30 actor-aware [95 %] | precision |
|---|---|---|---|
| dwell_25 | 6.01 [5.92, 6.10] | 0.367 [0.319, 0.414] (window-only 0.733) | 0.080 |
| dwell_60 | 4.55 [4.48, 4.63] | 0.000 (window-only 0.156) | 0.000 |
| C2 displacement clock | 8.94 [8.84, 9.05] | 0.775 [0.730, 0.817] | 0.154 |
| LearnedLoiterRule (round-2 retrained; superseded by round 3) | 3.75 [3.68, 3.82] | **0.831 [0.792, 0.869]** | **0.326** |
| label oracle | 0 | 1.000 (window-only 0.903) | 1.000 |

Actor-aware scoring shows the dwell rules' window-only recall was mostly
alarms on bystanders. The learned rule's FA margin over dwell_25 shrank from
2.06× to 1.60× (a θ-selection shift on the new train split, not the leak:
round-1 weights still score 2.92), but it is the only rule whose recall
holds up. (Round 2's "ship the retrained rule" is superseded by round 3 below
and then by 58 §8.4's operator-budget trade-off.) Always score with `actor_aware=True`.

### Actor-aware is now the default (post round 2)

`alarms.score()`'s `actor_aware` parameter is now `None` by default, meaning
**auto**: it resolves to `True` the moment any alarm in the call carries a
`uid` (which every rule in `survsim/eval/rules.py` does, as of the uid work
above), and falls back to the old window-only matching only when no alarm has
one. Explicit `True`/`False` still override auto mode, `survsim eval` exposes
this as `--actor-aware`/`--window-only`, and `AlarmScore.window_only_recall`
carries the old, actor-blind number alongside whichever mode actually ran,
plus a `bystander_hits` count (alarms inside an event's window naming a uid
that is not one of that event's actors). Consequence: **every window-only
recall quoted above for H5 and H12 (0.90 ceiling, and any number from before
this file's "Round 2" section) must now be read as an upper bound, not the
actor-aware number** — those runs predate rules emitting `uid` and were never
rerun under the new default; only the H58 round-2 table's `actor-aware`
column reflects it.


## Loiter rule round 3 (docs/research/58 §7, 2026-09-27)

H12 worlds, 3,002 clean cam-h, 360 events, 30 s tolerance, actor-aware scoring.

| rule | FA/cam-h [Garwood 95 %] | recall [95 %] |
|---|---|---|
| **`LearnedLoiterRule` round-1 weights (A1), θ 0.95, clock ≥ 5 s** | 2.915 [2.854, 2.977] | 0.825 [0.789, 0.862] |
| `LearnedLoiterRule` round-2 retrained, θ 0.9, clock ≥ 10 s (superseded by round-1 weights above) | 3.745 [3.676, 3.815] | 0.831 [0.792, 0.869] |
| `GBMLoiterRule` HistGBM, track-only, θ 0.8 | 3.114 [3.051, 3.178] | 0.842 [0.807, 0.876] |
| `GBMLoiterRule` + zone-function context (needs a site profile) | 2.468 [2.412, 2.525] | 0.822 [0.786, 0.860] |

The calibrated GBM arm fell back off-grid (declared deviation, 58 §7.2).
Adding context cuts FA by 20.7 %. Every rule is still ~2,500–3,700× the
assumed 0.001 FA/cam-h budget. Rounds 4–5 (H21, H23, H42, H22, H45, H33) moved the
question from "which rule" to "which θ for which operator load": the ship
point is an operator-budget choice among A1, pooled θ 0.9 and conformal θ
(58 §8.4–8.5). Their numbers are in the Experiments summary at the end, not
repeated here.

## Box aspect: MOT20 hand boxes vs batch_v8 mask boxes (2026-09-27)

docs/11 said MOT20's hand boxes are "14 % wider than the detector's"; no FACTS
row supported it. Its source was H6 (`out/experiments/h6_diagnose`): zero-shot
YOLOv8n widths on MOT20-02 are a median 0.865 of the hand labels (so MOT20 is
~16 % wider than *that detector*), while on every batch_v8 set the same
comparison gives 1.00–1.03 (`box_tightness.json`). The direct GT-vs-GT number
was never computed. Recomputed with `scripts/box_aspect_tracking_stats.py`:

* MOT20 train 01/02/03/05, conf = 1, class = 1; batch_v8 day sets
  disguise / smoke / street_crowd / street_crowd_far (night shares geometry;
  far cam_01 duplicates street cam_01, dropped). Visibility ≥ 0.9.
* **Border-touching boxes dropped** (3 px margin): MOT20 GT is clipped at the
  image edge, which made its "< 50 px" bin median w/h 1.27 — a truncation
  artefact, not small people. After the filter MOT20 has 5 tracks < 50 px, so
  that bin is not reported.
* Statistic: median(w/h) MOT20 ÷ median(w/h) batch_v8, 95 % percentile
  bootstrap resampling whole tracks (2,000 draws; frames within a track are
  not independent).

| height bin | MOT20 med w/h | v8 mask med w/h | ratio | 95 % CI | tracks MOT20 / v8 |
|---|---|---|---|---|---|
| 50–100 px | 0.446 | 0.365 | 1.221 | [1.131, 1.289] | 314 / 38 |
| 100–200 px | 0.432 | 0.430 | 1.004 | [0.821, 1.198] | 1170 / 27 |
| ≥ 200 px | 0.403 | 0.361 | 1.119 | [0.990, 1.256] | 247 / 6 |
| **pooled ≥ 50 px** | 0.432 | 0.380 | **1.138** | **[1.062, 1.213]** | 1401 / 49 |
| pooled ≥ 50, v8 *amodal* | 0.432 | 0.349 | 1.237 | [1.164, 1.294] | 1401 / 49 |

**Verdict.** The number survives by coincidence, the stated basis does not:
MOT20 boxes are **+14 % [+6, +21] wider than our mask GT pooled**, but the gap
is concentrated in 50–100 px (+22 %) and is not distinguishable from zero at
100–200 px, where most MOT20 boxes are. The pooled figure mixes height
distributions (median GT box height over all visible boxes: MOT20 140 px, ours 51 px; `results.json` "tracking"), so treat it as descriptive.
Our amodal boxes are *narrower* than our mask boxes (0.349 vs 0.380) — [A] likely because the
envelope (r_frac 0.13) is fitted to the body axis and misses swinging arms the mask
catches. Aspect is not pure label convention either — MOT20 is shot from high,
steep cameras, where foreshortening widens a standing person. docs/11 now
quotes the measured figure; FACTS row "Box aspect". Figure:
`docs/research/figures/fig_box_aspect.png`. Companion figure (people/frame,
visibility fraction, track length distributions for the same MOT20 vs
batch_v8 comparison, from the same script): `docs/research/figures/fig_tracking_stats.png`
(also discussed in `docs/research/73` §tracking).

## TrackEval parity (M1, 2026-09-27)

`evaluate_mot` is now checked against the reference TrackEval
(JonathonLuiten/TrackEval master, pip-installed into `.venv`; the removed
`np.float`/`np.int`/`np.bool` aliases are restored in-process by
`survsim/eval/trackeval_bridge.py`, which also writes our rows as a
MOTChallenge layout and runs the official `Evaluator` with `HOTA`, `CLEAR`,
`Identity`, preprocessing off so both sides see identical boxes). Driver:
`python tools/trackeval_parity.py --old <rev>` → `out/experiments/m1_trackeval_parity/results.json`.
Regression: `tests/test_trackeval_parity.py` (slow; skips without TrackEval) —
|Δ| < 1e-6 on edge cases, < 1e-3 on the MOT20 subset.

Inputs: the cached YOLO detections (`out/datasets/mot20_sub/baselines/detections.json`)
re-tracked with the numpy ByteTrack on CPU exactly as `baselines.run.eval_mot`
does (the old code reproduces the published 0.4342, so the inputs are the same);
batch_v8 `street_crowd_day` GT (3 cams) vs a seeded perturbation of itself
(15 % drop, 4 px jitter, one mid-sequence ID swap, 5 % FPs) — no cached tracker
output exists for batch_v8; three synthetic edge cases (empty frames, ID
switch, fragmentation).

Δ = ours − TrackEval, MOT20 subset (COMBINED = both sequences):

| metric | TrackEval | ours before (`d1e7f0f`) | Δ before | ours after | Δ after |
|---|---|---|---|---|---|
| HOTA (19-α mean) | 0.4428 | 0.4342 | −0.0086 | 0.4428 | < 1e-15 |
| DetA (α = 0.5) | 0.4846 | 0.4976 | +0.0130 | 0.4846 | 0 |
| AssA (α = 0.5) | 0.5955 | 0.5846 | −0.0109 | 0.5955 | 0 |
| HOTA (α = 0.5) | 0.5372 | 0.5393 | +0.0021 | 0.5372 | 0 |
| MOTA | 0.4658 | 0.4662 | +0.0003 | 0.4658 | 0 |
| MOTP | 0.7664 | 0.7666 | +0.0002 | 0.7664 | 1e-15 |
| IDF1 | 0.5585 | 0.5494 | −0.0091 | 0.5585 | 0 |
| IDP / IDR | 0.7622 / 0.4407 | 0.7498 / 0.4336 | −0.012 / −0.007 | same | 0 |
| IDSW | 123 | 114 | −9 | 123 | 0 |
| Frag (per seq) | 174 / 120 | 176 / 119 | +2 / −1 | 174 / 120 | 0 |
| FN / FP | 12,408 / 1,405 | same | 0 | same | 0 |

batch_v8 day (3 cams + combined) and the three edge cases: before and after
both agree to ≤ 7.8e-16 — the disagreements only appear with real tracker
output (dense scenes, near-tied matches). Two further hand cases in
`tests/test_tracking_eval.py` did disagree before: a gap in which the tracker
output *nothing* (old Frag 1, TrackEval 0) and report 26's 3-frame example
(old HOTA 0.4034, TrackEval 0.4005).

What was wrong in ours (definitions kept: 19-α HOTA, DetA = TP/(TP+FN+FP)):

1. **HOTA matching.** We re-ran Hungarian on IoU independently at each α.
   TrackEval matches once per frame maximising `global_alignment_score × IoU`
   (the paper's association-aware matching) and thresholds that one matching
   at each α. This was the whole HOTA gap (−0.0086) and the DetA/AssA gaps.
2. **`deta`/`assa`/`hota_at_05` came from the CLEAR (MOTA) matching**, not the
   HOTA matching — now the α = 0.5 slice of the HOTA computation.
3. **IDF1 counted only CLEAR-matched pairs.** Identity metrics take every
   GT/pred pair with IoU ≥ 0.5 in a frame as a potential match and solve one
   global identity assignment (Ristani et al.). −0.0091 IDF1.
4. **CLEAR continuity.** We kept a previous match greedily *across gaps* and
   then Hungarian'd the rest; TrackEval adds a 1000 bonus for the previous
   *frame's* match inside one Hungarian. Frames with no GT or no predictions
   are skipped entirely (they neither reset continuity nor break a Frag run);
   Frag = run starts − 1. IDSW +9.
5. **Epsilon.** Thresholds compare at machine eps like TrackEval, not our 1e-9,
   so an IoU of 0.899999…94 fails α = 0.90 (this is the 0.4034 → 0.4005 in the
   worked example; `2f7986c`'s epsilon is superseded for `evaluate_mot`).
6. MOTA is now `(TP − FP − IDSW)/max(1, TP + FN)` (differs only when there is no GT).

**Headline change: MOT20 subset HOTA 0.4342 → 0.4428 (+0.0086)**, IDF1
0.549 → 0.559, MOTA 0.466 unchanged. Numbers computed with `evaluate_mot`
before this commit (H17's tracking deltas — which also compared unequal
optimiser steps, H26 — and H9b) are internally consistent
(same code on both arms) but are "our definition", not TrackEval; they have not
been recomputed.

## ReID association in ByteTrack (H24, 2026-09-27)

`ByteTracker(app_weight=w, ema=0.9)` (`survsim/baselines/bytetrack.py`) adds an
appearance term to the stage-1 (high-score) cost: `(1 − IoU) + w·(1 − cos)`
between the track's EMA feature and the detection's embedding (`det["emb"]`),
solved and then IoU-filtered at 0.2 exactly like the control; stage 2 stays
IoU-only. `w = 0` (default) is bit-identical to the old tracker. Runner:
`survsim experiment h24_reid_assoc` (`survsim/experiments/reid_assoc.py`),
scored with reference TrackEval via `survsim/eval/trackeval_bridge.py`
(which now also returns α-mean `deta_mean`/`assa_mean`).

| set (mean of 5 h14b ckpts) | ByteTrack AssA / IDSW | + OSNet-ImageNet | + HSV |
|---|---|---|---|
| MOT20-02 frames 1–300 | 0.5060 / 92.6 | 0.5199 / 87.0 | 0.5224 / 84.0 |
| batch_v8 day, 12 cams | 0.5197 / 83.4 | 0.5535 / 71.6 | 0.5406 / 74.2 |

Per-sequence ΔAssA (OSNet-ImageNet): batch_v8 +0.0194 [+0.0004, +0.0439],
MOT20-02 +0.0139 [+0.0018, +0.0268]. It narrowly misses H24's +0.02 bar, but
appearance never lowered mean AssA on either set (per checkpoint it did twice, AUDIT_H24) and cuts ID switches, so `w = 1`
with OSNet-ImageNet is the recommended setting for the M3 reference tracker
(untuned; long-gap re-identification not implemented). Details: docs/research/32 §H24.

**H46 follow-up (2026-09-27) — w was untuned in the wrong direction.** Sweeping
w ∈ {0.25, 0.5, 1, 2, 4} (OSNet-ImageNet, same 5 checkpoints, TrackEval AssA
α-mean) on batch_v8 day and MOT20-02 finds ΔAssA monotonically increasing with
w on both sets over the whole swept range, with the same argmax (w = 4) on
both: batch_v8 day +0.0421 [+0.0083, +0.0819], MOT20-02 +0.0338 [+0.0157,
+0.0520] — both clear H24's +0.02 bar and both CIs exclude 0 (post-hoc sweep; the argmax w = 4 is
picked from the same 5 arms whose CI is then quoted, and does not survive Holm correction across
the 5 w values — cross-set validation pending in H46b, AUDIT_H46). w = 1 was not
the optimum tried; the sweep did not find a ceiling, so w = 4 is a lower bound
on the best setting, not a certified optimum. Night arm (batch_v8
`disguise_and_tamper_night` + `smoke_mock_night`, 1 of the 5 checkpoints,
fresh detections/embeddings, bounded to fit the 75 min budget) at w = 4: ΔAssA
−0.0147 [−0.0972, +0.0535] — appearance does **not** clearly help at night
(CI includes 0, mean negative), contradicting the pre-registered hypothesis
that it would help less than day but stay positive. Caveats: night arm is 2
sequences × 1 checkpoint (underpowered, wide CI); day/MOT20 sweep did not
extend past w = 4 so the true optimum is unknown. Runner:
`survsim experiment h46_reid_w_night` (`survsim/experiments/h46_reid_w_sweep.py`).
Details: docs/research/32 §H46.

**H46b follow-up (2026-09-27) — a ceiling exists, priced in ID switches; night arm
underpowered by a hair.** Extending the sweep to w ∈ {8, 16, 32} plus a true appearance-only arm
(`app_only=True`, geometry term dropped, IoU ≥ 0.2 gate unchanged) finds an interior AssA peak on
both sets — day argmax **w = 16** (+0.0613 [+0.0171, +0.1142]), MOT20-02 argmax **w = 8**
(+0.0486 [+0.0314, +0.0631]) — resolving H46's "no ceiling found". But ΔIDSW rises with w
throughout the extended range on MOT20-02 (+15.8 at w=8, +33.4 at w=16, +69.2 at w=32, all CI
excluding 0) and turns unfavourable on day only at w ≥ 16; the `app_only` arm is the sharpest
trade of all (day ΔAssA +0.0469 but ΔDetA −0.0109 and ΔIDSW +13.4 day / **+162.0 MOT20-02**, both
CI excluding 0). Cross-set validation: w* from day (16) gives MOT20-02 held-out ΔAssA +0.0479
[+0.0328, +0.0629]; w* from MOT20-02 (8) gives day held-out ΔAssA +0.0570 [+0.0208, +0.0987] —
both clear the +0.02 bar, but the MOT20-02-chosen w = 8 is the safer pick under an IDSW budget.
The full night arm (6 sequences × all 5 checkpoints — H46's "2 seq" undercounted the config's
night runs — at w = 16) gives ΔAssA +0.0470 [−0.0046, +0.1337]: positive, much tighter than H46's
1-checkpoint arm, but the CI still touches 0 by a small margin — reverses H46's negative point
estimate without yet clearing the pre-registered bar. **No w = 1 default change is made**;
choosing any of the higher-AssA arms means accepting materially more ID switches.
**Reference-tracker recommendation:** ByteTrack + OSNet-ImageNet appearance at **w ≈ 8**
(cross-validated; +0.05 AssA held-out) with the IDSW cost stated; never appearance-only.
Runner: `survsim experiment h46_reid_w_night_b` (`survsim/experiments/h46_reid_w_night_b.py`).
Figure: `docs/research/figures/fig_h46b.png`. Details: docs/research/32 §H46b.

## Experiments summary (H-numbers touching this doc's harness, 2026-09-27)

One row per experiment; the full pre-registration, CIs and caveats live in
`docs/research/32_EXPERIMENTS_LOG.md` (§ column), numbers in `FACTS_VERIFIED.md`.
The narrative sections above describe the harness and evaluator changes; they
do not restate these results.

| H | dataset | metric | result [95 % CI] | verdict | 32 § |
|---|---|---|---|---|---|
| H9b | MOT20 subset; batch_v7 (24 seq) | pooled HOTA, ByteTrack fix − original (pre-parity scorer) | +0.0005 MOT20; −0.0057 batch_v7 (per-seq CIs include 0) | not adopted, flag off | H9 |
| H11 | batch_v7 night | YOLOv8n recall, `cctv_night_ir` − raw | −0.609 [−0.710, −0.519] | sensor-model sensitivity, not a night penalty (H32b) | H11 |
| H12 | 3,002 clean mock cam-h | FA/cam-h dwell_60 / dwell_25 | 4.55 / 6.01 (4,500–87,000× over our assumed 0.001 across rules) | every track-only loiter rule far over budget | H12 |
| H16 | MOT20 subset; batch_v7 | zero-shot AP, YOLO26n − YOLOv8n; v7 recall | −0.026 @640, −0.003 @1280; recall +0.025 [+0.009, +0.042] / +0.028 [+0.006, +0.053] | yolov8n stays reference; YOLO26n dose gains +0.0092 / +0.0169 compared unequal steps (no equal-step run) | H16 |
| H17 | MOT20-02 frames 1–300 | HOTA mix_300 − real-only (pre-parity scorer) | +0.0103 [+0.0008, +0.0197], via DetA +0.0342; AssA −0.0051 n.s. | weak; unequal optimiser steps (H26), not re-run | H17 |
| H20 | MOT20 subset, cross-time | mAP, synthetic-FT OSNet − ImageNet | +0.021 [−0.047, +0.097] | no measurable effect | H20 |
| H21 | H12 worlds | FA/cam-h, calibrated GBM, 5 seeds | 2.960 [2.785, 3.135] at recall 0.836 | 2/5 seeds clear the bar (needs 4/5) | 58 round 4 |
| H22 | 976 H12 worlds, 1 operator × 40 cams | A1 realised recall @5 min, FIFO | 0.511 [0.484, 0.537] (ranked 0.586) | inconclusive (bar 0.495) | H22 |
| H23 | 10 train-world seeds | FA (R − F)/F | −8.5 % [−21.6 %, +6.2 %] | no dominance; θ selection dominates | 58 round 4 |
| H24 | batch_v8 day 12 cams; MOT20-02 | ΔAssA, + OSNet-ImageNet in stage 1 | +0.0194 [+0.0004, +0.0439]; +0.0139 [+0.0018, +0.0268] | +0.02 bar missed; w = 1 recommended for M3 | H24 |
| H46 | batch_v8 day 12 cams + MOT20-02, w sweep; batch_v8 night 2 seqs at best w | ΔAssA per w vs w=0; night ΔAssA at argmax w | day/mot20 argmax w=4: +0.0421 [+0.0083,+0.0819] / +0.0338 [+0.0157,+0.0520]; night: −0.0147 [−0.0972,+0.0535] | day+mot20 bar met post hoc (not Holm-significant; H46b cross-validation pending), same argmax w; night hypothesis (appearance still helps) not met | H46 |
| H46b | batch_v8 day 12 cams + MOT20-02, w∈{8,16,32}+app_only; batch_v8 night 6 seqs × 5 ckpt at cross-val. w* | ΔAssA/ΔDetA/ΔHOTA/ΔIDSW per arm; cross-val. held-out ΔAssA; night ΔAssA | day argmax w=16 +0.0613 [+0.0171,+0.1142] (IDSW −0.22); mot20 argmax w=8 +0.0486 [+0.0314,+0.0631] (IDSW +15.8); cross-val. held-out +0.0479 / +0.0570; night +0.0470 [−0.0046,+0.1337] | ceiling found (priced in rising IDSW, worst under app_only); cross-val. bar met both directions; night positive but CI misses 0 by a hair | H46b |
| H25 | 60 real + 100 batch_v8 | share of clean dose gain kept, σ 10 % + 10 % drop | 94 % (−0.0008 [−0.0010, −0.0006]); clean gain +0.0127 [+0.0114, +0.0133] vs a 6-epoch arm (unequal steps, H26) | refuted: label noise does not matter at this dose | H25 |
| H26 | 60 real + N batch_v8, 450 steps | AP gain at equal steps, N = 100 / 300 | +0.0041 [+0.0012, +0.0071] / +0.0045 [+0.0015, +0.0074] | none Holm-significant; no recommended dose | H26 |
| H51 | 60 real + N batch_v8, 450 steps, 10 paired seeds | AP gain at equal steps, N = 100 / 300 | +0.0042 [+0.0024, +0.0062] / +0.0051 [+0.0037, +0.0064] | both Holm-significant (p 0.0039): equal-step gain exists, small, one site | H51 |
| H52 | 60 real + 300 batch_v8 variants, 450 steps, 10 paired seeds | AP vs real-only 0.4911: true labels / shuffled labels / people masked (no boxes) / real x10 | +0.0051 / -0.0026 / +0.0036 / -0.0011; true - shuffled +0.0077 (Holm p 0.0098) | label-driven by the pre-registered rule. Person-free synthetic negatives also carry about 70 % (Holm p 0.047) — but see H61 | H52 |
| H61 | 60 real + 300 batch_v8, silhouette-masked (no inpainting, no boxes), 450 steps, 10 paired seeds | AP vs real-only 0.4911, true labels 0.4962: silhouette-masked (c') 0.4891 | a - c' +0.0071 (Holm p 0.0039); c' - real -0.0020 (Holm p 0.074, not significant) | box-fill artefact: H52's masked-background gain was the box-shaped inpainted fill, not real background content; the full +300 gain is labels-on-people | H61 |
| H32a/b | batch_v8 night, 9 cams with h ≥ 40 (611 boxes) | YOLOv8n recall Δ vs raw 0.938: IR / lowlight / thermal | −0.565 [−0.660, −0.496] / −0.835 [−0.888, −0.758] / −0.470 [−0.548, −0.394] | no profile in the LLVIP band: sensor-model sensitivities, not night penalties | H32a/H32b |
| H33 | 10 splits × 338/338 simulated worlds | splits with held-out FA > α = 2.915 | CRC 0/10 vs plug-in 6/10; recall −0.035 [−0.037, −0.033] | supported; 0.001 uncertifiable (CRC floor 0.248–0.263) | H33 |
| H33b | same 10 splits, B fixed in advance = 123.5 FA/cam-h (generator-derived) | held-out FA > α; recall vs empirical-B CRC | 0/10 at α 2.915 (FA 2.216), θ 0.9615–0.9642, recall −0.006 [−0.006, −0.005]; α 2.0 −0.005; α 1.0 −0.028 | supported at α 2.915 and 2.0 (partial at 1.0); CRC guarantee now exact for a loss bounded by a B fixed in advance (H33 approximate) | H33b |
| H33c | same 10 splits, fixed B, A1 alarms capped at 1 (and 2) per visitor per world | held-out FA > α; equal-θ FA cut; recall vs uncapped | capped1 0/10 at α 2.915 (FA 2.223, θ 0.9599–0.9628), 0 clipped, max 202 visitors ≤ 247; equal-θ FA cut 3.4 %; recall +0.004; 0 true alarms dropped; capped2 (B 247) −0.011 | partial (FA cut < 20 %); B = 123.5 now a valid a-priori bound → CRC exact; H45c 0.618 ranked @5 min, ship rule unchanged | H33c |
| H34 | 9 batch_v8 day cams, 12 shifts | false triggers per 24 cam-h; shifts detected | PSI/KS 1,440; z_cal 9.2 (6/12); embedding 0 (0/12) | inconclusive | H34 |
| H38 | h14b mix_300, MOT20-02 AP@640, n = 3 | AP loss FP16 / INT8 | 0.0000 / 0.0117 (range 0.0081..0.0154) | FP16 met; INT8 not met; calibration source n.s. (off-site real vs synthetic; on-site untested) | H38 |
| H43 | 5 ckpts (3 h14b + 2 H51), MOT20-02 AP75@640 | AP75 recovery, Percentile vs MinMax PTQ | 0.415 [all 5] / 0.424 [h14b only]; 0/5 regressions | PTQ leg not met (bar 0.50); QAT skipped (budget) → H43b | H43 |
| H43b | same 5 ckpts, QAT (150-iter fake-quant fine-tune, MinMax re-export) | AP75 recovery vs A1; every-ckpt AP loss ≤ 0.005 | recovery 0.366 [all 5] / 0.334 [h14b only]; 3/5 ckpts miss AP-loss bar | not met (primary bar 0.80, secondary 0.50); QAT underperforms Percentile PTQ | H43b |
| H43c | same 5 ckpts, QDQ export from QAT observers' learned ranges (`TensorQuantOverrides`, no re-fine-tune) | AP75 recovery vs A1; every-ckpt AP loss ≤ 0.005 | recovery 0.439; 4/5 ckpts meet AP-loss bar (`mix_300_s2` misses, 0.0067) | not met, either bar; ranges verified carried 5/5 | H43c |
| H43d | same 5 ckpts, QAT fine-tune 600 iters (was 150) + H43c's learned-range export | AP75 recovery vs A1, and vs H43c's 0.439 | pooled recovery **0.374** (down, not up); per-ckpt 0.331/0.531/0.782/0.077/**−0.500**; 3/5 ckpts miss AP-loss bar | not met, either bar; hypothesis (more iters recover more) refuted — effect is checkpoint-recipe-dependent, not monotonic in iterations; ship FP16, use Percentile PTQ over any QAT variant | H43d |
| H39 | 10 batch_v8 cams | world RMSE < 20 m, free f / datasheet f | 57.4 m [46.2, 68.0] / 0.96 m [0.77, 1.20] (post hoc) | free focal length fails | H39 |
| H40 | 3,002 clean cam-h | FA/cam-h naive → C; recall@10 | 70.96 [63.80, 78.30] → 4.20 [3.84, 4.57]; 0.945 → 0.100 | not met | H40 |
| H40b | fenced worlds | C clean FA; recall@10 | 0 (≤ 0.001, rule of three); 0.782 [0.736, 0.829] | not met (bar 0.9); twins patrol 0.389, maintenance 0.099 | H40b |
| H42 | 10 select folds, 1,077 events | pooled θ 0.9 − A1: ΔFA / Δrecall | +2.118 [+2.005, +2.237] / +0.069 [+0.045, +0.095] | met; the ship point is an operator-budget choice (58 §8.4) | H42 |
| H45 | 1 operator × 40 cams | realised @5 min FIFO / ranked | A1 0.511 / 0.586; pooled 0.324 / 0.504; conformal 0.571 / 0.621 | not met; conformal + ranked at 1 operator, A1 ranked at ≥ 2 | H45 |
| H53 | H40b worlds + simulated gate log / RF / PIDS | twin FA/cam-h; recall@10 | 0.488 → 0.0047 [0.0023, 0.0075]; 0.782 → 0.758 [0.710, 0.805] | not met (bar: no recall loss); tailgating defeats it (0.007) | H53 |
| H58 r3 | H12 worlds, actor-aware 30 s | A1 FA/cam-h; recall | 2.915 [2.854, 2.977]; 0.825 [0.789, 0.862] | one of three operator-budget points (58 §8.4) | 58 §7 |
| M1 | MOT20 subset | HOTA vs TrackEval | 0.4428, max \|Δ\| 1e-15 | parity met | — |
| H47 | 6 evasion techniques × 2 cams, 1–3 seeds, mask GT | ΔR YOLO26n vs matched control | crowd_cover −0.201 [−0.254, −0.154] (clip-cluster CI, AUDIT_H47); wall_hugging −0.054 (−43 % ≥ 20 px frames); dark/hi-vis/hood-colour-proxy \|Δ\| ≤ 0.003; umbrella/crawl untested; slow +0.036 | not met (1/6, need 3) | H47 |
| H56 | mock 40-cam site, 1 / 2 PTZs, 10 seeds, 3,000 + 1,184 alarms/arm; all PTZ timings assumed | acquire@3s, H39 calib, 1 PTZ; missed second alarm at 120/h | 0.901 [0.872, 0.936] ≤ 20 m / 0.802 / 0.727 [0.706, 0.747] > 30 m (exact 0.967 / 0.958 / 0.978); missed 0.369 [0.325, 0.406] (1 PTZ) vs 0.057 [0.043, 0.070] (2); far-field cause untested | not met (far leg; ≤ 20 m on point estimate only) | H56 |
| H54 | regenerated H40b worlds + staff pairs + 100 generated `fence_tailgate` worlds; est. vs true association | twin FA removed; recall@10; tailgater recall@10 | est C+abc 99.1 % [98.6, 99.5], 0.782 → 0.772; tailgater 0.056 (C+abc) / 0.685 [0.589, 0.778] (C+abcg gate counter, 96.3 % removed; H59: under H24-calibrated ID-switch noise the actor-aware score drops to 0.10 — a scoring artefact, not a fusion break) | met | H54 |
| H59 | H54 worlds + H24-calibrated identity-switch stage (157.6 / 472.7 IDSW/track-h), 10 noise seeds | calibrated/3× C+abc twin removal; calibrated recall loss vs C; calibrated tailgater recall under C+abcg | 99.1 % [98.7, 99.5] both rates (unchanged from H54); loss +0.002 [+0.000, +0.003]; tailgater 0.100 [0.071, 0.131] (base recall collapse, not a fusion-specific failure) | not met (3 of 4 criteria; only the tailgater bar, for the wrong reason) | H59 |
| H62 | H59's calibrated-arm tailgate worlds (100 worlds × 10 seeds), new `alarms.score(position_radius_m=r)` mode | C+abcg position_time recall @ r=1/2/3 m vs actor-aware (0.100)/window-only (0.739); false-credit (bystander) rate | 0.685 / **0.715** / 0.725; false-credit 14.8 % / **31.3 %** / 49.3 %; benign-arm match to actor-aware within 0.02 (0.711 vs 0.701) | partial: recall bar (≥ 0.6 at r=2 m) met; false-credit bar (≤ 5 %) not met at any r — do not adopt as the default scorer | H62 |
| H37 | 50 mock worlds × 40 identities (no renders, CLIP arms out of scope), 1500 attribute+time+place queries | uid recall@10 / precision@10, pooled-per-track vs per-epoch-segment attributes, epoch - pooled | recall@10 +0.000 [+0.000, +0.001] (clean) / -0.012 [-0.033, +0.009] (10 % attr-flip noise); precision@10 +0.000 [-0.011, 0.012] | not met — abandon condition triggered (CI includes 0 at both noise levels); mechanism confirmed at unit-test level, not at population recall@10 at this corpus scale | H37 |

## Figures for the H-numbers above (2026-09-27, audit AUDIT_FIGURES)

One-line pointer per PNG in `docs/research/figures/` not already linked from a
narrative section above or from `docs/research/64`'s Appendix A; details and
numbers are in the `32 §H<n>` row named. All CPU-only matplotlib, read only
each experiment's cached `results.json`.

* `fig_h33b.png` — H33b: CRC FA/target and recall/FA curves, empirical vs fixed B.
* `fig_h33c.png` — H33c: CRC FA/target and recall/FA curves under the per-visitor alarm cap.
* `fig_h34.png` — H34: PSI / z-cal / embedding drift score vs time on a severity-2 shift, `street_crowd_day/cam_01`.
* `fig_h39.png` — H39: foot-point world RMSE by range and per-box error scatter, free-f vs datasheet-f auto-calibration.
* `fig_h40.png` — H40: sterile-zone line-cross FA/cam-h and recall@10 by gating stage (N/A/B/C), noisy vs free tracks.
* `fig_h40b.png` — H40b: line-cross FA (log) and recall@10 by stage on the regenerated fenced worlds, with patrol/maintenance twins.
* `fig_h42.png` — H42: θ-selection policy draws (FA/cam-h, recall) for per-fold, pooled, CRC and pooled+floor policies.
* `fig_h43.png` — H43: PTQ AP75 loss (MinMax vs Percentile) and AP75-recovery fraction per checkpoint.
* `fig_h43b.png` — H43b: AP75 loss per checkpoint, MinMax PTQ vs Percentile PTQ vs QAT (fake-quant, MinMax export).
* `fig_h43c.png` — H43c: AP75 loss and recovery-vs-int8_minmax for QDQ built from QAT observers' learned ranges.
* `fig_h43d.png` — H43d: AP75 recovery at 150 vs 600 QAT iterations per checkpoint (refutes "more iterations closes more of the gap").
* `fig_h45.png` — H45: realised recall@5 min (FIFO/ranked) and operator utilisation vs operator count, at the three H42 θ points.
* `fig_h46.png` — H46: ΔAssA vs appearance weight w on batch_v8 day, MOT20-02 and the night arm.
* `fig_h46b.png` — H46b: extended w sweep to {8,16,32}+app_only, ΔIDSW, and the full 6-sequence night arm.
* `fig_h47.png` — H47: Δrecall vs zero-shot control per evasion technique, YOLO26n vs YOLOv8n.
* `fig_h51.png` — H51: per-seed MOT20-02 AP@640 by arm and paired AP-diff contrasts (equal-step dose gain).
* `fig_h52.png` — H52: per-arm AP and Holm-adjusted paired contrasts isolating the label-driven gain.
* `fig_h53.png` — H53: twin FA/cam-h removed and recall@10 under gate/RF/PIDS sensor fusion (tailgate/stolen-tag legs).
* `fig_h54.png` — H54: twin-FA-removal %, base recall@10, and generated-tailgater recall@10 under true vs estimated-position association.
* `fig_h56.png` — H56: PTZ slew-to-alarm acquisition@3s by range bin and missed-second-alarm share under contention, 1 vs 2 PTZs.
* `fig_h59.png` — H59: H54 fusion legs re-scored under H24-calibrated identity-switch noise (benign/calibrated/stress).
* `fig_h61.png` — H61: MOT20-02 AP@640, real-only vs silhouette-masked (no inpainting) vs true labels — resolves H52's background-content claim as a box-fill artefact.
* `fig_h62.png` — H62: position/time-keyed recall vs actor-aware/window-only, and false-credit rate by radius, on H59's calibrated-arm tailgate worlds.
* `fig_box_aspect.png` — box/tracking stats: MOT20 vs batch_v8 box aspect ratio by height bin, and the MOT20/batch_v8 ratio with bootstrap CIs (docs/13 "Box aspect" section, above).
* `fig_tracking_stats.png` — box/tracking stats: people-per-frame, GT visibility fraction, and track-length distributions, MOT20 vs batch_v8 (companion to `fig_box_aspect.png`, also in `docs/research/73` §tracking).
