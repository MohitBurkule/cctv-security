# 58 · Loiter rule redesign against the H12 alarm budget

H12 (docs/research/32 §H12) measured every shipped loiter rule on 3,002 clean
mock camera-hours: dwell_60 4.55 FA/cam-h (recall 0.16), dwell_25 6.01
(recall 0.90), path_loiter_25 20.7, path_loiter_15 87.4, against a budget of
0.001. This report pre-registers a redesign, then reports it on the *same*
worlds. Code: `survsim/eval/rules.py`, `survsim/eval/loiter_features.py`,
`tools/loiter_eval.py`. Outputs: `out/experiments/h58_loiter_redesign/`.

## 1. Pre-registration (written and committed before any candidate was scored)

```
id:            h58_loiter_redesign
commit:        the commit that adds this section (quoted in §3)
hypothesis:    A loiter detector built from track kinematics + zone semantics
               reaches <= 0.0455 FA/cam-h (100x below dwell_60, the lowest H12
               rate; 60 FA/1,000 cam-h [sic: 45.5 FA/1,000 cam-h — audit erratum, threshold unchanged]) on the H12 clean worlds while keeping
               recall >= 0.80 at the 30 s tolerance on the H12 recall worlds.
my prior:      FAIL. Mechanism read before any run: `SmokeBreak` subclasses
               `Loiter` (pace, radius 3 m, 0.35x speed) and H12 places ~half
               of smoke breaks in gate zones - where `loiter_arc` loiters. For
               the first 30 s (the scoring window) such an episode is the
               *same generating process* as a loiter. Predicted floor
               ~ 1 FA/cam-h (order of magnitude), i.e. ~5x better than
               dwell_60, not 100x. Idle waits (commute_wait, queue, phone_stop)
               should be separable from pacing by speed; transit by displacement.
primary metric: FA/cam-h, default scoring (not ilids_compat), tolerance 30 s,
               676 H12 clean worlds (3,002 cam-h), Garwood 95 % CI.
constraint:    recall at 30 s, default scoring, 360 events in the 300 H12
               recall worlds, world-bootstrap 95 % CI; point >= 0.80.
secondary:     precision at the operating point on the recall worlds; ilids_compat
               numbers; 10 s tolerance recall; raw alarms by archetype.
arms:          control = H12's dwell_25 / dwell_60 / path_loiter_25 (recomputed on
               the regenerated tracks; must reproduce H12 exactly).
               C1 ZoneDwellRule - DwellRule + exempt zone tags (queue) and
                  allowed-roles exemption.
               C2 DisplacementLoiterRule - clock resets whenever net displacement
                  over the last W s exceeds R (not after 15 s of movement); fires
                  after T s with a stationary-fraction band [f_lo, f_hi] and an
                  optional zone-tag gate.
               C3 RevisitRule - >= k returns to within R of an earlier position
                  after having left it by > R_out, inside a horizon H.
               C4 learned - logistic regression (numpy IRLS; sklearn is not in
                  the venv) on hand features per person per 1 s tick: dwell
                  clock, net displacement 10/30 s, path length, straightness,
                  mean speed, speed std, stationary fraction, heading entropy,
                  turn rate, zone tag one-hot, group size (others within 2 m),
                  distance to nearest entrance. Fires once per dwell episode
                  when p > theta.
               C5 combinations (C4 gated by C2 / zone).
forbidden features (simulation artefacts that would not exist on real CCTV):
               behaviour label, archetype, uid, role, absolute time / time-of-day
               (mock has none), distance to the zone *centroid* (loiter_arc walks
               to the exact centroid while innocent points are jittered - a pure
               generator leak). Distance-to-entrance is allowed but ablated.
training data: a DISJOINT split - seed 58 (recall worlds seed 59): 150 clean
               worlds + 300 recall worlds, same recipe (alarm_scale imported).
               H12 used seeds 12/13.
selection:     every hyper-parameter and theta is chosen on the train split only:
               minimise train clean FA/cam-h subject to train recall(30 s) >= 0.85
               (margin for transfer). The candidate with the lowest train FA rate
               meeting that constraint is "the shipped rule", fixed before the
               H12 evaluation runs. H12 is scored once; all candidates are
               reported, claims are only about the shipped rule (no multiplicity).
ceiling:       (a) label oracle: alarm at the start of each Director
               `suspicious.loiter` episode - 0 FA on clean worlds by construction;
               (b) kinematic-twin floor: rate of clean episodes whose generating
               process equals Loiter's (SmokeBreak in the zone tags loiter uses)
               x the detector's recall - no track-only rule can beat it.
success:       shipped rule Garwood upper <= 0.0455 FA/cam-h AND recall >= 0.80.
partial:       >= 10x below dwell_60 with recall >= 0.80.
stopping rule: fixed worlds (the 676 + 300 H12 worlds, regenerated
               deterministically; a world whose dwell_25 alarms differ from
               H12's worlds.jsonl is a reproduction failure and is reported).
confounds:     mock kinematics are not real dwell distributions; loiter
               durations (25-90 s) and archetype mix are the generator's; the
               recall set contains 60 disguise_swap 'scan' loiters that are idle
               (speed 0) for 10-36 s - kinematically a commute wait.
abandon if:    no candidate reaches recall 0.85 on train at any setting.
```

## 2. What was run

* **Reproduction.** All 976 H12 worlds (676 clean, 3,002.0 cam-h; 300 recall,
  360 loiter events) were regenerated from their seeds with `alarm_scale`'s
  own recipe; **0 of 976** differ from H12's cached dwell_25 alarm times, and
  the recomputed dwell_25 / dwell_60 / path_loiter_25 rows below equal H12's
  to the alarm. Tracks cached in `out/experiments/h58_loiter_redesign/tracks/`.
* **Training split** (seed 58/59): 150 clean worlds + 300 recall worlds,
  3.29 M tick rows, 10,250 positive ticks. Grid: 192 C2 settings, 36 C3,
  12 C1 (+3 baselines), 81 C4 (3 feature sets × 9 θ × 3 min-clock), 27 C4∧C2
  and 25 C2∧C3 (C5). Wall 10 min.
  *[Audit correction 2026-09-27, `selection.json` grid: 294 candidates were
  scored — **144** C2 (4 T × 4 stat-ceilings × 3 moving-floors × 3 gates, not
  192), 36 C3, **6** C1 (3 thresholds × ±wait zones, not 12; the 3 H12
  baselines were not in the train grid), 81 C4, 27 C4∧C2 and **0** C2∧C3 —
  the C2∧C3 step combines only C2/C3 settings reaching train recall 0.85 and
  no C3 did (best 0.797).]*
* **Selection on train** (constraint recall ≥ 0.85): shipped =
  `LearnedLoiterRule` on all features except distance-to-entrance, θ = 0.95,
  min clock 5 s (train 3.00 FA/cam-h, recall 0.883). C3 (revisit) never
  reached recall 0.80 on train at any setting — the 60 idle 'scan' loiters
  and short pacing loiters don't oscillate enough in 30 s — so it is out.
* **One H12 evaluation** (`tools/loiter_eval.py eval`), after the selection
  was written.

## 3. Results on the H12 worlds (pre-registration commit `0c0976f`)

Default scoring, 30 s tolerance unless stated; clean FA over 3,002 cam-h;
recall/precision on the 300 recall worlds (360 events), world bootstrap.

| rule | FA/cam-h [Garwood 95 %] | × our assumed budget | recall@30 [95 %] | precision@30 [95 %] | recall@10 | ilids FA/cam-h | top clean causes |
|---|---|---|---|---|---|---|---|
| dwell_25 (H12) | 6.007 [5.920, 6.095] | 6,007 | 0.900 [0.868, 0.928] | 0.182 [0.171, 0.195] | 0.125 | 5.44 | commute_wait 9.6k, queue 6.8k |
| dwell_60 (H12) | 4.552 [4.476, 4.629] | 4,552 | 0.156 [0.120, 0.193] | 0.067 | 0.056 | 4.22 | commute_wait 8.0k, queue 5.1k |
| path_loiter_25 (H12) | 20.65 [20.49, 20.81] | 20,651 | 0.942 [0.917, 0.963] | 0.048 | 0.364 | 15.2 | transit 19.2k |
| C1 zone-dwell 25 + wait zones | 5.717 [5.632, 5.803] | 5,717 | 0.872 [0.834, 0.906] | 0.178 | 0.125 | 5.18 | commute_wait 13.5k |
| C1 zone-dwell 60 + wait zones | 4.360 [4.286, 4.435] | 4,360 | 0.156 | 0.067 | 0.056 | 4.04 | commute_wait 10.7k |
| C2 displacement clock T15, gate | 8.944 [8.837, 9.051] | 8,944 | 0.872 [0.840, 0.905] | 0.170 | 0.211 | 7.82 | commute 10.0k, smoke 9.9k |
| C5 logit ∧ C2 | 6.775 [6.682, 6.869] | 6,775 | 0.864 [0.831, 0.898] | 0.182 | 0.208 | 6.11 | smoke 7.6k, commute 7.2k |
| **C4 logistic (shipped)** | **2.915 [2.854, 2.977]** | **2,915** | **0.867 [0.835, 0.900]** | **0.331 [0.308, 0.357]** | 0.472 | 2.77 | smoke 3.6k, queue 2.8k, commute 2.3k, transit 20 |
| label oracle (ceiling a) | 0 [0, 0.0012] | 0 | 0.903 | 0.903 | 0.933 | 0 | — |
| kinematic-twin floor (ceiling b) | ≥ 1.008 [0.973, 1.045] × recall | ≥ 1,008 × recall | — | — | — | — | smoke breaks pacing in gate zones |

World-cluster bootstrap for the shipped rule: 2.76–3.06 FA/cam-h. Its train
numbers (3.00, 0.883) transferred to H12 (2.92, 0.867) without drift.
Distance-to-entrance ablation: the no-entrance model beat the all-feature
model on train (3.001 vs 3.008 FA/cam-h at the same θ/clock — a tie, not
evidence the feature hurts), so the shipped rule does not use it. C4's learned weights
put nearly all the mass on stationary/moving fractions and the gate tag.

**Verdict against the pre-registration: FAIL, as predicted.** The shipped
rule is 1.56× below dwell_60 and 2.06× below dwell_25 at comparable recall
(0.867 vs 0.900) — not 100×, not even the 10× "partial". Precision at the
operating point rises 0.182 → 0.331 (0.583 ilids_compat).

**Before → after:** dwell_25 6.01 → 2.92 FA/cam-h (recall 0.900 → 0.867);
the most comparable-recall H12 rule is dwell_25, dwell_60 has recall 0.16.

## 4. Why: the ceiling

* **Label oracle (a) = 0 FA** by construction, and its recall is only
  **0.903**, not 1.0: `alarms.score` matches alarms actor-blind, so when two
  loiter events (the disguise_swap scan and the plain loiter) start within
  30 s of each other one alarm is credited to the earlier event and the second
  alarm becomes a repeat. That is a scorer property worth knowing: 0.90 is the
  best recall any rule can get on this set. The shipped rule's 0.867 is 96 %
  of attainable.
* **Kinematic twins (b).** Of the 33,904 dwell-type hard-negative episodes in
  the clean worlds (commute_wait 3.81/cam-h, phone_stop 2.50, queue 2.49,
  smoke_break 2.50), **3,027 smoke breaks pace in gate zones = 1.008 FA/cam-h
  [0.973, 1.045]**. `SmokeBreak` *is* `Loiter` (same 3 m pacing at 0.35×
  speed) placed where `loiter_arc` loiters; within the 30 s scoring window no
  track-only detector can tell them apart. Any rule with recall r on paced
  gate loiters pays ≈ r × 1.0 FA/cam-h — **~1,000× our assumed budget is the floor**,
  and 100× (0.0455) is unattainable on these worlds by construction. The
  simulation's own hard-negative rate (label-blind, motion-only) is therefore
  ~1 FA/cam-h; with durations and zone mix taken as given.
* **The gap between the shipped rule (2.92) and the floor (~0.87).** 5.1k of
  its 8.8k clean alarms are idle queue/commute waits in gate zones. They are
  the price of the 60 idle 'scan' loiters (disguise_swap, 17 % of events):
  standing still at a gate for 10–36 s is a commute wait kinematically. A
  pacing-only rule drops them and misses the 0.85 train-recall constraint
  (C3 peaks at 0.797; C2 with a stationary ceiling ≤ 0.5 peaks at 0.828 —
  *audit correction: previously "under 0.80" for both*). Repeat alarms on long smoke breaks
  (3,570 alarms on 3,027 gate episodes) are a smaller share.
* C1's zone semantics barely move the needle (6.01 → 5.72) because the
  generator puts commute waits and queues mostly in *gate*-tagged entrance
  zones (9,706 + 6,776 episodes), not in `queue` zones — exempting gates
  would exempt the loiterers too. Zone tagging only helps if the site map
  separates "where people wait" from "where people shouldn't".
* C2 fixes the H12 path-loiter bug completely (transit alarms 19,240 → 0 in
  C2; 20 in C4) but a clean displacement clock alone is a dwell timer: 8.9
  FA/cam-h.

## 5. What it means for a product

*Superseded in part by §6: round-1 recall figures here are window-only
scoring. Actor-aware (§6.2) the learned rule's 10 s recall is 0.097 (not
0.47) and dwell_25's is 0.000 (not 0.13); quote §6.2 numbers.*

* **Ship** `LearnedLoiterRule` (C4) over `DwellRule(25)` if you ship one:
  half the nuisance rate at the same recall, double the precision, and
  4× the 10 s-tolerance recall (0.47 vs 0.13) because it does not wait for a
  fixed dwell. Ship `DisplacementLoiterRule`'s clock as the dwell primitive in
  any rule; `PathLoiterRule` should be retired (transit false alarms).
* **Remaining gap to 0.001: ~2,900×** (Garwood lower 2,854×); ~870× even at
  the kinematic floor. No motion rule closes it. A loiter "alarm" at estate
  scale can only be a ranked *review queue* (report 51) or needs context the
  track does not contain: time-of-day / timetable (a platform wait at train
  time), identity dwell history across days (the same person at the same gate
  daily), gaze/orientation at targets (recon vs smoke), carried objects, and
  per-site learned priors on where waiting is normal.
* **Real data needed:** (1) dwell-duration and pacing-kinematics
  distributions per zone type from real sites (our 25–90 s loiter vs
  60–360 s smoke break vs 20–240 s commute are my generator's choices and
  set the floor); (2) a labelled set of real loitering incidents with timing,
  to know whether real loiterers pace or stand; (3) ≥ 3,000 real soak
  camera-hours per site class to certify any rate near budget (49 §5).
* **Simulator fixes this exposed:** `loiter_arc` walks to the exact zone
  centroid while innocents are jittered (a leak the forbidden-feature list
  had to exclude); `alarms.score` is actor-blind, capping recall at 0.90 on
  overlapping events.

Commits: pre-registration `0c0976f`; rules/features/tool `e750ba8`; results
(this section) follow.

## 6. Round 2 after simulator fixes

### 6.1 Pre-registration (2026-09-27, written before any round-2 number was seen)

Commit `473ace3` changed the Director: `Loiter.begin` (and so `CommuteWait`,
`SmokeBreak`, every `loiter_arc`) now samples its dwell point with
`world.sample_goal` jitter instead of the exact zone centroid. That changes
the *geometry* of every loiter and every dwell-type hard negative, so the §3
numbers no longer describe the current simulator. Round 2 re-runs them.

**Data.** Regenerate with the fixed Director (same `alarm_scale` recipe, same
seeds): H12 split (seed 12: 676 clean worlds ≈ 3,002 cam-h, 300 recall worlds
≈ 360 loiter events) and train split (seed 58/59: 150 clean + 300 recall).
Written to `out/experiments/h58_round2` (`H58_OUT`), round 1 kept intact.

**Rules scored on H12** (nothing tuned on H12):
1. `dwell_25`, `dwell_60` (H12 baselines, unchanged).
2. C2 displacement clock with the round-1 selected spec frozen
   (`T15, stat<=1.0, mov>=0.0, gate`).
3. C4 `LearnedLoiterRule` **retrained** on the regenerated train split with the
   round-1 shipped feature set (all `FEATURES` minus `dist_entrance`; there is
   no zone-centre-distance feature in `loiter_features` — the leak was only
   ever excluded, never a feature), same θ × min-clock grid, same selection
   (lowest train FA/cam-h with train recall@30 ≥ 0.85, window-only scoring).
4. Diagnostic: C4 with the round-1 weights frozen.
5. Label oracle (ceiling a) and the kinematic-twin floor (ceiling b: clean
   `SmokeBreak` episodes whose first dwell tick is in a gate zone, Garwood CI).

**Scoring.** Every rule now emits `Alarm.uid`. Each is scored twice: window-only
(as round 1) and `actor_aware=True`. 30 s tolerance default mode is primary;
FA/cam-h with Garwood 95 %, recall and precision with world bootstrap 95 %.

**Predictions.**
* P1: `actor_aware` lifts the oracle's recall from ≈ 0.90 to 1.00 and lifts
  every rule's recall by a similar few points; FA/cam-h are unchanged by it
  (it only reassigns hits; an alarm that loses its match to actor mismatch
  becomes a FA only if its person is not an actor of any in-window event).
* P2: dwell_25 / dwell_60 move by < 10 % (they never saw the centroid).
* P3: if the exact-centroid leak was helping C4 (e.g. via `tag_*` or
  near-zero-spread pacing at a fixed point), its margin over dwell_25
  (2.06× in round 1) shrinks. If it shrinks below 1.5× we say so and the
  shipping recommendation is re-examined; if it holds, the round-1 verdict
  stands.
* P4: the twin floor stays ≈ 1.0 FA/cam-h (durations and zone mix unchanged).

### 6.2 Results (regenerated with the fixed Director; `tools/loiter_eval.py round2`)

Regeneration: **0/676 clean** H12 worlds (and 0/150 train clean worlds)
differ from round 1 in their dwell_25 alarm times; **230/300 H12 recall
worlds differ**, and 237/300 train recall worlds. *(Audit correction: this
line previously said "0/450 train"; the generator's mismatch check has no
reference for the train split, so its "0 mismatches" there compared nothing.
Recounted from `tracks/*/*.json` of both rounds.)* The fix only
moved `loiter_arc` loiterers — the clean hard negatives in the `alarm_scale`
recipe were already jittered — so every clean FA count below is identical to
round 1, and all movement is in recall. Train refit selected θ = 0.9,
min-clock 10 s (train 3.95 FA/cam-h, recall 0.858; round 1 on train: 3.00,
0.883).

30 s tolerance, default mode, 3,002 clean cam-h (Garwood 95 %), 360 events
(world bootstrap 95 %).

| rule | FA/cam-h [Garwood] | recall window-only | recall actor-aware | precision actor-aware | recall@10 actor-aware |
|---|---|---|---|---|---|
| dwell_25 | 6.007 [5.920, 6.095] | 0.733 [0.686, 0.777] (r1 0.900) | **0.367** [0.319, 0.414] | 0.080 | 0.000 |
| dwell_60 | 4.552 [4.476, 4.629] | 0.156 (r1 0.156) | **0.000** | 0.000 | 0.000 |
| C2 disp. clock T15 gate (r1 spec) | 8.944 [8.837, 9.051] | 0.839 (r1 0.872) | 0.775 [0.730, 0.817] | 0.154 | 0.006 |
| **C4 retrained (round 2, shipped)** | **3.745 [3.676, 3.815]** | 0.853 [0.818, 0.887] | **0.831 [0.792, 0.869]** | **0.326 [0.304, 0.352]** | 0.097 |
| C4 round-1 weights (diagnostic) | 2.915 [2.854, 2.977] | 0.831 [0.796, 0.868] (r1 0.867) | 0.825 [0.789, 0.862] | 0.329 | 0.242 |
| label oracle | 0 [0, 0.001] | 0.903 | **1.000** | 1.000 | 1.000 |
| twin floor (smoke breaks in gate zones) | 1.008 [0.973, 1.045] × recall | — | — | — | — |

Against the predictions:
* **P1 half-right.** `actor_aware` lifts the oracle 0.903 → 1.000 as
  designed, and FA/cam-h are unchanged, but it *lowers* every real rule's
  recall. The window-only scorer had been crediting alarms on **bystanders**
  that happened to fall in a loiter event's 30 s window. dwell_60 cannot fire
  on the actor within 30 s of onset, and actor-aware shows all of its 0.156
  "recall" was bystanders; half of dwell_25's (0.733 → 0.367) was too, and
  none of its 10 s hits are real. The learned rule loses only 0.02 — its hits
  are on the right person. **Actor-aware is the honest number; window-only
  recall for dwell rules should not be quoted again.**
* **P2 half-right.** Dwell FA is unchanged (clean worlds unchanged), but
  dwell_25 window-only recall fell 0.900 → 0.733: at the exact centroid the
  loiterer stood where the generator puts gate waits, so the leak was helping
  the *dwell* rule too.
* **P3: the margin shrank, as flagged in the pre-registration.** Retrained C4
  vs dwell_25 on FA: 6.007 / 3.745 = **1.60×** (round 1: 2.06×), above the
  1.5× line. The refit is worse already on its own train split (3.95 vs
  round 1's 3.00 FA/cam-h; both transfer to H12 slightly *better* than
  train: 3.95 → 3.75, 3.00 → 2.92), and the frozen round-1 weights do better
  on the new worlds (2.92 at recall 0.825), so the round-1 fit was not
  dependent on the leak. Why the refit is worse is not tested: the θ choice
  moved (0.95 → 0.9) *and* 237/300 train recall worlds changed. On the honest
  (actor-aware) metric the margin *widened*: C4 has 2.3× the recall of
  dwell_25 at 0.62× its false-alarm rate, and 4× the precision.
* **P4 holds exactly** (1.008 FA/cam-h; clean worlds are identical).

**Verdict.** Ship `LearnedLoiterRule` (retrained, θ = 0.9, clock ≥ 10 s) —
it is the pre-registered round-2 candidate, and the learned family is the
only one whose recall survives actor-aware scoring (the frozen round-1
weights, a diagnostic arm, survive too at lower FA: 2.915 at 0.825 — a
candidate for the next pre-registered round, not a post-hoc swap). The dwell
baselines are worse than round 1 said: dwell_60 detects nothing within 30 s.
The pre-registered FAIL against 0.0455 FA/cam-h stands (~82× the 0.0455 target, ~3,700× the assumed 0.001 operator budget; twin
floor ~840× at recall 0.83: 1.008 × 0.831 = 0.838). Score all loiter rules with `actor_aware=True`
from now on.

## 7. Round 3: arm decision, gradient boosting, calibrated operating curve, value of context

### 7.1 Pre-registration (2026-09-27, written and committed before any round-3 number was computed)

**Data.** No regeneration: the round-2 worlds and feature tables under
`out/experiments/h58_round2` (H12 split: 676 clean worlds = 3,002 clean
cam-h, 300 recall worlds = 360 loiter events; train split: 150 clean + 300
recall, seed 58/59). Round-3 outputs go to `out/experiments/h58_round2/round3_*`
(`tools/loiter_eval.py round3`). **All scoring is `actor_aware=True`**, 30 s
tolerance, default mode — in selection on train as well as on H12 (round 2
selected window-only; that is changed here, before any number). FA/cam-h with
Garwood 95 %, recall and precision with world-bootstrap 95 % (2,000 resamples,
seed 58), as in §6 and docs/research/49.

**Held-out train fold.** Arms (b)–(d) split the 450 train worlds by world,
stratified by mode, with `np.random.default_rng(58)`: 70 % *fit* fold, 30 %
*select* fold (45 clean + 90 recall). Models are fitted on the fit fold only;
θ, min-clock and any calibrator are chosen on the select fold only. Nothing
is tuned on H12. Selection rule (unchanged from rounds 1–2 except for
actor-aware): lowest select-fold FA/cam-h with select-fold recall@30 ≥ 0.85
over θ ∈ {0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999} × min-clock
∈ {5, 10, 15} s.

**Arms.**
* **(a) Logistic arms, named.** `A1` = round-1 `LearnedLoiterRule` weights
  frozen (θ 0.95, clock ≥ 10 s); `A2` = round-2 retrained weights (θ 0.9,
  clock ≥ 10 s). Neither is refitted. *Their H12 numbers were already
  observed in §6.2* (A1 2.915 / 0.825, A2 3.745 / 0.831), so arm (a) is not
  a blind test: it is the formal decision the audit asked for instead of a
  post-hoc swap. Decision rule: ship the arm with lower H12 FA/cam-h among
  those with recall ≥ 0.80; tie (overlapping Garwood intervals *and* equal
  point FA to 3 decimals) → lower FA point estimate. The re-run must
  reproduce §6.2 exactly; any difference is a bug and stops the round.
* **(b) GBM.** `sklearn.ensemble.HistGradientBoostingClassifier` (seed 58,
  `max_iter=300`, `learning_rate=0.1`, `max_leaf_nodes=31`,
  `class_weight="balanced"`, early stopping off), on the same feature set as
  A1/A2 (`FEATURES` minus `dist_entrance`), same tick labels (`pos`,
  `late` ticks dropped), same negative subsample cap (1.5 M, seed 58), fitted
  on the fit fold.
* **(c) Calibrated GBM.** (b) followed by isotonic regression of the tick
  score on the select fold (non-late ticks), so `p` is an estimate of
  P(tick is in the first 30 s of a loiter). Operating point selected on the
  select fold by the same rule on the calibrated scale. On H12 we report
  (i) the tick-level Brier score and 10-bin ECE, (ii) the **operating curve**:
  FA/cam-h [Garwood] and actor-aware recall [bootstrap] and precision at
  θ ∈ {0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95} with the
  select-fold min-clock — descriptive, for a product to pick a point; no arm
  is chosen from it. The same curve is reported for A1 (its own logistic `p`)
  as a reference.
* **(d) Context ablation.** (b)'s pipeline (same fold, hyper-parameters,
  selection) with the Director's zone context added: one-hot of the zone
  *function* under the person (zone id with its `_k` suffix stripped:
  entrance, gateline, platform, reception, lobby, concourse, street, open,
  yard, bays, stage, crowd, fence_line, restricted, blindspot, none) — what a
  site profile ("people wait on the platform, not at the fence") would
  supply. **Time of day is not varied by the `alarm_scale` recipe** (worlds
  carry no clock; the Director's schedule is time-invariant), so its gain is
  0 by construction and is reported as untestable here, not as measured.
  World-elapsed `t` is **not** a substitute: clean worlds last 1,800 s and
  recall worlds 300 s, so `t` is a split label (leak). Person role is also
  excluded (`intruder` exists only in recall worlds). The value of context
  is reported as (i) the H12 FA and recall of (d) vs (b) at their own
  selected points, and (ii) FA at the first θ reaching H12 recall ≥ 0.80 on
  each arm's curve (descriptive).

**Shipping rule.** The (a) winner ships unless a track-only GBM arm ((b) or
(c)) has H12 recall ≥ 0.80 and its Garwood upper bound is below the (a)
winner's Garwood lower bound (a clear win, not noise), in which case the GBM
arm with lower FA ships. (d) is never the shipped generic rule — it needs a
site profile — it measures what one is worth.

**Predictions.**
* P5: A1 ships (known from §6.2); the re-run reproduces 2.915 / 0.825 and
  3.745 / 0.831.
* P6: (b) lands within ±30 % of A1's FA at recall ≥ 0.80 and does not
  clear the shipping bar: with the same track features, the kinematic-twin
  floor (1.008 FA/cam-h, §6.2) bounds any model, and A1 is already ≈ 2.9×
  that floor.
* P7: isotonic calibration transfers — H12 tick ECE < 0.02 — and no θ on
  either curve reaches FA < 1.0 at recall ≥ 0.80 (the twin floor).
* P8: zone-function context lowers FA by ≥ 25 % at the selected operating
  point with recall held ≥ 0.80, and can go below the 1.008 track-only twin
  floor (the twin floor is defined by zone *tag*; function is finer).

### 7.2 Results (`tools/loiter_eval.py round3`, `out/experiments/h58_round2/round3_results.{json,md}`)

H12 worlds, 3,002 clean cam-h (Garwood 95 %), 360 events (world bootstrap
95 %), 30 s tolerance, default mode, **actor-aware**. Nothing tuned on H12.

| arm | θ, clock | FA/cam-h [Garwood 95 %] | recall [95 %] | precision | select-fold FA, recall |
|---|---|---|---|---|---|
| **A1 logistic, round-1 weights frozen (shipped)** | 0.95, ≥ 5 s | **2.915 [2.854, 2.977]** | **0.825 [0.789, 0.862]** | 0.329 | — |
| A2 logistic, round-2 retrained | 0.9, ≥ 10 s | 3.745 [3.676, 3.815] | 0.831 [0.792, 0.869] | 0.326 | — |
| B GBM, track-only | 0.8, ≥ 5 s | 3.114 [3.051, 3.178] | 0.842 [0.807, 0.876] | 0.381 | 3.200, 0.868 |
| C GBM + isotonic, track-only (**deviation**, see below) | 0.5, ≥ 5 s | 0.335 [0.315, 0.357] | 0.553 [0.504, 0.601] | 0.926 | 0.335, 0.566 |
| D GBM + zone-function context (not shippable) | 0.8, ≥ 5 s | 2.468 [2.412, 2.525] | 0.822 [0.786, 0.860] | 0.388 | 2.655, 0.858 |

**Erratum to §7.1.** The pre-registration described A1 as "clock ≥ 10 s".
The frozen round-1 spec (`h58_loiter_redesign/selection.json`) is clock ≥ 5 s.
A1 was run from that file unchanged, so the row above is the round-1 rule as
shipped; only the §7.1 description was wrong.

**Declared deviation: C.** On the select fold, no (θ, clock) in the
pre-registered grid (θ ≥ 0.5) reached recall 0.85 on the calibrated scale.
Isotonic calibration maps the base rate (0.09 % of ticks are positive) to
small probabilities. `_select` fell back to the highest-recall grid point,
which the pre-registration did not specify. C's selected row is therefore
**not** a like-for-like arm and plays no part in the shipping decision. A
calibrated-scale θ grid is a round-4 pre-registration item, not a swap made
now. C's operating curve (below) was specified independently and is
unaffected.

**Operating curves (descriptive, H12, clock ≥ 5 s, actor-aware).** All four
curves finished:

| θ (C, calibrated) | FA/cam-h | recall |
|---|---|---|
| 0.05 | 2.765 | 0.831 |
| 0.1 | 1.951 | 0.803 |
| 0.2 | 1.412 | 0.789 |
| 0.3 | 1.050 | 0.772 |
| 0.4 | 0.769 | 0.736 |
| 0.5 | 0.335 | 0.553 |
| 0.7 | 0.060 | 0.256 |

Lowest FA with recall ≥ 0.80 on each curve: A1 2.915 (θ 0.95), C 1.951
(θ 0.1), B 2.224 (θ 0.9), D 1.803 (θ 0.9). The C and B points at θ 0.1 / 0.9
are *below* A1, but they were picked on H12 and are not a shipping result;
they are the reason round 4 should select GBM θ on a finer grid. Full curves
with CIs are in `round3_results.md`.

**Calibration (H12 non-late ticks).** Isotonic: Brier 0.0011, 10-bin ECE
0.0018. Uncalibrated GBM (`class_weight="balanced"`): Brier 0.0128, ECE
0.019. Base rate 0.00092.

**Against the predictions.**
* **P5 holds.** A1 and A2 reproduce §6.2 exactly (`reproduces_round2` =
  true for both). The (a) decision rule picks A1: both have recall ≥ 0.80, and
  A1 has the lower FA (2.915 vs 3.745, Garwood intervals disjoint).
* **P6 holds.** B is +6.8 % FA vs A1 at slightly higher recall (0.842). That
  is within ±30 %, and B does not clear the bar (its Garwood upper bound of
  3.178 is not below A1's lower bound of 2.854).
* **P7 holds.** ECE 0.0018 < 0.02. No point on any curve reaches FA < 1.0 at
  recall ≥ 0.80; the lowest is D at 1.803, and among track-only arms C at
  1.951. The 1.008 twin floor was not breached.
* **P8 fails.** Context cuts FA by **20.7 %** at the selected points (3.114
  → 2.468, disjoint Garwood intervals), with recall 0.842 → 0.822. On the
  curves the cut is 19 % (2.224 → 1.803 at recall ≥ 0.80). Both are below
  the predicted ≥ 25 %, and D does not go below the 1.008 floor. Time of day
  is untestable in this recipe (gain 0 by construction). Zone function is
  worth about a fifth of the false alarms here. That is real, but it is not
  the order-of-magnitude step the assumed 0.001 FA/cam-h budget needs.

**Shipped rule: A1** (`LearnedLoiterRule`, round-1 weights, θ 0.95, clock
≥ 5 s). It replaces the round-2 retrained rule under the pre-registered (a)
decision; no GBM arm met the clear-win bar. The pre-registered FAIL against
the budget still stands (2.915 FA/cam-h is ~2,900× our assumed 0.001 operator
budget).

**Round 4 candidates (not run):**
* select calibrated or GBM θ on a finer grid on the select fold (the curves
  suggest about 2.0 FA/cam-h at recall 0.80);
* D's context combined with that selection;
* a recipe that actually varies time of day.

## 8. Round 4: H21 + H23

### 8.1 Pre-registration (2026-09-27, written and committed before any round-4 number was computed)

Both items come from 66 (H21, H23). Same data, metric and scoring as §7:
H12 worlds (3,002 clean cam-h, 360 events), **actor-aware**, 30 s, default
mode; FA/cam-h with Garwood 95 %, recall with world-bootstrap 95 % (2,000,
seed 58). Selection rule unchanged from §7.1: lowest select-fold FA/cam-h
with select-fold recall ≥ 0.85 over θ × min-clock ∈ {5, 10, 15} s; nothing
is tuned on H12. `H58_OUT=out/experiments/h58_round2`; commands
`tools/loiter_eval.py h21` and `h23`; outputs
`round4_h21_results.json`, `round4_h23_results.json`.

**H21 · θ for calibrated GBM.**
* *Arms.* A1 frozen (control, 2.915 [2.854, 2.977] / 0.825). **C**: the §7
  GBM (same features, hyper-parameters, fit fold, 1.5 M negative cap) +
  isotonic on the select fold, θ on a calibrated-scale grid of **25
  log-spaced points 0.01–0.5** (`H21_GRID`). **B** (uncalibrated, §7 grid)
  as reference only.
* *Seeds.* 5 GBM seeds {58, 59, 60, 61, 62}; the seed sets both
  `random_state` and the negative-subsample RNG (without early stopping HGB
  is deterministic given its data, so the subsample is the real source of
  variation). Fold fixed = the round-3 select fold (asserted identical).
  Seed 58 is the primary model (its fit equals round-3 B/C).
* *Metric.* H12 FA/cam-h at the select-fold-chosen point; paired clean-world
  cluster bootstrap CI of C − A1 FA/cam-h (2,000, seed 58).
* *Bar (clear win).* A C seed clears iff a grid point reached select-fold
  recall ≥ 0.85, its H12 recall ≥ 0.80, and its Garwood upper < **2.854**
  (A1's lower). If no grid point reaches 0.85 that seed fails (no fallback).
* *Decision / stopping.* One pass, θ frozen before H12 scoring. **C ships
  (seed-58 model) only if ≥ 4/5 seeds clear the bar, seed 58 clears, and the
  seed-58 C − A1 bootstrap CI lies entirely below 0.** Otherwise A1 stays.
* *Prediction P9.* Select-fold recall ≥ 0.85 pushes θ to about 0.03–0.07,
  giving H12 FA ≈ 2.4–2.9 at recall ≈ 0.80–0.84 (the round-3 curve had
  2.765 / 0.831 at θ 0.05 and 1.951 / 0.803 at θ 0.1). Fewer than 4/5 seeds
  clear the bar; A1 stays.

**H23 · frozen vs retrained logistic weights.**
* *Arms, per seed s.* **F**: round-1 A1 weights frozen, θ × clock
  re-selected on seed s's select fold (§7.1 grid). **R**: logistic
  (`learned_rule`, same features, IRLS, L2 1, 1.5 M negative cap with seed s)
  refitted on seed s's fit fold, θ × clock selected on the same select fold.
  Shipped A1 (θ 0.95, clock 5) is the fixed reference.
* *Seeds.* 10 world-generation × training seeds s ∈ {58, 158, …, 958}.
  s = 58 is the existing round-2 train split; the other nine are **new train
  splits** `train_s<s>` (150 clean + 300 recall worlds, `alarm_scale` recipe,
  world seeds s / s+1), generated with `tools/loiter_eval.py gen/feats`. Fit /
  select split 70/30 by world, stratified by mode, `default_rng(s)`.
* *Metric.* Per seed: H12 FA/cam-h and recall of F and R; paired
  clean-world bootstrap of R − F. Across seeds: mean, SD and seed bootstrap
  95 % CI (10,000, seed 23) of F FA, R FA, R − F and (R − F)/F.
* *Stopping.* Fixed 10 seeds, no early stop, no seed dropped.
* *Decision.* A seed counts for R if R has H12 recall ≥ 0.80 and (F recall
  < 0.80 or R FA ≤ F FA); symmetrically for F (strict <). **R wins ≥ 7/10 →
  retraining is the default policy** and the next shipped weights are the
  seed-58 R (the canonical split; no seed is picked on H12). **F wins ≥ 7/10
  → freeze-and-ship is the policy**, A1 stays. Otherwise **no dominance**:
  A1 stays (incumbent), and the policy is "either; retraining must beat the
  incumbent on a select fold". *A1 typical or lucky:* count seeds whose R
  reaches FA ≤ 2.915 at recall ≥ 0.80: ≤ 1 → A1's 2.915 was lucky; ≥ 3 →
  typical; 2 → borderline.
* *Prediction P10.* The mean (R − F)/F lies within ±10 % with a CI covering
  0; neither arm reaches 7/10 (no dominance); A1's 2.915 is typical. The
  round-2 A2 3.745 vs A1 2.915 gap came from A2's θ 0.9 / clock 10 selection
  window-only on all train worlds, not from its weights.

**H22 + H33 (32, `57ffff6`, `93cc3b1`; AUDIT_H22_H33) — does this change what A1 ships with?**
A1's *weights and clock* do not change; its *θ and delivery* do.
* **θ.** Conformal risk control on a calibration half (θ 0.960–0.963 instead of the grid's 0.95) keeps
  held-out FA ≤ 2.915 in 10/10 splits vs 6/10 for the plug-in θ (and 6/10 for the grid θ 0.95 itself),
  at recall 0.789 vs 0.824 (cost −0.035 [−0.037, −0.033], inside the pre-registered 0.05). **Ship
  recommendation: A1 with a CRC-calibrated per-site θ** at the site's chosen α, stated as "expected
  per-site FA ≤ α on sites exchangeable with the calibration set" — not a per-site hard cap, and void
  under drift (H34, H35). The headline 2.915 / 0.825 stays the reference; the guaranteed operating
  point is ≈ 2.31 / 0.789. Below α ≈ 1 the cost grows fast (α = 1: −0.107, fails the ship clause).
* **Budget.** 0.001 (assumed, 28 §6) FA/cam-h cannot be certified from 338 simulated worlds: B/(n+1) ≥ 0.248. The FAIL stands.
* **Delivery.** Ship as a score-ranked review queue, not a FIFO alarm: H22 FIFO realises 0.511 of 0.825
  within 5 min (inconclusive vs the 0.495 bar) and 0.127 within 30 s; ranking adds +0.262 at 30 s.

### 8.2 Results (pre-registration commit `06475ab`; `round4_h21_results.json`, `round4_h23_results.json`)

H12 worlds, actor-aware, 30 s, default mode. A1 re-scored: 2.915 [2.854,
2.977] / 0.825 (asserted equal to §7.2). Nothing tuned on H12.

**H21 · calibrated GBM, θ on the 25-point grid 0.01–0.5 (select fold).**
Every seed had a grid point with select-fold recall ≥ 0.85, so no fallback
was used. The chosen point sat on the constraint: select-fold recall 0.868
(92/106) on seed 58 and 0.858 (91/106, the minimum count that passes) on
seeds 59–62.

| seed | C θ, clock | C FA/cam-h [Garwood] | C recall [95 %] | C − A1 [paired world boot 95 %] | clears bar | B (ref.) θ → FA / recall |
|---|---|---|---|---|---|---|
| 58 | 0.051, 5 | 2.765 [2.706, 2.825] | 0.831 [0.796, 0.866] | −0.150 [−0.231, −0.067] | yes | 0.8 → 3.114 / 0.842 |
| 59 | 0.043, 5 | 3.216 [3.152, 3.281] | 0.844 [0.811, 0.878] | +0.301 [0.217, 0.388] | no | 0.8 → 3.118 / 0.842 |
| 60 | 0.043, 5 | 2.992 [2.930, 3.055] | 0.839 [0.805, 0.874] | +0.077 [−0.009, 0.164] | no | 0.8 → 3.123 / 0.842 |
| 61 | 0.051, 5 | 3.126 [3.063, 3.190] | 0.833 [0.799, 0.868] | +0.211 [0.126, 0.295] | no | 0.9 → 2.250 / 0.814 |
| 62 | 0.051, 5 | 2.703 [2.644, 2.762] | 0.833 [0.799, 0.868] | −0.212 [−0.293, −0.131] | yes | 0.8 → 3.145 / 0.836 |

Over the 5 seeds, C FA is 2.960 (SD 0.223, seed-bootstrap 95 % [2.785,
3.135]) and recall 0.836 [0.832, 0.841]. **2/5 seeds clear the bar; the rule
needs 4/5. A1 stays.** Seed 58 on its own clears the bar, with a CI below 0.
That is the result a single-seed run would have shipped. The seed-to-seed
spread (2.70–3.22) is larger than the gap to A1, so the single-seed win is
not reproducible.

*P9 holds in substance.* θ landed at 0.043–0.051, inside the predicted
0.03–0.07. Recall was 0.831–0.844 (seed 59's 0.844 is just above the
predicted 0.80–0.84), and fewer than 4/5 seeds cleared, as predicted. FA overshot the predicted 2.4–2.9 band on 3 of 5 seeds (up to
3.22). The round-3 curve's 1.951 at θ 0.1 is not reachable by honest
selection: select-fold recall ≥ 0.85 always forces θ ≈ 0.05. B (reference)
shows the same instability. Seed 61 selected θ 0.9 and gives 2.250 / 0.814;
the other four selected θ 0.8 (one step lower on the §7 grid) and give
3.114–3.145. That is ≈ 0.9 FA/cam-h between adjacent grid points, but
across different seed models, so model and θ both differ.

**H23 · frozen (F) vs retrained (R) logistic weights, 10 world+training seeds.**
All nine new train splits generated with 0 errors (450 worlds each).

| seed | F θ, clock | F FA [Garwood] | F recall | R θ, clock | R FA [Garwood] | R recall [95 %] | R − F [paired boot 95 %] |
|---|---|---|---|---|---|---|---|
| 58 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.95, 5 | 4.101 [4.028, 4.174] | 0.872 [0.839, 0.906] | −0.932 [−1.010, −0.858] |
| 158 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.95, 5 | 4.288 [4.215, 4.363] | 0.856 [0.822, 0.890] | −0.744 [−0.808, −0.680] |
| 258 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.95, 5 | 4.187 [4.114, 4.261] | 0.869 [0.837, 0.903] | −0.845 [−0.914, −0.774] |
| 358 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.9, 5 | 6.225 [6.136, 6.315] | 0.914 [0.884, 0.942] | +1.193 [1.120, 1.265] |
| 458 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.95, 5 | 4.118 [4.046, 4.191] | 0.869 [0.836, 0.902] | −0.914 [−0.993, −0.836] |
| 558 | 0.95, 5 | 2.915 [2.854, 2.977] | 0.825 | 0.95, 5 | 3.983 [3.912, 4.055] | 0.856 [0.821, 0.890] | +1.068 [1.005, 1.131] |
| 658 | 0.95, 5 | 2.915 [2.854, 2.977] | 0.825 | 0.98, 5 | 2.257 [2.203, 2.311] | **0.789** [0.751, 0.829] | −0.658 [−0.715, −0.597] |
| 758 | 0.95, 5 | 2.915 [2.854, 2.977] | 0.825 | 0.98, 5 | 1.827 [1.779, 1.876] | **0.783** [0.748, 0.825] | −1.088 [−1.158, −1.013] |
| 858 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.95, 5 | 3.599 [3.531, 3.667] | 0.828 [0.791, 0.865] | −1.434 [−1.539, −1.323] |
| 958 | 0.9, 5 | 5.033 [4.953, 5.114] | 0.894 | 0.8, 10 | 5.592 [5.507, 5.677] | 0.883 [0.849, 0.916] | +0.559 [0.496, 0.623] |

Across seeds (mean, SD, seed-bootstrap 95 %): F FA 4.397 (1.023) [3.762,
5.033]; R FA 4.018 (1.314) [3.236, 4.776]; F recall 0.874 [0.853, 0.894]; R
recall 0.852 [0.827, 0.875]; **R − F −0.380 [−0.896, +0.203]**; **(R − F)/F
−8.5 % [−21.6 %, +6.2 %]**.

*Decision (pre-registered).*
* R wins 5/10 (58, 158, 258, 458, 858). F wins 5/10 (358, 558, 958, and
  658 and 758, where R's recall is below 0.80).
* Neither arm reaches 7/10, so the result is **no dominance: A1 stays as
  the incumbent**. The policy is that retrained weights ship only if they
  beat the incumbent on a select fold.
* A1's 2.915 counts as **lucky** by the pre-registered count (0 retrained
  seeds; ≤ 1 means lucky). No retrained seed reaches FA ≤ 2.915 at recall
  ≥ 0.80. The two that go lower (2.257, 1.827) buy it with recall 0.789 and
  0.783.
* *What F is (pre-registered, stated here so it is not misread).* F keeps
  A1's weights but re-selects θ × clock on each seed's select fold, so F is
  **not** the shipped A1: it equals A1 (θ 0.95) on only 3/10 seeds. The F
  win count is therefore "frozen weights + per-fold selection", and the
  "lucky" count compares R with the fixed A1 figure 2.915, not with F.

*What the luck actually is.* The frozen weights are identical on every
seed. The only thing a seed changes is the selected θ. On 7/10 select folds
the rule picks θ 0.9, giving 5.033 / 0.894. On 3/10 it picks θ 0.95, giving
2.915 / 0.825. So A1's 2.915 is not a property of the round-1 weights alone.
It depends on round 1's selection landing on θ 0.95 [INF: round 1 used a
different split; the 3/10 rate is measured on the ten new folds]. The
recall ≥ 0.85 criterion is applied on select folds of 102–113 events (106 on
seed 58); on seed 558 θ 0.95 passed with 92/108 = 0.852, one event above
the line. (The per-point select grid was not saved, so the margin by which
θ 0.95 failed on the other seven folds is not recoverable.) That single grid
step moves H12 FA by 2.118 FA/cam-h (5.033 − 2.915). The spread between
arms comes from θ selection far more than from the weights. That puts it in
the same place as H21's instability.

*Against P10.*
* Holds: the mean relative gap (−8.5 %) is inside ±10 % and its CI covers 0.
* Holds: no dominance.
* Fails: "A1 typical". By the pre-registered count it is lucky, and the
  mechanism is θ selection, not the weights.
* Not tested directly: "the round-2 A2 gap came from θ selection". No arm
  reproduces A2's window-only selection. Consistent with it [INF]: the same
  frozen weights give 2.915 or 5.033 depending only on the selected θ.

**Round-4 verdict.** Nothing changes in what ships. **A1 stays** (after H42 this single point is superseded by the three-point trade-off in §8.4)
(`LearnedLoiterRule`, round-1 weights, θ 0.95, clock ≥ 5 s, 2.915 FA/cam-h,
recall 0.825). Both hypotheses point at one weakness: **operating-point
selection on a ~100-event fold is the dominant source of variance.** It
exceeds the GBM-vs-logistic gap and the frozen-vs-retrained gap. The next
step is a variance-aware θ choice, not a better model. Options are the
conformal choice of H33 (32 §H33), or selecting on pooled select folds
across seeds. Any future "arm X beats A1" claim must be shown over seeds; the
bar is ≥ 4/5 seeds, as registered here. The assumed 0.001 FA/cam-h budget FAIL
stands.

### 8.3 H42: θ-selection policy (pre-registration in 32 §H42; results 32 §H42 results)

Four ways of choosing A1's (θ, clock) from the ten round-4 select folds (1,077 events pooled),
each drawn 10 times (per fold, or leave-one-fold-out), scored on H12:

* per-fold (round-4 control): θ 0.9 ×7 / 0.95 ×3 → H12 FA 2.915–5.033 (range 2.118, SD 1.023), recall 0.825–0.894.
* pooled LOFO: θ 0.9 on 10/10 draws → 5.033 / 0.894, zero spread.
* CRC α = 2.915 LOFO: θ 0.963–0.965 → 2.099–2.218, recall 0.778–0.783 (below 0.80 on every draw).
* pooled + recall floor 0.80 (0.85–0.99 grid): θ 0.96 ×10 → 2.364 / 0.792 (below 0.80 on H12).

The hypothesis (≥ 2× spread cut at recall ≥ 0.80 in ≥ 9/10) is **met by pooled selection**, which
becomes the shipped θ-selection policy. It moves the operating point: pooled select recall at θ 0.95
is 900/1,077 = 0.836, short of the 0.85 criterion, so the stable choice is θ 0.9 —
ΔFA vs A1 **+2.118 [+2.005, +2.237]**, Δrecall **+0.069 [+0.045, +0.095]** (paired bootstrap).
A1's 2.915 / 0.825 is thus a point the registered criterion does not select once the fold is large
enough. Keeping ≈ 2.4 FA/cam-h needs a lower select-recall criterion (0.80), which costs ≈ 0.03 recall
and falls just under 0.80 on H12 (0.792). That criterion change is a separate, operator-budget
decision; until it is made, quote A1 as "2.915 / 0.825 at θ 0.95 (a minority selection)" and the
pooled-policy point 5.033 / 0.894 alongside it. Budget FAIL unchanged.

*Audit (AUDIT_H42).* All numbers recompute; LOFO is used for the pooled arms. But LOFO pools share
8/9 folds, so "spread 2.118 → 0" is partly overlap by construction, not stability on independent
data; and θ 0.9 is a SEL_GRID artefact — on pooled counts θ 0.93 (select recall 0.886) and 0.94
(0.853) also pass 0.85 at lower FA, and H12 was not scored there. "Pooled picks 5.033 / 0.894" is
true of the registered coarse grid only.

### 8.4 The ship decision is an operator-budget trade-off, not "A1 ships"

After H42 there are three measured operating points for the same frozen A1 weights and clock
(≥ 5 s), all on H12 (3,002 clean cam-h, 360 events, actor-aware, 30 s), and none is "the" shipped
point until a site states its operator budget:

| point | θ | H12 FA/cam-h | H12 recall | ≈ alarms/h at 40 cams | H22 realised recall @5 min (FIFO / ranked) |
|---|---|---|---|---|---|
| A1 (round 3; a 3/10 small-fold draw) | 0.95 | 2.915 [2.854, 2.977] | 0.825 [0.789, 0.862] | 120 (measured) | **0.511 / 0.586 — measured** |
| pooled SEL_GRID (H42 shipped *policy*) | 0.9 | 5.033 [4.953, 5.114] | 0.894 [0.863, 0.924] | 205 (H45 measured) | **0.324 / 0.504 — measured (H45)** |
| conformal (CRC α = 2.915, H42 LOFO) | 0.963–0.965 | 2.10–2.22 | 0.778–0.783 | 92 at θ 0.962851 (H45 measured) | **0.571 / 0.621 — measured at θ 0.962851 (H45)** |

(pooled + 0.80 floor, θ 0.96: 2.364 / 0.792, ≈ 98/h, sits between A1 and CRC. H33's CRC on H12
halves gave 2.312 / 0.789.) Pooled vs A1, paired: +2.118 [+2.005, +2.237] FA, +0.069
[+0.045, +0.095] recall. **Before H45 only A1's rate had been run through the H22 operator sim**, and the bracketing below
was [INF] (kept for the record; H45, §8.5, measured it and it held in direction): at ≈ 205 alarms/h the pooled
point is above the invented operator's ~120/h fresh and ~96/h fatigued capacity and near dwell_25's
244/h, where FIFO realised 0.108 of 0.367 (60 % of alarms bulk-acked), so its +0.069 model recall
is likely to be *more than* lost at the console unless the site staffs more operators per camera;
the conformal point (≈ 90/h) sits between A1 (120/h, 88 % utilisation) and the twin floor (44/h,
realised 0.725 of 0.825), so it plausibly realises *more* than A1's 0.511 despite 0.04 lower model
recall. Which point ships is therefore a property of the site — operators per camera and the
tolerated alarm rate — and must be chosen by eliciting that budget (66 H45: rerun H22 at the pooled
and conformal rates), not read off H42. **Ship recommendation (measured, H45 §8.5; invented operator model, H22 caveat):**
**1 operator / 40 cams → conformal θ 0.9629 (0.962851) ranked (0.621 realised @5 min); ≥ 2 operators → A1
θ 0.95 ranked; never pooled θ 0.9.** Deliver A1's weights as a score-ranked review queue at all three.
Quote 2.915 / 0.825 as "one draw", never as "the shipped point" on its own; θ 0.962851 is the most permissive of H42's 10
distinct CRC draws (0.9629–0.9649; "modal" was a tie-break). The assumed 0.001 budget (A=4, K=500, H=8; 28 §6 — not a field standard, `81`) FAIL stands
at every point.


**H33b addendum (AUDIT_88, 32 §H33b; AUDIT_H33B) — does the ship θ move?** The CRC guarantee holds for a loss bounded by a
B fixed in advance; H33/H42 used the empirical max B (approximate). H33b fixes B = 123.5 FA/cam-h from the generator
(Poisson(180) 1 − 1e-6 quantile 247 visitors / 2.0 cam-h), but the "≤ 1 alarm per visitor" step is **not enforced**: A1
alarms once per dwell episode and one visitor can open several (up to 21 in H12). So 123.5 is not an a-priori bound on
L; the guarantee is exact for the clipped loss min(L, 123.5), which equals L on all 676 H12 worlds (max 89) — an
empirical fact, not a guarantee. CRC θ at α 2.915 is 0.9615–0.9642 (vs 0.9598–0.9627), held-out FA 2.216 ≤ 2.915 in
10/10 splits, recall 0.784 (−0.006 vs empirical B). θ 0.962851 lies below the fixed-B θ in 7/10 splits, so the
certified point moves up slightly, to the split median **θ 0.963436: 2.187 FA/cam-h / 0.783 on all worlds, 90 alarms/h**.
**Measured (H45b, 32 §H45b):** one operator, @5 min, 0.573 FIFO / **0.617 ranked**; paired vs θ 0.962851 +0.001
[−0.012, +0.015] / −0.004 [−0.017, +0.010]; vs A1 ranked +0.031 [+0.014, +0.050]. The staffing table is unchanged:
**1 operator / 40 cams → conformal θ 0.9634 (0.963436) ranked; ≥ 2 → A1 θ 0.95 ranked; never pooled.** (At 2 operators the
certified point's loss vs A1 is −0.019 [−0.043, +0.003], no longer CI-separated; A1 still ≥.) To make B a true bound,
enforce one alarm per visitor per world in the rule (or derive B from a per-visitor episode cap the generator guarantees).

**H33c addendum (32 §H33c) — making B a real bound.** Capping A1 at one alarm per visitor per world (`max_alarms_per_uid_per_world = 1`) makes B = 123.5 a valid a-priori bound (≤ 247 visitors at 1 − 1e-6; H12 max 202), so the CRC guarantee is exact, not for min(L, B). It costs nothing and buys little: equal-θ FA −3.4 %, 0 true alarms dropped, CRC θ 0.961780 → 2.196 FA/cam-h / 0.789; H45c 1 operator ranked 0.618 @5 min, +0.001 [−0.014, +0.016] vs θ 0.963436. **Ship rule unchanged; deliver the 1-operator conformal point with the cap** (assumes tracker uids hold within a world).

**The ship story (canonical wording — quoted verbatim-short elsewhere: 60, 48, 65 v2 §3, 78, 74 drill 1, 79/82):**
1 operator/40 cams → A1 weights, conformal θ 0.9618 with B = 123.5 fixed in advance and a one-alarm-per-visitor
cap, ranked review queue: 2.20 FA/cam-h (≈ 91 alarms/h), model recall 0.789, realised 0.618 at 5 min — the only
point with an exact guarantee (assumes GT identities; tracker ID switches would reopen the cap, H59); ≥ 2
operators → A1 θ 0.95 ranked; never pooled. **Scorer used for every number above: `alarms.score(actor_aware=True)`
(the default), not `position_radius_m`** — H62 (32 §H62) measured that mode's own false-credit rate at 14.8–49.3 %
on tailgate-style scenarios, well above what a ship number could quote; it remains a diagnostic for how much of
an actor-aware recall drop under tracker ID churn is a scoring artefact, not a candidate default.

### 8.5 H45: the three points through the H22 operator sim (32 §H45 results; supersedes 8.4's [INF] bracketing)

Same operator model, 10 seeds, 40 cameras; realised recall @5 min [95 %], one operator:

| point | alarms/h | utilisation | FIFO | ranked | vs A1 (ranked, paired) |
|---|---|---|---|---|---|
| A1 θ 0.95 | 120 | 0.88 | 0.511 [0.485, 0.537] | 0.586 [0.554, 0.618] | — |
| pooled θ 0.90 | 205 | 0.95 | 0.324 [0.304, 0.346] | 0.504 [0.472, 0.535] | −0.083 [−0.103, −0.064] |
| conformal θ 0.962851 | 92 | 0.79 | 0.571 [0.539, 0.605] | 0.621 [0.587, 0.657] | +0.035 [+0.016, +0.055] |

8.4's bracketing held in direction: pooled's +0.069 model recall becomes −0.08 (ranked) to −0.19 (FIFO)
realised recall at one operator (53 % of alarms bulk-acked), and the conformal point realises *more* than A1
despite 0.042 lower model recall. The pre-registered H45 was not met (pooled was predicted neutral; conformal's
utilisation cut is 10 %, not ≥ 20 %). Pooled never beats A1 with CI > 0 up to 3 operators per 40 cameras
(3 ranked: +0.013 [−0.009, +0.035]); at 2 operators A1 edges conformal (−0.022 [−0.045, −0.001], 0/10 seeds up — small but consistent).
**Ship point:** at one operator per 40 cameras, the conformal θ with a score-ranked queue; at ≥ 2 operators,
A1's θ 0.95 ranked. H42's pooled θ 0.9 is not a ship point at any staffing tested.
