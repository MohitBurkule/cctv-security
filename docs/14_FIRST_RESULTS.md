# 14 · First measured results on generated data

Everything here was produced by the repo on its own generated scenes, using the
mock backend (perfect tracking, no perception error). That matters for reading
the numbers: these are the errors the **behaviour layer** makes when detection
and tracking are flawless. A real system's numbers can only be worse.

---

## 1. A single scene cannot support behaviour learning

First attempt: train the trajectory classifier on one 240 s scene
(`disguise_and_tamper`), splitting train/test by identity.

| | value |
|---|---|
| segments | 264 |
| suspicious segments | 56 |
| **distinct suspicious identities** | **3** |
| AUC | **0.46** — worse than chance |

The model was useless, and the cause was not the model. Identity-disjoint
splitting is mandatory (otherwise the model memorises individuals and every score
inflates), but with three suspicious identities the training half holds perhaps
two, and the test half contains a person the model has never seen behaving
suspiciously. There is nothing to generalise from.

**Lesson:** behaviour work needs *many scenes*, not a longer scene. Extending the
same scene adds segments but no new identities, so it cannot fix this. This is
precisely what the batch generator exists for.

## 2. Identity diversity fixes discrimination

Same features, same model, trained across **10 generated scenes**:

| | one scene | ten scenes |
|---|---|---|
| segments | 264 | 5,580 |
| distinct suspicious identities | 3 | **18** |
| **AUC** | 0.46 | **0.72** |
| recall | 0.44 | 0.72 |

Discrimination becomes real once the model sees enough different people behaving
suspiciously in different sites.

## 3. …but precision collapses anyway, exactly as the field reports

| model | precision | recall | F1 |
|---|---|---|---|
| dwell-time rule (`dwell ≥ 20 s`) | 0.018 | 0.241 | 0.034 |
| learned trajectory classifier | **0.074** | **0.722** | 0.134 |

The learned model beats the rule roughly **4× on precision and 3× on recall** —
trajectory *shape* genuinely separates pacing from waiting, which dwell time
cannot. And it is still unusable: at 0.074 precision, **93% of alarms are false**.

The reason is the base rate, not the classifier. Suspicious segments are
184 of 5,580 — **3.3%** of the data. At that prevalence even a good classifier
produces mostly false positives, and the hard-negative false-alarm rate (0.295)
shows nearly a third of innocent waiting people still trigger it.

This reproduces, on our own data and with *perfect tracking*, the central finding
of the research corpus (R03, H02): the gap between research operating points and
control-room reality is an **architecture** problem — verification, corroboration,
and alarm budgeting — not something a better classifier closes. A vendor demoing
"AUC 0.72 behaviour detection" is quoting the number that flatters them.

## 4. What the model actually learned

Standardised weights, largest first:

```
dwell_fraction      -1.88
direction_changes   -1.64
radius_of_gyration  -1.48
max_speed           +0.56
```

Readable, and arguable with a domain expert — which is the point of keeping the
baseline linear. The signs are informative: in this scene mix, *suspicious*
segments involve **more** movement and wider spatial spread (recon, perimeter
probing, intrusion), while standing still is associated with innocent waiting.
That is the opposite of the loitering stereotype the dwell rule encodes, and it is
a direct consequence of the scenario mix — a different site profile would move
these weights, which is itself a reason to report them.

## 5. How to read these numbers honestly

- **Mock backend, perfect tracking.** No missed detections, no identity switches,
  no occlusion. Real perception error compounds on top.
- **Thresholds untuned.** Precision/recall trade could be moved; the operating
  point was not selected to flatter either method.
- **Scenario mix drives the labels.** These generated scenes are incident-dense
  compared with a real site, where the base rate would be far lower still — which
  makes the precision problem *worse*, not better.

## 6. The architecture rescues the unusable detector

Same classifier, same data, four architectures. Each stage from `eval/pipeline.py`
was added cumulatively:

| architecture | alarms | precision | recall | false alarms/camera-hour |
|---|---|---|---|---|
| raw detector | 114 | 0.026 | 0.500 | 27.75 |
| + threshold 0.8 | 35 | 0.086 | 0.500 | 8.00 |
| + persistence (2 in 60 s) | 6 | 0.333 | 0.333 | **1.00** |
| + corroboration (RF must agree) | 2 | **0.500** | 0.167 | **0.25** |

**Precision improves 19×** (0.026 → 0.500) and the **false-alarm rate falls 111×**
(27.75 → 0.25 per camera-hour) — without touching the model.

The cost is explicit and must not be hidden: **recall falls from 0.50 to 0.17**.
Two of every three events the detector could have caught are deliberately
discarded to make the remainder credible. Whether that trade is right is a
customer decision about which failure hurts more, and the pipeline reports each
stage's drop count so the decision is made with numbers rather than vibes.

Two honest caveats on this table:
- Corroboration here uses a *simulated* RF channel with favourable independence.
  `eval/fusion.py` shows that correlated nuisance (wind, rain, vehicles tripping
  both sensors) destroys most of this gain, so the real-site number depends on an
  empirical independence check.
- Recall is computed against one truth event per suspicious identity; a different
  event definition moves the absolute values, though not the direction.

## 7. What this implies for the roadmap

1. Behaviour experiments must run over **batches of scenes**, and any result from
   a single scene should be treated as unmeasured.
2. The interesting question is not "can a model classify behaviour" — at AUC 0.72
   with 7% precision, the answer is "not usefully alone". It is **what
   architecture makes the alarm rate survivable**: corroboration across sensors,
   verification before escalation, per-rule alarm budgets.
3. That makes `eval/pipeline.py`, `eval/fusion.py` and `eval/alarms.py` the
   load-bearing modules, and it is why they measure false alarms per camera-hour
   against an operator budget rather than reporting F1 alone.
4. The demonstrated 111x false-alarm reduction from architecture alone, versus a
   4x precision gain from replacing a rule with a learned model, is the ratio
   that should drive where effort goes.


---

## 8. Photorealism, measured against real CCTV — and a correction

Twelve real surveillance frames (MOTChallenge sequences) were finally obtainable,
which allowed the realism work to be checked rather than assumed. It immediately
overturned a conclusion reported earlier in this session.

**What I had claimed:** degradation profiles tuned against reasoned-out statistic
ranges moved renders toward realism (scores 0.98-0.99 against those targets).

**What the real frames showed:** the hand-tuned `cctv_day_720p` profile was
*further* from real footage than the undegraded render.

| | distance to real CCTV, in units of the real set's own spread |
|---|---|
| clean UE render | 1.072 |
| hand-tuned profile (reasoned targets) | **1.304 — worse** |
| profile tuned against real frames | **0.858** |

**Why the reasoned targets were wrong.** I assumed CCTV is blurry and clean, so
the targets rewarded softening and penalised noise. Measurement says the opposite:
real frames carry `noise_sigma` around 3.2 where I was producing 1.2, and
`edge_density` around 0.085 where I was producing 0.016. The winning parameter
search chose **zero defocus**. The legacy-4CIF mental model does not describe
modern surveillance footage.

**A metric defect surfaced on the way.** The first distance measure normalised
each statistic by its *mean*, so quantities with near-zero means dominated:
`clipped_fraction` averages 0.017 in real frames, making a 0.017 error a relative
gap of 1.0, while a 200-unit error on `laplacian_var` (mean ~400) scored 0.5.
Optimising against that chased the two smallest quantities and ignored sharpness
and noise entirely — which is exactly what the first parameter search did, and
why it returned a *worse* profile. Distance is now normalised by the real set's
standard deviation, asking how many typical between-frame variations away the
render sits.

**Remaining gaps against real footage**, in order: no blown highlights
(real 0.017, ours 0.000), no crushed shadow (0.021 vs 0.002), and colour too
muted (saturation 58.5 vs 39.5). All three are fixable in the exposure and tone
stages rather than requiring a better renderer.

**Scope caveat:** these reference frames skew toward modern, well-exposed cameras.
They describe *this* reference set, not all CCTV, and a legacy estate would sit
elsewhere. `tools/calibrate_targets.py` regenerates the ranges from any reference
folder, so the targets stay evidence rather than opinion.

---

## 9. The crowd model checked against real footage

`speed_for_density` carried two numbers taken from the pedestrian-planning
literature rather than from measurement: a 1.34 m/s free speed and a 5.4/m² jam
density. `survsim/gait/extract.py` measures them from MOT20 ground truth —
1,476 tracks, 205,996 speed samples across four sequences.

Scale comes from each person's own bounding box: a pedestrian is ~1.7 m, so box
height is a ruler at their own depth, and applying it per-detection absorbs
perspective without a homography.

**Measured fundamental diagram:**

| density (/m²) | mean speed (m/s) | samples |
|---|---|---|
| 0.15 | 0.642 | 29,874 |
| 0.55 | 0.555 | 112,137 |
| 1.15 | 0.475 | 59,263 |
| 2.00 | 0.411 | 4,653 |

**The shape is confirmed.** Fitting `v = v0(1 - d/d_jam)` gives
**d_jam = 4.53/m²** against our assumed 5.40, and the two curves — each
normalised by its own value at 0.15/m² — agree to **within 7%** across the
measured range. Real people slow down as it gets busier at close to the rate we
model. `jam_density` is now a parameter carrying this measurement rather than a
constant buried in a function body; the default stays at the literature value,
because one crowded dataset should not overturn it.

**The free speed is not validated, and cannot be by this method.** The fit
returns 0.640 m/s, less than half the literature figure. That is a property of
the measurement, not of pedestrians: displacement measured in the *image plane*
foreshortens motion along the camera axis, so anyone walking toward or away from
the camera reads slow, and MOT20 ships no calibration to correct it. Shape
survives the bias because it is scale-free; absolute speed does not. Taking
0.64 m/s as a free-speed target would have made every simulated crowd walk at
half pace on the strength of an uncorrected projection.

**Cadence is not recoverable here at all.** MOT boxes are interpolated between
keyframes and smoothed, so the vertical bob that carries step frequency is
mostly annotation artefact. Real gait style needs pose estimation on pixels.

### A bug the measurement caught by contradicting itself

The first run reported MOT20 at **0.149 people/m²** — free-flowing — while
simultaneously measuring shuffling speeds around 0.5 m/s. Those two cannot both
be true, and that is the only reason the error surfaced: density was being
computed over just the cleanly-visible boxes, but a crowd is crowded precisely
*because* its members occlude one another. Counting everyone annotated as a
neighbour, while still requiring a clean box for the speed ruler, moved density
to 0.66/m² and made the diagram monotonic.

A number that is merely wrong survives review. A number that is inconsistent
with another number you also measured does not — which is an argument for
measuring two related quantities rather than one.

---

## 10. Real gait from pose: a crowd is not a slow-motion crowd

§9 measured walking *speed* from bounding boxes and said cadence was not
recoverable from them. `survsim/gait/cadence.py` recovers it from pose
(Keypoint R-CNN on MOT20-01, 200 frames, keypoints attached to **ground-truth**
identities by IoU so a tracking error cannot splice two people's legs into one
gait signal).

| quantity | measured (crowd) | free walking (literature) |
|---|---|---|
| cadence | **123.2 ± 23.8 steps/min** | ~110 |
| step length | **0.392 ± 0.209 m** | ~0.75 |
| speed | 0.797 ± 0.480 m/s | 1.34 |

15 of 49 tracks supported an estimate (coverage 0.31). The refusals are the
design working: cadence needs two confident ankles and roughly lateral motion,
and a crowd supplies neither for most people. A number for those tracks would
have been invented.

**The finding: people in a crowd keep their leg rhythm and halve their step.**
Cadence is *slightly above* the free-walking figure while step length is roughly
half. They do not walk in slow motion.

This is invisible to `speed_for_density`, which only knows speed fell, and it
matters in three places:

- **Animation.** Reaching half speed by playing a walk cycle at half rate
  produces a person in slow motion. No pedestrian does that, and any
  gait-sensitive model would find it obviously synthetic.
- **Gait biometrics.** Cadence is roughly preserved under crowding while speed
  is not, making it the *more stable* identity cue — and therefore the thing a
  deliberate gait change has to defeat.
- **Motion detection.** Limbs keep moving fast while the body barely
  translates, so per-frame motion energy does not fall in proportion to speed.

`crowd.gait_for_density` now returns cadence and step length separately, with
cadence × step length reproducing `speed_for_density` exactly so the three
quantities cannot drift apart.

**Why to trust these numbers:** speed = (cadence/60) × step length is an
identity, and the three independently-derived quantities satisfy it to 1%
(0.805 predicted vs 0.797 measured). Three values constrained by one identity
cannot all be noise and still agree.

---

## 11. FID against real CCTV — and the trap in optimising it

900 real frames against 900 disjoint real frames, degraded in memory, at the
720p our cameras capture. The floor is the **undegraded** comparison: real
against real at exactly the sample size every other comparison uses.

| profile | FID | × floor |
|---|---|---|
| undegraded | 12.93 | 1.00 *(the floor)* |
| `clean` | 13.00 | **1.01** |
| `cctv_day_720p` | 32.81 | 2.54 |
| `cctv_legacy_sd` | 142.71 | 11.0 |
| `cctv_fog_day` | 249.22 | 19.3 |
| `cctv_night_ir` | 425.09 | 32.9 |

`clean` landing at 1.01× **validates the harness**: a profile that should be a
no-op is statistically indistinguishable from real footage, so the pipeline is
not introducing a bias of its own.

### Do not minimise this number

Every degradation scores *worse* than no degradation, and the naive reading —
"so degradation makes us less realistic, turn it off" — is wrong and would
destroy the point of the simulator.

**MOT20 is not degraded CCTV.** It is modern, well-exposed, high-resolution
surveillance footage. So this table measures *distance from clean modern
footage*, and a profile that models fog or a legacy SD camera is **supposed** to
be far from it. Optimising any profile to minimise FID here would converge on
applying no degradation at all.

What the table legitimately supports:

1. the harness is unbiased (`clean` ≈ floor);
2. the profiles are ordered as their physics implies — day 720p < legacy SD <
   fog < night IR — which is a real consistency check on the imaging chain;
3. a magnitude for how far each profile moves an image.

What it cannot support is "which profile is most realistic". That needs
reference footage *of the condition being modelled* — genuinely foggy frames to
judge `cctv_fog_day`. Until then, FID is a **relative** instrument here, and
§8's per-statistic calibration against real frames remains the better guide for
tuning a profile to a target condition.

---

## 12. Gait as a biometric — and the price of a deliberate limp

`Gait.style` was a *label*. It nudged walking speed and nothing else, which
quietly broke three things: `soft_biometrics` (the function that answers "what
survives a disguise") returned body measurements only, omitting the cue
surveillance actually uses; the gait evasion techniques degraded nothing
measurable; and two people walking "normally" were numerically identical, so any
gait matcher scored either perfectly or at chance.

`survsim/gait/signature.py` makes gait six measurable quantities — cadence, step
length, asymmetry, arm swing, sway, stance width — with per-person offsets
derived by hashing the identity, so a person walks the same way on every camera
and in every run.

### Gait ReID, and what a style change costs

300 identities, enrolled clean, observed with measurement noise as a fraction of
between-person spread. Degradation is the drop in rank-1 against the honest
baseline at the same noise level.

| measurement noise | honest rank-1 | limp_L | shuffle | crouch | brisk |
|---|---|---|---|---|---|
| 0.2 | 0.990 | 0.96 | 0.95 | 0.96 | 0.89 |
| 0.4 | 0.703 | 0.94 | 0.93 | 0.94 | 0.85 |
| **0.8** | **0.207** | **0.85** | 0.81 | 0.77 | 0.65 |

**The realistic row is the bottom one.** Published gait recognition on
surveillance-quality, cross-view footage reaches roughly 0.2–0.5 rank-1; the
0.99 at noise 0.2 is a laboratory number and should not be quoted as what gait
recognition does. Any claim made from this table has to name its noise level.

**`evasion.fake_limp` asserts a gait degradation of 0.85. At the realistic
operating point it measures 0.85.** That number was previously an assertion
attached to a technique that changed nothing measurable; it is now a measurement
that happens to confirm the assertion. The agreement is a genuine check on the
taxonomy, but it is confirmation *at one operating point* — at lower noise the
same technique costs 0.96, so the taxonomy's single scalar is really a value
sampled from a curve.

### What this says about relying on gait

- **Gait survives a change of clothes completely.** Nothing in the signature
  references clothing, so a coat swap costs exactly zero. That is the argument
  for carrying gait at all.
- **Gait is the one soft biometric a person can deliberately change.** Height
  and shoulder width are not adjustable; how you walk is. A limp costs an
  attacker nothing and removes ~85% of rank-1.
- **So the two cue families fail in opposite conditions**, and that is the
  actionable point: appearance defeats the person who changes clothes, gait
  defeats the person who does not. A system leaning on either alone is
  defeatable by someone who has worked out which. `soft_biometrics` therefore
  takes `include_gait=False`, so evaluation can ask how much of an
  identification rested on a cue the subject controls.

**Caveat on the style effects.** Cadence and step length for a normal walk are
measured (§10). The per-style multipliers are *argued*, not measured — no public
dataset gives per-style gait parameters for surveillance footage — so they live
in one table (`STYLE_EFFECTS`) where they can be disputed rather than scattered
through the code. The uniformly large degradation across styles reflects that
each style shifts a signature much further than individual variation does, which
is plausible and untested.

---

## 13. Parametric gait, and why mocap clips are not the answer

Two clips were downloaded as candidate gait sources. They are **not** used for
playback, and the reason is the same defect §12 removed, one layer down: a
library "Injured Walk" is one recording of one actor's limp. Driving every
simulated limper from it makes them all move identically, and gait ReID
evaluated on that data measures nothing — matching is either perfect (the clip
is a fingerprint of the style) or chance.

`survsim/gait/synthesis.py` generates motion instead, from the six parameters
that already define a person's `GaitSignature`. Each joint angle is a short
Fourier series over the stride, which is the standard biomechanical description
and gives three things a clip cannot: amplitude and phase are separately
controllable (so `asymmetry` can act on one leg only), the motion is continuous
(sample at any frame rate), and two people with the same style get similar but
distinct curves.

### Two bugs the synthesiser's own checks caught

**The animation did not walk the stride the signature asked for.** Hip angle
relates to step length through a *sine*, so scaling amplitude by
`requested / reference` does not produce the requested step. Measured: 0.65 m
synthesised against 0.75 m requested — a 15% error, with every joint curve still
looking correct, which would have put every rendered person out of step with
their own ground truth. The scale factor is now solved numerically at import, so
it stays right if the harmonics are ever refitted. Normal walks now agree to
0.6%, extreme styles to 6.4% (the residual is the sine's nonlinearity at large
amplitude).

**The knee hyperextended to −17°.** A Fourier series knows nothing about
ligaments. Real knees stop near −5°, so the normal-walk harmonics were producing
a leg that bends backwards. `JOINT_LIMITS` now clamps every joint to its
functional locomotor range — that is the physical behaviour, not a fudge.

### The mocap clips could not be measured, and that is the finding

`tools/measure_mocap_gait.py` was written to extract cadence and asymmetry from
the reference clips and so convert `limp_L`, `crouch` and `drunk` from argued to
measured. It **refuses**, correctly:

| clip | duration | step transitions | verdict |
|---|---|---|---|
| Walking | 1.40 s | 2 | refused |
| Crouched Walking | 1.07 s | 2 | refused |
| Injured Walk | 1.67 s | 4 | measurable, but no baseline |

Library animation clips are **single-stride loops built for looping playback**,
not for measurement. A cadence computed from two transitions is an artefact of
where the loop begins. Since the normal-walk baseline is itself unmeasurable,
every paired effect is refused rather than reported.

A second metric was falsified along the way. Asymmetry was first computed from
the positive versus negative excursion of foot separation, and it returned
**exactly 0.0 for an unmistakable limp** — a metric that cannot see the thing it
exists to measure. A limp is a difference in how long each leg bears weight, so
asymmetry is now measured from step *timing*. The replacement is tested against
a fixture with genuinely unequal half-cycles, after the first fixture turned out
to perturb amplitude while leaving the zero crossings — and therefore the
timing — untouched.

**So `limp_L`, `crouch` and `drunk` remain ARGUED.** Measuring them needs
continuous multi-stride recordings of the same actor in each style, which is
what CASIA-B provides for bag and coat (§13 above) and what library clips do
not. The clips remain useful for *rendering* — a rigged character and a walk to
retarget — just not as evidence.
