# 36 · Neuromorphic sensing and spiking networks for detection and tracking

**Why this file exists.** the vendor's own site describes [vendor product] as a
"Second generation… spiking neural network (SNN)" product and as a "sovereign"
that company may well ask what you think SNNs are good for, how you would
measure them, and how they fit next to a conventional detector and tracker.
technical conversation. The longer history and framework survey is
`D05_spiking_neural_networks_and_neuromorphic.md`.

**Tags.**
* **[F]** read on the cited primary page (arXiv abstract or HTML, publisher
  page, vendor datasheet) during this session, 2026-09-26. The link is next to
  the claim.
* **[CALC]** arithmetic I did from [F] numbers. The inputs are cited, the
  working is shown, and the result is only as good as the inputs.

There are no background-knowledge tags in this file. Every factual claim that
is not my opinion has a fetched source, or it has been removed.

---

## 1. The one-paragraph position

Spiking networks and event cameras win where the input is **sparse in time**,
the power budget is **milliwatts**, and **latency** matters more than top-line
accuracy. They lose on dense, static, high-resolution recognition, where a
quantised CNN on a Jetson is more accurate, easier to train and far better
supported by tools. The honest design is therefore **hybrid**: a spiking or
event-driven front end decides *when* and *where* something changed, and a
conventional detector, tracker and ReID stack decides *what* it is and *who*
it is. I would not claim that SNNs beat CNNs on COCO-style accuracy, although
the gap has narrowed sharply since 2024 (section 4). **[INF]**

The evidence that the gap narrowed matters. SpikeYOLO (ECCV 2024) reports
48.9 % mAP@50:95 on COCO, which is the range of mainstream small detectors, and
it does so as a spiking network
([Luo et al., arXiv:2407.20708](https://arxiv.org/abs/2407.20708)) **[F]**.
So the argument has moved on from "SNNs can't detect". It is now about whether
the claimed energy saving survives contact with real hardware and a real
pipeline.

## 2. Event cameras (DVS): the sensor half

### 2.1 What the sensor does

* Each pixel reports an asynchronous "event" `(x, y, t, polarity)` when its
  log brightness changes past a threshold. There are no frames.
* Gallego et al.'s survey gives the headline properties: temporal resolution
  "in the order of microseconds", dynamic range "140 dB vs. 60 dB" for frame
  cameras, low power, and much less motion blur
  ([arXiv:1904.08405](https://arxiv.org/abs/1904.08405)) **[F]**.
* Detection straight from events works at scale. Prophesee's 1-megapixel
  automotive dataset has 14+ hours of driving and 25 M boxes over cars,
  pedestrians and two-wheelers. The authors report that training "directly
  from raw events is possible, more efficient, and more accurate than passing
  through an intermediate intensity image"
  ([Perot et al., arXiv:2009.13436](https://arxiv.org/abs/2009.13436)) **[F]**.

### 2.2 The sensor and processor on one die

SynSense's **Speck** puts an event sensor and an asynchronous spiking CNN on
the same chip. Its ASYNC 2023 paper reports processing latency of
"3.36 μs for an incoming event" across nine layers, with 327,000 neurons, and
positions it both for "small stand-alone applications" and as "an edge node in
larger systems" ([Richter et al., arXiv:2304.06793](https://arxiv.org/abs/2304.06793)) **[F]**.
The product page quotes **< 2 mW** power and "< 5 ms response"
([SynSense Speck](https://www.synsense.ai/products/speck-2/)) **[F]**.

"Edge node in larger systems" is exactly the phrase that should make a
SAPIENT-literate listener pay attention: an event-camera node that emits a
SAPIENT `DetectionReport` is a legitimate autonomous sensor module (file 37).
**[INF]**

### 2.3 What that means for surveillance **[INF]**

* A static, well-lit perimeter camera watching an empty fence is where DVS is
  strongest. The background produces no events, so a person or a drone
  crossing it stands out, with microsecond timing and no blown highlights from
  headlights or sunrise.
* The weaknesses matter for our use case:
  * A person standing still (a loiterer) **disappears** from a DVS stream,
    because nothing changes at their pixels. This follows directly from the
    change-detection principle in Gallego et al. It is a sensor property, not
    something a better network can fix.
  * Rain, foliage and a moving PTZ head all produce event storms, because
    they all change brightness everywhere.
  * There is no absolute intensity, colour or texture, so appearance ReID is
    much harder.
* For intruder detection that makes DVS a good *cue* sensor or wake-up
  trigger. It cannot replace the CCTV.

### 2.4 Synthetic event data

You can emulate events from ordinary video. **v2e** synthesises "realistic"
DVS events from frames, modelling per-pixel Gaussian threshold variation,
intensity-dependent bandwidth and noise. Its authors report that "a car
detector trained with v2e events shows an average accuracy improvement of
40%" over intensity-based detection at night
([Hu, Liu & Delbruck, arXiv:2006.07722](https://arxiv.org/abs/2006.07722)) **[F]**.

For SurvSim this is the obvious route to an event sensor **[INF]**. Render at
a high frame rate, pass the frames through a v2e-style model, and keep the
Director's ground truth. The one honest caveat is temporal: v2e interpolates
between frames, so true microsecond timing needs high-rate rendering, and on
our 8 GB GPU that means low resolution. Say "that is the next sensor I would
add", not "we have it".

## 3. Training SNNs

| Route | Idea | State of the art (fetched) |
|---|---|---|
| **ANN→SNN conversion** | Train a normal ReLU network, then map activations to firing rates | Rueckauer et al. converted VGG-16 and Inception-v3 for the first time, reporting 0.56 % MNIST error and 11.18 % CIFAR-10 error, and showing SNNs can trade error for operations ([Frontiers 2017](https://www.frontiersin.org/articles/10.3389/fnins.2017.00682/full)) **[F]**. The classical cost was many timesteps. Bu et al. replace ReLU with a "quantization clip-floor-shift" activation and reach high accuracy with **4 time-steps** on CIFAR and ImageNet ([arXiv:2303.04347](https://arxiv.org/abs/2303.04347)) **[F]** |
| **Surrogate gradients** | Backpropagation through time, with the non-differentiable spike replaced by a smooth pseudo-derivative | Neftci, Mostafa & Zenke call it "a particularly flexible and efficient method" ([arXiv:1901.09948](https://arxiv.org/abs/1901.09948)) **[F]**. SpikeYOLO's integer-valued training is a descendant of this route (section 4) **[F]** |
| **Local rules (STDP)** | Hebbian, unsupervised | Diehl & Cook reached 95.0 % on MNIST with 6,400 excitatory neurons, fully unsupervised ([Frontiers 2015](https://www.frontiersin.org/articles/10.3389/fncom.2015.00099/full)) **[F]**. That is an elegant result, but it is MNIST. There is no competitive STDP-trained detector among the sources I fetched **[INF]** |

bit-width. Four timesteps with integer-valued spikes looks a lot like a 2–3-bit
quantised network run four times. That is why modern SNN results look so much
better than 2019 ones. It is also why the energy comparison has to be made
against an INT8 or INT4 CNN, not against FP32.

## 4. Detection with spiking networks

### 4.1 From Spiking-YOLO to SpikeYOLO

* **Spiking-YOLO (2019)** was the first SNN object detector. It reached "up
  to 98 %" of Tiny YOLO's accuracy on VOC/COCO at roughly **280× less energy**
  *on neuromorphic hardware (estimated)*
  ([Kim et al., arXiv:1903.06530](https://arxiv.org/abs/1903.06530)) **[F]**.
  The caveats to say out loud: the baseline is **Tiny** YOLO, and the energy
  figure comes from operation counts, not a measurement on a board. **[INF]**
* **SpikeYOLO (ECCV 2024)** simplifies YOLO, adds "meta SNN blocks", and uses
  a neuron that "activates Integer values during training while maintaining
  spike-driven" inference by expanding virtual timesteps. It reports **66.2 %
  mAP@50 and 48.9 % mAP@50:95 on COCO**, +15.0 and +18.7 points over the
  previous SNN state of the art. On the event-camera Gen1 dataset it reports
  67.2 % mAP@50, 2.5 points *above* an equivalent ANN, with 5.7× energy
  efficiency ([Luo et al., arXiv:2407.20708](https://arxiv.org/abs/2407.20708)) **[F]**.

### 4.2 How the energy numbers are computed (and why that matters)

SpikeYOLO's energy section is explicit about its method
([arXiv:2407.20708 HTML](https://arxiv.org/html/2407.20708)) **[F]**:

* It assumes 45 nm costs of **E_MAC = 4.6 pJ** per multiply-accumulate and
  **E_AC = 0.9 pJ** per accumulate.
* ANN energy is `O² · C_in · C_out · k² · E_MAC` summed over layers.
* SNN energy is `(T · D) · fr · O² · C_in · C_out · k² · E_AC`, where T is the
  timestep count, D the maximum integer activation, and fr the firing rate.
* Its COCO table (Table 1) then gives **YOLOv5 (ANN), 21.2 M parameters:
  112.5 mJ, 64.1 % mAP@50 / 45.4 % mAP@50:95** against two SpikeYOLO rows that
  matter: the **headline model, 68.8 M parameters, T×D = 1×4: 84.2 mJ, 66.2 %
  mAP@50 / 48.9 %**, and the **size-matched model, 23.1 M parameters, T×D =
  1×4: 34.6 mJ, 62.3 % / 45.5 %**. (Audit 2026-09-26: an earlier version gave
  the headline model 23.1 M parameters; it is 68.8 M.)

**Read that carefully [INF].** On SpikeYOLO's *own* accounting the headline
model saves about 25 % against YOLOv5 while being ~3× larger; the size-matched
23.1 M model saves about 3× (112.5 → 34.6 mJ) but gives up ~2 points of mAP@50
against YOLOv5. Either way it is single-digit multiples, not 100×. The multi-hundred-times
figures in older papers came from comparing against FP32 MACs on
unrealistically sparse inputs. These are also *theoretical 45 nm operation
energies*. They leave out memory traffic, which dominates real accelerators,
and they are not board measurements.

## 5. Hardware

| Chip | What it is (fetched) | Note |
|---|---|---|
| **Intel Loihi 2** | Second-generation research chip, "up to 10x faster" than Loihi 1, with the open-source Lava framework. **Hala Point** has 1.15 billion neurons. Kapoho Point is an 8-chip stackable board ([Intel](https://www.intel.com/content/www/us/en/research/neuromorphic-computing.html)) **[F]** | A research processor; Intel's own paper calls it "an asynchronous, brain-inspired research processor" ([arXiv:2310.03251](https://arxiv.org/abs/2310.03251)) **[F]**. Not a product you can field **[INF]** |
| **SpiNNaker2** (TU Dresden / Manchester) | A hybrid processing element with ARM M4 cores and accelerators for *both* SNNs and DNNs, 22 nm FDSOI, DVFS driven by spiking activity ([Höppner et al., arXiv:2103.08392](https://arxiv.org/abs/2103.08392)) **[F]** | The hybrid design is itself an admission that pure SNNs are not enough **[INF]** |
| **BrainChip Akida** | Licensable IP plus chips. Claims sparsity cuts data, weights and activations "up to 10x" at each level, and "real-time streaming AI that runs continuously on milliwatts". Runs CNNs/spatio-temporal CNNs, SSMs and TENNs ([BrainChip](https://brainchip.com/akida-generations/)) **[F]** | Vendor claims. I found no independent public detection benchmark **[INF]** |
| **SynSense Speck** | DVS plus SNN on one chip, 327 k neurons, 3.36 µs per event ([arXiv:2304.06793](https://arxiv.org/abs/2304.06793)); **< 2 mW** ([SynSense](https://www.synsense.ai/products/speck-2/)) **[F]** | Low resolution. Good for gestures and presence, not crowd ReID **[INF]** |

For comparison, a Jetson Orin Nano gives 34 TOPS (4 GB) or 67 TOPS (8 GB) at
7–25 W, and an Orin NX gives 117–157 TOPS at 10–40 W (these TOPS are the
JetPack 6.2 "Super" mode figures NVIDIA now lists)
([NVIDIA Jetson Orin](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)) **[F]**.
The power gap between a Speck and the smallest Orin power mode is 7 W / 2 mW
= **3,500×** **[CALC]**. That gap, not accuracy, is where neuromorphic
hardware earns its place: always-on sentry nodes, battery or solar ground
sensors, and small drones.

## 6. Measured comparisons, not estimated ones

on real boards.

### 6.1 Loihi 2 vs Jetson Orin Nano (Intel, 2023)

Shrestha et al. compare Loihi 2 against a **Jetson Orin Nano** on the same
tasks ([arXiv:2310.03251](https://arxiv.org/abs/2310.03251), Table 1 in the
[HTML version](https://arxiv.org/html/2310.03251)) **[F]**:

| Task | Loihi 2 | Jetson Orin Nano | Ratio |
|---|---|---|---|
| PilotNet (steering from dashcam video), per inference | **0.09 mJ**, 0.05 ms, EDP 0.11 µJs (no IO) | **13.72 mJ**, 3.43 ms, EDP 47.08 µJs (batch 1, INT8) | ~150× energy; the paper says "over 400× lower EDP" |
| Audio denoising (NsSDNet vs NsNet2) | 28.74 mJ, 3.48 ms | 2,143.35 mJ, 95.35 ms | ~74× |

The abstract's summary is "orders of magnitude gains in combined efficiency
and latency (energy-delay-product)" for feed-forward and convolutional networks
on video and audio **[F]**.

**How to read it [INF].**
* This is Intel measuring its own chip, on workloads chosen to suit it.
  PilotNet is a small regression network, not a multi-class detector at
  640 px. The Loihi figure also excludes IO, and on a real sensor node IO is
  not free.
* It is still the best public evidence I found that the advantage is real on
  silicon, against a modern edge GPU at INT8, not a strawman at FP32.
* Keyword spotting told the same story earlier: Loihi "outperforms all of
  these alternatives on an energy cost per inference basis while maintaining
  equivalent inference accuracy", against CPU, GPU, Jetson TX1 and Movidius
  ([Blouw et al., arXiv:1812.01739](https://arxiv.org/abs/1812.01739)) **[F]**.

### 6.2 Worked example: energy per inference at a given frame rate **[CALC]**


**Scenario.** One perimeter camera, person detection at 10 fps, running 24 h.

**Option A: Jetson Orin NX running a YOLO-class detector in TensorRT INT8.**
* Ultralytics measures YOLO26n TensorRT INT8 at **3.49 ms/image** on an Orin
  NX 16 GB, excluding pre- and post-processing
  ([Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/)) **[F]**.
* The Orin NX module is specified at 10–40 W
  ([NVIDIA](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)) **[F]**.
* Upper bound on inference energy if the whole module drew 25 W while busy:
  25 W × 3.49 ms = **87 mJ per frame** **[CALC]**. Busy fraction at 10 fps:
  10 × 3.49 ms = 3.5 % **[CALC]**.
* The true cost is dominated by **idle power**. At the 10 W minimum mode the
  module burns 10 W × 86,400 s = 864 kJ = **240 Wh per day** whether or not
  anyone walks past **[CALC]**.

**Option B: Loihi-class inference on a similar small network.**
* Scale the PilotNet ratio naively: 13.72 mJ → 0.09 mJ is ×0.0066. Applied to
  87 mJ that gives ~0.6 mJ per frame, or ~6 mW at 10 fps **[CALC]**. This is
  an extrapolation across different networks and should be presented as
  "order of magnitude only". **[INF]**

**Option C: hybrid wake-up.**
* A Speck-class event node at < 2 mW for 24 h uses 2 mW × 86,400 s = 173 J =
  **0.048 Wh per day** **[CALC]**, from the < 2 mW figure above **[F]**.
* If the Orin sleeps and wakes on activity with a 5 % duty cycle, its share
  falls to about 0.05 × 240 Wh = **12 Wh per day**, plus wake-up overhead
  I have not measured **[CALC]**.
* The hybrid saves roughly **20×** at system level (240 → ~12 Wh per day),
  and all of that saving comes from *not running the GPU*, not from the SNN
  being clever per inference **[CALC/INF]**.

0.6 mJ) is flattering and fragile. The system-level comparison (240 Wh vs
~12 Wh per day) is robust, because it depends on duty cycle, and duty cycle
comes from the scene. That is also exactly the quantity SurvSim can measure,
because we know how often something really happens in each scenario. A
wake-up sensor that misses the intruder has saved power by failing, so the
correct metric pair is **(energy per day, missed-intrusion rate)**, never
energy alone.

## 7. Where SNNs win and where they don't

**Win (credible):**
1. **Always-on wake-up.** A milliwatt-class node listens all the time and powers
   up the watt-class GPU only on activity. The system saving is large even if
   the SNN is not very accurate, because its job is recall, not precision
   (section 6.2).
2. **Latency on fast targets.** Speck's 3.36 µs per event **[F]** against a
   33 ms frame interval at 30 fps is four orders of magnitude. Drone
   propellers, thrown objects and muzzle flash all happen inside one frame
   interval. **[INF]**
3. **High dynamic range.** 140 dB against 60 dB **[F]** means headlights, dawn
   and tunnel exits stop blinding the sensor.
4. **Radio-silent, SWaP-limited platforms.** If you cannot stream video out,
   you have to decide on the device. **[INF]**

**Don't win (yet) [INF]:**
1. **Absolute accuracy** on dense recognition. SpikeYOLO's 48.9 % mAP@50:95
   is a real result but it is at the level of mainstream small ANN detectors,
   not the frontier.
2. **Tooling.** PyTorch, ONNX and TensorRT are mature. SNN compilers are
   chip-specific (Lava for Loihi, vendor SDKs for Akida and Speck).
3. **Static targets.** Loiterers and parked vehicles. This is a property of
   the sensor, not the network.
4. **Measured, as opposed to estimated, energy** on detection workloads. Most
   detection papers, SpikeYOLO included, report the 45 nm operation-count
   model rather than a board measurement.

## 8. Combining an SNN front end with a conventional tracker

### 8.1 Architecture

```
                 ┌────────────────────────── always on, mW ─────────────────────────┐
 DVS pixels ───► │ SNN region proposer (Speck/Akida class)                            │
 (or v2e from    │   out: event clusters (x,y,t), activity score, coarse class        │
  CCTV frames)   └───────────────┬────────────────────────────────────────────────────┘
                                 │ wake + ROI list                     (SAPIENT: this node
                                 ▼                                      can report its own
                 ┌──────────────── duty-cycled, W ─────────────────┐    DetectionReports)
 CCTV frame ───► │ CNN detector on ROI crops (TensorRT INT8, Orin) │──► boxes + calibrated p
                 └───────────────┬─────────────────────────────────┘
                                 ▼
                 ┌────────────────────────────────────────────────────────────┐
                 │ Tracker (ByteTrack / OC-SORT style, Kalman state)           │
                 │   • CNN boxes = full measurement updates at frame rate      │
                 │   • event clusters = extra position updates between frames │
                 │   • stationarity hand-over: no events ≠ target gone         │
                 └───────────────┬────────────────────────────────────────────┘
                                 ▼
                 ReID + behaviour on CCTV crops  ──►  alarm policy  ──►  operator
```

### 8.2 Design points **[INF]**

* **Treat SNN outputs as detections carrying a calibrated confidence**, so
  existing association code works unchanged. Low-confidence event clusters
  then feed a ByteTrack-style second association pass.
* **Use events between frames as extra measurement updates** in the Kalman
  filter. That is where the latency advantage turns into track quality: fewer
  association errors on fast crossing targets.
* **Stationarity hand-over.** When a track stops producing events, the
  frame-based detector must keep it alive. Otherwise every loiterer becomes a
  track loss followed by an ID switch, and the loiter behaviour detector never
  fires. This is the single most important integration rule.
* **Out-of-sequence data.** Event clusters and frame detections arrive with
  different latencies, so the tracker has to handle out-of-sequence
  measurements. The multi-target OOSM treatment is a retrodiction step
  followed by an update ([García-Fernández & Yi, arXiv:2106.04898](https://arxiv.org/abs/2106.04898)) **[F]**.
* **Evaluate the combined system** on false alarms per camera-hour and time to
  alarm, not on the SNN's accuracy alone.

### 8.3 How SurvSim can help, without over-claiming **[INF]**

* An event stream can be *emulated* from rendered frames (v2e-style) at the
  render rate. It is approximate, because true microsecond timing needs
  high-rate rendering.
* SurvSim's ground truth includes exact per-frame positions and the
  degradation profiles, so an event front end can be scored on the same alarm
  and tracking metrics as the CNN path.
* The loiter and `commute_wait` hard-negative pair (CLAUDE.md, principle 3) is
  a ready-made test of the stationarity hand-over rule. A DVS-only system
  should *fail* it, and the simulator can show that failure quantitatively.
* **Not built yet**: there is no event emulator in `survsim/sensors/` today.

## 9. Evaluation protocol I would propose for an SNN front end **[INF]**

1. **Fix the operating point by operator budget**, not by F1. For example, at
   most 1 false wake per camera per hour.
2. **Report the recall of intrusion events at that budget**, broken down by
   speed (walk, run, crawl), by light, and by whether the target stops.
3. **Report energy per day** from measured duty cycle, not per inference.
4. **Report latency to first alarm**, i-LIDS style, where a late alarm counts
   as a miss (file 31 and `survsim/eval/`).
5. **Ablate**: the CNN alone at full rate, the CNN at reduced rate, and the
   hybrid. The hybrid has to beat "the CNN at 2 fps", which is the cheap
   conventional alternative that people forget to test.

Point 5 is the one I would push hardest on. Running the conventional detector
less often is a zero-research way to save energy, and many neuromorphic
comparisons never include it as a baseline.

## 10. What to say if asked about [vendor product]-style approaches

> "I haven't built on neuromorphic hardware, so I'll be careful. What I've read
> says spiking networks earn their place on power and latency with sparse,
> temporal input: an always-on sentry that wakes a heavier model, or a drone
> that can't afford a GPU. Intel's Loihi 2 paper measured about 150 times less
> energy than an Orin Nano at INT8 on a small video network, so the advantage
> is real on silicon for the right workload. Accuracy has also caught up more
> than people think: SpikeYOLO is at 48.9 mAP on COCO. Where I'd push is
> evaluation. Most detection papers still estimate energy from 45 nm operation
> counts, and on SpikeYOLO's own accounting the saving is about 25 percent for
> the headline model and about 3 times for a same-size model, not 100 times. I'd want the SNN scored inside the whole
> pipeline, on false alarms per camera-hour, time to alarm and energy per day,
> against a conventional detector run at a lower frame rate. That's the kind
> of evaluation my simulator is built for. And I'd be curious whether
> [vendor product] is spiking *hardware* or spiking *dynamics* on conventional GPUs,
> because those are quite different bets."

**Things not to say [INF]:**
* "SNNs are 100–1000× more efficient." That is true only on specific hardware,
  for sparse inputs, and often only estimated.
* "Event cameras see everything." They miss stationary targets.
* Any guess about how [vendor product] works internally. Ask instead.


**Q1. What is the real advantage of an event camera over a normal CCTV
camera?**
A. Three physical properties: microsecond timing, about 140 dB of dynamic range
against about 60 dB, and very little motion blur (Gallego et al.). For
surveillance that buys you fast-target detection and robustness to headlights
and dawn. The cost is that anything static disappears, and you lose colour and
texture. I'd use it as a cue and wake-up sensor next to CCTV, not instead of
it.

**Q2. How would you compare an SNN detector's energy with a Jetson fairly?**
A. First, against INT8, not FP32. Second, measured on the board, including IO
and memory, not estimated from 45 nm MAC and AC costs. Third, at system level
per day, because idle power dominates. The Loihi 2 paper is the right shape:
0.09 mJ against 13.72 mJ on PilotNet, both measured, with the Orin at batch-1
INT8. And the baseline must include simply running the CNN less often.

**Q3. Is SNN accuracy still far behind?**
A. Less than it was. Spiking-YOLO in 2019 reached 98 % of *Tiny* YOLO. SpikeYOLO
in 2024 reports 48.9 % mAP@50:95 on COCO, and on event data (Gen1) it beats an
equivalent ANN by 2.5 points mAP@50. Part of the gain is that it trains with
integer activations and then spreads them over timesteps, so it behaves a bit
like a low-bit quantised network. That's also why its energy advantage on its
own estimate is modest: about 25 % for the (3× larger) headline model, about
3× for the size-matched one, which is also less accurate than YOLOv5.

**Q4. What is the failure mode you'd worry about most in a DVS-based
perimeter system?**
A. The stationary intruder. Someone who walks in and then stops generates no
events, so a DVS-only tracker drops the track, and when they move again you get
a new ID. For loitering detection that is fatal. The fix is architectural: the
frame-based path keeps the track alive whenever event activity stops. I'd test
it with loiter vs `commute_wait` scenarios in simulation.

**Q5. How would you train a spiking detector today?**
A. Surrogate-gradient training, or its integer-activation variant as in
SpikeYOLO, for anything new. ANN→SNN conversion if I already have a good ANN
and hardware that needs spikes. Conversion used to need hundreds of timesteps,
but Bu et al. show high accuracy at 4 timesteps by replacing ReLU with a
quantisation-aware activation. I wouldn't use STDP for detection. It's
beautiful on MNIST (95 % unsupervised) but not competitive beyond it.

**Q6. Where would you put an SNN in a counter-UAS or CNI system?**
A. At the outer layer, as an always-on, milliwatt cue: a Speck-class node on a
fence post or mast, reporting activity and coarse class. It wakes or cues the
EO/IR detector and the PTZ, and its reports go into the fusion node like any
other sensor, as SAPIENT detection reports with a calibrated confidence. Its
value is energy and latency, so it is scored on recall at a fixed false-wake
budget and energy per day.

**Q7. How would you get training data for event cameras?**
A. Real data where it exists, such as Prophesee's 1 MP automotive set with
25 M boxes. Otherwise synthesise events from video with v2e, which models
threshold mismatch and noise, and whose authors report a 40 % improvement for
a night-time car detector trained on synthetic events. In SurvSim I'd render at
a high frame rate and run a v2e-style converter, with the caveat that timing is
only as fine as the render rate.

**Q8. Give me one number that summarises the case for neuromorphic at the
edge.**
A. About 3,500×: that's the power ratio between a 2 mW Speck and a 7 W Orin
Nano at its minimum mode. It is the reason the wake-up architecture works. In
my worked example the system goes from about 240 Wh a day to about 12 Wh a day
at a 5 % duty cycle. Almost all of that comes from not running the GPU, not
from per-inference efficiency, and it only counts if the wake-up doesn't miss
the intruder.

## 12. Numbers to memorise

| Quantity | Value | Source |
|---|---|---|
| DVS dynamic range vs frame camera | 140 dB vs 60 dB | Gallego et al. **[F]** |
| DVS timing | microseconds | Gallego et al. **[F]** |
| Speck latency per event / neurons / power | 3.36 µs / 327 k / < 2 mW | arXiv:2304.06793, SynSense **[F]** |
| SpikeYOLO on COCO | 66.2 % mAP@50, 48.9 % mAP@50:95 | arXiv:2407.20708 **[F]** |
| SpikeYOLO vs YOLOv5 energy (45 nm estimate) | 84.2 mJ (68.8 M params) / 34.6 mJ (23.1 M, 62.3 % mAP@50) vs 112.5 mJ (21.2 M) | arXiv:2407.20708 Table 1 **[F]** |
| Assumed op energies in that estimate | 4.6 pJ MAC, 0.9 pJ AC | arXiv:2407.20708 **[F]** |
| Loihi 2 vs Orin Nano, PilotNet | 0.09 mJ vs 13.72 mJ per inference | arXiv:2310.03251 Table 1 **[F]** |
| Conversion timesteps (modern) | 4 | arXiv:2303.04347 **[F]** |
| YOLO26n INT8 on Orin NX | 3.49 ms/image | Ultralytics **[F]** |
| Speck vs Orin Nano minimum power | ~3,500× | **[CALC]** |

## 13. Questions I would ask them **[INF]**

* Is [vendor product] deployed on neuromorphic silicon, on an FPGA, or as spiking
  dynamics on a GPU? What drove that choice: power, latency, or robustness?
* What is the input: event cameras, radar returns, RF, or frames converted to
  spikes? Spiking dynamics suit time series like radar micro-Doppler and RF
  bursts as naturally as they suit vision.
* How do you report energy to customers: measured on the target board, or
  estimated from operation counts?
* How do you handle stationary targets if part of the stack is change-driven?
* Is the "sovereign" point about UK-owned IP, or about UK-controllable
  hardware supply? Those lead to different hardware choices.

These are questions, not claims. Asking them well signals that you understand
where the engineering difficulty actually sits.

## Sources fetched this session (2026-09-26)

1. Gallego et al., Event-based Vision: A Survey, [arXiv:1904.08405](https://arxiv.org/abs/1904.08405)
2. Perot et al., 1 MP event-camera detection, [arXiv:2009.13436](https://arxiv.org/abs/2009.13436)
3. Richter et al., Speck, [arXiv:2304.06793](https://arxiv.org/abs/2304.06793)
4. SynSense Speck product page, [synsense.ai](https://www.synsense.ai/products/speck-2/)
5. Hu, Liu & Delbruck, v2e, [arXiv:2006.07722](https://arxiv.org/abs/2006.07722)
6. Rueckauer et al. 2017, [Frontiers in Neuroscience](https://www.frontiersin.org/articles/10.3389/fnins.2017.00682/full)
7. Bu et al., Optimal ANN-SNN conversion, [arXiv:2303.04347](https://arxiv.org/abs/2303.04347)
8. Neftci, Mostafa & Zenke, surrogate gradients, [arXiv:1901.09948](https://arxiv.org/abs/1901.09948)
9. Diehl & Cook 2015, STDP on MNIST, [Frontiers in Computational Neuroscience](https://www.frontiersin.org/articles/10.3389/fncom.2015.00099/full)
10. Kim et al., Spiking-YOLO, [arXiv:1903.06530](https://arxiv.org/abs/1903.06530)
11. Luo et al., SpikeYOLO, [arXiv:2407.20708](https://arxiv.org/abs/2407.20708) and [HTML](https://arxiv.org/html/2407.20708) (energy method, Table 1)
12. Intel neuromorphic computing page (Loihi 2, Hala Point), [intel.com](https://www.intel.com/content/www/us/en/research/neuromorphic-computing.html)
13. Shrestha et al., Efficient Video and Audio processing with Loihi 2, [arXiv:2310.03251](https://arxiv.org/abs/2310.03251) and [HTML Table 1](https://arxiv.org/html/2310.03251)
14. Blouw et al., keyword spotting on Loihi, [arXiv:1812.01739](https://arxiv.org/abs/1812.01739)
15. Höppner et al., SpiNNaker 2 PE, [arXiv:2103.08392](https://arxiv.org/abs/2103.08392)
16. BrainChip Akida generations page, [brainchip.com](https://brainchip.com/akida-generations/)
17. NVIDIA Jetson Orin spec page, [nvidia.com](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)
18. Ultralytics NVIDIA Jetson guide (YOLO26 benchmarks), [docs.ultralytics.com](https://docs.ultralytics.com/guides/nvidia-jetson/)
19. García-Fernández & Yi, out-of-sequence measurements, [arXiv:2106.04898](https://arxiv.org/abs/2106.04898)
