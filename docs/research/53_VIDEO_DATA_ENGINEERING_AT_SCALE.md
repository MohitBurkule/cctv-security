# 53 · Video data engineering at scale — storage, indexing, evidence, curation, governance

Written 2026-09-26. Complements `43` (transport, decode, the 40-camera
pipeline budget), `22` (compute sizing, VMS licensing) and `21` (MLOps). This
file is about **the bytes after the pipeline**: where footage lives, how
events and embeddings are indexed, how a clip becomes evidence, how footage
becomes a training set, and what the law says about keeping any of it.

Tags: **[F]** fetched this session (URL in §10), **[R]** from the repo with
file/commit, **[INF]** my inference or arithmetic, **[T]** textbook/standard
knowledge not re-fetched. All arithmetic is shown so it can be redone.

---

## 1. Storage and retention maths

### 1.1 Bitrate assumptions

There is no single "right" CCTV bitrate — it depends on scene activity,
GOP, VBR ceiling and smart-codec features. I use round figures and show how
the answer scales with them.

| Stream | H.264 | H.265 | Basis |
|---|---|---|---|
| 1080p, 15 fps, VBR, typical outdoor scene | **4.0 Mbit/s** | **2.4 Mbit/s** | 4 Mbit/s matches `43` §8.1 [INF]; H.265 at −40 % [INF] |
| 720p, 10–15 fps | **2.0 Mbit/s** | **1.2 Mbit/s** | [INF], same −40 % |
| analytics sub-stream 720p/10 fps | — | 1.0 Mbit/s | `43` §8.1 [R] |

Why −40 %: the literature spans 25–50 % "better data compression at the same
level of video quality", with a BBC/University of the West of Scotland
subjective study averaging **59 %** (56 % at 720p, 62 % at 1080p) and a
PSNR-based measurement at **35.4 %** [F: Wikipedia HEVC, citing those
studies]. Surveillance scenes (static background, noise at night) sit at the
conservative end in my experience, so −40 % is a planning figure, not a
promise. Night IR noise can *double* VBR bitrate — plan headroom on the
ceiling, not the average [INF].

### 1.2 Per-camera volume

`bytes/day = Mbit/s × 10⁶ × 86 400 / 8`

| Stream | GB/day | 30 days |
|---|---|---|
| 1080p H.264 4.0 | 43.2 | **1.30 TB** |
| 1080p H.265 2.4 | 25.9 | **0.78 TB** |
| 720p H.264 2.0 | 21.6 | 0.65 TB |
| 720p H.265 1.2 | 13.0 | **0.39 TB** |

### 1.3 Fleet volume, 30-day continuous retention

| Cameras | 1080p H.264 | 1080p H.265 | 720p H.265 | Ingest at 1080p H.265 |
|---|---|---|---|---|
| 40 | 51.8 TB | 31.1 TB | 15.6 TB | 96 Mbit/s |
| 400 | **518 TB** | **311 TB** | 156 TB | 960 Mbit/s |
| 4 000 | 5.18 PB | 3.11 PB | 1.56 PB | 9.6 Gbit/s |

Raw usable capacity. Add RAID-6/erasure overhead (≈ 1.25× for 8+2) and ~15 %
free-space headroom for write performance ⇒ **×1.4 raw disk** [INF]. The
40-camera row reproduces `43` §8.6 (160 Mbit/s → 52 TB at H.264, 4 Mbit/s).

Levers, in order of size [INF]:
1. **Retention days** — linear. 30 → 14 days halves the bill, and (§7) the
   law pushes that way anyway.
2. **Codec** — H.264 → H.265 ≈ −40 %.
3. **Event-triggered or dual-rate recording** — record the sub-stream
   continuously and the main stream on motion/analytics events. At a 25 %
   activity duty cycle, with a 1.0 Mbit/s sub-stream: 0.25 × 2.4 + 1.0 = 1.6 Mbit/s vs 2.4, −33 %; bigger
   on quiet perimeters, near zero on a busy concourse.
4. **Frame rate** — roughly sub-linear under inter-frame coding; 15 → 10 fps
   saves perhaps 15–25 %, not 33 %.

### 1.4 Hot and cold tiers

Access to CCTV is steeply time-skewed: most retrievals happen within days of
an incident being reported. That gives a natural two-tier design:

| Tier | Holds | Medium | Why |
|---|---|---|---|
| **Hot** | last 3–7 days, all cameras | NVR/VMS local disk (RAID) | instant scrub, operator review, no egress |
| **Warm** | days 8–30 | on-prem object store *or* cloud infrequent-access class | cheap, seconds-to-minutes retrieval |
| **Evidence** | exported incident clips, any age | WORM object storage (Object Lock) | chain of custody (§3) |
| **Dataset** | curated, consented/lawful clips | versioned object store + manifest | ML (§5); separate legal basis |

Cloud object storage prices fetched 2026-09-26 [F]:

| Service | $/GB-month | $/TB-month | Notes |
|---|---|---|---|
| AWS S3 Standard (first 50 TB, us-east-1) | 0.023 | 23 | next 450 TB $0.022/GB; egress $0.09/GB (first 10 TB) |
| S3 Standard-IA | 0.0125 | 12.5 | minimum storage durations apply (30–180 days across classes) |
| S3 Glacier Instant Retrieval | 0.004 | 4 | |
| S3 Glacier Flexible Retrieval | 0.0036 | 3.6 | |
| S3 Glacier Deep Archive | 0.00099 | 0.99 | hours to retrieve |
| Backblaze B2 | — | 6.95 | free egress up to 3× stored; $0.01/GB beyond |
| Wasabi Pay-as-you-go | — | 7.99 | "no fees for egress or API requests" |

The trap [INF]: archive classes carry **minimum storage durations** longer
than a 30-day CCTV retention (AWS lists 30–180 days by class [F]). Writing
30-day footage into a 90-day-minimum class means paying for 90 days *and*
keeping data longer on the invoice than the policy allows on paper. For
30-day rolling video, the sensible cloud classes are Standard-IA-like or the
flat-rate providers; Glacier-class belongs to evidence and long-lived datasets.

Monthly steady-state cost of the 400-camera, 1080p H.265 estate (311 TB) if
**everything** sat in one cloud class [INF from the fetched prices]:

| Class | $/month |
|---|---|
| S3 Standard | ≈ 6 890 (tiered: 50 TB × $23 + 261 TB × $22; flat $23 would be 7 150) |
| S3 Standard-IA | 3 890 |
| Wasabi | 2 490 |
| Backblaze B2 | 2 160 |

Plus ingest bandwidth — 960 Mbit/s sustained upstream per site-aggregate is
the real reason CCTV stays on-prem for the hot tier, not the storage price.

---

## 2. Metadata and event indexing

Video is write-once, read-rarely. Metadata is write-constantly, read-often.
Keep them apart: the video store is keyed by `(camera_id, time range)` and
never queried by content; every content query goes to metadata and returns
time ranges to pull.

### 2.1 Three metadata streams

| Stream | Grain | Rate at 400 cams [INF] | Store |
|---|---|---|---|
| Detections | per frame per object | 400 × 10 fps × ~3 objects = **12 000 rows/s**; ~100 B/row ⇒ ~100 GB/day | *don't keep long*; roll up |
| Tracklets | per object per camera appearance | ~0.1 new tracklets/s/cam ⇒ **40/s, 3.5 M/day** | time-series table |
| Events/alarms | per rule firing | 10²–10⁴/day (the operator budget) | relational, audited |

The detection stream is the one that silently eats disks. The usual pattern
is to keep per-frame boxes only for the hot window (for scrubbing overlays),
and to persist **tracklets**: start/end time, camera, box trajectory
decimated to ~1 Hz, class, attributes (colour histograms, carried object,
vehicle type), best-shot thumbnail pointer, and one or a few **appearance
embeddings**.

Time-series choice [INF]: anything with time partitioning and a secondary
index on camera works — PostgreSQL with native range partitions (or
TimescaleDB hypertables), ClickHouse for heavy aggregation. Partition by day
so that retention is `DROP PARTITION`, not `DELETE … WHERE` — dropping is
instant, auditable, and cannot miss rows. This matters for §7: **retention
must be enforceable in metadata too**, not just in video.

### 2.2 Vector search for ReID embeddings

A "find this person across the estate" query is a nearest-neighbour search
over tracklet embeddings, filtered by time and camera.

Embedding size: a typical ReID backbone emits 512-d (OSNet) or 2048-d
(ResNet-50) features [T]. Assume 512-d float32.

Sizing formulas [F: FAISS wiki; pgvector README]:
- FAISS `IndexFlatL2`: `4·d` bytes/vector.
- FAISS `IndexHNSWFlat`: `4·d + x·M·2·4` bytes/vector (graph links; the wiki's x ≥ 1 is the mean number of levels per vector, ≈ 1 in practice, so the row below is a lower bound).
- FAISS `IndexIVFPQ`: `ceil(M·nbits/8) + 8` bytes/vector (the 8 is the id).
- pgvector `vector`: `4·d + 8` bytes; `halfvec`: `2·d + 8` bytes. HNSW indexes
  up to 2 000 dims for `vector`, 4 000 for `halfvec`; defaults `m = 16`,
  `ef_construction = 64`; since 0.8.0, **iterative index scans** re-query when a
  filter (e.g. time window) leaves too few results.

For the 400-camera estate, 30 days × 3.5 M tracklets/day = **104 M vectors**
[INF], one embedding per tracklet:

| Index | bytes/vector | Total | Fits |
|---|---|---|---|
| Flat float32 | 2 048 | 213 GB | disk, not RAM |
| HNSW flat, M = 32 | ≥ 2 048 + 256 = 2 304 | ≥ 240 GB | a big box's RAM, barely |
| pgvector halfvec | 1 032 | 107 GB (+ index) | Postgres on NVMe |
| IVFPQ, M = 64, 8 bits | 72 | **7.5 GB** | RAM on one node |

Design [INF]:
- **Partition the index by day** (and by site at 4 000 cameras). Queries are
  almost always time-bounded ("last Tuesday, 14:00–18:00"), so searching one
  or two day-partitions beats one global index, and retention is dropping a
  partition.
- **IVFPQ for recall-oriented candidate generation, rerank with exact
  distances** from full vectors stored on disk alongside the tracklet row.
  PQ at 72 B/vector loses ranking precision; reranking the top-k·10
  restores it.
- pgvector is enough up to ~10⁷–10⁸ vectors per partition when queries are
  heavily time-filtered; the iterative-scan feature exists precisely because
  HNSW + post-filter otherwise returns too few rows [F].
- 4 000 cameras ≈ 1 G vectors/30 days; PQ-compressed ≈ 75 GB. Shard by site;
  cross-site search fans out.

The SurvSim angle: ReID mAP is **not** stable across appearance epochs
(clothing changes) — an [INF] this repo has **not yet measured**: H10 found 0
cross-epoch queries on batch_v7 (renders stop before the only outfit change)
[R: `32` §H10, `4a51207`]. (H4's 0.219 vs 0.148 is HSV vs OSNet cross-camera
mAP, not an epoch effect.) An index that stores one embedding per *tracklet*
silently becomes one embedding per *outfit*; a search product should say so
in the UI, and the evaluation should be split by epoch.

---

## 3. Clip extraction and evidence chain of custody

### 3.1 What the regulators ask for

- ICO: you must be able to "obtain copies of footage from our system in a
  timely manner, in a suitable format without losing image quality or time
  and date information", and "may also wish to keep a record or audit trail
  showing how you handle information, if it is likely to be used as evidence
  for law enforcement purposes" [F: ICO video surveillance guidance].
- **BS 10008-1:2020**, *Evidential weight and legal admissibility of
  electronically stored information (ESI) — Specification*: covers "the
  management of the availability of ESI over time", "the electronic transfer
  or communication of ESI", and linking electronic identity to ESI through
  signatures and verification [F: BSI Knowledge]. It is the standard a UK
  buyer will cite for "can this export stand up in court".

### 3.2 A defensible export pipeline [INF built on the above]

1. **Export native + a transcoded viewing copy.** Native (the recorded
   H.264/H.265 elementary stream in its container) is the evidence; the
   transcode is a convenience. Re-encoding changes pixels, so never hash only
   the transcode.
2. **Hash at the moment of extraction** — SHA-256 [T: FIPS 180-4] over each
   file, and over a manifest listing camera id, start/end in UTC and local,
   clock-sync status (NTP offset at export — see `43` §5), operator id, case
   reference, VMS version, export software version.
3. **Sign the manifest** (organisation key; BS 10008's identity linkage).
4. **Write to WORM**: S3 Object Lock or equivalent [F]. *Compliance mode* —
   nobody, including the root account, can delete or shorten retention
   before expiry; *governance mode* — privileged users can bypass. **Legal
   hold** — no expiry, until explicitly removed; independent of the
   retention period. Variable retention (event hold) suits "keep for N years
   after the case closes". AWS notes Object Lock was assessed by Cohasset
   for SEC 17a-4/CFTC/FINRA [F] — financial regulations, not UK evidence law,
   but the same WORM property.
5. **Audit log** of every view, export and hold change, itself append-only.
6. **Verify on disclosure**: recompute hashes, compare to the signed
   manifest.

Two gotchas [INF]:
- **Overlays**: burnt-in analytics boxes are *derived* data. Export them as a
  separate sidecar (e.g. JSON tracks), never baked into the evidential copy.
- **Clock truth**: a clip whose camera clock was 40 s off NTP is still
  evidence, but the manifest must say so. SurvSim's "GT follows the live
  camera" principle is the same idea applied to pose: record the state that
  was, not the configuration that was intended.

### 3.3 Sizes

A 5-minute, 3-camera incident clip at 1080p H.265 2.4 Mbit/s = 3 × 90 MB =
270 MB. At 20 exported incidents/day across 400 cameras: 5.4 GB/day, ~2 TB/year
under Object Lock — negligible next to the rolling store, but it is kept for
years, so it is the tier where Glacier-class pricing actually fits [INF].

---

## 4. Search-by-attribute products

The market term is "forensic search": filter the tracklet store by
attributes (person/vehicle, upper/lower clothing colour, carried bag, vehicle
type and colour, direction, dwell) and by similarity to an example ("more
like this person"). BriefCam (Canon since 2018) is the archetype, alongside
VMS-native search in Milestone/Genetec and vendors such as IronYun Vaidio
[R: `34` rows; `FACTS_VERIFIED` l.323 for the Canon–BriefCam dates]. (Vendor
product pages I tried returned 404 this session; I am not quoting feature
lists I did not fetch.)

What makes these products work is data engineering, not model novelty [INF]:
- **Attributes are computed once, at ingest**, on best-shot crops per
  tracklet — not per frame, not at query time.
- **Colour is a lie at night.** IR footage is monochrome; a "red jacket"
  query over 24 h must either exclude IR periods or say it did. SurvSim H3/
  H11 numbers (degraded day recall 0.209 vs raw 0.83; IR degrade blinding the
  detector) are the quantitative version of this [R: `32` §H3, `4a51207`].
- **Recall, not precision, is the metric.** A forensic search that misses the
  person is useless; ten extra results cost an investigator seconds. Evaluate
  with recall@k per query and time-to-find, stratified by pixel height and
  lighting.
- **Queries are time-bounded** — the index design in §2.2 follows from it.

---

## 5. Dataset curation pipelines

Production footage turned into training data is a different product with a
different legal basis (§7). The pipeline:

```
 source clips (lawful basis, DPIA ref)
   -> sampling (per camera/scene/hour/lighting strata)
   -> dedup (exact hash, near-dup perceptual, semantic)
   -> pre-label (current model) -> active-learning queue
   -> human labelling -> label QA (consensus, gold, noise detection)
   -> versioned dataset + manifest (content hashes, licences, splits)
```

### 5.1 Deduplication

CCTV is pathologically redundant: a static camera produces near-identical
frames for hours. Three levels [INF except where marked]:
1. **Exact** — content hash per frame file (SHA-256).
2. **Near-duplicate** — perceptual hashes (pHash/dHash) or frame-difference
   thresholds; cheap, catches static scenes.
3. **Semantic** — cluster embeddings and keep representatives. SemDeDup
   (Abbas et al. 2023) removed **50 % of a LAION subset with minimal
   performance loss, effectively halving training time**, and improved
   out-of-distribution performance [F: arXiv 2303.09540].

Split *before* dedup by **camera and by day**, never by frame — adjacent
frames in train and test leak identity and background, and inflate every
number (`21` §1.1 makes the same point for SurvSim splits) [R].

### 5.2 Active-learning queues

Label budget goes where the model is uncertain *and* the data is
operationally important. Practical queue sources [INF, `21` §3]:
- **Operator dispositions** — false-alarm dismissals are free hard negatives;
  missed-event reports are the rarest, most valuable positives.
- **Disagreement** — detector vs tracker (a track with gaps where the
  detector dropped out), or between model versions.
- **Stratification gaps** — cells of the operating envelope (pixel height ×
  lighting × camera height) with few labels. This is exactly what SurvSim's
  ODD report (M10) is designed to expose.
Correct for selection bias: operator feedback over-represents alarms, so
weight or reserve a random slice for unbiased evaluation.

### 5.3 Labelling QA and label-noise detection

Label noise is normal, not exceptional. Northcutt, Athalye & Mueller found
**an average of at least 3.3 % errors across 10 benchmark test sets, and at
least 6 % in the ImageNet validation set**; about half of algorithmically
flagged candidates were confirmed by crowdsourcing, and with enough noise a
smaller model can beat a larger one [F: arXiv 2103.14749]. Confident
learning (Northcutt, Jiang & Chuang, JAIR 2021; the `cleanlab` library) is the
standard method: estimate the joint of noisy and true labels from
out-of-sample predicted probabilities, then rank and prune likely errors [F:
arXiv 1911.00068].

For **boxes**, class-flip detection is not enough. The noise that hurt us
was *geometric*.

### 5.4 The SurvSim loose-box finding, as a label-QA lesson

- H6 found the synthetic GT box tops were loose by **+7 % of person height**,
  and that this, not pixel statistics alone, explained much of why
  fine-tuning on renders cut real AP 0.276 → 0.152 [R: `32` §H6, `4eac637`;
  §H1, `5e5f53d`].
- The fix in progress derives boxes from rendered instance masks and gates
  them against a detector: median IoU vs detector **0.781 → 0.884**, top
  offset +0.048 → −0.006 of height, top-offset check FAIL → PASS [R:
  `out/batch_v7/smoke_mock_day_tightgt/box_tightness*.json`, **uncommitted,
  in progress**; retraining not yet re-run].

Generalised into a QA check any labelling pipeline can run [INF]:
1. Run a strong detector over labelled frames.
2. Match labels to detections (IoU ≥ 0.5).
3. Track the **distribution of signed edge offsets** (top, bottom, left,
   right, as fractions of box height/width), not just mean IoU. A systematic
   offset (all tops high) is a *labelling-policy* bug — a vendor drawing to
   the hair vs the forehead, or a projection bug like ours — and mean IoU
   hides it (0.78 "looks fine").
4. Gate dataset versions on the offset medians (we use |offset| ≤ 0.03).
5. Per-annotator breakdown turns the same statistic into annotator QA.

This is cheaper than consensus labelling and catches the one error class
consensus labelling cannot: everyone following the same wrong guideline.

### 5.5 Manifests

Every dataset version: list of content hashes, source camera/site, capture
time range, lawful basis and DPIA reference, licence (`commercial_ml_ok`, as
SurvSim writes per set [R: `9c87424`]), split assignment, label schema
version, QA statistics. Training runs cite the manifest hash, not a path.

---

## 6. Data governance

### 6.1 Retention

- UK Surveillance Camera Code of Practice, **Principle 6**: "No more images
  and information should be stored than that which is strictly required for
  the stated purpose of a surveillance camera system, and such images and
  information should be deleted once their purposes have been discharged."
  The Code sets no fixed maximum; operators review and reset periods by
  purpose and experience [F: gov.uk amended Code].
- ICO: "it is the purpose of your processing that should determine your
  retention period"; footage "shouldn't be kept for six months merely because
  the manufacturer's settings allow retention for this length of time" [F].
- **Principle 12** (reference databases for matching, e.g. face watchlists):
  data must be accurate and up to date, and biometric data from unsuccessful
  matches deleted "instantaneously or near-instantaneously" [F].

Engineering consequences [INF]:
- Retention is a **per-purpose, per-tier, per-stream** setting. Rolling video
  30 days; evidence clips until case closure + statutory period (legal hold);
  **ReID embeddings no longer than the video they came from**, and arguably
  shorter — an embedding is a biometric-adjacent search key that outlives the
  pixels if you forget it.
- Implement retention as partition drops (§2.1) and lifecycle rules, with a
  daily job that *proves* deletion (row counts older than the limit = 0) and
  writes the proof to the audit log.
- Training datasets drawn from footage need their own lawful basis and
  retention; "we kept it to train the model" is a new purpose.

### 6.2 DPIA

Article 35(3) requires a DPIA for "a systematic monitoring of a publicly
accessible area on a large scale"; the ICO's high-risk list adds biometrics
and "tracking an individual's geolocation or behaviour" when combined with
other criteria [F: ICO DPIA guidance]. Code Principle 2 requires considering
the effect on privacy with regular reviews, and expects DPIAs [F]. Cross-
camera ReID search over a 400-camera estate hits the tracking criterion
directly. `44` covers the legal detail [R].

What the DPIA should contain that engineers own [INF]: data-flow diagram
(every tier in §1.4 and every metadata store in §2), retention per store,
who can run a similarity search and how it is logged, embedding retention,
accuracy evidence per operating condition (this is where synthetic
evaluation with ground truth earns its place), and the export/chain-of-custody
controls.

---

## 7. Worked design: a 400-camera estate

Assumptions [INF]: mixed campus (transport interchange + car parks +
buildings), 400 cameras 1080p H.265 at 15 fps, VBR average 2.4 Mbit/s, 30-day
retention decided in the DPIA; analytics on a 720p/10 fps sub-stream; 3
people per camera on average; 20 exported incidents/day.

| Layer | Design | Number |
|---|---|---|
| Ingest | cameras → site aggregation → recorders | 960 Mbit/s main + 400 Mbit/s sub |
| Hot tier | recorders, 7 days, RAID-6 | 7 × 400 × 25.9 GB = **72.6 TB usable**, ~100 TB raw |
| Warm tier | on-prem S3-compatible object store (or cloud IA), days 8–30 | 23 × 10.4 TB/day = **238 TB usable**, ~330 TB raw at 8+2 EC + headroom |
| Warm, if cloud | Standard-IA / B2 / Wasabi | ≈ $2 980 / $1 650 / $1 900 per month [from §1.4 prices] + upstream bandwidth |
| Evidence | Object Lock compliance mode + legal hold | ~2 TB/yr |
| Metadata | Postgres, day partitions: tracklets, events, audit | tracklets 3.5 M/day; ~30 GB/month excluding vectors |
| Vectors | 512-d per tracklet; IVFPQ (M=64) per day + halfvec for rerank | 104 M vectors; 7.5 GB PQ in RAM, 107 GB halfvec on NVMe |
| Compute | decode + detect + track + embed on sub-streams | per `22` §1 and `43` §8 sizing |
| Retention | lifecycle rules + partition drops + daily deletion proof | video 30 d, embeddings ≤ 30 d, per-frame boxes 7 d |

Totals: roughly **430 TB raw disk on-prem** for video, about **$2–3 k/month**
if the warm tier goes to a flat-rate cloud provider instead. At this scale
the dominant question is not $/TB but upstream bandwidth and who can search
what; the vector store is small once compressed.

How SurvSim would test this design [INF]: render a scenario whose GT
identities cross cameras over hours; replay it into the pipeline (M3
hardware-in-the-loop); measure forensic-search recall@k and time-to-find by
pixel height and lighting; verify that after the retention window no
tracklet, embedding or clip for a synthetic identity remains — a deletion
test you cannot run on real people without a DPIA of its own.

---


**1. "Size storage for 400 cameras, 30 days."**
Mbit/s × 10.8 GB/day per Mbit/s. At 2.4 Mbit/s H.265 that's 26 GB/camera/day,
311 TB for 30 days, ~430 TB raw with erasure coding and headroom. Then name
the levers: retention days (linear), codec (−25 to −50 %), dual-rate
recording, and say the bitrate is an assumption to measure per scene —
night IR noise can double it.

**2. "Why not put it all in S3?"**
The storage is affordable — $3.9 k/month in Standard-IA, ~$2.2 k in B2 — but
960 Mbit/s of sustained upstream and retrieval latency for operators are not.
Hot tier stays on-prem; warm and evidence can go to object storage; beware
archive-class minimum durations longer than the retention policy.

**3. "Design person search across cameras."**
Tracklet-level embeddings (not per frame), attributes computed at ingest,
day-partitioned IVFPQ for candidates plus exact rerank, time/camera filters
first. 104 M vectors at 512-d is 213 GB flat but 7.5 GB with PQ. Evaluate
recall@k, split by clothing epoch and lighting.

**4. "How do you make an export admissible?"**
Native stream plus viewing copy; SHA-256 at extraction over files and a
manifest with UTC times and clock-sync status; sign the manifest; store in
WORM (Object Lock compliance mode, legal hold for cases); append-only audit
of every access; re-verify at disclosure. BS 10008-1:2020 is the UK standard
the buyer will name.

**5. "How long should you keep footage?"**
As long as the purpose requires and no longer — Code Principle 6 and the ICO
both refuse a fixed number and specifically reject "because the NVR
defaults to six months". Engineering answer: retention per purpose and per
store, including embeddings and per-frame metadata, enforced by partition
drops and proven daily.

**6. "Your labels are noisy. How would you know?"**
Benchmarks average ≥ 3.3 % test-label errors (ImageNet val ≥ 6 %). For
classes, confident learning. For boxes, run a strong detector and look at
signed edge offsets, not mean IoU: our synthetic boxes had tops 7 % of height
too high while mean IoU looked acceptable at 0.78; mask-derived boxes moved it
to 0.88 and the offset to ~0 (in progress, retraining not yet re-run).

**7. "How do you pick what to label next?"**
Operator dispositions (free hard negatives), missed-event reports,
detector–tracker disagreement, and under-covered operating cells — with a
random reserve for unbiased evaluation. Dedup first: CCTV is near-duplicate
by nature; semantic dedup halved a web dataset with minimal loss.

**8. "Where does a simulator fit in a data platform?"**
Not as bulk training data — ours hurt a real detector (0.276 → 0.152) — but as
the only source of ground truth for the things you can't label on real
footage: identity across outfits, exact visibility windows, tamper state, and
end-to-end tests of search recall and deletion guarantees.

---

## 9. Numbers to replace with measurements

Per-scene bitrates (day/night, per camera model); real duty cycle for
event-triggered recording; tracklets per camera per hour; embedding
dimension and search recall of the chosen ReID model; incident export rate;
object-store prices at contract time (fetched list prices change).

---

## 10. Citations

Fetched 2026-09-26:
- AWS S3 pricing — https://aws.amazon.com/s3/pricing/
- AWS S3 Object Lock — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- Backblaze B2 pricing — https://www.backblaze.com/cloud-storage/pricing
- Wasabi pricing — https://www.wasabi.com/pricing
- FAISS index memory — https://github.com/facebookresearch/faiss/wiki/Faiss-indexes
- pgvector README — https://github.com/pgvector/pgvector
- HEVC vs AVC efficiency (BBC/UWS subjective study, PSNR study) — https://en.wikipedia.org/wiki/High_Efficiency_Video_Coding
- Amended Surveillance Camera Code of Practice (Principles 2, 6, 12) — https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version
- ICO, when do we need a DPIA — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/when-do-we-need-to-do-a-dpia/
- ICO, complying with the principles when using surveillance systems — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/how-can-we-comply-with-the-data-protection-principles-when-using-surveillance-systems/
- BS 10008-1:2020 — https://knowledge.bsigroup.com/products/evidential-weight-and-legal-admissibility-of-electronically-stored-information-esi-specification
- Northcutt, Athalye, Mueller, *Pervasive Label Errors in Test Sets…* — https://arxiv.org/abs/2103.14749
- Northcutt, Jiang, Chuang, *Confident Learning*, JAIR 2021 — https://arxiv.org/abs/1911.00068
- Abbas et al., *SemDeDup* — https://arxiv.org/abs/2303.09540
- Zhou et al., *Omni-Scale Feature Learning for Person ReID* (OSNet) — https://arxiv.org/abs/1905.00953 (feature dimension not stated in the abstract; 512-d is [T])

Tried and failed (404): gov.uk CCTV evidence-retrieval guidance, Axis H.265
article, BriefCam, Avigilon and Milestone product pages — no claims taken
from them.

Repo: `43` §5, §8; `22` §1; `21` §1, §3; `34`; `44`; `32` §H1, H3, H4, H6, H10,
H11; `FACTS_VERIFIED.md` l.323; commits `5e5f53d`, `4eac637`, `9c87424`,
`4a51207`.
