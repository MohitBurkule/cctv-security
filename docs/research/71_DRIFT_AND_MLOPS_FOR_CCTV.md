# 71 · Drift monitoring and MLOps for deployed CCTV analytics

*2026-09-27. Why a new file: docs/research/53 (data engineering) has no
monitoring section, and adding one would push it further past its scope. This
file covers how deployed video analytics notice that they have stopped working,
and it records our first measurement of that (H34, docs/research/32).
Tags: **[V]** measured here, **[A]** published or vendor-documented but not
tested by us, **[X]** tried and broken.*

## 1. The problem is per camera, not per model

A CCTV estate is thousands of fixed sensors, and each one has its own viewpoint,
lighting cycle, codec settings and failure modes. A model can be fine on 399
cameras and useless on the 400th, because that camera's lens is dirty, its IR
cut filter is stuck, or someone reduced its bitrate. A global accuracy dashboard
averages that camera away. So the unit of monitoring is the **camera**, the
reference is **that camera's own commissioning window**, and the alert goes to
someone who can fix that camera.

There are two kinds of shift, and they need different responses:

| Shift | Example | Response |
|---|---|---|
| Imaging-chain (covariate) | dusk, defocus, bitrate cut, dirt, tamper, IR switch | camera-health ticket, flag the camera as degraded, possibly re-tune θ for it |
| Content / prior | new footfall pattern, new uniforms, seasonal clothing, events | re-baseline counts, review alarm rules, collect data for retraining |

Rabanser, Günnemann and Lipton (2019) found that for detecting dataset shift, a
two-sample test on a *low-dimensional representation* (the classifier's own
softmax, "BBSD", or a reduced embedding) with a Bonferroni-corrected univariate
KS test is a strong, cheap baseline. It works about as well as multivariate MMD
at far lower cost, and detection gets reliable only with hundreds of samples
[A; checked 2026-09-27 in the arXiv 1810.11953 PDF: "BBSDs was the best-performing
DR method", with KS + Bonferroni as the univariate test]. That last point decides how small a monitoring window can be (§4).

## 2. What deployed systems actually monitor

### 2.1 Camera health and tamper: the drift monitor that already ships

The oldest drift detector in CCTV is tamper detection, although nobody calls it
that. Ribnick et al. (2006, AVSS) and Saglam & Temizel (2009, AVSS) compare
short-term and long-term background statistics (histogram, edge energy, a
background-model match) to detect occlusion, defocus and redirection [A].
Commercial cameras ship this as firmware. ONVIF's analytics event topics include
`ImageTooDark`, `ImageTooBright`, `ImageTooBlurry` and `GlobalSceneChange`
video-source events [A; topic names checked 2026-09-27 in
onvif.org/specs/srv/analytics/ONVIF-Analytics-Service-Spec.pdf]. Axis, Bosch, Hanwha and others expose tamper, defocus and
"too dark / too bright / too noisy" alarms [A — vendor documentation; the
thresholds are proprietary]. These are label-free, per-camera, reference-window
monitors on image statistics. That is exactly the design H34 tests, and it is
why the right first reply to "how do you detect drift" in this domain is "the
camera-health channel already does half of it".

### 2.2 Output monitors on the model

Output monitors need no ground truth [A]:

* **Detection rate by hour of day and day of week**, per camera, against a
  commissioning baseline. A camera whose person count halves at 16:00 in
  November has gone dark, not quiet.
* **Confidence histogram** of accepted detections. Its PSI or KS against the
  reference is the BBSD idea from §1 applied to a detector. This is what 66's
  original H34 proposed.
* **Track statistics**: length, fragmentation (ID switches per track), and the
  fraction of one-frame tracks. Blur and codec damage show up as fragmentation
  before they show up as missing people.
* **Model assertions** (Kang et al. 2020, MLSys): a box that flickers on/off
  across consecutive frames, or objects that appear and vanish in one frame, are
  cheap consistency checks that also pick the frames worth labelling [A].
* **Alarm rate against the operator budget** (docs/research/49, 58). This is the
  monitor the customer actually feels. It is the first thing to watch and the
  last thing to trust on its own, because a blind camera raises no alarms.

### 2.3 Input monitors

Per-frame image statistics (our 13 in `survsim/realism/stats.py`: noise,
sharpness/MTF, exposure, contrast, colour cast, blockiness), or embeddings from
the detector backbone. TFX Data Validation (Breck et al. 2019, SysML) is the
industrial template: a schema plus reference distribution per feature, and
drift checks as L∞ distance or Jensen-Shannon against the previous span [A].
Alibi-detect (Van Looveren et al., Seldon) and Evidently package KS, MMD, PSI
and classifier-based detectors [A]. Evidently's defaults switch between tests
and distances depending on sample size: KS for ≤ 1,000 numerical objects and
Wasserstein distance above that [A; checked 2026-09-27 at
docs.evidentlyai.com/metrics/customize_data_drift]. That matters more than it
looks (§4).

### 2.4 Labels you get anyway

* **Operator dispositions.** Every dismissed alarm is a free false-positive
  label, and every incident found by other means is a missed-detection label.
  These labels are biased, because only alarmed events get reviewed, but they
  are the only field labels at estate scale.
* **Annotated spot checks**: a small stratified sample per camera per month
  (for example, 50 frames across day/night) labelled by an annotator and scored
  for recall at the operating threshold. This is the only monitor that measures
  recall directly. Budget it like any other labelling line (53 §5.2).
* **Shadow models**: a candidate model runs on live video without raising
  alarms, and its disagreement rate with production is logged per camera
  (Sato, Wider & Windheuser 2019, "Continuous Delivery for Machine Learning")
  [A]. High disagreement on one camera is itself a drift signal, and it shows
  where the new model changes behaviour before anyone ships it.

### 2.5 Governance

The NIST AI RMF 1.0 (2023) MANAGE function and EU AI Act Art. 72
(post-market monitoring for high-risk systems; the article's text was checked
2026-09-27 at artificialintelligenceact.eu/article/72) both expect in-service
monitoring with a plan written down in advance [A]. The UK Surveillance Camera
Code of Practice (principle 10: review and audit) and JSP 936 read the same way
for our buyers (68 Q14). The engineering point is that the monitor, its
thresholds and its escalation path are part of the deliverable, not an ops
afterthought (Sculley et al. 2015; Breck et al. 2017, "The ML Test Score").

## 3. A per-camera monitoring design

1. **Commissioning window**: 1–2 weeks per camera. Store the per-hour
   distributions of image statistics, detection rate, confidence and track
   length.
2. **Imaging-chain monitor**: per-frame image statistics (13 numbers, about
   0.2 s/frame on CPU [V]), aggregated per minute and compared with the same
   hour-of-day slice of the reference. It raises camera-health tickets.
3. **Output monitors**: detection rate, confidence and track-length
   distributions, compared hourly. They raise "model at risk" flags.
4. **Alarm rate vs budget**: daily, per camera. It triggers a per-camera θ
   re-tune (H33, H35).
5. **Spot checks and dispositions**: monthly. These are the only direct recall
   estimate, and they gate retraining.
6. **Thresholds calibrated on the camera's own null**: the false-trigger budget
   is set per camera from its stationary commissioning data, not from a
   textbook constant (§4).

## 4. What H34 measured

**Setup.** H34 used 9 batch_v8 day cameras degraded with `cctv_day_720p`,
which includes AE/AWB drift and a GOP codec. At the midpoint of each stream we
injected one of 12 shifts: dusk (−1 to −3 EV with rising gain), defocus, a CRF
bump, or lens dirt. Each camera's reference was its own first 4 s, and each
monitor window was 1 s. Recall came from zero-shot YOLOv8n on the same shifted
frames. [V]

| Monitor | Detects | False triggers / 24 cam-h (1 eval/min) | ρ(score, recall drop) |
|---|---|---|---|
| PSI, max over 13 stats, thr 0.1/0.2/0.25 | 12/12 at delay 0 | **1,440** (fires on 100 % of null windows) | 0.49 |
| KS, Bonferroni | 12/12 at delay 0 | **1,440** | −0.13 |
| z-score, threshold calibrated on the camera null | dusk 1–3, dirt 2–3, codec 3 | 9.2 | 0.61 |
| YOLOv8n backbone embedding, calibrated | 0/12 | 0 (rule-of-3 ≤ 26.6) | 0.61 [0.07, 0.91] |

Four lessons follow. [V for our data; the mechanism is general]

1. **Conventional PSI thresholds are meaningless for short windows.** PSI with
   10 bins, 13 samples and a 50-sample reference sits at about 5–12 under the
   null, because any statistic that leaves the reference range fills an eps
   bin. The 0.1/0.25 rules of thumb come from credit scoring with thousands of
   rows per bin (Yurdakul 2018). Rabanser et al.'s finding that shift tests
   need hundreds of samples says the same thing.
2. **Calibrate on the camera's own null, over a long enough span.** A 4-s
   reference cannot see the AE cycle (40 s period) or the traffic cycle. The
   calibrated scores separate shifted streams from the null clearly
   (fig_h34.png), but a threshold set on 18 short nulls lands in the wrong
   place: z_cal is too loose (9 FA per 24 h) and the embedding is too strict
   (nothing detected). Certifying ≤ 1 false trigger per 24 cam-h needs about
   4,300 independent null windows per camera class with no trigger (rule of
   three). That is days of data, not minutes.
3. **Image-statistic drift is not the same as harm.** A codec shift moves
   blockiness and sharpness a lot but costs almost no recall. Dirt costs recall
   while moving PSI least. A good monitor ranks shifts by *harm*, so it has to
   be paired with an output-side monitor (confidence/detection-rate BBSD)
   and with spot-check recall.
4. **Dusk is the easy case and blur is the hard one.** Exposure moves the
   luma statistics by hundreds of reference SDs. Blur of 1.6–3.5 px moves the
   sharpness statistics by less than the spread between cameras in the null,
   yet at 3.5 px it costs 0.43 recall. Tamper and defocus detectors therefore
   need a dedicated sharpness reference per camera (Saglam & Temizel's
   long-term vs short-term edge energy), not a pooled threshold.

**Next (H34b):** a 24-h synthetic null per camera (day/night cycle, traffic
cycle), hour-of-day references, a k-of-n persistence rule, and the output-side
arm that 66 originally proposed (confidence-histogram PSI on 1-minute windows
of about 1,000 detections).

## 5. Interview-ready summary

"Per camera, against that camera's own commissioning data, on three signals:
the image-chain statistics (the camera-health channel already does a crude
version of this with tamper and defocus alarms), the model's outputs
(detection rate by hour, confidence histogram, track length), and alarm rate
against the operator budget. Recall itself I'd sample with monthly spot checks
and operator dispositions. I tested the label-free part on simulated shifts.
PSI at 0.2 fired on every stationary window, because the textbook threshold
assumes thousands of samples. A threshold calibrated on each camera's own
stationary data caught dusk and dirt within a second but missed blur. Its score
tracked recall loss at ρ ≈ 0.6. So the design holds up, the thresholds have to
be learned per camera over days, and I would pair it with an output-side
monitor because image drift and harm are not the same thing." 

## Sources

* Rabanser, Günnemann, Lipton. *Failing Loudly: An Empirical Study of Methods for Detecting Dataset Shift.* NeurIPS 2019.
* Lipton, Wang, Smola. *Detecting and Correcting for Label Shift with Black Box Predictors.* ICML 2018.
* Breck, Polyzotis, Roy, Whang, Zinkevich. *Data Validation for Machine Learning.* SysML 2019 (TFX Data Validation).
* Breck, Cai, Nielsen, Salib, Sculley. *The ML Test Score: A Rubric for ML Production Readiness.* IEEE Big Data 2017.
* Sculley et al. *Hidden Technical Debt in Machine Learning Systems.* NeurIPS 2015.
* Kang, Raghavan, Bailis, Zaharia. *Model Assertions for Monitoring and Improving ML Models.* MLSys 2020.
* Ribnick, Atev, Masoud, Papanikolopoulos, Voyles. *Real-Time Detection of Camera Tampering.* IEEE AVSS 2006.
* Saglam, Temizel. *Real-Time Adaptive Camera Tamper Detection for Video Surveillance.* IEEE AVSS 2009.
* Yurdakul. *Statistical Properties of Population Stability Index.* PhD thesis, Western Michigan University, 2018 (origin of the 0.1 / 0.25 PSI conventions and their sample-size dependence).
* Sato, Wider, Windheuser. *Continuous Delivery for Machine Learning.* martinfowler.com, 2019 (shadow deployment).
* Van Looveren et al. *Alibi Detect* (Seldon), open-source drift-detection library; Evidently AI drift-preset documentation.
* ONVIF Analytics Service / event topic specifications (video-source image-quality and global-scene-change events).
* NIST AI Risk Management Framework 1.0 (2023); EU AI Act (Regulation 2024/1689) Art. 72.
* Huyen. *Designing Machine Learning Systems*, O'Reilly 2022, ch. 8 (data distribution shifts).
