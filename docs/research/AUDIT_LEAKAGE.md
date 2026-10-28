# AUDIT_LEAKAGE — train/tune vs. score overlap on real footage

*Adversarial sweep, 2026-09-28, triggered by AUDIT_H71 item 6 (H71 scored MOT20-01, the h14b
detector's training sequence). No GPU/editor: configs, code and cached `out/` only. One recompute
(H71, CPU, cached detections + embeddings). Script: session scratchpad `h71_excl.py` (reproduces the
stored MOT20-01 row to 4 dp before excluding frames).*

## 1 · What real data trains or tunes anything

| Consumer | Real data used to fit/tune/select | Evidence |
|---|---|---|
| Detector fine-tunes H7, H14, h14b, H15, H16, H18, H19, H25, H26, H51, H52, H61 (all "real ×5" arms) | **MOT20-01 frames 1–60** (`frames: 60`, loop `range(1, frames+1)`), ×5 repeats. Checkpoint = `last.pt`; trainer val set is synthetic (`smoke_mock_night`) — no real frame selects a checkpoint | `survsim/experiments/detection.py` L149–159, L165–167; configs `h14b_dose_fixedlabels.yaml` L55–62, `h51_equal_steps.yaml` |
| H1 real arms | same MOT20-01 frames; `leaky_sets: [mot20_sub]` skips MOT20-01 scoring for them | `h1_sim2real.yaml` L12–13; `detection.py` L227 |
| INT8 PTQ calibration H38, H43/H43b–d | MOT20-01 frames **61–429, n = 100** ("1–60 are h14b training frames") | `h38_quant_export.yaml` L15–18; `h43_qat.yaml` L22–27 |
| QAT fine-tune H43b–d | the checkpoint's own yolo_data (MOT20-01 1–60 + synthetic) | `h43_qat.yaml` `data:` paths |
| `cctv_day_720p` degrade profile | tuned so render statistics land in bands from real MOT proxy frames (`~/data/real_cctv`, incl. `MOT20-01-raw.jpg`); swept on **batch_v1 `street_crowd_day` cam_02 renders, N = 20–60** | `survsim/sensors/degrade.py` L727–742; `docs/15` "Sequence codec batching, take 2" |
| `cctv_night_lowlight`, `cctv_thermal` (H32a) | first 15 sorted LLVIP frames per modality: `Test__19000{1–6}`, `Test__20000{2–7}`, **`Train_01000{1–3}`**; hold-out = **`Train_01000{4–13}`** | `night_profiles.py` `split_real` (sorted, `[:15]`/`[15:]`); `ls ~/data/real_cctv_night/llvip_{vis,ir}` |
| Tracker knobs | ByteTrack defaults not fit to MOT20 (docs/13 "no per-sequence tuning"); H9b fix evaluated on MOT20-01/02 and **rejected**; H46/H46b w argmax picked on the same arms that are then quoted | `docs/13_BASELINES.md` L59–60, L398–407, L670–700 |
| ReID | OSNet-ImageNet (torchreid ImageNet weights) and H20 synthetic fine-tune — no real ReID data | FACTS H20/H24 rows |
| Conformal / alarm thresholds (H33, H33b, H59, H62, H63b) | simulated worlds only (338/338 splits) — **not real footage, out of scope** | FACTS H33/H62 rows |
| Pretrained detectors (yolov8n, yolo11n, yolo26n COCO) | third-party; vendor-stated COCO — contains no MOT20/LLVIP frames [A], not verifiable in repo | `weights/`, `yolov8n.pt` |

MOT20-02 is a different camera view from MOT20-01 (median-of-4-frames grayscale correlation −0.09;
01↔03 +0.08, 01↔05 −0.20), so MOT20-01 training does not put MOT20-02's scene into the detector.

## 2 · Every real-footage score, classified

| # | Number (FACTS / docs/13) | Scored on | Overlap with §1 | Class |
|---|---|---|---|---|
| 1 | docs/13 MOT20 subset HOTA 0.443 / IDF1 0.559 / MOTA 0.466; det AP 0.348 / AP50 0.730 | MOT20-01 + -02, frames 1–300 | COCO zero-shot detector, default tracker — nothing fit to MOT20 | CLEAN |
| 2 | M1 TrackEval parity (|Δ| ≤ 1e-15) | MOT20 subset | scorer identity check, no model quality claim | CLEAN |
| 3 | docs/13 ReID row (OSNet-ImageNet, 105 ids) | MOT20 subset | ImageNet weights | CLEAN |
| 4 | H9a / H9b (pre-parity) | MOT20-01/02 + batch_v7 | yolov8n zero-shot; H9b fix rejected, not shipped | CLEAN |
| 5 | H1 / H2 / H6 / H13 | MOT20-02 (H1 real arms), MOT20 subset (synthetic-only arms) | leakage rule enforced in code; H13 uses 40 MOT20-02 frames as a statistics reference, not fitted | CLEAN |
| 6 | Dose family H7, H14, h14b, H15, H16, H25, H26, H51, H52, H61 (MOT20-02 AP@640) | MOT20-02 1–300 | trained on MOT20-01 1–60 only; `last.pt`; different view | CLEAN |
| 7 | Far-field H8 / H18 / H19 | MOT20-02 downscaled | same as 6 | CLEAN |
| 8 | H17 (dose → tracking, pre-parity) | MOT20-02 1–300 | h14 / h14b checkpoints (MOT20-01 1–60) | CLEAN |
| 9 | H24 MOT20-02 ΔAssA +0.0139 / AssA 0.5060 | MOT20-02 1–300 | h14b; w = 1 fixed a priori | CLEAN |
| 10 | H38, H43, H43b–d (INT8/QAT loss on MOT20-02) | MOT20-02 | calibration MOT20-01 61–429, disjoint from training (1–60) and from the score set | CLEAN |
| 11 | H11 night (MOT20-05) | MOT20-05 | yolov8n zero-shot / synthetic-only arms | CLEAN |
| 12 | H46 MOT20-02 ΔAssA +0.0338 at w = 4 | MOT20-02 | **selection on the scored set** (w argmax over the same 5 arms). Day-selected w is also 4, so the clean cross-set value is the same number | OVERLAP (tuning) — Δ 0 |
| 13 | H46b MOT20-02 ΔAssA +0.0486 at w = 8 | MOT20-02 | w = 8 chosen on MOT20-02 itself. Clean equivalent (w chosen on day = 16, applied to MOT20-02) **+0.0479** | OVERLAP (tuning) — Δ −0.0007 |
| 14 | **H71** ρ +0.0096, regret 0.0034, real range 0.0174, per-knob real Δs | MOT20-01/02/03/05 1–300 | **MOT20-01 frames 1–60 are the h14b `mix_300_s0` detector's training frames** | **OVERLAP (frames)** — see §3 |
| 15 | H32a hold-out 2/13 (vis) · 3/13 (IR) | LLVIP `Train_01000{4–13}` | frames disjoint, but the whole hold-out is LLVIP scene prefix `01` whose frames 1–3 are in the tune set (scene id inferred from file names [A]). Leak direction favours the fit; the fit still fails, so "overfit" stands | OVERLAP (scene) — conservative |
| 16 | H32a tune 9/13 · 10/13 | LLVIP first 15 | in-sample by design, labelled "tune" | OVERLAP (by design, disclosed) |
| 17 | Realism `cctv_day` 6/14 in band | 60 frames of batch_v1 `street_crowd_day` cam_02 | **same camera/frames the profile was swept on (N = 20–60) — in-sample**; and they are **UE renders**, not "real street frames" as FACTS said. Not recomputed (needs a held-out render camera; not a cached prediction) | OVERLAP (in-sample) |
| 18 | Third-party pretrained weights under every number | — | vendor training sets not verifiable from the repo | UNKNOWN |

**Counts: CLEAN 11 · OVERLAP 6 · UNKNOWN 1** (rows 12–17 overlap; H33/H59/H62/H63b are simulated, not real footage, and are excluded).

## 3 · Recompute: H71 without MOT20-01's training frames

Cached `out/experiments/h71/dets|emb/MOT20-01__MOT20-01.*`, all 24 configs re-tracked and TrackEval-scored
on MOT20-01 frames 61–300 (GT and ignore rows restricted to the same frames); other three sequences and
the render matrix from `results.json`; `analyse()` unchanged (2,000 bootstraps). Frames 1–300 reproduce
the stored MOT20-01 row exactly (max |Δ| 0.0).

| | stored (MOT20-01 1–300) | MOT20-01 61–300 | AUDIT_H71 (MOT20-01 dropped) |
|---|---|---|---|
| MOT20-01 grid-mean HOTA | 0.5033 | 0.5023 (Δ −0.0010) | — |
| Spearman ρ [95 % CI] | +0.0096 reported (+0.0348 from 4-dp arrays) [−0.4066, +0.4624] | **−0.0200 [−0.4136, +0.4670]** | −0.2222 [−0.4939, +0.3418] |
| regret | 0.0034 | 0.0040 | 0.0097 |
| real range over configs | 0.0174 | 0.0127 | 0.0155 |
| w real Δ CI | [0.0018, 0.0136] | [0.0018, 0.0123] | [0.0016, 0.0029] |
| match_iou real Δ CI | [−0.0053, 0.0092] | [−0.0020, 0.0092] | [0.0012, 0.0119] |
| max_lost_s real Δ CI / preferred / transfers | [−0.007, 0.0044] / 0.4 / no | [−0.003, 0.0044] / **2.0 / yes** | [0.0001, 0.0059] |
| high (hard negative) transfers | yes (prediction failed) | **no (prediction held)** | — |

**Reading.** The detector's own 60 training frames barely move MOT20-01's HOTA (−0.0010) — a 60-frame ×5,
6-epoch fine-tune does not memorise the tracker-level outcome. The H71 verdict is unchanged
(inconclusive, CI spans 0 either way). Two per-knob readings move: max_lost_s's preferred real level
now matches renders (as AUDIT_H71 found with the sequence dropped), and the `high` hard-negative
prediction flips from failed to held — both inside CIs that span 0, so neither is a finding. Frames
61–300 are still the training *sequence*; the fully clean version remains AUDIT_H71's 3-sequence
number.

## 4 · What changes
* FACTS: qualifiers on H71, H46, H46b, H32a and the realism row (own hunks).
* **R73** retires "6/14 … 60 real street frames" (they are the tuning camera's renders, in-sample).
* No headline is retired: every published real-footage *headline* (HOTA 0.443, H51 +0.004–0.005 AP,
  H46b +0.0479 held-out, H32a overfit) is either CLEAN or its overlap runs against the claim.

## Honest sentence
"We swept every real-footage number for train/test overlap: the detector only ever saw MOT20-01
frames 1–60, and every detection and association headline is scored on MOT20-02, a different view;
the one experiment that scored MOT20-01 (H71) barely moves when those frames are dropped and stays
inconclusive, and our night-profile hold-out shares a scene with the tuning frames, which only makes
its failure more convincing." (AUDIT_LEAKAGE)
