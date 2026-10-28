# AUDIT_H3G — adversarial audit of H3g (noise recalibration)

Scope: 32 §H3g (pre-registration 1065f88, results 21cb015), `survsim/experiments/noise_recalibration.py`,
`configs/h3g_noise_recalibration.yaml`, `out/experiments/h3g/{estimate,results}.json`, figure, FACTS row. CPU, cached outputs only.

| # | Check | Verdict |
|---|---|---|
| 1 | Raw render reads 0.52 > real 0.263: does it invalidate "shipped 1.47× real"? | No, but it must be labelled. The estimator counts texture/aliasing in "flat" regions; the pipeline removes much of it (s = 0 still reads 0.119, shipped 0.387). The ratio is **output vs real on the same estimator, different scenes** — the right comparison for "does our output look like real CCTV", not a sensor-noise ratio. Subtracting the texture floor in quadrature (≈ 0.37 added) makes the profile look noisier, not cleaner, so "≥ 1.5×, not 2×" stands as an estimator-level statement. |
| 2 | s = 0.246 fitted on the frames it is judged on | Yes: fitted to the median of the same 12 real frames that define the HN band. **In-sample**; matched noise 8/12 in band is largely by construction. Labelled in 32 and FACTS. |
| 3 | 0.324 → 0.607 on the same frames? | Yes: raw/shipped/matched are all on H3f's scored 50 far frames (paired, shipped reproduces H3f's 0.324). That is half H3f's registered 100 — registered as such in H3g, inherited from H3f. "About half the lost far recall" = (0.607 − 0.324)/(0.924 − 0.324) = 0.47: honest. CI [0.513, 0.713] clears shipped. |
| 4 | Unreachable HN (real 4/12 vs bar 8/12) | Registration flaw (joint 3-stat band of 12 frames). The HN is **uninformative as registered**, not a clean fail. "1/12 < real 4/12" is post-hoc on n = 12, no test — a reading, not a result. The informative, per-stat finding: blockiness 2/12 vs real 8/12 (shipped 12/12). Not retired as a number; FACTS now says "uninformative as registered". |
| 5 | H32 "overfit pattern" supported by two experiments? | **No.** H32 failed a hold-out after tuning; H3g had no hold-out. H3g shows coupling (fit noise → blockiness leaves band). 32's "Reading (H32 pattern)" reworded; R76 guards the two-experiment claim. |
| 6 | Decision scoring | Correct: far 0.607 ≥ 0.60 (point), near 1280 drop 0.084 > 0.05 → NOT met. Near "60 % of the cost removed" = (0.210 − 0.084)/0.210: correct. |
| 7 | Reach | 65 §0 item 21 and 103 §2 get one line each. Demo files out of scope. |

**Honest sentence.** "On one noise estimator our day profile reads about 1.5× (1.47) real CCTV, not 2×; matching it — fitted in-sample to 12 real frames — recovers about half the lost far recall on the same 50 frames (0.324 to 0.607), but the stages are coupled (blockiness leaves the real band) and the near cost stays 0.084, so every degraded-stream number is still a lower bound."
