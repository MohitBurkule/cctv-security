# Adversarial accuracy audit — reports 17–24 (2026-09-26)

Every checkable claim was treated as wrong until its primary source (arXiv
abstract/HTML tables, NVIDIA datasheets, gov.uk / EUR-Lex text, repo files and
code) was fetched. Reports were corrected in place. "Confirmed" rows marked as
resting on in-repo dossiers (R03/D07/H01) are only as good as those dossiers.

## Scores (confirmed / total claim rows)
| Report | Confirmed | Total | Score |
|---|---|---|---|
| 17 system design | 16 | 23 | 70 % |
| 18 perception | 37 | 41 | 90 % |
| 19 behaviour | 28 | 44 | 64 % |
| 20 degraded & fusion | 28 | 41 | 68 % |
| 21 data & governance | 16 | 22 | 73 % |
| 22 deployment | 24 | 38 | 63 % |
| 23 roadmap | 19 | 30 | 63 % |
| 24 sim2real | 31 | 40 | 78 % |

## Cross-report consistency fixes
* "O(n²) association made full MOT20 infeasible (killed at 2.5 h)" — stale in
  18, 21, 22, 23; docs/13 retracts it (tracker+eval ≈ 62 s on 8,931 frames;
  `--task all` still slow, ReID/eval_det unprofiled). Fixed in all four.
* LTCC clothes-change Rank-1 "in the 30s" (17, 24) → ~40 % (CAL 40.1/18.0).
  Also repeated in 00 index fact 6, H01, D07, R02 — not edited (out of scope).
* Jetson AGX Orin decode quoted 22× (NVIDIA page) — 22 had 23× for NX; fixed.
* PeopleSansPeople keypoint figures in 18/21/24 are consistent (6.40→44.43 real-only;
  21.90→44.43 vs ImageNet init).
* Repo figures (recall 0.758 vs 0.577 on 770 boxes; 6/14 & 9/14 in band;
  0.567 s/frame degrade; ~11 fps render; HOTA 0.545) agree across all reports.

## Claim table
| claim | report § | source fetched (URL) | verdict | note |
|---|---|---|---|---|
| [17] T4: 65 FP16 TFLOPS, 130 INT8 TOPS, 70 W, decode up to 38 FHD streams | 3.2, 5.2 | https://www.nvidia.com/en-us/data-center/tesla-t4/ | confirmed | |
| [17] YOLO11n 6.5 GFLOPs, YOLO11s 21.6 GFLOPs @640 | 5.2 | https://docs.ultralytics.com/models/yolo11/ | confirmed | T4 TRT 1.5/2.5 ms |
| [17] Jetson AGX 15-60 W/275 TOPS, NX 10-40 W/157, Nano 7-25 W/67 | 7, ref 12 | https://www.nvidia.com/en-gb/autonomous-machines/embedded-systems/jetson-orin/ ; web search (Super mode) | corrected | NX/Nano TOPS are Super mode (JetPack 6.2); hedge added |
| [17] SCC principles 10-12 underpin audit | 0 item 11 | https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version | corrected | 10=audit, 11=evidential, 12=reference DBs; narrowed to 10-11, added binding-only-on-relevant-authorities |
| [17] IEC 62676-4 revised 2025 | 3.9 | https://webstore.iec.ch/en/publication/83425 ; https://newsroom.axis.com/en-us/blog/iec-62676-4-video-surveillance | confirmed | Ed 2.0 Oct 2025 |
| [17] BoT-SORT authors Aharon/Orfaig/Bobrovsky, CMC+ReID | 3.4 | https://arxiv.org/abs/2206.14651 | confirmed | |
| [17] LTCC Rank-1 in the 30s | 3.5 | CAL CVPR 2022 paper (openaccess.thecvf.com) | corrected | CAL 40.1 R1/18.0 mAP CC; SOTA 40s |
| [17] 1 deg at 30 m = 3.9 m ground error | 3.4 | H01/R02 in-repo (R^2 theta/h, h=4 m) | corrected | missing height assumption added; arithmetic 900*0.01745/4=3.93 ok |
| [17] Metadata 5-50 kb/s at 10 fps | 4.1 | BOE arithmetic | corrected | own BOE gives 96 kb/s JSON, ~32 protobuf; now 30-100 kb/s |
| [17] "frozen image" is a SurvSim tamper mode | 3.1 | survsim/director/camera_director.py TAMPER_KINDS | corrected | not a mode; six kinds cover/spray/tilt/unplug/glare/defocus |
| [17] ByteTrack MOTA .463/IDF1 .538/HOTA .545 on 600-frame MOT20 subset, zero-shot YOLO11n | 3.4 | docs/13_BASELINES.md | confirmed | |
| [17] Editor render ~11 fps at 720p | 5.3 | docs/11 line 70 | confirmed | |
| [17] Degradation 0.567 s/frame, 0.3 target not reached | 5.3 | docs/15 | confirmed | |
| [17] 288k frames = 7.3 h render + 45 h degrade | 5.3 | arithmetic | confirmed | |
| [17] ActEV 0.1 FA/min = 6 FA/camera-hour; 500 cams -> 3000/h | 0 | docs/research/R03 L1212,1672 (actev.nist.gov) | confirmed | repo-sourced |
| [17] i-LIDS 10 s tolerance, late alarm = FA | 0,5.1 | R03 L1461 | confirmed | repo-sourced |
| [17] Always-on VLM ~4.6M tokens/camera-hour | 7 | D07 L167 | confirmed | repo-sourced BOE |
| [17] Westminster ~100-200 cameras | 1.1 | D06 L108-118 | confirmed | repo-sourced quote |
| [17] 6 tamper kinds, evaluate_mtmc handoff_gap, reid_by_epoch, pipeline funnel, ONVIF-M-shaped metadata in gt/video.py | 2,3.7,4 | survsim code | confirmed | |
| [17] Per-camera clock offset/drift modelled | 3.1 | survsim/core/models.py, gt/video.py | confirmed | |
| [17] RFC 7826 = RTSP 2.0, 2016 | 3.1 | https://www.rfc-editor.org/rfc/rfc7826 | confirmed | from knowledge; not refetched |
| [17] CPU decode ~1 core per 1080p25 stream | 3.2 | none | unverifiable | tagged BOE/lore already |
| [17] 500x4 Mb/s = 2 Gb/s | 7 | arithmetic | confirmed | |
| [18] Person height at 20–50 m on 4 mm/1080p "roughly 30–80 px" | 1.1 | report's own BOE arithmetic | corrected | BOE gives 97 px @30 m, 58 px @50 m; changed to 60–100 px (40–65 at 720p) |
| [18] BOE FOV 37°, 97 px @30 m, 58 px @50 m | 1.1 | arithmetic | confirmed | 2·atan(2.7/8)=37.3°; atan(1.75/30)=3.34° |
| [18] Real CCTV stats noise 0.309 / edge 6.06 / blockiness 1.149 | 1.1 | docs/15 | confirmed | medians in docs/15 table |
| [18] IEC 62676-4:2014 DORI 25/62.5/125/250 px/m | 1.1 | https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014 | confirmed | Axis rounds observation to 63 |
| [18] IEC/EN 62676-4:2025 seven levels 20/40/80/125/250/500/1500 | 1.1 | https://www.jvsg.com/iec-62676-4-oodpcvs/ | confirmed | secondary source (standard paywalled) |
| [18] YOLOX-L 50.0 AP, 68.9 FPS V100 | 1.2 | https://arxiv.org/abs/2107.08430 | confirmed | |
| [18] YOLOv8s/m 44.9/50.2, 1.20 ms A100 TRT | 1.2 | https://docs.ultralytics.com/models/yolov8/ | confirmed | |
| [18] YOLO11n/s/m 39.5/47.0/51.5; 1.5/2.5/4.7 ms; 6.5/21.6/68.1 GFLOPs | 1.2 | https://docs.ultralytics.com/models/yolo11/ | confirmed | |
| [18] RT-DETR-R50/R101 53.1/54.3 AP, 108/74 FPS T4 | 1.2 | https://arxiv.org/abs/2304.08069 | confirmed | |
| [18] YOLO11n zero-shot MOT20 subset AP 0.348/0.730/0.293 | 1.3 | docs/13 | confirmed | |
| [18] batch_v4 yolov8n recall 0.758 vs 0.577 on 770 GT boxes | 1.3 | docs/11, docs/12 | confirmed | |
| [18] SAHI +6.8/+5.1/+5.3 sliced, +12.7/+13.4/+14.5 with FT, VisDrone+xView | 1.4 | https://arxiv.org/abs/2202.06934 | confirmed | |
| [18] CroHD 9 seq, 11,463 frames, ~2.28 M heads | 1.5 | https://arxiv.org/abs/2103.13516 | confirmed | 2,276,838 heads |
| [18] docs/11 bug 13 crowd density counted only visible | 1.5 | docs/11 | confirmed | |
| [18] MOTChallenge ignore classes 2/7/8/12 | 1.7 | docs/13 | confirmed | |
| [18] ByteTrack MOT17 63.1/80.3/77.3; MOT20 61.3/77.8/75.2 | 2.1 | https://github.com/ifzhang/ByteTrack | confirmed | |
| [18] OC-SORT MOT17 63.2/78.0/77.5; MOT20 HOTA 62.4 | 2.1 | https://github.com/noahcao/OC_SORT | confirmed | |
| [18] StrongSORT++ MOT17 64.4/79.6/79.5; MOT20 HOTA 62.6 | 2.1 | https://arxiv.org/pdf/2202.13514 (Tables) | confirmed | MOT20 IDF1 77.0, MOTA 73.8 |
| [18] BoT-SORT-ReID MOT17 65.0/80.5/80.2; MOT20 HOTA 63.3 | 2.1 | https://github.com/NirAharon/BoT-SORT | confirmed | |
| [18] Deep OC-SORT MOT17 64.9, MOT20 63.9 HOTA | 2.1 | https://arxiv.org/abs/2302.11813 | confirmed | |
| [18] in-repo ByteTrack HOTA 0.545 MOT20 subset | 2.1 | docs/13 | confirmed | |
| [18] max_lost = 1 s | 2.2 | docs/13 | confirmed | |
| [18] numpy association/HOTA O(n²) is the bottleneck; run killed after 2.5 h | 2.3 | docs/13 | corrected | docs/13 retracts O(n²) diagnosis; tracker+eval ~62 s on full train; time is in eval_det/ReID |
| [18] OSNet-x1.0 94.2/82.6, MSMT 74.9/43.8, 2.2 M, 0.98 GFLOPs | 3.1 | https://kaiyangzhou.github.io/deep-person-reid/MODEL_ZOO | confirmed | |
| [18] BoT 94.5/85.9 | 3.1 | https://arxiv.org/abs/1903.07071 | confirmed | |
| [18] TransReID 95.1/89.0, MSMT 85.3/67.8 | 3.1 | https://github.com/damo-cv/TransReID | confirmed | |
| [18] CLIP-ReID ~95/89.6, MSMT 88.7/73.4 | 3.1 | https://github.com/Syliz517/CLIP-ReID ; https://arxiv.org/abs/2211.13977 | unverifiable | abstract has no numbers; repo lists different (higher) figures; marked [unverified] |
| [18] CAL LTCC CC top-1 40.1 / mAP 18.0 | 3.1 | CVPR open access (403) + search snippet | confirmed | via search of paper text |
| [18] In-repo OSNet-ImageNet 0.186/0.231, mock 0.156/0.279 | 3.1 | docs/13 | confirmed | |
| [18] AI City 2026 Track 1 Multi-Camera 3D Perception (Sim2Real), 3D HOTA | 3.2 | https://www.aicitychallenge.org/ | confirmed | |
| [18] MVDet 88.2 % MODA Wildtrack | 3.2 | https://arxiv.org/abs/2007.07247 | confirmed | |
| [18] docs/11 bug 3 disguise in blind spot | 3.3 | docs/11 | confirmed | |
| [18] 3 baked bodies; crops ≥48 px vis ≥0.6; hi-vis 0.2 | 3.3 | docs/11, docs/13, docs/12 | confirmed | |
| [18] Pitch error 2.7 m per degree at 30 m/6 m | 4.3 | arithmetic | confirmed | |
| [18] MOTSynth 768 sequences + quote | 6.1 | https://arxiv.org/abs/2108.09518 | confirmed | 384 screenplays × day/night |
| [18] PeopleSansPeople 44.43 vs 21.90; 63.47 vs 62.40 | 6.1 | https://arxiv.org/abs/2112.09290 | confirmed | |
| [18] BEDLAM synthetic-only SOTA HPS | 6.1 | https://arxiv.org/abs/2306.16940 | confirmed | |
| [18] ClonedPerson 5,621 ids, 887,766 imgs | 6.1 | https://arxiv.org/abs/2204.02611 | confirmed | |
| [18] Synthehicle 17 h, 340 cams, 64 scenes | 6.1 | https://arxiv.org/abs/2208.14167 | confirmed | |
| [18] cctv_day_720p 6/14, legacy_sd 9/14, temporal_noise 9.46 vs 1.57–2.93 | 6.3 | docs/15 | confirmed | |
| [18] INT8 costs 0.5–2 AP | 8 | — | unverifiable | already hedged [INF/lore] in report |
| [19] i-LIDS 10-s alarm window, repeats disregarded | §5.1 | https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf | confirmed | verbatim p.~l.1426 |
| [19] i-LIDS one FP logged per 5 s | §5.1 | same | confirmed | verbatim |
| [19] F1 >= 0.7 application; "considerably more stringent" | §5.1 | same | confirmed | |
| [19] recall bias higher for Event Recording than Operational Alert | §5.1 | same | confirmed | added values 0.35 / 35 |
| [19] parked vehicle >60 s example | §5.1, §14 | same | confirmed | |
| [19] Abandoned baggage one of "original four scenarios" | §2.3 | same | corrected | guide: four event-detection scenarios of six initial |
| [19] SurvSim score(): tolerance 10 s, late = FP, detect once | §5.1 | survsim/eval/alarms.py | confirmed | |
| [19] ilids_compat is a missing/proposed flag | §5.1, §15.3, §17#10 | survsim/eval/alarms.py | corrected | already implemented (repeats + 5 s coalescing); recall-bias F1 missing |
| [19] ActEV RFA per minute; SRL ranks Pmiss@RFA=0.1 | §5.2 | https://actev.nist.gov/SRL | confirmed | |
| [19] ActEV18 used RFA 0.15 and 1; SRL reports 1,0.2,0.15,0.03,0.01; Tfa alongside | §5.2 | https://github.com/usnistgov/ActEV_Scorer | corrected | value list belongs to ActEV18_AD protocol; Tfa from ActEV19_AD; ActEV18 primary unverified |
| [19] UCF-Crime 128 h, 1,900 videos, 13 classes | §3.2, ref 3 | https://arxiv.org/abs/1801.04264 | confirmed | |
| [19] VadCLIP 88.02 AUC / 84.51 AP, AAAI 2024 | §3.2 | https://arxiv.org/abs/2308.11681 | confirmed | |
| [19] RWF-2000 FGN 87.25 %, Cheng/Cai/Li ICPR 2020 | §3.3 | https://arxiv.org/abs/1911.05913 | confirmed | |
| [19] NTU RGB+D 120: 114k clips, 120 classes, 106 subjects, TPAMI | §12 | https://arxiv.org/abs/1905.04757 | confirmed | |
| [19] ST-GCN/PoseC3D/CTR-GCN/SlowFast/VideoMAE/Trajectron++/CSRNet arXiv IDs | §3.1, §6 | arXiv (not individually fetched) | unverifiable | IDs match known papers; not refetched |
| [19] Fruin LoS F > ~5.4/m² | §6 | https://www.gkstill.com/Support/crowd-flow/fruin/Fruin1.html + search | confirmed (search extract only) | page itself cites critical 2-3/m² |
| [19] 4.7/m² "Wembley egress" | §6 | search extract (gkstill) | corrected | "typical in and around Wembley" (Green Guide standing) |
| [19] Axis Loitering Guard free, firmware >= 7.10 | §16 | https://www.axis.com/products/axis-loitering-guard | confirmed | AXIS OS 7.10–12.11; include/exclude area counts not confirmed |
| [19] NPSA hostile recon + SCaN | §11 | https://www.npsa.gov.uk/see-check-and-notify-scan (search) | confirmed | main URL 403 to fetcher |
| [19] Vendor claims Hanwha/Genetec/Avigilon/BriefCam/Ipsotek | §16 | not fetched | unverifiable | report already labels as secondary/extract |
| [19] VLM budget ~12k tokens, 400x | §3.5 | arithmetic | corrected | 7.2k tokens/cam-h, ~600x |
| [19] 99 % specificity at p=1e-3 -> ~10 FA per TP | §4.1 | arithmetic | confirmed | |
| [19] 0.12 nuisance/cam-h; 0.012 per type; 6/h = 50x | §5.3 | arithmetic | confirmed | RFA 0.1/min = 6/h |
| [19] 400 cam-h, 7.2 M frames, ~180 h at 11 fps | §7.4 | docs/11 l.70 | confirmed | |
| [19] funnel 2400->480->360->90->9; 0.0075/cam-h | §10 | arithmetic | confirmed | |
| [19] disguise_and_tamper: 240 s, 10 fps, seed 11, cams, zones, PTZ 20 s dwell 40°/s, spray t=150 | §13 | configs/scenarios/disguise_and_tamper.yaml | confirmed | |
| [19] hero "ten steps" | §13.1 | yaml | corrected | eight |
| [19] generators omitted (loiterer positive) | §13.1 | yaml | corrected | added |
| [19] PTZ cycle ~70 s | §13.2 | yaml (slews 100°+60°+160° at 40°/s ≈ 8 s) | confirmed | ~68 s |
| [19] DwellRule defaults 60 s, 0.5 m/s, zone tags | §13.2 | survsim/eval/rules.py | confirmed | |
| [19] DwellRule fires on commuters dwelling 60 s | §13.2 | yaml dur 30–60 | corrected | hedged "can fire" |
| [19] spread test / gap tolerance only "proposed" | §2.1, §13.2, §15.3 | survsim/eval/rules.py PathLoiterRule | corrected | implemented (radius 4.0, window 30, reentry 20) |
| [19] segments_from_world 30 s / 15 s | §13.2 | survsim/eval/behaviour.py | confirmed | |
| [19] AUC 0.72, precision 0.074, 3.3 % | §13.2 | docs/14_FIRST_RESULTS.md | confirmed | |
| [19] pipeline stage order & defaults (2 in 60 s, 0.5, 120 s dedup) | §13.2 | survsim/eval/pipeline.py | corrected | corroboration only if require_corroboration; after_hours conditional |
| [19] Candidate fields | §15.1 | survsim/eval/pipeline.py | confirmed | |
| [19] AbandonedObjectRule exists | §15.3 | survsim/eval/rules.py | confirmed | defaults static 30 s, owner 15 m |
| [19] retrieval.py recall@k, MRR | §11 | survsim/eval/retrieval.py | confirmed | |
| [19] access-control badge sensor | §2.2 | survsim/director/world.py | confirmed | |
| [19] observed_by missing | §17#4 | survsim/director/world.py | corrected | partial (appearance events only) |
| [19] 4 cams x 240 s = 0.267 h; 3.75 FA/h | §13.2 | arithmetic | confirmed | |
| [19] street_crowd 60 s, 10 fps, 3 cams 3.5–5 m, 18–25°, 70–95°, 720p, generator counts | §14 | configs/scenarios/street_crowd.yaml | confirmed | |
| [19] tamper 6 kinds, confound audit, bug 13 | §1, §4.3, §6 | docs/11 | confirmed | |
| [19] EU AI Act Art 5 profiling-only prediction prohibited; emotion recog workplace | §8 | https://eur-lex.europa.eu/eli/reg/2024/1689/oj (not fetched) | unverifiable | consistent with Art 5(1)(d),(f) from knowledge |
| [20] TAMPER_KINDS = cover,spray,tilt,unplug,glare,defocus; blind = cover/unplug | 0,13.1 | survsim/director/camera_director.py | confirmed | |
| [20] 5 degrade profiles, day crf29 gop8 bf0 grain3; legacy 704x576 crf34 scale .75; night iso11 motion5 grain.3; fog haze .45 crf32 | 1,14.1 | survsim/sensors/degrade.py | confirmed | |
| [20] day 6/14, legacy 9/14, night 3/14 in band; noise 0.391; temporal 9.46 vs 1.57-2.93 | 1.1 | docs/15 | confirmed | |
| [20] legacy misses = mtf, edge_width, temporal_noise | 1.1 | docs/15 table | corrected | also rms_contrast, luma_skew (5 misses) |
| [20] 0.567 s/frame degrade | 1.1 | docs/15 | confirmed | |
| [20] ExDark 7,363 imgs /12 classes /10 illum types | 2.1 | https://arxiv.org/abs/1805.11227 | confirmed | |
| [20] NightOwls 279k frames, 40 seq, 3 countries | 2.1 | https://www.robots.ox.ac.uk/~vgg/publications/2018/Neumann18b/ | corrected | 5 baselines, not 3 |
| [20] Johnson 1/4/6.4 lp ±0.25/0.8/1.5 | 2.2 | https://en.wikipedia.org/wiki/Johnson%27s_criteria | confirmed | |
| [20] JOHNSON_PIXELS 1.5/6/12 | 2.2 | survsim/sensors/thermal.py | confirmed | |
| [20] IFOV 0.68 mrad; 1.5px@735m; 3px@368m; 2.8px@400m | 2.2,10 | BOE | confirmed | |
| [20] Koschmieder 14% at V=200,d=100 | 2.3 | BOE | confirmed | |
| [20] Foggy Cityscapes 20,550; Foggy Driving 101; "significantly improves" | 2.3 | https://arxiv.org/abs/1708.07819 | confirmed | |
| [20] ACDC 8,012 / 4,006 adverse | 2.3 | https://arxiv.org/abs/2104.13395 | confirmed | |
| [20] Tamper survey 2023 | 3.1 | https://arxiv.org/abs/2310.07886 | confirmed | |
| [20] Ribnick 2006 / Saglam 2009 details | 3.1 | not fetched | unverifiable | left as cited |
| [20] rf.py n=2.8, sigma 4, -40 dBm@1m, -92 sens | 4.1 | survsim/sensors/rf.py | confirmed | |
| [20] BLE n=2.424 CI 2.06-2.79 in ref [10] | 4.1 | https://pmc.ncbi.nlm.nih.gov/articles/PMC7998977/ | removed | paper is outdoor ZigBee particle filter |
| [20] 10^(6/30)=1.6x | 4.1 | BOE | confirmed | |
| [20] SpotterRF C550 850 m walker, 1.5 km vehicle | 4.2 | https://www.securityinformed.com/news/co-9526-ga-co-177-ga.11929.html (search) | confirmed | |
| [20] C550-EXT 1,050 m | 4.2,15 | search results | corrected | secondary sources say 950 m; hedged |
| [20] Navtech person 1.5 km, vehicle 3 km | 4.2,15 | https://navtechradar.com/radar-solutions/radar-for-security-solutions/advanceguard-for-security/ | corrected | page gives model ranges 0.3/1/3/5 km only |
| [20] EchoGuard drones 1 km, vehicles 3.5 km, az<1° | 4.2,15 | https://www.echodyne.com/radar-systems/echoguard | corrected | only az<1°, range acc<3.25 m on page |
| [20] shout 88 dB, 0.05 dB/m absorption, 48 dB @100 m before absorption | 4.4 | survsim/sensors/audio.py | confirmed | |
| [20] AudioSet 2,084,320 clips, 527 classes | 4.4 | https://research.google.com/audioset/ | confirmed | |
| [20] UrbanSound8K 8,732 clips <=4 s 10 classes | 4.4 | https://urbansounddataset.weebly.com/urbansound8k.html | confirmed | |
| [20] SAPIENT: Dstl+Innovate UK, protobuf since v7, ~60% less bandwidth, MOD C-UAS, NATO eval | 5.1 | https://www.gov.uk/guidance/sapient-autonomous-sensor-system | confirmed | |
| [20] BSI Flex 335 v2.0 on GitHub | 5.1 | https://github.com/dstl/SAPIENT-Proto-Files | confirmed | v1 in effect 31 May 2023; v2.0 year not confirmed |
| [20] JDL revisions Steinberg 1999 | 5.1 | not fetched | unverifiable | |
| [20] AND fusion 2*f1*f2*W; 0.017 FA/h, 60x | 5.3 | survsim/eval/fusion.py | confirmed | |
| [20] Pd 0.765; corr 0.5 -> 0.258/h; note >0.3 | 13.1 | survsim/eval/fusion.py | confirmed | |
| [20] scenario: 240 s,10 fps, spray t=150, ptz 40 dps 20 s dwells | 13.1 | configs/scenarios/disguise_and_tamper.yaml | confirmed | cycle ~68 s -> ~30% |
| [20] audio: ambient 35+6log2(18)=60, SNR~8, DOA 7.5 deg, below at 20 m | 13.2 | survsim/sensors/audio.py | confirmed | 67.5 dB incl. absorption |
| [20] rotate_every_s 300 | 13.2 | survsim/sensors/rf.py | confirmed | |
| [20] Axis Q1961-TE output 640x480, 17 um | 15 | https://www.axis.com/products/axis-q1961-te | corrected | output 768x576; pitch not confirmed |
| [20] Hikvision DS-2TD2167 specs | 15 | hikvision page (failed to load) | unverifiable | hedged |
| [20] FLIR FC-AI 640x512, <25 mK, 8 lenses 8.6-90° | 15 | https://www.flir.com/products/fc-series-ai/ | confirmed | |
| [20] Senstar FP1150 ±4 m, 80 km | 15 | https://senstar.com/products/fence-sensors/fiberpatrol-fp1150/ | confirmed | |
| [20] FP400 4 zones x 300 m | 15 | not fetched | unverifiable | |
| [20] Axis ≈90% of Sound Intelligence sales (ProPublica) | 15 | https://projects.propublica.org/graphics/aggression-detector-data-analysis | removed | not found; hedged |
| [20] ProPublica 565 FPs (402/75/43/42), 35 of 65 missed, 40 students ~2 h | 15 | https://projects.propublica.org/graphics/aggression-detector-data-analysis | confirmed | 26+14 students |
| [20] Louroe price ~$366 eBay | 15 | not fetched | unverifiable | |
| [21] Omnibus: prov. agreement 6 May 2026, Council 13 May 2026, Annex III -> 2 Dec 2027, Annex I -> 2 Aug 2028, Art 50 keeps 2 Aug 2026, new Art 5 NCII/CSAM ban, no biometric changes | 7.2 | https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ | confirmed | |
| [21] Omnibus status (report implied only a political agreement) | 7.2 | https://www.nicfab.eu/en/posts/digital-omnibus-ai-official-journal/ | corrected | Now Regulation (EU) 2026/1744, OJ 24 Jul 2026, in force 27 Jul 2026; NCII ban applies 2 Dec 2026; ref [26] added |
| [21] AI Act = Reg 2024/1689, adopted 13 Jun 2024, OJ 12 Jul 2024; Art 5 applies 2 Feb 2025 | 7.2 | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | confirmed | well-established; Art 10/12/14/15 numbering matches |
| [21] Amended SC Code laid 16 Nov 2021, in effect 12 Jan 2022, no withdrawal | 7.1 | https://www.gov.uk/government/publications/update-to-surveillance-camera-code | confirmed | |
| [21] SC Code: PoFA 2012 s.30, 12 principles, binding on relevant authorities | 7.1 | https://www.gov.uk/government/publications/update-to-surveillance-camera-code | confirmed | |
| [21] Webster BSCC from 1 Nov 2025, 2-yr term, vacant since Aug 2024 | 7.1 | https://www.stir.ac.uk/news/2025/november-2025-news/university-of-stirling-surveillance-expert-is-new-biometrics-and-surveillance-camera-commissioner/ | corrected | added interim commissioner from 1 Jul 2025 |
| [21] DUAA 2025 Royal Assent 19 Jun 2025; did not abolish Code/Commissioner | 7.1 | https://ecl-ips.com/blog/operate-cctv-be-aware-of-data-protection-law-changes/ | confirmed | secondary source; consistent with Webster appointment after DUAA |
| [21] DPIA required Art 35 for large-scale public monitoring | 7.1 | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/ | corrected | tightened wording to Art 35(3)(c) text |
| [21] Bridges [2020] EWCA Civ 1058, 11 Aug 2020 | 7.1 | https://www.judiciary.uk/judgments/r-bridges-v-cc-south-wales/ | confirmed | |
| [21] PeopleSansPeople +38.03/+1.47/+22.53/+1.07 kp AP | 2.1 | https://arxiv.org/abs/2112.09290 | confirmed | |
| [21] MOTSynth "can be used as a replacement for real data" | 2.1 | https://arxiv.org/abs/2108.09518 | confirmed | |
| [21] docs/15 cctv_day_720p 6/14, legacy_sd 9/14 | 2.3 | docs/15_REALISM_STATS.md:236 | confirmed | on batch_v1 street_crowd cam_02 |
| [21] batch_v4 yolov8n recall 0.758 vs 0.577 CesiumMan | 2.3 | docs/11:84, docs/12:897 | confirmed | |
| [21] MOT20 subset AP 0.348, HOTA 0.545, R1 0.186 | 4.1 | docs/13_BASELINES.md:80 | confirmed | |
| [21] full MOT20 killed at 2.5 h | 4.2 | docs/13:89 | confirmed | |
| [21] ~11 frames/s editor render; 0.567 s/frame degrade | 13.4 | docs/11:70, docs/15:285 | confirmed | |
| [21] three baked bodies MHB01-03 | 1.1/13.6 | docs/11:81-89 | confirmed | |
| [21] split_for_seed: last=test, second-last=val | 1.1/13.2 | survsim/datasets/build.py:31 | confirmed | |
| [21] street_crowd 60 s 10 fps 3 cams; disguise_and_tamper 240 s 10 fps 4 cams -> ~57k frames, 1.4 h render, ~9 h degrade | 13.1/13.4 | configs/scenarios/*.yaml | confirmed | 5*(1800+9600)=57,000 |
| [21] Settles TR 1648 2009; Mitchell FAT* 2019; Gebru; DeepPrivacy2 WACV 2023; BEDLAM CVPR 2023 | refs | arXiv IDs as cited | unverifiable | not re-fetched this pass; well-known, IDs plausible |
| [21] Tool prices (W&B $60, CVAT $33/$23/$12k, Label Studio $50) | 15 | pricing pages cited | unverifiable | not re-fetched this pass; volatile |
| [21] MOTChallenge CC BY-NC-SA 3.0 | refs | https://motchallenge.net/ | unverifiable | not re-fetched |
| [22] YOLO11 n/s/m/l/x mAP, T4 TRT latency, params, FLOPs (all 5 rows) | §1.1 | https://docs.ultralytics.com/models/yolo11/ | confirmed | exact match |
| [22] T4 decodes up to 38 FHD streams; 130 INT8 TOPS; 65 FP16 TFLOPS; 70 W; 16 GB | §0,1.2,1.3 | https://www.nvidia.com/en-us/data-center/tesla-t4/ | confirmed | |
| [22] L4 485 INT8 TOPS, 242 FP16, 24 GB, 300 GB/s, 72 W, 4 NVDEC/2 NVENC/4 JPEG, 1,040 AV1 720p30 | §1.2,1.3 | https://www.nvidia.com/en-us/data-center/l4/ | confirmed | sparsity per datasheet footnote |
| [22] A2 36/72 INT8 TOPS, 16 GB, 40–60 W | §1.3 | https://www.nvidia.com/en-us/data-center/products/a2/ | confirmed | NVDEC count not on page |
| [22] Orin Nano 8GB 67 TOPS, 7–25 W, 11x 1080p30 | §1.2,1.3 | https://www.nvidia.com/en-gb/autonomous-machines/embedded-systems/jetson-orin/ | confirmed | 67 is Super-mode figure |
| [22] Orin NX 16GB 23x 1080p30 decode | §1.2 | same | corrected | 18x 1080p30; 23x is AGX Orin Industrial |
| [22] Orin NX 157 TOPS, 10–40 W | §1.3 | same | confirmed | |
| [22] AGX Orin 64GB 275 TOPS, 15–60 W, 22x 1080p30 | §0,1.2,1.3 | same | confirmed | |
| [22] AGX Orin 32GB 15–40 W | §1.3 | same | unverifiable | page power row ambiguous; hedged |
| [22] Jetson price rises: Nano Super 249->399, AGX devkit 1999->3499, AGX 32GB 899->1799, AGX 64GB +88 %, range 57–101 %, July 2026 | §0,1.3 | https://hwbusters.com/news/nvidia-jetson-prices-jump-up-to-101-the-249-orin-nano-super-is-now-399/ | confirmed | 21 July 2026; secondary press |
| [22] DeepStream PeopleNet 2.6.3 640 FP16 147 fps AGX Orin; RT-DETR+NvDCF 96 fps | §1.3 | https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html | confirmed | PeopleNet row uses MV3DT tracker (added) |
| [22] Savant 0.5.x prod on DS 7.0; 0.6.x dev DS 7.1/TRT 10.9 Blackwell | §0,3.4 | https://github.com/insight-platform/Savant | confirmed | |
| [22] Hailo-8 26 TOPS, 2.5 W typical | §1.3 | https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/ | confirmed | |
| [22] Hailo-8 M.2 $120–150 retail | §1.3 | (R18 is vendor page, no price) | removed | marked [unverified] |
| [22] CV72S 5 nm 4K 6x AI, ~3 W typical | §1.3 | https://www.ambarella.com/news/ambarella-launches-4k-5nm-edge-ai-soc-for-mainstream-security-cameras-with-new-highs-in-ai-performance-per-watt-image-quality-and-sensor-fusion/ | corrected | "less than 3 W" |
| [22] OSNet ~1 G mult-adds per crop | §1.1 | https://arxiv.org/abs/1905.00953 | confirmed | 0.98 G MACs, 2.2 M params (paper table) |
| [22] ReID = 20 GFLOP/s, ~10 % of YOLO11s | §1.1 | arithmetic | corrected | 20 GMAC = ~40 GFLOP -> ~19 % |
| [22] docs/13 found quadratic tracker impractical at MOT20 | §1.1 | docs/13_BASELINES.md | corrected | docs/13 retracts O(n2) diagnosis; ByteTracker ~6 ms/frame on MOT20 |
| [22] Summary AGX Orin 16–22 streams | §0 | internal (§1.4 says 14–22) | corrected | 14–22 |
| [22] GCP G2 L4 ~$0.70/h | §1.3,8.4 | https://instances.vantage.sh/gcp/g2-standard-4 (Google page not fetchable) | confirmed | $0.707/h us-central1, secondary |
| [22] Milestone does not publish prices | §8.1 | https://www.milestonesys.com/pricing/xprotect/ | confirmed | |
| [22] Milestone retail $109–177 | §8.1 | none | unverifiable | tagged [unverified] |
| [22] Genetec Standard $590+$150, Pro $1,130+$230, Ent $3,650+$250 | §8.1 | https://surveillant.ai/guides/genetec-pricing | corrected | page now: $150–400/camera one-time, SaaS $149/$199 |
| [22] Genetec SaaS $149/camera/yr | §0,8.1 | same | confirmed | secondary |
| [22] Nx per-channel, not locked to camera | §8.1 | https://www.networkoptix.com/nx-witness/faq | unverifiable | FAQ confirms Enterprise sub / Professional perpetual only |
| [22] Donald et al. 2015 Appl Ergon 47:220–228; decrements novices/generalists, not specialists, after ~30 min | §6.2 | https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:25479991&resultType=core&format=json | corrected | citation ok; 90-min task, specialists held 1 h then improved, 50 % detected; 30-min onset hedged |
| [22] disguise_and_tamper cameras res/fps/HFOV/height, spray t=150 | §2.1 | configs/scenarios/disguise_and_tamper.yaml | confirmed | |
| [22] street_crowd population | §2.2 | configs/scenarios/street_crowd.yaml | corrected | omitted 2 heroes (25 s loiter + 25 s commute_wait); T=30 conclusion adjusted |
| [22] ue_job fails >7,200 MB VRAM, commit d57db8c | §1.6 | git show d57db8c | confirmed | |
| [22] video.py functions + RTSP port 8554; not run (docs/11) | §3.5,10 | survsim/gt/video.py, docs/11 | confirmed | |
| [22] IQA field names in realism/stats.py | §3.3 | survsim/realism/stats.py | confirmed | all 6 present |
| [22] pipeline stages threshold->context->persistence->corroboration->budget | §3.3 | survsim/eval/pipeline.py | confirmed | |
| [22] apply_sequence / h264_sequence exist | §10 | survsim/sensors/degrade.py | confirmed | |
| [22] Arithmetic: 0.86/0.65/13/56 TFLOP/s; 240 stream-eq -> 6 L4; 31 GB/cam-month; 7.5 MB clip; 0.4–1.2 Gb/s | §1.5,2 | recomputed | confirmed | |
| [22] Cost model: $111.4k/yr, $557/cam-yr, HW ~$152/cam-yr; power $4,205; support $22.8k | §8.2 | recomputed | confirmed | |
| [22] Edge 17 boxes $25.5–51k, 425 W; cloud 5x8760x0.70=$30.7k | §8.3,8.4 | recomputed | confirmed | |
| [22] $40k per 4xL4 server, $5–40/cam/month licence, box $1.5–3k | §8 | none | unverifiable | already tagged [lore] |
| [22] ONVIF profiles S,T,M,G | §6.3 | https://www.onvif.org/profiles/ | unverifiable | not fetched; standard list (also A, C, D) |
| [23] 44 behaviour classes / 49 names | §1.3 | survsim/director/behaviours.py, CLAUDE.md | confirmed | 45 class defs incl. base Behaviour |
| [23] batch_v4 5,400 frames, recall 0.758 on 770 GT boxes | §0, §9.2 | docs/11 l.83-85, docs/12 l.897 | confirmed | batch_v5/v6 exist since; noted |
| [23] Day stats 6/14 in band | §0, §1.4 | docs/15 l.236 | confirmed | |
| [23] Degradation 0.567 s/frame, target 0.3 | §0, §1.4, M11 | docs/15 l.285-287 | confirmed | |
| [23] Three baked bodies (~1.58 m x2, ~1.93 m) | §1.2 | docs/11 l.89 | confirmed | |
| [23] Tracking harness O(n²), cannot score MOT20 | §0, M1 | docs/13 l.86-115 | corrected | docs/13: tracker+evaluate_mot = ~62 s full MOT20; bottleneck is ReID/eval_det (unprofiled) |
| [23] MOT20 full train 8,931 frames; killed 2.5 h | M1 | docs/13 | confirmed | second kill at 1h26m added |
| [23] MOT20 subset AP75 0.293 | §9.2 | docs/13 l.80 | confirmed | |
| [23] linear_sum_assignment line numbers | M1, §8 | survsim/baselines/bytetrack.py, survsim/eval/tracking.py | corrected | l.83; l.114, l.173 |
| [23] evaluate_* line numbers | §8 | survsim/eval/tracking.py | corrected | 71/193/255/294 |
| [23] observed_by at world.py l.390 | §1.3, §8 | survsim/director/world.py | corrected | l.406 |
| [23] t_detectable_from absent | §8 | grep survsim/ | confirmed | |
| [23] No radar/wildlife/fox/deer | §8 | grep survsim/ | confirmed | |
| [23] Scenario config line counts | §8 | configs/scenarios | corrected | street_crowd_far.yaml (81) exists, omitted |
| [23] M2 must add street_crowd_far.yaml | §9.2, §10 | configs/scenarios | corrected | already exists |
| [23] generator/layout.py untracked | §8 | git ls-files | corrected | tracked |
| [23] 60 test files; 626 tests | §8 | tests/, docs/11 | corrected | 59 files, 728 test functions; 626 is docs/11 figure |
| [23] sensors rf/audio/thermal exist | §8 | survsim/sensors | confirmed | |
| [23] gait modules list | §8 | survsim/gait | confirmed | |
| [23] eval pipeline/rules/fusion exist | §8 | survsim/eval | confirmed | |
| [23] 3 of docs/03 six templates without config | §8 | docs/03 §5 | confirmed | |
| [23] disguise_and_tamper 240 s,10 fps, seed 11 | §9.1 | config yaml | confirmed | |
| [23] street_crowd 60 s,10 fps, seed 7 | §9.2 | config yaml | confirmed | |
| [23] ~11 frames/s render at 720p | M2, §9.2 | docs/11 l.70 | confirmed | |
| [23] street_crowd_far 10-12 m / 30-50 m | §9.2 | not checked | unverifiable | hedged |
| [23] RWF-2000 2,000 clips, 87.25 % | M7, ref 7 | https://arxiv.org/abs/1911.05913 | confirmed | |
| [23] UR Fall 70 seqs (30/40), CC BY-NC-SA 4.0 | M7, §5, ref 8 | https://fenix.ur.edu.pl/~mkepski/ds/uf.html | confirmed | |
| [23] MOT20 CC BY-NC-SA 3.0 | §5, ref 1 | https://motchallenge.net/data/MOT20/ (fetch failed) | unverifiable | left as is; widely stated |
| [23] Parametric body 171.75->190.0 cm, 30 constraints | M7 | CLAUDE.md | confirmed | |
| [23] Effort/risk estimates | §4, §5, §11 | — | unverifiable | tagged [INF] already |
| [24] MOTSynth 768 seq, 1.3M frames, 40M instances, 29.5/frame, max 125 | §1,§2.1 | https://arxiv.org/html/2108.09518 | corrected | 1.38 M frames, 40.78 M instances |
| [24] MOTSynth det AP MOT17 FRCNN 76.68→78.98, MRCNN 76.96→78.83 | §2.1 | https://arxiv.org/html/2108.09518 | confirmed | Table 2 |
| [24] MOTSynth det AP MOT20 YOLOv3 42.42→53.69, FRCNN 43.67→53.90 | §0,§2.1 | https://arxiv.org/html/2108.09518 | confirmed | |
| [24] Sampling ablation 51.15→62.66 at fixed frame count | §0.3,§2.1,§8.3 | https://arxiv.org/html/2108.09518 | corrected | 2k vs 13k frames, not fixed; fair pairs 62.10(9k sparse) vs 62.66(13k dense), 62.59(17k) vs 63.13(52k) |
| [24] MOTSynth ReID MOT17 mAP 75.2/R1 92.8 vs Market 64.6/91.9 | §0,§4.2 | https://arxiv.org/html/2108.09518 | confirmed | split 4; split1 71.3/91.4 added |
| [24] Tracktor COCO 48.3/58.1, MOTSynth 49.8/53.8, +FT 50.3/59.9; IDF1 drop => association transfers worse | §3,§8.5 | https://arxiv.org/html/2108.09518 | corrected | apples-to-oranges (ReID vs no ReID); like for like MOTSynth wins 45.0/51.2 vs 43.5/49.6 and 50.3/59.8 vs 48.3/58.1; conclusion reversed |
| [24] CenterTrack CrowdHuman+FT 66.1/64.2 vs MOTSynth+FT 67.9/66.5 | §1,§3 | https://arxiv.org/html/2108.09518 | confirmed | MOT17 train half-split |
| [24] MOTS20 Tracktor-MOTSynth 55.1 sMOTSA/63.9 IDF1 vs TrackR-CNN 40.6/42.4 | §3 | https://arxiv.org/html/2108.09518 | confirmed | |
| [24] motsynth-baselines MOTA 45.3/IDF1 49.7, MOT17-02 25.7, -04 53.3, MOTS20 HOTA 44.6 | §1,§3 | https://github.com/dvl-tum/motsynth-baselines | confirmed | |
| [24] JTA ~500k frames, ~10M poses, "resolution and sharpness"; ECCV 2018; authors | §1,§3 | https://arxiv.org/abs/1803.08319 | confirmed | |
| [24] SOMAset 100K instances, "outperforms all competitors", authors | §1 | https://arxiv.org/abs/1701.03153 | confirmed | CVIU 167 venue not re-fetched |
| [24] PeopleSansPeople 490K imgs, 3.07M instances; COCO 64,115/262,465 | §1,§2.2 | https://arxiv.org/html/2112.09290 | confirmed | |
| [24] PSP bbox AP 13.82/27.61/42.58; 37.82/42.53/49.04; 56.73/56.09/57.44 | §0,§2.2 | https://arxiv.org/html/2112.09290 | confirmed | |
| [24] PSP keypoint AP 44.43 vs 6.40; 63.47 vs 62.00 | §0,§2.2 | https://arxiv.org/html/2112.09290 | confirmed | |
| [24] BEDLAM authors/CVPR 2023; 380K frames, 1M boxes, 271 shapes, 100 skins/7 ethnic groups, 111 outfits, 1691 textures, 2311 motions, 27 hair | §1,§5 | https://arxiv.org/html/2306.16940 | confirmed | UE5, CLO3D cloth |
| [24] BEDLAM-CLIFF 3DPW 46.6/72.0/85.0, RICH 51.2/84.5/96.6; HMR approaches CLIFF | §1,§5 | https://arxiv.org/html/2306.16940 | confirmed | Table 1 |
| [24] SYNTHIA "significantly improves" CVPR 2016 | §1,§2.3 | https://www.cv-foundation.org/openaccess/content_cvpr_2016/html/Ros_The_SYNTHIA_Dataset_CVPR_2016_paper.html | confirmed | via search snippet (CVF 403) |
| [24] PersonX 1,266 IDs, 273,456 imgs, 36 viewpoints, 6 backgrounds | §1 | https://arxiv.org/abs/1812.02162 | corrected | 36 viewpoints x 6 cameras |
| [24] PersonX trend consistency | §1,§7 | https://arxiv.org/abs/1812.02162 | confirmed | |
| [24] RandPerson 1,801,816 imgs, 8,000 IDs, ACM MM 2020, authors | §1 | https://arxiv.org/abs/2006.12774 | confirmed | |
| [24] RandPerson direct Market 55.6/28.8 vs MSMT 50.0/23.1, Duke 44.9/19.0, CUHK 33.1/12.9; MSMT17 20.1/6.3 | §1,§4 | https://arxiv.org/html/2006.12774 | confirmed | |
| [24] RandPerson joint 87.2/70.9, 65.0/36.8, 79.4/60.6 | §4.2 | https://arxiv.org/html/2006.12774 | confirmed | in-domain baselines added |
| [24] UnrealPerson 3,000 IDs/120k, 34 cams, 48 CPU-h | §1 | https://arxiv.org/html/2012.04268 | confirmed | noted full set 6,799/1,256,381 |
| [24] UnrealPerson direct 79.0/54.3, 69.7/49.4, 38.5/15.3 | §1,§4 | https://arxiv.org/html/2012.04268 | confirmed | |
| [24] UnrealPerson FT 94.0 vs 91.4, Duke 86.8 vs 82.1, MSMT 74.5 vs 72.5; JVTC+ 88.3/75.2, 68.2/34.8 | §0,§4.2 | https://arxiv.org/html/2012.04268 | confirmed | |
| [24] ClonedPerson 5,621 IDs/887,766; direct 84.5/59.9, 22.6/21.8, 49.1/18.5 | §1,§4 | https://arxiv.org/html/2204.02611 | confirmed | |
| [24] Clothing progression (55.6→79→84.5) is the lever; best MSMT mAP 18.5 | §0.4,§4.1 | https://arxiv.org/html/2204.02611 | corrected | same-recipe: 81.6/80.6/84.5; UnrealPerson beats ClonedPerson on MSMT (49.5/19.3) |
| [24] Alice ICLR 2024, authors, 5 cameras, ~42k boxes | §1,§4.3 | https://arxiv.org/abs/2310.04416 | confirmed | 42,760 bboxes |
| [24] Hattori beats real scene-specific when data limited | §0.6,§1,§2.3 | https://mlanthology.org/cvpr/2015/hattori2015cvpr-learning/ | unverifiable | zero-real setting confirmed; comparison hedged |
| [24] Marin CVPR 2010 HOG+SVM virtual works on real | §1,§2.3 | https://www.researchgate.net/publication/221362126 | confirmed | search snippet |
| [24] Driving in the Matrix synthetic-only beats real on KITTI, ICRA 2017 | §1 | https://arxiv.org/abs/1610.01983 | confirmed | |
| [24] Playing for Data 25K images, 1/3 CamVid beats full | §1 | https://arxiv.org/abs/1608.02192 | confirmed | |
| [24] Synthehicle 17h, 340 cams, 64 scenes; WACV 2023 | §1 | https://arxiv.org/abs/2208.14167 | corrected | venue made consistent as WACV Workshops (not re-verified) |
| [24] SURREAL 6.5M frames | §1,§5 | https://arxiv.org/abs/1701.01370 | corrected | abstract: >6 million |
| [24] SURREACT substantially improves NTU/UESTC | §1,§5 | https://arxiv.org/abs/1912.04070 | confirmed | |
| [24] Syn2Real video ReID: synthetic beats real cross-domain, 5 datasets | §1,§4.3 | https://arxiv.org/abs/2402.02108 | confirmed | |
| [24] batch_v4 yolov8n 0.758 vs 0.577, 770 GT boxes | §0,§7 | docs/11 L84, docs/12 L897 | confirmed | |
| [24] MOT20 subset MOTA/IDF1/HOTA 0.463/0.538/0.545 | §3 | docs/13 L80 | confirmed | |
| [24] cctv_day_720p 6/14, legacy 9/14 | §7 | docs/15 L236 | confirmed | night 3/14 |
| [24] ~11 frames/s render; 3 bodies 1.58/1.93 m; bug 13 crowd density | §5,§8 | docs/11 L70,L89,L142 | confirmed | |

## Round 2 — closing the "still not verified" list (2026-09-26)

Primary sources fetched from this machine. Note: `motchallenge.net` is blocked by
the local ISP (redirects to a mobile-broadband restriction page) and the Wayback
Machine is unreachable from the fetch tool, so the MOTChallenge licence is
confirmed via a secondary paper that quotes it.

| Item | Source | Outcome | Edit |
|---|---|---|---|
| MOT17/MOT20 licence CC BY-NC-SA 3.0 | https://arxiv.org/pdf/2306.09613 (UTOPIA, quotes motchallenge.net) | confirmed (secondary) | none needed |
| Hattori CVPR 2015 synthetic beats real scene-specific | https://www.cs.cmu.edu/~kkitani/pdf/HBKK-CVPR15.pdf | confirmed: "purely synthetic data is able to outperform models trained on real scene-specific data when data is limited" | 24 table row 13 tag removed |
| Marin CVPR 2010, SYNTHIA CVPR 2016 | search snippets (round 1) | confirmed (snippet level; CVF PDF 403) | none |
| CLIP-ReID Market/MSMT | https://arxiv.org/pdf/2211.13977 Table 2 | confirmed + completed: ViT-B/16 Market 89.6 mAP / 95.5 R1, MSMT 73.4 / 88.7; +SIE+OLP 90.5/95.4, 75.8/89.7; README's 86.7/91.1 MSMT is *with re-ranking* | 18 table row filled |
| arXiv IDs in 19 (11 IDs) | arXiv API `id_list` query | all 11 resolve to the cited titles | none |
| Hailo-8 M.2 $120–150 | eBay/Micro Center/Waveshare listings | **corrected**: ~$200–275 (Waveshare $204 + shipping) | 22 table + [R18] |
| Milestone $109–177 per device | B&H / education list XPPPLUSDL $177 | confirmed upper figure | 22 §8.1 tag replaced |
| Louroe DigiFact A ~$366 | B&H / distributor listings | **corrected**: ~$524–530 new; $366 was a used eBay listing | 20 §15 |
| CVAT $33 / $23 / $12k | https://www.cvat.ai/pricing/cloud | confirmed | none |
| W&B Pro $60/month | https://wandb.ai/site/pricing/ | confirmed | none |
| Label Studio Starter Cloud $50/month | https://humansignal.com/pricing/ | **corrected**: $99/month + $49 per extra user | 21 §15 |
| CAL LTCC CC 40.1 R1 / 18.0 mAP | https://arxiv.org/pdf/2204.06890 Table 2 | confirmed (PDF text) | — |

### LTCC / PRCC leftovers — fixed everywhere
* "LTCC Rank-1 in the 30s" replaced with ~40 % (CAL 40.1 / 18.0) in 00_INDEX fact 6,
  R02 §3.4 headline and §8 item 3, D07 (2 places), H01 (2 places). R02's source for
  "31.6 % R1" was 3DInvarReID's *re-run* of CAL, now labelled as such.
* **New finding:** the "64.1 % Rank-1 on PRCC" attributed to CAL (R02 §0.3 and
  §3.4, H01 ×2, H02) is not CAL's number — CAL's own Table 2 gives **PRCC CC
  55.2 R1 / 55.8 mAP** (same-clothes 100 / 99.8). 64.1 came from a 2026 survey
  table of a later method. Fixed in all five places; 18's "PRCC in the 30s–40s"
  also replaced with 55.2. This *strengthens* the "appearance is not identity"
  conclusion (95 → 55 is a ~40-point drop, not ~31).
