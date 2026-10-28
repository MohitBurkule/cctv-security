# 19 · Behaviour & Intent Analytics — design, models, hard negatives, and operator metrics

*Series 17–23. Stage [6]–[7] of report 17. R03 is the literature review (VAD
taxonomy, i-LIDS/ActEV history, human factors, law); H02 has 156 practitioner
questions. This report turns them into a buildable design and a data
specification for SurvSim.*

**Sourcing conditions.** 2026-09-26; no GPU/engine. Repo numbers cite docs/03,
docs/11. External figures were re-checked against the
primary source on 2026-09-26 and are cited as [n] (References at the end); practitioner knowledge is **[lore]**; inferences **[INF]**;
arithmetic **[BOE]**.

---

## 0. Summary

* **Most sellable analytics are geometric rules on good tracks.** Intrusion,
  loitering, line-crossing, wrong-way, tailgating counts, abandoned object and
  after-hours presence are all definable in metres, seconds and zones. Their
  failure is almost always upstream (detection, tracking, calibration) or
  contextual (a legitimate person doing the same thing).
* **Learned models earn their place where geometry cannot express the pattern:**
  fights, falls, reconnaissance-like attention patterns, group interactions,
  crowd surges. They operate on pose and trajectory sequences, rarely on raw
  pixels at scale.
* **Hard negatives define the product.** A loiter detector is only as good as
  its rejection of `commute_wait`, `smoke_break`, `vendor` and `sit_rest`
  (docs/03 §1). SurvSim pairs every suspicious behaviour with innocent look-
  alikes (principle 3) and tags them `hard_negative_for`.
* **Score like i-LIDS, budget like a control room.** Event-level detection with
  a timing tolerance (a late alarm is a false alarm), false alarms per camera-
  hour with hard negatives present, then an operator budget. Frame-AUC is not
  reported (principle 4).
* **Intent is not observable; indicators are.** The product should output
  "behaviour consistent with reconnaissance indicators A, B, C over 14 min" —
  never "hostile intent" (R03 §4, legal constraints §9).

---

## 1. The behaviour taxonomy the product needs

Mapped to docs/03's catalogue (44 classes / 49 names, complete per CLAUDE.md)
and to the operational definitions in R03 §1.

| Analytic | Operational definition (configurable) | Primary cues | Hard negatives (docs/03) | Method |
|---|---|---|---|---|
| Sterile-zone intrusion | any person/vehicle enters zone Z while armed | ground-plane track ∩ polygon | worker_patrol, maintenance (authorised) | rule + role context |
| Perimeter probe / climb | approach fence ≤ d, dwell/along-fence motion; vertical motion at fence | trajectory, pose | photograph, maintenance | rule + learned posture |
| Loitering | dwell ≥ T (60–600 s) within radius r in zone, optionally revisit | track dwell, revisit via ReID | commute_wait, smoke_break, vendor, sit_rest, lost_tourist | rule + context; learned re-ranker |
| Hostile reconnaissance | repeated attention to security features (cameras, gates), photographing, revisits across cameras | gaze proxy (head orientation), gesture, MTMC revisits | photograph (tourist), lost_tourist | learned, indicator-based, low-priority queue |
| Tailgating / piggybacking | people crossing door line per access-control grant > 1 within Δt | door line count ↔ badge events | group_walk (legit groups, if policy allows) | rule + access-control fusion |
| Following | trajectory correlation between A and B over T | pairwise trajectory similarity | group_walk, queue | learned/pairwise |
| Abandoned / unattended object | object static > T, owner (last associated person) > d away | object tracking, owner association | vendor stall items, bins, deliveries | rule on object/person graph |
| Object hand-off | brief contact + object transfer | pose + object tracks | meet_and_greet | learned |
| Fight / aggression | rapid limb motion, close proximity, bystander ring/flee | pose sequence, crowd response | meet_and_greet (hug), child_play | learned (skeleton), audio corroboration |
| Person down / fall | transition to lying, persists > T | pose, box aspect, motion | sit_rest (lying on bench), drunk_walk | learned + persistence |
| Crowd surge / rush / gather | density above band, flow divergence, speed | density maps, optical flow | queue, event egress | scene-level model |
| Counter-flow | velocity opposed to dominant local flow | flow field | lost_tourist | rule on flow |
| Camera tamper | cover, spray, tilt, cut, glare, unplug (docs/11: 6 kinds) | IQA, scene-change vs reference | weather (rain on dome), night switch | IQA + rule |
| After-hours presence | any presence in closed hours | schedule | cleaners, security | rule + roster |
| Vehicle loiter / drop-off | vehicle stop + person exit + re-entry | vehicle/person association | taxi pick-up | rule |
| Drone intrusion | small airborne object over perimeter | small-object detection, RF | birds | detector + RF/radar |

### 1.1 Parameters are a product surface

Every rule's parameters (T, r, d, armed schedule) differ by site and zone.
SurvSim should therefore evaluate **parameter sweeps** rather than one setting:
for loiter T ∈ {60, 120, 300} s, produce detection-probability vs false-alarm-
rate curves, so a commissioning engineer can choose from a curve, not a guess.

---

## 2. Rule-based analytics done properly

### 2.1 Loitering, worked through

A robust rule [INF, consistent with R03 and vendor documentation such as
Axis/Bosch/Hanwha loitering analytics]:

```
for each global track g in zone Z (armed):
    dwell(g) = time since first entry, tolerant to gaps ≤ G_max (e.g. 20 s)
    spread(g) = 90th-percentile distance from centroid over window
    revisit(g) = count of re-entries within 30 min (needs ReID across cameras)
    if dwell ≥ T and spread ≤ r_max:           candidate LOITER
    if revisit ≥ k:                               candidate LOITER.REVISIT
    context: suppress if zone is a queue/platform during service hours,
             if role(g) ∈ {staff} (badge / uniform classifier), if weather shelter
```

The two failure modes are **fragmentation** (the track breaks, dwell resets, no
alarm — a miss) and **context blindness** (a commuter waiting for a bus — a false
alarm). Gap-tolerant dwell (`PathLoiterRule.reentry_gap_s`) and cross-camera revisit fix the first; context and
learned re-ranking fix the second. SurvSim's `loiter_intermittent` (leave and
return) and `commute_wait` (30–900 s, phone use) exist exactly to exercise both
(docs/03 §1–2).

### 2.2 Tailgating

The only reliable formulation fuses the access-control system: each badge
grant opens a window; count people crossing the door line in that window.
Vision-only tailgating (count ≥ 2 closely spaced crossings) has high false-
alarm rates at legitimate group entries [lore]. SurvSim models
"access-control logs" as a sensor extra (docs/02 §1) — the fused test is
therefore possible now.

### 2.3 Abandoned object

i-LIDS "Abandoned baggage detection" is one of the four *event-detection*
scenarios in the i-LIDS User Guide [1] (with parked vehicle detection, doorway
surveillance and sterile zone monitoring; the guide describes the library as
"based initially on six different scenarios", the others being tracking). The owner-association step is what separates
"unattended" (owner left) from "static object" (bins, stall goods). Design:

1. Detect and track bags/suitcases (COCO classes) plus a generic "new static
   object" detector via background modelling (dual-rate background subtraction
   is the classical method, still useful for unknown objects).
2. Associate object to the person whose track overlapped it at placement.
3. Alarm when owner is > d (e.g. 10–20 m) away or out of view for T (30–60 s)
   and the object persists.

SurvSim's `object_abandon` (walk away ≥ 20 m, no return) and `object_handoff`
provide positives; vendor stall goods and deliveries are needed as negatives.

### 2.4 Rule engines

Rules should be data (JSON/YAML/DSL) evaluated by an engine over the global
track stream, with complex-event-processing primitives: `within(zone)`,
`dwell ≥`, `crosses(line, dir)`, `near(object, d)`, `count(window)`,
`sequence(A then B within T)`. SurvSim's `eval/rules.py` is the rule baseline
and should share the same rule DSL as the product so tests transfer [INF].

---

## 3. Learned behaviour models

### 3.1 Inputs: pixels, pose or tracks?

| Input | Cost at scale | Strengths | Weaknesses |
|---|---|---|---|
| Raw video clips (I3D, SlowFast, VideoMAE, X-CLIP) | high: ~50–200 GFLOP per clip | appearance + motion; weapons, objects | expensive; site-specific appearance overfit |
| Pose sequences (ST-GCN, PoseC3D, CTR-GCN) | low once pose exists | viewpoint- and clothing-robust; privacy-friendlier | pose unreliable < 60 px; occlusion |
| Trajectories + scene graph (GNN, transformers) | very low | multi-agent interaction, long horizon | blind to fine motion |
| Audio (report 20) | low | screams, glass break, shouting | privacy law; urban noise |

For CCTV at standoff, the practical default is **pose for close/medium-range
interaction classes (fight, fall), trajectories for everything wide-area, and
clip models only as a second-stage verifier on triggered candidates** [INF].

References: ST-GCN (arXiv:1801.07455), PoseC3D (arXiv:2104.13586), CTR-GCN
(arXiv:2107.12213), SlowFast (arXiv:1812.03982), VideoMAE (arXiv:2203.12602).
For trajectory/interaction: Social-LSTM/Trajectron++ style models
(arXiv:2001.03093) and graph networks over agents.

### 3.2 Anomaly detection (weakly supervised / unsupervised)

UCF-Crime (Sultani et al., arXiv:1801.04264) popularised weakly supervised
multiple-instance learning over video-level labels; later methods (RTFM,
MGFN, VadCLIP) push frame-level AUC on UCF-Crime into the high 80s —
VadCLIP (Wu et al., AAAI 2024) reports 88.02 % AUC on UCF-Crime and 84.51 % AP
on XD-Violence [4]. R03 §8 explains why these numbers are misleading for
operations: frame-AUC averages over long normal stretches and ignores alarm
timing, and ShanghaiTech/Avenue "anomalies" (cycling on a walkway) are not
security events. **Use VAD as a ranking signal for operator review queues, not
as an alarm generator** [INF].

### 3.3 Fights and falls

* Fight datasets: RWF-2000 (arXiv:1911.05913), Hockey Fights, Movie Fights,
  surveillance-fight collections. RWF-2000's own Flow Gated Network
  baseline reaches 87.25 % test accuracy (Cheng, Cai & Li, ICPR 2020) [9] — but clip-level balanced accuracy on trimmed clips says
  nothing about false alarms per hour on untrimmed footage.
* Falls: largely lab datasets (UR Fall, Le2i); in-the-wild fall detection in
  CCTV is thinly benchmarked. Person-down with persistence (lying for > 30 s)
  is more robust than detecting the fall moment [lore].
* **Corroboration** — audio (shouting, impact), crowd response (bystanders
  forming a ring or fleeing; docs/03 `fight` includes this) — is how false
  alarms from horseplay are reduced.

### 3.4 Graph models on tracks

A per-scene graph with nodes = agents/objects/zones and edges = proximity,
gaze, following, carrying, enables classifiers for handoff, following, group
formation and tailgating without pixels. Spatio-temporal GNNs and transformers
over agent tokens are natural fits [INF]. Data requirement: long, multi-agent
sequences with interaction labels — which real footage almost never has and
SurvSim produces natively (world.parquet actual positions + events.jsonl).

### 3.5 Video-language models

Always-on VLM analysis at 1 fps costs ~0.36M tokens per camera-hour at default
resolution and ~1.1M at high resolution; D07's ~4.6M assumes 2 fps × 640
tokens/frame (AUDIT_43-47) — uneconomic rather than infeasible. The pattern is two-stage: cheap detector/rule triggers a candidate,
a VLM (or smaller video classifier) re-scores the clip with a site-specific
prompt ("is this person a uniformed worker performing maintenance?") and writes
a one-line explanation for the operator. Budget: if 1 % of 10-s clips
trigger and each triggered clip costs ~2k tokens, cost is ~7.2k tokens per
camera-hour [BOE: 360 clips/h × 1 % × 2k = 7.2k] — roughly 50–150× fewer tokens than always-on at 0.36–1.1M (~640× only
against the 4.6M research-protocol figure). Report 45's "170–400×" is a
*dollar* ratio under a sparser trigger model (20 triggers/camera-day × 2,364
input + 150 output tokens ≈ 2k input tokens/camera-hour, priced with output
tokens on both sides: Flash $112–240 vs $0.66, Flash-Lite $31–74 vs $0.18);
both are right under their own trigger rate — quote the rate with the ratio
(docs/research/49 §0).
SurvSim's value: VLM verifiers must be tested against hard negatives with
known truth, especially role disguise (`role_disguise`: intruder in hi-vis,
docs/03 §4).

---

## 4. Hard negatives: the design discipline

### 4.1 Why they dominate the metric

In real footage, suspicious events are rare: say 1 loiter-of-interest per
camera per week versus hundreds of benign dwells [INF/lore]. With base rate
p ≈ 10⁻³ of dwell episodes, even a 99 %-specific classifier yields ~10 false
alarms per true one [BOE: 0.01 × 999 ≈ 10]. Precision is dominated by
negatives that *look like* positives, not by random negatives.

### 4.2 Pairing (from docs/03)

| Positive | Look-alike negatives |
|---|---|
| loiter | commute_wait, smoke_break, vendor, sit_rest, lost_tourist |
| recon | photograph (tourist), worker_patrol looking at cameras |
| asset_tamper, camera_tamper | maintenance (with tools, kneeling at asset) |
| fight | meet_and_greet (hug), child_play |
| person_down | sit_rest (lying on bench), drunk_walk |
| outfit_change / concealment | weather_reaction (hood up in rain) |
| wrong_zone_entry | worker_patrol (authorised), role_disguise (the adversarial twist) |
| following | group_walk, queue |
| erratic_motion | lost_tourist, child_play |

The adversarial modifiers (§4 of docs/03 — `role_disguise`, `crowd_cover`,
`camera_aware_timing`, `decoy_partner`) are the "hard positives": positives
engineered to look like negatives. A mature evaluation reports both.

### 4.3 Confound audits

SurvSim's evasion module has a "confound audit" (docs/11) — checking that a
positive is not trivially separable by a spurious cue (e.g. all intruders wear
black). This is the synthetic-data equivalent of shortcut learning checks and
must run on every generated dataset: for each label, train a trivial classifier
on metadata-only features (clothing colour, time of day, camera) and require
near-chance accuracy [INF].

---

## 5. Evaluation: operator-tolerance metrics

### 5.1 i-LIDS-style event scoring

The primary source is the Home Office i-LIDS User Guide [1]. For event-
detection scenarios it says: *"Systems have ten seconds to report an alarm
state after an alarm event begins in the evaluation footage. During this time
multiple alarm reports will be disregarded; an alarm event is either detected
or not. After this ten second window, any further alarms reported will be
deemed 'false positives'."* It also says *"Where a system false alarms several
times in quick succession, only one false positive alarm will be logged every
five seconds."* Systems must *not* keep alarming for the whole event, and
simultaneous events need separate alarms. Performance is a weighted F1: recall
r = a/(a+c), precision p = a/(a+b). A scenario-specific **recall bias α** is
set higher for the "Event Recording" role than for "Operational Alert", where
false alarms cost operator attention. The guide gives an application-stage
acceptance criterion of **overall F1 ≥ 0.7**, and warns that the i-LIDS
performance level itself is "considerably more stringent". Alarm events are
scenario-defined, for example *"a parked vehicle in a defined zone for more
than 60 seconds"*. The underlying standard paper is HOSDB's "i-LIDS: A
Standard for Testing Video Based Detection Systems" (IEEE ICCST 2006) [1].

SurvSim implements the core rule: `survsim/eval/alarms.py` uses
`DEFAULT_TOLERANCE_S = 10.0`, and `score()` counts an alarm as a hit only
between `t_start` and `t_start + tolerance`. A correct-but-late alarm is
counted as a false positive, and each event can be detected only once.
**Default divergence, now flagged:** by default `score()` counts every repeat
alarm as a false positive (`repeat_alarms`), whereas i-LIDS disregards repeats
inside the 10-s window and logs at most one false positive per 5 s. SurvSim's
default is therefore harsher than i-LIDS for systems that chatter. `score()`
already takes `ilids_compat=True` (with `fa_coalesce_s = DEFAULT_FA_COALESCE_S
= 5.0`) to reproduce both i-LIDS rules; the recall-bias-weighted F1 is not yet
implemented (plain F1 only). The guide's recall bias values are
Operational Alert α = 0.35 and Event Recording α = 35 (scenario definition
appendix) [1].

**Protocol details that matter [INF]:**
* **Onset definition.** "Detectable from" time, not behaviour start: a loiter
  becomes detectable at T after entry; a fence cut when the cutting begins on
  camera. SurvSim emits behaviour start/end and a "plausible-observer difficulty
  score" (docs/03 §6); it should also emit `detectable_from` per camera, using
  `usably_visible` (principle 5). Listed as a gap in report 23.
* **One alarm per event.** Duplicate alarms within an event window count once
  (or as FAs, depending on policy — state which).
* **Alarms in unlabelled time are FAs**, including alarms on hard negatives.
* **Per-camera-hour normalisation** uses armed hours only.

### 5.2 ActEV

NIST ActEV/DIVA (R03 §2) scores activity detection as probability of missed
detection at a fixed rate of false alarms, where RFA is false-alarm instances
per *minute* of video: the SRL leaderboard ranks on Pmiss@RFA = 0.1; the ActEV scorer's
ActEV18_AD protocol reports Pmiss at RFA = 1, 0.2, 0.15, 0.1, 0.03, 0.01
(which of these ActEV18 used as primary is [unverified]); from ActEV19_AD a
time-based false-alarm measure (Tfa) is used [2]; the corpus notes research operating points around ~6 FA per camera-
hour are ~3 orders of magnitude looser than a control room tolerates (corpus
fact 1). Report both: ActEV-style for comparison with literature, i-LIDS-style
for customers.

### 5.3 The false-alarm budget [BOE]

Assume an operator can meaningfully assess one alarm per ~2 minutes while also
doing other work, with ≤ 20 % of time on nuisance: ≈ 6 nuisance alarms per
operator-hour. At 1 operator per 50 cameras (a common UK ratio range is 1:16 to
1:100+, D06), the budget is **0.12 nuisance alarms per camera-hour**, or ~1 per
camera per 8 hours. Across 10 analytic types, that's ~0.012 per type per
camera-hour. Compare: ActEV-like 6/camera-hour is 50× the *whole* budget.

This is why corroboration and context are architectural, not features.

**Measured (H12, `9dea4f9`, `32` §H12).** On 3,002 clean mock camera-hours
(676 worlds, all six site types, 74,989 innocent people, no loiterers) with
*perfect* tracks, single-cue loiter rules land at dwell_60 **4.55**, dwell_25
**6.01**, path_loiter_25 **20.7** and path_loiter_15 **87.4** FA/cam-h (Garwood
95 % CIs ±1–2 %) — **4,500–87,000× the assumed 0.001 budget**, and 38–730× even this
section's gentler 0.12. i-LIDS 5 s coalescing removes 7–59 % and never touches
recall. Recall at a 30 s tolerance on 360 loiter events, window-only:
dwell_25 0.90, path_loiter_15 0.97, dwell_60 0.16 — but window-only scoring
credits any alarm in the event window, including alarms on bystanders;
requiring the alarm to be on the actor (H58 round 2) gives dwell_25 **0.367**
and dwell_60 **0.000**, so quote only actor-aware recall for alarms. The nuisances are the hard negatives
(commute_wait + queue ≥ 90 % of DwellRule alarms) and, for PathLoiterRule,
ordinary transit (54 % of path_loiter_15's). The world-cluster bootstrap CI is
~3× wider than Garwood: false alarms cluster by world. This replaces the H5
0.35-camera-hour figures (11–143 FA/cam-h) wherever the budget is argued;
the absolute rates are conditional on an unvalidated archetype mix, the gap
(3.6–4.9 orders of magnitude) is not.

**Best measured rule (H58 round 2, `44e34f5`, doc 58 §6).** A learned loiter
classifier on track features (`LearnedLoiterRule`, θ 0.9, clock ≥ 10 s),
retrained after the zone-centroid leak fix: **3.745 FA/cam-h [3.676, 3.815]** (round 2; superseded by round-3 A1 2.915 / 0.825, `bcbe9d2`),
actor-aware recall **0.831 [0.792, 0.869]**, precision 0.326, recall@10 s 0.097
— 1.60× fewer false alarms than dwell_25 (round 1's 2.06× is superseded) at
2.3× its actor-aware recall. Still ~3,700× over our assumed 0.001 (≈ 1.25 operators of
dismissals at 40 cameras × 30 s per check). Label oracle recall 1.000; the
motion-only kinematic-twin floor (smoke breaks in gate zones) is 1.008
FA/cam-h, so the remaining gap is exactly the context/corroboration problem
this section describes. Verdict: ship the learned rule, score actor-aware.

### 5.4 Reported outputs (per behaviour type, per site class, per profile)

1. Pd at tolerance, with 95 % CI (Wilson) — events are few; CIs are wide.
2. FA per camera-hour (armed), split into: on hard negatives / on background /
   on system faults (tamper, glitches).
3. Time-to-alarm distribution.
4. Pd vs T-parameter curve (§1.1).
5. Degradation curve (day → legacy SD → night IR).
6. After-policy operator load (alarms per operator-hour) at the chosen point.

---

## 6. Crowd analytics

Crowd safety analytics (density, flow, surge) is distinct from person-level
security (R03, D06). Fruin levels of service and the fundamental diagram
(speed vs density) are the physical grounding; SurvSim's crowd model already
has density bands, fundamental diagram and surge (docs/11). Densities above
~2 persons/m² make per-person tracking unreliable; crowd-counting networks
(CSRNet, arXiv:1802.10062; DM-Count; P2PNet) on density maps take over.
Critical densities: Fruin's level-of-service F — above roughly 5.4 persons/m²
in G. Keith Still's summary — is where individual movement becomes impossible
and compressive forces become lethal; ~4.7/m² is described as typical in and around
Wembley Stadium (the Green Guide standing figure) (Still, PhD thesis, Warwick 2000; Fruin LoS pages) [12]. Surge detection is
a change in the flow field (speed increase + density increase + direction
convergence). SurvSim's crowd-density bug (docs/11 bug 13) — counting only
visible people — is exactly the error a real density estimator makes; GT must
count all.

---

## 7. What labelled data the simulator must generate

### 7.1 Per event (events.jsonl)

```
{ event_id, type (full path e.g. plaza.intruder.loiter.pace), subjects[],
  t_start, t_end, t_detectable_from{cam: t}, zone_id, severity,
  difficulty_score, hard_negative_for[], adversarial_modifiers[],
  continuous: {dwell_s, dist_to_asset_m, aggression_intensity},
  observed_by{cam: [intervals usably_visible]} }
```
Existing: path labels, start/end, severity, difficulty, hard-negative tags,
continuous attributes (docs/03 §6). **To add**: `t_detectable_from` per camera
and `observed_by` intervals (computed from the same `usably_visible`).

### 7.2 Per tick (world.parquet)

Actual positions after avoidance (principle 1), heading, head yaw (gaze proxy
for recon), pose/bones (Unreal), carried-object state, role/badge, zone
membership.

### 7.3 Context feeds

Schedules (armed/disarmed), access-control events, staff rosters,
weather/lighting, maintenance tickets — so context-aware suppression can be
tested. Access-control logs exist (docs/02); schedules and rosters should be
emitted as scenario metadata.

### 7.4 Volume targets [BOE]

To estimate FA/camera-hour at the 0.01 level with ±50 % relative error you
need ~400 camera-hours of negative time per behaviour type [BOE: Poisson,
expected 4 FAs; relative SE = 1/√4 = 50 %]. At the render throughput in docs/11
(~11 frames/s at 720p) and 5 fps analysis, 400 camera-hours = 7.2 M frames ≈
180 h of rendering plus degradation — feasible only with the mock backend for
trajectory-level behaviour models, or with a much faster render path.
**Conclusion [INF]: evaluate trajectory/rule analytics at scale on mock-backend
worlds (validated against rendered subsets), and reserve rendered footage for
pixel-dependent models (fight, fall, tamper, detection-limited loiter).**

---

## 8. Legal and ethical constraints on behaviour analytics

(R03 §9 and report 21 in detail.) Under the EU AI Act, emotion recognition in
workplaces/education is prohibited, and several biometric categorisation and
real-time remote biometric identification uses are prohibited or high-risk
(Regulation (EU) 2024/1689, https://eur-lex.europa.eu/eli/reg/2024/1689/oj).
Behaviour analytics that do not identify people are not per se high-risk, but
"predicting criminal offences based solely on profiling" is prohibited (Art. 5)
— another reason to present indicators, not intent. In the UK, the ICO's
video surveillance guidance and the Surveillance Camera Code require
proportionality and DPIAs. Fairness: disabled mobility (`disabled_mobility`
in docs/03) and different gaits must not generate "erratic motion" alarms —
SurvSim can audit that directly.

---

## 9. Recommended build order for behaviour analytics

1. Zone/line/dwell rules on ground-plane global tracks + tamper health (M1).
2. Hard-negative-rich evaluation with i-LIDS timing and FA budgets (exists;
   add `t_detectable_from`).
3. Context suppression (schedule, role, weather) — quick FA wins.
4. Corroboration with access control / second camera / audio (report 20).
5. Pose-based person-down and fight on triggered crops.
6. Trajectory/graph models for following, recon indicators, handoff.
7. VLM verifier on triggered clips with explanation text.

Each step must lower FA/camera-hour at fixed Pd on the SurvSim hard-negative
suite *and* on a real pilot dataset — or it doesn't ship.

## 10. A worked alarm funnel [BOE]

Take a 50-camera transport site, 24 h armed, loiter analytic, T = 120 s.

| Stage | Candidates per day | Assumption |
|---|---|---|
| Raw dwell ≥ 120 s on tracks | ~2,400 | ~2 benign long dwells per camera-hour at a station |
| After track-gap tolerance (removes fragment artefacts, adds a few true) | ~2,400 | fragmentation mostly causes misses, not FAs |
| After context (queues/platforms in service hours suppressed) | ~480 | 80 % of dwell occurs in queue zones |
| After role suppression (staff by uniform/badge) | ~360 | 25 % of remainder are staff |
| After persistence + revisit requirement for low-priority zones | ~90 | only revisits or ≥ 300 s alarm in open concourse |
| After learned re-ranker (behaviour-level classifier, 90 % specificity on residual) | ~9 | trained on SurvSim hard negatives + site data |
| **Alarms to operators** | **~9/day ≈ 0.0075 per camera-hour** | inside the §5.3 per-type budget |

Recall cost must be measured at each step: context suppression is the most
dangerous because a hostile actor who *behaves like* a commuter in a queue zone
passes silently — which is precisely `role_disguise`/`crowd_cover` in docs/03 §4.
SurvSim should publish the funnel with Pd after each stage, not just the end
number, so the customer sees where recall went [INF]. `eval/pipeline.py` already
implements the stages; exporting per-stage counts is a small change.

## 11. Reconnaissance indicators, concretely

"Hostile reconnaissance" (NPSA — formerly CPNI — guidance,
https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance, which
also promotes the SCaN "See, Check and Notify" staff programme) [13] is detected by trained humans through indicators: unusual
attention to security measures, photographing access points, repeated passes,
testing responses, note-taking, loitering at vantage points. Machine proxies
(all [INF], to be validated):

| Indicator | Machine proxy | Needed GT from SurvSim |
|---|---|---|
| Attention to cameras/guards | head yaw toward known security features, dwell ≥ 3 s each | head-yaw per tick; list of security-feature positions |
| Photographing | phone-raised pose held toward a target | gesture label + target id |
| Repeated passes | ≥ k MTMC revisits of the same area within hours | global identity across epochs (outfit change) |
| Vantage dwelling | dwell at points with high visibility of assets | asset visibility map (rig analysis can compute) |
| Testing response | approach barrier, retreat, watch reaction | sequence labels (probe → retreat) |

These are low-priority "watch list" signals feeding an analyst queue, not
alarms. Their evaluation is ranking quality (e.g. recall@k of recon subjects
among all subjects of a day), which SurvSim's retrieval metrics (`eval/
retrieval.py`: recall@k, MRR) can compute.

## 12. Training learned behaviour models with SurvSim

1. **Pre-train on trajectories from the mock backend at scale** (millions of
   agent-hours are cheap; no rendering) for trajectory/graph models; validate
   the trajectory distribution against real pedestrian datasets (ETH/UCY,
   SDD, MOT20 speeds — docs/14 measured walking speed from boxes) so the model
   is not learning simulator physics.
2. **Pose models on rendered MetaHuman sequences** (the bones are GT from the
   Unreal backend) *plus* pose estimated from the degraded render — train on
   estimated pose, because that is what production sees.
3. **Mix with real clips** (RWF-2000, NTU RGB+D 120 for action primitives —
   114k clips, 120 classes, 106 subjects; Liu et al., TPAMI 2020, arXiv:1905.04757) [11] and site data from pilots.
4. **Hold out by scenario template and by site class** (report 21), never by
   clip, and keep the adversarial-modifier variants entirely in test for a
   "robustness" score.
5. **Calibrate** the output scores (temperature / isotonic) on real validation
   data before setting thresholds; synthetic-calibrated thresholds will be
   wrong [INF].

## 13. Worked example 1 — `disguise_and_tamper`

`configs/scenarios/disguise_and_tamper.yaml` runs 240 s at 10 fps on the mock
engine (seed 11), set in a compound with:

- four cameras: `cam_gate` 1080p, 70° HFOV; `cam_yard` 720p dome, 95°;
  `cam_sub` 1080p, 60°, sprayed at t = 150 s; and `cam_ptz`, which patrols the
  gate, fence and substation presets with 20 s dwell each at 40°/s;
- five zones: `zone.gate_A`, `zone.yard`, `zone.substation`, `zone.fence_north`,
  and `zone.blindspot_A`, which `survsim rig` verifies as unobserved.

The substation zone is restricted with `allowed_roles: [worker, guard]`.

### 13.1 The ground-truth event stream

The hero `intruder_a` (1.83 m, hoodie with a navy rain jacket, beanie, small
backpack, `camera_awareness 0.9`, `face_hiding 0.7`) runs through eight steps.
Each maps to one row of the §1 table:

| # | Intent step | GT label | Analytic that should fire | What makes it hard |
|---|---|---|---|---|
| 1 | transit spawn.east → gate_A | normal | — | — |
| 2 | recon targets cam_gate, cam_sub, door.substation, 6 s each at 7 m | `suspicious.recon` | recon indicators (§11) | 6 s dwell is below any sensible loiter threshold; only head orientation separates it |
| 3 | loiter gate_A, 30 s, pace, r = 3 m | `suspicious.loiter` | loiter rule | 4 `commute_wait_negative` generators dwell 30–60 s in the same zone |
| 4 | outfit_change in blindspot_A (outer removed, cap, light top, slow gait, mask) | `suspicious.appearance.change` | none at the moment it happens: it is unobservable by construction | cross-epoch ReID must reconnect the identity afterwards |
| 5 | perimeter_probe fence_seg_12, 8 m along the fence | `suspicious.probe.fence` | perimeter-probe rule | only covered while the PTZ sits on its `fence` preset (20 s in every ~70 s cycle) |
| 6 | camera_tamper cam_sub, spray, 4 s | `hostile.tamper.camera` | IQA tamper detector on cam_sub; the approach is visible on other cameras | the camera being attacked is the one that goes blind |
| 7 | wrong_zone_entry substation, 25 s | `suspicious.access.intrusion` | sterile-zone rule | cam_sub is blind by then; coverage relies on the PTZ `substation` preset |
| 8 | transit brisk → exit.west | normal | — | — |

The hard negatives are:

- `worker_1` (hi-vis, hardhat) stands idle for 90 s inside `zone.substation`,
  the textbook tamper and intrusion false positive, and is an authorised role.
- Generators add 4 `commute_wait_negative` (30–60 s in gate_A), 3 `passer_by`
  in the yard and 1 generated `loiterer` (40–70 s in gate_A, a positive).
- `tailgater_1` follows worker_1 through `door.substation` with a 1.2 m gap.
  This is a *positive* for `suspicious.access.tailgate`, but vision alone
  cannot tell it from two colleagues walking in together.

### 13.2 Expected analytic behaviour, stage by stage

- **Loiter.** The dwell baseline in `survsim/eval/rules.py` (`DwellRule`,
  defaults `threshold_s = 60`, `speed_cap_mps = 0.5`, zone tags `gate`,
  `restricted`, `perimeter_fence`) does **not** fire on the 30-s pacing
  loiter: it needs 60 s below 0.5 m/s, and pacing breaks the dwell. It
  **does** fire on worker_1 at 60 s into its 90-s idle (substation is tagged
  `restricted`), and can fire on a commuter whose sampled 30–60 s dwell reaches
  60 s [INF, not re-run]. So the default rule has recall 0 on the hero and at least one
  false alarm on a hard negative. That is the design intent of the scenario,
  and the reason a loiter analytic needs spatial spread rather than a speed
  cap — which `PathLoiterRule` in `survsim/eval/rules.py` already implements
  (90th-percentile distance from centroid ≤ `radius_m` = 4.0 over
  `window_s` = 30, with `reentry_gap_s` = 20 gap tolerance).
- **Learned classifier.** `BehaviourClassifier` works on 30-s windows with a
  15-s step (`segments_from_world`). Its features include `dwell_fraction`,
  `path_tortuosity`, `direction_changes`, `radius_of_gyration` and
  `zone_revisits`, which separate "pacing within 3 m" (high tortuosity and
  direction changes, small radius) from "standing idle" (low speed, near-zero
  tortuosity). docs/14 records the honest outcome at scale: AUC 0.72 but
  precision 0.074, because suspicious windows are 3.3 % of the data. That is
  the base-rate arithmetic of §4.1 again.
- **Alarm pipeline.** `AlarmPipeline` in `survsim/eval/pipeline.py` then
  applies its stages in order:
  1. `threshold`;
  2. `zone_context` (`priority_zones`, if set);
  3. `after_hours` (only if configured and an hour-of-day clock is passed);
  4. `persistence` (default 2 detections within 60 s);
  5. `corroboration` (any channel ≥ 0.5; only when `require_corroboration=True`, default False);
  6. `deduplicate` (one alarm per person-event, 120 s gap);
  7. `operator_budget` (`max_alarms_per_camera_hour`).

  For this scenario, `priority_zones = (zone.gate_A, zone.substation,
  zone.fence_north)` removes yard passers-by. Persistence at 2 × 15-s windows
  keeps the 30-s loiter (it spans two windows) but not a one-window glitch.
  Corroboration from the access-control sensor extra (a badge event for
  worker_1 at `door.substation`) is what should suppress worker_1 — and it
  should *also* flag tailgater_1, because two bodies crossed on one grant.
- **Timing.** Camera-hours here are 4 cameras × 240 s = 0.267 h. A single
  false alarm is therefore 3.75 FA/camera-hour. **Short scenarios cannot
  estimate FA rates.** They test logic. FA estimation needs the §7.4 volumes
  (≈ 400 camera-hours per type), meaning many seeds or long runs. H12 did
  this on the mock backend: 676 worlds × 30 min = 3,002 camera-hours in 99 min
  on 11 CPU workers — the §7.4 conclusion (trajectory rules at scale on mock)
  holds in practice.
- **Coverage-aware scoring.** After t = 150 s, `cam_sub` emits nothing
  (principle 2). An intrusion alarm for step 7 can only come from the PTZ,
  which dwells on `substation` for 20 s in each ~70-s patrol cycle
  (3 × 20 s dwell plus slews). A system that misses step 7 is not
  necessarily at fault: GT must say whether the event was observable at all
  (`observed_by` intervals, §7.1). Otherwise recall is charged for physics.

### 13.3 What this scenario proves and does not prove

It proves that the evaluation chain is wired, that hard negatives generate
false alarms under naive rules, that tamper removes GT, and that the outfit
change happens unobserved. It does not measure a rate. The acceptance test
for a behaviour analytic on this scenario is qualitative, and should be
written as a test: loiter recall on `intruder_a` > 0, no loiter alarm on
`worker_1` once badge corroboration is on, a tamper alarm on cam_sub within
10 s of t = 150 s, and a tailgate alarm for tailgater_1.

## 14. Worked example 2 — `street_crowd`

`configs/scenarios/street_crowd.yaml` is a 60-s, 10-fps plaza rendered from
three real-mount cameras: 3.5–5 m high, 18–25° down, 70–95° HFOV, 720p, with
people 60–200 px tall. The hero pair is `loiterer_1` (25-s pacing loiter in
`zone.gate_A`, r = 2.5 m) and `commuter_1` (`hard_negative_for: [loiter]`,
25-s idle `commute_wait` in the same zone). Around them the generators add
12 `passer_by`, 3 `commute_wait_negative` (20–40 s) and 1 `loiterer`
(30–50 s). This is the scenario behind the batch_v1/batch_v4 renders
(docs/15 uses `out/batch_v1/street_crowd_day/render/cam_02` as its tuning
set), so the same event can be scored on pixels, not only on world state.

Two lessons follow:

1. **Loiter and commute_wait are separable only by motion texture.** Both
   dwell 25 s in the same polygon. Pacing within 2.5 m yields speed ~0.3–0.8
   m/s with frequent reversals; idle waiting yields < 0.2 m/s with small
   shuffles. A pixel pipeline must preserve that texture through detection
   jitter. Box-centre noise of ±5 px at 100 px person height is roughly
   ±9 cm on the ground, and differentiating that into velocity at 10 fps
   gives ~±1 m/s of speed noise ([BOE]: 0.09 m × 10 Hz). Speed features
   therefore need smoothing over ≥ 1 s. A classifier trained on clean
   world-state speeds and deployed on tracker output will mistake the idle
   commuter for a pacer. **Train on tracker output, not on `world.parquet`.**
2. **A 60-s clip cannot contain a 60-s-threshold alarm.** With the default
   `DwellRule(threshold_s=60)`, no event is possible. The i-LIDS approach
   defines the alarm event relative to the threshold ("present for more than
   60 s") [1], so the scenario must be longer than threshold + tolerance.
   Scenario validation should reject configs where every positive's duration
   is shorter than the configured rule threshold [INF].

## 15. Concrete interfaces

### 15.1 Candidate event (analytics → alarm policy)

This extends `Candidate` in `survsim/eval/pipeline.py` (which already has
`t, uid, label, confidence, camera, zone, corroborating`) with the fields a
production system needs:

```json
{
  "schema": "survsim.candidate/2",
  "event_id": "c-2026-09-26T03:12:44.100Z-gateA-0017",
  "label": "suspicious.loiter",
  "t_detect_utc": "2026-09-26T03:12:44.100Z",
  "t_onset_est_utc": "2026-09-26T03:11:44.000Z",
  "site_id": "compound", "zone_id": "zone.gate_A",
  "subjects": [{"global_id": "g-481", "local": [["cam_gate", 17]], "role_est": "unknown"}],
  "confidence": 0.81,
  "features": {"dwell_s": 60.1, "radius_of_gyration_m": 1.9, "zone_revisits": 0},
  "evidence": [{"camera": "cam_gate", "pts_from": 1204, "pts_to": 1804,
                "bbox_xywh": [812, 402, 44, 118]}],
  "camera_health": {"cam_gate": "ok"},
  "corroborating": {"access_control": 0.0, "audio": 0.0},
  "producer": {"name": "rule.dwell", "version": "1.4.0", "config_hash": "sha256:..."}
}
```

### 15.2 Alarm (policy → operator / VMS)

```json
{
  "schema": "survsim.alarm/1",
  "alarm_id": "a-000912", "from_candidates": ["c-...-0017"],
  "priority": 2, "label": "suspicious.loiter",
  "raised_utc": "2026-09-26T03:12:46.300Z",
  "policy": {"version": "site-compound-7", "stages_passed":
             ["threshold", "zone_context", "persistence", "deduplicate"]},
  "explanation": "Dwell 60 s within 1.9 m in Gate A (armed 22:00-06:00)",
  "clip": {"camera": "cam_gate", "from_utc": "...", "to_utc": "..."},
  "disposition": null
}
```

The `disposition` field is filled by the operator
(`true | false | nuisance`, plus a `reason` code) and is the input for
report 21's active learning.

### 15.3 Rule configuration keys

Rules are data. The following mirrors `DwellRule` and `AlarmPipeline`
parameters that exist today:

```yaml
rules:
  - id: loiter.gateA
    type: dwell                        # DwellRule
    zones: [zone.gate_A]               # or zone_tags: [gate, restricted]
    threshold_s: 60                    # DwellRule.threshold_s
    speed_cap_mps: 0.5                 # DwellRule.speed_cap_mps
    max_radius_m: 3.0                  # exists as PathLoiterRule.radius_m (default 4.0)
    gap_tolerance_s: 20                # exists as PathLoiterRule.reentry_gap_s
    revisit: {window_s: 1800, min_count: 2}   # proposed, needs MTMC
    label: suspicious.loiter
    schedule: {armed: ["22:00-06:00"]}
  - id: abandon.concourse
    type: abandoned_object             # AbandonedObjectRule
    owner_distance_m: 15
    static_s: 45
policy:                                # AlarmPipeline
  threshold: 0.5
  priority_zones: [zone.gate_A, zone.substation, zone.fence_north]
  after_hours: [22, 6]
  persistence_windows: 2
  persistence_span_s: 60
  require_corroboration: false
  corroboration_min: 0.5
  max_alarms_per_camera_hour: 0.12     # §5.3 budget
scoring:
  tolerance_s: 10                      # i-LIDS [1]
  ilids_compat: true                   # exists in score(): repeats ignored, 5-s FA coalescing
```

## 16. Commercial landscape — what vendors ship

These are public claims, not tested performance. Prices are rarely published.

| Vendor / product | Behaviour analytics offered (public material) | Deployment | Pricing (public) |
|---|---|---|---|
| **Axis** — Loitering Guard, Fence Guard, Motion Guard (AXIS Guard Suite); AXIS Object Analytics | Loitering per object or per area, with one include area and three exclude areas per profile; virtual tripwire; object-classified line and area rules | on camera (ACAP) | **free** on supported cameras (firmware ≥ 7.10 for Loitering Guard) [14] |
| **Hanwha Vision** — Wisenet AI cameras, AI Analytics Box AIB-800A | Virtual line (crossing and direction), area (intrusion, loitering, enter/exit), object detection | on camera or box beside the VMS | quote [15] |
| **Genetec** — Security Center + KiwiVision | Intrusion, loitering, left/removed object, people counting, queue | server plug-in to the VMS | quote [16] |
| **Avigilon (Motorola Solutions)** — Unusual Activity/Motion Detection, Appearance Search | Rules-free learned "unusual" motion/activity; loitering, crowd formation; appearance search | camera + ACC/Unity VMS | quote [17] |
| **BriefCam** (in Milestone Systems / Canon Group since 2024) | Video synopsis, forensic search, real-time alerts, rules | server | per-sensor licence, one-off purchase plus maintenance. A 2011 IPVM report gave MSRP $150 per on-demand and $450 per live channel; current prices are quote-only [18] |
| **Ipsotek (Eviden)** — VISuite | Patented Scenario-Based Rule Engine (SBRE) for multi-step behaviours; deployments in 44+ countries (vendor claim) | server | quote [19] |

The implications for our product are all [INF]:

- **Single-rule loitering and intrusion are commoditised.** They are free on
  Axis cameras. A company cannot sell them.
- The sellable layer is what is on top: cross-camera revisit, context and
  corroboration, verified false-alarm rates, and multi-step scenarios.
- Ipsotek's SBRE shows that multi-step behaviour grammars are an established
  product category. Our rule DSL (§15.3) should support `sequence()` from
  day one.
- Avigilon's "no-rules" unusual-motion detection is the learned-anomaly
  approach. §3.2 argues it is better used as a ranking signal, and Avigilon
  in fact positions it for surfacing events to operators.
- No vendor publishes FA/camera-hour against hard negatives. A SurvSim-backed
  verified envelope (report 21 §10) is a differentiator.

## 17. What SurvSim must emit — checklist

| # | Item | Module | State |
|---|---|---|---|
| 1 | Behaviour path labels, start/end, severity, hard-negative tags | `survsim/director/behaviours.py` (class `label`), `survsim/gt/writers.py` (events.jsonl) | have |
| 2 | Continuous attributes per tick (dwell_s, dist_to_asset_m, intensity) | `survsim/gt/writers.py` (world.parquet) | have (docs/03 §6) |
| 3 | `t_detectable_from` per camera per event | `survsim/gt/writers.py` + `survsim/core` geometry (`usably_visible`) | **missing** |
| 4 | `observed_by` visibility intervals per event per camera, honouring tamper/PTZ | camera director + geometry | **partial**: `observed_by` camera list exists only for appearance-change events (`director/world.py`); no intervals for other events |
| 5 | Access-control events (badge grant per door, per person) | sensor extras in the Director | have: verify tailgate truth links grant ↔ bodies |
| 6 | Head yaw / gaze-target per tick for recon | `survsim/director/behaviours.py` (Recon) → world.parquet | partial: recon targets exist, head yaw export to confirm |
| 7 | Schedules / rosters / armed state as scenario metadata | scenario loader (`survsim/models`) | **missing** |
| 8 | Candidate schema v2 fields (evidence, producer, camera_health) | `survsim/eval/pipeline.py` `Candidate` | partial |
| 9 | Per-stage funnel with Pd and FA per stage | `survsim/eval/pipeline.py` `StageReport` | partial: counts only, no per-stage Pd |
| 10 | i-LIDS compatibility mode (ignore repeats in window, 5-s FA coalescing, recall-bias F1) | `survsim/eval/alarms.py` `score()` | **partial**: `ilids_compat` does repeats + 5-s coalescing; recall-bias F1 missing |
| 11 | Scenario validation: positive duration ≥ rule threshold + tolerance | `survsim validate` | **missing** |
| 12 | Tracker-output features for behaviour training (not world-state) | `survsim/eval/behaviour.py` `segments_from_world` → add `segments_from_tracks` | **missing** |
| 13 | Crowd density GT counting occluded people | `survsim/director/crowd.py` | have (bug 13 fixed) |
| 14 | Long-duration negative time (≥ 400 camera-h per type) | mock backend + `survsim/generator` | feasible, not generated |

---

## References

1. Home Office CAST, *Imagery Library for Intelligent Detection Systems — The i-LIDS User Guide* (10/11). https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf ; HOSDB, "i-LIDS: A Standard for Testing Video Based Detection Systems", IEEE ICCST 2006. https://ieeexplore.ieee.org/document/4105319 — verified (10-s window, 5-s FA coalescing, F1 with recall bias, F1 ≥ 0.7 application criterion).
2. NIST, ActEV leaderboards and scorer (Pmiss@RFA; RFA per minute; Tfa). https://actev.nist.gov/SRL ; https://github.com/usnistgov/ActEV_Scorer — verified.
3. W. Sultani, C. Chen, M. Shah, "Real-world Anomaly Detection in Surveillance Videos", CVPR 2018. https://arxiv.org/abs/1801.04264 — verified (128 h, 1,900 videos, 13 anomaly classes).
4. P. Wu et al., "VadCLIP", AAAI 2024. https://arxiv.org/abs/2308.11681 — verified (88.02 % AUC UCF-Crime, 84.51 % AP XD-Violence).
5. S. Yan, Y. Xiong, D. Lin, "ST-GCN", AAAI 2018. https://arxiv.org/abs/1801.07455 — verified.
6. H. Duan et al., "Revisiting Skeleton-based Action Recognition" (PoseC3D), CVPR 2022. https://arxiv.org/abs/2104.13586 — verified.
7. Y. Chen et al., "CTR-GCN", ICCV 2021. https://arxiv.org/abs/2107.12213 — verified.
8. C. Feichtenhofer et al., "SlowFast Networks", ICCV 2019. https://arxiv.org/abs/1812.03982 ; Z. Tong et al., "VideoMAE", NeurIPS 2022. https://arxiv.org/abs/2203.12602 — verified.
9. M. Cheng, K. Cai, M. Li, "RWF-2000", ICPR 2020. https://arxiv.org/abs/1911.05913 — verified (87.25 % baseline).
10. T. Salzmann et al., "Trajectron++", ECCV 2020. https://arxiv.org/abs/2001.03093 — verified.
11. J. Liu et al., "NTU RGB+D 120", TPAMI 2020. https://arxiv.org/abs/1905.04757 — verified.
12. G. K. Still, *Crowd Dynamics*, PhD thesis, Univ. of Warwick 2000, https://www.crowdrisks.com/uploads/1/4/6/1/146195766/2000_still.pdf ; Fruin LoS summary https://www.gkstill.com/Support/crowd-flow/fruin/index.html ; Y. Li et al., "CSRNet", CVPR 2018, https://arxiv.org/abs/1802.10062 — verified via search extracts (the 5.4/m² LoS F and 4.7/m² Wembley figures come from those extracts).
13. NPSA, Hostile Reconnaissance guidance. https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance — verified.
14. Axis Communications, AXIS Loitering Guard / Fence Guard product pages and datasheet. https://www.axis.com/products/axis-loitering-guard ; https://www.axis.com/products/axis-fence-guard — verified (free licence).
15. Hanwha Vision, AIB-800A AI Analytics Box. https://hanwhavisionamerica.com/product/aib-800a/ — verified via search extract.
16. Genetec KiwiVision (reseller description). https://callmc.com/genetec-kiwivision/ — secondary source.
17. Avigilon, "Unusual Activity Detection" design guide. https://docs.avigilon.com/bundle/designing-site-for-analytics/page/uad/unusual-activity-detection.htm — verified via search extract.
18. BriefCam FAQ on licensing, https://www.briefcam.com/company/resources/faq/is-the-briefcam-license-purchase-a-one-time-cost-or-is-it-a-yearly-reoccurring-cost/ ; IPVM, "BriefCam Enterprise Examined" (2011), https://ipvm.com/reports/examing-briefcam-enterprise — historic MSRP.
19. Ipsotek VISuite AI. https://www.ipsotek.com/products/visuite/ — verified via search extract.
20. Regulation (EU) 2024/1689 (AI Act). https://eur-lex.europa.eu/eli/reg/2024/1689/oj ; ICO, "CCTV and video surveillance". https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/ — verified (page exists).

In-repo sources: docs/03, docs/11, docs/14; `survsim/eval/{alarms,pipeline,rules,behaviour}.py`; `configs/scenarios/{disguise_and_tamper,street_crowd}.yaml`; research R03, H02, D06, D07.
