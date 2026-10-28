# D08 · Simulator Engineering Craft — how professionals actually build photoreal multi-camera human simulators

**Scope.** This document is about *craft*, not about which papers exist. It answers: when a team that
has shipped a synthetic-data pipeline sits down to build **SurvSim** (UE5 + UnrealCV/UnrealZoo +
MetaHuman + Mass AI + a Python director), what do they actually type, which console variables do
they set, which four things break first, and how do they know the data is correct?

**Relationship to the other docs.** [`01_RESEARCH_LANDSCAPE.md`](../01_RESEARCH_LANDSCAPE.md) chooses
the stack; this doc *builds* it. [`02_ARCHITECTURE.md`](../02_ARCHITECTURE.md) defines the module
boundaries; this doc supplies the UE-side implementation detail behind
`ASurvSimCCTVCamera`, `USurvSimGTSubsystem` and the Mass bridge.
[`06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md) specifies the sensor model as a
*parameter table*; §6 here covers the *implementation choice* (in-engine vs post) for each stage.
[`R04 §5–6`](R04_degraded_imaging_and_sim2real.md) already covers the sim-to-real *science*
(MOTSynth/BEDLAM/PeopleSansPeople numbers, domain randomisation theory, EPE, FID caveats,
mixed curricula) — §8 here does **not** repeat those and instead covers the *engineering* tests:
determinism harnesses, reprojection-error assertions, GT-leakage traps, CI.
[`08_ROADMAP_MILESTONES.md`](../08_ROADMAP_MILESTONES.md) gives the week grid; §11 here gives the
validated per-week recipe with exact plugin names, cvars and code sketches.

---

## 0. Research-conditions note (read this before trusting a citation)

This document was researched under two hard constraints, and they shape what is and is not
directly quotable:

1. **The WebSearch budget for the session was exhausted** (200/200 calls consumed before this task
   began). Every search call returned *"Web search was not performed: this session has used its web
   search budget"*. No new search-driven discovery was possible; the hop chain in §12 was walked by
   direct fetch of URLs already known or discovered from fetched pages' link graphs.
2. **The network egress proxy blocked most non-GitHub documentation hosts.** Confirmed blocks during
   this session: `dev.epicgames.com` (all Epic official documentation), `forums.unrealengine.com`,
   `docs.unrealcv.org`, `carla.readthedocs.io`, `arxiv.org`. GitHub (`github.com`,
   `raw.githubusercontent.com`) worked reliably and is the source of nearly every literal quote
   below.

**Consequence, stated plainly:** claims about Epic's own documented behaviour — Movie Render Queue
semantics, `SceneCaptureComponent2D` cost, `t.MaxFPS`, `UseFixedFrameRate`, Mass/StateTree/ZoneGraph
editor workflow, MetaHuman licence text, Chaos determinism, Lumen/Nanite cost — could **not** be
verified against the primary source in this session. They are written from engineering experience and
are marked **[VERIFY]** with the canonical URL to check. Treat every `[VERIFY]` as an action item for
week 0: open the URL, confirm the exact wording and the exact cvar name for your engine version, and
strike the marker. Anything *not* marked `[VERIFY]` and carrying a markdown link was fetched and read
during this session.

A second honesty note: UE console-variable names and Mass API surfaces **change between 5.3, 5.4,
5.5, 5.6 and 5.7**. The MassSample maintainers say this explicitly about their own documentation —
*"A lot of this documentation is still valid, but... code examples might use outdated pre-5.6 code.
When in doubt the code is always the most reliable indicator"*
([MassSample](https://github.com/Megafunk/MassSample)). Adopt that rule for everything in §2 and §5:
the engine source in `Engine/Source` is the authority, not this document and not a forum post.

---

## 1. Genealogy of CV simulators — what each got right and wrong for people-centric multi-camera video

The useful way to read this history is as a sequence of *arguments*, each one won and then partly
overturned. Below, each entry is judged on exactly the axes SurvSim cares about: (a) many people,
(b) many *fixed* cameras simultaneously, (c) long continuous video with stable identity, (d) rich
per-camera GT, (e) scriptable behaviour, (f) photometric realism of humans, (g) determinism and
reproducibility, (h) licence freedom.

### 1.1 The dataset-clone era (2016)

**Virtual KITTI** and **SYNTHIA** established that a game-engine clone of a real dataset transfers.
Their limitation for us is structural: both are *driving* datasets, ego-motion, one camera (or a
rigid stereo rig), people as background clutter at 20–60 px. Nothing in their design answers "what
does this person look like from camera 7 at the same instant". They got right: a *parallel*
synthetic/real pair, which is still the cleanest experimental design and the one MultiviewX later
copied for multi-camera (see 1.4).

**Playing for Data / Playing for Benchmarks** (GTA-V) won a different argument: labels can be
harvested from a *closed* commercial renderer by intercepting the graphics API, so you get
Rockstar's art budget for free. What it got wrong, unavoidably: no control. You cannot place a
camera on a pole, you cannot schedule a fight at t=412 s, you cannot get bone-level GT for a
specific person, and you cannot ship the data without legal risk. The whole JTA→MOTSynth line
inherits both the strength (art quality, crowd density) and the weakness (script-hook fragility,
EULA exposure). The lasting lesson for SurvSim is the **inverse**: we are paying for control, and
control is the only reason not to just use GTA. Every hour spent on realism that does not also buy
control is arguably misallocated — see the realism-vs-diversity reconciliation in
[R04 §5.4](R04_degraded_imaging_and_sim2real.md).

### 1.2 The programmable-engine era (2016–2018)

**UnrealCV** (2016 prototype, ACM MM 2017 paper) is the direct ancestor of our backend. Its design
insight is minimal and correct: *do not build a simulator, build a socket*. The plugin exposes a flat
verb/path command language — `vget` to read, `vset` to write, `vrun` to fall through to the UE console
— so "the virtual world" stays an ordinary UE project that an artist can open, while Python drives it
([unrealcv/unrealcv](https://github.com/unrealcv/unrealcv), MIT licensed, and per its README now
"supports Unreal Engine 5.2 and later"). What it got wrong is everything about throughput and about
*animated* content, and both failures are still live today: the maintainer's own 2016 issue says
*"the speed of unrealcv is roughly 10 - 20fps on my workstation"* and that performance *"will be the
next focus"* ([issue #19](https://github.com/unrealcv/unrealcv/issues/19)); a 2018 user could not hit
24 fps because *"I cannot render each image in 1/24 of a second but having a greater delay"* when
requesting `vget /camera/0/object_mask png`
([issue #109](https://github.com/unrealcv/unrealcv/issues/109)); and as of the current tracker the
top open issue is *"Any skeletal mesh causes a 100% crash for segmentation. VertexFactory not
initialized error"* ([issue #339](https://github.com/unrealcv/unrealcv/issues/339)). For a
*people* simulator, "skeletal meshes crash the segmentation pass" is not a footnote — it is the
critical path. §3 and §10 treat it as such.

**AirSim** (2017) got right the thing UnrealCV got wrong: it is a *plugin you drop into your own
project* with a proper RPC client in four languages, a pause/continue API for stepped simulation, and
a "Computer Vision mode" that decouples camera placement from vehicle physics — exactly the mode a
surveillance rig needs ([microsoft/AirSim](https://github.com/microsoft/AirSim), MIT). It also shipped
the only mainstream in-engine **thermal** approach worth copying (§6.3). What it got wrong: Microsoft
shut it down — *"This is a fork of the AirSim repository, which Microsoft decided to shutdown in July
of 2022"* — and the community fork **Colosseum** carried it to UE 5.6 before itself being *"archived
on July 11, 2026, and is now read-only"* ([CodexLabsLLC/Colosseum](https://github.com/CodexLabsLLC/Colosseum)).
Two dead-ends in a row is the single strongest argument in this document for **owning our own thin
plugin** rather than adopting a large third-party one: our GT exporter is ~2k lines of C++ we can
carry across engine versions, whereas a vehicle-dynamics-plus-RPC-plus-sensors framework is a
maintenance liability we cannot fund.

Colosseum also records the Linux reality we will hit: *"Ubuntu 22.04 currently lacks proper Vulkan
support; Docker deployment is recommended for that version"* — i.e. the container is not an
optimisation, it is the *fix* (§2.4).

**CARLA** (2017) is the reference implementation of *determinism as a product feature*: synchronous
mode plus a fixed delta, a replay system, and a test suite that includes collision determinism. Note
that determinism is not free even there — the tracker carries *"Synchronous mode: one tick_cue
produces two world frames (double-tick)"* (#9831, open), *"Unclear interaction between carla
executable -fps, -benchmark arguments and fixed-timestep synchronous mode"* (#5498, open since 2022),
plus *"Temporary fix for collision determinism test"* (#8899, merged) and *"TM determinism fixes"*
(#4989) ([search](https://github.com/carla-simulator/carla/issues?q=determinism)). **Read #9831 and
#5498 as a warning label on our own tick loop**: the two commonest determinism bugs in this class of
system are *a step command that advances the world a different number of frames than you think*, and
*two flags that both claim to control the timestep*. Our harness in §8.2 tests for precisely those.
CARLA's UE5 line also carries the modern hardware floor honestly — *"Intel i7/i9 9th gen or AMD Ryzen
7/9, 32GB RAM, NVIDIA RTX 3070+ with 16GB VRAM, and Ubuntu 22.04/24.04 or Windows 11"*
([carla README](https://github.com/carla-simulator/carla)) — which is a useful sanity check on the
BOM in [08](../08_ROADMAP_MILESTONES.md). What CARLA got wrong for us: it is a *vehicle* simulator.
Pedestrians are walkers with a simple controller, there is no body-shape variation worth the name, no
clothing variety, no face, and **no thermal sensor** in the sensor suite. Synthehicle is the proof by
construction that CARLA's strength is multi-camera *vehicles*: *"a massive CARLA-based synthetic
multi-vehicle multi-camera tracking dataset"*, 17 hours, *"64 scenes ... 16 different camera
configurations and 340 camera videos"* across *"four distinct weather scenarios (day, dawn, rain,
night)"* ([fubel/synthehicle](https://github.com/fubel/synthehicle)). That is the dataset-card shape
we should copy exactly; the content is the part CARLA cannot give us.

### 1.3 The embodied-AI era (2019–2022) — fast, interactive, and wrong for us

This family optimised a different objective: *steps per second for RL*, not *pixels per second for a
dataset*.

- **Habitat-Sim** is the extreme: *"several thousand frames per second (FPS) running single-threaded
  and reaches over 10,000 FPS multi-process on a single GPU"* and *"over 8,000 steps per second"* for
  a Fetch robot in ReplicaCAD ([facebookresearch/habitat-sim](https://github.com/facebookresearch/habitat-sim),
  MIT). It achieves that with baked scanned meshes and a lean OpenGL path — no dynamic GI, no
  skinned crowds, and *no bipedal humanoids in the listed robot set*. Photoreal people are simply not
  in scope.
- **AI2-THOR**: Unity, *"200+ custom scenes"*, *"2,600+ objects"*, RGB + segmentation + depth +
  metadata, Apache-2.0 — but *"the documentation does not mention human agent support"*
  ([allenai/ai2thor](https://github.com/allenai/ai2thor)). Note its Linux requirement, *"Linux
  requires X server with GLX module support"*, which is the exact class of pain UE's
  `-RenderOffscreen` exists to avoid (§2.4).
- **ThreeDWorld (TDW)** is the most interesting near-miss and worth studying before we design our
  agent tiers, because it *already invented our two-tier design*. TDW ships **Replicants** —
  *"humanoid agents with full-body animation, arm articulation, and grasping capabilities"* — and
  separately *"Non-physics humanoids: SMPL-based characters for background agents"*
  ([threedworld-mit/tdw](https://github.com/threedworld-mit/tdw), BSD-2-Clause). That is precisely
  SurvSim's "≤40 hero agents with bone GT, hundreds of Mass background agents" split from
  [02 §3.5](../02_ARCHITECTURE.md). It also ships a physically-derived audio system, **Clatter**,
  which is the right prior art for our audio-event channel. The catch: TDW is now in *"long-term
  support (LTS)"* and *"will receive only minor updates and bug fixes"* — a third abandoned platform
  in this document, and a third vote for owning the thin layer.
- **iGibson / Gibson** belong here too: real-scan interiors, fast, and fundamentally about robot
  navigation. [VERIFY — could not fetch `github.com/StanfordVL/iGibson` in this session; confirm its
  current status and licence before citing.]

**The transferable lesson.** These platforms taught the field to treat the simulator as a *stepped
function*, `obs = env.step(action)`, with an explicit clock — which is why UnrealZoo's gym API is
shaped that way and why our `Backend.step(dt)` / `Backend.capture(...)` split in
[02 §4](../02_ARCHITECTURE.md) is the correct interface. They also taught us the failure mode to
avoid: an API whose *only* consumer is a single RL agent tends to grow a "the observation is one
camera" assumption deep into the code. We must keep `capture()` list-valued from day one.

### 1.4 The offline-renderer era (2019–2024) — the correctness camp

**BlenderProc** and **Kubric** represent a philosophically different answer: give up interactivity,
render offline, and get *exactly reproducible, exactly correct* GT.

- **BlenderProc2** — *"a procedural pipeline built on Blender"* producing RGB, depth, normals,
  semantic segmentation, stereo pairs, into *"HDF5 containers with COCO and BOP format annotations"*,
  GPL-3.0 ([DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc)). Note the licence: **GPL-3.0
  is a redistribution consideration** if we ever vendored it into a product pipeline (§9).
  Its usability tax is real and instructive: *"Execution requires Blender's embedded Python
  environment—standard Python interpreters cannot run BlenderProc scripts directly. Remote debugging
  setup is necessary for IDE breakpoint debugging."* Any pipeline embedded in a DCC app inherits
  that; UE's runtime Python situation is the same problem in a different costume (§2.5).
- **Kubric** — Apache-2.0, PyBullet + Blender, producing *"instance segmentation masks, depth maps,
  optical flow data, object property metadata"*, with the candid admission that photorealism across
  all complexity levels *"is clearly not feasible"*
  ([google-research/kubric](https://github.com/google-research/kubric)). Kubric's real contribution
  to *our* craft is the **worker-container-plus-manifest** pattern: one scene = one hermetic
  container invocation = one deterministic shard. That is exactly the scale architecture in §7.4.
- **Infinigen** — BSD-3-Clause, procedural nature/indoors with *"Depth, Surface Normal, Instance
  Segmentation"* extended GT ([princeton-vl/infinigen](https://github.com/princeton-vl/infinigen)).
  The decisive fact for us: **no humans**. As fetched, *"human figure generation is not mentioned as a
  capability—all showcased examples feature landscapes, objects, and interior spaces without people."*
  Infinigen is therefore a *background* generator for us at best, and its lesson is the one that
  actually matters: **procedural generation removes the asset-library ceiling on diversity**, and per
  [R04 §5.2](R04_degraded_imaging_and_sim2real.md) diversity is what buys transfer. Our analogue is
  not procedural terrain, it is *procedural identity*: garments × colours × patterns × body × gait ×
  hair, combinatorially, which is what MOTSynth's MOTSynth-256 result says is worth more than volume.

**BEDLAM is the bridge between the two camps and the single most instructive engineering artefact in
this whole document**, because it is a *human-centric, UE-rendered, offline* pipeline whose tooling is
public. From [PerceivingSystems/bedlam_render](https://github.com/PerceivingSystems/bedlam_render):

- Engine pinned hard: *"UE 5.0.3 for Windows"* — a *specific patch release*, on Windows, for a paper
  whose whole claim is realism. Pin your engine version; realism pipelines are not version-portable.
- Rendering: **Movie Render Queue**, *"DX12 rasterizer with 7 temporal samples for motion blur"*, plus
  *"a secondary optional render pass [that] outputs EXR files (32-bit float, multilayer, cryptomatte)
  for depth maps and segmentation masks without spatial/temporal sampling"*.
  **Read that twice.** The professionals split the render into a *beauty pass with temporal
  accumulation* and a *GT pass with sampling switched off*, because temporal samples that make RGB
  beautiful make segmentation and depth wrong. And they used **cryptomatte multilayer EXR** for
  instance masks rather than a colour-coded PNG — which sidesteps the entire class of bugs UnrealCV
  users are living with in issues #330/#331 (§3.3).
- Bodies: two-stage, *"Create animated SMPL-X bodies (v1.1, female/male) from SMPL-X animation data
  files and export in Alembic ABC format. SMPL-X pose correctives are baked in the Alembic geometry
  cache"*, then imported to UE as `GeometryCache`. That is a **skinning bypass**: no UE skeleton, no
  retarget, no anim blueprint — the mesh is a per-frame vertex cache. It is exactly right for offline
  hero renders and exactly wrong for us (no runtime control, no interaction, huge disk), but it tells
  us where the fidelity ceiling of retargeting is: they chose not to trust a retarget at all.
- Hardware: *"Intel i9-12900K ... NVIDIA RTX3090 or higher ... 128GB or more"* memory. Note **128 GB
  RAM** for a single-scene human render farm node; the 64 GB in our BOM is the minimum, not the target.

### 1.5 The commercial-platform era (2021–2026)

**Unity Perception** is the cautionary tale about platform risk, in Unity's own words:
*"IMPORTANT: This project has been discontinued and is no longer supported by Unity. Please use the
Github issues page to seek community support."*
([com.unity.perception](https://github.com/Unity-Technologies/com.unity.perception)). It had the right
architecture — Perception Camera, labelers, a randomization framework, SOLO/Perception output schemas,
COCO converters, and *"Path Tracing/Accumulation"* for offline quality — and shipped
**PeopleSansPeople**, the most directly comparable prior work to SurvSim's people layer:
*"28 parameterized 3D human assets with 39 animation clips, 21,952 unique clothing textures"*
producing *"490,000 training images with 3+ million instances"* with COCO 2D boxes, keypoints,
semantic and instance masks and 3D boxes, Apache-2.0, with binaries for macOS and Linux
([PeopleSansPeople](https://github.com/Unity-Technologies/PeopleSansPeople)).
**The numbers are our floor and our ceiling simultaneously.** Floor: 28 humans × 39 clips is *small*,
and it still beat ImageNet pre-training decisively (*keypoint AP 46.40 vs 23.51* in the 641-real-image
regime). Ceiling: their 21,952 clothing textures are *texture* variation on a fixed garment set — no
garment geometry variation, no cloth sim, no faces worth re-identifying. **SurvSim's differentiator is
exactly in that gap: multi-camera, multi-hour, identity-persistent, garment-geometry-diverse.** If we
cannot beat PeopleSansPeople on person-detection transfer, we have built nothing; if we can produce
cross-camera identity GT they cannot produce at all, we have built something new regardless.

**Omniverse Replicator / Isaac Sim** is now genuinely open: Isaac Sim is *"an open-source application
on NVIDIA Omniverse"* under *"the Apache 2.0 license"*, Windows 11 or Ubuntu 22.04/24.04, *"RTX 4080
(minimum) to RTX PRO 6000 Blackwell"*, with standalone binaries, pip wheels and Docker
([isaac-sim/IsaacSim](https://github.com/isaac-sim/IsaacSim)). Note the sharp compiler constraint —
*"GCC/G++ version 11 specifically (versions 12+ unsupported)"* [confirmed in the IsaacSim README: "Building with Ubuntu 24.04 requires GCC/G++ 11 ... GCC/G++ 12+ is not supported" — applies to **building from source** `[audit R4 2026-09-26]`] — the kind of detail that costs a day
if discovered on day 40. The older container tooling repo is *"deprecated and archived as of March 30,
2026"* and points at the main repo, and its images carried the *"NVIDIA Omniverse License Agreement"*
rather than Apache — a licence split (code vs image/asset) that recurs everywhere in §9.
**Isaac Lab** on top offers *"over 16 robot models (manipulators, quadrupeds, humanoids)"* and 30+
training environments, Isaac Sim 6.1, Python 3.12, BSD-3/Apache dual
([isaac-sim/IsaacLab](https://github.com/isaac-sim/IsaacLab)) — but as fetched the README *"does not
explicitly address: human or pedestrian agent support [or] camera sensor rendering capabilities at
scale."* That is the honest state of the people story on Omniverse: `omni.anim.people` and the
"Isaac/Omniverse Replicator Agent" character pipeline exist and are the intended answer, but they are
not documented in the repos we could reach. [VERIFY — the character/people pipeline docs live on
`docs.omniverse.nvidia.com` / `docs.isaacsim.omniverse.nvidia.com`, both unreachable here; confirm
the current extension name (`omni.anim.people` vs the newer Agent SDK), the command-file format for
scripted character behaviour, and whether biped characters are Replicator-randomisable, before §4
is used to plan the optional Isaac backend.]

**GRUtopia / InternUtopia** is the most relevant recent Omniverse-side datapoint and it validates our
architecture from an unexpected direction: on Isaac Sim 4.5.0 it ships *"GRScenes: 100k interactive
finely annotated scenes"* across 89 categories and **GRResidents**, *"an LLM-driven NPC system"* for
*"social interaction, task generation, and task assignment"*, MIT code with assets under
*CC BY-NC-SA 4.0* ([OpenRobotLab/GRUtopia](https://github.com/OpenRobotLab/GRUtopia)). Two takeaways:
(i) **an LLM as the behaviour author is now a normal design**, which is directly applicable to
generating scenario YAML and dialogue-driven group behaviour in
[03_BEHAVIOUR_CATALOG.md](../03_BEHAVIOUR_CATALOG.md); (ii) the asset licence is **non-commercial**,
so a dataset built on GRScenes is not sellable — the single most common licence trap in this field
(§9).

**Genesis** is worth one paragraph and no more for us: Apache-2.0, *"designed to scale from a single
laptop kernel to datacenter-grade GPUs"*, with three renderer paths including *"Nyx (an in-house
renderer designed specifically for robotics)"* and a LuisaCompute ray-tracing path
([Genesis-Embodied-AI/Genesis](https://github.com/Genesis-Embodied-AI/Genesis)). As fetched, the
README *"doesn't address"* photoreal human video, motion synthesis or human modelling. It is a physics
platform with a renderer, not a people renderer with physics. Correct verdict: not a candidate.

**UnrealZoo (2024–25)** is our chosen foundation and deserves the most precise reading. From
[UnrealZoo/unrealzoo-gym](https://github.com/UnrealZoo/unrealzoo-gym): 100+ photorealistic
environments on **Unreal Engine 5.7**, scenes *"spanning up to 16 km²"*, *"10+ agents"* including
humanoid characters, Go1 quadrupeds, drones, vehicles and animals; observations covering
*"RGB-D, semantic masks, panoramic views, LiDAR point clouds, and occupancy voxel grids"* with v3.1
adding *"XYZI point-cloud observations"*; interactions including *"navigation, door opening, vehicle
entry/exit, object pickup, jumping, crouching, and climbing"*; physics on **Chaos**; **~70 GB**
package; Python 3.9+; Linux/Windows/macOS; **Apache-2.0**; and the headline throughput number
**"53.46 FPS at 2K"** — a README claim; the paper (arXiv 2412.20977, Table 2) reports only 640x480 throughput (83 FPS colour, 154 FPS mask) and "100 scenes" `[audit R3 2026-09-26]`.

Four notes a professional would make immediately:

1. **"53.46 FPS at 2K" is almost certainly single-camera capture throughput on a strong GPU, not
   N-camera multi-modality throughput.** Our workload is ~8 cameras × {RGB, depth, mask} = 24 render
   passes per tick. Budget accordingly (§2.3, §7.1) and measure it yourself in week 3 — this is the
   most important early benchmark in the project.
2. **UE 5.7 is a recent engine.** Matching it means matching its Mass, Motion Matching and MetaHuman
   API surfaces, and it means the MetaHuman plugin situation of 5.6+ (MetaHuman Creator moving
   in-engine), not the 5.4 one described in most tutorials.
3. **Apache-2.0 on the code** does not cover the 70 GB of scene content. Check per-scene provenance
   before shipping frames (§9).
4. **The `unrealzoo-gym` issue tracker was empty at fetch time** (the issues page returned "No
   results"). That is not a sign of maturity — it is a sign of a young project where *you* will be
   the one filing the first issue. Plan for reading the plugin source, not for a support queue.

### 1.6 What the genealogy prescribes for SurvSim (the one-paragraph synthesis)

Take UnrealCV's socket philosophy, but **do not depend on UnrealCV's render paths for ground truth**
— its open issues are concentrated in exactly the GT paths we need (skeletal segmentation, mask
colour fidelity, PIE-vs-Standalone, viewmode ordering). Take AirSim's "plugin in your project +
pause/step RPC + computer-vision mode" architecture, but own it, because both AirSim and Colosseum are
archived. Take CARLA's determinism discipline and its double-tick and flag-conflict bugs as your test
cases. Take BEDLAM's two-pass split (beauty with temporal samples / GT with sampling off) and its
EXR-multilayer instance masks. Take TDW's hero-vs-background agent tiering. Take PeopleSansPeople's
randomiser taxonomy and beat its identity diversity. Take Kubric's hermetic-shard scaling. Ignore
Genesis and Habitat for this project. And treat every platform in §1.3–1.5 that is now archived
(AirSim, Colosseum, Unity Perception, TDW-LTS, Isaac's old docker repo) as evidence for keeping our
UE-side surface area small enough to port in a week.

---

## 2. UE5 specifics for a multi-camera CCTV rig

This is the section where the project is won or lost. Everything here is about four questions:
*how do I get N camera images per tick*, *how do I make tick T reproducible*, *how do I run it with no
monitor*, and *how do I get correct labels out*.

### 2.1 The three capture architectures, and which one to use where

There are exactly three ways to get pixels out of UE5, and a mature pipeline uses **two of them for
different purposes**.

**(A) `USceneCaptureComponent2D` → `UTextureRenderTarget2D` → CPU readback.** One component per
camera, each rendering the scene into its own render target. This is what UnrealCV, AirSim and every
real-time CV plugin do, and it is what `ASurvSimCCTVCamera` in [02 §3.2](../02_ARCHITECTURE.md) is
built on.

*Cost model, which you must internalise:* a scene capture is **a whole additional scene render**. It
re-runs visibility culling, the base pass, shadows and (unless disabled) the post-process chain for
its own view. Eight captures at 1080p is therefore roughly *nine* renders per frame, not 1.1 renders.
The mitigations, in descending order of payoff:

1. **`bCaptureEveryFrame = false`, `bCaptureOnMovement = false`, and call `CaptureScene()` explicitly**
   from your tick. This single change converts "every camera renders every engine frame forever" into
   "each camera renders exactly when the director asks". It is the highest-leverage line of code in
   the whole capture path, and forgetting it is the classic reason a project mysteriously runs at 6 fps
   in an empty level. [VERIFY — property names on `USceneCaptureComponent`/`USceneCaptureComponent2D`:
   `https://dev.epicgames.com/documentation/en-us/unreal-engine/scene-capture-in-unreal-engine` (blocked
   this session).]
2. **`CaptureSource`**: prefer `SCS_FinalColorLDR` only when you need post-process; use
   `SCS_SceneColorHDR` / `SCS_SceneColorSceneDepth` when you want the raw buffers. Capturing final
   colour drags the full post-process chain (bloom, exposure, TSR history) per camera.
3. **`ShowFlags` pruning per capture component**: turn off `Bloom`, `MotionBlur`,
   `AmbientOcclusion`, `ScreenSpaceReflections`, `Atmosphere` where the camera does not need them, and
   `Fog` only if your scenario does not depend on it. For the *GT* captures (depth, mask) turn off
   essentially everything.
4. **`bAlwaysPersistRenderingState`** to avoid re-initialising view state each capture, at the cost of
   memory per camera.
5. **`PrimitiveRenderMode = UseShowOnlyList` / `HiddenActors`** to cut the visible set for cameras
   that only need people (e.g. an amodal-mask pass with the world hidden — see §2.7).
6. **Resolution discipline**: a real CCTV camera is often 704×576 (D1) or 1280×720. Rendering 4K and
   downsampling is a *worse* model of a cheap camera *and* 9× the cost. Render near-native.

**(B) Movie Render Queue (MRQ) / Movie Render Graph (MRG).** Offline, one camera at a time (per
sequence/camera cut), with temporal and spatial sampling, warm-up frames, deterministic frame-indexed
output, and high-quality writers (EXR multilayer, PNG16). This is what BEDLAM used, with the exact
split quoted in §1.4: *"DX12 rasterizer with 7 temporal samples for motion blur"* for the beauty pass
and a separate pass for *"depth maps and segmentation masks without spatial/temporal sampling"*
([bedlam_render](https://github.com/PerceivingSystems/bedlam_render)). MRQ's advantages are exactly
the ones that matter for a *published dataset*: it renders on a wall-clock-independent timeline, it
waits for streaming and shader compilation to settle (warm-up / `EngineWarmUpCount`), and its temporal
sampling gives *physically motivated* motion blur instead of the screen-space approximation.

**(C) `UTextureRenderTarget2D` + a custom RDG/RHI async readback path**, or a third-party recorder. The
UnrealCV tracker itself points at this: issue #283 recommends the **Runtime Video Recorder** plugin,
which uses *"GPU to perform efficient hardware accelerated capture of viewport, render targets and
cameras"*, can record *"surface normals and depth maps, material properties (metallic/specular),
bounding boxes and segmentation masks, custom post-processing outputs"*, needs no OpenCV, and
*"functions in packaged environments"*; it was used by *"Meta FAIR researchers for their IntPhys 2
paper"* ([unrealcv #283](https://github.com/unrealcv/unrealcv/issues/283)). IntPhys 2 is itself a UE
5.4 synthetic video benchmark of 253 scenes / 1,012 videos in its main set
([facebookresearch/IntPhys2](https://github.com/facebookresearch/IntPhys2)) — so this is a validated
production path, not a hobby plugin. **Recommendation: evaluate Runtime Video Recorder in week 3 as
the fast path for RGB video, and keep our own GT exporter for labels.** Encoding H.264 on the GPU
inside the engine removes the single largest cost in the naive pipeline (PNG-encoding 8 × 25 frames per
second on the CPU).

**The decision rule for SurvSim.**

| Purpose | Architecture | Why |
|---|---|---|
| Interactive iteration, behaviour debugging, RL-style loops | (A) SceneCapture, low res, round-robin | latency matters, quality does not |
| Bulk dataset recording (the 10 h dataset) | (A) at native CCTV res + (C) GPU video encode, offline-stepped (not real time) | throughput per GPU-hour |
| "Hero" clips, publication figures, realism validation set, FID reference set | (B) MRQ two-pass (beauty with temporal samples; GT with samples off) | physically-correct blur/AA and exact EXR GT |
| Depth / mask / normal GT in bulk | (A) or (C) with **all temporal features off** | correctness beats beauty |

Do **not** try to make one path serve all four. BEDLAM did not; nor should we.

### 2.2 Anti-aliasing, TSR/DLSS, and why they must be off for anything you label

The single most common silent corruption in UE-based synthetic data is **temporal accumulation
bleeding across object boundaries**. TAA, TSR, FSR, DLSS and MRQ's temporal samples all reproject
history from previous frames. For RGB that is desirable. For depth, mask, normal, optical flow or an
ID buffer it is *wrong by construction*: a mask pixel is a categorical value, and the average of
"person 3" and "background" is not a category. The failure is visible in the UnrealCV tracker as
*"Object Mask Rendering Artifacts/Glitches"* where masks arrive as *"scattered, noisy colored pixels"*
on UE 5.6/DX12, with TAA and Lumen named as the suspects
([issue #331](https://github.com/unrealcv/unrealcv/issues/331)).

Capture-configuration checklist for every labelled pass (set these and *assert* them in the run
manifest):

```
r.AntiAliasingMethod 0        ; 0=none, 1=FXAA, 2=TAA, 3=MSAA, 4=TSR   [VERIFY name/values per 5.x]
r.ScreenPercentage 100        ; no upscaling, no TSR history
r.TemporalAA.Upsampling 0
r.MotionBlurQuality 0         ; engine blur off; we model blur in post from the velocity buffer
r.DefaultFeature.MotionBlur 0
r.DefaultFeature.AutoExposure 0      ; fixed EV per camera; our exposure model owns this
r.DefaultFeature.Bloom 0
r.DefaultFeature.AmbientOcclusion 0
r.Tonemapper.Sharpen 0
r.Tonemapper.Quality 0        ; for GT passes
r.PostProcessAAQuality 0
r.SceneColorFringeQuality 0
r.Streaming.FullyLoadUsedTextures 1  ; kill texture pop-in between takes
r.Streaming.PoolSize 0               ; disable pool limit for deterministic texture residency
r.ShaderPipelineCache.Enabled 1      ; and pre-warm; see §2.9
```

EasySynth's list of limitations is the independent confirmation that this is real and that it bites
even in a purpose-built plugin: *"Anti-aliasing requires FXAA method specifically"*, and
*"optical flow rendering assumes all objects other than the camera are stationary"*
([ydrive/EasySynth](https://github.com/ydrive/EasySynth), MIT, UE 5.5–5.7). That second limitation is
a warning for us specifically: **do not trust an engine optical-flow/velocity buffer for moving
people without validating it**, because plugins in this space routinely only handle camera motion. Our
motion-blur and rolling-shutter models in [06 §3](../06_REALISM_AND_SENSOR_MODEL.md) depend on a
*correct* per-pixel velocity buffer for *skinned characters*; validating that in week 7 with a
synthetic checkerboard-on-a-walking-person test is cheap and prevents a silent, systematic error in
every blurred frame we ship.

Also note, from the same list: *"Take Recorder cannot integrate with the plugin's sequences"* and
*"rendering windows cannot be closed during processing"*. The second is the kind of thing that turns
an overnight batch into a wasted night.

### 2.3 Rendering N cameras per frame: the four strategies

Let `N` = cameras, `M` = modalities per camera, `R` = pixels, `f` = capture rate. Naive cost is
`N·M·R·f` full scene renders. Real pipelines attack every term.

**(1) Round-robin / staggered capture.** Not every camera needs a frame every tick. Real CCTV rigs are
*not* synchronised — indeed [02 §1.3](../02_ARCHITECTURE.md) already models `clock_offset_ms` and
`drift_ppm` as a *feature*. So capture camera `i` on ticks where `tick % k == i % k`. At 25 Hz sim and
8 cameras with `k=2`, you halve render cost and you get a *more realistic* rig (per-camera phase
offsets) rather than a less realistic one. **This is the best trade in the entire document: a
performance win that improves fidelity.** The constraint: any camera pair used for *multi-view
triangulation GT* must share a tick, so group the overlapping pairs into the same phase bucket.

**(2) Per-camera modality budgets.** Depth and mask are needed *for the cameras you are labelling*, at
the rate you are labelling. Many scenarios want 25 fps RGB but only need masks at 5 fps for training
data. Background cameras used only for "presence" evidence may need RGB only. Encode this in the
camera YAML as `capture: {rgb: 25, depth: 5, mask: 5, normal: 0}`.

**(3) Resolution stratification.** `near` cameras at 1920×1080, `mid` at 1280×720, `far`/overview at
704×576. This matches real deployments and cuts pixels by 3–6×.

**(4) GPU readback discipline — the hidden cost.** The stall that kills naive pipelines is not
rendering, it is `ReadPixels()` on the game thread: it forces a GPU flush, so you pay a full pipeline
bubble per camera per frame. The professional pattern is a **ring of N_frames staging buffers with
async readback and a 2–3 frame latency**: enqueue the copy on the render thread, fence it, and collect
the result two frames later, tagging every buffer with its sim tick so the writer can reassemble in
order. Your capture is then *pipelined* rather than *serialised*. Three corollaries:
(a) your GT JSON must be keyed by sim tick, never by "whatever frame just arrived";
(b) at shutdown you must drain the ring or you lose the last frames — a classic off-by-3 that
truncates every clip;
(c) prefer 8-bit BGRA for RGB, `R16F`/`R32F` for depth, and an **integer** format (`R32_UINT` or
`R16_UINT`) for instance IDs, never a colour-encoded 8-bit PNG (see §2.7 and issue #330).

**(5) `-RenderOffscreen` and the null RHI.** `-RenderOffscreen` creates a real GPU device and renders
into an offscreen surface with no visible window — **this is what you want** for headless capture.
`-nullrhi` creates *no* rendering device at all: it is for servers and automation tests, and with it
**every capture returns nothing**. Confusing the two is a rite of passage. Companion flags for a
batch run: `-unattended -nosound -nosplash -NoVerifyGC -stdout -FullStdOutLogOutput
-windowed -ResX=1920 -ResY=1080 -ini:Engine:[/Script/Engine.RendererSettings]` overrides as needed.
[VERIFY — exact current flag semantics: Epic's "Command-Line Arguments" and "Running Unreal Engine
without a GPU" pages on `dev.epicgames.com` (blocked this session).]

**(6) Pixel Streaming is irrelevant to us, and knowing why saves a week.** Pixel Streaming exists to
deliver an *interactive, H.264-encoded, latency-optimised, lossy* stream to a *browser*. It gives you
one view, compressed with rate control you do not want, with frames dropped under load, and no ground
truth. It is the correct answer for a demo UI for stakeholders and the wrong answer for data
generation. (If you want an RTSP "live camera" feel for integration testing, generate files then
re-stream with ffmpeg into [mediamtx](https://github.com/bluenviron/mediamtx) — MIT, *"a ready-to-use
and zero-dependency live media server"* that accepts an ffmpeg publisher — exactly as
[02 §POST-PROCESS](../02_ARCHITECTURE.md) already specifies.)

### 2.4 Determinism and the fixed timestep

Determinism for us means one thing operationally: **`survsim run --seed 42` twice produces
byte-identical GT and perceptually identical frames.** Note the asymmetry — we require *bit-exact
labels* but only *near-exact pixels*, because GPU driver versions can legitimately change the last bit
of a float in a shader. Bake that distinction into the tests (§8.2) or you will chase ghosts.

Layers, from most to least controllable:

1. **The Python director is fully deterministic and must be.** Per-subsystem `numpy.random.Generator`
   seeded from `hash(master_seed, subsystem_name)`, as [02 §2](../02_ARCHITECTURE.md) specifies. Never
   share one global RNG across subsystems: adding one call in the behaviour engine then reshuffles
   every outfit in the population, which destroys the ability to A/B a single knob. **Also forbid
   `set`/`dict` iteration order from influencing anything** — sort by uid before any RNG draw.
2. **Engine time.** Use a *fixed* delta. In UE the project settings are `bUseFixedFrameRate` +
   `FixedFrameRate` (General Settings), and the cvar `t.MaxFPS` *throttles* but does not *fix* the
   delta. There is also `-FixedTimeStep=` / `-benchmark` style command-line control, and this is
   exactly where CARLA's open issue #5498 warns about *"unclear interaction between ... -fps,
   -benchmark arguments and fixed-timestep synchronous mode"*. Pick **one** mechanism, assert the
   observed `DeltaSeconds` in-engine every tick, and fail loudly on drift.
   [VERIFY — `bUseFixedFrameRate`, `FixedFrameRate`, `t.MaxFPS`, `-FixedTimeStep`: Epic docs blocked;
   confirm names and precedence for your exact 5.x.]
3. **Stepped, not real-time.** The correct loop for dataset generation pauses the world, applies
   state, steps exactly one fixed delta, captures, and repeats. UnrealCV exposes the primitives:
   *"Action Commands: ... game state management (pause/resume)"* via `vset /action/game/pause`
   ([command reference](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/commands.rst)).
   AirSim's equivalent — *"Pause/continue simulation capabilities support controlled experimentation"*
   ([AirSim](https://github.com/microsoft/AirSim)) — is the pattern to copy: `simPause(True)`,
   `simContinueForTime(dt)`.
   **Guard against the double-tick.** CARLA's #9831, *"one tick_cue produces two world frames"*, is
   the exact bug to test for: stamp each captured frame with an in-engine monotonic tick counter, send
   it back with the GT, and assert in Python that it increases by exactly 1 per director step.
4. **Physics (Chaos).** Chaos is deterministic *only* under tightly controlled conditions: identical
   binary, identical substep count, identical initialisation order, single-threaded solve or a
   deterministic task graph, and no frame-rate-dependent substepping. Async physics and task-graph
   parallelism break it. The practical policy is the one already in
   [08 risk register](../08_ROADMAP_MILESTONES.md): **do not let physics carry semantics.** Ragdolls,
   cloth, debris and dropped props are *decoration*; the truth is the recorded state, not the planned
   state — *"truth is what happened, not what was planned"*. Record positions as GT after the step,
   never before.
   [VERIFY — Chaos determinism settings (`p.Chaos.Solver.*`, async physics tick, `bSubstepping`,
   `MaxSubstepDeltaTime` in Physics settings) on Epic docs; also check whether your UE version
   defaults to async physics, which you must disable.]
5. **Mass Entity determinism.** Mass is an ECS whose processors run *multithreaded by default* —
   MassSample documents `bRequiresGameThreadExecution`, the `mass.FullyParallel 1` cvar for
   per-processor parallelism, and `ParallelForEachEntityChunk` gated by `mass.AllowQueryParallelFor`
   ([MassSample](https://github.com/Megafunk/MassSample)). Parallel iteration over chunks is *fine*
   for determinism only if no processor's result depends on iteration order — and crowd avoidance
   emphatically does. **Policy: for recorded runs, force Mass single-threaded (`mass.FullyParallel 0`,
   parallel-for disabled) and treat the Mass background crowd as non-deterministic decoration whose
   *recorded* positions are the truth.** Any agent that carries a label — anyone whose behaviour is
   scored, or who appears in `events.jsonl` — must be a *hero* agent driven by the Python director,
   not a Mass entity. This is a hard architectural line and it should be enforced by a test that fails
   if a labelled uid has no hero handle.
   Note also Mass's LOD system (`MassLOD`) *"affecting render rates and tick frequencies"* and
   `MassRepresentation`'s *"rendering via ISMC or actor swapping at distance thresholds"*: an entity
   whose tick rate depends on distance-to-camera is **frame-rate- and viewpoint-dependent by design**,
   a second reason background crowd cannot be ground truth.
6. **Animation.** Skeletal animation evaluated with a fixed delta is deterministic; Motion Matching
   selecting a pose from a database *with a random tie-break or a time-based cost* is not. Seed it or
   pin it (§5.4).
7. **Streaming, GC and shader compilation** are the sneaky ones: level streaming completing on a
   different frame changes when an actor's `BeginPlay` runs, which changes RNG consumption order
   in-engine. Fix with warm-up frames before capture starts (MRQ does this for you;
   for SceneCapture paths, implement an explicit `warmup_ticks: 30` in the scenario and *discard*
   those frames), `r.Streaming.FullyLoadUsedTextures 1`, and a pre-warmed shader/PSO cache.

### 2.5 Python control of UE5: four options, ranked

| Option | Works at runtime in a packaged build? | Latency | Verdict for SurvSim |
|---|---|---|---|
| **UnrealCV / UnrealCV+ TCP** | Yes (that is its purpose) | ~ms per command, image transfer dominates | **Primary.** Reuse the protocol; extend with our own commands. |
| **Custom C++ plugin with a TCP or gRPC endpoint** | Yes | lowest; batch a whole tick in one message | **Required eventually** for batched GT and batched actor updates. |
| **Remote Control API (HTTP/WebSocket, `RemoteControl` plugins)** | Editor-oriented; exposing it in a packaged game is possible but not the designed path | ~ms, HTTP overhead per call | Useful for *authoring* tools (a web zone editor calling into the editor), not for the 25 Hz loop. [VERIFY — Epic's "Remote Control API" docs blocked; confirm packaged-runtime support.] |
| **Editor Python Scripting (`unreal` module)** | **No — editor only** | n/a | Use it for *build-time* automation: asset import, MetaHuman batch variant baking, nav-mesh export, sequence generation. Never for the run loop. |

**The most important fact in this table:** *there is no Python interpreter in a packaged UE5 game.*
The `unreal` Python module is an *editor* feature. Every tutorial that shows Python moving actors is
showing you editor scripting. Therefore SurvSim's runtime control path **must** be a socket into C++
(UnrealCV-style), and our editor-Python is a *separate*, offline tool tier. Get this straight in week 0
and the architecture in [02 §3](../02_ARCHITECTURE.md) is already correct; get it wrong and you
discover in week 12 that your pipeline only runs in the editor, which also means it inherits PIE's
behaviour — and PIE behaves differently from Standalone in exactly the place that hurts:
*"object_mask works in PIE but fails in Standalone (UE5.5, UnrealCV 5.2 branch)"*
([issue #282](https://github.com/unrealcv/unrealcv/issues/282)), where *"RGB images work perfectly"* in
standalone and manual console viewmode switching works, but the scripted capture produces no file.

**Batching is the other half.** One TCP round-trip per actor per tick at 40 actors × 25 Hz = 1000
round-trips/s and the socket becomes the bottleneck long before the GPU does. Design the protocol so
one message carries the whole tick: `vset /survsim/tick {json with all transforms, anim states,
appearance deltas}` → engine steps → `vget /survsim/gt` returns one JSON blob plus a manifest of
image buffer handles. UnrealCV+ (the UnrealZoo fork) moved in this direction; note the UnrealCV README
mentions *"RPC communication supporting Linux environments with 'higher FPS and more reliable'
operation"*, and that the *"source code for UnrealCV+"* was itself the subject of a tracker question
(#289) ([unrealcv](https://github.com/unrealcv/unrealcv)) — so **verify which fork you are actually
building against in week 0**, because the command sets differ.

### 2.6 Headless Linux rendering

The target: a GPU node with no X server producing frames. What actually works:

- **Vulkan, not OpenGL.** UE5 on Linux is Vulkan-first. UnrealCV's own known-issues page records the
  legacy pain: on Linux, *"binary execution failures, often related to OpenGL; troubleshooting involves
  installing mesa-utils and testing with `glxgears`"*
  ([issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)).
  If you are debugging `glxgears` in 2026 you are on the wrong path.
- **Containers are the supported route.** `ue4-docker` exists precisely for *"running built Unreal
  Engine projects with offscreen rendering"* on Linux *"via the NVIDIA Container Toolkit"*
  ([adamrehn/ue4-docker](https://github.com/adamrehn/ue4-docker), MIT). Colosseum's note that
  *"Ubuntu 22.04 currently lacks proper Vulkan support; Docker deployment is recommended"*
  ([Colosseum](https://github.com/CodexLabsLLC/Colosseum)) makes the same point from the other side.
- **Licence constraint on images, which is a real operational trap.** Epic's EULA restricts
  distribution of engine *source/tooling* container images; you may not push an image containing the
  engine to a public registry. Keep our UE image in a private registry, and structure the Dockerfile
  so the *engine* layer is built locally and only *our project* layers are shared.
  [VERIFY — Epic EULA §distribution and ue4-docker's own "licensing" docs at
  `adamrehn.github.io/ue4-docker` (unreachable); confirm before any CI image push.]
- **Concretely**: `docker run --rm --gpus all -e NVIDIA_DRIVER_CAPABILITIES=all
  -v $PWD/out:/out survsim-ue:5.7 /project/SurvSim.sh -RenderOffscreen -unattended -nosound
  -nosplash -ResX=1920 -ResY=1080 -UnrealCVPort=9000`. Two failure modes to expect: missing
  `NVIDIA_DRIVER_CAPABILITIES=all` (you get a device but no graphics capability), and a mismatch
  between the host driver and the container's Vulkan loader/ICD.
- **Do not use `-nullrhi`** for capture (§2.3.5). Use it for a nightly "does the level load and does
  the behaviour engine run" smoke test, which is a genuinely valuable, GPU-free CI job (§7.6).
- **Isaac Sim's requirement list is a useful cross-check on what a modern RTX container expects**:
  *"Windows 11 or Linux (Ubuntu 22.04/24.04)"*, *"RTX 4080 (minimum)"*, *"GCC/G++ version 11
  specifically (versions 12+ unsupported)"*
  ([IsaacSim](https://github.com/isaac-sim/IsaacSim)).

### 2.7 Ground-truth extraction: the six labels and how each actually goes wrong

**(a) Instance masks via custom stencil.** The standard UE trick: enable `r.CustomDepth 3`
(custom depth *with stencil*), set `bRenderCustomDepth = true` and
`CustomDepthStencilValue = id` per component, then read the stencil in a post-process material and
output it. Three hard limits, all of which you will hit:
1. **The stencil is 8-bit: 255 usable IDs, and 0 means "nothing".** With 500 identities per dataset
   you must recycle IDs per-frame and ship a *per-frame* `stencil_id → uid` map in the GT JSON, or
   move to a `SceneTexture`-based `PrimitiveID`/custom-data path.
2. **Skeletal meshes are the weak point.** `Any skeletal mesh causes a 100% crash for segmentation.
   VertexFactory not initialized error` — reported against UnrealCV's 5.2 branch on UE 5.3 *and* 5.6,
   with the observation that *"the same animations work fine elsewhere in Unreal Engine"*
   ([#339](https://github.com/unrealcv/unrealcv/issues/339)). Interpretation: it is a bug in how the
   segmentation viewmode's custom vertex factory is initialised for skinned meshes, not a fundamental
   limitation. **Mitigation for us: do not use UnrealCV's `object_mask` viewmode for people at all.
   Implement our own custom-stencil pass in the SurvSim plugin and validate it against skinned
   MetaHumans on day one of week 3.** This is the single most important de-risking task in the project
   and it belongs *before* Demo 1, not after.
3. **Colour-encoded mask PNGs lose information.** *"The distinction between overlapping instances is
   clearly visible in the UE viewport, but the images saved using the vget command show no difference
   at all"* — a gamma/compression discrepancy where IDs were encoded as `G = ID × 5`
   ([#330](https://github.com/unrealcv/unrealcv/issues/330)). **Root cause class: writing categorical
   IDs through an sRGB-encoded, possibly lossy, 8-bit channel.** Never do this. Write a single-channel
   16-bit PNG or an integer EXR layer. BEDLAM's choice of *"EXR files (32-bit float, multilayer,
   cryptomatte)"* for masks is exactly this lesson, learned earlier.
   Related: *"Why are some objects not visible in obj_mask mode?"*, where the reporter sees the target
   in lit mode but not in mask mode, *and the inverse* ([#287](https://github.com/unrealcv/unrealcv/issues/287)),
   and *"the effect of switching my scene from lit to object_mask (P1) differ from switching from
   depth/normal to object_mask (P2)"* ([#285](https://github.com/unrealcv/unrealcv/issues/285)) — i.e.
   **viewmode switching is order-dependent and stateful**. If you must use viewmodes, always return to
   `lit` between captures and never assume a viewmode switch is idempotent.

**(b) Depth.** Read `SceneTexture:SceneDepth` in a post-process material (or capture with
`SCS_SceneColorSceneDepth`) and write **linear metric depth in float**, not a normalised 0–1 ramp.
EasySynth's *"depth images – linear depth scaled between 0 and a user-specified range"*
([EasySynth](https://github.com/ydrive/EasySynth)) is the common shortcut and it silently clips your
long-range perimeter cameras; a 60 m fence camera with a 0–50 m range writes garbage beyond 50 m and
you will not notice until a ReID model trained on it fails. Also: depth from a scene capture is
*ray-length or z-depth depending on the node you use* — verify with a flat wall at known distance,
because the difference is a cosine falloff toward the frame edges that quietly biases every
back-projection. And expect trouble with translucent and particle content: *"UnrealCV does not work
with Niagara Particle system on UE 5.2"* — rain particles *"visible with a standard lit camera"*
disappear under `vset /viewmode depth`, and *"converting particles to mesh-based instead of
sprite-based"* and adding collision both failed ([#271](https://github.com/unrealcv/unrealcv/issues/271)).
For us this is *desirable* (we do not want rain in the depth buffer used for occlusion tests) but it
must be a **documented, asserted** property, not an accident.

**(c) Bone projection / 2D keypoints.** Get bone transforms in world space
(`USkeletalMeshComponent::GetSocketTransform` / `GetBoneTransform`), convert UE cm-left-handed to our
m-right-handed at the plugin boundary as [02 §1.1](../02_ARCHITECTURE.md) mandates, then project with
the camera's own K. **Project with the same K you publish in `calib/{cam}.json`, derived from the same
FOV and aspect, and never with a second hand-written copy of the maths** — duplicated projection code
that drifts is the #1 source of "the boxes are 3 px off" bugs. Test: project a bone, then unproject
using the depth buffer, and assert the round trip is < 0.5 px (§8.3).
**Keypoint visibility** is three-valued, not two: *outside frame* (truncated), *inside frame but
occluded*, *visible*. Compute occlusion by comparing the projected bone's camera-space depth against
the depth buffer at that pixel with a tolerance of a few centimetres (self-occlusion by the person's
own body is the common case and the tolerance must be tight enough to catch a hand behind a torso).
Note MetaHuman's skeleton is not COCO-17 and not SMPL-X's 54 joints
([smplx](https://github.com/vchoutas/smplx)); maintain one explicit, versioned mapping table and emit
the *engine* bone set plus the derived COCO-17, so a future re-mapping does not require re-rendering.

**(d) 2D boxes: `GetActorBounds` is not good enough.** An actor's bounds box is axis-aligned in world
space and generously padded; projecting its 8 corners and taking the extent gives a box that can be
20–40 % too large for a walking person, and *systematically* too large for a person with an arm out.
Options in ascending cost/accuracy: (i) projected bounds of the *skeletal mesh component* with
`bComputeBoundsFromPhysicsAsset` — better, still padded; (ii) projected convex hull of all bone
positions inflated by a per-bone radius — cheap, decent; (iii) **derive the box from the instance mask
itself** — exact by construction, and free if you are already rendering masks. **Use (iii) as the
published `bbox_visible` and (ii)/(i) as the `bbox_amodal` fallback.** Then *assert* that
`bbox_visible ⊆ bbox_amodal` for every instance in every frame; violations catch mask/stencil ID
mix-ups instantly.

**(e) Amodal boxes and occlusion ratio.** The clean way: render a *second* mask pass with the world
hidden (`PrimitiveRenderMode = UseShowOnlyList` with only the people) to get each person's unoccluded
silhouette, and a normal pass for the occluded one. Then
`occlusion_ratio = 1 − area(visible) / area(amodal)` exactly, and the amodal box falls out. Cost: one
extra low-cost render per camera (no lighting needed — an unlit ID pass). This is worth it: occlusion
ratio is the covariate that every serious detection/tracking analysis stratifies by, and estimating it
from geometry is much worse than measuring it. Person-person mutual occlusion also needs the
show-only list to contain *only the one person* if you want per-person amodal silhouettes in a crowd —
i.e. cost scales with people, so do it at a reduced rate (e.g. 5 Hz) for the labelled subset only.

**(f) Face visibility and pixel height** — cheap and high value for a surveillance dataset. Face
visible = head-bone forward vector vs camera ray angle < threshold **and** the nose/eye keypoints pass
the depth test **and** projected inter-ocular distance > N px. Pixel height = projected head-top minus
foot. Publish both; they are the natural difficulty axes for ReID and face tasks and they let a
reviewer see immediately whether a "hard" split is actually hard.

### 2.8 Writing frames out fast

Numbers to hold in your head (derived, §7.1): 8 cameras × 1080p × 25 fps of *lossless PNG* RGB is
roughly 2–3 GB/minute and will saturate a single NVMe *and* a CPU core per two cameras. Therefore:

- **RGB: encode video on the GPU, not PNGs on the CPU**, unless you need per-frame lossless. NVENC
  H.264/HEVC at high bitrate (CRF ~14–18) is visually near-lossless and 30–60× smaller; and since
  [06 §3.7](../06_REALISM_AND_SENSOR_MODEL.md) *deliberately* applies H.264 degradation anyway, an
  archival high-bitrate intermediate is scientifically fine as long as it is *documented* and the FID
  reference set is rendered lossless. If you want a lossless archival master, use PNG or lossless
  HEVC for a **sampled subset** (e.g. 1 frame in 25) rather than all frames.
- **Depth: EXR half-float (`R16F`) single channel, PIZ or ZIP compressed.** Half-float gives ~0.5 mm
  resolution at 10 m and ~5 cm at 100 m — adequate. Full float doubles the bill for no benefit at
  CCTV ranges. Note UnrealCV's known-issue list literally includes *"OpenEXR requirement"*
  ([issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)) —
  budget build-time pain for EXR support.
- **Masks: 16-bit single-channel PNG** (`uint16` instance id). Small, lossless, unambiguous.
- **Never write from the game thread.** Use UE's `FImageWriteQueue` (the async image-write subsystem
  MRQ uses) or hand frames to a dedicated writer thread pool with a bounded queue and a *drop-loudly*
  policy: if the queue is full, log and abort the take rather than silently dropping frames, because a
  dataset with silent gaps is worse than no dataset.
- **Filename = sim tick, zero-padded**, e.g. `frames/cam03/000412.jpg`, and a `frames/cam03/index.csv`
  with `tick,sim_time_s,wall_time_s,exposure_us,camera_clock_offset_ms`. The index is what lets you
  reconstruct the *per-camera* timeline including the deliberate jitter.

### 2.9 PIE vs packaged build

Develop in PIE, record in a packaged build, and **treat "works in PIE" as meaningless evidence**. The
canonical demonstration is UnrealCV #282 (§2.5). Differences that bite: PIE keeps editor-only
subsystems alive; asset cooking can strip or alter things (unused materials, editor-only data,
`bAllowCPUAccess` on meshes you need for CPU-side queries); shader permutations differ (PIE compiles
on demand, packaged uses a cooked PSO cache — so the *first* runs of a packaged build stutter unless
you pre-warm); `ini` overrides resolve differently. UnrealCV's known-issues page even lists
*"Unreal Engine config file not updating"* and *"screen resolution problems"* with the fix
*"using the console command `setres 640x480` in game mode, or modifying the config file shown via
`vget /unrealcv/status`"* ([issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)) —
i.e. resolution is a *config* problem, and config resolution differs between PIE and packaged.

**Policy: from week 3, the acceptance test for every milestone runs against a packaged Linux build in
the container.** If it only works in PIE, the milestone is not done.

---

## 3. UnrealCV and UnrealZoo: what you actually get

### 3.1 The command language

From the fetched reference
([commands.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/commands.rst)),
the protocol is a flat REST-like verb/path language over TCP, with five families:

| Family | Examples (as documented) | Notes |
|---|---|---|
| Camera | `vget /camera/[id]/location`, `vset /camera/[id]/rotation`, `vget /camera/[id]/lit`, `.../depth`, `.../object_mask`, `.../normal`, `vget /camera/[id]/optical_flow` | *"multiple data formats (binary and file-based output), field-of-view adjustment, depth sensing, and object masking"*. Binary mode (`png`/`npy` returned over the socket) avoids a disk round-trip. |
| Object | `vget /objects`, `vset /object/[obj_name]/location`, `vset /object/[obj_name]/color`, rotation/visibility | Object addressing is **by actor name string**, so spawn naming discipline is part of your protocol contract. |
| Plugin | `vget /unrealcv/status`, `vget /unrealcv/help` | `status` prints the listening port and the effective config file path — the first thing to check on any connection failure, per the known-issues page. |
| Action | `vset /action/game/pause`, keyboard-input injection, level navigation | Pause/resume is the basis of stepped capture (§2.4). |
| Engine passthrough | `vrun <console command>` | *"Unreal Engine built-in commands for development and debug"* — this is how you set cvars (`vrun r.AntiAliasingMethod 0`), `stat unit`, `setres`, screenshots. |

Two protocol properties worth designing around: commands are reachable **both** from the in-game
console (backtick) and from a socket, which makes interactive debugging of the exact command a
Python client sends very easy; and the docs state the list *"is growing and subject to change"* and
invite requests — i.e. **we should expect to add commands, and adding them is the intended workflow.**
Our additions: `vset /survsim/tick <json>`, `vget /survsim/gt`, `vget /survsim/cameras`,
`vset /survsim/person/<uid>/appearance <json>`, `vset /survsim/env <json>`,
`vset /survsim/camera/<id>/ptz <p,t,z>`, `vset /survsim/camera/<id>/tamper <kind>`.

### 3.2 Performance, honestly

The documented history is a straight line of the same complaint:

- 2016, maintainer: *"the speed of unrealcv is roughly 10 - 20fps on my workstation"*, adequate for
  *"dataset generation"* but not for RL ([#19](https://github.com/unrealcv/unrealcv/issues/19)).
- 2018, user on Ubuntu: cannot sustain 24 fps because *"I cannot render each image in 1/24 of a second
  but having a greater delay"* for `vget /camera/0/object_mask png`
  ([#109](https://github.com/unrealcv/unrealcv/issues/109), still open).
- Known issues page lists *"UnrealCV performance speed"* as a standing item
  ([issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)).
- 2025, a user recommends an entirely different capture plugin for *"performant capture of Synthetic
  scenes/simulations"* ([#283](https://github.com/unrealcv/unrealcv/issues/283)).
- UnrealZoo/UnrealCV+ reports **"53.46 FPS at 2K"** (README claim, not in the paper; `[audit R3 2026-09-26]`) ([unrealzoo-gym](https://github.com/UnrealZoo/unrealzoo-gym)),
  a genuine order-of-magnitude improvement, and the UnrealCV README credits the RPC rework with
  *"higher FPS and more reliable"* behaviour on Linux.

**Engineering conclusion.** The per-request architecture (one socket round-trip → one viewmode switch →
one render → one PNG encode → one transfer) is the bottleneck, not the GPU. The fix is structural, and
it is the same fix in every mature pipeline: **one message per tick, N renders batched in one engine
callback, raw buffers (not PNG) transferred, async readback, and no viewmode switching at all** (use
dedicated capture components per modality instead of switching a global viewmode). Budget: assume
**~8–15 Hz for 8 cameras × 3 modalities at 720p on an RTX 4090 with the naive path, and 25–40 Hz after
batching** — and then *measure it in week 3* and put the number in the repo. Note this makes offline
(slower-than-real-time) recording completely acceptable: [08](../08_ROADMAP_MILESTONES.md)'s week-14
acceptance of *"≥ 8 cams × 1080p × 25 fps offline ≥ 0.5× realtime"* is the right framing, because
nothing about dataset generation requires wall-clock real time.

### 3.3 Known issues, as a risk list

The full open tracker at fetch time
([issues](https://github.com/unrealcv/unrealcv/issues)): #339 skeletal-mesh segmentation crash;
#331 mask artefacts/noise on 5.6+DX12; #330 mask colour/gamma loss; #329 surface-normal errors in the
notebook; #287 objects missing in mask mode (and vice versa); #283 alternative recorder suggestion;
#282 mask fails in Standalone but works in PIE; #275 camera moves but capture returns the initial view;
#271 Niagara particles invisible in depth; #270, #268, #266 (`no unrealcv.ini`) usage issues.

**The shape of that list is the message: nine of twelve open issues are about the ground-truth render
paths.** RGB works; labels are fragile. Since labels are the entire product, the correct posture is:
*use UnrealCV for transport, control and RGB; implement masks/depth/normals/IDs ourselves inside the
SurvSim plugin, where we control the vertex factory, the stencil, the bit depth and the encoder.* That
is a ~1–2 week C++ task in week 3–5, and it is the difference between a pipeline we can debug and one
whose failures are somebody else's open issue.

#275 deserves a specific note because it looks like a mystery and is usually a *frame-ordering* bug:
the capture happens before the engine has rendered a frame with the new camera transform. The fix is
the one in §2.3.4 — capture on a later tick than the transform update, and tag every buffer with the
tick it was rendered on. If you build the async ring correctly, #275 cannot happen to you.

### 3.4 UnrealZoo's agent API

What is confirmed: *"10+ agents"* including humanoid characters, quadruped (Go1), drones, vehicles and
animals; interactions *"navigation, door opening, vehicle entry/exit, object pickup, jumping,
crouching, and climbing"*; gym-style Python API; RGB-D, semantic masks, panoramic, LiDAR, occupancy
grids; real-time multi-agent interaction with 10+ agents in one scene; Python 3.9+; binaries from
ModelScope or Hugging Face at ~70 GB; Apache-2.0
([unrealzoo-gym](https://github.com/UnrealZoo/unrealzoo-gym)). I could not fetch a per-agent
animation manifest — the `docs/` paths I tried returned 404, and the issue tracker was empty.

**[VERIFY — the three questions that decide whether we use UnrealZoo agents or our own MetaHumans in
weeks 3–5.]** Read these out of the shipped plugin content, not the README:
1. **What is the animation vocabulary per humanoid?** (walk/run/idle/crouch/jump/climb are implied by
   the interaction list; is there a *fight*, *fall*, *crouch-work*, *spray*, *reach-up* set? Almost
   certainly not — our behaviour catalogue will need its own anim library regardless.)
2. **What skeleton do the humanoids use, and is it UE5's `SK_Mannequin`/`UEFN` rig or a custom one?**
   This determines whether Mixamo/AMASS retargets drop straight in (§5.2).
3. **Can we add a MetaHuman as a new agent class without rebuilding the 70 GB binaries?** If agents are
   defined by data assets in a pak that we can mount as a patch pak, yes; if they are compiled in, then
   week 5 requires building our own project from the UnrealCV+ plugin source, which changes the plan.
   Plan for the second case: **treat the UnrealZoo binaries as an environment/asset source and Demo-1
   accelerator, and build our own UE project for the real work.**

### 3.5 What to keep from UnrealZoo regardless

Even if we build our own project: 100+ environments across 16 km² is an environment library we cannot
author ourselves, its UE 5.7 + Chaos baseline tells us which engine to match, its 53.46 FPS number is
the benchmark to beat, and its Apache-2.0 *code* licence means we can read and adapt the UnrealCV+
transport layer legally. Its agent tiering and multi-agent loop are also the best available reference
implementation of "many controlled humans in a photoreal UE scene over a socket".

---

## 4. Alternatives and hybrids: when to reach for something else

**Omniverse Replicator / Isaac Sim + USD.** Reach for it when (i) you need physically-accurate sensor
simulation with RTX ray tracing and radiometrically meaningful values, (ii) your pipeline is already
USD-based and you want scene composition/variant layering as a *data* operation rather than an editor
operation, or (iii) you need tight coupling to robot control. Its structural advantages over UE for our
task are real: Replicator's randomisation is declarative and *scene-graph-native*, USD layering makes
"same scene, 400 variants" a composition problem rather than a save-as problem, and the whole thing is
now Apache-2.0 open source ([IsaacSim](https://github.com/isaac-sim/IsaacSim)). Its structural
disadvantages for *people* are equally real: nothing in the Omniverse ecosystem matches MetaHuman for
photoreal human authoring, the character-animation extensions are thinner than UE's Motion Matching /
Control Rig / Chaos Cloth stack, and the people-pipeline documentation lives behind hosts we could not
reach. **Verdict: keep as the documented optional backend in [02](../02_ARCHITECTURE.md) (the abstract
`Backend` protocol already makes this cheap), spike it in week 16, and revisit seriously only if
Omniverse's character tooling matures or a customer demands USD.** GRUtopia's GRScenes + LLM-driven
GRResidents ([GRUtopia](https://github.com/OpenRobotLab/GRUtopia)) is the thing to watch — but its
assets are **CC BY-NC-SA 4.0**, so it cannot feed a commercial dataset (§9).

**Blender (BlenderProc / Kubric-style) for offline hero shots.** Reach for it for: cloth and hair
simulation you cannot afford at runtime, exact geometric GT via cryptomatte, physically-based path
tracing for the *realism reference* set, and any asset-conditioning work (garment fitting, UV/texture
generation, procedural pattern synthesis). BEDLAM is the proof that a Blender→UE hybrid is the
professional choice for humans: SMPL-X bodies were prepared in Blender and *"export[ed] in Alembic ABC
format"* with *"pose correctives ... baked in the Alembic geometry cache"*, then rendered in UE
([bedlam_render](https://github.com/PerceivingSystems/bedlam_render)). **Concrete recommendation for
SurvSim: use Blender offline to bake garment variants and to generate the FID/perceptual reference
set; do not put Blender in the per-frame path.** Mind BlenderProc's **GPL-3.0**
([BlenderProc](https://github.com/DLR-RM/BlenderProc)) if you vendor it.

**Unity.** Architecturally the closest competitor and the one with the best *people-specific* prior art
(PeopleSansPeople, MultiviewX). MultiviewX is worth copying wholesale as a *methodology*: a 25 m × 16 m
playground, *"6 synchronized cameras with overlapping fields-of-view"* at 1920×1080, with
*"calibrations ... provided"* and a toolkit of `generateAnnotation.py`, `calibrateCamera.py`,
`generatePOM.py`, `unitConversion.py` ([MultiviewX](https://github.com/hou-yz/MultiviewX)), evaluated
with WILDTRACK's MODA/MODP/precision/recall. **That file list is essentially the spec for our
`tools/` directory**, and the deliberate mirroring of WILDTRACK's setup is the "digital twin of a
camera topology" design we should reuse for at least one SurvSim environment so that cross-dataset
comparison is possible. But: Unity Perception is discontinued
([com.unity.perception](https://github.com/Unity-Technologies/com.unity.perception)), and Unity has no
MetaHuman. **Verdict: steal the methodology, not the engine.**

**Godot.** Free, MIT, lovely to script, and not a candidate: no photoreal human pipeline, no
production-grade GI/skin shading, no crowd framework at scale. Use it only if someone needs a
pedagogical toy backend; the `MockBackend` in [02](../02_ARCHITECTURE.md) already fills that niche more
cheaply.

**Generative video.** Out of scope here — [R04 §5.6](R04_degraded_imaging_and_sim2real.md) covers
world models and EPE-style realism transfer, including why a translation network trained toward one
real domain imports that domain's camera. One engineering-side addition: EPE-class methods need the
renderer's **G-buffers** as conditioning ([isl-org/PhotorealismEnhancement](https://github.com/isl-org/PhotorealismEnhancement),
archived Sept 2024), which means *if we ever want EPE, we must be exporting albedo/normal/depth/material
buffers now*. Exporting them costs almost nothing extra once the multi-modality capture path exists, so
**add `albedo` and `material` to the modality enum in week 3 even though nothing consumes them yet.**
That is a genuinely cheap option on a future capability.

---

## 5. Human motion and behaviour realism

Behaviour *semantics* live in [03_BEHAVIOUR_CATALOG.md](../03_BEHAVIOUR_CATALOG.md). This section is
about the animation and crowd *machinery*.

### 5.1 The three-tier motion architecture

Professionals do not pick one motion source; they layer three:

1. **Locomotion** — must be continuous, direction-agnostic, speed-parameterised and foot-planted.
   Source: Motion Matching (UE 5.4+ `PoseSearch`) over a motion database, or a classic blendspace.
2. **Actions** — discrete, triggered, possibly paired: sit, phone, reach, crouch-work, spray, climb,
   fall, punch/block. Source: Mixamo / mocap clips on a montage slot.
3. **Posture / style overlays** — limp, slouch, hands-in-pockets, carrying, looking-around. Source:
   **Control Rig** applied as a post-process anim layer, plus additive pose assets.

This layering is what makes 8 gait styles × 60 actions tractable: you do not author 480 clips, you
author 8 databases × 60 clips × a handful of rig layers. It is also what makes our `Person.gait` and
`Person.intent` schema in [02 §1.2](../02_ARCHITECTURE.md) implementable rather than aspirational.

### 5.2 Retargeting: Mixamo, AMASS/BEDLAM SMPL-X → MetaHuman

**Mixamo** is the pragmatic starting library: large, free, includes locomotion, idles and a fight set.
Its skeleton is the "mixamorig" hierarchy; retarget to the UE5 mannequin or directly to the MetaHuman
skeleton with the **IK Retargeter** (`IKRig` + `IKRetargeter` assets). The professional workflow is
*chain-based*: define IK chains (spine, arms, legs, head) on both rigs, set the retarget pose ("A-pose
to T-pose" is the classic first failure), then batch-retarget with editor Python (`unreal` module,
build time) rather than clicking 300 assets.
[VERIFY — IK Retargeter asset/API names and the editor-Python batch-retarget entry points on Epic
docs, blocked this session.]

**AMASS / BEDLAM (SMPL-X) → MetaHuman** is the higher-fidelity, higher-effort path and is worth it for
gait realism, because AMASS is real marker-based mocap: *"a large database of human motion unifying
different optical marker-based motion capture datasets by representing them within a common framework
and parameterization"*, SMPL+H parameterised, *"also compatible with SMPL and SMPL-X body models"*
([nghorbani/amass](https://github.com/nghorbani/amass)). Two hard problems:

- **Topology.** SMPL-X has *"54 joints"* and 10,475 vertices ([smplx](https://github.com/vchoutas/smplx));
  MetaHuman's skeleton is different in joint count, naming, orientation and — critically — **bone roll
  conventions**. A naive joint-angle copy produces twisted forearms and hyperextended knees. Do it as:
  SMPL-X params → posed joint *positions* → an IK rig solve on the MetaHuman → bake. Or take BEDLAM's
  radical option and bypass skinning entirely with an Alembic geometry cache (§1.4) when you only need
  pixels, not control.
- **Scale and ground contact.** SMPL-X is metric and floor-referenced at the origin; UE is centimetres
  with the actor pivot at the feet. Mismatch shows as **floating or sinking feet**, the single most
  common "this is obviously synthetic" tell in a human dataset, and one that a 2AFC human study
  (per [06 §4](../06_REALISM_AND_SENSOR_MODEL.md)) catches instantly. Add an explicit foot-IK/ground-
  trace pass and a CI check that asserts the lowest foot bone is within ±2 cm of the traced ground for
  ≥ 99 % of frames in a smoke clip. That single test is worth more than a week of eyeballing.

**Licence caution that changes what we can ship:** AMASS and SMPL-X are *"for non-commercial scientific
research purposes"* with commercial use requiring a separate licence from `ps-licensing@tue.mpg.de`
([amass](https://github.com/nghorbani/amass), [smplx](https://github.com/vchoutas/smplx)). Motion
*derived from* AMASS arguably carries that restriction into any dataset we render from it. **Policy:
keep an AMASS-free "commercially clean" motion set (Mixamo + our own mocap/synthesised motion) as the
default, and treat AMASS-driven runs as a research-only variant, flagged in the dataset card.** See §9.

### 5.3 Motion synthesis for behaviours we cannot buy clips for

Fights, tampering, furtive object handovers, "unusual posture" — the exact behaviours
[03](../03_BEHAVIOUR_CATALOG.md) needs — are poorly covered by stock libraries. Options:

- **Text-to-motion diffusion (MDM).** MIT-licensed, *"~0.4 seconds per sample"* after the 50-step
  speed-up, supporting *"Text-to-Motion, Action-to-Motion, [and] Motion Editing"* including inpainting,
  outputting SMPL mesh parameters and per-frame OBJs
  ([motion-diffusion-model](https://github.com/GuyTevet/motion-diffusion-model)). Motion *editing by
  inpainting* is the underrated feature for us: take a real walk cycle and inpaint "reaches up toward
  the camera housing" over frames 40–90, keeping the locomotion real.
- **MotionGPT.** MIT, unified text↔motion with *"motion captioning, motion prediction, and motion
  in-between"*, outputting `(nframe, 22, 3)` joint positions
  ([MotionGPT](https://github.com/OpenMotionLab/MotionGPT)). Its *captioning* direction is quietly
  useful to us for the NL-retrieval benchmark in [08 wk15](../08_ROADMAP_MILESTONES.md): auto-generate
  text descriptions of our own GT motions to build query/answer pairs.
- **The honest limitation, in the authors' words:** MotionGPT *"struggles with complex, unseen motions
  (gymnastics, diving)"* and is *"limited by small datasets (HumanML3D: 14,616 motions; KIT: 3,911
  motions)"*. Fights and tampering are precisely "complex, unseen". **Therefore: use synthesis for
  *variation* around clips we have, not for *creating* the hard behaviours.** And note both depend on
  SMPL/SMPL-X, inheriting §5.2's licence and topology problems.
- **Paired/choreographed animation for fights** is the boring answer that works and is what games ship:
  author (or buy) *matched pairs* — attacker `punch_R` and victim `hit_react_R` — with a shared
  root-relative alignment transform and a synchronised start tick. The Director places both agents at
  a canonical relative pose, plays both montages from the same tick, and *records what happened*. Do
  not attempt physically-negotiated fighting; it is a research project, it will not look better, and it
  destroys determinism.

### 5.4 Motion Matching / PoseSearch specifics (UE 5.4+)

Motion Matching replaces a state machine with a nearest-neighbour search over a pose database, using a
*trajectory* query (past and future root motion) plus pose features (bone positions/velocities). Why it
matters for us: it is the cheapest route to *non-robotic* crowd locomotion with correct foot planting
at arbitrary speeds and turn rates, which directly addresses [08](../08_ROADMAP_MILESTONES.md)'s
"behaviour looks robotic" risk.

Craft notes: build **one database per gait style** (normal/brisk/slow/limp/shuffle/military/crouch) so
"gait" is a database selection rather than a blend weight — this makes gait a *categorical, labellable*
attribute, which is what our GT schema wants. Database size drives both memory and search cost; keep
clips trimmed and mirrored. Budget CPU: the search is per-character per-frame, so it is a real cost at
40 hero agents and a reason background crowd should *not* use it (Mass crowd uses simple
anim-to-texture / vertex-animation paths instead). For determinism, ensure the cost function has no
random tie-break and that `bUseInertialBlending`-style history is reset consistently at take start.
[VERIFY — `PoseSearch`/Motion Matching asset names, the `MotionMatching` plugin name, and its
determinism-relevant settings on Epic docs, blocked this session.]

### 5.5 Crowd simulation: which planner for which tier

- **Hero agents (≤ 40, labelled):** our own Python planner — social force for comfort/personal-space
  and **ORCA/RVO2** for hard collision avoidance, exactly as [02 §1](../02_ARCHITECTURE.md) specifies.
  RVO2 is the right library: Apache-2.0, ORCA *"reduces collision-avoidance decisions to
  low-dimensional linear programming problems"*, handles *"thousands of agents with collision-free
  computations taking only milliseconds"*, with OpenMP parallelism and *"full simulation accessibility
  and manipulation during execution"* ([snape/RVO2](https://github.com/snape/RVO2)). Use the Python
  binding (`rvo2`) and keep the solve in Python so it is deterministic and testable without a GPU.
- **Reference implementations to read:** `pedsim_ros` for the social-force side — *"individual walking
  using social force model for very large crowds in real time"* plus *"group walking behaviors and
  social activity simulation"*, libpedsim under **LGPL** with BSD ROS wrappers
  ([srl-freiburg/pedsim_ros](https://github.com/srl-freiburg/pedsim_ros)); and **Menge** (Apache-2.0)
  as the modular academic framework with *"dozens of examples"*
  ([MengeCrowdSim/Menge](https://github.com/MengeCrowdSim/Menge)). Note the LGPL on libpedsim: read the
  papers and reimplement rather than linking, if there is any commercial ambiguity.
- **Background crowd (hundreds):** UE's **Mass** stack. From
  [MassSample](https://github.com/Megafunk/MassSample): `MassEntity` is Epic's *"archetype-based Entity
  Component System (ECS) framework created by Epic's AI team for massive crowd simulations ... featured
  in the 2021 Matrix Awakens demo"*, with `MassMovement` (`UMassApplyMovementProcessor`),
  `MassRepresentation` for *"rendering via ISMC or actor swapping at distance thresholds"*, `MassLOD`
  *"affecting render rates and tick frequencies"*, `MassSpawner` with *"EQS/ZoneGraph spawn point
  generation"*, `MassSmartObjects` for *"smart object reservation for entity interaction"*,
  `MassSignals`, and `MassActors` as *"the bridge enabling entity-actor data exchange"*. The AI plugin
  adds **ZoneGraph** — *"in-level splines/shapes with configurable lanes for pathfinding"* — and
  **StateTree**, *"a lightweight state machine for entity behavior control"*.

**The four Mass facts that shape our design:**

1. **`MassActors` is our hero/background bridge.** Promote a background entity to a full actor (and
   thus to a MetaHuman with bone GT) when a scenario needs it. This is how you get "one person out of
   the crowd does something" without simulating 500 MetaHumans.
2. **`ZoneGraph` lanes are our structured domain randomisation.** Pedestrians on lanes, queues at
   gates, loitering in plazas — this is SDR by construction (see
   [R04 §5.3](R04_degraded_imaging_and_sim2real.md)) and it is free with City Sample's crowd pipeline.
3. **`MassSmartObjects` is the prop-interaction mechanism** for [03](../03_BEHAVIOUR_CATALOG.md)'s bins,
   doors, benches, vending machines. Its *reservation* semantics are what stop six agents using one
   bench — and reservations are also a source of order-dependence, so see (4).
4. **Multithreading vs determinism** (§2.4.5): `mass.FullyParallel`, `mass.AllowQueryParallelFor`, and
   the deferred command buffer ordering (*"Create → Add → Remove → ChangeComposition → Set → None"*).
   Deferred commands are a *feature* for us — they make mutation order explicit — but the parallel
   query paths must be off for recorded runs.
   Also heed MassSample's warning that direct composition changes are *"only truly safe to call outside
   of processing on the main thread"*: our Python-driven spawn/despawn must be queued and flushed at a
   defined point in the tick, never applied mid-processing.

City Sample's crowd pipeline is the reference content ([VERIFY — the "City Sample" documentation page
on `dev.epicgames.com` was blocked; confirm the crowd-character LOD tiers, the
`AnimToTexture`/vertex-animation path used for distant pedestrians, and the **Rule Processor** plugin's
role in populating the city, which is the tool for scattering props/people by rule at build time]).

### 5.6 MetaHuman at scale, and the two things that will surprise you

- **Cost.** A MetaHuman at LOD0 with strand-based groom is a *cinematic* asset — high-poly body, several
  4K textures, complex skin shading, and hair strands that are among the most expensive things UE
  renders. Eight of them at LOD0 in a 1080p view is fine; forty is not. Policy from
  [06 §1](../06_REALISM_AND_SENSOR_MODEL.md) is correct and should be enforced in code: hero agents
  LOD0–2 with strands or cards, everyone else cards/LOD3+ or Mass crowd meshes. Add a runtime assert
  that at most `K` characters are above LOD2 in any camera's view.
- **Grooms are the first thing to cut.** Switching hair from strands to *cards* is usually the single
  biggest frame-time win available in a MetaHuman scene, and at CCTV resolution (a head is 15–40 px)
  it is visually free. Do it per-LOD and *measure*.
- **Runtime appearance change.** The realistic mechanism set: swap a *skeletal mesh component* for a
  garment slot (top/outer/bottom/shoes/headwear), drive colour/pattern/wetness through **material
  instance dynamic** parameters (and a Material Parameter Collection for global weather-driven
  wetness), toggle accessory components, and swap skin/base textures. What is *not* realistic at
  runtime: regenerating a MetaHuman's face/body from Creator parameters. **MetaHuman Creator produces
  assets at authoring time; there is no runtime "generate a new face" API.**
  [VERIFY — MetaHuman Creator's current delivery model changed with UE 5.6+ (Creator moving in-engine,
  new plugin names, and revised licence terms). Confirm at Epic's MetaHuman documentation and the
  MetaHuman licence page, both blocked here.]
  **Therefore identity diversity must be pre-baked**: author ~50–100 base MetaHumans, then multiply by
  garments × colours × patterns × hair × accessories × body-scale morphs at runtime to reach the
  ≥ 500 identities in [06 §5](../06_REALISM_AND_SENSOR_MODEL.md). Bake them in week 5 with editor
  Python; a batch of 100 is hours of GPU/CPU time and gigabytes of content, so it is a build artefact,
  not a runtime one.
- **Morphs/body variation.** Height and build variation is safest as *skeleton scaling plus a small
  set of body-type base meshes*, not as arbitrary runtime morph targets, because clothing meshes must
  follow. Mismatched garment/body scaling produces the classic poke-through that human observers spot
  immediately.
- **Chaos Cloth.** Real cost, per-character, on the CPU (with GPU paths available), and a determinism
  hazard. Use it for hero agents in close-range cameras only — exactly [06 §1](../06_REALISM_AND_SENSOR_MODEL.md)'s
  policy — and remember BEDLAM's evidence from [R04 §5.2](R04_degraded_imaging_and_sim2real.md) that
  *"clothing realistically simulated using commercial clothing physics simulation"* was part of why
  synthetic-only training worked for body-shape tasks. For us, the tasks that need it (attribute/ReID)
  are close-range; the tasks that do not (detection/tracking at 40 px) are far-range. So the cost/benefit
  aligns with the LOD split — a rare piece of good luck; exploit it.
- **Licence.** MetaHumans are usable **only in Unreal-Engine-rendered contexts** under Epic's terms —
  which is fine for rendering a dataset, and *not* fine for exporting the meshes into Blender or
  another renderer, or shipping the assets. [VERIFY — the exact MetaHuman licence wording and whether
  rendered *output* redistribution is unrestricted; this is the single most important licence question
  in the project and it must be answered in week 0, in writing. See §9.]

---

## 6. Sensor realism: in-engine vs post-process

The governing principle from [06](../06_REALISM_AND_SENSOR_MODEL.md) and
[R04 §5.4](R04_degraded_imaging_and_sim2real.md) is worth restating as an engineering rule:
**render clean and degrade in post, except where the effect needs scene information the renderer alone
has.** Post-processing is re-runnable (one render → many degrade profiles → curriculum datasets for
free), parameter-sweepable, testable in CI on a GPU-free machine, and inspectable. In-engine effects
are baked and unrepeatable.

The exceptions — effects that *must* be in-engine because they need geometry, materials or lighting:

| Effect | Where | Why |
|---|---|---|
| Lighting, GI, shadows, wet-surface roughness, puddles, headlights, IR illuminator *falloff on geometry* | In-engine | Needs the scene. |
| Rain/snow *in the volume*, splashes, fog scattering | In-engine (Niagara + volumetric fog) | Needs 3D placement and lighting interaction. |
| Camera *tilt/cover* tamper, PTZ motion, occluder placement | In-engine | It is a change to the world, not to the image. |
| Motion blur, rolling shutter | **Post**, from the velocity + depth buffers | We need controllable exposure time per camera; engine blur is screen-space and not parameterised in physical units. |
| Lens distortion, vignetting, chromatic aberration | **Post** (OpenCV `remap`) | Must be *invertible and consistent with the published intrinsics*. See §6.4. |
| Noise, ISP, WDR, auto-exposure lag, hot/dead pixels | **Post** | Physically parameterised, per-camera, re-runnable. |
| Rain-on-lens, dirt, spider webs | **Post** (sprite/alpha overlays) — or in-engine as a decal/post material if you want correct refraction | Either; post is cheaper and re-runnable. |
| Compression, packet loss, frame drop, OSD | **Post** (ffmpeg) | Obviously. |
| Thermal | **Hybrid** — see §6.3 | Needs material/temperature tagging in-engine. |

### 6.1 Noise and ISP

The correct model is the photon-transfer one: convert scene radiance to an expected photoelectron count
from exposure time, aperture, ISO/gain and quantum efficiency; apply **Poisson** shot noise on that
count; add **Gaussian** read noise; add fixed-pattern (per-pixel gain/offset) noise sampled once per
camera and *frozen for that camera's lifetime* (fixed-pattern noise that changes every frame is not
fixed-pattern noise — a common bug); then quantise. On top of that, the *ISP* is what makes real CCTV
look like CCTV: aggressive temporal denoise (which smears moving people — a strong, learnable cue),
sharpening halos, and WDR tone curves that crush contrast in the mid-tones. **The denoise smear is
probably the most under-modelled and most diagnostic artefact in cheap night-time CCTV**; if we model
only white noise we will produce night frames that no real camera ever produced.

### 6.2 Event cameras

If we ever want event data, the established route is to render at very high frame rate and convert:
**v2e** *"go[es] from conventional stroboscopic video frames with low frame rate into realistic
synthetic DVS event streams"*, modelling *"finite intensity-dependent photoreceptor bandwidth, Gaussian
pixel to pixel event threshold variation, and noise 'leak' events"*, with SuperSloMo interpolation for
temporal upsampling; MIT-licensed; and with the warning that *"v2e runs about 50-200X slower than real
time"* ([SensorsINI/v2e](https://github.com/SensorsINI/v2e)). For us the important craft note is that
**we can render at 200–1000 fps directly and skip the interpolation network**, which both removes v2e's
main artefact source and makes the cost a rendering cost rather than an inference cost. Low priority:
event cameras are not in the vendor's CCTV product surface. Note it in the backlog and move on.

### 6.3 Thermal

Nobody in this space renders true radiometric thermal; everyone fakes it with a temperature-tagged
material/ID pass. AirSim's approach is the documented reference and it is exactly the shape we
specified in [06 §3.4](../06_REALISM_AND_SENSOR_MODEL.md): it uses *"temperature, emissivity, and
camera response information to estimate the thermal digital count"* objects would produce, via a
preprocessing script (`create_ir_segmentation_map.py`) that *"reassign[s] segmentation IDs to match
calculated thermal digital counts"* before capture, and a capture script that records IR and visual
imagery in Computer Vision mode; temperature and emissivity values were *"derived from scientific
research"* for the Africa environment
([AirSim InfraredCamera.md](https://github.com/microsoft/AirSim/blob/main/docs/InfraredCamera.md)).

**This is directly portable to SurvSim and it is the right design**: our mask/ID pass already exists,
so a thermal frame is `ID → (T, ε)` lookup → `digital_count = f(T, ε, camera_response)` → palette. The
refinements that make it convincing for people: skin ≈ 33–36 °C at the surface (not 37 — clothing and
evaporation matter), *clothed* regions a few degrees above ambient and lagging it, exposed
face/hands/forearms hottest, breath plumes in cold air, hot engine bays and recently-parked vehicles,
sun-loaded surfaces retaining heat after dusk, glass as a mirror not a window, and wet surfaces reading
*cold*. Add per-camera NETD noise, the characteristic non-uniformity correction "shutter flash" every
few minutes, and a much narrower effective resolution (many real thermal cams are 384×288 or 640×512).
And the point from [R04 §5.4](R04_degraded_imaging_and_sim2real.md) applies doubly here: thermal is
where our *degradation channel* dominates realism, because the geometry is all that is real anyway.

CARLA, for the record, has **no thermal sensor** in its suite — one more reason the vehicle simulators
do not cover our product surface.

### 6.4 Lens distortion — and the trap

Two implementations: a UE post-process material that warps UVs (in-engine, GPU, cheap, and *visible in
the viewport*, which is good for placement sanity), or OpenCV `remap` in post (exact, invertible,
matches the published `k1..k3, p1, p2` / Kannala-Brandt coefficients).

**Use post, and here is the trap:** if you distort in post, then the projection you used for keypoints,
boxes and masks must be distorted *identically*, or every label is wrong by up to tens of pixels at the
frame edge. Concretely: render pinhole → project GT with pinhole K → **then apply the same distortion
map to both the image and the projected GT coordinates** (and re-derive mask-based boxes *after*
warping the mask). A distorted image with pinhole labels is the most insidious GT bug in this document
because it looks fine in the centre of frame, which is where you will happen to look. Make it a
reprojection unit test (§8.3) with a target placed deliberately at the corner.

### 6.5 Rolling shutter

A cheap, defensible approximation: render the frame, then per output row `r`, resample from a
time-warped position using the per-pixel velocity buffer scaled by `r · t_row`. This captures the
skew of a fast-moving person and the wobble of a PTZ pan, which are the visible effects, without a
per-row re-render. The exact approach requires rendering N sub-frames and compositing rows from each —
expensive, and worth doing only for a small validation subset so you can quantify the approximation
error and cite it. Document which you used per profile in the dataset card.

### 6.6 Compression and delivery

ffmpeg `libx264` with per-camera CRF/bitrate/GOP/B-frames, plus deliberate corruption: drop packets on
a copy of the stream and decode the damaged file to get *real* macroblock smears and frozen frames
rather than a synthetic imitation of them. Real CCTV also gives you: variable frame rate under motion
(many cameras drop to 6 fps when idle and jump to 25 fps on motion — a *massive* and rarely-modelled
domain feature), timestamp burn-in with drifting clocks, and multi-stream setups where the recorded
stream is a lower-resolution substream than the live one. All three are in
[06 §3.7–3.8](../06_REALISM_AND_SENSOR_MODEL.md); the VFR one deserves promotion because it changes
tracker behaviour more than noise does.

---

## 7. Data pipeline and scale

### 7.1 Storage maths — do this before you record anything

Per **camera-hour** at 25 fps = 90,000 frames.

| Stream | Format | Bytes/frame at 1920×1080 | Per camera-hour | Per camera-hour at 1280×720 |
|---|---|---|---|---|
| RGB, JPEG q90 | `.jpg` | ~250 KB | **~22 GB** | ~10 GB |
| RGB, PNG8 lossless | `.png` | ~2.5 MB | ~225 GB | ~100 GB |
| RGB, H.264 CRF 16 | in `.mp4` | ~60 KB eq. | **~5.4 GB** | ~2.4 GB |
| RGB, H.264 CRF 23 (the "delivered CCTV" profile) | `.mp4` | ~15 KB eq. | ~1.4 GB | ~0.6 GB |
| Depth, EXR half, ZIP | `.exr` | ~1.6 MB | **~144 GB** | ~64 GB |
| Depth, EXR half @ 5 Hz | `.exr` | — | ~29 GB | ~13 GB |
| Instance mask, PNG16 | `.png` | ~120 KB | ~11 GB | ~5 GB |
| Normal, PNG8 | `.png` | ~1.2 MB | ~108 GB | ~48 GB |
| GT JSON per frame (40 people, bones+boxes+kps) | `.jsonl`/parquet | ~25 KB / ~4 KB packed | ~2.2 GB / ~0.4 GB | same |

**The conclusions are stark and should drive policy:**

1. **Depth at full rate is the single largest line item — larger than lossless RGB.** Capture depth at
   5 Hz, not 25 Hz, unless a specific experiment needs more. That one decision saves ~115 GB per
   camera-hour.
2. **A 10-hour, 8-camera dataset is 80 camera-hours.** At the sensible profile (H.264 CRF16 RGB +
   5 Hz EXR depth + 5 Hz PNG16 masks + parquet GT) that is roughly
   `80 × (5.4 + 29 + 2.2 + 0.4)` ≈ **3 TB**. At the naive profile (PNG RGB + 25 Hz EXR depth + normals)
   it is `80 × (225 + 144 + 11 + 108)` ≈ **39 TB**. The BOM's 2 TB NVMe in
   [08](../08_ROADMAP_MILESTONES.md) is a *scratch* disk, not the dataset store — plan cold storage
   (an 8–16 TB HDD array or object storage) from week 0.
3. **Normals are optional.** Nothing in our task list consumes them. Capture them only for the EPE
   option (§4) and only for a sampled subset.
4. **GT should be parquet, not JSON, for anything per-frame-per-person.** A long-format table
   (`tick, cam_id, uid, x1,y1,x2,y2, kp[17×3], occ, trunc, zone, behaviour, ...`) in parquet with
   dictionary-encoded string columns is ~5–8× smaller than JSONL and ~50× faster to query. Keep
   *events* as JSONL (few rows, human-readable, append-friendly) and *calibration* as JSON per camera.
   This is exactly the split already in [05](../05_GROUND_TRUTH_AND_DATASET_FORMAT.md); the reason is
   the above.

### 7.2 Sharding and layout

One **take** = one scenario × one seed × one degrade profile, and it is the atomic unit of everything:
generation, caching, CI, splitting, deletion. Layout:

```
datasets/survsim-v0.2/
  takes/<env>__<scenario>__seed<NNNN>/
    meta/{scenario.resolved.yaml, seed.txt, manifest.json, engine.json, cvars.txt, git.json}
    frames/<cam>/{000000.jpg ...}   or video/<cam>.mp4
    depth/<cam>/*.exr   masks/<cam>/*.png
    gt/{world.parquet, percam.parquet, events.jsonl, calib/<cam>.json}
  splits/{train,val,test}.txt        # lists of take ids, never of frames
  dataset_card.md
```

Two rules with teeth: **splits are lists of takes, never of frames** (frame-level splits leak identity,
background and lighting across the split — see §8.5), and **`manifest.json` records everything needed to
regenerate the take**: git SHA of `survsim`, git SHA + build id of the UE project, engine version, GPU
model and driver version, every cvar actually in force, the resolved scenario, the seed, and the
wall-clock duration. If a take cannot be regenerated from its manifest, it is not reproducible, and
saying "reproducible" in a paper without that file is a bluff.

### 7.3 Multi-process and multi-GPU orchestration

UE is one process per instance and does not multi-GPU render usefully for our purposes, so scaling is
**embarrassingly parallel across takes**: `n_workers = min(GPUs × instances_per_GPU, CPU_cores / 4)`,
where `instances_per_GPU` is VRAM-bound (a City-Sample-class level with MetaHumans is comfortably
8–14 GB, so 1–2 instances per 24 GB card) and each instance needs its own UnrealCV port, its own output
directory and its own `-graphicsadapter=N`.

[Ray](https://github.com/ray-project/ray) (Apache-2.0) is the pragmatic orchestrator: Ray Core's
*"tasks: stateless functions executed in the cluster"*, *"actors: stateful worker processes"* and
*"objects: immutable values accessible across the cluster"* map cleanly onto "one take = one task",
"one UE instance = one actor holding a warm engine process", and "the take manifest = an object". The
*actor* mapping is the important one: **engine startup and shader/PSO warm-up is 30–120 s, so you must
reuse a warm engine across many takes**, which means the worker is stateful and must be *reset* between
takes (unload/reload level, reset RNG, clear streaming) — and you need a leak/drift detector that
recycles the actor every K takes, because UE processes accumulate memory and GPU state over hours.
A simpler alternative that works surprisingly well and is worth doing first: GNU `parallel`/`xargs -P`
over a take list with a per-take container, Kubric-style. Start there; move to Ray when the farm exceeds
one machine.

### 7.4 Cloud GPU costs per synthetic hour

Order-of-magnitude, on-demand US pricing as of 2026 — **[VERIFY all figures against current pricing
pages; cloud pricing changes monthly and every price below is from memory, not a fetched source]**:

| Option | Rough on-demand $/h | Notes |
|---|---|---|
| AWS `g5.2xlarge` (1× A10G 24 GB) | ~$1.2 | The workhorse. Good VRAM, adequate raster. |
| AWS `g6.2xlarge` (1× L4 24 GB) | ~$1.0 | Better perf/W, similar VRAM. |
| AWS `g6e.2xlarge` (1× L40S 48 GB) | ~$2.2 | Best for heavy Lumen/Nanite scenes. |
| Azure `NV`/`NVadsA10 v5` | ~$1.0–2.0 | Windows-friendly if you must run Windows builds. |
| RunPod / Lambda / Vast community RTX 4090 | ~$0.35–0.80 | Cheapest per raster-frame by a wide margin; no SLA, variable disk. |
| Owned RTX 4090 workstation | ~$0.05–0.10 amortised | Dominates on cost if utilisation > ~25 %. |

Now the number that matters. Suppose the batched pipeline sustains **8 cameras × 720p × 25 fps at 0.5×
real time** ([08 wk14](../08_ROADMAP_MILESTONES.md)'s acceptance). Then one *scenario-hour* (8
camera-hours of video) costs **2 GPU-hours** ≈ **$0.7–$2.4** in the cloud or ~**$0.15** on owned
hardware, plus egress if the data leaves the cloud (which at 3 TB per 10 h dataset is *the dominant
cost* on AWS at ~$0.09/GB ≈ **$270 per 10-hour dataset just to download it** — so **process in-cloud or
generate on-prem**; this is the single most commonly overlooked line item in synthetic-data budgeting).
A 100-hour dataset is therefore ~200 GPU-hours — a long weekend on four owned cards, or a few hundred
dollars of spot capacity. **Synthetic data generation is not compute-bound at our scale; it is
engineer-bound and storage-bound.** Plan staffing and disks, not GPUs.

### 7.5 Throughput engineering checklist

In rough order of payoff: batch one message per tick (§2.5) → `bCaptureEveryFrame=false` (§2.1) →
round-robin phases (§2.3.1) → native CCTV resolutions (§2.3.3) → async readback ring (§2.3.4) →
GPU H.264 instead of CPU PNG (§2.8) → depth at 5 Hz (§7.1) → groom cards not strands (§5.6) →
`r.Lumen.*` quality reductions and `r.Nanite.MaxPixelsPerEdge` relaxation for far cameras →
`ShowFlags` pruning per capture → disable Chaos Cloth on non-hero agents → warm engine reuse across
takes (§7.3). Measure with `stat unit`, `stat gpu`, `stat scenerendering` via `vrun`, and record
`GameThread/RenderThread/GPU` ms per take into the manifest so regressions are visible.

### 7.6 CI for scenario regression

Three tiers, because only the first can be free:

1. **GPU-free, every commit (minutes).** Mock backend only: schema validation of every YAML in
   `configs/`, behaviour-engine determinism (same seed → identical `events.jsonl` and `world.parquet`
   hashes), planner deadlock detection, all GT writers round-trip (MOT/COCO parse back to identical
   structures), degrade pipeline on fixture frames with a checksum, and the geometry/calibration unit
   tests of §8.3 on synthetic camera setups. This is the tier that catches 80 % of bugs and it is why
   the mock backend in [02](../02_ARCHITECTURE.md) exists.
2. **GPU nightly (tens of minutes).** Packaged Linux build in the container: `-nullrhi` level-load smoke
   test for every environment; then a 200-frame, 3-camera render of one canonical scenario with full GT;
   assert reprojection error, `bbox_visible ⊆ bbox_amodal`, mask-ID/uid consistency, no frame gaps, foot
   contact, and byte-identical GT against the previous night (pixels compared with a PSNR floor, not
   byte equality — see §8.2).
3. **Weekly (hours).** Full 1-hour multi-camera take, plus a downstream sanity model: train a small
   detector for a fixed short schedule on last week's take and this week's, and alert if AP moves more
   than a threshold. This catches the class of bug that produces *plausible-looking, systematically
   wrong* data — the worst kind — which no assertion catches.

Store the golden fixtures (a 20-frame take with its GT) in the repo via git-lfs; they are the only
thing that makes tier 1 meaningful.

---

## 8. Validation: how you know it is right

[R04 §5.5](R04_degraded_imaging_and_sim2real.md) covers the *sim-to-real* measurement programme (FID/KID
stratification caveats, the four downstream protocols, representation-gap diagnostics, human 2AFC). This
section covers the engineering validation that must pass *before* any of that is meaningful — because a
sim-to-real number computed on incorrect ground truth is worse than no number.

### 8.1 The validation pyramid

```
        downstream transfer (R04 §5.5)      ← only meaningful if everything below passes
      distributional realism (FID/KID, 2AFC)
   physical plausibility (speeds, spacing, contact)
  ground-truth correctness (reprojection, masks, IDs)      ← THE FOUNDATION
 determinism & reproducibility (seeds, manifests)
```

### 8.2 Determinism tests

- **`test_replay_identical`**: run the same seed twice; assert `sha256` equality of `world.parquet`,
  `events.jsonl` and `percam.parquet`. Pixels: assert PSNR > 50 dB rather than byte equality, and log
  the driver/GPU from the manifest so a genuine driver-induced change is attributable rather than
  mysterious.
- **`test_tick_monotonic`**: assert the in-engine tick counter returned with each frame increases by
  exactly 1 per director step. This is the CARLA-#9831 double-tick guard (§2.4.3) and it is three lines
  of code that will eventually save a week.
- **`test_fixed_delta`**: assert every reported `DeltaSeconds` equals `1/fps` to within 1e-6, and fail
  the take otherwise. This is the CARLA-#5498 flag-conflict guard.
- **`test_seed_isolation`**: change the behaviour-engine seed only; assert the population (identities,
  outfits) is *unchanged*. This proves the per-subsystem RNG split works and makes single-knob ablations
  trustworthy.
- **`test_no_wallclock_dependence`**: run once normally and once with an artificial 200 ms stall injected
  every 10 ticks; assert identical GT. Any difference means something is reading real time.

### 8.3 Ground-truth correctness tests

- **Reprojection round-trip.** For every labelled keypoint: project 3D → 2D with the published K/R/t,
  then back-project the 2D point using the depth buffer, and assert the recovered 3D point is within
  1 cm of the original. Target **mean reprojection error < 0.3 px, max < 1 px**. Run it with a target at
  the frame **corner** (§6.4) and with distortion applied.
- **Box consistency.** `bbox_visible` derived from the mask must be ⊆ `bbox_amodal`; both must be inside
  the frame after clipping; `occlusion_ratio` must equal `1 − area_visible/area_amodal` to within
  rounding; a person with `occlusion_ratio == 1.0` must be *absent* from the per-camera table or flagged,
  never present with a degenerate box (degenerate boxes silently poison MOT metrics).
- **ID consistency.** For every frame, the set of mask IDs present must be exactly the set of uids with
  `occlusion_ratio < 1`; and the stencil-id→uid map must be present in every frame's GT (§2.7a).
- **Cross-camera consistency.** Triangulate a person's pelvis from two overlapping cameras' 2D
  detections-from-GT and assert agreement with the world position to < 5 cm. This is the test that
  proves calibration and time-sync are jointly correct, and it is the one test unique to a
  multi-camera simulator.
- **Homography sanity.** Project the four corners of a known ground rectangle through the published
  ground-plane homography and assert closure to < 2 px. Every downstream MTMC baseline depends on it.
- **Foot contact.** As §5.2: lowest foot bone within ±2 cm of traced ground for ≥ 99 % of walking frames.
- **Temporal continuity.** Assert no person's world position jumps more than `v_max · dt` between ticks
  (catches teleporting spawns, nav failures and mid-take handle reassignment), and that identity uids
  are never reused within a take.
- **Physical plausibility distributions.** Pedestrian speed histogram in 0.8–1.8 m/s as
  [06 §4](../06_REALISM_AND_SENSOR_MODEL.md) requires, minimum interpersonal distance ≥ 0.4 m outside
  contact behaviours, queue spacing 0.6–1.2 m. Publish the histograms in the dataset card; they are
  cheap and they are the first thing a sceptical reviewer asks for.

### 8.4 Visual/overlay verification — do not skip this

Build the GT overlay tool in **week 3**, not week 10. It draws boxes, masks, keypoint skeletons, uids,
occlusion ratio and behaviour labels onto the frames and writes a contact-sheet MP4 per camera. Every
GT bug class described in §2.7 — off-by-one stencil IDs, pinhole-vs-distorted labels, `GetActorBounds`
padding, a frame/tick misalignment of exactly one — is *instantly* visible in an overlay video and
*invisible* in a metric. [08](../08_ROADMAP_MILESTONES.md) already makes this a week-3 acceptance
criterion (*"per-camera MOT GT visually aligned (overlay tool)"*); this section is the argument for why
that is the right priority.

### 8.5 GT leakage — the pitfalls that silently inflate every number

Synthetic data makes leakage *easy*, because everything is correlated with everything by construction.
The traps, each with its fix:

1. **Frame-level splits.** Adjacent frames are near-duplicates; a frame-level split gives a val set that
   is 99 % the train set. **Fix: split by take** (§7.2), and preferably by *environment* and *identity*
   too for the hardest split.
2. **Identity leakage across splits.** The same MetaHuman base + outfit appearing in train and test makes
   ReID trivially easy and the number meaningless. **Fix: partition the identity pool disjointly, and
   record the partition in the dataset card.** Also partition *garment meshes*, not just identities — a
   model can memorise a jacket.
3. **Background/environment leakage.** Train and test in the same level means a detector can use scene
   context. **Fix: hold out at least one environment entirely.**
4. **Camera-pose leakage.** The same extrinsics in train and test lets a model memorise the ground plane
   and person scale-vs-y relationship — this is the exact failure GMVD was built to expose. **Fix: hold
   out camera configurations, and report a "novel camera topology" test set.**
5. **Behaviour-label leakage through a rendering artefact.** If "loiterer" agents are all rendered with
   cloth sim on and commuters with it off, or all anomalous agents spawn at t=0 while normals stream in,
   the classifier learns the artefact. **Fix: randomise rendering/LOD/spawn policy *independently* of
   behaviour label, and test it — train a classifier on a *single frame* per clip; if it can predict the
   behaviour label well above chance from one frame, you have a leak.** This is the cheapest and most
   revealing leakage test in the list, and it belongs in weekly CI.
6. **Seed leakage.** Using consecutive seeds for train and test while the population generator uses the
   seed as a low-entropy input can correlate the sets. **Fix: hash the seed with the subsystem name
   (already the policy in §2.4.1) and use widely separated seed ranges per split.**
7. **Degrade-profile leakage.** The *same clean render* exported at profile A for train and profile B for
   test is *not* an independent test set; it shares every geometric and identity fact. **Fix: be explicit
   that a profile ladder measures robustness, not generalisation, and never report it as the latter.**
   This one is subtle and it is the most likely way *we* would accidentally overclaim.
8. **Open-set anomaly leakage.** UBnormal's design answer is the right one: *"disjoint sets of anomaly
   types in our training and test collections of videos"*
   ([UBnormal](https://github.com/lilygeorgescu/UBnormal)). Copy it: the behaviour catalogue must declare
   per-type train/test membership, and the ["what counts as anomalous"](../03_BEHAVIOUR_CATALOG.md) split
   must be published.

### 8.6 Realism validation, engineering-side

Two additions to [06 §4](../06_REALISM_AND_SENSOR_MODEL.md) worth stating as *tests*:
(i) **the FID reference set must be rendered losslessly and stratified by camera and profile**, per
[R04 §5.5](R04_degraded_imaging_and_sim2real.md) — so reserve a lossless subset at generation time,
because you cannot recover it later; (ii) **run the domain-classifier diagnostic as a CI job**: train a
small CNN to separate our frames from WILDTRACK/MEVA crops, report AUC per profile, and *use its
saliency maps* to find what gives us away. In practice that saliency map finds: over-clean pavement,
absent motion-denoise smear, too-perfect timestamp fonts, and identical asphalt tiling. All four are
one-day fixes once you know.

---

## 9. Licensing gotchas, per asset source

**This section is a legal-risk map, not legal advice. Every row must be re-read from the primary licence
before the first external data release.** The general pattern, which recurs everywhere: **the code is
permissive and the *assets* are not.**

| Source | What we want | The gotcha | Action |
|---|---|---|---|
| **UE5 engine** | Render our dataset | The EULA governs distribution of the engine and of engine-derived tooling/containers; royalties apply to *games*, not to internal tools or rendered output. Container images containing the engine may not be publicly distributed. | Private registry only (§2.6). [VERIFY] |
| **MetaHuman** | Photoreal identities | Usable **only in UE-rendered** contexts — no export to other renderers. Terms changed with the 5.6+ in-engine Creator. Whether *rendered frames* are freely redistributable is the critical question. | **Week 0, in writing.** [VERIFY at Epic's MetaHuman licence page] |
| **Fab (ex-Marketplace/Quixel)** | Garments, props, environments | Fab has **Standard vs Personal** licence tiers; "Personal" forbids commercial/organisational use, and some packs are per-seat. Megascans' 2025 move to Fab changed the previously "free for UE use" position for some content. | Record the licence tier **per asset** in an asset manifest; forbid Personal-tier assets in any take used for a deliverable. [VERIFY current Fab terms] |
| **City Sample** | Crowd + city environment | Free sample project, but sample content licences sometimes restrict use outside UE projects; the crowd characters are not MetaHumans. | Confirm before publishing frames. [VERIFY] |
| **UnrealZoo** | 100+ environments, agents | **Apache-2.0 covers the code; the 70 GB of scene content has per-scene provenance** (some scenes originate from Marketplace/Fab packs). | Audit per-scene provenance before shipping frames from a scene. ([repo](https://github.com/UnrealZoo/unrealzoo-gym)) |
| **UnrealCV** | Transport, commands | MIT. Clean. Citation requested (ACM MM 2017). | Cite. ([repo](https://github.com/unrealcv/unrealcv)) |
| **Mixamo** | Animations | Free with an Adobe account; historically permits use in projects but **not redistribution of the raw animation files**. Rendered output is the intended use. | Never ship FBX; ship frames. [VERIFY current Adobe terms] |
| **AMASS / SMPL / SMPL-X** | Realistic gait, body model | **"non-commercial scientific research purposes"**; commercial licence via `ps-licensing@tue.mpg.de`. Derived motion plausibly inherits this. | Maintain an **AMASS-free default motion set**; flag AMASS runs research-only. ([amass](https://github.com/nghorbani/amass), [smplx](https://github.com/vchoutas/smplx)) |
| **BEDLAM** | Motions, reference pipeline | Own licence page; the render tooling is a separate repo. | Read the licence; the *tooling ideas* are free to copy. ([bedlam_render](https://github.com/PerceivingSystems/bedlam_render)) |
| **RenderPeople / AXYZ / Ten24 scanned humans** | High-fidelity background humans | Per-model licences, usually per-seat, often forbidding use in "datasets" or ML training explicitly. | Read each EULA; many explicitly exclude ML training — assume excluded until proven otherwise. [VERIFY] |
| **UBnormal** | Anomaly benchmark comparison | **CC BY-NC-ND 4.0** — non-commercial **and no derivatives**. | Compare against it; never redistribute or remix. ([repo](https://github.com/lilygeorgescu/UBnormal)) |
| **GRUtopia / GRScenes** | Scenes, NPC ideas | Code MIT; assets **CC BY-NC-SA 4.0**. | Ideas only; no commercial dataset. ([repo](https://github.com/OpenRobotLab/GRUtopia)) |
| **IntPhys 2** | Method reference | **CC BY-NC 4.0**, evaluation-only, explicitly prohibiting *"generative AI applications that create new content"*. | Read-only reference. ([repo](https://github.com/facebookresearch/IntPhys2)) |
| **BlenderProc** | Offline rendering | **GPL-3.0**. | Fine as a separate tool invoked as a process; do not vendor into our package. ([repo](https://github.com/DLR-RM/BlenderProc)) |
| **libpedsim (pedsim_ros)** | Social force reference | **LGPL** core, BSD wrappers. | Read and reimplement; do not link. ([repo](https://github.com/srl-freiburg/pedsim_ros)) |
| **RVO2 / Menge / Kubric / Infinigen / PeopleSansPeople / Ray / mediamtx / v2e / EasySynth** | Planner, ideas, tooling | Apache-2.0 / BSD-3 / MIT — all clean. | Use freely, attribute. |
| **Isaac Sim** | Optional backend | Code Apache-2.0; **container images under the NVIDIA Omniverse License Agreement**. | Watch the code/image split. ([repo](https://github.com/isaac-sim/IsaacSim)) |
| **Real reference sets (WILDTRACK, MEVA, DukeMTMC, MOT17/20)** | FID reference, transfer eval | Research-only, and **DukeMTMC was withdrawn** by its authors on ethics grounds. | Use for internal evaluation only; do not redistribute crops; prefer WILDTRACK/MEVA/MOT for anything reported, and note DukeMTMC's status if used at all. |

**The two decisions that follow from this table.** First: **maintain an "all-redistributable" asset
subset** (already the mitigation in [08's risk register](../08_ROADMAP_MILESTONES.md)) and make the
dataset generator able to run in `--clean-assets` mode, so there is always a version of every dataset we
can hand to a customer. Second: **ship configs + seeds + a generator, not only frames.** A reproducible
recipe is licence-immune in a way that a tarball of pixels is not, and it is also a better scientific
artefact.

---

## 10. Forty-plus pitfalls, with sources

Ordered by the phase in which they bite. Sourced items link; unsourced ones are engineering lore and are
marked *(lore)*.

**Capture and rendering**

1. `bCaptureEveryFrame` left on → every camera renders every engine frame; framerate collapses in an
   empty level. *(lore; §2.1)*
2. Capturing `FinalColorLDR` for every camera → the whole post-process chain runs N times. *(lore)*
3. TAA/TSR/DLSS on during a labelled pass → masks arrive as *"scattered, noisy colored pixels"*
   ([unrealcv #331](https://github.com/unrealcv/unrealcv/issues/331)).
4. Anti-aliasing method other than none/FXAA in a GT pipeline → EasySynth documents *"Anti-aliasing
   requires FXAA method specifically"* ([EasySynth](https://github.com/ydrive/EasySynth)).
5. Engine motion blur left on → blur you cannot parameterise and cannot remove. *(lore; §2.2)*
6. Auto-exposure on → per-frame brightness drift uncorrelated with your exposure model. *(lore)*
7. `-nullrhi` instead of `-RenderOffscreen` → a running sim that captures nothing. *(lore; §2.3.5)*
8. Screen resolution silently wrong → UnrealCV lists *"screen resolution problems"* with the `setres`
   / config-file fix ([issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)).
9. Synchronous `ReadPixels` on the game thread → a GPU flush per camera per frame. *(lore; §2.3.4)*
10. Async readback ring not drained at shutdown → the last 2–3 frames of every take are missing. *(lore)*
11. Rendering 4K and downsampling to model a cheap camera → 9× cost and a *worse* model. *(lore)*
12. Trusting the engine velocity buffer for skinned characters → EasySynth: *"optical flow rendering
    assumes all objects other than the camera are stationary"*
    ([EasySynth](https://github.com/ydrive/EasySynth)).
13. Texture/shader pop-in in the first frames of a take → use warm-up frames and
    `r.Streaming.FullyLoadUsedTextures 1`; MRQ does this for you. *(lore; §2.4.7)*
14. Pixel Streaming chosen as the capture path → one lossy view, no GT. *(lore; §2.3.6)*

**Ground truth**

15. **Skeletal meshes crash the segmentation pass**: *"Any skeletal mesh causes a 100% crash for
    segmentation. VertexFactory not initialized error"*, on UE 5.3 *and* 5.6
    ([#339](https://github.com/unrealcv/unrealcv/issues/339)). For a people simulator this is
    existential — implement your own stencil pass.
16. Instance IDs encoded as 8-bit colour → *"the images saved using the vget command show no difference
    at all"* despite being visible in the viewport
    ([#330](https://github.com/unrealcv/unrealcv/issues/330)).
17. 8-bit stencil = 255 IDs; >255 people/props silently collide. *(lore; §2.7a)*
18. Objects present in lit but absent in mask mode, and vice versa
    ([#287](https://github.com/unrealcv/unrealcv/issues/287)).
19. Viewmode switching is order-dependent: *"switching my scene from lit to object_mask (P1) differ from
    switching from depth/normal to object_mask (P2)"* ([#285](https://github.com/unrealcv/unrealcv/issues/285)).
20. Mask capture works in PIE, fails in Standalone
    ([#282](https://github.com/unrealcv/unrealcv/issues/282)).
21. Camera moved but the capture returns the initial view — a frame-ordering bug
    ([#275](https://github.com/unrealcv/unrealcv/issues/275)).
22. Niagara particles invisible in depth; mesh-particle conversion and collision do not help
    ([#271](https://github.com/unrealcv/unrealcv/issues/271)). Make it a *documented* property.
23. Normalised depth with a user-set range → silent clipping beyond the range on long-throw cameras
    ([EasySynth](https://github.com/ydrive/EasySynth) documents the pattern).
24. Ray-length vs z-depth confusion → a cosine bias toward frame edges that corrupts every
    back-projection. *(lore; §2.7b)*
25. `GetActorBounds` as the 2D box → 20–40 % oversized, and worse with limbs extended. *(lore; §2.7d)*
26. Distorting the image in post but not the labels → edge labels wrong by tens of pixels, centre labels
    fine, so you will not notice. *(lore; §6.4)* — the most insidious bug in this document.
27. Two copies of the projection maths (one for GT, one for `calib.json`) drifting apart. *(lore)*
28. Two-valued keypoint visibility (in/out of frame) instead of three-valued (truncated / occluded /
    visible). *(lore; §2.7c)*
29. MetaHuman skeleton assumed to be COCO-17 or SMPL-X's *"54 joints"*
    ([smplx](https://github.com/vchoutas/smplx)) → silent keypoint mis-mapping.
30. Degenerate (zero-area) boxes for fully-occluded people left in the per-camera table → poisoned MOT
    metrics. *(lore; §8.3)*
31. Occlusion ratio *estimated from geometry* instead of *measured* from a two-pass mask. *(lore; §2.7e)*

**Determinism**

32. One step command advancing two engine frames — CARLA's *"Synchronous mode: one tick_cue produces two
    world frames (double-tick)"* (#9831,
    [search](https://github.com/carla-simulator/carla/issues?q=determinism)).
33. Two mechanisms both claiming to set the timestep — CARLA's *"Unclear interaction between carla
    executable -fps, -benchmark arguments and fixed-timestep synchronous mode"* (#5498, *ibid.*).
34. Physics determinism assumed rather than tested — CARLA needed a *"Temporary fix for collision
    determinism test"* (#8899, *ibid.*).
35. Mass processors running multithreaded during a recorded run — `mass.FullyParallel`,
    `ParallelForEachEntityChunk` ([MassSample](https://github.com/Megafunk/MassSample)).
36. Direct Mass entity composition changes during processing — *"only truly safe to call outside of
    processing on the main thread"* (*ibid.*).
37. Background Mass crowd used as labelled ground truth, when `MassLOD` makes its tick rate
    *viewpoint-dependent by design* (*ibid.*).
38. One global RNG shared across subsystems → adding a behaviour call reshuffles every outfit. *(lore)*
39. `dict`/`set` iteration order leaking into RNG consumption order. *(lore)*
40. Level streaming or GC completing on a different frame between runs. *(lore; §2.4.7)*
41. Motion Matching cost function with a random or time-based tie-break. *(lore; §5.4)*

**Humans and motion**

42. A-pose/T-pose retarget mismatch → twisted forearms and hyperextended knees. *(lore; §5.2)*
43. Metric/centimetre and pivot mismatch → floating or sinking feet, the #1 "obviously synthetic" tell.
    *(lore; §5.2)*
44. Runtime garment swap on a body whose scale differs from the garment's → poke-through. *(lore; §5.6)*
45. Expecting a runtime "generate a new MetaHuman face" API. There is none; bake variants offline.
    *(lore; §5.6)*
46. Strand grooms on 40 characters → frame time collapse for pixels smaller than a hair. *(lore; §5.6)*
47. Expecting motion synthesis to invent the hard behaviours — MotionGPT *"struggles with complex, unseen
    motions"* and is *"limited by small datasets (HumanML3D: 14,616 motions...)"*
    ([MotionGPT](https://github.com/OpenMotionLab/MotionGPT)).
48. Physically-negotiated fighting instead of paired montages → non-deterministic and looks worse.
    *(lore; §5.3)*

**Platform, pipeline, legal**

49. Depending on a large third-party framework: AirSim *"Microsoft decided to shutdown in July of 2022"*
    ([Colosseum](https://github.com/CodexLabsLLC/Colosseum)), Colosseum *"archived on July 11, 2026"*
    (*ibid.*), Unity Perception *"discontinued and no longer supported"*
    ([repo](https://github.com/Unity-Technologies/com.unity.perception)), TDW in *"long-term support"*
    ([repo](https://github.com/threedworld-mit/tdw)), Isaac's docker repo *"deprecated and archived"*
    ([repo](https://github.com/NVIDIA-Omniverse/IsaacSim)).
50. Vulkan/driver mismatch on Linux — *"Ubuntu 22.04 currently lacks proper Vulkan support; Docker
    deployment is recommended"* ([Colosseum](https://github.com/CodexLabsLLC/Colosseum)); legacy OpenGL
    debugging via *"mesa-utils and ... glxgears"*
    ([issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)).
51. Undocumented toolchain pins — Isaac Sim needs *"GCC/G++ version 11 specifically (versions 12+
    unsupported)"* ([IsaacSim](https://github.com/isaac-sim/IsaacSim)); BEDLAM pinned *"UE 5.0.3 for
    Windows"* ([bedlam_render](https://github.com/PerceivingSystems/bedlam_render)).
52. Under-specced RAM — BEDLAM's node spec is *"128GB or more"* (*ibid.*).
53. Full-rate EXR depth as the default → larger than lossless RGB; ~144 GB per camera-hour. *(derived;
    §7.1)*
54. Cloud **egress** ignored → ~$270 to download one 10-hour dataset from AWS. *(derived; §7.4)*
55. Cold engine start per take (30–120 s warm-up) instead of a warm reused worker. *(lore; §7.3)*
56. Frame-level train/test splits, shared identities, shared garments, shared cameras, shared
    environments. *(lore; §8.5)*
57. Non-commercial assets in a commercial dataset — GRScenes *CC BY-NC-SA 4.0*
    ([GRUtopia](https://github.com/OpenRobotLab/GRUtopia)), UBnormal *CC BY-NC-ND 4.0*
    ([repo](https://github.com/lilygeorgescu/UBnormal)), IntPhys 2 *CC BY-NC 4.0*
    ([repo](https://github.com/facebookresearch/IntPhys2)), AMASS/SMPL-X *"non-commercial scientific
    research purposes"* ([amass](https://github.com/nghorbani/amass)).
58. Assuming a permissive *code* licence covers the *assets* — Apache-2.0 UnrealZoo code over 70 GB of
    third-party scenes ([repo](https://github.com/UnrealZoo/unrealzoo-gym)); Apache-2.0 Isaac Sim code
    with images under the *"NVIDIA Omniverse License Agreement"*
    ([repo](https://github.com/NVIDIA-Omniverse/IsaacSim)).
59. Running the pipeline from editor Python and discovering there is no Python in a packaged build.
    *(lore; §2.5)*
60. A silently-dropping frame writer queue → a dataset with invisible gaps. *(lore; §2.8)*
61. Reporting a degrade-profile ladder as evidence of *generalisation*. *(lore; §8.5.7)*

---

## 11. The validated build recipe, weeks 0–8

This expands [08_ROADMAP_MILESTONES.md](../08_ROADMAP_MILESTONES.md) with the specific plugins, cvars,
commands and code shapes, and reorders two things based on §2–§3: **the custom mask/GT pass moves
earlier (week 3, before Demo 1)** because UnrealCV's segmentation path crashes on skeletal meshes
([#339](https://github.com/unrealcv/unrealcv/issues/339)), and **the packaged-Linux container becomes an
acceptance gate from week 3** rather than a week-14 task.

### Week 0 — decisions, not code

Install: UE **5.7** (match [UnrealZoo](https://github.com/UnrealZoo/unrealzoo-gym)) from source (needed
to build plugins and to package Linux), the UnrealZoo binary bundle (~70 GB), Python 3.10+, ffmpeg 6,
Docker + NVIDIA Container Toolkit.

Enable exactly these plugins in the project (names to confirm per 5.7): `UnrealCV` (or UnrealCV+ from the
UnrealZoo fork — **decide which fork and record it**), `MetaHuman` / `MetaHumanCharacter`,
`MassEntity`, `MassGameplay`, `MassAI`, `StateTree`, `SmartObjects`, `ZoneGraph`, `PoseSearch`
(Motion Matching), `ControlRig`, `IKRig`, `MovieRenderPipeline` + `MovieRenderPipelineEXR`-style writers,
`ChaosCloth`, `Niagara`, `SunPosition`, `EditorScriptingUtilities`, `PythonScriptPlugin` (editor-only —
see §2.5), `GeometryCache` (if you ever take BEDLAM's Alembic route), `RuleProcessor` (optional, for
rule-based scattering). **[VERIFY every plugin name against the 5.7 plugin browser.]**

Answer in writing, in `docs/decisions/`:
- the MetaHuman licence question (§9) — *blocking*;
- which UnrealCV fork and its command set (§3.1);
- the three UnrealZoo agent questions (§3.4);
- the storage plan from §7.1 (a number of terabytes, and where they live).

Benchmark, and commit the numbers to the repo: single-camera `vget /camera/0/lit png` round-trip latency;
same for `depth` and `object_mask`; then 8 cameras × 3 modalities. This is your baseline and every later
optimisation is measured against it.

### Week 1 — core models + mock backend

Unchanged from [08](../08_ROADMAP_MILESTONES.md). One addition: write the **geometry/calibration module
first and share it between the mock backend, the UE backend and the writers** — one `Camera` class that
owns `K`, `dist`, `R`, `t`, `project()`, `unproject()`, `homography_to_ground()`, and is the *only* place
projection maths exists (pitfall 27). The mock backend then exercises the same projection code that
production uses, which is why tier-1 CI is meaningful.

### Week 2 — behaviour engine + planner

Unchanged. Use [RVO2](https://github.com/snape/RVO2)'s Python binding for ORCA, layered under a
social-force comfort term; read [pedsim_ros](https://github.com/srl-freiburg/pedsim_ros) and
[Menge](https://github.com/MengeCrowdSim/Menge) for the force formulations but **reimplement** (LGPL,
§9). Add the deadlock checker and the `test_no_wallclock_dependence` determinism test (§8.2) now, while
the system is small enough to fix.

### Week 3 — UE backend v1 **plus the custom GT pass** (the critical week)

Python side: `UnrealBackend` over TCP with **one message per tick** (§2.5), async capture ring (§2.3.4),
UE-cm-LH → SI-m-RH conversion at the boundary.

UE side, `SurvSimPlugin`, in this order:
1. `ASurvSimCCTVCamera`: a `USceneCaptureComponent2D` per modality, `bCaptureEveryFrame = false`,
   explicit `CaptureScene()` from a subsystem tick, `ShowFlags` pruned per modality, per-camera
   `PostProcessSettings` with AA/bloom/AO/motion-blur/auto-exposure off.
2. **`USurvSimSegmentationPass`**: our own custom-depth-stencil (or `PrimitiveID`) instance pass,
   written as **16-bit single-channel**, with a per-frame `stencil_id → uid` map in the GT.
   **Validate against an animated MetaHuman on day 1** — this is the de-risking of
   [#339](https://github.com/unrealcv/unrealcv/issues/339) and the most important task of the week.
3. `USurvSimGTSubsystem`: bone transforms, mask-derived visible boxes, two-pass amodal via
   `UseShowOnlyList`, depth-test keypoint visibility, per-camera JSON keyed by sim tick.
4. Console setup applied at take start via `vrun`, and echoed into `meta/cvars.txt`:
   ```
   vrun r.AntiAliasingMethod 0
   vrun r.ScreenPercentage 100
   vrun r.MotionBlurQuality 0
   vrun r.DefaultFeature.AutoExposure 0
   vrun r.DefaultFeature.MotionBlur 0
   vrun r.DefaultFeature.Bloom 0
   vrun r.Streaming.FullyLoadUsedTextures 1
   vrun mass.FullyParallel 0
   vrun t.MaxFPS 0
   ```
5. Stepped loop, guarded:
   ```python
   ue.send({"cmd": "survsim/tick", "t": t, "people": [...], "cameras": [...]})
   ue.send("vset /action/game/pause")          # step exactly one fixed delta
   st = ue.send("vget /survsim/step 1")         # returns {"tick": n, "delta": 0.04}
   assert st["tick"] == prev_tick + 1           # CARLA #9831 guard
   assert abs(st["delta"] - 1/fps) < 1e-6       # CARLA #5498 guard
   frames = ring.collect(tick=st["tick"] - 2)   # async readback, 2-frame latency
   gt = ue.send("vget /survsim/gt")
   ```
6. **The overlay tool** (§8.4) and the reprojection test (§8.3). Acceptance: mean reprojection error
   < 0.3 px, and a human can see boxes and skeletons sitting correctly on people in an MP4.
7. **Package a Linux build and run all of the above in the container** (§2.6). From now on, PIE-only
   results do not count.

### Week 4 — Demo 1

As [08](../08_ROADMAP_MILESTONES.md): 4 cameras, 10 people, loiter + object-abandon in an UnrealZoo
outdoor scene, ByteTrack + HOTA. Add: the storage figure per hour measured for real, the GT test suite
green in CI, and the take `manifest.json` (§7.2) present and sufficient to regenerate the demo.

### Week 5 — Person actor and the identity factory

`ASurvSimPersonActor` on a MetaHuman base: garment slots as child skeletal mesh components, colour/
pattern/wetness through `UMaterialInstanceDynamic` + a weather Material Parameter Collection, accessory
components, hair as cards for non-hero LODs. **Bake 50–100 base MetaHumans with editor Python** (§2.5,
§5.6) into a content pak; the runtime combinatorics (garments × colours × patterns × hair × accessories
× body scale) produce ≥ 500 identities. Deliverable, per [08](../08_ROADMAP_MILESTONES.md): a contact
sheet of 50 identities, plus — added here — **an identity-partition file** assigning identities to
train/val/test disjointly from day one (§8.5.2), because retrofitting it later invalidates earlier
results.

### Week 6 — animation and gait

Batch-retarget Mixamo with editor Python through `IKRig`/`IKRetargeter`; build one Motion Matching
database per gait style (§5.4); Control Rig posture layers for limp/slouch/crouch/carrying; action
montages for phone/sit/crouch-work/spray/climb/fall plus **paired** fight sets (§5.3). Add the
**foot-contact CI test** (§5.2) and a `gait_classifier` smoke test: a tiny classifier on GT joint
trajectories should distinguish the 8 gait styles well above chance — if it cannot, the styles are not
actually distinct and no human will see them either.

### Week 7 — CCTV camera actor and degrade pipeline v1

PTZ as spring-arm rotation + FOV zoom, patrol schedules, tamper actions that are *real world changes*
(tilt the actor, spawn a cover mesh) per §6. Post pipeline in Python: distortion (**with labels warped
identically** — §6.4, pitfall 26), exposure, Poisson+Gaussian+fixed-pattern noise, motion blur from the
**validated** velocity buffer (§2.2), H.264 via ffmpeg, OSD. Reserve a **lossless subset** for FID
(§8.6). Validate the velocity buffer with the walking-checkerboard test before trusting any blurred
frame.

### Week 8 — Demo 2

Transit-station scenario, 8 cameras incl. PTZ, hard negatives, degrade profiles, 1-hour dataset v0.1,
eval report. Added acceptance gates: (i) the cross-camera triangulation test (§8.3) passes at < 5 cm;
(ii) the single-frame behaviour-leakage probe (§8.5.5) is at chance; (iii) the whole take is generated
by the container pipeline from a manifest with no manual steps; (iv) the measured throughput and the
storage-per-hour figure are in the README.

### The three things most likely to slip, and the pre-agreed fallbacks

| Risk | Fallback |
|---|---|
| Custom segmentation pass fights UE's skinned vertex factory ([#339](https://github.com/unrealcv/unrealcv/issues/339)) | Fall back to **MRQ two-pass** offline rendering for masks (BEDLAM's proven route, §1.4) and accept slower-than-real-time GT generation. Demo 1 still ships. |
| MetaHuman licence blocks the deliverable | Switch the "clean-assets" identity tier to purchased-or-CC0 characters; keep MetaHuman for internal realism work only. Decided in week 0, so no rework. |
| Throughput below 0.25× real time at 8 cameras | Round-robin phases (§2.3.1) + 704×576 for the far cameras + depth at 5 Hz + [Runtime Video Recorder](https://github.com/unrealcv/unrealcv/issues/283) for GPU-side encoding. These are all *configuration*, not rework — which is why they belong in the design now. |

---

## 12. Hop-chain appendix

How the sources were reached — the "seven-to-eight hops" of this investigation, all by direct fetch
(search was unavailable; §0). Each arrow is a link actually followed.

**Chain A — the capture-path chain (8 hops).**
`docs/01` names UnrealCV as the primary backend → [unrealcv README](https://github.com/unrealcv/unrealcv)
(MIT, UE 5.2+, points at UnrealZoo for binaries and mentions UnrealCV+) →
[commands.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/commands.rst)
(the five command families; `vrun` passthrough) →
[issues.rst](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)
(known issues: performance, OpenEXR, *"image and ground truth misalignment"*, Linux OpenGL) →
[open issue list](https://github.com/unrealcv/unrealcv/issues) (nine of twelve are GT-path bugs) →
[#339 skeletal-mesh segmentation crash](https://github.com/unrealcv/unrealcv/issues/339) →
[#283 Runtime Video Recorder recommendation](https://github.com/unrealcv/unrealcv/issues/283) →
[IntPhys 2](https://github.com/facebookresearch/IntPhys2) (UE 5.4, 253 scenes, CC BY-NC 4.0) — which
validates the alternative capture path *and* supplies a licence data point for §9.

**Chain B — the human-render chain (7 hops).**
[R04 §5.2](R04_degraded_imaging_and_sim2real.md) cites BEDLAM's synthetic-only SOTA →
[pixelite1201/BEDLAM](https://github.com/pixelite1201/BEDLAM) (points at a separate render repo) →
[PerceivingSystems/bedlam_render](https://github.com/PerceivingSystems/bedlam_render) (*"UE 5.0.3"*,
MRQ with *"7 temporal samples"*, a separate GT pass *"without spatial/temporal sampling"*,
*"multilayer, cryptomatte"* EXR, Alembic geometry caches with *"pose correctives ... baked"*,
128 GB RAM) → [smplx](https://github.com/vchoutas/smplx) (*"54 joints"*, *"non-commercial scientific
research purposes"*) → [amass](https://github.com/nghorbani/amass) (same licence; SMPL+H; SMPL-X
compatible) → [MDM](https://github.com/GuyTevet/motion-diffusion-model) (MIT, ~0.4 s/sample, motion
inpainting) → [MotionGPT](https://github.com/OpenMotionLab/MotionGPT) (*"struggles with complex, unseen
motions"*; HumanML3D is 14,616 motions) — producing §5.2–§5.3's "synthesise variation, not the hard
behaviours" rule and §9's AMASS-free-default policy.

**Chain C — the platform-mortality chain (8 hops).**
`docs/01` lists AirSim as a candidate → [microsoft/AirSim](https://github.com/microsoft/AirSim) (MIT,
pause/continue, CV mode) → [AirSim InfraredCamera.md](https://github.com/microsoft/AirSim/blob/main/docs/InfraredCamera.md)
(the temperature/emissivity/digital-count thermal recipe → §6.3) →
[Colosseum](https://github.com/CodexLabsLLC/Colosseum) (AirSim *"shutdown in July of 2022"*; UE 5.6;
*"Ubuntu 22.04 currently lacks proper Vulkan support"*; itself *"archived on July 11, 2026"*) →
[ue4-docker](https://github.com/adamrehn/ue4-docker) (offscreen rendering via the NVIDIA Container
Toolkit → §2.6) → [Unity Perception](https://github.com/Unity-Technologies/com.unity.perception)
(*"discontinued"*) → [PeopleSansPeople](https://github.com/Unity-Technologies/PeopleSansPeople)
(28 humans, 39 clips, 21,952 textures, 490k images, the 46.40-vs-23.51 keypoint-AP result) →
[MultiviewX](https://github.com/hou-yz/MultiviewX) via [MVDet](https://github.com/hou-yz/MVDet)
(6 synchronised cameras, 1920×1080, WILDTRACK-mirrored, and the
`generateAnnotation/calibrateCamera/generatePOM/unitConversion` toolkit that became §4's spec for
`tools/`). Conclusion drawn in §1.6: keep our UE surface area portable, because everything in this chain
is archived.

**Chain D — the determinism chain (6 hops).**
`docs/02` specifies deterministic stepping → [CARLA](https://github.com/carla-simulator/carla)
(UE 5.5 branch, hardware floor) →
[determinism issue search](https://github.com/carla-simulator/carla/issues?q=determinism) (#9831
double-tick, #5498 flag conflict, #8899/#4989 physics determinism fixes) →
[MassSample](https://github.com/Megafunk/MassSample) (`mass.FullyParallel`,
`ParallelForEachEntityChunk`, deferred command ordering, `MassLOD` viewpoint-dependent ticking,
*"only truly safe to call outside of processing on the main thread"*) →
[unrealcv #275](https://github.com/unrealcv/unrealcv/issues/275) (stale capture after a camera move — a
frame-ordering bug) → [EasySynth](https://github.com/ydrive/EasySynth) (FXAA-only AA; optical flow
assumes static objects) — yielding §8.2's five determinism tests and §2.3.4's tick-tagged readback ring.

**Chain E — the alternatives chain (7 hops).**
`docs/01`'s Isaac option → [IsaacSim](https://github.com/isaac-sim/IsaacSim) (Apache-2.0, GCC 11 only,
RTX 4080 min) → [IsaacLab](https://github.com/isaac-sim/IsaacLab) (humanoids listed; people/pedestrians
*not* documented) → [GRUtopia/InternUtopia](https://github.com/OpenRobotLab/GRUtopia) (Isaac Sim 4.5,
100k scenes, LLM-driven GRResidents, assets CC BY-NC-SA) →
[NVIDIA-Omniverse/IsaacSim docker repo](https://github.com/NVIDIA-Omniverse/IsaacSim) (archived;
images under the Omniverse licence) → [Genesis](https://github.com/Genesis-Embodied-AI/Genesis) (no
human story) → [habitat-sim](https://github.com/facebookresearch/habitat-sim) (10,000 FPS, no bipeds) →
[TDW](https://github.com/threedworld-mit/tdw) (Replicants + *"SMPL-based characters for background
agents"* — independent confirmation of our hero/background tiering; now LTS).

**Chain F — the offline-renderer chain (5 hops).**
[BlenderProc](https://github.com/DLR-RM/BlenderProc) (GPL-3.0; embedded-Python tax) →
[Kubric](https://github.com/google-research/kubric) (Apache-2.0; photorealism *"clearly not feasible"*;
hermetic shards) → [Infinigen](https://github.com/princeton-vl/infinigen) (BSD-3; **no humans**) →
[PhotorealismEnhancement](https://github.com/isl-org/PhotorealismEnhancement) (archived; needs
G-buffers → §4's "export albedo/material now" recommendation) →
[UBnormal](https://github.com/lilygeorgescu/UBnormal) (CC BY-NC-ND; disjoint anomaly types → §8.5.8).

**Chain G — the ops chain (4 hops).**
[Ray](https://github.com/ray-project/ray) (tasks/actors/objects → warm-engine workers) →
[mediamtx](https://github.com/bluenviron/mediamtx) (MIT RTSP re-stream) →
[v2e](https://github.com/SensorsINI/v2e) (*"50-200X slower than real time"* → render high-fps instead) →
[RVO2](https://github.com/snape/RVO2) / [pedsim_ros](https://github.com/srl-freiburg/pedsim_ros) /
[Menge](https://github.com/MengeCrowdSim/Menge) (planner choices and the LGPL caution).

**Dead ends, recorded so nobody repeats them.** Blocked by the egress proxy in this session:
`dev.epicgames.com` (all Epic documentation — SceneCapture, MRQ, Mass, MetaHuman, City Sample, licence),
`forums.unrealengine.com`, `docs.unrealcv.org`, `carla.readthedocs.io`, `arxiv.org`,
`amass.is.tue.mpg.de`-class hosts. 404 on GitHub: `UnrealZoo/unrealzoo-gym/docs/*` (no docs directory at
the paths tried), `UnrealZoo/unrealzoo-gym/blob/main/README.md` as a blob (the repo root rendered fine),
`EpicGames/UnrealEngine` (private, as expected). The `unrealzoo-gym` issue tracker returned **no
results** — an empty tracker, not an unreachable one.

---

## Sources

Fetched and read during this session (every literal quote above comes from one of these):

- [unrealcv/unrealcv](https://github.com/unrealcv/unrealcv) — README (MIT, UE 5.2+, UnrealCV+ note)
- [unrealcv command reference](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/commands.rst)
- [unrealcv known issues](https://raw.githubusercontent.com/unrealcv/unrealcv/master/docs/reference/issues.rst)
- [unrealcv open issues](https://github.com/unrealcv/unrealcv/issues) and individually:
  [#19](https://github.com/unrealcv/unrealcv/issues/19),
  [#109](https://github.com/unrealcv/unrealcv/issues/109),
  [#271](https://github.com/unrealcv/unrealcv/issues/271),
  [#275](https://github.com/unrealcv/unrealcv/issues/275),
  [#282](https://github.com/unrealcv/unrealcv/issues/282),
  [#283](https://github.com/unrealcv/unrealcv/issues/283),
  [#285](https://github.com/unrealcv/unrealcv/issues/285),
  [#287](https://github.com/unrealcv/unrealcv/issues/287),
  [#330](https://github.com/unrealcv/unrealcv/issues/330),
  [#331](https://github.com/unrealcv/unrealcv/issues/331),
  [#339](https://github.com/unrealcv/unrealcv/issues/339)
- [UnrealZoo/unrealzoo-gym](https://github.com/UnrealZoo/unrealzoo-gym) — UE 5.7, 100+ scenes, 53.46 FPS at 2K (README only), ~70 GB, Apache-2.0
- [PerceivingSystems/bedlam_render](https://github.com/PerceivingSystems/bedlam_render) and [pixelite1201/BEDLAM](https://github.com/pixelite1201/BEDLAM)
- [ydrive/EasySynth](https://github.com/ydrive/EasySynth) — MIT UE 5.5–5.7 synthetic-data plugin, documented limitations
- [Megafunk/MassSample](https://github.com/Megafunk/MassSample) — the Mass Entity/MassAI reference documentation
- [microsoft/AirSim](https://github.com/microsoft/AirSim) and [InfraredCamera.md](https://github.com/microsoft/AirSim/blob/main/docs/InfraredCamera.md)
- [CodexLabsLLC/Colosseum](https://github.com/CodexLabsLLC/Colosseum)
- [adamrehn/ue4-docker](https://github.com/adamrehn/ue4-docker)
- [carla-simulator/carla](https://github.com/carla-simulator/carla) and its [determinism issues](https://github.com/carla-simulator/carla/issues?q=determinism)
- [fubel/synthehicle](https://github.com/fubel/synthehicle)
- [dvl-tum/motsynth-baselines](https://github.com/dvl-tum/motsynth-baselines)
- [Unity-Technologies/PeopleSansPeople](https://github.com/Unity-Technologies/PeopleSansPeople) and [com.unity.perception](https://github.com/Unity-Technologies/com.unity.perception)
- [hou-yz/MultiviewX](https://github.com/hou-yz/MultiviewX), [hou-yz/MVDet](https://github.com/hou-yz/MVDet)
- [DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc), [google-research/kubric](https://github.com/google-research/kubric), [princeton-vl/infinigen](https://github.com/princeton-vl/infinigen)
- [isaac-sim/IsaacSim](https://github.com/isaac-sim/IsaacSim), [isaac-sim/IsaacLab](https://github.com/isaac-sim/IsaacLab), [NVIDIA-Omniverse/IsaacSim (archived docker)](https://github.com/NVIDIA-Omniverse/IsaacSim), [NVIDIA-Omniverse/synthetic-data-examples](https://github.com/NVIDIA-Omniverse/synthetic-data-examples)
- [OpenRobotLab/GRUtopia](https://github.com/OpenRobotLab/GRUtopia), [Genesis-Embodied-AI/Genesis](https://github.com/Genesis-Embodied-AI/Genesis)
- [facebookresearch/habitat-sim](https://github.com/facebookresearch/habitat-sim), [allenai/ai2thor](https://github.com/allenai/ai2thor), [threedworld-mit/tdw](https://github.com/threedworld-mit/tdw)
- [facebookresearch/IntPhys2](https://github.com/facebookresearch/IntPhys2)
- [vchoutas/smplx](https://github.com/vchoutas/smplx), [nghorbani/amass](https://github.com/nghorbani/amass)
- [GuyTevet/motion-diffusion-model](https://github.com/GuyTevet/motion-diffusion-model), [OpenMotionLab/MotionGPT](https://github.com/OpenMotionLab/MotionGPT)
- [snape/RVO2](https://github.com/snape/RVO2), [srl-freiburg/pedsim_ros](https://github.com/srl-freiburg/pedsim_ros), [MengeCrowdSim/Menge](https://github.com/MengeCrowdSim/Menge)
- [lilygeorgescu/UBnormal](https://github.com/lilygeorgescu/UBnormal), [isl-org/PhotorealismEnhancement](https://github.com/isl-org/PhotorealismEnhancement)
- [SensorsINI/v2e](https://github.com/SensorsINI/v2e), [bluenviron/mediamtx](https://github.com/bluenviron/mediamtx), [ray-project/ray](https://github.com/ray-project/ray)

**Unreachable in this session and therefore owed a verification pass** (all `[VERIFY]` markers above
point here): Epic official documentation on `dev.epicgames.com` (Scene Capture, Movie Render Queue /
Movie Render Graph, command-line arguments, fixed frame rate, Chaos solver settings, Mass Entity,
StateTree, Smart Objects, ZoneGraph, City Sample, Rule Processor, Motion Matching / PoseSearch, IK
Retargeter, MetaHuman, Remote Control API, Python Editor Scripting, and the MetaHuman/Fab/Megascans
licence pages); `forums.unrealengine.com`; `docs.unrealcv.org`; `carla.readthedocs.io`; `arxiv.org`;
Omniverse/Isaac Sim documentation for `omni.anim.people`; AWS/Azure/RunPod pricing pages.
