# R04 · Perception Under Degraded Conditions, the CCTV Imaging Chain, and Synthetic Data / Sim-to-Real for Surveillance Analytics

> **Audience.** An intern who must hold their own in a room with people who have spent
> twenty years staring at bad video. This document is deliberately long and deliberately
> specific. Read §1 before you touch the sensor model in
> [`docs/06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md); read §5 before
> you argue with anyone about whether synthetic data "works".
>
> **Framing.** the vendor's vendor lab brief is to *"enhance perimeter and area
> monitoring, particularly under challenging environmental or visual conditions, such as
> poor lighting, adverse weather, or degraded image quality"*. That sentence is a
> perception-under-degradation problem statement, and the whole reason our simulator exists
> is that **the degraded tail of the distribution is exactly the part of the data that
> real-world customers cannot give us, cannot label, and cannot reproduce on demand.**

### Sourcing and honesty note (read this first)

This dossier was compiled behind an egress proxy that blocked direct document retrieval
from `arxiv.org`, `axis.com`, `openaccess.thecvf.com`, `openreview.net`, `pmc.ncbi.nlm.nih.gov`
and most publisher domains; `github.com` and web search were reachable. Therefore:

* Text in **"double quotes"** is verbatim from the linked source as retrieved (repository
  READMEs, search-indexed abstracts, vendor datasheet summaries).
* Text marked **[paraphrase]** is an accurate summary of a real, linked source whose exact
  wording I could not re-verify through the proxy. Do not present it as a quotation.
* Text marked **[lore]** is craft knowledge from practice, not from a citable paper. It is
  often the most useful part. Label it as such when you repeat it — veterans respect
  "that's field lore, not a result" far more than a fake citation.
* Numbers in §1 physics are first-principles derivations (radiometry, noise, diffraction)
  and are marked **[derived]**. Check them yourself; that is the point.

---

## 1. The CCTV imaging chain, with physics

The single most common failure mode in junior video-analytics engineers is treating the
image as the beginning of the pipeline. It is not. It is the **output of a long lossy
analogue-then-digital chain**, and almost every "AI problem" in surveillance is an imaging
problem wearing a trench coat. Walk the chain in order: photons → lens → filter → sensor
well → ADC → ISP → encoder → network → VMS → decoder → your tensor.

### 1.1 Scene radiometry: how little light you actually have

Illuminance benchmarks you should have memorised (standard photometric values, **[derived/reference]**):

| Condition | Illuminance (lux) |
|---|---|
| Direct sunlight | 100 000 – 120 000 |
| Overcast day | 1 000 – 10 000 |
| Deep shade / very dark overcast | ~100 |
| Civil twilight | ~10 |
| Well-lit shop street / car park under sodium | 10 – 30 |
| Typical "lit" perimeter road | 5 – 15 |
| Corridor emergency lighting | 1 – 5 |
| Full moon, clear | 0.1 – 0.25 |
| Quarter moon | ~0.01 |
| Clear starlight, no moon | 0.001 – 0.002 |
| Overcast starlight | ~0.0001 |

The dynamic range of the *scene* across a single frame at a lit gate at night — headlight
filament to unlit hedge — routinely spans 5–6 decades, i.e. 100–120 dB. That is the
central fact that makes WDR necessary and makes WDR lie to you (§1.6).

Vendors quote **minimum illumination** in lux, and the number is nearly meaningless without
its footnotes. [ScienceDirect's overview of minimum illumination](https://www.sciencedirect.com/topics/computer-science/minimum-illumination)
collects the standard caveats; in practice a "0.05 lux colour" spec is achieved at 1/8 s
integration, maximum gain, with a 30 IRE output criterion and an F1.2 lens. **Change any
one of those and the number moves by an order of magnitude.** [lore] The first question to
ask a vendor is *"at what shutter speed and what F-number, and to what output level?"* If
they cannot answer in one sentence, the spec is marketing.

### 1.2 Sensor size, pixel pitch, and the photon budget

Surveillance sensors are almost all 1/3", 1/2.8", 1/1.8" or 1/1.2" CMOS. The relevant
quantity is not resolution, it is **photons per pixel per frame**, which scales with pixel
area × exposure time × lens aperture area × QE.

* A 1/2.8" sensor at 1920×1080 has ~2.9 µm pixel pitch; the same format at 3840×2160 has
  ~1.45 µm, i.e. **4× less area per pixel**. [derived] Going 4K on the same optic and the
  same night scene costs you ~2 stops of per-pixel SNR. This is the single most important
  trade in perimeter camera specification and it is almost always got wrong by
  procurement, who buy megapixels.
* Dedicated low-light sensors go the other way. Teledyne's low-light/surveillance line
  states that "low light image sensors with backside illuminated (BSI) processing can
  enable less than 0.001 Lux (overcast starlight) imaging capability", and that
  "exceptionally low read noise with high quantum efficiency BSI processing enables
  starlight (<1mLux) imaging capability at 60FPS"
  ([Fairchild/Teledyne low-light imaging](https://fairchildimaging.com/low-light-imaging)).
* The way they get there is big pixels: night-vision sensors have "a pixel area 3-10 times
  larger than general purpose sensors of similar megapixel capability, with a pixel pitch
  between 5 and 20 μm"
  ([US 10,225,498, pMOS/nMOS night-vision pixel](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10225498)).
* **Quantum efficiency** is, per Teledyne's sensitivity tutorial, "the probability that a
  photon generates an electron in a sensor at a given wavelength"
  ([How to Evaluate Camera Sensitivity](https://www.teledynevisionsolutions.com/learn/learning-center/machine-vision/how-to-evaluate-camera-sensitivity/)).
  Silicon peaks ~500–600 nm at 60–90 % for BSI, and falls to roughly 10–30 % at 850 nm and
  often under 10 % at 940 nm — which is the whole story of §1.5.

### 1.3 Noise: shot, read, dark, fixed-pattern

Four noise sources, three of which the ISP will try to hide from you:

1. **Photon shot noise** — Poisson, σ = √N electrons. Irreducible. At 100 photoelectrons
   you have 10 % noise; at 10 000 you have 1 %. [derived] *Every* night-video artefact
   people blame on "the codec" starts here.
2. **Read noise** — additive, per-pixel-read, in e⁻ rms. Modern scientific sensors reach
   "0.5e- rms Read Noise" and even "an average read noise of 0.35 e- rms at room
   temperature operation, enabling industry leading low-light imaging performance"
   ([IISW 2023, R75](https://imagesensors.org/Past%20Workshops/2023%20Workshop/2023%20Papers/R75.pdf)).
   Commodity CCTV sensors sit at 1–3 e⁻.
3. **Dark current shot noise** — doubles roughly every 6–8 °C. A camera in a sealed dome in
   full sun at 55 °C internal is a materially noisier camera at 23:00 than the same model in
   a shaded housing. Night-vision sensitivity is explicitly "limited in sensitivity by the
   shot noise on the detector's dark current and the pixel read noise, which is dominated by
   both thermal and 1/f noise of the pixel source follower"
   ([USPTO 10,225,498](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10225498)).
4. **Fixed-pattern noise / DSNU / PRNU** — column and pixel offsets, plus hot pixels. These
   are *spatially correlated and temporally static*, which means temporal denoisers do not
   remove them and CNNs happily learn them as features. [lore] This is why a detector
   fine-tuned on one camera can degrade on an identical model of camera next to it.

**Modelling consequence for us.** A physically defensible degrade stage is
`electrons = QE · photons(EV) · t`, then `Poisson(electrons) + N(0, σ_read) + FPN_map`,
then gain, then quantise. Adding Gaussian noise to an sRGB frame is *wrong* in a way that
matters: real noise is signal-dependent and lives in linear space before gamma. The
canonical treatment is Brooks et al., "Unprocessing Images for Learned Raw Denoising" —
their pipeline exposes exactly the inversion knobs you need,
"`random_ccm()` - color correction matrix", "`random_gains()` - sensor gains",
"`random_noise_levels()` - noise characteristics"
([unprocessing repo](https://github.com/timothybrooks/unprocessing)). **Invert the ISP,
inject noise in linear/Bayer space, re-apply the ISP.** That is the difference between a
noise model a veteran believes and one they laugh at.

### 1.4 Gain, AGC, exposure and the shutter/noise/blur trilemma

Once photons run out the camera has three levers and all three cost you:

* **Longer exposure** → motion blur. A person walking at 1.4 m/s at 10 m with a 1/2.8"
  sensor and 4 mm lens covers ~4–6 px in 1/25 s. [derived] At 1/8 s (a very common
  night auto-exposure floor) that is 12–20 px of smear — comparable to the width of the
  target's limbs. Gait, and often the person/bag distinction, is destroyed.
* **Wider aperture** → shallower depth of field and worse MTF at the edges (§1.7).
* **More gain** → amplifies shot and read noise together; the ISP then denoises, which
  *removes the target's texture along with the noise* (§1.8).

**AGC dynamics are a first-class simulation citizen.** Real AGC/AE loops have 300–800 ms
time constants and hysteresis; a torch swept across the lens, a car turning in, or a white
van parking causes a multi-second exposure excursion during which the rest of the frame is
crushed to black. Tracks break there, not in the steady state. [lore] Ask any operator
about "the van at gate 3" and you will get this story. Our pipeline already models
"auto-exposure lag (1st-order, 300-800 ms)" — keep it, and make sure the evaluation harness
reports metrics *conditioned on AE transient* as well as in aggregate.

### 1.5 IR-cut filter, near-IR illumination, 850 vs 940 nm

A "day/night" camera has a mechanically switched **IR-cut filter**. By day it is in place so
colour rendition is correct; below a lux threshold it swings out, the sensor's NIR response
is admitted, and the camera outputs monochrome. Axis's long-running white paper on the
topic is the standard reference
([IR in surveillance: Day-and-night cameras and OptimizedIR](https://www.axis.com/dam/public/a0/56/91/ir-in-surveillance-en-US-398429.pdf);
[whitepapers.axis.com landing page](https://whitepapers.axis.com/en-us/ir-in-surveillance)).
Key points as summarised from that document and the vendor literature:

* "Both camera-integrated and standalone illumination normally use IR light with a
  wavelength of 850 nm", with "850 nm for semi-covert surveillance and 940 nm to completely
  avoid red glowing LEDs" [paraphrase of the Axis white paper].
* "The camera can reach farther when using an 850 nm LED illuminator than with a 940nm LED
  illuminator. The disadvantage of using 850 nm LEDs is that they show up as a visible red
  dot, while 940nm LEDs provide completely covert illumination"
  ([Axton, 850 vs 940 nm](https://axtontech.com/infrared-850nm-vs-940nm-wavelength/)).
  Rule of thumb in the trade: **940 nm costs you roughly 30–50 % of range** for the same
  radiant power, because both LED efficiency and silicon QE are lower there. [lore/derived]
* **OptimizedIR** "automatically adjusts the intensity and angle of the illumination to
  match the camera's field of view. This prevents hotspots, where objects close to the
  camera appear overexposed, and ensures the entire scene is evenly lit"
  [paraphrase of [Axis OptimizedIR](https://www.axis.com/solutions/optimizedir)].
  The failure it fixes is the classic one: zoom in, illumination stays wide, the near
  bollard blooms white and the person at 25 m is invisible.
* Lumileds' emitter white paper is the component-side companion
  ([LUXEON IR emitters for surveillance cameras](https://lumileds.com/wp-content/uploads/files/WP37-luxeon-ir-emitters-for-surveillance-cameras-white-paper.pdf)).

**Physics of IR range.** Active illumination obeys inverse-square on the way out *and*
inverse-square on the way back from a Lambertian target, so returned irradiance at the
sensor falls as **1/d⁴** for a small target, 1/d² for a surface filling the field. [derived]
Practical consequences you must bake into the simulator:

* A "50 m IR" bullet camera delivers usable person contrast to maybe 25–35 m and *face*
  detail to 8–12 m. Doubling the stated range needs ~16× the optical power for a
  point-like target.
* **Retro-reflective materials break everything.** Hi-vis tape, number plates, road signs
  and some trainer logos return 100–1000× a diffuse surface and saturate the sensor,
  producing a white blob where a torso should be. Every analytic that keys on silhouette or
  clothing colour degrades at night on a worker in hi-vis. Our sensor model's
  "retro-reflective hi-vis blooming" stage exists for this reason — it is not a gimmick.
* **Hot near-field objects**: spider webs, insects and falling rain/snow within 1–3 m of the
  lens are lit far more strongly than the scene and become the dominant motion signal.
  Roughly half of all night false alarms on unattended perimeter cameras are spiders and
  moths. [lore] If your simulator cannot generate this, your false-alarm numbers are
  fiction.
* **Focus shift**: 850 nm focuses at a different distance from visible light. Cheap fixed-lens
  cameras are focused in daylight and are therefore *soft at night*; IR-corrected lenses
  exist and cost more. [paraphrase of the Axis white paper.]

### 1.6 WDR / HDR: what it buys and what it fabricates

* True WDR merges multiple exposures: "Sensors take 2 to 4 exposures per frame and merge
  on-chip", and "WDR - dynamic capture uses a dual-exposure method for merging images with
  different exposure times, though the dynamic range is limited by artifacts related to
  motion and flickering" [paraphrase of
  [Axis, Wide dynamic range: WDR solutions for forensic value](https://www.axis.com/dam/public/ba/52/11/wide-dynamic-range-en-US-379535.pdf)].
* "Forensic WDR is a combination of dual exposure and a local contrast enhancement method
  that provides images tuned for maximal forensic usability" and is "suitable in scenes with
  motion and in ultra high resolution cameras"
  [paraphrase of [Axis Forensic WDR](https://www.axis.com/solutions/forensic-wdr)].
* Axis explicitly warns against dB-number shopping: "Axis WDR solutions prioritize motion
  and appearance aspects over reach, meaning that Axis cameras may deliver better dynamic
  range imaging than their dB values imply, and a camera with a lower dB value could
  outperform one with higher dB value from another company" [paraphrase].
  The commonly quoted threshold is that "the generally accepted dB level for a camera to be
  considered True WDR is 120dB" ([Tec-Tel glossary](https://tec-tel.com/glossary/wdr)).

**What this does to analytics.** Multi-exposure WDR creates **ghosting and comb artefacts on
moving people**, because the long and short exposures disagree about where the person was.
Local tone mapping then makes *global* appearance non-stationary: the same jacket has a
different RGB triple depending on what else is in the frame. [lore] This is a first-order
cause of cross-camera re-ID failure and of colour-based attribute search ("man in red
jacket") returning brown, orange and maroon. If our simulator applies a *fixed* tone curve
per camera, we are making re-ID easier than reality; the WDR stage must be **content
dependent**.

### 1.7 Lens: F-number, MTF, diffraction, depth of field, distortion

* **Light gathering** scales as 1/F². F1.4 → F2.0 is one stop; a "3.6 mm F2.0" bullet camera
  has half the photon budget of an F1.4 unit. [derived]
* **Diffraction limit**: the Airy disc diameter is ≈ 2.44·λ·F. At λ = 550 nm and F8 that is
  ~10.7 µm — larger than four 2.9 µm pixels. [derived] So a 4K 1/2.8" camera stopped down in
  daylight is **optically incapable** of resolving its own pixel grid. Resolution claims and
  resolvable detail are different quantities.
* **MTF** is the honest metric: contrast transfer vs spatial frequency (lp/mm), usually
  quoted at MTF50. A cheap varifocal at full wide and full tele can lose 40–60 % of centre
  MTF at the corners, which is exactly where the perimeter fence line usually sits. [lore]
  Corner softness is why detection recall is frequently *worse at the edge of frame* by
  several AP points, independent of scale.
* **Depth of field** shrinks with focal length and aperture; a 12–40 mm tele at F1.6 focused
  at 30 m may have only a few metres of usable DoF, so a person walking toward the camera
  goes soft. PTZ autofocus hunting then produces multi-second full-frame defocus events that
  look exactly like tamper.
* **Distortion models** you must support: **Brown–Conrady** (radial k1,k2,k3 + tangential
  p1,p2) for normal lenses, and **Kannala–Brandt** (equidistant fisheye, θ-polynomial) for
  fisheye — the latter is what `cv::fisheye` implements. For >180° and panomorph optics
  neither fits well and you need a lookup/ray table. [reference]
* **Fisheye / 360 dewarping**: a 12 MP 360° ceiling camera dewarped into four "virtual PTZ"
  views has *wildly* non-uniform effective resolution — centre-of-room pixel density can be
  3–5× that at the wall. Person height in pixels is a function of radius, and standard
  anchor-based detectors trained on rectilinear data lose heavily on raw fisheye because
  people are rotated to point at the image centre. [lore, well known in the trade]
  Practical mitigations: rotation-aware anchors, radial-aware NMS, or detect on the dewarped
  tiles and fuse in world coordinates. Our simulator should render **both** the raw fisheye
  and the dewarps, with the dewarp parameters logged, because in production you often only
  receive the dewarps and you must not assume they are rectilinear-clean.

### 1.8 Rolling shutter and the ISP

* **Rolling shutter**: rows are exposed sequentially with a row time of ~10–30 µs, so a full
  1080p frame takes 10–30 ms to read out. A person's leg moving at 3 m/s during a 20 ms
  readout skews by centimetres; a PTZ panning at 100 °/s shears vertical poles visibly.
  [derived] Consequences: keypoint-based pose is biased, and structure-from-motion /
  homography calibration from PTZ frames is systematically wrong unless modelled. Our
  "rolling shutter skew from row time × velocity" stage should log the row time so
  downstream code can compensate.
* **ISP pipeline order** (typical): black-level → linearisation → white balance →
  **demosaic** → colour matrix → tone/gamma → **noise reduction (spatial + temporal)** →
  **sharpening** → scaling → encode. Each stage leaves a signature:
  * *Demosaic* produces zipper and false-colour artefacts on high-frequency edges — e.g. the
    diamonds of a chain-link fence, which is the single most common perimeter texture.
  * *Temporal NR* is the important one for us: it averages frames, so in low light a slowly
    moving person leaves a **comet trail / smear**, and a stationary person is progressively
    blended into the background. 3D-NR is why "loitering" targets sometimes *fade out* and
    background subtraction stops seeing them. [lore]
  * *Sharpening* adds halos that become false edges; aggressive sharpening plus high gain
    produces the classic "crunchy" night image where noise grains look like distant people.
    Small-object detectors hallucinate on it.

### 1.9 Thermal: LWIR/MWIR, microbolometers, NETD, and the 9 Hz rule

Thermal is the answer to most of §1.1–§1.8 and brings its own set of problems.

* **Bands.** LWIR 8–14 µm is the surveillance band (uncooled, no illumination needed, sees
  through smoke and most haze); MWIR 3–5 µm needs cryogenic cooling, costs 10–50× more, and
  is used for long-range military-grade systems. [reference]
* **Detector.** Uncooled **vanadium-oxide microbolometers**. Teledyne FLIR's Boson core is
  the reference commodity part: "The FPA is a two-dimensional array of vanadium-oxide (VOx)
  microbolometers with 12-micron pitch", "The QVGA configuration provides 320x256 pixels
  while the VGA configuration provides 640x512"
  ([Boson datasheet](https://groupgets-files.s3.amazonaws.com/boson/documents/Boson%20datasheet,%20102-2013-40,%20Rev%20340.pdf)).
* **NETD** (noise-equivalent temperature difference) is the thermal analogue of read noise:
  Boson grades are "Consumer Grade <60mK NEDT, Professional Grade <50mK NEDT, Industrial
  Grade <40mK NEDT", and Boson+ reaches "Professional Grade <30mK NEDT, Industrial Grade
  <20mK NEDT" [same datasheet]. Sub-30 mK is what lets you see a person against a
  sun-warmed wall in late afternoon; 60 mK does not.
* **Physical envelope** matters for deployment realism: "12 µm pixel pitch VOx
  microbolometer, 21 x 21 x 11 mm camera body, Weight as low as 7.5 grams, Low power
  consumption, starting at 500 mW", rated "-40 °C to +80 °C" [same datasheet].
* **The 9 Hz rule.** "The U.S. government allows thermal cameras with frame rates less than
  9 fps to be exported without a license if not used for military purposes", and
  "Thermal cameras with frame rates greater than 9 Hz are controlled for export under the
  U.S. Department of Commerce's Export Control Classification Number (ECCN) 6A003.b.4.b";
  ECCN 6D994 additionally covers "software capable of increasing the frame rate of cameras
  to more than 9 Hz" [paraphrase of
  [LightPath ITAR guide](https://www.lightpath.com/insights/complete-guide-to-itar-compliant-thermal-cameras),
  [FLIR OEM export information](https://flir.custhelp.com/app/answers/detail/a_id/3221/~/flir-oem---camera-modules-export-information),
  [BIS Federal Register 2009](https://www.federalregister.gov/documents/2009/05/22/E9-11951/revisions-to-license-requirements-and-license-exception-eligibility-for-certain-thermal-imaging)].
  **Why you care:** a large installed base of exported thermal cameras runs at 8.33–9 Hz.
  Your tracker's motion model, your IoU thresholds and your "loitering for 30 s" timers must
  work at 9 fps, and the simulator must be able to *emit* 9 fps thermal alongside 25 fps
  RGB with honest timestamps.
* **Thermal-specific artefacts to simulate**: periodic **shutter/FFC** (flat-field
  correction) freezes of 0.3–1 s every few minutes (Boson+ is marketed as "Shutterless",
  which is precisely because this is a nuisance); **halo** around hot objects; **narcissus**
  (reflection of the cold detector); **vignetting** drift with housing temperature; **thermal
  crossover** at dawn/dusk when scene and body temperature equalise and contrast collapses to
  near zero. Thermal crossover is the honest answer to "is thermal a silver bullet?" — no,
  it has two half-hour windows a day where it is at its worst.
* **What thermal loses**: colour, texture, text, faces at range, and therefore most
  appearance-based re-ID and all attribute search ("red jacket"). A thermal-only system can
  tell you *someone* is there; it struggles to tell you *who*, which is why the market
  pairs it with RGB (§2.5).

### 1.10 PTZ: zoom, presets, and the tracking paradox

* Optical zoom on a 30–40× PTZ dome means the effective F-number rises at tele (a "F1.6–F4.7"
  lens loses ~3 stops zoomed in), so **zooming in at night makes the image darker and
  noisier at the same time as making the target bigger**. The net effect on detection is
  frequently negative beyond 10×. [derived + lore]
* Digital zoom adds nothing but interpolation, and analytics vendors' "up to 200×" figures
  are optical×digital.
* **PTZ auto-tracking** is a self-defeating data source: while the camera moves, the
  background model is invalid, the calibration is unknown, motion-based detection is
  saturated, and rolling shutter shears the frame. Serious systems use a *fixed* camera to
  cue a PTZ, and only run analytics on the PTZ when it is parked (pan/tilt/zoom stable for
  >0.5 s). Log PTZ state per frame in our ground truth so learners can be told "this frame
  is in motion". [lore]
* Preset drift and backlash: a PTZ returned to preset 3 a thousand times will not be within
  a pixel of its first visit. Any rule tied to a hand-drawn zone in image space therefore
  degrades over months. This is why zone definitions should live in **world coordinates**
  with per-frame extrinsics, which our ground-truth format supports.

### 1.11 Compression: H.264 / H.265, GOP, bitrate, and packet loss

Typical surveillance operating points [reference/lore]:

| Stream | Resolution | fps | Codec | Bitrate | GOP |
|---|---|---|---|---|---|
| Legacy analogue-over-IP / encoder | D1 704×576 | 12 | H.264 | 0.5–1 Mb/s | 1–2 s |
| Commodity 1080p, smart codec on | 1920×1080 | 12–25 | H.265 | 1–3 Mb/s | 2–4 s (up to 8 s) |
| 1080p quality profile | 1920×1080 | 25 | H.264 | 4–8 Mb/s | 1 s |
| 4K perimeter | 3840×2160 | 15–25 | H.265 | 6–12 Mb/s | 2–4 s |
| Analytics substream | 640×360 | 10–15 | H.264 | 0.2–0.5 Mb/s | 1–2 s |

Things that follow from this table and that people forget:

* **Most analytics run on the substream**, not the recording stream. Your model is being fed
  640×360 at 0.3 Mb/s while the evidence clip is 4K. A person at 40 m in the substream is
  8 px tall. Half of "our detector missed it" tickets are substream tickets. [lore]
* **"Smart codec" / Zipstream-class encoders** deliberately raise quantisation on regions
  judged uninteresting and lengthen GOPs on static scenes. This means **the encoder is
  itself an uncalibrated analytic upstream of yours**, and it preferentially destroys
  exactly the low-contrast, low-motion regions where a crawling or loitering person lives.
* **Long GOP + packet loss = multi-second corruption**, not a single bad frame: errors
  propagate until the next IDR. Artefacts to reproduce: grey/green macroblock fields,
  smearing "melted" texture, frozen regions, and partial frames. Our stage "decoding a
  damaged stream" is the right approach — synthesise loss at the RTP/NAL level and let a
  real decoder produce the damage, rather than drawing fake blocks.
* **Quantitative effect on detectors**: a comparative study of detection under compression
  ([Masykuroh et al., *ETRI Journal* 2025](https://onlinelibrary.wiley.com/doi/full/10.4218/etrij.2025-0363))
  varies "resolution, FPS, entropy-coding method, motion-estimation algorithm, CRF, and
  preset" and reports that "Video quality is markedly affected by variations from
  compression" with corresponding detection degradation [paraphrase — I could not retrieve
  the table through the proxy; **verify the exact numbers before quoting them in a
  deliverable**]. Edge-analytics work such as
  [How2Compress](https://arxiv.org/html/2510.18409) takes the complementary route of
  learning per-macroblock quantisation to protect accuracy at low bitrate, which is
  indirect evidence of how strong the effect is.
* Compressed-domain analytics are a real and underused tool: motion vectors and macroblock
  types give you near-free coarse motion detection
  ([compressed-domain motion detection for surveillance](https://www.researchgate.net/publication/221315082_Fast_Compressed_Domain_Motion_Detection_in_H264_Video_Streams_for_Video_Surveillance_Applications);
  [bitstream-domain multi-object tracking](https://arxiv.org/pdf/1202.4743)). On a 500-camera
  site this is how you triage which streams to decode at all.

### 1.12 VMS, transcoding, frame drops, timestamp drift

The last mile is the most under-modelled and the most operationally important:

* **Double compression.** Camera encodes → VMS re-encodes for storage tiering or for the
  web client → your pipeline decodes. Second-generation artefacts are *not* the same as
  first-generation ones; a model robustified against single-pass H.264 can still fall over
  on transcoded output.
* **Frame drops and duplicates.** Under network or CPU pressure, streams lose frames in
  bursts and some VMS clients duplicate the last frame to keep wall-clock pace. A tracker
  using constant-velocity prediction with assumed Δt = 40 ms will mis-associate across a
  400 ms gap. **Always drive trackers from real timestamps, never frame indices.** [lore]
* **Timestamp drift.** Cameras without NTP drift seconds to minutes per week; cameras with
  NTP still show 50–500 ms inter-camera skew, and the burnt-in OSD clock often disagrees with
  the RTP timestamp and with the VMS's own record time. Cross-camera tracking and multi-view
  fusion are extremely sensitive to this: at 1.4 m/s, 200 ms of skew is 28 cm of world-space
  disagreement — comparable to the accuracy you need for occupancy fusion. Our simulator's
  deliberate "time-sync jitter" is therefore a *feature under test*, not decoration.
* **Burnt-in OSD** (timestamp, camera name, logos, "VIDEO LOSS") occupies real pixels, is
  temporally static, and is learned by models as a camera fingerprint. It also breaks
  histogram-based and BRISQUE-style quality metrics. [lore]

---

## 2. How much accuracy do you actually lose? Quantified degradation

This section exists so that you can answer "how bad is it?" with numbers instead of
adjectives. **Learn three or four of these by heart.**

### 2.1 Generic corruption robustness: the canonical result

Michaelis et al., *Benchmarking Robustness in Object Detection: Autonomous Driving when
Winter is Coming* (NeurIPS 2019 ML4AD workshop) is the paper to cite:

> "The three resulting benchmark datasets are termed Pascal-C, Coco-C and Cityscapes-C,
> containing a large variety of image corruptions."

> "A range of standard object detection models suffer a severe performance loss on corrupted
> images (down to 30-60% of the original performance)."

([arXiv 1907.07484](https://arxiv.org/abs/1907.07484);
[code/leaderboard](https://github.com/bethgelab/robust-detection-benchmark)). Their metrics
are **mPC** (mean performance under corruption, averaged over corruption types and
severities) and **rPC** (relative performance under corruption, i.e. mPC as a fraction of
clean performance). The repository's leaderboard gives the headline augmentation result:
on Pascal-C "Stylizing training data achieved mPC of 56.2 [AP50] vs baseline 48.6";
on COCO-C "mPC of 20.4 [AP] vs baseline 18.2"; on Cityscapes-C "mPC of 17.2 [AP] vs baseline
12.2" ([README](https://github.com/bethgelab/robust-detection-benchmark/blob/master/README.md)).
Note how small the absolute numbers are: **Cityscapes-C at 12–17 AP means a driving-grade
detector is nearly useless under corruption**, and the fix, stylisation, buys ~5 AP.

The corruption taxonomy comes from Hendrycks & Dietterich's ImageNet-C: 15 corruption types
× 5 severities across noise/blur/weather/digital families, scored by **mCE** (mean corruption
error, normalised to AlexNet). The repository notes "ImageNet-C has all 1000 classes where
each image is the standard size", references "15 corruptions", and provides
"a spreadsheet [that] shows how to calculate the mean Corruption Error"; ImageNet-P measures
*stability* under perturbation sequences, with "mFR" and "mT5D" metrics
([hendrycks/robustness](https://github.com/hendrycks/robustness)).

**Caveat a veteran will throw at you:** ImageNet-C/COCO-C corruptions are *synthetic
post-hoc filters* (additive Gaussian noise, synthetic fog overlay, JPEG). They are not what a
camera does (§1). Models can be trained to be robust to ImageNet-C in ways that do not
transfer to real weather — which is precisely the argument for a *physically grounded*
degrade pipeline like ours rather than an `imagecorruptions` call.

### 2.2 Low light and night

* **ExDark** ("Exclusively Dark") is the standard low-light detection benchmark: "7,363
  low-light images from extremely low-light environments to low-light environments (a total
  of 10 different lighting conditions)" with "12 object categories"
  ([Loh & Chan, CVIU 2019](https://www.sciencedirect.com/science/article/abs/pii/S1077314218304296);
  [dataset mirror](https://hyper.ai/en/datasets/18216)). Reported operating points span an
  enormous range depending on protocol — "the accuracy of YOLOv3 on the ExDark dataset was
  given by mAP value of 21.35%" in one study, while enhancement-plus-detection pipelines
  report "Retinexformer achieves 66.1 AP on the ExDark dataset" and "DPEC achieved the
  highest map50 score of 60 AP" [paraphrase of the search-indexed summaries of
  [Retinexformer](https://arxiv.org/pdf/2303.06705) and [DPEC](https://arxiv.org/pdf/2407.09553)].
  **The lesson is not the numbers, it is the spread**: low-light detection results are
  protocol-dependent to the point of incomparability. Always ask which AP, which split,
  which enhancement, which detector.
* **NightOwls** (Neumann et al., ACCV 2018) is the night pedestrian benchmark:
  "A sample Faster RCNN detector achieves an average Miss Rate (MR) of 21.54% at the
  Reasonable setting on the NightOwls dataset", against daytime Caltech where
  "Performance on the Caltech dataset is nearly saturated, with an average miss rate of
  4.54% by the state-of-the-art detector" [paraphrase of
  [NightOwls](https://www.robots.ox.ac.uk/~vedaldi/assets/pubs/neumann18nightowls.pdf) and
  [nightowlsapi](https://github.com/ox-vgg/nightowlsapi)]. That is roughly a **4–5×
  increase in miss rate** for the same nominal task.
* The most brutal number in the literature comes from *When Pedestrian Detection Meets
  Nighttime Surveillance: A New Benchmark* (IJCAI 2020): "The SDS R-CNN detector achieves an
  average miss rate of 7.36% when applied to the daytime Caltech dataset, while the average
  miss rate increases drastically to 64% on a nighttime dataset"
  [paraphrase of [IJCAI 2020 paper 0071](https://www.ijcai.org/proceedings/2020/0071.pdf)].
  **~9× worse.** This is the single most useful statistic to quote to a stakeholder who asks
  why we are building a night-capable simulator. Note also that this benchmark is
  *surveillance* nighttime, not automotive nighttime — automotive night scenes are lit by
  headlights, surveillance night scenes are lit by whatever the estate manager installed in
  2006.
* Related datasets to know: **LOD** (low-light object detection, RAW-domain),
  **DarkFace** (6 000 real night images for face detection, the UG²+ challenge set),
  **BDD100K** with its day/night attribute (the standard "free" night/day ablation —
  detectors typically lose 5–15 AP on the night subset), and **NightCity** for segmentation.
  [reference]

### 2.3 Fog, rain, snow, dust

* **Foggy Cityscapes** (Sakaridis et al.) synthesises physically based fog on Cityscapes using
  depth and the standard optical model with attenuation coefficient β, giving meteorological
  visibility ranges of 600 m / 300 m / 150 m. It is the workhorse for foggy domain adaptation
  and the reason most DA-detection papers report "Cityscapes → Foggy Cityscapes" mAP.
  **RainCityscapes** does the same for rain streaks + veiling. [reference]
* **RESIDE** is the dehazing benchmark (synthetic indoor/outdoor ITS/OTS plus a real-world
  task set, RTTS, which crucially has *detection* annotations) — RTTS is how you show that
  "better PSNR dehazing" and "better detection" are different objectives. [reference]
* **ACDC** (Sakaridis et al., ICCV 2021) is the real-adverse-condition segmentation
  benchmark: "ACDC consists of a large set of 8012 images, half of which (4006) are equally
  distributed between four common adverse conditions: fog, nighttime, rain, and snow. Each
  adverse-condition image comes with a high-quality pixel-level panoptic annotation, a
  corresponding image of the same scene under normal conditions, and a binary mask that
  distinguishes between intra-image regions of clear and uncertain semantic content"
  ([ACDC ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/papers/Sakaridis_ACDC_The_Adverse_Conditions_Dataset_With_Correspondences_for_Semantic_Driving_ICCV_2021_paper.pdf),
  [arXiv 2104.13395](https://arxiv.org/pdf/2104.13395)). Two design ideas worth stealing
  wholesale for our simulator: **paired normal-condition correspondences** (we get these for
  free — same seed, different weather preset) and an **invalid/uncertain mask** so that
  metrics are not dominated by regions no human could label.
* The general finding across this literature: "despite the success of recent semantic
  segmentation models in clear weather and standard illumination conditions, these methods
  struggle with adverse conditions (e.g., rainy, foggy, snowy, and nighttime), which degrade
  the feature extraction process" [paraphrase, ACDC-derived literature]. Per-class collapse
  is extreme and asymmetric — one diffusion-based robustness study reports "the terrain class
  drops from 64.8 mIoU in the original dataset to 5.4 mIoU in snow"
  [paraphrase of [Cityscape-Adverse](https://arxiv.org/pdf/2411.00425)]. **Aggregate metrics
  hide this; always report per-class and per-condition.**
* **DAWN** (Kenk & Popescu) is the small but pointed real adverse-weather detection set:
  "1000 images from real-traffic environments, which are divided into four sets of weather
  conditions: fog, snow, rain and sandstorms", annotated with "7,845 total bounding boxes
  including car (82.21%), bus (2.05%), truck (8.22%), motorcycles + bicycles (1.36%), and
  person (6.07%)" ([arXiv 2008.05402](https://arxiv.org/abs/2008.05402)). Note the **6 %
  person share** — this is a vehicle benchmark, and there is essentially *no* large real
  benchmark for **people in adverse weather from fixed elevated CCTV viewpoints**. That gap is
  our product's reason to exist; say it in exactly those words in a design review.
* **Dust/sand** is the least-studied condition and the most relevant to border and
  infrastructure work: it is *forward-scattering* and *non-uniform in time* (gusts), so
  unlike fog it cannot be modelled by a single β. [lore]

### 2.4 Resolution and tiny targets

* **TinyPerson** (Yu et al., WACV 2020) is the definitive reference for the regime we live in:
  "The dataset contains 72,651 objects with bounding boxes hand-annotated, featuring quite
  tiny persons compared with other representative datasets and many images with dense objects
  (more than 200 persons per image)", and evaluation divides scale into
  "tiny[2, 20], small[20, 32] and all[2, inf]"
  ([arXiv 1912.10664](https://arxiv.org/abs/1912.10664),
  [TinyBenchmark](https://github.com/sxy1122/TinyBenchmark)). Their diagnosis is the one you
  should internalise: "scale mismatch between the dataset for network pre-training and the
  dataset for detector learning could deteriorate feature representation and detectors,
  leading to a proposed Scale Match approach to align object scales between the two datasets"
  [paraphrase].
* Practical scale thresholds for person analytics [lore, widely used in the trade and
  consistent with the tiny-object literature]:
  * **< 8 px height**: motion blob only; no reliable classification.
  * **~16 px**: detection possible, no attributes.
  * **~30–40 px**: attributes (clothing colour, bag) become marginally usable.
  * **~60–80 px**: pose/gait usable; re-ID starts working.
  * **~80+ px between the eyes**: face recognition (the EN 62676-4 / operational guidance
    family gives similar "identify/recognise/observe/detect/monitor" pixel-density tiers;
    UK DORI figures are the usual reference — **DORI: Detect 25 px/m, Observe 62 px/m,
    Recognise 125 px/m, Identify 250 px/m**, per IEC/EN 62676-4). [reference]
  * **Scale Match's real message for us**: because we *control* the camera geometry, we can
    generate a synthetic set whose **object-scale histogram matches the deployment site's**.
    That is a cheap, defensible, sim-specific win no real dataset can offer.

### 2.5 Thermal and RGB-T fusion

* **KAIST Multispectral Pedestrian** (Hwang et al., CVPR 2015) is the foundation: "the only
  pedestrian dataset that provides large-scale aligned visible and far infrared (thermal)
  images with manual annotations", "95,328 color-thermal image pairs recorded via color and
  thermal cameras mounted on the rooftop of a car at a frame rate of 20 fps, with spatial
  alignment ensured by a beam splitter and camera calibration"
  ([benchmark paper](https://soonminhwang.github.io/rgbt-ped-detection/misc/CVPR15_Pedestrian_Benchmark_ext.pdf)).
  The baseline is stark: "The KAIST benchmark baseline using Aggregated Channel Features (ACF)
  with thermal intensity and HOG features obtained 50.48% log-average miss rate for overall
  performance in both day and night times" [paraphrase]. Modern fusion drives this to single
  digits — "one approach achieves 9.94% miss rate on reasonable day conditions, 8.38% at
  night, and 9.34% overall", "The FCE-RCNN method achieves a log-average miss rate of 6.92%
  during nighttime detection", and late fusion "outperforms the ACF+T+THOG baseline by 5.12%
  during the day and 10.4% at night" [paraphrase of
  [Illumination-aware Faster R-CNN](https://arxiv.org/pdf/1803.05347),
  [FCE-RCNN, IET ITS 2024](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12562),
  [Deep Fusion CNN](https://www.academia.edu/30372196/Multispectral_Pedestrian_Detection_using_Deep_Fusion_Convolutional_Neural_Networks)].
  Note the shape of the result: **fusion's gain at night is roughly double its gain by day**.
* **LLVIP** is the surveillance-relevant one (fixed street cameras, not a car roof):
  "30,976 images (15,488 pairs), most of which were taken at very dark scenes with all images
  strictly aligned in time and space" ([arXiv 2108.10831](https://arxiv.org/abs/2108.10831),
  [ICCVW 2021 PDF](https://openaccess.thecvf.com/content/ICCV2021W/RLQ/papers/Jia_LLVIP_A_Visible-Infrared_Paired_Dataset_for_Low-Light_Vision_ICCVW_2021_paper.pdf)).
  Use LLVIP, not KAIST, when you want a fixed-camera night argument.
* **FLIR ADAS** (v2, per FLIR's dataset page): **26,442 annotated frames**, 9,711 thermal + 9,233 RGB train/val images, and **7,498 video frames with a 1:1 thermal/visible match**; thermal 640x512. The "~13,000 aligned pairs" figure once quoted here is **not supported** by FLIR. The commonly used *aligned* FLIR subset (third-party) is ~5,142 pairs (4,129 train + 1,013 test) — snippet-only `[audit R3 2026-09-26]` ([FLIR ADAS](https://oem.flir.com/solutions/automotive/adas-dataset-form/)).
  **CVC-14** (day/night FIR+visible, greyscale), **OTCBVS/OSU** (the historical thermal
  pedestrian set), and **M3FD** — "4,200 RGB and IR-aligned image pairs collected in various
  environments including different lighting, seasons, and weather scenarios, with six
  categories" — complete the standard suite [paraphrase of the
  [FusionU10 survey](https://www.frontiersin.org/journals/neurorobotics/articles/10.3389/fnbot.2024.1504070/full)].
* **Fusion methods** worth naming: halfway/mid-level feature fusion (Liu et al.),
  **Illumination-aware Faster R-CNN** (gates the two streams by a predicted day/night score),
  **AR-CNN / weakly-aligned cross-modal learning** ([arXiv 1901.02645](https://arxiv.org/pdf/1901.02645))
  which handles the fact that **real RGB-T pairs are never perfectly registered**,
  **GFD-SSD** gated fusion ([arXiv 1903.06999](https://arxiv.org/pdf/1903.06999)),
  **ProbEn** probabilistic ensembling ([arXiv 2104.02904](https://arxiv.org/pdf/2104.02904)) —
  which is important because it shows a *late*, calibration-based ensemble can beat elaborate
  feature fusion — and recent state-space fusion, e.g.
  [Fusion-Mamba](https://arxiv.org/pdf/2404.09146).
* **The misalignment point is the one veterans care about.** On a real site the thermal and
  RGB cameras are two separate units 15 cm apart with different FOVs and different frame
  rates (possibly 9 Hz vs 25 Hz, §1.9). Papers that assume beam-splitter registration are
  solving an easier problem than production. Our simulator is uniquely able to generate
  **controlled mis-registration** (parallax, FOV mismatch, temporal offset) with exact ground
  truth — that is a genuinely publishable capability, not just an engineering nicety.

### 2.6 Tracking-specific degradation

Detection metrics understate the operational damage, because trackers amplify detection noise
into identity errors. ByteTrack's motivation is the canonical statement of the mechanism:
"The objects with low detection scores, e.g. occluded objects, are simply thrown away, which
brings non-negligible true object missing and fragmented trajectories", and its remedy is
"For the low score detection boxes, we utilize their similarities with tracklets to recover
true objects and filter out the background detections", reaching "MOTA: 80.3, IDF1: 77.3,
HOTA: 63.1" on MOT17 test ([ByteTrack](https://github.com/ifzhang/ByteTrack)).

Under degradation the score distribution shifts *down and flattens*, so **a fixed score
threshold tuned in daylight silently becomes a different operating point at night.** That is
one of the highest-value, lowest-effort findings our simulator can produce: sweep the
detector threshold across degrade profiles and show the curve moving. [lore, but trivially
demonstrable with our harness.]

An honest illustration of end-to-end condition sensitivity comes from Synthehicle's own
baselines, where the *same* model is evaluated per condition: detection (YOLOX-x)
"All conditions: 59.7% AP, Day: 58.7% AP, Dawn: 60.8% AP, Rain: 56.8% AP, Night: 50.6% AP",
while re-identification collapses far harder — "All conditions: 47.8% mAP, Day: 59.8% mAP,
Dawn: 47.57% mAP, Rain: 39.08% mAP, Night: 27.04% mAP"
([Synthehicle](https://github.com/fubel/synthehicle)). **Detection loses ~8 AP from day to
night; appearance re-ID loses 33 mAP — a 55 % relative collapse.** Re-ID/MTMC is the fragile
part of the stack under degradation, and our multi-camera ground truth is aimed exactly
there.

---

## 3. Mitigations, and which ones actually work

### 3.1 Image enhancement (and the trap)

* **Zero-DCE** (Guo et al., CVPR 2020) reframes enhancement as curve fitting:
  "Zero-Reference Deep Curve Estimation (Zero-DCE) formulates light enhancement as a task of
  image-specific curve estimation with a deep network", trains "a lightweight deep network,
  DCE-Net, to estimate pixel-wise and high-order curves for dynamic range adjustment", and
  crucially "does not require any paired or unpaired data during training, achieved through a
  set of carefully formulated non-reference loss functions" [paraphrase of
  [arXiv 2001.06826](https://arxiv.org/abs/2001.06826),
  [project page](https://li-chongyi.github.io/Proj_Zero-DCE.html);
  Zero-DCE++ is the fast variant, [arXiv 2103.00860](https://arxiv.org/abs/2103.00860)].
  Its appeal for us: no paired data, microseconds per frame class of cost, so it is deployable
  on an edge box.
* **SCI** (Self-Calibrated Illumination, CVPR 2022), **KinD / KinD++** (Retinex
  decomposition into reflectance + illumination), and **Retinexformer** (ICCV 2023) are the
  other names to know. Retinexformer is evaluated across "15+ benchmarks" including
  "LOL-v1, LOL-v2 (real and synthetic), SID, SMID, SDSD (indoor and outdoor), MIT Adobe
  FiveK, LIME, NPE, MEF, DICM, VV, NTIRE 2024, ExDark (nighttime object detection)", with
  "PSNR 27.18 / SSIM 0.850" on LOL-v1 under the KinD/LLFlow setting
  ([Retinexformer repo](https://github.com/caiyuanhao1998/Retinexformer)).
* **The trap.** Enhancement optimises human-visible quality (PSNR/SSIM/aesthetics) and that
  objective is *not* the detector's objective. Enhancement amplifies noise, invents texture,
  and shifts the input distribution away from what the detector was trained on. The clearest
  published demonstration in the haze domain is *From Fog to Failure*: "Though effective in
  foggy conditions, the dehazing approach unexpectedly degrades the performance on clear
  images", and "Their findings highlight the need for selective preprocessing and challenge
  assumptions about universal benefits from cascading transformations"; the authors note that
  "Models trained primarily on foggy conditions lack the ability to preserve the natural
  characteristics of clear images, leading to unintended alterations that degrade detection
  performance", and propose "the integration of a haze-level estimation module to prevent
  unnecessary processing by triggering dehazing only when haze exceeds a certain threshold"
  [paraphrase of [arXiv 2502.02027](https://arxiv.org/abs/2502.02027),
  [OpenReview](https://openreview.net/forum?id=dVzxB1isCQ)].
* **The veteran's rule**: *do not put an enhancer in front of a detector you did not retrain.*
  If you must enhance, either (a) train the detector on enhanced images, (b) make the enhancer
  a *learned, task-supervised* front end (the IDOD-YOLOv7 / DST-DETR / ADAM-Dehaze family of
  joint architectures — see [IDOD-YOLOv7](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9921160/),
  [DST-DETR](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11280984/),
  [ADAM-Dehaze](https://arxiv.org/pdf/2506.15837)), or (c) gate it on a degradation estimate.
  Enhancement for the *operator's* screen and enhancement for the *model* are two different
  products. Ship both, separately.
* **Deblurring** has the same structure. DeblurGAN-v2 "reaches 10-100 times faster than the
  nearest competitors, while maintaining close to state-of-the-art results", with
  "PSNR/SSIM metrics of 29.55/0.934 with InceptionResNet-v2 and 28.17/0.925 with MobileNet"
  ([DeblurGANv2](https://github.com/VITA-Group/DeblurGANv2)) — and its README makes **no claim
  about downstream detection**, which is itself the finding.

### 3.2 Robustness by training: augmentation

* **Stylisation** is the strongest simple result in the detection-robustness literature (§2.1):
  +7.6 mPC AP50 on Pascal-C, +2.2 on COCO-C, +5.0 on Cityscapes-C
  ([robust-detection-benchmark](https://github.com/bethgelab/robust-detection-benchmark)). Its
  theoretical justification is Geirhos et al.: "ImageNet-trained CNNs are strongly biased
  towards recognising textures rather than shapes, which is in stark contrast to human
  behavioural evidence and reveals fundamentally different classification strategies"; "The
  same standard architecture (ResNet-50) that learns a texture-based representation on
  ImageNet is able to learn a shape-based representation instead when trained on
  'Stylized-ImageNet'", and this "comes with unexpected emergent benefits such as improved
  object detection performance and robustness towards a wide range of image distortions"
  [paraphrase of [arXiv 1811.12231](https://arxiv.org/abs/1811.12231)]. The repo quantifies
  the shift: shape bias "Standard ResNet-50: 21.39%" → "ResNet-50 trained on
  Stylized-ImageNet (model A): 81.37%", validated against "48,560 human psychophysical trials
  across 97 participants in a controlled lab setting"
  ([texture-vs-shape](https://github.com/rgeirhos/texture-vs-shape)).
  **Why this matters enormously for us:** degradation (noise, compression, fog, IR) destroys
  *texture* while largely preserving *shape*. A texture-biased model is therefore
  structurally the wrong model for CCTV, and a simulator that randomises textures
  aggressively while keeping human shape/motion correct is producing exactly the right
  inductive bias. Note also the healthy dissent — a 2025 re-analysis argues
  "ImageNet-trained CNNs are not biased towards texture"
  ([arXiv 2509.20234](https://arxiv.org/pdf/2509.20234)) — so present it as a strong
  hypothesis, not gospel.
* **AugMix** (Hendrycks et al., ICLR 2020): "AugMix, a data processing technique that mixes
  augmented images and enforces consistent embeddings of the augmented images, which results
  in increased robustness and improved uncertainty calibration"; "The full AugMix method also
  adds a Jensen-Shanon Divergence consistency loss to enforce consistent predictions between
  two different augmentations of the input image and the clean image itself"; it "significantly
  improves robustness and uncertainty measures on challenging image classification benchmarks,
  closing the gap between previous methods and the best possible performance by more than half
  in some cases", with a released ResNet-50 at "a 65.3 mean Corruption Error (mCE) and a
  77.53% top-1 accuracy on clean ImageNet data"
  ([augmix](https://github.com/google-research/augmix)). **RandAugment** is the cheaper
  search-free policy; both are standard in modern detection recipes.
* **The honesty caveat**, from *The Many Faces of Robustness*
  ([arXiv 2006.16241](https://arxiv.org/pdf/2006.16241)): robustness is not one axis, and
  gains on synthetic corruptions frequently do not transfer to real distribution shift.
  Training on ImageNet-C-style corruptions and testing on ImageNet-C is partly a test of
  whether you memorised the corruption. **Hold out corruption families.** Our degrade
  profiles should be split into train-profiles and test-profiles for exactly this reason,
  and the harness should report "unseen-degradation" numbers separately.
* **Weather-specific augmentation** has a dataset-bias literature of its own — see
  *In Rain or Shine: Understanding and Overcoming Dataset Bias for Improving Robustness
  Against Weather Corruptions* ([arXiv 2204.01062](https://arxiv.org/pdf/2204.01062)).

### 3.3 Domain adaptation and domain generalisation

The family tree, in the order you should be able to recite it:

* **DANN** (Ganin & Lempitsky, 2015) — gradient-reversal adversarial feature alignment; the
  ancestor of nearly everything.
* **CycleGAN** (Zhu et al., 2017) — "Unpaired Image-to-Image Translation using Cycle-Consistent
  Adversarial Networks" ([repo](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix)).
  Used pervasively for day→night and clear→foggy "free" data. Its well-known failure modes
  (hallucinated structure, label-geometry drift, checkerboard texture) mean **you must never
  translate images and keep the old labels without checking geometry**. [lore]
* **DA-Faster R-CNN** (Chen et al., CVPR 2018) — image-level + instance-level adversarial
  alignment; introduced the Cityscapes→Foggy Cityscapes protocol that every subsequent paper
  reports.
* **Strong-Weak / SW-DA, SCDA, categorical alignment, Mean-Teacher DA, adaptive teacher** —
  the 2019–2022 progression.
* **SFOD / source-free object detection** — adapt without access to source data. This is the
  *commercially* relevant branch: in security you frequently cannot export customer footage,
  and you cannot ship a model back to the source data. Source-free and test-time methods are
  the only legally workable options on many sites. [lore + reference]
* **Test-time adaptation** — TENT (entropy minimisation on BN statistics), CoTTA (continual
  TTA), and BN-statistics-only recalibration. **The cheapest real win in the whole section is
  BN/statistics recalibration per camera**: for many detectors, simply re-estimating
  normalisation statistics on a few hundred unlabelled frames from *that* camera recovers a
  meaningful fraction of the loss, because much of the domain gap is first- and second-order
  image statistics. [lore, widely reproduced]
* **Domain generalisation for multi-view** is where GMVD lands its punch: "existing
  state-of-the-art models show poor generalization by overfitting to a single scene and camera
  configuration" ([GMVD](https://github.com/jeetv/GMVD)). Any multi-camera occupancy model
  trained on WILDTRACK alone is fitting *WILDTRACK's seven camera poses*, not the task. Our
  simulator's ability to randomise camera topology is therefore not a nice-to-have; it is the
  only way to train a deployable multi-view model.

### 3.4 Foundation models under corruption

* Self-supervised/foundation features are meaningfully more robust than supervised ones.
  DINOv2: "DINOv2 models produce high-performance visual features that can be directly
  employed with classifiers as simple as linear layers on a variety of computer vision tasks;
  these visual features are robust and perform well across domains without any requirement
  for fine-tuning", with ImageNet-1k linear probes of "ViT-S/14: 81.1%, ViT-B/14: 84.5%,
  ViT-L/14: 86.3%, ViT-g/14: 86.5%" ([dinov2](https://github.com/facebookresearch/dinov2)).
  DINOv3 is reported to achieve "the best robustness to corruptions (ImageNet-C) among
  self-supervised learning models" [paraphrase of [arXiv 2508.10104](https://arxiv.org/pdf/2508.10104)].
* **SAM**: "The Segment Anything Model (SAM) produces high quality object masks from input
  prompts such as points or boxes", "trained on a dataset of 11 million images and 1.1 billion
  masks", and "has strong zero-shot performance on a variety of segmentation tasks"
  ([segment-anything](https://github.com/facebookresearch/segment-anything)). Note what the
  README does *not* claim: it says nothing about out-of-distribution or degraded imagery. In
  practice SAM degrades sharply on low-contrast night frames, thermal, and heavy compression —
  it was trained on photographs, and CCTV is not photography. [lore]
* **Open-vocabulary detectors** (OWL-ViT, GroundingDINO, YOLO-World) are the most seductive and
  most dangerous tool for this domain: they give you "person with a backpack" zero-shot, and
  they fall apart under distribution shift. See *Open-Vocabulary Object Detectors: Robustness
  Challenges under Distribution Shifts* ([arXiv 2405.14874](https://arxiv.org/pdf/2405.14874)).
  **Benchmark them on our degrade profiles before anyone promises them to a customer.**
* Frequency-domain curricula are an emerging robustness lever, e.g.
  [FastDINOv2](https://arxiv.org/html/2507.03779v1) and
  [frequency/contrastive shape-bias regularisation](https://arxiv.org/pdf/2509.11355).

### 3.5 Beyond the visible camera

* **Event cameras** (DVS) output per-pixel asynchronous brightness changes with microsecond
  latency and ~120 dB dynamic range, no motion blur, and very low power — properties that map
  almost perfectly onto the CCTV failure modes in §1.4 and §1.6. The community hub is
  [uzh-rpg/event-based_vision_resources](https://github.com/uzh-rpg/event-based_vision_resources);
  simulators (ESIM, v2e) can synthesise events from high-frame-rate rendered video, which
  means **our UE5 pipeline could emit an event stream essentially for free** by rendering at
  high internal frame rate and differencing log-intensity. That is a strong differentiator and
  a low-cost experiment. Limits: no absolute intensity, no texture, essentially no appearance
  re-ID, tiny ecosystem, and almost no installed base in security. [reference + lore]
* **Radar-camera fusion** is the mature perimeter answer: mmWave/FMCW radar gives range and
  radial velocity in zero visibility and does not care about fog or darkness, at the cost of
  poor angular resolution and no identity. Commercial perimeter products (radar cues the PTZ,
  camera confirms) are the deployed architecture. The simulator analogue is cheap: we already
  have world-space ground truth, so a radar model is a geometry + RCS + clutter model, not a
  rendering problem.
* **LiDAR** appears in the literature far more than in security budgets, and rain/fog/snow
  degrade it too (false returns from droplets). Don't oversell it.
* **Audio, PIR, fence-vibration, RF** — the multi-sensor hooks already in our roadmap. The
  operationally important point: **fusion is mostly a false-alarm-reduction technology, not a
  detection technology.** Perimeter systems live and die on false alarms per kilometre per
  night, and a second modality's main job is to veto. [lore]

---

## 4. Camera tampering and image-quality analytics

This is the most commercially under-rated capability in the whole stack, because it is what
keeps the rest of the stack honest. A 500-camera site typically has 5–15 % of cameras
degraded at any moment (defocused, cobwebbed, sun-bleached, rotated by a cleaner, IR LED
dead, lens dome crazed by UV). Nobody knows until an incident. [lore]

### 4.1 No-reference image quality assessment

* **BRISQUE** (Mittal et al., 2012) — fits a generalised Gaussian to mean-subtracted
  contrast-normalised (MSCN) coefficients and their pairwise products, then regresses a
  quality score with an SVR trained on human opinion scores. Opinion-aware.
* **NIQE** (Mittal et al., 2013) — the same NSS features but **completely blind**: it fits a
  multivariate Gaussian to features from a corpus of pristine images and scores test images by
  Mahalanobis distance. No human scores needed, which makes it the practical choice for
  unattended monitoring. [reference]
* **MUSIQ** (Ke et al., ICCV 2021) — multi-scale transformer IQA that handles native
  resolutions and aspect ratios rather than fixed crops; state-of-the-art on the modern IQA
  sets. [reference]
* **PIQE, CORNIA, CLIP-IQA, ARNIQA** round out the list; CLIP-based IQA is the current
  trendline because it needs no IQA training set at all. [reference]
* **Warnings for CCTV use** [lore]:
  * NSS-based metrics were calibrated on *photographs*. Burnt-in OSD text, IR monochrome,
    thermal palettes and heavy 3D-NR all sit far outside their pristine corpus, so absolute
    scores are meaningless. **Use them as per-camera time series with per-camera baselines**
    and alarm on *change*, not on absolute value.
  * Any global IQA metric will flag a *correctly* exposed night image as "bad". Condition on
    time of day and on the camera's own history.
  * The useful features in practice are embarrassingly simple: edge-energy percentiles
    (defocus), frame-difference entropy (freeze), histogram occupancy + clipping fraction
    (cover/glare/AE failure), colour saturation (IR-cut state), block-edge energy at 8/16 px
    periodicity (bitrate starvation), and global homography residual vs a reference
    (displacement).

### 4.2 Tamper detection algorithms

The literature is small, old and surprisingly good. The canonical taxonomy is three events:
**occlusion / covering**, **defocus**, and **displacement (moved or rotated)**, sometimes plus
**video loss** and **spray/obscuration**.

* Methods surveyed and enhanced in *Comparative study and enhancement of Camera Tampering
  Detection algorithms* ([arXiv 1608.02385](https://arxiv.org/pdf/1608.02385)) and
  the sabotage-detection and adaptive-tamper literature use: "Edge information, frame count,
  foreground objects' coverage area and its static nature are used as features for detection";
  "SURF feature detector is employed to find interest points and compare/match them using
  MSAC algorithm for detecting camera movement and zoom"; "Edge differences and grayscale
  histogram analysis between current and previous frames have been used to identify camera
  tampering"; and "Wavelet-based methods have been used to detect defocused camera view and
  occluded camera view" [paraphrase of the surveyed methods, see also
  [Rapid detection of camera tampering and abnormal disturbance](https://www.sciencedirect.com/science/article/abs/pii/S1047320314001473),
  [SIFT-based camera tamper detection](https://www.researchgate.net/publication/261308979_Sift-based_camera_tamper_detection_for_video_surveillance),
  [Real-Time Adaptive Camera Tamper Detection](https://www.researchgate.net/publication/221315328_Real-Time_Adaptive_Camera_Tamper_Detection_for_Video_Surveillance)].
* Reported performance: "Three types of camera tampering (occlusion, defocus, and motion) were
  detected with an overall recognition rate of 94% in some test scenarios", and another
  approach achieved "detection of more than 96 percent of malicious events without false
  alarms for 13 hours of video with 350 tampering events from more than 20 different scenes"
  [paraphrase of the above sources]. **Take those numbers with salt**: the hard part is not
  recall on staged tamper, it is precision over months of real video where lorries park in
  front of cameras, fog rolls in, and cleaners shine torches.
* **The false-positive list every veteran carries in their head** [lore]: a parked
  vehicle/skip occupying the view; fog and heavy rain (looks exactly like defocus + contrast
  loss); direct sun into the lens at two specific times of year; condensation inside the dome
  at dawn; snow on the dome; a cobweb lit by the IR LEDs (looks like occlusion at night, gone
  by day); AE hunting; automatic IR-cut switching (huge global change, perfectly legitimate);
  and a legitimate PTZ preset tour (displacement alarm every cycle). A tamper detector that
  does not know the camera's own PTZ and IR-cut state will generate one alarm per camera per
  night, which means it will be turned off.
* **Why our simulator matters here more than anywhere else**: tamper is *rare, deliberate and
  unlabelled* in real archives. We can generate spray, cover, tilt, defocus, glare/laser,
  unplug and cut with exact onset timestamps and matched negatives (fog, parked lorry,
  cobweb) — the exact confusion pairs above. That is a dataset nobody can buy. Our sensor-model
  doc already lists these as first-class render stages; make sure the **matched hard negatives**
  are generated at ≥ 3:1 against positives, which is what the diversity budget in
  [`06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md) already mandates.
* Adjacent but distinct: **video forensics / deepfake and re-encoding detection** (double-JPEG,
  PRNU-based camera identification) answers "has this file been altered?", not "is this camera
  healthy?". Do not confuse the two in a customer conversation; see the forensic-analytics
  survey ([arXiv 2401.02960](https://arxiv.org/pdf/2401.02960)).

---

## 5. Synthetic data and simulation for surveillance analytics

### 5.1 A short history you should be able to tell in three minutes

| Era | Work | What it proved |
|---|---|---|
| 2016 | **Virtual KITTI** (Gaidon et al.) | Clones of a real dataset in a game engine; pre-training on synthetic transfers to real tracking/flow. |
| 2016 | **SYNTHIA** (Ros et al.) | 9k+ frames of virtual city segmentation; synthetic + a little real beats real alone. |
| 2016 | **Playing for Data / Playing for Benchmarks** (Richter et al., GTA-V) | Labels can be harvested almost free from a commercial game; 1/3 of the real data plus synthetic matched full real data. |
| 2017 | **Tobin et al., Domain Randomization** | "With enough variability in the simulator, the real world may appear to the model as just another variation." |
| 2018 | **JTA** (Fabbri et al., GTA-V) | Pose and tracking of many people from a game, with 3D joints. |
| 2018–20 | **CARLA**, **AirSim**, **Unity Perception**, **BlenderProc**, **Kubric** | Simulation became infrastructure rather than a one-off dataset. |
| 2019 | **MultiviewX** | Synthetic replica of a real multi-camera rig (WILDTRACK) — the first "digital twin of a camera topology". |
| 2021 | **MOTSynth** | Large-scale synthetic pedestrian tracking; synthetic-only training reaches parity on MOT17. |
| 2021 | **PeopleSansPeople** | Human-centric, privacy-preserving, parameterised DR; synthetic pre-training beats ImageNet pre-training. |
| 2021 | **EPE, Richter et al.** | Learned photorealism enhancement using G-buffers — realism as a post-process. |
| 2022 | **GMVD**, **Synthehicle**, **UBnormal**, **CrowdSim** | Synthetic data aimed at *generalisation across camera configurations*, MTMC, and anomalies. |
| 2023 | **BEDLAM** | "Neural networks trained only on synthetic data achieve state-of-the-art accuracy on 3D human pose and shape (HPS) estimation from real images." |
| 2023–24 | **Infinigen**, **Infinigen Indoors** | Fully procedural worlds; no asset-library ceiling on diversity. |
| 2024–25 | **UnrealZoo**, **MATRIX**, video world models (**Cosmos**, Genie-class, Sora-class) | Interactive photoreal worlds at scale; generative video as a data source. |

### 5.2 The headline sim-to-real results, with numbers

**MOTSynth** (Fabbri et al., ICCV 2021,
[arXiv 2108.09518](https://arxiv.org/abs/2108.09518),
[baselines](https://github.com/dvl-tum/motsynth-baselines)) is the reference you will cite most
often, because it is *our exact task*:

* "How Can Synthetic Data Help Pedestrian Detection and Tracking?" — 768 sequences, ~1.3 M
  frames, ~9.5 k identities from 579 pedestrian models.
* Detection: "YOLOv3 trained on MOTSynth-full achieved a +45.25 AP improvement over
  VIPER-trained models and +18.72 AP over JTA-trained models on MOT17" [paraphrase].
* Tracking: "When training on MOTSynth without fine-tuning using Tracktor, the model achieved
  45.0 MOTA and 51.2 IDF1, yielding +3.5 MOTA and +1.6 IDF1 improvement over the COCO-trained
  model (43.5 MOTA and 49.6 IDF1)" [paraphrase]. The published baselines repo reproduces
  "OVERALL | 49.7% IDF1 | ... | 45.3% MOTA" for a MOTSynth-trained Mask R-CNN on MOT17-train
  ([README](https://github.com/dvl-tum/motsynth-baselines)).
* Parity claim: "Models trained on synthetic data are on-par with state-of-the-art on
  MOTChallenge MOT17&MOT20, while extremely crowded MOT20 still requires fine-tuning";
  "Unlike MOT17, fine-tuning has a significant effect on MOT20 ... likely because MOTSynth does
  not have the extremely crowded scenes that are the focus of MOT20" [paraphrase].
* **The diversity result is the one to internalise**: "The diversity of MOTSynth, particularly
  in terms of people appearance, is identified as a crucial factor for bridging the domain gap,
  with a smaller, more diverse subset (MOTSynth-256) yielding significant AP improvements over
  JTA-trained models (+9.81 AP for YOLOv3 and +8.92 AP for Faster R-CNN)" [paraphrase].
  **A quarter of the data with more appearance diversity beat more data with less.** This
  directly justifies the "≥ 500 unique hero identities, ≥ 60 garment meshes × unbounded
  colours" line in our diversity budget.

**BEDLAM** (Black et al., CVPR 2023, [arXiv 2306.16940](https://arxiv.org/abs/2306.16940)):
"BEDLAM demonstrates that neural networks trained only on synthetic data achieve
state-of-the-art accuracy on 3D human pose and shape (HPS) estimation from real images"
[paraphrase]. The *reason* given is the realism inventory: "diversity of body shapes, motions,
skin tones, hair, and clothing, with clothing realistically simulated using commercial clothing
physics simulation", rendered with "varying numbers of people ... in realistic scenes with
varied lighting and camera motions", and explicitly contrasted with prior work where
"Previous synthetic datasets had been small, unrealistic, or lacked realistic clothing"
[paraphrase]. **BEDLAM is the strongest existing evidence that cloth simulation and hair are
not vanity features — they are the difference between transfer and no transfer for
body-centric tasks.**

**PeopleSansPeople** (Unity, [repo](https://github.com/Unity-Technologies/PeopleSansPeople)) —
"A human-centric privacy-preserving synthetic data generator with highly parametrized domain
randomization", with "28 parameterized 3D human assets, 39 animation clips, 21,952 unique
clothing textures, parameterized lighting and camera systems, natural backgrounds, and
primitive occluders/distractors", emitting "2D bounding boxes, human keypoints, semantic and
instance segmentation masks in COCO format, plus 3D bounding boxes". The benchmark numbers are
the useful part, because they isolate *pre-training value*:

* With 32 057 real samples — "From scratch: 55.80 / ImageNet pre-training: 57.50 /
  PeopleSansPeople pre-training: 60.37 ± 0.48" keypoint AP.
* With 6 411 real samples — "Scratch: 37.30 / ImageNet: 44.20 / Synthetic pre-training: 52.70".

**Read that second row carefully: synthetic pre-training is worth +8.5 AP over ImageNet when
real data is scarce, and +2.9 AP even when it is plentiful.** The scarce-data regime is
precisely the regime of a new customer site with a new camera topology. That is the business
case for our simulator in one table.

**Other numbers worth carrying:** Synthehicle's "17 hour ... 64 scenes in four different
weather conditions, 16 different camera setups, and 340 camera videos" with per-condition
baselines (§2.6) is the template for how we should publish *our* dataset card; UBnormal's
supervised open-set design — "abnormal events annotated at the pixel level at training time,
for the first time enabling the use of fully-supervised learning methods for abnormal event
detection", with "disjoint sets of anomaly types in our training and test collections of
videos" and best test results of "a Micro-AUC of 68.5 and Macro-AUC of 80.3"
([UBnormal](https://github.com/lilygeorgescu/UBnormal)) — is the template for our behaviour
catalogue's train/test split, and its low AUCs are a useful reality check on how hard
open-set anomaly detection still is.

### 5.3 Domain randomisation: theory, and the structured variant

Tobin et al.'s formulation is the founding idea: "Domain randomization, a simple technique for
training models on simulated images that transfer to real images by randomizing rendering in
the simulator. With enough variability in the simulator, the real world may appear to the model
as just another variation", achieving "the first successful transfer of a deep neural network
trained only on simulated RGB images (without pre-training on real images) to the real world
for the purpose of robotic control" [paraphrase of
[arXiv 1703.06907](https://arxiv.org/abs/1703.06907)].

Mechanically, DR works because it **prevents the network from relying on any factor that is
randomised**, forcing it onto invariants. The design rule follows directly and is the most
useful single heuristic in this whole document:

> **Randomise everything you do not want the model to use; keep physically correct everything
> you do want it to use.**

For person analytics that means: randomise textures, colours, materials, lighting colour and
placement, backgrounds, distractors, camera intrinsics, noise and compression aggressively;
keep **human proportions, biomechanically plausible gait, gravity, occlusion geometry, and
camera projection** correct. Getting that split wrong is the usual cause of "we randomised a
lot and it still didn't transfer".

**Structured domain randomisation (SDR)** (Prakash et al., 2019) adds context: sample scenes
from a *plausible layout distribution* rather than uniformly, so cars sit on roads and
pedestrians on pavements. For surveillance this is essential — uniformly scattered people is a
distribution no camera has ever seen, and a model trained on it wastes capacity. Our Zone
Graph / semantic-zone design (queue, entrance, restricted, perimeter) is SDR in all but name.

**Automatic / learned DR** closes the loop: DeceptionNet, meta-sim, and the "learn the
simulator parameters that maximise downstream real-set accuracy" family. This is a natural
Phase-5 research contribution for us because we own the simulator's parameter space and the
evaluation harness.

### 5.4 The realism-versus-diversity debate

Two camps, both with evidence:

* **Diversity camp**: DR, MOTSynth's MOTSynth-256 result, PeopleSansPeople's texture
  randomisation. Argument: transfer comes from covering the space, and photorealism is an
  expensive way to cover a tiny part of it.
* **Realism camp**: BEDLAM ("trained only on synthetic data ... state-of-the-art"), EPE,
  Infinigen. Argument: for tasks where the *signal itself* is fine appearance detail —
  body shape under clothing, face, gait, material — unrealistic renders teach the wrong thing.

**The reconciliation, which is what a veteran will say:** it depends on whether the
task-relevant signal is *geometric/semantic* or *photometric*. Detection and tracking of
people are largely geometric (silhouette, motion, scale, occlusion) → diversity dominates.
Re-ID, attribute recognition, fine-grained behaviour and face are photometric → realism
dominates. Our product must do both, which is why the stack is "UE5 realism **and** aggressive
randomisation", and why we should be explicitly measuring *which* tasks benefit from which
knob. That ablation — realism ladder × diversity ladder × task — is arguably the most
interesting experiment this project can run, and nobody has published it for fixed-camera
surveillance.

Third position worth knowing: **the degradation channel may matter more than either.** A
photoreal render that skips §1's imaging chain is *less* like real CCTV than a mediocre render
with a correct sensor model, because the real camera destroys most of the realism you paid for.
[lore, and the explicit design bet of this repo.]

### 5.5 Measuring the sim-to-real gap

Four families of method; use at least one from each:

1. **Distributional image metrics** — FID, KID, and for video FVD. Cheap, popular, and
   **weakly correlated with downstream utility**. FID is sensitive to resolution, JPEG level,
   crop policy and sample count, and it is computed with an ImageNet Inception network whose
   features are not meaningful for 640×360 night monochrome. EPE introduced **sKVD**
   (segmentation-weighted KVD) precisely because plain FID/KID compare incomparable scene
   layouts ([EPE project](https://isl-org.github.io/PhotorealismEnhancement/)). **Rule: report
   FID/KID stratified by camera and by degrade profile, never as a single number, and never as
   the primary claim.**
2. **Downstream-task protocols** — the only ones that matter. The four canonical experiments:
   * *Synthetic-only → real test* (the hardest and most honest, à la BEDLAM);
   * *Synthetic pre-train → real fine-tune* (the commercially normal one, à la
     PeopleSansPeople);
   * *Real-only vs real+synthetic at matched budget* (does synthetic add anything you could not
     buy with more real data?);
   * *Data-efficiency curves* — plot real-label count on x, accuracy on y, one curve per
     synthetic strategy. This is how you show "synthetic is worth N real labels", which is the
     only sentence a procurement manager understands.
3. **Representation-gap diagnostics** — per-class/per-condition AP gap (not aggregate),
   confusion-structure comparison, feature-space distance (CKA, MMD, domain-classifier AUC: if
   a small CNN can separate synthetic from real at 99 % AUC, your gap is enormous and you can
   *use that classifier's saliency to find out why*), and texture-vs-shape probes à la Geirhos.
4. **Human perceptual checks** — the 2AFC real-vs-synthetic study already specified in
   [`06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md). Cheap, and it catches
   embarrassments (wrong shadow direction, floating feet, impossible clothing) that no metric
   flags.

**Mixed curricula** that reliably work in practice [lore, consistent with the cited results]:
pre-train on synthetic at high volume and high diversity → fine-tune on real with a low
learning rate and frozen early layers → keep a synthetic replay fraction (10–30 %) in the
fine-tuning mix to prevent catastrophic forgetting of the rare degraded cases → and always
oversample synthetic *hard* conditions (night, fog, tiny, tamper) rather than sampling the
synthetic set uniformly. A 50/50 batch mix is the usual default and is usually not optimal;
tune the ratio, it is worth several AP.

### 5.6 Generative realism transfer and video world models

* **Image-translation realism transfer**: CycleGAN/CUT/MUNIT applied sim→real. EPE
  (Richter et al., 2021) is the strongest engineered version — an enhancement network
  conditioned on the renderer's **G-buffers** (geometry, materials, lighting), trained with a
  multi-level adversarial objective, translating GTA-V toward Cityscapes/KITTI/Mapillary
  [paraphrase of [EPE](https://isl-org.github.io/PhotorealismEnhancement/); the repo confirms
  result comparisons "with baselines (Color Transfer, CUT, MUNIT)"]. Descendants:
  [CARLA2Real](https://arxiv.org/html/2410.18238v2) applies EPE-style enhancement inside CARLA
  and explicitly frames it as "reducing the sim2real gap"; [REGEN](https://arxiv.org/pdf/2508.17061)
  targets real-time photorealism enhancement in games. **Why we should be cautious:** the
  translation network is trained toward *one* real domain, so it imports that domain's
  camera, weather and city. For a product sold into many sites, a realism-transfer net is a
  per-site asset, not a universal one. And it can move object boundaries, silently
  invalidating pixel-accurate labels.
* **Diffusion-generated training data**: the StableRep / synthetic-clones / "generative data
  augmentation" line shows text-to-image data can match or beat real data for
  *classification* at scale, and diffusion-based editing is now used to build robustness
  benchmarks ([Cityscape-Adverse](https://arxiv.org/pdf/2411.00425) builds adverse-condition
  variants by diffusion editing). For **detection and tracking** the blocker is labels:
  diffusion does not hand you boxes, masks, 3D positions or identities. Current practice is
  therefore diffusion as an *appearance augmenter on top of* a simulator that owns the
  geometry — which is exactly the architecture we should adopt: UE5 owns truth, diffusion
  optionally restyles pixels, and we validate that labels still fit.
* **Video world models (2025–26)**: NVIDIA Cosmos is the flagship open platform —
  "An open platform of world models, datasets, and tools that enables developers to build
  Physical AI for robots, autonomous vehicles, smart infrastructure, and more", with the
  "Cosmos 3 family ... Super (64B), Nano (16B), and Edge (4B)", able to "generate images,
  videos, synchronized audio, and action sequences", covering "world generation, world
  simulation, future prediction, synthetic data generation, policy learning, and robot
  training", under the "OpenMDW-1.1 License" ([NVIDIA/Cosmos](https://github.com/NVIDIA/Cosmos)).
  Genie-class and Sora-class models are the closed analogues.
  **Limits, stated plainly, because this is where hype lives:** (a) no exact ground truth —
  no boxes, no identities, no calibration, no world coordinates, so they cannot replace a
  simulator for supervised surveillance training; (b) identity drift over seconds, which is
  fatal for the *only* thing tracking and re-ID care about; (c) no controllability of the
  specific rare behaviour you need ("hand a bag over at 22:03 in camera 7's blind spot");
  (d) physics that looks right and is not (feet slide, occlusion order flips); (e) licensing
  and provenance exposure if the model was trained on scraped surveillance-like footage.
  The honest 2026 use cases are **appearance restyling of simulator output**, **rare-condition
  augmentation**, **operator-facing visual search pre-training**, and **scenario ideation** —
  not label-bearing data generation.

### 5.7 The commercial landscape (know the names, know the pitch)

Open/academic: UnrealZoo ("100+ scenes", "10+ agents", "RGB-D, masks, panorama, LiDAR, and
occupancy observations", "53.46 FPS at 2K" [a **README claim**, not a paper result — the paper, arXiv 2412.20977 Table 2, benchmarks only at 640x480 (e.g. 83 FPS colour) `[audit R3 2026-09-26]`], "Apache 2.0 license" —
[repo](https://github.com/UnrealZoo/unrealzoo-gym)); NVIDIA Omniverse Replicator and Isaac
Replicator Agent (IVA-oriented, YAML-driven characters and cameras); Unity Perception
(**note: the repo now states "This project has been discontinued and is no longer supported by
Unity"** — [repo](https://github.com/Unity-Technologies/com.unity.perception)); UnrealCV;
CARLA ("open-source simulator for autonomous driving research", "flexible specification of
sensor suites and environmental conditions", MIT code + CC-BY assets —
[repo](https://github.com/carla-simulator/carla)); AirSim ("a platform for AI research to
experiment with deep learning, computer vision and reinforcement learning algorithms", with a
"Computer Vision mode" and "Weather Effects" — [repo](https://github.com/microsoft/AirSim);
note it is archived in favour of Project AirSim/Cosmos-era tooling); BlenderProc
("A procedural Blender pipeline for photorealistic rendering", outputting "RGB, stereo, depth,
normal and segmentation images/sequences" as ".hdf5 containers, COCO & BOP annotations" —
[repo](https://github.com/DLR-RM/BlenderProc)); Kubric ("A data generation pipeline for
creating semi-realistic synthetic multi-object videos with rich annotations such as instance
segmentation masks, depth maps, and optical flow", aiming to "span the entire complexity range
from CLEVR all the way to real-world video" — [repo](https://github.com/google-research/kubric));
Infinigen ("Infinite Photorealistic Worlds using Procedural Generation", BSD-3-Clause —
[repo](https://github.com/princeton-vl/infinigen)).

Commercial synthetic-data vendors you will be asked about: **Datagen** (faces/humans,
now largely pivoted), **Synthesis AI**, **Rendered.ai** (platform/PaaS, strong on sensor
modelling incl. SAR/EO), **SKY ENGINE AI** (explicitly sells synthetic CCTV/person data),
**Anyverse** (physically based sensor + ISP simulation — closest to our §1 philosophy),
**Parallel Domain** (AV-focused, high fidelity), **CVEDIA** (CVEDIA-RT, and notable because it
sells *surveillance analytics trained on synthetic data* — the nearest competitor to the vendor's
pitch), **Duality AI Falcon** (digital twins, EO/IR sensor emphasis), **Mindtech Chameleon**
(explicitly security/retail person-centric synthetic data), **Bifrost** (geospatial/EO).
[reference — vendor claims are marketing; none publish peer-reviewed transfer results at the
level of MOTSynth or BEDLAM, and that absence is itself a fair thing to point out.]

**The strategically useful observation:** the vendors that survive sell **sensor-accurate**
synthetic data (Anyverse, Rendered.ai, Duality) or **vertical-specific person data** (Mindtech,
SKY ENGINE, CVEDIA). Generic "pretty renders of people" is a commodity. Our differentiation is
the intersection: *multi-camera topology + behaviour labels + a physically defensible CCTV
degradation chain*. Nobody is selling all three.

---

## 6. Rendering realism specifics for a UE5 / MetaHuman pipeline

### 6.1 Humans

* **Skin**: subsurface scattering is what separates "MetaHuman" from "game character", and it
  is nearly irrelevant at 30 px person height and completely irrelevant in IR monochrome.
  Spend the budget on it only for the close-range/face cameras. [lore]
* **Hair**: strand-based grooms are expensive and alias badly at distance; card-based LODs
  flicker under TAA, which produces temporal texture that trackers notice. Verify that hair LOD
  transitions do not create appearance discontinuities *mid-track* — that is a synthetic-only
  artefact that will teach a re-ID model something false. [lore]
* **Clothing**: BEDLAM's evidence says simulated cloth matters for body-shape tasks
  [paraphrase]. For us the cheaper and more important axis is **garment variety and
  layering** (hood up/down, bag, hi-vis over jacket), because that is what appearance-change
  and disguise scenarios need — and because hi-vis is an IR special case (§1.5).
* **Motion**: mocap-derived locomotion (AMASS/BEDLAM, CMU, Mixamo) plus Motion Matching. Two
  synthetic tells to avoid: **foot sliding** (breaks any gait or speed-based analytic) and
  **identical animation phase across a crowd** (a crowd all stepping in time is instantly
  recognisable and teaches a false temporal prior). Randomise animation start phase and
  playback rate per agent. [lore]

### 6.2 Lighting and camera

* **Lumen** gives you the thing that matters most at night: plausible *indirect* light from a
  handful of point sources. But Lumen is temporally noisy at low light and its denoiser
  produces low-frequency flicker that looks like AGC hunting — decide which you are modelling
  and do not let the renderer's artefacts masquerade as the sensor's. Bake or raise
  Lumen quality for capture, and add AGC behaviour *deliberately* in post. [lore]
* Our doc already mandates: motion blur off in-engine, auto-exposure off in-engine, TSR/DLSS
  off for capture. **That is the correct call** — every one of those is a stochastic,
  temporally-recurrent filter that would make the physical post-process model
  non-identifiable and the dataset non-reproducible.
* **Motion blur done right**: accumulate sub-frame samples or convolve along the velocity
  buffer with kernel length = exposure_time × pixel_velocity. A single velocity-buffer blur is
  a good approximation except at occlusion boundaries, which is precisely where a person's
  limbs are — so for hero cameras prefer temporal super-sampling (render at 8× frame rate and
  average) at least for validation of the cheap path. [derived]
* **Rolling shutter done right**: render N row-bands at time offsets t + row·t_row and
  composite. Expensive but exact; do it for one validation profile and use a shear
  approximation elsewhere. Log `t_row` in the camera spec. [derived]
* **Lens distortion**: implement Brown–Conrady and Kannala–Brandt as documented in
  [OpenCV's camera calibration](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) and
  [`cv::fisheye`](https://docs.opencv.org/4.x/db/d58/group__calib3d__fisheye.html), and
  **export the coefficients in the ground truth** so downstream users can undistort. A
  synthetic dataset with distortion and no coefficients is strictly worse than one with
  neither.
* **Noise**: use the unprocess→noise→reprocess route (§1.3,
  [unprocessing](https://github.com/timothybrooks/unprocessing)), with per-camera calibrated
  `(a, b)` heteroscedastic parameters (σ² = a·I + b). If you can, calibrate `a, b` from a real
  camera of the class you are imitating by shooting a flat grey chart at several gains; that
  single half-day of lab work buys more realism than a week of shader tweaking. [lore]

### 6.3 Thermal rendering

There is no turnkey LWIR renderer in UE5, so know the approaches:

* **Emissivity/temperature material model**: assign each material an emissivity ε and a
  temperature T, compute apparent radiance ≈ ε·σT⁴ + (1−ε)·σT_env⁴, map to 14-bit counts, then
  apply NETD noise, FFC drift, vignetting and the display palette. This is what our sensor-model
  doc already specifies ("emissivity-based grey mapping from material tags (skin 36 °C, clothes
  ambient+Δ, engines hot, glass reflective)") and it is the right level of fidelity for
  detection/tracking work.
* Things that make it convincing rather than cartoonish [lore]: clothing is *cooler* than skin
  (insulation), so an exposed face/hands are the hot spots and a person in a heavy coat is much
  lower contrast; wet surfaces are cooled by evaporation; concrete and metal have very
  different thermal inertia so a wall that baked all afternoon is hotter than air at 22:00 and
  *hides* people against it; glass is opaque in LWIR and reflective (you see reflections of
  hot objects, not through windows); car bonnets and exhausts are the brightest things in most
  scenes; **thermal crossover** (§1.9) must be reachable in the time-of-day sweep.
* Prior art to cite: thermal/IR sensor plugins for AirSim and CARLA, and the "thermal image
  synthesis" / RGB→thermal translation literature (physics-based rendering plus GAN refinement,
  typically validated by training a detector on synthetic thermal and testing on KAIST/FLIR).
  [reference — no reachable verbatim source through the proxy; verify before citing specifics.]
* **A shortcut worth knowing**: because thermal has no texture to speak of, synthetic thermal
  transfers *better* than synthetic RGB. The domain gap is smaller when the domain has less
  information. This is one of the few places where our simulator can plausibly claim
  near-real-grade training data today.

---

## 7. Evaluating synthetic data quality (and the fine print)

**Metrics checklist for a dataset card.** Per-condition and per-camera: object-scale
histogram; occlusion-level histogram; identities per sequence; behaviour-class counts;
lux/EV distribution; measured SNR and BRISQUE/NIQE distributions vs a real reference set;
FID/KID vs matched real sets; label self-consistency checks (do projected 3D boxes match the
2D boxes? do masks match boxes? does world position agree across cameras?). The last item is
free for us and is the thing real datasets cannot assert.

**The genuine advantages, stated precisely:**

* **Label-noise-free and label-complete.** Real MOT/ReID benchmarks have annotation error
  rates that are a non-trivial fraction of the differences between published methods; heavily
  occluded and tiny people are inconsistently labelled. We get pixel-exact masks, 3D positions,
  amodal boxes, occlusion fractions and persistent identity *through* occlusion — an
  annotation that is physically impossible to obtain by hand. Amodal + occlusion-fraction
  labels alone enable experiments (e.g. "at what occlusion level does IDF1 collapse?") that
  cannot be run on real data at all.
* **Counterfactual pairs.** Same seed, one factor changed. This turns robustness evaluation
  from correlational to causal: you can attribute a 9 AP drop to *fog specifically*, holding
  people, paths and camera fixed. ACDC's "corresponding image of the same scene under normal
  conditions" is the real-world approximation of this and it took a research team years; we get
  it from a config flag.
* **Privacy and lawful basis.** Real CCTV of identifiable people is personal data under
  GDPR/UK DPA; biometric use is special-category. Training sets built from real surveillance
  footage are a recurring source of retractions and regulatory trouble (the DukeMTMC and
  MS-Celeb-1M withdrawals being the canonical examples). PeopleSansPeople's self-description as
  "privacy-preserving" is not marketing fluff — it is the entire procurement argument in many
  jurisdictions.
* **Controlled bias.** We can *balance* skin tone, age, body type, gait and clothing by
  construction, and measure per-group performance. That is a compliance deliverable
  (EU AI Act-style documentation for a high-risk biometric/surveillance system) that no scraped
  dataset can produce. Caveat: balanced synthetic data does **not** guarantee fairness in
  deployment, because the *degradation* channel is itself group-correlated — lower-reflectance
  skin returns fewer photons under IR illumination and in low light, so SNR at a given range
  differs by group. **Measure this explicitly.** It is one of the most defensible novel
  findings this project could produce, and one of the most important ethically.

**Licensing gotchas that have killed projects** [reference + lore]:

* **GTA-V-derived data (JTA, MOTSynth, MTA, GMVD's GTA portion)** depends on a commercial game
  EULA and script hooks; fine for research, not for a shipped commercial model. Read the
  dataset's own terms, not the paper.
* **Epic content licence**: City Sample, MetaHuman and Fab assets are generally licensed for
  use *in Unreal Engine projects*. Whether rendered images are a permitted "distribution" for
  training a commercial model is a question for counsel, and MetaHuman terms have historically
  been restrictive about use outside UE. **Ask before building the product on it.**
* **Research-only motion/body assets**: AMASS, BEDLAM motions, SMPL/SMPL-X model licences are
  non-commercial in whole or part. A commercial pipeline needs commercially licensed mocap.
* **Dataset-derived textures/HDRIs**: check CC-BY-NC vs CC-BY. One NC HDRI in your randomiser
  contaminates the output.
* **Model licences flow downstream**: OpenMDW, NVIDIA licences and "research use only"
  checkpoints constrain what you can ship even if your data is clean.
* **Practical control**: maintain an asset manifest with licence per asset, emitted into every
  dataset's metadata. This is boring, cheap, and is the difference between a demo and a
  product.

---

## 8. Open problems, 2024–2026

1. **No real benchmark for people in adverse weather from fixed elevated CCTV.** Everything
   real is automotive (DAWN, ACDC, BDD) or daytime multi-view (WILDTRACK). This is the single
   clearest dataset-shaped hole in the field.
2. **Robustness transfer is unsolved**: gains on synthetic corruption benchmarks do not reliably
   transfer to real degradation ([Many Faces of Robustness](https://arxiv.org/pdf/2006.16241)).
   Nobody has shown that a *physically simulated* imaging chain transfers better than
   `imagecorruptions`. **That is a paper we could write with the assets in this repo.**
3. **Enhancement-for-machines** remains mostly unformalised; the field still optimises PSNR for
   a downstream consumer that does not care ([From Fog to Failure](https://arxiv.org/abs/2502.02027)).
4. **Cross-modal misalignment** in RGB-T: real pairs are unregistered, at different frame rates,
   with different FOVs; most fusion research assumes otherwise
   ([AR-CNN](https://arxiv.org/pdf/1901.02645) being an honourable exception).
5. **Multi-view / MTMC generalisation across camera topologies** — GMVD showed models "overfit
   to a single scene and camera configuration"; the problem is not solved, and camera-placement
   optimisation is barely explored.
6. **Long-horizon identity** across hours, non-overlapping views, and clothing change. Almost
   all re-ID research assumes same-day same-clothes. Cloth-changing re-ID is nascent and
   synthetic data is the obvious lever.
7. **Open-set / few-shot behaviour and anomaly detection**: UBnormal's best numbers
   ("Micro-AUC of 68.5") show how far from solved this is.
8. **Video world models as labelled data sources** — controllability and ground truth are the
   blockers (§5.6). Hybrid "simulator owns geometry, generative model owns pixels" is the open
   engineering problem, including how to *prove* labels survive the restyling.
9. **Automatic simulator tuning** (learned DR / meta-sim) at the scale of a full surveillance
   scene, optimised against a small real validation set, with guarantees against overfitting to
   it.
10. **Certification and documentation**: EU AI Act-style obligations for high-risk surveillance
    systems will demand per-condition, per-demographic performance evidence. Nobody has a
    standard way to produce it; a simulator is the only practical instrument.
11. **Edge compute reality**: models must run at 12–15 fps per stream on cheap accelerators,
    which rules out most of the robustness literature's architectures. Robustness *per FLOP* is
    an unstudied axis.
12. **Degradation-aware fairness** (see §7). Essentially unstudied, and uncomfortable.
13. **Tamper/health analytics** has no modern benchmark at all; the good papers are 2010–2016
    and evaluate on tens of hours.
14. **Event-camera surveillance** has no installed base and no benchmark, but the physics is a
    near-perfect match for night perimeter work. High risk, high reward.

---

## 9. What a 20-year veteran knows that papers don't say

1. **Most "AI failures" are installation failures.** Wrong height, wrong angle, camera looking
   into the rising sun twice a year, IR flooding a nearby wall. Before touching a model, ask for
   a photo of the mounting. [lore]
2. **The analytics stream is not the recording stream.** You are being fed the 640×360
   substream at 0.3 Mb/s; the customer is showing you 4K evidence clips. Always ask which stream
   the model consumes. [lore]
3. **Never trust frame indices; always use timestamps** — and expect the OSD clock, the RTP
   timestamp and the VMS record time to disagree (§1.12). [lore]
4. **Spiders, moths and rain within a metre of the lens cause more night alarms than humans
   do.** Any night false-alarm budget that ignores near-field IR-lit insects is fiction. [lore]
5. **Hi-vis clothing breaks night analytics**, because retro-reflection saturates the sensor
   (§1.5). Sites full of contractors in hi-vis are the hardest night sites, not the easiest.
   [lore]
6. **Thermal has two bad half-hours a day** (thermal crossover at dawn and dusk) and a large
   installed base capped at 9 Hz by export control (§1.9). Design timers and trackers for 9 fps.
   [sourced: ECCN 6A003.b.4.b / 6D994]
7. **Zooming a PTZ in at night makes things worse**: F-number rises with zoom, so you gain
   angular resolution and lose 2–3 stops of light simultaneously (§1.10). [derived]
8. **3D noise reduction erases stationary people.** The loiterer you most want to detect is the
   one the ISP is busy averaging into the background (§1.8). [lore]
9. **WDR makes colour non-stationary**, which is a primary hidden cause of colour-attribute
   search failure and cross-camera re-ID failure (§1.6). Never build a product feature on
   absolute RGB. [lore]
10. **A detector threshold tuned by day is a different operating point at night**, because the
    score distribution shifts. Re-calibrate per condition, and prefer per-camera calibration
    over global (§2.6). [lore, trivially demonstrable]
11. **Enhancement in front of an un-retrained detector usually loses accuracy** even when the
    image looks better to a human (§3.1). Ship the pretty pipeline to the operator's monitor
    and the ugly pipeline to the model. [sourced: *From Fog to Failure*]
12. **The cheapest real win is per-camera statistics recalibration** (BN stats / TTA) on a few
    hundred unlabelled frames from that camera. It takes an afternoon and recovers a chunk of
    the domain gap (§3.3). [lore]
13. **Diversity beats volume for synthetic person data**: MOTSynth-256 (a quarter of the data,
    more appearance variety) beat larger, less diverse sets by ~9–10 AP. Spend the budget on
    identities and garments, not on frames. [sourced: MOTSynth]
14. **Synthetic pre-training beats ImageNet pre-training for human tasks, and the advantage is
    biggest when real labels are scarce** (+8.5 keypoint AP at 6.4 k real samples). That is the
    slide for the budget meeting. [sourced: PeopleSansPeople]
15. **Cloth simulation and body-shape diversity are load-bearing, not cosmetic**, for
    body-centric transfer. [sourced: BEDLAM]
16. **Randomise what you don't want learned; keep physically correct what you do.** If a
    quantity is a cue the model should use (projection, gait, occlusion order, scale), it must
    be right; everything else should be noise. [sourced: Tobin et al., plus SDR]
17. **Match the object-scale histogram of the target site.** Scale mismatch between pre-training
    and deployment measurably degrades tiny-person detection, and we can fix it by construction
    (§2.4). [sourced: Scale Match / TinyPerson]
18. **Multi-view models overfit camera topology.** A model trained on one rig is fitting that
    rig. Randomise camera counts and poses or your MTMC numbers are meaningless off-site.
    [sourced: GMVD]
19. **Texture is the first thing degradation destroys and the first thing CNNs reach for.**
    Texture-biased models are structurally wrong for CCTV; stylisation/texture randomisation is
    the cheapest counter (§3.2). [sourced: Geirhos, Michaelis]
20. **Report per-condition and per-class, never a single mAP.** Aggregate metrics hide the
    collapse (terrain 64.8 → 5.4 mIoU in snow; re-ID 59.8 → 27.0 mAP day → night). Anyone who
    shows you one number is hiding something, including you. [sourced: Cityscape-Adverse,
    Synthehicle]
21. **FID is not a sim-to-real metric.** It is resolution-, crop- and codec-sensitive and its
    feature extractor knows nothing about night monochrome CCTV. Report it stratified, and make
    downstream task performance the claim (§5.5). [lore + EPE's sKVD motivation]
22. **Fusion is a false-alarm technology.** Sell the second modality as a veto that lets a
    guard sleep, not as a detection miracle. Perimeter contracts are won on false alarms per km
    per night. [lore]
23. **Tamper detection dies of false positives, not false negatives.** Unless it knows the
    camera's PTZ state, IR-cut state and the weather, it will cry wolf nightly and be switched
    off (§4.2). [lore]
24. **10 % of a large estate is degraded right now and nobody knows.** Camera-health analytics
    is the highest-ROI, least-glamorous product in the portfolio, and it makes every other
    metric interpretable. [lore]
25. **Licensing kills more synthetic-data projects than realism does.** GTA-derived data,
    MetaHuman terms, AMASS non-commercial clauses, one NC HDRI in the randomiser. Keep a
    per-asset licence manifest from day one (§7). [lore]
26. **Operators are part of the system.** An alert stream above roughly one actionable alarm
    per operator per 10–15 minutes is ignored wholesale, regardless of precision. Evaluate
    alerts per hour against operator load, as our harness already plans to. [lore]
27. **The degradation channel may matter more than the renderer.** A mediocre render through a
    correct imaging chain looks more like CCTV than a beautiful render through none. That is
    this repository's central bet, and it is a defensible one. [lore — and the thing to
    actually test]

---

## Sources

**Imaging chain, sensors, vendors, standards**
- [Axis · IR in surveillance: Day-and-night cameras and OptimizedIR (white paper)](https://www.axis.com/dam/public/a0/56/91/ir-in-surveillance-en-US-398429.pdf) · [landing page](https://whitepapers.axis.com/en-us/ir-in-surveillance) · [OptimizedIR](https://www.axis.com/solutions/optimizedir) · [2018 edition](https://www.axis.com/dam/public/da/54/a6/ir-in-surveillance-en-US-191142.pdf)
- [Axis · Wide dynamic range: WDR solutions for forensic value](https://www.axis.com/dam/public/ba/52/11/wide-dynamic-range-en-US-379535.pdf) · [Forensic WDR](https://www.axis.com/solutions/forensic-wdr) · [WDR article](https://www.axis.com/files/feature_articles/ar_wdr_58805_1407_r1_lo.pdf) · [Tec-Tel WDR glossary](https://tec-tel.com/glossary/wdr)
- [Lumileds · LUXEON IR emitters for surveillance cameras](https://lumileds.com/wp-content/uploads/files/WP37-luxeon-ir-emitters-for-surveillance-cameras-white-paper.pdf) · [Axton · 850 nm vs 940 nm](https://axtontech.com/infrared-850nm-vs-940nm-wavelength/)
- [Teledyne FLIR Boson datasheet](https://groupgets-files.s3.amazonaws.com/boson/documents/Boson%20datasheet,%20102-2013-40,%20Rev%20340.pdf) · [mirror](https://www.elimec.co.il/_Uploads/dbsAttachedFiles/Boson.pdf) · [Boson+ 640×512 product page](https://www.oemcameras.com/products/23640a032-htm)
- [Teledyne · How to Evaluate Camera Sensitivity](https://www.teledynevisionsolutions.com/learn/learning-center/machine-vision/how-to-evaluate-camera-sensitivity/) · [Fairchild/Teledyne · Low Light Imaging for Security & Surveillance](https://fairchildimaging.com/low-light-imaging) · [Adimec · Comparing Camera Performance: Sensitivity](https://www.adimec.com/comparing-camera-performance-part-1-sensitivity/) · [ScienceDirect · Minimum Illumination](https://www.sciencedirect.com/topics/computer-science/minimum-illumination)
- [IISW 2023 · 0.5e- rms read noise CMOS image sensors](https://imagesensors.org/Past%20Workshops/2023%20Workshop/2023%20Papers/R75.pdf) · [IISW 2023 · 1.40 µm pixel, NIR-enhanced](https://imagesensors.org/Past%20Workshops/2023%20Workshop/2023%20Papers/R16.pdf) · [US 10,225,498 · night-vision pixel](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10225498) · [Quanta image sensor, Sci. Rep.](https://www.nature.com/articles/s41598-022-17952-z)
- Export control: [LightPath · ITAR-compliant thermal cameras](https://www.lightpath.com/insights/complete-guide-to-itar-compliant-thermal-cameras) · [FLIR OEM export information](https://flir.custhelp.com/app/answers/detail/a_id/3221/~/flir-oem---camera-modules-export-information) · [BIS Federal Register 2009](https://www.federalregister.gov/documents/2009/05/22/E9-11951/revisions-to-license-requirements-and-license-exception-eligibility-for-certain-thermal-imaging) · [OEMCameras export conditions](https://www.oemcameras.com/export-conditions/)
- Compression: [Masykuroh et al., ETRI Journal 2025 · detection under compression](https://onlinelibrary.wiley.com/doi/full/10.4218/etrij.2025-0363) · [How2Compress](https://arxiv.org/html/2510.18409) · [H.264 bitstream-domain tracking](https://arxiv.org/pdf/1202.4743) · [compressed-domain motion detection](https://www.researchgate.net/publication/221315082_Fast_Compressed_Domain_Motion_Detection_in_H264_Video_Streams_for_Video_Surveillance_Applications) · [H.264 in IP surveillance](https://www.networkwebcams.co.uk/blog/h264-video-compression-in-ip-video-surveillance-systems/)
- Optics/calibration: [OpenCV calib3d](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) · [cv::fisheye (Kannala–Brandt)](https://docs.opencv.org/4.x/db/d58/group__calib3d__fisheye.html)

**Degradation benchmarks and quantified drops**
- [Michaelis et al. · Benchmarking Robustness in Object Detection (arXiv 1907.07484)](https://arxiv.org/abs/1907.07484) · [code/leaderboard](https://github.com/bethgelab/robust-detection-benchmark) · [README](https://github.com/bethgelab/robust-detection-benchmark/blob/master/README.md) · [ML4AD PDF](https://ml4ad.github.io/files/papers/Benchmarking%20Robustness%20in%20Object~Detection:%20Autonomous%20Driving%20when%20Winter%20is%20Coming.pdf)
- [Hendrycks & Dietterich · ImageNet-C/-P code](https://github.com/hendrycks/robustness) · [The Many Faces of Robustness](https://arxiv.org/pdf/2006.16241) · [Visually-continuous corruption robustness vs humans](https://arxiv.org/pdf/2402.19401)
- [Loh & Chan · Exclusively Dark (ExDark), CVIU 2019](https://www.sciencedirect.com/science/article/abs/pii/S1077314218304296) · [dataset](https://hyper.ai/en/datasets/18216) · [YOLA low-light detection](https://arxiv.org/pdf/2410.18398) · [Trash to Treasure](https://arxiv.org/pdf/2309.03548) · [PE-YOLO](https://arxiv.org/pdf/2307.10953) · [ISP-driven low-light data modeling](https://arxiv.org/pdf/2504.12204)
- [Neumann et al. · NightOwls](https://www.robots.ox.ac.uk/~vedaldi/assets/pubs/neumann18nightowls.pdf) · [nightowlsapi](https://github.com/ox-vgg/nightowlsapi) · [When Pedestrian Detection Meets Nighttime Surveillance (IJCAI 2020)](https://www.ijcai.org/proceedings/2020/0071.pdf)
- [Sakaridis et al. · ACDC (ICCV 2021)](https://openaccess.thecvf.com/content/ICCV2021/papers/Sakaridis_ACDC_The_Adverse_Conditions_Dataset_With_Correspondences_for_Semantic_Driving_ICCV_2021_paper.pdf) · [arXiv](https://arxiv.org/pdf/2104.13395) · [project](https://acdc.vision.ee.ethz.ch/) · [Cityscape-Adverse](https://arxiv.org/pdf/2411.00425) · [BTSeg](https://arxiv.org/pdf/2308.16819) · [Semantic segmentation under adverse conditions (BMVC 2022)](https://bmvc2022.mpi-inf.mpg.de/0977.pdf)
- [Kenk & Popescu · DAWN (arXiv 2008.05402)](https://arxiv.org/abs/2008.05402) · [IEEE DataPort](https://ieee-dataport.org/documents/dawn-vehicle-detection-adverse-weather-nature) · [In Rain or Shine: weather dataset bias](https://arxiv.org/pdf/2204.01062)
- [Yu et al. · Scale Match for Tiny Person Detection (arXiv 1912.10664)](https://arxiv.org/abs/1912.10664) · [TinyBenchmark](https://github.com/sxy1122/TinyBenchmark) · [SM+](https://arxiv.org/pdf/2102.03558) · [Backbones for tiny object detection](https://arxiv.org/pdf/2303.11267)
- [Hwang et al. · KAIST Multispectral Pedestrian Benchmark (CVPR 2015)](https://soonminhwang.github.io/rgbt-ped-detection/misc/CVPR15_Pedestrian_Benchmark_ext.pdf) · [Illumination-aware Faster R-CNN](https://arxiv.org/pdf/1803.05347) · [AR-CNN / weakly aligned cross-modal](https://arxiv.org/pdf/1901.02645) · [GFD-SSD](https://arxiv.org/pdf/1903.06999) · [ProbEn](https://arxiv.org/pdf/2104.02904) · [Attention fusion one-stage](https://pmc.ncbi.nlm.nih.gov/articles/PMC8235776/) · [FCE multispectral (IET ITS 2024)](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12562) · [Deep Fusion CNN](https://www.academia.edu/30372196/Multispectral_Pedestrian_Detection_using_Deep_Fusion_Convolutional_Neural_Networks)
- [LLVIP (arXiv 2108.10831)](https://arxiv.org/abs/2108.10831) · [ICCVW PDF](https://openaccess.thecvf.com/content/ICCV2021W/RLQ/papers/Jia_LLVIP_A_Visible-Infrared_Paired_Dataset_for_Low-Light_Vision_ICCVW_2021_paper.pdf) · [FusionU10 (FLIR/M3FD/LLVIP)](https://www.frontiersin.org/journals/neurorobotics/articles/10.3389/fnbot.2024.1504070/full) · [Fusion-Mamba](https://arxiv.org/pdf/2404.09146) · [Thermal pedestrian saliency](https://arxiv.org/pdf/1904.06859) · [ThermEval (VLMs on thermal)](https://arxiv.org/pdf/2602.14989)
- [ByteTrack](https://github.com/ifzhang/ByteTrack)

**Mitigations**
- [Zero-DCE (arXiv 2001.06826)](https://arxiv.org/abs/2001.06826) · [project](https://li-chongyi.github.io/Proj_Zero-DCE.html) · [Zero-DCE++](https://arxiv.org/abs/2103.00860) · [code](https://github.com/Li-Chongyi/Zero-DCE) · [Retinexformer](https://arxiv.org/pdf/2303.06705) · [code](https://github.com/caiyuanhao1998/Retinexformer) · [DPEC](https://arxiv.org/pdf/2407.09553)
- [From Fog to Failure (arXiv 2502.02027)](https://arxiv.org/abs/2502.02027) · [OpenReview](https://openreview.net/forum?id=dVzxB1isCQ) · [ADAM-Dehaze](https://arxiv.org/pdf/2506.15837) · [IDOD-YOLOv7](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9921160/) · [DST-DETR](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11280984/) · [DeblurGAN-v2](https://github.com/VITA-Group/DeblurGANv2)
- [Geirhos et al. · texture vs shape (arXiv 1811.12231)](https://arxiv.org/abs/1811.12231) · [code](https://github.com/rgeirhos/texture-vs-shape) · [dissent: CNNs are not biased towards texture](https://arxiv.org/pdf/2509.20234) · [shape-texture debiased training](https://arxiv.org/pdf/2010.05981) · [frequency/contrastive shape bias](https://arxiv.org/pdf/2509.11355)
- [AugMix](https://github.com/google-research/augmix) · [CycleGAN/pix2pix](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) · [RL-CycleGAN](https://arxiv.org/pdf/2006.09001)
- [DINOv2](https://github.com/facebookresearch/dinov2) · [DINOv3](https://arxiv.org/pdf/2508.10104) · [FastDINOv2](https://arxiv.org/html/2507.03779v1) · [SAM](https://github.com/facebookresearch/segment-anything) · [OVD robustness under distribution shift](https://arxiv.org/pdf/2405.14874) · [Visual state-space model robustness](https://arxiv.org/pdf/2406.09407)
- [Event-based vision resources (UZH-RPG)](https://github.com/uzh-rpg/event-based_vision_resources)

**Tamper and IQA**
- [Comparative study and enhancement of camera tampering detection (arXiv 1608.02385)](https://arxiv.org/pdf/1608.02385) · [Rapid detection of camera tampering (CVIU)](https://www.sciencedirect.com/science/article/abs/pii/S1047320314001473) · [SIFT-based tamper detection](https://www.researchgate.net/publication/261308979_Sift-based_camera_tamper_detection_for_video_surveillance) · [Real-time adaptive camera tamper detection](https://www.researchgate.net/publication/221315328_Real-Time_Adaptive_Camera_Tamper_Detection_for_Video_Surveillance) · [Automated camera sabotage detection](https://www.researchgate.net/publication/325510414_Automated_camera_sabotage_detection_for_enhancing_video_surveillance_systems) · [Occlusion detection for surveillance cameras](https://www.researchgate.net/publication/349528272_An_Algorithm_of_Occlusion_Detection_for_the_Surveillance_Camera) · [Forensic video analytic software](https://arxiv.org/pdf/2401.02960)

**Synthetic data, simulation, sim-to-real**
- [Tobin et al. · Domain Randomization (arXiv 1703.06907)](https://arxiv.org/abs/1703.06907) · [IROS version](https://dl.acm.org/doi/abs/10.1109/IROS.2017.8202133)
- [MOTSynth (arXiv 2108.09518)](https://arxiv.org/abs/2108.09518) · [baselines](https://github.com/dvl-tum/motsynth-baselines) · [JTA-Mods](https://github.com/fabbrimatteo/JTA-Mods) · [MTA-Mod](https://github.com/koehlp/MTA-Mod) · [PieTrack (synthetic training + SFDA)](https://deepai.org/publication/pietrack-an-mot-solution-based-on-synthetic-data-training-and-self-supervised-domain-adaptation)
- [BEDLAM (arXiv 2306.16940)](https://arxiv.org/abs/2306.16940) · [project](https://bedlam.is.tue.mpg.de/)
- [PeopleSansPeople](https://github.com/Unity-Technologies/PeopleSansPeople) · [PSP-HDRI+](https://arxiv.org/pdf/2207.05025) · [Unity Perception (discontinued)](https://github.com/Unity-Technologies/com.unity.perception)
- [MultiviewX](https://github.com/hou-yz/MultiviewX) · [GMVD](https://github.com/jeetv/GMVD) · [Synthehicle](https://github.com/fubel/synthehicle) · [UBnormal](https://github.com/lilygeorgescu/UBnormal) · [CrowdSim2](https://arxiv.org/pdf/2304.05090)
- [UnrealZoo (arXiv 2412.20977)](https://arxiv.org/abs/2412.20977) · [unrealzoo-gym](https://github.com/UnrealZoo/unrealzoo-gym) · [UnrealCV](https://unrealcv.org/) · [CARLA](https://github.com/carla-simulator/carla) · [AirSim](https://github.com/microsoft/AirSim) · [BlenderProc](https://github.com/DLR-RM/BlenderProc) · [Kubric](https://github.com/google-research/kubric) · [Infinigen](https://github.com/princeton-vl/infinigen) · [Infinigen Indoors](https://arxiv.org/pdf/2406.11824)
- [NVIDIA Isaac Sim Replicator Agent](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/replicator_tutorials/tutorial_replicator_agent.html) · [Omniverse Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html) · [NVIDIA Cosmos](https://github.com/NVIDIA/Cosmos)
- [Richter et al. · Enhancing Photorealism Enhancement](https://isl-org.github.io/PhotorealismEnhancement/) · [code](https://github.com/isl-org/PhotorealismEnhancement) · [ResearchGate PDF](https://www.researchgate.net/publication/359927882_Enhancing_Photorealism_Enhancement) · [CARLA2Real](https://arxiv.org/html/2410.18238v2) · [REGEN](https://arxiv.org/pdf/2508.17061) · [Sim2Real GAN domain transfer](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10780866/)
- [Brooks et al. · Unprocessing Images for Learned Raw Denoising](https://github.com/timothybrooks/unprocessing)
- Repo context: [`docs/01_RESEARCH_LANDSCAPE.md`](../01_RESEARCH_LANDSCAPE.md) · [`docs/06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md) · [a CCTV-analytics vendor]((vendor source removed))

---

*Compiled for the a CCTV-analytics vendor internship, September 2026. Quotation discipline as
described in the sourcing note at the top: verify any **[paraphrase]** item against the primary
source before it goes into an external deliverable.*
