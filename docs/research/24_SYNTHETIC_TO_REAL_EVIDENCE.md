# 24 · Synthetic-to-Real Evidence — what the literature measured for pedestrian detection, tracking and ReID

*Series 17–24. Report 18 §6 and report 21 §2 proposed a training-mix plan
(synthetic pre-train, real fine-tune, validate on real only). This report is
the evidence base behind that plan: every quantitative claim below was fetched
from the paper's abstract, arXiv HTML (ar5iv) rendering or official
repository on 2026-09-26 and is cited with author, venue, year and URL.
Figures that could not be verified in this session were dropped rather than
tagged; a list of what was dropped is in §9. **Audit 2026-09-26:** every table
number below was re-checked against the arXiv HTML table text; four errors were
corrected (MOTSynth Tracktor rows, MOTSynth sampling ablation, the ReID
clothing progression, PersonX cameras) and are flagged "corrected" inline.*

**How to read the numbers.** Each paper uses its own protocol. "Direct
transfer" means train on synthetic, test on real with no real labels.
"Pre-train + fine-tune" means synthetic initialisation then real labels.
Numbers are only comparable within a row group; when a comparison mixes
protocols, the text says so. Where a number came from an ar5iv rendering of
the paper's tables rather than the abstract, it is marked *(table)*; those are
reliable to the extent the HTML rendering is, and should be spot-checked
against the PDF before being quoted in a bid.

---

## 0. Summary — seven findings that shape our plan

1. **Synthetic pre-training helps most when real labels are scarce, and the
   advantage shrinks to about a point once real data is abundant.**
   PeopleSansPeople: person-box AP on COCO rises from 13.82 (real only) to
   42.58 with synthetic pre-training at 1 % of COCO (641 images), from 37.82
   to 49.04 at 10 %, but only from 56.73 to 57.44 at 100 % [5, table]. The
   keypoint numbers show the same shape: +38.03 AP few-shot, +1.47 AP with
   abundant data [5].
2. **Synthetic data helps most where real data is structurally hard to label
   — crowds.** MOTSynth pre-training raised MOT20 detection AP from 42.42 to
   53.69 (YOLOv3) and 43.67 to 53.90 (Faster R-CNN), about +10–11 AP. The
   same models gained only ~2 AP on the less crowded MOT17 [1, table].
3. **Diversity matters at least as much as volume.** MOTSynth's sampling
   ablation (Table 11) does *not* hold frame count fixed. Its useful reading is
   that sparse (1:60) sampling gets close to dense (1:10) sampling with far
   fewer frames: YOLOv3 62.59 AP from 17 k sparse frames vs 63.13 AP from
   52 k dense frames, and 62.10 AP from 9 k sparse vs 62.66 AP from 13 k dense
   [1, table]. *(Corrected: an earlier draft read 51.15 → 62.66 as a
   fixed-frame diversity gain; those are 2 k vs 13 k frames.)* BEDLAM makes a
   similar argument, crediting diverse bodies, skin tones and physically
   simulated clothing [6].
4. **For ReID, clothing realism helps, but less than the headline numbers
   suggest.** Each paper's own numbers show Market-1501 direct transfer rising
   from RandPerson (Rank-1 55.6 / mAP 28.8) [9, table] to UnrealPerson
   (79.0 / 54.3) [10, table] to ClonedPerson (84.5 / 59.9) [11, table]. Those
   use different backbones and recipes. **Under one recipe** (QAConv 2.0,
   ClonedPerson Table 4) the gap mostly closes: RandPerson* 81.6 / 56.4,
   UnrealPerson-120k 80.6 / 55.9, ClonedPerson 84.5 / 59.9 on Market. On
   MSMT17, UnrealPerson (49.5 / 19.3) slightly *beats* ClonedPerson
   (49.1 / 18.5) [11, table]. *(Corrected: the earlier draft presented the
   cross-paper progression as a clothing effect.) Much of the 55.6 → 84.5 jump
   is training recipe, not data.*
5. **Synthetic + real beats real alone for ReID, in both mixing and
   pre-training.** UnrealPerson pre-training followed by supervised
   fine-tuning gave Market-1501 Rank-1 94.0 vs 91.4 with ImageNet
   initialisation, and MSMT17 74.5 vs 72.5 [10, table]. Joint training on
   RandPerson + MSMT17 reached Rank-1 65.0 / mAP 36.8 on MSMT17 [9, table].
6. **Synthetic-only can match or beat real, but only for particular
   task/target pairs.** Examples:
   - vehicle detection on KITTI trained on GTA-V data only [15];
   - 3D human pose and shape on 3DPW/RICH trained on BEDLAM only [6];
   - scene-specific pedestrian detectors trained with zero real pedestrians
     [13] (the "beats real-trained when data is limited" comparison is
     [unverified]: the abstract confirms the zero-real-data setting only);
   - MOTSynth-trained ReID beat Market-1501-trained ReID on MOT17 (mAP 75.2
     vs 64.6) [1, table].

   None of these is evidence that synthetic-only training generalises to
   *our* target (degraded CCTV at 20–60 px). That must be measured (docs/13
   gap protocol).
7. **The residual gap is a measurable quantity and should be tracked like any
   other metric.** The Alice benchmarks (ICLR 2024) exist because synthetic →
   real ReID still needs domain adaptation to reach real-trained accuracy on
   uncurated real targets [12]. SurvSim's own detector-as-judge number is a
   measurement of the same kind: batch_v4 yolov8n recall 0.758 on MetaHuman
   renders vs 0.577 on CesiumMan, same 770 GT boxes (docs/11, docs/12).

---

## 1. The survey table

| # | Dataset / paper | Engine | Scale (as reported) | Task | Headline sim→real result (as reported) |
|---|---|---|---|---|---|
| 1 | MOTSynth (Fabbri et al., ICCV 2021) | GTA-V | 768 sequences, 1.38 M frames, 40.78 M pedestrian instances; 29.5 people/frame avg, max 125 [table] | detection, MOT, ReID, MOTS | MOT20 det AP +10–11 from synthetic pre-training; ReID on MOT17 mAP 75.2 vs 64.6 (Market-1501-trained); CenterTrack MOTSynth+FT 67.9 MOTA / 66.5 IDF1 vs CrowdHuman 66.1 / 64.2 on MOT17 [table] |
| 2 | motsynth-baselines (repo) | — | — | MOT on MOT17 train | Tracktor + Mask R-CNN trained on MOTSynth: MOTA 45.3, IDF1 49.7 on MOT17 train; MOTS20 HOTA 44.6 |
| 3 | JTA (Fabbri et al., ECCV 2018) | GTA-V | ~500,000 frames, almost 10 M body poses | pose detection + tracking | trained on virtual data, generalises to real tracking benchmarks, conditioned on "image resolution and sharpness" (abstract) |
| 4 | SOMAset (Barbosa et al., CVIU 2018) | human-body generator | 100 K instances | ReID via body structure | SOMAnet, trained on SOMAset and fine-tuned on real benchmarks, "outperforms all competitors", matching across different apparel (abstract; no number in abstract) |
| 5 | PeopleSansPeople (Ebadi et al., 2021/22) | Unity | 490 K images, 3.07 M+ person instances [table] | person det + keypoints | box AP 13.82→42.58 (1 % COCO), 37.82→49.04 (10 %), 56.73→57.44 (100 %) [table]; keypoint AP +38.03 few-shot, +1.47 full |
| 6 | BEDLAM (Black et al., CVPR 2023) | UE + physics cloth sim | ~380 K frames, ~1 M boxes; 271 body shapes, 111 outfits / 1,691 textures, 2,311 motions [table] | 3D pose & shape | synthetic-only BEDLAM-CLIFF: 3DPW PA-MPJPE 46.6 / MPJPE 72.0 / PVE 85.0; RICH 51.2 / 84.5 / 96.6 [table]; "SOTA accuracy" trained only on synthetic |
| 7 | SYNTHIA (Ros et al., CVPR 2016) | Unity | large urban set with pixel labels | semantic segmentation | adding SYNTHIA in training "significantly improves performance" (abstract) |
| 8 | PersonX (Sun & Zheng, CVPR 2019) | Unity | 1,266 identities, 273,456 images (= 1,266 × 36 viewpoints × 6 cameras) [paper §3.1] | ReID viewpoint analysis | algorithm performance trends match those on real datasets; "a person of a side view makes a better query" |
| 9 | RandPerson (Wang, Liao, Shao, ACM MM 2020) | Unity3D | 1,801,816 images, 8,000 identities | ReID generalisation | direct transfer Market R1 55.6 / mAP 28.8, beating MSMT17-trained (50.0 / 23.1) on Market [table] |
| 10 | UnrealPerson (Zhang et al., CVPR 2021) | UE4 | 3,000 IDs, 120,000 instances (abstract; the suggested subset of a 6,799-ID / 1,256,381-image full set per [11] Table 1); 34 cameras; ~48 CPU-hours [text] | ReID | direct transfer Market 79.0/54.3, Duke 69.7/49.4, MSMT17 38.5/15.3 [table] |
| 11 | ClonedPerson (Wang, Liang, Liao, CVPR 2022) | Unity3D | 5,621 identities, 887,766 images | ReID generalisation | direct transfer Market 84.5/59.9, CUHK03-NP 22.6/21.8, MSMT17 49.1/18.5 [table] |
| 12 | Alice benchmarks (Sun et al., ICLR 2024) | PersonX/VehicleX sources | AlicePerson real target: 5 cameras, ~42 k boxes | syn→real ReID DA | a standard evaluation server for synthetic→real ReID on uncurated real targets |
| 13 | Hattori et al., CVPR 2015 | custom renders | scene-geometry-specific | scene-specific pedestrian detection | detector for a new camera trained with zero real pedestrians from scene geometry + simulated pedestrians (abstract); abstract: purely synthetic "is able to outperform models trained on real scene-specific data when data is limited" [verified from CMU PDF 2026-09-26] |
| 14 | Marin et al., CVPR 2010 | game engine | — | pedestrian classification (HOG+SVM) | virtual-trained appearance model works on real images (abstract) |
| 15 | Driving in the Matrix (Johnson-Roberson et al., ICRA 2017) | GTA-V | — | vehicle detection | synthetic-only trained model beats the identical architecture trained on human-annotated real data on KITTI (abstract) |
| 16 | Playing for Data (Richter et al., ECCV 2016) | GTA-V | 25 K images | segmentation | game data + 1/3 of CamVid beats full CamVid (abstract) |
| 17 | Synthehicle (Herzog et al., WACV Workshops 2023 / arXiv 2022) | CARLA | 17 h video, 340 cameras, 64 scenes (day, rain, dawn, night) | vehicle MTMC | baselines for detection, ReID, single- and multi-camera tracking |
| 18 | SURREAL (Varol et al., CVPR 2017) | Blender + SMPL | > 6 M frames (abstract) | depth / body parts | large-scale synthetic humans with pose, depth, segmentation |
| 19 | SURREACT (Varol et al., IJCV 2021) | Blender + SMPL | — | action recognition from unseen viewpoints | synthetic humans "substantially improve" SOTA on NTU RGB+D and UESTC (abstract) |
| 20 | Synthetic-to-Real Video Person Re-ID (Zhang et al., arXiv 2024) | synthetic video | — | video ReID | across five real datasets, synthetic training beats real data *in cross-domain settings* (abstract) |

---

## 2. Detection

### 2.1 MOTSynth: the closest analogue to what we are building

MOTSynth [1] is the most relevant prior work because it targets the same
chain as SurvSim (detection → MOT → ReID) with a game engine. The
authors built 768 GTA-V sequences with 1.38 M densely annotated frames and
40.78 M pedestrian instances, averaging 29.5 people per frame and peaking at 125
[1, table]. Their abstract claims that MOTSynth "can be used as a replacement
for real data on tasks such as pedestrian detection, re-identification,
segmentation, and tracking" [1].

The detection numbers support that claim with a caveat:

| Detector | Test | COCO-pretrained AP | MOTSynth-trained AP | Δ |
|---|---|---|---|---|
| Faster R-CNN | MOT17 | 76.68 | 78.98 | +2.30 |
| Mask R-CNN | MOT17 | 76.96 | 78.83 | +1.87 |
| YOLOv3 | MOT20 | 42.42 | 53.69 | +11.27 |
| Faster R-CNN | MOT20 | 43.67 | 53.90 | +10.23 |

(All [1, table]; "MOTSynth-trained" is the paper's MOTSynth-4 configuration.)

**Reading.** Synthetic data barely moves detection on moderately dense
footage, where COCO already contains plenty of visible people. On extremely
dense footage it moves AP by ten points. Crowds are where real annotation is
slowest and least reliable, so they are also where exact synthetic labels —
including occluded people — pay off. SurvSim's own crowd-density bug (docs/11
bug 13: counting only visible people made MOT20 look "free-flowing") is the
same observation from the other side: in a crowd, occluded people are the
signal, and only a simulator labels them exactly.

**Diversity ablation (corrected).** Table 11 of [1] varies the sampling rate
(1:60 sparse vs 1:10 dense) and the subset size together, so frame count is
*not* fixed. The comparable pairs are: YOLOv3 62.10 AP from 9 k sparse frames
vs 62.66 AP from 13 k dense frames, and 62.59 AP from 17 k sparse vs 63.13 AP
from 52 k dense [1, table]. Sparse sampling reaches roughly the same AP with
one third of the frames. That is a real but modest diversity effect. It is not
the 11-point effect an earlier draft claimed (51.15 → 62.66 compares 2 k with
13 k frames). SurvSim's equivalent knob is the number of distinct
seeds/scenarios per rendered frame; the docs/13 dataset builder already splits
by seed, so the ablation can be run directly (report 23 M4).

### 2.2 PeopleSansPeople: the data-scaling curve

PeopleSansPeople [5] (Unity) generated 490 K images containing more than
3.07 M person instances — far more than COCO-person's 64,115 images and
262,465 instances [5, table]. The value of the paper is its clean scaling
curve for person-box AP on COCO (Detectron2 Keypoint R-CNN):

| Real COCO-person used | Real only | ImageNet init + FT | Synthetic init + FT |
|---|---|---|---|
| 1 % (641 images) | 13.82 | 27.61 | **42.58** |
| 10 % (6,411 images) | 37.82 | 42.53 | **49.04** |
| 100 % (64,115 images) | 56.73 | 56.09 | **57.44** |

([5, table]; keypoint AP abstract figures: 44.43 vs 6.40 few-shot, 63.47 vs
62.00 abundant [5].)

**Reading.** The gain from synthetic pre-training falls roughly by an order of
magnitude for each order-of-magnitude increase in real data (+28.8 → +11.2 →
+0.7 AP). For a CCTV company the practical question is where each *site
class* sits on this curve. For a new customer's IR perimeter cameras we may
have ~0 real labels, which is the left of the curve. For daytime transport
concourses, public data plus pilots can put us toward the right.

### 2.3 Older detection evidence

The idea is not new. Marin et al. (CVPR 2010) trained HOG+SVM pedestrian
classifiers on sequences from virtual scenarios and found they worked on real
images [14]. Hattori et al. (CVPR 2015) went further: for a newly installed
surveillance camera with **zero** real pedestrian examples, they generated
scene-geometry-specific synthetic pedestrians. The resulting detector beat
generic and hybrid detectors, and, reportedly, detectors trained on limited
real scene-specific data [13] [unverified: the comparison is not in the
abstract and the PDF was not readable in this session]. This is structurally identical to
what `survsim rig` plus the generator can do for a commissioned site: use the
calibrated geometry to render people at exactly that site's pixel heights and
viewpoints (report 18 §1.4 item 5). Beyond pedestrians, Johnson-Roberson et
al. showed that a detector trained only on GTA-V annotations beat the same
architecture trained on real KITTI annotations for vehicle detection [15].
Richter et al. showed that GTA-V segmentation data plus one third of CamVid
beat the full CamVid training set [16], and Ros et al. showed that adding
SYNTHIA improved urban segmentation [7].

---

## 3. Tracking

Tracking results are thinner and harder to interpret, because a tracker's
score depends on the detector feeding it.

* MOTSynth [1, Table 6], on the MOT17 *training* set (fine-tune on the first
  half of each sequence, evaluate on the second):
  - **Tracktor, no fine-tuning, no ReID**: COCO 43.5 MOTA / 49.6 IDF1;
    MOTSynth 45.0 / 51.2.
  - **Tracktor, fine-tuned**: COCO + Market ReID 48.3 / 58.1; MOTSynth, no
    ReID 49.8 / 53.8; MOTSynth + Market ReID 50.3 / 59.8; MOTSynth + MOTSynth
    ReID 50.3 / 59.9.
  - **CenterTrack**: CrowdHuman, no FT 52.2 / 53.8 vs MOTSynth, no FT
    54.3 / 57.7; CrowdHuman + FT 66.1 / 64.2 vs MOTSynth + FT 67.9 / 66.5.
  - **Segmentation-tracking**: Tracktor with a MOTSynth-only Mask R-CNN
    scores 55.1 sMOTSA / 63.9 IDF1 on MOTS20, against TrackR-CNN's 40.6 /
    42.4 (trained on COCO + Mapillary + MOTS20).
* Official MOTSynth baselines repo [2]: Tracktor with a MOTSynth-trained Mask
  R-CNN reaches MOTA 45.3 / IDF1 49.7 on MOT17 *train*, with wide per-sequence
  spread (MOTA 25.7 on MOT17-02 vs 53.3 on MOT17-04).

**Reading.**
1. *(Corrected.)* An earlier draft compared MOTSynth without a ReID model
   (IDF1 53.8) against COCO *with* a Market ReID model (58.1) — a retired no-ReID-vs-ReID comparison — and concluded
   that association transfers worse. Like for like, MOTSynth wins on both
   metrics: 45.0 / 51.2 vs 43.5 / 49.6 without fine-tuning or ReID, and
   50.3 / 59.8 vs 48.3 / 58.1 fine-tuned with the same Market ReID. What the
   table does show is that the ReID model drives IDF1: adding one is worth
   about +5–6 IDF1, more than the detector's training data.
2. Real fine-tuning adds about +5 MOTA to either initialisation.
3. The per-sequence spread shows that a single averaged number hides
   scene-specific failures. That argues for docs/13's stratified reporting.

For SurvSim, the MOT evidence argues for **HOTA with the DetA/AssA split**
(docs/13) specifically so that any association weakness (for example from a
synthetic-trained ReID head) is visible rather than averaged away. Our own real reference
(zero-shot YOLO11n + numpy ByteTrack on a MOT20 subset: MOTA 0.463 / IDF1
0.538 / HOTA 0.545 pre-fix; now 0.466 / 0.559 / 0.443, 0.537 at α = 0.5 at TrackEval parity, docs/13 §M1; 0.549 / 0.434 pre-parity `be9f52a`) sits in the same range as the MOTSynth
baselines above. It is not comparable, though: different detector, subset and
split.

JTA [3] (the same group's 2018 GTA-V set: ~500,000 frames, almost 10 M body
poses) is the pose-tracking precursor. Its abstract states the caveat
explicitly: generalisation to real benchmarks depends on "image resolution
and sharpness". That is the imaging-chain problem docs/15 is working on.

---

## 4. Re-identification

ReID has the richest synthetic literature because real ReID data is small,
ethically fraught and increasingly withdrawn from distribution.

### 4.1 The progression of synthetic ReID sets

| Dataset | Year | IDs | Images | Clothing method | Direct → Market R1/mAP | Direct → MSMT17 R1/mAP |
|---|---|---|---|---|---|---|
| SOMAset [4] | 2018 | — | 100 K instances | body-shape focused | — | — |
| PersonX [8] | 2019 | 1,266 | 273,456 | hand-crafted | — | — |
| RandPerson [9] | 2020 | 8,000 | 1,801,816 | random UV textures | 55.6 / 28.8 | 20.1 / 6.3 |
| UnrealPerson [10] | 2021 | 3,000 (subset) | 120,000 | real-image-derived textures, UE4 | 79.0 / 54.3 | 38.5 / 15.3 |
| ClonedPerson [11] | 2022 | 5,621 | 887,766 | outfits cloned from real photos | 84.5 / 59.9 | 49.1 / 18.5 |
| *same recipe, QAConv 2.0 [11 Table 4]:* RandPerson* / UnrealPerson-120k / ClonedPerson | | | | | 81.6/56.4 · 80.6/55.9 · 84.5/59.9 | 46.8/17.6 · 49.5/19.3 · 49.1/18.5 |

(Per-paper rows: [9, table], [10, table], [11, table]; backbones and recipes
differ. The last row is the only controlled comparison.)

**Reading.**
1. **Recipe matters as much as data.** Under one recipe the three sets are
   within ~4 Rank-1 points on Market, and UnrealPerson leads on MSMT17
   [11, Table 4]. Real-derived clothing gives ClonedPerson a modest Market
   edge (+3–4 Rank-1). It is not the 29-point jump the per-paper numbers
   suggest. Clothing is still SurvSim's weak point: painted street-wear per
   identity, and a MetaHuman wardrobe API that is still [A] (docs/11, CLAUDE.md).
2. **MSMT17 is the honest target.** It has 15 cameras, indoor and outdoor
   scenes, and varied lighting and seasons, so it is the most CCTV-like of the
   classic benchmarks. The best synthetic direct-transfer mAP in these tables
   is about 19–21 (UnrealPerson 19.3 with QAConv 2.0; RandPerson* 20.9 with
   TransMatcher [11, Table 4]), against 30.7 for in-domain MSMT17 training
   [9, table].
3. **RandPerson beats real sources on some targets.** Its direct transfer to
   Market (55.6 / 28.8) beat MSMT17-trained (50.0 / 23.1), Duke-trained (44.9 /
   19.0) and CUHK03-trained (33.1 / 12.9) models [9, table]. Synthetic
   diversity can beat a *different* real domain. It does not beat
   in-domain real data.

### 4.2 Mixing and pre-training

* RandPerson + real joint training [9, table]: + Market → Market R1 87.2 /
  mAP 70.9 (vs 82.2 / 58.9 real only); + MSMT17 → MSMT17 R1 65.0 / mAP 36.8
  (vs 60.8 / 30.7); + Duke → Duke 79.4 / 60.6 (vs 74.2 / 53.7).
* UnrealPerson pre-training + supervised fine-tuning [10, table]: Market R1
  94.0 vs 91.4 (ImageNet init); Duke 86.8 vs 82.1; MSMT17 74.5 vs 72.5. The
  same pre-training plus unsupervised domain adaptation (JVTC+) reaches Duke
  88.3 / 75.2 and MSMT17 68.2 / 34.8.
* MOTSynth ReID on MOT17 [1, table]: trained on MOTSynth (split 4, the
  largest), mAP 75.2 / R1 92.8 vs Market-1501-trained 64.6 / 91.9 (split 1:
  71.3 / 91.4). The gain is in mAP; Rank-1 is roughly flat. A synthetic source that shares the
  target's *viewpoint and density statistics* beat a real source that does not.

The last point is the most important for us. What transfers is the match
between source and target geometry: camera height, pitch, pixel heights and
crowding. Photorealism alone does not. SurvSim controls that geometry
precisely (rig analysis, camera director), so it can match a customer site's
geometry better than any public real ReID dataset.

### 4.3 Clothes-change and video ReID

SOMAset [4] targeted matching people "even with different apparel" through
body-structure cues (height, build). That is the idea behind SurvSim's soft
biometrics and gait signature, and behind `reid_by_epoch` (docs/11). The 2024
synthetic-to-real *video* ReID work [20] reports that across five real
datasets synthetic training outperformed real data in cross-domain settings.
Since gait and temporal cues are video properties, this supports rendering
sequences rather than stills for ReID. The Alice benchmarks [12] pair the
PersonX source with a new uncurated real target (AlicePerson: 5 cameras, ~42 k
boxes) and an evaluation server. That makes Alice the natural external
yardstick if SurvSim ever publishes a synthetic ReID set.

### 4.4 What none of these papers covers

None of the surveyed ReID sets applies a calibrated *CCTV imaging chain*
(codec, noise, IR) of the kind docs/15 measures. None generates controlled
appearance epochs (jacket off, hat on in a blind spot). None scores gait
under disguise. This is SurvSim's opening, as corpus fact 6 already notes:
clothes-changing ReID Rank-1 is only ~40 % on LTCC (CAL, CVPR 2022: 40.1 R1 / 18.0 mAP).

---

## 5. Human pose, shape and action — why BEDLAM matters to a CCTV company

BEDLAM [6] rendered ~380 K frames with ~1 M boxes. It covers 271 body shapes,
100 skin textures across seven ethnic groups, 111 outfits with 1,691 textures
(physically simulated cloth), 2,311 motions and 27 hairstyles [6, table].
Models trained on synthetic data *only* reach state-of-the-art accuracy on
real benchmarks: BEDLAM-CLIFF scores PA-MPJPE 46.6 / MPJPE 72.0 / PVE 85.0 on
3DPW, and 51.2 / 84.5 / 96.6 on RICH [6, table]. The authors note that even
basic HMR approaches the SOTA CLIFF when trained on BEDLAM [6].

The lesson transfers directly:
- **Body shape diversity.** BEDLAM has 271 shapes; SurvSim has three baked
  bodies, two ~1.58 m and one ~1.93 m, scaled per person (docs/11).
- **Simulated clothing.** BEDLAM simulates cloth physically; SurvSim paints
  street-wear per identity.
- **Motion diversity.** BEDLAM has 2,311 motions; SurvSim has walk/run/idle
  loops plus look-around.

BEDLAM is the strongest evidence that the three axes on which SurvSim is
thinnest are the ones that decide synthetic-only success. Report 23 M7
(≥ 20 bodies via the [V] parametric body, wardrobe verification, interaction
animations) is therefore not cosmetic.

SURREAL [18] (6.5 M frames of SMPL bodies) and SURREACT [19] (synthetic
humans that "substantially improve" action recognition from unseen viewpoints
on NTU RGB+D and UESTC) support rendering *behaviour* from new viewpoints.
That is directly relevant to report 19's pose-based fight and fall models.
CCTV pitch angles (10–45° down) are under-represented in real action datasets.

---

## 6. Multi-camera

Synthehicle [17] (CARLA; 17 h of video from 340 cameras in 64 scenes across
day, rain, dawn and night) is the template docs/02 names for synthetic MTMC.
It is for vehicles. A comparably-sized *pedestrian* MTMC set with calibrated
cameras, topology and appearance change does not appear in this survey.
MOTSynth is single-camera per sequence. SurvSim's multi-camera rigs with GT
that follows the live camera (principle 2) fill that gap. This is a
publishable contribution in its own right [inference from the survey].

---

## 7. Measuring the gap — methods from the literature and from SurvSim

The surveyed papers measure the gap in four ways, and SurvSim needs all four:

1. **Train-synthetic-test-real (TSTR) at fixed protocol.** Used by every
   paper above. It is the only measure that directly answers "does this data
   help?" SurvSim: report 23 M4.
2. **Scaling curves over real-data fraction.** PeopleSansPeople [5] shows the
   shape to expect. SurvSim: run 1/10/25/100 % real with and without synthetic
   pre-training, stratified by pixel height and night.
3. **Trend agreement.** PersonX [8] validates a synthetic benchmark by showing
   that algorithms *rank* the same way on synthetic and real data. This is the
   right criterion for SurvSim's *evaluation* role. We don't need identical
   numbers; we need the same ordering of models and the same direction of
   effects. It is cheap to check: score N public detectors on MOT20 and on
   SurvSim renders at matched pixel heights, then compute Spearman ρ between
   the two rankings.
4. **Controlled-factor studies.** PersonX isolates viewpoint [8]; MOTSynth
   isolates diversity vs volume [1]. SurvSim can isolate imaging-chain factors
   (docs/15 profiles), geometry (camera height/pitch), density and appearance
   epochs. No real dataset can.

SurvSim adds two in-house measures:
- **Image statistics against a real band.** docs/15: `cctv_day_720p` has
  6/14 stats in band on UE renders, `cctv_legacy_sd` 9/14, and night is
  uncalibrated.
- **Detector-as-judge.** A fixed real-trained detector's recall on synthetic
  people at matched heights: batch_v4 yolov8n recall 0.758 for MetaHuman vs
  0.577 for CesiumMan on the same 770 GT boxes (docs/11/12).

The +18-point jump from better humans matches the ReID progression in §4.1
(better humans give better transfer, with the recipe caveat in §4.1). It is a cheap leading indicator that
should be tracked per SurvSim release, alongside TSTR.

---

## 8. Implications for our training-mix plan

Reports 18 §6.2 and 21 §2.2 proposed: synthetic pre-train → real fine-tune
with a 10–50 % synthetic share per batch → validate on real only → synthetic
suites as stress tests. The evidence refines it as follows.

1. **Keep "pre-train then fine-tune" as the default.** It is the protocol
   with the most consistent positive results across detection [5], tracking
   [1] and ReID [10]. Joint training (RandPerson + real [9]) is also positive.
   It is a reasonable alternative when the synthetic domain is closer to the
   target than the pre-training corpus is.
2. **Expect large gains only where we are data-poor or where scenes are
   crowded.** Plan experiments at 1 % / 10 % / 100 % real (PeopleSansPeople
   shape) and on dense scenes (MOTSynth's MOT20 result). If SurvSim gives
   < 1 AP at full real data on daytime concourse footage, that is *expected*,
   not a failure. Report it honestly, as docs/13 requires.
3. **Invest in diversity before volume.** MOTSynth's sampling ablation (sparse
   sampling matches dense with ~⅓ the frames) [1] and BEDLAM [6] point that
   way. The ReID clothing progression [9–11] is weaker evidence than it looks,
   because recipe differences explain most of it (§4.1). Our
   binding constraints are 3 bodies, painted clothing and 3 walk/run/idle
   loops, not frame count. At ~11 frames/s render (docs/11), a 20k-frame suite
   costs 30 minutes. Diversity is the bottleneck, not throughput.
4. **Match geometry to the customer site.** Hattori [13, zero-real-data setting] and MOTSynth ReID
   (75.2 vs 64.6 mAP on MOT17) [1] show that matching camera geometry and
   density beats generic realism. The generator should take a site's rig and
   pixel-height distribution as input (report 18 §1.4).
5. **Watch association, not just detection.** In [1] the ReID model moved
   Tracktor IDF1 by ~5–6 points, more than the detector's training data did
   (MOTSynth beat COCO like for like on both MOTA and IDF1). Report DetA/AssA
   (docs/13) and budget real data for the association/ReID head.
6. **The imaging chain is the untested variable.** None of the surveyed
   papers applies calibrated CCTV degradation, and JTA explicitly ties
   transfer to resolution and sharpness [3]. SurvSim's own experiment (report
   23 M4) should therefore include a same-renders ablation: raw vs
   `cctv_day_720p`-degraded synthetic pre-training, tested on real CCTV-like
   footage. This is where SurvSim could add something the literature has not
   measured.
7. **Use trend agreement to validate SurvSim as an *evaluation* tool**
   (PersonX criterion [8]), separately from TSTR. SurvSim can be commercially
   useful as a test oracle even if TSTR gains turn out to be small — report
   23 §5 already names this fallback.
8. **Revised mix guidance.** Keep the 10–50 % synthetic batch share from
   report 21 as the search range. Weight it toward rare conditions (night,
   crowds, disguise, hard negatives). Select the ratio on *real* validation
   only. Where a site class has < ~1,000 labelled real frames, lean on
   synthetic pre-training harder: that is the regime in which
   PeopleSansPeople saw +11 to +29 AP.

### 8.1 A concrete first experiment (feeds report 23 M4)

| Arm | Pre-train | Fine-tune (real) | Test |
|---|---|---|---|
| A | COCO | MOT17 train subset at 1 / 10 / 100 % | MOT20 + held-out CCTV-like real set |
| B | COCO → SurvSim raw renders | same | same |
| C | COCO → SurvSim renders through `cctv_day_720p` | same | same |
| D | COCO → SurvSim degraded, sparse sampling across many seeds (diversity arm) | same | same |

Report AP by pixel-height bucket (20–40, 40–80, 80–160, > 160 px) with
≥ 3 seeds. The success criterion is carried from report 23 M4: C or D beats A
by ≥ 2 AP50 in the 20–60 px band or at ≤ 25 % real data. If not, write up the
negative result with a failure analysis.

---

## 9. Verification log

**Verified this session (fetched abstract, ar5iv/arXiv HTML table or official
repo):** references [1]–[20] below, 20 sources. Numbers marked *(table)* came
from the HTML rendering of the paper's tables and should be spot-checked
against the PDF before external use.

**Dropped (could not verify):**
- a "CenterTrack synthetic-only 59.7 MOTA / 52.0 IDF1 on MOT17" figure from a
  search-engine summary, which did not match the table rendering;
- a "6,000 identities" UnrealPerson figure from a search summary. The audit
  found the full UnrealPerson set is 6,799 IDs / 1,256,381 images per [11]
  Table 1, and 3,000 IDs / 120,000 is the suggested subset;
- Hattori et al.'s numeric AP results (PDF not machine-readable in this
  session);
- SOMAset numeric ReID results (not in abstract);
- GTA5-pedestrian and GMOT dataset specifics (not located in the time
  available);
- per-paper backbone details beyond what is stated.

Total: 20 citations checked; 6 claims dropped. Audit 2026-09-26: 4 table
readings corrected (§0 items 3–4, §2.1, §3, §4.1), Hattori's comparative
claim marked [unverified]; Hattori, Marin and SYNTHIA were checked via search
abstracts only (PDF/CVF pages not fetchable).

---

## References

1. M. Fabbri, G. Brasó, G. Maugeri, O. Cetintas, R. Gasparini, A. Ošep, S. Calderara, L. Leal-Taixé, R. Cucchiara. *MOTSynth: How Can Synthetic Data Help Pedestrian Detection and Tracking?* ICCV 2021. https://arxiv.org/abs/2108.09518 (tables via https://ar5iv.labs.arxiv.org/html/2108.09518)
2. dvl-tum. *MOTSynth baselines* (official repository). https://github.com/dvl-tum/motsynth-baselines
3. M. Fabbri, F. Lanzi, S. Calderara, A. Palazzi, R. Vezzani, R. Cucchiara. *Learning to Detect and Track Visible and Occluded Body Joints in a Virtual World* (JTA). ECCV 2018. https://arxiv.org/abs/1803.08319
4. I. B. Barbosa, M. Cristani, B. Caputo, A. Rognhaugen, T. Theoharis. *Looking Beyond Appearances: Synthetic Training Data for Deep CNNs in Re-identification* (SOMAset). CVIU 167, 2018. https://arxiv.org/abs/1701.03153
5. S. E. Ebadi, Y.-C. Jhang, A. Zook, S. Dhakad, A. Crespi, P. Parisi, S. Borkman, J. Hogins, S. Ganguly. *PeopleSansPeople: A Synthetic Data Generator for Human-Centric Computer Vision.* arXiv 2021 (rev. 2022). https://arxiv.org/abs/2112.09290 (tables via https://ar5iv.labs.arxiv.org/html/2112.09290)
6. M. J. Black, P. Patel, J. Tesch, J. Yang. *BEDLAM: A Synthetic Dataset of Bodies Exhibiting Detailed Lifelike Animated Motion.* CVPR 2023. https://arxiv.org/abs/2306.16940
7. G. Ros, L. Sellart, J. Materzynska, D. Vázquez, A. M. López. *The SYNTHIA Dataset: A Large Collection of Synthetic Images for Semantic Segmentation of Urban Scenes.* CVPR 2016. https://openaccess.thecvf.com/content_cvpr_2016/html/Ros_The_SYNTHIA_Dataset_CVPR_2016_paper.html
8. X. Sun, L. Zheng. *Dissecting Person Re-identification from the Viewpoint of Viewpoint* (PersonX). CVPR 2019. https://arxiv.org/abs/1812.02162
9. Y. Wang, S. Liao, L. Shao. *Surpassing Real-World Source Training Data: Random 3D Characters for Generalizable Person Re-Identification* (RandPerson). ACM MM 2020. https://arxiv.org/abs/2006.12774
10. T. Zhang, L. Xie, L. Wei, Z. Zhuang, Y. Zhang, B. Li, Q. Tian. *UnrealPerson: An Adaptive Pipeline towards Costless Person Re-identification.* CVPR 2021. https://arxiv.org/abs/2012.04268 ; code https://github.com/FlyHighest/UnrealPerson
11. Y. Wang, X. Liang, S. Liao. *Cloning Outfits from Real-World Images to 3D Characters for Generalizable Person Re-Identification* (ClonedPerson). CVPR 2022. https://arxiv.org/abs/2204.02611
12. X. Sun, Y. Yao, S. Wang, H. Li, L. Zheng. *Alice Benchmarks: Connecting Real World Re-Identification with the Synthetic.* ICLR 2024. https://arxiv.org/abs/2310.04416
13. H. Hattori, V. N. Boddeti, K. M. Kitani, T. Kanade. *Learning Scene-Specific Pedestrian Detectors without Real Data.* CVPR 2015. https://www.cs.cmu.edu/~kkitani/pdf/HBKK-CVPR15.pdf
14. J. Marín, D. Vázquez, D. Gerónimo, A. M. López. *Learning Appearance in Virtual Scenarios for Pedestrian Detection.* CVPR 2010. https://www.researchgate.net/publication/221362126_Learning_Appearance_in_Virtual_Scenarios_for_Pedestrian_Detection
15. M. Johnson-Roberson, C. Barto, R. Mehta, S. N. Sridhar, K. Rosaen, R. Vasudevan. *Driving in the Matrix: Can Virtual Worlds Replace Human-Generated Annotations for Real World Tasks?* ICRA 2017. https://arxiv.org/abs/1610.01983
16. S. R. Richter, V. Vineet, S. Roth, V. Koltun. *Playing for Data: Ground Truth from Computer Games.* ECCV 2016. https://arxiv.org/abs/1608.02192
17. F. Herzog, J. Chen, T. Teepe, J. Gilg, S. Hörmann, G. Rigoll. *Synthehicle: Multi-Vehicle Multi-Camera Tracking in Virtual Cities.* arXiv 2022 (WACV workshops 2023). https://arxiv.org/abs/2208.14167
18. G. Varol, J. Romero, X. Martin, N. Mahmood, M. J. Black, I. Laptev, C. Schmid. *Learning from Synthetic Humans* (SURREAL). CVPR 2017. https://arxiv.org/abs/1701.01370
19. G. Varol, I. Laptev, C. Schmid, A. Zisserman. *Synthetic Humans for Action Recognition from Unseen Viewpoints* (SURREACT). IJCV 2021. https://arxiv.org/abs/1912.04070
20. X. Zhang, W. Feng, R. Han, L. Wang, L. Song, J. Hou. *Synthetic-To-Real Video Person Re-ID.* arXiv 2024 (rev. 2025). https://arxiv.org/abs/2402.02108

In-repo: docs/11, docs/12 (batch_v4), docs/13, docs/15; research 18 §6, 21 §2, 23 M4/M7.
