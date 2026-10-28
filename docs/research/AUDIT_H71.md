# AUDIT_H71 — tracker-configuration transfer render → MOT20

*Adversarial audit, 2026-09-28. Inputs: 32 §H71 (pre-registration `fe97b09`, results `69cf497`),
`survsim/experiments/tracker_config_transfer.py`, `configs/h71_tracker_config_transfer.yaml`,
`out/experiments/h71/results.json` (no re-run: cached per-sequence HOTA only, no GPU/editor),
`docs/research/figures/h71_config_transfer.png`, FACTS H71 row. Recomputation: `analyse()` from the
module on the stored `hota_render` (12 × 24) and `hota_real` (4 × 24) arrays.*

## Verdicts

| # | Check | Verdict |
|---|---|---|
| 1 | Pre-registration before results | **PASS.** `fe97b09` (pre-reg) precedes `69cf497` (results); grid, bars and hard negative unchanged. |
| 2 | "D1 NOT met" | **Correct as scored; the reading "renders do not rank the configs the way MOT20 does" is an overclaim → INCONCLUSIVE.** The pre-registration itself said a CI including 0 is "not shown", not "does not transfer". |
| 3 | Is there a real ordering to transfer to? | **No.** MOT20 does not rank the 24 configs consistently with itself: pairwise per-sequence Spearman ρ −0.373 to +0.357; split-half ρ (2 vs 2 sequences) ≈ **+0.02** on average. The render set is moderately self-consistent (split-half median ρ **+0.34**, 95 % range −0.23 to +0.72, 12 sequences). A target that cannot rank itself cannot be matched; ρ ≈ 0 is the expected value under a flat real grid. |
| 4 | Real HOTA spread 0.0174 | **Supports "flat on real".** Per-sequence real ranges 0.018–0.054; config means span 0.0174 vs 0.0503 on renders. |
| 5 | Bootstrap over n = 4 real sequences | **Too weak for a negative.** Only 35 distinct real resamples; CI [−0.41, +0.46] cannot exclude a moderate ρ. Per-real-sequence ρ vs the render mean: MOT20-01 +0.19, -02 −0.318, -03 +0.325, -05 −0.129. |
| 6 | MOT20-01 excluded from real scoring? | **NO — contamination.** h14b `mix_300_s0` was trained on 60 MOT20-01 frames ×5 (32 §h14b). MOT20-01 is in `mot20_sequences` and in the mean. Without it (n = 3): ρ **−0.2222 [−0.4939, +0.3418]**, regret 0.0097, real range 0.0155 — conclusion unchanged (inconclusive), but per-knob readings change (row 7). |
| 7 | Per-knob "flip" claims | **Partly unsupported.** As reported (4 seqs) the real Δs for match_iou (+0.0024 [−0.0053, 0.0092]) and max_lost_s (−0.0005 [−0.007, 0.0044]) span 0: that is "no measurable effect on real", not a flip. Without contaminated MOT20-01: match_iou real Δ +[0.0012, 0.0119] (opposite sign to render, a small flip); max_lost_s real Δ +[0.0001, 0.0059], **same sign as render** (P same sign 0.998) — the "max_lost flips" claim is an artefact of including MOT20-01. Both 3-sequence CIs rest on 10 distinct resamples. |
| 8 | "Only w sign transfers" / H46b | **Survives in weakened form.** Real w Δ(8 − 0) +0.0060 [0.0018, 0.0136] excludes 0 (without MOT20-01: [0.0016, 0.0029]); preferred level render 8, real 2. On MOT20-02 alone the grid-averaged HOTA prefers w = 2 (0.5465 vs 0.5374 at w = 8). Reconciled with H46b (MOT20-02 argmax w = 8): H46b measured ΔAssA, over 5 checkpoints, at fixed other knobs, w up to 32; H71 is HOTA, one checkpoint, averaged over a 2×2×2 grid of the other knobs. Different metric and grid — not a contradiction, and neither is evidence about the level. |
| 9 | Render set size | **Text error.** 32/FACTS say "10 batch_v8 day sequences"; `render_seqs` lists **12** (4 runs × 2–4 cams). Fixed. |
| 10 | Stored-rounding | ρ from the 4-dp stored arrays is +0.035 vs reported +0.0096 (ties after rounding); immaterial. |
| 11 | Hard negative (`high`) | **Honestly reported** (failed as scored; both Δs span 0). |
| 12 | D2 "met but vacuous" | **Honest.** |

## Retired
- **R70** — "the renders do not rank the 24 configurations the way MOT20 does" / "does NOT transfer" read as a
  negative. Replacement: *inconclusive; MOT20 cannot rank the grid consistently with itself (split-half
  ρ ≈ +0.02), real spread 0.0174 HOTA.*
- **R71** — "match_iou and max_lost flip" / "the knobs that matter on renders flip or vanish". Replacement:
  *no measurable real effect with MOT20-01 in; without the detector's training sequence max_lost agrees in sign
  and match_iou reverses, on 3 sequences.*

"Tuning the whole tracker config on renders and checking it on MOT20 was inconclusive, not a failure: the 24
configs span only 0.0174 HOTA on MOT20 and the MOT20 sequences don't even rank them consistently with each
other, so there is no real ordering to match; what held is that adding appearance (w > 0) helps on both, and
any render-tuned setting still needs a real-footage check." (AUDIT_H71, R70/R71)

## Follow-up (not run)
Re-score with MOT20-01 removed as pre-registered policy; add more real sequences (MOT17 train) so the real
ordering is estimable before asking whether renders reproduce it.
