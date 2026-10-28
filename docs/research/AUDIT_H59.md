# AUDIT_H59 · Fusion under H24-calibrated identity switches

Audited 2026-09-27 against `docs/research/32_EXPERIMENTS_LOG.md` §H59, `out/experiments/h59_idsw_fusion/results.json`
(commit 3fdcf04), `survsim/experiments/sensor_fusion.py` (`fuse_world_h54`'s `h59` branch, `fuse_world_h59`,
`summarise_h59`), `survsim/experiments/line_cross.py` (`id_switch`, `close_pairs`), config `h59_idsw_fusion.yaml`,
`tests/test_sensor_fusion_h59.py`, `out/experiments/h24_reid_assoc/results.json` (IDSW source), 32 §H53/§H54.

**Score: 97/100.** Every headline number recomputes; the code path genuinely exercises identity switches
(proved empirically, not just by inspection); the IDSW-rate arithmetic is exact; the tailgater-recall
explanation is correct. **H59's verdict stands: `met=False` (3 of 4 pre-registered criteria unmet), and this
is a real negative result, not a null test that never touched what it claims to test.**

## 1. Does the switched identity reach fusion matching? (the suspicious-looking part)

The concern: twin-FA removal is 99.1 % under both calibrated (157.6 IDSW/track-h) and 3× (472.7) noise —
identical to H54's benign-noise 99.1 %. That similarity by itself does not distinguish "the code never tests a
swap" from "the fusion is genuinely insensitive to swaps." Traced and tested both:

* **Trace.** `fuse_world_h54(w, cfg, h59={...})` calls `LC.id_switch(df, h, r_m, persons, rng, cp=...)` on the
  *true* position dataframe before `LC.add_noise`. `id_switch` swaps the `uid` **label** between two people
  while a `body` column keeps the true identity (`tests/test_sensor_fusion_h59.py::test_id_switch_swaps_labels_only_between_close_people`
  proves this with h = 1e9, forcing a swap every tick). The swapped-label dataframe (`src_df`) — not the
  original `df` — is what `add_noise` turns into `tr`, so `tr`'s `uid` (and therefore every track group, every
  `alarms_with_tracks` entry, and `alarms.score`'s scored actor) carries the **post-swap label**. `alarms_with_tracks`
  additionally records the *true* body (`b`) alongside the label (`base`) for kind classification only —
  twin/incident/commuter kind is looked up by true body, never by label, which is correct: whether an alarm is
  physically about a twin doesn't change because its label got swapped.
* **Empirical check** (script run in this audit, tailgate world i=3, extreme hazard h=1e6):
  `LC.id_switch` produced **1,322 swap events**; of the 2 resulting `alarms_with_tracks` rows, **1 had a
  scored label (`p007`) different from its true body (`p001`)** — a swapped identity reaching a real fused
  decision. At the registered (non-extreme) rates, `results.json`'s `n_swap` is non-zero at every world/arm/seed
  (aggregate achieved rate 157.57/track-h calibrated, 472.67/track-h stress — both within noise of the 157.6/472.7
  targets, confirming the hazard is actually firing at realistic magnitude, not just at an artificially cranked
  test value).
* **Tests.** `test_id_switch_swaps_labels_only_between_close_people` exercises a forced swap (h=1e9) and checks
  the label/body split directly. `test_benign_reproduces_h54` checks the *complement*: h=0, seed=0 must
  reproduce H54 bit-for-bit — this is the control that proves the harness (not a silently-broken hazard) is
  what produces the h=0 null, so the calibrated/stress arms' identical-looking 99.1 % is not "the h=0 code path
  ran again by mistake."

**Conclusion: the switched identity does reach fusion matching and `alarms.score`. Count of fused decisions
affected is non-zero at every tested rate. H59 tested what it claims.**

## 2. IDSW-rate arithmetic from H24 — recomputed, exact

`out/experiments/h24_reid_assoc/results.json`, `scores.batch_v8.mix_300_s{0..4}.bytetrack.COMBINED.id_switches`
= 76, 81, 117, 77, 66 → sum 417, mean 83.4 (recomputed directly from the JSON, matches 32 §H59's registered
numbers exactly). GT track-seconds 1,904.6 (19,046 boxes @ 10 fps) is asserted, not independently recomputed
here (not stored alongside `id_switches` in this results.json), but is unchanged from what H24/H59 registered.

ρ = 83.4 / 1,904.6 = 0.0437891… IDSW/track-s = 157.6/track-h ✓ (`config.h59.rho_idsw_per_track_s` = 0.043789).

Calibrated hazard: `calibrate_h` sets h = ρ·track_s / (2·pair_s) so E[IDSW]/track-s = ρ (each swap event costs
2 IDSW — both labels move). From the run's exposure pre-pass: track_s = 13,102,539.0, pair_s = 2,172,805.2 →
h = 0.043789 × 13,102,539 / (2 × 2,172,805.2) = **0.13202911…**, matching `config.h59._h.calibrated` to 8
significant figures. Stress = 3× that hazard by config (`arms.stress: 3.0`), achieving 472.7/track-h ≈ 3.00×
157.6 — consistent, not "2× that" as an earlier backlog draft (66) once phrased it; 32's own deviations note
already flags and resolves this in favour of the registered 3× (no code deviation, just stale backlog prose).

**Is 157.6 plausible from "H24's 87–93 IDSW per MOT20-02 run" (quoted in AUDIT_H54/CLAUDE.md context)?**
That figure is a *different* H24 measurement: `scores.mot20` (real MOT20-02 footage validation), not
`scores.batch_v8` (our own rendered scenarios) — recomputed here: `mot20` ByteTrack COMBINED id_switches per
checkpoint = 91, 89, 87, 108, 88 (range 87–108 across 5 checkpoints; "87–93" in AUDIT_H54 likely refers to a
narrower per-sequence or subset figure, not audited further here — out of scope for H59, which explicitly used
`batch_v8`, not `mot20`). The batch_v8 rate used for H59's calibration (83.4 mean) is *lower* than mot20's
range (87–108), so if anything H59 under-calibrates relative to the real-footage number quoted elsewhere in
the docs — using the higher, real-MOT20 rate would only have driven *more* swaps, strengthening rather than
weakening the tested hazard, so this does not change H59's "not met" verdict or invalidate the arithmetic used.
This is a minor doc cross-reference ambiguity (two different H24 IDSW numbers exist for two different
datasets), not an error in H59's own calibration, which is self-consistent and reproduces exactly.

## 3. The tailgater recall collapse — real effect, not a fusion artefact, not the guessed mechanism

32's write-up already attributes this correctly to `alarms.score`'s actor-aware matching, not to fusion or to
dwell/track-continuity breakage. Confirmed by recomputation: `C` alone (no fusion leg at all) collapses
identically to `C+abc`/`C+abcg` (0.769→0.100 base recall, 0.108 tailgater@10 under `C` benign→calibrated) —
the collapse happens *before* any badge/RF/PIDS/counter gate runs, so it cannot be a fusion-leg effect. The
mechanism is: `id_switch` reassigns a track's *label* mid-dwell; when that happens to a track a base rule
(intrusion/probe/climb/tailgate) already caught, the detection now carries the wrong `uid`, and `alarms.score`'s
actor-aware matching (principle 4: "an alarm on the wrong person is not a hit") scores it as a miss against
the true actor's ground truth — regardless of whether the alarm's *position/time* would have counted under a
label-blind scorer. This is not track-continuity breakage in the sense of a fragmented/lost track (H40b's
fragmentation stage is separate and already active in the benign arm); it is a **scoring-denominator
artefact of applying actor-aware recall to a noise stage that reassigns labels**, exactly as 32 states.

One real, already-flagged confound this audit confirms rather than discovers: the swap hazard is applied
per close-pair-second **uniformly** across all scenarios, but tailgating (and staff-pair) scenarios hold two
people within `r_m=2 m` for most of their duration by construction, so they rack up far more swap
*opportunities* than an average passing encounter — meaning the aggregate calibration (which matches ρ exactly
across the whole corpus) concentrates disproportionately more of its swap budget on exactly the scenarios
being scored for tailgater/base recall. This is not a bug — `pair_s`/`track_s` are computed from the same
worlds being scored, so the calibration is self-consistent — but it means the calibrated rate is not
scenario-stratified, and "157.6/track-h in general" does not mean "157.6/track-h for a tailgater pair
specifically" (it is very likely higher there). The pre-registration's own confound list already says
"swaps only < 2 m, not occlusion-driven"; this audit adds the corollary that the *scenario mix* matters too.

## 4. Verdict

**Not changed. `met=False` stands, and correctly so.** This is not an invalid/untested hypothesis — the
identity-switch stage demonstrably reaches fusion matching and actor-aware scoring at the registered rates,
the IDSW-rate arithmetic is exact, and both surprising results (twin removal unchanged, tailgater collapse)
have verified mechanistic explanations that do not require discarding the run. The one thing worth adding
for future readers is the batch_v8-vs-mot20 IDSW-source distinction (§2), now recorded here.

## 5. Fold-in

No numbers changed in 32, FACTS, 66, or docs/13 — all four already state the correct verdict and mechanism.
Added: this file; 00 index row; a short "H24 IDSW source" clarifying note is not needed in 32/FACTS/66/13
beyond what is already there, since none of them claim the mot20 figure was used for H59's calibration.
