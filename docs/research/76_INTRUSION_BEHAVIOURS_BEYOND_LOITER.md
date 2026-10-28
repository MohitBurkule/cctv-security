# 76 · Intrusion behaviours beyond loiter

Every rule SurvSim scores today is a loiter rule or the abandoned-object rule
(`survsim/eval/rules.py`: `DwellRule`, `ZoneDwellRule`, `PathLoiterRule`,
`DisplacementLoiterRule`, `RevisitRule`, `LearnedLoiterRule`, `GBMLoiterRule`,
`AllOfRule`, `AbandonedObjectRule`). A defence-site intruder-detection system
is bought for something else first: **somebody crossed the fence line**. This
file lists the alarm classes such a system actually ships, how the UK test
standard times them, what rules and learned models do, which innocent events
they confuse with, and — read from the code rather than from
`docs/03_BEHAVIOUR_CATALOG.md` — where SurvSim's catalogue and rules stop.

Tags: **[V]** fetched and checked in this session; **[A]** asserted, secondary
or not fetched; **[FACTS]** already in `FACTS_VERIFIED.md`; **[CODE]** read
from the repo at the working-tree state of 2026-09-27; **[INF]** my inference.

---

## 1. The alarm classes a perimeter system ships

The list below is the union of the i-LIDS event scenarios (§2) and the
scenario menus of commercial edge analytics (§3). Each is given as the
*operational* definition an integrator configures, not a research label.

| # | Class | Operational definition (what fires) | Typical knobs |
|---|---|---|---|
| 1 | **Line-cross / tripwire** | A classified object's reference point crosses a drawn line in a set direction. Axis: "the object's point of detection must cross the line … Objects that only touch the line don't trigger"; for humans the point is the feet, for vehicles the centre [V: Axis Object Analytics manual, https://help.axis.com/en-us/axis-object-analytics] | direction, class filter (human/vehicle), min size via perspective |
| 2 | **Sterile-zone entry** | Any person present in a detection zone between two fences. i-LIDS calls the alarm "Fence Attack": "A person is present in the detection zone" [V: i-LIDS user guide App. I, https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf] | zone polygon, time-of-day schedule |
| 3 | **Fence climb / climb-over** | Person on or above the fence plane, or leaves the ground at the barrier. Usually *not* a separate video rule: it is line-cross on a line drawn along the fence top, or a fence-mounted sensor (vibration / taut-wire) fused with video [INF] | line height, dwell at barrier |
| 4 | **Tailgating at gates** | Two or more objects cross an access line inside a short window after one valid credential. Axis ships it as a scenario: "multiple objects crossing line within 0-20 seconds" [V: Axis Object Analytics manual] | window (0–20 s), link to access control |
| 5 | **Vehicle stop on approach road / no-parking zone** | i-LIDS parked vehicle: a vehicle stops in a no-parking zone, "remains stationary and has not moved since stopping & Over sixty seconds have passed since the vehicle stopped"; a second alarm "Person exits vehicle" [V: i-LIDS guide, parked vehicle definition] | stationary time, zone |
| 6 | **Abandoned object** | i-LIDS: a person places an object, leaves the detection area without it, and "Over sixty seconds after they left the detection area, that person has still not returned" [V: i-LIDS guide, abandoned baggage definition] | owner distance, dwell |
| 7 | **Running** | Track speed above a threshold for a minimum duration, usually inside a zone [INF — generic VMS feature; not fetched per vendor] | speed, duration |
| 8 | **Crowd forming** | Occupancy in an area above N (Axis "Occupancy in area" estimates count "at any time" [V: Axis manual]) held for T | N, T |
| 9 | **After-hours presence** | Class 1 or 2 armed by a schedule. Axis Fence Guard is marketed for "low-traffic, fenced-in areas during after hours" [V: https://www.axis.com/products/axis-fence-guard] | schedule, authorised-role exemption |
| 10 | **Camera tamper** | Scene change / defocus / cover / redirect detected from the image itself. Bosch/IQSight list tamper among IVA tasks [A — the fetched page (https://www.iqsight.com/en/products-and-technologies/video-analytics/) only summarised "IVA Pro and IVA Lite … perimeter, traffic, license-plate"; the task list was not visible] | sensitivity, reference image |

Two structural observations matter for SurvSim:

- **Classes 1, 2, 4 and 9 are instantaneous or near-instantaneous.** They fire
  on an *event*, not on a dwell. None of them is expressible as `DwellRule`,
  whose `speed_cap_mps = 0.5` [CODE] means a running intruder never starts the
  clock at all. That is the correct behaviour for a loiter rule and the wrong
  behaviour for a sterile zone.
- **Classes 5 and 6 are dwell-after-event.** The clock starts on a state
  change (stopped, owner left) and runs 60 s. That is the i-LIDS shape, and
  `AbandonedObjectRule` already implements the object half of it [CODE].

---

## 2. Standards and how they time an alarm

### 2.1 i-LIDS (Home Office CAST; formerly with CPNI)

All of the following is from the user guide PDF, fetched from gov.uk and
extracted locally in this session [V: https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf].
The gov.uk landing page lists the scenarios: sterile zone, parked vehicle,
abandoned baggage, doorway surveillance, new technologies (thermal/IR), plus
multiple-camera tracking [V: https://www.gov.uk/guidance/imagery-library-for-intelligent-detection-systems]
— five event-detection scenarios and one tracking scenario, consistent with
FACTS (five released scenarios).

**Timing rule (verbatim):** "Systems have ten seconds to report an alarm state
after an alarm event begins in the evaluation footage. During this time
multiple alarm reports will be disregarded … After this ten second window, any
further alarms reported will be deemed 'false positives'. NB. Systems should
NOT continue to alarm over the duration of alarm events." And: "Where a system
false alarms several times in quick succession, only one false positive alarm
will be logged every five seconds." [V] (FACTS row 20 already carries the 10 s
window.)

Note what "alarm event begins" means per scenario [V]:

- **Sterile zone** — the event begins when a person is present in the
  detection zone. So the 10 s is measured from *entry*, not from a dwell.
- **Parked vehicle** — the event begins when the 60 s stationary condition is
  met ("Alarm StartTime – Time elapsed in clip when alarm condition met"). So
  the system must fire between 60 s and 70 s after the vehicle stops. The
  brief's "~10 s after 60 s stationary" is correct.
- **Abandoned baggage** — likewise 60 s after the owner leaves the area, then
  the 10 s window.

**Scoring.** Recall r = a/(a+c), precision p = a/(a+b), and a weighted F1
with a scenario-specific "recall bias" α [V]. The α values printed in the
scenario appendices are [V, read from the extracted PDF; the glyph layout is
damaged so pairing is my reading]:

| Scenario | α Operational Alert | α Event Recording |
|---|---|---|
| Sterile zone | 0.65 | 75 |
| Parked vehicle | 0.55 | 60 |
| Doorway surveillance | 0.5 | 24 |

Operational Alert (α < 1) weights precision — the operator is watching live
and false alarms cost attention. Event Recording (α ≫ 1) weights recall — the
system is deciding what to record. The pass marks for the government catalogue
"are not made public"; commissioning acceptance is "an overall F1 score of
0.7 at the application phase" with the i-LIDS level "considerably more
stringent" [V].

**The sterile-zone metadata is a hard-negative list.** Every clip is indexed
with `Distraction – Potential causes of false alarms <Bag|Bats|Birds|Camera
switch from colour to monochrome|… |Flickering light|Foxes|Insect on
camera|Insects|Rabbits|Shadow through fence|Squirrel>`, and the attacker
`SubjectApproachType <Body drag|Crawl|Creep walk|Crouch run|Crouch walk|Log
roll|Run|Walk|Walk with ladder>` [V]. Both lists feed §4 and §5 directly: the
positives are *mostly not upright walking*, and the negatives are *mostly not
people*.

### 2.2 PIDS, CPNI/NPSA and the detection / nuisance split

The NPSA PIDS page returned 403 to WebFetch
(https://www.npsa.gov.uk/perimeter-intrusion-detection-systems-pids), so the
definitions here are [A], stated as they are commonly used in PIDS
engineering:

- **Probability of detection (Pd)** — fraction of defined attacks (attack
  methods × locations × conditions) that raise an alarm [A].
- **Nuisance alarm** — an alarm caused by a real stimulus that is not an
  intruder (animal, vegetation, weather); **false alarm** — an alarm with no
  identifiable stimulus (equipment/processing) [A]. Sandia-lineage physical
  protection texts report them separately as NAR and FAR [A — not fetched;
  OSTI returned a socket error].
- **Operational Requirement (OR)** — CPNI/NPSA's method for writing down what
  the system must detect, where, and against which attacker, before
  specifying product [A].

The engineering point survives the tag: PIDS practice separates the *cause*
of an unwanted alarm, because the fix differs (trim the hedge vs. retune the
analytic). SurvSim's `survsim eval` reports FA/cam-h without a cause label;
the cause is recoverable from GT (which innocent actor triggered it) but is not
reported [CODE: alarms carry `uid`; INF on reporting].

### 2.3 IEC / BS EN 62676-4 DORI

Detect 25, observe 62.5 (Axis rounds to 63), recognise 125, identify 250 px/m
[V: https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014;
FACTS row 27]. The DORI levels are defined for a *human operator* viewing video ("determine whether or not any individual is present" at 25 px/m [V]); they are not analytics thresholds [INF].
For analytics the relevant number is object height in pixels: SurvSim's
single "visible" definition is ≥ 20 px tall (`geometry.usably_visible`), and
i-LIDS indexes subject distance as 10–30 % of screen height for sterile zone
and 4–20 % for parked vehicle [V]. The 2025 revision's seven-level scale is in
FACTS as secondary.

---

## 3. Rule versus learned

### 3.1 Commercial rules

- **Axis Object Analytics** — nine scenarios: object in area, line crossing,
  time in area, crossline counting, occupancy in area, tailgating, PPE, motion
  in area, motion line crossing (the last two unclassified) [V]. Its manual
  lists failure causes: "Partially hidden people or vehicles", "Insects on the
  camera lens", "A combination of car headlights and heavy rain",
  "Human-size animals", "Strong light causing shadows" [V].
- **Axis Fence Guard** — line-crossing; "ignores ordinary background motion",
  can "filter out motion from headlights and small objects", and a
  perspective tool so it can "alert staff to a suspicious truck farther away
  while ignoring an animal nearby" [V: https://www.axis.com/products/axis-fence-guard].
  That is a *size-in-metres* filter, not a classifier.
- **Axis Perimeter Defender** — product page states only that it "can use
  different detection scenarios" [V: https://www.axis.com/products/axis-perimeter-defender];
  scenario names unverified.
- **Bosch IVA (now IQSight)**, **Hikvision**, **Milestone** — pages
  redirected, did not resolve, or did not show the task list in this session
  [A]. Do not quote their rule names in an interview without re-checking.

The shape is consistent: a detector/classifier makes objects, a tracker makes
tracks, and **the alarm is a geometric predicate on the track** — crossing,
dwell, count. The learned part is upstream; the alarm is a rule.

### 3.2 Trajectory classifiers

The step beyond a tripwire is to classify the track: approach angle to the
fence, speed profile, stop-at-barrier, reversal. SurvSim already does this for
loiter (`LearnedLoiterRule`, `GBMLoiterRule` on `loiter_features.py` [CODE]),
and H58 showed the lesson that transfers: kinematics cannot separate two
behaviours that share a generating process (the smoke-break/loiter floor,
docs/research/58 §1). For perimeter the analogous pair is
`perimeter_probe` vs a guard walking the fence line — same path, same speed.

### 3.3 Skeleton action recognition (ST-GCN)

ST-GCN (Yan et al., AAAI 2018) on NTU RGB+D: **81.5 % X-Sub, 88.3 % X-View**;
on Kinetics-skeleton **30.7 % top-1, 52.8 % top-5**; fused with RGB and flow on
Kinetics it reaches 71.7 % [V: https://arxiv.org/pdf/1801.07455, table values
read from the PDF text]. For climbing the relevance is that "climb" is a pose
sequence (hands above head, feet leave ground) that a centroid track cannot
see. The caveats: NTU is indoor Kinect at 2–4 m; a fence 40 m away at 720p is
tens of pixels tall, below where 2D keypoints are stable [INF]. i-LIDS
attackers crawl, log-roll and body-drag [V] — poses NTU does not contain.

Fence-climbing specific datasets: none fetched in this session [A]. Treat any
"fence-climb dataset" claim as unverified until the paper is in hand.

### 3.4 VLM / weakly supervised anomaly detection

| Method | Supervision | UCF-Crime | XD-Violence | Source |
|---|---|---|---|---|
| VadCLIP | weak (video labels), CLIP | 88.02 % AUC | 84.51 % AP | [V] https://arxiv.org/abs/2308.11681 |
| LAVAD | training-free, VLM captions + LLM | 80.28 % AUC | 62.01 % AP, 85.36 % AUC | [V] https://arxiv.org/html/2404.01014 |
| Holmes-VAD | instruction-tuned MLLM (VAD-Instruct50k) | 89.51 % AUC | 90.67 % AP | [V] https://arxiv.org/html/2406.12235 |

**Why these numbers do not answer the perimeter question** (principle 4):

1. **Frame-level AUC integrates over every threshold.** An operator runs one
   threshold. A detector with AUC 0.88 can sit at any false-alarm rate at the
   operating point — AUC does not say which.
2. **UCF-Crime is 50 % anomalous videos** — 950 anomalous and 950 normal of 1,900 [V: https://arxiv.org/pdf/1801.04264, §3]. A defence fence is quiet for
   thousands of hours per event; the prior differs by orders of magnitude, so
   precision at deployment is set by the negatives, which the benchmark barely
   samples. H12 found every loiter rule 4,500–87,000× over our assumed 0.001 FA/cam-h
   budget [FACTS]; nothing in a frame AUC predicts that.
3. **No timing.** i-LIDS scores an alarm 11 s late as a false positive [V].
   Frame AUC credits a detector that lights up anywhere in the event.
4. **No identity.** SurvSim's `alarms.score()` is `actor_aware` when alarms
   carry a `uid` [CLAUDE.md]; frame AUC credits an alarm on the guard for the
   intruder next to him.
5. **Compute.** An MLLM per frame per camera is not an edge component; it is
   at most a second-stage verifier on alarms the rule already raised [INF].

What a VLM *is* good for here: verifying and explaining a line-cross alarm
("person with ladder" vs "fox"), which is exactly the hard-negative problem.
Score it as a filter: FA/cam-h before and after, recall lost [INF].

---

## 4. Hard negatives, by class

| Class | Hard negatives | Source |
|---|---|---|
| Line-cross / sterile zone | foxes, rabbits, squirrels, birds, bats, insects on lens, shadow through fence, flickering light, colour↔mono switch, bag blown in | [V] i-LIDS sterile-zone distraction list |
| | human-size animals (deer, dogs), headlights + heavy rain, strong shadows, partial occlusion | [V] Axis Object Analytics manual |
| | patrol guard, maintenance crew, grounds staff (authorised crossing) | [INF] — the rule is right, the alarm is wrong; needs role/schedule |
| | vegetation sway, spider webs at IR illuminators, snow, fog | [A] common integrator lore; i-LIDS indexes rain/snow/fog per clip [V] |
| Fence climb | worker on ladder at fence, person leaning on fence, wildlife on fence | [INF]; i-LIDS positive "Walk with ladder" [V] shows the ladder is on both sides |
| Tailgating | family/colleague groups badged separately, door held for a wheelchair user, delivery trolley | [INF] |
| Vehicle stop | moving/parked vehicles, cyclist, pedestrian, ambulance (listed as a *subject*), drop-offs under 60 s | [V] parked-vehicle distraction list includes "Moving vehicle|Parked vehicle|Cyclist|Rabbits|Bird|… Out of focus"; subjects include Ambulance |
| Abandoned object | bag set down while owner queues, luggage beside a seated owner | [INF]; SurvSim `AbandonedObjectRule` requires owner distance [CODE] |
| Running | jogging commuter, late for train, child play | [CODE] `ChildPlay`; [INF] |
| Crowd forming | queue, meet-and-greet, bus stop | [CODE] `Queue`, `MeetAndGreet`, `CommuteWait` |
| After-hours | night-shift staff, security patrol, cleaner | [CODE] `NightPresence` docstring calls itself "context-only"; [INF] |
| Camera tamper | contractor on ladder under camera; rain on lens; IR switch; spider on dome | [CODE] `Maintenance` docstring: "the single biggest source of false alarms in real deployments"; [V] i-LIDS "Insect on camera", "Camera switch from colour to monochrome" |

The dominant pattern: **for a perimeter, most hard negatives are not
people.** SurvSim's director only simulates people (and vehicles/drones), so
its innocent population cannot generate the i-LIDS distraction list.

---

## 5. SurvSim coverage gap table

Read from `survsim/director/behaviours.py` (`REGISTRY`, `label` ClassVars),
`survsim/generator/narrative.py` (`BENIGN_TWIN`) and `survsim/eval/rules.py`
[CODE]. "Twin" means a matched innocent arc exists *in the generator*
(`BENIGN_TWIN`) or a catalogue class whose docstring declares itself the
benign twin; "adjacent" means an innocent behaviour exists but nothing pairs it.

| Class | Catalogue behaviour(s) (registry key → label) | Rule in `survsim/eval` | Hard-negative twin? | Gap |
|---|---|---|---|---|
| Line-cross / sterile-zone entry | `zone_intrusion` / `wrong_zone_entry` → `ZoneIntrusion`, `suspicious.access.intrusion`; `fence_cut` → `hostile.tamper.fence.cut`. **H40b:** both cross ≥ 3.5 m inside, visit the asset, pause and leave | `survsim/experiments/line_cross.py` (H40/H40b arms N/A/B/C; not yet in `eval/rules.py`) | **Yes (H40b):** `maintenance_visit` (role worker, enters by the gate) is BENIGN_TWIN for `zone_intrusion`; restricted zones are fenced, so commuters no longer cut through | Rule not in `survsim/eval`; no role/badge exemption. Twin residual on arm C is 0.49 FA/cam-h (H40b) |
| Fence climb | `climb_attempt` → `ClimbAttempt`; **`fence_climb` → `FenceClimb`, `hostile.breach.climb` (H40b; crosses at the end of the climb)** | line_cross arms (recall 0.800 on C, H40b) | **Yes (H40b):** `patrol_guard` | `climb_arc` now in compose; no pose-based cue scored; no ladder-work twin |
| Perimeter probe | `perimeter_probe` → `suspicious.probe.fence` (stands off and walks the fence tangent; on sites without panels it uses a restricted-zone fence point instead of falling back to recon, H40b) | `PathLoiterRule`/`DwellRule` catch it only if slow | **Yes (H40b):** `patrol_guard` walks the same fence ring and enters by the gate | Probe-only rule (no crossing) not scored |
| Tailgating | `tailgate`/`tailgating` → `suspicious.access.tailgate` | None | `transit_through` (BENIGN_TWIN) | No two-crossings-in-window rule; no credential event in GT to condition on |
| Vehicle stop on approach | `vehicle_dropoff_loiter` → `suspicious.vehicle.loiter`; `vehicle_ram` → `hostile.vehicle.ram` | None (DwellRule is per person `uid`; vehicles not scored) | Adjacent: `vehicle_move` → `normal.vehicle.transit` | No parked-vehicle 60 s + 10 s rule; no short-dropoff (< 60 s) negative |
| Abandoned object | `object_abandon` → `suspicious.object.abandon` | **`AbandonedObjectRule`** | `transit_through` (BENIGN_TWIN) | Closest to i-LIDS; negative is not "bag set down beside owner" |
| Running | `flee`, `crowd_rush`, `transit` with `gait.style: run` (narrative.py:160) | None | Adjacent: `child_play` | No speed rule |
| Crowd forming | `crowd_form` → `suspicious.crowd.gather`; `crowd_rush` | None | Adjacent: `queue`, `meet_and_greet`, `group_walk`, `commute_wait` | No occupancy rule |
| After-hours | `night_presence` → `suspicious.temporal.afterhours` (subclasses `Transit`) | None | None (no night-shift/guard arc) | Context-only by design, no schedule-aware rule |
| Camera tamper | `camera_tamper` → `hostile.tamper.camera` (+ camera director's six tamper kinds) | None in `rules.py` (eval/behaviour.py treats tamper windows as windows) | **Yes** — `Maintenance` / `normal.maintenance` explicitly; also `transit_through` in BENIGN_TWIN | Best-twinned class; lacks an image-based tamper detector to score |
| Loiter (reference) | `loiter`, `smoke_break`, `commute_wait` | 8 loiter rule classes | Yes — `wait_then_leave`, `SmokeBreak`, `CommuteWait` | the only class with a measured FA/cam-h (H12/H58) |
| Non-human distractors | **`wildlife` (H40b):** object_class animal, < 1 m, fast/erratic, crosses fences, MOT class 8 / consider 0 | height gating (arm A) removes all of it in H40b | — | Weather, headlight, lens-insect and shadow agents are still absent |

**Biggest gap.** The catalogue *has* the positives (`zone_intrusion`,
`fence_cut`, `climb_attempt`, `tailgate`) but `survsim/eval` has **no
line-crossing / sterile-zone rule at all**, so the core alarm a defence
perimeter is bought for had never produced a single FA/cam-h number (true when written; H40 below is the first, on mock tracks). The
second gap compounds it: the negatives that dominate a sterile zone (animals,
shadows, lens insects, authorised patrols) are not in the population, so even
a line-cross rule scored today would report an optimistic false-alarm rate —
every innocent in a mock world is a person on a path, and none of them has
a reason to cross the fence [INF]. (True when written. H40b added fences,
crossing intruders, a climb arc, `patrol_guard` / `maintenance_visit` twins and
`wildlife`; the table above is updated. Shadows, insects, weather and headlights
are still absent, and `LineCrossRule` is still not in `survsim/eval`.)

What would close it, in order of cost [INF]:

1. `LineCrossRule` (track segment × polyline intersection, direction, class,
   `allowed_roles` exemption, i-LIDS 10 s event scoring from first entry).
   Pure Python on `world.parquet`; the mock backend is enough.
2. A `patrol` behaviour (guard walks the fence line on a schedule, crosses at
   gates) as the twin for `perimeter_probe`, `zone_intrusion` and
   `night_presence`; add to `BENIGN_TWIN`.
3. A climb arc in `compose.py` and a `ladder_work` twin for `climb_attempt`.
4. Non-human distractors — at minimum an animal agent class on the mock
   backend (small, fast, erratic, ground-level), sized so a pixel-height
   filter is actually exercised. Weather/lighting belong in
   `sensors/degrade.py`, not the director.

---

## H40 — measured line-crossing FA/cam-h

[V, repo — recomputed in AUDIT_76_H40] Measured (32 §H40, pre-registered `02b51ae`, mock tracks with a declared tracker-noise model
— 0.3 m jitter, a fragment per 90 s, 10 ghosts/cam-h — whose parameters are **assumptions, not fitted to any tracker**;
3,002 clean cam-h, 200 intruder worlds, actor-aware, 10 s window, world-bootstrap 95 %):

| arm | clean FA/cam-h | recall@10 |
|---|---|---|
| N naive entry | 70.96 [63.80, 78.30] | 0.945 [0.910, 0.975] |
| A + age/height gating | 66.48 | 0.925 |
| B + inward, 1.5 m depth, 5 s dwell | 5.11 | 0.120 |
| C + gate/queue context | 4.20 [3.84, 4.57] | 0.100 [0.060, 0.145] |

H40 was **not met**: FA fell 16.9x [15.3, 18.6], but recall collapsed. Two catalogue findings drive
this. `ZoneIntrusion` stops the actor at the zone edge, and only 6/100 are 1.5 m deep within 10 s. The
restricted polygons are unfenced, so innocent transit cuts through them. The depth/dwell filter that
removes cut-throughs removes the modelled intruder too. Every arm is > 4,000x the assumed 0.001 budget.
Under the assumed noise model, fragments and jitter (not ghosts) are the dominant noise term; that ranking is a property of the chosen parameters, not a measurement of a real tracker.

**How to quote it.** These FA/cam-h are **optimistic for a real fence**: the clean worlds contain only commuters (no patrol guard, no animal, no weather/headlight twin), and the ghost rate is invented. A real sterile zone removes the cut-through commuters (the dominant residual here) but adds the i-LIDS distraction list, which SurvSim cannot generate. So H40 measures how the *rule stack* trades FA against recall, not what a site would see. Arm C also omits the pre-registered "door prop" exclusion (the runner uses gate/queue zones only; disclosed in AUDIT_76_H40). The fixes are the gap-table items: a
crossing intruder arc, a patrol twin, and non-human distractors.

---

## H40b — fenced worlds, crossing intruders (32 §H40b)

[V, repo — recomputed in AUDIT_H40B] Same arms and assumed noise model on regenerated worlds (pre-reg `d51e5f9`, engine `9468696`, results `12b6c92`; 676 worlds / 3,002 clean cam-h, 300 recall worlds / 298 events).

| arm | primary clean FA/cam-h | recall@10 | noise-free recall@10 | twin FA/cam-h patrol / maint |
|---|---|---|---|---|
| N naive | 369.4 [318.4, 428.9] | 0.862 | 1.000 | 2.66 / 0.61 |
| A + gating | 353.9 [303.9, 411.7] | 0.829 | 1.000 | 2.47 / 0.40 |
| B + dir/depth/dwell | 0 (≤ 0.001, rule of three) | 0.822 | 0.899 | 0.43 / 0.11 |
| C + gate context | **0** (≤ 0.001) | **0.782 [0.736, 0.829]** | 0.852 | **0.389 / 0.099** |
| C + fusion (H53 C+abc: gate log, RF tag, PIDS; simulated, true-position matching) | 0 | 0.758 [0.710, 0.805] | — | **0.0043 / 0.0003** (99.0 % of twin FA removed; tailgate recall 0.007) |
| C + fusion, estimated-position association (H54 est C+abc; generated fence_tailgate) | 0 | 0.772 [0.724, 0.818] | — | 99.1 % of twin FA removed (upper bound: benign noise, no ID switches); generated tailgater 0.056 |
| + gate people counter (H54 C+abcg) | 0 | 0.782 [0.736, 0.826] | — | 96.3 % removed; tailgater **0.685** [0.589, 0.778] (with GT identities; H59: 0.10 actor-aware under H24-calibrated ID-switch noise — a scoring artefact, not a fusion break; H62 measured position/time scoring at 0.715 recall (r=2 m) but a 31.3 % bystander false-credit rate, so it does not replace actor-aware as the default) |

Not met (bar 0.9). The gap-table fixes moved the problem. Cut-throughs are gone: noise-free N fell 16.98 → 1.84, and that residue is all wildlife (5.96 FA/cam-h on noisy N, 0 from arm A on). The recall loss is mostly the rule, not the tracker: depth/dwell costs 10.1 points on noise-free tracks (probe arcs worst), gate context 4.7, the assumed fragments/jitter 7.0. The FA floor is now **authorised crossers**: patrol 0.389 and maintenance 0.099 FA/cam-h on C (≈ 490× budget; 398 of C's 424 recall-world FPs). Arm C as registered does not exempt the fence gate; exempting it would cut the gate-entry share but blind the rule to forced or tailgated gate entry. Telling a guard from an intruder inside the fence needs a role/badge/schedule input or PIDS fusion (74; H49).

**What a real site adds (how to quote H40b).** Zero clean FA is a statement about *this* negative set: commuters, two kinds of authorised crosser and one animal class, on mock tracks with an assumed noise model. A real sterile zone adds the rest of the i-LIDS distraction list — shadows through the fence, insects and spider webs at the IR illuminator, rain, snow, fog, headlights, flicker, IR/colour switching, blown debris, human-size animals — plus ad-hoc staff who are on no schedule, and a real tracker whose fragments are not 1 per 90 s. None of those are generated, so 0 FA/cam-h is an upper bound on how well the rule stack can do, not a site prediction; the twin rate (0.49 FA/cam-h at 2 patrols/h + 1 visit/h, invented rates) scales with the site's real patrol and maintenance traffic.

---

## 6. Interview Q&As

**Q1. What is the i-LIDS timing rule, and why does it matter for a sterile zone?**
*Answer:* Ten seconds from the start of the alarm event to report; repeats in
the window are ignored; anything after is a false positive; repeated FAs are
logged once per 5 s [V]. For a sterile zone the event starts at entry, so a
dwell-based rule that waits 25–60 s is structurally a false-alarm generator
*and* a miss.
*Red flag:* "We alarm within a minute, that's fine" — or treating a late alarm
as a slow hit.

**Q2. How is the i-LIDS parked-vehicle alarm defined?**
*Answer:* Vehicle stops in a no-parking zone, stays stationary, and 60 s pass;
that moment is the event start, then 10 s to report. A second alarm fires when
a person exits the vehicle [V].
*Red flag:* "Alarm when a vehicle stops" — no dwell, so every drop-off alarms.

**Q3. How does i-LIDS score a system, and what is α?**
*Answer:* Weighted F1 on recall and precision; α is a scenario-specific recall
bias — below 1 for Operational Alert (0.65 sterile zone, 0.55 parked vehicle),
large for Event Recording [V]. Thresholds for the catalogue are unpublished;
0.7 F1 is only the commissioning entry bar [V].
*Red flag:* quoting frame AUC or mAP as an i-LIDS result.

**Q4. Why is UCF-Crime AUC 88–90 % not evidence a model works on a fence?**
*Answer:* AUC is threshold-free and prevalence-blind, has no timing tolerance
and no identity; the fence's prior is orders of magnitude lower. Report
FA/cam-h at the operating point against an operator budget (ours, 0.001, is assumed: 28 §6; PIDS practice ≈ 1 nuisance alarm/zone/day [A], `81`), with i-LIDS
timing [V numbers; principle 4].
*Red flag:* "Holmes-VAD gets 89.5, so we'll deploy an MLLM on every camera."

**Q5. Where does a VLM belong in a perimeter pipeline?**
*Answer:* As a second-stage verifier on rule alarms — "person with ladder" vs
"fox" — scored as FA/cam-h removed vs recall lost. LAVAD is training-free at
80.28 % UCF-Crime AUC [V], which is a prior for zero-shot filtering, not a
detector budget.
*Red flag:* running it on every frame, or trusting its explanation as ground
truth.

**Q6. Line-crossing looks trivial. What makes it hard in practice?**
*Answer:* The reference point (feet for humans per Axis [V]) is occluded at
fences; perspective means a fox near the camera is taller than a man at 60 m,
hence metric size filters [V Fence Guard]; tracker ID switches across the line
produce double or missing crossings; headlights, rain, shadows, insects on the
lens [V].
*Red flag:* "Just check if the box centre crosses the line."

**Q7. How would you detect a climb rather than a crossing?**
*Answer:* A line along the fence top plus time-at-barrier, optionally fused
with a fence vibration sensor; skeletons (ST-GCN 81.5 % X-Sub on NTU [V]) only
where the person is tall enough in pixels, which at a perimeter usually means
a PTZ slewed onto the alarm (and the PTZ is a queue: H56, mock, one PTZ per 40
cameras misses ~37 % of alarms at 120/h — `83`, AUDIT_83_H56). And remember i-LIDS
attackers crawl and log-roll [V].
*Red flag:* "Train ST-GCN on NTU and point it at the fence."

**Q8. What are the hard negatives for a sterile zone, and does your simulator have them?**
*Answer:* Mostly non-human: foxes, rabbits, birds, bats, insects, shadows
through the fence, flicker, IR/colour switch [V i-LIDS list]; plus authorised
patrols. Since H40b SurvSim has one animal class (`wildlife`, < 1 m, removed by
height gating) and `patrol_guard` / `maintenance_visit` twins, which leave
0.49 FA/cam-h on the full rule [CODE, H40b]; it still has no shadows, insects,
weather or headlights — so any FA/cam-h it reports for line-crossing is
optimistic for a real fence, and I would say so.
*Red flag:* "Our FA rate on synthetic data is near zero" without saying what
the negatives were.

**Q9. Nuisance alarm vs false alarm — why distinguish?**
*Answer:* Nuisance = real stimulus that is not a threat (animal, weather);
false = no stimulus (processing/equipment) [A, PIDS usage]. The remedies
differ (site management vs analytic tuning), and a customer's OR will often
budget them separately.
*Red flag:* treating every unwanted alarm as the model's fault, or as the
site's.

**Q10. Your simulator has `zone_intrusion` and `fence_cut`. Can you claim perimeter coverage?**
*Answer:* No. Behaviours exist; no rule in `survsim/eval` scores a crossing,
tailgate, parked vehicle, running or crowd; the twins for those are a straight
transit, not a patrol; and non-human distractors do not exist [CODE]. The
honest claim is "loiter and abandoned object are measured; perimeter classes
are generated but unscored". Since H40 one line-cross rule is scored on
mock tracks: best arm 4.20 FA/cam-h at recall@10 0.100 (H40), then 0 clean
FA at recall@10 0.782 with twins at ≈ 490× our assumed budget on fenced worlds (H40b) —
both not met, still not "perimeter coverage".
*Red flag:* counting catalogue names as capability — the same error as
reading a command list (CLAUDE.md "Known correction").

---

## Sources

[V] fetched this session:
- i-LIDS user guide PDF — https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf
- gov.uk i-LIDS guidance — https://www.gov.uk/guidance/imagery-library-for-intelligent-detection-systems
- Axis Object Analytics manual — https://help.axis.com/en-us/axis-object-analytics
- Axis Fence Guard — https://www.axis.com/products/axis-fence-guard
- Axis Perimeter Defender (page only) — https://www.axis.com/products/axis-perimeter-defender
- Axis DORI whitepaper — https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014
- ST-GCN — https://arxiv.org/pdf/1801.07455
- UCF-Crime (Sultani et al.) — https://arxiv.org/pdf/1801.04264 (950 + 950 videos; added in AUDIT_76_H40)
- VadCLIP — https://arxiv.org/abs/2308.11681
- LAVAD — https://arxiv.org/html/2404.01014
- Holmes-VAD — https://arxiv.org/html/2406.12235

[A] not reachable or not checked: NPSA PIDS (403) https://www.npsa.gov.uk/perimeter-intrusion-detection-systems-pids;
IQSIGHT/Bosch IVA task list https://www.iqsight.com/en/products-and-technologies/video-analytics/;
Hikvision and Milestone docs (DNS failure); Sandia/OSTI NAR vs Pd (socket error).
