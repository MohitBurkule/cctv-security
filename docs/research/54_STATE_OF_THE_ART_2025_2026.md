# 54 — State of the art, mid-2025 → September 2026

*What changed in the last ~18 months that an interviewer at a defence / CCTV-analytics
company would expect a candidate to know, with the number and the primary source.*

> **Audited 2026-09-26** (`AUDIT_54.md`): 50 numbers re-fetched; 8 fixes applied in place
> (SAM 3 metric labels, DOA-SORT split, YOLO26-vs-11 latency wording, Latent Clarity protocol,
> Thor INT8 attribution, DUAA s.117–119, tight-GT status). Score 8.5/10 before, 9.5/10 after.

**Method and honesty rules.** Every number below was fetched on **2026-09-26** from the
primary source named beside it (arXiv abstract page, arXiv API listing, official GitHub
README/release, vendor spec page, legislation.gov.uk, EUR-Lex). Where a source did not
state a number I say so instead of filling one in. Web *search* was unavailable during
this pass (quota exhausted), so discovery was done through the arXiv API
(`export.arxiv.org/api/query`, sorted by submission date) and known project pages; this
means coverage is biased toward arXiv-visible work and **some leaderboard pages could not
be read** (motchallenge.net refused the connection twice — see §2.1). Abstract-level
numbers are the paper's own claims, not reproductions. Where this file overlaps
`FACTS_VERIFIED.md`, FACTS wins.

**Relation to existing dossiers.** 25/26/27 (detection, MOT, ReID) are anchored on
YOLOv8/YOLO11, RT-DETR, ByteTrack/BoT-SORT/OC-SORT, OSNet and CLIP-ReID; 45 covers
Grounding DINO, OWLv2, YOLO-World, InternVL2/Holmes-VAU and Qwen3-VL. This file only
adds what is *newer* than those anchors, and says whether SurvSim's own baselines
(`32_EXPERIMENTS_LOG.md`: YOLOv8n detection, ImageNet-OSNet ReID, HOTA 0.545→0.434, 0.443 at TrackEval parity)
should be re-run against it.

Tag legend used in the "re-baseline?" lines: **Yes** = the current SurvSim number is
now stale as a reference point; **Optional** = worth one run for the interview story;
**No** = interesting but does not change a SurvSim conclusion.

---

## 1. Detection

### 1.1 Ultralytics YOLO26 (January 2026)

Source: <https://docs.ultralytics.com/models/yolo26/> and release v8.4.0
<https://github.com/ultralytics/ultralytics/releases/tag/v8.4.0> (fetched 2026-09-26).
The docs page gives the release as January 2026. (The fetch of the GitHub release page
returned a date string of "January 14, 2025"; the year is inconsistent with the docs and
with YOLO11 being Sept 2024, so treat the day as unconfirmed and the month as Jan 2026.)

| Model | COCO mAP50-95 | CPU ONNX ms | T4 TensorRT ms | Params M |
|---|---|---|---|---|
| YOLO26n | 40.9 | 38.9 | 1.7 | 2.4 |
| YOLO26s | 48.6 | 87.2 | 2.5 | 9.5 |
| YOLO26m | 53.1 | 220.0 | 4.7 | 20.4 |
| YOLO26l | 55.0 | 286.2 | 6.2 | 24.8 |
| YOLO26x | 57.5 | 525.8 | 11.8 | 55.7 |

What changed architecturally: native end-to-end **NMS-free** inference (one-to-one head,
with a one-to-many head retained for training/compat), **DFL removed** from the head
(simpler export), **MuSGD** optimiser (SGD + Muon), "ProgLoss" and "STAL" aimed at small
objects. The release headline is "43% faster CPU inference".

Compared with **YOLO11** (released 10 Sep 2024, <https://docs.ultralytics.com/models/yolo11/>):
n 39.5 / 56.1 ms CPU / 1.5 ms T4; s 47.0; m 51.5; l 53.4; x 54.7 / 11.3 ms T4. So size for
size YOLO26 gains **+1.4 (n) to +2.8 (x) mAP** at the same or slightly higher T4 latency
(s/m/l equal; n +0.2 ms, x +0.5 ms), and the nano CPU latency falls
56.1 → 38.9 ms (−31 %, not the headline 43 %, which is measured on a different basis).
Note the T4 number for YOLO26n is *slower* (1.7 vs 1.5 ms) — the win is on CPU.

*Why it matters:* NMS-free means crowd scenes no longer have a hand-tuned IoU threshold
suppressing a real second person — the exact failure mode that dense surveillance
crowds (MOT20-like) expose. It also removes the NMS step from edge latency budgets.
*Re-baseline?* **Yes.** SurvSim's detection experiments use YOLOv8n; the "zero-shot COCO
detector on our renders" number should be re-quoted against YOLO26n/s, especially the
small-person recall experiment (STAL targets exactly that).

### 1.2 The DETR family: RT-DETRv3, D-FINE, DEIM, DEIMv2

* **RT-DETRv3** — arXiv 2409.08475 (v1 13 Sep 2024, v3 19 Dec 2024,
  <https://arxiv.org/abs/2409.08475>): R18 48.1 AP (+1.6 over RT-DETR-R18), R101 54.6 AP.
  Gains are training-only (dense positive supervision via a CNN auxiliary branch), zero
  inference cost. Slightly older than the window, but it is the "v3" people cite.
* **D-FINE** — arXiv 2410.13842 (<https://arxiv.org/abs/2410.13842>; repo
  <https://github.com/Peterande/D-FINE>): L 54.0 AP @ 124 FPS T4, X 55.8 AP @ 78 FPS; with
  Objects365 pre-training 57.1 (L) / 59.3 (X) per the abstract; N 42.8 AP @ 472 FPS per
  the README. Box regression becomes iterative distribution refinement (FDR) plus
  self-distillation (GO-LSD). The README explicitly advertises robustness to
  "backlighting, motion blur, and dense crowds" — a CCTV claim worth testing, not trusting.
* **DEIM** — CVPR 2025 (<https://github.com/ShihuaHuang95/DEIM>): a matching/training
  recipe on top of D-FINE. DEIM-D-FINE N 43.0 / S 49.0 / M 52.7 / L 54.7 / X 56.5 AP at
  2.12 / 3.49 / 5.62 / 8.07 / 12.89 ms; Objects365-pretrained 59.5 AP.
* **DEIMv2** — arXiv 2509.20787, Sep 2025 (<https://github.com/Intellindust-AI-Lab/DEIMv2>):
  DINOv3 features in a real-time detector, eight sizes. Atto 23.8 AP / 0.5 M params;
  Pico 38.5 / 1.5 M; N 43.0 / 3.6 M; **S 50.9 AP / 9.7 M / 5.78 ms** (first sub-10 M model
  over 50 AP); L 56.0; **X 57.8 AP / 50.3 M / 13.75 ms**. Licence: custom "DEIMv2
  License" with commercial-enquiry wording — check before any product use.

*Why it matters:* the real-time frontier is now **DETR-style, NMS-free, foundation-feature
backbones**; YOLO26x (57.5) and DEIMv2-X (57.8) are within noise at comparable latency.
For a defence customer the deciding factors are licence (Ultralytics AGPL-3.0 vs Apache
D-FINE vs custom DEIMv2) and INT8/edge export behaviour, not 0.3 AP.
*Re-baseline?* **Optional.** Run D-FINE-S (Apache-2.0) next to YOLO26s on the synthetic
batch to show the result is not architecture-specific.

### 1.3 Open-vocabulary detection

* **YOLOE** — ICCV 2025, arXiv 2503.07465 (<https://arxiv.org/abs/2503.07465>): text,
  visual-exemplar and prompt-free modes in one real-time model; YOLOE-v8-S is **+3.5 AP
  over YOLO-Worldv2-S on LVIS** with 3× lower training cost and 1.4× faster inference.
* **DINO-X** — arXiv 2411.14347: 56.0 AP COCO zero-shot, 59.8 AP LVIS-minival, 52.4 AP
  LVIS-val (abstract, via arXiv API listing). API-only model; not self-hostable.
* Reference point: **YOLO-World** 35.4 AP LVIS zero-shot at 52 FPS (arXiv 2401.17270).
* 2026 open papers cluster far lower on LVIS zero-shot: VL-DINO 36.3–38.1 AP
  (2606.11546), FlowOVD 31.5 AP LVIS / 49.5 AP COCO (2606.00782), ExpAlign 36.2 AP_r
  on LVIS-minival (2601.22666) — all from abstracts in the arXiv API listing.

*Why it matters:* "find the person with the red backpack" is now a real-time query, not a
VLM call. But **the gap between the closed API (DINO-X ~59.8) and open real-time
(~35–38) on LVIS is still ~20 AP** — the honest interview answer.
*Re-baseline?* **Optional.** SurvSim ground truth carries attributes (outfit epochs), so an
attribute-query recall test on YOLOE is cheap and would be a novel number.

### 1.4 SAM 3 (Segment Anything with Concepts)

arXiv 2511.16719, submitted **20 Nov 2025**, revised 28 Mar 2026
(<https://arxiv.org/abs/2511.16719>; repo <https://github.com/facebookresearch/sam3>).
(The repo's news line dated 27 Mar 2026 is the **SAM 3.1** "Object Multiplex" update, not
the original release; the arXiv date is authoritative.)
Promptable **concept** segmentation: a noun phrase or image exemplar returns *all*
instances, with a detector and a memory-based video tracker sharing one backbone and a
"presence head" separating recognition from localisation. README numbers (re-read from the raw
README table 2026-09-26): SA-Co/Gold **54.1 cgF1 instance seg / 55.7 cgF1 box** (human
72.8 / 74.0); LVIS instance seg 37.2 cgF1 / **48.5 AP**; LVIS box 53.6 AP (DINO-X 52.4);
**COCO box 56.4 AP** (55.7 AP_o); SA-V test 30.3 cgF1 (human 53.1); the abstract claims it "doubles the accuracy of existing systems"
on image and video PCS. SA-Co has 270 K unique concepts from a 4 M-concept data engine.

*Why it matters:* SAM 2 was "click to track one object"; SAM 3 is "track every *person
carrying a bag*" — detection, segmentation and tracking in one open-vocabulary model. It
is also the obvious **auto-labeller** for real CCTV, which is the competitor to
SurvSim's "free perfect labels" pitch.
*Re-baseline?* **Yes, as a label-quality check.** SurvSim's tight-GT work (mask-derived
boxes, committed `0213002`/`68ee6d1`: median IoU vs YOLOv8n 0.781→0.884 smoke, 0.712→0.911
street; but synthetic-only transfer to MOT20 did *not* improve, 0.290 loose vs 0.266 tight,
because MOT20's own boxes are amodal) should be compared against SAM 3 masks on the same
renders: if SAM 3 matches our GT masks at ≥0.9 IoU on clean frames, then SurvSim's value
is the *rare-event and identity* GT, not the masks — say that in interview.

---

## 2. Multi-object tracking

### 2.1 Leaderboards — what could and could not be read

`motchallenge.net/results/MOT20/` refused the connection twice on 2026-09-26, so **no
MOT20 leaderboard top-entry is quoted here**; use the figures already in 26 and
FACTS_VERIFIED, and say in interview that you check the live board rather than quote it.
DanceTrack/SportsMOT figures below are paper-reported (arXiv abstracts), which is how
most people actually learn the numbers.

### 2.2 Query / transformer trackers and ID-prediction

* **MOTIP** — CVPR 2025 (<https://github.com/MCG-NJU/MOTIP>): tracking as **in-context ID
  prediction** — past trajectories with ID tokens are the context, the decoder emits an
  ID label per detection. New, simpler codebase April 2025. (The README page we fetched
  did not print the HOTA table; not quoted.)
* **Motion-Aware Transformer (MAT)** — arXiv 2509.21715 (26 Sep 2025, rev. 8 Mar 2026):
  MOTR-style; **DanceTrack 71.3 HOTA** (with extra data), **SportsMOT 72.2**, BDD100k 41.6 mHOTA.
* **SelfMOTR** — arXiv 2511.20279 (25 Nov 2025): DanceTrack 69.2 HOTA, BFT 71.1.

### 2.3 Tracking-by-detection is not dead

* **MeMoSORT** — arXiv 2508.09796 (Aug 2025): DanceTrack 67.9, SportsMOT 82.1 HOTA.
* **Occlusion-Aware SORT** — 2603.06034 (Mar 2026): DanceTrack 63.1 HOTA / 64.2 IDF1.
* **DOA-SORT** — 2609.22706 (19 Sep 2026): DanceTrack **validation** 66.34 HOTA (63.00 for
  its OA-SORT baseline) — a val-split number, not comparable with the test-set figures here.
* **StableTrack** — 2511.20418 (Nov 2025): +11.6 % on MOT17-val at **1 Hz detections**
  while holding standard-rate performance. Directly relevant: many CCTV deployments run
  the detector at 1–5 fps to save edge compute.

### 2.4 SAM-based trackers

* **SAM2MOT** — arXiv 2504.04519 (6 Apr 2025, v5 18 Nov 2025): "tracking by
  segmentation" — detector seeds, SAM 2 propagates masks; **+2.1 HOTA, +4.5 IDF1 on
  DanceTrack** over prior methods, **zero-shot** (no fine-tuning on tracking labels).
* **Selective Mask Propagation** — 2606.13033 (Jun 2026): SportsMOT 87.2 HOTA (abstract).
  If that holds it is well above the MAT/MeMoSORT figures — treat as a claim to check.
* SAM 3 (§1.4) folds this whole pattern into a single model.

*Why it matters (all of §2):* On DanceTrack (uniform appearance, erratic motion) the
best query trackers sit around **69–71 HOTA** and good SORT variants at **63–68** —
the gap is ~4 HOTA, not a paradigm gap. The low-frame-rate and zero-shot SAM directions
are the ones that map onto real CCTV constraints.
*Re-baseline?* **Yes.** SurvSim's HOTA 0.545→0.434 (0.443 at TrackEval parity) result (tracker degrading under our
harder conditions) is currently against a SORT-family tracker. Re-running one zero-shot
SAM2MOT-style tracker and StableTrack at 1 Hz on the same sequences would show whether the
drop is tracker-specific — a stronger claim either way.

---

## 3. Re-identification

### 3.1 Clothes-changing ReID (LTCC / PRCC), 2025–26

From the arXiv API listing sorted by date (abstract-level claims; most abstracts give
*deltas*, not absolute numbers):

| arXiv | Date | Method | Claimed gain |
|---|---|---|---|
| 2503.22912 | Mar 2025 | DIFFER (semantic-cue disentangling) | LTCC +3.6, PRCC +3.4 top-1 |
| 2505.12580 | May 2025 | RLQ coarse-attribute distillation | PRCC +5.3–6 top-1 |
| 2507.07230 | Jul 2025 | Colors See, Colors Ignore | LTCC +2.9, PRCC +5.0 top-1 |
| 2507.11119 | Jul 2025 | Try Harder (hard-sample generation) | "SOTA", no number in abstract |
| 2601.19133 | Jan 2026 | QA-ReID | "SOTA", no number in abstract |
| 2606.11661 | Jun 2026 | Instance-adaptive low-rank orthogonal subspaces | PRCC +5.9 top-1 |

The most recent absolute figure visible in an abstract is still **MIPL (2411.00330):
LTCC 74.8 % rank-1** (protocol unstated; CC LTCC is CAL 40.1, ≈ general-setting CAL 74.2 — not a clothes-change score; 70 §). The honest summary: the field is gaining 3–6 rank-1 points per
paper on PRCC, and **generative augmentation (diffusion try-on, DLCR 2411.07205: PRCC
+11.3 top-1)** is the biggest single lever.

### 3.2 CLIP-ReID successors

The arXiv search for CLIP-based ReID on Market/MSMT17 in 2025–26 surfaced ALADIN
(2603.21482, Mar 2026, attribute-language distillation) with no absolute numbers in the
abstract. I could not verify a single new "CLIP-ReID successor" with a headline number in
this pass — say so rather than invent one; 27's CLIP-ReID figures remain the anchor.

*Why it matters:* Clothing change is the defining failure of real-world multi-camera
re-association (a suspect removes a jacket). SurvSim's appearance epochs produce exactly
this with *known* identity — no public CC-ReID dataset has disguise events at scale.
*Re-baseline?* **Yes.** The current SurvSim ReID baseline is ImageNet OSNet (cross-time
rank-1 0.512). That is not a ReID model; the next number should be a CC-ReID-trained model
evaluated on SurvSim's outfit-change split, and the diffusion try-on result argues for
using SurvSim's wardrobe epochs *as* the augmentation.

---

## 4. Video anomaly detection and VLMs

### 4.1 Latest UCF-Crime / XD-Violence figures (2026)

| arXiv | Date | Method | UCF-Crime AUC | XD-Violence |
|---|---|---|---|---|
| 2603.19780 | Mar 2026 | Decoupled Sensitivity-Consistency (weakly sup.) | 89.37 | 87.18 AP |
| 2605.02912 | Apr 2026 | Reasoning-guided grounding (MLLM) | 94 ROC-AUC, 84 F1 | — |
| 2607.03558 | Jul 2026 | Latent Clarity (anticipation) | 89.94 *chunk-level* AUROC | 81.62 AUROC |
| 2609.06360 | Sep 2026 | **NOVA**, training-free zero-shot | **89.86** | 95.07 AUC / 84.82 AP |

Context from FACTS_VERIFIED: UR-DMU 86.97, Holmes-VAU 88.96, ASK-HINT 89.83 (training-free,
Qwen2.5-VL-7B). So **training-free VLM pipelines now match weakly-supervised ones at
~89.9 UCF-Crime AUC**; the 94 claim uses a different protocol and should not be compared
directly, and Latent Clarity's 89.94 is a chunk-level anticipation AUROC, not frame AUC.

Two 2026 papers every candidate should know because they attack the metric itself:
**"Frame-Level Evaluation in WSVAD Mostly Measures Video-Level Ranking"** (2608.21854,
Aug 2026) and **"Rethinking Open-World VAD: Diagnosing Definition Blindness"**
(2607.20780). Both make SurvSim's principle 4 (report alarms per camera-hour, not
frame AUC) look prescient.

*Why it matters:* frame-AUC on UCF-Crime is saturating near 90 and is now openly
criticised; the differentiator is operational false-alarm rate on hard negatives.
*Re-baseline?* **No for AUC; Yes for the argument.** Cite 2608.21854 next to SurvSim's
i-LIDS-style evaluator.

### 4.2 Long-context video-LLMs and on-device VLMs

* **Qwen3-VL** — tech report arXiv 2511.21631 (26–27 Nov 2025): dense 2B/4B/8B/32B and
  MoE 30B-A3B / 235B-A22B; **native 256 K-token interleaved context**; text timestamp
  alignment for video. (FACTS already records the 2 fps × 640-token protocol.)
* **SmolVLM** — arXiv 2504.05299 (7 Apr 2025): 256 M–2.2 B params; the 256 M model runs in
  **< 1 GB GPU memory** and is claimed to beat Idefics-80B; video capable.

*Why it matters:* a 2B–4B VLM now fits an 8 GB GPU or a Jetson for **alarm verification
and captioning**, and a 256 K window is ~200 s of 2 fps video — enough for one loiter
event, not for a shift. The pattern is detector/tracker for recall, VLM for explaining
and suppressing alarms.
*Re-baseline?* **Optional.** A Qwen3-VL-2B/4B "verify this alarm" pass on SurvSim's
`loiter` vs `commute_wait` pairs is the most on-message experiment available.

---

## 5. Event cameras and SNNs

From the arXiv API (Gen1 automotive benchmark; numbers as stated in abstracts):

* **Sequence-SOD** (2607.26703, Jul 2026) — spiking detector, **Gen1 26.88 mAP**.
* **SSLA** low-latency linear attention (2603.06228, Mar 2026) — **Gen1 0.375 mAP**.
* **SpikingMOT** (2607.19875, Jul 2026) — spike-driven *tracker*: SportsMOT 74.9, DanceTrack
  56.5 HOTA — i.e. an SNN tracker ~15 HOTA behind ANN trackers on DanceTrack.
* Reference SNN: SFOD (2403.15192) Gen1 32.1 % mAP.
* Representation-level temporal aggregation (2605.08825, May 2026): +0.8 Gen1,
  +0.5 1Mpx, **+3.0 eTraM** (eTraM is the static traffic-monitoring event dataset — the
  nearest thing to a fixed CCTV event camera).
* **DVS-PedX** (2509.04117, Sep 2025): event-based pedestrian dataset, synthetic (CARLA) +
  real (JAAD), explicitly reports a sim-to-real gap.

*Why it matters:* SNN detectors are still **~5–11 mAP behind** ANN event detectors on
Gen1 (26.9–32.1 vs ~37.5 — the ANN reference is not sourced in this file; check before quoting), so the neuromorphic pitch remains power and latency, not
accuracy. See 36 for the physics.
*Re-baseline?* **No.** SurvSim has no event-sensor model beyond what 36 describes; note
DVS-PedX as the synthetic-event precedent if asked.

---

## 6. Synthetic data and generative augmentation

The arXiv query for 2025–26 synthetic pedestrian / Unreal-Engine person datasets returned
**little new** — a meaningful finding: no large new synthetic *surveillance* person
dataset appeared in the window that I could verify. What did appear:

* **Generative editing for domain shift** — 2609.02299 (2 Sep 2026): GenAI image editing
  raises detection mAP by **+20.1 (foliage occlusion)** and **+14.4 (netting camouflage)**
  — a defence-relevant concealment result.
* **Diffusion try-on for CC-ReID** — 2512.07126 (Dec 2025): LTCC +2.5, PRCC +1.1 rank-1;
  earlier DLCR (2411.07205) PRCC +11.3.
* **AI City Challenge, 10th edition** (2608.17044, Aug 2026): 325 teams in 2026 vs 245 in
  2025, 26 countries — the main venue where synthetic multi-camera people data is used.
* Older anchor: diffusion refinement of simulated pedestrians gave +27.3 % AP over
  simulated-only (2305.09401) — see 24/30.

*Why it matters:* the 2025–26 trend is **diffusion as a post-process on simulator or real
data**, not new game-engine datasets. That is the direct competitor to MetaHuman-grade
rendering — and a complement: render for geometry and identity truth, diffuse for texture.
*Re-baseline?* **Optional.** A "SurvSim + diffusion realism pass" arm in the sim2real
experiment is the obvious next H-number.

---

## 7. Edge hardware

| Device | Date | Headline | Power | Price | Source |
|---|---|---|---|---|---|
| **Jetson AGX Thor** (dev kit / T5000) | GA 25 Aug 2025 | 2,070 FP4 TFLOPS (sparse per product page; newsroom says only "FP4"); 2,560-core Blackwell GPU; 14-core Neoverse-V3AE; **128 GB LPDDR5X, 273 GB/s** | 40–130 W | dev kit **from $3,499**; modules via distributors | <https://nvidianews.nvidia.com/news/nvidia-blackwell-powered-jetson-thor-now-available-accelerating-the-age-of-general-robotics>, <https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-thor/> |
| **Jetson Orin Nano Super** | 17 Dec 2024 | 40 → **67 sparse TOPS** via MAXN (`nvpmodel -m 2`), software only | (MAXN mode) | dev kit **$249** (was $499) | <https://developer.nvidia.com/blog/nvidia-jetson-orin-nano-developer-kit-gets-a-super-boost/> |
| **Hailo-10H** | GA 22 Jul 2025; Raspberry Pi AI HAT+ 2 on 15 Jan 2026 | 40 TOPS INT4 / 20 TOPS INT8, LPDDR4/4X interface for LLM/VLM | 2.5 W typical | not listed | <https://hailo.ai/products/ai-accelerators/hailo-10h-ai-accelerator/>, <https://hailo.ai/company-overview/newsroom/news/> |

Super mode also reaches Orin NX modules via JetPack 6.1.1 (same NVIDIA blog). NVIDIA
quotes Thor as 7.5× compute and 3.5× efficiency vs AGX Orin. Hailo gave no token rate on
the pages fetched — do not quote one.

*Why it matters:* Thor's 128 GB means a 30B-class VLM plus a detector on one fanless-ish
box at the camera cluster; Hailo-10H brings a small VLM to a 2.5 W camera-side part. 38
already records (from Ultralytics' Jetson guide, not our hardware) that INT8 is *slower*
than FP16 on Thor for YOLO26n — the
FP4/FP8 Blackwell path is for transformers, not tiny CNNs.
*Re-baseline?* **No** (no hardware here), but the edge table in 38 should cite the Thor
price and the Hailo GA date.

---

## 8. Regulation

### 8.1 UK — Data (Use and Access) Act 2025

legislation.gov.uk <https://www.legislation.gov.uk/ukpga/2025/18/contents>; Royal Assent
19 June 2025 per FACTS_VERIFIED (the contents page did not print the date).
CCTV-relevant provisions:

* **s.80 — automated decision-making** (new UK GDPR Arts 22A–22D;
  <https://www.legislation.gov.uk/ukpga/2025/18/section/80/enacted>). Solely-automated
  *significant* decisions are now permitted generally, **but not on special-category data**
  (which includes biometric data used to identify) unless explicit consent, or contract /
  legal requirement with conditions. Mandatory safeguards: tell the subject, let them make
  representations, obtain **human review**, and contest. "Meaningful human involvement"
  is defined; the Secretary of State may regulate further.
* **Sched. 4 — recognised legitimate interests** (a list of purposes, including crime
  prevention and security, that no longer need a balancing test).
* **s.76 / s.78 — subject access**: time limits and searches limited to what is
  "reasonable and proportionate" — relevant to CCTV SARs.
* **s.103 — complaints** must go to the controller first.
* **ss.117–119 + Sched. 14** — ICO abolished (s.118) and replaced by a corporate
  **Information Commission** (s.117), functions transferred (s.119).
* **ss.126–128** — biometric-data retention for recordable offences (police).

FACTS records that DUAA did **not** abolish the Surveillance Camera Code or Commissioner.

*Why it matters:* an automated "deny entry / flag to police" from face or gait matching
is a significant decision on special-category data — still effectively requires a human
in the loop. That is a product-design constraint: every alarm needs an operator review
path, which SurvSim's alarm-card evaluation (51) already assumes.

### 8.2 EU — AI Act Digital Omnibus, Regulation (EU) 2026/1744

Proposed 19 Nov 2025 (<https://digital-strategy.ec.europa.eu/en/library/digital-omnibus-ai-regulation-proposal>);
adopted 8 Jul 2026, OJ 24 Jul 2026, in force **27 Jul 2026**
(<https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng>). Key changes:

* **Annex III high-risk** (incl. biometrics) application moved from 2 Aug 2026 to
  **2 Dec 2027**; **Annex I** product-embedded high-risk to **2 Aug 2028**.
* Art 50 generative-marking gets a 4-month transition for systems on the market pre-2 Aug 2026.
* **Art 4a**: providers *and deployers* may process special-category data for **bias
  detection and correction** under strict safeguards, now extended beyond high-risk systems.
* Art 4 AI literacy softened to "take measures to support".
* Art 5 prohibitions (real-time remote biometric ID in public for law enforcement, etc.)
  unchanged — applied since 2 Feb 2025.

*Why it matters:* a UK vendor selling person-analytics into the EU has 16 more months
before Annex III conformity bites; Art 4a legitimises demographic bias testing — which is
precisely what a synthetic population with controlled skin tone/body shape enables
without processing real people's special-category data.

---

## 9. Re-baseline summary

| Area | SurvSim number today | Re-run against | Priority |
|---|---|---|---|
| Detection | YOLOv8n zero-shot / fine-tune | YOLO26n/s; D-FINE-S | High |
| Masks / tight GT | mask-derived box IoU 0.781→0.884 (smoke), 0.712→0.911 (street); transfer n.s. | SAM 3 on same renders; amodal-box variant for MOT20 | High |
| Tracking | HOTA 0.443 (TrackEval parity; 0.545→0.434 pre-parity; SORT-family) | SAM2MOT-style zero-shot; StableTrack @1 Hz | High |
| ReID | ImageNet OSNet rank-1 0.512 | a CC-ReID-trained model on outfit split | High |
| Anomaly | alarms/cam-h evaluator | Qwen3-VL-2B/4B alarm verification | Medium |
| Open-vocab | none | YOLOE attribute queries | Medium |
| Sim2real | H-series | + diffusion realism arm | Medium |

---

## 10. Interview Q&As — "have you seen X?"

**Q1. Have you seen YOLO26? What actually changed?**
Yes — January 2026. NMS-free one-to-one head, DFL removed, MuSGD. COCO 40.9 (n) to 57.5 (x)
mAP; versus YOLO11 that is +1.4 to +2.8 AP, and nano CPU ONNX 56.1 → 38.9 ms. On T4 the
nano is actually 0.2 ms slower, so the gain is CPU/edge. For crowds, dropping NMS matters
more than the AP: no IoU threshold eating the second person in an overlap.

**Q2. Would you pick YOLO26 or a DETR like D-FINE / DEIMv2 for a product?**
Accuracy is a wash at the top (57.5 vs 57.8 AP). I'd decide on licence — AGPL-3.0 for
Ultralytics, Apache-2.0 for D-FINE, a custom licence for DEIMv2 — then on INT8 behaviour on
the target Jetson, which I'd measure, because Ultralytics' own Jetson benchmark (in 38)
shows YOLO26n INT8 *slower* than FP16 on Thor (1.52 vs 1.39 ms). We have no Thor; that is
their number, not ours.

**Q3. Have you seen SAM 3? Does it make your simulator pointless?**
Nov 2025; concept prompts, detect-segment-track in one model, 56.4 AP COCO box (48.5 AP LVIS masks), ~2× prior
PCS accuracy. It makes *mask labels* cheap on real footage. It does not give identity
across cameras through an outfit change, the true intent behind a loiter, or 500 staged
tamper events — that is where simulation keeps its value. I'd use SAM 3 to audit our
own mask GT.

**Q4. What's state of the art on DanceTrack, and is tracking-by-detection dead?**
Query trackers report ~69–71 HOTA (MAT 71.3, SelfMOTR 69.2); good SORT variants 63–68
(MeMoSORT 67.9). About 4 HOTA — not dead. The more deployment-relevant work is
StableTrack at 1 Hz detections and zero-shot SAM2MOT.

**Q5. Have you followed clothes-changing ReID?**
Yes — steady 3–6 rank-1 points per paper on PRCC in 2025–26 (DIFFER, Colors See Colors
Ignore, the June 2026 subspace method +5.9); generative augmentation (DLCR +11.3 PRCC) is
the largest lever. The most recent absolute LTCC figure I can source is 74.8 % rank-1 (protocol unstated — not a clothes-change score, see 70; CC LTCC is CAL 40.1). Our
outfit-epoch data is a controlled CC-ReID test set with ground-truth identity.

**Q6. Where are UCF-Crime numbers now, and do you trust them?**
~89.4–89.9 AUC for both weakly-supervised and training-free VLM pipelines (NOVA 89.86,
Sep 2026). I don't trust frame AUC for procurement — a 2026 paper shows it mostly measures
video-level ranking. I report false alarms per camera-hour against an operator budget.

**Q7. What changed in edge hardware?**
Jetson AGX Thor (Aug 2025, $3,499 dev kit, 2,070 FP4 TFLOPS, 128 GB, 40–130 W) lets a
30B-class VLM run at the edge; Orin Nano Super went to 67 TOPS for $249 by a software
mode; Hailo-10H (GA Jul 2025) does 40 INT4 TOPS at 2.5 W and is now on a Raspberry Pi HAT.

**Q8. What does the Data (Use and Access) Act change for CCTV analytics, and what about the EU?**
UK: s.80 relaxes solely-automated decisions *except* on special-category data such as
biometric identification, and mandates human review and contest routes — so a face/gait
match that triggers action still needs a human. SARs are limited to reasonable and
proportionate searches, and the ICO becomes the Information Commission. EU: the Omnibus
(Reg 2026/1744, in force 27 Jul 2026) moves Annex III high-risk to 2 Dec 2027 and widens
Art 4a so bias testing on special-category data is allowed — synthetic populations are a
cleaner way to do that testing.

---

## Sources (all fetched 2026-09-26)

Ultralytics YOLO26 docs · YOLO11 docs · ultralytics release v8.4.0 · arXiv 2409.08475
(RT-DETRv3) · arXiv 2410.13842 + github.com/Peterande/D-FINE · github.com/ShihuaHuang95/DEIM ·
github.com/Intellindust-AI-Lab/DEIMv2 (arXiv 2509.20787) · arXiv 2503.07465 (YOLOE) ·
arXiv 2511.16719 + github.com/facebookresearch/sam3 · github.com/MCG-NJU/MOTIP ·
arXiv 2509.21715, 2504.04519 · arXiv API listings (DanceTrack/HOTA; clothes-changing LTCC;
UCF-Crime/XD-Violence; open-vocabulary LVIS; event Gen1; synthetic pedestrian; diffusion
augmentation) · arXiv 2511.21631 (Qwen3-VL) · arXiv 2504.05299 (SmolVLM) · NVIDIA Jetson
Thor page and newsroom (25 Aug 2025) · NVIDIA Orin Nano Super blog (17 Dec 2024) · Hailo-10H
product page and newsroom · legislation.gov.uk ukpga/2025/18 contents and s.80 · EUR-Lex
Reg 2026/1744 · EC Digital Omnibus proposal page. Not reachable: motchallenge.net MOT20 results.
