# AUDIT_70_73 · Clothes-change ReID (70), tracking sim-to-real (73), docs/13 "Box aspect"

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** the H17 row (+0.034 DetA, AssA −0.005) is pre-parity and unequal-step (AUDIT_M1_PARITY, R53); 73's 'only through detection' was later narrowed to synthetic data by AUDIT_H24.

Audited 2026-09-27 against `898d45e`. Method as AUDIT_67-69: every number grepped in
`FACTS_VERIFIED.md` / `32`, derived numbers recomputed, primary sources re-fetched (arXiv
abstract/HTML/PDF via WebFetch; PDFs text-extracted with `pdftotext -layout`).

## 1. Recomputation

`scripts/box_aspect_tracking_stats.py` re-run (2 min 42 s CPU) into scratch: `results.json`
**identical** to `out/experiments/box_aspect/results.json`. Checked from it:

| claim | recomputed | verdict |
|---|---|---|
| pooled ≥ 50 px 1.138 [1.062, 1.213]; bins 1.221 / 1.004 / 1.119; amodal 1.237 | same | [V] |
| 5.4 vs 123.5 people/frame, p90 9 vs 197 | same — but over **occupied** frames only; 202 of 3,300 v8 frames are empty → 5.05 per rendered frame | [V], definition added |
| "23× sparser" | 123.5/5.4 = 22.9 (24.5 per rendered frame) | [V], both shown |
| 0.915 vs 0.572; 2.4 % vs 44 % (18×) | same; 44/2.4 = 18.3 | [V] |
| 10 vs 25 fps | v8 `render_*.json` fps 10.0; MOT20 seqinfo 25 | [V] |
| 51 vs 140 px | median over **all visible boxes** (tracking stats), not the aspect sample | [V], docs/13 wording clarified |
| gaps/track 0.60 vs 0.05 (12×) | 0.60/0.048 = 12.5 | [V] |
| "12 cameras" | 4 + 2 + 3 + 2 = **11** | **[X] fixed** |
| 5 fps walker "~9 px of a 15 px box" | 0.28 m × ~29 px/m ≈ 8 px; box w ≈ 0.38 × 50 ≈ 19 px | [X] fixed |
| H29 cost 460 × 2 × 8 × 4 ≈ 30k; SE 0.3/√10 = 0.095, /√40 = 0.047; DLCR +11.3/+7.2 | arithmetic holds | [V] |
| "300 identities ÷ 16 bodies ≈ 19" | H29 is 460 ids → ~29 | [X] fixed |
| "3–6 rank-1 points per paper" | successive Table 1 rows: +2.7, +3.9, +2.5, +1.9, +2.3, +5.9 | [X] → 1.9–5.9 |
| H17 +0.034 DetA, AssA −0.005, IDsw +11 | matches FACTS l.196 and `32` §H17 | [V]; IDsw CI [−0.2, +19.6] now stated where "brings ID switches" is claimed |

## 2. Primary sources re-fetched

| claim | source | result |
|---|---|---|
| CAL PRCC 55.2/55.8 vs SC 100/99.8; body-only 24.5 (baseline 18.7) | 2204.06890 PDF Table 6 | [V] numbers; **"about half of CAL's CC score is the head" is our inference** — CAL's authors read Table 6 as body-shape gain. Tagged [INF], mAP 25.4/20.4 added |
| Ortho-ReID PRCC CC 74.4/70.2, all Table 1 rows, DIFFER footnote 54.6 | 2606.11661 HTML | [V]; abstract "+5.9 top-1" = 74.4 − 68.5 ✓. Marked preprint in Q3 |
| MEVID CAL 52.5/27.1, SC 56.6/39.0, DC 3.5/4.3, diff-loc 35.0/22.2 | 2211.04656 HTML | [V] |
| GaitBase SUSTech1K 81.46 → 49.60 / 25.92; P3D 83.53 → 46.28 / 27.30 | 2303.03301 Table 5 | [V] |
| DeepGaitV2 GREW 77.7 (P3D) – 79.4 (3D); GaitBase 60.1; 2D rank-10 86.1 | 2303.03301 Table 4 | [V] |
| P3D "2.9 GFLOPs per sequence" | footnote 2: **per silhouette image, backbone only** | **[X] fixed** (~90 GFLOPs / 30-frame sequence [INF]) |
| MOTSynth "IDF1 53.8 vs 58.1, IDF1 down 4.3" | 2108.09518 Table 6 | **[X]** 53.8 = MOTSynth FT *without* ReID, 58.1 = COCO FT *with* Market ReID. Like for like 50.3/59.8 vs 48.3/58.1 (+1.7 IDF1). `24` and FACTS l.127 had already retired this; 73 re-introduced it in §2, §3.1 and Q1 |
| ByteTrack 80.3/77.3/63.1, "1 to 10 points" IDF1 | 2110.06864 abstract | [V] |
| BoT-SORT 80.5/80.2/65.0 | 2206.14651 abstract | [V]; Q8 now notes ReID + CMC + KF are not separated |
| Deep OC-SORT MOT20 63.9 (1st), MOT17 64.9 (2nd), DanceTrack 61.3 | 2302.11813 abstract | [V] |
| PersonPath22 236 videos, amodal + visible, "order of magnitude larger", severe-occlusion tag | project page | [V] |

## 3. Fixes (in place)

| # | doc | problem | fix |
|---|---|---|---|
| 1 | 73 §2, §3.1, Q1 | MOTSynth "IDF1 down 4.3 — same shape as H17" (no-ReID vs ReID) | like-for-like +2.0/+1.7; MOTSynth has no DetA/AssA split; ReID model moves IDF1 most |
| 2 | 73 §3.2, §8 | "12 cameras" | 11 |
| 3 | 73 §3.2 | people/frame undefined (empty frames excluded) | row split: occupied 5.4 (23×) vs rendered 5.05 (24×) |
| 4 | 70 §5 | DeepGaitV2-P3D 2.9 GFLOPs "per sequence" — understates edge cost ~30× | per frame, backbone only |
| 5 | 70 §1.2, FACTS l.112 | "about half of CAL's CC score is the head" as [V] | [INF] with authors' opposite reading |
| 6 | 73 §2 HOTA, Q5 | H9 cam_sub 0.83 vs 0.51 presented as the MOT20-amodal mechanism | it is our own loose v7 GT (48 B5); MOT20 case [A] |
| 7 | 73 §3.1 | AssA range 0.40–0.72 omitted disguise/far cam_01 (to 0.89); v7 vs v8 unstated | corrected; noted |
| 8 | 70 §2 | "PRCC and LTCC … (152 and 221)" order swapped | 221 and 152 |
| 9 | 70 Q5 | "stature varies only a few cm within a sex" contradicts §6's ~7 cm | SD ~7 cm [A]; ±5 cm keeps ~40 % [INF] |
| 10 | 70 §6, Q7 | 300 ids / ~19 reuses; "360 ids" vs §7's 460 | 460 / ~29; 360 + 100 distractors |
| 11 | 70 §3.1; 73 §5 | "3–6 points per paper"; 5 fps px arithmetic | 1.9–5.9; 8 px of ~19 px |

Propagation: 60/65/68/48 checked — none quoted the MOTSynth 53.8/58.1 pair, 12 cameras or the
FLOPs; 68 Q-FU3 (5.4 / 0.92 / 123.5 / 0.57 / 10 vs 25 fps) and 48's "14 % narrower" (H6
0.865) are correct as written. FACTS: crowd row extended (11 cams, occupied-frame
definition, bit-exact re-run); new rows for DeepGaitV2 Tables 4–5 + FLOPs basis and the
MOTSynth Table 6 re-fetch. docs/13 box-height basis clarified. 00 index updated.

## 4. Q&A traceability

73 Q1–Q10: every number traces to FACTS (H17 l.196, box aspect l.197, crowd l.198) or `32`
§H9 or a fetched abstract, after fix 1 (Q1) and fix 6 (Q5). Q7/Q9/Q10 are design [A] by
nature. 70 Q1–Q10: CAL, Ortho-ReID, MEVID, DLCR, DeepGaitV2/SUSTech1K all [V] above; Q5
stature [A]; Q6 licences [V] per §2 table except PRCC/LTCC [A] (pages did not load — unchanged);
Q7 H20 now cited to `32`.

## 5. Scores (×10 per criterion, total scaled to 100)

| doc | numeric vs FACTS | primary-source claims | overclaim | cross-doc consistency | tagging | before | after |
|---|---|---|---|---|---|---|---|
| 70 | 8 | 8 | 8 | 9 | 9 | **84** | **96** |
| 73 | 7 | 7 | 7 | 8 | 9 | **76** | **95** |
| docs/13 Box aspect | 10 | – | 9 | 9 | 9 | **93** | **97** |

Residual: PRCC/LTCC licence pages still unloaded [A]; MIPL table unread; MEVID annotation
licence unconfirmed; 73 §5 and the "MOT20 cameras are high and steep" view-geometry claim remain [A].
