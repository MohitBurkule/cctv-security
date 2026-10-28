
> **Scope.** This covers the behaviour layer of a CCTV analytics stack, from first
> principles and with the arithmetic worked through. Topics: rule engines versus
> sequence models on tracks; trajectory forecasting (LSTM, Social-LSTM, Social GAN,
> Trajectron++, graph models); social-force crowd models; video anomaly detection
> (reconstruction, prediction, weakly-supervised MIL); the benchmarks and why their
> metrics mislead; how i-LIDS, PETS 2006 and ActEV/VIRAT define the events operators
> actually care about; and the economics of false alarms.
>
> **Relationship to other reports.** Report 19 is the design document for behaviour
> report does not repeat their taxonomy. It goes one level deeper on *mechanisms and
>
> **Evidence tags.** `[n]` means a primary source fetched and read this session (see
> References; each entry says what was taken from it). `[derived]` means my own
> arithmetic or reasoning from cited numbers. `[VERIFY]` means the claim was not
> confirmed from a fetched primary source this session and should be checked before
> being stated as fact. Repo claims cite file paths that were read this session.

---

## 0. The one-paragraph version

A behaviour alarm is a *decision about a track over time*, and it will be judged by an
operator who sees perhaps a few alarms an hour across hundreds of cameras. Almost
everything follows from that. Rules (dwell > T in zone Z) are transparent and
configurable, but they cannot tell a commuter from a loiterer, because they measure
the one feature on which the two agree. Learned sequence models on tracks can use the
features on which they differ, such as tortuosity, revisits and orientation to assets.
Pixel-level anomaly detectors (autoencoders, frame predictors, MIL rankers) score
"unusualness" rather than intent, and they are reported with frame-level AUC. That
metric ignores time-to-alarm, rewards chattering, and is dominated by normal frames.
The operational metric is *false alarms per camera-hour at a fixed detection
tolerance*, and the budget for it is several orders of magnitude tighter than research
operating points. SurvSim exists partly to measure exactly that gap, using hard
negatives such as `commute_wait` that are built to defeat the rule.

---

## 1. What "behaviour" means operationally: the three dialects

"loitering", "abandoned object" and "tailgating" are **defined by protocol, not by
intuition**. The definition sets the label, the label sets the metric, and the metric
sets which model wins.

### 1.1 i-LIDS (UK Home Office): event-detection scenarios

The i-LIDS User Guide [11] defines Event Detection scenarios: abandoned baggage,
parked vehicle, doorway surveillance and sterile zone. It also defines Object
Tracking scenarios, such as multiple-camera tracking. Each scenario's alarm events are
spelled out in an appendix. Two are worth memorising:

* **Abandoned object** (Appendix F) [11]. A person placed an object that was in their
  possession when they entered the clip onto the floor or a seat in the detection
  area; that person has left the detection area without the object; *over sixty
  seconds after they left*, they have still not returned; and the object remains. The
  clock starts when the **owner leaves the area**, not when the bag is put down. The
  definition therefore needs an owner association, a zone and a timer. A static-object
  detector alone cannot satisfy it.
* **Parked vehicle** [11]. The example alarm event is a vehicle in a defined zone for
  more than 60 seconds. There is also a follow-on alarm when a person exits the
  vehicle.

**There is no i-LIDS loitering scenario in the User Guide's list of six scenarios**
[11]. When a vendor says "i-LIDS-approved loitering detection", ask which scenario
they mean. The closest i-LIDS relatives are sterile zone (any presence counts) and
doorway surveillance (entry and exit through a door).

The **timing rule** is what matters most for evaluation. Quoting [11]: *"Systems have
ten seconds to report an alarm state after an alarm event begins … During this time
multiple alarm reports will be disregarded; an alarm event is either detected or not.
After this ten second window, any further alarms reported will be deemed 'false
positives'."* Also: *"Where a system false alarms several times in quick succession,
only one false positive alarm will be logged every five seconds,"* and systems
*"should NOT continue to alarm over the duration of alarm events."* Two simultaneous
events need two alarms.

**Scoring** [11]: recall r = a/(a+c) and precision p = a/(a+b), where a is true
positives, b false positives and c false negatives. These are combined into a
weighted F-measure with a scenario-declared **recall bias α**:

    F1 = (α + 1)·r·p / (r + α·p)                          [11 §6.4.1; the guide calls it "F1",
                                                            α = "recall bias". The PDF text
                                                            layer drops the α symbols; this
                                                            is the van Rijsbergen placement
                                                            that gives F → r as α → ∞, which
                                                            is what "recall bias" requires]

The declared α values are asymmetric. For abandoned baggage, **Operational Alert
α = 0.35** and **Event Recording α = 35**. For parked vehicle they are 0.55 and 60
[11]. Intuition: as α → ∞ the formula tends to r, so recall is all that counts (the
footage is being recorded for later search). As α → 0 it tends to p, so precision
dominates (a human is interrupted by every alarm). The pass thresholds themselves are
"not made public" [11].

Worked example [derived]. A system detects 8 of 10 abandoned bags and raises 12 false
alarms, so r = 0.8 and p = 8/20 = 0.4.
* Operational Alert, α = 0.35: F = 1.35·0.32 / (0.8 + 0.14) = 0.432/0.94 ≈ **0.46**.
* Event Recording, α = 35: F = 36·0.32 / (0.8 + 14) = 11.52/14.8 ≈ **0.78**.

The same system scores far worse as an alerting tool than as a recording tool. That is
the point of α. (Whether either score "passes" cannot be said: the F1 pass
boundaries are not made public [11].)

### 1.2 PETS 2006: abandoned luggage with a spatial rule

PETS 2006 was recorded in a railway station with support from British Transport
Police and Network Rail. It has seven multi-camera left-luggage sequences of
increasing complexity [12]. The definition is **spatio-temporal**: luggage is
abandoned if its owner is farther than **300 cm** from it for **30 seconds** [12].
Implementations (e.g. [12]) raise a *warning* when the owner first crosses b = 300 cm
and an *alarm* once that has persisted for 30 s [12]. Compared with i-LIDS, the clock
starts at a *distance* threshold rather than at "left the detection area", and the
timer is shorter. The two protocols can label the same clip differently.

PETS 2007 added loitering and theft scenarios. A commonly quoted PETS 2007 loitering
definition is "in the scene for more than 60 s" **[VERIFY — not confirmed from a
primary source in either writing or audit session]**.

### 1.3 ActEV / VIRAT (NIST): activities, not alarms

NIST's ActEV defines an activity as *"one or more people performing a specified
movement or interacting with an object or group of objects"*. Each activity is
formally defined by elements that include a name, a description and begin-time and
end-time rules [13]. The activity names are visibly *not* security alarms: `Closing`,
`Closing_trunk`, `Entering`, `Loading`, `Unloading`, `Transport_HeavyCarry`,
`Riding`, `Talking`, `specialized_talking_phone`, `specialized_texting_phone` [13].
They run on VIRAT footage [13]. The metric is **P_miss at a fixed rate of false
alarms**:

    P_miss(τ) = N_MD(τ) / N_TrueInstance         RateFA(τ) = N_FA(τ) / VideoDurationInMinutes    [13]

RateFA is expressed **per minute of video** [13]. Report 19 §5.2 records the operating
points of the later leaderboards.

### 1.4 How SurvSim encodes these

`docs/03_BEHAVIOUR_CATALOG.md` uses a 3-level label taxonomy (`class` / `type` /
`subtype`). Every suspicious type sits next to a normal type that exercises the same
cue. `commute_wait` (dwell 30–900 s in a queue or platform zone) is explicitly the
**"loitering false-positive hard negative"**, and `smoke_break`, `vendor` and
`maintenance` do the same job for loitering, long-stationary and tamper cues. In code
(`survsim/director/behaviours.py`), `class CommuteWait(Loiter)` *inherits the motion
of `Loiter` unchanged*. Only the label differs (`normal.commute_wait` versus
`suspicious.loiter`), and the docstring says so: "Indistinguishable from loitering by
dwell time alone." `ObjectAbandon` ("carry an object into a zone, put it down, then
walk away and do not return") and `Tailgate` (follow at `gap_m`, default 1.2 m,
through a controlled door) are the other two canonical events.

knows the owner's true position at every tick. It can compute an i-LIDS onset (owner
leaves the area, plus 60 s) and a PETS onset (owner beyond 3 m, plus 30 s) from the
same run. Real footage needs a separate annotation pass for each.

---

## 2. Rule engines: what they are good at and exactly where they break

### 2.1 Anatomy of a dwell rule

`survsim/eval/rules.py::DwellRule` is the rule every vendor ships first. For each
track, it starts a timer when the person enters an eligible zone (tag in `gate`,
`restricted` or `perimeter_fence`) *and* is moving at or below `speed_cap_mps = 0.5`.
It resets the timer when either condition fails, fires once per zone when the timer
reaches `threshold_s` (default 60 s), and emits `suspicious.loiter`. Its companion
`AbandonedObjectRule` fires when an object is static for 30 s with its owner more
than 15 m away.

The rule's parameters are the **product surface**: a site integrator tunes T, the
zones and the speed cap. That is the rule's real strength over a black-box model. It
is explainable to a guard, auditable by a regulator, and reconfigurable without
retraining.

### 2.2 Why a dwell rule cannot separate commuter from loiterer

Let D be dwell time. Suppose innocent platform waits are roughly uniform on
[30, 900] s, which is `commute_wait`'s range in docs/03, and suspicious loiters are
at least T_loiter = 120 s [derived from the catalogue parameters]. A rule
"D ≥ 120 s" catches every loiter and also every commuter who waited more than 2
minutes, which is (900 − 120)/(900 − 30) ≈ **90 %** of them [derived]. Raising T to
600 s cuts commuter alarms to (900 − 600)/870 ≈ 34 %, and it misses every loiter
shorter than 10 minutes. **No threshold on a feature whose class-conditional
distributions overlap can buy precision without paying recall.** This is not a
tuning problem. The two classes are identical on the measured axis.
`survsim/eval/rules.py`'s docstring makes the same point: run on *perfect* tracks,
the rule's errors are the rule's own, not perception errors.

### 2.3 The fix is more features, not a better threshold

`survsim/eval/behaviour.py` trains a regularised logistic regression on
**trajectory-only** features: `duration_s`, `dwell_fraction`, `mean_speed`,
`speed_std`, `max_speed`, `path_tortuosity`, `direction_changes`,
`radius_of_gyration`, `zone_revisits` and `n_zones_visited`. Appearance is excluded
on purpose. The evasion generator makes clothing carry no label information, and in
deployment a model that reads appearance would amount to profiling. The data is split
**by identity**, never by segment, so the model cannot memorise people. The design
is a *floor*. Any deep model must beat it to justify its opacity.

Why these features separate the classes [derived, physical intuition]. A commuter
waits *facing the arrival direction*, clustered tightly around one spot (small radius
of gyration), and leaves when the train comes (dwell ends at a scheduled time,
correlated across many people). A reconnaissance loiterer revisits zones, changes
direction more often, and orients to assets and cameras. The catalogue's
reconnaissance cues (report 19 §11) are this list. The correlated departure is a
*group-level* cue that a per-track model cannot see, which motivates §3.4.

### 2.4 Rule engines at scale: composition

Real products chain rules into state machines. For example: "person enters zone A →
within 30 s a bag becomes static → owner leaves zone → 60 s timer" is an i-LIDS
abandoned-object rule, and every arrow is a place where a tracking ID switch breaks
the chain. That observation connects the behaviour layer back to the MOT layer:
**ID-switch rate directly bounds recall of multi-step rules** [derived]. If the
per-transition ID survival is 0.95 and a rule has 4 transitions, chain survival is
0.95⁴ ≈ 0.81, a 19 % recall ceiling loss before any behaviour logic runs.

---

## 3. Sequence models on tracks

### 3.1 The problem statement: forecasting as a proxy for "normal"

Trajectory forecasting asks: given positions over the last t_obs steps, predict the
next t_pred. The standard pedestrian protocol observes **8 timesteps (3.2 s)** and
predicts **12 timesteps (4.8 s)**, at 0.4 s per step. It is evaluated leave-one-out
over the five ETH/UCY scenes (ETH, HOTEL, UNIV, ZARA1, ZARA2), trained on four and
tested on the fifth [4][5].

Metrics [4][5]:
* **ADE**: mean L2 distance between predicted and true positions over all predicted
  steps.
* **FDE**: L2 distance at the final step.
* **Best-of-N (minADE_N / minFDE_N)**: the minimum over N sampled futures [5]. With
  N = 20 this is the convention for generative models [4][5].
* **KDE NLL**: the negative log-likelihood of the ground truth under a kernel density
  fitted to samples [5]. Unlike best-of-N, this rewards a *calibrated distribution*.

Why a surveillance company cares. A forecaster is a learned model of *normal* motion
in a scene. Prediction error then becomes an anomaly score at the track level, the
trajectory analogue of the frame-prediction methods in §5.2. It is also useful for
bridging occlusions in tracking and for re-acquiring targets between cameras.

### 3.2 Social-LSTM (Alahi et al., CVPR 2016)

Intuition: one LSTM per person encodes that person's motion history, but people steer
around each other, so each LSTM needs to know its neighbours' state. **Social
pooling** gives it that. For person i at time t, build an **N_o × N_o × D** tensor
H_t^i: a spatial grid centred on i, where each cell sums the D-dimensional hidden
states of the neighbours that fall into it [3]. This preserves *where* neighbours are,
unlike a plain average. The pooling layer adds no parameters [3]. The output at each
step is the parameter set of a **bivariate Gaussian** over the next position, and the
model is trained by NLL [3]. It is evaluated on ETH and UCY [3].

### 3.3 The humbling baseline table (Social GAN, CVPR 2018)

Social GAN [4] replaced grid pooling with a pooling module over *all* people in the
scene. It trained adversarially against a recurrent discriminator and added a
**variety loss**: draw k samples and back-propagate only the best one,
L_variety = min_k ‖Y − Ŷ^(k)‖₂, which lets the model express multimodality [4]. Its
The averages over the five ETH/UCY scenes, ADE/FDE in metres at 8/12 predicted steps
[4], are:

| Model | ADE (8 / 12) | FDE (8 / 12) |
|---|---|---|
| Linear (constant velocity) | 0.54 / 0.79 | 0.98 / 1.59 |
| LSTM (no social) | 0.43 / 0.70 | 0.91 / 1.52 |
| Social-LSTM | 0.45 / 0.72 | 0.91 / 1.54 |
| SGAN 1V-1 (one sample) | 0.49 / 0.74 | 1.00 / 1.54 |
| SGAN 1V-20 (best of 20, one variety sample) | 0.45 / 0.67 | 0.93 / 1.41 |
| SGAN 20V-20 (best of 20) | 0.39 / 0.58 | 0.78 / 1.18 |

(Cells re-checked against the paper's Table 1 AVG row on 2026-09-26.)

What to say about it [derived]:
1. **The social term barely helps under single-sample evaluation.** Social-LSTM does
   not beat a plain LSTM on average, and neither beats constant velocity by more than
   about 10 cm ADE at 4.8 s.
2. **Most of the gains in later papers come from best-of-20.** Taking the minimum over
   20 guesses is a strong oracle: it reports the error of the best of 20 hypotheses,
   which no deployed system can pick without the ground truth. For anomaly scoring
   you need the *likelihood of what actually happened* (KDE NLL), not the best-case
   error.
3. **These errors are ~0.5–1.5 m at 4.8 s.** In a CCTV camera at typical standoff,
   that is several person-widths. Forecasting is a weak prior, not an oracle.

### 3.4 Trajectron++ and graph models

**Trajectron++** (ECCV 2020) [5] is a graph-structured recurrent model. Agents are
nodes and interactions are edges, and the model uses a **CVAE** latent variable to
represent multimodality explicitly [5]. It adds three things. First, **dynamics
integration**: it predicts controls (velocity or acceleration) and integrates them
through a dynamics model, so outputs are physically feasible. Second, *heterogeneous
data*: semantic maps and ego-plans. Third, it is evaluated on both ETH/UCY and
nuScenes [5]. It reports ADE, FDE, KDE NLL and best-of-N, and claims *"in some cases
achieving 60% lower average prediction error"* than prior work [5]. Its best-of-20
ETH/UCY averages (Table 2(b), Average row) are **0.19 / 0.41 m** ADE/FDE for the
full configuration (0.21 / 0.41 with dynamics integration), against
**0.58 / 1.18 m** for Social GAN in the same table [5].

**Social-STGCNN** (CVPR 2020) [6] models pedestrians as a spatio-temporal graph, with a
kernel function that embeds social interactions in the adjacency matrix. It claims a
**20 % FDE improvement**, **8.5× fewer parameters** and **up to 48× faster inference**
than previously reported methods [6]. The deployment lesson is that graph
convolutions over a sparse neighbourhood are cheap enough to run per-camera on edge
hardware. A per-person LSTM with pooling is not.

Why graphs matter for *behaviour*, not just forecasting [derived]. The cues that
separate a commuter crowd from a coordinated group are relational: simultaneous
departure when a train arrives, a stable formation, two people converging on the same
asset from different directions, or a follower keeping a constant 1–2 m gap (the
`Tailgate` behaviour's `gap_m = 1.2`). A per-track classifier sees none of these. A
GNN over the track graph, with edges carrying relative distance, relative velocity and
time-to-closest-approach, sees them directly. Report 19 §3.4 recommends this; it is
the natural successor to `survsim/eval/behaviour.py`.

### 3.5 Transformers on tracks

A Transformer replaces the recurrent state with attention over past timesteps and
over neighbours. Conceptually it generalises both the LSTM (temporal attention) and
social pooling (agent attention). The advantages are parallel training and long
context, which matter for dwell-scale behaviours measured in minutes rather than
3.2 s windows. The risk is the same as everywhere else: it will learn whatever
shortcut the data offers. That is why SurvSim's behaviour data pairs every positive
with a look-alike negative and splits by identity. (No transformer trajectory paper
was fetched this session; treat specific architectures as **[VERIFY]**.)

---

## 4. Crowd models: social force and what SurvSim actually does

### 4.1 Helbing & Molnár's social-force model, from first principles

Intuition: a pedestrian behaves *as if* acted on by forces. One pulls them towards
their desired velocity, one pushes them away from other people, one pushes them away
from walls, and some attract them (shop windows, friends). These are "social forces"
that measure internal motivation, not physical ones. The resulting equations are
nonlinearly coupled Langevin equations [2].

**Driving term** [2]. Each pedestrian α wants to move at speed v_α⁰ in direction
e_α. Deviations relax back over a **relaxation time τ_α**:

    F_α⁰ = (1/τ_α) · (v_α⁰ e_α − v_α)

**Repulsion from others** [2], an exponentially decaying potential in an elliptical
distance b that accounts for the other person's step:

    V_αβ(b) = V⁰_αβ · e^(−b/σ)

**Repulsion from walls** [2]:

    U_αB(‖r_αB‖) = U⁰_αB · e^(−‖r_αB‖/R)

**Field of view** [2]. Forces from behind are weighted down. The weight w is 1 inside
the angle of sight 2φ and **c** outside it.

**Total** [2]: F_α(t) = F_α⁰ + Σ_β F_αβ + Σ_B F_αB + Σ_i F_αi, and a fluctuation
term completes the Langevin form.

**Parameters used in the paper's simulations** [2]:

| Parameter | Value |
|---|---|
| desired speed v⁰ | Gaussian, mean **1.34 m/s**, s.d. **0.26 m/s** |
| max speed | 1.3 v⁰ |
| V⁰_αβ, σ | **2.1 m²/s²**, **0.3 m** |
| U⁰_αB, R | **10 m²/s²**, **0.2 m** |
| relaxation time τ_α | **0.5 s** ("Smaller values of τ_α let the pedestrians walk more aggressive") |
| angle of sight 2φ | **200°**, with out-of-view weight **c = 0.5** |
| Δt (step anticipation) | 2 s |
| walkway width | 10 m |

**Emergent phenomena** [2]. **Lane formation** in counter-flow, where lanes arise from
interaction and not from initial conditions. The number of lanes scales linearly with
walkway width: **N(W) = 0.36 m⁻¹·W + 0.59**, which gives about 4 lanes on the 10 m
walkway. There are also **oscillatory changes of walking direction at narrow
passages**.

Worked number [derived]. A pedestrian walking at 1.34 m/s who is stopped dead by an
obstacle and then released reaches 1 − e⁻¹ ≈ 63 % of desired speed after one τ =
0.5 s, and 95 % after 3τ = 1.5 s. That is why social-force crowds look "springy" in
bottlenecks: momentum is carried through τ.

### 4.2 SurvSim's crowd model versus social force

`survsim/director/crowd.py` is a deliberately cheap *first-order* model. At each tick
the desired velocity points at the goal, at a speed from `speed_for_density` (speed
falls with people/m²). A neighbour push is added with a **linear** falloff inside
3 × `personal_space_m`, and the result is clipped to the speed and assigned *directly*
to velocity. There is no relaxation time and no field-of-view anisotropy. Differences

| Aspect | Helbing & Molnár [2] | `crowd.py` |
|---|---|---|
| Order | 2nd-order (acceleration; momentum via τ) | 1st-order (velocity set each tick) |
| Repulsion | exponential, σ = 0.3 m | linear in distance, cut off at 3 × personal space |
| Anisotropy | 200° sight, c = 0.5 behind | isotropic |
| Walls | explicit U_αB | none in the step function |
| Density–speed | emergent | imposed by `speed_for_density` |

Why the simplification is defensible. Background agents exist to create
**occlusion, density and ID-switch pressure**. They are explicitly marked in the
ground truth as carrying no behaviour labels (docstring of `crowd.py`). Imposing the
density–speed relation directly guarantees that the density asked for is the density
produced. Why it matters when it is *not* defensible: bottleneck oscillation and lane
formation are exactly the patterns a *crowd-anomaly* detector learns as normal. If
counter-flow does not self-organise into lanes in the simulator, a detector trained
there will flag real lanes as anomalous, or will miss a real breakdown of lanes
(a surge precursor). Recommended step [derived]: add τ-relaxation and anisotropy as
an option and validate against N(W) = 0.36W + 0.59 before using the crowd for
crowd-behaviour training.

---

## 5. Video anomaly detection (VAD) from pixels

Three families recur. Each defines "anomaly" differently, and that choice matters more
than the architecture.

### 5.1 Reconstruction: learn to reproduce normal, flag what you can't

Hasan et al. (CVPR 2016) [7] learn a generative model of *regular* motion with an
autoencoder. They use two variants: a fully connected AE on handcrafted
spatio-temporal features, and a **fully convolutional** AE learned end to end [7].
Frames that reconstruct badly are irregular.

Failure mode [derived]. Autoencoders generalise. A big enough AE reconstructs
anomalies well too, especially appearance-simple ones such as a person running. The
reconstruction error then also rises with *nuisance* novelty: new lighting, rain, a
camera bump. That is precisely the degradation that CCTV is full of (see report 20).
On UCF-Crime, Hasan's method scores **50.6 % AUC**, which is chance [1].

### 5.2 Prediction: learn to forecast normal, flag what you can't forecast

Liu et al. (CVPR 2018) [8] predict the *next frame* with a U-Net generator trained
with intensity, gradient, optical-flow and adversarial losses. They score each frame
by the **PSNR** between prediction Î and truth I:

    PSNR(I, Î) = 10·log₁₀( [max Î]² / ((1/N) Σᵢ (Iᵢ − Îᵢ)²) )              [8]

then **min-max normalise PSNR within each test video** into a regular score
S(t) ∈ [0, 1] [8]. Frame-level AUC results [8]:

| Dataset | Liu et al. [8] | Best prior in their table [8] |
|---|---|---|
| CUHK Avenue | 84.9 % | 81.7 % (Stacked RNN) |
| UCSD Ped1 | 83.1 % | 81.8 % (MDT) |
| UCSD Ped2 | 95.4 % | 92.2 % |
| ShanghaiTech | **72.8 %** | 68.0 % (Stacked RNN) |

Dataset facts from [8]: **Avenue** has 16 training and 21 testing videos with 47
abnormal events, including throwing objects, *loitering* and running. **ShanghaiTech**
has 330 training and 107 testing videos with 130 abnormal events across 13 scenes.

Normalising PSNR *per test video* uses that video's own minimum and maximum. This is
information from the future that an online system does not have, and it forces every
test video, even an entirely normal one, to have a frame scoring 0 ("most
anomalous"). The pooled frame-level AUC then mixes scores that were rescaled
differently in every video. A deployed system needs a *global, fixed* threshold, and
per-video normalisation hides how badly that threshold transfers between videos.

### 5.3 Weakly-supervised MIL: Sultani et al. (CVPR 2018)

Motivation. Anomaly annotation at frame level is expensive, but video-level labels
("this clip contains a robbery somewhere") are cheap. **Multiple-instance learning**
treats each video as a *bag* and its segments as *instances* [1]. A positive bag
contains at least one anomalous instance. A negative bag contains none.

Mechanics [1]:
* Each video is divided into **32 non-overlapping temporal segments**, and C3D FC6
  features are averaged per segment.
* A 3-layer MLP (512 → 32 → 1 units) scores each segment.
* **MIL ranking loss with sparsity and smoothness** [1]:

      l(B_a, B_n) = max(0, 1 − max_{i∈B_a} f(V_a^i) + max_{i∈B_n} f(V_n^i))
                    + λ₁ Σ_i (f(V_a^i) − f(V_a^{i+1}))²      ← temporal smoothness
                    + λ₂ Σ_i f(V_a^i)                         ← sparsity

  with **λ₁ = λ₂ = 8 × 10⁻⁵** [1]. Mini-batches contain 30 positive and 30 negative
  bags.

Intuition. The hinge says "the most anomalous segment of an anomalous video should
outscore the most anomalous segment of a normal video by a margin of 1." Using the
*max* over instances is the MIL assumption. Sparsity says anomalies are brief.
Smoothness says scores should not flicker.

**UCF-Crime** (introduced in [1]) has **1,900** long, untrimmed real-world
surveillance videos (**128 hours**) with **13 anomaly classes**: abuse, arrest,
arson, assault, road accident, burglary, explosion, fighting, robbery, shooting,
stealing, shoplifting and vandalism (the paper's own list; its Table 1 excerpt shows
only eight of them) [1]. The training
set has **800 normal + 810 anomalous** videos and the test set **150 normal + 140
anomalous** [1]. Only test videos have temporal annotations, averaged over multiple
annotators [1].

Results (frame-level AUC on UCF-Crime) [1]:

| Method | AUC |
|---|---|
| Binary classifier | 50.0 |
| Hasan et al. (AE) | 50.6 |
| Lu et al. (sparse dictionary) | 65.51 |
| MIL without constraints | 74.44 |
| **MIL with constraints** | **75.41** |

and **false-alarm rate on normal test videos at a 50 % threshold**: Hasan **27.2 %**,
Lu **3.1 %**, proposed **1.9 %** [1]. The paper explicitly notes that *"a major part
of a surveillance video is normal"* and that a robust method needs low false alarms
on normal video [1]. It reports false-alarm causes including darkness, flying insects
in front of the camera, and *sudden people gathering* [1]. Sudden gathering is
the crowd-dynamics hard negative again.

### 5.4 XD-Violence: audio plus video, and AP instead of AUC

Wu et al. (ECCV 2020) [9] released **XD-Violence**: **4,754 untrimmed videos, 217
hours, with audio and weak labels**, covering six classes (**abuse, car accident,
explosion, fighting, riot, shooting**) [9]. They report **frame-level AP** (area
under the precision–recall curve) *"rather than … ROC … AUC since AUC usually shows
an optimistic result when dealing with class-imbalanced data"* [9]. Their method
reaches **78.64 AP** versus **73.20** for the Sultani baseline, and **82.44 AUC** on
UCF-Crime [9]. Adding audio gives clear per-class boosts for shooting, riot and car
accident [9]. That is a direct argument for the audio sensor in `survsim/sensors/`,
since those are exactly the events with loud acoustic signatures.

### 5.5 Where the pixel families sit relative to behaviour rules [derived]

| | Rules on tracks | Sequence / graph models on tracks | Pixel VAD (AE / prediction / MIL) |
|---|---|---|---|
| Notion of "anomaly" | protocol-defined event | learned normal motion or supervised class | unusual pixels / weak-label ranking |
| Needs tracking | yes | yes | no |
| Explainable to operator | high | medium | low |
| Robust to degradation | inherits tracker's | inherits tracker's | poor (nuisance novelty looks anomalous) |
| Can express "loiter vs commute" | no (§2.2) | yes, with the right features | only if context is in frame |
| Output | timed alarm | timed alarm / score | per-frame score (needs a temporal policy to become alarms) |

The last row matters most. A per-frame score is **not an alarm**. Turning it into one
needs smoothing, hysteresis, a minimum duration and a refractory period. None of that
is evaluated by frame-level AUC, and all of it determines false alarms per
camera-hour.

---

## 6. Why the benchmark metrics mislead

### 6.1 Frame-level AUC, precisely

Frame-level AUC treats every frame as an independent sample. A frame is positive if
any pixel is annotated anomalous, and the ROC is swept over thresholds [10]. It is
the probability that a random anomalous frame outscores a random normal frame
[derived; standard ROC interpretation].

Ramachandra, Jones and Vatsavai's survey [10] documents the flaws:
* The frame-level criterion *"does not evaluate whether any spatial localization has
  been achieved"*. The original authors recommended against using it alone [10].
* Widely used code computed pixel-level AUCs *higher* than frame-level AUCs, *"which
  is not possible since frame-level AUC imposes an upper bound on pixel-level AUC"*
  [10].
* The small benchmarks are **saturated** (frame-level AUC > 99 % on UMN for years),
  and the criteria *"clearly have serious flaws"* [10].
* Replacement criteria: **region-based (RBDR)** and **track-based (TBDR)** detection
  rates (the survey's own abbreviations), which count true positives per anomalous region or track and false
  positives per frame. They are claimed to give *"a much more realistic picture of how
  an algorithm will perform in practice"* [10].

Flaws the survey does not stress but an operator would [derived]:
1. **No latency.** An alarm 5 minutes after the robbery started contributes frames to
   the TPR just like an alarm at 1 s. Under i-LIDS [11] it is a *false alarm*.
2. **Chatter is free.** A detector that flickers on and off 40 times over one event
   earns full credit. i-LIDS disregards repeats in the window, and `alarms.py`
   (default mode) charges them as false positives.
3. **Imbalance hides the operating point.** Consider a test set with 5 % anomalous
   frames. AUC is invariant to class prior, but the *precision* of a threshold is not.
   This is XD-Violence's argument for AP [9].
4. **Pooled across videos with per-video normalisation** (§5.2), the frame-level score
   is not the score any deployed threshold would see.

### 6.2 From "1.9 % false-alarm rate" to alarms per camera-hour [derived]

Sultani's best system has a 1.9 % false-alarm rate on normal video [1]. How many false
alarms is that? The paper's rate is per *frame* (or per segment) at a 0.5 threshold,
so the answer depends on how frames become alarms. Take the most generous alarm
policy: coalesce consecutive positive frames and charge at most one alarm per 5 s
window, as i-LIDS does [11]. An hour has 720 such windows. If a positive frame in a
window triggers an alarm, and the 1.9 % of positive frames were spread evenly, then
up to 720 × (1 − (1 − 0.019)^(5·30)) windows fire at 30 fps. That is nearly all of
them, because 150 frames per window at 1.9 % each gives a 94 % chance of at least one
positive. If instead false positives are *clustered* (a dark scene, an insect), the
count could be a handful. **The frame-level rate is uninformative about the
operational rate within about two orders of magnitude.** The temporal structure of the
errors decides it, and that is why SurvSim scores events.

### 6.3 The ActEV bridge

ActEV's RateFA is *false alarms per minute of video* [13]. To convert to per
camera-hour, multiply by 60 [derived]. RateFA = 0.1/min is **6 false alarms per
camera-hour**. That is the figure `survsim/eval/alarms.py`'s docstring calls the
research operating point, and it is where the "three orders of magnitude" comparison
in report 19 comes from.

---


### 7.1 The budget [derived; staffing assumptions flagged]

Let
* K = cameras per operator,
* A = nuisance alarms an operator can absorb per shift without starting to ignore the
  system,
* H = shift length in hours.

Then the per-camera budget is

    B = A / (K · H)     false alarms per camera-hour.

`AlarmScore.operator_verdict` in `survsim/eval/alarms.py` hard-codes A = 4, H = 8
and K = 500 by default, so

    B = 4 / (500 · 8) = 0.001 per camera-hour ≈ one false alarm per camera per 42 days.

(An earlier module docstring said "roughly 0.005" while the code's formula gives
**0.001**, a 5× text error. It has since been fixed: the docstring now cites
`DEFAULT_BUDGET_FA_PER_CAMERA_HOUR` (0.001), and a comment records the fix. Still a
nuisance alarms per operator-hour at 1 operator per 50 cameras, giving
**0.12 per camera-hour**. The A, K and H figures are assumptions, not sourced
numbers; D06 discusses operator ratios, and they should be presented as **[VERIFY]**
ranges.

The budget spans **0.001 (assumed, 28 §6) to 0.12** depending on staffing. A research operating point
of 6 per camera-hour (§6.3) is **50× to 6,000× over our assumed budget** [derived].

**Measured, not derived (H12, `9dea4f9`).** SurvSim's own loiter rules on 3,002
clean mock camera-hours (676 worlds, 74,989 innocent people, zero loiterers,
perfect tracks): dwell_60 **4.55**, dwell_25 **6.01**, path_loiter_25 **20.7**,
path_loiter_15 **87.4** FA/cam-h — **4,500–87,000× the assumed 0.001 budget** (Garwood
95 % CIs ±1–2 %; a world-cluster bootstrap is ~3× wider because false alarms
cluster by world). dwell_25 lands almost exactly on the ActEV-like 6/cam-h
point above. i-LIDS 5 s coalescing cuts 7–59 %. This supersedes H5's
0.35-camera-hour estimate (11–143 FA/cam-h).

**The best rule so far (H58 round 2, `44e34f5`; doc 58 §6).** A
`LearnedLoiterRule` on track features, retrained after the zone-centroid leak
fix (`473ace3`): **3.745 FA/cam-h [3.676, 3.815]** (round 2; superseded by round-3 A1 2.915 / 0.825, `bcbe9d2`) on the same 3,002 clean
cam-h, actor-aware recall@30 s **0.831 [0.792, 0.869]**, precision 0.326,
recall@10 s 0.097 — 1.60× fewer false alarms than dwell_25 (round 1 said
2.06×) and still ~3,700× over our assumed 0.001, ≈ 1.25 operators of dismissals at 40
cameras × 30 s per check. The label oracle reaches recall 1.000; the
motion-only kinematic-twin floor is 1.008 FA/cam-h. **Scoring lesson:**
matching alarms to event *windows* instead of *people* credited dwell rules
for alarms on bystanders — actor-aware, dwell_25's recall is 0.367 (not
0.90) and dwell_60's is 0.000. Loiter rules are scored `actor_aware=True`
from here on.

### 7.2 Base rates: why precision collapses [derived]

Suppose a real suspicious event (a genuine loiter or tamper) happens at rate
λ = 0.01 per camera-hour, or once per camera per ~4 days. Suppose the detector has
recall R = 0.9 at a false-alarm rate F per camera-hour. Precision is

    P = R·λ / (R·λ + F).

* At F = 6 (research): P = 0.009 / 6.009 ≈ **0.15 %**. About 1 alarm in 670 is real.
* At F = 0.12 (the gentler budget): P = 0.009 / 0.129 ≈ **7 %**.
* At F = 0.001 (`alarms.py` default): P = 0.009 / 0.010 ≈ **90 %**.
* H12's dwell_25 (F = 6.01): with the window-only R = 0.90, P ≈ **0.15 %** — the
  research row above, measured; with its honest actor-aware R = 0.367, P ≈
  **0.06 %**.
* The shipped round-3 A1 learned rule (R = 0.825 actor-aware, F = 2.915): P ≈ **0.28 %**
  — better, and still about 1 true alarm in 350 (the superseded round-2 refit, F = 3.745, gave 0.22 %).

Only at the tight end is an alarm more likely true than false. This is Bayes' rule
wearing a security uniform, and it explains why operators disable analytics: with
P ≈ 0.15 %, the rational response to any alarm is to ignore it.

Consequence for evaluation: **precision measured on a benchmark is meaningless unless
the benchmark's base rate matches the site's.** UCF-Crime's test set is roughly half
anomalous videos (140 of 290) [1]. A real camera's footage is anomalous a vanishing
fraction of the time. SurvSim's `survsim/director/anomaly.py` makes the base rate an
explicit parameter: events are scheduled as a **Poisson process** at a configured rate
(e.g. "0.5 suspicious events per camera-hour"). It refuses to manufacture events when
the rate implies zero, and it **scales hard negatives with positives**, so precision
has "a defensible denominator" (module docstring).

### 7.3 Hard negatives dominate the false-alarm count [derived]

Take a 100-camera transit site, 24 h/day. Suppose platform cameras see about 20
commuters per camera-hour waiting at least 2 minutes (an assumption). A dwell rule
with T = 120 s fires on about 90 % of them (§2.2). That is roughly 18 false alarms
per platform camera-hour, 150× over the gentler 0.12 budget (18,000× over the
0.001 default), *from perfect tracks*. The
learned classifier's job is not "better detection". It is removing that 18 while
keeping recall. H12 measured it: commute waits and queues are ≥ 90 % of
DwellRule's false alarms on 3,002 camera-hours; for PathLoiterRule the largest
cause is plain transit (54 % of path_loiter_15's, because its 15 s re-entry
gap ≥ its 15 s threshold lets every walker reach the threshold). This is why CLAUDE.md principle 3 says hard negatives are as important
as positives: they set the denominator of the metric that decides whether the product
is switched on.

### 7.4 The detection window (`--tolerance-s`) and the dwell threshold (`--threshold-s`)

These are two *different* knobs in `survsim eval` (`survsim/cli.py`), and they are
often confused.

* `--threshold-s` (default 60) is the **dwell rule's** T, a parameter of the *system
  under test*.
* `--tolerance-s` (default 10) is the **i-LIDS detection window**, a parameter of the
  *evaluation protocol*. `score()` counts an alarm as a hit only if
  `t_start ≤ alarm.t ≤ t_start + tolerance_s`. Correct-but-late alarms become false
  positives. Each event can be detected once. In default mode repeats are charged as
  false positives. `ilids_compat=True` switches to the i-LIDS rules: repeats inside a
  matched window are disregarded and false positives are coalesced to one per 5 s,
  reproducing [11].

The interaction [derived]. A `Loiter` label starts at behaviour onset, but a dwell
rule with T = 60 s *cannot* fire before onset + 60 s. With tolerance 10 s, every
loiter is therefore "missed" and every rule firing is a false positive, unless the
truth onset is defined as the moment the event becomes *detectable* (onset + T_loiter),
which is how i-LIDS defines its events (e.g. "over sixty seconds after they left")
[11]. CLAUDE.md's suggested `survsim eval out/run --threshold-s 25` is one way to see
this: shrinking T moves firings into the window at the cost of firing on shorter
innocent dwells. Report 19 §5.1 lists `detectable_from` per camera as a gap. This
section is the arithmetic reason it matters.

---

## 8. Scene understanding as context

Behaviour is only suspicious *relative to a scene*. The same dwell is normal on a
platform, a smoke-break spot or a queue, and suspicious at a perimeter fence or next
to a camera pole. Scene understanding supplies that context in four ways:

1. **Semantic zones** (platform, gate, restricted, asset). `DwellRule` uses zone tags,
   and the learned model uses `zone_revisits` and `n_zones_visited`. Trajectron++'s
   map encoding is the learned version of the same idea [5].
2. **Schedules** (train arrivals, shift changes). These explain synchronised
   departures and arrivals, which are the strongest single cue for `commute_wait`
   [derived].
3. **Occupancy and density.** Social-force parameters change with density, and
   Sultani's false alarms on "sudden people gathering" [1] show what happens without
   density context.
4. **Camera state.** A tampered or slewed camera changes what "normal pixels" look
   like. Pixel VAD (§5.1–5.2) will flag the tamper *and* every subsequent frame, while
   a track-level model keyed to world coordinates will not. CLAUDE.md principle 2
   (ground truth follows the live camera) is what lets SurvSim score this correctly.

---

## 9. What SurvSim contributes that benchmarks cannot [derived]

| Benchmark limitation | SurvSim mechanism |
|---|---|
| Frame-level AUC, no latency | `alarms.score` with i-LIDS timing; `--tolerance-s` |
| Unknown or unrealistic base rate | `anomaly.py` Poisson rate with scaled hard negatives |
| Few hard negatives, so precision untestable | catalogue pairs (`commute_wait` ↔ `loiter`, `maintenance` ↔ tamper) |
| Protocol-specific labels (i-LIDS vs PETS) | world-truth owner positions, so any definition's onset can be recomputed |
| Rule errors confounded with tracker errors | rules run on perfect tracks first (`rules.py`), then on perception output |
| Appearance shortcuts / profiling | trajectory-only features, identity-disjoint splits (`behaviour.py`) |
| Crowd realism | density-controlled background crowd (`crowd.py`); social-force upgrade recommended (§4.2) |

Honest limits: the mock backend's top-down output is not something a pixel VAD model
can meaningfully consume (CLAUDE.md "Not yet"). Pixel-family evaluation therefore
waits on Unreal renders, while track-level evaluation is available today.

---


**Q: Rule or model for loitering?** Both, layered. The rule gives explainable,
configurable candidates. A trajectory model with context (zone, schedule, group
features) suppresses the hard negatives. The rule alone cannot work because dwell
time is identical for commuters and loiterers (§2.2).

**Q: Your VAD model has 85 % AUC on Avenue. Ship it?** Not on that evidence. Ask for
false alarms per camera-hour at a fixed recall, with an i-LIDS-style 10 s window, on
footage with the site's base rate. Frame AUC ignores latency and chatter, and
per-video normalisation hides threshold transfer (§5.2, §6.1).

**Q: Explain MIL for anomaly detection.** Video-level labels, 32 segments per video as
instances, hinge on the max-scoring segment of positive versus negative bags, plus
smoothness and sparsity. It reaches 75.4 % AUC on UCF-Crime against 50.6 % for an
autoencoder, and 1.9 % false alarms on normal video [1].

**Q: Why does Social-LSTM matter if it barely beats constant velocity?** It introduced
the right *structure* (agent interaction via pooling). Its numbers taught the field
that single-sample ADE is dominated by inherent multimodality. That led to generative
models with best-of-N, and then to calibrated likelihoods (KDE NLL, Trajectron++)
[3][4][5].

**Q: What's τ in the social-force model, and what does it do?** The relaxation time
towards desired velocity, 0.5 s in Helbing & Molnár. Smaller τ gives more aggressive
walkers. It produces momentum, and with it bottleneck oscillations and lane formation
[2].

**Q: How many false alarms can a control room tolerate?** Derive it: B = A/(K·H).
4 per 8-hour shift at 500 cameras per operator is 0.001 per camera-hour; 6 per hour
at 50 cameras is 0.12. Research operating points (~6 per camera-hour, ActEV
RateFA 0.1/min) are 50× to 6,000× over (§7.1). Measured: SurvSim's loiter rules on
3,002 clean camera-hours are 4,500–87,000× over our assumed 0.001 (H12).

---


* **Open with the operator, not the model.** "A behaviour alarm is judged by someone
  who can absorb a few bad alarms a shift across hundreds of cameras. So I start from
  false alarms per camera-hour, and at i-LIDS-style timing a late alarm counts as a
  false alarm."
* **Name the hard negative.** "Dwell time can't separate a commuter from a loiterer.
  In our simulator, `CommuteWait` literally inherits `Loiter`'s motion; only the label
  differs. So the fix is context and relational features, not a better threshold."
* **Be precise about metrics.** "Frame-level AUC has no notion of latency or chatter,
  and prediction-based methods normalise scores per test video, which a live system
  can't do. XD-Violence moved to AP because of imbalance. I'd report P_miss at a fixed
  false-alarm rate, converted to per camera-hour."
* **Show the arithmetic.** "At a 1-in-100-hours base rate and 90 % recall, 6 false
  alarms per camera-hour means about 0.15 % precision. You need to get near 0.001 per
  camera-hour before an alarm is more likely real than not."
* **Place the models.** "Rules for explainable candidates. Graph or sequence models on
  tracks for intent and group context. Pixel anomaly detectors as a
  catch-what-we-didn't-define layer, gated by corroboration, because they fire on
  nuisance novelty such as weather and camera bumps."
* **Close with the simulator's role.** "Real CCTV can't give you onset times under
  both i-LIDS and PETS definitions, a controlled base rate, or matched innocent
  look-alikes. A simulator can, and that's what makes precision and time-to-alarm
  measurable."

---

## References

All of the following were fetched this session. Where the abstract page lacked
detail, the PDF was downloaded and text-extracted.

1. W. Sultani, C. Chen, M. Shah, "Real-world Anomaly Detection in Surveillance
   Videos," CVPR 2018. https://arxiv.org/abs/1801.04264 (PDF
   https://arxiv.org/pdf/1801.04264). *Taken:* 1,900 videos, 128 h, 13 classes;
   800+810 train and 150+140 test split; 32 segments; C3D FC6; MLP 512-32-1; MIL
   ranking loss with smoothness and sparsity, λ₁ = λ₂ = 8e-5; 30+30 bag mini-batches;
   AUC table (50.0 / 50.6 / 65.51 / 74.44 / 75.41); false-alarm rates on normal video
   27.2 / 3.1 / 1.9 %; false-alarm causes.
2. D. Helbing, P. Molnár, "Social force model for pedestrian dynamics," Phys. Rev. E
   51, 4282 (1995). https://arxiv.org/abs/cond-mat/9805244 (PDF). *Taken:* force
   decomposition, Langevin framing, exponential potentials, all parameter values
   (1.34 ± 0.26 m/s, V⁰ = 2.1, σ = 0.3 m, U⁰ = 10, R = 0.2 m, τ = 0.5 s, 200°,
   c = 0.5, Δt = 2 s, 10 m walkway), lane formation, N(W) = 0.36W + 0.59, bottleneck
   oscillations.
3. A. Alahi et al., "Social LSTM: Human Trajectory Prediction in Crowded Spaces,"
   CVPR 2016. https://cvgl.stanford.edu/papers/CVPR16_Social_LSTM.pdf *Taken:* one
   LSTM per trajectory; social pooling as an N_o×N_o×D grid tensor of neighbour hidden
   states; no extra parameters; bivariate Gaussian output; ETH and UCY evaluation.
4. A. Gupta et al., "Social GAN: Socially Acceptable Trajectories with Generative
   Adversarial Networks," CVPR 2018. https://arxiv.org/abs/1803.10892 (PDF).
   *Taken:* variety loss (min over k); ADE/FDE definitions; 8-step (3.2 s) observe and
   8/12-step (3.2/4.8 s) predict; leave-one-out over five ETH/UCY scenes; Table 1
   averages (cell mapping marked VERIFY).
5. T. Salzmann et al., "Trajectron++: Dynamically-Feasible Trajectory Forecasting With
   Heterogeneous Data," ECCV 2020. https://arxiv.org/abs/2001.03093 (PDF). *Taken:*
   graph-structured recurrent model, CVAE multimodality, dynamics integration, map and
   robot-future encoding, ETH/UCY leave-one-out plus nuScenes, metrics (ADE, FDE,
   KDE NLL, best-of-N), "60% lower average prediction error" claim.
6. A. Mohamed et al., "Social-STGCNN," CVPR 2020. https://arxiv.org/abs/2002.11927
   (abstract). *Taken:* graph formulation with a kernel adjacency, 20 % FDE
   improvement, 8.5× fewer parameters, up to 48× faster inference.
7. M. Hasan et al., "Learning Temporal Regularity in Video Sequences," CVPR 2016.
   https://arxiv.org/abs/1604.04574 (abstract). *Taken:* fully connected AE on
   handcrafted features and fully convolutional AE; generative model of regular
   motion.
8. W. Liu, W. Luo, D. Lian, S. Gao, "Future Frame Prediction for Anomaly Detection – A
   New Baseline," CVPR 2018. https://arxiv.org/abs/1712.09867 (PDF). *Taken:* PSNR
   score formula; per-video min-max normalisation; frame-level AUC protocol; Table 1
   (Avenue 84.9, Ped1 83.1, Ped2 95.4, ShanghaiTech 72.8; best prior Avenue 81.7 Stacked RNN);
   Avenue 16/21 videos with 47 events including loitering; ShanghaiTech 330/107
   videos, 130 events, 13 scenes.
9. P. Wu et al., "Not only Look, but also Listen: Learning Multimodal Violence
   Detection under Weak Supervision," ECCV 2020. https://arxiv.org/abs/2007.04687
   (PDF). *Taken:* 4,754 videos, 217 h, audio, weak labels, 6 classes; AP rather than
   AUC because of imbalance; 78.64 vs 73.20 AP; 82.44 AUC on UCF-Crime; audio helps
   shooting, riot and car accident.
10. B. Ramachandra, M. Jones, R. R. Vatsavai, "A Survey of Single-Scene Video Anomaly
    Detection," IEEE TPAMI 2020. https://arxiv.org/abs/2004.05993 (PDF). *Taken:*
    frame-level and pixel-level criteria definitions and flaws; the buggy pixel-AUC
    code; UMN saturation above 99 %; RBDR/TBDR proposal.
11. Home Office CAST, "Imagery Library for Intelligent Detection Systems: The i-LIDS
    User Guide," Publication 10/11.
    https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/143875/ilids-user-guide.pdf
    *Taken:* scenario list; the 60 s parked-vehicle example; abandoned-object
    definition (Appendix F); the 10 s window, disregarded repeats, one false positive
    per 5 s, no continuous alarming, separate alarms for simultaneous events; the r, p
    and recall-bias F-measure; α values (abandoned baggage 0.35 / 35, parked vehicle
    0.55 / 60); pass thresholds not public.
12. E. Auvinet et al., "Left-luggage detection using homographies and simple
    heuristics," PETS 2006 workshop. https://www.egdn.net/mypubs/Auvinetal06PETS.pdf
    *Taken:* PETS 2006 context (railway station, BTP and Network Rail, seven
    multi-camera sequences); abandonment defined as owner beyond 300 cm for 30 s; the
    warning/alarm two-stage implementation.
13. NIST, "ActEV 2018 Evaluation Plan (draft)."
    https://actev.nist.gov/pub/Draft_ActEV_2018_EvaluationPlan.pdf *Taken:* activity
    definition; activity names; VIRAT source; the P_miss(τ) and RateFA(τ) formulas,
    with RateFA per minute of video; P_miss@RateFA as the primary measure.

**Repo files read this session:** `survsim/eval/alarms.py`, `survsim/eval/rules.py`,
`survsim/eval/behaviour.py`, `survsim/director/behaviours.py`,
`survsim/director/crowd.py`, `survsim/director/anomaly.py`, `survsim/cli.py`
(`eval` command), `docs/03_BEHAVIOUR_CATALOG.md`,
`docs/research/19_BEHAVIOUR_INTENT_ANALYTICS.md` (§5).
