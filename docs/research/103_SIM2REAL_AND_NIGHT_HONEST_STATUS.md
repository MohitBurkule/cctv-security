# 103 · Sim-to-real tracking/ReID and night/IR: the honest status

`FACTS_VERIFIED.md`** (the H-number names the row). Literature numbers are marked **[LIT]**
and carry the URL that FACTS records. "Accessed" is the date the FACTS row was fetched
(2026-09 audit rounds). The web search budget ran out for this session, so no new sources were
fetched today. Anything I could not re-verify is marked **[UNVERIFIED]**.

## 1 · What we measured vs what is published

### 1a. Tracking and ReID transfer

| Question | SurvSim (measured, FACTS) | Published [LIT] | Comparable? |
|---|---|---|---|
| Is our scorer right? | M1: `evaluate_mot` = reference TrackEval, abs Δ ≤ 1e-15 on HOTA/DetA/AssA/IDF1/IDSW (MOT20 subset, batch_v8, edge cases) | TrackEval is the MOTChallenge reference | Yes. This is a check that the scorer is correct, not evidence of transfer |
| Reference tracker on real footage | MOT20 subset HOTA 0.443, IDF1 0.559, MOTA 0.466. MOT20-02 ByteTrack AssA 0.5060 / HOTA 0.5268 | ByteTrack MOT20 HOTA 61.3 on the full test set ([LIT] github.com/ifzhang/ByteTrack) | No. Ours is a subset, with a zero-shot COCO yolov8n and no MOT20 training |
| Does synthetic *data* help real tracking? | H17 (pre-parity scorer, unequal steps): HOTA +0.0103, all of it via DetA; AssA −0.0051 n.s. H26/H51: equal-step detector gain +0.004–0.005 AP (H51 Holm p 0.0039) at one site | MOTSynth like-for-like Tracktor 45.0/51.2 vs real 43.5/49.6 MOTA/IDF1 ([LIT] arxiv.org/html/2108.09518) | Same direction: small detection gain, association gain not shown |
| Does an appearance *model* help association? | H24 w=1: ΔAssA MOT20-02 +0.0139, batch_v8 +0.0194 (bar +0.02 not met). H46b: day argmax w=16 +0.0613, MOT20-02 argmax w=8 +0.0486. **Cross-set:** w* from day → MOT20-02 held-out +0.0479; w* from MOT20-02 → day +0.0570. Cost: MOT20-02 ΔIDSW +15.80 at w=8, +33.4 at w=16 (CIs exclude 0). Shipped default stays w=1 | Trackers with ReID: StrongSORT++ MOT20 HOTA 62.6 ([LIT] arxiv.org/pdf/2202.13514); BoT-SORT-ReID MOT20 HOTA 63.3 ([LIT] github.com/NirAharon/BoT-SORT). No with/without-ReID delta quoted | **Our one real transfer result:** a design choice tuned on renders held on one real sequence (MOT20-02, 5 checkpoints) |
| Does synthetic ReID *training* transfer? | H20: 15 train ids. Synthetic cross-camera mAP +0.324, but MOT20 cross-time +0.021 [−0.047, +0.097], **no measurable effect** | UnrealPerson ~3,000 ids; ClonedPerson 5,621 ids, clothing realism 55.6 → 84.5 R1 on Market ([LIT] arxiv.org/html/2012.04268, arxiv.org/html/2204.02611) | Direction only. The limit is our identity count (15 vs thousands) |
| Is the synthetic crowd like the real one? | MOT20 vs batch_v8: 123.5 vs 5.4 people/frame; visibility 0.572 vs 0.915; box aspect ratio 1.138 | MOT20 ~127/frame, peak 246 ([LIT] arxiv.org/pdf/2003.09003) | This gap is why render HOTA ≠ real HOTA |

### 1b. Night / IR

| Question | SurvSim (measured, FACTS) | Published [LIT] | Status |
|---|---|---|---|
| Do renders look like real night? | H32a vs LLVIP: raw render 2/13 vis, 0/13 IR on hold-out. Tuned profiles 9/13 → **2/13** (lowlight) and 10/13 → **3/13** (thermal) on hold-out: **overfit** | LLVIP has 15,488 vis–IR pairs ([LIT] arxiv.org/abs/2108.10831) | Not met |
| Why? | Raw "night" renders are not dark: luma 90 vs a real median 34 (`69` §7 and CLAUDE.md; not a FACTS row) | — | Known cause, not yet fixed |
| Night detection penalty | H32b branch B3: **no profile is in band, so no recall number estimates the night penalty.** Recalls are sensor-model sensitivities only: raw 0.938, NIR Δ −0.565, lowlight Δ −0.835, thermal Δ −0.470 (optimistic: people are painted hot from the GT mask) | NightOwls, 279k frames ([LIT] robots.ox.ac.uk/~vgg/publications/2018/Neumann18b/) | Unmeasured |
| Night association | H46b night arm at w=16: ΔAssA +0.0470 [−0.0046, +0.1337]. The CI spans 0 | — | Not met (close) |
| Real thermal hardware | — | FLIR FC-AI 640×512, <25 mK ([LIT] flir.com/products/fc-series-ai/). FLIR ADAS v2 has 26,442 annotated frames ([LIT] oem.flir.com/solutions/automotive/adas-dataset-form/) | Context |
| H36 full LLVIP fit | Not run. Needs sign-off for the ~3.5 GB download | — | Blocked |

**Data licences.** MOT17/MOT20 are CC BY-NC-SA 3.0 (FACTS, secondary source arxiv.org/pdf/2306.09613).
LLVIP is non-commercial: we use it to measure, never to train or ship (`docs/11`). Our renders
are CC0 (batch_v8 `commercial_ml_ok`). KAIST multispectral and FLIR ADAS licence terms:
**[UNVERIFIED] today.** Read the licence page before any use. Do not quote either as commercial-OK.

## 2 · The honest six-line answers

**"How do you know your tracker numbers transfer?"**
1. I don't claim render HOTA transfers. The crowds differ: 5.4 people/frame vs MOT20's 123.5.
2. What I verify is the *scorer*: it matches reference TrackEval to 1e-15 (M1).
3. What transferred is a *decision*. The appearance weight chosen on renders (w=16) lifts MOT20-02 AssA by +0.0479 held-out; the reverse (w=8 chosen on MOT20-02) gives +0.0570 on day renders (H46b).
4. It has a cost: MOT20-02 ID switches rise by +15.80 at w=8 and +33.4 at w=16. So the shipped default stays w=1 until a real-site check.
5. Synthetic *data* helps detection slightly (+0.004–0.005 AP at equal steps, H51). No association gain was shown (H17, pre-parity scorer). This matches MOTSynth [LIT].
6. It is shown on one real sequence from a non-commercial set (MOT20-02). The next proof is a commercial-OK real site.
7. The *whole* tracker config (24 ByteTrack settings, H71) is inconclusive, not a failure: on MOT20 the configs span only 0.0174 HOTA and the four sequences do not rank them consistently with each other, so there is nothing to match. w > 0 helps on both sides; the best level does not carry over (AUDIT_H71).
8. Leakage check (AUDIT_LEAKAGE): the detector trained only on MOT20-01 frames 1–60; lines 3–6 are scored on MOT20-02, a different view, so they are clean. H71 did score MOT20-01; without the 60 training frames it moves by 0.0010 HOTA and stays inconclusive. The night hold-out (H32a) shares one LLVIP scene with the tune frames, which can only flatter the fit, and the fit still fails.

**"What's your night performance?"**
1. Unmeasured, and I say so.

**Night (audited, one paragraph; H32, H32a/b, H32c, H32d, H3g):** Our night detection penalty is unmeasured: the profiles tuned to LLVIP overfit (2/13 and 3/13 in band on hold-out, H32a) and our renders are not dark (luma 90 vs a real median 34), so no recall drop we have is a night penalty (H32b branch B3; R47).
The shipped low-light profile is broken for detection, not a pessimistic estimate: on 60 night frames it takes YOLOv8n from 0.766 raw (449 render-visible GT, R79) to 0.0045, on people clearly visible in the raw render, while still brighter than real night (H32c, AUDIT_H32C; R78).
The cause is two redundant killers, not the whole chain (H32d, AUDIT_H32D): the noise stage alone erases people (AOI share 0.988) and crf 39 alone, on a 2×-upsampled 640×360 render, removes three quarters (0.744); removing both recovers 0.978 of the loss, either alone at most a fifth; exposure, blur, denoise and colour are minor (each ≤ 7 %, R80).
Those shares were registered on the 362-row mock-visibility GT and move ≤ 0.02 on the 449-row GT (AUDIT_H32D).
The output reads 2.21× the LLVIP hold-out noise (noise stage alone 3.3×), yet noise off is 30× below real, so the fix is less noise and a lower CRF, judged on hold-out; H32e, run: fitting only noise scale and CRF to LLVIP tuning frames keeps crf 39 (s 0.7); fitted recall 0.018 [0.005, 0.029] and the hard negative fails (2/13 in band, bar 7), so the decision is not met and raw minus fitted is not a night penalty.
The day stream shows the same stage coupling (H3g: 1.47× real noise; matched noise recovers about half the far loss but pushes blockiness out of band; R76).
LLVIP is non-commercial and only measures; a real night number needs owned night footage.

Every far-field/degrade number with its denominator, frames, conf and licence: `112_FAR_FIELD_AND_DEGRADE_NUMBERS.md`.

**Far-field, H3b → H3e (audited, one paragraph):** At a 640 input YOLOv8n is blind to far people (under 3 % far recall on all rows of CC0 renders; 6 % on ≥ 20 px rows) and a 1280 input recovers about half of them (49 % at ≥ 20 px); 320×240 tiles at 2× add another 19 points on the same CC0 renders (68 %) at 6–7× the compute, at conf 0.25 only, and far recall on the degraded stream is about 30 % (a lower bound, AUDIT_H3F). Plain NMS over tiles multiplies near-camera false positives; a tile-border merge rule fixes that on renders (133 near FPs vs 146 at 1280, far recall kept). On real MOT20 crowds the same rule still removes 80 % of the tile false positives but deletes real people — recall −0.118 against plain NMS, and −0.079 even in the sparsest quarter of frames (about 41 people each) — so it must be gated on crowd density at a threshold we have not measured, and on dense real scenes we keep the 1280 full frame. (AUDIT_H3B, AUDIT_H3C, AUDIT_H3D, AUDIT_H3E; R72, R74)

**One-sentence versions.**
- *Transfer:* "I don't claim render scores transfer. One design decision did: the appearance weight chosen on renders lifts real MOT20-02 AssA by +0.0479 held-out, at a cost in ID switches, with a scorer at TrackEval parity. That is one sequence, and it is non-commercial. Tuning the whole tracker config on renders was inconclusive on MOT20, because MOT20 itself gives the configs no stable order."
- *Night:* "Unmeasured. Our night profiles overfit LLVIP (2/13 and 3/13 on hold-out) and our renders aren't dark enough (luma 90), so no recall number we have estimates the night penalty."

## 3 · Next week's experiments

**Transfer (H-next-T).** Record 2–4 h of our own footage at one owned or consented site (2 cameras,
overlapping). Annotate about 20 min with commercial terms. The footage is our own, so the licence
path is clean. Pre-register the same thing as H46b: choose w on batch_v8, apply it to the new
site, and pass if held-out ΔAssA ≥ +0.02 with a CI excluding 0 and ΔIDSW ≤ 0. Also report render
HOTA and real HOTA side by side, with no claim that they should be equal. A failure retires the
line "design choices transfer".

**Night (H-next-N, which also serves as H36-lite).** (a) Fix the exposure of the render itself:
bring the luma median to about 34 before any degrade. Only then fit profiles, on a *split by scene*
from LLVIP (measurement only, NC). (b) For a penalty number, record owned night footage at the same
site, visible and, if hardware allows, thermal. Label about 500 boxes and report YOLOv8n recall at
h ≥ 40 for night vs day on real frames. That is the first real night-penalty estimate. KAIST and FLIR ADAS
come in only after their licence pages are read and recorded in `~/data/assets/index.json`.

## 4 · Eight probes (answers ≤ 5 lines)

1. **"Your HOTA 0.443 is far below ByteTrack's published MOT20 numbers."**
   Our HOTA is on a subset with a zero-shot COCO yolov8n and no MOT20 training. The published score
   is on the full test set with a trained detector. I use 0.443 as a fixed reference point to
   compare our own changes against, not as a leaderboard claim.
2. **"Why trust your HOTA implementation?"**
   M1 parity: it matches reference TrackEval to within 1e-15 on every metric. Before the fix it
   was off by −0.0086 HOTA, so we did find and fix a real discrepancy.
3. **"Synthetic data improved tracking?"**
   Only via detection. H17's HOTA gain is all DetA, and AssA is flat. H17 used the pre-parity
   scorer and unequal steps, so I quote the equal-step detector gain (H51) instead.
4. **"Why not just train ReID on your renders?"**
   H20 tried it: 15 identities, no measurable MOT20 effect. The literature needed thousands of ids
   and realistic clothing (ClonedPerson [LIT]). Our limit is identity count, and I say that.
5. **"Is w=8 or w=16 the right weight?"**
   Each held-out direction clears +0.02 AssA, but MOT20-02 ID switches rise (+15.80 at w=8, +33.4 at
   w=16). So w=1 stays the shipped default until a real-site check, and w=8 is the safer candidate.
6. **"What's your thermal recall?"**
   0.468 on renders, and it is optimistic: people are painted hot from the GT mask. It measures the
   detector's sensitivity to our sensor model, not a night estimate.
7. **"Why not train on LLVIP / MOT20?"**
   Both are non-commercial. We measure against them and never train or ship on them. The commercial
   path is owned footage plus our CC0 renders.
8. **"What would convince you night works?"**
   A real-footage night-vs-day recall gap on labelled owned frames, and render profiles that stay
   in band on a scene-split hold-out. Neither exists today. H36 is blocked on download sign-off.
