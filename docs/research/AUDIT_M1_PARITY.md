# AUDIT_M1_PARITY · `evaluate_mot` vs reference TrackEval (commit `5571631`)

Audited 2026-09-27. Scope: the M1 parity claim in 32 §"M1 parity", docs/13 §TrackEval
parity, `tools/trackeval_parity.py`, `survsim/eval/tracking.py` diff, and propagation of
the new MOT20-subset numbers across docs. CPU only.

## 1. Re-run [V]

`tools/trackeval_parity.py --old 5571631~1` re-run from scratch into the scratchpad
(7 m 12 s wall, CPU). Max |ours − TrackEval| over every metric and sequence:

| case | max \|Δ\| re-run | committed results.json |
|---|---|---|
| edge (empty frames, ID switch, fragmentation, combined) | 0 | 0 |
| MOT20-01/02 frames 1–300 (+ combined) | 9.99e-16 | 9.99e-16 |
| batch_v8 `street_crowd_day` 3 cams (+ combined) | 7.77e-16 | 7.77e-16 |

All three ≤ 1e-15: **parity confirmed.** Re-run MOT20 combined: HOTA 0.44284, IDF1 0.55852,
hota_at_05 0.53720, MOTA 0.4658 — identical to the committed file.

## 2. Old code reproduces 0.4342 [V]

The `old` arm (tracking.py at `5571631~1`; byte-identical to `d1e7f0f`, which docs/13 names)
gives MOT20 combined HOTA **0.434235**, IDF1 0.54943, hota_at_05 0.53935, IDSW 114 — the
published pre-parity row. So the inputs (cached detections → numpy ByteTrack) are the same
and the +0.0086 is the scorer alone.

## 3. The five defects vs the diff

| claimed defect | in diff | verdict |
|---|---|---|
| HOTA per-α Hungarian → one association-aware matching (`global_alignment_score × IoU`) thresholded per α | `_hota_alphas`: potential/align matrices, single match per frame | match |
| DetA/AssA/hota_at_05 from CLEAR matching → α = 0.5 slice of HOTA | `deta_a[i05]`, `assa_a[i05]`, `hota_a[i05]` | match |
| IDF1 from CLEAR matches → all IoU ≥ 0.5 pairs, global identity Hungarian | `np.nonzero(sim >= thr)` into `id_pairs` | match |
| CLEAR greedy cross-gap continuity → 1000× previous-frame bonus, empty-frame skip, Frag = run starts − 1 | `score = 1000*(p == prev_step[g]) + sim`; `continue` on empty g/p | match |
| 1e-9 → machine-eps thresholds | `thr = iou_threshold - np.finfo(float).eps` | match |

(docs/13 lists a sixth, MOTA = (TP − FP − IDSW)/max(1, TP + FN); also in the diff.)

## 4. batch_v8 labelling [V] with one caveat

Tool docstring, 32 and docs/13 all say batch_v8 is **GT vs a seeded perturbation of GT**
(15 % drop, 4 px jitter, one ID swap, 5 % FP) because no cached tracker output exists — honest.
Caveat: the old scorer also agreed on it to ≤ 4.4e-16, so batch_v8 (like the edge cases)
does **not discriminate** old from new; only MOT20 does. 23's M1 row lists "batch_v8 day"
without the perturbed-GT qualifier — minor.

## 5. Findings

1. **Regression guard weaker than the claim.** `tests/test_trackeval_parity.py` asserts
   1e-6 (edge) and **1e-3** (MOT20), while docs claim 1e-15. A 1e-3 drift would pass. Not a
   false claim (the measured value is 1e-15), but the test would not catch a small regression.
   Recommend 1e-9.
   **Closed 2026-09-27:** tolerance now 1e-9 / 1e-12 (`4b9534d`). Tightening exposed that
   `tools/trackeval_parity.py::score()` raised `KeyError: 'deta_mean'` on COMBINED since `2fdecd6`
   (H24 added bridge-only `deta_mean`/`assa_mean` keys; score() looked every bridge key up on
   `TrackingResult`). Fixed by comparing only `TrackingResult` fields; re-run [V] max |Δ| 9.99e-16
   (MOT20 subset + edge), batch_v8 7.8e-16. Guard: `tests/test_trackeval_parity_keys.py`.
2. **Stale docs** (fixed here): 17, 18, 21, 24, 35, 40, 42, 46, 48, 52 (its [V]/[A] table still
   said "Parity with TrackEval: not done"), 54, 56, 57, 59, 65, 68, 00, docs/13 pre-parity rows,
   26 §8.2 item 3 ("STILL OPEN") and the worked example (0.403 exact → 0.4005 at parity).
3. **H9/H17 deltas are pre-parity.** Notes added to 32 §H9, §H17 results, 73 §3.1, FACTS (H9a,
   H9b, H17 rows), 64 and 68: absolute values pre-parity, deltas **not recomputed**; no claim
   that they hold. Recomputing them is cheap (CPU) and should precede quoting them as TrackEval.
4. RETIRED_CLAIMS R41–R43 added (HOTA 0.434, IDF1 0.549, hota_at_05 0.539 without a
   pre-parity/parity qualifier). Historical AUDIT_* files left as-is.
5. MOTA "unchanged" is true only at 3 dp (0.4662 → 0.4658); fine as stated.

## Score

**88 / 100.** The core claim is reproduced exactly and every listed defect is in the code;
deductions for the 1e-3 test tolerance (−5), non-discriminating batch_v8/edge cases presented
alongside MOT20 as equal evidence (−3), and incomplete propagation at commit time (−4).
