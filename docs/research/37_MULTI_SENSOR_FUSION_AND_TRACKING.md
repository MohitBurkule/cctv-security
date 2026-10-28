# 37 · Multi-sensor fusion and tracking for perimeter and counter-drone

**Why.** the vendor sells [vendor product], which "Fuses RADAR or RF, acoustic, and
EO/IR data streams within a low-SWaP, platform-agnostic architecture" for
"Counter-UAS and broader force protection" (file 33, [F] from their site). A
CCTV-intruder role in that company will be judged partly on whether you think
in **fused tracks**, not camera boxes, and whether you know the UK plumbing:
**SAPIENT / BSI Flex 335** for the interface, and **Stone Soup** for the
tracker. Deeper background is in `20_DEGRADED_IMAGERY_AND_FUSION.md` and
`R05_multisensor_fusion_and_nl_retrieval.md`.

**Tags.**
* **[F]** read on the cited primary source this session (2026-09-26). For
  SAPIENT and Stone Soup "primary" means the actual code: I cloned
  `github.com/dstl/SAPIENT-Proto-Files` and `github.com/dstl/Stone-Soup`
  (commit `e5a3e09`, 2026-09-25) and read the `.proto` and `.py` files.
* **[CALC]** my arithmetic or simulation, with the inputs cited.
* **[INF]** my design opinion.

No background-knowledge tags remain. Claims I could not source (for example
STANAG details, whose NGA-hosted PDFs return 403) have been removed.

---

## 1. Sensors on a CNI perimeter and what each is good for

The first table is engineering judgement about typical behaviour, so it is
tagged **[INF]** as a whole. The sensor *categories* match SAPIENT's own
`Registration.NodeType` enumeration (section 5.3), which is a useful
cross-check that the list is complete.

| Sensor | Gives | Strength | Typical failure |
|---|---|---|---|
| Radar (ground surveillance / C-UAS) | range, bearing, radial velocity, micro-Doppler | all weather, day and night, long range | birds, vegetation clutter, weak classification of *what* |
| EO (CCTV, PTZ) | appearance, class, identity cues | classification, evidence for operators | night, glare, fog, rain on the lens, tamper |
| Thermal IR | heat contrast | night, resists visual camouflage | thermal crossover at dawn and dusk, low resolution, blocked by glass |
| Acoustic | bearing (DoA), event class (glass, shout, rotor) | cheap, omnidirectional, drone rotor signature | range, wind, nuisance sounds |
| Passive RF (Wi-Fi/BLE, drone C2 links) | presence, emitter identity, controller bearing | sees through walls, cues silent targets | MAC randomisation, metres of RSSI ranging error |
| Fence / PIR / seismic | binary zone trips | very few misses at the line | wind, animals, no position beyond the zone |

**Principle [INF].** Use each sensor for what it is good at. Radar *finds*,
EO/IR *classifies and confirms*, RF and acoustic *cue* and *corroborate*, and
fence sensors *gate*. That is also the shape of the SAPIENT architecture.

## 2. Levels of fusion

| Level | What is combined | Pros | Cons |
|---|---|---|---|
| **Raw / pixel** (early) | e.g. an EO+IR image stack into one network | uses all the information; best for co-located, registered sensors | needs pixel registration, a common timebase and joint training data, which is rare |
| **Detection / measurement** (central) | every sensor's detections go into one tracker | statistically the best given good models: a weak radar blip plus a weak EO box can make a confident track | high bandwidth; needs every sensor's measurement model and covariance; millisecond time sync |
| **Track** (distributed, track-to-track) | each node tracks locally, a fusion node associates tracks | low bandwidth, vendor independence, survives link loss | errors between tracks are correlated, so the same prior gets counted twice and the result is overconfident |
| **Decision / declaration** | "intruder in zone 3, conf 0.8" | simplest; what alarm panels do | throws away geometry; confidence means different things per vendor |

The table is my synthesis **[INF]**, but the double-counting problem in track
fusion has a concrete, fetched fix. Stone Soup's `ChernoffUpdater` implements
the Chernoff fusion rule `p_ω(x) ∝ p₁(x)^ω · p₂(x)^(1−ω)` and notes that for
Gaussians "the above formula is equal to the Covariance Intersection Algorithm
from Julier et al.", giving the fused covariance
`D = (ω A⁻¹ + (1−ω) B⁻¹)⁻¹` and mean `d = D (ω A⁻¹ a + (1−ω) B⁻¹ b)`
(`stonesoup/updater/chernoff.py`) **[F]**. Covariance intersection stays
consistent whatever the unknown cross-correlation, which is why it is the
default answer to "how do you fuse two tracks that may share information?".

**Practical answer [INF].** Use detection-level fusion inside one vendor's
tightly integrated head (radar+EO slew-to-cue), and track- or
declaration-level fusion across vendors. SAPIENT is a standard for that second
layer, though it also carries raw-ish detections (section 5).

## 3. Trackers you should be able to talk about

### 3.1 The families, with primary references

* **Kalman / EKF / UKF + GNN (global nearest neighbour).** Hungarian
  assignment on gated Mahalanobis distance. This is the world of SORT and
  ByteTrack. It is fine when targets are well separated. Stone Soup has
  `GlobalNearestNeighbour` and `GNNWith2DAssignment` (the second uses a matrix
  assignment "instead of joint hypothesis enumeration")
  ([Stone Soup data associator docs](https://stonesoup.readthedocs.io/en/latest/stonesoup.dataassociator.html)) **[F]**.
* **PDA / JPDA (joint probabilistic data association).** Each track is updated
  with a probability-weighted mixture of all gated measurements. Stone Soup's
  docstring puts it as: "Rather than associate specific Detections/Tracks,
  JPDA calculates the new state of a Track based on its possible association
  with ALL Detections. The new state is a Gaussian Mixture, reduced to a single
  Gaussian" (`stonesoup/dataassociator/probability.py`) **[F]**. The original
  paper is Fortmann, Bar-Shalom & Scheffe, *IEEE J. Oceanic Eng.* 8(3):173–184,
  1983. I could not open the IEEE page, so the working equations below are
  taken from Stone Soup's implementation. JPDA's cost grows
  combinatorially with the size of an ambiguity cluster, and nearby tracks
  pull towards each other (coalescence), which the worked example in section
  3.3 shows numerically.
* **MHT (multiple hypothesis tracking).** Keeps a tree of association
  hypotheses and defers hard decisions, running a Kalman filter per
  hypothesis. The founding paper is Reid 1979 (*IEEE TAC* 24(6):843–854, DOI
  10.1109/TAC.1979.1102177; bibliographic only, page not opened).
  How hard it is to build is documented directly: its implementation "is
  associated with a significant programming effort, code size and long
  implementation time" ([Antunes et al., arXiv:1106.2263](https://arxiv.org/abs/1106.2263)) **[F]**.
* **Random finite sets: PHD, GM-PHD, GLMB.** Model the *set* of targets and
  estimate their number and states without explicit association.
  * GM-PHD is the closed-form Gaussian-mixture PHD filter (Vo & Ma, *IEEE
    TSP* 54:4091–4104, 2006, DOI 10.1109/TSP.2006.881190; bibliographic only).
    Stone Soup implements it as `PHDUpdater` inside
    `PointProcessMultiTargetTracker`, whose documentation calls it the
    "Gaussian Mixture implementation of point process filtering" **[F]**.
  * Plain PHD has no track labels. Labelled RFS filters fix that. The
    δ-GLMB filter is made tractable with ranked assignment for the update
    and k-shortest paths for the prediction
    ([Vo, Vo & Phung, arXiv:1312.2372](https://arxiv.org/abs/1312.2372)) **[F]**.
  * These are the right tools when clutter is dense and the number of targets
    is unknown: drone swarms, bird flocks **[INF]**.

(The bibliographic details for Fortmann, Reid and Vo & Ma come from search
result listings. Their IEEE landing pages would not load, so I cite only the
bibliographic facts and make no claim that depends on their text. The algorithmic content I rely on is from
the fetched Stone Soup code and the arXiv papers.)

### 3.2 Stone Soup: what is actually in it

Stone Soup is Dstl's MIT-licensed "framework for the development and testing
of tracking algorithms" ([GitHub](https://github.com/dstl/Stone-Soup)) **[F]**.
Its design is component-based. A tracker is assembled from a **Predictor**, an
**Updater**, a **DataAssociator** (which uses a **Hypothesiser**), an
**Initiator**, a **Deleter** and a detection **Reader**, with
**MetricGenerators** for evaluation. The design page stresses "modularity and
uniformity of external interfaces" and that "different Updaters are
interchangeable (within limits)"
([design page](https://stonesoup.readthedocs.io/en/latest/design.html)) **[F]**.

Classes I read in the source (commit `e5a3e09`) **[F]**:

| Component | Classes |
|---|---|
| **Trackers** (`stonesoup/tracker/`) | `SingleTargetTracker`, `SingleTargetMixtureTracker`, `MultiTargetTracker`, `MultiTargetMixtureTracker` (the mixture versions consume JPDA-style weighted hypotheses), `PointProcessMultiTargetTracker` (GM-PHD / LCC), `Single/MultiTargetExpectedLikelihoodParticleFilter`, `PMHTTracker` ("Probabilistic Multi-Hypothesis Tracker … Currently we assume a fixed number of targets") |
| **Data associators** | `NearestNeighbour`, `GlobalNearestNeighbour`, `GNNWith2DAssignment`, `PDA`, `JPDA`, `JPDAwithLBP` (loopy belief propagation), `JPDAwithEHM` / `JPDAwithEHM2` (efficient hypothesis management, exact marginals), `MFADataAssociator` (multi-frame assignment over a sliding window, citing Xia et al. 2019 on the multi-scan trajectory PMBM filter), plus KD-tree and TPR-tree accelerated variants |
| **Updaters** | `KalmanUpdater`, `ExtendedKalmanUpdater`, `UnscentedKalmanUpdater`, `CubatureKalmanUpdater`, `IteratedKalmanUpdater`, `SqrtKalmanUpdater`, `SchmidtKalmanUpdater`, `StochasticIntegrationUpdater`, `PHDUpdater`, `LCCUpdater`, `ChernoffUpdater`, particle updaters |
| **Initiators / deleters** | `MultiMeasurementInitiator`, `SimpleMeasurementInitiator`, `GaussianMixtureInitiator`, …; `UpdateTimeStepsDeleter`, `UpdateTimeDeleter`, `CovarianceBasedDeleter`, `CompositeDeleter` |
| **Track-to-track** | `TrackToTrackCounting`, `TrackToTruth`, `TrackIDbased`, `OneToOneTrackAssociator`, `ClearMotAssociator` |
| **Metrics** | `OSPAMetric` (a subclass of `GOSPAMetric`), `SIAPMetrics`, `IDSIAPMetrics`, `ClearMotMetrics`, `PCRBMetric`, covariance-norm metrics |

**Two corrections to my earlier notes.**
1. There is **no class called "MHT"** in Stone Soup. Multi-hypothesis
   behaviour comes from `MFADataAssociator` (multi-frame assignment, an
   N-scan style method) and `PMHTTracker`. Say "Stone Soup does MHT-style
   tracking through its multi-frame assignment associator", not "Stone Soup's
   MHT tracker".
2. GOSPA *is* implemented (`stonesoup/metricgenerator/ospametric.py`),
   including a switching term for track-label swaps.

A minimal Stone Soup JPDA tracker is therefore
`MultiTargetMixtureTracker(initiator, deleter, detector, JPDA(PDAHypothesiser(predictor, updater, clutter_spatial_density, prob_detect)), updater)`.
The multi-sensor version is to merge the detection readers and let
`PDAHypothesiser` evaluate each detection with its own measurement model.
**[INF]** on the recipe, **[F]** on the class names.

### 3.3 Worked example: one JPDA step with two sensors **[CALC]**

The equations are the ones in Stone Soup's `PDAHypothesiser` docstring and
code (`stonesoup/hypothesiser/probability.py`) **[F]**:

* likelihood of measurement *j* for a track: `L = N(z_j; ẑ, S) · P_D / λ`,
  where `S = H P Hᵀ + R` is the innovation covariance and λ is the clutter
  spatial density;
* missed-detection weight: `1 − P_D · P_G`;
* `JPDA` then enumerates joint hypotheses (each measurement to at most one
  track), multiplies the per-track weights, normalises, and marginalises to
  get β_{t,j}; the track is updated with the β-weighted mixture, reduced to a
  single Gaussian.

**Set-up.** Two walkers, tracks **A** and **B**, predicted at (0, 0) m and
(6, 0) m in the site ENU frame, predicted position covariance
`P = 4·I` m² (σ = 2 m). `P_D = 0.9`, `P_G = 0.99`.

* **Sensor 1, ground radar.** σ = 3 m after range/bearing → ENU conversion,
  so `R = 9·I`, `S = 13·I`. Clutter λ = 10⁻⁴ per m². Two detections:
  z₁ = (2.5, 1.0), z₂ = (4.0, −0.5).
* **Sensor 2, EO camera projected to the ground plane.** σ = 1 m, `R = I`,
  `S = 5·I`. Clutter λ = 10⁻³ per m² (more nuisance per area). One detection:
  z₃ = (3.2, 0.3).

The two sensors are processed **sequentially** on the same predicted tracks,
which is the standard way to fuse asynchronous sensors at detection level.
(To keep the numbers readable I apply the EO scan to the same prediction
rather than to the radar-updated state.)

**Radar scan.** Mahalanobis distances d² and likelihoods L:

| | z₁ | z₂ |
|---|---|---|
| A | d² = 0.56, L = 83.4 | d² = 1.25, L = 59.0 |
| B | d² = 1.02, L = 66.2 | d² = 0.33, L = 93.6 |

Missed-detection weight `1 − 0.9 × 0.99 = 0.109`. Joint hypotheses,
normalised:

| A ← | B ← | probability |
|---|---|---|
| z₁ | z₂ | **0.665** |
| z₂ | z₁ | **0.333** |
| any one miss | | ≈ 0.001 each |
| both miss | | < 0.001 |

Marginals: β_A = (miss 0.001, z₁ 0.665, z₂ 0.333) and
β_B = (0.001, 0.333, 0.665). With Kalman gain `K = P S⁻¹ = (4/13)·I`, the
combined innovation moves A to **(0.92, 0.15)** and B to **(5.23, 0.00)**.

**EO scan.** One detection, near the midpoint:

| | z₃ |
|---|---|
| A | d² = 2.07, L = 10.2 |
| B | d² = 1.59, L = 13.0 |

Hypotheses: (A←z₃, B miss) 0.438, (A miss, B←z₃) 0.557, both miss 0.005.
So β_A(z₃) = 0.438 and β_B(z₃) = 0.557, and **both** tracks move towards the
single EO detection: A to (1.12, 0.11) and B to (4.75, 0.13).

**What the example teaches [INF].**
1. **The radar is ambiguous (0.665 vs 0.333), and JPDA hedges** instead of
   committing, as GNN would. That is the point of JPDA.
2. **Coalescence is visible.** One EO detection between two tracks pulls
   both of them towards it: from the shared prediction A moves 1.1 m
   and B 1.25 m towards z₃ (and A still ends 0.2 m, B 0.5 m further
   towards the middle than the radar-only update put them). Repeat that for a few scans
   while two people walk together and the tracks merge. That is the textbook
   JPDA failure, and exactly why multi-frame methods (MFA/MHT) or labelled
   RFS filters exist.
3. **λ carries the sensor's credibility.** The EO clutter density is ten
   times the radar's in this example, so an EO hit counts for less evidence
   per unit likelihood. Calibrating λ per sensor and per condition (night,
   rain) *is* the confidence-calibration problem of section 4.
4. **Appearance breaks the tie.** A ReID embedding distance can be multiplied
   into L for the EO detection, which is how camera identity cues enter a
   Bayesian tracker without special-case code.

The script that produced these numbers is 40 lines of NumPy/SciPy. It is
reproducible from the parameters above.

## 4. Registration, time sync and calibration

**Spatial registration [INF].** Every sensor needs a pose in a common frame:
* a site ENU frame anchored to a surveyed point or a GNSS/RTK reference;
* camera extrinsics and intrinsics (file 29);
* the radar's boresight and north alignment.

Bias hurts more than noise. **[CALC]** A 1° radar north misalignment gives
1000 m × tan(1°) = **17.5 m** of error at 1 km. That is several times the 3 m
radar σ in the worked example, so gating would reject the true association
with the EO track. Estimate bias online from targets of opportunity, or with a
cooperative walker or drone carrying GPS truth. SAPIENT supports this
directly: `Location` carries `x_error`, `y_error`, `z_error` alongside the
coordinates and a mandatory `datum` (`location.proto`) **[F]**, so each node
can declare its own uncertainty.

**Time.**
* **[CALC]** A walker at 1.5 m/s moves 0.15 m in 100 ms, which is fine. A
  drone at 20 m/s moves 2 m in 100 ms, which is comparable to EO σ. So
  timestamp at the sensor, not on arrival.
* SAPIENT makes that possible: every `SapientMessage` carries a mandatory UTC
  `google.protobuf.Timestamp` (`sapient_message.proto`) **[F]**.
* For the clock itself, IEEE 1588 is the "Standard for A Precision Clock
  Synchronization Protocol for Networked Measurement and Control Systems"
  ([NIST IEEE 1588 page](https://www.nist.gov/el/intelligent-systems-division-73500/ieee-1588)) **[F]**.
* Late data must be handled as **out-of-sequence measurements (OOSM)**. The
  optimal multi-target treatment "performs a retrodiction step that adds
  trajectory information at the OOS measurement time stamp followed by an
  update step" ([García-Fernández & Yi, arXiv:2106.04898](https://arxiv.org/abs/2106.04898)) **[F]**.
  The cheap engineering alternative is a small reorder buffer, which trades
  latency for simplicity. **[INF]**
* CCTV over RTSP adds variable delay, often hundreds of milliseconds, which is
  the classic pitfall. **[INF]**, from experience rather than a source.

**Confidence calibration across sensors [INF].** A radar "0.9" and a detector
"0.9" do not mean the same thing.
* Calibrate each sensor's score to an empirical probability (temperature
  scaling or isotonic regression) **per condition bin**: night, rain, range
  band.
* Then fuse in log-odds, with a correlation discount for sensors that share a
  failure mode. EO and IR both fail in fog, so they should not be counted as
  independent. Covariance intersection (section 2) is the state-space version
  of the same caution.
* Report reliability diagrams per sensor. SurvSim can generate the
  condition-labelled data needed to fit these curves, because its ground truth
  is exact.
* SAPIENT carries confidence as `detection_confidence` (a float in 0–1) plus a
  per-class `confidence` inside each `DetectionReportClassification`
  **[F]**. The standard gives you the field, not its calibration. Calibration
  is your job.

## 5. SAPIENT / BSI Flex 335: the actual interface

### 5.1 What it is

* SAPIENT (Sensing for Asset Protection with Integrated Electronic Networked
  Technology) is "a network of advanced sensors with artificial intelligence
  (AI) at the edge, combined with intelligent fusion and sensor management"
  ([gov.uk guidance](https://www.gov.uk/guidance/sapient-autonomous-sensor-system)) **[F]**.
* The ICD is freely available as **BSI Flex 335**. From SAPIENT **version 7**
  it "moved from a XML-based message format to a binary Protobuf-based message
  format", reducing bandwidth by about 60 % **[F]** (gov.uk).
* The UK MOD adopted SAPIENT as its counter-UAS standard in the 2019
  Counter-Unmanned Air Systems Strategy **[F]** (gov.uk).
* NATO exercises: at **TIE21** (November 2021) it "facilitated over 70
  connections between C-UAS sensor systems". At **TIE22** (September 2022) it
  "enabled 31 advanced autonomous sensor nodes from different vendors to
  connect to 13 decision-making nodes" **[F]** (gov.uk).
* Open resources: `dstl/SAPIENT-Proto-Files`,
  `dstl/BSI-Flex-335-v2-Test-Harness` and `dstl/Apex-SAPIENT-Middleware` on
  GitHub **[F]** (gov.uk).

The repository README sets out four principles **[F]**
([SAPIENT-Proto-Files README](https://github.com/dstl/SAPIENT-Proto-Files/blob/main/Readme.md)):
1. local autonomy at the edge;
2. transmission of *information*, not raw sensor data;
3. fusion at remote fusion nodes, which generate tasking for taskable edge
   nodes;
4. local autonomous execution of the tasking received.

The README also says BSI Flex 335 "came into effect on May 31st 2023", lists
Dstl's Paul Thomas as lead technical author, and names an advisory group
including Createc, L3Harris, Leonardo, MARSS, MBDA and others **[F]**. Version
2.0 adds hierarchies of fusion nodes and mobile or pointable nodes, with new
`MOVE_TO`, `PATROL` and `FOLLOW` commands **[F]** (search listing of the
same repo, confirmed by the `task.proto` fields below).

### 5.2 The envelope

Every message is a `SapientMessage` (`bsi_flex_335_v2_0/sapient_message.proto`) **[F]**:

```
SapientMessage
 ├─ timestamp        (UTC, mandatory)
 ├─ node_id          (UUID of sender, mandatory)
 ├─ destination_id   (UUID, optional; used when tasking a node)
 └─ oneof content
      4  Registration        5  RegistrationAck
      6  StatusReport        7  DetectionReport
      8  Task                9  TaskAck
     10  Alert              11  AlertAck
     12  Error
```

Nine message types in total. The lifecycle **[INF]** on the sequence, **[F]**
on the message names:

```
 Edge node (ASM)                               Fusion node (DMM)
      │ ── Registration (what I am, modes, classes, FoV) ──►│
      │ ◄───────────── RegistrationAck ─────────────────── │
      │ ── StatusReport (heartbeat: OK/WARNING/ERROR,      │
      │      coverage, obscuration, power, faults) ──────► │
      │ ── DetectionReport (object_id, location, conf,     │
      │      classification, behaviour, velocity) ───────► │  fuse, decide
      │ ◄───────── Task (look_at / mode_change /           │
      │      thresholds / move_to / patrol / follow) ───── │
      │ ── TaskAck ──────────────────────────────────────► │
      │ ── Alert (e.g. tamper, mode change) ─────────────► │
      │ ◄───────────── AlertAck ────────────────────────── │
```

### 5.3 The messages, field by field

**`Registration`** (`registration.proto`) **[F]**. The node declares what it
is. `NodeType` values include RADAR, LIDAR, CAMERA, SEISMIC, ACOUSTIC,
PROXIMITY_SENSOR, PASSIVE_RF, **HUMAN** (a spotter or guard), CHEMICAL,
BIOLOGICAL, RADIATION, and effectors: KINETIC, JAMMER, CYBER, LDEW (laser
directed energy weapon), RFDEW, plus MOBILE_NODE, POINTABLE_NODE and
FUSION_NODE (a child fusion node in a hierarchy). The node also declares its
modes (`ModeType`: PERMANENT, TEMPORARY, DEFAULT; `ScanType`: FIXED, SCANNING,
STEERABLE) and, most usefully for a tracking engineer, its **`TrackingType`**:

| TrackingType | Meaning (from the proto comments) |
|---|---|
| `NONE` | no data association; every detection gets a new `object_id` |
| `TRACKLET` | tries to keep `object_id` between detections of the same object |
| `TRACK` | keeps `object_id` persistently |
| `TRACK_WITH_RE_ID` | tracks that can be re-associated using re-identification |

A CCTV analytics node that does ByteTrack plus appearance ReID should register
as `TRACK_WITH_RE_ID`. That enumeration is where our whole multi-camera ReID
story plugs into the UK standard. **[INF]**

`DetectionDefinition` inside the registration lists the classes and behaviours
the node can report, with `PerformanceValue` entries for detection
performance and `GeometricError`, so a fusion node can know each sensor's
claimed accuracy before the first detection arrives **[F]**.

**`DetectionReport`** (`detection_report.proto`) **[F]**.

| # | Field | Notes |
|---|---|---|
| 1 | `report_id` | ULID, mandatory |
| 2 | `object_id` | ULID, mandatory; this is the track ID if the node tracks |
| 3 | `task_id` | the task the node is executing |
| 4 | `state` | special cases, e.g. "object lost" |
| 5/6 | `range_bearing` **or** `location` | `oneof`: polar relative to the node, or x/y/z with errors, coordinate system and datum |
| 7 | `detection_confidence` | 0–1 |
| 8/10 | `track_info`, `object_info` | key–value extras declared at registration |
| 9 | `prediction_location` | where the object is predicted to be |
| 11 | `classification` | repeated: `type` (mandatory), `confidence`, nested `sub_class` |
| 12 | `behaviour` | repeated behavioural information |
| 13 | `associated_file` | URLs for clips or images, hosted on the network |
| 14 | `signal` | RF signal information |
| 15/16 | `associated_detection`, `derived_detection` | links to other SAPIENT detections |
| 19 | `enu_velocity` | velocity vector |
| 22/23 | `colour`, `id` | object colour; object ID such as an aircraft tail number |

Fields 17, 18, 20 and 21 are `reserved`: they were used in SAPIENT v7 and have
been retired (17/18/20/21 were alternative velocity frames; only ENU survives in the `oneof`).

**Implications [INF].**
* `associated_file` is how an EO node gives the operator the evidence clip
  without streaming video over the tactical link, which is principle 2 in
  practice.
* `behaviour` is where loiter, approach and dwell outputs belong. SurvSim's
  behaviour catalogue maps onto it directly.
* `object_id` + `TrackingType` means a fusion node can distinguish "same
  person, still tracked" from "new detection", which is what track-level
  fusion needs.

**`StatusReport`** (`status_report.proto`) **[F]**. This is the heartbeat and
health message. `System` is OK, WARNING, ERROR or GOODBYE. `coverage` and
`obscuration` are regions (repeated, so a child fusion node can report its
aggregate coverage). `Power` has a source (mains, battery, solar,
generator, fuel cell…) and a status. `StatusType` includes INTERNAL_FAULT,
EXTERNAL_FAULT, ILLUMINATION, WEATHER, CLUTTER, EXPOSURE,
MOTION_SENSITIVITY, PTZ_STATUS, **PD**, **FAR** and NOT_DETECTING, with a
`StatusLevel` of information, warning or error.

**This is the graceful-degradation hook [INF].** A camera node that detects
its own blinding or tamper (SurvSim has 6 tamper kinds) should report
`EXTERNAL_FAULT` or `NOT_DETECTING` and shrink its `coverage`, and it should
report its current `PD`/`FAR` in fog. The fusion node then re-weights. The
fact that PD and FAR are first-class status types says that the standard
expects nodes to know their own operating-point performance. That is exactly
the per-condition calibration of section 4.

**`Task`** (`task.proto`) **[F]**. `Control`: START, STOP, PAUSE. A
`Command` is a `oneof`:
* `request` (free text);
* `detection_threshold`, `detection_report_rate`, `classification_threshold`
  (each LOW, MEDIUM or HIGH);
* `mode_change`;
* `look_at` (a location or range-bearing, for pointing nodes such as a PTZ);
* `move_to`, `patrol` (location lists) and `follow` (an object), for mobile
  nodes.

`Region` has a `RegionType` of AREA_OF_INTEREST, IGNORE, BOUNDARY,
MOBILE_NODE_NO_GO_AREA or MOBILE_NODE_GO_AREA, with class and behaviour
filters. **Slew-to-cue is a SAPIENT `Task` with `look_at`.** Ignore zones
(the tree that always triggers) are a `Region` with `REGION_TYPE_IGNORE`.
**[INF]** on the use; **[F]** on the fields.

**`Alert`** (`alert.proto`) **[F]**. `AlertType`: INFORMATION, WARNING,
CRITICAL, ERROR, FATAL, MODE_CHANGE. `AlertStatus`: ACTIVE, ACKNOWLEDGE,
REJECT, IGNORE, CLEAR. `DiscretePriority`: LOW, MEDIUM, HIGH. An alert carries
a location, `associated_file` and `associated_detection` links. The operator's
`AlertAck` is, in effect, a label: an ACKNOWLEDGE or REJECT on a specific
alert is exactly the operator verdict we want to feed back into training.
**[INF]**

### 5.4 How a SurvSim camera node would speak SAPIENT **[INF]**

```
survsim Director GT  ──►  EO analytic (detector + ByteTrack + ReID)
                               │ ground-plane projection (calib from Recorder)
                               ▼
                 SapientMessage{ timestamp=render time (UTC),
                                 node_id=camera UUID,
                   detection_report{ object_id=ULID(track_id),
                                     location{x,y,z, x_error,y_error, datum},
                                     detection_confidence=calibrated p,
                                     classification[{type:"Human", confidence}],
                                     behaviour[{"loiter", conf}],
                                     enu_velocity{...},
                                     associated_file[{url: clip.mp4}] } }
```

Because the Director knows the truth, every emitted report can be scored:
was the object real, was the location within the declared error, was the
behaviour correct, and was the `StatusReport` honest about PD in fog. A
"SAPIENT conformance plus accuracy" harness is a concrete product idea that
SurvSim is close to supporting. It would need a protobuf writer beside the
existing GT writers, and nothing else structural.

## 6. Other standards, briefly

* **ONVIF Profile M** covers "analytics configuration and information query
  for metadata", "configuration and streaming of metadata", generic object
  classification, and metadata definitions for "geolocation, vehicle, license
  plate, human face and body". Events can go over the metadata stream, the
  ONVIF event service, or MQTT
  ([ONVIF Profile M](https://www.onvif.org/profiles/profile-m/)) **[F]**. This
  is the civil-CCTV counterpart of a SAPIENT detection report.
* **NATO STANAGs.** I could not fetch the STANAG 4609 or MISB documents (the
  NGA-hosted PDFs return 403), so I will not state their contents. In an
  interview I would say "I know motion imagery from drones arrives under a
  NATO motion-imagery STANAG with platform metadata, and I would read the
  spec before designing geo-registration from it". **[INF]**

**Why it matters to the vendor [INF].** A product that emits SAPIENT detection
reports can plug into UK C-UAS integrations without bespoke work. If
[vendor product]'s fusion engine speaks SAPIENT, an EO analytic becomes one more
autonomous sensor module. Whether [vendor product] or [vendor product] consume SAPIENT is a
good question to ask them.

## 7. Evaluating fused tracks

* **OSPA.** A multi-object distance combining localisation and cardinality
  error with a cut-off *c* (Schuhmacher, Vo & Vo, *IEEE TSP* 56(8):3447–3457,
  2008, DOI 10.1109/TSP.2008.920469; bibliographic only). The implementation I
  rely on is Stone Soup's `OSPAMetric`, which subclasses `GOSPAMetric` **[F]**.
* **GOSPA** is "unnormalized as a function of the cardinality" and penalises
  cardinality errors differently, so it decomposes into localisation error,
  **missed** targets and **false** targets. That lets you say *why* a result
  is bad ([Rahmathullah, García-Fernández & Svensson, arXiv:1601.05585](https://arxiv.org/abs/1601.05585);
  best paper, FUSION 2017) **[F]**. Stone Soup implements it as `GOSPAMetric`
  with a label-switching term **[F]**.
* **SIAP** (single integrated air picture). Stone Soup's `SIAPMetrics`
  computes **completeness** ("fraction of true objects being tracked", target
  1), **ambiguity** (tracks per true object, target 1), **spuriousness**
  (fraction of tracks not assigned to a truth, target 0), **positional** and
  **velocity accuracy** (target 0), **rate of track number changes** (target 0)
  and **longest track segment** (target 1). `IDSIAPMetrics` adds ID
  completeness, ID correctness and ID ambiguity
  ([Stone Soup track-to-truth metrics](https://stonesoup.readthedocs.io/en/latest/stonesoup.metricgenerator.tracktotruthmetrics.html)) **[F]**.
* **HOTA / IDF1** for identity over time. SurvSim already implements these,
  validated against MOT20 (CLAUDE.md).
* **Operational metrics [INF].** False alarms per *site*-hour (not per
  camera), time to first alarm, time to operator confirmation, and the
  probability of detecting the intruder before they reach the asset.
* **Sensor-dropout ablation [INF].** Remove each sensor in turn and report the
  metric change. A fused system that is worse than its best single sensor
  under dropout has a confidence-calibration bug.

**Mapping for the interview [INF].** SIAP "spuriousness" is the fusion
community's false-alarm rate; SIAP "ambiguity" is roughly the MOT community's
fragmentation; "rate of track number changes" is ID switches. Speaking both
vocabularies is what a CCTV person moving into defence fusion should
demonstrate.

## 8. How SurvSim's RF and audio sensors relate

* `survsim/sensors/rf.py` models Wi-Fi probe and BLE emitters per person,
  **MAC randomisation** (with MAC-to-identity ground truth recorded),
  log-distance path loss with log-normal shadowing (`PATH_LOSS_EXPONENT = 2.8`,
  `SHADOWING_SIGMA_DB = 4.0`, read from the source today) and RSSI ranging.
  It gives exactly what an RF-camera association study needs, and what real
  deployments never have: the true identity behind each MAC.
* `survsim/sensors/audio.py` models inverse-square spreading plus absorption,
  ambient noise rising with crowd and weather, DoA error growing as SNR falls,
  and **nuisance events** at a configurable rate. This is the hard-negative
  principle applied to audio.
* `survsim/sensors/thermal.py` models apparent temperature, thermal
  **crossover** by hour, and pixels-on-target detectability.
* **Gap: no radar model yet.** A simple one (range, bearing and Doppler noise;
  P_D as a function of RCS and range; Poisson clutter at a configurable λ;
  birds as hard negatives) is the obvious next sensor for a C-UAS or CNI
  story. It would feed the JPDA example above directly. **Say "next", not
  "done".**
* Because the Director owns ground truth for every agent, each sensor's
  measurements carry the true identity. That means detection-level fusion,
  association accuracy, GOSPA and SIAP can all be scored exactly, and the
  per-condition λ and P_D values that JPDA needs can be *measured* rather than
  guessed. **[INF]**
* **Measured on SurvSim (H53, 2026-09-27, 32 §H53) [V repo, simulated sensors].**
  Late fusion of the line-cross rule with a gate access log, the RF model above
  (registered BLE tag, RSSI > −80 dBm) and a simple PIDS model removed 99.0 %
  [98.5, 99.5] of authorised-crosser false alarms (0.488 → 0.0047 FA/cam-h) at
  a recall cost of 0.023 (0.782 → 0.758). RF proximity alone cost 16 recall
  points (tagged staff near intruders); tailgating a badged gate defeats the
  combined rule. Every sensor parameter is an assumption, not a product figure, and
  alarms were matched to sensors on true tracks/positions (a real system uses
  estimated positions; H54).

## 9. Concrete design: fused intruder detection for a CNI site **[INF]**

Site: a substation or water works, a 600 m fenced perimeter, one gatehouse,
unattended at night, with a remote alarm-receiving-centre (ARC) operator.

```
                        ┌──────────────── Layer 4: human ────────────────┐
                        │ ARC operator: 1 alarm = 1 fused track + clip   │
                        │ + map + "why"; AlertAck = label → retraining   │
                        └───────────────────────▲────────────────────────┘
                                                │ SAPIENT Alert
┌────────────────────────── Layer 3: logic ─────┴───────────────────────────┐
│ zone rules on fused tracks (approach → dwell → breach), loiter vs          │
│ commute_wait models, slew-to-cue (SAPIENT Task look_at), tamper watchdog   │
└──────────────────────────────────────▲─────────────────────────────────────┘
┌────────────────────────── Layer 2: fusion node (DMM) ─────────────────────┐
│ Stone Soup: detection-level JPDA (or MFA if crossings matter, GM-PHD/GLMB  │
│ if swarms); ChernoffUpdater (covariance intersection) for 3rd-party tracks │
│ online bias estimation; per-sensor λ, P_D from StatusReport + calibration  │
└───────▲──────────────────▲───────────────────▲──────────────────▲─────────┘
        │ DetectionReport  │                   │                  │
┌───────┴──────┐  ┌────────┴────────┐  ┌───────┴───────┐  ┌───────┴────────┐
│ 2 ground     │  │ 6 EO + 6 thermal│  │ acoustic nodes│  │ fence zones (8)│
│ radars (360°)│  │ + 2 PTZ; Orin NX│  │ rotor / glass │  │ + RF sniffer   │
│ NodeType     │  │ per 4 cams:     │  │ / cutting     │  │ at gate        │
│ RADAR        │  │ INT8 detector,  │  │ ACOUSTIC      │  │ PROXIMITY /    │
│              │  │ ByteTrack+ReID  │  │               │  │ PASSIVE_RF     │
│              │  │ TRACK_WITH_RE_ID│  │               │  │                │
└──────────────┘  └─────────────────┘  └───────────────┘  └────────────────┘
      Layer 0 cue / Layer 1 edge
```

Key decisions:
1. **Radar first, camera confirms.** An alarm needs a fused track above the
   probability threshold *and* either EO/IR confirmation or two independent
   cue modalities. That cuts foliage and bird alarms, which cause most of the
   nuisance at CNI sites.
2. **Graceful degradation through `StatusReport`.** Each node publishes its
   health. The fusion node re-weights, and the alarm policy tightens or
   loosens explicitly by mode. For example: "EO blinded → thermal and radar
   only, raise the threshold, tell the operator capability is reduced".
   Blinding is itself an `Alert`.
3. **Time budget [CALC].** Fence to asset is about 40 s at a walk (60 m at
   1.5 m/s). With a 25 s i-LIDS-style tolerance, and allowing time for the
   operator to act, the pipeline must alarm within roughly 10 s of the fence
   crossing, which drives edge placement.
4. **Evaluate in SurvSim first.**
   * Scenario sweep: night, fog, rain, wind; intruders mixed with hard
     negatives (deer, a maintenance crew, a passer-by at the fence).
   * Report false alarms per site-night, time to alarm, GOSPA and SIAP, and
     the dropout ablation.
   * Then shadow-deploy on the real site, logging operator `AlertAck`
     verdicts before alarms go live.

## 10. Interview answers (8 Q&As)

**Q1. What is SAPIENT, concretely?**
A. A Dstl-originated architecture and interface, published as BSI Flex 335,
where sensor nodes do their own AI at the edge and send information rather
than raw data to fusion nodes that task them. Since version 7 the messages are
protobuf, which cut bandwidth by about 60 %. There are nine message types in a
`SapientMessage` envelope: Registration and its Ack, StatusReport,
DetectionReport, Task and its Ack, Alert and its Ack, and Error. MOD adopted it
for counter-UAS in 2019. At NATO TIE22 it connected 31 nodes from different
vendors to 13 decision nodes.

**Q2. If you built a CCTV analytic for us, how would it plug into SAPIENT?**
A. Register as a CAMERA node with `TrackingType` TRACK_WITH_RE_ID, and declare
classes, behaviours and geometric error. Emit DetectionReports with a stable
`object_id` per track, a ground-plane location with x/y error, a calibrated
`detection_confidence`, classifications, behaviours like loiter, ENU velocity,
and an `associated_file` URL for the clip. Heartbeat with StatusReports that
report honest PD, FAR and coverage, including tamper as a fault. Accept `Task`
`look_at` for PTZ slew-to-cue and IGNORE regions for nuisance zones.

**Q3. GNN, JPDA or MHT: which and when?**
A. GNN when targets are well separated and clutter is low; it's what
ByteTrack does. JPDA when there's clutter and occasional closeness; it hedges
rather than committing, but tracks coalesce when targets walk together. My
worked example shows two tracks both pulled 0.2–0.5 m towards one ambiguous EO
detection. Multi-frame methods (MHT, or Stone Soup's MFA associator) when
crossing targets matter and you can afford the compute. Labelled RFS (GLMB)
for swarms with unknown numbers.

**Q4. What is in Stone Soup, and why would you use it?**
A. Dstl's MIT-licensed tracking framework, built from interchangeable
components: predictor, updater, hypothesiser, data associator, initiator,
deleter, tracker and metric generators. It has Kalman variants from EKF to
cubature, PDA and JPDA (including EHM and loopy-BP versions), GNN, a
multi-frame assignment associator, GM-PHD and LCC updaters, a PMHT tracker,
covariance intersection through the Chernoff updater, and OSPA, GOSPA and SIAP
metrics. I'd use it because it's the common language of UK defence tracking
work, and because swapping JPDA for MFA is a one-line change, which makes
ablations honest.

**Q5. How do you fuse a radar and a camera that disagree about confidence?**
A. Calibrate each to an empirical probability per condition bin first, since
their raw scores aren't comparable. In a Bayesian tracker that calibration
shows up as each sensor's P_D and clutter density λ, which set how much a
detection counts. Across sensors that share a failure mode, like EO and IR in
fog, don't treat them as independent: use a correlation discount, or
covariance intersection at track level. Then validate with a dropout ablation:
fused should never be worse than the best single sensor.

**Q6. How would you evaluate a fused tracker?**
A. Three layers. Set-level: GOSPA, because it splits error into localisation,
missed and false. Air-picture: SIAP completeness, ambiguity, spuriousness,
accuracy and track-number changes. Identity: HOTA and IDF1. On top of that,
operational numbers: false alarms per site-hour against the operator budget,
time to alarm with late alarms counted as misses, and the dropout ablation.
Simulation gives exact truth for all of it.

**Q7. What goes wrong with time and registration in real deployments?**
A. Bias, more than noise: 1° of radar north error is 17.5 m at a kilometre,
enough to break every association with the cameras. Time: a drone at 20 m/s
moves 2 m in 100 ms, so stamp at the sensor. SAPIENT makes the UTC timestamp
mandatory for this reason. Use PTP or GNSS-disciplined clocks, and handle
late data as out-of-sequence measurements, by retrodiction or a small reorder
buffer. RTSP camera latency is the usual culprit.

**Q8. What would you add to your simulator to make it useful for [vendor product]-
style fusion?**
A. A radar model with range, bearing and Doppler noise, P_D by RCS and range,
Poisson clutter and birds as hard negatives, plus a SAPIENT protobuf writer
beside the existing ground-truth writers. Then every sensor, including the RF
and audio models that already exist, emits SAPIENT detection reports with
known truth. That gives a conformance and accuracy harness: GOSPA, SIAP and
alarm metrics per condition, and measured per-condition λ and P_D to feed
straight into the tracker.

## Sources fetched this session (2026-09-26)

1. gov.uk, SAPIENT autonomous sensor system guidance, [gov.uk](https://www.gov.uk/guidance/sapient-autonomous-sensor-system)
2. dstl/SAPIENT-Proto-Files: README and `bsi_flex_335_v2_0/*.proto` (sapient_message, registration, status_report, detection_report, task, alert, location), cloned from [GitHub](https://github.com/dstl/SAPIENT-Proto-Files)
3. dstl/Stone-Soup source at commit `e5a3e09` (tracker, dataassociator, hypothesiser/probability, updater/chernoff, metricgenerator), cloned from [GitHub](https://github.com/dstl/Stone-Soup)
4. Stone Soup docs: [design](https://stonesoup.readthedocs.io/en/latest/design.html), [trackers](https://stonesoup.readthedocs.io/en/latest/stonesoup.tracker.html), [data associators](https://stonesoup.readthedocs.io/en/latest/stonesoup.dataassociator.html), [track-to-truth metrics / SIAP](https://stonesoup.readthedocs.io/en/latest/stonesoup.metricgenerator.tracktotruthmetrics.html), [JPDA tutorial](https://stonesoup.readthedocs.io/en/latest/auto_tutorials/08_JPDATutorial.html)
5. Rahmathullah, García-Fernández & Svensson, GOSPA, [arXiv:1601.05585](https://arxiv.org/abs/1601.05585)
6. Vo, Vo & Phung, labelled RFS / δ-GLMB, [arXiv:1312.2372](https://arxiv.org/abs/1312.2372)
7. Antunes et al., MHT library, [arXiv:1106.2263](https://arxiv.org/abs/1106.2263)
8. García-Fernández & Yi, OOSM multi-target tracking, [arXiv:2106.04898](https://arxiv.org/abs/2106.04898)
9. NIST IEEE 1588 page, [nist.gov](https://www.nist.gov/el/intelligent-systems-division-73500/ieee-1588)
10. ONVIF Profile M, [onvif.org](https://www.onvif.org/profiles/profile-m/)

Bibliographic only (DOIs from search listings; the IEEE pages would not load,
and no claim in this file depends on their text beyond what the fetched
sources implement): Fortmann, Bar-Shalom & Scheffe 1983 (JPDA); Reid 1979
(MHT); Vo & Ma 2006 (GM-PHD); Schuhmacher, Vo & Vo 2008 (OSPA).
