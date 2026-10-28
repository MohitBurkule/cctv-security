# AUDIT_H3E — adversarial audit of H3e (H3d's tile-merge rule on MOT20)

Scope: 32 §H3e (pre-registration 4d91a0c, results d8db7ae), `survsim/experiments/tile_merge_real.py`,
`survsim/experiments/configs/h3e_tile_merge_real.yaml`, `tests/test_tile_merge_real.py`,
`out/experiments/h3e/results.json`, `figures/h3e_tile_merge_real.png`, the FACTS H3e row.
All recomputation is CPU-only from the cached detections in `out/experiments/h3e/dets`, re-using the
runner's `items_of`, `cache_dets` (cache hit, no detector run), `merge`, `frame_counts`.
MOT20 is non-commercial: measurement only.

## Verdicts

| # | Question | Verdict |
|---|---|---|
| 1 | Order and freezing | **Clean.** 4d91a0c (pre-registration) precedes d8db7ae (results) in `git log`; the runner, config and test are touched only by 4d91a0c and are unmodified in the working tree. d8db7ae adds only 32 text, the FACTS row, the figure and `out/experiments/h3e/*`. |
| 2 | "10 blocks registered, 12 actual" | **No CI changes.** The block count is not a parameter: the frozen config sets `block: 30` (sampled frames) and `make_blocks` splits each sequence's 100 frames into 30/30/30/10, giving 12. The "10" was prose arithmetic in the registration; every CI in results.json is what the frozen code computes. Minor note: the 10-frame tail blocks make blocks unequal in size (unweighted resampling of unequal blocks), which the H3b–H3d runs share. |
| 3 | 0.383 TP-deletion follow-up | **Honestly labelled** ("Post-hoc diagnostic (not registered)") in 32. **Reproduced exactly**: 7,122 / 18,598 (greedy conf-ordered IoU ≥ 0.5 match of (a)'s conf ≥ 0.25 boxes; ignore regions not applied). The FACTS row said "Post-hoc:" — kept, it is labelled. |
| 4 | "sparse scenes only" supported? | **Not by MOT20, and not as a density rule.** See §Density. The recall cost appears at every density measured, including the sparsest quartile (−0.079 at ~41 people per frame, four times the 0.02 allowance). Between sequences the cost grows with density (Spearman −0.48 per frame), but within each sequence it is flat (within-sequence quartiles −0.117 / −0.119 / −0.125 / −0.113), and MOT20-03 (82 people/frame, −0.037) costs less than MOT20-02 (42/frame, −0.072). The gradient is a scene effect confounded with density. The only evidence that (d) costs no recall is the CC0 renders; the threshold for a density gate is **unmeasured**. Text corrected: "render-validated; on every real MOT20 density tested (≥ ~40 people/frame) it deletes people; a density gate is a hypothesis with no measured threshold". |
| 5 | MOT20-01 excluded (leakage)? | **Yes.** The config lists only MOT20-02/03/05; `items_of` iterates only `cfg["sequences"]`; results.json `frames_per_seq` has 100 each for those three. |
| 6 | "Neither tile arm beats full_1280 on AP50" vs H71/H3c | **Consistent but needed scoping.** True on MOT20 (0.449 / 0.572 vs 0.684). On the renders tile arms do beat 1280 (H3c far AP50 0.741 vs 0.497; H3d (d) near AP50 0.973 vs 0.944), and H3b's "tiling does not beat 1280" was about its 0.91× arm. H71 makes no tiling statement. Scoped to "on MOT20" in the appended 32 note. |
| 7 | FACTS / 32 sentences honest? | Numbers all correct (table rows, FP cut 0.802, Δ −0.118, HN −0.104 match results.json). Two wording fixes: the FACTS row said "HN passes" with no qualifier, and both said "(d) holds for sparse far scenes only", which MOT20 does not show (item 4). |
| 8 | Hard negative "passes for the wrong reason" labelled? | **In 32 yes** ("but for the bad reason above"); **in FACTS no** — fixed: the HN passes because (d) deletes real near people, not because tiling is correctly neutral on large people; (a)'s Δ +0.021 spans 0. |

## Density check (post-hoc, not registered)

Per-frame density = GT boxes ≥ 20 px. Recall at conf 0.25; CIs are i.i.d.-frame bootstraps (1000, seed 0),
narrower than a block bootstrap — diagnostic only.

| slice | frames | mean GT/frame | full_1280 | (a) | (d) | (d) − (a) [CI] | FP cut |
|---|---|---|---|---|---|---|---|
| MOT20-02 | 100 | 42 | 0.591 | 0.588 | 0.515 | −0.072 [−0.084, −0.061] | 0.840 |
| MOT20-03 | 100 | 82 | 0.685 | 0.668 | 0.631 | −0.037 [−0.042, −0.032] | 0.722 |
| MOT20-05 | 100 | 196 | 0.380 | 0.423 | 0.260 | −0.162 [−0.168, −0.157] | 0.818 |
| pooled Q1 (sparsest) | 71 | 41 | 0.613 | 0.606 | 0.528 | −0.079 [−0.093, −0.067] | 0.852 |
| pooled Q2 | 67 | 64 | 0.662 | 0.645 | 0.596 | −0.049 [−0.058, −0.041] | 0.779 |
| pooled Q3 | 79 | 106 | 0.562 | 0.570 | 0.491 | −0.080 [−0.096, −0.062] | 0.741 |
| pooled Q4 (densest) | 83 | 198 | 0.379 | 0.422 | 0.259 | −0.163 [−0.170, −0.157] | 0.821 |
| within-seq Q1..Q4 | 75 each | 101–115 | 0.48–0.50 | 0.48–0.53 | 0.37–0.41 | −0.117 / −0.119 / −0.125 / −0.113 | 0.79–0.81 |

Reading: the recall cost does **not** shrink toward zero as density falls; the sparsest real quartile
(~41 people/frame) still fails the registered 0.02 allowance fourfold. The densest quartile is worse
(−0.163), but that quartile is almost entirely MOT20-05. So the finding is "(d) fails on real crowds of
≥ ~40 people per frame; its only pass is on sparse CC0 renders" — a density gate is a plausible but
untested rule, not a measured one.

## Retired
R74: "the tile-border rule (d) costs no recall" stated without the render / sparse-scene scope.

## Honest far-field paragraph (used in 65 v2 §0 item 21, 103 §2, 105 Q27)
See 65 v2 §0 item 21, "Far-field (H3b–H3e audits)".
