# 83 — PTZ auto-tracking, slew-to-alarm and hand-off

Scope: how pan-tilt-zoom (PTZ) cameras are driven in real products, the computer-vision chain
from a fixed-camera detection to a PTZ command, and where SurvSim can measure things that real
sites cannot. Companions: `75_CAMERA_GEOMETRY_AND_CALIBRATION.md` (calibration errors, PTZ
re-registration §4.4), `73_TRACKING_SIM2REAL.md` (PTZ hand-off note), `76_INTRUSION_BEHAVIOURS_BEYOND_LOITER.md`,
`74_SYSTEM_DESIGN_DRILLS.md` (drill 1), `49_EVALUATION_STATISTICS_AND_EXPERIMENT_DESIGN.md`,
`66_HYPOTHESIS_BACKLOG.md`, `FACTS_VERIFIED.md`, `RETIRED_CLAIMS.md`.

Tags: **[V]** fetched and read this session, or measured in the repo; **[A]** from memory, not
fetched — treat as a lead, not a fact; **[X]** fetched and found wrong. AUDIT_83_H56 (2026-09-27)
fetched the ONVIF PTZ spec (v26.06, read via pdftotext) and the Profile S/T pages: four ONVIF items
moved [A] → [V] and one to [X] (auto-tracking *is* partly standardised, `MoveAndStartTracking`).
The Axis/Bosch/Hanwha URLs loaded only generic pages or 404/redirected, so everything vendor-specific
below stays [A] and must be checked before it is quoted to a customer.

## 1. What the repo already has

* `survsim/director/camera_director.py` — PTZ patrols (preset tours) and the six tamper kinds
  `TAMPER_KINDS = ("cover", "spray", "tilt", "unplug", "glare", "defocus")` [V]. `cover` and
  `unplug` blind the camera (it emits no GT). `tilt` is the only tamper that changes geometry.
  `CameraDirector.live_camera(camera_id)` returns the camera *as it is now* — PTZ pose and tilt
  applied — so ground truth follows the live head (CLAUDE.md principle 2) [V].
* `survsim/core/geometry.py::usably_visible` — the one definition of visible: in frame, in
  front, ≥ 20 px tall (principle 5) [V]. Coverage, "was it observed?" and PTZ acquisition must
  all use it.
* `75` §4.4: PTZ `R = R_mount·R(pan, tilt)`, `K = K(zoom)`; re-derive from telemetry every frame;
  drop positions mid-slew (rolling-shutter shear). `75` Q6 red flag: "one stored homography per PTZ".
* H39 (`FACTS_VERIFIED.md`, `75`) [V]: known-height auto-calibration with **datasheet focal**
  gives world RMSE **0.96 m [0.77, 1.20] under 20 m** and **2.92 m at ≥ 30 m**; exact-calibration
  floor 0.21 m; free-f fits are broken (57.4 m). `cam_ptz` was excluded because its live hfov
  (30–35°) differs from the configured 60° — the principle-2 trap in action.
* H34 (`FACTS_VERIFIED.md`) [V]: label-free drift monitor — PSI/KS fire on 100 % of stationary
  windows (1,440 FA/24 cam-h), calibrated mean-shift catches 6/12 shifts and misses blur ×3.
  Relevant to tamper detection (§7).
* `73` line ~254: a slewing PTZ breaks image-space motion models; SurvSim can test hand-off with truth.
* `76` ~397: alarms are verified by a PTZ slewed onto the alarm.

## 2. How PTZ control works in products

### 2.1 ONVIF PTZ service

The ONVIF PTZ Service Specification [V] (https://www.onvif.org/specs/srv/ptz/ONVIF-PTZ-Service-Spec.pdf)
defines `AbsoluteMove`, `RelativeMove`, `ContinuousMove`, preset set/goto/remove, **preset
tours**, and `GetStatus`, which returns position and an **optional** `MoveStatus` of IDLE, MOVING
or UNKNOWN (present only if the device signals the MoveStatus capability; spec v26.06) [V].
Coordinate spaces are declared per device: the generic pan/tilt position space normalised to
[−1, 1] "shall be provided by every PTZ node that supports absolute pan/tilt" (§5.7.1.1) [V]; zoom
[0, 1] is the generic zoom space [A — not re-read]. Consequences:

* **Normalised is not degrees.** The generic space maps to a device-specific range; converting
  a world bearing to a pan value needs either a device that exposes the optional spherical
  pan/tilt position space in degrees (spec §5.7.1.2, defined for a ceiling-mounted dome) [V] or a
  per-model table. This is an integration error source separate from calibration.
* **MOVING is the blind flag — when the device reports it.** `MoveStatus` tells you when the head
  is in motion; analytics must not trust image positions (or run image-space trackers) while it
  reads MOVING. It is optional, so a device without it needs a commanded-move timer instead.
* Profile S covers PTZ control "for conformant devices and clients that support such features"
  (optional) [V]; Profile T lists H.264/H.265 and makes **PTZ control mandatory for clients**,
  conditional for devices [V] (https://www.onvif.org/profiles/profile-s/,
  https://www.onvif.org/profiles/profile-t/, fetched 2026-09-27). "VMSs actually check them" stays [A].
* ~~Auto-tracking itself is not standardised in ONVIF~~ **[X]**: the PTZ spec defines
  `MoveAndStartTracking` (§5.3.6, v26.06) — an atomic "move to a position (GeoLocation, preset or
  PTZVector), then delegate PTZ control to the tracking algorithm", with an optional ObjectID when
  detection and tracking run in the same device; mandatory only for nodes signalling MoveAndTrack.
  What is standardised is the hand-off command; the tracker's behaviour (loss, timeout, target
  choice) remains vendor-specific [A].

### 2.2 Vendor auto-tracking [A]

* **Axis Autotracking 2** (https://help.axis.com, product pages for Q60-series; not fetched):
  on-camera; the operator clicks a target or the camera starts on motion in a zone; the camera
  pans/tilts/zooms to keep the object centred; it gives up after loss and returns to a home
  preset. Tuned for one object at a time.
* **Bosch Intelligent Tracking** (AUTODOME / MIC series; not fetched): uses on-board Intelligent
  Video Analytics; can be triggered by an IVA alarm rule and follows the object; modes include
  follow-and-return-to-preset.
* **Hanwha auto-tracking** (Wisenet PTZ Plus; not fetched): on-board tracking; recent models
  claim deep-learning object classes (person/vehicle) to avoid tracking foliage.

Common shape [A]: single target, on-camera, image-space (centre the box), zoom chosen to hold a
target height, timeout then return-to-home. None of them know about other cameras — that is
the VMS's or our job.

### 2.3 Preset tours / guard tours

A guard tour cycles through presets with a dwell per preset. It is the default idle
behaviour of most perimeter PTZs [A]. Its weakness is arithmetic: with N presets, dwell d and
transit s, any given preset is watched d/(N·(d+s)) of the time. A 6-preset tour with 10 s
dwell and 2 s slew watches each preset 14 % of the time — a guard tour is **not** detection
coverage and must not be counted as such in `survsim rig` coverage. SurvSim's patrol mode is
exactly this, so `live_camera` makes the gap measurable (§5).

### 2.4 Master–slave (fixed → PTZ)

A fixed "master" camera detects; a PTZ "slave" is steered to the world position. Classic
academic formulations [A]: Zhou et al., "A master-slave system to acquire biometric imagery of
humans at distance" (ACM IWVS 2003); Senior, Hampapur, Lu, "Acquiring multi-scale images by
pan-tilt-zoom control and automatic multi-camera calibration" (WACV 2005); Del Bimbo et al.,
"Exploiting distinctive visual landmark maps in pan-tilt-zoom camera networks" (CVIU 2010).
Two families: (a) calibrate both into a shared ground plane / world frame; (b) learn a direct
lookup from master pixel to slave pan/tilt without full calibration (works for one master–slave
pair, does not generalise to height or new pairs).

## 3. The CV chain: fixed detection → world → PTZ command

1. **Detect** in the fixed camera (box, foot point = bottom-centre of the mask-derived box).
2. **Back-project** the foot point through the fixed camera's homography to the ground plane
   → world (x, y). Error here is H39's: ~1 m under 20 m, ~3 m at 30 m+ with datasheet focal.
3. **Predict** forward by the command latency (below) using the world-space track velocity.
4. **Aim**: bearing and elevation from the PTZ mount (`R_mount`) to the predicted point at
   target mid-height (~0.9 m); invert `R(pan, tilt)`; convert to the device's coordinate space.
5. **Zoom**: choose hfov so the target is H px tall (e.g. 40 % of frame for recognise), with a
   margin that covers the position uncertainty.
6. **Acquire**: once `MOVING → IDLE`, run a detector in the PTZ image and associate with the
   predicted point (nearest to centre, or appearance match to the master crop).
7. **Close the loop**: switch to image-space centring (vendor auto-track) or keep world-space
   steering from the fixed cameras.

### 3.1 Zoom budget — the calibration error sets the widest usable zoom

Position error ε at range R subtends ≈ ε/R radians. To keep the target in frame the half-fov
must exceed that, plus the target's own motion during latency. With H39 numbers:

| range | ε (H39 datasheet f) | angular error | min hfov (2×, margin) | person height at that hfov, 1280 px |
|---|---|---|---|---|
| 15 m | 0.96 m | 3.7° | ~15° | ~1.75/ (2·15·tan 7.5°) ×1280 ≈ 570 px |
| 30 m | 2.92 m | 5.6° | ~22° | ≈ 190 px |
| 60 m | 2.92 m (assumed flat — extrapolation) | 2.8° | ~11° | ≈ 190 px |

(Arithmetic [V], ε values [V] from H39; the 60 m row is an extrapolation [A].) Reading: at the
H39 error, first-look zoom is limited to "detect/recognise-ish" framing; tight identification
framing needs a second, image-closed-loop step. Exact calibration (0.21 m) would allow ~4×
tighter first-look zoom. That is the value of calibration in operational terms.

### 3.2 Latency budget

Illustrative [A] components: fixed-camera detection + tracker confirmation 0.3–1 s;
VMS rule + command 0.1–0.3 s; slew at ~100–400°/s preset speed (big PTZs are slower under
load; wiper/heater housings slower still) plus settle ~0.3–0.5 s; autofocus after zoom
0.3–1 s; PTZ-side detection 0.1–0.2 s. Total **~1.5–3 s** is a reasonable first guess; a
walker covers 2–5 m in that time, a runner 6–15 m — larger than H39's error. So **prediction
matters more than calibration for runners**, and calibration matters more at range for walkers.
These are the knobs H56 should sweep rather than assert.

## 4. Target loss and re-acquisition

Loss causes: occlusion, leaving the PTZ view faster than it can slew, zoom too tight, autofocus
hunt, IR switch at dusk, a second alarm stealing the head. Standard policy [A]: coast on the
world-space prediction for T_coast (1–3 s), widen zoom by a factor, re-detect; after T_giveup
return to preset. Re-acquisition must re-verify identity — the nearest person to centre is
often the wrong person in a crowd. SurvSim scores that with actor-aware matching (principle 4:
an alarm on the wrong person is not a hit): an acquisition counts only if the uid in the PTZ
frame equals the alarm's uid **and** it is `usably_visible` at the required height.

## 5. The "PTZ blind while slewing" gap — and why SurvSim can measure it

While a PTZ slews, zooms and focuses, it produces motion-blurred or sheared frames that are
useless for detection and misleading for trackers (`75` rolling-shutter row). And while it is
aimed at alarm A, it is not watching its preset/tour. Real sites cannot measure either gap
because nobody records what the PTZ *should* have seen.

SurvSim can, because GT follows the live camera (principle 2): `live_camera()` gives the actual
pose each tick, and `usably_visible` over that pose gives, per person-second:

* **blind time** = time in MOVING (or with hfov/focus not settled) — no detections credited;
* **time-to-acquire** = alarm time → first frame the target uid is usably visible at ≥ H px in
  the live PTZ view;
* **opportunity cost** = person-seconds of events in the PTZ's home coverage that went
  unobserved because the head was away (a missed second intrusion is the headline metric);
* **wrong-target acquisitions** = acquisitions where the centred uid ≠ alarm uid.

A test must pin that scoring uses `live_camera`, not the configured pose — the H39 `cam_ptz`
exclusion (live hfov 30–35° vs calibrated 60°) is the concrete example of what happens otherwise.

## 6. Multi-target contention

One PTZ, two alarms. Policies [A]: FIFO (finish the first), pre-empt on priority (zone,
behaviour class, score), time-slice (alternate with dwell), or hand to a second PTZ. With A1's
operating point at ~120 alarms/h per 40 cameras (`66` H45/H22 context) [V], alarms arrive about
every 30 s site-wide. If each verification occupies a PTZ for ~10–20 s, a single site-wide PTZ is
busy 33–67 % of the time and a second alarm lands while it is busy with probability of that order
(Poisson, assumed). That is the H56 question: does a second PTZ buy measurable
acquisition rate, and is FA reduction upstream (conformal point, `66` H45) worth more than
hardware? Note the PTZ also verifies false alarms, so the false-alarm rate directly consumes PTZ
time — FA/cam-h is a PTZ capacity metric, not only an operator one.

## 7. Tamper kinds and their detection

| SurvSim kind | effect in sim | real detection approach [A] | notes |
|---|---|---|---|
| `cover` | blind, no GT | mean-intensity / variance collapse, loss of edges vs reference | easy; the danger is night (dark scene looks covered) |
| `spray` | pixels degraded | edge-energy / sharpness drop vs reference, colour cast | slow partial spray looks like dirt — H34's dirt misses apply |
| `tilt` | geometry changes | "redirect": feature match vs reference frame fails, homography jumps | only kind that invalidates calibration; `live_camera` applies it |
| `unplug` | blind, no GT | stream loss / VMS heartbeat | trivial, but record the time |
| `glare` | saturation | saturated-pixel fraction; confounded with headlights/sun | needs a time-of-day aware reference |
| `defocus` | blur | Laplacian-variance / high-frequency energy drop | H34's calibrated monitor **missed blur ×3** [V] — generic drift monitors are not tamper detectors |

Vendor cameras ship on-board "tampering" alarms that cover blocked / redirected / defocused [A]
(e.g. Axis "Tampering" in AXIS OS; Bosch IVA "camera trouble"; not fetched). The honest SurvSim
line: tamper detection needs *specific* detectors per kind; H34 shows that a label-free drift
statistic either fires constantly (PSI/KS, 1,440 FA/24 cam-h) or misses blur. A PTZ adds one
more: a PTZ that has slewed looks "redirected" to a naive reference-frame detector, so tamper
detection on PTZs must be keyed to the reported pose (per-preset references, suppressed while MOVING).

## 8. What a defence site deploys

* **Fixed cameras for detection** — perimeter fence lines with overlapping fields, thermal where
  lighting is poor; every metre of fence covered continuously. Detection must not depend on a PTZ
  being in the right place (§2.3 arithmetic).
* **PTZ for verification and recognition** — one per sector, slewed on alarm (master–slave), with
  a guard tour only when idle. The DORI framing (`75`/29): detect on fixed, recognise/identify on PTZ.
* **Radar / fence sensors cueing PTZs** — same chain as §3 with a different master; the RF/audio
  sensors in `survsim/sensors/` are the SurvSim analogue.
* **Operator in the loop** — the PTZ shows the operator the alarm; realised recall is operator-
  and PTZ-limited, which is why H22/H45/H48 (`66`) and H56 belong together.


**Q1. Why not use PTZs for detection and save cameras?**
A guard tour watches each preset a fraction d/(N(d+s)) of the time; a 6-preset tour is ~14 %.
Detection needs continuous coverage, so fixed for detect, PTZ for verify.
*Red flag:* "The PTZ covers 360° so one camera covers the whole fence."

**Q2. Walk me through slewing a PTZ to a fixed-camera alarm.**
Foot point → ground homography → world point; predict forward by latency; bearing from PTZ mount;
convert to device coordinate space; zoom for the position uncertainty; wait for IDLE; detect and
re-associate by uid/appearance.
*Red flag:* skipping prediction, or "send the pixel coordinates to the PTZ".

**Q3. How good does calibration need to be?**
Set by the zoom you want on first look: angular error ≈ ε/R. With H39 datasheet-focal errors
(~1 m < 20 m, ~3 m ≥ 30 m) first-look hfov is ~15–22°, so identification needs a second
closed-loop zoom.
*Red flag:* "sub-pixel reprojection error, so it's fine" — reprojection is not world error.

**Q4. What happens to tracking while the PTZ moves?**
Image-space motion models break and frames shear; mark MOVING from `GetStatus`, don't update
image tracks, carry world-space prediction from the fixed cameras, re-associate on arrival.
*Red flag:* running the same Kalman tracker on PTZ frames through the slew.

**Q5. How do you score a PTZ in simulation?**
Against its live pose (principle 2): time-to-acquire, blind time, wrong-target rate, and
opportunity cost on the home coverage, all via `usably_visible`.
*Red flag:* scoring against the configured pose — H39 had to exclude `cam_ptz` for that reason.

**Q6. Two alarms, one PTZ.**
Name a policy (FIFO / priority pre-emption / time-slice / second PTZ), then quantify: at ~120
alarms/h per 40 cams and 10–20 s per verification, contention is common; FA reduction frees PTZ
time as well as operator time.
*Red flag:* "The PTZ tracks both." It can't unless both are in one field of view.

**Q7. The target is lost after a slew. Now what?**
Coast on prediction, zoom out, re-detect, verify identity before resuming, give up to preset
after a timeout; log a loss event.
*Red flag:* "lock onto the nearest person" — in a crowd that is a wrong-person hit.

**Q8. How do you detect tampering, and what is special on a PTZ?**
Per-kind detectors: cover (variance collapse), defocus (Laplacian variance), redirect (feature
match vs reference), glare (saturation), spray (edge energy). On a PTZ keep per-preset references
and suppress while MOVING. Generic drift stats are not enough — H34 missed blur ×3 and PSI/KS fire
always.
*Red flag:* "one anomaly model catches all tampering."

**Q9. What is ONVIF actually standardising here?**
PTZ moves, presets, preset tours and an optional move status (IDLE/MOVING/UNKNOWN) in the PTZ
service; the generic [−1, 1] pan/tilt space is mandatory for absolute moves, degrees are optional.
`MoveAndStartTracking` standardises the *hand-off* to an on-camera tracker (move, then track, by
GeoLocation/preset/vector); the tracker itself is vendor-specific. PTZ is optional in Profile S and
mandatory for Profile T clients. [V] AUDIT_83_H56.
*Red flag:* "ONVIF auto-tracking works the same across vendors" — and equally "ONVIF has nothing for tracking"

**Q10. Runner vs walker: which failure dominates?**
Latency × speed: at ~2 s a runner moves 12 m, far beyond calibration error, so prediction
dominates; for a walker at 40 m, calibration error dominates.
*Red flag:* one fixed zoom level for all alarms.

## H56 result

H56 (32 §H56, `out/experiments/h56_ptz_slew/results.json`, figures/fig_h56.png; mock geometry, 40 fixed
cameras, 10 seeds, seed-cluster 95 % CI; audited AUDIT_83_H56 — rerun reproduces every number). Acquired =
`usably_visible` on the live PTZ within 3 s of the alarm. Distance bins are ground range from the
**detecting fixed camera** (which sets the injected H39 error), not from the PTZ. H39 datasheet-focal
calibration, 1 PTZ: **0.901 [0.872, 0.936] ≤ 20 m (n 455), 0.802 [0.774, 0.830] 20–30 m (n 600),
0.727 [0.706, 0.747] > 30 m (n 1,945)**; exact calibration 0.967 / 0.958 / 0.978. Both arms share targets,
headings and motion, so the 7–25-point gap is the calibration error; motion alone costs 2–4 points.
2 PTZs, independent alarms: H39 0.897 / 0.772 / 0.691, exact 0.938 / 0.955 / 0.957 — no gain, and slightly
worse in both arms; the cause is **untested** (a 6 m frame and a fixed metric error both scale as 1/range,
so "closer PTZ" is not by itself an explanation). Contention, one hour of Poisson alarms at A1's 120/h per
seed (1,184 alarms): missed second alarm **0.369 [0.325, 0.406] with 1 PTZ vs 0.057 [0.043, 0.070] with 2**
(share of *all* alarms that arrive with every PTZ busy and are not acquired in 3 s). Busy-at-arrival is
0.382 / 0.066: with an assumed 10 s dwell longer than the 3 s window, a queued alarm almost never makes it,
so the missed share is essentially the busy share. Overall contention acquire@3s (H39) 0.479 (1 PTZ) /
0.689 (2); exact 0.612 / 0.914.

**Not met.** ≤ 20 m leg met on the point estimate only (0.901 vs 0.9; the CI [0.872, 0.936] spans the
bar); contention leg met (0.369 ≥ 0.30); the > 30 m leg failed — 0.727 is above the ≤ 0.6 prediction.
**Every PTZ timing is an assumption, not a measured product**: 200 °/s, 0.5 s latency, 0.8 s zoom settle,
6 m framing, 10 s dwell, single open-loop aim, no lead, no occlusion, PTZ's own calibration exact,
H39's error transplanted onto every camera with σ_lat = σ_range/3.

Reading: at A1's load one PTZ per 40 cameras loses ~37 % of alarms to contention, a bigger loss than
calibration in this model (1→2 PTZs +21 points overall; exact vs H39 calibration +13 points at 1 PTZ);
a second PTZ cuts the missed share 6.5×. **Why far targets are lost is untested**: the working guess is
~3 m range error against a 6 m frame (at 30 m slant a 6 m frame is ~11° hfov, below §3.1's ~22° budget),
which H57 tests by widening framing with σ(d) and re-detecting on the PTZ before trusting it.

## Sources

* [V] ONVIF PTZ Service Specification v26.06 (June 2026) — https://www.onvif.org/specs/srv/ptz/ONVIF-PTZ-Service-Spec.pdf (§5.3.6 MoveAndStartTracking, §5.7.1.1–2 position spaces, MoveStatus; fetched 2026-09-27)
* [V] ONVIF Profile S — https://www.onvif.org/profiles/profile-s/ ; Profile T — https://www.onvif.org/profiles/profile-t/ (fetched 2026-09-27)
* [A] Axis Autotracking 2 / tampering — https://help.axis.com (knowledge-base page loads but has neither; product URLs 404 — not verified)
* [A] Bosch Intelligent Tracking — https://www.boschsecurity.com (301 to a life-safety site — not verified)
* [A] Hanwha Wisenet auto-tracking — https://www.hanwhavision.com (home page loads, no auto-tracking detail — not verified)
* [A] Zhou et al., IWVS 2003; Senior, Hampapur, Lu, WACV 2005; Del Bimbo et al., CVIU 2010 (master–slave PTZ calibration)
* [V] Repo: `75_CAMERA_GEOMETRY_AND_CALIBRATION.md`, `73_TRACKING_SIM2REAL.md`, `76_INTRUSION_BEHAVIOURS_BEYOND_LOITER.md`,
  `74_SYSTEM_DESIGN_DRILLS.md`, `49_EVALUATION_STATISTICS_AND_EXPERIMENT_DESIGN.md`, `66_HYPOTHESIS_BACKLOG.md`,
  `FACTS_VERIFIED.md` (H34, H39), `RETIRED_CLAIMS.md`, `survsim/director/camera_director.py`, `survsim/core/geometry.py`
