# 17 · System Design Overview — a real-world multi-camera CCTV analytics system

*Series 17–23: "how would the real product work, and what does SurvSim have to
produce for each piece of it". This report is the spine; 18–22 zoom into each
layer; 23 turns the gaps into a plan.*

**Sourcing conditions.** Written 2026-09-26 without engine or GPU access. Numbers
from this repo are cited to their file (docs/11, docs/13, docs/15, docs/12).
External figures are cited as [n] to the References section; each was
checked against the paper, vendor or standards page on 2026-09-26, and
anything that could not be confirmed was corrected or removed. Back-of-envelope arithmetic is
tagged **[BOE]** and shown inline. Inferences are tagged **[INF]**. This report
deliberately does not repeat D04 (deployment architecture, 19k words) — it
references it where D04 already settled a question, and concentrates on the
*analytics* pipeline, its data contracts and its budgets.

---

## 0. Executive summary — twelve design decisions

1. **The product is a verification pipeline, not a detector.** A 500-camera
   control room tolerates on the order of one nuisance alarm per operator per
   several minutes; research operating points (ActEV ≈ 6 false alarms per
   camera-hour) would deliver 3,000 alarms/hour across that estate (R03, H02).
   Every layer after detection exists to delete alarms. Architecture follows.
2. **Seven stages, four clocks.** Ingest → decode → per-frame perception →
   per-camera tracking → cross-camera association → behaviour/intent → alarm
   policy → operator/audit. Perception runs at frame rate (5–25 Hz), tracking at
   frame rate, association at ~1 Hz, behaviour at 0.2–2 Hz on track windows,
   alarm policy is event-driven. Designing each stage to its own clock is the
   single biggest throughput lever.
3. **The track, not the frame, is the unit of meaning.** Everything above
   single-camera MOT consumes *tracklets* (id, time span, box sequence, embedding
   summary, ground-plane trajectory, quality flags). Getting that contract right
   matters more than any model choice.
4. **Ground plane or nothing.** Behaviours are defined in metres and seconds
   (loiter ≥ N s inside zone Z, speed > v m/s). Each camera needs a validated
   image→ground homography and a *health flag* saying whether it still holds
   (tamper, PTZ slew). SurvSim principle 2 ("ground truth must follow the live
   camera") is the same rule applied to production.
5. **Latency budget: ≤ 10 s event-to-operator for i-LIDS-style detection
   events,** ≤ 2 s for PTZ slew-to-cue, ≤ 500 ms glass-to-glass for live
   viewing (D04). i-LIDS scores a correct alarm later than its tolerance as a
   false alarm (R03), so latency is an accuracy metric, not a performance one.
6. **Edge-heavy perception, central association.** Detection+MOT belongs next to
   the camera (edge box or on-prem GPU node) because raw video is the expensive
   thing to move. Cross-camera association and behaviour need a site-wide view,
   so they sit on a site server. Cloud is for training, fleet management,
   search-over-archive, and optional VLM verification — not for the live loop in
   most CNI/defence estates (air-gapped; D04, D06).
7. **Metadata bus as the integration spine.** ONVIF Profile M metadata / MQTT or
   Kafka topics carrying typed JSON/Protobuf messages between stages. Video stays
   in the VMS; analytics exchange *references* (camera, PTS/UTC, box) not pixels.
8. **Degradation is a first-class input.** Each frame/tracklet carries an image
   quality score (blur, noise, exposure, blockiness, tamper state). Downstream
   stages condition on it (e.g. suppress a loiter alarm from a camera whose
   quality has collapsed rather than silently miss).
9. **Corroboration beats confidence.** A second, weakly-correlated channel (a
   second camera, radar, a fence sensor, RF presence, audio) cuts false alarms
   multiplicatively *if* the nuisance sources are independent — SurvSim's
   `eval/fusion.py` already penalises correlated nuisances (docs/11).
10. **Humans are the last stage and the scarcest resource.** Operator budget
    (alarms per operator-hour) is the constraint the alarm policy optimises
    against; the UI is part of the detection system.
11. **Audit is a legal requirement, not a nice-to-have.** UK Surveillance Camera
    Code principles 10 (review and audit) and 11 (evidential value) — binding on
    relevant authorities such as police and councils, voluntary for others — and EU AI Act logging obligations mean every alarm must
    be reproducible: model versions, thresholds, zone config, and evidence clip
    (report 21).
12. **SurvSim is the test oracle for every contract above.** Because it knows
    what actually happened (principle 1), it can score each stage in isolation
    *and* the end-to-end chain — including latency, handoff gaps and alarm
    budgets, which real data never labels.

---

## 1. Scope, users and the operational problem

The company sells CCTV analytics into security operations centres: critical
national infrastructure (substations, water, rail), defence estates, borders,
transport hubs and large events (R06, D06). The job the system does, restated as
an operator would:

* **Detect** that something requiring attention is happening (intrusion,
  loitering/hostile reconnaissance, tailgating, abandoned object, fight,
  person-down, crowd surge, camera tamper).
* **Locate and follow** the subject across cameras, even through blind spots and
  appearance change.
* **Present** it to an operator with enough context to decide in seconds.
* **Record** a defensible audit trail and evidence.
* **Search** afterwards ("person in red jacket near gate 3 between 02:00 and
  03:00").

D06 established that pilot failures are overwhelmingly about configuration,
video quality, integration and operator load, not model accuracy (Keval &
Sasse). The design therefore spends as much structure on configuration,
health, and workflow as on perception.

### 1.1 Reference scale points

| Estate | Cameras | Streams analysed | Operators | Typical hardware |
|---|---|---|---|---|
| Single site (substation, depot) | 8–32 | all | 0–1 local, remote SOC | 1 edge box or 1 GPU server |
| Campus / port / airport zone | 100–500 | all | 4–12 | 2–10 GPU servers on-prem |
| City / multi-site SOC | 1,000–10,000 | selective | 10–50 | distributed edge + regional DC |

Westminster's monitored public-realm CCTV is ~100–200 cameras (D06 correction),
a useful reminder that "city scale" in the UK is smaller than vendor decks imply.

---

## 2. The end-to-end pipeline

```
 cameras (ONVIF S/T, RTSP H.264/H.265, 720p–4K, 5–25 fps)
    │  RTSP/RTP over TCP; NTP/PTP time; ONVIF events (tamper, IO)
    ▼
 [1] INGEST & HEALTH  ── stream supervisor, reconnect, clock-skew estimate,
    │                    per-camera config (zones, homography, schedule)
    ▼
 [2] DECODE & SAMPLE ── HW decode (NVDEC / Jetson NVDEC / VA-API), frame
    │                    sampling to analysis rate, resize/letterbox, IQA
    ▼
 [3] PERCEPTION ─────── person/vehicle/object detector (+ pose, + attributes)
    │                    batched across cameras on GPU
    ▼
 [4] SINGLE-CAM MOT ─── ByteTrack/BoT-SORT-class tracker, CMC for PTZ,
    │                    appearance embedding per track (sampled)
    ▼  tracklets (ground-plane projected, quality-scored)
 [5] CROSS-CAMERA ───── topology-gated ReID association → global identities,
    │                    handoff, re-acquisition after blind spots
    ▼  global tracks + scene graph
 [6] BEHAVIOUR/INTENT ─ rules over zones & trajectories; learned sequence /
    │                    graph models; object-state (abandoned); crowd fields
    ▼  candidate events with scores
 [7] ALARM POLICY ───── threshold → context → persistence → corroboration →
    │                    operator-budget control (SurvSim eval/pipeline.py)
    ▼  alarms
 [8] OPERATOR UI / C2 ─ alarm queue, clip, map, PTZ slew-to-cue, disposition
    │                    (true/false/nuisance) → feedback store
    ▼
 [9] AUDIT & EVIDENCE ─ immutable log, model/config versions, export bundle
```

Side channels: **[S1] other sensors** (radar, PIDS fence, RF, audio, access
control) join at [5]–[7]; **[S2] search/archive** indexes [3]–[6] outputs for
retrospective query; **[S3] learning loop** consumes [8] dispositions (report 21).

The SurvSim mirror of this chain already exists in code (docs/11): detection
scoring (`eval/detection.py`), single-camera tracking (`eval/tracking.py`),
MTMC with `handoff_gap` (`evaluate_mtmc`), ReID across appearance epochs
(`reid_by_epoch`), behaviour (`eval/behaviour.py`, rule baseline + learned
classifier), fusion (`eval/fusion.py`), the alarm pipeline
(`eval/pipeline.py`: threshold→context→persistence→corroboration→budget), and
VMS-style outputs (`gt/video.py`: video, timing sidecars, ONVIF metadata).

---

## 3. Stage by stage

### 3.1 Ingest and stream health [1]

**Protocols.** ONVIF Profile S (streaming) and T (H.264/H.265, metadata,
imaging) for camera discovery and control; Profile M for analytics metadata;
Profile G for edge storage [6]. RTSP (RFC 7826 [7]) carries RTP/H.264 (ITU-T H.264) or
H.265. In practice analytics usually pull a *secondary* stream from the VMS
(Milestone, Genetec, Avigilon, Nx) rather than the camera, to avoid exceeding
camera session limits (D04).

**Responsibilities.**
* Reconnect with exponential backoff; detect frozen streams (identical PTS or
  identical frame hashes). Note: SurvSim's camera director does *not* model a
  frozen image — its six tamper kinds are cover, spray, tilt, unplug, glare,
  defocus (`director/camera_director.py`); a freeze mode would be a gap to add.
* Estimate clock offset per camera. Consumer cameras drift seconds per day
  without NTP; cross-camera association with a 2 s skew mislabels handoffs.
  SurvSim models per-camera clock offset and drift (docs/02 §1.1) and emits
  timing sidecars (`gt/video.py`) precisely so this can be tested.
* Hold camera config: resolution, fps, zones, homography, schedule
  (armed/disarmed), sensitivity, PTZ presets. Config is versioned (§6).

**Failure modes.** Silent resolution change after camera firmware reboot
(homography now wrong by a scale factor) [lore]; VMS transcode adding 1–3 s
latency [lore, D04]; RTSP over UDP losing packets → grey smears that look like
motion to naive detectors (R04).

### 3.2 Decode, sample and quality [2]

* **Hardware decode is mandatory at scale.** NVIDIA rates the T4 at "up to 38
  full-HD video streams" of decode [9]; newer L4-class cards are rated higher
  (see the Video Codec SDK support matrix [10] and report 22). CPU decode at
  1080p costs roughly one core per stream at 25 fps [BOE/lore].
* **Sample to the analysis rate, not the camera rate.** Tracking collapses below
  ~3 fps (R01); above ~10 fps additional frames buy little for walking people.
  Default: decode all (needed for GOP), *infer* on 5–10 fps, with burst to full
  rate on cameras with an active event. Decoding every frame but inferring on
  every 3rd is the cheap way to preserve IDs.
* **Image-quality assessment (IQA) per camera per N seconds**: sharpness
  (Laplacian variance), noise, exposure, blockiness, scene-change vs. reference
  (tamper). SurvSim computes exactly these statistics in
  `survsim/realism/stats.py` (docs/15: `noise_sigma`, `lap_var_log10`,
  `mtf_ratio`, `edge_width`, `blockiness`, `temporal_noise`...), so the same code
  can serve as the production IQA feature set and the sim-realism metric — a
  useful convergence [INF].

### 3.3 Perception [3]

Detector (person, vehicle, bag/object, optionally pose keypoints and attributes
such as upper/lower clothing colour, hi-vis, carried items). At surveillance
standoff people are 20–120 px tall; the 20–60 px band is where products win or
lose (R01, report 18). Tiling / SAHI-style slicing [4] for 4K
wide-area cameras; region-of-interest masks to avoid inferring on sky.

**Contract out (per frame, per camera):**
```
Detection { camera_id, frame_pts, utc_ns, class, score, bbox_xywh_px,
            keypoints?[17x3], attrs?{...}, iqa_ref }
```

### 3.4 Single-camera MOT [4]

Tracking-by-detection with a Kalman motion model and two-stage association
(ByteTrack [1]), observation-centric re-update (OC-SORT [2]), and camera-motion compensation plus ReID fusion (BoT-SORT [3]) for PTZ and shake. SurvSim's own numpy ByteTrack reaches
MOTA 0.466 / IDF1 0.559 / HOTA 0.443 (0.537 at α = 0.5; TrackEval parity, docs/13 — 0.434 pre-parity, 0.545 pre-fix `be9f52a`) on a 600-frame MOT20 subset with zero-shot
YOLO11n (docs/13) — a floor, not a target.

**Contract out (per track, updated each frame; closed tracklets on end):**
```
Tracklet { camera_id, local_track_id, t_start, t_end,
           boxes[(t, bbox, score, visibility_est)],
           ground_xy[(t, x_m, y_m, cov)],        # via homography
           embeddings[k x D] (sampled best-quality crops),
           attrs_summary, quality{min_h_px, mean_iqa, occlusion_frac},
           state: tentative|confirmed|lost|closed }
```
Ground-plane covariance matters: R02 computed that 1° of extrinsic error at 30 m
range from a 4 m mounting height is ≈ 3.9 m on the ground (ΔX ≈ R²θ/h) — larger than most zone boundaries. The tracker must
propagate that uncertainty rather than pretend the projected foot-point is exact.

### 3.5 Cross-camera association [5]

Two regimes (R02): **overlapping** fields of view (fuse on the ground plane;
WILDTRACK-style), and **non-overlapping** (associate across blind gaps using
appearance + camera-topology transit-time priors). Production systems combine:

* a **camera graph** with learned or configured transit-time distributions
  between exits and entries (SurvSim already has a camera graph and blind-spot
  analysis: `survsim rig`),
* **appearance similarity** from ReID embeddings (OSNet / TransReID / CLIP-ReID),
* **soft biometrics** that survive disguise (height, gait — SurvSim's six-
  parameter gait signature, docs/11),
* **constraints**: one person can't be in two non-overlapping places at once.

Output is a set of **global tracks** with confidence per link. Links are
revisable — late evidence may split or merge (the system must emit
corrections, and downstream consumers must tolerate them).

```
GlobalTrack { global_id, members[(camera_id, local_track_id, link_score)],
              trajectory_world[(t, x, y)], appearance_epochs[(t0,t1,emb)],
              revision }
```
The *appearance epoch* concept — identity persists while appearance changes —
is directly SurvSim's (`reid_by_epoch`), and it is what clothes-change ReID
research needs (LTCC clothes-changing Rank-1 is only ~40 %: CAL, CVPR 2022,
reports 40.1 % / 18.0 mAP [17]; later methods sit in the 40s — corrected from
an earlier "30s" figure).

### 3.6 Behaviour / intent [6]

Detailed in report 19. Architecturally, three families run side by side:

1. **Geometric rules** on global tracks and zones (loiter dwell, line-cross,
   wrong-way, tailgate count at door, speed). Cheap, explainable, configurable
   per site — the thing a customer can sign off.
2. **Learned models** on pose/trajectory sequences (fight, fall, reconnaissance
   patterns), including graph models over interacting tracks.
3. **Object-state models** (a bag appears, owner leaves, bag persists > T) and
   **scene-level** models (crowd density, flow, surge).

Outputs are *candidate events* with score, evidence references and the rule or
model version that produced them.
```
CandidateEvent { event_id, type, t_start, t_detect, zone_id, subjects[global_id],
                 score, evidence[(camera, pts range, bbox)], producer{name,ver},
                 features{...} }
```

### 3.7 Alarm policy [7]

The five-step funnel SurvSim implements in `eval/pipeline.py` (docs/11):

1. **Threshold** on candidate score.
2. **Context** — schedule, zone arming, weather state, known maintenance, camera
   health (suppress or down-weight on a degraded camera; flag the camera instead).
3. **Persistence** — require the condition to hold for Δt or across k frames.
4. **Corroboration** — second camera, radar, fence, RF, audio. Independent
   nuisance sources multiply down false alarms; correlated ones (wind moves both
   the fence and the vegetation on camera) don't (R05; `eval/fusion.py`).
5. **Budget** — adaptive thresholds per camera so the alarm rate per operator
   stays within budget, with explicit accounting of what recall that costs.

The policy is the most site-specific component and should be data (YAML/JSON
rules, versioned), not code.

### 3.8 Operator UI, C2 integration [8]

Alarm queue sorted by priority and age; each alarm shows a pre-roll/post-roll
clip, the subject highlighted, the map position, and linked cameras. One-click
PTZ slew-to-cue. One-click disposition: *true / false (system error) / nuisance
(real but irrelevant: fox, staff)*. Dispositions are the most valuable labels the
company will ever get (report 21). Integration outward to PSIM/C2 via the VMS
alarm API or standards (e.g. ONVIF events, SIA/CAP-style messages; D04 §6).

### 3.9 Audit and evidence [9]

Append-only log of every alarm with: input references, model versions, config
hash, operator actions and timestamps. Evidence export (clip + metadata +
hash). IEC/EN 62676-4 (video surveillance application guidelines; revised as Edition 2.0 in
October 2025, replacing DORI with new pixel-density/operational-requirement
categories [13]) and the Home Office *CCTV Operational Requirements Manual 2009*
(Cohen, Gattuso & MacLennan-Brown, HOSDB publication 28/09 [14]) frame what a
court or regulator expects; report 21 covers law.

---

## 4. Data contracts and the metadata bus

### 4.1 Principles

* **Pixels stay put.** Video lives in the VMS/NVR; everything else moves
  references `(camera_id, utc_ns | pts, bbox)`. A 1080p H.264 stream is
  2–6 Mb/s; its detection metadata at 10 fps is ~30–100 kb/s [BOE: 10 fps × ~20
  objects × ~60 bytes ≈ 12 kB/s ≈ 96 kb/s uncompressed JSON; protobuf ~3×
  smaller ≈ 32 kb/s] — still ~50–100× less than the video.
* **Every message carries time in two clocks**: camera PTS and site UTC
  (with the estimated skew applied and the skew itself recorded).
* **Every message carries a producer version.** Without it, an alarm cannot be
  reproduced, and regression analysis after a model update is impossible.
* **Revisions are explicit.** Global track merges/splits emit a new revision;
  consumers are idempotent on `(id, revision)`.
* **Schema-first.** Protobuf/Avro with a registry, so edge boxes on old
  firmware keep talking to new servers.

### 4.2 Transport

| Link | Rate | Choice | Why |
|---|---|---|---|
| camera → decoder | 2–8 Mb/s per stream | RTSP/RTP (TCP interleaved on lossy links) | universal |
| detector → tracker | per-frame | in-process (DeepStream metadata, shared memory) | avoid serialisation at frame rate |
| tracker → site bus | tracklet updates ~1–5 Hz | MQTT (edge) / Kafka or NATS (site) | fan-out, replay |
| bus → association/behaviour | same | consumer groups | horizontal scale |
| alarms → VMS/PSIM | events | VMS SDK / ONVIF events / REST webhooks | integration |
| archive index | batch | object store + vector DB | search |

ONVIF Profile M defines a metadata schema for object classification and events
[6]; aligning internal messages with it
cuts integration cost with VMSs that already understand it [INF]. SurvSim
already emits "ONVIF metadata" alongside video (`gt/video.py`, docs/11) — the
simplest way to prove the product ingests real-world metadata formats.

### 4.3 The contract table — what SurvSim must emit to test each

| Contract | Real producer | SurvSim GT equivalent (exists?) |
|---|---|---|
| Detection | detector | MOT `gt/mot_<cam>.txt`, COCO w/ keypoints, mask-derived boxes (Unreal) — yes |
| Tracklet | tracker | per-camera MOT ids + visibility — yes |
| Ground trajectory | homography | `world.parquet` actual positions — yes |
| GlobalTrack | association | `identities.parquet`, appearance epochs — yes |
| CandidateEvent/Alarm | behaviour + policy | `events.jsonl` with behaviour labels — yes; *onset/"detectable-from" time* — partial |
| Camera health | IQA/tamper | camera director tamper events (6 kinds) — yes |
| Clock skew | ingest | per-camera offset/drift + timing sidecars — yes |
| Operator disposition | human | **not modelled** — needed for active-learning simulation (report 21) |

---

## 5. Latency and throughput budgets

### 5.1 Latency (detection event → operator sees alarm)

| Stage | Budget | Notes |
|---|---|---|
| Camera encode + network | 150–400 ms | GOP/B-frames add latency; D04 |
| VMS relay (if in path) | 0–1,500 ms | a transcode relay is the worst offender [lore] |
| Decode + queue | 30–100 ms | batch-size dependent |
| Detection | 10–40 ms | batched GPU; see report 22 |
| MOT update | 1–5 ms | CPU |
| Track → bus → association | 100–1,000 ms | association runs ~1 Hz |
| Behaviour decision | *inherent dwell* + 0.5–2 s | loitering needs its dwell; this is not "latency" |
| Alarm policy (persistence) | 1–5 s | deliberate |
| UI push | 100–300 ms | websocket |
| **Total (excluding inherent dwell)** | **≈ 3–9 s** | inside the 10 s i-LIDS tolerance [BOE] |

The persistence window is the knob that trades latency against false alarms;
i-LIDS timing makes that trade explicit, which is why SurvSim reports an alarm
later than tolerance as a false alarm (`survsim eval --threshold-s`).

PTZ slew-to-cue needs the *pre-policy* track position, not the alarm: ≤ 2 s
from detection to PTZ command, or the target leaves the fixed camera's view.

### 5.2 Throughput [BOE]

Per 1080p stream at 10 inference fps with a 6.5–21.6 GFLOP detector (YOLO11n
to YOLO11s at 640 px [11]): ≈ 65–216 GFLOP/s. A T4 (65 FP16 TFLOPS / 130 INT8
TOPS peak, 70 W [9]; realistically 10–20 % utilisation for small batched models)
has compute headroom for roughly 40–100 such streams [BOE], but its rated
decode ceiling of ~38 full-HD streams [9] binds first. **Decode, not compute,
is the binding constraint** for small detectors on this class of card. ReID embedding is sampled (e.g. 1–2 crops per track per second)
so it costs ~10–20 % of detection [BOE]. Behaviour models on tracks are
negligible compared to pixels; video-transformer action models are not
(report 19).

### 5.3 SurvSim constraint

The development machine is an 8 GB RTX 2070 Max-Q (CLAUDE.md): capture stays at
720p with ≤ 12 hero agents. The editor render pipeline runs ~11 frames/s at 720p
(docs/11), and degradation costs 0.567 s/frame (docs/15; target ≤ 0.3 s not
reached). Generating a 1-hour, 8-camera, 10 fps evaluation set is
8 × 36,000 = 288,000 frames ≈ 7.3 h render + 45 h degradation single-threaded
[BOE] — so degradation parallelism, not rendering, is SurvSim's throughput
bottleneck for long-duration false-alarm evaluation (report 23).

---

## 6. Configuration as a product surface

Most real-world failures are configuration (D06). The design treats site config
as versioned, validated data:

* **Camera record**: stream URLs, intrinsics (focal, distortion), extrinsics or
  homography, calibration residual, mounting height, PTZ presets, schedule.
* **Zone polygons on the ground plane** (not in image space — image-space zones
  break on every PTZ move or re-aim).
* **Rules** per zone: behaviour type, parameters (dwell, direction, count),
  arming schedule, priority.
* **Validation on save**: SurvSim's rig analysis (`survsim rig`: coverage, blind
  spots, pixels-on-target per zone) is exactly the tool a commissioning engineer
  needs — "zone 3's far edge gives 14 px people; loiter detection there will be
  unreliable" [INF: productise `survsim rig` as a commissioning check].
* **Change log**: who changed what, when; roll back.

---

## 7. Placement: edge vs on-prem vs cloud

| Function | Edge (camera / box) | On-prem site server | Cloud / central |
|---|---|---|---|
| Decode | ✔ (NVDEC/Jetson) | ✔ | ✘ (bandwidth) |
| Detection + MOT | ✔ preferred | ✔ | rare |
| ReID embedding | ✔ | ✔ | archive search |
| Cross-camera association | ✘ (needs site view) | ✔ | multi-site only |
| Behaviour rules | limited (per camera) | ✔ | ✘ |
| Alarm policy & UI backend | ✘ | ✔ | managed-service variant |
| VLM verification on trigger | ✘ (power) | ✔ if GPU | ✔ if allowed |
| Training, registry, fleet mgmt | ✘ | optional | ✔ |

Drivers: **bandwidth** (moving 500 × 4 Mb/s = 2 Gb/s off-site is costly),
**air-gap** (defence/CNI often forbid cloud), **latency**, **power/space at the
edge** (Jetson Orin NX 10–40 W, up to 157 TOPS; Orin Nano 7–25 W, up to 67 TOPS;
AGX Orin 15–60 W, up to 275 TOPS [12] — the NX/Nano figures are "Super"
mode, JetPack 6.2+; earlier software rates NX at 100 TOPS),
and **data protection** (keeping personal data on-prem simplifies DPIAs).

D04 §12 has three sized reference architectures; the analytic placement above
is compatible with all three. The VLM-on-trigger pattern follows from D07's
arithmetic that always-on VLM analysis costs ~0.36M (default resolution, 1 fps)
to ~1.1M (high resolution) tokens/camera-hour — 4.6M only under a 2 fps × 640
tokens/frame research protocol (AUDIT_43-47). Uneconomic, not infeasible.

---

## 8. Failure modes and how the design contains them

| Failure | Effect | Containment | SurvSim test |
|---|---|---|---|
| Camera knocked/tilted | homography wrong; zones misplaced | IQA scene-change vs reference → camera health flag → suppress + alert maintenance | tamper `tilt` invalidates calibration (docs/11) |
| Camera blinded/covered | no detections — silent miss | "absence of expected activity" + IQA → tamper alarm | tamper kinds; blinded camera emits nothing (principle 2) |
| PTZ moved by operator | fixed-zone rules wrong | read PTZ position (ONVIF PTZ status); disable image-space rules while off-preset | PTZ slews in camera director |
| Night / IR switch | detector drift, colour attrs useless | IQA day/night state; per-mode thresholds; attribute suppression | `cctv_night_ir` profile |
| Rain/snow/insects near IR | false motion, spurious detections | temporal persistence; corroboration | weather in EnvDirector (partial) |
| Clock skew | wrong handoffs, wrong ordering in evidence | skew estimation; record skew in metadata | per-camera offset/drift |
| Stream drop | track fragmentation, missed events | reconnect; mark gap; don't close tracks instantly | frame-drop in degrade |
| Crowding | ID switches, ReID confusion | crowd mode: density estimate instead of per-person rules | crowd model, density bands |
| Model update regression | FA rate jumps | shadow deployment, per-site eval gate (report 21) | SurvSim regression suite |
| Adversary evasion | no detection by design | multi-cue (gait, height, RF), coverage design | 52 evasion techniques |
| Operator overload | real alarms ignored | budget control, priority, dedup | alarm budget in `eval/pipeline.py` |
| Bus outage | alarms lost | local buffering at edge, at-least-once delivery | not modelled |

The two dangerous failures are *silent* ones: a blinded camera (no data looks
like no events) and a moved camera (valid-looking data in the wrong place).
Both are addressed by health monitoring as an analytics output in its own right,
and both are exactly SurvSim principle 2.

---

## 9. Security of the analytics system itself

Summarised; D04 §7 is the long form. Cameras are the most-compromised IoT
class (Mirai); analytics nodes sit on the camera VLAN and must not become a
bridge. Requirements: signed model artefacts and container images; mTLS on the
bus; no inbound internet; role-based access to live video vs metadata; Cyber
Essentials Plus for UK customers; ISA/IEC 62443 security levels (SL 1–4) where
the analytics sit inside an industrial control/OT environment such as a
substation or water works [15]; and the Surveillance Camera Code of Practice
[16] across the whole chain. Adversarial ML (patches, IR LEDs) belongs in the
threat model; SurvSim's evasion taxonomy (40 techniques) is the test catalogue.

---

## 10. How to evaluate the whole system, not just its parts

Component metrics (AP, HOTA, IDF1, Rank-1) do not compose into the operational
metric. The end-to-end harness must report:

1. **Event recall at i-LIDS timing** per behaviour type (hit only if within
   tolerance of onset).
2. **False alarms per camera-hour** and **per operator-hour**, with hard
   negatives present (principle 3).
3. **Time-to-alarm distribution** (median, p95).
4. **Handoff success and handoff gap** across cameras (`evaluate_mtmc`).
5. **Degradation curves**: each of the above vs imaging profile.
6. **Health detection**: time-to-detect tamper, false tamper alarms.
7. **Operator load**: alarms/operator-hour after policy, fraction of shift
   spent on nuisance.

SurvSim already computes 1–4 and 6 in some form (docs/11); 5 requires running
the same scenario through multiple profiles (supported by
`sensors.degrade.apply_profile`), and 7 requires an operator model (report 21,
23). A real-data check must accompany every synthetic claim — docs/13's gap
protocol (same models, thresholds, code; report the synthetic − real gap).

---

## 11. Minimum viable product cut

If a team had to ship in six months, the defensible MVP is [INF]:

* Ingest from one VMS (Milestone or Genetec), ONVIF fallback.
* YOLO-class person/vehicle detector fine-tuned on in-domain + synthetic.
* ByteTrack/BoT-SORT per camera with CMC.
* Ground-plane zones with intrusion, loiter, line-cross, wrong-way; camera-
  tamper health.
* Alarm policy with persistence and per-camera budgets.
* Simple web alarm queue with clip + disposition; audit log.
* No cross-camera ReID in v1 except "show me this person on nearby cameras"
  (operator-assisted search), which is lower-risk than automated global
  identity and still high value.

This matches what buyers actually test in trials (D06) and uses SurvSim where
it is already strongest (zones, dwell, tamper, hard negatives, alarm timing).

---

## 12. Open design questions

1. Should association happen on tracklets (online, ~1 Hz) or re-run as a batch
   over a sliding window with revisions? (Recommendation: online with a 30–60 s
   revision window.)
2. Where does pose run — every person every frame (costly) or only on tracks
   whose behaviour model requests it? (Recommendation: on demand.)
3. How much of the alarm policy should be learned? Learned thresholds per
   camera are cheap; learned "context" risks unexplainable suppression.
4. What is the minimum calibration quality before a camera's alarms are
   trusted? SurvSim can answer this quantitatively by perturbing extrinsics and
   measuring zone-event F1 (report 23 milestone).

---

## References

Checked 2026-09-26 (abstract, official repository, vendor or standards page).

1. Zhang et al. "ByteTrack: Multi-Object Tracking by Associating Every Detection Box." ECCV 2022. https://arxiv.org/abs/2110.06864
2. Cao et al. "Observation-Centric SORT." CVPR 2023. https://arxiv.org/abs/2203.14360
3. Aharon, Orfaig, Bobrovsky. "BoT-SORT: Robust Associations Multi-Pedestrian Tracking." arXiv 2022. https://arxiv.org/abs/2206.14651
4. Akyon, Altinuc, Temizel. "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection." ICIP 2022. https://arxiv.org/abs/2202.06934
5. Luiten et al. "HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking." IJCV 2021. https://arxiv.org/abs/2009.07736 (the earlier draft cited a wrong arXiv id)
6. ONVIF profiles S/T/M/G; Profile M. https://www.onvif.org/profiles/ ; https://www.onvif.org/profiles/profile-m/
7. Schulzrinne et al. RFC 7826, Real-Time Streaming Protocol Version 2.0. IETF 2016. https://www.rfc-editor.org/rfc/rfc7826
8. NVIDIA DeepStream SDK developer guide. https://docs.nvidia.com/metropolis/deepstream/dev-guide/
9. NVIDIA T4 product page (65 FP16 TFLOPS, 130 INT8 TOPS, 70 W, "up to 38 full-HD video streams"). https://www.nvidia.com/en-us/data-center/tesla-t4/
10. NVIDIA Video Codec SDK. https://developer.nvidia.com/video-codec-sdk
11. Ultralytics YOLO11 model table (FLOPs, T4 TensorRT latency). https://docs.ultralytics.com/models/yolo11/
12. NVIDIA Jetson Orin family page (AGX 15–60 W / 275 TOPS; NX 10–40 W / 157 TOPS; Nano 7–25 W / 67 TOPS). https://www.nvidia.com/en-gb/autonomous-machines/embedded-systems/jetson-orin/
13. IEC 62676-4 (2014; 2025 revision) — IEC webstore https://webstore.iec.ch/ ; summary of the 2025 levels https://www.jvsg.com/iec-62676-4-oodpcvs/
14. Cohen, Gattuso, MacLennan-Brown. *CCTV Operational Requirements Manual 2009.* Home Office Scientific Development Branch, publication 28/09. https://assets.publishing.service.gov.uk/media/5a7def31e5274a2e8ab44c3e/28_09_CCTV_OR_Manual2835.pdf
15. IEC, "Understanding IEC 62443." https://www.iec.ch/blog/understanding-iec-62443 ; ISA/IEC 62443 series https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards
16. UK Surveillance Camera Code of Practice (amended 2021). https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version
17. Gu et al. "Clothes-Changing Person Re-identification with RGB Modality Only" (CAL). CVPR 2022. https://openaccess.thecvf.com/content/CVPR2022/papers/Gu_Clothes-Changing_Person_Re-Identification_With_RGB_Modality_Only_CVPR_2022_paper.pdf

In-repo: docs/02, docs/11, docs/13, docs/15; research D04, D06, D07, R01–R05
(i-LIDS/ActEV protocols: R03 §2; Keval & Sasse: D06).
