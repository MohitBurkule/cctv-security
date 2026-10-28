# AUDIT_H3B · Adversarial audit of H3b (far-field on CC0 batch_v8)

Scope: 32 §H3b (pre-registration 97cff66, results 8405bca), `survsim/experiments/far_field_cc0.py`,
`survsim/experiments/configs/h3b_far_field_cc0.yaml`, `out/experiments/h3b/results.json`, FACTS row,
compared with 32 §H3. Re-run 2026-09-28 on the GPU (2.7 GB in use, no jobs): the detections reproduce
every recall and CI exactly; the audit only changes the bootstrap blocking.

## Verdicts

| # | Question | Verdict |
|---|---|---|
| 1 | Pre-registration order | **Confirmed.** 97cff66 04:23:35 (32 only) → results.json 04:28:18 → 8405bca 04:30:10. The runner and config were committed only with the results, so the text, not the code, was frozen. The config matches the registered arms. |
| 2 | D1–D4 same as H3's or loosened? | **Not loosened** — H3 had no numeric criteria; H3b adds them. D1 (640 recall < 0.5 at 13–20 px) is a weak bar that H3's own 0.007 made impossible to fail; D2/D3 (+0.15, CI > 0) are real bars. |
| 3 | Principle 5: < 20 px rows | **Qualify.** 3303 of 5061 far GT (65 %) are 13–20 px — not usably visible. They are fair for a detector-limit question but should not dominate a "far recall" headline. On the ≥ 20 px (20–40 px) rows alone: recall 640 / 1280 / tiled 0.060 / 0.491 / 0.401; Δ vs 640 +0.431 [0.330, 0.538] (1280) and +0.341 [0.249, 0.438] (tiled). D1–D3 all still hold. Far cameras have no GT ≥ 40 px. |
| 4 | Tiling arm vs H3 | **Different arm — stated precisely now.** H3: 320×240 tiles, 20 % overlap, letterboxed to 640 → 2.0× native linear (4× area). H3b: 704×396 tiles, 10 % overlap, at 640 → 0.91× native, i.e. *downscaled*, below full_1280's 1.0×. Both add the full frame and merge by NMS 0.5. So "tiled < 1280 on CC0" follows from tile resolution by construction; it says nothing about CC0 vs MetaHuman data. The 32 text "≈1.8× upscale" (true only relative to full_640) is retired (R72). |
| 5 | Block length | 10 sampled frames × stride 3 = 3 s at 10 fps; people stay in view longer and raw/degraded day streams are the same moments, so CIs are optimistic. Sensitivity: 30-frame blocks → far tiled Δ [0.218, 0.419], 1280 Δ [0.266, 0.479], near HN Δ [0.017, 0.085]; joint time blocks across cams and sources (9 s) → HN Δ [0.019, 0.067] (only 8 blocks, indicative). **No decision changes.** |
| 6 | Near-camera hard negative | **Honestly reported** in 32 and FACTS ("hard negative FAILS", +0.046 [0.026, 0.069], with the AP50 caveat). Survives longer blocks. Note full_1280 also gains at 40–80 px but loses at ≥ 80 px, so "extra resolution helps mid-size near people" is the reading, not "tiling is special". |
| 7 | Degraded ≈ 0 (0.000 / 0.024 / 0.001) | Not comparable to H3's 0.209 (that was the 320×240 arm). Frames checked: same 1280×720 as raw, GT aligned. Contradicts nothing: demo 04 is a dusk rain/fog clip (44 % / 21 %), demo 09 uses day raw and quotes H3 labelled engineering-only; docs/13 has no far-field degraded number. Cause (profile vs arm) unverified. |
| 8 | Latency | Labelled desktop only, shared GPU. **Unstable:** the audit re-run gave 15.5 / 16.9 / 55.4 ms vs 14.0 / 13.3 / 39.4; the D4 ratio (≥ 2×) holds in both. |
| 9 | FACTS / 32 sentences | Honest apart from the "1.8× upscale" wording and the missing usably-visible split; both fixed, numbers added to FACTS. |

## Honest interview sentence

"On customer-safe CC0 renders, YOLOv8n at its default 640 input finds almost none of the far-camera
people (2.5 %, and 6 % of those at least 20 px tall); a 1280 input finds about 40 % (49 % of the
≥ 20 px ones). The tiling I pre-registered downscaled its tiles and did worse than 1280, so the
earlier '63 % with small tiles' is still a MetaHuman engineering number, and on the degraded CCTV
stream every arm is near zero."

Retired: R72. Ledger: Z13. Still unverified: H3's 320×240 arm on CC0; why the degraded stream is ≈ 0.
