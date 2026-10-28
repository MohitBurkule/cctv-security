# 66 · Hypothesis backlog H21–H36 (ranked, pre-registrable)

*2026-09-27. Twelve next experiments drawn from the open caveats in 32
(H1–H20), 58 (loiter rounds 1–3) and 64 §7–8. Each is written in the 49 §12
template, cut to ≤ 120 words: hypothesis, arms, seeds, metric, stopping rule,
cost, decision. None is registered yet. To register one, expand it to the full
49 §12 block in 32, commit it, and quote that commit in the results. Rank
= expected value per unit cost, the same scoring as 23 §4. Cost: CPU = dev
machine without GPU; GPU = the 8 GB RTX 2070, editor stopped (49 §11).
Milestones refer to 23 v2.*

| Rank | id | One line | Needs | Cost |
|---|---|---|---|---|
| 1 | ~~H21~~ | calibrated-GBM θ on a calibrated-scale grid — **done `bd4c028`: 2/5 seeds clear the bar (4/5 needed), A1 stays; AUDIT_ROUND4** | — | — |
| 2 | ~~H22~~ | operator review-queue simulation — **done `57ffff6`: inconclusive (0.511 vs bar 0.495); ranked +0.262 @30 s** | — | — |
| 3 | ~~H23~~ | frozen vs retrained loiter weights across seeds — **done `bd4c028`: no dominance (5–5), A1's 2.915 a θ-selection draw; AUDIT_ROUND4** | — | — |
| 4 | ~~H24~~ | ReID association in tracking on batch_v8 — **done `2fdecd6`: not met by 0.0006 at w = 1 (batch_v8 ΔAssA +0.0194 [+0.0004, +0.0439] vs +0.02); MOT20-02 +0.0139, IDSW −5.6; audited AUDIT_H24; H46b done — bar met post cross-validation at w = 8 (day held-out ΔAssA +0.0570)** | — | — |
| 4b | H46 | appearance weight w sweep + night arm for ByteTrack+OSNet (from H24) | nothing (cached dets/embeddings) | GPU light |
| 5 | ~~H25~~ | label-noise injection — **done `c1100bb` (reduced, 27 runs): refuted, σ 10 % keeps 97 % of gain; AUDIT_H25** | — | — |
| 6 | ~~H26~~ | dose curve, fixed steps — **done `dbd21c4` (reduced: 5 arms × 5 seeds): +0.0041 / +0.0045 at 100 / 300, none Holm-significant; h14b's +0.0121 was unequal steps; AUDIT_H26** | — | — |
| 6b | ~~H51~~ | equal-step dose re-run, 10 paired seeds — **done `385f363`, met: +0.0042 / +0.0051 at 100 / 300, Holm p 0.0039; AUDIT_H51. H52 unblocked** | — | — |
| 6c | ~~H52~~ | image-level vs label-level ablation at equal steps — **done `f7f1d3f`: label-driven (true − shuffled +0.0077, Holm 0.0098); masked +0.0036 (Holm 0.047); AUDIT_H52. H61 next** | — | — |
| 6d | ~~H61~~ | silhouette masking without inpainting; (a) − (c) registered as primary, 10 seeds — **done: box-fill artefact, not background-real (a−c′ +0.0071 Holm p 0.0039; c′−real −0.0020 Holm p 0.074); 32 §H61** | batch_v8 | GPU ~2 h |
| 7 | ~~H27~~ | synthetic-only far arm at 1280, 5 seeds — **answered by H19, not run** | — | — |
| 8 | H28 | degrade-profile retune on batch_v8 | M11 | GPU |
| 9 | H29 | clothes-change ReID with 40 held-out changers + MEVID real check (`70` §7; **raised by H20**: 15 ids → no real transfer) | M15 renders | GPU + editor |
| 10 | H30 | multi-site real eval of the dose gain | M12 | GPU |
| 11 | H31 | gait from pixels | M14 foot IK | GPU |
| 12 | ~~H32~~ | night against a real IR reference — **done `1acb9bd`: lowlight/thermal fits overfit (hold-out 2/13 vis, 3/13 IR), branch B3, no night-penalty estimate; audited AUDIT_H32** | — | — |
| 13 | H36 | full LLVIP held-out fit (**needs ~3.5 GB download sign-off**) | sign-off | CPU + GPU light |
| 14 | H37 | forensic attribute search recall@10 and the appearance-epoch trap (`72` §3) — **mock slice done, not met** (recall@10 pooled vs per-epoch diff +0.0004/-0.0118, two orders of magnitude below the 0.15 bar at both noise levels; ceiling effect — relevant sets mean 2.67/max 9, all ≤10; mechanism confirmed at unit level; CLIP arms still untouched; H37b registered to fix the design) | nothing (mock) done / H37b + batch_v8 for CLIP arms | CPU done + GPU light pending |
| 15 | ~~H38~~ | INT8/FP16 export accuracy — **done `d6b204d`: FP16 met (0.0000); INT8 not met (0.0117, s2 0.0154 > 0.015; AP75 −0.030); calibration n.s.; audited AUDIT_H38** | — | — |
| 15b | ~~H43~~ | INT8 calibration recovery, no-Jetson branch (`h43_qat`) — **PTQ leg done, not met** (Percentile AP75 recovery 0.415 all 5 / 0.424 h14b-only < 0.50 bar, 0/5 checkpoints regressed vs MinMax); QAT leg ran end-to-end on only 1/5 checkpoints (budget deviation, not a tooling failure) — **deferred as H43b**; audited AUDIT_H43 | — | — |
| 15c | ~~H43b~~ | QAT INT8 recovery, full 5-checkpoint corpus — **done: not met, either bar** (AP75 recovery 0.366 [all 5] / 0.334 [h14b-only] < 0.50 secondary and 0.80 primary; 3/5 checkpoints exceed the 0.005 AP-loss bar); QAT underperforms Percentile PTQ (H43) itself, because export re-quantizes with plain MinMax instead of keeping QAT's learned ranges; `32` §H43b | — | — |
| 15d | ~~H43c~~ | H43b root-cause fix: export QDQ from the QAT observers' learned ranges (`TensorQuantOverrides`, no re-fine-tuning) — **done: not met, either bar** (AP75 recovery 0.439 < 0.50 secondary and 0.80 primary; 4/5 checkpoints meet the 0.005 AP-loss bar, `mix_300_s2` misses it at 0.0067); learned-range export mechanism **[V] verified working** (ranges carried into the exported graph on 5/5 checkpoints) after fixing a Conv-node-order mapping trap (`model.modules()` order ≠ ONNX graph order, 31/64 mismatched by position — fixed by exact weight-byte matching); `32` §H43c | — | — |
| 15e | ~~H43d~~ | follow-up to H43c: does more QAT fine-tuning (600 iters, same recipe/export otherwise) close more of the AP75 gap — **done: hypothesis refuted** (pooled AP75 recovery fell 0.439→0.374; effect is checkpoint-recipe-dependent, not monotonic in iterations — 3 h14b checkpoints improved, 2 H51 `dose300` checkpoints got worse, one negative); `32` §H43d | — | — |
| 15f | H43e | TensorRT INT8 on real Jetson hardware (the un-run arm of H43) — **the only remaining edge item; needs an Orin NX or equivalent, cannot be done CPU-only** | nothing (Jetson hardware) | Jetson only |
| 16 | ~~H42~~ | pooled-fold / conformal θ selection across seeds — **done `0b4f5d9`: met by pooled (θ 0.9 ×10 → 5.033 / 0.894); CRC 2.10–2.22 / 0.78; LOFO overlap + coarse-grid caveats; audited AUDIT_H42** | — | — |
| 16b | H45 | operator-budget elicitation: rerun the H22 operator sim at the pooled (5.033) and conformal (≈ 2.15) rates (from H42, 58 §8.4) | nothing | CPU |
| 17 | H44 | certify the drift monitor: longer stationary streams (≥ 4,314 independent null windows) for the embedding arm's FA rate, plus detection-rate and track-length monitors as arms (from H34) | nothing (renders) | CPU + GPU light |

Ranks 1–3 run today on CPU. Ranks 10–12 have the highest value but are
blocked on data or on the engine.

---

## H21 · θ selection for calibrated GBM (`h21_gbm_theta`) — **DONE (`06475ab` → `bd4c028`)**
- **Status:** A1 stays. C mean 2.960 [2.785, 3.135] FA/cam-h at recall 0.836 over 5 seeds; 2/5 seeds clear the bar (Garwood upper < 2.854 at recall ≥ 0.80), 4/5 needed; seed 58 alone would have shipped. P9 holds in substance (θ 0.043–0.051). 58 §8.2, audited AUDIT_ROUND4.
- **Hypothesis:** on a calibrated-scale grid (θ ∈ {0.01…0.5}, 25 log-spaced points) chosen on the select fold, calibrated GBM (C) beats A1's 2.915 FA/cam-h at recall ≥ 0.80 on H12 worlds.
- **Arms:** A1 frozen (control); C with the new grid; B uncalibrated (reference).
- **Seeds:** 5 GBM seeds × the fixed select/test world split.
- **Metric:** FA/cam-h at recall ≥ 0.80, actor-aware, 30 s; world-cluster bootstrap CI.
- **Stopping:** one pass; θ frozen before test scoring.
- **Cost:** CPU, ~1 h.
- **Decision:** whether round 4 ships C (58 §7.2 read C 1.95 off the test worlds). If the CI for C − A1 includes 0, A1 stays.

## H22 · Operator-in-the-loop alarm queue (`h22_operator_queue`) — **DONE (`1d8cd26` → `57ffff6`)**
- **Status:** inconclusive on the primary (A1/FIFO 0.511 [0.484, 0.537] vs 0.495 at 5 min); ranked beats FIFO at 30 s for every rule; product shape = ranked review queue (23 M9). Audited AUDIT_H22_H33.
- **Hypothesis:** at A1's 2.9 FA/cam-h over 40 cameras, a simulated operator (check 30 s, fatigue after 2 h, bulk-acknowledge when the queue > N) realises < 0.6 of the model recall of 0.825.
- **Arms:** alarm queue (FIFO) vs ranked review queue (score-sorted, top-k/h); rates A1, dwell_25, twin-floor.
- **Seeds:** 10 operator-model seeds × 3,002 cam-h.
- **Metric:** realised recall at 30 s and at 5 min; operator utilisation.
- **Stopping:** fixed.
- **Cost:** CPU, < 1 h.
- **Decision:** alarm vs review-queue product shape (M9). Also tests 13 §A4's "cliff".

## H23 · Frozen vs retrained loiter weights across seeds (`h23_frozen_retrain`) — **DONE (`06475ab` → `bd4c028`)**
- **Status:** no dominance (5–5); R − F −0.380 [−0.896, +0.203], −8.5 % [−21.6, +6.2]. A1 'lucky' by the registered count (0/10 retrained seeds ≤ 2.915 at recall ≥ 0.80): frozen weights pick θ 0.9 on 7/10 folds (5.033) and θ 0.95 on 3/10 (2.915). P10 half right (gap and no-dominance hold; 'A1 typical' fails). F re-selects θ per fold, so F ≠ shipped A1 on 7/10 seeds. 58 §8.2, AUDIT_ROUND4.
- **Hypothesis:** A1 (round-1 weights frozen) beating A2 (retrained, 2.915 vs 3.745) is seed noise; over 10 training seeds the FA gap at matched recall is within ±10 %.
- **Arms:** frozen round-1; retrained on round-2 worlds; both θ-selected on the select fold.
- **Seeds:** 10 world-generation × training seeds.
- **Metric:** FA/cam-h at recall ≥ 0.80; paired difference, bootstrap over seeds.
- **Stopping:** fixed 10 seeds.
- **Cost:** CPU, ~3 h (world regeneration dominates).
- **Decision:** whether "freeze and ship" is a policy or an accident. If retrained ≤ frozen on ≥ 7/10 seeds, retraining is the default.

## H24 · Tracking with ReID association on our data (`h24_reid_assoc`) — **DONE 2026-09-27**
- **Status:** not met by the registered bar — OSNet-ImageNet ΔAssA batch_v8 +0.0194 [+0.0004, +0.0439] (bar +0.02); MOT20-02 +0.0139 [+0.0018, +0.0268] (no decrease: met, it rises), IDSW −5.6. HSV/H20 arms same shape. GT-box arm keeps the gain (association, not DetA). 32 §H24 results.
- **Audit (AUDIT_H24):** numbers recompute. Bar missed by 0.0006; MOT20-02 rise is a consistent direction but n = 5 checkpoints (exact sign-flip p 0.19 OSNet); HSV and H20 batch_v8 CIs span 0; GT-box CI spans 0. "Never lowered AssA" is true of arm means only. **Decision:** ReID enters the reference tracker (ImageNet OSNet, w untuned); H20 weights no better. Follow-up **H46** (w sweep + night arm).
- **Hypothesis:** adding OSNet appearance to ByteTrack association raises AssA on batch_v8 (occluding crowds) by ≥ 0.02 and does not lower it on MOT20-02.
- **Arms:** ByteTrack (control); ByteTrack + OSNet-ImageNet; + HSV histogram; + H20 weights if H20 transfers.
- **Seeds:** deterministic tracker; 5 detector checkpoints (h14b seeds).
- **Metric:** HOTA/AssA on batch_v8 day and MOT20-02, **scored by TrackEval** (requires M1 parity).
- **Stopping:** fixed.
- **Cost:** GPU light, ~2 h.
- **Decision:** whether ReID enters the reference tracker for M3, and whether H17's ID-switch rise is fixable.

## H25 · Label-noise injection (`h25_label_noise`) — **DONE (`c1100bb`, reduced design)**
- **Status:** refuted — clean gain +0.0127 [+0.0114, +0.0133]; σ 10 % keeps 97 %, σ 10 % + 10 % drop 94 % (−0.0008); not monotone. Ran 4 σ × 2 drop × 3 seeds (not 3 drop × 5 seeds). Consistent with H15 (dose 300) but does not explain it alone. H26 (dose curve) is now running. Audited AUDIT_H25.
- **Hypothesis:** detector sensitivity to label noise is monotone: injecting box jitter σ ∈ {0, 2, 5, 10 %} of height and 0/5/10 % dropped boxes into the 100 synthetic frames of h14b reduces the dose gain by ≥ 50 % only at σ ≥ 10 %.
- **Arms:** 4 jitter × 3 drop levels on the h14b mix (60 real + 100 batch_v8).
- **Seeds:** 5 per cell.
- **Metric:** MOT20-02 AP@640, gain vs real-only.
- **Stopping:** fixed.
- **Cost:** GPU, ~12 h.
- **Decision:** how much labelling precision synthetic data needs. Consistent with H15's null (labels inert) or refutes it.

## H26 · Dose curve beyond 300 (`h26_dose_fixedstep`) — **DONE `dbd21c4`, AUDIT_H26**
- **Status:** ran reduced (0/100/300/600/1,000 × 5 seeds, 450 steps; 3,000 arm cut). Gains vs equal-step real-only 0.4911: +0.0041 (p 0.048), +0.0045 (0.040), +0.0015, −0.0003; none Holm-significant → no recommended dose. Real-only itself gains +0.0049 from 228 → 450 steps, so h14b's +0.0121 compared unequal steps. The 1,000 fade is not the step confound. Follow-ups H51, H52.
- **Hypothesis:** with a fixed step count (H7's confound removed) and batch_v8 labels, the gain vs 60 real frames peaks between 100 and 1,000 synthetic frames and is ≥ 0 up to 3,000.
- **Arms:** 0, 100, 300, 600, 1,000, 3,000 batch_v8 frames + 60 real, same optimiser steps.
- **Seeds:** 10 per arm (64 §8 item 4).
- **Metric:** MOT20-02 AP@640; Holm over 5 contrasts vs 0.
- **Stopping:** fixed.
- **Cost:** GPU, ~20 h.
- **Decision:** the recommended synthetic dose. Also whether "fades at 1,000" (H7) was the step-count confound.

## H51 · Equal-step re-run of the dose results (`h51_equalstep_rerun`) — from H26
- **Hypothesis:** at equal optimiser steps (450, as H26) and 10 seeds, 100 batch_v7 frames (h14b recipe), 300 batch_v8 visible-label frames (H15 recipe) and 100 batch_v8 frames (H25 clean recipe) each beat real-only with Holm-significant gain ≥ +0.003 AP. Re-establishes or retires the dose gain that H26 cut to +0.004–0.005 (n.s.).
- **Arms:** real-only 450 steps; h14b mix_100 (v7), H15 v8_vis_300, H25 j00_d00 (v8, 100), each at 450 steps by epochs/padding (H26 `schedule`); same warm-up (225 iterations) in every arm.
- **Seeds:** 10 (perm-p floor 1/92,378 unpaired).
- **Metric:** MOT20-02 AP@640; Holm over 3 contrasts vs real-only.
- **Stopping:** fixed.
- **Cost:** GPU ~6 h (40 runs × ~5 min + contention).
- **Decision:** all three n.s. ⇒ retire "synthetic helps as an additive" to "no measurable effect at 60 real frames"; any significant ⇒ that recipe is the equal-step headline. Also resolves H26's unreconciled 0.0025 gap between H15 v8_vis_300 and H26 dose300.
- **Registered 2026-09-27 (32 §H51, narrowed):** primary = real-only vs +100 v8 vs +300 v8 at H26's exact recipe, 10 seeds, paired sign-flip + Holm over 2, success = both ≥ +0.004 with Holm p < 0.05; h14b v7 recipe demoted to a 5-seed diagnostic arm (v7 +100 at H26 recipe) that explains the H26-vs-h14b gap. Config `h51_equal_steps.yaml`.
- **Status: DONE — met.** Paired, 10 seeds, 450 steps: +100 v8 **+0.0042** [+0.0024, +0.0062], +300 v8 **+0.0051** [+0.0037, +0.0064], both Holm p 0.0039 → the equal-step dose gain exists (small, one site). Diagnostic: v7 +100 at H26 recipe 0.4932 (−0.0021 vs v8) → the h14b 0.4983 gap is the recipe (300 its + 150-its warm-up + mosaic off, AUDIT_H51), not the pool. H52 unblocked.

## H52 · Image-level vs label-level ablation at equal steps (`h52_image_vs_label`) — from H25/H15/H26
- **Hypothesis:** whatever equal-step gain exists comes from images, not boxes: 300 batch_v8 frames with their boxes removed (background-only) give ≥ 50 % of the gain of the same frames with boxes.
- **Arms:** real-only; +300 v8 with visible boxes; +300 v8 images with empty label files; +300 v8 with labels shuffled across images — all 450 steps.
- **Seeds:** 10.
- **Metric:** MOT20-02 AP@640; paired by seed (same subset).
- **Stopping:** fixed; run only after H51 finds a significant gain (otherwise there is nothing to decompose).
- **Status: DONE (2026-09-27): label-driven.** True − shuffled +0.0077, Holm p 0.0098. Masked backgrounds +0.0036 (Holm 0.047). Real ×10 −0.0011 (32 §H52). **Audited (AUDIT_H52):** numbers reproduce; (c) masks are inpainted rectangles, so part of its gain may be artefact; (d) is a list-construction control; a − c +0.0015 exploratory only → H61. Earlier: unblocked — H51 met (+300 v8 gain +0.0051, Holm p 0.0039; AUDIT_H51). Not registered or run. The gain to decompose is ~0.005 AP with a 10-seed sd of ~0.0026 per arm, so the "≥ 50 %" contrast (~0.0025) sits near the paired noise floor; register the power question before the run. H51's real-only and +300-visible arms share this recipe and could be reused only if list construction is identical.
- **Registered 2026-09-27 (32 §H52, `h52_ablation`):** arms narrowed/changed to (a) H51 dose300 reused, (b) labels shuffled across images, (c) people inpainted out (no boxes), (d) real ×10 duplicated; 10 seeds, Holm over 5 contrasts; rule: label-driven / image-level / diversity-only / unresolved (32).
- **Cost:** GPU ~4 h.
- **Decision:** images carry it ⇒ invest in scene/pixel realism, not label precision (consistent with H15/H25 nulls).

## H61 · Is the masked-background gain real background, or inpainting artefact? (`h61_silhouette_mask`) — from AUDIT_H52
- **Why:** H52 (c) removed people by Telea-inpainting dilated rectangles (+10 %/side) at 1/4 resolution. That leaves smooth, blurred box-shaped patches a detector could learn as "no person here", and deletes background inside every box. So (c)'s +0.0036 (Holm 0.047) may be partly artefact, and a − c (+0.0015, unadjusted p 0.057) was not registered.
- **Hypothesis:** the person-free gain is background content: with people removed by their **rendered silhouette masks** (batch_v8 has them) and **no inpainting** — masked pixels set to a constant/mean or to the same frame with the person layer omitted where available — (c') still gains ≥ +0.003 over real-only.
- **Arms:** H51 real-only and dose300 reused (byte-identical arm JSONs, as in H52); (c) H52 mask300 reused; (c') silhouette-masked, no inpainting, no boxes; (c'') silhouette-masked + ignore regions (masked pixels excluded from the loss) if the trainer allows it, else dropped before the run.
- **Seeds:** 10, paired. **Primary contrasts (Holm over 3):** (a) − (c'), (c') − real, (c) − (c').
- **Rule:** background-real iff (c') − real ≥ +0.003 Holm p < 0.05; artefact iff (c) − (c') ≥ +0.003 Holm p < 0.05; labels-on-people iff (a) − (c') ≥ +0.003 Holm p < 0.05. All holding reported.
- **Power:** paired sd of a − c in H52 ≈ 0.0022, so +0.003 at 10 seeds is marginal; say so before the run.
- **Cost:** GPU ~2 h (20 new arms × ~4 min). **Status: DONE (2026-09-27).** Ran only (a), real-only and (c') (10 sil300 seeds; the ignore-region arm (c'') was dropped from scope, ~17 min wall, 10 new runs). sil300 (c') 0.4891 [0.4873, 0.4909] vs real-only 0.4911 and true labels (a) 0.4962. Primary, Holm over 2: **(a) − (c') +0.0071** [+0.0058, +0.0084] Holm p **0.0039**; **(c') − real −0.0020** [−0.0041, −0.0002] Holm p 0.074 (n.s., and negative). **Rule selects box-fill artefact, not background-real**: H52 (c)'s +0.0036 gain over real-only was the box-shaped Telea-inpainted fill, not real background content — context contrast (c) − (c') = +0.0056 [+0.0048, +0.0065], the box-fill alone exceeds (c)'s whole reported gain. The full H51/H52 +300 gain is labels-on-people. 32 §H61, FACTS_VERIFIED, docs/13 row, 52 §5b.

## H27 · Synthetic-only far arm at 1280 (`h27_far_syn1280`) — **ANSWERED by H19 (`cfa9c2a`); do not run**
- **Status:** H19 was not inconclusive: v8 synthetic-only at 1280 collapses to AP50 **0.000 in all 3 seeds** (as does the v6 H8 replicate) vs zero-shot 0.613, recall 0.000 at conf 0.25. The registered stopping rule ("run only if H19 is inconclusive") therefore retires H27. Five seeds would only lower the sign-flip floor on a contrast whose every diff is already exactly zero. The cause is synthetic-only training itself; 60 real frames fix it (0.817).
- **Hypothesis:** a synthetic-only batch_v8 far fine-tune at imgsz 1280 does not collapse (AP50 at scale 0.25 ≥ 0.5 × zero-shot) on all 5 seeds.
- **Arms:** zero-shot; v8 far synthetic-only 1280; v6 far synthetic-only 1280 (H8 replicate).
- **Seeds:** 5 (H19 had 3; sign-flip floor p 0.25 → 0.0625).
- **Metric:** AP50, scale 0.25, full_1280, H8/H18 harness.
- **Stopping:** run only if H19 is inconclusive; fixed 5 seeds.
- **Cost:** GPU, ~6 h.
- **Decision:** whether H8's collapse was labels/heights (fixed in v8) or synthetic-only training itself. Settles H18's open cause.

## H28 · Degrade-profile retune on batch_v8 (`h28_degrade_retune`)
- **Hypothesis:** retuning `cctv_day` on batch_v8 to minimise mean |z| to MOT20 (H13's screen) raises in-band stats from 6/14 to ≥ 9/14 **and** raises the h14b gain.
- **Arms:** current profile vs retuned profile, h14b recipe.
- **Seeds:** 5.
- **Metric:** primary AP gain vs real-only; secondary stats in band.
- **Stopping:** fixed; tuning uses MOT20-01 only.
- **Cost:** GPU ~8 h + CPU degrade (~1.6 h at 0.567 s/frame × 10k frames; M11 halves it).
- **Decision:** whether H13's ρ −0.60 is causal enough to tune against.

## H29 · Clothes-change ReID with more changers (`h29_reid_changers`)
- **Full design: `70` §7** (supersedes this sketch).
- **Hypothesis:** H29a OSNet fine-tuned with identity across epochs keeps held-out cross-epoch (CC) rank-1 ≥ 2× the epoch-blind fine-tune; H29b + CAL loss beats ImageNet OSNet on MEVID different-clothes (CAL 3.5 R1 / 4.3 mAP) with CI excluding 0; H29c height + gait + appearance fusion beats appearance alone.
- **Arms:** ImageNet OSNet; HSV; fine-tune epoch-blind; fine-tune across epochs; + CAL (outfit hash as clothes label); height-only; gait signature; fusion.
- **Seeds / data:** 3 training seeds; 260 train ids (130 changers), 100 test ids (**40 held-out changers**, ~0.047 SE per arm), 100 distractors with ≥ 20 % same-outfit hard negatives; identity = CC0 body × scale × morph × gait (16 bodies otherwise confound shape).
- **Motivation from H20 (`cfa9c2a`):** 15 synthetic ids gave +0.324 [+0.197, +0.493] synth cross-camera mAP but +0.021 [−0.047, +0.097] on MOT20 — no real transfer. Identity count is the limiter.
- **Metric:** CC mAP/rank-1 (LTCC rule: gallery excludes the query's epoch), id-level bootstrap; SC and general alongside; false links per 100 queries at 90 % recall for fusion.
- **Stopping:** fixed; tune on a 20-id train slice.
- **Cost:** ~30k crops ≈ 1.5 editor-days + GPU ~3 h per arm-set; blocked on per-identity scale/morph and MEVID annotation-licence confirmation.
- **Decision:** H29a without H29b ⇒ appearance truth is an evaluation asset, not a training one (as H20); H29b ⇒ epochs are a training product feature.

## H30 · Multi-site real evaluation (`h30_crosssite`)
- **Hypothesis:** the additive gain (h14b +0.0121 at unequal steps; +0.004–0.005 at equal steps, H26) is ≥ 0 with CI excluding 0 when real train and test come from **different** sites.
- **Arms:** real-only vs real + 100 batch_v8, for each train site → held-out site.
- **Seeds:** 5 per arm per site pair; ≥ 3 sites incl. one genuine far-field camera.
- **Metric:** AP@640 on held-out sites; site-level bootstrap.
- **Stopping:** fixed.
- **Cost:** GPU ~10 h, after M12 (data acquisition).
- **Decision:** whether claim (a) of 64 is publishable and whether training on synthetic is a product feature or only an evaluation aid.

## H31 · Gait from pixels (`h31_gait_pixels`)
- **Hypothesis:** a gait embedding from silhouettes of batch_v8 walkers identifies them across an outfit change better than appearance (rank-1 ≥ 2× HSV), once feet contact the ground (foot IK).
- **Arms:** appearance (HSV, OSNet); gait from GT pose; gait from mask silhouettes; before/after foot IK.
- **Seeds:** 3 training seeds; clips ≥ 2 gait cycles.
- **Metric:** cross-epoch rank-1.
- **Stopping:** fixed.
- **Cost:** GPU ~4 h after M14; real check on MOT20 gait extraction (written first).
- **Decision:** whether gait is a cue SurvSim can simulate credibly or a sliding-feet artefact.

## H32 · Night against a real IR reference (`h32_night_ir`) — **DONE as H32a/H32b (`f3353a2` → `1acb9bd`)**
- **Status:** H32a not met — `cctv_night_lowlight` 9/13 tune → 2/13 hold-out (vis), `cctv_thermal` 10/13 → 3/13 (IR); both overfit on 15 tune frames. H32b branch B3: YOLOv8n raw 0.938 → NIR 0.373 / lowlight 0.103 / thermal 0.468 (Δ −0.565 / −0.835 / −0.470), none an estimate of a real night penalty; P1 refuted, P2 holds. Ran 1 degrade seed (not 3), 9 cameras with GT. Audited AUDIT_H32 (device and camera-count corrections, thermal mask leak). Successor: H36.
- **Hypothesis:** `cctv_night_ir` retuned against ≥ 200 licensed real IR frames reaches ≥ 9/14 stats in band and cuts H11's sensor-model −0.609 recall loss by half.
- **Arms:** current IR profile vs retuned; zero-shot detector on real IR as the reference.
- **Seeds:** 3 degrade seeds; detector frozen.
- **Metric:** recall on degraded batch_v8 night vs real-IR recall; stats in band.
- **Stopping:** fixed.
- **Cost:** CPU/GPU ~4 h after M16.
- **Decision:** whether night claims can be made at all (23 v2 §7 item 4); until then they stay withheld.


## H36 · Full LLVIP held-out fit (`h36_llvip_full`) — **needs sign-off for the ~3.5 GB LLVIP download**
- **Hypothesis:** with ≥ 200 LLVIP frames per modality and bands held out **by scene** (not by filename order), `cctv_night_lowlight` reaches ≥ 9/13 hold-out vis and `cctv_thermal` ≥ 8/13 hold-out IR, with tune − hold-out ≤ 2.
- **Arms:** H32 profiles as-is; refit on the larger tune split with a realism prior (per-channel chroma-noise cap, fixed search budget and logged draws); thermal with a mask-free heat model (to remove the GT-mask leak, AUDIT_H32).
- **Seeds:** 3 degrade seeds; detectors frozen (YOLOv8n, YOLO26n).
- **Metric:** hold-out band count; then, only for an in-band profile, recall Δ vs raw on batch_v8 night (9 cams, camera-cluster bootstrap) — the first quotable night penalty.
- **Stopping:** fixed. **Cost:** download + ~1 h CPU stats + ~1 h GPU recall.
- **Licence:** LLVIP is non-commercial research: measurement only, nothing trained on it; a commercial claim still needs a licensed set (M16).
- **Decision:** whether the simulator can quote a night recall penalty at all.


## H33 · Conformal θ for the FA budget (`h33_conformal_theta`) — **DONE (`4da4eef` → `93cc3b1`)**
- **Status:** supported at α = 2.915 (CRC 0/10 exceed vs plug-in 6/10, recall −0.035); ran 10 splits and α ∈ {0.001, 1, 2, 2.915} (deviation declared in 32); 0.001 uncertifiable (floor ≥ 0.248). Audited AUDIT_H22_H33.
- **Hypothesis:** conformal risk control (Angelopoulos et al. 2022) choosing A1's θ on a calibration split keeps held-out FA/cam-h ≤ target α in ≥ 90 % of splits, where the 58 grid-picked θ does not.
- **Arms:** grid θ (58 round 3) vs conformal θ; α ∈ {1, 2, 3} FA/cam-h.
- **Seeds:** 20 random calibration/test splits of the 3,002 cam-h (H12), split by camera.
- **Metric:** fraction of splits with test FA ≤ α; recall at that θ.
- **Stopping:** fixed.
- **Cost:** CPU < 1 h, today.
- **Decision:** whether per-site θ ships with a stated guarantee (67 §1 Q3).

## H34 · Label-free drift monitor (`h34_drift_monitor`) — **DONE (`5108fc9`/`cf33bb2`): inconclusive**
- **Status:** ran as re-scoped in 32 (13 image stats + embedding, 4 kinds × 3 severities, not confidence PSI × 5). PSI/KS fire on 100 % of stationary windows (1,440/24 cam-h at 1 check/min); z_cal 6/12 at 9.2, misses blur; emb 0/12, ≤ 26.6 certifiable; ρ 0.61 (z_cal, emb). Audited AUDIT_H34. Follow-up: H44.
- **Hypothesis:** PSI on detector-confidence histograms flags each degrade profile (fog, night IR, compression) as shift before recall falls by 0.05.
- **Arms:** clean batch_v8 reference vs each profile at 5 severity steps; monitors: confidence PSI, detection-count rate, track-length KS.
- **Seeds:** 3 degrade seeds.
- **Metric:** severity at alarm vs severity at recall −0.05; false-alarm rate of the monitor on clean held-out.
- **Stopping:** fixed.
- **Cost:** CPU/GPU ~2 h.
- **Decision:** which field-monitoring signal ships (67 §1 Q7, §2 Q6).

## H44 · Certify the drift monitor (`h44_drift_certify`)
- **Hypothesis:** with ≥ 4,314 independent stationary windows per arm, the embedding arm (threshold at a null quantile, not the null max) keeps ≤ 1 false trigger per 24 cam-h (1 check/min) while detecting ≥ 8/12 H34 shifts; detection-rate and track-length monitors detect blur 2-3, which image stats miss.
- **Arms:** H34 z_cal and emb re-thresholded at null quantiles; detection count per window; median track length (ByteTrack); k-of-n window voting.
- **Seeds:** ≥ 10 degrade sequence seeds per camera; longer (≥ 10 min) stationary renders.
- **Metric:** as H34 (delay, FA/24 cam-h with rule-of-three upper bound, Spearman vs recall drop, per-camera cluster CI).
- **Stopping:** fixed.
- **Cost:** CPU + GPU light (detector passes).
- **Decision:** which drift signal and threshold rule ship (71, 74 Drill 3).

## H35 · Per-camera vs global θ (`h35_percam_theta`)
- **Hypothesis:** per-camera θ set on a simulated 2-week burn-in lowers the max per-camera FA/cam-h by ≥ 30 % at equal total recall vs one global θ.
- **Arms:** global θ; per-camera θ (budget split equally); per-camera θ weighted by camera traffic.
- **Seeds:** 5 scenario seeds.
- **Metric:** max and total FA/cam-h, recall (actor-aware).
- **Stopping:** fixed.
- **Cost:** CPU ~1 h.
- **Decision:** whether commissioning includes per-camera calibration (67 §3 Q3, Q12).
- **Motivation from H33 (`93cc3b1`):** CRC bounds the *expected per-world* FA over exchangeable sites; worlds are far from uniform (worst calibration world 84–89 FA/cam-h vs pooled 2.9; per-world mean 3.42 vs pooled 2.92), so a global θ that is safe on average can leave individual cameras far over α. H35 asks whether per-camera θ trims that tail without losing recall — and a per-camera CRC needs per-camera calibration data, which is the 2-week burn-in.

## H37 · Forensic attribute search recall and the epoch trap (`h37_forensic_search`)
- **Hypothesis:** On SurvSim runs with appearance-epoch changes, uid-level
  recall@10 for attribute+time+place queries is ≥ 0.15 lower when attributes
  are pooled per *track* than per *epoch-segmented track*. A CLIP text query
  has lower recall@10 than a PAR-attribute filter on the same queries.
- **Arms:** (A) PAR attributes pooled per track; (B) PAR pooled per epoch
  segment (split at attribute change-points); (C) CLIP ViT-B text→crop cosine;
  (D) B ∧ C re-rank. All on the same tracker output.
- **Seeds:** 5 scenario seeds × 60 generated queries (colour × garment × window
  × camera group), ≥ 30 % with an epoch boundary inside the window.
- **Metric:** uid recall@10, mAP, and journey edit distance for 20 probes;
  bootstrap 95 % CIs (49 §5).
- **Stopping:** fixed.
- **Cost:** CPU for the mock backend (attribute oracle + noise) now; GPU light
  on batch_v8 renders for C/D. CC0 characters only (MetaHuman renders
  excluded, licence).
- **Decision:** whether the product segments attributes at change-points, and
  whether NL search ships as a primary query or as a re-ranker.
- **49 §12 fields added (AUDIT_72):** *primary metric* = uid recall@10 on the
  epoch-boundary query subset (mAP, edit distance are secondary); *control
  arm* = A; *held fixed* = tracker output, PAR/CLIP checkpoints, query set;
  *analysis* = paired bootstrap over queries (seed-clustered), α = 0.05, Holm
  over B−A, C−B, D−B; *success* = B−A ≥ 0.15 with CI lower bound > 0;
  *sample size* = 300 queries, ≥ 90 with a boundary; *confounds* = mock
  attribute-oracle noise level (report two levels); *abandon if* B−A CI
  includes 0 at both noise levels.
- **Status (2026-09-27): mock-only slice (A vs B, no CLIP) done, `32` §H37.**
  50 mock worlds × 40 identities (35 % changers), 1500 queries (30 % boundary,
  1363 scored): recall@10 diff (B−A) +0.0004 [+0.0001, +0.0008] clean, −0.0118
  [−0.033, +0.009] at 10 % attribute-flip noise — **not met** on the 0.15
  magnitude bar at both noise levels (two orders of magnitude short); the
  pre-registration's literal abandon condition ("CI includes 0 at both noise
  levels") holds only at 10 % noise — at zero noise the CI barely excludes 0,
  a mechanical artefact of pooled being a strict superset of epoch's
  candidates, not a meaningful effect. The mechanism is demonstrated directly
  at the unit level (`tests/test_forensic_search.py`) but does not register
  as a population recall@10 gap here because relevant sets are small by
  construction (mean 2.67, median 2.0, max 9 over the 1363 scored queries —
  all ≤ 10, so recall@10 saturates for both arms; 137/1500 queries had an
  empty relevant set and were excluded). This is a ceiling effect, not
  evidence the trap doesn't matter — see **H37b** below.

## H37b · Forensic attribute search: a design that can discriminate pooled vs epoch-segmented (`h37b_forensic_mock`)
- **Motivation:** H37's mock slice (above) can't separate pooled from
  per-epoch pooling at recall@10 because relevant sets are small (mean 2.67,
  max 9, all ≤ 10 at 40 identities x 6 attribute combinations) — a ceiling
  effect built into the design, not a finding that epoch segmentation is
  unnecessary.
- **Design change:** (1) score recall@1 and MRR, where the pooled index's
  extra false-positive candidates can outrank a true hit even when |R| is
  small; and/or (2) widen the identity:attribute-vocabulary ratio (more
  identities per world, or fewer colour x garment combinations) so |R|
  routinely exceeds 10, giving recall@10 room to show a gap; (3) add the
  CLIP arms (C, D) once batch_v8-class CC0 renders exist (mock-only cannot
  produce them).
- **Status:** not run (registered here only).

## H38 · Quantised export accuracy (`h38_quant_export`)
- **Hypothesis:** exporting the h14b mixed-data YOLOv8n to ONNX FP16 loses ≤ 0.005 AP@640 on MOT20-02 and to INT8 (static PTQ, 100 real MOT20 train frames) ≤ 0.015, across 3 checkpoints; calibrating INT8 on synthetic batch_v8 frames loses ≥ 0.01 more.
- **Arms:** FP32 PyTorch (control), ONNX FP32, ONNX FP16, INT8 real-calibrated, INT8 synthetic-calibrated.
- **Seeds:** 3 checkpoints (h14b mix_300_s0–s2).
- **Metric:** MOT20-02 AP@640 loss vs control, paired; CPU latency for context only.
- **Stopping:** fixed.
- **Cost:** CPU ~1 h, onnxruntime.
- **Decision:** whether 38 §2.5's INT8 budget carries an accuracy cost we must plan for, and whether site footage is needed for calibration (68 Q10 follow-up 2).
- **Status (2026-09-27): done** (`d6b204d`; AUDIT_H38). FP16 **met** (loss 0.0000, range −0.0002..+0.0003); INT8 **not met** (0.0117, range 0.0081..0.0154; s2 0.0154 > 0.015), almost all AP75 (−0.030; AP50 ≤ −0.0042); calibration branch **not met** (synthetic − off-site real +0.0015, n.s.; on-site calibration untested). n = 3 ⇒ the "bootstrap CI" is the range. CPU latency uninformative (4.7× spread across identical graphs). Follow-up: H43.

## H43 · TensorRT INT8 on real Jetson hardware, else QAT (`h43_trt_int8`) — follow-up to H38, not yet registered
- **Status (2026-09-27): the "else QAT" branch ran to completion as H43/H43b/H43c/H43d (all CPU-only,
  onnxruntime), all done, none met either recovery bar; H43d refuted the "more QAT iterations helps"
  inference. The TensorRT-on-real-Jetson-hardware arm below never ran (no hardware) and is now the
  **only remaining edge item** — relabelled **H43e** so it is tracked as its own hypothesis rather than
  buried inside a partly-completed H43. Needs an Orin NX (or equivalent) and cannot be done CPU-only.
- **H43e hypothesis:** on an Orin NX 16 GB (TensorRT, entropy calibrator, same 3 h14b checkpoints, same 100 MOT20-01 calibration frames) INT8 loses ≤ 0.015 MOT20-02 AP@640 on all 3 and runs ≥ 1.1× faster than FP16 at batch 1.
- **Arms:** TRT FP16, TRT INT8 (entropy), TRT INT8 (MinMax, H38 parity), and — without hardware — onnxruntime INT8 QDQ from a QAT checkpoint vs H38's PTQ.
- **Seeds:** 3 checkpoints (h14b mix_300_s0–s2); latency = median of 200 after 20 warm-up with `trtexec`, jetson_clocks on, power mode stated.
- **Metric:** paired AP / AP50 / AP75 loss vs FP32; ms/im and W at batch 1 and at DeepStream multi-stream (feeds 38 §2.5 rows 4–12).
- **Stopping:** fixed. **Cost:** Jetson hours, or GPU ~1 h (QAT).
- **Decision:** whether INT8 or FP16 is the shipped Orin precision, and whether 38 §2.5's 10–12 cameras/NX is measured rather than [A] (closes 77 weak answer #3).
- **Registered 2026-09-27 in 32** (no-Jetson branch, `h43_qat`): n = 5 (3 h14b + 2 H51 dose300); arms FP32, INT8 MinMax (H38), INT8 Percentile [primary PTQ], INT8 Entropy, INT8 QAT (150 its, fake-quant, LR/10). Met iff Percentile recovers ≥ 50 % of AP75 loss; QAT ≥ 80 % and AP loss ≤ 0.005 on every checkpoint. Supersedes the ≤ 3-epoch / 0.006 wording above.

## H43d · Does more QAT fine-tuning close the H43c gap? (`h43d_qat_more_iters`) — registered and done, refuted
- **Status (2026-09-27): done, hypothesis refuted** (`32` §H43d). 600 QAT iterations (fresh fine-tune,
  same recipe/export as H43c) does **not** raise recovery — pooled AP75 recovery **fell** to 0.374
  (from H43c's 0.439 at 150 iters), and the per-checkpoint effect is not uniform: the 3 h14b checkpoints
  improved (0.266→0.331, 0.322→0.531, 0.561→0.782) while both H51 `dose300` checkpoints got worse, one
  going **negative** (−0.500: `int8_qat_qdq` costs *more* AP75 than plain MinMax PTQ). H43c's "residual
  gap is the 150-iteration recipe" attribution does not hold as a uniform effect — the true driver is
  checkpoint-recipe-dependent (h14b mixed-data vs H51 batch_v8 equal-steps), not simply iteration count.
  Only 600 iterations run (1,000 not attempted: the reversed direction on 2/5 checkpoints made a
  1,000-iter arm low-value within budget). No change to the deployment recommendation (ship FP16, use
  Percentile PTQ over any QAT variant if INT8 is required) — the result strengthens the case against
  QAT rather than reversing it.
- **Status (2026-09-27, superseded above): proposed by AUDIT_H43BC.** H43c's write-up (`32` §H43c) attributed its residual
  AP75 gap (recovery 0.439, still < the 0.50/0.80 bars) to the 150-iteration QAT recipe rather than the
  export path, on the strength of one data point (more iterations were never run) — that attribution is
  an inference, not a measurement, and this hypothesis tests it directly.
```
id:            h43d_qat_more_iters
commit:        <hash of the registration, before the run>
hypothesis:    on the same 5 checkpoints as H43b/H43c, running the QAT fake-quant fine-tune for
               600-1,000 iterations instead of 150 (same recipe: AdamW, H51 auto LR / 10, batch 8,
               imgsz 640), then exporting the QDQ graph from the learned observer ranges exactly as
               H43c (`TensorQuantOverrides`, no fresh MinMax pass), raises the mean AP75 recovery
               vs int8_minmax above H43c's 0.439, moving it materially toward (not necessarily past)
               the 0.50 secondary bar
primary metric: AP75 recovery vs int8_minmax, pooled-loss formula (as H43/H43b/H43c), MOT20-02 @640
arms:          int8_qat_qdq @150 iters (H43c, control); @600 iters; @1,000 iters
held fixed:    5 checkpoints, calibration frames, learned-range export path and its Conv-order
               weight-byte matching (verified in H43c), CPU-only onnxruntime eval
seeds:         the 5 H43b/H43c checkpoints (no new seeds; not re-drawing training data)
sample size:   n = 5 checkpoints, same as H43b/H43c (small; report per-checkpoint, not just pooled)
analysis:      per-checkpoint AP75 recovery + pooled-loss recovery, as H43c; qat_fp32 (fake-quant
               stripped) AP/AP75 vs fp32_torch reported per iteration count as the confound check
               (more steps alone should raise qat_fp32, as it did at 150 iters in H43b)
success:       recovery(600 or 1000 iters) > recovery(150 iters) with the improvement not fully
               explained by the qat_fp32 confound (i.e. int8_qat_qdq gains more than qat_fp32 does)
stopping rule: fixed
confounds:     same as H43b/H43c — extra optimiser steps alone improve qat_fp32 independent of
               ranges; report it, don't let it get counted as ranges/iteration count improving recovery
abandon if:    600-1,000 iterations does not fit the GPU/wall budget for all 5 checkpoints; run 600
               only and report partial
```

## H39 · Ground-plane auto-calibration from pedestrians (`h39_autocalib`)
- **Hypothesis:** a detector-free known-height auto-calibration (mask-box feet/heads + one mean height 1.70 m; yaw and position from the install record) reaches ≤ 0.5 m world-position RMSE within 20 m of the camera on batch_v8 and degrades ≥ 3× beyond 30 m.
- **Arms:** exact calib homography (floor), DLT from GT foot correspondences (upper bound), auto-calibration on all 30 s, auto-calibration on the first 10 s.
- **Seeds:** deterministic fit; bootstrap over tracks (seed 39).
- **Metric:** world RMSE (m) by ground-distance bin; per-track height error vs identities height_m.
- **Stopping:** fixed.
- **Cost:** CPU minutes.
- **Decision:** whether auto-calibration is good enough for metric speed/height and world-coordinate tracking (73) or whether sites need a survey (75).
- **Status (2026-09-27): done, not met** (`2bdb46b`; AUDIT_75_H39). Free-f A2 57.4 m [46.2, 68.0] RMSE < 20 m (bar 0.5); f unidentifiable from box heights (5/10 cameras at the bound); exact floor 0.208 m; DLT-on-GT 0.117 m; A3 74.7 m; height MAE 0.077 (A2) vs 0.024 (exact) = trap metric. Datasheet-f arms (0.958 m / 2.92 m) are post hoc and do not count. Follow-up: H41.

## H41 · Head–foot keypoint auto-calibration (`h41_keypoint_autocalib`) — follow-up to H39, not yet registered
- **Hypothesis:** replacing box top/bottom-centre with head and ankle-midpoint keypoints from our COCO keypoint GT (body axis, not box axis) restores the vertical vanishing point (Lv/Zhao/Nevatia) and makes free f identifiable: A2 with keypoints reaches ≤ 0.5 m RMSE < 20 m on the same 10 batch_v8 cameras, and f within 10 % of calib on ≥ 8/10.
- **Prerequisite (checked on audit):** batch_v8 `gt/` has no keypoint file; keypoints must come from the bone export / COCO-keypoint writer on a fresh render of the same scenes (engine) or be projected from world bones — confirm before registering.
- **Arms:** H39 A2 (box) re-run as control; K1 keypoints, free f, mean-height prior; K2 K1 + per-person height distribution (Liu et al.); K3 K1 with keypoint noise σ = 3 px (detector-like).
- **Metric:** as H39 (RMSE by range bin, bootstrap over tracks; f / pitch / h error per camera); height MAE reported but not used to judge (trap metric).
- **Stopping:** fixed. **Cost:** CPU minutes, no GPU, no engine.
- **Decision:** whether pedestrian auto-calibration can replace a survey when a pose model is available, or whether datasheet f + surveyed points stays the recommendation (75 Q2).

---

**Sources:** 32 (H1–H20), 58 §6–7, 64 §7–8, 23 v2, 49 §2 and §12, 13 §A4, 52 §5–6.

## H40 · Sterile-zone line-crossing rule (`h40_line_cross`) — **registered 2026-09-27 in 32**
- **Hypothesis:** on the 676 H12 clean worlds (~3,002 cam-h) with a declared tracker-noise model, a naive line-cross/zone-entry rule is >= 10x over the 0.001 FA/cam-h budget; track-quality gating + direction/dwell + gate context cuts FA >= 5x with recall@10 s >= 0.9 on intrusion/perimeter-probe worlds.
- **Arms:** N naive, A +age/height gating, B +inward direction/1.5 m depth/5 s dwell, C +gate/path exclusion.
- **Seeds:** 40 (noise, recall worlds, bootstrap).
- **Metric:** actor-aware FA/cam-h (Garwood, world bootstrap), recall@10/30 s, FA ratio N/C.
- **Stopping:** fixed. **Cost:** CPU < 1 h.
- **Decision:** whether a video-only sterile-zone rule can be quoted against the budget or needs PIDS/radar fusion (74).
- **Status (2026-09-27): done, not met** (`2323de7`; AUDIT_76_H40). Naive 70.96 FA/cam-h, C 4.20 [3.84, 4.57] (÷16.9 [15.3, 18.6]); recall@10 0.945 → 0.100. Causes are generator gaps (intruder stops at the edge; unfenced polygons; no patrol/animal/weather twins), so the FA is optimistic. Follow-up **H40b** registered below (32 §H40b).

## H40b · Line-cross rule on crossing intruders and fenced zones (`h40b_line_cross`) — **registered 2026-09-27 in 32**
- **Motivation:** H40 failed on generator gaps: intruders stopped at the zone edge, polygons were unfenced, and there were no patrol or animal twins. The behaviour engine now fences restricted zones, makes intrusions cross (>= 3.5 m inside, post-cross arc), and adds `fence_climb`, `patrol_guard`, `maintenance_visit` and `wildlife`.
- **Hypothesis:** H40's full rule (arm C) reaches recall@10 s >= 0.9 on intrusion / fence-cut / fence-climb worlds, with primary clean FA/cam-h <= 2.915 (the round-3 loiter A1 level). Primary FA excludes the authorised twins; their FA is reported separately.
- **Arms:** H40's N / A / B / C, unchanged; same noise model (assumed, not fitted).
- **Data:** 676 H12 clean worlds regenerated (same seed) + twins/wildlife on a separate stream; 300 recall worlds (H40's 200 seeds + 100 fence_climb).
- **Seeds:** 40. **Stopping:** fixed. **Cost:** CPU ~1 h.
- **Decision:** whether the sterile-zone rule is limited by the rule or by authorised crossers. The twin FA is the residual that only role/schedule context (or PIDS fusion, 74) removes.
- **Status (2026-09-27): done, not met** (`12b6c92`; AUDIT_H40B). C primary clean FA **0** in 3,002 cam-h (rule of three ≤ 0.001), but recall@10 **0.782 [0.736, 0.829]** < 0.9. Shortfall: depth/dwell rule 10.1 pts on noise-free tracks, gate context 4.7, assumed tracker noise 7.0. Twin FA on C: patrol 0.389 [0.367, 0.412], maintenance 0.099 [0.088, 0.111] FA/cam-h (~490× budget); 398 of C's 424 recall-world FPs are twins. Wildlife 5.96 FA/cam-h on N, 0 from arm A. Follow-ups H49 (twins), H50 (dwell).

## H49 · Schedule / route-prior twin suppression: patrol schedule + gate-log fusion (`h49_twin_suppression`) — follow-up to H40b, not yet registered
- **Status (2026-09-27): gate-log arm answered by H53** (C+a: twin FA 0.488 → 0.0100, 49× cut, but recall −0.037 > 0.02, and tailgate recall 0.000). Only the schedule/route arm and the patrol-gap adversary remain; register those alone if at all.
```
id:            h49_twin_suppression
commit:        <hash of the registration, before the run>
hypothesis:    on H40b's 676 regenerated clean worlds, suppressing an arm-C alarm when it
               matches (a) a gate-log badge event at the entering gate within ±Δt or (b) the
               published patrol schedule/route (time window + distance to route ≤ d) cuts the
               twin FA/cam-h (patrol + maintenance, 0.488 on C) ≥ 10× while C recall@10 on the
               300 recall worlds drops ≤ 0.02 absolute
primary metric: twin FA/cam-h on C (clean worlds), actor-aware, 10 s window, Garwood 95 %
arms:          C (control, H40b); C+schedule; C+gate-log; C+both
held fixed:    H40b worlds, tracks, noise model (assumed), arms N-C, scoring code
seeds:         40 (H40b); schedule/badge jitter from a separate stream; 2 adversary variants
               in recall worlds: intruder tailgates a badge entry; intruder times the patrol gap
sample size:   1,000 twin agents / 1,465 twin FAs on C — Garwood width known a priori
analysis:      twin FA ratio C / arm with world-cluster bootstrap 95 %; recall McNemar per
               actor vs C; Holm over the 3 arms
success:       ≥ 10× twin-FA cut with CI lower ≥ 5×, AND recall drop ≤ 0.02 on base recall
               worlds; report recall on the two adversary variants separately (no bar)
stopping rule: fixed
secondary:     tailgate/patrol-gap recall (the price of trusting the prior); badge-log
               latency sensitivity
confounds:     schedule and gate log are simulated and perfectly timestamped; a real log has
               clock skew, missing swipes and ad-hoc patrols; twins in the mock always use the gate
abandon if:    the twin cut needs a Δt/d so wide that the adversary variants lose > 0.2 recall
```

## H50 · Fragment-robust dwell via track stitching (`h50_dwell_stitch`) — follow-up to H40b, not yet registered
```
id:            h50_dwell_stitch
commit:        <hash of the registration, before the run>
hypothesis:    re-linking track fragments (gap ≤ 1 s, distance ≤ 1 m, same side of the fence)
               before arm B/C's 1.5 m-depth / 5 s-dwell test raises noisy C recall@10 from
               0.782 toward the noise-free 0.852 (≥ +0.05 absolute) with primary clean FA still
               ≤ 0.001/cam-h (rule of three)
primary metric: C recall@10, 300 H40b recall worlds, actor-aware, world bootstrap 95 %
arms:          C (control); C+stitch(1 s, 1 m); C+stitch(2 s, 1.5 m)
held fixed:    H40b worlds and assumed noise model; truth; scoring
seeds:         40 (H40b) + 2 fresh noise seeds on the same tracks
sample size:   298 events; paired per-actor contrast
analysis:      paired bootstrap on recall; McNemar per actor; Holm over 2 contrasts
success:       Δrecall ≥ +0.05, CI lower > 0, FA ≤ 0.001 (rule of three)
stopping rule: fixed
secondary:     noise-free B's 10-point loss (A 1.000 → B 0.899) broken down by arc (probe 0.827)
confounds:     stitching is tuned to the assumed noise model; a real tracker's fragments
               may be longer or ID-switched across people
abandon if:    stitching raises clean FA above the rule-of-three bound
```
Ceiling: H50 can recover at most the 7.0 noise points (noise-free C is 0.852), so it **cannot** meet
H40b's 0.9 bar alone; the rule's own 10-point loss on noise-free tracks (probe arcs) needs a
depth/dwell redesign as well.

## H42 · Pooled-fold / conformal θ selection across seeds (`h42_theta_policy`)
- **Motivation (round 4, `bd4c028`):** one grid search on a ~106-event select fold picks θ 0.9 (5.033 FA/cam-h) or θ 0.95 (2.915) for the *same* A1 weights (H23 7/10 vs 3/10); this spread exceeds every model gap measured in rounds 3–4.
- **Hypothesis:** choosing θ on the select folds of all 10 H23 train splits pooled (≈ 1,070 events), or by CRC (H33) on the pooled clean calibration worlds, gives an H12 FA whose leave-one-split-out spread is ≤ ¼ of the per-fold spread (5.033 − 2.915 = 2.118), at recall ≥ 0.80.
- **Arms:** per-fold grid (round 4 control); pooled-fold grid; pooled CRC at α = 2.915; A1's weights throughout.
- **Seeds:** the 10 H23 splits, leave-one-split-out (10 draws).
- **Metric:** H12 FA/cam-h and recall per draw; range and SD across draws.
- **Stopping:** fixed 10 draws.
- **Cost:** CPU, < 1 h (feature tables exist).
- **Decision:** the arm with the smallest spread at recall ≥ 0.80 becomes the shipped θ-selection policy; every future challenger to A1 is compared under it and must win on ≥ 4/5 seeds.
- **Status (2026-09-27): registered in 32 §H42** — four policies (per-fold, pooled LOFO, CRC LOFO at α = 2.915, pooled + recall-floor 0.80 on a 0.85–0.99 grid); primary bar is ≥ 2× spread cut, 66's ≤ ¼ reported as secondary.
- **Result (2026-09-27): met by pooled selection** (32 §H42 results, 58 §8.3): pooled LOFO picks θ 0.9 on 10/10 draws (5.033 / 0.894; spread 2.118 → 0); CRC and pooled+floor cut FA (2.13, 2.36) but miss H12 recall 0.80 on every draw. Pooled is the shipped policy; its point is +2.118 [+2.005, +2.237] FA and +0.069 [+0.045, +0.095] recall vs A1. Whether to lower the 0.85 select-recall criterion is the open follow-up.
- **Audit (AUDIT_H42):** numbers recompute; LOFO pools overlap 8/9, so zero spread is partly by construction; θ 0.9 is a SEL_GRID artefact (pooled 0.93/0.94 also pass 0.85, unscored on H12). The ship point is an operator-budget trade-off among three points (58 §8.4) → H45.

## H45 · Operator-budget elicitation at the H42 operating points (`h45_operator_points`) — **DONE (`090e358` → `85e6b18`; AUDIT_H45): not met**
- **Motivation:** H42 leaves three measured A1 operating points (A1 θ 0.95 2.915 / 0.825; pooled θ 0.9 5.033 / 0.894; CRC α 2.915 θ ≈ 0.964 ≈ 2.15 / 0.78). H22 simulated the operator only at A1's rate (~120 alarms/h per 40 cams, realised @5 min 0.511 FIFO / 0.586 ranked), so realised recall at the other two is bracketed [INF], not measured.
- **Hypothesis:** with H22's operator model unchanged, realised recall @5 min (ranked queue) is higher at the conformal point than at A1, and lower at the pooled point than at A1, despite pooled's +0.069 model recall.
- **Arms:** {A1, pooled θ 0.9, CRC θ (modal 0.963), pooled+floor θ 0.96} × {FIFO, ranked} × operators per 40 cams {1, 2}.
- **Seeds:** H22's 10 operator seeds; world-cluster bootstrap over the 300 recall worlds.
- **Metric:** realised recall @30 s and @5 min, utilisation, bulk-ack share; the operating point that maximises realised recall per staffing level.
- **Stopping:** fixed. **Cost:** CPU ~20 min (H22 was 292 s).
- **Decision:** which θ ships at a given staffing level — turns 58 §8.4's trade-off into a table a site can pick from. Invented-operator caveat carries over.
- **Status (2026-09-27): registered in 32 §H45** (`h45_operator_points`): three points (A1 0.95, pooled 0.90, CRC modal 0.962851) × FIFO/ranked × 1–3 operators; primary: pooled − A1 @5 min within ±0.02 (one operator) and CRC − A1 ≥ −0.03 with utilisation cut ≥ 20 %. Pooled+floor dropped (not one of 58 §8.4's three).
- **Result:** not met — pooled is worse than A1, not neutral (ranked −0.083 [−0.103, −0.064], FIFO −0.186, one operator); conformal gains (+0.035 ranked, +0.061 FIFO, 10/10 seeds) but cuts utilisation 10 % (< 20 %). Pooled never beats A1 with CI > 0 at 1–3 operators. **Ship:** 1 operator/40 cams → conformal θ 0.9629 ranked (0.621 realised @5 min); ≥ 2 operators → A1 θ 0.95 ranked; never pooled θ 0.9 (58 §8.4–8.5). Conformal θ 0.962851 is the most permissive of 10 distinct CRC draws ("modal" was a tie-break). Invented operator → H48.

## H48 · Validate the operator model against a real SOC's review-time distribution (`h48_operator_validation`) — follow-up to H45, not yet registered; blocked on data
- **Motivation:** H22/H45's staffing table (1 operator/40 cams → conformal θ 0.9629 ranked (0.621 realised @5 min); ≥ 2 operators → A1 θ 0.95 ranked; never pooled θ 0.9) rests on an invented operator: 30 s gamma review (cv 0.3), fatigue ×1.25 after 2 h, miss 0.05/0.15, clear-all above 10 queued. If real review times are heavier-tailed or clear-all is triggered earlier, the crossover (1 vs 2 operators) moves.
- **Data needed (from one real control room / SOC, anonymised):** a per-alarm log with alarm-raised time, review-start and review-end (or acknowledge) timestamps, operator ID and shift start, disposition (true / false / bulk-cleared / timed-out), camera ID and the analytic's score if logged; ≥ 1 month and ≥ 2,000 reviewed alarms across ≥ 3 operators so per-hour-of-shift fatigue is estimable; site staffing (operators per camera per shift) and the alarm rate per camera-hour over the same period; any clear-all / bulk-ack events with queue length at the time. Missed-alarm rate needs a seeded-test subset (known staged events, e.g. a red-team walk) — without it the miss parameter stays invented.
- **Hypothesis:** with review-time distribution, fatigue slope and bulk-ack threshold fitted to that log (held-out month for validation), the simulator's predicted utilisation and bulk-ack share match the held-out month within ±0.05 absolute, and the H45 ship table (which point wins at 1 and 2 operators) is unchanged.
- **Metric:** KS distance of review-time distribution; predicted vs observed utilisation and bulk-ack share per shift; re-run H45 with fitted parameters.
- **Decision:** if unchanged, the staffing table is quotable to that site; if it flips, H45's recommendation is site-specific and must be re-derived per customer from their log.

## H46 · Appearance-weight sweep and night arm for ByteTrack + OSNet (`h46_reid_w_night`) — **done, partial 2026-09-27** (day/mot20 sweep bar met post hoc — not Holm-significant, H46b cross-validation pending; argmax w=4 matches; night arm not met, underpowered)
- **Hypothesis:** H24's w = 1 was untuned; the best w ∈ {0.25, 0.5, 1, 2, 4} (OSNet-ImageNet) lifts batch_v8 day
  ΔAssA to ≥ +0.02 with CI > 0, with no MOT20-02 decrease, and the argmax w matches on both sets; on batch_v8
  **night** sequences at that w, appearance still helps (ΔAssA > 0, CI excl. 0) but by less than day — the 73 §6
  night arm H24 did not run.
- **Arms:** w ∈ {0.25, 0.5, 1, 2, 4}, OSNet-ImageNet, vs the w = 0 (IoU-only) control; night: day-selected best w
  vs w = 0.
- **Seeds:** the same 5 h14b checkpoints; H24's cached day/MOT20-02 detections and embeddings reused unmodified,
  new caches for night.
- **Metric:** TrackEval AssA α-mean, per-sequence mean, two-way bootstrap (as H24); IDSW secondary.
- **Stopping:** fixed, ≤ 75 min. **Cost:** GPU light, night detections/embeddings only, tracker on CPU.
- **Decision:** report ΔAssA/ΔIDSW per w on both sets, the best w, and the night verdict; no default change here.

## H46b · Extend the sweep, cross-validate w*, full night arm (`h46_reid_w_night_b`) — **done 2026-09-27** (ceiling found, priced in ID switches; cross-val. bar met both directions; night positive, CI misses 0 by a hair)
- **Motivation:** H46 found ΔAssA still rising at w = 4, no ceiling; its night arm was 2 sequences
  × 1 checkpoint (CI spans 0) — underpowered, not a verdict.
- **Hypothesis:** (a) a ceiling exists at or below w = 32 (checked against w ∈ {8,16,32} and a true
  appearance-only arm, gate kept); (b) the w* chosen on one set (argmax dAssA) gives dAssA >= +0.02
  on the *other*, held-out set, in both directions; (c) the full 5-checkpoint night arm at the
  batch_v8-cross-validated w* gives dAssA > 0 with CI excluding 0.
- **Arms:** w in {8, 16, 32}, an app_only=True arm (cost = appearance alone, IoU >= 0.2 gate
  unchanged — new `survsim/baselines/bytetrack.py` flag), vs the w = 0 control; night arm at 5
  checkpoints (H46 had 1).
  Reports dAssA, dDetA, dHOTA, dIDSW per arm — a rise in AssA with rising IDSW or falling DetA is
  a trade, not a win.
- **Seeds:** the same 5 h14b checkpoints; H24/H46 caches reused for day/MOT20-02, fresh
  detections/embeddings for the 4 night checkpoints H46 did not cache.
- **Metric:** TrackEval AssA alpha-mean, DetA, HOTA, IDSW; two-way bootstrap.
- **Stopping:** fixed, <= 75 min. **Cost:** GPU light (night det/embed for 4 checkpoints only).
- **Decision:** ceiling w (if any), both cross-validated held-out numbers, AssA/IDSW/DetA trade
  flag, 5-checkpoint night verdict. Details: `32` §H46b.
- **Result (2026-09-27):** ceiling found — day argmax w=16 (+0.0613), MOT20-02 argmax w=8
  (+0.0486) — but IDSW rises with w throughout on MOT20-02 (+15.8/+33.4/+69.2 at w=8/16/32) and the
  `app_only` arm is the sharpest trade (day ΔDetA −0.0109, ΔIDSW +13.4 day/+162.0 mot20). Cross-
  validation bar (+0.02) met both directions (w*(day)→mot20 held-out +0.0479; w*(mot20)→day
  held-out +0.0570), but the mot20-chosen w=8 is the safer pick under an IDSW budget. Full night
  arm (6 seqs × 5 ckpt, w=16): ΔAssA +0.0470 [−0.0046,+0.1337] — positive, reverses H46's negative
  point estimate, but CI still touches 0. No w=1 default change made. **Reference-tracker
  recommendation:** ByteTrack + OSNet-ImageNet appearance at w ≈ 8 (cross-validated; +0.05 AssA
  held-out) with the IDSW cost stated; never appearance-only.

## H47 · Evasion techniques vs zero-shot person recall (`h47_evasion`) — **done, not met** (`6d7f5f1`; AUDIT_H47)
- **Status (2026-09-27): registered in 32 §H47.** 6 renderable techniques (dark_lowcontrast, hivis, hood_up, slow_deliberate, crowd_cover, wall_hugging) vs a matched control, 3 seeds × 2 cameras, 30 s, mask GT; met iff ≥ 3 of 6 have ΔR(YOLO26n) ≤ −0.10 with Holm-adjusted one-sided bootstrap p < 0.05. **Cost:** editor ~2 h, CPU scoring.
- **Result (2026-09-27): NOT MET, 1/6** (`6d7f5f1`; 32 §H47 results; AUDIT_H47) — crowd_cover ΔR(YOLO26n) −0.201 [−0.254, −0.154] (clip-cluster CI over 4 seed×cam clips; the frame-level [−0.210, −0.192] / Holm p 0.003 is too narrow — 4 clips cannot give p < 1/16); wall_hugging −0.054 [−0.074, −0.033], under the bar, and −43 % ≥ 20 px person-frames (3,262 vs 5,736; an earlier "halves exposure" overstated it); dark / hi-vis / hood *colour proxy* ≈ 0; slow +0.036. Seed 3 dropped for 4 techniques (disk cap). Umbrella, carried object, crouch/crawl, face-away: untested (→ H55).

## H53 · Late sensor fusion on the line-cross rule: gate log + RF tag + PIDS (`h53_sensor_fusion`) — **registered 2026-09-27 in 32**
- **Motivation:** H40b arm C leaves 0.488 twin FA/cam-h (patrol 0.389 + maintenance 0.099) that no role-blind video rule removes. AUDIT_78 retired "the fix is context and a second sensor" as unsupported. This tests it.
- **Hypothesis:** late fusion of C with a gate access log, a registered RF tag and PIDS fence vibration (drop iff (badge or tag) and no PIDS) removes >= 90 % of twin FA while recall@10 stays >= 0.782.
- **Arms:** C, C+a, C+b, C+c, C+abc; adversary arms tailgate and stolen_tag on recall worlds. All sensor parameters simulated and declared (32 §H53).
- **Seeds:** 53. **Stopping:** fixed. **Cost:** CPU minutes (reuses H40b caches).
- **Decision:** whether "context and a second sensor" can be reinstated with a SurvSim number, and what each sensor's failure mode costs.
- **Status (2026-09-27): done, not met on recall** (`0c492ba`; 32 §H53 results). C+abc twin FA **0.0047 [0.0023, 0.0075]** FA/cam-h (99.0 % [98.5, 99.5] removed; twin leg met, boot upper 0.0075 ≤ 0.0488); recall@10 **0.758 [0.710, 0.805]** < 0.782 (−0.023, 7 detections; H49's ≤ 0.02 also missed). Single gates: badge 98.0 % / recall 0.745, RF 95.4 % / 0.621, PIDS 99.1 % / 0.681. Tailgate recall ~0 on badge and combined; stolen tag 0 on RF, 0.701 combined. All sensors simulated (declared) and matched on true tracks/positions, not estimated ones (AUDIT_H53). Reinstates "context and a second sensor" only in 78's qualified form. Follow-up H54.

## H54 · Tailgate on the fence gate + estimated-position matching (`h54_fusion_realistic`) — follow-up to H53, not yet registered
- **Motivation:** H53 injected the tailgate as a sensor-stream edit (catalogue `tailgate` is a door behaviour, not wired to the fence gate) and matched alarms to sensors on true tracks. Both flatter or hide the real failure.
- **Hypothesis:** with (i) the `tailgate` behaviour connected to the fence gate so an intruder physically follows a badged twin through it, and (ii) sensor association by the alarm's *estimated* position (noisy arm-C track), C+abc still removes ≥ 90 % of twin FA; a gate-camera rule (two bodies per badge) recovers tailgate recall ≥ 0.5.
- **Arms:** C, C+abc (true matching, = H53), C+abc (estimated matching), C+abc+gate-camera; base / tailgate / stolen_tag recall worlds.
- **Decision:** whether H53's 99 % survives realistic association, and whether the tailgate hole can be closed with video. Bar on recall: loss ≤ 0.02 vs C (not zero — fusion can only remove alarms). **Cost:** CPU; needs a behaviour change in `survsim/` (not a doc task).
- **Status (2026-09-27): registered in 32 §H54** as `h54_tailgate_fusion` — generated `fence_tailgate` + `staff_escort` twin, estimated-position matching (true kept as control), gate-section people counter as arm C+abcg. Bar: est. C+abc removal ≥ 90 %, recall loss ≤ 0.03, tailgater recall ≥ 0.6 only with the gate sensor.
- **Result (2026-09-27): MET** (32 §H54 results). Est. matching C+abc removes 99.1 % [98.6, 99.5] of twin FA (true 99.1 %: estimated association costs ~nothing under H40b's 0.3 m noise model), recall loss 0.010; generated tailgater recall 0.056 under C+abc, 0.685 [0.589, 0.778] with a gate people counter (C+abcg, twin removal 96.3 %).
- **Audit (AUDIT_H54):** all numbers recompute (true matching leaves 18 alarms, est 19). The 99.1 % is an upper bound under a benign noise model (no ID switches, 0.3 m jitter); the ≈ 90 % prediction was wrong in the optimistic direction. Follow-up **H59**.

## H55 · Evasion at night + prop/pose techniques, cluster-level power (`h55_evasion_night`) — follow-up to H47, not yet registered
- **Motivation:** H47 tested six renderable techniques by day only; umbrella, carried object, crouch/crawl and face-away were untested (no CC0 asset/clip), the hood was a colour proxy, and with 4 clips per technique no clip-level test can reach p < 0.05.
- **Hypothesis:** at night (IR profile) dark clothing costs ≥ 0.10 zero-shot recall where by day it cost 0; umbrella / carried object / crawl each cost ≥ 0.10 by day.
- **Arms:** control, dark_lowcontrast (night), umbrella, carried_object, crouch_crawl, face_away, real hood geometry — each once a licensed (CC0/CC-BY) asset or clip exists (record in `~/data/assets/index.json`).
- **Seeds:** ≥ 5 per arm × 2 cams (≥ 10 clips, so a clip-level sign-flip test can reach p < 0.05); CI = paired clip-cluster bootstrap as the **primary**, frame-level secondary; also a clip-cluster re-score of H47 from its `det_cache/` (done in AUDIT_H47, 6 s CPU).
- **Stopping:** fixed. **Cost:** editor ~5 min/set; disk ~0.9 GB/set before PNG cleanup — check `df` first.
- **Decision:** which evasions enter the required hard-case set; whether night needs its own detector gate.

## H56 · PTZ slew-to-alarm acquisition and second-alarm contention (`h56_ptz_slew`) — **done, not met (2026-09-27; `0f05f04`, AUDIT_83_H56)**
- **Motivation:** 83 (PTZ auto-track and hand-off): "the fixed camera detects, the PTZ verifies" assumes the PTZ lands on the target; H39 says a datasheet-focal calibration puts the world estimate ~1 m off near and ~3 m off far, and the PTZ is blind while slewing.
- **Hypothesis:** with H39 datasheet-focal error, a PTZ slewed to the fixed-camera estimate acquires the target (usably_visible) within 3 s at ≥ 0.9 for targets ≤ 20 m and ≤ 0.6 beyond 30 m; at A1's 120 alarms/h a second alarm is missed ≥ 30 % of the time with one PTZ.
- **Arms:** exact vs H39 calibration × 1 vs 2 PTZs; 10 seeds; seed-cluster bootstrap. CPU, mock geometry.
- **Decision:** whether the verify loop needs closed-loop auto-tracking / wider verify framing, and PTZ count per 40 cameras.
- **Result:** H39 1 PTZ acquire@3s 0.901 [0.872, 0.936] ≤ 20 m (point estimate only), 0.727 [0.706, 0.747] > 30 m (bar ≤ 0.6 — failed); exact 0.967 / 0.958 / 0.978; missed second alarm 0.369 [0.325, 0.406] (1 PTZ) vs 0.057 (2). All PTZ timings assumed; far-field cause untested. Answer to the decision: ≥ 2 PTZs per 40 cameras; framing/closed loop → H57.

## H57 · PTZ re-detect-before-trust and distance-widened framing (`h57_ptz_framing`) — backlog
- **Motivation:** H56's far leg (0.727 > 30 m vs 0.978 exact) is attributed — untested — to ~3 m range error against a fixed 6 m frame (at 30 m a 6 m frame is ~11° hfov, below 83 §3.1's ~22° budget). An open-loop PTZ also "acquires" whoever is in frame.
- **Hypothesis:** framing width w(d) = max(6 m, k·σ(d)) with k ≈ 4, plus one PTZ-side detection and re-centre before the verify frame is trusted, lifts H39 > 30 m acquire@3s to ≥ 0.9 at ≥ 60 px person height, and the re-detect step keeps wrong-target acquisitions (actor-aware uid ≠ alarm uid) ≤ 2 % in crowds of ≥ 5 people within 10 m.
- **Arms:** fixed 6 m vs σ(d)-widened framing × open-loop vs re-detect (assumed 0.2 s detector latency, recall by pixel height from H3) × 1/2 PTZs; H56 site, 10 seeds; add bystanders for the wrong-target metric. CPU, mock.
- **Decision:** the verify-framing rule and whether closed-loop re-detection is mandatory before an operator sees the frame.

## H58 · Occlusion on the PTZ path (`h58_ptz_occlusion`) — backlog
- **Motivation:** H56 is free space: no buildings, vehicles or fences between PTZ and target, so acquisition is an upper bound.
- **Hypothesis:** with the fenced-sim occluders (H40b worlds) and a 10 m pole, acquire@3s drops by ≥ 10 points for the 1-PTZ arm, and a second PTZ on a different bearing recovers more of it than it did in H56 (where 2 PTZs gave no acquisition gain).
- **Arms:** H56 arms × {free space, fenced-sim occluders} using mask-derived visibility (principle 1), 10 seeds.
- **Decision:** PTZ siting — whether pole placement for line-of-sight diversity matters more than count.

## H59 · Fusion under ID switches and track breaks (`h59_fusion_idsw`) — follow-up to H54, backlog
- **Motivation:** H54's estimated matching cost nothing because H40b's noise model never swaps identities between people (0.3 m jitter, fragmentation, ghosts). A swap is exactly what hands a twin's badge or tag to an intruder beside it; 99.1 % is an upper bound.
- **Hypothesis:** with a noise model whose ID-switch and track-break rates are calibrated to H24's measured counts (ByteTrack+OSNet IDSW 87.0 per MOT20-02 run, 71.6 per batch_v8 sequence, scaled per track-second), est-matched C+abc still removes ≥ 90 % of twin FA and recall loss vs C stays ≤ 0.03; tailgater recall under C+abcg stays ≥ 0.6.
- **Arms:** H54 arms × {H40b noise, H24-calibrated IDSW + breaks, 2× that}; swaps preferentially between people < 2 m apart (the staff pair, the tailgater and its leader).
- **Decision:** whether fusion survives realistic association, or needs track-level (not alarm-level) fusion. **Cost:** CPU; noise-model change in `survsim/experiments` (not a doc task).
- **Pre-registered 2026-09-27 (32 §H59, `h59_idsw_fusion`):** hypothesis tightened to a *failure* prediction — calibrated IDSW (ByteTrack batch_v8: 83.4 IDSW per 12-sequence set / 1,904.6 GT track-s = 157.6 per track-hour; the "71.6 per sequence" above is OSNet's 12-sequence total) drops C+abc twin removal to ≤ 97 %, 3× to ≤ 90 %, recall loss ≥ 0.03, tailgater under C+abcg < 0.6. Arms benign / calibrated / 3×, 10 noise seeds.
- **Status (2026-09-27): done, not met** (32 §H59 results, 7,406 s). Calibrated and 3× stress (157.6 / 472.7
  IDSW/track-h) C+abc twin-FA removal both **99.1 % [98.7, 99.5]**, unchanged from H54's benign-noise ceiling
  (not ≤ 97 % / ≤ 90 %); calibrated recall loss vs C **+0.002 [+0.000, +0.003]** (not ≥ 0.03); calibrated
  tailgater recall under C+abcg **0.100 [0.071, 0.131]** (< 0.6, met, but only because base recall itself
  collapses 0.769→0.100 from actor-aware ID mismatch, not a fusion-specific tailgater failure). Only 1 of 4
  criteria met. Fusion survives realistic association because its legs gate on estimated *position*, not
  *label*; the identity-switch cost instead lands on actor-aware recall. Most identity-sensitive leg: C+b (RF).
  Deployment caveat carried to 32 §H33c: a per-visitor alarm cap keys on label, unlike these fusion legs, and
  was not itself tested here.

## H60 · Alarm-card generator with a sim-only GT guard (`h60_alarm_card`) — proposed by AUDIT_86; **slices 1–2 done** (32 §H60, AUDIT_H60, 32 §H60 slice 2: per-site salt, head.json fail-closed verify,
JCS-style canonical form, H22 score/θ/rank/verdict per alarm carded, config/model/clip hashes). **Open:** H33 per-alarm output, H22 alarms on a real run dir (camera/clip), signed head, rule trace
- **Motivation:** `86` §7 proposes an alarm card / evidence pack / WORM log schema, and AUDIT_86 found that SurvSim emits only part of it today: `Alarm` carries `t, label, camera, uid`, with camera set only by pipeline alarms and uid only by GT rules; score, rank, rule trace and verdicts live only inside runners; no alarm id, clip hash or chain exists. A generator would turn a run into cards that `51`/`59`-style reviews and the H22 operator model can consume. Its main risk is leakage: the GT match (`hit|late|wrong_actor|false`) is a simulator-only field, and a card that carried it on a real site would be a fabricated label presented as evidence.
- **Scope (when implemented; code in `survsim/`, not a doc task):** one card per alarm with `alarm_id` (deterministic from run seed + index), sim time, camera, uid, zone (world.parquet join), MOT box + `visible_frac`, `camera_status` at t, rule id + threshold, and score / θ / rank from the H22/H33 runner outputs; a pack with SHA-256 of the frames or clip, config hash, commit and `licences.json`; a log with `h_i = SHA-256(h_{i−1} ‖ entry_i)`; an i-LIDS verdict (`gt_match`) **only when `mode=sim`**.

Pre-registration (template `49` §12):

```
id:            h60_alarm_card
commit:        <hash of this entry before any code>
hypothesis:    a card generator built from existing GT and runner outputs can fill
               every [fillable]/[join] field of 86 §7 for H12 worlds and H22 A1
               alarms, and in mode=real never emits gt_match, event_id or any
               value read from gt/events.jsonl or gt/identities.parquet
primary metric: (a) leak count: cards (mode=real) containing any GT-derived key or
               value, over all alarms of the H22 A1 arm, 10 seeds — must be 0;
               (b) field fill rate in mode=sim over the 86 §7 fields tagged
               fillable or join
arms:          mode=sim (control: full card incl. gt_match) vs mode=real
held fixed:    H12 worlds, A1 rule and θ 0.95, H22 operator seeds, commit, config
seeds:         10 operator seeds (same as H22); generator itself deterministic
sample size:   all A1 alarms (~120/h × 80.6 wall-h per seed per H22); a leak
               test needs no power calculation — one leak fails it
analysis:      (a) exact count; (b) fill rate per field with a Wilson 95 % CI;
               chain check: recompute every h_i and require identical heads
               across two runs of the same seed (determinism, CLAUDE.md §6)
success:       leak count 0 in mode=real; chain heads identical across reruns;
               tampering any one entry breaks verification at that entry;
               fill rate ≥ 0.99 for each [fillable] field
stopping rule: fixed; single run per seed
secondary:     card size in bytes; per-alarm i-LIDS delay agrees with
               eval.alarms.score latencies (same multiset); rank on card equals
               the H22 simulated queue rank
confounds:     GT leaking indirectly through a runner output (e.g. an H22 event
               index, or a uid that is a GT identity rather than a tracker id) —
               mode=real must take uids from a tracker, and the test inspects
               values as well as keys
abandon if:    uid, zone or score cannot be filled without reading GT in
               mode=real (then the generator is sim-only by construction and the
               "real" mode is dropped rather than faked)
```

- **Test to write first:** `tests/test_alarm_card_real_mode.py` — build cards from a tiny mock run with `mode=real`; assert no key in {`gt_match`, `event_id`, `hard_negative`, `actors`} at any depth, no value equal to a GT event id, and that passing `mode=real` with a GT path raises. A second test flips one log entry and expects verification to fail at that index.
- **Decision:** whether SurvSim can claim "produces sim alarm cards and a verifiable log" (never "evidence packs for court"; `86` Q4, Q10).

## H33b · Conformal θ with B fixed in advance (`h33b_conformal_fixed_B`) — **done** (32 §H33b results; supported at α 2.915/2.0, partial at 1.0), proposed by AUDIT_88

* **Status (AUDIT_H33B):** done. B = 123.5 is not a valid a-priori bound (the per-visitor cap is not enforced; up to 21 episodes per visitor) — guarantee exact for min(L, B) only. **H45b** (32 §H45b, done): the certified θ 0.963436 realises 0.617 ranked @5 min, 1 operator, −0.004 [−0.017, +0.010] vs θ 0.962851 — ship rule unchanged. Follow-up: enforce one alarm per visitor per world (or a generator-guaranteed episode cap) to make B a true bound.

* **Why:** H33's CRC used B = max calibration loss (data-derived), so its guarantee is approximate.
* **Hypothesis:** with B = 123.5 FA/cam-h fixed from the H12 generator (Poisson(180) 1 − 1e-6 arrivals
  / 2.0 cam-h, ≤ 1 alarm per visitor), θ is at least as conservative as H33's, held-out FA ≤ α in 10/10
  splits, and recall cost vs empirical B ≤ 0.02. `choose_crc(mode="real")` requires B; `mode="empirical"`
  keeps H33/H42/H45 reproducible.

## H33c · Per-visitor alarm cap makes B a real bound (`h33c_capped`) — **done, partial** (32 §H33c results), from AUDIT_H33B

* **Status:** done. Cap 1 makes B = 123.5 a valid bound (max 202 visitors/world ≤ 247; 0 clipped; 0/10 exceed); recall +0.004 at the CRC θ; but the equal-θ FA cut is 3.4 %, not ≥ 20 % → partial. H45c: capped θ 0.961780 realises 0.618 ranked @5 min, 1 op, +0.001 [−0.014, +0.016] vs H45b — ship rule unchanged; deliver conformal with the cap (exact certificate).

* **Why:** H33b's B = 123.5 rests on ≤ 1 alarm per visitor, which A1 does not enforce (up to 21 episodes/visitor).
* **Hypothesis:** with `max_alarms_per_uid_per_world = 1` B is a valid a-priori bound; at α 2.915 the cap cuts
  held-out clean FA ≥ 20 % at equal θ, costs ≤ 0.02 recall at the CRC θ, exceeds α in 0/10 splits and clips no
  world. Arms uncapped / capped1 / capped2 (B 247). H45c reruns the operator sim at the capped certified θ.

## H62 · Position/time-keyed alarm scoring as the default when identities come from a tracker (`h62_label_agnostic_score`) — pre-registration, from AUDIT_TAILGATER_RECONCILIATION

* **Motivation:** H59 (32 §H59, AUDIT_H59) found that under H24-calibrated ID-switch noise, `alarms.score`'s
  actor-aware matching (default since round 2, docs/13) collapses the tailgater/base recall from 0.769 to
  0.100 — not because fusion breaks (the position-gated legs still fire the same way), but because a label
  swap mid-track reassigns an already-caught detection to the wrong `uid`, and actor-aware scoring counts that
  as a miss. AUDIT_TAILGATER_RECONCILIATION re-verified this from `h59_idsw_fusion`'s cached
  `fused_worlds.jsonl` and additionally re-scored the same alarms with `AlarmScore.window_only_recall` (label +
  timing, no `uid` check — a label-agnostic, position/time proxy): calibrated-arm tailgater recall@10 goes
  from 0.108 (`C`) / 0.100 (`C+abcg`) actor-aware to 0.828 / 0.739 window-only. The gap is almost entirely a
  scoring artefact of crediting alarms to a `uid` a real tracker would have already swapped.
* **Hypothesis:** for any deployment whose alarm `uid` comes from a tracker/ReID pipeline (not GT), scoring by
  position/time (window-only, or an uid-tolerant match within a small spatial radius) rather than by label
  identity recovers ≥ 90 % of the label-agnostic recall lost to actor-aware scoring under H59's calibrated
  IDSW rate, while an actor-aware score is reserved for the identity/re-identification-specific metrics (e.g.
  "which specific person was this alarm about") it is designed to measure.
* **Scope (pre-registration template `49` §12):**
```
id:            h62_label_agnostic_score
commit:        <hash of this entry before any code>
hypothesis:    a position/time-keyed (window-only or uid-tolerant-within-r) alarm score,
               applied to h59_idsw_fusion's calibrated arm, recovers >= 90% of the
               label-agnostic (window-only) tailgater recall relative to the current
               actor-aware default, while a same-uid check (identity-specific metric,
               reported separately) still distinguishes "alarm on the right person" from
               "alarm on a bystander" for cases with no tracker-driven label churn
primary metric: tailgater recall@10 (calibrated arm, C+abcg) under: (a) current
               actor-aware default, (b) window-only, (c) uid-tolerant-within-r_m
confounds:     window-only alone reopens the pre-round-2 "two events, one window"
               overcount (docs/13 principle 4, docs/research/58 §4) — must report
               window_only_recall alongside repeat/false-positive counts, not recall alone
abandon if:    reverting to window-only regresses bystander-hit count (an alarm on the
               wrong, non-swapped person) back to pre-round-2 levels
```
* **Decision:** whether a tracker-fed deployment should default `alarms.score` to `actor_aware=False` (or a
  new uid-tolerant mode) rather than the current `actor_aware=True` default, and under what identity-churn
  rate that default should switch.

* **Status (32 §H62 results, 2026-09-27): partially met.** A `position_radius_m` mode was added to
  `alarms.score`. On H59's calibrated-arm tailgate worlds, C+abcg: position_time(2 m) recall 0.715 (>= the
  0.6 bar; actor-aware 0.100, window-only 0.739) — but its false-credit (bystander-within-radius) rate is
  31.3 % at 2 m (14.8 % even at 1 m), far above the pre-registered 5 % bar, because tailgating puts the actor
  and a bystander within a few metres by construction. Benign-arm match to actor-aware within 0.02: met
  (0.711 vs 0.701). **Decision: keep `actor_aware=True` as the default (principle 4 unchanged); do not adopt
  `position_radius_m` as a replacement scorer** — it recovers recall but cannot reliably tell the actor from
  a bystander at the radii that matter for this scenario. Wording proposed for principle 4 (not applied):
  32 §H62.
* **Follow-up (code, not implemented, AUDIT_H62):** H62's headline numbers use a dynamic per-alarm actor
  reference computed in the eval script, not `alarms.score`'s own `TruthEvent.actor_pos` (a static snapshot
  at `t_start`, which almost never hits — 0.2–2.8 % — once an actor has walked away from that snapshot
  within a multi-second tolerance window). If `position_radius_m` is to be usable on real, moving actors
  without a caller pre-computing a per-alarm reference itself, `alarms.score` should accept a time-varying
  `actor_pos` (a callable or interpolated track, keyed by alarm time) rather than one static point per event.
  Scope for a future round, not this one.

## H63–H68 · Infiltration-playbook hypotheses (from `100` §4) — backlog, not registered
Template `49` §12; all CPU/mock unless stated; none implemented.
```
id:            h63_role_zone_mismatch
hypothesis:    a role x zone x time mismatch score joined to the badge log flags >= 0.5 of
               role_disguise intruders (hi_vis_worker, cleaner, courier, security_uniform)
               at twin FA <= H53 C+abc (0.0047 FA/cam-h upper 0.0075)
primary:       disguised-intruder recall@10; confounds: roster realism, badge simulated
abandon if:    mismatch needs GT role labels to work
```
**H63 run 2026-09-28 (32 §H63, as `h63_uniform_mismatch`, uniform=guard variant): not met on the absolute bar.** Role suppression 0.027; badge+RF mismatch 0.745 [0.694, 0.794] = 96 % of C's 0.775 ceiling at twin FA 0.018/cam-h; +route prior 0.198 (5 m corridor covers small zones). Follow-ups: other `role_disguise` roles (worker/cleaner vs work-order), off-shift roster, H59 ID switches.
```
id:            h63b_roster_realism_and_role_error
hypothesis:    H63's caveats, tested directly: (i) a rostered-hours model where not every
               guard/worker twin is on shift all world (so the badge/RF time leg can actually
               fire and drop a corroborated twin instead of degenerately always matching);
               (ii) a sweep of the role-classifier assumption (p_guard_given_uniform 0.80-0.99,
               p_guard_given_other 0.0-0.10) to see how much of (b)'s 0.745 recall depends on
               the assumed 0.95/0.02 pair rather than the corroboration logic
primary:       (b) recall@10 and twin FA/cam-h as a function of roster on-shift fraction and
               (p_guard_given_uniform, p_guard_given_other); confounds: still no GT role label,
               still H53's simulated sensor values
abandon if:    off-shift roster gating requires a schedule model H54's worlds do not carry
```
**H63b not registered** — backlog only until a rostered-hours schedule exists on H54's worlds.
id:            h64_patrol_timing
hypothesis:    ptz_timing intruders enter while the PTZ is away at a rate above chance that a
               detector over PTZ state + entry time flags within <= 3 entries; randomised tours
               cut the exploitation rate by >= 50 %
primary:       P(entry | PTZ away) vs tour duty cycle; confounds: fixed-camera overlap
```
```
id:            h65_service_entry_coverage
hypothesis:    covering service entrances (rig blind-spot fix) raises unmonitored-approach
               intruder recall by >= 0.3 at <= 0.05 FA/cam-h extra from un-suppressed staff routes
primary:       recall on wrong_zone_entry via service door; FA/cam-h delta (maintenance, staff_escort twins)
```
```
id:            h66_decoy_flooding
hypothesis:    a decoy incident (fight/person_down/throw_object) concurrent with a fence intrusion
               pushes the intrusion's operator-review time past the i-LIDS tolerance in >= 50 % of
               runs under the H45 operator model; a dedicated perimeter queue restores it
primary:       fraction of intrusions reviewed within tolerance; builds on H56 contention
```
```
id:            h67_vehicle_concealment
hypothesis:    camera-only recall on a person concealed in a vehicle is 0 by construction; a
               vehicle-gate dwell/procedure rule flags >= 0.5 of vehicles that skip the search stop
primary:       vehicle-level recall; declare: no person-in-vehicle rendering
```
```
id:            h68_drone_overflight
hypothesis:    fixed perimeter cameras detect drone_overflight with recall < 0.3 beyond 30 m
               altitude at 720p; bounds the claim "cameras catch drones"
primary:       per-pass recall vs altitude/size; needs a CC0 drone asset (licence check first)
```
