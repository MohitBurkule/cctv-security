# AUDIT_82 · Sceptical hiring-manager audit of `82` (mock interview round 6, process)

Audited 2026-09-27 against `f2bbf77`. Method: every count traced to the file that records it;
every model-answer number grepped in `FACTS_VERIFIED.md`; H26 timeline checked against
`git log --format='%h %ci %s'`; red-flag read (blaming tools, overclaiming the fix, treating the
retraction as proof). Fixes applied in place.

## 1. Counts traced

| Claim in 82 | Recorded in | Verdict | FACTS process row |
|---|---|---|---|
| 125 ledger rows (25/67/33) | AUDIT_LEDGER §8 counts line | match | added |
| 27 audits on 2026-09-27 | AUDIT_LEDGER l.13 | match | added |
| 14 contradictions (§10) | AUDIT_LEDGER §10 (14 rows) | match | added |
| 39 "3/14" hits, 17 current | AUDIT_STALENESS_SWEEP row 1 | match | added |
| 31 marker-rule hits | commit `ff76386` message only | match, weakly sourced; 82 now says so | added |
| 17 bare-"was" hits | AUDIT_79 "Test" | match | added |
| 105 lines / 33 files; 100 + 5 + 14 | AUDIT_81 | match | added |
| 56 registry rows R01–R56 | RETIRED_CLAIMS.md (56 `\| Rnn` rows) | match | added |
| two doc tests | tests/test_docs_retired_claims.py, test_docs_numbers_in_facts.py | match | added |
| 19 docs carried h14b | AUDIT_H26 §4 | match | added (timeline row) |
| 315 → 318 FACTS | AUDIT_79 | match | added |
| 137 docs/13 decimals | AUDIT_LEDGER §9 | match | added (ledger row) |
| 0.4952 / 0.4983 / 0.4981 / 0.4956; 600 s | AUDIT_H26 | match; were absent from FACTS | added |
| 7,200 MB guard, 3.4 GB peak | docs/12 l.1068–1069 | match; absent from FACTS | added |

All other model-answer numbers (h14b 0.0121 [0.0111, 0.0130], p 0.0079, +0.0041/+0.0045,
+0.0049, H24 0.0006, H32 9/13→2/13 and 10/13→3/13, H53 0.488→0.0047 / 99.0 % / 0.782→0.758 /
7 of 298 / tailgate 0.007, H47 −0.201 [−0.254, −0.154], H22 0.511 / +0.262, A1 0.825, HOTA
0.434→0.443, 953 GB, ~228 steps, budget A = 4 / K = 500) are in FACTS. "2.3 points" = FACTS −0.023.

## 2. H26 timeline vs git

06:48 `1cc0b93` pre-reg · 09:27 `dbd21c4` results · 09:40 `7d481e0` AUDIT_H26 · 09:43 `679df88`
H51 pre-reg · 09:48 `e299c88` 52 §5b · 09:55 `50c76a7` AUDIT_NARRATIVE_POST_H26 (17/27).
**All six match.** "Pre-registration to result in under three hours" (2 h 39 min): match.
"Suspected it while re-reading the runner" is not checkable from git; acceptable as testimony.

## 3. Red flags found and fixed

1. **Q1 framed the retraction as proof of wrongness** ("a precise wrong answer"). The h14b
   number was a correct measurement of a confounded comparison; H26 shows the claim unsupported
   (+0.004–0.005, n.s.), not that the gain is zero. Reworded.
2. **Q20** "replaced a larger wrong one" → "a larger, confounded one" (same reason).
3. **Narrative overclaimed the fix**: "retracted the headline everywhere" → "in the 19 docs that
   stated it as current (32 keeps it as the historical h14b result)".
4. Q11's 31 now states its only record is the commit message.

No answer blames tools (Q1, Q16, Q18 each name the blame-tools red flag and avoid it); every
fix carries a stated hole (Q3 runner guard "proposed, not built"; Q10 "what doesn't it catch").

## 4. Consistency with 46 stories 18–24 and 65 v2 §5

Same numbers (~228 vs 300–450 steps, +0.004–0.005, +0.0049, R51/R52/R53, H51 10 seeds) and
the same "not significant after Holm" framing in 46 #24 and 65 v2 §5. **46 story 23 was stale**:
"43 rows" → 56 (R01–R56), and its exemption list still included "was", removed by AUDIT_79.
Fixed. 00 index row for 46 now names the H26 story.

## 5. 82's gap list

FACTS H40b row says "assumed budget" (`6d0e8ff`): **closed**. 00 index "Twenty-four stories"
(`6d0e8ff`): **closed**. New: FACTS header count said 324 but HEAD had 339 rows; now 350 with
the 10 process rows (350 incl. a concurrent H51 row). H51 results were landing while this audit ran: 82 Q2/Q15/Q20 "H51 running" will need updating when they commit.

## Score

**8 / 10 → 9.5 / 10.** Every count traced and the timeline exact; lost points for two answers
treating the retraction as proof of wrongness, one "everywhere" overclaim, a
commit-message-only count, and 13 process numbers with no FACTS row.
