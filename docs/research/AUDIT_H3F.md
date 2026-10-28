# AUDIT_H3F — adversarial audit of H3f (degrade-stage ablation, far field)

Scope: 32 §H3f (pre-registration bf17f1a, partial bcc90dd, results d06863f), `survsim/experiments/degrade_ablation_far.py`,
`configs/h3f_degrade_ablation.yaml`, `out/experiments/h3f/results.json`, figure, FACTS rows. CPU only, from cached detections.

| # | Check | Verdict |
|---|---|---|
| 1 | Order / freeze | Clean: registration committed before any detection; runner defaults reproduce the registered design. |
| 2 | Post-hoc `frames_every: 2`, `groups_subset` | Disclosed. Ablated-variant detections exist **only for the scored half** (25 frames/camera; `full` and `loo_optics` cam_02 have all 50), so the LOO/AOI shares cannot be recomputed on the registered 100 frames. Label: **half the registered frames**. |
| 3 | Does halving move the CIs? | Checked where possible (raw and shipped = full, H3d cache, all 100 frames, tiles (d)): scored half raw 0.924 / full 0.324 / loss 0.600 [0.474, 0.771]; unscored half 0.860 / 0.293 / 0.567 [0.451, 0.706]; registered 100: 0.892 [0.838, 0.946] / 0.309 [0.219, 0.393] / 0.583 [0.487, 0.688]. The denominator is stable (Δ 0.017); CIs narrow by ~√2 with 20 blocks. Shares on 10 blocks are wide: noise LOO [0.423, 0.804] straddles the 0.60 bar. |
| 4 | LOO 0.621 vs AOI 0.299 for noise | "Noise is what erases far people" is **not** honest on the registered arm. Noise is the largest necessary lever, not sufficient; the loss is noise interacting with optics blur and codec (the registration itself says disagreement = interaction). Corrected in 32; R75. On full_1280 noise meets both (0.663 / 0.954) — secondary arm. |
| 5 | Decision scoring | Correct: primary arm is `tiles_d` (config `decision.primary_arm`), culprit noise LOO 0.621 ≥ 0.60 but AOI 0.299 < 0.60 → NOT met. The 1280 pass cannot substitute. |
| 6 | "Resample 0" | Labelled "by construction" (1280 source, resize is identity) in both registration and results; it is untested, not measured zero. |
| 7 | Near HN fail reach | Full-profile near ≥ 80 px drop 0.210 at 1280: the profile is harsher than real CCTV implies. Qualifier "profile noise uncalibrated, lower bound" added to FACTS rows H3b, AUDIT_H3D (degraded far 0.295) and H32b; 65 §0 item 21 gets one line. H32 night profiles are a different profile, not ablated — qualifier is precautionary. Demo segment 04 rain/fog captions: not in FACTS; demo files are out of scope for this audit — owner should add "lower bound" if they quote recall. Nothing retired beyond R75. |
| 8 | Minor | H3d's 0.295 degraded far and this 100-frame 0.309 differ because H3d scored a different frame set; not a contradiction. |

**Honest sentence.** "Sensor noise is the largest single lever — take it out and far recall recovers most — but on its own it explains only about 0.3 of the loss on the registered arm, measured on half the registered frames; far people are lost to noise interacting with blur and the codec, and every degraded-stream number is a lower bound until the profile's noise is recalibrated."

Recompute script: scratch (raw/shipped from `out/experiments/h3d/dets`, same `base.frame_counts`, `make_blocks(…, 5)`, 1000 bootstrap, seed 0).
