# Adversarial accuracy audit — reports 48–51 (2026-09-26)

Method as in AUDIT_43-47: every checkable claim treated as wrong until its
primary source was fetched (arXiv/CVF PDFs via `curl` + `pdftotext`, Crossref
API DOI records, Europe PMC / PMC full text, BSI Knowledge, nsi.org.uk, the
NPCC 2024 PDF) or, for 48, found in a **committed** repo file with its hash.
Worked statistics in 49 were recomputed with scipy (`.venv`). Publisher DOI
landing pages (Wiley, T&F, OUP, JSTOR) are Cloudflare-gated to `curl`, so
bibliographic facts come from Crossref metadata. No editor or GPU used.

## Scores (confirmed / total claim rows)

| Report | Confirmed | Total | Score | Commit |
|---|---|---|---|---|
| 49 evaluation statistics | 19 | 20 | 95 % (1 corrected; 7 [NF] → [V]) | `95834d3` |
| 50 evasion / tamper (spot-check + weak rows) | 7 | 8 | 88 % (1 corrected) | `b69bfea` |
| 51 operator human factors | 9 | 11 | 82 % (1 withdrawn, 1 upgraded) | `1efb315` |

## Corrections that change conclusions

* **50 Ribnick 2006**: the "3.1 % missing / 7.8 % false alarms" figures (from
  a search snippet) are **not in the paper**. Body fetched: 20 real tamper
  events, optimal thresholds → 5 false alarms, 1 miss (95 % detected, 79.2 %
  of alarms true); 4/5 false alarms were lights switched off. DOI
  10.1109/AVSS.2006.94.
* **51 NSI ARC Gold**: the cited 2018 criteria PDF is 404; the "BS 5979 or
  BS 8591 incl. BS EN 50518" wording is withdrawn. Current NSI page lists
  BS 5979, BS 8418, BS 8484 + ISO 9001.
* **51 BS 9518** now [V] from BSI: published 31 Jul 2021, supersedes BS 8591:2014
  (withdrawn 31 Jul 2022), scope explicitly includes video surveillance
  systems, complements BS EN 50518:2019.
* **49 Welch** t ≈ 5.5 on 3.2 df (was 5.6 / 3.3); p 0.010 unchanged in effect.
* **50 Ma 2026** 0.925 @ FPR 0.025 is confirmed but is a non-held-out sweep
  ("sensitivity diagnostic", authors' words) — caveat added.

## Recomputed worked numbers (49)

| quantity | doc | recomputed | verdict |
|---|---|---|---|
| Wilson 95 % for 8/10 | [0.49, 0.94] | 0.490–0.943 (Clopper–Pearson 0.444–0.975) | confirmed |
| 2(z.975+z.8)² | 15.7 | 15.698 | confirmed |
| seeds, σ 0.025, Δ 0.02 / 0.05 | 25 / 4 | 24.5 / 3.9 | confirmed |
| rule of three −ln 0.05 | 3/T | 2.996/T; 0.35 h → 8.56, 400 h → 0.0075, 3 000 h → 0.0010 | confirmed |
| Garwood upper, k=1, 3 000 h | 0.0019 | χ²₀.₉₇₅(4)/6000 = 0.00186 | confirmed |
| permutation 3-vs-3 | 1/20 | C(6,3)=20 | confirmed |
| Spearman n=4 perfect | 1/24 = 0.042 | 1/4! | confirmed |
| σ CI from n=3 | 0.5–6.3 σ̂ | 0.52–6.28 | confirmed |
| t-interval synthetic | [0.090, 0.214] | ±0.0621 | confirmed |
| paired t | −5.8, p 0.03 | −5.77, p 0.029 | confirmed |
| Welch | 5.6, 3.3 df | 5.47, 3.19 df, p 0.010 | **corrected** |
| far-band SE, n=15 | 0.13 | 0.129 | confirmed |
| Δ/s_d for 80 % power | 2.8 | 2.80 | confirmed |
| (0.015/0.007)² | 4.6× | 4.59 | confirmed |
| 5 seeds resolve Δ | 0.045 | √(15.7·0.025²/5)=0.0443 | confirmed |

## [NF] → fetched citations (49)

Efron 1979 *Ann. Statist.* 7(1) doi:10.1214/aos/1176344552 · Künsch 1989
*Ann. Statist.* 17(3) doi:10.1214/aos/1176347265 · Wilson 1927 *JASA*
22(158):209–212 doi:10.1080/01621459.1927.10502953 · Garwood 1936 *Biometrika*
28(3–4):437–442 doi:10.1093/biomet/28.3-4.437 · Cohen 1988 (Routledge reissue)
doi:10.4324/9780203771587 · Benjamini & Hochberg 1995 *JRSS-B* 57(1):289–300
doi:10.1111/j.2517-6161.1995.tb02031.x · Page 1963 *JASA* 58(301):216–230
doi:10.1080/01621459.1963.10500843. All via `api.crossref.org/works/<doi>`.

## Claim tables

### 48 — "Numbers you must have in your head"

| # | source | verdict |
|---|---|---|
| 1–3 | `git show 5e5f53d:32` (0.276, 0.152 (0.025), per-seed; 0.073→0.007) | confirmed |
| 2 | 32 H1 seed table; FACTS | confirmed |
| 4 | `d0d00ac` subject + 32 §H2 | confirmed |
| 5–6 | 32 §H3 (0.021/0.405/0.629, 156.2 vs 21 ms; degraded 0.209 vs 0.830) | confirmed |
| 7–8 | FACTS l.172 (`5e5f53d`) | confirmed |
| 9 | FACTS l.173 | confirmed |
| 10 | 32 §H5 table (0.091 → 0.250) | confirmed |
| 11–12 | FACTS l.174, `4eac637` | confirmed |
| 13 | FACTS l.175, docs/12 l.1200, `8c3b03b` | confirmed |
| 14 | docs/12 l.1204 (`8c3b03b`); 16 bodies `9c87424` | confirmed, hash re-attributed |
| 15 | AUDIT_43-47 (47) | confirmed |
| 16 | docs/13 l.81/293, FACTS l.176, `be9f52a` | confirmed |
| 17–20 | AUDIT_43-47 corrections | confirmed |
| 21 | CLAUDE.md principle 5 | confirmed |
| 22 | 3/30 = 0.1 | confirmed |
| 23–24 | docs/12 l.1038/1078/1182–1183; 1 258 in 32 | confirmed |
| 25 | FACTS / 47 | confirmed |

### 49

Rows: the 15 recomputations above (14 confirmed, 1 corrected) + 5
external-citation rows (Holm, Demšar, Guo, Nixon, Bouthillier — already [V]
in the draft, not refetched; counted confirmed on the prior fetch).

### 50 (spot-check)

| claim | source fetched | verdict |
|---|---|---|
| Thys: OBJ recall 26.46 % (CLEAN 100, NOISE 87.14) | arXiv 1904.08653 PDF Table 1 | confirmed |
| Xu: 74 % digital / 57 % physical vs YOLOv2 | arXiv 1910.11099 PDF | confirmed |
| Hu 2022: mASR 0.791 @1.6 m → 0.257 @7.0 m | arXiv 2203.03373 PDF suppl. | confirmed |
| Zhu 2021: AP drop 34.48 % | arXiv 2101.08154 PDF | confirmed |
| Ma 2026: 0.925 recall @ FPR 0.025; 9.09 cam-h zero FA | arXiv 2607.14760 PDF | confirmed + caveat |
| Wu 2020: YOLO→Faster R-CNN transfers, not reverse; shirts ~50 % don't transfer | arXiv 1910.14667 PDF | confirmed |
| Hu 2021 ICCV abstract "competitive attack performance" | CVF PDF | confirmed (upgraded from search index; Table 1 figure added) |
| Ribnick 3.1 % / 7.8 % | AVSS 2006 body | **corrected** |

### 51

| claim | source fetched | verdict |
|---|---|---|
| NPCC 3 false calls / rolling 12 months | NPCC 2024 PDF l.452/459 | confirmed |
| CCTV thresholds same as IAS | l.500 | confirmed |
| 90 days free of false calls | l.482 | confirmed |
| keyholder 20 min | l.302 | confirmed |
| Donald 2015 50 % | FACTS / Europe PMC | confirmed |
| BS 9518 supersedes BS 8591 | BSI Knowledge | confirmed (upgraded from secondary) |
| NSI Gold requires BS 5979/8591/50518 | PDF 404; NSI page | **withdrawn** |
| Mackworth 10–15 % in 30 min | Wikipedia (paper paywalled) | confirmed-secondary |
| Wolfe 7/16/30 % | PMC4224304 | confirmed (new) |
| Parasuraman & Manzey complacency | Europe PMC abstract | confirmed (new) |
| Wickens / NASA-TLX | Crossref + S2 / Wikipedia | confirmed (new) |

## Residual weak points

* Mackworth numbers rest on Wikipedia; paper body paywalled.
* Hu 2021 Table 1 values beyond the YOLOv2 column not trusted (pdftotext).
* 51's operator-utilisation worked example keeps two illustrative inputs
  (16 cameras, 14 h armed; 20 s verify; 2 intrusions/yr) tagged [INF].
* 49's Holm/Demšar/Guo/Nixon/Bouthillier rows were not refetched this pass.
