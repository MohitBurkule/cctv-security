# Audit of 54 (2026-09-26)

Method as `AUDIT_52-53.md`: every checkable number re-fetched from the primary
source (arXiv abstract / arXiv API, raw GitHub README, vendor page,
legislation.gov.uk). Score = share of checkable claims correct.

## Score: 8.5/10 before, 9.5/10 after

~50 numbers checked; 8 corrections applied in place.

| # | Claim in 54 | Finding | Source |
|---|---|---|---|
| 1 | YOLO26 n 40.9 / x 57.5, n CPU 38.9 ms, T4 1.7 ms | [V] exact (38.9 ± 0.7) | docs.ultralytics.com/models/yolo26 |
| 2 | YOLO11 39.5 / 54.7, 56.1 ms; −31 % CPU | [V] | docs.ultralytics.com/models/yolo11 |
| 3 | "at equal T4 latency YOLO26 gains +1.4–2.8" | **Fixed**: n (+0.2 ms) and x (+0.5 ms) are not equal-latency; now "size for size" | same |
| 4 | RT-DETRv3 48.1 / 54.6, v1 13 Sep, v3 19 Dec 2024 | [V] | arXiv 2409.08475 |
| 5 | D-FINE L 54.0 @124, X 55.8 @78, O365 57.1 / 59.3, N 42.8 @472 | [V] | arXiv 2410.13842, D-FINE README |
| 6 | DEIM-D-FINE 43.0/49.0/52.7/54.7/56.5, 59.5 O365 | [V] | DEIM README |
| 7 | DEIMv2 S 50.9 / 9.7 M / 5.78 ms, X 57.8 / 50.3 M / 13.75 ms, custom licence | [V] | DEIMv2 README, arXiv 2509.20787 |
| 8 | YOLOE +3.5 AP over YOLO-Worldv2-S, 3× / 1.4× | [V] | arXiv 2503.07465 |
| 9 | DINO-X 56.0 / 59.8 / 52.4 | [V] | arXiv 2411.14347 |
| 10 | SAM 3 arXiv 20 Nov 2025, rev. 28 Mar 2026 | [V] | arXiv 2511.16719 |
| 11 | SAM 3 "54.1 cgF1 LVIS instance seg, 48.5 AP COCO box" | **Fixed [X]**: 54.1 is SA-Co/Gold instance cgF1; 48.5 is LVIS mask AP; COCO box is **56.4 AP**. 55.7 is SA-Co/Gold box cgF1 (and COCO AP_o) | raw sam3 README table |
| 12 | SAM 3 repo "March 2025" | **Fixed**: the 27 Mar 2026 repo line is SAM 3.1 | sam3 README |
| 13 | MAT 71.3 / 72.2 / 41.6; SelfMOTR 69.2 / 71.1; MeMoSORT 67.9 / 82.1; OA-SORT 63.1 / 64.2; StableTrack +11.6 % @1 Hz; SAM2MOT +2.1 / +4.5; SMP 87.2 | [V] | arXiv abstracts |
| 14 | DOA-SORT "DanceTrack 66.34 HOTA" | **Fixed**: validation split (baseline 63.00) — not comparable with test figures | arXiv 2609.22706 |
| 15 | CC-ReID deltas (DIFFER, RLQ, Colors, 2606.11661), MIPL 74.8, DLCR +11.3, try-on +2.5/+1.1 | [V] | arXiv API |
| 16 | NOVA 89.86 / 95.07 / 84.82, 6 Sep 2026; DeSC 89.37 / 87.18 | [V] | arXiv 2609.06360, 2603.19780 |
| 17 | Latent Clarity 89.94 as UCF-Crime AUC | **Fixed**: chunk-level anticipation AUROC, different protocol | arXiv 2607.03558 |
| 18 | Qwen3-VL 2B–32B, 30B-A3B / 235B-A22B, 256 K native, 26–27 Nov 2025 | [V] | arXiv 2511.21631 |
| 19 | Event/SNN: Sequence-SOD 26.88, SSLA 0.375, SpikingMOT 74.9 / 56.5, Ev-DTAD +0.8/+0.5/+3.0 | [V]; the ANN reference "37.5" has no source in 54 — flagged in text | arXiv API |
| 20 | GenAI camouflage +20.1 / +14.4 | [V] | arXiv 2609.02299 |
| 21 | Thor GA 25 Aug 2025, $3,499, 2,070 FP4 TFLOPS, 128 GB, 7.5× / 3.5× | [V]; newsroom says "FP4" without "sparse" — noted | NVIDIA newsroom |
| 22 | Orin Nano Super 17 Dec 2024, $249 (was $499), 40→67 sparse TOPS, `nvpmodel -m 2` | [V] | NVIDIA blog |
| 23 | Hailo-10H 40 TOPS INT4 / 20 INT8 @ 2.5 W typical, LPDDR4/4X | [V] | hailo.ai product page |
| 24 | DUAA s.80, Sched. 4, s.76/78, s.103, ss.126–128 | [V] | legislation.gov.uk contents |
| 25 | DUAA "Part 6, ss.117–120" Information Commission | **Fixed**: ss.117–119 + Sched. 14 (s.118 abolishes the Commissioner) | same |
| 26 | Q2 "on Thor INT8 slower than FP16 … in our own test" | **Fixed [X]**: SurvSim has no Thor; the 1.52 vs 1.39 ms is Ultralytics' YOLO26n Jetson benchmark cited in 38 | `38` l.144, Ultralytics Jetson guide |
| 27 | Tight GT "0.781→0.884 in progress" | **Fixed**: committed `0213002`/`68ee6d1`; street 0.712→0.911; transfer not improved | `git show 0213002` |

Not re-fetched: EU Reg 2026/1744 dates (EUR-Lex not re-opened this pass),
Hailo AI HAT+ 2 date, AI City 325/245 teams (abstract listing only).
Residual weakness: coverage is arXiv-biased (stated in 54's method note); MOT20
leaderboard still unread.
