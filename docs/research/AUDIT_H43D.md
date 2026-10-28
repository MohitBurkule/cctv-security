# AUDIT_H43D — H43d (does more QAT fine-tuning close the H43c gap?) recomputed

Scope: `32` §H43d, `FACTS_VERIFIED.md`'s H43d row, `66` H43d/H43e, and the downstream QAT-story
mentions in `38` §2.5 row 13, `68` Q10, `65_DRESS_REHEARSAL_V2.md` §0/§4, `77` #3, `91` (checked, no
QAT mentions there). No `survsim/`, `out/`, `03`, `58`, `71`, or other H-section edits made.

## 1. Numbers recomputed against `out/experiments/h43d_qat_more_iters/results.json`

| Claim | Recomputation | Verdict |
|---|---|---|
| Per-checkpoint AP75 recovery 0.331/0.531/0.782/0.077/−0.500 | `(int8_minmax loss − int8_qat_qdq loss) / int8_minmax loss` per checkpoint: (0.0263−0.0176)/0.0263=0.331; (0.0245−0.0115)/0.0245=0.531; (0.0399−0.0087)/0.0399=0.782; (0.0169−0.0156)/0.0169=0.077; (0.0156−0.0234)/0.0156=**−0.500** | match |
| AP loss (met ≤0.005 / miss): 0.0040/0.0032/0.0045 met; 0.0102/0.0108 miss | `decision.loss_vs_fp32.AP.int8_qat_qdq.loss` = [0.0040, 0.0032, 0.0045, 0.0102, 0.0108] exactly | match |
| `qat_fp32` AP ≥ `fp32_torch` AP on all 5 | qat_fp32 = [0.4989, 0.4963, 0.4982, 0.4978, 0.4955] vs fp32_torch = [0.4970, 0.4957, 0.4955, 0.4968, 0.4941] — every pair qat_fp32 > fp32_torch (deltas +0.0007..+0.0027) | match |
| Pooled AP75 recovery 0.374 vs H43c's 0.439 | `decision.recovery.AP75` = 0.374 (mean int8_minmax AP75 loss 0.0246, mean int8_qat_qdq AP75 loss 0.0154, 1−0.0154/0.0246=0.374); H43c's 0.439 confirmed unchanged in `32` §H43c | match |
| Hypothesis is stated as refuted, not "not met" | Pre-fix, `32` §H43d's decision line read "hypothesis not supported" — imprecise relative to `66`'s and `38`'s "refuted" wording for the same result | **fixed**: `32` now reads "hypothesis refuted — recovery fell, it did not rise" |

## 2. The −0.500 recovery on `dose300_s1`

Recovery is negative because, at 600 iterations, `int8_qat_qdq`'s own AP75 loss (0.0234) is *larger*
than plain MinMax PTQ's AP75 loss (0.0156) on this one checkpoint — the QAT+learned-range path costs
more accuracy than doing no QAT at all and just running static MinMax calibration. This is not
"the model got generically worse": `qat_fp32` (the fake-quant-stripped FP32 control) shows **zero**
degradation on `dose300_s1` (loss exactly 0.0000, matching the doc), so the 600-iteration fine-tune by
itself does not hurt the FP32 weights — the damage is specific to what INT8 quantisation does to those
fine-tuned weights, not overfitting visible in FP32. `mix_300_s2`'s `qat_fp32` loss is the largest
regression seen anywhere in the fake-quant-stripped control (−0.0158 AP75, i.e. the biggest *gain*),
and it also has the biggest INT8 recovery gain (0.782) — the opposite correlation from `dose300_s1` —
which is itself evidence that iteration count alone does not predict the INT8 outcome; whatever the
observers learn interacts with the checkpoint.

**Do the `dose300` checkpoints differ from the `h14b` ones in a way that matters?** Yes, and it is
recorded in `results.json["config"]["checkpoints"]`: `mix_300_s0/s1/s2` are loaded from
`h14b_dose_fixedlabels` (H38's original 3 checkpoints, mixed-data recipe), while `dose300_s0/s1` are
loaded from `h51_equal_steps` (the H51 equal-steps dosing recipe on batch_v8, a different training
run entirely — different data mix, different step schedule). The recovery split is exactly along this
line: all 3 `h14b`/mixed-data checkpoints improved with more QAT iterations (0.266→0.331,
0.322→0.531, 0.561→0.782); both `H51`/equal-steps checkpoints got worse (0.615→0.077, 0.429→−0.500).
This is the checkpoint-recipe dependence `32` §H43d and `66`'s H43d entry already state; this audit
confirms the config keys back the claim rather than it being an unverified pattern-match on two
numbers.

## 3. 600-iteration LR and calibration-frame overfit check

`results.json["config"]["qat"]` records `iters: 600, lr: 1.19e-05, weight_decay: 0.0005, batch: 8,
imgsz: 640` — the same H51-auto-LR/10 recipe as H43c's 150-iteration run, scaled to more steps, not a
different (higher) LR that could explain instability by itself. Fine-tuning happens on the QAT
observers/fake-quant fine-tune data, evaluation is on MOT20-02 (a held-out eval set, never used for
QAT fine-tuning or calibration) — so a rise in `qat_fp32` AP on the *training* distribution while
INT8 AP75 falls on MOT20-02 would be classic overfit-to-calibration-frames symptomatology. But the
`qat_fp32` (FP32, fake-quant-stripped) MOT20-02 numbers do **not** show degradation on any of the 5
checkpoints (all ≥ baseline) — if 600 iterations were overfitting the calibration/fine-tune frames
badly enough to explain a 0.500 negative *INT8* recovery, the FP32 held-out numbers would be expected
to degrade too, and they do not. The regression is therefore INT8-quantisation-specific (how the
observers' 600-iteration ranges interact with the `quint8`→`int8` QDQ export for this particular
checkpoint), not a generic fine-tune overfit that a longer LR schedule would fix. This matches `32`
§H43d's own statement ("not simply 'more overfitting'") and `66` H43d's identical framing; this audit
found no basis to weaken or strengthen that conclusion further with the data available.

## 4. Downstream QAT-story clause added

Added, verbatim, wherever the QAT story is told outside `32`/`66`/`FACTS_VERIFIED.md` (all of which
already stated the H43d result in full): **"longer QAT (600 it) does not help and hurts two
checkpoints (H43d) — remaining loss is INT8 quantisation of this architecture, not the fine-tune."**

- `38_EDGE_DEPLOYMENT_FOR_DEFENCE.md` §2.5 row 13 — appended after the existing H43d prose.
- `68_MOCK_INTERVIEW_ROUND4_TECHNICAL.md` Q10 follow-up 2 — appended; this location previously had
  **no H43d mention at all** (stale since H43c, predating H43d) — now current.
- `65_DRESS_REHEARSAL_V2.md` §4 gap 4 — appended; also fixed a stale "not itself measured (proposed
  follow-up H43d)" line in §0 item 8, which predated H43d actually running, to state the refutation.
- `77_COLD_READ_REVIEW_V2.md` #3 — appended.
- `91` (checked): no QAT/H43 mentions exist in that document; nothing to add.
- `removed-vendor-doc.md` (flagged mid-audit): §2 edge-budget bullet and the §3 90-day-plan
  bullet still said H43d was "pre-registered and running, not yet resolved" (stale since H43d
  completed) — both fixed to the refuted result with the same clause, and the 90-day bullet now
  points at H43e (TensorRT on real Jetson) as the remaining item.

`60` item 37 and `AUDIT_H43BC.md` already state the H43c-era "recipe not export" attribution as a
hedged inference with an H43d pointer and were left as historical record (they describe what was true
before H43d ran); `60` item 37 does not itself repeat the QAT story with the specific "recipe vs
export" framing this clause targets, so it was not edited.

## 5. `66` — H43d status and H43e added

`66`'s H43d block and ranked-list row 15e already read "done, hypothesis refuted" before this audit —
correct, no fix needed. Added **H43e** (row 15f and a status note inside the pre-existing `## H43 ·
TensorRT INT8 on real Jetson hardware` block): the original H43 pre-registration bundled a
TensorRT-on-real-Jetson arm with a CPU-only "else QAT" fallback; the fallback ran to completion as
H43/H43b/H43c/H43d (all done, all CPU-only, none met either bar), but the TensorRT-on-hardware arm
itself never ran (no Jetson available) and remains the only edge item with no measurement at all.
Relabelled that un-run arm **H43e** so it is tracked as its own item rather than left implicit inside
an otherwise-completed H43.

## 6. R46 (no latency claims) and CLAUDE.md scope check

No latency number or INT8-vs-FP16/FP32 speed comparison was added anywhere in this pass; `cpu_latency_ms_median`
is not referenced in any edited file. No edits touched `survsim/`, `out/`, `docs/research/03`,
`docs/research/58`, `docs/research/71`, or any H-section in `32` other than §H43d's one wording fix
(non-numeric: "not supported" → "refuted").

## Score: 9/10

Every H43d number in `32`/`FACTS_VERIFIED.md`/`66` was already correct and recomputes exactly from
`results.json`; the −0.500 recovery is explained by INT8-specific regression (not FP32 overfit, not a
generically higher LR) and tied to the concrete config difference (H51 `dose300` vs h14b `mix_300`
checkpoints); the QAT-closing clause is now present in all five places the QAT story is told outside
the primary log, including one location (`68` Q10) that had silently gone stale with no H43d mention
at all. The one point off: this audit added a new hypothesis id (H43e) by relabelling part of an
existing, already-registered H43 block rather than opening a fresh, independently pre-registered
entry — defensible given H43e genuinely never ran and needs hardware this environment does not have,
but it is a naming decision made unilaterally rather than one that went through its own
pre-registration pass.
