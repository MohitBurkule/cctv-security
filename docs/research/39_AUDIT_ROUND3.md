# Audit round 3 — resolving "unverifiable" rows of AUDIT_01-16

Date: 2026-09-26. Method: WebFetch of primary pages (arXiv html/abs, arXiv PDFs
text-extracted locally with `pdftotext`, IBM Research publication page, Europe
PMC REST abstract, vendor pages, GitHub READMEs). Search snippets were never
counted as confirmation. Blocked/unusable hosts: PubMed (reCAPTCHA),
ieeexplore (empty body), WikiChip (socket closed), flir.com old ADAS URL (404),
arXiv 2112.01839 PDF (404 — the paper is **withdrawn**), Intel Loihi 2 brief
(no numbers in page text).

| claim | origin row | source URL fetched | verdict | exact value found + where |
|---|---|---|---|---|
| Hyperbolic AVVD 85.67 AP on XD-Violence | R03 | https://arxiv.org/html/2305.18797 | confirmed | 85.67% AP (A+V), Table 1; +2.27 over MACIL-SD 83.40 |
| LAVAD 80.28 | R03 | https://arxiv.org/html/2404.01014 | confirmed | 80.28% AUC on **UCF-Crime**, Table 1 (XD-Violence: 62.01 AP / 85.36 AUC, Table 2) |
| Holmes-VAU 88.96 | R03 | https://arxiv.org/html/2412.06171 | confirmed | 88.96% AUC on UCF-Crime; 87.68 AP on XD-Violence (results section) |
| UR-DMU 86.97 | R03, H02 | https://arxiv.org/pdf/2302.05160 | confirmed | 86.97% AUC UCF-Crime, I3D (comparison table + text "SOTA AUC score of 86.97%"); XD-Violence 81.66 AP |
| MGFN 86.98 | R03, H02 | https://arxiv.org/pdf/2211.15098 | confirmed | 86.98% AUC UCF-Crime, I3D-RGB (Table, and contributions list); XD-Violence 80.11 AP (VideoSwin) |
| ASK-HINT 89.83 training-free | R03, H02 | https://arxiv.org/html/2510.02155v1 | confirmed | 89.83% AUC UCF-Crime, Table 1 (Qwen2.5-VL-7B frozen); XD-Violence 90.31 AUC, Table 2 |
| UnrealZoo 53.46 FPS at 2K, 100+ scenes, Apache 2.0 | R04 | https://github.com/UnrealZoo/unrealzoo-gym ; https://arxiv.org/html/2412.20977 | confirmed (README) | README: "53.46 FPS at 2K and 29.59 FPS at 4K", "100+ scenes", Apache 2.0. Paper Table 2 reports only 640x480 figures (e.g. 83 FPS colour, 154 FPS mask) and "100 scenes" |
| FLIR ADAS ~13,000 aligned pairs | R04 | https://oem.flir.com/solutions/automotive/adas-dataset-form/ | corrected | Current (v2) page: 26,442 annotated frames; 9,711 thermal + 9,233 RGB train/val images; 7,498 video frames with 1:1 thermal/visible match. No "13,000 aligned". The commonly used *aligned* FLIR subset is 4,129 train + 1,013 test pairs (snippet-only, third-party) |
| TrueNorth 4,096 cores / 1M neurons / 256M synapses / 70 mW | D05 | https://research.ibm.com/publications/truenorth-design-and-tool-flow-of-a-65-mw-1-million-neuron-programmable-neurosynaptic-chip ; Europe PMC abstract PMID 25104385 | corrected (power only) | 4,096 cores, 1M neurons, 256M synapses, 5.4B transistors confirmed. Power: Science abstract "63 mW" (400x240 video @30 fps); Akopyan TCAD title "65 mW". 70 mW is the press/Wikipedia figure |
| Loihi 1 ~130k neurons, ~130M synapses | D05 | https://open-neuromorphic.org/neuromorphic-computing/hardware/loihi-intel/ | confirmed (secondary) | "up to 130,000 ... neurons", "130 million synapses", 128 neuromorphic cores + 3 x86 cores. Davies 2018 primary not reachable (IEEE empty) |
| Tianjic 156 cores, ~40k neurons, 3.8x3.8 mm | D05 | https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2022.959626/full ; Europe PMC abstract | confirmed (secondary) for cores/neurons; area snippet-only | Frontiers review: "156 neural cores, simulating 40,000 neurons and 10,000,000 synapses". Nature abstract gives no counts; 3.8x3.8 mm² only in search snippet |
| Xylo 219 µW idle / 93 µW dynamic | D05 | https://open-neuromorphic.org/neuromorphic-computing/hardware/xylo-synsense/ | confirmed (secondary) | page text: "219 μW idle power", "93 μW dynamic inference power ... audio classification" |
| TrackTacular MOTA 92.7 / IDF1 79.64 | R02 | https://arxiv.org/html/2403.12573 ; GitHub README | corrected | Paper: Wildtrack MOTA 91.8 / IDF1 95.3; MultiviewX MOTA 92.4 / IDF1 85.6. Neither 92.7 nor 79.64 appears. README has no numbers |
| ACR 49.0 mAP / 74.2 R1 MSMT17 | R02 | https://arxiv.org/abs/2112.01839 | corrected (source withdrawn) | Paper is **withdrawn** by author ("experimental results are not sufficient"); PDF 404. Numbers must not be cited |
| MSFM 8.1/43.0/8.1/5.2 MR | R01 | https://arxiv.org/pdf/2010.10744 | still unverifiable | text-extracted tables: 10.12/38.45 etc.; no 8.1/43.0 row |
| PSC-Net 11.92 R / 47.88 HO | R01, H01 | https://arxiv.org/pdf/2001.09252 | still unverifiable | neither 11.92 nor 47.88 in extracted text |
| Keval & Sasse 13/38/13 | D06 | not attempted | still unverifiable | |
| Isaac Sim GCC 11 | D08 | not attempted | still unverifiable | |
| AI City "77.7 incl. 10% bonus" | H01 | not attempted | still unverifiable | round 2 already found 67.22 / 71.94 on 2024 page |

## Conclusion-changing
- **ACR (2112.01839) is a withdrawn paper** — drop the 49.0/74.2 citation from R02.
- **TrackTacular numbers are wrong**: use 91.8/95.3 (Wildtrack) or 92.4/85.6 (MultiviewX).
- **FLIR "~13,000 aligned pairs" is not supported**; cite v2 counts (9,711 thermal / 9,233 RGB + 7,498 paired video frames) and ~5,142 for the aligned subset.
- **UnrealZoo 53.46 FPS at 2K is a README claim, not a paper result** (paper benchmarks at 640x480).
- R03 SOTA table values (LAVAD, Holmes-VAU, UR-DMU, MGFN, ASK-HINT) are all **UCF-Crime AUC**; ensure the table is not labelled XD-Violence. Holmes-VAU XD = 87.68 AP.
- TrueNorth power: 63 mW (Science) / 65 mW (TCAD), not 70 mW.

## Still open
- MSFM and PSC-Net CityPersons values (not in the papers; likely from a different table/version).
- Loihi 1 and Tianjic from the primary papers (IEEE Micro / Nature paywalled); Tianjic die area.
- Keval & Sasse counts, Isaac Sim GCC 11, AI City 77.7, ROGLE, mmWave, GAO towers, i-LIDS 10 s tolerance.
