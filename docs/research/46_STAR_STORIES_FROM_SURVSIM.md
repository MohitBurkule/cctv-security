# 46 · STAR stories from SurvSim

Twenty-three behavioural-interview stories drawn **only** from this repository's
history. Each STAR block is ≤ 180 words (stories 18–23: ≤ 220, with a named competency) so it can be said aloud in about 70
seconds. After each: the metric to quote, the lesson, the follow-up question an
interviewer is likely to ask, and a short answer to it.

**Sourcing rule.** Every number is copied from a file or commit in this repo,
cited by path and/or short hash (read 2026-09-26). The repository is the primary
source here; no web claims are made. Where I characterise *why* something
happened beyond what the file says, it is tagged **[INF]**. Stories 5, 6, 12
and 13 quote experiment numbers; since the audit (AUDIT_43-47.md) every one of
them is reconciled with the **committed** `docs/research/32_EXPERIMENTS_LOG.md`
(H1/H4/H5 `5e5f53d`, H2 `d0d00ac`, H6 `4eac637`) or `docs/12` (batch_v7
`8c3b03b`), not with the uncommitted `out/experiments/*/row.md` an earlier
draft cited. Pre-fix figures (two-seed AP 0.161, leaked cross-lighting 0.869)
were removed.

How to use: pick four stories that together cover *technical depth*,
*being wrong*, *prioritisation under constraints* and *ethics/judgement*. A
suggested mapping is at the end.

---

## 1. The black render: `unreal.Rotator` is (roll, pitch, yaw)

**Sources:** `docs/BUG_black_render.md`; commits `a329b36`, `84eca5c`,
`25303ff`, `97325e4` (2026-09-18); `tests/test_ue_scripts.py`.

**S.** Our headless Unreal 5.8 editor path rendered every frame pure black, on
both Movie Render Queue and SceneCapture2D. A day went on it.
**T.** Prove whether this was the engine, the GPU/driver, exposure — or us.
**A.** I stopped guessing and bisected the pipeline. SceneCapture2D was also
black, so not MRQ. EXR output proved it was not exposure. The G-buffer had
BaseColor and Normal at zero with alpha zero — *no geometry in view*. Writing a
known colour into a render target read back correctly, so the GPU and readback
worked. That left the view itself, so I dumped actor transforms from the saved
map: the camera read pitch 90. The Python `unreal.Rotator(a, b, c)` is
positionally (roll, pitch, yaw); we had written (pitch, yaw, roll). The camera
stared at the zenith; the sun was below the horizon.
**R.** Keyword rotators everywhere, including `build_scene.py`, which would
have mis-aimed every exported camera; a static test fails on any positional
`Rotator(`. Verified by pixels: MRQ 50 frames mean 157.6, std 21.9.

- **Metric:** 0.0 in every channel before; mean 157.6 / std 21.9 after
  (`docs/BUG_black_render.md`).
- **Lesson:** when output is "impossible", check the inputs you are certain
  about *before* the infrastructure you are not. Three commits fixed real but
  irrelevant misconfigurations first (`84eca5c` title: "three real
  misconfigurations fixed, cause still open").
- **Follow-up:** *"Why did it take a day?"* — Because every earlier fix was
  plausible and genuinely wrong-ish; each one felt like progress. The turn came
  when I asked "is there geometry in view at all?", which the G-buffer answers
  in one frame. Now the rule in `CLAUDE.md` is: when a render is empty, dump
  transforms before suspecting the engine.

---

## 2. Discovering our HOTA was wrong

**Sources:** commit `be9f52a`; `docs/13_BASELINES.md` §"HOTA/MOTA fix";
`docs/research/26_MOT_DEEP_DIVE.md`; commit `9d9188f`.

**S.** Our tracking evaluator reported HOTA for every baseline, and a MOT20
subset row was already written up at HOTA 0.545 (retired; 0.443 after parity).
**T.** While writing a teaching note on HOTA I hand-derived a three-frame worked
example — and our code disagreed with my derivation.
**A.** I went back to the paper's equations rather than trusting either. Our
DetA was TP/(TP+FN), i.e. detection recall; the paper defines
DetA = TP/(TP+FN+FP), so false positives never touched it. And `hota` was a
single α = 0.5 slice, not the mean over 19 thresholds (0.05–0.95). I also found
our MOTA matcher re-solved Hungarian from scratch each frame, which can invent
identity switches between near-tied assignments; the CLEAR-MOT procedure
carries valid matches forward first.
**R.** Fixed all three, kept `hota_at_05` for continuity, added the worked
example as a test. The MOT20 subset HOTA moved **0.545 → 0.434** (0.443 after TrackEval parity, M1); the worked
example's DetA 0.833 → 0.714.

- **Metric:** HOTA 0.545 → 0.434 (→ 0.443 at TrackEval parity) on MOT20-01/02 subset (`docs/13_BASELINES.md`
  rows "old"/"new"); MOTA barely moved (0.463 → 0.466).
- **Lesson:** a self-consistent metric implementation can be consistently
  wrong. Test metrics against a hand derivation from the paper, not against
  themselves.
- **Follow-up:** *"How do you know it's right now?"* — Three kinds of check:
  the paper's own derivation reproduced as a test; property tests (dropping 10 %
  of boxes costs exactly 0.10 MOTA; HOTA lies between DetA and AssA —
  `docs/11_IMPLEMENTATION_STATUS.md`); and 8 tests on real MOT20 footage where a
  perfect tracker must score 1.0. The honest residual: I have not diffed against
  TrackEval on the full set, and I would say so.

---

## 3. The stuck-agent audit: 35 % → 0 %

**Sources:** `docs/11_IMPLEMENTATION_STATUS.md` §"Motion audit"; commit
`e5af8cd`; `tests/test_motion_audit.py`.

**S.** Rendered crowd videos *looked* busy, but ground truth labelled people
`normal.transit` who were not moving.
**T.** Quantify it and fix the Director, because a "walking" label on a
standing person is poisoned ground truth for any loiter detector.
**A.** I wrote `survsim audit-motion`, which measures speed from *positions*,
not recorded velocity, and classifies stuck episodes by cause. It found three:
every walker sent to the same goal coordinate with a 0.5 m arrival radius, so
repulsion let only one arrive (congestion); agents lingering on the exit after
their plan ended; and everyone spawned at t = 0 on two points (median nearest
neighbour 6 mm). Fixes: per-person goals sampled inside zones, stall detection
with re-planning, keep-right yielding, departure at exits, and Poisson arrivals
with a 30 s simulated warm-up before frame 0.
**R.** street_crowd stuck fraction **34.6 % → 0.0 %**; disguise_and_tamper
**49.1 % → 0.0 %**; walking-speed median unchanged (1.08 → 1.10 m/s).
A regression test pins stuck < 2 %.

- **Metric:** 34.6 % / 49.1 % → 0.0 %; t=0 co-location 100 % → 0 %.
- **Lesson:** principle 1 in `CLAUDE.md` — truth is what happened, not what was
  planned. The label came from the plan; the audit read what happened.
- **Follow-up:** *"Did fixing it break anything downstream?"* — Yes, knowingly:
  tracks no longer start at frame 0 and end at N, so the renderer must spawn and
  hide actors at those bounds. I documented it as a caveat rather than hide it.

---

## 4. The editor out-of-memory crash and the VRAM guard

**Sources:** `docs/12_UNREALCV_ENGINE_NOTES.md` (VRAM/speed paragraph, ~l.874);
commits `d57db8c`, `35a2105`; `CLAUDE.md` (8 GB RTX 2070 Max-Q).

**S.** We render on an 8 GB laptop GPU; the plan had assumed 24 GB. With
MetaHuman textures on, Movie Render Queue ran out of memory in `FGPUSkinCache`
and the editor died mid-batch.
**T.** Make batch rendering survivable on the hardware we actually have, and
make failure loud rather than silent.
**A.** Two halves. Reduce: disable skin cache (`r.SkinCache.Mode 0`), cap the
texture pool at 1000 MB, bias skeletal LOD by one, free the previous set and
garbage-collect before each rebuild, meter exposure at 640×360. Guard: the job
runner records `vram_peak_mb` in every result and fails a job above 7 200 MB or
on any "Failed to allocate Device Memory" log line; its heartbeat runs on a
thread, so a hung game thread is not mistaken for a dead editor.
**R.** Peak during batch_v4 was **3.4 GB**, and later batches stayed under
4 GB; 18 MetaHumans × 300 frames × 3 cameras render as fast as the placeholder
mannequin. No people cap needed.

- **Metric:** OOM crash → peak 3.4 GB; guard threshold 7 200 MB.
- **Lesson:** a resource ceiling you do not measure is a crash you schedule.
  Put the measurement in every result record.
- **Follow-up:** *"Why 7 200 MB?"* — Headroom under 8 GB for the driver and
  desktop **[INF]**; the value is a policy, and the point is that it is logged
  per job so drift is visible.

---

## 5. Synthetic-only fine-tuning hurt real AP

**Sources:** `docs/research/32_EXPERIMENTS_LOG.md` §H1 (commit `5e5f53d`),
§H2 (`d0d00ac`), §H6 (`4eac637`).

**S.** The pitch for a simulator is that its data improves real detectors. We
had 1 258 labelled synthetic frames from eight rendered runs.
**T.** Test it honestly on real footage (MOT20-02), with a zero-shot baseline
and a small real-data control.
**A.** I fine-tuned COCO-pretrained YOLOv8n in four arms (zero-shot,
synthetic-only, 60 real MOT20-01 frames ×5 repeats only, synthetic + real),
three training seeds, scored on MOT20-02 at 640, AP by person-height band.
**R.** Synthetic-only **lowered** real AP from 0.276 (zero-shot) to
0.152 ± 0.025 (3 seeds). Sixty real frames reached 0.491 ± 0.003; adding
synthetic to real gave 0.472 ± 0.005 — a small, seed-consistent loss. The
damage concentrated on mid-size people: AP50 at 80–120 px fell 0.073 → 0.007
(seed 0). Follow-ups (H2, H6) found three partial causes: loose GT box tops
(+7 % of height), backbone drift (freezing it gives 0.221) and pixel
statistics (degrading the renders doubles AP, 0.093 → 0.188, still below
zero-shot).

- **Metric:** real AP 0.276 → 0.152 ± 0.025 (synthetic-only, 3 seeds) vs
  0.491 ± 0.003 (60 real frames); synthetic + real 0.472 ± 0.005. Caveat to
  volunteer: MOT20-01 and -02 are very likely the same site.
- **Lesson:** negative results are results. The literature says synthetic helps
  when it is diverse; ours was 1 258 frames from a handful of scenes, and the
  honest statement is "not yet, and here is why I think so" **[INF]**.
- **Follow-up:** *"So is the simulator useless?"* — For *training a detector*
  at this scale, currently yes, and I would not claim otherwise. Its stronger
  value is ground truth real CCTV cannot give — timing of acts, identity across
  disguise, observed-vs-occurred — for evaluating alarm pipelines.

---

## 6. The loiter rule redesign

**Sources:** commit `1a5322b`; `docs/13_BASELINES.md`;
`docs/research/32_EXPERIMENTS_LOG.md` §H5 (`5e5f53d`).

**S.** Our baseline loiter detector was a vendor-style `DwellRule`: flag anyone
slow inside a watched zone for 60 s.
**T.** Find out why it missed the scripted loiterer in disguise_and_tamper.
**A.** Two causes. A pacing loiterer's instantaneous speed exceeded the rule's
speed cap, so dwell never accumulated; and the pacing drifted outside the
nominal gate polygon. Separately I found that overlapping zones resolved
first-match-in-config-order, so a worker inside a restricted substation was
reported in the enclosing yard and lost his role exemption. I wrote
`PathLoiterRule`: dwell keyed on the 90th-percentile displacement from a
trailing centroid, a re-entry tolerance, its own smallest-containing-zone
lookup, and role exemptions honoured.
**R.** On seed 11, `DwellRule(60 s)` recall **0/2**, `PathLoiterRule(25 s)`
**2/2**, and it never fired on the worker.

- **Metric:** recall 0/2 → 2/2. The honest sequel (h5): across three worlds at
  30 s tolerance `PathLoiterRule(25 s)` reaches 0.8 recall at **51.43 false
  alarms per camera-hour** (default scoring; 28.57 i-LIDS-compatible) — every
  rule that finds loiterers is 10⁴–10⁵× over our assumed 0.001 FA/cam-h budget, with
  perfect perception, on 5 truth events / 0.35 camera-hours.
- **Lesson:** fixing recall exposes the precision problem; report both.
- **Follow-up:** *"51 FA/camera-hour is unusable — why tell me?"* — Because it
  is the true number, and it motivates story 7: the fix is architecture, not a
  cleverer rule.

---

## 7. Making a 7 %-precision detector deployable

**Sources:** commit `38a8cb4`; `docs/14_FIRST_RESULTS.md`.

**S.** A trajectory classifier we trained produced 93 % false alarms — a
base-rate effect that no model improvement would fix.
**T.** Test the research corpus's claim that the answer is pipeline
architecture.
**A.** I built the alarm funnel as explicit stages, each counting what it
dropped and why: confidence threshold, zone and after-hours context,
persistence across windows, cross-sensor corroboration, deduplication, and a
hard operator-capacity cap applied last.
**R.** On the same classifier and data: raw 114 alarms, precision 0.026,
27.75 FA/camera-hour; after threshold, persistence and corroboration, 2
alarms, precision 0.50, 0.25 FA/camera-hour. **19× precision, 111× fewer false
alarms** without touching the model, versus 4× from replacing the dwell rule
with a learned one. Recall fell 0.50 → 0.17, and I reported that as a customer
decision, not a footnote.

- **Metric:** FA/cam-hr 27.75 → 0.25; recall 0.50 → 0.17.
- **Lesson:** where effort belongs is a measurable question.
- **Follow-up:** *"Isn't corroboration assuming independent nuisances?"* — Yes,
  and the commit says so: `eval/fusion.py` shows nuisances are often correlated
  on real sites (wind moves the fence *and* the tree), so 0.25 is an optimistic
  bound.

---

## 8. Scene-generator variety, gated

**Sources:** commits `3f72ac9`, `d2f91d9`, `19d2df4`, `af55515`;
`docs/12_UNREALCV_ENGINE_NOTES.md` §"Environment variety", §"Automated render
gate".

**S.** Early renders looked like one grey plaza with different camera angles —
useless for a detector that must generalise across sites.
**T.** Generate genuinely different sites and prove each frame is usable
before anyone trains on it.
**A.** Scene generator v2 builds real layouts per site type — forecourt,
warehouse yard, retail, transit and so on — with roads, kerbs, crossings,
parking, gates, decals, a solar sun and weather, plus an installer-style camera
rig. Every frame goes through an automated render gate (`scripts/check_render.py`)
and an in-editor frustum gate that checks object footprints, not centre
points, are in view. Early batches had encoded *failed* sets into videos; I
made the gate blocking.
**R.** 18/18 variety frames pass after fixing container spacing, decals on
solids, asset paint and metering (commit `19d2df4`); 0 gate failures across 6
site types; batch_v3 6/6 sets, 5 400 frames.

- **Metric:** 18/18 gated; 6/6 site types; per-camera core-coverage test.
- **Lesson:** "variety" must be a test, not a screenshot you like.
- **Follow-up:** *"Does visual variety close the sim-to-real gap?"* — Story 5
  says not by itself; variety is necessary, not sufficient.

---

## 9. The MOT20 licence realisation

**Sources:** `docs/research/23_ROADMAP_AND_GAP_ANALYSIS.md` (risk table);
`docs/research/32_EXPERIMENTS_LOG.md` header; `docs/research/40_MOCK_INTERVIEW.md`
§C6; `docs/research/FACTS_VERIFIED.md`.

**S.** MOT20 was our real-footage reference for every baseline, and the
obvious next move was to fine-tune on it.
**T.** Before building a product story on it, check what we were allowed to do.
**A.** I read the dataset terms: MOT17/MOT20 are CC BY-NC-SA 3.0 —
non-commercial. So are Stanford Drone and UR Fall, which the roadmap also
leaned on; AMASS motion is research-only. I recorded this in the roadmap's risk
table (high likelihood, high impact), marked MOT20 "evaluation only" at the top
of the experiments log, and planned licensed or customer-consented real data as
a budget line.
**R.** Every MOT20 number in the repo is labelled a research reference, not
product training data; the "real frames" arm in story 5 is explicitly a
research control.

- **Metric:** three datasets reclassified non-commercial; one budget line added.
- **Lesson:** licences are requirements. Read them before the architecture
  depends on them.
- **Follow-up:** *"You still trained on it."* — For a research comparison,
  within the licence. A shipped model would not be; this is also where synthetic
  data earns its keep — it is data we own **[INF]**.

---

## 10. "Alive" has three meanings: the hung engine

**Sources:** `docs/12_UNREALCV_ENGINE_NOTES.md` §2 "The build now hangs at
frame 1"; `scripts/engine.sh`; `CLAUDE.md`.

**S.** The packaged UnrealZoo runtime ran fine for about 7 h, then every start
stopped at frame 1. Our health checks said it was up.
**T.** Establish whether it was really alive and stop losing hours to false
"healthy" signals.
**A.** Five clean restarts, one left 40 minutes to rule out shader
compilation. The process was busy — 150 % CPU, 4.6 GB VRAM — but never reached
frame 2. The key finding was that our three checks meant different things: a
listening port proves a socket is bound; a handshake proves the *network*
thread lives; only a command returning proves the *game* thread executes.
UnrealCV answers handshakes off the game thread, so a hung engine passed two of
three checks.
**R.** `scripts/engine.sh` encodes the distinction and is the only sanctioned
way to start/stop; the table is in the engine notes. Cause still not
established — and I say that.

- **Metric:** 5/5 restarts hung at frame 1; hours lost to false-positive health.
- **Lesson:** a health check must exercise the path you depend on.
- **Follow-up:** *"How would you monitor 40 cameras' analytics the same way?"*
  — End-to-end canaries: a known event must produce a known alarm, not just a
  heartbeat **[INF]**.

---

## 11. The performance diagnosis that was never measured

**Sources:** commit `ef74a24`; `docs/13_BASELINES.md` §"What was actually
slow, corrected".

**S.** A full MOT20 baseline run was killed after 2.5 h with no output. The
commit blamed O(n²) association in our numpy ByteTrack on crowds of 100+.
**T.** Later I needed the full-set numbers and had to decide whether to rewrite
the tracker.
**A.** Before rewriting, I profiled. Tracker plus evaluator over all 8 931
frames took **62 s** combined. The diagnosis had been assumed, never measured;
I wrote in the doc that it was wrong. By elimination, the time was in COCO mAP
or, more likely, the ReID stage decoding full-resolution JPEGs per crop
[the doc's own inference]. I still landed small verified wins — a ~14 % cut in
the Kalman inner loop — checked bit-identical (MOT20-01 MOTA 0.4223 unchanged).
**R.** Avoided a needless rewrite; the next step is to time ReID and cache
crops.

- **Metric:** 62 s for tracking + eval versus 1 h 26 min for the whole job.
- **Lesson:** profile before optimising; write down when a past diagnosis was
  wrong, in the same file.
- **Follow-up:** *"Why not just profile the whole thing?"* — I should have; I
  profiled the suspected half first. Honest answer.

---

## 12. When a colour histogram beats a ReID network

**Sources:** `docs/research/32_EXPERIMENTS_LOG.md` §H4 (commit `5e5f53d`).

**S.** We wanted to show our renders support person re-identification research.
**T.** Measure an ImageNet OSNet on our people across camera, time and lighting
— and include a trivial baseline.
**A.** 610 crops, 20 identities, 8 camera views. I added an HSV colour
histogram as a control, which most demos would skip.
**R.** The histogram beat OSNet cross-camera (rank-1 0.291 vs 0.251, mAP 0.219
vs 0.148) and cross-time (rank-1 0.584 vs 0.512). OSNet won only day↔night
(rank-1 0.444 vs 0.245, ≥5 s apart). An earlier protocol that allowed
same-frame day/night pairs gave OSNet 0.869 — a leak, and I caught and
discarded it. On these renders identity is mostly clothing colour — too easy,
and not like real ReID (same OSNet on real MOT20 cross-time: 0.186).

- **Metric:** histogram mAP 0.219 vs OSNet 0.148 cross-camera.
- **Lesson:** always run the dumb baseline; it tells you whether the benchmark
  measures what you think.
- **Follow-up:** *"What would you change?"* — More outfits per identity and
  shared colours across identities, so colour stops being a shortcut; that is
  what appearance epochs (clothing change mid-run) are for **[INF]**.

---

## 13. Paying for a licence-clean cast

**Sources:** commits `9c87424`, `8c3b03b`; `docs/12_UNREALCV_ENGINE_NOTES.md`
§"batch_v7"; `docs/research/47_CHARACTER_AND_ASSET_LICENSING.md`.

**S.** Our renders used MetaHumans, whose licence page says you may not use
MetaHuman characters or animation curves to "train or test" AI/ML (47 §0;
the trailing rendered-output sentence is ambiguous, but the operative "train or
test" sentence does not depend on it). Consequence: batch_v4–v6, and so the
H1–H6 experiments, are internal engineering evidence only.
**T.** Replace the cast with assets we may use commercially and measure what it
costs.
**A.** Made a CC0 stack the render default: 16 verified Quaternius bodies on
their own animation clips with region-painted clothing, and wrote
`asset_licences` and `commercial_ml_ok` into ground truth. Re-rendered the same
8 sets, frames and cameras as batch_v6 (batch_v7).
**R.** Every set `commercial_ml_ok: true`. YOLOv8n recall 0.652 vs 0.665 for
MetaHuman (−0.013; precision 0.814 vs 0.823), cost concentrated in 20–60 px
people; the hand-keyed clips still foot-slide 8.5–9.8 cm/s.

- **Metric:** −0.013 recall for a licence-clean dataset.
- **Lesson:** make compliance a field in the data, not a note in a wiki.
- **Follow-up:** *"Is −0.013 significant?"* — One detector, 10 frames/camera,
  1 070 GT; I would call it "small, not zero" and not claim more.

---

## 14. Tighter labels, no better detector

**Sources:** commits `0213002`, `68ee6d1`; `docs/11_IMPLEMENTATION_STATUS.md`
l.190–204; `32` §H6(c).

**S.** H6 blamed part of the synthetic-hurts-real result (story 5) on loose box
tops: our GT boxes were projected from an upright 3-D envelope at the
Director's height, ~7 % of height looser than a detector's.
**T.** Make the boxes describe what was rendered, then see if the loss goes away.
**A.** I gave every person a CustomDepth stencil ID, rendered a second ID-mask
pass, and derived occlusion-truncated boxes from the pixels, with a gate
(median IoU vs zero-shot YOLOv8n ≥ 0.75, |top offset| ≤ 3 %). Then I re-ran the
fine-tune, loose vs tight, 2 seeds, MOT20-02.
**R.** Label fit fixed: 0.781 → 0.884 (smoke), 0.712 → 0.911 (street) — tighter
than MOT20's own hand labels (0.797). Transfer did **not** improve: loose
0.290 ± 0.024, tight 0.266 ± 0.004. MOT20's boxes are amodal; the detector's
are 13.5 % narrower than them. "Tight" is not "MOT20-like".

- **Metric:** IoU 0.781 → 0.884 / 0.712 → 0.911; AP 0.290 vs 0.266.
- **Lesson:** "truth is what happened" fixes *our* labels, but the target
  benchmark has its own labelling convention; accuracy to pixels and match to
  the evaluation protocol are different properties. Reported as a negative.
- **Follow-up:** *"So was the fix wasted?"* — No: every downstream metric on our
  own renders (tracking, coverage) now uses boxes that include occlusion. It
  just removed one hypothesis for the transfer gap, which is what an experiment
  is for. Next lever is an amodal-box variant, not more tightness.

---

## 15. Everyone was 1.70 m tall

**Sources:** commit `92e1e97`; `0213002` message; `survsim/checks/render.py`;
`tests/test_checks_render.py`.

**S.** The Director gives each person a height; the Unreal manifest builds each
rendered body. While writing the tight-GT commit I noticed the manifest "pins
every person at 1.70 m".
**T.** Find why, and make it impossible to recur silently.
**A.** `build_manifest()` read `ident.get("wardrobe", default)`, but
`identities.parquet` never has a `wardrobe` field — appearance is the `outfit`
JSON column and `height_m` a flat column. The `.get` default always won, no
error, no log. I derived the wardrobe from the identities row, made GT
`height_m` override any supplied wardrobe, and added
`check_rendered_height_matches_gt` (> 2 cm mismatch fails).
**R.** Rendered height now equals GT height; tests cover a height sweep, NaN
fallback and the "everyone 1.70 m" failure mode directly.

- **Metric:** 100 % of rendered people at the 1.70 m default before `92e1e97`.
- **Lesson:** a silent default is a lie in the ground truth: the GT could say 1.85 m,
  the pixels showed 1.70 m, and nothing disagreed loudly. Truth has to be
  checked against what was rendered, not what was requested.
- **Follow-up:** *"What did it contaminate?"* — Every render before `92e1e97`:
  height-based soft biometrics and the projected boxes (part of H6's loose
  tops). Mask-derived boxes are immune because they read the pixels [INF].
  Since `208cfc5` the check runs in the render gate, and it **fails both
  tightgt sets** (rendered at 1.70 m vs GT 1.22–1.89 m; worst +47.6 cm) — so
  batch_v8 was re-rendered rather than trusting `height_m` on them (story 17).

---

## 16. Alarm budget at scale: 87,000× over, a learned rule, and a leak that shrank its margin

**Sources:** `32` §H12 (pre-registered `98b7c03`, results `9dea4f9`);
`out/experiments/h12_alarm_scale/results.json`, `worlds.jsonl`; earlier H5
(`5e5f53d`); redesign `58` §6 round 2 (`44e34f5`, after the `473ace3`
centroid fix), `out/experiments/h58_round2/round2_results.json`.

**S.** H5 had said our loiter rules were 10⁴–10⁵× over our assumed 0.001 FA/camera-hour
budget — on **0.35 camera-hours** and 5 loiter events. An interviewer's first
question would be "isn't that noise?", and the honest answer was "partly".
**T.** Measure the false-alarm rate at a volume where sampling error is gone,
pre-register what I expected, and find *which* innocent behaviour causes it.
**A.** Generated 676 clean mock worlds across all six site types — 3,002
camera-hours, 74,989 innocent people (commute waits, queues, phone stops,
smoke breaks, transit), **zero** loiterers, perfect tracks — and ran four
rules under default and i-LIDS-compatible scoring (99 min on 11 CPU workers).
Reported Garwood Poisson CIs *and* a world-cluster bootstrap, and a separate
300-world recall set with 360 loiter events. Attributed every alarm to the
archetype that caused it.
**R.** Every rule over budget with CIs of ±1–2 %: dwell_60 **4.55**, dwell_25
**6.01**, path_loiter_25 **20.7**, path_loiter_15 **87.4** FA/cam-h —
**4,500× to 87,000×** over our assumed 0.001. The pre-registration was half wrong: I
expected dwell archetypes to dominate, but path_loiter_15's biggest cause was
**ordinary transit (54 %)**. Its dwell clock only resets after a 15 s re-entry
gap, equal to its 15 s threshold, so *every walker* reaches the threshold — a
parameter-interaction bug that H5's 0.35 hours reported as "142 FA/cam-h"
without showing why. i-LIDS coalescing cut 7–59 % and left recall unchanged;
dwell_60 is quietest, and window-only scoring credited dwell_25 with 0.90
recall and dwell_60 with 0.16.

**Round 2 (doc 58).** I then trained a `LearnedLoiterRule` on track features
and found a leak: every loiterer dwelled at the *exact* zone centroid. Fixed
in the Director (`473ace3`), pre-registered that the margin over dwell_25
(2.06× in round 1) would shrink and that under 1.5× I would re-examine
shipping, regenerated, retrained, and rescored **actor-aware** (an alarm only
counts if it is on the loiterer, not anyone in the event window). Result: the
round-2 learned rule (since superseded by round-3 A1 2.915 / 0.825) **3.745 FA/cam-h [3.676, 3.815]**, recall **0.831 [0.792, 0.869]**,
precision 0.326 — margin shrank **2.06× → 1.60×** but held. The bigger
surprise was the baseline: dwell_25's 0.90 was mostly **alarms on
bystanders**; actor-aware it is **0.367**, and dwell_60 is **0.000**. The
label oracle reaches 1.000; the motion-only kinematic-twin floor is 1.008
FA/cam-h. Verdict: ship the learned rule, score actor-aware — and it is still
~3,700× over our assumed 0.001, about 1.25 operators of pure false-alarm work at 40
cameras and 30 s per check.

**Epilogue — round 3 (doc 58 §7, `bcbe9d2`).** Round 2 had left a loose end:
the *frozen round-1 weights*, re-scored on the fixed worlds, beat the refit
(2.915 vs 3.745 FA/cam-h). I did not swap post hoc. I pre-registered round 3
(`cec3317`) with an arm-decision rule, a GBM, a calibrated GBM and a
zone-context ablation, then ran it once. The decision rule shipped **A1, the
round-1 weights: 2.915 FA/cam-h [2.854, 2.977], actor-aware recall 0.825
[0.789, 0.862]**. The GBM (3.114 at 0.842) was not a clear win. Zone-function
context cut false alarms **~21 %** (2.468 vs 3.114), short of the 25 % I had
predicted, and a real site would have to supply that zone profile. I also
logged an erratum against my own pre-registration (it said A1's clock was
≥ 10 s; the frozen spec is ≥ 5 s). Still ~2,900× over our assumed budget, about 0.97
operators of dismissals at 40 cameras.

- **Metric:** 87.4 FA/cam-h = 87,440× our assumed budget (Garwood lower bound 87,106×);
  3,002 camera-hours; world-cluster CI ~3× Garwood.
- **Design change:** the reset gap must be shorter than the threshold (or the
  clock must reset on sustained displacement), and no single-cue threshold can
  close a 3.6–4.9 order-of-magnitude gap — the next stage has to be context
  and corroboration (zone tagging already does DwellRule's filtering), scored
  at a fixed recall.
- **Round-2 metric (superseded by round-3 A1 2.915):** 3.745 vs 6.007 FA/cam-h (1.60× fewer, was 2.06×);
  actor-aware recall 0.831 vs 0.367 (2.3×), precision 4×; recall@10 s only
  0.097.
- **Round-3 metric (shipped):** A1 2.915 vs 6.007 FA/cam-h (2.06× fewer),
  actor-aware recall 0.825 vs 0.367, recall@10 s 0.242; zone context −20.7 %.
- **Lesson:** a small soak tells you *that* you are over budget; only volume
  tells you *why*, and the why is what changes the design. And a scorer that
  matches alarms to event *windows* rather than *people* credits a rule for
  firing on bystanders — dwell_25 lost 60 % of its recall to that one fix.
- **Follow-up:** *"Are 87 alarms an hour real?"* — Absolute rates depend on
  my mock archetype mix (55 % transit), which is not validated against real
  dwell distributions; the ordering and the transit mechanism are properties
  of the rules. False alarms cluster by world (bootstrap ~3× wider), which is
  why staffing should be sized on bursts, not means (51 §3.1b).

---

## 17. batch_v8: every label true to the pixels

**Sources:** `docs/12` §"batch_v8" (`94145fa`); decoder `1fd38df`;
`out/demo_humans_v2/recall_v8_vs_v7.json`; `out/batch_v8/*/check_render.txt`.

**S.** Stories 14 and 15 left our labels with three known lies: heights (the
v7 tightgt sets FAILed the height gate by up to 47.6 cm), loose projected
boxes, and no amodal box to match MOT20's convention.
**T.** Re-render a batch where every label is checked against the pixels, and
make each check a gate, not a report.
**A.** Read GT `height_m` unclamped into the mesh scale; added a height gate
and a box-tightness gate to every set; wrote visible (mask), amodal and
visibility labels per box; rendered appearance epochs. The mask decoder took
~17 min per camera, so I rewrote it (colour LUT, one nonzero pass): 33 s per
4-camera set, byte-identical output.
**R.** 9/9 sets gate-clean: 0 people beyond 2 cm, tightness IoU 0.876–0.932,
amodal holdout IoU 0.879–0.914, 12.5–19.4 % of person-frames < 0.8 visible.
Same characters, recall 0.664 → 0.696 — from labels alone.

- **Metric:** gate 9/9; height 0 beyond 2 cm; recall 0.696 / P 0.879 vs v7
  0.664 / 0.819; decode ~70 min → 33 s per set.
- **Lesson:** a label you have not checked against the render is a claim, not
  ground truth; and "byte-identical" is the bar for a speed-up of a GT writer.
- **Follow-up:** *"Is amodal better?"* — Not for scoring near people: amodal
  GT recall at 120+ px is 0.854 vs 0.991 visible, because near people are cut
  off by the frame edge or occluded and a detector boxes what it sees. Whether
  amodal *training* labels transfer better to MOT20 was H15: no effect,
  −0.0005 [−0.0012, +0.0001] (`b6c735e`). Recall noise is ~±0.03 per set (10 frames/camera).

---

## 18. The night profile that overfit (H32)

**Sources:** 32 §H32a/H32b (`1acb9bd`); AUDIT_H32; FACTS H32 rows.
**Competency:** scientific integrity — honouring a pre-registration when the result is bad.

**S.** Night degrade profiles were our weakest realism claim; we had only day-target band counts.
**T.** Pre-register a night test against real LLVIP frames: tune on the first 15 frames per modality, score on the last 10, 13 bands each.
**A.** I tuned `cctv_night_lowlight` and `cctv_thermal`, then ran the held-out split exactly as written. Low-light went **9/13 tune → 2/13 held-out**; thermal 10/13 → 3/13. Both overfit. I could have re-tuned on all 25 frames and reported the tune count; that would have measured my fitting, not the profile. The pre-registration said recall would only be read as a night penalty if a profile landed in band, so I took branch B3: recall is reported (raw 0.938, low-light 0.103) but explicitly *not* as a night-penalty estimate.
**R.** Verdict "not met"; P1 refuted, P2 held; the audit added that thermal recall is optimistic because people are painted hot from the GT mask.

- **Follow-up:** *"Why not just use all 25 frames?"* — Because then no number measures generalisation. The fix is more frames and a new registration, not a new split after seeing results.

---

## 19. Auto-calibration off by two orders of magnitude (H39)

**Sources:** 32 §H39; 75; AUDIT_75_H39; FACTS H39 rows.
**Competency:** debugging ownership and honest labelling of post-hoc work.

**S.** Known-height auto-calibration was meant to put 40 fixed cameras on a ground plane without a survey.
**T.** The pre-registered bar was ≤ 0.5 m world error at < 20 m on batch_v8.
**A.** The first fit drove f to the 5,120 px bound on every camera. I inspected rather than tuned: it also used the u residual of the box top, which measures box geometry (an axis-aligned box's top-centre has the foot's u), not the head. I switched to the v-only residual and wrote `test_axis_aligned_box_heads_do_not_bias_fit`, mutation-checked: re-inserting the u residual drives f to 5,120 on the test scene (fixed code: 800.0). The fixed, registered fit still gave **57.4 m** RMSE [46.2, 68.0] — two orders of magnitude over the bar, with 5/10 cameras at or near the f bound. The rest is the method: height spread and a narrow row band. A datasheet-f arm gave 0.96 m — but I added it after seeing the failure.
**R.** H39 is reported **not met**; the datasheet arm is labelled post hoc everywhere. Height MAE looked fine on the broken fit (0.077 m): a trap metric.

- **Follow-up:** *"So can you calibrate a site?"* — Not from this: I would use survey points or datasheet f as a new pre-registered test.

---

## 20. A 16.9× false-alarm cut that killed recall (H40)

**Sources:** 32 §H40 (`02b51ae`); 76; AUDIT_76_H40; 23 M8 row (D37).
**Competency:** product judgement — fixing the cause, not the metric.

**S.** Sterile-zone line-cross is a core perimeter analytic; naive rule 70.96 FA/cam-h over 3,002 simulated cam-h.
**T.** Pre-registered: cut false alarms without losing the 0.9 recall bar.
**A.** Layered gating (age/height, direction, 1.5 m depth, 5 s dwell, gate context) took FA to **4.20** — a **16.9× [15.3, 18.6]** cut. But actor-aware recall fell from 0.945 to **0.100**. Before blaming the rule, I looked at the intruders: re-derived from tracks, only 6/100 went ≥ 1.5 m deep within 10 s of entry. The mock generator's intruders stopped at the zone edge, so the depth gate was measuring our simulator. Relaxing the gate would have "passed" on unrealistic data; I opened D37 to fix the behaviour engine instead (intruder arc that crosses the zone, patrol-guard twin, climb arc, animal agent) with H40b to re-test.
**R.** H40 reported **not met**, FA flagged optimistic (assumed noise model, no patrol/animal/weather twins).

- **Follow-up:** *"Would you ship it?"* — Not on these numbers; H40b on corrected intruders decides.

---

## 21. Five defects in our own HOTA scorer (M1)

**Sources:** `docs/13_BASELINES.md` §TrackEval parity; `tests/test_trackeval_parity.py`; AUDIT_M1_PARITY.
**Competency:** rigour and follow-through — correcting a number I had already published.

**S.** Story 2 left one honest residual: our evaluator had never been diffed against TrackEval.
**T.** Reach exact parity or explain every difference.
**A.** I ran both on the MOT20 subset, batch_v8 with perturbed GT and three edge cases. MOT20 disagreed (Δ HOTA −0.0086, IDSW −9), and I traced five defects: per-α Hungarian instead of one association-aware match; DetA/AssA taken from CLEAR matching; IDF1 from CLEAR matches instead of all IoU ≥ 0.5 pairs; CLEAR continuity across gaps; and 1e-9 instead of machine-eps thresholds. After fixes, |Δ| ≤ 1e-15 on every metric. I noted batch_v8 and the edge cases did not discriminate old from new — only MOT20 did.
**R.** Headline HOTA **0.434 → 0.443**; I retired the old value everywhere (registry row R41) and flagged every downstream delta computed pre-parity.

- **Follow-up:** *"Why not just use TrackEval?"* — We keep the parity test instead: it runs in CI and guards our faster in-process scorer.

---

## 22. From "recall 0.825" to a ranked review queue (H22/H33)

**Sources:** 32 §H22 (`57ffff6`), §H33 (`93cc3b1`); AUDIT_H22_H33; FACTS H22/H33 rows.
**Competency:** customer/operational thinking — reframing a model metric into a product decision.

**S.** Our loiter rule A1 had model recall 0.825 at 2.915 FA/cam-h — a number a customer would never experience.
**T.** Estimate what an operator actually catches, and certify a threshold per site.
**A.** H22 simulated one operator on 40 cameras (10 seeds, an invented but stated operator model). FIFO realised recall within 5 min was **0.511** [0.484, 0.537] — inconclusive against the 0.495 bar — with a quarter of alarms bulk-acked. Ranking the queue added **+0.262** at 30 s (10/10 seeds). H33 replaced a plug-in threshold with conformal risk control: at α = 2.915 it exceeded budget in **0/10** splits vs 6/10, costing −0.035 recall; α = 0.001 is uncertifiable.
**R.** The product shape changed: a ranked review queue with a per-site conformal threshold, not a detector with a score. Caveat said upfront: 338 simulated worlds, not real sites.

- **Follow-up:** *"Where do the operator parameters come from?"* — Invented; the first real deployment should log review times to replace them.

---

## 23. Retired numbers kept coming back: a registry that fails the build

**Sources:** RETIRED_CLAIMS.md; `tests/test_docs_retired_claims.py`; AUDIT_STALENESS_SWEEP.
**Competency:** process improvement — turning a recurring human error into an automated check.

**S.** Audits kept correcting numbers, and the corrections kept not sticking.
**T.** Stop corrected numbers resurfacing across ~80 research docs.
**A.** The staleness sweep found the retired "3/14 night" realism figure in **39** places, 17 still stated as current. Fixing by hand had already failed once. I built a registry: one row per retired claim — regex, correct form, which audit retired it, and an exemption only for lines that carry a retirement marker ("pre-fix", "retired") or the correct value — a bare "was" no longer exempts (AUDIT_79). A test scans every doc and `CLAUDE.md` and fails on any unexempted hit. It now has 57 rows (R01–R57), including the HOTA values from stories 2 and 21.
**R.** A retired number can only appear as the "before" of a stated correction; this very section was checked by it.

- **Follow-up:** *"Isn't regex brittle?"* — Yes, both ways; the exemption rule is deliberately narrow and false positives are fixed by rewording, which usually improves the sentence.

---

## 24. The headline number I had to retract (H26, H51)

**Sources:** `32` §H26, §H51; AUDIT_H26; AUDIT_H51; RETIRED_CLAIMS R51; `52` §5b.
**Competency:** integrity — testing your own best result and changing the story.

**S.** My best sim-to-real result was h14b: renders added to 60 real frames beat real-only, 5 seeds, Holm-significant. It was in the pitch.
**T.** Before leaning on it, find out whether it was synthetic data or something else.
**A.** I noticed the mix arms ran more optimiser steps than real-only (~228 vs 300–450). So I pre-registered H26, which fixes every arm at 450 steps and varies only the dose, from 0 to 1,000 frames.
**R.** Real-only alone gains +0.0049 from H26's longer recipe (steps, warm-up and mosaic changed together, AUDIT_H51). At 5 seeds H26 found +0.004–0.005 AP at 100–300 frames that did not clear Holm, so I retracted the headline, added it to the retired-claims registry (R51, story 23), flagged H16/H17 as sharing the confound (R52/R53) and pre-registered H51: the same recipe, ten paired seeds. H51 gave +0.0042 and +0.0051, Holm p 0.0039 both. I retracted a number that mixed in training steps, re-ran it properly, and the honest gain is a third to a half of what I first claimed — and significant; about 1 % relative, one site, one detector. H52/H61 (10 paired seeds each): the gain is labels on people — shuffled boxes erase it (+0.0077 gap), silhouette-masked frames with no box-shaped fill give nothing (−0.002 vs real-only); H52's apparent 'background' gain was the inpainted box fill. Duplicating real frames does nothing (−0.0011). The simulator is an evaluation and stress-test instrument first, a training-data source second.

- **Follow-up:** *"Doesn't that sink the project?"* No. The value that survives is mask-derived ground truth (batch_v8), hard-negative twins (H40b) and measured rule variance (H21/H23/H42), none of which depend on AP.

---

## 25. The security review that broke my evidence log (H60)

**Sources:** `32` §H60 slices 1–2; AUDIT_H60; `39da635`, `f85d479`, `caebe7a`; `87`.
**Competency:** welcoming adversarial review — asking to be attacked, then fixing what it finds.

**S.** I built alarm cards and a hash-chained verdict log (H60 slice 1) and wrote that deleting a record "fails at the gap".
**T.** Before anyone relied on it, have a hostile reviewer attack it as a security engineer would.
**A.** The review (AUDIT_H60, 7/10) found the verifier passed tail truncation and a full re-chain, accepted a re-hashed reason-less dismiss, and the GT leak guard's value list missed zone names; the operator-id salt was a public default. For each defect I wrote the failing test first, then the fix: `expected_head`, dismiss-needs-reason at verify, zone names in `gt_values`, NaN refused (tests 13 → 17). Slice 2, pre-registered, added a per-site salt file (`*.salt` git-ignored) and `head.json` with fail-closed verify (22 tests).
**R.** Truncation and re-chain now fail against the head; real-mode leak 0 across 9 654 carded H22 alarms. I also corrected my own wording: the log is tamper-evident only against an off-box copy of the head.

- **Follow-up:** *"Is it secure now?"* It is reviewed against the attacks we listed. The head is still unsigned and untimestamped.

---

## 26. The INT8 chain: knowing when to stop chasing a recipe (H38/H43/H43b/H43c/H43d)

**Sources:** `32` §H38, §H43, §H43b, §H43c, §H43d; AUDIT_H43, AUDIT_H43BC, AUDIT_H43D; FACTS_VERIFIED.md.
**Competency:** knowing when to stop chasing a result, and how to state what was learned.

**S.** INT8 export of our detector (H38) cost 0.0117 AP, mostly AP75 (−0.025..−0.040) — a real edge-deployment problem, not noise.
**T.** Recover enough of that loss to justify INT8's smaller footprint, without pretending a partial recovery is a full one.
**A.** Four pre-registered follow-ups, each testing one explanation, in order. H43: better PTQ calibration (Percentile) reached AP75 recovery 0.415/0.424, short of the 0.50 bar. H43b: QAT recovered only 0.366 — worse than free PTQ — and I first blamed the export path. H43c fixed that: verified the QAT observers' learned ranges carried into export byte-for-byte, found a real Conv-node-order bug, and recovery rose to 0.439, still short. H43d tested my own inference that longer QAT would close the rest — 600 iterations vs 150 — and recovery *fell*, to 0.374, refuting it.
**R.** Four registered arms, none clearing the bar. Conclusion: the loss is INT8 quantisation of this architecture, not the recipe or the export. Ship FP16 (H38 loss 0.0000). One open item, H43e (TensorRT on real Jetson), needs hardware we don't have.

- **Follow-up:** *"Why not try QAT-aware architecture changes instead of tuning the recipe?"* Each of the four arms was cheap and pre-registered; an architecture change is not — it earns its cost only once recipe/export causes are ruled out.

---

## Presenting negative results in an interview

1. **Lead with the verdict word the pre-registration used** ("not met", "inconclusive"). *Defence customers buy against acceptance criteria; a supplier who re-words a failure fails assurance.*
2. **Give the number that failed, then the one that passed.** *An operator budget is breached by the worst number, not the best.*
3. **Say what you did not do** (re-tune on the test split, relax the gate). *Evaluators under JSP 936 need to know the result was not steered.*
4. **Label anything post hoc as post hoc.** *Post-hoc fixes are hypotheses; treating them as results is how untested capability reaches the field.*
5. **End on the next test, not the excuse.** *They care that a gap has a dated plan to close it, because they will be asked the same question by their own customer.*

---

## Suggested mapping to common questions

| Question | Best story | Backup |
|---|---|---|
| Hardest bug | 1 black render | 10 hung engine |
| A time you were wrong | 2 HOTA | 11 performance |
| Negative result / disappointment | 5 synthetic hurt | 14 tight labels |
| Prioritisation / impact | 7 alarm funnel | 6 loiter rule, 16 alarm budget at scale |
| Constraints / resources | 4 VRAM | 11 profiling |
| Data quality | 3 stuck agents | 15 height default, 17 batch_v8 labels, 8 variety gate |
| Ethics / compliance | 9 licence | 13 CC0 cast |
| Operational thinking | 7, 16 | 6, 10 |
| Pre-registration / being wrong in advance | 16 alarm budget (transit, not dwell) | 14 tight labels, 18 night overfit |
| Honest failure / post hoc labelling | 19 auto-calibration | 18 night overfit |
| Fixing the cause, not the metric | 20 line-cross | 17 batch_v8 |
| Correcting a published number | 21 TrackEval parity | 2 HOTA |
| Customer / product shape | 22 ranked queue | 7 alarm funnel |
| Process improvement | 23 retired-claims registry | 8 variety gate |

## Cross-cutting lines to reuse

- "Truth is what happened, not what was planned" (stories 3, 6).
- "A metric that agrees with itself can still be wrong" (2, 12).
- "I report the cost as well as the gain" (6, 7).
- "Tagging: verified, API exists but untried, tried and broken" — the
  [V]/[A]/[X] convention from `CLAUDE.md` came directly out of stories 1 and 10.

## Things not to say

- Do not claim synthetic data improved real accuracy — it did not here (5).
- Do not quote HOTA 0.545; it was the pre-fix value (2).
- Do not attribute the 2.5 h MOT20 run to O(n²) association (11).
- Do not say MetaHuman wardrobe works end-to-end; `CLAUDE.md` marks it [A].

---

## Second-level probes (what comes after the first follow-up)

Interviewers who liked the first answer dig one level further. These are the
second questions I expect, with the answer and where it comes from.

**1 · Black render.** *"How would you stop the next convention mismatch?"* —
Convert once at a single boundary and test the boundary. SurvSim already does
this for units: SI metres and degrees above the backend, with the Unreal
backend doing ×100, negate Y, negate yaw (`CLAUDE.md` principle 7;
`docs/12_UNREALCV_ENGINE_NOTES.md` ~l.400). The Rotator bug happened in
in-editor scripts that bypassed that boundary. The static test forbids the
dangerous call shape rather than checking values, because value tests are what
let the earlier inverted-pitch bug survive (`CLAUDE.md`, "Working style").

**2 · HOTA.** *"Which number would a customer care about — HOTA or MOTA?"* —
Neither directly. A security customer cares about false alarms per
camera-hour against an operator budget and whether the alarm arrived in time
(`CLAUDE.md` principle 4). Tracking metrics are diagnostic: AssA falling tells
you ReID or occlusion handling broke, which predicts missed loiter alarms
**[INF]**. That is why the evaluator reports DetA/AssA separately.

**3 · Stuck agents.** *"Why did nobody notice from the videos?"* — Because a
crowd with a third of people standing still still *looks* like a crowd; the
eye reads density, not per-person velocity **[INF]**. That is the argument for
computing audits from `gt/world.parquet` positions instead of watching output.

**4 · VRAM.** *"What did you give up?"* — Skin cache off and LOD bias +1
cost some deformation and mesh detail. At surveillance standoff (people often
tens of pixels tall) that detail is below what the sensor model preserves
**[INF]**; `CLAUDE.md` already caps capture at 720p for the same reason.

**5 · Synthetic hurt.** *"What was your best hypothesis and how would you
test it?"* — Feature drift: 12 epochs on 1 258 synthetic frames overwrite COCO
backbone features. The test is `h6_freeze.yaml` — same data with backbone
frozen (freeze 10) or only the Detect head trained (freeze 22). Result
(32 §H6, `4eac637`): freeze10 0.221 ± 0.008 (2 seeds), head-only 0.197 (1 seed)
— drift explains roughly half the loss, not all. The label diagnosis found our
GT boxes loose at the top (detector head 7 % of height lower on renders vs
1 % on MOT20; 48 % vs 79 % of boxes reach IoU 0.7), and image-statistic
distance orders the four arms the same way as AP. No single cause restores
zero-shot.

**6 · Loiter.** *"Why the 90th-percentile displacement and not mean speed?"*
— A pacer's mean speed can be walking speed while their spread stays inside a
few metres; spread measures *confinement*, which is what loitering is. The
90th percentile tolerates one excursion without resetting (commit `1a5322b`).

**7 · Alarm funnel.** *"Who chooses the recall/precision point?"* — The
customer, with numbers. Each stage logs how many candidates it dropped and why,
so the trade is visible (`38a8cb4`). My job is to make it an informed choice,
not to pick it silently.

**8 · Variety.** *"How do you know your gate isn't too lenient?"* — It blocked
real failures (v1/v2 had encoded failed sets before it became blocking) and
it checks footprints, not centre points. The remaining risk is aesthetic
realism the gate cannot measure; `docs/15_REALISM_STATS.md` compares image
statistics to real footage for that.

**9 · Licence.** *"How would you get real data legally?"* — Customer-consented
footage under a data-processing agreement with a DPIA, or licensed datasets;
report 44 covers the UK GDPR side. The roadmap already lists it as a budget
line (`23_ROADMAP_AND_GAP_ANALYSIS.md`).

**10 · Hung engine.** *"Why not just switch engines?"* — Because the editor
route turned out to be the real one: headless MRQ and SceneCapture2D render
real frames, and the parametric body is verified there (`CLAUDE.md`, "The
editor route is the real one"). Switching the *path* within Unreal cost less
than switching engines.

**11 · Profiling.** *"What would you do differently?"* — Profile the whole
`--task all` run with a sampling profiler first, then drill in. I profiled the
suspected half because I had a hypothesis; the hypothesis was the problem.

**12 · Histogram.** *"Isn't OSNet winning cross-lighting good news?"* —
Partly: it shows the embedding is not purely colour, because colour shifts
day↔night and the histogram collapses to rank-1 0.245 (OSNet 0.444). Do not
quote 0.869 — that was the leaky same-frame protocol (32 §H4 caveat). But cross-camera is the
operational task, and there the network loses to colour. Both facts go in the
write-up.

## Delivery notes

- Lead with the **number**, then the story: "HOTA went from 0.545 to 0.434 (0.443 once matched to TrackEval)
  when I fixed our evaluator — here's how I found it."
- Keep the Action as the longest part; interviewers score what *you* did.
- End each story with the lesson in one sentence and stop; let them ask.
- If asked "what did the AI assistant do versus you?", be straightforward:
  commits in this repo carry co-author trailers, and the judgement calls —
  which hypotheses to test, what to report, what to stop claiming — are the
  part to own.

## Verification table

| Story | Key number | File/commit |
|---|---|---|
| 1 | mean 157.6 / std 21.9 | `docs/BUG_black_render.md`, `97325e4` |
| 2 | HOTA 0.545 → 0.434 (→ 0.443 TrackEval parity, M1) | `docs/13_BASELINES.md` l.80–81, `be9f52a` |
| 3 | 34.6 % → 0.0 % | `docs/11_IMPLEMENTATION_STATUS.md` l.252–255 |
| 4 | peak 3.4 GB; guard 7 200 MB | `docs/12_UNREALCV_ENGINE_NOTES.md` l.874–882, `d57db8c` |
| 5 | AP 0.276 → 0.152 ± 0.025; real 0.491 ± 0.003; +synth 0.472 | 32 §H1 `5e5f53d`; §H6 `4eac637` |
| 6 | 0/2 → 2/2; 51.43 FA/cam-h | `1a5322b`; 32 §H5 `5e5f53d` |
| 7 | 27.75 → 0.25 FA/cam-h | `38a8cb4` |
| 8 | 18/18; 6/6 | `19d2df4`; `docs/12` §Environment variety |
| 9 | CC BY-NC-SA 3.0 | `docs/research/23_ROADMAP_AND_GAP_ANALYSIS.md` l.317, 547 |
| 10 | 5 restarts, 40 min | `docs/12_UNREALCV_ENGINE_NOTES.md` §2 |
| 11 | 62.0 s vs 1 h 26 min | `docs/13_BASELINES.md` l.90–130 |
| 12 | mAP 0.219 vs 0.148; lighting rank-1 0.444 vs 0.245 | 32 §H4 `5e5f53d` |
| 13 | recall 0.652 vs 0.665 (−0.013); 16 CC0 bodies | `docs/12` §batch_v7, `8c3b03b`, `9c87424` |
| 14 | IoU 0.781 → 0.884, 0.712 → 0.911; AP loose 0.290 ± 0.024 vs tight 0.266 ± 0.004 | `0213002`, `68ee6d1`, docs/11 l.198–204 |
| 15 | all rendered bodies 1.70 m; > 2 cm check; both tightgt sets FAIL the gate | `92e1e97`; `208cfc5` |
| 16 | 4.55 / 6.01 / 20.7 / 87.4 FA/cam-h; 4,500–87,000×; transit 54 %; 3,002 cam-h; round 2: learned 3.745 [3.676, 3.815], actor-aware recall 0.831 vs dwell_25 0.367 / dwell_60 0.000, 1.60× (was 2.06×); round 3 shipped A1 2.915 [2.854, 2.977] / 0.825, context −21 %, ~2,900× | 32 §H12, `9dea4f9`; 58 §6 `44e34f5`, §7 `bcbe9d2` |
| 17 | gate 9/9; height 0 > 2 cm; IoU 0.876–0.932; amodal 0.879–0.914; vis < 0.8 12.5–19.4 %; recall 0.696 / 0.879 vs 0.664 / 0.819; 33 s decode | `docs/12` §batch_v8 `94145fa`; `1fd38df` |
| 18 | 9/13 tune → 2/13 held-out (low-light); raw recall 0.938, low-light 0.103 | 32 §H32, `1acb9bd`, AUDIT_H32 |
| 19 | 57.4 m [46.2, 68.0] vs ≤ 0.5 m bar; 5/10 at f bound; datasheet f 0.96 m (post hoc) | 32 §H39, AUDIT_75_H39 |
| 20 | 70.96 → 4.20 FA/cam-h (16.9×); recall 0.945 → 0.100; 6/100 intruders ≥ 1.5 m deep | 32 §H40 `02b51ae`, AUDIT_76_H40 |
| 21 | HOTA 0.434 → 0.443; \|Δ\| ≤ 1e-15; five defects | docs/13 §TrackEval parity, AUDIT_M1_PARITY |
| 22 | realised recall 0.511 vs 0.825; ranked +0.262 @30 s; CRC 0/10 vs 6/10, −0.035 | 32 §H22 `57ffff6`, §H33 `93cc3b1` |
| 23 | 39 hits (17 current); 43 registry rows | AUDIT_STALENESS_SWEEP, RETIRED_CLAIMS.md |
| 25 | AUDIT_H60 7/10; tests 13 → 17 → 22; leak 0 of 9 654 | 32 §H60 `39da635`, `f85d479`, `caebe7a`, AUDIT_H60 |
