# 23 · Roadmap — gap analysis and prioritised build plan (v2, post-experiment)

*v2, 2026-09-27. Rewritten after H1–H18, h14b, H58 rounds 1–3 and the H19/H20
pre-registrations (32, 58, 64); Far-field and ReID rows updated with H19/H20 results (`cfa9c2a`). The original plan, written on 2026-09-26
before any experiment ran, is kept unchanged as **Appendix — v1,
pre-experiment**. v1's §8–§12 (code re-check, walk-throughs, interfaces,
effort, master checklist) are still in the appendix and still valid as
engineering reference. Tags: [V] verified, [A] exists but untried, [X] tried and
broken. Commit hashes are the commits that hold the results, as cited in 32,
52 §5 and 64 Table 2.*

---

## 0. The one-paragraph answer (v2)

v1 staked the roadmap on one bet: M4, "synthetic data helps a real metric".
Nineteen experiments later that bet has a measured answer. **As a replacement
for real data, no** (synthetic-only fine-tune 0.276 → 0.152 ± 0.025 AP, H1).
**As an additive, a little**: +0.004–0.005 AP at equal optimiser steps
from 100–300 CC0 renders beside 60 real frames — Holm-significant at 10 paired seeds
(H51, `385f363`: +0.0042 / +0.0051, p 0.0039) after H26's 5 seeds (`dbd21c4`) did not clear Holm; h14b's +0.0121 [0.0111, 0.0130] (`549f433`) compared unequal
steps. H52/H61 (10 paired seeds each): the gain is labels on people — shuffled boxes erase it (+0.0077 gap), silhouette-masked frames with no box-shaped fill give nothing (−0.002 vs real-only); H52's apparent 'background' gain was the inpainted box fill. Duplicating real frames does nothing (−0.0011). The unequal-step gain replicated on YOLO26n, and carried weakly to HOTA
(+0.0103, H17, `829feb4`, same unequal-step arms, pre-parity scorer). All of it is on **one real site** (MOT20-01 →
MOT20-02, very likely the same square) under a **non-commercial** licence.
The alarm side has a sharper answer. No track-only loiter rule comes near
an operator budget. The shipped learned rule runs at 2.915 FA/cam-h (recall
0.825, `bcbe9d2`) against 0.001, and a generator-defined kinematic-twin
floor of about 1 FA/cam-h bounds every track-only rule. The binding
constraints are therefore no longer code. They are **real data** (more sites,
commercial licence, genuine far-field and IR) and **context** (site profiles).
The v2 roadmap is re-ranked around those two, and keeps the simulator's value
where it has been shown: evaluation with ground truth real CCTV cannot give.

---

## 1. Gaps, re-measured (replaces v1 §1)

| Area | v1 status (pre-experiment) | Measured now | Evidence |
|---|---|---|---|
| Harness throughput | `--task all` cannot finish MOT20 | Tracker + `evaluate_mot` run all 8,931 MOT20 frames in ~62 s; ReID and `eval_det` stages still unprofiled | `5b01bf0`, docs/13 |
| Metric trust | HOTA/IDF1 untested against reference | Validated against definitions (30 tests, 8 on real MOT20), and since M1 (`5571631`) against TrackEval: HOTA 0.443, max \|Δ\| 1e-15 (the pre-M1 "parity not done" row is superseded) | 52 §5, AUDIT_M1_PARITY |
| Render labels | loose projected boxes, 1.70 m height fallback | **batch_v8 is the first fully-labelled set**: 9 sets, visible + amodal + visibility, GT heights 1.22–1.89 m, gate 9/9, box IoU 0.876–0.932, CC0 | `94145fa`, `92e1e97` |
| Label choice as a lever | untested | Inert: tight vs loose −0.024 (n.s.), amodal − visible −0.0005 [−0.0012, +0.0001]; σ 10 % jitter + 10 % drop keeps 94 % of the dose-100 gain (H25) — gain not in box geometry | docs/11, H15 `b6c735e`, H25 `c1100bb` |
| Synthetic → real detection | untested (M4) | Replacement [X]; additive [A] +0.004–0.005 at equal steps (H51, Holm p 0.0039; h14b +0.0121 was unequal steps), null by 1,000 frames and turns negative as pre-training (H7) | h14b `549f433`, H16 `549f433` |
| Realism screen | 6/14 day in band | Image-stat distance predicts transfer, ρ −0.60 [−0.78, −0.20], n = 20, one seed per source | H13 `9dea4f9` |
| Far field | untested | Far − near HOTA −0.171 [−0.251, −0.086]; H8's collapse **replicates** synthetic-only at 1280 on v6 *and* v8 (AP50 0.000 all 3 seeds vs zero-shot 0.613), so it is a domain effect, not labels/heights; 60 real frames fix it (0.817, +0.817 [+0.812, +0.824]); H27 retired | H9 `4a51207`, H18 `829feb4`, H19 `cfa9c2a` |
| Night | uncalibrated, 3/14 vs day targets; 3/13 vis · 2/13 thermal vs LLVIP (69 §7); renders luma 90 = not dark | IR degrade − night recall −0.609 [−0.710, −0.519] (simulated sensor model; H32 overfit, not a field penalty); MOT20-05 is lit colour night, not IR — **LLVIP (NC, measurement only) is now the reference**; H32 `cctv_night_lowlight`/`cctv_thermal` overfit (hold-out 2/13, 3/13) | H11 `4a51207` |
| Drift monitoring | design only (21, 53) | H34: uncalibrated PSI/KS useless (100 % of stationary windows fire, 1,440/24 cam-h at 1 check/min); calibrated mean-shift 6/12 at 9.2/24 cam-h, misses blur; embedding 0/12 (≤ 26.6 certifiable); inconclusive → H44 | H34 `cf33bb2`, AUDIT_H34 |
| ReID | ImageNet OSNet only | On renders an HSV histogram matches ImageNet OSNet; both collapse across an outfit change (one changer). **H20**: OSNet fine-tuned on 15 synthetic ids → held-out synth cross-camera mAP +0.324 [+0.197, +0.493], MOT20 cross-time +0.021 [−0.047, +0.097] (no measurable effect) — identity count is the limiter | H10b `41f77f9`, H20 `cfa9c2a` |
| Alarm scale | H5 mock estimates | 3,002 clean camera-hours: shipped rules 4.55–87.4 FA/cam-h; learned A1 2.915 [2.854, 2.977] @ recall 0.825; twin floor 1.008 [0.973, 1.045]; zone context −20.7 % (P8 needed 25 %) | H12 `9dea4f9`, H58 r3 `bcbe9d2` |
| Alarm realism | — | All alarm numbers are on **GT tracks** (perfect perception) with **generator-chosen** dwell distributions: lower bounds, not estimates | 64 §7.4 |
| Edge precision cost | assumed free (INT8 budgeted in 38 §2.5) | FP16 export loses 0.0000 AP; INT8 static PTQ 0.0117 (range 0.0081..0.0154; not met at 0.015), mostly AP75 (−0.030); calibration source n.s. — onnxruntime CPU only; **no Jetson/TensorRT latency** (next: H43) | H38 `d6b204d`, AUDIT_H38 |
| Licences | not audited | MetaHuman renders (batch_v4–v6) forbidden for ML by the current licence; batch_v7+ CC0 (`commercial_ml_ok`). **MOT20 is CC BY-NC-SA**: every real number and every trained weight is non-commercial | 47 §0, 64 §7.1 |
| Degrade speed | 0.567 s/frame | unchanged, 0.567 s/frame; target ≤ 0.3 not reached | docs/15 |
| Wardrobe / gait | [A] | Wardrobe still [A] (no dressed render); parametric body [V]; gait from MOT20 downloaded, not extracted; outfit epochs are palette swaps + cap proxy | 52 §5–6, `99d986b` |
| Pipeline-in-the-loop, sensors, operator, ODD report | Missing | still Missing: no `t_detectable_from`, no radar/wildlife, no operator model, no mediamtx rig, no coverage report generator (grep of `survsim/`, 2026-09-27) | — |

---

## 2. Prioritisation logic (v2)

v1: value × unblocking ÷ cost, with "no synthetic number without a real
counterpart". v2 keeps both and adds two lessons the experiments taught:

1. **The real side sets the ceiling.** 60 real frames alone add +0.21 AP (H1);
   100 synthetic frames add +0.004 at equal steps (H51, Holm-significant, ~1 % relative). Any milestone that multiplies real
   evaluation sites moves every claim; one that improves renders moves the
   second decimal.
2. **Negative results are cheap to buy and expensive to ignore.** Four
   "obvious" levers (tight labels, amodal labels, pre-training, large doses)
   did nothing or hurt. So every milestone below is paired with a
   pre-registered hypothesis in `66_HYPOTHESIS_BACKLOG.md` and an abandon rule.

Expected value (EV) below = P(success) × value to the product claim ÷ cost,
scored 1–5 each [INF].

---

## 3. Milestones: measured status (replaces v1 §3 status)

| M | v1 goal | Status 2026-09-27 | Commits | What remains |
|---|---|---|---|---|
| M1 | Harness throughput + TrackEval parity | **Partial.** Throughput met for tracking (~62 s / 8,931 frames); metrics definition-validated. **TrackEval parity done (2026-09-27):** |Δ| ≤ 1e-15 on MOT20 subset / batch_v8 day / edge cases after fixing HOTA matching, IDF1 potential matches and CLEAR continuity; HOTA 0.434 → 0.443 (docs/13 §TrackEval parity, `tests/test_trackeval_parity.py`); funnel export and manifest content hashes not built | `5b01bf0` | TrackEval side-by-side (engineering; H24 in 66 depends on it); `eval_det`/ReID profiling; hashes |
| M2 | First honest render numbers | **Done** (differently from plan). docs/13 rows on renders (det, MOT, ReID), YOLO26n re-baseline, far/near and day/night splits | `4a51207`, `549f433` | 20k-frame 6-scenario suite not rendered; batch_v8 is 10k frames |
| M3 | Pipeline-in-the-loop | **Not started** | — | unchanged; also needed to put perception into alarm studies |
| M4 | Synthetic helps a real metric | **Answered, narrowly.** Replacement [X] (H1, H2, H8, H11-B). Additive [A]: **+0.004–0.005 at equal steps (H51, 10 paired seeds, Holm p 0.0039)**; unequal-step h14b +0.0121 [0.0111, 0.0130] at 60 real frames, +0.0095 at 300, 5 seeds, Holm p 0.0079; YOLO26n +0.0092/+0.0169; HOTA +0.0103. v1's acceptance (≥ 2 AP50 at ≤ 25 % real) **not met**; the "documented negative with failure analysis" branch is met (H6, 64 §6) | `549f433`, `829feb4`, `5e5f53d` | cross-site transfer; H51 equal-step 10-seed re-run (H26 done: n.s.); commercial-licence real set |
| M5 | Night/IR calibration | **Partly unblocked.** LLVIP (NC) reference: 3/13 vis · 2/13 thermal; H32 profiles overfit (9/13→2/13, 10/13→3/13, `1acb9bd`); IR degrade costs −0.609 recall in simulation (not quotable: H32 overfit); no licensed real IR frames | `4a51207` | new M16 (night reference set) is the prerequisite |
| M6 | Behaviour eval at operational scale | **Mostly done on mock.** 3,002 clean cam-h + 360 recall events; actor-aware scoring default (`7827ddc`); rules 4.55–87.4, A1 2.915 FA/cam-h (**~2,900× over our assumed 0.001**), twin floor 1.008; round 4 (`bd4c028`): A1 stays, but its 2.915 is a θ-selection draw (5.033 at the adjacent θ on 7/10 folds). `t_detectable_from` still missing; mock trajectories **not validated** against real pedestrian statistics | `9dea4f9`, `44e34f5`, `bcbe9d2` | trajectory validation; perception-in-the-loop alarms; site profiles (M12) |
| M7 | Population/asset diversity | **Partial.** CC0 cast of 16 Quaternius bodies, GT heights (`92e1e97`); parametric MetaHuman body [V] but MetaHuman output is **licence-barred for ML**; wardrobe [A]; one outfit changer | `92e1e97`, `99d986b` | reframed: CC0 diversity + foot IK (M14); MetaHuman route only for non-ML demos |
| M8 | Perimeter sensors | Not started as sensors (RF/audio exist; no radar/fence sensor). Behaviour gaps closed by H40b (`9468696`): fenced zones, crossing intruders, fence_climb, patrol/maintenance twins, wildlife agents. **H40b (`12b6c92`, AUDIT_H40B):** C 0 clean FA (≤ 0.001) at recall@10 0.782, not met; twin FA 0.389 + 0.099 ≈ 490× budget → H49 gate-log/schedule fusion, H50 track stitching. **H40 (`2323de7`), before the fix:** naive 70.96 → 4.20 FA/cam-h (÷16.9) but recall@10 0.100, not met; FA optimistic (no patrol/animal/weather twins, assumed tracker noise) | `2323de7` | behaviour-engine gaps first — intruder arc that crosses the zone, patrol-guard twin, climb arc, animal agent (76 §5); **D37 is fixing these**; then H40b (pre-registration pending — link here when it lands); radar/fence fusion after |
| M9 | Operator model | **Simulated (H22), invented operator.** One operator × 40 cams at A1's rate: utilisation 0.88, 25 % of alarms bulk-acked; FIFO realises 0.511 [0.484, 0.537] of 0.825 at 5 min (inconclusive vs 0.495), 0.127 at 30 s; **ranked queue +0.262 at 30 s** → product shape = score-ranked review queue above ~1 FA/cam-h per 40 cams; θ per site by CRC (H33, 0/10 splits over α, −0.035 recall) | `57ffff6`, `93cc3b1` | measured operator parameters (review time, fatigue, bulk-ack) from a real control room; per-camera θ (H35) |
| M10 | Coverage-driven verification report | Not started | — | depends on M12 + real counterpart numbers |
| M11 | Degradation speed | Not done; 0.567 s/frame | — | unchanged, cheap |

**Licence-clean data status.** Synthetic side: clean from batch_v7 on (CC0,
`licences.json`, `commercial_ml_ok`); H14b–H18 use only CC0 renders.
batch_v4–v6 (MetaHuman) are internal evidence only. Real side: **not clean** —
MOT20 (CC BY-NC-SA 3.0) is the only real source, so weights from H1/H7/H14–H18
cannot ship. **batch_v8** is the first set that is simultaneously
commercially clean, fully labelled (visible, amodal, visibility), height-true
and gated 9/9; it is the default training/eval source for everything below.

---

## 4. Re-ranked roadmap (replaces v1 §4 sequencing)

New milestones M12–M16 are the ones the evidence demands.

Calibration note (H39, `2bdb46b`, AUDIT_75_H39): pedestrian-box auto-calibration with free f is not
met (57.4 m RMSE < 20 m); world-coordinate tracking (73) and metric speed/height need datasheet f
+ surveyed validation points, or head–foot keypoint auto-calibration (H41, 66) — a cheap CPU item
that uses our keypoint GT and rides with M14 (foot IK tightens the 0.21 m floor).

| Rank | M | What | Why now (evidence) | EV [INF] | Est. |
|---|---|---|---|---|---|
| 1 | **M12 (new)** Real multi-site data acquisition, commercial licence | ≥ 3 real sites held out by site, incl. one genuine far-field camera; consented or commercially licensed; per-site soak hours | Every detection claim is one site, non-commercial (64 §7.1–7.2); publication item 1–2 | 5×5÷4 | 6–10 wk, mostly procurement/legal |
| 2 | M1 remainder | TrackEval parity, `eval_det`/ReID profiling, manifest hashes | Cheap; every tracking number is currently "our definition" | 5×3÷1 | 1 wk |
| 3 | **M13 (new)** Site-profile capture | SiteProfile schema (62 §1, §5): zone function, timetables, portals; generator + inference from tracks | Only lever measured against the alarm floor (−20.7 %); A1 cannot go below ~1 FA/cam-h track-only | 4×4÷3 | 3 wk |
| 4 | M9 (up from P2) | Operator + review-queue simulation | At 2.9 FA/cam-h the alarm is a queue, not an alarm; decides the product shape | 4×4÷2 | 2 wk |
| 5 | M3 | Pipeline-in-the-loop | Alarm rates are lower bounds until detector + tracker errors are in the loop (64 §7.4) | 4×4÷3 | 3 wk |
| 6 | **M15 (new)** ReID trained on appearance truth | Train on epoch-labelled identities; needs ≥ 100 ids and ≥ 10 changers — H20 (15 ids) measured the floor: +0.324 in-domain, no real transfer (+0.021 [−0.047, +0.097]), so ids first | Only task where synthetic truth is uniquely valuable (outfit-change pairs real data lacks) | 3×4÷3 | 3 wk (render-bound) |
| 7 | M4 follow-up | Fixed-step dose curve, ≥ 10 seeds, non-nano detector, cross-site | Confirms/limits the one positive transfer result | 3×3÷2 | 2 wk GPU |
| 8 | **M14 (new)** Foot IK | Ground-contact IK for CC0 bodies | Feet drive amodal boxes, height and homography stature (13 §A2); gait-from-pixels needs real foot contact | 3×3÷2 | 2 wk (editor) |
| 9 | **M16 (new)** Night reference set | ≥ 200 licensed real IR CCTV frames with labels | Prerequisite for M5; night claims are withheld until it exists. **H32 reference (`1acb9bd`):** fits to 15 LLVIP frames overfit (hold-out 2/13 vis, 3/13 IR); recall spread −0.47 to −0.84 by sensor model, so no night penalty is quotable; next is H36 (full LLVIP, ~3.5 GB, sign-off) and a commercially licensed set | 3×3÷3 | 4 wk procurement |
| 10 | M5 | Night/IR calibration | Only after M16 | 3×3÷2 | 2 wk |
| 11 | M11 | Degrade speed | Needed for any large degraded re-run (H28) | 2×2÷1 | 1 wk |
| 12 | M6 remainder | `t_detectable_from`; mock trajectory validation vs ETH/UCY/SDD | Makes FA/cam-h a claim about the world, not the generator | 3×3÷2 | 2 wk |
| 13 | M10 | Coverage report | Needs M12 real counterparts and M13 site classes | 4×3÷3 | 3 wk |
| 14 | M7 | CC0 population diversity (more bodies, carried objects) | Diversity is the literature's condition for synthetic benefit (64 §6) | 2×3÷4 | 4 wk |
| 15 | M8 | Radar/fence sensors, gate-log fusion | H40b: with wildlife/patrol twins now generated, video-only reaches 0 clean FA but recall 0.782 and twin FA ≈ 490× our assumed budget — the twin needs access-log/schedule fusion (H49). H40: a video-only sterile-zone rule is > 4,000× budget and loses 90 % recall at its best arm; the missing wildlife/patrol twins mean even that FA is optimistic. Behaviour-engine gaps (D37) come before sensors | 2×3÷3 | 3 wk |

```
weeks:  1  2  3  4  5  6  7  8  9 10 11 12
M12     ████████████████████████████████    (procurement, parallel to all)
M1      ██
M11       ██
M13       ██████
M9              ████
M3              ██████
M15                   ██████
M4+                   ████
M14                         ████
M16     ████████████████                    (procurement)
M5                          ████
M6r                               ████
M10                                  ██████
```

Critical path: **M12 → (M4 follow-up cross-site) → M10**; alarm path:
**M13 → M9 → M3**.

---

## 5. Risks (v2 additions)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No commercially licensed real multi-site data obtainable | high | high | customer-consented pilot data under DPIA (44, 62 §6); otherwise publish as evaluation-oracle only, with every training claim marked non-commercial |
| Additive gain vanishes cross-site | medium | medium | it is +0.004–0.005 at equal steps (H51) on near-in-domain data; drafted as H30 (66) so a null is a result |
| Site profiles are too costly to author per camera | medium | high | inference of zone function from tracks (62 §3); measure inferred vs GT profile |
| Mock alarm rates are optimistic | high (known) | medium | M3 (perception-in-the-loop alarms); never quote GT-track FA as a system number |
| Engine-bound work (foot IK, bodies) stalls | medium | medium | CC0 path already [V]; keep MetaHuman out of any ML path (licence) |

## 6. What to stop doing (v2 additions)

* Treating synthetic data as a replacement for real data (H1, H7, H8, H11-B).
* Adding label variants in the hope of transfer (H15: no effect).
* Tuning loiter thresholds on the test worlds (58 round 3: C 1.95 / D 1.80
  were round-4 candidates only; round 4's honest selection put C at 2.960).
* Choosing θ by one grid search on one ~106-event select fold, or claiming an
  arm beats A1 from one seed (58 §8.2: H21 2/5 seeds; H23 same weights 2.915
  or 5.033 by fold). Next: pooled-fold / conformal θ as the shipped policy
  (66 H42), challengers must win ≥ 4/5 seeds.
* Quoting any MetaHuman-rendered number externally (47 §0).

## 7. Definition of success (v2, next 12 weeks)

1. One detection result measured **across sites** (held out by site) on
   commercially usable real data, positive or null.
2. TrackEval parity table in docs/13.
3. An alarm result with perception in the loop and a site profile, reported
   as an operator review-queue load, not as a raw FA/cam-h.
4. Night claims calibrated against a real IR reference or still withheld.

The hypotheses that operationalise these are in
[`66_HYPOTHESIS_BACKLOG.md`](66_HYPOTHESIS_BACKLOG.md) (H21–H32).

---

# Appendix — v1, pre-experiment (2026-09-26)

*Kept verbatim except that headings are demoted one level. Written before any
experiment ran; superseded by §0–§7 above wherever they disagree.*


*Series 17–23. Takes the requirements of reports 17–22, compares them with what
SurvSim can already produce (docs/11, docs/12, docs/13, docs/15 as of
2026-09-26), and orders the work. Every milestone has a measurable acceptance
criterion; nothing is "done" because code exists (CLAUDE.md working style: [V]
verified, [A] exists untried, [X] tried and broken).*

**Sourcing.** In-repo documents; estimates of effort are **[INF]** and assume
one engineer-week ≈ 5 focused days.

---

### 0. The one-paragraph answer

SurvSim already covers the *evaluation* side of the real-world system unusually
well — it scores detection as alarms per camera-hour, tracking with HOTA
DetA/AssA, MTMC with handoff gaps, ReID across appearance epochs, 32+
behaviours with hard negatives, i-LIDS timing, tamper, fusion with correlated
nuisances and an alarm funnel (docs/11). It is weakest where the real system
meets pixels at scale: renders are few (batch_v4: 5,400 frames; batch_v5/v6 since added more sets, docs/12) and only
recently person-realistic (MetaHuman, recall 0.758), image statistics sit 6/14
in band for day and are uncalibrated for night (docs/15), three body shapes
limit ReID and height cues, degradation runs at 0.567 s/frame, and
`survsim baseline --task all` cannot finish full MOT20 (killed at 2.5 h and again
at 1 h 26 min; docs/13). docs/13 has since profiled the tracker + `evaluate_mot`
at ~62 s for all 8,931 frames, so the "O(n²) association" diagnosis was wrong;
the remaining time is most likely the ReID stage and/or `eval_det`, which have not
been profiled.
The roadmap therefore (1) fixes harness throughput, (2) produces the first
honest synthetic-vs-real numbers on renders, (3) proves synthetic data helps
a real metric (TSTR), (4) turns SurvSim into a pipeline-in-the-loop and
coverage-verification tool, and (5) fills sensor and population gaps in the
order the product needs them.

---

### 1. Gap analysis by component

Legend: **Have** = [V] in repo; **Partial**; **Missing**.

#### 1.1 Ingest, timing, health (report 17 §3.1–3.2, report 22 §4)

| Need | SurvSim state | Gap |
|---|---|---|
| Per-camera video + timing sidecars | Have (`gt/video.py`) | — |
| ONVIF-style metadata | Have (docs/11) | validate against a real VMS parser |
| Clock offset/drift | Have (docs/02) | scenario suite that sweeps skew |
| Live RTSP serving | Partial: command returned, not run (docs/11) | HIL rig (M3) |
| Stream faults (drop, freeze, corruption) | Partial: frame drop in degrade; freeze as tamper | packet-loss corruption model |
| IQA stats | Have (`realism/stats.py`) | expose as per-frame GT sidecar |

#### 1.2 Perception (report 18)

| Need | State | Gap |
|---|---|---|
| Realistic people | Have: every rendered person MetaHuman [V] (docs/11) | only 3 baked bodies (two ~1.58 m, one ~1.93 m, scaled) |
| Mask-derived boxes, visibility, keypoints | Have | — |
| Clothing variety | Partial: painted street-wear per identity; wardrobe API [A] | real garments; hi-vis/uniform variety |
| Hard-negative objects (mannequins, posters, reflections, animals) | Missing | asset set + labels |
| Pixel-height matched datasets | Partial: rig analysis computes, generator stratifies | automatic matching to a target site |
| Detector baseline on renders | Partial: yolov8n recall on 770 GT boxes (docs/12) | full AP by bucket via `survsim baseline` |
| MOT baseline | Partial: numpy ByteTrack, MOT20 subset only | vectorised association + TrackEval cross-check |
| ReID baseline | Partial: OSNet-ImageNet only | MSMT17-trained OSNet, CLIP-ReID |
| PTZ GT | Have | slew-to-cue benchmark |
| Calibration GT (configured vs actual) | Have | commissioning-noise simulation |

#### 1.3 Behaviour (report 19)

| Need | State | Gap |
|---|---|---|
| Catalogue with hard negatives | Have (44 classes / 49 names) | — |
| Event GT with difficulty and hard-neg tags | Have | `t_detectable_from` per camera; `observed_by` exists only on appearance-change records (`director/world.py` l.406) |
| Rule baseline + learned classifier | Have | shared rule DSL with product |
| Alarm funnel | Have (`eval/pipeline.py`) | per-stage Pd/FA export |
| Volume for FA estimation (~400 camera-h per type) | Partial: mock backend scales; renders don't | validated mock-trajectory realism |
| Animation for fight/fall/tamper | Partial: walk/run/idle loops + look-around (docs/11) | interaction animations (fight, fall, climb, kneel-tool) |

#### 1.4 Degradation & fusion (report 20)

| Need | State | Gap |
|---|---|---|
| Day profile calibrated | Partial: 6/14 on renders; spatial stats pass fixture | temporal noise; content stats |
| Night/IR | Partial: profile exists; no real reference | real IR reference set; illuminator/particle model |
| Thermal | Have | validation data |
| Weather | Partial | rain on lens, fog per Koschmieder, snow under IR |
| Tamper | Have (6 kinds) | negatives (night switch, cleaning) as scenarios |
| RF, audio | Have | real-reference validation |
| Radar, fence/DAS | Missing | models driven from shared world state |
| Wildlife agents | Missing | fox/deer/birds for perimeter nuisance |
| Degradation speed | 0.567 s/frame (target 0.3) | buffer reuse, LUT gamma, parallelism |

#### 1.5 Data/MLOps & operations (reports 21, 22)

| Need | State | Gap |
|---|---|---|
| Dataset build + seed splits | Have (`survsim dataset`) | site/camera-level splits for real data |
| Real reference row | Partial: MOT20 subset | full MOT20; a CCTV-like real set (e.g. public surveillance datasets with licences) |
| Operator model | Missing | disposition accuracy/latency/fatigue simulation |
| Coverage-driven verification / ODD report | Partial: generator stratifies; no coverage report | ODD definition + report generator |
| Pipeline-in-the-loop | Missing | mediamtx + DeepStream HIL rig |
| Registry-friendly outputs | Partial: manifests | content hashes, SurvSim commit, profile versions in every manifest |

---

### 2. Prioritisation logic

Priority = (value to the product's core claim) × (unblocks other work) ÷ cost,
with a hard rule: **no synthetic number is reported externally without a real
counterpart** (docs/13 rule 4). The product's core claim is "fewer false
alarms at operationally-timed detection, verified across a stated envelope"
(reports 17, 19). So work that produces the first honest end-to-end number on
realistic renders beats work that adds features.

---

### 3. Milestones

#### M1 — Harness throughput and trust (2 weeks) — P0

**Why**: every later milestone runs the harness; today `--task all` can't finish MOT20.
**Update (docs/13, 2026-09-26):** ByteTrack + `evaluate_mot` already run full
MOT20 train in ~62 s after vectorisation (commit 5b01bf0), so acceptance 1 is
met for the tracking stages; the open work is profiling the ReID and `eval_det`
stages.

Work:
* Profile and vectorise the per-frame Python loops in `baselines/bytetrack.py`
  and `eval/tracking.py`. Both already call `scipy.optimize.linear_sum_assignment`
  (bytetrack l.83; tracking l.114, l.173), so the cost docs/13 reports is the
  dense per-frame IoU construction and the dict-based pair counting
  (`_id_true_positives`, `_association_accuracy`), not the solver. Gate the
  cost matrices, build IoU by broadcasting, and count (gt, pred) pairs with
  `np.unique` on encoded ids.
* Cross-check HOTA/IDF1 against TrackEval [2] (MIT licence; implements HOTA,
  CLEAR and Identity metrics) on MOT17/MOT20 train.
* Add per-stage funnel export from `eval/pipeline.py`.
* Add content hashes + SurvSim commit + profile params to dataset manifests.

**Acceptance**:
1. Full MOT20 train (4 sequences, 8,931 frames) scored end to end in < 20 min
   on the dev machine using cached detections.
2. HOTA/IDF1/MOTA within ±0.5 points of TrackEval on the same inputs.
3. Funnel report lists candidates, Pd and FA after each stage for
   `configs/scenarios/disguise_and_tamper.yaml`.
4. Regression tests added for each (working-style rule).

#### M2 — First honest render numbers (3 weeks) — P0

**Why**: docs/11 "Detection/MOT/ReID baselines on our own renders" is the
top "not yet" item; batch_v4 finally has realistic people.

Work:
* Render a *baseline suite*: 6 scenarios × day/night × 3 camera heights,
  ~20k frames total at 720p (≈ 30 min render at 11 fps; ≈ 3 h degradation at
  0.567 s/frame — run in background, parallelise across processes).
* `survsim dataset --frames-dir` → `survsim baseline --task all` with
  YOLO11n/s, ByteTrack, OSNet (MSMT17 weights).
* Report synthetic − real gap per task at matched pixel heights against the
  full MOT20 row (from M1).

**Acceptance**:
1. docs/13 results table gains a row with `synthetic_topdown: false` for each
   of det/MOT/ReID on renders.
2. Gap reported per height bucket; any bucket with |gap| > 0.2 AP50 has a
   written failure analysis (report 18 §9 order).
3. Day profile stats reported on the suite (docs/15 method).

#### M3 — Pipeline-in-the-loop (3 weeks) — P1

**Why**: report 17's contracts and report 22's latency budget can only be
tested with real streaming.

Work:
* Serve degraded SurvSim videos over RTSP via mediamtx [3] with SurvSim timing.
* A reference analytics pipeline (DeepStream on a GPU box, or PyAV+ONNX on the
  dev machine) emitting report 17's message contracts to MQTT.
* Scorer that consumes the bus and GT: latency, Pd at i-LIDS tolerance,
  FA/camera-hour, handoff gap.
* Fault injection: stream drop, freeze, clock skew, tamper.
* Reference tracker (H24/H46b, AUDIT_H24/H46B): ByteTrack + OSNet-ImageNet appearance at **w ≈ 8**
  (cross-validated; +0.05 AssA held-out) with the IDSW cost stated (day ΔIDSW −1.62, MOT20-02
  ΔIDSW +15.8) — never appearance-only (`app_only` ΔIDSW +162.0 MOT20-02, ΔDetA −0.0109). H20's
  synthetic ReID weights are not used (no better). Night arm positive but CI misses 0 by a hair
  (H46b bar met post cross-validation at w = 8).

**Acceptance**:
1. 8 cameras × 1 h synthetic scenario runs unattended; report produced.
2. Measured p95 alarm latency reported; injected 2 s skew shows a measurable
   handoff-error increase.
3. Stream drop of 30 s produces a camera-health event within 60 s.

#### M4 — Synthetic helps a real metric (TSTR) (4 weeks) — P0

**Why**: the only evidence that makes SurvSim commercially meaningful.

Work:
* Fine-tune YOLO11s: (a) real only (a CCTV-like real set with permissive
  licence + MOT17/20 train), (b) synthetic pre-train + real fine-tune,
  (c) 10/25/50 % real data subsets for low-data curves.
* Evaluate on held-out real sequences (split by sequence/site), stratified by
  pixel height and night.

**Acceptance**:
1. (b) beats (a) by ≥ 2 AP50 on the 20–60 px bucket or at ≤ 25 % real data,
   with CIs from ≥ 3 seeds; **or** a documented negative result with the
   failure analysis (a negative result is still a deliverable).
2. Results added to docs/13 with training manifests.

#### M5 — Night/IR calibration (2 weeks) — P1

Work: acquire ≥ 200 real IR CCTV frames (licensed), compute docs/15 band,
retune `cctv_night_ir` (monochrome-aware grain — docs/15 notes the per-channel
grain cap), add illuminator falloff + near-lens particles.

**Acceptance**: ≥ 9/14 stats in the IR band on renders; night detector-recall
gap to real IR reported.

#### M6 — Behaviour evaluation at operational scale (3 weeks) — P1

Work:
* Emit `t_detectable_from` per camera and `observed_by` intervals.
* Validate mock-backend trajectory statistics (speed, dwell, spacing) against
  real pedestrian data (docs/14 speeds; ETH/UCY [5]; Stanford Drone [6]) — the licence to use mock
  worlds for FA estimation.
* Generate ≥ 400 camera-hours per behaviour type on mock worlds; loiter T-sweep
  curves; funnel per stage.

**Acceptance**:
1. Mock-vs-real trajectory statistics within documented bands (≥ 4 of 5
   chosen stats).
2. Pd–FA curves with CIs for loiter, intrusion, tailgating, abandoned object;
   FA estimates with ≤ ±50 % relative error at 0.01 FA/camera-hour.
3. Hard negatives account for a reported share of FAs per type.

#### M7 — Population and asset diversity (4 weeks, engine-bound) — P1

Work: more MetaHuman bodies (target ≥ 20 distinct body shapes via the [V]
parametric body — height driven 171.75 → 190.0 cm across 30 constraints —
baked offline), clothing variety (wardrobe API is [A] — verify by building,
dressing and rendering one character), uniforms/hi-vis, carried objects,
mobility aids; interaction animations (fight, fall, kneel-with-tool, climb).

**Acceptance**:
1. A dressed parametric MetaHuman rendered, tagged [V] in CLAUDE.md with
   the evidence file.
2. ReID baseline on renders with bodies held out between train/test; cross-
   epoch R1 reported via `reid_by_epoch`.
3. Fight/fall clips render with bone GT; a pose-based classifier trained on
   them reports real-data accuracy on RWF-2000 [7] (2,000 clips; the paper's
   Flow Gated Network reaches 87.25 %) and UR Fall [8] (70 sequences).

#### M8 — Perimeter sensor suite (3 weeks) — P2

Radar and fence/DAS models from shared world state; wildlife agents; wind as a
shared cause (report 20 §6).

**Acceptance**: fused FA reduction factor reported for independent vs
correlated nuisances on `border_fence_night_probe`; radar Pd vs range matches
a vendor-published curve within stated tolerance.

#### M9 — Operator model and active-learning simulation (2 weeks) — P2

Simulated operator (accuracy, latency, fatigue, reason codes); closed-loop
experiment: per-site threshold adaptation + active learning over simulated
weeks.

**Acceptance**: curve of FA/camera-hour and Pd over simulated weeks for two
strategies (disposition-only vs disposition + below-threshold sampling),
demonstrating (or refuting) silent recall loss.

#### M10 — Coverage-driven verification report (3 weeks) — P1

ODD definition per site class; coverage metric; automatic failure-region
search; a customer-facing PDF/HTML report generator (DORI bands, scenario
classes, Pd and nuisance rate per cell, limitations, real corroboration).

**Acceptance**: one report for the "CNI perimeter" class with ≥ 80 % ODD cell
coverage, every external claim paired with a real-data number or marked
"synthetic-only".

#### M11 — Degradation speed (1 week) — P2

Shared float32 buffer through `_pre_codec`, LUT gamma, multiprocessing.

**Acceptance**: ≤ 0.3 s/frame single-process at 720p (docs/15 target) with
the parity fixture unchanged or re-justified; ≥ 4× wall-clock with 6 workers.

---

### 4. Sequencing

```
weeks:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
M1      ████
M11       ██
M2         ██████
M4               ████████
M3               ██████
M5                     ████
M6                     ██████
M7            ████████████████   (engine-bound, parallel)
M10                          ██████
M8                                 ██████
M9                                       ████
```

Critical path: M1 → M2 → M4 → M10. M7 runs in parallel because it is
engine-bound and has the highest schedule risk (third-time lesson: a
capability is only [V] when rendered).

---

### 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| TSTR shows no gain | medium | high | report honestly; analyse gap by bucket; shift to "evaluation oracle" positioning (which does not need TSTR gains) |
| Wardrobe API [A] fails in practice | medium | medium | painted clothing is already [V]; buy garment assets |
| 8 GB GPU limits render volume | high | medium | mock worlds for trajectory analytics; rent GPU time for bulk renders |
| Night realism unverifiable without data | medium | high | M5 data acquisition first; mark night claims synthetic-only until then |
| Licensing of real datasets for commercial use | high | high | MOT20 [1], Stanford Drone [6] and UR Fall [8] are all CC BY-NC-SA (non-commercial): fine for research baselines, **not** for training a shipped model; budget for licensed or customer-consented real data |
| Metric definitions drift between SurvSim and product | medium | high | share code (rule DSL, eval library) |
| Overfitting to SurvSim's style | medium | medium | never select models on synthetic; domain-classifier probes |

---

### 6. What to stop doing

* Reporting numbers on `synthetic_topdown` data (already prohibited, docs/13).
* Inferring capability from API names (three incidents; CLAUDE.md).
* Tuning degradation to stats measured from JPEG-still sequences as if they
  were video (docs/15 caveat on `temporal_noise`).
* Adding behaviours before the evaluation volume exists to measure them —
  the catalogue is complete; the constraint is now evidence, not coverage.

---

### 7. Definition of success at 20 weeks

1. A docs/13 table with real and synthetic rows for det/MOT/ReID on renders,
   and a TSTR result (positive or rigorously negative).
2. A pipeline-in-the-loop run producing i-LIDS-timed Pd and FA/camera-hour
   from a real streaming stack.
3. A coverage-verification report for one site class that a customer could
   read.
4. Night claims either calibrated against real IR or explicitly withheld.

---

### 8. Gap tables re-checked against the code (2026-09-26)

The tables in §1 were written from the docs. This section checks them against
the repository itself, so the plan does not rest on stale status.

| Claim | Evidence in tree | Verdict |
|---|---|---|
| MOT / MTMC / ReID scoring exists | `survsim/eval/tracking.py`: `evaluate_mot` (l.71), `evaluate_mtmc` (l.193), `evaluate_reid` (l.255), `reid_by_epoch` (l.294) | Have |
| Hungarian solver already used | `baselines/bytetrack.py` l.83; `eval/tracking.py` l.114, l.173 | M1 is a loop-vectorisation job, not a solver swap (corrected in §3) |
| Alarm funnel | `survsim/eval/pipeline.py`, `eval/alarms.py`, CLI `survsim eval` (`cli.py:eval_alarms`) | Have; per-stage export missing |
| Rule baseline | `survsim/eval/rules.py` | Have |
| Fusion with correlated nuisance | `survsim/eval/fusion.py` | Have |
| RF, audio, thermal | `survsim/sensors/{rf,audio,thermal}.py` | Have |
| Radar, fence/DAS, wildlife | no occurrence of `radar`, `wildlife`, `fox`, `deer` in `survsim/**/*.py` | **Missing** (M8) |
| Imaging chain + realism stats | `sensors/degrade.py`, `sensors/lens.py`, `realism/compare.py`, CLI `survsim realism` | Have |
| `observed_by` | `director/world.py` l.406, only in the `appearance_change` sensor-log record | Partial |
| `t_detectable_from` | no occurrence anywhere in `survsim/` | **Missing** (M6) |
| Dataset/baseline harness | `datasets/build.py`, `baselines/{run,metrics,bytetrack}.py`, CLI `dataset`, `baseline` | Have |
| Video + RTSP command | `gt/video.py`, CLI `video` | Partial: server not launched |
| Rig / coverage | `director/rig.py`, CLI `rig` | Have |
| Scenario generator | `generator/{spec,site,place,compose,narrative,batch}.py`, CLI `generate` | Have (`generator/layout.py` is now tracked in git) |
| Gait signature | `gait/{signature,cadence,extract,synthesis,casia}.py` | Have |
| Operator model | nothing in `eval/` or `director/` | **Missing** (M9) |
| Scenario configs | `configs/scenarios/`: `smoke_mock`, `disguise_and_tamper` (126 lines), `street_crowd` (67), `plaza_event_crowd` (52), `border_fence_night_probe` (39), `street_crowd_far` (81) | 3 of docs/03 §5's six templates have no config yet: `transit_station_rush`, `corporate_lobby_afterhours` and `car_park_multilevel` |

`tests/` holds 59 `test_*.py` files with 728 `def test_` functions (grep, 2026-09-26); docs/11's "626 tests passing" headline is older than the current tree and was not re-run for this audit. [staleness sweep: current is 881 collected / 859 selected at `94145fa`]

---

### 9. Worked walk-throughs on our own scenarios

#### 9.1 `disguise_and_tamper` (mock, 240 s, 10 fps, seed 11)

The config sets up a compound with the following elements:
- `zone.gate_A`
- a restricted `zone.substation`, with `allowed_roles: [worker, guard]`
- the `zone.fence_north` perimeter
- `zone.blindspot_A`, verified blind by `survsim rig`, where the outfit change happens
- a cuttable panel, `fence_seg_12`
- a PTZ camera on patrol
- a tamper that blinds one camera mid-run
- hard negatives that dwell exactly as long as the loiterer

**Commands for the M1 funnel acceptance:**
```bash
source .venv/bin/activate
survsim validate configs/scenarios/disguise_and_tamper.yaml
survsim rig      configs/scenarios/disguise_and_tamper.yaml --out out/dt/rig
survsim run      configs/scenarios/disguise_and_tamper.yaml --out out/dt/run
survsim events   out/dt/run
survsim eval     out/dt/run --threshold-s 25
```
M1 adds a new option, `survsim eval ... --funnel out/dt/funnel.json`. It writes
`{candidates, tp, fp, pd, fa_per_cam_h}` for each stage: threshold, context,
persistence, corroboration and budget.

The funnel should pass these checks:
- The intrusion into `zone.substation` must survive the context stage, because
  the intruder's role is not in `allowed_roles`.
- The dwell-matched hard negatives must be removed by persistence or context.
  If they die at the *threshold*, the score is separating them by itself —
  a confound, and the confound audit (`director/evasion.py`) must run.

**M6 on the same run:**
- `t_detectable_from[cam]` for the loiter is the first time the loiterer has
  been `usably_visible` in that camera for the dwell threshold.
- The blinded camera has no detectable-from time after the tamper (principle 2).
  The event can only be credited to a camera-health alarm or to a neighbouring
  camera. The eval must treat an alarm on the blinded stream as impossible,
  not as a miss.

**Cross-epoch ReID (M7):** `reid_by_epoch` reports within-epoch and cross-epoch
rank-1 separately. If cross-epoch is *not* lower, the outfit change is
invisible to the embedding. The likely cause is that clothing is painted onto
three baked bodies, so body shape carries identity.

#### 9.2 `street_crowd` (render demo, 60 s, 10 fps, seed 7)

The scene has 18 people around a hero pair: a loiterer and a `commute_wait`
hard negative. Three cameras are mounted 3.5–5 m high, 15–30° down, with
70–95° HFOV, so people are 60–200 px tall. This scene is the source of
docs/15's `out/batch_v1/street_crowd_day/render/cam_02` realism figures.

**Commands for M2:**
```bash
survsim export  out/sc/run            # Unreal manifest (cli.py:export_unreal)
python tools/render_run.py ...        # editor job per camera; see docs/12 for args
python scripts/check_render.py ...    # render gate
survsim dataset configs/scenarios/street_crowd.yaml --seeds 3 \
    --frames-dir out/renders --profile cctv_day_720p --out out/ds_sc
survsim baseline out/ds_sc --task all
python -m survsim.realism compare --real ~/data/real_cctv \
    --synthetic out/renders/street_crowd/cam_02 --profiles cctv_day_720p,cctv_legacy_sd
```

**Budget [BOE]:** 3 seeds × 3 cameras × 600 frames = 5,400 frames.
- Rendering: about 8 min at ~11 frames/s.
- Degradation: about 51 min single-process at 0.567 s/frame. Run it in the background.

**Limitation:** `street_crowd` people are 60–200 px tall, so the 20–60 px bucket
that report 18 says decides products is empty. `configs/scenarios/street_crowd_far.yaml` (81 lines) now exists for this (far cameras; exact mount geometry [unverified] here).

**What to watch:** batch_v4 already gave yolov8n recall 0.758 on 770 GT boxes.
The M2 number to watch is AP75 against MOT20's 0.293. Mask-derived tight boxes
can inflate AP75 against hand-labelled real boxes. If synthetic AP75 is far
above real, check the box convention before claiming realism.

#### 9.3 `border_fence_night_probe` (for M5 and M8)

This config exists (39 lines), but the sensors it needs do not yet: radar,
fence/DAS and wildlife negatives. It is the natural acceptance scenario for M8.
Until M5 lands, its night profile is unmeasured, so every output from it is
labelled synthetic-only.

---

### 10. Interfaces and files per milestone

| M | New/changed files | Interface |
|---|---|---|
| M1 | `baselines/bytetrack.py`, `eval/tracking.py`, `eval/pipeline.py`, `datasets/build.py`, `tests/test_tracking_trackeval_parity.py` | `evaluate_mot` signature unchanged; `pipeline` gains `funnel_out: Path \| None`; manifest gains `survsim_commit`, `content_sha256`, `profile_params` |
| M2 | `configs/scenarios/street_crowd_far.yaml` (exists); docs/13 rows | reuses `dataset` / `baseline` |
| M3 | `tools/hil/serve.py` (mediamtx over `gt/video.rtsp_command`), `tools/hil/ref_pipeline.py`, `survsim/eval/bus_score.py` | MQTT `survsim/{site}/{cam}/det`, `.../tracklet`, `survsim/{site}/alarm`; JSON payloads per report 17 §3, each with `utc_ns`, `pts`, `producer{name,ver}` |
| M4 | `tools/train/tstr.py`; docs/13 TSTR section | train manifests cite dataset `content_sha256` |
| M5 | `sensors/degrade.py` (monochrome-aware grain, illuminator falloff, near-lens particles); IR band in `tests/test_realism_stats.py` | new `Profile` fields `ir_illuminator_range_m`, `particle_rate` |
| M6 | `director/world.py`, `gt/writers.py` | events.jsonl gains `t_detectable_from: {cam: t}` and `observed_by: {cam: [[t0, t1], ...]}`, both computed with `geometry.usably_visible` only (principle 5) |
| M7 | `scripts/ue/*` bake scripts, `export/outfits.py` | `identities.parquet` gains `body_id`, so splits can hold bodies out |
| M8 | `sensors/radar.py`, `sensors/fence.py`, `director/wildlife.py` | sensor-log rows `{t, sensor: radar\|fence, ...}` like rf/audio; shared `environment.wind_ms` |
| M9 | `eval/operator.py` | `Operator(accuracy, latency_s, fatigue_half_life_min).dispose(alarm) -> Disposition` |
| M10 | `eval/odd.py`, `tools/report/coverage_report.py` | ODD YAML `axes: {cam_height_m: [3, 12], px_height: [20, 200], lighting: [...]}` → per-cell metrics JSON → HTML |
| M11 | `sensors/degrade.py` | API unchanged; parity fixture re-justified |

---

### 11. Effort estimates [INF]

| M | Engineer-weeks | Confidence | Main uncertainty |
|---|---|---|---|
| M1 | 1.5–2 | high | TrackEval format adapters |
| M2 | 2–3 | medium | render-gate failures on new scenes |
| M3 | 3 | medium | DeepStream on the laptop GPU is unrepresentative; use a PyAV+ONNX reference |
| M4 | 3–4 | medium | commercially usable real data (§5 licence risk) |
| M5 | 1.5–2 | low | sourcing licensed real IR frames |
| M6 | 2–3 | medium | mock trajectories may fail validation and force a planner change |
| M7 | 4+ | low | engine-bound; wardrobe API still [A] |
| M8 | 3 | medium | radar validation data |
| M9 | 1.5–2 | high | pure Python |
| M10 | 3 | medium | whether a real buyer accepts the report format |
| M11 | 1 | high | profiling already done (docs/15) |
| **Total** | **~27–33** | | about one engineer for 7 months, or two for the 20 weeks in §4 |

---

### 12. Master checklist — what SurvSim must emit (reports 17–22)

| # | Requirement (source) | Module(s) | State |
|---|---|---|---|
| 1 | Per-camera video, timing sidecars, clock offset/drift (17 §3.1) | `gt/video.py`, `director/world.py` | Have |
| 2 | ONVIF-style analytics metadata (17 §4.2) | `gt/video.py` | Have (not yet validated against a VMS) |
| 3 | Stream faults: drop, freeze, packet-loss corruption (17 §8; 20 §2.4) | `sensors/degrade.py`, `director/camera_director.py` | Partial (no packet loss) |
| 4 | Per-frame IQA sidecar (17 §3.2; 22 §4) | `realism/` stats | Partial (offline only) |
| 5 | Mask-derived visible/amodal boxes, visibility (18 §1.7) | `backends/unreal`, `gt/writers.py` | Have |
| 6 | COCO with keypoints (18 §1.6) | `gt/coco.py` | Have |
| 7 | MOTChallenge GT with ignore classes (18 §2.4) | `gt/writers.py`, `eval/motchallenge.py` | Have |
| 8 | Occlusion events: who occluded whom (18 §2.4) | — | Missing |
| 9 | PTZ state and shake per frame (18 §5) | `director/camera_director.py` | Have (PTZ); shake Partial |
| 10 | Configured vs actual pose after tamper (18 §4.4; 20 §3.3) | `director/camera_director.py` | Have |
| 11 | Commissioning-noise survey points (18 §4.4) | — | Missing |
| 12 | Global identities and appearance epochs (18 §3.3) | `core/appearance.py`, `gt/writers.py` | Have |
| 13 | Body id per identity for held-out-body splits (21 §1.1) | `export/outfits.py` | Missing (M7) |
| 14 | Gait parameters per identity (18 §3.3) | `gait/signature.py` | Have |
| 15 | Hard-negative objects: mannequins, posters, reflections (18 §1.7) | — | Missing |
| 16 | Path labels, severity, difficulty, `hard_negative_for` (19 §7.1) | `director/behaviours.py`, `gt/writers.py` | Have |
| 17 | `t_detectable_from` per camera (19 §5.1) | — | Missing (M6) |
| 18 | `observed_by` intervals for every event (19 §7.1) | `director/world.py` | Partial (appearance changes only) |
| 19 | Head yaw / gaze proxy per tick (19 §11) | `director/world.py` | Unconfirmed — check `world.parquet` columns |
| 20 | Context feeds: schedules, rosters, access control (19 §7.3) | sensor extras in `director/world.py` | Partial |
| 21 | Per-stage alarm funnel (19 §10) | `eval/pipeline.py` | Partial (M1) |
| 22 | Crowd density that counts occluded people (19 §6) | `director/crowd.py` | Have (bug 13 fixed) |
| 23 | Night/IR with illuminator and near-lens particles (20 §2.1) | `sensors/degrade.py` | Partial (M5) |
| 24 | Thermal with resolution limit (20 §2.2) | `sensors/thermal.py` | Have |
| 25 | Weather as a cause shared across sensors (20 §6.1) | `director/environment.py` | Partial |
| 26 | RF with MAC randomisation (20 §4.1) | `sensors/rf.py` | Have |
| 27 | Audio: SPL, DOA error, nuisance sources (20 §4.4) | `sensors/audio.py` | Have |
| 28 | Radar and fence/DAS (20 §4.2–4.3) | — | Missing (M8) |
| 29 | Wildlife agents (20 §8) | — | Missing (M8) |
| 30 | Splits with manifests and content hashes (21 §1) | `datasets/build.py` | Partial (seed splits; hashes in M1) |
| 31 | Operator dispositions (21 §3.4) | — | Missing (M9) |
| 32 | ODD coverage report (21 §10) | `generator/` stratification | Partial (M10) |
| 33 | Live RTSP for pipeline-in-the-loop (22 §2.4) | `gt/video.py` | Partial (M3) |
| 34 | Latency ground truth, detectable → alarm (17 §5) | bus scorer | Missing (M3) |

**Tally:** 14 Have, 10 Partial, 9 Missing, 1 unconfirmed.
- Six of the Missing items are scheduled: #17 (M6), #28 and #29 (M8), #31 (M9),
  #34 (M3) and #13 (M7).
- The other three (#8, #11, #15) are small and can be picked up opportunistically.

---

### References

1. Dendorfer, P. et al. "MOT20: A benchmark for multi object tracking in crowded scenes." arXiv:2003.09003 (2020). https://arxiv.org/abs/2003.09003. Data and licence (CC BY-NC-SA 3.0): https://motchallenge.net/data/MOT20/ — verified.
2. Luiten, J. & Hoffhues, A. *TrackEval*: HOTA, CLEAR and Identity metrics; MIT licence. https://github.com/JonathonLuiten/TrackEval — verified.
3. bluenviron. *MediaMTX*, a live media server and proxy (RTSP, RTMP, HLS, WebRTC, SRT). https://github.com/bluenviron/mediamtx — verified.
4. Luiten, J. et al. "HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking." IJCV (2021). https://arxiv.org/abs/2009.07976
5. Pellegrini, S. et al. "You'll never walk alone" (ETH), ICCV 2009; Lerner, A., Chrysanthou, Y., Lischinski, D. "Crowds by Example" (UCY), Computer Graphics Forum 2007. Standard trajectory benchmark pair; cited from memory, not fetched.
6. Robicquet, A., Sadeghian, A., Alahi, A., Savarese, S. "Learning Social Etiquette: Human Trajectory Prediction in Crowded Scenes." ECCV 2016. Stanford Drone Dataset, CC BY-NC-SA 3.0. https://cvgl.stanford.edu/projects/uav_data/ — verified.
7. Cheng, M., Cai, K., Li, M. "RWF-2000: An Open Large Scale Video Database for Violence Detection." ICPR 2020. https://arxiv.org/abs/1911.05913 — verified (2,000 clips; 87.25 % accuracy).
8. Kwolek, B. & Kepski, M. "Human fall detection on embedded platform using depth maps and wireless accelerometer." *Computer Methods and Programs in Biomedicine* 117(3), 2014. UR Fall Detection Dataset: 70 sequences (30 falls, 40 daily-living activities), CC BY-NC-SA 4.0. https://fenix.ur.edu.pl/~mkepski/ds/uf.html — verified.

---

### Sources (in-repo)

In-repo: CLAUDE.md, docs/02, docs/03, docs/11, docs/12, docs/13, docs/14,
docs/15; research 17–22 (this series), R01–R05, D04, D07, D08. External sources
are cited in reports 17–22.
