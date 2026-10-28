# AUDIT_H51 · Equal-step dose re-run, 10 paired seeds (32 §H51)

Audited 2026-09-27 against `679df88` (pre-registration) and `385f363` (results). Method as
AUDIT_H26: every number in 32's H51 results section recomputed in Python from
`out/experiments/h51_equal_steps/results.json` (`arms[*].eval["mot20_02@640"]`, `arms[*].train_opts`,
`arms[*].train_cost`, `seed_summary`, `paired`, `contrasts`, `curve`); the exact sign-flip test
re-enumerated over all 2^10 sign vectors; Holm redone by hand; the 15 arms shared with H26 compared
against `out/experiments/h26_dose_fixedstep/results.json`; the recipe of h14b and H15 read from their
`work/*/train/args.yaml`; ultralytics 8.4.163's `engine/trainer.py` read for the close_mosaic rule;
`driver.log` for the relaunch. No GPU, no re-training.

## 1. Recomputed

| claim in 32 §H51 | recomputed | result |
|---|---|---|
| real-only 0.4911 [0.4895, 0.4926], sd 0.0027 | same (`curve["0"]`, 10 arm APs) | match |
| +100 v8 0.4953 [0.4936, 0.4968]; +300 v8 0.4962 [0.4947, 0.4977] | same | match |
| +100 v7 diagnostic 0.4932, n = 5 | 0.49316 | match |
| AP50 means 0.8212 / 0.8245 / 0.8251 / 0.8245; AP75 0.5209 / 0.5227 / 0.5245 / 0.5214 | same | match |
| paired +0.0042 [+0.0024, +0.0062]; +0.0051 [+0.0037, +0.0064] | diffs mean 0.0042 / 0.0051; CIs as stored | match |
| exact sign-flip p 0.0039 / 0.0020 | 0.00391 / 0.00195 (1 024 vectors) | match |
| Holm p 0.0039 both | min(2 × 0.00195, …) = 0.0039; second 0.0039 | match |
| AP50 +0.0033 (0.023) / +0.0039 (0.033); AP75 +0.0018 (0.18) / +0.0036 (0.033) | same | match (AP75 at 100 n.s.) |
| seeds > 0: 9/10, 10/10; v7 0/5 | 9 (seed 2 −0.0001), 10, 0 | match |
| v7 − v8 −0.0021 [−0.0026, −0.0016], p 0.0625 | same; 0.0625 is the n = 5 floor, so n.s. | match |
| unpaired perm p 0.0038 / 0.0005, Holm-rejected | `contrasts.primary` | match |
| 15/15 shared arms equal H26 to 4 dp | 15/15 identical, including the re-trained dose300_s2 | match |
| recipe: 450 steps, 225-its warm-up, close_mosaic 0, batch 8 | `train_opts` 12/9/6 ep × 300/400/600 imgs, warmup 6.0/4.5/3.0 | match |
| deviation: crash after 9 arms, dose300_s2 empty and re-trained | `driver.log` "10:17:04 disk 5 GB, arm dose300_s2" | match |
| df check only before the relaunch | one `driver.log` disk line | match |
| "free space stayed ≥ 4-18 GB" | not logged anywhere | **unverifiable** → reworded |
| last.pt kept, eval uses last.pt | `work/*/train/weights/last.pt` only | match |
| `--arm` fix (`ARM_RUNNERS`, `run(..., arms)`) | `385f363` diff | match |
| primary family narrowed to two v8 doses, as registered | 32 §H51 pre-registration, 66 | match |
| "size unchanged from H26" | H26 +0.0041 / +0.0045 → +0.0042 / +0.0051 (seeds 5-9 raised 300) | **imprecise** → "close to" with both pairs |
| "carried more by AP@0.5:0.95 than AP50 at 100 frames" | AP +0.0042 > AP50 +0.0033 > AP75 +0.0018 (n.s.) | **vague** → the three numbers stated |
| "Wall ~1.7 h of training" | 1.7 h is wall incl. eval and the crash; `train_cost` sums 0.71 h | **imprecise** → both stated |
| h14b gap "is the schedule … cannot split step count from warm-up" | h14b `args.yaml`: close_mosaic 10, 6 epochs → under 8.4.163's `epoch >= epochs − close_mosaic`, mosaic closed from epoch 0; H26/H51 close_mosaic 0 → mosaic on | **incomplete**: three factors move together, not two [A: inferred from args + code, no log line] |
| Corollary "with the v7 pool, 300 iterations beat 450" | mosaic and warm-up moved too | **overclaim** → removed |
| H15 v8_vis_300 vs dose300 "nominally the same recipe" | H15 `args.yaml`: 6 ep × 600 = 450 its, warm-up 225, but close_mosaic 10 → mosaic off | **wrong** → not the same recipe; mosaic a candidate cause, untested |

## 2. What stands

The pre-registered rule was met and the numbers are exact: at equal steps and ten paired seeds,
+0.0042 (100) and +0.0051 (300) AP over real-only 0.4911, Holm p 0.0039 both. The gain is real on
this setup and small: ~1 % relative, one real site (MOT20-01 → 02), one nano detector, 60 real
frames; AP75 at 100 frames is not significant. The h14b figure stays retired (R51) — it compared
unequal steps.

## 3. New finding: the "schedule" is also a mosaic switch

h14b and H15 trained 6 epochs with the default close_mosaic 10; the installed trainer closes mosaic
once `epoch >= epochs − close_mosaic`, i.e. from epoch 0. H26/H51 set close_mosaic 0 (mosaic always
on). So every cross-study comparison in the H26/H51 story — h14b mix_100 0.4983 vs 0.4953, H15 0.4981
vs 0.4962, and **real-only's +0.0049 "from extra steps"** — mixes steps, warm-up length and mosaic.
Within H26 and H51 all arms share one recipe, so the equal-step gain itself is unaffected. Wording
"+0.0049 from the extra steps" changed to "from H26's longer recipe" where this audit's sweep touched
it (46 #24, 52 §5b, 60 #9, 64 abstract, 65 v2 §5); the H26 section of 32 is left as history. A
one-factor re-run (h14b recipe with close_mosaic 0) would split it; not registered.

## 4. Story propagated (once)

"+0.004–0.005 AP at equal steps, Holm-significant at ten paired seeds (H51) — small, one site, one
detector; the +0.012 stays retired", and the retraction line "I retracted a number that mixed in
training steps, re-ran it properly, and the honest gain is a third to a half of what I first claimed
— and significant" (0.0042/0.0121 = 0.35, 0.0051/0.0095 = 0.54). Updated: 52 §5b + H14 row + new H51
row + §6 + pitch, 60 #9/#37/traps/pitch, 64 abstract/§reading/H26+H51 paragraph/evidence table/
conclusion, 78 opener and results lines, 68 Q18 + opener + quick list, 79 Q26, 46 story 24 (and
story 23's row count), 77 #2, 80 figure-2 text (the figure still plots H26's 5-seed points; noted),
65 v2 §2/§5/wave 1/Q1, 42 pitch, 82 Q2/Q15/Q20 + narrative (kept ≤ 300 words), 23, 57, 67, 74, 63, 00.
Registry: R51 note extended; **R57** flags the dose gain called "n.s."/"not significant after Holm"
without an "H26" or "before H51" marker (allowed: 32, 66, 13, audits). FACTS: H51 audit row, H51
timeline row, unreconciled-cells row updated, registry count 57. 66: H51 done, H52 unblocked (with a
power warning: a 50 % split of ~0.005 is ~0.0025, near the paired noise floor).

## 5. Score

26 checkable claims (§1): 19 match, 4 imprecise, vague or unverifiable (size "unchanged", AP split,
wall time, free disk), 1 incomplete (schedule = steps + warm-up only), 1 overclaim (300 beats 450),
1 wrong (H15 "same recipe").
**Score 19 / 26 (73 %).** Every number recomputes exactly and the verdict stands; the errors are all in
the cross-study explanation, which missed that mosaic was switched off in h14b and H15.
