# D07 — The frontier and the future (2024 → 2035) of surveillance / ISR video analytics

**What's new, what's coming, what to add to a product like the vendor's, what is obsolete,
what became easy, and what remains hard.**

---

## 0. Front matter: how this document was built, and how to read it

This dossier is the "outward" companion to the five inward dossiers already in this repo
(`R01` detection & single-camera tracking, `R02` MTMC & re-ID, `R03` behaviour/intent/anomaly,
`R04` degraded imaging & sim2real, `R05` multi-sensor fusion & NL retrieval) and to the
company/ecosystem dossier `R06`. Those documents establish *where the field is*. This one
establishes *where it is going*, and — more importantly for an engineering organisation — which
of the coming things are load-bearing for a product and a simulator, and which are
press-release physics.

### 0.1 Sourcing discipline and an honest limitation

> **Retrieval limitation, stated up front.** This session's live web-search budget was consumed
> (200/200 calls) part-way through the research pass, and direct page fetching was refused by
> the environment's egress policy for every domain attempted (`ai.meta.com`, `arxiv.org`,
> `docs.nvidia.com`, `huggingface.co`, `blogs.nvidia.com`, `en.wikipedia.org`,
> `digital-strategy.ec.europa.eu`, and others — all returned `EGRESS_BLOCKED`). The practical
> consequence: **the frontier-model section below rests on eight fresh search passes performed
> before the budget ran out, plus the several hundred already-captured, already-linked
> quotations in `R01`–`R06`, plus clearly-labelled professional judgement.** Every quotation
> I could not personally re-read verbatim in this session is marked `[VERIFY]`. Quotations
> re-used from a sibling dossier are marked `[via R0x]` and carry that dossier's own caveats.
> Nothing here is a fabricated quotation. Where a number is my own arithmetic, it says so.
> **Before any of this is shown to a customer, a regulator, or a funder, the `[VERIFY]` marks
> must be cleared against the primary source.**

Three reading conventions:

* `[VERIFY]` — the claim is sourced but I could not re-read the primary wording in this session.
* `[via R0x]` — verbatim quotation captured and linked in dossier `R0x` of this repo.
* `[lore]` / `[judgement]` — practitioner knowledge or my own inference, deliberately unsourced,
  offered as an engineering position rather than a citation.

### 0.2 Non-duplication check against R01–R05 "open problems"

I read the open-problems sections of all five dossiers before writing. They collectively claim
the following as unsolved, and **this document does not re-litigate them**; it only asks what
the 2024–2026 frontier does *to* them:

| Already claimed as open by | Problems |
|---|---|
| `R01 §8` | frame-rate-agnostic tracking; long-horizon within-camera identity; crowd-scale association; degradation robustness as a benchmark axis; benchmark-vs-deployable-reliability; foundation-model tracking not yet always-on; amodal vs visible boxes; FA-per-camera-hour evaluation |
| `R02 §8` | generalisation across camera rigs; moving/mixed-modality networks; clothes-changing re-ID; days-to-months identity; adversarially-aware tracking; open-set operation; group reasoning; foundation-model unification; privacy-preserving analytics; self-healing calibration; degraded-imagery re-ID; evaluation realism (sync/calibration error as variables) |
| `R03 §10` | rate-based evaluation; the 1,200× operating-point gap; open-set pose anomaly; zero-label site adaptation; owner–object association; cross-camera behaviour; VLM cost/latency architecture; calibration & abstention; adversarial behaviour; benchmark contamination |
| `R04 §8` | no adverse-weather fixed-CCTV people benchmark; robustness transfer; enhancement-for-machines; cross-modal misalignment; multi-view topology generalisation; long-horizon identity; open-set behaviour; world models as label sources; automatic simulator tuning; certification documentation; edge compute reality; degradation-aware fairness; tamper analytics; event-camera surveillance |
| `R05 §13` | wildlife-vs-human; correlated nuisance; RF-to-vision association; self-maintaining cross-modal calibration; DAS cross-site generalisation; adversarial POD; formalising *assessment*; grading regimes vs monthly models; frame-accurate boundaries; streaming "when to speak"; annotator-disagreement-robust evaluation; in-domain grounding benchmarks; calibrated abstention; continuous-indexing economics; standing queries; provenance; privacy-preserving retrieval |

**The contribution of this document, stated precisely:** it is the *time axis*. R01–R05 are
cross-sections of 2024–2026. D07 asks which of those cross-sections dissolve by 2028, which
harden into permanent constraints, and what an engineering roadmap and a simulator requirement
list look like when you take the answer seriously.

---

## 1. Foundation models for video: what actually landed in 2024–2026

### 1.1 The headline shift: from "train a detector" to "prompt a detector"

The single largest change between 2023 and 2026 is not accuracy. It is **the interface**. In
2019 a new object class cost you a labelling campaign; in 2026 it costs you a noun phrase. The
clearest artefact of that shift is **SAM 3**, released 19 November 2025, which introduces
*Promptable Concept Segmentation*: "given a short noun phrase such as *yellow school bus* or an
image exemplar, SAM 3 returns unique masks and IDs for every matching instance at once, where
SAM 1 and SAM 2 predicted one object per prompt" `[VERIFY — paraphrase assembled from the
search summary of` [SAM 3: Segment Anything with Concepts](https://arxiv.org/abs/2511.16719) `and`
[Roboflow's explainer](https://blog.roboflow.com/what-is-sam3/)`]`. The architecture matters for
our purposes: "the model consists of an image-level detector and a memory-based video tracker
that share a single backbone", with "recognition and localization … decoupled with a presence
head" `[VERIFY]`. Reported gain: "a 2× performance gain over existing systems in Promptable
Concept Segmentation while maintaining and improving SAM 2's capabilities for interactive
visual segmentation" `[VERIFY]`. The data engine produced "4M unique concept labels, including
hard negatives, across images and videos" `[VERIFY]`.

There is already a **SAM 3.1**, described by Meta as "Faster and More Accessible Real-Time
Video Detection and Tracking With Multiplexing and Global Reasoning"
([Meta AI blog](https://ai.meta.com/blog/segment-anything-model-3/)) — the title alone tells you
the competitive axis has moved from *can it segment* to *can it segment many streams in real
time*. `[VERIFY — the page itself is egress-blocked in this environment; only the title was
retrievable.]`

Why this matters commercially, in one sentence: **the open-vocabulary detector is no longer a
research curiosity, it is the default new-class mechanism, and the moat therefore moves off
"which classes do you support" and onto "at what false-alarm rate, on what hardware, under what
degradation".** That is precisely the axis this repo's simulator measures.

### 1.2 The self-supervised backbone: DINOv2 → DINOv3

**DINOv3** (2025) is the backbone story. It is a distillation pyramid: "a very large ViT
(7 billion parameters) is first self-trained on a huge image set, then smaller student models
learn to mimic the teacher's outputs" `[VERIFY —` [DINOv3 paper](https://arxiv.org/pdf/2508.10104)`,
summarised via` [Lightly's technical overview](https://www.lightly.ai/blog/dinov3)`]`. The
technical contribution that matters for surveillance is **Gram Anchoring**, introduced "to
address the known issue of dense feature maps degrading during long training schedules"
`[VERIFY]`. The reported effect: "in semantic segmentation it outperforms DINOv2 by +6 mIoU
point on ADE20K" and it "significantly surpasses others on dense benchmarks, including models
that leverage mask annotation priors such as AM-RADIO" `[VERIFY]`. Meta evaluated it "across
15 diverse visual tasks and more than 60 benchmarks" `[VERIFY]`.

The operational reading `[judgement]`: for a surveillance product, DINOv3-class frozen features
are the single cheapest upgrade available, because they are *task-agnostic*. One frozen
backbone, many light heads: person detection, re-ID embedding, tamper/IQA change detection,
anomaly-by-feature-distance, cross-camera appearance matching. The `R02` finding that
**CLIP-ReID generalises better cross-domain than TransReID** — "on [the specialised domain]
TransReID … shows a drop of 50.75% and 23.01% mAP compared to Market1501 and MSMT17
respectively, while CLIP-ReID exhibits a drop of 38.09% and 21.74% mAP, indicating that
CLIP-ReID generalizes better to this specialized domain" `[via R02 §3.2]` — is the same finding
one generation earlier: **large-scale pretrained features degrade more gracefully off-domain than
supervised-from-scratch features.** Expect DINOv3-initialised re-ID to inherit that property,
and *test it on the degrade profiles* before believing it.

### 1.3 Video encoders: VideoPrism, InternVideo2/2.5/3

**VideoPrism** (ICML 2024) is the cleanest demonstration of the frozen-video-encoder thesis:
"when tested on 33 public video understanding benchmarks over four task categories, a single
frozen VideoPrism checkpoint outperforms previous best-performing foundation models on 31 of
them, with no fine-tuning on target task datasets" [audit 2026-09-26: arXiv 2402.13217 abstract says 31/33; the current Google blog says 30/33] `[VERIFY —`
[Google Research blog](https://research.google/blog/videoprism-a-foundational-visual-encoder-for-video-understanding/)`,`
[code](https://github.com/google-deepmind/videoprism)`]`. Architecturally it is modest —
"VideoPrism-B/L are the composition of a Vision Transformer image encoder and four
temporal-attention Transformer layers" `[VERIFY]` — which is good news for edge feasibility.
Notably its strongest surprise was in *scientific* video (ethology, behavioural neuroscience,
ecology), "actually surpassing models designed specifically for those tasks" `[VERIFY]`. That
generalisation-to-weird-domains property is the one a CCTV integrator wants.

**InternVideo2.5** is the long-context line: it "enhances the original MLLMs' ability to perceive
fine-grained details and capture long-form temporal structure", using "dense vision task
annotations … with direct preference optimization" and "adaptive hierarchical token
compression", achieving SOTA "in around 7B model size, significantly increasing input video
sequences by six times in length" `[VERIFY —`
[arXiv 2501.12386](https://arxiv.org/abs/2501.12386)`]`. The per-benchmark deltas are the honest
part and deserve to be read closely: "+12.4 on EgoSchema and +3.9 on MLVU while … relatively
marginal on LongVideoBench (+0.6) and VideoMME (+0.9)" `[VERIFY]`. **Twelve points on one
benchmark and 0.6 on another is the signature of benchmark-specific gains, not of a capability
jump.** The paper's own most interesting claim for us is a side-effect: "the design of long and
rich context (LRC) enables the MLLM to master specialized vision capabilities like object
tracking and segmentation" `[VERIFY]` — i.e. the video-LLM is starting to absorb the tracker.

**InternVideo3** (2026) names the next step in its title — *Agentify Foundation Models with
Multimodal Contextual Reasoning* ([arXiv 2606.12195](https://arxiv.org/pdf/2606.12195))
`[VERIFY — title only]`. Also worth tracking: `VideoARM` "agentic reasoning over hierarchical
memory" ([arXiv 2512.12360](https://arxiv.org/pdf/2512.12360)) `[via R05 §9.1]`.

### 1.4 The general VLMs: Qwen2.5/3-VL, Gemini, GPT-class

**Qwen3-VL** is the open-weights frontier for video. Its technical report reports "substantially
improved video understanding capabilities through the integration of interleaved MRoPE,
insertion of textual timestamps, and scaling temporally dense video captions, with the 8B
variant achieving performance competitive with the significantly larger Qwen2.5-VL 72B model"
`[VERIFY —` [Qwen3-VL Technical Report](https://arxiv.org/abs/2511.21631)`]`. Against closed
models: "in comparison with state-of-the-art proprietary models including Gemini 2.5 Pro, GPT-5,
and Claude Opus 4.1, Qwen3-VL demonstrates competitive and sometimes superior performance", and
"with a 256K token context window, it further attains or surpasses Gemini-2.5-Pro on long-video
evaluation tasks, particularly on MLVU" `[VERIFY]`.

**Read the evaluation protocol, because it is the cost story.** Qwen3-VL's own evaluation
imposed "a cap of 2,048 frames per video across all benchmarks with video tokens not exceeding
224K, maximum tokens per frame set to 768 … or 640 for other benchmarks, and Charades-STA videos
sampled at 4 frames per second while other benchmarks used 2 fps" `[VERIFY]`. Do the arithmetic
`[my arithmetic]`: 2 fps × 640 tokens/frame = **1,280 visual tokens per second of video**. One
camera-hour is therefore ≈ 4.6 M visual tokens *under this research protocol* (2 fps × 640
tokens/frame). [audit 2026-09-26, AUDIT_43-47: a production always-on deployment at 1 fps with
Gemini's default (low) video resolution is ~0.36 M tokens/camera-hour, ~1.1 M at high resolution;
4.6 M holds only under the 2 fps × 640 tokens/frame assumption.] At 4.6 M, a 500-camera site running
24/7 is ≈ 5.5 × 10¹⁰ visual tokens per day (≈ 4.3 × 10⁹ at the 0.36 M default). At *any* plausible 2026 price per million tokens this is not a business;
it is an arithmetic refutation. This is the quantitative form of `R05 §13` open problem 14
("cost-efficient continuous indexing") and of `R03 §6.2`'s conclusion that the viable
architecture is "cheap always-on detection plus VLM for suppression" `[via R03]`.

The frontier long-video number that should anchor every roadmap conversation, from `R05`:
"*GPT-4o achieves the leading performance in the MLVU experiment, attaining an average score of
64.6% in multi-choice tasks*" `[via R05 §9.1, itself marked VERIFY]`, and "*LongVideoBench
presents significant challenges even for the most advanced proprietary models like GPT-4o, while
their open-source counterparts show an even larger performance gap*" `[via R05]`. **~65% on
multiple choice, where guessing scores 25%, is the 2026 state of long-video comprehension.**
[audit 2026-09-26: 64.6% is the MLVU v1 / CVPR 2025 dev-set M-Avg; the later arXiv version's
six-option test set gives GPT-4o 54.5% against a 16.7% chance baseline.]
Anyone selling narrative comprehension of hours of CCTV is selling a research goal.

And the sharpest diagnostic in the whole field, which every buyer should be taught to use
`[via R05 §9.1, lore]`: **"how does your system score if I give it one random frame instead of
the video?"** If the drop is small, it is not doing video understanding — a critique formalised
as *Breaking Down Video LLM Benchmarks: Knowledge, Spatial Perception, or True Temporal
Understanding?* ([arXiv 2505.14321](https://arxiv.org/html/2505.14321v1)) `[via R05]`.

### 1.5 Open-vocabulary detection: Grounding DINO 1.5/1.6, YOLO-World, OWLv2

This is the family the product-marketing department will fall in love with, and `R04 §3.4`
already contains the necessary cold water: open-vocabulary detectors "are the most seductive and
most dangerous tool for this domain: they give you 'person with a backpack' zero-shot, and they
fall apart under distribution shift", citing *Open-Vocabulary Object Detectors: Robustness
Challenges under Distribution Shifts* ([arXiv 2405.14874](https://arxiv.org/pdf/2405.14874))
`[via R04]`. And from `H01`: "OWL-ViT/GroundingDINO/YOLO-World **fall apart under distribution
shift**, and SAM-class models degrade sharply on low-contrast night frames, thermal and heavy
compression because **they were trained on photographs, and CCTV is not photography**"
`[via H01/R04, lore]`.

**The 2026 synthesis `[judgement]`:** open-vocabulary detection has become the right tool for
*three* jobs and the wrong tool for a fourth.

* **Right — scenario authoring and dataset bootstrapping.** Auto-labelling a new class in
  simulator output or in archive footage, then distilling to a small closed-vocabulary model.
  This is now the standard industrial pattern and it is genuinely transformative for time-to-new-class.
* **Right — forensic search over archive.** Recall matters, latency does not, a human adjudicates.
* **Right — long-tail corroboration on an already-triggered clip.** "Is there a ladder in this
  alarm clip?" asked once, not 30 times a second.
* **Wrong — always-on primary alerting.** Distribution-shift fragility plus uncalibrated
  confidence plus per-frame cost equals a nuisance-alarm generator. Keep the primary detector
  closed-vocabulary, distilled, quantised and measured.

### 1.6 The rest of the 2024–2026 model zoo, placed

`[judgement + VERIFY throughout this subsection — these are placements from professional
knowledge, not re-verified in this session]`

* **Florence-2** (Microsoft) — the small unified vision model: detection, grounding, captioning,
  OCR from one prompt-conditioned seq2seq head. Its real value in this domain is **OCR-in-scene
  and dense captioning at a size that fits an edge box**, not its detection accuracy.
* **PaliGemma 2** (Google) — open weights, small, easy to fine-tune, strong at *structured*
  outputs. The pragmatic choice when you want a small VLM you can actually host and version.
  Underrated for **attribute extraction** (garment colour, bag presence) feeding a structured
  index — which, per `R05 §11.1`, is the part of "AI video search" that actually works.
* **Molmo** (Ai2) — notable for **pointing** as a native output modality, and for a genuinely
  open data pipeline. Pointing is a better interface than boxes for operator-in-the-loop
  workflows ("point at the thing you mean") and for grounding an agent's claims.
* **Grounding DINO 1.5 / 1.6** (IDEA) — the strongest of the open-set detector line, with an
  explicit "edge" variant; the practical baseline against which SAM 3's promptable concept
  segmentation should be measured on *our* degrade profiles.
* **YOLO-World / YOLOE-class** — the real-time end of open-vocabulary. This is the only branch
  of the family with a credible always-on story, and even then, treat the vocabulary as frozen
  at deployment time and re-measure FA/camera-hour every time it changes.
* **OWLv2** — self-training scaled open-vocabulary detection; historically the best
  *recall-oriented* zero-shot detector, which makes it a good auto-labeller and a bad alarmer.

### 1.7 Cost and latency: the numbers nobody publishes

`R05 §13` open problem 14 and `R05 §15` bullet 28 both say it: "no vendor publishes cost per
camera-hour of VLM inference. This is the number that kills deployments" `[via R05, lore]`.
This remains true in 2026. My position `[judgement]`: **a surveillance product should publish
three numbers per feature and be the first in the industry to do so** —

1. **GPU-seconds per camera-hour** at the configured operating point;
2. **alarms per camera-hour**, split into true, nuisance and false-by-cause;
3. **time-to-first-alert** from stimulus onset (the i-LIDS clock, see §8).

Whoever publishes these first wins every technical evaluation they enter, because every
competitor will be unable to answer.

---

## 2. Video agents and agentic surveillance

### 2.1 What "video agent" means, concretely

Strip the marketing and an agentic video system is: **a language model that plans a sequence of
tool calls over a video corpus, maintains memory across calls, and emits a natural-language
answer or alert with citations back to clips.** The tools are the boring, reliable parts —
detector, tracker, re-ID, OCR/ALPR, geometry, time filter, vector search, VMS query, access-control
log. The LLM is the orchestrator, not the perceiver. This is the same retrieve-then-reason split
that `R05 §11.2` identifies as correct and non-optional `[via R05]`.

The reference implementation to know is **NVIDIA's AI Blueprint for Video Search and
Summarization (VSS)**: "a GPU-accelerated reference architecture for building video analytics
agents with real-time verified alerts, visual Q&A, and automated reporting", using "vision
language models (VLMs) such as NVIDIA Cosmos, LLMs such as NVIDIA Nemotron, RAG, and NVIDIA
NIMs" `[VERIFY —` [VSS blueprint repo](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)`]`.
Its own architectural decomposition is worth adopting wholesale as a vocabulary: VSS "is
organized into three areas of processing and analysis: **real-time video intelligence** (feature
extraction, embeddings, and stream understanding with results published to a message broker),
**downstream analytics** (enrichment of metadata into trajectories, incidents, and verified
alerts), and **agentic and offline processing** (orchestrated tools for search, Q&A,
summarization, and clip retrieval, including via the Model Context Protocol)" `[VERIFY —`
[VSS docs](https://docs.nvidia.com/vss/latest/index.html)`]`. The headline claim: "users can
summarize a video 100× faster than watching in real time. For example, an hourlong video can be
summarized in text in less than one minute" `[VERIFY —`
[NVIDIA blog](https://blogs.nvidia.com/blog/ai-blueprint-video-search-and-summarization/)`]`.
Note also that it is "built on top of the NVIDIA Metropolis platform" `[VERIFY]`, i.e. the
agentic layer sits on the same DeepStream/Metropolis substrate that `R01 §5.1` already covers.

Two words in that architecture deserve underlining. **"Verified alerts."** NVIDIA has put
verification in the architecture diagram, not in the FAQ. That is the correct instinct and it is
the single most important design idea in agentic surveillance: *the agent's job is not to detect,
it is to verify, explain and route.*

And **"Model Context Protocol."** By 2026, the integration surface for video analytics is
becoming an MCP tool server, not a proprietary SDK. `[judgement]` This is a strategic fork for
any analytics vendor: expose your detector/tracker/index as MCP tools and become a component in
someone else's agent, or build the agent and own the operator relationship. Doing neither is the
only losing move.

### 2.2 The academic line: VideoAgent and friends

The academic agentic-video line (VideoAgent and its successors) established the pattern:
iterative frame selection under an LLM's control, with memory, beats uniform sampling at a
fraction of the token cost. `[VERIFY — I was unable to retrieve VideoAgent's numbers in this
session; treat the claim as a well-known result requiring citation before external use.]`
`R03 §11` already logs the surveillance-specific instance: **Ava**, "agentic video analytics"
([arXiv 2505.00254](https://arxiv.org/html/2505.00254v5)), alongside **Zelda** (VLM video
analytics, [arXiv 2305.03785](https://arxiv.org/pdf/2305.03785)) and **SketchQL**
([DOI](https://dl.acm.org/doi/pdf/10.1145/3677140)) `[via R03]`.

### 2.3 Streaming VLMs: the "when to speak" problem is the alarm-threshold problem

This is, in my view, the most important conceptual import of the last two years, and `R05 §9.2`
states it precisely: streaming "forces a *decision* the offline setting never faces: **when to
speak**", which "is structurally identical to the perimeter alarm threshold problem … fire early
and you generate false alarms; wait for certainty and you miss the response window. **Live NL
video monitoring is an alarm-threshold problem wearing a language-model costume.**" `[via R05]`

The models: **VideoLLM-online** with "the LIVE framework … introducing a streaming training
objective, data generation scheme, and an optimized inference pipeline with a continuous KV
cache"; **Flash-VStream** which "simulates the memory mechanism of humans and is able to process
extremely long video streams in real-time", via "Spatial-Temporal-Abstract-Retrieved (STAR)
memory"; and **Dispider**, whose title names the decomposition — *Enabling Video LLMs with
Active Real-Time Interaction via Disentangled Perception, Decision, and Reaction*
([arXiv 2501.03218](https://arxiv.org/pdf/2501.03218)) `[all via R05 §9.2]`.

**The deployable pattern in 2026 is not end-to-end streaming comprehension.** It is the sliding-window
index: "ingest, segment on a 2–10 s cadence, embed and caption each segment, upsert into a vector
index and a text index, and let queries run against an index that is a few seconds behind live
… it supports standing queries (a saved query re-evaluated against each new segment = a live
alert)" `[via R05 §9.2, lore]`. **Standing queries are the product.** A saved natural-language
query, re-evaluated continuously, with a per-query false-alarm budget, is the mechanism by which
"alert me if someone climbs the fence" replaces a zone-polygon configuration wizard.

### 2.4 Natural-language rules replacing configuration: the real prize, and the real trap

The commercial promise is that an operator types *"alert me if someone climbs the fence between
the substation and the car park after 20:00"* and the system configures itself. The market is
already selling adjacent versions of this. From `R03 §5.3`: Hakimo "automatically resolves
door-forced alerts with near 100% accuracy" and "escalates only genuine security threats to
authorities, eliminating false alarms"; in March 2025 it "announced a $10.5 million funding round
and the launch of AI Operator, a breakthrough autonomous security agent that monitors existing
security hardware, detects threats in real time, and executes response protocols just like a
human security professional" `[via R03]`. Ambient.ai claims "90–95% false alarm reduction at
enterprise scale" and to "auto-clear and reduce 95% of false access control alarms" `[via R03]`.
Verkada's NL search "understands natural language queries like 'FedEx truck on January 15'" and
uses "Dynamic Score Thresholding to set the threshold level for what counts as a 'match'"
`[via R05 §11.1]`.

**Four engineering truths about NL rules `[judgement, grounded in the above]`:**

1. **The NL layer is a compiler, not a perceiver.** The durable design is: natural language in →
   *an explicit, inspectable, versioned rule object* out (zone geometry + class + predicate +
   time window + dwell + confidence threshold + escalation). `R05 §11.1`'s reading of BriefCam
   is the same insight from the retrieval side: "what that feature list is: a structured
   attribute filter over an object index, not a language model … **Do not let an LLM-shaped
   roadmap discard the structured-attribute index; it is the part that works**" `[via R05, lore]`.
2. **The compiled rule must be shown back to the human and approved.** "I understood you to mean:
   *person* crossing *polygon A→B* upward vertical displacement > 1.2 m within 4 s, 20:00–06:00,
   suppressed during rain-mode." That sentence is the entire trust mechanism.
3. **Every rule needs a false-alarm budget attached at compile time**, with the simulator as the
   instrument that estimates it before the rule goes live. This is a feature no incumbent has, and
   it is the natural product of a repo like this one.
4. **Ambiguity must produce a question, not a guess.** "Climbs the fence" is under-specified
   (which fence; does sitting on it count; does a ladder against it count). An agent that asks
   is trustworthy; one that guesses generates the 3–4 false alarms that, per `R03 §5.2`, are
   enough that "operators begin to distrust the system" `[via R03]`.

### 2.5 Hallucination: the named failure mode and how to engineer around it

`R05 §12` is unambiguous: "**Hallucination is measurable and endemic.**" **VideoHallucer** is
"the first comprehensive benchmark for hallucination detection in large video-language models
(LVLMs)", categorising hallucinations "into two main types: intrinsic and extrinsic" `[via R05]`.
And the domain-specific danger, stated there better than I can restate it: "**The
security-specific danger is *extrinsic non-factual* hallucination**: a VLM asked 'is this person
carrying a weapon?' that answers from language priors about the scene rather than from pixels.
In an evidential chain that is not a bug, it is a fabrication." `[via R05]` The governing rule
follows: "**A VLM's prose is never the record.** The record is the clip plus a thresholded
structured detection" `[via R05 §15 bullet 34]`.

**A hallucination-control checklist for an agentic surveillance product `[judgement]`:**

* **Grounded citation or nothing.** Every clause of every generated sentence must carry a
  `(camera, t_start, t_end, track_id, box)` citation. Unciteable clauses are stripped, not shown.
* **Ask closed questions.** "Does this clip contain a person climbing?" with a calibrated
  yes/no/abstain beats "describe what happens". Open generation is where fabrication lives.
* **Two-model disagreement as an abstention trigger.** Cheap detector says yes, VLM says no →
  escalate to human, do not resolve. Disagreement is signal.
* **Abstention as a first-class output class**, per `R03 §10` item 8: "No VAD paper reports ECE.
  Operators need 'I don't know' as an output class" `[via R03]`.
* **Negative-control prompts in production.** Periodically ask the agent about objects that are
  not present, on live footage, and alarm on the fabrication rate. This is cheap continuous
  hallucination monitoring and nobody does it.
* **Never let the agent's prose enter the evidential export.** Structured detections and clips
  only; prose goes in an advisory pane marked as such.

### 2.6 Evaluating agents

There is no accepted benchmark for "agentic surveillance". `[judgement]` The one that should
exist, and which this repo could create, has four axes:

1. **Task success on standing queries** — scored with i-LIDS-style timed windows, per `R05 §5.2`:
   an alarm within 10 s of onset is a TP, "alarms after 10 s are counted as an FP" `[via R05]`.
2. **Tool-call efficiency** — GPU-seconds and tool calls per resolved alert.
3. **Grounding fidelity** — fraction of generated clauses with a valid citation that a human
   confirms.
4. **Refusal calibration** — abstention rate vs error rate; a Pareto curve, not a number.

---

## 3. 3D reconstruction, digital twins and world models

### 3.1 4D reconstruction from CCTV: Gaussian splatting arrives, and hits a wall

Gaussian splatting (3DGS, 2023) and its dynamic/4D descendants made *photoreal novel-view
synthesis from posed images* a commodity between 2023 and 2026, and the tooling is now
consumer-grade. `[VERIFY — I could not re-verify specific 4DGS-from-CCTV results in this
session; the following are engineering positions.]`

**Where it works for surveillance `[judgement]`:**
* **Static scene capture from a survey walk.** A phone or a 360 camera walk of a site produces a
  metric 3D scene good enough for camera-placement analysis, sightline computation and occlusion
  maps. This is the highest-value, lowest-risk application and it is available today.
* **Camera placement and coverage optimisation.** `R04 §8` item 5 notes "camera-placement
  optimisation is barely explored". A splat/NeRF reconstruction plus a projective coverage solver
  is a *sellable consulting-grade product* and a natural simulator feature: given a 3D site, place
  N cameras to maximise the probability of achieving ≥60 px target height on every approach path.
  The 60-px threshold is not arbitrary: `R04 §2` gives the ladder — "**~60–80 px**: pose/gait
  usable; re-ID starts working" `[via R04]`.
* **Forensic scene reconstruction for court.** Metric measurement from recorded footage (how tall
  was he; how fast was the vehicle) with a documented uncertainty budget.

**Where it does not work `[judgement]`:** dynamic 4D reconstruction of *people* from sparse,
unsynchronised, wide-baseline, heavily-compressed CCTV. Every assumption 4DGS makes — dense
views, small baselines, accurate poses, high bitrate — is violated. `R02 §8` item 12 already
records that "benchmarks are minutes long, perfectly synchronised and perfectly calibrated"
`[via R02]`. Splatting a crowd from six 640×360 substreams at 0.3 Mb/s (the real bitrate per
`R04 §1`/`H01` — "**most analytics run on the substream**: 640×360 at 0.2–0.5 Mb/s" `[via H01]`)
is not a solved problem and will not be by 2028.

### 3.2 Digital twins of sites

The vendor landscape: **NVIDIA Omniverse** (airports, factories, warehouses; already the source
of the AI City Challenge's synthetic MTMC data — "synthetic data built using the NVIDIA Omniverse
Platform" `[via R02 §6]`), **Siemens** (Xcelerator/industrial twins), **Bentley** (infrastructure
twins), plus **Duality AI Falcon** ("digital twins, EO/IR sensor emphasis") and **CVEDIA** —
"notable because it sells *surveillance analytics trained on synthetic data* — the nearest
competitor to the vendor's pitch" `[via R04 §5.7]`.

**The strategic observation `[judgement]`:** the digital-twin market and the
synthetic-surveillance-data market are converging, and the integration point is the *camera
model*. A BIM/twin vendor has the geometry and no imaging chain; a synthetic-data vendor has the
imaging chain and no site. Whoever ships "import the customer's twin, place their real camera
models, predict their real analytics performance" owns a category. `R04 §5.7` makes the same
point about **Anyverse** — "physically based sensor + ISP simulation — closest to our §1
philosophy" `[via R04]` — and this repo's entire §1 thesis is that the imaging chain is where
sim2real is won or lost.

### 3.3 Sim-in-the-loop and the "geometry vs pixels" division of labour

`R04 §5.6` states the architecture that should be this repo's constitutional position: "UE5 owns
truth, diffusion optionally restyles pixels, and we validate that labels still fit" `[via R04]`.
The corresponding open problem is stated in `R04 §8` item 8: "Hybrid 'simulator owns geometry,
generative model owns pixels' is the open engineering problem, including how to *prove* labels
survive the restyling" `[via R04]`.

**Cosmos** is the tooling that makes this concrete. **Cosmos Transfer** is exactly the restyler:
"Cosmos Transfer 2.5 is 3.5× smaller yet faster and higher quality, producing photorealistic
data from spatial inputs and ground truth simulations" `[VERIFY —`
[HF blog](https://huggingface.co/blog/nvidia/cosmos-predict-and-transfer2-5)`]`. **Cosmos
Predict** is the world simulator: "Cosmos Predict 2.5 combines three WFMs into one, reducing
complexity while enabling longer (up to 30s) video generation and multi-view outputs", unifying
"Text2World, Image2World, and Video2World generation in a single model", and leveraging
"Cosmos-Reason1, a Physical AI vision-language model, to provide richer text grounding and finer
control of world simulation" `[VERIFY]`. **Cosmos Reason** is "an open, customizable,
7-billion-parameter reasoning Vision Language Model (VLM) for physical AI and robotics that
enables robots and vision AI agents to reason like humans, using prior knowledge, physics
understanding and common sense" `[VERIFY —` [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/)`]`.
The adopter list is real-industrial: "Agility Robotics, Figure AI, Foretellix, Skild AI and Uber"
`[VERIFY]`. And `R04 §5.6` already logs the scale ladder: "Cosmos 3 family … Super (64B), Nano
(16B), and Edge (4B)", able to "generate images, videos, synchronized audio, and action
sequences", under the "OpenMDW-1.1 License" `[via R04,` [NVIDIA/Cosmos](https://github.com/NVIDIA/Cosmos)`]`.

**Note the three-part structure and steal it.** Reason / Predict / Transfer maps onto
*understand / imagine / render*, and a surveillance simulator needs exactly those three
capabilities with exactly that separation: a behaviour engine that reasons about what an actor
would do, a scenario engine that rolls it forward, and an imaging chain that renders it as a
particular camera would see it.

**The limits, quoted in full from `R04 §5.6` because they are the best single paragraph in this
repo on generative-video hype** `[via R04]`: "(a) no exact ground truth — no boxes, no
identities, no calibration, no world coordinates, so they cannot replace a simulator for
supervised surveillance training; (b) identity drift over seconds, which is fatal for the *only*
thing tracking and re-ID care about; (c) no controllability of the specific rare behaviour you
need ('hand a bag over at 22:03 in camera 7's blind spot'); (d) physics that looks right and is
not (feet slide, occlusion order flips); (e) licensing and provenance exposure if the model was
trained on scraped surveillance-like footage." The honest 2026 use cases are "**appearance
restyling of simulator output**, **rare-condition augmentation**, **operator-facing visual search
pre-training**, and **scenario ideation** — not label-bearing data generation" `[via R04]`.

**Genie 3-class interactive world models** (DeepMind) are the closed frontier of controllable
world generation; they change the *ideation* and *interactive-agent-training* story and do not
change the label story. `[VERIFY — not sourced this session.]` My forecast `[judgement]`: by
2029, generative world models will produce *consistent identities over minutes* and *exportable
approximate geometry*, at which point limitation (b) softens and the hybrid architecture
rebalances toward pixels. Limitation (a) — exact metric ground truth — is a structural property
of sampling from a learned distribution and will not be solved by scale; it will be solved by
hybrid pipelines. **Which means the geometry-owning simulator does not become obsolete. It
becomes the supervisor of the generative model.**

### 3.4 World models as prediction, not generation: V-JEPA 2

**V-JEPA 2** matters less for pixels than for *prediction in latent space*: it "achieves strong
performance on motion understanding with 77.3 top-1 accuracy on Something-Something v2" and
"state-of-the-art performance on human action anticipation with 39.7 recall-at-5 on
Epic-Kitchens-100" `[VERIFY —`
[Meta AI blog](https://ai.meta.com/blog/v-jepa-2-world-model-benchmarks/)`]`. It can be
"post-trained into an action-conditioned world model (V-JEPA 2-AC) using fewer than 62 hours of
unlabeled robot video, enabling zero-shot robotic planning" `[VERIFY]`. Meta also shipped three
physical-reasoning benchmarks — "IntPhys 2, Minimal Video Pairs (MVPBench), and CausalVQA"
`[VERIFY]`.

**Why an ISR product should care `[judgement]`:** *action anticipation is intent prediction with
a respectable name.* `R03` treats intent as the hardest open problem; 39.7 recall@5 on
Epic-Kitchens is a sober reminder of what "anticipation" currently means (five guesses, kitchen
domain, ~40% of the time one is right). But the architectural idea — **predict the future latent,
and treat prediction error as the anomaly score** — is the most principled anomaly-detection
framing available, and it is *self-supervised*, which directly attacks `R03 §10` item 4
("scene-dependent normality with zero on-site labels"). A per-camera V-JEPA-style predictor,
fine-tuned on that camera's own quiet hours, whose surprisal is the anomaly signal, is the most
promising research bet in this document. It also has the right economics: no labels, per-site
adaptation, and a scalar output you can threshold and calibrate.

---

## 4. The tracking and identity frontier

### 4.1 Promptable trackers: SAM2 / SAMURAI

`R01 §3.9` has the verdict already, and it has not changed: SAMURAI adds "temporal motion cues
with a motion-aware memory selection mechanism" and gains "+7.1% AUC [on LaSOT_ext], +3.5% AO
[on GOT-10k] over SAM 2 baseline" `[via R01]`; but this family is "excellent single-object,
prompted, forensic" and "poor for the always-on" case ("no detection, no identity management").
The recommendation stands: "Build the forensic feature on SAM2/SAMURAI; do not build the
always-on pipeline on it" `[via R01]`.

**What changes with SAM 3 `[judgement]`:** the "no detection" half of that objection is now
partially answered — promptable *concept* segmentation returns all instances with IDs, which is a
detector. The remaining objections are cost, calibration and crowd-scale association. **The
2027–2029 prediction:** a SAM-3-lineage model becomes a credible always-on multi-object
tracker at 5–10 fps on a datacentre GPU and remains out of reach on a 2.5 W edge accelerator
(see §7). The architecture that wins on the edge is still distillation: use the big promptable
model to *teach*, ship the small model.

### 4.2 End-to-end and ID-as-prediction: MOTIP and the transformer line

`R01 §3.8`: **MOTIP** (CVPR 2025) "regard[s] multiple object tracking as an in-context ID
prediction problem" and "directly decodes the ID labels" from trajectories, reporting "69.6 HOTA
(no extra data) / 72.6 HOTA" (with extra data), both on the DanceTrack test set, with "60.4 / 63.2 AssA" [audit 2026-09-26: both figures are DanceTrack (MOTIP Table 1), not DanceTrack/SportsMOT] `[via R01 §3.8, §8]`.
The significance is architectural: **association stops being a hand-tuned Hungarian cost and
becomes a learned, contextual prediction.** That is the same movement that ended hand-tuned
features in detection a decade earlier, and it will end hand-tuned association.

`R01 §8`'s three leaderboard-reading rules must be applied to every number in this section, and
are worth reprinting because they are the most transferable epistemics in this repo `[via R01]`:
**detector-normalise** (a two-point MOTA delta between "trackers" can be a detector delta);
**online vs offline** (AFLink/GSI post-processing, ensembling and validation-set training are
"unavailable in a live alerting product"); and **MOT17 is saturated and unrepresentative**.

**End-to-end MTMC transformers** are the obvious next step and the obvious trap. `R02 §8` item 1
already names the reason: GMVD "showed BEV detectors memorise rigs", and the open question is
"a detector that takes calibration as *input* and works on an unseen 9-camera layout zero-shot"
`[via R02]`. `[judgement]` **Any end-to-end MTMC model that does not take extrinsics as an
explicit input is memorising a site, and will be re-trained per customer. That is a services
business pretending to be a product business.** The single highest-leverage architectural
requirement for MTMC in the next five years is *calibration-conditioned* rather than
*calibration-implicit* models — and a simulator that can randomise camera topology is the only
practical way to force that property.

### 4.3 Tracking any point: CoTracker3

Point tracking (CoTracker3 and the TAP line) is the quietly-useful frontier. `[VERIFY — numbers
not re-verified this session.]` Its surveillance value `[judgement]` is not "track people" —
it is:
* **Self-calibration and drift detection.** Long-term point tracks on static structure give you a
  continuous homography residual, which is exactly the "calibration that self-heals" of `R02 §8`
  item 10 and the displacement detector of `R04 §4.1` ("global homography residual vs a
  reference").
* **Tamper detection.** Point-track collapse = defocus, cover, or dome crazing.
* **Fine-grained motion evidence.** Climbing, throwing, handover: the kinematics of the *limb*
  and the *object*, not the box. Owner–object association (`R03 §10` item 5) is a point-tracking
  problem more than a detection problem, and nobody has framed it that way.

### 4.4 3D human mesh from CCTV: Multi-HMR, SAM-3D-Body

Multi-person 3D mesh recovery from a single image (Multi-HMR and successors) and the emerging
SAM-3D-Body line push toward **metric, articulated, occlusion-aware human state from one camera**.
`[VERIFY — no numbers re-verified this session.]` Why this is more than a graphics demo
`[judgement]`:

* **It collapses three analytics into one representation.** Pose anomaly, gait, and height/body-shape
  re-ID all read off the same mesh. `R02 §3.5` establishes gait as "the clothing-invariant
  fallback" but with hard constraints: it "needs a clear walking sequence (≥ ~1 gait cycle, i.e.
  ~1 s at 1.4 m/s)" and in the wild gives "~50–70% Rank-1, not ~90%" `[via R02]`. A mesh gives you
  body *shape* — which is clothing-invariant in a different way from gait and does not need a
  gait cycle.
* **It makes behaviour rules metric and therefore portable.** "Climbing" as *vertical displacement
  of the pelvis relative to the ground plane exceeding 1.2 m with hands above shoulders* is a rule
  that transfers between sites. "Climbing" as a learned video classifier is a rule that does not.
* **It is the natural bridge to the simulator.** Our simulator emits SMPL-class parameters as
  ground truth for free. **Mesh-space ground truth is a differentiator we already own.**

The caveat is severe and must be stated: at the pixel heights that matter (`R04 §2`: 15–80 px
people, "~60–80 px: pose/gait usable"), monocular mesh recovery is mostly prior, not evidence.
Report per-pixel-height accuracy or do not report it.

### 4.5 Whole-body biometrics at range: BRIAR / FarSight, and the fusion result

The most credible programme remains IARPA **BRIAR**, whose dataset is "over 350,000 …" `[via R02 §3.6 —
partial quote; verify the full sentence]`, and the headline fusion result is large and specific:
FarSight "achieves a 34.1% absolute gain in 1:1 verification accuracy … and a 17.8% reduction in
false negative identification errors (FNIR@1% FPIR)" `[via R02 §3.6,`
[FarSight](https://arxiv.org/pdf/2306.17206)`]`, with the companion work *Person Recognition at
Altitude and Range: Fusion of Face, Body Shape and Gait* `[via R02]`.

**Three things follow, and they are the most under-appreciated facts in commercial video
analytics `[judgement, grounded in R02]`:**

1. **Face is a special case, not the default.** `R02 §5` concludes "general CCTV at standoff is a
   body/gait problem, and face recognition only works where the geometry was designed for it"
   `[via R02]`. The product implication: build the body/gait/shape pipeline first, and treat face
   as an opportunistic high-precision cue gated on inter-eye distance.
2. **Fusion policy should be evidence-gated, not fixed-weight.** `R02 §3.6`: "use face when IED is
   sufficient, body/gait otherwise" `[via R02]`. That requires *per-frame face-visibility and IED
   ground truth* — which, again, a simulator can produce and a real dataset essentially cannot.
   `R02 §11` item 6 already lists exactly this as a simulator requirement.
3. **The metric must change.** `R02 §8` item 6: "Open-set metrics (FNIR@FPIR, as used by
   BRIAR/FarSight) should replace CMC in security work" `[via R02]`. CMC/Rank-1 assumes the person
   is in the gallery. In a real estate they usually are not.

**Long-term whole-body re-ID remains the hardest identity problem and is not closing.** `R02 §8`
item 3: "LTCC Rank-1 [~40 %, CAL 40.1; retired: 'in the 30s'] is the honest state of the art; nothing yet gets long-term ReID
to a level where an automatic alert is defensible" `[via R02]`. And item 4: DeepChange's 12-month
window "remains low" `[via R02]`. **Forecast to 2030 `[judgement]`: clothes-changing re-ID reaches
deployable quality for *candidate ranking with human adjudication* and does not reach deployable
quality for *automatic alerting*, because the failure mode is a false accusation, and the
acceptable rate for that is near zero.**

Also note the attack surface, from `R02 §4.3`: gait spoofing needs no technology — "it was indeed
possible to spoof gait biometric systems by clothing imitation" — and "the cheapest real-world
gait attack is behavioural" `[via R02]`. Any biometric claim that does not come with a
presentation-attack story is incomplete.

---

## 5. Privacy-preserving analytics as a product category

### 5.1 The regulatory clock

`R02 §5.4` and `R03 §9.3` carry the primary material. The load-bearing facts:

* **EU AI Act Article 5** "prohibits placing on the market or into service AI systems for
  real-time remote biometric identification in publicly accessible spaces for law enforcement
  purposes", with prohibitions enforceable "in February 2025, with fines of up to €35 million or
  7% of global annual turnover" `[via R02 §5.4]`. Exceptions are narrow and procedurally
  expensive: "prior judicial or independent administrative authorisation, fundamental rights
  impact assessment, geographic and temporal limits, notification to market surveillance and data
  protection authorities, and registration in the EU database" `[via R02]`.
* **The scoping that decides product strategy**, quoted from `R02 §5.4`: "The prohibition applies
  only to law enforcement. This prohibition does not apply to private actors in
  non-law-enforcement contexts" — *and* "**tracking/ReID without biometric identification is a
  different, high-risk-but-permitted category**, which is precisely why an appearance-and-geometry
  MTMC product is more legally tractable in the EU than a face-matching one" `[via R02]`.
* **Emotion recognition** is prohibited "at education and workplace", and Article 5(1)(g) bans
  biometric categorisation "to deduce or infer their race, political opinions, trade union
  membership, religious or philosophical beliefs, sex life or sexual orientation" `[via R03 §9.3]`.
  `R03`'s product conclusion is exactly right and should be a written engineering rule: "**Never
  label a module 'emotion' or 'anger' when it is in fact 'rapid limb motion + proximity'**"
  `[via R03]`.
* **High-risk (Annex III) obligations** — "risk management, data governance, logging, human
  oversight, accuracy/robustness documentation and post-market monitoring" — plausibly catch
  CNI security analytics, though `R03 §9.3` flags the Annex III wording as unverified `[via R03,
  marked unquoted there]`. **This remains the single most important open legal question for this
  product line and should be resolved with counsel, not with search engines.** `[VERIFY]`
* **UK**: the ICO regime plus the **Data (Use and Access) Act 2025** `[via R06 §5, VERIFY]`, with
  the UK's "pro-innovation approach" white paper as the contrasting posture `[via R06]`. A DPIA is
  "effectively mandatory for behaviour analytics" `[via R03 §9.2]`, and for audio the ICO position
  is to "switch audio recording off by default unless there is a much stronger justification"
  `[via R05 §15 bullet 11]`.

**The dates to plan against `[judgement, VERIFY the specifics]`:** Article 5 prohibitions bit in
February 2025; GPAI obligations through 2025; the high-risk regime phases in across 2026–2027
with the longest tails for products embedded in regulated equipment. For an engineering roadmap
the relevant consequence is not the date — it is that **from 2026 onward, "we tested it and it
works" is not an acceptable answer; per-condition, per-subgroup performance evidence with a
documented test corpus is.** `R04 §8` item 10 says it: "EU AI Act-style obligations for high-risk
surveillance systems will demand per-condition, per-demographic performance evidence. Nobody has
a standard way to produce it; **a simulator is the only practical instrument**" `[via R04]`.

### 5.2 The technical privacy toolkit, ranked by whether it actually helps

`[judgement, with sources where available]`

1. **Analyse-at-the-edge, transmit events not pixels.** The strongest privacy argument and also
   the strongest cost argument. `R05 §15` bullet 11 gives the pattern for audio —
   "`(t, mic_id, event, spl_db, doa_deg)` … is a compliance architecture, not just a schema"
   `[via R05]` — and it generalises: the wire format should be structured events plus
   on-demand clip retrieval, never a continuous video egress.
2. **Embeddings-only pipelines with scoped watchlists.** `R02 §8` item 9 names it: "embeddings-only
   pipelines, on-camera processing, and provable watchlist-scoping" `[via R02]`. "Provable" is the
   word to build to: cryptographic enrolment receipts, per-watchlist purpose binding, automatic
   expiry.
3. **Face/plate redaction as a default, reversible under authorisation.** Two-key export.
4. **Synthetic-only training as a compliance posture.** `R04 §7` makes the strong version of this
   argument: "We can *balance* skin tone, age, body type, gait and clothing by construction"
   producing documentation "that no scraped dataset's metadata" can `[via R04]`. **This is
   the vendor's single best regulatory story and it is under-sold.** A model whose training set
   contains no real person's likeness is a fundamentally easier conversation with a DPO.
5. **Event cameras as privacy-by-physics.** DVS output has "no absolute intensity, no texture,
   essentially no appearance re-ID" `[via R04 §3.5]` — which is a *limitation* for analytics and a
   *feature* for privacy. A perimeter sensor that physically cannot recognise a face is a
   compelling product for schools, hospitals, workplaces and residential edges.
6. **Federated learning** — real, and mostly useful for *model improvement across customers
   without data egress*. `R03 §3.4` already cites *Exploring Personalized Federated Learning
   Architectures for Violence Detection* ([arXiv 2504.00857](https://arxiv.org/pdf/2504.00857))
   `[via R03]`. Caveat `[judgement]`: federated learning protects the *pixels*, not the
   *inferences*, and gradient-inversion literature means it is not a privacy guarantee on its own.
7. **Differential privacy** — honestly, the weakest fit. DP is designed for aggregate statistics
   over many individuals. It is a good fit for *footfall counts and occupancy analytics* and a
   bad fit for per-incident alerting, where the entire point is to single out one person. Selling
   DP on an alerting product is a category error. `[judgement]`

### 5.3 Business models around privacy

`[judgement]`
* **Privacy-tier SKUs.** "Redacted mode", "no-biometrics mode", "events-only mode" as
  contractually enforced configurations with an audit trail — sold at a premium to public-sector
  and education buyers, not discounted as a degraded product.
* **Compliance evidence as a deliverable.** A per-deployment performance dossier: per-condition
  accuracy, per-subgroup accuracy, FA/camera-hour, drift monitoring. Charge for it. It is the
  Annex III artefact the customer will otherwise have to produce themselves.
* **Synthetic-data provenance certificates.** "No real person's likeness was used in training
  this model, and here is the asset manifest." Currently unsellable because nobody asks; by 2028
  a procurement checkbox. `[judgement]`
* **Audit-log-as-a-service.** Every query, every watchlist change, every export, immutable. The
  UK/EU market will require it; the US market will follow via litigation.

---

## 6. The sensor frontier

`[This section is mostly judgement plus material carried from R04 §3.5 and R05 Part A; treat
un-marked claims as engineering positions.]`

**4K/8K and multi-sensor cameras.** The resolution war is largely over and was won by *pixels on
target per pound*, not by sensor count. The operative fact from `H01`/`R04` is that "**most
analytics run on the substream**: 640×360 at 0.2–0.5 Mb/s, while the evidence clip is 4K. A
person at 40 m in the substream is **8 px tall**. Half of 'our detector missed it' tickets are
substream tickets" `[via H01]`. **Therefore: 8K changes nothing unless the analytics pipeline
gets access to the high-resolution stream with tiling, and tiling multiplies inference cost by
the tile count.** The real frontier here is *attention*: cheap wide-FOV detection that triggers
high-resolution tiled inference only on candidate regions. That is a product feature, not a
sensor feature.

**Multi-sensor (multi-imager) cameras** — four or five imagers in one dome, one cable, one
licence — are the genuinely important 2024–2026 hardware trend, because they change the economics
of coverage and they create *overlapping fields of view by default*, which is the precondition for
BEV/multi-view detection (`R02 §2`). `[judgement]` A multi-imager dome is a pre-calibrated
micro-rig. Analytics that exploit intra-dome overlap for 3D localisation would be a differentiator.

**SWIR.** InGaAs SWIR sees through haze and some smoke, images covert 1,550 nm illumination, and
distinguishes materials that look identical in visible light. Historically priced for defence;
quantum-dot and Ge-on-Si SWIR are pushing cost down. `[VERIFY — cost curve not sourced.]` My
position: SWIR is a 2028+ niche for border and maritime, and a red herring for commercial CCTV.

**Radar-on-camera.** `R04 §3.5` has the operational truth: "radar-camera fusion is the mature
perimeter answer … radar cues the PTZ, camera confirms is the deployed architecture" `[via R04]`,
and `R05 §15` bullet 1: "**The camera is the only sensor that closes an alarm; everything else is
a cue.** Design every non-camera sensor as a pointing device, and budget the pointing latency"
`[via R05]`. Radar modules are now cheap enough to co-package with a camera. The 2026–2030 trend
is **the fused sensor as a single SKU**, which removes the calibration truck-roll that `R05 §13`
item 4 names as an open problem — you calibrate at the factory.

**LiDAR cost curve.** Automotive volume has crashed unit cost, but `R04 §3.5` is right that
"LiDAR appears in the literature far more than in security budgets, and rain/fog/snow degrade it
too" `[via R04]`. LiDAR's real security niche is *height-gated volumetric tripwires* in
high-value sterile zones and *ground-truth capture for site survey* (a LiDAR-SLAM backpack walk,
which `R02 §2` already recommends for calibration ground truth `[via R02]`).

**Event cameras.** The strongest technical bet on this list and the weakest commercial one.
`R04 §3.5`: "microsecond latency and ~120 dB dynamic range, no motion blur, and very low power —
properties that map almost perfectly onto the CCTV failure modes", plus the crucial simulator
insight: "simulators (ESIM, v2e) can synthesise events from high-frame-rate rendered video,
which means **our UE5 pipeline could emit an event stream essentially for free**" `[via R04]`.
Limits: "no absolute intensity, no texture, essentially no appearance re-ID, tiny ecosystem, and
almost no installed base in security" `[via R04]`, and `R04 §8` item 14: "no installed base and
no benchmark, but the physics is a near-perfect match for night perimeter work. High risk, high
reward" `[via R04]`. **Recommendation: build the simulator's event-stream emitter (cheap),
publish the first event-camera perimeter benchmark (differentiating), and do not put event
cameras on a product roadmap until a customer asks.**

**Acoustic arrays.** The ceiling is low and known. `R05 §15` bullet 9: audio "aggression"
detection "is arousal detection" — the vendor's own words, that the detector "analyzes sound but
doesn't take words or meaning into account" and "guaranteed 100% that the system will at times
misconstrue innocent behavior" `[via R05,` ProPublica `]`. Bullet 10: "an F-score of 0.90 on
DCASE-style 30-second mixtures still yields a mostly-nuisance alert stream when real glass breaks
happen once a year per site" `[via R05]`. Bullet 12: "**The microphone in the dome is a bad
microphone**" `[via R05]`. Acoustic gunshot/glass/scream detection is a *cueing* modality with a
severe base-rate problem and a UK legal problem. Ship classified events, never waveforms.

**RF sensing and Wi-Fi 7 / IEEE 802.11bf.** The standardisation of WLAN sensing is the
interesting 2025–2027 development: sensing becomes a first-class service of commodity access
points, which means *device-free presence and coarse motion sensing without any camera*, at
essentially zero marginal hardware cost, in every building that has Wi-Fi. `[VERIFY — 802.11bf
status and timeline not sourced this session.]` `R05 Part A` already covers the Wi-Fi probe/MAC
side, including that randomisation causes over-counting — schemes "make conventional
MAC-address-based crowd monitoring systems count the same device more than once" `[via R05]` —
and the through-wall pose line (MIT RF-Pose) `[via R05]`. The open problem `R05 §13` item 3
("RF-to-vision association in crowds, under randomisation, with multi-device and device-less
people — and the labelled data to train it, which barely exists **outside simulation**")
`[via R05]` is a direct simulator opportunity: we can generate RF/vision association ground truth
that does not exist in the real world. **My forecast: 802.11bf-class sensing becomes a standard
*occupancy and tamper corroboration* input by 2030, and never becomes an identification
modality in commercial products because the legal exposure is worse than cameras and the accuracy
is worse than cameras.**

**Satellite, aerial and WAMI.** Planet's daily global cadence and Maxar's sub-30 cm imagery have
made *change detection at national scale* routine; wide-area motion imagery (WAMI) makes
*persistent city-scale tracking* technically possible and politically radioactive. `[VERIFY]`
For a product like the vendor's the relevant convergence is **cross-scale tasking**: a satellite change
detection cues a drone, which cues a ground camera. The hard technical problem is not any single
tier; it is **identity and geometry handover across scales and sensors**, which is `R02 §8` item 2
(moving and mixed-modality networks) at a larger scale.

**Drones-as-cameras and counter-UAS.** Drones invert every assumption in the CCTV literature:
moving camera, oblique-to-nadir view, changing illumination, no fixed calibration.
`R02 §8` item 2 names the mixed fixed/drone/body-cam association graph as open, citing DIVOTrack
and MATRIX `[via R02]`. Counter-UAS is the mirror product: detect, classify, track and (legally)
mitigate. `R05` covers the Remote ID surface (DJI AeroScope, FAA Part 89) `[via R05 sources]`.
`[judgement]` The 2026–2032 growth market in physical security is *the airspace above the
perimeter*, and the analytics stack for it is radar + RF + EO/IR fusion — i.e. exactly the vendor's
stated multi-sensor surface (`R06`: "perimeter and area monitoring using fused visible light and
IR, RF, passive …" `[via R06]`). A simulator that models the airspace tier as well as the ground
tier is substantially more valuable than one that does not.

---

## 7. The compute frontier

`[Verified anchors from R01 §5.1; forward-looking claims are judgement/VERIFY.]`

Two hard anchor points to reason from `[via R01 §5.1]`:
* "**The Jetson Orin NX 16GB can handle up to 18 streams of 1080p30**, making it suitable for
  mid-sized video analytics deployments" ([Seeed Studio](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/)). [staleness v2: decode ceiling only — with detect+ReID compute ≈ 12 cams/NX, so 40 cams → 4 NX; FACTS, 38 §2.5]
* **Hailo-8**: "26 Tera-Operations Per Second (TOPS) with best-in-class power efficiency and
  typical power consumption of 2.5W", and independently "can handle roughly 4 full-rate 1080p
  detection streams with typical detect rates" [audit 2026-09-26: 26 TOPS / 2.5 W confirmed on hailo.ai; 18× 1080p30 H.265 decode for Orin NX 16GB confirmed on NVIDIA's Jetson Orin spec table]
  ([Hailo-8](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/);
  [edgeaistack](https://edgeaistack.ai/blog/hailo-8-vs-8l-vs-10h-2026/)).

And the mental model that saves more engineering time than any benchmark `[via R01 §5.1, lore]`:
"**you are almost never inference-bound first.** In order, the bottlenecks are usually (1)
H.264/H.265 **decode** — a fixed-function NVDEC or VPU with a hard stream limit, independent of
your model; (2) memory bandwidth for frame copies and colour conversion; (3) inference; (4) the
tracker, if it runs on CPU with a per-track Python loop; (5) the ReID embedding, which is
per-detection and therefore scales with crowd size, not camera count — a queue of 60 people can
cost more than 10 empty cameras."

**The 2026–2030 hardware picture `[judgement + VERIFY]`:**

* **Jetson Thor / Blackwell-class edge.** An order-of-magnitude step in edge FLOPs and, crucially,
  in *memory capacity and bandwidth*, which is what a 7B VLM at the edge actually needs. This is
  the enabling hardware for "small VLM on the box, running on triggered clips only". It does not
  enable "VLM on every frame of every camera" and will not by 2030 — the arithmetic in §1.4 is
  four to five orders of magnitude out, not one.
* **Hailo-10 / next-gen NPU.** The generative-AI-at-the-edge pitch at single-digit watts. The
  realistic 2027 edge deployment is: closed-vocabulary detector + tracker + re-ID embedder at
  full rate, plus a 1–3 B VLM invoked a few times per minute per camera for alarm corroboration
  and captioning.
* **Apple / Qualcomm NPUs.** Matter for the *client* side, not the camera side: on-device review
  and redaction on an operator's tablet, and for body-worn devices.
* **Neuromorphic.** Pointer to `D05`. Summary position: the physics argument (event-driven,
  sparse, µW–mW) is genuinely aligned with always-on perimeter sensing; the software ecosystem
  and installed base are not, and no security procurement in 2026 will accept it. Watch, do not
  bet.
* **Cost per stream trend.** `[my estimate, to be replaced with measured data]` The
  inference-hardware cost of a single 1080p detect-and-track stream has fallen roughly an order
  of magnitude per five years since 2015 and is now a small fraction of the camera's own cost.
  **The binding cost is no longer inference; it is (a) video decode, (b) storage/egress, and (c)
  human review of alarms.** A product strategy aimed at reducing inference cost is optimising the
  wrong term. A product strategy aimed at reducing human review minutes per incident is
  optimising the right one.
* **Model compression.** Quantisation-aware training to INT8/INT4, structured pruning,
  distillation from the promptable giants, and — increasingly — *distillation of the VLM's
  decision into a small classifier for the specific site*. `R06 §4` already names the constraint:
  "every model must survive quantisation and a Jetson-class or neuromorphic power [budget]"
  `[via R06]`. Add the TensorRT deployment landmine from `R01 §5.1`: "engine files are GPU-arch-
  and version-specific — an engine built on one driver may not load on another" `[via R01]`.

---

## 8. The evaluation frontier

This is where I believe the largest unclaimed value in the entire field sits, and where a
simulator-owning organisation has a structural advantage that no model-owning organisation can
copy.

### 8.1 The four indictments of current evaluation, already established in this repo

1. **Frame AUC is the wrong metric.** `R03 §8`: academia uses frame-level AUC "almost
   exclusively, and government uses rate-based event scoring" `[via R03]`.
2. **The operating-point gap is 1,200×.** `R03 §5.2`'s arithmetic: a 500-camera site needing ~20
   actionable alarms per 8-hour shift permits **0.005 FA per camera-hour**, versus ActEV's measured
   **0.1 FA/minute = 6 per camera-hour** `[via R03]`. "This single comparison is … the strongest
   possible argument that progress must come from *verification architecture and corroboration*,
   not from squeezing the last AUC point out of a detector" `[via R03]`.
3. **Per-frame precision hides eternal false positives.** `H01`/`R01 §1.5`: "A detector with 99.9%
   per-frame precision on a 15 fps camera still emits **~1,300 false positives per day per
   camera**", and "**Your worst false positives are stationary and eternal** … a retail-window
   mannequin fires **every frame for years**" `[via H01/R01]`.
4. **Benchmarks are split wrong.** `R03 §8`: "Any evaluation must be split by scene/camera, not by
   clip" `[via R03]`, and background bias is documented (ACM MM 2019, *Exploring Background-bias
   for Anomaly Detection in Surveillance Videos*) `[via R03]`.

### 8.2 What the 2026–2030 evaluation frontier looks like

**(a) Continuous benchmarking.** Evaluation stops being a paper table and becomes a service: every
model build scored against a fixed, versioned scenario suite, with per-condition breakdowns, on
every commit. `[judgement]` This is CI for perception. The reason nobody does it is that nobody has
a corpus they can regenerate on demand — which is exactly what a simulator is.

**(b) Synthetic scenario regression.** The specific artefact: a suite of N parameterised scenarios
(intrusion, climb, loiter, handover, abandonment, tailgating, crowd surge) × M conditions (rain,
fog, night+IR, low bitrate, sun glare, wet tarmac) × K rig topologies, with exact ground truth,
scored with the i-LIDS timed rule. `R05 §5.2` gives the rule verbatim: an alarm within 10 s of
intrusion onset is a TP, "alarms after 10 s are counted as an FP" `[via R05]`, and the corollary
that should be tattooed on the alerting team: "**A late detection is scored as a false positive**
… Every debounce frame you add spends that budget" `[via R05 §15 bullet 6]`.

**(c) Stratified reporting as the default output format.** Not "mAP 0.87" but a table: recall at
each pixel-height band × each condition × each subgroup, plus FA/camera-hour by cause. `R01 §4`:
"recall at the required pixel height, not average recall, is the missed-alarm number. Everything
else is a proxy" `[via R01]`.

**(d) LLM-as-judge for events — useful, and dangerous in three specific ways.** `[judgement]`
Using an LLM/VLM to adjudicate whether an alert was correct is attractive because human
adjudication is the cost bottleneck. The risks are concrete:
* **Circularity.** If the judge shares a backbone or training corpus with the system under test,
  the evaluation is self-congratulatory. `R03 §10` item 10 already names "benchmark contamination
  by web-scale VLM pretraining; no accepted audit method exists" `[via R03]`.
* **Judge hallucination.** The judge is subject to the same extrinsic non-factual failure as the
  system (`R05 §12`), and a hallucinating judge silently corrupts every downstream number.
* **Position/verbosity/self-preference bias.** Well documented in text LLM-judge literature and
  there is no reason to expect video to be better. `[VERIFY]`
The defensible protocol: **LLM-as-judge is permitted for triage and for scaling *negative* labels
(confirming that nothing happened), never for adjudicating positives**, must be calibrated against
a human-labelled sample each release with reported agreement (κ), must use a different model family
from the system under test, and its verdicts must be stored as *evidence-linked*, auditable
records, not as scores.

**(e) Red-teaming as a standing function.** `R02 §8` item 5 and `R03 §10` item 9 both name
adversarial/evasive behaviour as essentially unstudied "because you cannot collect it" `[via R03]`.
A simulator can collect it: camera-aware path planning, blind-spot outfit swaps, crowd cover, role
disguise (`R02 §11` item 5: "appearance mutation with hidden-identity truth: outfit swap, accessory
hand-off, hood/mask, gait change" `[via R02]`). **An "adversarial POD" benchmark — probability of
detection against an adversary who knows the camera layout — does not exist publicly (`R05 §13`
item 6) and is the single most defensible thing this repo could publish.**

**(f) Assessment metrics, not just detection metrics.** `R05 §13` item 7: "the industry measures
detection; the bottleneck is human assessment, and there is no standard metric for it" `[via R05]`.
Candidate metrics: seconds-to-verify per alert, operator agreement rate with the system's
classification, clip-sufficiency rate (fraction of alerts whose attached clip is sufficient to
adjudicate without opening the VMS). `H02` already frames the goal: alerts must "**be verifiable
in seconds**" `[via H02]`.

---

## 9. What is obsolete, what became easy, what remains hard

### 9.1 Obsolete (with the argument, and with the honest counter-argument)

**1. Background subtraction as a *primary* detector.** Obsolete as a primary. MOG2/KNN-class
methods fire on every illumination change, headlight, cloud shadow, rain streak and swaying
branch, which is precisely the nuisance list the industry quotes: false alarms "caused by anything
from lighting to the weather to foliage in the camera view" `[via R03 §5.3, Calipsa]`. *Counter:*
it remains excellent as a *cheap gate* to avoid running a detector on a static frame, and as a
tamper/freeze signal. Keep it as a pre-filter; never let it raise an alarm.

**2. Handcrafted appearance features (HOG, colour histograms, LBP, HOG+SVM people detection).**
Obsolete for recognition. The entire re-ID and detection literature moved to learned embeddings a
decade ago and the gap is not closable. *Counter:* handcrafted *image-quality* features are not
obsolete and are in fact preferable for tamper analytics — `R04 §4.1`: "the useful features in
practice are embarrassingly simple: edge-energy percentiles (defocus), frame-difference entropy
(freeze), histogram occupancy + clipping fraction … block-edge energy at 8/16 px periodicity
(bitrate starvation)" `[via R04]`. Distinguish *recognition* (learned) from *diagnostics*
(handcrafted). The 2010–2016 tamper papers are old because the problem was solved, not because it
was abandoned — and `R04 §8` item 13 notes there is no modern benchmark at all.

**3. Rule-only analytics with no learned perception.** Obsolete. A tripwire over a
background-subtraction blob is the product that created the "98% of Security Camera Alarms Are
False" statistic `[via R03 §5.2, IntelliSee]`. *Counter, and it is a strong one:* rules are not
obsolete — *rules without learned perception* are. The durable architecture is learned perception
feeding an explicit, inspectable rule layer (§2.4). Anyone who says "no more rules, just AI" is
selling an uninspectable system into an industry that needs to explain itself in court.

**4. Per-camera silo configuration.** Obsolete, and the most expensive obsolete thing in the
industry. Configuring 500 cameras individually is why deployments take nine months and why
`R05 §15` bullet 5 finds that "the programme dies of uptime, not of accuracy" `[via R05, EFF
border-tower audits]`. The replacement: site-level semantics (a 3D site model with named regions
and rules attached to *places*, not to *camera pixel polygons*), automatically projected into each
camera's view. This is a direct consequence of having a 3D twin (§3.2) and it is a large,
defensible product feature.

**5. Manual calibration.** Obsolete as a *manual* step. Learned single-image geometry (GeoCalib and
successors `[via R02 §8 item 10]`), pedestrian-based auto-calibration (people are metre sticks with
known height distributions), and continuous point-track homography monitoring (§4.3) make
auto-calibration feasible. `R02 §8` item 10: "Mounts get bumped, PTZ encoders drift, buildings
settle. Continuous auto-recalibration … is the obvious product, and **nobody ships it**"
`[via R02]`. *Counter:* metric accuracy still needs a survey anchor for court-grade measurement;
auto-calibration gets you operational accuracy, not evidential accuracy.

**6. Fixed-vocabulary class lists as a product boundary.** Obsolete as a *marketing* boundary
(§1.1). *Counter, important:* fixed vocabulary remains the right *engineering* boundary for the
always-on alerting path, because an alarm class is a thing you must be able to measure FA/hour for.
The resolution: open vocabulary for search and authoring, closed and measured vocabulary for
alerting.

**7. VMS-locked analytics.** Obsolete. Analytics welded to one VMS cannot be evaluated, cannot be
replaced, and cannot be improved on a model-release cadence. The market has moved to ONVIF/MQTT
event buses and now to MCP tool servers (§2.1). *Counter:* the VMS owns the video, the users, and
the storage; "VMS-agnostic" in practice means "integrates with six VMSs badly". The honest position
is a thin, well-specified event contract plus deep integrations with the three VMSs your customers
actually own.

**8. On-prem-only — the debate, argued both ways `[judgement]`.**
*For obsolescence:* model release cadence is now monthly; fleet-wide evaluation, drift monitoring
and continuous benchmarking (§8.2a) are impossible without telemetry; the VLM/agentic layer needs
elastic GPU that no site will buy; and the cloud false-alarm-filtering vendors demonstrated the
business model works — Calipsa "100% cloud-based … remove over 90% of event-based video false
alarms", one station reporting it "filtered out over 1.9m false alarms in the last 30 days"
`[via R03 §5.3]`.
*Against obsolescence:* CNI, defence and government sites will not egress video, period; bandwidth
from a border tower is a hard physical constraint; latency budgets of 10 s (i-LIDS) are hostile to
round trips; and `R05`'s finding that the camera "is the only sensor that closes an alarm" implies
the decision loop must live where the camera is.
**My resolution:** on-prem-*only* is obsolete; on-prem *inference* is not. The durable architecture
is **edge inference, local decision, structured-event egress, cloud-side model management,
evaluation and long-horizon analytics — with a hard air-gap mode that degrades features rather than
failing.** Anyone selling cloud-only into CNI is not going to win, and anyone selling
on-prem-only will lose the model-improvement race.

**9. Also obsolete, briefly:** per-frame-precision reporting (§8.1.3); CMC/Rank-1 as the re-ID
metric in security (`R02 §8` item 6); MOT17 as a headline benchmark (`R01 §8`); "accuracy" claims
without a denominator and an adjudicator (`R05 §15` bullet 7 — ShotSpotter's "97% accuracy"
versus "89% of … deployments turned up no gun-related crime" is "the same system measured two
ways" `[via R05]`); and PSNR-optimised enhancement in front of a machine consumer (`R04 §8`
item 3).

### 9.2 What became easy (2019 → 2026)

Each with its evidence and its residual catch.

* **Person/vehicle detection in good conditions.** Commodity. Any competent team reaches
  near-ceiling on daylight, well-framed, >80 px targets. *Catch:* `R01 §1.5` — 99.9% per-frame
  precision is still 1,300 FP/day/camera `[via R01]`, and `H01` — the literature is automotive:
  "eye height, forward lens, daylight, 50–300 px people, 30 fps, high bitrate, 30-second clips.
  Real CCTV is 3–6 m mount at 20–45° depression, **15–80 px people**" `[via H01]`.
* **ALPR.** A solved commodity in cooperative geometry with plate-specific illumination. *Catch:*
  it is solved *as an engineering system* (lens, angle, IR illuminator, shutter, jurisdiction
  syntax), not as a model.
* **Counting and occupancy.** Easy, and now available from three independent modalities (camera,
  mmWave radar — TI's reference designs `[via R05]`, Wi-Fi). *Catch:* MAC randomisation causes
  over-counting `[via R05]`; and "easy" means ±5–10%, not exact.
* **Basic forensic search by structured attribute.** Easy and mature — BriefCam's "object size,
  colour, direction, dwell and speed", plus plate and vehicle make/model `[via R05 §11.1]`. And
  natural-language *front ends* onto it are now table stakes (Verkada, Ambient) `[via R05]`.
  *Catch:* "**The time and place filters are doing most of the work**" `[via R05 §11.1]`.
* **Single-camera short-horizon tracking.** MOT17-class performance is saturated `[via R01 §8]`.
* **Adding a new object class.** Days, not months (§1.1, §1.5).
* **Photoreal synthetic imagery.** UE5 + Omniverse + Cosmos Transfer have made *appearance*
  cheap. *Catch:* `R04` is emphatic that appearance was never the bottleneck — the bottleneck is
  the imaging chain and the label semantics, and the tells that break analytics are things like
  "**foot sliding** (breaks any gait or speed-based analytic)" `[via R04 §5.7]`.
* **Captioning and summarising a *short* clip.** Genuinely easy now, and genuinely useful for
  alert triage.

### 9.3 What remains hard (and why, with evidence)

* **Intent.** Hard because it is not in the pixels. The best available proxies are anticipation
  (V-JEPA 2's 39.7 recall@5 `[VERIFY]`) and behaviour composition. And the legal layer bites:
  inferring emotional state from biometric data is prohibited in workplace and education contexts
  `[via R03 §9.3]`. **The honest product position is "indicators", never "intent", and the honest
  engineering position is that a composition of geometric predicates over time (approach, dwell,
  test, retreat, return) is both more accurate and more defensible than a learned "intent"
  classifier.**
* **Rare events.** Hard because of base rates, not models. `R05 §15` bullet 10: "An F-score of
  0.90 … still yields a mostly-nuisance alert stream when real glass breaks happen once a year per
  site" `[via R05]`. No amount of model improvement fixes a 10⁻⁷ prior; only corroboration and
  cheap verification do.
* **Cross-camera identity under appearance change.** Hard and not closing: "LTCC Rank-1 [~40 %, CAL 40.1]
  is the honest state of the art" `[via R02 §8]`; DeepChange's 12-month results "remain low"
  `[via R02]`; in-the-wild gait is "~50–70% Rank-1, not ~90%" `[via R02 §9]` [audit 2026-09-26: dated — OpenGait model zoo lists GREW Rank-1 of 79.4 (DeepGaitV2-3D) and 85.8 (SkeletonGait++); ~50% is the 2019–21 generation].
* **False alarms at scale.** The 1,200× gap `[via R03 §5.2]`, the "3–4 false alarms and operators
  begin to distrust the system" threshold `[via R03]`, and the 500:1 cameras-per-operator ratio
  `[via R03]`. This is the central unsolved problem of the industry and it is an *architecture*
  problem, not a model problem.
* **Robustness to degradation.** `R04 §8` items 1–2: no real benchmark for people in adverse
  weather from fixed elevated CCTV, and "robustness transfer is unsolved: gains on synthetic
  corruption benchmarks do not reliably transfer to real degradation" `[via R04]`.
* **Evaluation itself.** §8. The metric the customer buys (FA/camera-hour at fixed recall,
  stratified by cause) is published by nobody `[via R01 §8]`.
* **Trust and operator reliance.** `R03 §7`: operators miss "up to 45% of screen activity" after
  extended monitoring `[via R03, VERIFY]`; and the ShotSpotter/Chicago OIG finding that "every
  alerting system changes the behaviour of the people attached to it, and that is part of its
  performance" `[via R05 §15 bullet 8]`.
* **Legal and evidential defensibility.** Chain of custody, provenance (C2PA/Content Credentials),
  reproducibility of a model version months later, and per-subgroup performance disclosure.
  `R05 §13` item 16: "provenance and authenticity fused into retrieval, so a retrieved clip
  carries a verifiable chain of custody" — nobody ships it.
* **Uptime, availability and calibration drift.** The unglamorous killer: "the programme dies of
  uptime, not of accuracy" `[via R05 §15 bullet 5]`; a 500-camera site "typically has 5–15% of
  cameras degraded at any moment" `[via R04 §4]`.
* **Wildlife vs human at the sensor level.** Explicitly unsolved: weather nuisance can be cut by
  ">90%" but the same method "cannot distinguish alarms caused by wildlife" `[via R05 §13 item 1]`.

---

## 10. Twenty-five features to add, and fifteen not to build

### 10.1 Twenty-five features, ranked by (value × feasibility)

Scoring is my own `[judgement]`: **V** = value to the customer, **F** = feasibility with a
simulator-owning team, both 1–5.

| # | Feature | V | F | Why it wins |
|---|---|---|---|---|
| 1 | **False-alarm budget simulator per rule** — before a rule goes live, estimate its FA/camera-hour from simulated site conditions | 5 | 5 | Directly attacks the 1,200× gap (`R03 §5.2`); no incumbent has it; only possible if you own a simulator |
| 2 | **i-LIDS-verbatim timed scoring in the eval harness** (TP within 10 s, FP after) | 5 | 5 | The protocol UK government buyers recognise `[via R05 §5.2]`; days of work |
| 3 | **Camera-health / tamper analytics with per-camera baselines** and change-alarming | 5 | 5 | 5–15% of cameras degraded at any time `[via R04 §4]`; no modern benchmark exists; keeps every other number honest |
| 4 | **Stratified performance dossier per deployment** (pixel-height × condition × subgroup × FA-by-cause) | 5 | 4 | The Annex III artefact (§5.1); a sellable deliverable |
| 5 | **Continuous auto-recalibration** from pedestrian observations + point-track homography residual | 5 | 4 | "Nobody ships it" `[via R02 §8 item 10]`; removes truck rolls |
| 6 | **Site-level semantic configuration** — rules attached to 3D places, projected into every camera | 5 | 3 | Kills per-camera silo config (§9.1.4); the largest deployment-cost reduction available |
| 7 | **NL-rule compiler with human-approved, versioned rule objects** | 5 | 4 | The trust mechanism for agentic surveillance (§2.4) |
| 8 | **Standing natural-language queries with per-query FA budgets** | 5 | 4 | The merge point of alerting and retrieval (`R05 §13 item 15`) |
| 9 | **Two-stage architecture: cheap always-on detection + VLM corroboration on triggered clips** | 5 | 4 | The only affordable VLM architecture (§1.4, `R03 §6.2`) |
| 10 | **Abstention / "I don't know" as a first-class output with calibration reporting (ECE)** | 4 | 5 | `R03 §10 item 8`; trivially implementable; enormously trust-building |
| 11 | **Evidence-linked alert packet** (clip ±10 s, boxes, track, rule, confidence, suppression log) verifiable in seconds | 5 | 5 | `H02`: alerts must "be verifiable in seconds"; attacks assessment cost (`R05 §13 item 7`) |
| 12 | **Adversarial POD benchmark** — POD against a camera-aware evader | 4 | 5 | Does not exist publicly (`R05 §13 item 6`); only a simulator can generate it |
| 13 | **Structured-attribute forensic index** (colour, size, direction, dwell, speed, bag, plate) with an NL front end | 5 | 4 | The part of "AI video search" that works `[via R05 §11.1]` |
| 14 | **Dynamic score thresholding** for embedding search | 4 | 5 | Verkada's published trick; "cosine similarity has no absolute meaning" `[via R05 §11.1]` |
| 15 | **Body/gait/shape-first identity with face as an IED-gated cue** | 5 | 3 | `R02 §5`: standoff CCTV is a body problem; also the legally tractable path (§5.1) |
| 16 | **Open-set re-ID metrics (FNIR@FPIR) replacing CMC** in all reporting | 4 | 5 | `R02 §8 item 6` |
| 17 | **Camera-placement optimiser** over a 3D site model targeting ≥60 px on all approach paths | 4 | 4 | Barely explored (`R04 §8 item 5`); natural pre-sales tool and a consulting revenue line |
| 18 | **Self-supervised per-camera normality model** (latent prediction error as anomaly score), adapted on that camera's quiet hours | 4 | 3 | Attacks zero-label site adaptation (`R03 §10 item 4`); V-JEPA-style (§3.4) |
| 19 | **Radar/RF/fence cue → camera confirm pipeline with explicit pointing-latency budget** | 4 | 4 | `R05 §15 bullet 1`; the deployed perimeter architecture |
| 20 | **Suppression audit log** — everything the system vetoed, with cause, queryable | 4 | 5 | Makes AND-gating safe (`R05 §15 bullet 4`: an AND-gate "silently lowers probability of detection") |
| 21 | **Privacy-tier SKUs** (redacted / no-biometrics / events-only) as enforced configurations | 4 | 4 | §5.3; opens education, healthcare and public-sector buyers |
| 22 | **MCP tool-server surface** for detector/tracker/index | 4 | 5 | Becomes a component in every customer's agent (§2.1) |
| 23 | **Simulator-driven CI for perception** — every build scored on the scenario suite | 4 | 4 | §8.2a; the capability no model-only vendor can copy |
| 24 | **Event-stream emitter in the simulator** (ESIM/v2e from high-rate renders) + first event-camera perimeter benchmark | 3 | 5 | Nearly free `[via R04 §3.5]`; high research visibility |
| 25 | **Provenance/C2PA signing of exported clips** with model-version attestation | 3 | 4 | `R05 §13 item 16`; evidential defensibility |

Honourable mentions that just missed the cut `[judgement]`: mesh-space (SMPL) ground truth
export; drone/airspace tier in the simulator; multi-imager intra-dome 3D localisation;
negative-control hallucination monitoring in production; per-subgroup drift alarms.

### 10.2 Fifteen things to remove, or never build

1. **Emotion / aggression-state classification on faces or bodies.** Prohibited in workplace and
   education contexts `[via R03 §9.3]` and technically indefensible (audio "aggression detection is
   arousal detection" `[via R05]`). Rename to the physical act or delete.
2. **"Pre-crime" / threat-propensity scoring of individuals.** `R03 §9` flags it; it is a
   reputational and legal catastrophe with no evidential basis.
3. **Real-time face matching in publicly accessible spaces sold to law-enforcement buyers in the
   EU.** Article 5 `[via R02 §5.4]`. The procedural exceptions are narrow and expensive; do not
   build the business on them.
4. **Always-on per-frame VLM inference on every camera.** The arithmetic in §1.4 refutes it.
5. **Always-on primary alerting on open-vocabulary detectors.** Distribution-shift fragility
   `[via R04 §3.4]`.
6. **Background-subtraction-driven alarms.** §9.1.1.
7. **Frame-level AUC as a headline metric.** §8.1.1. Delete it from the datasheet.
8. **Rank-1/CMC as the headline re-ID metric.** §9.1.9.
9. **MOT17 in marketing material.** Saturated and unrepresentative `[via R01 §8]`.
10. **Per-camera configuration wizards as the primary UX.** §9.1.4. Keep as an override, not a
    workflow.
11. **Generative video as a source of labelled training data.** `R04 §5.6`'s five limitations
    `[via R04]`. Use it for restyling, not for labels.
12. **Audio waveform recording by default.** ICO: "switch audio recording off by default unless
    there is a much stronger justification" `[via R05 §15 bullet 11]`. Ship classified events.
13. **LiDAR as a headline perimeter modality.** "Appears in the literature far more than in
    security budgets" `[via R04 §3.5]`.
14. **Neuromorphic hardware on the near-term roadmap.** §7; watch, do not bet. See `D05`.
15. **A VLM's prose in the evidential export.** `R05 §15 bullet 34`: "A VLM's prose is never the
    record" `[via R05]`.

Plus three organisational removals `[judgement]`: the per-customer model fine-tune (it is a
services trap — fix it with calibration-conditioned models and site adaptation instead); the
bespoke per-VMS analytics build; and any claim of a percentage improvement without a stated
denominator and adjudicator (`R05 §15 bullet 7`).

---

## 11. Three scenarios, 2026 → 2035

`[All of §11 is judgement. The purpose is to make the bets explicit and falsifiable, not to
predict.]`

### Scenario A — "Agentic consolidation" (I weight this ~45%)

**Shape.** The VLM/agent layer commoditises fast. By 2028 the NVIDIA-VSS-shaped stack (or an
open equivalent) is a free reference architecture that any integrator can stand up in a week.
Cameras ship with SAM-3-lineage promptable detection on-chip. Natural-language rules become a
checkbox feature everywhere within 24 months of each other.

**Consequences.** Differentiation collapses onto three things: (1) **false-alarm rate at a
published operating point**, (2) **deployment cost per camera** (calibration, configuration,
uptime), and (3) **evidence and compliance artefacts**. Model quality ceases to be a moat because
everyone rents the same models. The winners are the companies that own *measurement* and
*deployment economics*. Two or three large platform vendors (VMS incumbents plus a cloud) take the
mid-market; specialists survive in CNI, defence and border where air-gap and sovereignty rule out
the platforms.

**What to do about it.** Everything in §10.1 rows 1–6 and 23. Own the benchmark, own the
deployment automation, publish the numbers nobody else will. Do not try to out-model Alibaba,
Google or Meta.

**Falsifiable indicators to watch:** a major VMS shipping NL standing-query alerting as standard
by 2028; camera SoCs shipping promptable open-vocabulary detection by 2029; a public FA/camera-hour
benchmark appearing from any vendor.

### Scenario B — "Regulatory bifurcation" (~35%)

**Shape.** The EU high-risk regime bites hard in 2026–2028; a handful of enforcement actions
establish that behaviour analytics on staffed sites is caught, and that documentation must be
per-condition and per-subgroup. The UK diverges pragmatically but converges on DPIA-plus-evidence
in practice. The US fragments by state. Meanwhile a couple of high-profile failures (a
misidentification, a hallucinated weapon claim in an evidential chain) harden public opinion.

**Consequences.** The market splits into a **compliance-heavy tier** (documented, auditable,
biometrics-restricted, synthetic-trained, evidence-exporting) and a **commodity tier** that sells
into unregulated or extraterritorial contexts. Compliance costs become the barrier to entry and
therefore the moat. Synthetic-only training goes from a curiosity to a procurement advantage.
Privacy-by-physics sensors (event cameras, radar, 802.11bf occupancy) grow faster than cameras in
sensitive environments. Insurance and procurement start demanding per-subgroup performance
disclosure.

**What to do about it.** Rows 4, 21, 25 of §10.1 become top-three priorities rather than
mid-table. Build the compliance dossier generator *now*, while it is a differentiator rather than
a requirement. Keep the product's identity layer on appearance-and-geometry rather than
biometrics, per `R02 §5.4`'s scoping insight.

**Indicators:** the first EU enforcement action against a behaviour-analytics vendor; a national
procurement framework requiring per-subgroup accuracy; an insurer pricing on false-alarm rate.

### Scenario C — "World-model integration" (~20%)

**Shape.** Generative world models cross two thresholds by roughly 2029–2031: **identity
consistency over minutes**, and **exportable approximate geometry and instance labels**. Cosmos-
and Genie-lineage systems become controllable enough to script rare behaviours. Simultaneously,
latent-prediction models (V-JEPA lineage) become the standard anomaly backbone: per-camera
self-supervised surprisal replaces both background subtraction and supervised VAD.

**Consequences.** The simulator does not die — **it becomes the supervisor.** The pipeline becomes:
geometry engine defines truth → world model renders and diversifies → verifier checks label
survival → trained model → simulator-based regression. Data scarcity stops being the bottleneck
for anything except *evaluation*, where exact truth is irreplaceable, so **the value of a
simulator migrates from training data to evaluation infrastructure and certification**. Intent
prediction gets meaningfully better (not solved) because anticipation becomes a pretraining task
at scale. Cross-camera identity gets better through simulated appearance-mutation supervision at a
scale no real dataset can reach.

**What to do about it.** Rows 18, 23, 24 and the label-survival verifier (`R04 §8` item 8) become
strategic. Invest in the *verifier* — "how to *prove* labels survive the restyling" is the open
engineering problem, and whoever solves it owns the interface between world models and supervised
perception.

**Indicators:** a world model demonstrating >60 s identity consistency with exportable instance
masks; a published result where world-model-augmented training beats simulator-only training on a
real held-out surveillance benchmark; a VAD paper whose method is per-camera self-supervised
surprisal beating supervised baselines on UBnormal-style open-set splits.

**What all three scenarios share, and therefore what is a no-regret investment:** measurement
infrastructure, deployment automation, calibration self-healing, evidence packaging, and the
honesty to publish operating points. None of those depend on which scenario happens.

---

## 12. Frontier item → simulator requirement (the mapping table)

The purpose of this table is to convert everything above into work items for `survsim`. "Exists"
means the repo already has or plans it per `R01`–`R06`; "New" means this document is proposing it.

| # | Frontier item (§) | Simulator requirement | Status |
|---|---|---|---|
| 1 | Promptable concept segmentation, SAM 3 (§1.1) | Emit **text-phrase-level ground truth** ("man with ladder", "person on fence") alongside class IDs, so open-vocabulary models can be scored on *concepts*, not classes | New |
| 2 | Open-vocab robustness collapse (§1.5) | Degrade-profile sweep (bitrate, IR, weather, pixel height) applied to a fixed open-vocab prompt set; report AP per profile | Exists (`R04`) |
| 3 | Frozen-backbone re-ID (§1.2) | Cross-domain splits by *site and rig*, never by clip; publish the generalisation gap | Exists (`R03 §8`) |
| 4 | VLM token economics (§1.4) | Report **GPU-seconds and tokens per camera-hour** as a first-class output of every eval run | New |
| 5 | Long-video comprehension ceiling (§1.4) | Include a **one-random-frame baseline** and a **distribution-only baseline** in every NL benchmark | Exists (`R05 §15 item 10`) |
| 6 | Agentic orchestration / VSS (§2.1) | Expose simulator scenarios + ground truth as an **MCP tool server** so agents can be evaluated against them | New |
| 7 | Streaming "when to speak" (§2.3) | Continuous multi-hour streams with exact event onsets; score with i-LIDS timed windows | Exists (`R05 §15 item 1`) |
| 8 | NL rules → compiled rule objects (§2.4) | Generate **(NL query, compiled rule, exact event truth)** triples from the behaviour engine's event log | Exists (`R05 §15 item 9`) |
| 9 | Hallucination control (§2.5) | **Negative-control scenarios**: scenes that contain *no* weapon/ladder/bag, with prompts asking about them; score fabrication rate | New |
| 10 | Agent evaluation (§2.6) | Grounding-fidelity ground truth: every event annotated with the minimal citation set that justifies it | New |
| 11 | 4D reconstruction / novel view (§3.1) | Export posed multi-view frames + metric geometry so 3DGS/NeRF pipelines can be scored against true geometry | New |
| 12 | Digital twins (§3.2) | **Import** customer BIM/twin geometry; **apply** our camera and imaging models to it | New (high value) |
| 13 | Camera-placement optimisation (§3.1, §10.1 row 17) | Coverage solver over the 3D site with pixel-height-on-path objective | New |
| 14 | Cosmos Transfer restyling (§3.3) | **Label-survival verifier**: after restyling, re-score boxes/masks/IDs against original truth and report drift | New (strategic) |
| 15 | Cosmos Reason / Predict separation (§3.3) | Keep behaviour reasoning, scenario rollout and imaging rendering as three independently swappable stages | Exists (architecture) |
| 16 | V-JEPA-style surprisal anomaly (§3.4) | Long "boring" baseline recordings per camera (weeks of nothing) as a *training* asset, plus injected rare events as *test* | New |
| 17 | SAM2/SAMURAI forensic tracking (§4.1) | Prompted single-target tracking benchmark with occlusion, exit/re-entry and appearance change, scored by AUC and ID persistence | New |
| 18 | MOTIP / learned association (§4.2) | Crowd-density sweep (5 → 200 people/frame) with exact ID truth; report AssA vs density | Exists (`R01 §8`) |
| 19 | Calibration-conditioned MTMC (§4.2) | **Randomise rig topology** (camera count, placement, overlap, height, FOV) as a first-class scenario parameter; hold out unseen topologies | Exists (`R02 §8 item 1`) |
| 20 | CoTracker3 / point tracking (§4.3) | Emit dense point-correspondence truth on static structure and on limbs; inject mount bump / defocus / dome crazing | New |
| 21 | 3D human mesh (§4.4) | Export **SMPL-class body parameters** per person per frame as ground truth | New (we get it free) |
| 22 | Face/body/gait fusion policy (§4.5) | Per-frame **face visibility and inter-eye distance** truth, plus gait-cycle completeness flags | Exists (`R02 §11 item 6`) |
| 23 | Long-term whole-body re-ID (§4.5) | Multi-session scenarios over simulated days/weeks with outfit change and hidden-identity truth | Exists (`R02 §11 item 5`) |
| 24 | Adversarial evasion (§8.2e) | **Camera-aware adversarial planner**: an actor with the camera layout as input, planning blind-spot routes and appearance swaps | New (highest research value) |
| 25 | Privacy-preserving analytics (§5.2) | Render **redacted** and **events-only** variants of every scenario; measure the accuracy cost of each privacy tier | New |
| 26 | Synthetic-only training as compliance (§5.2.4) | Asset manifest and demographic-balance report emitted with every dataset build | Exists (`R04 §7`) |
| 27 | Event cameras (§6) | High-internal-frame-rate rendering + ESIM/v2e event emission; publish an event-camera perimeter benchmark | Planned (`R04 §3.5`) |
| 28 | Radar / RF / 802.11bf (§6) | Geometry+RCS radar model and an RF/Wi-Fi association model with device-count and randomisation parameters | Exists (`R04 §3.5`, `R05 §13 item 3`) |
| 29 | Multi-imager domes (§6) | Multi-imager camera primitive with factory-accurate intra-dome extrinsics | New |
| 30 | Drone / airspace tier (§6) | Moving-camera actors (drone, body-worn) in the same association graph as fixed cameras | New |
| 31 | Substream reality (§6, §7) | Dual-stream emission: 4K "evidence" and 640×360 @0.3 Mb/s "analytics" substream from the same truth | Exists (`R04 §1`) |
| 32 | Edge compute limits (§7) | Cost model per scenario: decode load, inference budget, per-detection re-ID cost as a function of crowd size | New |
| 33 | Continuous benchmarking (§8.2a) | Versioned, regenerable scenario suite with a stable scoring contract; run on every commit | New (core) |
| 34 | LLM-as-judge risk (§8.2d) | Human-adjudicated gold subset in every release, with reported judge–human agreement (κ) | New |
| 35 | Assessment metrics (§8.2f) | Emit **clip-sufficiency** truth: is the attached clip sufficient to adjudicate the event without further context | New |
| 36 | Tamper / camera health (§9.1.2) | Injectable tamper library: defocus, cover, spray, rotation, IR-LED failure, cobweb, freeze, bitrate starvation | Exists (`R04 §4`) |
| 37 | Uptime and drift (§9.3) | Sensor outage, dirty lens, PTZ home drift and stale zone polygons as scenario parameters | Exists (`R05 §15 item 12`) |
| 38 | Wildlife nuisance (§9.3) | Animal actors (fox, deer, bird, cat, insect-on-lens) with intruder-like kinematics | New (directly attacks `R05 §13 item 1`) |
| 39 | Operator load (§8.2f) | Model alarms per operator-hour and a saturation threshold as an output | Exists (`R05 §15 item 11`) |
| 40 | Provenance (§10.1 row 25) | Sign every generated clip and every label file with a manifest hash and model/asset versions | New |

---

## Appendix A — the hop chain

This is the actual traversal, recorded so a reader can audit how far each claim is from a primary
source. **Hops 1–4 were performed with live search in this session; hops 5–8 were performed
against the repo's own already-verified corpus plus professional knowledge, because the search
budget was exhausted and all direct fetches were egress-blocked (see §0.1).**

* **Hop 1 — The promptable-segmentation frontier.** Query: SAM 3 / promptable concept
  segmentation. → Found SAM 3 (arXiv 2511.16719), *and* the existence of **SAM 3.1** with
  "Multiplexing and Global Reasoning" in the title. **Lesson taken:** the competitive axis moved
  to real-time multi-stream. Feeds §1.1, §4.1.
* **Hop 2 — Backbones.** Query: DINOv3. → Gram Anchoring, +6 mIoU ADE20K, 7 B teacher with
  distilled students, 60+ benchmarks. **Connected to** `R02 §3.2`'s CLIP-ReID-generalises-better
  finding → the hypothesis in §1.2 that DINOv3-initialised re-ID inherits graceful off-domain
  degradation. Feeds §1.2.
* **Hop 3 — Video encoders.** Queries: VideoPrism; InternVideo2.5. → 31/33 benchmarks frozen;
  +12.4 EgoSchema vs +0.6 LongVideoBench. **Lesson taken:** uneven per-benchmark deltas are the
  signature of benchmark-specific gains. Onward pointer discovered: **InternVideo3 — "Agentify
  Foundation Models"** (arXiv 2606.12195), which is hop 4's bridge. Feeds §1.3.
* **Hop 4 — Frontier VLMs and their cost.** Query: Qwen3-VL. → Competitive with Gemini 2.5 Pro /
  GPT-5 / Claude Opus 4.1; 256 K context; **and the evaluation protocol** (2 fps, 640–768
  tokens/frame, 2,048-frame cap). **This was the pivotal find:** it converts a capability claim
  into an arithmetic refutation of always-on VLM analytics (§1.4). Bridged to `R05 §13 item 14`
  (continuous-indexing economics) and `R03 §6.2` (where to put the expensive model).
* **Hop 4b — The agentic stack.** Queries: NVIDIA VSS blueprint; Cosmos Reason/Predict/Transfer;
  V-JEPA 2. → VSS's three-tier decomposition, "verified alerts", MCP; Cosmos Predict 2.5 unifying
  three WFMs with Cosmos-Reason1 grounding, Transfer 2.5 "3.5× smaller"; V-JEPA 2's 39.7 R@5
  anticipation and IntPhys 2 / MVPBench / CausalVQA. **Lesson taken:** "verified alerts" and the
  Reason/Predict/Transfer split are both architectural ideas worth stealing (§2.1, §3.3).
* **Hop 5 — Back into the repo, deliberately.** Search budget exhausted; all fetches blocked.
  Traversed `R01 §5.1` (Jetson/Hailo anchors, the decode-first bottleneck ladder), `R01 §8`
  (leaderboard-reading rules), `R02 §3.6` (BRIAR/FarSight fusion deltas), `R02 §5.4` (Article 5
  scoping), `R02 §8` (twelve open problems), `R03 §5.2` (the 1,200× arithmetic), `R03 §5.3`
  (Calipsa/Ambient/Hakimo claims and how to read them), `R03 §9.3` (Article 5 emotion/biometric
  categorisation), `R04 §3.4–3.5` (open-vocab fragility; event cameras; radar; LiDAR),
  `R04 §4.1` (the embarrassingly-simple tamper features), `R04 §5.6–5.7` (world-model limits;
  vendor landscape), `R05 §9.1–9.2` (long-video ceiling; streaming "when to speak"),
  `R05 §11.1–11.2` (BriefCam/Verkada/Ambient/Twelve Labs; retrieve-then-reason), `R05 §12`
  (VideoHallucer), `R05 §15` (the veteran bullets).
* **Hop 6 — Cross-linking the two halves.** Each frontier item from hops 1–4b was paired with the
  open problem it does or does not close. The three highest-value pairings: **(a)** Qwen3-VL's
  token protocol × `R03 §6.2` → the two-stage architecture is now arithmetically forced, not
  merely prudent. **(b)** V-JEPA 2's latent prediction × `R03 §10 item 4` (zero-label site
  adaptation) → per-camera surprisal is the most promising research bet available (§3.4, §10.1
  row 18). **(c)** Cosmos Transfer × `R04 §8 item 8` → the **label-survival verifier** is the
  missing artefact at the world-model/perception interface (§12 row 14).
* **Hop 7 — Inversion: what does the frontier make obsolete?** Applied each new capability to the
  legacy stack and wrote the argument *and the counter-argument* for each (§9.1), including the
  on-prem debate, which is the only one where I think the popular answer is wrong in both
  directions.
* **Hop 8 — Forward projection and requirement extraction.** Built the three scenarios (§11) as
  falsifiable bets with named indicators, then mechanically walked every frontier item into a
  simulator requirement (§12), marking which already exist in `R01`–`R06` and which are new. Of
  the 40 requirements, **22 are new**, and the four I would fund first are: the label-survival
  verifier, the camera-aware adversarial planner, twin import with our camera models, and
  simulator-driven CI.

**Where the chain is weakest, stated plainly:** hops 1–4b rest on search-result summaries rather
than on primary PDFs I re-read in this session, so every number in §1 carries `[VERIFY]`. §6
(SWIR, LiDAR cost curve, 802.11bf, satellite/WAMI, counter-UAS) and parts of §7 (Jetson Thor,
Hailo-10, Blackwell edge) are the least-sourced sections in this document and should be treated as
structured hypotheses for a future retrieval pass, not as findings. §3.1 (Gaussian splatting from
CCTV) and §4.3–4.4 (CoTracker3, Multi-HMR, SAM-3D-Body) contain no retrieved numbers at all.

---

## Appendix B — a first retrieval list for the next pass

For whoever runs this again with a live search budget, in priority order:

1. SAM 3 / SAM 3.1 primary: SA-Co benchmark cgF1, LVIS zero-shot AP, per-image latency on H200 at
   N objects, video tracking rate. Compare directly against Grounding DINO 1.6 and OWLv2 on our
   degrade profiles.
2. Qwen3-VL and Gemini 2.5/3 published *prices* per million input tokens, converted to £ per
   camera-hour at 1 fps and 0.2 fps.
3. EU AI Act Annex III primary text: is a security analytic on a CNI site a "safety component of
   critical infrastructure management"? Plus the 2026/2027 phase-in dates verbatim. **Resolve with
   counsel.**
4. UK Data (Use and Access) Act 2025: what changed for CCTV/biometrics specifically.
5. Jetson Thor and Hailo-10 primary specs: TOPS, memory bandwidth, decode channel counts, power.
6. IEEE 802.11bf status, and any published Wi-Fi-sensing accuracy for presence/occupancy.
7. Gaussian-splatting-from-surveillance papers 2025–2026; dynamic/4D GS with wide baselines.
8. CoTracker3, Multi-HMR and SAM-3D-Body primary numbers, with per-pixel-height breakdowns if any.
9. BRIAR/FarSight latest results and the current BRIAR dataset statistics verbatim.
10. Genie 3 / Cosmos Predict identity-consistency duration claims — the threshold that governs
    Scenario C.
11. LLM-as-judge bias literature, and any video-specific judge calibration study.
12. Anduril/CBP sentry-tower and counter-UAS programme numbers (already partly in `R05` sources).

---

## Sources

**Retrieved in this session (search-result summaries; primary pages were egress-blocked — all marked `[VERIFY]` above)**
- SAM 3 — [arXiv 2511.16719](https://arxiv.org/abs/2511.16719) · [paper PDF](https://arxiv.org/pdf/2511.16719) · [Meta research page](https://ai.meta.com/research/publications/sam-3-segment-anything-with-concepts/) · [Meta blog: SAM 3.1](https://ai.meta.com/blog/segment-anything-model-3/) · [Roboflow explainer](https://blog.roboflow.com/what-is-sam3/) · [Ultralytics docs](https://docs.ultralytics.com/models/sam-3) · [FiftyOne guide](https://voxel51.com/blog/how-to-use-segment-anything-model-sam3)
- DINOv3 — [arXiv 2508.10104](https://arxiv.org/pdf/2508.10104) · [HTML](https://arxiv.org/html/2508.10104v1) · [Meta blog](https://ai.meta.com/blog/dinov3-self-supervised-vision-model/) · [Meta research](https://ai.meta.com/research/dinov3/) · [Lightly technical deep dive](https://www.lightly.ai/blog/dinov3) · [Roboflow training guide](https://blog.roboflow.com/train-dinov3/)
- VideoPrism — [Google Research blog](https://research.google/blog/videoprism-a-foundational-visual-encoder-for-video-understanding/) · [code](https://github.com/google-deepmind/videoprism) · [model card](https://huggingface.co/google/videoprism-base-f16r288)
- InternVideo2.5 — [arXiv 2501.12386](https://arxiv.org/abs/2501.12386) · [HTML](https://arxiv.org/html/2501.12386v1) · [OpenReview](https://openreview.net/forum?id=stqE9Appk5) · InternVideo3 — [arXiv 2606.12195](https://arxiv.org/pdf/2606.12195)
- Qwen3-VL — [Technical Report, arXiv 2511.21631](https://arxiv.org/abs/2511.21631) · [PDF](https://arxiv.org/pdf/2511.21631) · [repo](https://github.com/qwenlm/qwen3-vl) · Qwen2.5-VL — [arXiv 2502.13923](https://arxiv.org/pdf/2502.13923)
- NVIDIA Cosmos — [product page](https://www.nvidia.com/en-us/ai/cosmos/) · [Predict 2.5 / Transfer 2.5 announcement](https://huggingface.co/blog/nvidia/cosmos-predict-and-transfer2-5) · [cosmos-predict2.5 repo](https://github.com/nvidia-cosmos/cosmos-predict2.5) · [NVIDIA newsroom release](https://nvidianews.nvidia.com/news/nvidia-announces-major-release-of-cosmos-world-foundation-models-and-physical-ai-data-tools) · [World Simulation with Video Foundation Models, arXiv 2511.00062](https://arxiv.org/abs/2511.00062) · [NVIDIA/Cosmos](https://github.com/NVIDIA/Cosmos)
- V-JEPA 2 — [Meta blog + benchmarks](https://ai.meta.com/blog/v-jepa-2-world-model-benchmarks/) · [Meta research page](https://ai.meta.com/research/publications/v-jepa-2-self-supervised-video-models-enable-understanding-prediction-and-planning/)
- NVIDIA VSS — [blueprint repo](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization) · [docs](https://docs.nvidia.com/vss/latest/index.html) · [3.0.0 overview](https://docs.nvidia.com/vss/3.0.0/overview/3.0.0/) · [NVIDIA blog](https://blogs.nvidia.com/blog/ai-blueprint-video-search-and-summarization/) · [NGC helm chart](https://catalog.ngc.nvidia.com/orgs/nvidia/blueprint/helm-charts/nvidia-blueprint-vss/-)
- Video benchmark critiques surfaced in passing — [Video-MME-v2, arXiv 2604.05015](https://arxiv.org/pdf/2604.05015) · [GLIMPSE, arXiv 2507.09491](https://arxiv.org/pdf/2507.09491) · [TOC-Bench, arXiv 2605.09904](https://arxiv.org/pdf/2605.09904) · [SlowFast-LLaVA-1.5, arXiv 2503.18943](https://arxiv.org/pdf/2503.18943) · [World Models survey, arXiv 2606.00133](https://arxiv.org/pdf/2606.00133)

**Carried from this repo's verified corpus (see the cited dossier for the captured quotation and its own caveats)**
- Detection, tracking, edge compute — `R01`: [MOTIP CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Gao_Multiple_Object_Tracking_as_ID_Prediction_CVPR_2025_paper.pdf) · [SAMURAI, arXiv 2411.11922](https://arxiv.org/abs/2411.11922) · [Jetson Orin streams](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/) · [Hailo-8](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/) · [edgeaistack comparison](https://edgeaistack.ai/blog/hailo-8-vs-8l-vs-10h-2026/) · [DeepStream performance](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html) · [Benchmark AUC Is Not Deployable Reliability, arXiv 2606.29506](https://arxiv.org/pdf/2606.29506)
- MTMC, re-ID, biometrics, law — `R02`: [OpenGait](https://arxiv.org/pdf/2405.09138) · [MultiGait++](https://arxiv.org/pdf/2412.11495) · [RealGait](https://arxiv.org/pdf/2201.04806) · [IARPA BRIAR](https://www.iarpa.gov/research-programs/briar) · [FarSight](https://arxiv.org/pdf/2306.17206) · [BRIAR covariate analysis](https://arxiv.org/abs/2409.01514) · [GMVD](https://github.com/jeetv/GMVD) · [MVUDA, arXiv 2412.04117](https://arxiv.org/pdf/2412.04117) · [GeoCalib](https://github.com/cvg/GeoCalib) · [DeepChange](https://arxiv.org/abs/2105.14685) · [ReID5o](https://arxiv.org/html/2506.09385v1) · [EU AI Act Article 5](https://artificialintelligenceact.eu/article/5/) · [FPF on real-time RBI](https://fpf.org/blog/red-lines-under-the-eu-ai-act-restricting-real-time-remote-biometric-identification-systems-for-law-enforcement-purposes/) · [AI City Challenge](https://www.aicitychallenge.org/2023-challenge-tracks/)
- Behaviour, anomaly, alarm economics, regulation — `R03`: [Actuate on alarm fatigue](https://actuate.ai/alarm-fatigue/) · [IntelliSee: 98% of alarms are false](https://intellisee.com/98-of-security-camera-alarms-are-false-heres-what-thats-actually-costing-you/) · [IntelliSee: the 20-minute limit](https://intellisee.com/the-human-monitoring-limit-why-manufacturing-cctv-fails-every-20-minutes/) · [Calipsa](https://www.calipsa.io/solution/for-monitoring-stations) · [Ambient.ai platform](https://www.ambient.ai/platform-overview) · [Hakimo](https://www.hakimo.ai/) · [Hakimo funding](https://www.hakimo.ai/blog/hakimo-secures-10-5m-to-transform-physical-security-with-human-like-autonomous-security-agent) · [UBnormal](https://github.com/lilygeorgescu/UBnormal) · [Holmes-VAU](https://arxiv.org/pdf/2412.06171) · [Rethinking Metrics and Benchmarks of VAD](https://arxiv.org/html/2505.19022v2) · [Background-bias in VAD, ACM MM 2019](https://dl.acm.org/doi/10.1145/3343031.3350998) · [Ava: agentic video analytics](https://arxiv.org/html/2505.00254v5) · [Zelda](https://arxiv.org/pdf/2305.03785) · [SketchQL](https://dl.acm.org/doi/pdf/10.1145/3677140) · [AI Act Service Desk, Article 5 FAQ](https://ai-act-service-desk.ec.europa.eu/en/ai-act/faq/what-systems-are-prohibited-under-article-5-ai-act-eg-social-scoring-emotion-recognition) · [Federated violence detection, arXiv 2504.00857](https://arxiv.org/pdf/2504.00857) · [Sandia/DOE on false and nuisance alarms](https://www.osti.gov/servlets/purl/1347158)
- Degraded imaging, sim2real, world models — `R04`: [Open-Vocabulary Detectors under Distribution Shifts, arXiv 2405.14874](https://arxiv.org/pdf/2405.14874) · [Many Faces of Robustness](https://arxiv.org/pdf/2006.16241) · [From Fog to Failure, arXiv 2502.02027](https://arxiv.org/abs/2502.02027) · [event-based vision resources](https://github.com/uzh-rpg/event-based_vision_resources) · [UnrealZoo](https://github.com/UnrealZoo/unrealzoo-gym) · [Omniverse Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html) · [Kubric](https://github.com/google-research/kubric) · [Infinigen](https://github.com/princeton-vl/infinigen) · [BlenderProc](https://github.com/DLR-RM/BlenderProc) · [CARLA](https://github.com/carla-simulator/carla) · [ETRI compression benchmark](https://onlinelibrary.wiley.com/doi/10.4218/etrij.2025-0363) · [Deep Vision with Standard Codecs, arXiv 2404.12330](https://arxiv.org/pdf/2404.12330)
- Fusion, retrieval, streaming, hallucination — `R05`: [i-LIDS scoring via Sensors 22:3601](https://www.mdpi.com/1424-8220/22/9/3601) · [NPSA PIDS guidance](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-pids) · [MDPI on φ-OTDR nuisance alarm reduction](https://www.mdpi.com/2673-3269/4/2/24) · [Radar-camera fusion survey, arXiv 2410.19872](https://arxiv.org/pdf/2410.19872) · [Dispider, arXiv 2501.03218](https://arxiv.org/pdf/2501.03218) · [Flash-VStream, arXiv 2406.08085](https://arxiv.org/abs/2406.08085) · [MLVU, arXiv 2406.04264](https://arxiv.org/html/2406.04264v2) · [LongVideoBench](https://huggingface.co/papers/2407.15754) · [Breaking Down Video LLM Benchmarks, arXiv 2505.14321](https://arxiv.org/html/2505.14321v1) · [VideoARM, arXiv 2512.12360](https://arxiv.org/pdf/2512.12360) · [VideoHallucer](https://www.researchgate.net/publication/381666694_VideoHallucer_Evaluating_Intrinsic_and_Extrinsic_Hallucinations_in_Large_Video-Language_Models) · [IRRA](https://github.com/anosorae/IRRA) · [BriefCam federal capabilities](https://www.briefcam.com/wp-content/uploads/2025/06/BriefCam-FederalCapabilitiesStatement-2023-1.pdf) · [Verkada on NL video search](https://www.verkada.com/blog/scaling-natural-language-video-search-inside-verkadas-breakthrough/) · [Twelve Labs models overview](https://www.twelvelabs.io/product/models-overview) · [Marengo 3.0](https://www.twelvelabs.io/blog/marengo-3-0) · [Elastic + Twelve Labs pipeline](https://www.elastic.co/search-labs/blog/twelvelabs-marengo-video-embedding-amazon-bedrock) · [ProPublica on aggression detectors](https://features.propublica.org/aggression-detector/the-unproven-invasive-surveillance-technology-schools-are-using-to-monitor-students/) · [ICO position on CCTV audio via LegalVision](https://legalvision.co.uk/data-privacy-it/audio-recording-cctv-gdpr-dpa-ico/) · [EFF on border surveillance towers](https://www.eff.org/deeplinks/2024/10/us-border-surveillance-towers-have-always-been-broken) · [Chicago OIG on ShotSpotter](https://igchicago.org/2021/08/24/oig-finds-that-shotspotter-alerts-rarely-lead-to-evidence-of-a-gun-related-crime-and-that-presence-of-the-technology-changes-police-behavior/)
- Company and ecosystem context — `R06`: [a CCTV-analytics vendor]((vendor source removed)) · [ICO](https://ico.org.uk/) · [EU AI Act portal](https://artificialintelligenceact.eu/) · [Dstl](https://www.gov.uk/government/organisations/defence-science-and-technology-laboratory) · [DASA](https://www.gov.uk/government/organisations/defence-and-security-accelerator)

---

*End of D07. Twelve sections, forty simulator requirements, twenty-five features in, fifteen out,
three scenarios. Every `[VERIFY]` in this document is a debt; §Appendix B is the repayment
schedule.*
