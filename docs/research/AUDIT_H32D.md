# AUDIT · H32d night-profile stage ablation (32 §H32d)

Pre-registration 1713d6c, results 21cea36. CPU only. Detections are not cached by the runner (only one
PNG per variant), so the audit re-ran the 14 registered variants plus two pair variants (noise+codec) on
the same 60 frames with the runner's own `GROUPS`/`_pre_codec`/`h264_sequence` calls, scoring each against
both GT files in one pass. The re-run reproduces every per-block hit count in `results.json` exactly.
LLVIP measure-only.

| # | Question | Finding | Verdict |
|---|---|---|---|
| 1 | Runner/config unchanged 1713d6c → 21cea36? | `git diff 1713d6c 21cea36` touches neither `night_stage_ablation.py` nor `h32d_night_stage_ablation.yaml` | Holds |
| 2 | Redundancy reading (noise AOI 0.988, codec AOI 0.744, both LOO small) | Measured the pair: removing noise **and** codec from the full chain gives recall 0.870 → pair LOO share **0.978 [0.941, 1.013]**; noise+codec alone gives 0.041 → pair AOI **0.959 [0.924, 0.989]**. Each alone is sufficient, the pair is necessary: two redundant killers, as read | Holds (now measured) |
| 3 | "≤ 6 % for darkness/blur/denoise" under block bootstrap | Point estimates ≤ 0.059, but upper 95 % limits reach 0.097 (isp AOI, CI [0.034, 0.097] excludes 0) and 0.062 (colour LOO). On the 449-row GT isp AOI is 0.067 [0.043, 0.105]. Minor, not "innocent" | Reworded (R80): "each ≤ 7 %, upper CI ≤ 11 %" |
| 4 | 2× upsample before crf 39 — bug or design? | Design: every profile has a fixed output `resolution` (the modelled camera, 1280×720); the renders are 640×360, so resize (INTER_AREA, i.e. upsampling), then defocus, noise at 720p pixels, then crf 39 on the upsampled frame. Not a profile bug, but the finding is "crf 39 on a 2×-upsampled 360p render", not "crf 39 at a native 720p camera" (a 20 px person is 40 px to the codec; injected noise is per 720p pixel, i.e. finer than scene detail) | Qualify wording |
| 5 | GT: 362 mock-visibility rows vs corrected 449 render-visible rows (`out/gt_vis_v2/showcase_all_night`) | Re-scored from the same detections: raw 0.766 [0.667, 0.850], loss 0.762; noise LOO 0.199 [0.129, 0.278], AOI 0.988 [0.966, 1.005]; codec LOO −0.006, AOI 0.749 [0.697, 0.803]; pair LOO 0.977, AOI 0.959; other groups ≤ 0.067. Every share moves ≤ 0.02; decision (not met), culprit (noise) and reading unchanged | Holds; quote with GT stated |
| 6 | "noise ≈ 3× real" vs H32c's 2.21× | Different arms: 3.3× is σ 0.558 of **aoi_noise** (noise stage alone at raw brightness, no denoise/codec) vs hold-out 0.1685; 2.21× is the **shipped** chain's σ 0.3723 (denoise + codec smooth part of the injected noise). Both true; "injects ≈ 3× real-night noise" must say "noise stage alone" and the output figure is 2.21× | Reworded |
| 7 | FACTS / 32 sentences | FACTS numbers match `results.json`. 32 "Honest night sentence" said "darkness, blur and denoise are innocent (≤ 6 %)" and "injects ≈ 3× real-night noise" unqualified — corrected in place (audit note appended), FACTS row extended with rows 2–5 | Fixed |

**Pair variants are post hoc** (not registered); they test the reading, not the decision.

**Honest sentence.** "The shipped night profile fails for two redundant reasons: its noise stage alone
(3.3× real at raw brightness; the shipped output reads 2.21×) erases people, and its crf 39 alone, on a
2×-upsampled 360p render, removes three quarters of them; removing both recovers 0.978 of the loss, either
alone at most 0.2, and the other stages are minor (each ≤ 7 %, upper CI ≤ 11 %)."

Re-score script (not committed, scratch): variants via `night_stage_ablation.GROUPS`, pair variants
`loo_noise+codec` = all groups but noise and codec, `aoi_noise+codec` = only those two; GT v2 via
`batch_cameras(out/gt_vis_v2, showcase_all_night, min_vis=0.01)`; bootstrap as `bootstrap()` (10 000, seed 0).
