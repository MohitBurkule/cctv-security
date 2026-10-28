# AUDIT_74 · Adversarial audit of 74 (system-design drills)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** 'h14b +0.0121' traced ✓ in §1 is retired as the dose gain (AUDIT_H26, R51); the drill-1 alarm load now follows the 58 §8.4 staffing table (AUDIT_H45).

Audited 2026-09-27 against `c1237a7`. Method as AUDIT_67-69: every number grepped in
`FACTS_VERIFIED.md`, else in the cited corpus file; arithmetic recomputed; law
instruments checked against 67 §5 / AUDIT_67-69 [V] rows; RETIRED_CLAIMS grep run.

## 1. Numbers recomputed

| claim | check | result |
|---|---|---|
| 31.1 TB / 30 d, 96 Mbit/s | 40 × 2.4 Mbit/s × 2,592,000 s / 8 = 31.1 TB | ✓ |
| 93.3 TB for 3 sites | 3 × 31.1 | ✓ |
| ~31 bn tokens, 120 cams × 30 d | 120 × 720 h × 0.36M (FACTS 45 row) = 31.1 bn; high-res 1.1M → 95 bn | ✓ (high-res added) |
| 290M tokens/h fleet | 800 × 0.36M = 288M | ✓ |
| 4 NX for 40 cams | FACTS 38 row (10–12/NX, decode 18) | ✓, but plan figure (ReID [A]) — now said |
| 2.31 FA/cam-h, recall 0.789, −0.035, 0/10 vs 6/10 | FACTS H33 | ✓ |
| conformal floor 0.248 | FACTS H33 0.248–0.263 | was implicit; now stated with range |
| 0.511 realised @5 min | FACTS H22 | ✓, but "inconclusive" vs bar omitted → added |
| 92 alarms/h, util 0.77 | 2.31 × 40; 92 × 30 / 3600 | ✓ arithmetic; not an H22 run → caveated |
| 2,300× | 2.31 / 0.001 = 2,310 | ✓ |
| i-LIDS 10 s, recall@10 s 0.242 | FACTS #20, H58 r3 | ✓ |
| ~55 alarms/cam-day | 2.31 × 24 | ✓ |
| H1 0.152, h14b +0.0121, H25 94 % | FACTS; R15/R21 clean | ✓ |
| MEVID 3.5 %, tamper six kinds | FACTS 113, R38 | ✓ |

## 2. Fixes (in place)

1. **Drill-1 box count inconsistent**: "4 × NX (10 cams each, 1 hot spare)" is 40 cams with no spare. → 5 NX (4 active + 1 spare); fleet 100 NX not "80 plus spares".
2. **Drill-2 NX over budget**: PAR + CLIP heads placed on the NX, which 38 §2.5's 10–12 cams/NX does not afford. → moved to the site server on keyframe crops, [A].
3. **Alarm path missing upstream + decision point**: fusion consumed PIDS/radar that had no box; audit log only saw verdicts, not raised alarms; no explicit human-decision box. → PIDS input drawn; alarm engine writes every alarm to audit; "HUMAN DECISION" (Arts 22A–D) on console; change-board human approval in drill 3; automatic rollback made conditional on board pre-approval.
4. **Overclaims a hostile CTO would hit**: "the operator is the bottleneck" stated as fact from an invented-parameter queue sim that H22 itself calls inconclusive → hypothesis; "selected before touching a site" implied site deployment → "none checked on a real site"; "training pipeline **refuses**" a set without licences.json — no such gate exists → "should refuse; manual today"; "compliant set costs little" from one comparison → hedged; no line-crossing number exists → said.
5. **Law instruments**: JSP 936 now "Part 1, 13 Nov 2024"; Art 22 → "Arts 22A–D inserted by DUAA s.80, in force 5 Feb 2026 (SI 2026/82)"; SCC "of the 12", PoFA, principle 7 for query gating; PSTI added (drill 1 and 3) with consumer-SKU scope and "not the software"; drill 2 notes a lead is probably not a "significant decision".
6. **Rubrics made observable**: Strong rows rewritten as things on the board or said aloud (box counts, named boxes, arrows), not qualities.

## 3. Score

| | before | after |
|---|---|---|
| numbers traced | 17/18 (floor implicit) | 18/18 |
| design consistency | 2/3 drills | 3/3 |
| law overlay | 3/5 instruments precise | 5/5 |
| rubric observable | 0/3 | 3/3 |
| **overall** | **74** | **93** |

Residual: 72 §2.3's 7–71 GB index may exclude PAR/CLIP thumbnails (flagged in text, not re-derived); NX figures for PAR/ReID remain [A] until measured.
