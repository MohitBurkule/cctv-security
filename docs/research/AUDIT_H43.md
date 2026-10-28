# AUDIT_H43 · INT8 accuracy recovery: PTQ calibration and QAT (32 §H43)

Audited 2026-09-27 against pre-registration and results in `32_EXPERIMENTS_LOG.md` §H43
(commit `8edbebf`), the PTQ-calibration arm run. Method as AUDIT_H38: every number recomputed
in Python from `out/experiments/h43_qat/ckpts/{mix_300_s0,mix_300_s1,mix_300_s2,dose300_s0,
dose300_s1}.json`; method claims checked against `survsim/experiments/quant_export.py`.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| per-checkpoint AP75 recovery 0.510 / 0.314 / 0.434 / 0.118 / 0.679 | (0.0263−0.0129)/0.0263=0.510; (0.0245−0.0168)/0.0245=0.314; (0.0399−0.0226)/0.0399=0.434; (0.0169−0.0149)/0.0169=0.118; (0.0156−0.0050)/0.0156=0.679 | match |
| corpus recovery (mean-loss based, pre-registered formula) 0.415, all 5 | mean A1 loss 0.0246, mean P1 loss 0.0144, (0.0246−0.0144)/0.0246=0.4146 | match — **note:** this is not the mean of the five per-checkpoint recoveries above (mean of those is 0.411); the pre-registered formula pools losses first, and the doc already says so |
| h14b-only recovery 0.424 | mean A1 (3 h14b) 0.03023, mean P1 0.017433, recovery 0.4227 | match |
| 0/5 checkpoints regressed vs MinMax | P1 AP75 loss < A1 AP75 loss on all 5 rows | match |
| decision: PTQ leg not met (both cuts < 0.50 bar) | 0.415 and 0.424 both < 0.50 | match |
| A1 AP75 loss 0.0246 [0.0179, 0.0326]; P1 0.0144 [0.0093, 0.0195], 95 % percentile bootstrap, n = 5 | recomputed via `_bootstrap` (`quant_export.py:46`), 10k resamples, matches to 4 d.p. | match |
| calibration method actually differs between arms | `_int8()` (`quant_export.py:411-432`) takes `calibrate_method=getattr(CalibrationMethod, method)` — MinMax/Percentile/Entropy are distinct `onnxruntime.quantization.CalibrationMethod` values, all with `per_channel=True`, same 100-frame calibration set (`calibration_frames.json`, 1 entry — reused from H38's `frames 61-429`, per pre-reg) | match — genuine calibration-method ablation, not a relabelling |
| Entropy (P2) numerically identical to MinMax (A1) on `mix_300_s0` | `int8_entropy.AP75 = 0.5110`, `int8_minmax.AP75 = 0.5110` (`ckpts/mix_300_s0.json`) | match |
| QAT (Q1) ran end-to-end only on `mix_300_s0`; other 4 have no `int8_qat`/`qat_fp32` entries | confirmed — `mix_300_s0.json` has both keys; `mix_300_s1/s2`, `dose300_s0/s1` have none (only fp32_torch/int8_minmax reused from H38, no fresh eval cached) | match |
| QAT single-checkpoint recovery ≈ 0.07, misses the 0.50 PTQ bar and the 0.80 QAT bar | (0.0263−0.0244)/0.0263 = 0.0722 | match |
| QAT recorded as a budget deviation (code path works), not a tooling failure, deferred to H43b | consistent with `mix_300_s0` having a complete 6-arm run (fp32_torch, int8_minmax, int8_percentile, int8_entropy, qat_fp32, int8_qat) while the other 4 checkpoints only have model/QAT exports and no fresh evals | match |
| n = 5 "95 % bootstrap" is a genuine interval, not degenerate min/max (contrast AUDIT_H38's n = 3 finding) | for n = 5, an all-same-value resample requires 5 identical draws from 5 values, p = (1/5)⁵ = 0.00032 = 0.032 % ≪ 2.5 %, so the 2.5th/97.5th percentiles are not forced to the sample min/max the way they were at n = 3 (p = 1/27 = 3.7 % > 2.5 %) | **confirmed distinct** — the "bootstrap" label is correctly used for n = 5 (unlike n = 3, where AUDIT_H38 required "range" instead); 32/FACTS/38/60 do not mislabel this |
| no INT8 latency/speed claim made (R46) | `32` §H43 results section carries no latency comparison between arms; `cpu_latency_ms_median` is present per-arm in the raw JSON but not used for any speed claim in the write-up | match — R46 respected |
| AP recovery 0.381; AP50 recovery 0.933 (not load-bearing, one negative loss) | AP: mean A1 AP loss vs mean P1 AP loss recomputed to the same ratio; AP50: one checkpoint (`dose300_s1`, per source data) has a negative P1 AP50 loss (P1 slightly *beats* FP32 on AP50), consistent with "not load-bearing" | match |

## 2. Downstream propagation checked

- **FACTS_VERIFIED.md** (row "H43"): all figures match §1 above; correctly states 0/5 regressions,
  n = 1 status for Entropy/QAT, and the deviation/H43b deferral. No edit needed.
- **38 §2.5 row 13:** correctly folds in H43 as "[V] measured … not TensorRT on a Jetson" and states
  the 0.415/0.42 recovery, the 0.50-bar miss, and "QAT not yet run to a full-corpus result (H43b)".
  No edit needed.
- **68 Q10 model answer:** the prompt's target sentence — "ship FP16; INT8 PTQ costs ~0.012 AP mostly
  AP75; better calibration recovers ~40 % of the AP75 loss, not enough; QAT untested at scale — H43b"
  — matches the recomputed numbers (H38's 0.0117 AP ≈ "~0.012"; H43's recovery 0.415/0.424 ≈ "~40 %";
  QAT n = 1 ≈ "untested at scale"). `68` Q10's existing answer (line 424, the Orin-NX-budget question)
  is a different question and is unaffected; no H43-specific model answer sentence existed in `68`
  before this audit, and none needed adding — the sentence tracked in this task lives in the audit
  report, not as a new insertion into `68`.
- **60 item 37, 65 v2 §4 gap #4, 77 weak-answer #3:** checked. Gap #4 and #3 are specifically about
  *Jetson latency*, which H43's no-Jetson branch never measured (context-only CPU latency, no speed
  claim, R46) — both remain accurate unedited. Item 37 said H43 was "backlog … not registered", which
  is now stale (it is registered and the PTQ leg ran) — **edited** to record the PTQ-not-met result
  and the QAT/H43b deferral, leaving TensorRT-on-a-real-Orin as the remaining backlog item.
- **66 (backlog):** row 15b described H43 as an unregistered TensorRT-or-QAT hypothesis, stale since
  the PTQ leg is done and QAT deferred — **edited** to `~~H43~~ … done, not met` (matching the
  `~~H38~~`/`~~H42~~` convention) and a new row 15c added for **H43b** (QAT, full 5-checkpoint corpus).

## 3. Corrections made (Edit only, no data recomputation changed)

1. `60_ONE_PAGE_CHEAT_SHEET.md` item 37: "H43 TensorRT INT8 on an Orin (or QAT) is backlog (66), not
   registered" → "H43 no-Jetson PTQ-calibration leg done, not met (Percentile AP75 recovery
   0.415/0.424 < 0.50 bar, AUDIT_H43); QAT leg deferred to H43b (66), TensorRT-on-a-real-Orin is
   still backlog".
2. `66_HYPOTHESIS_BACKLOG.md` row 15b: unregistered-hypothesis wording → `~~H43~~ … done, not met`
   summary (PTQ recovery, 0/5 regressions, QAT n = 1 deferral, AUDIT_H43 cite); added row 15c for
   H43b (QAT, full corpus, GPU time).

No numeric claim in `32`, `FACTS_VERIFIED.md`, `38`, or `68` needed correction — all recomputed
accurate (they scope the open gap to Jetson latency specifically, which is correct and unaffected
by H43's accuracy-only, no-Jetson result).

## Score: 9/10

The pre-registration and results section in `32` were already numerically exact and correctly
hedged (mean-loss-based recovery formula stated explicitly, n = 1 arms not scored as corpus results,
no latency claim, bootstrap vs range distinction correctly drawn for n = 5 vs H38's n = 3). The one
point off is process, not arithmetic: two downstream summaries (`60` item 37, `66` row 15b) had not
been updated after the PTQ leg landed and still described H43 as an unregistered, not-yet-run
hypothesis — the same class of staleness AUDIT_H38 and AUDIT_H42 caught in their own downstream rows.
