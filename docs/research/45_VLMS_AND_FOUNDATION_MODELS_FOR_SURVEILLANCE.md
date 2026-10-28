# 45 — Vision-Language and Foundation Models for Surveillance

*Written 2026-09-26. All sources below were fetched on 2026-09-26 unless stated.
Anything not traceable to a fetched page is tagged **[INF]** (inference or
arithmetic by the author). Where a figure in this report disagrees with an
earlier dossier, the disagreement is stated, not silently resolved.*

## 0. Why this report exists

An interviewer at a CCTV analytics company in 2026 will almost certainly ask
some version of "what do you think about VLMs for surveillance?" The question is
a trap in both directions. Answer "they replace the pipeline" and you have shown
you have never costed a camera-hour or sat with an operator drowning in false
alarms. Answer "they are hype" and you have ignored the one place they are
genuinely transformative: turning a detector's trigger into a sentence an
operator can act on, and letting an operator type a query the system was never
trained for.

The thesis of this report, argued with numbers below:

1. **Open-vocabulary detectors are a real, deployable tool** for the long tail
   of objects (an abandoned rucksack, a ladder against a fence, a hi-vis vest)
   — but they are slower and less accurate than closed-set detectors on the
   classes a surveillance system cares about most (person, vehicle), so they
   *augment* rather than replace the primary detector.
2. **VLM/LLM anomaly detectors have closed most of the gap to weakly-supervised
   methods on academic benchmarks**, but those benchmarks score frame-level AUC
   on curated clips, which (doc 03/R03, principle 4 in CLAUDE.md) flatters
   systems that would be unusable at an operator's false-alarm budget.
3. **Always-on video-LLM analysis is priced per token and is affordable per
   camera only at very low frame rates; its real cost is latency and
   hallucination, not dollars.** The architecture that survives is
   *cheap detector → trigger → VLM verification/description → operator*.
4. The best near-term use of foundation models in a product is **offline**:
   auto-labelling, distillation into edge models, and natural-language search
   over recorded metadata.

## 1. Open-vocabulary detection

### 1.1 The three models an interviewer will name

**Grounding DINO** (Liu et al., IDEA Research / Tsinghua). A DINO-style DETR
detector fused with a text encoder, pre-trained on grounding data so a free-text
prompt ("person carrying a ladder") selects boxes. The abstract reports
**52.5 AP on COCO zero-shot** — "without any COCO training data" — and a record
**26.1 mean AP on ODinW zero-shot**
([arXiv 2303.05499](https://arxiv.org/abs/2303.05499), fetched 2026-09-26).
The official repository's model table is more modest for the openly released
weights: **GroundingDINO-T (Swin-T) 48.4 AP zero-shot on COCO, 57.2 fine-tuned**;
the Swin-B checkpoint is listed at 56.7 fine-tuned, with COCO in its training
mix so no zero-shot figure
([github.com/IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO), fetched 2026-09-26).

> Interview point: the 52.5 headline comes from the larger model and training
> mix; the checkpoint most people actually download is the Swin-T at 48.4. Quote
> the one you'd deploy.

**OWL-ViT / OWLv2** (Minderer et al., Google). OWL-ViT (ECCV 2022) showed that
a plain ViT with contrastive image–text pre-training plus end-to-end detection
fine-tuning gives zero-shot text-conditioned and **one-shot image-conditioned**
detection ([arXiv 2205.06230](https://arxiv.org/abs/2205.06230), fetched
2026-09-26). The image-conditioned mode matters for surveillance: an operator
can crop "this bag" from one camera and search for it elsewhere without naming
it. OWLv2 scales self-training on web image–text pairs to over 1 billion
examples; with an L/14 backbone, LVIS *rare*-class AP rises **from 31.2 % to
44.6 % (a 43 % relative improvement)** — on categories with no human-annotated
boxes ([arXiv 2306.09683](https://arxiv.org/abs/2306.09683), fetched 2026-09-26).

**YOLO-World** (Cheng et al., Tencent AI Lab / HUST, CVPR 2024). A YOLOv8-style
detector with a re-parameterisable vision–language PAN and region–text
contrastive learning. Headline: **35.4 AP on LVIS at 52.0 FPS on a V100**
zero-shot ([arXiv 2401.17270](https://arxiv.org/abs/2401.17270), fetched
2026-09-26). The re-parameterisation is the practical trick: once the operator's
vocabulary is fixed ("person, rucksack, ladder, bolt cutters"), text embeddings
are folded into the weights and the model runs as a closed-set YOLO — which is
what makes TensorRT export and edge deployment tractable **[INF: from the
paper's description of re-parameterisation; not measured here]**.

### 1.2 What those numbers mean for a CCTV product

| Model | Headline zero-shot figure | Speed claim | Source |
|---|---|---|---|
| Grounding DINO (paper) | 52.5 AP COCO; 26.1 mAP ODinW | not in abstract | arXiv 2303.05499 |
| Grounding DINO-T (released) | 48.4 AP COCO | not in README | GitHub README |
| OWLv2 L/14 | 44.6 AP LVIS-rare | — | arXiv 2306.09683 |
| YOLO-World-L | 35.4 AP LVIS | 52.0 FPS V100 | arXiv 2401.17270 |

Three points to make out loud:

* **COCO AP and LVIS AP are different scales.** LVIS has ~1,200 long-tail
  categories; 35 AP there is not "worse" than 48 AP on COCO's 80 classes. Never
  compare across the two.
* **"Person" is not a long-tail class.** Every closed-set detector trained on
  COCO/CrowdHuman already detects people well. The open-vocabulary win is on
  objects and attributes — the rucksack left behind, the angle grinder, the
  ladder — and on the long tail of vehicles (quad bike, e-scooter) **[INF]**.
* **Surveillance imagery is out of distribution for all of them.** None of the
  above evaluate on elevated, low-resolution, compressed, IR or night imagery.
  A 30-px-tall person in H.265 at night (docs/research/30, R04) is not what web
  image–text pairs contain. Treat benchmark AP as an upper bound until measured
  on your own footage **[INF]**. This is exactly the gap SurvSim's degradation
  profiles (`survsim/sensors/degrade.py`) exist to probe.

### 1.3 Prompt engineering is a failure mode, not a feature

Open-vocabulary detectors are sensitive to wording; "bag", "backpack" and
"rucksack" give different recalls, and negatives are hard to express ("a bag
*not* being carried"). The operational consequence: a vocabulary must be
**versioned and regression-tested like model weights** — changing a prompt is a
model change and must go through the same false-alarm evaluation **[INF]**. In
SurvSim terms: the prompt set is part of the configuration hashed into the eval
run, alongside the detector checkpoint.

## 2. VLM- and LLM-based video anomaly detection

### 2.1 The benchmarks, first

Every paper below reports on **UCF-Crime** and **XD-Violence**. UCF-Crime
(Sultani, Chen & Shah, CVPR 2018) is **1,900 untrimmed videos, 128 hours, 13
anomaly classes** — fighting, road accident, burglary, robbery and so on — plus
normal footage ([arXiv 1801.04264](https://arxiv.org/abs/1801.04264), fetched
2026-09-26). It was scraped from YouTube and LiveLeak; many "anomalies" are
dramatic and short, and the metric is **frame-level ROC AUC**.

Why this matters: frame-level AUC integrates over all thresholds and weights
every frame equally. A security evaluation fixes the threshold at the operator's
budget (false alarms per camera-hour) and scores event-level, time-bounded
detection (i-LIDS rule: late = false). A method at 88 % AUC may still produce
hundreds of false alarms per camera-day at the recall an operator needs
**[INF: argued in R03 and implemented in `survsim/eval/`; not a property of any
specific paper]**. Keep this caveat attached to every number in this section.

### 2.2 LAVAD — training-free (CVPR 2024)

Zanella et al., *Harnessing Large Language Models for Training-free Video
Anomaly Detection* ([arXiv 2404.01014](https://arxiv.org/abs/2404.01014),
fetched 2026-09-26). Pipeline:

1. Caption frames with an ensemble of **BLIP-2** captioners.
2. Clean captions using cross-modal (image–text) similarity to neighbouring
   frames.
3. Summarise temporal windows and prompt **Llama-2-13b-chat** to output an
   anomaly score.
4. Refine scores across similar frames.

Results (from the HTML full text,
[arxiv.org/html/2404.01014](https://arxiv.org/html/2404.01014), fetched
2026-09-26): **UCF-Crime AUC 80.28 %; XD-Violence AUC 85.36 %, AP 62.01 %**.
The paper samples "every 16 frames for computational efficiency" and gives no
runtime figures.

What to say: LAVAD's contribution is proof that **zero training data** gets you
into the same band as unsupervised and one-class methods — valuable for a new
site with no labelled incidents. Its weakness is cost and latency: a captioner
plus a 13B LLM per window is far heavier than a detector, and the paper does not
report wall-clock time **[INF]**.

### 2.3 VadCLIP — frozen CLIP, weakly supervised (AAAI 2024)

Wu et al. ([arXiv 2308.11681](https://arxiv.org/abs/2308.11681), fetched
2026-09-26). Uses frozen CLIP features with a dual branch: a coarse binary
visual classifier and a fine-grained branch that aligns video features with
class-name text embeddings. Weakly supervised (video-level labels). Results:
**88.02 % AUC on UCF-Crime, 84.51 % AP on XD-Violence**.

What to say: VadCLIP is the pragmatic middle — cheap frozen features, a small
trained head, and the text branch gives *class names* for anomalies ("fighting"
vs "road accident") rather than a bare score. That class name is what an
operator actually needs.

### 2.4 Holmes-VAU — multimodal LLM with anomaly-focused sampling (CVPR 2025)

Zhang et al. ([arXiv 2412.06171](https://arxiv.org/abs/2412.06171), fetched
2026-09-26). Two contributions: **HIVAU-70k**, >70,000 annotations at clip,
event and video level produced by a semi-automated engine (manual segmentation +
LLM recursive annotation); and an **Anomaly-focused Temporal Sampler (ATS)** that
uses a cheap anomaly scorer plus density-aware sampling to choose which frames
the multimodal LLM sees. Base model **InternVL2-2B**. Frame-level results
([arxiv.org/html/2412.06171](https://arxiv.org/html/2412.06171), fetched
2026-09-26): **UCF-Crime AUC 88.96 %; XD-Violence AP 87.68 %**.

What to say: the ATS is the architectural lesson. Holmes-VAU *already is* a
two-stage system — a cheap scorer decides where to spend the expensive model's
attention. That is the same shape as the production pipeline in §4, arrived at
from the research side.

Caution: the 2B-parameter model is small enough to run on a workstation GPU,
but do not quote a system latency from the paper. Its latency table (§5.3,
Table 4) reports *time to first token* in ms for different frame-sampling
settings (e.g. 8 frames: ~0.46–0.51 ms for Top-K/ATS as extracted, hundreds of
ms for uniform sampling); these are first-token delays under the paper's
setup, not end-to-end alarm latency. *[audit 2026-09-26: earlier text said
"~0.566 ms … for the sampler"; the fetched table does not support that
attribution. The sub-ms values look implausible for an MLLM first token and
may be a unit/extraction artefact — re-read the PDF before quoting any.]*

### 2.5 Summary table

| Method | Venue | Supervision | UCF-Crime AUC | XD-Violence | Source |
|---|---|---|---|---|---|
| LAVAD | CVPR 2024 | none (training-free) | 80.28 | AUC 85.36 / AP 62.01 | arXiv 2404.01014 |
| VadCLIP | AAAI 2024 | weak (video labels) | 88.02 | AP 84.51 | arXiv 2308.11681 |
| Holmes-VAU | CVPR 2025 | instruction-tuned MLLM | 88.96 | AP 87.68 | arXiv 2412.06171 |

Reading it: the training-free method is ~8 AUC points behind; the gap between
the frozen-CLIP method and a 2B MLLM on UCF-Crime is under one point. The large
jump on XD-Violence AP (84.5 → 87.7) is real but is on a dataset of movie and
game clips as well as CCTV **[INF: XD-Violence composition from general
knowledge of the dataset; not fetched here]**.

### 2.6 Zero-shot event description

The quiet but most useful capability across these systems is not the score but
the **sentence**: "two people exchange a bag beside the white van, then walk
off in opposite directions". For an operator, a description that can be
verified in two seconds beats a score that must be verified by watching thirty
seconds of video. Description also enables *search*: embed the description and
query it later ("person in red jacket near gate 3 yesterday afternoon") **[INF]**.

## 3. Hallucination is the false-alarm problem in a new costume

Li et al. (EMNLP 2023) showed that large vision-language models "tend to
generate objects that are inconsistent with the target images", with objects
that are frequent in training instructions or that co-occur with the image
content especially prone to hallucination; they introduced the POPE polling
evaluation ([arXiv 2305.10355](https://arxiv.org/abs/2305.10355), fetched
2026-09-26).

Translate to CCTV **[INF throughout this subsection]**:

* **Co-occurrence hallucination is the dangerous kind.** A car park image makes
  "a person near the car" likely in language space; a dark alley makes "a
  person loitering" likely. The model's priors are the scene's stereotypes —
  exactly what produces false alarms, and also a bias risk (who the model
  expects to see where).
* **Hallucinated descriptions are worse than false boxes.** A false box is
  discarded in a glance; a fluent sentence ("a man appears to be forcing the
  door") primes the operator and can be copied into an incident log.
* **Mitigations that work at system level:**
  - Ground every noun in the description to a detector box / track ID; drop
    unsupported clauses (a detector-veto).
  - Ask closed questions (POPE-style yes/no: "Is a person touching the
    door handle?") rather than open captions for the alarm decision, and keep
    the open caption for display only.
  - Score the VLM stage exactly like any detector: false alarms per
    camera-hour at the operating threshold, on hard negatives
    (`commute_wait` vs `loiter` in SurvSim's catalogue).
  - Log the prompt, model version and raw output with every alarm for audit.

SurvSim angle: because the simulator knows exactly what happened, it can
measure hallucination directly — every noun or verb in a generated description
can be checked against the ground-truth event stream (`events.jsonl`). That is
an evaluation almost impossible on real footage and a concrete pitch.

## 4. Where foundation models belong in an alarm pipeline

```
camera ─► decode ─► closed-set detector + tracker (edge, every frame)
                        │
                        ▼
                rule / behaviour engine (zones, dwell, direction, count)
                        │   trigger (rare: ≤ tens per camera-day)
                        ▼
        VLM verification: closed yes/no questions on a short clip
        + open-vocab detector for scene-specific objects
                        │   pass
                        ▼
        description + evidence frames ─► operator (VMS alarm)
                        │
                        ▼
        offline: index descriptions/embeddings for NL search;
                 feed operator verdicts back as labels
```

Why the VLM sits at **verification, not detection** **[INF, supported by the
cost model in §5 and by the ATS design in Holmes-VAU]**:

1. **Cost scales with triggers, not with time.** Detection must run on every
   frame of every camera; verification runs only on the handful of seconds
   around a trigger.
2. **Latency is bounded where it matters.** The detector gives a sub-second
   trigger; the VLM adds seconds, which is inside an i-LIDS-style tolerance
   only if it runs on a short clip, not a long context.
3. **Recall is set by the cheap stage.** A verifier can only *remove* alarms.
   So the detector/rule stage must be tuned for high recall and the VLM tuned
   to cut false alarms. This makes the verifier's own miss rate critical:
   every true alarm it rejects is gone. Evaluate the verifier's false-reject
   rate on true events as carefully as its false-accept rate.
4. **Explainability comes free.** The verifier's answer and description are
   the alarm annotation.

Open-vocabulary detectors fit at two places: as a **second detector on
triggered clips** (for site-specific objects) and, in their re-parameterised
YOLO-World form, **as the edge detector itself** when the vocabulary is fixed.

## 5. Worked cost model: VLM per camera-hour

### 5.1 Inputs (all fetched 2026-09-26)

* Gemini API: images ≤384 px both sides = **258 tokens**; larger images tiled
  into 768×768 tiles at 258 tokens each; video **263 tokens per second**
  (static processing); audio 32 tokens/s
  ([ai.google.dev/gemini-api/docs/tokens](https://ai.google.dev/gemini-api/docs/tokens)).
* Gemini video: default sampling **1 frame per second**; **the default media
  resolution is *low*: 66 tokens/frame**; **high** media resolution is
  **258 tokens/frame**; "approximately 100 tokens per second of video at
  default (low) media resolution, or approximately 300 tokens per second of
  video at high media resolution", audio (32 tok/s) included
  ([ai.google.dev/gemini-api/docs/video-understanding](https://ai.google.dev/gemini-api/docs/video-understanding)).
  *[audit 2026-09-26: an earlier draft had 258 as the default and 66 as "low";
  the page says default = low = 66.] The tokens page's 263 tok/s corresponds
  to the **high-resolution** frame rate (258/frame), not to the default; at
  the API's default settings a camera-second costs ~100 tokens.*
* Gemini 2.5 Flash: **$0.30 / 1M input tokens** (text/image/video), **$2.50 /
  1M output**; batch $0.15 / $1.25. Gemini 2.5 Flash-Lite: **$0.10 input,
  $0.40 output**; batch $0.05 / $0.20
  ([ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)).
* Anthropic API: Haiku 4.5 **$1 / $5** per MTok in/out; Sonnet 5 $2 / $10;
  Opus 5.5 $4 / $20; batch processing saves 50 %
  ([claude.com/pricing](https://claude.com/pricing)).

### 5.2 Scenario A — always-on, 1 fps, one camera

Tokens per camera-hour **[INF, arithmetic]**:

| Setting | tokens/s | tokens/hour |
|---|---|---|
| Default = low media res (~100 tok/s incl. audio) | 100 | 360,000 |
| Static video, tokens page (263 tok/s ≈ high-res frames) | 263 | 946,800 |
| High media res (~300 tok/s) | 300 | 1,080,000 |

Input cost per camera-hour at Flash-Lite ($0.10/M) and Flash ($0.30/M):

| tokens/hour | Flash-Lite | Flash |
|---|---|---|
| 360,000 | $0.036 | $0.108 |
| 946,800 | $0.095 | $0.284 |
| 1,080,000 | $0.108 | $0.324 |

Add output: if the model emits a 50-token status every 10 s, that is 18,000
output tokens/hour = $0.007 (Flash-Lite) or $0.045 (Flash) **[INF]**.

Per camera-month (730 h), at the *default* ~100 tok/s: Flash ≈ **$79 + $33
output ≈ $112**, Flash-Lite ≈ **$26 + $5 ≈ $31** **[INF]**. At the 263 tok/s
(high-res) rate, Flash: ≈ **$207 +
$33 output ≈ $240**; Flash-Lite ≈ **$69 + $5 ≈ $74** **[INF]**. For a
**40-camera site** (the size used in report 43): ≈ **$9,600/month on Flash**,
≈ **$3,000/month on Flash-Lite**, before any egress or storage **[INF]**.

Cross-check against the corpus: the index's load-bearing fact 9 says always-on
VLM is "~4.6M tokens/camera-hour" (D07). **Source of the discrepancy (audit
2026-09-26):** D07 §L164–167 derives 4.6M from the *Qwen3-VL benchmark
protocol* — 2 fps × 640 visual tokens/frame = 1,280 tok/s — not from any API's
default video tokenisation. Its arithmetic is right for that protocol. With
Gemini's documented video pipeline at 1 fps the figure is **~0.36M at the
default (low) resolution and ~0.95–1.1M at high resolution**. Neither number
is "wrong"; each is meaningless without its frame rate and tokens/frame. The
conclusion (always-on is a poor use of money relative to gating) survives, but
quote it as: "0.4–1M tokens per camera-hour at 1 fps on Gemini's video
pipeline; ~4.6M at a 2 fps, 640-token/frame research protocol."

**The real killer is not dollars, it is 1 fps.** A 1 fps sampler cannot track
(tracking collapses below ~3 fps, index fact 5), misses a 0.5 s hand-off, and
has no identity continuity. Raising to 5 fps roughly quintuples input cost to ~$1,100 per
camera-month on Flash **[INF]** and still gives no tracker. And each call adds
network round-trip plus model latency that no edge detector pays.

### 5.3 Scenario B — trigger-gated verification

Assume **[INF, illustrative]**: the rule engine fires 20 candidate alarms per
camera per day (well above an operator budget, which is the point — the VLM is
there to cut it). Each verification sends 8 frames at ≤768 px (1 tile each,
258 tokens) plus a 300-token prompt, and receives 150 tokens.

* Input per trigger: 8 × 258 + 300 = 2,364 tokens.
* Per camera-day: 20 × 2,364 = 47,280 input; 20 × 150 = 3,000 output.
* Flash: 47,280 × $0.30/M + 3,000 × $2.50/M = $0.0142 + $0.0075 ≈ **$0.022
  per camera-day** ≈ **$0.66 per camera-month**.
* Haiku 4.5 (Anthropic image tokenisation differs; assume a similar ~2.4k input
  tokens for comparison only): 47,280 × $1/M + 3,000 × $5/M ≈ $0.062/day ≈
  **$1.9 per camera-month**.
* 40 cameras: **≈ $26–76/month** depending on the model.

Trigger-gating at **20 triggers/camera-day** (§5.3) is ~**170–400× cheaper**
in dollars than always-on at 1 fps on the same model (Flash: $112–240 vs
$0.66; Flash-Lite: $31–74 vs $0.18) **[INF, ratio of the two scenarios;
audit-corrected from 100–350×]**. This is a dollar ratio at this specific
trigger rate, not the token ratio (19 §3.5 gets ~50–150× fewer tokens from a
different, denser trigger model — see 49 §0 for the reconciliation), and it
spends tokens on 8 frames at the moment
of interest instead of one frame per second of empty car park.

### 5.4 Scenario C — self-hosted

A self-hosted 2B model (Holmes-VAU's InternVL2-2B base) fits an 8 GB
workstation GPU in reduced precision **[INF: parameter count × 2 bytes ≈ 4 GB
weights; not measured on this machine]**. The cost becomes a capital GPU plus
power, with no per-token fee and no footage leaving site — which for a UK
security customer is often the deciding factor (data-protection impact,
report 44) rather than price. The sizing question becomes throughput: how many
triggered clips per second one GPU can verify; measure it, do not quote a
paper.

### 5.5 What to say in one breath

"At Google's published video rates — about 100 tokens a second at default
resolution, about 300 at high — a camera at 1 fps is 0.4 to 1 million tokens
an hour: 4 to 30 cents on Flash-class pricing, tens to a couple of hundred
dollars per camera-month, and it still can't track. Gate it
on triggers — 20 a day, 8 frames each — and it's under a dollar a
camera-month. The money argument for gating is two orders of magnitude; the
latency and data-residency arguments are stronger still."

## 6. Distillation to the edge

The durable value of foundation models for an edge product is **as teachers**
**[INF: synthesis]**:

1. **Auto-labelling.** Run Grounding DINO / OWLv2 offline over site footage with
   the site's vocabulary, filter by confidence and by agreement with the
   production tracker, and train a small closed-set detector. OWLv2's own
   method is self-training at scale — pseudo-labels from web image–text pairs
   ([arXiv 2306.09683](https://arxiv.org/abs/2306.09683)) — the same idea
   pointed at one site.
2. **Vocabulary freezing.** YOLO-World's re-parameterisation collapses a text
   vocabulary into weights ([arXiv 2401.17270](https://arxiv.org/abs/2401.17270)),
   producing a model with closed-set deployment characteristics.
3. **Caption-to-rule distillation.** Use VLM descriptions of verified alarms to
   discover which cheap features (dwell, direction, proximity to a door)
   separated true from false, and encode those as rules or a small classifier.
4. **Feature distillation.** VadCLIP shows a frozen CLIP backbone plus a
   small head reaches 88 AUC on UCF-Crime
   ([arXiv 2308.11681](https://arxiv.org/abs/2308.11681)); a smaller student
   can be distilled from those features for edge hardware.

Risks: pseudo-labels inherit the teacher's biases and hallucinations; a
distilled student will be confidently wrong in exactly the teacher's blind
spots (IR, night, extreme angles). Validate against real and synthetic hard
negatives, not against the teacher **[INF]**.

SurvSim's role here: it provides *true* labels to measure how wrong the
teacher's pseudo-labels are under each degradation profile — a calibration of
the auto-labeller, not just of the student.

## 7. What's hype, honestly

| Claim you will hear | Reality | Basis |
|---|---|---|
| "VLMs replace the detector." | They're slower, costlier per frame, and not better on person/vehicle. They need a detector in front of them. | §1, §5 **[INF]** |
| "Zero-shot anomaly detection, no data needed." | LAVAD is ~8 AUC points behind trained methods on UCF-Crime (80.28 vs 88.02/88.96), and AUC is itself the wrong metric for operations. | §2.5 |
| "It understands intent." | It describes appearances and actions in fluent language; intent is inferred from priors, which is also how it hallucinates and how bias enters. | arXiv 2305.10355 + **[INF]** |
| "Cheap now — pennies an hour." | True per token; false per *useful* camera-hour, because 1 fps can't track and 5 fps costs five times more. | §5.2 |
| "88 % AUC = production ready." | Frame-level AUC on YouTube-sourced clips says nothing about false alarms per camera-hour at a fixed threshold. | UCF-Crime composition (arXiv 1801.04264) + R03 |
| "Natural-language search over all your video." | Real and valuable — over *indexed metadata and descriptions*, not by re-running a VLM over months of footage. | **[INF]** |
| "Open-vocabulary means any object." | Recall depends on the object being well represented in web image–text data and on prompt wording; surveillance angles and IR are poorly represented. | §1.2–1.3 **[INF]** |

What is **not** hype:

* Open-vocabulary detection for the long tail and for operator-defined objects.
* Image-conditioned search (OWL-ViT's one-shot mode) — "find this bag".
* VLM verification that cuts false alarms before they reach the operator,
  **if** measured at the operator's budget.
* Auto-labelling and distillation to shrink the labelling bill for a new site.
* Readable alarm descriptions and NL search over indexed metadata.

## 8. How SurvSim could evaluate this (a pitch)

**[INF throughout — proposals, not implemented features]**

1. **Hallucination rate against ground truth.** For every triggered alarm,
   generate a description; parse nouns/verbs; check each against `events.jsonl`
   and the per-frame agent state. Report hallucinated-claims per alarm by
   degradation profile.
2. **Verifier ROC at operator budget.** Feed the rule engine's candidates
   (including hard negatives from the behaviour catalogue) to a VLM verifier;
   report false alarms per camera-hour before and after, and **true alarms
   lost**. The second number is the one vendors omit.
3. **Open-vocabulary recall vs pixel height.** Place catalogue objects at
   controlled distances and profiles; plot recall against object pixel height,
   using the same `usably_visible` definition as coverage analysis.
4. **Prompt-sensitivity sweep.** Synonym sets per object class; report recall
   variance. A model with high variance needs a curated vocabulary.

Honest limit: until the Unreal backend produces photoreal renders at scale
(docs/11), running these on the mock backend's top-down frames would produce a
number that means nothing — the same reason CLAUDE.md defers detection
baselines.

## 9. Interview Q&A

**Q1. Would you put a VLM in the detection path?**
No — in the verification path. Detection must run every frame on every
camera at edge latency; a VLM on Gemini's documented video pipeline is
0.4–1M tokens per camera-hour at 1 fps and still can't track. Gate it on triggers and
it costs under a dollar a camera-month and adds seconds only to candidate
alarms.

**Q2. Grounding DINO versus YOLO-World for a customer who wants "detect
ladders near the fence"?**
YOLO-World if the vocabulary is fixed: 35.4 LVIS AP at 52 FPS on a V100 and it
re-parameterises into a closed-set model for export. Grounding DINO (48.4 COCO
zero-shot for the released Swin-T) as an offline labeller or second-stage
checker where free-text flexibility matters more than speed. Either way,
measure recall on the customer's own elevated, compressed footage first.

**Q3. LAVAD reports 80 % AUC with no training. Why not ship it?**
Because AUC isn't the metric: an operator has a false-alarm budget, and
AUC averages over thresholds the product will never use. LAVAD is also a
captioner plus a 13B LLM per window with no reported runtime. It's a good
cold-start labeller for a site with no incidents, not a real-time detector.

**Q4. How do you stop a VLM from hallucinating an intruder?**
Ask closed yes/no questions for the decision and keep captions for display;
require every claimed entity to map to a detector track; score the verifier on
hard negatives at the operating threshold; log prompt, model version and output
with each alarm. POPE showed hallucinations concentrate on co-occurring
objects — so the scenes that "look like" a crime are exactly where it lies.

**Q5. What does a VLM verifier cost you in recall?**
Everything it wrongly rejects. A verifier can only remove alarms, so its
false-reject rate on true events caps system recall. You must report "true
alarms lost" alongside "false alarms removed".

**Q6. Holmes-VAU vs VadCLIP?**
Similar UCF-Crime AUC (88.96 vs 88.02). Holmes-VAU adds hierarchical
explanation from a 2B MLLM and, importantly, a cheap anomaly scorer choosing
which frames the MLLM sees — a research-side version of the two-stage
architecture. VadCLIP is cheaper: frozen CLIP and a small head.

**Q7. Cloud VLM for a UK critical-infrastructure customer?**
Often a non-starter for data-protection and security reasons regardless of
price — footage leaves the site. A 2B-class model self-hosted, verifying
triggered clips, is the likely shape; measure its throughput on the target
GPU.

**Q8. What's the most useful thing a foundation model does for your product
this year?**
Offline: auto-labelling new sites and distilling into the edge detector, and
turning verified alarms into searchable descriptions. Real-time VLM is the
smallest part of the value.

**Q9. How would you evaluate this with synthetic data?**
The simulator knows the truth, so hallucination can be counted claim-by-claim
against the event log, verifier recall can be measured against planted events
and hard negatives, and open-vocabulary recall can be plotted against pixel
height — but only on renders a pretrained model can meaningfully consume.

**Q10. The D07 dossier says 4.6M tokens per camera-hour. You said ~1M. Which?**
Both, under different assumptions. Google documents ~100 tokens per second
of video at 1 fps and default (low) resolution (≈0.36M/hour) and ~300 at high
resolution (≈1.1M/hour; the tokens page's 263 tok/s is this case). D07's 4.6M
is Qwen3-VL's benchmark protocol: 2 fps × 640 tokens/frame. Always state the frame rate
with the token count.

## 10. Sources (all fetched 2026-09-26)

1. Liu et al., *Grounding DINO*, arXiv 2303.05499 — https://arxiv.org/abs/2303.05499
2. IDEA-Research GroundingDINO README (model table) — https://github.com/IDEA-Research/GroundingDINO
3. Minderer et al., *Simple Open-Vocabulary Object Detection with Vision Transformers* (OWL-ViT), ECCV 2022, arXiv 2205.06230 — https://arxiv.org/abs/2205.06230
4. Minderer, Gritsenko, Houlsby, *Scaling Open-Vocabulary Object Detection* (OWLv2), arXiv 2306.09683 — https://arxiv.org/abs/2306.09683
5. Cheng et al., *YOLO-World*, arXiv 2401.17270 — https://arxiv.org/abs/2401.17270
6. Zanella et al., *LAVAD*, CVPR 2024, arXiv 2404.01014 — https://arxiv.org/abs/2404.01014 and https://arxiv.org/html/2404.01014
7. Wu et al., *VadCLIP*, AAAI 2024, arXiv 2308.11681 — https://arxiv.org/abs/2308.11681
8. Zhang et al., *Holmes-VAU*, CVPR 2025, arXiv 2412.06171 — https://arxiv.org/abs/2412.06171 and https://arxiv.org/html/2412.06171
9. Sultani, Chen, Shah, *Real-world Anomaly Detection in Surveillance Videos* (UCF-Crime), arXiv 1801.04264 — https://arxiv.org/abs/1801.04264
10. Li et al., *Evaluating Object Hallucination in Large Vision-Language Models* (POPE), EMNLP 2023, arXiv 2305.10355 — https://arxiv.org/abs/2305.10355
11. Google, Gemini API pricing — https://ai.google.dev/gemini-api/docs/pricing
12. Google, Gemini API token counting — https://ai.google.dev/gemini-api/docs/tokens
13. Google, Gemini API video understanding — https://ai.google.dev/gemini-api/docs/video-understanding
14. Anthropic / Claude pricing — https://claude.com/pricing

Prices change often; re-fetch §5 inputs before quoting them in an interview.
