# AUDIT_H45 · Operator sim at the three H42 operating points (32 §H45)

Audited 2026-09-27 against `090e358` (pre-registration) and `85e6b18` (results, 58 §8.5, 13, FACTS).
Method as AUDIT_H42: every number recomputed in Python from
`out/experiments/h45_operator_points/results.json` (`model`, `cells`, `vs_ref`, `decision`) and
`point_streams.json` (FA/cam-h and TP recounted from the tagged streams); A1 cells compared
field-by-field with `out/experiments/h22_operator_queue/results.json`; model points compared with
`out/experiments/h42_theta_policy/results.json`; method checked against
`survsim/experiments/operator_queue.py` (`simulate` multi-operator branch, `build_point_streams`,
`_paired`, `run_points`). No GPU, no editor.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| realised @5 min, 1 op, FIFO / ranked: A1 0.511 / 0.586, pooled 0.324 / 0.504, conformal 0.571 / 0.621 | 0.5108 / 0.5861, 0.3244 / 0.5036, 0.5714 / 0.6214 (CIs as in row.md) | match |
| realised @30 s: A1 0.127 / 0.389, pooled 0.090 / 0.376, conformal 0.184 / 0.411 | 0.1267 / 0.3886, 0.0900 / 0.3761, 0.184 / 0.411 | match |
| loads 120 / 205 / 92 alarms/h at 40 cams | 119.84 / 205.50 / 91.7 | match |
| utilisation 0.88 / 0.95 / 0.79 | 0.8804 / 0.9524 / 0.7938 | match |
| bulk-ack share 0.25 / 0.53 / 0.12 | 0.2534 / 0.5276 / 0.122 (dropped ÷ alarms) | match |
| paired vs A1 @5 min: pooled FIFO −0.186 [−0.212, −0.161], ranked −0.083 [−0.103, −0.064], 0/10 seeds up | −0.1864, −0.0825 [−0.1034, −0.0637]; seeds +/− 0/10 both | match |
| conformal FIFO +0.061 [+0.037, +0.085], ranked +0.035 [+0.016, +0.055], 10/10 up | +0.0606, +0.0353 [+0.0157, +0.0551]; 10/0 both | match |
| sweep: pooled best +0.013 [−0.009, +0.035] at 3 ranked; never CI > 0 at 1–3 | +0.0133 (7/3 seeds); `pooled_beats_ref_at_operators` null/null | match |
| 2 ops: conformal − A1 ranked −0.022 [−0.045, −0.001] | −0.0222 [−0.0452, −0.0008], **0/10 seeds up** | match; 32's "≈ tie" is **imprecise** (below) |
| 3 ops: pooled FIFO −0.024 [−0.048, +0.001]; conformal ranked −0.034 [−0.056, −0.013] | same | match |
| not met; conformal utilisation cut 10 % < 20 % | 1 − 0.7938/0.8804 = 9.84 %; `decision.hypothesis_met` false, (a) and (b) false | match — the cut is identical under FIFO and ranked (queue order does not change review count or time); 32 now says so (minor) |
| (b) fails "on utilisation only" | CRC − A1 CI lower bounds +0.037 / +0.016 ≥ −0.03 | match |
| streams reproduce H42's model points exactly | recount from `point_streams.json`: A1 2.9151 / 297 of 360, pooled 5.0326 / 322, conformal 2.2179 / 282 — equal to H42 `crc.summary.modal` and `pooled.summary` to full precision | match |
| A1's one-operator cells reproduce H22 | utilisation, alarms/h, bulk counts and both horizons' realised recall identical to H22 `A1/fifo`, `A1/ranked` (floats equal); only bootstrap CIs differ (different resample seed) | match |
| H22 config/behaviour unchanged | `h22_operator_queue.yaml` last touched `1d8cd26`; `simulate` with `operators` absent → n_ops = 1, `free = [max(f, t)]` ≡ old `if t_free <= t: t_free = t`; `pytest -k "h22 or h45"` 2 passed | match |
| "θ 0.962851 — the modal CRC draw" | H42 `crc.summary.points`: 10 distinct θ (0.962851–0.964855), **each count 1**; "modal" is a tie-break that returns the lowest θ = the most permissive draw (FA 2.218 = the max of 2.099–2.218) | **imprecise** → 32, 58, 66, FACTS now say "most permissive of 10 distinct draws" |
| ship table 1 op → conformal ranked; 2 → A1; never pooled | follows from the cells above; at 2 ops A1 beats conformal 0/10 seeds up and pooled by −0.062 [−0.085, −0.040] | match |

## 2. Corrections made (Edit in place)

* 32 §H45 results: "conformal −0.022 ≈ tie" → a small but consistent loss (CI excludes 0, 0/10 seeds up);
  added audit notes (utilisation leg is one number for both queues; "modal" CRC draw = most permissive of 10
  distinct draws, mean draw θ 0.9643 not simulated; 3-op conformal ranked seeds 1/9).
* 58 §8.4: "not measured" cells replaced by H45's measured values; the [INF] bracketing kept for the record
  and marked as confirmed in direction; "Default recommendation until H45 runs" replaced by the measured
  ship recommendation — **1 operator/40 cams → conformal θ 0.9629 ranked (0.621 realised); ≥ 2 operators →
  A1 θ 0.95 ranked; never pooled θ 0.9**. §8.5 gains "0/10 seeds up" for the 2-operator comparison.

## 3. Propagation

52 (H42 row + loiter paragraph), 64 (H42 paragraph), 60 #23 (still 39 items), 48 C8e follow-up + #41c,
65 N2b, 74 constants row + drill 1 alarm load, 78 results line + opener + first-90-days M9 bullet, 79 Q21,
FACTS (ship-point row now measured; H45 row gains loads, bulk shares, 2-op result, CRC draw, audit tag),
66 (H45 DONE with result; **H48 added**: validate the operator model against a real SOC's per-alarm
review log — timestamps, operator/shift, disposition, bulk-clears, seeded test events for the miss rate),
77 weak answer #1 partially closed (which-threshold-ships is now a staffing table in simulation; real
tracks and real review times still open). Figure pack: figure 3 redrawn with H45 realised-recall bars per
point (FIFO/ranked, 95 % CIs, model recall dashed); every caption hard-wrapped (figure 7's was clipped at
the right edge); figure 2's legend moved off the data; all 8 PNGs viewed; `pack.pdf` rebuilt; 80 text
for figures 3 and 7 updated.

## 4. Score

20 claims checked: 17 match, 1 minor (utilisation cut reported per queue though identical by
construction), 2 imprecise ("≈ tie" for a 0/10-seed loss; "modal" for a tie-broken, most permissive
CRC draw). **Score 18 / 20 (90 %).** Every number recomputes and both reproduction checks (H42 model
points, H22 A1 cells) are exact; the defects are wording. The whole ship table rests on the invented H22
operator — H48 is what would make it quotable to a site.
