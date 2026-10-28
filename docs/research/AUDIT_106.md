# AUDIT_106 · adversarial audit of 106_COMPUTE_AND_COST_MODEL.md (commits da44f32, 9b78068)

Method: every decimal checked against `FACTS_VERIFIED.md` rows (H3b/H3c/AUDIT_H3C, H38/H43, H45c, H56,
H69, H70/H70b, FACTS 4/33/34) and R46/R67/R72/R74; every cameras/GPU and GPU count recomputed from the
stated ms and A1/A5/A6 (per-camera cost = fps × ms × 1.2; cameras/GPU = 700 ÷ cost).

Recomputed: 640 700/84 = 8.3, 700/93 = 7.5; 1280 700/115.8 = 6.04; tiles 700/859.8 = 0.81 (0.81× → 491
GPUs for 400); tiles at 114.1 ms 1.02; tiles at 2 fps 700/343.9 = 2.03; 400/8 = 50; 400/6 = 67;
80/6 = 13; clip WAN 200 × 10 × 2.4 / 3600 = 1.33 Mb/s; WAN ratio 400 / 81.3 = 4.9×; INT8 6 × 1.5–2 = 9–12.

| # | where | finding | fix |
|---|---|---|---|
| 1 | §3, probe 8 | H56 1-PTZ missed-second quoted 0.367; FACTS row is 0.369 [0.325, 0.406] | 0.369 |
| 2 | §1 estate, probe 1 | 320/6 + 80/2 rounded up to ~94; with the table's own 6.04 and 2.03 it is 53 + 39 ≈ 93 | ~93 |
| 3 | §3 bandwidth | 10 s alarm clip and "alarms = B × cameras" used silently as facts | declared as A12 |
| 4 | §0 A11 | INT8 speed unmeasured — correct, but did not say H38/H43 measured AP only | A11 says so; §2 "A11 (unmeasured)" |
| 5 | §4 H45c | "with ≥ 2 operators ranking stops helping (A1 θ 0.95 ranked)": misread — 32 §H45c recommends ranked A1 at ≥ 2 ops; the *capped conformal* θ stops beating it; "A1" collides with assumption A1 | reworded, CI quoted, arm name disambiguated, H22 invented-operator caveat |
| 6 | probe 7 | same misreading ("with 2+ it does not help") | reworded |
| 7 | probe 6 | H70 "same recall" at K = 2/3 without R67's by-construction qualifier (§4 had it) | qualifier + R67 added |
| 8 | §6 | "~30 operators" at 4,000 cams reads as a result; it is the K = 3 staffing choice × 10 | labelled |

Held: A2–A4 ms (FACTS H3b/H3c, AUDIT_H3C), far recall 0.491/0.681/+0.190 CI (CC0), near FP 36 → 300,
H38 FP16 0.0000 and INT8 0.0117/0.0154, H43 0.0144/0.0246/0.415, H43c 0.0138/0.439, H43d 0.374,
H69 SD 0.355, H70 0.842/0.563 and ≈ 3 sites > 2B, H70b 0.896, H3e −0.118 (R74 wording respected),
FACTS 4/33/34 vendor numbers labelled as vendor. Totals: 8 fixes, 0 numbers retired.
