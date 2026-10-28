# Adversarial accuracy audit — reports 25–31, 33–38 (2026-09-26)

Method as in AUDIT_17-24.md: every checkable claim was treated as wrong until
its primary source (arXiv tables, vendor datasheets, public registry, cloned
SAPIENT / Stone Soup repos, JSP 936 V1.1 PDF, i-LIDS guide, repo code) was
fetched. Equations were re-derived (Kalman gain, Hungarian, HOTA/MOTA/IDF1,
focal/triplet/Circle loss, homography DOF, EV100, JPDA worked example). Reports
were corrected in place, one commit per report. FACTS_VERIFIED.md was used
read-only for cross-checks. Report 32 does not exist; 39/40 are out of scope.

## Scores (confirmed / total claim rows)
Where a group's own table disagreed with its rows, the row count is used (25–27).

| Report | Confirmed | Total | Score |
|---|---|---|---|
| 25 detection | 34 | 40 | 85 % |
| 26 MOT | 25 | 34 | 74 % |
| 27 ReID | 19 | 32 | 59 % |
| 28 behaviour & scene | 34 | 45 | 76 % |
| 29 camera geometry | 33 | 40 | 83 % |
| 30 synthetic / sim2real | 34 | 44 | 77 % |
| 33 the vendor brief | 16 | 27 | 59 % (5 misses were F2→F retags, not errors) |
| 34 market & competitors | 6 | 15 | 40 % |
| 35 the vendor playbook | 24 | 36 | 67 % |
| 36 neuromorphic & SNN | 24 | 27 | 89 % |
| 37 fusion & tracking | 20 | 23 | 87 % |
| 38 edge deployment | 21 | 27 | 78 % |

## Corrections that change conclusions
* **HOTA 0.545 is stale everywhere (26, 31, 35).** It was HOTA at α=0.5 with a
  recall-only DetA. After be9f52a the MOT20 subset gives HOTA 0.434 (19-α mean),
  0.539 at α=0.5. 26 §8.2 now marks what is fixed (DetA = TP/(TP+FN+FP), 19-α
  mean, MOTA continuity, fragmentation edge case) and what is still open
  (per-frame IoU Hungarian rather than HOTA-maximising matching, no ignore
  regions, no MT/PT/ML).
* **Code issue found (not fixed; out of scope):** in the 26 §6.4 worked example
  the IoUs 0.9/0.8/0.7 are computed as 0.8999… etc. and fail `>= alpha`, so
  `evaluate_mot` gives HOTA ≈0.38–0.39 instead of the hand-derived 0.4034. The
  test tolerance (0.38 ± 0.03) hides it. `_hota_multi_threshold` needs an epsilon.
* **35 realism headline 12/14 → 6/14** (12/14 was the tuning grid, not the
  committed profile); night IR 3/14.
* **28 false-alarm budget ratio 3,000× → 150×**; i-LIDS pass thresholds are not
  published, so "fails as alerting" is not claimable.
* **31 FID direction reversed** (fog 249 vs day 32.8: minimising FID selects no
  degradation); 0.042 FA/cam-h is 24× stricter than 1/h, not 6×.
* **36 SpikeYOLO 84.2 mJ model has 68.8 M params, not 23.1 M.** The "25 % saving
  vs same-size ANN" becomes ~3× vs a size-matched but less accurate model.
* **38 Orin NX 16 GB has 2 DLAs**; Nano/NX TOPS are Super-mode (JetPack 6.2).
* **37 JPDA coalescence shift** is 1.1 / 1.25 m from the shared prediction
  (0.2 / 0.5 m is only the extra shift vs the radar-only update).
* **25 eval_recall.py** now matches in score order (COCO); docs/12 recalls were
  recorded under the old tallest-first order. YOLOv8n 0.99 ms is A100, not T4.
* **27 gallery false-match** ≈ 1 − e^(−Np), not ≈ Np.
* **29** the Axis sources do not say DORI was replaced in 2025; Zhang RMS from Table 1.
* **33 WB Group partnership** dated 5 Mar 2026, not 2025. **34** Evolon 98.5 % is
  accuracy, not FA reduction; Coram Series B June 2026.

## Cross-report consistency
* ByteTrack MOT17 80.3/77.3/63.1, MOT20 77.8/75.2/61.3; BoT-SORT-ReID MOT17
  80.5/80.2/65.0: consistent with FACTS_VERIFIED.
* OC-SORT MOT20 HOTA: 26 cites the paper (62.1); FACTS_VERIFIED has the README
  (62.4). 26 now notes both.
* CAL LTCC 40.1/18.0: consistent. OSNet Market 94.8/84.9 in 27 is CAL's
  re-run; the OSNet paper's own is 94.2/82.6 (FACTS_VERIFIED). Not edited.
* Orin TOPS: 36 and 38 now carry the Super-mode note, matching FACTS_VERIFIED.
* i-LIDS timing rules (late alarm = false alarm): consistent; 35 pitch fixed.
* Out of scope and left stale: CLAUDE.md says 40 evasion techniques (code has 52);
  docs/11 says 32 behaviours (44).

## Claim tables by group

### Reports 25-27

| claim | report § | source fetched (URL) | verdict | note |
|---|---|---|---|---|
| [25] RetinaNet 9 anchors/location (3×3) on P3–P7 | 1.2 | https://ar5iv.labs.arxiv.org/html/1708.02002 | confirmed | |
| [25] ~100k locations, ~1:1000 imbalance | 1.2 | same | confirmed | |
| [25] FL = −α(1−p)^γ log p, γ=2, α=0.25 | 1.2 | same | confirmed | |
| [25] Anchor IoU 0.5/0.4 thresholds [VERIFY] | 1.2 | same (paper §4) | corrected | VERIFY removed; stated as the paper's values |
| [25] Worked: p_t .99 → 10⁻⁴ factor; .5 → 4× | 1.2 | derived | confirmed | re-derived |
| [25] RetinaNet 39.1 AP R101-FPN | 1.2 | same | confirmed | test-dev |
| [25] FCOS 44.7 AP | 1.3 | https://arxiv.org/abs/1904.01355 | confirmed | ResNeXt-64x4d-101 |
| [25] YOLOv8 "anchor-free split Ultralytics head" | 1.3 | https://docs.ultralytics.com/models/yolov8/ | confirmed | |
| [25] DETR N=100, 300/500 epochs, +1.5 AP | 1.4 | https://ar5iv.labs.arxiv.org/html/2005.12872 | confirmed | |
| [25] DETR 42.0 ties FRCNN; APs 20.5 vs 26.6, APl 61.1 vs 53.4 | 1.4 | same | corrected | the comparison row is FRCNN-FPN+; plain row added |
| [25] RT-DETR R50 53.1/108 FPS, R101 54.3/74 FPS T4 | 1.5 | https://arxiv.org/abs/2304.08069 | confirmed | |
| [25] RT-DETR +2.2 AP vs DINO-R50, 21× faster | 1.5 | same | confirmed | |
| [25] stride-8 map has 16× the tokens of stride-32 | 1.5 | derived | confirmed | (32/8)² |
| [25] YOLO11m 22 % fewer params than YOLOv8m | 2.1 | https://docs.ultralytics.com/models/yolo11/ | confirmed | |
| [25] YOLOv8n 37.3 mAP at 0.99 ms T4 TensorRT | 2.1 | https://docs.ultralytics.com/models/yolov8/ | corrected | 0.99 ms is A100 TensorRT |
| [25] YOLOv8x 53.9, 68.2 M params | 2.1 | same | confirmed | |
| [25] YOLO11n 39.5/2.6 M; YOLO11x 54.7; 1.5–11.3 ms T4 | 2.1 | yolo11 docs | confirmed | TensorRT10; precision unstated (kept VERIFY) |
| [25] FPN AR_s 32.0→44.9; anchors 32²..512²; k0=4 | 2.1, 3.3 | https://ar5iv.labs.arxiv.org/html/1612.03144 | confirmed | |
| [25] n scale [0.33, 0.25, 1024]; P2 head P2–P5 | 2.1, 3.3 | raw ultralytics cfg/models/v8/yolov8-p2.yaml | confirmed | |
| [25] DFL formula, ŷ = Σ P y | 2.2 | https://arxiv.org/abs/2006.04388 | unverifiable | standard GFL form; not refetched |
| [25] reg_max 16 [VERIFY] | 2.2 | raw ultralytics nn/modules/head.py, utils/loss.py | corrected | confirmed default; VERIFY removed |
| [25] DFL worked 3.4 → 0.6/0.4; 15 strides = 120/480 px | 2.2 | derived | confirmed | |
| [25] CIoU/DIoU formulas, DIoU-NMS | 2.3 | https://arxiv.org/abs/1911.08287 | confirmed | standard form (from knowledge) |
| [25] CIoU worked: IoU .667, c² 544, L .340 | 2.3 | derived | confirmed | |
| [25] Ultralytics CIoU=True, BCEWithLogitsLoss | 2.3–2.4 | raw utils/loss.py L134, L349 | confirmed | |
| [25] VFL formula | 2.4 | https://ar5iv.labs.arxiv.org/html/2008.13367 | unverifiable | not refetched |
| [25] TOOD α=1, β=6, m=13, 51.1 AP | 2.5 | https://ar5iv.labs.arxiv.org/html/2108.07755 | confirmed | |
| [25] Ultralytics TAL topk 10, α 0.5, β 6 | 2.5 | raw utils/loss.py L342, L365-371 | confirmed | |
| [25] TAL worked 0.105 vs 0.336 | 2.5 | derived | confirmed | |
| [25] gains 7.5/0.5/1.5; conf .25/.001; iou .7; max_det 300; imgsz 640 | 2.6–2.7 | raw cfg/default.yaml | confirmed | |
| [25] COCO 10 IoU thrs, 101 recThrs, maxDets [1,10,100], areas 32²/96², backward sweep, searchsorted left | 4.1 | raw pycocotools/cocoeval.py L400-509 | confirmed | |
| [25] Worked AP 0.686 (101-pt), 0.683 all-point | 4.2 | derived | confirmed | 69.33/101 |
| [25] ECE worked 0.105 | 5.1 | derived | confirmed | |
| [25] Temp scaling ResNet-110/C100 ECE 16.53 → 1.26 % | 5.2 | https://ar5iv.labs.arxiv.org/html/1706.04599 | confirmed | |
| [25] Wu et al.: per-channel weights / per-tensor acts; no universal calibrator; QAT ~10 %; within 1 % | 6.1–6.3 | https://ar5iv.labs.arxiv.org/html/2004.09602 | confirmed | |
| [25] INT8 worked s=0.157, 0.047, 3.3× | 6.2 | derived | confirmed | |
| [25] 720p→640 = 0.5; 20 px → 1.25 cells @s8; SAHI 6 tiles + full pass | 3.1, 3.4 | derived | confirmed | steps of 480 give 3×2 |
| [25] SAHI +6.8/+5.1/+5.3, up to +14.5 with SF | 3.4 | https://ar5iv.labs.arxiv.org/html/2202.06934 | confirmed | 12.7/13.4 and slice sizes not in the fetched summary |
| [25] eval_recall matches greedy by GT height; 96 lines | 7.1 | tools/eval_recall.py | corrected | now score-ordered COCO-style; 129 lines; pre-fix numbers use the old order |
| [25] docs/12 recall figures (0.577→0.758/770; 0.439→0.634; 0.72→0.96; 0.678; 0.734; 0.866→0.810; 0.631→0.495) | 7.2 | docs/12 L706-1103 | confirmed | repo-sourced |
| [26] SORT state, T_Lost=1, 260 Hz, MOT15 33.4/1001/1764 | 2.2, 5.1 | https://ar5iv.labs.arxiv.org/html/1602.00763 | confirmed | |
| [26] DeepSORT 8-D state, t=9.4877, L=100, λ=0, A_max 30, 3 tentative, 1423→781 (45 %), det 0.3 | 5.2 | https://ar5iv.labs.arxiv.org/html/1703.07402 | confirmed | χ²₄(0.95)=9.4877 |
| [26] F=[I I;0 I], H=[I 0]; repo _F/_H | 2.3 | survsim/baselines/bytetrack.py | confirmed | |
| [26] Repo Q/R/P₀ weights 1/20, 1/160, 1e-2, 1e-5, 1e-1, 2h/20, 10h/160 | 2.3 | bytetrack.py L31-45 | confirmed | |
| [26] BoT-SORT σ_p .05, σ_v .00625, σ_m .05 | 2.3 | https://ar5iv.labs.arxiv.org/html/2206.14651 | confirmed | |
| [26] KF equations; worked K ≈ 0.71 | 2.4–2.5 | derived | confirmed | 60/85 |
| [26] Hungarian worked (greedy 0.6 vs optimal 1.05) | 3.3 | derived | confirmed | |
| [26] SciPy LSA = modified Jonker-Volgenant | 3.2 | scipy docs | unverifiable | not refetched |
| [26] Repo `_match` solves on raw −IoU then gates | 3.4 | bytetrack.py L78-83 | confirmed | still true after be9f52a |
| [26] ByteTrack τ 0.6, IoU <0.2 reject, 30 frames | 5.3 | https://ar5iv.labs.arxiv.org/html/2110.06864 | confirmed | |
| [26] BYTE on SORT 74.6→76.6, 76.9→79.3, 291→159 | 5.3 | same | confirmed | |
| [26] ByteTrack MOT17 80.3/77.3/63.1 @30 FPS; MOT20 77.8/75.2/61.3 | 5.3 | same | confirmed | |
| [26] 1–10 IDF1 on nine trackers; 170 ped/image MOT20 test | 5.3, 7 | same | confirmed | |
| [26] OC-SORT MOT17 63.2/78.0/77.5/1950 vs 63.1/80.3/77.3/2196 | 5.4 | https://ar5iv.labs.arxiv.org/html/2203.14360 | confirmed | |
| [26] OC-SORT MOT20 62.1/75.5/75.9/913 vs 61.3/77.8/75.2/1223 | 5.4 | same | confirmed | IDs −25 %, MOTA −2.3 |
| [26] OCM Δt=3, λ=0.2 | 5.4 | same | confirmed | |
| [26] BoT-SORT EMA α .9, θ_iou .5, θ_emb .25, weighted-sum λ .98 | 5.5 | 2206.14651 | confirmed | |
| [26] BoT-SORT MOT17 80.5/80.2/65.0 @4.5; MOT20 77.8/77.5/63.3 @2.4; ByteTrack 29.6 FPS | 5.5 | same | confirmed | |
| [26] CMC affine equations (M̃, T̃) | 5.6 | same | unverifiable | Eqs. 5-8 not in the fetched summary |
| [26] MOTA/MOTP/IDF1 Eqs. 2-6 | 6.1-6.2 | https://ar5iv.labs.arxiv.org/html/2009.07736 | confirmed | |
| [26] A(c) is Eq. 20 | 6.3 | same | corrected | Eq. 14 |
| [26] DetA Eq 18, AssA Eq 19, 19-α Eq 16, LocA Eq 17, DetRe/DetPr; two quotes | 6.3 | same | confirmed | |
| [26] Worked: MOTA .333, MOTP .77, IDF1 .5, DetA .714, AssA .34, HOTA₀.₅ .493 | 6.4 | derived; evaluate_mot at be9f52a | confirmed | code matches |
| [26] Worked: 19-α HOTA .403, DetA .554, AssA .301 | 6.4 | derived; evaluate_mot | confirmed | code 0.4034 with IoU-at-threshold epsilon; 0.392 with float rounding (note added) |
| [26] MOT20 per-sequence table and totals; 246 ped/frame; 25 fps | 7 | https://ar5iv.labs.arxiv.org/html/2003.09003 | confirmed | |
| [26] Repo tracker high .5/low .1/new .6/match_iou .2/low_iou .5; max_lost=fps | 8.1 | bytetrack.py L92-118; baselines/run.py L101 | confirmed | |
| [26] Unconfirmed-track third round in ByteTrack reference | 8.1 | none | unverifiable | kept VERIFY |
| [26] Evaluator DetA = recall (defect) | 8.2 | survsim/eval/tracking.py L179; commit be9f52a | corrected | FIXED: TP/(TP+FN+FP) |
| [26] Evaluator single α | 8.2 | tracking.py L35-38, L239-283 | corrected | FIXED: 19-α mean; hota_at_05 kept |
| [26] MOTA solves each frame from scratch | 8.2 | tracking.py L192-236 | corrected | FIXED: continuity carry-over (persists across gaps) |
| [26] Frag counts a GT entering unmatched | 8.2 | tracking.py L156-167 | corrected | FIXED via ever_tracked |
| [26] HOTA uses per-frame IoU Hungarian, not HOTA-maximising | 8.2 | tracking.py L246-272 | confirmed | still open |
| [26] MOT20 subset HOTA 0.545 is an upper bound | 8.2 | docs/13 L80-81 | corrected | now 0.434 (19-α), hota_at_05 0.539 |
| [26] metrics.py maxDets [1,10,1000] | 8.3 | docs/13 L37-38 | confirmed | metrics.py itself not re-read |
| [27] Label-smoothing form, ε=0.1; worked 0.9001 | 2.1 | https://ar5iv.labs.arxiv.org/html/1903.07071 | confirmed | |
| [27] Batch-hard formula, soft-margin "slightly better" | 2.2 | https://arxiv.org/abs/1703.07737 | unverifiable | ar5iv conversion failed; PDF unreadable |
| [27] TriNet 69.14/84.92, 81.07 re-ranked; P18K4, P32K4 | 2.2 | same | unverifiable | consistent with widely reproduced figures |
| [27] DTL 41.5 mAP | 2.2 | same | unverifiable | |
| [27] Triplet worked 0.5 vs 0 | 2.2 | derived | confirmed | |
| [27] Circle loss formula [VERIFY] | 2.3 | https://ar5iv.labs.arxiv.org/html/2002.10857 | corrected | formula confirmed; VERIFY removed; γ≈128 ReID, m≈0.25 noted |
| [27] CircleLoss 94.2/84.9 Market (CAL T4) | 2.3 | https://ar5iv.labs.arxiv.org/html/2204.06890 | confirmed | |
| [27] BoT 94.5/85.9; warmup 10 ep to 3.5e-4; ε .1; 16×8 | 2.4 | 1903.07071 | confirmed | |
| [27] Duke ablation 79.7/63.7 … 82.6/70.6 | 2.4 | same | unverifiable | not in the fetched summary |
| [27] Cross-domain: warmup/LS/BNNeck help; stride/centre don't | 2.4 | same | corrected | added that REA hurts cross-domain |
| [27] OSNet 94.8/84.9 Market (CAL T4) | 3.1 | 2204.06890 | confirmed | MSMT17 78.7/52.9 not returned |
| [27] OSNet ≈2.2 M params | 3.1 | none | unverifiable | kept VERIFY |
| [27] AP worked A .722, B .417, mAP .569, R1 50 %, R5 100 % | 4.3 | derived | confirmed | |
| [27] evaluate_reid: sort −sim, −inf mask, skip no-hit, AP=Σ(P·hit)/Σhit | 4.3 | tracking.py L378-414 | confirmed | |
| [27] k-reciprocal λ .3, k1 20, k2 6 | 5 | https://arxiv.org/abs/1701.08398 | unverifiable | kept VERIFY |
| [27] st-ReID Market 91.2→98.1, Duke 83.8→94.4 | 6.2 | https://arxiv.org/abs/1812.03282 | confirmed | |
| [27] st-ReID worked 0.65 vs 0.08 | 6.2 | derived | confirmed | |
| [27] CityFlow 3+ h, 40 cams, 10 intersections, 2.5 km, 200k+ boxes | 6.3 | https://arxiv.org/abs/1903.09254 | confirmed | |
| [27] 1−(1−p)^N ≈ Np; 39 % at p=1e-4, N=5000 | 7 | derived | corrected | ≈Np invalid at Np=0.5; 1−e^(−Np)=39.3 % |
| [27] LTCC 152/17,119; PRCC 221/33,698 | 8 | 2204.06890 Table 1 | confirmed | |
| [27] CAL Table 2, all 16 cells | 8 | same | confirmed | |
| [27] Cooperative clothes classifier LTCC CC 21.9 | 8 | same | unverifiable | not returned by fetch |
| [27] CCVID GaitSet 81.9/73.2, CAL 82.6/81.3 general | 8 | same | confirmed | CC columns not returned |
| [27] AppearanceState blake2b 8-byte; epoch+=1 on hash change | 9.1 | survsim/core/appearance.py L61-112 | confirmed | |
| [27] SOFT_BIOMETRIC_KEYS + flattened gait_* | 9.1 | appearance.py L25, L141 | confirmed | |
| [27] Gait signature 6 params; INDIVIDUAL_SPREAD 7 %/9 %/0.04 | 9.2 | survsim/gait/signature.py L110-136 | confirmed | |
| [27] 123 spm @0.39 m crowd vs ~110/~0.75 free; CASIA-B coat −0.0001 z −0.1, bag +0.040 z +9.9 | 9.2 | signature.py docstring | confirmed | repo-sourced |
| [27] gait_distance normalised by population_spread | 9.2 | signature.py L226-236 | corrected | defaults to unit spread; the similarity matrix normalises by default |
| [27] observe noise 0.15 of between-person spread | 9.2 | signature.py L239-261 | confirmed | uses nominal INDIVIDUAL_SPREAD |
| [27] reid_by_epoch masks (within excludes same camera; cross does not) | 9.3 | tracking.py L417-467 | confirmed | |
| [27] UK GDPR Art 4(14) quote; ICO gait / special category | 10.1 | legislation.gov.uk; ico.org.uk | unverifiable | not refetched |
| [27] AI Act 5(e)/(g)/(h) lettering and content | 10.2 | https://artificialintelligenceact.eu/article/5/ | unverifiable | from knowledge of the final text; not refetched |

### Reports 28-30

| claim | § | source fetched (URL) | verdict | note |
|---|---|---|---|---|
| [28] i-LIDS scenarios: abandoned baggage, parked vehicle, doorway, sterile zone + MCT; "six scenarios" | 1.1 | https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf §4.1 | confirmed | six = 5 + New Technologies |
| [28] No i-LIDS loitering scenario | 1.1 | same, §4.1 | confirmed | |
| [28] Abandoned object: owner left, "over sixty seconds after they left", object remains (App. F) | 1.1 | same, l.1769 | confirmed | |
| [28] Parked vehicle: >60 s in zone; follow-on "Person exits vehicle" | 1.1 | same, l.1920-1931 | confirmed | |
| [28] 10 s window; repeats disregarded; "should NOT continue to alarm"; one FP per 5 s | 1.1 | same, l.1202-1209 | confirmed | matches FACTS_VERIFIED #20 |
| [28] r = a/(a+c), p = a/(a+b) | 1.1 | same, §6.4.1 | confirmed | |
| [28] F = (α+1)rp/(r+αp), reconstructed, VERIFY | 1.1 | same, §6.4.1 (α glyphs dropped in PDF text layer) | corrected | called "F1" in guide; placement fixed by the α→∞ ⇒ recall requirement; hedge rewritten |
| [28] α abandoned baggage 0.35 / 35; parked vehicle 0.55 / 60 | 1.1 | same, l.1797-1800, 1963 | confirmed | doorway 0.5/24, sterile 0.65/75 also present |
| [28] Pass thresholds "not made public" | 1.1 | same, l.1393 | confirmed | |
| [28] Worked F: 0.46 / 0.78; "fails as alerting, passes as recording" | 1.1 | arithmetic | corrected | arithmetic right; pass/fail claim removed (thresholds secret) |
| [28] PETS 2006: railway station, BTP + Network Rail, 7 sequences, 300 cm / 30 s, warning→alarm | 1.2 | https://www.egdn.net/mypubs/Auvinetal06PETS.pdf | confirmed | |
| [28] PETS 2007 loitering "> 60 s" | 1.2 | none reachable | unverifiable | tag kept, reworded |
| [28] ActEV activity definition quote; five elements; example names | 1.3 | https://actev.nist.gov/pub/Draft_ActEV_2018_EvaluationPlan.pdf p.5 | confirmed | definition verbatim; name list not re-checked against App. D |
| [28] RateFA per minute of video; P_miss formula | 1.3 | FACTS_VERIFIED #21 / actev.nist.gov | confirmed | repo-sourced |
| [28] `CommuteWait(Loiter)` inherits motion, label `normal.commute_wait`, docstring quote | 1.4 | survsim/director/behaviours.py:125-128 | confirmed | |
| [28] `Tailgate` gap_m default 1.2; `ObjectAbandon` docstring | 1.4 | behaviours.py:131-134, 354 | confirmed | |
| [28] docs/03 commute_wait 30–900 s, smoke_break/vendor/maintenance negatives | 1.4, 2.2 | docs/03_BEHAVIOUR_CATALOG.md l.16-24 | confirmed | |
| [28] DwellRule: tags gate/restricted/perimeter_fence, speed cap 0.5, threshold 60, fires once per zone | 2.1 | survsim/eval/rules.py:27-57 | confirmed | |
| [28] AbandonedObjectRule: static 30 s, owner > 15 m | 2.1 | rules.py:67-68 | confirmed | |
| [28] 90 % / 34 % commuter arithmetic | 2.2 | arithmetic | confirmed | (780/870, 300/870) |
| [28] behaviour.py ten trajectory-only features; split by identity | 2.3 | survsim/eval/behaviour.py:34-44 | confirmed | |
| [28] 0.95⁴ ≈ 0.81 | 2.4 | arithmetic | confirmed | 0.8145 |
| [28] 8 obs (3.2 s) / 12 pred (4.8 s), leave-one-out ETH/UCY | 3.1 | Social GAN PDF (arxiv 1803.10892) | confirmed | |
| [28] Social-LSTM N_o×N_o×D tensor, no extra params, bivariate Gaussian | 3.2 | https://cvgl.stanford.edu/papers/CVPR16_Social_LSTM.pdf | confirmed | |
| [28] Social GAN Table 1 AVG cells (Linear, LSTM, S-LSTM, 1V-1, 20V-20) [VERIFY] | 3.3 | arxiv 1803.10892 PDF Table 1 | corrected | all cells right; VERIFY removed, 1V-20 row and 20V-20 FDE 0.78/1.18 added |
| [28] Trajectron++ "60 % lower" quote; best-of-20 ≈ 0.2/0.4 vs SGAN ≈ 0.6/1.2 [VERIFY] | 3.4 | arxiv 2001.03093 PDF Table 2(b) | corrected | exact: 0.19/0.41 (Ours+ 0.21/0.41) vs 0.58/1.18 |
| [28] Social-STGCNN 20 % FDE, 8.5× fewer params, 48× faster | 3.4 | https://arxiv.org/abs/2002.11927 | confirmed | |
| [28] Helbing parameters (1.34±0.26, 1.3v⁰, 2.1/0.3, 10/0.2, τ 0.5, 200°, c 0.5, Δt 2 s, 10 m) | 4.1 | arxiv cond-mat/9805244 PDF | confirmed | "aggressive" quote made verbatim |
| [28] N(W) = 0.36 m⁻¹·W + 0.59; ~4 lanes at 10 m | 4.1 | same, Fig. 2/3 captions | confirmed | at density 0.3 m⁻² |
| [28] crowd.py: first-order, linear push inside 3×personal_space, no τ, no walls, no labels | 4.2 | survsim/director/crowd.py:149, 213-223, 249-273 | confirmed | |
| [28] Hasan: FC-AE on handcrafted features + fully-conv AE | 5.1 | arxiv 1604.04574 PDF | confirmed | |
| [28] Liu PSNR formula, per-video min-max normalisation | 5.2 | arxiv 1712.09867 PDF | confirmed | |
| [28] Liu AUC table: Avenue ~85 [VERIFY], Ped1 83.1 (MDT 81.8), Ped2 95.4 (92.2), ShanghaiTech 72.8 (68.0) | 5.2 | same, Table 1 | corrected | Avenue 84.9; best prior Avenue is Stacked RNN 81.7, not 80.6 |
| [28] Avenue 16/21 videos, 47 events incl. loitering; ShanghaiTech 330/107, 130 events, 13 scenes | 5.2 | same | confirmed | |
| [28] Sultani: 32 segments, C3D FC6, MLP 512-32-1, λ = 8e-5, 30+30 bags | 5.3 | arxiv 1801.04264 PDF | confirmed | |
| [28] UCF-Crime 1,900 / 128 h / 13 classes [VERIFY list]; 800+810 / 150+140 | 5.3 | same | corrected | list confirmed verbatim; VERIFY removed (Table 1 shows only 8) |
| [28] AUC 50.0 / 50.6 / 65.51 / 74.44 / 75.41; FA 27.2 / 3.1 / 1.9 at 50 % | 5.3 | same, Tables 3-4 | confirmed | |
| [28] FA causes: darkness, insects, sudden gathering; "major part … is normal" | 5.3 | same | confirmed | |
| [28] XD-Violence 4,754 videos, 217 h, 6 classes; AP rationale; 78.64 vs 73.20; 82.44 AUC | 5.4 | https://ar5iv.labs.arxiv.org/html/2007.04687 | confirmed | Sultani re-run 75.51 in their table |
| [28] Ramachandra quotes; UMN > 99 %; RBDC/TBDC | 6.1 | arxiv 2004.05993 PDF | corrected | survey's acronyms are RBDR/TBDR |
| [28] 720 windows; 1−0.981¹⁵⁰ ≈ 94 % | 6.2 | arithmetic | confirmed | 0.944 |
| [28] alarms.py A=4, K=500, H=8 ⇒ 0.001; docstring "roughly 0.005" | 7.1 | survsim/eval/alarms.py:11-45 | corrected | docstring already fixed; text now past tense |
| [28] "3,000× over the gentler budget" | 7.3 | arithmetic | corrected | 18/0.12 = 150× |
| [28] Base-rate precision 0.15 % / 7 % / 90 % | 7.2 | arithmetic | confirmed | |
| [28] anomaly.py Poisson rate 0.5/cam-h, hard_negative_ratio 3, "defensible denominator" | 7.2 | survsim/director/anomaly.py:9-17, 71-89 | confirmed | |
| [28] cli `--threshold-s` 60, `--tolerance-s` 10; `ilids_compat` coalesces 5 s, ignores repeats | 7.4 | survsim/cli.py:116-131; alarms.py:150-200 | confirmed | |

### Report 29 — Camera geometry and calibration
| claim | § | source fetched (URL) | verdict | note |
|---|---|---|---|---|
| [29] P = K[R|t], 11 DoF | 1.2 | derivation | confirmed | 5+3+3 |
| [29] Zhang "pixels are square" aspect-ratio quote | 1.2 | https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr98-71.pdf l.1082 | confirmed | |
| [29] intrinsics(): f = (W/2)/tan(HFOV/2), f_y = f_x, centred pp, zero skew | 1.2 | survsim/core/geometry.py:15-19 | confirmed | |
| [29] cam_gate K = [[1371,0,960],[0,1371,540]]; VFOV 43.0° | 1.2 | geometry.py run; arithmetic | confirmed | 1371.0 |
| [29] R_mount = Rz(yaw)·Ry(−pitch)·Rx(roll), docstring "looks at the sky" | 1.3 | geometry.py:22-35 | confirmed | |
| [29] to_optical permutation; R = to_optical·R_mountᵀ; t = −R·C | 1.3 | geometry.py:38-46 | confirmed | |
| [29] Unreal boundary: M_TO_CM 100, −Y, −yaw | 1.3 | CLAUDE.md principle 7; backend.py | confirmed | repo-sourced |
| [29] unreal.Rotator(roll, pitch, yaw) positional | 1.3 | https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Rotator?application_version=5.4 | confirmed | |
| [29] H = K[r1 r2 t], 8 DoF, 4 points | 2.2 | derivation; Zhang §2 | confirmed | |
| [29] cam_gate H matrix values | 2.3 | geometry.py run | confirmed | matches to 4 s.f. |
| [29] near ground 5.1 m; horizon in frame | 2.3 | arithmetic | confirmed | 4.5/tan 41.5° = 5.09 |
| [29] OpenCV Brown–Conrady full equation, coefficient ordering, fisheye θ_d | 3.2-3.3 | calib3d.hpp (from knowledge, not refetched) | confirmed | standard |
| [29] Zhang barrel/pincushion k1 sign remark; "first two terms" | 3.2 | tr98-71 l.434, 978 | confirmed | |
| [29] apply_distortion 5-term brown, 4-term fisheye, θ = atan(r), default distort=True | 3.2-3.3 | geometry.py:49-98 | confirmed | |
| [29] Zhang constraints h1ᵀBh2 = 0 etc.; 2n×6 SVD; n=2 with skew=0 | 4.2 | tr98-71 l.389-390, 575 | confirmed | |
| [29] "MLE improves considerably"; RMS 0.33–0.34 px | 4.3 | tr98-71 Table 1 | corrected | 0.295/0.393/0.361/0.335 |
| [29] PULNiX 6 mm, 640×480, 8×8 squares, 256 corners, 17 cm, 5 images, "very consistent" | 4.4 | tr98-71 l.772-774, 1072 | confirmed | |
| [29] "From 2 to 3, the errors decrease significantly" | 4.4 | tr98-71 l.756 | confirmed | |
| [29] WILDTRACK: intrinsics once per camera; hand-measured cm; 1,398 points; 15 params; joint best | 4.5 | arxiv 1707.09299 PDF l.574-632 | confirmed | |
| [29] WILDTRACK 3.92 views/position; 1440×480 grid; 50 ms sync; "notable calibration inaccuracy" | 7.4, 9.2 | same l.397, 509-512 | confirmed | inaccuracy quote refers to PETS 2009 |
| [29] Sinha & Pollefeys: centre-of-rotation quote; "negligible compared to"; VB-C10 linear vs SNC-RZ30 non-linear; distortion more prominent at short f; pp straight line | 5.2 | https://snsinha.github.io/pdfs/SinhaOMNI2004.pdf l.101-104, 210, 243, 720-722 | confirmed | |
| [29] cam_ptz (0,0,9), hfov [3,60], 40°/s, presets 30/35/30 | 5.3 | configs/scenarios/disguise_and_tamper.yaml:55-69 | confirmed | |
| [29] _step_ptz hfov lag min(1, 4·dt), writes live hfov_deg | 5.3 | camera_director.py:85, 130 | confirmed | |
| [29] PTZ f 1663 / 3583 / 36,661 px; 22×; VFOV 1.7°; 18.6–20.1 m; 1,470 px/m | 5.3 | arithmetic | confirmed | |
| [29] gate→fence 100° in 2.5 s | 5.4 | yaml presets −10 → 90 | confirmed | |
| [29] DORI table 4/10/20/40 px/face, 25/63/125/250 px/m, 16 cm face; caveats | 6.2 | https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014 | confirmed | |
| [29] 2025 seven levels 20…1500 px/m; fps/IR/angle/monitor changes; LPDO/HPDO [VERIFY] | 6.3 | https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2025 | corrected | acronyms expanded from source; VERIFY removed |
| [29] Axis blog: 3 / 240 px/face; 20 Nov 2025; cybersecurity | 6.3 | https://newsroom.axis.com/blog/iec-62676-4-video-surveillance | confirmed | |
| [29] Blog says 2025 "replaced DORI" | 6.3 | same | corrected | blog does not say replaced; white paper keeps DORI alongside |
| [29] Range table f/D for four cameras | 6.4 | arithmetic | confirmed | |
| [29] Footprint table near/far for 4 cameras | 7.1 | arithmetic | confirmed | |
| [29] pixel_height table 305…18 px; usably_visible flips at 150 m | 7.2 | geometry.py run (H = 1.75) | confirmed | |
| [29] MIN_USABLE_PX_HEIGHT = 20; usably_visible definition | 7.3 | geometry.py:127-141 | confirmed | note: default person height 1.7 m, rig uses PERSON_H = 1.7 |
| [29] R_20 ≈ 120 / 51 / 145 m; 11 px/m | 7.3 | arithmetic | confirmed | |
| [29] `survsim rig` blind 39.6 %, 1.14, 44.8 %; overlap 1.00 vs 0.17; blind 1,652 / 346 m² | 7.4 | command run this session | confirmed | |
| [29] overlap asymmetry definition [VERIFY in survsim/rig/] | 7.4 | survsim/director/rig.py:109-120 | corrected | path was wrong; docstring confirms reading; VERIFY removed |
| [29] 1° yaw: 24.5 px, 0.70 m at 40 m; 0.87 m at 50 m | 8.2 | geometry.py run | confirmed | |
| [29] 1° pitch: 6.2 m small-angle; 25.4 px / 7.4 m; 5.4 m the other way | 8.3 | geometry.py run | confirmed | 5.44 / 7.44 |
| [29] CityFlow 40 cams, 10 intersections, 2.5 km, 5–14 landmarks, 11.52 px, lane-line straightening, flat-earth | 8.4, 9.2 | https://arxiv.org/pdf/1903.09254 l.14-15, 428-437 | confirmed | |
| [29] cam_yard 95° dome handled by Brown–Conrady; self-calibration from people | 3.3, 9.2 | none | unverifiable | already tagged |

### Report 30 — Synthetic data and sim2real
| claim | § | source fetched (URL) | verdict | note |
|---|---|---|---|---|
| [30] Tobin: non-realistic textures, 1.5 cm, "first successful transfer", "just another variation" | 2.1 | https://arxiv.org/abs/1703.06907 | confirmed | |
| [30] Tremblay 100K imgs, ≤14 cars, 36 models, 8K textures, az 0–360 / el 5–30, flying distractors | 2.2 | https://arxiv.org/html/1804.06516 | confirmed | |
| [30] Table AP@0.5: 79.7/78.1, 64.6/71.5, 36.1/46.3; VKITTI 2.5K | 2.2 | same | confirmed | |
| [30] Fine-tune 6,000 real → 98.5, +1.6 / +2.1 | 2.2 | same | confirmed | |
| [30] Ablation 73.7 / 67.6 / 69.0 / 72.0 / 71.5 / 73.6 | 2.2 | same | confirmed | |
| [30] Ablation rows "flying distractors (−1.1 %)" and "light augmentation only 73.6" | 2.2 | same | corrected | rows are "no distractors 72.6" and "no light augmentation 73.6" |
| [30] Freezing: 66.4 vs 78.1, 69.4 vs 71.5 | 2.2 | same | confirmed | |
| [30] Hinterstoisser: freeze real-pretrained extractor, OpenGL renders | 2.2 | https://arxiv.org/abs/1710.10710 | confirmed | |
| [30] SDR Table I (49.6/44.8/33.6 … 77.3/65.6/52.2); saturation 10K, 43.7 @1K, DR ~50K | 2.3-2.4 | https://arxiv.org/html/1810.10093 | confirmed | |
| [30] SDR Table III 69.6/65.8/52.5 vs BDD100K 59.7/54.3/45.6 | 2.4 | same | confirmed | |
| [30] "far cameras see 14 to 60 px people" | 2.3 | docs/12 l.1064-1065, 1082 | corrected | 14–40 px at 45–60 m |
| [30] Johnson-Roberson Sim200k 68.03/52.57/42.07 vs Cityscapes 62.47/42.74/35.66 on 7,481 | 2.5 | https://ar5iv.labs.arxiv.org/html/1610.01983 Table II | confirmed | |
| [30] MetaHuman vs CesiumMan recall 0.577→0.758 / prec 0.852→0.884 / 770 boxes / 50 px 0.439→0.634, 0.72→0.96 | 2.6 | docs/12 l.884-901 | confirmed | |
| [30] far cams 0.0–0.11 recall; yolov8n misses 14–40 px | 2.6 | docs/12 l.1060-1065 | confirmed | |
| [30] FID formula; 1-D worked example 0.41 | 3.2 | https://arxiv.org/abs/1706.08500; arithmetic | confirmed | |
| [30] FID_MIN_SAMPLES = 2048; "with a straight face" 12 frames; _trace_sqrt_product | 3.2 | survsim/eval/realism.py:151-154, 226 | confirmed | |
| [30] Bińkowski: FID biased; CIFAR n=10,000 ≈ 8.1 still falling; reversal at n=50,000; kernel (xᵀy/d+1)³ unbiased | 3.3-3.4 | https://arxiv.org/html/1801.01401 | confirmed | "asymptotically normal" not seen in fetched text |
| [30] Chong & Forsyth E[FID_N] = FID∞ + K/N, model-dependent K; DCGAN flip; "5K to 50K" | 3.3 | https://ar5iv.labs.arxiv.org/html/1911.07023 | corrected | subsets ≥5K of a 50K pool |
| [30] Clean-FID: JPEG-matching improves FID; resize aliasing | 3.5 | https://arxiv.org/abs/2104.11222 | confirmed | |
| [30] Kynkäänniemi 2023: Top-1 matching −8 to 11 % (FFHQ −11.3 %) | 3.6 | https://arxiv.org/html/2203.06026 | confirmed | 8.4–11.3 |
| [30] pre-logit resampling −58 to 72 % | 3.6 | same | corrected | 42–72 % |
| [30] Grad-CAM outside face; FastGAN 5.28 / StyleGAN2 5.30; FID-CLIP 4.67 / 2.76 | 3.6 | same | confirmed | |
| [30] Stein: no metric correlates strongly; DINOv2-ViT-L/14; 17 metrics, 9 encoders | 3.6 | https://arxiv.org/abs/2306.04675 | confirmed | |
| [30] DINO features carry segmentation info | 3.6 | https://arxiv.org/abs/2104.14294 | confirmed | abstract |
| [30] Kynkäänniemi 2019: VGG-16 fc2, k=3, 50K; "anything in between" quote; f(φ,Φ) definition | 4.1-4.2 | https://ar5iv.labs.arxiv.org/html/1904.06991 | confirmed | |
| [30] Naeem: outlier-sensitive, fails identical distributions; density/coverage [VERIFY formulas] | 4.3 | https://arxiv.org/abs/2002.09797 | confirmed | formulas still tagged VERIFY (abstract only) |
| [30] 14 stats, 720 px, blockiness native; 80 frames; noise 0.309 (0.278–0.353); blockiness 1.149 (1.111–1.197) | 5.2 | docs/15 l.22-51 | confirmed | |
| [30] 2/14 raw; "per-frame codec profile reached 12/14"; finals 6/14, 9/14, 3/14 on 60 frames | 5.3 | docs/15 l.56-58, 218-238 | corrected | 12/14 was cctv_day_720p on its tuning grid; wording tightened |
| [30] mtf_ratio 0.15 vs ≤0.033; grain → 0.0202 | 5.3 | docs/15 l.58, 224 | confirmed | |
| [30] GOP: blockiness 1.118→0.865; temporal 2.20→0.53; grain overshoots 5–10 vs 1.57–2.93; xfail | 5.3 | docs/15 l.121-184 | confirmed | |
| [30] MOT sequences per-frame JPEG; no real IR reference | 5.3-5.4 | docs/15 l.186-190, 246 | confirmed | |
| [30] UE PBR: polarizing-filter quote, metallic binary, specular 0.5, charcoal 0.02–snow 0.81 | 6.1 | https://dev.epicgames.com/documentation/en-us/unreal-engine/physically-based-materials-in-unreal-engine | confirmed | |
| [30] asphalt albedo "about 0.1 [VERIFY]" | 6.1 | same table | corrected | fresh 0.02, worn 0.08 |
| [30] Tremblay −6.1 AP fixed light; sun 25–60°; 40,000 lux EV100 12.5 | 6.2 | docs/12 l.589-590, 740 | confirmed | |
| [30] Night history: first pass black; 3400 K 25,000 lm "too bright"; v2 4000 K 9,000 lm 30 m | 6.2 | docs/12 l.762-763, 1067-1076 | corrected | first *v2* pass; 78° spots; "amber and bright near lamps" verbatim; earlier 15,000 lm noted |
| [30] UE AE: Histogram 64 bins default, Basic, Manual; EV100 = log2(N²/t·100/ISO); min=max disables; 2^ExpComp; stops/s | 6.3 | https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-exposure-in-unreal-engine | confirmed | |
| [30] Recipe AEM_MANUAL, bias = −EV100, [X] histogram; 3-frame probe 60–140, log2(m/100); per-camera v6; cam_sub 25.6 % / EV 12.98 vs 13.5; plaza 43 → 11.8 | 6.3 | docs/12 l.587-589, 746-748, 1039-1081 | confirmed | |
| [30] log2(43/100) = −1.22; 2.3× | 6.3 | arithmetic | confirmed | |
| [30] degrade: sensor_noise Poisson/CLT≥20/FPN/hot/grain; auto_exposure median ±max_ev p1–p99; camera_automatics; rolling_exposure sinusoid no shear; motion_blur global; dark_flat_quantise; h264_sequence libx264 GOP/B yuv420p; no libx265 | 6.4-6.7 | survsim/sensors/degrade.py:99-180, 314-395, 434-479 | confirmed | |
| [30] Foi σ²(y) = a·y + b, a = χ⁻¹, clipping | 6.4 | Foi TIP 2008 abstract (PDF not re-read) | confirmed | a = χ⁻¹ from knowledge |
| [30] Brooks 14–38 % lower error, 9–18× faster | 6.4 | https://arxiv.org/abs/1811.11127 | confirmed | |
| [30] Basler: higher fps reduces effect; exposure time no influence | 6.5 | https://www.baslerweb.com/en/learning/cmos-rolling-shutter-cameras/ | confirmed | |
| [30] 31 px slew shift; 3 / 12.5 px blur; 0.077 bit/px | 6.5-6.7 | arithmetic | confirmed | |
| [30] `barrel_distort` k1 ≈ −0.16 | 6.8 | degrade.py:41, 528, 599-604 | corrected | dead Profile value; distortion now via lens.distort_image |
| [30] H.265 CTU up to 64×64; NVRs default H.265; 1/12 s night shutter; 850 nm IR; NIR dye reflectance | 6.2, 6.6-6.7 | none | unverifiable | already tagged [VERIFY] |
| [30] tools/eval_recall.py and `python -m survsim.realism compare` exist | 7 | repo | confirmed | |

### Reports 31, 35

| claim | § or Q# | source URL | verdict | note |
|---|---|---|---|---|
| [31] COCO IoU .50:.05:.95; small<32², medium 32²–96²; maxDets 100 | Q1,Q3 | https://raw.githubusercontent.com/cocodataset/cocoapi/master/PythonAPI/pycocotools/cocoeval.py | confirmed | |
| [31] keypoint areaRng all/medium/large, maxDets 20 | Q9 | same | confirmed | |
| [31] IoU 18/22≈0.82, 198/202≈0.98; 32²≈20×51 px | Q1,Q3 | arithmetic | confirmed | |
| [31] AUC 0.72, P 0.074, 93 % false, prevalence 3.3 % | Q2,Q28 | docs/14 §2–3 | confirmed | |
| [31] SORT Kalman+Hungarian, 260 Hz, detector up to 18.9 % | Q4,Q16 | https://arxiv.org/abs/1602.00763 | confirmed | |
| [31] ~14 % KF speed-up, bit-identical | Q4 | docs/13; survsim/baselines/bytetrack.py `_process_noise/_obs_noise` | confirmed | |
| [31] Hungarian O(n³) | Q5 | standard result | confirmed | VERIFY tag left |
| [31] DeepSORT NN appearance queries, ReID-trained, −45 % IDs | Q5,Q16 | https://arxiv.org/abs/1703.07402 | confirmed | |
| [31] MOT20 "extremely crowded" | Q5,Q13 | https://arxiv.org/abs/2003.09003 | confirmed | |
| [31] focal-loss quotes | Q6 | https://arxiv.org/abs/1708.02002 | confirmed | |
| [31] RetinaNet "matched two-stage accuracy at one-stage speed" | Q6 | same | corrected | surpassed two-stage accuracy |
| [31] 1080p→640 wide ÷3 height | Q7 | arithmetic | confirmed | |
| [31] stride-8 ~3 cells | Q7 | none | unverifiable | tagged VERIFY |
| [31] DukeMTMC calibrated, 8 cams, >2,700 ids, 85 min | Q8,Q24 | https://arxiv.org/abs/1609.01775 | confirmed | |
| [31] IDF1 quote (errors uniform, correct identification) | Q17,Q25 | same | confirmed | |
| [31] DR quote, 1.5 cm, sim-only RGB | Q10,Q50,Q52 | https://arxiv.org/abs/1703.06907 | confirmed | |
| [31] AdaBN | Q10 | none | unverifiable | tagged VERIFY |
| [31] persistence 8.0→1.0 FA/h, recall 0.50→0.33 | Q12 | docs/14 §6 | confirmed | |
| [31] i-LIDS 10 s; repeats disregarded; one FP per 5 s | Q12,Q41,Q45 | https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/143875/ilids-user-guide.pdf | confirmed | guide §6.3.2; FACTS #20 |
| [31] YOLO11n AP .35/.73/.29 on 600 frames | Q13 | docs/13 | confirmed | |
| [31] full-MOT20 run abandoned for time | Q13 | docs/13 | confirmed | |
| [31] ByteTrack +1–10 IDF1 over 9 trackers | Q15 | https://arxiv.org/abs/2110.06864 | confirmed | |
| [31] ByteTrack 80.3/77.3/63.1 MOT17, 30 FPS V100 | Q16 | same; FACTS #1 | confirmed | |
| [31] HOTA √(DetA·AssA), α .05–.95; MOTA first-order; IDF1 can fall as detection improves; human alignment | Q17 | https://arxiv.org/abs/2009.07736 (PDF §7) | confirmed | matches survsim/eval/tracking.py |
| [31] i-LIDS track fails if continuity lost >4 s | Q18,Q24,Q25 | guide §6.4.2 | confirmed | |
| [31] 6 tamper kinds; GT follows live camera | Q19,Q38,W7 | survsim/director/camera_director.py TAMPER_KINDS | confirmed | |
| [31] repo ByteTrack MOTA .46/IDF1 .54/HOTA .55 | Q20 | docs/13 fix section; survsim/eval/tracking.py | corrected | .47/.55/.43 (.54 @α=.5) |
| [31] 62 s track+eval on 8,931 frames; O(n²) story wrong | Q20,Q40 | docs/13 | confirmed | |
| [31] BoT 94.5 R1 / 85.9 mAP Market | Q21 | https://arxiv.org/abs/1903.07071 | confirmed | |
| [31] OSNet-ImageNet R1 .19, mAP .23 | Q22 | docs/13 | confirmed | |
| [31] OSNet design; SOTA on six datasets | Q23 | https://arxiv.org/abs/1905.00953 | confirmed | |
| [31] i-LIDS MCT 3 overlapping / 5 mixed cams | Q24 | https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf | confirmed | |
| [31] limp cost §12; crowd ≠ slow-motion §10 | Q26 | docs/14 | confirmed | |
| [31] RBI definition "physical, physiological, behavioural"; 1:1 excluded | Q26,Q56,Q57 | https://artificialintelligenceact.eu/annex/3/ | confirmed | |
| [31] ~4× P, ~3× R; 27.75→0.25 FA/h; recall .50→.17 | Q27 | docs/14 §3,§6 | confirmed | |
| [31] "common video defects" cited to user guide | Q28,Q33,Q59 | guide text (absent); https://www.researchgate.net/publication/284353547 | corrected | re-cited [23] |
| [31] F1 0.7 commissioning, stricter for approval | Q28,Q59 | guide §6.3.2 | confirmed | |
| [31] survey "considered as an FP … strongly penalizes"; ignores duration | Q28,Q45,W10 | https://pmc.ncbi.nlm.nih.gov/articles/PMC9104546/ | confirmed | |
| [31] loiter bugs; dwell 0/2, path-loiter 2/2 +13 FP | Q29 | docs/13 | confirmed | |
| [31] AUC .46 (3 ids) → .72 (10 scenes, 18 ids) | Q31 | docs/14 §1–2 | confirmed | |
| [31] weights −1.88/−1.64/−1.48/+0.56 | Q32 | docs/14 §4 | confirmed | |
| [31] controller handles operational alerts; recall bias per role | Q32,Q59 | guide §5.1.2.3 | confirmed | |
| [31] real band from 80 frames real+MOT20 | Q33 | docs/15 | confirmed | |
| [31] FID quote | Q34 | https://arxiv.org/abs/1706.08500 | confirmed | |
| [31] fog can score closer than day under FID | Q34 | docs/14 §11 | corrected | inverted |
| [31] i-LIDS NIR/MWIR/LWIR persons/vehicles/boats | Q35 | brochure | confirmed | |
| [31] RF 1.00→0.25 FA/h; correlated nuisance | Q36,W8 | docs/14 §6 | confirmed | |
| [31] ICO "lawful, necessary and proportionate"; FRT/ANPR/BWV/drones; under review (DUAA) | Q39,Q55 | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/ | confirmed | |
| [31] ilids_compat; toy precision .10→.33 | Q41,Q45 | survsim/eval/alarms.py; docs/13 | confirmed | |
| [31] i-LIDS private evaluation set | Q44,W10 | guide §4.2 | confirmed | |
| [31] 5th-frame annotation; 100 %/75 % height; shoulders | Q46 | guide | confirmed | |
| [31] occlusion flag when 100 % in scene but obscured | Q46 | guide | corrected | needs 50 %+ occluded |
| [31] 228 MB cached detections | Q48 | docs/13 | confirmed | |
| [31] "500GB hard disk" | Q49 | brochure | confirmed | |
| [31] Wood et al. synthetic matches real | Q50 | https://arxiv.org/abs/2109.15102 | confirmed | |
| [31] mock AP 0.008 | Q51 | docs/13 | confirmed | |
| [31] SCC laid 16 Nov 2021, in force 12 Jan 2022 | Q55 | https://www.gov.uk/government/publications/update-to-surveillance-camera-code | confirmed | |
| [31] DPIA Art 35(3)(c) wording | Q55 | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/when-do-we-need-to-do-a-dpia/ | confirmed | |
| [31] Art 5 list | Q56 | https://artificialintelligenceact.eu/article/5/ | confirmed | |
| [31] W2 "six times stricter" | W2 | arithmetic | corrected | 24×/6× |
| [31] rule of three → ~72 h | W2 | arithmetic | confirmed | |
| [35] £3 M Maven raise, >£5 M revenue | §0 | (vendor source removed) | confirmed | |
| [35] the vendor CCTV quotes | §0 | docs/research/33 | confirmed | repo-sourced |
| [35] "32 behaviours" | §1 | survsim/director/behaviours.py REGISTRY | corrected | 44 classes/49 names |
| [35] realism 12/14 from 2 | §1,Q31,§5 | docs/15 final table | corrected | 12/14 grid; 6/14 render check |
| [35] misses MTF/edge; night 4/14 | Q6 | docs/15 | corrected | temporal noise; night 3/14 |
| [35] 626 tests | §1,Q8,§5 | docs/11; pytest collect ~773 | corrected | "600+" |
| [35] 44 classes/49 names | Q2 | REGISTRY | confirmed | |
| [35] P .018/R .241; P .074/R .722; 5,580; hard-neg .295 | Q3 | docs/14 §3 | confirmed | |
| [35] AUC .46→.72 | Q4 | docs/14 | confirmed | |
| [35] Rotator bug; editor false success | Q5 | CLAUDE.md; docs/BUG_black_render.md | confirmed | |
| [35] AP .348/AP50 .730; OSNet .186; mock .008 | Q7 | docs/13 | confirmed | |
| [35] MOTA .463/IDF1 .538/HOTA .545 | Q7,§5 | docs/13; tracking.py | corrected | .466/.549/.434 |
| [35] HOTA definition | Q12 | https://arxiv.org/abs/2009.07736 | confirmed | |
| [35] 40-technique taxonomy | Q15 | survsim/director/evasion.py ALL | corrected | 52 |
| [35] i-LIDS 10 s, recall-biased F1 | Q16 | guide | confirmed | |
| [35] pipeline.py per-stage drops | Q21 | survsim/eval/pipeline.py | confirmed | |
| [35] 60 s dwell 0/2; PathLoiter R 1.0 P .133 | Q22 | docs/13 | confirmed | |
| [35] no i-LIDS loitering; six scenarios | Q22,§4 | brochure; guide text search | confirmed | |
| [35] thermal crossover; MAC randomisation | Q14, pitch | survsim/sensors/thermal.py, rf.py | confirmed | |
| [35] ONVIF-style metadata | Q26 | survsim/gt/video.py | confirmed | |
| [35] Calipsa → Motorola 2022 | §4 | https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-acquires-calipsa.html | confirmed | |
| [35] [person] CEO, Livingstone CTO; RCO/Leonardo/WB | §5 | docs/research/33 | confirmed | repo-sourced |
| [35] operator handles every alarm | Q38 | guide §5.1.2.3 | confirmed | |
| [35] SAPIENT BSI Flex 335, MOD C-UAS, "NATO adopting" | §6 Q8 | https://www.gov.uk/guidance/sapient-autonomous-sensor-system | corrected | evaluated as potential NATO std |
| [35] Thys 2019 cardboard patch | §6 Q11 | https://arxiv.org/abs/1904.08653 | confirmed | |
| [35] 1° at 1 km = 17 m | §6 Q14 | arithmetic | confirmed | |
| [35] late alarm "counts as a miss" | re-cut pitch | guide; CLAUDE.md principle 4 | corrected | false alarm |
| [35] RTSP jitter hundreds of ms | §6 Q14 | none | unverifiable | |
| [35] SNN mW vs W | §6 Q3 | none | unverifiable | |
| [35] JSP 936 / DEF STAN / NIST RMF | §6 Q12 | none this pass | unverifiable | |
| [35] BS 8418 scope | Q20 | none | unverifiable | |
| [35] Applied Intuition Dstl swarm award | §4 | none | unverifiable | |

### Reports 33, 34, 36

| claim | § | source URL | verdict | note |
|---|---|---|---|---|
| [33] Home page "future of AI in Defence", "more robust and accurate" | 0 | (vendor source removed) | confirmed | |
| [33] vendor lab CCTV false alarms/operator fatigue, border/CNI, loitering/tampering list, FR, media | 0,3,4 | (vendor source removed) | confirmed | |
| [33] Investor text "detect, identify, and track... multiple sensors" | 0 | Dealroom via search extract | confirmed | [F2], 403 direct |
| [33] 12211733, inc 17 Sep 2019 | 1 | https://find-and-update.company-information.service.gov.uk/company/12211733 | corrected | upgraded F2→F |
| [33] SIC 72190 | 1 | same | corrected | upgraded F2→F |
| [33] 1 Friar St, moved Aug 2025, law-firm address | 1 | officers + filing-history | corrected | Blandy Services secretary 14 Aug 2025 confirms; INF→F |
| [33] Accounts "total-exemption full", FY 30 Sep, filed 30 Jun 2025 | 1 | filing-history | corrected | CH labels them "full accounts"; exemption wording removed; FY2025 due 30 Sep 2026 |
| [33] PSCs [person]/Livingstone 25-50 %, Stringer ceased 22 Jan 2026 | 1 | .../persons-with-significant-control | confirmed | |
| [33] Directors [person] 2020, Livingstone 2019, Matthews 1 Jul 2026, Eccles-Williams 3 Aug 2026 | 1 | .../officers | confirmed | added that Livingstone is also secretary |
| [33] Stringer resigned 18 Jul 2024, Beldon 29 Aug 2025 | 1 | .../officers | confirmed | appointment dates added |
| [33] Subdivision 25 Oct 2024; allotments 16 Jun 2025, 1 Jul 2026, 9 Sep 2026; articles/resolutions 31 Jul 2026 | 1 | .../filing-history | confirmed | |
| [33] £3 M, Maven lead, first institutional round | 1 | (vendor source removed) | confirmed | |
| [33] Maven VCTs + Maven Cognition EIS + angels | 1 | Dealroom search extract | unverifiable | [F2]; hedged |
| [33] >£5 M revenue from MOD and primes | 1 | Dealroom search extract | unverifiable | [F2] tag kept |
| [33] Diligency maturity benchmarking, prototype→deployment | 1 | Diligency | confirmed | F2→F |
| [33] LinkedIn 2-10 headcount | 1 | none fetched | unverifiable | already [F2]/[INF] |
| [33] [person] bio (25 yrs, maths, CA, LBS MBA distinction, chairs OFTNAI) | 2 | (vendor source removed) | confirmed | "UAV payloads, machine vision" not re-seen |
| [33] Livingstone bio (30 yrs, Oxford DPhil biophysics/bioinformatics, OFTNAI trustee) | 2 | about-us | confirmed | Welsh/Scottish adviser not re-seen |
| [33] [vendor product] flagship, "unmatched real-world performance" | 3 | (vendor source removed) | confirmed | |
| [33] [vendor product] second-gen SNN, sovereign | 3 | (vendor source removed) | corrected | quote re-worded to the fetched text; low-shot/SWaP added |
| [33] [vendor product] MLOps + labelling/synthetics | 3 | what-we-offer, our-work | corrected | synthetics now [F] from Our Work |
| [33] ReconSphere WinTAK/QGIS/Socet GXP | 3 | what-we-offer | confirmed | |
| [33] [vendor product] fusion, C-UAS | 3 | what-we-offer | confirmed | |
| [33] Sensor list, edge "UAVs, effectors, C-UAS", "artificial stupidity" | 3 | what-we-offer, our-work | confirmed | |
| [33] WB Group announced 5 March 2025 at Polish embassy | 4 | (vendor source removed) | corrected | 5 Mar **2026**, London; Calibre article 12 Jun 2026 |
| [33] [vendor product] with RAF RCO; Ukraine data | 3,4 | (vendor source removed) | confirmed | vendor-sourced; hedged |
| [33] Leonardo partner, ADS member | 4 | not refetched | unverifiable | tagged [F2] already |
| [34] Calipsa London 2016, Motorola 19 Apr 2022, >90 % | 2 | https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-acquires-calipsa.html ; https://www.euronews.com/next/2022/04/19/motorola-m-a-calipsa | confirmed | |
| [34] Avigilon Motorola 2018 | 2 | FACTS_VERIFIED (Motorola PR) | confirmed | $1.0 bn added |
| [34] BriefCam Canon 2018 | 2 | FACTS_VERIFIED (global.canon) | confirmed | closed 3 Jul 2018 |
| [34] Ipsotek/Eviden, VCA, Genetec, Milestone/Canon, Verkada, Rhombus, SentryAI, Iveda, IronYun, Bosch/Axis | 2 | not fetched | unverifiable | already [VERIFY]-hedged (Ipsotek/VCA links not refetched) |
| [34] Spot AI ~$93–110 M | 2 | https://siliconangle.com/2024/10/31/spot-ai-reels-31m-ai-powered-video-processing-platform/ | corrected | $93 M as of Oct 2024; the $110 M upper figure is unsourced |
| [34] Coram A $13.8 M Jan 2025, B $35 M | 2 | https://www.coram.ai/post/coram-series-b-fundraise ; search (BusinessWire 403) | corrected | B = June 2026; $66 M total added |
| [34] Ambient Series B Apr 2025, ~155 staff | 2 | Tracxn via search | corrected | staff count hedged |
| [34] Hakimo 2020, $10.5 M A Mar 2025, $20.5 M, >100 clients | 2 | https://siliconangle.com/2025/03/27/hakimo-secures-10-5m-new-funding-launches-autonomous-ai-security-agent/ | confirmed | |
| [34] Actuate 95 %+ FP reduction | 2 | https://actuate.ai/ | confirmed | |
| [34] Actuate $10k reimbursement | 2,5 | search extract (securityinfowatch/sdmmag) | corrected | tag F→F2 |
| [34] Actuate Brivo/DICE, 20k cams/1,200 sites | 2 | SecurityInfoWatch PR (not present) | unverifiable | hedged |
| [34] Evolon up to 98.5 % FA reduction | 2 | https://www.evolontech.com/ | corrected | 90 %+ reduction; 98.5 % = accuracy |
| [34] Evolon Jemez/Los Alamos, Immix/UCC | 2 | evolontech.com | unverifiable | hedged |
| [34] DFUSION/KiwiVision NPSA CSE-listed | 2 | https://www.npsa.gov.uk/cse/dfusion | unverifiable | NPSA returned 403 |
| [34] i-LIDS scenarios, no loitering | 4 | FACTS_VERIFIED snippet-only (i-LIDS guide) | confirmed | snippet-grade only |
| [36] Gallego 140 dB vs 60 dB, µs | 2.1 | https://arxiv.org/abs/1904.08405 | confirmed | |
| [36] Prophesee 1MP: 14 h, 25 M boxes, raw events better | 2.1 | https://arxiv.org/abs/2009.13436 | confirmed | |
| [36] Speck 3.36 µs, 9 layers, 327k neurons, ASYNC 2023, edge-node quote | 2.2 | https://arxiv.org/abs/2304.06793 | confirmed | product page says 330k |
| [36] Speck <2 mW, <5 ms | 2.2 | https://www.synsense.ai/products/speck-2/ | confirmed | |
| [36] v2e 40 % night car detector | 2.4 | https://arxiv.org/abs/2006.07722 | confirmed | vs YOLOv3 on intensity frames |
| [36] Rueckauer 0.56 % MNIST, 11.18 % CIFAR-10, VGG-16/Inception-v3 first | 3 | https://www.frontiersin.org/articles/10.3389/fnins.2017.00682/full | confirmed | |
| [36] Bu et al. QCFS, 4 timesteps | 3 | https://arxiv.org/abs/2303.04347 | confirmed | |
| [36] Neftci/Mostafa/Zenke quote | 3 | https://arxiv.org/abs/1901.09948 | confirmed | |
| [36] Diehl & Cook 95 %, 6,400 neurons | 3 | https://www.frontiersin.org/articles/10.3389/fncom.2015.00099/full | confirmed | |
| [36] Spiking-YOLO 98 % of Tiny YOLO, 280× | 4.1 | https://arxiv.org/abs/1903.06530 | confirmed | |
| [36] SpikeYOLO 66.2/48.9, +15.0/+18.7, Gen1 67.2 +2.5, 5.7×, ECCV 2024 | 1,4.1 | https://arxiv.org/abs/2407.20708 | confirmed | |
| [36] E_MAC 4.6 pJ, E_AC 0.9 pJ, formulas | 4.2 | https://arxiv.org/html/2407.20708 | confirmed | |
| [36] YOLOv5 21.2 M 112.5 mJ 64.1 | 4.2 | same, Table 1 | confirmed | mAP50:95 45.4 added |
| [36] SpikeYOLO 23.1 M, 84.2 mJ, 66.2 % | 4.2,12 | same, Table 1 | corrected | 84.2 mJ row is 68.8 M params; 23.1 M 1×4 = 34.6 mJ, 62.3/45.5 |
| [36] "~25 % saving vs same-size ANN" | 4.2,10,Q3 | derived | corrected | 25 % for a 3× larger model; ~3× for same-size |
| [36] Loihi 2 "up to 10x faster", Lava, Hala Point 1.15 B, Kapoho Point 8-chip | 5 | https://www.intel.com/content/www/us/en/research/neuromorphic-computing.html | confirmed | |
| [36] Loihi 2 "asynchronous, brain-inspired research processor" | 5 | https://arxiv.org/abs/2310.03251 | confirmed | |
| [36] SpiNNaker2 ARM M4, SNN+DNN accel, 22 nm FDSOI, DVFS | 5 | https://arxiv.org/abs/2103.08392 | confirmed | |
| [36] Akida "up to 10x", milliwatts vs watts, CNN/SSM/TENN/RNN | 5 | https://brainchip.com/akida-generations/ | corrected | "watts" and RNN not found on page; reworded |
| [36] Orin Nano 34/67 TOPS 7–25 W, NX 117–157 TOPS 10–40 W | 5 | https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/ | confirmed | Super-mode note added (per FACTS) |
| [36] Loihi 2 vs Orin Nano PilotNet 0.09/13.72 mJ, 0.05/3.43 ms, EDP 0.11/47.08; >400× EDP | 6.1 | https://arxiv.org/html/2310.03251 | confirmed | paper also says >150× energy |
| [36] Audio denoise 28.74 vs 2143.35 mJ, 3.48 vs 95.35 ms | 6.1 | same | confirmed | |
| [36] "orders of magnitude gains... EDP" | 6.1 | https://arxiv.org/abs/2310.03251 | confirmed | |
| [36] Blouw KWS quote; CPU, GPU, TX1, Movidius | 6.1 | https://arxiv.org/abs/1812.01739 | confirmed | |
| [36] YOLO26n INT8 Orin NX 16GB 3.49 ms, excluding pre/post | 6.2 | https://docs.ultralytics.com/guides/nvidia-jetson/ | confirmed | |
| [36] García-Fernández & Yi OOSM retrodiction+update | 8.2 | https://arxiv.org/abs/2106.04898 | confirmed | |
| [36] CALC rows (87 mJ, 240 Wh/day, 0.048 Wh, 3,500×, 20×) | 5,6.2 | arithmetic | confirmed | |

### Reports 37, 38

| claim | § | source URL | verdict | note |
|---|---|---|---|---|
| [37] SapientMessage oneof: fields 4–12 (Registration…Error), nine types | 5.2 | https://github.com/dstl/SAPIENT-Proto-Files (bsi_flex_335_v2_0/sapient_message.proto) | confirmed | |
| [37] mandatory UTC google.protobuf.Timestamp | 4, 5.2 | same | confirmed | |
| [37] v7 moved XML→protobuf, ~60 % bandwidth cut | 5.1 | https://www.gov.uk/guidance/sapient-autonomous-sensor-system | confirmed | |
| [37] MOD adopted in 2019 C-UAS strategy | 5.1 | same | confirmed | |
| [37] TIE21 Nov 2021 >70 connections; TIE22 Sep 2022 31 nodes → 13 decision nodes | 5.1 | same | confirmed | |
| [37] three dstl repos | 5.1 | same | confirmed | |
| [37] BSI Flex 335 in effect 31 May 2023 | 5.1 | Readme.md in repo | confirmed | |
| [37] NodeType list (RADAR … LDEW, RFDEW, MOBILE, POINTABLE, FUSION) | 5.3 | registration.proto | confirmed | |
| [37] DetectionReport fields 1–16, 19; 17/18/20/21 reserved | 5.3 | detection_report.proto | corrected | fields 22 `colour` and 23 `id` were omitted; row added |
| [37] StatusReport System/StatusType/Power enums | 5.3 | status_report.proto | confirmed | |
| [37] Task Control, Command oneof, RegionType | 5.3 | task.proto | confirmed | |
| [37] Alert type/status/priority enums | 5.3 | alert.proto | confirmed | |
| [37] Location x/y/z_error and mandatory datum | 4 | location.proto | confirmed | |
| [37] Stone Soup tracker/associator/updater/metric class names (all ~30) | 3.2 | https://github.com/dstl/Stone-Soup | confirmed | every class grepped; EL particle filters exist as Single/MultiTargetExpectedLikelihoodParticleFilter |
| [37] no "MHT" class; PMHTTracker exists | 3.2 | tracker/pmht.py | confirmed | |
| [37] OSPAMetric subclasses GOSPAMetric; GOSPA switching term | 7 | metricgenerator/ospametric.py | confirmed | |
| [37] ChernoffUpdater formula / CI equivalence | 2 | updater/chernoff.py | confirmed | |
| [37] PDAHypothesiser: L = N·P_D/λ, miss = 1 − P_D·P_G | 3.3 | hypothesiser/probability.py L136-178 | confirmed | |
| [37] JPDA worked example numbers (d², L, 0.665/0.333, (0.92,0.15), (5.23,0.00), 0.438/0.557, (1.12,0.11), (4.75,0.13)) | 3.3 | re-derived (scratchpad script) | confirmed | every value reproduces |
| [37] coalescence pulls tracks 0.2–0.5 m | 3.3 | re-derived | corrected | 1.1 m / 1.25 m from the prediction |
| [37] 1° misalignment → 17.5 m at 1 km | 4 | arithmetic | confirmed | |
| [37] 1.5 m/s → 0.15 m; 20 m/s → 2 m in 100 ms | 4 | arithmetic | confirmed | |
| [37] Fortmann 1983, Reid 1979, Vo & Ma 2006 bibliographic details | 3.1 | — | unverifiable | not re-fetched; already flagged as search-listing-only in the doc |
| [38] JSP 936 V1.1, Nov 2024, 41 pp | 4.1 | https://assets.publishing.service.gov.uk/media/6735fc89f6920bfb5abc7b62/JSP936_Part1.pdf | confirmed | PDF created 14 Nov 2024 |
| [38] Preface paras 1–3 | 4.1 | same | confirmed | |
| [38] para 23 Def Stan 00-055 "currently only addresses ML" | 4.1, 4.4 | same | confirmed | |
| [38] paras 38, 39, 69, 74, 75, 76, 78 quotes | 4.2 | same | confirmed | |
| [38] para 79 "must cover … development environment" | 4.2 | same | corrected | the analysis "must be carried out"; the list is "should include" |
| [38] para 82, 89, 141–142, 146–147, 158, 160–163, 165, 167, 170–172, 177, 179–181 | 4.2 | same | confirmed | |
| [38] para 88 Table 1 escalation (Critical/Major/Moderate) | 4.2 | same | corrected | the table has Severe/Major → Defence-level and Moderate/Minor → TLB; it is an ethical-risk referral table |
| [38] AGX 275 = 170 GPU + 105 DLA sparse; 5.3 FP32 TFLOPS | 1.2 | https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf | confirmed | |
| [38] AGX 64 GB decode 22× 1080p30 and the list; 32 GB 18×; encode 16× | 1.3 | brief + product page | confirmed | |
| [38] AGX 32/64: 200/275 TOPS, 1792/2048 cores, 56/64 TC, 204.8 GB/s, 15–40/15–60 W | 1.1 | brief; https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/ | corrected | the current product page lists the 32 GB at 241 TOPS; note added |
| [38] Orin Nano 34/67 TOPS, 7–25 W | 1.1 | product page | corrected | Super-mode hedge added |
| [38] Orin NX 117/157 TOPS, 10–40 W | 1.1 | product page | corrected | Super-mode hedge added |
| [38] Orin NX 16 GB "1 DLA" | 1.1, Q1 | https://developer.nvidia.com/downloads/jetson-orin-nx-module-series-data-sheet | corrected | 2 on the 16 GB, 1 on the 8 GB |
| [38] Hailo-8 26 TOPS, 2.5 W typical | 1.1 | FACTS_VERIFIED row 258 | confirmed | via the verified table |
| [38] Thor 2070 FP4 TFLOPS, 40–130 W, 128 GB; Speck <2 mW | 1.1 | — | unverifiable | not re-fetched this pass |
| [38] 2:4 sparsity doubles throughput → ~85 dense TOPS | 1.2 | arXiv:2104.08378 (not re-fetched); arithmetic | confirmed | arithmetic |
| [38] TensorRT quotes (500 images, entropy calibrator required for DLA, batch advice, Q/DQ, kCALIBRATE_BEFORE_FUSION) | 2.1 | https://docs.nvidia.com/deeplearning/tensorrt/archives/tensorrt-861/developer-guide/index.html | confirmed | all verbatim |
| [38] symmetric scale max(\|x\|)/127 | 2.1 | same | confirmed | |
| [38] Nagel et al. PTQ quote | 2.1 | arXiv:2106.08295 | unverifiable | not re-fetched |
| [38] Ultralytics YOLO26n Jetson table (all 4 devices, versions, mAP, ms, sizes) | 2.2 | https://docs.ultralytics.com/guides/nvidia-jetson/ | confirmed | the AGX FP32/FP16 0.0450 anomaly is really on the page |
| [38] derived speed-ups and fps (1.98×/1.20×/263, 2.01×/1.18×/287, 1.25×/0.91×/658) | 2.2 | arithmetic | confirmed | |
| [38] TensorRT 10.3 / JetPack 6 INT8 FAQ issue | 2.2 | Ultralytics page | confirmed | |
| [38] stream budget 5×3.49 = 17.5 ms → 57 cameras | 2.4 | arithmetic | confirmed | |
| [38] NIST AI RMF 26 Jan 2023; GenAI profile 26 Jul 2024; CI concept note 7 Apr 2026 | 4.4 | https://www.nist.gov/itl/ai-risk-management-framework | confirmed | |
| [38] Jetson secure boot quotes (r36.4) | 3 | — | unverifiable | not re-fetched |
| [38] Orin NX decode 18× 1080p30 | 2.4 | product page | confirmed | matches FACTS_VERIFIED row 254 |
