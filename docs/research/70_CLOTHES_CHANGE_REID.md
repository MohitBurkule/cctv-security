# 70 — Clothes-change ReID: the problem, the evidence, and what a defence site should build

**Why this file exists.** Q5 of `68` ("re-identify the intruder after he changes
his jacket") was graded one of the six weakest answers: it had one number from
one paper (CAL on PRCC), a one-person case study (H10 v2) and a null (H20).
This dossier puts the whole problem in one place: the benchmarks with their
licences, the state of the art checked against the papers' own tables, the
method families, what a site system should actually do, where SurvSim's
appearance truth helps, and the design of H29.

Tags: **[V]** checked in the primary source on 2026-09-27 (table or abstract
text fetched from arXiv or the dataset's own page); **[A]** stated by a source
we did not open, or a design claim we have not tested; **[INF]** our own
inference. Numbers are rank-1 / mAP in %, **CC** = clothes-changing
protocol, **SC** = same-clothes, **general** = both kinds of gallery match
allowed.

---

## 1. The problem

### 1.1 Short-term and long-term ReID

*Short-term* ReID (Market-1501, MSMT17, DukeMTMC) matches a person across
cameras within minutes or hours, so the person is wearing the same clothes.
Methods are rewarded for learning clothing. That is fine for the data, but
it means a Market-1501 number of 94–95 % rank-1 (OSNet 94.2, CLIP-ReID 95.5;
FACTS) says almost nothing about a man who has taken his coat off.

*Long-term* or *clothes-changing* ReID (CC-ReID) keeps the identity label
across outfits. The benchmarks build a test that **removes every gallery
image of the query in the same clothes**, so an appearance shortcut cannot
score. That removal is what "CC protocol" means below, and it is the protocol
SurvSim's appearance epochs reproduce: gallery restricted to other
`(uid, epoch)` pairs.

### 1.2 Why appearance features collapse

A ReID embedding is trained with identity labels. On a short-term dataset
each identity is one outfit, so "identity" and "outfit" are the same label,
and the cheapest discriminative signal (colour and texture of the torso and
legs) wins. Three pieces of primary evidence:

* **CAL (Gu et al., CVPR 2022)** [V] — on PRCC, SC 100 / 99.8 against CC
  55.2 / 55.8: a 45-point rank-1 drop for the same model. On LTCC, general
  74.2 / 40.8 against CC 40.1 / 18.0. Plain RGB baselines are worse (PCB on
  PRCC: SC 99.8 → CC 41.8).
* **The face and hair are doing much of the work** — CAL's Table 6 feeds
  PRCC body regions only: CC rank-1 **24.5** / mAP 25.4 (baseline 18.7 / 20.4)
  [V]. Against the full-image 55.2 that is ~56 % of the score gone with the
  head [INF — our reading; CAL's authors read the same table as evidence that
  CAL's remaining gain is body shape, not clothes]. At CCTV standoff the
  head is a few pixels, so benchmark CC numbers overstate what survives at a
  perimeter.
* **MEVID (Davila et al., WACV 2023)**, 33 real surveillance cameras [V]:
  CAL scores **SC 56.6 / 39.0** and **different clothes 3.5 / 4.3**. At
  real CCTV range, the method that "solves" PRCC at 55 % is close to chance
  when the outfit changes.

SurvSim's own case study (H10 v2, `32`) agrees in direction and is not a
result: one changer, 3 epoch-1 crops, ImageNet OSNet cross-epoch rank-1
0.083 against 0.746 same-epoch; HSV 0.083 against 0.845. The HSV histogram
ranked the other-outfit intruder *worse than chance* (median 157 of ~175),
OSNet at median 8.5, so OSNet carries some body-shape signal.

### 1.3 How often it happens in a 24–72 h intruder scenario

There is no published rate of outfit change for hostile actors, so this is
**[INF]**, built from the scenario rather than from data:

| Time gap between sightings | Outfit change likelihood | Why |
|---|---|---|
| Same visit, < 1 h | Low unless deliberate | Normal people do not change; a deliberate change (reversible jacket, hood up, layer removed) is an evasion technique (`50` §3.3, `blindspot_change`) |
| Same day, hours apart | Moderate | Outer layer on/off with weather, hi-vis added as a pretext (`50` §3.5) |
| Next day (24 h) | High | Most people wear different clothes on consecutive days; DeepChange was built because a 12-month collection shows this (§2) |
| 48–72 h (reconnaissance → attack) | Near certain for anyone careful | The attack visit is when the adversary most wants not to be linked to the reconnaissance visit |

So for the scenario that matters most to a defence site — link the person
who walked the fence on Monday to the person at the gate on Wednesday —
**cross-day matching is the normal case, and short-term ReID is the wrong
tool**. Within one visit, an outfit change is rare but is itself a signal.

---

## 2. Datasets and licences

Counts from the dataset paper where we opened it, otherwise from CAL's
Table 1 (a secondary source, marked). "Commercial ML" is our reading of the
licence text, not legal advice (`47` is the licence register).

| Dataset | Ids / images | Cameras, span | Protocol | Licence | Commercial ML |
|---|---|---|---|---|---|
| **PRCC** (Yang, Wu, Zheng, TPAMI 2019) | 221 / 33,698 [V] | 3 indoor cams; camera C is the changed-clothes view | SC (A↔B), CC (A↔C) | Request from authors [A] — page did not load | No [A] |
| **LTCC** (Qian et al., ACCV 2020) | 152 / 17,138 [V] (CAL tabulates 17,119), 478 outfits, ~5 per person; test 45 changers + 30 non-changers | 12 indoor cams, 2 months | general, CC | Request form [A] | No [A] |
| **Celeb-reID** (Huang et al., 2019) | 1,052 / 34,186 [V, repo README]; **-light** 590 / 10,842 | web celebrity photos, not CCTV | CC (most ids change clothes) | "research only … DO NOT … use it for commercial purpose" [V] | No |
| **DeepChange** (Xu et al., 2021) | 1,121 / 178,407 [V] | 17 outdoor surveillance cams, **12 months** | long-term (cross-day/month/season) | Non-commercial research only, signed access agreement [V] | No |
| **CCVID** (Gu et al., CVPR 2022, from FVG) | 226 / 347,833 boxes, 2,856 sequences [V] | 1 view, video | general, CC (video) | CC BY-NC-SA 4.0 [V, CAL paper text] | No |
| **LaST** (Shu et al., 2021) | 10,862 ids / > 228k images [V] | movies, many cities, day/night, seasons | long-term, large spatial span | "academic research use only" [V] | No |
| **MEVID** (Davila et al., WACV 2023) | 158 ids, 598 outfits (~4 per id), 8,092 tracklets, > 1.7M boxes [V] | **33 real surveillance cams, 17 locations, 73 days** | SC / different clothes / location splits | Built on **MEVA, CC BY 4.0** [V, mevadata.org]; hired actors under IRB [V]; MEVID annotation licence not stated in the repo [A] | **Probably yes** (attribution) — the only one |

Two things matter for us:

1. **MEVID is the benchmark closest to our problem** (real multi-camera
   CCTV, weeks apart, several outfits, consenting actors) **and the only one
   whose licence does not forbid commercial ML.** It should be the real-data
   check in H29, and it belongs in `47` and `~/data/assets/index.json`
   after the annotation licence is confirmed with Kitware.
2. PRCC and LTCC are the benchmarks everyone quotes, and they are small (221
   and 152 identities), indoor, and short-span. Treat them as comparison
   points, not evidence for a perimeter.

---

## 3. State of the art, checked against the papers

### 3.1 Image CC-ReID (PRCC, LTCC)

All rows below were read from **Table 1 of Ortho-ReID (arXiv 2606.11661, Jun
2026)**, which compiles them, and the CAL, CSCI and DIFFER rows were cross-checked
against each paper's own table [V].

| Method | Venue | PRCC CC | PRCC SC | LTCC CC | LTCC general |
|---|---|---|---|---|---|
| CAL | CVPR 22 | 55.2 / 55.8 | 100 / 99.8 | 40.1 / 18.0 | 74.2 / 40.8 |
| AIM | CVPR 23 | 57.9 / 58.3 | 100 / 99.9 | 40.6 / 19.1 | 76.3 / 41.1 |
| CGPG (silhouette) | CVPR 24 | 61.8 / 58.3 | 100 / 99.6 | 46.2 / 22.9 | 77.2 / 42.9 |
| MADE (text) | TMM 24 | 64.3 / 59.1 | 100 / 98.6 | 47.4 / 24.4 | 84.2 / 48.2 |
| CSCI (RGB only, colour token) | ICCV 25 | 66.2 / 61.3 | 100 / 99.9 | 47.8 / 24.4 | 82.6 / 48.0 |
| DIFFER (text-guided disentangling) | CVPR 25 | 68.5 / 64.7 | 99.9 / 99.5 | 58.2 / 31.6 † | 85.0 / 52.8 |
| **Ortho-ReID** (low-rank orthogonal subspaces) | arXiv Jun 2026 | **74.4 / 70.2** | 100 / 99.0 | 56.1 / 30.2 | 85.4 / 52.0 |

† Ortho-ReID's footnote: DIFFER's LTCC result comes with an unusually high
baseline (54.6 vs 45.9 for MADE and 44.9 for CSCI under the same settings), which
suggests implementation differences [V]. So the best **uncontested** LTCC CC is
~56 rank-1 / ~30 mAP.

Other checks:

* **DLCR** (diffusion data expansion, arXiv 2411.07205) [V]: PRCC CC
  **66.5 / 63.0**, "+11.3 / +7.2" over the CAL baseline it was bolted onto.
  The largest single lever is *generating more outfits per identity*, which
  is exactly what a simulator's wardrobe does.
* **MIPL** (arXiv 2411.00330) [V, abstract]: "LTCC 74.8 %" rank-1. That is
  indistinguishable from the *general* LTCC numbers above (CAL 74.2), and the
  abstract does not say which protocol. `54` §3.1 quoted it as the most
  recent absolute LTCC number; **do not quote it as a CC score** until the
  table is read. Correction for `54`.
* **Non-surveillance sets** [V, Ortho-ReID Table 2]: Celeb-reID-light
  79.1 / 59.0; LaST 84.3 / 53.5. Ortho-ReID's text calls LaST "228K
  identities"; the LaST paper says 10,862 identities and 228k *images*.

(CAL 2022) to ~26 points (Ortho-ReID 2026); on LTCC CC rank-1 is still ~56 %
and mAP ~30 %. Successive rows gain 1.9–5.9 PRCC CC rank-1 points each, and generative
outfit augmentation (+11.3 on PRCC) is the biggest single lever.

### 3.2 Video and in-the-wild

* **CCVID** [V, CAL Table 5]: CAL general 82.6 / 81.3, **CC 81.7 / 79.6**;
  GaitSet (silhouettes) CC 71.0 / 62.1. CCVID is one view with frontal faces,
  so the face does most of the work, and its numbers are the most optimistic.
* **MEVID** [V, MEVID Tables]: CAL overall 52.5 / 27.1; **same clothes 56.6
  / 39.0; different clothes 3.5 / 4.3**; different locations 35.0 / 22.2.
  This is the number to remember: **surveillance-range CC-ReID is
  essentially unsolved by appearance.**
* **DeepChange** [V, Table 5]: the best baseline in the dataset paper
  (ViT-B/16, RGB + grayscale) is 48.0 / 15.2 over a 12-month span.

### 3.3 Gait under clothing change

From **DeepGaitV2 (Fan et al., arXiv 2303.03301)** Table 4 [V]:

| Model | Gait3D R-1 / mAP | GREW R-1 |
|---|---|---|
| GaitSet (2019) | 36.7 / 30.0 | 46.3 |
| GaitBase (CVPR 23, OpenGait) | 64.6 / – | 60.1 |
| DeepGaitV2-P3D (11.1 M params) | 74.4 / 65.8 | 77.7 |
| DeepGaitV2-3D (27.5 M) | 72.8 / 63.9 | **79.4** |
| SwinGait-3D | **75.0** / 67.2 | 79.3 |

and, the part people forget, the **SUSTech1K attribute split** [V, Table 5]:
GaitBase Normal 81.5 → **Clothing 49.6**, Night **25.9**; DeepGaitV2-P3D
Normal 83.5 → Clothing 46.3, Night 27.3. **Gait is not clothes-invariant**:
silhouettes change with a long coat or a bulky jacket, and at night the
silhouette itself degrades. Gait is a strong *independent* cue, not a
solution. (`68` Q5 said "GREW 79–86 % R1"; the 86 is rank-10 of
DeepGaitV2-2D. Use **GREW rank-1 77.7–79.4**.)

---

## 4. Method families

| Family | Idea | Evidence | Fits a perimeter? |
|---|---|---|---|
| **Adversarial / disentangling on RGB** (CAL, AIM, CSCI, Ortho-ReID) | Penalise the embedding for predicting the clothes label | PRCC CC 55 → 74 (§3.1) | Partly: needs clothes labels to train, and half the gain is the head (CAL Table 6) |
| **Shape / silhouette / pose / 3D** (FSAM, 3DSL, CGPG, CVSL) | Add a body-shape stream from masks, keypoints, SMPL | CGPG PRCC CC 61.8 | Yes in principle; silhouettes are noisy at < 100 px and under occlusion |
| **Gait** (GaitSet, GaitBase, DeepGaitV2, SwinGait) | Temporal silhouette sequence | GREW R-1 ~79; drops to ~46–50 under clothing, ~26 at night (§3.3) | Yes for walking in the open with ≥ 2 gait cycles; not for someone standing |
| **Face-assisted** | Use the face when resolvable | CCVID CC 81.7 is face-rich; PRCC body-only 24.5 | Rarely at perimeter standoff; and under EU AI Act Art 5/UK DPA it is remote biometric identification — a governance decision, not a model choice (`44`) |
| **Soft biometrics** (height, build, limb ratios) | Metric measurements from a calibrated camera | Our batch_v8 gate: rendered height within 2 cm of truth (0 beyond 2 cm) [V, `42`]; real single-camera height error is several cm and depends on calibration and pose [A] | **Yes** — cheap, clothes-invariant apart from shoes/hats, and a strong *eliminator* |
| **Text / CLIP / VLM prompts** (MADE, DIFFER, Instruct-ReID, MIPL) | Use language descriptions to separate biometric from clothing attributes | DIFFER PRCC 68.5; Ortho-ReID 74.4 | Research-grade; costs a VLM pass in training, not at inference |
| **Generative outfit augmentation** (DLCR, try-on 2512.07126) | Synthesise more outfits per identity | DLCR PRCC +11.3 | Yes, and this is the simulator's natural role |
| **Tracklet / space-time reasoning** | Link tracks by continuity, transit time and entry/exit portals, not only by look | MEVID: different *location* costs much less than different *clothes* (35.0 vs 3.5 R-1) | **Yes** — the cue an intruder cannot change without being seen changing it |
| **Camera-topology priors** | Learn which camera pairs connect and with what transit-time distribution | Classical (Javed et al. 2003 [A]); MEVID's authors suggest learning transit patterns [V] | **Yes** — cheap, site-specific, explainable |

---

## 5. What a defence-site system should actually do

**Design sentence:** *link tracks with calibrated height, gait and
time-topology feasibility first; use appearance only inside an appearance
epoch; and treat a clothing change as an event to flag, not a failure to
hide.*

In practice:

1. **Within an epoch, appearance is fine.** Same visit, same clothes: OSNet
   or CLIP-ReID plus the tracker's own continuity. This is the short-term
   problem where Market numbers apply.
2. **Across a possible change, gate before you match.** Two tracks are
   candidates only if (a) transit time between the exit camera and entry
   camera is feasible under the site topology prior, (b) calibrated heights
   agree within the measurement error (e.g. |Δh| < 4–6 cm [INF]), and (c)
   gait embeddings agree when both tracks have ≥ 2 cycles of walking.
   Appearance similarity is then a *weak* extra feature, not the decision.
3. **Detect the change itself.** A track that disappears into a blind spot
   and a height- and gait-compatible track with a new outfit appears within
   the feasible transit window is a *clothing-change event*. That is more
   useful to an operator than a silent re-link: it is behaviour
   (`blindspot_change` in the evasion catalogue).
4. **Output a ranked candidate list to a human, not a verdict.** Cross-day
   linking is an investigative aid ("these three sightings may be the same
   person; here is why"), with the cue breakdown shown. This also keeps the
   system on the right side of `44` (no automated identification decision)
   and fits `59`'s audit trail.
5. **Size it for the edge.** Height and topology cost nothing per crop; gait
   needs a silhouette sequence (DeepGaitV2-P3D is 11.1 M params, 2.9 GFLOPs
   **per silhouette frame, backbone only** [V, footnote 2] — ~90 GFLOPs for a
   30-frame sequence [INF]) and should run only on tracks that crossed a blind spot
   or a day boundary, not on every track.

### 5.1 What SurvSim lets you measure that real data cannot

Recorded today (`survsim/core/appearance.py`, `survsim/director/world.py`,
`survsim/gt/writers.py`) [V, code read]:

* `identities.parquet` has **one row per `(uid, epoch)`** with `t_from`,
  `t_to`, `appearance_hash`, `face_visible`, `dominant_colour`, `gait_style`,
  the full `outfit` JSON, and the soft biometrics `height_m`, `shoulder_w`,
  `bmi_class`, `skin_tone`, `age_band` plus flattened gait-signature columns.
* `world.parquet` carries `appearance_epoch` on every per-frame row, so any
  crop joins to its epoch.
* An epoch starts only when the appearance hash actually changes
  (`AppearanceState.apply`), so the label is "what happened", not "what was
  planned" (principle 1).

That enables measurements that no real dataset gives:

| Measurement | Real data | SurvSim |
|---|---|---|
| Exact epoch boundary (when the jacket came off) | Never known; annotators see only the result | `t_to`/`t_from` to the frame |
| Height error of the site's own cameras | Needs a surveyed person | GT `height_m` vs. estimate per camera, per range [V: gate 0 beyond 2 cm on batch_v8] |
| Controlled change: same body, only the jacket differs | Not collectable at scale | One delta per epoch, all else fixed |
| Hard negatives: two ids in the **same outfit** | Rare | Assign the same outfit JSON to different uids (breaks the clothing shortcut in training and tests it in evaluation) |
| Which cue did the linking | Unknown | Score height-only, gait-only, appearance-only and fused arms on the same queries |
| Evasion cost | Needs red-team actors | Evasion techniques from `50` with benign twins (principle 3) |
| Operational metric | Rank-1 on crops | False links per camera-day and missed links per changer, against an operator budget (principle 4) |

---

## 6. Failure modes, evasion and honest limits

From `50`'s taxonomy [V, `survsim/director/evasion.py`]:

| Technique | Cue it attacks | What survives |
|---|---|---|
| `reversible_jacket`, `layered_removal`, `bulky_coat` | Appearance; bulky coat also shape and gait silhouette | Height; transit time; gait partly (SUSTech1K clothing split ~46–50) |
| `bag_front`, `bag_swap` | Silhouette, carrying gait | Height, topology |
| `hi_vis_worker`, `courier`, `security_uniform` | Appearance and *operator expectation* | Physical cues; the behaviour is the tell (`19`, `62`) |
| `blindspot_change` | Tracker continuity | The disappearance itself; `survsim rig` reports blind spots |
| `fake_limp` | Gait | Height, appearance within epoch; recorded separately in `soft_biometrics` because the evader controls it |
| Shoe lifts / hat | Height (a few cm) | Gait, topology; widen the height gate |
| Different day, different route | Topology prior (transit windows reset overnight) | Height, gait only; this is the hardest case |

Limits we should say out loud:

* **Cross-day, cross-route, dressed differently, standing still** is not
  solvable with current methods at CCTV range. MEVID's 3.5 % rank-1 is the
  honest number. Height narrows the population; it does not identify.
* **Height discriminates weakly.** Adult stature has a spread of roughly
  7 cm within a sex [A], so a ±5 cm gate keeps a large fraction of a
  population. It is a filter that removes most wrong candidates, not a
  matcher.
* **Gait needs walking.** Loiterers, crouchers and people in vehicles give
  no usable gait.
* **SurvSim cannot yet render the change.** The MetaHuman wardrobe is
  engine-blocked (CLAUDE.md), and MetaHuman renders are barred from ML
  testing anyway. The CC0 route has **16 Quaternius bodies**, so H29's 460
  identities (§7) would reuse each body ~29 times. Body shape would then
  be a *confounder* (two "identities" sharing a mesh) unless each identity
  gets its own scale and morph. That must be fixed before any shape or
  height result means anything.
* **Our gait result is by construction.** H10 v2's gait 1.000 is a simulated
  measurement of epoch-invariant parameters; H31 must extract gait from
  pixels before gait is a claim.

---

## 7. H29 design detail (supersedes the sketch in `66`)

**Question.** Does training with SurvSim's appearance truth (identity across
epochs, plus same-outfit hard negatives) make an embedding hold up across a
clothing change, on synthetic held-out changers **and** on real MEVID?

**Why the old sketch was not enough.** "≥ 100 ids, ≥ 10 changers" gives an
id-level bootstrap over 10 people. With per-changer rank-1 sd around 0.3
[INF, from H10 v2's spread], the standard error of the mean over 10 changers
is ~0.095, so a 2× contrast from a 0.10 baseline (+0.10) is inside the
noise. **About 40 held-out changers** gives SE ~0.047 for each arm; a paired
comparison on the same queries is tighter still.

**Data (render, CC0 bodies only, licence-clean).**

| Split | Identities | Changers | Epochs per changer | Crop quota |
|---|---|---|---|---|
| Train | 260 | 130 (50 %) | 2–4 | ≥ 8 crops per (uid, epoch, camera), ≥ 48 px |
| Held-out test | 100 | 40 | 2–3 | same |
| Distractors (test gallery only) | 100 | 0 | 1 | same |

* **Identity = body × scale × morph × gait style**, not outfit. Scale each
  of the 16 CC0 bodies over 1.55–1.95 m and vary width morphs so no two
  identities share `(mesh, height_m ± 2 cm, shoulder_w)`. Record all three.
* **Same-outfit hard negatives:** ≥ 20 % of test distractors wear an outfit
  that some changer wears in another epoch.
* **Changes happen out of view** (blind spot or a scene cut), to match the
  CC protocol, plus a small set **in view** for the change-event detector.
* **Cameras:** ≥ 4 per site, 2 sites, day only first (night is H32's job).

**Protocols** (mirror PRCC/LTCC so numbers are comparable in kind):

1. **SC** — gallery = same `(uid, epoch)` on other cameras.
2. **CC** — gallery excludes every crop of the query's own epoch (the LTCC
   rule); primary metric.
3. **General** — both allowed.
4. **Real check:** MEVID "different clothes" split, where CAL scores 3.5 /
   4.3 [V]. Pre-register "no measurable transfer" if the CI spans 0 (as H20
   did on MOT20).

**Arms.** (a) ImageNet OSNet; (b) HSV; (c) OSNet fine-tuned with identity
labels that ignore epochs (the usual short-term recipe: each epoch its own
id); (d) OSNet fine-tuned with identity across epochs; (e) (d) + CAL loss
with the outfit hash as the clothes label; (f) height-only (GT height plus
realistic noise); (g) gait signature; (h) fusion of (e)+(f)+(g) by
score-level sum. 3 training seeds each.

**Metrics.** CC mAP and rank-1 on held-out changers, id-level bootstrap
(10k resamples); SC and general reported alongside; for the fusion arm,
**false links per 100 queries at 90 % recall** — the operational metric.

**Hypotheses** (pre-register before rendering).
* H29a: (d) CC rank-1 ≥ 2× (c) on held-out synthetic changers.
* H29b: (e) CC mAP on MEVID different-clothes > (a) with CI excluding 0.
* H29c: (h) beats (e) on synthetic CC rank-1 — the cue-fusion claim.

**Stopping.** Fixed: 3 seeds, no tuning on the test split (tune on a
20-id slice of train).

**Cost.** Render: 460 identities × ≥ 2 epochs × ~8 crops × 4 cameras is
~30k crops, roughly 1.5 editor-days on the 8 GB GPU at 720p; training ~3 h
per arm-set. **Blockers:** per-identity scale/morph on CC0 bodies (a
`tools/render_run.py` change), MEVID annotation licence confirmation.

**Decision.** If H29a holds and H29b is null, appearance truth is an
*evaluation* asset (measure the collapse, test fusion) rather than a training
asset — the same verdict H20 reached. If H29b holds, SurvSim's epochs are a
product feature for training.

---


**1. "Re-identify the intruder after he changes his jacket."**
Appearance is not identity. On PRCC CAL drops from 100 to 55 rank-1; the
best 2026 method (Ortho-ReID) reaches 74.4. On MEVID, real surveillance
cameras, CAL is 56.6 same-clothes and **3.5 different-clothes**. So I would
not promise appearance matching across a change. I'd gate candidates by
calibrated height and transit-time feasibility, add gait when they walk,
flag the change as an event, and give the operator a ranked list.
*Red flag:* quoting Market-1501 or PRCC SC numbers.

**2. "Why does PRCC look so much better than MEVID?"**
PRCC is 3 indoor cameras, 221 people, and faces are visible; CAL's own
body-only ablation drops PRCC CC from 55.2 to 24.5. MEVID is 33 cameras at
range across 73 days. *Red flag:* treating benchmark CC scores as
deployable.

**3. "What's the state of the art?"**
PRCC CC 74.4 / 70.2 (Ortho-ReID, Jun 2026 preprint, not yet peer-reviewed);
DIFFER 68.5 (CVPR 25); LTCC CC ~56 / 30. Biggest single lever: generating more outfits (DLCR +11.3 on
PRCC). *Red flag:* the 74.8 % LTCC MIPL figure quoted as clothes-changing.

**4. "Isn't gait the answer?"**
It's the best independent cue: GREW rank-1 ~79 (DeepGaitV2), but on
SUSTech1K clothing drops it from ~82 to ~46–50 and night to ~26. It needs
two gait cycles of walking. *Red flag:* "gait is clothes-invariant".

**5. "How good is height?"**
A filter, not an identifier. In SurvSim GT heights are exact and our render
gate checks rendered heights to 2 cm; on a real calibrated camera expect
several cm of error [A]. Adult stature has an SD of roughly 7 cm within a sex
[A], so a ±5 cm gate still keeps ~40 % of same-sex candidates (|Δ| < 5 cm for two people drawn at SD 7 cm: SD of Δ ≈ 9.9 cm) [INF]:
it removes wrong candidates rather than confirming the right one.
*Red flag:* claiming height identifies people.

**6. "Which dataset would you use commercially?"**
MEVID: it's built on MEVA, CC BY 4.0, consenting hired actors. PRCC,
LTCC, DeepChange, LaST, Celeb-reID and CCVID are all non-commercial or
academic-only. I'd still confirm the MEVID annotation licence with Kitware.
*Red flag:* training a product on DeepChange.

**7. "What does your simulator add here?"**
Exact epoch boundaries, per-identity soft biometrics, same-outfit hard
negatives and controlled single-variable changes, so I can report which cue
made each link and the false links per camera-day. H20 showed synthetic ids
didn't transfer at 15 ids (`32` §H20); H29 is designed with 360 train+test
ids plus 100 distractors, 40 held-out changers and MEVID as the real check. *Red flag:* claiming H10 v2's one
changer as a result.

**8. "How would you detect the change itself?"**
Track ends near a blind spot, and a height- and gait-compatible track with a
new appearance hash starts inside the feasible transit window. Raise it as a
behaviour event with the evidence attached. *Red flag:* silently re-linking
and losing the fact that someone changed.

**9. "How do you stop the model learning clothes?"**
Label identity across outfits, add a clothes-adversarial loss (CAL) with the
outfit as the clothes label, and put same-outfit different-person pairs in
every batch. The simulator gives the outfit label for free. *Red flag:*
"more data" with no mechanism.

**10. "Legal issues?"**
Cross-day person linking from face or gait edges into remote biometric
identification: restricted by the EU AI Act and UK data protection. Keep a
human decision, log the cue breakdown, and scope retention (`44`, `59`).
*Red flag:* auto-alerting on a gait match to a watch-list.

---

## 9. Sources (all fetched 2026-09-27)

* CAL, CCVID: Gu et al., CVPR 2022 — https://arxiv.org/abs/2204.06890 (Tables 1, 2, 5, 6)
* PRCC: Yang, Wu, Zheng, TPAMI 2019 — https://arxiv.org/abs/2002.02295 ; http://www.isee-ai.cn/~yangqize/clothing.html (did not load)
* LTCC: Qian et al., ACCV 2020 — https://arxiv.org/abs/2005.12633
* Celeb-reID — https://github.com/Huang-3/Celeb-reID
* DeepChange — https://arxiv.org/abs/2105.14685 ; licence https://github.com/PengBoXiangShang/deepchange
* LaST — https://arxiv.org/abs/2105.15076 ; licence https://github.com/shuxjweb/last
* MEVID — https://arxiv.org/abs/2211.04656 ; https://github.com/Kitware/MEVID ; MEVA licence https://mevadata.org/ and https://mevadata.org/resources/MEVA-data-license.txt
* Ortho-ReID (Jun 2026) — https://arxiv.org/abs/2606.11661 (Tables 1–2)
* DIFFER (CVPR 2025) — https://arxiv.org/abs/2503.22912
* CSCI (ICCV 2025) — https://arxiv.org/abs/2507.07230
* DLCR — https://arxiv.org/abs/2411.07205
* MIPL — https://arxiv.org/abs/2411.00330 (abstract only)
* DeepGaitV2 / SwinGait — https://arxiv.org/abs/2303.03301 (Tables 4, 5)
* OpenGait / GaitBase — https://arxiv.org/abs/2211.06597
* SurvSim code: `survsim/core/appearance.py`, `survsim/director/world.py`, `survsim/gt/writers.py`, `survsim/director/evasion.py`; experiments `32` §H4, §H10 v2, §H20.
