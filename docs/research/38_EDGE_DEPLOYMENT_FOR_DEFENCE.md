# 38 · Edge deployment of computer vision for defence

**Why.** the vendor's pitch is ML that runs "on any platform": on field devices,
drones and counter-drone systems, "where visibility, data, or communications
are limited" (file 33). [vendor product] is their MLOps product: "rapid model training
and deployment, performance management of deployed models and retraining"
(file 33, [F]). This file covers edge hardware, compression with real numbers,
disconnected updates, **JSP 936** assurance clause by clause, adversarial
robustness, secure MLOps, and how SurvSim maps onto a [vendor product]-like product.
Background: `22_DEPLOYMENT_AND_OPERATIONS.md` and
`21_DATA_MLOPS_AND_GOVERNANCE.md`.

**Tags.**
* **[F]** read on the cited primary source on 2026-09-26. For JSP 936 I
  downloaded the gov.uk PDF (V1.1, Nov 2024, 41 pages), extracted the text and
  read the numbered paragraphs, so paragraph numbers below are exact.
* **[CALC]** my arithmetic from [F] numbers, with the working shown.
* **[INF]** my opinion or engineering practice. Say it as such.

No background-knowledge or secondary-extract tags remain. Claims I could not
source have been removed or turned into explicit opinions.

---

## 1. Hardware and SWaP

### 1.1 The menu

| Class | Example | Compute / power (fetched) | Fits **[INF]** |
|---|---|---|---|
| Micro / always-on | SynSense Speck | < 2 mW, DVS + SNN on one chip ([SynSense](https://www.synsense.ai/products/speck-2/)) **[F]** | wake-up, ground sensors (file 36) |
| Camera-class NPU | **Hailo-8** | 26 TOPS, "typical power consumption of 2.5W", memory on die, M.2/mPCIe/PCIe ([Hailo](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/)) **[F]** | analytics inside the camera or a small box |
| Small edge GPU | **Jetson Orin Nano** 4/8 GB | 34 / 67 TOPS (**Super** mode, JetPack 6.2; originally 20 / 40 TOPS at 7–15 W), 512-core Ampere, 16 Tensor Cores, 7–25 W, no DLA **[F]** | 1–4 streams at 720p, small drones |
| Mid edge GPU | **Jetson Orin NX** 8/16 GB | 117 / 157 TOPS (**Super** mode; originally 70 / 100 TOPS at 10–25 W), 1024 cores, 32 Tensor Cores, 2 DLAs on 16 GB and 1 on 8 GB (NX datasheet DS-10712), 10–40 W with Super **[F]** | 4–8 camera pole or box, C-UAS EO head |
| Large edge GPU | **Jetson AGX Orin** 32/64 GB | 200 / 275 TOPS INT8 (brief; the current product page lists the 32 GB at 241 TOPS), 1792 / 2048 CUDA cores, 56 / 64 Tensor Cores, 2× NVDLA v2.0, 204.8 GB/s, 15–40 W / 15–60 W **[F]** | vehicle or mast, multi-sensor fusion node |
| Next generation | **Jetson AGX Thor** | up to 2070 FP4 TFLOPS, 40–130 W, 128 GB ([NVIDIA Jetson modules](https://developer.nvidia.com/embedded/jetson-modules), fetched 2026-09-26) **[F]** | on-device VLM and transformer stacks |

Nano and NX rows: [NVIDIA Jetson Orin spec page](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/) **[F]**.
AGX row: the [Jetson AGX Orin technical brief](https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf) **[F]**.

### 1.2 Read the TOPS carefully

The AGX Orin brief is explicit about where "275 TOPS" comes from **[F]**:
* the GPU gives "up to 170 Sparse TOPs of INT8 Tensor compute", and
* the two DLAs give "up to 105 INT8 Sparse TOPs total".

170 + 105 = **275**, and both halves are **sparse** figures **[CALC]**. NVIDIA's
Ampere sparse Tensor Cores exploit a "2:4 (50%) sparsity pattern that leads to
twice the math throughput of dense matrix units"
([Mishra et al., arXiv:2104.08378](https://arxiv.org/abs/2104.08378)) **[F]**.
So a dense INT8 model on the AGX Orin GPU sees about 85 TOPS, not 275
**[CALC]**. The same brief gives 5.3 FP32 TFLOPS of CUDA compute **[F]**.
Divide a TOPS headline by two for dense models, and then remember that small
detectors are usually memory-bound, not compute-bound. **[INF]**

### 1.3 Video decode is often the real limit

The AGX Orin 64 GB decodes **1× 8K30, 3× 4K60, 7× 4K30, 11× 1080p60 or
22× 1080p30 (H.265)**, and the 32 GB version 18× 1080p30. Encode is up to
16× 1080p30 H.265 on the 64 GB **[F]** (AGX Orin brief, spec table). For a
multi-camera box the question is often "how many RTSP streams can I decode",
before it is "how many can I infer" (section 2.4). **[INF]**

### 1.4 SWaP-C reality **[INF]**

* Heat is often the limit, not TOPS. A sealed IP67 box in the sun throttles,
  so benchmark at 50 °C ambient in the power mode you will ship, not at
  `nvpmodel -m 0` on a bench.
* Power comes from batteries or solar on remote sensors, and from the
  airframe's budget on drones.
* Defence programmes also care about supply lifetime and export status. That
  is a procurement question to ask the customer, not something to assert.

## 2. Model compression: what the numbers really are

### 2.1 INT8 post-training quantisation (PTQ)

* The Qualcomm white paper concludes that "in most cases, PTQ is sufficient
  for achieving 8-bit quantization with close to floating-point accuracy", and
  that quantisation-aware training (QAT) is needed for lower bit-widths
  ([Nagel et al., arXiv:2106.08295](https://arxiv.org/abs/2106.08295)) **[F]**.
* **How TensorRT does it** (TensorRT 8.6 developer guide,
  [NVIDIA docs](https://docs.nvidia.com/deeplearning/tensorrt/archives/tensorrt-861/developer-guide/index.html)) **[F]**:
  * Quantisation is symmetric. The weight scale is
    `s = max(|x_min|, |x_max|) / 127`, per tensor.
  * For activations TensorRT runs "representative input data" through the
    network "to collect statistics for each activation tensor". The guide says
    "experiments indicate that about 500 images are sufficient for calibrating
    ImageNet classification networks".
  * Choosing a scale means "balancing two sources of error": discretisation
    error and truncation (clipping) error.
  * **`IInt8EntropyCalibrator2`** "chooses the tensor's scale factor to
    optimize the quantized tensor's information-theoretic content, and usually
    suppresses outliers in the distribution. This is the current and
    recommended entropy calibrator and is required for DLA."
  * Batch matters: "calibrating using multiple small batches of calibration
    data may result in reduced histogram resolution and poor scale value", so
    "calibrate with as large a single batch as possible, and ensure that
    calibration batches are well randomized".
  * Two routes to INT8: **implicit** quantisation (a scale per tensor, from
    calibration or `setDynamicRange`) and **explicit** quantisation, where
    "conversion to/from INT8 type requires an explicit Q/DQ layer", as
    produced by QAT.
  * Calibration happens before layer fusion by default. The
    `kCALIBRATE_BEFORE_FUSION` flag exists because DLA fusion patterns can
    differ.

**The trap [INF].** "500 images" was measured for *ImageNet classification*.
A surveillance detector needs the calibration set to span the operating
envelope: night, IR, rain, fog, glare. If it doesn't, the entropy calibrator
clips exactly the activation ranges that occur at night, and the accuracy loss
lands where it hurts. SurvSim's degradation profiles make a good generator of
*envelope-balanced* calibration sets, and JSP 936 para 160 (verification data
must cover "the breadth of the ODD including edge cases") asks for the same
coverage for verification.

### 2.2 Worked table: INT8 on Orin for a YOLO-class detector

Ultralytics' Jetson benchmarks for **YOLO26n**, 640 px, TensorRT, inference
time excluding pre- and post-processing. The mAP is on **COCO128**, a 128-image
subset, which is noisy
([Ultralytics NVIDIA Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/)) **[F]**:

| Device (Ultralytics version) | FP32 mAP50-95 / ms | FP16 mAP50-95 / ms | **INT8** mAP50-95 / ms | Size FP32 → INT8 |
|---|---|---|---|---|
| Orin Nano Super dev kit (8.4.33) | 0.4770 / 7.53 | 0.4800 / 4.57 | **0.4490 / 3.80** | 11.3 → 5.3 MB |
| Orin NX 16 GB (8.4.33) | 0.4770 / 7.01 | 0.4789 / 4.13 | **0.4489 / 3.49** | 11.4 → 5.5 MB |
| AGX Orin 64 GB (8.4.32) | *0.0450* / 4.18 | *0.0450* / 2.62 | **0.4640 / 2.30** | 11.5 → 5.4 MB |
| AGX Thor dev kit (8.4.7) | 0.4791 / 1.90 | 0.4797 / 1.39 | **0.4273 / 1.52** | 13.9 → 6.5 MB |

Derived numbers **[CALC]**:

| Device | INT8 speed-up vs FP32 | INT8 vs FP16 | INT8 mAP loss vs FP16 (points) | INT8 throughput (inference only) |
|---|---|---|---|---|
| Orin Nano Super | 1.98× | 1.20× | **−3.1** | ~263 fps |
| Orin NX 16 GB | 2.01× | 1.18× | **−3.0** | ~287 fps |
| AGX Thor | 1.25× | **0.91× (slower)** | **−5.2** | ~658 fps |

**What the table actually says [INF].**
1. **FP16 is nearly free and INT8 is not.** On a nano-size model, INT8 costs
   about **3 mAP points** against FP16 on Orin Nano and NX with default PTQ,
   for only a 1.2× speed-up over FP16. The folklore "0–1 mAP at INT8" does not
   hold for this model with this toolchain. Small, already-efficient models
   have less redundancy to absorb quantisation noise.
2. **On Thor, INT8 is *slower* than FP16** (1.52 vs 1.39 ms) and loses 5
   points. Newer hardware with fast FP16/FP8/FP4 paths changes which precision
   is best. Measure; don't assume.
3. **The AGX Orin FP32/FP16 rows are obviously broken** (mAP 0.045 while
   INT8 is 0.464). The page gives no explanation. (Its FAQ does describe a
   TensorRT 10.3 issue on JetPack 6 that disables NMS-free *INT8* exports
   **[F]**, which is a different symptom.) Whatever the cause, a published table with a 10× accuracy collapse shows why you
   re-validate accuracy on the target after every export, not just latency.
4. **Latency excludes pre- and post-processing.** At 720p, resize and
   normalise on the CPU can cost as much as the inference unless you do it on
   the GPU or VIC.

**My deployment choice [INF].** Default to FP16 on Orin for nano and small
detectors. Go to INT8 only with QAT or a calibration set balanced across the
ODD, and only if the stream count needs the extra 20 %. Put the DLA to work on
a second model (for example ReID or a classifier) rather than squeezing the
detector.

### 2.3 Pruning, sparsity and distillation

* **Pruning plus quantisation.** Deep Compression shrank AlexNet 240 MB →
  6.9 MB (35×) and VGG-16 552 MB → 11.3 MB (49×). Pruning alone gave 9–13×
  fewer connections, with 3–4× layer-wise speed-up and 3–7× better energy
  efficiency ([Han et al., arXiv:1510.00149](https://arxiv.org/abs/1510.00149)) **[F]**.
* **Structured sparsity.** The speed-up that GPUs actually deliver comes from
  hardware-supported patterns. Ampere's 2:4 pattern gives "twice the math
  throughput of dense matrix units", and the authors present a training recipe
  that makes it "easy to prepare accurate models" for it
  ([Mishra et al., arXiv:2104.08378](https://arxiv.org/abs/2104.08378)) **[F]**.
  Unstructured sparsity generally doesn't map onto that hardware path. **[INF]**
* **Distillation.** Hinton et al. showed "it is possible to compress the
  knowledge in an ensemble into a single model which is much easier to deploy"
  ([arXiv:1503.02531](https://arxiv.org/abs/1503.02531)) **[F]**. The practical
  recipe: a big teacher (an open-vocabulary detector or VLM, run offline)
  labels synthetic and real data, and a small student runs at the edge **[INF]**.

### 2.4 Worked example: stream budget on one Orin NX 16 GB **[CALC]**

Goal: how many 720p cameras can one Orin NX serve at a useful rate?

* INT8 inference: 3.49 ms per frame (table above).
* Detect at 5 fps per camera and track (Kalman prediction) at 25 fps, which
  is cheap: 5 × 3.49 ms = 17.5 ms of GPU time per camera-second.
* Inference-bound ceiling: 1000 / 17.5 ≈ **57 cameras**. That number is
  meaningless, because:
  * pre- and post-processing are excluded (assume ×2 → ~28);
  * ReID on new tracks and a second model share the GPU (→ ~15–20);
  * decode: the NX's decoder has to handle every stream at its *native* frame
    rate, not 5 fps.
* **Rule of thumb [INF]:** 8 cameras per Orin NX at 720p with a detector,
  tracker and ReID is comfortable. That matches the "Orin NX per 4–8 cameras"
  sizing in file 37's CNI design, with headroom for thermal throttling.

**Resolution and frame-rate budgeting often beat all the compression above
[INF]:** motion-gated person tiles or ROIs, detection at 5 fps and tracking at
25 fps, and heavy ReID only on new tracks.

### 2.5 Edge budget worked example — streams per Orin NX 16 GB (2026-09-27)

Closes 68 Q10. Every input is tagged **[V]** (primary source fetched
2026-09-27) or **[A]** (assumption/estimate — measure in week one). Nothing
here was measured on a Jetson by us.

**Inputs**

| # | Input | Value | Tag / source |
|---|---|---|---|
| 1 | NX 16 GB AI performance | 157 sparse INT8 TOPS (Super); GPU tensor cores **77 sparse / 38 dense** INT8 TOPS, rest is 2× DLA | [V] [NVIDIA Jetson Orin spec table](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/) |
| 2 | Power modes | 10 / 15 / 25 / 40 W (40 W = Super/MAXN) | [V] same table |
| 3 | Decode | **18× 1080p30 H.265** (NX 16 GB and 8 GB share the column); also 9× 1080p60, 4× 4K30, 1× 8K30 | [V] same table. The "23×" in that row is **AGX Orin Industrial**, not NX |
| 4 | YOLO26n TensorRT INT8, 640, NX 16 GB | **3.49 ms/im** (FP16 4.13) | [V] [Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/), reComputer J4012, Ultralytics 8.4.33 (vendor-of-model, not NVIDIA) |
| 5 | YOLO11n in DeepStream, INT8, 640, NX 16 GB | **4.54 ms/im** (FP16 5.27) | [V] [Ultralytics DeepStream guide](https://docs.ultralytics.com/guides/deepstream-nvidia-jetson/), JP 5.1.3 |
| 6 | YOLO11s INT8, 640, NX 16 GB | 6.05 ms/im (165 fps) | [V] Ultralytics DeepStream guide FAQ |
| 7 | NVIDIA-published YOLOv8n/v8s INT8 fps on Orin NX | **none found** — jetson-benchmarks has only MLPerf on NX (RetinaNet 66.5 samples/s, ResNet-50 2,640/s offline); DS_Performance lists AGX Orin/Thor, not NX | [V] absence: [jetson-benchmarks](https://developer.nvidia.com/embedded/jetson-benchmarks), [DS_Performance](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html) |
| 8 | YOLOv8n vs YOLO11n cost | ≈ 1.3× (8.7 vs 6.5 GFLOPs) | [A] Ultralytics model cards; FLOPs ≠ latency |
| 9 | 1280 input vs 640 | ≈ 4× latency (4× pixels) → ~18 ms/im for an n-model | [A] |
| 10 | OSNet x1.0 on ~10 crops/s/camera | ~1 ms/crop batched → ~10 ms GPU per camera-second | [A] (OSNet ~1 GFLOP at 256×128) |
| 11 | ByteTrack | CPU, ≪ 1 ms/frame/camera; 18 cams × 25 fps fits in < 1 of 8 A78AE cores | [A] |
| 12 | Usable GPU | 70 % of each second (30 % for pre/post, OSD, thermal) | [A] |
| 13 | Accuracy cost of FP16 / INT8 on our detector (h14b yolov8n, MOT20-02 AP@640) | FP16 **−0.0000** (range −0.0003..+0.0002); INT8 static PTQ (MinMax) **−0.0117** (range −0.0154..−0.0081 over 3 checkpoints; s2 misses the 0.015 bar) — mostly AP75 (−0.030), AP50 only −0.0002..−0.0042; synthetic-calibrated INT8 −0.0132. **H43: Percentile calibration (99.999) is a free, drop-in improvement over MinMax** — AP75 loss −0.0302→−0.0174 on the same 3 checkpoints (recovery 0.42, over the 5-checkpoint corpus 0.415), 0/5 checkpoints regressed — but recovers under half the AP75 loss, short of the pre-registered 0.50 bar, so INT8 export still costs roughly half of H38's original AP75 loss even with better calibration. **H43b (full 5-checkpoint QAT): recovery 0.366 [all 5]/0.334 [h14b-only], both < the 0.50 secondary and 0.80 primary bars — QAT underperforms Percentile PTQ**, because export re-quantizes with plain MinMax instead of keeping QAT's learned ranges. **H43c (fix: export the QDQ graph from the QAT observers' learned ranges via onnxruntime `TensorQuantOverrides`, no re-fine-tuning): recovery rises to 0.439, still < both bars** — the learned-range mechanism is now [V] verified working (ranges verified carried into the exported graph on 5/5 checkpoints), the residual shortfall is *inferred* to sit in the recipe (150 iterations), not the export path — not itself measured (proposed as H43d: more QAT iterations, same learned-range export) — but the net conclusion is unchanged: **ship FP16 (free); INT8 PTQ costs ~0.012 AP, mostly AP75; Percentile calibration recovers ~41 % of the AP75 loss and QAT with a range-preserving export ~44 % — neither reaches the 50 % bar; use INT8 only where AP75 (box tightness) does not drive the alarm; nothing measured on a Jetson**. **H43d (600 QAT iterations instead of 150, same learned-range export): the "more iterations closes the gap" inference is refuted, not confirmed** — pooled AP75 recovery *fell* to 0.374 (from H43c's 0.439), and the effect is checkpoint-recipe-dependent, not uniform: the 3 h14b checkpoints improved (up to 0.782) while both H51 `dose300` checkpoints got worse, one going negative (`int8_qat_qdq` costing *more* AP75 than plain MinMax PTQ). This does not change the recommendation — it strengthens it: QAT (in every variant tried — plain re-export, learned-range export, more iterations) has never beaten Percentile PTQ, and more QAT training is not a safe knob (it can make a specific checkpoint worse, not just less good). Longer QAT (600 it) does not help and hurts two checkpoints (H43d) — remaining loss is INT8 quantisation of this architecture, not the fine-tune | [V] measured, onnxruntime CPU QDQ (H38, H43, H43b, H43c, `32` §H38/§H43/§H43b/§H43c, AUDIT_H38) — **not** TensorRT on a Jetson; TRT INT8 kernels/calibrator can differ. No Jetson latency measured |

**Arithmetic** (GPU ms per camera-second = det fps × det ms + ReID 10 ms;
cameras = 700 / that, then capped by decode):

| Config (n-model, INT8, DeepStream 4.54 ms basis) | ms / cam-s | Compute cap | Decode cap (25 fps H.265 1080p) | **Streams/node** |
|---|---|---|---|---|
| 640, detect 5 fps | 32.7 | 21 | 18–21 | **18** (decode-bound) |
| 640, detect 10 fps | 55.4 | 12.6 | 18–21 | **12** |
| 640, detect 25 fps | 123.5 | 5.7 | 18–21 | **5** |
| 1280, detect 5 fps | 100.8 | 6.9 | 18–21 | **6–7** |
| 1280, detect 25 fps | 464 | 1.5 | — | **1** |
| YOLOv8n instead (×1.3 [A]), 640 @ 5 fps | 39.5 | 17.7 | 18–21 | **17** |

**Conclusion.** "18 streams" is right as the **decode ceiling** [V] and is
reachable only if detection runs at ≤ 5 fps at 640 with tracker
interpolation. The defensible planning number for our pipeline
(640 at 10 fps, far-field 1280 tiles only on the far band, ReID on ~10
crops/s) is **~10–12 cameras per NX at 40 W**, so a 40-camera site needs
**4 NX** (3 only if detection drops to 5 fps). Full-rate 1280 detection is
not an NX workload. This supersedes §2.4's "8 is comfortable" rule of thumb
as the worked case; 8 remains the conservative figure at 25 W. Row 13 means INT8 costs ~0.012 AP (~2.4 %) on our
detector, almost all box tightness (AP75), so INT8 is not free — plan for it or ship FP16
(≈ 1.16–1.18× the INT8 latency, rows 4–5). The sizing survives FP16: at the DeepStream FP16
5.27 ms, 640 @ 10 fps is 62.7 ms/cam-s → 700/62.7 ≈ 11 cameras, still inside 10–12 [INF on rows 5, 10, 12]. Inputs 8–12
are [A] until measured with `trtexec` and a DeepStream multi-stream run.

## 3. Model updates in disconnected or contested environments **[INF]**

```
  ┌──────────── accredited base (OFFICIAL-SENSITIVE / SECRET) ────────────┐
  │ data lake (versioned) → train (pinned containers) → eval harness       │
  │        ▲                        │ (SurvSim scenario grid + real hold-out)│
  │        │                        ▼                                       │
  │  returned artefacts      signed bundle = {model.plan, pre/post config,  │
  │  (crops, embeddings,       thresholds, ODD manifest, data-manifest hash,│
  │   alarm clips + verdicts)  eval report, model card}  + signature        │
  └────────▲───────────────────────────┬───────────────────────────────────┘
           │ opportunistic sync /      │ courier media / low-bandwidth delta
           │ courier                   ▼
  ┌────────┴──────────────── edge device (Orin, secure boot) ───────────────┐
  │ verify signature + version (no downgrade) → shadow-run new model beside  │
  │ old → compare alarm rate and score drift → promote or roll back          │
  │ ODD monitor: brightness, blur, IR/EO mode, score histograms, alarms/hour │
  └──────────────────────────────────────────────────────────────────────────┘
```

* **Signed, versioned model bundles.** The device refuses unsigned or
  downgraded bundles.
* **Delivery.** Physical media on air-gapped sites. Opportunistic sync over
  constrained links, using delta updates and small adapters instead of full
  weights.
* **A/B and rollback on the device.** Keep the previous model, run the new one
  in shadow mode first, and compare alarm rates before promoting it.
* **Data return.** A disconnected device can't stream raw video home. Log
  compact artefacts instead: embeddings, low-confidence crops, alarm clips
  plus the operator verdict. That is what feeds the next training round.
* **Drift monitors on the device.** These are required, not optional, under
  JSP 936 paras 179–180 (section 4.3).

**Platform support [F].** Jetson secure boot "prevents execution of
unauthorized boot codes through the chain of trust", with PKC keys held in
"write-once-read-multiple fuse devices". The same security documentation
covers disk encryption, an OP-TEE trusted execution environment, secure
storage and rollback protection
([Jetson Linux r36.4 Secure Boot](https://docs.nvidia.com/jetson/archives/r36.4/DeveloperGuide/SD/Security/SecureBoot.html)) **[F]**.
Rollback protection on the boot chain is the hardware analogue of the "no
downgraded model bundle" rule. **[INF]**

## 4. Assurance: JSP 936, clause by clause

### 4.1 What it is

**JSP 936 Part 1 (Directive), "Dependable Artificial Intelligence (AI) in
Defence"**, published 13 November 2024; the PDF is V1.1, 41 pages
([gov.uk publication page](https://www.gov.uk/government/publications/jsp-936-dependable-artificial-intelligence-ai-in-defence-part-1-directive);
[PDF](https://assets.publishing.service.gov.uk/media/6735fc89f6920bfb5abc7b62/JSP936_Part1.pdf)) **[F]**.

* **Preface para 1:** it "mandates the application of ambitious, safe and
  responsible practices relating to all Defence projects that include
  Artificial Intelligence", is aligned to the Government Technology Code of
  Practice, and will be reviewed "at least every two years" **[F]**.
* **Preface para 2:** two parts. Part 1 is the Directive ("must be
  followed"); Part 2 is Guidance ("best practice") **[F]**. The gov.uk page
  lists only Part 1 **[F]**.
* **Preface para 3:** "must" means compulsory; "should" means recommended
  good practice, applied "as far as possible in the relevant context" **[F]**.
* **Para 23:** "The primary standard for software is **Def Stan 00-055**
  Requirements for Safety of Programmable Elements (PE) in Defence Systems".
  It notes that 00-055 "currently only addresses ML", and that **Def Stan
  00-056** (Safety Management Requirements for Defence Systems) "is also
  relevant" **[F]**.
* **The five ethical principles** are the section headings: **Human
  Centricity, Responsibility, Understanding, Bias and Harm Mitigation,
  Reliability** **[F]**.

### 4.2 The paragraphs an ML engineer actually has to satisfy

| Para | What it says (quoted or close paraphrase) **[F]** | What I would produce **[INF]** |
|---|---|---|
| **38** | "The ODD for the AI should be identified and include information about its context of use" | ODD document: light, weather, range, camera height, crowd density, behaviours |
| **39** | AI-containing systems "must be clearly identified as such" | labelled UI; model card |
| **69** | "An analysis of data, AI learning algorithms and models must be made for unwanted bias that may lead to unintentional harms" | per-subgroup detection rates (clothing, skin tone, gait aids) from SurvSim's population generator plus real hold-out |
| **74** | AI "cannot be expected to be reliable outside the operating context for which it is designed (its ODD)" and "cannot be guaranteed to produce error-free behaviour when inside its ODD" | explicit residual-error statement |
| **75** | the operating context "must be clearly defined"; constraints "may be geospatial, temporal, or functional" | zones, hours, modes in the deployment config |
| **76** | performance targets "must be clearly defined … and demonstrated to a level of confidence that is commensurate with the risk" | alarm-rate and recall targets with confidence intervals |
| **78** | "Appropriate response to reasonably expected inputs outside of the intended design must be defined and demonstrated" | out-of-ODD detection → degrade to "capability reduced" state (the SAPIENT `StatusReport`, file 37) |
| **79–80** | security threat and vulnerability analysis "must be carried out" and "should include the development environment, supply chains, data chains"; guards and mitigations must be in place | SBOM, signed bundles, data-manifest hashes (section 6) |
| **82** | failure-mode analysis "must be carried out"; "inter-system emergent effects and cascaded failures must be considered" | FMEA including tamper, blinding and adversarial patches |
| **88** | "Each AI use case must be given an overall risk rating", based on residual risk; Table 1 (ethical-risk referral) escalates **Critical** to 2PUS (Ministers by exception), **Severe/Major** to Defence-level oversight (e.g. JROC/IAC), **Moderate/Minor** to TLB level with delegation | know where your project sits |
| **89** | special attention applications: "AI in kinetic effects" and "AI in novel and contentious applications" | a CCTV intruder analytic is neither, but a C-UAS cueing chain that feeds an effector might approach the first |
| **141–142** | a Hazard Analysis "must be undertaken"; new hazards from AI "must be passed back up" | hazard log entries for the vision component |
| **146–147** | sparse or missing data needs mitigation; set-aside data must be curated "for sufficiently independent verification confidence" | a sealed real-world test set never used for tuning |
| **158** | "Separate training, test and verification data must be produced … maintained independently" | three splits, with hashes |
| **160** | verification data should "address the breadth of the ODD including edge cases that sit inside, on, and beyond the boundary conditions" | SurvSim scenario grid *explicitly* sampling the ODD boundary |
| **161–162** | "Data provenance must be assured and recorded from the point of collection to ingestion"; all data under configuration management | data manifests; DVC/lakeFS-style versioning |
| **163** | synthetic data must be validated "from the perspective of the AI … because AI can cue on different features of the data than a human" | sim-to-real checks: feature statistics and transfer tests, not just "looks realistic" |
| **165–166** | models "must be accompanied by relevant information … assumptions, dependencies, known errors and weaknesses", including the ODD; re-use requires the risk owner to understand them | model card per release |
| **167** | models should "provide measures of uncertainty that are understandable" | calibrated scores; reliability diagrams |
| **170–171** | V&V "must include demonstration across the ODD including boundary conditions and realistic edge cases"; safe behaviour outside the ODD "must be demonstrated" | scenario-grid coverage map with metrics per cell |
| **172** | after updates, V&V "must include testing for both existing and new behaviours", to rule out "catastrophic forgetting and model drift" | regression suite on every model bundle |
| **177** | "The approved ODD … must be clearly defined in the operating context" | the ODD manifest shipped inside the bundle |
| **179–180** | the operational environment "must be monitored" to stay within the ODD; performance "must be monitored" | on-device drift monitors, alarms-per-hour against baseline |
| **181** | where AI is intended for modification, procedures "must be in place to ensure the continued assurance" | the signed update pipeline of section 3 |

Para 160's "inside, on, and beyond the boundary conditions" is the single
strongest argument for a simulator in a defence ML pipeline: real data cannot
be commissioned at the ODD boundary on demand, and synthetic data can. Para
163 is the matching caution: synthetic data has to be validated from the
model's point of view. **[INF]**

### 4.3 How SurvSim produces JSP 936 evidence **[INF]**

* **ODD as a scenario grid** (paras 38, 75, 177): light × weather × range ×
  camera height × crowd density × behaviour, each cell with metrics. The
  result is a coverage map that says where the model was validated.
* **Boundary and beyond-boundary cases** (paras 160, 170, 171): sweep each
  axis past the ODD edge and show the "capability reduced" behaviour.
* **Hard-negative suites** (para 76): measured false-alarm rates with
  confidence intervals, which the performance targets need.
* **Determinism** (paras 161–162): seeded runs make every number reproducible
  for audit.
* **The tamper and degradation catalogue** (paras 78, 82): effectively a
  structured hazard list for the vision component.
* **What it cannot do** (para 163): prove sim-to-real transfer. That needs a
  real verification set, per para 158.

### 4.4 Other frameworks

* **NIST AI RMF 1.0**, released 26 January 2023, organised around **Govern,
  Map, Measure, Manage**. The Generative AI Profile followed on 26 July 2024.
  On 7 April 2026 NIST announced a concept note for an AI RMF Profile on
  Trustworthy AI in **Critical Infrastructure**, to "guide critical
  infrastructure operators towards specific risk management practices"
  ([NIST](https://www.nist.gov/itl/ai-risk-management-framework)) **[F]**.
  That last one bears directly on CNI intrusion products.
* **Def Stan 00-055 / 00-056.** As JSP 936 para 23 says, 00-055 is the
  primary software safety standard and "currently only addresses ML".
  Awareness level is enough: "I'd work with the safety engineer on the ML part
  of the safety argument, especially data coverage." **[F]** for the
  reference, **[INF]** for the stance.

## 5. Adversarial robustness

* **Adversarial patches.** Brown et al. showed "universal, robust, targeted"
  printable patches that make classifiers ignore the rest of the scene
  ([arXiv:1712.09665](https://arxiv.org/abs/1712.09665)) **[F]**. Thys et al.
  attacked **person detection** in surveillance with a small cardboard patch
  held in front of the body, the first attack on a class as variable as
  people ([arXiv:1904.08653](https://arxiv.org/abs/1904.08653)) **[F]**.
* **Certified defences.** PatchGuard uses small receptive fields to limit how
  many features a patch can corrupt, then robust masking; the authors can
  "prove the robustness of our defense against any adversary within our threat
  model" (classification on ImageNet, ImageNette and CIFAR-10;
  [Xiang et al., arXiv:2005.10884](https://arxiv.org/abs/2005.10884)) **[F]**.
  Note that this is for *classifiers*. Certified patch defence for detectors
  is a harder, less mature problem. **[INF]**
* **Physical evasion is also low-tech [INF]:** thermal blankets against IR,
  crawling, umbrellas, blinding or tampering with the camera. SurvSim's
  evasion taxonomy (40 techniques) and its 6 tamper kinds belong here.
* **Defences in a real system [INF]:**
  * **Multi-sensor fusion.** A patch that fools the EO detector does not fool
    radar or thermal. This is the strongest practical defence and a good
    reason to fuse (file 37).
  * **Temporal consistency.** A person who vanishes mid-track with no
    occlusion is itself an anomaly: alarm on "track lost in open ground".
  * **Patch augmentation in training**, plus certified defences where the
    model is a classifier (for example a second-stage person verifier).
  * **Red-team in simulation.** Render patched textures on agents and measure
    the detection-rate drop. That is also JSP 936 para 79 threat analysis in
    practice.
* **Data poisoning and supply chain [INF].** Check training-data provenance and
  hash the manifests (JSP 936 para 161). Don't pull pretrained weights from
  unvetted hubs without scanning and re-validating them.

## 6. Secure MLOps for defence **[INF]**

* Segregated environments by classification. Training on OFFICIAL-SENSITIVE
  or SECRET data happens on accredited infrastructure. Code and synthetic data
  flow *up* more easily than real data flows *down*, which is one more reason
  synthetic data matters.
* Reproducible pipelines: pinned containers, a data-version manifest,
  experiment tracking, and a model card plus eval report per release (JSP 936
  paras 162, 165).
* An SBOM for the inference container, signed artefacts, and a minimal attack
  surface on the device: read-only root filesystem, secure boot, encrypted
  model at rest (section 3's Jetson features).
* A human-in-the-loop label store: every operator verdict is versioned and
  attributable (JSP 936's Responsibility principle).

## 7. What an "MLOps + synthetic data" product ([vendor product]-like) needs, and SurvSim's mapping

**[INF] I don't know [vendor product]'s internals. This is what such a product would
need, mapped to JSP 936 where a paragraph applies.**

| Need | Why | JSP 936 | SurvSim today | Gap |
|---|---|---|---|---|
| Scenario authoring at scale | real defence data is scarce or classified; rare events never recur | 146, 160 | YAML scenarios, scene and population generators, 49-name behaviour catalogue | no GUI; no geo-specific terrain import |
| Pixel-perfect GT | labels are free and exact | 161 | MOT / parquet / JSONL, mask-derived boxes, keypoints, COCO export | Unreal render path blocked on the engine (CLAUDE.md) |
| Multi-sensor | fusion products need joint data | — | EO + degradation, thermal, RF, audio | radar, event camera, aerial view |
| Hard negatives | precision is meaningless without them | 76 | paired innocent behaviours (`commute_wait` vs `loiter`) | animal, bird and vehicle negatives |
| Synthetic-data validation | AI cues on different features than humans | 163 | degradation, recolour, lens models; realism checks | no measured sim→real transfer yet (files 24, 30) |
| Evaluation harness | customers buy operational metrics | 76, 170 | alarms per camera-hour, i-LIDS timing, HOTA/IDF1 validated on MOT20 | GOSPA/SIAP for fused tracks (file 37) |
| Reproducibility / audit | evidence must be repeatable | 162 | seeded `RngHub`, deterministic runs, a large test suite | model-card and report generator |
| Edge loop | train → compress → deploy → monitor | 172, 179–181 | none (research code) | precision-aware eval (section 2.2), drift monitors |

**One-line mapping.** SurvSim is the *data generation plus evaluation* half
of a [vendor product]-like system. The MLOps half (registry, deployment, monitoring) is
standard tooling I'd plug in, not reinvent.

## 8. Interview answers (8 Q&As)

**Q1. Which Jetson would you put on a 6-camera perimeter pole, and why?**
A. An Orin NX 16 GB: 157 TOPS on the (Super-mode, sparse) headline, 10–40 W, and two DLAs for a
second model. YOLO26n runs at about 3.5 ms at INT8 and 4.1 ms at FP16 there,
so detection at 5 fps across 6 cameras is a few percent of the GPU. The real
limits are decode, pre-processing and thermal throttling in a sealed box, so
I'd size for about 8 cameras and benchmark at 50 °C in the shipped power mode.

**Q2. Does INT8 cost accuracy?**
A. It depends on the model and the calibration. Ultralytics' own Jetson
numbers for YOLO26n show INT8 about 3 mAP points below FP16 on Orin Nano and
NX, for only a 1.2× speed-up, and on Thor INT8 is actually slower than FP16.
The Qualcomm white paper says PTQ is usually close to float at 8 bits, but
that is an average over models, and small detectors are more sensitive. So I
default to FP16, and use INT8 with QAT or an ODD-balanced calibration set
when the stream count needs it.

**Q3. How does TensorRT INT8 calibration work, and what goes wrong?**
A. Symmetric quantisation. Weights take max-abs over 127. Activations get
scales from running representative data through the network and, with the
recommended entropy calibrator, picking the scale that best preserves the
distribution's information while suppressing outliers. NVIDIA suggests about
500 images for ImageNet classification. What goes wrong is coverage: calibrate
on daytime images and the night-time activation ranges get clipped. Small
randomised batches also hurt histogram resolution. The explicit alternative is
QAT with Q/DQ nodes in the ONNX graph.

**Q4. What does "275 TOPS" on AGX Orin actually mean?**
A. 170 sparse INT8 TOPS from the GPU plus 105 sparse INT8 TOPS from the two
DLAs. Sparse means 2:4 structured sparsity, which doubles Tensor Core
throughput, so a dense model on the GPU sees about 85. Small detectors are
often memory-bound anyway. I quote latency measured on the target at the
shipped power mode, not TOPS.

**Q5. What is JSP 936, and what does it make you do as an ML engineer?**
A. MOD's Directive on dependable AI, Part 1, November 2024, built on five
principles: human centricity, responsibility, understanding, bias and harm
mitigation, and reliability. In engineering terms: define the ODD (para 38)
and ship it with the model (177); keep separate training, test and
verification data (158), with verification covering the ODD's edge cases
"inside, on, and beyond" the boundary (160); record data provenance (161);
validate synthetic data from the model's point of view (163); demonstrate V&V
across the ODD and safe behaviour outside it (170–171); regression-test every
update (172); and monitor the environment and performance in service
(179–180). Def Stan 00-055 is named as the primary software safety standard
(para 23).

**Q6. How would you update models on air-gapped or disconnected systems?**
A. Signed, versioned bundles containing the engine, pre/post config,
thresholds, ODD manifest, data-manifest hash, eval report and model card. The
device verifies the signature and refuses downgrades, which mirrors Jetson's
secure boot and rollback protection. The new model runs in shadow beside the
old one, we compare alarm rates and score distributions, then promote or roll
back. The data coming home is compact: crops, embeddings, alarm clips with
operator verdicts. That's also what JSP 936 paras 172 and 181 ask for.

**Q7. How would you defend a person detector against adversarial patches?**
A. Architecturally first: fuse with thermal or radar, because a patch that
fools EO doesn't fool them, and treat a track that vanishes in open ground as
an alarm in its own right. Then in the model: patch augmentation in training,
and certified defences like PatchGuard for any classifier stage, remembering
those guarantees are for classification, not detection. Then measure it: render
patched agents in simulation and report the recall drop at a fixed false-alarm
budget. That's also JSP 936 threat analysis in practice.

**Q8. Where does a simulator fit in a defence MLOps loop?**
A. In three places. Before training, to generate data at the ODD boundary,
which real collection can't do on demand. At quantisation, to build
calibration sets balanced across night, rain and IR. At release, as the V&V
harness that produces the ODD coverage map and the regression suite that JSP
936 asks for. The caution is para 163: synthetic data has to be validated from
the model's point of view, so a sealed real verification set is still needed.

## Sources fetched (2026-09-26)

1. JSP 936 Part 1, gov.uk [publication page](https://www.gov.uk/government/publications/jsp-936-dependable-artificial-intelligence-ai-in-defence-part-1-directive) and [PDF V1.1](https://assets.publishing.service.gov.uk/media/6735fc89f6920bfb5abc7b62/JSP936_Part1.pdf) (full text extracted; paragraphs quoted above)
2. NVIDIA Jetson AGX Orin technical brief, [PDF](https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf) (TOPS split, decode/encode, power)
3. NVIDIA Jetson Orin spec page, [nvidia.com](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)
4. NVIDIA Jetson modules page (AGX Thor), [developer.nvidia.com](https://developer.nvidia.com/embedded/jetson-modules)
5. TensorRT 8.6.1 Developer Guide, INT8 and calibration, [docs.nvidia.com](https://docs.nvidia.com/deeplearning/tensorrt/archives/tensorrt-861/developer-guide/index.html)
6. Ultralytics NVIDIA Jetson guide, YOLO26 benchmark tables, [docs.ultralytics.com](https://docs.ultralytics.com/guides/nvidia-jetson/)
7. Jetson Linux r36.4 Secure Boot, [docs.nvidia.com](https://docs.nvidia.com/jetson/archives/r36.4/DeveloperGuide/SD/Security/SecureBoot.html)
8. Hailo-8 product page, [hailo.ai](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/)
9. SynSense Speck product page, [synsense.ai](https://www.synsense.ai/products/speck-2/)
10. Nagel et al., quantisation white paper, [arXiv:2106.08295](https://arxiv.org/abs/2106.08295)
11. Mishra et al., Accelerating Sparse Deep Neural Networks (2:4), [arXiv:2104.08378](https://arxiv.org/abs/2104.08378)
12. Han et al., Deep Compression, [arXiv:1510.00149](https://arxiv.org/abs/1510.00149)
13. Hinton et al., Distillation, [arXiv:1503.02531](https://arxiv.org/abs/1503.02531)
14. NIST AI RMF page, [nist.gov](https://www.nist.gov/itl/ai-risk-management-framework)
15. Brown et al., Adversarial Patch, [arXiv:1712.09665](https://arxiv.org/abs/1712.09665)
16. Thys et al., patches vs person detection, [arXiv:1904.08653](https://arxiv.org/abs/1904.08653)
17. Xiang et al., PatchGuard, [arXiv:2005.10884](https://arxiv.org/abs/2005.10884)
