# AUDIT_81 · Field alarm benchmarks (81) and the 0.001 budget's provenance

Audited 2026-09-27 against `4efaec0`. Method as AUDIT_67-69: primary sources re-downloaded
(`curl` + `pdftotext -layout`, then grepped), every conversion recomputed, every [A] checked
for a missing fetch, then a corpus-wide sweep of "0.001" / "× over budget" lines.

## 1. Primary sources re-fetched

| claim | where | result |
|---|---|---|
| NPCC 2024: Level 1 until 3 false calls in a rolling 12 months (§3.2.1); warning at 2 (§3.2.2); withdrawal at 3 (§3.2.3) | 81 E1, Q2 | **[V]** verbatim, extracted l. 452–460 |
| 90 days free of false calls to reinstate | 81 E3 | **[V]** l. 482 |
| BS 8418 CCTV: "False alarm withdrawal thresholds for CCTV systems are the same as IAS" | 81 E2 | **[V]** l. 499–500 |
| Hold-up alarms: Level 1 until 2; withdrawal at 2 (§3.4.2–3) | 81 E3 | **[V]** l. 523–529 |
| i-LIDS: ~24 h per event dataset; "ten seconds to report an alarm state"; repeat FP logged every five seconds; overall F1 0.7 at application phase | 81 E6, Q5 | **[V]** l. 349, 1202, 1209, 1171 |

## 2. Conversions

| claim | check | result |
|---|---|---|
| 3 / 12 months ≈ 3.4 × 10⁻⁴ per system-hour; 8.6 × 10⁻⁶ over 40 cams | 3/8,760; /40 | ✓ 3.42e-4; 8.6e-6 |
| 1 / zone / day = 0.042 / h | 1/24 | ✓ 0.0417 |
| A1 ≈ 120 alarms/h at 40 cams, ≈ 1 M/yr | 2.915 × 40; × 8,760 | ✓ 117; 1.02 M |
| pooled 5.033 ≈ 205/h | 5.033 × 40 = 201 | ✗ → **≈ 200**. Fixed |
| conformal 2.10–2.22 ≈ 92/h | 84–89 | ✗ → **≈ 86**. Fixed |
| loiter 50–120× zone-day; twins ~12×; fused ~9× under; floor 24× | /0.0417 | ✓ (50–53, 70, 121; 11.7; 8.9; 24) |
| "20–40× over the lenient end" (0.12) | 2.10/0.12 … 5.033/0.12 | ✗ → **~18–42×**. Fixed |
| 2,000–5,000× over 0.001 | 2,100–5,033 | ✓ |
| zero-failure Pd 0.9: 22 trials at 90 %, 29 at 95 % | ln(1−C)/ln 0.9 | ✓ 21.9, 28.4 |

## 3. Tags

Every [A] (E9 PIDS 1/zone/day, E10 50131/62676, E11 vendor claims, §3 OR practice) is a
source that failed to fetch or is paywalled, as the header says — honestly [A]. E5 is
correctly "[V] secondary". No [V] rests on a failed fetch. §3 heading and table column
now say "assumed" explicitly.

## 4. Budget-provenance sweep

New registry row **R56** (RETIRED_CLAIMS; fixtures in `tests/test_docs_retired_claims.py`)
flags a line quoting 0.001 as a budget or "× (over) budget" unless it carries
`assumed | our budget | 28 §6 | A=4 | zone/day`. First scan: **105 lines** in 33 files
(32, 03, 66, 71 excluded by instruction and allowed in R56). **100** were reworded mechanically
("… over our assumed 0.001 budget", "0.001 (assumed, 28 §6)"), 5 in 81 by hand, and
**14** targeted edits added the external anchors (PIDS ≈ 1/zone/day [A]; NPCC 3 calls/12 months
[V], a different quantity) to 60 #23 and "never say" #2, 65 v2 (opener, §2 #5, Q2), 68 Q12
model answer and follow-up, 79 Q18, 78 alarm economics, 74 drill 1 (question 2 and budget gap),
58 §8.4, 52 register, 76 metric, 48 C8, 77 #1. CLAUDE.md principle 4 says "an operator
budget", which does not imply a standard: left unchanged. Three FACTS rows added (NPCC,
i-LIDS, provenance/conversions).

## 5. Score

3 arithmetic errors in 81's table/§3 (all in derived [INF] cells, none in a sourced number),
0 quote errors, 0 tag errors. **Score: 8.5 / 10.**
