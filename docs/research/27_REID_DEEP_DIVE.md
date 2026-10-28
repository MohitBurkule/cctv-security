# 27 · Re-Identification and Cross-Camera Association: A Deep Dive

**Scope.** This report goes deeper than R02 §3 (which surveys the ReID model lineage, the domain gap and clothes-changing ReID) and 18_PERCEPTION_STACK (which places ReID in the pipeline). The aim here is that you can **derive** every piece on a whiteboard: why a softmax over identities learns a usable embedding, what batch-hard mining actually selects, why BNNeck exists, how rank-1 and mAP are computed (with a worked example you can repeat by hand), how camera topology turns ReID from "search everyone" into "search the few who could physically be here", and where the legal line falls when a system starts matching people. It closes by tying all of it to `survsim/gait/signature.py`, `survsim/core/appearance.py` and `survsim/eval/tracking.py`.

**Evidence tags.** `[n]` = fetched this session (see References). `[derived]` = arithmetic or reasoning of mine from cited material. `[VERIFY]` = from memory, not fetched; check before quoting in an interview.

---

## 1. The problem, stated precisely

**Intuition.** A detector tells you *there is a person in this box*. A single-camera tracker tells you *this box and that box one frame later are the same person*, largely by motion continuity. ReID answers the question left over when motion continuity breaks: the person walked out of camera 3 and, forty seconds later, someone walked into camera 7. Same person?

There is no motion to lean on across that gap, so the system has to compare *appearance* — and whatever else survives the gap (height, gait, the time it took, the direction they left in).

**Formal version.** Learn an embedding function `f: image → R^d` such that for images `x_a, x_b`:

- if `id(x_a) = id(x_b)`, then `D(f(x_a), f(x_b))` is small;
- otherwise it is large;

where `D` is Euclidean or cosine distance. At test time there is a **query** set and a **gallery** set of *identities never seen in training* (this is the key difference from classification — ReID is open-set at the identity level). For each query, rank the gallery by distance and see where the true matches land.

Why not just classify? Because the identities in deployment are strangers. A classifier's output layer is indexed by training IDs, which is useless at test time; what transfers is the *penultimate feature*, provided the training objective shaped that feature space so that "near" means "same person". Every loss below is a different way of shaping that space.

---

## 2. Losses: how the embedding space is shaped

### 2.1 Softmax identity (ID) loss — "classification as a proxy"

**Intuition.** Train the network to classify the N training identities. To do so it must learn features that separate those people. Throw the classifier away at test time and keep the feature; the hope is the features that separate 751 training people also separate strangers.

**Equation.** With feature `f`, classifier weights `W_j` for class `j`, logits `z_j = W_j·f (+ b_j)`:

    p_j = exp(z_j) / Σ_k exp(z_k)
    L_ID = − Σ_j q_j log p_j

with `q` the one-hot target. **Label smoothing** replaces the one-hot with `q_i = 1 − (N−1)ε/N` for the true class and `ε/N` elsewhere; Luo et al. use `ε = 0.1` [2]. The motivation given is that ReID training sets are small in identities and a hard one-hot target lets the network overfit the training IDs [2].

**Worked number [derived].** With N = 751 and ε = 0.1, the true class target is `1 − 750·0.1/751 ≈ 0.9001` and each other class gets `0.1/751 ≈ 1.33e-4`. So the network is asked to be only ~90 % confident — enough to stop it driving logits to infinity.

**Weakness.** Softmax cares that the true class *wins*, not that the features are compact. Two images of the same person can sit far apart as long as both fall on the right side of the decision hyperplane. That is the gap metric losses close.

### 2.2 Triplet loss and batch-hard mining

**Intuition.** Directly state what you want: an anchor must be closer to a positive (same ID) than to a negative (different ID), by a margin.

    L_tri = [ m + D(a, p) − D(a, n) ]_+

**The mining problem.** Almost all random triplets are already satisfied (loss zero), so they contribute nothing. Hermans, Beyer and Leibe's "In Defense of the Triplet Loss" [1] fixed this with **PK batches** and **batch-hard** mining: sample P identities × K images each; for every anchor, take the **hardest positive** (farthest same-ID image in the batch) and the **hardest negative** (closest different-ID image in the batch):

    L_BH = Σ_{i=1..P} Σ_{a=1..K} [ m + max_p D(x_a^i, x_p^i) − min_{j≠i, n} D(x_a^i, x_n^j) ]_+

They also propose the **soft-margin** variant, replacing the hinge `[m + x]_+` with `softplus(x) = ln(1 + e^x)`, which removes the margin hyperparameter and in their experiments "performs slightly better" [1]. They report TriNet with P = 18, K = 4 (batch 72) and LuNet (trained from scratch) with P = 32, K = 4 [1].

**Why it matters in numbers.** TriNet reached **69.14 % mAP / 84.92 % rank-1** on Market-1501 single-query, and **81.07 % mAP** after re-ranking [1]. Their headline comparison: another ResNet-50 triplet model (DTL) was at 41.5 % mAP — the jump came from *how* the triplets were chosen, not from the loss shape [1].

**Worked example [derived].** Batch with P = 2 people, K = 2 images: A1, A2, B1, B2. Distances: D(A1,A2) = 0.8, D(A1,B1) = 0.6, D(A1,B2) = 1.4, m = 0.3.
Anchor A1: hardest positive 0.8, hardest negative 0.6 → loss = [0.3 + 0.8 − 0.6]_+ = **0.5**. A random triplet (A1, A2, B2) would give [0.3 + 0.8 − 1.4]_+ = 0 — no gradient. Batch-hard finds the triplet that is actually wrong.

**Caveat worth saying aloud.** "Hardest" in a small batch can be a labelling error or an occluded crop. That is one reason K is kept small and why soft-margin (which never goes flat) helps.

### 2.3 Circle loss — reweighting each similarity

**Intuition.** Triplet and softmax both push on the gap `s_n − s_p` (negative similarity minus positive similarity) with equal force on each term. But if a positive pair is already very similar, pushing it further is wasted effort; if a negative is already far, same. Circle loss gives each similarity its *own* weight, proportional to how far it is from its optimum, so the optimisation effort goes where it is needed. Sun et al. describe it as re-weighting "each similarity score to highlight the less-optimized" ones, unifying class-level (softmax-style) and pair-wise (triplet-style) learning, with a circular decision boundary [6].

**Equation [6] (checked against the paper's Eq. for the unified loss at audit, 2026-09-26; the paper suggests γ ≈ 128 for ReID and m ≈ 0.25).**

    L_circle = log[ 1 + Σ_j exp(γ α_n^j (s_n^j − Δ_n)) · Σ_i exp(−γ α_p^i (s_p^i − Δ_p)) ]
    α_p = [O_p − s_p]_+ ,  α_n = [s_n − O_n]_+ ,  O_p = 1+m, O_n = −m, Δ_p = 1−m, Δ_n = m

The resulting decision boundary is a circle in the `(s_n, s_p)` plane — hence the name. As a ReID data point, the CAL paper's Table 4 lists CircleLoss at 94.2 % top-1 / 84.9 % mAP on Market-1501 [10].

### 2.4 The "bag of tricks" strong baseline (ID + triplet + BNNeck)

Luo et al. [2] showed a plain ResNet-50 with global features only reaches **94.5 % rank-1 / 85.9 % mAP on Market-1501** [2] by stacking six tricks, added one at a time:

| Trick | What it does [2] | Why (first principles) |
|---|---|---|
| Warmup LR | 10 epochs ramping up; base LR 3.5e-4, ×0.1 at epochs 40 and 70, 120 epochs total [2] | Large early steps wreck ImageNet-pretrained features before the new head is sensible |
| Random erasing | Erase a random rectangle | Simulates occlusion — the dominant CCTV failure mode |
| Label smoothing | ε = 0.1 [2] | See §2.1 |
| Last stride = 1 | ResNet-50's last downsample removed; feature map 16×8 instead of 8×4 for a 256×128 input [2] | More spatial detail for fine cues (logos, bag straps) at trivial compute cost |
| BNNeck | BN layer between feature and classifier | See below |
| Center loss | Pulls each feature toward a learned per-ID centre | Triplet only constrains *relative* distances; centre loss adds absolute compactness |

**BNNeck, the one to be able to draw.** The problem: ID loss wants features separable by hyperplanes through angular space; triplet loss wants them compact in Euclidean space. Optimising both on the same vector makes one oscillate while the other falls [2]. BNNeck puts a batch-norm layer after the feature: the pre-BN feature `f_t` feeds the **triplet** loss, the post-BN feature `f_i` feeds the **ID** loss (with the classifier bias removed so hyperplanes pass through the origin), and at inference `f_i` is used **with cosine distance** [2]. The BN layer pushes `f_i` to be roughly Gaussian near a hypersphere, which suits a softmax; `f_t` is freed from the ID loss's constraint, so triplet converges too [2].

Their Duke same-domain ablation climbs from 79.7/63.7 (rank-1/mAP) baseline, through 80.6/65.1 with warmup, 81.5/68.3 with random erasing, 82.4/69.3 with label smoothing, to 82.6/70.6 with stride 1, before BNNeck and centre loss [2]. They also note warmup, label smoothing and BNNeck improve *cross-domain* transfer, while stride change and centre loss don't clearly help it and **random erasing actually hurts** cross-domain transfer [2] — a point that matters more for CCTV than the same-domain number.

---

## 3. Architectures

### 3.1 OSNet — omni-scale, lightweight

**Intuition.** Identity cues live at many scales at once: a shoe (small), a jacket-and-bag combination (medium), whole-body silhouette (large). OSNet's block runs several convolutional streams with different receptive fields and fuses them with a **unified aggregation gate** — input-dependent channel-wise weights — so each image can decide which scale matters [3]. Efficiency comes from pointwise + depthwise convolutions [3]; the paper claims it is "extremely lightweight", trainable from scratch, and beats most larger models on six ReID datasets [3]. Parameter count ≈ 2.2 M [VERIFY]. CAL's Table 4 lists OSNet at 94.8 % / 84.9 % mAP on Market-1501 and 78.7 / 52.9 on MSMT17 [10].

**Why a CCTV company cares.** It is the default in BoxMOT/torchreid-style trackers; at 10+ streams on an edge GPU, model size dominates.

### 3.2 TransReID — ViT with camera awareness

**Intuition.** CNNs lose fine detail through downsampling; a ViT keeps patch-level detail and global attention from layer one [4]. Two ReID-specific additions [4]:

- **Jigsaw Patch Module (JPM):** shift and shuffle patch embeddings into groups to learn robust part-level features — part features without a pose estimator.
- **Side Information Embedding (SIE):** learnable embeddings of *camera ID and viewpoint* added to the input, to reduce feature bias from camera/view [4].

SIE is the architectural admission of a real fact: the same person under two cameras differs systematically (white balance, angle, compression), and telling the network *which camera* lets it subtract that. For a deployment, this means the model must be conditioned on **site camera IDs** — which don't exist at train time. Treat SIE as an argument for per-site fine-tuning or for normalising per camera. [derived]

### 3.3 CLIP-ReID — borrowing language priors without language

**Problem.** CLIP learns from image–text pairs, but ReID labels are just integers. CLIP-ReID [5] solves this in two stages:

1. Freeze both CLIP encoders; learn a set of **per-identity text tokens** ("A photo of a [X1][X2]...[XM] person") with a contrastive loss, so each ID gets an "ambiguous description" [5].
2. Freeze those tokens; fine-tune the image encoder with them as class anchors plus the usual ID/triplet losses [5].

They also report that merely initialising from CLIP's image encoder is already competitive [5]. Interview angle: the value of foundation-model initialisation is *robustness to domain shift*, which is exactly the thing CCTV lacks labels for.

---

## 4. Metrics, derived and worked

### 4.1 CMC / rank-k

For each query `q`, sort the gallery by similarity. Let `r(q)` be the position (1-based) of the **first** correct match. Then

    CMC(k) = (1/|Q|) Σ_q 1[ r(q) ≤ k ]

Rank-1 = CMC(1). It only looks at the first hit, so it ignores whether the *other* images of that person are found. Queries with no match in the gallery are dropped (closed-set).

### 4.2 Average precision and mAP

For query `q` with `G_q` relevant gallery items, and `hit(k) ∈ {0,1}` at rank k:

    P@k = (Σ_{i≤k} hit(i)) / k
    AP(q) = (1/G_q) Σ_k P@k · hit(k)
    mAP = mean_q AP(q)

AP rewards finding **all** instances early. That is the operationally relevant number when an investigator wants *every* sighting of a suspect, not just one.

### 4.3 Worked example (do this by hand in the interview) [derived]

Gallery ranking for two queries (✓ = same ID):

- **Query A** (3 relevant): ✓ ✗ ✓ ✗ ✗ ✓
  - Hits at ranks 1, 3, 6. P@1 = 1/1, P@3 = 2/3, P@6 = 3/6.
  - AP = (1 + 0.667 + 0.5)/3 = **0.722**. First hit at rank 1.
- **Query B** (2 relevant): ✗ ✗ ✓ ✓ ✗ ✗
  - Hits at 3, 4. P@3 = 1/3, P@4 = 2/4. AP = (0.333 + 0.5)/2 = **0.417**. First hit at rank 3.

Rank-1 = (1 + 0)/2 = **50 %**. Rank-5 = (1 + 1)/2 = **100 %**. mAP = (0.722 + 0.417)/2 = **0.569**.

The lesson: rank-5 at 100 % sounds great, mAP at 57 % tells you a third of sightings are buried. That gap is why the TriNet paper reports 84.9 % rank-1 but 69.1 % mAP on the same run [1].

This exact procedure is `evaluate_reid` in `survsim/eval/tracking.py`: it sorts by `−similarity`, masks excluded entries to `−inf`, skips queries with no hit, and computes AP as `Σ(precision·hits)/Σhits` — identical to the formula above.

### 4.4 Protocol traps

- **Same-camera exclusion.** Market-1501 protocol removes gallery images of the same ID *from the same camera* as the query, otherwise near-duplicate consecutive frames inflate rank-1. [VERIFY exact wording in Market-1501 paper]
- **Closed-set vs open-set.** Benchmarks guarantee the query is in the gallery. In deployment, most "queries" (people entering a camera) are *not* anywhere in the gallery of interest. That needs a threshold and a false-match rate (e.g. TPIR at fixed FPIR), which CMC does not give.
- **mAP doesn't have an operator budget.** Repo principle 4 — report false alarms per camera-hour — applies to ReID too: a watchlist alert fired by a ReID match is an alarm.

---

## 5. Re-ranking: k-reciprocal encoding

**Intuition.** If `g` is truly the same person as `q`, then not only is `g` in `q`'s top-k — `q` is also in `g`'s top-k. False matches are often one-sided: a generic "man in dark jacket" is near many queries, but those queries aren't near each other. Zhong et al. [7] formalise this:

- **k-nearest** `N(q,k)` = top-k of q.
- **k-reciprocal** `R(q,k) = { g ∈ N(q,k) : q ∈ N(g,k) }`.
- Expand it with the reciprocal neighbours of its members (to recover positives lost to pose/view), encode the set as a weighted vector, and compute a **Jaccard distance** between the vectors of q and g.
- Final distance = `λ · d_original + (1−λ) · d_Jaccard` [7]; λ ≈ 0.3, k1 = 20, k2 = 6 [VERIFY defaults].

It needs no labels and no training [7]. TriNet's Market mAP went 69.1 → 81.1 with it [1] — a **+12 point mAP** gain for free.

**Deployment cost.** It needs the *gallery-vs-gallery* neighbourhood, i.e. O(N²) distances and a batch view of the gallery. That's fine for forensic search over yesterday's footage, awkward for online handover at 50 fps. [derived]

---

## 6. Camera topology and transition-time priors

### 6.1 Why topology is the biggest lever

**Intuition.** Appearance alone searches every person on every camera. Physics says: if someone left camera 3's east exit at t = 100 s, and the corridor to camera 7 is 40 m, a walker at ~1.3 m/s arrives around t ≈ 130 s; nobody appearing on camera 12 two floors away at t = 105 is a candidate. A prior on *where and when* collapses the candidate set before appearance even gets a vote.

### 6.2 st-ReID — combining visual and spatio-temporal similarity

Wang et al. [8] learn, from training data, a histogram of transit time for each camera pair, smooth it (Histogram-Parzen), and turn both visual similarity and spatio-temporal probability into bounded scores with **logistic smoothing** before multiplying them into a **joint similarity** [8]. Results: Market-1501 rank-1 **91.2 % → 98.1 %**, DukeMTMC-reID **83.8 % → 94.4 %** [8].

**Formulation [derived from [8]'s description].**

    p_st(Δt | c_i, c_j) = Parzen-smoothed histogram of transit times, camera pair (i,j)
    S_joint = σ_v(s_visual) · σ_st(p_st),    σ(x) = 1 / (1 + λ e^{−γx})

Logistic smoothing matters: a raw zero-probability transit time would veto a true match that happened to be slow (someone stopped for coffee). The sigmoid floor keeps a slow true match alive.

**Worked example [derived].** Two candidates on camera 7 for a person leaving camera 3. Visual cosine: X = 0.72, Y = 0.78. Transit times: X at 32 s (inside the histogram's bulk, p_st high → σ ≈ 0.9), Y at 4 s (physically implausible for 40 m, σ ≈ 0.1). Joint: X ≈ 0.72·0.9 = 0.65; Y ≈ 0.78·0.1 = 0.08. Appearance alone would have chosen Y.

### 6.3 CityFlow / AI City MTMC

CityFlow [9] is the reference MTMC benchmark: **3+ hours of synchronised HD video from 40 cameras across 10 intersections**, up to **2.5 km** between simultaneously-recording cameras, **200 k+ annotated boxes**, with camera geometry/calibration provided so that spatio-temporal reasoning is possible [9]. It is vehicles, not people, but the lessons transfer: winning AI City recipes are dominated by zone-based entry/exit rules and travel-time windows between adjacent cameras, with ReID features resolving the remaining ambiguity (see R02 §6.1 for the recipes).

### 6.4 Where topology fails

- **Dwell.** Toilets, shops, cars: a person may vanish for 20 minutes. Transit priors must have heavy tails.
- **Blind-spot behaviour change.** The adversarial case this repo models: the jacket comes off in exactly the region no camera sees. The time prior is still good; appearance is now actively misleading.
- **Topology drift.** A closed door or new barrier changes transit distributions. Priors must be re-estimated online from confident matches [derived].

---

## 7. Gallery management

What a benchmark hides and a system must decide [derived unless cited]:

1. **Track-level, not image-level features.** Average (or quality-weight) L2-normalised features across a tracklet; one blurred frame shouldn't define a person. Weight by box height, occlusion (from masks — the repo's box truth is mask-derived precisely so this can be measured), and detector confidence.
2. **Gallery lifetime.** Cross-camera candidates expire when they can no longer physically arrive (topology) or after a site-specific window. A gallery that grows forever raises false-match probability roughly linearly with its size: at a fixed per-comparison false-match rate `p`, the probability of at least one false match against N identities is `1 − (1−p)^N ≈ 1 − e^{−Np}`, which is ≈ Np only while Np ≪ 1. At p = 1e-4 and N = 5 000, Np = 0.5 and the exact value is ≈ 39 %. [derived]
3. **Update policy.** Updating a gallery template with a new sighting fixes drift (lighting through the day) but risks **template poisoning** — one wrong merge contaminates every future match. Update only above a high-confidence threshold, and keep the original template.
4. **Appearance epochs.** When an appearance change is detected (or suspected: a track that re-enters at the right time with the wrong colours), open a new *appearance* template under the same *identity* hypothesis rather than overwriting. This is exactly the data structure the simulator's ground truth uses (§9).
5. **Retention.** Templates of people who are not subjects of interest are personal data — and, if used to uniquely identify, biometric data (§8). Retention must be short and justified.

---

## 8. Clothes-changing ReID: where surveillance actually lives

**Why standard ReID is the wrong test.** Market-1501 and Duke are single-day, same-clothes. Much of what they measure is *clothing matching*. The moment a subject changes a top, colour histograms and most learned features point the wrong way.

**Benchmarks.**
- **PRCC** — 221 identities, 33,698 images, cameras A/B same clothes, camera C different clothes [11]; Yang et al. used contour sketches to rely on body shape rather than colour [11].
- **LTCC** — 152 identities, 17,119 images [10] (LTCC paper [12]); people captured over a long period with frequent clothing changes, with a shape-embedding and "cloth-elimination shape-distillation" method [12].

**Numbers to know (CAL Table 2/3, CVPR 2022) [10].**

| Method | LTCC general top-1 / mAP | LTCC clothes-changing top-1 / mAP | PRCC same-clothes top-1 / mAP | PRCC clothes-changing top-1 / mAP |
|---|---|---|---|---|
| PCB (RGB) | 65.1 / 30.6 | 23.5 / 10.0 | 99.8 / 97.0 | 41.8 / 38.7 |
| FSAM (RGB+pose+sil.) | 73.2 / 35.4 | 38.5 / 16.2 | 98.8 / – | 54.5 / – |
| CAL baseline | 65.5 / 29.4 | 28.1 / 11.0 | 99.8 / 97.9 | 45.6 / 43.3 |
| **CAL** | **74.2 / 40.8** | **40.1 / 18.0** | **100 / 99.8** | **55.2 / 55.8** |

**Read it this way.** On PRCC, the *same* network goes from **~100 % rank-1 same-clothes to ~55 % across a clothing change** [10]. On LTCC clothes-changing, the best RGB method's mAP is **18 %** [10]. That is the size of the problem, and it is the single most persuasive number for why a simulator with appearance epochs is useful.

**How CAL works [10].** Add a clothes classifier on the features and train the backbone *adversarially* against it: penalise the model's ability to predict clothes so it has to rely on face, hairstyle, body shape and gait. A naive clothes classifier trained *cooperatively* makes it worse (LTCC CC top-1 21.9 vs 28.1 baseline) [10] — a nice counter-intuitive fact: telling the network about clothes teaches it to use clothes.

**Gait as fallback.** CAL's CCVID table shows GaitSet at 81.9/73.2 general and 71.0/62.1 clothes-changing (top-1/mAP), versus CAL's 82.6/81.3 and 81.7/79.6 [10] — gait loses less under clothing change than appearance does, but a good clothes-invariant RGB model can still beat it on video. [10]

---

## 9. Tie to the repository

### 9.1 Appearance epochs — `survsim/core/appearance.py`

`AppearanceState` hashes outfit, accessories, hair, face and gait style (`blake2b`, 8-byte digest). `apply(delta, t)` changes the state, and **if the hash changes, `epoch += 1` and `epoch_started_s = t`**. So an *epoch* is a maximal interval of constant appearance; `survsim/gt/writers.py` writes `appearance_epoch` per agent-frame and one row per epoch, and evaluation joins on `(uid, epoch)`.

This is the ground truth CAL's benchmarks have to hand-label: PRCC encodes it by *camera* (camera C = different clothes) [11]; the simulator encodes it *per person per second*, including changes that happen inside blind spots.

`soft_biometrics()` returns `SOFT_BIOMETRIC_KEYS = (height_m, shoulder_w, bmi_class, skin_tone, age_band)` plus flattened `gait_*` columns. The docstring's key point: gait is *the one soft biometric a person can deliberately change* (via `director/evasion.fake_limp`), so it is recorded separately rather than blended, so an evaluation can ask how much identification depended on an evader-controlled cue.

### 9.2 Gait signature — `survsim/gait/signature.py`

A `GaitSignature` is six numbers: cadence (spm), step length (m), asymmetry, arm swing, sway amplitude (m), stance width (m).

- **Individuality**: each person gets a stable seeded offset per parameter (`INDIVIDUAL_SPREAD`, e.g. 7 % cadence, 9 % step, 0.04 absolute asymmetry). Without it, two "normal" walkers are identical and a gait matcher scores at chance or perfectly — both meaningless.
- **Calibration**: free-walking cadence and step come from `director/crowd.py`; the module docstring cites MOT20 pose measurements of **123 spm at 0.39 m step in a crowd vs ~110 spm, ~0.75 m free** (docs/14 §10) — crowds shorten stride, they don't slow cadence.
- **Measured vs argued styles**: `carrying_bag` and `heavy_coat` multipliers are marked MEASURED from CASIA-B, paired within subject (docs/14 §13); coat changes asymmetry by −0.0001 (z = −0.1) while a bag adds +0.040 (z = +9.9). That null result is direct evidence that clothing changes appearance without changing gait symmetry — the premise of gait ReID. Limp/drunk/shuffle are explicitly ARGUED.
- **Distance**: `gait_distance` is RMS difference in units of **population standard deviation** when a `population_spread` vector is passed (`gait_similarity_matrix` computes one by default; `gait_distance` itself defaults to unit spread, i.e. unnormalised), so 1.0 = "as different as two random people". Unnormalised Euclidean would be a cadence comparison (cadence ~110 vs asymmetry ~0.04).
- **Observation noise**: `observe(signature, noise=0.15)` adds Gaussian error at 15 % of between-person spread, because matching clean signatures against themselves measures nothing.
- **Same scorer**: `gait_similarity_matrix` returns `−distance` and is fed into `eval.tracking.evaluate_reid`, so gait and appearance get the **identical rank-1/rank-5/mAP definitions** of §4.

### 9.3 Scoring within vs across epochs — `survsim/eval/tracking.py::reid_by_epoch`

L2-normalises features, uses cosine similarity (as BNNeck recommends [2]), and reports two numbers:

- **within_epoch**: excludes self, same-camera pairs, and same-ID-different-epoch positives → "can you re-find someone wearing the same clothes on another camera?" (the Market-1501 question).
- **cross_epoch**: excludes self and same-ID-same-epoch positives → "can you re-find them after they changed?" (the PRCC-CC / LTCC-CC question).
- `rank1_drop_across_appearance_change` = the difference; in the literature that drop is ~45 points on PRCC [10].

Other identities stay in the gallery as distractors in both cases — removing them would make the task trivial.

**Observation to raise (not a claim of a bug) [derived].** The cross-epoch scope does not apply the same-camera exclusion that the within-epoch scope does. That's defensible — a changed outfit on the same camera is a legitimate hard case — but it means the two numbers use slightly different protocols, which should be stated whenever the drop is quoted.

### 9.4 What the simulator adds that benchmarks can't

1. Exact epoch boundaries, including off-camera changes.
2. Transit-time ground truth per camera pair, from the director's actual agent trajectories (principle 1: "truth is what happened"), so st-ReID-style priors [8] can be learned and scored without annotation.
3. Deliberate gait evasion with a measurable degradation, rather than an annotation.
4. Hard negatives: the same outfit on different people (population generator), the case where appearance ReID *should* fail and a good system must not merge.

What it can't yet do (per CLAUDE.md): MetaHuman wardrobe changes in the Unreal backend are blocked on engine work, so image-level clothes-changing ReID on photoreal renders is not available; the epoch machinery is exercised on the mock backend and in the GT.

---

## 10. Privacy, soft biometrics and law (UK/EU)

### 10.1 When is ReID "biometric"?

UK GDPR Art. 4(14): biometric data is "personal data resulting from specific technical processing relating to the physical, physiological or behavioural characteristics of a natural person, which allow or confirm the unique identification of that natural person, such as facial images or dactyloscopic data" [13]. The ICO adds that it is **special category data** when processed *for the purpose of uniquely identifying* a person, requiring an Art. 9 condition, and lists **gait analysis** among biometric techniques [14]. Holding photographs alone is not automatically biometric data; the line is crossed by technical processing into templates for automated matching [14].

**So what for ReID [derived from [13][14]].**
- A ReID embedding is a template produced by specific technical processing of physical (and, with gait, behavioural) characteristics.
- Within-site, anonymous tracklet linking ("the same unknown person went from door A to door B") arguably does not aim to identify a *named* individual — but the ICO focus is on unique identification, and linking sightings of one person over hours singles them out. Treat it as likely special-category and do a DPIA.
- Watchlist matching (is this the person in this reference image?) is unambiguously unique identification.
- Gait and height are explicitly in scope: "soft" biometrics are not a loophole.

### 10.2 EU AI Act, Article 5

Prohibited practices include [15]:
- **5(e)** untargeted scraping of facial images from the internet or **CCTV footage** to build facial recognition databases;
- **5(g)** biometric categorisation to infer race, political opinion, religion, sexual orientation, etc.;
- **5(h)** real-time remote biometric identification in publicly accessible spaces for law enforcement, save narrow exceptions (victim search, imminent threat, locating suspects of serious offences) [15].

Other RBI uses are high-risk rather than banned [VERIFY Annex III wording].

**Design consequences [derived].**
- Keep attribute-based search (colour, bag, "red jacket") separate from anything that infers protected characteristics. `skin_tone` in `SOFT_BIOMETRIC_KEYS` is fine as *simulator ground truth* for fairness testing, but a deployed product that categorises by it walks towards 5(g).
- Don't build galleries from untargeted CCTV — enrol only subjects of a lawful investigation.
- Prefer on-site, short-retention, tracklet-level linking; log every cross-camera match with a human decision.
- Synthetic data is a genuine privacy tool here: you can train and *evaluate* cross-epoch ReID and fairness across skin tone / height without collecting biometric data of real people. That is a legitimate selling point of the simulator, not just convenience.

---

## 11. How to say this in an interview

- **One-liner.** "ReID is metric learning for strangers: train a classifier over known identities so the penultimate layer becomes a space where distance means identity, then rank strangers in it."
- **The strong baseline.** "ResNet-50, ID + batch-hard triplet, BNNeck — triplet on the pre-BN feature, softmax on the post-BN feature, cosine at inference. That's 94.5 rank-1 / 85.9 mAP on Market with no bells [2]. Anything fancy has to beat that."
- **Why batch-hard.** "Random triplets are mostly already satisfied, so there's no gradient; picking the farthest positive and closest negative within a PK batch took triplet ReID from ~41 to 69 mAP [1]."
- **Metrics.** Draw the ✓✗✓✗✗✓ example: rank-1 hides buried sightings, mAP exposes them. Then say: "Neither has an operator budget; in deployment it's open-set, so I care about false-match rate at a threshold, per camera-hour."
- **Topology.** "The cheapest accuracy is physics. st-ReID took Market rank-1 from 91 to 98 just by multiplying in a smoothed transit-time prior [8]." Give the X/Y worked example.
- **Clothes change.** "On PRCC the same model goes from ~100 % to ~55 % rank-1 once clothes change; LTCC clothes-changing mAP is 18 % for the best RGB method in CAL [10]. That's why our simulator records appearance epochs and reports within-epoch vs cross-epoch rank-1 separately — one averaged number hides the failure a disguise is designed to cause."
- **Gait.** "Gait is the soft biometric that survives clothing, and the only one an evader can deliberately change. In our sim it's a six-parameter signature with per-person offsets, calibrated to MOT20 and CASIA-B, scored with the same rank-1/mAP code as appearance."
- **Law.** "In the UK a ReID template is biometric data once it's used to uniquely identify someone, gait included [13][14]. The EU AI Act bans untargeted scraping of CCTV into face databases and biometric categorisation by protected traits [15]. So: targeted enrolment, short retention, human-in-the-loop, and synthetic data for fairness testing."

---

## References

All fetched on 2026-09-26.

1. Hermans, Beyer, Leibe, "In Defense of the Triplet Loss for Person Re-Identification", arXiv:1703.07737 — https://arxiv.org/abs/1703.07737 and PDF https://arxiv.org/pdf/1703.07737. Taken: batch-hard loss, soft-margin variant "performs slightly better", P=18/K=4 (TriNet), P=32/K=4 (LuNet), Market-1501 69.14 mAP / 84.92 rank-1, 81.07 mAP re-ranked, DTL 41.5 mAP comparison.
2. Luo et al., "Bag of Tricks and A Strong Baseline for Deep Person Re-identification", arXiv:1903.07071 — https://arxiv.org/abs/1903.07071 and PDF. Taken: 94.5/85.9 Market-1501; LR 3.5e-4, ×0.1 at 40/70, 120 epochs; ε=0.1; last stride 16×8; BNNeck mechanics (f_t triplet, f_i ID, no classifier bias, f_i + cosine at inference); Duke ablation numbers; cross-domain remarks.
3. Zhou et al., "Omni-Scale Feature Learning for Person Re-Identification" (OSNet), arXiv:1905.00953 — https://arxiv.org/abs/1905.00953. Taken: multi-stream block, unified aggregation gate, depthwise/pointwise, lightweight, six datasets.
4. He et al., "TransReID: Transformer-based Object Re-Identification", arXiv:2102.04378 — https://arxiv.org/abs/2102.04378. Taken: JPM, SIE (camera/view), motivation re CNN detail loss.
5. Li, Sun, Li, "CLIP-ReID", arXiv:2211.13977 — https://arxiv.org/abs/2211.13977. Taken: two-stage learnable per-ID text tokens; CLIP init already competitive; AAAI 2023.
6. Sun et al., "Circle Loss: A Unified Perspective of Pair Similarity Optimization", arXiv:2002.10857 — https://arxiv.org/abs/2002.10857. Taken: re-weighting less-optimised similarities, unifying class/pair-wise learning, circular boundary. Unified-loss formula and O_p/O_n/Δ_p/Δ_n settings checked against https://ar5iv.labs.arxiv.org/html/2002.10857 at audit.
7. Zhong et al., "Re-ranking Person Re-identification with k-reciprocal Encoding", arXiv:1701.08398 — https://arxiv.org/abs/1701.08398. Taken: k-reciprocal neighbours, Jaccard distance, combination with original distance, unsupervised/automatic.
8. Wang et al., "Spatial-Temporal Person Re-identification", arXiv:1812.03282 — https://arxiv.org/abs/1812.03282. Taken: logistic smoothing, Histogram-Parzen, joint similarity; Market 91.2→98.1, Duke 83.8→94.4 rank-1.
9. Tang et al., "CityFlow", arXiv:1903.09254 — https://arxiv.org/abs/1903.09254. Taken: 3+ h, 40 cameras, 10 intersections, 2.5 km, 200k+ boxes, calibration provided.
10. Gu et al., "Clothes-Changing Person Re-identification with RGB Modality Only" (CAL), arXiv:2204.06890 — https://arxiv.org/abs/2204.06890 and PDF. Taken: Table 1 LTCC 152 IDs / 17,119 images; Table 2 LTCC/PRCC comparisons; Table 3 ablation (clothes classifier, baseline, CAL); Table 4 Market/MSMT17 OSNet, CircleLoss; Table 5 CCVID GaitSet.
11. Yang et al., "Person Re-identification by Contour Sketch under Moderate Clothing Change", arXiv:2002.02295 — https://arxiv.org/abs/2002.02295. Taken: PRCC 221 IDs, 33,698 images; contour-sketch approach. (Camera A/B/C layout from search-result summary of the paper — treat as [VERIFY].)
12. Qian et al., "Long-Term Cloth-Changing Person Re-identification", arXiv:2005.12633 — https://arxiv.org/abs/2005.12633. Taken: LTCC purpose, shape embedding and cloth-elimination shape-distillation.
13. UK GDPR Art. 4 (legislation.gov.uk) — https://www.legislation.gov.uk/eur/2016/679/article/4. Taken: Art. 4(14) definition quoted.
14. ICO, "What is special category data?" — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-is-special-category-data/. Taken: special category when for unique identification; gait listed; photos not automatically biometric.
15. EU AI Act Art. 5 (artificialintelligenceact.eu) — https://artificialintelligenceact.eu/article/5/. Taken: 5(e) untargeted scraping incl. CCTV, 5(g) biometric categorisation, 5(h) real-time RBI for law enforcement and exceptions.

Repo files read: `survsim/gait/signature.py`, `survsim/core/appearance.py`, `survsim/eval/tracking.py` (`evaluate_reid`, `reid_by_epoch`), `survsim/gt/writers.py`. Cross-references: R02 §3–§6, 18_PERCEPTION_STACK.
