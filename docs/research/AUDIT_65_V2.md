# AUDIT_65_V2 · Dress rehearsal v2 (`65_DRESS_REHEARSAL_V2.md`, commit 7b47e30)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** 'H53 running, no result' is superseded — H53 reported and 65 v2 was updated by AUDIT_H53 (99 % twin FA cut, recall 0.782 → 0.758, not met).

Method as AUDIT_65: every number extracted by script, every derivation recomputed, every
don't-say mapped to a registry row. No engine, no GPU.

## 1. Numbers vs FACTS_VERIFIED.md

Script: `re.findall(r"(?<![\d.])\d+\.\d+(?![\d.])", v2)` → **115 distinct decimals, 115 present in
FACTS** (0 misses). Integers/ratios checked by grep: 205 / 92 / 120 alarms/h, 490×, 4,500–87,000×,
3,002 cam-h, 450 / ~228 steps, 80.6 h, 9.2/24 cam-h, 1e-15 — all in FACTS. Derivations recomputed:

| value in v2 | derivation | check |
|---|---|---|
| ~2,900× | 2.915 / 0.001 = 2,915 | ok |
| "cut by a fifth" | 1 − 2.218/2.915 = 0.239 (CRC) | ok (≈ a fifth to a quarter) |
| 2.2 to 5.0 | 2.218 and 5.033 rounded | ok |
| 0.62 | 0.621 rounded | ok |
| ~3,000 real cam-h (Q3) | rule of three, 3 / 0.001 | ok (not R30: no "×") |
| 4 NX | ⌈40 / 12⌉ = 4, ⌈40 / 10⌉ = 4 | ok |
| −0.083 | 0.504 − 0.586 (ranked, pooled − A1) = −0.082; FACTS/58 §8.4 paired −0.083 | ok (paired estimate) |
| +0.035 | 0.621 − 0.586 = +0.035 | ok |
| 60's `15.7` (only 60 miss) | 2(1.95996 + 0.84162)² = 15.70 | ok → allowlist |

## 2. Don't-say → RETIRED_CLAIMS rows

§8's 25 items all cite existing rows (R02–R53). **Miss:** the §2 ✗ overclaims and two §10 bullets
had no row. Fixed: new **R54** (never-measured overclaims, allowed only in the don't-say lists of
60/65 v2/48/78/79); §8 item 26 and §10 now cite R54/R46; "photoreal" answered by R20.

## 3. Ship recommendation vs 58 §8.4

Matches: 1 op → conformal θ 0.962851 ranked, 0.621 realised; ≥ 2 → A1 θ 0.95 ranked; pooled never.
Table rows match 58 §8.4 exactly. Fixed: the spoken rule now states "θ 0.9629" as 58 §8.4 does.

## 4. Ten 20-word answers

No retired number in any. **Unmeasured claims fixed:** Q2 "fusion … can [fix it]" (H53 running) →
"fusion is untested (H53 running)"; Q4 "the constants move, not the structure" → marked as an
untested expectation. §7's fuse line and §10's fusion bullet now say H53 is running, no result;
§2 item 4 extends "no number yet" to H47/H51/H53. Q6's "contention noise" is R46's correct form.

## 5. Whiteboard (§7)

Human-decision box ("1 operator … HUMAN decides") and WORM audit log (model hash, θ, verdict) both
present; tamper as its own alarm and "nothing leaves site" required unprompted. Pass.

## 6. "Time I was wrong" (§5)

States "+0.004 to +0.005 AP, not significant after Holm, and nothing at 1,000" and the real-only
+0.0049 step effect; never calls H26 a proof. The 10-seed re-run (H51) is stated as running. Pass.

## 7. Test gap closed

`tests/test_docs_numbers_in_facts.py` (< 0.1 s): every decimal in 60 and 65 v2 must be in FACTS or in
`facts_derived_allowlist.txt` (value | file | derivation; entry format itself tested).

## Score

| criterion | before | after |
|---|---|---|
| numeric accuracy vs FACTS | 10/10 | 10/10 |
| derivations | 10/10 | 10/10 |
| don't-say → registry | 7/10 | 10/10 |
| ship answer vs 58 §8.4 | 9.5/10 | 10/10 |
| hard answers: no unmeasured claims | 7/10 | 10/10 |
| whiteboard safeguards | 10/10 | 10/10 |
| retraction framing | 10/10 | 10/10 |
| automated number guard | 5/10 | 10/10 |
| **total (×1.25)** | **85/100** | **100/100** |
