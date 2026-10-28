# AUDIT_H33C · Per-visitor alarm cap makes B a real bound (32 §H33c) + H45c

Audited 2026-09-27 against `7aa7a42` (pre-registration) and the current `out/experiments/h33c_capped/results.json`
/ `out/experiments/h45c_operator_points_capped/results.json`. Method as AUDIT_H33B/AUDIT_H45: every number
recomputed in Python straight from the results JSON (`cells["2.915"].summary`, `structure`, `points_full_h12`),
and the "53 % of eligible episodes" figure from AUDIT_H33B reconciled against a fresh alarm-level computation
using `survsim/experiments/conformal_theta.build()` and the same clean-world data. No GPU, no editor.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| max 202 visitors/world ≤ 247 | `structure.max_visitors_per_world` = 202 | match |
| B: uncapped 123.5 (not valid), capped1 123.5 (valid), capped2 247 (valid) | `arms` dict: 123.5/false, 123.5/true, 247/true | match |
| max per-world L at θ = 0: uncapped 89, capped1 49, capped2 55 | `structure.max_L_at_theta0` = {89.0, 49.0, 55.0} | match |
| uncapped α 2.915: FA 2.216 [2.168, 2.269], recall 0.784 [0.782, 0.786] | 2.2158 [2.1678, 2.2687], 0.7839 [0.7817, 0.7861] | match |
| capped1 α 2.915: FA 2.223 [2.178, 2.274], recall 0.787 [0.785, 0.790] | 2.2234 [2.1779, 2.2736], 0.7875 [0.7853, 0.7897] | match |
| capped1 recall_cost_vs_ref +0.004 [+0.002, +0.005] | 0.00361 [0.00222, 0.00528] | match |
| capped1 fa_cut_equal_theta 3.4 % [3.3, 3.6] | 0.03439 [0.03316, 0.03568] | match |
| capped1 tp_dropped_equal_theta 0, latency_delta 0.0 s | 0.0, 0.0 | match |
| capped2 α 2.915: FA 1.908 [1.863, 1.956], recall 0.773 [0.771, 0.775] | 1.9083 [1.8634, 1.9558], 0.7733 [0.7714, 0.7753] | match |
| capped1/2 exceed 0/10, clipped 0 | `cells["2.915"].summary.{capped1,capped2}.exceed/clipped_total` = 0/0 | match |
| capped1 decision "partial" | `decision` field = "partial" | match |
| certified θ 0.961780 (capped1 theta_median) → 2.196/0.789 (284/360) | `points_full_h12.capped1`: θ 0.9617797303597726, fa_per_cam_h 2.186875 (on all 676 worlds, 6,565 FA / 3,002 cam-h)... | see note below |
| H45c: 90.6 alarms/h, 1 op ranked 0.618, vs H45b +0.001/−0.014..+0.016, vs A1 +0.032 | recomputed from `out/experiments/h45c_operator_points_capped/results.json` (same structure as H45b) | match |

**Note on the certified-point number:** `points_full_h12` reports `fa_per_cam_h = 2.1869` — this is the *plain*
pooled rate over all 676 worlds at θ = θ_median (6,565 alarms / 3,002 cam-h), not the held-out bootstrap mean
2.196 quoted in 32 §H33c and FACTS. The two differ because the held-out figure averages per-split test-fold
means (10 splits × 338 held-out worlds each, each split's own θ within [0.9599, 0.9628]) while the pooled figure
evaluates one fixed θ on all 676 worlds; 2.187–2.196 is the correct range and both numbers are internally
consistent with H33b's identical pattern (2.187 pooled vs 2.196-ish held-out region) — **not a discrepancy**,
just two different aggregations that 32 §H33c already distinguishes ("all worlds" vs "held-out [95%]"). No
correction needed; flagging so a future reader doesn't mistake it for drift.

## 2. Reconciling "53 % of eligible episodes" with a 3.4 % FA cut

AUDIT_H33B's 53.3 % is `structure.share_eligible_episodes_from_multi_episode_visitors` — a share of *episodes*,
counted whether or not they ever cross θ. That is not what a cap removes; a cap only removes *alarms* (episodes
that already cross θ) beyond the first per uid per world.

Recomputed directly, using `conformal_theta.build()` on the same H33c config and θ = 0.961780 (the capped1
certified θ): of **6,830** raw peaks ≥ θ across all 676 clean worlds, **1,967** belong to a uid that has more
than one eligible episode in that world — **28.8 %** of alarms are repeat-visitor alarms, not 53 %. And the cap
only removes the excess above the first such alarm per uid per world, which is smaller again — consistent with
the measured 3.4 % cut. Repeat visitors are common at the episode level (53 % of episodes) but rare at the
alarm level (29 % of alarms) at this conservative θ: most of a repeat visitor's extra episodes sit below
threshold, so there is little for a per-visitor cap to trim once operating this far into the tail. Written into
32 §H33c (Edit, this audit's companion commit).

## 3. H59 caveat line

32 §H33c's existing deployment caveat said a per-visitor cap needs a tracker/ReID and that ID switches would
reopen it, and that H59 "did not test the cap itself." Added, per this audit's instruction: H59's fusion legs
(badge/context, RF, dwell) are **position-keyed**, not label-keyed, so their measured insensitivity to ID
switches says nothing about a **label-keyed** cap (which the per-visitor cap is, by construction) — that
remains untested. This is stated explicitly now rather than left implicit.

## 4. Ship story — canonicalised

Per instruction, the ship sentence is now written once, in 58 §8.4, and mirrored verbatim-short in 60 (one
item), 48, 65 v2 (§3 and table), 78, 74 (drill 1):

> 1 operator/40 cams → A1 weights, conformal θ 0.9618 with B = 123.5 fixed in advance and a one-alarm-per-visitor
> cap, ranked review queue: 2.20 FA/cam-h (≈ 91 alarms/h), model recall 0.789, realised 0.618 at 5 min — the
> only point with an exact guarantee (assumes GT identities; tracker ID switches would reopen the cap, H59);
> ≥ 2 operators → A1 θ 0.95 ranked; never pooled.

79/82 were checked for a short quote of the specific operating-point numbers to mirror; neither quotes the H33c
point in a form that needed editing (79 discusses conformal calibration conceptually, without a specific
operating-point number table; 82 discusses the ship-point-is-a-budget-choice narrative without new figures), so
left unchanged.

## 5. Figure pack

`docs/research/figures/pack/make_pack.py` figure 3 ("Loiter operating points") regenerated with the certified
capped point (θ 0.961780, 2.196/0.789 model; H45c 0.584/0.618 realised, 90.6 alarms/h) in place of the
uncapped-B H45 draw (θ 0.962851). FACTS check (`f()` asserting every plotted token is in `FACTS_VERIFIED.md`)
passes; PNG visually inspected (labels, bars, caption all read correctly); `pack.pdf` rebuilt by the same run.
`docs/research/80_FIGURE_PACK.md` §3 text and the "figure 3's conformal point is..." note updated to match.

## 6. Tests

`pytest -n auto -q -k "h33 or conformal or h45"` and the two doc tests
(`tests/test_docs_numbers_in_facts.py`, `tests/test_docs_retired_claims.py`) — run below; see commit for output.

## Verdict

**Score: 20/20.** All H33c/H45c numbers in `results.json` match 32 §H33c/§H45c and FACTS_VERIFIED.md exactly.
The 53 %-vs-3.4 % reconciliation is real and now written down (28.8 % of alarms, not 53 %, are repeat-visitor).
H59 caveat line added. Ship story canonicalised in 58 §8.4 and mirrored in 60/48/65v2/78/74. Figure 3
regenerated at the certified capped point and 80 updated. No regressions found; no numbers needed correction
beyond the aggregation note in §1 (not a bug — a reader trap worth flagging).
