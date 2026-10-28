# AUDIT_H38 · Quantised export of the h14b detector (32 §H38)

Audited 2026-09-27 against `d6b204d` (runner, 13, 38 §2.5, 68 Q10, FACTS) and `dc402ad` (32
results section), pre-registration `0e36a98`. Method as AUDIT_H25: every number recomputed in
Python from `out/experiments/h38_quant_export/results.json` (`checkpoints[*].arms`, `ap`,
`ap_mean`, `latency_ms_mean`, `decision`); method claims checked against
`survsim/experiments/quant_export.py` and `configs/h38_quant_export.yaml`.

## 0. Process defect found first

The H38 results section written in `dc402ad` is **not in HEAD**: `5108fc9` (H34) rewrote 32 from
a copy that predated it. Restored after the H38 pre-registration, corrected as below. FACTS had
the H38 row glued onto the batch_v8 row (`|| batch_v8 …`, one table row); split.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| wall 5,183 s | 5,183.2 s | match |
| FP32 torch mean 0.4961 (0.4970 / 0.4957 / 0.4955) | same | match |
| ONNX FP32 identical (sanity ≤ 0.001) | `sanity_max_abs` 0.0 | match |
| all 15 per-checkpoint APs and 5 means in the table | equal to 4 d.p. | match |
| AP75 means 0.5310 / 0.5310 / 0.5309 / 0.5008 / 0.5033 | same | match |
| FP16 loss 0.0000 [−0.0002, +0.0003], met | losses −0.0001/−0.0002/+0.0003; `fp16_met` true | match (interval = range, row below) |
| INT8 real 0.4844, loss 0.0117 [0.0081, 0.0154] | 0.0115/0.0081/0.0154 | match |
| s2 0.0154 > 0.015 → INT8 not met ("all 3" rule) | `int8_met` false; rule in `0e36a98` is "on all 3" | match |
| INT8 syn 0.4829, loss 0.0132 | same | match |
| real − syn +0.0015 [−0.0004, +0.0044], calib not met | 0.0005/0.0044/−0.0004; `calib_met` false | match |
| "as predicted" (calibration branch fails) | pre-reg prediction: "synthetic a few 1e-3 worse, the calibration branch probably fails" | match |
| **"95 % bootstrap" intervals** | percentile bootstrap over n = 3: each all-same resample has p = 1/27 = 3.7 % > 2.5 %, so the 2.5/97.5 percentiles are exactly min and max — every interval is the range | **mislabelled** → "range" in 32/13/38/68/FACTS (pre-reg had warned) |
| AP50 falls "≤ 0.004" | 0.0042 / 0.0002 / 0.0024 | **imprecise** → ≤ 0.0042 |
| AP75 falls "0.024–0.040" | 0.0263 / 0.0245 / 0.0399 (mean 0.0302) | **imprecise** → 0.025–0.040 |
| "reproduces h14b GPU numbers (0.4969/0.4956/0.4952)" | CPU FP32 is +0.0001/+0.0001/+0.0003 above GPU FP16 | minor → "within 0.0003" |
| CPU latency 178/141/198/273, PyTorch 3,065 ms, context only | `latency_ms_mean` same | match |
| "ORT CPU QDQ INT8 was not faster than FP16" | the same graph ranges 57–264 ms (onnx_fp32) and 105–367 ms (int8_syn) across checkpoints: contention noise 4.7×; no arm comparison is supported | **unsupported** → retracted (R46) |
| calibration procedure = registration | static PTQ, QDQ, per-channel S8/S8, MinMax; real = 100 evenly spaced MOT20-01 61–429; syn = 50 render + 50 degraded, seed 38, dirs not prefixed `_` (only `_failed_entrance_gate` exists); 23 `/model.22` decode nodes excluded | match |
| 68 Q10: "site footage is not needed for calibration" | the "real" arm is MOT20-01, not the MOT20-02 test site; neither arm is on-site | **overclaim** → "calibration source (off-site real vs synthetic) did not matter; on-site untested" |
| 38 row 13 interval "[−0.0081, −0.0154]", "AP50 ≤ −0.004" | reversed order; 0.0042 | **imprecise** → fixed |

## 2. Interpretation carried to the corpus

Export is free at FP16; INT8 PTQ costs ~0.012 AP, and it is box tightness (AP75), not detection
(AP50) — matters for anything metric (ground-plane feet, speed, height). Calibration source did not
matter. No Jetson latency is measured; the 38 §2.5 sizing (10–12 cams/NX, costed on INT8 4.54 ms)
survives FP16 at ~11 cams/NX [INF]. Follow-up H43 (TensorRT INT8 on an Orin, else QAT).

Propagated: 32 §H38 (restored + fixed), 13, 38 §2.5 row 13 + arithmetic, 68 Q10, FACTS (row split,
ranges), 52 §4.4 register, 64 register + §4.2 paragraph, 60 #33/#37/not-to-say #6, 48 C8g + #45,
65 N15, 74 drill 1 (d) + diagram FP16, 23 gap row, 66 (H38 done, H43 added), 77 #3 partially
closed, 78 (stale "not run" lines), RETIRED_CLAIMS R46, 00 index.

## 3. Score

21 claims checked: 14 match, 1 minor (h14b reproduction wording), 6 wrong/imprecise fixed
(interval label, AP50, AP75, latency comparison, site-footage overclaim, 38 row 13).
**Score 14.5 / 21 (69 %)** — every AP and loss value was right and the decisions stand; the defects
were the n = 3 "CI", an unsupported latency comparison, a scope overclaim on calibration, and a
results section lost from HEAD by a concurrent commit.
