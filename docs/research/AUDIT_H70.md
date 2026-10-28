# AUDIT_H70 — alarm budgets at estate scale (adversarial audit, 2026-09-28)

Scope: 32 §H70 (pre-registration 9554eed, results be2ca77), `survsim/experiments/alarm_budget_scale.py`,
`survsim/experiments/configs/h70_alarm_budget_scale.yaml`, `out/experiments/h70_alarm_budget_scale/results.json`,
`docs/research/figures/h70_budget_scale.png`, FACTS row. Simulated; no engine or GPU.

| # | Check | Verdict |
|---|---|---|
| 1 | Order | **OK.** 9554eed touches only 32 (pre-registration); runner, config, test, results and figure first appear in be2ca77. |
| 2 | "Recall is detector-limited" | **True by construction, was stated as a finding.** Every site shares one intrusion score model N(1.5, 1) and p_detect 0.775; at B the pooled θ ≈ −0.04, so the ceiling 0.775 × P(N(1.5,1) ≥ θ) × 0.95 ≈ 0.69 is fixed by inputs. K = 3 giving the same recall only shows the queue is not binding at utilisation 0.84 with bulk-ack at 20. Labelled in 32 and FACTS; R67 added. |
| 3 | D3 drift detection 1.0 | **Construction of the design.** At B = 0.5 a site expects 0.5 × 10 × 24 = 120 FA/day; the hour-96 check sees 12 h normal + 12 h ×3 ≈ 240 vs a p < 0.001 threshold ≈ 155. Smallest drift caught [derived, Poisson, per-site at B]: ×1.25 0.041, ×1.5 0.323, ×1.75 0.768, ×2 0.968, ×3 1.000. D3 therefore certifies large drifts only. |
| 4 | Pooled monitor 0.133 as comparator | **Not a fair threshold-scheme comparison.** (a) tests the estate total (mu 4800/day) so a one-site excess of ≈ 120 is < 2 SD; an estate-total monitor catches ×3 0.085 (derived), ×5 0.63, ×10 1.0. Nothing in pooled θ forbids per-site monitors at that θ; the 0.133 vs 1.0 contrast is monitor granularity. Also (a)'s "notice" counts any estate flag on the drift day (upper bound; already labelled). Text fixed. |
| 5 | σ_δ = 0.3 from H69 | **Honestly labelled as matched to an interim number**, but the unit differs: H69's 56.5 % (N = 9, interim; final 0.53 of splits, 0.68 per held-out site) is a detector-FP rate on 3 s clips in held-out splits, not a per-site alarm rate. Realised (a) within budget ≈ 1 − 15.3/39 ≈ 0.61. Qualifier added to 32. |
| 6 | Worst-site FA 1.622 vs 2B | **Consistent.** B = 0.5 in config, 2B = 1.0; 1.622 = 3.2 × B. "3× budget" in the takeaway is the worst site; ≈ 3.3 sites per world exceed 2B. |
| 7 | (b) in-sample budget leak | **No leak.** Headline (b) numbers are test-week (worst 0.551, 19.3 sites > B labelled Poisson noise around θ set at B). In-sample budget is listed under "by construction". |
| 8 | Operator = H22? | **Yes, minus fatigue (declared).** Gamma 30 s CV 0.3, miss 0.05, clear-all at queue > 10 per operator match the FACTS H22 row; that operator is itself invented. K operators share one queue (bulk-ack at 10·K), an extension of H22's single operator. |
| 9 | FACTS / 32 sentences | Mostly honest; two fixes: "detector-limited" now "by construction"; "(a) estate monitor 0.133" now carries the granularity and minimum-drift qualifier. |
| 10 | Takeaway "per-site governance ... not recall" | **Overclaim.** Recall equality is an input, and the monitor contrast is granularity. Reworded in 32 as a simulation of declared rates, not a measured governance answer. |

## Rerun (10 worlds × 3 seeds, primary σ_δ = 0.3, 1000 bootstraps)

| seed | recall@300 K=2 (a / b / c) | (c) − (a) [95 %], Holm p | worst FA (a / b / c) | (c) worlds ≤ 2B | drift noticed (a / b / c) | D1 D2 D3 |
|---|---|---|---|---|---|---|
| 1 | 0.691 / 0.720 / 0.693 | +0.002 [−0.018, +0.022], 0.91 | 1.628 / 0.552 / 0.925 | 0.8 | 0.1 / 1.0 / 1.0 | F F T |
| 2 | 0.670 / 0.675 / 0.675 | +0.005 [−0.015, +0.031], 0.55 | 1.440 / 0.551 / 0.821 | 1.0 | 0.3 / 1.0 / 1.0 | F T T |
| 3 | 0.688 / 0.686 / 0.674 | −0.014 [−0.046, +0.020], 1.00 | 1.687 / 0.550 / 0.903 | 0.8 | 0.1 / 1.0 / 1.0 | F F T |

Direction reproduces: D1 fails every seed, D3 met every seed, decision NOT met every seed. D2 is seed-sensitive at
10 worlds (seed 2 passes), so "D2 fails" rests on the 30-world primary (0.8).

## Retired / qualified
- R67: H70 "detector-limited" without "by construction" / AUDIT_H70.

## Honest interview sentence
*In a simulated 40-site estate with the same detector everywhere, one pooled threshold keeps the estate on budget
while about three sites run above twice their budget, and re-allocating the budget buys no recall because the
detector is identical by assumption; a per-site daily count catches a site tripling its alarms, a whole-estate
count mostly misses it, though the per-site check only reliably catches drifts of about ×2 or more.*
