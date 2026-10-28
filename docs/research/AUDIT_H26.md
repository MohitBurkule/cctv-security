# AUDIT_H26 · Dose curve at fixed optimiser steps (32 §H26)

Audited 2026-09-27 against `1cc0b93` (pre-registration) and `dbd21c4` (results). Method as
AUDIT_H25: every number in 32's H26 sections recomputed in Python from
`out/experiments/h26_dose_fixedstep/results.json` (`arms[*].dataset`, `arms[*].gpu_wait`,
`arms[*].train_opts`, `curve`, `contrasts`, `seed_summary`); the exact permutation test
re-enumerated (252 splits); the padding checked against `pad_train_list` in
`survsim/experiments/detection.py` and the 25 `work/dose*/yolo_data/images/train` lists;
`schedule` in `survsim/experiments/dose_fixedstep.py`; the h14b/H25/H15 baselines against their
own results.json.

## 1. Recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| 25 runs, 5 doses × 5 seeds | 25 arms | match |
| pool 2,176 candidate frames | `synthetic_candidates` = 2,176 in every synthetic arm | match |
| 450 steps = 6 × 75 (600 / 8) | L × E = 3,600 for all 25 arms: 300×12, 400×9, 600×6, 900×4, 1,800×2 | match; **imprecise**: ultralytics rounds the last partial batch up, so realised iterations are 456 (dose0, 38×12), 452 (600, 113×4), 450 otherwise → added |
| 1,000 arm = 1,300 + 500 duplicates × 2 epochs | `train_images` 1,800, `padded` 500, epochs 2, on all 5 seeds | match |
| warm-up 225 iterations | `warmup_epochs` 6.0 / 4.5 / 3.0 / 2.0 / 1.0 = 225 × 8 / L | match |
| per-arm means and bootstrap CIs (table) | all 5 means and 10 CI bounds equal to 4 d.p. | match |
| per-seed APs | identical | match |
| contrasts +0.0041 / +0.0045 / +0.0015 / −0.0003 | same | match |
| perm p 0.048 / 0.040 / 0.468 / 0.952 | exact enumeration 12/252, 10/252, 118/252, 240/252 | match |
| Holm first-step threshold 0.0125, none rejects | 0.05 / 4 = 0.0125 > 0.040 smallest p | match |
| bootstrap CIs of 100/300 exclude 0 | [+0.0012, +0.0071], [+0.0015, +0.0074] | match (independent re-draw ±0.0001) |
| 1,000 arm "noisiest (sd 0.0067 vs ~0.003)" | 0.0067 vs 0.0025–0.0033 | match, range stated |
| perm-p floor 0.008 | two-sided 2/252 = 0.0079 | match |
| wall 9,292 s | 9,292.1 | match |
| "several arms waited up to the 600 s cap (e.g. dose1000_s1 at 2,255 MiB)" | three arms waited: dose1000_s1 600 s, dose0_s2 600 s, dose100_s2 480 s; 22 ≤ 1 s | **vague** → listed |
| real share at 1,000 = 23 % | 300 / 1,300 = 23.1 %; pads held 108/115/112/114/119 real images (expected 115.4) | match |
| "each real frame seen ~2x instead of ~12x" | each real *list image* ~2.8× vs 12×; each unique MOT20-01 frame ~14× vs 60× | **imprecise** → both stated |
| "1,000 arm images seen 1-2x unevenly" | 800 images 2×, 500 duplicated images 4× | **wrong** → corrected |
| real-only 0.4911 is +0.0054 above h14b/H25 0.4857 | 0.4857 is h14b **seed 0** (H25 3-seed mean 0.4859; h14b 5-seed 0.4862); seed-paired vs h14b: +0.0049 [+0.0031, +0.0068], every seed positive (+0.0022 … +0.0078) | **imprecise** → paired figure added |
| "about 60 % of the h14b dose gain was more steps" | the real-only rise explains 0.0049 / 0.0121 ≈ 40 % at 100 frames; the equal-step gain is 34 % (100) / 47 % (300) of h14b's | **overclaim of precision** → rewritten as "a third to a half survives"; decomposition stated as not clean |
| "overstate the synthetic effect by that much" for H7, H14b, H15, H25 | H15's primary (vis vs amodal) and H25's (noise vs clean) are within-dose, equal-list contrasts, unaffected; H16 was omitted | **overclaim** → scoped |

## 2. Specific checks the brief asked for

* **Seeded-duplicate padding does not bias the 1,000 arm.** `pad_train_list` draws 500 indices
  without replacement from the arm's own 1,300-image list with `default_rng([seed, 26])`. Real
  images among the pads: 108–119 per seed vs 115.4 expected (hypergeometric sd ≈ 7.4). The mix
  proportion is preserved; what padding does change is that 500 images are presented 4× and 800
  2× — a within-arm non-uniformity stated in 32, not a mix bias.
* **Is 0.4857 the same checkpoint recipe?** No, and the pre-registration said so ("the 0 arm now
  trains 12 epochs so it is not the h14b 0.4857 baseline"). h14b and H25 real-only: 6 epochs,
  ultralytics default warm-up (3 epochs ≈ 114 iterations), `close_mosaic` default (10 ≥ epochs,
  so mosaic on throughout — same as H26's explicit 0). H26 dose0: 12 epochs, warm-up 225
  iterations. H26's pool is batch_v8 (9 sets, the H15/H25 spec); h14b's mix arms used batch_v7.
  H1's 12-epoch real-only (0.491 ± 0.003, 60 item 10) independently agrees with 0.4911.
* **GPU-wait deviations disclosed?** Wall-time overrun was; the individual waits were only
  gestured at → now listed. Waits happen before training and cannot change a checkpoint (the
  training is `deterministic=True` with fixed seeds), so they are a cost deviation, not a
  validity one.

## 3. Not reconciled

1. **H26 dose100 (0.4952, 450 steps) is below h14b mix_100 (0.4983, 300 steps)** and below H25's
   clean v8 cell (0.4986, 300 steps). More steps did not raise the 100-frame arm; pool (v7 vs v8),
   warm-up and seed draw all differ. So "the +0.0121 shrank because real-only rose" explains only
   ~40 % of the drop.
2. **H15 v8_vis_300 scored 0.4981** on nominally the same recipe as H26 dose300 (0.4956): batch_v8,
   6 epochs × 75 = 450 iterations, 225-iteration warm-up. Seeds (7 vs 5) and subset draws differ;
   n is too small to call it noise or not. Added to 32 as unreconciled; H51 (66) is designed to
   settle both.
3. At 300 frames the studies agree (h14b mix_300 0.4957 vs H26 dose300 0.4956, both 450 steps),
   which supports the step explanation there.

## 4. Propagation (R51)

Headline everywhere: **"+0.004–0.005 AP at equal steps (100–300 frames), not significant after
Holm; the earlier +0.0121 [0.0111, 0.0130] compared unequal steps."** RETIRED_CLAIMS R51 flags
+0.0121 / +0.012 / +0.0107 on any line without the equal-step value or a retirement marker.
Docs that carried the unequal-step number as the current dose gain and were fixed: FACTS (H14,
h14b, H25 rows caveated; H26 row added), 00, 23, 42, 52 (register row + §5/§6/pitch), 57, 60
(item 9 / story 3 / not-to-say / pitch / item 37), 61, 63, 64 (abstract, §4.1 H26 paragraph,
register, §5 table, §8 claim (a)), 65, 66 (H26 done; H51, H52 added), 67, 68, 74, 77, 78
(opener + 90-day plan), 79, 80 (figure 2 text; `figures/pack/02_sim_to_real.png` and
`pack.pdf` regenerated with the H26 curve and h14b/H7 greyed as unequal-step). **19 docs** carried the unequal-step number as the current gain (32 itself keeps it as the historical h14b result).
Unchanged by design: H1 (synthetic-only 0.276 → 0.152) and H19 (far: real frames fix it).
H16's YOLO26n +0.0092 / +0.0169 and H17's HOTA +0.0103 inherit the same unequal-step confound;
they are caveated where they sit beside the headline but not re-registered in R51.

## 5. Score

21 checkable claims (§1): 14 match, 4 imprecise or vague (iteration rounding, waits, real-frame
exposure, 0.4857 vs the paired baseline), 1 wrong (pads "1-2×"), 2 overclaims ("60 %"
decomposition; which earlier studies are confounded).
**Score 14 / 21 (67 %).** The numbers are right and the headline conclusion (no Holm-significant
dose; the fade is not the step confound; much of h14b's gain was steps) stands; the prose around
the step decomposition was more precise than the data allows, and two cross-study gaps remain
open (§3).
