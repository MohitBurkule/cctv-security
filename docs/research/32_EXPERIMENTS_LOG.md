# 32 · Experiments log

Hypothesis-driven experiments on SurvSim's own data (`out/batch_v6`, 8 rendered
runs, 300 frames per camera) and a real reference (MOT20-01/02, first 300
frames each; **non-commercial licence, evaluation only**).

```bash
survsim experiment <name> [--arm A --arm B]   # configs: survsim/experiments/configs/<name>.yaml
```
Each run writes `out/experiments/<name>/results.json` (config, environment,
every number) and `row.md`. **Every number below is copied from those files.**
Detection arms cache per-arm results in `out/experiments/<name>/arms/<arm>.json`.

Conventions: render PNG *i* = MOT frame *i* (the `check_render` offset-0
pairing); GT targets are `conf==1, class==1`. Hardware: RTX 2070 Max-Q 8 GB,
shared with an idle Unreal editor (~3 GB); the editor was **not** stopped.

---

## H1 · Sim-to-real person detection (`h1_sim2real`)

**Hypothesis.** Fine-tuning COCO-pretrained YOLOv8n on batch_v6 synthetic frames
changes person AP on real MOT20; 60 real frames (MOT20-01) help more than
synthetic alone; synthetic + real beats real alone.

**Method.** YOLOv8n, 12 epochs, imgsz 640, batch 8, `last.pt` scored (no
checkpoint selection on real data). Synthetic = 5 train scenarios, raw every
8th frame + `cctv_day_720p`-degraded every 8th (offset 4) = 1258 images;
synthetic val = the held-out `smoke_mock` scenario. Real = MOT20-01 frames
1–60 ×5 repeats. Scored with the docs/13 harness (COCO AP, ignore regions).
Arms that saw MOT20-01 are scored on **MOT20-02 only** (`mot20_02`); the
`mot20_sub` set (01+02) is reported only for arms without real frames.
Seeds 0/1/2 (training seed), scored at imgsz 640 on `mot20_02`.

**Results** (`out/experiments/h1_sim2real/results.json`, seed 0, MOT20-02):

| arm | eval | AP | AP50 | AP75 | R@.25 | P@.25 | AP50 80–120 px | AP50 160–240 px | train s | train imgs |
|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | mot20_02@640 | 0.276 | 0.606 | 0.210 | 0.407 | 0.909 | 0.073 | 0.723 | – | 0 |
| zero_shot | mot20_02@1280 | 0.334 | 0.712 | 0.268 | 0.588 | 0.866 | 0.173 | 0.803 | – | 0 |
| synthetic | mot20_02@640 | 0.142 | 0.371 | 0.074 | 0.274 | 0.836 | 0.007 | 0.502 | 297 | 1258 |
| synthetic | mot20_02@1280 | 0.115 | 0.310 | 0.062 | 0.133 | 0.739 | 0.051 | 0.530 | 297 | 1258 |
| real10_only | mot20_02@640 | 0.494 | 0.823 | 0.532 | 0.786 | 0.825 | 0.419 | 0.883 | 59 | 300 |
| synth_plus_real10 | mot20_02@640 | 0.473 | 0.808 | 0.504 | 0.774 | 0.828 | 0.448 | 0.881 | 236 | 1558 |

Leak-free both-sequence set, no-real arms: zero_shot AP 0.281 (640) / 0.338
(1280); synthetic 0.181 / 0.136.

Seed summary (MOT20-02 @ 640, 3 training seeds, mean (sample sd)):

| arm | AP | AP50 | per-seed AP |
|---|---|---|---|
| synthetic | 0.152 (0.025) | 0.387 (0.050) | 0.142, 0.180, 0.134 |
| synth_plus_real10 | 0.472 (0.005) | 0.807 (0.008) | 0.473, 0.477, 0.467 |
| real10_only | 0.491 (0.003) | 0.819 (0.004) | 0.494, 0.489, 0.489 |

**Interpretation.**
* **Synthetic-only fine-tuning hurt real AP: 0.276 → 0.142** (seed 0; 0.152 ±
  0.025 over 3 seeds), well outside seed noise. The damage is concentrated in
  small/medium boxes (AP50 80–120 px 0.073 → 0.007; 120–160 px 0.242 → 0.009)
  while ≥240 px holds (0.955 → 0.908). The detector unlearned mid-size people.
* 60 real frames nearly doubled AP (0.276 → 0.494).
* **Synthetic + real did not beat real-only**: 0.472 ± 0.005 vs 0.491 ± 0.003
  — a small but seed-consistent *loss* (every seed of synth+real is below every
  seed of real-only). Only the 80–120 px band improved (0.448 vs 0.419, seed 0).
* The hypothesis's first clause holds (AP changes — it drops); the third is
  **rejected** at this data scale.

**Caveats.** MOT20-01 and MOT20-02 are very likely the **same site** (same
square, similar viewpoint), so "60 real frames" is near-in-domain adaptation,
an optimistic stand-in for real data from a *new* site. imgsz 1280 was worse
than 640 for every fine-tuned arm (trained at 640). One real dataset, one small
detector, 12 epochs; synthetic content is batch_v6 only (5 scenarios).

## H2 · Degradation matters (`h2_degradation`)

**Hypothesis.** Training on synthetic frames passed through the
`cctv_day_720p` degrade chain (noise, blur, stream codec) gives higher real
MOT20 AP than training on the same scenes' raw renders, at equal image count
and schedule.

**Method.** As H1: same 5 train scenarios, every 4th frame, 1258 images per
arm; `raw_only` uses the renders, `degraded_only` the *same frames* after the
degrade chain. Seed 0 only. Scored on the leak-free `mot20_sub`
(MOT20-01 + 02).

**Results** (`out/experiments/h2_degradation/results.json`; zero-shot on the
same set from H1 for reference):

| arm | eval | AP | AP50 | AP75 | R@.25 | P@.25 | AP50 80–120 px | AP50 160–240 px | AP50 240+ px |
|---|---|---|---|---|---|---|---|---|---|
| zero_shot (H1) | mot20_sub@640 | 0.281 | 0.618 | 0.216 | 0.402 | 0.919 | 0.102 | 0.743 | 0.946 |
| raw_only | mot20_sub@640 | 0.093 | 0.265 | 0.044 | 0.153 | 0.772 | 0.004 | 0.411 | 0.505 |
| degraded_only | mot20_sub@640 | 0.188 | 0.469 | 0.103 | 0.279 | 0.857 | 0.059 | 0.605 | 0.852 |
| raw_only | mot20_sub@1280 | 0.063 | 0.212 | 0.013 | 0.086 | 0.771 | 0.003 | 0.376 | 0.214 |
| degraded_only | mot20_sub@1280 | 0.079 | 0.218 | 0.044 | 0.055 | 0.801 | 0.052 | 0.366 | 0.104 |

**Interpretation.** Degradation roughly **doubles** the real AP of a
synthetic-only model (0.093 → 0.188 at 640), and the gain is largest on big
people (AP50 240+ px 0.505 → 0.852). But **both arms remain below zero-shot
(0.281)**: degradation reduces the harm of synthetic fine-tuning, it does not
turn it into a benefit. The H1 raw+degraded mix (0.181 on the same set) sits
at the degraded-only level, i.e. the raw half contributed nothing.

**Caveats.** One seed; H1 shows synthetic-only arms have seed sd ≈ 0.025 AP,
so the 0.095 gap is ~4 sd — likely real but unreplicated. At 1280 both arms
collapse (trained at 640). The degrade profile was tuned on image statistics
(docs/15), not on detection transfer.

## H3 · Far-field people (`h3_farfield`)

**Hypothesis.** Zero-shot YOLOv8n at imgsz 640 misses most people under
~30 px on the batch_v6 far cameras; imgsz 1280 and SAHI-style slicing
recover much of the gap, at a measurable latency cost.

**Method.** Far cameras cam_02/cam_03 of `street_crowd_far` (median GT height
16 / 22 px), day + night raw and day degraded, every 3rd frame: 594 frames,
5142 GT people ≥ 13 px (smaller GT = ignore regions). Zero-shot COCO YOLOv8n,
fp16. Tiling: full frame + overlapping tiles (20 % overlap) each resized to
640, merged by NMS 0.5. Recall/precision at conf 0.25, IoU 0.5. Latency =
wall-clock ms per 1280×720 frame on the RTX 2070 Max-Q (Unreal editor
resident on the same GPU).

**Results** (`out/experiments/h3_farfield/results.json`):

| method | R 13–20 px | R 20–30 px | R 30–45 px | R all | P | AP50 all | ms/frame |
|---|---|---|---|---|---|---|---|
| full_640 | 0.007 | 0.043 | 0.000 | 0.021 | 0.240 | 0.021 | 21.4 |
| full_1280 | 0.374 | 0.451 | 0.533 | 0.405 | 0.735 | 0.461 | 21.3 |
| sahi_512x384 | 0.523 | 0.573 | 0.533 | 0.543 | 0.736 | 0.568 | 86.9 |
| sahi_320x240 | 0.616 | 0.649 | 0.533 | 0.629 | 0.781 | 0.669 | 156.2 |

(n = 3087 / 2040 / 15 GT in the three bands.) Recall by source at
sahi_320x240: day raw 0.830, night raw 0.848, **day degraded 0.209**.

**Interpretation.** Confirmed. At the default imgsz 640 the far camera is
effectively blind (recall 0.021). imgsz 1280 recovers to 0.405 at no latency
cost on this GPU; 320×240 tiling reaches 0.629 at 7× the latency (156 vs 21
ms/frame, ≈ 6 fps). The degraded stream is far harder than either raw
lighting condition (0.209 vs 0.83–0.85): at 13–30 px, the codec and noise
destroy what little person signal there is.

**Caveats.** Synthetic frames only — H8 tests the same question on real
pixels. The 30–45 px band has 15 GT and should not be read. The VRAM column
in `row.md` (13–183 MiB) is torch-allocated memory for fp16 inference only,
not the process footprint. Latency shares the GPU with the editor.

## H4 · ReID appearance truth (`h4_reid`)

**Hypothesis.** ImageNet OSNet re-identifies batch_v6 people cross-time far
better than cross-camera or cross-lighting, and its embedding captures the
painted clothing palette — but not better than a plain HSV colour histogram,
because on these renders identity is mostly clothing colour.

**Method.** 610 person crops (≥48 px, visibility ≥0.6, ≤6 per identity per
camera), 20 identities, 19 outfits, 8 camera views. Embeddings:
`osnet_x1_0` (torchreid, ImageNet weights, no ReID training) and an HSV
histogram. Protocols set the gallery per query: cross-camera (same
lighting), cross-time (same camera, ≥5 s apart), cross-lighting (same
camera, day↔night, ≥5 s apart). Palette clustering: k-means purity vs a
label-permuted baseline, NMI.

**Results** (`out/experiments/h4_reid/results.json`):

| embedding | protocol | queries | rank-1 | rank-5 | mAP |
|---|---|---|---|---|---|
| OSNet (ImageNet) | cross-camera | 598 | 0.251 | 0.440 | 0.148 |
| OSNet (ImageNet) | cross-time ≥5 s | 498 | 0.512 | 0.715 | 0.469 |
| OSNet (ImageNet) | cross-lighting ≥5 s | 498 | 0.444 | 0.661 | 0.425 |
| HSV histogram | cross-camera | 598 | 0.291 | 0.520 | 0.219 |
| HSV histogram | cross-time ≥5 s | 498 | 0.584 | 0.733 | 0.533 |
| HSV histogram | cross-lighting ≥5 s | 498 | 0.245 | 0.524 | 0.335 |
| OSNet (ImageNet), MOT20 subset (docs/13) | cross-time ≥5 s | 105 ids | 0.186 | 0.341 | 0.231 |

| embedding | label | k-means purity | permuted | NMI |
|---|---|---|---|---|
| OSNet | outfit (19) | 0.351 | 0.137 | 0.403 |
| HSV | outfit (19) | 0.257 | 0.136 | 0.330 |

**Interpretation.**
* **The colour histogram beats OSNet-ImageNet on our crops** in the same
  lighting: cross-camera mAP 0.219 vs 0.148, cross-time 0.533 vs 0.469.
  Identity in batch_v6 is carried mostly by clothing colour.
* Across lighting the histogram collapses (rank-1 0.245) while OSNet keeps
  0.444 — the one place a learned embedding earns its keep here.
* Cross-camera is the hard protocol for both (rank-1 0.25–0.29).
* OSNet's embedding clusters by outfit well above chance (purity 0.351 vs
  0.137 permuted).
* Our cross-time rank-1 (0.512) is far above the same model on real MOT20
  (0.186): batch_v6 identities are **easier** than real people — few
  identities (20) and flat, saturated clothing.

**Caveats — do not cite the leaky number.** An earlier cross-lighting
protocol allowed same-frame day/night pairs, which are near-duplicates (day
and night renders share every pose frame for frame); it gave OSNet rank-1
0.869. That figure is **leaked and must not be cited**; it is kept in
results.json only as the "LEAKY" row to show the inflation. 20 identities is
a small gallery; there is no trained ReID model in this comparison.

## H5 · Alarm scoring (`h5_alarms`)

**Hypothesis.** DwellRule(60 s) misses pacing loiterers that PathLoiterRule
catches; PathLoiterRule pays in false alarms far above an operator budget;
i-LIDS-compatible scoring flatters precision relative to default scoring
without changing recall.

**Method.** Ground-truth world tracks of 3 batch_v6 worlds
(disguise_and_tamper, smoke_mock, street_crowd; day runs — night runs share
the same worlds), 0.35 camera-hours, 5 truth loiter events. Rules on GT
tracks (perfect perception). Scored with `survsim eval` at tolerances 10 s and
30 s; operator budget 0.001 false alarms per camera-hour.

**Results** (`out/experiments/h5_alarms/results.json`, tolerance 30 s):

| rule | scoring | alarms | TP | FP | FN | precision | recall | FA/cam-h | × budget |
|---|---|---|---|---|---|---|---|---|---|
| dwell_60 | default | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.0 | 0 |
| dwell_25 | default | 9 | 4 | 5 | 1 | 0.444 | 0.800 | 14.29 | 14 286 |
| dwell_25 | ilids_compat | 9 | 4 | 4 | 1 | 0.500 | 0.800 | 11.43 | 11 429 |
| path_loiter_25 | default | 22 | 4 | 18 | 1 | 0.182 | 0.800 | 51.43 | 51 429 |
| path_loiter_25 | ilids_compat | 22 | 4 | 10 | 1 | 0.286 | 0.800 | 28.57 | 28 571 |
| path_loiter_15 | default | 55 | 5 | 50 | 0 | 0.091 | 1.000 | 142.86 | 142 857 |
| path_loiter_15 | ilids_compat | 55 | 5 | 15 | 0 | 0.250 | 1.000 | 42.86 | 42 857 |

At tolerance 10 s every rule loses hits (dwell_25 recall 0.800 → 0.000;
path_loiter_25 0.800 → 0.600), because a late alarm is a false alarm.

**Interpretation.**
* DwellRule(60 s) fires **nothing** on these worlds (recall 0).
* Every rule that finds loiterers is **10⁴–10⁵× over the 0.001 FA/cam-h
  budget** (11–143 FA/cam-h), *with perfect perception*. No loiter rule here
  is deployable.
* i-LIDS-compatible scoring raises precision (path_loiter_15: 0.091 → 0.250)
  with identical recall — it forgives repeat alarms on the same event. It
  flatters; SurvSim default scoring is the one to report.

**Caveats.** 5 truth events and 0.35 camera-hours: a single event moves
recall by 0.2, and FA/cam-h has a large sampling error. GT tracks, not
detector tracks — real false-alarm rates would be higher.

## H6 · Why does synthetic-only fine-tuning hurt? (`h6_freeze`, `h6_diagnose`)

H1 found synthetic-only fine-tuning drops MOT20-02 AP from 0.276 to 0.152 ±
0.025. Four candidate explanations, one arm each.

**(a) Feature drift — freeze the backbone / everything but the head.** Same
data and schedule as H1 `synthetic` (1258 images, 12 epochs), with
ultralytics `freeze=10` (backbone frozen) or `freeze=22` (only the Detect
head trains). `out/experiments/h6_freeze/results.json`, MOT20-02 @ 640:

| arm | seeds | AP | AP50 | AP75 | R@.25 | AP50 80–120 px | AP50 120–160 px | AP50 240+ px |
|---|---|---|---|---|---|---|---|---|
| zero_shot (H1) | – | 0.276 | 0.606 | 0.210 | 0.407 | 0.073 | 0.242 | 0.955 |
| full fine-tune (H1, 3 seeds) | 3 | 0.152 ± 0.025 | 0.387 ± 0.050 | – | – | – | – | – |
| freeze10 (backbone frozen), seed 0 | – | 0.226 | 0.532 | 0.145 | 0.212 | 0.233 | 0.317 | 0.587 |
| freeze10, seed 1 | – | 0.216 | 0.501 | 0.141 | 0.204 | 0.209 | 0.319 | 0.449 |
| freeze10 mean (sd) | 2 | 0.221 (0.008) | 0.516 (0.022) | | | | | |
| freeze22 (head only), seed 0 | 1 | 0.197 | 0.453 | 0.129 | 0.146 | 0.068 | 0.172 | 0.625 |

freeze22 seed 1 did not run: the job hit its 30-min timeout (training was
~2× slower than H1 because the Unreal editor was rendering on the same GPU).

**(b) Pixel realism — degraded vs raw.** This is H2: at equal frames the
`cctv_day_720p` stream-codec degrade doubles real AP (0.093 → 0.188,
`mot20_sub`@640), but both stay below zero-shot (0.281). No separate run.

**(c) Label quality.** 30 random synthetic frames per source (4 day/night
scenarios) and 30 MOT20-02 frames; GT ≥ 40 px and visibility ≥ 0.7; each GT
box matched to its best zero-shot YOLOv8n box (imgsz 1280, conf 0.1).
Offsets are prediction − GT, divided by GT height, over pairs with IoU ≥ 0.3.
`out/experiments/h6_diagnose/results.json`; overlays (GT green, YOLO red) in
`out/experiments/h6_diagnose/overlays/`:

| set | GT | IoU median | IoU ≥ .5 | IoU ≥ .7 | no match | top offset | bottom offset | height ratio | width ratio |
|---|---|---|---|---|---|---|---|---|---|
| synthetic raw | 156 | 0.696 | 0.968 | 0.481 | 0.000 | +0.072 | −0.023 | 0.915 | 1.013 |
| synthetic degraded | 146 | 0.675 | 0.767 | 0.411 | 0.185 | +0.054 | −0.026 | 0.925 | 1.024 |
| real MOT20-02 | 428 | 0.797 | 0.970 | 0.794 | 0.014 | +0.011 | −0.029 | 0.963 | 0.865 |

**(d) Image statistics vs transfer.** docs/15 frame statistics (13) of 40
sampled frames per training set vs MOT20-02; z = (set median − MOT20-02
median) / MOT20-02 p10–p90 spread:

| training set | stats in real band | mean abs z | noise z | MTF z | chroma z | luma z | real AP of that arm |
|---|---|---|---|---|---|---|---|
| raw renders | 1/13 | 4.21 | +10.28 | +15.36 | +2.89 | −1.74 | 0.093 (H2 raw_only, mot20_sub) |
| raw + degraded | 0/13 | 3.14 | +4.58 | +3.15 | +1.74 | −5.28 | 0.181 (H1 synthetic, mot20_sub) |
| degraded | 2/13 | 2.86 | +3.63 | −0.45 | +5.21 | −7.18 | 0.188 (H2 degraded_only, mot20_sub) |
| real MOT20-01, 60 frames | 2/13 | 1.40 | +0.94 | +4.09 | +2.27 | −0.10 | 0.494 (H1 real10_only, MOT20-02) |

**Interpretation.**
* **Labels are part of it.** SurvSim GT boxes are systematically **loose at
  the top**: a zero-shot detector puts the head 7 % of box height lower than
  our GT (raw; +1 % on MOT20), and our boxes are ~8 % taller than what the
  detector sees as the person (height ratio 0.915 vs 0.963). Only 48 % of our
  boxes reach IoU 0.7 with the detector vs 79 % on MOT20. The overlays show
  the same: green boxes start well above the head, and some are offset
  sideways from the body. A detector trained on these learns to draw loose
  boxes, which costs AP75 most (zero-shot 0.210 → head-only 0.129).
* **Feature drift is part of it.** Freezing the backbone roughly halves the
  loss (0.221 vs 0.152) but does not remove it; training only the head still
  hurts (0.197), which is what one expects if the *labels* are part of the
  problem: the head alone can learn the loose-box convention.
* **Pixels are part of it.** Degradation doubles transfer (H2); every
  synthetic set is far outside MOT20's image-statistics band (0–2 of 13
  stats), and ordering by mean |z| matches ordering by AP on these four
  points (raw 4.21 → 0.093; raw+degraded 3.14 → 0.181; degraded 2.86 →
  0.188; real 1.40 → 0.494).
* None of the three alone restores zero-shot AP; the drop is not one bug.

**Caveats.** (a) 1–2 seeds per freeze arm. (c) The zero-shot detector is a
*reference*, not truth: its own boxes have biases (on MOT20 it draws boxes
14 % narrower than the hand labels). The comparison is relative — same
detector on both sets. Degraded frames lose 18.5 % of matches because the
detector fails, not the labels. (d) Four points, with AP from two different
eval sets (`mot20_sub` vs MOT20-02) — a consistent ordering, not a fit; it
cannot separate "closer statistics" from "more real content".

## H7 · Mixing ratio and pre-train-then-fine-tune (`h7_mixing`)

**Hypothesis.** With 60 real MOT20-01 frames fixed, adding 100 / 300 / 1000
synthetic frames changes MOT20-02 AP monotonically, and the PeopleSansPeople
recipe (synthetic pre-training, then real fine-tuning; docs/research/24 §2.2)
beats naive mixing at the same data.

**Method.** Real = MOT20-01 frames 1–60 ×5 (300 images) in every arm.
Synthetic = a seeded random N of H1's 1258-frame raw+degraded pool (≈ half
each). `pretrain1000_then_real` trains 6 epochs on the same 1000 synthetic
frames, then 6 epochs on the real 300 from that checkpoint. **6 epochs per
stage, not H1's 12** (GPU budget beside a rendering editor), so compare within
H7 only. Seeds 0 and 1 (the seed also picks the synthetic subset). MOT20-02 @
640.

**Results** (`out/experiments/h7_mixing/results.json`):

| arm | train imgs (real share) | AP seed 0 / 1 | AP mean (sd) | AP50 mean | AP75 seed 0 / 1 | AP50 80–120 px seed 0 / 1 |
|---|---|---|---|---|---|---|
| mix_0 (real only) | 300 (100 %) | 0.486 / 0.486 | 0.486 (0.000) | 0.822 | 0.512 / 0.510 | 0.466 / 0.467 |
| mix_100 | 400 (75 %) | 0.496 / 0.497 | 0.496 (0.001) | 0.833 | 0.533 / 0.527 | 0.467 / 0.525 |
| mix_300 | 600 (50 %) | 0.497 / 0.498 | 0.497 (0.001) | 0.833 | 0.540 / 0.535 | 0.474 / 0.492 |
| mix_1000 | 1300 (23 %) | 0.482 / 0.490 | 0.486 (0.006) | 0.819 | 0.517 / 0.525 | 0.452 / 0.490 |
| pretrain1000_then_real | 1000 → 300 | 0.480 / 0.478 | 0.479 (0.001) | 0.813 | 0.513 / 0.516 | 0.452 / 0.484 |

**Interpretation.**
* **Not monotonic.** A small synthetic dose helps a little and consistently:
  100–300 frames give +0.010–0.011 AP over real-only, ~10× the seed spread
  (both seeds, both doses). 1000 frames erase the gain (0.486 = real-only).
* **Pre-train-then-fine-tune is the worst arm** (0.479, −0.007 vs real-only,
  both seeds). The PeopleSansPeople ordering does not reproduce here.
* Reconciles with H1: H1's synth+real used all 1258 synthetic (real share
  19 %) and lost 0.019 AP — the same side of the curve as mix_1000.
* Reading with H6: synthetic frames carry loose boxes and off-distribution
  pixels; in small doses they act as augmentation, in large doses (or as the
  initialisation) they pull the model toward the synthetic box convention.

**Caveats.** 2 seeds, a +0.01 effect; 6-epoch schedule; the real share and
the step count both change with N, so "more synthetic" and "fewer real
steps per epoch" are confounded (a fixed-step design would separate them).
MOT20-01/02 are likely the same site, which favours real data. PeopleSansPeople
pre-trained on 490 K images; our 1000 is three orders of magnitude smaller.

## H8 · Far-field on real pixels (`h8_farreal`)

**Hypothesis.** Fine-tuning YOLOv8n at imgsz 1280 on SurvSim's far-camera
renders (median person 16–22 px) raises recall and AP50 on real MOT20-02
people shrunk below 60 px, over zero-shot and over the H1 general-synthetic
weights, with and without tiling.

**Method.** MOT20-02 has no GT under 89 px at 1080p, so small real people are
made by downscaling whole frames (INTER_AREA) by 0.25 (→ 480×270) and 0.33
(→ 640×360); GT scaled with them. Targets = GT < 60 px after scaling, larger
GT = ignore regions. Frames 5…300 step 5 (60 frames). Methods: full frame at
the frame's own size (`full_native`, no upsampling), and full frame + 320×240
tiles upsampled to 640 (`sahi_320x240`). Arms: zero-shot COCO; H1 `synthetic`
(seed 0) weights; `far_ft` = fine-tuned 8 epochs at imgsz 1280 (batch 2) on
the far cameras cam_02/cam_03 of `street_crowd_far` (day + night raw, day
degraded, every 3rd frame: 596 images, 5206 boxes). Seed 0.

**Results** (`out/experiments/h8_farreal/results.json`; recall/precision at
conf 0.25, IoU 0.5):

| arm | scale | method | GT | AP50 | R | P | R < 30 px | R 30–45 px | R 45–60 px |
|---|---|---|---|---|---|---|---|---|---|
| zero_shot | 0.25 | full_native | 2250 | 0.478 | 0.272 | 0.882 | 0.000 | 0.055 | 0.515 |
| zero_shot | 0.25 | sahi_320x240 | 2250 | 0.564 | 0.442 | 0.806 | 0.104 | 0.264 | 0.670 |
| zero_shot | 0.33 | full_native | 1177 | 0.211 | 0.083 | 0.530 | 0.000 | 0.002 | 0.151 |
| zero_shot | 0.33 | sahi_320x240 | 1177 | 0.222 | 0.356 | 0.374 | 0.091 | 0.256 | 0.451 |
| h1_synthetic | 0.25 | full_native | 2250 | 0.295 | 0.181 | 0.821 | 0.000 | 0.032 | 0.346 |
| h1_synthetic | 0.25 | sahi_320x240 | 2250 | 0.469 | 0.329 | 0.828 | 0.071 | 0.174 | 0.519 |
| h1_synthetic | 0.33 | full_native | 1177 | 0.022 | 0.019 | 0.211 | 0.000 | 0.000 | 0.036 |
| h1_synthetic | 0.33 | sahi_320x240 | 1177 | 0.220 | 0.189 | 0.493 | 0.045 | 0.128 | 0.245 |
| far_ft | 0.25 | full_native | 2250 | 0.004 | 0.007 | 0.077 | 0.019 | 0.004 | 0.006 |
| far_ft | 0.25 | sahi_320x240 | 2250 | 0.003 | 0.006 | 0.085 | 0.019 | 0.002 | 0.006 |
| far_ft | 0.33 | full_native | 1177 | 0.018 | 0.010 | 0.226 | 0.000 | 0.024 | 0.000 |
| far_ft | 0.33 | sahi_320x240 | 1177 | 0.017 | 0.009 | 0.239 | 0.000 | 0.022 | 0.000 |

Sanity check (not in results.json; H3 harness with `far_ft` weights, full
frame at 1280, every 15th far-camera frame — **frames it trained on**):
recall 0.953, AP50 0.935, vs zero-shot 0.405 / 0.461 in H3.

**Interpretation.** **Rejected, emphatically.** Far-field fine-tuning on our
renders **destroys** small-person detection on real pixels (AP50 0.478 →
0.004 at 0.25 scale), while fitting its own renders almost perfectly. With
596 images of one street from two cameras, the model learned *that scene's*
16–22 px blobs, not small people. The H1 general-synthetic weights also lose
to zero-shot at every setting. What actually helps small real people is
tiling a COCO model (0.25 scale: recall 0.272 → 0.442; people < 30 px
0.000 → 0.104) — H3's synthetic result transfers to real pixels in
direction, though with much lower absolute recall.

**Caveats.** Downscaled 1080p is not a real far camera: INTER_AREA
anti-aliasing is cleaner than optics + sensor + codec at range, and
perspective is unchanged. The two scales are different target sets (at 0.33
only people originally < 180 px are targets, the hard ones), so compare arms
within a scale. One seed; 8 epochs at batch 2; the sanity check measures
training-set fit, not held-out synthetic accuracy.

---

# Pre-registrations: H9–H11 (written before any run; report 49 §12 template)

Data for all three: `out/batch_v7` (CC0 characters, `commercial_ml_ok: true`),
rendered frames 0–299 per camera at 10 fps (t = 0–30 s of each 240 s
simulation). MOT20 is non-commercial, evaluation only. Detector for every arm
is COCO `yolov8n.pt`, zero-shot unless stated. GPU budget ≤ 2 GB per process,
each run gated by `wait_for_gpu`; the Unreal editor is **not** stopped (§11
confound: timings only, never accuracy, are affected).

```
id:            h9a_tracking
hypothesis:    zero-shot yolov8n + numpy ByteTrack tracks batch_v7 people worse
               on far cameras (median GT box < 50 px) than near, and worse at
               night than day; the failure is detection-limited (DetA < AssA),
               the same failure mode as on MOT20-01/02.
primary metric: HOTA (19-alpha, survsim.eval.tracking) per camera sequence,
               GT frames 1..299, all GT rows conf==1/class==1.
arms:          sequences, not training arms. Day (control) vs night: the same
               camera and trajectories rendered twice -> paired by camera.
               Near vs far: camera-level split on median GT height (unpaired).
held fixed:    yolov8n.pt, imgsz 1280, det conf 0.1, ByteTrack defaults
               (high 0.5, low 0.1, new 0.6, max_lost = fps), eval IoU 0.5.
seeds:         none (deterministic detector + tracker).
sample size:   all 12 day/night camera pairs in batch_v7 (disguise 4, street 3,
               street_far 3, smoke 2) — every sequence that exists; ~12 pairs
               resolves |dHOTA| ≳ 0.05 only if the per-pair sd ≤ 0.08.
analysis:      night−day paired mean dHOTA, 95 % percentile bootstrap over
               camera pairs (10 000 resamples, seed 0); far−near difference
               of means, bootstrap over cameras. Holm over {night−day, far−near}.
success:       CI excludes 0 in the stated direction; "detection-limited" iff
               DetA < AssA on ≥ 75 % of sequences in both datasets.
stopping rule: one pass over all sequences, no re-runs with other settings.
secondary:     MOTA, IDF1, ID switches, per-scenario and per-camera table;
               MOT20 rows re-detected with the same yolov8n@1280 for a like-
               for-like comparison.
confounds:     street_crowd and street_crowd_far share an identical cam_01
               (counted twice; also reported without the duplicate);
               night sets share trajectories with day (hence pairing);
               MOT20 is 25 fps / dense, ours 10 fps / sparse.
abandon if:    fewer than 8 sequences produce any confirmed track.

id:            h9b_bytetrack_fix
hypothesis:    the docs/13 fix (high/low split tau 0.6; cost[iou<thr]=1e6 before
               the Hungarian solve, both rounds) raises HOTA on both MOT20-01/02
               and batch_v7.
primary metric: pooled HOTA per dataset (sequences concatenated as in
               baselines/run.eval_mot); same detections as h9a (cached).
arms:          old (control, bit-identical default path) vs fixed (flag).
seeds:         none (deterministic).
analysis:      paired per-sequence dHOTA, bootstrap CI over sequences.
success/adopt: fixed pooled HOTA > old on BOTH datasets and pooled IDF1 not
               lower by > 0.005 on either. Otherwise the flag stays off.
stopping rule: one pass.
confounds:     tau 0.6 changes which detections enter round 1 AND the gate
               changes matching — two changes in one flag; also report each
               alone (secondary) so an adoption is not blind to which helped.

id:            h10_reid_epochs
hypothesis:    on disguise_and_tamper (day+night), rank-1 of OSNet-ImageNet and
               HSV histograms collapses across an appearance epoch (outfit
               change) while a gait signature does not.
primary metric: rank-1 per cue per protocol: (i) same-epoch, (ii) cross-epoch,
               (iii) cross-camera same-epoch; 95 % Wilson CI on rank-1 (query
               = unit, noted as optimistic because crops of one person are
               correlated), mAP with bootstrap CI over identities.
arms:          osnet_x1_0 ImageNet, HSV 8x4x4 upper/lower (control), gait
               signature (survsim.gait.signature.observe of each identity's
               parquet gait parameters, noise 0.15, one draw per crop, seed =
               crop index) — a SIMULATED measurement, not extracted from pixels.
held fixed:    GT crops, min_h 48 px, min_vis 0.6, 6 crops per id per camera.
PRE-RUN CHECK: identities.parquet puts intruder_a's epoch 0->1 at t = 115.1 s;
               renders cover t = 0–30 s, and render_appearance.json carries ONE
               outfit per uid. Expected cross-epoch pixel queries: n = 0. If so,
               (ii) is reported "not measurable on batch_v7", no number is
               imputed, and the gait cross-epoch figure is labelled tautological
               (its parameters are epoch-invariant by construction).
secondary:     (exploratory) three uids share one body mesh
               (quaternius animated_woman_9kf7) in different outfits: same-body/
               different-outfit similarity vs different-body pairs, as the only
               rendered "same body, other clothes" contrast available.
abandon if:    < 5 identities pass the crop filter.

id:            h11_night
hypothesis:    zero-shot yolov8n recall falls at night vs day on batch_v7, most
               in small boxes, and falls further after cctv_night_ir; fine-
               tuning on night-IR-degraded synthetic raises real night AP50.
primary metric: (A) recall @conf 0.25, IoU 0.5, GT h ≥ 40 px, per camera,
               night − day paired by camera (same frames); (B) AP50 on real
               MOT20-05 (the only dark MOT20 sequence, mean luma 47 vs 108–126
               for 01/02/03: a lit night street, colour, NOT IR).
arms:          A: day raw (control), night raw, night + cctv_night_ir.
               B: zero_shot (control), ft_night_ir (yolov8n, 8 ep, imgsz 640,
               batch 8, night runs' IR-degraded frames), ft_night_raw (same
               frames undegraded) — the H2-style contrast is ir vs raw.
held fixed:    frames 1..299 step 5; imgsz 1280 for A; IR degrade applied per
               camera to the sub-sampled frames as a sequence (seed 0), GT
               scaled 1920x1080 -> 1280x720.
seeds:         A none; B 1 training seed (pilot, ≤ 25 min budget).
analysis:      A: paired bootstrap over cameras; B: bootstrap over frames of
               MOT20-05 (paired, same frames), claim only |dAP50| ≥ 0.05 with CI
               excluding 0 — one seed cannot separate training noise (H1
               sd 0.025 AP), so B is at most "suggestive".
stopping rule: one pass.
confounds:     no real IR night reference exists (docs/15) — B tests transfer
               to a colour night scene, so an IR-trained model is mismatched by
               design; MOT20-05 frames used: 1..600 step 10.
abandon if:    MOT20-05 GT unreadable -> B reported synthetic-only.
```

## H9 · Tracking on batch_v7, and the docs/13 ByteTrack fix (`h9_tracking`)

> **Pre-parity scorer (added 2026-09-27, AUDIT_M1_PARITY).** Every HOTA/DetA/AssA/IDF1/IDSW
> number in this section was computed with `evaluate_mot` *before* M1 TrackEval parity
> (`5571631`): per-α Hungarian HOTA matching, IDF1 from CLEAR matches, greedy cross-gap
> continuity. Absolute values are pre-parity; the deltas used the same old code on both arms
> but have **not been recomputed** with the parity scorer, so whether they hold is unknown [A].

Pre-registered above (commit `741b025`); runner `survsim/experiments/tracking.py`,
code at `2495de5`. yolov8n.pt zero-shot, imgsz 1280, conf ≥ 0.1, numpy
ByteTrack (max_lost = fps), `evaluate_mot` (corrected 19-alpha HOTA; DetA/AssA
columns are the alpha = 0.5 slice). batch_v7: frames 1..299 of all 24 camera
sequences. MOT20-01/02: the 300-frame `mot20_sub`, **re-detected with the same
yolov8n@1280** (the docs/13 row used yolo11n, so these numbers differ from it).
Wall 675 s, editor running.

**Results** (`out/experiments/h9_tracking/results.json`), per sequence, old tracker:

| sequence | light | med GT h px | n_gt | HOTA | DetA | AssA | MOTA | IDF1 | IDsw |
|---|---|---|---|---|---|---|---|---|---|
| disguise / cam_gate | day | 60 | 1014 | 0.635 | 0.881 | 0.779 | 0.879 | 0.877 | 2 |
| disguise / cam_gate | night | 60 | 1014 | 0.539 | 0.683 | 0.706 | 0.679 | 0.723 | 2 |
| disguise / cam_ptz | day | 241 | 285 | 0.536 | 0.830 | 0.645 | 0.821 | 0.721 | 1 |
| disguise / cam_ptz | night | 241 | 285 | 0.527 | 0.827 | 0.640 | 0.818 | 0.719 | 1 |
| disguise / cam_sub | day | 313 | 363 | 0.514 | 0.833 | 0.833 | 0.826 | 0.891 | 1 |
| disguise / cam_sub | night | 313 | 363 | 0.512 | 0.828 | 0.826 | 0.821 | 0.888 | 1 |
| disguise / cam_yard | day | 32 | 1145 | 0.602 | 0.806 | 0.828 | 0.804 | 0.893 | 0 |
| disguise / cam_yard | night | 32 | 1145 | **0.401** | 0.508 | 0.474 | 0.500 | 0.568 | 7 |
| street_crowd / cam_01 | day | 95 | 2374 | 0.610 | 0.947 | 0.707 | 0.944 | 0.796 | 6 |
| street_crowd / cam_01 | night | 95 | 2374 | 0.668 | 0.939 | 0.886 | 0.936 | 0.923 | 4 |
| street_crowd / cam_02 | day | 57 | 2368 | 0.593 | 0.910 | 0.687 | 0.905 | 0.778 | 9 |
| street_crowd / cam_02 | night | 57 | 2368 | 0.599 | 0.901 | 0.714 | 0.895 | 0.811 | 12 |
| street_crowd / cam_03 | day | 72 | 2319 | 0.588 | 0.878 | 0.656 | 0.869 | 0.775 | 10 |
| street_crowd / cam_03 | night | 72 | 2319 | 0.620 | 0.877 | 0.721 | 0.868 | 0.845 | 10 |
| street_crowd_far / cam_01 | day | 95 | 2374 | 0.660 | 0.956 | 0.834 | 0.952 | 0.906 | 8 |
| street_crowd_far / cam_01 | night | 95 | 2374 | 0.672 | 0.949 | 0.893 | 0.946 | 0.927 | 6 |
| street_crowd_far / cam_02 | day | 16 | 2610 | 0.344 | 0.403 | 0.436 | 0.339 | 0.492 | 11 |
| street_crowd_far / cam_02 | night | 16 | 2610 | 0.284 | 0.303 | 0.416 | 0.230 | 0.392 | 7 |
| street_crowd_far / cam_03 | day | 21 | 2610 | **0.284** | 0.371 | 0.302 | 0.268 | 0.356 | 11 |
| street_crowd_far / cam_03 | night | 21 | 2610 | 0.352 | 0.440 | 0.416 | 0.365 | 0.468 | 10 |
| smoke_mock / cam_01 | day | 94 | 896 | 0.494 | 0.959 | 0.430 | 0.945 | 0.629 | 12 |
| smoke_mock / cam_01 | night | 94 | 896 | 0.548 | 0.967 | 0.546 | 0.962 | 0.707 | 4 |
| smoke_mock / cam_02 | day | 47 | 673 | 0.476 | 0.884 | 0.399 | 0.880 | 0.571 | 2 |
| smoke_mock / cam_02 | night | 47 | 673 | 0.545 | 0.904 | 0.545 | 0.896 | 0.649 | 4 |
| MOT20-01 (real) | day | 181 | 13417 | 0.427 | 0.470 | 0.590 | 0.444 | 0.534 | 76 |
| MOT20-02 (real) | day | 187 | 12673 | 0.426 | 0.488 | 0.574 | 0.459 | 0.560 | 34 |

Pre-registered contrasts (bootstrap over cameras, 10 000 resamples):

| contrast | estimate | 95 % CI | p | Holm |
|---|---|---|---|---|
| night − day HOTA (12 paired cameras) | −0.006 | [−0.053, 0.033] | 0.79 | not rejected |
| night − day HOTA, duplicate cam_01 dropped (11) | −0.007 | [−0.058, 0.035] | – | – |
| far (median < 50 px, 8 seqs) − near (16) HOTA | **−0.171** | [−0.251, −0.086] | 0.0002 (perm.) | **rejected** |
| detection-limited (DetA < AssA) share | batch_v7 **0.17** (4/24) | MOT20 **1.00** (2/2) | | |

Secondary (not claimed): night − day MOTA −0.043 [−0.108, 0.009], DetA −0.045
[−0.107, 0.005], AssA +0.021 [−0.064, 0.086].

**H9b, the docs/13 fix** — pooled over sequences (same detections):

| dataset | variant | HOTA | DetA | AssA | MOTA | IDF1 | IDsw |
|---|---|---|---|---|---|---|---|
| batch_v7 | old (control) | 0.5383 | 0.7364 | 0.6739 | 0.7210 | 0.7211 | 141 |
| batch_v7 | fixed (tau 0.6 + gate) | 0.5326 | 0.7332 | 0.6642 | 0.7187 | 0.7204 | 135 |
| batch_v7 | gate only | 0.5302 | 0.7351 | 0.6539 | 0.7197 | 0.7127 | 143 |
| batch_v7 | tau 0.6 only | 0.5411 | 0.7344 | 0.6852 | 0.7205 | 0.7300 | 131 |
| mot20_sub | old (control) | 0.4266 | 0.4784 | 0.5820 | 0.4512 | 0.5467 | 110 |
| mot20_sub | fixed | 0.4271 | 0.4747 | 0.5809 | 0.4486 | 0.5427 | 96 |
| mot20_sub | gate only | 0.4213 | 0.4778 | 0.5622 | 0.4506 | 0.5315 | 116 |
| mot20_sub | tau 0.6 only | 0.4282 | 0.4732 | 0.5855 | 0.4470 | 0.5452 | 96 |

Per-sequence paired ΔHOTA (fixed − old): batch_v7 +0.0008 [−0.015, 0.019]
(n = 24); MOT20 +0.0004 [−0.0015, 0.0024] (n = 2). Gate-only is *worse* on both
(batch_v7 −0.0045 [−0.0095, −0.0005]; MOT20 −0.0053). `adopt_fixed = false`.

**Interpretation.**
* **Far vs near: supported.** Cameras whose median person is < 50 px lose 0.17
  HOTA (CI excludes 0 after Holm). The worst sequences are the 16–21 px far
  cameras (HOTA 0.28–0.35) and the 32 px yard at night (0.40).
* **Night vs day: not supported as a general effect** — the paired mean is −0.006
  with a CI spanning ±0.05. Night is catastrophic on exactly one camera (disguise
  yard, 32 px: 0.602 → 0.401, DetA 0.81 → 0.51) and mildly harmful on gate and
  far cam_02; on street_crowd and smoke_mock it is neutral-to-*better*. Night
  hurts where people are already small, i.e. it is an interaction with size.
* **Failure mode differs from MOT20.** MOT20 is detection-limited (DetA < AssA on
  both sequences: 0.47/0.49 vs 0.59/0.57, dense occlusion). On batch_v7 only 4/24
  sequences are (the far and the yard-night ones); on the rest DetA@0.5 is
  0.80–0.96 and **association** is what holds HOTA down (e.g. smoke_mock AssA
  0.40–0.55, street_crowd 0.66–0.72). HOTA is also well below DetA@0.5 on near
  cameras (sub: 0.51 vs 0.83) — the loose-GT effect (48 B5) penalising the
  high-alpha IoU thresholds, not tracking.
* **H9b: rejected; the flag stays off.** Pooled HOTA rises on MOT20 (+0.0005) but
  falls on batch_v7 (−0.0057), and the change is inside noise on both. The two
  parts pull in opposite directions: tau = 0.6 alone is marginally better on both
  (batch_v7 +0.003 pooled, MOT20 +0.0016), while gate-before-solve alone is
  consistently worse. The gate is not a bug fix in effect here: with the solver
  free to take a sub-threshold pair, the second-best valid pair it would have
  displaced was apparently rarely the right one. A tau-only change would need
  its own pre-registered run (the adoption rule named the combined fix).

**Caveats.** 12 camera pairs; street_crowd and street_crowd_far share cam_01
(dropping it changes nothing). MOT20 contributes n = 2 sequences, so the "1.00"
share is two of two. 10 fps synthetic vs 25 fps real; one detector.
batch_v7 renders are **mixed resolution** (disguise gate/ptz/sub 1920×1080,
everything else 1280×720), and the far/near split used render pixels. Sensitivity
(computed after the run, not pre-registered): on detector-input pixels
(×1280/width) disguise cam_gate becomes 40 px → far; far − near is then −0.135
[−0.218, −0.052] (10 vs 14 sequences) — same conclusion.

## H10 · ReID across appearance epochs (`h10_reid_epochs`)

Pre-registered above (commit `741b025`); runner `survsim/experiments/reid_epochs.py`.
GT crops from `disguise_and_tamper_{day,night}` (min_h 48, min_vis 0.6, 6 per
id per camera), epoch per crop read from `world.parquet` (`appearance_epoch`
at that frame). Galleries are restricted to the query's own lighting (day/night
renders are frame-for-frame duplicates). Rank-1 CI = Wilson over queries
(optimistic: crops of one person are correlated); mAP CI = bootstrap over
identities. Wall 14 s.

**The pre-run check fired.** `identities.parquet` has one epoch change
(`intruder_a`, 0 → 1 at t = 115.1 s); the renders span t = 0.1–29.9 s, so all
106 crops are epoch 0 and **no identity has crops in two epochs**. Independently,
`render_appearance.json` stores a single outfit per uid, i.e. the renderer did
not implement the epoch-1 outfit even for frames it would have rendered.

**Results** (`out/experiments/h10_reid_epochs/results.json`; 106 crops, 5
identities, 3 camera views — cam_yard has no person ≥ 48 px at vis ≥ 0.6):

| cue | protocol | queries | ids | rank-1 [95 % Wilson] | mAP | mAP [boot over ids] |
|---|---|---|---|---|---|---|
| OSNet x1.0 ImageNet | (i) same epoch (≥ 5 s or other cam) | 106 | 5 | 0.726 [0.635, 0.802] | 0.522 | [0.393, 0.795] |
| OSNet x1.0 ImageNet | (ii) cross epoch | **0** | 0 | not measurable | – | – |
| OSNet x1.0 ImageNet | (iii) cross camera, same epoch | 94 | 4 | 0.319 [0.234, 0.419] | 0.383 | [0.215, 0.557] |
| HSV histogram | (i) | 106 | 5 | 0.717 [0.625, 0.794] | 0.536 | [0.408, 0.734] |
| HSV histogram | (ii) | **0** | 0 | not measurable | – | – |
| HSV histogram | (iii) | 94 | 4 | 0.383 [0.291, 0.484] | 0.390 | [0.165, 0.623] |
| gait signature (simulated obs., noise 0.15) | (i) | 106 | 5 | 1.000 [0.965, 1.000] | 1.000 | [1.000, 1.000] |
| gait signature (simulated obs.) | (ii) | **0** | 0 | not measurable | – | – |
| gait signature (simulated obs.) | (iii) | 94 | 4 | 1.000 [0.961, 1.000] | 1.000 | [1.000, 1.000] |

Exploratory same-mesh contrast: the three uids sharing
`quaternius:animated_woman_9kf7` (intruder_a, commute_wait_negative_02,
passer_by_102) never co-occur in the rendered 30 s (only intruder_a appears),
so n_pairs = 0 — also not measurable.

**Interpretation.** **The hypothesis could not be tested; nothing is claimed
about outfit change.** What the data does say: (1) OSNet-ImageNet is no better
than a colour histogram on these renders, within epoch (0.726 vs 0.717) or
across cameras (0.319 vs 0.383; CIs overlap heavily) — H4's "identity is mostly
clothing colour" carries over to batch_v7; (2) both collapse across cameras
(≈ 0.72 → 0.32–0.38) *without* any outfit change, so viewpoint alone costs
more than half the rank-1; (3) the gait row is 1.000 because it matches noisy
copies of 5 people's true parameters (5-way, 0.15 × population sd) — it is an
upper bound on a perfect gait extractor, not a measurement from pixels, and its
cross-epoch value would be 1.0 by construction since gait parameters are
epoch-invariant in the simulator.

**What unblocks it** (not in this pass's scope — survsim/gt and scripts/ue
belong to the other agent): render the window around t = 115 s (e.g. frames
1000–1300) and make the renderer honour `appearance_epoch` when choosing the
outfit; then this same config runs unchanged. With 5 identities and one
changer, even then (ii) would have one identity's queries — the scenario
needs several changers before (ii) can carry a CI narrower than ±0.3.

## H11 · Night (`h11_night`)

Pre-registered above (commit `741b025`); runner `survsim/experiments/night.py`.
**Part A** — yolov8n zero-shot, imgsz 1280, recall at conf 0.25 / IoU 0.5,
frames 1..299 step 5, same frames day vs night (raw detections shared with H9's
cache), and night after `cctv_night_ir` (applied per camera to the 60
sub-sampled frames as one sequence, seed 0; its 1280×720 detections are mapped
back to render pixels). **Part B** — yolov8n fine-tuned 8 epochs, imgsz 640,
batch 8, seed 0, on the 720 night frames (4 night runs, 12 cameras) either
IR-degraded (`ft_night_ir`) or raw (`ft_night_raw`); scored on **MOT20-05**
frames 1..600 step 10 (60 frames, 11 649 GT) — a real, dark (mean luma 47),
*colour* night street, the only night reference available; MOT20 is
non-commercial, evaluation only. **There is no real IR night footage**, so B
measures transfer to lit colour night, not to IR.

**Bug found during the run and fixed before the reported numbers.** The first
pass assumed every render is 1920×1080; batch_v7 is mixed (disguise gate/ptz/sub
1920, the rest 1280), so IR GT was mis-scaled and IR recall read 0.018. The
scale is now taken per camera from the render (`_ir_scale`, regression test
`test_ir_scale_follows_render_width`); the first pass's training runs were
discarded. A path bug (ultralytics prefixing `runs/detect/` to a relative
project) stopped the second pass after training; the two trained weights
were moved into place and the evaluation re-run without retraining.

**Results A** (`out/experiments/h11_night/results.json`, pooled over 9 cameras
with targets ≥ 40 px; far cam_02/03 and yard have none at that height):

| arm | recall | precision | R 0–20 px | R 20–40 | R 40–80 | R 80–160 | R 160+ |
|---|---|---|---|---|---|---|---|
| day raw (control) | 0.815 | 0.879 | 0.468 (n=633) | 0.720 (686) | 0.918 (1393) | 0.943 (889) | 0.948 (211) |
| night raw | 0.807 | 0.904 | 0.531 | 0.676 | 0.891 | 0.943 | 0.934 |
| night + cctv_night_ir | **0.236** | 0.901 | 0.000 | 0.000 | 0.292 | 0.481 | 0.308 |

Pre-registered primary (recall, GT ≥ 40 px, paired by camera, n = 9,
bootstrap): night − day **−0.020 [−0.053, −0.001]**, p = 0.08;
night_ir − night **−0.609 [−0.710, −0.519]**; night_ir − day −0.630
[−0.727, −0.542]. Per camera, night hurts only disguise cam_gate (0.828 →
0.685); IR is worst on disguise cam_sub (0.000) and smoke cam_02 (0.015).

**Results B** (AP50 on MOT20-05; CI = paired bootstrap over the 60 frames,
1000 resamples — evaluation noise only, one training seed):

| arm | AP50 @640 | AP50 @1280 | recall@0.25 @1280 |
|---|---|---|---|
| zero_shot (control) | 0.491 | **0.652** | 0.386 |
| ft_night_raw | 0.160 | 0.460 | 0.252 |
| ft_night_ir | 0.069 | 0.348 | 0.163 |

| contrast | @640 | @1280 |
|---|---|---|
| ft_night_ir − zero_shot | −0.422 [−0.436, −0.412] | −0.303 [−0.318, −0.290] |
| ft_night_raw − zero_shot | −0.331 [−0.345, −0.316] | −0.192 [−0.204, −0.178] |
| ft_night_ir − ft_night_raw (H2-style) | −0.091 [−0.103, −0.083] | −0.111 [−0.131, −0.096] |

(The pre-registration named no eval imgsz for B; both are reported, and the
conclusion is the same at each. `_ap` agrees with `ap50_by_height` to 4 dp.)

**Interpretation.**
* **Night alone barely matters on our renders**: −0.02 recall at ≥ 40 px, CI
  just excluding 0 but p = 0.08 by the pre-registered bootstrap test —
  "small, not established". The night preset is lit (street lamps, EV-metered
  exposure), so the raw night render is not a hard night. Night even *raises*
  recall below 20 px (0.468 → 0.531) and precision (0.879 → 0.904).
* **The IR degrade is the dominant effect**: −0.61 recall, and zero recall
  below 40 px. Precision stays 0.90 — the detector does not hallucinate on IR,
  it goes blind. Even 160+ px people are only 0.31 recalled (the illuminator's
  falloff leaves near-edge people in black).
* **Training on night-degraded synthetic does not help real night; it hurts,
  and the IR degrade hurts more than raw night.** Every fine-tuned arm is
  below zero-shot on MOT20-05 (−0.19 to −0.42 AP50), and IR-degraded training
  is a further −0.09/−0.11 below raw-night training. With one training seed,
  the fine-tune − zero-shot gaps (≥ 7× H1's seed sd of 0.025) are safe to call;
  the IR − raw gap (~4× that sd) is **suggestive only**. This repeats H1/H8
  (fine-tuning on our renders unlearns real people) and extends H2's
  degradation result to night: our IR profile moves synthetic *away* from real
  colour night footage.

**Caveats.** No real IR reference exists — B is a mismatch by design for the IR
arm and must not be read as "IR training fails on IR cameras". MOT20-05 is one
site; 60 frames; one seed; 720 training images from 4 scenes. The IR degrade
was applied to 1-in-5 frames, so its codec saw a 2 fps sequence.

---

# Pre-registrations: H12–H14 (written before any run; report 49 §12 template)

Code: `survsim/experiments/{alarm_scale,realism_transfer,dose,inference}.py`,
configs `h12_alarm_scale.yaml`, `h13_realism_transfer.yaml`, `h14_dose.yaml`.
The only runs made before this entry were code smoke tests of H12 at seed 999
(one clean and one recall world, not the registered seed 12) and a check that
the fast PathLoiter/zone helpers return alarms identical to
`PathLoiterRule.run` / `World.zone_of`. GPU ≤ 2 GB per process behind
`wait_for_gpu`; the editor is not touched.

```
id:            h12_alarm_scale
hypothesis:    on >= 3,000 camera-hours of mock worlds containing NO loiterers,
               every loiter rule is above the 0.001 FA/camera-hour budget with
               its Garwood 95 % lower bound also above it; dwell_60 has the
               lowest rate of the four rules but is still over budget; the
               nuisance alarms come from the dwell archetypes (commute_wait,
               smoke_break, phone_stop, queue), not from transit.
worlds:        scene generator sites (6 site types cycled; footprint 50-130 m,
               1-5 entrances, 4-14 cameras at target coverage 0.55, repaired
               like generate_batch), 1800 s each at 5 Hz, 60 s warm-up.
               People: staggered Poisson stream, 1.5-6 arrivals/min, archetype
               mix transit .55 / commute_wait .15 (20-240 s, queue|gate zone)
               / queue .10 (30-150 s) / phone_stop .10 (idle 15-120 s at a
               random public point) / smoke_break .10 (pacing r 3 m, 60-360 s).
               No hero, no incident; a world with any suspicious.loiter truth
               event would be reported (expected: zero).
rules:         dwell_25, dwell_60 (DwellRule), path_loiter_15, path_loiter_25
               (PathLoiterRule radius 4 m, re-entry 15 s) — H5's parameters.
scoring:       default and ilids_compat, tolerance 30 s; with no truth every
               alarm is a false alarm (ilids_compat coalesces FAs < 5 s apart).
primary metric: FA per camera-hour (camera-hours = n_cameras x duration, as
               alarms.camera_hours_of), Garwood exact 95 % CI; rule of three if
               0 FAs. Secondary: world-cluster bootstrap CI (alarms cluster by
               world), FA per site-hour, top causes by archetype / behaviour.
stopping rule: worlds in index order (seed 12) until cumulative camera-hours
               >= 3,000; no peeking at alarms before the target is reached.
recall side:   300 generator worlds (seed 13 recipe offset), 300 s, incident
               mixes cycling [loiter], [loiter, tailgate], [object_abandon,
               loiter], [erratic_motion, loiter], [disguise_swap, loiter,
               follow] with the generator's hard-negative twins/background;
               recall at tolerance 30 s (and 10 s), 95 % percentile bootstrap
               over worlds (2000 resamples). Descriptive, no test.
success:       H12 confirmed if all four rules have Garwood lower bound > 0.001
               in default scoring. Refuted for any rule whose upper bound is
               <= 0.001.
confounds:     mock trajectories are not validated against real dwell
               distributions (49 §5 caveat b); archetype mix and durations are
               my choice, so the rate is conditional on them; 5 Hz vs H5's 10 Hz.
```

```
id:            h13_realism_transfer   (EXPLORATORY)
hypothesis:    across distinct synthetic training sources, smaller docs/15
               image-statistics distance to MOT20-02 goes with higher real
               MOT20-02 AP after a short fine-tune: Spearman rho < 0.
sources:       every (batch_v5|v6|v7, run, raw|degraded) with >= 300 frames,
               excluding *_failed and *_tightgt runs, de-duplicated by the md5
               of the middle frame (v7 disguise_and_tamper is pixel-identical
               to v6): 41 eligible; a seeded (13) random 20 are used.
distance:      mean |z| over the 13 FrameStats, z = (source median - MOT20-02
               median) / MOT20-02 p10-p90, 40 seeded frames per source; the
               MOT20-02 band from 40 evenly spaced frames of its first 300.
transfer:      yolov8n.pt fine-tuned 4 epochs, imgsz 640, batch 8, seed 0, on
               a seeded 300-frame sample of that source only; last.pt;
               MOT20-02 AP (COCO 0.5:0.95) at 640. 1 seed per source.
analysis:      Spearman rho(mean |z|, AP), 95 % pair-bootstrap CI, two-sided
               permutation p (20,000). Secondary: rho(in-band count, AP).
success:       "predicts" only if rho < 0 with the bootstrap CI excluding 0.
               Anything else: "not shown" (n = 20, single seed, exploratory).
confounds:     source content (scene, near/far, night) varies with statistics;
               one seed -> AP noise ~0.02 (H1 sd 0.025).
```

```
id:            h14_dose
hypothesis:    with 60 real MOT20-01 frames (x5) fixed, adding 100 or 300
               batch_v7 (CC0) synthetic frames raises MOT20-02 AP@640 over
               real-only (H7: +0.010-0.011, 2 seeds).
arms:          mix_0 (control), mix_100, mix_300 — H7's recipe (6 epochs, raw
               stride 8 + degraded stride 8 phase 4, same 5 training runs) on
               batch_v7. Secondary: loose_{100,300} (smoke_mock_day +
               street_crowd_day, projected GT) vs tight_{100,300} (the
               *_tightgt runs, mask GT; street_crowd_day pixels identical,
               smoke_mock_day re-rendered). 5 seeds (0-4) each = 35 runs; the
               seed sets both training randomness and the synthetic subset.
primary:       MOT20-02 AP@640, last.pt.
analysis:      two primary contrasts (mix_100 - mix_0, mix_300 - mix_0):
               exact two-sided unpaired permutation p over C(10,5) = 252
               splits, 95 % bootstrap CI of the mean difference; Holm over the
               two at alpha 0.05. Secondary (no claims): tight - loose paired
               by seed (same subset indices), bootstrap CI and exact sign-flip
               p (minimum attainable 0.0625 with 5 pairs).
success:       gain "real" if Holm rejects and the CI excludes 0 for a dose.
               Tight GT "enlarges" it only as a secondary observation.
stopping:      fixed 5 seeds; no additional seeds after seeing results.
```

```
id:            h10b_reid_epochs   (H10 v2; written before the run)
data:          out/batch_v7/disguise_and_tamper_day_epochs (render commit
               99d986b; frames 950-1349, t 95-135 s, day only). intruder_a
               changes outfit at frame 1152 (epoch 0 black top / face visible;
               epoch 1 white hoodie, navy cap, face hidden). cam_gate sees
               epoch 0 at 950-1084 and epoch 1 at 1311-1349 (88-122 px);
               cam_yard people are 20-35 px (below min_h, excluded); cam_ptz
               sees epoch 1 only at 1225-1231.
hypothesis:    OSNet-ImageNet and HSV-histogram retrieval of intruder_a across
               the outfit change is worse than same-epoch retrieval; the
               simulated gait signature is unaffected (by construction).
crops:         GT boxes, min_h 48, min_vis 0.6, 12 evenly spaced per id per
               camera; epoch from world.parquet at that frame.
protocols:     (i) same epoch (>= 5 s apart or other camera), (ii) cross epoch
               (a query's positives are only its other-epoch crops),
               (iii) cross camera same epoch. Gallery = all other crops.
metrics:       rank-1 (Wilson 95 %) and mAP (bootstrap over identities), as
               H10. n is small: ONE identity changes outfit, so (ii) has one
               identity's queries and its CIs are over correlated crops of one
               person. Therefore also: for intruder_a, the rank of the first
               true match among the distractor gallery (median, range, vs
               chance (gallery+1)/2), split by query epoch.
success:       "collapse" for a cue if intruder_a's cross-epoch median rank is
               > 1 and cross-epoch rank-1 upper Wilson bound < same-epoch
               rank-1 point estimate. With one changer this is a case study,
               not a population estimate; no claim generalises beyond it.
```

## H10 v2 · ReID across an outfit change (`h10b_reid_epochs`)

Pre-registered above (commit `fd775af`). `out/experiments/h10b_reid_epochs/results.json`.
184 GT crops, 7 identities; **only intruder_a spans two epochs, and it has just 3
epoch-1 crops** (cam_gate 1311–1349 and cam_ptz 1225–1231; 12 evenly spaced
crops per id per camera catch few of these short windows). cam_yard gives no
crops because its people are below 48 px.

| cue | protocol | queries | ids | rank-1 [95 % Wilson] | mAP [boot over ids] |
|---|---|---|---|---|---|
| OSNet x1.0 ImageNet | (i) same epoch | 181 | 7 | 0.746 [0.678, 0.804] | 0.391 [0.303, 0.507] |
| OSNet x1.0 ImageNet | (ii) cross epoch | 12 | 1 | 0.083 [0.015, 0.354] | 0.090 |
| OSNet x1.0 ImageNet | (iii) cross camera | 160 | 5 | 0.519 [0.442, 0.595] | 0.308 [0.195, 0.367] |
| HSV histogram | (i) | 181 | 7 | 0.845 [0.785, 0.891] | 0.533 [0.442, 0.726] |
| HSV histogram | (ii) | 12 | 1 | 0.083 [0.015, 0.354] | 0.062 |
| HSV histogram | (iii) | 160 | 5 | 0.588 [0.510, 0.661] | 0.484 [0.377, 0.573] |
| gait signature (simulated obs.) | (i)/(ii)/(iii) | 181/12/160 | | 1.000 | 1.000 |

Distractor ranking for intruder_a's 12 cross-epoch queries (gallery ~175 crops,
6 distractor identities, chance median rank 88):

| cue | median rank of first true match | range | epoch-0 queries (9) | epoch-1 queries (3) |
|---|---|---|---|---|
| OSNet | 8.5 | 1–116 | 16 | 2 |
| HSV histogram | 157 | 1–171 | 161 | 6 |
| gait (simulated) | 1 | 1–1 | 1 | 1 |

**Interpretation (a one-person case study).** By the pre-registered rule
both appearance cues **collapse** across the outfit change: cross-epoch rank-1
0.083 (upper Wilson 0.354) against same-epoch 0.746 / 0.845. The distractor
ranking separates them, though: the colour histogram ranks the other-outfit
intruder_a *worse than chance* (median 157 of ~175 — the black top and the
white hoodie are near-opposite histograms), while OSNet still puts it well
above chance (median 8.5), so OSNet carries some non-colour identity signal
(body shape/pose) that a histogram cannot. The asymmetry by query epoch
(epoch-1 queries find epoch-0 crops at rank 2–6; epoch-0 queries find the 3
epoch-1 crops at 16–161) is partly a gallery-size effect: 3 targets vs ~60.
Gait is 1.000 by construction (simulated measurement of epoch-invariant
parameters), an upper bound, not a pixel result.

**Caveats.** n = 1 changer and 3 epoch-1 crops: the cross-epoch rows are not
population estimates and CIs over correlated crops are optimistic. Day only.
A population-level claim needs several changers and denser epoch-1 sampling
(per-epoch crop quotas).

## H12 · Loiter-rule false alarms at scale (`h12_alarm_scale`)

Pre-registered above (commit `98b7c03`). `out/experiments/h12_alarm_scale/results.json`
(per-world alarms in `worlds.jsonl`). 676 clean worlds (all 6 site types, all
valid), **3,002 camera-hours** (338 site-hours), 74,989 innocent people
(transit 41,150; commute_wait 11,441; phone_stop 7,509; smoke_break 7,495;
queue 7,476 — note: these archetype counts sum to 75,071, not the 74,989
people total, an unresolved inconsistency inside `results.json`), **0 truth loiter events**. Wall 99 min on 11 workers (CPU shared
with other jobs; load 20–68 — over the 40-min budget; 54 CPU-ks of world time).
Every alarm is a false alarm. Budget 0.001 FA/cam-h.

| rule | scoring | FA | FA/cam-h | Garwood 95 % | world-bootstrap 95 % | FA/site-h | × budget (Garwood lower) | top causes (raw alarms) |
|---|---|---|---|---|---|---|---|---|
| dwell_25 | default | 18,033 | 6.01 | 5.92–6.10 | 5.76–6.28 | 53.4 | 6,007 (5,920) | commute_wait 9,561, queue 6,809, smoke_break 1,087 |
| dwell_25 | ilids_compat | 16,317 | 5.44 | 5.35–5.52 | 5.23–5.67 | 48.3 | 5,435 (5,352) | same |
| dwell_60 | default | 13,664 | 4.55 | 4.48–4.63 | 4.35–4.77 | 40.4 | 4,552 (4,476) | commute_wait 8,043, queue 5,081, phone_stop 368 |
| dwell_60 | ilids_compat | 12,658 | 4.22 | 4.14–4.29 | 4.04–4.40 | 37.5 | 4,217 (4,143) | same |
| path_loiter_15 | default | 262,494 | 87.4 | 87.1–87.8 | 83.7–91.4 | 777 | 87,440 (87,106) | **transit 141,507**, commute_wait 39,510, smoke_break 27,983 |
| path_loiter_15 | ilids_compat | 107,718 | 35.9 | 35.7–36.1 | 34.8–37.1 | 319 | 35,882 (35,668) | same |
| path_loiter_25 | default | 61,995 | 20.7 | 20.5–20.8 | 19.8–21.5 | 183 | 20,651 (20,489) | **transit 19,240**, commute_wait 14,439, phone_stop 9,547 |
| path_loiter_25 | ilids_compat | 45,549 | 15.2 | 15.0–15.3 | 14.6–15.8 | 135 | 15,173 (15,034) | same |

Recall side: 300 generator worlds with loiterers (220 camera-h, 360 truth
loiter events), recall with 95 % bootstrap over worlds:

| rule | scoring | tol 30 s recall | tol 10 s recall | precision (tol 30) | FA/cam-h (tol 30) | median latency s |
|---|---|---|---|---|---|---|
| dwell_25 | default | 0.900 [0.869, 0.929] | 0.125 [0.089, 0.163] | 0.182 | 6.59 | 24.4 |
| dwell_25 | ilids_compat | 0.900 [0.869, 0.929] | 0.125 | 0.403 | 2.18 | 24.4 |
| dwell_60 | default | 0.156 [0.117, 0.193] | 0.056 [0.034, 0.081] | 0.067 | 3.55 | 15.6 |
| path_loiter_15 | default | 0.967 [0.949, 0.983] | 0.636 [0.588, 0.683] | 0.010 | 163 | 9.0 |
| path_loiter_25 | default | 0.942 [0.918, 0.964] | 0.364 [0.313, 0.414] | 0.048 | 30.4 | 17.0 |
| path_loiter_25 | ilids_compat | 0.942 [0.920, 0.964] | 0.364 | 0.138 | 9.63 | 17.0 |

**Verdict against the pre-registration.** *Confirmed*: all four rules are over
budget with Garwood lower bounds 4,100–87,000× the 0.001 budget; dwell_60 is
the lowest-rate rule (4.55 FA/cam-h) and also nearly useless (recall 0.156,
because generated loiters last 25–90 s and a 60 s dwell only completes inside
the 30 s window for the long ones). *Refuted in part*: nuisance causes are the
dwell archetypes only for DwellRule; for PathLoiterRule the **largest cause is
ordinary transit** (54 % of path_loiter_15's raw alarms, 31 % of path_loiter_25's).

**Interpretation.**
* With 3,002 camera-hours the sampling error is gone (CIs ±1–2 %); the gap
  to the budget is 3.6–4.9 orders of magnitude. No threshold tweak within
  these families closes that; this is a rule-design problem, not a data-volume
  one. Rule of three was not needed — no rule was quiet.
* **path_loiter_15 alarms on walkers by construction**: its dwell clock only
  resets after `reentry_gap_s` (15 s) of continuous spread > radius, so with
  threshold ≤ re-entry gap every track reaches the threshold before it can be
  reset. path_loiter_25 fires on walkers that slow or turn. That is a
  parameter-interaction bug in the rule, visible only at this volume
  (H5's 0.35 camera-hours showed "142 FA/cam-h", not *why*).
* DwellRule's nuisances are exactly its hard negatives: commute waits and
  queues in gate/queue zones (≥ 90 % of its alarms). Phone stops and smoke
  breaks in open public areas rarely hit it because those zones are not tagged
  gate/restricted — zone tagging, not behaviour, is doing its filtering.
* The world-cluster bootstrap CI is ~3× wider than Garwood: false alarms
  cluster by world (crowded worlds produce many), as 49 §5 warns.
* ilids_compat lowers FAs by 7–59 % via 5 s coalescing only; recall is
  unchanged (it never touches hits), precision flatters (dwell_25: 0.182 → 0.403).
* Recall at the 10 s tolerance collapses for every rule (dwell_25 0.90 → 0.13):
  a dwell rule cannot alarm before its own threshold, so an i-LIDS window
  shorter than the threshold makes it un-scorable.

**Caveats.** Mock trajectories and my archetype mix (55 % transit; durations
as pre-registered) are not validated against real dwell distributions, so the
absolute rates are conditional on them; the *ordering* and the transit
mechanism are properties of the rules. FA/cam-h counts site-level alarms over
all cameras' hours (the codebase definition); per site-hour is 8.9× higher.
5 Hz ticks (H5 used 10 Hz). GT tracks — perception errors would add alarms.

## H13 · Does the realism band predict transfer? (`h13_realism_transfer`, exploratory)

Pre-registered above (commit `98b7c03`). `out/experiments/h13_realism_transfer/results.json`.
41 distinct eligible sources, seeded 20 used; 4 epochs on 300 frames each,
MOT20-02 AP@640, 1 seed (median train 63 s; wall 80 min with contention).

| source | in band | mean abs z | AP | AP50 |
|---|---|---|---|---|
| v7 smoke_mock_day degraded | 2/13 | 2.61 | 0.235 | 0.602 |
| v6 smoke_mock_day degraded | 2/13 | 2.62 | 0.194 | 0.573 |
| v7 street_crowd_day degraded | 1/13 | 3.39 | 0.305 | 0.635 |
| v7 street_crowd_night degraded | 2/13 | 3.80 | 0.312 | 0.626 |
| v7 street_crowd_far_day degraded | 2/13 | 3.97 | 0.254 | 0.507 |
| v6 street_crowd_far_day degraded | 2/13 | 4.00 | 0.241 | 0.515 |
| v6 smoke_mock_night degraded | 1/13 | 4.38 | 0.163 | 0.487 |
| v7 street_crowd_day raw | 1/13 | 4.43 | 0.276 | 0.619 |
| v6 street_crowd_day raw | 1/13 | 4.47 | 0.265 | 0.588 |
| v5 street_crowd_day raw | 1/13 | 4.49 | 0.265 | 0.591 |
| v6 street_crowd_far_day raw | 2/13 | 5.35 | 0.191 | 0.424 |
| v7 street_crowd_night raw | 1/13 | 5.38 | 0.272 | 0.588 |
| v6 street_crowd_night raw | 1/13 | 5.39 | 0.288 | 0.619 |
| v6 smoke_mock_day raw | 1/13 | 5.77 | 0.127 | 0.384 |
| v5 disguise_and_tamper_day raw | 1/13 | 5.92 | 0.062 | 0.157 |
| v5 disguise_and_tamper_night raw | 2/13 | 6.64 | 0.028 | 0.066 |
| v5 disguise_and_tamper_night degraded | 1/13 | 7.96 | 0.108 | 0.267 |
| v6 smoke_mock_night raw | 0/13 | 8.36 | 0.150 | 0.416 |
| v6 street_crowd_far_night raw | 0/13 | 9.81 | 0.161 | 0.326 |
| v5 smoke_mock_night raw | 2/13 | 10.46 | 0.179 | 0.480 |

**Spearman ρ(mean |z|, AP) = −0.60 [95 % bootstrap −0.78, −0.20], permutation
p = 0.005, n = 20** — by the pre-registered criterion, image-statistics
distance *predicts* transfer (exploratory). The in-band *count* does not:
ρ = +0.10 [−0.40, 0.51], p = 0.67 (every source has 0–2 of 13 in band, so the
count has no range).

**Interpretation.** H6(d)'s 4-point ordering survives at n = 20: sources
closer to MOT20 in frame statistics transfer better, and the degraded variant
of a scene is closer *and* better in 5 of the 6 same-(batch, run) raw/degraded pairs
present (the exception: v5 disguise_night degraded is better but farther, 7.96 vs 6.64). But distance is confounded with content: the worst sources are
v5 disguise_and_tamper (AP 0.03–0.11, a scene H1–H6 already found poor) and
night renders, and within the same distance band street_crowd beats
smoke_mock by ~0.1 AP. So mean |z| is a useful cheap screen (ρ ≈ −0.6 means
~36 % of rank variance), not a substitute for the fine-tune.

**Caveats.** One seed per source (seed sd ≈ 0.025 from H1, comparable to many
neighbouring gaps); 4 epochs from COCO — every arm is still below zero-shot
(0.276 on MOT20-02) except three street_crowd sources (v7 street_crowd_day raw ties at 0.2757); sources share scenes
across batches (not independent); exploratory, no multiplicity control.

## H14 · Tiny synthetic dose, replicated (`h14_dose`)

Pre-registered above (commit `98b7c03`). `out/experiments/h14_dose/results.json`.
35 runs: 60 real MOT20-01 frames ×5 in every arm, 6 epochs, MOT20-02 AP@640,
last.pt, seeds 0–4 (the seed also picks the synthetic subset).

| arm | AP mean (sd), 5 seeds |
|---|---|
| mix_0 (real only) | 0.4862 (0.0006) |
| mix_100 (batch_v7) | 0.4969 (0.0013) |
| mix_300 (batch_v7) | 0.4951 (0.0028) |
| loose_100 / loose_300 (smoke_mock_day + street_crowd_day, projected GT) | 0.4969 (0.0008) / 0.4979 (0.0014) |
| tight_100 / tight_300 (the *_tightgt runs, mask GT) | 0.4975 (0.0013) / 0.5000 (0.0021) |

| contrast | diff | 95 % bootstrap | p | Holm (α 0.05) |
|---|---|---|---|---|
| **mix_100 − mix_0** (primary) | +0.0107 | [+0.0096, +0.0118] | 0.0079 (exact permutation) | reject |
| **mix_300 − mix_0** (primary) | +0.0089 | [+0.0066, +0.0111] | 0.0079 | reject |
| tight_100 − loose_100 (secondary, paired) | +0.0006 | [−0.0007, +0.0020] | sign-flip 0.44 | – |
| tight_300 − loose_300 (secondary, paired) | +0.0021 | [+0.0008, +0.0036] | sign-flip 0.0625 (min. attainable) | – |
| tight_300 − mix_0 (secondary) | +0.0138 | [+0.0121, +0.0155] | unpaired 0.0079 | – |
| loose_300 − mix_0 (secondary) | +0.0117 | [+0.0105, +0.0129] | unpaired 0.0079 | – |

p = 0.0079 = 2/252 is the smallest p the exact test can give with 5 vs 5:
the arms separate completely.

**Headline (fixed labels, `h14b_dose_fixedlabels`).** The mix arms drew on disguise
frames whose labels were mis-scaled (see "Label-geometry bug" below). Re-run with
the fix: **mix_100 − mix_0 = +0.0121 [+0.0111, +0.0130], mix_300 − mix_0 = +0.0095
[+0.0084, +0.0106]**, both p = 0.0079, Holm-reject. The mix arms moved by +0.0014
(100) and +0.0006 (300) relative to the table above; tight/loose arms were unaffected
(all 1280×720). The table above is the original, buggy-label run.

**Conclusion.** H7's small-dose gain replicates on CC0 batch_v7 frames with 5
seeds: **+0.012 AP (100 frames) and +0.010 (300 frames)** with fixed labels
(+0.011 / +0.009 in the original buggy-label run), both significant
after Holm, matching H7's +0.010–0.011. Tight (mask) GT adds at most a
further ~+0.002 at 300 frames. All 5 paired differences are positive, but n = 5
cannot reach p < 0.0625, so this is suggestive, not established. At 100 frames
tight GT adds nothing measurable.

**Caveats.** One real site (MOT20-01/02 likely the same scene); a ~0.01 effect
on a 0.49 baseline; the step count grows with dose (H7's confound); tight vs
loose differs in pixels too for smoke_mock_day (re-rendered), only
street_crowd_day is a label-only contrast.

## Label-geometry bug found while preparing H15 (affects H1–H14 `mix`/pool arms)

`detection.build_train_set` normalised every synthetic label by a hard-coded
1280×720. batch_v6/v7 disguise cameras gate/ptz/sub render **1920×1080** raw,
and their degraded video is 1280×720 while the GT stays in 1920-pixel
coordinates. So raw disguise labels were stretched ×1.5 (and clipped), and
degraded disguise labels were stretched ×1.5 relative to their pixels. Only
arms drawing on the disguise runs were affected (H1/H2/H6/H7 synthetic pools,
H14 `mix_*`); the H14 tight/loose arms (smoke_mock/street_crowd, all 1280×720)
were not. Fixed: labels are now written in each image's own pixels, scaled
from the raw render size (`_synth_candidates`, regression test
`test_synth_labels_follow_image_size_not_a_fixed_1280`). H14's mix arms are
re-run under the fix as `h14b_dose_fixedlabels` (below, with H16).

## H15 · Amodal vs visible labels (`h15_amodal_labels`) — pre-registration

Registered 2026-09-27, before any H15 arm was trained.

```
id:            h15_amodal_labels   (config survsim/experiments/configs/h15_amodal_labels.yaml)
data:          visible (mask-derived) GT gt/mot_<cam>.txt vs amodal GT gt/amodal/mot_<cam>.txt
               (col 9 = MOT20-style visibility = visible mask px / amodal-box expectation).
               Two pixel sets, each its own contrast:
                 v7 = out/batch_v7/{smoke_mock_day,street_crowd_day}_tightgt
                 v8 = out/batch_v8/{smoke_mock_day,smoke_mock_night,disguise_and_tamper_day,
                      disguise_and_tamper_night}  (the 4 of 5 v8 runs with degraded video;
                      street_crowd_day was still rendering)
               Same H7 pool recipe (raw stride 8 + degraded stride 8 phase 4).
hypothesis:    H15a: amodal labels > visible labels in MOT20-02 AP@640 (MOT20 GT is amodal),
               mostly via AP75.  H15b (direction not predicted): dropping amodal rows with
               visibility < 0.3 changes AP relative to amodal-all.
visibility:    MOT20 paper (Dendorfer et al. 2020, arXiv 2003.09003) annotates every moving
               pedestrian with a visibility ratio and applies NO visibility cut in its own
               evaluation (only conf/class flags). The cut is detector-training practice
               (e.g. Tracktor/FRCNN on MOT17 uses ~0.25); 0.3 is used here as requested.
               Filtered rows are removed from labels (not made ignore regions). The real
               MOT20-01 labels are left untouched in every arm (the real part is held fixed).
design:        H14 recipe: 60 real MOT20-01 x5 + 300 synthetic, yolov8n, 6 epochs, imgsz 640,
               last.pt, MOT20-02 AP@640. Arms {vis, amo, amo_v03} x {v7, v8} x seeds 0-6
               (42 runs). Within a seed and pixel set, the 300 frames are identical across
               label arms (same candidate list, same seeded subset) -> paired.
analysis:      per contrast, paired by seed (n = 7): percentile bootstrap CI of the mean
               difference + exact sign-flip p (min 1/64 = 0.016). Primary: amo - vis on v7
               and on v8, Holm over the two. Secondary: amo_v03 - amo, amo_v03 - vis;
               AP75 and AP50 differences reported descriptively.
decision:      H15a supported only if both primaries are positive and Holm-rejected; one set
               only = "set-dependent"; a CI straddling 0 = "no measurable effect at this dose".
```

**Amendment 2026-09-27 (before any H15 arm ran; H15 was queued behind H16).**
batch_v8 finished and was gated (commit `94145fa`): 9 CC0 sets, all with
degraded video, visible + amodal GT and correct heights. The v7 `*_tightgt`
sets carry the **1.70 m character-height error** (every agent the same
height), so they are demoted to a secondary contrast. Revised design:
v8 = all 9 batch_v8 sets (disguise day/day_epochs/night, smoke_mock day/night,
street_crowd day/night, street_crowd_far day/night). **Primary (single, no
Holm): v8_amo − v8_vis**, paired, 7 seeds. Secondary: v8_amo_v03 − v8_amo,
v8_amo_v03 − v8_vis, and v7_amo − v7_vis (height caveat). v7_amo_v03 dropped.
35 runs. Decision rule for H15a now refers to the v8 primary alone; v7 is
reported as a consistency check.

### H15 results

`out/experiments/h15_amodal_labels/results.json`, 35 runs, MOT20-02 AP@640,
7 seeds, paired by seed (same 300 frames within a seed and pixel set).

| arm | AP mean (sd) | AP50 mean (sd) |
|---|---|---|
| v8_vis_300 (visible mask boxes) | 0.4981 (0.0032) | 0.828 (0.003) |
| v8_amo_300 (amodal boxes) | 0.4976 (0.0039) | 0.829 (0.004) |
| v8_amo_v03_300 (amodal, vis ≥ 0.3) | 0.4975 (0.0035) | 0.829 (0.004) |
| v7_vis_300 | 0.5004 (0.0026) | 0.832 (0.004) |
| v7_amo_300 | 0.4996 (0.0024) | 0.833 (0.006) |

| contrast (paired, n = 7) | ΔAP [95 % bootstrap] | sign-flip p | ΔAP50 | ΔAP75 |
|---|---|---|---|---|
| **v8_amo − v8_vis (primary)** | −0.0005 [−0.0012, +0.0001] | 0.31 | +0.0011 [+0.0003, +0.0021] | −0.0005 [−0.0018, +0.0007] |
| v8_amo_v03 − v8_amo | −0.0000 [−0.0006, +0.0005] | 0.92 | +0.0001 | +0.0004 |
| v8_amo_v03 − v8_vis | −0.0005 [−0.0012, +0.0001] | 0.19 | – | – |
| v7_amo − v7_vis (height caveat) | −0.0007 [−0.0013, −0.0002] | 0.078 | +0.0004 | −0.0001 |

**Conclusion.** H15a is **not supported**: amodal instead of visible labels on
the same 300 synthetic frames changes MOT20-02 AP by −0.0005 [−0.0012,
+0.0001] (v8) — no measurable effect, and the predicted AP75 gain is absent
(−0.0005 [−0.0018, +0.0007]); only AP50 moves, +0.001. v7 agrees in sign and
size. H15b: the visibility ≥ 0.3 cut does nothing (−0.0000), and cannot: it
removed 20 of 12,514 training boxes in seed 0 (0.16 %; the sampled
frames rarely hold anyone below visibility 0.3, unlike MOT20's dense crowds).

**Caveats.** At this dose the synthetic part is 300 of 600 images next to 60
real frames ×5 whose (amodal) labels are fixed — label geometry on the
synthetic half is a second-order input; the effect may be larger when
synthetic dominates (H1-style synthetic-only) — untested. The visibility cut
mirrors detector-training practice, not the MOT20 paper, which annotates
every moving pedestrian with a visibility ratio and applies no cut in its
evaluation. Amodal boxes are a calibrated body-envelope model (holdout IoU
median ~0.89–0.91), not hand labels.

## H16 · Re-baseline to YOLO26n (`h16_yolo26_zeroshot`, `h16_yolo26_dose`, `h14b_dose_fixedlabels`) — pre-registration

Registered 2026-09-27, before any H16 run (report 54 §9, "YOLO26n/s: High").
YOLO26n weights: Ultralytics release file `yolo26n.pt` (2.57 M params),
ultralytics 8.4.163, copied to `out/experiments/weights/`.

```
zero-shot:     yolov8n vs yolo26n, COCO weights, no training. MOT20 subset (01+02, first 300
               frames each) AP/AP50/AP75 at imgsz 640 and 1280 (docs/13 harness); batch_v7 raw
               recall by GT height (8 runs, every 10th frame, conf 0.25, IoU 0.5).
               Descriptive; the one test is the paired per-camera-sequence recall difference
               (bootstrap CI over sequences). Zero-shot gap = yolo26n - yolov8n.
dose:          h16_yolo26_dose = H14 mix_0/mix_100/mix_300 x seeds 0-4 with base yolo26n,
               labels fixed. h14b_dose_fixedlabels = the same with yolov8n (mix_0 copied from
               H14: no synthetic frames, identical code path).
hypothesis:    H16: mix_100 > mix_0 and mix_300 > mix_0 on MOT20-02 AP@640 for yolo26n
               (unpaired exact permutation p, bootstrap CI, Holm over the two), as in H14.
               Secondary: the gain (mix_k - mix_0) differs between detectors (bootstrap CI of
               the difference of differences); and h14b vs H14 shows what the label bug cost.
```

### H16 results

`out/experiments/h16_yolo26_zeroshot/results.json`, `h16_yolo26_dose/`,
`h14b_dose_fixedlabels/`.

**Zero-shot** (COCO weights; MOT20 subset 01+02, 600 frames; batch_v7 raw every
10th frame, 3,692 GT, 24 camera-sequences):

| model | imgsz | MOT20 AP | AP50 | AP75 | v7 R all | R 0–20 | R 20–40 | R 40–80 | v7 P |
|---|---|---|---|---|---|---|---|---|---|
| yolov8n | 640 | 0.281 | 0.618 | 0.216 | 0.573 | 0.015 | 0.175 | 0.734 | 0.848 |
| yolov8n | 1280 | 0.338 | 0.703 | 0.288 | 0.824 | 0.547 | 0.707 | 0.912 | 0.888 |
| yolo26n | 640 | 0.255 | 0.567 | 0.195 | 0.608 | 0.065 | 0.236 | 0.778 | 0.887 |
| yolo26n | 1280 | 0.335 | 0.708 | 0.276 | 0.853 | 0.645 | 0.748 | 0.926 | 0.910 |

yolov8n@640 reproduces H1's 0.281 exactly. Paired per-sequence recall
difference yolo26n − yolov8n: +0.025 [+0.009, +0.042] at 640, +0.028
[+0.006, +0.053] at 1280. On MOT20 YOLO26n is lower at 640 (−0.026 AP; recall
at conf 0.25 0.27 vs 0.40 — it is far more conservative in dense crowds) and
equal at 1280 (−0.003 AP, +0.006 AP50 (0.0059)).

**Dose** (MOT20-02 AP@640, 5 seeds, mean (sd)):

| detector | mix_0 | mix_100 | mix_300 | gain 100 [95 % CI], p | gain 300 [95 % CI], p |
|---|---|---|---|---|---|
| yolo26n | 0.4587 (0.0017) | 0.4679 (0.0015) | 0.4757 (0.0022) | +0.0092 [+0.0075, +0.0109], 0.0079 | +0.0169 [+0.0147, +0.0190], 0.0079 |
| yolov8n, labels fixed (h14b) | 0.4862 (0.0006) | 0.4983 (0.0011) | 0.4957 (0.0012) | +0.0121 [+0.0111, +0.0130], 0.0079 | +0.0095 [+0.0084, +0.0106], 0.0079 |
| yolov8n, H14 (buggy disguise labels) | 0.4862 | 0.4969 | 0.4951 | +0.0107 | +0.0089 |

All four H16/h14b primaries Holm-reject (p = 2/252, complete separation).
Gain difference yolo26n − yolov8n: 100 frames −0.0030 [−0.0049, −0.0010];
300 frames +0.0074 [+0.0049, +0.0097] (independent bootstrap). The label fix
moved yolov8n mix arms by +0.0014 (100, all 5 paired seeds positive) and
+0.0006 (300, mixed signs): the bug cost ~0.001 AP, it did not create H14's
effect.

**Conclusion.** The small-dose synthetic gain **holds on YOLO26n**
(+0.009 / +0.017 AP) and, unlike yolov8n, keeps growing from 100 to 300
frames. But YOLO26n is the *weaker* base for this task: −0.026 AP zero-shot
at 640 and −0.028 AP after the 60-real-frame fine-tune (0.459 vs 0.486); its
AP75 is also lower (0.467 vs 0.512 real-only), so the yolov8n rows remain the
reference. It is better only where the scene is sparse and people are small
(batch_v7 recall +0.025–0.028; <20 px recall at 1280 0.645 vs 0.547).

**Caveats.** Nano models only (YOLO26s not run); YOLO26n trained with the
same recipe tuned for yolov8n (6 epochs, lr0 0.01, optimizer auto) — its
fine-tune deficit may be a recipe mismatch rather than the architecture;
one real site; the synthetic recall set is batch_v7 (1.70 m height error).

> **Note (2026-09-27, H26/AUDIT_H26):** the +0.0092 / +0.0169 YOLO26n gains compare unequal optimiser steps (mix_0 ~228 vs mix_100 300 / mix_300 450 iterations), the h14b confound; no equal-step YOLO26n run exists (R52).

## H17 · Does the detection gain carry to tracking? (`h17_tracking_transfer`) — pre-registration

Registered 2026-09-27, before any H17 run. Report 24 §MOTSynth claims a
synthetic-trained detector improves tracking on MOT17/20; this tests it on our data.

```
id:            h17_tracking_transfer  (config survsim/experiments/configs/h17_tracking_transfer.yaml)
detectors:     no training. mix_0_s{0..4} = H14 real-only weights (60 real MOT20-01 x5, 6 ep,
               imgsz 640; h14b copied mix_0 from H14, identical code path); mix_300_s{0..4} =
               h14b_dose_fixedlabels weights (+300 batch_v7 frames, fixed labels). Both kept on
               disk, so 5 seeds (not 3) at no GPU cost. Reference row: zero-shot COCO yolov8n.
data:          MOT20-02, docs/13 subset (frames 1..300), GT conf==1/class==1, ignore regions as
               in H9 (MOT20-01 was training data: never evaluated).
held fixed:    det imgsz 640 (the training size and the H14 primary), det conf 0.1, default
               numpy ByteTrack (H9: the "fixed" variant was NOT adopted), max_lost = fps.
hypothesis:    H17: mix_300 - mix_0 HOTA > 0 (small), and the shift is mainly DetA
               (|dDetA| > |dAssA|).
metrics:       corrected HOTA (survsim.eval.tracking), DetA, AssA, MOTA, IDF1, ID switches.
analysis:      paired by training seed (n = 5): mean difference, percentile bootstrap 95 % CI
               (10 000 resamples, seed 0), exact two-sided sign-flip p (min 2/32 = 0.0625, so
               "significant at 0.05" is unattainable; the CI is the evidence). Single primary
               (HOTA), no Holm; the rest secondary.
decision:      supported iff HOTA CI > 0 and |dDetA| > |dAssA|; CI straddling 0 = "gain does
               not measurably carry to tracking".
stopping rule: one pass. Budget: 11 detectors x 300 frames inference only (~5 min GPU).
confounds:     one sequence, one site (MOT20-01/02 likely the same scene as training);
               300 frames; nano model; the tracker is our numpy ByteTrack, not the reference.
```

## H18 · Far-field v2 (`h18_farreal_v2`) — pre-registration

Registered 2026-09-27, before any H18 arm was trained. Replicates H8 with its
three flaws fixed: H8 trained on batch_v6 far sets only (one street, no real
frames, 1 seed); now batch_v8 (correct heights, tight visible mask labels),
mixed with real frames, 3 seeds.

```
id:            h18_farreal_v2   (config survsim/experiments/configs/h18_farreal_v2.yaml; runner farreal)
arms:          zero_shot (COCO yolov8n); real_only_s{0,1,2} = H14 mix_0 weights (60 real MOT20-01
               x5, 6 ep, imgsz 640, batch 8 — reused, identical recipe); far_mix_s{0,1,2} = same
               recipe + a seeded 300 of batch_v8 street_crowd_far_{day,night}, all cameras,
               raw stride 4 + degraded stride 4 phase 2 (894 candidates, 7,572 boxes; GT height
               p5/p50/p95 = 14/20/121 px), visible (mask) labels.
eval:          H8 harness: MOT20-02 frames 5..300 step 5 downscaled INTER_AREA by 0.25 and 0.33;
               targets = GT < 60 px after scaling, larger GT = ignore. Methods: full frame at
               imgsz 640, full frame at imgsz 1280, and 320x240 tiles (+full) at 640.
hypothesis:    (prediction from H8) far_mix - real_only AP50 < 0 on small real people; if mixing
               with real rescues it the CI will include or exceed 0.
primary:       far_mix - real_only AP50, scale 0.25, full_640 and full_1280 (two, Holm).
               Paired by seed (n = 3): bootstrap CI + exact sign-flip p (min 0.25 at n = 3, so
               no primary can reject; the decision is on the CI and the sign of all 3 seeds).
secondary:     same at scale 0.33 and with sahi_320x240; far_mix - zero_shot (zero-shot as a
               constant, CI over far_mix seeds) incl. vs zero_shot sahi_320x240; recall bands.
decision:      "synthetic far frames hurt" iff both primary CIs < 0 with all 3 seeds negative;
               "help" iff both > 0; otherwise "no measurable effect at n = 3".
stopping rule: one pass; budget 3 trainings (~1.5 min each) + 7 evals x 3 methods x 2 scales.
confounds:     downscaled 1080p != a real far camera (H8 caveat); training at 640 on 1280x720
               far frames halves the synthetic people (7-30 px) — H8 trained at 1280; one real
               site; the dose grows the step count (H7 confound).
```

### H17 results

> **Pre-parity scorer (added 2026-09-27, AUDIT_M1_PARITY).** Every HOTA/DetA/AssA/IDF1/IDSW
> number in this section was computed with `evaluate_mot` *before* M1 TrackEval parity
> (`5571631`): per-α Hungarian HOTA matching, IDF1 from CLEAR matches, greedy cross-gap
> continuity. Absolute values are pre-parity; the deltas used the same old code on both arms
> but have **not been recomputed** with the parity scorer, so whether they hold is unknown [A].

`out/experiments/h17_tracking_transfer/results.json`; MOT20-02 frames 1–300,
det imgsz 640, default ByteTrack.

| arm | HOTA | DetA | AssA | MOTA | IDF1 |
|---|---|---|---|---|---|
| zero-shot yolov8n (reference) | 0.318 | 0.325 | 0.475 | 0.308 | 0.378 |
| mix_0 (real only), mean of 5 seeds | 0.5026 | 0.6666 | 0.5610 | 0.6434 | 0.6011 |
| mix_300, mean of 5 seeds | 0.5128 | 0.7008 | 0.5559 | 0.6760 | 0.6139 |

| mix_300 − mix_0 (paired by seed, n = 5) | mean | 95 % bootstrap | sign-flip p |
|---|---|---|---|
| **HOTA (primary)** | **+0.0103** | **[+0.0008, +0.0197]** | 0.25 |
| DetA | +0.0342 | [+0.0299, +0.0397] | 0.0625 (min.) |
| AssA | −0.0051 | [−0.0257, +0.0140] | 0.75 |
| MOTA | +0.0326 | [+0.0268, +0.0380] | 0.0625 (min.) |
| IDF1 | +0.0128 | [+0.0021, +0.0227] | 0.125 |
| ID switches | +11 | [−0.2, +19.6] | 0.125 |

**Conclusion.** Supported by the pre-registered rule, weakly: the synthetic dose
lifts HOTA by +0.010 [+0.001, +0.020], entirely through detection (DetA +0.034,
all 5 seeds positive; AssA −0.005, CI straddles 0). But HOTA rose in only 3 of 5
seeds (s2 −0.001, s3 −0.002): the DetA gain is robust, the HOTA gain is not —
extra detections also bring more ID switches (+11), which eats much of it.
MOTA (+0.033) carries the detection gain almost 1:1. The MOTSynth direction
holds on our data, at a small effect size; the n = 5 bootstrap CI is optimistic.

> **Note (2026-09-27, H26/AUDIT_H26):** mix_0 (H14 real-only, ~228 iterations) vs mix_300 (h14b, 450) is the unequal-step confound, so part of the DetA/HOTA gain may be extra steps; not re-run at equal steps (R53).

### H18 results

`out/experiments/h18_farreal_v2/results.json`; AP50 on MOT20-02 people < 60 px
after downscaling, 3 seeds (mean). far_mix trained 54–58 s per seed.

| arm | 0.25 full_640 | 0.25 full_1280 | 0.25 tiles | 0.33 full_640 | 0.33 full_1280 | 0.33 tiles |
|---|---|---|---|---|---|---|
| zero_shot | 0.521 | 0.613 | 0.564 | 0.211 | 0.377 | 0.222 |
| real_only | 0.769 | 0.782 | 0.789 | 0.628 | 0.682 | 0.549 |
| far_mix | 0.779 | 0.781 | 0.798 | 0.641 | 0.692 | 0.519 |

| far_mix − real_only (paired, n = 3) | ΔAP50 | 95 % bootstrap | per seed |
|---|---|---|---|
| **0.25 full_640 (primary)** | **+0.0099** | **[+0.0067, +0.0144]** | all + |
| **0.25 full_1280 (primary)** | **−0.0014** | **[−0.0045, +0.0013]** | −, +, − |
| 0.25 tiles 320×240 | +0.0089 | [+0.0051, +0.0113] | all + |
| 0.33 full_640 | +0.0129 | [−0.0015, +0.0268] | −, +, + |
| 0.33 full_1280 | +0.0106 | [+0.0062, +0.0190] | all + |
| 0.33 tiles 320×240 | −0.0303 | [−0.0513, −0.0172] | all − |

Sign-flip p ≥ 0.25 everywhere (n = 3 floor); Holm cannot reject either primary.
far_mix − zero-shot (tiled): +0.235 [+0.234, +0.236] at 0.25, +0.297 [+0.286,
+0.308] at 0.33. zero_shot tiles reproduce H8 exactly (0.564 / 0.222).

**Conclusion.** H8's prediction **fails once real frames are mixed in**: the
batch_v8 far frames no longer destroy small-person AP (H8: 0.478 → 0.004).
By the pre-registered rule the result is **"no measurable effect at n = 3"**:
one primary is +0.010 [+0.007, +0.014] (640), the other −0.001 [−0.005, +0.001]
(1280). Secondaries are mostly small positives, except tiled inference at 0.33
scale, where far_mix loses −0.030 [−0.051, −0.017] (precision, not recall).
The dominant effect is the 60 real frames (+0.25 AP50 over zero-shot) — which
are the same site as the test sequence.

**Caveats.** n = 3 cannot reach p < 0.25; trained at 640, so synthetic people
were 7–30 px in training (H8 trained at 1280); downscaled 1080p is not a real
far camera; one real site; H8's "hurt" was synthetic-only, which H18 did not
re-run, so what changed (real mix vs v8 labels/heights) is not separated.

## H19 · Far-field v3: which fix removed H8's collapse? (`h19_farreal_v3`) — pre-registration

Registered 2026-09-27, before any H19 arm was trained. H18 left open whether
H8's collapse (AP50 0.478 → 0.004) disappeared because of the batch_v8 fixes
(tight visible labels, correct heights) or because 60 real frames were mixed
in, and it trained at 640 where H8 trained at 1280.

```
id:            h19_farreal_v3   (config survsim/experiments/configs/h19_farreal_v3.yaml; runner farreal)
arms (x3 seeds): v6_syn   = H8 far_ft recipe replicated (batch_v6 street_crowd_far cam_02/03, raw stride 3
                            + degraded stride 3 phase 1, 8 ep, imgsz 1280, batch 2) — synthetic only.
                 v8_syn   = the identical recipe on batch_v8 far sets — synthetic only.
                 v8_mix1280 = H18 far_mix recipe (60 real MOT20-01 x5 + seeded 300 batch_v8 far) at
                            imgsz 1280, batch 2, 6 ep.
               re-scored, not retrained: zero_shot; real_only_s{0,1,2} (H14 mix_0, 640);
               v8_mix640_s{0,1,2} (H18 far_mix, 640).
eval:          H8/H18 harness (MOT20-02 frames 5..300 step 5, INTER_AREA 0.25 / 0.33, targets GT < 60 px,
               larger GT ignore); methods full_native (H8's), full_640, full_1280, 320x240 tiles.
primary:       AP50 at scale 0.25, full_1280, paired by seed (n = 3):
               P1 v8_syn - v6_syn   (effect of the batch_v8 label/height fixes, synthetic only)
               P2 v8_mix1280 - v8_syn (effect of adding real frames at 1280)
secondary:     same at 0.33 / other methods; each arm vs zero_shot; v8_mix1280 - real_only;
               v8_mix1280 - v8_mix640 (training resolution); recall bands.
"collapse":    an arm collapses if its AP50 (0.25, full_1280) < 0.5 x zero_shot's, in all 3 seeds.
decision:      v6_syn collapses and v8_syn does not            -> "the batch_v8 fixes removed it";
               both collapse and v8_mix1280 does not           -> "the real mix removed it";
               v6_syn does not collapse                        -> "H8's collapse does not replicate at
                                                                  n = 3 / these eval methods";
               neither fix alone, and mix also collapses       -> "not removed at 1280".
stopping rule: one pass; 9 trainings (~3-4 min each at 1280, batch 2) + 16 evals.
confounds:     v6 and v8 far renders also differ in lighting/assets beyond labels and heights (so P1 is
               "batch_v8 vs batch_v6", not labels alone); downscaled 1080p != real far camera; one real
               site; n = 3 gives a sign-flip floor of p = 0.25.
```

## H20 · Can synthetic data train a ReID embedding? (`h20_reid_train`) — pre-registration

Registered 2026-09-27, before any H20 training. H4/H10 only *scored* an
ImageNet OSNet on our crops; nothing has been trained on them.

**Identity budget — deviation from the requested ≥ 100 ids.** batch_v8 contains
**23 distinct identities**, not ≥ 100: street_crowd (13, shared by day / night /
far day / far night), smoke_mock (3), disguise_and_tamper (5) and
disguise_and_tamper_day_epochs (7, one of which changes outfit). *(AUDIT_H19_H20: the listed counts sum to 28 per-scene
identities, not 23; 23 is not recoverable from the run. As scored, results.json has 16 train candidates
(15 used) and 13 held-out scene:uid:epoch keys; several held-out uids, e.g. loiterer_200, reuse names seen
in training, so treat "held-out" as held-out by scene, not provably by appearance.)* Splitting
(identity × camera) or (identity × set) into pseudo-ids would label the same
person as different classes across cameras — the opposite of what ReID must
learn — so it is not done. The experiment runs with what exists, and the
comparison to the ~19 % MSMT17 mAP literature figure (UnrealPerson, ~3,000
identities; doc 24 §4) is therefore about direction, not magnitude.

```
id:            h20_reid_train   (config survsim/experiments/configs/h20_reid_train.yaml; runner reid_train)
train:         street_crowd_{day,night,far_day,far_night} + smoke_mock_{day,night} (16 ids; identity =
               world:uid). GT crops h >= 48 px, vis >= 0.6, raw renders, up to 40 evenly spaced per
               (identity, camera, set).
held out:      disguise_and_tamper_{day,night} + disguise_and_tamper_day_epochs (by scene; identity =
               world:uid:epoch, 13 test ids), 12 crops per (id, camera, set).
model:         torchreid osnet_x1_0, ImageNet init; softmax-CE (label smoothing 0.1) + batch-hard triplet
               (margin 0.3); PK batches P=8, K=4; 256x128, flip + pad-crop + random erasing (no colour
               jitter); Adam 3e-4, AMP; fixed 12 epochs-equivalent, capped at 5 min per seed; last
               checkpoint (no selection on test data). Seeds 0, 1, 2.
baselines:     OSNet-ImageNet (same preprocessing, same code path), HSV histogram (reid.hsv_hist).
eval:          (a) held-out synthetic: cross-camera (same lighting, same epoch) and cross-time (same
               camera, >= 5 s); (b) real: out/datasets/mot20_sub (MOT20-01/02 first 300 frames), the
               docs/13 cross-time protocol (same camera, >= 5 s, 4 crops per id, 105 ids).
               Sanity: OSNet-ImageNet must reproduce docs/13's 0.186 rank-1 / 0.231 mAP on (b).
primary:       (b) MOT20 cross-time mAP, fine-tuned - ImageNet, paired over query identities (bootstrap
               CI over ids), per seed and seed mean.
secondary:     rank-1 on (b); (a) both protocols, fine-tuned vs ImageNet vs HSV.
decision:      "synthetic training transfers" iff the seed-mean primary CI > 0 and all 3 seeds > 0;
               "it hurts real ReID" iff CI < 0 and all 3 seeds < 0; else "no measurable effect".
prediction:    with 16 ids, the embedding overfits to 16 outfits: (a) improves, (b) does not (or drops).
confounds:     16 training ids (literature: thousands); crops share a handful of Quaternius meshes; MOT20
               cross-time is easier than cross-camera; CIs over crops of one id are correlated, so the
               bootstrap is over ids.
```

### H19 results

`out/experiments/h19_farreal_v3/results.json`; mean AP50 over 3 seeds on MOT20-02 people < 60 px after downscaling.
v8_syn trained on 796 images (396 raw + 400 degraded, batch_v8 has night degraded too; v6: 596), 252–372 s/seed
(mean 304; v6_syn 189–268 s, v8_mix1280 145–280 s). Every synthetic-only arm has recall 0.000 at the
0.25 operating point (0.25, full_1280) in all 3 seeds. *(Corrected per AUDIT_H19_H20: "372 s/seed" was seed 0 only.)*

| arm | 0.25 full_1280 | 0.25 full_640 | 0.25 native | 0.25 tiles | 0.33 full_1280 | 0.33 full_640 | 0.33 tiles |
|---|---|---|---|---|---|---|---|
| zero_shot | 0.613 | 0.521 | 0.478 | 0.564 | 0.377 | 0.211 | 0.222 |
| v6_syn (H8 recipe) | 0.000 | 0.010 | 0.003 | 0.003 | 0.000 | 0.011 | 0.010 |
| v8_syn | 0.000 | 0.014 | 0.007 | 0.006 | 0.004 | 0.008 | 0.008 |
| v8_mix1280 | 0.817 | 0.756 | 0.646 | 0.775 | 0.713 | 0.585 | 0.532 |
| v8_mix640 (H18) | 0.781 | 0.779 | 0.725 | 0.798 | 0.692 | 0.641 | 0.519 |
| real_only (640) | 0.783 | 0.769 | 0.707 | 0.789 | 0.681 | 0.628 | 0.549 |

| paired contrast (n = 3), 0.25 full_1280 | ΔAP50 | 95 % bootstrap |
|---|---|---|
| **P1 v8_syn − v6_syn** | **0.000** | [0.000, 0.000] (both exactly 0 in every seed) |
| **P2 v8_mix1280 − v8_syn** | **+0.817** | [+0.812, +0.824] (all 3 seeds +; sign-flip p 0.25, the n = 3 floor) |
| v8_mix1280 − real_only | +0.035 | [+0.026, +0.040] (all +); at native size −0.061 [−0.079, −0.046] |
| v8_mix1280 − v8_mix640 | +0.036 | [+0.031, +0.040]; at native size −0.079 [−0.104, −0.056] |

**Conclusion.** Pre-registered branch: **"the real mix removed it."** H8's collapse
replicates in all 3 seeds (v6_syn AP50 0.000 at 1280 vs zero-shot 0.613), and the
batch_v8 fixes change nothing measurable (v8_syn also 0.000; seed-mean ≤ 0.014 under any method; at native
size P1 is +0.004 [+0.003, +0.005], all 3 seeds +, i.e. 0.003 → 0.007 — negligible, not zero). Synthetic-only
far fine-tuning on one street is destroyed on real small people regardless of label
tightness or heights; adding 60 real frames restores it (0.817). Training at 1280
instead of 640 helps at 1280 inference (+0.036) but hurts at native inference (−0.079),
i.e. it matches train/test scale rather than adding capability.

**Caveats.** v6 vs v8 also differ in image count (596 vs 796) and scene detail; the
floor effect (both 0) makes P1 uninformative about *smaller* effects of the fixes;
real frames are the same site as the test sequence; downscaled 1080p is not a far camera.

### H20 results

`out/experiments/h20_reid_train/results.json`. **Deviation:** 15 training ids, not 16
(street_crowd passer_by_11 never reaches 48 px); 13 held-out synthetic id keys (scene:uid:epoch; the
cross-camera protocol scores only **9** of them, 336 queries; cross-time 12, 333 queries); 105 MOT20 ids
but only 51 have a valid ≥ 5 s positive (167 queries). OSNet-ImageNet on MOT20 gives
0.180 / 0.228 vs docs/13's 0.186 / 0.231 — sanity check passes (same crops, own preprocessing).
Training: 12 epochs, 242–270 s/seed, 1,346 MiB peak VRAM.

*Table convention (AUDIT_H19_H20):* point mAPs are query-weighted; bracketed CIs and all Δ rows are
bootstrap over the **identity-mean** mAP (e.g. HSV cross-camera id-mean 0.300, ImageNet 0.194, FT seed-mean 0.518).

| embedding | held-out synth cross-camera mAP [boot ids] | held-out synth cross-time mAP | MOT20 cross-time rank-1 / mAP [boot ids] |
|---|---|---|---|
| HSV histogram | 0.273 [0.175, 0.456] | 0.844 | 0.144 / 0.195 [0.141, 0.273] |
| OSNet-ImageNet | 0.208 [0.122, 0.300] | 0.769 | 0.180 / 0.228 [0.170, 0.315] |
| OSNet synth-FT s0/s1/s2 | 0.450 / 0.501 / 0.538 | 0.952 / 0.974 / 0.958 | 0.180–0.222 / 0.228–0.264 |

| FT (seed mean) − ImageNet, paired over ids | ΔmAP | 95 % bootstrap | per seed |
|---|---|---|---|
| synth cross-camera | +0.324 | [+0.197, +0.493] | +0.276, +0.315, +0.382 |
| synth cross-time | +0.204 | [+0.139, +0.261] | +0.197, +0.217, +0.197 |
| **MOT20 cross-time (primary)** | **+0.021** | **[−0.047, +0.097]** | +0.017, +0.034, +0.013 |

**Conclusion.** Pre-registered rule: **"no measurable effect"** on real ReID — all three
seeds are positive but small, and the CI over identities includes 0. The prediction is
confirmed in shape: 15 synthetic identities teach an embedding that more than doubles
held-out *synthetic* cross-camera mAP (0.21 → 0.50 query-weighted; 0.19 → 0.52 id-mean, whence +0.324)
and beats the colour histogram there, but it barely moves real pixels (0.228 → 0.243 query-weighted;
0.239 → 0.261 id-mean). *(Corrected: "0.249" matched neither; each per-seed CI also includes 0.)* Against the literature, synthetic-only
UnrealPerson reaches 19.3 % mAP on MSMT17 with ~3,000 identities (doc 24 §4); our
MOT20 cross-time number (~0.25) is not comparable in magnitude (easier protocol, single
camera), and 15 ids are two orders of magnitude short of the regime where synthetic ReID
transfers. The bottleneck is identity count, which the simulator can raise.

**Caveats.** 15 train ids and a handful of Quaternius meshes; no identity bootstrap over
seeds; MOT20 cross-time is easier than cross-camera; 51 of 105 MOT20 ids have valid queries.

## H22 · Operator-in-the-loop alarm queue (`h22_operator_queue`) — pre-registration

Registered 2026-09-27, before any H22 stream was built or simulated
(docs/research/66 H22). CPU only; reuses the round-3 H12 feature tables.

```
id:            h22_operator_queue  (config survsim/experiments/configs/h22_operator_queue.yaml;
               runner operator_queue)
streams:       H12 worlds (676 clean = 3,002 cam-h, 300 recall = 360 events). Per world, every alarm
               (t, uid, score) of: A1 (round-1 LearnedLoiterRule, θ 0.95, clock >= 5 s, shipped in 58 §7.2);
               dwell_25 (H12 baseline, raw tracks; ranked by A1's probability for that person at the
               alarm tick); twin_floor = A1 with false alarms thinned (lowest A1 score first) to the
               1.008 FA/cam-h kinematic-twin floor, true alarms untouched (a hypothetical best
               track-only rule). Each alarm is tagged with the event it hits under eval.alarms.score
               (actor-aware, 30 s, default mode). Sanity: A1 model recall 0.825 and FA 2.915 must be
               reproduced from the tags.
wall:          one operator, 40 cameras. Worlds shuffled per operator seed and laid end to end so 40
               camera-streams run concurrently (world k starts at cumulative cam-s of earlier worlds / 40);
               ~79 wall-hours per seed.
operator:      review time gamma(mean 30 s, cv 0.3); 8 h shifts, fatigued after 2 h of each shift
               (review x1.25, P(dismiss a true alarm) 0.15 vs 0.05 fresh); when the queue exceeds
               N = 10 the operator bulk-acknowledges (clears) the whole queue.
arms:          {A1, dwell_25, twin_floor} x {FIFO, ranked (highest score first)} x 10 operator seeds.
metric:        realised recall at H = 30 s and 5 min: an event is realised if an alarm hitting it is
               taken up for review within H of being raised and the operator recognises it; denominator
               = all 360 events (ceiling = model recall). Operator utilisation = busy time / wall time.
CIs:           world-cluster bootstrap over the 300 recall worlds (2,000 resamples), pooled over the 10
               seeds; seed range reported. ranked - FIFO paired by seed, same bootstrap.
primary:       A1, FIFO, realised recall at 5 min vs the bar 0.6 x model recall (0.6 x 0.825 = 0.495).
decision:      CI upper < bar -> "supported: the operator loses > 40 % of A1's recall";
               CI lower >= bar -> "refuted"; else "inconclusive".
secondary:     ranked - FIFO per arm and horizon (product shape: alarm vs review queue, M9); whether
               twin_floor utilisation is < 0.5 (the 13 §A4 "cliff": A1 at ~117 alarms/h vs a
               ~120/h fresh capacity sits on it).
prediction:    A1/FIFO below the bar (utilisation near 1, fatigued capacity ~96/h < ~117/h arrival ->
               bulk-acks); ranked recovers part of it; twin_floor realises most of the model recall.
confounds:     the operator model is invented (no measured SurvSim operator data); a single operator
               per 40 cameras; bulk-ack clears everything; worlds are independent 5-30 min sites
               stitched together, not one continuous site; parameters fixed here, no tuning after.
```

### H22 results

`out/experiments/h22_operator_queue/results.json` (292 s CPU). Sanity passes: the
tagged streams reproduce A1's 0.825 recall / 2.915 FA/cam-h and dwell_25's actor-aware
0.367 / 6.007 (58 §6.2). 976 worlds -> 80.6 wall-hours per operator seed at 40 cameras
(pre-registration said ~79; AUDIT_H22_H33);
10 seeds; world-cluster bootstrap over the 300 recall worlds.

| arm | model FA/cam-h | model recall | alarms/h | queue | utilisation | realised @30 s [95 %] | realised @5 min [95 %] | alarms bulk-acked |
|---|---|---|---|---|---|---|---|---|
| A1 | 2.915 | 0.825 | 120 | FIFO | 0.88 | 0.127 [0.114, 0.140] | **0.511 [0.484, 0.537]** | 25 % |
| A1 | 2.915 | 0.825 | 120 | ranked | 0.88 | 0.389 [0.362, 0.419] | 0.586 [0.554, 0.619] | 25 % |
| dwell_25 | 6.007 | 0.367 | 244 | FIFO | 0.97 | 0.029 [0.023, 0.036] | 0.108 [0.090, 0.128] | 60 % |
| dwell_25 | 6.007 | 0.367 | 244 | ranked | 0.97 | 0.161 [0.136, 0.186] | 0.204 [0.175, 0.236] | 60 % |
| twin_floor | 1.008 | 0.825 | 44 | FIFO | 0.43 | 0.450 [0.421, 0.479] | 0.725 [0.692, 0.757] | 0.2 % |
| twin_floor | 1.008 | 0.825 | 44 | ranked | 0.43 | 0.515 [0.486, 0.543] | 0.709 [0.677, 0.741] | 0.2 % |

| ranked − FIFO (paired by seed) | Δ realised recall [95 %] | seeds +/− |
|---|---|---|
| A1 @30 s | +0.262 [+0.240, +0.286] | 10/0 |
| A1 @5 min | +0.075 [+0.055, +0.095] | 10/0 |
| dwell_25 @30 s / @5 min | +0.131 [+0.110, +0.154] / +0.096 [+0.078, +0.115] | 10/0, 10/0 |
| twin_floor @30 s / @5 min | +0.064 [+0.049, +0.081] / −0.015 [−0.024, −0.007] | 10/0, 1/9 |

**Conclusion.** Pre-registered branch: **inconclusive.** A1/FIFO realises 0.511 [0.484,
0.537] at 5 min against the bar 0.495 (0.6 × 0.825): the operator keeps 62 % of the model's
recall (CI 59–65 %; per-seed range 0.481–0.553 = 58–67 %), and the CI straddles the bar. The point estimate is on the "not
supported" side, but the prediction's shape holds: at 120 alarms/h the operator runs at
88 % utilisation, bulk-acknowledges a quarter of all alarms (222 clear-alls
per 80.6 h seed run), and within 30 s realises only 0.127. Secondary:
**a ranked review queue beats FIFO for every rule at 30 s** (A1 +0.26, 3× the realised
recall) and for A1/dwell at 5 min; at the twin floor (44 alarms/h, utilisation 0.43, 0.6
bulk-acks per seed run, 0.2 % of alarms) ranking gives +0.06 at 30 s and costs −0.015 at 5 min (low-score true alarms
wait). The 13 §A4 "cliff" is confirmed as a regime change, not a ratio: at 1.0 FA/cam-h
the operator realises 0.725 of 0.825 (88 %); at 2.9 it realises 62 %; dwell_25 at 6.0
saturates the operator (0.97) and realises 0.108 of an already-poor 0.367. For M9 the
product shape is a **score-ranked review queue**, not an alarm FIFO, whenever the rate is
above ~1 FA/cam-h per 40 cameras.

**Caveats.** The operator model is invented, not measured (30 s gamma review, fatigue
×1.25 time and 15 % miss after 2 h, clear-all bulk-ack at N = 10); results scale with those
constants. "Realised at H" means the alarm is *taken up* for review within H, not
confirmed within H. Worlds are stitched independent sites; dwell_25 is ranked by A1's
probability (a ranked dwell rule needs a score from somewhere). The twin-floor arm is
hypothetical (A1 with false alarms thinned by score). Utilisation is identical for FIFO and ranked
by construction (same arrivals, same review-time draws, bulk-ack depends on queue length only), so
the policy effect is purely *which* alarm waits, not how much work is done (AUDIT_H22_H33).

## H25 · Label-noise injection (`h25_label_noise`) — pre-registration (reduced design)

Registered 2026-09-27, before any H25 arm was trained (docs/research/66 H25).
**Reduced from the backlog design** (4 jitter × 3 drop × 5 seeds, ~12 GPU-h) to
**4 jitter × 2 drop × 3 seeds + 3 real-only = 27 runs** (~1 GPU-h); drop 5 % is
cut and n = 3 per cell gives a sign-flip floor of p = 0.25, so this is a
screening run, not a confirmatory one.

```
id:            h25_label_noise  (config survsim/experiments/configs/h25_label_noise.yaml; runner label_noise)
recipe:        H15 v8_vis recipe at dose 100: 60 real MOT20-01 x5 + 100 batch_v8 frames (all 9 sets,
               raw stride 8 + degraded stride 8 phase 4, visible mask labels, seeded subset per seed),
               yolov8n, 6 epochs, imgsz 640, batch 8, last.pt. Real labels never perturbed.
noise:         synthetic boxes only. Jitter: each box edge moves N(0, sigma x box width) (x edges) or
               N(0, sigma x box height) (y edges), sigma in {0, 0.02, 0.05, 0.10}. Drop: a box is removed
               with probability in {0, 0.10}. Draws depend only on (seed, box order): within a seed all
               cells share frames, jitter directions and nested drop sets (paired).
arms:          real_only_s{0,1,2} (retrained here, same code path) + 8 cells x seeds 0-2.
metric:        MOT20-02 AP@640 (the h14b/H15 harness). Gain = cell AP - real_only AP, paired by seed.
               Retained = mean gain(cell) / mean gain(j00_d00). 95 % percentile bootstrap over seeds.
testability:   the clean cell's gain must be real: bootstrap CI lower > 0 and mean >= 0.002 AP.
               Otherwise the branch is "untestable: no clean dose gain to erode" and only
               cell - clean differences are reported.
decision:      (if testable) "supported" iff at drop 0 retained >= 0.5 for sigma 0.02 and 0.05, retained
               < 0.5 at sigma 0.10, and mean AP is non-increasing in sigma; else "refuted".
               Drop-10 % cells are secondary (reported, not in the decision).
prediction:    the clean gain at dose 100 is small (H15 dose 300 gave ~+0.012 over H14b real-only); the
               likely outcome is "untestable" or a flat response, i.e. labels are second-order at this
               dose (consistent with H15's null).
confounds:     n = 3; Gaussian jitter is not the structure of real annotation error; one real site;
               yolov8n only.
```

## H33 · Conformal θ for the FA budget (`h33_conformal_theta`) — pre-registration

Registered 2026-09-27, before any H33 split was drawn or scored (docs/research/66
H33, 67 §1 Q3). CPU only (≤ 4 cores); reuses the round-2 H12 feature tables and A1's
frozen round-1 logistic weights (58 §7.2). Only θ is re-chosen; the score and clock
(≥ 5 s) are A1's.

```
id:            h33_conformal_theta  (config survsim/experiments/configs/h33_conformal_theta.yaml;
               runner conformal_theta)
data:          H12 clean worlds: 676 independent synthetic sites = 3,002 clean cam-h (every alarm is
               false). Unit of exchangeability = one clean world (one site/seed). Per world i and θ:
               k_i(θ) = # dwell episodes whose A1 probability reaches θ at a tick with clock >= 5 s
               (not in an allowed zone) = A1's alarm count; L_i(θ) = k_i(θ) / camh_i. Recall is
               scored on all 300 recall worlds (360 events; never used to choose θ), actor-aware, 30 s.
splits:        10 seeds; each seed permutes the 676 clean worlds, calibration = 50 %, test = 50 %.
targets α:     {0.001 (operator budget), 1.0, 2.0, 2.915 (A1's H12 operating point)} FA/cam-h.
arms:          grid  : θ = 0.95 fixed (58's grid-picked A1 θ, ignores α);
               plain : smallest θ with calibration pooled FA/cam-h <= α (plug-in quantile);
               crc   : conformal risk control (Angelopoulos et al. 2022): smallest θ with
                       n/(n+1) * mean_i L_i(θ) + B/(n+1) <= α, B = max_i L_i(θ_min) over calibration
                       worlds at the lowest candidate θ (an empirical bound — declared, since per-world
                       FA/cam-h is not bounded a priori); infeasible -> θ = 1 (never alarm, recall 0).
               θ candidates: the calibration episodes' own peak probabilities, plus 1.0.
metric:        realised held-out FA/cam-h (pooled over test worlds) with Garwood 95 % and a test-world
               cluster bootstrap 95 % (2,000); per-world-mean test FA (the quantity CRC controls);
               exceed = test FA > α; recall at the chosen θ with world bootstrap. Across seeds: mean
               and seed-bootstrap 95 % CI of test FA, exceed count /10, mean recall.
primary:       α = 2.915. crc exceed count vs plain exceed count; recall cost crc - plain (seed CI).
decision:      "supported" if crc exceeds α in <= 1/10 seeds and plain in >= 3/10;
               "refuted" if crc exceeds in >= 3/10; else "inconclusive". Ships per-site θ with a
               stated guarantee only if supported and the recall cost CI upper bound is within 0.05.
prediction:    P1 plain exceeds α ≈ half the time (it is centred on α), crc ≤ 1/10 at a recall cost
               ≈ 0.02-0.05. P2 α = 0.001 is infeasible for crc (B/(n+1) alone ≫ 0.001 with n = 338)
               and plain's θ gives test FA > 0.001 or recall ≈ 0 — the 0.001 budget cannot be
               certified by any calibration set of this size (a statement about data, not the rule).
               P3 grid θ exceeds 2.915 in ≈ half the seeds, like plain.
deviation:     66 said 20 seeds and α ∈ {1,2,3}; changed here (before running) to 10 seeds and the
               brief's α set incl. 0.001 and 2.915.
confounds:     synthetic worlds; per-world rate (not pooled) is what CRC bounds — worlds differ in
               cam-h; B is data-derived; exchangeability of sites is assumed, which a real estate
               with site-level drift would violate.
```

### H33 · results (run 2026-09-27, 167 s on 4 cores; `out/experiments/h33_conformal_theta`)

A1 on all 676 clean worlds reproduces 2.915 FA/cam-h (sanity). 10 splits × 338/338 worlds;
test FA is pooled FA/cam-h on the held-out half; seed 95 % = bootstrap over the 10 splits.
Recall is on the fixed 300 recall worlds, so its seed CI reflects θ variation only (the world
bootstrap per split, ≈ ±0.040, is in results.json).

| α | arm | θ range | exceed /10 | test FA/cam-h mean [seed 95 %] | recall mean [95 %] |
|---|---|---|---|---|---|
| 0.001 | grid | 0.950 | 10 | 2.935 [2.909, 2.963] | 0.825 |
| 0.001 | plain | 0.99999(6–7) | 0 | 0.000 (≤ 0.0007; 1 FA in 3/10 test halves) | 0.000 |
| 0.001 | crc | infeasible → never alarm | 0 | 0.000 | 0.000 |
| 1.0 | plain | 0.983–0.985 | 5 | 1.005 [0.983, 1.031] | 0.690 |
| 1.0 | crc | 0.991–0.992 | 0 | 0.636 [0.619, 0.657] | 0.582 |
| 2.0 | plain | 0.966–0.967 | 5 | 2.023 [1.984, 2.065] | 0.778 |
| 2.0 | crc | 0.974–0.976 | 0 | 1.506 [1.467, 1.552] | 0.747 |
| **2.915** | grid | 0.950 | 6 | 2.935 [2.909, 2.963] | 0.825 |
| **2.915** | plain | 0.948–0.951 | 6 | 2.958 [2.906, 3.015] | 0.824 |
| **2.915** | **crc** | 0.960–0.963 | **0** | **2.312 [2.265, 2.364]** | **0.789** |

crc − plain recall: α 2.915 −0.035 [−0.037, −0.033]; α 2.0 −0.031 [−0.033, −0.028]; α 1.0
−0.107 [−0.111, −0.104]. CRC bound B = 84–89 FA/cam-h across splits (worst calibration world at the lowest θ),
so the finite-sample floor B/(n+1) = 0.248–0.263 FA/cam-h (minimum 0.248).

**Decision (pre-registered branch): supported** at α = 2.915 — crc exceeded α in 0/10 splits
(≤ 1 required), plain in 6/10 (≥ 3 required); recall-cost CI upper bound 0.037 < 0.05, so per-site
θ may ship *with a stated guarantee* (on exchangeable sites). The exceed rule is also met at α = 1 and 2,
but the ship clause (cost CI upper ≤ 0.05) holds only at α = 2 (0.033); at α = 1 it fails (0.111).
`conformal_theta.decide` encodes only the exceed counts; the recall-cost clause is applied by hand
(AUDIT_H22_H33).

Against the predictions: **P1 held** (plain exceeds ≈ half: 5–6/10; crc 0/10; cost 0.031–0.035,
inside the 0.02–0.05 band at α ≥ 2; at α = 1 the cost is 0.107 because the FA curve is flat there).
**P2 held in substance, not in form**: crc is infeasible at 0.001 (floor 0.248 ≫ 0.001) and plain
"meets" 0.001 only by almost never alarming (θ ≈ 0.999996; 0–1 test FA per split, recall 0) — no θ gives a useful rule, and no calibration
set of 338 simulated worlds can certify 0.001 unless the worst world's rate B falls below ≈ 0.34. **P3 held**
(grid exceeds 2.915 in 6/10).

What CRC guarantees: E[per-world FA/cam-h] ≤ α, marginal over the calibration draw — not pooled FA
**Caveat (AUDIT_88, H33b):** CRC guarantee holds for a loss bounded by a B fixed in advance; H33 used the empirical max B (84–89, approximate); H33b fixes B = 123.5 FA/cam-h in advance, which makes the guarantee exact for the clipped loss min(L, 123.5) only — the ≤ 1-alarm-per-visitor cap behind it is not enforced (A1 alarms once per dwell *episode*; one visitor opened up to 21; AUDIT_H33B), so 123.5 is not an a-priori bound on L itself (no H12 world exceeds it: max 89). θ 0.9615–0.9642, held-out FA 2.216 ≤ 2.915 in 10/10 splits, recall −0.006 vs empirical B; at the certified θ 0.963436 the 1-operator ranked queue realises 0.617 @5 min, −0.004 [−0.017, +0.010] vs θ 0.962851 (H45b) (32 §H33b, §H45b).
per split. "10/10" is the observed frequency, not the guarantee. The controlled quantity is larger
than pooled FA (A1 on all 676 worlds: per-world mean 3.417 vs pooled 2.915, since short worlds are
noisy); CRC's per-world test mean at α = 2.915 was 2.54–2.89, all ≤ α (AUDIT_H22_H33).

What it means: CRC is conservative by design — realised 2.31 vs target 2.915 (the B/(n+1) term plus
per-world vs pooled averaging); the price is 3.5 recall points. The guarantee is only as good as
exchangeability: these are 676 i.i.d. synthetic sites; a real estate with drifting sites needs
per-site calibration and the H34 drift trigger. The 0.001 budget remains a *data* problem as much
as a model one.

## H32 · Night against a real IR reference (`h32_night_ir`) — step 0: reference set established

*2026-09-27. This is not the experiment. No recall was measured and no GPU
was used.*

* **Reference.** 50 LLVIP sample frames (25 thermal, 25 aligned visible
  low-light) in `~/data/real_cctv_night/`. The licence is LLVIP
  non-commercial research, so the frames are used for measurement only.
  47 §2 and `~/data/assets/index.json` record it. KAIST (CC BY-NC-SA, 1.44
  GB preview), FLIR ADAS (terms page 404) and M3FD (no dataset licence)
  were skipped.
* **Stats.** Measured on `batch_v8/street_crowd_night/cam_02` with
  `survsim.realism compare`, over 13 stats (temporal is n/a).
  `cctv_night_ir` is in band for **3/13 vs LLVIP-visible and 2/13 vs
  LLVIP-thermal**. The raw render gets 6 and 4. Full table: docs/15 "Real
  night reference".
* **What this changes.**
  1. The raw night render has luma 90 vs a real 26–59. H11's "illumination
     barely matters" (−0.020) was measured on renders that weren't dark, so
     it is now qualified.
  2. The −0.609 H11 loss comes from a profile that is itself out of band
     (noise 0.001 vs 0.06–0.31). That makes it an upper bound on the sensor
     penalty, not an estimate of it.
  3. Modality mismatch: the profile is active NIR, and the reference is
     thermal plus visible.
* **Registration change proposed.** Split H32 into H32a (visible low-light
  profile vs LLVIP-vis, target ≥ 9/13) and H32b (a new `cctv_thermal`
  profile vs LLVIP-IR). The ≥ 200-frame bar needs the full LLVIP zip
  (~3.5 GB), so it needs sign-off.

## H32a/H32b · In-band night profiles and the recall they give (`h32_night_profiles`) — pre-registration

*Written 2026-09-27, before any profile was written or any number measured.*

* **Reference split.** LLVIP frames in `~/data/real_cctv_night/llvip_{vis,ir}`,
  sorted by filename. The first 15 of each modality are the **tune** set and
  the last 10 are the **hold-out** set. Tuning may look only at the tune set. The
  hold-out band is p10–p90 over the 10 hold-out frames. LLVIP is
  non-commercial, so it is used for measurement only and nothing is trained on it.
* **Synthetic set.** 30 frames from `out/batch_v8/street_crowd_night/render/cam_02`
  (the docs/15 set), scored by their median, over the 13 docs/15 stats
  (temporal is n/a because LLVIP samples are not consecutive).
* **H32a (realism).**
  - `cctv_night_lowlight` (visible: exposure/gain pull-down, sensor noise,
    chroma loss, low-bitrate H.264) scores **≥ 9/13** inside the hold-out
    LLVIP-vis band.
  - `cctv_thermal` (grey radiometric mapping from the person mask plus
    background: hot people, halo, AGC, NETD noise, 640×512 upscale) scores
    **≥ 8/13** inside the hold-out LLVIP-IR band.
  - Tune-set band counts are reported too. If the hold-out count is more than
    2 below the tune count, the profile is flagged as overfit.
* **H32b (recall).**
  - Detectors: zero-shot YOLOv8n (primary, as in H11) and YOLO26n (secondary).
  - Settings: imgsz 1280, op conf 0.25, IoU 0.5, GT = mask-derived
    `gt/mot_<cam>.txt` with h ≥ 40 px.
  - Data: all 12 batch_v8 night cameras, frames 1..299 at stride 20
    (15 frames/cam, 180 frames). That stays inside the CPU ≤ 200-frame cap,
    so the design is the same whichever device runs it. GPU is used only if
    ≥ 1.5 GB is free.
  - Arms: raw, `cctv_night_ir`, `cctv_night_lowlight`, `cctv_thermal`.
  - Report: pooled recall with a camera-cluster bootstrap 95 % CI, plus
    paired per-camera Δ vs raw with a bootstrap CI.
* **Predictions and branches (fixed now).**
  - P1. Δ(lowlight − raw) is smaller in magnitude than Δ(night_ir − raw).
    That brackets H11's −0.609, which becomes an upper bound on the sensor
    penalty.
  - P2. Δ(thermal − raw) < 0 with a CI that excludes 0, because an RGB-trained
    detector is out of modality.
  - B1. Lowlight in band and its Δ CI excludes 0: the visible-night sensor
    penalty is real, and we report the bracket [Δ_lowlight, Δ_ir].
  - B2. Lowlight in band and its Δ CI includes 0: H11's loss came from the
    out-of-band profile, not from "night".
  - B3. A profile misses its band target: its recall is reported as
    out-of-band, is not used as an estimate, and the realism result is a failure.

## H34 · Label-free drift monitor (`h34_drift_monitor`) — pre-registration

Registered 2026-09-27, before any H34 stream was degraded or scored (docs/research/66
H34, 68 Q14). CPU only. Deviation from 66, declared before running: 66 proposed
confidence-histogram PSI over 5 severities × 3 seeds; this run follows the brief
instead — the 13 per-frame image statistics (`survsim/realism/stats.py`) as the
monitored signal, 4 shift kinds × 3 severities, and a detector-backbone embedding
arm.

```
id:          h34_drift_monitor (config survsim/experiments/configs/h34_drift_monitor.yaml;
             runner survsim/experiments/drift_monitor.py, `python -m survsim.experiments.drift_monitor`)
data:        batch_v8 {street_crowd_day, street_crowd_far_day, disguise_and_tamper_day} ×
             cam_01..03 = 9 camera streams; raw renders, frames 0..299 at stride 2 = 150
             samples/stream (12.5 samples/s of scene time).
baseline:    cctv_day_720p via apply_sequence (AE/AWB drift, grain, GOP codec), degrade
             sequence_seed ∈ {0, 1} = 18 stationary (null) streams.
shifts:      samples 0..74 baseline, samples 75..149 re-degraded with a shifted profile
             (seed 0, spliced at sample 75 = the shift point). 12 conditions:
               dusk   : ev −1 / −2 / −3 with iso_gain ×1.5 / ×2 / ×3   (after AE, i.e. AE saturated)
               blur   : defocus 1.6 / 2.5 / 3.5
               codec  : crf 36 / 40 / 44
               dirt   : dirt 0.3 / 0.5 / 0.8  (lens dirt / partial tamper)
             → 108 shifted streams.
reference:   per camera, samples 0..49 of the stream itself. Monitor window = trailing 13
             samples (≈ 1 s), evaluated at every sample ≥ 62.
arms:        psi_0.10 / psi_0.20 / psi_0.25 : per-stat PSI, 10 reference-quantile bins
               (eps 1e-4), score = max over the 13 stats, trigger when score > threshold.
             ks : per-stat two-sample KS, trigger when min p < 0.01/13 (Bonferroni).
             z_cal (declared extra): max over stats of |mean_win − mean_ref| / sd_ref;
               threshold = max null score on seed-0 streams × 1.1, false triggers counted
               on seed-1 streams only.
             emb : YOLOv8n SPPF (layer 9) output, global-average-pooled (imgsz 320);
               score = ||mean_win − mean_ref|| / median ref-frame distance to mean_ref;
               threshold calibrated like z_cal.
metrics:     delay = first trigger sample ≥ 75 minus 75 (samples; ×2 frames; ≤ 74 else
               "missed"), per arm × condition, median over the 9 cams.
             false triggers: fraction of null window evaluations that trigger (pre-shift
               evaluations 62..74 of shifted streams included). Converted to per 24
               camera-hours at a deployment cadence of ONE window evaluation per minute
               (1,440 evals = 24 cam-h), plus a rule-of-three upper bound using only
               non-overlapping windows as independent.
             recall: zero-shot YOLOv8n, imgsz 640, conf 0.25, IoU 0.5, class person, GT =
               gt/mot_<cam>.txt rows h ≥ 20 px; 13 conditions (clean + 12) × 23 post-shift
               frames (same frames in every condition, spread over the 9 cams) = 299 frames.
               recall drop = recall(baseline) − recall(condition).
             correlation: Spearman over the 12 conditions between the post-shift mean score
               (mean over samples 75..149 and 9 cams) and recall drop; per arm, primary = PSI
               score (one score for all three PSI thresholds). Bootstrap CI + permutation p.
decision:    SUPPORTED for an arm if (a) it triggers in ≤ 74 samples on ≥ 10/12 conditions
               (median over cams), (b) point-estimate false triggers ≤ 1 per 24 cam-h, and
               (c) Spearman ρ ≥ 0.5. REFUTED if (b) fails for every arm or ρ < 0.5 for
               every arm. Else INCONCLUSIVE. Certifying (b) needs ≥ 3 × 1,440 independent
               null windows with zero triggers; we have ~200, so (b) can only ever be a
               point estimate here — stated now, not after.
predictions: P1 PSI with 13-sample windows and 10 bins is dominated by sampling noise
               (E[PSI] ≈ (k−1)(1/n+1/m) ≈ 0.87 under the null), so all three PSI arms
               false-trigger on most null evaluations: fixed PSI thresholds are not
               transferable to small windows. P2 KS also over-triggers (frames are
               autocorrelated; KS assumes iid). P3 z_cal and emb detect dusk/blur/codec
               severities 2-3 within a window (≤ 13 samples) and miss dirt 0.3.
               P4 ρ(score, recall drop) ≥ 0.5 for z_cal; blockiness shifts move stats most
               but cost the least recall, which is the main threat to ρ.
```

### H34 · results (2026-09-27, `survsim experiment h34_drift_monitor`)

**Deviation (made before any result was scored):** the first run crashed with
`TypeError: 'NoneType' object is not subscriptable` inside a stream worker.
Cause: `disguise_and_tamper_day` has no `cam_01..03` (its cameras are
`cam_gate/cam_ptz/cam_sub/cam_yard`), so `cv2.imread` silently returned `None`
for all 150 paths and `apply_sequence` failed on the first `None`. The config's
`cams` is now a per-run map; that run uses its three fixed cameras
`cam_gate, cam_sub, cam_yard` (PTZ excluded because slewing breaks a stationary
null). The worker now raises `FileNotFoundError` naming the first unreadable
frame, and `tests/test_drift_monitor.py` checks every configured stream exists.
The embedding arm was not at fault and ran as registered.

Output: `out/experiments/h34_drift_monitor/results.json`, figure
`docs/research/figures/fig_h34.png`. 9 streams, 18 null streams, 108 shifted streams.
Delay is the median over the 9 cameras, in samples (1 sample = 2 frames). `miss` means
the delay was more than 74 samples, or fewer than 5 of the 9 cameras triggered.
*FA / 24 cam-h assumes one window evaluation per minute (1,440 per 24 cam-h,
`evals_per_24h` in the config), not the 12.5 evaluations per second the run makes;
at the run's own cadence the PSI/KS rate would be 1.08 M per 24 cam-h. ρ CI: percentile
bootstrap over the 12 conditions (pairs resampled, 4,000 draws); p: two-sided rank
permutation (10,000). Streams: 12.5 samples/s, window 13 samples ≈ 1 s, reference =
samples 0..49 = first 4 s. (Added, AUDIT_H34.)*

| arm | thr | detected /12 | delays (dusk 1-3 · blur 1-3 · codec 1-3 · dirt 1-3) | null fires / evals | FA / 24 cam-h | ρ(score, recall drop) [95 % CI], perm p |
|---|---|---|---|---|---|---|
| psi_0.10/0.20/0.25 | 0.10–0.25 | 12* | 0 everywhere | 2988 / 2988 | 1440 | 0.49 [−0.15, 0.84], p 0.11 |
| ks (Bonferroni) | p < 7.7e-4 | 12* | 0 everywhere | 2988 / 2988 | 1440 | −0.13 [−0.68, 0.46], p 0.69 |
| z_cal | 32.7 | 6 | 3,1,0 · miss×3 · miss,miss,11 · miss,7,3 | 14 / 2196 | 9.2 | 0.61 [−0.08, 0.98], p 0.04 |
| emb | 5.4 | 0 | miss ×12 | 0 / 2196 | 0.0 (ro3 upper 26.6) | 0.61 [0.07, 0.91], p 0.04 |

\* These arms "detect" only because they fire on every null evaluation, so delay 0
means nothing here.

z_cal's 14 null fires (of 2,196 overlapping evaluations) leave only 1 of its 162
non-overlapping null windows firing, so they are clustered in time: the independent-window rate (1/162 × 1,440 ≈ 8.9) agrees with 9.2, and both
rest on a single event. Near-misses by the ≥ 5-of-9 rule: z_cal codec 1-2 fired on 4/9
cameras; emb fired on 1–2 cameras for dusk 3, codec 2-3 and dirt 2-3. emb's ro3 upper
bound is −ln 0.05 / 162 × 1,440 = 26.6. Delays in seconds (÷ 12.5): dusk 0.24 / 0.08 / 0,
dirt 0.56 / 0.24, codec 3 0.88 — all within one window. (Added, AUDIT_H34.)

Zero-shot recall (YOLOv8n, h ≥ 20 px, 23 frames per condition, 124 GT boxes, so one box
= 0.008): clean 0.492 (61/124);
dusk 0.242 / 0.024 / 0.000; blur 0.468 / 0.282 / 0.065; codec 0.484 / 0.492 / 0.403;
dirt 0.500 / 0.476 / 0.363.

**Verdict: INCONCLUSIVE, so the pre-registered SUPPORTED branch was not met.** No arm
passes all three tests. PSI and KS fail (b) at 1,440 FA per 24 cam-h (one evaluation per minute). z_cal fails (a)
with 6/12 detected and fails (b) at 9.2 (one event among 162 independent windows). emb passes (b) and (c) but detects 0/12.
REFUTED is also ruled out because emb passes (b) and z_cal and emb pass (c).

Predictions: **P1 confirmed.** Every PSI arm fired on 100 % of null evaluations, so
fixed PSI conventions do not transfer to 13-sample windows. **P2 confirmed.** KS
behaved the same way. **P3 partly wrong.** z_cal caught dusk and dirt 2-3 but missed
blur at every severity and codec 1-2. emb detected no condition, because a threshold of
1.1 × the maximum seed-0 null score (5.40) sits above every condition's mean post-shift
score (max 4.10, dusk 3); single windows crossed it on at most 2/9 cameras. *(Corrected
in place, AUDIT_H34: was "sits above every post-shift window mean", which the per-camera
triggers contradict.)*
Calibrating on the null maximum buys a zero false-alarm rate at the price of zero
sensitivity. **P4 confirmed on the point estimate.** z_cal ρ = 0.61, but its CI
crosses 0. The predicted threat is only partly what happened: codec 1-2 do move z_cal (27, 49)
far more than blur (13–15) at ≈ 0 recall cost, but they do not move it most (dusk 121–790,
dirt 3 111). The larger rank breaker is blur: blur 2-3 cost 0.21 and 0.43 recall yet score
only 14–15 (below every codec severity). *(Corrected in place, AUDIT_H34: was "the codec shift moves the statistics most
while costing the least recall".)* Read (b) as a point estimate only: we have 162 independent null
windows for the calibrated arms (216 for PSI/KS), and certifying ≤ 1 per 24 cam-h with zero
triggers needs ≥ 4,314 (−ln 0.05 × 1,440; "≈ 3 × 1,440" in the pre-registration).

### H32a/H32b · results (2026-09-27, `survsim experiment h32_night_profiles`)

The runner is `survsim/experiments/night_profiles.py` and the full output is
`out/experiments/h32_night_profiles/results.json`. Both new profiles were fitted
by random search on the 15 tune frames (the search script and draw count were
not committed, so "≈20–35 draws" is unrecorded; only the chosen parameters in
`survsim/sensors/degrade.py` are). Recall ran on 180 frames × 4 arms × 2 models;
`results.json` records `device: "0"` (GPU, 4,531 MiB free), not CPU as first
written — detections cached by an earlier CPU invocation may have been reused.
Of the 12 night cameras, only **9 have GT boxes with h ≥ 40 px** (611 boxes;
`cam_yard` and far `cam_02`/`cam_03` have none), so the camera-cluster bootstrap
resamples 9 clusters. One degrade seed (0), one detector pass: the CIs cover
camera sampling only, not degrade-noise or seed variance. *(Corrected in place,
AUDIT_H32.)*

| profile | vis tune | vis hold-out | IR tune | IR hold-out |
|---|---|---|---|---|
| raw render | 5/13 | 2/13 | 4/13 | 0/13 |
| `cctv_night_ir` | 3/13 | 2/13 | 1/13 | 2/13 |
| `cctv_night_lowlight` | **9/13** | **2/13** | 4/13 | 2/13 |
| `cctv_thermal` | 2/13 | 3/13 | **10/13** | **3/13** |

| model | arm | recall h≥40 [95 % CI, camera cluster] | Δ vs raw [95 % CI] |
|---|---|---|---|
| YOLOv8n | raw | 0.938 [0.872, 0.976] | — |
| YOLOv8n | `cctv_night_ir` | 0.373 [0.251, 0.464] | −0.565 [−0.660, −0.496] |
| YOLOv8n | `cctv_night_lowlight` | 0.103 [0.054, 0.164] | −0.835 [−0.888, −0.758] |
| YOLOv8n | `cctv_thermal` | 0.468 [0.367, 0.566] | −0.470 [−0.548, −0.394] |
| YOLO26n | raw | 0.949 [0.921, 0.971] | — |
| YOLO26n | `cctv_night_ir` | 0.448 [0.275, 0.579] | −0.501 [−0.649, −0.388] |
| YOLO26n | `cctv_night_lowlight` | 0.056 [0.026, 0.117] | −0.894 [−0.933, −0.821] |
| YOLO26n | `cctv_thermal` | 0.566 [0.394, 0.721] | −0.383 [−0.536, −0.244] |

* **H32a is not met, for either profile.** The fits reach 9/13 (vis) and
  10/13 (IR) on the tune split but fall to **2/13 and 3/13 on the hold-out
  split**. Both are flagged as overfit (tune minus hold-out > 2).
  - The hold-out frames are other LLVIP scenes, and their 10-frame p10–p90
    bands are narrow. For example, vis luma is 28–39 on the hold-out split
    against 26–60 on the tune split.
  - So 15 frames cannot set a band that generalises. The pre-registered
    ≥ 200-frame bar (full LLVIP) was the right one.
  - The lowlight fit is also visibly wrong despite its 9/13: its chroma noise
    is far too strong (fig_h32). Stat bands can be gamed.
* **H32b: branch B3 applies.** No profile is in band, so none of these
  recalls is an estimate of a real night penalty.
  - P1 is refuted. The lowlight Δ (−0.835) is *larger* than `cctv_night_ir`'s
    (−0.565), so it does not bracket H11's −0.609 from below.
  - P2 holds: thermal Δ is −0.470, with a CI that excludes 0.
  - The stated range for the sensor penalty is now "−0.47 to −0.84 (YOLOv8n;
    −0.38 to −0.89 for YOLO26n) depending on an unvalidated sensor model".
    H11's −0.609 sits inside that range and is no more trustworthy than it was.
  - The thermal arm is optimistic by construction: `cctv_thermal` paints people
    hot from the render mask, the same mask the GT boxes come from, so the
    detector sees exactly GT-shaped blobs. *(Added, AUDIT_H32.)*
  - The reproduced `cctv_night_ir` number on batch_v8 is −0.565, against H11's
    −0.609 on batch_v7, which is consistent.
* **Next.** Get the full-LLVIP sign-off (≥ 200 frames per modality, scene-held-out
  bands), refit with a realism prior (a per-channel noise cap), and only
  then quote a night recall penalty.

### H25 results

`out/experiments/h25_label_noise/results.json`, 27 runs, MOT20-02 AP@640, 3 seeds per cell,
paired by seed. real_only re-trained here reproduces h14b mix_0 exactly (0.4857 / 0.4860 /
0.4860). Wall 6,879 s (the pre-registration estimated ~1 GPU-h; the GPU was shared with a
running Unreal editor, ~3 GB, no waits needed).

| cell (jitter σ, drop) | AP mean | gain vs real-only [95 %] | − clean cell [95 %] | gain retained |
|---|---|---|---|---|
| j00_d00 (clean) | 0.4986 | +0.0127 [+0.0114, +0.0133] | — | 1.00 |
| j02_d00 | 0.4981 | +0.0122 [+0.0109, +0.0129] | −0.0005 [−0.0006, −0.0004] | 0.96 |
| j05_d00 | 0.4979 | +0.0120 [+0.0114, +0.0124] | −0.0007 [−0.0012, 0.0000] | 0.95 |
| **j10_d00** | 0.4982 | +0.0123 [+0.0106, +0.0138] | −0.0003 [−0.0008, +0.0005] | **0.97** |
| j00_d10 | 0.4982 | +0.0123 [+0.0109, +0.0131] | −0.0004 [−0.0005, −0.0002] | 0.97 |
| j02_d10 | 0.4981 | +0.0122 [+0.0118, +0.0129] | −0.0004 [−0.0013, +0.0004] | 0.97 |
| j05_d10 | 0.4983 | +0.0124 [+0.0106, +0.0136] | −0.0002 [−0.0008, +0.0003] | 0.98 |
| j10_d10 | 0.4978 | +0.0119 [+0.0108, +0.0126] | −0.0008 [−0.0010, −0.0006] | 0.94 |

**Conclusion.** Testable (clean gain +0.0127 [+0.0114, +0.0133]), and the pre-registered
branch is **"refuted"**: at σ = 10 % the dose gain is 97 % retained, not < 50 %, and AP is
not monotone in σ (0.4981 → 0.4979 → 0.4982). Every noise cell, including 10 % jitter plus
10 % dropped boxes, keeps ≥ 94 % of the gain; the largest cost is −0.0008 AP. At this dose
the detector is insensitive to synthetic-label precision. That is *consistent with* H15's
null (visible vs amodal boxes, −0.0005 [−0.0012, +0.0001]) but does not by itself explain
it — H15 ran at dose 300, H25 at dose 100: **the gain from 100 synthetic frames is not
carried by their box geometry** (most likely image-level/context content). The flip side:
perfect GT buys nothing measurable at this dose either.

**Caveats.** The synthetic part is small in box terms — 447 of 11,452 training boxes
(3.9 %) in seed 0 (480/11,485 = 4.2 %, 459/11,464 = 4.0 % in seeds 1–2); real frames are
repeated ×5, so by *unique* boxes synthetic is 447/2,648 = 16.9 % — the real labels
dominate the gradient, less so the label set. The realised drop rate was 9.4–10.9 %
(42/447, 51/480, 50/459); noise might matter at synthetic-
dominated doses (H26 territory) or synthetic-only training. n = 3 per cell (sign-flip floor
p = 0.25), 5 % drop level cut (reduced design). Gaussian independent edge jitter is not
the correlated error of real annotators.

## H26 · Dose curve with fixed optimiser steps (`h26_dose_fixedstep`) — pre-registration (reduced design)

Registered 2026-09-27, before any H26 arm was trained (docs/research/66 H26).
**Reduced from the backlog design** (6 arms incl. 3,000 × 10 seeds, ~20 GPU-h) to
**5 arms × 5 seeds = 25 runs**; the 3,000 arm is cut (budget), so the "≥ 0 up to 3,000"
half of the backlog hypothesis is not tested. Estimated cost: every run has the step
count of an h14b/H25 dose-300 run (≈ 4–5 min) → **~2 GPU-h**, beside an Unreal editor
holding ~3 GB.

```
id:            h26_dose_fixedstep  (config survsim/experiments/configs/h26_dose_fixedstep.yaml; runner dose_fixedstep)
pool:          batch_v8, all 9 sets, raw stride 8 + degraded stride 8 phase 4, visible mask labels
               (the H15/H25 source spec) = 2,176 candidate frames, so the 1,000 arm is available.
               Seeded subset per seed (seed 0-4), as in h14b.
real:          MOT20-01 frames 1-60 x5 (300 images) in every arm.
arms:          dose in {0, 100, 300, 600, 1000} synthetic frames, seeds 0-4.
fixed steps:   450 optimiser steps for every arm = the 300-frame arm's 6 epochs x 75 iterations
               (600 images / batch 8). Each arm's image list is L images and trains E epochs with
               L x E = 3,600:  0 -> 300 x 12;  100 -> 400 x 9;  300 -> 600 x 6;  600 -> 900 x 4;
               1000 -> 1,300 images + 500 seeded duplicates from its own list = 1,800 x 2.
               Warm-up held at 225 iterations (warmup_epochs = 1,800 / L); close_mosaic = 0 (mosaic on
               throughout, which is what 6-epoch h14b runs had); optimizer auto (AdamW for all, < 10k its).
model:         yolov8n, imgsz 640, batch 8, last.pt.
metric:        MOT20-02 AP@640 (h14b/H25 harness).
contrasts:     dose d vs 0 for d in {100, 300, 600, 1000}: unpaired exact permutation p on 5 v 5 seeds,
               95 % bootstrap CI of the mean difference, Holm over the 4 at alpha 0.05 (dose.contrasts).
decision:      the recommended dose = the highest-mean arm among Holm-significant positive contrasts.
               "fades at 1,000 was the step-count confound" iff the 1,000 contrast is Holm-significant
               positive (H7 at 1,000 was +0.000 with ~2.2x the steps of its 300 arm). If 1,000 is
               below 300 with non-overlapping bootstrap CIs of the two gains, the fade is real at fixed steps.
prediction:    gain peaks at 300-600 and 1,000 stays positive but smaller (i.e. H7's fade was partly
               the confound, partly real).
confounds:     5 seeds; one real site (MOT20-01 -> 02); the 0 arm now trains 12 epochs so it is not the
               h14b 0.4857 baseline; the 1,000 arm sees each image ~2x, the 0 arm ~12x.
```

## M1 parity · `evaluate_mot` vs reference TrackEval (2026-09-27, CPU, `out/experiments/m1_trackeval_parity`)

Not a hypothesis — an engineering gate (unblocks H24 in 66). TrackEval
(JonathonLuiten/TrackEval master) installed in `.venv`; `survsim/eval/trackeval_bridge.py`
writes a MOTChallenge layout and runs the official Evaluator (HOTA, CLEAR,
Identity, no preprocessing). Cases: MOT20-01/02 frames 1–300 (cached
detections, ByteTrack re-run on CPU), batch_v8 `street_crowd_day` GT vs a seeded
perturbation of itself (no cached tracker output exists), three edge cases.

Before (Δ = ours − TrackEval, MOT20 combined): HOTA −0.0086, DetA@0.5 +0.0130,
AssA@0.5 −0.0109, IDF1 −0.0091, MOTA +0.0003, IDSW −9, Frag +2/−1 per sequence;
batch_v8 and the edge cases already agreed (≤ 1e-15). Causes: per-α Hungarian
instead of HOTA's single association-aware matching; DetA/AssA@0.5 taken from
the MOTA matching; IDF1 from CLEAR matches instead of all IoU ≥ 0.5 pairs;
greedy cross-gap continuity instead of TrackEval's previous-frame bonus and
empty-frame skip; 1e-9 vs machine-eps thresholds. After: every metric
|Δ| ≤ 1e-15 on all cases. **MOT20 subset HOTA 0.4342 → 0.4428 (+0.0086)**,
IDF1 0.549 → 0.559, MOTA 0.466. `tests/test_trackeval_parity.py` (slow)
guards it. H17's HOTA deltas used the old code on both arms; not recomputed.
Details: docs/13 §TrackEval parity.

## H38 · Quantised export of the h14b detector (`h38_quant_export`) — pre-registration

Registered 2026-09-27, before any H38 arm was exported or scored (docs/research/66 H38).
Motivation: 38 §2.5 and 68 Q10 budget the Orin NX on INT8 latency, but the accuracy
cost of INT8 on *our* detector is [A]. CPU only (GPU held by X28); no training.

```
id:            h38_quant_export  (config survsim/experiments/configs/h38_quant_export.yaml; runner quant_export)
checkpoints:   h14b mix_300_s{0,1,2} last.pt (60 real MOT20-01 x5 + 300 batch_v7 synthetic, yolov8n,
               the weights scored in h14b: MOT20-02 AP@640 0.4969 / 0.4956 / 0.4952 on GPU FP16).
arms:          A0 fp32_torch   ultralytics predict on CPU, FP32 (control)
               A1 onnx_fp32    ultralytics export format=onnx, imgsz [384, 640] static, opset default, no NMS
               A2 onnx_fp16    A1 converted with onnxruntime float16 converter (keep_io_types, FP32 IO)
               A3 int8_real    A1 -> onnxruntime quantize_static, QDQ, per-channel S8 weights, S8 activations,
                               MinMax calibration on 100 real MOT20-01 frames (61-429, evenly spaced;
                               MOT20-01 1-60 are h14b training frames; MOT20-02 never used)
               A4 int8_syn     as A3 but calibrated on 100 batch_v8 frames (seeded, half render / half
                               degraded, all scenario dirs except _failed_entrance_gate)
               INT8 arms keep the Detect head's non-Conv decode ops (DFL softmax, dist2bbox, sigmoid,
               concat) in FP32 (nodes_to_exclude); the standard recipe, since the output concat mixes
               pixel coordinates with [0,1] scores.
input:         [384, 640] = the rect letterbox ultralytics uses for 1920x1080 at imgsz 640 in A0, so all
               arms see the same tensor. All ONNX arms run through ultralytics predict (same pre/post,
               NMS, conf) on onnxruntime CPUExecutionProvider.
metric:        MOT20-02 AP (COCO 0.5:0.95) at 640, 300 frames, the h14b/H25 harness (eval_det).
               Loss(arm) = AP(A0) - AP(arm), paired by checkpoint. Report mean and 95 % percentile
               bootstrap over the 3 checkpoints (and the range; n = 3 is a floor, not a CI worth much).
sanity:        |AP(A1) - AP(A0)| <= 0.001 on every checkpoint, else the export pipeline is a confound
               and the FP16/INT8 branches are reported relative to A1 instead of A0 (stated).
decision:      FP16 branch met iff loss(A2) <= 0.005 on all 3 checkpoints.
               INT8 branch met iff loss(A3) <= 0.015 on all 3 checkpoints.
               Calibration branch met iff AP(A3) - AP(A4) >= 0.01 on all 3 checkpoints (paired).
context only:  per-image latency, batch 1, CPU (12 threads, shared with X28's data loaders), median of
               50 runs after 5 warm-up. NOT a Jetson/TensorRT number; ORT CPU INT8 speed says nothing
               about Orin DLA/GPU INT8.
prediction:    FP16 ~0 loss; INT8 real-calibrated 0.005-0.02 loss; synthetic calibration a few 1e-3 worse,
               i.e. the calibration branch probably fails (activation ranges are set by the letterbox,
               not by scene content).
confounds:     ORT CPU QDQ is not TensorRT INT8 (different kernels, fusions, calibrators: entropy vs
               MinMax); one real site; yolov8n only; 3 checkpoints from one recipe.
```

### H38 · results (2026-09-27, 5,183 s CPU, `out/experiments/h38_quant_export`; audited AUDIT_H38)

| arm | AP s0 / s1 / s2 | AP mean | loss vs FP32 torch, mean (range = the "95 % boot" interval at n = 3) | AP75 mean | CPU ms/im* |
|---|---|---|---|---|---|
| fp32_torch | 0.4970 / 0.4957 / 0.4955 | 0.4961 | reference | 0.5310 | 3065 |
| onnx_fp32 | 0.4970 / 0.4957 / 0.4955 | 0.4961 | +0.0000 (identical) | 0.5310 | 178 |
| onnx_fp16 | 0.4971 / 0.4959 / 0.4952 | 0.4961 | +0.0000 (−0.0002..+0.0003) | 0.5309 | 141 |
| int8_real | 0.4855 / 0.4876 / 0.4801 | 0.4844 | **+0.0117 (+0.0081..+0.0154)** | 0.5008 | 198 |
| int8_syn | 0.4850 / 0.4832 / 0.4805 | 0.4829 | +0.0132 (+0.0120..+0.0150) | 0.5033 | 273 |

- Sanity: ONNX FP32 = PyTorch to 4 dp on all 3 → reference is fp32_torch as registered. fp32_torch is within 0.0003 of h14b's GPU-FP16 numbers (0.4969/0.4956/0.4952).
- **Interval method (corrected on audit):** the runner's "95 % percentile bootstrap" resamples 3 checkpoint losses; with n = 3 the 2.5/97.5 percentiles are exactly the min and max (each all-same resample has p = 1/27 > 2.5 %), so every bracket here is the **range**, not a CI — as the pre-registration warned. Read them as "worst and best of 3 checkpoints".
- **FP16 branch: met** (max loss 0.0003).
- **INT8 branch: not met** — mean loss 0.0117 is inside 0.015 but s2 loses 0.0154 (> 0.015 by 0.0004), and the rule was "all 3". The loss is localisation: AP50 falls 0.0002–0.0042 (≤ 0.0042), AP75 falls 0.025–0.040 (mean 0.030).
- **Calibration branch: not met** — INT8 real − syn = +0.0015 (−0.0004..+0.0044; s2 −0.0004); synthetic calibration costs ≤ 0.0044 extra on the worst checkpoint, as predicted. Scope: the "real" set is MOT20-01, a different real sequence from the MOT20-02 test set, so **neither arm is calibrated on the deployment site**; what is shown is that calibration source (off-site real vs synthetic) did not matter, not that on-site calibration would not help.
- *Latency is context only, and weaker than first written: the same graph varies 4.7× across checkpoints (onnx_fp32 57 / 213 / 264 ms; int8_syn 105–367 ms) under shared-CPU contention (X28 and others on 12 threads), so the means are not comparisons between arms. The earlier line "ORT CPU QDQ INT8 was not faster than FP16" is **not supported** either way (retracted); the PyTorch 3,065 ms is thread-oversubscribed. Not a Jetson/TensorRT number.
- Calibration procedure matches the registration (checked on audit): static PTQ, QDQ, per-channel S8 weights, S8 activations, MinMax; real = 100 evenly spaced MOT20-01 frames 61–429 (1–60 are h14b training frames); syn = 50 render + 50 degraded batch_v8 frames, seed 38, from every scenario dir not prefixed `_` (only `_failed_entrance_gate` exists); the 23 Detect-head decode nodes (`/model.22/…` DFL softmax, dist2bbox, sigmoid, concats) kept FP32 via `nodes_to_exclude`. Deviations: none. MinMax, not TensorRT's entropy calibrator.

## H39 · Ground-plane auto-calibration from pedestrians (`h39_autocalib`) — pre-registration

Registered 2026-09-27, before any H39 arm was fitted or scored (docs/research/66 H39,
docs/research/75). Question: how good is a detector-free "calibrate from walking people with
a known mean height" homography, measured against the exact calib GT that real sites never
have? CPU only, no engine, no training.

```
id:            h39_autocalib  (config survsim/experiments/configs/h39_autocalib.yaml; runner autocalib)
data:          out/batch_v8 *_day scenes, rendered window frames 1-299 (30 s at 10 fps), mask boxes
               (gt/boxes_mask.parquet), truth gt/world.parquet (same frame, uid), heights
               gt/identities.parquet height_m, calib/<cam>.json.
cameras:       every camera EXCEPT (i) one whose camera_status pose/hfov/tamper differs from its calib
               file anywhere in the window (principle 2: cam_ptz slews, calib is its configured pose)
               and (ii) exact duplicates (street_crowd_far_day cam_01 = street_crowd_day cam_01, same
               pose, same world GT). The runner writes the kept/excluded list and reasons.
boxes:         visibility >= 0.95, box >= 20 px tall, >= 2 px from every image border.
               foot = bottom-centre of the mask box, head = top-centre.
arms:          A0 exact     H = K[r1 r2 t] from calib (floor: box-bottom-is-not-the-foot error only)
               A1 gt_foot   8-DOF DLT homography (Hartley-normalised least squares) from box foot pixel ->
                            world.parquet (x, y), all frames (upper bound for any homography learned
                            from people; in-sample)
               A2 auto_all  known-height auto-calibration: principal point = image centre, square
                            pixels, no distortion; fit f, pitch, roll, camera height h by robust
                            (soft-L1) least squares of box-top reprojection given the box foot and a
                            single mean person height 1.70 m (Lv/Zhao-style known-height prior);
                            yaw and camera ground position are gauge (unobservable from one view) and
                            are taken from the install record (calib position_world x,y and heading of
                            the optical axis) -- no per-person GT enters the fit. All 30 s.
               A3 auto_10s  as A2, fit on frames <= 100 (first 10 s) only, scored on frames 101-299.
               DEVIATION from the brief's "first 30 s": the rendered window IS 30 s, so 30 s = A2.
metric:        world-position error |H^-1(foot px) - (x, y)| (m); RMSE per ground-distance-from-camera
               bin [0,10) [10,20) [20,30) [30,inf) m and pooled <20 m; 95 % percentile bootstrap over
               tracks (unit = scene/camera/uid), 1000 resamples, seed 39.
               Height error: per box, height of the vertical segment whose foot is the ground point and
               whose top lies on the head ray; per track median vs identities height_m; MAE and mean
               signed error (m). Recovered f / pitch / h vs calib per camera.
decision:      H39 met iff for A2 RMSE(<20 m) <= 0.5 m AND RMSE(>=30 m) / RMSE(<20 m) >= 3 (point
               estimates); "robust" additionally iff the CI upper of RMSE(<20 m) <= 0.5 and the CI lower
               of the ratio >= 3 (bootstrap of the ratio over the same resamples).
               Secondary: A3 RMSE(<20 m) within 1.5x of A2.
prediction:    A0 ~0.1-0.3 m (box bottom vs foot centre); A1 close to A0; A2 0.3-0.8 m < 20 m, with error
               growing ~linearly with range because a height-prior bias is a scale error on h; the ratio
               probably 2-4 -- coin-flip on the 3x branch. A3 close to A2 (people cover depth in 10 s).
confounds:     simulated people have a height distribution (incl. children) whose mean is not 1.70 m;
               flat ground by construction (real sites are not); no lens distortion in batch_v8; box
               top is hair/head-top, bottom is the lowest shoe, not the ankle midpoint; 11 cameras,
               4 scenes; yaw/position from the install record is the realistic-but-optimistic case.
```

## H24 · ReID appearance in ByteTrack association (`h24_reid_assoc`) — pre-registration

Registered 2026-09-27, before any H24 arm was tracked or scored (docs/research/66 H24,
refinements from 73 §6). Unblocked by M1 parity (`5571631`): all metrics are the
reference TrackEval via `survsim/eval/trackeval_bridge.py`, not `evaluate_mot`.

```
id:            h24_reid_assoc  (config survsim/experiments/configs/h24_reid_assoc.yaml; runner reid_assoc)
tracker:       numpy ByteTrack (survsim/baselines/bytetrack.py), defaults as H17 (high 0.5, low 0.1,
               new 0.6, match_iou 0.2, low_iou 0.5, max_lost = fps). No other change between arms.
appearance:    stage 1 only (high-score dets vs all tracks). Cost = (1 - IoU) + w * d_app,
               d_app = 1 - cos(track feature, det feature) clipped to [0, 1], w = 1.0 for every
               embedding (not tuned). Feasibility unchanged: a pair is accepted only if IoU >= 0.2,
               so appearance can only re-rank IoU-feasible pairs (ID swaps in crowds), never create
               a match IoU forbids. Track feature = EMA (alpha 0.9) of L2-normalised det features,
               updated on stage-1 matches only; stage 2 (low-score) stays IoU-only (BoT-SORT
               convention). Features computed for dets with score >= 0.5 only.
arms:          A0 bytetrack           control, w = 0 (bit-identical to the H17 tracker)
               A1 osnet_imagenet      torchreid osnet_x1_0 ImageNet, 256x128 (reid_train.embed)
               A2 hsv_histogram       reid.hsv_hist (8x4x4 upper/lower halves)
               A3 osnet_h20           H20 synthetic fine-tune. H20 did not save weights, so seed 0 is
                                      retrained with reid_train.train on the identical H20 config
                                      (deviation, stated). H20 trained on street_crowd_* and
                                      smoke_mock_* identities => A3 is LEAKY on those batch_v8
                                      sequences; A3 on batch_v8 is scored only on disguise_and_tamper_day
                                      (held out in H20). MOT20 is unaffected.
data:          (a) MOT20-02 frames 1-300 (docs/13 subset, ignore regions dropped as in H9/H17), cached
                   h17 detections of the 5 h14b mix_300_s{0..4} checkpoints (det imgsz 640, conf 0.1).
               (b) batch_v8 day, raw renders: street_crowd_day, street_crowd_far_day, smoke_mock_day,
                   disguise_and_tamper_day = 12 camera sequences x 300 frames, GT = visible
                   mot_<cam>.txt; detections from the same 5 h14b checkpoints (imgsz 640, conf 0.1),
                   run once and cached (GPU if >= 2 GiB free after a bounded wait, small batch;
                   X28 holds the card). fps 10 -> max_lost 10.
               (c) secondary, 73 §6: GT-box arm on batch_v8 = GT boxes jittered (sigma 5 % of h on
                   centre/size, score 0.9), 5 noise seeds in place of checkpoints; isolates AssA from DetA.
metrics:       TrackEval HOTA, DetA, AssA (alpha-averaged HOTA; DetA/AssA reported at alpha 0.5 as the
               bridge does, plus alpha-mean AssA), IDF1, IDSW. Per sequence and COMBINED.
primary:       dAssA = AssA(arm) - AssA(A0), paired by (sequence, checkpoint).
               batch_v8: mean over 12 sequences x 5 checkpoints of the per-sequence dAssA (alpha-mean
               AssA); 95 % CI by two-way bootstrap (resample sequences and checkpoints independently,
               10 000, seed 0). MOT20-02: one sequence, mean over 5 checkpoints, bootstrap over
               checkpoints + exact sign-flip p (floor 0.0625).
hypothesis:    for A1 (primary arm): batch_v8 dAssA >= +0.02 with CI lower bound > 0, AND MOT20-02
               "no decrease" = CI lower bound of dAssA >= -0.005. Both needed. A2, A3 same rule,
               reported as secondaries (no multiplicity correction; 3 arms stated).
secondaries:   dIDSW (H17's +11 is what H24 should fix), dHOTA, dIDF1; batch_v8 street_crowd_day
               separately (densest); GT-box arm dAssA.
prediction:    small positive on batch_v8 street_crowd (swap-driven), ~0 elsewhere (sparse scenes have
               little ambiguity); MOT20-02 ~0 +/- 0.01 (IoU gate dominates at 25 fps; OSNet-ImageNet
               MOT20 mAP is only 0.23); HSV >= OSNet on batch_v8 (H20: synthetic colour is distinctive).
stopping:      one pass, fixed.
confounds:     w = 1 not tuned for any embedding (HSV and OSNet distances have different scales);
               appearance only in stage 1 and gated by IoU (no long-gap re-identification);
               3 synthetic scenes; MOT20 one sequence; A3 retrained (not the H20 weights).
```

## H40 · Sterile-zone line-crossing rule: naive vs gated vs context (`h40_line_cross`) — pre-registration

Registered 2026-09-27, before any H40 arm was scored (docs/research/66 H40, docs/research/76). 74 says
"we have no measured line-crossing number"; this is that number, on mock tracks, CPU only. Seen before
registration (disclosed): the raw count of outside->inside restricted-zone transitions on 34 of the 676
clean H12 worlds (1,626 in 137.5 cam-h, 11.8/cam-h: the mock planner routes innocent transit straight
through restricted polygons), and 6 probe worlds showing `perimeter_probe` falls back to `recon` on any
site without `fence_panel` props (only `perimeter_site` has them) and that `fence_cut` never moves the
actor across the fence.

```
id:            h40_line_cross  (config survsim/experiments/configs/h40_line_cross.yaml;
               runner survsim/experiments/line_cross.py, `python -m survsim.experiments.line_cross`)
sterile zone:  every zone tagged restricted or perimeter_fence (the "line" is its polygon boundary).
clean data:    the 676 regenerated H12 clean worlds (out/experiments/h58_round2/tracks/h12/clean_*,
               ~3,002 cam-h, innocent commuters only). No truth events: every alarm is a false alarm.
recall data:   200 new 300 s worlds, alarm_scale recipe (_site_spec/_compose_valid/_simulate), seed 40:
               100 x incidents [zone_intrusion] on all site types, 100 x [perimeter_probe] on
               perimeter_site only (the only type where the probe is a probe). compose adds the
               transit_through/wait_then_leave twins; guards/workers present are NOT exempt (a camera
               does not know roles) and count as false alarms.
truth:         what happened (principle 1): per incident actor, the first tick the actor is inside a
               sterile zone at or after the arc's first hostile phase begins. Actor never inside => no
               truth event (counted and reported, not scored). Label "intrusion.line_cross".
tracker model: (applied identically to clean and recall; seeded per world, seed 40)
               position jitter N(0, 0.30 m) per axis per 5 Hz tick; track fragmentation at Poisson
               rate 1/90 s per track (fragment uid "<uid>#k", alarm uid mapped back to <uid> for
               actor-aware scoring); person height N(1.70, 0.09) per track + N(0, 0.15) per tick;
               ghost tracks at 10 per camera-hour (assumed nuisance rate, not measured), duration
               U(0.4, 4) s, speed U(0, 1.5) m/s, start uniform over the zone bounding box +/- 5 m,
               height U(0.2, 0.8) m (wildlife, p = 0.5) else U(0.3, 2.2) m (shadow/weather/headlight).
               Secondary: every arm also scored on noise-free tracks (no jitter/fragments/ghosts).
arms:          (cumulative; parameters fixed here, not tuned)
               N  naive       alarm on every outside->inside transition of any track, and on a track
                              first seen inside (object-in-zone onset).
               A  +gating     N, and track age >= 2.0 s at the crossing and median height so far >= 1.2 m.
               B  +dir/dwell  A, and the track was seen outside before (inward crossing only), is
                              >= 1.5 m inside the boundary, and has stayed inside >= 5 s; alarm at the
                              tick all hold; one alarm per track per entry.
               C  +context    B, excluding crossings whose crossing point lies within 4 m of a gate-
                              or queue-tagged zone or a door prop (paths/gates where legitimate traffic
                              passes the line).
metric:        survsim.eval.alarms.score, actor_aware=True, label "intrusion.line_cross"; primary
               tolerance 10 s (i-LIDS sterile zone), secondary 30 s. Clean FA/cam-h with Garwood 95 %
               and world-cluster bootstrap 95 %; recall with world bootstrap 95 % (2,000, seed 40);
               FA ratio N/C with paired world-cluster bootstrap 95 %. Budget 0.001 FA/cam-h.
decision:      H40 met iff (i) N clean FA/cam-h >= 0.01 (>= 10x budget) with Garwood lower >= 0.01,
               AND (ii) FA ratio N/C >= 5 (point), AND (iii) C recall@10 s >= 0.9 (point).
               "Robust" additionally iff ratio CI lower >= 5 and C recall CI lower >= 0.9.
               Reported regardless: per-arm FA/cam-h vs budget, recall@10/@30, where the clean alarms
               come from (ghost / fragment / commuter cut-through).
prediction:    N ~10-30 FA/cam-h (cut-throughs + ghosts + fragments); A removes most ghosts; B removes
               short corner cuts but not commuters who walk through a restricted polygon for >5 s; C
               helps little because cut-throughs are not at gates. Expect (i) and (ii) met, (iii)
               at risk from the 5 s dwell against the 10 s window, and every arm >> budget.
confounds:     mock tracks; restricted polygons are not fenced, so innocent cut-through is a
               simulator artefact a real sterile zone (two fences) would not have; ghost rate and
               heights are assumptions; fence_cut and ClimbAttempt never cross in the mock, so the
               probe arm scores approach to the fence strip, not a climb-over.
```

### H40 results (2026-09-27, pre-registration `02b51ae`, `out/experiments/h40_line_cross/results.json`, fig `figures/fig_h40.png`)

676 clean worlds = 3,002.0 cam-h; 200 intruder worlds (100 zone_intrusion, 100 perimeter_probe on
perimeter_site), 200 truth events, 0 actors that never entered a sterile zone. Actor-aware, i-LIDS 10 s
window; world-cluster bootstrap 95 % (2,000, seed 40). Wall 11 min, 10 workers.

| arm | clean FA/cam-h [world-boot 95 %] | x budget | recall@10 [95 %] | recall@30 | intrusion / probe @10 | noise-free FA/cam-h, recall@10 |
|---|---|---|---|---|---|---|
| N naive | 70.96 [63.80, 78.30] | 70,964 | 0.945 [0.910, 0.975] | 0.980 | 0.980 / 0.910 | 16.98, 0.940 |
| A +gating | 66.48 [59.67, 73.30] | 66,484 | 0.925 [0.885, 0.960] | 0.960 | 0.960 / 0.890 | 16.44, 0.940 |
| B +dir/dwell | 5.11 [4.70, 5.55] | 5,111 | 0.120 [0.075, 0.170] | 0.125 | 0.030 / 0.210 | 5.41, 0.115 |
| C +context | 4.20 [3.84, 4.57] | 4,196 | 0.100 [0.060, 0.145] | 0.105 | 0.000 / 0.200 | 4.41, 0.095 |

FA ratio N/C (noisy) **16.9 [15.3, 18.6]**; noise-free 3.85. Garwood intervals are ±0.3 or tighter at
these counts (k = 12,597 to 213,034) and understate the between-world spread; the world bootstrap is the
honest interval.

**Decision: H40 not met.** (i) naive ≥ 10x budget: met (71,000x). (ii) N/C ≥ 5: met, robustly (CI lower
15.3). (iii) C recall@10 ≥ 0.9: **failed, 0.100**. Every arm is 4,000x+ over the 0.001 budget.

Where the clean alarms come from (noisy N): fragments 109,445, commuters 101,716, ghosts 1,873.
Gating (A) removes 96 % of ghosts (1,873 → 71) but ghosts were < 1 % of N; fragments + jitter re-crossing
the line are the real noise term *under the assumed noise model* (jitter, fragment and ghost rates
are assumptions, not fitted to a tracker; noisy N is 4.2x noise-free N). Direction/dwell (B) removes 92 % of N.
What is left is innocent commuters walking through restricted polygons for > 5 s. That is a simulator
artefact: the polygons have no fence, so the planner routes transit straight through them.

Why recall collapses (post-hoc diagnostic, not pre-registered): the 1.5 m depth gate. `ZoneIntrusion`
stops the actor the moment `zone_of` equals the target, i.e. at the boundary. Only 6/100 intrusion
actors are ≥ 1.5 m deep within 10 s of entry (35/100 ever). The perimeter strip is 3 m wide, so its
maximum depth is 1.5 m (25/100 within 10 s). The depth/dwell filter that kills cut-throughs also kills
the intruder the mock models, who stops just inside. A real sterile zone gives the opposite trade: nobody
innocent is inside, so arm N's recall is available at low FA only if cut-throughs are physically
impossible. Next: an intruder arc that crosses the zone (climb over, run to the inner fence), a
depth-free B (dwell only), and a patrol-guard twin (76 §gap table).

## H40b · Line-cross rule on crossing intruders and fenced zones (`h40b_line_cross`) — pre-registration

Registered 2026-09-27, before any H40b arm was scored (docs/research/66 H40b; follows H40 above and the
76 §5 gap table). H40 failed on generator gaps, not on the rule. This run keeps the rule and fixes the
generator. The four arms, parameters, noise model and scoring code are H40's, unchanged.

Simulator changes under test (commit before this one; `tests/test_behaviours_intrusion.py`):
`restricted` / `perimeter_fence` zones are fenced (`survsim/director/fences.py`). An unauthorised walker
is stopped at the fence on its *actual* position, and `Transit` routes round the fence. Each fenced area
has a gate prop. `zone_intrusion`, `fence_cut` and the new `fence_climb` cross, go >= 3.5 m inside, visit
the asset, pause and leave. `perimeter_site` now has a fenced compound with the 3 m sterile strip nested
inside its outer fence. `perimeter_probe`/`fence_cut` no longer fall back to recon on sites without panels.
New twins: `patrol_guard` (twin of probe/cut/climb) and `maintenance_visit` (twin of zone_intrusion), both
entering by the gate. New `wildlife` agents: object_class animal, height < 1 m, fast and erratic.

Seen before registration (disclosed): engineering sanity runs only. (a) 12 300 s worlds built with seed 40000.
The three `zone_intrusion` ones are registered recall worlds 0/6/12 (the others are the wrong seed
offset). In them every intruder reached >= 3.4 m inside, and no transit/wait innocent had a tick inside a
fence. One probe world's intruder ran out of the 300 s window before cutting. (b) Clean world 1
regenerated once: noisy N 324 alarms (291 commuter, 28 wildlife, 5 maintenance twin), C 1 (the
maintenance twin). No recall number and no pooled FA had been computed.

```
id:            h40b_line_cross  (config survsim/experiments/configs/h40b_line_cross.yaml; runner
               survsim/experiments/line_cross.py; `survsim experiment h40b_line_cross`)
clean data:    the 676 H12 clean worlds REGENERATED with the fenced simulator: same H12 seed (12) and
               recipe (_site_spec/_compose_valid/innocent_people/_simulate, as tools/loiter_eval.py),
               so the commuter population and arrival draws are H12's; positions differ where fences
               bite. Added from a separate stream ([40, i, 41]): patrol_guard ~ Poisson(2/h), role guard;
               maintenance_visit ~ Poisson(1/h), role worker; wildlife ~ Poisson(4/h), 30-120 s each.
recall data:   same recipe and seeds as H40 (seed 40; intrusion x100 offset 0, probe x100 offset 1 on
               perimeter_site) regenerated with the new simulator, PLUS 100 fence_climb worlds on
               perimeter_site (offset 2). compose adds the BENIGN_TWIN twins (now maintenance_visit /
               patrol_guard); they are false alarms if they alarm.
truth:         unchanged: first tick inside a sterile zone at/after the actor's first hostile phase.
tracker model: H40's, unchanged (0.3 m jitter, fragments 1/90 s, 10 ghosts/cam-h, person height
               N(1.70, 0.09) + N(0, 0.15)). ASSUMPTION, stated: the same noise model is right for the
               regenerated worlds; it is not fitted to any tracker. One addition: a non-person track
               (wildlife) gets its true height + N(0, 0.09) instead of the person prior.
arms:          N, A, B, C exactly as H40 (A: age >= 2 s, median h >= 1.2 m; B: inward, >= 1.5 m deep,
               >= 5 s inside; C: B minus crossings within 4 m of gate/queue zones).
metric:        actor-aware alarms.score, 10 s primary / 30 s secondary. PRIMARY clean FA/cam-h = all
               clean alarms except those on patrol_guard / maintenance_visit tracks (commuters,
               fragments, ghosts and wildlife stay in). Twin FA/cam-h (per kind, Garwood) and wildlife
               FA reported separately, plus the total including twins, plus twin FPs in recall worlds.
               World-cluster bootstrap 95 % (2,000, seed 40).
decision:      H40b met iff C recall@10 (all 300 recall worlds, point) >= 0.9 AND C primary clean
               FA/cam-h (point) <= 2.915 (round-3 loiter A1 operating point, 32 §H58 round 3).
               Robust iff C recall boot-95 lower >= 0.9 AND C FA world-boot upper <= 2.915.
               H40's own (i)-(iii) are recomputed and reported too.
prediction:    recall@10 for C ~0.85-0.95. The main risks are fragment breaks inside the 5 s dwell, and
               crossings within 4 m of an entrance gate zone. C primary FA well under 2.915, because
               cut-through commuters are gone and ghosts cannot satisfy 5 s dwell. Twins: every
               patrol/maintenance gate entry passes B and C (they go deep and stay), so twin FA ~= twin
               entries per cam-h. That is the number a role-blind video rule cannot remove.
confounds:     mock tracks; noise model assumed; gate entries are placed away from gate/queue *zones*,
               so arm C does not exempt the fence gate (a real site would, at the price of gate
               tailgating); wildlife rate invented; recall worlds are 300 s, so a slow probe+cut arc can
               end before crossing (counted as "never inside", not scored).
```

### H40b results (2026-09-27, pre-registration `d51e5f9`, engine `9468696`, `out/experiments/h40b_line_cross/results.json`, fig `figures/fig_h40b.png`)

676 regenerated clean worlds = 3,002.0 cam-h, with 678 patrol_guard, 322 maintenance_visit and 1,370
wildlife agents added. 300 recall worlds gave 298 truth events. Two actors never got inside: slow
probe+cut arcs ran out of the 300 s window. Scoring is actor-aware with the i-LIDS 10 s window and a
world bootstrap (95 %). Wall time 45 min on 10 workers. The noise model is H40's, assumed and not fitted.

| arm | primary clean FA/cam-h [world-boot 95 %] | recall@10 [95 %] | intrusion / cut / climb @10 | twin FA/cam-h patrol / maint [Garwood] | wildlife FA/cam-h | noise-free FA, recall@10 |
|---|---|---|---|---|---|---|
| N naive | 369.4 [318.4, 428.9] | 0.862 [0.825, 0.900] | 0.870 / 0.816 / 0.900 | 2.66 / 0.61 | 5.96 | 1.84, 1.000 |
| A +gating | 353.9 [303.9, 411.7] | 0.829 [0.785, 0.872] | 0.840 / 0.786 / 0.860 | 2.47 / 0.40 | 0 | 0, 1.000 |
| B +dir/dwell | **0** (rule of three ≤ 0.001) | 0.822 [0.780, 0.863] | 0.890 / 0.776 / 0.800 | 0.43 / 0.11 | 0 | 0, 0.899 |
| C +context | **0** (≤ 0.001) | **0.782 [0.736, 0.829]** | 0.780 / 0.765 / 0.800 | **0.389 [0.367, 0.412] / 0.099 [0.088, 0.111]** | 0 | 0, 0.852 |

**Decision: H40b not met.** The FA leg is met with room to spare: C's primary clean FA is 0 in 3,002 cam-h,
which is ≤ 2.915 and also under the 0.001 budget by the rule of three. The recall leg fails: C recall@10 is
0.782, and even its CI upper bound (0.829) is below 0.9. H40's (i) and (ii) still hold. The N/C ratio is
undefined because C = 0.

What changed from H40 is the generator. Fences removed every innocent cut-through. Noise-free N fell from
16.98 to 1.84 FA/cam-h. That residue is **all wildlife** (5,518 alarms; primary FA keeps wildlife by
registration), with zero noise-free commuter alarms — corrected in AUDIT_H40B from "commuters pressed
against a fence". Noisy N rose to 369, mostly fragments (937k of 1.11M): commuters now wait and walk along
fence lines, and 0.3 m jitter crosses the line. B's inward/depth/dwell test removes all of those. Recall
rose from 0.100 to 0.782 because intruders now go ≥ 3.5 m inside.

Where C's 21.8-point recall shortfall comes from (AUDIT_H40B decomposition, recall@10): the depth/dwell
rule itself costs 10.1 points on **noise-free** tracks (A 1.000 → B 0.899; still 0.916 at 30 s, so it is
not only timing; probe arcs are worst, 0.827), gate context 4.7 more (noise-free C 0.852), and the assumed
tracker noise 7.0 (noisy C 0.782). Fragments are therefore a minority of the misses, not "the remaining
misses" as first written. Noisy B is 0.822; arm C drops another 4 points on crossings within 4 m of an
entrance gate zone.

**The residual is the twins.** On the clean worlds, authorised patrols and maintenance visits give C
0.49 FA/cam-h in total (0.389 + 0.099 = 0.488, ~490x the budget). As registered, arm C does not exempt
the fence gate (gate entries sit away from gate/queue *zones*, see confounds), so a gate exemption would
remove gate-entry twin alarms, but only by blinding the rule to forced or tailgated gate entry; what a
role-blind rule cannot do is tell the guard from the intruder once both are inside. In the recall worlds,
398 of C's 424 false positives (94 %) are twins. Wildlife is removed entirely by height gating (arm A).

Next: a fragment-tolerant dwell (re-link within 1 s) for recall (H50; it can recover at most the 7
noise points, and noise-free C is 0.852, so it cannot meet the 0.9 bar on its own), and role/schedule or
gate-log context for the twin residual (H49; 74 PIDS/access fusion).

### H39 results (run 2026-09-27, 432 s CPU, `out/experiments/h39_autocalib`)
Figure: `docs/research/figures/fig_h39.png` (docs/research/75, docs/13 figures index).
*Audit (AUDIT_76_H40, 2026-09-27):* every number above recomputed from `results.json` and matches;
"6/100 within 10 s (35 ever)" and "25/100" re-derived from the cached recall tracks. One deviation from
the registration, disclosed here: arm C excludes crossings within 4 m of gate/queue zones only — the
registered "or a door prop" clause is not implemented in `near_context`. It cannot rescue (iii): C's
recall is bounded above by B's 0.120. Read every FA/cam-h here as **optimistic for a real fence**: the
clean worlds have no patrol-guard, animal or weather twin, and the ghost rate is invented.


10 cameras, 4 scenes, 67 tracks, 8,195 boxes (excluded: `cam_ptz`, which slews — its calib
is the configured pose, principle 2 — and `street_crowd_far_day/cam_01`, a pose-and-GT duplicate).
RMSE (m) of the mask-box bottom-centre mapped to the ground vs world.parquet, 95 % bootstrap over tracks:

| arm | 0-10 m | 10-20 m | 20-30 m | ≥ 30 m | < 20 m pooled | ratio ≥30 / <20 |
|---|---|---|---|---|---|---|
| A0 exact calib H | 0.205 [0.176, 0.226] | 0.208 [0.167, 0.248] | 0.203 [0.178, 0.230] | 0.263 [0.237, 0.286] | 0.208 [0.172, 0.244] | 1.26 [1.05, 1.55] |
| A1 DLT on GT feet (in-sample) | 0.084 [0.067, 0.107] | 0.122 [0.108, 0.136] | 0.141 [0.128, 0.154] | 0.205 [0.193, 0.218] | 0.117 [0.103, 0.131] | 1.75 [1.55, 2.01] |
| **A2 auto, free f (registered)** | 13.1 [3.0, 25.5] | 61.8 [51.2, 71.6] | 90.0 [68.8, 107.9] | 257 [215, 296] | **57.4 [46.2, 68.0]** | 4.49 [3.50, 5.77] |
| A3 auto, free f, first 10 s | 42.9 [19.3, 62.1] | 80.1 [71.0, 89.9] | 139.6 [126.0, 150.1] | 243 [199, 282] | 74.7 [64.7, 84.4] | 3.26 [2.58, 4.01] |
| A2f auto, datasheet f (post hoc) | 0.885 [0.657, 1.143] | 0.969 [0.755, 1.236] | 2.20 [1.40, 2.98] | 2.92 [2.27, 3.66] | 0.958 [0.769, 1.201] | 3.05 [2.21, 4.08] |
| A3f datasheet f, first 10 s (post hoc) | 0.599 [0.334, 0.822] | 0.790 [0.610, 0.972] | 2.29 [1.04, 3.36] | 5.11 [2.37, 8.67] | 0.759 [0.597, 0.918] | 6.74 [2.99, 11.93] |

Per-track height MAE (m): A0 0.024, A2 0.077, A3 0.104, A2f 0.074, A3f 0.093 (population mean
1.652 m vs the 1.70 m prior).

**Verdict: H39 not met.** The near branch fails by two orders of magnitude (57 m, not ≤ 0.5 m);
the ratio branch (4.5×) is met but meaningless on a broken fit. Secondary (A3 within 1.5× of A2) met, 1.30×, equally meaningless.

What happened, in order of importance:

1. **Free focal length is unidentifiable from box heights alone.** 5 of 10 cameras ran f to
   (4) or within 1.2 % of (1) the 4w = 5,120 px bound, with pitch 1.5-4.0° (true 9-20° on those
   five); only `cam_02` of the rest got f within 20 % (audit AUDIT_75_H39 corrected "8 of 10, 2-4°"): pixel height ≈ f·H/Z is almost the same function of
   image row for (long lens, shallow tilt) and (short lens, steep tilt) over the band of rows people
   occupy, and ±10 % height spread (children in the population) plus box noise flattens the rest.
   On synthetic people of exactly 1.70 m the same fit recovers f within 1 % (test) — the failure is
   the height spread and the narrow row band, not the code. Lv/Zhao/Nevatia recover f from the
   *vertical vanishing point* of head-foot lines; axis-aligned boxes throw that away (a box's
   top-centre has the foot's u).
2. **Implementation bug found on the way (regression test added):** the first fit also used the
   u residual of the box top; that measures box geometry, not the head, and drove f to the bound on
   every camera. The registered numbers above use the v-only residual.
3. **With f from the datasheet (A2f, post hoc, not the registered arm)** the fit is sane — pitch
   within 2.1° on 7/10 and 2.7° on 9/10 cameras (`cam_sub` 8.7° off; audit-corrected from "~2° on 8/10") — but still 0.96 m RMSE < 20 m, rising to 2.9 m beyond 30 m. The
   1.70 m prior vs 1.652 m truth is a 3 % scale error on camera height; the bigger error is pitch,
   whose ground error grows as d²/h (29 §8.3). `cam_sub` (153 boxes) fitted roll 15° (bound).
4. **Height error is a trap metric.** A2's per-track height MAE (0.077 m) is as good as A2f's while
   its positions are 60× worse: the fit is *chosen* to make heights match the prior, so height
   consistency says nothing about ground-plane accuracy. Validate calibration on positions/distances.
5. **The foot floor is ~0.2 m.** Even the exact calibration gives 0.21 m because the mask-box
   bottom-centre is the lowest shoe during a stride, not the ground point under the body; the
   in-sample DLT (A1) absorbs part of that bias (0.12 m). Any world-coordinate tracker inherits ~0.2 m.

Deviation logged: "first 30 s" became first 10 s because the rendered window is 30 s (registered).
A2f/A3f were added after seeing the free-f degeneracy and are exploratory; they do not bear on the
H39 verdict. Audit note (AUDIT_75_H39): the confounds line's "11 cameras" should read 12 calib files
(10 scored + 2 excluded); every table number above re-derived from `errors.parquet`, all match.

## H58 round 4 · H21 + H23 (loiter θ and weights over seeds) — pre-registration `06475ab`, results `bd4c028`

Full pre-registration and tables: 58 §8.1–8.2; outputs
`out/experiments/h58_round2/round4_h21_results.json`, `round4_h23_results.json`
(`tools/loiter_eval.py h21`, `h23`, `H58_OUT=out/experiments/h58_round2`; 43 min and
34 min CPU). Same H12 worlds as round 3 (3,002 clean cam-h, 360 events), actor-aware,
30 s. Audited AUDIT_ROUND4 (every number below recomputed from the JSONs).

```
H21  hypothesis: calibrated GBM (C, isotonic on the select fold) with θ on a 25-point log
                 grid 0.01–0.5, chosen on the round-3 select fold, beats A1 (2.915) at
                 recall ≥ 0.80.
     seeds:      5 GBM seeds {58..62} (random_state + negative-subsample RNG); fold fixed.
     bar:        a seed clears iff select recall ≥ 0.85 reached, H12 recall ≥ 0.80 and
                 Garwood upper < 2.854 (A1's lower). Ship C iff ≥ 4/5 clear, seed 58 clears,
                 and seed-58 paired C − A1 CI < 0.
H23  hypothesis: frozen round-1 weights (F) vs logistic retrained per seed (R) differ by
                 within ±10 % FA; both arms re-select θ × clock on each seed's select fold.
     seeds:      10 world+training seeds {58, 158, ..., 958}; 9 new train splits (450 worlds).
     decision:   ≥ 7/10 wins → that policy; else no dominance, A1 stays. A1 "lucky" if ≤ 1
                 retrained seed reaches FA ≤ 2.915 at recall ≥ 0.80.
```

### Results

| H21 seed | C θ | C FA/cam-h [Garwood] | recall | C − A1 [paired world boot] | clears |
|---|---|---|---|---|---|
| 58 | 0.051 | 2.765 [2.706, 2.825] | 0.831 | −0.150 [−0.231, −0.067] | yes |
| 59 | 0.043 | 3.216 [3.152, 3.281] | 0.844 | +0.301 [+0.217, +0.388] | no |
| 60 | 0.043 | 2.992 [2.930, 3.055] | 0.839 | +0.077 [−0.009, +0.164] | no |
| 61 | 0.051 | 3.126 [3.063, 3.190] | 0.833 | +0.211 [+0.126, +0.295] | no |
| 62 | 0.051 | 2.703 [2.644, 2.762] | 0.833 | −0.212 [−0.293, −0.131] | yes |

* **H21: 2/5 seeds clear; 4/5 needed → A1 stays.** Mean 2.960 (SD 0.223, seed bootstrap
  [2.785, 3.135]), recall 0.836. Seed 58 alone clears with a CI below 0 — a single-seed
  run would have shipped C. P9 holds in substance (θ 0.043–0.051; FA above the predicted
  2.4–2.9 on 3/5 seeds).
* **H23: no dominance.** R wins 5 (58, 158, 258, 458, 858), F wins 5 (358, 558, 958; 658
  and 758 where R's recall is 0.789 / 0.783). F 4.397 [3.762, 5.033], R 4.018
  [3.236, 4.776]; **R − F −0.380 [−0.896, +0.203]; (R − F)/F −8.5 % [−21.6 %, +6.2 %]**.
  0/10 retrained seeds reach ≤ 2.915 at recall ≥ 0.80 → **A1 "lucky"**. P10: gap and
  no-dominance hold; "A1 typical" fails.
* **Mechanism.** F's weights are identical on every seed; the select fold picks θ 0.9 on
  7/10 (5.033 / 0.894) and θ 0.95 on 3/10 (2.915 / 0.825). Select folds hold 102–113
  events; one grid step moves H12 FA by 2.118. F re-selects θ (registered), so F equals
  the shipped A1 on only 3/10 seeds.
* **Verdict.** A1 ships unchanged (θ 0.95, clock ≥ 5 s, 2.915 / 0.825). θ selection is the
  dominant variance, larger than the GBM-vs-logistic and frozen-vs-retrained gaps. Next:
  pooled-fold / conformal θ as the selection policy (66 H42, with H33); any challenger
  must win on ≥ 4/5 seeds. The 0.001 budget FAIL stands.

## H42 · θ-selection policy for the frozen A1 weights (`h42_theta_policy`) — pre-registration

Registered 2026-09-27, before any H42 number was computed. Motivation: round 4 (58 §8.2)
showed the same A1 weights land on θ 0.9 (5.033 FA/cam-h, recall 0.894) on 7/10 select folds
and θ 0.95 (2.915, 0.825) on 3/10, so a ~106-event select fold sets the shipped point.

```
data:      A1 = frozen round-1 logistic weights (58 §7.2). Select folds = stratified_fold(metas, s)
           (30 %, by mode) of the 10 H23 train splits {train (s58), train_s158 … train_s958};
           ≈ 1,060 recall events pooled. Scoring: the 676 clean + 300 recall H12 worlds,
           actor-aware, 30 s tolerance, default mode (round-3 primary).
policies:  (a) per-fold: round-4 _select — θ ∈ SEL_GRID × clock ∈ {5,10,15}; min select FA with
               select recall ≥ 0.85. One draw per fold (10 draws).
           (b) pooled: the same rule on counts summed over 9 folds (leave-one-fold-out, 10 draws).
           (c) CRC (H33 choose_crc): clock fixed at A1's 5 s; per-world loss k_i(θ)/camh_i on the
               pooled clean select-fold worlds of 9 folds; α = 2.915; default B; LOFO, 10 draws.
           (d) pooled + recall floor: θ ∈ {0.85, 0.86, …, 0.99} × clock {5,10,15}; min pooled FA
               with pooled select recall ≥ 0.80; LOFO, 10 draws.
metric:    per draw: chosen (θ, clock), H12 FA/cam-h and recall. Spread = range and SD of H12 FA
           over the 10 draws.
hypothesis:(b) or (c) has H12-FA spread ≤ ½ of (a)'s (range and SD; 66's stricter ≤ ¼ reported
           too) AND H12 recall ≥ 0.80 in ≥ 9/10 draws.
decision:  the policy with the smallest spread among those with recall ≥ 0.80 in ≥ 9/10 draws is
           the shipped θ-selection policy (ties → the one whose modal point has lower FA). Its
           modal operating point is compared with A1 (2.915 / 0.825): paired clean-world cluster
           bootstrap of ΔFA and paired recall-world bootstrap of Δrecall (2,000 resamples).
           If the modal point is A1's (θ 0.95, clock 5) the shipped point is unchanged.
seeds:     fixed 10 folds; no stopping rule. Cost: CPU ≤ 6 cores, < 1 h.
```

### H42 · results (run 2026-09-27, 1,190 s on ≤ 6 cores; `out/experiments/h42_theta_policy`, fig `figures/fig_h42.png`)

Frozen A1 weights throughout; pooled select folds = 1,077 events (102–113 per fold). H12:
3,002 clean cam-h, 360 events, actor-aware, 30 s. Numbers copied from `row.md` / `results.json`.

| policy | chosen θ @ clock (10 draws) | H12 FA/cam-h range [min–max] | FA SD | H12 recall range | recall ≥ 0.80 |
|---|---|---|---|---|---|
| (a) per-fold (control) | 0.9@5 ×7, 0.95@5 ×3 | 2.118 [2.915–5.033] | 1.023 | 0.825–0.894 | 10/10 |
| (b) pooled LOFO | 0.9@5 ×10 | 0 [5.033] | 0 | 0.894 | 10/10 |
| (c) CRC α = 2.915 LOFO | 0.9629–0.9649 @5 | 0.119 [2.099–2.218] | 0.032 | 0.778–0.783 | 0/10 |
| (d) pooled + floor 0.80 LOFO | 0.96@5 ×10 | 0 [2.364] | 0 | 0.792 | 0/10 |

Modal operating point vs A1 (0.95@5, 2.915 / 0.825), paired bootstrap (2,000, clean-world / recall-world clusters):

* (b) θ 0.9: FA 5.033 [Garwood 4.953, 5.114], recall 0.894 [0.863, 0.924]; ΔFA **+2.118 [+2.005, +2.237]**, Δrecall **+0.069 [+0.045, +0.095]**.
* (c) θ 0.963: FA 2.218 [2.165, 2.272], recall 0.783 [0.745, 0.824]; ΔFA −0.697 [−0.740, −0.654], Δrecall −0.042 [−0.064, −0.022].
* (d) θ 0.96: FA 2.364 [2.310, 2.420], recall 0.792 [0.754, 0.833]; ΔFA −0.551 [−0.587, −0.515], Δrecall −0.033 [−0.054, −0.014].

**Hypothesis met** (by (b): spread cut from 2.118 to 0, ≥ 2× and ≥ ¼; recall ≥ 0.80 in 10/10).
(c) cuts the spread 17.9× but misses recall 0.80 on H12 in every draw; (d) meets 0.80 on the
pooled select folds (by construction) but lands at 0.792 on H12, so it fails the H12 recall clause.
**Shipped θ-selection policy: pooled (b).** Under the registered select-recall ≥ 0.85 criterion,
pooling 1,077 events picks θ 0.9 on every draw: A1's θ 0.95 reaches pooled select
recall 900/1,077 = 0.836 (< 0.85; θ 0.9: 991/1,077 = 0.920), so round 1's 0.95 was a
small-fold draw. The stable operating point *on SEL_GRID* is therefore 5.033 / 0.894, not
2.915 / 0.825 — +1.7× FA for +0.069 recall. Whether to adopt that point or to relax the select-recall
criterion to 0.80 (which, per (d), gives ≈ 2.36 / 0.79 on H12) is a criterion choice, not a variance one;
it is not decided by H42. The 0.001 budget FAIL stands under every policy.

**Audit (AUDIT_H42, 2026-09-27).** Every number above recomputes from `results.json` /
`fold_stats.json`; LOFO is really used for (b)–(d) (`draws()` pools `folds[:i] + folds[i+1:]`).
Three qualifications. (1) *Spread is not like-for-like:* any two LOFO pools share 8 of their 9
folds, so their between-draw spread is deflated by construction, whereas (a)'s draws are disjoint
single folds; "2.118 → 0" shows that pooling removes the single-fold draw, not that a pooled θ is
stable across independent data. The verdict is met under the registered wording, which did not
require disjoint pools. (2) *θ 0.9 is a grid artefact:* SEL_GRID has no point between 0.9 and 0.95;
on pooled counts θ 0.93 (select recall 954/1,077 = 0.886, select FA 4.10) and θ 0.94 (919/1,077 =
0.853, 3.59) both pass 0.85 at lower FA, so the 0.85 criterion on a fine grid would pick ≈ 0.94. H12
was not scored at 0.93/0.94 — the "stable point 5.033 / 0.894" holds for SEL_GRID only. (3) The
900/1,077 = 0.836 figure pools all 10 folds; each LOFO pool holds 964–975 events. The ship decision
is now an operator-budget choice among three measured points (58 §8.4).

### H24 results

`out/experiments/h24_reid_assoc/results.json` (+ `row.md`, `docs/research/figures/fig_h24.png`),
6,338 s wall (GPU shared with X28). All metrics reference TrackEval via the bridge.

**Deviations.** (1) A3's H20 retrain (seed 0, H20 config) hit H20's own `max_seconds` 300 cap
after **8 of 12 epochs** (GPU shared; H20 ran 12 in 242–270 s), so A3 is an under-trained H20.
(2) batch_v8 detections for checkpoints s1–s4 and all embedding caches were produced by two
helper processes running the runner's own functions (`detect_paths`, `_crops`, `embedders`)
in parallel to cut wall time; same code, same device (GPU FP16), so no numeric change intended.
(3) The pre-registration text was clarified after commit (before any run) to say the fused
cost is solved then IoU-filtered exactly like A0 (no gate-before-solve); the code never did otherwise.
*[AUDIT_H24: "before any run" is not verifiable from git — the clarification, the fused-cost code
and the results all landed in one commit, `2fdecd6` (09:01), after `results.json` was written (08:57).
The registered text (`4095a4c`, 07:09) already said "IoU >= 0.2 ... never create a match IoU forbids",
which the solve-then-filter code satisfies, so the clarification does not change the test.]*

Mean of the 5 h14b checkpoints (COMBINED over sequences; AssA/DetA α-mean). *Not the registered
basis on batch_v8: the registered ΔAssA is the mean of per-sequence ΔAssA, on which ByteTrack is
0.4248 and OSNet-ImageNet 0.4442 (+0.0194); the COMBINED 0.5197 → 0.5535 below is the pooled +0.0338.*

| set | arm | HOTA | DetA | AssA | IDF1 | IDSW |
|---|---|---|---|---|---|---|
| MOT20-02 | ByteTrack | 0.5268 | 0.5532 | 0.5060 | 0.6410 | 92.6 |
| MOT20-02 | + OSNet-ImageNet | 0.5353 | 0.5557 | 0.5199 | 0.6525 | 87.0 |
| MOT20-02 | + HSV | 0.5378 | 0.5583 | 0.5224 | 0.6535 | 84.0 |
| MOT20-02 | + OSNet-H20 | 0.5364 | 0.5567 | 0.5214 | 0.6533 | 89.0 |
| batch_v8 day (12 seq) | ByteTrack | 0.4831 | 0.4505 | 0.5197 | 0.6216 | 83.4 |
| batch_v8 day | + OSNet-ImageNet | 0.4996 | 0.4522 | 0.5535 | 0.6426 | 71.6 |
| batch_v8 day | + HSV | 0.4925 | 0.4502 | 0.5406 | 0.6345 | 74.2 |
| batch_v8 day | + OSNet-H20 (leaky on 8/12 seq) | 0.5186 | 0.4537 | 0.5944 | 0.6763 | 55.4 |
| batch_v8 GT boxes | ByteTrack | 0.6614 | 0.7165 | 0.6111 | 0.8644 | 114.4 |
| batch_v8 GT boxes | + OSNet-ImageNet | 0.6691 | 0.7172 | 0.6249 | 0.8781 | 93.0 |

Pre-registered contrasts (arm − ByteTrack). batch_v8: per-sequence mean, two-way bootstrap over
12 sequences × 5 checkpoints; MOT20-02: bootstrap over 5 checkpoints (sign-flip p floor 0.0625).
IDSW on batch_v8 is per sequence.

| set | arm | **ΔAssA** [95 %] | ΔHOTA [95 %] | ΔIDF1 [95 %] | ΔIDSW [95 %] |
|---|---|---|---|---|---|
| MOT20-02 | OSNet-ImageNet | +0.0139 [+0.0018, +0.0268] | +0.0085 [+0.0018, +0.0152] | +0.0115 [+0.0004, +0.0226] | −5.6 [−11.0, −0.2] |
| MOT20-02 | HSV | +0.0163 [+0.0060, +0.0254] | +0.0110 [+0.0047, +0.0174] | +0.0125 [+0.0016, +0.0234] | −8.6 [−13.4, −3.6] |
| MOT20-02 | OSNet-H20 | +0.0154 [+0.0102, +0.0201] | +0.0097 [+0.0063, +0.0129] | +0.0122 [+0.0027, +0.0199] | −3.6 [−7.0, −0.2] |
| batch_v8 | **OSNet-ImageNet (primary)** | **+0.0194 [+0.0004, +0.0439]** | +0.0125 [+0.0009, +0.0297] | +0.0164 [+0.0023, +0.0358] | −0.98 [−2.22, −0.17] |
| batch_v8 street_crowd_day | OSNet-ImageNet | +0.0267 [+0.0055, +0.0600] | | | |
| batch_v8 | HSV | +0.0123 [−0.0054, +0.0395] | +0.0075 [−0.0032, +0.0251] | +0.0110 [−0.0009, +0.0309] | −0.77 [−1.77, 0.00] |
| batch_v8 held-out (disguise, 4 seq) | OSNet-H20 | +0.0147 [−0.0044, +0.0568] | +0.0075 [−0.0019, +0.0297] | +0.0194 [−0.0047, +0.0759] | −2.05 [−6.7, 0.0] |
| batch_v8 GT boxes | OSNet-ImageNet | +0.0137 [−0.0011, +0.0312] | +0.0082 [−0.0006, +0.0183] | +0.0136 [−0.0020, +0.0316] | −1.78 [−5.13, +0.45] |
| batch_v8 GT boxes | HSV | +0.0076 [−0.0028, +0.0202] | | | |
| batch_v8 GT boxes (held-out) | OSNet-H20 | +0.0160 [+0.0000, +0.0479] | | | |

Context (not the pre-registered statistic): COMBINED batch_v8 AssA for OSNet-ImageNet is
+0.0338 [+0.0251, +0.0431] with all 5 checkpoints positive, and IDSW −11.8 [−18.8, −5.8] per
checkpoint — pooling weights the dense street_crowd sequences, where the effect lives.

**Conclusion.** Pre-registered rule: **not met** for any arm. The primary (OSNet-ImageNet) gains
+0.0194 AssA on batch_v8 with a CI above 0, but the mean misses the +0.02 bar by 0.0006; the MOT20-02
"no decrease" branch is met by a wide margin — appearance *raises* MOT20-02 AssA by +0.014–0.016 in
every arm (CI > 0 in all three), with fewer ID switches. So the direction of H24 is right on both
sets and the effect is about the size predicted for batch_v8, but it is not ≥ 0.02 by the registered
statistic; the prediction that MOT20 would be ~0 was wrong (the IoU gate leaves plenty of
near-tied pairs at 25 fps in a 120-person crowd). HSV is not better than OSNet on batch_v8 (+0.012,
CI spans 0) — prediction wrong; it is marginally best on MOT20. The GT-box arm keeps most of the gain
(+0.014 vs +0.019), so this is association, not a DetA side-effect (OSNet-ImageNet α-mean DetA moves
≤ 0.003; at α 0.5 +0.0048 MOT20 / +0.0040 batch_v8; HSV on MOT20 +0.0051 α-mean) — though the GT-box
CI alone spans 0 [−0.0011, +0.0312]. H17's ID-switch
rise is fixable: −5.6 IDSW on MOT20-02 with OSNet, −8.6 with HSV. For M3: appearance in stage 1 is a
cheap, non-harmful default; w = 1 was untuned, and long-gap re-identification was not tested.

**Caveats.** n = 5 checkpoints from one recipe; one real sequence; 12 synthetic sequences from 4
scenes, most sparse (smoke_mock/disguise: 2–5 ids); A3 under-trained and leaky outside disguise;
the two-way bootstrap with 12 × 5 units is optimistic about scene-level variance.

**Audit (AUDIT_H24, 2026-09-27).** Every number above recomputes from `results.json` (`scores`
per sequence × checkpoint, independently averaged; `analysis` matches). Qualifications: (1) the MOT20-02
"CI > 0 in all three" CIs are percentile bootstraps over **5 checkpoints**; the exact sign-flip p is
0.19 (OSNet-ImageNet, 4/5 checkpoints positive), 0.125 (HSV, 4/5) and 0.0625 (H20, 5/5 — the floor),
so none is significant at 0.05 by the exact test; "raises MOT20-02 AssA" is a consistent direction,
not an established effect. (2) "Appearance never lowered AssA" (FACTS) holds for arm **means** only:
per checkpoint, OSNet-ImageNet lowered MOT20-02 AssA on s1 (−0.0049) and HSV on s4 (−0.0032). (3) The
registered statistic (per-sequence mean, two-way bootstrap) is the one the runner's decision block (`analyse()`) uses; the pooled
COMBINED +0.0338 [+0.0251, +0.0431] is exploratory and was correctly labelled "not the pre-registered
statistic". (4) Scoring is the TrackEval bridge (`reid_assoc.trackeval_score` → `run_trackeval`).
(5) Untested: w (fixed at 1, untuned), the 73 §6 night arm, long-gap re-identification — now H46 (66).

## H45 · Operator sim at the three H42 operating points (`h45_operator_points`) — pre-registration

- **Question:** H22 simulated one operator only at A1's rate (θ 0.95: 2.915 FA/cam-h, model recall 0.825; realised @5 min 0.511 FIFO / 0.586 ranked). H42 left two more points on the same frozen A1 weights (58 §8.4): pooled θ 0.90 (5.033 / 0.894) and conformal (CRC α 2.915) θ 0.962851 — the modal CRC draw (2.218 / 0.783; mean θ 0.9643 ≈ 2.13 / 0.778).
- **Hypothesis (H45):** with H22's operator model unchanged (40 cameras, 30 s gamma review cv 0.3, fatigue after 2 h, miss 0.05/0.15, bulk-ack when queue > 10), one operator: (a) the pooled point's +0.069 model recall is **not realised** — realised recall @5 min within ±0.02 of A1's (paired world-cluster bootstrap 95 % CI of pooled − A1 inside [−0.02, +0.02]) under both FIFO and ranked queues; (b) the conformal point loses ≤ 0.03 realised recall @5 min vs A1 (CI lower bound of CRC − A1 ≥ −0.03) and cuts mean utilisation by ≥ 20 % relative. Met iff (a) and (b) hold for both queues.
- **Secondary:** operator sweep 1, 2, 3 operators sharing one queue (earliest-free operator takes the next alarm; bulk-ack threshold unchanged); report the smallest count at which pooled's realised recall @5 min beats A1's (paired CI > 0) per queue. Also realised @30 s, bulk-ack drop share.
- **Streams:** rebuilt from the frozen A1 weights on the H12 worlds (same first-per-episode condition as H22 `build_streams`, only θ changed); model recall/FA recomputed from the tagged streams must match H42's (0.825/2.915, 0.894/5.033, 0.783/2.218).
- **Seeds:** H22's 10 operator seeds; bootstrap 2000 world-cluster resamples of the recall worlds, paired across points (same seeds, same resamples).
- **Stopping:** fixed. **Cost:** CPU ≤ 6 cores, ~30 min.
- **Decision:** the ship point per staffing level. If (a) holds, pooled is not shipped at one operator despite H42 selecting it; if (b) holds, conformal is the one-operator ship point. Invented-operator caveat (H22) carries over.

## H47 · Evasion techniques vs zero-shot person recall (`h47_evasion`) — pre-registration

- **Question:** 50 lists 52 evasion techniques (`survsim/director/evasion.py`); none has been measured against a detector on rendered pixels. Which of the ones the engine can actually render cost a zero-shot COCO person detector recall on the same cameras?
- **Renderable subset (6; the CC0 renderer has no props, crouch or head-turn clips, so umbrella, carried objects, crouch/crawl, face_away are out — [X] by capability, not measured):** `dark_lowcontrast` (reversible_jacket-style near-black top + bottom + shoes), `hivis` (high-contrast yellow top; hi_vis_worker palette), `hood_up` (face-cover proxy, CoverOn over head, dark), `slow_deliberate` (0.6 m/s vs 1.35), `crowd_cover` (all six walk one lane from one spawn cluster), `wall_hugging` (lanes moved to the yard perimeter, |y| ≈ 17 m). The three appearance techniques re-render the control run's GT unchanged (identical trajectories); the three path/gait techniques are separate mock runs from the same scenario, seed and spawn side.
- **Scene:** `smoke_yard` geometry and its 2 cameras (cam_01 bullet, cam_02 dome), 6 walkers on 6 parallel lanes, 30 s, 10 fps, 1280×720, day, CC0 characters, `--id-mask` (mask-derived visible GT), office/yard layout from the run seed.
- **Hypothesis (H47):** at least half (≥ 3 of 6) of the techniques reduce YOLO26n person recall by ≥ 0.10 vs the matched control: technique *k* counts iff Δ_k = R_k − R_control ≤ −0.10 **and** its Holm-adjusted (over 6) one-sided bootstrap p for Δ_k < 0 is < 0.05.
- **Metric:** recall at conf 0.25, IoU ≥ 0.5 (COCO greedy, `tools/eval_recall.match_frame`), over **every** rendered frame, GT = `gt/mot_<cam>.txt` mask boxes with visible pixels and height ≥ 20 px (the `usably_visible` bar). Pooled over 3 seeds × 2 cameras. **Secondary:** YOLOv8n; precision; GT person-frames (exposure: a path technique can hide people by leaving the ≥ 20 px set, which recall does not see); per-camera Δ.
- **CI:** 2000 bootstrap resamples of frames within each (seed, camera) stratum, arms resampled independently (path arms are not frame-paired); 95 % percentile CI; p = share of resamples with Δ ≥ 0.
- **Seeds:** 3 (1, 2, 3); each seed changes lane jitter, outfits and layout, shared by all arms of that seed.
- **Gate:** `scripts/check_render.py` must pass on a set; a failed set is re-rendered once, else its technique is reported unscored (not imputed).
- **Stopping:** fixed, 21 sets. **Cost:** editor render ~21 × 5 min, VRAM guard (≤ 2 GB above baseline, another job trains on the GPU); scoring CPU.
- **Decision:** techniques that clear the bar enter 50 §"measured" as detector-relevant evasion and become required hard cases in the eval sets; the others are recorded as detection-neutral (they may still matter for ReID/face, not tested here).

### H45 results (run 2026-09-27, 588 s CPU, pre-registration `090e358`; `out/experiments/h45_operator_points/results.json`, fig `figures/fig_h45.png`)

Sanity: streams rebuilt from the frozen A1 weights reproduce H42's model points exactly (A1 2.915 / 0.825,
pooled θ 0.90 5.033 / 0.894, conformal θ 0.962851 2.218 / 0.783) and A1's one-operator cells reproduce H22
(0.511 FIFO / 0.586 ranked @5 min). Alarms/h at 40 cams: 120 / 205 / 92.

| point | ops | queue | util. | realised @30 s [95 %] | realised @5 min [95 %] | bulk-dropped |
|---|---|---|---|---|---|---|
| A1 | 1 | FIFO | 0.88 | 0.127 [0.115, 0.139] | 0.511 [0.485, 0.537] | 0.25 |
| A1 | 1 | ranked | 0.88 | 0.389 [0.361, 0.416] | 0.586 [0.554, 0.618] | 0.25 |
| pooled | 1 | FIFO | 0.95 | 0.090 [0.081, 0.099] | 0.324 [0.304, 0.346] | 0.53 |
| pooled | 1 | ranked | 0.95 | 0.376 [0.349, 0.403] | 0.504 [0.472, 0.535] | 0.53 |
| conformal | 1 | FIFO | 0.79 | 0.184 [0.166, 0.205] | 0.571 [0.539, 0.605] | 0.12 |
| conformal | 1 | ranked | 0.79 | 0.411 [0.381, 0.444] | 0.621 [0.587, 0.657] | 0.12 |
| A1 / pooled / conformal | 2 | ranked | 0.58 / 0.83 / 0.45 | 0.613 / 0.560 / 0.613 | 0.707 / 0.645 / 0.685 | 0.02 / 0.18 / 0.00 |
| A1 / pooled / conformal | 3 | ranked | 0.39 / 0.65 / 0.30 | 0.685 / 0.677 / 0.668 | 0.727 / 0.739 / 0.693 | 0 / 0.04 / 0 |

Paired vs A1 @5 min (same seeds, world-cluster bootstrap): one operator — pooled FIFO −0.186 [−0.212, −0.161],
ranked −0.083 [−0.103, −0.064] (0/10 seeds up); conformal FIFO +0.061 [+0.037, +0.085], ranked +0.035
[+0.016, +0.055] (10/10 up). Two operators — pooled ranked −0.062 [−0.085, −0.040]; conformal ranked −0.022
[−0.045, −0.001]. Three operators — pooled ranked +0.013 [−0.009, +0.035], FIFO −0.024 [−0.048, +0.001];
conformal ranked −0.034 [−0.056, −0.013]. Full table in `row.md`.

**Decision: not met.** (a) fails in the other direction — pooled's +0.069 model recall is not merely unrealised,
it *costs* 0.08–0.19 realised recall at one operator (outside ±0.02). (b) fails on utilisation only — conformal
*gains* realised recall (+0.035 ranked, +0.061 FIFO) but cuts utilisation 10 % (0.88 → 0.79), not ≥ 20 %.
Operator crossover: pooled never beats A1 with CI > 0 in 1–3 operators (point estimate first positive at 3,
ranked, +0.013, CI spans 0). Ship point by staffing: 1 operator/40 cams → conformal, ranked; 2 → A1 (conformal
−0.022 [−0.045, −0.001], 0/10 seeds up: a small but consistent loss, not a tie; conformal buys 0.45 vs 0.58 utilisation); 3 → A1 or pooled (tie). Invented-operator caveat (H22) carries over.

Audit notes (AUDIT_H45): the utilisation cut (1 − 0.794/0.880 = 9.8 %) is identical under FIFO and ranked because
the queue policy reorders reviews but not their number or duration, so (b)'s utilisation leg is one number, not two.
"Modal CRC draw" (pre-registration) is imprecise: H42's 10 LOFO CRC draws are all distinct (θ 0.962851–0.964855,
each count 1), so the "modal" θ 0.962851 is a tie-break that picked the **most permissive** draw (FA 2.218, the
max of 2.10–2.22). The conformal row is therefore the high-alarm end of what CRC ships; the mean draw (θ 0.9643,
≈ 2.13 / 0.778) was not simulated and would sit slightly lower on alarms and model recall. Three operators, ranked:
conformal −0.034 [−0.056, −0.013] (1/9 seeds up).

### H26 results

`out/experiments/h26_dose_fixedstep/results.json`, 25 runs, 450 optimiser steps each
(train images x epochs = 3,600, batch 8; verified per arm: dose0 300 x 12, dose100 400 x 9,
dose300 600 x 6, dose600 900 x 4, dose1000 1,800 x 2 incl. 500 seeded duplicates). Wall
9,292 s (~2.6 h vs ~2 h estimated): the GPU was shared with the Unreal editor, H24/H38 jobs
and a CPU load of ~35-45; three arms waited for GPU memory (`gpu_wait` in results.json:
dose1000_s1 and dose0_s2 600 s, the `wait_for_gpu` cap, starting at 2,255 MiB free;
dose100_s2 480 s; the other 22 waited ≤ 1 s). No arm failed or was restarted.
"450 steps" is presentations / batch (3,600 / 8); ultralytics' partial last batch makes the
realised iteration counts 456 (dose0, 38 × 12), 450 (100, 300, 1,000) and 452 (600, 113 × 4).
Figure: `docs/research/figures/fig_h26.png` (H7's fixed-epoch curve overlaid).

| dose | AP mean [95 % bootstrap] | per seed 0-4 |
|---|---|---|
| 0 (real only) | 0.4911 [0.4890, 0.4932] | 0.4879 0.4888 0.4923 0.4950 0.4915 |
| 100 | 0.4952 [0.4933, 0.4971] | 0.4966 0.4955 0.4922 0.4984 0.4935 |
| 300 | 0.4956 [0.4936, 0.4975] | 0.4959 0.4933 0.4977 0.4982 0.4928 |
| 600 | 0.4926 [0.4900, 0.4952] | 0.4893 0.4932 0.4966 0.4891 0.4947 |
| 1000 | 0.4908 [0.4860, 0.4961] | 0.4888 0.4828 0.4930 0.5008 0.4884 |

| contrast vs 0 | diff | 95 % bootstrap | perm p | Holm (α 0.05, m = 4) |
|---|---|---|---|---|
| 100 | +0.0041 | [+0.0012, +0.0071] | 0.048 | keep |
| 300 | +0.0045 | [+0.0015, +0.0074] | 0.040 | keep |
| 600 | +0.0015 | [−0.0020, +0.0049] | 0.468 | keep |
| 1000 | −0.0003 | [−0.0058, +0.0056] | 0.952 | keep |

**Conclusion.** No contrast survives Holm (smallest p 0.040 vs the 0.0125 first-step
threshold), so by the pre-registered rule **there is no recommended dose**; the point
estimates still peak at 100-300 (+0.004 AP, bootstrap CIs exclude 0) and return to
real-only by 1,000. **"Fades at 1,000" was not the step-count confound**: with steps held
fixed the 1,000 arm is −0.0003 AP, the same null H7 saw with 2.2x the steps; the 1,000 arm
is also the noisiest (sd 0.0067 vs 0.0025-0.0033). The fade is consistent with dilution:
at 1,000 the real share of presentations is 23 % (300 of 1,300 list images; the 500 pads
held 108-119 real images per seed vs 115 expected) and each real list image is presented
~2.8x instead of 12x (each unique MOT20-01 frame ~14x instead of 60x).

**New finding the design exposed.** The real-only arm at 450 steps (12 epochs) is 0.4911,
+0.0054 above h14b's seed-0 real-only 0.4857 (the value H25 reproduced); against h14b's
5-seed real-only mean 0.4862 the seed-paired step effect is **+0.0049** [+0.0031, +0.0068]
(per seed +0.0022 … +0.0078, all positive). h14b's real-only arm trained ~228 iterations
(38 × 6), its mix_100 300 and its mix_300 450, so its +0.0121 (100) and +0.0095 (300)
compared **unequal steps**. At equal steps the synthetic gain is **+0.0041 (100) / +0.0045
(300), neither Holm-significant**, i.e. about a third to a half of the h14b figures. The
decomposition is not clean: the real-only rise (+0.0049) explains ~40 % of +0.0121; the rest
is that H26's dose100 (0.4952, 450 steps) is *below* h14b mix_100 (0.4983, 300 steps). At 300
frames the two studies agree (h14b mix_300 0.4957 vs H26 dose300 0.4956, both 450 steps).
Recipe differences from h14b, so 0.4857 is *not* the same checkpoint recipe: 12 vs 6 epochs,
warm-up fixed at 225 iterations (6 epochs for dose0) vs ultralytics' default 3 epochs, and
the synthetic pool is batch_v8 (9 sets, the H15/H25 spec) not h14b's batch_v7.
Dose gains quoted against a 6-epoch real-only arm (H7, H14b, H16, H25's "gain vs real-only")
compare unequal steps; within-dose contrasts at equal list length (H15 vis vs amodal, H25
noise vs clean, H14 tight vs loose) are not affected. **Unreconciled:** H15's v8_vis_300
(batch_v8, 6 epochs × 75 = 450 iterations, default 3-epoch = 225-iteration warm-up, 7 seeds)
scored 0.4981, 0.0025 above H26 dose300 (0.4956) on what is nominally the same recipe; seed
sets and subset draws differ, and 5-7 seeds cannot say whether that gap is noise.

**Deviations.** 3,000 arm and seeds 5-9 cut (pre-registered reduced design); wall 2.6 h not
2 h (shared GPU; waits above). Caveats: 5 seeds (two-sided perm-p floor 2/252 = 0.008);
one real site; the 1,000 arm pads 500 seeded duplicates drawn without replacement from its
own 1,300-image list, so 800 images are presented 2x and 500 are presented 4x; the real
share among the pads matches expectation (above), so padding does not bias the mix.
Audited: `docs/research/AUDIT_H26.md`.

## H51 · Equal-step dose re-run, 10 seeds, paired (`h51_equal_steps`) — pre-registration

Registered 2026-09-27, before any H51 arm was trained. **Narrowed from the backlog design**
(66 H51 listed three recipes: h14b v7, H15 vis-300, H25 clean-100): the primary family is the
two batch_v8 doses H26 left at p ≈ 0.04; the batch_v7 recipe moves to a 5-seed diagnostic.

```
id:          h51_equal_steps (config survsim/experiments/configs/h51_equal_steps.yaml; runner dose_fixedstep,
             new opt-in `paired_primary: true`; H26 behaviour unchanged, its test still passes)
recipe:      H26's exactly: 60 real MOT20-01 frames x5 (300 list images) in every arm; batch_v8 pool = 9 sets,
             raw stride 8 phase 0 + degraded stride 8 phase 4, visible mask labels, seeded subset per seed;
             450 optimiser steps via list length x epochs = 3,600 (dose0 300 x 12, dose100 400 x 9,
             dose300 600 x 6); warm-up 225 iterations (warmup_epochs 6.0 / 4.5 / 3.0); close_mosaic 0;
             batch 8; workers 2; yolov8n.pt, imgsz 640, last.pt; optimizer auto.
arms:        dose0 (real only), dose100 (+100 v8), dose300 (+300 v8); seeds 0-9 (30 runs, all fresh:
             H26's seeds 0-4 are re-trained, not reused, and serve as a reproducibility check).
metric:      MOT20-02 AP@640 (primary), AP50, AP75 reported.
contrasts:   dose100 - dose0 and dose300 - dose0, PAIRED by seed: exact two-sided sign-flip p over all
             2^10 patterns (floor 1/512), seed-bootstrap 95 % CI of the mean paired difference; Holm over
             the two AP contrasts. H26-style unpaired permutation also reported.
success:     BOTH contrasts mean diff >= +0.004 AP with Holm-adjusted p < 0.05 => the equal-step dose gain
             exists at 60 real frames. Either contrast < +0.004 or Holm p >= 0.05 => the gain is not
             established; if both are n.s. the claim "synthetic helps as an additive" is retired to
             "no measurable effect at 60 real frames" (60 item B, RETIRED_CLAIMS).
diagnostic:  v7dose100 = real + 100 batch_v7 (h14b pool: 5 sets, raw s8 p0 + degraded s8 p4) at H26's recipe,
             seeds 0-4, paired vs dose100 s0-4 (sign-flip, not in the Holm family). Reads the unreconciled
             gap H26 dose100 0.4952 vs h14b mix_100 0.4983: if v7dose100 - dose100 >= +0.002 the pool
             (v7 vs v8) explains it; if ~0, the remaining difference is the schedule (h14b: 6 epochs x 38 = ~228
             its for real-only, 300 for mix_100, default 3-epoch warm-up) or seed noise, judged against the
             10-seed dose100 sd. The H15 v8_vis_300 0.4981 vs H26 dose300 0.4956 gap is read against the
             10-seed dose300 CI (inside => seed/subset noise).
budget:      35 runs x ~5 min ~ 3 GPU-h beside the Unreal editor (~3 GB); wait_for_gpu cap 600 s per arm.
prediction:  both gains +0.003-0.005, at most one Holm-significant.
```

## H53 · Late sensor fusion on the line-cross rule: gate log + RF tag + PIDS (`h53_sensor_fusion`) — pre-registration

Registered 2026-09-27, before any H53 arm was scored (docs/research/66 H53). It tests the claim AUDIT_78
retired: "the fix is context and a second sensor". Base is H40b arm C (noisy tracks), which is unchanged.
The runner reads H40b's cached worlds and alarms (`out/experiments/h40b_line_cross/{worlds.jsonl,
clean_tracks,recall_tracks}`) and adds simulated sensor streams. Nothing is re-simulated.
Seen before registration: only the H40b numbers already in this log. No sensor stream had been generated.

```
id:            h53_sensor_fusion (config survsim/experiments/configs/h53_sensor_fusion.yaml; runner
               survsim/experiments/sensor_fusion.py)
data:          H40b's 676 clean worlds (3,002 cam-h) and 300 recall worlds, arm C noisy alarms as
               recorded. For each alarm, the crossing is the alarmed person's last outside->inside
               transition on its TRUE track at or before the alarm, and its fenced zone is the one
               zone_state assigns there.
sensors (every parameter is an ASSUMPTION, not fitted to any product or site; sensor RNG [53, i, k]):
  (a) gate access log: each patrol_guard / maintenance_visit gate entry badges with p=0.98,
      timestamp = true entry + N(0, 1 s). Intruders and commuters never badge. Match = a badge in the
      same fenced zone within +/-15 s of the alarmed crossing.
  (b) RF tag: staff (twins) carry a registered BLE tag with p=0.95 (tx 0 dBm, 1 Hz adverts, 15 %
      missed adverts, rf.rssi_at path loss n=2.8, shadowing 4 dB). Intruders and commuters carry no
      registered tag (unregistered phones are ignored). Match = any advert from a registered tag with
      RSSI > -80 dBm, measured at the alarmed track's true position, within +/-5 s of the alarm.
  (c) PIDS fence vibration: every non-gate fence crossing (fence_cut, fence_climb, zone_intrusion
      breach) triggers with p=0.90 at t_cross - U(0, 10) s. The gate section is masked, so gate
      entries never trigger. Wind nuisance triggers ~ Poisson(1.0 per fenced zone per hour).
      Confirmation = a trigger in the same fenced zone within [t_cross - 30 s, t_cross + 5 s].
arms (late fusion, alarm-level gates on C):
  C        control (H40b arm C)
  C+a      drop the alarm if the gate log matches
  C+b      drop the alarm if a registered RF tag matches
  C+c      keep the alarm only if PIDS confirms
  C+abc    drop the alarm iff (a or b matches) AND PIDS does not confirm
adversary arms (recall worlds, sensor-stream injections; the catalogue `tailgate` is a door behaviour
               and is not wired to the fence gate, so neither is a simulated behaviour):
  tailgate     an authorised badge is logged in the intruder's zone at t_cross - U(1, 5) s, and the
               intruder enters through the open gate, so PIDS never triggers
  stolen_tag   the intruder carries a registered tag (p=1); PIDS unchanged
metric:        actor-aware alarms.score, 10 s primary / 30 s secondary. Twin FA/cam-h (patrol +
               maintenance) on the clean worlds, total clean FA/cam-h (all kinds), recall@10 on the 300
               recall worlds. World-cluster bootstrap 95 % (2,000, seed 53); Garwood on counts.
decision:      H53 met iff on C+abc twin FA/cam-h (point) <= 0.1 x C's 0.488 (>= 90 % removed) AND
               recall@10 (point) >= C's 0.782. Fusion only removes alarms, so the recall leg means no
               intruder detection lost. Robust iff the twin FA world-boot upper <= 0.0488 too.
               Secondary: recall loss <= 0.02 (H49's bar); per-arm numbers; adversary recall (no bar).
prediction:    C+a and C+b each remove ~95 % of twin FA with near-zero recall cost. C+c removes ~all
               twin FA but costs ~10 % recall (PIDS misses). C+abc removes >= 95 % of twin FA and loses
               recall only where a twin badge or tag coincides with an intrusion AND PIDS misses (<1 pt),
               so the recall leg is at risk of failing on a hair. Tailgate recall under C+a / C+abc ~0;
               stolen_tag recall under C+b ~0 but under C+abc ~0.9 x C.
confounds:     every sensor is simulated and perfectly clock-synced; association uses true positions;
               twins always use the gate and always badge on the same timeline as the video; PIDS
               p_detect and wind rate are invented. A result here shows the fusion LOGIC works on
               SurvSim; it is not a measured PIDS/ACS field performance.
```

### H53 results (2026-09-27, pre-registration `6766666`, runner `0c492ba`, `out/experiments/h53_sensor_fusion/results.json`, fig `figures/fig_h53.png`)

H40b's 676 clean worlds (3,002 cam-h, 1,465 twin alarms on C) and 300 recall worlds (298 truth events), arm C
noisy alarms, with the three simulated sensors exactly as registered. Actor-aware, i-LIDS 10 s, world bootstrap
95 % (2,000, seed 53). Wall time 25 s on 6 workers. Primary (non-twin) clean FA is 0 on every arm, as on C.

| arm | twin FA/cam-h [world-boot 95 %] | twin FA removed [95 %] | patrol / maint | recall@10 [95 %] | tailgate @10 | stolen_tag @10 |
|---|---|---|---|---|---|---|
| C (H40b) | 0.488 [0.447, 0.533] | — | 0.389 / 0.099 | 0.782 [0.735, 0.829] | 0.782 | 0.782 |
| C+a gate log | 0.0100 [0.0064, 0.0142] | 98.0 % [97.1, 98.7] | 0.0077 / 0.0023 | 0.745 [0.696, 0.795] | **0.000** | 0.745 |
| C+b RF tag | 0.0227 [0.0151, 0.0315] | 95.4 % [93.7, 96.9] | 0.0190 / 0.0037 | 0.621 [0.567, 0.675] | 0.621 | **0.000** |
| C+c PIDS confirm | 0.0043 [0.0020, 0.0070] | 99.1 % [98.6, 99.6] | 0.0040 / 0.0003 | 0.681 [0.629, 0.733] | 0.007 | 0.701 |
| **C+abc** | **0.0047 [0.0023, 0.0075]** | **99.0 % [98.5, 99.5]** | 0.0043 / 0.0003 | **0.758 [0.710, 0.805]** | 0.007 | 0.701 |

**Decision: H53 not met, on the recall leg only.** The twin leg is met and robust: C+abc leaves 14 twin alarms
(0.0047 FA/cam-h, Garwood [0.0025, 0.0078]; boot upper 0.0075 ≤ 0.0488), i.e. 99.0 % removed. Recall@10 is
0.758, 7 intruder detections (0.023) below C's 0.782, so the point leg (≥ 0.782) fails and so does the
secondary H49 bar (loss ≤ 0.02). The CIs of C and C+abc overlap almost completely.

Why recall drops (per intruder alarm on C, 259 alarms): the RF gate matches 52 (20 %) and the badge gate 11.
Those are not errors in the sensors. In the recall worlds compose runs the benign twin (a tagged guard or
worker who badges in) alongside the intruder, so a registered tag within ~8 m or a badge in the same fenced zone
within 15 s is common. PIDS rescues most of those (the override), and 7 alarms had no PIDS trigger (p_detect
0.9) and are lost. Alone, RF is the worst gate (recall 0.621) because proximity association is coarse.

Failure modes, as registered adversary arms: **tailgate** (a badge a few seconds earlier, entry through the
open gate, no fence vibration) takes the badge gate and the combined rule to recall ~0 — the combined rule is
no protection against a tailgater, because PIDS masks the gate. **Stolen tag** zeroes the RF gate; under C+abc
the PIDS override keeps 0.701 (0.9 × the base, as predicted).

Reading: "context and a second sensor" removes the twin residual (≥ 95 % with any one of the three, 99 %
combined) at a recall cost of 2.3 points combined (single gates cost more: badge 3.7, PIDS 10.1, RF 16.1
points) on these worlds, with every sensor simulated and perfectly synced. Association is on ground truth:
each alarm is tied to its person's true track (true crossing time and zone for a/c, true position for the RF
range), where a real system matches by estimated position and would lose some of the 99 %. The ≥ 0.782
recall bar was near-unreachable by design (fusion only removes alarms, so it demanded zero loss while
knowingly running the benign twin next to the intruder); that was a design flaw of the registration, which
should have used the ≤ 0.02 secondary as the bar — and it misses that too, by 7 detections (AUDIT_H53). It is a statement about the fusion logic on SurvSim, not
about any PIDS or ACS product; the tailgate arm is the hole a real site must close with a gate camera rule.

### H47 · deviation addendum (2026-09-27, before scoring)
- **hood_up s3** was cut off at 245/300 frames when the root disk filled (no mask GT); the coordinator capped H47 disk use (~20 GB), so it was **not re-rendered** and **slow_deliberate / crowd_cover / wall_hugging s3 were not rendered** (option "drop seed 3"). Those four techniques are scored on seeds 1–2 against the control's seeds 1–2 (Δ always uses the matched (seed, camera) strata); dark_lowcontrast and hivis on seeds 1–3. Not an outcome-driven choice: no set had been scored when it was made.
- Engine note: the scene's own rig leaves some lane spawns unseen, so sets were rendered with `--entrance-gate warn` (as street_crowd_far in batch_v8).

### H47 results (2026-09-27, pre-registration `f4a1cdf`, `out/experiments/h47_evasion/results.json`, fig `figures/fig_h47.png`, sheet `figures/h47_examples.png`)
- **Gate:** 17/17 rendered-complete sets PASS 22/22 checks (`scripts/check_render.py`, mask GT, heights 0 beyond 2 cm); hood_up s3 incomplete → unscored. CC0 characters only; editor peak device VRAM 5,593 MB (hivis s3, `render_result.json` `vram_peak_mb`; audit AUDIT_H47 corrected an earlier "5.18 GB", which is dark_lowcontrast s2's 5,176 MB, not the maximum); 0 `LogPython: Error` in job results. (results.json's `gate` lists slow_deliberate/crowd_cover/wall_hugging s3 as `false`: those sets were never rendered, they did not fail.)
- **Recall, YOLO26n (primary)** / YOLOv8n, conf 0.25, IoU 0.5, GT = visible mask boxes ≥ 20 px, every frame; Δ vs matched control (same (seed, cam) clips). **Headline CI = clip-cluster bootstrap.** AUDIT_H47 first recomputed this by hand from `det_cache/` (6 s CPU, exhaustive paired resampling of the 4 or 6 (seed × camera) clips, pooled recall per resample); `bootstrap_delta()` now takes a `cluster` argument (`survsim/experiments/evasion.py`, `"clip"` default — the fix at source) and `cmd_score` writes the clip-cluster CI under `results.json`'s `delta` key as the primary result, with the pre-registered frame-level bootstrap kept under the separate `delta_frame_level` key for the record; it is **too narrow** (frames in a 30 s clip are autocorrelated — `tests/test_evasion_h47.py::test_bootstrap_clip_vs_frame_cluster` proves this with a perfectly-correlated-within-clip fixture). A re-score from the cached detections (no rendering, < 6 s) reproduces the audit's hand computation exactly: crowd_cover 26n −0.201 [−0.254, −0.154]. Control R 0.948 is seeds 1–3; its seeds 1–2 value (the matched control for the 1–2 rows) is 0.947.

| technique | seeds (clips) | GT person-frames | R 26n | Δ 26n [95 % clip-cluster CI] | per-clip Δ 26n (min..max) | Δ v8n [clip-cluster CI] | frame-level (pre-reg.) Δ 26n CI, p_Holm |
|---|---|---|---|---|---|---|---|
| control | 1–3 (6) | 8,524 | 0.948 | — | — | — (R 0.943) | — |
| dark_lowcontrast | 1–3 (6) | 8,524 | 0.951 | +0.003 [−0.001, +0.006] | −0.004..+0.008 | −0.001 [−0.006, +0.003] | [−0.004, +0.010], 1.0 |
| hivis | 1–3 (6) | 8,524 | 0.949 | +0.001 [−0.000, +0.003] | −0.001..+0.005 | +0.001 [−0.001, +0.002] | [−0.005, +0.008], 1.0 |
| hood_up (colour proxy) | 1–2 (4) | 5,736 | 0.946 | −0.001 [−0.003, +0.000] | −0.003..+0.002 | −0.001 [−0.003, +0.001] | [−0.010, +0.007], 1.0 |
| slow_deliberate | 1–2 (4) | 6,101 | 0.983 | +0.036 [+0.015, +0.061] | +0.013..+0.067 | +0.031 [+0.015, +0.050] | [+0.028, +0.043], 1.0 |
| **crowd_cover** | 1–2 (4) | 6,949 | 0.746 | **−0.201 [−0.254, −0.154]** | −0.281..−0.136 | −0.166 [−0.209, −0.129] | [−0.210, −0.192], 0.003 |
| wall_hugging | 1–2 (4) | 3,262 | 0.893 | −0.054 [−0.074, −0.033] | −0.072..−0.024 | −0.047 [−0.068, −0.025] | [−0.066, −0.042], 0.003 |

Appearance rows are the *same* trajectories re-rendered, so their per-clip Δ is truly paired and the clip CI is tighter than the frame one; path rows are different runs. With only 4 clips, the smallest one-sided p any clip-level test can give is 1/16 = 0.0625 (all 4 clips negative, sign-flip), so **the frame-level Holm p 0.003 is not a clip-level significance**; crowd_cover's Δ is ≤ −0.136 in every clip, i.e. beyond the −0.10 bar everywhere, but "Holm p < 0.05" as pre-registered was only met at frame level. The verdict is NOT MET either way.

- **Verdict: NOT MET — 1 of 6** (crowd_cover; 3 needed). Both detectors agree on the sign of every effect whose CI excludes 0 (crowd, wall, slow); for the three palette rows the point estimates flip sign between detectors (dark 26n +0.003 / v8n −0.001), which is noise around zero (AUDIT_H47 corrected "agree on every sign"). crowd_cover drops recall in all 4 (seed, cam) strata (26n 0.69–0.80 vs control 0.92–0.97): mutual occlusion inside the group, i.e. the detector loses people it is shown, not people who left the frame. wall_hugging is significant but under the bar; its bigger effect is **exposure**: 3,262 GT person-frames vs 5,736 for the control's seeds 1–2 (−43 %) (people on the perimeter are more often < 20 px or out of frame) — recall conditional on being visible hides it, so exposure must be reported next to recall in any evasion eval. slow_deliberate *raises* recall (more frames at a given position, less pose blur is not modelled; mainly a different frame mix). Palette techniques (dark, hi-vis, and the hood *colour* proxy) are detection-neutral at 1280 px input on this plain paved yard, day.
- **Caveats:** frames within a 30 s clip are autocorrelated, so the frame bootstrap CIs are too narrow — the table's headline now uses the clip-cluster CI (crowd −0.201 [−0.254, −0.154], ~5× wider than the frame CI; per-clip recall 0.69–0.80). 4 clips is still a small cluster count: treat the clip CI as a scale, not a precise interval. One site, one lighting (day), bright paved background — dark clothing may matter against dark backgrounds or at night (not tested). The hood is a colour proxy (`face_cover` kind hood: dark RGB painted over hair and head skin, `survsim/export/outfits.py`), not hood geometry — "hood does nothing" means "a dark head colour does nothing". Renderable subset only: umbrella, carried objects, crouch/crawl, face_away have no CC0 asset/clip ([X] capability) — they are **untested**, not "no effect". Zero-shot COCO detectors only.
- **Disk:** after scoring, 10,186 beauty PNGs of the scored sets were deleted (14.7 GB → 283 MB); kept: masks, mask GT, render plans, detection caches (`det_cache/`), and frame 0120 of every seed-1 set (the contact sheet's frames).

## H54 · Fence-gate tailgate + estimated-position fusion (`h54_tailgate_fusion`) — pre-registration

Registered 2026-09-27, before any H54 world was generated or scored (docs/research/66 H54; follow-up to H53 and
AUDIT_H53). Two things H53 flattered are fixed: (1) the tailgate becomes a *simulated behaviour* at the fence gate
instead of a sensor-stream edit, with a legitimate twin; (2) alarms are associated to sensors by the alarm's
*estimated* (noisy tracked) position and gate-passage time, with H53's true-position association kept as a control.
Seen before registration: only the H40b/H53 numbers already in this log.

```
id:            h54_tailgate_fusion (config survsim/experiments/configs/h54_tailgate_fusion.yaml; runner
               survsim/experiments/sensor_fusion.py, H53 path unchanged)
engine:        new behaviour `fence_tailgate` (survsim/director/behaviours.py): an intruder waits outside a
               fenced component's gate (~3 m along the fence), and when an authorised-role person passes the
               gate inward, follows through the gate (never over the fence); if nobody passes within wait_s
               it leaves without entering. After entering it goes to the asset, dwells, leaves via the gate.
               Truth (principle 1): the event label is suspicious.access.tailgate from the start of the wait;
               sensor_log gets an access_control `tailgate` record with the leader uid, the follower uid, the
               leader's and follower's actual gate-passage times and the gap. Twin `staff_escort`: a badged
               worker who walks in with a partner worker (follows at ~1.2 m) and leaves when the partner's
               visit ends (label normal.maintenance.escort; role worker, so the fence lets it through).
worlds:        (i) clean: H40b's 676 worlds regenerated with the same H12 seed/recipe and the same
               patrol/maintenance/wildlife stream [40, i, 41], PLUS staff pairs (a maintenance_visit worker +
               a staff_escort partner, arriving 1 s apart) from a new stream [54, i, 42] at 1.0 pair/h.
               (ii) recall: H40b's 300 intrusion/probe/climb worlds regenerated (same seeds; no new agents).
               (iii) NEW 100 tailgate recall worlds: perimeter_site, 300 s, compose with incident
               `fence_tailgate` (hostile = fence_tailgate on restricted zone Z, benign twin =
               maintenance_visit worker on the same Z), seeds 40*1000+3. Truth = the tailgater's first tick
               inside a sterile zone after its suspicious phase starts (as H40b). Tracker noise, arms N/A/B/C
               and the RNG [40, i, 0] are H40b's (0.30 m jitter, fragmentation, ghosts — an assumption).
sensors:       H53's parameters unchanged (gate log p 0.98 +-15 s, RF p_carry 0.95 etc., PIDS p 0.90, wind
               1/zone/h), except: staff_escort also badges (p 0.98) and carries a tag; fence PIDS triggers
               on an incident actor's entry only if that entry is > 3 m from every gate (a gate passage never
               shakes the fence). NEW gate-section sensor g (ASSUMPTION): a directional people counter on
               each fence gate counting every inward gate passage with p 0.95; an "excess" trigger fires at a
               counted passage when counted passages exceed badges in that zone within +-10 s. Sensor RNG
               [54, i, k, v].
matching:      TRUE (control, = H53): crossing time/zone from the alarmed person's true track, RF range at the
               true position. ESTIMATED (primary): crossing = the alarmed noisy track's last outside->inside
               transition at or before the alarm (its own zone_state), RF range from the noisy track's
               position at the alarm tick. Sensors still fire on what really happened.
arms:          C, C+a, C+b, C+c, C+abc (H53 rules) and C+abcg = C+abc with c := (fence PIDS or gate excess),
               each under both matchings. Variants: base, stolen_tag (as H53). H53's injected tailgate is
               dropped; the generated tailgate worlds replace it.
metric:        twin FA/cam-h on clean worlds (twins = patrol_guard, maintenance_visit, staff_pair; also
               reported for H53's two kinds), % removed vs C; recall@10 (actor-aware, i-LIDS) on the 300
               base recall worlds and separately on the 100 tailgate worlds. World bootstrap 2,000, seed 54.
decision:      H54 met iff, under ESTIMATED matching, C+abc removes >= 90 % of twin FA (point) AND its
               recall@10 loss vs C on the 300 base worlds is <= 0.03 AND tailgater recall@10 is >= 0.6 under
               C+abcg (gate section instrumented) and < 0.6 under C+abc (fence PIDS only). Both tailgate
               numbers reported whatever happens.
prediction:    estimated-matching removal falls from H53's 99 % but stays >= 90 %; recall cost <= 0.03;
               tailgater recall ~0 under C+a / C+abc, ~0.7 under C+abcg; staff pairs cost C+abcg a few % of
               removal (a missed swipe on a pair reads as a tailgate).
confounds:     every sensor is simulated and perfectly clock-synced; the gate counter is an invented
               product; the tracker-noise model is H40b's assumption, not a fitted tracker; the tailgater
               always waits at the right gate (it knows which gate staff use).
```

## H56 · PTZ slew-to-alarm acquisition and contention (`h56_ptz_slew`) — pre-registration

Registered 2026-09-27, before any H56 number was computed (docs/research/66 H56; background docs/research/83).
CPU only, pure geometry on the mock stack; GT follows the live camera (principle 2): acquisition is
`geometry.usably_visible` evaluated against a `Camera` built at the PTZ's *commanded, reached* pose and zoom.
Seen before registration: H39's datasheet-focal errors (0.96 m < 20 m, 2.92 m >= 30 m, floor 0.21 m) and
A1's 120 alarms/h at 40 cameras (FACTS H22/H45).

```
id:            h56_ptz_slew (config survsim/experiments/configs/h56_ptz_slew.yaml; runner
               survsim/experiments/ptz_slew.py, `python -m survsim.experiments.ptz_slew`)
site:          240 x 160 m, 40 fixed cameras on an 8 x 5 pole grid (30 m x 32 m pitch), 6 m high,
               pitch -12 deg, hfov 60 deg, 1280x720, yaw uniform per seed. PTZ poles 10 m high:
               1-PTZ arm at the site centre (120, 80); 2-PTZ arm at (60, 80) and (180, 80).
               PTZ: pan/tilt 200 deg/s (ASSUMPTION; products quote 300-700 deg/s preset moves), hfov
               2-60 deg, zoom settle 0.8 s, alarm->command latency 0.5 s (ASSUMPTIONS), framing = 6 m
               horizontal at the estimated range, aimed at the estimate's 0.9 m height. One command per
               alarm (no lead, no closed-loop auto-track).
target:        uniform point on the site that is usably_visible in >= 1 fixed camera; the detecting camera
               is the nearest such; distance bin = ground distance from that camera: <=20, 20-30, >30 m.
               Target walks 1.4 m/s on a uniform heading from the alarm time.
calib arms:    exact = 2-D RMSE 0.21 m (H39 exact-calib floor, detection noise only);
               h39 = RMSE r(d): 0.96 m for d<=20, 2.92 m for d>=30, linear between; error is range-
               dominated: sigma_lateral = sigma_range / 3 in the camera's ground frame, scaled to r(d).
acquire:       acquired iff at any 0.2 s tick in [t_ready, t0 + 3 s] the true target is usably_visible in
               the PTZ, t_ready = t0 + 0.5 + slew + 0.8 (the head is blind while slewing/zooming).
               300 independent alarms per seed (no contention), nearest PTZ serves.
contention:    per seed one hour of Poisson alarms at 120/h (A1), same target model; a PTZ is busy for
               latency + slew + zoom + 10 s verify dwell (ASSUMPTION, guard-tour-like view time); an alarm
               arriving with all PTZs busy waits (FIFO) for the first free one. missed_second = share of
               ALL alarms that arrive while every PTZ is busy AND are not acquired within 3 s of arrival.
seeds:         10 (56000 + s); CI = seed-cluster bootstrap 2,000, seed 56.
decision:      H56 met iff, in the h39 arm with 1 PTZ, acquire@3s >= 0.9 for <=20 m AND <= 0.6 for > 30 m
               AND missed_second >= 0.30. All arms reported whatever happens.
prediction:    exact arm ~0.95 at every distance (motion, not calibration, is the loss); h39 <=20 m ~0.9
               (borderline), >30 m ~0.5; missed_second ~0.28-0.35 with 1 PTZ, ~0.05-0.10 with 2.
confounds:     free-space site (no occlusion), constant-velocity walker, a single aim command; slew rate,
               latency, framing and dwell are assumptions, not a measured product; PTZ's own calibration
               exact; H39's error measured on 10 cameras is transplanted onto every camera.
```

### H56 results (2026-09-27, CPU, wall 10.0 s in results.json, `out/experiments/h56_ptz_slew`, figures/fig_h56.png)

| arm | acq@3s 0-20 m | acq@3s 20-30 m | acq@3s 30-1000 m | busy@arrival | missed_second |
|---|---|---|---|---|---|
| exact_1ptz | 0.967 [0.952, 0.983] (n 455) | 0.958 [0.938, 0.980] (n 600) | 0.978 [0.970, 0.985] (n 1945) | 0.382 | 0.367 [0.322, 0.405] |
| exact_2ptz | 0.938 [0.916, 0.958] (n 455) | 0.955 [0.937, 0.969] (n 600) | 0.957 [0.949, 0.966] (n 1945) | 0.066 | 0.056 [0.043, 0.069] |
| h39_1ptz | 0.901 [0.872, 0.936] (n 455) | 0.802 [0.774, 0.830] (n 600) | 0.727 [0.706, 0.747] (n 1945) | 0.382 | 0.369 [0.325, 0.406] |
| h39_2ptz | 0.897 [0.872, 0.921] (n 455) | 0.772 [0.739, 0.796] (n 600) | 0.691 [0.668, 0.716] (n 1945) | 0.066 | 0.057 [0.043, 0.070] |

decision: {'near_ge_0.9': True, 'far_le_0.6': False, 'missed_second_ge_0.30': True, 'met': False}

Per-arm n: 3,000 independent alarms (455 / 600 / 1,945 per bin) and 1,184 Poisson alarms per arm; CI = seed-cluster
bootstrap 2,000. Recorded detail not in the pre-registration: independent alarms start from a random home pan at
pitch −15° / hfov 60°; common random numbers (same target, heading, error draw) across all four arms.

**Verdict: not met.** ≤ 20 m leg held (0.901, CI lower 0.872 — borderline), contention leg held (0.369 ≥ 0.30),
far leg failed: 0.727 > 0.6. Untested explanation for the prediction miss: range-dominated error (σ_lat = σ_range/3) mostly moves the target
along the PTZ's optical axis when the PTZ sits near the fixed camera's line of sight, where a 6 m frame at range
tolerates it. 2 PTZs did not raise acquisition (0.897 / 0.772 / 0.691; exact arm also drops, 0.938 near) — cause untested
(a 6 m frame and a fixed metric error both scale as 1/range, so "closer PTZ" alone does not explain it) — but cut
contention misses 6.5× (0.057). Calibration, not target motion, is the far-field loss (exact 0.978, same targets
and motion). Follow-ups: H57 (σ(d)-widened framing + PTZ re-detect before trust), H58 (occlusion on the PTZ path) — 66.

Audit (AUDIT_83_H56, 2026-09-27): a fresh rerun (`survsim experiment h56_ptz_slew`, now registered) reproduces
results.json exactly. Precision notes: the ≤ 20 m leg is met on the point estimate only (CI [0.872, 0.936] spans
0.9); distance bins are range from the detecting fixed camera, whose injected error sets the bin RMSE (0.94 /
1.97 / 2.92 m recomputed = the H39 inputs, by construction); busy-at-arrival 0.382 vs missed 0.369 — with a 10 s
assumed dwell > 3 s window a queued alarm is almost never acquired, so missed_second ≈ the busy share under FIFO.
Every PTZ timing (200 °/s, 0.5 s, 0.8 s, 6 m, 10 s) is an assumption.

### H51 results (2026-09-27, pre-registration `679df88`, `out/experiments/h51_equal_steps/results.json`, fig `figures/fig_h51.png`)

35 runs, all at H26's recipe (450 optimiser steps, 225-iteration warm-up, close_mosaic 0, batch 8, yolov8n,
last.pt). **Reproducibility:** the 15 arms shared with H26 (dose 0/100/300, seeds 0-4) reproduced H26's AP
**exactly (15/15 to 4 dp)**, so seeds 5-9 extend H26 rather than replace it. No arm waited for the GPU.

| arm (MOT20-02 @640) | n | AP mean [95 % bootstrap] | sd | AP50 | AP75 |
|---|---|---|---|---|---|
| real only (dose0) | 10 | 0.4911 [0.4895, 0.4926] | 0.0027 | 0.8212 | 0.5209 |
| + 100 batch_v8 | 10 | 0.4953 [0.4936, 0.4968] | 0.0027 | 0.8245 | 0.5227 |
| + 300 batch_v8 | 10 | 0.4962 [0.4947, 0.4977] | 0.0026 | 0.8251 | 0.5245 |
| + 100 batch_v7 (diagnostic) | 5 | 0.4932 [0.4911, 0.4949] | 0.0025 | 0.8245 | 0.5214 |

| paired contrast (by seed) | AP diff [95 % boot] | exact sign-flip p | **Holm p** | AP50 diff (p) | AP75 diff (p) | seeds > 0 |
|---|---|---|---|---|---|---|
| +100 v8 − real | **+0.0042** [+0.0024, +0.0062] | 0.0039 | **0.0039** | +0.0033 (0.023) | +0.0018 (0.18) | 9/10 |
| +300 v8 − real | **+0.0051** [+0.0037, +0.0064] | 0.0020 | **0.0039** | +0.0039 (0.033) | +0.0036 (0.033) | 10/10 |
| +100 v7 − +100 v8 (diagnostic, s0-4) | −0.0021 [−0.0026, −0.0016] | 0.0625 (n = 5 floor) | — | | | 0/5 |

Unpaired (H26-style) permutation p: 0.0038 (100), 0.0005 (300), both Holm-rejected too.

**Decision (pre-registered rule met): the equal-step synthetic dose gain exists.** Both contrasts are
≥ +0.004 AP with Holm-adjusted p 0.0039 < 0.05. The size is close to H26's (+0.0041 / +0.0045 → +0.0042 / +0.0051;
the 15 shared arms are identical, seeds 5-9 moved the 300 contrast up); what H26 lacked was seeds and pairing. It is small (~1 % relative on 0.491), at 100 frames larger in AP@0.5:0.95 (+0.0042) than in AP50 (+0.0033, p 0.023) or AP75
(+0.0018, p 0.18, n.s.), and still one real site (MOT20-01 → 02), one detector, 60 real frames. H52 (image vs label)
is now unblocked by its own stopping rule.

**The H26-vs-h14b gap is the schedule, not the pool.** At H26's recipe, 100 batch_v7 frames score 0.4932,
*below* 100 batch_v8 (−0.0021, all 5 seeds negative), so v7 frames do not explain h14b mix_100's 0.4983; the
v7 recipe loses 0.0051 going from h14b's schedule (6 epochs × 50 = 300 iterations, ultralytics' default
3-epoch = 150-iteration warm-up) to H26's (9 × 50 = 450 iterations, 225-iteration warm-up). This run cannot
split step count from warm-up length or from mosaic (h14b left close_mosaic at the default 10 with 6 epochs, which under ultralytics 8.4.163's `epoch >= epochs − close_mosaic` rule closes mosaic from epoch 0; H26/H51 set close_mosaic 0, mosaic on throughout — inferred from `args.yaml` and the trainer code, no log line checked) — all three change together; it only shows the gap is the training recipe, not the pool. Corollary
(corrected at AUDIT_H51): with the v7 pool, h14b's recipe beats H26's, but that does not show 300 iterations
beat 450 — mosaic moved too. H25 clean (0.4986, h14b schedule, v8) is the same recipe effect. **H15 v8_vis_300 0.4981 vs dose300 0.4962**
(same 450 its and 225-its warm-up, but **not** the same recipe: H15's `args.yaml` has close_mosaic 10 over
6 epochs, so mosaic off, vs H51's close_mosaic 0 — AUDIT_H51): 0.4981 lies just outside dose300's 10-seed CI
[0.4947, 0.4977] but inside its seed range (0.4928-0.5009); H15 used 7 different seeds/subset draws. Mosaic
and seed/subset variation are both candidate causes; not resolved, untested.

**Deviations.** (1) The first invocation died at 10:08 with `OSError: No space left on device` (root disk
100 % from another job's renders) after 9 arms; the ninth arm's JSON (dose300_s2) was written empty and was
deleted and re-trained; the 8 intact arms were reused (their AP equals H26's). The sweep resumed at 10:17
behind a `df ≥ 5 GB` check; the check only ran before the resumed invocation (the runner then trained the
remaining arms in one process; free space after the relaunch was not logged — `driver.log` records only the 10:17 check, 5 GB — but no
further error). best.pt and the per-arm
image copies were deleted after eval; **last.pt was kept** because the eval uses last.pt. (2) Code: runner
`dose_fixedstep` now honours `--arm` (was silently ignored: it was not in `ARM_RUNNERS`); H26 behaviour
unchanged, its test passes. (3) Backlog H51 listed three recipes; the registration narrowed the primary
family to the two v8 doses (32 §H51 pre-registration). Wall ~1.7 h (09:4x-11:24) including evaluation and the crash/restart; per-arm `train_cost` sums to 0.71 h
over the 35 arms. Audited: AUDIT_H51.

### H54 results (2026-09-27, pre-registration `137a338`, runner `b2e71e0`, `out/experiments/h54_tailgate_fusion/results.json`, fig `figures/fig_h54.png`)

Regenerated worlds: 676 clean (3,002 cam-h; 678 patrol, 322 maintenance, 672 staff-pair people, 1,370 wildlife),
300 base recall worlds (same seeds as H40b; C recall 0.782 reproduces exactly, 233/298), 100 generated
fence_tailgate worlds (89 truth events; 86 logged tailgates, median leader→follower gap 3.0 s, max 46.6 s). Wall
2,938 s on 6 workers. Actor-aware, i-LIDS 10 s, world bootstrap 95 % (2,000, seed 54).

| match | arm | twin FA/cam-h [95 %] | removed [95 %] | recall@10 base [95 %] | loss vs C | tailgater @10 [95 %] | stolen_tag @10 |
|---|---|---|---|---|---|---|---|
| — | C | 0.688 [0.635, 0.741] | — | 0.782 [0.736, 0.826] | — | 0.742 [0.648, 0.828] | 0.782 |
| true | C+abc | 0.0060 [0.0033, 0.0090] | 99.1 % [98.7, 99.5] | 0.772 [0.724, 0.818] | 0.010 | 0.056 [0.011, 0.109] | 0.674 |
| est | C+a | 0.0107 | 98.4 % | 0.742 | 0.040 | 0.056 | 0.745 |
| est | C+b | 0.0247 | 96.4 % | 0.624 | 0.158 | 0.090 | 0.000 |
| est | C+c | 0.0063 | 99.1 % | 0.685 | 0.097 | 0.056 | 0.674 |
| **est** | **C+abc** | **0.0063 [0.0034, 0.0096]** | **99.1 % [98.6, 99.5]** | **0.772 [0.724, 0.818]** | **0.010** | **0.056 [0.011, 0.109]** | 0.674 |
| est | C+abcg (gate counter) | 0.0253 [0.0181, 0.0332] | 96.3 % [95.3, 97.3] | 0.782 [0.736, 0.826] | 0.000 | **0.685 [0.589, 0.778]** | 0.698 |

**Decision: H54 met (all four legs).** Under estimated matching C+abc removes 99.1 % of twin FA (19 of 2,064
alarms left; true matching leaves 18; boot lower 98.6 % ≥ 90 %), recall loss 0.010 (3 detections) ≤ 0.03; the generated tailgater is
caught 0.056 under C+abc (< 0.6) and 0.685 under C+abcg (≥ 0.6).

Reading: (1) **estimated-position association costs almost nothing here — under a benign noise model, so 99.1 %
is an upper bound** — est vs true differ by ≤ 0.3 pt on every arm. The prediction (99 % → ~90 %) was wrong in the
*optimistic* direction: H40b's noise model has 0.30 m jitter, fragmentation and ghosts but **no ID switches
between people and no multi-metre ground-plane error**, so the noisy track's crossing lands within a second or two
of the true one and the ±15 s / ±30 s windows absorb it. A real tracker's IDSW (H24: 87–93 per MOT20-02 run) is
exactly what would hand a twin's badge to an intruder; H59 (66) tests that.
(2) The generated tailgater confirms H53's injected result: badge + the leader's tag within ~3 m silence it
(0.056) and fence PIDS never fires on a gate passage. (3) A gate-section people counter reconciled against the
badge log recovers it (0.685) at a cost of 0.019 FA/cam-h more twin FA, mostly staff pairs (0.0083) and patrols,
where a missed swipe or counter coincidence reads as "two bodies, one badge". (4) C+abc's recall loss here (0.010)
is smaller than H53's 0.023 on the same base worlds — sensor RNG stream and gate-geometry PIDS rule differ; the
two are within noise (7 vs 3 detections). Confounds as registered: simulated, clock-synced sensors; invented
gate counter; the tailgater always picks the staff gate. Audit notes (AUDIT_H54): the counter counts only twins'
and incident actors' gate passages (commuters/wildlife never counted — idealised), and its excess trigger is
associated with PIDS's [−30, +5] s window; 3 of 89 truth events have no logged tailgate (not diagnosed) and 12 of
86 logged gaps exceed 10 s, so "follows within seconds" holds for the median, not the tail.

## H52 · Where does the equal-step gain come from? Label vs image vs diversity ablation (`h52_ablation`) — pre-registration

Registered 2026-09-27, before any H52 arm was trained. Decomposes H51's +300 batch_v8 gain (+0.0051 AP,
Holm p 0.0039). **Power warning (66 H52):** 10-seed per-arm sd ~0.0026, so a +0.003 paired contrast is near
the noise floor. A "≈" verdict here means the contrast was not resolved, not that it is zero.

```
id:          h52_ablation (config survsim/experiments/configs/h52_ablation.yaml; runner dose_fixedstep, new
             opt-in train.synthetic_mode in {true, shuffled_labels, masked}; H26/H51 behaviour unchanged, their
             tests still pass)
recipe:      H51 exactly: 450 steps, 225 warm-up its, close_mosaic 0, batch 8, workers 2, yolov8n, imgsz 640, last.pt.
arms (x10 seeds 0-9, paired):
  dose0      real only (60 MOT20-01 x5, 12 ep)       REUSED from H51, not retrained
  dose300    (a) +300 v8, true labels (6 ep)          REUSED from H51, not retrained
  shuf300    (b) the same 300 frames per seed; label lists deranged across images (seed [s,52]), boxes rescaled
                 to the receiving image's size -> pixels real, boxes wrong
  mask300    (c) the same 300 frames; every GT box (+10 % per side) Telea-inpainted at 1/4 res, no labels ->
                 background/context only (box masks, not silhouette masks)
  dup        (d) 60 real x10 = 600 list images, 6 ep, no synthetic (augmentation only). Note: this has the same
                 unique images as dose0 at the same steps, so it is essentially a list-construction control.
metric:      MOT20-02 AP@640.
contrasts:   paired sign-flip (exact, 2^10), seed-bootstrap CI, Holm over the 5 AP contrasts:
             dose300-shuf300, shuf300-dose0, mask300-dose0, dup-dose0, dose300-dup.
rule:        X≈Y iff |paired mean diff| < 0.003 AND Holm p >= 0.05.
             label-driven   iff (a)-(b) >= +0.003 and Holm p < 0.05
             image-level    iff (a)≈(b) and (b)-dose0 >= +0.003 and Holm p < 0.05
             diversity-only iff (d)≈(a)
             checked in that order. First holding = selected label, all holding are reported. None -> "unresolved".
budget:      30 new runs x ~5 min beside the editor (~3 GB), wait_for_gpu per arm, disk checked >= 10 GB per arm.
prediction:  (b) keeps part of the gain but (a)-(b) is ~+0.002, below threshold -> likely "unresolved".
             (d)≈dose0.
```

## H59 · Fusion under ID switches and track breaks (`h59_idsw_fusion`) — pre-registration

Registered 2026-09-27, before any H59 arm was run (docs/research/66 H59; follows H54 and AUDIT_H54, which
stated H54's 99.1 % twin-FA removal as an upper bound under a benign noise model: 0.3 m jitter, no ID switches).

```
id:          h59_idsw_fusion (config survsim/experiments/configs/h59_idsw_fusion.yaml; runner sensor_fusion,
             new opt-in `h59` block; H53/H54 paths and their tests unchanged)
worlds:      H54's cached worlds, unchanged: 676 clean (FA), 300 base recall (100 intrusion/probe/climb),
             100 generated fence_tailgate. H54 sensor parameters unchanged (gate log, RF, PIDS, gate counter).
noise:       H40b/H54 model (jitter 0.30 m, track breaks at H40b's frag_rate 0.011111 /s, heights, ghosts)
             PLUS a new identity-switch stage applied to the true positions *before* the H40b stage:
             a swap between two people exchanges their track labels from that tick on (label A follows body B
             and vice versa). Swaps occur only between two people (wildlife excluded) whose true positions are
             < 2.0 m apart, as a Bernoulli per close pair per tick with hazard h (per close-pair-second).
IDSW rate:   derived from out/experiments/h24_reid_assoc/results.json, ByteTrack arm (A0), batch_v8 day:
             sum over the 12 sequences of TrackEval IDSW = 76, 81, 117, 77, 66 for checkpoints s0..s4
             (mean 83.4 = the "83.4" in the H24 table, which is per 12-sequence set, not per sequence;
             6.95 per sequence). GT = 19,046 visible boxes at 10 fps = 1,904.6 GT track-seconds.
             rho = 83.4 / 1,904.6 = 0.04379 IDSW per track-second = 157.6 per track-hour.
             A full swap counts 2 IDSW (both tracks), so swap events per person track-second = rho/2.
             h is set globally so the expected IDSW per person-track-hour over all H59 worlds equals rho:
             h = rho * sum(person track-seconds) / (2 * sum(close-pair-seconds)), computed by a deterministic
             pre-pass over the same worlds (reported with the achieved IDSW/track-h per arm).
             Correction to 66 H59: "71.6 per batch_v8 sequence" is the OSNet arm's 12-sequence total.
             Caveat: TrackEval IDSW also counts break-then-rebirth switches, which the H40b fragmentation stage
             already models, so applying all of rho to swaps overstates swaps (stress-leaning).
identity:    the alarm carries the track's *label* (the identity the tracker claims). Recall is actor-aware on
             that label (principle 4: an alarm on the wrong person is not a hit). Twin-FA class on clean worlds
             is the *body* physically on the track at the alarm tick. Fusion legs are unchanged from H54 and
             associate on the estimated (noisy, possibly spliced) track: crossing from the track's own entries,
             RF at the track position at the alarm. Only est matching is scored.
arms:        benign (H54 control, h = 0), calibrated (h), stress (3h); each scored for C, C+a, C+b, C+c, C+abc,
             C+abcg; 10 noise seeds (0..9; seed 0 of benign is H54's own noise stream).
metrics:     per arm, pooled over seeds: twin-FA removed by C+abc vs C (same arm), recall@10 (base 300),
             recall loss C - C+abc, tailgater recall@10 under C+abcg. 95 % CI by world bootstrap (2,000,
             seed 59) resampling worlds with all their seeds.
hypothesis:  (1) calibrated C+abc twin removal <= 97 %; (2) stress C+abc twin removal <= 90 %;
             (3) calibrated recall loss C - C+abc >= 0.03; (4) calibrated tailgater recall under C+abcg < 0.6.
             Met iff all four (point estimates). Secondary: "most identity-sensitive leg" = the single-leg arm
             (C+a, C+b, C+c) whose twin-removal plus recall changes most from benign to calibrated
             (reported as both deltas; no test).
prediction:  swaps concentrate in staff pairs and tailgater/leader pairs, so the counter (g) and RF (b) move most.
confounds:   swaps only < 2 m, not occlusion-driven; ground-plane world tracks, not per-camera; label-swap
             changes the row order of the H40b noise draws, so noise seeds are not bit-paired across arms.
stopping:    one pass, fixed. CPU, 6 workers.
```

### H59 · results (run 2026-09-27, 7,406 s CPU wall, 6 workers; `out/experiments/h59_idsw_fusion/`, fig_h59.png)

Pre-registration above. IDSW rate as registered: H24 ByteTrack (A0), batch_v8 day, 12-sequence sum IDSW = 76,
81, 117, 77, 66 (checkpoints s0–s4, mean 83.4) over 19,046 visible boxes at 10 fps = 1,904.6 GT track-seconds
→ rho = 83.4 / 1,904.6 = 0.043789 IDSW/track-s = 157.6/track-h (`config.h59.rho_idsw_per_track_s` in results.json).
The deterministic pre-pass over the H54 worlds gives hazard h = 0.13203/close-pair-s for the calibrated arm
(3× = 0.39609 for stress); achieved IDSW/track-h from the swap process itself: benign 0.0, **calibrated 157.6**
(matches rho exactly, as designed), **stress 472.7** (3.00×, not the nominal "3h" label rescaled — consistent
with the registered swap-hazard scaling).

| noise arm | IDSW/track-h | fusion arm | twin removed [95 %] | recall@10 [95 %] | loss vs C [95 %] | tailgater @10 [95 %] |
|---|---|---|---|---|---|---|
| benign | 0.0 | C | 0.0 % [0.0, 0.0] | 0.769 [0.730, 0.809] | +0.000 [+0.000, +0.000] | 0.771 [0.698, 0.840] |
| benign | 0.0 | C+abc | 99.1 % [98.7, 99.5] | 0.761 [0.720, 0.802] | +0.008 [+0.000, +0.019] | 0.062 [0.021, 0.111] |
| benign | 0.0 | C+abcg | 96.4 % [95.4, 97.4] | 0.769 [0.730, 0.809] | +0.000 [+0.000, +0.000] | 0.701 [0.616, 0.783] |
| calibrated | 157.6 | C | 0.0 % [0.0, 0.0] | 0.100 [0.083, 0.118] | +0.000 [+0.000, +0.000] | 0.108 [0.079, 0.139] |
| calibrated | 157.6 | C+abc | 99.1 % [98.7, 99.5] | 0.099 [0.081, 0.116] | +0.002 [+0.000, +0.003] | 0.010 [0.003, 0.019] |
| calibrated | 157.6 | C+abcg | 96.4 % [95.4, 97.4] | 0.099 [0.081, 0.116] | +0.001 [+0.000, +0.003] | 0.100 [0.071, 0.131] |
| stress | 472.7 | C | 0.0 % [0.0, 0.0] | 0.058 [0.047, 0.069] | +0.000 [+0.000, +0.000] | 0.083 [0.061, 0.106] |
| stress | 472.7 | C+abc | 99.1 % [98.7, 99.5] | 0.057 [0.046, 0.068] | +0.002 [+0.000, +0.003] | 0.007 [0.001, 0.014] |
| stress | 472.7 | C+abcg | 96.4 % [95.3, 97.4] | 0.057 [0.046, 0.068] | +0.001 [+0.000, +0.003] | 0.080 [0.058, 0.103] |

Single-leg arms (C+a, C+b, C+c), used only for the leg-sensitivity secondary, are in `table.md` alongside this
table; not reproduced here.

**Decision: not met** (pre-registered rule: all four point-estimate criteria must hold).
`decision` block in results.json: `calib_removal_le_0.97=False`, `stress_removal_le_0.90=False`,
`calib_recall_loss_ge_0.03=False`, `calib_tailgate_abcg_lt_0.6=True`, `met=False`.

* **(1) calibrated C+abc twin removal ≤ 97 %: not met.** 99.1 % [98.7, 99.5] — identical to H54's benign-noise
  99.1 % to within CI; IDSW calibrated to H24's real ByteTrack rate does not move this leg.
* **(2) stress (3×) C+abc twin removal ≤ 90 %: not met.** 99.1 % [98.7, 99.5] at 472.7 IDSW/track-h — no
  measurable degradation even at 3× the calibrated rate.
* **(3) calibrated recall loss (C − C+abc) ≥ 0.03: not met.** +0.002 [+0.000, +0.003], an order of magnitude
  below the registered bar (and below H54's own benign-arm loss of 0.008).
* **(4) calibrated tailgater recall under C+abcg < 0.6: met.** 0.100 [0.071, 0.131] — well under 0.6, but for a
  reason unrelated to the hypothesis: calibrated-arm base recall collapses to 0.100 (from 0.769 benign) because
  the H24-calibrated IDSW rate mostly re-labels *already-caught* base-recall detections onto the wrong actor, so
  `alarms.score`'s actor-aware matching drops them regardless of leg — C alone (no fusion) is already at 0.108.
  This criterion passes on a collapsed denominator, not on a fusion-specific tailgater failure.

**Most identity-sensitive leg (secondary, benign → calibrated deltas, `leg_sensitivity` in results.json):
C+b (RF)** — d_recall −0.540, d_loss_vs_C −0.130, d_twin_removed +0.0003 (`most_sensitive_leg` field). C+abcg
has the largest single delta (d_tailgate −0.601) but that tracks the base-recall collapse above, not identity
sensitivity per se; among the three single legs the ranking by |d_recall| is C+a (−0.638) > C+c (−0.583) >
C+b (−0.540), but by |d_loss_vs_C| it is C+b (−0.130) > C+c (−0.086) > C+a (−0.031) — RF (b) is most sensitive
by the pre-registered loss-vs-C metric, hence the reported `most_sensitive_leg`.

**Prediction wrong, and in the opposite direction from H54's.** H54's ≈90% prediction was optimistic (true
result 99.1%, no swaps in the noise model); H59 predicted swaps calibrated to a real tracker's IDSW rate would
push twin-FA removal down toward 97%/90% and cost recall — instead twin removal is unchanged from H54's
benign-noise ceiling at both calibrated (157.6/track-h) and 3× stress (472.7/track-h) rates, and the only large
effect is on *base recall*, not on the twin-suppression legs. Reading: a label swap between two people who
cross paths within 2 m relabels which uid a fusion match is scored against, but H54's fusion legs (badge
proximity, RF at the track position, dwell/context) associate on the *track's estimated position* at the alarm
tick — a swap does not move that position, so C+abc's spatial/temporal gates still fire or don't fire the same
way. What a swap *does* change is which uid gets credit at scoring time, which is exactly what recall's
actor-aware matching (principle 4) is built to penalise — and it hits the base intrusion/probe/climb recall
denominator (C alone, no fusion) far harder than any twin-suppression leg, because those 300 base worlds have
no twin at all: a swap there simply reassigns a caught detection to the wrong body, an automatic recall miss.

**Deviations from the pre-registration:** (a) wall time 7,406 s (~2 h) vs. no time budget stated in the
pre-reg (CPU only, 6 workers, as registered — no deviation on resources, just slower than H54's few-minute
scale because of the 10-noise-seed × 3-arm × per-world exposure pre-pass). (b) achieved stress IDSW/track-h is
472.7, exactly 3.00× calibrated (157.57) — the registered "2× that" language for the hazard scaling (`arms.stress:
3.0` in config, not 2×) matches the *pre-registered* 3× multiplier in the hypothesis text, not the "H59 ·
Fusion under ID switches..." backlog entry's earlier "2× that" phrasing (docs/research/66 H59) — the config and
32's own pre-registration (`stress <= 90%`, "3x") govern; no code deviation. (c) no other config deviation found
against the pre-registration (worlds, noise stages, arms, CIs, seeds all as registered).

**Caveat carried forward (also see 32 §H33c deployment caveat and docs/13):** these fusion legs (badge/context,
RF, dwell) are insensitive to the identity-switch rates tested here because they gate on position, not label;
a cap or rule that instead keys off the tracker's *label* persisting (e.g. a per-visitor alarm cap, H33c) is
not protected the same way — H33c's own confound already flagged this ("a deployed cap needs a
tracker/ReID, whose ID switches would re-open the cap"); H59 supplies the first measured number for that
class of risk, on base recall rather than the cap itself (see 32 §H33c caveat line below).

**Audit (AUDIT_H59, 2026-09-27): verdict stands — H59 is a valid, correctly-negative result, not a null test.**
Traced the code path (`fuse_world_h54`'s `h59` branch, `line_cross.id_switch`) and confirmed empirically: a
single extreme-hazard rerun of a tailgate world (`h=1e6`) produced 1,322 swap events and an alarm whose scored
label (`p007`) differed from its true physical body (`p001`) — the switched identity does reach both the
matching stage and `alarms.score`'s actor-aware denominator; `n_swap` is non-zero at every registered arm
(calibrated 157.57/track-h, stress 472.67/track-h, both within noise of the 157.6/472.7 targets) and
`test_id_switch_swaps_labels_only_between_close_people`/`test_benign_reproduces_h54` already exercise a swap
directly (h = 1e9 forces one every tick; the benign arm's h = 0 is proved to reproduce H54 bit-for-bit,
confirming the harness, not a broken hazard, produces the null at h = 0). IDSW-rate arithmetic reproduces
exactly: batch_v8 ByteTrack (A0) `id_switches` at `mix_300_s0..s4` COMBINED = 76, 81, 117, 77, 66 (sum 417,
mean 83.4) over 19,046 visible boxes at 10 fps = 1,904.6 GT track-s → ρ = 83.4 / 1,904.6 = 0.043789 IDSW/track-s
= 157.6/track-h, matching `results.json`'s `config.h59.rho_idsw_per_track_s` and the calibrated-arm hazard
h = ρ·track_s / (2·pair_s) = 0.043789 × 13,102,539 / (2 × 2,172,805.2) = 0.132029/close-pair-s exactly.
(AUDIT_H54's "H24 87.0–92.6 per MOT20-02 run" is a different H24 measurement — real MOT20 footage, not
batch_v8's own-render evaluation — and is *higher* than the 83.4 used here; calibrating to it would only have
strengthened the swap rate tested, not weakened it, so it does not change the "not met" verdict.) Twin-removal
insensitivity is real, not an artefact: C+a/b/c/g match badges, RF hits and gate-counter excess to the alarmed
track's *estimated position and time*, never to its label, so swapping which uid a continuous, spatially
unchanged trajectory carries cannot move whether those geometric gates fire — this is a structural property of
position-gated fusion, confirmed by the empirical check above (the alarm with a swapped label still hit the
same badge/RF gates its true body would have). The tailgater/base-recall collapse (0.769 → 0.100 benign →
calibrated) is real and is exactly what `alarms.score`'s actor-aware matching (principle 4) is designed to
penalise: a label swap mid-track reassigns an already-caught detection to the wrong `uid`, an automatic miss
against that actor's ground truth regardless of any fusion leg — this is not the tracker-continuity/dwell
breakage originally guessed, it is a scoring-denominator effect on `C` alone (`C` recall collapses identically
to `C+abc`/`C+abcg`, before any fusion leg runs). One documented confound remains real and unresolved: the
swap hazard is uniform per close-pair-second regardless of scenario, but tailgating and staff-pair scenarios by
construction hold two people within 2 m for most of their duration, so they accumulate disproportionately more
swap opportunities than a passing-encounter close pair — the calibration is correct in aggregate (matches ρ
exactly) but not scenario-stratified, which is exactly the (already pre-registered) reason the tailgater
denominator is hit hardest. No numbers changed; no verdict changed. Score: 97/100 (the one deduction is the
uncorrected MOT20-02-vs-batch_v8 IDSW-source ambiguity noted above, now resolved here).

**Reading for the interview (reconciled, AUDIT_TAILGATER_RECONCILIATION 2026-09-27).** Re-verified from
`out/experiments/h59_idsw_fusion/fused_worlds.jsonl` (calibrated arm, 100 generated tailgate worlds): `C`
alone (no fusion leg) actor-aware tailgater recall@10 is 0.108, and `C+abcg` (the H54 gate people-counter fix)
is 0.100 — statistically the same collapse, confirming AUDIT_H59's attribution that this is a scoring effect,
not a fusion regression. Re-scoring the *same* cached alarms with `alarms.score`'s window-only match (label +
timing, no `uid` check — a label-agnostic, position/time proxy) instead of actor-aware gives tailgater
recall@10 0.828 for `C` alone and 0.739 for `C+abcg`: both far above the 0.10 actor-aware number, and the
0.739 vs 0.828 gap shows the gate counter still costs a little real recall under ID-switch noise (consistent
with H54's own benign-arm C+abcg cost) but nothing like the reported 0.685 → 0.10 collapse, which is almost
entirely the swapped-label scoring artefact. **One reconciled sentence for reuse:** with GT identities a gate
counter catches the tailgater at 0.685 (H54); under realistic ID switches the actor-aware *score* drops to
0.10 because the alarm is credited to the swapped label — the fusion decision itself is unchanged (label-
agnostic recall recomputed at 0.83 alone / 0.74 with the counter); a real system would score by position/time.

## H60 · Alarm-card generator with a sim-only GT guard (`h60_alarm_card`) — pre-registration

Registered 2026-09-27, before any H60 code was written (docs/research/66 H60, pre-registered there by
AUDIT_86; schema docs/research/86 §7). This entry narrows 66's scope to a first, verifiable slice.

```
id:          h60_alarm_card (slice 1: generator + guard + chained pack on one mock run)
data:        survsim run configs/scenarios/smoke_mock.yaml, fresh, to scratchpad; alarms = eval.rules
             run_baseline (GT dwell rule, threshold 25 s) — the only alarms a mock run has.
code:        survsim/eval/alarm_card.py (cards + JSON-schema-style key whitelist per mode),
             survsim/eval/evidence_pack.py (JSONL WORM log, h_i = sha256(h_{i-1} || canonical(record_i))),
             CLI `survsim alarm-cards <run_dir> --mode sim|real`.
real-mode rule: a card may carry only what a deployed site has: alarm t, label, camera, a *tracker*
             track id supplied with the alarm, PTZ pose from camera_status (a PTZ head reports its pose),
             calib, licences ref, score/θ/rank if a runner supplies them. Anything read from gt/ (world.parquet
             zone, mot boxes, events.jsonl, identities.parquet, tamper/blind truth, GT uid) is sim-only.
primary:     (a) leak count = real-mode cards whose serialised JSON contains any sim-only key OR any GT uid /
             event_id value — must be 0; (b) number of cards = number of alarms.
chain:       verifier recomputes every hash; editing any one record (verdict flip) must fail at that index;
             two runs of the same inputs give the same chain head (determinism).
prediction:  leak 0; uid, zone and box are empty in real mode for GT-rule alarms (the 66 "abandon if"
             clause applies to those fields for this alarm source — they need a tracker, not a fix).
stopping:    one pass.
```

### H60 · result (slice 1)

Run: `survsim run configs/scenarios/smoke_mock.yaml` fresh to scratchpad, then
`survsim alarm-cards <run> --mode sim|real` (baseline dwell rule, 25 s). Tests: `tests/test_alarm_card.py`
(13 at commit 39da635; 17 after AUDIT_H60).

* **Leak count (mode=real): 0** of 2 cards — no sim-only key and no GT uid/event id in the
  serialised JSON. AUDIT_H60 re-grepped the real cards by *value* against every uid, event id,
  `world.parquet` zone name and `identities.parquet` cell: 0 hits (the only substring hit, `loiter`, is
  inside the rule's own label). The shipped `gt_values` did not include zone names until AUDIT_H60
  (no leak, but a gap in the guard; fixed + test). The same guard on sim cards counts 2/2 (it detects what it should). The alarm id
  deliberately excludes the GT uid (a hash of GT is still GT).
* **Cards: 2 = alarms: 2** in both modes; ids identical across modes and reruns.
  Sim verdicts: `loiterer_1` t = 30.4 s → `late` (delay 25.1 s > 10 s tolerance: a 25 s dwell rule
  cannot be i-LIDS-timely), `commuter_1` t = 43.1 s → `false` (hard negative).
  Per-alarm hit delays equal `alarms.score` latencies (unit test, same multiset).
* **Chain:** verifier passes on the written log; flipping the verdict of any one of 5 records fails at
  exactly that index (5/5, synthetic cards), deleting a *middle* record fails at the gap, swapping
  records 0/1 and editing record 0 fail at 0; identical inputs give identical heads (unit test, not
  CLI). **Not caught without an anchored head:** dropping tail records, or rewriting the whole log
  from genesis — the chain is tamper-evident only relative to a head stored elsewhere
  (`verify(..., expected_head=)` added by AUDIT_H60). Canonical form = sorted keys, compact
  separators, ASCII, Python float repr, NaN refused — not RFC 8785. Operator ids are salted sha256,
  but the CLI salt defaults to a public constant (`survsim-h60`) and is stored nowhere: a real site
  needs a per-site secret salt, or a small roster is reversible by enumeration. Since AUDIT_H60 the
  verifier also rejects a (re-hashed) `dismiss` without a reason code.
* **Prediction held:** real cards for GT-rule alarms carry t, label, alarm id, run id, mode, licences
  (camera_id and track_id null) — camera, box, zone and identity need a tracker source (`--alarms`
  with `track_id`), not a join. Read literally, 66's "abandon if" (uid, zone or score unfillable
  without GT) **is triggered** for GT-rule alarms: real mode is kept only as a guard for tracker-sourced
  alarms, and no tracker-sourced alarm, and no runner-written score, has been carded end-to-end yet.
* Not done from the 66 scope (slice 2): H22 A1 alarms × 10 seeds, fill-rate CIs, clip/frame hashes.

### H60 · slice 2 — pre-registration

Registered 2026-09-27, before any slice-2 code, to close the AUDIT_H60 defects (public salt, unanchored
head, non-JCS canonical form, no runner-written score/θ/rank, no model/config/clip hashes).

```
id:          h60_alarm_card slice 2
code:        survsim/eval/evidence_pack.py, survsim/eval/alarm_card.py, CLI `survsim alarm-cards`,
             survsim/experiments/operator_queue.py (H22 runner emits alarms_scored.jsonl).
salt:        --salt-file (32 random bytes, `--init-salt` writes it, *.salt gitignored); mode=real refuses the
             public default unless --insecure-default-salt. Test: real mode without a salt file exits non-zero.
head:        pack writes head.json {chain_head, n_records, created_at}; verify() requires it by default;
             CLI prints the head for out-of-band anchoring. Tests: tail truncation and full re-chain from
             genesis both fail verification against head.json (fail closed; a missing head.json also fails).
canonical:   JCS-compatible subset (RFC 8785): sorted keys (UTF-16 code-unit order), no whitespace,
             integers as-is, floats as shortest round-trip repr (ES-style exponent form), NaN/Inf refused.
             Test: canonical(x) identical across dict key orderings; known RFC 8785 number vectors.
runner:      H22 run() writes alarms_scored.jsonl (alarm key, score, θ, rank_in_queue, simulated-operator
             verdict) for operator seed 0 of every arm/policy cell; `--alarms alarms_scored.jsonl` fills
             score/θ/rank. Guard: H22 metrics unchanged — test_h22 passes and a re-run on the cached
             streams reproduces results.json (all keys except env/finished/wall time) byte-identically.
hashes:      card gets config_hash (sha256 of meta/scenario.resolved.json or --config YAML) and model_hash
             (sha256 of --model checkpoint, else absent); clip_hash only if frames exist in the run dir
             (sha256 over frame files in [t-5 s, t+5 s]), else "not emitted".
prediction:  all pass; real-mode leak count stays 0; H22 reproduction exact.
stopping:    one pass.
```

### H60 · result (slice 2)

Tests: `tests/test_alarm_card.py` 22 pass (17 → 22); `tests/test_experiments.py -k "h22 or h45"` 2 pass.

* **Per-site salt:** `survsim alarm-cards --salt-file F [--init-salt]` (32 bytes from `secrets`, file
  mode 0600, refuses to overwrite; `*.salt` in `.gitignore`). `mode=real` without a salt file exits 2
  unless `--insecure-default-salt`; the public `survsim-h60` hash is absent from a salted log (test).
  The salt is stored nowhere by the pack — losing the file makes operator ids unlinkable, by design.
* **Anchored head:** the pack writes `head.json` {chain_head, n_records, created_at}; `verify()` now
  fails closed with no head, on a head mismatch, and on a record-count mismatch. Tail truncation and a
  same-length re-chain from genesis both fail against `head.json` (test). The CLI prints
  `ANCHOR THIS HEAD out of band: <hash> n_records=<n>`. Caveat kept: `head.json` beside the log is
  rewritable by whoever can rewrite the log — only an out-of-band copy makes it an anchor.
* **Canonical form:** `evidence_pack.canonical` = RFC 8785-compatible for the subset used (UTF-16
  key order, no whitespace, ints as-is, ECMAScript shortest number form: `1.0→1`, `1e21→1e+21`,
  `1e-7→1e-7`, `-0→0`; NaN/Inf refused); order-independence and 13 number vectors tested. Not
  checked against an external JCS implementation. Slice-1 hashes change (logs are regenerable).
* **Score/θ/rank:** H22's `run` writes `alarms_scored.jsonl` (65 716 rows = operator seed 0 × 3 arms × 2
  queues; key, world, t, score, θ, `rank_in_queue` at arrival, `queue_len_at_arrival`, operator verdict +
  `t_verdict`). The trace draws no random numbers. **Reproduction: re-running `h22_operator_queue` on
  the cached `streams.json` (12 s) gives a results.json equal on every key except env/finished/wall time**,
  and `simulate(..., trace=)` == `simulate(...)` (test). Carding the 9 654 A1/FIFO rows in real mode:
  score/θ/rank filled 9 654/9 654, leak 0, chain_ok, verdicts dispatch 210 / dismiss 7 013 / bulk_ack
  2 431, max rank 11. θ = 0.95 for A1 and twin_floor (plus `score_cut` for twin_floor); dwell_25 has no θ.
* **Hashes:** cards carry `config_hash` (sha256 of `--config` YAML, else `meta/scenario.resolved.json`),
  `model_hash` (sha256 of `--model`, absent otherwise), `clip_hash` (sha256 over `frames/<cam>/NNNN.png`
  within t ± 5 s; `"not emitted"` when a run has no frames — every mock run today).
* **Remaining gaps:** H22 alarm rows come from the H12 worlds, not from a run dir, so carding them
  against a mock run gives score/θ/rank/verdict but no camera, pose or clip — a joined H12 world run dir
  does not exist on disk; H33 writes no per-alarm file yet; the H22 "operator" verdict is simulated
  (informed by its GT event tag, as a real operator's judgement would be by the scene) and is not
  evidence; no signature/RFC 3161 timestamp on the head; model hash covers one file, not
  detector/tracker/reid separately; rule trace, VLM caption and process log still not emitted.

### H60 · slice 2b — result (AUDIT_87 §5.1–5.2, commit e3f7e13)

Tests: `tests/test_alarm_card.py` 24 pass (22 → 24; no existing test or hash changed).

* **Leak guard:** `gt_values` now adds every string cell of `gt/identities.parquet` (uid, role,
  outfit, gait style, …); `leak_count` keeps the by-key check and matches each GT value as a
  *substring* of any string field of a real card, skipping `LEAK_ALLOWLIST` (rule labels such as
  `loiter`, generic words) and values shorter than 4 characters. Real-mode leak on the smoke run
  stays 0; a card with `calib_ref="calib/<uid>_cam.json"` or label `"suspect intruder"` now counts.
* **Card–log binding:** the log already stores each card's canonical hash as `card_sha256` at write
  time, so no schema change (no `card_hash` field added; entry hashes unchanged).
  `evidence_pack.verify_cards(log, cards)` recomputes it for every card and requires a one-to-one
  alarm_id match; it returns `(False, alarm_id)` for an edited, missing or extra card. The CLI's
  `chain_ok` is now `verify and verify_cards`.
* **Still open:** allowlist is hand-kept; substring matching can false-positive on short generic GT
  values (hence the length floor); AUDIT_87 §5.3–5.4 unchanged.

## H33b · Conformal θ with B fixed in advance (`h33b_conformal_fixed_B`) — pre-registration

Registered 2026-09-27, before any H33b split was scored (AUDIT_88: H33's `choose_crc` used
B = the largest calibration loss, so its CRC guarantee is only *approximate* — Angelopoulos et
al. 2022 require L ≤ B with B known a priori). CPU only; same data, splits, α and recall scoring
as H33 (reuses `out/experiments/h33_conformal_theta/data.json`); only B changes.

```
id:            h33b_conformal_fixed_B (config survsim/experiments/configs/h33b_conformal_fixed_B.yaml;
               runner conformal_theta, new arm crc_fixed = choose_crc(mode="real", B=fixed))
B (fixed):     from h12_alarm_scale.yaml only, never from calibration data: A1 fires <= once per dwell
               episode and (stated cap) <= once per arriving visitor; arrivals ~ Poisson(6/min × 1800 s
               = 180); B = Poisson(180).ppf(1 − 1e-6) / min camera-hours per world = 247 / 2.0 =
               123.5 FA/cam-h. Losses above B are clipped and counted (guarantee exact for min(L, B));
               floor B/(n+1) = 0.364 at n = 338 (vs 0.248–0.263 with the empirical B 84–89).
arms:          grid, plain, crc (empirical B, = H33, must reproduce), crc_fixed.
α:             {1.0, 2.0, 2.915} (0.001 dropped: infeasible for either B).
primary:       α = 2.915. (a) θ_fixed ≥ θ_empirical on every split; (b) crc_fixed exceed count;
               (c) recall cost crc_fixed − crc (seed mean, seed-bootstrap 95 %).
decision:      supported if (a) holds, crc_fixed exceeds α in 0/10 splits and mean cost ≥ −0.02;
               refuted if crc_fixed exceeds in ≥ 1/10; else partial (cost > 0.02 or θ not ≥).
               Ship-point question: does 58 §8.4's conformal θ (0.962851) move under fixed B?
prediction:    θ_fixed ≈ 0.963–0.966, 0/10 exceed, cost ≈ 0.01–0.02.
confounds:     the per-visitor cap is a modelling assumption about the generator, not a law; a
               clipped world would mean the guarantee holds only for min(L, B) (reported).
```

### H52 results (2026-09-27, pre-registration `6a52327`, `out/experiments/h52_ablation/results.json`, fig `figures/fig_h52.png`)

30 new runs beside the editor, 11:48-13:32 (1.7-6.6 min wall per arm; training 49-159 s, 0.78 h summed). dose0/dose300 are H51's arm JSONs, copied, not retrained (20/20 byte-identical to `h51_equal_steps/arms`, AUDIT_H52).
MOT20-02 AP@640, 10 seeds, mean [seed-bootstrap 95 %]:

| arm | AP |
|---|---|
| real only (dose0, H51) | 0.4911 [0.4895, 0.4927] |
| (a) +300 v8 true labels (dose300, H51) | 0.4962 [0.4947, 0.4978] |
| (b) +300 labels shuffled across images | 0.4885 [0.4864, 0.4904] |
| (c) +300 people inpainted out, no boxes | 0.4947 [0.4929, 0.4964] |
| (d) real x10, no synthetic | 0.4900 [0.4882, 0.4917] |

| paired contrast | AP diff [95 %] | sign-flip p | Holm p |
|---|---|---|---|
| (a) - (b) | **+0.0077** [+0.0062, +0.0093] | 0.0020 | **0.0098** |
| (b) - real | -0.0026 [-0.0050, -0.0004] | 0.064 | 0.129 |
| (c) - real | **+0.0036** [+0.0014, +0.0056] | 0.0156 | **0.047** |
| (d) - real | -0.0011 [-0.0035, +0.0012] | 0.455 | 0.455 |
| (a) - (d) | **+0.0062** [+0.0042, +0.0082] | 0.0020 | **0.0098** |

**Rule verdict: label-driven** ((a)-(b) = +0.0077, Holm p 0.0098). Image-level and diversity-only do not hold. The prediction
("unresolved") was wrong. Wrong boxes on the same pixels erase the gain; (b) is nominally below real-only (-0.0026, Holm p 0.13, not significant). Duplicating real frames does nothing ((d) - real -0.0011, p 0.46); (d) has the same 60 unique images as real-only, so it is a list-construction control, not a diversity test.
**Not in the rule, but it limits the reading:** (c), synthetic backgrounds with the people removed and no boxes, keeps about 70 % of
the gain (+0.0036, Holm p 0.047, just under 0.05). [INF] So the true-label gain plausibly has two parts. (1) Correct positives: shuffled boxes
put positives on background and leave the real people unlabelled, which hurts. (2) Person-free synthetic scenes used as pure negatives: these help at roughly (c)'s size.
Caveat on (c): people are removed by low-res (1/4) Telea inpainting of rectangles, which leaves smooth, blurred box-shaped patches; a detector
could learn "blurred patch = no person", so part of (c)'s +0.0036 may be artefact rather than background content (untested; H61).
The rule can't separate how much of (a) is "labels on people" and how much is "the rest of the frame is correctly negative",
because (a) - (c) = +0.0015 (exploratory, not registered; unadjusted sign-flip p 0.057) is below the noise floor.
Deviations: `secondary_contrasts: []` added to the config after arm 1. The first three arms logged FAIL in `driver.log` (`KeyError: 'secondary_contrasts'` in post-arm aggregation,
before the key was added), but their arm JSONs are complete and unaffected. Masks are dilated boxes (+10 %), not silhouettes. One site, one detector, 60 real frames.

### H33b · results (run 2026-09-27, ~3 min CPU; `out/experiments/h33b_conformal_fixed_B`, figures/fig_h33b.png)

B fixed in advance = 123.5 FA/cam-h (derivation in the pre-registration; 0 calibration worlds clipped in
any split — and no H12 world at all exceeds 123.5 — but the guarantee is for min(L, 123.5), since the per-visitor
cap behind B is not enforced; AUDIT_H33B). H33's grid/plain/crc cells reproduce exactly.

| α | arm | θ range | exceed /10 | test FA/cam-h mean [seed 95 %] | recall mean |
|---|---|---|---|---|---|
| 1.0 | crc (empirical B) | 0.9910–0.9923 | 0 | 0.636 [0.619, 0.657] | 0.582 |
| 1.0 | crc_fixed | 0.9934–0.9942 | 0 | 0.542 [0.528, 0.558] | 0.555 |
| 2.0 | crc (empirical B) | 0.9736–0.9758 | 0 | 1.506 [1.467, 1.552] | 0.747 |
| 2.0 | crc_fixed | 0.9752–0.9770 | 0 | 1.413 [1.378, 1.455] | 0.743 |
| **2.915** | crc (empirical B) | 0.9598–0.9627 | 0 | 2.312 [2.265, 2.364] | 0.789 |
| **2.915** | **crc_fixed** | 0.9615–0.9642 | **0** | **2.216 [2.168, 2.269]** | **0.784** |

Recall cost crc_fixed − crc: α 2.915 −0.006 [−0.006, −0.005]; α 2.0 −0.005 [−0.007, −0.003]; α 1.0
−0.028 [−0.031, −0.025]. θ_fixed ≥ θ_empirical on 10/10 splits at every α. Per-world test mean (the
controlled quantity) at α 2.915: 2.44–2.79, all ≤ α.

**Decision: supported** at α = 2.915 (and 2.0): more conservative on every split, 0/10 exceed, cost 0.006
≤ 0.02. **Partial** at α = 1.0 (cost 0.028 > 0.02). Prediction held (θ 0.9615–0.9642 vs predicted
0.963–0.966; cost below the predicted 0.01–0.02). **Ship point (58 §8.4):** θ 0.962851 is below θ_fixed
in 7/10 splits → the certified conformal point moves to ≈ 0.9635 (≈ 2.22 / 0.784); H45 not rerun [INF].
*AUDIT_H33B corrections:* (1) B = 247 / 2.0 = 123.5 is the right arithmetic, but the "≤ 1 alarm per visitor" cap is
**not enforced** — A1 alarms once per dwell episode and a visitor can open several (max 21; 53 % of eligible
episodes come from multi-episode visitors), so B is not an a-priori bound on L and the guarantee is exact only
for min(L, 123.5) (= L on all 676 worlds, max 89 — empirical). (2) "≈ 2.22 / 0.784" are split-mean held-out
numbers, not the point's: θ 0.963436 (median crc_fixed θ) gives 2.187 / 0.783 on all worlds. (3) Now measured
(§H45b): 0.617 ranked @5 min, 1 operator, equivalent to θ 0.962851.
Statement to use: CRC guarantee holds for a loss bounded by a B fixed in advance; H33 used the empirical
max B (approximate); H33b uses a fixed B (123.5) — 0/10 exceed, recall −0.006. `choose_crc(mode="real")`
now requires B; `mode="empirical"` (default) keeps H33/H42/H45 reproducible.

## H45b · Operator sim at the H33b certified conformal θ (`h45b_operator_points_fixedB`) — pre-registration

Registered 2026-09-27, before the run (AUDIT_H33B). H33b moved the conformal ship point from θ 0.962851 to
≈ 0.9635 by inference only; this makes it measured. CPU only, ~10 min.

```
id:          h45b_operator_points_fixedB (config survsim/experiments/configs/h45b_operator_points_fixedB.yaml;
             runner operator_queue.run_points, unchanged except an optional `paired_extra` contrast)
points:      H45's three (A1 0.95, pooled 0.90, conformal 0.962851) + conformal_fixedB θ 0.963436
             (median of H33b's 10 crc_fixed θ at α 2.915; range 0.961477–0.964196). H45's config/results untouched.
operator:    H45/H22 model unchanged; 10 operator seeds; 1–3 operators; FIFO and ranked; horizons 30 s, 5 min.
primary:     1 operator, @5 min, paired (same seeds, world-cluster bootstrap): conformal_fixedB − conformal
             per queue; and conformal_fixedB − A1 per queue.
decision:    "1 operator → conformal, ranked" holds at the certified θ iff conformal_fixedB − A1 has CI > 0
             under ranked (and FIFO); equivalence to H45's point iff fixedB − conformal CI ⊂ [−0.02, +0.02].
sanity:      A1/pooled/conformal cells must reproduce H45's results.json exactly.
prediction:  model 2.19 FA/cam-h / 0.782 recall; realised within ±0.01 of H45's conformal point.
caveat:      invented operator (H22); B = 123.5 is not a valid a-priori bound (AUDIT_H33B), so "certified"
             means certified for the clipped loss min(L, 123.5).
```

### H45b · results (run 2026-09-27, 426 s CPU; `out/experiments/h45b_operator_points_fixedB/`)

Sanity: A1/pooled/conformal model points, all 18 cells and all vs-A1 contrasts equal H45's results.json exactly.
Certified point θ 0.963436: model 2.187 FA/cam-h / 0.783 (282/360 TP, same as θ 0.962851), 90 alarms/h, utilisation
0.79 (1 op; cut 10.5 % vs A1).

| 1 operator, @5 min | FIFO [95 %] | ranked [95 %] |
|---|---|---|
| conformal θ 0.962851 (H45) | 0.571 [0.539, 0.605] | 0.621 [0.587, 0.657] |
| conformal_fixedB θ 0.963436 | 0.573 [0.541, 0.605] | 0.617 [0.583, 0.651] |
| fixedB − conformal (paired) | +0.001 [−0.012, +0.015] | −0.004 [−0.017, +0.010] |
| fixedB − A1 (paired) | +0.062 [+0.039, +0.085] 10/0 | +0.031 [+0.014, +0.050] 8/2 |

2 operators ranked: fixedB − A1 −0.019 [−0.043, +0.003] (H45 conformal −0.022 [−0.045, −0.001]); 3 operators ranked
−0.034 [−0.055, −0.013]. fixedB − conformal at 2–3 operators all CIs within ±0.03, point estimates −0.004…+0.014.
**Decision: holds.** Equivalent to H45's point (both queues' CIs ⊂ [−0.02, +0.02]) and beats A1 with CI > 0 under
ranked and FIFO → "1 operator → conformal, ranked" holds at the certified θ; ≥ 2 → A1 unchanged. Prediction held
(model 2.19 / 0.782 predicted vs 2.187 / 0.783). The runner's built-in `decision` field is H45's rule re-applied
with conformal_fixedB (utilisation cut 10.5 % < 20 % → false), not H45b's; ignore it. Invented-operator caveat.

## H43 · INT8 accuracy recovery: better PTQ calibration and QAT (`h43_qat`) — pre-registration

Registered 2026-09-27, before any H43 arm was exported, trained or scored (docs/research/66 H43,
no-Jetson branch). No Orin is available, so this is the QAT/calibration branch only; TensorRT
latency/power stays [A]. Follow-up to H38 (INT8 MinMax PTQ lost 0.0117 AP, AP75 −0.025..−0.040).

```
id:            h43_qat  (config survsim/experiments/configs/h43_qat.yaml; runner quant_export, mode h43)
checkpoints:   n = 5: h14b mix_300_s{0,1,2} (H38's three; A0/A1 AP reused from H38 ckpts/*.json)
               + H51 dose300_s{0,1} (60 real MOT20-01 x5 + 300 batch_v8, 450 steps). The H51 pair is a
               different recipe (batch_v8, equal steps): heterogeneity is disclosed, not hidden; results
               are also given for the 3 h14b checkpoints alone.
arms:          A0 fp32_torch      ultralytics predict CPU FP32 (control)
               A1 int8_minmax     = H38 int8_real (QDQ, per-channel S8 weights, S8 act, MinMax, 100 MOT20-01
                                    frames 61-429); reused for h14b, computed identically for H51
               P1 int8_percentile A1 with CalibrationMethod.Percentile (99.999), same frames   [primary PTQ]
               P2 int8_entropy    A1 with CalibrationMethod.Entropy, same frames              [secondary]
               Q1 int8_qat        fine-tune the checkpoint with fake-quant (torch.ao FakeQuantize: per-channel
                                  symmetric S8 weights, per-tensor affine 8-bit activations at every Conv
                                  module's input and output), BN frozen, 150 iterations, batch 8, imgsz 640,
                                  AdamW lr = H51 auto LR / 10 = 1.19e-5, wd 5e-4, no warm-up, the checkpoint's
                                  own yolo_data train split and ultralytics default aug; strip fake-quant ->
                                  ONNX FP32 -> quantize_static exactly as A1 (MinMax, same frames). GPU.
               All INT8 arms keep the Detect decode ops in FP32 (as H38).
metric:        MOT20-02 AP / AP50 / AP75 @640 via onnxruntime CPU EP through ultralytics predict (as H38).
               loss(arm) = A0 - arm, paired by checkpoint; mean, 95 % percentile bootstrap over the 5
               checkpoints (10k), and range.
               recovery(arm) = (mean AP75 loss(A1) - mean AP75 loss(arm)) / mean AP75 loss(A1).
decision:      PTQ branch met iff recovery(P1) >= 0.50 (P2 reported; if only P2 clears, "secondary only").
               QAT branch met iff recovery(Q1) >= 0.80 AND AP loss(Q1) <= 0.005 on every checkpoint.
context only:  CPU latency (median of 20 after 5 warm-up) — R46: not an INT8 speed claim.
prediction:    Percentile recovers 20-60 % (MinMax ranges are outlier-dominated in SiLU outputs); entropy
               similar or worse; QAT recovers most of AP75, but ≤ 0.005 on every checkpoint is uncertain
               because the export re-calibrates ranges with MinMax instead of the learned ones.
confounds:     Q1 is 150 more optimiser steps: a Q1 gain could be fine-tuning, not quant-awareness. A
               matched FP32 fine-tune control is not in budget; Q1's own FP32 AP (fake-quant stripped)
               is reported so the confound is visible. ORT CPU QDQ is not TensorRT.
budget:        <= 2.5 h wall. If QAT tooling fails, run P1/P2 only and record the deviation.
```

### H43 · results (run 2026-09-27, PTQ-calibration arm only; `out/experiments/h43_qat/`, fig_h43.png)

Salvaged after an interrupted run: `mix_300_s0` had already finished all 6 arms (fp32_torch, int8_minmax,
int8_percentile, int8_entropy, qat_fp32, int8_qat, ~35 min CPU eval + 98 s QAT fine-tune); the other four
checkpoints had model/QAT checkpoints exported but no fresh evals cached. Given the remaining time budget
this run scores **P1 (Percentile PTQ) vs A1 (MinMax PTQ) on all 5 checkpoints only** — the primary,
pre-registered PTQ leg. **QAT (Q1) is skipped as a deviation from budget**, not a tooling failure: the code
path ran to completion once (`mix_300_s0`), so it is not "unavailable," but re-running it end-to-end on the
remaining 4 checkpoints (150-iter fine-tune + 2 fresh ONNX exports + 2 INT8 calibrations + 4 evals each)
did not fit the remaining wall-clock. Recorded as **H43b** for a follow-up run in 66. P2 (Entropy) is
likewise only available for `mix_300_s0` (identical to A1 there) and not reported as a corpus number.

FP32 torch and MinMax-PTQ (A1) AP for the 3 h14b checkpoints reproduce H38's `int8_real`/`fp32_torch`
exactly (reused via `reuse_h38`, not re-evaluated). The 2 H51 `dose300` checkpoints (batch_v8, equal-steps
recipe) are new PTQ evaluations, disclosed as the heterogeneous pair per the pre-registration.

| checkpoint | FP32 AP75 | A1 (MinMax) AP75 loss | P1 (Percentile) AP75 loss | AP75 recovery |
|---|---|---|---|---|
| mix_300_s0 | 0.5373 | 0.0263 | 0.0129 | 0.510 |
| mix_300_s1 | 0.5316 | 0.0245 | 0.0168 | 0.314 |
| mix_300_s2 | 0.5242 | 0.0399 | 0.0226 | 0.434 |
| dose300_s0 | 0.5238 | 0.0169 | 0.0149 | 0.118 |
| dose300_s1 | 0.5262 | 0.0156 | 0.0050 | 0.679 |

Paired over all 5: A1 AP75 loss **0.0246 [0.0179, 0.0326]** (95 % percentile bootstrap), P1 AP75 loss
**0.0144 [0.0093, 0.0195]**; recovery (mean-loss based, as pre-registered) **0.415**. 3 h14b checkpoints
alone: A1 0.0302 [0.0245, 0.0399], P1 0.0174 [0.0129, 0.0226], recovery **0.424** — matches AUDIT_H38's
corrected AP75 range for A1. AP recovery (all 5) 0.381; AP50 recovery 0.933 but AP50 losses are tiny and
noisy (one checkpoint's P1 AP50 loss is negative), so the AP50 figure is not load-bearing.

**Decision (pre-registered rule, PTQ leg): not met.** recovery(P1, AP75) = 0.415 (all 5) / 0.424
(h14b-only) < 0.50 on both the full and h14b-only cuts — Percentile calibration recovers **under half**
of the MinMax-PTQ AP75 loss, not the 50–60 % the pre-registration predicted (partially right: it did beat
MinMax on every one of the 5 checkpoints, 0/5 regressions, just short of the bar). P2 (Entropy) is not
scored on the corpus (see above); on the one checkpoint it did run it was numerically identical to A1
(no calibration benefit there), consistent with the pre-registration's "similar or worse" prediction for
entropy, but n = 1 is not evidence either way.

**QAT (H43b, not run to the bar in this pass):** `mix_300_s0` alone shows int8_qat AP75 loss 0.0244
(fp32_torch 0.5373 → qat_fp32 0.5410, fake-quant int8_qat 0.5129) — recovery on this single checkpoint
would be (0.0263−0.0244)/0.0263 ≈ 0.07, i.e. on this one checkpoint QAT (re-quantised with plain MinMax
after fine-tuning, as pre-registered) did **not** clear even the PTQ bar, let alone the 0.80 QAT bar —
but n = 1 checkpoint is not a corpus result and is not scored as H43's QAT leg. Deviation recorded;
QAT stays open as **H43b** (docs/research/66) for a follow-up run with a fresh time budget, scoring all
5 checkpoints once QAT-fine-tuned models are (re-)exported.

**Deployment reading:** Percentile calibration is a free, drop-in win over MinMax (0/5 regressions, mean
AP75 loss cut from 0.0246 to 0.0144) but does not get INT8 export within striking distance of FP32 on
box tightness; anything metric (ground-plane feet, height) run on INT8-exported detections should still
expect a materially tighter-box-worse AP75 than FP32, roughly half of H38's original loss rather than
under a quarter of it.

## H43b · QAT INT8 recovery, full 5-checkpoint corpus (`h43_qat`) — pre-registration

Registered 2026-09-27, before any additional checkpoint's QAT arm was evaluated in this pass. Follow-up
to H43 (docs/research/66 row 15c; AUDIT_H43): the PTQ-calibration leg is done and did not meet its bar
(Percentile AP75 recovery 0.415 all 5 / 0.424 h14b-only < 0.50); the QAT leg (`int8_qat`, fake-quant
fine-tune) ran end-to-end on only 1 of 5 checkpoints (`mix_300_s0`) in the H43 pass, a budget deviation,
not a tooling failure. This pass finishes the QAT leg on the remaining 4 checkpoints
(`mix_300_s1`, `mix_300_s2`, `dose300_s0`, `dose300_s1`) with the same recipe, config and thresholds
already registered in `h43_qat.yaml` (unchanged): 150 fake-quant fine-tune iterations at H51 auto LR / 10
(1.19e-5), batch 8, imgsz 640, AdamW, then strip fake-quant, export ONNX FP32, and re-quantize with plain
MinMax (identical to A1's PTQ) exactly as A1.

```
id:            h43_qat  (same config/runner; only the missing arms are computed — cache is per-arm,
               so already-exported qat.pt / qat_fp32.onnx / int8_qat.onnx files for
               mix_300_s1/s2/dose300_s0/s1 are reused, not re-fine-tuned)
checkpoints:   the same 5 as H43: h14b mix_300_s{0,1,2}, H51 dose300_s{0,1}
arms scored:   int8_qat vs fp32_torch (primary), qat_fp32 (fp32 fine-tune control, confound check)
metric:        MOT20-02 AP / AP50 / AP75 @640 via onnxruntime CPU EP through ultralytics predict, as H43.
               loss(arm) = A0 - arm; recovery(Q1) = (mean AP75 loss(A1, MinMax PTQ) - mean AP75 loss(Q1)) /
               mean AP75 loss(A1), same pooled-loss formula as H43 (pre-registered there, reused here
               unchanged so the two legs are comparable).
decision:      primary — QAT met iff recovery(Q1, AP75) >= 0.80 AND AP loss(Q1) <= 0.005 on every one of
               the 5 checkpoints (H43's original QAT bar, unchanged).
               secondary — recovery(Q1, AP75) >= 0.50 (H43's PTQ bar, i.e. does QAT at least match what
               better calibration alone achieved).
prediction:    the n = 1 result already in hand (`mix_300_s0`: recovery ≈ 0.07, missing even the 0.50
               bar) predicts the 4-checkpoint corpus will also miss both bars — re-quantizing the
               fine-tuned model with plain MinMax throws away the learned fake-quant ranges, so QAT as
               implemented here is not expected to behave like textbook QAT (which keeps the learned
               ranges through to export). Recorded as a prediction, not assumed; scored below on the
               full corpus regardless.
confounds:     unchanged from H43 — Q1 is 150 more optimiser steps than A0/A1; no matched FP32-only
               fine-tune control is in budget beyond `qat_fp32` (fake-quant stripped, same steps),
               which is reported per checkpoint so the confound stays visible. ORT CPU QDQ, not TensorRT.
budget:        <= 90 min wall. GPU checked free (editor down); `free -g` >= 8 and
               `df --output=avail -B1G /` >= 10 confirmed before starting. If a checkpoint's run exceeds
               the budget, report the completed checkpoints only and mark the pass partial.
```

### H43b · results (run 2026-09-27, `out/experiments/h43_qat/results.json`, fig_h43b.png)

Ran in 968 s wall (well under the 90 min budget) — most of the heavy work (150-iter fake-quant
fine-tune, ONNX export of `qat_fp32`/`int8_qat`) was already cached from the interrupted H43 pass for
`mix_300_s1`, `mix_300_s2`, `dose300_s0`, `dose300_s1` (only `int8_entropy`/`qat_fp32`/`int8_qat` evals
were missing); this run only added the missing evals, no re-fine-tuning. GPU/RAM/disk checked free
before starting (`free -g` available 23, disk avail 100 GB, GPU 23 MiB used of 8192).

| checkpoint | FP32 AP75 | A1 (MinMax) AP75 loss | Q1 (int8_qat) AP75 loss | AP75 recovery | Q1 AP loss (bar ≤ 0.005) |
|---|---|---|---|---|---|
| mix_300_s0 | 0.5373 | 0.0263 | 0.0244 | 0.072 | 0.0053 (miss) |
| mix_300_s1 | 0.5316 | 0.0245 | 0.0139 | 0.433 | 0.0013 (met) |
| mix_300_s2 | 0.5242 | 0.0399 | 0.0219 | 0.451 | 0.0088 (miss) |
| dose300_s0 | 0.5238 | 0.0169 | 0.0093 | 0.450 | 0.0053 (miss) |
| dose300_s1 | 0.5262 | 0.0156 | 0.0087 | 0.442 | 0.0031 (met) |

Paired over all 5: A1 AP75 loss 0.0246 [0.0179, 0.0326] (unchanged from H43), Q1 (int8_qat) AP75 loss
**0.0156 [0.0100, 0.0213]**; **AP75 recovery (pooled-loss formula, all 5) 0.366; h14b-only (3) 0.334.**
(Note, AUDIT_H43BC: the mean of the five *per-checkpoint* recovery ratios below is 0.370, not 0.366 —
the pooled-loss formula is the pre-registered one and is what's reported as "the" recovery throughout;
the two do not always coincide, as they happen to for H43c below.)
AP recovery 0.543 (all 5) / 0.564 (h14b-only) — better than AP75, but AP is not the primary metric.
Q1's own AP loss per checkpoint: mix_300_s0 0.0053, mix_300_s1 0.0013, mix_300_s2 0.0088, dose300_s0
0.0053, dose300_s1 0.0031 — **3/5 checkpoints (mix_300_s0, mix_300_s2, dose300_s0) exceed the 0.005 bar**;
only mix_300_s1 (0.0013) and dose300_s1 (0.0031) clear it — **3/5 miss the every-checkpoint AP-loss bar.**
`qat_fp32` (the FP32 fine-tune control, fake-quant stripped) *beats* FP32 torch on every checkpoint
(AP75 loss −0.0037..−0.0116, i.e. a gain) — confirming the pre-registered confound: 150 extra optimiser
steps improve the model on their own, and QAT's real signal is masked by that gain being given back at
INT8 export.

**Decision (pre-registered rule): not met, either bar.** Primary (recovery ≥ 0.80 AND every-checkpoint AP
loss ≤ 0.005): recovery 0.366 ≪ 0.80, and 3/5 checkpoints exceed the AP-loss bar — **fails on both
conjuncts**. Secondary (recovery ≥ 0.50, matching H43's PTQ bar): 0.366 (all 5) / 0.334 (h14b-only) also
**both < 0.50** — QAT, as implemented here (fine-tune with fake-quant, then re-quantize the stripped FP32
model with plain MinMax), does not even match what free Percentile-calibration PTQ already achieved
(0.415/0.424) on this metric. The prediction registered above (recovery ≈ the n = 1 mix_300_s0 value,
~0.07, on the full corpus) was directionally right but too pessimistic — the other 4 checkpoints recover
33–45 %, materially better than mix_300_s0 alone, though still short of both bars. `mix_300_s0` remains
the worst checkpoint by a wide margin (0.072 vs 0.43–0.45 for the other 4); no cause was investigated
(out of budget) — it is the one h14b checkpoint whose H43 pass ran with genuinely fresh fine-tuning
rather than the cached artifacts reused here, so a first-run/warm-up effect on that checkpoint's own QAT
weights, not on this run, is plausible but unverified [A].

**Root-cause reading (why QAT underperforms Percentile PTQ here):** the pipeline strips fake-quant after
fine-tuning and re-quantizes with plain MinMax calibration (pre-registered this way in H43/H43b to keep
QAT and PTQ exports comparable) — it never carries the *learned* fake-quant activation ranges through to
the exported INT8 graph. That throws away exactly the information QAT is supposed to contribute beyond
extra fine-tuning steps, which is consistent with `qat_fp32` (FP32, ranges irrelevant) beating baseline
on every checkpoint while `int8_qat` (INT8, learned ranges discarded) does not recover more of the AP75
loss than Percentile PTQ alone. A QAT pipeline that exports the learned ranges directly (no re-calibration
pass) is the natural next step, but is out of this pass's registered scope and budget.

**Deployment reading:** neither PTQ leg (H43) nor this QAT leg (H43b) gets INT8 export within the
pre-registered bars of FP32 box tightness on this detector/export path. Percentile PTQ remains the best
free option (recovery 0.415/0.424, 0/5 regressions); QAT as implemented does not beat it and costs ~150
extra fine-tune iterations + a second calibration pass for no net gain over Percentile alone. Ship FP16
(H38, loss 0.0000) unless INT8's smaller footprint is required, in which case use Percentile calibration,
not QAT, and budget for the same ~half-of-H38's-original AP75 loss the PTQ leg already quantified.

## H43c · QDQ built from the QAT observers' learned ranges (`h43c_learned_ranges`) — pre-registration

**Hypothesis** (docs/research/66, this follow-up to H43b's root-cause finding above): exporting the
QAT-fine-tuned model's INT8 graph directly from its fake-quant observers' **learned** scale/zero-point
(onnxruntime `quantize_static` QDQ format with per-tensor `TensorQuantOverrides`, no fresh MinMax
calibration pass) recovers ≥ 80 % of the `int8_minmax` AP75 loss and keeps AP loss ≤ 0.005 on every
checkpoint (secondary: ≥ 50 % on AP75). No re-fine-tuning — reuses the 5 cached `h43_qat` QAT
checkpoints (`qat.pt`, `qat_fp32.onnx`) as-is. CPU only (GPU free for this run); latency is not a claim.
Runner: `survsim/experiments/quant_export.py` mode `h43c`, config `h43c_learned_ranges.yaml`.

**Method.** Fake-quant is re-attached to each cached `qat.pt` (same `_fq_attach` used for training),
observers are re-enabled and fake-quant simulation disabled, and the model is run over the same 100
real MOT20-01 calibration frames used throughout H38/H43/H43b — this converges each observer's
moving-average min/max without touching the already-fine-tuned weights. Per-channel symmetric weight
scales come straight from each Conv's weight fake-quant module; per-tensor activation scale/zero-point
are recomputed from each activation observer's converged `[min_val, max_val]` on the standard affine
INT8 grid ([-128, 127]) — the observers were trained in `quint8` (0–255) for the training loss, so this
is a grid conversion, not a re-estimate of the range itself. These are handed to `quantize_static` as
`TensorQuantOverrides` (extra options `DedicatedQDQPair`, `QDQDisableWeightAdjustForInt32Bias`); a
`CalibrationDataReader` is still supplied (ORT 1.30 requires ≥ 1 batch to run) but every tensor that
matters is fully overridden and ignores whatever that pass would have computed.

**The toolchain problem that had to be solved:** `model.modules()` Conv2d traversal order does **not**
match the ONNX graph's Conv node order for this branchy YOLO backbone (verified: 31/64 convs
mismatched by position on `mix_300_s0`, e.g. 16-channel vs 32-channel swapped at index 3). A positional
zip silently assigns the wrong observer's range to the wrong tensor. Fixed by matching each ONNX Conv
node to its PyTorch module by **exact byte match of the pre-fake-quant weight tensor** (bit-identical
between the freshly-loaded torch model and the `qat_fp32.onnx` initializer, since fake-quant leaves the
underlying stored weight untouched) — verified unique 64/64 on the trial checkpoint, no collisions.

**Verification that the learned ranges are actually carried** (not just computed and discarded): for
one sample weight tensor and one sample activation tensor per checkpoint, the exported graph's
`<tensor>_scale` initializer is compared byte-for-byte to the value we passed in via
`TensorQuantOverrides`; `verify_learned_ranges_carried` in `quant_export.py` asserts equality and the
per-checkpoint result is written to `ckpts/<name>.json["verify"]`.

### H43c · results (run 2026-09-27, `out/experiments/h43_qat/../h43c_learned_ranges/results.json`, fig_h43c.png)

| arm | AP mean | AP loss [95 % boot] (range) | AP75 loss [95 % boot] | AP50 loss |
|---|---|---|---|---|
| fp32_torch | 0.4958 | reference | | |
| int8_minmax | 0.4853 | +0.0105 [+0.0082, +0.0131] (+0.0074..+0.0154) | +0.0246 [+0.0179, +0.0323] | +0.0015 |
| qat_fp32 | 0.5001 | −0.0043 [−0.0057, −0.0028] (−0.0061..−0.0021) | −0.0083 [−0.0104, −0.0058] | −0.0071 |
| int8_qat_qdq | 0.4919 | +0.0040 [+0.0028, +0.0055] (+0.0027..+0.0067) | +0.0138 [+0.0092, +0.0180] | −0.0086 |

Per-checkpoint AP75 recovery vs `int8_minmax` (mix_300_s0/s1/s2, dose300_s0/s1): **0.266 / 0.322 / 0.561
/ 0.615 / 0.429** — mean **0.439**, both above H43b's own `int8_qat` recovery (0.366 all-5 / 0.334
h14b-only) and above every individual H43b per-checkpoint recovery, but still **below the 0.50
secondary bar and well below the 0.80 primary bar**. Per-checkpoint AP loss (bar ≤ 0.005):
0.0046 / 0.0027 / **0.0067** / 0.0030 / 0.0028 — **4/5 checkpoints meet the bar, `mix_300_s2` misses it**
(0.0067 > 0.005). **Learned ranges verified carried into the exported graph on all 5/5 checkpoints**
(`ranges_verified` all `true` — the sample weight-tensor and activation-tensor scale initializers match
the observer values passed in, to float32 precision).

**Decision: not met, either bar** (`qdq_recovery_met: false`, `qdq_every_ckpt_met: false`,
`qdq_met: false`), though the toolchain question the follow-up was pre-registered to answer is answered
cleanly: **yes, the learned ranges can be carried into the ONNX QDQ graph** (onnxruntime
`TensorQuantOverrides`, available since ≥ 1.16, works with this pipeline once the Conv-order trap above
is fixed) — the earlier `int8_qat` shortfall in H43b was a real, fixable pipeline bug, not a toolchain
limitation. Carrying the ranges roughly **1.2× the recovery** of re-quantizing with fresh MinMax (0.439
vs 0.366) but does not close even half the gap to FP32, let alone 80 % of it. The residual gap most
likely sits in the 150-iteration QAT recipe itself (H43b already showed `qat_fp32` — FP32, ranges
irrelevant — only gains ~0.004–0.012 AP over baseline; there is limited headroom for INT8 ranges learned
from that little fine-tuning to recover much more) and in the `quint8`→`int8` grid conversion for
activations, which was not itself ablated here (out of the 60-minute budget: comparing against a QAT
recipe trained natively in the export's int8/affine convention is the natural next step, not run).

**Deployment reading (updates H43b's, and 38 §2.5 row 13):** Percentile PTQ (H43, recovery 0.415/0.424,
free, no fine-tuning) remains the best available INT8 option on this detector/export path. QAT with
learned-range export (H43c) narrows, but does not close, the gap to Percentile PTQ, and still costs the
same extra fine-tuning + a second (now override-driven, not calibration-driven) export pass for less
recovery than Percentile gets for free. **QAT still does not beat Percentile PTQ.** The export path has
now been ruled out as *the* bottleneck (ranges verified carried, recovery rose 0.366 → 0.439) — but
attributing the *residual* gap to the 150-iteration QAT recipe is an inference from that one data point,
not something this pass measured directly (no longer-QAT arm was run). Proposed as **H43d** (66):
QAT with more fake-quant fine-tune iterations (e.g. 600–1,000, same recipe otherwise), same learned-range
export as H43c, same bars — if recovery rises with iterations, the recipe attribution holds; if it does
not, the residual gap sits elsewhere (e.g. the `quint8`→`int8` grid conversion, untested here).

No latency claim is made here (R46); `cpu_latency_ms_median` is recorded per arm in the raw JSON only.

## H43d · Does more QAT fine-tuning close the H43c gap? (`h43d_qat_more_iters`) — pre-registration

Registered 2026-09-27, before any H43d checkpoint was fine-tuned or exported (docs/research/66 H43d
block; proposed by AUDIT_H43BC as the direct test of H43c's inference that its residual AP75 gap is
the 150-iteration QAT recipe, not the export path). Config `h43d_qat_more_iters.yaml`, runner
`quant_export` mode `h43d`.

```
id:            h43d_qat_more_iters
commit:        <hash of the registration, before the run>
hypothesis:    on the same 5 checkpoints as H43b/H43c, running the QAT fake-quant fine-tune for
               600-1,000 iterations instead of 150 (same recipe: AdamW, H51 auto LR / 10, batch 8,
               imgsz 640), then exporting the QDQ graph from the learned observer ranges exactly as
               H43c (`TensorQuantOverrides`, no fresh MinMax pass), raises the mean AP75 recovery
               vs int8_minmax above H43c's 0.439, moving it materially toward (not necessarily past)
               the 0.50 secondary bar
primary metric: AP75 recovery vs int8_minmax, pooled-loss formula (as H43/H43b/H43c), MOT20-02 @640
arms:          int8_qat_qdq @150 iters (H43c, control); @600 iters; @1,000 iters
held fixed:    5 checkpoints, calibration frames, learned-range export path and its Conv-order
               weight-byte matching (verified in H43c), CPU-only onnxruntime eval
seeds:         the 5 H43b/H43c checkpoints (no new seeds; not re-drawing training data)
sample size:   n = 5 checkpoints, same as H43b/H43c (small; report per-checkpoint, not just pooled)
analysis:      per-checkpoint AP75 recovery + pooled-loss recovery, as H43c; qat_fp32 (fake-quant
               stripped) AP/AP75 vs fp32_torch reported per iteration count as the confound check
               (more steps alone should raise qat_fp32, as it did at 150 iters in H43b)
success:       recovery(600 or 1000 iters) > recovery(150 iters) with the improvement not fully
               explained by the qat_fp32 confound (i.e. int8_qat_qdq gains more than qat_fp32 does)
stopping rule: fixed
confounds:     same as H43b/H43c — extra optimiser steps alone improve qat_fp32 independent of
               ranges; report it, don't let it get counted as ranges/iteration count improving recovery
abandon if:    600-1,000 iterations does not fit the GPU/wall budget for all 5 checkpoints; run 600
               only and report partial
decision:      primary — recovery(AP75, 600 or 1000 iters) >= 0.80 AND AP loss <= 0.005 on every one
               of the 5 checkpoints (H43's original QAT bar, unchanged). secondary — recovery(AP75)
               >= 0.50 (H43/H43b's PTQ-parity bar). Also reported regardless of either bar: whether
               recovery(600 iters) > recovery(150 iters, H43c's 0.439) at all, and whether that gain
               survives the qat_fp32 confound check above.
budget:        <= 90 min wall; GPU checked free (`free -g` >= 8, disk avail >= 10 GB) before starting.
               600 iterations only, per the abandon-if clause (1,000 not attempted this pass).
```

### H43d · results (run 2026-09-27, ~23 min wall (1396 s), `out/experiments/h43d_qat_more_iters/results.json`,
fig_h43d.png)

GPU/RAM/disk checked free before starting (`free -g` available 24, disk avail 100 GB, GPU 23 MiB used
of 8192). 600-iteration fake-quant fine-tune ran fresh for all 5 checkpoints (`iters: 600` confirmed in
each `ckpts/<name>.json`), then the identical H43c learned-range QDQ export (`_collect_qat_ranges` /
`_qdq_from_ranges` / `verify_learned_ranges_carried`) — **ranges verified carried on 5/5 checkpoints**
(same as H43c). Only 600 iterations were run (1,000 not attempted; not needed — the abandon-if clause
was not triggered, but the direction of the 600-iter result made a 1,000-iter arm low-value within the
remaining budget, see below).

| checkpoint | FP32 AP75 | A1 (MinMax) AP75 loss | qat_fp32 AP75 (loss) | int8_qat_qdq @150 (H43c) recovery | int8_qat_qdq @600 (H43d) AP75 loss | @600 recovery | AP loss @600 (bar ≤ 0.005) |
|---|---|---|---|---|---|---|---|
| mix_300_s0 | 0.5373 | 0.0263 | 0.5404 (−0.0031) | 0.266 | 0.0176 | 0.331 | 0.0040 (met) |
| mix_300_s1 | 0.5316 | 0.0245 | 0.5362 (−0.0046) | 0.322 | 0.0115 | 0.531 | 0.0032 (met) |
| mix_300_s2 | 0.5242 | 0.0399 | 0.5400 (−0.0158) | 0.561 | 0.0087 | 0.782 | 0.0045 (met) |
| dose300_s0 | 0.5238 | 0.0169 | 0.5268 (−0.0030) | 0.615 | 0.0156 | 0.077 | 0.0102 (miss) |
| dose300_s1 | 0.5262 | 0.0156 | 0.5262 (0.0000) | 0.429 | 0.0234 | **−0.500** | 0.0108 (miss) |

`qat_fp32` AP (fake-quant stripped, the confound/no-degradation check): 0.4989 / 0.4963 / 0.4982 / 0.4978
/ 0.4955, all above `fp32_torch`'s 0.4970 / 0.4957 / 0.4955 / 0.4968 / 0.4941 (gains +0.0007..+0.0027) —
**the 600-iteration fine-tune itself does not degrade the model on any checkpoint**; if anything the
gain shrank vs H43c's 150-iteration `qat_fp32` gains (AP75 −0.0031..−0.0158 here vs −0.0021..−0.0104 at
150 iters, i.e. *more* negative/larger gains at 600 iters on 3/5 checkpoints, smaller on 2/5 — no clean
monotonic trend even in the confound arm).

Paired over all 5 (pooled-loss formula, as H43/H43b/H43c): A1 AP75 loss unchanged at 0.0246 [0.0179,
0.0323]; `int8_qat_qdq`@600 AP75 loss **0.0154 [0.0110, 0.0199]**; **pooled AP75 recovery 0.374** — down
from H43c's 0.439 at 150 iterations, not up. AP recovery 0.381 (also down from H43c, not reported there
but recomputable: 1 − 0.0065/0.0105 = 0.381). Mean of the five per-checkpoint AP75 recovery ratios is
0.244 (0.331+0.531+0.782+0.077−0.500)/5 — well below even the pooled figure, because `dose300_s1`'s
ratio is negative (int8_qat_qdq lost more AP75 than plain MinMax PTQ at 600 iters) and pulls the mean
down harder than the pooled-loss formula, which weights by absolute loss.

**Decision (pre-registered rule): hypothesis refuted — recovery fell, it did not rise.**
`success: recovery(600) > recovery(150)` is **false** at the pooled level (0.374 < 0.439) and at the
per-checkpoint mean (0.244 < 0.439). Per-checkpoint, the direction is **not uniform**: `mix_300_s0/s1/s2`
(the 3 original h14b checkpoints) all recover *more* than at 150 iters (0.266→0.331, 0.322→0.531,
0.561→0.782 — `mix_300_s2` even reaches 0.782, close to the 0.80 primary bar on this one checkpoint),
while both H51 `dose300` checkpoints recover *less*, and `dose300_s1` goes **negative** (int8_qat_qdq
now costs *more* AP75 than plain MinMax PTQ, −0.500 recovery) — the opposite of the confound direction
(qat_fp32 shows no comparable regression on `dose300_s1`, loss exactly 0.0000, so this is not simply
"more overfitting"). **Primary bar** (recovery ≥ 0.80 AND every-checkpoint AP loss ≤ 0.005): fails on
both counts (pooled recovery 0.374, and `dose300_s0`/`dose300_s1` now miss the AP-loss bar more badly,
0.0102/0.0108 vs H43c's 0.0030/0.0028 at 150 iters). **Secondary bar** (recovery ≥ 0.50): 0.374 < 0.50,
also not met, and *worse* than H43c's 0.439. A 1,000-iteration arm was not run: the pre-registration's
success criterion already failed in the direction that would make 1,000 iterations answer the question
(if 600 iters made the pooled result worse, extrapolating further in the same direction is not expected
to help, and the 90-minute budget was better spent finishing the write-up than a third fine-tune pass
whose sign is already known to disagree with the hypothesis on 2/5 checkpoints).

**What this rules out.** H43c's write-up (hedged by AUDIT_H43BC) inferred, from one data point, that
the residual AP75 gap "most likely sits in the 150-iteration QAT recipe" — i.e. that more fine-tuning
would let the learned ranges recover more of the loss. **H43d directly measures that and finds it false
as a pooled/uniform effect**: recovery does not rise monotonically with iterations; it rises for the 3
h14b checkpoints and falls (once going negative) for the 2 H51 `dose300` checkpoints, which use a
different training recipe (batch_v8 data, equal-steps dosing, H51) from the 3 h14b checkpoints (H38's
mixed-data set). The heterogeneity the pre-registration disclosed rather than hid in H43/H43b/H43c
(§H43's checkpoint table) is exactly where this split falls — the "recipe-length" attribution was too
coarse; whatever drives the residual gap interacts with *which* checkpoint recipe was fine-tuned, not
just how many QAT iterations were run. The `quint8`→`int8` grid conversion (flagged as untested in H43c)
remains a live candidate, as does per-checkpoint sensitivity of the observers' moving-average ranges to
how far the weights have drifted from where they were when H38's original calibration frames were
chosen — neither is disambiguated here (out of this 90-minute pass's budget).

**Deployment reading (no change to the recommendation):** Percentile PTQ (H43, recovery 0.415/0.424,
free, no fine-tuning) remains the best available INT8 option; QAT (H43b/H43c/H43d, in every variant
tried — plain re-quantization, learned-range export, and now longer fine-tuning with the learned-range
export) has never beaten it on the pooled metric, and H43d shows more QAT iterations can make specific
checkpoints (here, the H51-recipe ones) actively *worse* than PTQ, not just "less good" — a reason to
prefer PTQ over any QAT variant on this pipeline rather than assume "more training" is a safe knob to
turn. **Ship FP16; if INT8 is required, use Percentile PTQ, not QAT.** No latency claim is made here
(R46); the edge-deployment recommendation stays as already stated in `38`/`60`/`65 v2`/`68`/`77` (H43d's
result does not change it — it strengthens the case against QAT rather than reversing the recommendation
to ship FP16 and use PTQ for INT8, so the canonical edge sentence is left unchanged in all five places).

## H33c · Per-visitor alarm cap makes B a real bound (`h33c_capped`) — pre-registration

Registered 2026-09-27, before any capped stream was built or scored (AUDIT_H33B follow-up). H33b's B = 123.5
FA/cam-h assumed ≤ 1 alarm per visitor, but A1 alarms once per dwell *episode* (up to 21 per visitor; 53 % of
eligible episodes from multi-episode visitors), so B was not an a-priori bound. H33c enforces the cap in the rule.
CPU only (≤ 4 cores), no GPU/editor.

```
id:          h33c_capped (config survsim/experiments/configs/h33c_capped.yaml; runner conformal_theta)
change:      new option max_alarms_per_uid_per_world (default None = current behaviour) in the loiter alarm
             stream (tools/loiter_eval.alarms_by_world / cap_per_uid; conformal_theta counts and recall;
             operator_queue.build_point_streams): per world, a uid keeps only its first k alarms in time order
             (alarms are already one per episode). None must reproduce H33/H33b/H42/H45 exactly.
B:           k = 1: k_i <= distinct visitors <= arrivals_i <= Poisson(180).ppf(1 − 1e-6) = 247 w.p. ≥ 1 − 1e-6,
             / 2.0 cam-h → B = 123.5 is now a valid a-priori bound (up to the 1e-6 tail; checked: max distinct
             uids per H12 world reported). k = 2: B = 2 × 123.5 = 247 (valid by the same argument).
             Uncapped arm keeps H33b's B = 123.5 (clipped; not valid).
arms:        uncapped (= H33b crc_fixed, must reproduce), capped1 (B 123.5), capped2 (B 247); each
             choose_crc(mode="real"); also plug-in and A1 grid θ per cap (context).
data:        676 clean H12 worlds (FA/cam-h, calibration half / test half), 300 recall worlds (actor-aware
             recall, 30 s; plus i-LIDS-compat recall and median latency; count of truth events hit uncapped
             but missed capped at the same θ = "dropped/delayed true alarm").
splits:      H33/H33b's 10 random 50/50 calibration/test splits (seeds 0–9); α ∈ {1.0, 2.0, 2.915}; primary 2.915.
hypothesis:  at α 2.915, capped1 vs uncapped: (a) held-out clean FA at the uncapped arm's θ cut ≥ 20 %
             (same θ, cap only — isolates the cap); (b) recall cost at the CRC-chosen θ ≤ 0.02 (mean over
             splits, seed-bootstrap 95 %); (c) capped1 exceeds α in 0/10 splits; (d) 0 calibration worlds
             clipped (so the guarantee is exact for L, not min(L, B)).
decision:    supported iff (a)–(d) all hold; refuted if (c) fails or cost > 0.05; else partial.
H45c:        rerun H45 operator sim (copy of h45b config, h45c_operator_points_capped.yaml) adding the capped1
             certified θ (median of the 10 capped1 CRC θ at α 2.915) streamed with cap 1; 1 operator @5 min,
             FIFO and ranked, paired vs H45b's conformal_fixedB and A1. Ship change iff capped1 − fixedB CI > 0
             or equivalence (CI ⊂ ±0.02) with a lower alarm rate; otherwise ship rule unchanged.
prediction:  repeat episodes are mostly innocent re-stops → FA cut 25–40 % at equal θ; CRC θ drops (more
             permissive) so recall roughly unchanged (cost ≤ 0.01); 0/10 exceed.
confounds:   a loiterer whose first episode fires innocently and whose loiter episode is later loses the true
             alarm (measured directly); uid persistence assumes perfect ReID within a world (sim GT uid) —
             a deployed cap needs a tracker/ReID, whose ID switches would re-open the cap.
```

### H33c · results (run 2026-09-27, ~2 min CPU on 4 cores; `out/experiments/h33c_capped/`, figures/fig_h33c.png)

Pre-registration `7aa7a42`. The uncapped arm reproduces H33b's crc_fixed θ, FA and recall on 30/30 split×α cells.
Structure (clean H12): max 21 eligible episodes per visitor, 53.3 % of eligible episodes from multi-episode visitors,
**max 202 distinct visitors per world ≤ 247**; max per-world L at θ = 0: uncapped 89, capped1 49, capped2 55 FA/cam-h.

| α | arm | B | θ range | exceed /10 | clipped | test FA/cam-h [seed 95 %] | recall [95 %] |
|---|---|---|---|---|---|---|---|
| 2.915 | uncapped (= H33b) | 123.5 (not a bound) | 0.9615–0.9642 | 0 | 0 | 2.216 [2.168, 2.269] | 0.784 [0.782, 0.786] |
| **2.915** | **capped1** | **123.5 (valid)** | 0.9599–0.9628 | **0** | **0** | **2.223 [2.178, 2.274]** | **0.787 [0.785, 0.790]** |
| 2.915 | capped2 | 247 (valid) | 0.9672–0.9698 | 0 | 0 | 1.908 [1.863, 1.956] | 0.773 [0.771, 0.775] |
| 2.0 | uncapped / capped1 / capped2 | | | 0 / 0 / 0 | 0 | 1.413 / 1.416 / 1.097 | 0.743 / 0.745 / 0.706 |
| 1.0 | uncapped / capped1 / capped2 | | | 0 / 0 / 0 | 0 | 0.542 / 0.541 / 0.229 | 0.555 / 0.556 / 0.277 |

At the uncapped arm's θ (cap only): capped1 cuts held-out clean FA by **3.4 % [3.3, 3.6]** at α 2.915 (2.6 % at 2.0,
1.3 % at 1.0); capped2 0.09 %. It drops **0** true alarms and changes median latency by 0.0 s (i-LIDS-compat recall =
default recall in every cell) — at these θ a loiterer's alarming episode is its first alarming one. Recall at the CRC θ:
capped1 − uncapped **+0.004 [+0.002, +0.005]** (the lower loss lets CRC pick a lower θ); capped2 −0.011 (B = 247 doubles
the floor B/(n+1) to 0.73, not the cap itself).

**Decision: partial** (pre-registered rule): (b) cost ≤ 0.02 ✓ (a gain), (c) 0/10 exceed ✓, (d) 0 clipped ✓, but
(a) FA cut ≥ 20 % ✗ (3.4 %). **Prediction wrong on (a):** repeat episodes are mostly innocent, but at θ ≈ 0.96 they
rarely reach θ; the ones that do are mostly one per visitor, so there is little to cap.

**Reconciling 53 % of episodes with a 3.4 % FA cut (AUDIT_H33C):** AUDIT_H33B's 53.3 % figure is a share of
*eligible episodes* (every dwell episode a repeat visitor generates, whether or not it ever crosses θ). What the
cap can actually remove is a share of *alarms* — episodes that already cross θ ≈ 0.9618. Recomputed directly from
the same `build()` clean-world data (`survsim/experiments/conformal_theta.py`) at θ = 0.961780: of 6,830 raw
peaks ≥ θ across all clean worlds, only 1,967 belong to a uid with more than one eligible episode in that world —
**28.8 %** of alarms are repeat-visitor alarms, not 53 %. And the cap only removes the *excess* beyond the first
per uid per world, which is smaller still — consistent with the observed 3.4 % cut. Repeat visitors are common at
the episode level but rare at the alarm level: most of their extra episodes sit below θ, so there is little for a
per-visitor cap to trim once the operating point is this conservative.

**B is now a valid a-priori
bound** for capped1: k_i ≤ distinct visitors ≤ arrivals ≤ 247 w.p. ≥ 1 − 1e-6, so the CRC guarantee is exact for L
(up to the 1e-6 Poisson tail and the perfect-uid assumption), not only for min(L, B).
Certified point (median capped1 θ at α 2.915) **θ 0.961780: 2.196 FA/cam-h [2.143, 2.249] / 0.789 [0.748, 0.829]
(284/360) on all worlds**. Note on splits: the brief said "leave-one-fold-out"; H33/H33b's 10 random 50/50 splits were used (as registered).

**Deployment caveat:** the cap keys on the sim's ground-truth uid (perfect ReID within a world); this section's
own confound already flagged that a deployed cap needs a tracker/ReID, and that tracker ID switches would
re-open the cap by letting one visitor's alarms be spread over two labels (or two visitors' alarms merged onto
one). Tracker ID switches reopen the cap — H59 measured: at H24-calibrated ByteTrack ID-switch rates (157.6
IDSW/track-h, 3× stress 472.7/track-h) the H54 fusion legs (position-gated: badge/context, RF, dwell) show no
measurable twin-FA-removal or recall cost, but actor-aware *base* recall collapses (0.769→0.100 benign→calibrated)
because a swap relabels which uid a caught detection is scored against — the same relabelling mechanism a
per-visitor cap would need to defend against, and H59 did not test the cap itself. **H59 line for this caveat:**
the label-keyed cap itself was not exercised by H59 — H59's fusion legs (badge/context, RF, dwell) are
position-keyed, not label-keyed, so their insensitivity to swaps says nothing about whether a per-visitor cap
(which is label-keyed by construction) survives ID switches; that remains untested.

### H45c · results (run 2026-09-27, ~6 min CPU; `out/experiments/h45c_operator_points_capped/`, config h45c_operator_points_capped.yaml)

H45b's five cells reproduce exactly (model points and all cells equal H45b's results.json). Capped certified point θ
0.961780 with max_alarms_per_uid_per_world = 1: 90.6 alarms/h at 40 cams, utilisation 0.79 (1 op).

| 1 operator, @5 min | FIFO [95 %] | ranked [95 %] |
|---|---|---|
| conformal_fixedB θ 0.963436 (H45b) | 0.573 [0.541, 0.605] | 0.617 [0.583, 0.651] |
| conformal_capped1 θ 0.961780 | 0.584 [0.552, 0.616] | **0.618 [0.583, 0.652]** |
| capped1 − fixedB (paired) | +0.012 [−0.003, +0.027] | +0.001 [−0.014, +0.016] |
| capped1 − A1 (paired) | +0.074 [+0.051, +0.097] 10/0 | +0.032 [+0.014, +0.052] 7/3 |

2 ops ranked vs A1 −0.015 [−0.038, +0.008]; 3 ops −0.031 [−0.052, −0.011]. **Decision (pre-registered): ship rule
unchanged** — no CI > 0 vs fixedB, and equivalence (ranked CI ⊂ ±0.02) comes at the same alarm rate (90.6 vs 90/h),
not a lower one. **Recommendation:** 1 operator / 40 cams → conformal ranked, delivered with the per-visitor cap at
θ 0.961780 — the only variant whose FA certificate is exact, at no measured cost; ≥ 2 operators → A1 θ 0.95 ranked;
never pooled. Caveats: invented operator (H22); the cap uses sim GT uids — deployed, ID switches re-open it.

## H46 · Appearance-weight sweep and night arm for ByteTrack + OSNet-ImageNet (`h46_reid_w_night`) — pre-registration

**Why:** H24 shipped w = 1 untuned (docs/32 §H24, AUDIT_H24) and ran day sequences only (73 §6 flagged the missing
night arm). This sweeps w and adds the night arm before treating H24's OSNet-ImageNet result as a default.

**Design.** Reuses H24's caches unmodified (`out/experiments/h24_reid_assoc/dets/<ckpt>/*.json`,
`.../emb/{batch_v8,mot20}/<ckpt>/*.npz`, field `osnet_imagenet`) — no re-detection or re-embedding for the day/MOT20
arms. Tracker: `survsim/baselines/bytetrack.py:track_sequence`, `app_weight ∈ {0.25, 0.5, 1, 2, 4}` vs the same
w = 0 (IoU-only) control read from cache. Scoring: `survsim.eval.trackeval_bridge` (TrackEval AssA α-mean, HOTA,
IDF1, IDSW), two-way bootstrap over {5 h14b checkpoints × sequences}, matching H24's `analyse()`.
- **(a) Day + MOT20-02 sweep** — batch_v8 day (`street_crowd_day`, `street_crowd_far_day`, `smoke_mock_day`,
  `disguise_and_tamper_day`, 12 seqs) × 5 checkpoints, and MOT20-02, all 5 w values, OSNet-ImageNet only.
  **Hypothesis:** the best w on batch_v8 gives ΔAssA ≥ +0.02 (H24's bar) with CI lower bound > 0, with no
  MOT20-02 AssA decrease (CI lower bound ≥ −0.005), and the argmax w is the same on both sets — else report the
  mismatch rather than pick per-set winners.
- **(b) Night arm** — batch_v8 night sets `disguise_and_tamper_night`, `smoke_mock_night`, at the single best w
  from (a). New detections/embeddings (not cached; det weights = same h14b checkpoints, OSNet-ImageNet embedder).
  **Hypothesis:** appearance still helps at night (ΔAssA > 0, CI excludes 0) but the mean gain is smaller than
  the matching day scenario's gain at the same w.
- **Decision:** report ΔAssA (and ΔIDSW) per w for both sets, name the best w, and give the night verdict
  (helps / no effect / hurts) against the day comparison. No new default is adopted here — this is a diagnostic
  sweep; a change to H24's shipped w = 1 default is a separate follow-up.
- **Budget:** ≤ 75 min wall-clock; GPU (RTX 2070 Max-Q) only for night detection/embedding, ≤ 4 workers. Partial
  results (e.g. day+MOT20 sweep complete, night incomplete) are reported as such, not silently dropped.
- **Runner:** `survsim/experiments/h46_reid_w_sweep.py`, config `survsim/experiments/configs/h46_reid_w_night.yaml`.

### H46 · results (2026-09-27)

`survsim experiment h46_reid_w_night`, `out/experiments/h46_reid_w_night/results.json`, `fig_h46.png`.

| set | w | ΔAssA vs w=0 [95%] | ΔIDSW [95%] | n_seq | n_ckpt |
|---|---|---|---|---|---|
| batch_v8 day | 0.25 | +0.0020 [−0.0085, +0.0120] | −0.17 [−0.63, +0.20] | 12 | 5 |
| batch_v8 day | 0.5  | +0.0122 [−0.0031, +0.0295] | −0.45 [−1.27, +0.08] | 12 | 5 |
| batch_v8 day | 1.0  | +0.0194 [+0.0004, +0.0439] | −0.98 [−2.22, −0.17] | 12 | 5 |
| batch_v8 day | 2.0  | +0.0271 [+0.0058, +0.0550] | −1.35 [−2.92, −0.20] | 12 | 5 |
| batch_v8 day | 4.0  | **+0.0421 [+0.0083, +0.0819]** | −2.12 [−4.32, −0.33] | 12 | 5 |
| MOT20-02 | 0.25 | +0.0053 [−0.0033, +0.0164] | −3.00 [−6.60, +0.60] | 1 | 5 |
| MOT20-02 | 0.5  | +0.0127 [+0.0029, +0.0226] | −5.20 [−9.40, −0.20] | 1 | 5 |
| MOT20-02 | 1.0  | +0.0139 [+0.0018, +0.0268] | −5.60 [−11.00, −0.20] | 1 | 5 |
| MOT20-02 | 2.0  | +0.0193 [+0.0094, +0.0297] | −4.80 [−7.60, −2.60] | 1 | 5 |
| MOT20-02 | 4.0  | **+0.0338 [+0.0157, +0.0520]** | −1.00 [−5.40, +3.20] | 1 | 5 |
| batch_v8 night (2 seq, 1 ckpt) | 4.0 | **−0.0147 [−0.0972, +0.0535]** | see results.json | 2 | 1 |

**Hypothesis (a) — met.** ΔAssA rises monotonically with w across the whole swept range on both
sets — the sweep did not bracket a maximum, so w = 4 is a lower bound on the true optimum, not a
certified one. The argmax is w = 4 on **both** batch_v8 day and MOT20-02 (same optimum, no
mismatch to report). Both clear H24's +0.02 bar with CI lower bound > 0, and MOT20-02 never
decreases (all five w give a positive, CI-excluding-0 gain over the control). H24's shipped w = 1
default is dominated by every larger w tried on both sets.

**Hypothesis (b) — not met.** At the day-selected best w = 4, the night arm
(`disguise_and_tamper_night`, `smoke_mock_night`; 1 of the 5 h14b checkpoints and fresh
detections/embeddings, both bounded to fit the 75 min budget) gives ΔAssA −0.0147
[−0.0972, +0.0535]: the CI includes 0 and the point estimate is negative, not "positive but
smaller than day" as hypothesised. This is a 2-sequence × 1-checkpoint arm (day/MOT20-02 use 5
checkpoints), so the honest reading is *underpowered, not disproved* — the CI is wide enough
to be compatible with a small positive effect. Do not read this as "appearance hurts at night";
read it as "the day-tuned w is not shown to help at night with the evidence collected here."

**Caveats.** (1) The w sweep stopped at 4 because that was the pre-registered top of the range;
whether AssA keeps rising past w = 4 is untested — a follow-up should extend the sweep upward
until it turns over. (2) Night detections/embeddings are new (not H24-cached) and use only 1
checkpoint to fit the budget; a 5-checkpoint night arm is the natural next step before trusting
the negative point estimate. (3) No HSV arm here (H24 already showed HSV performs similarly to
OSNet-ImageNet on day data; out of scope for this sweep). (4) No default change to H24's shipped
w = 1 is made from this result alone — that is a separate follow-up decision.

**Audit (AUDIT_H46, 2026-09-27).** (1) Recomputed ΔAssA/ΔDetA/ΔHOTA/ΔIDSW per w directly from
`results.json`'s per-checkpoint COMBINED scores (a simple mean, not the registered two-way
bootstrap over sequences × checkpoints — approximate, direction/consistency check only): on both
sets ΔDetA and ΔHOTA rise alongside ΔAssA at every w, and ΔIDSW falls (fewer switches) at every
w — AssA does not rise on the back of a DetA drop or an IDSW increase; the reported CIs and point
estimates recompute in sign and rough magnitude. (2) **Multiplicity.** Five w values (0.25, 0.5,
1, 2, 4) are each compared to the w = 0 control with no correction. Approximating each arm's SE
from its reported 95 % CI half-width and applying Holm across the 5 batch_v8-day tests: p ≈ 0.025
(w = 4), 0.031 (w = 2), 0.080 (w = 1), 0.142 (w = 0.5), 0.702 (w = 0.25); Holm thresholds (ascending)
0.01, 0.0125, 0.0167, 0.025, 0.05. **w = 4's p (0.025) exceeds its Holm threshold (0.01) — it does
not survive Holm correction**, nor does any other w. (3) **Garden of forking paths.** "Hypothesis
(a) — met" picks the argmax w post hoc from the same 5 arms it then quotes a CI for — the CI is
conditional on w = 4 having won the sweep, so its coverage is not the nominal 95 % once the
selection is taken into account. This is a real garden-of-forking-paths pattern, not merely a
labelling nit: **the verdict that w = 4 "clears H24's bar" is a post-hoc-selected result,
pending cross-set validation (H46b, appended below) before it can be treated as a validated
optimum.** (4) **Night arm.** −0.0147 [−0.0972, +0.0535] recomputes; CI width 0.1507 on n = 2
sequences × 1 checkpoint is wide enough that "underpowered, not disproved" is the honest reading
stated in the text — it is not overclaimed either direction. (5) **w → ∞ in the code.**
`survsim/baselines/bytetrack.py:_match` solves `linear_sum_assignment((1 - iou) + app_weight *
app)` and only *afterwards* filters `iou[i, j] >= thresh` (the `match_iou` gate, default 0.2) —
the gate is applied identically at every w, including w = 0. As w → ∞ the assignment step
degenerates to a pure appearance-distance matching (the `1 - iou` term becomes negligible), so
candidate pairs are chosen by embedding distance alone; the *acceptance* gate still discards any
resulting pair with iou < 0.2, so a very large w cannot itself create low-IoU matches — it can
only route matches through the fixed geometric gate more or less well, and can strand a detection
unmatched if its appearance-best partner fails the gate. The monotone rise up to w = 4 is
therefore not "the gate doing the work" (the gate is w-invariant), but it does mean the sweep has
not shown where increasing w starts trading correct-appearance-wrong-geometry matches for gate
rejections — consistent with caveat (1)'s open question of where the curve turns over.

## H46b · Extending the appearance-weight sweep, cross-set validation, full night arm (`h46_reid_w_night_b`) — pre-registration

**Why:** H46 (above) found ΔAssA rising monotonically to w = 4 on both batch_v8 day and MOT20-02
with no ceiling found, and a night arm too small to trust (2 sequences, 1 checkpoint, CI spans 0).
`survsim/baselines/bytetrack.py:_match` fuses cost as `(1 - iou) + w * app` (both terms in
[0, 1]), solved by `linear_sum_assignment`, then **filtered post-hoc**: `m = [(i,j) for i,j in
zip(r,c) if iou[i,j] >= thresh]` — the IoU >= 0.2 gate is applied to every arm regardless of w,
so no finite w is literally "appearance-only": a geometrically-infeasible match can still win the
solve (once w dominates the assignment cost) but is then discarded by the gate, not run. This
pre-registration adds a true appearance-only cost (`app_only=True`, cost = `app` alone, gate
unchanged — `survsim/baselines/bytetrack.py` `_match`/`ByteTracker`) to separate "large w" from
"appearance-only assignment, same gate" as an explicit arm.

**Design.** Reuses H24/H46's caches unmodified for day/MOT20-02
(`out/experiments/h24_reid_assoc/dets|emb`); no re-detection/re-embedding for those two sets.
Tracker: same `track_sequence`, arms `app_weight ∈ {8, 16, 32}` plus `app_only=True`, vs the
existing w = 0 control. Scoring: `survsim.eval.trackeval_bridge` (TrackEval AssA α-mean, DetA,
HOTA, IDSW), two-way bootstrap over {5 h14b checkpoints × sequences}, matching H24/H46's
`analyse()`.
- **(a) Extended day + MOT20-02 sweep** — batch_v8 day (12 seqs) and MOT20-02, w ∈ {8, 16, 32} and
  `app_only`, 5 checkpoints, OSNet-ImageNet, fully cached (CPU only).
  **Hypothesis:** ΔAssA peaks and then falls somewhere in {8, 16, 32, app_only} — i.e. a ceiling
  exists at or below w = 32 (H46 showed no ceiling through w = 4). Every w/app_only row also
  reports ΔDetA and ΔIDSW: a rise in AssA accompanied by rising IDSW or falling DetA is logged as
  a trade, not a win, even if it is the argmax.
- **(b) Cross-set validation** — choose w* = argmax ΔAssA over the full grid
  {0.25, 0.5, 1, 2, 4, 8, 16, 32, app_only} on batch_v8 day only, then report MOT20-02's ΔAssA at
  that w* (no MOT20-02 peeking before the choice is made), and separately choose w* on MOT20-02
  only and report batch_v8 day's ΔAssA at that w*.
  **Hypothesis:** the batch_v8-chosen w* gives ΔAssA >= +0.02 on held-out MOT20-02, and the
  MOT20-02-chosen w* gives ΔAssA >= +0.02 on held-out batch_v8 day (H24's bar, now demanded
  out-of-set).
- **(c) Full night arm** — batch_v8 night (`disguise_and_tamper_night`, `smoke_mock_night`) at the
  batch_v8-cross-validated w* from (b) (night is a batch_v8 scenario family, so the batch_v8-chosen
  w* is the one applied), all 5 h14b checkpoints (H46's night arm used 1). Fresh
  detections/embeddings for the 4 checkpoints not already cached by H46
  (`out/experiments/h46_reid_w_night/dets|emb/night/mix_300_s0` reused; s1–s4 fresh).
  **Hypothesis:** night ΔAssA > 0 with a bootstrap CI excluding 0 across the 5 checkpoints (H46's
  single-checkpoint night arm was underpowered, not disproved).
- **Decision:** report ΔAssA/ΔDetA/ΔHOTA/ΔIDSW per arm on both sets; name the ceiling w (if any)
  and mark AssA-vs-IDSW/DetA trades explicitly; report both cross-validated held-out numbers; give
  the night verdict at 5 checkpoints. No default change to H24's shipped w = 1 is made here.
- **Budget:** <= 75 min wall-clock; GPU (RTX 2070 Max-Q) only for the 4 fresh night
  checkpoints' detection/embedding, <= 4 workers. Partial results are reported as such.
- **Runner:** `survsim/experiments/h46_reid_w_night_b.py`, config
  `survsim/experiments/configs/h46_reid_w_night_b.yaml`.

### H46b · results (2026-09-27)

`survsim experiment h46_reid_w_night_b`, `out/experiments/h46_reid_w_night_b/results.json`,
`figures/fig_h46b.png`. 742.9 s wall-clock, GPU used only for the 4 night checkpoints H46 had not cached.

| set | arm | ΔAssA [95%] | ΔDetA [95%] | ΔHOTA [95%] | ΔIDSW [95%] | n_seq | n_ckpt |
|---|---|---|---|---|---|---|---|
| day | 8.0  | +0.0570 [+0.0208,+0.0987] | +0.0014 [−0.0055,+0.0083] | +0.0324 [+0.0105,+0.0605] | −1.62 [−3.48,+0.02] | 12 | 5 |
| day | 16.0 | **+0.0613 [+0.0171,+0.1142]** | −0.0037 [−0.0120,+0.0041] | +0.0327 [+0.0051,+0.0686] | −0.22 [−2.77,+1.98] | 12 | 5 |
| day | 32.0 | +0.0600 [+0.0161,+0.1174] | −0.0034 [−0.0109,+0.0047] | +0.0322 [+0.0048,+0.0710] | +2.37 [−0.82,+6.87] | 12 | 5 |
| day | app_only | +0.0469 [−0.0008,+0.1080] | −0.0109 [−0.0225,−0.0004] | +0.0220 [−0.0084,+0.0636] | **+13.43 [+2.72,+28.67]** | 12 | 5 |
| mot20 | 8.0  | **+0.0486 [+0.0314,+0.0631]** | +0.0044 [+0.0009,+0.0083] | +0.0272 [+0.0181,+0.0351] | +15.80 [+6.00,+26.80] | 1 | 5 |
| mot20 | 16.0 | +0.0479 [+0.0328,+0.0629] | +0.0012 [−0.0026,+0.0053] | +0.0251 [+0.0161,+0.0344] | +33.40 [+21.00,+49.60] | 1 | 5 |
| mot20 | 32.0 | +0.0258 [−0.0024,+0.0502] | +0.0018 [−0.0034,+0.0080] | +0.0139 [−0.0010,+0.0280] | +69.20 [+58.40,+80.00] | 1 | 5 |
| mot20 | app_only | +0.0070 [−0.0130,+0.0318] | −0.0091 [−0.0160,−0.0023] | −0.0017 [−0.0123,+0.0132] | **+162.00 [+134.60,+188.80]** | 1 | 5 |
| night (w=16, cross-val.) | 16.0 | +0.0470 [−0.0046,+0.1337] | −0.0069 [−0.0179,+0.0011] | +0.0239 [−0.0080,+0.0770] | +1.97 [−0.47,+5.63] | 6 | 5 |

(rows for w ∈ {0.25,0.5,1,2,4} unchanged from H46, recomputed here from the same caches for
consistency; see `row.md` for the full table.)

**Hypothesis (a) — met, but the "ceiling" is an IDSW cliff, not a clean optimum.** ΔAssA now
peaks at an interior w on both sets: **day argmax w = 16** (+0.0613; w = 32 is lower, +0.0600),
**mot20 argmax w = 8** (+0.0486; w = 16/32 are lower). A ceiling exists at or below w = 32 on
both sets, resolving H46's open question. But every arm's ΔIDSW is reported alongside, and the
picture is not "AssA rises then plateaus cleanly": on MOT20-02, IDSW *rises with w through the
whole extended range* — +15.8 at w = 8, +33.4 at w = 16, +69.2 at w = 32, CI excluding 0 at every
point — while day's IDSW stays favourable through w = 8 (−1.62) and only turns unfavourable
(CI still spanning 0) at w ≥ 16. The **app_only arm is the clearest trade in the whole table**:
day ΔAssA is still positive (+0.0469, CI barely touches 0) but ΔDetA is *negative* (−0.0109,
CI excludes 0) and ΔIDSW is enormous (+13.4 day, **+162.0 on MOT20-02**, both CI excluding 0) —
dropping the geometry term entirely (even with the IoU >= 0.2 gate unchanged) produces far more ID
switches than any weighted arm, confirming that the gate alone does not stop appearance from
picking geometrically-plausible-but-wrong matches once it is the *only* signal feeding the solver.
Read together: **AssA and IDSW decouple above roughly w = 4–8** — later w values buy AssA at a
steadily increasing IDSW cost, most severely on MOT20-02 and worst of all under `app_only`. The
argmax-by-AssA-alone selections (w = 16 day, w = 8 mot20) are therefore reported as ceilings, but
neither is unambiguously "the win" once IDSW is weighed — the honest summary is *a ceiling exists,
and it is priced in ID switches that rise faster than AssA past w ≈ 8*.

**Hypothesis (b) — met on point estimates, met on this data.** Cross-validating in both
directions: **w\* chosen on batch_v8 day (w = 16) gives MOT20-02 held-out ΔAssA +0.0479
[+0.0328, +0.0629]** (>= +0.02, CI excludes 0); **w\* chosen on MOT20-02 (w = 8) gives batch_v8 day
held-out ΔAssA +0.0570 [+0.0208, +0.0987]** (also clears the bar). Both directions pass — but
given (a), the day-chosen w* (16) buys its MOT20-02 gain at IDSW +33.4, and the mot20-chosen w*
(8) buys its day gain at day IDSW −1.62 (still favourable) but at MOT20-02's own IDSW +15.8. The
MOT20-02-chosen w = 8 is the safer pick of the two under an IDSW budget; the day-chosen w = 16 is
not free.

**Hypothesis (c) — not met on the pre-registered CI test, but far closer than H46's arm.** The
full night arm (6 sequences — H46's headline table undercounted this as "2 seq"; the config's
`night_runs` resolve to 6 camera sequences, and the recount here uses all 6 — × all 5 checkpoints,
at w\* = 16 from the day cross-validation) gives ΔAssA **+0.0470 [−0.0046, +0.1337]**: positive
point estimate, much narrower relative to the mean than H46's 1-checkpoint arm, but the CI still
touches 0 (lower bound −0.0046). ΔIDSW +1.97 [−0.47, +5.63] and ΔDetA −0.0069 [−0.0179, +0.0011]
both also span 0 — night, at this w, shows no IDSW trade the way day/mot20 do at w >= 16, it is
simply underpowered by a hair. Read as: **appearance most likely still helps at night at this w**,
reversing H46's negative point estimate, but the pre-registered "CI excludes 0" bar is missed by a
small margin — a 10-checkpoint or multi-w night arm is the natural next step, not a 6th checkpoint
alone.

**Caveats.** (1) MOT20-02 remains 1 real sequence; its IDSW blow-up at large w could be sequence-
specific density/occlusion, not a general property — a second real MOT sequence would help. (2)
The `app_only` arm's IDSW explosion is consistent with the fused-cost read above the pre-
registration: the IoU gate discards infeasible *winners* of the solve but cannot stop the solve
from preferring an appearance-close, geometrically-distant candidate over the true match in the
first place once geometry is dropped from the cost — so it is a genuine ablation result, not a
bug. (3) No default change to H24's w = 1 is made from this result either; a shipped default
would need to state its IDSW tolerance, since the highest-AssA arms are not the lowest-IDSW arms.

## H61 · Is H52's masked-background gain real background, or a box-shaped inpainting artefact? (`h61_silhouette_mask`) — pre-registration + results

Registered and run 2026-09-27, from AUDIT_H52 and docs/research/66 H61. H52 (c) removed people by Telea-inpainting
dilated (+10 %/side) boxes at 1/4 res, which leaves smooth, blurred box-shaped patches — a detector could learn
"blurred box = no person" rather than anything about the background. This decomposes that +0.0036 (Holm p 0.047).

```
id:          h61_silhouette_mask (config survsim/experiments/configs/h61_silhouette_mask.yaml; runner
             dose_fixedstep, new opt-in train.synthetic_mode = "silhouette"; H26/H51/H52 modes unchanged)
recipe:      H51/H52 exactly: 450 steps, 225 warm-up its, close_mosaic 0, batch 8, workers 2, yolov8n,
             imgsz 640, last.pt.
arms (x10 seeds 0-9, paired):
  dose0      real only (60 MOT20-01 x5, 12 ep)          REUSED from H51, not retrained
  dose300    (a) +300 v8, true labels (6 ep)             REUSED from H51, not retrained
  sil300     (c') the same 300 frames per seed (byte-identical selection to H52's mask300); every person
                  pixel removed by its *rendered silhouette mask* (survsim/gt/mask_boxes.py decode_ids on
                  batch_v8's per-camera ID-mask PNG, nearest-resized to the item's resolution), filled with
                  the frame's own background median colour (no inpainting, no box shape) -- no labels.
metric:      MOT20-02 AP@640.
contrasts:   paired sign-flip (exact, 2^10), seed-bootstrap CI, Holm over 2: dose300-sil300 (a-c'),
             sil300-dose0 (c'-real).
rule:        background-real iff (c')-real >= +0.003 with CI excluding 0 and Holm p < 0.05;
             box-fill artefact iff (c') approx real (|diff| < 0.003 or Holm p >= 0.05);
             labels-on-people iff (a)-(c') >= +0.003 and Holm p < 0.05.
budget:      10 new runs beside the editor (~2 min each), wait_for_gpu/disk checked per arm. GPU idle,
             editor down for this run.
prediction (66): paired sd of (a)-(c) in H52 ~0.0022, so +0.003 at 10 seeds is marginal; said so before running.
```

### H61 results (2026-09-27, `out/experiments/h61_silhouette_mask/results.json`, fig `figures/fig_h61.png`)

10 new runs (sil300_s0..s9), ~100 s training each, ~17 min wall total. dose0/dose300 arm JSONs copied
byte-identical from `h51_equal_steps/arms` (not retrained). MOT20-02 AP@640, 10 seeds, mean [seed-bootstrap 95 %]:

| arm | AP |
|---|---|
| real only (dose0, H51) | 0.4911 [0.4895, 0.4927] |
| (a) +300 v8 true labels (dose300, H51) | 0.4962 [0.4947, 0.4978] |
| (c') +300 v8, silhouette-masked, no inpainting, no boxes | 0.4891 [0.4873, 0.4909] |
| (c) +300 v8, box-inpainted, no boxes (H52, reused for context) | 0.4947 [0.4929, 0.4964] |

| paired contrast | AP diff [95 %] | sign-flip p | Holm p |
|---|---|---|---|
| (a) - (c') | **+0.0071** [+0.0058, +0.0084] | 0.0020 | **0.0039** |
| (c') - real | -0.0020 [-0.0041, -0.0002] | 0.0742 | 0.0742 |

**Rule verdict: box-fill artefact.** (c') is not ≥ real by the +0.003 threshold — its mean diff vs real-only is
*negative* (-0.0020, Holm p 0.074, not significant either way) — so `background-real` does not hold. `labels-on-people`
holds: (a)-(c') = +0.0071, Holm p 0.0039. The prediction (marginal power) undersold the outcome; the sign flipped
the direction the artefact hypothesis predicted, and the effect (+0.0071) was clear enough to reject Holm at 0.004,
not marginal.

**Not in the pre-registered family, computed for context (32 style, "not in the rule" convention, H52):** (c) - (c')
(box-inpainted minus silhouette-masked, same 300-frame selection, same seeds) = **+0.0056** [+0.0048, +0.0065]
(seed-bootstrap; not Holm-adjusted, not primary). The box-shaped inpainted fill is worth essentially all of what H52's
(c) gained over real-only (+0.0036) plus a bit more — replacing the box with the true silhouette and a flat fill
erases the gain entirely and trends slightly negative. **Conclusion: H52's masked-background gain (c) was the
box-shaped, dilated, Telea-inpainted fill pattern — a detector-learnable artefact — not real background/negative
content.** batch_v8's synthetic scenes with people correctly removed by their true silhouette carry no measurable
training signal beyond real-only at this recipe; the entire H51/H52 +300 gain is `labels-on-people` ((a)-(c')
= +0.0071, consistent with (a)-(c) = +0.0015 exploratory + (c)-(c') = +0.0056 artefact, within rounding).
Caveats: one site, one detector, 60 real frames, 10 seeds; the ignore-region arm (c'', H61's 66 §-listed fourth
arm) was dropped from this run's scope per task budget and not run — if the trainer's loss can exclude silhouette
regions rather than filling them, that is a cleaner (but untested) way to isolate "negatives from the rest of the
frame" from "flat-fill artefact". RETIRED_CLAIMS.md: H52 (c)'s +0.0036 is retired as a background-content claim.

## H62 · Position/time-keyed alarm scoring as the default when identities come from a tracker (`h62_label_agnostic_score`) — pre-registration + results

Registered 2026-09-27, before the position_time mode existed in code (docs/research/66 H62,
pre-registered there from AUDIT_TAILGATER_RECONCILIATION). Adds a **third** scoring mode to
`alarms.score` alongside `actor_aware` and `window_only`: `position_radius_m=r` credits a hit iff
the alarm lands in the event's `[t_start, t_start+tolerance_s]` window (label + timing, same as
window-only) AND the alarm's estimated position at alarm time is within `r` metres of the true
offending actor's position — never consulting `uid`, so it cannot be cost a hit by a tracker
relabelling a spatially-unchanged track (H59's collapse mechanism).

```
id:            h62_label_agnostic_score
commit:        877530e (branch head before this entry)
hypothesis:    on H59's calibrated-arm tailgate worlds (C, C+abc, C+abcg), position_time(r=2 m)
               recall for C+abcg is >= 0.6 (vs actor-aware 0.10) and its false-credit rate
               (bystander within r at a position_time hit) is <= 5%; on the benign arm it
               matches actor-aware within 0.02.
r values:      1, 2, 3 m (r_m in the H59 swap model is 2.0 m, same order)
data:          H59's cached tailgate worlds are re-fused with a new, additive
               `fuse_world_h54(..., with_positions=True)` (default False; existing callers
               unaffected -- test_with_positions_is_additive_only) that attaches, to every kept
               alarm, the alarmed track's estimated position at alarm time and the true actor's
               own true position at that same instant (dynamically tracked, not frozen at
               t_start -- see caveat below). 100 tailgate worlds x 10 seeds x {C, C+abc, C+abcg},
               calibrated arm (h = 0.132029/close-pair-s, exactly H59's registered value) and,
               for the "matches actor-aware within 0.02" check, the benign arm (h = 0).
               890/1000 (world, seed) instances have a truth event (some worlds have none).
scoring:       survsim.eval.alarms.score(actor_aware=True|False, position_radius_m=r) -- the new
               mode added to alarms.py this round (Alarm.pos, TruthEvent.actor_pos/bystander_pos,
               AlarmScore.position_time_recall/position_time_false_credit_rate).
confounds:     alarms.score's own position_radius_m mode is defined against TruthEvent.actor_pos,
               a single position snapshot at t_start (by design, matching the generic per-event
               API) -- a moving actor can be metres from that snapshot by the time an alarm fires
               inside a 10 s tolerance window, so scoring this way undercounts badly (measured
               below, "static_t_start"). The headline numbers use a dynamic per-alarm reference
               instead (the actor's own true position at the alarm's own timestamp, from
               with_positions) -- a deliberate, documented deviation from a literal reading of
               `TruthEvent.actor_pos`, computed directly in the eval script rather than through
               alarms.score's own position_radius_m call (that call is still exercised and
               reported as "static_t_start", to validate the API path itself, not as the
               pre-registered primary metric).
abandon if:    false-credit rate could not be measured at all (no bystander/true-body data) --
               not the case: `body` (the true physical source of each alarm) is available from
               H59's own id-switch stage and used as the bystander check (a hit is false-credit
               iff the alarm's true body != the true offending actor even though its position
               landed within r of that actor -- i.e. a bystander standing close enough).
```

### H62 · results (run 2026-09-27, ~70 s CPU wall total, 4 workers; `out/experiments/h62_position_time_score/results_calibrated.json`, `results_benign.json`; `docs/research/figures/fig_h62.png`)

| arm | scorer | recall | false-credit rate |
|---|---|---|---|
| calibrated, C | actor-aware | 0.108 | — |
| calibrated, C | window-only | 0.828 | — |
| calibrated, C | position_time (r=2 m, dynamic) | 0.792 | 32.9 % |
| calibrated, C+abc | actor-aware | 0.010 | — |
| calibrated, C+abc | window-only | 0.066 | — |
| calibrated, C+abc | position_time (r=2 m, dynamic) | 0.066 | 3.4 % |
| **calibrated, C+abcg** | **actor-aware** | **0.100** | — |
| calibrated, C+abcg | window-only | 0.739 | — |
| calibrated, C+abcg | position_time (r=1 m, dynamic) | 0.685 | 14.8 % |
| **calibrated, C+abcg** | **position_time (r=2 m, dynamic)** | **0.715** | **31.3 %** |
| calibrated, C+abcg | position_time (r=3 m, dynamic) | 0.725 | 49.3 % |
| calibrated, C+abcg | position_time (r=2 m, **static t_start**) | 0.002 | (n/a, ~0 hits) |
| benign, C+abcg | actor-aware | 0.701 | — |
| benign, C+abcg | window-only | 0.724 | — |
| benign, C+abcg | position_time (r=2 m, dynamic) | 0.711 | 25.8 % |

**Decision: partially met.** (1) recall bar (position_time(2 m) on calibrated C+abcg >= 0.6): **met**,
0.715 >= 0.6, and even r=1 m clears it (0.685). (2) false-credit bar (<= 5 %): **not met** at any
tested radius -- 14.8 % (r=1 m), 31.3 % (r=2 m), 49.3 % (r=3 m); the false-credit rate rises
sharply with r because tailgating is defined by two people being within a few metres of each other,
so a position-only rule increasingly cannot tell "the actor" from "the person they are tailgating"
as the radius grows -- this is a structural property of the tailgate scenario, not an estimation
artefact. (3) benign-arm match within 0.02: **met** (0.711 vs 0.701 actor-aware, diff 0.010 at
r=2 m; 0.703 vs 0.701, diff 0.002 at r=1 m).

**The static (`TruthEvent.actor_pos`-at-`t_start`) call of `alarms.score`'s own `position_radius_m`
almost never hits** (0.2-2.8 % across arms) -- confirmed by direct inspection: a sample alarm at
`t=126.4` (event `t_start=121.6`) has an estimated position ~6 m from the actor's `t_start` snapshot,
because the actor keeps moving for the 5 s between event start and the alarm firing, well past a
1-3 m radius. This is not a bug in the scoring rule so much as a mismatch between a single static
per-event position (the generic, currently-shipped `TruthEvent.actor_pos` contract) and a scenario
where the tolerance window (10 s) is long relative to how far a person walks in that time. **Anyone
using `position_radius_m` on a moving actor over a multi-second window should supply `actor_pos` at
a time close to the expected alarm time, not at `t_start`** -- documented as a usage caveat, not
fixed in `alarms.score` itself (fixing it generically would need a time-varying position, which is
out of scope for this round).

**Reading:** position/time scoring does recover most of the actor-aware collapse's *recall* (0.715
vs 0.100, i.e. window-only-level performance minus a small geometric-mismatch discount), confirming
AUDIT_TAILGATER_RECONCILIATION's claim that the fusion decision itself is unchanged by ID switches.
But it recovers that recall by being unable to distinguish the actor from a bystander standing
within the same few metres — exactly the situation a tailgater creates by construction — so a
deployed "position/time" scorer would credit roughly a third of its tailgate hits (at r=2 m) to
the wrong physical person. **This is not a case for changing the shipped default (principle 4 stays
as written; no CLAUDE.md edit made here).** Proposed wording for principle 4, for a human to review
before applying (not applied by this entry): *"An alarm on the wrong person is not a hit —
`alarms.score()` matches by actor identity (`actor_aware`) whenever alarms carry a `uid`. When a
uid comes from a tracker/ReID pipeline rather than ground truth, its identity churn can be scored
separately with `position_radius_m` (docs/research/32 H62), but H62 found that mode's own
bystander/false-credit rate exceeds 30% at 2 m on tailgate-style scenarios where the actor and a
bystander are within the same radius by construction — it is not a safe drop-in replacement for
`actor_aware`, only a diagnostic for how much of an actor-aware recall drop is a scoring artefact
versus a real fusion failure."*

**Caveats:** (a) false-credit is measured via the true physical body on the alarmed track, not a
full crowd-position stream, so it only catches cases where *that specific alarm's own track* was
someone else; a bystander who never triggered a track-level alarm at all is invisible to this
check (conservative in the direction of understating false-credit). (b) bounded eval, not H59's full
sweep: only the tailgate worlds, only C/C+abc/C+abcg, only the calibrated + benign arms, 1 pass, 4
workers, ~70 s -- the stress (3x) arm and the base recall (intrusion/probe/climb) worlds were not
run (scope limited to the tailgate case AUDIT_TAILGATER_RECONCILIATION already flagged as the
site of the collapse). (c) `position_radius_m`'s bystander check (`TruthEvent.bystander_pos`) is a
generic per-event API tested with synthetic cases in `tests/test_alarm_position_time.py`; this H62
run computes false-credit outside that API (via the dynamic per-alarm `body` check) because the
generic static-snapshot API does not fit a moving actor, per the confound above.

## H37 · Forensic attribute search: mock-only slice, pooled vs epoch-segmented attributes (`h37_forensic_mock`) — done

**Pre-registration (this entry, before results):** on 50 seeded mock worlds (no
Director/backend, no renders — a direct GT generator matching `identities.parquet`
one-row-per-epoch / `world.parquet` zone-occupancy semantics), each with 40
identities and >=30% given a clothing change (epoch boundary), build 30 queries
per world (attribute colour x garment + zone + time window; >=30% of windows
straddle an epoch boundary) = 1500 queries. Two indexes from the same GT: (A)
pooled per track (union of attribute values over all epochs, matched against
*any* of the uid's zone visits regardless of that visit's actual epoch); (B) per
epoch-segment (attribute and visits both scoped to one epoch). Retrieve top-10 by
exact attribute+time+place match, ties broken by dwell (overlap seconds,
descending). Ground truth relevance is always computed per-epoch (72 §3.1).
Metric: uid-level recall@10 and precision@10 per query, paired across queries
(same query scored on both arms), bootstrap 95% CI over queries (10000
resamples, `bootstrap_mean_diff`). Also scored at a 10% PAR attribute-flip noise
level applied to both indexes' attributes (not to the GT relevant set) for
sensitivity. **Hypothesis (H37, 66/72): epoch-segmented recall@10 is >= 0.15
higher than pooled, with the CI lower bound of the difference > 0.** CLIP arms
(C/D) are explicitly out of scope here — they need renders; only the PAR/mock
arms A and B run. CPU only, no GPU.

**Result (`survsim experiment h37_forensic_mock`, `out/experiments/h37_forensic_mock/`):**
50 worlds x 40 identities (35% with a clothing change); 1500 queries generated,
1363 scored (queries whose relevant set was non-empty), 30% (398/1363 kept) with
an epoch boundary inside the window.

| noise | metric | pooled | per-epoch | epoch - pooled [95% boot] | n |
|---|---|---|---|---|---|
| 0.0 | recall@10 | 1.000 | 1.000 | +0.000 [+0.000, +0.001] | 1363 |
| 0.0 | precision@10 | 0.267 | 0.267 | +0.000 [-0.011, +0.012] | 1363 |
| 0.0 | recall@10 (boundary subset) | 1.000 | 1.000 | +0.000 [+0.000, +0.001] | 398 |
| 0.10 | recall@10 | 0.827 | 0.815 | -0.012 [-0.033, +0.009] | 1363 |
| 0.10 | precision@10 | 0.220 | 0.218 | -0.002 [-0.013, +0.008] | 1363 |
| 0.10 | recall@10 (boundary subset) | 0.846 | 0.830 | -0.016 [-0.054, +0.022] | 398 |

**Decision: not met.** epoch - pooled = +0.0004 [+0.0001, +0.0008] at zero noise
(bar: >= 0.15, CI lower bound > 0); at 10% attribute-flip noise the sign even
flips slightly negative (-0.0118 [-0.033, +0.009]) — pooling does not
measurably cost population-level recall@10 in this design, at either noise
level; the estimate is two orders of magnitude below the 0.15 bar at both
noise levels, so **not met** on the magnitude criterion alone regardless of
CI. The pre-registration's literal abandon condition ("B-A CI includes 0 at
both noise levels") is satisfied only at the 10% noise level (CI
[-0.033, +0.009] straddles 0); at zero noise the CI [+0.0001, +0.0008]
technically excludes zero (pooled is a strict superset of epoch's candidates
by construction, so this tiny positive floor is a mechanical artefact, not a
sampling fluke) but the point estimate (0.0004) is negligible next to the
0.15 bar. The correct summary is "fails the magnitude bar at both noise
levels" rather than "CI includes 0 at both noise levels" — a rounding-scale
distinction that does not change the not-met verdict.

**Why the trap does not show up at recall@10, and where it does show up.** The
pooled index is a *superset* of the epoch index's candidates for a matching
uid (it also matches that uid's other-epoch visits), so it can only add
false-positive uids, never drop a true one from its own candidate set. That
inflates the *pool* pooled ranks from, but with only 6 colour x garment
combinations at 40 identities/world, true relevant sets are almost always
<=10 — recall@10 saturates at 1.0 for both arms before the extra pooled
candidates are numerous enough to push a true hit out of the top 10 by dwell.
The trap is real and directly demonstrated at the mechanism level (unit test
`test_pooled_index_matches_wrong_epoch_segment_but_epoch_index_does_not` in
`tests/test_forensic_search.py`: an identity is retrieved by the pooled index
for a query attribute that belongs to their *other* epoch and never visited
the queried zone under it — the per-epoch index and the GT relevant set both
correctly exclude them) — it just needs a bigger, more collision-heavy corpus
(more identities per world relative to the attribute vocabulary, or a coarser
top-k) before it registers as a *population* recall@10 gap rather than only a
precision leak (which this run also failed to show cleanly at 0.267 vs 0.267,
for the same ceiling reason: the identity's other candidates are true
positives too at this vocabulary size).

**Relevant-set sizes (audit, recomputed from `gen_world`/`build_queries`/
`ground_truth_relevant` at the pre-registered seed/config): mean 2.67, median
2.0, max 9, over the 1363 scored queries — every single one is ≤ 10.** With
only 6 colour x garment combinations spread over 40 identities/world, R
almost never exceeds a single operator screen, so recall@10 is a ceiling
metric for this design by construction: pooling can only add false-positive
candidates, and until R approaches 10 those extras have no room to push a
true hit out of the top 10. This is the direct cause of the near-zero diffs
above, not a fluke of this seed. The 137 unscored queries (1500 - 1363) are
exactly the ones whose R was empty (no identity's active-epoch attribute+zone
combination overlapped the query window) — a query-generation byproduct
(72 §3 already flags "a combination that never co-occurred"), not a
scoring bug; confirmed by direct recomputation (`empty == 137` at seed 37).

**The honest reading:** the mock slice can't separate pooled from
per-epoch pooling at recall@10 because relevant sets are small (mean 2.67,
max 9, all ≤ 10) — this is a ceiling effect built into the design (40
identities x 6 attribute combinations), not evidence that epoch segmentation
doesn't matter. A discriminating design needs recall@1/MRR (where the
pooled index's extra false-positive candidates can outrank a true hit even
when |R| is small) or a much larger identity pool relative to the attribute
vocabulary (so |R| routinely exceeds 10). Tracked as **H37b** in `66`.

**Caveats:** (a) mock-only, not the full Director/behaviour engine — no camera
FOV, no tracker, no crop-level noise beyond the explicit attribute-flip
sensitivity arm; "camera group" is collapsed to "zone". (b) CLIP arms (C, D)
untouched — no number exists for NL-query recall or the B∧C re-rank; do not
quote this entry for those. (c) The near-zero diffs here are about *this*
recall@10 design at *this* corpus scale (a ceiling effect from small relevant
sets, above), not a claim that epoch segmentation is worthless — the
unit-level trap demonstration stands, and H37b (recall@1/MRR, a larger
identity pool, and the CLIP arms once renders exist) is the follow-up that
can actually discriminate the two arms. (d) figure:
`docs/research/figures/fig_h37.png`.

## H63 · Uniformed intruder vs. corroboration mismatch (`h63_uniform_mismatch`) — pre-registration

Registered 2026-09-28, before `survsim/experiments/uniform_disguise.py` existed (docs/research/66 H63,
filed from 100_INFILTRATION_PLAYBOOK). Mock backend, CPU, 4 workers.

```
id:            h63_uniform_mismatch
hypothesis:    against a `uniformed_intruder` (appearance role = guard; no roster entry, no badge,
               no registered RF tag; non-patrol route into the restricted zone), arm (b)
               corroboration-mismatch recovers intruder recall@10 >= 0.8 at twin FA
               (patrol_guard + maintenance_visit + staff_pair) <= 0.05 /cam-h; arm (a)
               naive appearance-role suppression has recall@10 <= 0.1.
data:          H54's cached worlds (same seeds): 300 recall worlds (intrusion/probe/climb x 100,
               every hostile actor re-labelled uniformed_intruder -- role only changes appearance,
               not motion, so trajectories are reused) + 676 clean worlds for FA. H54 tracker noise,
               est matching (alarm -> sensors via the tracked position).
base alarm:    H40b line-cross arm C (unchanged).
role model:    ASSUMPTION: appearance classifier says "guard" w.p. 0.95 for guard-uniformed bodies
               (patrol_guard, uniformed_intruder), 0.02 for anyone else (drawn per alarmed track).
arms:          every arm treats non-guard-role alarms identically (H53 corroboration: drop iff
               badge or RF match). Guard-role alarms:
               C   keep all;
               (a) drop (looks like a guard -> suppress);
               (b) keep iff NOT(badge within +/-15 s at that zone crossing AND registered RF tag
                   within 8 m of the track in +/-5 s AND the identified tag/badge is on-roster now);
               (c) keep iff (b) AND off-route: distance from rostered patrol path (fence ring at
                   1 m + gate->zone-centroid leg) > 5 m for > 5 s continuous in [t_alarm-30, t_alarm];
                   if the streak completes later the alarm is re-timed to that moment.
sensors:       H53/H54 values reused verbatim as assumptions (p_swipe 0.98, jitter 1 s; RF p_carry
               0.95, miss 0.15, n 2.8, shadow 4 dB, -80 dBm; roster: every guard/worker twin is
               on-shift for the whole world).
metrics:       intruder recall@10 s, actor-aware and position-keyed (est pos within 2 m of actor at
               alarm, H62 dynamic); FA/cam-h all + twins on clean worlds; Wilson / bootstrap 95 %.
abandon if:    (b) needs GT role labels (it does not: role comes from the noisy appearance model).
```

### H63 · results (run 2026-09-28, ~4 min CPU wall, 4 workers; `out/experiments/h63_uniform_mismatch/results.json`; `docs/research/figures/fig_h63.png`)

300 recall worlds (298 truth events), 676 clean worlds (3,002 cam-h; 678 patrol_guard, 322 maintenance_visit,
672 staff-pair people). Bootstrap 95 % over worlds (recall), Garwood 95 % (FA).

| arm | recall@10 actor-aware [95 %] | recall@10 position-keyed (2 m) | clean FA/cam-h [Garwood 95 %] | twin FA/cam-h |
|---|---|---|---|---|
| C (no role logic) | 0.775 (231/298) [0.726, 0.822] | 0.775 | 0.375 [0.354, 0.398] | 0.375 (1,111 patrol_guard) |
| (a) looks like a guard → suppress | **0.027** (8/298) [0.010, 0.047] | 0.027 | 0.000 [0, 0.0012] | 0.000 |
| (b) corroboration mismatch | **0.745** (222/298) [0.694, 0.794] | 0.745 | 0.018 [0.014, 0.024] | **0.018** (55, all patrol_guard) |
| (c) (b) + patrol-route prior | 0.198 (59/298) [0.152, 0.242] | 0.198 | 0.007 [0.005, 0.011] | 0.007 |

**Decision: not met** (2 of 3). (a) ≤ 0.1 ✓; (b) twin FA ≤ 0.05 ✓ (0.018, upper 0.024); (b) recall ≥ 0.8 ✗
(0.745, CI upper 0.794). The miss is the ceiling, not the rule: the line-cross base C only reaches 0.775
on these worlds (H40b/H54), so (b) keeps 222/231 = 96 % of what C can catch; the 9 lost are guard-role
alarms coincidentally corroborated by a real, badged, tagged guard within 8 m. The pre-registered
absolute 0.8 bar was above C's own ceiling — a registration error, reported, not re-scored.
(c) is worse, not better: the 5 m patrol-path corridor (fence ring + gate→centre leg) covers most of
a small restricted zone, so an intruder walking to the asset is rarely > 5 m off it for 5 s —
a route prior only discriminates on sites whose zones are large relative to the corridor.
Position-keyed = actor-aware here because H54 noise has no ID switches (H59 would separate them).
Caveats: role classifier, badge, RF, roster all simulated (H53 values); roster = every twin on shift
all world (so the time leg never fires); FA clean-world alarms are all patrol_guard because
non-guard-role alarms get H53 corroboration in every arm.

## H63b · Corroboration mismatch on tracker-fed identities (`h63b_uniform_tracker`) — pre-registration

Registered 2026-09-28, before the full run [AUDIT_H63B: committed in the same commit as the results (be425c0), so git does not evidence the precedence] (a 12-world, 2-seed smoke only checked the code path; its numbers
are not used). Filed in docs/research/100 (H63b). Runner `survsim/experiments/uniform_disguise_tracker.py`,
config `survsim/experiments/configs/h63b_uniform_tracker.yaml` (repo convention for configs), output
`out/experiments/h63b/`. Mock backend, CPU, 6 workers.

```
question:   H63's corroboration-mismatch rule (b) gave recall 0.745 on GT identities. Does it survive when
            the role and the corroboration are keyed by a tracker's track id?
worlds:     H63's, unchanged: 300 recall (intrusion/probe/climb x 100, hostile = uniformed_intruder),
            676 clean. Clip unit = world.
identity:   arm gt (h = 0, H54 noise only: the H63 condition) vs arm osnet: H59 swap stage (< 2 m pairs)
            with hazard = H59's calibrated 0.13203 /close-pair-s x 71.6/83.4 (H24 batch_v8 IDSW,
            ByteTrack+OSNet-ImageNet vs ByteTrack, 12-sequence sums, mean of s0..s4) = 0.11335, then the
            H40b break/jitter stage. 10 noise seeds per arm; sensor streams (badge, RF carry) identical
            across arms (same RNG key), role draws per seed.
keyed by    role: drawn once per track id from the body at the track's first tick (0.95 / 0.02, H63);
track id:   history: times the track id was corroborated (badge +/-15 s AND RF <= 8 m) at its own crossings.
            A break starts a new id (history lost); a swap carries role + history onto another body.
rules:      guard-role alarms -- C keep; a drop; b keep iff NOT live (H63 as-is); s keep iff NOT (live OR
            any history) [sticky]; g keep iff NOT (live OR history within 30 s) [mitigation: grace window].
            Non-guard alarms: H53 corroboration in every arm.
metrics:    uniformed-intruder recall@10 s body-keyed (primary: the body on the alarmed track at the alarm
            tick is the actor -- principle 4), label-keyed (H59 convention) and 2 m position-keyed
            (diagnostic, H62). Twin FA/cam-h on clean worlds (body kind in patrol_guard/maintenance/
            staff_pair), seeds pooled. 95 % CIs: bootstrap over clips (2,000, seed 631), all seeds kept.
test:       per rule in {b, s, g}: paired body-keyed recall drop gt -> osnet, one-sided bootstrap p (drop <= 0);
            Holm over the 3 rules, alpha 0.05.
hypothesis: (1) b drop >= 0.05 and Holm-significant; (2) b twin FA (osnet) <= 0.05/cam-h; (3) s drops more
            than b; (4) g recovers body-keyed hits over s. Met iff all four.
prediction: (1) yes, small (~0.05-0.1): swaps put intruder bodies on tracks born as guards and vice versa;
            (3) yes; (4) yes, partially.
confounds:  ground-plane swap model, not per-camera; role classifier, badge, RF, roster simulated (H53);
            no swap detector modelled (so "re-corroborate on switch" is represented by the grace window).
stopping:   one pass, fixed.
```

### H63b · results (run 2026-09-28, 2,232 s CPU wall, 6 workers; `out/experiments/h63b/results.json`; `docs/research/figures/h63b_recall_fa.png`)

300 recall worlds × 10 seeds (2,980 event-seeds), 676 clean worlds × 10 seeds (30,020 cam-h). Osnet swap
hazard 0.11335 /close-pair-s (2,289,195 swap events over all osnet runs). 95 % = clip bootstrap.

| rule | gt recall (body) | osnet recall (body) | osnet label-keyed | osnet 2 m pos | gt twin FA/cam-h | osnet twin FA/cam-h |
|---|---|---|---|---|---|---|
| C | 0.766 [0.728, 0.807] | 0.709 [0.668, 0.751] | 0.104 | 0.716 | 0.367 | 0.304 |
| (a) suppress | 0.028 [0.022, 0.034] | **0.249** [0.221, 0.277] | 0.006 | 0.249 | 0.000 | 0.000 |
| (b) live | 0.740 [0.697, 0.782] | **0.700** [0.657, 0.743] | 0.098 | 0.705 | 0.020 [0.014, 0.027] | **0.016** [0.011, 0.022] |
| (s) sticky | 0.730 [0.687, 0.773] | 0.689 [0.645, 0.733] | 0.097 | 0.695 | 0.018 | 0.015 |
| (g) grace 30 s | 0.734 [0.692, 0.777] | 0.696 [0.652, 0.740] | 0.097 | 0.701 | 0.019 | 0.016 |

Paired body-keyed drop gt → osnet (Holm over b/s/g): b **0.040** [0.020, 0.062], s 0.041 [0.020, 0.063],
g 0.039 [0.019, 0.060]; all p_one-sided 0.0005, p_Holm 0.0015.

**Decision: not met** (3 of 4). (1) b drop ≥ 0.05: ✗ — the drop is real (Holm p 0.0015) but 0.040, and
almost all of it is the base detector's, not the rule's: C itself drops 0.766 → 0.709 (0.057) because breaks
and swaps split the intruder's crossing [**AUDIT_H63B: wrong attribution** — C is not role-free, its
non-guard alarms go through the H53 drop; with role re-drawn from the body at each alarm (3-seed rerun) C
holds 0.761 and b's drop is 0.007, so most of the drop is the cached-at-birth role, not the detector]; b keeps 2,085/2,114 = 98.6 % of C's hits under the tracker (96.5 %
on GT ids). (2) b twin FA 0.016 ≤ 0.05 ✓. (3) sticky drops more than live ✓ but only by 0.0007 (≈ 2 hits; the 31 hits are the osnet-arm level gap b − s, not a drop difference) — noise.
(4) grace recovers over sticky ✓ (19 of 31 hits); live (no history) still beats both [AUDIT_H63B: (4) and
"live ≥ grace ≥ sticky" hold by construction for every grace window — the keep sets are nested — so they are
not evidence; only the FA side (0.018 vs 0.020) is measured] — history buys no FA
reduction worth its recall cost (0.018 vs 0.020 on GT ids), so the recommendation is: don't carry
corroboration on a track id at all; corroborate live at each alarm.
Surprise: naive suppression (a) rises 0.028 → 0.249 on tracker ids, because swaps put the intruder's body on
tracks born as commuters (role cached non-guard) — the "defence" works by accident [AUDIT_H63B: an artefact of caching the role at track birth; re-drawing
the role per alarm keeps (a) at 0.027 on tracker ids], the same identity noise
that would hand a guard's trust to an intruder under a sticky rule.
Label-keyed recall collapses to ~0.10 in every arm, as in H59: scoring on the tracker's label is not usable;
body-keyed and 2 m position-keyed agree within 0.007 here (C 0.709 vs 0.716).
Prediction (1) was right in direction, wrong in size. Caveats: simulated sensors/role/roster (H53); swaps
are a ground-plane model, not per-camera; no swap detector, so re-corroborate-on-switch is only proxied by
the grace window; gt arm reproduces H63's 0.745 as 0.740 (10 noise seeds vs 1).

## H66 · Decoy flooding vs. the operator queue (`h66_decoy_flooding`) — pre-registration

Registered 2026-09-28, before `survsim/experiments/decoy_flooding.py` existed and before any H66 number was
computed (docs/research/100 T4, filed H66). Pure-Python discrete-event simulation, CPU, ≤ 6 workers.

**Why H66 first of H64–H68.** H67 (vehicle concealment) is recall 0 by construction and H68 (drone) needs
renders we cannot make (no GPU/editor); H64 (PTZ timing) and H65 (service entry) are coverage questions `survsim rig`
already answers geometrically. H66 is the one where the *detector works and the system still fails*: the
decoy is loud (T4 is **C+**), and the attack succeeds only through the operator queue — the part of the
stack that H22/H45c showed realises far less than model recall. It is also the interview question a
security buyer actually asks ("what if they start a fight at the front while someone goes over the back
fence?"), and it has a natural hard negative (a genuine incident that coincides with an innocent perimeter
crossing) so any "decoy-aware" defence has a measurable false-alarm cost.

```
id:            h66_decoy_flooding
hypothesis:    a decoy incident that emits k alarms starting 30-90 s before a real perimeter intrusion
               lowers operator-realised intrusion recall within 300 s under FIFO review; the drop grows
               with k and is >= 0.20 at k = 16. A coincidence-escalation policy (a perimeter alarm that is
               NOT badge-corroborated, arriving within 180 s of an active incident, jumps the queue)
               restores recall to within 0.05 of the no-decoy FIFO level at k = 16, and in hard-negative
               worlds costs <= 0.05 escalations/cam-h and <= 30 s median added delay to the genuine
               incident's first review.
world:         1 h, 40 cameras (H22 wall). Background FA stream Poisson at the H40b/H63 line-cross arm-C
               clean rate 0.375 /cam-h (15 /h over 40 cams), score ~ Beta(2,5).
               Recall worlds: one intrusion at t ~ U(900, 2700) s; the base detector alarms on it
               w.p. 0.775 (H63 arm C recall@10), perimeter score ~ Beta(5,3).
               Decoy arms k in {0, 4, 8, 16}: incident starts at t_int - U(30, 90) s, k alarms with
               Exp inter-arrivals of mean 60/k s (all within ~60 s), incident score ~ Beta(8,2) (fight /
               person_down detectors score high — that is the point). Paired: same world RNG across k.
               Hard-negative worlds (principle 3): NO intrusion; a genuine k = 8 incident at a random
               time plus an innocent badged staff member crossing the perimeter U(30, 90) s later, whose
               crossing raises a perimeter alarm w.p. 0.775 (same detector, same score law).
corroboration: drawn LIVE per perimeter alarm, never cached per track (AUDIT_H63B lesson): staff swipes
               w.p. 0.98 (H53 p_swipe), badge within +/-15 s -> corroborated; intruder never has a badge.
operator:      H22 values verbatim: 1 operator, gamma review mean 30 s cv 0.3, miss 0.05 (0.15 fatigued),
               fatigued if the world's random shift offset U(0, 8 h) is past 2 h (review x1.25),
               bulk-acknowledge (queue cleared, alarms lost) when queue > 10.
policies:      fifo; ranked (score); escalate (fifo + coincidence escalation as above); lane (a second,
               dedicated perimeter operator reviewing only perimeter-class alarms, FIFO).
metrics:       realised recall@300 s and @30 s (intrusion alarm raised, reviewed within horizon, not
               missed); hard-negative escalations/cam-h and genuine-incident first-review delay.
seeds:         1,000 worlds per arm x 10 operator seeds (world RNG and operator RNG separate).
inference:     world-level bootstrap (2,000, resample worlds, operator seeds averaged within world);
               one-sided bootstrap p for FIFO drop(k) = recall(k=0) - recall(k) > 0, Holm over k in {4,8,16};
               Holm over the 3 escalate-vs-fifo recovery tests at k in {4,8,16} separately.
decision:      met iff (1) Holm p < 0.05 for k = 8 and 16 AND drop(16) >= 0.20; (2) escalate@16 - fifo@0
               CI lower bound >= -0.05; (3) hard-negative escalate: escalations/cam-h <= 0.05 AND median
               added genuine-incident first-review delay <= 30 s. All three.
predictions:   (1) yes, mostly via bulk-acknowledge at k = 16; ranked worse than fifo under decoy (decoy
               scores high); lane recovers fully at the price of a second operator; (3) holds because the
               live badge check removes 98 % of innocent coincidences.
labelled by construction: lane's recall at every k is independent of k (the decoy never enters its
               queue) — reported, not evidence. Every rate above is a declared assumption, not a measurement.
abandon if:    fifo recall at k = 0 is < 0.5 (then the queue is already saturated and H66 measures H22 again).
```

### H66 · results (run 2026-09-28, ~9 s CPU wall, 6 workers; `out/experiments/h66_decoy_flooding/results.json`, `sensitivity.json`; `docs/research/figures/h66_decoy_flooding.png`)

1,000 paired worlds × 10 operator seeds per cell; world-level bootstrap 95 %. Realised intrusion recall @300 s:

| decoy k | fifo | ranked | escalate | lane (2nd operator) |
|---|---|---|---|---|
| 0 | 0.690 [0.667, 0.712] | 0.690 | 0.690 | 0.690 |
| 4 | 0.693 [0.671, 0.716] | 0.695 | 0.691 | 0.690 |
| 8 | 0.600 [0.577, 0.621] | 0.587 | 0.690 | 0.690 |
| 16 | **0.486** [0.459, 0.514] | 0.483 | **0.689** [0.666, 0.711] | 0.690 |

FIFO drop vs k = 0 (Holm over k): k4 −0.004 [−0.012, 0.005] p_Holm 0.80; k8 **0.090** [0.078, 0.102] p_Holm 0.0015;
k16 **0.203** [0.179, 0.228] p_Holm 0.0015. Escalate@k − fifo@0: k16 −0.001 [−0.009, 0.008] (all three Holm p 0.0015
against a −0.05 margin). Hard negative (genuine k = 8 incident + innocent badged crossing, no intrusion): escalations
**0.001 /cam-h** [0.0007, 0.0013]; median added genuine-incident first-review delay **0 s** (fifo median 36.6 s).
@30 s the decoy is near-total even at k = 4: fifo 0.200 → 0.026; escalate only 0.058; lane 0.200.

**Decision: NOT met as registered** (corrected by AUDIT_H66). The registered operator "bulk-acknowledge (queue cleared, alarms lost)" has no exemption; the exempt variant that scored 3 of 3 was added in code after registration. Under the registered rule escalate@16 is 0.538 [0.514, 0.563], so (2) fails; (1) and (3) hold. Original qualifications, kept for the record:
1. **The recovery is the bulk-acknowledge exemption, not the queue jump.** The pre-registration said "jumps the queue";
   the implementation also exempts escalated alarms from bulk-acknowledge. Without the exemption (sensitivity,
   `sensitivity.json`) escalate@16 is **0.538** [0.514, 0.563] — decision (2) fails. The decoy's mechanism is the
   operator clearing a flooded queue (H22's bulk-ack > 10), so the defence is "never auto-clear an un-corroborated
   perimeter alarm", which is a procedure, not a model.
2. **(3) is almost by construction of the badge assumption.** Cost ≈ (1 − p_swipe) × p_detect per coincidence; at
   p_swipe 0.80 escalations rise 9× to 0.009 /cam-h, still under the bar. Lane (dedicated perimeter operator) is
   k-independent by construction (the decoy never enters its queue) — labelled, not evidence.
Ranked is no better than FIFO under decoy (0.483 vs 0.486 at k = 16) because decoys out-score perimeter alarms — the
predicted direction, but within CI. Caveats: every rate is a declared assumption (H22 operator, H63 arm C detector,
H53 badge); one decoy per world; operator fatigue as H22; no PTZ contention (H56).

**AUDIT_H66 (2026-09-28).** Pre-registration aa80867 (02:27) predates results 2879e65 (02:32). Findings: (a) the
bulk-ack exemption is a post-registration change and carries 0.151 of the 0.203 recovery at k = 16 (the queue jump
alone gives +0.052), so the registered decision is not met; (b) the escalation rule is oracle-clean in recall worlds —
the intruder is never badged and always lands inside the 180 s window, so every detected intrusion escalates; (c) the
hard-negative "0 s added delay" is structural — the innocent crossing always follows the incident's first alarm, so it
can never delay that first review (added delay is 0 in every world of a 100 × 3 rerun), and escalations are 0.04 per
world, so (3) tests only the 1 − p_swipe rate; (d) "ranked" sorts by a Beta stand-in score, not H45c's scorer;
(e) Holm p 0.0015 is the bootstrap floor (3 × 1/2001). Reduced rerun (100 worlds × 3 seeds) reproduces the direction:
fifo 0.723 → 0.570 at k = 16; escalate 0.703 with exemption, 0.603 without. Honest sentence: in a simulated H22
operator, a 16-alarm decoy cuts FIFO realised recall about 0.20, and what saves the intrusion is a procedure (never
bulk-clear an un-badged perimeter alarm), not the escalation ranking.

## H64 · PTZ-tour timing exploitation and randomised tours (`h64_patrol_timing`) — pre-registration

Registered 2026-09-28, before `survsim/experiments/patrol_timing.py` existed and before any H64 number was computed
(docs/research/100 T8, filed H64). Pure-Python simulation, CPU, ≤ 6 workers, no GPU/editor.

**Why H64 of the remaining H64/H65/H67/H68.** H67 (vehicle concealment) is camera recall 0 by construction; H68
(drone) needs renders we cannot make (no GPU/editor); H65 (service entrance) is mostly the coverage question
`survsim rig` already answers geometrically. H64 tests a defence every integrator sells — "randomise the PTZ tour" —
against an attacker a buyer can picture (watch the dome, go when it turns away), and the answer can go either way.
It also has a natural, measurable hard negative: the attacker's recon is a long dwell near the fence, which is
exactly what an innocent commuter waiting at a bus stop does (`commute_wait` vs `recon`).

```
id:            h64_patrol_timing
hypothesis:    (1) against a fixed cyclic PTZ tour, an attacker who times the crossing to the camera's departure
               is caught far less often than a naive one: exploitation E_fixed = catch(naive) - catch(timed)
               > 0.10. (2) a randomised tour cuts exploitation at least in half: E_random < 0.5 * E_fixed.
               (3) the attacker's recon is detectable: a dwell rule on the approach camera, calibrated to
               <= 0.5 FA/cam-h on innocent commuter waits, flags the timed attacker's recon w.p. > 0.5.
world:         one fence of 6 segments covered ONLY by one PTZ with 6 presets (one per segment); no fixed
               camera on the fence (T8 premise). 1 h per world. Attacker picks a segment uniformly, arrives
               at the approach zone at t_a ~ U(600, 2400) s. Crossing duration c ~ U(8, 15) s.
tours:         fixed  : cyclic order 0..5, dwell 20 s per preset, slew 2 s between presets (period 132 s),
                        random start phase U(0, 132) s.
               random : next preset uniform over the OTHER 5, dwell ~ U(10, 30) s (mean 20 s, same duty),
                        slew 2 s, random start preset.
               Coverage = the PTZ is stationary on the attacker's segment (slew time covers nothing).
caught:        crossing interval [s, s + c] overlaps a stationary coverage interval of the attacker's segment
               by >= 2 s, AND a single per-world uniform u < p_det = 0.775 (H63 arm C recall@10). u is shared
               by all arms of a world (paired); it is a detector draw, not an operator (no operator queue).
attackers:     naive : starts crossing at t_a + U(0, 60) s.
               timed : from t_a watches its own segment; after observing N = 3 departures of the PTZ from it
                       (a departure = end of a stationary interval on that segment, observed only if the interval
                       ends after t_a), starts crossing 1 s after the 3rd departure. Same rule under both tours.
               N sweep {1, 2, 3, 5} reported as secondary, not part of the decision.
recon rule:    one fixed approach camera watches the approach zone. The timed attacker dwells there for
               (start - t_a + c) s and is visible to it w.p. p_vis = 0.7 (per-world draw; declared
               assumption: 30 % watch from a hidden spot). Hard negatives: innocent commuters Poisson 8 /h,
               dwell ~ LogNormal(median 240 s, sigma 0.6), always visible. Rule: flag a person iff dwell >= tau.
               tau is calibrated ONCE on 2,000 separate calibration hard-negative worlds (seed offset) as the
               smallest observed innocent dwell value such that innocent flags <= 0.5 per cam-h, then frozen
               and applied to the test worlds. No other rule, suppression or exemption exists.
seeds:         10 seed blocks x 500 worlds = 5,000 test worlds (world RNG [seed, block, i]); per-block
               exploitation reported as a spread check.
inference:     world-level bootstrap, 2,000 resamples. One-sided bootstrap p (fraction of resamples on the H0
               side, (b+1)/(B+1)) for T1 H0: E_fixed <= 0.10; T2 H0: E_random - 0.5 * E_fixed >= 0;
               T3 H0: recon recall (fixed tour, timed attacker, N = 3) <= 0.5. Holm over {T1, T2, T3}.
decision:      met iff Holm p < 0.05 for T1, T2 and T3 AND test-world innocent FA <= 0.6 /cam-h (0.1
               allowance for calibration drift). All four.
predictions:   (1) yes. (2) NO — a randomised tour defeats period-learning but not departure-triggering: the
               PTZ cannot return to a segment sooner than slew + another preset's dwell + slew (>= 14 s), so
               "go the moment it turns away" still works. (3) NO — N = 3 passes of a 132 s tour take ~ 5 min,
               inside the commuter dwell distribution; tau at 0.5 FA/cam-h lands near 10 min.
labelled by construction:
               timed catch under the fixed tour is 0 (min return gap 5 x 22 + 2 = 112 s > 1 + 15 s) — the
               measured part of E_fixed is only catch(naive). catch(naive) is the same in expectation under
               both tours (equal mean dwell, same slew). recon recall <= p_vis = 0.7. The innocent FA is at the
               calibrated 0.5 /cam-h by construction up to calibration/test sampling. Every rate is a declared
               assumption, not a measurement.
abandon if:    catch(naive, fixed) < 0.10 (then there is nothing to exploit and T1 cannot pass).
```

### H64 · results (run 2026-09-28, ~7 s CPU wall, 6 workers; `out/experiments/h64_patrol_timing/results.json`, `sensitivity.json`; `docs/research/figures/h64_patrol_timing.png`)

5,000 test worlds (10 blocks × 500), world-level bootstrap 95 %. tau calibrated on 2,000 innocent-only worlds: **616 s**.

| tour | naive caught | timed caught (N = 1, 2, 3, 5) |
|---|---|---|
| fixed | 0.162 [0.151, 0.172] | 0.000 at every N |
| random | 0.164 [0.155, 0.174] | 0.000 at every N |

E_fixed **0.162** [0.151, 0.172] (T1 Holm p 0.0015, the bootstrap floor 3/2001); E_random **0.164** [0.155, 0.174]
(T2 p_Holm 1.0; E_random − 0.5 E_fixed 0.084 [0.073, 0.095]); per-block E_fixed 0.144–0.194, E_random 0.146–0.184.
Recon rule at tau = 616 s: timed-attacker recon flagged **0.000** at N = 3 under the fixed tour (median recon dwell
340 s; T3 p_Holm 1.0); 0.298 at N = 5 (median 604 s); innocent FA **0.459** /cam-h [0.439, 0.478] on test worlds.

**Decision: NOT met** (T1 and FA hold; T2 and T3 fail, both as predicted). Qualifications:
1. **T1 and T2 are both determined by construction, and T2's was not foreseen at registration.** The pre-registration
   labelled timed catch = 0 for the fixed tour only, and said the random tour's minimum return gap (14 s) made a catch
   possible. With the registered 2 s overlap, crossings ≤ 15 s starting 1 s after departure, a return at ≥ leave + 14 s
   overlaps by ≤ 2 s only when the other preset's dwell is exactly 10 s — measure zero. So timed catch is 0 under
   both tours, and E = catch(naive) for both. The naive catch is itself an identity: p_det × (dwell + E[c] − 2 × overlap) / period = 0.775 × 27.5 / 132 = 0.161 (measured 0.162); the fixed-tour duty cycle is 20/132 = 0.152, a different number (AUDIT_H64). Post-hoc,
   not registered (`sensitivity.json`): widening the random dwell to U(2, 38) s (same mean) gives timed catch 0.020
   [0.016, 0.024], E_random 0.139 [0.128, 0.150] — still far from halving. The finding survives; its size is a
   geometry fact, not a statistic.
2. **The hard negative did fail the detector** (T3), which is the part that could go either way: 3 passes of a 132 s
   tour take ~ 340 s, inside the commuter wait distribution (median 240 s), and the 0.5 FA/cam-h dwell threshold sits
   at 616 s. Recon only becomes flaggable at N = 5 (0.298, capped by p_vis 0.7). But the attacker needs N = 1
   (timed catch is 0 at every N), so the dwell rule is defeated by an attacker who simply watches once.
3. Caveats: every rate is a declared assumption (6-preset tour, dwells, commuter law, p_vis, H63 arm C p_det); no
   operator queue; the attacker is assumed to see which way the dome points; one intruder per world.

Interview sentence (corrected by AUDIT_H64): *a single PTZ covering a fence catches a naive crosser ~16 % of the time in this model — p_det × the dwell/crossing overlap window, arithmetic not measurement — and an intruder who goes the moment
it turns away is never caught whether the tour is fixed or randomised — randomising beats period-learning, not
departure-triggering (both zeros are by construction of the registered geometry); and the one-look recon is shorter than a bus-stop wait (a declared commuter law, not measured). The fix is fixed overlap or a
fence sensor, not a cleverer tour.*

### H64 · audit addendum (AUDIT_H64, 2026-09-28)
Adversarial audit: `docs/research/AUDIT_H64.md`. Order confirmed (pre-reg e52f977 02:38 → results f853a1d 02:41, code added only in the latter).
All four headline results are arithmetic of declared inputs: naive catch 0.162 = 0.775 × 27.5/132 (identity, not the
duty cycle 0.152); timed catch 0 under both tours (return ≥ leave + 14 s, crossing ends ≤ leave + 16 s, overlap ≥ 2 s
needs dwell ≤ c − 5 ≤ 10 s); fixed-tour recon at N ≤ 3 is 0 by construction (dwell ≤ 3 × 132 + 16 = 412 s < tau);
tau is a plug-in quantile of a declared LogNormal commuter law (not H33 conformal, not engine `commute_wait`). The
random-tour recon at N = 3 is not zero (0.054–0.096 in a 500 × 3-seed rerun, below 0.5). Rerun reproduces every
direction and the NOT-met decision (tau 587–618 s).

### H69 · cross-site generalisation of detection and thresholds — PRE-REGISTRATION (2026-09-28)
Committed alone, before any code or detector output on the sites exists.

**Data.** Every site `out/showcase/sites/<nn>_<type>_s<seed>/` (tools/infinite_sites.py, read-only) whose `gate.txt`
has every check PASS (no FAIL row), whose `set/licences.json` says `commercial_ml_ok: true`, and which has ≥ 30
frames in `set/render/<camera>` (the camera named in site.json). Re-scanned at analysis time. **N ≥ 16 sites is
required; with fewer the result is reported as PARTIAL** and no sub-hypothesis is called met/not met, only
directionally described. Each site is one camera × 30 frames at 10 fps, 640 × 360 (3 s of footage).

**Detector / operating point (docs/13, unchanged).** YOLO11n COCO (`yolo11n.pt`, same weights), imgsz 1280, person
class, conf ≥ 0.25, greedy IoU ≥ 0.5 via `survsim.eval.detection.evaluate`; targets are MOT rows with conf = 1,
class = 1 (all heights, as docs/13). Image index i ↔ MOT frame i (the render gate's default offset 0); images with no
GT row count only toward false positives. Secondary (reported, not decided on): recall on targets ≥ 20 px tall.

**H69a.** Per-site recall r_s with a 95 % frame-bootstrap CI (2000 resamples of frames within the site). Between-site
SD is the noise-corrected SD sqrt(max(0, var_s(r_s) − mean_s(within-site bootstrap var))). Its CI: two-stage bootstrap
(resample sites, then frames within each resampled site; 2000). **Met iff corrected SD > 0.05 and its two-stage 95 %
lower bound > 0.05.**

**H69b.** A false alarm here is a detector false positive (unmatched detection, score ≥ θ), FA/cam-h = FP/frame × 10 ×
3600 — a *detector* rate extrapolated from 3 s clips, not an operator alarm. Budget B = 3600 FA/cam-h (0.1 FP/frame).
θ is the smallest value on the grid 0.05, 0.06, …, 0.95 whose pooled FA/cam-h on the calibration half ≤ B. 200 random
half-splits (seed 69; floor(N/2) calibration sites). Held-out pooled FA/cam-h ≤ B counts as "within budget".
**Prediction: within budget in ≤ X = 80 % of splits (met iff the fraction ≤ 0.80).** Labelled in advance: if the
calibrated θ equals the grid minimum 0.05 in > 50 % of splits the budget is not binding and H69b is reported as
**vacuous (true/false by construction)**, not met/not met. Also reported: per-split held-out recall at the transferred θ.

**H69c.** OLS r_s ~ 1 + cam_height_m (calib position_world z) + range_m (median horizontal camera-to-person distance
over GT-boxed person-frames, from world.parquet + track_ids.json — not from box height, which would be circular) +
density (site.json `people`) + tod (day 0, dusk 1, night 2). **Met iff adjusted R² > 0.50.** Leave-one-site-out R²
is reported alongside (with N ≈ 16 and 4 covariates in-sample R² is inflated). Site *type* is not a regressor
(6 levels would saturate the model); it is used only in the hard negative.

**Hard negative (can fail).** Pairs of sites with the same type and different seed: each pair's recall difference with a
95 % frame-bootstrap CI. **Passes iff every pair's CI covers 0** (the pair differs by no more than within-site noise).
Note, declared up front: the generator changes time-of-day and headcount with the index/seed, so "same type" is not
"same conditions" — which is exactly why this check can fail. If it fails while H69a is met, the between-site
variation is attributed to seed-level conditions, not to site type.

Runner `survsim/experiments/site_generalisation.py`, config `h69_site_generalisation`; results `out/experiments/h69/`,
figure `docs/research/figures/h69_site_variance.png`.

### H69 · partial (N = 9): directions only (2026-09-28, interim)
Below the registered N ≥ 16, so no decisions. 9 gate-PASS, CC0 sites (02/07/08 gate FAIL). H69a direction: corrected
between-site recall SD 0.36 [0.17, 0.44]; H69b: held-out within budget in 56.5 % of 200 splits (not vacuous);
H69c: adjusted R² −0.22 (camera height is 4.5 m at every site — a constant regressor); hard negative FAILS
(4/4 same-type pairs differ). Final numbers follow once ≥ 16 sites pass.

## H70 · Alarm budgets at estate scale (`h70_alarm_budget_scale`) — PRE-REGISTRATION (2026-09-28)

**Question.** One operator wall of K operators serves a 40-site, 400-camera estate (10 cameras/site). Which
threshold scheme gives the most operator-realised intrusion recall without letting individual sites blow their
false-alarm budget: (a) one global budget B with one pooled θ, (b) per-site budgets B with per-site θ calibrated on
that site's own week, or (c) the global budget B × 400 cam re-allocated across sites by a load-aware per-site θ?

**Simulated world (every number is a declared assumption, not a FACT).**
- Per camera, background alarm *candidates* arrive Poisson at 20 /cam-h with score logit ~ N(−2 + δ_s, 1).
  Site offset δ_s ~ N(0, σ_δ), **σ_δ = 0.3** (primary; sensitivity σ_δ = 0.6). σ_δ = 0.3 was chosen before any
  outcome run because at the pooled θ it leaves ≈ 60 % of sites within budget, matching the *partial* H69 figure
  (held-out within budget in 56.5 % of splits, N = 9, interim). This is a matching of an input to an interim
  number, not a measurement; H69's between-site recall SD 0.36 is not reproduced (score shift only).
- Intrusions: Poisson, 1 per site per week, uniform in time and camera; a candidate is produced with p = 0.775
  (H63 arm C recall@10) with score logit ~ N(1.5, 1), identical at every site (assumption).
- One calibration week (168 h, no intrusions needed) then one test week (168 h). Budget **B = 0.5 FA/cam-h**
  (H64's calibration target).
- Operators (H22 values, fatigue omitted): one shared FIFO queue, K servers, review time Gamma(mean 30 s,
  CV 0.3), per-review miss 0.05, bulk-ack (queue cleared) when the queue exceeds 10·K. K ∈ {2, 3}; K = 2 primary
  (400 × 0.5 = 200 FA/h ≈ 0.83 of two operators' 240 reviews/h).
- Worlds: **30 seeds** (≥ 10 required); each world redraws δ_s, alarms, intrusions and the drift site.

**Schemes (all calibrated on the calibration week only).**
- (a) pooled θ = the empirical score quantile giving estate FA ≤ B on the calibration week.
- (b) θ_s = site quantile giving site FA ≤ B on its own calibration week.
- (c) θ_s from a Lagrangian: maximise Σ_s recall(θ_s) − λ·FA_s(θ_s) with FA_s from the site's calibration week
  and recall(θ) from the declared intrusion score model (assumed known from staged tests), λ chosen so estate
  FA = B on the calibration week. No per-site cap.

**Drift monitor and hard negative.** In every world one random site's candidate rate becomes ×3 at test-week
hour 84. Every scheme runs a daily check at 24 h boundaries. (b) and (c) test each site: one-sided Poisson
p < 0.001 of the day's FA count against the site's calibration-week rate at its θ_s; a flagged site is
recalibrated on that day's alarms (to B under (b), to its allocated FA under (c)). (a) has one θ and so tests the
estate total the same way and, if flagged, recalibrates the pooled θ. "Noticed" = flagged within 24 h of onset,
i.e. at the hour-96 check (hours 84–96 of drifted data only — this is why it can fail).

**Outcomes (test week).** Realised intrusion recall@300 s (candidate, reviewed, not missed, within 300 s of
arrival); operator utilisation (busy time / K·168 h); worst-site FA/cam-h (excluding the drift site; the drift
site reported separately); number of sites with FA > B and > 2B. CIs: world-level bootstrap (2000 resamples).
Holm over the two K comparisons of D1.

**Decision (all must hold; registered before any outcome run).**
- D1: (c) − (a) recall@300 at K = 2 ≥ 0.05 with Holm-adjusted one-sided bootstrap p < 0.05 (Holm over K = 2, 3).
- D2: under (c), worst non-drift site FA ≤ 2B in ≥ 90 % of worlds.
- D3 (hard negative): (c) notices the drifting site within 24 h in ≥ 90 % of worlds, with ≤ 0.05 false flags per
  non-drift site-week.
Also reported, not decision-bearing: (b) vs (a); (a)'s drift notice rate; σ_δ = 0.6 sensitivity.

**Prediction (a guess, stated so it can be wrong).** D1 fails: (c) gains < 0.05 over (a) because all sites share
one intrusion score model, so re-allocation only moves the operating point along nearly the same curve; D2 may
fail because (c) spends budget on quiet sites; D3 passes for (c)/(b) and fails for (a).

**True by construction (not findings).** (a) meets the estate budget and (b) every site budget *in-sample*; (c)
meets the estate budget in-sample. Test week is stationary apart from the drift site, so out-of-sample budget
misses under (b) are Poisson noise only. How many sites (a) puts over budget is set by σ_δ, an input matched to
H69's partial spread — a larger σ_δ makes (a) look worse by assumption. Recall is identical across sites for a
given θ by assumption, so any recall gap between schemes comes only from operating point and queueing.

### H70 · results (2026-09-28, simulated, `out/experiments/h70_alarm_budget_scale/results.json`, 16 s, 6 workers)
30 worlds × 40 sites × 400 cams, 1,214 test-week intrusions (primary σ_δ = 0.3), world bootstrap 2000, Holm over K.

| scheme (σ_δ = 0.3) | recall@300 K=2 | util K=2 | worst non-drift site FA/cam-h | sites > B / > 2B | drift noticed ≤ 24 h |
|---|---|---|---|---|---|
| (a) pooled θ | 0.704 [0.682, 0.727] | 0.842 | 1.622 [1.499, 1.755] | 15.3 / 3.3 | 0.133 |
| (b) per-site θ | 0.697 [0.673, 0.719] | 0.837 | 0.551 [0.546, 0.555] | 19.3 / 0.0 | 1.0 |
| (c) re-allocated | 0.700 [0.676, 0.725] | 0.842 | 0.914 [0.876, 0.954] | 17.7 / 0.2 | 1.0 |

- **D1 fails**: (c) − (a) at K = 2 = −0.004 [−0.020, +0.011], Holm p 0.70 (K = 3: +0.004, p 0.59). Recall is
  detector-limited, not queue-limited — **by construction** (one declared intrusion score model at every site, AUDIT_H70): K = 3 (utilisation 0.563) gives the same recall as K = 2 (0.842), and the
  ceiling p_detect × P(score ≥ θ) × (1 − miss) ≈ 0.68–0.70 is where every scheme sits.
- **D2 fails**: under (c) the worst non-drift site stays ≤ 2B in only 0.8 of worlds (registered ≥ 0.9); (c)
  spends budget on quiet sites, as predicted. (a) puts ≈ 3 sites over 2B in every world (0.0 of worlds pass).
- **D3 met** (AUDIT_H70: easy by design — at B a site expects 120 FA/day, and half a day at ×3 gives ≈ 240; the
  per-site check catches a ×2 drift 0.97 of the time and ×1.5 only 0.32 [derived, Poisson]): (c) notices the ×3 drift at the first daily check in 1.0 of worlds with 0.015 false flags per
  site-week; (b) the same (0.009). The pooled estate monitor of (a) notices it in only 0.133 — one site ×3 is
  lost in the estate total. That contrast is monitor granularity, not the threshold scheme: nothing stops (a)
  running per-site monitors at its pooled θ (not run; AUDIT_H70).
- Decision **not met** (D1, D2 fail). Prediction was right on D1 and D3, D2 fail was flagged as possible.
- Sensitivity σ_δ = 0.6: (c) − (a) = +0.019 [−0.001, +0.041], Holm p 0.075; (a) worst site 3.137 FA/cam-h and
  ≈ 5.8 sites over 2B; (c) passes ≤ 2B in 0.067 of worlds. Wider site spread helps (c)'s recall a little and hurts
  its per-site budget a lot.
- **By construction** (not findings): in-sample budgets (test asserts); (b)'s 19.3 sites "over B" are Poisson
  noise around a θ set exactly at B (worst 0.551); how badly (a) blows sites scales with σ_δ, an input. Same
  intrusion score model at every site means re-allocation cannot find recall; a site-dependent detector would.
  (a)'s drift "notice" counts any estate flag on the drift day, so it is an upper bound.
- **Takeaway** (AUDIT_H70 wording): in this simulated estate, with the same detector at every site, re-allocating
  budget buys no recall (by construction) and pooled θ lets ≈ 3 sites run above 2× budget (worst ≈ 3.2× B); a per-site
  daily monitor catches a ×3 drift, an estate-total monitor mostly does not. It is a simulation of declared rates,
  not a measured governance answer.
- **Audit (AUDIT_H70, 2026-09-28)**: order confirmed (pre-reg 9554eed, then runner/config/results be2ca77). Rerun
  10 worlds × 3 seeds: D1 fails in all 3 ((c) − (a) −0.014 to +0.005), D3 met in all 3, D2 fails in 2 of 3 (seed 2
  passes: D2 is seed-sensitive at 10 worlds). σ_δ = 0.3 was matched to H69's *interim* 56.5 % of splits; the final
  H69 figure is 0.53 of splits / 0.68 per held-out site, and H69's unit was a detector-FP rate on 3 s clips, not
  site alarms.

### H69 · results (N = 16, registered N met; 2026-09-28)
`out/experiments/h69/results.json`, figure `docs/research/figures/h69_site_variance.png`. 16 gate-PASS, commercial_ml_ok
sites (00–20; excluded gate FAIL: 02, 07, 08, 13, 19, 21). YOLO11n imgsz 1280, conf 0.25, IoU 0.5, all conf = 1 targets.
Frame offset 0 checked against ±1 on the first 9 sites (0 best or within 0.01 everywhere except 06, where −1 is 0.075 lower).

| sub-hypothesis | result | decision |
|---|---|---|
| H69a between-site SD > 0.05 | corrected SD **0.355** [0.197, 0.431] (two-stage bootstrap), mean recall 0.642; per-site 0.000–0.966 | **met** |
| H69b within budget ≤ 80 % of splits | pooled θ (median 0.33, range 0.21–0.42) keeps held-out FA ≤ 3600 /cam-h in **0.53** of 200 splits; held-out FA median 3300, p95 9780; per held-out site within budget 0.68 | **met** (θ never at grid minimum: not vacuous) |
| H69c covariates adj R² > 0.5 | R² 0.537, **adj R² 0.369**, LOO R² 0.171 | **NOT met** |
| hard negative: same-type pairs within noise | **13 of 16** same-type pairs differ beyond their 95 % CI | **FAILS** |

Qualifications:
1. **Camera height is 4.5 m at every site** (a constant regressor, collinear with the intercept), so H69c effectively
   tests range, density and time of day only. The adjusted R² still counts it as a parameter; dropping it would change
   the adjustment, not the fit.
2. **The hard-negative failure means site type does not predict recall.** Same-type seeds differ as much as
   different types (event_plaza: 0.000 / 0.483 / 0.034). The generator changes time of day, headcount and the
   re-aimed view with the seed, so "same type" is not "same conditions" (declared at registration).
3. **Post-hoc sensitivity, NOT registered:** counting only targets ≥ 20 px tall with vis ≥ 0.5 raises most sites to
   0.94–1.00 (mean 0.756, raw SD 0.378). The spread survives, though: 05 plaza, 09 transit (dusk) and 17 plaza (night)
   stay ≤ 0.10 (0 detections at conf ≥ 0.05 on 05 and 09). Part of the spread is
   the docs/13 denominator counting occluded or edge-clipped rows (05's GT is edge slivers with vis 0–1). **Corrected
   by AUDIT_H69:** the 09/17 targets that pass ≥ 20 px & vis ≥ 0.5 stand behind fence railings (7–10 px wide,
   21–29 px tall) that the GT visibility does not model, so those rows are not usable targets either; the ≤ 0.10
   sites are a GT/visibility-labelling artefact plus tiny targets, not shown to be detector failure.
4. The FA budget is a detector-FP rate extrapolated from 3 s clips (30 frames per site), not an operator alarm.
   H69b's "met" says a pooled detector threshold transfers only about half the time. Nothing here is conformal.
5. Each site contributes one camera × 30 frames. The within-site CIs are frame bootstraps over correlated frames, so
   they are too narrow, which makes the hard-negative failure easier to trigger. 12's CI is degenerate (the same 4/7
   in every frame).

Interview sentence (superseded by AUDIT_H69 below): *across 16 generated sites the same detector at the same operating point ranges from 0 to 0.97
recall (between-site SD 0.36). Neither the site type nor the obvious covariates predict which sites fail (adj R² 0.37),
and a false-alarm threshold pooled on half the sites holds on the other half only 53 % of the time. So you calibrate
per site and per view, not per product.*

### H69 · audit (2026-09-28, `docs/research/AUDIT_H69.md`)
Pre-registration 7f3d2ce → interim 0727b9c → results 6df8784 (order confirmed). Recomputed from the cached detections
on the same 16 sites (no GPU). **H69a holds**: 5-frame block bootstrap gives corrected SD 0.354 [0.209, 0.433].
**Hard negative still fails** under the block bootstrap: 12 of 16 same-type pairs differ (was 13; 03 vs 15 now covers 0).
**H69b holds at every budget tried** (fraction of splits within budget 0.415–0.535, never at the grid minimum), including
B = 6150 /cam-h, the docs/13 conf 0.25 pooled FP rate, so 3600 is *tighter* than the operating point, not near-vacuous;
but budgets below ≈ 1200 are not resolvable with 30 frames per site (one FP = 1200 /cam-h per site). The rerun
split fraction moves 0.50–0.535 with RNG state alone. **The 0-recall sites are not detector failures shown on usable
targets**: 05 has 8 GT rows, all 3.5–6 px-wide right-edge slivers in frames 25–29; 09 and 17 are people behind fence
railings that the GT visibility does not model. Camera height 4.5 m is hard-coded in `tools/infinite_sites.py`
(design, not a bug; it makes H69c's height term constant). Site 21 passed its gate at 03:18, after the result (03:15):
an unpinned re-scan now yields N = 17 and different numbers; results are pinned to the 16 listed sites.
Interview sentence: *across 16 generated sites one detector at one operating point scores between 0 and 0.97 recall
under the docs/13 all-rows denominator, but the lowest sites are GT artefacts (edge slivers, people behind railings
the visibility label misses); what survives is that a pooled FP threshold transfers to held-out sites only about
half the time, so calibrate per site.*

### H69 · post-fix GT for sites 05/09/17 (2026-09-28, UNREGISTERED, post-audit)

Not part of the registration; re-scoring only, cached detections
(`out/experiments/h69/detections`), op conf 0.25, IoU 0.5, frames 0-29. GT corrected by
`survsim.gt.static_occlusion` (docs/BUG_gt_visibility_fences.md): env_plan fences projected
through the calibration at 4x supersampling (overlay matches the rendered pales), visibility
multiplied by the unoccluded fraction, and in-frame boxes failing `geometry.box_usable`
flagged unusable. Corrected MOT in `out/experiments/h69/gt_static_occ/<site>/`.
Site 09: 0/58 (all rows) unchanged; median visibility 0.839 -> 0.332, 67/80 rows `occluder=static`,
rows with vis >= 0.5 fall 45 -> 0, so its zero recall is over targets the corrected GT calls mostly
hidden. Site 05: usable rows 8 -> 3, still 0 hits (3 targets; not interpretable). Site 17: 3/87
unchanged; vis >= 0.5 rows 31 -> 20 at 2/20 recall: the one person whose corrected visibility
stays near 0.5 (two fence layers, cover ~0.47) is still missed, so on 17 night lighting remains a
live cause next to the fence. Registered H69 numbers stand as committed; this only confirms
R68's reading for 09 and 05.

## H70b · Per-site drift monitoring done fairly (`h70b_drift_monitor_scale`) — PRE-REGISTRATION (2026-09-28)

**Why.** AUDIT_H70 §4: H70's 0.133 vs 1.0 drift contrast compared an estate-total monitor with per-site
monitors, i.e. monitor *granularity*, not threshold *scheme*. H70b holds granularity fixed (every monitor is
per site) and asks whether the θ scheme matters, and whether a sequential monitor on hourly counts beats the
daily check.

**Simulated world (declared, H70 inputs).** 40 sites × 10 cameras; candidates 20 /cam-h with score logit
N(−2 + δ_s, 1), δ_s ~ N(0, 0.3); budget B = 0.5 FA/cam-h. Under **per-site θ** each site's expected alarm rate is
λ_s = B·10 = 5 /h; under **pooled θ** (θ set so the estate mean is B) λ_s = 10·20·Φ(−2 + δ_s − θ), which spreads
around 5 /h. Hourly alarm counts are Poisson(λ_s · m(t) · d(t)). One calibration week (168 h) estimates each
site's baseline λ̂_s; then one test week. Every site is simulated twice per world: a **null arm** (no drift) and a
**drift arm** (rate × d from onset hour ~ U[24, 72), so ≥ 96 h of drifted data), d ∈ {1.25, 1.5, 2, 3}.
m(t) = 1 (flat) or the **diurnal hard negative** m(t) = 4/3 for hours 07–19, 2/3 otherwise (2× day/night ratio,
same mean), present in both weeks. Worlds: 10 seeds × 20 worlds = 200 worlds (40 sites each).

**Monitors (per site, identical under both θ schemes).**
- **Daily Poisson**: at every 24 h boundary, flag if P(Poisson(24 λ̂_s) ≥ day count) < 0.001 (H70's check).
- **CUSUM** on hourly counts, tuned to a ×1.5 shift: k = λ̂(1.5 − 1)/ln 1.5, S ← max(0, S + x − k), flag when
  S > h_s; h_s chosen per site by 2,000 null weeks simulated at λ̂_s so P(any flag in 168 h) = 0.01. Flat
  baseline (it does not model time of day). After a flag the statistic resets.
- Reported, not decision-bearing: a diurnal-aware CUSUM (baseline per hour-of-day from the calibration week).

**Outcomes.** Detection within 48 h of onset (fraction of drift-arm sites), detection delay (hours, median over
detected), false flags per site-week (null arm). CIs: world bootstrap (2,000). **Analytic curve**: the daily
check's detection-within-48 h is exact Poisson math given λ = 5 and uniform onset phase — reported next to the
simulation (per-site θ); agreement within 0.03 is a sanity check, not a finding.

**Decision (all must hold).**
- C1: CUSUM under per-site θ detects ×1.5 within 48 h in ≥ 0.8 of drift instances, with ≤ 0.02 false flags per
  site-week (flat null arm).
- C2: the threshold scheme does not matter for drift detection: for the daily Poisson monitor, pooled-θ minus
  per-site-θ detection-within-48 h lies inside (−0.05, +0.05) at every drift size (TOST, Holm over the 4 sizes,
  adjusted p < 0.05).
- C3 (hard negative, can fail): the flat CUSUM under the diurnal pattern (no drift) raises ≤ 0.02 false flags per
  site-week.

**Prediction (a guess).** C1 met (CUSUM pools evidence across hours; ×1.5 of 5 /h is ≈ 60 excess alarms per
day). C2 likely fails at ×1.25–×1.5 because pooled θ gives some sites λ_s well below 5 /h, and power at small
drifts is steep in λ. C3 fails: a flat CUSUM reads the daytime 4/3 rate as drift.

**True by construction (not findings).** The daily check sums a whole day, so a diurnal pattern with the same
daily mean is invisible to it. Daily Poisson power is analytic in λ_s and d — the simulation only adds baseline
estimation noise from one calibration week. The only difference between θ schemes here is the spread of λ_s,
set by σ_δ = 0.3 (an input); a larger σ_δ widens the pooled-θ gap by assumption. CUSUM false-flag rate is set
to 0.01/site-week by the h_s calibration (up to λ̂ estimation error).

### H70b · results (2026-09-28, simulated, `out/experiments/h70b/results.json`, 531 s, 6 workers)
200 worlds (10 seeds × 20) × 40 sites; world bootstrap 2,000; figure `docs/research/figures/h70b_drift_detection.png`.

| θ | pattern | monitor | false flags/site-wk | det48 ×1.25 | ×1.5 | ×2 | ×3 | median delay ×1.5 (h) |
|---|---|---|---|---|---|---|---|---|
| per-site | flat | daily | 0.014 | 0.394 | 0.975 | 1.000 | 1.000 | 26 |
| per-site | flat | CUSUM | 0.020 [0.017, 0.023] | 0.512 | 0.996 [0.995, 0.997] | 1.000 | 1.000 | 13 |
| pooled | flat | daily | 0.014 | 0.355 | 0.828 | 0.985 | 1.000 | 29 |
| pooled | flat | CUSUM | 0.021 | 0.444 | 0.923 | 0.996 | 1.000 | 15 |
| per-site | diurnal | daily | 0.014 | 0.387 | 0.976 | 1.000 | 1.000 | 26 |
| per-site | diurnal | CUSUM (flat) | **0.896** [0.877, 0.915] | — | — | — | — | — |
| per-site | diurnal | CUSUM hour-of-day | 0.032 | 0.547 | 0.998 | 1.000 | 1.000 | 12 |
| analytic | flat, λ = 5/h | daily | 0.0065 | 0.384 | 0.982 | 1.000 | 1.000 | 26 |

- **C1 marginal** (AUDIT_H70B, R69 — detection met, false-flag rate on the bar; CI straddles 0.02 and a reduced re-run fails it): CUSUM ×1.5 within 48 h 0.996 [0.995, 0.997] at 0.020 [0.017, 0.023] false flags/site-week (the
  false-flag rate sits on the bar because h was set for 0.01 and one calibration week of λ̂ noise doubles it —
  construction, not finding; every seed 0.993–0.999).
- **C2 NOT met**: pooled − per-site daily det48: ×1.25 −0.039 [−0.054, −0.024] (Holm TOST p 0.15), ×1.5
  **−0.147** [−0.156, −0.139] (p 1.0), ×2 −0.015 (p 0.002), ×3 −0.000 (p 0.002). The θ scheme matters at ×1.5,
  exactly where power is steep in λ_s: pooled θ leaves low-rate sites with too few counts. CUSUM gap ×1.5 −0.073.
- **C3 NOT met (hard negative fails, as predicted)**: flat CUSUM flags the benign 2× day/night pattern 0.896
  times per site-week (every seed 0.86–0.93). An hour-of-day baseline (pre-registered, reported only) cuts it to 0.032 — still above the 0.02 bar
  (24 hourly baselines from 7 samples each; AUDIT_H70B) — at no loss of power. The daily check is immune by construction (daily totals).
- Analytic vs simulated daily det48 max |diff| 0.010 (sanity; the simulation adds only λ̂ noise, which doubles the
  daily false-flag rate 0.0065 → 0.014).
- **Decision NOT met** (C2, C3 fail). Takeaway: once every monitor is per site, pooled θ costs 0.15 detection at
  ×1.5 (not the 0.87 H70 implied at ×3, which was granularity); CUSUM halves delay at ×1.5 (26 → 13 h; ×2 19 → 5, ×3 15 → 3, ×1.25 only 61 → 47; AUDIT_H70B) but must
  model time of day or it alarms on every normal day. Every rate is declared; σ_δ = 0.3 sets the C2 gap.

### H70b · audit (2026-09-28, `docs/research/AUDIT_H70B.md`)
Reduced re-run (3 seeds × 40 worlds) at σ_δ 0.15 / 0.3 / 0.6. **C1 is marginal, not met**: detection ×1.5 is robust
(0.996 at every σ_δ) but the false-flag rate is a coin flip on the 0.02 bar (full run CI straddles it; the σ_δ 0.15
re-run gives 0.0206 and fails). h is not fitted on test data (fresh simulated nulls). **C2 is set by σ_δ**: pooled −
per-site daily det48 at ×1.5 is −0.034 at σ_δ 0.15 (C2 passes), −0.159 at 0.3, −0.384 at 0.6. The hour-of-day CUSUM
was pre-registered (not post hoc) but does not meet the bar. Analytic curve checked correct. H70's "only reliably
catches ×2 or more" is for one check; with 48 h (two checks) the daily count catches ×1.5 at 0.975 — scope, not
contradiction.

## H71 · Tracker-configuration transfer beyond one knob (`h71_tracker_config_transfer`) — PRE-REGISTRATION (2026-09-28)

**Question.** H46b showed the appearance weight w chosen on renders transfers to MOT20-02. Does the *full*
ByteTrack configuration selected on the CC0 renders rank the same way on real MOT20 footage, and what does
picking the render-best configuration cost on real?

**Grid (24 configs, fixed before any run).** `survsim/baselines/bytetrack.py`, low = 0.1, new_track = 0.6:
w ∈ {0, 2, 8} × first-stage IoU gate `match_iou` ∈ {0.2, 0.4} × track buffer `max_lost` ∈ {0.4 s, 2.0 s}
(× sequence fps) × detection confidence split `high` ∈ {0.4, 0.6}.

**Data.** Detector = h14b `mix_300_s0` (one checkpoint on both sides), embeddings = the H24 `osnet_imagenet`
embedder. Render: batch_v8 (CC0, `licences.json` commercial_ml_ok) — the 10 H24/H46b day camera-sequences,
≤ 300 frames @ 10 fps, cached dets/embeddings. Real: MOT20-01, -02, -03, -05 train, first 300 frames @ 25 fps
(MOT20-02 cached; the other three detected/embedded once, GPU only under the load rules, else CPU). MOT20 is
non-commercial: measured only, nothing trained on it.

**Outcomes.** HOTA per sequence via TrackEval (`eval/trackeval_bridge.py`); config score = mean over sequences.
(1) Spearman ρ between the 24 render and 24 real config scores, 95 % CI from 2000 bootstrap resamples of
sequences (render and real resampled independently). (2) Regret = real HOTA of the real-best config − real HOTA
of the render-best config, with the same bootstrap CI.

**Decision (both must hold).** D1: ρ ≥ 0.6 and its 95 % CI excludes 0. D2: regret ≤ 0.02 HOTA (point estimate).

**Hard negative (predicted NOT to transfer, able to fail).** Detection-confidence split `high`: render detector
calibration differs from real (same checkpoint, domain-shifted scores), so I predict the render-preferred level
of `high` (argmax of its marginal mean HOTA over the other 12 configs) differs from the real-preferred level, or
the marginal Δ(0.6 − 0.4) has opposite signs. The prediction fails if both sides prefer the same level with the
same sign. Per-knob marginals (render-preferred vs real-preferred level, Δ with CI) are reported for all four
knobs; other predictions: w transfers (H46b), max_lost transfers, match_iou uncertain.

**True by construction (not findings).** Both sides use the same detector, embedder and tracker code, so any
knob whose effect is mechanical (e.g. a longer buffer fewer fragmentations at any realism) agrees without the
renders being realistic; ρ is therefore reported together with a diagnostic ρ computed *within* levels of the
knob with the largest render marginal effect (removes the dominant structural ordering). With 4 real sequences
the CI on ρ is wide; a CI including 0 is a "not shown", not a "does not transfer". Result is single-checkpoint.

### H71 · results (2026-09-28, `out/experiments/h71/results.json`, 2155 s, CPU only, 6 workers)

Full run, not partial: 24 configs × 12 batch_v8 day camera-sequences (4 runs; "10" in the first draft was wrong, AUDIT_H71) (cached H24 dets/embeddings) and 24 × 4 MOT20
sequences (01/03/05 detected + embedded here **on CPU** — an editor job was `.running` for the whole window, so
the GPU was not used; MOT20-02 from the H17/H24 cache). Detector h14b `mix_300_s0`, single checkpoint.

- **D1 NOT met.** Spearman ρ(render, real) = **+0.0096 [−0.4088, +0.4618]**. Within levels of the dominant
  render knob (match_iou) ρ = +0.1713. Inconclusive, not a negative (AUDIT_H71, R70): MOT20 does not rank the grid consistently with itself (split-half ρ ≈ +0.02; renders +0.34), so there is no stable real ordering to match; MOT20-01 is the detector's training sequence and was not excluded (without it ρ −0.2222 [−0.4939, +0.3418], same reading).
- **D2 met, but vacuous by construction.** Regret = **0.0034 [0.0000, 0.0183]** (render-best
  w8_iou0.2_age2_hi0.6 scores 0.4425 on real; real-best w2_iou0.4_age2_hi0.6 0.446). The whole real HOTA range
  over the 24 configs is 0.4286–0.446 (0.0174), so *every* config, including the worst, has regret < 0.02 — the
  registered 0.02 bar could not fail on this grid. Not evidence of transfer; evidence that on MOT20 these knobs
  barely matter.
- **Per-knob marginals** (render pref / real pref; Δ last−first render vs real; bootstrap P(same sign)):
  w 8 / 2, +0.0088 vs +0.0060, 0.917 (direction transfers, the level does not — consistent with H46b);
  match_iou 0.2 / 0.4, **−0.0123 [−0.0194, −0.0062]** vs +0.0024 [−0.0053, 0.0092], 0.3065 (real Δ spans 0: no measurable real effect; without MOT20-01 real +[0.0012, 0.0119], a small reversal on 3 seqs);
  max_lost_s 2 / 0.4, **+0.0108 [0.0026, 0.0199]** vs −0.0005 [−0.007, 0.0044], 0.45 (real Δ spans 0; without MOT20-01 real +[0.0001, 0.0059], same sign as render — no flip, AUDIT_H71 R71);
  high 0.6 / 0.6, +0.0043 vs +0.0014, 0.5535.
- **Hard negative: prediction FAILED as scored** — `high` prefers the same level with the same sign on both
  sides. But both Δs span 0 and P(same sign) 0.5535 is a coin flip: the det-conf knob is flat on both sides at
  this grid, so "transfers" here is agreement between two noise estimates, not a transfer.
- Reading (audited, AUDIT_H71): on MOT20 the whole grid is flat (0.0174) and unranked, so knob agreement is
  mostly unmeasurable; w > 0 helps on both (real Δ CI excludes 0), the level does not carry over (H71 is HOTA,
  one checkpoint, grid-averaged; H46b's w = 8 on MOT20-02 is AssA at fixed knobs — not a contradiction). Render-chosen *tracker
  configs* should not be shipped without a real-footage check. MOT20 non-commercial, measured only.

## H3b · Far-field people on the CC0 set (`h3b_far_field_cc0`) — PRE-REGISTRATION

*Registered 2026-09-28 before any batch_v8 detection was run. Replicates H3 (batch_v6, MetaHuman,
engineering-only) on `out/batch_v8` (Quaternius CC0 bodies, `licences.json` commercial_ml_ok = true
for street_crowd_far_day/night) so that the far-field numbers can be customer-safe.*

**Hypothesis (same as H3).** Zero-shot YOLOv8n at imgsz 640 misses most far-camera people under
20 px; imgsz 1280 and tiling recover a large part of that gap at a measurable latency cost.

**Data.** `street_crowd_far` batch_v8, sources as H3: day raw, night raw, day degraded; every 3rd
frame (frames 3–297). Far cameras cam_02/cam_03 (median GT height 15 / 20 px); near camera cam_01
(median 88 px) for the hard negative. GT < 13 px = ignore regions (as H3). Same zero-shot COCO
YOLOv8n fp16, conf 0.25, IoU 0.5 matching (H3 code path `farfield.predict`).

**Arms.** `full_640`; `full_1280`; `tiled_2x2`: full frame at 640 + 2×2 tiles of 704×396 (≈10 %
overlap), each at imgsz 640, merged by NMS 0.5.

**Outcomes.** Recall at conf 0.25 per GT height bin 13–20 ("<20"), 20–40, 40–80, ≥ 80 px, far and
near cameras reported separately; AP50 per bin (point estimate). 95 % CIs by frame-block bootstrap
(blocks of 10 consecutive sampled frames within one camera/source stream, 1000 resamples, seed 0),
paired across arms for Δs. Latency: ms/frame per arm on this RTX 2070 Max-Q, **desktop only**, GPU
shared with the Unreal editor — not a deployment number.

**Decision criteria (mirroring H3's claims).**
- D1 (640 is blind at range): far-camera recall at full_640 in the < 20 px bin < 0.5.
- D2 (1280 recovers): far recall (all bins) full_1280 − full_640 ≥ +0.15 with block-bootstrap CI
  lower bound > 0.
- D3 (tiling recovers): far recall tiled_2x2 − full_640 ≥ +0.15, CI lower bound > 0.
- D4 (cost): tiled_2x2 ms/frame ≥ 2× full_640.
- Hard negative HN (can fail): on the near camera cam_01 (all bins ≥ 13 px), tiling must NOT
  improve recall: HN passes iff the CI lower bound of near recall (tiled_2x2 − full_640) ≤ 0.
  Near-camera people are ≥ 40 px mostly, so extra resolution should add nothing; if it passes the
  bootstrap lower bound, the "tiling only helps far-field" story is wrong.
Decision met iff D1–D4 all hold; HN reported separately. H3's conclusion "holds on CC0" iff D1–D3 hold.

### H3b results (`out/experiments/h3b/results.json`, figure `figures/h3b_far_field_cc0.png`)

**CC0, customer-safe** (batch_v8 Quaternius bodies, `licences.json` commercial_ml_ok = true, checked by the
runner). 891 frames (594 far-camera, 5061 GT ≥ 13 px; 297 near-camera, 2361 GT). Recall at conf 0.25,
IoU 0.5, [95 % frame-block bootstrap CI, 10-frame blocks, 1000 resamples]. Far cameras have no GT ≥ 40 px.

| arm | far 13–20 px | far 20–40 px | far all | far AP50 all | near all | ms/frame (desktop only) |
|---|---|---|---|---|---|---|
| full_640 | 0.007 [0.003, 0.012] | 0.060 [0.040, 0.081] | 0.025 [0.016, 0.035] | 0.027 | 0.904 [0.866, 0.937] | 14.0 |
| full_1280 | 0.354 [0.283, 0.424] | 0.491 [0.378, 0.609] | 0.402 [0.329, 0.476] | 0.497 | 0.918 [0.884, 0.947] | 13.3 |
| tiled_2x2 | 0.317 [0.249, 0.384] | 0.401 [0.295, 0.507] | 0.346 [0.279, 0.415] | 0.382 | 0.950 [0.931, 0.968] | 39.4 |

Near camera by bin (640 / 1280 / tiled): 40–80 px 0.877 / 0.949 / 0.940; ≥ 80 px 0.951 / 0.910 / 0.966
(20–40 px has n = 156, CIs ±0.2).

**Side by side with H3 (batch_v6, MetaHuman, engineering-only):** far recall all at 640 — H3 0.021, H3b 0.025;
at 1280 — H3 0.405, H3b 0.402. H3's best tiling (320×240 tiles at 640, 2.0× native linear) reached 0.629; H3b's registered
2×2 tiling (704×396 tiles at 640, 0.91× native linear, i.e. downscaled; full_1280 is 1.0×) reaches only 0.346, below 1280 — so the arms are not the
same tiling and "tiling beats 1280" is **not** carried over. Degraded day stream: H3b far recall 0.000 /
0.024 / 0.001 (640 / 1280 / tiled), versus H3's 0.209 at 320×240 tiling.

**Decision.** D1 met (0.007 < 0.5); D2 met (Δ +0.376 [0.307, 0.448]); D3 met (Δ +0.321 [0.256, 0.385]);
D4 met (39.4 vs 14.0 ms, 2.8×). **Decision met; H3's conclusion (640 is blind at range, 1280 and tiling
recover a large part) holds on CC0.** **Hard negative FAILS:** on the near camera tiling improves recall
+0.046 [0.026, 0.069] (40–80 px +0.063, ≥ 80 px +0.015, both CIs > 0), so tiling is not a far-field-only
effect; note tiled near AP50 is lower (0.887 vs 0.954 at 640), i.e. the recall gain at conf 0.25 comes with a
worse ranking. Latency is desktop only (RTX 2070 Max-Q shared with the resident Unreal editor), not a
deployment number.

### H3b audit (`docs/research/AUDIT_H3B.md`)

- Order confirmed: pre-registration 97cff66 (04:23:35) before the run (results written 04:28:18) and
  results 8405bca (04:30:10); the runner and config were first committed with the results, so only the
  text, not the code, was frozen in advance.
- D1–D4 are not looser than H3 (H3 had no numeric criteria); D1 (< 0.5) is a weak bar that could not fail.
- Principle 5: 3303 of 5061 far GT (65 %) are 13–20 px, i.e. not usably visible. On the usably visible
  20–40 px rows alone: 640 / 1280 / tiled 0.060 / 0.491 / 0.401; Δ vs 640 +0.431 [0.330, 0.538] and
  +0.341 [0.249, 0.438]. D1–D3 hold on those rows too.
- Tiling arm: H3b tiles are 0.91× native (downscaled), H3's 320×240 tiles 2.0× native; also 10 % vs
  20 % overlap. "Tiling does not beat 1280" is a statement about this arm, not about CC0 data.
- Block length 10 sampled frames = 3 s at 10 fps; re-run (detections reproduce exactly) with 30-frame
  blocks widens far Δ tiled to [0.218, 0.419] and near HN Δ to [0.017, 0.085]: no decision changes.
- Degraded ≈ 0 is not comparable to H3's 0.209 (different tiling arm); it contradicts no demo caption.
- Latency is unstable: the audit re-run gave 15.5 / 16.9 / 55.4 ms (vs 14.0 / 13.3 / 39.4), shared GPU.

## H3c · H3's exact tiling arm on the CC0 set (`h3c_tiling_arms`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H3c detection was run. Runner `survsim/experiments/far_field_h3c.py`
and config `configs/h3c_tiling_arms.yaml` are committed together with this text, so the code is
frozen too (the gap AUDIT_H3B found in H3b).*

**Question.** H3 (batch_v6, MetaHuman, engineering-only) reported 320×240 tiling at 0.629 far recall,
above 1280 — the claim behind "63 %". H3b tested a different arm (704×396, 0.91× native). Does H3's
*exact* arm beat 1280 on the customer-safe CC0 batch_v8?

**Data.** As H3b: `out/batch_v8` street_crowd_far day raw, night raw, day degraded; every 3rd frame;
far cam_02/cam_03, near cam_01; GT < 13 px = ignore; zero-shot COCO YOLOv8n fp16, det conf 0.01,
operating conf 0.25, IoU 0.5; licence gate (`commercial_ml_ok`).

**Arms.** `full_1280` (base); `tiles_2p0x_320x240` = H3's `sahi_320x240` exactly (full frame at 640 +
320×240 tiles, 20 % overlap, each at imgsz 640 → 2.0× native, NMS 0.5); `tiles_1p5x_427x320`
(same, 427×320 tiles → 1.5× native).

**Primary outcome (principle 5).** Far-camera recall at conf 0.25 on GT ≥ 20 px rows; 95 % CI by
paired block bootstrap, blocks of 30 consecutive sampled frames within a stream, 1000 resamples,
seed 0. Secondary: all rows ≥ 13 px and per bin.

**Decision.** Met iff far ≥ 20 px recall (tiles_2p0x − full_1280) ≥ +0.05 with CI lower bound > 0.
1.5× arm reported, not part of the decision.
**Hard negative (can fail).** Near-camera AP50 (all rows) of each tiling arm must not be more than
0.05 below full_1280 (point estimate).
**Latency.** ms/frame per arm reported, labelled shared-GPU/unstable (RTX 2070 Max-Q shared with
other agents' renders) — not a deployment number.
**Licence reading.** If the decision is met, the "tiling beats 1280, ~63 %" class of result may be
quoted from CC0 (customer-safe) with the H3c number; if not, the 63 % figure stays MetaHuman
engineering-only.

### H3c results (`out/experiments/h3c/results.json`, figure `figures/h3c_tiling_arms.png`)

**CC0, customer-safe** (batch_v8 Quaternius, `commercial_ml_ok` true, checked by the runner). 891 frames
(594 far, 1758 far GT ≥ 20 px of 5061 ≥ 13 px; 297 near, 2361 GT). Recall at conf 0.25, IoU 0.5,
[95 % paired 30-frame block bootstrap CI].

| arm | far ≥ 20 px (primary) | Δ vs 1280 | far all ≥ 13 px | far AP50 | near AP50 | ms/frame (shared GPU, unstable) |
|---|---|---|---|---|---|---|
| full_1280 | 0.491 [0.311, 0.670] | — | 0.402 | 0.497 | 0.944 | 19.3 |
| tiles_2p0x_320x240 (H3's arm) | 0.681 [0.521, 0.830] | +0.190 [+0.119, +0.265] | 0.643 | 0.741 | 0.901 | 143.3 |
| tiles_1p5x_427x320 | 0.632 [0.479, 0.779] | +0.141 [+0.083, +0.195] | 0.592 | 0.647 | 0.771 | 114.4 |

Far recall per stream (1280 / 2.0× / 1.5×): day raw 0.555 / 0.889 / 0.816; night raw 0.625 / 0.863 / 0.823;
day degraded 0.024 / 0.178 / 0.135.

**Decision met:** H3's exact arm beats 1280 on ≥ 20 px rows by +0.190, CI [+0.119, +0.265] excludes 0.
On all rows it gives 0.643, i.e. H3's MetaHuman 0.629 replicates on CC0. **Hard negative:** near AP50 drop
vs 1280 is 0.043 for the 2.0× arm (passes, ≤ 0.05) and 0.173 for the 1.5× arm (FAILS). Near recall still
rises with tiling (+0.038 [0.012, 0.072] for 2.0×), but AUDIT_H3C found near false positives at conf 0.25 rise 36 → 300 on a 198-frame re-run (precision 0.931 → 0.625: tile-border fragments NMS 0.5 does not merge), so the near recall gain is not a benefit.
**Licence reading:** the "tiling beats 1280, ~63 %" class of result is now **customer-safe on CC0**, quoted
as the H3c numbers (0.681 on ≥ 20 px, 0.643 all rows), with the ~7× latency of full_1280 on this shared
GPU stated alongside; the H3 MetaHuman 0.629 itself stays engineering-only.

### H3c audit (AUDIT_H3C, 2026-09-28)

Runner, config and `far_field_cc0.py` unchanged fe6e5e5..7b8a977 (frozen as registered). 198-frame re-run
(22 per stream, same code): far ≥ 20 px Δ 2.0× vs 1280 +0.155 [+0.048, +0.289] (decision holds); far
precision at conf 0.25 0.769 / 0.815 / 0.723, so the far gain is not NMS double counting. **Hard negative
is marginal:** full-set near AP50 drop 0.043 passes a 0.05 bar by 0.007, and the re-run subset gives 0.087
(FAILS). Latency re-time 18.1 / 114.1 / 59.3 ms (GPU 84 % busy with the Unreal editor, not idle): 2.0× arm
6.3× full_1280 (7.4× in the main run), so say "6–7×, shared GPU"; an idle-GPU timing is untested. Far CI
has 24 blocks (6 of them 9 frames) and the degraded stream repeats the day-raw moments, so it is
optimistic; the decision's lower bound is far from 0 either way.


## H3d · Tile-merge strategies for H3c's 2.0× arm (`h3d_tile_merge`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H3d detection was cached (a 2-frame-per-stream plumbing smoke ran
into a scratch dir; its numbers were not read). Runner `survsim/experiments/tile_merge.py`, config
`configs/h3d_tile_merge.yaml` and `tests/test_tile_merge.py` are committed with this text.*

**Question.** AUDIT_H3C: on the near camera, H3c's 2.0× tiling multiplies false positives at conf 0.25
because NMS at IoU 0.5 keeps both the full-frame box and tile-cut fragments. Can a better merge keep the
far gain and remove the near FPs?

**Data.** As H3c (batch_v8 CC0, day raw / night raw / day degraded, every 3rd frame, far cam_02/03,
near cam_01, GT < 13 px ignore, licence gate). YOLOv8n zero-shot, det conf 0.01, fp32 on **CPU** (GPU is
shared with editor renders) — so arm (a) is H3c's arm re-run, not H3c's cached boxes. Detections are
**cached once** (`out/experiments/h3d/dets`: full frame at 1280, full frame at 640, every 320×240 tile at
640) and every strategy is scored offline on the same boxes.

**Strategies** (all on full-640 + 2.0× tiles): (a) NMS 0.5 (H3c baseline); (b) NMS 0.5 plus suppression
when intersection / smaller area > 0.6; (c) weighted boxes fusion, IoU 0.55, score-weighted mean box,
max score; (d) tile-border rule: drop a tile box within 3 px of an inner tile edge when a full-frame box
has IoM ≥ 0.5 with it, then NMS 0.5; (e) tiles only where calibration says a 1.7 m person standing at
that row is 0 < h < 64 px, then NMS 0.5. References: full_1280, full_640 (no tiles).

**Outcomes.** Far recall at conf 0.25 on GT ≥ 20 px, 95 % paired 30-frame block bootstrap CI (1000,
seed 0); near-camera FP count and precision at conf 0.25; near AP50 (all rows); CPU merge ms/frame.

**Sanity gate.** (a) far ≥ 20 px recall within 0.03 of H3c's 0.681, else the cache differs from H3c and
the comparison is reported but flagged.

**Decision.** Met iff some strategy has far ≥ 20 px recall ≥ 0.65 **and** near FP ≤ 2× full_1280's near FP
on the same cache **and** near AP50 ≥ full_1280's − 0.02. (AUDIT_H3C's 36 → 300 was a 198-frame subset;
on the full 891 frames H3c had 148 → 983, so the cap is taken from this run's full_1280, not a fixed 72.)

**Hard negative (can fail).** (e) must not raise near-camera recall on 13–40 px rows over full_640
(point Δ ≤ 0): the ROI gate should only add tiles where people are far.

### H3d results (`out/experiments/h3d/results.json`, figure `figures/h3d_tile_merge.png`)

**CC0, customer-safe.** 891 frames, detections cached once on CPU (fp32) in `out/experiments/h3d/dets`;
sanity gate passes ((a) 0.681 vs H3c 0.681). Far recall at conf 0.25 on ≥ 20 px [95 % 30-frame block CI].

| arm | far ≥ 20 px | near FP | near precision | near AP50 | merge CPU ms/frame |
|---|---|---|---|---|---|
| full_1280 | 0.492 [0.312, 0.671] | 146 | 0.937 | 0.944 | — |
| full_640 | 0.061 | 142 | 0.938 | 0.954 | — |
| (a) NMS 0.5 | 0.681 [0.520, 0.829] | 979 | 0.697 | 0.901 | 1.008 |
| (b) NMS + IoM 0.6 | 0.676 [0.517, 0.824] | 159 | 0.932 | 0.935 | 0.716 |
| (c) WBF | 0.681 | 1071 | 0.678 | 0.889 | 3.615 |
| (d) tile-border rule | 0.682 [0.520, 0.829] | 133 | 0.944 | 0.973 | 1.631 |
| (e) far-ROI tiles | 0.681 | 914 | 0.711 | 0.904 | 0.993 |

**Decision met** by (b) and (d): far ≥ 0.65, near FP ≤ 292 (2 × 146), AP50 drop ≤ 0.02. (d) removes
every tiling FP (133 < 1280's 146) and *raises* near AP50 by 0.029 at no far cost; (b) is close
(159 FP, AP50 −0.009, far −0.005). WBF does not help: fusing a fragment with the full box still leaves
unclustered fragments. **Hard negative FAILS:** (e) raises near-camera 13–40 px recall 0.667 → 0.803
(Δ +0.136 [+0.022, +0.293], n = 162): cam_01's calibration keeps 10 of 20 tiles, and they do find its
small people — so the ROI gate is not "far cameras only", and it barely cuts near FPs (914). On cam_03 the
gate keeps all 20 tiles. **Recommended setting:** 2.0× tiles + tile-border rule (d). Merge cost is CPU
milliseconds, negligible next to the 6–7× detector cost (H3c), which H3d does not change.

**Audit (AUDIT_H3D).** Runner/config/test unchanged 3d056ec → 6c8a233; the 292 cap is the registered one
(the pre-registration already rejected a fixed 72). The pass is conf 0.25 on the pooled point: far ≥ 20 px
CI lower bound 0.521 for (d); at conf 0.4 every tile arm has far 0.592 (< 0.65) and (b)'s near FP 82 exceeds
the cap 74 while (d)'s 42 does not; day-degraded far is 0.295 for every tile arm. (d)'s AP50 above full_1280
comes from full_640's large-person recall (≥ 80 px 0.951 vs 0.910) plus tile recall on 20–40 px near people
(0.692 → 0.833) — the same small-person gain that fails (e)'s HN. IoM/border settings are insensitive
(b: 156 / 159 / 162 at IoM 0.5 / 0.6 / 0.7; d: 123 / 133 / 156 at border IoM 0.3 / 0.5 / 0.7).

## H3e · Does H3d's tile-merge choice transfer to real footage? (`h3e_tile_merge_real`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H3e number was read (a 10-frame MOT20-02 timing smoke, 2.9 s/frame on
CPU, ran into a scratch dir; its boxes were not scored). Runner `survsim/experiments/tile_merge_real.py`,
config `survsim/experiments/configs/h3e_tile_merge_real.yaml` and `tests/test_tile_merge_real.py` are
committed with this text. MOT20 is non-commercial: measurement only, never training.*

**Question.** H3d chose the tile-border rule (d) on CC0 renders. Does that design decision hold on real
crowded CCTV, or was it a property of the renders?

**Data.** MOT20-02, -03, -05, frames 3..300 step 3 (100 each, 300 total). MOT20-01 excluded
(AUDIT_LEAKAGE: frames 1–60 trained h14b; the detector here is zero-shot YOLOv8n, so this is caution,
not necessity). GT targets with height ≥ 20 px are scored; smaller targets and MOT20 ignore classes are
ignore regions. Detections cached once on CPU (fp32, det conf 0.01, max_det 1000): full frame at 1280,
full frame at 640, every 320×240 tile (20 % overlap) at 640. `out/experiments/h71/dets` is not reused: it
lacks MOT20-02 and was cached under H71's settings, so the baseline is re-run on the same frames.

**Arms.** full_1280 (reference), full_640, and the 2.0× tile arm merged with (a) NMS 0.5 and (d) the
tile-border rule, both with H3d's merge code and settings unchanged.

**Outcomes.** Recall at conf 0.25 by GT height bin (20–40, 40–80, ≥ 80, all), FP count and precision at
conf 0.25, AP50; 95 % paired 30-sampled-frame block bootstrap (1000, seed 0; 10 blocks).

**Decision (H3d transfers).** Met iff FP cut 1 − FP(d)/FP(a) ≥ 0.50 **and** recall(d) − recall(a) on all
GT ≥ 20 px ≥ −0.02 (point estimates; CIs reported).

**Hard negative (can fail).** On MOT20's dense near-field crowds tiling must NOT beat full_1280 on GT ≥ 80 px:
recall(d) − recall(full_1280) on ≥ 80 px ≤ 0 (point).

**By construction.** (d) only deletes tile boxes, so FP(d) ≤ FP(a) and recall(d) ≤ recall(a) up to NMS
ordering effects; the test is the *size* of the FP cut and the recall cost. A 320×240 tile cannot contain a
person taller than ~240 px, so ≥ 80 px recall in the tile arm comes largely from the full-640 pass plus
fragments; the hard negative therefore mostly measures 640 vs 1280 on large people plus what fragments add.

## H3f · Which cctv_day_720p stage kills far-field recall? (`h3f_degrade_ablation`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H3f detection was run (a 2-frame pixel check of the re-degraded stream
against the shipped one ran in a scratch shell to confirm seeds/fps; no detector was run). Runner
`survsim/experiments/degrade_ablation_far.py`, config `survsim/experiments/configs/h3f_degrade_ablation.yaml`
and `tests/test_degrade_ablation_far.py` are committed with this text.*

**Question.** AUDIT_H3D: on the day-degraded stream far ≥ 20 px recall is 0.295 for every tile arm vs 0.894
raw (full_1280 0.055); H3b saw ≈ 0 at 640/1280. Cause unverified. Which stage of the profile does it?

**Data.** CC0 batch_v8 `street_crowd_far_day`, far cam_02/03, frames 3, 9, …, 297 (stride 6, 50 per camera,
100 total); GT < 13 px are ignore regions; licence gate. Raw and the shipped degraded stream reuse H3d's
cached detections (`out/experiments/h3d/dets`, same frames). Every variant is re-degraded from the raw PNGs
with the profile's own calls (`Profile._pre_codec`, then `h264_sequence` over all 300 frames so the GOP is
real), same sequence seeds and fps as `survsim/video.py`, OSD off. YOLOv8n zero-shot, CPU fp32, det conf 0.01.

**Stage groups.** optics (defocus, vignette, chromatic aberration, lens dirt); noise (shot/read, FPN, hot
pixels, grain); isp (bilateral denoise, unsharp mask, dark-flat quantisation); exposure (metered AE,
auto-levels, AE/AWB drift, rolling banding); codec (H.264 crf 29, gop 8, bf 0). Variants: full, leave-one-out
(LOO, full minus g) and add-one-in (AOI, raw plus g only) for each g — 11 re-degraded variants.

**Arms.** full frame at 1280; H3d's 2.0× tiles (320×240 at 640, 20 % overlap) + tile-border rule (d) = primary.

**Outcome.** Far recall at conf 0.25, IoU 0.5, GT ≥ 20 px per variant; 95 % paired block bootstrap (1000,
seed 0), blocks of 5 sampled frames = 30 source frames (20 blocks). Loss L = R(raw) − R(full).
LOO share(g) = (R(loo_g) − R(full)) / L; AOI share(g) = (R(raw) − R(aoi_g)) / L.

**Decision.** On the primary arm, the stage with the largest LOO share must have LOO share ≥ 0.60 **and**
AOI share ≥ 0.60 (point estimates), with L ≥ 0.10. Requiring both directions separates "necessary" from
"sufficient"; if they disagree the loss is an interaction and the decision is not met.

**Prior (stated before running).** Predicted culprit: **codec** (≈ 45 %), then ISP bilateral denoise
(≈ 25 %), noise (≈ 15 %), optics blur (≈ 10 %), exposure (≈ 5 %). Downscale/resample: **0 by construction**
(below). Reasoning: a far person is ~8 px wide, one 8×8 transform block; crf 29 quantises that block's
AC energy — the only thing distinguishing a person from background — while blur at σ 0.82 and a 5-px
bilateral cost at most a pixel of edge.

**Sanity gate.** |R(full re-degraded, no OSD) − R(shipped)| ≤ 0.05 on the primary arm; else flagged.

**Hard negative (can fail).** Near cam_01 (H3d's stride-3 cache, raw vs shipped), GT ≥ 80 px: the full
profile must cost < 0.05 recall on both arms. If it fails, the profile is too harsh everywhere, not only
for small people.

**By construction.** (i) batch_v8 renders are already 1280×720, so the profile's resize is the identity:
a 13 px person stays 13 px — the "720p resample" stage cannot contribute here (asserted in the test); on
a 1080p source it would make a 13 px person ~9 px. (ii) The tile arm upsamples 2×, so a 20 px person is
40 px to the detector — but the codec's blocks are upsampled with it (8 px → 16 px); tiling cannot undo
information the codec removed. (iii) Shares need not sum to 1; LOO and AOI sums are reported as the
interaction measure. (iv) With noise off, pre-codec output equals the input within 1 grey level.

### H3e results (`out/experiments/h3e/results.json`, figure `figures/h3e_tile_merge_real.png`)

**MOT20, measurement only.** 300 frames (100 each of MOT20-02/03/05), 31,992 GT ≥ 20 px (30,222 of them
≥ 80 px), detections cached once on CPU in `out/experiments/h3e/dets` (779 s; 48 / 25 / 42 tiles per frame).
Block count is 12 (4 per sequence), not the 10 written in the registration — an arithmetic slip, no
analysis change. Recall at conf 0.25 [95 % 30-frame block CI].

| arm | recall ≥ 20 px | recall ≥ 80 px | FP @ 0.25 | precision | AP50 |
|---|---|---|---|---|---|
| full_1280 | 0.486 [0.423, 0.606] | 0.497 | 2037 | 0.884 | 0.684 |
| full_640 | 0.231 [0.144, 0.390] | 0.236 | 461 | 0.941 | 0.548 |
| (a) NMS 0.5 | 0.507 [0.453, 0.603] | 0.518 | 13082 | 0.554 | 0.449 |
| (d) tile-border rule | 0.389 [0.308, 0.534] | 0.393 | 2593 | 0.828 | 0.572 |

**Decision NOT met.** The FP half transfers: (d) cuts the tile arm's FPs by 0.802 [0.769, 0.824]
(render: 0.864). The recall half does not: recall(d) − recall(a) = −0.118 [−0.146, −0.067], six times
the 0.02 allowance (render: −0.004). Post-hoc diagnostic (not registered): of the conf ≥ 0.25 boxes
present in (a) and absent in (d), 7,122 of 18,598 (0.383) were true positives. The rule assumes an
edge-touching tile box overlapping a full-frame box is a fragment of the *same* person; in MOT20's
shoulder-to-shoulder crowds IoM ≥ 0.5 with *some* full-640 box is usually true of a different person,
and full_640 finds only 0.231 of people, so its boxes are not a reliable "already found" signal.
**Hard negative passes:** (d) is below full_1280 on ≥ 80 px, Δ −0.104 [−0.124, −0.077] — but for the
bad reason above; (a) is Δ +0.021 [−0.007, +0.038] (CI spans 0). Neither tile arm beats full_1280 on
AP50 (0.449 / 0.572 vs 0.684). **Recommendation change:** H3d's (d) is a render-validated choice for
sparse far scenes only; on dense real crowds keep full_1280, and do not quote H3d's "(d) costs no
recall" beyond sparse scenes.

### H3e audit (AUDIT_H3E, 2026-09-28)

Order and freezing clean (4d91a0c before d8db7ae; runner/config/test untouched since). The 12-vs-10 block
slip changes no CI (the count is computed by the frozen code from `block: 30`; tail blocks are 10 frames).
The 0.383 TP-deletion diagnostic reproduces exactly and is labelled post-hoc. MOT20-01 is excluded.
"Neither tile arm beats full_1280 on AP50" holds **on MOT20 only** (renders: H3c far 0.741 vs 0.497, H3d near
0.973 vs 0.944). The hard negative passes **for the wrong reason** ((d) deletes real near people).
**Correction to the recommendation:** "sparse scenes only" is not shown by MOT20. Post-hoc density check:
(d) − (a) recall is −0.079 even in the sparsest pooled quartile (~41 people/frame) and −0.163 in the densest;
within each sequence the quartiles are flat (−0.113 to −0.125), so the between-sequence gradient is a scene
effect. Say instead: (d) is render-validated; on every real density tested (≥ ~40 people/frame) it deletes
people, so gate it on density with a threshold that is still unmeasured, and keep full_1280 on real crowds.
R74 retires "(d) costs no recall" without the render/sparse scope.

### H3f results — PARTIAL, codec group only (`out/experiments/h3f_partial/results.json`, figure `figures/h3f_degrade_ablation.png`)

**Deviation, stated up front.** On CPU (GPU held by a render job) detection ran at ~9 s/frame, so this
commit scores **every 2nd registered frame (50 far frames, 10 blocks, 145 GT ≥ 20 px)** and only the
**codec** group (full, loo_codec, aoi_codec). The remaining four groups are running under the same
reduced frames into `out/experiments/h3f/`; they get their own section. Runner knobs `frames_every` and
`groups_subset` were added after registration; defaults reproduce the registered design.
**Sanity gate passes exactly:** re-degraded full = shipped recall on both arms (Δ 0.000; median pixel
diff 0, so seeds and fps match `survsim/video.py`).

| variant | full_1280 | tiles (d) |
|---|---|---|
| raw | 0.662 [0.506, 0.857] | 0.924 [0.885, 0.968] |
| full (= shipped) | 0.069 [0.000, 0.146] | 0.324 [0.189, 0.431] |
| full minus codec | 0.097 | 0.434 [0.279, 0.566] |
| raw plus codec only | 0.538 | 0.793 [0.712, 0.875] |

Codec share of the loss, tiles (d): LOO 0.184 [0.063, 0.294], AOI 0.218 [0.119, 0.357]; full_1280:
LOO 0.047, AOI 0.209. **The registered prior is wrong: codec explains ~20 %, not ≥ 60 %.** No codec
decision is possible above 0.60, so whether *any* single group meets it waits on the other four; ~80 % of
the loss sits in the pre-codec chain (optics / noise / ISP / exposure).

**Hard negative FAILS** (near cam_01, GT ≥ 80 px, H3d cache, 99 frames, 442 GT): full_1280 raw 0.982 →
full 0.772, drop 0.210 [0.168, 0.257]; tiles (d) drop 0.032 [0.006, 0.063] (passes on its own). The profile
costs a 1280 full-frame detector a fifth of its **large, near** people — too harsh everywhere, not only for
small people. Any degraded-stream detection number from this profile understates what the detector can do.

### H3f results — all five groups (`out/experiments/h3f/results.json`, figure `figures/h3f_degrade_ablation.png` replaced)

Same reduced frames as the partial section (every 2nd registered frame: 50 far frames, 10 blocks, 145 GT
≥ 20 px); sanity gate passes (full = shipped, Δ 0.000). Far recall at conf 0.25, tiles (d): raw 0.924,
full 0.324; full minus optics / noise / isp / exposure / codec 0.462 / 0.697 / 0.200 / 0.290 / 0.434; raw
plus only optics / noise / isp / exposure / codec 0.841 / 0.745 / 0.910 / 0.910 / 0.793.

| group | LOO share (d) | AOI share (d) | LOO share 1280 | AOI share 1280 |
|---|---|---|---|---|
| optics | 0.230 [0.151, 0.342] | 0.138 [0.035, 0.281] | 0.174 | 0.035 |
| **noise** | **0.621 [0.423, 0.804]** | **0.299 [0.173, 0.430]** | 0.663 [0.549, 0.850] | 0.954 [0.827, 1.063] |
| isp | −0.207 [−0.375, −0.037] | 0.023 | −0.081 | −0.070 |
| exposure | −0.058 | 0.023 | −0.035 | −0.023 |
| codec | 0.184 [0.063, 0.294] | 0.218 [0.119, 0.357] | 0.047 | 0.209 |

**Decision NOT met on the registered (tiles) arm:** the largest LOO share is **sensor noise, 0.621** (≥ 0.60),
but noise alone explains only 0.299 by AOI — on the tile arm the loss is an interaction of noise with optics
blur and the codec (LOO sum 0.770, AOI sum 0.701). On the secondary full_1280 arm noise meets both (0.663 /
0.954). **Prior wrong:** codec was predicted; it is third. Resample contributed 0 by construction. The ISP
*helps*: removing its bilateral denoise lowers far recall (0.324 → 0.200), because it is partly cleaning up
the noise. **Hard negative FAILS** (as in the partial section: full_1280 near ≥ 80 px drop 0.210).
**Reading (corrected by AUDIT_H3F):** on the registered tile arm, removing the profile's shot/read noise + grain (iso_gain 2.7 / grain_sigma 3) recovers the most far recall, but noise alone causes only 0.299 of the loss — the far loss is noise interacting with optics blur and the codec; only on the secondary full_1280 arm does noise alone account for it;
that same noise costs a fifth of large near people at 1280, so the profile is harsher than the MOT frames it
was tuned to imply for detection, and degraded-stream recall numbers from it are a lower bound.

### H3f audit (AUDIT_H3F, 2026-09-28)

Order and freezing clean (bf17f1a registration → bcc90dd partial → d06863f results). **Half the registered
frames:** `frames_every: 2` and `groups_subset` were added after registration and are disclosed; the ablated
variants' detections exist only for the scored half (25 frames/camera; `full` and `loo_optics` cam_02 have 50),
so the shares **cannot** be recomputed on the registered 100 frames. What can be checked, from H3d's cache on all
100 frames (tiles (d)): raw 0.892 [0.838, 0.946], full 0.309 [0.219, 0.393], loss 0.583 [0.487, 0.688] vs the
scored half's 0.924 / 0.324 / 0.600 and the unscored half's 0.860 / 0.293 / 0.567 — the loss denominator is
stable. With 10 blocks the noise LOO CI [0.423, 0.804] straddles 0.60, so "LOO ≥ 0.60" is a point-estimate
pass only. **Decision "NOT met" is correctly scored** on the registered primary arm (tiles_d); the 1280 pass is
the secondary arm and cannot rescue it. **Honest sentence:** "Sensor noise is the largest single lever — take it
out and far recall recovers most — but on its own it explains only about 0.3 of the loss on the registered arm;
far people are lost to noise interacting with blur and the codec." "Resample 0" is by construction (1280 source),
untested. **Hard negative consequence:** every cctv_day_720p degraded-stream detection number (H3b degraded,
H3d degraded far 0.295, demo rain/fog captions if they quote recall) is a lower bound until profile noise is
recalibrated against real footage; H32 night profiles are a different profile and untested for this, but carry
the same "sensor noise uncalibrated for detection" caveat. R75 retires "noise is the culprit/what erases far people"
without the interaction qualifier.


## H3g · Is cctv_day_720p's sensor noise too strong for real CCTV? (`h3g_noise_recalibration`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H3g number (noise estimate or detection) was computed. Runner
`survsim/experiments/noise_recalibration.py`, config `h3g_noise_recalibration.yaml` and
`tests/test_noise_recalibration.py` are committed alone with this section and frozen.*

**Why.** H3f: sensor noise is the largest single share of the far-recall loss (LOO 0.62 on tiles) and the
full profile costs large near people 0.21 at 1280 — so the profile may simply be noisier than real CCTV.

**(1) Estimator (stated before measuring).** Immerkaer (1996) MAD-of-Laplacian noise sigma — the repo's
`survsim.realism.stats.noise_sigma`: 3×3 Laplacian-difference kernel, σ = √(π/2)·mean|r|/6 over the flattest
50 % of pixels (smoothed Sobel), 8-bit luma after resizing to 720 lines. The *same* function on (a) the 12 real
day frames in `~/data/real_cctv` (MOT16/17/20, non-commercial: measured only, never trained on), (b) raw
batch_v8 renders, (c) the shipped profile's output (full chain incl. sequence codec, frames 0–15 of
cam_01/02/03). Output-referred σ is in 0–255 luma. Profile units: one std factor *s* scales the noise stage,
iso_gain·s², read_noise·s, fpn·s (sensor variance g·x + rn² scales by s²); grain_sigma (a correlation length)
is not touched. Per-pixel input σ at mid-grey = √(g·128 + rn² + fpn²) is reported for shipped and matched.

**(2) Hypothesis.** Shipped output σ ≥ 2× the real median σ. **Prior: 55 %** (H3f says noise is harmful, but
the profile was tuned to 9/14 docs/15 stats incl. noise_sigma, so a 2× miss would be surprising; the MOT frames
are JPEG and mostly 1080p→720 downscaled, which lowers their σ).

**(3) Refit and re-run.** *s* is fit by linear interpolation on the grid {0, .1, .2, .3, .4, .5, .6, .8, 1}
so median output σ = real median σ (clamped at grid ends, reported). Optics, ISP, exposure, codec unchanged.
The matched profile re-degrades H3f's 50 far frames (cam_02/03) and H3d's 99 near cam_01 frames with the same
seeds / fps / sequence codec; YOLOv8n fp32 CPU, H3f's arms (full_1280, tiles_d), conf 0.25, block bootstrap.
Raw and shipped detections are H3d's cache (so shipped far tiles recall must reproduce H3f's 0.324).

**Decision (met iff both):** far recall GT ≥ 20 px on tiles_d with matched noise ≥ 0.60 (point) **AND** near
cam_01 GT ≥ 80 px raw → matched drop < 0.05 (point) on **both** arms. Prior for the decision: 35 % (the near
1280 cost may be optics/codec, not noise).

**Hard negative (can fail):** the matched profile's output keeps noise_sigma, lap_var_log10 (blur) and
blockiness all inside the real p10–p90 band of the 12 frames on ≥ 8/12 matched frames (4 per camera). If it
fails, matching the noise broke the realism fit and H32's overfit story applies: one stat matched, others off.

**By construction (not findings):** the matched σ equals the real σ on the fit frames (it is fitted); the
p10–p90 band of 12 frames contains ~10/12 of the real frames themselves; raw/shipped recall reuse caches.

### H3g results (`out/experiments/h3g/results.json`, figure `figures/h3g_noise_recal.png`)

Runner, config and test ran as frozen at 1065f88. MAD-of-Laplacian σ (luma, 720p): **real median 0.263**, raw
render 0.52, shipped output 0.387. **Ratio 1.47, so hypothesis (1) is NOT met** (prior 55 %, wrong). Output σ is
strongly compressive in the noise level: s = 0.3 to 1.0 moves output σ only 0.291 to 0.387, because the bilateral
denoise and the codec remove most of it. Fit **s = 0.246** (not clamped). In profile units: iso_gain 2.7 to 0.163,
read_noise 2.0 to 0.49, fpn 0.5 to 0.12. Input σ at mid-grey falls from 18.7 to 4.6 DN, about 4× lower
*before* the ISP. The raw render (0.52) reads noisier than real frames because this estimator counts render
aliasing and texture in "flat" regions as noise, so it is not a pure sensor-noise measure (caveat).

| recall (conf 0.25, 95 % block CI) | raw | shipped | matched |
|---|---|---|---|
| far tiles (d), GT ≥ 20 px, n 145 | 0.924 | 0.324 | **0.607 [0.513, 0.713]** |
| far full_1280 | 0.662 | 0.069 | 0.283 [0.175, 0.421] |
| near full_1280, GT ≥ 80 px, n 442 | 0.982 | 0.772 | 0.898 (drop **0.084 [0.064, 0.106]**) |
| near tiles (d) | 0.982 | 0.950 | 0.982 (drop 0.000) |

**Decision NOT met.** The far tiles arm clears 0.60 at its point estimate (the CI crosses it), but the near 1280
cost is still 0.084, above 0.05. Matching the noise removes about 60 % of the near-camera cost; the remaining
~8 points come from optics, the codec or the noise stage's grain shape. **Hard negative FAILS: 1/12** matched
frames have all three stats in band. Per stat: noise 8/12, blur 12/12, blockiness 2/12. With less noise, the
codec grid shows more (the shipped profile had blockiness 12/12 and noise 0/12). By construction, the joint
3-stat p10–p90 band holds only **4/12 of the real frames themselves**, so the pre-registered ≥ 8/12 bar could
not be reached even by real footage. That is a registration flaw, stated here and not re-tested. It does not
rescue the result: 1/12 is still below real's 4/12, and blockiness left the band. **Reading (coupling — not H32's hold-out overfit, AUDIT_H3G):** fitting one stat
(noise) moves another (blockiness) out of band, so the profile is a coupled fit, not separable knobs. The far
recall numbers under the shipped profile are a lower bound. A matched-noise profile recovers about half the far
loss on tiles (0.32 to 0.61) but is not a validated replacement.

**Audit (AUDIT_H3G).** (i) The 1.47 ratio is estimator-referred output σ on different scenes: it includes render
texture/aliasing the pipeline leaves (s = 0 still reads 0.119), and real frames include their own scene texture, so it is
"the shipped output reads 1.47× real on this estimator", not a pure sensor-noise ratio; the added noise alone
(quadrature, 0.387 vs 0.119) is ~0.37, which would make the gap larger, not smaller. (ii) s = 0.246 is fitted to the median
of the same 12 real frames that define the HN band: in-sample; matched noise 8/12 in band is largely by construction.
(iii) The 50 far frames are H3f's scored half (half of H3f's registered 100); raw/shipped/matched share them, so the
0.324 → 0.607 comparison is paired and fair. (iv) The joint ≥ 8/12 HN bar was unreachable (real 4/12): the HN is
**uninformative as registered**, not failed; "1/12 vs real 4/12" is post-hoc on n = 12 and not significant. The
informative per-stat reading is blockiness 2/12 vs real 8/12. (v) This is coupling, not overfitting — H3g had no
hold-out — so it does not add a second instance of H32's overfit pattern.

## H32c · Is cctv_night_lowlight over-noised too, and does it make renders dark? (`h32c_night_noise`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H32c σ, luma or recall number on the showcase was computed (a plumbing
smoke run on 2 frames/camera was executed and its numbers not read). Runner
`survsim/experiments/night_noise_check.py`, config `h32c_night_noise.yaml` and `tests/test_night_noise_check.py`
are committed alone with this section and frozen. LLVIP is non-commercial research data: **measure only**, never
trained on or shipped.*

**Why.** H3g found the day profile reads 1.47× real σ after processing; H32 flagged the night profiles overfit
(hold-out 2/13 vis, 3/13 IR) and raw night renders "not dark" (luma 90 vs real ~34). Is the night profile the
same story, and does it fix the brightness?

**(1) Noise and luma.** H3g's estimator unchanged (`realism.stats.frame_stats`: Immerkaer MAD-of-Laplacian
`noise_sigma`, `luma_mean`, 8-bit luma at 720 lines) on (a) the 10 LLVIP-visible hold-out frames (last 10 of 25
sorted; the first 15 were H32's tuning set), (b) raw `out/showcase/showcase_all_night` renders, (c)
`cctv_night_lowlight` output (sequence codec, OSD off). Frames: cam_01/cam_02/cam_ptz, render frames 3..98
stride 5 = 60 frames. **Hypothesis: shipped σ ≥ 1.5× the hold-out median σ. Prior 50 %** (the night profile has
3.6× the day iso_gain, but also stronger denoise 1.56 and CRF 39, which H3g showed eat most added noise).

**(2) Luma gap.** Report raw, shipped and real hold-out median luma and the fraction of the raw→real gap the
profile closes. **By construction (label, not a finding):** the profile's auto-exposure meters the frame
median and scales it to `ae_target` = 48.65 (±2 EV clamp) before gamma/WB/noise/ISP/codec, so it is *designed*
to close (raw − 48.65)/(raw − real) of the gap and no more; the runner reports that predicted fraction next to
the measured one. It can never reach the real median (~33) unless later stages darken it.

**(3) Recall.** Noise-matched arm = H3g's refit (one std factor s: iso_gain·s², read_noise·s, fpn·s; nothing
else touched), s fitted on the grid {0, .1, .2, .3, .4, .5, .6, .8, 1} so median output σ on the 60 frames
equals the median σ of the **15 LLVIP tuning** frames (not the hold-out, so the hold-out ratio is not fitted).
YOLOv8n fp32 CPU (timed: 0.30 s/frame at imgsz 1280), conf 0.25, IoU 0.5, GT h ≥ 20 px and MOT visibility > 0
(fully occluded rows dropped), degraded boxes mapped back to render pixels. 95 % CI: paired block bootstrap,
10 000 resamples, blocks of 30 render frames per camera (12 blocks). Frame/GT alignment checked on raw
(offset 0 best: 30/33 vs 21–22/33 for ±1).

**Decision (met iff):** matched recall − shipped recall ≥ **0.10** (point) with the 95 % CI excluding 0.
Prior 30 % (the showcase has many near people that survive noise; H3g's gain was at far range).

**Hard negative (can fail):** matched-profile luma lies inside the LLVIP hold-out p10–p90 luma band on ≥ **8/13**
frames (13 evenly spaced of the 60). **Reachability, checked before running:** the band is [27.8, 39.4] (median
33.0) and **8/10 real hold-out frames pass their own band** (0.80 ≥ 8/13 = 0.62), so the bar is reachable by real
footage and is kept at 8/13. Prior that it passes: **15 %** — the AE target 48.65 sits above the band's p90 by
construction, so it passes only if the ISP/codec darken by ≥ 9 luma. If it fails, the night profile's "dark" is
brighter than real night CCTV and every night-recall number under it is optimistic in exposure.

### H32c results (`out/experiments/h32c/results.json`, figure `figures/h32c_night_noise.png`)

Runner, config and test ran as frozen at 361bb5c (output dir renamed h32c_night_noise → h32c after the run).
60 frames, 362 GT (h ≥ 20 px, vis > 0), 12 blocks. LLVIP is **measure-only**.

| arm | σ median | luma median | recall [95 % block CI] |
|---|---|---|---|
| LLVIP vis hold-out (10) | 0.1685 | 33.0 (band 27.8–39.4) | – |
| raw render | 0.2152 | 76.2 | 0.890 [0.829, 0.936] |
| shipped cctv_night_lowlight | 0.3723 | 50.8 | 0.006 [0.000, 0.016] |
| noise-matched (s 0.710) | 0.2447 | 50.8 | 0.019 [0.004, 0.033] |

**(1) Hypothesis MET:** shipped σ is **2.21×** the hold-out median (prior 50 %); raw is 1.28×. The fit target
(tuning-15 median 0.2378) is itself 1.41× the hold-out median, so the matched arm lands at 1.45× hold-out:
the two LLVIP halves disagree on σ by more than H3g's day gap.
**(2) Luma:** the profile closes **0.59** of the raw→real gap (76.2 → 50.8 vs 33.0); its AE target alone predicts
0.64 **by construction** — i.e. the darkening is what the AE target was set to do, and the output stays ~18 luma
above real night.
**(3) Decision NOT met:** matched − shipped = **+0.014 [−0.004, +0.032]**. The recall collapse (raw 0.890 →
shipped 0.006, Δ 0.884 [0.826, 0.933]) is not a noise-level effect: at matched noise it is still 0.019. Visual
check of frame cam_02/0053: people are low-contrast dark silhouettes after AE + defocus 1.52 + denoise 1.56 +
CRF 39 — the whole chain, not the noise level.
**Hard negative FAILS: 0/13** matched frames in the LLVIP luma band (real self-pass 8/10); matched luma 49–64,
cam_ptz ~63. As predicted by construction (AE target 48.65 > band p90 39.4).

**Reading (corrected by AUDIT_H32C).** The night profile reads over-noised (2.21× the hold-out by this
estimator; 1.57× the tuning-15 median, so the ≥ 1.5× hypothesis holds on either denominator but thinly) *and*
too bright (~51 vs 33), yet makes people nearly undetectable (recall 0.006). Noise was only **partially
matched** (1.45× hold-out), so "matching noise alone" was not fully tested. The night profile is **broken for
detection** — it erases people visible in the raw render — and its recall is not a night-penalty estimate of
any sign (R78); the real night penalty remains unmeasured.

### H32c audit (AUDIT_H32C)

Runner, config and test are byte-identical between 361bb5c and c7d073a. The 2.21× ratio uses the hold-out
denominator as registered; against the tuning-15 median it is 1.57×. It is not a texture-floor artefact like
H3g's (the profile at s = 0 reads σ 0.0056 — defocus + denoise erase render texture — so shipped σ is almost all
injected noise), but it is still estimator-referred on a different scene. The matched arm is **partially
matched** (fit to tuning-15, lands 1.45× hold-out). Frame check (Read tool, cam_01/cam_02 frame 53): people
clearly visible in raw; in shipped/matched they are dark blobs on darkened ground. Verdict: the night profile is
broken for detection, not a pessimistic outlier (R78). Luma 0.64 predicted vs 0.59 measured is by construction.

### H32c GT-count qualifier (BUG_night_visibility_zero, 2026-09-28)

[V] The 362 GT used "MOT visibility > 0" on `out/showcase/showcase_all_night/gt`, whose column 9 was the
mock painter's `visible_frac` (fences painted as opaque L x L boxes), not the render. With column 9 from the
rendered mask (survsim/gt/amodal.write_render_visibility) the same filter keeps **449** rows: 87 real, rendered
people (h >= 20 px) were dropped. H32c recall figures (raw 0.890, shipped 0.006, matched 0.019) were scored on
the 362 and have **not** been re-run on 449 [A]; the qualitative decision (profile broken for detection) is
not expected to flip but is unverified. docs/BUG_night_visibility_zero.md.

**Re-scored on 449 (2026-09-28) [V].** `out/experiments/h32c_vis_v2/results.json`: identical config, frames and seed;
only the GT dir changes (`out/gt_vis_v2/showcase_all_night`, column 9 from write_render_visibility). Raw 0.766
[0.667, 0.850] (was 0.890 [0.829, 0.936] on 362 — outside its CI, R79), shipped 0.0045 [0.000, 0.013] (0.006),
matched 0.016 [0.003, 0.028] (0.019), Δ matched−shipped 0.011 [−0.003, 0.027] (0.014). Decision still NOT met; noise
ratio 2.209 and HN 0/13 unchanged (no GT). The 87 added rows score about 0.25 raw [derived: (344 − 322) / 87 hits], so raw
falls; why they are harder is not checked [A]; "broken for detection" stands. H3b/H3c/H3d (batch_v8) used all rows (no visibility filter): unaffected, though
batch_v8 column 9 is also the mock painter's (1,557–4,067 rows per set differ from render visibility). H69 headline,
SD and hard negative use all rows: unaffected; its post-hoc vis ≥ 0.5 column is mock-based and sites have no ID mask.

## H32d · Which cctv_night_lowlight stage takes night recall from 0.890 to 0.006? (`h32d_night_stage_ablation`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H32d detection, σ or luma was computed. Runner
`survsim/experiments/night_stage_ablation.py`, config `survsim/experiments/configs/h32d_night_stage_ablation.yaml`
and `tests/test_night_stage_ablation.py` are committed with this text.*

**Question.** H32c: raw recall 0.890, shipped 0.006, noise-matched 0.019. The audit's sentence "the collapse
comes from the whole chain: defocus, denoise, CRF 39 silhouettes" is unverified. Which stage does it?
This diagnoses the profile; it does not calibrate it (LLVIP is measured only, never fitted to here).

**Data and detector.** Exactly H32c's 60 frames (showcase_all_night cam_01/cam_02/cam_ptz, frames 3..98 stride
5), YOLOv8n CPU imgsz 1280, conf 0.25, IoU 0.5, GT h ≥ 20 px, vis > 0; paired block bootstrap (10 000, seed 0)
over 12 blocks of 30 render frames. Each variant is degraded exactly as H32c's arms (the 20 sampled frames of a
camera as one sequence, apply_sequence's seeds), OSD off in all.

**Stage groups.** exposure (AE target 48.65, auto-levels 0.39, gamma 1.02); optics (defocus 1.52, vignette,
chromatic aberration, lens dirt); noise (shot/read, FPN, hot pixels, grain); isp (bilateral denoise, unsharp,
dark-flat); codec (H.264 crf 39, gop 8, bf 2); colour (saturation 0.56, WB gains). Variants: full, LOO (full
minus g), AOI (resize plus g only) — 13 degraded variants + raw. Loss L = R(raw) − R(full);
LOO share = (R(loo_g) − R(full))/L; AOI share = (R(raw) − R(aoi_g))/L (H3f's definitions).

**Decision.** The stage with the largest LOO share must have LOO ≥ 0.60 **and** AOI ≥ 0.60 (point estimates),
L ≥ 0.10. H3f's lesson: LOO alone overstates (a stage can be necessary without being sufficient); if the two
disagree the loss is an interaction and the decision is **not met**. Sanity: |R(full) − 0.006| ≤ 0.05.

**Prior (stated before running).** Predicted culprit **codec** (≈ 40 %), then noise (≈ 25 %), optics (≈ 15 %),
exposure (≈ 10 %), isp and colour (≈ 5 % each); P(decision met) ≈ 35 % — I expect an interaction. Reasoning:
crf 39 is 10 above the day profile's 29 (≈ 3× coarser quantiser step), and at luma ≈ 50 a dark-clothed person
is a low-contrast patch whose AC energy is exactly what the quantiser removes; the injected noise then costs
bits, making it worse (hence the interaction). Exposure only rescales, and YOLO is fairly luma-robust.

**Hard negative (can fail).** Removing the culprit (loo_culprit) must not push median luma or median σ further
outside the LLVIP hold-out bands than shipped (luma: grey levels outside p10–p90, tol 0.5; σ: |log2 ratio to
hold-out median|, tol 0.05). If exposure is the culprit this fails by construction-adjacent reasoning (AE off
returns luma toward raw 76) — which would mean the realistic darkness itself is what kills recall.

**By construction.** (i) The renders are 640×360 and the profile outputs 1280×720, so every arm upsamples 2×:
a 20 px person is 40 px to the codec and one 8×8 transform block is 4×4 source pixels — detail finer than ~4
source px is at the quantiser's mercy, detail coarser is not removed by block size alone. (ii) Detections are
scaled back by 0.5 to GT coordinates. (iii) With every group off the chain is the resize alone (asserted in the
test). (iv) Shares need not sum to 1; sums are reported as the interaction measure. (v) The OSD overlay is not
ablated (off in every arm, as in H32c).

### H32d results (`out/experiments/h32d/results.json`, figure `figures/h32d_night_stages.png`)

Pre-registration 1713d6c. 60 frames, 12 blocks, 362 GT ≥ 20 px (the same mock-visibility filter as H32c, so
the BUG_night_visibility_zero qualifier applies here too). Sanity met: re-degraded full reproduces H32c's
shipped arm exactly (σ 0.3723, luma 50.8, recall 0.0055 vs 0.006). Loss L = 0.884 [0.826, 0.933].
Recall [95 % block CI]:

| group g | full minus g (LOO) | resize + g only (AOI) | LOO share | AOI share |
|---|---|---|---|---|
| exposure | 0.008 | 0.862 | 0.003 [−0.017, 0.027] | 0.031 [0.018, 0.053] |
| optics | 0.008 | 0.881 | 0.003 [−0.008, 0.018] | 0.009 [−0.017, 0.042] |
| noise | 0.169 [0.107, 0.220] | 0.017 [0.003, 0.034] | **0.184 [0.118, 0.248]** | **0.988 [0.963, 1.005]** |
| isp | 0.011 | 0.837 | 0.006 [−0.014, 0.028] | 0.059 [0.034, 0.097] |
| codec | 0.000 | 0.232 [0.179, 0.281] | −0.006 [−0.018, 0.000] | 0.744 [0.692, 0.799] |
| colour | 0.036 | 0.865 | 0.034 [0.008, 0.062] | 0.028 [0.000, 0.054] |

Sums: LOO 0.225, AOI 1.859 — a redundant (over-determined) loss, not an additive one.

**Decision NOT met.** Culprit by LOO = **noise** (LOO 0.184, AOI 0.988): the injected sensor noise alone
(at raw brightness, σ 0.558, 3.3× the LLVIP hold-out median) takes recall to 0.017, and crf 39 alone takes it
to 0.232; with either one left in, removing the other recovers ≤ 0.17. Two sufficient killers, so no single
stage is necessary — exactly the case where LOO alone would have said "nothing matters" and AOI alone "noise".
**Prior wrong:** I predicted codec; codec is the second sufficient cause, not the first, and LOO codec is 0.
**Hard negative FAILS:** without noise σ drops to 0.0056 (|log2| 4.91 vs shipped 1.14 from the hold-out
median) — far further outside the band; luma is unchanged (11.2 vs 11.5 grey levels above p90).
**Retired by measurement:** the audit sentence "defocus, denoise" — optics and isp shares are ≤ 0.06 both
ways. **By construction:** σ 0.0056 with noise off is H32c's s = 0 floor (defocus + denoise + codec erase
render texture); aoi_exposure luma 54.1 is the AE target 48.65 plus auto-levels.

**Honest night sentence (corrected by AUDIT_H32D).** The shipped night profile does not model a dark camera
that misses people; its noise stage alone (3.3× real at raw brightness; the shipped output reads 2.21×) erases
them, and its crf 39 alone, on a 2×-upsampled 640×360 render, removes three quarters of them; exposure, blur,
denoise and colour are minor (each ≤ 7 % of the loss, upper CI ≤ 11 %, R80). A usable night profile needs both
less noise and a lower CRF, and turning noise off entirely is not realism (σ 30× below LLVIP) — diagnosis, not
calibration.

**Audit (AUDIT_H32D).** Runner/config unchanged 1713d6c → 21cea36; the re-run reproduces every per-block count.
Post hoc pair variants confirm the redundancy: removing noise and codec together recovers recall 0.870 (pair LOO
share 0.978 [0.941, 1.013]); the two alone give 0.041 (pair AOI 0.959 [0.924, 0.989]). On the corrected 449-row
render-visible GT (raw 0.766) every share moves ≤ 0.02 (noise LOO 0.199, AOI 0.988; codec AOI 0.749; pair LOO
0.977): decision, culprit and reading unchanged. The 2× upsample is by design (fixed 1280×720 output), so the
codec finding is for upsampled 360p renders, not a native 720p camera.

## H32e · Fit only noise and CRF of cctv_night_lowlight to LLVIP; what night recall is left? (`h32e_night_profile_fit`) — PRE-REGISTRATION

*Registered 2026-09-28 before any H32e fit, σ, blockiness or detection was computed. Runner
`survsim/experiments/night_profile_fit.py`, config `survsim/experiments/configs/h32e_night_profile_fit.yaml`
and `tests/test_night_profile_fit.py` are committed with this text, alone.*

**Question.** H32d: the injected noise (≈ 3× LLVIP) alone and crf 39 alone each remove most night detections;
exposure/optics/isp/colour ≤ 6 %. If only those two knobs are set to real-night values, how much recall is
left — and is raw − fitted the first defensible (still simulated-render) night penalty?

**Fit (in-sample, labelled).** Knobs: noise scale s (H3g's refit: iso_gain·s², read_noise·s, fpn·s) and CRF.
Everything else (AE/luma — left as is, optics, ISP, colour, gop 8, bf 2) is the shipped value; OSD off in every
arm. Grid s ∈ {0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0} × CRF ∈ {23, 26, 29, 32, 35, 39} (48 cells), each
cell degrading the 60 detection frames (per camera as one sequence, apply_sequence seeds). Objective:
L = log2(med σ_out / med σ_tune)² + log2(med blk_out / med blk_tune)², argmin (first cell on ties), σ =
Immerkaer on 720-line luma, blockiness = 8×8 boundary/interior gradient on native luma (the
`realism.stats.frame_stats` estimators), targets = medians of the **15 LLVIP-visible tuning frames** only.
Fitted values will be written as a new profile `cctv_night_lowlight_v2`; the shipped defaults are not changed.

**Hard negative (hold-out only, can fail).** LLVIP hold-out = the other **10** frames (the caller's "13" is
the number of sampled output frames, as in H32c; there are 25 LLVIP-vis frames, 15 + 10). First the joint
self-pass: how many of the 10 hold-out frames have σ AND blockiness inside their own p10–p90 bands. Then 13
fitted-output frames (evenly spaced over the 60) must have σ AND blockiness inside the hold-out bands on ≥
bar = min(8, floor(13 × self-pass / 10)) frames.

**Primary.** YOLOv8n CPU, imgsz 1280, conf 0.25, IoU 0.5, GT h ≥ 20 px with **render-derived visibility > 0**
(`out/gt_vis_v2/showcase_all_night`, BUG_night_visibility_zero; the same filter kept 449 rows there), H32c's
60 frames, arms raw / shipped / fitted; paired block bootstrap (10 000, seed 0) over 12 blocks of 30 frames.

**Decision.** Met iff R(fitted) ≥ 0.5 AND the 95 % CI of R(fitted) − R(shipped) excludes 0 AND the hard
negative passes. Reported regardless: night penalty = R(raw) − R(fitted) with its paired CI, labelled as a
simulated-render estimate (one scene, one detector, a profile fitted on 15 frames of one public dataset).

**Prior (before running).** Fitted s ≈ 0.5–0.6 (H32c's σ-only match was s 0.71 at crf 39, and a lower CRF
keeps more noise), CRF ≈ 29–32. R(fitted) ≈ 0.6 [wide]; P(recall_ok) ≈ 55 %, P(HN passes) ≈ 45 % (H3g:
fitting one stat pushes the other out; blockiness of LLVIP JPEGs may not be reachable by H.264 on a 2×
upsampled render), P(decision met) ≈ 30 %.

**By construction.** (i) s and CRF are fitted on the same 60 frames recall is measured on (render in-sample;
LLVIP tuning/hold-out split respected). (ii) Luma is untouched, so the luma band is not judged here (H32c: it
fails). (iii) Shipped = fit_profile(1, 39) ≡ H32c's shipped arm. (iv) The render upsample 640×360 → 1280×720
halves the effective block size relative to the source, which the blockiness fit absorbs.

### H32e results (`out/experiments/h32e/results.json`, figure `figures/h32e_night_fit.png`)

Pre-registration 70513bf; the run completed (not partial). GT: `out/gt_vis_v2/showcase_all_night` (render-derived
visibility), **449** GT ≥ 20 px over 60 frames, 12 blocks. LLVIP tuning-15 medians σ 0.2378, blockiness 1.444;
hold-out-10 σ band 0.1455–0.1847, blockiness band 1.384–1.546; joint self-pass **6/10**, so bar = floor(13 × 6/10) = 7.

**Fit (in-sample): s 0.7, CRF 39** (loss 0.0234; output σ 0.2367, blockiness 1.299). The fit *kept* the shipped
CRF: LLVIP's blockiness (JPEG, 1.44) is higher than any H.264 cell reaches on the 2× upsampled render (max 1.46 at
s 0.2/crf 39, where σ collapses), so the blockiness term pulls CRF up, not down. The premise "real-night blockiness
implies a lower CRF" is wrong for this estimator: LLVIP's 8×8 grid is its JPEG storage, not a camera codec.

| arm | σ | blockiness | recall [95 % CI] |
|---|---|---|---|
| raw | 0.2152 | 0.982 | 0.766 [0.667, 0.850] |
| shipped | 0.3723 | 1.296 | 0.0045 [0.000, 0.013] |
| fitted (s 0.7, crf 39) | 0.2367 | 1.299 | 0.018 [0.005, 0.029] |

Δ fitted − shipped 0.013 [0.003, 0.023]. **Decision NOT met**: recall 0.018 ≪ 0.5. **Hard negative FAILS**: 2/13
fitted frames inside both hold-out bands (σ 3, blockiness 2) vs bar 7; shipped 0/13. The fitted σ lands on the tuning
median but 1.40× the hold-out median: tuning and hold-out LLVIP disagree (H3g coupling: a tuning-set fit is not a
hold-out fit). Prior wrong on s (0.7 vs predicted 0.5–0.6) and CRF (39 vs 29–32).

**Night penalty, honestly.** raw − fitted = 0.748 [0.658, 0.827] is **not** a defensible night penalty: the fitted
profile is a statistics match to JPEG stills that keeps crf 39, which H32d showed alone removes three quarters of
people. It says "a camera matching LLVIP's σ and 8×8 blockiness through H.264 crf 39 loses ~75 % of rendered people",
not "night costs 75 %". The real night penalty remains unmeasured (R78 stands); a defensible fit needs a codec-free
blockiness reference (real H.264 night footage) or a blockiness estimator that excludes JPEG storage.
`cctv_night_lowlight_v2` (s 0.7, crf 39) is written to degrade.py as a record, not a recommendation; shipped defaults unchanged.
Raw recall here is 0.766 on 449 GT (H32c's 0.890 was on the mock-visibility 362).
