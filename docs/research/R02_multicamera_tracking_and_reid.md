# R02 · Multi-Camera Tracking, Cross-View Association, Calibration & Person Re-Identification

*Research dossier for the SurvSim programme (see [`01_RESEARCH_LANDSCAPE.md`](../01_RESEARCH_LANDSCAPE.md) and
[`02_ARCHITECTURE.md`](../02_ARCHITECTURE.md)). Audience: an engineer who must be able to hold their own in a
room with people who have run camera networks for twenty years. Every substantive claim is quoted and linked.
Items marked **[lore]** are practitioner knowledge that the literature does not state; treat them as
hypotheses to validate inside the simulator rather than citations.*

---

## 0. Executive orientation — the five things that actually decide whether MTMC works

1. **Geometry beats appearance.** In every winning multi-camera system of the last five years, the
   appearance model (ReID) is the weak signal and the calibrated ground plane plus time is the strong one.
   The 2024 AI City Challenge Track 1 winner is literally titled *"A Robust Online Multi-Camera People
   Tracking System With Geometric Consistency and State-aware Re-ID Correction"* — Re-ID appears as the
   thing that needs *correcting* by geometry, not the other way round
   ([8th AI City Challenge summary](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Wang_The_8th_AI_City_Challenge_CVPRW_2024_paper.pdf)).
2. **Overlapping and non-overlapping are different sciences.** With overlap you solve a *geometric fusion*
   problem (occupancy on a ground plane, solvable to >90% MODA). Without overlap you solve a *probabilistic
   routing* problem (topology + transit-time priors + appearance), and you are permanently in the regime
   where ReID mAP is the ceiling.
3. **Appearance is not identity.** Standard ReID benchmarks are same-day, same-clothes. Change the clothes
   and accuracy collapses: the reference clothes-changing method CAL scores **55.2% Rank-1 on PRCC** clothes-changing
   (and 40.1% on LTCC) in its own paper ([arXiv 2204.06890](https://arxiv.org/abs/2204.06890), Table 2;
   the 64.1% previously quoted here is a later method's figure from a 2026 survey table) `[audit 2026-09-26]`, against
   ~95% Rank-1 for same-clothes Market-1501. Roughly *a third of the signal you rely on can be removed by a
   jacket*.
4. **Calibration error and clock error are the silent killers.** A ground-plane association threshold of
   0.5 m (the standard MODA tolerance, see §7) is easily blown by 2° of extrinsic error at 30 m, or by 200 ms
   of inter-camera clock skew on a person walking 1.4 m/s. NTP "is accurate under ten milliseconds, while
   PTP is accurate up to less than a microsecond"
   ([Mikrodev, PTP vs NTP](https://www.mikrodev.com/ptp-ieee-1588-vs-ntp-millisecond-precision-time-synchronization-in-industrial-networks-and-scada/)) —
   but almost no deployed CCTV estate runs PTP.
5. **Adversaries are cheap and effective.** A printed pattern on a shirt takes rank-1 matching for a target
   "from 87.9% to 27.1% under Evading Attack"
   ([advPattern, ICCV 2019](https://arxiv.org/abs/1908.09327)). Any product claim about "identifying people"
   must be scoped against deliberate appearance manipulation.

---

## 1. Problem definition and taxonomy

### 1.1 MTSC vs MTMC

* **MTSC (multi-target single-camera)** — detect + track within one view. Output: per-camera tracklets with
  locally unique IDs. Metrics: MOTA/IDF1/HOTA on image coordinates.
* **MTMC / MTMCT (multi-target multi-camera tracking)** — assign *globally consistent* identities to all
  targets across the whole network and the whole time window. Output: a set of trajectories, each a sequence
  of (camera, time, box) plus optionally a world-space path.
* The near-universal pipeline is **detect → MTSC tracklets → ReID embedding per tracklet → cross-camera
  clustering / graph association → global IDs**, optionally with a geometric re-projection step. The 2023
  AI City Track 1 winner is exactly this shape: "The baseline method uses an anchor-guided clustering
  multi-camera people tracking approach without any spatial-temporal re-assignment, which achieves an IDF1
  score of 89.57%", raised to "an IDF1 score of 95.36" by adding *Spatio-Temporal Consistency Re-Assignment*
  ([Anchor-Guided Clustering + STCRA](https://arxiv.org/pdf/2304.09471)).
* Key structural fact: **cross-camera association is a clustering problem over tracklets, not a
  frame-by-frame matching problem.** Tracklet-level embeddings average away pose and blur noise; per-frame
  matching does not. This is why offline/batch MTMC still beats online MTMC, and why AI City awards an
  explicit handicap: "Submissions employing online tracking received a 10% bonus to their HOTA score", with
  the best fully-online system (SJTU-Lenovo) scoring HOTA 67.2175 vs the offline runner-up's 71.9446 (top HOTA; the organisers named the online SJTU-Lenovo entry winner) in the organisers'
  leaderboard (arXiv 2404.09432 Table 1); "77.7258 adjusted" is only the team's own README claim `[audit R4 2026-09-26]`
  ([8th AI City Challenge](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Wang_The_8th_AI_City_Challenge_CVPRW_2024_paper.pdf)).
  Read that number carefully: on a *synthetic, perfectly calibrated, perfectly synchronised* dataset, the
  best online system in the world is at ~78 HOTA. Real estates are worse.

### 1.2 Overlapping FOV — the occupancy-map lineage

When two or more cameras see the same ground patch, you can fuse *before* identity: project features or
detections into a common bird's-eye-view (BEV) / ground-plane grid and detect there. The lineage:

* **POM / KSP (EPFL, 2008)** — the ancestor. Fleuret et al. "shows how to effectively combine a generative
  model with dynamic programming to track up to six individuals across thousands of frames despite
  significant occlusions and lighting changes, using two to four synchronized video streams"
  ([Fleuret et al., PAMI 2008](https://infoscience.epfl.ch/record/145991/files/FleuretBLF08.pdf)). POM
  "estimates the probabilities of occupancy through mean-field inference, naturally handling occlusions" —
  occlusion reasoning falls out of the generative model instead of being patched on.
* **MVDet (ECCV 2020)** — the modern restart: per-view CNN features are warped to the ground plane by a
  homography ("feature perspective transformation") and aggregated by convolutions, and it shipped the
  **MultiviewX** synthetic twin of WILDTRACK
  ([MVDet](https://github.com/hou-yz/MVDet), [paper](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123520001.pdf)).
* **MVDeTr (ACM MM 2021)** — replaces convolutional fusion with a *shadow transformer*: "MVDeTr is a
  multiview detection method that outperforms the previous state-of-the-art by +3.3% MODA on the Wildtrack
  dataset, and +9.8% MODA on the MultiviewX dataset. MVDeTr achieves 91.5% and 93.7% MODA on the two
  datasets respectively" ([MVDeTr](https://github.com/hou-yz/MVDeTr)). The lesson stated in the paper's
  reception: "the importance of jointly considering multiple views during the attention mechanism, rather
  than fusing only at the final layer, is crucial".
* **SHOT / Booster-SHOT** — one homography assumes everyone is a point on the floor; a *stack* of
  homographies at multiple heights approximates the 3D projection. "The Stacked HOmography Transformations
  (SHOT) approach is motivated by approximating projections in 3D world coordinates via a stack of
  homographies, which is empirically verified to be capable of estimating accurate correspondences from
  individual views" ([Booster-SHOT](https://arxiv.org/pdf/2208.09211)). For a surveillance product this
  matters because *the single-homography assumption is exactly what breaks on ramps, stairs and kerbs*.
* **GMVD (WACVW 2023)** — the generalisation wake-up call. "The Generalized Multi-View Detection (GMVD)
  dataset is a new MVD dataset containing diverse non-overlapping scenes within and across training and
  test sets", "curated using Grand Theft Auto V (GTAV) and Unity Game Engine", with "daytime variations
  (morning, afternoon, evening, night) and weather variations (sunny, cloudy, rainy, snowy)" and "seven
  scenes, with six scenes used for training and the last scene with two configurations reserved for
  testing" ([GMVD](https://github.com/jeetv/GMVD),
  [paper](https://openaccess.thecvf.com/content/WACV2023W/RWS/papers/Vora_Bringing_Generalization_to_Deep_Multi-View_Pedestrian_Detection_WACVW_2023_paper.pdf)).
  **This is the single most important prior work for SurvSim's value proposition**: it demonstrates that
  MVD models memorise camera configurations, and that synthetic camera-layout diversity is the fix.
* **EarlyBird (WACVW 2024)** — extends BEV detection to *tracking*: "EarlyBird outperforms the
  state-of-the-art methods and improves the current state-of-the-art on Wildtrack by +4.6 MOTA and +5.6
  IDF1" ([EarlyBird](https://openaccess.thecvf.com/content/WACV2024W/RWS/papers/Teepe_EarlyBird_Early-Fusion_for_Multi-View_Tracking_in_the_Birds_Eye_View_WACVW_2024_paper.pdf)).
  EarlyBird's own Table 1 reports detection MODA 91.2 / recall 96.3 on Wildtrack and MODA 94.2 / recall 95.7 on
  MultiviewX; Table 2 gives Wildtrack tracking IDF1 92.3 / MOTA 89.5 (the "MODA 94% / recall 95.9%" once quoted
  here was a secondary-source conflation) `[audit 2026-09-26]`.
* **TrackTacular** — "Lifting Multi-View Detection and Tracking to the Bird's Eye View", an extension of
  EarlyBird. The paper reports **Wildtrack MOTA 91.8 / IDF1 95.3** and **MultiviewX MOTA 92.4 / IDF1 85.6**
  ([arXiv 2403.12573](https://arxiv.org/html/2403.12573); [code](https://github.com/tteepe/TrackTacular)). The "92.7 / 79.64"
  once quoted here appears nowhere in the paper and has been removed `[audit R3 2026-09-26]`.
* **MVFlow** — adds motion priors: "MVFlow integrates human flow constraints into a deep learning framework
  by developing a weakly supervised approach to predict human flow over time using only detection data on
  the ground plane" (as characterised by
  [MVTrajecter](https://arxiv.org/html/2509.01157)), which also notes that "improvements over MVFlow,
  TrackTacular, and MVTr, which only use motion information for the association, show the benefits of
  utilizing information from multiple past timestamps and incorporating appearance information."
* **Occupancy volumes, not planes** — the current frontier is replacing the ground-plane grid with a 3D
  volume, e.g. "Enhanced Multi-View Pedestrian Detection Using Probabilistic Occupancy Volume"
  ([arXiv 2503.10982](https://arxiv.org/pdf/2503.10982)), and dual 2D/3D geometric constraints
  ([MVDGC](https://arxiv.org/pdf/2607.00273)).

**Engineering read-out:** if your cameras overlap and are calibrated, do *not* start with ReID. Start with
BEV occupancy. MODA in the low 90s at 0.5 m tolerance is achievable; identity then only has to survive
*gaps in coverage*, not every frame.

### 1.3 Non-overlapping FOV — topology, transit times, handover

Without overlap, there is no geometric constraint linking two observations except *reachability in time*.
The classical formulation learns a **camera network topology**: "Camera network topology represents
spatio-temporal relations and connections between cameras, involving inter-camera transition distributions
between two cameras, which denote the transition distributions of objects across cameras according to time
and represent the strength of connectivity between the cameras"
([Distance-based Camera Network Topology Inference](https://arxiv.org/pdf/1712.00158)).

Three things must be learned, and Chen et al. name them exactly: "the topology of a non-overlapping
multi-camera network includes nodes, links, and transition time distributions"
([Learning the Three Factors of a Non-overlapping Multi-camera Network Topology](https://link.springer.com/chapter/10.1007/978-3-642-33506-8_14)) —
i.e. *which cameras exist*, *which pairs are directly reachable*, and *how long the walk takes*. Methods:

* **Cross-correlation of entry/exit events** — unsupervised, no identities needed: correlate departure
  events at camera A's exit zone with arrival events at camera B's entry zone over candidate lags; peaks in
  the correlogram are links. "The network topology can be learned in an unsupervised fashion and
  network-wise reidentification performance improves"
  ([topology inference](https://arxiv.org/pdf/1712.00158)).
* **Joint ReID + topology** — chicken-and-egg solved by alternation: use weak ReID to get candidate
  correspondences, estimate the topology, use the topology to prune ReID candidates, repeat. See
  "Joint Person Re-identification and Camera Network Topology Inference in Multiple Cameras"
  ([arXiv 1710.00983](https://arxiv.org/pdf/1710.00983)) and the
  [unified framework](https://arxiv.org/pdf/1704.07085).
* **Distance-based topology, not time-based** — a subtle but very practical refinement: because people walk
  at different speeds, a fixed transit-time prior is wrong per person. The distance-based method involves
  "calibrating each camera, estimating relative scales between cameras, and using calibration results to
  estimate person speed and infer distances between cameras", so that "the proposed distance-based topology
  can be adaptively applied to each person according to their speed and can handle diverse transition times
  of people between non-overlapping cameras"
  ([Distance-based topology inference](https://arxiv.org/pdf/1712.00158)). **Implement this. A slow elderly
  person and a running courier need different gates on the same edge.**
* **Handover regions** — in practice you define, per camera, an *exit zone* polygon and an *entry zone*
  polygon, plus per-edge (A.exit → B.entry) transit-time distributions. Association candidates are gated by
  (i) edge existence, (ii) transit time within e.g. the 1st–99th percentile of the edge distribution,
  (iii) appearance distance. This is precisely the "camera link model" formalism used by AI City vehicle
  MTMC winners: see
  [Metadata-Aided Re-ID and Trajectory-Based Camera Link Model](https://arxiv.org/pdf/2105.01213).
* **DukeMTMC** was the canonical non-overlapping/partially-overlapping campus benchmark and is **retracted**:
  "The DukeMTMC dataset of videos was taken down in June 2019 due to ethics issues, including lack of consent
  from people in the video and use for surveillance technology", and the authors' apology conceded that data
  collection "had violated IRB guidelines in two respects: Recording outdoors rather than indoors, and making
  the data available without protections"
  ([Mitigating Dataset Harms Requires Stewardship](https://arxiv.org/pdf/2108.02922)). It was nevertheless
  "still used in 135 research papers after it was taken down, at conferences including CVPR and AAAI"
  ([Rachel Thomas summarising the paper](https://x.com/math_rachel/status/1319006175455703040)). For SurvSim
  this is both an ethics lesson and a *market* argument: a synthetic, consent-free replacement for
  DukeMTMC-style benchmarks is a genuine gap.

### 1.4 Spatio-temporal constraints as hard logic

The constraints that buy the most accuracy per line of code:

1. **Mutual exclusion in time** — one identity cannot be in two non-overlapping cameras at the same instant
   (modulo clock skew ε and FOV overlap).
2. **Reachability** — transit time must be ≥ geodesic distance / max walking speed. Use the nav-mesh, not
   Euclidean distance: a fence makes 5 m into 80 m.
3. **Topological consistency of the path** — if A→C requires passing through B's FOV, an A→C match with no
   B observation is suspicious (and is a great *coverage-gap* diagnostic).
4. **Directionality** — exit heading at A should be consistent with entry heading at B (this is where
   infinite-homography / vanishing-point calibration pays off, §2).
5. **Cardinality / counting consistency** — the number of people crossing a line must balance across
   cameras; useful as a global sanity residual.

---

## 2. Calibration in the wild

### 2.1 What "calibration" must actually produce

* **Intrinsics** `K` (fx, fy, cx, cy) + distortion (radial k1..k3, tangential p1,p2, or a fisheye/equidistant
  model). CCTV lenses are wide and cheap: ignoring distortion at the image edge is a metre of ground error.
* **Extrinsics** `[R|t]` per camera in a *single shared world frame*. The shared frame is the deliverable; a
  set of individually-calibrated cameras is worthless for MTMC.
* **Ground-plane homography** `H = K [r1 r2 t]` mapping image points to the Z=0 plane. For people you map
  the **foot point**, not the box centre — this is why WILDTRACK annotates ground-plane positions and why
  MVDet-family methods warp features with foot-plane homographies.
* **Derived artefacts our simulator should emit**: overlap graph, per-cell camera-count map ("each location
  in the scene is covered by 3.74 cameras" in WILDTRACK —
  [MVDet paper](https://arxiv.org/pdf/2007.07247)), blind-spot heatmap, per-edge transit-time truth,
  per-pixel ground resolution (px/m) map.

### 2.2 Tools, and what they are actually good for

* **OpenCV** (`calibrateCamera`, `findChessboardCorners`, `solvePnP`, `findHomography`, `fisheye::*`) — the
  workhorse. Chessboard intrinsics in the lab; `solvePnP` from surveyed ground points on site. In a live
  estate you rarely get to wave a board in front of a 6 m pole camera, so **PnP from 4+ surveyed ground
  landmarks is the realistic field procedure.**
* **COLMAP** — SfM for extrinsics when views share texture: "Infrastructure methods use the sensed
  environment to calibrate a multi-camera system, usually through an existing Structure-from-Motion
  framework, such as COLMAP or a version of SLAM"
  ([CALICO](https://arxiv.org/html/1903.06811v3)). The catch is exactly our case: "Calibration of
  multi-camera systems without overlapping parts is inaccurate"
  ([NMC3D](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11359340/)). Non-overlapping extrinsics usually need
  a map built by a moving agent — "The calibration environment map is constructed by running the SLAM
  algorithm separately for each camera in the multi-camera system in closed-loop motion" (ibid). In the
  field, the equivalent trick is **walk a person or a trolley with RTK GPS / a LiDAR-SLAM backpack through
  the whole estate and register every camera to that trajectory.** [lore]
* **Kalibr** — built for rigid multi-camera + IMU rigs with overlapping views and temporal offsets; the right
  tool for a body-cam/drone rig or a stereo head, the wrong tool for pole-mounted estate cameras. Online
  multi-camera–IMU calibration is an active area ([arXiv 2209.13821](https://arxiv.org/pdf/2209.13821)).

### 2.3 Auto-calibration from pedestrians (the CCTV-native method)

People are calibration targets that arrive for free: approximately constant height, vertical, and walking on
a plane.

* **Vertical vanishing point from head–foot lines**: connect each person's head and foot point; across many
  detections these lines meet at the vertical VP. The horizon/horizontal VP comes from foot-point motion or
  scene lines. Formally, "Three orthogonal vanishing points are computed by extracting head and feet
  positions in their leg-crossing phases"
  ([hierarchical auto-calibration](https://www.sciencedirect.com/science/article/abs/pii/S0957417413006714)) —
  note the detail: the *leg-crossing phase* is when the foot point is least ambiguous. Height priors then fix
  scale.
* **Uneven terrain** is handled by explicitly modelling multiple local planes
  ([Using pedestrians walking on uneven terrains for camera calibration](https://link.springer.com/article/10.1007/s00138-009-0210-2)).
* **Cross-camera extrinsics from pedestrians**: "Researchers automatically estimate vertical and horizontal
  vanishing points by observing pedestrians in each camera and use the corresponding vanishing points to
  estimate the infinite homography existing between the different cameras"
  ([Extrinsic Calibration of Camera Networks Based on Pedestrians](https://www.academia.edu/95066018/Extrinsic_Calibration_of_Camera_Networks_Based_on_Pedestrians)).
  This is *the* method for an estate you cannot survey.
* Why it matters for us: "This process is useful to recover metrics from images or applying information of 3D
  models to estimate 2D pose of targets, making object detection and tracking more robust to noise and
  occlusions. Moreover, the algorithm is independent of the position of the camera, and it is able to work
  with variable pan-tilt-zoom (PTZ) cameras in fully self-adaptive mode"
  ([hierarchical auto-calibration](https://www.sciencedirect.com/science/article/abs/pii/S0957417413006714)).

### 2.4 PTZ: calibration that expires

A PTZ camera's intrinsics change whenever an operator touches it. "PTZ (Pan-Tilt-Zoom) cameras are widely
used in modern surveillance systems, but their zooming ability makes calibration challenging since any
zooming action results in modification of intrinsic parameters, requiring online calibration called
self-calibration" ([survey of PTZ self-calibration](https://www.researchgate.net/publication/338580315_DeepPTZ_Deep_Self-Calibration_for_PTZ_Cameras)).
The practical approach is frame-to-frame homography chaining: "continuously tracks distinctive image feature
points from frame to frame, and from these correspondences robustly calculates the homography transformation
between frames, from which camera internal parameters are then calculated"
([Continuous Localization and Mapping of a PTZ Camera](https://arxiv.org/pdf/1401.6606)).

And the failure mode you must simulate: "Calibration routines are accurate for small PTZ operations, but as
camera orientation changes grow larger, accuracy breaks down, particularly for calculated tilt angles under
large pan angle changes, due to inaccurate homographies, equation inaccuracies, or imprecise PTZ mechanism
movement" — with the mitigation that "Frequent calibrations at a fast rate can improve performance"
([Implementation of Efficient PTZ Camera Calibration](https://apps.dtic.mil/sti/pdfs/ADA497476.pdf)).
Newer work (PTZ-Calib, two-point methods for sports) pushes robustness
([PTZ-Calib](https://www.researchgate.net/publication/395224362_PTZ-Calib_Robust_Pan-Tilt-Zoom_Camera_Calibration),
[two-point method](https://arxiv.org/pdf/1801.09005)).

**SurvSim requirement:** PTZ pose must be exported as *ground truth per frame*, and we should also export a
*deliberately wrong* calibration (with configurable pan/tilt backlash and zoom-encoder error) so that
downstream algorithms can be scored under calibration drift.

### 2.5 Learned single-image calibration

When there is no board, no survey and no PTZ telemetry — e.g. a legacy camera whose mount was bumped:

* **Perspective Fields (CVPR 2023)** — "The approach parameterizes perspective projection by roll, pitch,
  and field of view, and optionally the principal point location", predicting a dense per-pixel field
  where "the Up-vectors aligned with gravity, and Latitude values with 0° on the horizon"
  ([Perspective Fields](https://arxiv.org/pdf/2212.03239)). A pixel-wise field is far more robust in
  cluttered CCTV scenes than regressing four numbers.
* **GeoCalib (ECCV 2024)** — adds a geometric optimisation layer on top: "GeoCalib can robustly predict lens
  distortion from a single image which can be used to rectify images from any source, and estimates more
  accurate distortion than other approaches even when trained only on pinhole images"
  ([GeoCalib](https://github.com/cvg/GeoCalib),
  [paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/05636.pdf)). Its confidence behaviour is
  operationally useful: "The up-vector component is most confident near vertical lines or upright objects like
  trees, while the latitude component is most confident near the horizon" — i.e. expect it to fail on a
  tight, texture-poor corridor view.

### 2.6 Error propagation — the number to burn into your head

Ground-plane error from an angular extrinsic error θ at range R and camera height h scales roughly as
`ΔX ≈ R² · θ / h` for a shallow-looking camera (small-angle, flat-ground approximation). At R = 30 m,
h = 4 m, θ = 1° (0.0175 rad): `ΔX ≈ 900 · 0.0175 / 4 ≈ 3.9 m`. That is **eight times** the 0.5 m MODA
tolerance used by the multi-view benchmarks (§7). Consequences:

* Shallow-mounted, long-range cameras cannot be fused geometrically without very good extrinsics.
* Foot-point detection error acts the same way: a 10 px foot error at 30 m on a 1080p 60° HFOV camera is
  ~0.5 m of ground error on its own. **Occlusion of the feet is a calibration problem, not just a detection
  problem** — which is exactly why SHOT-style multi-height homographies and 3D occupancy volumes exist.
* Therefore: gate cross-camera association with a *range-dependent* spatial threshold, not a constant. [lore]

---

## 3. Person Re-Identification

### 3.1 The classical benchmarks and what they measure

| Dataset | Scale | Note |
|---|---|---|
| **Market-1501** | 1,501 IDs, 6 cameras | The default. Saturated. |
| **DukeMTMC-reID** | 1,404 IDs, 8 cameras | **Retracted**; "A derivative of DukeMTMC—DukeMTMC-ReID, a 'person re-identification benchmark'—has been used in research projects for 'ethically dubious' purposes" ([Mitigating Dataset Harms](https://arxiv.org/pdf/2108.02922)). Do not ship models trained on it. |
| **CUHK03** | 1,467 IDs | Small, two protocols (labelled/detected), noisy. |
| **MSMT17** | 4,101 IDs, 15 cameras, indoor+outdoor, multi-season | The hardest of the "classical" four; introduced with PTGAN ([arXiv 1711.08565](https://arxiv.org/abs/1711.08565)). |
| **Occluded-Duke** | "training set containing 15,618 images of 702 identities, a query set consisting of 2,210 occluded images from 519 identities, and a gallery set containing 17,661 full-body images from 1,110 identities" ([occluded ReID survey](https://link.springer.com/article/10.1007/s00371-026-04699-1)) | The occlusion benchmark. |
| **MARS** | "1,261 different pedestrians and approximately 20,000 video sequences" ([MARS](https://link.springer.com/chapter/10.1007/978-3-319-46466-4_52)) | Video ReID. "On MARS, video-based re-id exceeds image-based re-id by +19.92% in mAP" ([survey](https://arxiv.org/pdf/2110.04764)). |
| **iLIDS-VID** | "acquired by two cameras at the airport and contains 300 pedestrians with 600 tracks totaling 42,495 pedestrian images" ([survey](https://arxiv.org/pdf/2110.04764)) | Small, hard, airport. |

**Metrics:** CMC Rank-k and mAP. For surveillance, *mAP matters more than Rank-1* — an operator wants all
appearances of the suspect, not one.

### 3.2 The model lineage, with numbers

* **BoT / "Bag of Tricks"** — the ResNet-50 baseline that made ReID reproducible (BNNeck, warmup LR, random
  erasing, label smoothing, centre loss). Still the correct first thing to build.
* **OSNet (ICCV 2019)** — the efficiency sweet spot: "a residual block composed of multiple convolutional
  streams, each detecting features at a certain scale" plus "a novel unified aggregation gate to dynamically
  fuse multi-scale features with input-dependent channel-wise weights". "On Market-1501, OSNet reaches a
  Rank-1 accuracy of 94.8% and a mean Average Precision (mAP) of 84.9%", and "Despite its superior
  performance, OSNet is remarkably efficient, containing only 2.2 million parameters, substantially fewer
  than the popular ResNet50-based models" ([OSNet](https://arxiv.org/abs/1905.00953)). **2.2 M parameters is
  why OSNet is the default edge ReID model in real deployments.**
* **TransReID (2021)** — ViT with jigsaw patch modules and side-information (camera/view) embeddings.
* **SOLIDER / PASS** — human-centric self-supervised pretraining, then fine-tune.
* **CLIP-ReID** — language-aligned pretraining with learned ID prompts.
* Head-to-head, from a single comparison table: "On MSMT17, SOLIDER achieved 67.4% mAP with 85.9% R@1,
  TransReID achieved 67.4% mAP with 85.3% R@1, and CLIP-ReID achieved 75.8% mAP with 89.7% R@1. On
  Market-1501, SOLIDER achieved 91.6% mAP with 96.1% R@1, TransReID achieved 88.9% mAP with 95.3% R@1, and
  CLIP-ReID achieved 90.5% mAP with 95.4% R@1"
  ([IUST_PersonReId](https://arxiv.org/html/2412.18874v1)).
* **The generalisation warning in the same paper**: on a new cultural domain (modest attire), "SOLIDER shows
  a drop of 50.75% and 23.01% mAP compared to Market1501 and MSMT17 respectively, while CLIP-ReID exhibits a
  drop of 38.09% and 21.74% mAP, indicating that CLIP-ReID generalizes better to this specialized domain"
  (ibid). Two lessons: **(a) language-aligned pretraining generalises better; (b) a 20–50 point mAP cliff on
  domain shift is normal, not exceptional.**

### 3.3 The cross-domain gap, quantified

Direct transfer is catastrophic. "A baseline model trained on Market1501 ... achieved 92.5% in rank-1
accuracy and 80.8% in mAP on Market1501, but dropped to 30.5% and 16.1% when tested on DukeMTMC-reID,
representing a performance gap of more than 55%"
([Bridging the Source-to-target Gap](https://arxiv.org/pdf/2203.01682)). More generally, "domain gap
commonly exists between datasets, which essentially causes severe performance drop when training and testing
on different datasets" (ibid).

**Unsupervised / UDA ReID** is therefore not academic hygiene, it is the deployment path — you will have
unlabelled video from the customer's own cameras. State of the art is clustering + contrastive memory:

* **Cluster Contrast (ACCV 2022)** — "stores feature vectors and computes contrast loss at the cluster
  level, employing a unique cluster representation to describe each cluster", improving "9.9%, 8.3%, 12.1%
  compared to state-of-the-art purely unsupervised re-ID methods" on Market, Duke, MSMT17
  ([Cluster Contrast](https://arxiv.org/abs/2103.11568)).
* (An "ACR 49.0 mAP / 74.2 R1 on MSMT17" figure formerly cited here came from arXiv 2112.01839, which its author has **withdrawn** ("experimental results are not sufficient"); it is removed and must not be cited `[audit R3 2026-09-26]`.)
* Read the absolute number: **Cluster Contrast reaches 33.0 mAP / 62.0 R1 on MSMT17 purely unsupervised
  (camera-aware PPLR: 42.2 / 73.3; Cluster Contrast Table, arXiv 2103.11568) vs ~76 supervised** `[audit R3 2026-09-26; replaces the withdrawn ACR ~49]`. Unsupervised adaptation
  recovers roughly half the gap. Plan capacity accordingly.

### 3.4 Clothes-changing and long-term ReID — where surveillance actually lives

The core claim of the field, stated plainly: standard ReID assumes clothing is constant, which is false over
days and false within hours for anyone who wants to evade.

**Datasets:**

| Dataset | Statistics (quoted) |
|---|---|
| **PRCC** | "PRCC containing 33,698 images of 221 identities with two distinct clothing sets" ([CC-ReID study](https://www.sciencedirect.com/science/article/abs/pii/S0167865526001352)) |
| **LTCC** | "LTCC including 17,119 images of 152 identities with an average of 3.1 clothing variations per identity" (ibid) |
| **VC-Clothes** | "VC-Clothes has 512 identities, 4 scenes (cameras) and on average 9 images/scene for each identity and a total number of 19,060 images ... a synthetic CC-ReID dataset rendered by the GTA5 game engine. Each identity wears 1-3 different outfits" ([When Person Re-identification Meets Changing Clothes](https://arxiv.org/pdf/2003.04070)) |
| **Celeb-reID** | "There are 34,186 images with 1,052 IDs, and the probability of clothing change for a person is 70% on average"; Celeb-reID-light "contains 10,842 images of 590 identities" where "all images of each person are in different clothes" ([Celeb-reID line](https://arxiv.org/pdf/2208.12023)) |
| **DeepChange** | "178,407 images of 1,121 identities from 17 cameras and only includes the recording date without clothing labels", covering "a period of 12 months with a wide variety of different weathers and contexts, presenting the longest time duration among all re-id datasets with natural/native personal appearance variations" ([DeepChange](https://arxiv.org/abs/2105.14685)) |
| **LaST** | "collected from more than 2,000 movies in 8 countries, containing 10,862 identities and 228,156 images" ([as summarised in CC-ReID work](https://arxiv.org/html/2202.03087v3)) |
| **CCVID** | video CC-ReID benchmark introduced with CAL ([Gu et al., CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/papers/Gu_Clothes-Changing_Person_Re-Identification_With_RGB_Modality_Only_CVPR_2022_paper.pdf)) |

Note **VC-Clothes is synthetic (GTA5)** and is a standard CC-ReID benchmark. That is direct precedent for
SurvSim's appearance-mutation feature being scientifically acceptable, not a toy.

**Methods:**

* **CAL — Clothes-based Adversarial Loss (CVPR 2022)** — the reference baseline: mine clothes-irrelevant
  features from RGB only by adversarially penalising clothes-predictability. Reported in the CAL paper (Table 2): PRCC clothes-changing **55.2% Rank-1 / 55.8% mAP**, same-clothes
  100/99.8 (the "64.1%" once quoted here from a [2026 survey](https://www.sciencedirect.com/science/article/abs/pii/S0167865526001352)
  is not CAL's own number) `[audit 2026-09-26]`; on LTCC,
  CAL is quoted at "20.3% mAP and 31.6% Rank1"
  ([3DInvarReID comparison](https://arxiv.org/pdf/2308.10658)) — a re-run under 3DInvarReID's protocol; the CAL
  paper itself reports **40.1% Rank-1 / 18.0% mAP** clothes-changing on LTCC
  ([arXiv 2204.06890](https://arxiv.org/abs/2204.06890), Table 2) `[audit 2026-09-26]`.
* **3D shape / clothing-invariant 3D representation** — "3DInvarReID addresses challenges in long-term person
  re-identification by disentangling identity from pose and clothing and leveraging 3D body shapes for
  discriminative feature learning", reporting "20.1% mAP and 34.6% Rank1 accuracy" on LTCC
  ([3DInvarReID, ICCV 2023](https://github.com/liufeng2915/3DInvarReID)).
* **Gait / silhouette / skeleton** — "Cloth-Changing Person Re-identification from A Single Image with Gait
  Prediction and Regularization" ([arXiv 2103.15537](https://arxiv.org/pdf/2103.15537)) and skeleton-dynamics
  approaches ([arXiv 2503.10759](https://arxiv.org/pdf/2503.10759)).
* **Semantic/parsing consistency** ([SCNet](https://arxiv.org/pdf/2308.14113)), **hard-sample generation**
  ([Try Harder](https://arxiv.org/pdf/2507.11119)), **prompt learning**
  ([MIPL](https://arxiv.org/html/2411.00330v1)), **pose+clothing augmentation**
  ([CCPA](https://arxiv.org/pdf/2402.14454)), **instance-adaptive low-rank orthogonal subspaces**
  ([arXiv 2606.11661](https://arxiv.org/pdf/2606.11661)).
* **Unsupervised long-term ReID with clothes change** exists too
  ([arXiv 2202.03087](https://arxiv.org/html/2202.03087v3)) — important because nobody will hand-label clothes
  changes in a customer's estate.

**The headline you should quote in any product review: LTCC clothes-changing Rank-1 is ~40 % (CAL: 40.1 R1 / 18.0 mAP)
and mAP is below ~25 %.** (Earlier text said "Rank-1 in the 30s"; that used a third-party re-run of CAL.) In the clothes-changing regime, ReID is a *shortlisting* tool, not an identification tool.

### 3.5 Gait as the clothing-invariant fallback

* **OpenGait / GaitBase** — the community's mmdetection moment: "OpenGait is a unified and consolidated
  platform that facilitates a comprehensive study of gait recognition methods", and "has been widely adopted
  in two major international gait recognition competitions, HID and GREW, with all top-10 winning teams at
  HID2022 and 2023 choosing OpenGait as the codebase"
  ([OpenGait](https://arxiv.org/pdf/2405.09138)).
* **The in-the-wild collapse**: "While models exhibit near 90% Rank-1 accuracy on the CASIA-B and OU-MVLP
  datasets, their performance declines to approximately 50% on the GREW dataset, highlighting the challenges
  of real-world gait recognition" (ibid). Constrained-lab gait numbers are *marketing*; GREW/Gait3D numbers
  are engineering.
* Current in-the-wild progress: MultiGait++ "raises the state-of-the-art standard by +7.6% and +4.9% in
  rank-1 accuracy on GREW and Gait3D", and on CCPG (the clothes-changing gait benchmark) improves "+4.8%,
  +4.2%, +4.3%, and +1.6% in rank-1 accuracy on the CL, UP, DN, and BG subsets"
  ([MultiGait++](https://arxiv.org/pdf/2412.11495)).
* **RealGait** makes the bridge explicit — gait recognition evaluated *as* ReID on real surveillance tracklets
  ([arXiv 2201.04806](https://arxiv.org/pdf/2201.04806)).
* Practical constraint set for gait: needs a clear walking sequence (≥ ~1 gait cycle, i.e. ~1 s at 1.4 m/s),
  a reasonably side-on view, a clean silhouette (so bad background subtraction or heavy crowding kills it),
  and no carried-object / clothing confound. All four are simulator-controllable variables. [lore]

### 3.6 Face + body fusion, and the long-range regime

The most credible "identify people in CCTV" programme is IARPA **BRIAR**: "The BRIAR program began in
November 2021, with the goal of developing software algorithm-based systems capable of performing whole-body
biometric identification at long-range and from elevated platforms"
([IARPA BRIAR](https://www.iarpa.gov/research-programs/briar)). The dataset: "BRIAR consists of over 350,000
images and 1,300 hours of videos from 1,055 subjects in outdoor settings", "rich with imagery captured from
UAVs, providing data that include different angles, poses, and motion states of subjects"
([covariate analysis](https://arxiv.org/abs/2409.01514)).

Fusion works, and the deltas are large: FarSight "achieves a 34.1% absolute gain in 1:1 verification accuracy
(TAR@0.1% FAR), a 17.8% increase in closed-set identification (Rank-20), and a 34.3% reduction in open-set
identification errors (FNIR@1% FPIR)" ([FarSight, arXiv 2505.04616](https://arxiv.org/abs/2505.04616) — these gains are the 2025 system *versus the preliminary 2023 FarSight* ([2306.17206](https://arxiv.org/pdf/2306.17206)), not fusion versus a single modality) `[audit 2026-09-26]`; see also
"Person Recognition at Altitude and Range: Fusion of Face, Body Shape and Gait"
([arXiv 2505.04616](https://arxiv.org/pdf/2505.04616)) and the aerial-surveillance decade survey
([arXiv 2511.17674](https://arxiv.org/pdf/2511.17674)).

**Design implication for SurvSim:** we must ship *face-visible* and *face-pixel-height* ground truth per
frame per camera (already in the architecture's GT spec) so a fusion policy can be *learned and evaluated*:
use face when IED is sufficient, body/gait otherwise.

### 3.7 Attributes, text queries, groups

* **Attributes** — the operator-friendly middle layer. PETA "consists of 19,000 person images with 61 binary
  attributes and 4 multi-class attributes"; "PA100K dataset is the largest pedestrian attribute recognition
  dataset, which contains 100,000 pedestrian images and 26 binary attributes"
  ([PAR survey material](https://arxiv.org/pdf/2509.22331)). Recent numbers: "PETA: One method achieves 88.50
  mA, 83.27 accuracy ..."; "PA-100K: Another approach reaches 87.95 mA, 84.01 accuracy" (ibid). mA in the high
  80s sounds good until you realise per-attribute recall on rare attributes (e.g. "carrying a knife-like
  object") is far lower — **always report per-attribute, never mA, in a security context.** [lore]
* **Text-based person search** — "find the man in a red jacket with a black backpack". CUHK-PEDES and
  RSTPReid are the benchmarks (ROGLE 76.93 / 65.20 confirmed in [arXiv 2606.01825v1 html](https://arxiv.org/html/2606.01825v1) `[audit R4 2026-09-26]`). "ROGLE achieves 76.93% Rank-1 accuracy on CUHK-PEDES" and "65.20% Rank-1
  accuracy on RSTPReid, significantly higher than previous methods such as IVT (51.7%) and Cfine (55.55%)"
  ([ROGLE](https://arxiv.org/pdf/2606.01825)). ~65–77% Rank-1 means a text query is a *triage* tool:
  excellent for cutting 10,000 tracklets to 50, useless as evidence.
* **Group ReID** — people move in groups; the group is a stronger and more clothes-robust signature than any
  individual in it, and group membership is a powerful association prior across non-overlapping cameras.
  Literature is thinner than individual ReID (searches for occluded ReID surface little group work —
  [occluded survey](https://link.springer.com/article/10.1007/s00371-026-04699-1)), which makes
  **group-consistent cross-camera association an exploitable gap for us**, and our simulator already models
  `group_id` and split/merge events.
* **Multi-modal / instruction-driven ReID is the 2025–26 direction**: "Instruct-ReID++ (He et al., 2025) aims
  to handle multiple Re-ID scenarios within a single model including image-based, text-based,
  visible-infrared, and clothes-changing tasks"
  ([as summarised here](https://arxiv.org/pdf/2606.16161)); VP-ReID offers "257,310 multi-modal queries and
  gallery images, covering ten diverse person ReID tasks"
  ([Find Them All](https://arxiv.org/html/2508.06908)); ReID5o/ORBench covers "5 modalities for 1,000
  identities" ([ReID5o](https://arxiv.org/html/2506.09385v1)). And the sober 2026 finding:
  "Language-aligned models show surprising robustness cross-domain for ReID tasks, even though they are not
  explicitly trained to do so" ([Person Re-ID in 2025](https://arxiv.org/pdf/2601.20598)).

---

## 4. Adversarial identity: disguise, evasion and deliberate appearance change

This section is the difference between a demo and a security product. Assume the subject knows the system
exists.

### 4.1 Attacking the detector (if you are never detected, you are never tracked)

* **Adversarial YOLO / "Fooling Automated Surveillance Cameras" (CVPRW 2019)** — "Adversarial YOLO is the
  first method to perform physical adversarial attacks on the person detection task, creating a small
  (40 cm × 40 cm) adversarial patch that can fool the one-stage detector YOLOv2"
  ([Thys et al.](https://openaccess.thecvf.com/content_CVPRW_2019/papers/CV-COPS/Thys_Fooling_Automated_Surveillance_Cameras_Adversarial_Patches_to_Attack_Person_Detection_CVPRW_2019_paper.pdf)).
  A cardboard sign. That is the attack cost.
* **Invisibility Cloak (ECCV 2020)** — wearable version: "The proposed method generates an adversarial patch
  and prints it on real clothes to make a three dimensional invisible cloak, allowing anyone wearing it to
  evade the detection of person detectors and achieve stealth"
  ([Making an Invisibility Cloak](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123490001.pdf)).
* **Adversarial T-shirt** — the deformation problem solved: it "uses a TPS-based transformer to model the
  temporal deformation of a T-shirt caused by pose changes of a moving person, ensuring attack effectiveness
  in the physical world" ([as described in the physical-attack survey](https://arxiv.org/pdf/2305.01074)).
* **Reported effectiveness**: "The attack success rate of the generated adversarial patch in digital domain
  (Inria dataset) is 86.56% against YOLO v2 and 80.32% against YOLO v5"; and in simulation, "adversarial
  patches mapped on the body of 3D human models can reduce the detection accuracy from 100% to 17% using 8
  patches" ([3D Invisible Cloak](https://arxiv.org/pdf/2011.13705)).
* **Note the synthetic-evaluation precedent**: 3D Invisible Cloak evaluates attacks "In virtual scenes using
  3DS Max". A UE5 pipeline with controllable garment textures is a *better* version of that experiment, and
  it is a product feature we can sell as red-teaming.

### 4.2 Attacking ReID

* **advPattern (ICCV 2019)** — the canonical physical attack on ReID. Two threat models: evasion ("don't
  match me to myself") and impersonation ("match me to someone else"). Numbers: "The rank-1 accuracy of
  re-ID models for matching the adversary decreases from 87.9% to 27.1% under Evading Attack", with "an
  average rank-1 accuracy drop of 74.3% and an average mAP drop of 61.1% across 14 different physical testing
  points"; and "The adversary can impersonate a target person with 47.1% rank-1 accuracy and 67.9% mAP under
  Impersonation Attack" ([advPattern](https://arxiv.org/abs/1908.09327)).
  **Impersonation is the under-appreciated risk**: it produces confidently wrong identity assignments, i.e.
  false accusations, not just misses.
* **Digital attacks (Deep Mis-Ranking, CVPR 2020)** — "highly effective across a wide range of
  state-of-the-art ReID systems, consistently reducing their rank-1 accuracy to near zero, often below 3.9%
  on Market1501 and even lower on CUHK03"
  ([Deep Mis-Ranking](https://arxiv.org/html/2004.04199v1)).
* **Detection of attacks** is possible via context inconsistency — "Multi-Expert Adversarial Attack Detection
  in Person Re-identification Using Context Inconsistency"
  ([arXiv 2108.09891](https://arxiv.org/pdf/2108.09891)) — a good SurvSim eval task: can a system flag "this
  match is adversarial" rather than silently matching?

### 4.3 Attacking gait

* **Traditional spoofing** needs no technology: "Traditional spoofing attacks to gait recognition systems were
  attempted by trained impostors, notably with similar body shapes and clothes, imitating the walking styles
  of target subjects. It was shown that it was indeed possible to spoof gait biometric systems by clothing
  impersonation and the deliberate selection of a target that has a similar build to the attacker"
  ([gait spoofing survey material](https://pmc.ncbi.nlm.nih.gov/articles/PMC13365055/)).
* **Adversarial silhouettes**: models "are vulnerable to adversarial attacks by adding adversarial silhouettes
  in video sequences computed using Generative Adversarial Networks"
  ([Attacking Gait Recognition Systems via Silhouette Guided GANs](https://dl.acm.org/doi/10.1145/3343031.3351018)),
  plus temporally sparse attacks ([arXiv 2002.09674](https://arxiv.org/pdf/2002.09674)) and latent-space
  perturbation studies ([Scientific Reports 2025](https://www.nature.com/articles/s41598-025-22869-4)).
* **The cheapest real-world gait attack is behavioural**: "An adversary attempts to fool the system by actively
  modifying their natural silhouette, usually through clever clothing changes or the addition of carried
  objects" (ibid). A long coat, a rucksack, a limp, or a phone held to the ear will do it.
* Presentation-attack detection for gait now exists (GaitSpoofNet,
  [Frontiers 2026](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1821341/full)),
  which means "liveness/spoof detection for gait" is a scorable task we can generate data for.

### 4.4 Camera-aware evasion — the attack nobody benchmarks

Neither the detector-attack nor ReID-attack literature covers what an experienced offender actually does:

* Walk timing tuned to PTZ patrol cycles (present only while the camera looks elsewhere).
* Path planning through the blind-spot graph — staying in the complement of the coverage map.
* Hooding/masking only inside FOVs, uncovering in gaps (breaks appearance continuity *and* face capture).
* Clothing layer swaps executed inside a coverage gap (the "outfit swap in the stairwell" pattern).
* Handing a distinctive bag to an accomplice mid-route (breaks accessory-based ReID and group ReID at once).
* Walking behind/among a group so the detector only fires on the group.

**This is the strongest research argument for SurvSim.** No public dataset contains ground-truthed,
deliberately camera-aware adversarial behaviour with known identity. Our `adversarial` person fields
(`camera_awareness`, `face_hiding`, `avoid_zones`, `timing_gaps_cameras`) plus `change_events` make this
benchmarkable for the first time. [lore, but grounded in the coverage-map and PTZ-drift literature above]

---

## 5. Face recognition in CCTV: what is physically possible, and what is legally allowed

### 5.1 Resolution is the binding constraint

Inter-eye distance (IED) is the standard yardstick, and the recommendations span a factor of ten:

* "There is a recommendation of at least 64 pixels between a subject's two eyes"; "Under ideal circumstances,
  images/videos with at least 160 pixels between the eyes should be used"; "ISO/IEC standards suggest
  preferring an IED of 120 pixels or more as best practice for frontal image type, with specifications
  requiring at least 90 pixels"; "32 pixels is the recommended minimal distance between eyes for reliable
  face template extraction"; "Currently available face recognition systems usually require face images with
  more than 50 pixels between the eyes"
  ([synthesised from face-quality standards and vendor guidance](https://arxiv.org/pdf/2211.08030),
  [Kairos best practices](https://face.kairos.com/docs/api/best-practices),
  [iOmniscient FAQ](https://iomni.ai/faq/what-is-the-pixel-numbers-needed-for-face-detection/)).
* Hard floor: "Face images with a tight bounding box smaller than 32×32 pixels begin to present significant
  accuracy challenges to face recognition systems. However, some works mention that the minimal resolution
  that allows identification is 16×16"
  ([Face Recognition in Low Quality Images: A Survey](https://arxiv.org/pdf/1805.11519)).
* Classic quantification of the fall-off:
  [Boom et al., "The Effect of Image Resolution on the Performance of a Face Recognition System"](https://ris.utwente.nl/ws/files/5328208/Boom06effect.pdf),
  and the observation that "performance continuing to degrade when resolution decreased in surveillance
  scenarios".

**Do the arithmetic for your estate.** A 1080p camera with 60° HFOV gives ~32 px/degree. A face at 20 m
subtends about 0.5° between the eyes (≈6 cm IED), i.e. **~16 px IED — an order of magnitude below the ISO
recommendation**. Conclusion: *general CCTV at standoff is a body/gait problem, and face recognition only
works at chokepoints (doors, turnstiles, gates) with dedicated, well-lit, near-frontal cameras.* SurvSim
should emit face IED per frame so this can be reasoned about numerically rather than rhetorically.

### 5.2 Pose, illumination, motion, compression

The other covariates compound multiplicatively: yaw beyond ~30–45°, top-down mounting (the standard CCTV
mount produces exactly the worst pitch), backlit doorways, IR-mode monochrome with different skin
reflectance, motion blur at 1/25 s exposure, and H.264 at low bitrate destroying exactly the
high-frequency periocular detail recognition depends on. BRIAR's covariate analysis exists precisely because
these interact
([covariate analysis of BRIAR](https://arxiv.org/abs/2409.01514)).

### 5.3 NIST: the ground truth on accuracy and on demographics

* NIST's evaluation has been restructured: "What was formerly known as FRVT has been rebranded and split into
  FRTE (Face Recognition Technology Evaluation) and FATE (Face Analysis Technology Evaluation), with tracks
  that pertain to identity verification running under FRTE"
  ([NIST FRTE 1:1](https://pages.nist.gov/frvt/html/frvt11.html);
  programme page: [NIST FRVT](https://www.nist.gov/programs-projects/face-recognition-vendor-test-frvt)).
* Demographics are tracked separately and continuously: "The FRTE 1:1 Demographic Differentials table ...
  includes summary indicators for how error rates vary by age, sex, and race. These cover false negative
  demographic effects (failures to associate two photos of an individual) and false positive demographic
  effects (incorrect association of two photos of different individuals)"
  ([FRTE Demographics](https://pages.nist.gov/frvt/html/frvt_demographics.html)).
* Scale of the evidence base: NIST FRTE data covers "1,368 algorithms from 420 developers (2017–2026)", and
  an independent analysis of "NIST's 2024–2025 submissions shows that the demographic differential pattern
  appears in >95% of evaluated algorithms across this period"
  ([NIST FRTE bias visualisations](https://github.com/DrMarioDeSean411-arch/nist-frte-facial-recognition-bias)).
* The two-sided framing you must be able to give: top algorithms are extraordinarily accurate on
  well-posed images and far less so on non-ideal ones; see the policy-side summary at
  [Bipartisan Policy Center, "Face Recognition Technology Accuracy and Performance"](https://bipartisanpolicy.org/article/frt-accuracy-performance/).
  **False-positive differentials matter more than false-negative ones operationally**, because a false
  positive puts an innocent person in front of a police officer.

### 5.4 Law: UK and EU

**Bridges v South Wales Police (UK Court of Appeal, 11 August 2020)** — the first appellate judgment anywhere
on police AFR:

* "On 11 August 2020, the Court of Appeal handed down a judgment in R (Bridges) v Chief Constable of South
  Wales Police, finding there to be three ways in which the South Wales Police's use of LAFR technology was
  unlawful" ([Ada Lovelace Institute](https://www.adalovelaceinstitute.org/blog/facial-recognition-technology-needs-proper-regulation/)).
* "The Court of Appeal said that the interference resulting from the use of the AFT was not 'in accordance
  with law' as required by Article 8(2) of the Convention", and "The judges ruled there was no clear guidance
  on where AFR Locate could be used and who could be put on a watchlist, and that 'too much discretion is
  currently left to individual police officers'"
  ([Inforrm case note](https://inforrm.org/2020/08/17/case-law-r-on-the-application-of-bridges-v-chief-constable-of-south-wales-police-use-of-automatic-facial-recognition-technology-unlawful-hugh-tomlinson-qc/);
  see also [Hunton](https://www.hunton.com/privacy-and-information-security-law/uk-court-of-appeal-finds-automated-facial-recognition-technology-unlawful-in-bridges-v-south-wales-police),
  [Liberty](https://www.libertyhumanrights.org.uk/issue/legal-challenge-ed-bridges-v-south-wales-police/)).
* Crucially, the court did *not* ban AFR — it found the *framework* inadequate, including a failure under the
  Public Sector Equality Duty to satisfy itself about demographic bias. **The engineering consequence: a
  deployable system must ship watchlist-governance controls, deployment-scope logging, DPIA/EqIA artefacts and
  bias-test evidence as product features.**

**Met Police LFR, current operational data** (useful because it is the most-quoted real-world numbers):

* "Between September 2024 and 2025, more than 1,400 arrests were linked to live facial recognition (LFR) use,
  with 962 arrests made during that specific period", and "The technology was deployed more than 200 times
  across London boroughs" ([Biometric Update](https://www.biometricupdate.com/202511/metropolitan-police-to-expand-live-facial-recognition-use-even-amid-legal-challenge)).
* "The Met maintains that the false alert rate remains low, standing at 0.0003 percent from over three million
  scans. More specifically, from 203 deployments, LFR cameras triggered 2,077 alerts with 10 false positives"
  (ibid).
* "The report acknowledged that 10 individuals were falsely flagged by the system, eight of whom were Black.
  While none were arrested, six were briefly stopped by officers" (ibid; see also
  [The Register](https://www.theregister.com/2025/11/03/metropolitan_police_hails_facial_recognition/) and
  the critical view from [Big Brother Watch coverage](https://www.theregister.com/2025/07/09/big_brother_watch_met_lfr/)).
  the operationally meaningful figure is false positives per *alert* (10/2,077 ≈ 0.5%) and per *deployment*
  (10/203 ≈ 1 every 20 deployments). And 8 of 10 false alerts affecting Black individuals, on a sample of 10,
  is statistically thin but exactly the pattern NIST's demographic tables predict. Never let a vendor quote
  you a per-scan rate.

**EU AI Act, Article 5** — "Article 5 of the Act prohibits placing on the market or into service AI systems
for real-time remote biometric identification in publicly accessible spaces for law enforcement purposes",
with prohibitions enforceable "in February 2025, with fines of up to €35 million or 7% of global annual
turnover" ([Article 5 analysis](https://securityboulevard.com/2026/04/article-5-and-the-eu-ai-acts-absolute-red-lines-firetail-blog/);
primary text: [artificialintelligenceact.eu Article 5](https://artificialintelligenceact.eu/article/5/)).
Exceptions are narrow: "targeted search for victims of abduction, trafficking, sexual exploitation, or missing
persons; prevention of a specific, substantial, imminent threat to life or physical safety, including
terrorism; and identification of a suspect of certain serious offences (those punishable by at least four
years' custody)", and even then "Article 5(2) imposes strict procedural conditions: prior judicial or
independent administrative authorisation, fundamental rights impact assessment, geographic and temporal
limits, notification to market surveillance and data protection authorities, and registration in the EU
database" ([FPF analysis](https://fpf.org/blog/red-lines-under-the-eu-ai-act-restricting-real-time-remote-biometric-identification-systems-for-law-enforcement-purposes/)).
Note the scoping that decides product strategy: "The prohibition applies only to law enforcement. This
prohibition does not apply to private actors in non-law-enforcement contexts" (ibid) — *and* note that
**tracking/ReID without biometric identification is a different, high-risk-but-permitted category**, which is
precisely why an appearance-and-geometry MTMC product is more legally tractable in the EU than a face-matching
one.

---

## 6. Datasets and benchmarks — the table to memorise

| Benchmark | Type | Key statistics (quoted) |
|---|---|---|
| **WILDTRACK** | Overlapping, real, outdoor | "400 synchronized frames from 7 cameras, covering a 12 meters by 36 meters region ... 1080 × 1920 resolution, and are annotated at 2 frames per second"; "the ground plane is quantized into a 480 × 1440 grid, where each grid cell is a 2.5-centimeter square ... over 40,000 bounding boxes ... more than 300 individuals"; "On average, there are 20 persons per frame ... each location in the scene is covered by 3.74 cameras" ([MVDet paper](https://arxiv.org/pdf/2007.07247), [WILDTRACK](https://infoscience.epfl.ch/record/256268)) |
| **MultiviewX** | Overlapping, synthetic (Unity) | "built in a virtual environment with six calibrated cameras and 400 frames" ([EarlyBird](https://arxiv.org/html/2310.13350)) |
| **GMVD** | Overlapping, synthetic, generalisation | "seven scenes, with six scenes used for training and the last scene with two configurations reserved for testing", GTA V + Unity, day/weather variation ([GMVD](https://github.com/jeetv/GMVD)) |
| **EPFL (Terrace/Passageway/Laboratory/Campus/Basketball)** | Overlapping, real, small | "five sequences ... each sequence consisting of three or four different views filming 6-11 pedestrians, shot at 25 FPS with a resolution of 360 × 288" ([as tabulated in DIVOTrack](https://arxiv.org/pdf/2302.07676)) |
| **CAMPUS** | Overlapping, real | "four sequences including two gardens, one parking lot, and one auditorium, shot by four 1080P cameras with videos lasting three to four minutes at 30 FPS" (ibid) |
| **PETS2009** | Overlapping, real, crowd | "PETS2009 was an early dataset that sparked the development of tracking datasets, though relatively small in scale" (ibid) |
| **MMPTRACK** | Overlapping, real, indoor, large | "more than 9.6 hours of videos were collected, covering 28 subjects in five representative environments: Retail, Lobby, Industry, Cafe, and Office"; "the number of cameras varies from four to six"; "densely labeled with the help of RGBD cameras and verified and corrected by human labelers"; "over half a million frame-wise annotations for each camera view" ([MMPTRACK, WACV 2023](https://openaccess.thecvf.com/content/WACV2023/papers/Han_MMPTRACK_Large-Scale_Densely_Annotated_Multi-Camera_Multiple_People_Tracking_Benchmark_WACV_2023_paper.pdf), [challenge page](https://iccv2021-mmp.github.io/subpage/dataset.html)) |
| **DIVOTrack** | Cross-view, **moving** cameras | "1,690 single-view tracks and 953 cross-view tracks, both of which are significantly larger than the previous cross-view multi-object tracking datasets"; "10 scenes captured by 3 moving cameras" ([DIVOTrack, IJCV 2024](https://github.com/shengyuhao/DIVOTrack)) |
| **DukeMTMC / DukeMTMC-reID** | Non-overlapping campus | **Retracted** (see §1.3). |
| **AI City Challenge Track 1** | MTMC people, real + synthetic | 2023: real warehouse + "synthetic data built using the NVIDIA Omniverse Platform" ([2023 tracks](https://www.aicitychallenge.org/2023-challenge-tracks/)); 2024: "the number of cameras increased from 129 to approximately 1,300, and the number of people tracked rising from 156 to around 3,400", metric "updated to the Higher Order Tracking Accuracy (HOTA) based on 3D distance" ([8th AI City Challenge](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Wang_The_8th_AI_City_Challenge_CVPRW_2024_paper.pdf)) |
| **Synthehicle** | MTMC vehicles, synthetic (CARLA) | "17 hours of labeled video material, recorded from 340 cameras in 64 diverse day, rain, dawn, and night scenes, making it the most extensive dataset for multi-target multi-camera tracking so far"; "a varying number of cameras (3 to 8) in each scene"; "1920 × 1080 px and a frame rate of 10 fps"; "perfect labels for 3D bounding boxes in camera- and world coordinates, depth estimation, and instance, semantic and panoptic segmentation" ([Synthehicle](https://github.com/fubel/synthehicle), [paper](https://arxiv.org/abs/2208.14167)) |
| **SoccerNet-Tracking / SoccerTrack v2** | Multi-view sport | [SoccerNet 2023 challenge results](https://arxiv.org/pdf/2309.06006), [SoccerNet 2024](https://arxiv.org/pdf/2409.10587), [SoccerTrack v2 full-pitch multi-view](https://arxiv.org/pdf/2508.01802); useful because occlusion + identical uniforms is the pure "appearance is useless" stress test. |
| **MATRIX** | Multi-drone multi-view, UE5 | "A Multi-Drone Multi-View Dataset and Deep Learning Framework for Pedestrian Detection and Tracking" ([arXiv 2511.08615](https://arxiv.org/html/2511.08615)) |

### 6.1 AI City MTMC winning recipes (quote-level detail)

* **2023 Track 1, 1st place**: "The first-place winner achieved an IDF1 score of 95.36, IDP score of 95.83,
  and IDR score of 94.88, ranking first among 27 teams", using anchor-guided clustering plus
  "Spatio-Temporal Consistency Re-Assignment (STCRA) and iterative refinement techniques (i-STCRA)"
  ([arXiv 2304.09471](https://arxiv.org/pdf/2304.09471)); 2nd place "achieved an IDF1 of 94.17%" with a
  "Mixture of Realistic and Synthetic Knowledge" ReID training strategy
  ([repo](https://github.com/nguyenquivinhquang/Multi-camera-People-Tracking-With-Mixture-of-Realistic-and-Synthetic-Knowledge)).
  **Read the 2nd-place title again: mixing synthetic with real ReID training data won a medal. That is our
  thesis, already validated.**
* **2024 Track 1, official winner per the organisers' winners page but 2nd by raw HOTA (67.2175 vs Yachiyo 71.9446; winner rule favours online + on-time paper)** `[audit R4 2026-09-26]`: "A Robust Online Multi-Camera People Tracking System With Geometric Consistency
  and State-aware Re-ID Correction", "a fully online method ... qualified for a 10% bonus, with an adjusted
  HOTA score of 77.7258" [team claim, PoseTrack README — not in the organisers' table]
  ([8th AI City Challenge](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Wang_The_8th_AI_City_Challenge_CVPRW_2024_paper.pdf)).
  Other 2024 entries worth reading as engineering templates: "Overlap Suppression Clustering for Offline
  Multi-Camera People Tracking"
  ([Yoshida et al.](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Yoshida_Overlap_Suppression_Clustering__for_Offline_Multi-Camera_People_Tracking_CVPRW_2024_paper.pdf))
  and "Cluster Self-Refinement for Enhanced Online Multi-Camera People Tracking"
  ([Kim et al.](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Kim_Cluster_Self-Refinement_for_Enhanced_Online_Multi-Camera_People_Tracking_CVPRW_2024_paper.pdf)).
* **2025 onward** the BEV/depth fusion approach entered the challenge: "DepthTrack: Cluster Meets BEV for
  Multi-Camera Multi-Target 3D Tracking"
  ([ICCVW 2025](https://openaccess.thecvf.com/content/ICCV2025W/AICity/papers/Tran_DepthTrack_Cluster_Meets_BEV_for_Multi-Camera_Multi-Target_3D_Tracking_ICCVW_2025_paper.pdf)),
  and the challenge itself continues ([2026 Track 1](https://www.aicitychallenge.org/2026-track1/)).

**The pattern across all winners**: strong detector → strong ReID (often trained on *both* real and synthetic)
→ tracklet clustering → *spatio-temporal consistency repair pass*. The last stage is where the points are.

---

## 7. Practical system engineering

### 7.1 Time synchronisation — the first thing to audit on site

* Accuracy classes: "IEEE-1588 PTP allows synchronization of devices within a few microseconds, compared to
  NTP which operates on the millisecond scale", and "NTP is accurate under ten milliseconds, while PTP is
  accurate up to less than a microsecond and is measured in nanoseconds"
  ([PTP vs NTP](https://www.mikrodev.com/ptp-ieee-1588-vs-ntp-millisecond-precision-time-synchronization-in-industrial-networks-and-scada/)).
  PTP achieves this because it "utilizes hardware based timestamping to improve over NTP latency accuracy"
  ([Teledyne](https://www.teledynevisionsolutions.com/learn/learning-center/machine-vision/precision-system-synchronization-with-the-ieee-1588-precision-time-protocol-ptp/)).
* But PTP degrades over the network you actually have: "PTP can maintain its precision through about 5
  switches/routers unless these devices are also transparent clocks or boundary clocks, and even with on-path
  support there is a limit of a few dozen hops before network timing asymmetry builds up and ruins the
  accuracy of PTP" ([Meinberg](https://blog.meinbergglobal.com/2013/11/22/ntp-vs-ptp-network-timing-smackdown/)).
* Media-specific profile: "SMPTE 2059 is directed to leveraging PTP to provide timestamps for video data
  encapsulated in IP packets, allowing PTP time reference data to be shared throughout a network to provide
  synchronized clocks to media nodes (e.g., cameras)" (ibid).
* **What goes wrong in practice** [lore]: RTSP/RTP presentation timestamps are in a 90 kHz clock with an
  arbitrary random offset and *no* wall-clock meaning until you receive an RTCP sender report; VMS software
  often re-stamps frames at *ingest*, so your "timestamp" is actually network arrival time plus jitter; the
  burnt-in OSD clock is frequently the only source of truth and it is per-camera, drifting, and sometimes in
  the wrong DST; cheap cameras free-run at "25 fps" that is really 24.97 fps, so two cameras drift a frame
  every ~40 s; a camera that loses NTP after a reboot can come back at 1970 or at manufacture date.
* **Budget rule**: a person at 1.4 m/s moves 0.28 m in 200 ms. If your association gate is 0.5 m, then
  **your total clock error budget across the network is ~300 ms, and that is before you add exposure-time
  mid-point differences.** Sync must be an explicit, monitored, alarmed metric — and SurvSim must therefore
  model `clock_offset_ms` and `drift_ppm` per camera (it does) and include a *sync-error sweep* in the eval
  harness.

### 7.2 Frame-rate mismatch, drops and codecs

Mixed 25/30/15/6 fps estates are normal; so are variable-frame-rate streams under bandwidth pressure. Fixes:
resample all tracks onto a common world-time grid (interpolate world positions, never image positions); carry
a per-observation timestamp rather than a frame index; treat frame drops as missing data in the motion model
rather than as evidence of absence. Long GOPs mean a dropped I-frame corrupts up to a second of video; low
bitrate destroys ReID-relevant texture before it destroys human-perceived quality. **Always evaluate ReID at
the customer's bitrate, not on clean JPEGs.** [lore, and the reason SurvSim's degradation pipeline runs
codec-last on clean frames.]

### 7.3 Global association: the algorithm menu

* **Min-cost flow / network flow** — the classical globally-optimal batch formulation: "the
  maximum-a-posteriori (MAP) data association problem is mapped into a cost-flow network with a non-overlap
  constraint on trajectories", and "The globally optimal solution to a minimum-cost network flow problem can
  be found in polynomial-time, e.g., with the push-relabel algorithm"
  ([Zhang et al., CVPR 2008](http://vision.cse.psu.edu/courses/Tracking/vlpr12/lzhang_cvpr08global.pdf)).
  Two-stage variants remain competitive ([arXiv 2311.02642](https://arxiv.org/pdf/2311.02642)), and the global
  objective itself can be learned ([Monash](https://researchmgt.monash.edu/ws/portalfiles/portal/402292190/402291877_oa.pdf)).
* **Bipartite matching per camera pair** — the cheap default, with a known weakness: "Cross-camera image data
  association is typically stated as a bipartite graph matching problem and often solved by applying
  minimum-cost flow techniques, which may be computationally inefficient with large data, and cameras are
  usually treated by pairs, obtaining local solutions, rather than finding a global solution at once"
  ([GNNs for Cross-Camera Data Association](https://arxiv.org/pdf/2201.06311)).
* **GNNs** — learn the affinity *and* the message passing over the tracklet graph; but note the honest
  criticism that "graph-based MC-MOT methods often rely on computationally inefficient min-cost flow
  approaches for cross-camera association, with static graph structures that lack adaptability to new
  detections" (ibid / as summarised in the MC-MOT literature).
* **Transformers** — "A transformer-based global MTMC association module can explore target associations
  across different cameras and frames, generating global trajectories directly"; see
  [MCTR: Multi Camera Tracking Transformer](https://arxiv.org/pdf/2408.13243).
* **Clustering + repair** — what actually wins challenges (§6.1): agglomerative/anchor-guided clustering of
  tracklet embeddings, followed by spatio-temporal consistency re-assignment.
* **Distributed association** — for large estates: "Distributed multi-camera multi-target association for
  real-time tracking" ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9246937/)), and fully distributed
  real-time multi-view 3D tracking ([arXiv 2606.13127](https://arxiv.org/pdf/2606.13127)).

### 7.4 Online vs batch, and the architecture that serves both

Batch wins accuracy; operations need online. The standard compromise is a **sliding-window hierarchical
tracker**: online per-camera tracking → short-window (5–30 s) cross-camera clustering for live alerts →
periodic longer-window re-clustering that is allowed to *merge and rename* identities retrospectively, with
the UI presenting a stable "provisional ID → confirmed ID" mapping. Note that the AI City 10% online bonus
exists precisely because the community accepts online is intrinsically harder
([8th AI City Challenge](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Wang_The_8th_AI_City_Challenge_CVPRW_2024_paper.pdf)).
**Never let retrospective ID merges silently rewrite an alert history — keep an append-only audit log.** [lore]

### 7.5 Scale: hundreds to thousands of cameras

* Naive all-pairs tracklet comparison is O(N²) in tracklets, which at 1,000 cameras is hopeless. The fix is
  the topology graph as a *sparsifier*: only compare tracklets on edges that exist, within the transit-time
  window. This is the single biggest scalability lever, and it is why §1.3 matters even when you have partial
  overlap.
* Second lever: ANN search (FAISS/HNSW) over tracklet embeddings with time-bucketed indices, plus
  query-adaptive pruning — see [TRACER](https://arxiv.org/pdf/2507.09448) on adaptive query processing for
  networked-camera ReID, and [STAC](https://arxiv.org/pdf/2401.15288) on "Leveraging Spatio-Temporal Data
  Associations For Efficient Cross-Camera Streaming and Analytics".
* Third lever: push detection + embedding to the edge, ship embeddings (≈512 floats, or 128 bytes int8 with
  PQ) instead of video. Bandwidth then scales with *people*, not pixels.
* Storage arithmetic [lore]: 1,000 cameras × 4 Mbps × 30 days ≈ 1.3 PB. Embeddings for 1,000 cameras at 10
  tracklets/min/camera × 512 B ≈ 7 GB/month. **Your analytics index is ~5 orders of magnitude smaller than
  your video. Design the index to be permanent and the video to be ephemeral.**
* The surveys agree on the blockers: "Persistent challenges are identified, particularly in inter-camera data
  association, scalability, computational efficiency, privacy preservation, and dataset availability"
  ([Multi Camera Connected Vision System survey](https://arxiv.org/html/2510.09731v1)); see also
  [MC-MOT review](https://www.sciencedirect.com/science/article/pii/S0925231223006811) and the
  2020–2025 systematic review ([Algorithms 2026](https://doi.org/10.3390/a19040249)).

### 7.6 Evaluation: what to report, and the traps

* **Detection on the ground plane**: "MODA = 1 - (FP + FN)/N, where FP is the number of false positives, FN is
  the number of false negatives, and N is the number of ground-truth objects", and "MODP is calculated as
  MODP = Σ(1 - d[d < t]/t) / TP, where d represents the distance between a detection and its corresponding
  ground truth, with t set to 0.5 m as a threshold to determine true positives"
  ([Probabilistic Occupancy Volume paper](https://arxiv.org/html/2503.10982v1); protocol origin:
  [CLEAR evaluation protocol](https://catalog.ldc.upenn.edu/docs/LDC2011V03/ClearEval_Protocol_v5.pdf)).
  **Always state the distance threshold.** MODA at 1.0 m and MODA at 0.5 m are different papers.
* **Identity**: "The identity F1 (IDF1), identity precision (IDP), and identity recall (IDR) scores proposed
  by Ristani et al. established themselves as the standard metrics for evaluating MTMCT systems"
  ([Ristani & Tomasi, CVPR 2018](https://users.cs.duke.edu/~tomasi/papers/ristani/ristaniCvpr18.pdf) —
  as summarised [here](https://eurasip.org/Proceedings/Eusipco/Eusipco2022/pdfs/0000533.pdf)). "IDF1 is
  expressed as a ratio of correctly identified detections over the average number of ground-truth and
  computed detections and balances identification precision and recall through their harmonic mean", and
  "The IDF1 measure is an identity-based measure that emphasizes the track identity preservation capability
  over the entire sequence, with predictions-to-ground-truth mapping established by solving a bipartite
  matching problem" (ibid).
* **HOTA** decomposes detection and association explicitly
  ([HOTA, IJCV 2021](https://link.springer.com/article/10.1007/s11263-020-01375-2)) and is now the AI City
  MTMC metric (in 3D distance form).
* **Traps** [lore]: (1) IDF1 is dominated by long tracks — a system that nails the one person who stands
  around for 10 minutes and fumbles 20 transients can score well; report per-identity distributions.
  (2) Evaluating MTMC with ground-truth detections hides the real failure mode. (3) Cross-camera-only IDF1
  (ignoring within-camera errors) is the number that tells you whether your ReID/topology works — compute it
  separately. (4) For a security product, the metric that matters is **alerts per operator-hour at fixed
  recall**, not IDF1; a 2-point IDF1 gain that doubles false alarms is a regression.
* Reuse: TrackEval / py-motmetrics, and Synthehicle ships MTMC evaluation code
  ([Synthehicle](https://github.com/fubel/synthehicle)).

---

## 8. Open problems, 2024–2026

1. **Generalisation across camera configurations.** GMVD showed BEV detectors memorise rigs; the open question
   is a detector that takes calibration as *input* and works on an unseen 9-camera layout zero-shot
   ([GMVD](https://github.com/jeetv/GMVD)). Unsupervised domain adaptation for multi-view detection is
   emerging ([MVUDA](https://arxiv.org/pdf/2412.04117)), as is fully unsupervised multi-view detection
   ([arXiv 2305.12457](https://arxiv.org/pdf/2305.12457)).
2. **Moving and mixed-modality networks.** Drones + body-cams + fixed cameras in one association graph:
   DIVOTrack ([IJCV 2024](https://github.com/shengyuhao/DIVOTrack)), MATRIX
   ([arXiv 2511.08615](https://arxiv.org/html/2511.08615)), multi-moving-camera tracking
   ([arXiv 2312.11035](https://arxiv.org/pdf/2312.11035)).
3. **Clothes-changing ReID at deployable accuracy.** LTCC clothes-changing Rank-1 around 40 % (CAL 40.1) is the honest state of the art;
   nothing yet gets long-term ReID to a level where an automatic alert is defensible.
4. **Long-horizon identity (days to months)** — DeepChange's 12-month window is the only natural-variation
   benchmark of that length ([DeepChange](https://arxiv.org/abs/2105.14685)), and results there remain low.
5. **Adversarially-aware tracking.** No standard benchmark exists for camera-aware evasion, deliberate outfit
   swapping in blind spots, or impersonation attacks at the *system* level (as opposed to the model level).
6. **Open-set / unknown-identity operation.** Every benchmark is closed-set-ish; real estates have an
   unbounded, mostly-unknown population, and calibration of "this is a new person" vs "this is a re-appearance"
   is unsolved. Open-set metrics (FNIR@FPIR, as used by BRIAR/FarSight) should replace CMC in security work.
7. **Group and social-structure reasoning** as a first-class association cue.
8. **Foundation/multi-modal unification**: Instruct-ReID++, ReID5o/ORBench, VP-ReID
   ([ReID5o](https://arxiv.org/html/2506.09385v1), [VP-ReID](https://arxiv.org/html/2508.06908)) — can one
   model serve image, text, IR and clothes-changing queries at deployable latency?
9. **Privacy-preserving analytics**: embeddings-only pipelines, on-camera processing, and provable
   watchlist-scoping — driven by the legal environment in §5.4, and named as an open challenge by the surveys
   ([survey](https://arxiv.org/html/2510.09731v1)).
10. **Calibration that self-heals.** Mounts get bumped, PTZ encoders drift, buildings settle. Continuous
    auto-recalibration from pedestrian observations plus learned single-image priors
    ([GeoCalib](https://github.com/cvg/GeoCalib)) is the obvious product, and nobody ships it.
11. **Degraded-imagery ReID**: thermal/IR cross-modality, night, fog, heavy compression. Cross-modality
    visible–infrared ReID is in Instruct-ReID++'s task list precisely because it is unsolved.
12. **Evaluation realism**: benchmarks are minutes long, perfectly synchronised and perfectly calibrated. The
    community lacks a benchmark that varies sync error, calibration error and coverage gaps as controlled
    variables — **which is exactly the benchmark SurvSim can create.**

---


* **Nine-tenths of "the algorithm is bad" turns out to be installation.** Camera looking at the sun at 07:30,
  a wasp nest in the housing, a shrub that grew 40 cm, a cleaner who re-aimed a dome to see the till.
  Before touching the model, diff today's background against last month's. [lore]
* **Ask for the camera schedule and the maintenance log before the video.** In any large estate a double-digit
  percentage of cameras are mis-focused, mis-timed or mis-labelled in the VMS. Camera IDs in the VMS do not
  match the site plan; two cameras are swapped. Every MTMC system silently produces teleporting people because
  of this. [lore]
* **Foot points are worth more than boxes.** Everything geometric depends on the foot contact point, which is
  the first thing occluded by crowds, bollards and shopping trolleys. That is the real reason multi-height
  homographies ([SHOT](https://arxiv.org/pdf/2208.09211)) and occupancy volumes
  ([arXiv 2503.10982](https://arxiv.org/pdf/2503.10982)) beat single-homography methods.
* **The ground plane is a lie.** Steps, ramps, kerbs, escalators, mezzanines. One homography per camera is a
  bug you will ship. Model zones with per-zone planes.
* **ReID scores are not calibrated probabilities and are camera-pair-specific.** The same cosine distance
  means different things for the well-lit lobby pair and the IR-at-night car-park pair. Learn a per-edge
  threshold (or a per-edge score normalisation); this is the cheapest single accuracy win in a real
  deployment, and it is invisible in benchmarks where all cameras are similar. [lore]
* **Two-thirds of your cross-camera errors will be four people**: the high-vis jacket crew, the school-uniform
  cohort, the black-puffer-coat winter population, and staff in identical uniforms. Appearance-only ReID is
  near-chance inside those cohorts — which is what SoccerNet (identical kits) measures in the extreme
  ([SoccerNet 2023](https://arxiv.org/pdf/2309.06006)). Plan to fall back on geometry and timing.
* **Impersonation is the liability, not evasion.** A missed detection is an operational miss; a confident
  wrong identity is a wrongful stop. advPattern's "47.1% rank-1 accuracy ... under Impersonation Attack"
  ([advPattern](https://arxiv.org/abs/1908.09327)) and the Met's "10 individuals were falsely flagged ...
  eight of whom were Black"
  ([Biometric Update](https://www.biometricupdate.com/202511/metropolitan-police-to-expand-live-facial-recognition-use-even-amid-legal-challenge))
  are the same lesson from two directions. Tune for precision on alerts and always present a human-verifiable
  image strip, never a bare ID.
* **Never quote a per-scan false-positive rate.** Quote false alerts per deployment and per operator shift
  (§5.4). Any vendor volunteering "0.0003%" is choosing a denominator. [lore]
* **Face recognition at a standoff is a chokepoint product.** Run the IED arithmetic (§5.1) in the sales
  meeting; a 1080p pole camera at 20 m is ~16 px IED against an ISO recommendation of ≥90–120 px
  ([face quality standards](https://arxiv.org/pdf/2211.08030)). Put the FR camera at the door, and use
  body/gait/appearance everywhere else.
* **Gait needs a gait cycle, a side view and a clean silhouette** — so it works on corridors and open plazas,
  and fails in crowds, at turnstiles, and on anyone carrying a bag. And its in-the-wild numbers are ~50%
  Rank-1, not ~90% ([OpenGait](https://arxiv.org/pdf/2405.09138)). [lore + source]
* **Sync first, always.** Before any modelling, plot the cross-correlation of per-camera people-count time
  series for overlapping pairs; the lag of the peak is your clock offset, for free, per pair, continuously.
  It is the same trick as topology inference ([arXiv 1712.00158](https://arxiv.org/pdf/1712.00158)) applied to
  a different unknown. [lore]
* **Coverage gaps are the product, not the bug.** The blind-spot map and the transit-time graph are what the
  customer's security manager actually wants on a wall. They also tell your tracker where to expect identity
  breaks, and they tell you where an adversary will walk.
* **Operators trust systems that admit uncertainty.** A "possible same person, 62%, 3 candidates" UI outperforms
  a confident wrong ID, because the operator stays in the loop and keeps using the tool. An alert stream with
  more than a few false alarms per shift gets muted, and then the system is worth zero regardless of IDF1. [lore]
* **Retrospective ID merges must be visible.** Batch re-clustering will rename identities; if that silently
  rewrites yesterday's alerts, your evidential chain is gone. Append-only identity history, with a
  provisional/confirmed distinction. [lore]
* **Legal posture is an engineering requirement.** Bridges failed on *framework*, not technology — watchlist
  provenance, deployment scoping, retention, DPIA/EqIA and bias-testing evidence are features to build, not
  paperwork to append ([Ada Lovelace](https://www.adalovelaceinstitute.org/blog/facial-recognition-technology-needs-proper-regulation/)).
  And in the EU, "real-time remote biometric identification" is the tripwire
  ([Article 5](https://artificialintelligenceact.eu/article/5/)) — non-biometric appearance tracking is a
  materially different regulatory product.
* **Never train on a retracted dataset.** DukeMTMC-reID weights are in half the open-source ReID zoo; a
  customer procurement questionnaire will eventually ask. Keep a provenance manifest per model
  ([Mitigating Dataset Harms](https://arxiv.org/pdf/2108.02922)). [lore + source]
* **Synthetic data already wins medals.** The AI City 2023 runner-up trained ReID on a "Mixture of Realistic
  and Synthetic Knowledge"
  ([repo](https://github.com/nguyenquivinhquang/Multi-camera-People-Tracking-With-Mixture-of-Realistic-and-Synthetic-Knowledge))
  and VC-Clothes, a standard CC-ReID benchmark, is GTA5-rendered
  ([VC-Clothes](https://arxiv.org/pdf/2003.04070)). When someone says "synthetic doesn't transfer", these are
  the two citations to reach for.

---

## 10. Concrete requirements this dossier imposes on SurvSim

1. Export, per camera per frame: `K`, distortion, `[R|t]`, ground homography, **and the PTZ pose actually
   used**, plus an optional *corrupted* calibration with configurable angular/zoom error (§2.4, §2.6).
2. Export per-camera `clock_offset_ms`, `drift_ppm`, frame-drop mask and true capture timestamp, and provide a
   sync-error sweep in the eval harness (§7.1).
3. Export the **camera topology truth**: overlap graph, per-cell camera count, blind-spot map, per-edge
   geodesic distance and true transit-time distributions (§1.3, §7.5).
4. Support both regimes in one scenario: an overlapping cluster (WILDTRACK-like, for MODA/MODP and BEV methods)
   and a non-overlapping chain (Duke-like, for topology + ReID) (§1.2, §1.3).
5. Appearance mutation with hidden-identity truth: outfit swap, accessory hand-off, hood/mask, gait change —
   with `change_events` timestamps so CC-ReID can be scored *as a function of what changed* (§3.4).
6. Face IED and face-visibility ground truth per frame, so face/body/gait fusion policies can be learned and
   audited (§3.6, §5.1).
7. Adversarial behaviour primitives: PTZ-cycle timing, blind-spot routing, in-gap outfit swap, group
   concealment, plus support for rendering adversarial-patch textures on garments (§4).
8. Evaluation: MODA/MODP at declared thresholds, IDF1/IDP/IDR, HOTA (2D and 3D-distance), **cross-camera-only
   IDF1**, ReID mAP/Rank-k split by same-clothes vs clothes-changed, open-set FNIR@FPIR, and
   alerts-per-operator-hour at fixed recall (§7.6).

---

## Sources

**Overlapping multi-view detection & tracking**
- [Fleuret et al., Multi-Camera People Tracking with a Probabilistic Occupancy Map (PAMI 2008)](https://infoscience.epfl.ch/record/145991/files/FleuretBLF08.pdf)
- [MVDet (ECCV 2020) — repo](https://github.com/hou-yz/MVDet) · [paper](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123520001.pdf) · [arXiv version](https://arxiv.org/pdf/2007.07247)
- [MVDeTr (ACM MM 2021)](https://github.com/hou-yz/MVDeTr) · [paper](https://arxiv.org/pdf/2108.05888)
- [Booster-SHOT / SHOT](https://arxiv.org/pdf/2208.09211)
- [GMVD — Bringing Generalization to Deep Multi-View Pedestrian Detection](https://github.com/jeetv/GMVD) · [paper](https://openaccess.thecvf.com/content/WACV2023W/RWS/papers/Vora_Bringing_Generalization_to_Deep_Multi-View_Pedestrian_Detection_WACVW_2023_paper.pdf) · [arXiv](https://arxiv.org/pdf/2109.12227)
- [EarlyBird (WACVW 2024)](https://openaccess.thecvf.com/content/WACV2024W/RWS/papers/Teepe_EarlyBird_Early-Fusion_for_Multi-View_Tracking_in_the_Birds_Eye_View_WACVW_2024_paper.pdf) · [arXiv](https://arxiv.org/html/2310.13350)
- [TrackTacular](https://github.com/tteepe/TrackTacular)
- [MVTrajecter — trajectory motion & appearance cost](https://arxiv.org/html/2509.01157)
- [Enhanced Multi-View Pedestrian Detection Using Probabilistic Occupancy Volume](https://arxiv.org/html/2503.10982v1)
- [MVDGC — dual geometric constraints](https://arxiv.org/pdf/2607.00273) · [MSMVD](https://arxiv.org/pdf/2508.20447) · [Attention-Aware Multi-View Pedestrian Tracking](https://arxiv.org/html/2504.03047)
- [MVUDA — UDA for multi-view detection](https://arxiv.org/pdf/2412.04117) · [Unsupervised Multi-view Pedestrian Detection](https://arxiv.org/pdf/2305.12457)
- [Fully Distributed Multi-View 3D Tracking in Real-Time](https://arxiv.org/pdf/2606.13127)

**Non-overlapping networks & topology**
- [Distance-based Camera Network Topology Inference for Person Re-identification](https://arxiv.org/pdf/1712.00158)
- [Learning the Three Factors of a Non-overlapping Multi-camera Network Topology](https://link.springer.com/chapter/10.1007/978-3-642-33506-8_14)
- [Joint Person Re-identification and Camera Network Topology Inference](https://arxiv.org/pdf/1710.00983) · [Unified Framework](https://arxiv.org/pdf/1704.07085)
- [Metadata-Aided Re-ID and Trajectory-Based Camera Link Model](https://arxiv.org/pdf/2105.01213)

**Calibration**
- [Perspective Fields for Single Image Camera Calibration (CVPR 2023)](https://arxiv.org/pdf/2212.03239)
- [GeoCalib (ECCV 2024) — repo](https://github.com/cvg/GeoCalib) · [paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/05636.pdf) · [slides](https://eccv.ecva.net/media/eccv-2024/Slides/1349_WHtPdnV.pdf)
- [Hierarchical camera auto-calibration for traffic surveillance systems](https://www.sciencedirect.com/science/article/abs/pii/S0957417413006714)
- [Using pedestrians walking on uneven terrains for camera calibration](https://link.springer.com/article/10.1007/s00138-009-0210-2)
- [Extrinsic Calibration of Camera Networks Based on Pedestrians](https://www.academia.edu/95066018/Extrinsic_Calibration_of_Camera_Networks_Based_on_Pedestrians)
- [Camera auto-calibration using pedestrians and zebra-crossings](https://www.academia.edu/16959323/Camera_auto_calibration_using_pedestrians_and_zebra_crossings)
- [Implementation of Efficient PTZ Camera Calibration (DTIC)](https://apps.dtic.mil/sti/pdfs/ADA497476.pdf) · [DeepPTZ](https://www.researchgate.net/publication/338580315_DeepPTZ_Deep_Self-Calibration_for_PTZ_Cameras) · [PTZ-Calib](https://www.researchgate.net/publication/395224362_PTZ-Calib_Robust_Pan-Tilt-Zoom_Camera_Calibration) · [Two-point PTZ method](https://arxiv.org/pdf/1801.09005) · [Continuous PTZ localization & mapping](https://arxiv.org/pdf/1401.6606)
- [CALICO — multi-camera calibration with pattern rigs](https://arxiv.org/html/1903.06811v3) · [NMC3D — non-overlapping calibration via sparse 3D map](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11359340/) · [Online Multi Camera-IMU Calibration](https://arxiv.org/pdf/2209.13821) · [On-line non-overlapping camera calibration net](https://arxiv.org/pdf/2002.08005)

**ReID (general)**
- [OSNet (ICCV 2019)](https://arxiv.org/abs/1905.00953)
- [MSMT17 / PTGAN](https://arxiv.org/abs/1711.08565)
- [IUST_PersonReId — cross-domain comparison of SOLIDER / TransReID / CLIP-ReID](https://arxiv.org/html/2412.18874v1)
- [Cluster Contrast for Unsupervised Person Re-ID](https://arxiv.org/abs/2103.11568) · [SSG](https://arxiv.org/pdf/1811.10144)
- [Bridging the Source-to-target Gap with Intermediate Domains](https://arxiv.org/pdf/2203.01682)
- [Deep learning-based person re-identification: survey and outlook](https://arxiv.org/pdf/2110.04764)
- [MARS video ReID benchmark](https://link.springer.com/chapter/10.1007/978-3-319-46466-4_52) · [VID-Trans-ReID](https://github.com/AishahAADU/VID-Trans-ReID)
- [Occluded ReID taxonomic survey & benchmark](https://link.springer.com/article/10.1007/s00371-026-04699-1)
- [Instruct-ReID (CVPR 2024)](https://openaccess.thecvf.com/content/CVPR2024/papers/He_Instruct-ReID_A_Multi-purpose_Person_Re-identification_Task_with_Instructions_CVPR_2024_paper.pdf) · [MLLM re-ranking / Instruct-ReID++ summary](https://arxiv.org/pdf/2606.16161) · [Find Them All / VP-ReID](https://arxiv.org/html/2508.06908) · [ReID5o / ORBench](https://arxiv.org/html/2506.09385v1) · [Person Re-ID in 2025](https://arxiv.org/pdf/2601.20598)

**Clothes-changing / long-term ReID, gait, attributes, text**
- [CAL — Clothes-Changing ReID with RGB Modality Only (CVPR 2022)](https://openaccess.thecvf.com/content/CVPR2022/papers/Gu_Clothes-Changing_Person_Re-Identification_With_RGB_Modality_Only_CVPR_2022_paper.pdf)
- [3DInvarReID (ICCV 2023)](https://github.com/liufeng2915/3DInvarReID) · [paper](https://arxiv.org/pdf/2308.10658)
- [DeepChange](https://arxiv.org/abs/2105.14685) · [LTCC](https://arxiv.org/pdf/2005.12633) · [VC-Clothes](https://arxiv.org/pdf/2003.04070) · [Celeb-reID line](https://arxiv.org/pdf/2208.12023) · [Unsupervised long-term ReID with clothes change](https://arxiv.org/html/2202.03087v3)
- [Gait prediction & regularization for single-image CC-ReID](https://arxiv.org/pdf/2103.15537) · [Skeleton dynamics CC-ReID](https://arxiv.org/pdf/2503.10759) · [SCNet](https://arxiv.org/pdf/2308.14113) · [Try Harder](https://arxiv.org/pdf/2507.11119) · [MIPL](https://arxiv.org/html/2411.00330v1) · [CCPA](https://arxiv.org/pdf/2402.14454) · [Instance-adaptive low-rank orthogonal subspaces](https://arxiv.org/pdf/2606.11661) · [CC-ReID comparative study](https://www.sciencedirect.com/science/article/abs/pii/S0167865526001352)
- [OpenGait benchmark study](https://arxiv.org/pdf/2405.09138) · [MultiGait++](https://arxiv.org/pdf/2412.11495) · [GREW](https://arxiv.org/pdf/2205.02692) · [RealGait](https://arxiv.org/pdf/2201.04806) · [Deep Gait Recognition survey](https://arxiv.org/pdf/2102.09546)
- [Pedestrian attribute recognition (PETA / PA-100K) — hypergraph learning](https://arxiv.org/pdf/2509.22331) · [Localization Guided Learning](https://arxiv.org/pdf/1808.09102)
- [ROGLE — text-based person search](https://arxiv.org/pdf/2606.01825) · [SCMM](https://arxiv.org/pdf/2304.02278) · [Part-level cross-modal correspondence](https://arxiv.org/pdf/2501.00318)

**Adversarial identity**
- [advPattern (ICCV 2019)](https://arxiv.org/abs/1908.09327) · [PDF](https://arxiv.org/pdf/1908.09327)
- [Deep Mis-Ranking (CVPR 2020)](https://arxiv.org/html/2004.04199v1) · [repo](https://github.com/whj363636/Adversarial-attack-on-Person-ReID-With-Deep-Mis-Ranking)
- [Thys et al., Fooling Automated Surveillance Cameras (CVPRW 2019)](https://openaccess.thecvf.com/content_CVPRW_2019/papers/CV-COPS/Thys_Fooling_Automated_Surveillance_Cameras_Adversarial_Patches_to_Attack_Person_Detection_CVPRW_2019_paper.pdf)
- [Making an Invisibility Cloak (ECCV 2020)](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123490001.pdf) · [3D Invisible Cloak](https://arxiv.org/pdf/2011.13705)
- [Physical Adversarial Attacks for Surveillance: A Survey](https://arxiv.org/pdf/2305.01074) · [Physical Adversarial Attack meets Computer Vision: A Decade Survey](https://arxiv.org/pdf/2209.15179) · [Camera-based smart systems survey](https://arxiv.org/pdf/2308.06173)
- [Multi-Expert Adversarial Attack Detection via Context Inconsistency](https://arxiv.org/pdf/2108.09891)
- [Attacking Gait Recognition via Silhouette Guided GANs](https://dl.acm.org/doi/10.1145/3343031.3351018) · [Temporal Sparse Adversarial Attack on Gait](https://arxiv.org/pdf/2002.09674) · [Latent-based perturbations of gait models](https://www.nature.com/articles/s41598-025-22869-4) · [GaitSpoofNet](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1821341/full) · [Gait biometrics under spoofing attacks](https://scispace.com/pdf/improving-gait-biometrics-under-spoofing-attacks-59qn8gye1z.pdf)

**Face recognition, law and policy**
- [NIST FRVT programme](https://www.nist.gov/programs-projects/face-recognition-vendor-test-frvt) · [FRTE 1:1 Verification](https://pages.nist.gov/frvt/html/frvt11.html) · [FRTE Demographics](https://pages.nist.gov/frvt/html/frvt_demographics.html) · [NIST Face Projects](https://www.nist.gov/programs-projects/face-projects)
- [NIST FRTE bias visualisations (1,368 algorithms, 2017–2026)](https://github.com/DrMarioDeSean411-arch/nist-frte-facial-recognition-bias) · [Bipartisan Policy Center on FRT accuracy](https://bipartisanpolicy.org/article/frt-accuracy-performance/)
- [Face Recognition in Low Quality Images: A Survey](https://arxiv.org/pdf/1805.11519) · [State of the Art of Quality Assessment of Facial Images](https://arxiv.org/pdf/2211.08030) · [Boom et al., effect of image resolution](https://ris.utwente.nl/ws/files/5328208/Boom06effect.pdf) · [BriefCam on resolution](https://www.briefcam.com/resources/videos/resolution-considerations-for-face-recognition-accuracy/) · [Kairos best practices](https://face.kairos.com/docs/api/best-practices) · [iOmniscient pixel FAQ](https://iomni.ai/faq/what-is-the-pixel-numbers-needed-for-face-detection/)
- [Ada Lovelace Institute on Bridges](https://www.adalovelaceinstitute.org/blog/facial-recognition-technology-needs-proper-regulation/) · [Inforrm case note](https://inforrm.org/2020/08/17/case-law-r-on-the-application-of-bridges-v-chief-constable-of-south-wales-police-use-of-automatic-facial-recognition-technology-unlawful-hugh-tomlinson-qc/) · [Hunton](https://www.hunton.com/privacy-and-information-security-law/uk-court-of-appeal-finds-automated-facial-recognition-technology-unlawful-in-bridges-v-south-wales-police) · [Osborne Clarke](https://www.osborneclarke.com/insights/appeals-court-hands-uks-first-judgment-automated-facial-recognition) · [Liberty](https://www.libertyhumanrights.org.uk/issue/legal-challenge-ed-bridges-v-south-wales-police/) · [Columbia Global Freedom of Expression case page](https://globalfreedomofexpression.columbia.edu/cases/r-v-the-chief-constable-of-south-wales-police/)
- [EU AI Act Article 5 (text)](https://artificialintelligenceact.eu/article/5/) · [FPF on real-time RBI red lines](https://fpf.org/blog/red-lines-under-the-eu-ai-act-restricting-real-time-remote-biometric-identification-systems-for-law-enforcement-purposes/) · [Article 5 red lines commentary](https://securityboulevard.com/2026/04/article-5-and-the-eu-ai-acts-absolute-red-lines-firetail-blog/)
- [Met Police LFR expansion & statistics](https://www.biometricupdate.com/202511/metropolitan-police-to-expand-live-facial-recognition-use-even-amid-legal-challenge) · [Met permanent LFR pilot](https://www.biometricupdate.com/202605/met-police-tout-arrests-crime-drop-from-permanent-lfr-camera-pilot) · [Met press release](https://news.met.police.uk/news/met-makes-one-arrest-every-35-minutes-during-live-facial-recognition-pilot-509256) · [The Register (Nov 2025)](https://www.theregister.com/2025/11/03/metropolitan_police_hails_facial_recognition/) · [Big Brother Watch response](https://www.theregister.com/2025/07/09/big_brother_watch_met_lfr/)
- [IARPA BRIAR programme](https://www.iarpa.gov/research-programs/briar) · [BRIAR covariate analysis](https://arxiv.org/abs/2409.01514) · [FarSight](https://arxiv.org/pdf/2306.17206) · [Fusion of Face, Body Shape and Gait](https://arxiv.org/pdf/2505.04616) · [Person Recognition in Aerial Surveillance: A Decade Survey](https://arxiv.org/pdf/2511.17674) · [CoNAN](https://arxiv.org/pdf/2307.10237)

**Datasets & benchmarks**
- [WILDTRACK (CVPR 2018)](https://infoscience.epfl.ch/record/256268) · [arXiv](https://arxiv.org/pdf/1707.09299) · [KU Leuven PDF](https://homes.esat.kuleuven.be/~konijn/publications/2018/WILDTRACK.pdf)
- [MMPTRACK (WACV 2023)](https://openaccess.thecvf.com/content/WACV2023/papers/Han_MMPTRACK_Large-Scale_Densely_Annotated_Multi-Camera_Multiple_People_Tracking_Benchmark_WACV_2023_paper.pdf) · [ICCV 2021 MMP challenge dataset page](https://iccv2021-mmp.github.io/subpage/dataset.html)
- [DIVOTrack (IJCV 2024)](https://github.com/shengyuhao/DIVOTrack) · [paper](https://arxiv.org/pdf/2302.07676) · [Springer](https://link.springer.com/article/10.1007/s11263-023-01922-7)
- [Synthehicle (WACVW 2023)](https://github.com/fubel/synthehicle) · [paper](https://arxiv.org/abs/2208.14167)
- [AI City Challenge 2023 tracks](https://www.aicitychallenge.org/2023-challenge-tracks/) · [2023 winners](https://www.aicitychallenge.org/2023-challenge-winners/) · [2024 winners](https://www.aicitychallenge.org/2024-challenge-winners/) · [2026 Track 1](https://www.aicitychallenge.org/2026-track1/) · [8th AI City Challenge summary](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Wang_The_8th_AI_City_Challenge_CVPRW_2024_paper.pdf)
- [Anchor-Guided Clustering + STCRA (2023 winner)](https://arxiv.org/pdf/2304.09471) · [Mixture of Realistic and Synthetic Knowledge (2nd place)](https://github.com/nguyenquivinhquang/Multi-camera-People-Tracking-With-Mixture-of-Realistic-and-Synthetic-Knowledge) · [Overlap Suppression Clustering](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Yoshida_Overlap_Suppression_Clustering__for_Offline_Multi-Camera_People_Tracking_CVPRW_2024_paper.pdf) · [Cluster Self-Refinement](https://openaccess.thecvf.com/content/CVPR2024W/AICity/papers/Kim_Cluster_Self-Refinement_for_Enhanced_Online_Multi-Camera_People_Tracking_CVPRW_2024_paper.pdf) · [DepthTrack (ICCVW 2025)](https://openaccess.thecvf.com/content/ICCV2025W/AICity/papers/Tran_DepthTrack_Cluster_Meets_BEV_for_Multi-Camera_Multi-Target_3D_Tracking_ICCVW_2025_paper.pdf)
- [SoccerNet 2023 Challenges Results](https://arxiv.org/pdf/2309.06006) · [SoccerNet 2024](https://arxiv.org/pdf/2409.10587) · [SoccerTrack v2](https://arxiv.org/pdf/2508.01802) · [Multi-view multi-player soccer dataset](https://www.mdpi.com/2076-3417/13/9/5361)
- [MATRIX multi-drone multi-view dataset](https://arxiv.org/html/2511.08615)
- [Mitigating Dataset Harms Requires Stewardship (DukeMTMC retraction analysis)](https://arxiv.org/pdf/2108.02922) · [Exposing.ai DukeMTMC page](https://exposing.ai/duke_mtmc/)

**Association, metrics, systems**
- [Zhang et al., Global Data Association Using Network Flows (CVPR 2008)](http://vision.cse.psu.edu/courses/Tracking/vlpr12/lzhang_cvpr08global.pdf) · [Two-Stage Min-Cost Flow](https://arxiv.org/pdf/2311.02642) · [Learning the Global Objective for Network Flow](https://researchmgt.monash.edu/ws/portalfiles/portal/402292190/402291877_oa.pdf)
- [GNNs for Cross-Camera Data Association](https://arxiv.org/pdf/2201.06311) · [MCTR: Multi Camera Tracking Transformer](https://arxiv.org/pdf/2408.13243) · [Glance-MCMT](https://arxiv.org/html/2507.10115v1) · [Unified Multi-view Multi-person Tracking Framework](https://arxiv.org/pdf/2302.03820) · [Self-supervised multi-view association & tracking](https://arxiv.org/pdf/2401.17617)
- [Ristani & Tomasi, Features for MTMC Tracking and Re-Identification (CVPR 2018)](https://users.cs.duke.edu/~tomasi/papers/ristani/ristaniCvpr18.pdf) · [HOTA (IJCV 2021)](https://link.springer.com/article/10.1007/s11263-020-01375-2) · [CLEAR evaluation protocol](https://catalog.ldc.upenn.edu/docs/LDC2011V03/ClearEval_Protocol_v5.pdf) · [Online real-time MTMC (EUSIPCO 2022)](https://eurasip.org/Proceedings/Eusipco/Eusipco2022/pdfs/0000533.pdf) · [CityFlow](https://arxiv.org/pdf/1903.09254)
- [PTP vs NTP (Mikrodev)](https://www.mikrodev.com/ptp-ieee-1588-vs-ntp-millisecond-precision-time-synchronization-in-industrial-networks-and-scada/) · [NTP vs PTP (Meinberg)](https://blog.meinbergglobal.com/2013/11/22/ntp-vs-ptp-network-timing-smackdown/) · [Teledyne on IEEE-1588](https://www.teledynevisionsolutions.com/learn/learning-center/machine-vision/precision-system-synchronization-with-the-ieee-1588-precision-time-protocol-ptp/) · [PTP explained (NetworkLessons)](https://networklessons.com/ip-services/precision-time-protocol-ptp-explained) · [Synchronized multimodal multisensor acquisition](https://arxiv.org/pdf/2008.03715)
- [STAC — spatio-temporal associations for cross-camera streaming](https://arxiv.org/pdf/2401.15288) · [TRACER — adaptive query processing for networked-camera ReID](https://arxiv.org/pdf/2507.09448) · [Distributed multi-camera multi-target association](https://pmc.ncbi.nlm.nih.gov/articles/PMC9246937/)
- [Multi Camera Connected Vision System survey (2025)](https://arxiv.org/html/2510.09731v1) · [MC-MOT review](https://www.sciencedirect.com/science/article/pii/S0925231223006811) · [Recent Advances in Multi-Camera CV for Industry 4.0 & Smart Cities (2026)](https://doi.org/10.3390/a19040249) · [Challenge of Multi-Camera Tracking](https://arxiv.org/pdf/1702.01507) · [Towards Effective Multi-Moving-Camera Tracking](https://arxiv.org/pdf/2312.11035)
