# AUDIT_H42 · θ-selection policy for the frozen A1 weights (32 §H42)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** the pooled (~205/h) and conformal (~90/h) operator loads bracketed [INF] in §2 were measured by H45 (AUDIT_H45); 58 §8.4 now carries measured values.

Audited 2026-09-27 against `ce4f880` (pre-registration) and `0b4f5d9` (results, 58 §8.3, FACTS,
66). Method as AUDIT_H38: every number recomputed in Python from
`out/experiments/h42_theta_policy/results.json` (`policies[*].draws`, `summary`, `A1`, `decision`)
and `fold_stats.json` (per-fold grid counts, summed by hand for the pooled figures); method claims
checked against `survsim/experiments/theta_policy.py`.

## 1. Recomputed

| claim | recomputed | result |
|---|---|---|
| wall 1,190 s; 1,077 pooled events, 102–113 per fold | 1,190.1 s; `events_per_fold` sum 1,077, min 102, max 113 | match |
| (a) per-fold θ 0.9 ×7 / 0.95 ×3 | draws: 0.9 on 58,158,258,358,458,858,958; 0.95 on 558,658,758 | match |
| (a) FA range 2.118 [2.915–5.033], SD 1.023 | 2.1176; SD ddof = 1 1.0229 (ddof = 0 0.970) | match (SD is sample SD) |
| (a) recall 0.825–0.894, 10/10 ≥ 0.80 | same | match |
| (b) pooled θ 0.9 ×10 → 5.033 [4.953, 5.114], recall 0.894 [0.863, 0.924] | same | match |
| (c) CRC θ 0.9629–0.9649, FA 2.099–2.218, SD 0.032 | 0.96285–0.96486; 2.0993–2.2179; SD 0.0324 | match |
| (c) recall 0.778–0.783, 0/10 ≥ 0.80 | 0.7778–0.7833 | match |
| (d) θ 0.96 ×10 → 2.364 / 0.792, 0/10 | 2.3644 / 0.7917 | match |
| (d) "meets 0.80 on the pooled select folds by construction" | pooled select recall at 0.96 = 876/1,077 = 0.813 | match |
| (b) − A1 ΔFA +2.118 [+2.005, +2.237], Δrecall +0.069 [+0.045, +0.095] | +2.1176 [+2.0050, +2.2374]; +0.0694 [+0.0455, +0.0946]; paired on the same H12 worlds (`paired()`) | match |
| (c), (d) − A1 deltas (−0.697 / −0.042; −0.551 / −0.033) | same | match |
| "+1.7× FA for +0.069 recall" | 5.033 / 2.915 = 1.73 | match |
| (c) cuts spread 17.9× | range cut 17.86 (SD cut 31.6) | match |
| LOFO really used for (b)–(d) | `draws()`: per_fold → `[f]`; others → `folds[:i] + folds[i+1:]`; CRC pools the 9 folds' clean-world peaks | match |
| pooled select recall at θ 0.95 = 900/1,077 = 0.836; θ 0.9 991/1,077 = 0.920 | summed `fold_stats` grid at clock 5: 900/1,077, 991/1,077 | match — but these pool **all 10** folds; each LOFO pool has 964–975 events | minor → stated in 32 |
| verdict "hypothesis met by (b)" vs pre-registered "(b) or (c) has H12-FA spread ≤ ½ of (a)'s (range and SD) AND recall ≥ 0.80 in ≥ 9/10" | (b): range/SD 0 vs 2.118/1.023, recall 10/10 → literally met; `decide()` encodes the same | match on wording, **qualified**: LOFO pools share 8/9 folds, (a)'s draws are disjoint single folds, so the spread comparison is not like-for-like and zero spread is partly by construction. The registration did not demand disjoint pools, so the verdict stands with the caveat |
| shipped policy = (b) (smallest spread among recall-OK) | only (a), (b) recall-OK; (b) range 0 | match |
| "The stable operating point is therefore 5.033 / 0.894" | SEL_GRID = {0.5, 0.8, 0.9, 0.95, 0.98, …}; on pooled counts θ 0.93 (954/1,077 = 0.886, select FA 4.10) and 0.94 (919/1,077 = 0.853, 3.59) also pass 0.85 at lower FA; H12 not scored at either | **imprecise** → "on SEL_GRID"; a fine-grid pooled choice would be ≈ 0.94 |
| "A1's θ 0.95 was a small-fold draw" | 3/10 per-fold, 0/10 pooled | match |
| "The 0.001 FAIL stands under every policy" | lowest FA 2.099 | match |

## 2. Corpus issue (not a number error)

After H42 the corpus still said "A1 ships" as a single point in 52/60/64/65/74/78, while 58 §8.3
already said the pooled point and a criterion change were open. There are three measured points
for the same weights — A1 2.915 / 0.825, pooled 5.033 / 0.894, conformal ≈ 2.15 / 0.78 — and only
A1's alarm rate (~120/h per 40 cameras) has been through the H22 operator sim (realised 0.511 FIFO
/ 0.586 ranked @5 min). The pooled point (≈ 205/h) and the conformal point (≈ 90/h) are bracketed
[INF] by H22's dwell_25 (244/h) and twin-floor (44/h) arms, not measured. Written once as 58 §8.4;
referenced from 52 (new H42 row + two lines), 64 (§ round-4 paragraph, register row, (c)), 60 #23,
48 C8e follow-up + #41c, 65 N2b, 74 constants table + drill 1 alarm load, 78 results line +
opener; FACTS (audit row + trade-off row); RETIRED_CLAIMS R48 ("A1 ships unchanged / with θ 0.95"
without the §8.4 caveat); 66 (H42 done, H45 operator-budget elicitation added); 00 index.

## 3. Score

21 claims checked: 18 match, 1 minor (900/1,077 pools all 10 folds, not a LOFO pool), 1 qualified
(verdict met on wording, spread comparison not like-for-like), 1 imprecise (stable point is a grid
artefact). **Score 19 / 21 (90 %)** — every number was right; the defects are interpretation: the
zero spread is partly structural, the pooled θ 0.9 depends on a coarse grid, and the ship decision
is an operator-budget trade-off that H42 cannot settle (H45).
