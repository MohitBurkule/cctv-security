# 21 · Data, MLOps and Governance — datasets, feedback loops, evaluation, drift, and the law

*Series 17–23. How the company builds, validates, ships and legally operates
models for the pipeline in report 17, with SurvSim as the evaluation engine.
R03 §9 and R02 §5 cover UK/EU law for behaviour and face; this report covers
the data lifecycle end to end.*

**Sourcing conditions.** 2026-09-26; no GPU/engine. Legal texts cited by URL;
this is engineering analysis, not legal advice. Every external claim was re-checked
by web fetch/search on 2026-09-26 and is cited as [n] to the References
section; claims that could not be confirmed were removed; **[INF]** inference; **[BOE]**
arithmetic.

---

## 0. Summary

1. **Split by site, then camera, then time — never by frame.** Neighbouring
   frames are near-duplicates; SurvSim already splits by seed for this reason
   (docs/13). In the product, generalisation to *unseen sites* is the claim
   customers buy, so the test split is unseen sites.
2. **Synthetic is a training accelerant and a test oracle, not a substitute.**
   Pre-train on synthetic, fine-tune on real, validate on real, stress-test on
   synthetic. Report every synthetic number next to a real one (docs/13 gap
   protocol).
3. **Operator dispositions are the flywheel.** True/false/nuisance clicks on
   alarms are cheap, abundant, on-distribution labels — biased toward what the
   system already alarms on. Active learning must correct that bias.
4. **The evaluation harness is the product's conscience.** Every model, rule,
   threshold or config change runs through the same harness (SurvSim eval +
   real regression sets) and produces operational metrics (Pd at i-LIDS timing,
   FA/camera-hour, operator load). No green, no ship.
5. **Registry + lineage are regulatory requirements.** The EU AI Act (for
   high-risk uses) and UK Surveillance Camera Code expect traceability; build
   it in from day one.
6. **Privacy by design is also an engineering simplifier.** Metadata-first
   pipelines, on-prem processing, short retention and anonymised training data
   reduce both legal risk and infrastructure cost.

---

## 1. Dataset design

### 1.1 Units and splits

| Level | Why it matters | Rule |
|---|---|---|
| Site | backgrounds, camera models, behaviours differ | test on held-out sites |
| Camera | viewpoint, lens, mounting height | within a training site, hold out cameras for val |
| Time | day/night, season, weather | stratify; hold out whole days, not hours |
| Identity | ReID must generalise to new people | identities disjoint across splits (Market-1501/MSMT convention) |
| Event | behaviour models | events disjoint; adjacent windows from the same event stay together |
| Scenario/seed (synthetic) | seeds are near-independent worlds | last seed test, second-last val (docs/13) |

Leakage traps [INF/lore]: the same person appearing in train and test via a
different camera (ReID leakage); the same event sliced into overlapping clips
across splits (behaviour leakage); pretraining on a public dataset that shares
footage with the test benchmark (MOT17/MOT20 train/test overlap with derived
sets); synthetic assets shared between train and test worlds (the same three
baked MetaHuman bodies, docs/11 — a ReID model can learn body shape; hold out
bodies when possible).

### 1.2 Stratification targets

Report and balance by: pixel height bucket (20–40, 40–80, 80–160, > 160 px),
imaging profile/condition (day, dusk, night colour, IR, thermal, rain, fog),
density band (docs/11 crowd bands), camera height/pitch bands, behaviour class
with hard negatives, and demographic/appearance attributes for fairness audits
(clothing, mobility aids — `disabled_mobility` in docs/03).

### 1.3 Label taxonomy and schema

A single versioned ontology for classes, attributes, behaviours (docs/03 path
labels like `plaza.intruder.loiter.pace`) and hard-negative relations, shared by
SurvSim writers, annotation tooling and the product. Formats: MOTChallenge for
tracks, COCO (+keypoints) for detection, parquet for world state, JSONL for
events (all emitted by `survsim/gt/writers.py`). Real-data annotation tools:
CVAT [14] supports tracks and attributes; Label
Studio for events.

### 1.4 How much real data [BOE/INF]

Typical fine-tuning scale that moves a COCO-pretrained detector on a new
domain: 2k–20k labelled frames (sparse sampling, e.g. 1 frame per 2 s per
camera, to avoid duplicates). At ~30 persons/frame and ~5 s per box with
tracking-assisted annotation, 10k frames ≈ 300k boxes ≈ 400 annotator-hours —
~£8–12k at UK/EU outsourced rates [BOE; rates vary widely]. Behaviour events
are the expensive part: each true event requires review of long footage.
Synthetic data's economic value concentrates exactly there.

---

## 2. Synthetic + real mixing

### 2.1 Evidence

(Details in report 18 §6 and report 24.) PeopleSansPeople (Ebadi et al.,
2021 [17]): with Detectron2 Keypoint R-CNN, synthetic pre-training gave +38.03
keypoint AP over training on the few-shot real subset alone and +1.47 with the
full real set; against ImageNet pre-training, +22.53 (few-shot) and +1.07
(full). MOTSynth (Fabbri et al., ICCV 2021 [18]): the authors conclude that
their GTA-V dataset "can be used as a replacement for real data" for
pedestrian detection, ReID, segmentation and tracking. BEDLAM (Black et al.,
CVPR 2023 [19]): networks trained only on synthetic data reached
state-of-the-art 3D human pose/shape accuracy on real images. The
common finding: **diversity and realism of people matter more than volume;
fine-tuning on real closes most of the remaining gap.**

### 2.2 Operating recipe

1. Pre-train on a large synthetic pool (all conditions, strong hard negatives).
2. Fine-tune on real with a synthetic fraction of 10–50 % per batch, weighted
   toward rare conditions (night, rain, adversarial modifiers) [INF].
3. Ablate: real-only vs mixed at fixed real volume, reported per stratum.
   The mixing ratio is a hyperparameter selected on *real* val.
4. Keep synthetic-only evaluation sets as **stress suites**; never select
   models on them.

### 2.3 Domain-gap monitoring for synthetic data

Track per SurvSim release: docs/15 realism stats (e.g. `cctv_day_720p` 6/14
in band, `cctv_legacy_sd` 9/14), FID/KID on person crops, detector-as-judge
recall (batch_v4: yolov8n recall 0.758 on MetaHuman renders vs 0.577 on
CesiumMan), and TSTR (train synthetic, test real). A SurvSim release that
improves image stats but lowers TSTR is a regression.

---

## 3. Active learning from operator feedback

### 3.1 What operators give you

Each alarm disposition (true / false / nuisance + optional reason code:
"animal", "staff", "weather", "reflection") is a label on an event *the model
already scored above threshold*. It is plentiful — at 0.1 alarms/camera-hour
across 1,000 cameras, ~2,400 labels/day [BOE] — and biased: it never labels
misses.

### 3.2 Correcting the bias

* **Sample below threshold**: route a small, randomised fraction of near-
  threshold candidates (e.g. 1 %) to a *separate* review queue — not the live
  operator queue — for labelling (uncertainty sampling; Settles' survey [9]).
* **Scheduled audits for misses**: periodic review of randomly sampled time
  windows (or red-team exercises: staged walk-throughs at known times) gives
  unbiased recall estimates. SurvSim scenarios can script the red-team run.
* **Diversity sampling** over embedding space so labels do not concentrate on
  one nuisance type.
* **Reason codes feed hard-negative mining**: 500 "fox at night" nuisances
  become a training cluster and a new SurvSim wildlife scenario requirement.

### 3.3 Human factors

Operators are not annotators: disposition UI must be one click, and label
quality varies with fatigue (D06; Keval & Sasse). Use agreement checks
(sample 5 % for second review) and model operator reliability [INF].

### 3.4 Simulating the loop

SurvSim can simulate an operator (disposition accuracy, latency, fatigue) and
run closed-loop experiments: how quickly does per-site FA rate fall with
active learning, and does recall silently degrade? No real deployment can run
this experiment safely. **Not built** — an operator model is listed in
report 23.

---

## 4. The evaluation harness

### 4.1 Layers

| Layer | Content | Owner |
|---|---|---|
| Unit metrics | AP by bucket, HOTA/IDF1, ReID R1/mAP, MTMC IDF1, handoff gap | ML team |
| Event metrics | Pd at i-LIDS tolerance, FA/camera-hour, time-to-alarm | analytics team |
| Operational | alarms per operator-hour, funnel per stage (report 19 §10) | product |
| Robustness | the above per profile/condition, adversarial modifiers | ML + red team |
| Fairness | recall/FA by appearance attributes and mobility | governance |
| Real regression | frozen real clips per site class with known events | QA |

SurvSim already provides most synthetic layers (docs/11: detection with
alarms/camera-hour, MOTA/IDF1/HOTA with DetA/AssA, MTMC with `handoff_gap`,
`reid_by_epoch`, behaviour P/R, fusion, retrieval, alarm pipeline, i-LIDS
timing via `survsim eval --threshold-s`). docs/13 provides the dataset/baseline
harness and the real reference row (MOT20 subset: AP 0.348, HOTA 0.443 (TrackEval parity; 0.434 pre-parity, 0.545 pre-fix), ReID
R1 0.186 with ImageNet OSNet).

### 4.2 Harness requirements [INF]

* **Deterministic** (seeded; principle 6) — a metric change must be
  attributable to the model, not to the data draw.
* **Versioned datasets** (content hash + generator version + SurvSim commit).
* **Confidence intervals** on every event metric (events are few).
* **Degenerate-case detection**: docs/11 bug 9 — a test split with no
  positives returned AUC 0.5; the harness must refuse to report it.
* **Performance**: `survsim baseline --task all` on full MOT20 was killed at
  2.5 h, but docs/13 retracts the "O(n²) association" diagnosis: tracker +
  `evaluate_mot` take ~62 s on all 8,931 frames; the unprofiled ReID/`eval_det`
  stages are the suspects. Profile before blaming, and keep harness code fast.
* **CI integration**: fast subset on every PR (the repo's pre-commit runs
  checks in < 30 s), full suite nightly, release suite before promotion.

### 4.3 Promotion gates (example) [INF]

A new detector version is promoted to a site class when, versus the current
production model, on the real regression set: Pd at tolerance not lower by
more than 1 point per behaviour; FA/camera-hour not higher by more than 5 %;
no pixel-height bucket recall drop > 3 points; synthetic stress suites no
regression on adversarial modifiers; and quantised export parity within
tolerance (report 18 §8).

---

## 5. Deployment-time monitoring and drift

### 5.1 What drifts

Scenes (construction, seasons, foliage), cameras (re-aimed, dirty, replaced),
populations (events, holidays), and the adversary (people learn the system).

### 5.2 Signals

* **Input drift**: IQA stats per camera vs baseline (docs/15 stats), detection
  count rates, pixel-height distributions, day/night proportion.
* **Output drift**: alarm rates per camera and type, score distributions
  (population stability index), track length and fragmentation rates.
* **Feedback drift**: disposition ratios (rising "false" share on a camera).
* **Calibration drift**: reprojection residuals of static keypoints (report 18).

Alerts go to the *engineering* on-call, not the security operator. Most
"model drift" in CCTV is actually a camera problem [lore; D06].

### 5.3 Response

Per-camera threshold adjustments (bounded, logged), camera maintenance
tickets, targeted data collection, and — if a site class drifts — a retraining
cycle through the full gate.

---

## 6. Model registry and lineage

Minimum record per model artefact: training data manifests (hashes, SurvSim
generator versions, real-data sources and legal basis), code commit,
hyperparameters, evaluation reports (all harness layers), export artefacts
(ONNX/TensorRT engines with target hardware), approval sign-off, and deployed
sites. Tools: MLflow Model Registry [10]
or equivalent; DVC/lakeFS for dataset versioning. Deployed configs (rules,
thresholds, zones) are versioned alongside models — an alarm must be
reproducible from `(model_version, config_version, input clip)`.

---

## 7. Privacy, law and governance

### 7.1 UK

* **UK GDPR + Data Protection Act 2018**: CCTV images of identifiable people
  are personal data. Lawful basis (usually legitimate interests or public
  task), DPIA mandatory for systematic monitoring of a publicly accessible area on a large scale (UK
  GDPR Art. 35(3)(c)) — ICO guidance:
  [4].
* **Surveillance Camera Code of Practice** (Protection of Freedoms Act 2012
  s.30; 12 guiding principles; binding on "relevant authorities", voluntary
  for others). The amended code was laid before Parliament on 16 November 2021
  and came into effect on 12 January 2022 [5]. Principles cover purpose,
  privacy impact, transparency, accountability, clear rules, retention
  minimum necessary, access, standards, security, review/audit, evidential
  effectiveness, and accuracy of reference databases. The Data (Use and
  Access) Act 2025 (Royal Assent 19 June 2025) amends UK GDPR/DPA 2018 but did
  **not** abolish the Code or the Commissioner [6]; Professor William Webster
  (University of Stirling) took office as Biometrics and Surveillance Camera
  Commissioner on 1 November 2025 for a two-year term, after the post had been
  vacant since August 2024 (an interim commissioner served from 1 July 2025) [7].
* **Biometrics**: live facial recognition use by police is shaped by
  R (Bridges) v Chief Constable of South Wales Police [2020] EWCA Civ 1058,
  judgment 11 August 2020 [8] — equality duty
  and clear policy requirements. Special-category data (biometric for unique
  identification) requires an Art. 9 condition.
* **Employment**: monitoring staff requires transparency and proportionality
  (ICO employment practices guidance).

### 7.2 EU AI Act (Regulation (EU) 2024/1689)

Regulation (EU) 2024/1689, adopted 13 June 2024, published in the Official
Journal 12 July 2024 [1].
* **Prohibited (Art. 5)**: real-time remote biometric identification in
  publicly accessible spaces for law enforcement (narrow exceptions);
  untargeted scraping of facial images to build databases; emotion recognition
  in workplace and education; biometric categorisation inferring sensitive
  attributes; individual risk assessment of offending based solely on
  profiling/personality traits. Applied from 2 Feb 2025.
* **High-risk (Annex III)**: remote biometric identification (non-prohibited),
  biometric categorisation, emotion recognition; critical infrastructure safety
  components; some law-enforcement uses. High-risk obligations (risk
  management, data governance Art. 10, technical documentation, logging Art.
  12, transparency, human oversight Art. 14, accuracy/robustness/cybersecurity
  Art. 15, conformity assessment) were due from 2 Aug 2026 for Annex III
  systems. **Changed by the Digital Omnibus on AI**: provisional political
  agreement 6 May 2026, confirmed by Member States 13 May 2026, adopted as
  Regulation (EU) 2026/1744 (OJ 24 July 2026, in force 27 July 2026) [2][26], postpones
  Annex III high-risk obligations to **2 December 2027** and Annex I
  (product-embedded) to **2 August 2028**; Art. 50 transparency obligations
  keep the 2 August 2026 date; a new Art. 5 prohibition on non-consensual
  intimate imagery/CSAM generation was added (applies 2 Dec 2026). No biometric-provision changes
  were reported [2][3]. Planning date for a surveillance product sold into
  the EU: December 2027.
* **Implication**: person detection/tracking/behaviour analytics without
  identification are generally not high-risk per se, but **cross-camera ReID
  that re-identifies individuals may be argued to be remote biometric
  identification** if it uses biometric data (face, gait) [INF — contested;
  appearance-based ReID on clothing is arguably not biometric, gait is].
  Design the product so biometric modules are separable, switchable, and
  documented to high-risk standard.
* Art. 10 data governance (relevance, representativeness, bias examination)
  maps directly to §1 stratification and fairness audits; SurvSim's controlled
  demographics are a way to *demonstrate* bias examination.

### 7.3 Synthetic data and privacy

Synthetic people are not personal data, *but*: MetaHuman or scanned assets
derived from real people carry licence and likeness terms (D08 licences);
models trained on real CCTV remain derived from personal data; and synthetic
data does not exempt the deployed system from any obligation. A strong,
honest claim: "training on synthetic reduces the volume of real personal data
processed for development" — a data-minimisation argument under UK GDPR Art.
5(1)(c) [INF].

### 7.4 Retention and anonymisation

* Retention: UK practice commonly 30 days for general CCTV unless an incident
  requires longer [lore; ICO says no longer than necessary]. Metadata can be
  retained longer if de-identified; embeddings are personal data if linkable.
* Training data derived from customer footage: contractual permission, DPIA,
  and anonymisation (face/body blurring degrades training value; alternatives
  are secure enclaves and on-site training) [INF].
* **Anonymisation techniques**: face blurring (DeepPrivacy2, Hukkelås &
  Lindseth, WACV 2023 [13], for realistic full-body/face replacement), full-body replacement with
  synthetic humans (SurvSim assets could serve), feature-only retention.
  Blurred data is often still personal data (re-identifiable by context).
* **Embeddings**: ReID vectors are identifiers; store with the same
  controls as images, rotate/expire.

### 7.5 Governance artefacts to maintain

DPIA template per deployment; model cards (Mitchell et al., FAT* 2019 [11])
and datasheets (Gebru et al. [12]) per model/dataset; an
algorithmic impact assessment for behaviour analytics; an audit log (report
17 §3.9); a fairness report per release; incident process for wrongful alarms.

---

## 8. Team and process

A realistic small-company allocation [INF]: 2 ML engineers (perception,
behaviour), 1 MLOps/data engineer (harness, registry, pipelines), 1 SurvSim
engineer (scenarios, rendering, sensor models), 0.5 annotation lead, 0.5
governance/DPO support, plus field engineers who own commissioning data.
Weekly "failure review" of operator-disposed false alarms feeding both
retraining and SurvSim scenario backlog closes the loop.

## 9. Data pipeline architecture

```
 sites (on-prem)                                  company (training enclave)
 ─────────────────                                ──────────────────────────
 VMS clips on alarm/disposition ──┐
 metadata (tracks, events, IQA) ──┼─► site data agent ──(consented, filtered,
 operator dispositions ───────────┘    encrypted, rate-limited)──► landing zone
                                                                       │
 SurvSim cluster ──► synthetic runs (scenario, seed, profile) ────────► │
                                                                       ▼
                         object store (raw) ─► curated datasets (versioned, DVC/lakeFS)
                                                   │
                         annotation (CVAT) ◄───────┤
                                                   ▼
                         training jobs ─► registry ─► eval harness ─► promotion
                                                                        │
                         signed artefacts ◄─────────────────────────────┘
                              │
                         fleet manager ─► staged rollout (shadow → canary → all)
```

Design points [INF]:

* **Pull only what you need.** Most learning value is in alarm clips (with
  dispositions), near-threshold clips (active-learning samples) and scheduled
  audit windows; continuous upload is neither affordable nor lawful by default.
* **Per-site legal basis travels with the data** as metadata; a dataset build
  refuses records whose basis does not cover model training.
* **Shadow mode**: a candidate model runs on live streams without alarming;
  its would-be alarms are compared with production and with dispositions.
  This is the only honest pre-release test of FA/camera-hour on a real site.
* **Canary**: roll to 5–10 % of cameras per site class, monitor §5 signals for
  a week, then widen.
* **Air-gapped customers**: the same flow runs with a physical transfer step
  (signed media) and on-site evaluation; the harness must run offline — which
  SurvSim already does (no network, CPU-capable, docs/11: tests offline-capable).

## 10. Coverage-driven verification with SurvSim

Corpus fact 8 (R04, D03, D07): the unbuilt product is a scenario DSL with
coverage-driven verification and a regulator-shaped test report. The data/MLOps
view of that idea:

1. **Define the operational design domain (ODD)** per site class as a set of
   axes with ranges: camera height 3–12 m, pitch 10–45°, pixel height 20–200
   px, lighting {day, dusk, night colour, IR, thermal}, weather {clear, rain,
   fog, snow}, density band, behaviour × hard-negative pairs, adversarial
   modifiers. This borrows the autonomous-driving ODD concept (e.g. SAE J3016
   terminology; BSI PAS 1883:2020 ODD taxonomy for automated driving [16]
   — note BSI lists it as withdrawn, so borrow the structure, not the
   standard).
2. **Generate scenarios to cover the ODD** — SurvSim's scene generator is
   already "stratified, validated, repairing" (docs/11). Coverage is measured
   as the fraction of ODD cells with ≥ N evaluated events.
3. **Score each cell**: Pd at tolerance, FA/camera-hour, with CIs.
4. **Find failure regions** automatically (cells below requirement) and
   generate more scenarios there (importance sampling / adversarial search),
   the way AV simulation does.
5. **Emit a test report** in the customer's language: DORI bands, i-LIDS-style
   scenario classes, detection probability and nuisance-alarm rate per cell,
   known limitations, and the real-data corroboration for each claim.

The value to a buyer is not "we trained on synthetic data" but "here is a
verified map of where the system works and where it does not" — which also
satisfies AI Act Art. 9/15 expectations for risk management and accuracy
declarations where they apply [INF].

## 11. A worked quarter [INF]

| Week | Data work | Output |
|---|---|---|
| 1–2 | Freeze real regression sets for 3 site classes (transport, CNI perimeter, campus); legal review | versioned sets, DPIAs |
| 3–4 | SurvSim ODD definition + scenario generation for the same classes | 3 synthetic suites with coverage reports |
| 5–6 | Train detector v2: synthetic pre-train + real fine-tune; ablate mixing ratio | registry entries with harness reports |
| 7 | Shadow-deploy v2 at 2 pilot sites | FA/camera-hour vs production |
| 8–9 | Active-learning sampling from shadow disagreements + dispositions; annotate 3k frames | dataset v2.1 |
| 10 | Retrain; promotion gate | v2.1 |
| 11–12 | Canary rollout; drift dashboards; quarterly fairness report | release notes, model card |

## 12. Metrics for the data/MLOps function itself

* Time from a new false-alarm pattern being reported to a model/policy fix in
  production (target: weeks, not quarters).
* Fraction of production alarms reproducible from registry + config + clip
  (target 100 %).
* Share of evaluation claims backed by a real-data number (target 100 % for
  external claims; docs/13 rule 4 — no number on `synthetic_topdown` data).
* Annotation cost per point of Pd gained, per behaviour.
* Harness wall-clock for the nightly suite (it only protects you if it runs).

## 13. Worked example — building a dataset from our own scenarios

This walks the pipeline that exists today (`survsim/datasets/build.py`,
`survsim/cli.py` commands `dataset` and `baseline`, `survsim/gt/writers.py`)
on the two scenarios that matter most for the product claim.

### 13.1 The scenarios

* `configs/scenarios/disguise_and_tamper.yaml` — 240 s at 10 fps on the
  `compound` environment: a gate zone, a public yard, a restricted substation
  (`allowed_roles: [worker, guard]`), a north perimeter fence with a cuttable
  panel (`fence_seg_12`), and `zone.blindspot_A`, which `survsim rig` verifies
  no camera observes. It combines an outfit change inside that blind spot
  (cross-epoch ReID), a patrolling PTZ, a camera tamper that blinds a camera
  mid-run, hostile reconnaissance, fence probing, an intrusion, and hard
  negatives generated to dwell *exactly* as long as the loiterer.
* `configs/scenarios/street_crowd.yaml` — 60 s at 10 fps, `street_plaza`, 18
  people around a hero pair (a loiterer and a `commute_wait` hard negative),
  three cameras at 3.5–5 m, 15–30° down, 70–95° HFOV, so people are 60–200 px
  tall. It is also the render demo used by `tools/render_batch.py`, and its
  `cam_02` renders are the docs/15 realism reference.

### 13.2 Commands

```bash
source .venv/bin/activate
# 1. plumbing check on the mock backend (synthetic_topdown: true)
survsim dataset configs/scenarios/disguise_and_tamper.yaml \
    configs/scenarios/street_crowd.yaml --seeds 5 --out out/ds_dt_sc_mock
# 2. with renders (layout <frames-dir>/<run>/<cam>/NNNN.png, run = <stem>_s<seed>)
survsim dataset configs/scenarios/disguise_and_tamper.yaml \
    configs/scenarios/street_crowd.yaml --seeds 5 \
    --frames-dir out/renders --profile cctv_day_720p --max-frames 0 \
    --out out/ds_dt_sc_day
# 3. real reference row, same code path
survsim dataset --mot ~/data/mot/extracted/MOT20 --max-frames 0 --out out/ds_mot20
# 4. zero-shot baselines, identical models/thresholds on both
survsim baseline out/ds_dt_sc_day --task all --model yolo11n.pt --imgsz 1280
survsim baseline out/ds_mot20     --task all --model yolo11n.pt --imgsz 1280
```

With `--seeds 5`, `split_for_seed` assigns seeds 0–2 to train, seed 3 to val
and seed 4 to test. Each scenario is split independently, so both scenarios
appear in every split — right for a first fine-tune and **wrong for a claim
of generalisation to new sites**. For that claim, hold out a whole scenario:
build `street_crowd` as the test set on its own and train on the other four
scenario files. The CLI supports this today by running `dataset` twice.

### 13.3 What lands on disk

Per run (`runs/<stem>_s<seed>/`, written by `Recorder.write`):

| File | Content | Used by |
|---|---|---|
| `gt/mot_<cam>.txt` | MOTChallenge rows `frame,id,x,y,w,h,1,1,visible_frac` | det/MOT/ReID baselines |
| `gt/events.jsonl` | behaviour events with labels, hard-negative tags | `survsim eval`, behaviour models |
| `gt/sensors.jsonl` | RF/audio/access-control log | fusion |
| `gt/camera_status.jsonl` | live camera state (PTZ pose, tamper) | health/tamper evaluation |
| world parquet, identities parquet | actual positions and identity/epoch table | MTMC, ReID-by-epoch |
| `calib/<cam>.json` | intrinsics, extrinsics, resolution, fps | ground-plane projection |
| `meta/scenario.resolved.json`, `meta/track_ids.json` | resolved config and uid→track id | reproducibility |

Per dataset: `frames/<run>/<cam>/NNNNNN.jpg`, `coco/<run>.json`, and
`manifest.json`:

```json
{ "kind": "survsim",
  "synthetic_topdown": false,
  "note": "rendered frames, degrade profile=cctv_day_720p",
  "degrade_profile": "cctv_day_720p",
  "runs": [ { "name": "street_crowd_s4", "scenario": "configs/scenarios/street_crowd.yaml",
              "seed": 4, "split": "test", "coco": "coco/street_crowd_s4.json",
              "cameras": { "cam_02": { "gt": "runs/street_crowd_s4/gt/mot_cam_02.txt",
                                       "fps": 10.0, "resolution": [1280, 720],
                                       "frames": { "1": "frames/street_crowd_s4/cam_02/000001.jpg" } } } } ] }
```

### 13.4 Volume arithmetic [BOE]

`street_crowd`: 60 s × 10 fps × 3 cameras = 1,800 frames per seed.
`disguise_and_tamper`: 240 s × 10 fps × *N* cameras (its rig has a gate
bullet camera, a PTZ and others) ≈ 2,400 frames per camera per seed. Five seeds
of both with four cameras in the compound gives ~57k frames. At the docs/11
editor rate (~11 frames/s at 720p) that is ~1.4 h of rendering, and at docs/15's
0.567 s/frame degradation ~9 h single-process. **Degradation, not rendering,
is the bottleneck**; run it in the background across processes (report 23,
M11).

### 13.5 Checks before any number is believed

1. `synthetic_topdown` must be false (docs/13 rule 4).
2. Plot five random frames per camera with GT boxes (geometry before models,
   report 18 §9).
3. In `disguise_and_tamper`, the tampered camera must have **no** GT rows
   after the tamper onset (principle 2). If rows exist, the dataset is wrong.
4. The outfit-change identity must have two appearance epochs in the
   identities table, and the change must fall inside `zone.blindspot_A`.
5. Pixel-height histogram per split, compared with the target site's
   histogram from `survsim rig`.

### 13.6 Manifest fields to add

The current manifest is enough for baselines but not for a model registry.
Proposed additions, all cheap to compute in `build_dataset`:

```json
{ "schema_version": 2,
  "survsim_commit": "fbca5c1",
  "created_utc": "2026-09-26T12:00:00Z",
  "generator": { "backend": "mock|unreal", "render_job_ids": ["..."],
                 "character_bodies": ["MHB01","MHB02","MHB03"] },
  "degrade": { "profile": "cctv_day_720p", "params_hash": "sha256:…",
               "codec": "h264_sequence", "gop": 8, "bf": 0, "crf": 29 },
  "split_policy": "by_seed|by_scenario|by_site",
  "content_hash": "sha256 over sorted (path, sha256) of frames+gt",
  "stats": { "frames": 57600, "boxes": 0, "identities": 0,
             "height_px_hist": {"20-40": 0, "40-80": 0, "80-160": 0, ">160": 0},
             "realism_in_band": {"cctv_day_720p": "6/14"} },
  "licence": "internal-synthetic", "personal_data": false }
```

`character_bodies` matters because only three baked MetaHuman bodies exist
(docs/11); a ReID test split that shares bodies with train leaks identity cues.

## 14. Concrete schemas

### 14.1 Model registry record

Stored as MLflow model-version tags [10], or as a JSON sidecar next to the
artefact:

```yaml
model: person-det
version: 7
aliases: [production-transport, canary-cni]      # mutable pointers, MLflow aliases
artefacts:
  pytorch: s3://models/person-det/7/best.pt
  onnx: s3://models/person-det/7/model.onnx
  tensorrt:
    - {target: "L4/TRT10/FP16", path: ".../l4_fp16.engine", sha256: "…"}
    - {target: "OrinNX/JP6/INT8", path: ".../orin_int8.engine", calib_set: "calib-cni-v3"}
training:
  code_commit: "abc1234"
  datasets:
    - {name: ds_dt_sc_day, content_hash: "sha256:…", role: pretrain}
    - {name: real-transport-v4, content_hash: "sha256:…", role: finetune, legal_basis: "contract-2026-014"}
  synthetic_fraction_finetune: 0.25
evaluation:
  harness_version: "survsim@fbca5c1"
  real:
    pd_at_tolerance: {loiter: 0.91, intrusion: 0.97}
    fa_per_cam_hour: {loiter: 0.011, intrusion: 0.004}
    recall_by_height: {"20-40": 0.62, "40-80": 0.88, "80-160": 0.95}
  synthetic_stress:
    adversarial_modifiers_pd: {role_disguise: 0.55, crowd_cover: 0.61}
  export_parity: {int8_max_bucket_drop: 0.021}
approval: {by: "ml-lead", at: "2026-10-01", gate: "promotion-v2"}
deployed_to: [site-017, site-023]
```
(The numbers are illustrative placeholders, not results.)

### 14.2 Operator disposition record

```json
{ "alarm_id": "a-2026-10-02-000123",
  "site": "site-017", "camera": "cam_gate", "rule": "loiter.gate_A", "rule_version": 12,
  "model_versions": {"person-det": 7, "reid": 3, "behaviour": 2},
  "t_event_utc": "…", "t_raised_utc": "…", "t_ack_utc": "…", "t_closed_utc": "…",
  "disposition": "true|false|nuisance",
  "reason_code": "animal|staff|weather|reflection|other|null",
  "operator_id_hash": "…", "second_review": null,
  "clip_ref": {"vms": "milestone", "camera_guid": "…", "start": "…", "end": "…"},
  "consent_for_training": true }
```
`consent_for_training` records whether the site contract covers training use.
If it does not, the record may feed metrics but must not enter a dataset.

### 14.3 Active-learning and drift configuration keys

```yaml
active_learning:
  below_threshold_sample_rate: 0.01      # of candidates in [thr-0.15, thr)
  max_review_items_per_site_day: 50
  diversity: {embedding: reid-v3, method: kcenter, k: 20}
  audit_windows: {per_camera_per_week: 2, duration_s: 600}
drift:
  iqa_psi_alert: 0.25                    # population stability index vs 28-day baseline
  detections_rate_z_alert: 4.0
  disposition_false_share_alert: 0.5
  calib_residual_px_alert: 6
promotion_gate:
  max_pd_drop_points: 1.0
  max_fa_increase_pct: 5
  max_height_bucket_recall_drop: 0.03
```

## 15. Tooling comparison (prices checked 2026-09-26)

| Need | Tool | Licence / hosting | Public price | Notes |
|---|---|---|---|---|
| Experiment tracking + registry | MLflow [10] | Apache-2.0, self-host | free | versions, aliases, tags; fits air-gapped sites |
| | Weights & Biases [20] | SaaS or self-host | Free; Pro from $60/month; Enterprise custom; self-hosted Personal is free but "corporate use is not allowed" | best UX; the SaaS model may conflict with customer data rules |
| Data versioning | DVC [21] | Apache-2.0 | free (open source) | git-native; stores pointers to object storage |
| | lakeFS [22] | open-source core; lakeFS Cloud | Cloud pricing not public (sales contact) | branch/commit semantics over S3; suits large frame stores |
| Annotation | CVAT [14][15] | MIT, self-host; CVAT Cloud | Solo $33/month ($23 billed annually); Team $33/user/month (min 2 seats); Enterprise self-hosted from $12,000/year | strong video/track interpolation, suits MOT |
| | Label Studio [23] | Apache-2.0 community; HumanSignal Starter Cloud / Enterprise | Starter Cloud $99/month + $49 per additional user (pricing page, 2026-09-26); Enterprise via sales | flexible for event/timeline labels |
| | Labelbox, Encord, Scale AI | SaaS + managed workforce | not published; secondary sources give Labelbox from ~$1,500/month [24] and bounding boxes around $0.02–$1.00 per object across vendors [25] | treat as indicative only; per-task enterprise contracts |

Recommendation: a self-hosted stack of MLflow, DVC or lakeFS and CVAT covers
air-gapped defence/CNI customers with no per-seat SaaS dependency. Use a
managed workforce only for bulk box annotation on data the contract allows to
leave the site.

## 16. What SurvSim must emit — data/MLOps checklist

| # | Item | Module | State |
|---|---|---|---|
| 1 | Seed-level splits, never frame-level | `survsim/datasets/build.py::split_for_seed` | done |
| 2 | Scenario-/site-level split policy option | `survsim/datasets/build.py`, `survsim/cli.py::dataset` | to add (`--split-by scenario`) |
| 3 | `synthetic_topdown` flag and refusal to report on it | `build.py`, `survsim/baselines/run.py` | done |
| 4 | Manifest provenance: commit, content hash, profile params, bodies | `build.py` | to add (§13.6) |
| 5 | MOT GT with visibility; COCO with keypoints | `survsim/gt/writers.py`, `survsim/gt/coco.py` | done |
| 6 | Events with hard-negative tags, `t_detectable_from`, `observed_by` | `survsim/gt/writers.py`, `survsim/director/behaviours.py` | partial (last two missing) |
| 7 | Live camera status (PTZ, tamper) | `gt/camera_status.jsonl` via `Recorder.add_camera_status` | done |
| 8 | Identity/appearance-epoch table | `Recorder._write_identities` | done |
| 9 | Per-frame IQA sidecar | `survsim/realism/stats.py` → new `gt/iqa_<cam>.parquet` | to add |
| 10 | Height-bucket and condition stratification in baseline reports | `survsim/baselines/run.py`, `survsim/eval/detection.py` | partial |
| 11 | Degenerate-split detection (no positives) | `survsim/eval/behaviour.py` | done (docs/11 bug 9) |
| 12 | Simulated operator dispositions (§14.2 schema) | new `survsim/eval/operator.py` | missing |
| 13 | Alarm funnel per stage for registry records | `survsim/eval/pipeline.py` | to add |
| 14 | Fairness strata (mobility aids, clothing) in reports | `survsim/director/population*`, `eval/*` | partial |
| 15 | Licence/personal-data flags in manifest | `build.py` | to add |

---

## References

All fetched or confirmed by search on 2026-09-26.

1. Regulation (EU) 2024/1689 (Artificial Intelligence Act), OJ L, 12 July 2024. https://eur-lex.europa.eu/eli/reg/2024/1689/oj
2. Gibson Dunn, "EU AI Act Omnibus Agreement — Postponed High-Risk Deadlines and Other Key Changes", 2026. https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/
3. Cloud Security Alliance research note, "EU AI Act's High-Risk Deadline: Deferred, Not Cancelled", 2026. https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-deadline-omnibus-20260/
4. ICO, CCTV and video surveillance guidance hub. https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/
5. Home Office, "Update to Surveillance Camera Code of Practice" (amended code in force 12 Jan 2022). https://www.gov.uk/government/publications/update-to-surveillance-camera-code
6. Ecl-ips, "Operate CCTV? Be aware of data protection law changes" (DUAA 2025 effect on the Code), 2026. https://ecl-ips.com/blog/operate-cctv-be-aware-of-data-protection-law-changes/
7. University of Stirling, "Surveillance expert is new Biometrics and Surveillance Camera Commissioner", Nov 2025. https://www.stir.ac.uk/news/2025/november-2025-news/university-of-stirling-surveillance-expert-is-new-biometrics-and-surveillance-camera-commissioner/
8. R (Bridges) v Chief Constable of South Wales Police [2020] EWCA Civ 1058, 11 Aug 2020. https://www.judiciary.uk/judgments/r-bridges-v-cc-south-wales/
9. B. Settles, "Active Learning Literature Survey", Univ. of Wisconsin–Madison CS Tech. Report 1648, 2009. https://burrsettles.com/pub/settles.activelearning.pdf
10. MLflow Model Registry documentation. https://mlflow.org/docs/latest/ml/model-registry/
11. M. Mitchell et al., "Model Cards for Model Reporting", FAT* 2019. https://arxiv.org/abs/1810.03993
12. T. Gebru et al., "Datasheets for Datasets", CACM 2021. https://arxiv.org/abs/1803.09010
13. H. Hukkelås, F. Lindseth, "DeepPrivacy2: Towards Realistic Full-Body Anonymization", WACV 2023. https://arxiv.org/abs/2211.09454
14. CVAT source. https://github.com/cvat-ai/cvat
15. CVAT Cloud pricing. https://www.cvat.ai/pricing/cloud
16. BSI PAS 1883:2020, ODD taxonomy for an automated driving system (listed as withdrawn). https://knowledge.bsigroup.com/products/operational-design-domain-odd-taxonomy-for-an-automated-driving-system-ads-specification
17. S. E. Ebadi et al., "PeopleSansPeople: A Synthetic Data Generator for Human-Centric Computer Vision", 2021. https://arxiv.org/abs/2112.09290
18. M. Fabbri et al., "MOTSynth: How Can Synthetic Data Help Pedestrian Detection and Tracking?", ICCV 2021. https://arxiv.org/abs/2108.09518
19. M. J. Black et al., "BEDLAM: A Synthetic Dataset of Bodies Exhibiting Detailed Lifelike Animated Motion", CVPR 2023. https://arxiv.org/abs/2306.16940
20. Weights & Biases pricing. https://wandb.ai/site/pricing/
21. DVC. https://dvc.org/
22. lakeFS pricing. https://lakefs.io/pricing/
23. HumanSignal (Label Studio) pricing. https://humansignal.com/pricing/
24. DataX Power, "Data Annotation Tools Compared: Labelbox vs. Scale AI vs. CVAT vs. Encord (2026)" (secondary). https://www.dataxpower.com/blog/data-annotation-tools-comparison-2026
26. Regulation (EU) 2026/1744 (Digital Omnibus on AI), OJ 24 July 2026. http://data.europa.eu/eli/reg/2026/1744/oj (confirmed via https://www.nicfab.eu/en/posts/digital-omnibus-ai-official-journal/)
25. Label Your Data, "Scale AI Review 2026" (secondary; market rates). https://labelyourdata.com/articles/scale-ai-review

MOTChallenge data (MOT17/MOT20) and MOTSynth are released under CC BY-NC-SA
3.0, which forbids commercial use (https://motchallenge.net/). Use them for
internal reference measurement only, never as commercial training data
without a separate licence.

In-repo: docs/03, docs/11, docs/13, docs/15; research R02 §5, R03 §9, D06, D08.
