# AUDIT_H61 — is H52 (c)'s masked-background gain real background, or a box-shaped inpainting artefact?

Recomputes 32 §H61 (`out/experiments/h61_silhouette_mask/results.json`) against its own numbers,
against the pre-registration in 32/66, and against the sibling H51/H52 arms it reuses.

## 1. Numbers reproduce

`seed_summary` / `groups` (10 seeds each, MOT20-02 AP@640):

| arm | AP mean | seed-bootstrap 95 % |
|---|---|---|
| dose0 (real-only, reused from H51) | 0.4911 | [0.4895, 0.4927] |
| dose300 (a, +300 v8 true labels, reused from H51) | 0.4962 | [0.4947, 0.4978] |
| sil300 (c′, +300 v8 silhouette-masked, no inpainting, no boxes) | **0.4891** | [0.4873, 0.4909] |
| mask300 (c, H52's box-inpainted arm, context only) | 0.4947 | [0.4929, 0.4964] |

`paired` (sign-flip, exact 2¹⁰; seed-bootstrap CI; Holm over the 2 primary contrasts):

| contrast | AP diff | 95 % CI | sign-flip p | Holm p |
|---|---|---|---|---|
| (a) − (c′) | **+0.0071** | [+0.0058, +0.0084] | 0.0020 | **0.0039** |
| (c′) − real | −0.0020 | [−0.0041, −0.0002] | 0.0742 | 0.0742 |

Both match the numbers given in the audit brief and in 32 §H61 exactly. Not-in-the-family context
contrast, same 10 seeds, same 300-frame selection: (c) − (c′) = **+0.0056** [+0.0048, +0.0065]
(seed-bootstrap, not Holm-adjusted) — also matches.

10/10 seeds give a positive (a) − (c′) diff (`contrasts.paired[0].AP.diffs`, all 10 values > 0:
0.0090, 0.0063, 0.0049, 0.0113, 0.0089, 0.0061, 0.0051, 0.0078, 0.0073, 0.0039) — confirmed against
the raw per-seed arrays, not just the summary. (c′) − real is mixed sign (7 negative, 3 non-negative
of the 10 diffs in `contrasts.primary[1].a`/`b`), consistent with the wide, zero-crossing CI and the
n.s. Holm p.

## 2. Recipe and reuse checks

- `config.fixed_steps` = 450 presentations, 225 warm-up iters, batch 8 — matches H51/H52's recipe
  exactly, as claimed.
- `config.reuse_from` lists `h51_equal_steps` and `h52_ablation`; the arm JSONs for dose0/dose300 in
  `results.json.arms` carry `train_cost.seconds` and `dataset` blocks byte-identical to their H51
  originals (checked: same `train_images: 600`, same per-source counts, same seeds 0–9) — dose0 and
  dose300 were reused, not retrained, as stated.
- `dataset.synthetic_mode: "silhouette"` on every sil300 arm, `by_source` shows `real: 300` (the true
  300 v8 synthetic frames, byte-identical selection to H52's mask300 per the pre-registration) plus
  the same 60 real MOT20-01 frames ×5 as dose0/dose300.

## 3. Silhouette-mask mechanism check

`survsim/experiments/dose_fixedstep.py` (`mask_people_silhouette`, `apply_synthetic_mode`,
`SYNTHETIC_MODES`) and `survsim/gt/mask_boxes.py` (`decode_ids`) were read (not modified — out of
scope) to confirm the mechanism claimed in 32 §H61's pre-registration:

- `"silhouette"` mode decodes the per-camera ID-mask PNG with `decode_ids`, nearest-resizes it to the
  frame's resolution, and zeroes exactly the pixels whose decoded id matches a removed person — a
  per-pixel mask from the renderer's own ground truth, not a box. This is the same mask source
  `survsim/gt/writers.py`'s occlusion-aware boxes are read from (CLAUDE.md principle 1: "read boxes
  from rendered masks"), reused here to *remove* pixels rather than to derive a box.
- The fill colour is computed per-frame as the median RGB of the frame's own non-person pixels (its
  background), not a constant, not a per-box fill, and not inpainted — there is no Telea/other
  inpainting call in the silhouette path, unlike H52's `mask300`/`(c)` arm, whose masks are call sites
  for `cv2.inpaint` on dilated (+10 %/side) rectangles at 1/4 resolution (confirmed by reading
  H52's masking code referenced from AUDIT_H52).
- No box shape appears anywhere in the sil300 pixel-removal path — the removed region's outline is
  the person's true silhouette, which is the entire point of the contrast against H52's rectangle.

This matches the pre-registration's description of (c′) in 32 §H61 line-for-line: "every person pixel
removed by its rendered silhouette mask ... filled with the frame's own background median colour (no
inpainting, no box shape) — no labels."

## 4. Pre-registered rule applied correctly

Rule as registered: `background-real` iff (c′) − real ≥ +0.003 with CI excluding 0 and Holm p < 0.05;
`box-fill-artefact` iff (c′) ≈ real. Observed (c′) − real = **−0.0020** [−0.0041, −0.0002], Holm p
0.074 — CI excludes 0 but on the *wrong* side (negative, not the required ≥ +0.003), and Holm p is
n.s. Neither half of `background-real`'s conjunction holds, so the rule correctly selects
`box-fill-artefact`. `labels-on-people` (a − c′ ≥ +0.003, Holm p < 0.05) also holds: +0.0071, Holm
p 0.0039. Both verdicts in 32 §H61's prose are the outputs the pre-registered rule actually produces
on these numbers, not a post-hoc reading.

The pre-registration's own prediction ("paired sd of (a) − (c) in H52 ≈ 0.0022, so +0.003 at 10 seeds
is marginal") is reported as wrong in 32 §H61's own text, and correctly so: the observed effect
(+0.0071 on a−c′) cleared Holm at p 0.0039, not marginally — the prediction undersold the power, and
32 §H61 says exactly that rather than retrofitting the prediction to look right.

## 5. What stands

H52 (c)'s +0.0036 "masked-background" gain over real-only was the box-shaped, dilated, Telea-inpainted
fill pattern — a detector-learnable artefact, not real background/negative content. With the true
silhouette and a flat median fill in place of the inpainted rectangle, the gain over real-only
disappears (and trends slightly negative, n.s.). The entire H51/H52 +300-frame gain is
labels-on-people. The (c'') ignore-region arm (excluding masked pixels from the loss rather than
filling them) was pre-registered as a fourth arm and dropped from this run's scope — it remains an
open, cleaner test of "negatives from the rest of the frame" that H61 did not run.

Caveats carried forward unchanged from 32 §H61: one site, one detector, 60 real frames, 10 seeds.

## 6. Score

**9/10.** Every number in the results file reproduces exactly against the claims in 32 §H61 and
against the audit brief's own numbers; the mechanism (silhouette mask source, median fill, no
inpainting, no box) was verified against the actual code paths, not just the prose description; the
reuse of dose0/dose300 from H51 was checked, not assumed; the rule was applied as registered and its
failed prediction reported honestly. Deduction: the (c'') ignore-region arm was pre-registered as part
of this hypothesis's arm list and never run (correctly disclosed as dropped, but still an open thread
this audit did not close).
