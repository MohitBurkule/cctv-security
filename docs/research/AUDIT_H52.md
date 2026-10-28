# AUDIT_H52 · Label vs image vs diversity ablation, 10 paired seeds (32 §H52)

Audited 2026-09-27 against `6a52327`/`8dfebb9` (pre-registration) and `f7f1d3f` (results). Method as
AUDIT_H51: every number in 32's H52 results section recomputed in Python from
`out/experiments/h52_ablation/results.json` (`groups`, `paired`, `contrasts`, `h52_decision`, `arms[*].dataset`,
`arms[*].train_cost`); the exact sign-flip test re-enumerated over all 2^10 sign vectors for the
unregistered a − c contrast; the 20 reused arms compared byte-for-byte with `out/experiments/h51_equal_steps/arms`;
`driver.log` and `logs/*_s0.log` read for the FAIL lines; `survsim/experiments/dose_fixedstep.py`
(`shuffle_labels`, `mask_people`, `apply_synthetic_mode`) read for the arm construction. No GPU, no re-training.

## 1. Recomputed

| claim in 32 §H52 | recomputed | result |
|---|---|---|
| real-only 0.4911 [0.4895, 0.4927] | `groups.dose0` | match |
| (a) 0.4962 [0.4947, 0.4978] | `groups.dose300` | match |
| (b) shuffled 0.4885 [0.4864, 0.4904] | `groups.shuf300` | match |
| (c) masked 0.4947 [0.4929, 0.4964] | `groups.mask300` | match |
| (d) real ×10 0.4900 [0.4882, 0.4917] | `groups.dup` | match |
| (a) − (b) +0.0077 [+0.0062, +0.0093], p 0.0020, Holm 0.0098 | 0.00195 → ×5 = 0.00975; 10/10 seeds positive | match |
| (b) − real −0.0026 [−0.0050, −0.0004], p 0.064, Holm 0.129 | 0.06445 → 0.1289 | match |
| (c) − real +0.0036 [+0.0014, +0.0056], p 0.0156, Holm 0.047 | 0.01562 × 3 = 0.04686; 8/10 seeds positive | match |
| (d) − real −0.0011, p 0.455, Holm 0.455 | same | match |
| (a) − (d) +0.0062 [+0.0042, +0.0082], Holm 0.0098 | same | match |
| verdict label-driven | `h52_decision`: label-driven true, image-level false, diversity-only false; rule applied by hand gives the same | match |
| "~70 % of the gain" | 0.0036 / 0.0051 = 0.71 | match |
| (a) − (c) +0.0015 "below the noise floor" | +0.0015, unadjusted sign-flip p 0.057 (1 024 vectors); not in the family | **incomplete** → labelled exploratory with its p |
| dose0/dose300 copied from H51, not retrained | 20/20 arm JSONs byte-identical; no `work/dose*` directories | match |
| "~2-3.5 min each" | `driver.log` gaps 1.7–6.6 min per arm; `train_cost` 49–159 s, 0.78 h summed | **imprecise** → both stated |
| "Wrong boxes … fall below real-only" | −0.0026, Holm 0.13 | **overclaim** → "nominally below, not significant" |
| "Duplicating real frames does nothing" | −0.0011, p 0.46; (d) uses the same 60 unique images as real-only at the same steps | match, but it is a list-construction control, not a diversity test → stated |
| "The first three arms logged FAIL on post-aggregation" | `KeyError: 'secondary_contrasts'` in shuf300_s0 / mask300_s0 / dup_s0 logs; arm evals present | match; cause now named |
| "true-label gain has two parts" | interpretation, not a registered contrast | **overclaim** → tagged [INF] |

## 2. Arm construction

* **(b) shuffled:** a seeded derangement (no image keeps its own labels) over the same 300 images, boxes
  rescaled between 1920×1080 and 1280×720. Pixels are real and real people are left unlabelled, so (b)
  both adds positives on background and teaches the people as negatives. The contrast (a) − (b) measures
  "correct boxes vs actively wrong boxes", which is stronger than "boxes vs no boxes".
* **(c) masked:** every GT box grown 10 % per side, Telea-inpainted at 1/4 resolution, upsampled
  bilinearly and pasted back; no labels. **Caveat:** this leaves smooth, blurred, box-shaped patches
  where every person stood. A detector can learn "blurred rectangle = background", which is a cue real
  MOT20 never shows, and the rectangles delete the true background inside each box. Only labelled
  people are removed; anyone below the GT visibility threshold stays in the image unlabelled. So (c)'s
  +0.0036 is "person-free-ish scenes with artefacts as negatives", not clean background. Stated in 32
  and FACTS; H61 registered in 66 to test silhouette masks without inpainting.
* **(d) dup:** 60 real ×10, 6 epochs — the same unique images and step count as real-only (60 ×5,
  12 epochs). It controls list construction/epoch count, not diversity; its null says nothing about
  what *different* real frames would buy.

## 3. What stands

The pre-registered rule selects **label-driven**, and the numbers are exact. At H51's recipe, putting the
same 300 synthetic images in with deranged boxes erases the gain (+0.0077 in favour of true boxes,
10/10 seeds). Person-removed scenes without boxes keep about 70 % of the gain (Holm 0.047, just under),
so correct negatives/background contribute, with the inpainting caveat. The split between "labels on
people" and "the rest of the frame is correctly negative" is not resolved (a − c exploratory). One real
site, one nano detector, 60 real frames.

## 4. Propagation

One sentence folded into the sim-to-real story in the same places as H51: 52 §5b, 60 #9, 64 §4, 78,
68 Q18, 79 Q26, 46 #24, 77 #2, 80 fig 2, 65 v2 [9], 82, 42, 23; FACTS H52 row qualified plus an audit
row; 66 H52 closed and H61 added. 13 already carried the H52 row.

## 5. Score

**8/10.** Every number reproduces, the rule was applied as registered, the reused arms really are
reused, and the failed prediction was reported as wrong. Deductions: (c)'s masking is a box inpaint with a
learnable artefact that was noted only as "not silhouettes"; the results over-read (b) − real and the
two-part decomposition; wall time was misstated.
