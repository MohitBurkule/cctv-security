# 59 · Explainability, assurance and audit trails for alarm systems

How a defence or CNI buyer expects an alarm system to justify itself: why each
alarm fired, why the model can be trusted in *this* operating context, and how
anyone can prove afterwards that the record was not changed. Written 2026-09-27
for the the vendor interview; it pulls together 38 (JSP 936 paragraph map), 21
(governance), 44 (law), 49 (statistics), 51 (operators), 52 (brief) and 58
(loiter redesign), and adds fetched primary sources for model cards,
datasheets, AMLAS, GSN, BS 10008, saliency sanity checks, TCAV and Merkle logs.

Tags: **[F]** read on the primary source on 2026-09-27 (or on 2026-09-26 for
JSP 936, via 38); **[R]** repo-sourced with commit; **[INF]** my inference or
design, not a claim about any source. Every SurvSim number is copied from
`FACTS_VERIFIED.md` or `58_LOITER_RULE_REDESIGN.md`; where FACTS disagrees with
a dossier, FACTS wins.

---

## 0. The answer in five sentences

1. A security buyer does not want a heat map. They want an **evidence pack**
   per alarm: the frames, the track, the rule that fired and the values it
   fired on, the model and configuration versions, and the camera calibration
   at that moment.
2. For the *system*, they want an **assurance case**: a structured argument
   (GSN or Claims–Arguments–Evidence) that links "this alarm is acceptably
   reliable in this operating context" to test evidence, with JSP 936
   paragraphs 76, 158, 160–163, 170–172 and 179–181 as the checklist for UK
   defence **[F via 38]**.
3. The evidence has to be **reproducible and untampered**: seeded runs,
   hashed data manifests, pre-registered tests, and a hash-chained audit log
   of every alarm, operator action and model update (BS 10008-1:2020 is the
   UK standard for the evidential weight of electronic records **[F]**).
4. In service, assurance does not end at release. JSP 936 para 179–180 say
   the ODD and performance "must be monitored" **[F via 38]**, so the
   system needs drift monitors on the inputs and on the alarm rate, with an
   incident review loop that feeds new cases back into the test suite.
5. SurvSim already produces some of this evidence: render gates,
   pre-registered experiments with commit hashes, per-subsystem seeds,
   licence provenance per set, and alarm scoring in FA/camera-hour. It does
   **not** yet produce per-alarm evidence packs, a signed or hash-chained log,
   a real-data verification set, or a model card per release.

---

## 1. What "explainable" means to the people who pay

### 1.1 Three families of explanation

| Family | What it shows | Example methods | What an operator or auditor can do with it |
|---|---|---|---|
| **Saliency / attribution** | which pixels moved the score | Grad-CAM, integrated gradients, occlusion | little; it is a debugging aid for the ML team |
| **Concept-based** | which human concepts the network uses | TCAV (concept activation vectors) | useful for bias and ODD audits ("does the intruder score depend on 'hi-vis jacket'?") |
| **Rule trace / structured reason** | which rule fired, on which track, with what values vs thresholds | dwell timer, zone ID, speed profile, rule version | the operator can check it against the video in seconds; the auditor can re-run it |

**Saliency is weaker than it looks.** Adebayo et al., *Sanity Checks for
Saliency Maps* (NeurIPS 2018 — confirmed on papers.nips.cc; arXiv 1810.03292) found that "some existing
saliency methods are independent both of the model and of the data
generating process" **[F]**: randomise the weights and some maps barely
change. If a map does not depend on the model, it cannot explain what the
model did. That is the sentence to have ready when someone proposes Grad-CAM
overlays as the explainability feature.

**Concept-based methods answer auditor questions.** Kim et al., *TCAV*
(ICML 2018, arXiv 1711.11279) define a concept activation vector as "an
interpretation of a neural net's internal state in terms of human-friendly
concepts" **[F]**. For a surveillance model the concepts are ones a bias
analysis under JSP 936 para 69 would need: clothing colour, headwear,
carried objects, mobility aids, skin tone **[INF]**. SurvSim can generate the
concept sets on demand, because the population generator controls these
attributes and records them in `identities.parquet` **[R]**.

**Rule traces are what operators actually use.** Doc 51's alarm-card
patterns (§ on alarm UI) and the BS 8418 / NPCC context are all about
getting an operator to a correct verdict in seconds: a short clip with the
track drawn in, the zone, the dwell or path value against the threshold,
and a one-line reason ("in gate zone 4 for 41 s; threshold 25 s; moving
fraction 0.18") **[INF, grounded in 51]**. An operator who faces a false
alarm every few minutes has no time for a heat map. The structured reason
also has to survive in the log, so that an alarm reviewed a month later can
be re-explained exactly as it was at the time.

### 1.2 Explain the three layers separately

| Layer | The question | The evidence that answers it |
|---|---|---|
| Detection | "Was there really a person there?" | box on the frame, detector score, model hash; the calibrated score (JSP 936 para 167 asks for "measures of uncertainty that are understandable" **[F via 38]**) |
| Track | "Is it the same person throughout?" | track ID over time, ID switches flagged, association cost at each switch, ReID similarity if used across cameras |
| Alarm | "Why is this an alarm and not a commuter?" | rule ID and version, the features it fired on vs thresholds, zone, time-of-day policy, suppression state, i-LIDS window |

Most alarm errors in SurvSim's own experiments are at the **alarm** layer,
not the detection layer. H12 used perfect perception (ground-truth tracks) and
every loiter rule still ran **4,500–87,000× over our assumed 0.001 FA/cam-h** **[R,
`9dea4f9`]**. So an explanation that stops at "the detector saw a person"
explains nothing about why the alarm was wrong. The top nuisance causes in H12
were behavioural look-alikes — for the dwell rules, commute_wait + queue
(≥ 90 %); for path_loiter_15, transit (54 %) **[R]** — and the rule trace
is what makes those visible.

### 1.3 VLM captions are not explanations

A vision-language model can write "a man in a grey hoodie loitering near the
gate", and operators like reading it (45 covers the cost). It is a
*description*, generated separately from the decision; it can be fluent and
wrong. Treat it as a second opinion with its own error rate, log its model
version and prompt, and never let it replace the rule trace **[INF]**.

---

## 2. The per-alarm evidence pack

A design for what every alarm should carry. Items marked ✓ exist in
SurvSim's ground truth today; the rest are gaps **[R / INF]**.

| Item | Why a buyer wants it | SurvSim today |
|---|---|---|
| Alarm ID, UTC time, camera ID, zone ID | the basic record | ✓ `events.jsonl` has event time, camera, zone |
| Pre/post clip (e.g. −10 s / +5 s), keyframes | operator verification; court disclosure | frames exist per run; no per-alarm clip export |
| Track: IDs, boxes, visibility per frame | shows the object and occlusions | ✓ MOT + parquet, mask-derived boxes, visibility fraction |
| Rule trace: rule ID and version, feature values, thresholds | the explanation | partial — `tools/loiter_eval.py` computes features; not written per alarm |
| Model versions: detector, tracker, ReID hashes; config hash | reproducibility; JSP 936 paras 165–166 | code commit only |
| Camera calibration and pose at alarm time | principle 2: GT must follow the live camera | ✓ `calib/`, PTZ and tamper state tracked by the camera director |
| Degradation / health state | an alarm from a blinded camera is suspect | ✓ tamper kinds in GT; no live health score |
| i-LIDS timing (delay since event onset) | late alarm = false alarm | ✓ scorer, 10 s i-LIDS window, 30 s default tolerance |
| Operator verdict, reason code, time to verdict | the feedback loop; JSP 936 para 172 regression | gap |
| Licence and provenance of any training data | commercial use; EU AI Act documentation | ✓ `licences.json`, `commercial_ml_ok` per set (`9c87424`) |
| Hash of the pack, chained to the previous entry | tamper evidence (BS 10008) | gap |

The pack does double duty. For the operator it is the alarm card. For the
auditor it is a reproducible record: given the hashes, anyone can re-run the
same model on the same frames and get the same rule trace. That is
explainability you can test.

---

## 3. Documentation: model cards and datasheets

### 3.1 Model cards (Mitchell et al. 2019)

*Model Cards for Model Reporting*, Mitchell, Wu, Zaldivar, Barnes, Vasserman,
Hutchinson, Spitzer, Raji, Gebru, FAT* 2019 (arXiv 1810.03993) **[F]**. A
model card gives "benchmarked evaluation in a variety of conditions, such as
across different cultural, demographic, or phenotypic groups (e.g., race,
geographic location, sex, Fitzpatrick skin type)" and discloses "the context
in which models are intended to be used, details of the performance
evaluation procedures, and other relevant information" **[F]**.

This maps directly onto JSP 936 paras 165–166 (a model "must be accompanied
by relevant information … assumptions, dependencies, known errors and
weaknesses", including the ODD) **[F via 38]**. The card for an intrusion or
loiter analytic should show, per ODD cell (day/night, range band, crowd
density, camera height), the detection recall, the FA/cam-h with a Garwood
interval and the i-LIDS delay — the disaggregated evaluation Mitchell asks for,
using operating-point metrics instead of AUC **[INF]**.

### 3.2 Datasheets for datasets (Gebru et al. 2021)

*Datasheets for Datasets*, Gebru, Morgenstern, Vecchione, Wortman Vaughan,
Wallach, Daumé III, Crawford, Communications of the ACM, December 2021 (arXiv
1803.09010) **[F]**: every dataset should document "its motivation,
composition, collection process, recommended uses, and so on" **[F]**.

For SurvSim a datasheet per render batch is mostly already in the repo; it is
just not in one file **[R]**:

* **Motivation and composition:** batch_v8 = 9 sets (4 scenarios × day/night
  + disguise), 10,000 frames, gate 9/9, CC0 cast (`94145fa`).
* **Collection process:** scenario YAML, seed, SurvSim commit, degrade profile.
* **Label quality:** height gate 0 people beyond 2 cm on all 9; box
  tightness median IoU vs detector 0.876–0.932; amodal holdout IoU vs mask
  0.879–0.914.
* **Known limits:** realism 6/14 statistics in band for `cctv_day`, 3/14 [vs day targets; vs real LLVIP night 3/13 vis · 2/13 thermal, raw renders luma 90 = not dark (69 §7)] for
  `cctv_night_ir` (`docs/15`).
* **Recommended uses and licence:** `commercial_ml_ok: true`; MetaHuman
  batches v4–v6 internal only, because the MetaHuman licence forbids use "to
  build or enhance any database or train or test artificial intelligence"
  **[F, FACTS]**; MOT17/MOT20 are CC BY-NC-SA 3.0, evaluation only.

JSP 936 para 163 adds a requirement datasheets do not: synthetic data must be
validated "from the perspective of the AI … because AI can cue on different
features of the data than a human" **[F via 38]**. H13 is the start of that
evidence: image-statistic distance to MOT20-02 vs real AP, Spearman −0.60
[−0.78, −0.20], perm. p = 0.005, n = 20, 1 seed, exploratory **[R]**.

---

## 4. Assurance cases: GSN, CAE and AMLAS

### 4.1 The notation

An assurance case is a structured argument that a claim (e.g. "the loiter
alarm is acceptably reliable for site X") is supported by evidence. Two
notations dominate:

* **GSN (Goal Structuring Notation)**, maintained by the Safety-Critical
  Systems Club's GSN Standard Working Group; **Version 3** is the current
  release, providing "a comprehensive, authoritative definition of the Goal
  Structuring Notation" **[F, scsc.uk/gsn-standard, 2026-09-27; re-fetch
  in the audit reached the page but the v3 PDF download was reset by the
  server]**. GSN was developed at York in the early 1990s (Kelly's thesis)
  and first standardised as the Community Standard in 2011 **[secondary,
  Wikipedia]**. The elements are Goals (claims), Strategies (how a goal is
  decomposed), Solutions (evidence), and Context, Assumptions and
  Justifications **[INF: standard GSN vocabulary; the v3 PDF could not be
  retrieved, so the element list is not checked against it]**.
* **CAE (Claims–Arguments–Evidence)**, the simpler three-element form
  associated with Adelard; see Bloomfield & Bishop, *Safety and Assurance
  Cases: Past, Present and Possible Future — an Adelard Perspective*,
  Safety-critical Systems Symposium 2010, Springer *Making Systems Safer*,
  doi 10.1007/978-1-84996-086-1_4 **[bibliographic record confirmed via
  Crossref; paper text closed-access, not read — the "three elements" and
  "UK nuclear and defence practice" remain INF]**.

The buyer does not care which notation. They care that every claim ends in
evidence they can inspect, and that assumptions are written down rather than
buried.

### 4.2 AMLAS (University of York, 2021)

*Guidance on the Assurance of Machine Learning in Autonomous Systems
(AMLAS)*, Hawkins, Paterson, Picardi, Jia, Calinescu, Habli, Assuring
Autonomy International Programme, University of York, Version 1, February
2021 (arXiv 2102.01564) **[F]**. It "comprises a set of safety case patterns
and a process for (1) systematically integrating safety assurance into the
development of ML components and (2) for generating the evidence base for
explicitly justifying the acceptable safety of these components" **[F]**.

The six stages (from the document's contents) **[F]**:

| Stage | AMLAS name | Loiter-alarm equivalent **[INF]** |
|---|---|---|
| 1 | ML Safety Assurance Scoping | the alarm's role in the site's security case; ODD |
| 2 | ML Safety Requirements Assurance | FA/cam-h budget, recall at tolerance, i-LIDS timing |
| 3 | Data Management | data requirements for "relevance, completeness, accuracy and balance" **[F]** |
| 4 | Model Learning | rule / model selection on a disjoint training split |
| 5 | Model Verification | held-out verification, "sufficiently independent from the development activities" **[F]** |
| 6 | Model Deployment | integration test, in-service monitoring |

Two AMLAS sentences worth quoting: data requirements "shall include
consideration of the relevance, completeness, accuracy and balance" of data,
and "All verification activities shall be sufficiently independent from the
development activities" **[F]**. The second is JSP 936 para 158 in different
words (separate training, test and verification data "maintained
independently") **[F via 38]**.

### 4.3 JSP 936 as the checklist

Doc 38 §4.2 maps the paragraphs. The ones an assurance case for a CCTV alarm
must answer, in order **[F via 38]**:

* **38, 75, 177** — ODD defined, including geospatial/temporal/functional
  constraints.
* **76** — performance targets "demonstrated to a level of confidence that
  is commensurate with the risk" → FA/cam-h and recall *with intervals*.
* **78** — defined response to out-of-design inputs → "capability reduced"
  state on camera tamper or night IR.
* **82** — failure-mode analysis → the tamper and evasion catalogue (50).
* **146–147, 158** — sealed verification data, independent of tuning.
* **160** — edge cases "inside, on, and beyond the boundary conditions" →
  the simulator's strongest argument.
* **161–163** — provenance recorded from collection to ingestion; synthetic
  data validated from the model's viewpoint.
* **165–167** — model card with known weaknesses; understandable uncertainty.
* **170–172** — V&V across the ODD; regression after updates.
* **179–181** — monitoring in service; continued assurance under change.

---

## 5. ML test and verification evidence: what SurvSim already has

| Evidence type | SurvSim artefact | Status |
|---|---|---|
| **Pre-registration** | hypothesis, metric, thresholds and stop rules committed before the run; H12 (`98b7c03` pre-reg), H14 (`98b7c03`), H58 (`0c0976f`) | **[R]** done for the big claims |
| **Negative results reported** | H1 synthetic-only fine-tune 0.276 → 0.152 ± 0.025 AP; H58 verdict FAIL against its own pre-registration | **[R]** |
| **Multiple-comparison control** | H14 Holm-rejected (exact perm. p 0.0079) | **[R]** |
| **Operating-point metrics** | FA/cam-h with Garwood intervals and world-bootstrap intervals (~3× wider); i-LIDS scoring | **[R]** |
| **Render and label gates** | `check_render` gate 9/9 batch_v8; height gate; box-tightness gate; stuck-agent audit | **[R]** |
| **Determinism** | `RngHub` seeded per subsystem; same seed ⇒ same run; mask decoder byte-identical MOT and parquet (`1fd38df`) | **[R]** |
| **Regression tests** | 881 collected, 859 selected at `94145fa`; one per bug (e.g. the `unreal.Rotator` keyword test) | **[R]** |
| **Adversarial audits** | AUDIT_* files; corrections logged (e.g. realism 12/14 → 6/14, HOTA 0.545 → 0.434 → 0.443 TrackEval parity) | **[R]** |
| **Licence provenance** | `licences.json`, `commercial_ml_ok`, per-person `asset_licences` | **[R]** `9c87424` |

What is **missing** for a real assurance case **[INF]**:

1. **A real, sealed verification set** under the buyer's ODD (JSP 936
   paras 146–147, 158). Everything real so far is MOT20-01/02, probably one
   site, non-commercial licence.
2. **Real hard negatives at scale.** H12's 3,002 camera-hours are mock
   worlds; the FA rate transfers only as far as the behaviour mix does.
3. **Uncertainty calibration** (para 167): reliability diagrams and ECE for
   detector and alarm scores; 49 has the method, nothing is shipped.
4. **Per-alarm evidence packs and a hash-chained log** (§2, §6).
5. **Model cards and datasheets as files**, one per release and per batch.
6. **Independence** (AMLAS stage 5): the same person wrote the rules, the
   scorer and the tests. Pre-registration reduces, but does not remove, that.
7. **Drift monitors** in any deployed form (§7).

---

## 6. Audit trails and tamper-evident logs

### 6.1 The standard

**BS 10008-1:2020**, *Evidential weight and legal admissibility of
electronically stored information (ESI) — Specification*, published 31 May
2020, current; it replaces the 2014 edition and adds IoT, distributed-ledger,
cloud and UK GDPR / DPA 2018 content **[F, BSI Knowledge]**. Its purpose is to
keep ESI "demonstrably trustworthy about its authenticity and integrity"
throughout its lifecycle, covering electronic transfer, identity linking and
digital signatures **[F]**. (The first edition, BS 10008:2008, was withdrawn
8 December 2014 **[F]**.) Doc 53 covers the storage side: object-lock WORM
buckets and signed manifests.

### 6.2 The mechanism: hash chains and Merkle trees

* **Hash chain.** Each log entry stores `h_i = SHA-256(h_{i−1} ‖ entry_i)`.
  Changing any past entry changes every later hash, so a verifier holding
  only the latest hash can detect edits **[INF, standard construction — not
  from RFC 6962, which defines a Merkle tree, not a linear chain]**.
* **RFC 6962 §2.1 Merkle Tree Hash:** leaf `SHA-256(0x00 ‖ d)`, interior
  node `SHA-256(0x01 ‖ left ‖ right)`; the distinct prefixes stop a leaf
  being passed off as a node **[F, re-fetched 2026-09-27]**.
* **Merkle tree (RFC 6962, Certificate Transparency, June 2013).** "The
  append-only property of each log is technically achieved using Merkle
  Trees, which can be used to show that any particular version of the log is
  a superset of any particular previous version" **[F]**. Consistency proofs
  are logarithmic in log size, and "if a log attempts to show different
  things to different people, this can be efficiently detected by comparing
  tree roots" **[F]**.
* **Anchoring.** Periodically sign the head hash with an organisation key
  (HSM) and write it somewhere the operator cannot edit — a WORM bucket, a
  second site, or the customer's own system **[INF]**.

### 6.3 What goes in the log **[INF]**

Every alarm evidence pack hash; every operator action (acknowledge, dismiss
with reason code, escalate), with operator ID hashed for privacy (21 has the
schema field `operator_id_hash`); every configuration change (zones,
thresholds, schedules, suppressions — 51 notes that a suppression needs "an
expiry and an audit trail"); every model or rule deployment with its bundle
hash and signature; every camera health event (tamper, blind, PTZ off-preset);
every access to or export of footage. For UK police use, the export must
carry the hash so the recipient can re-verify at disclosure (44 lists
"evidential-grade export: timestamps, hash chain, calibration" under the
Surveillance Camera Code's effectiveness principle).

---

## 7. In service: drift, performance monitoring and incident review

JSP 936 para 179–180: the operational environment "must be monitored" to
stay within the ODD, and performance "must be monitored" **[F via 38]**.
Para 172: after updates, V&V "must include testing for both existing and new
behaviours", to rule out "catastrophic forgetting and model drift" **[F via
38]**.

**What to monitor [INF, methods from 49]:**

| Signal | Why | Method |
|---|---|---|
| Alarms per camera-hour | the operational KPI; a jump is a nuisance source or a fault | CUSUM against a per-camera baseline (49); Garwood interval for "is this real?" |
| Operator dismiss rate by reason code | the only real-world precision label you get cheaply | weekly by camera and rule |
| Input statistics (brightness, contrast, blur, noise, compression) | ODD drift: new lighting, dirty lens, codec change | the same 13 image statistics as `docs/15` / H13, per camera |
| Detection score distribution, track length, ID-switch rate | model drift before alarms change | population-stability or KS vs commissioning week |
| Camera health (tamper, off-preset) | GT follows the live camera; so must assurance | the camera director's tamper kinds as monitored states |

**The zero-event trap.** "No missed intrusions in the last month" proves
little. Rule of three: 0 events in 30 camera-hours only bounds the rate
below 0.1/h at 95 %; to show 0.001 (assumed, 28 §6) FA/cam-h needs ~3,000 camera-hours (55
§13, 49). That is why a simulator is useful in service too: it can inject
scripted events (red-team or synthetic replay) to keep measuring recall where
real events are rare **[INF]**.

**Incident review loop [INF].** Every missed event or bad alarm becomes (1) a
log-linked incident record, (2) a root-cause class (perception, tracking,
rule, configuration, camera health, operator), (3) a new SurvSim scenario or
real clip in the regression suite, and (4) a model-card update if it reveals
a weakness. The SurvSim stories that show this pattern: stuck agents (a
"walking" label on people who were not moving → the motion audit, 35 % → 0
%), HOTA bug (0.545 → 0.434, 0.443 at TrackEval parity, with regression tests), everyone-1.70 m
(`92e1e97`, now a > 2 cm height gate).

---

## 8. Human-in-the-loop accountability

JSP 936's five principles are Human Centricity, Responsibility, Understanding,
Bias and Harm Mitigation, Reliability **[F via 38]**. For an alarm system,
"Responsibility" turns into three concrete things **[INF]**:

1. **A named human decides.** The analytic raises; an operator verifies; a
   response is dispatched by a human. The log records who and when. The NPCC
   rule in 51 (3 false calls in 12 months ⇒ police response withdrawn) shows
   the cost of letting unverified alarms through.
2. **The operator can see why and can disagree.** The evidence pack and
   rule trace let them dismiss with a reason; the dismissal is itself data.
3. **Automation bias is designed against.** Do not show a confidence number
   the operator cannot interpret; show the rule trace and the clip. 51's
   vigilance evidence (e.g. Donald 2015, 50 % detected) says human
   verification is fallible too, so measure it.

On the legal side (44): UK GDPR Art 22 and the DPA 2018 limit solely
automated decisions with significant effects; the EU AI Act puts
high-risk-system obligations (logging, human oversight, technical
documentation) on the Annex III timetable, now 2 Dec 2027 under Omnibus Reg
2026/1744 **[FACTS]**. Bridges [2020] EWCA Civ 1058 turned on the
*framework* — who can be put on a watchlist, where, and the equality duty —
not accuracy alone **[FACTS / 44]**. An audit trail is how you show the
framework was followed.

---

## 9. Worked example: an assurance case for the loiter alarm

Written as CAE with GSN-style labels. Every number is from `58` or FACTS
**[R]**; the structure is **[INF]**.

**G0 (top claim).** The C4 learned loiter rule (`LearnedLoiterRule`,
retrained in 58 round 2, θ = 0.9, clock ≥ 10 s) is acceptably reliable for
use as an *operator cue* at a CNI perimeter gate, within ODD-1.

* **C0 (context).** ODD-1 = mock worlds with the H12 behaviour mix; ground-truth
  tracks (perfect perception); daytime; gate-tagged entrance zones. Budget
  0.001 (assumed, 28 §6) FA/cam-h (an operator budget from 51); tolerance 30 s; scoring
  `actor_aware=True` (an alarm counts only if it is on the event's actor).
* **A0 (assumption).** The mock behaviour mix is representative of the site.
  *Unvalidated — the biggest hole in the case.*

**S1 (strategy).** Argue over (a) false-alarm rate, (b) recall and timing,
(c) independence of evidence, (d) data provenance and realism, (e) residual
risk.

**G1 — False-alarm rate is characterised.**
* **E1.1** C4 (round 2) = **3.745 FA/cam-h [3.676, 3.815]** Garwood over
  3,002 clean camera-hours (58 §6.2, `44e34f5`). Round 1 (`070cf97`) gave
  2.915 [2.854, 2.977] before the `473ace3` simulator fix; that figure is
  superseded.
* **E1.2** Baseline dwell_25 = 6.007 → C4 3.745: a 1.60× reduction (round 1
  said 2.06×).
* **Verdict:** characterised, but **~3,700× over our assumed budget**. G1 as "meets
  budget" is **FALSE**. The case must say so.

**G2 — The budget is unattainable by any track-only rule on these worlds.**
* **E2.1** Kinematic-twin floor: 3,027 smoke breaks pace in gate zones =
  **1.008 FA/cam-h [0.973, 1.045]**, unchanged in round 2; `SmokeBreak` is
  kinematically identical to `Loiter` within 30 s. Any rule with recall r
  pays ≈ r × 1.0 FA/cam-h → at C4's recall 0.831, ~830× our assumed budget is the floor.
* **Consequence:** the claim becomes "cue for human verification", not
  "autonomous alarm". Meeting 0.001 needs more information (identity,
  authorisation badge, time-of-day policy, a second sensor), not a better
  rule.

**G3 — Recall and timing are adequate.**
* **E3.1** Actor-aware recall@30 s **0.831 [0.792, 0.869]** on 360 events;
  the label oracle reaches 1.000 under actor-aware scoring.
* **E3.2** Actor-aware recall@10 s 0.097 — at the i-LIDS 10 s window almost
  no loiters alarm in time. *Weak.*
* **E3.3** Precision@30 s 0.326 [0.304, 0.352]. For comparison dwell_25's
  actor-aware recall is only **0.367** (its window-only 0.900 in H12 was
  mostly alarms on bystanders) and dwell_60's is 0.000.

**G4 — The evidence is independent of rule selection.**
* **E4.1** Pre-registered `0c0976f` (round 1) and 58 §6.1 (round 2) before
  scoring; success, partial and abandon criteria written in advance.
* **E4.2** Rule selected on a disjoint split (seeds 58/59: 150 clean + 300
  recall worlds); round-2 train 3.95 FA/cam-h, 0.858 recall → H12 3.745,
  0.831.
* **E4.3** Verdict reported as **FAIL, as predicted**, and the round-2
  prediction that the margin could shrink (P3) was written down before it
  did — the pre-registration held the author to it.
* **Residual:** same author wrote the generator, rule and scorer (AMLAS
  stage 5 independence not met).

**G5 — Data provenance and realism are known.**
* **E5.1** Worlds from the mock backend; seeds recorded; deterministic.
* **E5.2** For any rendered evidence: CC0 cast, `commercial_ml_ok: true`
  (`9c87424`); MetaHuman batches excluded by licence; MOT20 evaluation only.
* **E5.3** Realism of renders **6/14 day, 3/14 [vs day targets; vs real LLVIP night 3/13 vis · 2/13 thermal, raw renders luma 90 = not dark (69 §7)] night** — so rendered
  evidence cannot stand in for real footage (JSP 936 para 163).
* **E5.4** Perception gap: H12 used perfect tracks; H3 shows far cameras
  (13–45 px) at recall 0.021 at 640 px input. Real FA/cam-h will be *worse*
  once tracks fragment. *Gap: re-run on detector tracks.*

**G6 — Residual risk and monitoring.**
* **E6.1** In-service: alarms/cam-h CUSUM per camera; dismiss reasons; input
  statistics drift (§7).
* **E6.2** Out-of-ODD: night IR is out of ODD-1 (H11: `cctv_night_ir`
  degrade −0.609 recall, a simulated sensor-model value; H32: profiles overfit, no night penalty quotable) → "capability reduced" state (JSP 936 para 78).

**What this case supports.** "C4 has 1.6× fewer false alarms than a dwell
timer and 2.3× its actor-aware recall, fit to raise cues for a verifying
operator, in daytime, at a camera load where ~4 cues per camera-hour is
affordable." It does **not**
support "autonomous loiter alarm within an assumed 0.001 budget", and it says why,
with a number (the 1.008 floor). A buyer trusts a case that shows its own
failure more than one that shows only green boxes.

**Operator load check (51's formula U = C·B·t/3600).** At the round-2
3.745 FA/cam-h, 40 cameras and 30 s per verification:
40 × 3.745 = 149.8 cues/h; × 30 s = 4,494 s; / 3,600 = **1.25 operators**
— for one rule alone **[INF, arithmetic]**. (The round-1 figure was
40 × 2.92 × 30 / 3600 = 3,504 / 3,600 = 0.97; with the unrounded 2.915 it
is 0.972.) That is the sentence that makes the budget concrete.

---

## 10. Interview Q&As

**Q1. What does explainability mean for a CCTV analytic?**
Three layers — detection, track, alarm — each with its own evidence. For
operators, a rule trace with the clip ("gate 4, 41 s, threshold 25 s") beats
any heat map. Saliency maps fail sanity checks: Adebayo et al. found some
are "independent both of the model and of the data generating process". I
would use concept tests (TCAV) for bias audits, and saliency only for
debugging.

**Q2. What is in your evidence pack per alarm?**
Clip and keyframes, track with boxes and visibility, rule ID/version and
feature values vs thresholds, model and config hashes, camera calibration
and health at alarm time, i-LIDS delay, operator verdict — all hashed into
an append-only log. SurvSim already writes the track, calibration, tamper
state and event timing; the per-alarm pack and the log are gaps.

**Q3. How would you build an assurance case for a new model under JSP 936?**
AMLAS's six stages as the process, GSN or CAE as the notation, JSP 936 as
the checklist: ODD (38/75/177), targets with confidence (76), out-of-ODD
response (78), sealed verification data (158), boundary cases (160),
provenance (161–162), synthetic data validated from the model's view (163),
model card (165–166), regression after updates (172), in-service monitoring
(179–180).

**Q4. Your loiter rule is ~3,700× over our assumed budget. Why would anyone deploy it?**
Not as an autonomous alarm. The pre-registered redesign cut dwell_25's
rate 1.6× (6.01 → 3.75 FA/cam-h) while raising actor-aware recall from
0.367 to 0.831 — dwell_25's old 0.900 was mostly bystanders — and proved a
floor: smoke breaks are kinematic twins of loiters, ~1.0 FA/cam-h, so no
track-only rule can reach 0.001. The case therefore supports a cue for human
verification and says what extra information — authorisation, time policy,
a second sensor — the budget needs.

**Q5. How do you make the audit log tamper-evident?**
Hash-chain each entry to the previous one; batch into a Merkle tree as in
RFC 6962 so you can prove the log only grew; sign and anchor the head in a
place the operator cannot write (WORM, second site). Map the process to
BS 10008-1:2020 for evidential weight. Log operator actions and config
changes, not just alarms.

**Q6. How do you know the model is still fine six months after deployment?**
JSP 936 179–180 require monitoring. Per-camera CUSUM on alarms/cam-h,
operator dismiss rate by reason code, input image statistics vs
commissioning, detection score and track-length distributions. Zero missed
events proves little — rule of three says 30 quiet hours only bounds the
rate under 0.1/h — so inject scripted test events.

**Q7. What does a model card for a surveillance model need beyond Mitchell's template?**
Operating-point metrics per ODD cell: recall, FA/cam-h with a Garwood
interval, i-LIDS delay. Out-of-ODD behaviour. Training-data licences
(MetaHuman and SMPL-X forbid this use; MOT20 is non-commercial). Known
failure modes, e.g. far cameras at 640 px recall 0.021.

**Q8. What is SurvSim's weakest assurance evidence, and how would you fix it?**
Independence and real-world validity. The same person wrote the generator,
rule and scorer; the behaviour mix is assumed; realism is 6/14 day, 3/14 [vs day targets; vs real LLVIP night 3/13 vis · 2/13 thermal, raw renders luma 90 = not dark (69 §7)]
night; H12 used perfect tracks. Fixes: a sealed real verification set at the
customer's site, a second person owning the scorer, and re-running H12/H58
on detector tracks rather than ground truth.

---

## 11. Sources

Primary, fetched 2026-09-27 unless stated:

1. M. Mitchell et al., *Model Cards for Model Reporting*, FAT* 2019. https://arxiv.org/abs/1810.03993
2. T. Gebru et al., *Datasheets for Datasets*, CACM, Dec 2021. https://arxiv.org/abs/1803.09010
3. R. Hawkins et al., *Guidance on the Assurance of Machine Learning in Autonomous Systems (AMLAS)*, University of York AAIP, v1 Feb 2021. https://arxiv.org/abs/2102.01564 (PDF text extracted: stages, "relevance, completeness, accuracy and balance", independence clause)
4. SCSC GSN Standard Working Group, GSN Community Standard Version 3. https://scsc.uk/gsn-standard
5. BSI, BS 10008-1:2020 (31 May 2020, current). https://knowledge.bsigroup.com/products/evidential-weight-and-legal-admissibility-of-electronically-stored-information-esi-specification ; BS 10008:2008 withdrawn 8 Dec 2014: https://knowledge.bsigroup.com/products/evidential-weight-and-legal-admissibility-of-electronic-information-specification
6. B. Laurie, A. Langley, E. Kasper, RFC 6962 *Certificate Transparency*, June 2013. https://datatracker.ietf.org/doc/html/rfc6962
7. J. Adebayo et al., *Sanity Checks for Saliency Maps*, 2018. https://arxiv.org/abs/1810.03292 ; NeurIPS 2018 venue confirmed at papers.nips.cc (proceedings page, 2026-09-27)
8. B. Kim et al., *TCAV*, ICML 2018. https://arxiv.org/abs/1711.11279
9. MOD, JSP 936 Part 1 V1.1 — paragraphs as mapped in `38` §4.2 (fetched 2026-09-26). https://assets.publishing.service.gov.uk/media/6735fc89f6920bfb5abc7b62/JSP936_Part1.pdf

Repo: `FACTS_VERIFIED.md` (H3, H11, H12, H13, H14, batch_v8, licences, tests);
`58_LOITER_RULE_REDESIGN.md` §3–4 (pre-registration `0c0976f`);
`38` §4; `21` §model record; `44`; `49`; `51`; `52`; `53` (WORM).

10. R. Bloomfield, P. Bishop, *Safety and Assurance Cases: Past, Present and Possible Future — an Adelard Perspective*, SSS 2010. doi:10.1007/978-1-84996-086-1_4 (record only; text closed).

Still [INF] after the audit (`AUDIT_59-60.md`): GSN element names (v3 PDF
download reset), CAE's content (paper closed), the linear hash chain (a
standard construction, not RFC 6962's), Art 22 detail (see 44).
