# AUDIT · H32c night-profile noise/luma/recall (32 §H32c)

Pre-registration 361bb5c, results c7d073a. CPU only, cached `out/experiments/h32c`. LLVIP measure-only.

| # | Question | Finding | Verdict |
|---|---|---|---|
| 1 | Runner/config/test unchanged between commits? | `git diff 361bb5c c7d073a` touches none of `night_noise_check.py`, `h32c_night_noise.yaml`, `test_night_noise_check.py` | Holds |
| 2 | Honest denominator for "2.21× real" | Registered denominator is the 10-frame hold-out (0.1685) → 2.21×. The tuning-15 median (0.2378) is 1.41× the hold-out; against it shipped is 1.57×. Hypothesis (≥ 1.5×) holds on both, thinly on the second. Quote "2.21× hold-out (1.57× tuning)" | Holds, qualify |
| 3 | Estimator-referred like H3g? | Not a texture floor: at s = 0 the profile reads σ 0.0056 (defocus + denoise erase render texture), so shipped σ is almost all injected noise. Still estimator-referred on a different scene (raw render already reads 1.28× hold-out); shipped/raw is 1.73× | Qualify |
| 4 | Was noise matched? | s was fitted to the tuning-15 median (as registered); the arm lands at 1.45× the hold-out. **Partially matched.** "Fixing noise alone recovers nothing" overstates: noise was not brought to the hold-out level | Reworded (R78) |
| 5 | Recall collapse 0.890 → 0.006 real? | Read tool on frame 53: raw cam_01 shows ~12 people clearly lit; shipped cam_01 and matched cam_02 show dark blobs on darkened ground, many invisible, under colour noise + blur + CRF 39 blocking. GT ≥ 20 px people are present in raw | Holds |
| 6 | "Pessimistic outlier" or broken? | A profile that erases people a human sees in the raw frame, while being *brighter* than real night (51 vs 33), is not a pessimistic estimate of anything: **the night profile is broken for detection.** Existing H32/H32b rows already refuse to quote lowlight recall as a penalty (103 §2 line 5, 60, 52): kept; the only offending sentence was 32 §H32c "Reading", now corrected | Retired (R78) |
| 7 | Luma 0.64 vs 0.59 | Pre-registered and reported as "by construction" (AE target 48.65); measured 0.59 is below it because later stages darken slightly. Labelled correctly | Holds |
| 8 | FACTS / 32 sentences | FACTS numbers match `summary.json`; row extended with 1.57, 1.73, 0.0056, partial match, R78 | Fixed |

**Honest sentence (103 §2 item 8, 65 v2 item 21):** "Our shipped low-light profile is broken for detection —
it takes YOLOv8n from 0.890 to 0.006 recall on people clearly visible in the raw render, still does so with
its noise partially matched to real, and is still brighter than real night — so it is a bug to fix, not a
night penalty."
