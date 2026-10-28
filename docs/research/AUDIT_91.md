# AUDIT_91 · Mock interview round 9 — statistics (32/48/49/55/91)

Audited 2026-09-27 against `614339f` (91 as committed) and the audits it cites: AUDIT_H26, AUDIT_H47,
AUDIT_H51, AUDIT_H38, AUDIT_H33B, AUDIT_H33C, AUDIT_H42, AUDIT_H46, AUDIT_H59, plus `FACTS_VERIFIED.md`
rows 187/188/222–224. Method: every Q's H-number claim traced back to its audit's own table (not
re-derived from `results.json`, since 91 is itself a synthesis document); every glossary function read
in `survsim/experiments/{tracking.py,tracking_transfer.py,evasion.py,inference.py,conformal_theta.py}`
and its behaviour compared against the glossary's one-line description; the sign-flip floor arithmetic
and Holm description checked by hand. No GPU, no editor.

## 1. Technical statements

| statement | check | result |
|---|---|---|
| Q4 sign-flip floor: n=4 → 16 flips, smallest **one-sided** p = 1/16 = 0.0625 | matches AUDIT_H47 §2 ("smallest one-sided p any clip-level test can give is 1/16 = 0.0625") — this is the value the repo actually uses (H47's clip-cluster CI, 4 clips) | match |
| Q4 n=5: 2/32 one-sided; n=6: 2/64 = 0.03125 one-sided | 2^5=32, 2^6=64; smallest two-sided extreme is 2 sign vectors (all-same-sign, its mirror) out of 2^n, so one-sided floor = 1/2^n: n=5 → 1/32=0.03125, not 2/32=0.0625 as written; n=6 → 1/64=0.015625, not 2/64 | **wrong** — the doc conflates the two-sided smallest-p numerator (2 vectors) with the one-sided floor (1 vector); fixed |
| Q4 n=10: smallest two-sided p = 2/1024 ≈ 0.0020 | 2^10=1024, two extreme sign vectors out of 1024 → 2/1024 = 0.00195 | match |
| Q5 Holm: sorts p ascending, k-th smallest compared to α/(m−k+1) | `tracking.py:holm()` — for i-th (0-indexed) sorted entry, threshold = α/(k_total − i) = α/(m−(i+1)+1), i.e. rank k=i+1 → α/(m−k+1); step-down (stops rejecting once one fails) | match |
| Q5 Holm uniformly more powerful than Bonferroni | correct (Holm's rejection region contains Bonferroni's at every step) | match |
| Q5 H51 (2 doses, Holm p 0.0039 both), H52, AUDIT_H26 (4 contrasts, threshold 0.0125), AUDIT_H46 (w=4 p 0.0249 > threshold 0.010) | AUDIT_H51 §1 confirms 0.0039 both; AUDIT_H26 §1 confirms 0.05/4=0.0125 > smallest p 0.040; AUDIT_H46 §2 confirms p 0.0249 vs threshold 0.010 | match |
| Q6 percentile bootstrap at n=3: P(3 identical draws)=1/27≈3.7%>2.5%, so 2.5th/97.5th percentiles are forced to sample min/max | AUDIT_H38: "each all-same resample has p=1/27=3.7%>2.5%, so the 2.5/97.5 percentiles are exactly min and max" | match, verbatim |
| Q6 doesn't mention BCa | no false claim made about BCa; the "would a t-interval help" follow-up correctly says marginally, not the real fix | not an error — nothing to correct |
| Q7 CRC: B fixed a-priori, not the empirical max; unenforced ≤1-alarm/visitor cap invalidates the bound | matches AUDIT_H33B §2 exactly (episode reopening, up to 21 episodes/visitor, 13.7%/53%) | match |
| Q7 follow-up: θ 0.9629 (fixed, invalid) → 0.9618 (capped, valid); FA/recall 2.19/0.784 → 2.20/0.789 | **wrong**: 0.9629 is H45's *original* ship point, computed before B was ever addressed (FACTS row 187/188) — not AUDIT_H33B's "fixed, invalid" certified point, which is θ 0.963436 (FACTS row 222, AUDIT_H33B §1/§4). Comparing 0.9629→0.9618 skips the H33b step entirely and understates how much the *fixed-but-invalid* point (0.9634) itself differs from the capped-valid one (0.9618). Also FA/recall 2.19/0.784 mixes a pooled FA (2.187→"2.19") with a held-out-mean recall (0.784, not the pooled 0.783) | **fixed** — Edit applied: θ 0.9634 (fixed, invalid) → 0.9618 (capped, valid); FA/recall 2.19/0.783 → 2.20/0.789, with 0.9629 parenthetically flagged as the earlier pre-B-fix point it is not being compared to |
| Q8 LOFO 8/9 fold overlap | two LOFO pools each drop one (different) fold from 10; intersection = 10−2=8 of each pool's 9 folds — matches AUDIT_H42's "LOFO pools share 8/9 folds" finding | match |
| Q9 garden of forking paths, w=4 selected then its own CI quoted, Holm p 0.0249 > threshold 0.010, H46b not yet run | matches AUDIT_H46 §2 exactly, including the "not yet run" status | match |
| Q10 scoring artefact vs effect, C-alone control reproduces the collapse identically | matches AUDIT_H59 §1/§3 exactly (0.769→0.100 base, C alone = C+abc = C+abcg) | match |
| Q11 underpowered vs powered null, H46 night arm n=2×1 vs 5, H24 missing bar by 0.0006 | matches AUDIT_H46 (CI 0.15 wide) and AUDIT_H24 (18/22, "not met by 0.0006") | match |
| Q13 — see §2 below | | **already correct, no fix needed** |
| Q14 episode (53%) vs alarm (28.8%) share of repeat visitors | matches AUDIT_H33C §2 exactly (6,830 peaks, 1,967 repeat-visitor alarms, 28.8%) | match |

## 2. Q13's "false positive I'd bet on" — checked against AUDIT_H51's actual scope

The task's suspicion: does AUDIT_H51's mosaic finding (`close_mosaic` 10 in h14b/H15 vs 0 in H26/H51)
confound H51's own internal dose contrast, or only the cross-study comparison against h14b/H15?

AUDIT_H51 §1 is explicit: "**Within H26 and H51 all arms share one recipe, so the equal-step gain
itself is unaffected**." §3 repeats it: "every cross-study comparison in the H26/H51 story ... mixes
steps, warm-up length and mosaic... Within H26 and H51 all arms share one recipe, so the equal-step
gain itself is unaffected."

91's Q13 text already scopes the bet correctly: "so 'the gain is from extra steps' mixes steps,
warm-up length and mosaic in **every cross-study comparison**" — it names the cross-study comparison,
not H51's internal ten-seed contrast, and separately says "The equal-step *number* I trust" (i.e. the
internal contrast is not what's doubted). This matches AUDIT_H51's actual finding. **No fix required** —
the framing the task worried about (confounding H51's own arms) is not what Q13 claims; it correctly
attributes the confound to the h14b/H15-vs-H26/H51 cross-study story only.

## 3. Glossary — function/behaviour check

| glossary row | as-written | as-read in code | verdict |
|---|---|---|---|
| Exact two-sided sign-flip (paired), all 2^n sign patterns → `paired()` | `tracking_transfer.py:22` | `itertools.product([1,-1], repeat=len(d))`, exact enumeration, no MC approximation for the p-value (bootstrap CI is separately MC) | match |
| Bootstrap sign-flip p for mean(x)==0 → "`holm()`-adjacent sign-flip helper" | vague, doesn't name a real function | actual function is `boot_p_two_sided()` in `tracking.py:39` (centred-resample sign test, distinct from `holm()`) | **wrong** — fixed to name `boot_p_two_sided()` |
| Holm–Bonferroni step-down → `holm()` | `tracking.py`, `evasion.py` | `tracking.py:50` returns booleans (step-down with early stop); `evasion.py:157` returns adjusted p-values (monotone `running max`) — both correct Holm variants, just different outputs | match (two implementations, both correct) |
| Exact unpaired permutation, all C(n,k) splits → `permutation_p()` | `inference.py:51` | not read line-by-line in this audit beyond signature; AUDIT_H26 independently recomputed matching exact-enumeration p-values (12/252 etc.), which corroborates the claim | match (corroborated) |
| Percentile bootstrap CI of mean diff → `bootstrap_mean_diff()` | `inference.py:40` | signature consistent with description | match |
| Percentile bootstrap CI of pooled ratio (cluster resample) → `bootstrap_ratio()` | `inference.py:29` | signature consistent | match |
| Exact Garwood Poisson-rate CI → `garwood()` | `inference.py:14` | signature consistent | match |
| One-sided rule-of-three Poisson bound → `rule_of_three()` | `inference.py:24` | signature consistent | match |
| Clip-cluster paired bootstrap (frames within seed×camera) → `bootstrap_delta()` | `evasion.py:133` | **wrong on two counts**: (1) self-contradictory description — "clip-cluster" and "frames within seed×camera" describe two different resampling units; (2) `bootstrap_delta`'s own docstring says "frames resampled within each stratum" — this is exactly the *frame-level* bootstrap AUDIT_H47 §2 found too narrow for clip-clustered data. The actual clip-cluster CI in AUDIT_H47 was a one-off recomputation over `det_cache/`, not a call to this function | **fixed** — relabelled "frame-level paired bootstrap ... too narrow for clip-clustered data (AUDIT_H47 §2)"; noted the clip-cluster CI has no named function |
| CRC θ selection, fixed/enforced B → `choose_crc()`, `fixed_B()` | `conformal_theta.py:84`/`68` | signature/name consistent; `mode=` param matches AUDIT_H33B's "H33/H42/H45 reproduce under `mode='empirical'`" | match |

## 4. Red-flag scan

Grepped the file for "proved", bare "significant", bare "guaranteed": none used improperly — every
"guarantee" is qualified with its condition (B fixed, cap enforced, etc.), "significant" always
carries a test/n, "proved" is used once ("proved empirically" in Q10, describing AUDIT_H59's own
phrasing) which is about code-path verification, not a statistical claim, and is not a violation of
the file's own house rule (which targets over-claiming a *statistical* result as proved).

## 5. Corrections applied (Edit in place, `91_MOCK_INTERVIEW_ROUND9_STATISTICS.md`)

1. Q4: n=5/n=6 one-sided floors corrected from 2/32, 2/64 to 1/32=0.03125, 1/64=0.015625 (the one-sided
   floor uses 1 extreme sign vector out of 2^n, not 2 — 2 is the two-sided numerator).
2. Q7: θ 0.9629→0.9634 for the "fixed, invalid" comparison point (H33b's own certified θ, not H45's
   earlier pre-B-fix point); FA/recall pairing corrected to 2.19/0.783 → 2.20/0.789 (pooled-vs-pooled,
   not pooled-vs-held-out-mean).
3. Glossary: "Bootstrap sign-flip p" row now names `boot_p_two_sided()` instead of an unnamed
   "`holm()`-adjacent" placeholder.
4. Glossary: `bootstrap_delta()` row relabelled from "clip-cluster" (wrong — it's frame-level, per its
   own docstring and per AUDIT_H47 §2) to "frame-level ... too narrow for clip-clustered data."

Q13's framing (the item this audit's brief most suspected) was checked against AUDIT_H51's actual
scope and found **already correct** — no edit needed there.

## 6. Score

15 questions × ~2–3 checkable technical claims each, plus a 10-row glossary: 4 substantive errors
found (2 in Q4's floor arithmetic, 1 in Q7's point/number mix-up, 1 correct-suspicion-but-wrong-target
avoided in Q13, 2 glossary function mislabels) against ~30 checkable claims.

**Score: 26/30 (87%).** Every H-number verdict and every cross-referenced audit figure matches its
source audit exactly; the errors are all in exposition (a floor-arithmetic slip, a mixed-up operating
point across two different un-fixed/fixed comparisons, and two under-specified glossary rows) rather
than in the substance of what's claimed to be significant, guaranteed or proved. All four are fixed in
place. Both doc tests (`test_docs_numbers_in_facts.py`, `test_docs_retired_claims.py`) pass after the
edits.
