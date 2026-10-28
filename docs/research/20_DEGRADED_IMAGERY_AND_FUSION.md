# 20 · Degraded Imagery & Multi-Sensor Fusion — sensor models, robustness, and consistent simulation

*Series 17–23. R04 (imaging chain physics, quantified degradation, synthetic
data) and R05 (RF/audio/radar/DAS, fusion methods) are the literature reviews.
This report designs the production robustness and fusion layers and specifies
how SurvSim must simulate each sensor so that all sensors agree about one
world.*

**Sourcing conditions.** 2026-09-26; no GPU/engine. Repo numbers from docs/11
and docs/15. External figures recalled from primary sources and not
re-fetched were checked in a second pass (2026-09-26) and are cited as [n] to the numbered References; figures that could not be confirmed were removed. **[BOE]** arithmetic, **[INF]** inference, **[lore]**
practitioner knowledge.

---

## 0. Summary

1. **Train for degradation; do not pre-process it away.** R04: dehazing and
   low-light enhancement frequently *hurt* un-retrained detectors.
   Degradation-aware training plus a per-camera quality signal wins.
2. **Quality is an output.** Every camera publishes an image-quality vector
   (sharpness, noise, exposure, blockiness, scene-change) and a health state;
   alarm policy conditions on it (report 17 §3.2).
3. **Tamper is a behaviour and a sensor state at once.** SurvSim's 6 tamper
   kinds in `survsim/director/camera_director.py` (`TAMPER_KINDS = cover, spray, tilt, unplug, glare, defocus`) drive both the image (degrade)
   and the ground truth (the tampered camera no longer matches its calibration;
   a blinded one emits nothing — principle 2).
4. **Fusion is mostly decision-level with explicit correlation handling.** Most
   real fusion in security is "camera confirms radar/fence/RF cue" — late
   fusion with gating. Feature-level fusion is research. The biggest error in
   fused systems is assuming nuisance sources are independent (`eval/fusion.py`
   penalises correlated nuisances, docs/11).
5. **One world, many sensors.** The simulator's job is consistency: the same
   person, at the same position and time, drives the camera pixels, the RF
   emissions of their phone, the footsteps and voice in the audio, and the
   radar return. Independent random generators per sensor produce fusion
   results that are artefacts.

---

## 1. The CCTV imaging chain and its degradations

R04 §1 walks the chain in physics terms: scene radiance → atmosphere → lens
(MTF, flare, dirt, distortion) → sensor (photon shot noise, read noise, dark
current, FPN, rolling shutter) → ISP (demosaic, AE/AWB, denoise, sharpen, WDR
tone-mapping, gamma) → encoder (H.264/H.265, GOP, rate control) → network
(loss, jitter) → VMS (transcode, storage). SurvSim's `sensors/degrade.py`
models that chain with profiles (`cctv_day_720p`, `cctv_legacy_sd`,
`cctv_night_ir`, plus others: 5 profiles in total per docs/11), including
effects added in docs/15: camera automatics (AE/AWB drift), rolling exposure,
dark-flat quantisation, correlated grain, per-camera FPN, lens dirt, and a
batched-GOP H.264 codec.

### 1.1 Calibration status (docs/15)

On 60 frames of real UE street renders:

| Profile | stats in real band (of 14) | Notable misses |
|---|---|---|
| `cctv_day_720p` | 6 | noise_sigma 0.391 (band 0.278–0.353), lap_var high, temporal_noise 9.46 vs 1.57–2.93 |
| `cctv_legacy_sd` | 9 | mtf_ratio, edge_width, rms_contrast, luma_skew, temporal_noise |
| `cctv_night_ir` | 3 | scored against a *day* band — no real night/IR reference yet |

The spatial imaging-chain stats for `cctv_day_720p` pass in the pytest fixture;
temporal noise is an accepted, documented miss, partly because the real band
was measured from per-frame JPEG sequences (docs/15 caveat). Degradation costs
0.567 s/frame at 720p (target 0.3 s not reached).

**Implication for product work [INF]:** SurvSim's day profile is good enough
for detector robustness stress tests at the spatial level; night/IR
conclusions should not be drawn until a real IR reference set exists; temporal
models (trackers' sensitivity to flicker, codec smear) should be validated on
real video.

---

## 2. Degradation by condition — what breaks and what to do

### 2.1 Low light and night

* **Colour cameras at night**: high gain → noise, slow shutter → motion blur,
  aggressive temporal noise reduction → ghosting of moving people [lore].
  Detector recall on dark footage falls sharply; ExDark (Loh & Chan, CVIU 2019,
  https://github.com/cs-chan/Exclusively-Dark-Image-Dataset) and NightOwls
  (Neumann et al., ACCV 2018, https://www.nightowls-dataset.org/) are the public night benchmarks: ExDark has
  7,363 low-light images in 12 classes across 10 illumination types [1];
  NightOwls has 279k fully annotated night frames in 40 sequences from 3
  countries, with five pedestrian baselines (ACF, Checkerboards, Faster R-CNN, RPN+BF, SDS-RCNN) [2]. (An
  earlier draft claimed a specific "tens of AP points" night drop; no source
  confirming a single figure was found, so it is withdrawn.)
* **IR-illuminated (near-IR, 850 nm) mode**: monochrome, strong vignetting
  from the illuminator's beam, **hot-spotting** of near objects and
  **insects/rain/spider webs near the lens lit brightly** — the single most
  famous CCTV nuisance source [lore; H01]. Range limited by illuminator (typ.
  20–50 m for built-in LEDs).
* **Day/night switch** (IR-cut filter flip) produces a brightness step that
  naive motion detection sees as scene change → false tamper alarm [lore].
* **Mitigations**: train on night/IR data (synthetic helps most where real
  labelled night data is scarce — R04); per-mode thresholds; disable colour
  attributes in IR mode; temporal persistence against insects; IQA-aware
  suppression.
* **SurvSim needs**: IR illuminator model with inverse-square falloff and beam
  pattern; near-lens particles (insects, raindrops) lit by the illuminator;
  day/night switch events; a real IR reference set for docs/15-style
  calibration (open gap).

### 2.2 Thermal (LWIR)

SurvSim `sensors/thermal.py` has emissivity, thermal crossover and Johnson
criteria, and fixed a bug where a cheap core claimed person detection at 800 m
where a person subtends under one pixel (docs/11 bug 11). Johnson criteria
(Johnson 1958: detection ≈ 1 ± 0.25 line pairs, recognition 4 ± 0.8,
identification 6.4 ± 1.5 line pairs across the target's critical dimension, at
50 % observer probability; security vendors usually restate these as ~1.5 / 6 /
12 *pixels*, the convention in `JOHNSON_PIXELS = {detect: 1.5, recognise: 6.0,
identify: 12.0}` in `survsim/sensors/thermal.py`) [3]. The in-code values are
the vendor pixel convention and are optimistic relative to Johnson's original
line-pair figures (1 lp ≈ 2 px) — deliberate, to match how datasheets quote
DRI ranges translate to ranges: for a 640×512 core with
17 µm pitch and 25 mm lens, IFOV = 0.68 mrad; a 0.75 m target covers 1.5 px
(vendor "detect") at ~735 m and 3 px at ~370 m [BOE: 0.75 / (3 × 0.68e-3) ≈ 368 m]. Thermal crossover (dawn/dusk,
when people and background are at equal apparent temperature) and hot
backgrounds (sun-heated tarmac) are the failure modes.

### 2.3 Weather

* **Rain**: streaks and lens droplets (the latter far more damaging on domes);
  reduced contrast; wet-surface reflections → phantom people [lore].
* **Fog/haze**: Koschmieder contrast attenuation `C = C0·e^(−βd)`; visibility
  V ≈ 3.912/β. At V = 200 m, a person at 100 m keeps e^(−3.912×0.5) ≈ 14 % of
  contrast [BOE].
* **Snow**: moving flakes near the lens are large bright blobs, especially
  under IR.
* **Wind**: camera shake (pole masts), moving vegetation and shadows —
  the classic motion-based false alarm; deep detectors are much better, but
  wind shake still breaks trackers and zone projections.
* Datasets: Foggy Cityscapes — 20,550 synthetic-fog images; Sakaridis, Dai &
  Van Gool (IJCV 2018) report that supervised training on it "significantly
  improves" segmentation on 101 real foggy images (Foggy Driving) [4]; ACDC —
  8,012 images (4,006 adverse: fog, night, rain, snow, each paired with a
  normal-condition counterpart) [5]. Both are driving datasets; the
  transferable lesson is that synthetic-fog pre-training helps on real fog.

### 2.4 Compression and transport

At CRF ≈ 28–34 (typical of CCTV storage streams), small people lose texture;
ReID suffers before detection does [INF from R04]. GOP structure produces
temporal pumping (quality jumps at I-frames) and smear under motion. Packet
loss yields grey/green block corruption spreading until the next I-frame.
Mitigations: analyse the primary stream if bandwidth allows; request higher
bitrate on analytics streams; train with codec augmentation (SurvSim's
batched GOP codec is exactly this augmentation, docs/15); detect corruption in
IQA and drop frames rather than infer on them.

### 2.5 Optics and mounting

Out-of-focus after maintenance, dirty domes, spider webs, sun glare at low
sun, lens flare from street lights, wide-angle distortion at frame edges, and
**mounting too high** (steep angles → head-top views that COCO detectors
under-recall). SurvSim models defocus, lens dirt, distortion (matched to
OpenCV), glare tamper.

---

## 3. Camera tamper and image-quality analytics

### 3.1 Tamper taxonomy (SurvSim's 6 kinds plus stream loss)

| Kind | Image signature | Detection method | Common false triggers |
|---|---|---|---|
| cover (hand, bag, tape) | abrupt loss of edges, dark/uniform | edge-energy drop vs reference, histogram collapse | night switch, lights off |
| spray (paint) | gradual blur/colour cast, edges fade | sharpness trend, colour stats | fog, condensation |
| tilt / redirect | scene change with preserved sharpness | keypoint match vs reference image; homography estimation | PTZ moves, large vehicles parking |
| defocus (lens turned / smeared) | global sharpness loss, edges stay in place | Laplacian-variance / MTF drop vs reference | fog, condensation, IR focus shift at night |
| glare (laser/torch) | saturation region | clipped-pixel fraction | sun, headlights |
| unplug | stream loss + ONVIF event | ingest | power cycling |

The literature uses exactly these features. Ribnick et al. (AVSS 2006)
compare a buffer of older frames with recent ones using three dissimilarity
measures [6]; Saglam & Temizel (AVSS 2009) use adaptive background subtraction
and an "edge disappearance rate" against an adaptive threshold to detect moved,
defocused and covered cameras [7]; a 2023 survey reviews the feature types
[8]. A cable cut is not an image tamper — it is a stream-loss event for the
ingest supervisor (report 17 §3.1), covered by SurvSim's `unplug`. Modern practice adds a learned classifier on IQA
features, and — critically — **temporal persistence** (require ≥ 5–20 s).

### 3.2 Why tamper belongs in analytics, not maintenance

A camera that is tilted keeps producing plausible video: detections, tracks,
zone events — in the wrong place. Principle 2 in SurvSim is the production
rule: when the live camera no longer matches its configuration, stop trusting
its geometry-dependent outputs, alarm on the camera, and tell the operator
which zones lost coverage (`survsim rig` can compute the coverage loss).

### 3.3 What SurvSim must emit

Per camera per frame: tamper state (kind, onset, severity), configured vs
actual pose, and the IQA stats (docs/15 set). Paired negatives: night switch,
maintenance cleaning (hand near lens), heavy rain on dome, PTZ moves, large
vehicles occluding. `maintenance` is already the tamper hard negative in
docs/03.

---

## 4. Non-visual sensors

### 4.1 RF: Wi-Fi / BLE / cellular presence

R05 §2 covers the physics. Key facts for design:
* **MAC randomisation** (iOS 14+, Android 10+) breaks naive device counting and
  tracking across sessions; probe requests are rarer on modern phones [R05].
  SurvSim's RF module models MAC randomisation (docs/11).
* **RSSI → range** via log-distance path loss `RSSI(d) = P0 − 10·n·log10(d/d0)
  + X_σ`, with exponents from ~2 (free space) to ~4–5 in cluttered buildings, and log-normal
  shadowing σ commonly 4–10 dB [9] [textbook ranges; the specific BLE exponent
  and CI an earlier draft cited to [10] were not found in that paper — [10] is an
  outdoor ZigBee particle-filter study — so they are withdrawn]. SurvSim's `survsim/sensors/rf.py` defaults are
  `PATH_LOSS_EXPONENT = 2.8`, `SHADOWING_SIGMA_DB = 4.0`, `RSSI_AT_1M_DBM =
  -40`, sniffer sensitivity −92 dBm — the optimistic end of the range. At σ = 6 dB and n = 3, a single RSSI gives a range error
  factor of 10^(6/30) ≈ 1.6× (±60 %) [BOE]. RF localises to "zone", not
  "metre".
* **Value**: presence corroboration in sterile zones (nobody should be there
  with a phone at 3 am), device-to-track association over time (the RF
  signature that co-moves with a visual track), counting in crowds.
* **Legal**: capturing device identifiers is personal data (GDPR/UK GDPR);
  hashing with rotating salts and aggregation is the usual mitigation (report
  21).

### 4.2 Radar

Perimeter radars (FMCW, 9–24 GHz and 77 GHz) detect walkers at hundreds of
metres to kilometres, day/night, in fog/rain, with range/azimuth/velocity.
Published walker ranges: SpotterRF C550 ~850 m, vehicles 1.5 km (C550-EXT
longer; secondary sources say ~950 m for people [unverified]) [11];
Navtech AdvanceGuard radars HDR134/200/300/351 are quoted at up to
0.3/1/3/5 km instrumented range (person-specific range not on the product
page) [12]; Echodyne EchoGuard quotes < 1° azimuth accuracy and range accuracy
< 3.25 m, but no walker/drone range figures on its product page [13].
Weaknesses: vegetation and animals, multipath near structures; classification
of person vs animal by micro-Doppler is imperfect. **Radar + PTZ slew-to-cue**
is the classic perimeter architecture (R05, D04).

### 4.3 Perimeter intrusion detection systems (PIDS) and DAS

Fence-mounted sensors (vibration, taut-wire, fibre DAS) detect climbing and
cutting along segments; nuisance from wind, rain, wildlife, traffic vibration.
In the UK, NPSA (formerly CPNI) runs functional evaluation schemes for PIDS;
passing products receive a CLASS rating and are listed in the Catalogue of
Security Equipment (CSE) [14]; the NPSA/Home Office *Guide to PIDS* describes
the technologies and their nuisance sources [15]. SurvSim's
`fence_cut` and `climb_attempt` behaviours need a fence-sensor model
(segment, vibration signature, wind-correlated nuisance) — not built yet.

### 4.4 Audio

R05 §3: the highest-value, highest-controversy sensor. Detectable events:
gunshot, glass break, screaming, shouting/aggression, alarms, vehicle crashes.
SurvSim's audio module models SPL, direction-of-arrival error and named
nuisance sources (docs/11). Physics: spherical spreading −6 dB per doubling of
distance plus air absorption; a shout or scream is ~80–90 dB SPL at 1 m (record screams exceed 120 dB) —
SurvSim uses `SOURCE_LEVELS_DB["shout"] = 88` in `survsim/sensors/audio.py` —
so ~48 dB at 100 m [BOE: −40 dB for 100×, before the module's 0.05 dB/m
absorption], below typical urban background [lore: 55–70 dB(A)]. Datasets: AudioSet (2,084,320 human-labelled 10-s YouTube clips, 527
classes; Gemmeke et al., ICASSP 2017) [16], UrbanSound8K (8,732 clips ≤ 4 s,
10 classes incl. gun_shot and children_playing; Salamon et al., ACM MM 2014)
[17], and the DCASE challenges [18]. Legal: recording
*conversation* is far more intrusive than detecting events; on-device event
classification with no audio retention is the defensible design (report 21).

### 4.5 Access control and other context feeds

Badge events, door contacts, intercom, alarm panels, ANPR. These are the
highest-precision corroborators available and the cheapest to integrate via
the PSIM/VMS. Tailgating fundamentally requires them (report 19 §2.2).

---

## 5. Fusion architecture

### 5.1 Levels

| Level | Example | When |
|---|---|---|
| Data/raw | pixel-level RGB+thermal fusion | co-located, co-registered sensors; research-grade |
| Feature | radar tracks + visual detections into one tracker state | shared ground plane, synchronised clocks |
| Track | associate radar track with visual track; RF device with visual track | the practical workhorse |
| Decision | alarm = camera-loiter AND RF-presence; or weighted voting | most deployed systems |

Standards/frameworks: the JDL data fusion model levels 0–4 (Steinberg, Bowman
& White, "Revisions to the JDL data fusion model", SPIE 1999) [19]; SAPIENT —
MOD-owned, developed with Dstl and Innovate UK, interface control document
published as BSI Flex 335 (v2.0, 2024), Protobuf messages since v7 (≈ 60 %
less bandwidth than XML), adopted by MOD for counter-UAS and evaluated as a
potential NATO standard, proto files on GitHub [20][21] — is directly relevant to UK defence buyers — a fusion
node that speaks SAPIENT is a procurement advantage [INF; R05, D04].

### 5.2 Track-level fusion design

1. Common ground-plane coordinates and clock (report 17 §4).
2. Per-sensor track with covariance (camera: from calibration error budget,
   report 18 §4.3; radar: range/azimuth accuracy; RF: zone-level).
3. Gated association (Mahalanobis distance) with JPDA/MHT or simpler global
   nearest neighbour; RF associates by co-movement over minutes, not per frame.
4. Fused state with provenance: which sensors support this track.

### 5.3 Decision-level fusion and correlated nuisances

Independent Poisson false-alarm streams f1, f2 coincide within ±W at rate
≈ 2·f1·f2·W — the expression `fuse(mode="and")` in `survsim/eval/fusion.py`
implements: two sensors at 1 FA/h each with W = 30 s yield
2 × 1 × 1 × (30/3600) ≈ 0.017 FA/h — a 60× reduction.
**If** the nuisances share a cause (wind moves the fence and the trees on
camera; rain triggers audio and vision), the reduction collapses toward f1.
SurvSim's `eval/fusion.py` includes a correlated-nuisance penalty (docs/11);
the simulator must therefore drive *shared causes* (weather, wildlife, traffic)
into all affected sensors from one weather/world state.

### 5.4 Learned fusion

Bayesian/Dempster–Shafer combinations and learned late-fusion classifiers
(gradient-boosted trees on per-sensor features) are practical; deep multimodal
fusion needs synchronised multimodal training data which barely exists for
security — SurvSim can generate it, which is a genuine differentiator [INF].

---

## 6. Simulating sensors consistently

### 6.1 Principles

1. **Single world state** — positions, poses, device carriage, voice/footstep
   emitters, weather, lighting, wildlife — produced by the Director each tick.
2. **Sensors are pure functions of world state + their own noise RNG** (seeded
   per subsystem via `RngHub`, principle 6), so reruns agree and noise is
   independent where physics says so.
3. **Shared causes are shared inputs**: wind speed drives fence vibration,
   vegetation motion in the render, camera shake and audio wind noise.
4. **Each sensor has an explicit visibility/detectability model with the same
   rigour as `usably_visible`**: RF (link budget ≥ receiver sensitivity),
   audio (SNR ≥ threshold at the mic), radar (RCS, range, clutter), thermal
   (Johnson/pixels on target).
5. **Clock models per sensor** (offset, drift, latency) — fusion is extremely
   sensitive to timing.

### 6.2 Per-sensor model checklist

| Sensor | Must model | SurvSim state |
|---|---|---|
| Visible camera | imaging chain, codec, tamper | done, calibration partial (docs/15) |
| Near-IR night | illuminator falloff, hot-spot, near-lens particles, mono | profile exists; illuminator/particles partial; no real reference |
| Thermal | emissivity, crossover, resolution limit | done (docs/11) |
| RF | MAC randomisation, path loss + shadowing, probe rates, device carriage | done (docs/11) |
| Audio | SPL, spreading, DOA error, nuisance classes | done (docs/11) |
| Radar | range/azimuth/velocity noise, RCS, clutter, micro-Doppler class | **not built** |
| Fence/DAS | segment, event signature, wind/wildlife nuisance | **not built** |
| Access control | badge events per door, tailgating truth | exists as sensor extra (docs/02) |

### 6.3 Validation of sensor models

Each simulated sensor needs a real reference in the style of docs/15: RSSI
distributions vs distance from a site survey; audio event SNR at distances;
radar detection probability vs range from vendor test data; IR frames for the
night profile. Without them, fused results are self-consistent but not
realistic (the docs/11 "realism targets that were wrong" lesson, bug 7).

---

## 7. Evaluation of robustness and fusion

* **Degradation curves**: Pd and FA/camera-hour vs profile and severity (CRF,
  fog visibility, illuminator power), with matched scenarios so only the
  imaging changes.
* **Condition-stratified reporting**: never report a single number across
  day/night.
* **Tamper**: time-to-detect per kind, false tamper alarms per camera-day on
  negative conditions.
* **Fusion**: FA reduction factor vs single-sensor at equal Pd, split by
  nuisance cause; Pd loss from requiring corroboration (a missed corroboration
  loses a true event).
* **Timing**: fused alarm latency vs slowest sensor.

---

## 8. Recommendations

1. Build a real night/IR reference set (even 200 frames from public CCTV
   footage with permissive licences) before claiming anything about night.
2. Make IQA a product feature using `survsim/realism/stats.py` features.
3. Implement radar and fence-sensor models driven from the same weather and
   wildlife state as vision; wildlife agents (fox, deer, birds) are the
   highest-value missing negatives for perimeter work.
4. Evaluate fusion with correlated nuisances by construction.
5. Add SAPIENT-compatible message export for UK defence customers.

## 9. A degradation-aware training recipe

Concrete augmentation ranges for a CCTV person detector [INF, anchored to the
docs/15 real-band statistics and R04]:

| Stage | Parameter | Range | Anchor |
|---|---|---|---|
| Optics | defocus Gaussian σ | 0.5–1.5 px at 720p | edge_width real median 6.06 px |
| Optics | lens dirt / smear | 0–30 % of frames, low alpha | lore |
| Sensor | read noise + shot noise → noise_sigma | 0.25–0.45 | real band 0.278–0.353 |
| Sensor | correlated grain | σ 0–3 | `cctv_day_720p` grain_sigma 3.0 |
| ISP | gamma / AE drift | ±0.3 EV, slow drift | `camera_automatics` |
| ISP | denoise + sharpen | as profiles | halos at edges |
| Codec | H.264 CRF | 24–36, GOP 8–50, bf 0–2 | profiles use CRF 29/34/30 |
| Codec | packet-loss corruption | 0–2 % of GOPs | lore |
| Frame rate | analysis fps | 2–25 | tracking cliff ~3 fps (R01) |
| Night | IR mono + illuminator falloff | 30–50 % of night samples | `cctv_night_ir` |
| Weather | fog visibility V | 100–2,000 m | Koschmieder |
| Weather | rain streaks / lens droplets | 0–20 % of frames | ACDC-like |
| Geometry | resolution | 480p, 720p, 1080p, crops of 4K | site mix |

Two rules: (1) augment on the **real** training data too, not only synthetic,
so the model cannot use "is degraded" as a domain cue for "is synthetic";
(2) keep a clean held-out real set and a degraded held-out real set, and
require no regression on the clean one [INF].

## 10. Worked example — perimeter at night

A 1.2 km substation fence; 6 fixed thermal cameras (640×512, 25 mm), 2 PTZ
visible/IR cameras, one 24 GHz radar covering the approach, fence DAS.

1. Radar detects a walker at 400 m (Pd ≈ 0.9 per scan at that range for a
   person-class radar [INF]); nuisance: deer, vegetation.
2. Radar track gates the nearest thermal camera: at 400 m a person is ~2.8 px
   wide on this core [BOE, §2.2: 3 px at ~370 m] — detection-level only.
3. PTZ slews to cue (≤ 2 s budget, report 17); at 250 mm-equivalent zoom the
   person is ~100 px tall → recognition-level, human confirms.
4. DAS registers climbing on segment 14; coincident with the radar track's
   position ± 20 m within 30 s → fused high-priority alarm.
5. Correlated nuisance check: high wind raises DAS nuisance and radar
   vegetation clutter together; a fused rule requiring radar+DAS in wind
   > 10 m/s must re-estimate its FA rate — the coincidence arithmetic in §5.3
   no longer holds. The camera (thermal) is the only uncorrelated channel.

SurvSim coverage of this scenario: behaviours (`perimeter_probe`,
`climb_attempt`, `fence_cut`), thermal model, PTZ director, scenario template
`border_fence_night_probe` (docs/03 §5) exist; radar and DAS models and
wildlife agents do not (report 23).

## 11. Fusion failure modes

| Failure | Cause | Symptom | Mitigation |
|---|---|---|---|
| Timing misalignment | unsynchronised clocks, sensor latency | coincidences missed, spurious pairs | PTP/NTP, per-sensor latency calibration, widen W with care |
| Coordinate misregistration | camera calibration error (report 18 §4), radar boresight | wrong track pairing | joint calibration with a walked target; residual monitoring |
| Correlated nuisance | shared cause (wind, rain, traffic) | FA reduction far below predicted | model causes; condition fusion on weather |
| Single-sensor dominance | one sensor always fires | fusion degenerates to that sensor | per-sensor FA monitoring |
| Corroboration-induced misses | second sensor has blind areas | true events dropped | coverage-aware rules (require corroboration only where coverage exists) |
| RF association drift | MAC randomisation mid-track | identity splits | associate on co-movement windows, not MAC persistence |
| Audio privacy breach | continuous recording | legal exposure | on-device event classification, no retention |

## 12. Open research questions for SurvSim

1. How much of the night-time detection gap closes with synthetic IR pre-
   training once a real IR reference set exists to calibrate `cctv_night_ir`?
2. What is the realistic FA-reduction factor of camera+RF fusion when phones
   randomise MACs, measured against a simulated population whose device
   carriage and randomisation settings follow published market shares?
3. Can IQA features (docs/15 set) predict per-frame detector recall well
   enough to drive dynamic thresholds? SurvSim can generate paired
   (IQA, recall) data at scale.
4. Does training with the batched-GOP codec (temporal artefacts) improve
   tracking on real compressed video more than per-frame intra codec
   augmentation?

---

## 13. Worked examples on SurvSim's own scenarios

### 13.1 `configs/scenarios/disguise_and_tamper.yaml`

240 s at 10 fps on a 60 × 60 m compound; four cameras: `cam_gate` (1080p,
70° HFOV, 4.5 m), `cam_yard` (720p dome, 95°, 5 m), `cam_sub` (1080p, 60°,
4 m, **sprayed at t = 150 s**) and `cam_ptz` (1080p, 3–60° HFOV, 9 m mast,
40 °/s, patrolling gate → fence → substation presets with 20 s dwells). Zones
include a restricted substation (roles worker/guard allowed), a north
perimeter fence with a cuttable panel `fence_seg_12`, and `zone.blindspot_A`,
verified unobserved by `survsim rig` so the outfit change is genuinely unseen.

What each layer of this report must do on it:

1. **Tamper, t = 150 s.** `CameraDirector.tamper("cam_sub","spray",150)`
   sets `CameraState.tamper = "spray"`, `tamper_since_s = 150`. Spray is *not*
   `blind` (only cover/unplug are, per `CameraState.blind`), so GT keeps
   emitting boxes but the degrade stage smears the image. The correct product
   behaviour is: sharpness (`lap_var_log10`) falls over several seconds, the
   IQA tamper classifier fires with persistence ≥ 5 s, a *camera* alarm is
   raised, and every substation-zone rule is flagged "coverage degraded". The
   scoring question SurvSim can answer and real data cannot: how many GT boxes
   in `cam_sub` after t = 150 s were still detectable (≥ 20 px, principle 5)
   versus how many the detector found — i.e. *how blind is a sprayed camera?*
2. **PTZ coverage.** The fence is only watched while `cam_ptz` sits on its
   fence preset (20 s of each ~70 s cycle incl. slews at 40 °/s). An intruder
   probing the fence has roughly a 30 % chance of being in view at any instant
   [BOE: 20 s / (3 × 20 s + slew time ≈ 66 s)]. This is exactly where a fence
   sensor earns its keep: with DAS on `fence_seg_12`, a climb raises a cue and
   the PTZ slews-to-cue instead of patrolling. The fused test is:
   Pd(fence event) with PTZ patrol only vs with DAS→PTZ cue.
3. **Night variant.** Re-running the scenario through `cctv_night_ir` (mono,
   `iso_gain=11`, `motion_px=5`, `grain_sigma=0.3`) should reduce detector
   recall at the far fence; the report's claim "night conclusions are
   uncalibrated" (§1.1) applies — publish the number only as synthetic-only.
4. **Fusion.** With channels `SensorChannel("camera_intrusion", p_detect=0.85,
   false_alarms_per_hour=0.5)` and `SensorChannel("das_fence", 0.9, 2.0)`,
   `fuse(mode="and", window_s=30)` gives Pd = 0.765 and, at correlation 0, FA
   ≈ 2 × 0.5 × 2 × 30/3600 ≈ 0.017/h; at correlation 0.5 (wind drives both),
   ≈ 0.5 × 0.017 + 0.5 × 0.5 = 0.258/h — fifteen times worse, and the module
   adds its "verify independence on site" note above 0.3 [arithmetic from the
   function's formula; channel numbers are illustrative].

### 13.2 `configs/scenarios/street_crowd.yaml`

60 s at 10 fps, 18 generated people around a loiterer (`loiterer_1`, 25 s
pace at `zone.gate_A`, radius 2.5 m) and a `commute_wait` hard negative; three
720p cameras at 3.5–5 m, 15–30° down, 70–95° HFOV, so people are 60–200 px
tall. This is the scene behind docs/15's realism numbers
(`out/batch_v1/street_crowd_day/render/cam_02`, `cctv_day_720p` 6/14 stats in
band, `temporal_noise` 9.46 vs band 1.57–2.93).

Uses in this report's scope:

* **Codec robustness experiment.** Degrade the same render with
  `crf ∈ {24, 29, 34}` and `gop ∈ {8, 25, 50}` via `apply_sequence` and score
  ReID rank-1 of the loiterer vs the hard negative across the three cameras.
  Hypothesis (report 18, R04): ReID degrades before detection as CRF rises.
* **Audio corroboration.** Put an `AudioSimulator` with one array microphone
  at the gate; ambient rises by `crowd_ambient_gain_db = 6` dB per doubling
  of crowd size, so with 18 people ambient is ≈ 35 + 6·log2(18) ≈ 60 dB
  [BOE]. A shout (88 dB at 1 m) from 10 m arrives at ≈ 68 dB — SNR ≈ 8 dB,
  just over `detection_threshold_snr_db = 6`, and DOA error scales by 20/8,
  i.e. σ ≈ 7.5° from the 3° baseline (`doa_error_deg`). At 20 m the shout
  falls below threshold. So in a busy plaza audio corroborates only nearby
  events — a quantitative limit worth stating in bids.
* **RF counting.** With 18 people carrying Wi-Fi emitters that randomise MACs
  every 300 s (`Emitter.rotate_every_s`), a 60 s run barely sees a rotation;
  run it for 1 h and `RfSimulator.overcount_ratio()` shows how badly naive MAC
  counting over-counts a stable crowd.

## 14. Interfaces — messages and config keys

### 14.1 Degradation profile (as implemented)

`survsim/sensors/degrade.py::Profile` fields, grouped by imaging stage:

| Stage | Keys |
|---|---|
| geometry | `resolution`, `k1`, `k2` (barrel), `vignette`, `chroma_px` |
| optics | `defocus`, `motion_px`, `motion_angle`, `haze`, `dirt` |
| exposure/ISP | `ev`, `gamma`, `ae_target`, `auto_levels`, `ae_drift_ev`, `awb_drift`, `drift_period_s`, `wb_gains`, `rolling`, `denoise`, `sharpen` |
| sensor | `iso_gain`, `read_noise`, `fpn`, `hot_pixels`, `grain_sigma`, `night_ir` |
| codec | `crf`, `codec_scale`, `dark_flatten`, `gop`, `bf`, `fps` |
| overlay | `osd`, `osd_text` |

Named profiles: `clean`, `cctv_day_720p` (crf 29, gop 8, bf 0,
grain_sigma 3.0), `cctv_legacy_sd` (704×576, crf 34, codec_scale 0.75),
`cctv_night_ir` (night_ir, iso_gain 11, motion_px 5), `cctv_fog_day`
(haze 0.45, crf 32). Entry points: `apply_profile(img, profile, depth, seed,
camera, frame_index, ...)` and `apply_sequence(frames, profile,
sequence_seed, ...)`. A production augmentation library should use the same
keys so that "trained on profile X" is a reproducible statement.

### 14.2 Camera health message (proposed, extends `CameraState.as_dict`)

```json
{"t": 150.0, "camera": "cam_sub", "yaw": 180.0, "pitch": -15.0, "hfov_deg": 60.0,
 "tamper": "spray", "blind": false, "tamper_since_s": 150.0,
 "iqa": {"lap_var_log10": 1.41, "noise_sigma": 0.33, "blockiness": 1.12,
         "luma_mean": 61.0, "scene_change": 0.08},
 "calibration_valid": true, "coverage_lost_zones": ["zone.substation"]}
```
`iqa` keys are the docs/15 statistics from `survsim/realism/stats.py`;
`calibration_valid` becomes false on `tilt`; `coverage_lost_zones` comes from
the rig analysis.

### 14.3 Non-visual sensor observations (proposed common envelope)

```json
{"sensor_id": "mic_gate", "kind": "audio", "t": 32.4, "clock_offset_s": 0.02,
 "event": "shout", "level_db": 68.1, "snr_db": 8.1, "bearing_deg": 41.7,
 "bearing_sigma_deg": 7.5,
 "gt": {"source_uid": "p_07", "is_nuisance": false, "true_bearing_deg": 44.0}}
```
RF: `{"kind":"rf","proto":"wifi_probe","mac":"…","rssi_dbm":-71.3,
"gt":{"uid":…,"distance_m":…}}`; radar: `{"kind":"radar","track_id":…,
"range_m":…,"azimuth_deg":…,"radial_mps":…,"class":"person|vehicle|animal",
"gt":{…}}`; fence/DAS: `{"kind":"das","segment":"fence_seg_12",
"position_m":…,"energy":…,"gt":{"cause":"climb|wind|animal"}}`. The `gt`
block is stripped for inference and kept for scoring. Mapping these to SAPIENT
Protobuf `DetectionReport`/`StatusReport` messages [21] is the route to UK
defence integration.

## 15. Vendor landscape — public specifications

| Category | Product | Public spec | Price (public) |
|---|---|---|---|
| Thermal camera | Axis Q1961-TE | 384×288 uncooled, max output 768×576, NETD 40 mK, 7/13 mm, 8.3 or 30 fps [22] (pixel pitch not re-confirmed) | not listed publicly (reseller quote) |
| Thermal camera | Hikvision DS-2TD2167 series | 640×512 VOx, 17 µm, NETD ≤ 35 mK, 6.5–35 mm variants [23] [unverified: page did not load] | reseller |
| Thermal camera | Teledyne FLIR FC-Series AI | 640×512, NETD < 25 mK, onboard DNN human/vehicle classification, 8 lenses 7.5–75 mm, 8.6°–90° HFOV [24] | reseller |
| Perimeter radar | SpotterRF C550 | walker ~850 m, vehicle 1.5 km; C550-EXT longer [11] | reseller |
| Perimeter radar | Navtech AdvanceGuard | models to 0.3 / 1 / 3 / 5 km range [12] | project pricing |
| Radar (C-UAS/ground) | Echodyne EchoGuard | az. < 1°, range acc. < 3.25 m; ranges not on product page [13] | project pricing |
| Fibre fence sensor | Senstar FiberPatrol FP1150 | locates to ±4 m, up to 80 km per processor [25] | project pricing |
| Fibre fence sensor | Senstar FiberPatrol FP400 | 4 zones × 300 m per processor [25] | project pricing |
| Audio analytics | Sound Intelligence (aggression, gunshot, glass) | runs on Axis cameras/mics [26] (an "Axis ≈ 90 % of sales" figure could not be confirmed [unverified]) | licence per device |
| Audio analytics | Axis Audio Analytics | edge detection of screams, shouts, glass break; streams metadata, not audio [28] | bundled |
| Microphone | Louroe DigiFact A (LE-870) | IP ceiling mic, > 30 ft coverage, analytics suite [29] | ~$524–530 new retail (B&H / distributors, 2026-09); ~$366 was a used eBay listing [29] |

**The field evidence for audio is sobering.** ProPublica (2019) tested a
Louroe Digifact A running Sound Intelligence's aggression detector with 40
students (26 in Queens, 14 in Connecticut): 565 false positives in ~2 h of group recording (402 on screams/shouts,
75 on loud discussion, 43 on laughter, 42 on cheering), while 35 of 65
deliberately aggressive screams failed to trigger [27]. That is the canonical
case for (a) hard negatives in audio evaluation — `NUISANCE_SOURCES` in
`survsim/sensors/audio.py` already lists laughter, child playing and football
chants as `shout` confusers — and (b) never alarming on audio alone.

Prices for security sensors are rarely published; thermal cameras of the
classes above typically sell from low thousands of USD per unit and radar/DAS
on project pricing [lore]. Treat the column as a pointer to get quotes, not as
a cost model (report 22 has the per-camera cost model).

## 16. What SurvSim must emit — checklist tied to modules

| # | Emit | Module | State |
|---|---|---|---|
| 1 | Degraded frames with profile name + all `Profile` params in the manifest | `survsim/sensors/degrade.py`, `survsim/datasets` | frames yes; full params in manifest — add |
| 2 | Per-frame IQA stats sidecar | `survsim/realism/stats.py` | compute yes; sidecar — add |
| 3 | Camera state per tick incl. tamper kind, since, blind, live pose | `survsim/director/camera_director.py` (`snapshot`) | yes |
| 4 | `calibration_valid` and `coverage_lost_zones` on tamper/PTZ | camera_director + rig analysis | add |
| 5 | Day/night switch and illuminator state events | `survsim/sensors/degrade.py` (`ir_night`) | add |
| 6 | Near-lens particles (insects, rain, snow) with GT "not a person" | degrade + scenario weather | add |
| 7 | Thermal frames + DRI range report | `survsim/sensors/thermal.py` (`render`, `range_report`) | yes |
| 8 | RF observations with GT uid, true distance, MAC epoch | `survsim/sensors/rf.py` (`RfSimulator.step`) | yes |
| 9 | Audio observations with GT source, nuisance flag, true bearing | `survsim/sensors/audio.py` | yes |
| 10 | Radar tracks with class and GT | new `survsim/sensors/radar.py` | missing |
| 11 | Fence/DAS events by segment with cause | new `survsim/sensors/fence.py` | missing |
| 12 | Shared-cause variables (wind, rain, wildlife) as a per-tick world table | Director / EnvDirector | partial |
| 13 | Per-sensor clock offset/drift | Director clock | cameras yes; other sensors add |
| 14 | Fusion operating points (`SensorChannel`) measured per run, plus correlation estimate | `survsim/eval/fusion.py` | fuse yes; measured correlation — add |
| 15 | SAPIENT-shaped export of detections/status | new exporter under `survsim/gt/` | missing |

---

## References

1. Y. P. Loh, C. S. Chan, "Getting to know low-light images with the Exclusively Dark dataset", *CVIU* 178:30–42, 2019. https://arxiv.org/abs/1805.11227 ; data https://github.com/cs-chan/Exclusively-Dark-Image-Dataset
2. L. Neumann et al., "NightOwls: A Pedestrians at Night Dataset", *ACCV* 2018. https://www.robots.ox.ac.uk/~vgg/publications/2018/Neumann18b/
3. "Johnson's criteria" (J. Johnson, 1958, US Army Night Vision Lab), summary with line-pair values. https://en.wikipedia.org/wiki/Johnson%27s_criteria
4. C. Sakaridis, D. Dai, L. Van Gool, "Semantic Foggy Scene Understanding with Synthetic Data", *IJCV* 126(9):973–992, 2018. https://arxiv.org/abs/1708.07819
5. C. Sakaridis et al., "ACDC: The Adverse Conditions Dataset with Correspondences", *ICCV* 2021 / *T-PAMI* 2025. https://arxiv.org/abs/2104.13395
6. E. Ribnick, S. Atev, O. Masoud, N. Papanikolopoulos, R. Voyles, "Real-Time Detection of Camera Tampering", *AVSS* 2006, pp. 10–15. https://www.computer.org/csdl/proceedings-article/avss/2006/26880010/12OmNBoNrtE
7. A. Saglam, A. Temizel, "Real-Time Adaptive Camera Tamper Detection for Video Surveillance", *AVSS* 2009. https://www.researchgate.net/publication/221315328_Real-Time_Adaptive_Camera_Tamper_Detection_for_Video_Surveillance
8. "A Survey of Feature Types and Their Contributions for Camera Tampering Detection", 2023. https://arxiv.org/abs/2310.07886
9. T. S. Rappaport, *Wireless Communications: Principles and Practice*, 2nd ed., Prentice Hall, 2002 — log-distance path loss with log-normal shadowing (textbook model; not re-fetched).
10. Particle-filter path-loss-exponent estimation from outdoor ZigBee RSSI (1–100 m), *Sensors* 2021 — cited only for the log-normal shadowing model; it does not contain the BLE exponent an earlier draft attributed to it. https://pmc.ncbi.nlm.nih.gov/articles/PMC7998977/
11. SpotterRF C-series datasheet / C550 announcement. https://www.securityinformed.com/news/co-9526-ga-co-177-ga.11929.html ; https://www.spotterglobal.com/shop/product/sp-c550-ext-2-0-sp-c550-ext-13879
12. Navtech Radar, AdvanceGuard for Security; 5 km radar. https://navtechradar.com/radar-solutions/radar-for-security-solutions/advanceguard-for-security/ ; https://navtechradar.com/news/5km-radius-radar/
13. Echodyne EchoGuard. https://www.echodyne.com/radar-systems/echoguard
14. NPSA, PIDS evaluation schemes. https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-systems-pids-evaluation-schemes
15. NPSA / Home Office, *Guide to Perimeter Intrusion Detection Systems*. https://www.npsa.gov.uk/system/files/documents/2c/80/Guide-to-PIDS.pdf
16. J. F. Gemmeke et al., "Audio Set", *ICASSP* 2017. https://research.google.com/audioset/
17. J. Salamon, C. Jacoby, J. P. Bello, "A Dataset and Taxonomy for Urban Sound Research", *ACM MM* 2014. https://urbansounddataset.weebly.com/urbansound8k.html
18. DCASE challenge series. https://dcase.community/
19. A. N. Steinberg, C. L. Bowman, F. E. White, "Revisions to the JDL data fusion model", *Proc. SPIE* 3719, 1999 (not re-fetched).
20. GOV.UK, "SAPIENT autonomous sensor system". https://www.gov.uk/guidance/sapient-autonomous-sensor-system
21. Dstl, SAPIENT proto files (BSI Flex 335). https://github.com/dstl/SAPIENT-Proto-Files
22. Axis Q1961-TE product page. https://www.axis.com/products/axis-q1961-te
23. Hikvision DS-2TD2167 series. https://www.hikvision.com/en/products/Thermal-Products/Security-thermal-cameras/Bullet-series/ds-2td2167-15-py/
24. Teledyne FLIR FC-Series AI. https://www.flir.com/products/fc-series-ai/
25. Senstar FiberPatrol FP1150 / FP400. https://senstar.com/products/fence-sensors/fiberpatrol-fp1150/ ; https://senstar.com/products/fence-sensors/fiberpatrol-fp400/
26. Sound Intelligence, Aggression Detection. https://www.soundintel.com/products/overview/aggression/
27. ProPublica, "Aggression Detectors: The Unproven, Invasive Surveillance Technology Schools Are Using" and methodology, 2019. https://features.propublica.org/aggression-detector/the-unproven-invasive-surveillance-technology-schools-are-using-to-monitor-students/ ; https://projects.propublica.org/graphics/aggression-detector-data-analysis
28. Axis Audio Analytics. https://www.axis.com/products/axis-audio-analytics
29. Louroe DigiFact A. https://www.louroe.com/product/digifact-a/ ; price reference https://www.ebay.com/p/16059813219
30. ONVIF profiles. https://www.onvif.org/profiles/

In-repo: docs/11, docs/15; `survsim/sensors/{degrade,thermal,rf,audio}.py`, `survsim/eval/fusion.py`, `survsim/director/camera_director.py`, `configs/scenarios/{disguise_and_tamper,street_crowd}.yaml`; research R04, R05, H01, H02, D04.
