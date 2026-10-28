# 13 · Open questions worth a hypothesis, and what can still be added

Two lists. The first is what this simulator could *answer* that nobody has
answered properly, because the experiment needs ground truth real CCTV cannot
provide. The second is what the simulator could *become*.

Both are ordered by value, and each question states the experiment, so it can be
run rather than merely discussed.

---

## Part A — Questions that need a hypothesis and an experiment

### A1. Where exactly does identity survive a disguise? (highest value)
The literature reports clothes-changing ReID Rank-1 in the low 30s, but not *why*
it fails. With `evasion.residual_cues` we can vary one cue at a time.

* **Hypothesis**: identification accuracy is predicted by the residual-cue vector,
  not by the number of techniques worn — one technique that removes the face
  hurts more than three that only alter clothing.
* **Experiment**: sweep all compatible 1–3 technique combinations; measure ReID
  Rank-1 against residual `face`, `gait`, `body_shape`, `height`.
* **Deliverable**: a *disguise-difficulty curve* — the first quantitative account
  of which combination defeats which method. Nobody has this because real data
  has no ground-truth "same person, deliberately disguised" pairs at scale.

### A2. Does height survive everything?
Height is the one cue clothing cannot remove and gait cannot fake.
* **Hypothesis**: calibrated stature estimation beats appearance ReID under
  disguise, and the crossover happens at roughly 2 evasion techniques.
* **Experiment**: estimate height from the ground-plane homography; compare to
  OSNet/CLIP-ReID as disguise level rises.
* **Caveat to test honestly**: height estimation error is dominated by extrinsic
  calibration error (1° at 30 m ≈ 3.9 m ground error, from R02), so measure the
  degradation jointly.

### A3. How much does camera *placement* matter compared to model choice?
Every vendor sells a better model; nobody sells a better camera layout.
* **Hypothesis**: for a fixed budget, moving from a naive to an optimised rig
  improves end-to-end MTMC more than swapping the detector for the next SOTA.
* **Experiment**: fix the model, vary placement (random, perimeter, greedy, our
  optimiser); then fix placement, vary the model. Compare effect sizes.
* **Why it matters commercially**: if placement dominates, the product is a
  survey tool, not a model.

### A4. Where is the false-alarm cliff for an operator?
R03 gives 1,200× between research operating points and deployment reality.
* **Hypothesis**: measured system P_d collapses non-linearly above ~6 alarms per
  camera-hour because operators bulk-acknowledge, so *model* P_d and *system* P_d
  diverge sharply.
* **Experiment**: simulate operator behaviour with an acknowledge-latency model;
  sweep alarm rate; plot model P_d vs realised P_d.

### A5. Do degradation and realism interact, or add?
* **Hypothesis**: past a moderate degradation level, extra render realism stops
  mattering — noise and compression destroy the very detail that photorealism
  adds — so effort is better spent on the sensor model than on the renderer.
* **Experiment**: 3 render-quality levels × 5 degradation profiles, train and
  evaluate detection; test for interaction.
* **This is the highest-leverage question for our own roadmap**, because it tells
  us whether to chase photorealism at all.

### A6. What is the real low-fps cliff for tracking?
R01 records AssA collapsing 43.6 → 27.8 % between 3 and 1 fps.
* **Hypothesis**: for a fixed compute budget, 4–6 fps at higher resolution beats
  25 fps at low resolution, because association survives better than detection.
* **Experiment**: sweep fps × resolution at constant pixel throughput.

### A7. Can behaviour be classified when appearance is uninformative by design?
Our matched pairs make appearance carry zero label information.
* **Hypothesis**: models trained on conventional datasets lose most of their
  accuracy on matched pairs, revealing they were reading clothing all along.
* **Experiment**: train on an unmatched set, test on matched; measure the drop.
* This is a publishable negative result about the whole field's datasets.

### A8. How much does a blind spot actually cost?
* **Hypothesis**: MTMC identity error scales with *transit-time uncertainty*
  through unobserved regions rather than with blind area.
* **Experiment**: vary blind-spot size and topology at constant coverage.

### A9. Does multi-sensor corroboration beat a better camera model?
* **Hypothesis**: a weak detector plus one corroborating sensor (RF/audio/door)
  achieves a lower false-alarm rate than a strong detector alone — the
  architectural claim in R05.
* **Experiment**: add simulated RF/door events with realistic false-alarm rates;
  compare AND-gated alarms to single-sensor.
* **Watch for**: correlated nuisance (weather affects both), which breaks the
  independence the AND-gate assumes.
* **H63 (2026-09-28, 32 §H63):** against a guard-uniformed intruder, appearance-role suppression gives recall 0.027; a badge+RF corroboration-mismatch rule gives 0.745 (96 % of the line-cross ceiling) at 0.018 twin FA/cam-h — corroboration, not appearance, is what separates a uniform from an authorisation. Simulated sensors.

### A10. Are event cameras useless for loitering?
* **Hypothesis**: event cameras lose a person entirely once they stop moving
  (D05: "blind to the stationary components"), so loitering detection fails
  catastrophically where frame cameras merely degrade.
* **Experiment**: render high-fps sequences, synthesise events with v2e, measure
  false-negative rate vs seconds-since-motion.

### A11. What does a PTZ patrol actually cost in missed events?
* **Hypothesis**: a patrolling PTZ has a duty cycle low enough that an adversary
  who observes one full cycle can cross with near-certainty.
* **Experiment**: sweep patrol period against crossing time; compute interception
  probability with and without camera-aware timing.

### A12. Does synthetic pre-training still help once real data is plentiful?
MOTSynth reports large few-shot gains and small abundant-data gains.
* **Hypothesis**: the benefit persists only for *rare* classes — tamper,
  abandoned object, disguise — precisely where real data cannot be collected.

---

## Part B — What can be added to the simulator

### B1. Perception ground truth (near-term, unblocks everything)
* COCO export, 2D/3D keypoints, amodal boxes, occlusion ratio.
* Optical flow and velocity buffers (already available from the engine).
* Per-frame difficulty score: pixel height × visibility × lighting, so results can
  be bucketed by difficulty rather than averaged into meaninglessness.

### B2. Sensors beyond the camera
* **RF**: Wi-Fi probe/BLE emitters per person with MAC randomisation, path loss,
  shadowing; truth mapping MAC → identity. Enables the fusion experiment (A9).
* **Audio**: footsteps, raised voices, glass break, with DOA and realistic
  false-alarm rates.
* **Access control / door contacts / fence vibration**, each with a nuisance-alarm
  model — the corroboration story needs the nuisances, not just the events.
* **Thermal / IR** rendering via material emissivity; **event camera** synthesis.

### B3. Environment realism
* Weather and time-of-day director (rain, fog, snow, dusk) driving both the render
  and the degradation profile coherently.
* Crowd density curves and queueing; groups that form, split and merge.
* Vehicles, drones and animals — the dominant nuisance sources at real perimeters.

### B4. People
* MetaHuman parametric wardrobe and body wired end-to-end (in progress).
* Real gait from motion capture or pose-estimated CCTV, instead of game clips.
* Interaction: doors, turnstiles, bags handed over, ladders carried.
* Children, wheelchairs, prams — both for realism and for fairness auditing.

### B5. Adversarial and red-team
* Camera-aware path planner that routes through blind spots and PTZ gaps.
* Adversarial patches and printed patterns against detectors.
* Coordinated multi-actor incidents (decoy plus principal).

### B6. Evaluation and product
* Detection/MOT/MTMC/ReID baselines with HOTA/IDF1/mAP on our data.
* i-LIDS-style timed scoring harness (partly built) plus operator-load simulation.
* **Scenario regression suite as CI**: a fixed set of scenes an analytics build
  must pass — this is the commercially distinctive artefact, per D03.
* RTSP re-streaming and ONVIF metadata emission, so a real VMS can ingest the
  output and the whole chain is exercised, not just the model.
* Camera-placement optimiser exposed as a site-survey tool (D04 calls this the
  highest-value business output).

### B7. Scale
* Headless batch rendering across seeds, multi-process; dataset cards; splits with
  no identity leakage (already enforced by hash).
* Shared-memory capture path to escape the ~10 fps PNG-encoding ceiling (D12 §4).

---

## The three I would fund first

1. **A5 (realism × degradation interaction)** — it decides whether photorealism is
   worth the effort, and no one can answer it without a controllable renderer.
2. **A1 (disguise-difficulty curve)** — the clearest novel result, directly aligned
   with the cross-epoch ReID capability already built.
3. **B6 (scenario regression CI)** — the piece that turns a research simulator into
   something a security vendor would pay for.
