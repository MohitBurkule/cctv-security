# 30 · Synthetic data and sim2real: why it transfers, how to measure the gap, and what a CCTV rendering pipeline has to get right

**Scope.** Doc 24 surveyed *which* synthetic pedestrian datasets exist and what
train-synthetic-test-real (TSTR) numbers they report (MOTSynth, PeopleSansPeople,
PersonX, BEDLAM...). This document does not repeat that survey. It covers the
*mechanisms* underneath it:

1. Why synthetic data transfers at all, and why two opposite recipes both work:
   domain randomisation (make the sim deliberately unrealistic but diverse) and
   photorealism (make the sim look like the target).
2. Structured domain randomisation: the middle path, which is the one SurvSim is
   actually on.
3. How to *measure* the distance between a synthetic and a real image set: FID,
   KID, their biases, their Inception dependency, and precision/recall, which
   splits "realistic" from "diverse".
4. Low-level image statistics as a cheaper and more diagnosable alternative,
   as implemented in `survsim/realism/` and `docs/15_REALISM_STATS.md`.
5. What a rendering + degradation pipeline must model to look like CCTV: PBR,
   image-based lighting, exposure, sensor noise, rolling shutter, codec and
   motion blur. This part is tied to `survsim/sensors/degrade.py` and
   `docs/12_UNREALCV_ENGINE_NOTES.md`.

Citation convention. `[n]` is a source fetched while writing this document
(listed in References with what was taken from it). **[derived]** means my own
arithmetic or reasoning from cited material. **[VERIFY]** means a claim I
believe but did not fetch a primary source for this session. Repository facts
are cited by file path.

---

## 1. The core idea in one paragraph

A detector trained on distribution *S* (synthetic) and tested on *R* (real)
suffers when the features it relies on are distributed differently in *S* and
*R*. There are two ways to shrink that mismatch:

* **Move S onto R (photorealism).** Render so well that the features look
  the same in both. This costs artists, assets and compute, and it never
  fully gets there. The residual gap is systematic: the same wrong specular
  model, the same too-clean noise, on every image.
* **Make S so wide that R is inside it (domain randomisation, DR).** Randomise
  textures, lights, camera poses and distractors so violently that the network
  cannot rely on any of them. The only thing constant across the training set
  is the object's shape and context, so that is what it learns. Tobin et al.
  put it this way: with enough variability, "the real world may appear to the
  model as just another variation" [1].

Both work. Neither is free. The interesting engineering question, and the one
right, and how you know*. The answer for CCTV is that the **imaging chain**
(exposure, noise, codec, resolution) must be *right*, because it is narrow and
systematic in real CCTV. **Appearance and scene content** (clothes, lighting
direction, backgrounds) should be *randomised within plausible structure*,
because real CCTV is wide there.

---

## 2. Domain randomisation: the evidence and the mechanism

### 2.1 Tobin et al. 2017: DR for robot grasping

Tobin et al. trained an object localiser only on simulated RGB images. The
renders used deliberately "non-realistic random textures", randomised
lighting and camera placement. The localiser reached about **1.5 cm**
accuracy in the real world, and the authors describe it as the first
successful transfer of a deep network trained only on simulated RGB images
to real-world robotic control [1].

**Mechanism.** Think of the network as a function that must be invariant to
nuisance variables *z* (texture, light, background) and sensitive to the
object's state *y*. In real data, *z* varies over some range *Z_R* that you do
not know. If training covers a range *Z_S* ⊇ *Z_R*, the invariance you learnt
covers the test case. DR approximates ⊇ by making *Z_S* very large. It works
without knowing *Z_R* at all. The price is capacity and data spent learning
invariance to variations that never occur. **[derived]**

### 2.2 Tremblay et al. 2018: DR for car detection, with numbers

Tremblay et al. carried DR from a tabletop to a detection task on KITTI cars
[2]. What they generated:

* 100K images with at most 14 cars each. Each car was drawn from 36 sedan and
  hatchback models and given one of **8K random textures** [2].
* Random numbers of lights, random viewpoints (the paper lists camera
  azimuth 0 to 360° and elevation 5 to 30°), and a random background image [2].
* **"Flying distractors"**: random geometric shapes (cones, pyramids...)
  scattered in the scene with random textures. They force the network to
  ignore nearby clutter and to handle partial occlusion [2].

Results, AP@0.5 on a KITTI subset, trained on synthetic only [2]:

| architecture | trained on VKITTI (2.5K photoreal-ish images) | trained on DR (100K images) |
|---|---|---|
| Faster R-CNN | 79.7 | 78.1 |
| R-FCN | 64.6 | 71.5 |
| SSD | 36.1 | 46.3 |

"Cartoonish" DR images matched or beat a dataset built specifically to clone
KITTI in 2 of 3 architectures. After fine-tuning on all 6,000 real images, DR
reached **AP 98.5**: 1.6 points above VKITTI plus real, and 2.1 points above
real only [2].

The **ablation** is the part to remember, because it shows *which*
randomisation carries the effect. Faster R-CNN, 50K images, full DR baseline
AP 73.7 [2]:

| removed component | AP | drop |
|---|---|---|
| random lights → fixed light | 67.6 | −6.1 |
| random textures → none | 69.0 | −4.7 |
| data augmentation (contrast, brightness, crop, flip, resize, Gaussian noise) | 72.0 | −1.7 |
| 8K → 4K textures | 71.5 | −2.2 |
| flying distractors removed | 72.6 | −1.1 |
| no light augmentation (3D lights still random) | 73.6 | −0.1 |

**Lighting variation is the single most important factor.** Removing
geometric randomised lights (fixed light) costs 6 AP, but removing 2D
brightness/contrast augmentation costs almost nothing once lights are
randomised in 3D [2]. That is a precise, quotable result: *3D lighting
variation cannot be replaced by 2D photometric augmentation*. This bears on
SurvSim's decision to vary sun angle, night lamps and metered exposure in the
engine, rather than as post-hoc jitter. **[derived]**

A second result that surprises people: Tremblay et al. found **freezing** the
ImageNet-pretrained early layers harmful. Full fine-tuning gave Faster R-CNN
78.1 vs 66.4 frozen, and R-FCN 71.5 vs 69.4 [2]. Hinterstoisser et al.
reported the opposite for plain OpenGL renders: freezing the feature extractor
at real-image weights and training only the later layers works well [5].
The reconciliation **[derived]**: freezing protects a feature extractor from
learning synthetic-only low-level statistics. That helps when the renders are
crude (OpenGL, no noise model). It hurts when the synthetic set is rich enough
that adapting the features is net positive. It is an empirical hyperparameter,
not a law. Test both.

### 2.3 Where plain DR fails: context and small objects

Plain DR scatters objects without regard to scene structure. That is fine for a
large car in the middle of the frame. It fails for small, distant, occluded
objects, whose recognition depends on *context*: cars are on roads, people are
on floors. Prakash et al. (same NVIDIA group) measured this [3]. Faster R-CNN,
AP@0.7 on the full 7,500 KITTI images, trained on synthetic only:

| training set | size | Easy | Moderate | Hard |
|---|---|---|---|---|
| VKITTI clones | 2.2K | 49.6 | 44.8 | 33.6 |
| VKITTI | 21K | 70.3 | 53.6 | 39.9 |
| Sim 200k (GTA V) | 200K | 68.0 | 52.6 | 42.1 |
| DR | 25K | 56.7 | 38.8 | 24.0 |
| **SDR** | 25K | **77.3** | **65.6** | **52.2** |

DR does reasonably on Easy (big cars) and collapses on Moderate and Hard. The
authors attribute this to small objects needing context [3]. KITTI's
difficulty levels are defined by minimum box height and maximum occlusion
[3], so Hard is essentially "small or occluded". That is exactly the CCTV
regime: SurvSim's far cameras see 14 to 40 px people at 45 to 60 m (docs/12 batch_v5).
**[derived]**

### 2.4 Structured DR (SDR): randomise *inside* a scene grammar

SDR samples a scene from a hierarchy: first a global scenario (road shape,
number of lanes), then context splines (lanes, sidewalks), then objects placed
*on* those splines with context-dependent probability, then the usual
randomised textures, lights and distractors [3]. It keeps DR's variation
while restoring the co-occurrence statistics that small-object detection needs.

Two further SDR results matter for a simulator pitch [3]:

* **Data efficiency.** SDR saturates around 10K images and reaches 43.7 AP
  with just 1K. Plain DR does not saturate until about 50K.
* **Synthetic beats wrong-domain real.** On a 1,500-image KITTI test split,
  SDR (25K synthetic) scored 69.6 / 65.8 / 52.5. BDD100K (70K *real* images
  from a different domain) scored 59.7 / 54.3 / 45.6 [3]. The paper's
  conclusion is that there is a reality gap, but also large gaps *between
  real datasets*.

That second point is the strongest argument for a CCTV simulator. A
customer's camera, with its height, pitch, codec and night IR, is its own
domain. COCO, or even MOT20, is "wrong-domain real". Well-structured
synthetic data from a matched viewpoint can beat it. **[derived]**

### 2.5 Photorealism: the other pole

Johnson-Roberson et al. ("Driving in the Matrix") trained Faster R-CNN on
frames captured from GTA V with automatic labels. They report that the
synthetic-only network outperformed the identical architecture trained on
2,975 human-labelled Cityscapes images, tested on all 7,481 KITTI images [4]:

| training | Easy | Moderate | Hard |
|---|---|---|---|
| Sim 200k (GTA) | 68.03 | 52.57 | 42.07 |
| Cityscapes (real, 2,975) | 62.47 | 42.74 | 35.66 |

Compare the SDR table: 25K SDR images (77.3 / 65.6 / 52.2) beat 200K
photorealistic GTA images (68.0 / 52.6 / 42.1) on the same metric [3].
**Structure and variation mattered more than pixel fidelity, at 8× less
data.** This is the correct headline. The wrong one is "realism doesn't
matter". SurvSim's own data shows why.

### 2.6 SurvSim's own evidence: realism *of the person* matters

docs/12 ("Detector: MetaHuman vs CesiumMan, same GT") holds everything fixed
(same runs, cameras, GT boxes and lighting) and swaps only the character mesh.
A COCO-trained yolov8n's person recall over 770 GT boxes rose from
**0.577 (CesiumMan) to 0.758 (MetaHuman)**, and precision from 0.852 to 0.884.
At a matched 50 px box height, mean person confidence went 0.439 → 0.634 and
recall@0.25 went 0.72 → 0.96.

How to square this with Tremblay [2]: in DR, the *nuisance* variables are
unrealistic, but the *object* (a 3D car model) is geometrically correct.
CesiumMan is a stylised figure. Its silhouette, proportions and clothing
cues are the *signal*, not the nuisance. Photorealism is required for the
signal; randomisation is acceptable for the nuisance. **[derived]** This is the

Note what that experiment is: a *detector-as-judge* measurement. A frozen
real-trained model is a proxy for "do these pixels look like people to
something that learned people from photographs". It is cheap, has no sample
size bias, and is stratifiable by pixel height. Its weakness is that it
inherits the judge's blind spots. yolov8n misses 14 to 40 px people in *real*
footage too (docs/12 batch_v5: far cams 0.0 to 0.11).

---

## 3. Measuring distribution distance: FID and KID from first principles

### 3.1 Intuition

You cannot compare two image sets pixel by pixel. So you (a) map each image
to a feature vector with a fixed network, then (b) compare the two *clouds*
of vectors. Every metric in this section is a choice of (a) the feature
network and (b) the cloud comparison. Their failure modes follow directly
from those two choices.

### 3.2 FID

Heusel et al. introduced the Fréchet Inception Distance [6]. It fits a
Gaussian to each cloud of Inception-v3 pool features (2048-d) and computes the
Fréchet (Wasserstein-2) distance between the two Gaussians [6][8]:

$$\mathrm{FID} = \lVert \mu_r - \mu_g \rVert_2^2 + \operatorname{Tr}\!\left(\Sigma_r + \Sigma_g - 2(\Sigma_r\Sigma_g)^{1/2}\right)$$

Read it term by term:

* **Mean term.** How far apart the centres are. A global colour cast or
  exposure offset that moves every feature a bit lands here.
* **Trace term.** How different the spreads are. A synthetic set that is too
  uniform (low diversity) has a small Σ_g, and the trace term penalises the
  mismatch.

**Worked 1-D example [derived].** With scalars, the trace term is
σ_r² + σ_g² − 2σ_rσ_g = (σ_r − σ_g)². So FID₁ᴰ = (μ_r − μ_g)² + (σ_r − σ_g)².
Let real luma features have μ = 0, σ = 1. A synthetic set with μ = 0.5 and
σ = 0.6 scores 0.25 + 0.16 = 0.41. Shifting the mean alone by 0.64 gives the
same number. **FID cannot tell "too narrow" from "shifted"**. That is why
precision/recall (§4) exists.

**Why ≥ 2048 samples.** Σ is 2048×2048. With N < 2048 images, the sample
covariance has rank ≤ N−1: it is singular by construction. `sqrtm` still
returns a number, and it looks like an FID. SurvSim encodes this as a guard
in `survsim/eval/realism.py` (`FID_MIN_SAMPLES = 2048`). The comment there
records that the first attempt would have reported an FID from 12 frames
"with a straight face". The same file computes Tr((Σ_rΣ_g)^{1/2}) without
forming the matrix square root (`_trace_sqrt_product`), because the direct
Schur decomposition on 2048² is slow and unstable when Σ is near-singular.

### 3.3 FID is biased, and the bias depends on the model

Bińkowski et al. showed that the standard FID estimator is **biased**. On
CIFAR-10, at n = 10,000 (the full test set), FID between the training and
test sets still seemed to be falling from about 8.1 towards zero. They also
built distributions where the true ordering FID(P₁,Q) < FID(P₂,Q) is reversed
by finite-sample estimates "even estimating with n = 50,000 samples" [7].

Chong and Forsyth characterised the bias [8]:

$$\mathbb{E}[\widehat{\mathrm{FID}}_N] = \mathrm{FID}_\infty + \frac{K}{N} + O(1/N^2)$$

The key word is that **K depends on the generator**. Two models evaluated at
the same N carry *different* biases, so a fixed-N comparison can flip. Their
example: two DCGANs of identical architecture, where DCGAN 1 is better at one
N, they tie at another, and DCGAN 2 is better at a third [8]. The fix,
FID∞, is to compute FID at several N (subsets of at least 5K drawn from a
50K pool), regress it against 1/N, and read off the intercept [8].

**What this means for SurvSim [derived].** A realism score compared across
releases must be computed at the **same N**, and preferably reported as
FID∞ or as KID. "FID went from 48 to 41" between batch_v4 and batch_v6 means
nothing if v6 used more frames.

### 3.4 KID: an unbiased alternative

Bińkowski et al. proposed the Kernel Inception Distance [7]. It is the
squared **Maximum Mean Discrepancy** between the feature clouds, with a cubic
polynomial kernel:

$$k(x,y) = \left(\tfrac{1}{d}\,x^\top y + 1\right)^3$$

where d is the feature dimension (2048) [7]. The unbiased estimator, for m
real features x and n synthetic features y, is:

$$\widehat{\mathrm{KID}} = \frac{1}{m(m-1)}\sum_{i\ne j}k(x_i,x_j) + \frac{1}{n(n-1)}\sum_{i\ne j}k(y_i,y_j) - \frac{2}{mn}\sum_{i,j}k(x_i,y_j)$$

Intuition: the average similarity *within* each set, minus twice the
similarity *across* them. If the sets are drawn from the same distribution,
the three terms cancel in expectation. Excluding i = j in the within-set sums
is exactly what removes the bias. The paper states KID's estimator is
unbiased and asymptotically normal, so you can put **confidence intervals**
on it [7]. The cubic kernel matches means, and also second and third moments
of the features. It makes no Gaussian assumption. **[derived]** from the
kernel's polynomial form.

**Practical rule.** For small synthetic sets (hundreds to low thousands of
frames per camera, which is SurvSim's regime), report KID with a
bootstrap CI, not FID. **[derived]**

### 3.5 Preprocessing changes FID

Parmar et al. (Clean-FID) showed that low-level choices move FID
substantially [13]. Common resize implementations alias. Worse, if the
real set is JPEG-compressed, applying the same compression to the generated
set *improves* FID [13].

That second finding cuts directly at a CCTV simulator. Real CCTV frames are
heavily compressed. So *adding the codec to renders will lower FID whether or
not anything else improved*. FID will reward matching the codec, which is
partly legitimate (the codec is part of the domain). But it means FID cannot
tell you whether your *people* got more realistic. It gets dominated by
whichever low-level statistic mismatches most. **[derived]**

### 3.6 The Inception problem: FID sees ImageNet classes

Kynkäänniemi et al. (2023) showed that Inception features encode ImageNet
class evidence so strongly that FID can be moved **without improving image
quality** [9]:

* Resampling generated images so that their Top-1 ImageNet class histogram
  matches the real set's reduces FID by about 8 to 11 % (FFHQ −11.3 %).
  Resampling in pre-logit space reduces it by 42 to 72 % (FFHQ −66.4 %,
  Places −72.3 %, AFHQ Dog −42.2 %). FID computed on CLIP features barely
  moves [9].
* Grad-CAM shows FID on faces attends to regions **outside the face**
  (accessories, clothing, background objects), because ImageNet has no
  "face" class [9].
* Projected FastGAN and StyleGAN2 have near-identical FID (5.28 vs 5.30),
  but FID-CLIP is 4.67 vs 2.76, and FastGAN's faces are visibly more distorted
  [9].

**Implication for CCTV [derived].** ImageNet has no "pedestrian at 40 px
under sodium light" class. An Inception-FID between SurvSim renders and real
CCTV will be driven by whatever ImageNet objects dominate the scene: cars,
street furniture, "parking meter", "street sign". It will say little about
people. Stein et al. ran a large human study and found **no existing metric
correlates strongly with human judgement**. They trace this partly to
Inception-v3 features and recommend DINOv2-ViT-L/14 features instead [14].
Self-supervised ViT features (DINO) carry explicit semantic segmentation
information without labels [15]. That makes them a better base for "does this
*region* look right". An actionable upgrade for `survsim.eval.realism` is
therefore to compute KID on DINOv2 features of **person crops**, stratified
by pixel height, alongside whole-frame statistics. **[derived]**

---

## 4. Precision and recall for generative models: splitting fidelity from coverage

### 4.1 Why one number is not enough

A single divergence mixes two failures [11]:

* **Low precision.** The synthetic images include things that never occur in
  real data (artefacts, cartoon people). Training on them teaches the model
  wrong features.
* **Low recall.** The synthetic set covers only part of real variation (only
  daylight, only frontal views, only one body shape). Training on it leaves
  holes.

Sajjadi et al. formalised precision and recall *for distributions* to
disentangle sample quality from coverage [11]. Kynkäänniemi et al. (2019)
made it practical and robust with k-NN manifolds [10]. Their paper states
directly that a low FID "may indicate high precision (realistic images), high
recall (large amount of variation), or anything in between" [10].

### 4.2 The k-NN definition (Kynkäänniemi et al. 2019)

Embed the real set Φ_r and the generated set Φ_g (they used VGG-16 features
after the second fully connected layer, with 50K images per set, and k = 3)
[10]. Around each feature φ′, draw a hypersphere whose radius is the distance
to its k-th nearest neighbour in its own set. The union of those spheres
estimates the manifold. Then [10]:

$$f(\phi,\Phi) = \begin{cases}1 & \text{if } \lVert\phi-\phi'\rVert_2 \le \lVert\phi'-\mathrm{NN}_k(\phi',\Phi)\rVert_2 \text{ for some } \phi'\in\Phi\\ 0 & \text{otherwise}\end{cases}$$

$$\text{precision} = \frac{1}{|\Phi_g|}\sum_{\phi_g\in\Phi_g} f(\phi_g,\Phi_r),\qquad \text{recall} = \frac{1}{|\Phi_r|}\sum_{\phi_r\in\Phi_r} f(\phi_r,\Phi_g)$$

In words:

* **Precision** is the fraction of synthetic samples that land inside the
  real manifold.
* **Recall** is the fraction of real samples that land inside the synthetic
  manifold.

**Worked example [derived].** Suppose 1,000 real CCTV frames are 70 % day
and 30 % night. SurvSim renders 1,000 frames, all day, all realistic.
Precision ≈ 1.0 (every render looks like some real day frame). Recall ≈ 0.7
(no synthetic sphere covers the night frames). Now render 50 % day, 50 %
night, but with night lamps that are too amber (the docs/12 batch_v5 note
says "night frames read amber and bright near lamps"). Recall rises toward
1.0, but night precision falls because those renders sit off the real night
manifold. FID would blend both effects into one number and hide which fix is
needed.

### 4.3 Robustness caveats

Naeem et al. showed that k-NN precision/recall is **sensitive to outliers**
(one real outlier inflates a sphere and swallows many fakes). It can also fail
to report 1.0 for identical distributions, and its hyperparameters are
arbitrary. They propose **density** and **coverage** as more reliable
replacements [12]. **[VERIFY]** the exact formulas: density counts how many
real-sample spheres contain each fake, divided by k. Coverage is the fraction
important point is the *why*: spheres centred on real samples are more
robust than spheres centred on generated ones, because the real set does
not contain generator outliers.

### 4.4 The same idea, with a detector as the embedding

SurvSim's "detector-as-judge" test (§2.6) is a one-dimensional,
task-specific version of *precision*: what fraction of synthetic people land
where a real-trained detector expects people? The trend-agreement test in
doc 24 §7 (rank N detectors on real and synthetic footage and compute
Spearman ρ) is a *validity* check on the benchmark, not a distance. Both are
better aligned with the product question than FID is. **[derived]**

---

## 5. Image-statistics matching: SurvSim's approach, and why it is the right first tool

### 5.1 Idea

Deep-feature metrics tell you *that* sets differ, not *why*. For an imaging
chain, most differences come from a handful of physical quantities: noise
level, sharpness, contrast, colour, blockiness. Measure those directly on
both sets. Define the real distribution as a band (p10 to p90). Tune the
degradation profile until the synthetic median falls in band. Each miss
names a knob. This is the approach in `survsim/realism/stats.py` and
`docs/15_REALISM_STATS.md`.

### 5.2 The 14 statistics, and what physical cause each one isolates

From docs/15 (computed at 720 px height; blockiness at native resolution):

| stat | physical cause it isolates |
|---|---|
| `noise_sigma` (Immerkær residual on the flattest 50 % of pixels) | sensor shot + read noise after ISP denoise |
| `lap_var_log10` | overall sharpness: optics, defocus, ISP sharpening |
| `mtf_ratio` (spectral energy 0.25–0.5 / 0.05–0.25 cyc/px) | shape of the MTF; white noise inflates it |
| `edge_width` (10–90 % rise) | lens blur + demosaic + scaler |
| `luma_mean`, `rms_contrast`, `dynamic_range`, `luma_skew`, `hist_entropy` | exposure and tone curve (AE, WDR, gamma) |
| `chroma_mean`, `cast_a`, `cast_b` | white balance, saturation, illuminant colour |
| `blockiness` (8-px boundary / interior gradient) | DCT codec quantisation |
| `temporal_noise` | frame-to-frame noise surviving the codec's P/B prediction |

The real band comes from 80 frames (real CCTV plus MOT20). For example,
noise_sigma median is 0.309 (p10–p90 0.278–0.353), and blockiness median is
1.149 (1.111–1.197) (docs/15).


* A raw UE render has only **2/14** stats in band ("no noise, no blocks,
  bright/flat, no colour"). After tuning, `cctv_day_720p` reached 12/14 (was the tuning grid; realism is 6/14) on
  its tuning grid (this was the per-frame intra-codec era). After moving to a realistic GOP codec and
  retuning, the final table shows `cctv_day_720p` at **6/14**,
  `cctv_legacy_sd` at 9/14 and `cctv_night_ir` at 3/14 [vs day targets; vs real LLVIP night 3/13 vis · 2/13 thermal, raw renders luma 90 = not dark (69 §7)] on 60 frames of
  street-crowd content (docs/15).
* **White noise is the wrong noise.** Per-pixel independent noise put too
  much energy above 0.25 cyc/px (`mtf_ratio` 0.15 vs a real ≤ 0.033). Real
  CCTV noise is spatially correlated by demosaicing, ISP denoise and 4:2:0
  chroma subsampling, so `grain_sigma` (Gaussian-blurred, re-scaled noise) was
  added to `sensor_noise` (degrade.py). With it, `mtf_ratio` lands in band
  (0.0202).
* **The codec restructures the noise.** Switching `apply_sequence` from
  per-frame intra encoding to one GOP stream (libx264, P/B frames) made
  blockiness fall *out of* band (1.118 → 0.865), and `temporal_noise`
  collapse (2.20 → 0.53). P/B prediction copies the static background and
  averages away noise that is independent from frame to frame (docs/15).
  Adding enough correlated grain to survive the codec then overshoots
  temporal noise (5 to 10 vs a band of 1.57–2.93). The spatial/temporal
  tension is genuine and documented as an xfail.
* **Check the reference itself.** MOT sequences are distributed as per-frame
  JPEG stills. Part of the "real" temporal-noise band is therefore JPEG
  re-quantisation between independently compressed frames, not camera
  behaviour (docs/15). Clean-FID makes the same point about compression
  contaminating FID references [13]. A reference set must come in the same
  container as the product's input, which for CCTV means **H.264/H.265
  streams from the NVR, not stills**. **[derived]**

### 5.4 Limits of statistics matching

* **Marginals, not joints.** Matching 14 scalar medians does not match the
  joint distribution, and it says nothing about semantics. A frame of pure
  correctly-coloured noise could score well. Pair it with a semantic metric
  (detector-as-judge, KID on person crops).
* **The band is only as good as the reference.** 80 frames from a few
  sequences is a small reference. A band per camera *type* (day colour,
  IR night, legacy SD) is needed. docs/15 notes that no real IR reference
  exists yet, which is why night fails by design on chroma.
* **Content confound.** The same profile scores differently on different
  scenes (docs/15 notes a pytest fixture vs street-render difference). Match
  content class before comparing imaging statistics.

---

## 6. What a rendering pipeline needs for CCTV realism

Order these by how much they move a *detector*, not by how much they impress
a human. The list follows light from the scene to the stored bitstream.

### 6.1 Materials: physically based rendering (PBR)

UE's PBR material has four core inputs: **Base Color, Metallic, Roughness,
Specular** [19]:

* Base Color is "the color when photographed using a polarizing filter" (the
  albedo with no specular).
* Metallic should be treated as binary (0 or 1).
* Roughness goes from mirror (0) to matte (1).
* Specular defaults to 0.5, which is accurate for most materials. Do not set
  it to 0 [19].

The documentation gives measured albedos: non-metals range from charcoal 0.02
to fresh snow 0.81 [19].

**Why it matters for CCTV [derived].** Auto-exposure meters the scene. If
asphalt albedo is 0.4 instead of the documented 0.02 (fresh) to 0.08 (worn)
[19], the metered EV
darkens everything, people included. SurvSim hit exactly this: batch_v6 notes
"neutral-tinted PBR asphalt". Albedo errors become exposure errors, and
exposure errors become recall errors. The camera closes the loop.

### 6.2 Lighting: IBL/HDRI for day, practical lights for night

* **Day.** Image-based lighting from an HDR environment map gives the correct
  sky colour, soft ambient occlusion and a plausible dynamic range. Lighting
  was the largest single factor in Tremblay's ablation (−6.1 AP for a fixed
  light) [2]. So vary sun elevation and azimuth and sky state per sequence.
  docs/12 records a 25–60° elevation default and day at 40,000 lux,
  EV100 12.5.
* **Night.** This is the CCTV-defining condition, and it is almost entirely
  *artificial point lighting*: falloff, colour temperature and pools of light
  with dark gaps. SurvSim's history here is a good war story (docs/12,
  batches v2 to v6):
  * the first v2 night pass was black (no lamps in the yard layout, no metering);
  * then 78° 3400 K, 25,000 lm spots, whose frames "read amber and bright near
    lamps" (earlier notes used 15,000 lm 3400 K spots at EV100 1.5);
  * night v2: 4000 K, 9,000 lm, 30 m lamps, a blue-grey sky light and fog
    in-scattering.

  Real sites typically use roughly 3000–4000 K LED or legacy sodium around
  2000 K **[VERIFY]**. Randomise colour temperature across that range rather
  than fixing one value (structured DR on lighting). **[derived]**
* **IR.** Many CCTV cameras switch to 850 nm IR illumination with the IR-cut
  filter removed, which produces monochrome frames with a bright centre
  hotspot and fast falloff **[VERIFY]**. `degrade.ir_night` approximates this
  in 2D. A correct version needs per-material NIR reflectance: clothing dyes
  that look dark in visible light can look bright in NIR **[VERIFY]**.

### 6.3 Exposure: meter per camera, then simulate the camera's AE

UE offers Histogram (default, 64 bins), Basic and Manual exposure. EV100 is
defined as log2(N²/t · 100/ISO). When Min EV100 equals Max EV100, auto
exposure is disabled. Exposure compensation scales by 2^ExpComp.
Speed-up and speed-down control adaptation rate, in f-stops per second [18].

SurvSim's verified recipe (docs/12):

* `AEM_MANUAL` with physical-camera exposure off, and
  `auto_exposure_bias = −EV100`.
* **[X]**: a histogram mode with min = max was ignored in that build.
* A **3-frame probe render** meters luma. If it is outside 60–140, EV100
  moves by log2(measured/100), once.
* batch_v6 made this **per camera**: each CineCamera carries its own
  post-process exposure. That fixed the one gate failure in batch_v5
  (cam_sub looking into warehouse shade, 25.6 % crushed pixels). cam_sub is
  now metered to EV 12.98 against 13.5 global.

**Worked number [derived].** A probe luma of 43 gives a correction of
log2(43/100) = −1.22 EV. The EV100 goes *down* by 1.22 stops, so the image
gets 2^1.22 ≈ 2.3× brighter. That matches the docs/12 "plaza 43 → EV 11.8"
entry if the base was 13.0.

Then, in 2D, `degrade.auto_exposure` meters the *median* luma toward a target
(clamped ±`max_ev`), with a partial p1..p99 auto-levels stretch.
`camera_automatics` adds slow, seed-deterministic AE/AWB drift. Real CCTV
"breathes": exposure hunts when a bus fills the frame. Freezing it makes
every frame suspiciously stable. **Detector relevance [derived]:** a person
walking out of shade into sun under a lagging AE is briefly over-exposed.
That is a real miss mode, and only temporal AE produces it.

### 6.4 Sensor noise: Poisson-Gaussian, not additive Gaussian

Foi et al. model raw sensor data as a Poissonian photon-counting part plus a
Gaussian signal-independent part. The resulting per-pixel variance is
**affine in the signal** [16]:

$$z = y + \sigma(y)\,\xi,\qquad \sigma^2(y) = a\,y + b,\quad a = \chi^{-1}$$

Here χ is the photon-to-signal scale (quantum efficiency × gain), and b is
read and other stationary noise. The model also treats **clipping**
explicitly: over- and under-exposed data are non-linearly distorted in their
noise statistics [16].

Brooks et al. showed why this matters for learning. By *unprocessing* sRGB
images back to raw (invert tone curve, gamma, colour correction matrix and
white balance, then re-mosaic) and adding shot + read noise there, a learned
denoiser gets 14 to 38 % lower error than prior state of the art, and runs
9 to 18× faster [17]. **The lesson for simulators:** add noise in the *linear
raw* domain, then apply the ISP, *not* in display-referred sRGB.

**Worked numbers [derived].** Take a = 1/χ with χ = 1 e⁻/DN at high gain:

* A dark pixel at 5 DN has σ² = 5 + b. With b = 4, SNR = 5/3 ≈ 1.7.
* A bright pixel at 200 DN has σ² = 204, so SNR ≈ 14.

Additive Gaussian noise with a constant σ of 3 would give the dark pixel the
same absolute noise as the bright one. That is why "Gaussian noise looks
wrong at night".

In the repo, `degrade.sensor_noise` implements exactly this split: Poisson
shot noise on electrons = DN/iso_gain, plus read noise, plus column
fixed-pattern noise from a per-camera RNG (so it stays put across frames),
plus hot pixels. For pixels with λ ≥ 20 it uses the CLT Gaussian
approximation (a speed optimisation, verified not to move `noise_sigma`).
True Poisson sampling is kept where the skew is visible: dark and night
pixels. Its docstring says the same thing as Foi [16], in plain English.

**Gap [derived].** degrade.py adds noise in 8-bit display space after the
renderer's tone map, not in linear raw before a simulated ISP, which is
where Brooks [17] adds it. The ISP (`isp()` = denoise + sharpen) and the
codec then act on it. The error is largest in shadows, where the tone curve
is steepest. Moving noise before an explicit inverse tone map is the
principled fix.

### 6.5 Rolling shutter

CMOS rolling-shutter sensors expose and read rows sequentially, top to
bottom. A moving object is therefore sampled at slightly different times per
row. Typical artefacts are skewed verticals and bent fast-moving parts. Static
scenes are unaffected. Higher frame rate (faster readout) reduces the effect,
and exposure time does not change it [20].

**For CCTV [derived]:**

* Geometric skew is small for walking people (1.5 m/s) at 25 fps.
* It is large for a **slewing PTZ head**. SurvSim's camera director slews PTZ
  cameras, so frames captured mid-slew should shear.
* The more visible rolling artefact in CCTV is **flicker banding**: row-wise
  gain ripple where mains-powered lights (100/120 Hz) beat against the row
  readout. `degrade.rolling_exposure` models the banding (a slow sinusoidal
  row gain drifting down the frame). It does not model geometric shear.
* To add shear, re-render or warp each row with the camera pose at time
  t₀ + row · t_line. For a pure pan, that is a per-row horizontal shift of
  ω · f · t_row.

**Worked number [derived].** A 60°/s slew, f = 1000 px, 720 rows read over
about 30 ms gives a shift of (60·π/180)·1000·0.030 ≈ 31 px, top to bottom.
That is clearly visible.

### 6.6 Motion blur

Blur length ≈ image-plane speed × exposure time. **[derived] worked
number:** a person crossing at 1.5 m/s, 10 m away, f = 1000 px, moves
150 px/s. At 1/50 s exposure that is 3 px of blur. At night, with a 1/12 s
shutter (slow-shutter mode is common on CCTV **[VERIFY]**), it is 12.5 px.
That smears limbs, and it is one mechanism behind night recall loss that
noise alone does not explain.

`degrade.motion_blur(length, angle)` is a *global* linear kernel, which is
right for camera shake. For moving people it is wrong, because the
background should stay sharp. The correct approach is per-pixel velocity blur
from the renderer (UE's motion-blur post-process uses velocity buffers
**[VERIFY]**), with shutter time tied to the metered exposure.

### 6.7 Codec: H.264/H.265 artefacts are a *temporal* process

* **Per-frame artefacts.** 8×8 / 4×4 block transform quantisation (blocking),
  ringing at edges, colour bleeding from 4:2:0 chroma subsampling.
* **Temporal artefacts** exist only in a GOP stream:
  * **I-frame pumping**: a quality jump at every keyframe;
  * **smearing and trails**: motion vectors copy blocks, and residuals are
    under-coded at low bitrate;
  * **frozen background noise**: the static background is predicted rather
    than refreshed.
* **Rate control bias.** Encoders spend bits where content is complex. Dark,
  flat regions get coarse quantisation. `degrade.dark_flat_quantise` injects
  this explicitly, because a uniform CRF round trip does not reproduce it.
* **Worked number [derived].** CCTV NVRs often stream 1080p at a few Mbit/s
  **[VERIFY]**. At 4 Mbit/s, 25 fps and 1920×1080, that is 4×10⁶ /
  (25 · 2.07×10⁶) ≈ 0.077 bits per pixel. At that budget a 30 px-tall
  person's face and clothing texture is essentially gone, and ReID must
  rely on colour and shape.

SurvSim's `h264_sequence` encodes a whole sequence through one libx264
encode→decode pipe (GOP and B-frames configurable, yuv420p). That reproduces
the temporal structure, which the old per-frame intra round trip did not
(docs/15). **Gap:** there is no H.265 path. Many current NVRs default to
H.265 **[VERIFY]**, whose larger coding blocks (up to 64×64 CTUs **[VERIFY]**)
produce larger smooth patches than H.264. A second codec is cheap to add
through ffmpeg's libx265.

### 6.8 The rest of the chain, briefly

* **Lens.** Barrel distortion: now applied per camera via `lens.distort_image`,
  so the same coefficients drive pixels and GT (`barrel_distort` defaults to
  k1 = −0.18, and the `Profile`'s k1 = −0.16 is documented as no longer
  distorting anything), vignetting,
  lateral chromatic aberration, defocus. Wide CCTV lenses distort
  noticeably at the frame edge. GT boxes must go through the same
  distortion, which principle 2 in CLAUDE.md implies.
* **ISP.** Denoise, then sharpen (`isp()`). The halo from sharpening is part
  of the CCTV look and changes `edge_width`.
* **OSD.** The timestamp/camera-name overlay (`osd()`). Detectors trained
  without it sometimes fire on it. A cheap hard negative.
* **Lens dirt, haze.** Seeded per camera and static across a sequence.

### 6.9 Priority order for a detector [derived]

1. Person appearance at the target pixel height (MetaHuman vs CesiumMan:
   +18 recall points, docs/12).
2. Exposure and lighting per camera, especially night (docs/12 night recall
   deltas; Tremblay's lighting ablation [2]).
3. Resolution and codec at the real bitrate (small people vanish).
4. Signal-dependent noise (mainly night).
5. Motion blur tied to shutter (mainly night).
6. Lens, rolling shutter, OSD (second order for detection; first order for
   geometry, calibration and PTZ GT).

---

## 7. Putting it together: a measurement protocol for SurvSim releases

A release is "more realistic" only if all four of these move the right way,
at fixed N and on fixed reference sets. **[derived]**

| layer | metric | tool | why |
|---|---|---|---|
| imaging chain | 14-stat band, count in band, per profile | `python -m survsim.realism compare` | diagnosable; names the knob |
| global distribution | KID with bootstrap CI (and FID∞ if reported) | `survsim.eval.realism` | unbiased at small N [7][8] |
| people | KID / precision-recall on DINOv2 person crops, by height bin | to add | Inception blind to people [9][14] |
| task | yolov8n recall at matched heights; TSTR (doc 24 §7) | `tools/eval_recall.py` | what the product cares about |

What must *not* be done:

* Comparing FID across different N [8].
* Computing FID with N < 2048 (`FID_MIN_SAMPLES`).
* Using still-JPEG references for a video codec (docs/15 caveat, [13]).
* Declaring victory on image metrics without a task metric.

---


**"Domain randomisation or photorealism?"** Both, for different variables.
Tremblay et al. showed cartoonish randomised cars trained a detector as well
as a KITTI clone: 78.1 vs 79.7 AP for Faster R-CNN, and better for R-FCN and
SSD. Fine-tuning on 6K real images reached 98.5, above real-only. But plain
DR collapses on small objects: 24 AP on KITTI-Hard vs 52 for structured DR,
because small objects need context. And the object itself must be right. In
our simulator, swapping a stylised mannequin for MetaHumans lifted a
COCO-trained detector's recall from 0.58 to 0.76 on identical ground truth.
So: get the *signal* realistic, randomise the *nuisance* within a scene
grammar, and get the *imaging chain* right, because real CCTV is narrow and
systematic there.

**"How do you know your synthetic data is realistic?"** Four layers:

1. Low-level image statistics against a real band, because they name the
   knob: noise, MTF, blockiness, exposure.
2. KID rather than FID, because FID is biased with a model-dependent 1/N
   term. Bińkowski showed ranking flips even at 50K samples.
3. Precision and recall, because FID cannot tell "unrealistic" from "not
   diverse".
4. A task metric: a frozen real-trained detector's recall at matched
   pixel heights, and ultimately train-on-synthetic, test-on-real.

I'd also move off Inception features. Kynkäänniemi showed FID can be gamed
by matching ImageNet class histograms, and ImageNet has no CCTV pedestrian.

**"What makes a render look like CCTV?"** Walk the light path:

* PBR albedos, because auto-exposure couples them to everyone's brightness.
* Per-camera metered exposure and temporal AE drift.
* Poisson-Gaussian noise (variance = a·y + b), added before the ISP, and
  spatially correlated by demosaic and denoise.
* Rolling-shutter flicker, and shear under PTZ slew.
* Shutter-linked motion blur, which is 12 px at night for a walking person.
* A real GOP codec at the real bitrate. About 0.08 bits per pixel at
  4 Mbit/s 1080p deletes a 30 px person's texture.

We found white noise was the wrong noise (MTF 5× too high), and that moving
to a GOP codec restructured the noise statistics entirely. So the codec
belongs inside the realism loop, not bolted on afterwards.

**One-line summary.** "Randomise what the real world randomises, match what
the real camera fixes, and measure it with a metric that can tell you which
of the two you got wrong."

---

## References

All URLs fetched on 2026-09-26 while writing this document.

1. Tobin et al., *Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World*, IROS 2017. https://arxiv.org/abs/1703.06907. Used for: randomised non-realistic textures and lighting; 1.5 cm real-world accuracy; claimed first sim-only RGB transfer for robot control; the "just another variation" framing.
2. Tremblay et al., *Training Deep Networks with Synthetic Data: Bridging the Reality Gap by Domain Randomization*, CVPRW 2018. https://arxiv.org/abs/1804.06516 (PDF read). Used for: 100K images, 36 car models, 8K textures, flying distractors, camera ranges; Table 1 AP@0.5 VKITTI vs DR (79.7/78.1, 64.6/71.5, 36.1/46.3); fine-tuned 98.5 (+1.6 vs VKITTI, +2.1 vs real); ablation (baseline 73.7; fixed light 67.6; no texture 69.0; 4K textures 71.5; no augmentation 72.0; no light augmentation 73.6; no distractors 72.6); freezing vs full training (66.4 vs 78.1, 69.4 vs 71.5).
3. Prakash et al., *Structured Domain Randomization: Bridging the Reality Gap by Context-Aware Synthetic Data*, ICRA 2019. https://arxiv.org/abs/1810.10093 (PDF read). Used for: SDR method; Table I AP@0.7 on 7,500 KITTI images (VKITTI clones, VKITTI, Sim 200k, DR, SDR); saturation around 10K and 43.7 AP at 1K, DR saturating near 50K; Table III (DR 56.8/38.0/23.9, SDR 69.6/65.8/52.5, BDD100K 59.7/54.3/45.6); small objects need context.
4. Johnson-Roberson et al., *Driving in the Matrix*, ICRA 2017. https://arxiv.org/abs/1610.01983 and https://ar5iv.labs.arxiv.org/html/1610.01983. Used for: Sim 10k/50k/200k sizes; Sim 200k 0.6803/0.5257/0.4207 vs Cityscapes (2,975) 0.6247/0.4274/0.3566 on 7,481 KITTI images.
5. Hinterstoisser et al., *On Pre-Trained Image Features and Synthetic Images for Deep Learning*, 2017. https://arxiv.org/abs/1710.10710. Used for: freezing real-pretrained feature extractors and training only later layers on OpenGL renders works well.
6. Heusel et al., *GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium*, NeurIPS 2017. https://arxiv.org/abs/1706.08500. Used for: introduction of FID as a Wasserstein-2 distance between Gaussians fitted to Inception features (abstract; the ar5iv full text did not render).
7. Bińkowski et al., *Demystifying MMD GANs*, ICLR 2018. https://arxiv.org/abs/1801.01401 and https://ar5iv.labs.arxiv.org/html/1801.01401. Used for: KID kernel (x·y/d + 1)³; unbiased, asymptotically normal estimator; FID estimator biased; CIFAR n = 10,000 FID ≈ 8.1 still falling; ranking reversal even at n = 50,000.
8. Chong & Forsyth, *Effectively Unbiased FID and Inception Score and Where to Find Them*, CVPR 2020. https://arxiv.org/abs/1911.07023 (PDF and ar5iv). Used for: FID formula; E[FID_N] = FID∞ + K/N + O(1/N²) with model-dependent K; extrapolation from ≥5K subsets of a 50K pool; DCGAN ranking flip example (Fig. 3).
9. Kynkäänniemi et al., *The Role of ImageNet Classes in Fréchet Inception Distance*, ICLR 2023. https://arxiv.org/abs/2203.06026 and https://ar5iv.labs.arxiv.org/html/2203.06026. Used for: Top-1 matching −8.4 to 11.3 % FID (FFHQ −11.3 %); pre-logit resampling −42 to 72 %; Grad-CAM attends outside faces; FastGAN 5.28 vs StyleGAN2 5.30 FID with FID-CLIP 4.67 vs 2.76.
10. Kynkäänniemi et al., *Improved Precision and Recall Metric for Assessing Generative Models*, NeurIPS 2019. https://arxiv.org/abs/1904.06991 and https://ar5iv.labs.arxiv.org/html/1904.06991. Used for: the f(φ,Φ) definition; precision/recall formulas; k = 3; 50K samples; VGG-16 fc2 features; "low FID may indicate high precision, high recall, or anything in between".
11. Sajjadi et al., *Assessing Generative Models via Precision and Recall*, NeurIPS 2018. https://arxiv.org/abs/1806.00035. Used for: precision and recall for distributions, disentangling sample quality from coverage.
12. Naeem et al., *Reliable Fidelity and Diversity Metrics for Generative Models*, ICML 2020. https://arxiv.org/abs/2002.09797. Used for: k-NN P/R fails to detect identical distributions, is outlier-sensitive, and has arbitrary hyperparameters; density and coverage proposed (exact formulas tagged [VERIFY]).
13. Parmar et al., *On Aliased Resizing and Surprising Subtleties in GAN Evaluation* (Clean-FID), CVPR 2022. https://arxiv.org/abs/2104.11222. Used for: resize aliasing corrupts FID; JPEG-compressing generated images to match compressed references improves FID.
14. Stein et al., *Exposing Flaws of Generative Model Evaluation Metrics and Their Unfair Treatment of Diffusion Models*, NeurIPS 2023. https://arxiv.org/abs/2306.04675. Used for: no metric correlates strongly with human judgement; Inception-v3 over-reliance; DINOv2-ViT-L/14 recommended; 17 metrics, 9 encoders.
15. Caron et al., *Emerging Properties in Self-Supervised Vision Transformers* (DINO), ICCV 2021. https://arxiv.org/abs/2104.14294. Used for: self-supervised ViT features contain explicit semantic segmentation information.
16. Foi et al., *Practical Poissonian-Gaussian Noise Modeling and Fitting for Single-Image Raw-Data*, IEEE TIP 2008. https://webpages.tuni.fi/foi/papers/Foi-PoissonianGaussianClippedRaw-2007-IEEE_TIP.pdf (PDF read). Used for: Poissonian + Gaussian raw noise model; σ²(y) = a·y + b with a = χ⁻¹; explicit clipping treatment.
17. Brooks et al., *Unprocessing Images for Learned Raw Denoising*, CVPR 2019. https://arxiv.org/abs/1811.11127. Used for: inverting tone map, gamma, CCM and WB to raw; shot/read noise; 14–38 % lower error; 9–18× faster.
18. Epic Games, *Auto Exposure in Unreal Engine* (official docs). https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-exposure-in-unreal-engine. Used for: Histogram (64-bin), Basic and Manual modes; EV100 definition; min = max disables AE; 2^ExpComp; speed up/down in stops/s; physical camera exposure defaults.
19. Epic Games, *Physically Based Materials in Unreal Engine* (official docs). https://dev.epicgames.com/documentation/en-us/unreal-engine/physically-based-materials-in-unreal-engine. Used for: Base Color / Metallic / Roughness / Specular semantics; metallic binary; specular 0.5 default; albedos charcoal 0.02 to fresh snow 0.81, fresh asphalt 0.02, worn asphalt 0.08.
20. Basler AG, *CMOS Rolling Shutter Cameras* (manufacturer technical note). https://www.baslerweb.com/en/learning/cmos-rolling-shutter-cameras/. Used for: sequential line exposure; typical artefacts; static scenes unaffected; higher frame rate reduces the effect and exposure time does not.

Repository sources: `docs/12_UNREALCV_ENGINE_NOTES.md` (exposure recipe,
metering, night lighting v1 to v2, batch_v3–v6 recall tables, MetaHuman vs
CesiumMan); `docs/15_REALISM_STATS.md` (14 stats, real band, profile tuning,
GOP codec findings, JPEG reference caveat); `survsim/sensors/degrade.py`
(`sensor_noise`, `auto_exposure`, `camera_automatics`, `rolling_exposure`,
`dark_flat_quantise`, `h264_sequence`, `Profile`); `survsim/eval/realism.py`
(`FID_MIN_SAMPLES`, `_trace_sqrt_product`); `docs/research/24_SYNTHETIC_TO_REAL_EVIDENCE.md` §7.
