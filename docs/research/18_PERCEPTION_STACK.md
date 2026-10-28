# 18 · Perception Stack — detection, tracking, ReID, calibration, PTZ, and sim→real training

*Series 17–23. Zooms into stages [3]–[5] of report 17. R01/R02 cover the history
and literature; this report makes choices, sets numbers, and states what
SurvSim must output for each component.*

**Sourcing conditions.** 2026-09-26, no GPU/engine used for this report. Repo
numbers cite docs/11/12/13/15. Published benchmark numbers recalled from the
primary paper were re-checked against the paper abstract, official repository
or vendor page on 2026-09-26 and are cited as [n] to the References section;
figures that could not be confirmed were removed or are marked as such. **[BOE]** = arithmetic shown. **[INF]** = inference.

---

## 0. Summary of recommendations

| Component | Default choice | Alternative | Why |
|---|---|---|---|
| Person detector | YOLO-family (v8/11) *s* or *m* at 960–1280 px, fine-tuned | RT-DETR-R18/R50 | mature export (TensorRT, DeepStream), small-object recall with larger input; DETR where NMS in crowds hurts |
| Small-object strategy | higher input res + tiling (SAHI) on wide cameras + P2 head | super-resolution | cheap, measurable; SR often hallucinates (R04) |
| Single-camera MOT | BoT-SORT (ByteTrack + CMC + ReID) | OC-SORT for non-linear motion; ByteTrack where ReID is too costly | best balance of IDF1 and cost |
| ReID | OSNet-x1.0 (edge) / CLIP-ReID or TransReID ViT-B (server) | clothes-change models (CAL) for long-term | cost ladder |
| Soft biometrics | height from ground plane, gait descriptor | face (where legal) | survive clothing change |
| Calibration | per-camera homography from surveyed ground points + intrinsics from lens model; auto-refinement from walking people | full PnP with LiDAR survey | cheapest adequate |
| PTZ | read pose over ONVIF; CMC in tracker; suspend image-space rules while moving | full online self-calibration | robustness |
| Training | real in-domain + synthetic (≈ 1:1 to 1:4 real:synthetic by image count), synthetic pre-train then real fine-tune | synthetic only | MOTSynth/PeopleSansPeople evidence |

---

## 1. Detection

### 1.1 What the image looks like

From R01 and docs/15: CCTV frames are 720p–1080p (4K increasingly on new
installs), H.264/H.265 at CRF-equivalent quality 26–34, with the real-footage
statistics SurvSim measured on 80 frames: noise σ median 0.309, edge width
median 6.06 px (soft), blockiness 1.149. People at 20–50 m standoff on a 4 mm
lens at 1080p occupy roughly 60–100 px of height (≈ 40–65 px at 720p) [BOE: vertical FOV ≈ 2·atan(
2.7 mm/(2·4 mm)) ≈ 37°; a 1.75 m person at 30 m subtends 3.3° → 1080·3.3/37 ≈
97 px; at 50 m ≈ 58 px; at 720p multiply by 0.67]. SurvSim's shared visibility
definition — ≥ 20 px tall (`geometry.usably_visible`, CLAUDE.md principle 5) —
marks the lower edge of the operating envelope.

Johnson-criteria style reasoning (R04) sets rough pixel targets: detection of a
person ~ 20–25 px tall; recognition of activity ~ 50–80 px; identification
(face) at 250 px per metre. IEC 62676-4:2014 anchors the DORI tasks to
pixel density on the target plane: detection 25 px/m, observation 62.5 px/m,
recognition 125 px/m, identification 250 px/m [1]. **Correction:** the 2025
revision (IEC/EN 62676-4:2025) replaces DORI with seven levels — overview 20,
outline 40, discern 80, perceive 125, characterise 250, validate 500,
scrutinise 1,500 px/m [2]. Specifications written from 2026 on may use either
vocabulary; the product's commissioning report should state both.

### 1.2 Detector families

| Model | COCO AP (val) | Speed reference | Notes |
|---|---|---|---|
| YOLOX-L | 50.0 | 68.9 FPS on V100 (paper) | YOLOX family (X variant) is ByteTrack's detector [3][4] |
| YOLOv8-s / -m | 44.9 / 50.2 | A100 TensorRT 1.20 ms (s) | Ultralytics docs [5] |
| YOLO11-n / -s / -m | 39.5 / 47.0 / 51.5 | T4 TensorRT10 1.5 / 2.5 / 4.7 ms; 6.5 / 21.6 / 68.1 GFLOPs | Ultralytics docs [6] |
| YOLOv10 (NMS-free) | see paper tables | lower end-to-end latency (no NMS) | Wang et al. 2024 [7] |
| RT-DETR-R50 / -R101 | 53.1 / 54.3 | 108 / 74 FPS on T4 (paper) | Zhao et al. 2023 [8] |
| RT-DETRv2 | bag-of-freebies improvements; discrete sampling operator eases deployment | | Lv et al. 2024 [9] |
| Grounding DINO / OWL-ViT (open vocab) | — | 10–100× heavier | for rare objects / search, not the live loop |

COCO AP is a poor predictor of CCTV person recall: COCO persons are large and
well-lit. The number that matters is **recall at the operating threshold for
persons 20–60 px tall under the site's degradation**, plus **false positives
per camera-hour** (SurvSim `eval/detection.py` already converts FPPI into
alarms/camera-hour, docs/11).

### 1.3 In-repo evidence

docs/13: zero-shot YOLO11n (COCO, imgsz 1280, conf ≥ 0.01) on a 600-frame
MOT20 subset: **AP 0.348, AP50 0.730, AP75 0.293**. docs/11/12: on SurvSim's
batch_v4 renders (all MetaHuman, 3 scenarios × day/night, 5,400 frames),
yolov8n **recall 0.758 vs 0.577** for the older CesiumMan characters on the same
770 GT boxes. That delta — +18 points of recall from better humans — is the
cleanest in-house sim-realism measurement so far and shows why "the detector
finds the synthetic person" is a realism metric in its own right.

### 1.4 The 20–60 px band

Techniques, in order of cost-effectiveness [INF from R01 and the cited papers]:

1. **Raise input resolution** (640 → 1280). Roughly 4× compute; typically the
   single largest small-object gain.
2. **Add a stride-4 (P2) head**; cheap for YOLO-family.
3. **Tiling / slicing** (SAHI, arXiv:2202.06934): overlapping tiles + full-frame
   pass, merge. Akyon et al. (ICIP 2022) report +6.8 / +5.1 / +5.3 AP from
   sliced inference alone (FCOS / VFNet / TOOD) and +12.7 / +13.4 / +14.5 AP
   with sliced fine-tuning, on VisDrone and xView [10]. Cost scales with tile count; use only
   on wide-area cameras where the far field matters.
4. **Temporal context**: tracks rescue low-score detections (ByteTrack's core
   insight). This is why detector threshold should be low (0.1) with the
   tracker deciding.
5. **Fine-tune on in-domain small people** including synthetic ones at the
   exact pixel heights of the site — SurvSim's rig analysis can compute the
   site's pixel-height distribution per zone, and the generator can match it.
6. **Degradation-aware training** (R04: enhancement pre-processing often hurts
   un-retrained detectors; training on degraded imagery helps).

### 1.5 Crowds

Dense crowds (MOT20: >100 people/frame) break NMS. Options: NMS-free/DETR
detectors, head detection (CroHD: 9 sequences, 11,463 frames, ~2.28 M annotated heads; Sundararaman et al., CVPR 2021 [11]) with body
inference, and switching to density estimation above a threshold (report 19
crowd section). SurvSim's crowd-density bug (docs/11 bug 13: counting only
visible people underestimated density) is a reminder that density GT must
count occluded people.

### 1.6 Other perception heads

* **Pose** (17 COCO keypoints; RTMPose, arXiv:2303.07399; YOLO-pose): feeds
  fall/fight models and gait. At < 60 px pose is unreliable [lore]; run on
  demand.
* **Attributes** (upper/lower colour, hat, bag, hi-vis): the substrate for
  natural-language search (R05) and for operator descriptions. PA-100K/PETA/
  RAP style attribute sets; CLIP-based zero-shot attributes are viable server-
  side.
* **Objects**: bags, suitcases, vehicles, ladders (perimeter), drones. COCO has
  handbag/backpack/suitcase; "abandoned object" needs better small-object
  classes (report 19).

### 1.7 What SurvSim must output for detection

* Mask-derived amodal **and** visible boxes (Unreal backend: yes; docs/11).
* Visibility fraction, pixel height, distance, occluder class.
* Ignore regions in MOTChallenge convention (static persons, reflections,
  distractors — docs/13 uses classes 2/7/8/12).
* Per-frame imaging-profile ID and IQA stats so recall can be stratified by
  degradation.
* Hard-negative objects: mannequins, posters of people, reflections in glass,
  statues, animals at night (fox/deer in IR) — **not yet systematically
  generated** (report 23).
* COCO keypoints (yes, docs/11) and attribute labels per identity per epoch
  (partial: appearance epochs exist; attribute vocabulary needs to be exported
  in a standard schema).

---

## 2. Single-camera multi-object tracking

### 2.1 The family

All strong 2022–2025 online trackers are SORT descendants (Kalman + Hungarian;
arXiv:1602.00763):

| Tracker | Key idea | MOT17 test (HOTA / MOTA / IDF1) | MOT20 test HOTA |
|---|---|---|---|
| DeepSORT [13] | + appearance | superseded; re-baselined as StrongSORT [16] | — |
| ByteTrack [14] | associate low-score boxes in a second pass | 63.1 / 80.3 / 77.3 | 61.3 (MOTA 77.8, IDF1 75.2) |
| OC-SORT [15] | observation-centric re-update, momentum | 63.2 / 78.0 / 77.5 | 62.4 (repo README) |
| StrongSORT++ [16] | modern DeepSORT + AFLink + GSI | 64.4 / 79.6 / 79.5 | 62.6 |
| BoT-SORT-ReID [17] | ByteTrack + CMC + ReID fusion + better KF state | 65.0 / 80.5 / 80.2 | 63.3 |
| Deep OC-SORT [18] | OC-SORT + adaptive appearance | 64.9 HOTA | 63.9 |
| MOTR / MOTRv2 (end-to-end transformers) | query propagation | competitive on DanceTrack, heavier | — |

All MOT17/20 numbers are private-detector test results taken from the
paper abstracts or official repositories [14]–[18] (checked 2026-09-26). Of the
earlier figures, OC-SORT's MOT20 HOTA was corrected from 62.1 to 62.4, and
DeepSORT's numbers and Deep OC-SORT's IDF1 were removed as unconfirmed. They use MOT-trained YOLOX-X detectors — docs/13's numpy
ByteTrack with zero-shot YOLO11n at HOTA 0.443 (0.537 at α = 0.5; TrackEval parity — 0.434 pre-parity, 0.545 pre-fix) on a MOT20 subset is not
comparable, and says so.

### 2.2 Choice for CCTV

* **Fixed cameras**: ByteTrack or OC-SORT is enough for most scenes; add
  sampled ReID features when occlusion is frequent. Low detection threshold
  (0.1) into the second association stage.
* **PTZ and shaky masts**: camera-motion compensation (CMC) is mandatory
  (BoT-SORT uses sparse optical flow / ECC); read the PTZ state too.
* **Low frame rate**: below ~3 fps (R01) IoU association fails; switch to
  ground-plane distance + appearance gating. WILDTRACK at 2 fps sits on this
  cliff.
* **Long occlusions**: keep lost tracks 1–3 s (docs/13's `max_lost` = 1 s);
  longer lost buffers inflate ID-switches in crowds.
* **Metrics**: HOTA with DetA/AssA split (Luiten et al., IJCV 2021 [19]) plus IDF1; MOTA is
  detection-dominated and should not be the headline (R01, docs/13).

### 2.3 Engineering debt found in-repo

docs/13: a full 8,931-frame MOT20 `--task all` run was killed after 2.5 h (and
again after 1 h 26 min). **Correction:** docs/13 (2026-09-26) retracts the earlier
"association/HOTA is O(n²)" diagnosis — profiling shows `ByteTracker` +
`evaluate_mot` take ~62 s for the whole MOT20 train split; the remaining time is
in the unprofiled COCO-mAP and (likely) ReID crop-embedding stages. Profile those
next, and use TrackEval's reference HOTA
(https://github.com/JonathonLuiten/TrackEval) for cross-checking. This is a
prerequisite for any serious tracker benchmarking (report 23, M1).

### 2.4 What SurvSim must output for MOT

* Per-camera identities stable across the whole run, including through
  occlusion (mask-derived visibility per frame).
* Occlusion *events* (who occluded whom, duration) — lets failure analysis
  separate "lost in occlusion" from "lost at frame edge".
* Frame-rate and frame-drop variants of the same run (degrade profile controls
  frame drop) to map the fps cliff.
* PTZ state per frame (pan/tilt/zoom) and camera shake trajectory so CMC can be
  scored separately from association.

---

## 3. Re-identification and cross-camera association

### 3.1 Model ladder

| Model | Market-1501 R1/mAP | MSMT17 R1/mAP | Cost | Source |
|---|---|---|---|---|
| OSNet-x1.0 | 94.2 / 82.6 | 74.9 / 43.8 | 2.2 M params, 0.98 GFLOPs | Zhou et al. ICCV 2019 [20]; torchreid model zoo, softmax, same-domain [21] |
| BoT (ResNet50 bag of tricks) | 94.5 / 85.9 | — | baseline | Luo et al. CVPRW 2019 [22] |
| TransReID (ViT-B, official repo) | 95.1 / 89.0 | 85.3 / 67.8 | server | He et al. ICCV 2021 [23] |
| CLIP-ReID (ViT-B/16) | 95.5 / 89.6 (+SIE+OLP 95.4 / 90.5) | 88.7 / 73.4 (+SIE+OLP 89.7 / 75.8) [paper Table 2, verified 2026-09-26; README 91.1/86.7 on MSMT is *with re-ranking*] | server | Li et al. AAAI 2023 [24] |
| SOLIDER (self-supervised human-centric pre-training) | reported higher; see paper | | server | Chen et al. CVPR 2023 [25] |

**Clothes-changing ReID** is the real surveillance problem (R02): LTCC
(Qian et al., ACCV 2020 [26]) and PRCC clothes-change Rank-1 is far below same-clothes;
the dedicated CAL method reports LTCC clothes-changing
top-1 40.1 % / mAP 18.0 % and PRCC clothes-changing 55.2 % / 55.8 % (Gu et al., CVPR 2022 [27]). Gait collapses in the wild (GREW, Gait3D: Rank-1
well below lab CASIA-B numbers, R02). SurvSim's `reid_by_epoch` scores ReID
within and across appearance epochs, and its gait signature (6 parameters,
defeatable by a limp) is a first-class biometric — this is SurvSim's strongest
research niche (R02, corpus fact 6).

In-repo floor: OSNet with **ImageNet** weights (no ReID training) scores
R1 0.186 / mAP 0.231 cross-time on MOT20 subset and 0.156 / 0.279 cross-camera
on the mock set (docs/13; mock is plumbing-only). A MSMT17-trained OSNet is the
obvious next baseline.

### 3.2 Association in a real estate

Production MTMC combines (R02; the AI City Challenge has run multi-camera
people tracking tracks, and its 2026 Track 1 is "Multi-Camera 3D Perception
(Sim2Real)" scored by 3D HOTA — itself a synthetic-to-real benchmark directly
relevant to SurvSim [28]):

1. **Topology prior**: camera graph with exit→entry zones and transit-time
   distributions (log-normal fits), learned from confident matches over days.
2. **Appearance**: mean or quality-weighted embedding over the tracklet's best
   crops (highest, least occluded, sharpest).
3. **Space-time constraints**: no simultaneous presence in non-overlapping
   views; speed limits.
4. **Hierarchical clustering / min-cost flow** over tracklets in a sliding
   window with revisions.
5. **Overlapping views**: ground-plane fusion (calibrated) — MVDet/MVDeTr style
   multiview detection (MVDet: 88.2 % MODA on Wildtrack; Hou et al., ECCV 2020 [29]) if a site has dense overlap.

Metrics: global IDF1 across cameras, and SurvSim's `handoff_gap` (time a subject
is unaccounted for between cameras). Operators care about "did the system
keep the person across the handoff", which IDF1 averages away.

### 3.3 What SurvSim must output for ReID/MTMC

* Global identity per person across all cameras (yes, `identities.parquet`).
* Appearance epochs with the *act* of change (removing a jacket in a blind
  spot vs on camera) (yes; disguise-in-blind-spot bug fixed, docs/11 bug 3).
* Transit-time ground truth between camera pairs (derivable from world.parquet).
* Per-identity soft biometrics: height (only 3 baked bodies scaled per person,
  docs/11 — a known limitation for height-based ReID), gait parameters.
* Crops meeting a quality spec (height ≥ 48 px, visibility ≥ 0.6, docs/13) with
  camera, epoch and distance tags.
* Look-alike distractor populations (same uniform, same hi-vis — docs/11 notes
  hi-vis share 0.2 on work sites) as ReID hard negatives.

---

## 4. Calibration and geo-registration

### 4.1 Why it dominates

R02: 1° extrinsic pitch error at 30 m ≈ 3.9 m ground-plane error — 8× the MODA
tolerance of 0.5 m. SurvSim's own history (docs/11 bug 1: inverted pitch sign
pointed every camera at the sky; bug 5: distortion applied to pixels but not to
projection) shows how silent calibration errors are.

### 4.2 Practical procedure per camera

1. **Intrinsics**: from lens datasheet (focal, sensor size) and a one-off
   checkerboard/ChArUco on representative units per model; distortion
   (Brown–Conrady; fisheye model for < 2.8 mm) matched to OpenCV (SurvSim
   matches OpenCV to 1e-6, docs/11).
2. **Extrinsics / homography**: ≥ 6 surveyed ground points (RTK-GNSS or from a
   site plan / OS MasterMap) clicked in image; solve PnP with known intrinsics
   or a direct homography for the ground plane. Report reprojection residual in
   **metres on the ground**, not pixels.
3. **Auto-refinement**: walking-person height statistics (vanishing-point from
   head–foot lines; Lv, Zhao & Nevatia, TPAMI 2006 [30]) to detect drift.
4. **Health**: compare a keypoint set on static structure to the reference;
   raise "calibration invalid" when displacement > threshold (tamper `tilt`).

### 4.3 Error budget [BOE]

For a camera at height h = 6 m, target at ground distance d = 30 m, the ray
depression angle θ = atan(6/30) = 11.3°. Ground distance error per degree of
pitch error ≈ d²+h² / h · Δθ(rad) = (900+36)/6 × 0.01745 ≈ 2.7 m (R02's 3.9 m
uses different geometry — both show metres per degree at CCTV standoffs).
Consequence: **zones near their far edge need margins of several metres or a
higher mount**; SurvSim can sweep this (report 23).

### 4.4 What SurvSim must output

* Exact intrinsics + distortion + extrinsics per camera per frame (live pose —
  principle 2).
* A "configured" vs "actual" pose pair after tamper/PTZ, so the product's
  calibration-health detector can be scored.
* Survey-point sets with realistic noise to simulate commissioning error.

---

## 5. PTZ handling

* Read absolute PTZ position over ONVIF PTZ service (GetStatus) at ≥ 5 Hz; not
  all cameras report accurately during motion [lore].
* During motion: pause image-space logic, run CMC-enabled tracker, lower
  confidence of ground projections.
* At a preset: restore homography from preset calibration (per-preset
  homographies are the practical approach; continuous PTZ calibration from
  pan/tilt/zoom→intrinsics lookup tables is possible but brittle [INF]).
* Slew-to-cue: convert target ground position → pan/tilt with a per-camera
  model; zoom to reach the "recognise" DORI band (~125 px/m).
* Auto-tracking: closed-loop visual servoing on the target track; operators
  often disable it because it loses targets in clutter [lore].

SurvSim's camera director implements PTZ schedules; GT follows the live pose.
What's missing is a **slew-to-cue benchmark**: given a cue at t0, did the PTZ
acquire the subject at recognise-level pixel density by t0+Δ? (report 23).

---

## 6. Training recipes: synthetic → real

### 6.1 Evidence base

* **MOTSynth** (Fabbri et al., ICCV 2021, arXiv:2108.09518): 768 GTA-V
   sequences; the authors state that "MOTSynth can be used as a replacement for
   real data on tasks such as pedestrian detection, re-identification,
   segmentation, and tracking" [31]. (Exact per-table deltas were not
   re-verified here; report 24 covers them.)
* **PeopleSansPeople** (Ebadi et al., 2021 [32]): on COCO person keypoints,
  synthetic pre-training + fine-tuning gave 44.43 ± 0.17 AP vs 21.90 AP for
  ImageNet pre-training in the few-shot regime (+22.53), and 63.47 ± 0.19 vs
  62.40 AP with abundant real data (+1.07). **Correction:** the earlier draft's
  "60.37 vs 55.80" was wrong. The gain is large when real data is scarce and
  small once it is plentiful.
* **BEDLAM** (Black et al., CVPR 2023 [33]): HPS models trained
  on synthetic data alone matched or beat real-trained models on real
  benchmarks — body diversity, realistic clothing simulation and lighting were
  the causal ingredients.
* **Domain randomisation** (Tobin et al., IROS 2017 [34]) vs **structured /
  photoreal**: for people, structured realism (MOTSynth, BEDLAM) beats pure
  randomisation [INF from R04].
* **JTA / GTA-based ReID** (e.g. PersonX, Sun & Zheng, CVPR 2019 [35]; ClonedPerson — 5,621
  identities, 887,766 images, Wang et al., CVPR 2022 [36]): synthetic ReID pre-training helps, but domain gap
  to real remains large without fine-tuning.
* **Synthehicle** (vehicle MTMC: 17 h of video, 340 cameras, 64 scenes; Herzog et al. 2022 [37]) — the design
  template docs/02 names for synthetic MTMC.

### 6.2 Recipe (recommended default)

1. Start from a COCO-/Objects365-pretrained detector.
2. **Pre-train on synthetic** (SurvSim renders degraded through the calibrated
   profiles; mix day/night/IR/weather; match site pixel-height distributions).
3. **Fine-tune on real** in-domain data (even 1–5k labelled frames from the
   target site class). Keep 10–30 % synthetic in the fine-tune batches to avoid
   forgetting rare conditions (night, rain, disguise) [INF].
4. Ratio guidance: evidence suggests diminishing returns beyond ~4:1
   synthetic:real by image count at full real data; the gain is concentrated in
   rare conditions and low-data regimes [INF from PeopleSansPeople/MOTSynth].
5. **Validate only on real**, split by site/camera (report 21). Synthetic
   validation is for per-condition stress testing, not model selection.

### 6.3 Measuring the sim2real gap

SurvSim already defines the protocol (docs/13): same models, thresholds, code,
metric definitions; report synthetic − real per task at matched pixel-height
distributions; if synthetic is much easier, it is not realistic enough to
evaluate on; if much harder, suspect a rendering artefact. Complementary
measures:

* **Image statistics** (docs/15): `cctv_day_720p` now 6/14 stats in the real
  band on UE renders (`mtf_ratio`, `edge_width`, `luma_mean`, `chroma_mean`,
  `cast_a`, `cast_b`); `cctv_legacy_sd` 9/14; `temporal_noise` still out
  (9.46 vs 1.57–2.93 band), partly because the real band is JPEG-still noise.
* **FID/KID** on crops rather than full frames (FID on full frames is dominated
  by background) — `eval/realism.fid_report` exists.
* **Detector-as-judge**: recall of a fixed real-trained detector on synthetic
  people at matched pixel heights (batch_v4: 0.758 recall).
* **Train-on-synthetic, test-on-real (TSTR)** — the only measure that directly
  answers "does this data help?".
* **Feature-space domain classifiers**: if a linear probe on detector features
  separates synthetic from real at > 95 %, the gap is large [INF].

### 6.4 Domain randomisation dimensions SurvSim should cover

Lighting (sun elevation/azimuth, overcast, streetlights, IR illuminator
falloff), camera (height 3–12 m, pitch 10–45°, focal 2.8–12 mm, sensor noise,
codec CRF 26–36, GOP), weather (rain streaks near lens, fog, snow), people
(body shape — only 3 baked bodies today, docs/11 — clothing, carried objects,
gait), density (1–100 per view), clutter, and **hard negatives**.

---

## 7. Putting it together: per-component "definition of done"

| Component | Acceptance on real validation set | Synthetic stress set |
|---|---|---|
| Detector | recall ≥ 0.9 for ≥ 40 px persons at ≤ 0.5 FP/camera-hour after tracking (site-class dependent) [INF target] | recall by pixel-height bucket and profile; no bucket < 0.6 above 20 px |
| MOT | HOTA ≥ 0.6, IDF1 ≥ 0.7 on in-domain sequences | ID-switch rate vs fps and occlusion density |
| ReID | R1 ≥ 0.8 same-clothes cross-camera within site; report clothes-change separately | `reid_by_epoch` within/across epoch |
| MTMC | global IDF1 ≥ 0.6; median handoff gap ≤ transit time + 2 s | `handoff_gap` distribution |
| Calibration | ground residual ≤ 0.5 m at zone boundaries | zone-event F1 vs injected extrinsic error |
| PTZ | slew-to-cue acquisition ≥ 90 % within 3 s | cue benchmark |

These targets are proposals to be negotiated with customers, marked [INF]; the
point is that each has a real and a synthetic half.

## 8. Model export, quantisation and the accuracy you lose getting to the edge

A model that scores well in PyTorch is not the model that runs. The production
path is PyTorch → ONNX → TensorRT (server/Jetson) or OpenVINO (Intel) or a
vendor NPU compiler (Hailo, Ambarella CVflow, Axis ARTPEC DLPU on-camera).
Three accuracy taxes accrue:

1. **Pre-processing mismatch.** Letterbox vs stretch resize, BGR vs RGB,
   normalisation constants, and — most insidiously — decoding the stream with a
   different colour matrix (BT.601 vs BT.709) than the training frames. A
   pipeline that trains on PNG renders and infers on NVDEC-decoded H.264 must
   make SurvSim's degradation chain end in the same colour conversion the
   production decoder uses [INF]. SurvSim's batched `h264_sequence` codec
   (docs/15) is a step toward this; it encodes yuv420p, so the chroma
   subsampling at least matches.
2. **FP16** is essentially free for detection and ReID on modern GPUs.
3. **INT8 post-training quantisation** typically costs 0.5–2 AP on COCO for
   YOLO-family models with good calibration data [INF/lore; no vendor figure
   re-verified — measure it; TensorRT INT8 calibration is documented in
   [38]]. The
   loss concentrates in exactly the small, low-contrast objects CCTV cares
   about [lore], so the calibration set must be drawn from the deployment
   distribution — degraded, night, small people — not from COCO. SurvSim can
   supply a stratified calibration set per site class.

**Acceptance rule [INF]:** every exported artefact is re-scored on the same
evaluation harness (docs/13's `survsim baseline` run against the exported
engine's detections), and the delta per pixel-height bucket is recorded in the
model registry (report 21). A quantised model is promoted only if no bucket
drops more than a set tolerance (e.g. 3 recall points).

## 9. A failure-analysis cookbook

When a number is bad, the order of suspicion that has paid off in this repo and
in the literature:

1. **Geometry before models.** Check camera pose and projection (docs/11 bugs
   1 and 5; the "black render" was a rotator argument order). Plot GT boxes on
   frames before believing any metric.
2. **Ground-truth convention.** Ignore regions, amodal vs visible boxes,
   1-based vs 0-based frames (docs/13: render frame i is MOT frame i+1),
   maxDets (docs/13: COCO's default 100 silently caps recall on MOT20).
3. **Resolution and pixel height.** Stratify every metric by height bucket;
   most "the model is bad" findings are "the people are 18 px tall".
4. **Degradation stage.** Re-score on the clean render; if the gap is huge, the
   profile, not the model, is the story (docs/15 shows how far current profiles
   sit from the real band on some stats).
5. **Association vs detection.** HOTA's DetA/AssA split tells you which half
   failed; do not tune the tracker when DetA is the problem.
6. **Only then** the model: capacity, training data, augmentation.

Every one of these should become a regression test when it bites (CLAUDE.md
working style) — including in the product codebase, not only in SurvSim.

## 10. Open research questions SurvSim is positioned to answer

1. What is the recall curve vs pixel height for a fine-tuned detector under
   each calibrated profile — and where does night IR move the 50 %-recall
   point? (Needs a real IR reference set, docs/15 gap.)
2. How much does synthetic pre-training help **clothes-changing** ReID when
   epochs are generated with controlled changes (jacket off, hat on, bag
   swap)? No public dataset controls this.
3. How robust is MTMC association to clock skew and calibration drift, jointly?
   SurvSim can inject both with ground truth; real data cannot.
4. Does gait survive codec and frame-rate degradation at 30–60 px? The six-
   parameter gait signature can be scored against degraded renders.
5. At what density does per-person tracking stop being worth running (versus
   density estimation), for each profile?

---

## References

Checked 2026-09-26 by fetching the arXiv abstract, the official repository or
the vendor/standards page.

1. IEC 62676-4:2014 DORI pixel densities — Axis white paper, "Pixel density based on IEC 62676-4:2014". https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014
2. IEC/EN 62676-4:2025 seven-level model — JVSG summary. https://www.jvsg.com/iec-62676-4-oodpcvs/ ; IEC webstore https://webstore.iec.ch/
3. Ge, Liu, Wang, Li, Sun. "YOLOX: Exceeding YOLO Series in 2021." arXiv 2021. https://arxiv.org/abs/2107.08430
4. Zhang et al. "ByteTrack: Multi-Object Tracking by Associating Every Detection Box." ECCV 2022. https://arxiv.org/abs/2110.06864
5. Ultralytics YOLOv8 docs. https://docs.ultralytics.com/models/yolov8/
6. Ultralytics YOLO11 docs. https://docs.ultralytics.com/models/yolo11/
7. Wang et al. "YOLOv10: Real-Time End-to-End Object Detection." NeurIPS 2024. https://arxiv.org/abs/2405.14458
8. Zhao et al. "DETRs Beat YOLOs on Real-time Object Detection" (RT-DETR). CVPR 2024. https://arxiv.org/abs/2304.08069
9. Lv et al. "RT-DETRv2: Improved Baseline with Bag-of-Freebies." arXiv 2024. https://arxiv.org/abs/2407.17140
10. Akyon, Altinuc, Temizel. "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection" (SAHI). ICIP 2022. https://arxiv.org/abs/2202.06934
11. Sundararaman et al. "Tracking Pedestrian Heads in Dense Crowd" (CroHD). CVPR 2021. https://arxiv.org/abs/2103.13516
12. Bewley et al. "Simple Online and Realtime Tracking" (SORT). ICIP 2016. https://arxiv.org/abs/1602.00763
13. Wojke, Bewley, Paulus. "Simple Online and Realtime Tracking with a Deep Association Metric" (DeepSORT). ICIP 2017. https://arxiv.org/abs/1703.07402
14. ByteTrack official repository (MOT20 results). https://github.com/ifzhang/ByteTrack
15. Cao et al. "Observation-Centric SORT." CVPR 2023. https://arxiv.org/abs/2203.14360 ; results https://github.com/noahcao/OC_SORT
16. Du et al. "StrongSORT: Make DeepSORT Great Again." IEEE TMM 2023. https://arxiv.org/abs/2202.13514
17. Aharon, Orfaig, Bobrovsky. "BoT-SORT: Robust Associations Multi-Pedestrian Tracking." arXiv 2022. https://arxiv.org/abs/2206.14651 ; https://github.com/NirAharon/BoT-SORT
18. Maggiolino et al. "Deep OC-SORT." ICIP 2023. https://arxiv.org/abs/2302.11813
19. Luiten et al. "HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking." IJCV 2021. https://arxiv.org/abs/2009.07736 ; TrackEval https://github.com/JonathonLuiten/TrackEval ; Dendorfer et al. "MOT20." arXiv 2020. https://arxiv.org/abs/2003.09003
20. Zhou, Yang, Cavallaro, Xiang. "Omni-Scale Feature Learning for Person Re-Identification" (OSNet). ICCV 2019. https://arxiv.org/abs/1905.00953
21. torchreid model zoo. https://kaiyangzhou.github.io/deep-person-reid/MODEL_ZOO
22. Luo et al. "Bag of Tricks and A Strong Baseline for Deep Person Re-identification." CVPRW 2019. https://arxiv.org/abs/1903.07071
23. He et al. "TransReID: Transformer-based Object Re-Identification." ICCV 2021. https://arxiv.org/abs/2102.04378 ; https://github.com/damo-cv/TransReID
24. Li, Sun, Li. "CLIP-ReID." AAAI 2023. https://arxiv.org/abs/2211.13977
25. Chen et al. "Beyond Appearance: a Semantic Controllable Self-Supervised Learning Framework for Human-Centric Visual Tasks" (SOLIDER). CVPR 2023. https://arxiv.org/abs/2303.17602
26. Qian et al. "Long-Term Cloth-Changing Person Re-identification" (LTCC). ACCV 2020. https://arxiv.org/abs/2005.12633
27. Gu et al. "Clothes-Changing Person Re-identification with RGB Modality Only" (CAL). CVPR 2022. https://openaccess.thecvf.com/content/CVPR2022/papers/Gu_Clothes-Changing_Person_Re-Identification_With_RGB_Modality_Only_CVPR_2022_paper.pdf
28. AI City Challenge. https://www.aicitychallenge.org/
29. Hou, Zheng, Gould. "Multiview Detection with Feature Perspective Transformation" (MVDet). ECCV 2020. https://arxiv.org/abs/2007.07247
30. Lv, Zhao, Nevatia. "Camera Calibration from Video of a Walking Human." IEEE TPAMI 28(9), 2006. https://doi.org/10.1109/TPAMI.2006.178
31. Fabbri et al. "MOTSynth: How Can Synthetic Data Help Pedestrian Detection and Tracking?" ICCV 2021. https://arxiv.org/abs/2108.09518
32. Ebadi et al. "PeopleSansPeople: A Synthetic Data Generator for Human-Centric Computer Vision." arXiv 2021. https://arxiv.org/abs/2112.09290
33. Black et al. "BEDLAM." CVPR 2023. https://arxiv.org/abs/2306.16940
34. Tobin et al. "Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World." IROS 2017. https://arxiv.org/abs/1703.06907
35. Sun, Zheng. "Dissecting Person Re-identification from the Viewpoint of Viewpoint" (PersonX). CVPR 2019. https://arxiv.org/abs/1812.02162
36. Wang, Liang, Liao. "Cloning Outfits from Real-World Images to 3D Characters for Generalizable Person Re-Identification" (ClonedPerson). CVPR 2022. https://arxiv.org/abs/2204.02611
37. Herzog et al. "Synthehicle: Multi-Vehicle Multi-Camera Tracking in Virtual Cities." arXiv 2022. https://arxiv.org/abs/2208.14167
38. NVIDIA TensorRT documentation. https://docs.nvidia.com/deeplearning/tensorrt/
39. Lu et al. "RTMPose." arXiv 2023. https://arxiv.org/abs/2303.07399

In-repo: docs/11, docs/12 (batch_v4), docs/13, docs/15; research R01, R02, R04, H01.
