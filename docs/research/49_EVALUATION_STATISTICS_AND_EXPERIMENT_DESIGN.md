# 49 — Evaluation statistics and experiment design for SurvSim

us, before the next GPU-week. Every worked number below comes from
`docs/13_BASELINES.md` or `23_ROADMAP_AND_GAP_ANALYSIS.md`; every formula is
tagged with a fetched source or **[INF]** (our arithmetic). Nothing here was
run on the GPU; all computations are closed-form and reproducible by hand.

Tags: **[V]** fetched/verified 2026-09-26, **[INF]** derived here,
(**[NF]** tags from the first draft were all replaced by fetched DOI
metadata on 2026-09-26 — Crossref API records, see References; see
`AUDIT_48-51.md`.)

---

## 0. A worked example of why every ratio needs its inputs: the VLM gating ratio

Three documents disagreed about how much cheaper trigger-gated VLM
verification is than always-on:

| where | claim | inputs actually used |
|---|---|---|
| 19 §3.5 | 50–150× | gated = 1 % of 10-s clips × 2k tokens = **7.2k tokens/cam-h** (input only); always-on 0.36M / 1.1M tokens/cam-h |
| 45 §5.3, AUDIT_43-47, index fact 9, 48 C5 | 170–400× | gated = **20 triggers/camera-day** × (8 × 258 + 300 = 2,364 input + 150 output) ≈ 1,970 input tokens/cam-h; ratio taken in **dollars**, output tokens included on both sides |

Recomputation **[INF]**:

* Token ratio, 19's gating: 360,000 / 7,200 = **50×**; 1,080,000 / 7,200 =
  **150×**; 4.6M / 7,200 = **639×**.
* Dollar ratio, 45's gating: Flash $112 / $0.66 = **170×**, $240 / $0.66 =
  **364×**; Flash-Lite $31 / $0.18 = **172×**, $74 / $0.18 = **411×** — hence
  "170–400×".
* Token ratio, 45's gating (input only): 360,000 / 1,970 = 183×;
  1,080,000 / 1,970 = 548×.

So nobody's arithmetic is wrong. The two gating scenarios differ by a factor
of ~3.7 in trigger volume (19: 36 clips/cam-h at 1 %; 45: 0.83 triggers/cam-h),
and 45 additionally prices output tokens, which weigh more in the gated case
(150 output tokens at $2.50/M are half of Flash's gated bill). The audit
confirmed 45's scenario inputs and corrected its ratio, but its one-line
summary ("gating is ~170–400× cheaper") dropped the trigger rate, and 48 C5
then pasted that ratio next to 19's 7.2k figure — a sentence whose two halves
come from different models. This is the evaluation-engineer lesson in
miniature: *a ratio without its numerator and denominator is not a result.*
19 now says both; fact 9 and 48 C5 should quote the trigger rate with the
ratio.

---

## 1. Confidence intervals for AP and recall

### 1.1 What the sampling unit is

AP is a function of the whole ranked detection list, so it has no closed-form
standard error; the standard tool is the **nonparametric bootstrap** (Efron
1979, *Ann. Statist.* 7(1), doi:10.1214/aos/1176344552 **[V]**): resample the evaluation units with replacement, recompute AP,
take the 2.5/97.5 percentiles (or BCa). The only real decision is *what the

* **Bootstrap over images** treats frames as independent. In video they are
  not: MOT20-02's consecutive frames share the same people, pose, lighting
  and occluders. An image bootstrap on 2,782 frames behaves as if there were
  2,782 independent tests when the effective sample size is closer to the
  number of distinct *(person, visibility episode)* pairs. The resulting CI is
  too narrow — often by several times **[INF]**.
* **Bootstrap over sequences (or cameras/sites)** respects the dependence but
  with MOT20's four training sequences gives a CI built from four units — so
  wide it is almost uninformative, and honest.
* **Block (moving-block) bootstrap over contiguous frame windows** is the
  compromise for a single long sequence: blocks longer than the typical track
  duration (≥ 10–30 s at 25 fps) keep within-block correlation intact **[V: Künsch
  1989, *Ann. Statist.* 17(3), doi:10.1214/aos/1176347265]**. This is what we should use for H1-style single-sequence
  evaluation.

Rule for SurvSim reports: **the resampling unit is the unit you would
generalise over.** Claims about "a new camera" resample cameras; claims about
"more frames from this camera" can resample blocks of frames. Never frames.

### 1.2 Why per-camera recall on 10 frames is ±0.1 (at best)

Recall of a detector on a small check (e.g. a per-camera sanity gate over 10
frames with ~one hero agent each) is a binomial proportion. Its standard error
is sqrt(p(1−p)/n) **[INF]**:

| true recall p | n = 10 | n = 50 | n = 400 |
|---|---|---|---|
| 0.5 | 0.158 | 0.071 | 0.025 |
| 0.8 | 0.126 | 0.057 | 0.020 |
| 0.9 | 0.095 | 0.042 | 0.015 |

So on 10 frames *one standard error* is ≈ 0.1–0.16, and the 95 % Wilson
interval for 8/10 is ≈ [0.49, 0.94] **[INF, recomputed: 0.490–0.943; Wilson 1927,
*JASA* 22(158):209–212, doi:10.1080/01621459.1927.10502953 [V]]**; the exact
Clopper–Pearson interval is wider, [0.44, 0.97]. And the 10
frames of one camera are correlated, so the effective n is smaller still. A
per-camera recall on 10 frames can distinguish "works" from "blind"; it cannot
rank two cameras or two models. H5 is the alarm-level version of the same
problem: 5 truth loiter events means **one event moves recall by 0.2**, which
32 says in its caveat.

Use the **Wilson or Clopper–Pearson** interval, not the normal ("Wald")
interval, for any proportion with n < ~100 or p near 0/1 — Wald gives
impossible intervals like [0.94, 1.06] for 9/10.

### 1.3 AP-specific cautions

* AP depends on matching, ignore regions and IoU threshold: bootstrap the
  *whole* pipeline (matching inside each resample), not a fixed matched list.
* AP at small n per size band is unstable: H3's far band has **15 GT boxes**,
  so its recall has SE ≈ 0.13 **[INF]**; report it as "effectively blind",
  as 32 does, not as a number to two decimals.

---

## 2. Seed variance and how many seeds you need

### 2.1 What H1 measured

Training-seed spread on MOT20-02 @ 640 (32, H1; 3 seeds, sample sd):

| arm | mean AP | sd | per-seed |
|---|---|---|---|
| synthetic | 0.152 | 0.025 | 0.142, 0.180, 0.134 |
| synth + real60 | 0.472 | 0.005 | 0.473, 0.477, 0.467 |
| real60 only | 0.491 | 0.003 | 0.494, 0.489, 0.489 |

Two lessons. (1) **Variance is arm-dependent** — synthetic-only is 5–8× noisier
than arms anchored by real data, because it is being pushed off the COCO
optimum and where it lands depends on the seed. Never borrow one arm's sd for
another. (2) With 3 seeds the sd estimate itself is poor: a 95 % CI for σ from
n = 3 spans roughly 0.5σ̂ to 6.3σ̂ (χ² with 2 df) **[INF]** — the "0.025" could
plausibly be 0.013 or 0.16.

The 95 % t-interval for synthetic mean AP is 0.152 ± 4.30 × 0.025/√3 =
**[0.090, 0.214]** **[INF]** — it excludes zero-shot 0.276 comfortably, which is
why "synthetic hurts" survives 3 seeds, while the magnitude does not (the

### 2.2 Seeds needed to detect a difference

For two independent arms with common sd σ, to detect a difference Δ at
two-sided α = 0.05 with power 0.8, n per arm ≈ 2(z₀.₉₇₅ + z₀.₈)² σ²/Δ² =
15.7 σ²/Δ² **[INF, standard normal-approximation power formula, Cohen, *Statistical Power Analysis
for the Behavioral Sciences*, 2nd ed. 1988, Routledge reissue
doi:10.4324/9780203771587 [V]; 2(1.960+0.842)² = 15.70 recomputed]**:

| σ (from H1) | Δ = 0.02 AP | Δ = 0.05 AP | Δ = 0.10 AP |
|---|---|---|---|
| 0.025 (synthetic) | **25 seeds/arm** | 4 | 1 → use ≥ 3 |
| 0.005 (synth+real) | 1 → use ≥ 3 | ≥ 3 | ≥ 3 |
| 0.003 (real only) | ≥ 3 | ≥ 3 | ≥ 3 |

(For small n add ~2 seeds for the t-distribution penalty.) Two consequences
for SurvSim: a claim that tight GT boxes improve synthetic-only AP by 0.02 is
**not testable** at our budget (25 seeds × 2 arms × ~5 min ≈ 4 GPU-hours is
fine on paper, but the H1 synthetic arm took 297 s alone and is ~2× slower
beside the editor); a claim of ≥ 0.05 is testable with 4–5 seeds. The
synth+real vs real-only difference (0.019) was detectable with 3 seeds only
because both arms are quiet.

### 2.3 Exact small-n reasoning

With 3 seeds per arm, "every synth+real seed below every real-only seed" is a
permutation event with probability 1/C(6,3) = **1/20 = 0.05** one-sided under
the null of exchangeability **[INF]**. That is the *smallest* p a 3-vs-3 rank
test can ever produce — so the claim is right at the edge, and saying so is

### 2.4 Bouthillier et al. on sources of variance

Bouthillier et al. (2021) show that benchmark conclusions are sensitive to
data sampling, initialisation and hyperparameter choice, and that
**randomising more sources of variation** (data order, splits, init together)
gives a better estimator of the true expected performance than repeating only
the seed, at a fraction of the compute ("51 times reduction in compute cost")
**[V: arXiv 2103.03098]**. For SurvSim the extra sources are cheap and
meaningful: re-sample *which* synthetic frames (the every-8th offset) and
*which* scenarios, not just the training seed. Our current 3 seeds measure
only init/order noise and therefore **understate** the variance a customer
would see from a different render batch.

---

## 3. Paired vs unpaired comparisons

**Paired** means the two arms share the source of noise you want to cancel.
In detection that is usually the *test images*: evaluate model A and model B
on the same frames and analyse per-image (or per-block) differences. The
image-level difficulty that dominates variance cancels, so the paired SE is
much smaller than the unpaired SE.

For **seeds**, pairing only helps if the seed controls something shared
(same data order, same init for the shared backbone). H1 per-seed differences
synth+real − real: −0.021, −0.012, −0.022; mean −0.018, sd 0.0055, paired
t = −5.8 on 2 df, p ≈ 0.03 **[INF]**. Welch unpaired: t ≈ 5.5, ~3.2 df,
p ≈ 0.010 **[INF, recomputed with scipy; was 5.6 / 3.3]**. Pairing did *not* help, which is itself informative: seed
noise in the two arms is uncorrelated (different data streams), so "seed 0"
in arm A and "seed 0" in arm B are not a meaningful pair. Pair on test
images, not on seed labels.

Practical recipe for a SurvSim A/B:
1. Same test set, same matcher, same ignore regions for both arms.
2. Paired block bootstrap over test blocks for *evaluation* noise.
3. Seeds (≥ 3, more if σ is large) for *training* noise.
4. Report both components; the total CI combines them (nested resampling or
   the variance sum).

---

## 4. Multiple-comparison control across arms

H1 has 4 arms and 2 eval resolutions; H6 has freeze levels × diagnostics;
32 reports 8+ per-band AP50s per arm. Test enough cells and something is
"significant". Controls:

* **Holm–Bonferroni** for a small family of pre-registered contrasts: sort
  p-values, compare the k-th smallest to α/(m−k+1), stop at the first failure;
  controls family-wise error and is uniformly more powerful than Bonferroni
  **[V: Holm 1979, Scand. J. Statist. 6(2):65–70]**.
* **Benjamini–Hochberg FDR** for exploratory sweeps (degrade-profile grids,
  per-band breakdowns) where a false lead costs one follow-up run, not a
  shipped claim **[V: Benjamini & Hochberg 1995, *JRSS-B*
57(1):289–300, doi:10.1111/j.2517-6161.1995.tb02031.x]**.
* For **many models across many datasets/sites**, Demšar recommends
  non-parametric tests — Wilcoxon signed-ranks for two classifiers, Friedman
  with post-hoc tests and critical-difference diagrams for several
  **[V: Demšar 2006, JMLR 7]**.

SurvSim policy: each experiment names **one primary contrast** in its
pre-registration (§10); everything else (per-band, 1280 px, AP75) is labelled
*secondary/exploratory* and not claimed without a follow-up run. H1's 80–120 px
"improvement" (0.448 vs 0.419, seed 0 only) is precisely such an
exploratory cell and 48 A2 is right to present it as a single-seed curiosity.

---

## 5. Zero-false-alarm soak tests: rule of three and Poisson bounds

False alarms per camera-hour are counts over exposure; model them as Poisson
with rate λ. If a soak of T camera-hours produces **zero** false alarms, the
95 % upper bound on λ is −ln(0.05)/T ≈ **3/T** — the rule of three
**[V: Hanley & Lippman-Hand 1983, JAMA 249(13):1743–5; general form −ln(α)/n]**.
With k > 0 events, use the exact (Garwood) interval: upper = χ²₀.₉₇₅(2k+2)/2T,
lower = χ²₀.₀₂₅(2k)/2T **[V: Garwood 1936, "Fiducial limits for the Poisson
distribution", *Biometrika* 28(3–4):437–442, doi:10.1093/biomet/28.3-4.437]**.

Worked with SurvSim's numbers **[INF]**:

| soak (camera-h) | 0 FAs ⇒ 95 % upper bound | against assumed 0.001 FA/cam-h budget (H5) |
|---|---|---|
| 0.35 (H5) | 8.6 FA/cam-h | useless |
| 30 (48 C2) | 0.10 | 100× our assumed budget |
| **400** (23 §acceptance, "≥ 400 camera-hours per behaviour type") | **0.0075** | 7.5× our assumed budget |
| 3,000 | 0.001 (assumed, 28 §6) | just demonstrates the budget |
| 3,000 with 1 FA | 0.0019 (Garwood) | fails |

So the roadmap's **400 camera-hours** per behaviour type bounds FA/cam-h to
< 0.0075 if clean — enough to *reject* a rule that is 10⁴× over our assumed budget (H5's
11–143 FA/cam-h would produce thousands of alarms), **not** enough to *certify*
the assumed 0.001 budget. Certification needs ~3,000 clean camera-hours (≈ 125
camera-days; a 40-camera site does it in ~3 days of real soak). That is
the right division of labour: mock-world volume to kill bad rules cheaply,
on-site soak to sign off.

real false alarms cluster (a flapping tree, a night of rain), so bound
per-*incident* or use an overdispersed (negative-binomial) model; (b)
mock-world hours count only if mock trajectories are validated (23's
acceptance item 1), otherwise 400 mock hours bound the wrong process;
(c) the bound is per behaviour type *and* per condition — 400 day-hours say
nothing about night.

---

## 6. Power analysis for a 0.02 AP difference

§2.2 gave the training-seed side. The evaluation-set side: what test size
lets a *fixed pair* of models be told apart at Δ = 0.02 AP?

AP's evaluation SE shrinks roughly as 1/√(effective units). If a paired
block bootstrap on MOT20-02 gives a paired-difference SE of s_d, the
required ratio is Δ/s_d ≥ 2.8 for 80 % power at α = 0.05 **[INF]**. So Δ =
0.02 needs s_d ≤ 0.007. We have not yet measured s_d; it is the first number
to compute (cheap: resampling predictions already on disk, no GPU). If it
comes back at, say, 0.015, the test set must be ~4.6× larger in effective
units — i.e. more *sequences/sites*, since more frames of the same scene add
little.

Combined, detecting 0.02 AP between two *training recipes* needs both:
enough seeds that σ_seed·√(2/n) ≤ ~0.007, and a test set with s_d ≤ ~0.007;
the variances add. For synthetic-only arms (σ = 0.025) that is ~25 seeds —
the honest statement is "we can detect ≥ 0.05; 0.02 is below our resolution
for synthetic-only training."

---

## 7. McNemar for per-frame (per-object) detection

When the outcome is binary per item — "was this GT person detected at IoU ≥
0.5 and conf ≥ τ?" — two models on the same items form a paired 2 × 2 table.
McNemar's test uses only the discordant cells: χ² = (b − c)²/(b + c), with an
exact binomial test when b + c < 25 **[V: McNemar 1947; Wikipedia summary]**.

Use it for recall at a fixed operating point (H3's tiling vs 1280 px on the
same 3,087 small GT boxes is a textbook case). Two caveats:
* Items must be independent-ish: per-object detections within one frame and
  across adjacent frames are correlated, so McNemar's p is optimistic in
  video. Cluster it: compute b and c per block and bootstrap, or use a
  clustered McNemar variant.
* McNemar tests *recall at τ*, not AP. Two models can tie on AP and differ
  significantly at the operating threshold — which is the one that matters for
  alarms. Report both.

---

## 8. Cross-validation leakage: the MOT20-01/02 problem

Leakage is any path by which the test set informs training. In video the
common path is **site**: frames from the same camera share background, people,
lighting and compression, so a random frame split is near-duplicate leakage,
and even a sequence split leaks if two sequences film the same place.

MOT20's paper describes 8 sequences of very crowded scenes **[V: Dendorfer
et al. 2020, arXiv 2003.09003]**; it does not state that train sequences share
locations, but MOT20-01 and MOT20-02 visibly show the same square from a
similar viewpoint (32 H1 caveat; our observation, not a published fact). So:

* H1's "60 real frames from MOT20-01, scored on MOT20-02" is **near-in-domain
  adaptation**, an optimistic proxy for "60 frames from a new customer site".
  The 0.276 → 0.491 jump would likely be smaller on a genuinely new site.
* The mot20_sub set (01+02) is correctly reserved for arms that never saw
  MOT20 frames.
* SurvSim's own splits must be **by scenario/world and by camera**, never by
  frame: H1 held out `smoke_mock` as synthetic val — right in spirit, but the
  same cast and assets appear in train, so it measures in-distribution
  generalisation only.

Group-aware CV (leave-one-site-out, `GroupKFold` by site id) is the
A2 follow-up) — hold out a different, licence-clean dataset — is leave-one-
site-out with k = 1.

---

## 9. Calibration and alarm thresholds

A detector's confidence is **calibrated** if, among boxes scored 0.7, ~70 %
are true positives. Modern networks are often over-confident; depth, width,
weight decay and batch-norm all affect calibration, and single-parameter
**temperature scaling** fixes much of it post hoc **[V: Guo et al. 2017,
ICML, arXiv 1706.04599]**. It is assessed with a **reliability diagram**
(accuracy vs confidence per bin) and summarised by **ECE**, the bin-weighted
mean |accuracy − confidence|. ECE has known flaws — bin-count sensitivity,
bias; Nixon et al. recommend adaptive (equal-mass) binning, class-conditional
evaluation and L2 variants, and show that the choice of calibration metric
changes which recalibration method looks best **[V: Nixon et al. 2019,
arXiv 1904.01685]**.

Why a surveillance evaluation engineer cares:
* **Alarm thresholds are set in confidence units.** If the site calibration
  differs from the lab (new camera, night, rain), the same τ gives a
  different FA/cam-h. A calibrated score lets τ be set from a desired
  precision; an uncalibrated one must be re-tuned per site by soak.
* **Calibration drifts with domain.** H1's synthetic-trained detector's
  precision at conf 0.25 fell from 0.909 to 0.836 while recall fell too — the
  confidence meant something different. Measure ECE on the *target* domain;
  sim-domain calibration transfers no better than sim-domain AP.
* **Fusion needs probabilities.** Multi-sensor fusion (RF, audio, EO) combines
  scores; uncalibrated inputs let the most over-confident sensor dominate.

For detection, calibration is conditional on matching (a box is "correct" if
matched at IoU ≥ 0.5); state the IoU rule with the ECE.

---

## 10. Non-stationarity and drift

A camera's input is not stationary: daylight, season, foliage, construction,
lens dirt, re-aiming (SurvSim models 6 tamper kinds precisely because this
happens). Evaluation implications:

* **FA/cam-h is not one number.** Report it stratified by time-of-day and
  weather; a 400-hour day soak bounds day only.
* **Detecting drift online.** CUSUM — cumulative sums of deviations from a
  reference mean, with an alarm when the sum exceeds a threshold — detects
  small persistent shifts and is characterised by its average run length
  **[V: Page 1954, Biometrika 41:100–115; Wikipedia]**. Apply it to cheap
  label-free signals: detections per hour, mean confidence, image statistics
  (the docs/15 sharpness/noise/contrast set), alarm rate.
* **Testing a trend across ordered conditions** (e.g. AP across degrade
  severity levels) is a one-sided ordered-alternative problem; Page's trend
  test (or Jonckheere) is more powerful than an unordered Friedman/ANOVA
  **[V: Page 1963, "Ordered Hypotheses for Multiple Treatments",
  *JASA* 58(301):216–230, doi:10.1080/01621459.1963.10500843]**.
* **Distribution-shift tests on inputs**: two-sample tests on image-stat
  vectors (per-feature KS with FDR, or MMD) flag when the live camera leaves
  the region where the model was validated.

The n = 4 image-stats result (48 B-round: mean |z| orders AP across four
points) is a drift-proxy hypothesis, not a finding: 4 points, two eval sets,
and the best point *is* real data. With n = 4, a perfect rank order has
Spearman ρ = 1 at one-sided p = 1/4! = 0.042 — "significant" at 0.05 by one
permutation, and confounded. The proper test (48 B-round) varies the degrade
profile continuously on fixed content and fits AP against |z|.

---

## 11. The shared-GPU confound

H6 ran beside an idle Unreal editor (~3 GB resident). AP is deterministic
given seed and data, so AP is unaffected; **wall-clock is not**, and one
freeze22 seed timed out at 30 min — a lost seed is a *missing-not-at-random*
datum if the timeout correlates with the arm (heavier arms time out more).
Rules: log the environment block (already in every results.json), never
compare latency across runs with different co-tenants, stop the editor for
training runs, and treat timeouts as failed runs to be re-run, not dropped.

---

## 12. Pre-registration template for SurvSim experiments

Write this *before* the run, commit it, and quote the commit hash in the
results. It is short on purpose.

```
id:            hN_<slug>
commit:        <hash of this file before the run>
hypothesis:    one falsifiable sentence, direction stated
primary metric: one metric, one eval set, one resolution, one checkpoint rule
arms:          list; the control arm named
held fixed:    data, epochs, imgsz, batch, matcher, ignore regions, eval set
seeds:         N per arm, and which randomness each seed controls
sample size:   justification (σ from prior run, Δ of interest, §2.2)
analysis:      test (paired bootstrap / Welch / permutation / McNemar),
               α, multiplicity control (Holm over the named contrasts)
success:       numeric criterion on the primary metric
stopping rule: fixed N — no peeking; or a pre-declared sequential rule
secondary:     exploratory metrics, labelled as such, no claims
confounds:     known ones and how they are controlled
abandon if:    the outcome that kills the idea
```

### 12.1 Retroactive: H1 (as it should have been written)

```
id:            h1_sim2real
hypothesis:    fine-tuning YOLOv8n on batch_v6 synthetic changes MOT20-02 AP
               (two-sided); synth+real60 > real60 (one-sided)
primary metric: COCO AP, MOT20-02, imgsz 640, last.pt (no checkpoint
               selection on real)
arms:          zero_shot (control), synthetic, real60_only, synth_plus_real60
held fixed:    12 epochs, batch 8, 1258 synthetic images, docs/13 harness
seeds:         3 per trained arm (training seed = init + order)
sample size:   3 — pilot; resolves Δ ≥ 0.05 only if σ ≤ 0.01 (unknown a priori)
analysis:      contrast A: synthetic vs zero_shot (t-interval, 3 seeds);
               contrast B: synth+real vs real (3-vs-3 permutation, one-sided);
               Holm over {A, B}
success:       A: CI excludes 0.276; B: permutation p ≤ 0.05 in the + direction
stopping rule: fixed 3 seeds
secondary:     AP50/AP75, per-height bands, imgsz 1280, mot20_sub
confounds:     MOT20-01/02 same site (real60 is near-in-domain);
               one detector size; batch_v6 cast
```

Outcome under this plan: A holds (CI [0.090, 0.214] excludes 0.276; synthetic
*hurts*). B is **rejected in the opposite direction**: every synth+real seed is
below every real-only seed, permutation p = 0.05 one-sided *for a loss*,
which after Holm (second-smallest p compared to α/1 = 0.05) is borderline.
The honest summary is exactly 32's: direction robust, magnitude not.

### 12.2 Prospective: the tight-GT rerun (48 B5)

```
id:            h7_tight_gt
commit:        <to fill>
hypothesis:    replacing loose boxes with mask-derived tight boxes
               (head-top check; survsim/gt/mask_boxes.py) raises
               synthetic-only MOT20-02 AP75, and AP toward zero-shot
primary metric: AP75, MOT20-02 @640, last.pt
arms:          (0) v6 loose, (1) v6 tight   ← primary contrast (1)−(0)
               (2) v7 loose (cast control), (3) v7 tight
               secondary recipes: freeze10, synth-pretrain→real60
held fixed:    1258 images (same frame indices), 12 epochs, batch 8, imgsz 640
seeds:         5 per primary arm; resample the frame offset per seed
               (Bouthillier: vary data sampling, not only init)
sample size:   σ ≈ 0.025 AP (H1 synthetic); AP75 σ assumed ≤ 0.03;
               5 seeds resolves Δ ≈ 0.045 at 80 % power — claim only ≥ 0.05
analysis:      primary: Welch t on (1)−(0) + paired block bootstrap on the
               test set for eval noise; secondary contrasts Holm-corrected
success:       AP75(1) − AP75(0) ≥ 0.05 with 95 % CI excluding 0;
               stretch: synth+real60 > 0.491 on every seed
stopping rule: fixed 5 seeds; Unreal editor stopped; timeouts re-run
confounds:     cast change v6→v7 isolated by arms (0) vs (2);
               box-tightness gate (survsim/checks/box_tightness.py) must pass
               on the tight labels before training
abandon if:    AP75 moves < 0.02 with CI including 0 ⇒ labels were not the
               driver; next is degrade tuned against transfer
```

This plan fixes three weaknesses of H1: variance from data sampling is
included, the cast confound is controlled by a factorial arm, and the claim
threshold (0.05) matches the resolution the seed count can deliver.

---


**Q1. You report AP 0.152 ± 0.025. What is ± here and what is it not?**
Sample sd over 3 training seeds; it is training noise only, not
evaluation-set noise, not data-sampling noise. The 95 % CI on the mean is
[0.090, 0.214] with t on 2 df. It supports "worse than 0.276", not "0.15".

**Q2. How would you put a CI on AP for one video?**
Block bootstrap over contiguous windows longer than typical track lifetime,
recomputing matching per resample. Never an image bootstrap on video —
correlated frames make the CI far too narrow. For generalisation claims,
resample sequences/sites and accept wide CIs.

**Q3. How many seeds to detect a 0.02 AP gain?**
n ≈ 15.7σ²/Δ² per arm. With our synthetic σ = 0.025, ~25 per arm; with
real-anchored arms (σ ≈ 0.004), 3 suffice. So the answer depends on the arm,
and I'd pilot 3 seeds to estimate σ before committing.

**Q4. Your soak showed zero false alarms in 400 camera-hours. Is the system
under 0.001 (assumed, 28 §6) FA/cam-h?**
No. Rule of three: the 95 % upper bound is 3/400 = 0.0075, 7.5× our assumed budget.
Showing 0.001 needs ~3,000 clean camera-hours, stratified by condition, and
alarms cluster so I'd bound incidents, not raw alarms.

**Q5. Two detectors, same AP. Is there a difference that matters?**
Possibly at the operating threshold. McNemar on per-object hit/miss at the
alarm τ, clustered by block; plus calibration, since the threshold is set in
confidence units and an uncalibrated model shifts FA/cam-h per site.

**Q6. You trained on MOT20-01 and tested on MOT20-02. What's wrong?**
They appear to be the same square — site leakage. It measures near-in-domain
adaptation; a new site would likely see a smaller gain. Split by site
(leave-one-site-out) or hold out a different licence-clean dataset.

**Q7. You tested 12 per-band AP50s and one improved. Claim?**
No — exploratory cell, one seed, multiplicity. One primary contrast per
experiment, Holm over named secondaries, BH for sweeps; the 80–120 px
improvement gets a follow-up run, not a slide.

**Q8. Your deployed FA rate doubled in November. Model regression?**
Check non-stationarity first: stratify by time of day and weather, run CUSUM
on label-free signals (detections/h, mean confidence, image statistics) to
date the change, check for a camera re-aim/tamper. Then compare calibration
on recent labelled alarms; recalibrate (temperature) before retraining.

---

## References

Fetched 2026-09-26 **[V]**:
1. Hanley, J. A., Lippman-Hand, A. (1983). "If nothing goes wrong, is
   everything alright?" *JAMA* 249(13):1743–5 — via
   https://en.wikipedia.org/wiki/Rule_of_three_(statistics)
2. Guo, C., Pleiss, G., Sun, Y., Weinberger, K. Q. (2017). "On Calibration of
   Modern Neural Networks." ICML — https://arxiv.org/abs/1706.04599
3. Nixon, J. et al. (2019). "Measuring Calibration in Deep Learning." —
   https://arxiv.org/abs/1904.01685
4. Bouthillier, X. et al. (2021). "Accounting for Variance in Machine Learning
   Benchmarks." — https://arxiv.org/abs/2103.03098
5. McNemar, Q. (1947) — test statistic and exact small-sample rule via
   https://en.wikipedia.org/wiki/McNemar%27s_test
6. Holm, S. (1979). "A simple sequentially rejective multiple test
   procedure." *Scand. J. Statist.* 6(2):65–70 — via
   https://en.wikipedia.org/wiki/Holm%E2%80%93Bonferroni_method
7. Demšar, J. (2006). "Statistical Comparisons of Classifiers over Multiple
   Data Sets." *JMLR* 7 — https://jmlr.org/papers/v7/demsar06a.html
8. Dendorfer, P. et al. (2020). "MOT20: A benchmark for multi object tracking
   in crowded scenes." — https://arxiv.org/abs/2003.09003
9. Page, E. S. (1954). "Continuous Inspection Schemes." *Biometrika*
   41(1/2):100–115 — via https://en.wikipedia.org/wiki/CUSUM
10. Page's trend test — https://en.wikipedia.org/wiki/Page%27s_trend_test

Fetched as DOI metadata (Crossref API `api.crossref.org/works/<doi>`,
2026-09-26; publisher landing pages are Cloudflare-gated to `curl`) **[V]**:
11. Efron, B. (1979). "Bootstrap Methods: Another Look at the Jackknife."
    *Ann. Statist.* 7(1). doi:10.1214/aos/1176344552
12. Künsch, H. R. (1989). "The Jackknife and the Bootstrap for General
    Stationary Observations." *Ann. Statist.* 17(3). doi:10.1214/aos/1176347265
13. Wilson, E. B. (1927). "Probable Inference, the Law of Succession, and
    Statistical Inference." *JASA* 22(158):209–212.
    doi:10.1080/01621459.1927.10502953
14. Garwood, F. (1936). "Fiducial Limits for the Poisson Distribution."
    *Biometrika* 28(3–4):437–442. doi:10.1093/biomet/28.3-4.437
15. Cohen, J. (1988). *Statistical Power Analysis for the Behavioral
    Sciences*, 2nd ed.; Routledge 2013 reissue doi:10.4324/9780203771587
16. Benjamini, Y., Hochberg, Y. (1995). "Controlling the False Discovery
    Rate: A Practical and Powerful Approach to Multiple Testing." *JRSS-B*
    57(1):289–300. doi:10.1111/j.2517-6161.1995.tb02031.x

Internal: 32 (H1–H6), 45 §5.2–5.3, 48 (A1–A2, B5, B10, C2, C5), 19 §3.5,
23 (400 camera-hours), AUDIT_43-47, docs/13, `survsim/eval/`
(`detection.py` AP/FPPI, `alarms.py` FA/cam-h and i-LIDS timing).
