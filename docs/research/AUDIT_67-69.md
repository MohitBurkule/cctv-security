# AUDIT_67-69 · Adversarial panel gaps (67), mock panel round 4 (68), night/thermal (69)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** H17 figures cited here (AssA −0.0051, DetA) are pre-parity and unequal-step (AUDIT_M1_PARITY, AUDIT_NARRATIVE_POST_H26, R53).

Audited 2026-09-27 against `090816f`. Method as AUDIT_64/65: every number grepped in
`FACTS_VERIFIED.md` (Python substring search, not regex), else in `58`/`60`/`65`; the H32
step-0 realism numbers checked against the original `survsim.realism compare` JSON outputs
(25 LLVIP IR + 25 LLVIP visible frames vs `batch_v8/street_crowd_night/cam_02`); primary
sources re-fetched where a claim depends on them.

## 1. Primary sources re-fetched

| claim | where | result |
|---|---|---|
| LLVIP AP50 YOLOv5 0.908 vis / 0.965 IR; YOLOv3 0.871 / 0.940 (arxiv.org/html/2108.10831) | 69 §4, Q&A 2 | **[V]** numbers; AP 0.527 / 0.670. **[X] framing**: 69 said "even for detectors pre-trained on colour" — each detector was trained per modality on LLVIP's 77.6 % train split |
| LLVIP not suitable for long-distance small targets | 69 §4 | [V] |
| DUAA s.80 Arts 22A–D; fully in force 5 Feb 2026, SI 2026/82 | 67 §5 Q4, 68 Q21 | [V] |
| Art 22B special-category conditions | 67 §5 Q4 | **[X]** 67 said "explicit consent or contract/legal necessity"; text requires (contract *or* required/authorised by law) **and** Art 9(2)(g), and bars reliance on Art 6(1)(ea) |
| JSP 936 Part 1, 13 Nov 2024, 41 pp | 67, 68 Q20 | [V]; "expects in-service monitoring" (68 Q14) not a quoted clause → tagged [A] |
| Surveillance Camera Code updated, in effect 12 Jan 2022, 12 principles, police + local authorities | 67 §5 Q5, 68 Q22 | [V] |
| Orin NX 18× 1080p30 H.265 decode; 10–12 cams/NX, 4 NX for 40 cams | 67 §2 Q1, 68 Q9/Q10/RF4 | [V] via FACTS l.308/413 (nvidia.com, fetched by AUDIT_43-47); 40/18 → 3 NX decode-only, 40/12 → 4 NX: arithmetic consistent across 38/60/67/68 |
| PSTI SI 2023/1007 in force 29 Apr 2024; s.54 scope | 67, 68 Q22 | [V] in 67's own pass; 68 consistent |

## 2. Numbers and derivations

- H33: 338 simulated worlds, 10/10 vs 6/10, −0.035, floor 0.248–0.263 — match FACTS; 67 rounded
  the floor to "0.25" and omitted "per-world expected FA" → fixed.
- H32 step 0 (69 §7) recomputed from JSON: vis noise p10–p90 0.147–0.309, IR 0.061–0.232; luma
  89.7 vs vis median 33.6; night_ir luma 15.6, DR 64, entropy 4.8, mtf 0.509; in-band 4/14 → 3/13
  vis, 3/14 → 2/13 IR — all match. "Two orders of magnitude" for 0.001 vs ≥ 0.061 is ~60× → fixed.
  Q&A 4 "real 0.15–0.22" was the two medians, not a band → relabelled.
- 68: all 60+ numbers found in FACTS (ByteTrack/BoT-SORT, CAL, DORI, Johnson, SAHI, H1–H22,
  0.36M tokens, 4,006 ACDC, 7–59 % coalescing from 52/H12 row) except the misuses below.
- 2.915 × 40 = 116.6 + true alarms ≈ 120/h (H22) consistent; rule of three 3/0.001 = 3,000 cam-h.

## 3. Fixes (in place)

| # | doc | problem | fix |
|---|---|---|---|
| 1 | 67 §5 Q2 | "GBM ≈ −33 % FA at recall 0.80 (58)" — **no source anywhere**; FACTS: track-only GBM was **+6.8 %** vs A1 | replaced, retired |
| 2 | 67 §5 Q4 | Art 22B special-category conditions wrong (see §1) | rewritten from statute |
| 3 | 69 §4, Q&A 2 | LLVIP "pre-trained on colour" false; 0.965/0.908 quoted without detector/training | YOLOv5, trained per modality, one dataset, AP 0.527/0.670 added |
| 4 | 68 Q5 | "40.1 on LTCC vs near-perfect on PRCC — 45-point drop" compared two datasets | drop is within PRCC (55.2 vs 100); LTCC stated separately |
| 5 | 67 §2 Q7, 68 Q6, 68 critique | night realism 3/14 quoted after 69 showed renders not dark and 3/13 vis / 2/13 IR vs a real reference; 69 said it "qualifies 68 Q6" but 68 was not updated | both updated; H11 "darkness barely matters" now "untested" |
| 6 | 67 §3 Q8, §5 Q2; 68 Q12 | zone context "−21 % FA" read as vs A1 (AUDIT_65 #5 recurrence) | "vs track-only GBM arm B, P8 ≥ 25 % failed, per-site profile" |
| 7 | 68 Q15 FU1 | "at 10 s dwell_25 falls to 0.125" placed after actor-aware 0.367 — 0.125 is window-only | labelled window-only |
| 8 | 68 Q17 | "entirely via DetA … AssA did not move" | AssA −0.0051 (CI spans 0), 3/5 seeds |
| 9 | 68 Q9 FU2, Q14 FU2 | "capability reduced" — not a SAPIENT state (AUDIT_65 #6 recurrence) | `StatusReport` coverage / `NOT_DETECTING`; plain wording in Q14 |
| 10 | 67 §3 Q1, §5 Q1 | "~3,000×" vs FACTS/60/65 "~2,900×" | normalised |
| 11 | 69 Q&A 4, 8; §6 | "night numbers were a sensor-model artefact" (overclaim); "conformal per band (H33) holds the budget" (H33 not per band, simulated); "fusion is how sites hit single-digit FA" unsourced | hedged; [A] |
| 12 | 69 header, 68 Q14, Q22 | "weakest answer" (Q6 is #2 in 68's own critique); JSP 936 monitoring claim; Commissioner claim | corrected / tagged [A] / "secondary source" |

## 4. Scores (×10 per criterion, total scaled to 100)

| doc | numeric vs FACTS | primary-source claims | overclaim (hostile ML lead) | cross-doc consistency | tagging | before | after |
|---|---|---|---|---|---|---|---|
| 67 | 8 | 7 | 8 | 7 | 9 | **78** | **96** |
| 68 | 8 | 9 | 7 | 7 | 8 | **78** | **96** |
| 69 | 9 | 7 | 7 | 8 | 9 | **80** | **96** |

Residual (not fixable without new work): HSE ALARP pages still 404 [X]; Def Stan 05-138 Issue 4
CE floor unread [X]; 69 §1–2 vendor/physics figures remain [A] by design; KAIST MR figures [A].
