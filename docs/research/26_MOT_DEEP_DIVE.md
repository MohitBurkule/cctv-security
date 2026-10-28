# 26 · Multi-Object Tracking: a deep dive from first principles

*Kalman filter and Hungarian assignment, SORT → DeepSORT → ByteTrack → OC-SORT →
BoT-SORT, camera-motion compensation, ID switches and fragmentation, MOTA / IDF1 /
HOTA with a worked three-frame example, why MOT20 is hard, and an audit of what
SurvSim's numpy ByteTrack and `evaluate_mot` actually do.*

Companion to `18_PERCEPTION_STACK.md` §2 (tracker choice for CCTV) and
`R01_detection_and_single_camera_tracking.md` (history, metrics survey). This
document goes one level deeper: it is the version you need to derive things on a
whiteboard.

## 0. Sourcing

Every paper cited below was fetched in this session (arXiv PDFs converted to text
with `pdftotext` and read directly; SciPy docs via web fetch). Numbers quoted
with `[n]` come from those texts. `[derived]` means I computed it here (all
worked-example numbers were also re-run through `survsim.eval.tracking.evaluate_mot`
and a stand-alone multi-α HOTA script). `[VERIFY]` means stated from memory or from
code I did not fetch; check before repeating externally. Repo claims come from
reading the code at commit `7d1316a`; §8.2 was re-audited on 2026-09-26 against
commit `be9f52a` ("eval: fix HOTA DetA formula, 19-alpha average, MOTA continuity
matching"), which fixed several of the defects this document originally reported.

---

## 1. The problem in one picture

Tracking-by-detection splits MOT into two problems:

1. **Detection** — per frame, a detector gives boxes with confidence scores.
2. **Association** — decide which box in frame *t* is the same person as which
   track alive at *t−1*, start new tracks, and kill dead ones.

Everything from SORT (2016) to BoT-SORT (2022) keeps the same skeleton — *predict
where every track will be, score every (track, detection) pair, solve an
assignment, update* — and changes only (a) the motion model, (b) the pairwise
score, and (c) which detections are allowed into which round of matching.
Understanding that skeleton is 80 % of the interview.

---

## 2. The Kalman filter for a bounding box

### 2.1 Intuition

A person's box moves smoothly between frames at 25–30 fps. If I know where it was
and how fast it was moving, I can guess where it will be, and I also know *how
unsure* that guess is. When a detection arrives I blend guess and measurement,
weighting each by how much I trust it. The Kalman filter is exactly that blend,
done optimally for linear dynamics and Gaussian noise.

### 2.2 State choices across trackers

* **SORT** uses **x = [u, v, s, r, u̇, v̇, ṡ]ᵀ** — centre (u, v), *scale s = area*,
  aspect ratio r, and velocities of u, v, s; "the aspect ratio is considered to be
  constant" [1]. Seven states.
* **DeepSORT** moves to an eight-dimensional state **(u, v, γ, h, ẋ, ẏ, γ̇, ḣ)**:
  centre, aspect ratio γ, *height* h and their velocities, with (u, v, γ, h) as
  direct observations under a constant-velocity model [2]. ByteTrack inherits this.
* **BoT-SORT** replaces (γ, h) with **(w, h)**:
  x = [x_c, y_c, w, h, ẋ_c, ẏ_c, ẇ, ḣ]ᵀ, arguing that estimating width directly
  gives better boxes [5].
* **SurvSim's** `_KF` uses the DeepSORT/ByteTrack state `(cx, cy, a, h)` + four
  velocities (`survsim/baselines/bytetrack.py`, class `_KF`).

### 2.3 The matrices (constant velocity, Δt = 1 frame)

With p = (u, v, a, h) and x = [p; ṗ] ∈ ℝ⁸:

```
F = [ I₄  I₄ ]        H = [ I₄  0₄ ]
    [ 0₄  I₄ ]
```

**F** says "next position = position + velocity; velocity unchanged". **H** says
"the detector observes position, not velocity". This is precisely what the repo
builds: `_F = eye(8); _F[:4, 4:] = eye(4)`, `_H = eye(4, 8)`.

**Noise is height-scaled.** A tall (near) person jitters by more pixels than a
small far one, so noise standard deviations are proportional to box height.
BoT-SORT writes the process and measurement noise explicitly [5]:

```
Q_k = diag( (σ_p w)², (σ_p h)², (σ_p w)², (σ_p h)²,
            (σ_v w)², (σ_v h)², (σ_v w)², (σ_v h)² )
R_k = diag( (σ_m w)², (σ_m h)², (σ_m w)², (σ_m h)² )
```

with **σ_p = 0.05, σ_v = 0.00625, σ_m = 0.05**, "chosen as in [DeepSORT] …
since our frame rate is also 30 FPS" [5]. Note 0.05 = 1/20 and 0.00625 = 1/160.

The repo's `_process_noise()` is `diag((h/20)², (h/20)², 1e-2², (h/20)², (h/160)², (h/160)², 1e-5², (h/160)²)`
and `_obs_noise()` is `diag((h/20)², (h/20)², 1e-1², (h/20)²)` — i.e. the same
1/20 and 1/160 weights, but in the (a, h) parameterisation where the aspect ratio
gets a small constant noise instead of a height-scaled one. Initial covariance
`P₀` uses 2·h/20 for position and 10·h/160 for velocity, the DeepSORT reference
implementation's initiation values [VERIFY — against `nwojke/deep_sort`
`kalman_filter.py`, not fetched].

### 2.4 The two steps

Predict:
```
x̂⁻ = F x̂          P⁻ = F P Fᵀ + Q
```
Update with measurement z:
```
y = z − H x̂⁻                 (innovation)
S = H P⁻ Hᵀ + R              (innovation covariance)
K = P⁻ Hᵀ S⁻¹                (Kalman gain)
x̂ = x̂⁻ + K y     P = (I − K H) P⁻
```
These are the equations BoT-SORT writes as its Eq. (9) [5] and exactly what
`_KF.predict` / `_KF.update` compute.

### 2.5 Worked numbers [derived]

A person of height h = 100 px. Process noise on position σ = h/20 = 5 px; on
velocity h/160 = 0.625 px/frame. Measurement noise on centre = 5 px. Suppose after
some frames the position variance has settled to P_pos ≈ 30 px² before predict.
Predict adds velocity variance and Q: roughly P⁻ ≈ 30 + P_vel + 25 ≈ 60 px². Then
K ≈ P⁻/(P⁻ + R) = 60/(60 + 25) ≈ 0.71 — the filter moves 71 % of the way toward
the detection. If the person is occluded for 10 frames, P⁻ keeps growing by Q
(and by velocity uncertainty, which grows the position variance quadratically), so
the predicted box drifts on its last velocity with widening uncertainty. That drift
under occlusion is the problem OC-SORT attacks (§5.4).

**Why this matters in an interview:** the KF is not a "smoother"; it is the
source of the *predicted box* used for IoU matching. When the prediction is bad
(non-linear motion, camera shake, long occlusion), IoU with the right detection
falls below threshold, the match fails, and you get an ID switch or fragment.

---

## 3. Assignment: the Hungarian algorithm

### 3.1 Intuition

Given N predicted tracks and M detections, build an N×M cost matrix C (e.g.
C = 1 − IoU). Pick at most one detection per track and one track per detection
to minimise total cost. Greedy ("each track grabs its best detection") fails
when two tracks want the same detection: the first to ask wins even if the
global optimum gives it to the other.

### 3.2 Formal

Minimise Σᵢⱼ Cᵢⱼ Xᵢⱼ subject to Σⱼ Xᵢⱼ ≤ 1, Σᵢ Xᵢⱼ ≤ 1, Xᵢⱼ ∈ {0,1}. This is the
linear assignment problem, solvable in polynomial time — O(n³) for the classic
Hungarian / Kuhn–Munkres method [VERIFY: Kuhn 1955 not fetched]. SORT solves it
"optimally using the Hungarian algorithm" and then rejects pairs with IoU below
IOU_min [1]. SciPy's `linear_sum_assignment` — which the repo uses both in the
tracker and in the evaluator — implements "a modified Jonker-Volgenant algorithm
with no initialization" (Crouse 2016), accepts rectangular matrices where not
every row or column is assigned, and has a `maximize` flag [9].

### 3.3 Worked example [derived]

Two tracks T1, T2; two detections D1, D2. IoU:

|    | D1  | D2  |
|----|-----|-----|
| T1 | 0.6 | 0.5 |
| T2 | 0.55| 0.0 |

Greedy in row order: T1 takes D1 (0.6); T2 is left with D2 (IoU 0) → rejected →
T2 lost, D2 spawns a new track. Total matched IoU 0.6.
Hungarian: T1→D2 (0.5), T2→D1 (0.55) → total 1.05, both tracks continue. The
greedy answer produces an ID switch-shaped error the Hungarian answer avoids.
This is the same argument the repo docstring makes for using optimal rather than
greedy matching in the *evaluator* ("what stops a poor detection ordering from
inventing identity switches", `eval/tracking.py`).

### 3.4 Gating

Post-hoc thresholding (drop matches with IoU < τ) is called *gating*. Note a
subtlety in the repo tracker's `_match`: it solves on raw −IoU and only then
drops pairs below threshold. The evaluator instead sets sub-threshold costs to
1e6 before solving, which prevents the solver from "spending" a track on an
invalid pair when a valid alternative existed. For tracking-time matching the
former can occasionally lose a valid match in dense scenes [derived]; ByteTrack's
reference code gates before solving (via `lap.lapjv` with `cost_limit`)
[VERIFY — code not fetched].

---

## 4. Identity switches and fragmentation

MOT20's paper (the CLEAR-MOT conventions used by MOTChallenge) illustrates the
two failure types [8]:

* **ID switch (IDSW, "mismatch")** — a ground-truth object's matched hypothesis
  changes from one ID to another between its matched frames [8]. Two people cross,
  the tracker swaps their IDs: two IDSWs.
* **Fragmentation (Frag)** — "an interrupted ground truth trajectory will cause a
  fragmentation": the object was tracked, then untracked, then tracked again [8].
  An occlusion that the tracker bridges *with the same ID* is still one Frag if
  frames in the middle were not output; an occlusion bridged with a new ID is one
  Frag *and* one IDSW.

Operationally for CCTV: IDSW breaks "follow this person" and dwell-time
(loiter) timers; Frag breaks dwell timers even when the ID survives unless the
analytic tolerates gaps. `docs/03_BEHAVIOUR_CATALOG.md`'s loiter rule is only as
good as the tracker's IDF1 on long occlusions.

---

## 5. The tracker lineage, with equations

### 5.1 SORT (Bewley et al., 2016) [1]

* State [u, v, s, r, u̇, v̇, ṡ], constant velocity, KF.
* Cost: IoU between predicted and detected boxes; Hungarian; reject below IOU_min.
* Track death: after **T_Lost = 1** frame without detection — "the constant
  velocity model is a poor predictor of the true dynamics and … we are primarily
  concerned with frame-to-frame tracking where object re-identification is beyond
  the scope" [1]. So any occlusion ≥ 1 frame produces a new ID.
* Speed: the tracker "updates at a rate of 260 Hz" on a single CPU core [1].
* MOT15: MOTA 33.4, 1,001 ID switches, 1,764 fragmentations [1].

**One-line summary:** motion-only, IoU-only, no memory. Fast; switches IDs at
every occlusion.

### 5.2 DeepSORT (Wojke et al., 2017) [2]

Adds memory and appearance.

* **Motion cost** — squared Mahalanobis distance between detection d_j and the
  track's projected distribution (y_i, S_i):
  `d⁽¹⁾(i,j) = (d_j − y_i)ᵀ S_i⁻¹ (d_j − y_i)`, gated at the 95 % χ² quantile for
  4 DoF, **t⁽¹⁾ = 9.4877** [2]. Intuition: distance measured in standard
  deviations of the filter's own uncertainty, so a long-lost track (large S)
  accepts farther detections.
* **Appearance cost** — each track keeps a gallery R_i of the last **L = 100**
  unit-norm embeddings; `d⁽²⁾(i,j) = min{1 − r_jᵀ r_k⁽ⁱ⁾ | r_k⁽ⁱ⁾ ∈ R_i}` [2].
* **Combined** — `c_ij = λ d⁽¹⁾ + (1−λ) d⁽²⁾`, admissible only if inside *both*
  gates [2]. On MOT16 they used **λ = 0** (appearance only for cost, motion only
  as a gate) and **A_max = 30** frames [2].
* **Matching cascade** — tracks are matched in order of age since last
  association (n = 1 … A_max), so recently seen tracks get priority over long-lost
  ones whose Gaussian has smeared out [2].
* **Tentative tracks** — new tracks are tentative for their first three frames
  and deleted if unmatched in any of them [2].
* Result: ID switches on MOT16 drop from 1,423 (SORT, same detections) to 781,
  about 45 % [2].

**One-line summary:** Mahalanobis gate + cosine appearance + age cascade; buys
occlusion robustness with a ReID network.

### 5.3 ByteTrack (Zhang et al., 2021/ECCV 2022) [3]

**Insight:** low-confidence detections are not all background — many are
*occluded people*. Throwing away everything under a score threshold throws away
exactly the frames where a person is half-hidden, which is where tracks die.

**BYTE algorithm** (their Algorithm 1) [3]:

1. Predict all tracks with the KF.
2. Split detections by score threshold τ: **D_high** (score > τ) and **D_low**
   (the rest above a floor).
3. **First association:** all tracks T (including lost ones) vs D_high, by IoU
   (or ReID) similarity, Hungarian.
4. **Second association:** the *remaining* tracks vs D_low, by IoU only. Low
   detections that don't match a track are deleted as background — they never
   start tracks.
5. Unmatched high detections start new tracks; tracks unmatched after both rounds
   are kept as "lost" for a buffer and deleted after it.

Why IoU-only in round 2: low-score boxes are usually occluded and their
appearance features are unreliable [3].

Settings reported: default τ = **0.6**; matches with IoU < **0.2** rejected; lost
tracklets kept **30 frames**; for MOT17/MOT20/HiEve only IoU similarity is used
[3]. Applied to SORT on the MOT17 val split, BYTE raises MOTA 74.6 → 76.6, IDF1
76.9 → 79.3 and cuts IDs 291 → 159 [3]. Test results: **MOT17 80.3 MOTA / 77.3 IDF1
/ 63.1 HOTA at 30 FPS; MOT20 77.8 MOTA / 75.2 IDF1 / 61.3 HOTA** [3]. Applying
BYTE to nine other trackers gave 1–10 point IDF1 gains [3].

**One-line summary:** a second, IoU-only round that lets low-score boxes
rescue existing tracks but never create new ones.

### 5.4 OC-SORT (Cao et al., CVPR 2023) [4]

**Insight:** the KF trusts its *estimates*; during occlusion there are no
observations, errors accumulate, and when the person reappears the prediction
(and its velocity) is wrong. So re-centre everything on *observations*.

Three additions [4]:

* **ORU — Observation-centric Re-Update.** When a lost track is re-associated,
  build a *virtual trajectory* between the last observation before loss z_{t₁}
  and the re-associating observation z_{t₂}:
  `z̃_t = Traj_virtual(z_{t₁}, z_{t₂}, t),  t₁ < t < t₂` — in their implementation
  linear interpolation, `z̃_t = z_{t₁} + (t−t₁)/(t₂−t₁)·(z_{t₂} − z_{t₁})` [4] —
  then re-run predict/update along it, so the filter's velocity and covariance
  are what they would have been had the person been visible.
* **OCM — Observation-centric Momentum.** Add a direction-consistency term to the
  cost:
  `C(X̂, Z) = C_IoU(X̂, Z) + λ C_v(𝒵, Z)` [4], where C_v contains
  `Δθ = |θ_track − θ_intention|`: θ_track is the direction between two past
  *observations* on the track, θ_intention the direction from a historical
  observation to the candidate new detection; θ = arctan((v₁−v₂)/(u₁−u₂)). They
  use **Δt = 3** frames between observations for the direction and **λ = 0.2** [4].
  Δt is a trade-off: small Δt amplifies noise, large Δt breaks the linear
  assumption [4]. Intuition: in a crowd two people may overlap in IoU but walk in
  opposite directions; the direction term breaks the tie.
* **OCR — Observation-centric Recovery.** A heuristic second attempt that matches
  the *last observation* (not the drifted prediction) of unmatched tracks to
  unmatched detections, for objects that stopped or were briefly occluded [4].

Results with the same detections as ByteTrack: **MOT17 test 63.2 HOTA / 78.0 MOTA
/ 77.5 IDF1 / 1,950 IDs** vs ByteTrack 63.1 / 80.3 / 77.3 / 2,196; **MOT20 test
62.1 HOTA / 75.5 MOTA / 75.9 IDF1 / 913 IDs** vs ByteTrack 61.3 / 77.8 / 75.2 /
1,223 [4] (paper table; the OC-SORT GitHub README lists MOT20 HOTA 62.4, as recorded in FACTS_VERIFIED — cite which one you mean). Note the pattern: OC-SORT *loses* MOTA and *wins* on IDs, AssA and HOTA.
That is the metrics lesson of §6 in miniature — MOTA is detection-dominated.

**One-line summary:** trust observations over the filter; repair the filter
after occlusion; use direction as a cue.

### 5.5 BoT-SORT (Aharon et al., 2022) [5]

Three changes on top of ByteTrack [5]:

1. **KF state (x, y, w, h)** with the Q, R in §2.3.
2. **Camera-motion compensation (CMC)** — §5.6.
3. **IoU–ReID fusion.** Appearance embedding per track updated by EMA:
   `e_i^k = α e_i^{k−1} + (1−α) f_i^k`, **α = 0.9**, only from high-confidence
   detections [5]. They explicitly *abandon* DeepSORT-style weighted sums
   (`C = λA_a + (1−λ)A_m`, λ typically 0.98) and instead use:
   ```
   d̂cos_ij = 0.5 · dcos_ij   if dcos_ij < θ_emb and diou_ij < θ_iou
             1                otherwise
   C_ij = min{ diou_ij , d̂cos_ij }
   ```
   with **θ_iou = 0.5** (proximity gate) and **θ_emb = 0.25** (appearance gate
   chosen from a positive/negative histogram on MOT17 val) [5]. Intuition:
   appearance can only *help* a pair that is already spatially plausible; a
   confident appearance match halves the cost; otherwise fall back to IoU.

Results: **MOT17 test BoT-SORT-ReID 80.5 MOTA / 80.2 IDF1 / 65.0 HOTA** at 4.5 FPS;
**MOT20 test 77.8 MOTA / 77.5 IDF1 / 63.3 HOTA** at 2.4 FPS [5]. The price of ReID
is speed: ByteTrack is listed at 29.6 FPS in the same MOT17 table [5].

### 5.6 Camera-motion compensation

**Why:** the KF assumes the image frame is fixed. A pan, a shaky pole, or "motion
by vibrations or drifts caused by the wind, as in MOT20" [5] moves every box
together; a constant-velocity prediction then misses and IoU collapses.

**How (BoT-SORT) [5]:** extract keypoints, track them with sparse optical flow with
translation-based outlier rejection (following OpenCV's video-stabilisation global
motion compensation), and fit a 2×3 affine `A = [M | T]` by RANSAC. Detections are
masked out so the fit follows the *background*. Then transform every track's
predicted state and covariance:

```
M̃ = blockdiag(M, M, M, M)    (8×8),   T̃ = [a13, a23, 0, …, 0]ᵀ
x̂'_{k|k−1} = M̃ x̂_{k|k−1} + T̃
P'_{k|k−1} = M̃ P_{k|k−1} M̃ᵀ
```

— translation only moves the centre; M rotates/scales positions, sizes *and*
velocities [5]. They note the covariance correction can be dropped when the
camera changes slowly relative to frame rate [5].

**SurvSim relevance:** a PTZ slew in `camera director` is exactly this situation.
Principle 2 in `CLAUDE.md` ("ground truth must follow the live camera") ensures
GT is right during a slew; a CMC-less tracker (ours) will fragment there. A
scenario with a scripted PTZ slew over walking people is the cheapest possible
CMC ablation, and SurvSim knows the true camera motion, so it can also score the
*estimated* affine against truth [derived].

### 5.7 Summary table

| | Motion | Pairwise score | Low-score dets | Occlusion handling | ReID | CMC |
|---|---|---|---|---|---|---|
| SORT [1] | KF (u,v,s,r) | IoU | dropped | none (T_Lost = 1) | no | no |
| DeepSORT [2] | KF (u,v,γ,h) | Mahalanobis gate + cosine | dropped (0.3 conf) | cascade, A_max 30 | gallery 100 | no |
| ByteTrack [3] | KF (u,v,γ,h) | IoU | **2nd round** | 30-frame buffer | optional | no |
| OC-SORT [4] | KF + ORU | IoU + λ·direction | — | ORU, OCR | no | no |
| BoT-SORT [5] | KF (x,y,w,h) | min(IoU, gated ½cos) | 2nd round | buffer | EMA α 0.9 | **yes** |

---

## 6. Metrics: MOTA, IDF1, HOTA

### 6.1 MOTA (CLEAR-MOT)

**Intuition:** count every mistake, frame by frame, normalise by how many objects
there were.

```
MOTA = 1 − (|FN| + |FP| + |IDSW|) / |gtDet|            [6, Eq. 2]
MOTP = (1/|TP|) Σ_TP S                                  [6, Eq. 3]
```

Matching is per frame; matches from the previous frame that still have S ≥ α and
would not cause an IDSW are kept, and the remainder solved by Hungarian to
maximise TPs then mean similarity [6]. Consequences:

* FN and FP each count once per *frame*; IDSW counts once per *event*. In a
  1,000-frame track one ID switch costs as much as one missed frame. MOTA is
  therefore dominated by detection [6] (and see OC-SORT vs ByteTrack, §5.4).
* MOTA can be negative (more errors than objects).
* It has no localisation term; MOTP is reported separately [6].

### 6.2 IDF1 (Ristani et al., 2016)

**Intuition:** find the best *one-to-one* mapping between whole GT trajectories
and whole predicted trajectories, then ask what fraction of detections agree with
that mapping.

A bipartite "truth-to-result" match between trajectories is computed once for the
whole sequence and chosen to be optimal [7]. Matched overlapping frames are
IDTP; unmatched GT detections IDFN; unmatched predicted detections IDFP [6][7]:

```
IDP  = IDTP / (IDTP + IDFP)
IDR  = IDTP / (IDTP + IDFN)
IDF1 = IDTP / (IDTP + ½ IDFN + ½ IDFP) = 2·IDTP / (|gtDet| + |prDet|)   [6, Eqs. 4-6]
```

(The second form follows because IDTP + IDFN = |gtDet| and IDTP + IDFP = |prDet|
[derived].) IDF1 rewards long consistent identity. Its weakness: because only one
predicted track can be credited per GT track, a tracker that switches halfway
loses half the credit even if both halves are perfect, and detection quality
still leaks in through IDFN/IDFP [6].

### 6.3 HOTA (Luiten et al., IJCV 2021) [6]

**Intuition:** score detection and association *separately*, each as a Jaccard
index, then take the geometric mean so neither can hide the other; repeat at many
localisation thresholds so localisation counts too.

For a fixed IoU threshold α, match detections per frame (maximising HOTA). Then
for each TP c (a matched pair of gt ID g and pred ID p):

```
TPA(c) = TPs with the same (gtID, prID) as c         — correct associations
FNA(c) = gtDets of g not matched to p (matched to another ID, or missed)
FPA(c) = prDets of p not matched to g (matched to another gt, or FP)
A(c)   = |TPA| / (|TPA| + |FNA| + |FPA|)                         [6, Eq. 14]

DetA_α = |TP| / (|TP| + |FN| + |FP|)                              [6, Eq. 18]
AssA_α = (1/|TP|) Σ_c A(c)                                         [6, Eq. 19]
HOTA_α = √(DetA_α · AssA_α)                                        [6, Eq. 21]
HOTA   = (1/19) Σ_{α ∈ {0.05, 0.10, …, 0.95}} HOTA_α               [6, Eq. 16]
LocA   = ∫ (1/|TP_α|) Σ_{c∈TP_α} S(c) dα                           [6, Eq. 17]
```

Further decomposition: DetRe = TP/(TP+FN), DetPr = TP/(TP+FP), and
DetA = DetRe·DetPr / (DetRe + DetPr − DetRe·DetPr) [6, Eqs. 22-24]; similarly
AssRe and AssPr [6]. The paper stresses that DetA and AssA "should only be
combined into HOTA before integrating over a range of α values, not afterwards"
[6]. Notice A(c) depends only on the (g, p) pair, so AssA is the TP-weighted mean
of per-pair Jaccards `|g∩p| / (|g| + |p| − |g∩p|)` [derived] — which is exactly
how the repo computes it (§8.2).

The paper also notes that in surveillance "it is typically more important to
ensure all objects are found (detection recall), whereas extra detections can
easily be ignored by human observers" [6] — a direct argument for reporting
DetRe alongside HOTA in a CCTV product, and, in SurvSim's terms, for pairing it
with false alarms per camera-hour (Principle 4).

### 6.4 Worked three-frame example

Two people, **A** and **B**, visible in all three frames (|gtDet| = 6). The
tracker outputs IDs 1, 2, 3.

| Frame | A matched to | B matched to | Extra | IoUs of matches |
|---|---|---|---|---|
| 1 | **1** | **2** | — | A 0.90, B 0.80 |
| 2 | **2** | *missed* | **3** (on nothing) | A 0.70 |
| 3 | **2** | **1** | — | A 0.85, B 0.60 |

What happened: in frame 2 the tracker lost B, gave B's ID (2) to A, and hallucinated
a box. In frame 3 B came back and was given A's old ID (1).

**Counts (α = 0.5).** TP = 5, FN = 1 (B in f2), FP = 1 (ID 3), |prDet| = 6.

**IDSW.** A: f1 → 1, f2 → 2 ⇒ switch (1). f3 → 2, no switch. B: last matched to 2
in f1, matched to 1 in f3 ⇒ switch (2). **IDSW = 2.**
**Frag.** B tracked, untracked, tracked ⇒ **Frag = 1.**

**MOTA** = 1 − (1 + 1 + 2)/6 = 1 − 4/6 = **0.333.**
**MOTP** (mean IoU of TPs) = (0.9+0.8+0.7+0.85+0.6)/5 = **0.77.**

**IDF1.** Co-occurrence counts n(g,p): (A,1)=1, (A,2)=2, (B,2)=1, (B,1)=1.
Candidate bijections: {A↔2, B↔1} → 2+1 = 3; {A↔1, B↔2} → 1+1 = 2. Best: IDTP = 3.
IDFN = 6 − 3 = 3; IDFP = 6 − 3 = 3.
IDP = IDR = 3/6 = 0.5; **IDF1** = 2·3/(6+6) = **0.500.**

**HOTA at α = 0.5.** DetA = 5/(5+1+1) = **0.714.** Track lengths: |A| = |B| = 3;
|1| = 2 (f1, f3), |2| = 3, |3| = 1. Per-pair Jaccard:

| pair | ∩ | union = |g|+|p|−∩ | A(c) | # TPs |
|---|---|---|---|---|
| (A,1) | 1 | 3+2−1 = 4 | 0.25 | 1 |
| (A,2) | 2 | 3+3−2 = 4 | 0.50 | 2 |
| (B,2) | 1 | 3+3−1 = 5 | 0.20 | 1 |
| (B,1) | 1 | 3+2−1 = 4 | 0.25 | 1 |

AssA = (0.25 + 2·0.50 + 0.20 + 0.25)/5 = 1.70/5 = **0.340.**
HOTA₀.₅ = √(0.714 × 0.340) = √0.243 = **0.493.**

**Full HOTA over 19 α values** [derived; computed by script]. For α ≤ 0.60 all
five matches survive (HOTA_α = 0.493). Above that, matches drop out by IoU:
α ∈ {0.65, 0.70}: 4 TPs, DetA 0.5, AssA 0.3625, HOTA_α 0.426;
α ∈ {0.75, 0.80}: 3 TPs, DetA 0.333, AssA 0.217, HOTA_α 0.269;
α = 0.85: 2 TPs, 0.212; α = 0.90: 1 TP, 0.151; α = 0.95: 0.
Averaging: **HOTA ≈ 0.403, DetA ≈ 0.554, AssA ≈ 0.301** (exact arithmetic; TrackEval, and `evaluate_mot` since M1 parity, give **0.4005** because an IoU of 0.8999…94 fails α = 0.90 at machine-eps — docs/13 §TrackEval parity), LocA ≈ 0.80 (mean TP
IoU per α, averaged over the 18 α with any TPs) [derived]. Note the FN at high α
counts *twice*: an unmatched pair becomes both an FN and an FP.

**Reading the example.** MOTA 0.33 says "bad". IDF1 0.50 says "half the identity
is right". HOTA 0.40 with DetA 0.55 ≫ AssA 0.30 says **the association half is the
problem** — which is true: detection was 5/6, but identities were scrambled. That
diagnostic split is the reason HOTA exists.

---

## 7. Why MOT20 is hard

MOT20 (Dendorfer et al., 2020) has 8 new sequences filmed at 25 fps, with mean
crowd density reaching 246 pedestrians per frame in the paper's abstract figure
[8]. The per-sequence table [8]:

| Seq | Resolution | Frames | Tracks | Boxes | Density (per frame) | Scene |
|---|---|---|---|---|---|---|
| MOT20-01 | 1920×1080 | 429 | 74 | 19,870 | 46.3 | indoor |
| MOT20-02 | 1920×1080 | 2,782 | 270 | 154,742 | 55.6 | indoor |
| MOT20-03 | 1173×880 | 2,405 | 702 | 313,658 | 130.4 | outdoor, night |
| MOT20-05 | 1654×1080 | 3,315 | 1,169 | 646,344 | 195.0 | outdoor, night |
| **train total** | | **8,931** | **2,215** | **1,134,614** | **127.0** | |
| test total (04,06,07,08) | | 4,479 | 1,242 | 517,426 | 115.5 | |

ByteTrack reports 170 pedestrians per image on average in the MOT20 test set [3].

What makes it hard, in mechanism terms:

1. **Occlusion is the norm, not the exception.** At ~130–195 people per frame from
   an elevated view, most boxes overlap others. Detector NMS suppresses true
   positives in overlapping clusters, and the survivors often have low scores —
   exactly the regime ByteTrack's second round was designed for [3].
2. **IoU becomes ambiguous.** Neighbouring predicted boxes overlap several
   detections, so the IoU cost matrix has many near-ties; a small KF error flips
   the assignment → IDSW. Direction cues (OC-SORT OCM) and appearance (BoT-SORT)
   exist to break these ties [4][5].
3. **Small and dark targets.** Two of four training sequences are at night [8];
   appearance embeddings degrade, which is why BoT-SORT gates ReID behind IoU and
   uses only high-confidence detections for the EMA [5].
4. **Scale of evaluation.** Over a million boxes in train [8]; per-frame assignment
   with >100 boxes is where naive Python costs show up (the repo's own profiling,
   §8.3).
5. **Camera drift.** BoT-SORT names wind-induced vibration in MOT20 as a reason
   for CMC even with static cameras [5].

Headline scores fall accordingly: ByteTrack 63.1 → 61.3 HOTA and OC-SORT 63.2 →
62.1 from MOT17 to MOT20 [3][4].

---

## 8. What SurvSim's implementation does and doesn't do

### 8.1 `survsim/baselines/bytetrack.py`

**Does:**

* KF on (cx, cy, a, h) + velocities, constant velocity, DeepSORT-style
  height-scaled Q and R (1/20, 1/160) — matches §2.3.
* Two-stage BYTE association: high (≥ `high`=0.5) vs all tracks at IoU ≥
  `match_iou`=0.2, then remaining tracks vs low (0.1 ≤ score < 0.5) at IoU ≥
  `low_iou`=0.5. Low detections never create tracks. The 0.2 first-stage gate
  matches the paper [3].
* New tracks only from unmatched high detections with score ≥ `new_track`=0.6;
  tentative until a second hit; tentative tracks die on first miss.
* Confirmed tracks survive `max_lost` frames; `baselines/run.py` sets
  `max_lost = fps` (1 s; 25 frames on MOT20), close to the paper's 30 [3].
* Output only confirmed tracks matched *this* frame (no extrapolated boxes).
* Solver: `scipy.optimize.linear_sum_assignment` [9].

**Doesn't (and what each costs):**

| Missing | Effect | Reference |
|---|---|---|
| Camera-motion compensation | PTZ slews / shake → fragments, IDSW | BoT-SORT §5.6 [5] |
| Appearance / ReID in either stage | long occlusions → new ID | DeepSORT, BoT-SORT [2][5] |
| ORU / OCM / OCR | filter drift after occlusion is never repaired | OC-SORT [4] |
| Mahalanobis gating | uses IoU only; P is propagated but never used for association | DeepSORT [2] |
| Gate-before-solve in `_match` | solver can spend a track on a sub-threshold pair, then discard it | §3.4 [derived] |
| Separate stage for unconfirmed tracks | ByteTrack's reference matches unconfirmed tracks in a third round with leftover high dets; here they compete in round 1 | [VERIFY — reference code not fetched] |
| τ = 0.6 split | repo splits at 0.5 and creates tracks at 0.6; paper's default split is 0.6 [3] | — |
| Score fusion, per-sequence thresholds, interpolation | leaderboard entries tune these | module docstring |

The module docstring is honest about the headline gaps ("the published algorithm
minus camera-motion compensation and the per-sequence thresholds"), and
`docs/13_BASELINES.md` states the MOT20 numbers are not leaderboard-comparable.

### 8.2 `survsim/eval/tracking.py::evaluate_mot`

**Does:**

* Per-frame CLEAR-MOT matching (`_match_frame_with_continuity`, since `be9f52a`):
  a still-valid (IoU ≥ 0.5) previous match is kept first, then the remainder is
  solved by Hungarian on 1 − IoU with sub-threshold pairs set to 1e6 *before*
  solving (correct gating).
* MOTA = 1 − (FN + FP + IDSW)/|gt| — the CLEAR formula [6].
* IDSW when a GT id's matched pred id differs from its last matched pred id,
  carrying across gaps (CLEAR convention [8]).
* IDF1 via a global Hungarian on the (gt, pred) co-occurrence matrix, IDF1 =
  2·IDTP/(|gt| + |pred|) — matches §6.2 [6][7].
* AssA as the TP-weighted mean of per-pair Jaccard `inter / (|g| + |p| − inter)`,
  which is algebraically the HOTA definition [6] (§6.3).

Running the §6.4 example through it (re-run at audit, `be9f52a`) gives MOTA
0.3333, MOTP 0.77, IDF1 0.50, IDSW 2, Frag 1, DetA 0.714, AssA 0.34,
`hota_at_05` 0.493 and `hota` 0.403 (0.4005 since M1 TrackEval parity, see §6.4) — all agreeing with the hand calculation
[derived, run]. (IoUs exactly equal to an α threshold must be constructed with a
tiny epsilon; float rounding at 0.70/0.80 otherwise drops them and gives 0.392.)

**Problems originally found, and their status after `be9f52a`:**

1. **FIXED — DetA was detection *recall*.** The code used TP/(TP+FN); HOTA's DetA
   is TP/(TP + FN + FP) [6, Eq. 18]. It is now `deta = tp_05 / (tp_05 + misses +
   fps_)`. On the worked example this moved DetA 0.833 → 0.714 and HOTA₀.₅
   0.532 → 0.493 (commit message).
2. **FIXED — single α = 0.5.** `hota` is now the mean of HOTA_α over the 19 α in
   {0.05, …, 0.95} (`HOTA_ALPHAS`, `_hota_multi_threshold`), each α re-matched at its
   own threshold [6, Eq. 16]; the old slice is kept as `hota_at_05`, and
   `deta`/`assa` are still the α = 0.5 slice. No LocA is reported (MOTP at 0.5 is).
3. **FIXED in M1 (2026-09-27, docs/13 §TrackEval parity) — HOTA matching was not HOTA's matching.** Now one association-aware matching per frame, thresholded per α; the text below describes the pre-M1 code. HOTA matches to maximise
   HOTA (association-aware); the repo uses plain per-frame IoU Hungarian per α (the
   continuity carry-over is deliberately *not* used for HOTA). Usually a small
   difference [6].
4. **FIXED — MOTA continuity.** A still-valid previous match is now kept before
   Hungarian on the rest (CLEAR procedure). Nuance: `last_match` persists across
   gaps, so the "previous" match can be from before an occlusion, not strictly
   frame t−1 [derived from code].
5. **FIXED — fragmentation edge case.** A GT that enters unmatched and is picked up
   later is no longer counted as a fragment: Frag now needs the GT to be in
   `ever_tracked` before the untracked gap.
6. **STILL OPEN** — no ignore-region handling inside the function (done upstream in
   `baselines/run.py` per `docs/13_BASELINES.md`); no MT/ML/PT counts.

The repo's MOT20 subset row was re-scored after the fix: **old** MOTA 0.463 /
IDF1 0.538 / HOTA 0.545 (retired: HOTA₀.₅, recall-only DetA) → **new** MOTA 0.466 /
IDF1 0.549 / HOTA 0.434 (pre-parity, 19-α; `hota_at_05` 0.539) (`docs/13_BASELINES.md`), and
after TrackEval parity (M1, 2026-09-27) MOTA 0.466 / IDF1 0.559 / HOTA 0.443
(`hota_at_05` 0.537); 0.434 is the pre-parity value. The
0.545 → 0.434 drop is the size of the correction the earlier version of this
section predicted. The same doc's full-train profiling (tracker ≈ 56 s, evaluator
≈ 6 s over 8,931 frames, measured before the fix) shows neither was a runtime
bottleneck; the 19-α pass adds evaluator time that has not been re-profiled.

### 8.3 `survsim/baselines/metrics.py`

Detection only: COCO AP via pycocotools with MOT ignore classes mapped to
`iscrowd` and `maxDets = [1, 10, 1000]`, reading the precision array directly
because `summarize()` hard-codes 100 detections — which on MOT20's 127 boxes per
frame on average [8] would silently cap recall. That is a correct and
non-obvious fix and worth mentioning in an interview.

### 8.4 What SurvSim can offer that MOT20 can't

* **Exact identities through total occlusion** and appearance epochs (disguise),
  so AssA can be scored across events no human annotator could label.
* **Known camera motion** (PTZ, tamper) for a CMC ablation (§5.6).
* **Density sweeps** — the crowd model can walk from MOT17-like to MOT20-like
  density with everything else fixed, turning "why MOT20 is hard" into a curve.
* **Mask-derived boxes** (Principle 1) mean GT boxes already reflect occlusion,
  which matters for DetA at high α.

---

## 9. How to say this in an interview

* **Skeleton first.** "Every tracker since SORT is predict–score–assign–update.
  They differ in the motion model, the cost, and which detections enter which
  round."
* **KF in one breath.** "Eight-state constant velocity on centre, aspect, height;
  F adds velocity to position, H reads position; noise scales with box height —
  1/20 for position, 1/160 for velocity — because a near person jitters more
  pixels."
* **Hungarian.** "Global optimum of a bipartite assignment; greedy creates ID
  switches when two tracks want one detection. Gate before you solve."
* **The lineage.** "SORT: IoU only, dies after one frame. DeepSORT: Mahalanobis
  gate plus cosine appearance with a 100-embedding gallery and an age cascade —
  45 % fewer switches. ByteTrack: don't throw away low-score boxes; use them in a
  second IoU-only round to keep occluded tracks alive, never to start tracks.
  OC-SORT: trust observations — re-update the filter along a virtual trajectory
  after occlusion and add a direction-consistency cost. BoT-SORT: fix the image
  frame with an affine camera-motion estimate, and fuse ReID as min(IoU, ½cos)
  gated by both."
* **Metrics.** "MOTA counts per-frame errors and is detection-dominated; an ID
  switch costs one frame. IDF1 is the best one-to-one trajectory mapping —
  identity consistency. HOTA is √(DetA·AssA), both Jaccard indices, averaged over
  19 IoU thresholds, so I can tell which half to fix." Then draw the 3-frame
  example: MOTA 0.33, IDF1 0.50, HOTA₀.₅ 0.49 with DetA 0.71 vs AssA 0.34.
* **MOT20.** "Up to ~195 people per frame in training, night scenes, pervasive
  overlap: low scores, ambiguous IoU. OC-SORT loses 2.3 MOTA to ByteTrack there
  but wins HOTA and cuts IDs by a quarter — the metric disagreement is the lesson."
* **Ownership.** "In our simulator I read the tracker and evaluator line by line.
  The tracker is a faithful BYTE without CMC or ReID. The evaluator's DetA used to
  omit false positives and HOTA was a single α; that was fixed, and on our MOT20
  subset HOTA fell from 0.545 to 0.434 (0.443 after TrackEval parity) — the three-frame example is the
  regression case."
* **For CCTV specifically.** "Operators need recall and stable identity through
  occlusion for dwell rules; I'd report DetRe, AssA and IDSW per hour next to
  false alarms per camera-hour, not MOTA."

---

## References

1. Bewley, Ge, Ott, Ramos, Upcroft — *Simple Online and Realtime Tracking*, ICIP
   2016. https://arxiv.org/abs/1602.00763 (PDF fetched). Used: state
   [u,v,s,r,u̇,v̇,ṡ], constant aspect ratio, IoU + Hungarian + IOU_min, T_Lost = 1
   and its rationale, 260 Hz, MOT15 table (MOTA 33.4, IDSW 1,001, Frag 1,764).
2. Wojke, Bewley, Paulus — *Simple Online and Realtime Tracking with a Deep
   Association Metric*, ICIP 2017. https://arxiv.org/abs/1703.07402 (PDF fetched).
   Used: 8-D state, Mahalanobis d⁽¹⁾ and t⁽¹⁾ = 9.4877, gallery L = 100, cosine
   d⁽²⁾, c = λd⁽¹⁾ + (1−λ)d⁽²⁾, λ = 0, A_max = 30, tentative 3 frames, matching
   cascade, IDSW 1,423 → 781 (45 %), detection threshold 0.3.
3. Zhang et al. — *ByteTrack: Multi-Object Tracking by Associating Every Detection
   Box*, ECCV 2022. https://arxiv.org/abs/2110.06864 (abstract page and PDF
   fetched). Used: BYTE algorithm, τ = 0.6, IoU reject < 0.2, 30-frame buffer,
   IoU-only for MOT17/20, SORT→BYTE ablation (74.6→76.6 MOTA, 76.9→79.3 IDF1,
   291→159 IDs), MOT17 80.3/77.3/63.1 @30 FPS, MOT20 77.8/75.2/61.3, 170
   pedestrians/frame on MOT20 test, 1–10 IDF1 on nine trackers.
4. Cao, Pang, Weng, Khirodkar, Kitani — *Observation-Centric SORT*, CVPR 2023.
   https://arxiv.org/abs/2203.14360 (PDF fetched). Used: ORU virtual trajectory
   and re-update, OCM cost C_IoU + λC_v, Δθ definition, Δt = 3, λ = 0.2, OCR,
   MOT17/MOT20 test tables vs ByteTrack.
5. Aharon, Orfaig, Bobrovsky — *BoT-SORT: Robust Associations Multi-Pedestrian
   Tracking*, 2022. https://arxiv.org/abs/2206.14651 (PDF fetched). Used: state
   (x,y,w,h), Q/R with σ_p = 0.05, σ_v = 0.00625, σ_m = 0.05, KF update Eq. 9,
   CMC (keypoints + sparse optical flow + RANSAC affine; Eqs. 5–8), wind
   vibration in MOT20, EMA α = 0.9, IoU-ReID fusion Eqs. 12–13 with θ_iou = 0.5,
   θ_emb = 0.25, weighted-sum λ = 0.98 note, MOT17/MOT20 test tables.
6. Luiten et al. — *HOTA: A Higher Order Metric for Evaluating Multi-Object
   Tracking*, IJCV 2021. https://arxiv.org/abs/2009.07736 (PDF fetched). Used:
   MOTA/MOTP Eqs. 2–3 and CLEAR matching procedure, IDF1 Eqs. 4–6 and matching,
   TPA/FNA/FPA, A(c), DetA/AssA/HOTA_α Eqs. 18–21, 19-α integral Eq. 16, LocA
   Eq. 17, DetRe/DetPr decomposition, surveillance recall remark.
7. Ristani, Solera, Zou, Cucchiara, Tomasi — *Performance Measures and a Data Set
   for Multi-Target, Multi-Camera Tracking*, ECCV-W 2016.
   https://arxiv.org/abs/1609.01775 (PDF fetched). Used: optimal bipartite
   truth-to-result trajectory match underlying IDTP/IDFN/IDFP.
8. Dendorfer et al. — *MOT20: A benchmark for multi object tracking in crowded
   scenes*, 2020. https://arxiv.org/abs/2003.09003 (PDF fetched). Used: 8
   sequences, 246 ped/frame, per-sequence table (fps, resolution, frames, tracks,
   boxes, density), train/test totals, IDSW and fragmentation illustrations.
9. SciPy — `scipy.optimize.linear_sum_assignment` documentation.
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html
   (fetched). Used: modified Jonker–Volgenant (Crouse 2016), rectangular
   matrices, `maximize`.

Repo files read: `survsim/baselines/bytetrack.py`, `survsim/eval/tracking.py`,
`survsim/baselines/metrics.py`, `survsim/baselines/run.py` (max_lost), 
`docs/13_BASELINES.md`, `tests/test_tracking_eval.py` and
`tests/test_metric_validation.py` (grep).
