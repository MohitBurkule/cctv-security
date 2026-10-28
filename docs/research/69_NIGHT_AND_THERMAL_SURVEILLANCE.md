# 69 · Night and thermal surveillance — imaging physics, datasets, failure modes, deployment

*2026-09-27. Closes the second-weakest answer in 68 (Q6, night/IR) and sets up H32
(66). Tags: **[V]** checked against a primary source or measured here today,
**[A]** stated from a source or standard practice but not re-checked in this
pass, **[X]** tried and found false. ~3.3k words.*

**Bottom line.** "Night" means three different sensors that fail in different
ways: (1) a colour camera running at high gain under streetlight, (2) the same
camera switched to monochrome under its own 850/940 nm infrared illuminator
(active NIR), and (3) a thermal (LWIR, 8–14 µm) camera that sees emitted heat
and needs no light. SurvSim's `cctv_night_ir` models (2). The only
licence-usable real reference we could get today (LLVIP, non-commercial
research) is (1) + (3). That mismatch is the main result of the H32 set-up

---

## 1. How a CCTV camera actually sees at night

### 1.1 Day/night switching and the IR-cut filter (ICR)
* Silicon sensors respond out to ~1,000 nm. In daylight a mechanical **IR-cut
  filter** (IR-cut filter removable, "ICR") sits in front of the sensor so
  near-infrared doesn't wash out colour. At dusk a light sensor or the
  image-luminance threshold swings the filter out. The camera then drops to
  **monochrome**, because the Bayer colour filters all pass NIR roughly
  equally, and it turns on its IR LEDs. [A — standard vendor practice. See
  Axis's "day and night functionality" white paper,
  https://www.axis.com/learning/web-articles/day-and-night-functionality]
* **ICR failure modes that show up in footage** [A]:
  - *Hunting.* Near the switch threshold, the camera's own IR lights up
    nearby reflective surfaces. That pushes scene luminance back over the
    day threshold, so the filter clicks in and out every few seconds.
    Vendors add hysteresis and a delay (typically 5–30 s).
  - *Stuck filter.* The filter jams in "day" at night, giving a black,
    noisy colour image, or in "night" by day, giving pink/magenta-cast
    washed-out colour. This is a common field fault on cheap domes.
  - *Headlight flips.* A car's headlights push the camera back into day mode
    for a few seconds, and detections drop out when the mode switches.
  For analytics, a mode switch is a **distribution shift inside one clip**.
  A tracker's appearance model trained on colour sees a different sensor
  after the switch.

### 1.2 IR illuminators: 850 nm vs 940 nm
* **850 nm** LEDs glow faint red, which people can see. Silicon quantum
  efficiency is roughly 2× higher there than at 940 nm, so the range is
  longer. Vendor datasheets typically claim 30–50 m for domes and 100–200 m
  for bullets with array IR. [A — vendor datasheets. Treat claimed IR range
  as "the distance at which something is visible", not "detectable by an
  analytic".]
* **940 nm** is covert (no visible glow), but it gets roughly 30–50 % less
  range for the same LED power. [A]
* **Illumination falls off with the inverse square law** (IR light reflected
  back is ~1/r², on top of target albedo). That produces the classic IR
  scene: a **hot spot** in the foreground, faces and hi-vis clothing
  saturated near the camera, and a black background beyond the IR range.
  Modern "smart IR" dims the LEDs when the scene is close, to stop faces
  blowing out. [A]
* **NIR reflectance is not visible reflectance.** Cotton and most dyed
  fabrics look bright in NIR whatever their colour. Some black synthetics
  look white, and vegetation is bright (the chlorophyll "red edge"). So
  **clothing colour, the strongest ReID cue by day, carries almost no
  information under active IR.** [A — well-known remote-sensing property. See
  the USGS spectral library, https://www.usgs.gov/labs/spectroscopy-lab]

### 1.3 Gain, noise and the ISP
* In low light, auto-exposure first lengthens the shutter up to a cap
  (usually 1/25–1/30 s at 25/30 fps, sometimes "slow shutter" 1/6 s), then
  raises analogue and digital gain. At high gain, shot noise and read noise
  dominate. The camera's **3D (temporal) noise reduction** then smooths them,
  which creates **motion smear / ghost trails** behind moving people, because
  temporal NR blends frames where there's motion. [A]
* Consequences for detection. A walking person gets a blurred, low-contrast
  trailing edge. Small far people are **denoised out**: the NR treats a 10-px
  person as noise. And the H.264/H.265 encoder spends few bits on a dark
  frame, so it quantises the shadows to flat blocks.
* **SurvSim cross-check [V, measured today]:** `cctv_night_ir` has
  `denoise=9.0` and produces Immerkaer `noise_sigma` 0.001. That's ~60–150× below the 10th percentile of
  *either* real night band (LLVIP visible 0.147–0.309,
  LLVIP thermal 0.061–0.232; §7). So our night profile over-denoises. Real
  night frames stay visibly noisy after the ISP.

### 1.4 Artefacts that trigger false alarms at night
* **Insects and spiders near the IR LEDs.** The LEDs are next to the lens, so
  a moth 20 cm away is lit brightly and out of focus: a huge moving blob. A
  web in front of the lens is the most common cause of night false alarms in
  video-motion detection. [A — widely reported by installers; there is no
  good peer-reviewed rate]
* **Rain and snow bloom.** Drops close to the lens light up as streaks or
  discs. Fog backscatters the IR, which cuts range and lifts the black level.
  [A]
* **IR reflection from the dome bubble or housing.** A dirty or scratched
  dome scatters the camera's own IR back into the lens as a haze. This is why
  bullet cameras with external illuminators are preferred for perimeter
  runs. [A]
* **Headlights, security lights and PIR-triggered floodlights** cause sudden
  global luminance steps that background models read as motion. [A]

---

## 2. Thermal (LWIR) imaging

### 2.1 Sensor
* Security thermal cameras are almost all **uncooled microbolometers**
  (vanadium oxide, VOx, or amorphous silicon) sensing 8–14 µm long-wave IR.
  They see emitted heat, so they need **no illumination and are not blinded
  by headlights**. [A]
* Typical resolutions are **384×288 and 640×512**; 1280×1024 is premium. The
  pixel pitch has fallen from 17 µm to 12 µm, and 10 µm/8 µm is emerging.
  [A — e.g. Teledyne FLIR Boson/Boson+ datasheets,
  https://www.flir.com/products/boson/]
* **NETD** (noise-equivalent temperature difference) is typically < 50 mK for
  commodity cores and ≤ 20–30 mK for premium ones (Boson+ claims ≤ 20 mK).
  [A]
* **Export control.** Cores faster than 9 Hz fall under US export control
  (EAR 6A003), so "9 Hz" models exist for export. That matters for tracking.
  [A]
* **Cost.** A 640×512 security bullet is roughly £3–10k. A 384×288 one is
  roughly £1–3k. Long-range pan-tilt thermal is £20k and up. A decent visible
  IR bullet is roughly £150–600. [A — order-of-magnitude market prices]

### 2.2 Thermal artefacts
* **Halo.** Hot targets against a cool background (and the reverse) get a
  dark or bright ring. The camera's local contrast enhancement causes it, and
  it inflates box extents. [A]
* **AGC swings.** Automatic gain control maps the scene's temperature range
  to 8 bits. When a hot vehicle enters, every person in the frame goes darker
  *in the same frame*. A detector trained on fixed-contrast thermal loses
  them. [A]
* **Thermal crossover.** Around dawn and dusk, or on hot days, when the
  background reaches ~30–35 °C, people lose their contrast with the ground.
  Thermal's "always sees people" claim fails at exactly the hours when
  attackers expect less attention. [A]
* **NUC freeze.** The periodic non-uniformity correction closes a shutter
  flag for ~0.2–0.5 s, and the frame freezes. Trackers see a dropped frame.
  [A]
* **Glass is opaque in LWIR.** Thermal cannot see through windows or vehicle
  windscreens, and wet surfaces and glass show reflections of heat
  ("ghosts"). [A]
* **No identity.** Faces and clothing text are unreadable, so thermal
  supports **detection and classification**, not recognition. [A]

---

## 3. Real datasets and what they allow (licence verdicts → 47 §2)

| Dataset | What it is | Size | Licence (ML/commercial clause) | Verdict for SurvSim |
|---|---|---|---|---|
| **LLVIP** — https://bupt-ai-cz.github.io/LLVIP/, arXiv 2108.10831 | 15,488 aligned visible/thermal pairs, "most … very dark scenes", fixed surveillance view, 1280×1024 registered; thermal 8–14 µm | 30,976 images, ~3.5 GB zip [A] | "freely available … for **non-commercial purposes** such as academic research, teaching … personal experimentation" (homepage, **[V]** 2026-09-27) | **Usable for internal H32 reference stats only.** Not for training a sold model. 50 frames downloaded (§7). |
| **KAIST multispectral** — https://github.com/SoonminHwang/rgbt-ped-detection | 95k colour/thermal pairs, 640×480, 20 Hz, vehicle-mounted, day + night; 103,128 boxes, 1,182 pedestrians | 36.32 GB full, 1.44 GB preview | **CC BY-NC-SA 4.0** (repo, **[V]**) | Non-commercial evaluation only. Skipped: even the 1.44 GB preview is > 200 MB, and it's a vehicle viewpoint, not CCTV. |
| **FLIR ADAS v2** — https://www.flir.com/oem/adas/adas-dataset-form/ | ~26k annotated thermal + RGB frames, 640×512, 15 classes, driving [A] | several GB [A] | Gated behind a form. The form URL returned **404 on 2026-09-27**, so the terms could not be verified; historically "free for research" [A] | **Unverified → treat as blocked.** Also a vehicle viewpoint. |
| **M3FD** (TarDAL, CVPR 2022) — https://github.com/JinyuanLiu-CV/TarDAL | 4,200 IR/visible pairs, 1024×768, 6 classes incl. People, 34,407 labels | Google Drive/Baidu | The repo is GPL-3.0 (code). **No explicit dataset licence** (**[V]** repo read) | **Unclear → blocked** until the authors confirm. |

Common thread: **no licence-clear (commercial-ML-OK) real night/thermal
person dataset was found.** Every usable one is non-commercial research. That
is exactly the gap a CC0 synthetic night/thermal set could fill. It is also
why night realism has to be validated against NC data used **only for
measurement, never training** (the same regime as MOT20 in 47).

---

## 4. Person detection on thermal and low-light: state of the art

* **LLVIP's own baseline** (arXiv 2108.10831 §4, **[V]**):
  pedestrian AP50 **YOLOv5 0.908 on visible vs 0.965 on infrared**, YOLOv3
  0.871 vs 0.940; the stricter AP (0.5:0.95) gap is larger, 0.527 vs 0.670
  (YOLOv5). Each detector was **trained per modality on LLVIP's own train
  split** (77.6 / 22.4 %), so this is ~6 AP50 points for thermal on *one*
  dataset's dark fixed views, not a zero-shot or general result. LLVIP pedestrians
  are **medium-sized**, and the authors themselves say it doesn't cover
  long-range small targets.
* **KAIST** reports log-average **miss rate** (MR⁻², lower is better), not
  AP. Fusion detectors went from ~30 % MR (ACF+T+THOG, 2015) to single
  digits on the "sanitised" test annotations (MBNet 2020, ~8 %; later
  ProbEn/CFT/INSANet ~5–7 %). [A — read tables in the papers before quoting
  exact figures] The night subset is consistently *better* than day for
  thermal-only models, because pedestrians are high-contrast against cold
  roads.
* **Fusion families** [A]:
  - *Early fusion*: stack RGB+T as 4 channels. Cheap, but the two images must
    be registered.
  - *Halfway/mid fusion*: two backbones joined at feature level
    (Liu et al. 2016 halfway fusion, Cross-modality Fusion Transformer CFT
    2021).
  - *Late/decision fusion*: run detectors separately and combine the boxes
    (ProbEn, probabilistic ensembling, ECCV 2022). This holds up best when
    one modality drops out, and on a real site one will: the ICR sticks, or
    the thermal is in a NUC freeze.
  - *Image-fusion-then-detect* (TarDAL on M3FD). Pretty fused pictures, but
    it doesn't reliably beat feature fusion on AP.
* **Unaligned pairs are the real-world case.** Security thermal and visible
  cameras are rarely co-boresighted. KAIST needed a beam splitter, and LLVIP
  registers after capture. On a real site fusion has to happen in **world
  coordinates** (the ground plane via calibration), not pixel by pixel. That
  suits SurvSim's calibrated rigs.

---

## 5. What fails at night, per task

| Task | Day failure | Night / IR / thermal failure | Mechanism |
|---|---|---|---|
| Detection | occlusion, small size | **small far people vanish first**; boxes grow (halo, smear) | IR range falloff 1/r²; NR erases low-contrast blobs; thermal AGC; our H11: `cctv_night_ir` −0.609 recall **[V]** (sensor-model sensitivity, not a night penalty; H32) |
| Tracking | ID switches at crossings | **more fragmentation** at the IR range edge (people fade in and out), ICR mode switches, NUC freezes | detections drop in and out → track births/deaths; Kalman gating fails on a frozen frame |
| ReID | clothing change | **colour is gone** (IR mono, thermal); NIR reflectance ≠ visible colour; thermal has no texture | cross-modal ReID (RGB↔IR) is its own benchmark field (SYSU-MM01, RegDB), with R1 far below same-modality [A] |
| Behaviour / loiter | innocent dwellers | fewer innocents at night → **the base rate changes** → a day θ gives wrong FA/cam-h | per-time-band calibration (68 Q13, H33 conformal per band) |
| False alarms | shadows, foliage | **insects, webs, rain bloom, headlight sweeps, IR hot spots** | these dominate night VMD alarms; a person detector suppresses many, but not spiders on the lens |

Take-away for SurvSim: H11 showed rendered *darkness* barely mattered (−0.020
recall), while the *sensor model* cost 0.609. The sensor model is where the
night gap lives. Today's stats (§7) show that the sensor model is itself
uncalibrated against any real night reference.

---

## 6. What a defence-site / CNI perimeter actually deploys

* **Layered, fused detection, not cameras alone** [A — pattern across the UK
  NPSA (ex-CPNI) guidance, https://www.npsa.gov.uk/, and vendor system
  designs]:
  1. **PIDS** (perimeter intrusion detection systems) on the fence:
     fence-mounted fibre or taut-wire vibration sensing, buried
     seismic/pressure cable, microwave or IR beam barriers in sterile zones.
     These say *where along the fence* something happened, not *what*.
     NPSA tests and lists PIDS against CAPSS.
  2. **Ground-surveillance radar** covers open areas. It gives range,
     bearing and speed in all weather, day or night, with detection of a
     walking person to hundreds of metres to ~1–2 km (short-range
     security radars). It cues the cameras. [A]
  3. **Thermal cameras for detection** along the fence line and approach.
     They are usually specified by the **DRI (detection/recognition/
     identification)** Johnson-criteria ranges on the datasheet. [A]
  4. **Visible/IR PTZ for assessment and recognition**, slewed to the radar
     or PIDS cue: "slew-to-cue". The operator confirms with a
     colour/IR image. [A]
  5. **Lighting** is often deliberately *off* or low in sterile zones
     (thermal needs none, and lights help an attacker), so the visible
     cameras rely on IR.
* **Pixel-density standard.** EN 62676-4 / IEC 62676-4 sets operational
  levels by pixels per metre at the target: detect ≈ 25 px/m, observe
  ≈ 62, recognise ≈ 125, identify ≈ 250. [A] At night with IR, the
  *effective* range at those densities is set by the illuminator, not the
  lens.
* **Why this matters for the job.** An ML alarm on a CNI perimeter is scored
  **after fusion**. A thermal detection that agrees with a PIDS zone and a
  radar track is a very different alarm from a visible-only detection. That
  maps directly onto SurvSim's multi-sensor fusion design (RF and audio
  sensors exist, radar/PIDS do not). It also maps onto the operator budget
  (FA/cam-h): fusion is how sites aim for single-digit false alarms per night [A — no
  measured source].

---

## 7. H32 set-up: the real night reference, measured today

**Reference set [V].** We used 25 aligned LLVIP thermal frames and their 25
visible (low-light) partners, 1280×1024, from the sample images LLVIP
publishes in its GitHub repo (`FusionGAN/{Train,Test}_LLVIP_{ir,vi}`). That's
4.3 MB in total, stored in `~/data/real_cctv_night/llvip_{ir,vis}`.
Licence: LLVIP non-commercial research (§3). We use them for measurement
only.

**Synthetic.** `out/batch_v8/street_crowd_night/render/cam_02` (CC0
characters, `licences.json` has `commercial_ml_ok: true`), raw and through
`cctv_night_ir` / `cctv_day_720p`. Tool:
`python -m survsim.realism compare --n 30`.

| reference | raw render | + `cctv_night_ir` | + `cctv_day_720p` |
|---|---|---|---|
| LLVIP thermal (8–14 µm) | 5/14 | **3/14** | 6/14 |
| LLVIP visible low-light | 7/14 | **4/14** | 6/14 |

The counts include `temporal_noise`, which scores "ok" against a NaN band:
the samples aren't consecutive video. On the 13 real stats the night profile
is **2/13 and 3/13**. Findings:
1. **The "night" render isn't dark.** Raw luma is 89.7, against LLVIP visible
   at 26–59 (median 33.6). batch_v8 night renders sit in the *day* luminance
   band, so H11's "darkness barely matters" was measured on scenes that
   weren't dark enough. This is new, and it qualifies 68 Q6.
2. **`cctv_night_ir` over-corrects in the other direction.** Luma is 15.6
   (below both bands), dynamic range 64 (vs 86–222), entropy 4.8 (vs
   5.5–7.1), noise 0.001 (vs 0.06–0.31), because `denoise=9.0` wipes the
   noise out. And `mtf_ratio` 0.51 sits far above both bands (0.006–0.185).
3. **The modality mismatch is structural.** `cctv_night_ir` models active
   NIR. LLVIP's IR is thermal and its visible channel is colour low-light, so
   *neither* is the right target for this profile. Thermal is also blurrier
   (lap_var 1.1–1.7 vs our 2.3) and has zero chroma by construction. H32
   needs either an active-NIR CCTV reference (none licence-clear found) or a
   new `cctv_thermal` profile validated on LLVIP IR.
4. The LLVIP samples are JPEG re-saves (blockiness 1.46–1.67), so blockiness
   says more about how they were distributed than about the sensor. Exclude it.

**H32a/b have now run (32, docs/15): hold-out 2/13 vis, 3/13 IR — not met.** Original next step: Split it into H32a, retune a *visible
low-light* profile against LLVIP-vis (target ≥ 9/13), and H32b, add a thermal
profile against LLVIP-IR. Reaching the 200-frame bar needs the full LLVIP
zip (~3.5 GB > 200 MB), which is outside this step's budget. Recall
comparisons also need a GPU.

---


1. **"How does a CCTV camera see at night?"** — It swings its IR-cut filter
   out, goes monochrome and lights the scene with 850 or 940 nm LEDs. Range
   is set by the illuminator and falls off with the square of distance, so
   you get a hot foreground and a black background. Thermal is a different
   sensor: it sees heat, needs no light, and is 640×512 at best at sensible
   cost.
2. **"Thermal or visible for a perimeter?"** — Thermal to *detect*, because
   it's unaffected by lighting or headlights and gives high person contrast
   (LLVIP, YOLOv5 trained per modality: 0.965 vs 0.908 AP50 — one dataset,
   medium-range pedestrians). Visible/IR PTZ to *assess and recognise*,
   slewed to the cue. Fuse them in world coordinates with radar and PIDS.
3. **"What breaks at night?"** — Far people vanish (IR range, noise
   reduction). Tracks fragment at the edge of the IR range and when the ICR
   switches. Colour-based ReID dies. Night false alarms come from insects,
   webs, rain bloom and headlight sweeps.
4. **"What did your simulator show?"** — Darkness in the render cost almost
   nothing (−0.020 recall), but the sensor model cost 0.609. Today's real
   reference then showed two things: our "night" renders weren't dark
   (luma 90 vs a real median 34), and the IR profile over-denoises (noise
   0.001 vs real medians 0.15 thermal / 0.22 visible). So my night numbers
   measure a sensor model, not night — possibly an artefact of it. H32 then
   fitted a visible low-light and a thermal profile. They reach 9/13 and 10/13
   on the tune frames but only 2/13 and 3/13 on the held-out LLVIP frames.
   Across the three sensor models, YOLOv8n recall falls by 0.47 (thermal),
   0.57 (NIR) and 0.84 (low-light) from 0.94 raw. That spread *is* the
   answer: the penalty depends on an unvalidated sensor model. I'd say that
   before claiming anything.
5. **"How do you get real night data legally?"** — LLVIP, KAIST and FLIR ADAS
   are all non-commercial or unverified. Use them only to *measure* realism
   and evaluate, never to train a sold model. That's the same regime I use
   for MOT20. A CC0 synthetic night set is the commercially clean training
   source.
6. **"RGB-thermal fusion — which kind?"** — Late/probabilistic fusion
   (ProbEn) for deployment, because it survives one modality dropping out.
   Mid-level fusion gives the best benchmark numbers but needs registered
   pairs, which site cameras rarely give you.
7. **"Thermal crossover?"** — When the background approaches body
   temperature (around dusk and dawn, or hot days), people lose contrast.
   Fused visible or radar covers those hours, and detection metrics should
   be reported per time band.
8. **"How would you set night thresholds?"** — Calibrate each camera for
   each time band. The night base rate of innocents differs, so a day θ
   gives the wrong FA/cam-h. Conformal θ per band is the method I'd use — H33
   held the budget in 10/10 splits, but on simulated worlds and not per band;
   per-band calibration is untested.
9. **"Cross-modal ReID?"** — Visible↔IR ReID is a separate, much harder
   benchmark (SYSU-MM01, RegDB). At night I'd lean on spatio-temporal
   camera-network constraints and gait/shape, not appearance.
10. **"Top night false-alarm source and fix?"** — A spider or insect at the
    IR LEDs. Put a person classifier behind motion detection, add a
    minimum-track-length and ground-plane-size gate (a moth on the lens has
    no plausible world size), and fit external illuminators so the LEDs
    aren't next to the lens.
