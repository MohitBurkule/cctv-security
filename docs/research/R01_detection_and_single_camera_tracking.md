# R01 · Person Detection and Single-Camera Multi-Object Tracking in Real-World Surveillance Video

**Audience.** Whoever is going to argue about detection and tracking with a
customer's security manager, a VMS integrator, and a reviewer at CVPR, in the
same week. This is the dossier that lets you do that without bluffing.

**Scope.** Everything up to and including "one camera, many people, IDs held
over time". Cross-camera re-identification, multi-camera fusion, behaviour
classification and the simulator's own design live in sibling documents; this
one is the foundation they all sit on. Read along
[`docs/01_RESEARCH_LANDSCAPE.md`](../01_RESEARCH_LANDSCAPE.md) (what we reuse)
and [`docs/02_ARCHITECTURE.md`](../02_ARCHITECTURE.md) (where in SurvSim each
of these failure modes gets simulated).

> **Sourcing note — read this before you quote anything.** This pass was
> written under an egress policy that permitted web *search* but blocked direct
> fetching of arxiv.org, motchallenge.net, paperswithcode.com, vendor docs and
> most publisher sites. Every **quoted** string below is text returned by search
> against the cited source. Claims that are well established in the field but
> whose exact figures were **not** re-verified in this pass are explicitly
> marked `[unverified — confirm before external use]`. Claims that come from
> operational experience rather than a citable document are marked
> `[practitioner lore]`. Do not launder either category into a customer deck as
> if it were a measured number. That habit is what separates twenty years of
> experience from twenty years of confident wrongness.

---

## 1. The operational problem: what CCTV actually looks like

### 1.1 The gap between "pedestrian detection" and "surveillance"

Almost the entire academic pedestrian-detection literature is *automotive*.
Caltech, KITTI, CityPersons, EuroCity Persons — all recorded from a vehicle, at
eye height, with a forward-facing lens, in daylight, at a fixed and generous
resolution. EuroCity Persons is explicit that its images were "collected
on-board a moving vehicle in 31 cities of 12 European countries"
([EuroCity Persons](https://eurocity-dataset.tudelft.nl/)). Everything an
autonomous car cares about — a person 1.5 m off the bumper, filling 300 px of
image height, about to be hit — is the *easiest* case in surveillance and the
one you will almost never see.

Real CCTV is the opposite on every axis:

| Axis | Automotive benchmark | Real fixed CCTV |
|---|---|---|
| Viewpoint | eye level, forward | 3–6 m mount, 20–45° depression; ceiling domes near-nadir |
| Person pixel height | 50–300 px | 15–80 px across most of the useful field |
| Frame rate | 10–30 fps, constant | 4–15 fps typical recorded; drops under load; bursty |
| Compression | lossless / high bitrate | H.264/H.265 at 1–4 Mbps for 1080p, heavy on motion |
| Lighting | daylight, occasional night | 24 h incl. IR cut-filter switch, sodium/LED mix, backlight |
| Scene | street, transient | one scene forever; same shadows, same reflections, same bench |
| Density | a few pedestrians | zero for 23 h, then 200 in a queue |
| Duration | 30 s clips | continuous, years |

A practical consequence that the literature rarely states: in surveillance the
**dominant error source is not the classifier, it is the pixels on target**.
The industry's own rule of thumb is the "pixels per foot / pixels per metre"
spec used to size lenses — detection, classification, and identification are
different pixel-density regimes, and analytics vendors publish minimum target
heights in *percent of image height* for exactly this reason
`[practitioner lore; codified informally in IPVM-style specification threads such as [this discussion on specifying analytics false-alarm rate](https://ipvm.com/discussions/end-user-how-do-i-specify-video-analytics-performance-false-alarm-rate)]`.

### 1.2 Density and occlusion, in numbers

The MOTChallenge family is the standard reference for "how crowded is crowded".
The measured contrast between MOT17 and MOT20 is the single most useful pair of
numbers to have memorised:

* MOT17 — "contains 204,701 pedestrians spread across 5,316 frames, giving an
  average of 38 pedestrians per frame", and "on average, there are only 2.5
  pairs of pedestrians with an Intersection over Union (IOU) score greater
  than 0.4"
  ([MOT20 benchmark paper](https://arxiv.org/pdf/2003.09003), via search).
* MOT20 — "contains a total of 1,134,614 pedestrians distributed over 8,931
  frames, yielding an average of 127 pedestrians per frame", with "about 20
  pairs of pedestrians" above IoU 0.4, and "some of the new sequences show a
  pedestrian density of 246 pedestrians per frame". The dataset holds "circa 3
  times more bounding boxes for training and testing compared to MOT17"
  ([MOT20](https://arxiv.org/pdf/2003.09003)).

Read those together and you get the real lesson: **an 8× jump in crowding
produces an 8× jump in mutually-overlapping pairs**, which is the quantity that
actually breaks NMS and breaks association. Trackers that look excellent on
MOT17 routinely lose 10–20 HOTA points on MOT20, and the reason is combinatorial,
not perceptual.

For detection specifically, CrowdHuman is the reference crowd benchmark: "on
average there are ~22.6 persons per image", and it provides "a total of 470K
human instances from the train and validation subsets… with various kinds of
occlusions"
([CrowdHuman](https://arxiv.org/abs/1805.00123)). Its design choice matters more
than its size: CrowdHuman annotates **head box, visible box and full body box**
for every person, which is what makes it possible to train detectors that
predict amodal extent through occlusion and to evaluate them honestly.

CityPersons formalises the occlusion split that everyone now reports against:
"the visibility ratio in R set is larger than 65% whereas in HO it ranges from
20% to 65%"
([CityPersons occlusion subsets](https://www.researchgate.net/figure/Subsets-of-CityPersons-dataset-based-on-visibility_tbl2_372331924)).
The number to keep in your head is the ratio between them. A representative
pair: the MSFM-Net paper's **VGG-16 baseline** gets **11.92% Reasonable / 47.88% Heavy Occlusion**
log-average miss rate on CityPersons, "outperforming the adapted FasterRCNN baseline in CityPersons by
0.89%" (i.e. vs 12.81) ([MSFM-Net, arXiv 2010.10744v1, ablation table](https://arxiv.org/pdf/2010.10744)).
PSC-Net itself reports e.g. 13.8 R / 56.8 HO for its baseline ([PSC-Net](https://arxiv.org/pdf/2001.09252)).
`[audit R4 2026-09-26]`: the 11.92/47.88 pair was previously attributed to PSC-Net (it is MSFM's baseline); the
"8.1 / 43.0 / 8.1 / 5.2" set once quoted here appears in neither paper and has been removed. **Heavy occlusion costs roughly
4–5× the miss rate of the reasonable set, and that gap has barely moved in a
decade.** In a queue, a turnstile, or a doorway, heavy occlusion is not an edge
case — it is the operating point.

### 1.3 Pixels on target: the tiny-person regime

TinyPerson is the honest benchmark for the long-range surveillance case
(perimeter cameras, border fence lines, harbour and coastline watch). It is
"1610 large-scale seaside images with more than 70000 bounding boxes", and
critically: "The average absolute size of target objects is about 18 pixels and
non-small objects (absolute size > 32 pixels) are rare", measured as
"18.0 ± 17.4 pixels"
([Scale Match for Tiny Person Detection](https://openaccess.thecvf.com/content_WACV_2020/papers/Yu_Scale_Match_for_Tiny_Person_Detection_WACV_2020_paper.pdf)).
The benchmark partitions by absolute size: "tiny [2,20], small [20,32] and all
[2,∞]", with "tiny1 [2,8], tiny2 [8,12] and tiny3 [12,20]". Best reported
figures are in the region of "Faster RCNN-PANet achieving AP₅₀^tiny of 57.17".

Internalise what an AP₅₀ of ~57 on 18-pixel people means operationally: on a
perimeter camera looking 80 m down a fence, **roughly two in five people are
missed at a threshold loose enough that box quality is nearly irrelevant.** Any
claim of "99% detection" on such a view is either measured on a different pixel
regime or measured on a different definition of detection.

VIRAT states the surveillance operating envelope directly — it is designed to
capture "2–30Hz frame rates and 10–200 pixels in person-height"
([VIRAT](https://viratdata.org/), via
[OpenTraj's VIRAT notes](https://github.com/crowdbotp/OpenTraj/blob/master/datasets/VIRAT/README.md)).
That single sentence is the best one-line specification of the real problem
domain in the whole literature, and it is from 2011.

### 1.4 Multi-camera and long-duration reference sets

* **WILDTRACK** — the reference overlapping-camera rig: "recorded in a
  real-world environment with seven fixed cameras, each recording at 1080 × 1920
  resolution and 2 fps", "synchronized and calibrated with overlapping fields of
  view that cover a region of 12 m × 36 m", discretised into "a 480 × 1440 grid,
  with each grid cell measuring 2.5 cm × 2.5 cm". "On average, each frame
  contains 20 pedestrians, with each location being captured by approximately
  3.74 cameras." Total: "7 series of 400 annotated frames… at a rate of 2 frames
  per second, resulting in over 40,000 bounding boxes… for a total of more than
  300 individuals"
  ([WILDTRACK](https://infoscience.epfl.ch/record/256268),
  [arXiv](https://arxiv.org/abs/1707.09299)).
  Two things to note and never forget: **400 frames of ground truth is tiny**
  (360 train / 40 test), and **2 fps means no usable motion model**. Most
  "multi-view detection SOTA" is therefore fit to 360 frames of one plaza.
* **MEVA** — the closest public analogue to a real facility deployment. "The
  total video in MEVA is 9300 hours while 144 hours were annotated", covering
  "37 activity types", from "38 RGB and thermal IR cameras, 42 hours of UAV
  footage, as well as GPS locations for the actors"
  ([MEVA, WACV 2021](https://openaccess.thecvf.com/content/WACV2021/papers/Corona_MEVA_A_Large-Scale_Multiview_Multimodal_Video_Dataset_for_Activity_Detection_WACV_2021_paper.pdf),
  [mevadata.org](https://mevadata.org/)). The NIST
  [ActEV](https://www-nlpir.nist.gov/projects/tv2022/actev.html) series built on
  it is "designed to accelerate the development of robust, multi-camera,
  automatic human activity detection systems for forensic and real-time alerting
  applications" — which is verbatim the product we are building for.
  The annotation ratio, 144 / 9300 ≈ 1.5%, is itself the lesson: **nobody can
  afford to label real surveillance video densely.** That is the entire economic
  argument for SurvSim.
* **DukeMTMC**, **PETS2009**, **i-LIDS** — historically the multi-camera,
  crowd-analysis and UK-government operational benchmarks respectively.
  DukeMTMC was withdrawn by its authors over consent/ethics concerns and should
  be treated as unusable for any deliverable, though derived ReID splits still
  circulate; i-LIDS is distributed under UK Home Office terms with restricted
  redistribution. `[unverified in this pass — confirm current licence status
  before touching either; the ethics exposure here is real and is a contract
  risk, not a footnote]`
* **WiderPerson**, **SOMPT22** — WiderPerson is a dense outdoor-but-not-traffic
  detection set widely used alongside CrowdHuman (IterDet reports state of the
  art on it, below); [SOMPT22](https://arxiv.org/html/2208.02580v1) is
  explicitly a "Surveillance Oriented Multi-Pedestrian Tracking Dataset" and is
  the closest thing to an MOT benchmark shot from real CCTV mounting heights —
  worth knowing about precisely because so few people do.

### 1.5 Why detection and tracking fail here — the causal chain

Put the above together and the failure chain is mechanical:

1. **Small targets** → few pixels → weak appearance features → low detection
   confidence → detections fall below threshold intermittently.
2. **Intermittent detections** → track fragmentation → ID switches at
   re-appearance → every downstream behaviour metric (dwell time, loitering
   duration, count) corrupted.
3. **Crowding** → overlapping boxes → NMS suppresses true positives, or
   thresholds loosened and duplicates appear → association ambiguity.
4. **Low and variable fps** → IoU between consecutive frames drops toward zero →
   motion-based association collapses (quantified in §4.9).
5. **Compression** → block artefacts on exactly the moving regions you care
   about, because the encoder spends its bits elsewhere → feature degradation
   correlated with motion, i.e. correlated with the thing you are detecting.
6. **Fixed scene, forever** → any systematic false positive (a reflection, a
   poster, a mannequin) fires *every single frame for years*, which is what
   actually destroys operator trust.

Point 6 is the one academics structurally cannot see, because their benchmarks
are 30-second clips scored by average precision. A detector with 99.9%
per-frame precision on a 15 fps camera still emits ~1,300 false positives per
day per camera. Multiply by a 500-camera site.

---

## 2. History of person detection, and why the old ideas keep coming back

### 2.1 Background subtraction: 1999–2010, and still shipping

The first generation of "video analytics" was motion detection: model the
background per pixel, threshold the deviation, group blobs, classify by
aspect ratio and size. The canonical parametric model is Stauffer & Grimson's
Gaussian Mixture Model (MOG/MOG2) and its many refinements; the canonical
non-parametric one is **ViBe**, whose contribution search-verifiably is that
"ViBe's main innovation concerns the use of a random policy to select values to
build a samples-based estimation of the background. It is the first time that a
random aggregation is used in the field of background extraction"
([ViBe](https://github.com/vandroogenbroeckmarc/vibe), published IEEE TIP
20(6):1709–1724, June 2011). ViBe "could cope with multi-mode pixel background
similar to Gaussian Mixture Models and other advanced techniques but faster and
simpler than them."

Two pieces of hard-won practitioner knowledge:

* **It is still deployed.** Essentially every camera's on-board "motion
  detection" and every legacy VMS's "video motion detection" (VMD) is a
  background/frame-difference method. When a customer says "our existing
  analytics", this is usually what they mean, and it is the baseline your false
  alarm rate will be compared against.
* **Licensing finally cleared.** "As of January 2026, ViBe is now totally free,
  even for commercial usages. The algorithm was previously covered by several
  patents but these have now expired"
  ([ViBe repo](https://github.com/vandroogenbroeckmarc/vibe)). Worth knowing
  because patent encumbrance is exactly why the industry standardised on MOG2 in
  OpenCV instead.

Why it fails: illumination change, camera shake, moving foliage, shadows (a
shadow is a *legitimately* changed pixel), stopped objects being absorbed into
the background, and the impossibility of distinguishing a person from a bin bag.
The background model has no concept of "person".

### 2.2 Hand-crafted features: HOG (2005) and DPM (2008)

Dalal & Triggs replaced motion with appearance. Their reported operating point
is worth quoting exactly, because it shows how the field used to measure itself:
the optimal R-HOG configuration achieved "a 10.4% miss rate at 10^-4 FPPW",
and HOG detectors gave "near-perfect separation on the MIT test set and at least
an order of magnitude reduction in FPPW on the INRIA dataset"
([Dalal & Triggs, CVPR 2005](https://lear.inrialpes.fr/people/triggs/pubs/Dalal-cvpr05.pdf)).

Note the metric: **false positives per *window***, not per image. A 1080p image
sliding-windowed at multiple scales contains on the order of 10⁵–10⁶ windows, so
10⁻⁴ FPPW is tens of false positives *per frame*. The field's move to
false-positives-per-image (FPPI) was not cosmetic; it was the moment pedestrian
detection started being evaluated in units an operator could care about.

Felzenszwalb's Deformable Part Model added a root filter plus part filters with
deformation costs — the first serious attempt at occlusion and articulation, and
the direct ancestor of every "part-based occlusion handling" paper since
`[unverified numbers in this pass; the architectural lineage is not in dispute]`.

The two survey papers that closed this era are the ones to cite when someone
claims a novel occlusion insight: Dollár et al.'s *Pedestrian Detection: An
Evaluation of the State of the Art* (TPAMI 2011), which contributed "a large,
well-annotated, and realistic monocular pedestrian detection dataset with study
of statistics on size, position, and occlusion patterns", "a refined per-frame
evaluation methodology… including performance in relation to scale and
occlusion", and an "evaluation of sixteen pretrained state-of-the-art detectors"
([CaltechAUTHORS](https://authors.library.caltech.edu/records/e69e6-ezc50)); and
Benenson et al.'s *Ten Years of Pedestrian Detection, What Have We Learned?*
which reviewed "40+ proposed methods"
([arXiv 1411.4304](https://arxiv.org/pdf/1411.4304)). Caltech introduced the
metric everyone still reports: "The log-average miss rate over 9 points ranging
from 10^-2 to 10^0 FPPI".

### 2.3 Deep detectors: two-stage, one-stage, transformer

The lineage, with what each stage actually changed for *surveillance*:

* **R-CNN → Fast → Faster R-CNN (2014–2015).** Learned features and a learned
  region proposal network. For surveillance, the important property is the
  two-stage design's robustness to small objects via RoI pooling on high-res
  feature maps — which is why occluded-pedestrian research (OR-CNN, PSC-Net,
  Progressive Refinement Network, CrowdDet, IterDet) is still overwhelmingly
  built on **FPN-Res50 Faster R-CNN**, not on YOLO. When a paper says it beats
  a Faster R-CNN baseline on CityPersons HO, that is the tradition it is in.
* **SSD / RetinaNet / focal loss (2016–2017).** Single-shot speed; focal loss
  addressed the extreme foreground/background imbalance that a surveillance
  scene (mostly empty pavement) exemplifies.
* **YOLO family (2016–present).** The practical default for deployed video
  analytics, because it is fast, exportable, and has an enormous tooling
  ecosystem. In this pass I could not re-verify per-version mAP/latency tables
  for v5/v8/v11/v12 or the 2025–26 releases; treat any specific number you have
  memorised as `[unverified — pull the current table from the vendor's own
  benchmark page before quoting]`. What *is* verified and more useful anyway is
  a robustness finding: under compression, "YOLOv5 exhibited the highest
  robustness to compression, followed by Fast R-CNN and DETR, whereas
  EfficientDet and YOLOv8 were more sensitive to quality degradation"
  ([ETRI Journal benchmark](https://onlinelibrary.wiley.com/doi/10.4218/etrij.2025-0363)).
  **Newer is not automatically better on degraded CCTV**, and that sentence is
  worth more in a customer meeting than a COCO leaderboard.
* **DETR → Deformable DETR → DINO → RT-DETR (2020–2023).** Set prediction with
  learned queries and Hungarian matching removes NMS entirely, which is
  structurally attractive in crowds — NMS is precisely the component that fails
  when two people genuinely overlap at IoU 0.7. RT-DETR brought this to
  real-time. Specific AP/FPS figures `[unverified in this pass]`. The
  query-based paradigm also matters because it is the bridge to end-to-end
  tracking (§4.7): a track is just a query that persists.

### 2.4 Small-object tricks that earn their keep

For surveillance the single highest-leverage engineering trick is **tiled
inference**. SAHI (Slicing Aided Hyper Inference) formalised it and measured it:
"the proposed inference method can increase object detection AP by 6.8%, 5.1%
and 5.3% for FCOS, VFNet and TOOD detectors"
([SAHI](https://arxiv.org/abs/2202.06934), see also the
[LearnOpenCV walkthrough](https://learnopencv.com/slicing-aided-hyper-inference/)).
Adaptive variants now exist for high-resolution imagery
([adaptive SAHI](https://arxiv.org/html/2604.19233v1)).

Practitioner caveats that SAHI papers underplay `[practitioner lore]`:

* Tiling multiplies inference cost by the tile count. Four tiles plus a full
  frame is 5× the GPU. That is the difference between 16 cameras per GPU and 3.
* Tile boundaries cut people in half; you need overlap plus a cross-tile merge,
  and that merge is a second NMS with its own failure modes.
* Tiling helps *detection recall* but destroys *tracking* if you tile
  inconsistently per frame — boxes jitter at seams and the Kalman filter chases
  the seam.
* Learned super-resolution before detection is usually a trap: it hallucinates
  plausible texture, which raises confidence on non-people (posters, patterned
  fabric) as readily as on people.

Also in this family: **scale match** (TinyPerson's own contribution — match the
scale distribution of your pretraining data to your target domain, rather than
adding capacity), **anti-aliasing in the backbone** for tiny objects
([paper](https://arxiv.org/pdf/2310.14221)), and label-assignment fixes for tiny
boxes where a one-pixel shift swings IoU enormously
([similarity-distance label assignment](https://arxiv.org/pdf/2407.02394)).

### 2.5 Crowded-scene detectors

Two designs are worth knowing in detail because they attack NMS directly.

**CrowdDet** (CVPR 2020) lets "each proposal predict a set of correlated
instances rather than a single one", with "EMD Loss" — "EMD (earth mover's
distance) loss is used to select the best matching one with the smallest loss
for all permutations of matching" — and "Set NMS", which "largely follows the
normal NMS procedure but skips suppression for prediction coming from the same
anchor". Measured: "On a FPN-Res50 baseline, the detector obtains 4.9% AP gains
on the challenging CrowdHuman dataset", and "without the refinement module, the
method still obtains 4.5% improvements in AP and 2.2% in JI"
([CrowdDet](https://arxiv.org/abs/2003.09163),
[code](https://github.com/xg-chu/CrowdDet)).

**IterDet** (S+SSPR 2020) instead detects iteratively: "at each iteration, a new
subset of objects is detected, and detected boxes from all previous iterations
are considered at the current iteration to ensure that the same object would not
be detected twice." Measured: "On the most challenging full-body annotation,
IterDet improves recall by more than 5.5% and AP by 3.1% with respect to
baseline", reaching "95.80% recall and 88.08% AP" with two iterations on Faster
R-CNN, plus state of the art on WiderPerson
([IterDet](https://arxiv.org/pdf/2005.05708),
[code](https://github.com/SamsungLabs/iterdet)).

Set-prediction detectors (DETR family, and
[end-to-end FCN detection](https://arxiv.org/pdf/2012.03544)) get the same
benefit structurally rather than by patching NMS.

**Pose-based detection** deserves a mention because it is the most
under-used tool in crowded surveillance: a keypoint detector can resolve two
heavily-overlapping people that a box detector cannot, since keypoints are
sparse where boxes are dense. The JTA line of work (§8) exists precisely to
supply occluded-joint supervision — every joint is flagged "occluded if it is
not directly visible from the camera point of view and it is occluded by objects
or other pedestrians", and "self-occluded if it is occluded by the same person"
([JTA](https://arxiv.org/pdf/1803.08319)). Head detection is the cheap
practical version: heads are rarely mutually occluded even in a dense queue,
which is why crowd-counting and head-tracking benchmarks exist at all.

---

## 3. Single-camera multi-object tracking

### 3.1 The paradigm: tracking-by-detection

Since 2016 the field has converged on: detect per frame, then associate. The
association step needs (a) a motion model to predict where a track should be,
(b) an affinity between predictions and detections, (c) an assignment algorithm
(Hungarian/JV), and (d) a track lifecycle policy (birth, confirmation, coast,
death). Almost all of the "SORT family" differences are in (b) and (d), and
almost all of the *practical* differences in deployment are in (d) — which
nobody writes papers about.

### 3.2 SORT and DeepSORT

**SORT** (2016) is a Kalman filter on box centre/scale/aspect with constant
velocity, IoU affinity, Hungarian assignment, and immediate deletion of unmatched
tracks. It is a few hundred lines and it is still the right answer for a
sparse, high-fps, well-lit scene. **DeepSORT** (2017) added a CNN appearance
embedding and a cascaded matching that prefers recently-seen tracks, which
bought a large reduction in ID switches at modest cost.
`[canonical numbers unverified in this pass]`

The structural weaknesses, which every later paper is a response to:

* Kalman with constant velocity is wrong for people (who stop, turn, and are
  pushed) and catastrophically wrong when the camera itself moves.
* Unmatched tracks coast on prediction, and a linear prediction through a long
  occlusion diverges — then "re-updates" the filter with a bad state.
* Appearance embeddings trained on ReID benchmarks are trained on ~128×256
  crops. On 20-pixel-tall people the embedding is noise.
* Confidence thresholding throws away the occluded person, exactly when you
  needed them.

### 3.3 ByteTrack: the highest value-per-line idea in the field

ByteTrack's observation is that "objects with low detection scores, such as
occluded objects, are simply thrown away, which brings non-negligible true
object missing and fragmented trajectories". Its fix is to associate in two
stages: high-score detections first, then, "for the low score detection boxes,
utilize their similarities with tracklets to recover true objects and filter out
the background detections". Result: "ByteTrack achieves 80.3 MOTA, 77.3 IDF1 and
63.1 HOTA on the test set of MOT17 with 30 FPS running speed on a single V100
GPU"
([ByteTrack, ECCV 2022](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136820001.pdf),
[code](https://github.com/FoundationVision/ByteTrack)).

Why this matters for us specifically: the low-score box is *the surveillance
case*. A person at 25 px in a doorway, half occluded, in IR, is a 0.25-confidence
detection. ByteTrack's second stage is the difference between a continuous
dwell-time measurement and forty fragments.

### 3.4 BoT-SORT: camera motion compensation and fused affinity

BoT-SORT-ReID "achieved state-of-the-art results on the MOT17 test set, with
80.5 MOTA, 80.2 IDF1, and 65.0 HOTA, being the first tracker to exceed an IDF1
score of 80". Its three components: a refined Kalman state parameterisation,
camera motion compensation — "integrated using OpenCV's Video Stabilization
module with affine transformation, applying translation-based outlier rejection
and RANSAC to account for global scene motion" — and "a novel IoU-Re-ID fusion
strategy… taking the minimum of IoU distance and a conditionally masked Re-ID
cosine distance"
([BoT-SORT](https://arxiv.org/abs/2206.14651),
[code](https://github.com/NirAharon/BoT-SORT)).

CMC is the component that turns a benchmark tracker into a deployable one. Any
pole-mounted camera oscillates in wind; any PTZ camera on a guard tour moves
metres of apparent scene per second; any vehicle-mounted or drone camera moves
constantly. Without global-motion estimation, every track's Kalman velocity
absorbs camera motion as target motion, and association falls apart on the
frame after the camera stops. See also
[UCMCTrack](https://arxiv.org/pdf/2312.08952), which takes the further step of
modelling motion on the *ground plane* with a uniform camera-motion model —
directly relevant to us, since SurvSim exports calibration and can therefore
support ground-plane trackers that most real deployments cannot.

### 3.5 OC-SORT and Deep OC-SORT: fixing the filter, not the features

OC-SORT names the disease: SORT is **estimation-centric**. "Challenges like
occlusions and non-linear object motion can distort estimation processes… Instead
of relying only on the linear state estimate (i.e., estimation-centric approach),
OC-SORT uses object observations… to compute a virtual trajectory over the
occlusion period to fix the error accumulation of filter parameters." Its two
mechanisms are Observation-Centric Re-Update — "When a track is re-activated,
ORU backchecks the period it was untracked and re-updates the KF parameters
based on a virtual trajectory generated from the last-seen observation and the
re-activating observation" — and Observation-Centric Momentum
([OC-SORT, CVPR 2023](https://openaccess.thecvf.com/content/CVPR2023/papers/Cao_Observation-Centric_SORT_Rethinking_SORT_for_Robust_Multi-Object_Tracking_CVPR_2023_paper.pdf),
[code](https://github.com/noahcao/OC_SORT)).

**Deep OC-SORT** adds appearance back, adaptively: "Camera Motion Compensation
(CMC), Dynamic Appearance (DA), and Adaptive Weighting (AW)", and "achieved 1st
place on MOT20 and 2nd place on MOT17 with 63.9 and 64.9 HOTA, respectively",
plus "61.3 HOTA on the challenging DanceTrack benchmark"
([Deep OC-SORT](https://arxiv.org/abs/2302.11813)).

Note the ordering: **MOT20 first, MOT17 second, and MOT20's HOTA is the lower
number.** Crowding costs about a point of HOTA even for the method that wins it.

### 3.6 StrongSORT: the offline post-processing nobody admits to using

StrongSORT "significantly improves upon the classic DeepSORT tracker from
multiple perspectives including object detection, feature embedding, and
trajectory association", then adds two *global* steps: "an appearance-free link
model (AFLink) to perform global association without appearance information,
and Gaussian-smoothed interpolation (GSI) based on Gaussian process regression
to address missing detections". "By integrating StrongSORT with AFLink and GSI,
the final tracker StrongSORT++ ranks first on MOT17 in terms of HOTA and IDF1
metrics"
([StrongSORT, TMM 2023](https://arxiv.org/abs/2202.13514),
[code](https://github.com/dyhBUPT/StrongSORT)).

This is where a veteran reads the fine print. AFLink and GSI are **offline**:
they link and interpolate using future frames. They are perfectly legitimate for
forensic review — "find everyone who entered this corridor last Tuesday" — and
completely unavailable for live alerting. A large fraction of MOTChallenge
leaderboard headroom above the online trackers is of this kind. **When comparing
to a leaderboard, always ask: online or offline, and with which detector.**
Which brings us to the second piece of fine print: most MOT17/20 leaderboard
entries share the same YOLOX detector weights, so the leaderboard is largely
measuring association, not the system you would ship.

### 3.7 Hybrid-SORT: weak cues

Hybrid-SORT's contribution is that when strong cues (IoU, appearance) are
ambiguous, weak ones discriminate. It "introduces confidence and height state as
potential weak cues, along with velocity direction", via Tracklet Confidence
Modeling (TCM), Height Modulated IoU (HMIoU — "combines Height IoU with
conventional IoU to improve discrimination for clustered objects using stable
height information"), and corner-based multi-interval velocity direction.
Measured plug-and-play gains: "TCM improves DeepSORT by 4.9 HOTA in DanceTrack
and 0.9 HOTA in MOT17, while HMIoU boosts SORT by 1.6 HOTA in DanceTrack and 1.0
HOTA in MOT17"
([Hybrid-SORT, AAAI 2024](https://arxiv.org/abs/2308.00783)).

Height is a *beautiful* cue for fixed CCTV and the paper undersells why: on a
calibrated fixed camera, image height is a monotone function of ground-plane
distance, so height is effectively a depth measurement. Two people overlapping
at IoU 0.8 in image space but 4 m apart in depth have clearly different heights.
SurvSim exports exactly the calibration needed to exploit this, and real
deployments have it too (anyone who has drawn a "tripwire" in a VMS has
implicitly calibrated).

### 3.8 End-to-end / query-based tracking

**TrackFormer** and **MOTR** made tracks into persistent decoder queries, so
association is learned rather than hand-designed. The catch was detection
quality. **MOTRv2** fixed it by "using an extra object detector to generate
proposals as anchors, providing detection prior to MOTR", reaching "69.9 HOTA on
the DanceTrack dataset", "14.8% better than the previous best method", and
"73.4% HOTA on the DanceTrack test set" with post-processing, validation-set
training and a 4-model ensemble
([MOTRv2, CVPR 2023](https://arxiv.org/abs/2211.09791)).
**MeMOTR** and **CO-MOT** extended the memory and supervision.

**MOTIP** (CVPR 2025) reframes the problem again: "regard multiple object
tracking as an in-context ID prediction problem, where given a set of
trajectories carried with ID information, MOTIP directly decodes the ID labels
for current detections". It reports "a HOTA score of 69.6 (without extra data)"
on DanceTrack, "significantly outperforming the previous best CO-MOT by 4.3 HOTA
and 6.9 AssA", "72.6 HOTA on SportsMOT", and new state of the art on association
with "60.4 AssA on DanceTrack" and "63.2 AssA on SportsMOT"
([MOTIP](https://openaccess.thecvf.com/content/CVPR2025/papers/Gao_Multiple_Object_Tracking_as_ID_Prediction_CVPR_2025_paper.pdf),
[code](https://github.com/MCG-NJU/MOTIP)).

The honest assessment for our product: end-to-end trackers win where motion is
non-linear and appearance is uninformative (dance, sport). On MOT17/20-style
pedestrian video they are "competitive", not dominant, and they are far harder
to deploy — no clean decoupling of detector and tracker, higher latency, and no
way for an integrator to swap in the detector they already certified.
`[practitioner judgement, consistent with the MOTIP paper's own framing that it
"performs competitively with other transformer-based methods on MOT17"]`

### 3.9 Segmentation-based tracking: SAM 2, SAMURAI

SAM 2 brought promptable video segmentation with a memory bank. Its weakness is
exactly ours: "SAM 2 … faces challenges in visual object tracking, particularly
when managing crowded scenes with fast-moving or self-occluding objects, and the
fixed-window memory approach in the original model does not consider the quality
of memories selected to condition the image features for the next frame, leading
to error propagation in videos." **SAMURAI** adds "temporal motion cues with a
motion-aware memory selection mechanism", "without requiring retraining or
fine-tuning", and reports "a 7.1% AUC gain on LaSOT_ext and a 3.5% AO gain on
GOT-10k", operating in real time
([SAMURAI](https://arxiv.org/abs/2411.11922),
[project](https://yangchris11.github.io/samurai/)).

Where this lands operationally: these are *single-object, prompted* trackers.
They are outstanding for the forensic workflow ("operator clicks a person,
system follows them through the clip") and poor for the always-on
multi-target alerting workflow (cost scales with targets, no birth/death policy,
no identity management). Build the forensic feature on SAM2/SAMURAI; do not
build the alerting pipeline on it.

### 3.10 Occlusion handling, ID switches, and long-term re-appearance

The taxonomy of ID-switch causes you should be able to recite, with where each
is addressed:

| Cause | Mechanism | Mitigation | Reference |
|---|---|---|---|
| Detector miss during occlusion | track coasts, then dies | keep low-score boxes; longer max-age | [ByteTrack](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136820001.pdf) |
| Filter divergence during coast | linear prediction drifts | re-update on re-acquisition | [OC-SORT](https://github.com/noahcao/OC_SORT) |
| Crossing pairs with similar appearance | affinity genuinely ambiguous | height/depth cue, velocity direction | [Hybrid-SORT](https://arxiv.org/abs/2308.00783) |
| Camera motion | apparent global translation | CMC / ground-plane model | [BoT-SORT](https://arxiv.org/abs/2206.14651), [UCMCTrack](https://arxiv.org/pdf/2312.08952) |
| Low fps, large displacement | IoU → 0 between frames | frame-rate-aware association | [FraMOT](https://arxiv.org/abs/2209.11404) |
| Long absence (left the view) | no track exists to match | global/offline linking, or ReID gallery | [StrongSORT AFLink](https://arxiv.org/abs/2202.13514) |
| NMS suppression in a crowd | true positive removed | set prediction / Set NMS | [CrowdDet](https://arxiv.org/abs/2003.09163) |

Long-term re-appearance is the one the field mostly declines to solve in the
single-camera setting, because MOT benchmarks are short. Operationally it is
essential: "did the person who loitered at 14:02 come back at 14:40?" is a
*within-camera, across-minutes* question, and no SORT variant with a 30-frame
max-age answers it. The working architecture is a two-tier one: a short-horizon
tracker producing tracklets, plus a tracklet-level gallery with appearance
embeddings and spatio-temporal gating — architecturally the same machinery as
cross-camera ReID, pointed at one camera and the time axis.
`[practitioner architecture; the offline analogue is exactly AFLink/GSI and
tracklet-clustering work such as [hierarchical tracklet clustering](https://arxiv.org/pdf/2210.03355)]`

### 3.11 Kalman vs learned motion

Learned motion models (diffusion-based
[DiffMOT](https://arxiv.org/pdf/2403.02075), learned filters — see
[Beyond Kalman Filters](https://arxiv.org/pdf/2402.09865)) beat constant-velocity
Kalman on non-linear motion, which is why they show up on DanceTrack and in
tiny-fast-object work (see the
[Kalman-filter analysis for fast tiny objects](https://arxiv.org/pdf/2509.18451)).
For pedestrian CCTV, honest summary: **Kalman plus CMC plus a
depth-aware cue captures most of the available gain at a fraction of the cost**,
and a learned motion model trained on one site's crowd dynamics is a
generalisation risk you will be asked to defend. `[practitioner judgement]`

### 3.12 Tracking at low frame rate — the number that changes designs

This is the single most decision-relevant measurement in this document for a
CCTV product:

> "Tracking shows stable performance from 30 FPS down to 3 FPS, followed by
> sharp degradation below 2 FPS, where the drop is primarily association-driven
> with AssA decreasing from 43.6% at 3 FPS to 36.5% at 2 FPS and 27.8% at 1 FPS."
> — [Low-FPS Multi-Object Multi-Camera Tracking via Deep Learning](https://www.mdpi.com/2079-9292/14/7/1373)

Three consequences:

1. **Do not spend GPU going above ~5 fps for tracking.** Between 30 and 3 fps
   you buy almost nothing in association. Spend the compute on more cameras, or
   on higher resolution / tiling for recall.
2. **Below 2 fps, redesign rather than tune.** The failure is association, not
   detection. Either add frame-rate-aware association (FraMOT's "Frame Rate
   Agnostic Association Module (FRAAM) and Periodic Training Scheme (PTS)",
   [arXiv 2209.11404](https://arxiv.org/abs/2209.11404)), or move to
   appearance-and-geometry matching on the ground plane, or accept tracklets
   instead of tracks.
3. WILDTRACK's 2 fps is *exactly* at the cliff edge. That is worth knowing
   before you believe any single-camera motion result computed on it.

---

## 4. Metrics: what the papers score, and what the customer scores

### 4.1 CLEAR MOT / MOTA

MOTA = 1 − (FN + FP + IDSW) / GT, summed over frames. It is dominated by FN and
FP counts because ID switches are rare relative to detections. Hence its known
pathology: **MOTA is essentially a detection metric wearing a tracking metric's
hat.** A tracker that swaps every ID but detects perfectly scores well.

### 4.2 IDF1

The identity-preserving F1 over a global ID-to-ID matching. It over-corrects in
the opposite direction: a tracker that finds only the easy half of the people
but never swaps them can beat a tracker that finds everyone with occasional
swaps.

### 4.3 HOTA

Luiten et al.'s diagnosis is the quotable one: "MOTA and IDF1 overemphasize the
effect of accurate detection and association respectively. HOTA balances both of
these by being an explicit combination of a detection score DetA and an
association score." HOTA "divides the task of evaluating tracking into three
subtasks (detection, association and localization), and calculates a score for
each using an IoU formulation", and "decomposes into a family of sub-metrics
which are able to evaluate each of five basic error types separately"
([HOTA, IJCV 2021](https://www.cvlibs.net/publications/Luiten2020IJCV.pdf); see
also Luiten's own
[explainer](https://autonomousvision.github.io/hota-metrics/)).

Practically: **always report DetA and AssA, never HOTA alone.** The
decomposition is the whole point, and it is what tells you whether to work on
the detector or the associator. The low-fps result in §3.12 is a perfect example
— it is legible only because AssA was reported separately.

HOTA's own pitfalls, which you should be able to name: it is computed at a range
of IoU thresholds and averaged, so localisation quality leaks into the headline;
it treats all identities as equally important, whereas an operator cares only
about the one person who climbed the fence; and like every MOT metric it is
computed against boxes, so a tracker that holds the right identity on the wrong
box geometry (common with tiling and with amodal/visible box mismatch) is scored
oddly.

### 4.4 TrackEval and the plumbing

[TrackEval](https://github.com/JonathonLuiten/TrackEval) is the reference
implementation for HOTA, CLEAR and Identity metrics and is what MOTChallenge
runs; `py-motmetrics` is the older CLEAR/IDF1 implementation. Use TrackEval, pin
its commit, and check its `ignore`-region handling — CrowdHuman and MOTChallenge
both define "don't care" regions, and whether your evaluation honours them moves
scores by several points. `[practitioner lore; the existence of ignore regions
is documented — CrowdHuman ships "~99k ignore region annotations" in train
alone ([CrowdHuman](https://arxiv.org/abs/1805.00123))]`

### 4.5 Detection metrics: AP vs log-average miss rate

Computer vision defaults to AP/mAP. Pedestrian detection has always preferred
**log-average miss rate over FPPI** (Caltech: "over 9 points ranging from 10^-2
to 10^0 FPPI"). MR-FPPI is the right family for security, because "false
positives per image" converts directly to "false alarms per hour" once you know
the frame rate, and because the metric is dominated by the low-FPPI regime that
operators live in. **If a vendor quotes you mAP for an alerting product, they
have chosen the metric that hides their false alarm rate.**

Fisheye work adds a further wrinkle worth knowing: RAPiD adopts "AP at IoU = 0.5
(AP₅₀) as an evaluation metric, considering only AP at IoU = 0.5 since a perfect
detection algorithm could have relatively low IoU due to non-uniqueness of
ground truth with multiple equally good bounding boxes at different angles"
([RAPiD](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w38/Duan_RAPiD_Rotation-Aware_People_Detection_in_Overhead_Fisheye_Images_CVPRW_2020_paper.pdf)).
The ground truth is ambiguous; the metric has to be loosened to stay meaningful.
That situation recurs everywhere in surveillance and is almost never
acknowledged.

### 4.6 What security operators actually care about

None of the above appears in a security KPI. The operational metrics are:

1. **Missed alarms (P(detect | event))** — per event type, per zone, per
   lighting condition. Usually specified as "no missed intrusions", which is
   unachievable, so the real negotiation is about the detection *range* at which
   it holds.
2. **False alarms per camera per hour/day** — the number that determines whether
   the system gets switched off. Verified anchors: a monitoring vendor notes that
   "A site of 40 cameras on raw motion can easily generate well over a thousand
   nuisance alarms a day"
   ([Fora Soft, tuning analytics](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy));
   more broadly, "when monitoring a large camera network, there may be thousands
   of false alerts per day because of noise". Industry claims about how many
   alarms are false range widely — "98% of security alarm activations are false,
   costing $1.8B yearly"
   ([IntelliSee](https://intellisee.com/98-of-security-camera-alarms-are-false-heres-what-thats-actually-costing-you/))
   versus "around 76% of alarms are false alarms, triggered by animals, objects
   blowing in the wind, pets, leaves or branches"
   ([Davantis](https://www.davantis.com/en/blog/technology/false-alarms-false-negatives/)).
   Treat all such figures as marketing-adjacent; cite them as *claims*, and note
   that vendors uniformly promise reduction "by up to 90%"
   ([Lumana](https://www.lumana.ai/blog/how-ai-powered-video-analytics-cut-false-alarms-by-up-to-90),
   [Scylla](https://www.scylla.ai/how-ai-video-analytics-helps-reduce-false-alarms/)).
3. **Latency, end to end** — camera → encoder → network → decode → inference →
   rule → VMS alarm → operator screen. For some applications this is tight
   enough that the standards path is the bottleneck: "For sub-100 ms alerting
   (trading floor surveillance, perimeter intrusion at critical facilities),
   direct WebRTC + in-band alarm metadata can beat the Profile M path"
   ([Fora Soft on ONVIF Profile M](https://www.forasoft.com/blog/article/onvif-profile-m)).
4. **Operator attention budget.** The industry's canonical (and
   methodologically shaky) claim is that "after about twenty minutes of observing
   a single screen, operators may lose up to 95% of their attentional focus"
   ([Fora Soft](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy)).
   Whatever the true figure, the design consequence is real: **the system's job
   is to spend the operator's attention well**, and that is an alert-precision
   problem, not a HOTA problem.
5. **Time-to-review for forensics** — how long to answer "where did this person
   go" over 72 hours of 200 cameras. This is where ID quality (IDF1/AssA)
   actually converts into money.

The bridge you should be able to build on a whiteboard: FPPI × fps × 3600 =
false alarms per camera per hour, before any temporal or rule-based filtering;
and recall at the required pixel height, not average recall, is the missed-alarm
number. Everything else is a proxy.

---

## 5. Edge and integration realities

### 5.1 Throughput: what a box actually runs

Verified anchor points:

* **Jetson / DeepStream.** "The Jetson Orin NX 16GB can handle up to 18 streams
  of 1080p30, making it suitable for mid-sized video analytics deployments" [staleness v2: decode ceiling only — with detect+ReID compute ≈ 12 cams/NX, so 40 cams → 4 NX; FACTS, 38 §2.5]
  ([Seeed Studio, on Jetson Orin video analytics](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/)).
  NVIDIA's own per-model tables live in the
  [DeepStream performance documentation](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html);
  read them with care, because published stream counts assume a specific model,
  resolution, batch size, inference *interval* (often skipping frames), and no
  tracker, no tiling and no secondary classifier.
* **Hailo-8.** "26 Tera-Operations Per Second (TOPS) with best-in-class power
  efficiency and typical power consumption of 2.5W", PCIe Gen3 ×2, passively
  cooled ([Hailo-8 product page](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/)).
  A practical estimate from an independent guide: the Hailo-8 "can handle
  roughly 4 full-rate 1080p detection streams with typical detect rates"
  ([edgeaistack](https://edgeaistack.ai/blog/hailo-8-vs-8l-vs-10h-2026/)).

The useful mental model `[practitioner lore]`: **you are almost never
inference-bound first.** In order, the bottlenecks are usually
(1) H.264/H.265 **decode** — a fixed-function NVDEC or VPU with a hard stream
limit, independent of your model; (2) memory bandwidth for frame copies and
colour conversion; (3) inference; (4) the tracker, if it runs on CPU with a
per-track Python loop; (5) the ReID embedding, which is per-detection and
therefore scales with crowd size, not camera count — a queue of 60 people can
cost more than 10 empty cameras.

Runtime stacks you must be able to talk about: **TensorRT** (NVIDIA, INT8/FP16
calibration, engine files are GPU-arch- and version-specific — an engine built
on one driver may not load on another, which is a deployment landmine),
**OpenVINO** (Intel CPU/iGPU/NPU; the default when the customer's existing NVR
is an x86 box with no GPU), **DeepStream** (GStreamer-based pipeline with
hardware decode, batched inference, and a built-in `nvtracker` offering
IOU/NvSORT/NvDCF/DeepSORT), **Hailo/Ambarella/Axis ARTPEC** for in-camera
inference, and ONNX as the interchange format that never quite round-trips
cleanly.

### 5.2 Ingest: RTSP, ONVIF, and the parts that break

* **RTSP/RTP** is the transport. "Media control is accomplished over RTSP as
  defined in RFC 2326", with "RTP, RTCP and RTSP profiling"
  ([ONVIF Streaming Specification](https://www.onvif.org/specs/stream/ONVIF-Streaming-Spec.pdf)).
  Practical failure modes: TCP vs UDP interleaving, keyframe intervals of 2–4
  seconds (so a reconnect costs seconds of blindness), SPS/PPS not resent,
  timestamp discontinuities, and cameras that silently drop to 5 fps under
  their own IR/WDR load. `[practitioner lore]`
* **ONVIF profiles.** Profile S/T for streaming and configuration — "Profile T
  supports video streaming features such as the use of H.264 and H.265 encoding
  formats, imaging settings, and alarm events such as motion and tampering
  detection" ([ONVIF Profile T](https://www.onvif.org/profiles/profile-t/)) —
  Profile G for recording, and **Profile M for analytics metadata**: it
  "supports analytics configuration and information query for metadata, as well
  as filtering and streaming of metadata", with "interfaces for generic object
  classification, and specified metadata for geolocation, vehicle, license
  plate, human face and human body"
  ([ONVIF Profile M](https://www.onvif.org/profiles/profile-m/),
  [spec PDF](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf)).
  The integrator's summary is blunt and correct: "Streams are easy — RTSP,
  H.264, H.265, done. Metadata is where multi-vendor deployments fall apart, and
  where ONVIF Profile M is supposed to help"
  ([Fora Soft](https://www.forasoft.com/blog/article/onvif-profile-m)).
* **VMS integration.** Milestone's route is the MIP SDK — "a set of
  comprehensive tools that makes it easy to create applications or device
  drivers that will work for Milestone XProtect video management software"
  ([Milestone](https://www.milestonesys.com/support/for-developers/integrate-with-xprotect/))
  — where "Producers of metadata can be hardware devices (usually cameras), or
  analytics services that uses the MIP SDK to send data to the XProtect VMS. A
  common exchange format, the ONVIF MetadataStream schema, decouples the
  producer from the consumer"
  ([MIP metadata intro](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html)).
  The modern container-friendly path is **Milestone AI Bridge**, which "acts as
  a bridge between installations of XProtect… and Intelligent Video Analytics
  (IVA) applications deployed as docker containers" and "allows the IVA
  applications to send the analysis results back into your XProtect VMS as
  Events, Metadata, and Video". Genetec (Security Center SDK / Media Gateway)
  and Avigilon (ACC) have analogous but incompatible SDKs and certification
  programmes. `[unverified specifics for Genetec/Avigilon in this pass]`

The architectural lesson: **your analytics output must land as an event and as
metadata in the customer's VMS, on their timeline, searchable, with a bookmark.**
An accuracy improvement that does not reach the operator's timeline is invisible.
This is also why our simulator's roadmap includes RTSP re-streaming via
`mediamtx` (see [`02_ARCHITECTURE.md`](../02_ARCHITECTURE.md)) — testing against
a real RTSP ingest path catches an entire class of bugs that file-based
evaluation never will.

---

## 6. Hard failure modes, with evidence

Each of these is a real incident class; each should become a SurvSim scenario.

1. **Reflections.** Wet pavement, polished lobby floors, glass façades and
   vehicle bodywork produce geometrically plausible inverted people. The
   detector is right — there *is* a person-shaped thing there. Mitigation is
   geometric (ground-plane consistency: a person whose feet are above the
   horizon-consistent ground point is a reflection), not perceptual.
   `[practitioner lore; the general category appears in vendor false-alarm
   guidance, e.g. "Car headlights reflecting off surfaces, and shifting cloud
   cover all cause pixel changes" ([Fora Soft](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy))]`
2. **Shadows.** A cast shadow is a legitimate pixel change, so background
   subtraction always fires; for deep detectors the failure is subtler — the
   shadow extends the blob, inflating the box, corrupting the foot point, and
   therefore corrupting ground-plane position and speed. Long shadows at dawn
   and dusk are the worst case, and they are *scheduled*: the same false alarm
   at the same time every day, drifting seasonally.
3. **Mannequins, posters, printed people, screens.** CEPDOF deliberately
   includes "images of people on projection screens" among its challenging
   scenarios
   ([CEPDOF](https://vip.bu.edu/projects/vsns/cossy/datasets/cepdof)). A
   retail-window mannequin fires forever. The only robust fixes are temporal
   (a real person eventually moves) and geometric (scale-vs-position
   consistency).
4. **Umbrellas, hoods, large bags, PPE.** Change the silhouette's top — the most
   informative region for a pedestrian detector — and recall falls. Umbrellas
   additionally occlude the head from a ceiling or high-mounted camera, which
   defeats head-based detection and tracking simultaneously. `[practitioner lore]`
5. **Groups.** The quantified case: MOT20's ~20 pairs per frame above IoU 0.4 vs
   MOT17's 2.5 ([MOT20](https://arxiv.org/pdf/2003.09003)). Two people walking
   arm-in-arm are a single blob to NMS and a single track to IoU association, and
   they cost you both a count and an identity.
6. **Night and IR.** The IR illuminator produces a monochrome, high-contrast,
   vignetted image with hot-spot saturation near the lens and near-total
   darkness beyond the illuminator's range — so **detection range at night is
   set by the illuminator, not the sensor or the model**. On the thermal/RGB
   research side, KAIST is the reference: "95k color-thermal pairs (640x480,
   20Hz)… for a total of 103,128 dense annotations and 1,182 unique pedestrians",
   split at test into "1455 images… captured during the daytime, and 797…
   during the nighttime"
   ([KAIST benchmark](https://soonminhwang.github.io/rgbt-ped-detection/)).
   Modern fusion narrows the day/night gap substantially — C²Former "obtained
   28.48 miss rate (MR) on the 'Day' subset, 26.67 MR on the 'Night' subset, and
   28.39 MR on the 'All' subset"
   ([C²Former](https://arxiv.org/pdf/2306.16175)) — note night is *better* than
   day there, because thermal contrast improves when the sun stops heating
   everything. That is a genuinely counter-intuitive, quotable fact.
7. **Insects on and near the lens.** The most common single cause of overnight
   nuisance alarms on outdoor IR cameras. "Spiders building webs across camera
   lenses create constant motion triggers as they move", and "When the insect or
   spider moves across the lens or across the view, it may trigger false alarms,
   as the camera analytics software may interpret its movements as being
   movements in the scene rather than movements in close proximity to or on the
   lens itself"
   ([Fora Soft](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy),
   [Reolink on flying bugs](https://reolink.com/blog/flying-bugs-on-night-vision-cameras/)).
   The field mitigations are physical, not algorithmic — insecticide on the
   housing, brushing webs off, and "Hang an electric bug zapper at least six
   feet from the camera and three feet higher than the lens." Know this. It is
   the fastest way to establish credibility with an installer, and it tells you
   something real: a moth 3 cm from the lens subtends the same angle as a person
   at 40 m, so **no appearance model can separate them; only defocus,
   parallax and motion statistics can.**
8. **Weather.** "Wind moves tree branches, flags, and debris across detection
   zones, generating pixel shifts that motion sensors register as intrusion
   events. Rain produces similar disruptions; falling droplets scatter infrared
   light and create surface reflections that confuse detection algorithms"
   ([Trunetto](https://www.trunetto.com/troubleshooting/security-cameras/reolink/reolink-camera-false-motion-alerts-rain-wind)).
   With IR on, rain and snow near the lens are brilliant white streaks — the
   classic "snow globe" effect.
9. **PTZ motion.** During a pan, every static object moves. Without camera
   motion compensation, every track's velocity is wrong and every tripwire is in
   the wrong place. This is precisely what BoT-SORT's CMC addresses
   ([BoT-SORT](https://arxiv.org/abs/2206.14651)). Additional realities: PTZ
   presets drift mechanically over months, so a calibrated tripwire silently
   moves off its line; and analytics is usually *suspended* during motion, which
   is exploitable by anyone who has watched the guard tour.
10. **Wide-angle and fisheye.** People are radially oriented, not axis-aligned,
    so axis-aligned box detectors are structurally mismatched. RAPiD's
    rotation-aware approach reports "an AP₅₀ of 85.8, significantly
    outperforming the previous best of 76.9" on CEPDOF
    ([RAPiD](https://arxiv.org/pdf/2005.11623)); CEPDOF itself is "8 videos with
    up to 13 people visible at a time, over 25,000 annotated frames"
    ([CEPDOF](https://vip.bu.edu/projects/vsns/cossy/datasets/cepdof)). The
    in-the-wild set is harder: "All metrics on WEPDTOF are significantly lower
    than those on CEPDOF due to challenges captured in WEPDTOF"
    ([WEPDTOF](https://www.researchgate.net/publication/363115429_WEPDTOF_A_Dataset_and_Benchmark_Algorithms_for_In-the-Wild_People_Detection_and_Tracking_from_Overhead_Fisheye_Cameras)).
    Useful survey: [Overhead fisheye cameras for indoor monitoring: challenges
    and recent progress](https://www.frontiersin.org/journals/imaging/articles/10.3389/fimag.2024.1387543/full).
11. **Compression.** Two verified findings worth carrying: "PSNR scales
    approximately linearly with bitrate, whereas detection accuracy exhibits
    saturation with diminishing returns at higher bitrates", and the
    model-dependence of robustness — "YOLOv5 exhibited the highest robustness to
    compression… whereas EfficientDet and YOLOv8 were more sensitive to quality
    degradation"
    ([ETRI benchmark](https://onlinelibrary.wiley.com/doi/10.4218/etrij.2025-0363)).
    H.264 "offers support for different quantization parameters (QP), where QP
    ranges from 0 to 51". Two implications: there is a knee in the
    bitrate/accuracy curve, so **find it and spec bitrate to it instead of
    arguing**; and evaluate candidate models *at the customer's bitrate*, not on
    pristine frames.
12. **Stopped and re-started people.** A person who stands still for two minutes
    is absorbed by a background model, and becomes low-confidence to a detector
    that has learned motion-blur cues. Loitering detection — the behaviour the
    customer most wants — is therefore built on the tracker's weakest regime.
    `[practitioner lore]`

---

## 7. Synthetic data for detection and tracking: what the numbers actually say

This section is the empirical justification for SurvSim's existence, so the
numbers matter more than the enthusiasm.

### 7.1 MOTSynth — the strongest published sim2real result for MOT

MOTSynth is "a large and diverse synthetic dataset for pedestrian detection,
tracking, and segmentation, designed to replace real-world data". Its headline
results:

* "Models trained solely using synthetic data achieve highly competitive
  results, with Tracktor-MOTSynth outperforming Tracktor trained on COCO and
  fine-tuned on MOT17 by +3.4 MOTA and +4.6 IDF1 on MOT17."
* "CenterTrack trained only on synthetic data achieves 59.7 MOTA and 52.0 IDF1,
  with fine-tuning on MOT17 establishing state-of-the-art at 65.1 MOTA and 57.9
  IDF1."
* On segmentation: "Tracktor trained only on synthetic data significantly
  outperforms TrackR-CNN trained on real datasets, improving sMOTSA by +14.45,
  MOTSA by +15.04, MOTSP by +3.47, and IDF1 by +21.47."
* And the design lesson: "The diversity of MOTSynth is identified as more
  crucial for bridging the domain gap than sheer data volume, with smaller, more
  diverse subsets yielding significant improvements."

([MOTSynth, ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/papers/Fabbri_MOTSynth_How_Can_Synthetic_Data_Help_Pedestrian_Detection_and_Tracking_ICCV_2021_paper.pdf))

That last sentence should be on the wall of our scenario-authoring room. Our
generator's value is in the *breadth of the randomisation axes* — camera
geometry, lighting, clothing, gait, weather, sensor degradation — not in frame
count. The MOTChallenge community took the question seriously enough to run a
workshop titled
["How Far Can Synthetic Data Take us?"](https://motchallenge.net/workshops/bmtt2022/).

### 7.2 JTA — the occlusion-supervision ancestor

"512 Full HD videos, 30 seconds long, recorded at 30 fps", with "a number of
people ranging between 0 and 60 with an average of more than 21 people, totaling
almost 10M annotated body poses over 460,800 densely annotated frames", each
with "a precise annotation of visible and occluded body parts, people tracking
with 2D and 3D coordinates in the game virtual world"
([JTA, ECCV 2018](https://arxiv.org/pdf/1803.08319)).

The capability no real dataset has: **ground truth for invisible joints.** You
cannot annotate an occluded elbow from video; you can read it out of a
simulator. That is the structural, not incremental, advantage of synthetic data,
and it is the one to lead with.

### 7.3 PeopleSansPeople — the controlled ablation

Unity's generator provides "simulation-ready 3D human assets, a parameterized
lighting and camera system", generating "2D and 3D bounding box, instance and
semantic segmentation, and COCO pose labels". The measured transfer:

* Few-shot: synthetic pre-training then fine-tuning gave "keypoint AP of
  60.37 ± 0.48 (COCO test-dev2017), outperforming models trained with the same
  real data alone (keypoint AP of 55.80) and pre-trained with ImageNet (keypoint
  AP of 57.50)".
* Abundant-data: "a keypoint AP increase of +1.47 (63.47 ± 0.19 vs. 62.00)".

([PeopleSansPeople](https://arxiv.org/abs/2112.09290v1),
[project](https://unity-technologies.github.io/PeopleSansPeople/))

Read the shape of that result honestly, because a customer will: **synthetic
pre-training is worth ~4.5 AP when real data is scarce and ~1.5 AP when it is
abundant.** The value of synthetic data is inversely proportional to how much
real labelled data you have — which is exactly the regime of a new site, a new
camera geometry, or a rare behaviour.

### 7.4 Synthehicle, and the multi-camera pattern

"17 hours of labeled video material, recorded from 340 cameras placed around
crossroads and highways in 64 diverse day, rain, dawn and night scenes", with
"ground truth for 2D detection and tracking, 3D detection and tracking, depth
estimation, and semantic, instance and panoptic segmentation", plus "a public
evaluation server"
([Synthehicle, WACVW 2023](https://openaccess.thecvf.com/content/WACV2023W/RWS/papers/Herzog_Synthehicle_Multi-Vehicle_Multi-Camera_Tracking_in_Virtual_Cities_WACVW_2023_paper.pdf),
[code](https://github.com/fubel/synthehicle)). Vehicles, not people, but the
template — many cameras, weather-stratified scenes, all annotation modalities,
an evaluation server — is the one to copy, and its MTMC evaluation code is
listed in our reuse inventory.

### 7.5 Others, and the honest caveats

**BEDLAM** (SMPL-X bodies with simulated clothing) is the reference for body/
clothing realism and is already in our animation sourcing plan
([arXiv 2306.16940](https://arxiv.org/abs/2306.16940)); **UBnormal** supplies a
synthetic anomaly taxonomy; **CrowdSim2** targets crowd detection
([arXiv 2304.05090](https://arxiv.org/pdf/2304.05090)); **MultiviewX** and
**GMVD** replicate WILDTRACK-style rigs; **SDTracker**
([arXiv 2303.14653](https://arxiv.org/pdf/2303.14653)) is the "synthetic-data-based
MOT" follow-up to MOTSynth.

The caveats a veteran states before the reviewer does:

* GTA-V-derived data (JTA, MOTSynth, MTA) carries EULA risk and is Windows-only
  and mod-fragile. Excellent science, poor supply chain.
* Sim2real gains are reported on *benchmarks whose domain resembles the
  simulator* (street-level, 25–30 fps, HD). Nobody has published a comparable
  result for 4 fps, 1 Mbps, IR, 45°-depression CCTV — which is both the gap and
  our opportunity.
* Synthetic data reliably fixes **geometry, occlusion topology and rare
  behaviour**; it much less reliably fixes **sensor appearance**. That is why
  §6's degradation model is a first-class component of the architecture and not
  a post-hoc filter.

---

## 8. Open problems, 2024–2026, and reading leaderboards honestly

**Leaderboard caveat first.** I could not access
[MOTChallenge](https://motchallenge.net/) or
[Papers with Code](https://paperswithcode.com/) in this pass, so all rankings
below are from paper self-reports and are ordinal, not current. The verified
per-method numbers gathered here:

| Method | Benchmark | Reported |
|---|---|---|
| ByteTrack | MOT17 test | 80.3 MOTA / 77.3 IDF1 / 63.1 HOTA, 30 FPS on one V100 |
| BoT-SORT-ReID | MOT17 test | 80.5 MOTA / 80.2 IDF1 / 65.0 HOTA — "first tracker to exceed an IDF1 score of 80" |
| Deep OC-SORT | MOT17 / MOT20 | 64.9 / 63.9 HOTA; 1st on MOT20, 2nd on MOT17 at time of publication |
| Deep OC-SORT | DanceTrack | 61.3 HOTA |
| StrongSORT++ | MOT17 | "ranks first on MOT17 in terms of HOTA and IDF1" (offline components) |
| MOTRv2 | DanceTrack | 69.9 HOTA; 73.4 HOTA with ensemble + val training + post-processing |
| MOTIP | DanceTrack / SportsMOT | 69.6 HOTA (no extra data) / 72.6 HOTA; 60.4 / 63.2 AssA |
| SAMURAI | LaSOT_ext, GOT-10k | +7.1% AUC, +3.5% AO over SAM 2 baseline |
| RAPiD | CEPDOF (fisheye) | AP₅₀ 85.8 vs previous best 76.9 |
| IterDet | CrowdHuman full-body | 95.80% recall, 88.08% AP |

Three structural reading rules `[practitioner lore, but defensible from the
papers above]`:

1. **Detector-normalise.** Most MOT17/20 entries use shared YOLOX weights. A
   two-point MOTA delta between two "trackers" can be a detector delta.
2. **Online vs offline.** AFLink/GSI-class post-processing, ensembling and
   validation-set training (all explicitly disclosed by MOTRv2 for its 73.4)
   are unavailable in a live alerting product.
3. **MOT17 is saturated and unrepresentative.** MOTA around 80 has been the
   ceiling for years, and the benchmark is 2.5 overlapping pairs per frame from
   a camera at head height. MOT20 (crowding), DanceTrack (non-linear motion,
   uniform appearance) and SportsMOT are where the discriminative signal is —
   and *none* of them is CCTV. That gap is the case for
   [SOMPT22](https://arxiv.org/html/2208.02580v1) and for our simulator.

**The open problems that are actually open, as of this writing:**

1. **Frame-rate-agnostic tracking.** Quantified in §3.12; partially addressed by
   [FraMOT](https://arxiv.org/abs/2209.11404) and ColTrack. Unsolved below 2 fps,
   which is where a lot of recorded CCTV lives.
2. **Long-horizon identity within one camera.** Minutes-to-hours re-appearance,
   online. No standard benchmark, no standard metric.
3. **Crowd-scale association.** The pair-overlap statistic grows roughly
   quadratically with density; MOT20 is 127/frame and real event crowds are
   denser still.
4. **Degradation robustness as a first-class axis.** There is no standard
   "detection under CCTV degradation" benchmark stratified by bitrate, IR,
   weather and pixel height. The
   [ETRI compression benchmark](https://onlinelibrary.wiley.com/doi/10.4218/etrij.2025-0363)
   and [A Perspective on Deep Vision Performance with Standard Image and Video
   Codecs](https://arxiv.org/pdf/2404.12330) are early steps. **This is the
   clearest gap SurvSim can fill and own.**
5. **Deployable reliability vs benchmark score.** A 2026 cross-dataset audit
   makes the argument in its title: *Benchmark AUC Is Not Deployable
   Reliability* ([arXiv 2606.29506](https://arxiv.org/pdf/2606.29506)). Expect
   the field to move toward cross-domain generalisation protocols; expect
   customers to have been there for twenty years.
6. **Foundation-model tracking.** SAM 2 / SAMURAI-class promptable trackers are
   excellent single-object, prompted, forensic tools, and not yet multi-target
   always-on systems. Bridging that is live work.
7. **Amodal vs visible boxes.** CrowdHuman's three-box annotation exposes a
   definitional split the metrics still do not handle cleanly, and it is the
   root of a lot of unexplained IoU-threshold sensitivity in crowds.
8. **Evaluation aligned to operations.** Nobody publishes false-alarms-per-hour
   at fixed recall, stratified by cause. That is the number the customer buys.

---

## 9. What a 20-year veteran knows that the papers don't say

Each item is tagged with a source or explicitly marked as lore.

1. **The camera install decides your accuracy, not the model.** Mounting height,
   depression angle, focal length and illuminator reach set the pixel height on
   target, and pixel height is the dominant term — TinyPerson's "average absolute
   size of target objects is about 18 pixels" with best-case AP₅₀^tiny around 57
   is the proof ([Scale Match](https://openaccess.thecvf.com/content_WACV_2020/papers/Yu_Scale_Match_for_Tiny_Person_Detection_WACV_2020_paper.pdf)).
   Two hours moving a camera beats two months of model work. `[lore + source]`
2. **Ask for the recorded stream, not the live stream.** Sites record at lower
   resolution, lower fps and lower bitrate than they preview at, and your
   forensic product runs on the recording. Detection accuracy saturates with
   bitrate, so there is a knee to find, not a fight to have
   ([ETRI](https://onlinelibrary.wiley.com/doi/10.4218/etrij.2025-0363)). `[lore + source]`
3. **Stop spending GPU on frame rate.** 30 → 3 fps is nearly free in association
   quality; below 2 fps it collapses — "AssA decreasing from 43.6% at 3 FPS to
   36.5% at 2 FPS and 27.8% at 1 FPS"
   ([Low-FPS MOT](https://www.mdpi.com/2079-9292/14/7/1373)). Run detection at
   4–6 fps and spend the rest on resolution, tiling or more cameras. `[source]`
4. **Decode, not inference, is your first wall.** Fixed-function decoders have
   hard stream limits and published analytics throughput figures assume
   generous inference intervals and no tracker; read NVIDIA's
   [performance tables](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html)
   with that in mind, and note that "18 streams of 1080p30" on an Orin NX 16GB
   ([Seeed](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/))
   is a model-and-config-specific figure, not a property of the board. `[lore + source]`
5. **The moth is unsolvable in appearance space.** An insect centimetres from the
   lens subtends the same angle as a person at 40 m; the field's own remedies
   are insecticide, brushing webs, and "Hang an electric bug zapper at least six
   feet from the camera and three feet higher than the lens"
   ([Fora Soft](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy)).
   Budget for a defocus/parallax/near-field-motion rejector, and for the
   installer's site visit. `[lore + source]`
6. **Night detection range is the illuminator's range.** Nothing in the model
   recovers a person beyond the IR reach. Conversely, in *thermal*, night can be
   easier than day — C²Former reports "28.48 miss rate (MR) on the 'Day' subset,
   26.67 MR on the 'Night' subset" ([C²Former](https://arxiv.org/pdf/2306.16175)).
   Use this to steer sensor choice, not to argue about models. `[lore + source]`
7. **Your worst false positives are stationary and eternal.** A reflection, a
   poster, a mannequin, a screen showing people. CEPDOF includes "images of
   people on projection screens" as a named challenge
   ([CEPDOF](https://vip.bu.edu/projects/vsns/cossy/datasets/cepdof)). Precision
   measured per-frame on a clip hides these; precision measured per-day on a
   fixed scene exposes them. Always evaluate on at least 24 continuous hours of
   the actual camera. `[lore + source]`
8. **Track lifecycle parameters beat algorithm choice.** `max_age`,
   `min_hits`/confirmation count, birth thresholds and the coast policy move
   IDF1 and false-alarm rate more than swapping ByteTrack for BoT-SORT, and
   nobody publishes them because they are per-site. Expose them in config, log
   them with every result, and version them per camera. `[lore]`
9. **Half the leaderboard is offline.** StrongSORT++'s first place rests on
   AFLink and GSI, which use future frames
   ([StrongSORT](https://arxiv.org/abs/2202.13514)), and MOTRv2's 73.4 HOTA
   involves "an ensemble of 4 models" and validation-set training
   ([MOTRv2](https://arxiv.org/abs/2211.09791)). Know which product line you are
   quoting into: forensic review may use offline methods; live alerting cannot.
   `[source]`
10. **Keep the low-confidence detections.** ByteTrack's entire contribution, and
    the single cheapest large win available on surveillance footage, because the
    occluded and distant person *is* the low-score box
    ([ByteTrack](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136820001.pdf)).
    `[source]`
11. **Height is depth on a fixed camera, and depth breaks ties.** Hybrid-SORT's
    Height Modulated IoU "combines Height IoU with conventional IoU to improve
    discrimination for clustered objects using stable height information"
    ([Hybrid-SORT](https://arxiv.org/abs/2308.00783)). On a calibrated fixed
    CCTV view this is nearly free and disproportionately effective in queues.
    `[source + lore]`
12. **Compensate camera motion even on "fixed" cameras.** Poles oscillate in
    wind, housings settle, and PTZ presets drift mechanically over months. CMC
    via "OpenCV's Video Stabilization module with affine transformation…
    and RANSAC" ([BoT-SORT](https://arxiv.org/abs/2206.14651)) costs little and
    prevents a whole class of mysterious ID-switch bursts correlated with
    weather. `[source + lore]`
13. **Nobody will ever label your real data densely.** MEVA annotated 144 of
    9300 hours ([MEVA](https://mevadata.org/)); WILDTRACK's entire ground truth
    is 400 frames ([WILDTRACK](https://infoscience.epfl.ch/record/256268)). Plan
    for synthetic ground truth, weak labels and targeted human review — not for
    a labelling campaign. `[source]`
14. **Diversity beats volume in synthetic data.** MOTSynth's own conclusion:
    "The diversity of MOTSynth is identified as more crucial for bridging the
    domain gap than sheer data volume, with smaller, more diverse subsets
    yielding significant improvements"
    ([MOTSynth](https://openaccess.thecvf.com/content/ICCV2021/papers/Fabbri_MOTSynth_How_Can_Synthetic_Data_Help_Pedestrian_Detection_and_Tracking_ICCV_2021_paper.pdf)).
    Randomise camera geometry and lighting before you render another million
    frames of the same plaza. `[source]`
15. **Synthetic pre-training pays most when real data is scarce.**
    PeopleSansPeople: +4.6 keypoint AP over real-only in the few-shot regime
    (60.37 vs 55.80), +1.47 in the abundant regime
    ([PeopleSansPeople](https://arxiv.org/abs/2112.09290v1)). Pitch it for new
    sites, new geometries and rare behaviours, not as a universal accuracy
    upgrade. `[source]`
16. **Report DetA and AssA, never HOTA alone.** HOTA exists because "MOTA and
    IDF1 overemphasize the effect of accurate detection and association
    respectively" ([HOTA](https://www.cvlibs.net/publications/Luiten2020IJCV.pdf));
    throwing away the decomposition throws away the diagnosis. `[source]`
17. **Convert every metric into the operator's units before the meeting.**
    FPPI × fps × 3600 = false alarms per camera-hour; recall *at the required
    pixel height* is the missed-alarm rate. Log-average miss rate over
    "10^-2 to 10^0 FPPI" ([Caltech](https://authors.library.caltech.edu/records/e69e6-ezc50))
    is the metric family that survives this translation; mAP is not. `[lore + source]`
18. **The integration is the product.** If the detection does not arrive in
    XProtect / Security Center / ACC as an event with a bookmark on the right
    timeline, it does not exist. Milestone's metadata path is deliberately
    decoupled — "A common exchange format, the ONVIF MetadataStream schema,
    decouples the producer from the consumer"
    ([Milestone MIP](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html))
    — and multi-vendor metadata is still where deployments fail: "Streams are
    easy… Metadata is where multi-vendor deployments fall apart"
    ([Fora Soft](https://www.forasoft.com/blog/article/onvif-profile-m)). `[source]`
19. **Distrust every "90% fewer false alarms" claim, including your own.**
    Vendors converge on that exact figure
    ([Lumana](https://www.lumana.ai/blog/how-ai-powered-video-analytics-cut-false-alarms-by-up-to-90),
    [Scylla](https://www.scylla.ai/how-ai-video-analytics-helps-reduce-false-alarms/)),
    and the baseline is always raw motion detection — which, per
    [Fora Soft](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy),
    can produce "well over a thousand nuisance alarms a day" on 40 cameras. A
    90% reduction from an absurd baseline is still an unusable system. Quote
    absolute alarms per camera-day, at a stated recall. `[lore + source]`
20. **Loitering detection sits on the tracker's weakest regime.** The behaviour
    customers most want requires holding identity on a *stationary* person —
    precisely the case where background models absorb the target and motion cues
    vanish. Build it on tracklet re-linking plus an appearance gallery, and test
    it against a scenario where someone stands still for ten minutes. `[lore]`
21. **Ethics and provenance are engineering constraints.** DukeMTMC was
    withdrawn by its own authors; i-LIDS ships under restrictive government
    terms. A dataset choice can become a contractual problem years later.
    Document provenance and licence for every training source, from day one.
    `[lore; licence status unverified in this pass — check before relying on it]`

---

## Sources

**Datasets and benchmarks**
- MOT20 / MOTChallenge — [arXiv 2003.09003](https://arxiv.org/pdf/2003.09003) · [MOTChallenge IJCV](https://link.springer.com/article/10.1007/s11263-020-01393-0) · [BMTT 2022 workshop: "How Far Can Synthetic Data Take us?"](https://motchallenge.net/workshops/bmtt2022/)
- CrowdHuman — [arXiv 1805.00123](https://arxiv.org/abs/1805.00123)
- CityPersons occlusion subsets — [table](https://www.researchgate.net/figure/Subsets-of-CityPersons-dataset-based-on-visibility_tbl2_372331924) · [PSC-Net](https://arxiv.org/pdf/2001.09252) · [MSFM-Net](https://arxiv.org/pdf/2010.10744)
- EuroCity Persons — [dataset site](https://eurocity-dataset.tudelft.nl/) · [arXiv 1805.07193](https://arxiv.org/abs/1805.07193)
- TinyPerson / Scale Match — [WACV 2020](https://openaccess.thecvf.com/content_WACV_2020/papers/Yu_Scale_Match_for_Tiny_Person_Detection_WACV_2020_paper.pdf) · [arXiv 1912.10664](https://arxiv.org/pdf/1912.10664)
- VIRAT — [viratdata.org](https://viratdata.org/) · [OpenTraj notes](https://github.com/crowdbotp/OpenTraj/blob/master/datasets/VIRAT/README.md) · [OD-VIRAT benchmark](https://arxiv.org/pdf/2507.12396)
- MEVA / ActEV — [WACV 2021 paper](https://openaccess.thecvf.com/content/WACV2021/papers/Corona_MEVA_A_Large-Scale_Multiview_Multimodal_Video_Dataset_for_Activity_Detection_WACV_2021_paper.pdf) · [mevadata.org](https://mevadata.org/) · [NIST ActEV](https://www-nlpir.nist.gov/projects/tv2022/actev.html) · [AWS Open Data](https://registry.opendata.aws/mevadata/)
- WILDTRACK — [EPFL Infoscience](https://infoscience.epfl.ch/record/256268) · [arXiv 1707.09299](https://arxiv.org/abs/1707.09299)
- SOMPT22 (surveillance-oriented MOT) — [arXiv 2208.02580](https://arxiv.org/html/2208.02580v1)
- KAIST multispectral — [benchmark site](https://soonminhwang.github.io/rgbt-ped-detection/) · [C²Former](https://arxiv.org/pdf/2306.16175) · [multispectral resource list](https://github.com/CalayZhou/Multispectral-Pedestrian-Detection-Resource)
- Fisheye — [CEPDOF](https://vip.bu.edu/projects/vsns/cossy/datasets/cepdof) · [WEPDTOF](https://www.researchgate.net/publication/363115429_WEPDTOF_A_Dataset_and_Benchmark_Algorithms_for_In-the-Wild_People_Detection_and_Tracking_from_Overhead_Fisheye_Cameras) · [Frontiers survey](https://www.frontiersin.org/journals/imaging/articles/10.3389/fimag.2024.1387543/full)

**Detection**
- Dalal & Triggs, HOG — [CVPR 2005 PDF](https://lear.inrialpes.fr/people/triggs/pubs/Dalal-cvpr05.pdf)
- Dollár et al., Caltech evaluation — [CaltechAUTHORS](https://authors.library.caltech.edu/records/e69e6-ezc50)
- Benenson et al., Ten Years of Pedestrian Detection — [arXiv 1411.4304](https://arxiv.org/pdf/1411.4304)
- ViBe — [official code](https://github.com/vandroogenbroeckmarc/vibe) · [ORBi record](https://orbi.uliege.be/handle/2268/12087)
- CrowdDet — [arXiv 2003.09163](https://arxiv.org/abs/2003.09163) · [code](https://github.com/xg-chu/CrowdDet)
- IterDet — [arXiv 2005.05708](https://arxiv.org/pdf/2005.05708) · [code](https://github.com/SamsungLabs/iterdet)
- End-to-end FCN detection (NMS-free) — [arXiv 2012.03544](https://arxiv.org/pdf/2012.03544)
- SAHI — [arXiv 2202.06934](https://arxiv.org/abs/2202.06934) · [LearnOpenCV](https://learnopencv.com/slicing-aided-hyper-inference/) · [adaptive SAHI](https://arxiv.org/html/2604.19233v1)
- Tiny-object backbones / anti-aliasing / label assignment — [arXiv 2303.11267](https://arxiv.org/pdf/2303.11267) · [arXiv 2310.14221](https://arxiv.org/pdf/2310.14221) · [arXiv 2407.02394](https://arxiv.org/pdf/2407.02394)
- RAPiD (rotation-aware fisheye) — [arXiv 2005.11623](https://arxiv.org/pdf/2005.11623) · [CVPRW 2020](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w38/Duan_RAPiD_Rotation-Aware_People_Detection_in_Overhead_Fisheye_Images_CVPRW_2020_paper.pdf)

**Tracking**
- ByteTrack — [ECCV 2022 PDF](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136820001.pdf) · [code](https://github.com/FoundationVision/ByteTrack)
- BoT-SORT — [arXiv 2206.14651](https://arxiv.org/abs/2206.14651) · [code](https://github.com/NirAharon/BoT-SORT)
- OC-SORT — [CVPR 2023 PDF](https://openaccess.thecvf.com/content/CVPR2023/papers/Cao_Observation-Centric_SORT_Rethinking_SORT_for_Robust_Multi-Object_Tracking_CVPR_2023_paper.pdf) · [code](https://github.com/noahcao/OC_SORT)
- Deep OC-SORT — [arXiv 2302.11813](https://arxiv.org/abs/2302.11813)
- StrongSORT / StrongSORT++ — [arXiv 2202.13514](https://arxiv.org/abs/2202.13514) · [code](https://github.com/dyhBUPT/StrongSORT)
- Hybrid-SORT — [arXiv 2308.00783](https://arxiv.org/abs/2308.00783) · [AAAI 2024](https://ojs.aaai.org/index.php/AAAI/article/view/28471)
- UCMCTrack — [arXiv 2312.08952](https://arxiv.org/pdf/2312.08952)
- MOTRv2 — [arXiv 2211.09791](https://arxiv.org/abs/2211.09791) · [CVPR 2023 PDF](https://openaccess.thecvf.com/content/CVPR2023/papers/Zhang_MOTRv2_Bootstrapping_End-to-End_Multi-Object_Tracking_by_Pretrained_Object_Detectors_CVPR_2023_paper.pdf)
- MOTIP — [CVPR 2025 PDF](https://openaccess.thecvf.com/content/CVPR2025/papers/Gao_Multiple_Object_Tracking_as_ID_Prediction_CVPR_2025_paper.pdf) · [arXiv 2403.16848](https://arxiv.org/abs/2403.16848) · [code](https://github.com/MCG-NJU/MOTIP)
- SAMURAI / SAM 2 tracking — [arXiv 2411.11922](https://arxiv.org/abs/2411.11922) · [project page](https://yangchris11.github.io/samurai/)
- FraMOT (frame-rate-agnostic MOT) — [arXiv 2209.11404](https://arxiv.org/abs/2209.11404)
- Low-FPS multi-object multi-camera tracking — [Electronics 14(7):1373](https://www.mdpi.com/2079-9292/14/7/1373)
- DiffMOT / learned filters — [arXiv 2403.02075](https://arxiv.org/pdf/2403.02075) · [arXiv 2402.09865](https://arxiv.org/pdf/2402.09865)
- Kalman filters for fast tiny objects — [arXiv 2509.18451](https://arxiv.org/pdf/2509.18451)
- Tracklet clustering / hierarchical association — [arXiv 2210.03355](https://arxiv.org/pdf/2210.03355) · [PMC9955888](https://pmc.ncbi.nlm.nih.gov/articles/PMC9955888/)
- NOOUGAT (unified online/offline MOT) — [arXiv 2509.02111](https://arxiv.org/pdf/2509.02111)
- Edge tracking measurement study — [arXiv 2309.02666](https://arxiv.org/pdf/2309.02666)

**Metrics**
- HOTA — [IJCV PDF](https://www.cvlibs.net/publications/Luiten2020IJCV.pdf) · [arXiv 2009.07736](https://arxiv.org/abs/2009.07736) · [author's explainer](https://autonomousvision.github.io/hota-metrics/)
- TrackEval — [github.com/JonathonLuiten/TrackEval](https://github.com/JonathonLuiten/TrackEval)
- Benchmark-vs-deployment audit — [arXiv 2606.29506](https://arxiv.org/pdf/2606.29506)

**Deployment, standards, VMS**
- DeepStream performance — [current docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html) · [SDK page](https://developer.nvidia.com/deepstream-sdk) · [Jetson Orin video analytics](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/)
- Hailo-8 — [product page](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/) · [product brief](https://hailo.ai/hailo-files/hailo-8-product-brief-en/) · [independent comparison](https://edgeaistack.ai/blog/hailo-8-vs-8l-vs-10h-2026/)
- ONVIF — [Profile M](https://www.onvif.org/profiles/profile-m/) · [Profile M spec v1.0](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf) · [Profile T](https://www.onvif.org/profiles/profile-t/) · [Streaming spec](https://www.onvif.org/specs/stream/ONVIF-Streaming-Spec.pdf) · [Profile M in practice](https://www.forasoft.com/blog/article/onvif-profile-m)
- Milestone XProtect — [developer portal](https://www.milestonesys.com/support/for-developers/integrate-with-xprotect/) · [metadata intro](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html) · [integration overview](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/Integration_overview.html) · [metadata integration decision guide (PDF)](https://dqhg7aoeit2za.cloudfront.net/m/0347c6383aa05741/original/Metadata-Integrations-with-XProtect-MIP-SDK-Decision-Guide.PDF)
- Compression vs detection — [ETRI Journal benchmark](https://onlinelibrary.wiley.com/doi/10.4218/etrij.2025-0363) · [Video Compression for Object Detection Algorithms (ICPR'18)](https://flore.unifi.it/bitstream/2158/1140979/1/ICPR18_1121_FI.pdf) · [Deep vision with standard codecs](https://arxiv.org/pdf/2404.12330)

**Operational / false alarms**
- [Tuning Analytics: False Alarms, Accuracy & the Operator (Fora Soft)](https://www.forasoft.com/learn/video-surveillance/articles-vms/tuning-analytics-false-alarms-accuracy)
- [IPVM: specifying video analytics performance / false alarm rate](https://ipvm.com/discussions/end-user-how-do-i-specify-video-analytics-performance-false-alarm-rate)
- [Davantis: false alarms vs false negatives](https://www.davantis.com/en/blog/technology/false-alarms-false-negatives/) · [IntelliSee](https://intellisee.com/98-of-security-camera-alarms-are-false-heres-what-thats-actually-costing-you/) · [Lumana](https://www.lumana.ai/blog/how-ai-powered-video-analytics-cut-false-alarms-by-up-to-90) · [Scylla](https://www.scylla.ai/how-ai-video-analytics-helps-reduce-false-alarms/) · [VDS](https://visiondetectionsystems.com/blog/how-to-reduce-false-alarms-in-video-analytics)
- [Reolink: flying bugs on night-vision cameras](https://reolink.com/blog/flying-bugs-on-night-vision-cameras/) · [Trunetto: rain and wind false alerts](https://www.trunetto.com/troubleshooting/security-cameras/reolink/reolink-camera-false-motion-alerts-rain-wind)

**Synthetic data**
- MOTSynth — [ICCV 2021 PDF](https://openaccess.thecvf.com/content/ICCV2021/papers/Fabbri_MOTSynth_How_Can_Synthetic_Data_Help_Pedestrian_Detection_and_Tracking_ICCV_2021_paper.pdf) · [arXiv 2108.09518](https://arxiv.org/pdf/2108.09518)
- JTA — [ECCV 2018 PDF](https://openaccess.thecvf.com/content_ECCV_2018/papers/Matteo_Fabbri_Learning_to_Detect_ECCV_2018_paper.pdf) · [arXiv 1803.08319](https://arxiv.org/pdf/1803.08319)
- PeopleSansPeople — [arXiv 2112.09290](https://arxiv.org/abs/2112.09290v1) · [project](https://unity-technologies.github.io/PeopleSansPeople/) · [code](https://github.com/Unity-Technologies/PeopleSansPeople)
- Synthehicle — [WACVW 2023 PDF](https://openaccess.thecvf.com/content/WACV2023W/RWS/papers/Herzog_Synthehicle_Multi-Vehicle_Multi-Camera_Tracking_in_Virtual_Cities_WACVW_2023_paper.pdf) · [code](https://github.com/fubel/synthehicle)
- SDTracker — [arXiv 2303.14653](https://arxiv.org/pdf/2303.14653) · "So you think you can track?" — [arXiv 2309.07268](https://arxiv.org/pdf/2309.07268)
- BEDLAM — [arXiv 2306.16940](https://arxiv.org/abs/2306.16940) · CrowdSim2 — [arXiv 2304.05090](https://arxiv.org/pdf/2304.05090)

---

*Written for SurvSim / multi-person-camera-real-sim. Companion documents:
[01 Research Landscape](../01_RESEARCH_LANDSCAPE.md),
[02 Architecture](../02_ARCHITECTURE.md),
[06 Realism and Sensor Model](../06_REALISM_AND_SENSOR_MODEL.md),
[07 Evaluation and Algo Sandbox](../07_EVALUATION_AND_ALGO_SANDBOX.md).*
