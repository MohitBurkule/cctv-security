# 56 · Glossary (interview terms)

One or two lines each, with where the corpus treats it. `§` = section of the
numbered doc. Formulas live in `55`. Where FACTS_VERIFIED disagrees with a
dossier, FACTS wins.

## Operations, standards and alarm handling

| Term | Definition | Where |
|---|---|---|
| ARC | Alarm Receiving Centre: receives and handles alarm signals; construction/staffing governed by BS EN 50518. | 51, 33 |
| RVRC | Remote Video Response Centre: monitoring company that views alarm-triggered video; NPCC Appendix R (Mar 2024) rules. | 51 |
| BS 8418 | BS 8418:2021, design, installation, commissioning, maintenance and remote monitoring of detector-activated remote-monitored CCTV. | 51 |
| NSI Gold | NSI's top certification tier for security/fire providers (NACOSS Gold for security systems); per nsi.org.uk (fetched 2026-09-26) **all Gold schemes include ISO 9001**, optionally ISO 14001/45001; UKAS-accredited. Which BS/EN product standards a given scheme audits is scheme-specific — not confirmed. | nsi.org.uk, AUDIT_55-56 |
| NPCC false-call rule | 3 false calls in 12 months can withdraw police response to a site. | 51 |
| i-LIDS | UK Home Office benchmark (sterile zone, abandoned object, parked vehicle…); an alarm later than the tolerance (10 s) counts as a false alarm. | 28 §1.1, FACTS |
| PETS 2006 | Abandoned-luggage benchmark with a spatial (distance-to-owner) rule. | 28 §1.2 |
| ActEV / VIRAT | NIST activity-detection evaluation; scores activities, not alarms. | 28 §1.3 |
| DORI | 2014 pixel-density levels: 25/62.5/125/250 px/m for Detect/Observe/Recognise/Identify. | 29 §6.2 |
| IEC 62676-4:2025 | Seven levels, Overview 20 → Scrutinize 1500 px/m; Perceive/Characterize coincide with Recognise/Identify. | 29 §6.3 |
| Nuisance alarm | A true detection of an irrelevant cause (fox, tree, rain) — distinct from a false detection, but costs the operator the same. | 28 §7, R03 |
| Operator budget | Alarms per camera-hour an operator can actually assess; the denominator for every alarm metric (e.g. 0.1 or 0.001 (assumed, 28 §6) FA/cam-h). | 28 §7.1, 51 |
| False alarms per camera-hour | Principle-4 metric: FA count ÷ camera-hours of exposure; bounded by Poisson/rule of three. | 49 §5, 28 §6.2 |
| Operator utilisation | U = C·B·t/3600 (cameras × alarm rate × handling seconds). | 51 |
| Hard negative | Innocent behaviour that fires the same rule (commute_wait vs loiter); required pair for every positive. | 28 §7.3, CLAUDE.md |
| Base rate | Prevalence of true events; at 3.3 % prevalence even R 0.72 gives P 0.074. | 28 §7.2, 42 |
| Soak test | Long run on live/mock video counting false alarms; 0 in T ⇒ rate < 3/T. | 49 §5 |
| Tamper detection | Detecting a camera moved, covered, defocused or blinded; GT must follow the live camera. | 50, CLAUDE.md |

## Video pipeline

| Term | Definition | Where |
|---|---|---|
| RTSP | Control protocol (DESCRIBE/SETUP/PLAY); media travels in RTP, timing in RTCP. | 43 §1.1 |
| RTP / RTCP | Media packets with timestamps; RTCP sender reports map them to wall-clock (NTP). | 43 §1.2 |
| ONVIF Profile S | Basic streaming profile; being retired (deprecation in process). | 43 §2 |
| ONVIF Profile T | H.264/H.265, imaging, motion/tamper events, metadata streaming, HTTPS streaming. | 43 §2 |
| ONVIF Profile M | Metadata/analytics events profile. | 43 §2 |
| GOP | Group of pictures: one I/IDR frame then P/B frames; long GOPs (1–4 s) on CCTV; noise "pumps" at the GOP period. | 43 §3, 40 §A9 |
| I / P / B frame | Intra-coded; forward-predicted; bi-predicted (needs a future frame ⇒ reorder latency). | 43 §3.2 |
| H.265 / HEVC | ~40 % lower bitrate than H.264 at similar quality (assumption used for storage). | 53 §1.1 |
| Sub-stream | Low-res camera stream (e.g. 720p/10 fps/1 Mbit/s) fed to analytics while main goes to the VMS. | 43 §8.1 |
| NVDEC | NVIDIA hardware video decoder; often the real stream limit (Orin NX 16 GB: 18 × 1080p30 H.265). | 43 §4, FACTS |
| DeepStream | NVIDIA GStreamer-based analytics SDK: decode → mux → infer → track → msgbroker. | 43 §6 |
| nvstreammux | DeepStream plugin that batches frames from many streams into one inference batch. | 43 §6.2 |
| nvinfer / nvtracker | TensorRT inference plugin; tracker plugin that bridges frames skipped by `interval`. | 43 §6.3–6.4 |
| Backpressure | Downstream slowness propagating upstream; policy decides which frames to drop. | 43 §7 |
| NTP / PTP | Clock sync: ms-level vs sub-µs; multi-camera fusion needs frame-level alignment. | 43 §5 |
| VMS | Video management system (Milestone XProtect MIP SDK, Genetec Security Center). | 43 §9 |
| TensorRT | NVIDIA inference compiler; symmetric INT8 with entropy calibration (`IInt8EntropyCalibrator2`). | 38 §2.1 |
| PTQ / QAT | Post-training quantisation vs quantisation-aware training; PTQ usually enough at 8-bit. | 25 §6.3, 38 §2.1 |
| SWaP-C | Size, weight, power and cost — the edge-deployment constraint. | 38 §1.4 |

## Detection

| Term | Definition | Where |
|---|---|---|
| Anchor-free | Predict box distances per cell (FCOS, YOLOv8/11) instead of offsets from template anchors. | 25 §1.3 |
| DETR / RT-DETR | Set prediction with Hungarian matching loss; NMS-free; RT-DETR at YOLO speeds. | 25 §1.4–1.5 |
| NMS / Soft-NMS | Greedy suppression of overlapping boxes / decaying scores instead; crowd failure mode. | 25 §2.7, 40 §A1 |
| DFL | Distribution Focal Loss: box edge as a discrete distribution over reg_max bins. | 25 §2.2 |
| TAL | Task-aligned assigner, t = s^α u^β, picks positives where score and IoU agree. | 25 §2.5 |
| SAHI | Slicing-aided inference: tile the frame to enlarge small people. | 25 §3.4 |
| AP50 / AP50:95 | AP at IoU 0.5 / mean over 0.50–0.95; AP50 is closer to CCTV's question. | 25 §4.1 |
| Amodal box | Box around the full (including occluded) extent; MOT20 GT is amodal. | 52, FACTS |
| Modal / visible box | Box around visible pixels only; our mask-derived "tight GT" is modal. | 46, FACTS |
| ECE | Expected calibration error: weighted gap between confidence and accuracy per bin. | 25 §5.1, 49 §9 |
| Temperature scaling | Divide logits by T to calibrate; AP unchanged. | 25 §5.2 |

## Single- and multi-camera tracking

| Term | Definition | Where |
|---|---|---|
| Kalman filter | Linear-Gaussian predict/update giving the predicted box for matching. | 26 §2 |
| Hungarian algorithm | Optimal linear assignment on a cost matrix (O(n³) via Edmonds–Karp/Tomizawa; Munkres' original O(n⁴)); gating removes invalid pairs first. | 26 §3 |
| SORT / DeepSORT | KF + Hungarian on IoU; DeepSORT adds appearance embedding and Mahalanobis gate. | 26 §5.1–5.2 |
| ByteTrack | Two-stage association; low-score boxes can extend, never start, tracks. | 26 §5.3 |
| OC-SORT | Observation-centric re-update, momentum term; fixes KF drift after occlusion. | 26 §5.4 |
| BoT-SORT | ByteTrack + CMC + ReID + (x,y,w,h) KF state. | 26 §5.5 |
| CMC (motion) | Camera-motion compensation: warp predicted boxes by estimated global motion (PTZ/shake). | 26 §5.6 |
| CMC (ReID) | Cumulative matching characteristic: rank-k curve. Same acronym — say which. | 27 §4.1 |
| ID switch / Frag | Track's matched GT identity changes / GT track interrupted then resumed. | 26 §4 |
| MOTA | 1 − (FN+FP+IDSW)/GT; detection-dominated. | 26 §6.1 |
| IDF1 | Identity F1 under a global one-to-one trajectory bijection. | 26 §6.2 |
| HOTA | √(DetA·AssA) averaged over 19 IoU thresholds. | 26 §6.3 |
| DetA / AssA | Detection Jaccard / mean per-TP association Jaccard; our repo bug ignored FPs in DetA (HOTA 0.545 → 0.434 after fix; 0.443 after TrackEval parity). | 26 §6.3, §8.2 |
| MOT20 | Crowded MOT benchmark (127.04 people/frame mean over the training set, up to 246 in one sequence — Dendorfer et al. arXiv 2003.09003 Tab. 1); non-commercial licence. | 26 §7, 40 §C6 |
| JPDA | Joint probabilistic data association: β-weighted soft assignment; coalescence failure. | 37 §3.3 |
| MHT | Multiple hypothesis tracking: keeps a tree of association hypotheses over frames. | 37 §3.1 |
| PHD / GM-PHD | Random-finite-set filter propagating target intensity; Gaussian-mixture closed form; no labels. | 37 §3.1 |
| Stone Soup | Dstl open-source tracking framework (JPDA, MFA, GM-PHD, PMHT). | 37 §3.2 |
| OSPA | Set-distance metric for fused multi-target tracks. | 37 §7 |

## ReID and gait

| Term | Definition | Where |
|---|---|---|
| ReID | Matching the same person across cameras/time by appearance embedding. | 27 §1 |
| Triplet / circle / ID loss | Margin on anchor–positive vs negative; per-similarity reweighting; softmax over training IDs. | 27 §2 |
| BNNeck | BatchNorm between triplet feature and ID classifier (bag-of-tricks baseline). | 27 §2.4 |
| OSNet | Lightweight omni-scale ReID CNN. | 27 §3.1 |
| TransReID | ViT ReID with camera/view side-information embeddings. | 27 §3.2 |
| CLIP-ReID | Uses CLIP's image encoder plus learned text prompts per ID. | 27 §3.3 |
| Rank-k / mAP (ReID) | First-hit accuracy / mean AP over all true matches. | 27 §4 |
| k-reciprocal re-ranking | Re-scores gallery by mutual-neighbour sets. | 27 §5 |
| CC-ReID | Clothes-changing ReID; Rank-1 still ~40 % on LTCC. | 27 §8, FACTS |
| LTCC / PRCC | Clothes-change benchmarks; CAL: LTCC 40.1 R1, PRCC 55.2 R1. | 27 §8, 42 |
| Gait recognition | Identity from walking pattern; large lab-to-wild drop. | 27 §9.2, R02 |
| Appearance epoch | SurvSim span where a person's outfit is constant; ReID scored within vs across epochs. | 27 §9.1, 9.3 |
| Transition-time prior | Camera-topology travel-time distribution used to prune cross-camera matches. | 27 §6 |
| MTMC | Multi-target multi-camera tracking (AI City: 71.94 offline). | 27 §6.3, FACTS |

## Synthetic data and sim2real

| Term | Definition | Where |
|---|---|---|
| Domain randomisation | Randomise textures/lighting/pose so the real world is one more variation. | 30 §2.1–2.2 |
| Structured DR | Randomise inside a scene grammar (context kept plausible). | 30 §2.4 |
| MOTSynth | Large GTA-V synthetic pedestrian MOT dataset. | 24, 30 |
| PeopleSansPeople | Unity-based synthetic human dataset generator. | 24, 30 |
| BEDLAM | SMPL-X synthetic human dataset; licence bars surveillance use. | 24, 47 |
| TSTR | Train on synthetic, test on real. | 24 |
| FID | Fréchet distance between Gaussian fits of Inception features; biased, sample-size dependent. | 30 §3.2–3.3 |
| KID | Squared MMD with cubic kernel; unbiased alternative to FID. | 30 §3.4 |
| Generative precision/recall | k-NN fidelity vs coverage split. | 30 §4 |
| Image-statistics matching | SurvSim's 14 physical stats vs a real band (6/14 on committed profile). | 30 §5, 42 |
| Stencil / ID pass | Per-actor CustomDepth stencil rendered as an ID mask → occlusion-aware boxes. | D08, 46 |
| Degradation profile | `sensors/degrade.py` chain (noise, blur, codec, AE) turning clean renders into CCTV. | 30 §6, 20 |
| Poisson–Gaussian noise | Signal-dependent shot noise + read noise; not additive Gaussian. | 30 §6.4 |
| Rolling shutter | Row-sequential exposure skewing moving objects. | 30 §6.5 |
| EV100 | Exposure value at ISO 100: log₂(N²/t) − log₂(S/100). | 30 §6.3, 55 |
| Negative transfer | Synthetic data lowering real AP (0.276 → 0.152 in H1). | 32, 42 |

## Behaviour and anomaly

| Term | Definition | Where |
|---|---|---|
| Dwell / loiter rule | Alarm when time in zone > threshold; can't separate commuter from loiterer. | 28 §2 |
| Social force | Helbing–Molnár pedestrian model of goal + repulsive forces. | 28 §4 |
| VAD | Video anomaly detection (reconstruction, prediction, weakly supervised MIL). | 28 §5 |
| Frame-level AUC | Common VAD metric; flatters systems unusable at operator budgets. | 28 §6.1 |
| Detection window | `--tolerance-s`: how late an alarm may be and still count. | 28 §7.4 |

## Multi-sensor and defence

| Term | Definition | Where |
|---|---|---|
| SAPIENT | UK MOD sensor-fusion interface, published as BSI Flex 335 (registration, status, detection, task messages). | 37 §5 |
| STANAG 4609 | NATO digital motion-imagery standard (implemented via MISB/NGA standards). **[UNSOURCED]** — NGA/MISB pages were CAPTCHA/403-blocked on 2026-09-26; say "NATO motion-imagery format with KLV metadata" and no more. | 37 §6 |
| Detection-level fusion | Fuse raw detections in one tracker vs track-to-track fusion. | 37 §2 |
| JSP 936 | MOD policy for dependable AI in defence; ODD coverage, out-of-ODD response. | 38 §4 |
| DEF STAN 00-055 / 00-056 | MOD software safety / safety management for defence systems; awareness level. **[UNSOURCED]** — dstan.mod.uk requires Defence Gateway login (checked 2026-09-26); scope wording not confirmed from a primary source. | 35 |
| ODD | Operational design domain — conditions the system is certified for. | 38 §4 |
| Dual-use / export control | UK Strategic Export Control List entries relevant to surveillance analytics. | 44 §7 |

## Neuromorphic

| Term | Definition | Where |
|---|---|---|
| DVS / event camera | Pixels report log-brightness changes asynchronously; blind to static targets. | 36 §2, 00 fact 10 |
| SNN | Spiking neural network: binary/graded spikes over timesteps. | 36, D05 |
| LIF | Leaky integrate-and-fire neuron: τ_m du/dt = −(u−u_rest) + RI; leak, integrate, threshold, reset (Gerstner, *Neuronal Dynamics* §1.3). | D05, 55 §15 |
| Surrogate gradient | Smooth pseudo-derivative replacing the spike's step for BPTT training. | 36 §3 |
| ANN→SNN conversion | Map a trained ReLU net's activations to firing rates. | 36 §3 |
| Loihi / Loihi 2 | Intel neuromorphic chips; Loihi 2 has programmable neurons and graded spikes; Hala Point 1.15 B neurons. | 36 §5, D05, FACTS |
| SpiNNaker / SpiNNaker2 | Manchester/Dresden ARM-core neuromorphic platform; v2 accelerates SNNs and DNNs. | 36 §5 |
| SpikeYOLO / I-LIF | Spiking detector with integer-valued training, spikes at inference. | 36 §4, D05 |

## Law and governance (UK/EU)

| Term | Definition | Where |
|---|---|---|
| DPIA | Data protection impact assessment; required for high-risk processing (Art 35). | 44 §1.3 |
| Bridges | *R (Bridges) v CC South Wales Police* [2020] EWCA Civ 1058: live FR unlawful — too much discretion, deficient DPIA, PSED breach. | 44 §3 |
| SCC principles | Surveillance Camera Code of Practice's 12 guiding principles. | 44 §2 |
| Biometric data | Special-category data from technical processing for unique identification; appearance ReID usually not, FR yes. | 44 §4 |
| Remote biometric identification | Identifying people at a distance by biometrics; real-time use in public by police prohibited in EU AI Act Art 5(1)(h) with exceptions. | 44 §6.2 |
| Annex III | EU AI Act high-risk list; point 1 biometrics; applies from 2 Dec 2027 after Omnibus 2026/1744. | 44 §6.3–6.5 |
| EU AI Act Art 5 | Prohibited practices (e.g. sensitive biometric categorisation, untargeted face scraping). | 44 §6.2 |
| Pseudonymisation | Replacing identifiers but re-identifiable — still personal data, unlike anonymisation. | 44 §5.3 |
| PSED | Public Sector Equality Duty (Equality Act s.149) — the bias ground in Bridges. | 44 §3 |
| MetaHuman licence | Bars using characters to train or test AI; CC0 cast is the render default. | 47, 44 §8 |

## Data engineering and statistics

| Term | Definition | Where |
|---|---|---|
| WORM | Write-once-read-many storage (S3 Object Lock) for evidential retention. | 53 |
| BS 10008-1:2020 | Evidential weight and legal admissibility of electronic information. | 53 |
| IVF-PQ | FAISS inverted-file index with product quantisation: 104 M vectors in 7.5 GB. | 53 |
| HNSW | Hierarchical navigable small-world graph ANN index (FAISS, pgvector). | 53 |
| Label noise | ≥ 3.3 % in major benchmarks (Northcutt 2021). | 53 |
| Bootstrap | Resampling the generalisation unit (sequence/camera/block) for CIs. | 49 §1.1 |
| Block bootstrap | Resample contiguous frame windows longer than a track. | 49 §1.1 |
| Wilson interval | Binomial CI that behaves at small n; 8/10 → [0.49, 0.94]. | 49 §1.2 |
| Rule of three | 0 events in T ⇒ 95 % upper rate ≈ 3/T. | 49 §5 |
| McNemar | Paired test on discordant items: (b−c)²/(b+c). | 49 §7 |
| Holm | Step-down family-wise error control. | 49 §4 |
| Benjamini–Hochberg | False-discovery-rate control for exploratory sweeps. | 49 §4 |
| Power analysis | n ≈ 15.7σ²/Δ² per arm; 25 seeds for 0.02 AP at σ 0.025. | 49 §2.2 |
| Pre-registration | Name one primary contrast before running; rest exploratory. | 49 §12 |
| CUSUM | Cumulative-sum drift detector on alarm/score streams. | 49 §10 |
| Leakage (site) | MOT20-01/02 share a site; split by site, not sequence. | 49 §8 |

## SurvSim-specific

| Term | Definition | Where |
|---|---|---|
| usably_visible | The one visibility definition: in frame, in front, ≥ 20 px tall. | 29 §7.3, CLAUDE.md |
| Director / Backend | Engine-agnostic sim core / mock or Unreal renderer behind it. | 52, CLAUDE.md |
| [V] / [A] / [X] | Verified / API exists untried / tried and broken. | CLAUDE.md, 52 |
| Camera director | Drives PTZ and 6 tamper kinds; GT follows the live pose. | 52 |
