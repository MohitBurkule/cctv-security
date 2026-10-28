# 75 · Camera geometry and calibration for world-coordinate CCTV analytics

Companion to **29** (pinhole, homography derivation, Zhang, PTZ model, DORI, error
propagation — read that first; this doc does not repeat its derivations). 75 covers what 29
left as `[VERIFY]`: **auto-calibration from people**, how a calibrated ground plane is used
(world tracking, metric speed/height, hand-off, PTZ re-calibration), what breaks in the field,
and the one thing only a simulator can do — **measure auto-calibration error against exact
truth** (H39, 32 §H39). Tags: **[V]** fetched/measured, **[A]** from memory or abstract only.

---

## 0. Corpus coverage before this doc (grep, 2026-09-27)

| Topic | Where it already lives | Gap filled here |
|---|---|---|
| Pinhole, K, Brown–Conrady/fisheye | 29 §1, §3 | — (pointer only) |
| Ground homography `K[r1 r2 t]`, 8 DOF | 29 §2, 55 formula sheet | how to *get* it without a survey |
| Zhang / PnP / bundle adjustment | 29 §4, §9.2 | — |
| Self-calibration from people | 29 §9.2 item 4, tagged `[VERIFY]` | §3, H39 |
| PTZ `R_mount·R(pan,tilt)`, `f(z)` | 29 §5, §9.4 | re-calibration after slew, §5 |
| World-coordinate tracking | 73 (one bullet), R02 | error budget with measured numbers, §4 |
| Pitch error ∝ d²/h | 29 §8.3, 73 | measured on our renders, §6 |
| Metric height / speed | not covered | §4.2 |

---

## 1. The model in five lines (see 29 for derivations)

* Pixel `x ~ K [R | t] X`, `K = [[f,0,cx],[0,f,cy],[0,0,1]]` for a square-pixel CCTV sensor.
  SurvSim's `survsim/core/geometry.py` builds K from HFOV with the principal point at centre.
* Distortion is applied in normalised coordinates before K (Brown–Conrady k1,k2,p1,p2,k3; or
  fisheye θ-polynomial). batch_v8 renders have **zero distortion** — a confound for H39.
* For points on z = 0 the third column of R drops out: `H = K [r1 r2 t]`, a 3×3 homography, 8
  DOF, **4 non-collinear ground correspondences** fix it.
* Everything off the plane (heads, roofs, a person on a stair) is *not* mapped by H.
* SurvSim writes the exact K, R, t per camera to `calib/<cam>.json`
  (`survsim/gt/writers.py::_write_calib`), including the distortion coefficients actually used.

---

## 2. Extrinsics: survey vs auto-calibration

### 2.1 Survey (what integrators actually do)

1. **Map/orthophoto homography.** Click ≥ 4 ground landmarks in image and site plan, fit H
   with RANSAC. CityFlow did exactly this with Google Maps: 5–14 landmarks per camera, 11.52 px
   mean reprojection error [V, via 29 ref 7]. No intrinsics needed; only valid on the plane.
2. **Bench intrinsics + field PnP.** Checkerboard K on the bench (Zhang, ~0.3 px RMS [V, 29]),
   then ≥ 4 surveyed 3-D points → `[R|t]`. Recovers mount height and tilt, so heads project too.
3. **Joint bundle adjustment** for overlapping cameras (WILDTRACK: 1,398 annotated points) — the
   only route to *mutually consistent* calibrations in overlap [V, 29 ref 8].

Cost: a site survey is a half-day of an engineer with a laser distance meter per few cameras.
That is the number auto-calibration competes with.

### 2.2 Auto-calibration: the families

| Family | Cue | Recovers | Needs | Reported error |
|---|---|---|---|---|
| **People as vertical sticks** (Lv, Zhao, Nevatia, PAMI 2006 [A]) | head–foot lines of a walking person converge to the *vertical vanishing point*; head–head and foot–foot lines of the same person at different times give the *horizon* | f, tilt, roll; metric scale from a known height | tracked person, head/foot points on the body axis (not box corners) | no number quoted [A — Semantic Scholar 429 and dblp blocked again on audit, 2026-09-27] |
| **Height distributions** (Liu, Collins, Liu, BMVC 2011 [A]) | many detections, heights ~ N(1.7, σ) | f, tilt, camera height | detector only, no tracking | [A] |
| **Pedestrian detections + learned pose** (Brouwers et al., ECCV 2016 Workshops, doi 10.1007/978-3-319-48881-3_52 [V title/venue]) | detected people in the wild | f, tilt, height | many detections | not fetched [A] |
| **Pedestrian scale + CNN pose** (Wagner et al., "4-D Scene Alignment in Surveillance Video", arXiv 1906.01675 [V]) | CNN camera-pose estimate, vertical scale from pedestrians; *no* head/foot detection or tracking | pose + metric scale | pedestrians | abstract gives no numbers [V] |
| **Vehicles** (Sochor, Juránek, Herout, CVIU; arXiv 1702.06451 [V]) | two vanishing points from vehicle motion/edges + scale by aligning 3-D car models to boxes | full K, R, scale | traffic | **speed error 7.98 → 1.10 km/h** vs prior automatic; **manual calibration 1.35 km/h** — auto beat the hand survey [V] |
| **Vehicle VP heatmaps** (Kocur & Ftáčnik, arXiv 2103.11438 [V]) | CNN heatmaps of VPs in diamond space | f, road plane | traffic | abstract gives no numbers [V] |
| **Fisheye traffic** (Jain & Saunier, arXiv 2001.07243 [V]) | equidistant fisheye intrinsics + two ground VPs from vehicles at perpendicular intersections | K, distortion, R | **camera height as user input** | abstract gives no numbers [V] |
| **Street-view reconstruction** (Vuong, Tamburo, Narasimhan, WACV 2024; arXiv 2311.04243 [V]) | metric 3-D model from street-level imagery, register camera | K, R, t | street imagery of the site | 100+ cameras calibrated; 20 fully calibrated for eval [V] |
| **Single-image learned** (GeoCalib, Veicht et al., ECCV 2024; arXiv 2409.06704 [V]) | network + geometric optimisation of gravity and FoV | roll, pitch, vFoV (no height, no scale) | one image | LaMAR median **roll 0.28°, pitch 0.87°, FoV 3.03°**; MegaDepth roll 0.36°, pitch 1.94°, FoV 4.46° [V, Table 1 re-fetched on audit] |
| Human-tracking self-calibration in the 2017 AI City Challenge Track 2 winner (Tang et al., arXiv 1708.06831 [V]) | "evolutionary camera self-calibration from tracking of walking humans" | K, R | tracks | no numbers in abstract [V] |

**Read the numbers correctly.** GeoCalib's 0.87° pitch is excellent for AR; for CCTV it is
large: by 29 §8.3, 1° of pitch on a 4.5 m pole is ~7 m of ground error at 40 m. Single-image
methods give **no metric scale** — you still need a height (of the camera, or of people).
Sochor's result is the strongest pro-auto argument: in traffic, where cues are rich (vehicle
edges, known car dimensions), automatic beat manual (1.10 vs 1.35 km/h).

### 2.3 The known-height model we tested (H39)

Assume square pixels, centred principal point, no distortion, and zero yaw/position (gauge:
a single camera cannot know which way is north or where it stands). Unknowns: f, pitch, roll,
camera height h. For each detection, back-project the foot pixel to the ground, stand a person
of height `H_prior` there, project the head, and minimise the **vertical** pixel residual to
the box top (robust soft-L1). Yaw and ground position come from the install record — the
realistic case: an installer writes down where the pole is and which way it faces, but not the
tilt to a degree. Code: `survsim/experiments/autocalib.py`.

Why vertical only: an axis-aligned box's top-centre has *the same u* as its bottom-centre, so a
horizontal residual measures box geometry, not the head. Our first version used both, and it
drove f to its bound on every camera — the bug is recorded in 32 §H39 with a regression test.
Lv/Zhao/Nevatia get f from the vertical vanishing point of **body-axis** head–foot lines; a box
throws that cue away. That turns out to decide the experiment.

---

## 3. H39: what auto-calibration costs, measured against exact truth

Pre-registered in 32 before any fit. 10 cameras, 4 batch_v8 day scenes, 67 tracks, 8,195
mask boxes; `cam_ptz` excluded because it slews (its calib file is the configured pose —
principle 2), one pose-and-GT duplicate excluded. World RMSE (m) of box-bottom → ground vs
`world.parquet`, 95 % bootstrap over tracks. Figure: `figures/fig_h39.png`.

| arm | < 20 m | 20-30 m | ≥ 30 m |
|---|---|---|---|
| A0 exact calibration H | 0.208 [0.172, 0.244] | 0.203 | 0.263 [0.237, 0.286] |
| A1 DLT on GT foot points (upper bound, in-sample) | 0.117 [0.103, 0.131] | 0.141 | 0.205 |
| **A2 auto, free f (registered)** | **57.4 [46.2, 68.0]** | 90.0 | 257 |
| A3 auto, free f, first 10 s | 74.7 [64.7, 84.4] | 139.6 | 243 |
| A2f auto, datasheet f (post hoc) | 0.958 [0.769, 1.201] | 2.20 | 2.92 [2.27, 3.66] |
| A3f datasheet f, first 10 s (post hoc) | 0.759 [0.597, 0.918] | 2.29 | 5.11 |

**Hypothesis not met.** The registered method misses 0.5 m by two orders of magnitude; its 4.5×
far/near ratio "meets" the second branch only because everything is broken.

Findings:

1. **f is not identifiable from box heights** when real people vary ±10 % (children included;
   population mean 1.652 m; street_crowd SD 0.195 m, range 1.22–1.89 m) and occupy a narrow band of
   image rows: (long lens, shallow tilt) and (true lens, steep tilt) predict almost the same pixel
   height per row. 5/10 cameras went to (4) or within 1.2 % of (1) the 4w = 5,120 px f bound, with
   pitch 1.5–4.0° against true 9–20°; of the other five only `cam_02` got f within 20 % (1.03×;
   the rest 0.46×–2.05×). *(Audit correction: the first draft said "8/10 at the bound, 2–4°".)* On synthetic people of exactly 1.70 m the same code recovers f within 1 % — so this
   is a property of the *data*, which real sites share.
2. **Fix f from the datasheet** (post hoc, exploratory — added after the free-f failure was seen;
   it does not rescue the hypothesis) and the fit becomes sane — pitch within 2.1° on 7/10 cameras
   and 2.7° on 9/10; `cam_sub` (153 boxes, roll at its 15° bound) is 8.7° off — but 0.96 m < 20 m and ~3 m beyond 30 m: not good enough for a 0.5 m
   gate, fine for "which zone is this person in".
3. **Height consistency is a trap metric.** Per-track height MAE was 0.077 m for the broken A2 and
   0.074 m for A2f. The fit is *chosen* to explain heights, so heights cannot validate it.
   Validate with distances between known ground points or with positions.
4. **The foot floor is ~0.2 m even with perfect calibration.** A mask-box bottom-centre is the
   lowest shoe mid-stride, not the ground point under the pelvis. A world-coordinate tracker
   inherits it; an in-sample homography fitted to GT feet absorbs part of the bias (0.12 m).
5. **10 s vs 30 s** barely matters once f is fixed (0.76 vs 0.96 m near; worse far) — the
   limit is the model, not the amount of data.

What would likely help next (not tested — do not quote as results): head–foot points on the
mask's principal axis (restores the vertical VP), a per-person height *distribution* rather
than a mean (Liu et al.), and 2–4 surveyed ground points to pin pitch.

---

## 4. Using a calibrated ground plane

### 4.1 World-coordinate tracking

Track foot points in metres (73 §world-coordinate tracking): the constant-velocity prior
becomes physical (walk ≈ 1.4 m/s), gates are the same size at 5 m and 50 m, and
multi-camera association becomes a distance test. **Gate size must come from the calibration
error, not from a guess:** with H39's post-hoc A2f you need ~1 m gates near and ~3 m far, and the
gate should be elongated along the viewing ray (pitch error acts along it, yaw across it;
29 §8). A 0.5 m gate on a 1 m calibration fragments every far track.

### 4.2 Metric speed and height

* **Speed** = Δ(world position)/Δt. Position noise σ at frame rate r gives speed noise
  ~ √2·σ·r on raw differences — at σ = 0.2 m and 10 fps that is 2.8 m/s, twice a walking speed.
  Smooth over ≥ 1 s (Kalman / regression over a window) before thresholding "running".
* A **calibration scale error** is a *multiplicative* speed bias: a 3 % height-prior error is a
  3 % speed error everywhere; a pitch error is a range-dependent bias. Running-detection
  thresholds therefore drift with distance from the camera — test them by range bin.
* **Height** needs the full camera (not just H): intersect the head ray with the vertical
  through the foot point. With exact calibration our per-track height MAE is 0.024 m [V, H39];
  with auto-calibration it is circular (§3 finding 3).

### 4.3 Cross-camera hand-off

Two cameras registered to one site frame hand a track over when the predicted world position
leaving A matches the position entering B within the combined gate, in time. Errors to budget:
each camera's calibration error (independent, so gates add in quadrature), the foot floor
(0.2 m), **clock offset** (a 100 ms skew at 1.5 m/s is 0.15 m; `calib` records
`clock_offset_ms` and `drift_ppm`), and non-overlap travel time. Calibrations must be
*mutually* consistent in overlap — bundle adjustment, not per-camera surveys (29 §9.2).

### 4.4 PTZ re-calibration after slew — principle 2

A PTZ is registered once at the mount; at run time `R = R_mount · R(pan, tilt)`, `K = K(zoom)`
(29 §5). Three consequences:

1. **The ground homography is valid only for the current pan/tilt/zoom.** Any stored H is wrong
   after a slew. Re-derive it from telemetry every frame.
2. **Telemetry lags and backlashes.** Down-weight or drop positions while the head is moving; if
   no telemetry, re-register by matching static keypoints to a reference panorama.
3. **Ground truth must follow the live head** — CLAUDE.md principle 2. In H39 the PTZ's calib file
   says hfov 60° while `camera_status.jsonl` shows the live head at 30–35° hfov and pitch −22°/−18°,
   changing inside the window *(audit correction: the draft said "sat at 48°")*; scoring it against the static file
   would have manufactured an "auto-calibration error" that is really a stale-GT error. The
   runner therefore excludes any camera whose `camera_status.jsonl` pose/hfov/tamper differs
   from its calib in the window. A future experiment should export per-frame K, R, t (29 §10).

What H39's error costs a PTZ that is slewed to a fixed-camera alarm is measured in H56 (`83` §H56,
AUDIT_83_H56; mock, PTZ timings assumed): acquire within 3 s 0.901 ≤ 20 m and 0.727 > 30 m with
datasheet-focal calibration vs 0.967 / 0.978 exact — calibration costs 7–25 points, contention more.

---

## 5. What breaks in the field

| Failure | Symptom | Size | Detect / mitigate |
|---|---|---|---|
| **Lens change / refocus / zoom preset** | f changes, H silently wrong | proportional to Δf: all ranges scale | store lens id; re-run intrinsics; alarm on detected-height drift *by row* |
| **Bump, wind, thermal sag** (tamper "shift/rotate") | pitch/yaw change | 1° pitch ≈ 7 m at 40 m from 4.5 m (29 §8.3) | static-keypoint residual vs reference frame, alarm on median reprojection > N px (29 §9.3); SurvSim's tamper kinds already move the live pose |
| **Rolling shutter** | rows exposed at different times; fast lateral motion skews people; during a PTZ slew the whole frame shears | at 30 ms readout and 1.5 m/s, 4.5 cm — negligible for walkers; large for PTZ slews and vehicles | don't use positions during slews; per-row timestamp for vehicles |
| **Wide-angle distortion** | straight lines bow; edge feet land metres off if undistortion skipped | grows with r²; worst in corners where people enter | undistort points (not whole frames) before H; fisheye model for > ~100° HFOV; check the corners separately |
| **Ground not planar** | slopes, kerbs, stairs, ramps | a 3 % slope at 30 m ≈ 0.9 m height offset → metres of ground error at shallow tilt | piecewise homographies per zone (62 zone semantics), or a DEM; flag stairs as no-metric zones |
| **Foot not visible** | occlusion by cars/crowds; box bottom = occluder top | person "floats" metres away | use amodal/visible ratio; drop occluded foot points; head point + height prior as a fallback |
| **Heights not what you assume** | children, crouching, sitting, bikes | H39: a 3 % prior bias is a 3 % scale error | per-person height from the calibrated camera once, then track it |
| **Clock skew between cameras** | hand-off misses | 0.15 m per 100 ms at walking speed | PTP/NTP; record offsets (SurvSim `clock_offset_ms`) |

---

## 6. What the simulator adds that no real site can

A real site has no true K, R, t and no true foot position, so auto-calibration papers report
angle errors on a handful of surveyed cameras or a downstream proxy (Sochor's km/h). SurvSim
writes the **exact** calibration per camera and the **exact** ground position per person per
frame, so:

* auto-calibration error is measured in metres *per range bin*, per camera, with CIs (H39);
* the floor of any box-based method is separable (A0: 0.21 m from foot definition alone);
* the height distribution is known, so a height-prior bias can be attributed (1.652 vs 1.70 m);
* nuisance can be dialled in one at a time: distortion, a pitch bump via the tamper director,
  slopes, clock offsets — each with its true size;
* principle 2 means a slewed or tampered camera is scored against its *live* pose, so
  "calibration broke" and "GT went stale" are never confused.

Caveats: batch_v8 is flat, undistorted and 30 s long, with 10 cameras; the people are CC0/
MetaHuman rigs whose box geometry is plausible (detector-width / mask-box-width ratio 1.00–1.03
on batch_v8, 13 "Box aspect") but not real. *(Audit correction: the draft cited a non-existent
"box tightness IoU 0.90".)* The numbers bound the method's behaviour, not a site's.

---

## 7. Interview Q&A (with red flags)

**Q1. How do you get from a pixel to metres on the ground?**
Back-project the foot point through `H⁻¹` with `H = K[r1 r2 t]`, after undistorting the point.
Only feet: heads are off-plane. *Red flag:* projecting the box centre, or saying "just use the
bounding-box height as depth".

**Q2. How would you calibrate 400 existing cameras without a survey crew?**
Datasheet f (lens is known), install record for position and heading, auto-calibrate tilt/roll/
height from pedestrians over minutes, then **validate** on 2–4 measured ground distances per camera
and flag the cameras that fail. *Red flag:* "auto-calibration is solved"; or a free-f fit —
we measured 57 m RMSE when f was left free on real-looking height spread (H39).

**Q3. Your calibration makes everyone's height come out 1.70 ± 0.08 m. Is it good?**
Not evidence: the fit was tuned to explain heights. In H39 a fit with 57 m position error had
7.7 cm height MAE. Validate on positions or known distances. *Red flag:* accepting height
consistency as validation.

**Q4. Why does error grow with range, and how fast?**
Scale errors (camera-height or height-prior) grow linearly with distance; pitch errors grow
~d²/h. H39 with datasheet f (post hoc arm): 0.96 m < 20 m, 2.9 m ≥ 30 m. So gates must widen with range and
along the viewing ray. *Red flag:* one fixed-metre gate for the whole scene.

**Q5. What floor does a perfect calibration leave?**
~0.2 m in our renders: the box bottom is the lowest shoe mid-stride. Plus occluded feet, which
can be metres. *Red flag:* claiming centimetre world tracking from boxes.

**Q6. A PTZ slewed; what happens to your tracks and your ground truth?**
H changes with pan/tilt/zoom; recompute from telemetry, drop positions mid-slew, re-register
by keypoints if telemetry is absent. GT must follow the live head (principle 2) — scoring
against the configured pose invents errors. *Red flag:* one stored homography per PTZ.

**Q7. The site has a ramp and a staircase.**
Piecewise homographies per zone, or a DEM; mark stairs as no-metric. A 3 % slope is ~0.9 m
of height at 30 m. *Red flag:* ignoring it because "it's mostly flat".

**Q8. When is automatic calibration better than a manual survey?**
When the scene has rich, known-size cues: Sochor et al. got 1.10 km/h speed error vs 1.35 km/h
for manual calibration on traffic cameras. For pedestrians only, with box detections, the registered
free-f method gave 57 m; even the post-hoc datasheet-f arm stayed at 0.76–0.96 m within 20 m. *Red flag:* not knowing any number either way.

**Q9. How do you know a deployed camera's calibration has gone bad?**
Monitor reprojection of static keypoints against a reference frame; also the *row-wise* median
pixel height of people (a shift at fixed rows means tilt or zoom changed). Alarm, don't
silently re-fit. *Red flag:* "re-calibrate nightly" without a detector for when it's needed.

**Q10. Why use a simulator for any of this?**
Because it is the only place with exact K, R, t and exact foot positions, so you can measure
auto-calibration error in metres by range, separate the foot-definition floor from the
calibration error, and dial in bumps, distortion and slopes one at a time. *Red flag:* claiming
sim numbers are site numbers — batch_v8 is flat and undistorted.

---

## References

1. **29_CAMERA_GEOMETRY_CALIBRATION.md** (this repo) — Zhang, CityFlow 11.52 px, WILDTRACK, error
   propagation, PTZ model, with its own verified references.
2. J. Sochor, R. Juránek, A. Herout, "Traffic Surveillance Camera Calibration by 3D Model Bounding
   Box Alignment for Accurate Vehicle Speed Measurement," CVIU. https://arxiv.org/abs/1702.06451 [V]
3. V. Kocur, M. Ftáčnik, "Traffic Camera Calibration via Vehicle Vanishing Point Detection,"
   ICANN 2021. https://arxiv.org/abs/2103.11438 [V]
4. A. G. Jain, N. Saunier, "Autocamera Calibration for traffic surveillance cameras with wide
   angle lenses." https://arxiv.org/abs/2001.07243 [V]
5. K. Vuong, R. Tamburo, S. G. Narasimhan, "Toward Planet-Wide Traffic Camera Calibration,"
   WACV 2024. https://arxiv.org/abs/2311.04243 [V]
6. A. Veicht, P.-E. Sarlin, P. Lindenberger, M. Pollefeys, "GeoCalib: Learning Single-image
   Calibration with Geometric Optimization," ECCV 2024. https://arxiv.org/html/2409.06704 [V]
7. R. Wagner, D. Crispell, P. Feeney, J. Mundy, "4-D Scene Alignment in Surveillance Video."
   https://arxiv.org/abs/1906.01675 [V]
8. Z. Tang et al., "Multiple-Kernel Based Vehicle Tracking Using 3D Deformable Model and Camera
   Self-Calibration," AI City Challenge 2017. https://arxiv.org/abs/1708.06831 [V]
9. Y. Hold-Geoffroy et al., "A Perceptual Measure for Deep Single Image Camera Calibration,"
   CVPR 2018. https://arxiv.org/abs/1712.01259 [V abstract; no numbers quoted]
10. G. Brouwers, M. Zwemer, R. Wijnhoven, P. de With, "Automatic Calibration of Stationary
    Surveillance Cameras in the Wild," ECCV 2016 Workshops, doi 10.1007/978-3-319-48881-3_52
    (Crossref metadata) [V title/venue; results A]
11. F. Lv, T. Zhao, R. Nevatia, "Camera Calibration from Video of a Walking Human," IEEE TPAMI
    2006 [A — not fetched; Semantic Scholar 429 and dblp bot-wall again on audit 2026-09-27].
12. J. Liu, R. T. Collins, Y. Liu, "Surveillance Camera Autocalibration based on Pedestrian Height
    Distributions," BMVC 2011 [A — not fetched; bmva.org proceedings page empty/404 on audit].
13. H39 results: `out/experiments/h39_autocalib/results.json`, docs/research/32 §H39 [V].
