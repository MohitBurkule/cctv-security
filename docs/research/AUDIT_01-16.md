# Adversarial accuracy audit — dossiers R01–R06, D01–D08, H01–H02 (2026-09-26)

Method: same as AUDIT_17-24.md. For each dossier I sampled the claims an
interviewer would probe (benchmark numbers, dataset sizes and licences,
standards, legal cases, hardware figures, acquisitions, "X % better") and
checked them against primary sources. Wrong claims were fixed in place and
tagged `[audit 2026-09-26]`. Sampling was 7–25 claims per file, not exhaustive.
`motchallenge.net`, `web.archive.org`, bailii, congress.gov and science.org
could not be reached from this machine.

## Scores (confirmed / corrected / unverifiable → accuracy = confirmed ÷ (confirmed + corrected))

| Dossier | Conf | Corr | Unver | Accuracy | Notes |
|---|---|---|---|---|---|
| R01 detection & SCT | 6 | 0 | 2 | 100 % | CityPersons occlusion MRs not found in the cited tables (conclusion holds) |
| R02 MCT & ReID | 6+3* | 2+2* | 3 | 69 % | *round-2 CAL/LTCC/PRCC and CLIP-ReID fixes are counted here |
| R03 behaviour/anomaly | 1 | 1 | 5 | 50 % | thin sample; many SOTA-table AUCs not retrievable |
| R04 degraded & sim2real | 10 | 0 | 3 | 100 % | |
| R05 fusion & NL retrieval | 9 | 0 | 3 | 100 % | |
| R06 the vendor | 3 | 1 | 2 | 75 % | officer count wrong |
| D01 history | 3 | 1 | 1 | 75 % | |
| D02 people & labs | 1 | 2 | 1 | 33 % | attribution errors; many [VERIFY] still open |
| D03 industry | 7 | 1 | 0 | 88 % | |
| D04 deployment | 5 | 0 | 1 | 100 % | mostly arithmetic and standards |
| D05 neuromorphic | 11 | 0 | 5 | 100 % | |
| D06 users & field | 6 | 4 | 2 | 60 % | dates and titles |
| D07 frontier | 6 | 4+1* | 2 | 55 % | |
| D08 simulator craft | 9 | 0 | 1 | 100 % | |
| H01 veteran Q perception | 5 | 1+2* | 3 | 63 % | |
| H02 veteran Q behaviour/ops | 7 | 1+1* | 2 | 78 % | |

## Corrections that change a conclusion
1. **CAL on PRCC is 55.2 % Rank-1, not 64.1 %** (R02, H01, H02, 18). The 64.1 was
   a later method's figure from a 2026 survey. **LTCC is ~40 %, not "the 30s"**
   (00_INDEX, R02, D07, H01). Same-clothes → clothes-changed is a drop of about
   40 points on PRCC, so the "appearance is not identity" point gets stronger.
2. **FarSight gains (R02)**: the 34.1 % / 17.8 % / 34.3 % figures compare the
   2025 system with the earlier FarSight system (arXiv 2505.04616), not fusion
   with a single modality. They no longer directly support "fusion deltas are
   large".
3. **Gait in the wild (D07, H01, 00_INDEX)**: "~50 % Rank-1 on GREW" is out of
   date; OpenGait-era models report ~79–86 %. The lab-versus-field gap is real,
   but "gait collapses in the wild" overstates it.
4. **the vendor (R06)**: public registry lists **four active directors**
   (Livingstone, [person], Matthews from Jul 2026, Eccles-Williams from Aug 2026),
   not "one Director and two Secretaries".
5. **AI City 2024 "77.7 adjusted HOTA" (H01)** does not match the published
   winners page (online 67.22, offline runner-up 71.94). Now tagged [unverified];
   don't quote it.

Minor, non-conclusion corrections: RTFM UCF-Crime 84.30 not 83.30 (R03, H02);
EarlyBird Wildtrack MODA 91.2 / recall 96.3 (R02); i-LIDS has 5 released
scenarios, not "four" (D01, D06); Canon–BriefCam closed 3 Jul 2018 (announced
9 May) (D03); MOTSynth author list and GHOST lineage (D02); HORS 292 is dated
Feb 2005; Procurement Act 2023 (not "2022"); North Hyde fire 20 Mar 2025 (D06);
MLVU GPT-4o 64.6 is the dev set, test is 54.5 (D07); VideoPrism 30 or 31/33
depending on source (D07).

## Claim tables

### Audit G1: R01, R02, R03 (2026-09-26)

| claim | section | source URL | verdict | note |
|---|---|---|---|---|
| [R01] CrowdHuman 470K instances, ~22.6 persons/img, head/visible/full-body boxes | §2 | https://arxiv.org/abs/1805.00123 | confirmed | abstract verbatim |
| [R01] ByteTrack MOT17 80.3 MOTA/77.3 IDF1/63.1 HOTA, 30 FPS V100 | §3.3 | https://arxiv.org/abs/2110.06864 | confirmed | abstract verbatim |
| [R01] BoT-SORT MOT17 80.5/80.2/65.0 | §3.4 | https://arxiv.org/abs/2206.14651 | confirmed | |
| [R01] Deep OC-SORT 1st MOT20 / 2nd MOT17, 63.9/64.9 HOTA, DanceTrack 61.3 | §3.5 | https://arxiv.org/abs/2302.11813 | confirmed | |
| [R01] StrongSORT AFLink + GSI (offline global steps) | §3.6 | https://arxiv.org/abs/2202.13514 | confirmed | |
| [R01] MOTRv2 69.9 HOTA DanceTrack, 14.8% better; 73.4 in challenge | §3.8 | https://arxiv.org/abs/2211.09791 | confirmed | paper body + abstract |
| [R01] MSFM "8.1/43.0/8.1/5.2 MR" on CityPersons occlusion subsets | §2 | https://arxiv.org/pdf/2010.10744 | unverifiable | exact values not found in the PDF tables (these show 6.45/38.01/13.40/2.80 and 10.12/38.45); left as-is because the stakes are low |
| [R01] PSC-Net "11.92 R / 47.88 HO" | §2 | https://arxiv.org/pdf/2001.09252 | unverifiable | PDF tables show e.g. 10.6/50.2 and 9.9/37.2; quoted values not found; the "HO is about 4-5x R" conclusion still holds |
| [R02] AIC23 Track 1 winner: baseline 89.57 → 95.36 IDF1 | §1 | https://arxiv.org/abs/2304.09471 | confirmed | |
| [R02] MVDeTr 91.5 / 93.7 MODA | §2 | https://arxiv.org/abs/2108.05888 | confirmed | Table 1 |
| [R02] EarlyBird +4.6 MOTA / +5.6 IDF1 on Wildtrack | §2 | https://arxiv.org/abs/2310.13350 | confirmed | |
| [R02] EarlyBird "MODA 94%, recall 95.9%" | §2 | https://arxiv.org/abs/2310.13350 | corrected | Table 1: Wildtrack MODA 91.2 / recall 96.3; MultiviewX 94.2 / 95.7. Wildtrack tracking: IDF1 92.3 / MOTA 89.5 |
| [R02] TrackTacular MOTA 92.7 / IDF1 79.64 | §2 | https://github.com/tteepe/TrackTacular | unverifiable | tagged [unverified]; secondary quote |
| [R02] advPattern 87.9→27.1% R1; 47.1% R1 / 67.9 mAP impersonation | §4.2 | https://arxiv.org/abs/1908.09327 | confirmed | PDF verbatim |
| [R02] MultiGait++ +7.6/+4.9 on GREW/Gait3D; CCPG +4.8/+4.2/... | gait | https://arxiv.org/abs/2412.11495 | confirmed | |
| [R02] FarSight: 34.1% TAR gain, 17.8% Rank-20, 34.3% FNIR reduction | fusion | https://arxiv.org/abs/2505.04616 | corrected | the numbers are right, but they come from the 2025 paper (2505.04616) and compare against the *preliminary FarSight system*, not fusion against a single modality. The cited 2306.17206 reports +11.82% R20 / +11.3% TAR@1%FAR |
| [R02] ACR 49.0 mAP / 74.2 R1 on MSMT17 | UDA | https://arxiv.org/abs/2112.01839 | unverifiable | abstract gives no numbers |
| [R02] ROGLE 76.93 / 65.20 R1 | text ReID | arXiv 2606.01825 | unverifiable | not checked |
| [R03] Sultani deep MIL 75.41% AUC; UCF-Crime 128 h | anomaly | https://arxiv.org/abs/1801.04264 | confirmed | PDF verbatim; [to verify] hedge resolved |
| [R03] RTFM 83.30% AUC on UCF-Crime | SOTA table | https://arxiv.org/abs/2101.10030 | corrected | paper reports 84.30 (I3D RGB) |
| [R03] LAVAD 80.28 | SOTA table | https://arxiv.org/abs/2404.01014 | unverifiable | PDF not retrieved |
| [R03] Holmes-VAU 88.96 | SOTA table | https://arxiv.org/abs/2412.06171 | unverifiable | number not in abstract; PDF download failed |
| [R03] UR-DMU 86.97, MGFN 86.98 | SOTA table | n/a | unverifiable | not re-checked |
| [R03] Hyperbolic AVVD 85.67 AP on XD-Violence | XD-Violence | https://arxiv.org/abs/2305.18797 | unverifiable | abstract says only "sizable margin"; PDF fetch failed |
| [R03] ASK-HINT 89.83 training-free | SOTA table | n/a | unverifiable | text already treats it as suspicious |

SCORE R01: confirmed 6 / corrected 0 / unverifiable 2
SCORE R02: confirmed 6 / corrected 2 / unverifiable 3
SCORE R03: confirmed 1 / corrected 1 / unverifiable 5

#### CONCLUSION-CHANGING
- R02 FarSight: the argument "fusion works, the deltas are large" rested on gains that compare system v2 with system v1, not multimodal with unimodal. That quote no longer directly supports the conclusion that fusion helps (edited in place with an audit note).
- No other finding changes a conclusion. The RTFM correction (83.30→84.30) and the EarlyBird detection figures do not change any ranking.

### Audit G2 (R04, R05, R06): 2026-09-26

| claim | section | source URL | status | note |
|---|---|---|---|---|
| [R04] ACDC 8012 images, 4006 adverse, 4 conditions | ACDC | https://arxiv.org/abs/2104.13395 | confirmed | abstract |
| [R04] DAWN 1000 images, 4 weather sets | DAWN | https://arxiv.org/abs/2008.05402 | confirmed | abstract |
| [R04] DAWN 7,845 boxes; class shares 82.21/2.05/8.22/1.36/6.07 % | DAWN | arXiv 2008.05402 PDF | confirmed | paper text |
| [R04] LLVIP 30,976 images / 15,488 pairs | thermal | https://arxiv.org/abs/2108.10831 | confirmed | abstract |
| [R04] M3FD 4,200 pairs | thermal | https://arxiv.org/abs/2203.16220 | confirmed | TarDAL paper |
| [R04] FLIR ADAS ~13,000 aligned pairs | thermal | flir.com | unverifiable | tagged [unverified] |
| [R04] Synthehicle YOLOX-x AP 59.7/58.7/60.8/56.8/50.6 | condition sensitivity | https://github.com/fubel/synthehicle | confirmed | README |
| [R04] Synthehicle ReID mAP 47.8/59.8/47.57/39.08/27.04; 33 mAP / 55% drop | same | same | confirmed | arithmetic holds |
| [R04] Shape bias 21.39% -> 81.37% | shape bias | https://github.com/rgeirhos/texture-vs-shape | confirmed | README |
| [R04] 48,560 trials, 97 observers | same | https://arxiv.org/abs/1811.12231 | confirmed | abstract |
| [R04] AugMix 65.3 mCE, 77.53% top-1 | AugMix | https://github.com/google-research/augmix | confirmed | README |
| [R04] UnrealZoo 53.46 FPS at 2K, 100+ scenes, Apache 2.0 | 5.7 | github.com/UnrealZoo/unrealzoo-gym | unverifiable | no README match |
| [R04] Tamper detection 94% / 96% | tamper | paywalled | unverifiable | already hedged |
| [R05] Video-MME 900 videos / 254 h / 2,700 QA | 9.1 | https://arxiv.org/abs/2405.21075 | confirmed | abstract |
| [R05] LongVideoBench 6,678 MCQ, 17 categories | 9.1 | https://arxiv.org/abs/2407.15754 | confirmed | abstract |
| [R05] EgoSchema >5000 MCQ | 9.1 | https://arxiv.org/abs/2308.09126 | confirmed | abstract |
| [R05] MLVU GPT-4o 64.6% | 9.1 | arXiv 2406.04264 Table 2 | confirmed | [VERIFY] resolved |
| [R05] IRRA 73.38 R1 / 66.13 mAP, 3-9% margin | person search | https://github.com/anosorae/IRRA | confirmed | README |
| [R05] Charades-STA bias baseline | 8 | https://arxiv.org/abs/2101.09028 | confirmed | abstract |
| [R05] RF-Pose 83% of lineup of 100 | RF | https://news.mit.edu/2018/artificial-intelligence-senses-people-through-walls-0612 | confirmed | [VERIFY] resolved |
| [R05] ShotSpotter 97% vs MJC 89%/86% over 21 months | audio | https://www.macarthurjustice.org/case/williams-v-city-of-chicago/ | confirmed | verbatim |
| [R05] Chicago OIG 24 Aug 2021 | audio | igchicago.org | confirmed | page and date exist |
| [R05] mmWave 98.86% / 95.45% | RF | mdpi.com | unverifiable | blocked |
| [R05] GAO 803 towers; 2,300 by 2034 | border | fedscoop | unverifiable | [VERIFY] left |
| [R05] phi-OTDR NAR >90% | fibre | mdpi | unverifiable | [VERIFY] left |
| [R06] 12211733, 1 Friar St RG1 1DA, inc. 17 Sep 2019, SIC 72190 | 1.1 | https://find-and-update.company-information.service.gov.uk/company/12211733 | confirmed | live |
| [R06] [person] DOB Mar 1963, appointed 10 Jan 2020, ID verified 1 Apr 2025 | 1.2 | .../officers | confirmed | live |
| [R06] "an active Director and two Secretaries" | 1.2 | https://find-and-update.company-information.service.gov.uk/company/12211733/officers | **corrected** | 4 active directors (Livingstone 2019, [person] 2020, Matthews Jul 2026, Eccles-Williams Aug 2026); 2 resigned (Stringer, Beldon) |
| [R06] WB Group FlyEye/FT-5/Warmate into a vendor platform; Ukraine data since 2015 | 1.6 | (vendor source removed) | confirmed | dated 12 Jun 2026 |
| [R06] Seemakurthy AAAI 2023 paper | 2.2 | ojs.aaai.org | unverifiable | no title returned |
| [R06] About-Us CEO/CTO quotes | 2.1 | vendor.com | unverifiable | 403 |

SCORE R04: confirmed 10 / corrected 0 / unverifiable 3
SCORE R05: confirmed 9 / corrected 0 / unverifiable 3
SCORE R06: confirmed 3 / corrected 1 / unverifiable 2

#### CONCLUSION-CHANGING
- R06 1.2: the vendor has **four active directors, not one**, two of them appointed in July and August 2026. Fixed in place.

### Audit G4 (2026-09-26), pass 2
Status rule: "confirmed" means the primary page was fetched. "confirmed (search)" means only a search-result extract was seen, not the page.

| claim | section | source URL | status | note |
|---|---|---|---|---|
| [D05] Hala Point 1.15B neurons, 1,152 Loihi 2, 128B synapses, 140,544 cores, 2,600 W, 20 petaops, >15 TOPS/W INT8, >2,300 x86, up to 12x Pohoiki Springs, Sandia | §1.6 | https://www.intc.com/news-events/press-releases/detail/1691/intel-builds-worlds-largest-neuromorphic-system-to | confirmed | the newsroom URL cited in D05 now 404s; the IR copy has every figure |
| [D05] Loihi 2: 1M neurons, 120M synapses, Intel 4 | §1.6 | https://open-neuromorphic.org/neuromorphic-computing/hardware/loihi-2-intel/ | confirmed | |
| [D05] Loihi 1: 128 cores, 14 nm | §1.6 | https://www.researchgate.net/publication/322548911 | confirmed (search) | Davies 2018, IEEE Micro 38(1) |
| [D05] Loihi 1: ~130k neurons, ~130M synapses | §1.6 | none | unverifiable | not found on any page I fetched |
| [D05] BrainChip/Raytheon AFRL $1.8M, 1 Apr 2025, AF242-D015, micro-Doppler | §1.7 | https://brainchip.com/brainchip-partners-with-rtxs-raytheon-for-afrl-radar-contract/ | confirmed | Business Wire returned 403; the BrainChip page matches |
| [D05] TrueNorth 4,096 cores, 1M neurons, 256M synapses, 70 mW; Science 345:668 | §1.6 | science.org / PubMed | unverifiable | both returned 403 or a captcha |
| [D05] Tianjic, Nature cover 1 Aug 2019 | §1.6 | https://www.tsinghua.edu.cn/en/info/1244/3005.htm | confirmed | |
| [D05] Tianjic 156 cores, ~40k neurons, 3.8x3.8 mm | §1.6 | nature.com (login redirect) | unverifiable | |
| [D05] BrainScaleS-2: 512 neurons, 131k synapses, 1000x speed-up | §1.6 | https://open-neuromorphic.org/neuromorphic-computing/hardware/brainscales-2-universitat-heidelberg/ | confirmed | |
| [D05] SpiNNcloud: 35,000 chips, >5M cores | §1.6 | https://tu-dresden.de/tu-dresden/newsportal/news/milestone-for-energy-efficient-ai-systems-tud-launches-spinncloud-supercomputer | confirmed | the "five-billion neuron" line is not on that page (unverifiable) |
| [D05] Diehl & Cook 2015 STDP MNIST 95% | §1.3 | https://www.frontiersin.org/articles/10.3389/fncom.2015.00099/full | confirmed | [VERIFY] tag replaced with an audit note |
| [D05] GrAI Matter Labs acquired by Snap, 2023 | §1.7 | https://www.eetimes.com/has-grai-matter-labs-been-snapped-up-by-snap-inc/ | confirmed (search) | 31 Oct 2023, made public 2024; [VERIFY] replaced |
| [D05] IMX636: 1280x720, 4.86 µm pixel, >120 dB | §1.8 | https://docs.prophesee.ai/stable/hw/sensors/imx636.html | confirmed | |
| [D05] Innatera Pulsar, 21 May 2025; 100x latency / 500x energy; RISC-V + CNN + FFT | §1.7 | https://www.innatera.com/newsroom/innatera-unveils-pulsar-the-worlds-first-mass-market-neuromorphic-microcontroller-for-the-sensor-edge/ | confirmed | |
| [D05] Xylo 219 µW idle / 93 µW dynamic | §1.7 | https://open-neuromorphic.org/neuromorphic-computing/hardware/xylo-synsense/ | unverifiable | search snippet only; the SynSense product page no longer lists the figures |
| [D06] i-LIDS "four scenarios" | l.471, l.1385 | https://www.securityindustry.org/wp-content/uploads/2017/08/iLids-User-Guide.pdf | corrected | five scenarios; from the search extract of the guide (the PDF returns 403 to direct fetch) |
| [D06] HORS 292 "January 2005" | §2.4 | https://popcenter.asu.edu/sites/g/files/litvpz3631/files/Responses/video_surveillance/PDFs/Gill&Spriggs_2005.pdf | corrected | title page reads February 2005 |
| [D06] "2022 Procurement Act" | §2.3 | https://www.dlapiper.com/en-pr/insights/publications/2023/10/the-procurement-act-has-received-royal-assent | corrected | Procurement Act 2023, Royal Assent 26 Oct 2023 |
| [D06] North Hyde fire "21 March 2025" | §3.3 | https://www.neso.energy/news/final-report-review-north-hyde-substation-outage | corrected | fire was 20 March, closure 21 March; NESO puts the cause as bushing moisture (an equipment fault) |
| [D06] Bridges, Court of Appeal 2020, grounds (who/where discretion, PSED) | §5.3 | https://www.judiciary.uk/judgments/r-bridges-v-cc-south-wales/ | confirmed | [2020] EWCA Civ 1058, 11 Aug 2020; appeal allowed on grounds 1, 3 and 5 (grounds via the press-summary search extract); bailii returned 403 |
| [D06] NDAA FY2019 §889, named Chinese video vendors | §2.3 | https://www.acquisition.gov/far/52.204-25 | confirmed | congress.gov returned 403; FAR 52.204-25 names Hytera, Hikvision and Dahua |
| [D06] Surveillance Camera Code: 12 principles, PoFA s.33(5) | §2.2 | https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version | confirmed | |
| [D06] Code laid 16 Nov 2021, in force 12 Jan 2022 | §2.2 | Lords Library (403) | unverifiable | |
| [D06] Moore County attack, Dec 2022, no suspect | §3.3 | https://en.wikipedia.org/wiki/Moore_County_substation_attack | confirmed (search) | 3 Dec 2022, ~40–45k customers, still unsolved |
| [D06] Norris & Armstrong: 888 surveillances, 711 with demographics | §2.5 | https://popcenter.asu.edu/sites/g/files/litvpz3631/files/library/CrimePrevention/Volume_10/06-NorrisArmstrong.pdf | confirmed (search) | |
| [D06] Keval & Sasse: 13 managers, 38 operators, 13 control rooms | §2.5 | UCL Discovery (403) | unverifiable | |
| [D07] MOTIP 69.6/72.6 HOTA "DanceTrack/SportsMOT" | §4.2 | https://arxiv.org/pdf/2403.16848 | corrected | both figures are DanceTrack (without / with extra data) |
| [D07] Orin NX 16GB 18x 1080p30 decode | §7 | https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/ | confirmed | 18x 1080p30 (H.265) |
| [D07] Hailo-8 26 TOPS, 2.5 W | §7 | https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/ | confirmed | |
| [D07] DINOv3 7B; +6 mIoU over DINOv2 on ADE20K; 15 tasks, 60+ benchmarks | §1.2 | https://arxiv.org/html/2508.10104 ; https://ai.meta.com/blog/dinov3-self-supervised-vision-model/ | confirmed | 55.9 vs 49.5 mIoU; beats AM-RADIOv2.5 by about 3 |
| [D07] VideoPrism best on 31/33 benchmarks | §1.3 | https://arxiv.org/abs/2402.13217 | corrected (note) | arXiv says 31/33; the current Google blog says 30/33 |
| [D07] InternVideo2.5 +12.4 EgoSchema, +3.9 MLVU, +0.6 LVB, +0.9 VideoMME, 6x longer input | §1.3 | https://arxiv.org/html/2501.12386 | confirmed | |
| [D07] Qwen3-VL 8B ≈ Qwen2.5-VL 72B; 2,048-frame / 224K-token / 640–768 tokens-per-frame / 2 fps protocol | §1.4 | https://arxiv.org/html/2511.21631 | confirmed | |
| [D07] Qwen3-VL "competitive with Gemini 2.5 Pro, GPT-5, Claude Opus 4.1" | §1.4 | same | unverifiable | page says "on par with Gemini 2.5 Pro"; the exact three-model sentence was not located |
| [D07] MLVU GPT-4o 64.6%, where guessing scores 25% | §1.4 | https://openaccess.thecvf.com/content/CVPR2025/papers/Zhou_MLVU_Benchmarking_Multi-task_Long_Video_Understanding_CVPR_2025_paper.pdf ; https://arxiv.org/html/2406.04264 | corrected (note) | 64.6 is the dev set; the latest version's six-option test set gives 54.5 against 16.7% chance |
| [D07] in-the-wild gait "~50–70% Rank-1" | §9 | https://github.com/ShiqiYu/OpenGait/blob/master/docs/1.model_zoo.md | corrected (dated) | GREW now 79–86 (DeepGaitV2, SkeletonGait++) |
| [D07] TransReID −50.75 / CLIP-ReID −38.09 mAP | §1.2 | via R02, no primary | unverifiable | |
| [D08] UBnormal CC BY-NC-ND 4.0 | §9 | https://github.com/lilygeorgescu/UBnormal | confirmed | |
| [D08] GRUtopia code MIT, GRScenes CC BY-NC-SA 4.0, 100k scenes | §1, §9 | https://github.com/OpenRobotLab/GRUtopia | confirmed | |
| [D08] IntPhys 2: CC BY-NC, gen-AI use prohibited, UE 5.4, 253 scenes | §9, §12 | https://github.com/facebookresearch/IntPhys2 | confirmed | 253 is the main set; 344 scenes in total |
| [D08] PeopleSansPeople 28 humans, 39 clips, 21,952 textures, 490k images, KP AP 46.40 vs 23.51 | §12 | https://github.com/Unity-Technologies/PeopleSansPeople | confirmed | README says ">21,000 textures" |
| [D08] HumanML3D 14,616 motions | §12 | https://github.com/EricGuo5513/HumanML3D | confirmed | |
| [D08] SMPL-X 54 joints, non-commercial licence | §12 | https://github.com/vchoutas/smplx | confirmed | |
| [D08] UnrealZoo 100+ envs, UE 5.7, 16 km², 10+ agent types | §1 | https://github.com/UnrealZoo/unrealzoo-gym | confirmed | |
| [D08] v2e 50–200x slower than real time | §12 | https://github.com/SensorsINI/v2e | confirmed | |
| [D08] MultiviewX 6 cameras, 1920x1080 | §12 | https://github.com/hou-yz/MultiviewX | confirmed | |
| [D08] Isaac Sim GCC 11 only | §1 | not refetched | unverifiable | |
| [H01] MOT20 average 127/frame, 246 peak | 5.3 | https://arxiv.org/pdf/2003.09003 | confirmed | |
| [H01] TinyPerson 18.0 ± 17.4 px | 5.1 | https://openaccess.thecvf.com/content_WACV_2020/papers/Yu_Scale_Match_for_Tiny_Person_Detection_WACV_2020_paper.pdf | confirmed (search) | AP50-tiny ≈ 57 not checked |
| [H01] WILDTRACK 7 cameras, 400 frames, 360/40 split | 7.11 | https://arxiv.org/pdf/2007.07247 | confirmed (search) | |
| [H01] VIRAT "2–30 Hz, 10–200 px person height" | 5.4 | https://viratdata.org/ | confirmed (search) | |
| [H01] 2024 AI City Track 1 winner = "Geometric Consistency and State-aware Re-ID Correction" | 8.1 | https://www.aicitychallenge.org/2024-challenge-winners/ | confirmed | SJTU-LENOVO, online, HOTA 67.22 |
| [H01] best online MTMC "adjusted HOTA 77.7 incl. 10% bonus" | 8.4 | https://www.aicitychallenge.org/2024-challenge-winners/ | unverifiable | tagged; the 2024 page shows 67.22 (online) and 71.94 (offline) |
| [H01] gait "~50% on GREW" | 9.7 | https://github.com/ShiqiYu/OpenGait/blob/master/docs/1.model_zoo.md | corrected (dated) | true of 2019–21 models; now 60–86 |
| [H01] 92.5/80.8 → 30.5/16.1 cross-domain | 9.2 | none | unverifiable | tagged |
| [H01] CityPersons 11.92/47.88 MR | 5.2 | not fetched | unverifiable | |
| [H02] IEC 62676-4:2025 seven visual-performance levels | Q24 | https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2025 | confirmed (search) | the pass-1 [unverified] tag is replaced with an audit note |
| [H02] IEC 62676-6:2026 video-analytics grading | Q24 | https://webstore.iec.ch/en/publication/59704 | confirmed (search) | published 18 Feb 2026 |
| [H02] MEVA/ActEV 37 EO / 34 IR activities | Q119 | https://actev.nist.gov/sdl20 | confirmed (search) | |
| [H02] Sultani UCF-Crime 75.4 "[to verify]" | Q121 | https://openaccess.thecvf.com/content_cvpr_2018/papers/Sultani_Real-World_Anomaly_Detection_CVPR_2018_paper.pdf | confirmed (search) | 75.41 |
| [H02] RTFM 83.30 | Q121 | https://github.com/tianyu0207/RTFM | corrected | 84.30 |
| [H02] VadCLIP 88.02 | Q121 | https://arxiv.org/abs/2308.11681 | confirmed | |
| [H02] LAVAD 80.28 | Q121 | https://lucazanella.github.io/lavad/ | confirmed (search) | |
| [H02] four i-LIDS event scenarios + a separate MCT subset | Q115 | i-LIDS User Guide (search extract) | confirmed (search) | wording consistent |
| [H02] i-LIDS 10 s tolerance | Q27, Q116 | none fetched | unverifiable | the pass-1 "confirmed" is withdrawn; the guide PDF returns 403 |
| [H02] UR-DMU 86.97, MGFN 86.98 | Q121 | not fetched | unverifiable | |

SCORE D05: confirmed 11 / corrected 0 / unverifiable 5 (two [VERIFY] tags resolved)
SCORE D06: confirmed 6 / corrected 4 / unverifiable 2
SCORE D07: confirmed 6 / corrected 4 / unverifiable 2
SCORE D08: confirmed 9 / corrected 0 / unverifiable 1
SCORE H01: confirmed 5 / corrected 1 / unverifiable 3
SCORE H02: confirmed 7 / corrected 1 / unverifiable 2

#### CONCLUSION-CHANGING
- **Gait (H01 9.7, D07 §9).** "In-the-wild gait ≈ 50%" is out of date. Current OpenGait models reach 79–86% Rank-1 on GREW. The qualitative point still holds (lab numbers overstate field performance), but "gait fails in the wild" is now too strong.
- **AI City online MTMC ceiling (H01 8.4).** The "77.7 adjusted HOTA" does not match the 2024 results page (67.2 online). It is tagged [unverified]; do not quote it.
- **North Hyde (D06).** NESO has now established the cause: equipment and maintenance failure (moisture in a transformer bushing). This strengthens the document's own caution against calling it arson.
- Everything else is detail only: the i-LIDS scenario count, HORS 292 date, Procurement Act year, RTFM AUC, MOTIP dataset attribution, and the MLVU dev-vs-test split.

### Audit G3: D01–D04

| claim | section | source URL | verdict | note |
|---|---|---|---|---|
| [D01] Olean NY 1968, first US city street CCTV | 1.3 | https://www.oleantimesherald.com/news/nation-s-first-surveillance-cameras-were-installed-in-olean/article_fa09f59d-4ce3-558d-b713-1aa287a57d7e.html | confirmed | Sep 1968; [VERIFY] resolved |
| [D01] Trafalgar Square 1960, Times Square 1973 | 1.3 | — | unverifiable | [VERIFY] left |
| [D01] i-LIDS "four scenarios" | 6.1 | https://www.securityindustry.org/wp-content/uploads/2017/08/iLids-User-Guide.pdf | corrected | released library has 5 (adds multi-camera tracking) |
| [D01] i-LIDS launched 2006 | 6.1 | same | confirmed | |
| [D01] Stauffer–Grimson 1999, Viola–Jones 2001, AlexNet 2012, VSAM 1997–99 | various | standard bibliography | confirmed | from knowledge, not fetched |
| [D02] Dendorfer as MOTSynth author | 3 | https://arxiv.org/abs/2108.09518 | corrected | not an author; Ošep is |
| [D02] GHOST credited to Kitani lineage | 3 | Seidenschwarz et al. CVPR 2023 | corrected | TUM / Leal-Taixé |
| [D02] SORT ICIP 2016, FairMOT IJCV 2021, POM TPAMI 2008 etc. | reading list | standard bibliography | confirmed | from knowledge |
| [D02] Ošep TUM → NVIDIA | 3 | — | unverifiable | tagged |
| [D03] Omdia $27 bn market, +4.3 % | 1.2 | https://omdia.tech.informa.com/pr/2026/july/global-video-surveillance-market-grows-4point3percent-to-27-billion-dollars-as-ai-demand-intensifies-supply-chain-pressures | confirmed | |
| [D03] Motorola–Avigilon $1.0 bn, Mar 2018 | companies | https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-completes-acquisition-avigilon.html | confirmed | |
| [D03] Canon acquired BriefCam 9 May 2018 | acquisitions | https://global.canon/en/news/2018/20180703-2.html | corrected | announced 9 May; closed 3 Jul 2018 |
| [D03] Irisity–Agent Vi $67.5 m | acquisitions | https://www.securitysales.com/news/video-analytics-irisity-acquire-agent-vi/133633/ | confirmed | |
| [D03] Motorola–Calipsa 2022 | acquisitions | https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-acquires-calipsa.html | confirmed | 19 Apr 2022 |
| [D03] Metropolis–Oosto $125 m all-stock | acquisitions | https://techcrunch.com/2025/01/20/sources-ai-vision-startup-metropolis-is-buying-oosto-formerly-known-as-anyvision-for-just-125m/ | confirmed | raised ~$352–380 m (sources differ) |
| [D03] Verkada $5.8 bn, CapitalG, Dec 2025 | companies | https://www.cnbc.com/2025/12/03/verkada-capitalg-valuation-security.html | confirmed | |
| [D03] Alarm.com–Vintra assets Apr 2023 | acquisitions | https://www.securitysystemsnews.com/article/alarm-com-acquires-assets-of-ai-based-video-analytics-provider-vintra | confirmed | |
| [D04] storage/ingest worked examples | 2.x | arithmetic | confirmed | 4 rows recomputed |
| [D04] DORI 25/62.5/125/250 px/m | 9.1 | https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014 | confirmed | |
| [D04] PoE 15.4/30/60/90 W | 1.6 | IEEE 802.3af/at/bt | confirmed | |
| [D04] RTSPS port 322 | 1.2 | IANA registry | confirmed | |
| [D04] Hailo-8 26 TOPS / 2.5 W | edge | https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/ | confirmed | |
| [D04] Jetson stream-density | edge | vendor | unverifiable | already hedged |

SCORE D01 3/1/1 · D02 1/2/1 · D03 7/1/0 · D04 5/0/1
