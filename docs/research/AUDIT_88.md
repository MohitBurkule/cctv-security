# AUDIT_88 · Coding drills, from a hostile ML lead running a live-coding round

Audited 2026-09-27 against `82876b1` (88 as written). Read: `88_CODING_DRILLS.md`,
`drills/drills.py`, `tests/test_coding_drills.py`, and the survsim references
`eval/tracking.py::evaluate_mot`, `baselines/bytetrack.py::{_KF,_match}`,
`experiments/autocalib.py::dlt_homography`, `experiments/conformal_theta.py::choose_crc`,
`experiments/dose_fixedstep.py::paired_contrasts`. Probes in scratchpad; no GPU, editor, `out/`.
Nothing under `survsim/` was changed.

**Score: 7/10.** The ten drills are the right ten, and each (b)/(e) is mostly
the question a real panel asks. But three references had real bugs: a wrong
MOTA/IDSW in one case, a solve-then-filter gate (the very trap Drill 3 warns
about), and a DLT that was not normalised while claiming parity with a
normalised one. In every case the "matches survsim exactly" tests passed
because they used toys too clean to separate the two versions. A candidate who
learned from the old file would have written the Drill 7 bug in the room.

## 1. Correctness beyond the tests

| Drill | Probe | Verdict / fix |
|---|---|---|
| 1 IoU | point box, zero-height line, 0×0 vs 0×0, empty A | [V] all 0, no NaN (`np.maximum(union,1e-12)` inside `np.where`). Inverted boxes (x1<x0) are *not* caught (area of two negatives is positive); stated as a clarifier |
| 2 NMS | equal scores; IoU exactly = thr | [V] stable sort keeps the lower index; `<= thr` kept (torchvision `>` suppresses). O(N²) worst case correct. Both now tested |
| 3 Assignment | `[[1,2],[2,100]]` greedy trap | [V] (already tested). **Bug:** `hungarian` solved then filtered by `max_cost`. On `[[0,.45],[.45,.6]]`, gate .5, it and greedy return 1 match and a gated solve returns 2. **Fixed:** `gate_first=True` (big finite constant, not inf); the old behaviour kept as `gate_first=False` with a test. The tracker (Drill 5) inherits the fix. ByteTrack's default `_match` is still solve-then-filter (`gate=True` is docs/13 fix 2); noted, not touched |
| 4 Kalman | 8-D (cx,cy,a,h,v·), px and px/frame, noise ∝ h; miss = predict only | [V] matches `_KF` at rtol 1e-12. "bit-for-bit" in 88 was not what the test asserts; reworded. Added the units and the "never update with the prediction" miss trap |
| 5 Tracker | birth only from unmatched high; death at `age > max_age`; order stage 1 → 2 → age → birth → kill | [V] tests cover a one-miss survive and a two-miss death. Omissions vs real ByteTrack (stage 2 over *tracked* only, unconfirmed stage) now stated |
| 6 DLT | 12 noisy 1080p points | **Bug (claim):** reference was unnormalised; 88 claimed parity with survsim's Hartley version using 4 exact points, where every correct DLT agrees. **Fixed:** Hartley normalisation added (`normalise=True` default); new test: matches survsim at rtol 1e-8 on noisy points, and `normalise=False` does *not* |
| 7 MOTA/IDF1 | GT matched to 1, missed in a frame that has a pred, then overlaps 1 (IoU .54) and 2 (IoU .82); plus FP-only and empty frames | **Bug:** the continuity bonus used the last-*ever* pred id; TrackEval (and `evaluate_mot`) use the *previous scored frame*. Old drill: IDSW 0, MOTA −0.33; survsim: IDSW 1, MOTA −0.67. Also `n_gt = 0` raised ZeroDivisionError. **Fixed:** `prev` (reset per scored frame) vs `last` (IDSW); frames with an empty side are skipped for matching; MOTA = (N−FN−FP−IDSW)/max(1,N). The new test matches survsim on MOTA, IDF1 and IDSW. IDF1 was already a global identity assignment over all IoU ≥ .5 pairs [V] |
| 8 Loiter | on/off thresholds; leave-and-return | [V] time hysteresis (t_on fires, t_off re-arms). Added: a blip after the alarm does not re-fire. 88 now says that blip frames are not *added* to dwell, and that a return under a new track id restarts from zero |
| 9 Conformal | rank ⌈(n+1)(1−α)⌉ | [V] **drills.py uses the finite-sample rank** (equivalently the ⌈(n+1)(1−α)⌉/n quantile). A sweep over n=1…299 × 6 α against `Fraction` found no float off-by-one; a −1e-9 guard was added anyway and the sweep is now a test. **`choose_crc` uses the CRC analogue** n/(n+1)·mean + B/(n+1) [V]. Caveat added: B defaults to the largest *observed* loss (survsim documents it as a "declared empirical bound"), so the CRC guarantee is approximate unless B is fixed a priori |
| 10 Bootstrap / sign-flip | percentile vs BCa; n=10 | [V] percentile (not BCa), which is now stated along with why BCa does not rescue n=5. Sign-flip is exact: n=10 enumerates 1,024 patterns and ten same-sign differences give 2/1,024 (new test). The n ≥ 6 minimum for p<.05 is correct (2/64) |

## 2. Complexity claims
All correct: IoU O(NM); NMS O(N²) + sort; Hungarian O(n³), greedy O(nm log nm);
KF O(d³) per track, constant; DLT constant (8×9 SVD; 2N×9 overdetermined);
CLEAR O(F·n³) + identity O(I³); loiter O(n)/O(1); conformal O(n log n);
sign-flip O(2ⁿ·n), bootstrap O(B·n).

## 3. "Matches survsim" re-run
`pytest -q tests/test_coding_drills.py`: 19 passed (12 original + 7 added). All six
parity claims hold after the fixes. Two of them (Drill 6, Drill 7) held before only
because their toys could not tell the two versions apart. Drill 4's "bit-for-bit"
is now "rtol 1e-12".

## 4. Interview framing
Every trap is one a panel sets. Drill 3's gate trap and Drill 7's continuity trap are
now the strongest, because the old reference fell into both. Each drill now ends with
**(f) What they are really testing**.

## 5. Time budget
Now in the table and in each heading. 10 min: 1, 2, 3, 6, 8, 10. 25 min: 4, 5, 7, 9.

## Remaining
- The ByteTrack baseline's default solve-then-filter is a survsim question, not a drill
  question (docs/13 fix 2 measured it). Out of scope here.
- Drill 5 remains "behaviour only". There is no parity test against `ByteTracker`,
  because the drill has no Kalman filter.
