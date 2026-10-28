# 25 · Detection Deep Dive: anchors, YOLOv8/11, RT-DETR, small objects, INT8, calibration and reading our recall tables

while writing this (see References). Anything not fetched is tagged **[VERIFY]**. Arithmetic
of my own is tagged **[derived]**. Where it touches the repo it names the file.*

Cross-references: detector families and the 20–60 px band are also covered in
`18_PERCEPTION_STACK.md` §1.2–1.4 and §8 (export/quantisation); history in
`R01_detection_and_single_camera_tracking.md` §2.3–2.5. This document does not repeat
those surveys. It goes one level deeper into *how the detectors actually compute their
outputs and losses*, and *how to read the numbers this repo produces*.

---

## 0. The one-paragraph version

A detector maps an image to a set of (box, class, score) triples. There are three ways to
get that set. **Anchor-based** detectors tile the image with template boxes and learn to
correct them (RetinaNet [7]). **Anchor-free** dense detectors predict a box directly from
every feature-map cell (FCOS [8], and the YOLOv8/YOLO11 head [10][11]). Both produce many
duplicate predictions per object, so they need **NMS**. **DETR-family** detectors predict a
fixed-size *set* and train it against the ground truth with a one-to-one **Hungarian
matching** [1], so no NMS is needed (RT-DETR made this real-time [2]). Most CCTV problems
are about people who are *small*, so the practical choices are input resolution, stride of
the finest pyramid level, and tiling (SAHI [15]). Deployment brings INT8 quantisation [16],
which moves accuracy in ways you have to measure. The scores these detectors emit are
**not probabilities** until you calibrate them [18][19]. And "mAP" is a specific, 101-point,
10-IoU-threshold average [20] that is not the same thing as the fixed-threshold
"recall@height" our own tools report.

---

## 1. Three ways to produce a set of boxes

### 1.1 The underlying problem

Intuition: the number of objects in an image is unknown and variable, but a neural network
emits a tensor of fixed shape. Every detector design answers one question: *how do I turn a
fixed-shape output into a variable-size set, and how do I decide which output is responsible
for which ground-truth object during training?* That second question, **label assignment**,
is where most of the progress since 2019 has come from.

### 1.2 Anchor-based (RetinaNet as the archetype)

- Put `A` template boxes ("anchors") at every location of every pyramid level. RetinaNet uses
  **9 anchors per location** (3 scales × 3 aspect ratios) on levels **P3–P7** [7].
- Training assignment is by IoU against ground truth. An anchor that overlaps a GT box enough
  is a positive, one with little overlap is a negative, and the band in between is ignored
  (RetinaNet: IoU ≥ 0.5 positive, IoU < 0.4 background, 0.4–0.5 ignored [7]).
- The network regresses offsets from the anchor to the box, and a class score per anchor.
- The result is roughly **100k candidate locations per image with a ~1:1000
  foreground:background imbalance** [7]. The easy negatives swamp the loss. **Focal loss**
  fixes that:

  FL(p_t) = −α_t (1 − p_t)^γ log(p_t), with γ = 2 and α = 0.25 working best [7].

  Worked number **[derived]**: an easy background anchor with p_t = 0.99 has a modulating
  factor (0.01)² = 10⁻⁴, so it contributes 10,000× less than under plain cross-entropy. A hard
  one with p_t = 0.5 is only damped 4×. RetinaNet reached **39.1 AP** (ResNet-101-FPN) [7].

The weakness for CCTV: anchor scales and aspect ratios are hyperparameters tuned to the
dataset. A camera 45 m away (our `street_crowd_far` rigs) produces 14–40 px people
(docs/12, batch_v5 notes). If no anchor is small enough, no anchor reaches positive IoU
with those boxes, so they are never trained as positives.

### 1.3 Anchor-free dense (FCOS, then YOLOv8/11)

FCOS does "per-pixel prediction, analogue to semantic segmentation". It removes anchor
hyperparameters and the anchor-IoU computation, and reached 44.7% AP [8]. Each cell whose
centre falls inside a GT box predicts the four distances (l, t, r, b) from itself to the box
edges. YOLOv8 describes its head as an **"anchor-free split Ultralytics head"** [10]:
separate branches for box and class, each predicting per cell. Intuitively, anchor-free
means *"the anchor is a point, not a box"*. The prior on shape is gone, and assignment
becomes a question of which *points* should own which object.

### 1.4 Set prediction (DETR, then RT-DETR)

DETR "views object detection as a direct set prediction problem", with no NMS and no anchor
generation [1]. It has a fixed number of learned **object queries**, **N = 100** [1]. A
transformer decoder turns each query into (class or ∅ "no object", box). Training finds the
**one-to-one assignment** σ between the predictions and the ground truth (padded with ∅)
that minimises a matching cost built from −p̂_σ(i)(c_i) plus a box loss for every non-∅
target [1]. The Hungarian algorithm solves this exactly. Because each GT object gets exactly
one prediction, the loss itself penalises duplicates, and the network learns not to produce
them. That is why no NMS is needed.

Costs, from the paper [1]:
- Training is slow: **300 epochs** for ablations and **500** for the main results (the longer
  schedule adds ~1.5 AP).
- Small objects suffer. With ResNet-50, DETR ties Faster R-CNN-FPN at **42.0 AP** (the
  enhanced "Faster RCNN-FPN+" row), but its **AP_S is 20.5 vs 26.6**, while its AP_L is
  **61.1 vs 53.4** (vs the plain Faster RCNN-FPN row: 40.2 AP, AP_S 24.2, AP_L 52.0). Global attention helps large
  objects. Running only on a coarse single-scale feature hurts small ones.

For surveillance that small-object trade-off is the one that matters. Section 3 returns to it.

### 1.5 RT-DETR: the DETR family at YOLO speeds

RT-DETR [2] keeps set prediction and fixes the speed:
- **Efficient hybrid encoder.** It "decouples intra-scale interaction and cross-scale
  fusion". Self-attention (AIFI) runs **only on the highest-level feature**, which is small
  and semantically rich. Multi-scale fusion (CCFF/CCFM) is done with convolutions [2].
  Intuition: attention costs O(tokens²), and the stride-8 map has 16× more tokens than the
  stride-32 map **[derived]**. Spending attention only where it is cheap and useful is
  the whole trick.
- **Uncertainty-minimal query selection.** The initial decoder queries are the encoder
  features ranked on classification *and* localisation quality, not class confidence alone [2].
  (The query count of 300 is widely quoted but I did not confirm it in the fetched text
  **[VERIFY]**.)
- **Speed can be tuned after training** by dropping decoder layers, with no retraining [2].
- Results: **RT-DETR-R50 53.1 AP at 108 FPS, R101 54.3 AP at 74 FPS on a T4**. It is
  +2.2 AP over DINO-Deformable-DETR-R50 and 21× faster [2].
- **The NMS point.** The authors built an *end-to-end* speed benchmark because NMS time
  "depends significantly on confidence and IoU thresholds". It is a hidden cost that YOLO
  speed tables typically leave out [2]. In a crowd (MOT20 has >100 people per frame; see
  docs/13), NMS time grows with the number of candidate boxes, and a latency quoted
  model-only understates the real cost.

---

## 2. YOLOv8 / YOLO11 in detail

### 2.1 Backbone, neck, head

- **Backbone**: a CSP-style conv net that produces features at strides 8, 16 and 32 (P3, P4,
  P5). YOLO11 changes the blocks (C3k2, plus a C2PSA attention block) and claims **22% fewer
  parameters for YOLO11m than YOLOv8m at higher accuracy** [11]. The block names are
  from the Ultralytics docs page. I did not verify their internals **[VERIFY]**.
- **Neck**: an FPN/PAN-style top-down plus bottom-up fusion. FPN's idea [9] is to build "a
  feature pyramid with high-level semantics throughout". The coarse map is upsampled ×2 and
  added to a 1×1-projected lateral connection from the backbone, then smoothed with a 3×3.
  In the FPN paper this raised small-object proposal recall **AR_s from 32.0 to 44.9
  (+12.9)** [9]. Both the top-down path and the lateral connections are needed [9].
- **Head**: decoupled ("split") branches per level [10]. The class branch gives one logit
  per class per cell. The box branch gives, for each of the four sides, a *distribution*
  over `reg_max` bins (next section).
- **Scaling**: the n/s/m/l/x variants share one YAML with depth/width multipliers. For `n`
  these are **[0.33, 0.25, 1024]** (depth, width, max channels) [14].

Published COCO numbers (val, 640 px): **YOLOv8n 37.3 mAP50-95** at 0.99 ms *A100* TensorRT (not T4), and
**YOLOv8x 53.9** at 68.2 M parameters [10]. **YOLO11n 39.5 mAP** with 2.6 M parameters, and
**YOLO11x 54.7**, at **1.5–11.3 ms on T4 TensorRT10** [11]. (The page does not state the
precision of the T4 timing; FP16 is the usual Ultralytics export but that is **[VERIFY]**.)

### 2.2 Box regression as a distribution: DFL

Intuition. A single regressed number says "the left edge is 3.4 cells away" with no way to
say "I'm unsure, it's 3 or 4". If an edge is occluded (a person behind a bollard), a
bimodal or flat distribution is the honest answer. GFL [3] replaces the Dirac-delta target
with a **general discrete distribution**:

- Discretise the range [y_0, y_n] into n+1 values with spacing Δ (typically 1). Predict
  softmax probabilities S_i. The estimate is **ŷ = Σ_j P(y_j) y_j** [3].
- **Distribution Focal Loss** pushes mass onto the two bins that bracket the target y:

  DFL(S_i, S_{i+1}) = −((y_{i+1} − y) log S_i + (y − y_i) log S_{i+1}) [3].

- In Ultralytics, `reg_max` bins are projected with `proj = arange(reg_max)`, and DFL is on
  when `reg_max > 1` [12]. The default is **`reg_max=16`** (`Detect.__init__` in
  `ultralytics/nn/modules/head.py`, and `BboxLoss(reg_max=16)`) (GFL itself
  recommends n ≈ 14–16 [3]).

Worked number **[derived]**: target distance 3.4 (in stride units). y_i = 3 and
y_{i+1} = 4, so the loss wants S_3 = 0.6 and S_4 = 0.4, and 0.6·3 + 0.4·4 = 3.4. At
stride 8 that is 27.2 px. With 16 bins (0…15) the *largest* distance a cell can express is
15 strides: 120 px at P3, 480 px at P5. That caps box size per level, and it is why big
objects must be owned by coarse levels.

### 2.3 IoU-family box loss: CIoU

Plain 1 − IoU has zero gradient when boxes do not overlap and is blind to *where* the
mismatch is. DIoU adds a normalised centre distance. CIoU also adds aspect ratio [5]:

- L_DIoU = 1 − IoU + ρ²(b, b^gt)/c². Here ρ is the distance between the centres and c is the
  diagonal of the smallest enclosing box [5].
- L_CIoU = L_DIoU + αv, with v = (4/π²)(arctan(w^gt/h^gt) − arctan(w/h))² and
  α = v / ((1 − IoU) + v) [5].
- Ultralytics calls `bbox_iou(..., CIoU=True)` and uses `(1 − iou) * weight` [12].

Worked example **[derived]**: GT person box 10×20 px at x∈[0,10], y∈[0,20]. The prediction
is the same size shifted 2 px right. Intersection is 8×20 = 160 and union 240, so
IoU = 0.667. The centres are 2 px apart, so ρ² = 4. The enclosing box is 12×20, so
c² = 544 and ρ²/c² = 0.0074. The aspect ratios are equal, so v = 0. L_CIoU = 0.340. The
lesson for small people: **a 2 px error costs a third of the IoU on a 10 px-wide box.** A
20 px person can fail IoU ≥ 0.5 from sub-pixel-scale ambiguity. This is why our
recall@IoU0.5 collapses in the 20–60 px band (section 6).

DIoU also plugs into NMS. A box is suppressed only if IoU − R_DIoU ≥ ε, so two heavily
overlapping boxes whose centres are far apart (two people side by side) survive [5].

### 2.4 Classification loss: BCE with soft (quality) targets, and varifocal

Ultralytics uses **`BCEWithLogitsLoss`** [12]. The target is *not* 1 for positives. It is
a soft, IoU-aware value produced by the assigner (next section). This idea runs through
GFL's **Quality Focal Loss**, QFL(σ) = −|y − σ|^β((1−y)log(1−σ) + y log σ) with y the IoU
and β = 2 [3], and VarifocalNet's **varifocal loss** [6]:

VFL(p, q) = −q(q log p + (1−q) log(1−p)) if q > 0; −α p^γ log(1−p) if q = 0 [6].

Here q is the IoU for foreground and 0 for background. Unlike focal loss, only
*negatives* are down-weighted, and positives are *weighted up by their IoU* [6]. RT-DETR's
reference implementation uses varifocal loss for classification **[VERIFY]**. The
"is this a person"**. So a confidence of 0.36 on a small, blurry person (docs/12 records a
mean of **0.356** on stylised figures) is partly the model saying "the box will be poor",
and not only "not a person". That is one reason calibration (section 5) is not optional.

### 2.5 Label assignment: the task-aligned assigner (TAL)

TOOD's insight [4] is that the anchor with the best classification score and the anchor
with the best box are often different cells. Train so that they coincide. The alignment
metric is

**t = s^α · u^β**, where s is the class score and u the IoU [4].

TOOD selected **α = 1, β = 6, top m = 13** positives per instance [4]. Ultralytics
uses **topk = 10, α = 0.5, β = 6.0** [12]. The normalised t̂ (its maximum within each
instance is set to that instance's largest IoU) replaces the binary label in the
classification loss [4]. TOOD reached 51.1 AP [4].

Worked example **[derived]**, Ultralytics settings. Cell A has s = 0.8, u = 0.7, so
t = 0.894 × 0.118 = 0.105. Cell B has s = 0.4, u = 0.9, so t = 0.632 × 0.531 = 0.336. **B
wins by 3×** despite half the score. β = 6 makes IoU dominate, so training pulls
high-score predictions toward well-localised cells. The result is fewer
"confident-but-misplaced" boxes that NMS would otherwise keep over better ones.

### 2.6 Putting the loss together

Total = 7.5·L_box(CIoU) + 0.5·L_cls(BCE) + 1.5·L_DFL. These are the default gains
`box: 7.5, cls: 0.5, dfl: 1.5` [13], applied as `loss[i] *= hyp.*` [12].

### 2.7 Inference and NMS

Defaults: `conf` 0.25 for predict and **0.001 for val**, `iou` (NMS) **0.7**,
`max_det` 300, `imgsz` 640 [13]. Two things matter here:

1. **val uses conf 0.001 on purpose.** AP integrates over *all* thresholds, so low-score
   detections must be kept to trace the tail of the PR curve. A mAP measured at conf 0.25 is
   a truncated, lower number **[derived from the definition in §4]**. Our docs/13 baseline
   uses conf ≥ 0.01 and `maxDets=1000` for exactly this reason (MOT20 frames hold >100
   people, and COCO's default cap of 100 [20] silently limits recall).
2. **Greedy NMS in crowds.** Sort by score and keep the top box. Delete any remaining box
   with IoU > 0.7 against it, then repeat. Two people walking shoulder-to-shoulder whose boxes
   overlap at IoU 0.75 become one detection. No threshold is right for both a sparse car park
   and a dense concourse. DIoU-NMS [5] or a set-prediction model [1][2] is the principled
   fix.

---

## 3. Small objects: what actually helps, from first principles

### 3.1 Count pixels per feature cell

A person H px tall at stride s covers H/s cells vertically. Our 720p frames
(CLAUDE.md) are resized to 640 on the long side by `imgsz=640` [13], a factor of
0.5 **[derived]**. So a 20 px GT person (our `usably_visible` floor) is **10 px at network
input, 1.25 cells at stride 8 and 0.3 cells at stride 32** **[derived]**. Only P3 has any
chance. The receptive field of that cell is mostly background. Three levers follow.

### 3.2 Lever 1: input resolution

Run at `imgsz=1280`. docs/13 does this for YOLO11n. That doubles pixels on target and
costs ~4× the FLOPs **[derived: quadratic in side length]**. It is the cheapest lever to try
and the most expensive to deploy.

### 3.3 Lever 2: a finer pyramid level (P2, stride 4)

`yolov8-p2.yaml` adds a P2/4 output. The head reads **P2/4, P3/8, P4/16, P5/32** [14].
FPN's original design already had anchors of area **32² on P2** up to 512² on P6, and
assigned RoIs by k = ⌊k₀ + log₂(√(wh)/224)⌋ with k₀ = 4 [9]. The formula shows the logic:
every halving of object size drops one pyramid level. A 20 px object wants a level two
below a 80 px one **[derived]**. P2 costs memory: its map has 4× the cells of P3.

### 3.4 Lever 3: tiling (SAHI)

SAHI [15] slices the image into overlapping patches, upsamples each to network size, detects
on each, and merges back with NMS, optionally adding a full-image pass [15]. It used
**640×640 slices on VisDrone, 400×400 on xView, 25% overlap** [15]. AP50 gains on VisDrone
from sliced inference alone were **FCOS +6.8, VFNet +5.1, TOOD +5.3**. With
slicing-aided fine-tuning as well: **+12.7 / +13.4 / +14.5** [15].

Costs **[derived]**. A 1280×720 frame in 640×640 tiles at 25% overlap needs 3×2 = 6 tiles
plus the full pass, about 7× compute. Cross-tile duplicates and cut people (half a body in
each tile) have to be merged. SAHI's NMS merge also inherits the crowd problem of §2.7.

### 3.5 Lever 4 (anchor-based only): anchor size and stride

If you must use anchors, the smallest anchor must be able to reach positive IoU with your
smallest target. The regression cap of §2.2 is the anchor-free analogue.

### 3.6 Lever 5: train on the size distribution you deploy at

The largest lever is data. A COCO-pretrained nano model has seen few 20 px people. This is
the main argument for SurvSim: matched pixel-height distributions (docs/13, "Real-vs-synthetic
gap protocol", point 2).

---

## 4. What mAP, AP50, AP50:95 and recall actually mean

### 4.1 Definitions (COCO / pycocotools)

- Precision = TP/(TP+FP). Recall = TP/(TP+FN). A detection is a TP if it matches an unmatched
  GT of the same class at IoU ≥ threshold. Matching is greedy in score order.
- **IoU thresholds**: 10 values, 0.50:0.05:0.95 [20].
- **Recall sampling**: **101 points**, 0.00:0.01:1.00 [20].
- **maxDets** [1, 10, 100] and **area ranges**: small < 32², medium 32²–96², large > 96² [20].
- **Interpolation**: precision is made monotone non-increasing by a backward sweep
  (`if pr[i] > pr[i-1]: pr[i-1] = pr[i]`). The value at each recall threshold is found with
  `searchsorted(rc, recThrs, side='left')` [20]. A recall level never reached contributes 0.
- **AP** for one class at one IoU is the mean of those 101 interpolated precisions. "AP" or
  "mAP" or "AP50:95" in COCO parlance is that mean over the 10 IoU thresholds (and over
  classes) [20][21]. **AP50** uses IoU 0.5 only, **AP75** 0.75 only.

Intuition. AP50 asks "did you find it?". AP75 asks "did you box it tightly?". AP50:95
rewards both. For CCTV person detection, **AP50 is closer to the operational question**.
A tracker and a loiter rule tolerate a loose box but not a missing person. AP75 on 20 px
people is dominated by annotation and pixel quantisation noise (§2.3 worked example).

### 4.2 A worked AP computation

One class, 5 GT people, 8 detections sorted by score, with match outcome at IoU 0.5:

| rank | score | TP/FP | cum TP | cum FP | precision | recall | interp. P |
|---|---|---|---|---|---|---|---|
| 1 | .95 | TP | 1 | 0 | 1.000 | 0.2 | 1.000 |
| 2 | .90 | TP | 2 | 0 | 1.000 | 0.4 | 1.000 |
| 3 | .80 | FP | 2 | 1 | 0.667 | 0.4 | 0.750 |
| 4 | .70 | TP | 3 | 1 | 0.750 | 0.6 | 0.750 |
| 5 | .60 | FP | 3 | 2 | 0.600 | 0.6 | 0.667 |
| 6 | .50 | TP | 4 | 2 | 0.667 | 0.8 | 0.667 |
| 7 | .40 | FP | 4 | 3 | 0.571 | 0.8 | 0.571 |
| 8 | .30 | FP | 4 | 4 | 0.500 | 0.8 | 0.500 |

"Interp. P" is the max precision at this rank or later (the backward sweep).

COCO 101-point sampling **[derived]**:
- r = 0.00…0.20 (21 points): first rank with recall ≥ r is rank 1, giving 1.0.
- r = 0.21…0.40 (20 points): rank 2, giving 1.0.
- r = 0.41…0.60 (20 points): rank 4, giving 0.75.
- r = 0.61…0.80 (20 points): rank 6, giving 0.667.
- r = 0.81…1.00 (20 points): never reached, giving 0.

AP = (21 + 20 + 15 + 13.33) / 101 = **0.686**. The all-point area version (VOC 2010+ style)
gives 0.2·(1 + 1 + 0.75 + 0.667) = 0.683. They are close. The 101-point version gives a
little extra weight to the r = 0 point.

Lessons:
- **The missed person (recall capped at 0.8) cost ~0.2 AP.** No threshold can recover it.
  That is the small-person failure mode.
- **Adding more low-score FPs after the last TP does not change AP.** Rows 7–8 did nothing.
  That is why AP flatters a system that would drown an operator. CLAUDE.md principle 4 and
  docs/13's "false alarms per camera-hour" operating point exist for exactly this.
- Repeat at IoU 0.55…0.95. A slightly loose box that is a TP at 0.5 becomes an FP *and* leaves
  an FN at 0.75. Averaging gives AP50:95.

### 4.3 Reading docs/13's MOT20 row

YOLO11n zero-shot on the MOT20-01/02 subset: **AP 0.348, AP50 0.730, AP75 0.293** (docs/13).
The large AP50 → AP75 drop says the detector *finds* most people but *boxes* them
loosely. In dense, occluded crowds, GT boxes cover the full body extent (occluded parts
included) while the detector boxes the visible part. docs/13 is candid that its "right
ballpark" comparison is from memory, not a cited paper. Treat that sentence as
**[VERIFY]**.

---

## 5. Confidence calibration

### 5.1 What calibrated means

A model is calibrated if, among detections scored 0.7, 70% are correct. Guo et al. showed
that **modern deep nets are overconfident**. Depth, width, BatchNorm and less weight decay
all make it worse [18].

**ECE** bins predictions into M equal-width confidence bins [18]:

ECE = Σ_m (|B_m|/n) · |acc(B_m) − conf(B_m)|.

Worked **[derived]**, 3 bins, 100 detections:
- bin [0.3, 0.6): 40 detections, mean conf 0.45, 30% correct, gap 0.15
- bin [0.6, 0.8): 30 detections, mean conf 0.70, 60% correct, gap 0.10
- bin [0.8, 1.0]: 30 detections, mean conf 0.90, 85% correct, gap 0.05

ECE = 0.4·0.15 + 0.3·0.10 + 0.3·0.05 = **0.105**.

### 5.2 Temperature scaling

Divide the logits by a single scalar T > 0 fitted by minimising NLL on held-out data. It
**does not change accuracy**, because the argmax is unchanged [18]. On ResNet-110/CIFAR-100
it took ECE from **16.53% to 1.26%** [18]. For a sigmoid detector the analogue is
p = σ(z/T) **[derived]**. It preserves ranking, so **AP is unchanged**. Only the meaning of
the threshold changes.

### 5.3 Why detection calibration is harder

In detection, "accuracy" means precision at an IoU, and miscalibration *depends on box
position and scale*. Küppers et al. proposed calibration conditioned on box location and
size, with a detection-specific miscalibration measure (D-ECE) [19]. For CCTV this is the
key point. A single T fitted on a dataset dominated by 150 px people will be wrong for
25 px people. **Calibrate per height band, and per camera if you can.** SurvSim gives you
exact TP/FP labels at every height (`usably_visible`, mask-derived boxes), so it can fit
such calibrators. Whether they transfer to real footage is a sim-to-real question (doc 24).

### 5.4 Why an operator cares

An alarm rule "person in zone with conf > 0.5 for 20 s" only means the same thing on every
camera if 0.5 does. An uncalibrated far camera with systematically low scores looks
"quiet" (misses). A near one looks "noisy". Calibration is how one threshold becomes a
fleet-wide policy.

---

## 6. Quantisation and TensorRT

### 6.1 The mechanism

Map real x to an 8-bit integer q = round(x/s), clipped to [−127, 127]. **Scale
quantisation** (symmetric, no zero-point) is cheapest. **Affine** adds a zero-point, which
"can introduce considerable overhead, reducing or even eliminating the throughput
advantage" [16]. TensorRT uses a **symmetric scheme** for weights and activations [17]. Wu
et al. recommend **per-channel symmetric max-calibrated weights and per-tensor activations**
[16]. Weights need per-channel scales because BN folding gives channels very different
ranges [16].

### 6.2 Calibration (choosing s for activations)

Three methods [16]:
- **max**: s = max|x|/127. Outlier-sensitive.
- **entropy/KL**: minimise the information lost between the FP32 and quantised histograms.
- **percentile**: clip at the 99.99–99.9999th percentile.

**No single method won everywhere** [16].

Worked **[derived]**. An activation with max 20 has s = 20/127 = 0.157. Every value below
0.079 rounds to 0. Clip at a 99.99th percentile of 6 and s = 0.047, so resolution is 3.3×
finer, but the rare values above 6 saturate. Detection makes this sharp in two ways. Box
regression outputs need fine resolution (§2.3: 2 px is a third of the IoU on a small
person), and the class logits that separate a 0.2 score from a 0.3 score for a small person
live in the low range that max-calibration crushes. **Expect INT8 to hurt small objects
first.** Verify per height band, not on overall mAP. The calibration set should also look
like deployment: night frames, rain, far cameras. SurvSim + `sensors/degrade.py` can
generate such a set on demand.

### 6.3 PTQ vs QAT

- **PTQ**: calibrate a trained model with a few hundred representative images and build
  the engine. Fast, but can lose accuracy.
- Recovery ladder [16]: first **partial quantisation**, keeping sensitive layers (often the
  first conv and the detection head) in FP16/FP32. Then **QAT**, fine-tuning with fake
  quantisation for **~10% of the original training steps**. With this workflow Wu et al.
  kept all tested networks **within 1% of the FP32 baseline**, including hard cases such
  as MobileNets and BERT-large [16].
- TensorRT supports both PTQ and QAT. Explicit Q/DQ-node networks carry the quantisation in
  the graph. Current formats include INT8, FP8 (E4M3), FP4 and weight-only INT4 [17].
  The specific calibrator class names (e.g. `IInt8EntropyCalibrator2`) were not on the
  fetched page **[VERIFY]**.
- Ultralytics exports with `int8`/`fp16` quantisation options [13].

### 6.4 What to measure

Measure the FP32 → FP16 → INT8 deltas in AP50, recall in the 20–60 px band, and ECE, plus
*end-to-end* latency including NMS at the deployed conf threshold (RT-DETR's point [2]).
Also re-fit the temperature after quantising, because quantisation shifts the logits
**[derived]**. docs/18 §8 covers the edge-hardware side.

---

## 7. How to read the recall tables in docs/12 and docs/13

### 7.1 What `tools/eval_recall.py` computes

The code (read in full, 129 lines; re-read at audit, 2026-09-26):
- For each camera it takes `n` evenly spaced frames (default 5, `--n 10` in the tables) that
  contain at least one GT person **≥ 20 px tall** (`MIN_H = 20.0`, matching
  `geometry.usably_visible`).
- It runs YOLO `model.predict(conf=0.25, classes=[0])`, person only, at the **default
  imgsz 640** [13] (not set, so it inherits). The default model is **yolov8n** (a local
  `yolov8n.pt`, falling back to the hub name).
- **Matching is now COCO-style: detections in descending score order** (`match_frame`).
  Each detection claims its best-IoU unclaimed GT box, and is a TP if IoU ≥ 0.5, else an FP.
  It *used to* be greedy by GT height, tallest first; the file's docstring says any recall
  numbers recorded before that fix (the docs/12 tables) are on the old matching order.
  At a single threshold the two usually agree, but in crowds they can differ **[derived]**.
- recall = TP/(TP+FN). precision = TP/(TP+FP) with FP = all unmatched detections.
- `recall_by_height` bands are **20–60, 60–120 and 120+ px**.

### 7.2 What the numbers are, and are not

1. **An operating point, not AP.** It is one threshold (0.25) and one IoU (0.5). It is
   "recall@0.25, IoU 0.5", comparable to one point on the §4.2 curve. It cannot be compared
   with docs/13's AP numbers. Those use YOLO11n, imgsz 1280, conf ≥ 0.01 and pycocotools.
2. **Precision is pessimistic.** GT below 20 px is dropped, but detections of those people
   still count as FPs **[derived from code]**. On the far cameras (14–40 px people) some
   "false positives" are real people.
3. **Small samples.** With 10 frames per camera, a camera with ~20 GT boxes at recall 0.5 has
   a binomial standard error of √(0.25/20) ≈ 0.11 **[derived]**. Neighbouring frames are
   correlated, so the effective n is smaller. docs/12 itself calls the batch_v5 → v6 change
   "flat within noise". Differences of ±0.1 on a single camera mean nothing. The pooled
   rows (1,070 GT boxes, SE ≈ 0.015 **[derived]**) are meaningful.
4. **Height explains most of the variance.** docs/12 says people ≥ 120 px are found at
   0.75–1.0 and the misses are the 20–60 px figures. By §3.1, a 20–60 px person at 720p
   is 10–30 px at network input, at most ~4 cells at P3. cam_yard (all < 60 px) scores
   0.0–0.3. street_crowd_far cam_02 (people 45–60 m away) scores **0.0**.
5. **Controlled comparisons are the valuable rows.** The CesiumMan → MetaHuman table holds
   runs, cameras and GT fixed and changes only the character. Pooled recall went
   **0.577 → 0.758** (770 boxes). At a matched 50 px height, mean confidence went
   0.439 → 0.634 and recall@0.25 went 0.72 → 0.96 (docs/12). That is a genuine,
   height-controlled appearance effect, the kind of controlled experiment real CCTV cannot
   run. By contrast, batch_v4 0.758 vs batch_v5 0.678 is *not* a regression. The set
   changed: 300 far-camera boxes were added, and excluding them gives 0.734 (docs/12 says
   so explicitly).
6. **Night vs day** in batch_v6: street_crowd 0.866 → 0.810, disguise 0.631 → 0.495. The
   drop is concentrated in small-person cameras. This fits the view that low light
   pushes marginal detections below the 0.25 cutoff first **[derived]**. docs/12 notes
   there is no *real* night reference yet (docs/15). So "is this drop realistic?" is open.
7. **The `detector_recall` render gate** (`check_render.py --detector --min-recall`) uses this
   number as a *render-validity* check ("renders a detector cannot use"), not as a model
   benchmark. That is the right use of a zero-shot nano model.

### 7.3 How to make these tables stronger (things to propose)

- Report recall at a **fixed FP rate** (false alarms per camera-hour, as in `eval.detection`)
  rather than fixed conf.
- Add bootstrap CIs over frames.
- Run at imgsz 1280 and with SAHI to separate "the model can't see it" from "it was
  downsampled away".
- Report AP50 per height band with pycocotools area ranges re-cut to *height* (COCO's
  32²/96² area bins are the wrong axis for upright people).
- Report ECE per band (§5).

---

## 8. Choosing a detector for CCTV: a defensible answer

- **Edge box, many streams, mostly medium-size people**: a YOLO11s/m-class anchor-free model
  with TensorRT FP16. Go to INT8 only after a per-band recall check, and re-calibrate. NMS
  IoU tuned per site.
- **Wide-area, far cameras**: add P2 or tile (SAHI) *on the cameras that need it*. Don't
  pay 7× on every stream. A per-camera config derived from rig analysis
  (`survsim rig` reports the pixel heights each camera produces) tells you which ones.
- **Dense crowds, GPU server**: RT-DETR. No NMS means no crowd-merging errors and stable
  end-to-end latency [2]. But check AP_S. The DETR lineage is weakest on small objects
  [1], and RT-DETR's multi-scale encoder exists to recover that.
- In every case, calibrate per height band [18][19] and report operational metrics.

---


- "Every detector answers two questions: how to turn a fixed tensor into a variable set, and
  who is responsible for which object during training. Anchors, anchor-free points and
  Hungarian matching are three answers. NMS is the price of answering one-to-many."
- "YOLOv8/11 is anchor-free. BCE on an IoU-aware soft target, CIoU plus DFL for the box, a
  task-aligned assigner with t = s^0.5·u^6 so the best-scored cell is also the best-boxed
  one, then NMS at IoU 0.7."
- "DFL predicts a distribution over edge distances instead of one number, so the model can
  express uncertainty about an occluded edge."
- "RT-DETR keeps DETR's set prediction but runs attention only on the coarsest map, which
  gets it to 53 AP at 108 FPS on a T4 with no NMS. NMS isn't free in crowds, and latency
  tables usually hide it."
- "Small people are a pixels-per-cell problem. A 20 px person in a 720p frame at imgsz 640
  is about one cell at stride 8. Raise the resolution, add P2, or tile with SAHI. Each costs
  compute, so apply it per camera."
- "AP50:95 is 101-point interpolated precision averaged over ten IoU thresholds. I can
  compute one by hand. A missed object caps recall and costs AP that no threshold recovers,
  and trailing false positives cost nothing, which is why I also report false alarms per
  camera-hour."
- "Scores aren't probabilities. Temperature scaling fixes it without touching AP, but
  detection miscalibration depends on box size, so calibrate per height band."
- "INT8: symmetric per-channel weights and per-tensor activations. Calibration method
  matters, and small objects degrade first. Recovery is partial quantisation, then QAT for
  ~10% of the training steps."
- On our repo: "Our recall tables are a single operating point on ten frames per camera. I
  trust the pooled and the controlled rows. MetaHuman vs CesiumMan at matched height was
  0.577 to 0.758 recall. Single-camera deltas of 0.1 are noise."

---

## References

[1] Carion et al., "End-to-End Object Detection with Transformers" (DETR), ECCV 2020.
https://arxiv.org/abs/2005.12872 and https://ar5iv.labs.arxiv.org/html/2005.12872. Taken:
set prediction/Hungarian matching and the cost form, N = 100 queries, 300/500-epoch
schedules (+1.5 AP), R50 AP 42.0 vs Faster R-CNN 42.0, AP_S 20.5 vs 26.6, AP_L 61.1 vs 53.4.

[2] Zhao et al., "DETRs Beat YOLOs on Real-time Object Detection" (RT-DETR), CVPR 2024.
https://arxiv.org/abs/2304.08069 and https://ar5iv.labs.arxiv.org/html/2304.08069. Taken:
hybrid encoder (AIFI on high-level features, CCFF), uncertainty-minimal query selection,
decoder-layer speed tuning, R50 53.1 AP/108 FPS and R101 54.3 AP/74 FPS on T4, +2.2 AP and
21× faster than DINO-Deformable-DETR-R50, NMS time depending on thresholds.

[3] Li et al., "Generalized Focal Loss" (GFL), NeurIPS 2020. https://arxiv.org/abs/2006.04388,
https://ar5iv.labs.arxiv.org/html/2006.04388. Taken: QFL and DFL formulas, β = 2,
ŷ = ΣP(y_j)y_j, n ≈ 14–16, Δ = 1, 45.0/48.2 AP.

[4] Feng et al., "TOOD: Task-aligned One-stage Object Detection", ICCV 2021.
https://arxiv.org/abs/2108.07755, https://ar5iv.labs.arxiv.org/html/2108.07755. Taken:
t = s^α u^β, α = 1, β = 6, m = 13, normalised t̂ as soft label, 51.1 AP.

[5] Zheng et al., "Distance-IoU Loss", AAAI 2020. https://arxiv.org/abs/1911.08287,
https://ar5iv.labs.arxiv.org/html/1911.08287. Taken: DIoU and CIoU formulas (v, α), DIoU-NMS.

[6] Zhang et al., "VarifocalNet: An IoU-aware Dense Object Detector", CVPR 2021.
https://ar5iv.labs.arxiv.org/html/2008.13367. Taken: VFL formula, IACS, asymmetric
down-weighting of negatives only.

[7] Lin et al., "Focal Loss for Dense Object Detection" (RetinaNet), ICCV 2017.
https://ar5iv.labs.arxiv.org/html/1708.02002. Taken: FL formula, γ = 2, α = 0.25, ~100k
locations and ~1:1000 imbalance, 9 anchors per location on P3–P7, 39.1 AP.

[8] Tian et al., "FCOS", ICCV 2019. https://arxiv.org/abs/1904.01355. Taken: per-pixel
anchor-free prediction, removes anchor hyperparameters, 44.7% AP.

[9] Lin et al., "Feature Pyramid Networks for Object Detection", CVPR 2017.
https://ar5iv.labs.arxiv.org/html/1612.03144. Taken: top-down plus lateral design, anchor areas
32²…512² on P2…P6, k = ⌊k₀ + log₂(√(wh)/224)⌋ with k₀ = 4, AR_s 32.0 → 44.9, +2.3 AP.

[10] Ultralytics, YOLOv8 docs. https://docs.ultralytics.com/models/yolov8/. Taken:
"anchor-free split head", YOLOv8n 37.3 mAP50-95 at 0.99 ms, YOLOv8x 53.9 at 68.2 M params.

[11] Ultralytics, YOLO11 docs. https://docs.ultralytics.com/models/yolo11/. Taken: 22% fewer
params for YOLO11m vs YOLOv8m, YOLO11n 39.5 mAP at 2.6 M params, YOLO11x 54.7, 1.5–11.3 ms
on T4 TensorRT.

[12] Ultralytics source, `ultralytics/utils/loss.py`.
https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/utils/loss.py.
Taken: TaskAlignedAssigner(topk = 10, alpha = 0.5, beta = 6.0), BCEWithLogitsLoss, CIoU box
loss, DFL with proj = arange(reg_max) when reg_max > 1, loss-gain multiplication.

[13] Ultralytics source, `ultralytics/cfg/default.yaml`.
https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/cfg/default.yaml.
Taken: box 7.5, cls 0.5, dfl 1.5, NMS iou 0.7, conf 0.25 predict / 0.001 val, imgsz 640,
max_det 300, int8/fp16 export.

[14] Ultralytics source, `cfg/models/v8/yolov8-p2.yaml`.
https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/cfg/models/v8/yolov8-p2.yaml.
Taken: Detect on P2/4, P3/8, P4/16, P5/32; n scale [0.33, 0.25, 1024].

[15] Akyon et al., "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection"
(SAHI), ICIP 2022. https://ar5iv.labs.arxiv.org/html/2202.06934. Taken: method, 640/400 px
slices, 25% overlap, NMS merge, VisDrone AP50 gains +6.8/+5.1/+5.3 and with fine-tuning
+12.7/+13.4/+14.5.

[16] Wu et al. (NVIDIA), "Integer Quantization for Deep Learning Inference: Principles and
Empirical Evaluation", 2020. https://ar5iv.labs.arxiv.org/html/2004.09602. Taken:
scale vs affine, per-channel weights and per-tensor activations, max/entropy/percentile
calibration with no universal winner, partial quantisation, QAT at ~10% of steps, within 1%.

[17] NVIDIA TensorRT docs, "Working with Quantized Types".
https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/work-with-quantized-types.html.
Taken: PTQ and QAT support, symmetric scheme, Q/DQ explicit quantisation, INT8/FP8/FP4/INT4.

[18] Guo et al., "On Calibration of Modern Neural Networks", ICML 2017.
https://ar5iv.labs.arxiv.org/html/1706.04599. Taken: ECE definition, temperature scaling fitted
by NLL, accuracy unchanged, ResNet-110/CIFAR-100 ECE 16.53% → 1.26%, overconfidence factors.

[19] Küppers et al., "Multivariate Confidence Calibration for Object Detection", CVPR-W 2020.
https://arxiv.org/abs/2004.13546. Taken: detection calibration conditioned on box position and
scale, a detection-specific miscalibration measure.

[20] COCO API, `pycocotools/cocoeval.py`.
https://raw.githubusercontent.com/cocodataset/cocoapi/master/PythonAPI/pycocotools/cocoeval.py.
Taken: iouThrs 0.5:0.05:0.95, 101 recThrs, maxDets [1, 10, 100], area ranges 32²/96², the
monotone precision sweep, searchsorted sampling.

[21] COCO detection evaluation page. https://cocodataset.org/#detection-eval. Taken: AP
averaged over IoU .50:.05:.95, AP50/AP75, and AP averaged over categories (= mAP).

Repo sources read: `tools/eval_recall.py`, `docs/12_UNREALCV_ENGINE_NOTES.md` (recall tables
for batches v3–v6, the detector_recall gate), `docs/13_BASELINES.md`, `CLAUDE.md`.
