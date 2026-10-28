# 62 · Site context and zone semantics: giving an alarm system what the track does not contain

*Written 2026-09-27. Design document, not a result. Every external claim is
tied to a source fetched on that date (§9). Repo facts are tagged [repo] with
the path. Tags: **[F]** fetched primary source, **[repo]** read from this
repository, **[derived]** my reasoning, **[proposal]** not built.*

## 0. The problem in one paragraph

Report 58 showed that a loiter rule fed only the track has a floor. In the H12
worlds 3,027 smoke breaks pace in gate zones, which alone puts any track-only
rule at **1.008 FA/cam-h × recall** (58 §6.2) [repo]. The round-3 run
(`out/experiments/h58_round2/round3_results.md`) then added one context
feature, the *function* of the zone under the person, to an otherwise
identical gradient-boosted model. At the selected operating points the
track-only GBM (arm B) scored **3.114 [3.051, 3.178] FA/cam-h at recall 0.842**.
The context GBM (arm D) scored **2.468 [2.412, 2.525] at recall 0.822**
[repo]. That is 20.7 % fewer false alarms at a slightly lower recall. The
pre-registered prediction P8 was ≥ 25 %, so P8 **fails** on its own threshold,
but the effect is real: the Garwood intervals do not overlap. The context
came free from the Director. A deployed system has to get it from somewhere,
and that "somewhere" is the **site profile**. This document designs one:
what it contains, how vendors capture it today, how it can be inferred or
imported, how SurvSim should generate and label it, how to measure what each
part is worth without fooling ourselves, and what it costs in privacy.

## 1. What a site profile contains

A site profile is the per-site configuration that turns "person at (x, y)
for 70 s" into "person on the platform at 07:52, four minutes before the
07:56, which is normal". I propose seven layers, ordered from cheapest to
capture to most sensitive [proposal]:

| # | Layer | Content | Changes | Sensitivity |
|---|---|---|---|---|
| L1 | Geometry | site plan in metres, camera poses, ground homographies (29 §2) | on install/re-aim | low |
| L2 | Zones | polygons in site coordinates, each with a **function** (platform, gateline, fence_line, smoking_area…) and a **policy tag** (public/restricted/perimeter) | months | low |
| L3 | Portals | entrances/exits with direction (in/out/both), kind (main/service/emergency) | months | low |
| L4 | Timetables | opening hours per zone; scheduled events (train departures, shift change, deliveries) | days–weeks | medium |
| L5 | Expected occupancy | per zone × hour-of-week: mean count, dwell distribution | learned, weekly | low if aggregate |
| L6 | Patrols | guard routes and schedule windows | weekly | **high** (security-sensitive) |
| L7 | Authorised roles | which role may be in which zone at which time | per shift | **high** (personal data) |

Two design choices matter more than the table.

**Function is separate from policy.** SurvSim's `Zone.tag` already carries
the *policy* (`public`, `restricted`, `perimeter_fence`, `gate`, `queue`,
`parking`, `sensitive_asset`, `blindspot`) and `Zone.allowed_roles` carries
L7 in embryo (`survsim/core/models.py`) [repo]. The zone *id* carries the
function (`zone.platform`, `zone.gateline`, `zone.reception`…) set by
`site.build_site` (`survsim/generator/site.py`) [repo]. Round 3 got its gain
from the id, which is finer than the tag. For example `zone.platform` and
`zone.reception` share the tag `queue`, and `zone.gateline` shares `gate`
with every `zone.entrance_k`. The 1.008 twin floor is defined by tag. So the
profile must store function as a first-class field, not recover it from a
string suffix the way round 3 did.

**Everything is in site coordinates, not pixels.** Vendors store zones per
camera in normalised image coordinates (below). A per-camera zone breaks when
a PTZ slews or a camera is knocked (CLAUDE.md principle 2). It also cannot be
shared between two cameras that see the same platform. The profile stores
polygons in metres. Each camera derives its pixel mask through its current
homography, so a re-aimed camera re-derives it and keeps the zone
[derived; 29 §2, §5.4].

## 2. How vendors capture context today

The common pattern is a **per-camera rule editor**: a polygon, a class
filter, a dwell threshold and, on some platforms, a schedule. Function is
implicit in the rule's name, and occupancy is never an input.

**ONVIF (the interoperability floor).** The ONVIF Analytics Service
Specification v26.06 defines standard rules. A `LineDetector` is "a
non-intersecting simple polyline". A `FieldDetector` is "a simple
non-intersecting polygon". A `LoiteringDetector` is "a simple
non-intersecting polygon as an area of interest and threshold loitering
interval" with parameters `Field [tt:Polygon]` (marked *optional*) and
`TimeThreshold [xs:duration]`. It publishes `tns1:RuleEngine/LoiteringDetector/ObjectIsLoitering`
with a `Since` timestamp [F: ONVIF Analytics spec §A.4]. The spec says any
region-based rule "should contain a parameter 'Field' ElementItem", a
polygon "in normalized coordinates" [F: §A.1.2.1 and §A.3]. The metadata schema does
carry `GeoLocation` and `GeoOrientation` for objects [F]. There is **no
field for zone function, schedule or occupancy** in the rule description. So
a standards-only integration can carry the polygon and the threshold, and
nothing that would separate a platform from a fence [derived from F].

**Axis Object Analytics.** Scenarios include "Object in area", "Time in
area" (a time limit "for how long an object is allowed to stay inside the
include area before the application triggers an alarm") and "Occupancy in
area" [F: Axis OA manual]. You can define "up to 5 exclude areas". Timing is
handled outside the analytic, by the device's action rules: an operator can
"select a schedule from the list" [F]. Perspective is set by placing vertical
bars in the image [F]. **Axis Perimeter Defender** adds *conditional zones*,
which trigger "when a person or a vehicle enters a zone defined on the
ground without first passing through another zone". That is a primitive for authorised paths. Its
calibration is automatic (a person walks a zigzag) or manual (person sticks,
lines) [F: Axis Perimeter Defender manual]. The fetched manual describes no
schedule inside the analytic [F].

**Milestone XProtect.** Analytics reach the VMS as events. In the MAD format
the source carries a `Location Name='Exit Door'` sub-element and a `Rule`
element with a type and a polygon for overlay. The event's `Message` "is used
to match against the alarm definition created in the management client"
[F: MIP SDK analytics events]. So zone meaning lives in free-text names and
alarm definitions, not in a typed field [derived from F]. (I could not fetch
Milestone's time-profile page: 404 on 2026-09-27. Time-profile behaviour is
therefore **[not verified here]**.)

**Genetec and Avigilon.** Report 34 lists Genetec Security Center as a
unified platform with analytics "mostly via partners" (KiwiVision) [repo: 34].
Avigilon sells learned-normality products, Unusual Motion Detection and
Unusual Activity Detection. Both documentation pages
(`docs.avigilon.com/.../umd/...`, `.../uad/...`) returned only navigation
chrome on fetch, and the Genetec RSA brochure returned only a brand string.
Their learning periods and map-zone mechanics are **[not verified here]**

**What this means for the design** [derived]. The industry already has
three of the seven layers: L2 as per-camera polygons with no typed function,
L4 as a VMS schedule that gates whether a rule is armed, and a crude L7 as
conditional zones or access-control integration. What nobody exposes
through a standard is a typed zone function, a learned per-zone occupancy
prior (L5), or context as a *feature* rather than an on/off switch. A
schedule that disarms the loiter rule outside 22:00–06:00 is context used as
a hard gate. Arm D uses it as a soft feature, so the model can learn that
70 s on a platform is normal while 70 s at the fence is not. The rest of this
document is about the second use.

## 3. Inferring zone function from traffic

Hand-drawing a function for every zone on 400 cameras (the 53 §7 estate) is
the cost that stops site profiles being built. The research line that avoids
it is older than deep learning.

* **Stauffer & Grimson (2000)**, *Learning patterns of activity using
  real-time tracking*, TPAMI 22(8). Their system "passively observes moving
  objects in a site and learns patterns of activity from those
  observations" by accumulating co-occurrence statistics over tracks
  [F: abstract, doi 10.1109/34.868677].
* **Makris & Ellis (2005)**, *Learning semantic scene models from observing
  activity in visual surveillance*, IEEE TSMC-B. "A scene model is proposed
  that labels regions according to an identifiable activity in each region,
  such as **entry/exit zones, junctions, paths, and stop zones**," learned
  unsupervised [F: abstract, doi 10.1109/TSMCB.2005.846652]. This is L2/L3
  inferred from tracks, and "stop zone" is exactly the platform-vs-corridor
  distinction.
* **Morris & Trivedi (2008)**, survey in IEEE TCSVT. The "scene topology is
  automatically learned and is distinguished by points of interest and
  motion characterized by activity paths". It supports "virtual fencing,
  speed profiling, behavior classification, anomaly detection"
  [F: abstract, doi 10.1109/TCSVT.2008.927109].
* **Wang, Ma & Grimson (2009)**, TPAMI. Hierarchical Bayesian models (LDA,
  HDP, Dual-HDP) cluster moving pixels into "atomic activities" in "crowded
  traffic scenes and train station scenes", "without tracking and human
  labeling effort" [F: abstract, doi 10.1109/TPAMI.2008.87]. This matters
  where tracks break, which is at the density where waiting areas are
  busiest.

**Proposed inference pipeline** [proposal], using statistics SurvSim already
computes or trivially could:

1. **Portals from track births and deaths.** Take the ground-plane positions
   of track starts and ends, excluding those at the frame edge that are
   explained by a neighbouring camera's handover, and cluster them (DBSCAN in
   metres). Dense clusters are entrances or exits. The birth:death ratio
   gives direction: an exit-only door shows deaths and no births. This is
   Makris & Ellis's entry/exit zone [F] with a multi-camera correction.
2. **Stop zones from dwell heatmaps.** Grid the ground at 0.5 m. Per cell
   and per hour-of-week, accumulate occupancy-seconds, the fraction of those
   seconds at speed < 0.3 m/s, and the dwell-episode length distribution.
   Cells with a high stationary fraction *and* many distinct people are
   waiting areas. High stationarity with few people is a post: a guard, a
   kiosk, or a loiterer. The **distinct-people count** is what separates
   them, and it is also what makes this personal-data processing (§6).
3. **Paths from flow fields.** Per cell, a histogram of heading. Cells whose
   dominant flow is bimodal and aligned are corridors. Uniform headings mean
   an open plaza.
4. **Time-of-day profiles.** Aggregate by hour-of-week so that "the platform
   fills at :52 and empties at :57" is visible as periodicity. A
   Fourier/autocorrelation peak at the timetable period flags a
   timetable-driven zone before the timetable is imported.
5. **Human confirmation, not human drawing.** The inferred map is shown to
   the installer as proposed zones with a suggested function ("stop zone,
   peak 07:50–08:00, looks like a platform: confirm?"). One click per zone
   instead of a polygon per camera. The confirmed label is what trains the
   model. This is the answer to "how do you get context without labelling"
   (§7 Q1).

**The trap** [derived]. A learned occupancy prior (L5) is *normality*, and
normality learned from live traffic includes the loiterers who were there
during learning. A drug-dealing spot that is busy every evening becomes a
"stop zone". Three defences: (i) learn L5 only from windows the operator has
reviewed as clean, or at least exclude alarmed tracks; (ii) cap how far L5
can lower a score, so it discounts and never vetoes; (iii) keep an explicit
function label (L2), which a human confirmed, above the learned prior.

## 4. Importing maps: OSM, floor plans, BIM, and registering cameras to them

Where a map exists, import it rather than infer it.

* **OpenStreetMap.** `entrance=*` distinguishes `main`, `secondary` ("often
  used only for events or at special times"), `service` ("often only for
  employees or for delivering"), `exit` ("a one-way out"), `emergency` and
  others [F: OSM wiki Key:entrance]. That maps straight onto L3's kind and
  direction. Simple Indoor Tagging gives `indoor=room|area|corridor`, and
  `level=*`, with "0 … normally the ground-level" [F: OSM wiki SIT].
  `opening_hours=*` has a formal grammar ("Mo-Fr 08:00-17:00",
  "Mo-Sa 10:00-20:00; Tu off") [F: OSM wiki Key:opening_hours]. Use that
  grammar for L4 so importing and exporting timetables is lossless
  [proposal].
* **BIM (IFC).** IFC4.3 property definitions include `OccupancyType`,
  `OccupancyNumberPeak` ("maximal number of people required for the
  activity assigned to this space in peak time") and `OccupancyTimePerDay`
  ("the amount of time during the day that the activity is required within
  this space") [F: buildingSMART IFC4.3.x-development repo, docs/properties/o/].
  A building with a maintained IFC model therefore ships an L5 *design*
  prior, and IfcSpace gives L2 polygons. The design prior is what the
  architect intended, not what happens, so it initialises L5 and the
  learned statistics then update it [proposal].
* **Floor-plan images (PDF/PNG).** These are the commonest case and the
  least structured. They need a manual scale and four-point registration.
  Room labels can be OCR'd into suggested functions.

**Camera-to-map registration** is report 29's ground homography turned
around. 29 §2 derives H from K[r1 r2 t], so a foot point maps to metres on
the ground plane [repo: 29]. With a map, the installer clicks ≥ 4
corresponding points (a kerb corner, a door, a bollard) in the image and on
the plan, and H is solved directly (DLT plus RANSAC). No intrinsic
calibration is needed for the ground-plane use [derived; 29 §2]. Two cautions
carried over from 29. First, near the horizon the homography is very
sensitive to small errors (29 §2.3: the top rows of a 20°-tilt camera look
above the horizon), so zone membership near the far edge must carry an
uncertainty. Second, a raised platform is *off* the ground plane (29 §2.2
pitfall 1), so a platform needs its own plane height or feet will map to the
wrong place. Axis's automatic calibration by a person walking a zigzag [F]
is the product form of the same idea.

## 5. How SurvSim should generate and label site profiles

SurvSim already has most of the profile, scattered across modules [repo]:

* `site.build_site` emits `Zone(id, tag, polygon, allowed_roles)` per site
  type, plus entrances, exits and spawn points (`survsim/generator/site.py`).
  Only `zone.stage` and `zone.restricted_k` set `allowed_roles`
  (`["worker", "guard"]`); every other zone leaves it empty.
* `env_plan.SITE_TYPES` = office_building, transit_station, perimeter_site,
  retail_street, car_park, event_plaza. `infer_site_type` falls back on
  keywords in the environment id, zone ids, zone tags and prop types, and
  defaults to `event_plaza` (`survsim/export/env_plan.py`).
* `layout.Layout` carries `entrances` with side/along/yaw and refuses solids
  on a 3 m entrance throat. `layout.pick_time` already samples a date and
  local hour, and `solar_position` lights the scene from it
  (`survsim/generator/layout.py`). It is daytime only: local hour 07:00–18:30
  with the sun ≥ 12° up. Separately, `Scenario.time_of_day` (`{start: ISO
  datetime}`, `survsim/core/models.py`) exists and `env_plan.lighting_for`
  reads its hour to pick a day or night preset (night if ≥ 20:00 or < 06:00).
  So the renderer has a clock and the Director ignores it.

### 5.1 Schema proposal [proposal]

A `SiteProfile` written by the Recorder next to `calib`, one per world:

```yaml
site_profile:
  version: 1
  site_type: transit_station            # env_plan.SITE_TYPES
  frame: site_m                          # SI, same frame as world.parquet
  clock: {tz: Europe/London, start: "2026-03-09T07:30:00", calendar: weekday}
  zones:
    - id: zone.platform
      function: platform                 # controlled vocabulary, below
      policy: queue                      # = Zone.tag (unchanged)
      polygon: [[...]]
      level: 0
      hours: "Mo-Su 05:30-00:30"         # OSM opening_hours grammar
      occupancy_prior: {source: design|learned|none, by_hour: [...]}
      allowed_roles: []                  # = Zone.allowed_roles
  portals:
    - {id: entrance_0, kind: main, direction: both, zone: zone.entrance_0}
  events:                                # timetable drivers (L4)
    - {kind: departure, zone: zone.platform, times: ["07:56", "08:11", ...]}
  patrols:                               # L6; synthetic only
    - {route: [zone.fence_line, zone.yard], every_s: 3600, jitter_s: 600}
  provenance: {zones: ground_truth|inferred|imported, noise: {...}}
```

**Function vocabulary** = the ids the generator already emits, stripped of
`_k`: entrance, gateline, platform, reception, lobby, concourse, street,
open, yard, bays, stage, crowd, fence_line, restricted, blindspot, plus
`none` for a person in no zone. Add
`smoking_area` and `bus_stop`, which are where the hard negatives
(`smoke_break`, `commute_wait`) should live if they are to be distinguished
at all. This is exactly round 3's one-hot, so arm D reproduces unchanged
from a profile-loaded feature.

### 5.2 The Director needs a clock [proposal]

58 §7.1 says time of day "is not varied by the `alarm_scale` recipe (worlds
carry no clock; the Director's schedule is time-invariant), so its gain is 0
by construction" [repo]. To make it testable:

1. **World clock.** Each world gets a start datetime sampled from a
   calendar distribution (weekday/weekend/holiday × hour-of-day), written
   into the existing `Scenario.time_of_day.start` so that `lighting_for`
   and the behaviour agree (a night world is dark *and* quiet). `pick_time`
   cannot be reused as it stands, because it only samples daylight.
2. **Arrival intensity λ(zone, t).** Replace the time-invariant arrival
   schedule with an inhomogeneous Poisson process whose rate follows the
   profile's `events` (a platform surge before each departure, a
   shift-change wave at 06:00/14:00/22:00 on perimeter sites, lunch at
   retail).
3. **Behaviour mix conditioned on t.** `commute_wait` concentrates around
   departures, `smoke_break` around break times, `patrol` on its route
   schedule. **Crucially, the suspicious behaviours must be sampled from
   distributions that overlap the innocent ones in time as well as space**,
   or time becomes a label (below). Loitering must also happen at 07:55 on
   a platform.
4. **Closed-hours regime.** Outside `hours`, an innocent presence in a zone
   is rarer but not zero (cleaners, staff with an allowed role). That gives
   the role layer something to explain.

### 5.3 Noisy profiles, because real ones are wrong [proposal]

A profile that exactly matches the generator is a leak dressed as a feature.
SurvSim should emit the *true* profile for ground truth and a *degraded*
profile as the model input, with named perturbations:

* polygon jitter (σ 0.5–2 m) and dropped or merged zones,
* function mislabels at a rate p (e.g. platform ↔ concourse),
* timetable drift (trains late by an exponential delay) and stale
  timetables (last season's),
* missing layers (no L4 at 40 % of sites, no L6 at most),
* inferred rather than ground-truth zones: run the §3 pipeline on the
  world's own clean tracks and feed its output.

The last one is the honest test: it measures whether the automatic route
buys what the hand-labelled one does.

## 6. Evaluation: generalising the context ablation

Round 3's arm D is a single ablation with a single feature. The general
design is a **ladder of context arms**, each adding one layer, all sharing
arm B's folds, hyper-parameters and selection rule (58 §7.1), and all
pre-registered before any number is seen [proposal]:

| Arm | Adds | Measures | Main leakage risk | Control |
|---|---|---|---|---|
| B | track only | baseline (3.114 @ 0.842) | — | — |
| D1 | zone policy tag | coarse context | little; tag is shared by innocents and loiterers | — |
| D2 | zone function (true) | round 3 arm D (2.468 @ 0.822) | loiter spawn zones ≠ innocent zones in the generator | stratify recall worlds so every function hosts both |
| D3 | function (noisy/inferred) | value under realistic profiles | none new; *should* be ≤ D2 | report the D2−D3 gap |
| D4 | + time of day / calendar | L4 value | **clock as a split label**: if recall worlds are sampled at different hours from clean ones, *t* identifies the split | sample world clocks from one distribution for both splits; permutation test that *t* alone gives AUC ≈ 0.5 for world type |
| D5 | + time-to-next-event | timetable value | same, plus loiter times aligned to departures only if the generator does so | loiterers sampled independent of events *and* a variant aligned with them (adversary who knows the timetable) |
| D6 | + learned occupancy prior (L5) | normality value | prior learned from worlds that include the test loiterers | learn L5 on fit-fold clean worlds only; a "poisoned prior" variant learned with loiterers present |
| D7 | + role (authorised list) | L7 value | `intruder` exists only in recall worlds (58 §7.1 already excludes role) | roles must exist in clean worlds too (staff in restricted zones), and the model sees *claimed* role from access control, not the true one |
| D8 | + patrol schedule | L6 value | patrols only in clean worlds would label them | patrols in both splits |

**Reporting.** For each arm: H12 FA/cam-h [Garwood] and recall [bootstrap]
at its own select-fold operating point, plus FA at the first θ reaching
recall ≥ 0.80 on its curve (58 §7.1's descriptive metric). Report the
**marginal** gain of each rung, not just the top. A single "context helps
40 %" hides which layer, and the layers differ by orders of magnitude in
capture cost and privacy cost (the last two columns of the §1 table). The quantity a
buyer wants is *FA reduction per unit of site-profile effort*.

**Order effects.** Marginal gains depend on order: time helps less once
function is present, because the platform is where timed waiting happens.
Report a leave-one-layer-out table as well as the forward ladder.

**The leakage test that must pass first** [proposal]. For each context
feature f, train a classifier to predict *world type* (clean vs recall) from
f alone, pooled over all ticks. If its AUC is materially above 0.5, f
carries split identity and any gain it shows is suspect. 58 §7.1 already
applied this reasoning by hand to world-elapsed *t* (clean worlds 1,800 s,
recall 300 s) [repo]. This makes it a gate. It would also have caught
round 1's centroid leak (58 §5: `loiter_arc` walked to the exact zone
centroid) [repo].

**What round 3 already says** [repo; derived]. Arm D's 20.7 % is the *upper
bound* of D2 under a perfect, true profile. D3 will be lower. The reduction
is also far short of the ~2,900× gap to the assumed 0.001 budget (58 §5), so context
is a multiplier on a review queue, not a path to autonomous alarms. The
calibrated track-only arm C reached 0.335 FA/cam-h at recall 0.553
(`round3_results.md`) [repo], which shows that moving along the operating
curve still buys more than context does at fixed recall. Say both.

**Real-data validation.** None of this certifies anything on a real site.
The minimum real test is one site class, with its profile captured by the
§3 pipeline and confirmed by the installer. Compare B and D3 on soak footage
of ≥ 3,000 camera-hours (58 §5, 49 §5) [repo], with the site's own alarm
log as the incident set.

## 7. Privacy and DPIA implications

The profile layers differ sharply in legal weight.

* **L1–L3 (geometry, zones, portals)** describe places, not people.
  Low risk, but security-sensitive (a map of blind spots and emergency exits
  is useful to an intruder). Access control, not DPIA, is the issue.
* **L5 (occupancy prior)** is aggregate if stored as counts per cell-hour.
  It becomes personal data if it retains per-track dwell histories, which
  the "same person at the same gate daily" feature (58 §5) would need
  [derived]. The ICO lists as likely-high-risk "processing which involves
  tracking an individual's geolocation or behaviour", "data processing at
  the workplace" and "processing location data of employees" [F: ICO
  examples of high-risk processing]. So a cross-day identity dwell feature
  pulls the system into those categories.
* **L4 (timetables)** is harmless for trains. For *shift* timetables and
  break times it describes when named groups of employees are where.
  Combined with tracks, it infers individuals' attendance.
* **L6 (patrols)** is employee monitoring by construction: a model that
  treats an off-schedule guard as anomalous is monitoring the guard.
* **L7 (authorised-role lists)** joins access-control identity to video
  tracks. The ICO names "combining, comparing or matching personal data
  obtained from multiple sources" as a high-risk category, and "the novel
  application of existing technologies (including AI)" as a criterion that
  requires a DPIA "when combined with any other criterion" [F]. L7 hits
  both.

The ICO's surveillance guidance says a DPIA is "a legal requirement and
applies in most cases, due to the inherent privacy risks involved". It asks
controllers to "identify the minimum amount of personal data you need", and
says data may be reused for a new purpose only if it is "compatible with
your original purpose", the individuals consent, or the law sets a clear
obligation. For monitoring workers, employers should "consult with
your workforce (eg staff and/or trade unions), especially during the DPIA
process" [F: ICO video surveillance guidance]. Report 44 §1.3 maps the
Art 35(3) triggers for a CCTV-analytics product [repo: 44].

**Design consequences** [proposal]:

1. **Roles, not names.** L7 stores roles (`cleaner`, `guard`) and the
   access-control system asserts "badge of role R entered door D at t". The
   analytic never holds the roster. This minimises data and keeps the
   identity join in the system that is already lawful for it.
2. **Aggregate L5 by default.** Per-cell-hour counts with k-anonymity
   thresholds (suppress cells with < k distinct tracks). Cross-day identity
   dwell is a separate, off-by-default module with its own DPIA.
3. **Purpose lock.** Patrol and shift data may *discount* alarms (a guard on
   schedule is not a loiterer). They must not be used to *score* staff. That
   second use is the function creep the ICO warns against. Enforce it in
   code: the patrol feature can lower a score and never raise one.
4. **Retention.** The profile is config, retained for the life of the
   deployment. Learned statistics decay (rolling 8 weeks). Per-track
   evidence follows the video retention schedule (53).
5. **SurvSim advantage.** Every profile SurvSim emits is synthetic, so the
   high-risk layers can be developed and ablated (D7, D8) with no personal
   data at all. The DPIA question comes only at deployment, and the
   ablation tells the controller whether the risky layer is worth its risk.
   That is the proportionality argument, made with numbers.


**Q1. How would you cut nuisance alarms without more labelled data?**
Give the model context the track lacks, and get that context without
labelling. In our simulator, adding the zone's function to a GBM cut false
alarms 21 %, from 3.114 to 2.468 FA/cam-h at recall ~0.82, on 3,000 held-out
camera-hours. The context is not labels. It is the installer confirming
inferred zones: cluster track births for entrances, use dwell heatmaps for
stop zones (Makris & Ellis 2005 learned entry/exit and stop zones
unsupervised), and one click per zone to confirm "platform". Then import
OSM entrances and opening hours where they exist. The second lever is to
move along a calibrated operating curve: our isotonic GBM gave 0.335
FA/cam-h at recall 0.55, which suits a review queue.

**Q2. Why not just schedule the rule off during busy hours?**
That is context as a hard gate, and every VMS already does it. Axis action
rules take a schedule, for example [F]. It throws away recall exactly when
crowds give cover. As a *feature*, the model can learn that 70 s on a
platform at 07:55 is normal and 70 s at the fence at 07:55 is not. Our
evidence is only for zone function. Time of day was untestable because our
worlds had no clock, and I would say that rather than claim it.

**Q3. What does ONVIF give you here?**
Polygons and thresholds. `LoiteringDetector` has a `Field` polygon in
normalised image coordinates and a `TimeThreshold` duration [F]. There is
no typed zone function, no schedule, no occupancy. So context lives in the
VMS or in our own site profile. Zones should be stored in site metres and
projected per camera through the current homography, so a slewed PTZ keeps
its zones.

**Q4. What is the biggest risk in learning "normal" occupancy?**
Normality learned from live traffic includes the behaviour you want to
catch. A regular dealing spot becomes a "stop zone". Learn only from reviewed
or non-alarmed windows, cap the discount a prior can apply, and keep human-
confirmed function above the learned prior. In the simulator, test it with
a poisoned-prior arm.

**Q5. How do you know the context gain isn't leakage?**
Because I have been bitten. Round 1's loiterers walked to the exact zone
centroid, and world-elapsed time differed between clean and recall worlds.
Now every context feature must first fail to predict the world type on its
own, with AUC ≈ 0.5. Clocks and roles are sampled from the same
distribution in both splits, and the gain is reported per layer, with
noisy and inferred profiles as well as the true one.

**Q6. Does context get you to the operator budget?**
No. Twenty-one percent against a ~2,900× gap is a multiplier on a review
queue, not autonomy. The honest product is a ranked queue with a calibrated
score and a site-chosen operating point, with context improving the ranking.

**Q7. What are the privacy costs?**
Zones and entrances describe places. Shift timetables, patrol schedules and
role lists describe employees. Joining access control to video is
"combining data from multiple sources" plus novel technology, which is
DPIA territory in the ICO's list [F]. Store roles, not names. Keep occupancy
aggregate with k-thresholds. Make staff data able only to *lower* alarm
scores, never to score staff. Use synthetic ablation to show whether the
risky layer earns its place before anyone processes real rosters.

**Q8. How would you register cameras to a floor plan at scale?**
Four or more click-pairs per camera between image and plan give a ground
homography with no intrinsic calibration. Store zones in plan coordinates.
Watch the far field, where small errors blow up near the horizon, and raised
surfaces like platforms, which need their own plane height. For PTZ cameras,
compose with the pan/tilt/zoom model so the homography follows the head.
Where BIM exists, IFC spaces give polygons and design occupancy
(`OccupancyNumberPeak`) as a prior [F].

## 9. Sources (fetched 2026-09-27)

1. ONVIF Analytics Service Specification v26.06, §A.3 Field Detector, §A.4
   Loitering Detector, metadata GeoLocation —
   https://www.onvif.org/specs/srv/analytics/ONVIF-Analytics-Service-Spec.pdf
2. Axis Object Analytics user manual — https://help.axis.com/en-us/axis-object-analytics
3. Axis Perimeter Defender user manual — https://help.axis.com/en-us/axis-perimeter-defender
4. Milestone MIP SDK, analytics and MAD events —
   https://doc.developer.milestonesys.com/mipsdk/reference/protocols/analytics_and_mad_events.html
5. Stauffer & Grimson, *Learning patterns of activity using real-time
   tracking*, TPAMI 2000, doi:10.1109/34.868677 (abstract via
   https://api.openalex.org/works/doi:10.1109/34.868677)
6. Makris & Ellis, *Learning semantic scene models from observing activity
   in visual surveillance*, IEEE TSMC-B 2005, doi:10.1109/TSMCB.2005.846652
   (abstract via OpenAlex)
7. Morris & Trivedi, *A survey of vision-based trajectory learning and
   analysis for surveillance*, IEEE TCSVT 2008, doi:10.1109/TCSVT.2008.927109
   (abstract via OpenAlex)
8. Wang, Ma & Grimson, *Unsupervised activity perception in crowded and
   complicated scenes using hierarchical Bayesian models*, TPAMI 2009,
   doi:10.1109/TPAMI.2008.87 (abstract via OpenAlex)
9. OSM wiki, Key:entrance — https://wiki.openstreetmap.org/wiki/Key:entrance
10. OSM wiki, Simple Indoor Tagging — https://wiki.openstreetmap.org/wiki/Simple_Indoor_Tagging
11. OSM wiki, Key:opening_hours — https://wiki.openstreetmap.org/wiki/Key:opening_hours
12. buildingSMART IFC4.3.x-development, property definitions
    OccupancyNumberPeak / OccupancyTimePerDay / OccupancyType —
    https://github.com/buildingSMART/IFC4.3.x-development/tree/master/docs/properties/o
13. ICO, Examples of processing likely to result in high risk —
    https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/examples-of-processing-likely-to-result-in-high-risk/
14. ICO, Video surveillance: complying with the data protection principles —
    https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/how-can-we-comply-with-the-data-protection-principles-when-using-surveillance-systems/

**Tried and not usable on 2026-09-27** (claims about these products are
therefore *not* made above): Avigilon UMD/UAD docs pages (navigation only),
Genetec RSA brochure (brand string only), Milestone time-profile page (404),
buildingSMART IfcSpace HTML (403).

**Repo sources:** `docs/research/58_LOITER_RULE_REDESIGN.md` §5–7;
`out/experiments/h58_round2/round3_results.md`; `survsim/core/models.py`
(`Zone`); `survsim/generator/site.py`; `survsim/generator/layout.py`;
`survsim/export/env_plan.py`; reports 29, 34, 44, 49, 51, 53.
