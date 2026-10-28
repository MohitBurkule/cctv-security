# AUDIT_H46B · Extended w sweep, cross-set validation, full night arm (32 §H46b)

Audited 2026-09-27 against `out/experiments/h46_reid_w_night_b/results.json`, `row.md`,
`survsim/experiments/h46_reid_w_night_b.py`, `survsim/experiments/reid_assoc.py`,
`survsim/baselines/bytetrack.py`, docs/research/32 §H46b, docs/13_BASELINES.md §H46b follow-up.

## 1. Recomputed from `results.json`

| claim | recomputed | result |
|---|---|---|
| day argmax w = 16, ΔAssA +0.0613 [+0.0171,+0.1142] | `ceiling.day.argmax_w` = 16.0, `cross_validation.day_dAssA_at_w_star_from_day` = {mean 0.0613, boot95 [0.0171,0.1142]} | match |
| day ΔIDSW at w=16 −0.22 (spans 0) | `row.md`: `-0.22 [-2.77,+1.98]` | match, CI spans 0 |
| mot20 argmax w = 8, ΔAssA +0.0486 [+0.0314,+0.0631] | `ceiling.mot20.argmax_w` = 8.0, `cross_validation.mot20_dAssA_at_w_star_from_mot20` = {mean 0.0486, boot95 [0.0314,0.0631]} | match |
| mot20 ΔIDSW at w=8 +15.8, CI excl. 0 | `row.md`: `+15.80 [+6.00,+26.80]` | match, excludes 0 |
| mot20 ΔIDSW +69.2 at w=32 | `row.md`: `+69.20 [+58.40,+80.00]` | match |
| app_only ΔIDSW +13.4 day / +162.0 mot20 | `row.md`: `+13.43 [+2.72,+28.67]` day, `+162.00 [+134.60,+188.80]` mot20 | match |
| app_only ΔDetA −0.0109 (day) | `row.md`: `-0.0109 [-0.0225,-0.0004]` | match, CI excludes 0 |
| cross-val. w*(day=16)→mot20 held-out ΔAssA +0.0479 [+0.0328,+0.0629] | `cross_validation.mot20_dAssA_at_w_star_from_day` | match |
| cross-val. w*(mot20=8)→day held-out ΔAssA +0.0570 [+0.0208,+0.0987] | `cross_validation.day_dAssA_at_w_star_from_mot20` | match |
| full night arm (6 seq × 5 ckpt, w=16): ΔAssA +0.0470 [−0.0046,+0.1337] | `night.analysis["16.0"].assa_mean_delta` = {mean 0.047, boot95 [-0.0046,0.1337], n_seq 6, n_units 5} | match, n_seq = 6 confirmed (not "2 seq") |

All numbers recompute exactly from the shipped `results.json`; no discrepancies found in the
headline table (32 §H46b, docs/13 §H46b follow-up, `row.md` all agree with each other and with
`results.json`).

## 2. Cross-validation: did it peek?

`survsim/experiments/h46_reid_w_night_b.py:_cross_validate` (lines ~76–90) computes
`w_from_day = argmax(day_analysis)` and `w_from_mot = argmax(mot_analysis)` **independently**, each
from only its own set's per-w `assa_mean_delta`. It then reports:
- `day_dAssA_at_w_star_from_day` (selection and evaluation both on day — not held-out, correctly
  not quoted as a held-out number anywhere in 32/13/66)
- `mot20_dAssA_at_w_star_from_day` (**w* chosen on day, evaluated on mot20** — genuinely held-out)
- `mot20_dAssA_at_w_star_from_mot20` (selection and evaluation both on mot20 — not held-out)
- `day_dAssA_at_w_star_from_mot20` (**w* chosen on mot20, evaluated on day** — genuinely held-out)

The two numbers quoted throughout the docs as "cross-validated held-out" (+0.0479 and +0.0570) are
exactly the two that use a w* selected on the *other* set. **No peeking found** — the selection
rule and the reported CI are computed on disjoint data in both directions. This is a real
improvement over H46/AUDIT_H46's garden-of-forking-paths problem (argmax and its own CI drawn from
the same 5 arms), and 32 §H46b's text correctly credits H46b, not H46, with clearing R62's bar.

## 3. ΔHOTA reported?

Yes — every row of the `row.md` / 32 §H46b table carries ΔHOTA alongside ΔAssA/ΔDetA/ΔIDSW (e.g.
day w=16: ΔHOTA +0.0327 [+0.0051,+0.0686]; mot20 w=8: ΔHOTA +0.0272 [+0.0181,+0.0351]; night w=16:
ΔHOTA +0.0239 [−0.0080,+0.0770]). `HOTA_α = √(DetA_α · AssA_α)` (geometric mean), so a rising AssA
with flat-to-slightly-falling DetA (day w=16: ΔDetA −0.0037) still lifts HOTA, just by less than
AssA alone — consistent with every reported ΔHOTA sitting between 0 and its arm's ΔAssA. AUDIT_H46
flagged ΔDetA/ΔHOTA as *missing* from H46's table; **that gap is fixed in H46b** — no repeat finding.

## 4. Pre-registered hypothesis verdicts

| hypothesis | pre-registered bar | verdict as recomputed | verdict as stated in 32 §H46b |
|---|---|---|---|
| (a) ceiling exists ≤ w=32 | AssA peaks then falls at or below w=32 | **yes** — day peaks at w=16 (32 lower, +0.0600); mot20 peaks at w=8 (16/32 lower) | "met, but the ceiling is an IDSW cliff, not a clean optimum" — matches |
| (b) held-out ΔAssA ≥ +0.02 both directions | cross-validated w* clears +0.02 on the other set | **met** both directions (+0.0479, +0.0570, both CI excl. 0) | "met on point estimates, met on this data" — matches |
| (c) night CI excludes 0 | ΔAssA > 0 with bootstrap CI excluding 0 at w* (16), 5 ckpt | **not met** — mean +0.0470 > 0, but boot95 lower bound is −0.0046, which does not exclude 0 | "not met on the pre-registered CI test" — matches, correctly said as **not met** rather than softened to "effectively positive" |

All three verdicts in 32 §H46b/docs/13/66 match the pre-registered bars exactly, including the
important discipline of calling (c) **not met** despite the positive point estimate and the
much tighter CI than H46's single-checkpoint arm.

## 5. Fold-in check (tracker recommendation)

The canonical sentence — "ByteTrack + OSNet-ImageNet appearance at w ≈ 8 (cross-validated; +0.05
AssA held-out) with the IDSW cost stated; never appearance-only" — is now present in `73` §3
(primary), and mirrored in `60` (item 37, cheat sheet ≤ 40 items unchanged), `48` (C8h + table row
68 has no H24/H46-specific answer to update, only generic ByteTrack anchors — left alone per
scope), `23` (M3 reference-tracker bullet), and `66` (H24 row now notes "H46b bar met post
cross-validation at w = 8"; H46b's own entry gets the same sentence appended). `RETIRED_CLAIMS.md`
R62 gets an update note: the allowed-form hedge is no longer only about w = 4 post-hoc — w = 8/16
are now cross-validated, but any argmax quote still needs its ΔIDSW stated.

## 6. Figure

`fig_h46b.png` did not exist before this audit (a dangling reference in 32 §H46b/docs/13 — the
filename was named in prose but never generated or committed). Generated at
`docs/research/figures/fig_h46b.png` from `results.json`/`row.md` directly: panel (a) ΔAssA vs w
on both sets with `app_only` as a separate diamond marker and the two argmax lines annotated;
panel (b) the matching ΔIDSW vs w (shows the MOT20-02 IDSW rise and the app_only spike); panel (c)
a bar chart of the full night arm's four deltas (ΔAssA/ΔDetA/ΔHOTA/ΔIDSW-scaled) with their 95% CI
whiskers at w = 16, visually showing the CI touching 0. Referenced from 32 §H46b and docs/13
§H46b follow-up.

## Score

**9/10.** The headline numbers, the cross-validation's no-peeking property, ΔHOTA reporting, and
all three hypothesis verdicts were already stated correctly and recompute exactly from
`results.json` before this audit — H46b's own write-up is unusually careful (better than H46's).
The one point off: the figure referenced by name in 32 §H46b and docs/13 since the 2026-09-27
results landed had never actually been generated or committed, and the tracker-recommendation
sentence, while implied by the numbers, was not written as a single explicit, quotable line in any
