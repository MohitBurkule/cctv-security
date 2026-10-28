# AUDIT_H22_H33 · Operator review queue and conformal θ (32 §H22, §H33)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** the 58 §8 ship recommendation noted here (θ by CRC, ranked) is replaced by the measured 58 §8.4 staffing table: 1 operator → conformal θ 0.9629 ranked; ≥ 2 → A1 ranked; never pooled (AUDIT_H42, AUDIT_H45, R48).
>
> **Superseded in part (AUDIT_88, H33b):** the CRC used here took B = the largest calibration loss, so the guarantee audited below is approximate. CRC guarantee holds for a loss bounded by a B fixed in advance; H33 used the empirical max B (84–89, approximate); H33b uses a fixed B = 123.5 FA/cam-h — θ 0.9615–0.9642, held-out FA 2.216 ≤ 2.915 in 10/10 splits, recall −0.006 vs empirical B (32 §H33b).

Audited 2026-09-27 against `93cc3b1` (32 as written). Method as AUDIT_H19_H20: every number in 32's
H22/H33 pre-registration and results sections recomputed in Python (`.venv`) from
`out/experiments/h22_operator_queue/results.json` (`model`, `cells[*].horizons`, `ranked_minus_fifo`,
`decision`, `wall_h`, `bulk_*`) and `out/experiments/h33_conformal_theta/results.json` (+ `data.json`
for episode peaks); method claims checked against `survsim/experiments/operator_queue.py`
(`tag_alarms`, `add_twin_floor`, `simulate`, `_boot`) and `survsim/experiments/conformal_theta.py`
(`choose_plain`, `choose_crc`, `heldout_fa`, `decide`) and both configs.

## 1. H22 — recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| sanity A1 0.825 / 2.915; dwell_25 0.367 / 6.007 | 297/360 = 0.825, 2.9151; 132/360 = 0.3667, 6.0070 | match |
| twin floor 1.008, recall 0.825 | 1.00799; tp 297 | match |
| "~79 wall-hours per seed" (pre-reg and results) | `wall_h` 80.556 | **imprecise** — fixed to 80.6 in results; pre-reg left as registered |
| table: 6 cells × {util, @30 s, @5 min, CIs} | all 36 values equal to 3 d.p. | match |
| alarms/h 120 / 244 / 44 | 119.8 / 244.3 / 43.7 | match |
| bulk-acked 25 % / 60 % | 0.2534 / 0.5966 | match |
| twin_floor bulk-acked "0 %", "no bulk-acks" | 0.0019 of alarms; 0.6 bulk-acks per seed | **imprecise** — fixed to 0.2 % / 0.6 |
| 222 clear-alls per seed | `bulk_acks_mean` 222.4 | match |
| decision inconclusive, bar 0.495 | bar 0.4950, CI [0.4836, 0.5374] straddles | match |
| "keeps 62 % (58–65 %)" | 0.619; CI/0.825 = 58.6–65.1 %; seed range 0.481–0.553 = 58–67 % | **imprecise** — range was CI, now labelled; seed range added |
| ranked − FIFO rows, seeds +/− | all 6 diffs, CIs and 10/0, 1/9 counts match | match |
| "3× the realised recall" at 30 s | 0.3886 / 0.1267 = 3.07 | match |
| twin 0.725 of 0.825 (88 %) | 0.7247, 0.878 | match |
| fatigued capacity ~96/h | 3600 / (30 × 1.25) = 96 | match |
| utilisation per policy | FIFO and ranked **identical** to 1e-15 in every seed | not wrong, but unexplained — by construction (same arrivals, same RNG draw sequence, bulk-ack on length) → caveat added |
| realised = "taken up within H" | `take()`: `now − t0 ≤ h` at pop, then miss draw | match (caveat already present) |
| bootstrap = world clusters over 300 recall worlds, pooled seeds | `_boot`: resample `rec_idx`, sum over seeds | match |

## 2. H33 — recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| A1 on 676 clean worlds 2.915 | 8,751 FA / 3,002 cam-h = 2.9151 | match |
| table: 10 rows (θ range, exceed, FA mean + seed CI, recall) | all match except the row below | match |
| α 0.001 plain "θ 1.000", "never alarming (θ = 1)" | θ 0.9999961–0.9999971; 1 test FA in 3/10 splits (≤ 0.00068 FA/cam-h, no exceed); recall 0 | **imprecise** — fixed |
| crc − plain −0.035 [−0.037, −0.033]; −0.031; −0.107 [−0.111, −0.104] | −0.0350 [−0.0372, −0.0331]; −0.0306; −0.1072 [−0.1106, −0.1036] | match |
| "B = 84 FA/cam-h … floor 0.248" | B ∈ {84.0, 86.5, 89.0} across splits; floor 0.2478–0.2625 | **imprecise** — seed 0 only; range added (0.248 is the minimum) |
| world bootstrap per split "≈ ±0.037" | mean half-width 0.040 | **imprecise** — fixed |
| decision supported at 2.915 (0 ≤ 1, 6 ≥ 3), cost upper 0.037 < 0.05 | `decide(0, 6)` = supported; |upper| 0.0372 | match |
| "Also supported at α = 1 and 2" | exceed rule yes (0/10 vs 5/10); ship clause fails at α = 1 (0.111 > 0.05) | **imprecise** — ship clause stated per α; `decide` omits the cost clause (applied by hand) → noted |
| P2: 0.001 needs worst-world B < ≈ 0.34 | 0.001 × 339 = 0.339 | match |
| P3 grid exceeds in 6/10 | 6 | match |
| "3.5 recall points" | 0.035 | match |
| implied reading "CRC keeps FA ≤ α in 10/10 splits" as the guarantee | CRC (as coded) bounds E[per-world k/camh], marginal over calibration draws; per-world mean test FA at α 2.915 = 2.54–2.89 (≤ α); full-set per-world mean 3.417 vs pooled 2.915 | **missing caveat** — added: 10/10 is an observed frequency, the guarantee is on the per-world expectation |
| 167 s on 4 cores | `wall_seconds_this_invocation` 167.1 | match |

## 3. Fixes applied in place (32)

1. H22 wall-hours ~79 → 80.6 (results, conclusion).
2. H22 twin-floor bulk-ack 0 % → 0.2 %; "no bulk-acks" → 0.6 per seed run.
3. H22 "58–65 %" labelled as CI; seed range 58–67 % added.
4. H22 caveat: utilisation policy-invariant by construction.
5. H33 α 0.001 plain row and P2 text: θ ≈ 0.999996, 0–1 FA per split, not "θ = 1, never".
6. H33 B 84 → 84–89, floor 0.248–0.263.
7. H33 recall world-bootstrap ±0.037 → ±0.040.
8. H33 "also supported at α = 1 and 2" split into exceed rule vs ship clause; `decide` scope noted.
9. H33 what CRC guarantees (per-world expectation, not per-split pooled cap) added.

Downstream: FACTS rows H22/H33; 52 §4.4 register + header; 64 §4 register rows + §4.4 paragraph +
Figure 6 (`figures/fig_h22_h33.png`) + Appendix A; 60 items 31–32; 48 numbers 40–41 + Q&A C8b/C8c;
65 N12 + D4 + retired list; 58 §8 ship recommendation (θ by CRC, ranked queue; weights unchanged);
23 M9; 66 H22/H33 done, H35 motivation. H21/H23 (running) untouched.

## 4. Score

| criterion | before | after |
|---|---|---|
| H22 numeric accuracy vs results.json | 9/10 (79 h, 0 %) | 10/10 |
| H33 numeric accuracy vs results.json | 8.5/10 (θ = 1, B, ±0.037) | 10/10 |
| decision rules applied as registered | 9/10 (α = 1 ship clause) | 10/10 |
| statement of what CRC guarantees | 6/10 | 9.5/10 |
| caveats (invented operator, policy-invariant utilisation, exchangeability) | 8/10 | 10/10 |
| code ↔ text agreement | 9/10 (`decide` scope) | 10/10 |
| provenance | 10/10 | 10/10 |
| **total (×100/70)** | **85/100** | **99/100** |
