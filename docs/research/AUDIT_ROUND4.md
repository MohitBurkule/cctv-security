# AUDIT_ROUND4 · Loiter redesign round 4 (58 §8.1–8.2: H21 + H23)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** H21's `ships` = A1 is the round-4 decision only; the ship point is now an operator-budget choice (58 §8.4, AUDIT_H42/AUDIT_H45, R48).

Audited 2026-09-27 against `bd4c028` (results) and `06475ab` (pre-registration). Method as
AUDIT_H22_H33: every number in 58 §8.2 recomputed in Python (`.venv`) from
`out/experiments/h58_round2/round4_h21_results.json` (`results.*`, `C_fa_over_seeds`,
`C_recall_over_seeds`, `C_seeds_clearing_bar`, `ships`) and `round4_h23_results.json`
(`per_seed[*].{F,R,R_minus_F,rel_gap}`, `decision`, `F_fa`, `R_fa`, `R_minus_F`, `rel_gap`);
method checked against `tools/loiter_eval.py` (`cmd_h21`, `cmd_h23`, `_select`,
`stratified_fold`, `paired_world_diff`, `seed_bootstrap`, `h23_decision`, `A1_LO`, `H21_GRID`)
and `tests/test_rules_round4.py`.

**Score: 20/25 checked claims match, 5 imprecise (fixed in place), 0 wrong; 2 missing caveats added (plus 1 clarifying caveat). Headline numbers and both decisions all reproduce.**

## 1. H21 — recomputed

| claim in 58 | recomputed | result |
|---|---|---|
| A1 re-scored 2.915 [2.854, 2.977] / 0.825 | 8,751 / 3,002 = 2.9151; Garwood [2.8543, 2.9768]; asserted in code | match |
| per-seed C θ 0.051/0.043/0.043/0.051/0.051, clock 5 | 0.05104 / 0.04336 / 0.04336 / 0.05104 / 0.05104 | match |
| C FA 2.765 / 3.216 / 2.992 / 3.126 / 2.703 + Garwood | all 5 + CIs equal to 3 d.p. | match |
| C recall 0.831 / 0.844 / 0.839 / 0.833 / 0.833 + CIs | match | match |
| C − A1 −0.150 [−0.231, −0.067], +0.301, +0.077 [−0.009, 0.164], +0.211, −0.212 [−0.293, −0.131] | all match (paired clean-world cluster bootstrap, 2,000, seed 58) | match |
| clears bar: yes/no/no/no/yes | recomputed as select-recall ≥ 0.85 ∧ recall ≥ 0.80 ∧ Garwood upper < 2.8543: same; 2 < 4 → `ships` "A1" | match |
| ship rule (≥ 4/5 ∧ seed 58 ∧ CI < 0) | code matches registration | match |
| B reference θ → FA / recall (5 rows) | all match | match |
| mean 2.960 (SD 0.223) [2.785, 3.135]; recall 0.836 [0.832, 0.841] | 2.9604, 0.2228, [2.7855, 3.1354]; 0.8361 [0.8322, 0.8411] | match |
| "no fallback was used" | every C `selectable` true; chosen select recall 0.868 (92/106) seed 58, 0.858 (91/106) seeds 59–62 — the minimum passing count | match; **caveat added**: C sits exactly on the constraint |
| P9: θ 0.043–0.051 inside 0.03–0.07; < 4/5 clear; FA overshoot on 3/5 | yes; 2.765 and 2.703 in band, 3 above | match |
| P9: "recall 0.831–0.844" vs predicted 0.80–0.84 | 0.844 is outside the band | **imprecise** — noted |
| "One grid step moves FA by 0.9" (B) | seed 61 θ 0.9 → 2.250 vs seeds 58/59/60/62 θ 0.8 → 3.114–3.145: adjacent grid points, but *different seed models* | **imprecise** — reworded (R45) |
| wall 2,587 s | `wall_s` 2587.1 | match |

## 2. H23 — recomputed

| claim in 58 | recomputed | result |
|---|---|---|
| table: 10 seeds × F/R θ, clock, FA, Garwood, recall, R − F [boot] | all 90+ values equal to 3 d.p. | match |
| F 4.397 (1.023) [3.762, 5.033]; R 4.018 (1.314) [3.236, 4.776] | 4.3974 / 1.0229 / [3.7621, 5.0326]; 4.0177 / 1.3143 / [3.2357, 4.7760] | match |
| recall F 0.874 [0.853, 0.894], R 0.852 [0.827, 0.875] | 0.8736 [0.8528, 0.8944]; 0.8519 [0.8272, 0.8747] | match |
| **R − F −0.380 [−0.896, +0.203]**; (R − F)/F −8.5 % [−21.6, +6.2] | −0.3797 [−0.8956, +0.2033]; −0.0852 [−0.2159, +0.0620] | match |
| R wins 5 (58/158/258/458/858), F wins 5 (358/558/958 + 658/758 recall < 0.80) | `h23_decision` re-applied by hand: identical; `decision` = 5/5 no-dominance | match |
| "no retrained seed reaches ≤ 2.915 at recall ≥ 0.80" (lucky) | `retrained_at_or_below_A1` 0; 2.257 / 0.789 and 1.827 / 0.783 are below 0.80 | match |
| 7/10 pick θ 0.9 → 5.033 / 0.894; 3/10 (558/658/758) pick 0.95 → 2.915 / 0.825 | yes; F clock 5 on all 10 | match |
| "single step moves H12 FA by 2.1" | 5.0326 − 2.9151 = 2.118 | match |
| "~106-event select fold" | select-fold event counts from recall fractions: 106 (58/158/258), 108 (358/558/758/858), 112 (458), 113 (958), 102 (658) | **imprecise** — now "102–113 (106 on seed 58)" |
| "flips between adjacent grid points on one or two events" | the per-point select grid is not saved; only seed 558's pass margin is known (92/108 = 0.852, one event); the fail margin on the other 7 folds is not recoverable | **imprecise / unverifiable** — replaced (R44) |
| "A1's 2.915 … comes from round 1's selection landing on θ 0.95" | round 1 selected on a different split; the 3/10 rate is from the 10 new folds | **imprecise** — tagged [INF] |
| all 9 new splits 0 errors, 450 worlds | not in the results JSON (gen logs) | not checked here |
| wall | `wall_s` 2039.2 (scoring only; excludes gen/feats) | — |

## 3. Method and disclosure checks

* **Frozen arm re-selects θ per fold.** Registered in §8.1 ("θ × clock re-selected on seed s's
  select fold"), so not a deviation — but §8.2 never said that F is therefore *not* the shipped
  A1 (equal on 3/10 seeds) and that the "lucky" count compares R with the fixed 2.915, not with
  F. **Missing caveat — added** to 58 §8.2 and 32.
* **P10's last sentence** (A2's round-2 gap came from selection, not weights) had no verdict.
  Not tested directly (no arm reproduces A2's window-only selection); consistent [INF]. **Added.**
* Seed-58 fold equals the round-3 select fold (asserted in `cmd_h21`); A1 re-score asserted
  (|Δ| < 5e-4). `paired_world_diff` resamples clean worlds with both arms paired (2,000, seed 58);
  `seed_bootstrap` 10,000, seed 23 — both as registered. H21 fits exclude `late` rows; H23's
  `learned_rule` fit uses the whole fit fold — each as in its own round-3 recipe.
* Verdicts: P9 holds in substance; P10 two of three parts hold, "A1 typical" fails. Both stated
  correctly in 58.

## 4. Fixes applied in place (58 §8.2)

1. C's chosen point sits on the recall constraint (92/106, 91/106) — added.
2. P9 recall range: 0.844 just above the predicted 0.80–0.84 — noted.
3. B "one grid step moves FA by 0.9" → across different seed models (3.114–3.145 vs 2.250).
4. "~106-event … one or two events" → 102–113 events; only seed 558's one-event margin is known.
5. "comes from round 1's selection" → tagged [INF].
6. F ≠ shipped A1 on 7/10 seeds; lucky count is R vs 2.915 — added.
7. P10 A2 clause: not tested directly — added.

## 5. Folded in

32 (new round-4 section, appended; H24/H26/H34/H38/H40b untouched), FACTS (2 rows), 52 (register
row + status line), 64 (register row, round-4 bullet, θ-selection paragraph), 60 item 23, 48 C8e
("is your loiter rule lucky?") + fact row 41b, 65 N2b, 23 (M6 row, §6 bullet), 66 (H21/H23 done,
H42 added), 00 (index row), RETIRED_CLAIMS R44–R45.
