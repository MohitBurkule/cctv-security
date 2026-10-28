# 72 · The "insights" half: forensic search, analytics and reporting

*2026-09-27. the vendor pitches "CCTV footage analysis to detect intruders
**and provide insights**" (`33`). The corpus covers the *detect* half in depth
(`25`–`28`, `58`, `64`). This doc covers the *insights* half: what ships, the
ML behind it, how much storage it needs, how SurvSim can evaluate it, the law,
and interview material.*

**Tags.** **[V]** = verified from a primary source already fetched into this
corpus, with the file named. **[A]** = vendor or API claim with the URL given
but **not fetched this session** (the web-search budget was spent). Treat every
[A] line as "check before quoting". **[INF]** = my arithmetic or inference.

## 0 · Coverage audit: what the corpus already said

I grepped the corpus for each insights capability.

| Capability | Where it is covered | Depth before this doc |
|---|---|---|
| Natural-language video search | `45` §"NL search" (index metadata, don't re-run a VLM), `R05` §video-text retrieval (InternVideo2, QVHighlights) | good on models, **no product/architecture or index budget** |
| Appearance / attribute search | `34` rows (Avigilon, BriefCam, both `[VERIFY]`), `27` | **one table cell** |
| Footfall, dwell, occupancy, heat maps | `51` §5 "insights product class", §5.1 metrics | definitions only, no eval design |
| Incident timelines, journey reconstruction | `27`/`R02` (MTMC), `62` (zones) | MTMC as tracking; **not as a forensic product** |
| Reporting / BI | `51` §5 | thin |
| Retrospective search over weeks | `53` (storage 31.1 TB for 40 cams) | storage of video only; **no index sizing** |
| Vehicles / ANPR | — | **absent** |
| PPE / safety | — | **absent** |
| Anomaly detection | `R03`, `19`, `28` | good |
| Privacy of retrospective search | `44` (Bridges, DPIA, Art 9) | good on live FR; **purpose limitation of search not separated** |

**Gap found:** no interview answer covered "how would you build and *evaluate*
forensic search", so `68` gets Q26 (below).

## 1 · What commercial products ship

Rows were **[A]**; re-tagged [V]/[X] from fetches on 2026-09-27 (AUDIT_72). Pricing is almost never public for
enterprise VMS analytics; where I give none, none is published that I know of.

### 1.1 Avigilon (Motorola Solutions): Appearance Search, Unusual Motion
- **Appearance Search.** You click a person or vehicle, or give attributes
  (gender, upper/lower clothing colour, hair colour, age class), and it returns
  similar appearances across cameras and time, ranked. Architecture as
  documented: analytics cameras or appliances produce per-object "appearance
  signatures" (an embedding) and store them beside the recording on the
  Avigilon Control Center / Unity server. Search is nearest-neighbour over
  those signatures plus attribute filters. https://www.avigilon.com/products/ai-video-analytics/appearance-search **[V]** (fetched 2026-09-27, AUDIT_72): "Filter by age, gender, clothing and faces to search across specific cameras, sites and timeframes". Hair colour and the signature/embedding architecture are *not* on the page — **[INF]**
- **Unusual Motion Detection (UMD).** Learns normal motion per pixel region
  over time without rules and flags or searches for deviations. It is
  retrospective-first: "show me the unusual things on this camera last night".
  https://www.avigilon.com/products/ai-video-analytics/unusual-motion-detection **[X]** — HTTP 404 (fetched 2026-09-27, AUDIT_72); UMD survives only as a feature name on the Alta page below
- **Natural-language search** is now marketed on the cloud line (Avigilon
  Alta, formerly Ava). https://www.avigilon.com/alta **[X]** (fetched 2026-09-27, AUDIT_72): the page lists "Appearance Search™, unusual motion detection, facial recognition, license plate recognition, crowd and object detection and PPE detection" but says nothing about natural-language search or Ava
- Motorola bought Avigilon in 2018 for about US$1.0 bn **[V]** (`FACTS_VERIFIED`, `34`).

### 1.2 BriefCam (Canon): Review / Research / Respond
- **Review** is **video synopsis**: objects from hours of footage are
  re-composited into one short clip, each stamped with its time. The idea
  comes from Pritch, Rav-Acha & Peleg, "Nonchronological video synopsis and
  indexing", IEEE TPAMI 30(11), 2008 (Hebrew University, BriefCam's origin).
  https://doi.org/10.1109/TPAMI.2008.29 **[X] could not load** (DOI → ieeexplore 4444355, empty body) (fetched 2026-09-27, AUDIT_72)
- Filters: class (person, vehicle type), colour, size, direction, speed, dwell,
  path crossing a line or area, appearance similarity, face and ANPR
  (licence-dependent). **Research** gives dashboards (counts, dwell, heat maps,
  path maps). **Respond** gives rule alerts. https://www.briefcam.com/solutions/platform/ **[X]** 404 (fetched 2026-09-27, AUDIT_72). **Correction:** briefcam.com now 301-redirects to https://www.milestonesys.com/products/software/briefcam/ **[V]**, which sells variants *Investigator / Rapid Review / Protect / Insights* (not Review/Research/Respond) and says "Search for class, appearance object type, direction, and other criteria"; synopsis "displaying multiple events simultaneously"
- Canon's acquisition of BriefCam was announced 9 May 2018 and closed
  3 Jul 2018 **[V]** (`FACTS_VERIFIED` l.366).

### 1.3 Genetec Security Center
- Unified VMS (Omnicast) + access (Synergis) + **ANPR (AutoVu)**.
  "Forensic search" works over metadata supplied by camera or partner
  analytics. Genetec has a **Clearance** evidence-management product for
  sharing and redacting. Its strength is the correlation of events across
  subsystems, not in-house deep learning.
  https://www.genetec.com/products/unified-security/security-center ,
  https://www.genetec.com/products/license-plate-recognition **[X]** 404; Security Center page **[V]** (fetched 2026-09-27, AUDIT_72) names Omnicast, Synergis, AutoVu (ALPR), Clearance and forensic search

### 1.4 Milestone XProtect
- An open-platform VMS. **XProtect Smart Client** has "Search" across
  cameras, which uses metadata from any ONVIF Profile M source or plug-in
  (for example BriefCam or Axis). Milestone runs search over **metadata that
  third parties produce**. Milestone is owned by Canon (2014).
  https://www.milestonesys.com/solutions/platform/video-management-software/ **[X]** 404 (fetched 2026-09-27, AUDIT_72); milestonesys.com home **[V]** only for "open-platform software" — the Profile-M search mechanism and Canon ownership are not on it
- **ONVIF Profile M** standardises analytics metadata (objects, attributes,
  events) so a VMS can search it without knowing the vendor.
  https://www.onvif.org/profiles/profile-m/ **[V]** (fetched 2026-09-27, AUDIT_72): "Analytics configuration and information query for metadata", "Generic object classification support", events for counting/face/LPR via metadata stream, ONVIF events or MQTT. This is the interoperability
  point to name in an interview.

### 1.5 Verkada
- Cloud-managed cameras with on-camera storage. "People/vehicle search" by
  attributes; "AI-powered search" in natural language is sold as a
  subscription feature. Licensing is per camera per year, and list prices
  appear through resellers rather than on Verkada's site.
  https://www.verkada.com/security-cameras/ **[V]** (fetched 2026-09-27, AUDIT_72): "AI-powered search, to face search, and reverse image search"; onboard storage "ranging from 30 - 365 days". Per-camera licensing/reseller pricing is not on the page **[INF]**

### 1.6 Axis
- Edge analytics on ARTPEC SoCs (Object Analytics; AXIS Scene Metadata
  delivers classes, colours and bounding boxes as ONVIF metadata). The model
  is "extract on camera, search in the VMS".
  https://www.axis.com/products/axis-object-analytics **[V]** (fetched 2026-09-27, AUDIT_72): "Detect, classify, track, and count humans, vehicles, and types of vehicles", processed "directly on the camera", "preinstalled ... at no extra cost". ARTPEC and Scene Metadata colours are not on that page

### 1.7 Coram, Spot AI (cloud-AI challengers)
- Both market "search your video with plain language" over existing cameras
  through an on-site appliance plus cloud. The likely mechanism, from their
  marketing and job posts, is a CLIP-style image embedding on sampled frames or
  crops, with the text embedding matched against it. Both publish per-camera
  subscription pricing.
  https://www.coram.ai/ , https://www.spot.ai/ **[V]** (fetched 2026-09-27, AUDIT_72): Coram "Build alerts in plain English", "Works with any IP camera"; Spot AI "Iris ... ask any camera a question in plain language", "camera-agnostic". **[X]** "both publish per-camera pricing": neither homepage shows pricing (demo only)
- **[INF]** None publishes a retrieval benchmark. Their claims are demos.

### 1.8 Edge silicon: Ambarella, Hailo
- **Ambarella CV7x/CV3** and the "N1" family market on-camera transformer and
  VLM inference. Ambarella has demonstrated natural-language search at the
  edge. https://www.ambarella.com/ **[X]** (fetched 2026-09-27, AUDIT_72): homepage says only "AI Vision Processors For Edge Applications"/CVflow; CV7/N1/VLM/NL-search claims unsupported there
- **Hailo-8 (26 TOPS)** and **Hailo-15** (camera SoC) run detection and
  embeddings on camera, and Hailo-10H targets generative models.
  https://hailo.ai/products/ **[V]** (fetched 2026-09-27, AUDIT_72): Hailo-8 "26 TOPS", Hailo-15 "up to 20 TOPS" (smart cameras), Hailo-10H "40 TOPS of INT4" (generative AI), Hailo-8L "up to 13 TOPS"
- **[INF]** The consequence for architecture: embedding extraction moves to the
  camera, and the server stores only vectors and metadata. The index budget in
  §2.3 therefore holds whether extraction happens on the camera or on a GPU box.

### 1.9 The pattern **[INF]**
Every product splits into **(a) per-object metadata extraction** at ingest
(class, box, track, attributes, one embedding per track), **(b) a metadata and
vector store** held beside the recording, and **(c) query-time filtering and
ranking**. At query time nobody re-runs heavy models over weeks of pixels; `45`
reached the same conclusion for VLMs. The vendors differ in *who extracts*
(camera, appliance, cloud) and *whether the extractor is theirs*
(Avigilon/Verkada/BriefCam: theirs; Milestone/Genetec: partners through ONVIF M).

## 2 · The CV/ML behind each feature

### 2.1 Building blocks
| Feature | Model / algorithm | Output stored |
|---|---|---|
| Detection + tracking | YOLO/RT-DETR + ByteTrack/BoT-SORT (`25`, `26`) | track id, boxes at a sub-sampled rate |
| **Attribute extraction** | Pedestrian-attribute recognition (PAR) head, multi-label, trained on PA-100K / PETA / RAP. Colour is often done by histogram in a clothing region; vehicle make, model and colour by a classifier | 20–60 sigmoid scores per track, pooled over good frames |
| **Appearance embedding** | ReID backbone (OSNet, CLIP-ReID, TransReID; `27`) giving 256–768-d, L2-normalised, **one per track** (quality-weighted mean of frames) | a vector per track or per camera-segment |
| **Text-to-video** | CLIP / SigLIP / InternVideo2 dual encoder (`R05`); text is embedded at query time and scored by cosine against crop or keyframe embeddings | 1–4 keyframe vectors per track |
| VLM captioning (optional) | small VLM captions *triggered* tracks (`45`: trigger-gating is 170–400× cheaper) | a caption string, which is BM25-indexed |
| **Vector index** | FAISS (IVF-PQ, HNSW) — https://github.com/facebookresearch/faiss ; HNSW from Malkov & Yashunin, arXiv 1603.09320 https://arxiv.org/abs/1603.09320 [V] | ANN graph / inverted lists |
| **Event store** | append-only events (zone entry, line cross, dwell > t, alarm, disposition) in a columnar table or time-series DB; this is the shape of `events.jsonl` | rows keyed by (time, camera, track) |
| **Track summarisation** | keyframe selection (sharpest, largest, frontal); synopsis rendering (BriefCam) | thumbnails plus a synopsis index |
| **Cross-camera journey** | MTMC: ReID similarity × camera-topology transit-time prior (`27`, `70` time-topology gating), plus Hungarian or graph clustering | a global id per track set, with a confidence |
| **Footfall / dwell / occupancy / heat map** | line-cross counting on ground-plane tracks; dwell = time in zone polygon (`62`); occupancy = in − out with drift correction; heat map = ground-plane histogram of foot points (needs calib, `29`) | aggregates per 5–15 min bin |
| **ANPR** | plate detection → rectification → OCR (CRNN/transformer), with a per-country syntax check. IR-illuminated dedicated cameras at 1/1000 s shutter; general CCTV gives poor plate reads | plate string, confidence, crop |
| **PPE / safety** | detector classes for helmet/vest; zone rules (person in exclusion zone near machine) | events |
| **Anomaly** | per-camera normality models (Avigilon UMD style), or track-feature density (`R03`, `19`) | a score per track or time bin |

### 2.2 Why "one embedding per track" is the key design choice **[INF]**
Per-frame vectors multiply storage by ~100 and give duplicate hits. Per-track
pooling removes both problems and lowers noise. It costs you recall when the
tracker switches identities mid-track. That is why IDSW (`26`) is a
*forensic-search* metric as well as a tracking one.

### 2.3 Storage and index budget: 40 cameras × 30 days **[INF]**
Assumptions: 1080p H.265 at 2.4 Mbit/s continuous (the `53` row). Traffic of
**500 tracks per camera per day** (a quiet CNI site) and **5,000** (a busy
transport or retail site). Each track stores: 1 ReID vector 512-d fp16 (1 KB)
+ 4 CLIP keyframe vectors 768-d fp16 (6 KB) = 5 vectors; ~100 sub-sampled
boxes × 32 B; 200 B of attributes/metadata. HNSW with M = 32 costs
≈ 2M × 4 B = 256 B of links per vector.

| Item | Quiet (500/cam/day) | Busy (5,000/cam/day) |
|---|---|---|
| Video: 2.4 Mbit/s × 86,400 s / 8 × 30 d × 40 | **31.1 TB** | 31.1 TB |
| Tracks in 30 days | 600,000 | 6,000,000 |
| Vectors (5 per track) | 3.0 M | 30 M |
| Raw vectors, fp16 | 4.3 GB | 43 GB |
| HNSW links | 0.77 GB | 7.7 GB |
| Boxes (100/track) | 1.9 GB | 19 GB |
| Attributes + metadata | 0.12 GB | 1.2 GB |
| **Index total** | **≈ 7.1 GB (0.02 % of video)** | **≈ 71 GB (0.23 %)** |
| Same vectors IVF-PQ at 64 B | 0.19 GB | 1.9 GB |

Consequences:
1. **The index is a rounding error beside the video.** The quiet site fits in
   RAM on one server, and the busy site fits with PQ. The storage bill is video
   retention, not search.
2. **Metadata can outlive video**, and legally this is the dangerous part (§4):
   a 7 GB index of every person's appearance for a year is cheap to keep, so
   the retention policy has to cover the index explicitly.
3. **Ingest compute:** 5,000 tracks/cam/day × 40 = 200k tracks/day ≈ 2.3
   tracks/s averaged. Embedding 5 crops per track is ~12 crops/s, which is
   trivial against detection at 40 cams × 5–10 fps = 200–400 frames/s.
   Detection dominates, as `43` found.
4. **Query latency:** HNSW over 30 M vectors answers in ~ms. An attribute plus
   time/camera pre-filter shrinks the candidate set first. Use filtered search
   (FAISS IDSelector, or partition by camera-day) so results are not starved
   post-filter.

## 3 · Evaluating forensic search with SurvSim ground truth

Real CCTV cannot tell you *who was actually in a red jacket at gate B at 02:14*.
SurvSim records it by construction:

| GT artefact | Used for |
|---|---|
| `identities.parquet` (uid, height, wardrobe per **appearance epoch**) | attribute truth (upper colour, garment) *as worn at that time*; clothes changes invalidate naive "red jacket" labels |
| `world.parquet` (actual pose per tick, after avoidance) | truth of where each uid was, including when no camera saw them |
| MOT files (boxes from rendered masks, with occlusion) | which uid was **usably visible** (`geometry.usably_visible`) on which camera and when; this is the retrievable set |
| `events.jsonl` (behaviours, zone entries, tamper) | event queries ("who entered the fence zone after 02:00") and incident timelines |
| `calib/` | ground-plane heat maps, dwell and footfall truth; journey positions |

### 3.1 Metrics
- **Attribute + time + place query** ("person in red upper, 02:00–03:00,
  gate B cameras"). The relevant set R = uids with the attribute in their
  active epoch **and** usably visible on those cameras in the window. The
  system returns ranked tracks, and a track counts as relevant if its majority
  GT uid ∈ R. Report **uid-level recall@k** (k = 10, 50: roughly one operator
  screen and one scroll), mAP, and **time-to-first-hit** in screens. A
  duplicate track of the same uid is not a second hit. Principle 4: an operator
  cares about finding the person, not about tracks.
- **Hard negatives** (principle 3): distractors in dark red, orange or maroon,
  red *bags*, and the same person before and after taking the jacket off (the
  epoch boundary). Report precision at the negative-heavy slices separately.
- **Journey reconstruction.** For a probe uid, the system outputs an ordered
  list of (camera, t_in, t_out). Compare against the GT visit sequence of
  usably-visible segments. Metrics: segment **recall/precision**, **edit
  distance** of the camera sequence, **temporal IoU** per segment, and
  **full-journey accuracy** (fraction of probes whose sequence is exactly
  right). IDF1 across cameras (`26`) is the tracking-side complement.
- **Footfall / dwell.** Absolute error of counts per 15-min bin against GT line
  crossings from `world.parquet`. For dwell, the error of the median dwell per
  zone. Report the invisible fraction too: GT crossings no camera saw set a
  ceiling that the analytics cannot beat.
- **NL query** ("man carrying a ladder near the fence"): same recall@k, with R
  from `events.jsonl` behaviour labels and props.

**H37 mock-only slice, run (2026-09-27):** on 50 seeded mock worlds the
pooled-vs-per-epoch recall@10 gap does **not** appear at the population level
(diff +0.0004 [+0.0001, +0.0008] clean, -0.0118 [-0.033, +0.009] at 10 %
attribute noise — two orders of magnitude below the 0.15 bar at both noise
levels), even though the pooling mechanism is directly demonstrated at the
unit level (a uid retrieved on an attribute+visit combination that never
co-occurred). The reason is a ceiling effect built into this mock design:
relevant-set sizes are small (mean 2.67, max 9, all ≤ 10 over 1363 scored
queries at 40 identities x 6 attribute combinations), so recall@10 saturates
before pooling's extra false-positive candidates can push a true hit out of
the top 10. The design-level claim that SurvSim can evaluate forensic search
still stands (the GT and metric machinery ran end-to-end); what does not
survive is the *expectation* that per-epoch pooling would show up as a
recall@10 win at this scale — a discriminating design needs recall@1/MRR or a
larger identity pool (**H37b**, `66`); `32` §H37, `13`.

### 3.2 H37 (to add to `66`, 49 §12 template)

## H37 · Forensic attribute search recall and the epoch trap (`h37_forensic_search`)
- **Hypothesis:** On SurvSim runs with appearance-epoch changes, uid-level
  recall@10 for attribute+time+place queries is ≥ 0.15 lower when attributes
  are pooled per *track* than per *epoch-segmented track*. A CLIP text query
  has lower recall@10 than a PAR-attribute filter on the same queries.
- **Arms:** (A) PAR attributes pooled per track; (B) PAR pooled per epoch
  segment (split at attribute change-points); (C) CLIP ViT-B text→crop cosine;
  (D) B ∧ C re-rank. All on the same tracker output.
- **Seeds:** 5 scenario seeds × 60 generated queries (colour × garment × window
  × camera group), ≥ 30 % with an epoch boundary inside the window.
- **Metric:** uid recall@10, mAP, and journey edit distance for 20 probes;
  bootstrap 95 % CIs (49 §5).
- **Stopping:** fixed.
- **Cost:** CPU for the mock backend (attribute oracle + noise) now; GPU light
  on batch_v8 renders for C/D. CC0 characters only (MetaHuman renders
  excluded, licence).
- **Decision:** whether the product segments attributes at change-points, and
  whether NL search ships as a primary query or as a re-ranker.
- **49 §12 fields added (AUDIT_72):** *primary metric* = uid recall@10 on the
  epoch-boundary query subset (mAP, edit distance are secondary); *control
  arm* = A; *held fixed* = tracker output, PAR/CLIP checkpoints, query set;
  *analysis* = paired bootstrap over queries (seed-clustered), α = 0.05, Holm
  over B−A, C−B, D−B; *success* = B−A ≥ 0.15 with CI lower bound > 0;
  *sample size* = 300 queries, ≥ 90 with a boundary; *confounds* = mock
  attribute-oracle noise level (report two levels); *abandon if* B−A CI
  includes 0 at both noise levels.

## 4 · Privacy and law for retrospective search

Legal detail is in `44`; this section covers what is specific to *search*.

1. **DPIA is mandatory.** UK GDPR Art 35(3) and the ICO high-risk list
   (innovative technology, tracking) **[V]** (`44` §1.3; S6/S7:
   https://www.legislation.gov.uk/eur/2016/679/article/35). A searchable
   appearance index is "tracking" in the plainest sense, so the DPIA must
   name forensic search as its own processing operation, separate from live
   alarms.
2. **Purpose limitation (Art 5(1)(b)).** Footage collected "for the
   prevention and detection of crime on this site" cannot become footfall
   marketing analytics without a compatible-purpose assessment. Search must be
   **tied to an incident reference**, and the query log is the audit trail
   (`59`). **[INF] from Art 5 (https://www.legislation.gov.uk/eur/2016/679/article/5) [V] (fetched 2026-09-27, AUDIT_72): 5(1)(b) "not further processed in a manner that is incompatible"**
3. **Storage limitation / retention.** Keep video and the metadata index on
   the **same or shorter** clock. §2.3 shows the index is cheap enough to keep
   forever, so it has to be governed explicitly. The ICO CCTV guidance expects
   retention to be justified and set as short as possible **[V]** (`44` S5).
4. **Surveillance Camera Code, Principle 8.** Operators should meet approved
   standards. In the amended 2021 Code, principle 8 concerns "approved
   operational, technical and competency standards" **[V]** (`44` S1:
   https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version).
   Principles 6 (storage no longer than necessary) and 7 (access restricted to
   defined purposes) bear directly on search.
5. ***Bridges* [2020] EWCA Civ 1058** **[V]** (`44` §3; press summary
   https://www.judiciary.uk/wp-content/uploads/2020/08/R-Bridges-v-CC-South-Wales-ors-Press-Summary.pdf).
   The Court of Appeal found **governance** failures: discretion over who and
   where was too broad, the DPIA was deficient, and there was no bias
   enquiry under PSED. It did **not** find a failure of proportionality. For
   search: define who may search, for what, with what approval, and test
   attribute and ReID performance across demographic groups.
6. **The attribute/biometric line.** Special-category *biometric data*
   (Art 9) is personal data from specific technical processing of physical or
   behavioural characteristics **used to uniquely identify** a person **[V]**
   (`44` S4, S10 ICO biometric recognition guidance). Therefore:
   - "Red upper, blue lower, backpack" filtering → personal data, **not**
     biometric. It narrows candidates without identifying anyone.
   - A ReID embedding used to find *the same individual* across cameras sits
     close to the line. It is not face recognition, but it is processing
     designed to single out one person. **[INF]:** treat it as high-risk in the
     DPIA, bound it to an incident, and keep embeddings on the video's
     retention clock.
   - Face matching against a watchlist → biometric, Art 9 condition needed.
     This is *Bridges* territory, and under EU AI Act Art 5 real-time remote
     biometric ID in public spaces is prohibited for law enforcement with
     narrow exceptions **[V]** (`44` S9).
   - A line to rehearse: *"We search by what people wear, not by who they are;
     identity is a human decision made after the search, logged against an
     incident."*

## 4b · ANPR (gap filled, AUDIT_72)

- **Standard.** *National ANPR Standards for Policing and Law Enforcement*
  (NASPLE), v3.5, July 2026, gov.uk
  https://www.gov.uk/government/publications/national-anpr-standards/national-anpr-standards-for-policing-and-law-enforcement-accessible-version
  **[V]** (fetched 2026-09-27). §9.7: static/moveable/multi-lane cameras must
  "capture 98% of all VRM ... and accurately read 95% of captured VRM";
  CCTV-integrated 85 % capture / 95 % read; mobile-moving 80 % / 95 %.
  **[INF]** End-to-end correct read for a static site camera is therefore
  specified at ≥ 0.98 × 0.95 ≈ **93 %** of passing plates.
- **Retention (§10.4) [V]:** national (NAS) records "deleted 12 months after
  their initial capture"; local components 90 days; third-party systems
  "within 7 days". Quarterly NAS compliance dashboards exist (Q1–Q2 2025:
  overall compliance 91 %) — they report governance, not read accuracy **[V]**.
- **Private operators** fall under the ICO, not NASPLE: DPIA "prior to
  deployment", keep data "for the minimum period necessary", data-sharing
  agreement for any police feed **[V]** (ICO ANPR guidance,
  https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/additional-considerations-for-technologies-other-than-cctv/automatic-number-plate-recognition-anpr/).
- **Defence-site gate [INF].** ANPR is an *access-control credential check*
  at a chokepoint, not an analytic: plate read → allow-list (vehicle pass) →
  barrier + booking record, fused with the driver's pass (Genetec AutoVu +
  Synergis is the productised form). Design to the 95 % read figure: ~5 % of
  permitted vehicles need a guard-read fallback, so the failure mode is
  *queue*, not *breach*; the breach risk is a cloned plate, which ANPR alone
  cannot see — pair it with make/model/colour from the appearance index (§2)
  and flag plate-vs-vehicle mismatch. Retain non-hit reads on the local
  90-day analogue unless an incident reference extends them (§4 purpose
  limitation). SurvSim has no plate renderer; evaluation needs real data.

## 4c · PPE / safety analytics (gap filled, AUDIT_72)

- **What ships [V]:** Avigilon lists "PPE detection" ("verifying compliance
  with AI-powered video analytics that spot missing PPE") on its analytics and
  Alta pages; BriefCam (Milestone) alerts on "safety events" (§1.2). Typical
  classes: hard hat, hi-vis vest, mask, gloves, glasses, restricted-zone entry.
- **Accuracy on public datasets [V]:**
  - **SH17** (Ahmad & Rahimi, arXiv 2407.04590): 8,099 images, 17 classes,
    75,994 instances, manufacturing; best YOLOv9-e mAP "exceeds 70.9%".
  - **CHV** (Wang et al., *Sensors* 2021, repo
    https://github.com/ZijianWang-ZW/PPE_detection): 1,330 images, person +
    vest + 4 helmet colours; "YOLO v5x owns the best mAP, 86.55%", YOLOv5s
    52 FPS. (MDPI page returned 403; figures from the authors' repo.)
  - **[INF]** Small, close-range, per-image mAP; the 16-point gap is class
    count (6 vs 17) and small items (gloves, glasses) rather than model. At CCTV
    standoff (20–40 px heads) expect materially lower — measure on site.
- **Different false-alarm economy [INF].** Intruder detection has a
  near-zero base rate, a high cost per miss and an operator who must respond,
  so the budget is FA per camera-hour (H35). PPE non-compliance is *common*,
  low-severity per event and usually *not* acted on live: the output is a
  compliance rate per shift/zone. So (a) precision matters more than recall —
  a false "no helmet" is an HR accusation; (b) errors average out in an
  aggregate but not in a per-person citation; (c) the operator budget is
  replaced by a reporting cadence; (d) it is workplace monitoring of
  employees, so ICO employment guidance and a DPIA apply, and per-person
  attribution should be off by default. Scoring: per-zone compliance-rate
  error, not alarms per camera-hour.

## 5 · Interview material

### 5.1 Ten Q&As
**Q1. "How would you build 'find the man in the red jacket' across 40 cameras?"**
Extract at ingest: track, then pool PAR attributes and a ReID vector per track
(segmented at attribute change-points), stored beside the recording. Querying
is a pre-filter on time and camera, an attribute filter, then a re-rank by
embedding. I would never re-run models over the archive.
*Red flag:* "run a VLM over the footage".

**Q2. "How big is the index?"** For 40 cams × 30 days at 500 tracks/cam/day,
~7 GB against 31 TB of video (0.02 %). At 10× traffic it is ~71 GB, or ~2 GB
of PQ vectors. *Red flag:* sizing per frame rather than per track.

**Q3. "CLIP text search vs attribute classifiers?"** Attributes are
calibratable, auditable and robust at 30-px-wide crops. CLIP handles open
vocabulary ("ladder", "hi-vis") but is poorly calibrated on low-res CCTV
crops. Use attributes as the filter and CLIP as the re-rank or open-vocab
fallback, then measure both (H37). *Red flag:* quoting MSR-VTT R@1 as
evidence for CCTV.

**Q4. "How do you evaluate search without ground truth?"** On real data, a
small audited query set with human-verified relevant sets (expensive, and
recall is unknowable because nobody watched everything). In SurvSim, full
truth: uid-level recall@k with epochs and hard negatives. *Red flag:*
precision-only evaluation, since recall is the forensic failure mode.

**Q5. "Journey reconstruction — how and how measured?"** Per-camera tracks,
then MTMC association with ReID × a transit-time prior over the camera graph.
Output an ordered visit list with confidence, and let a human confirm each
hop. Measure edit distance and per-segment tIoU against GT visits.
*Red flag:* claiming a fully automatic journey across a site with blind spots
(`survsim rig` shows where they are).

**Q6. "Footfall/dwell numbers for the client's BI?"** Line-cross on
ground-plane tracks (calibrated), aggregated in 15-min bins, reported with an
error bar from a validation period. Watch occupancy drift (in − out) and reset
it. *Red flag:* counting detections instead of tracks.

**Q7. "Is appearance search biometric?"** Attribute search is not, because it
does not uniquely identify. ReID-based same-person search is close to the
line, so handle it as high-risk in the DPIA. Face-watchlist is Art 9 and
*Bridges*. *Red flag:* "it's anonymous because we don't store names".

**Q8. "Retention for the metadata?"** The same clock as the video or shorter,
purged together. The query log is kept longer as the audit trail. *Red flag:*
"metadata is small so we keep it".

**Q9. "ANPR on general CCTV?"** Mostly no. Plates need a dedicated IR camera,
a fast shutter and ~130+ px character height, so general cameras give poor
plate reads. Use vehicle type and colour attributes there, and integrate a
proper ANPR feed (Genetec AutoVu, or the BOF/NASPLE feed for police).
*Red flag:* promising plates from a 4 mm dome at 30 m.

**Q10. "How do live alarms and forensic search share a pipeline?"** One ingest
(decode → detect → track → attributes/embeddings → events). Alarms are a
stream consumer with budgets per camera-hour. Search is a batch consumer of
the same store. Operator dispositions feed back into both (`51` §5A).
*Red flag:* two separate model stacks that disagree about what happened.

### 5.2 Whiteboard in 10 minutes: 40 cameras, live alarms + forensic search
```
 40 IP cams (H.265 2.4 Mb/s, RTSP/ONVIF) ──► VMS recorder ── 31 TB / 30 d (ring)
            │ substream 720p @ 5-10 fps
            ▼
 ┌─ GPU ingest node(s) ─────────────────────────────────────────┐
 │ decode(NVDEC) → detect → track → per-track:                  │
 │   PAR attributes · ReID vec (512) · 4 CLIP keyframes · thumbs │
 │   zone/line events (calib + site zones, 62)                   │
 └───────┬───────────────────────────────┬──────────────────────┘
         │ events (stream)               │ track records (batch, per minute)
         ▼                               ▼
 ┌ Alarm engine ────────┐     ┌ Metadata store ─────────────────────────┐
 │ rules + learned score│     │ columnar tracks/events (Parquet/TSDB)   │
 │ θ per camera (H35)   │     │ FAISS HNSW / IVF-PQ  ~7-71 GB           │
 │ FA/cam-h budget      │     │ partitioned by camera-day, same TTL as  │
 └──────┬───────────────┘     │ video; query log = audit trail          │
        ▼                     └──────┬──────────────────────────────────┘
 Operator console ◄── alarms         │  query: time∧camera → attrs → ANN
   dispositions ──► labels/drift(71) ▼  re-rank → journey (MTMC+topology)
   incident ref ──────────────► Forensic UI: results, synopsis, timeline, export
   RBAC · DPIA · redaction on export · BI aggregates (footfall/dwell, 15-min)
```
Talking points: one ingest path; index ≪ video; retention coupled; search
gated by incident reference; eval via SurvSim GT (H37).

## Sources
- Corpus-verified: `44` S1, S3–S7, S9, S10 (URLs above); `FACTS_VERIFIED`
  (Canon–BriefCam, Motorola–Avigilon); `53` storage table; `45`, `R05`
  (retrieval models); `51` §5 (insights metrics).
- Vendor pages, fetched 2026-09-27 — per-claim [V]/[X] inline and in `AUDIT_72.md`: avigilon.com (Appearance
  Search, UMD, Alta); briefcam.com; genetec.com (Security Center, AutoVu);
  milestonesys.com; onvif.org Profile M; verkada.com; axis.com; coram.ai;
  spot.ai; ambarella.com; hailo.ai.
- Methods: Pritch et al., TPAMI 2008 **[X] unloadable**; FAISS **[V]** ("A library for efficient similarity search and clustering of dense vectors"); HNSW arXiv 1603.09320 **[V]** (Malkov & Yashunin) — AUDIT_72.
- Arithmetic **[INF]:** §2.3, reproducible with `python3 -c` from the stated
  assumptions.
