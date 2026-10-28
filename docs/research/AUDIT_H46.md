# AUDIT_H46 · Appearance-weight sweep and night arm (32 §H46)

Audited 2026-09-27 against `6c87152` (pre-registration) and `aae5206` (results; code, 32 results,
FACTS, 66, 13, 73). Method: recomputed ΔAssA/ΔDetA/ΔHOTA/ΔIDSW per w directly from
`out/experiments/h46_reid_w_night/results.json`'s per-checkpoint `COMBINED` scores (a simple mean
across checkpoints — a direction/consistency check, not a re-derivation of the registered two-way
bootstrap over sequences × checkpoints); Holm correction applied to the 5 day-set w-vs-control
comparisons using SEs backed out of the reported 95 % CI half-widths; fused-cost formula read from
`survsim/baselines/bytetrack.py:_match`/`ByteTracker`. Scope: H46 only — §H46b (X134, in
progress) and `survsim/experiments/reid_assoc.py` were not touched.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| batch_v8 day argmax w = 4, ΔAssA rises monotonically 0.25→4 | mean-of-checkpoints ΔAssA (COMBINED): +0.0114/+0.0285/+0.0446/+0.0641/+0.0997 at w=0.25/0.5/1/2/4 — different absolute values than the registered per-sequence-mean statistic (expected, different aggregation), same monotone-rising shape, same argmax w = 4 | match (direction/shape) |
| MOT20-02 argmax w = 4, never decreases | +0.0072/+0.0157/+0.0181/+0.0248/+0.0443 — monotone rising, argmax w = 4 | match (direction/shape) |
| "no MOT20-02 decrease" | all 5 w give a positive mean ΔAssA in this recomputation too | match |
| ΔIDSW reported per w, falls as w rises | day: −2.0/−5.4/−11.8/−16.2/−25.4 (0.25→4); MOT20-02: −3.0/−5.2/−5.6/−4.8/−1.0 — falls at every w on both sets (MOT20-02 non-monotone but never rises above 0) | match; IDSW never rises alongside the AssA rise |
| ΔDetA/ΔHOTA reported alongside ΔAssA | not reported per w in 32 §H46's table (only ΔAssA/ΔIDSW are) | **imprecise** — DetA/HOTA deltas exist in `results.json` and were checked here (they rise, never fall, at every w on both sets: day ΔDetA +0.0007→+0.0056, ΔHOTA +0.0036→+0.0359; MOT20 ΔDetA +0.0009→+0.0103, ΔHOTA +0.0031→+0.0199) but are absent from the published table — AssA is not rising on the back of a DetA drop, but the table does not show that, contrary to the audit brief's expectation that ΔDetA/ΔHOTA be reported per w |
| night arm −0.0147 [−0.0972, +0.0535] | matches `results.json['night']`; CI width 0.1507 | match |
| "underpowered, not disproved" (night) | n = 2 sequences × 1 checkpoint vs 5 checkpoints for day/MOT20-02; CI wide enough to contain plausible small-positive effects | match — honest wording, not overclaimed either direction |
| "both clear H24's +0.02 bar" / "hypothesis (a) — met" | true of the point statistic and its own CI, but the argmax w = 4 is selected from the same 5 arms whose CI is then quoted (post-hoc selection) | **qualified** — a garden-of-forking-paths pattern: selection and inference use the same data; see §2 |
| implicit "5 independent tests, no multiplicity issue" | 5 w values vs w = 0, day set, no stated correction | **flagged** — see §2, w = 4 does not survive Holm |
| "no default change to w = 1 is made from this result alone" | `analyse()`/32 text: sweep is diagnostic only, decision deferred | match |

## 2. Statistics

**Multiplicity.** Approximating each arm's SE as `(CI_hi − CI_lo) / (2 × 1.96)` from the reported
day-set 95 % CIs and computing a two-sided normal p-value:

| w | mean ΔAssA | SE (approx) | z | p | Holm threshold (ascending rank) |
|---|---|---|---|---|---|
| 4.0  | +0.0421 | 0.0188 | 2.242 | 0.0249 | 0.010 |
| 2.0  | +0.0271 | 0.0126 | 2.159 | 0.0308 | 0.0125 |
| 1.0  | +0.0194 | 0.0111 | 1.748 | 0.0804 | 0.0167 |
| 0.5  | +0.0122 | 0.0083 | 1.467 | 0.1424 | 0.025 |
| 0.25 | +0.0020 | 0.0052 | 0.382 | 0.7021 | 0.05 |

**w = 4's p (0.0249) exceeds its Holm threshold (0.010) — it does not survive Holm correction
across the 5 w values, and neither does any other w.** 32 §H46 reports each w's own CI (correctly
excluding 0 for w ≥ 1 individually) but never states that 5 comparisons were made against the same
control with no adjustment; the "both clear H24's bar" framing reads as more decisive than a
Holm-adjusted family permits.

**Garden of forking paths.** The pre-registered hypothesis text says "the best w ... gives ΔAssA
≥ +0.02 ... with CI lower bound > 0 ... else report the mismatch." That is exactly what happened:
the *argmax* is chosen from the 5-arm sweep, and *then* that argmax's own CI is quoted as evidence
it clears the bar. This is the textbook garden-of-forking-paths setup — the selection rule and the
significance test share the same draw, so the quoted CI's nominal 95 % coverage does not apply to
"the best of 5 arms." The pre-registration is honest that this is what will happen (it says "else
report the mismatch," not "else stop"), but the results text's "Hypothesis (a) — met" does not
carry that caveat forward into the verdict language itself. **Verdict: defer to H46b's
cross-set-validation arm (w tested on an independent split before treating w = 4 as a validated
optimum, not a sweep-argmax).** This is now stated in 32 §H46 (audit paragraph, appended within
§H46 only) and propagated to FACTS_VERIFIED, 13_BASELINES, 66, 73 wording, and RETIRED_CLAIMS R62.

## 3. Fused-cost formula / w → ∞

`survsim/baselines/bytetrack.py:_match`:

```python
r, c = linear_sum_assignment((1 - iou) + app_weight * app)
...
m = [(i, j) for i, j in zip(r, c) if iou[i, j] >= thresh]
```

The assignment problem is solved on `(1 − iou) + w·app`; the result is then filtered by a fixed
IoU gate (`match_iou`, default 0.2) **regardless of w**, including w = 0. As w → ∞ the `(1 − iou)`
term becomes negligible relative to `w·app`, so the linear-sum-assignment step degenerates to
appearance-distance-only matching among all candidate pairs — but the acceptance gate is
unchanged, so a pair chosen purely for appearance similarity is still discarded if its IoU falls
below 0.2. **w → ∞ is therefore not "appearance-only, gate removed" — it is "appearance-only
assignment, IoU gate still enforced afterward,"** which can strand detections unmatched (lost, not
mis-swapped) when the appearance-best partner fails geometry. The monotone AssA rise observed up
to w = 4 is consistent with appearance breaking IoU ties among geometrically plausible candidates
(gate-preserving) rather than the gate doing the work by itself (the gate is identical at every
w), but the sweep never tested whether a much larger w starts trading correct matches for gate
rejections — an open question the results text's caveat (1) already flags for "does AssA keep
rising past w = 4," and this audit narrows it to "or does the gate start rejecting more
appearance-preferred pairs."

## 4. Score

10 claims/derivations checked: 7 match, 1 imprecise (ΔDetA/ΔHOTA exist but are not in the
published per-w table), 1 qualified (garden-of-forking-paths in the "met" verdict), 1 flagged
(no multiplicity correction; w = 4 does not survive Holm). Scoring match 1, imprecise/qualified/
flagged ½: **Score 8.5 / 10 (85 %)**. Every number recomputes; the day/MOT20-02 point estimates
and CIs are correct on their own terms. The defect is entirely in verdict strength: "Hypothesis
(a) — met" and "both clear H24's bar" are true of the selected arm's own CI but overstate what a
5-way post-hoc sweep with no multiplicity correction can certify — that is exactly what H46b's
cross-set validation exists to resolve, and this audit's corrections say so everywhere the claim
was quoted without that qualifier.
