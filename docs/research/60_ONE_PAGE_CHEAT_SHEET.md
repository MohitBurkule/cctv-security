# 60 · One-page cheat sheet (last hour)

Every number is copied from `FACTS_VERIFIED.md` (a test enforces it); formulas from `55`; stories from `46`.
True at HEAD `e231a4a` (includes H22/H25/H26/H32/H33/H38/H39/H40/H40b/H42/H45/H47/H51/H53/H54/H56, M1 TrackEval parity; restructured by `77`, re-checked by `84`; section B rewritten post-H26 `e299c88`; AUDIT_NARRATIVE_POST_H26).
Arc: A built → B buys → C doesn't buy → D operator (the twin problem) → E law → F next → G drift → H the twin answer (fusion, PTZ).
Alarm tolerance is **30 s** unless stated (i-LIDS's own is 10 s; 5 s is FA coalescing).
All alarm numbers are **simulated** camera-hours (mock trajectories), never a real site.

Format: **number** (H-number) — *so what* — ✗ the retired/wrong version to never say, where one exists.

## 40 numbers
### A · What we built (and the yardsticks it is judged against)
1. batch_v8: 10,000 frames, gate 9/9, height 0 people beyond 2 cm, tightness IoU 0.876–0.932 (docs/12) — *every label is checked against pixels by an automated gate* — ✗ retired: "photoreal"
2. batch_v8 recall visible GT 0.696 / P 0.879 vs v7 0.664 / 0.819 — *same characters, so the gain is labels, not pixels*
3. HOTA 0.443 on the MOT20 subset, TrackEval-parity (M1) — *our evaluator now matches the reference to 1e-15* — ✗ retired: 0.545 (DetA bug); 0.434 is pre-parity
4. Anchors: ByteTrack MOT17 80.3 / 77.3 / 63.1 (MOTA/IDF1/HOTA); BoT-SORT 80.5 / 80.2 / 65.0 — *ReID+CMC buys IDF1, not MOTA*
5. MOT20 ~127 people/frame, peak 246 — *why zero-shot numbers on it are low*
6. CC0 cast costs −0.013 recall (0.652 vs 0.665); `commercial_ml_ok: true` — *licence compliance costs almost nothing*
7. Realism 6/14 image statistics in band by day (`docs/15`) — *renders are not CCTV-real; say it first* — ✗ retired: 12/14 (the tuning grid)
8. H39 auto-calibration from pedestrians: free-f fit 57.4 m RMSE < 20 m (bar 0.5 m) = not met; exact-calib floor 0.21 m — *f is unidentifiable from box heights; height MAE 0.077 m on the broken fit makes height consistency a trap metric* — ✗ do not quote datasheet-f 0.96 m as the H39 result (post hoc)

### B · What synthetic buys (post-H26: an evaluation instrument first, training data second; 52 §5b)
9. H26 + H51 (equal steps, 450, 10 paired seeds): **+0.0042** (100 renders) / **+0.0051** (300) over real-only 0.4911, **both Holm-significant (p 0.0039)**. H52/H61 (10 paired seeds each): the gain is labels on people — shuffled boxes erase it (+0.0077 gap), silhouette-masked frames with no box-shaped fill give nothing (−0.002 vs real-only); H52's apparent 'background' gain was the inpainted box fill. Duplicating real frames does nothing (−0.0011). 1,000 → −0.0003 (H26) — *small (~1 % rel.), one real site; real-only alone gains +0.0049 from H26's longer recipe (steps + warm-up + mosaic)* — ✗ retracted: h14b's unequal-step +0.0121 as the headline (R51)
10. H1 60 real frames 0.491 ± 0.003 (12 epochs) — *why 60 real frames matter more than any render count*
11. What it reliably buys is not AP: label truth (#1), hard-negative twins (#27), measured rule variance (#23: H21 2/5 seeds, H42 range 2.118) — forensic search (H37) mock slice ran and is **not met** (recall@10 pooled-vs-epoch diff +0.0004/-0.0118, two orders of magnitude below the 0.15 bar; a ceiling effect — relevant sets mean 2.67, max 9, all ≤10; CLIP arms still need renders, design-level only, H37b) — evasion now measured: H47 only crowd-blending cuts recall (−0.201 [−0.254, −0.154], clip CI); clothing/hood colour ≈ 0; wall-hugging beats geometry (−43 % ≥ 20 px frames), not the model
12. H24 vs H17: an appearance *model* lifts MOT20-02 ΔAssA +0.0139 (IDSW −5.6); synthetic *data* gives AssA −0.0051 n.s. (H17: unequal-step arms, pre-parity) — *the model helps association, the data does not* — ✗ retired: the H17 HOTA gain without "unequal steps, pre-parity" (R53)
13. H20: synthetic ReID fine-tune, synth cross-camera mAP +0.324 [+0.197, +0.493] — *in-domain only; limiter is 15 identities* — ✗ retired: H20's old identity count and mAP (R04/R10)
14. H63 uniformed intruder (simulated role/badge/RF): "looks like a guard → suppress" recall 0.027 [0.010, 0.047]; badge+RF corroboration mismatch recovers 0.745 [0.694, 0.794] — 96 % of the line-cross rule's own 0.775 ceiling — at 0.018 twin FA/cam-h [0.014, 0.024]; +5 m route prior drops to 0.198 — *never trust the uniform, trust the corroboration* — ✗ retired: an absolute ≥ 0.8 recall bar for (b) (registered above C's own ceiling; not re-scored)

### C · What synthetic does not buy
15. H1: zero-shot 0.276 → synthetic-only 0.152 ± 0.025 AP (MOT20-02 @640) — *synthetic-only hurts; lead with it* — ✗ retired: the two-seed and synth+real H1 variants (R21/R22)
16. H19: synthetic-only far fine-tune AP50 0.000 every seed, v6 and v8 (zero-shot 0.613); +60 real → 0.817 — *a domain effect real frames fix, not a renderer bug* — ✗ retired: "cause unresolved" (R24)
17. H20 on MOT20: +0.021 [−0.047, +0.097] = no measurable effect — *15 ids cannot train ReID; UnrealPerson used ~3,000*
18. H3: far recall 0.021 at 640, 0.405 at 1280, 0.629 tiled at 7× latency — *far people are a resolution problem, not a data problem*
19. H4: HSV histogram beats OSNet cross-camera mAP 0.219 vs 0.148 — *ImageNet ReID doesn't transfer to our crops* — ✗ retired: ReID 0.869 (leaky same-frame)
20. H32 night (LLVIP, measurement only): lowlight profile 9/13 tune → 2/13 hold-out; YOLOv8n raw 0.938 → NIR 0.373 / lowlight 0.103 / thermal 0.468 — *profiles overfit, so no night penalty can be quoted* — ✗ retired: "3/14 night" as a realism score; say 3/13 vis · 2/13 thermal vs LLVIP
21. Clothes-change ReID: CAL PRCC same-clothes 100 → 55.2 R1 changed; MEVID real CCTV 3.5; LTCC 40.1 R1 / 18.0 mAP — *appearance is not identity; our cue set is height + gait + topology (`70`)*

### D · What the operator sees
22. H12: 3,002 cam-h; loiter rules 4,500–87,000× over our assumed 0.001 FA/cam-h (dwell_60 4.55 … path_loiter_15 87.4) — *even with perfect perception*
23. Shipped rule A1 (H58 round 3): 2.915 FA/cam-h [2.854, 2.977], recall 0.825, precision 0.329 — *~2,900× over our assumed 0.001 budget (A=4, K=500, H=8; 28 §6 — not a field standard; external anchors: ≈ 1 nuisance alarm/zone/day for PIDS [A], NPCC 3 false police calls/12 months [V] — a different, post-verification quantity; `81`)*; H23: the same weights give 5.033 when the select fold picks θ 0.9 (7/10 folds) — *2.915 is one θ grid step from 5.033, so a challenger must win on ≥ 4/5 seeds (H21 C: 2/5)*; H42: pooled selection → 5.033 / 0.894, conformal → 2.10–2.22 / 0.778–0.783 — *H45 (operator sim, invented operator): 1 operator/40 cams → conformal θ 0.9629 ranked (0.621 realised @5 min; 0.617 at the H33b certified θ 0.963436, H45b — same rule); ≥ 2 operators → A1 θ 0.95 ranked; never pooled θ 0.9 — pooled's +0.069 model recall costs −0.08 realised (ranked, 1 op)* — ✗ retired: round-2 3.745 / 0.831; dwell_25 recall 0.900 (window-only; 0.367 actor-aware)
24. Kinematic-twin floor 1.008 FA/cam-h — *innocents that move exactly like loiterers; any track-only rule pays ≈ recall × 1.008*
25. H22 (invented operator, 1 per 40 cams, 120 alarms/h): A1/FIFO realised recall 0.511 @5 min (bar 0.495, inconclusive), 0.127 @30 s; ranked queue +0.262 @30 s — *the queue policy matters as much as the rule* — ✗ retired: "~79 wall-hours", "0 % bulk-acked"
26. H33 conformal θ (CRC): held-out FA ≤ 2.915 in 10/10 splits vs plug-in 6/10, recall −0.035 — *a certified threshold is cheap*; 0.001 is uncertifiable from 338 simulated worlds (floor ≥ 0.248) — ✗ retired: "338 sites"
    *Caveat:* CRC guarantee holds for a loss bounded by a B fixed in advance; H33 used the empirical max B (84–89, approximate); H33b fixes B = 123.5 FA/cam-h in advance, which makes the guarantee exact for the clipped loss min(L, 123.5) only — the ≤ 1-alarm-per-visitor cap behind it is not enforced (A1 alarms once per dwell *episode*; one visitor opened up to 21; AUDIT_H33B), so 123.5 is not an a-priori bound on L itself (no H12 world exceeds it: max 89). θ 0.9615–0.9642, held-out FA 2.216 ≤ 2.915 in 10/10 splits, recall −0.006 vs empirical B; at the certified θ 0.963436 the 1-operator ranked queue realises 0.617 @5 min, −0.004 [−0.017, +0.010] vs θ 0.962851 (H45b) (32 §H33b, §H45b).
26a. **Ship story (H33c/H45c):** 1 op/40 cams → A1 weights, conformal θ 0.9618, B=123.5 fixed + one-alarm-per-visitor cap, ranked queue: 2.20 FA/cam-h (~91/h), recall 0.789, realised 0.618 @5 min — the only exact-guarantee point (assumes GT ids; H59); ≥2 ops → A1 θ 0.95 ranked; never pooled.
27. H40/H40b line-cross (mock, **assumed** tracker noise): on fenced worlds with crossing intruders (H40b) the full rule gives **0** clean FA in 3,002 cam-h (≤ 0.001) but recall@10 **0.782** (not met); twins (patrol 0.389 + maintenance 0.099 FA/cam-h) ≈ 490× budget — *after fixing the generator, the twin, not the rule, is the product problem; the answer is #40* (H40 before the fix: 70.96 → 4.20, recall 0.100) — ✗ retired: "line-cross is solved"
28. i-LIDS 10 s alarm window, repeat alarms disregarded — *a late alarm is a false alarm*
29. ActEV RFA 0.1/min = 6 false alarms per camera-hour — *the only public benchmark scored at an operating point*
30. UCF-Crime frame AUC: Sultani 75.41, RTFM 84.30, VadCLIP 88.02 — *AUC in the 80s is still an unusable alarm rate*
31. DORI 25 / 62.5 / 125 / 250 px/m — *how installers specify cameras*
32. Orin NX 16 GB: 18× 1080p30 decode is a ceiling; ~10–12 cams/NX with detect + ReID ⇒ 4 NX for 40 cams — ✗ retired: the decode-only count as the budget
33. YOLO11n 39.5 / YOLO11s 47.0 COCO AP; 1.5 / 2.5 ms T4 TRT; OSNet-x1.0 2.2 M params, 0.98 GMACs — *the edge budget arithmetic starts here*; H38 (CPU, not Jetson): FP16 export loses 0.0000 AP, INT8 PTQ 0.0117 (mostly AP75) — *ship FP16 unless the latency is needed; no Jetson latency measured* — ✗ retired: "INT8 is free", "INT8 not faster than FP16" (R46/R54)

### E · What the law demands
34. MOT17/MOT20 CC BY-NC-SA 3.0 — *evaluation only; a company can't ship models trained on them*
35. MetaHuman terms forbid "train or test artificial intelligence" — *hence the CC0 cast (#6); batch_v4–v6 are engineering evidence only*
36. EU AI Act Annex III high-risk moved to 2 Dec 2027 (Reg 2026/1744); Bridges [2020] EWCA Civ 1058 — *identity features get the Bridges question*; UK GDPR Arts 22A–D (DUAA 2025 s.80, fully in force 5 Feb 2026: no meaningful human involvement ⇒ solely automated ⇒ safeguards) and JSP 936 Part 1 (13 Nov 2024) are in FACTS (Law) — *alarms go to a human; the system never takes an adverse action alone*

### F · What we'd do next (#37 records what closed; only the rest is "planned")
37. H24 done (not met at w=1): ImageNet OSNet in ByteTrack stage 1 → ΔAssA +0.0194 batch_v8 (bar +0.02), +0.0139 MOT20-02, fewer ID switches — *association, not detection*. H46b done: reference tracker is ByteTrack + OSNet-ImageNet at **w ≈ 8** (cross-validated; +0.05 AssA held-out) with the IDSW cost stated (day favourable, MOT20-02 +15.8) — *never appearance-only* (`app_only` ΔIDSW +162.0 MOT20-02) — ✗ never: "H24 met" without "H46b bar met at w=8". H26 fixed-step dose curve done (item 9; AUDIT_H26); H51 done (item 9; AUDIT_H51), H52 done (label-driven, item 9); H43 no-Jetson PTQ-calibration leg done, not met (Percentile AP75 recovery 0.415/0.424 < 0.50 bar, AUDIT_H43); QAT leg (H43b, then H43c's range-preserving export fix) also done, also not met (recovery 0.366→0.439, still < 0.50) — FP16 export is free, INT8 PTQ costs ~0.012 AP mostly AP75, Percentile calibration recovers ~41 %, QAT with range-preserving export ~44 %, neither reaches the 50 % bar; H43d (600 vs 150 QAT iterations) refuted "the recipe, not the export" — longer QAT does not help and hurts two checkpoints (pooled recovery fell to 0.374), so the residual loss is INT8 quantisation of this architecture; ship FP16, use INT8 only where AP75 doesn't drive the alarm; TensorRT-on-a-real-Orin (H43e) is still backlog
38. Real-site dwell/intruder tracks to replace mock trajectories; MetaHuman wardrobe is still [A] — *the two gaps every alarm and ReID claim above rests on* — ✗ never: "wardrobe works end to end"

### G · Drift in the field (H34, measured on renders)
39. H34 label-free drift: PSI/KS fire on 100 % of stationary 1-s windows (1,440/24 cam-h at one check per minute); calibrated mean-shift 6/12 shifts at 9.2/24 cam-h, blind to blur; embedding 0/12, ≤ 26.6 certifiable; ρ 0.61 — *uncalibrated image-stat monitors are useless per camera; inconclusive, no validated threshold* — ✗ never: "PSI > 0.2 is our drift alarm"

### H · The twin answer (closes the #27 problem; all sensors and PTZ timings simulated)
40. H53 fusion (simulated gate log + RF tag + PIDS, matched on true positions): twin FA 0.488 → 0.0047 FA/cam-h (99 % removed), recall@10 0.782 → 0.758 — *fusion is the twin answer; a tailgater defeats the gate log (recall 0.007); PIDS is the backstop (stolen tag 0.701)*; H54: est-position matching keeps 99.1 % (upper bound — no ID switches in the noise model), gate people counter catches the tailgater 0.685 [0.589, 0.778] at 96.3 % removal (H59: with GT identities; the actor-aware score drops to 0.10 under H24-calibrated ID-switch noise — a scoring artefact, not a fusion break; H62: position/time scoring recovers recall to 0.715 but false-credits bystanders 31.3 % at r=2 m, so it stays a diagnostic, not a replacement scorer) · H56 PTZ slew (mock, all PTZ timings assumed): missed second alarm 0.369 with 1 PTZ per 40 cams at 120/h vs 0.057 with 2; acquire@3s 0.901 ≤ 20 m, 0.727 > 30 m — *PTZ verification is contention-limited first; far-field cause untested* — ✗ never: "one PTZ verifies every alarm"

## 10 formulas
1. `IoU = |A∩B| / (|A|+|B|−|A∩B|)`
2. `P = TP/(TP+FP)`, `R = TP/(TP+FN)`
3. `MOTA = 1 − (FN+FP+IDSW)/GT`
4. `IDF1 = 2·IDTP/(|gtDet|+|prDet|)`
5. `HOTA_α = √(DetA_α·AssA_α)`, averaged over 19 α
6. `f_x = (W/2)/tan(HFOV/2)`; `px ≈ f_x·H/R` (1920 px, 70° → 1371 px)
7. `R_max = f_x / D` (DORI px/m)
8. Rule of three: 0 events in T ⇒ `λ < 3/T` (0.001 (assumed, 28 §6)/h needs ~3,000 cam-h)
9. Seeds: `n ≈ 15.7 σ²/Δ²` (σ 0.025, Δ 0.02 → 25/arm)
10. Operator load `U = C·B·t/3600`

## 6 stories (46)
1. **Black render** — `unreal.Rotator` is (roll, pitch, yaw); now a keyword test.
2. **HOTA was wrong** — 0.545 → 0.434, with regression tests; 0.443 after TrackEval parity (M1).
3. **Synthetic hurt** — 0.276 → 0.152 AP; reported; the additive gain is +0.004–0.005 at equal steps (H51, 10 paired seeds, Holm p 0.0039; ~1 % relative, one site) — h14b's +0.0121 compared unequal steps.
4. **Alarm budget at scale** — 3,002 cam-h, 4,500–87,000× over our assumed budget; it changed rule design.
5. **MOT20 licence** — CC BY-NC-SA ⇒ evaluation only; CC0 cast at −0.013 recall.
6. **batch_v8** — every label checked against pixels: gate 9/9, height 0 beyond 2 cm.

## 7 things not to say (the ✗ partners above, plus)
1. "Synthetic data improves real detectors" — additive +0.004–0.005 at equal steps (H51, Holm-significant, ~1 % relative, one site, one detector); never quote +0.0121 without "unequal steps".
2. "The loiter rule meets budget" — the shipped rule is ~2,900× over our assumed budget (28 §6), and ~70× a 1/zone/day PIDS norm [A].
3. "Renders are photoreal", or "night costs X recall" (H32 overfit).
4. Frame-level AUC as proof an alarm is usable.
5. "Auto-calibration works" (H39 not met) or "line-cross is solved" (H40/H40b not met: recall 0.782, twin FA ≈ 490× our assumed budget).
6. "H24 met" or "ReID fixes tracking" (bar missed, w untuned), the dose gain as more than small (+0.004–0.005 at equal steps, H51: significant but ~1 % relative, one site) or H26's five-seed n.s. as current; a validated drift threshold (H34 inconclusive); or "INT8 is free" (H38: −0.0117 AP) or any Jetson latency of ours.
7. Any number as "real-site" performance — all alarm numbers are simulated.

## The 90-second pitch (52)
"SurvSim is a surveillance simulator I built to evaluate CCTV analytics against
ground truth real footage can't give you — identities across cameras and
clothing changes, exactly when a behaviour became visible, which camera was
tampered with. A Python director runs behaviour classes with innocent
look-alikes for every suspicious one, drives a pure-Python backend or Unreal
Engine, and writes MOT, parquet and event logs. It scores alarms the way
buyers do: false alarms per camera-hour against a budget; late alarms count
as false. The most useful results were negative: fine-tuning on our renders
cut real AP from 0.276 to 0.152. Mask-derived boxes lifted box IoU against a
detector from 0.781 to 0.884, but retraining on them did not help, because
MOT20's labels are amodal. The one positive: adding 100 renders to 60 real
frames gives +0.004–0.005 AP once training steps are equal — significant over ten paired seeds but about 1 % relative, so
the simulator is an evaluation and stress-test instrument first, a training-data source second. And I
found HOTA bugs that had inflated our real-footage number to 0.545; the
correct value is 0.434 (0.443 once matched exactly to TrackEval)."

## 3 questions to ask them
1. What is the target operating point — alarms per camera-hour, or a detection guarantee?
2. How do you evaluate a model before it ships, and who owns the assurance case (JSP 936)?
3. Where does your synthetic data come from, and how do you measure its value on real data?
