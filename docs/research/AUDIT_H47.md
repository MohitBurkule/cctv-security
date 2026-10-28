# AUDIT_H47 · Evasion techniques vs zero-shot person recall

Audited 2026-09-27 against `out/experiments/h47_evasion/{results.json,det_cache/,sets/*/check_render.txt,sets/*/render_result.json}`,
`survsim/experiments/evasion.py`, config `survsim/experiments/configs/h47_evasion.yaml`, pre-registration `f4a1cdf`
(32 §H47), results `6d7f5f1`, `tools/render_run.py` (`SURVSIM_OUTFIT_OVERRIDE`). No GPU, no editor, nothing
re-rendered; the clip-cluster statistic was recomputed from the cached per-frame detections plus mask GT
(6 s CPU).

**Score: 80 → 100** (every point estimate matched; the headline CI and its p-value were frame-level and are
now replaced by a clip-cluster CI; one false "agree on every sign"; a wrong VRAM peak; "halves exposure" in 66;
hood colour proxy and untested techniques made explicit wherever quoted).

## 1. Numbers recomputed

| claim | recomputed | ok |
|---|---|---|
| control R 0.948 (YOLO26n) | 0.9480 pooled over seeds 1–3; matched seeds 1–2 control 0.9470 | ✓ (label clarified) |
| crowd −0.201 [−0.210, −0.192], Holm p 0.003; v8n −0.166 | −0.2010 [−0.2103, −0.1917], p_Holm 0.0030; v8n −0.1664 | ✓ numbers; **CI/p are frame-level** (§2) |
| wall −0.054 [−0.066, −0.042]; 43 % fewer ≥ 20 px person-frames | −0.0540; 3,262 vs 5,736 (control s1–2) = 0.569 → −43.1 % | ✓ |
| dark / hi-vis / hood ≈ 0 | +0.0027 / +0.0013 / −0.0012 (26n) | ✓ |
| slow +0.036 | +0.0356 | ✓ |
| 1/6 ≥ 0.10 → not met | `verdict.counted` = [crowd_cover], need 3, met false (both models) | ✓ |
| 17/17 gate-passed sets 22/22 | 17 `check_render.txt` with "PASS: 0 failed of 22 checks" | ✓ |
| seeds: dark/hivis 1–3, others 1–2; hood_up s3 truncated | hood_up s3 "render aborted by root disk full (245/300 cam_01 frames)"; slow/crowd/wall s3 have **no set** (never rendered — results.json lists them `false`, which reads like a gate failure) | ✓ (wording added) |
| crowd per-clip recall 0.69–0.80 | 0.691 / 0.712 / 0.786 / 0.795 | ✓ |
| 10,186 PNGs deleted | 17 sets × 600 = 10,200 − 14 kept (frame 0120 × 2 cams × 7 seed-1 sets); 14 PNGs remain on disk | ✓ |
| editor VRAM peak 5.18 GB | max `vram_peak_mb` = **5,593** (hivis s3); 5,176 is dark_lowcontrast s2 | ✗ corrected |
| "Both detectors agree on every sign" | dark 26n +0.003 vs v8n −0.001 | ✗ corrected (agree on every effect whose CI excludes 0) |

## 2. The CI: frame-level → clip-cluster

`bootstrap_delta` resamples **frames** within each (seed, camera) stratum. Frames of a 30 s, 10 fps clip are
strongly autocorrelated, so this CI is too narrow. Recomputed from `det_cache/` + `sets/*/gt/mot_<cam>.txt`
with the runner's own `frame_hits` (identical per-clip counts to results.json), resampling the matched
(seed × camera) **clips** with replacement, paired, exhaustively (4⁴ or 6⁶ resamples), pooled recall per resample:

| technique | clips | Δ 26n [clip-cluster 95 %] | per-clip Δ | Δ v8n [clip-cluster] | frame-level (pre-reg.) |
|---|---|---|---|---|---|
| dark_lowcontrast | 6 | +0.003 [−0.001, +0.006] | −0.004..+0.008 | −0.001 [−0.006, +0.003] | [−0.004, +0.010] |
| hivis | 6 | +0.001 [−0.000, +0.003] | −0.001..+0.005 | +0.001 [−0.001, +0.002] | [−0.005, +0.008] |
| hood_up (colour proxy) | 4 | −0.001 [−0.003, +0.000] | −0.003..+0.002 | −0.001 [−0.003, +0.001] | [−0.010, +0.007] |
| slow_deliberate | 4 | +0.036 [+0.015, +0.061] | +0.013..+0.067 | +0.031 [+0.015, +0.050] | [+0.028, +0.043] |
| **crowd_cover** | 4 | **−0.201 [−0.254, −0.154]** | −0.281..−0.136 | −0.166 [−0.209, −0.129] | [−0.210, −0.192] |
| wall_hugging | 4 | −0.054 [−0.074, −0.033] | −0.072..−0.024 | −0.047 [−0.068, −0.025] | [−0.066, −0.042] |

* Path techniques: the clip CI is ~2–5× wider than the frame CI. Appearance techniques re-render the *same*
  trajectories, so their clip deltas are truly paired and come out tighter.
* **Significance.** With 4 clips the smallest one-sided p any clip-level test can give is 1/16 = 0.0625
  (all four negative under sign-flip). The pre-registered "Holm p < 0.05" was therefore only reachable at
  frame level; the p 0.003 must not be quoted as the significance. crowd_cover is ≤ −0.136 in every clip
  (beyond the −0.10 bar everywhere), so the direction and size are not in doubt; the verdict is NOT MET either way.
* 4 clusters is small: treat the clip CI as a scale, not a precise interval. H55 (66) asks for ≥ 10 clips.

## 3. Design checks

* **Hood is a colour proxy.** `OUTFIT_OVERRIDES["hood_up"]` = `face_cover {kind: hood, rgb (0.03, 0.03, 0.035)}` +
  dark hair; `survsim/export/outfits.py` paints the headwear colour over hair and head skin. No hood geometry.
  The result is "a dark head colour does nothing"; now stated in 32, 50, 52, 64, FACTS, 48, 65 v2, 79.
* **Untested ≠ no effect.** Umbrella, carried object, crouch/crawl, face_away were excluded at registration
  ([X] capability: no CC0 asset/clip). 50 §Measured listed them as "not tested"; now "untested, not 'no
  effect'" everywhere H47 is quoted, and they are H55's arms.
* **Matched control.** `cmd_score` computes Δ on `set(arms[t]) & set(ctrl)`, so seed-1–2 techniques are
  compared with the control's seeds 1–2 ✓; only the displayed "control 0.948" is 3-seed (0.947 matched).
* **Appearance arms share GT**: `run_of()` maps them to the control run; the override hook in `render_run.py`
  merges `ov["all"]` into each person's outfit ✓.
* **Runner registration.** `evasion` was missing from `RUNNERS`, so `test_all_configs_load_and_name_a_runner`
  failed; registered (the module is a staged CLI, not a `run()` runner — `survsim experiment h47_evasion`
  would still fail; use `python -m survsim.experiments.evasion`).

## 4. Corrections (Edit in place)

| # | where | was | now | class |
|---|---|---|---|---|
| 1 | 32 results table, FACTS, 50, 66, 52, 64, 60, 65 v2, 79, 48, 74 | crowd −0.201 [−0.210, −0.192] as headline | [−0.254, −0.154] clip-cluster; frame CI kept as a labelled column in 32 | headline |
| 2 | 32, 66, FACTS, 48, 65 v2, 79 | Holm p 0.003 as the significance | frame-level only; 4 clips cannot go below p 1/16 | headline |
| 3 | 32 verdict | "agree on every sign" | on every effect whose CI excludes 0 | supporting |
| 4 | 32 gate | VRAM peak 5.18 GB | 5,593 MB (hivis s3) | supporting |
| 5 | 66 | "halves exposure" | −43 % | supporting |
| 6 | 50, 52, 64, FACTS, 48, 66 | hood / "not tested" | hood colour proxy; untested ≠ no effect | supporting |
| 7 | 32 | "gate false" for unrendered s3 sets; control 0.948 unlabeled | never rendered; 0.947 matched | cosmetic |
| 8 | 48 C6 | "40-technique taxonomy" | 52 | cosmetic |

## 5. Fold-in

`survsim/experiments/__init__.py` RUNNERS += evasion; FACTS H47 row (CI type tagged) + audit row; 52/64 register
rows; 52 §5b and 64 §4 intro (H47 now has a number) + 64 evasion paragraph; 60 item 11; 48 C6 new Q ("how would an
intruder beat your detector?"); 65 v2 §2 item 4; 79 Q answer + red flags; 50 §Measured; 74 drill 1 evasion row;
66 H47 → done, result line moved under its entry, new H55; 77 note under weak answer #1; 00 index.
