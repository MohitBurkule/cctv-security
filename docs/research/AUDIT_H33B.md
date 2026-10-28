# AUDIT_H33B · Conformal θ with B fixed in advance (32 §H33b) + H45b

Audited 2026-09-27 against `6a6b955` (pre-registration) and `451209f` (results, 58 §8.4, FACTS, R59).
Method as AUDIT_H42/H45: every number recomputed in Python from
`out/experiments/h33b_conformal_fixed_B/results.json` (`cells[α].summary`, per-split `seeds`); B's premise
checked against the data it is meant to bound (`tools/loiter_eval.load_split("h12")`, the tick table A1 scores,
episode key `epk`) and against the code (`conformal_theta.fixed_B`, `choose_crc`,
`loiter_features.person_features` episode definition). Ship-θ inference replaced by a measurement (H45b, below).
No GPU, no editor.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| λ = 6/min × 1,800 s = 180; Poisson 1 − 1e-6 quantile 247 | `poisson.ppf(1-1e-6, 180)` = 247 | match |
| min 2.0 cam-h per world | H12 clean camera-hours ∈ {2.0, 2.5, …, 7.0} (4–14 cams × 0.5 h) | match |
| B = 247 / 2.0 = 123.5 | 123.5 | arithmetic **match**; validity **fails** (§2) |
| floor B/(n+1) 0.364 vs 0.248–0.263 | 123.5/339 = 0.3643; 84/339 = 0.2478, 89/339 = 0.2625 | match |
| 0 worlds clipped | `crc_fixed_clipped` 0 on all 30 split×α cells; max L over all 676 worlds at the lowest candidate θ = 89.0 | match |
| α 2.915: θ 0.9615–0.9642 | 0.961477–0.964196 (median 0.963436) | match |
| held-out FA 2.216 [2.168, 2.269] | 2.2158 [2.1678, 2.2687] | match |
| recall 0.784 | 0.7839 | match |
| cost −0.006 [−0.006, −0.005] | −0.00556 [−0.00639, −0.00472] | match |
| 0/10 exceed at 2.915 and 2.0; α 2.0 cost −0.005 | 0, 0; −0.0047 [−0.0067, −0.0031] | match |
| α 1.0 cost −0.028 (partial) | −0.0278 [−0.0311, −0.0247]; `h33b` = partial | match |
| θ_fixed ≥ θ_empirical on every split, every α | 30/30 | match |
| θ 0.962851 below θ_fixed in 7/10 splits | 7/10 | match |
| H33/H42/H45 reproduce under `mode="empirical"` | H33 cells identical (H33b run); H42 `theta_policy` calls `choose_crc` with the default mode (code path unchanged); H45 cells, model points and vs-A1 contrasts reproduced **exactly** by the H45b run; `pytest -k "conformal or h33 or h45"` passes | match |
| certified point "≈ 0.9635 (≈ 2.22 / 0.784)", "staffing table not expected to change" | was [INF]; 2.22 / 0.784 are split-mean *held-out* numbers, not the point's. θ 0.963436 on all 676 worlds: **2.187 / 0.783**. Staffing now measured (H45b) | **imprecise → corrected** |

## 2. Is B a valid bound? No.

B's derivation needs k_i ≤ arrivals_i, i.e. **at most one A1 alarm per visitor**. Nothing enforces that.
A1 fires once per dwell *episode* (`first_per_episode` on `epk`), and an episode is "time since the last
departure" (`person_features`: the C2 clock resets whenever net displacement over the trailing window
exceeds the departure radius). A visitor who stops, moves on and stops again opens a new episode and can
alarm again. Measured on the H12 clean worlds (A1 eligibility: clock ≥ 5 s, not in an allowed zone):

* up to **21** eligible episodes for one visitor; **13.7 %** of visitors with an eligible episode have > 1,
  and they supply **53 %** of all eligible episodes;
* one world has 125 eligible episodes more than a one-per-visitor cap would allow.

So 123.5 is **not an a-priori bound on L**. What H33b does guarantee is exact CRC control of the **clipped**
loss min(L, 123.5) — B is still fixed before calibration, so that statement is valid. On these data min(L, B)
= L on every one of the 676 worlds (max 89), so the numbers are unaffected, but that is an empirical fact about
this sample, not part of the guarantee. (Secondary: the 1 − 1e-6 tail adds ≤ 1e-6 per-world slack even under
the cap; negligible, unstated.) Fix options: enforce one alarm per visitor per world in the rule, or derive B
from an episode cap the generator guarantees (e.g. duration / minimum dwell — which is so loose CRC becomes
infeasible). Wording corrected in place in 32, 48, 58, 60, 65 v2, 66, 74, 78, FACTS; R60 added; docstring of
`fixed_B` now says the cap is unenforced (test).

## 3. H45b — the ship claim, measured

`h45b_operator_points_fixedB` (config copy with one added point θ 0.963436 = median crc_fixed θ at α 2.915;
H45's config and results untouched; 426 s CPU). A1/pooled/conformal cells and vs-A1 contrasts equal H45's
exactly. Certified point: 2.187 FA/cam-h / 0.783, 90 alarms/h, utilisation 0.79.

| 1 operator @5 min | FIFO | ranked |
|---|---|---|
| θ 0.962851 (H45) | 0.571 | 0.621 |
| θ 0.963436 (certified) | 0.573 | **0.617** |
| certified − H45 point (paired) | +0.001 [−0.012, +0.015] | −0.004 [−0.017, +0.010] |
| certified − A1 (paired) | +0.062 [+0.039, +0.085] | +0.031 [+0.014, +0.050] |

**1 operator → conformal ranked still holds** at the certified θ; ≥ 2 → A1 unchanged (2 ops ranked:
−0.019 [−0.043, +0.003], now CI-overlapping 0 instead of H45's −0.022 [−0.045, −0.001]).

## 4. Score

**15/20.** All 14 recomputed numbers match and the pre-registered decision is correctly applied (+). The
central premise is wrong: "≤ 1 alarm per visitor" was stated as a cap but is not enforced, so B = 123.5 was
presented as a valid a-priori bound when it only bounds the clipped loss (−3). "0 worlds clipped, so the
guarantee applies to the unclipped loss" does not follow (−1). The certified point was quoted with held-out
split means (2.22 / 0.784) instead of its own numbers (2.187 / 0.783) (−1). The [INF] ship claim was flagged
honestly and is now measured.
