# AUDIT_H43BC · QAT INT8 recovery (H43b) and its root-cause fix (H43c) (32 §H43b/§H43c)

Audited 2026-09-27 against pre-registration and results in `32_EXPERIMENTS_LOG.md` §H43b/§H43c
(commits `d891d6d`, `86a40c1`). Method as AUDIT_H43: every number recomputed in Python from
`out/experiments/h43_qat/ckpts/{mix_300_s0,mix_300_s1,mix_300_s2,dose300_s0,dose300_s1}.json` (H43b)
and `out/experiments/h43c_learned_ranges/results.json` (H43c); method claims checked against
`survsim/experiments/quant_export.py` and `tests/test_experiments.py`.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| H43b per-checkpoint AP75 recovery (int8_qat vs int8_minmax loss) 0.072/0.433/0.451/0.450/0.442 | (0.0263−0.0244)/0.0263=0.0722; (0.0245−0.0139)/0.0245=0.4327; (0.0399−0.0219)/0.0399=0.4511; (0.0169−0.0093)/0.0169=0.4497; (0.0156−0.0087)/0.0156=0.4423 | match |
| H43b mean of those five per-checkpoint recoveries | (0.072+0.433+0.451+0.450+0.442)/5 = 0.370 | **differs from the doc's reported 0.366** by 0.004 — not an error: the doc uses the pre-registered pooled-loss formula (mean loss(A1)=0.0246, mean loss(Q1)=0.0156, recovery=1−0.0156/0.0246=0.366), not a mean of per-checkpoint ratios (0.370). Same formula distinction AUDIT_H43 already flagged for H43 itself; correctly applied here too, but the doc never states the two numbers differ — added a one-line note (32 §H43b) |
| H43b decision: not met, either bar (recovery 0.366/0.334 < 0.50 and 0.80; 3/5 exceed 0.005 AP-loss bar) | AP loss per checkpoint 0.0053/0.0013/0.0088/0.0053/0.0031 → 3 of 5 (mix_300_s0, mix_300_s2, dose300_s0) > 0.005 | match |
| H43b `qat_fp32` beats `fp32_torch` on every checkpoint | AP loss list [−0.0027,−0.0045,−0.0021,−0.0061,−0.0059], AP75 [−0.0037,−0.0088,−0.0116,−0.0091,−0.0082], AP50 all negative too — all 5×3 = 15 values negative (a gain) | match — confirmed true from the raw JSON, not just asserted |
| H43c per-checkpoint AP75 recovery (int8_qat_qdq vs int8_minmax) 0.266/0.322/0.561/0.615/0.429 | (0.0263−0.0193)/0.0263=0.2662; (0.0245−0.0166)/0.0245=0.3224; (0.0399−0.0175)/0.0399=0.5614; (0.0169−0.0065)/0.0169=0.6154; (0.0156−0.0089)/0.0156=0.4295 | match |
| H43c mean 0.439 | mean of the five above = 2.1949/5 = 0.4390; pooled-loss formula (1−0.0138/0.0246) = 0.4390 — **the two methods agree to 4 d.p. for H43c** (unlike H43b, where they differ by 0.004) | match, and worth noting the H43b/H43c discrepancy-vs-agreement contrast is itself informative (H43c's per-checkpoint losses are more proportionally similar to the pooled mean) |
| H43b AP loss: 3/5 checkpoints exceed 0.005 | 0.0053, 0.0013, 0.0088, 0.0053, 0.0031 → 0.0053 ≥ 0.005 (yes), 0.0088 (yes), 0.0053 (yes) = 3/5 | match |
| H43c AP loss: 4/5 under 0.005 | 0.0046, 0.0027, 0.0067, 0.0030, 0.0028 → only 0.0067 (mix_300_s2) exceeds; 4/5 under | match |
| "ranges carried" tested by comparing exported scale initialisers to observer values, 5/5 | `verify_learned_ranges_carried` (`quant_export.py:655-677`) loads the exported ONNX, reads the sample weight/activation `_scale` initializers, and asserts `abs(got - meta[...]) < 1e-6` against the values passed in as `TensorQuantOverrides`; `results.json["ranges_verified"]` is `true` for all 5 checkpoints and `"all_ranges_verified": true` | match — this is a real byte/float-level comparison against the values actually handed to `quantize_static`, not a re-derivation that could coincidentally agree |
| Conv-order weight-byte matching fix has a regression test | searched `tests/test_experiments.py` and the rest of `tests/` for any test invoking `_qdq_from_ranges`, `verify_learned_ranges_carried`, `_collect_qat_ranges`, or asserting Conv-node/module order — **none exists** | **gap, not a false claim** — the doc never claims a pytest regression test exists; it correctly says the check ran "on the trial checkpoint" (verified unique 64/64) and is re-verified live every time `h43c`'s per-checkpoint pipeline runs (which is real, but is not a standing, fast, CI-covered regression test guarding against the bug recurring if the export code changes). Flagged below, no doc edit needed since no doc overclaimed a pytest test — but a fixture-scale test is a good follow-up (out of this audit's scope: `survsim/` is off-limits here) |
| "QAT-FP32 beats baseline on every checkpoint" (H43b write-up) | see row above — confirmed true in both AP and AP75 (and AP50) | match |
| pre-registered bars: H43b primary recovery ≥ 0.80 AND AP loss ≤ 0.005 every checkpoint; secondary ≥ 0.50. H43c: same bars, vs int8_minmax | `h43_qat.yaml` config (referenced) and `h43c_learned_ranges.yaml`'s `thresholds: {qdq_recovery: 0.8, qdq_recovery_secondary: 0.5, qdq_ap_loss: 0.005}` in `results.json["config"]["thresholds"]` | match |
| H43b/H43c verdicts in `results.json` (`qdq_recovery_met`/`qdq_met`: false for H43c; H43b's analogous flags) | H43c `decision`: `qdq_recovery_met: false, qdq_recovery_secondary_only: false, qdq_every_ckpt_met: false, qdq_met: false`; H43b `ptq_met/qat_recovery_met/qat_every_ckpt_met/qat_met` all false | match |
| final attribution ("shortfall is the 150-iteration recipe, not the export") | as written pre-audit in `32` §H43c and `65 v2` §4 gap 4 and `FACTS_VERIFIED.md`'s H43c row, this was stated as a flat conclusion ("**QAT still does not beat Percentile PTQ, and now that the learned-range mechanism has been tried, the remaining gap is attributed to the QAT recipe, not the export path.**") — **imprecise: this is an inference from one data point (no longer-QAT arm was run), not something H43c measured.** No `qat_fp32`-at-more-iterations or `int8_qat_qdq`-at-more-iterations arm exists anywhere in the corpus | **fixed** in `32`, `FACTS_VERIFIED.md`, `65_v2`; hedged with "*inferred*... not itself measured" and pointed at new follow-up **H43d** (66), proposed with a full pre-registration block in the 49-style template |
| no latency claims (R46) | `32` §H43b/§H43c prose contains no INT8-vs-FP16/FP32 speed comparison; `cpu_latency_ms_median` appears only in raw JSON and in per-arm result tables, never as a claim. H43c's own text states "latency is not a claim" explicitly | match — R46 respected in both sections, both before and after this audit's edits |

## 2. Downstream propagation checked and fixed

- **`38` §2.5 row 13:** stated the same flat attribution ("QAT's shortfall here is the recipe (150
  iterations), not the export path") — **fixed**: hedged as inference, and the row now carries the
  single canonical edge sentence (below) instead of a bespoke paraphrase.
- **`68` Q10 follow-up 2:** correctly described H43b/H43c mechanics and numbers; its closing sentence
  was updated to the canonical edge sentence for consistency with `38`/`60`/`65`/`77`.
- **`60` item 37:** was stale — described only the H43 PTQ leg and "(66)" deferral to H43b, with no
  H43b/H43c outcome at all. **Fixed**: added the H43b/H43c done-not-met result and the canonical edge
  sentence.
- **`65_DRESS_REHEARSAL_V2.md` §0 item 8 / §4 gap 4:** §0 item 8 repeated the flat attribution — fixed
  the same way, with the H43d pointer. §4 gap 4 itself was already careful (scopes the open gap to
  Jetson latency specifically, correctly notes H43/H43b/H43c are all CPU-only accuracy legs) — no
  numeric or scope error found there; left as written per the task's "already stands" framing, only
  the cross-referenced §0 item 8 needed the fix.
- **`77_COLD_READ_REVIEW_V2.md` #3 (edge answer):** predated H43b/H43c and only covered H43's PTQ
  result. Added the calibration/QAT recovery numbers and the canonical edge sentence.
- **`FACTS_VERIFIED.md` H43c row:** carried the same flat attribution — fixed with the same hedge and
  H43d pointer.
- **The edge answer is now one sentence, placed identically (word-for-word or near-identical) in
  `38` §2.5 row 13, `68` Q10, `60` item 37, `65 v2` §0 item 8, and `77` #3:**
  > FP16 export is free; INT8 PTQ costs ~0.012 AP, mostly AP75; Percentile calibration recovers ~41 %
  > of the AP75 loss and QAT with a range-preserving export ~44 % — neither reaches the 50 % bar; ship
  > FP16, use INT8 only where AP75 (box tightness) doesn't drive the alarm; nothing measured on a
  > Jetson.

## 3. Gaps noted (not doc errors, flagged for future work)

- No pytest-level regression test exists for the Conv-node/module-order byte-matching fix
  (`_qdq_from_ranges` in `quant_export.py:589-652`) or for `verify_learned_ranges_carried`
  (`quant_export.py:655-677`). Both are exercised live by the `h43c` experiment runner, and their
  results are checked into `results.json`, but nothing in `tests/test_experiments.py` guards them on
  a small fixture independent of a full GPU/CPU experiment run. `survsim/` is out of scope for this
  audit's edits; recorded here as a follow-up.
- H43b's own reported pooled-loss recovery (0.366) and the mean of its five per-checkpoint ratios
  (0.370) differ by 0.004 without the doc calling that out (H43c's two methods happen to agree to 4
  d.p., which could read as if the formulas always agree) — a one-line clarifying note was added to
  `32` §H43b.

## Score: 8/10

Every number in both sections recomputed exactly from the raw JSON; the pre-registered bars and
verdicts match `results.json`'s own decision flags; "ranges carried" is a real byte/float comparison
against the values handed to the exporter, not a coincidental re-derivation; no latency claim exists
anywhere in either section (R46 respected). The two points off: (1) the final causal attribution in
five places (`32`, `FACTS_VERIFIED.md`, `38`, `65 v2`, and implicitly `60`/`68`/`77` before this audit)
was written as a settled conclusion rather than the single-data-point inference it actually is — now
hedged and given a named follow-up (H43d); (2) the edge-deployment answer had drifted into five
different paraphrases across `38`/`60`/`65`/`68`/`77`, none of which was numerically wrong but none of
which agreed on wording — now one sentence, placed identically in all five.
