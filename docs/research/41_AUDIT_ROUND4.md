# Audit round 4: applying round 3 and clearing the AUDIT_01-16 queue

Date: 2026-09-26. The round-3 corrections recorded in `39_AUDIT_ROUND3.md` were
written up but never applied. This round does two things:

1. It applies those corrections to R01–R06, D01–D08, H01–H02 and `FACTS_VERIFIED.md`.
2. It works through the remaining open rows of `AUDIT_01-16.md`, trying other hosts where the first one was blocked.

Edits in the dossiers carry the tag `[audit R3 2026-09-26]` or `[audit R4 2026-09-26]`.

**Method.** I fetched primary pages directly, and used mirrors where the primary was blocked:
- arXiv, for the html version, a specific PDF version, or several versions compared
- the DocumentCloud per-page text of a GAO report
- PMC and A*STAR OAR, as mirrors for MDPI abstracts (MDPI returns 403)
- the OJP/NCJRS abstract, as a mirror for the UCL PDF (which returns 403)
- GitHub READMEs, fetched raw
- researchers' homepages

As before, a search snippet does not count as confirmation.

## A. Round-3 corrections, now applied (22 dossier edits)

| # | Where | Change |
|---|---|---|
| 1 | R03 §3.2 table header | now reads "UCF-Crime frame **AUC** (not XD-Violence AP)", with an explanatory note under the table |
| 2–6 | R03 rows UR-DMU, MGFN, LAVAD, Holmes-VAU, ASK-HINT | each row keeps its UCF-Crime AUC and gains the paper's XD-Violence number with the correct metric: 81.66 AP, 80.11 AP, 62.01 AP / 85.36 AUC, 87.68 AP, 90.31 AUC |
| 7 | R03 §3.3 | 85.67 AP (A+V, Table 1, +2.27 over MACIL-SD's 83.40) marked confirmed |
| 8 | R04 thermal list | FLIR ADAS changed from "~13,000 aligned pairs" to v2 counts: 26,442 frames, 9,711 thermal + 9,233 RGB, 7,498 1:1 matched; the ~5,142 aligned subset is flagged snippet-only |
| 9 | R04 §5.7 | UnrealZoo 53.46 FPS at 2K marked as a README claim (the paper reports only 640x480) |
| 10–12 | D08 (three places) | the same UnrealZoo README-only caveat |
| 13–14 | D05 TrueNorth | "70 mW" replaced with 63 mW (Science) / 65 mW (TCAD); the lesson paragraph updated |
| 15 | D05 Loihi 1 | tagged secondary-only |
| 16 | D05 Tianjic | cores and neurons tagged secondary (Frontiers review); die area tagged snippet-only |
| 17 | D05 Xylo | tagged confirmed (secondary) |
| 18 | R02 TrackTacular | 92.7 / 79.64 replaced with Wildtrack 91.8/95.3 and MultiviewX 92.4/85.6 |
| 19–20 | R02 ACR | withdrawn paper: quote and reference-list link removed, with a note left in their place |
| 21 | R02 UDA takeaway | "~49 mAP unsupervised on MSMT17" depended on ACR; replaced with Cluster Contrast 33.0 mAP / 62.0 R1 (PPLR camera-aware 42.2 / 73.3), taken from the Cluster Contrast PDF table; "two-thirds of the gap" changed to "roughly half" |
| 22 | FACTS_VERIFIED | new "Rounds 3–4 resolutions" table; LAVAD moved out of snippet-only; Tianjic die area and FLIR aligned subset added to snippet-only |

## B. The five "still unverifiable" items from round 3, chased again

| claim | host tried | verdict | finding |
|---|---|---|---|
| PSC-Net "11.92 R / 47.88 HO" (R01, H01) | arXiv PDF **v1 of 2010.10744** (MSFM) and of 2001.09252 | **corrected (misattributed)** | 11.92 / 47.88 is **MSFM-Net's VGG-16 baseline** (ablation table and text: "baseline detector obtains a log-average miss rate of 11.92% on R set … outperforming the adapted FasterRCNN baseline by 0.89%"). It is not a PSC-Net number. PSC-Net's own baseline is 13.8 / 56.8. R01 and H01 fixed. |
| MSFM "8.1 / 43.0 / 8.1 / 5.2" (R01, H01) | 2010.10744v1, 2001.09252 (current and v1); exact-phrase web search | **still unverifiable → removed** | The values are in neither paper. A search snippet repeats the sentence but names no paper. Removed from R01 and H01, because the 4–5x HO/R conclusion stands on 11.92 / 47.88 alone. |
| AI City "77.7 incl. 10 % bonus" (H01, R02) | arXiv html of the 8th AI City paper (2404.09432v1); PoseTrack GitHub README; 9th challenge (2508.13564v1) | **source found; not official** | The organisers' Table 1 lists Yachiyo 71.9446 (offline, rank 1) and SJTU-Lenovo 67.2175 (online, rank 2). The 10 % online bonus is confirmed (§3.1, §4.1). "Adjusted score becomes 77.7258" appears only in the team's own README, and it is arithmetically inconsistent with 67.2175 × 1.1 = 73.94. For comparison, 2025 Track 1: ZV 69.91 (offline). R02 (two places) and H01 now quote the organisers' numbers. |
| Keval & Sasse 13 / 38 / 13 (D06) | OJP/NCJRS abstract | **confirmed** | "13 managers and 38 operators at 13 CCTV control rooms" plus the five failure factors, verbatim |
| Isaac Sim GCC 11 (D08) | raw README on GitHub | **confirmed, with a nuance** | "Building with Ubuntu 24.04 requires GCC/G++ 11 … GCC/G++ 12+ is not supported". The constraint applies to building from source; D08 now says so. |

Two items remain open from round 3:
- **Loihi 1** and **Tianjic** primary figures. IEEE Micro and the Nature full text are paywalled, and no author preprint was found. Both are tagged secondary.
- **Tianjic die area** (3.8 × 3.8 mm) is still snippet-only.

## C. AUDIT_01-16 open queue

| claim | host | verdict | finding / action |
|---|---|---|---|
| [R05] GAO "803 towers; 2,300 by 2034" | DocumentCloud page text of **GAO-26-108118** (the gao.gov PDF is >10 MB) | **confirmed; the report contradicts itself** | p.98: "The IST program consists of 803 fielded towers…". p.99: "IST currently has 830 fielded towers and plans to deliver another 175 … FOC in March 2034 … 2,300 towers". EFF and Reason use 830. R05 and D06 annotated; the safe phrasing is "~800+ fielded, 2,300 by March 2034". |
| [R05] mmWave 98.86 % / 95.45 % | PMC12944725 | **confirmed** | abstract verbatim; 60 GHz; *Sensors* 2026; counting covers 0–3 persons only |
| [R05] φ-OTDR "NAR reduced by >90 %" | A*STAR OAR record (MDPI 403) | **confirmed (abstract)** | the wildlife-limitation sentence is body text, not re-read; it stays unconfirmed |
| [R02] ROGLE 76.93 / 65.20 | arXiv html 2606.01825v1 | **confirmed** | tag added in R02 |
| [D01] Trafalgar Square 1960 | Professional Security (Rowe, 2022), citing National Archives MEPO 2/9956 | **confirmed (secondary)** | 19–20 July 1960, Thai state visit; Guy Fawkes demonstration planned. Timeline row updated. |
| [D01] Times Square 1973 | notbored.org NYC timeline | **confirmed (secondary, activist source)** | "pilot … abandoned after 18 months … 10 arrests"; no NYPD primary found |
| [D02] Ošep TUM → NVIDIA | aljosaosep.github.io; TUM DVL | **confirmed** | Senior Research Scientist, NVIDIA; RWTH PhD; TUM from Aug 2019; also CMU RI |
| [D02] Laptev INRIA → MBZUAI | mbzuai.ac.ae faculty page (search) | **confirmed** | Professor at MBZUAI from 2023; led WILLOW 2021–23 |
| [D02] Sivic INRIA → CIIRC | ciirc.cvut.cz | **confirmed** | Professor at CIIRC CTU; ERC Advanced Grant 2022 |
| [D02] Fleuret (Geneva) | fleuret.org bio | **confirmed** | Full Professor, University of Geneva, and Meta FAIR |
| [D02] Benenson ex-MPI → Google | research.google profile | **confirmed** | post-docs at KU Leuven and MPI-INF; Google since 2016 |
| [D02] Hogg (Leeds) + Hogg–Cohn event models | Leeds staff page; search record | **confirmed; citation corrected** | the reading-list item "Lichtenauer / Hogg & Cohn" is wrong. The paper is Fernyhough, Cohn & Hogg, IVC 2000 (with follow-up work in JAIR 2015). |
| [D02] v2e from Delbruck's group | v2e README | **confirmed** | Hu, Liu & Delbruck, INI, CVPRW 2021 |
| [D02] Gül Varol "SURREAL-lineage" | arXiv 1701.01370 | **confirmed, stronger** | she is SURREAL's first author |
| [D06] Keval & Sasse | OJP | confirmed | see B |
| [D08] Isaac Sim GCC 11 | GitHub | confirmed | see B |

**Not attempted this round** (low interview stakes, or too many to cover):
- The remaining ~35 `[VERIFY]` tags in D02: reading-list venues, "Not searched" watch-lists, Hauptmann/ActEV, Jia Deng.
- About 30 `[VERIFY]` tags in D01: corporate chains and product dates.
- The D06 Code of Practice dates ("laid 16 Nov 2021, in force 12 Jan 2022"). These were already quoted from gov.uk in D06 §2.2. The Lords Library page 403s.
- R05's STANAG 4676, Mixpeek 0.470, and DAS 60.4 %.

The i-LIDS 10 s window was already verified verbatim (FACTS row 20).

## Tally

| | count |
|---|---|
| Round-3 corrections applied to dossiers | 22 |
| Round-4 dossier edits (R01 1, H01 2, R02 4, D06 2, D08 1, D02 8, D01 2, R05 3) | 23 |
| New verified FACTS rows | 20 (plus top-40 item 11 rewritten; 2 snippet-only rows added, 1 moved out) |
| Items still unverifiable | 5: MSFM 8.1/43.0 (removed from text), Tianjic die area, Loihi 1 / Tianjic primary counts, φ-OTDR wildlife sentence, Times Square 1973 primary |

## Conclusion-changing
- **CityPersons occlusion pair:** keep the numbers but change the attribution. 11.92 / 47.88 is MSFM-Net's baseline, not PSC-Net.
- **Unsupervised ReID on MSMT17 is ~33 mAP, not ~49.** The 49 came from a withdrawn paper, and the gap to supervised (~76) is larger than the dossier claimed.
- **AI City 2024:** the best online system is 67.22 raw — 2nd by HOTA but the official winner (online rule); Yachiyo 71.94 is runner-up. Do not quote 77.7.
- **GAO towers:** the report gives both 803 and 830. Quote the range and cite the page.
