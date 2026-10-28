# R03 · Behaviour, Intent and Anomaly Detection from Surveillance Video

**Scope.** Operational definitions used by industry and government; the UK i-LIDS
and US DIVA/ActEV evaluation programmes; the academic video-anomaly-detection
(VAD) literature and its numbers; intent prediction and what is scientifically
defensible; the human-factors problem (false alarms, operator fatigue, alert
design); video-language models and natural-language event search; datasets;
evaluation protocols and their flaws; legal/ethical constraints; open problems.

**Why this document exists.** The product surface we are building a simulator for
is described as *"Behavioural analysis modules detect and classify indicators of
threat or intent, including loitering, tampering, unusual postures or movements,
and aggressive behaviour"* ([a CCTV-analytics vendor]((vendor source removed))).
Every noun in that sentence is a contested term with a different meaning in a
vendor datasheet, a Home Office test protocol, and a CVPR paper. A person with
twenty years in this field is distinguished precisely by knowing which of the
three is being spoken at any given moment. That translation table is the core of
this dossier.

> **Sourcing note — read this first.** Claims below are quoted and linked.
> Quotations were captured through a search-and-extract pipeline against the
> linked sources; the network in this environment blocked direct fetching of
> `npsa.gov.uk`, `arxiv.org`, `openaccess.thecvf.com`, `help.axis.com` and
> `pmc.ncbi.nlm.nih.gov`, so **wording should be re-verified verbatim against
> the primary PDF before any external use or publication**. Where I state
> something from professional knowledge without a retrieved quote, it is marked
> `[unquoted]` or `[lore]`. Nothing in this document is a fabricated quotation;
> where I could not retrieve a number, I say so.

---

## 1. Operational definitions: what the words actually mean

### 1.0 The three dialects

The same behaviour label lives in three incompatible worlds:

| Dialect | Who speaks it | What a "loitering" label means | What "performance" means |
|---|---|---|---|
| **Rule/geometry** | Camera and VMS vendors (Axis, Bosch, Hikvision, Genetec, Avigilon, Milestone) | A tracked object's dwell time inside an operator-drawn polygon exceeds a configured number of seconds | Configuration survives the site: does it alarm on foliage, headlights, rain, spiders |
| **Assurance/test** | UK Home Office i-LIDS, NPSA (ex-CPNI), NIST ActEV | A scenario-defined alarm event in a sequestered corpus, with a temporal tolerance window | Probability of detection at a fixed false-alarm *rate per unit time* |
| **Learned/semantic** | Academia, VLM vendors (BriefCam, viisights, Ambient, Hakimo, Actuate) | A frame or segment scored anomalous, or a class predicted from video | Frame-level AUC / AP on a public benchmark |

customer is writing in, because the acceptance test differs by orders of
magnitude in difficulty. A rule engine that "does loitering" can be
demonstrated in ten minutes and will fail an i-LIDS-style trial; a model with
89% AUC on UCF-Crime has never been asked to survive a wet Tuesday night on a
substation perimeter.

### 1.1 Loitering

**Vendor definition (rule dialect).** Axis states plainly that loitering is
*"when a person or a vehicle remains in a predetermined zone for more than a
certain number of seconds"* ([AXIS Loitering Guard](https://help.axis.com/en-us/axis-loitering-guard) /
[AXIS Perimeter Defender](https://help.axis.com/en-us/axis-perimeter-defender)).
There is **no vendor-standard default threshold** — searching the Axis
documentation confirms that *"the documentation does not specify a fixed minimum
number of seconds for the loitering time-in-area definition… this value is
configurable"* (search extraction against
[help.axis.com](https://help.axis.com/en-us/axis-loitering-guard)). This is the
single most important fact in this section: **the dwell threshold is a customer
policy decision, not a technical constant.** Anyone who tells you "loitering is
60 seconds" is quoting a site, not a standard.

Axis also documents a *separate* and often-confused parameter: an object must be
*"completely visible in the detection zone for at least three seconds to be
detected"* before any rule timer starts
([AXIS Perimeter Defender user manual](https://www.a1securitycameras.com/content/product_documents/13284/axis-um_perimeterdefender_1587516_en_1702-A1.pdf)).
So the effective alarm latency is `track_acquisition + dwell_threshold`, and
forensic reviews that compare an alarm timestamp with a CCTV timecode routinely
"discover" a 3–5 s discrepancy that is simply this.

**Bosch (rule dialect, richer).** Bosch Intelligent Video Analytics exposes
Loitering as a discrete *task* alongside Idle object, Removed object, Tampering,
Crowd detection, Following route, Condition change and Occupancy
([Bosch IVA Pro configuration manual](https://www.networkwebcams.co.uk/content/pdf/bosch/bosch-iva-pro-traffic-user-manual.pdf);
[Bosch: what each task does](https://knowledge.keenfinity-group.com/video-systems/article/what-does-do-each-task-of-video-analytics-bosch-se)).
Crucially Bosch's Loitering is parameterised by **a radius as well as a time** —
the object must remain *within a radius* for a period — which is the correct
model, because a pure dwell-in-polygon test cannot distinguish a person standing
still from a person walking a 40 m beat inside a large zone. `[unquoted:
the radius-plus-time formulation is standard in Bosch IVA and in the "loiter
within R metres for T seconds" literature; verify the parameter names in the
current firmware manual.]`

Bosch's device-capability whitepaper is the document to cite when someone asks
"can the camera do it at the edge?" — capability is per-model and per-firmware
([IVA Capabilities per Device FW 8.90/9.00](https://media.boschsecurity.com/fs/media/pb/media/products_1/video_systems_1/Whitepaper_IVA_CapabilitiesPerDevice_FW900.pdf)).

**Hikvision (rule dialect).** Hikvision's VCA "Intrusion Detection" is in fact a
dwell rule, not a crossing rule: it *"tracks subjects within a specified area and
triggers when a subject has remained within the zone for a pre-defined amount of
time"*, with a *"percentage, which defines the ratio of the in-region part of an
object that can trigger an alarm"*
([Hikvision: How to configure VCA function](https://www.hikvisioneurope.com/eu/portal/portal/Technical%20Materials/24%20How%20To/CCTV/How%20to%20configure%20VCA%20function.pdf)).
That "percentage" parameter is the sleeper: it is the reason the same rule
behaves differently on a wide-angle vs telephoto view of the same zone, because
it is expressed in fractions of the object's bounding box, which changes with
perspective.

**Genetec (rule dialect, scenario-composed).** Genetec's KiwiVision Intrusion
Detector *"helps protect perimeters and generates real-time notifications when
people or vehicles enter critical areas"*, and — this is the interesting part —
*"custom intrusion detection scenarios can define areas with an alarm region,
source region, and transport region"*
([Genetec KiwiVision](https://www.genetec.com/products/unified-security/omnicast/video-analytics);
[KiwiVision custom intrusion scenario](https://techdocs.genetec.com/r/es-MX/Guia-del-usuario-de-KiwiVisionTM-para-Security-Center-5.12.2.0/Escenario-del-detector-de-intrusiones-personalizado-para-KiwiVision-video-analytics)).
The three-region model (where a track must have *come from*, where it must *go*,
where it *alarms*) is the industrial answer to false alarms and is a design
pattern our simulator must be able to express: **ground truth needs the whole
trajectory's zone history, not just the alarm zone occupancy.**

**Avigilon (learned dialect, unsupervised).** Avigilon ships **Unusual Motion
Detection** and **Unusual Activity Detection** — scene-specific learned
normality rather than a drawn rule
([Avigilon UMD docs](https://docs.avigilon.com/bundle/designing-site-for-analytics/page/umd/unusual-motion-detection.htm);
[Avigilon UAD](https://support.avigilon.com/s/article/Video-ACC-Unusual-Activity-Detection?language=en_US)).
UMD is the commercial instance of the academic "one-class / normality model"
family (§3) and inherits its central weakness: it cannot tell you *why*, only
*that*, and its notion of unusual drifts with the scene.

**Behaviour-recognition vendors (semantic dialect).** viisights Wise supports
*"detection of Objects (with attributes like color and location), Actions
(behaviors over time like running or falling), Events (interactions between
objects like fighting), Scene classification, and Attributes, along with
capabilities for violent activity prediction, suspicious behavior recognition,
crowd behavior, and traffic monitoring"*
([viisights technology](https://viisights.com/technology/);
[Wise product page](https://viisights.com/products/wise)).
Note the ontology: **object → action → event → scene**. That four-level ladder is
worth copying; it maps almost exactly onto the `class / type / subtype` taxonomy
already used in [`docs/03_BEHAVIOUR_CATALOG.md`](../03_BEHAVIOUR_CATALOG.md).

BriefCam, by contrast, is explicit that its search is **attribute-based, not
semantic-narrative**: users *"can search and filter objects by men, women,
children, vehicles, and lighting changes using 28 classes and attributes, in
addition to face recognition, license plate recognition, appearance similarity,
color, size, speed, path, direction, and dwell time"*
([Milestone on BriefCam](https://www.milestonesys.com/resources/content/articles/briefcam-video-analytics-software/);
[BriefCam federal capabilities statement](https://www.briefcam.com/wp-content/uploads/2025/06/BriefCam-FederalCapabilitiesStatement-2023-1.pdf)).
"Dwell time" appears in that attribute list — i.e. **BriefCam's loitering is a
post-hoc filter over tracks, not a real-time alarm primitive.** That distinction
(forensic vs real-time) determines whether latency or recall dominates your
acceptance test.

**ONVIF (interop dialect).** Profile M is the standard that makes behaviour
labels portable: it *"standardizes the delivery of AI-generated metadata such as
object detection, classification, and events, making analytics from IP cameras
interoperable across third-party platforms"*, and a client *"can query which
analytics modules the camera runs, including motion, tamper, object detection,
line crossing, loitering, and people counting"*, publishing *"JSON events"* /
*"JSON-formatted events over MQTT"*
([ONVIF Profile M](https://www.onvif.org/profiles/profile-m/);
[ONVIF release announcement](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/);
[ONVIF Analytics Service Specification](https://www.onvif.org/specs/srv/analytics/ONVIF-Analytics-Service-Spec.pdf)).
**Loitering and tampering are named in the ONVIF analytics interface.** That is
the closest thing to an industry-wide behaviour vocabulary, and it is the
schema our simulator's event log should be trivially mappable to.

### 1.2 Camera tampering

Tamper detection is the oldest "behaviour" analytic and the only one that is
essentially solved by classical signal processing — which is why it is a useful
sanity baseline for any new ML pipeline.

**What vendors claim to detect.** Bosch: *"the built-in tamper detection
generates alarms on camera hooding/masking, blinding, defocusing, and
repositioning"*
([Bosch IVA 3.5](https://objects.eanixter.com/PD513616.PDF)). That four-way
taxonomy — **occlusion / blinding / defocus / displacement** — is the industry
standard breakdown and is echoed across the literature: methods are *"designed
to detect video camera tampering events like occlusion, defocus and
displacement"*, including *"malicious actions against the camera like spray
paint, occlusion, and displacement"*
([Unified Camera Tamper Detection Based on Edge and Object Information, Sensors 2015](https://www.mdpi.com/1424-8220/15/5/10315)).

**How it works.** *"Implementation of camera tamper detection uses background
modeling algorithms, histogram analysis, edge comparison, and image brightness
measurement for real-time detection. Features used include edge information,
frame count, foreground objects' coverage area and its static nature"*; the
unified approach uses *"edge change information between current and background
frames as a common feature, while object information is used to prevent
foreground edges from affecting detection and reduce false alarm rates"*, with an
*"edge disappearance rate [that] measures the amount of edge pixels that
disappear from the background frame, with tamper attacks detected if the
difference exceeds an adaptive threshold"*
([MDPI Sensors 2015](https://www.mdpi.com/1424-8220/15/5/10315);
[Real-Time Adaptive Camera Tamper Detection for Video Surveillance](https://www.researchgate.net/publication/221315328_Real-Time_Adaptive_Camera_Tamper_Detection_for_Video_Surveillance);
[Rapid detection of camera tampering and abnormal disturbance, JVCI 2014](https://www.sciencedirect.com/science/article/abs/pii/S1047320314001473)).

**Reported performance.** A representative result: the algorithm *"detected more
than 96 percent of malicious events without false alarms for 13 hours of video
with 350 tampering events from more than 20 different scenes"*
([MDPI Sensors 2015](https://www.mdpi.com/1424-8220/15/5/10315)).
Note the shape of that claim — **PD at zero FA over a stated number of hours and
scenes.** That is the correct way to report a security analytic, and it is how
i-LIDS and ActEV report too (§2). Compare with a frame-AUC number, which cannot
be converted into an operational expectation at all.

almost never adversarial: they are a delivery lorry parked in front of the lens
(occlusion), sunrise through a fence (blinding), a spider web or a rain droplet
on the dome (defocus), and thermal expansion of a pole mast over the diurnal
cycle (displacement). The correct architecture is therefore *tamper + dwell +
schedule + correlate-with-neighbour-camera*, not tamper alone. Our simulator's
`hostile.tamper.camera.{cover,spray,tilt,cut,glare,unplug}` labels should
therefore always be generated alongside benign twins (a lorry, a sunrise, a
maintenance ladder) or the resulting benchmark is meaningless.

### 1.3 Abandoned / unattended object

This is the behaviour with the **most explicit numeric definition** in the whole
field, because PETS2006 and i-LIDS forced the issue.

**The PETS2006 rule.** The luggage *"is declared an un-attended object when the
owner leaves it and disappears, and it is not re-attended within time T = n
seconds"*, and *"T is 30 seconds in the PETS2006 dataset"*; spatially, *"when the
distance between the owner and the luggage is longer than a pre-defined
distance, then an alarm event is triggered"*
([Localized Detection of Abandoned Luggage, EURASIP JASP 2010](https://link.springer.com/article/10.1155/2010/675784/tables/1);
[PETS 2006 data](http://www.cvg.reading.ac.uk/PETS2006/data.html)).
I could **not** retrieve verbatim confirmation of the widely-repeated *3 metre*
threshold from the primary PETS2006 specification — the search explicitly noted
that it *"don't provide explicit confirmation of the 3-metre spatial rule"*. So:
**treat "3 m / 30 s" as the folk formulation and cite the PETS2006 ground-truth
files for the actual numbers.** `[The PETS2006 protocol in fact defines nested
spatial zones around the owner and a warning/alarm escalation; verify against
the dataset's own documentation.]`

**The PETS2006 corpus.** It *"consists of seven scenarios captured from four
different viewpoints (cameras)"* with *"briefcase, suitcase, 25 litre rucksack,
70 litre backpack and sky gear carrier"*, and ground truth *"represents the alarm
time defined in the dataset"*
([PETS 2006](http://www.cvg.reading.ac.uk/PETS2006/data.html);
[EURASIP 2010](https://link.springer.com/article/10.1155/2010/675784/tables/1)).
Four synchronised views of the same event, with a single canonical alarm
timestamp, is exactly the multi-camera ground-truth structure our simulator
emits — PETS2006 is the format to be compatible with for this behaviour.

**The vendor equivalent.** Bosch's *Idle object* task *"generates an alarm event
if an object is detected as idle or left in a certain area (for example, a piece
of luggage without an owner)"*, and its mirror, *Removed object*, *"generates an
alarm event if an object is detected as removed in a certain area (for example,
due to theft)"*
([Bosch: configure idle & removed object](https://knowledge.keenfinity-group.com/video-systems/article/how-to-configure-idle-removed-object-detection-on-)).
Note what is absent: **no vendor idle-object task actually models ownership.** It
models "a blob became static". Owner-association — the part that makes the
alarm *mean* abandonment — is the hard research problem
([Robust Detection of Abandoned Object for Smart Video Surveillance in
Illumination Changes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6928649/);
[Real-Time Deep Learning Method for Abandoned Luggage Detection in Video](https://arxiv.org/pdf/1803.01160)).
Synthetic data has been applied here specifically because real abandonment is
rare: see [Abandoned Luggage Detection with Synthetic Scenario
Generation](https://link.springer.com/chapter/10.1007/978-3-032-13757-9_21) —
direct precedent for this repository's thesis.

### 1.4 Perimeter intrusion, sterile zones and tripwires

**The governing UK doctrine is NPSA's, not a vendor's.** NPSA (the National
Protective Security Authority, formerly CPNI) defines the category: *"Perimeter
Intruder Detection Systems, or PIDS, are used to detect intruders attempting to
gain illegal entry onto or into your site"*, and they *"are deployed at your
perimeter so that a maximum early warning is enabled"* and *"should be deployed
in conjunction with other security measures such as CCTV and Access Controls
Systems"*
([NPSA Perimeter Intrusion Detection (PIDS)](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-pids);
[Guide to PIDS](https://www.npsa.gov.uk/system/files/documents/2c/80/Guide-to-PIDS.pdf)).

Two NPSA statements should be tattooed on the forehead of anyone specifying a
behaviour analytic:

1. **False alarms are assumed, not exceptional.** *"As PIDS are prone to false
   alarms, all alarms need to be verified quickly, before any security response
   is initiated. Alarms are typically verified through the use of CCTV video
   surveillance."*
   ([NPSA PIDS](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-pids))
   The design goal of an analytic in CNI is therefore **not** "don't false
   alarm" but "be verifiable in seconds". That reframes the whole product: what
   matters is the *clip you hand the operator*, not the score.
2. **There is a documented minimum human review cadence.** *"If the perimeter is
   protected by other NPSA assured physical security measures (e.g. PIDS or
   Fencing), each camera image should be actively viewed at least once every
   five minutes."*
   ([NPSA CCTV for CNI Perimeter Security](https://www.npsa.gov.uk/system/files/documents/NPSA%20CCTV%20for%20CNI%20Perimeter.pdf))
   A five-minute revisit interval per camera is the hard arithmetic constraint
   that sets your cameras-per-operator ratio, and it is why "AI reduces
   headcount" claims must be checked against assurance requirements, not just
   against alarm counts.

NPSA also runs the product-assurance machinery: *"NPSA runs various functional
evaluation schemes for perimeter intrusion detection products"*
([PIDS Evaluation Schemes](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-systems-pids-evaluation-schemes)).
Being on an NPSA-assured list, not a benchmark score, is what sells into UK CNI.

**Standards.** The relevant UK/EU standards family for *video* is **IEC/EN 62676**
(video surveillance systems for security applications), whose Part 4 is the
application-guidelines document that gives the DORI pixel-density criteria
([Axis: pixel density based on IEC 62676-4:2014](https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014)).
DORI = *"Detect, Observe, Recognize, and Identify"*, and the canonical numbers
are *"Detection… 25 px/m, Observation at 62.5 px/m, Recognition at 125 px/m, and
Identification at 250 px/m"*, glossed as: *"25 PPM is enough to tell that a
person-sized object is present; 63 PPM lets a trained operator describe gender
and clothing colour; 125 PPM allows a familiar face to be matched; 250 PPM
enables forensic identification of a stranger"*
([DORI explained / EN 62676-4:2025](https://www.backstreet-surveillance.com/cctv-industry-experts/dori-cctv.html);
[Infiniti Electro-Optics DORI whitepaper](https://www.infinitioptics.com/whitepapers/dori-detection-observation-recognition-identification)).

**This matters enormously for behaviour analytics and is almost universally
ignored:** DORI is specified for *human* observers. A pose-based fight detector
needs limb-level resolution, which is nowhere near 25 px/m and arguably beyond
125 px/m. There is no standardised "pixels per metre for posture estimation"
figure — this is a genuine gap our simulator can fill, because we can sweep
pixel height as a controlled variable and produce the missing curve.

Note also the 2025 revision: *"The 2025 revision of IEC 62676-4 expands the older
DORI model into a broader visual-performance framework with seven operational
levels: overview, outline, discern, perceive, characterize, validate, and
scrutinize"*, and *"refines pixel density requirements, accounting for
higher-resolution digital IP cameras while considering factors like compression
and noise"*
([Axis: From DORI to Visual Performance in IEC 62676-4:2025](https://newsroom.axis.com/en-us/blog/iec-62676-4-video-surveillance);
[JVSG on IEC/EN 62676-4:2025](https://www.jvsg.com/iec-62676-4-oodpcvs/)).
**Compression and noise being explicitly in scope in 2025** is direct
vindication of the sensor-model work in
[`docs/06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md).

`[unquoted, but standard practice]` **BS EN 50131** is the intruder-and-hold-up
alarm systems series (grades 1–4, environmental classes) and applies to the
*alarm system* around the video, not to video analytics performance; **BS EN
50132** is the older CCTV series largely superseded by IEC 62676. If a tender
cites EN 50131 for a video analytic, it is a copy-paste error — flag it, and ask
whether they mean EN 50131 grading of the alarm transmission path or IEC 62676-4
operational requirements for the camera. Verify current part numbers before
quoting in a bid.

**Sterile zone** is an i-LIDS term of art (§2) meaning a region where *any*
human presence is by definition an alarm — the easiest possible behaviour
analytic, because normality is "empty". **Tripwire / line crossing** is
directionally-filtered boundary crossing and is, per field testing,
*more* reliable than area intrusion: IPVM's assessment is that *"intrusion
detection is noted as less accurate than line crossing detection"*, and that
low-cost analytics *"perform reliably indoors but struggle in outdoor
conditions"*
([IPVM analytics course](https://ipvm.com/course/analytics-course-on-demand/overview);
[IPVM: Struggling with video analytics on Hikvision NVRs](https://ipvm.com/discussions/struggling-with-video-analytics-on-hikvision-nvrs-member-email)).

### 1.5 The loitering-threshold dilemma, stated properly

IPVM puts the core engineering tension in one sentence: *"When configuring
loitering analytics, making the delay short results in being flooded with false
alerts, while making it long decreases false alerts but may cause missing rare
real incidents"*
([IPVM: Good Loitering Analytics?](https://ipvm.com/discussions/loitering-analytics)).

This is not a tuning inconvenience; it is the field's central structural
problem, and it has a precise form. Let `D(t)` be the survival function of
legitimate dwell times in a zone and `H(t)` that of hostile dwell times. A dwell
threshold `T` yields `FPR = D(T)` and `TPR = H(T)`. **You cannot beat the overlap
of those two distributions by improving the detector or tracker** — only by
adding a feature that is not dwell (orientation, revisit count, gaze target,
identity persistence across cameras, time-of-day context, role/uniform). Every
credible improvement in loitering analytics in the last decade has been an
attack on that overlap, not on the timer. This is exactly what the
`commute_wait`, `smoke_break`, `vendor` and `lost_tourist` **hard negatives** in
[`docs/03_BEHAVIOUR_CATALOG.md`](../03_BEHAVIOUR_CATALOG.md) exist to measure,
and it is why `hard_negative_for: [loiter, tamper]` tagging is the most valuable
single field in our ground truth.

---

## 2. Government evaluation programmes: i-LIDS and DIVA/ActEV

If you learn one thing that separates you from a CVPR-trained engineer, learn
this section. Government evaluation programmes measure **detections per unit
time against a false-alarm rate**, on **sequestered data**, in **operationally
representative conditions**. Academic benchmarks measure **frame-level ranking
quality** on **public data** with **known test sets**. The former predicts field
behaviour; the latter predicts publication.

### 2.1 i-LIDS: what it is and who owns it

i-LIDS is the **Imagery Library for Intelligent Detection Systems** — *"a UK
Government initiative to facilitate development and selection of video analytics
to meet Government requirements for security operations"*, *"developed by the
Centre for Applied Science and Technology (CAST) in partnership with the Centre
for the Protection of National Infrastructure (CPNI)"*
([Imagery Library for Intelligent Detection Systems (i-LIDS): A Standard for
Testing Video Based Detection Systems](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)).

The institutional lineage is a recurring source of confusion in tenders, so
memorise it: **PSDB → HOSDB → CAST** on the science side (the Home Office
Scientific Development Branch became the Centre for Applied Science and
Technology), and **CPNI → NPSA** on the protective-security side (CPNI became
the National Protective Security Authority, hosted by MI5)
([NPSA hostile reconnaissance guidance](https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance),
which states NPSA is *"formerly CPNI"*). DSTL is a separate MOD body and is
*not* the i-LIDS owner, though it funds adjacent work. `[If a requirement cites
"HOSDB i-LIDS approval", it is a pre-2011 document being recycled — check
whether the current NPSA scheme has superseded the reference.]`

### 2.2 The four scenarios

[historical quote; released library has five] *"The i-LIDS project is focused on four scenarios: Abandoned Baggage Detection,
Parked Vehicle Detection, Doorway Surveillance, and Sterile Zone Monitoring.
Each scenario contains a variety of 'alarm' and 'non-alarm' events"*
([i-LIDS standard paper](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)).
Concretely:

- *"The abandoned baggage scenario contains alarm events of unattended bags on
  the platform of an underground station."*
- *"The parked vehicles scenario contains alarm events of suspiciously parked
  vehicles in an urban setting."*
- *"In the case of sterile zone monitoring, analytics systems must detect the
  presence of persons in a restricted area or 'sterile zone'."*
- Doorway surveillance = people entering/exiting a controlled doorway.

There is also a **multiple-camera tracking** scenario in the wider i-LIDS family;
the "i-LIDS MCT" subset is the one the re-identification literature cites, and it
is a different animal from the four event-detection scenarios. `[unquoted —
verify against the current i-LIDS dataset catalogue.]`

**The corpus design is the lesson.** *"The datasets for the event detection
scenarios each contain approximately 24 hours of footage, filmed to represent all
weather conditions, time of day and scene densities expected within the scenario,
and consist of two or three camera views which are further segmented into
shorter video clips of 30 to 60 minutes"*
([i-LIDS standard paper](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)).

Read that again against the academic datasets in §7. **24 hours per scenario, all
weather, all times of day, two or three views, deliberately including non-alarm
events.** UCSD Ped2's entire test set is about 2,010 frames — roughly **67
seconds** at 30 fps. i-LIDS is three orders of magnitude more operationally
representative and nobody in the academic community uses it, largely because
access is controlled. This asymmetry is the single best argument for the
simulator this repository builds: **we can generate i-LIDS-shaped corpora (24 h,
all-weather, multi-view, alarm and non-alarm) at will**, which no public academic
dataset provides.

### 2.3 The i-LIDS scoring protocol — and why it is the right one

The i-LIDS evaluation protocol is recognised in the academic literature as one of
three standard protocols: *"Three evaluation protocols are commonly used:
frame-level (FL), i-LIDS, and edge-level (EL)"*, and the i-LIDS one is defined by
a **temporal tolerance window**:

> *"If no alarm is raised within 10 seconds of the intrusion beginning, a false
> negative (FN) is counted, and following alarms that do not occur within 10
> seconds from the beginning of the intrusion are marked as false positives
> (FP)."*
> — [Perimeter Intrusion Detection by Video Surveillance: A Survey (Sensors 2022)](https://pubmed.ncbi.nlm.nih.gov/35591289/)

That 10-second rule encodes three deep design decisions:

1. **Event-level, not frame-level.** One intrusion = one scoring opportunity. A
   detector that fires on 900 of 1,000 anomalous frames scores identically to one
   that fires on frame 1 only, which is what an operator experiences.
2. **Latency is part of correctness.** A detection at t+11 s is a *miss*, not a
   late hit. Rule engines that need `3 s track acquisition + T s dwell` are thus
   structurally penalised, which is fair: a perimeter alarm that arrives after
   the intruder has crossed is worthless.
3. **Repeat firing is punished.** Extra alarms inside the window are FPs — i.e.
   **alarm de-duplication is a scored feature, not a UI nicety.**

On the *"primary"/"secondary"* classification in the task brief: I could **not**
retrieve a source confirming an i-LIDS "primary/secondary" detection
classification — the search for it explicitly returned *"The search results did
not provide specific information regarding 'primary secondary detection' or
'approval' aspects"*. `[unquoted / to verify]` In my experience the terms in play
are (a) **primary vs secondary detection system** in PIDS doctrine — the PIDS is
primary, CCTV is the secondary/verification layer, consistent with NPSA's
"alarms… verified through the use of CCTV" statement above — and (b) NIST
ActEV's *primary task* designation (§2.4), which is a different usage. **Do not
assert an i-LIDS primary/secondary metric without the current scheme document.**

Similarly, the folk claim that "passing i-LIDS meant detecting N% of events at
fewer than M false alarms per camera per hour" is structurally right but I could
not retrieve the figures. What is safe to say: **i-LIDS-family scoring is
reported as detections at a specified false-alarm rate per camera-hour, on
sequestered footage, per scenario, and it is a pass/fail assurance regime rather
than a leaderboard.** Get the thresholds from NPSA directly before quoting them.

### 2.4 US: DIVA, MEVA and NIST ActEV

*"The National Institute of Standards and Technology (NIST) developed the
Activities in Extended Video (ActEV) evaluations series to support the needs of
the Intelligence Advanced Research Projects Activity (IARPA) Deep Intermodal
Video Analytics (DIVA) Program"*, and the series is *"designed to accelerate the
development of robust, multi-camera, automatic human activity detection systems
for forensic and real-time alerting applications"*
([NIST ActEV](https://actev.nist.gov/);
[NIST: Activities in Extended Videos Evaluation](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)).

**"Multi-camera" and "real-time alerting" in the programme's own charter.** This
is the closest government-scale analogue to the product in scope, and MEVA is the
dataset taxonomy our behaviour catalogue should be alignable with.

**Activity count.** *"The number of target activities in EO (Electro-Optical)
videos is 37 and the target activity for IR (Infrared) videos is 34 as the IR
cameras are only outdoor"*, and *"the activities can be broadly classified as,
person/multi-person activities, person object interaction, vehicle activities,
person facility interaction, and person vehicle interaction"*
([2020 Sequestered Data Evaluation for Known Activities in Extended Video, WACVW 2021](https://openaccess.thecvf.com/content/WACV2021W/HADCV/papers/Godil_2020_Sequestered_Data_Evaluation_for_Known_Activities_in_Extended_Video_WACVW_2021_paper.pdf)).

- **The EO/IR split (37 vs 34) is a hard-won detail:** three activities are
  indoor-only, and IR cameras were outdoor-only. Any claim of "sensor-agnostic
  behaviour analytics" should be met by asking which activities were dropped.
- **The five-way grouping** (person / person-object / vehicle / person-facility /
  person-vehicle) is a better top-level ontology than "normal/suspicious/hostile"
  because it is defined by *what entities participate*, which is observable,
  rather than by *intent*, which is not. Our catalogue's class axis
  (normal/suspicious/hostile) should be kept **orthogonal** to a MEVA-style
  participant-structure axis, not conflated with it.

**Metrics.** *"For both the AOD (primary) and AD tasks, the submitted results are
measured by Probability of Missed Detection (Pmiss) at a Rate of Fixed False
Alarm (RateFA) of 0.1 (Pmiss@TFA). Additionally, the performance metric for the
leaderboard ranking is the partial, normalized Area Under the Detection Error
Tradeoff (DET) curve (nAUDC)"*
([WACVW 2021 ActEV summary](https://openaccess.thecvf.com/content/WACV2021W/HADCV/papers/Godil_2020_Sequestered_Data_Evaluation_for_Known_Activities_in_Extended_Video_WACVW_2021_paper.pdf);
[TREC'24 ActEV Self-Reported Leaderboard](https://actev.nist.gov/srl)).

Decode this, because it is the most operationally honest metric in the field:

- **`RateFA = 0.1`** means **0.1 false alarms per minute = 6 per camera-hour**.
  That is the *fixed operating point* at which detection is measured. Compare
  with a frame-AUC number, which averages over operating points nobody would
  deploy.
- **`Pmiss@TFA`** is therefore "what fraction of real activities do you miss when
  you are allowed 6 nuisance alarms per camera-hour?" — a question an operations
  manager can actually act on.
- **`nAUDC`** is a partial area under the **Detection Error Tradeoff** curve
  (Pmiss vs time-based FA rate, typically log-scaled), truncated to the
  low-false-alarm region. Lower is better, unlike AUC. **A DET curve is the right
  plot for any behaviour analytic**; ROC in frame space is not.
- The **AOD** (activity-object detection) task being "primary" — this is the
  ActEV usage of "primary" and it means *spatially localising the objects
  involved*, not just temporally detecting the activity. That is the
  explainability requirement in disguise (§5.5), and it is why AOD is primary:
  an alert an operator cannot see the subject of is not actionable.

Reference systems in this programme are worth knowing by name for credibility:
**Argus++** is the widely-cited real-time ActEV system, described as *"Robust
Real-time Activity Detection for Unconstrained Video Streams with Overlapping
Cube Proposals"*
([Argus++](https://arxiv.org/pdf/2201.05290)); and the broader "fine-grained
activities of people worldwide" work sits in the same programme lineage
([Fine-grained Activities of People Worldwide](https://arxiv.org/pdf/2207.05182)).
TRECVID's own overview papers are the place to find the year-on-year task
definitions and participant counts
([TRECVID 2020 overview](https://arxiv.org/pdf/2104.13473);
[TRECVID 2022 overview](https://arxiv.org/pdf/2306.13118)).

**On TRECVID SED and VIRAT** `[unquoted — I exhausted my search budget before
confirming]`: TRECVID's Surveillance Event Detection task ran from 2008 and used
**i-LIDS multi-camera airport footage**, with event classes including
`PersonRuns`, `ObjectPut`, `CellToEar`, `Embrace`, `PeopleMeet`, `PeopleSplitUp`,
`Pointing`, and was scored with NIST's **DCR** (Detection Cost Rate — a weighted
combination of miss probability and false-alarm rate per unit time, again a
*rate*-based cost). Performance was famously poor: minimum DCR values near or
above 1.0 for several classes, meaning systems were no better than not
detecting at all. **VIRAT** (ground and aerial) preceded MEVA with 23 event types
in the ground release. Verify both against the TRECVID SED overview papers and
the VIRAT paper before citing numbers — the DCR>1 result is the single most
useful "the field is harder than it looks" citation available, so it is worth
getting exactly right.

### 2.5 The lesson to carry into our simulator's evaluation harness

Our [`docs/07_EVALUATION_AND_ALGO_SANDBOX.md`](../07_EVALUATION_AND_ALGO_SANDBOX.md)
should therefore report behaviour detection as:

1. **Event-level**, with an explicit temporal tolerance (default 10 s, i-LIDS
   convention, configurable), and de-duplication penalised.
2. **Pmiss at fixed FA-per-camera-hour**, with `RateFA = 0.1/min` as a headline
   operating point for ActEV comparability, plus a **DET curve** and **nAUDC**.
3. Stratified by the **difficulty score** already specified in the behaviour
   catalogue (visibility, pixel height, occlusion, lighting) — this is what
   turns a single number into an engineering diagnosis.
4. With frame-level AUC reported **only** as a secondary, clearly-labelled
   number for academic comparability, accompanied by the caveats in §8.

---

## 3. Academic anomaly detection: taxonomy, datasets, numbers

### 3.1 The taxonomy, and why it exists

The literature splits by **what supervision is available**, which in practice is
a split by **what data you could plausibly collect**:

| Family | Training data | Core assumption | Failure mode |
|---|---|---|---|
| **Reconstruction-based** (autoencoders, memory-augmented AE) | Normal frames only | The model reconstructs normal well and anomalies badly | Autoencoders generalise too well — they reconstruct unseen anomalies fine |
| **Prediction-based** (future-frame prediction) | Normal video only | Anomalies are unpredictable | Motion-heavy but normal events (running child) score anomalous |
| **One-class / density** (SVDD, normalizing flows, Gaussian on features) | Normal features | Normality is a compact region | Depends wholly on the feature extractor's inductive bias |
| **Weakly-supervised MIL** | Video-level labels (this video contains an anomaly *somewhere*) | Top-scoring snippets in a positive bag are anomalous | Learns scene/background shortcuts (§8) |
| **Fully-supervised / open-set** (UBnormal) | Pixel-level anomaly labels at train time, disjoint anomaly types at test | You can supervise on *some* anomaly types and generalise | Only possible with synthetic data |
| **Skeleton/pose-based** | Normal pose sequences | Anomaly is in the body, not the pixels | Fails when the anomaly is an object, a vehicle, or a scene-context violation |
| **VLM / zero-shot & training-free** | None (frozen LLM/VLM) | Anomaly is describable in language | Hallucination; no calibrated score; cost/latency |

The field's foundational weakly-supervised paper is Sultani, Chen and Shah,
*Real-world Anomaly Detection in Surveillance Videos* (CVPR 2018), which
introduced both the **deep MIL ranking loss** and **UCF-Crime**: *"The authors
trained the anomaly detection model using the proposed deep MIL (Multiple
Instance Learning) ranking loss, using both positive (anomalous) and negative
(normal) bags"*
([CVPR 2018 paper](https://openaccess.thecvf.com/content_cvpr_2018/papers/Sultani_Real-World_Anomaly_Detection_CVPR_2018_paper.pdf);
[UCF CRCV project page](https://www.crcv.ucf.edu/research/real-world-anomaly-detection-in-surveillance-videos/)).

**UCF-Crime.** *"1,900 videos that encompass 13 distinct anomalous event
categories, recorded via indoor and outdoor CCTV cameras under varied lighting
conditions"*; the classes are *"Abuse, Arrest, Arson, Assault, Road Accident,
Burglary, Explosion, Fighting, Robbery, Shooting, Stealing, Shoplifting, and
Vandalism"*
([UCF-Crime overview](https://www.emergentmind.com/topics/ucf-crime-dataset);
[CRCV](https://www.crcv.ucf.edu/projects/real-world/)). I could not retrieve
verbatim confirmation of the paper's headline **75.41% AUC** for its own method
nor the 128 h total duration — search noted *"I did not find the specific AUC
score of 75.41 mentioned in the search results"*. `[Treat 75.41% AUC and ~128
hours as widely-repeated figures to verify in the PDF's Table 3.]` `[audit 2026-09-26: both confirmed in arXiv 1801.04264 — "75.41" and "128 hours"]`

The dataset's characterisation in later work is worth quoting because it explains
why the benchmark is hard in a way that is *not* representative of CCTV
operations: it is *"characterized by long video durations, sparse anomaly
segments, and complex backgrounds"* and is compiled largely from **YouTube/web
footage**, not from a deployed camera estate
([UCF-Crime overview](https://www.emergentmind.com/topics/ucf-crime-dataset)).
That provenance is the root of the scene-bias problem in §8.

### 3.2 The numbers: UCF-Crime frame-AUC, 2018 → 2026

This is the table people quote at you in meetings. Know it, and know what it does
*not* mean.

| Method | Year | Supervision | UCF-Crime frame **AUC** (not XD-Violence AP) |
|---|---|---|---|
| Sultani et al. (deep MIL) | 2018 | Weak (video-level) | 75.41% (confirmed in paper PDF) `[audit 2026-09-26]` |
| **RTFM** | 2021 | Weak | **84.30%** (I3D; 83.30 was a secondary-source typo) `[audit 2026-09-26]` |
| **UR-DMU** | 2023 | Weak | **86.97%** (I3D; XD-Violence 81.66 AP) `[audit R3 2026-09-26]` |
| **MGFN** | 2023 | Weak | **86.98%** (I3D-RGB; XD-Violence 80.11 AP) `[audit R3 2026-09-26]` |
| **VadCLIP** | 2024 | Weak + CLIP language | **88.02%** |
| **LAVAD** | 2024 | Training-free LLM/VLM | **80.28%** (XD-Violence: 62.01 AP / 85.36 AUC) `[audit R3 2026-09-26]` |
| **Holmes-VAU** | 2025 | MLLM, multi-granularity | **88.96%** (XD-Violence: 87.68 AP) `[audit R3 2026-09-26]` |
| **HiProbe-VAD** (tuned) | 2025 | MLLM probing | **88.91%** |
| **ASK-HINT** | 2025 | Training-free MLLM | **89.83%** (frozen Qwen2.5-VL-7B; XD-Violence 90.31 AUC) `[audit R3 2026-09-26]` |

Every value in this column is **UCF-Crime frame AUC**, checked against each paper's own table in audit round 3 (`39_AUDIT_ROUND3.md`). XD-Violence is scored in **AP** and must never be mixed into this column.

Quoted: *"traditional approaches like RTFM achieve 83.30% AUC [sic — RTFM paper reports 84.30; audit 2026-09-26], UR-DMU reaches
86.97%, and MGFN achieves 86.98%"*; *"VadCLIP achieves 88.02% AUC, while
Holmes-VAU achieves an AUC of 88.96% on UCF-Crime, significantly outperforming
prior state-of-the-art methods"*; *"LAVAD achieves 80.28% AUC, while HiProbe-VAD
(Tuned) reaches 88.91%"*; *"ASK-HINT (a training-free MLLM method) achieves 89.83%
AUC, representing the current state-of-the-art performance on UCF-Crime as of
late 2025"*
([Holmes-VAU, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Zhang_Holmes-VAU_Towards_Long-term_Video_Anomaly_Understanding_at_Any_Granularity_CVPR_2025_paper.pdf);
[Holmes-VAU arXiv](https://arxiv.org/pdf/2412.06171);
[Unlocking Vision-Language Models for VAD via Fine-Grained Prompting](https://arxiv.org/html/2510.02155v1)).


1. **Seven years of work bought ~14 AUC points**, and the last four years bought
   about three. The benchmark is saturating, which usually means the remaining
   error is dataset artefact rather than modelling deficiency (§8).
2. **Training-free MLLM methods now beat seven years of supervised engineering.**
   ASK-HINT at 89.83% with no training is either a remarkable result or a sign
   that UCF-Crime is solvable from single-frame semantics ("this frame contains a
   fire/gun/crowd") without any temporal reasoning. Both readings are bad news
   for the benchmark's validity as a proxy for CCTV.
3. **None of these numbers is a false-alarm rate.** A frame-AUC of 89.8% is
   compatible with alarm rates that would bury a control room. To convert, you
   need the ROC's low-FPR region: at 1% FPR on a 24/7 camera you still emit
   **~14.4 minutes of alarmed video per camera per day**. Nobody reports this.
4. **The comparison is not apples-to-apples in supervision.** Weakly supervised
   methods saw UCF-Crime's training videos; training-free MLLMs saw the internet,
   which almost certainly includes UCF-Crime's source YouTube videos. Contamination
   in the training-free column is essentially unauditable. `[lore, but I would
   raise it in any technical review.]`

### 3.3 XD-Violence: the audio-visual benchmark

*"The XD-Violence dataset contains 4754 untrimmed films with video-level labels
in the training set and frame-level labels in the testing set, for a total
runtime of nearly 217 hours"*, *"compiled from real-world movies, web videos,
sport streaming, security cameras, and CCTVs"*, and evaluated with **Average
Precision**: *"Average Precision (AP) metric is used for evaluation following
previous works"*
([Not only Look, But Also Listen, ECCV 2020](https://link.springer.com/chapter/10.1007/978-3-030-58577-8_20);
[Learning Weakly Supervised Audio-Visual Violence Detection in Hyperbolic Space](https://arxiv.org/pdf/2305.18797)).

Reported SOTA-class numbers (85.67% AP confirmed, Table 1 of 2305.18797, audio+visual, +2.27 over MACIL-SD 83.40 `[audit R3 2026-09-26]`): *"one method achieves 85.67% AP on the XD-Violence
benchmark, outperforming state-of-the-art methods by a sizable margin"*, and
relative gains of *"a minimum of 4.01% improvement"* over unimodal weakly
supervised methods and *"a substantial improvement of 2.27%"* over MACIL-SD
([Hyperbolic-space AVVD](https://arxiv.org/pdf/2305.18797);
[MACIL-SD](https://arxiv.org/pdf/2207.05500);
[Aligning First, Then Fusing](https://arxiv.org/html/2501.07496v2)).

**Two professional cautions.** (a) **AP, not AUC** — XD-Violence uses AP because
the positive class is rare, which is the *correct* choice and should be the
default for our harness too. (b) **The audio channel is a movie artefact.**
XD-Violence includes films; film audio contains scored music and foley designed
to signal violence. Audio-visual gains on XD-Violence do not transfer to CCTV,
where most cameras have no usable audio and where recording audio is a legal
problem in the UK (§9 — the ICO explicitly flags audio-recording cameras as a
high-risk example).

### 3.4 The classic scene-level benchmarks (and their true size)

| Dataset | Train | Test | Resolution | Scenes | Anomalies |
|---|---|---|---|---|---|
| **UCSD Ped2** | 2,550 frames (16 videos) | 2,010 frames (12 videos), 12 abnormal events | 240×360 | 1 | bicycles, skateboarders, wheelchairs on a walkway |
| **CUHK Avenue** | 15,328 frames (16 videos) | 10,622 frames (21 videos), 47 abnormal events | 360×640 | 1 | throwing objects, loitering, running |
| **ShanghaiTech** | 274,515 frames (330 videos) | 42,883 frames (107 videos), 130 abnormal events | 480×856 | **13** | + brawling, chasing, snatching |

Quoted: *"UCSD Ped2 comprises 2550 training frames and 2010 test frames… 16
training videos and 12 testing videos with 12 abnormal events… All the anomalous
events are caused due to vehicles such as bicycles, skateboarders and
wheelchairs crossing pedestrian areas"*; *"The Avenue dataset contains 15328
frames for training and 10622 frames for testing… 47 abnormal events captured in
CUHK campus avenue… The anomalous behaviour is represented by people throwing
objects, loitering and running"*; *"The ShanghaiTech dataset includes 13
different scenes… 330 training videos and 107 test videos… 274,515 normal
training frames… 42,883 testing frames in 107 videos with 130 complex abnormal
events… interpersonal interactions such as brawling, chasing, and snatching"*
([An Attribute-based Method for Video Anomaly Detection](https://arxiv.org/html/2212.00789v2);
[Video Anomaly Detection by Estimating Likelihood of Representations](https://arxiv.org/pdf/2012.01468);
[Hierarchical Semantic Contrast for Scene-aware VAD](https://arxiv.org/pdf/2303.13051)).

**Say this out loud in a meeting and watch the room change:** the entire UCSD
Ped2 test set is **2,010 frames — about 67 seconds of video — containing 12
events**, and papers report AUC on it to two decimal places. Avenue's anomalies
include *"loitering"* as a single visual event class, which has nothing to do
with the dwell-threshold problem in §1.5. **These datasets are unit tests, not
field trials.** i-LIDS gave 24 hours per scenario, in all weathers, in 2006.

### 3.5 Open-set and synthetic: UBnormal

UBnormal is the most important dataset for this repository because it is the
existence proof for our whole approach: *"multiple virtual scenes generated in
Cinema4D using virtual animated characters and objects placed in real-world
backgrounds"*, *"543 clips (236,902 frames)… across 29 virtual scenes, with
pixel-level target annotations"*, with scenes representing *"street scenes, train
stations, office rooms, among others"*
([UBnormal, CVPR 2022](https://arxiv.org/abs/2111.08644);
[UBnormal HTML](https://arxiv.org/html/2111.08644v3);
[UBnormal repo](https://github.com/lilygeorgescu/UBnormal)).

The claim that matters:

> *"Unlike existing datasets, UBnormal introduces abnormal events annotated at
> the pixel level at training time, enabling the use of fully-supervised learning
> methods for abnormal event detection, while preserving the open-set formulation
> by including disjoint sets of anomaly types in training and test collections."*
> — [UBnormal](https://arxiv.org/html/2111.08644v3)

Two things follow directly for our design:

1. **Synthetic data is the only way to get pixel-level anomaly supervision at
   scale** — you cannot ask a real person to be stabbed on cue with a
   segmentation mask. Our simulator produces exactly this, plus multi-camera and
   3D world-space truth, which UBnormal does not.
2. **The open-set protocol (disjoint anomaly types train/test) is the correct
   evaluation design and we should adopt it verbatim.** It is the only protocol
   that measures what a customer actually buys: performance on the attack nobody
   scripted. Our anomaly injector should therefore support a declared
   `train_types` / `test_types` partition as a first-class config concept.

### 3.6 NWPU Campus: scene-dependent anomaly and *anticipation*

*"The NWPU Campus dataset contains 43 scenes, 28 classes of abnormal events, and
16 hours of videos. It is the largest semi-supervised VAD dataset with the
largest number of scenes and classes of anomalies, the longest duration, and the
only one considering scene-dependent anomaly"*; it is *"also the first dataset
proposed for video anomaly anticipation"*; *"305 training videos and 242 testing
videos"*; and *"the anomalies encompass various categories such as single-person
anomalies, interaction anomalies, group anomalies, scene-dependent anomalies,
location anomalies, appearance anomalies, and trajectory anomalies"*
([A New Comprehensive Benchmark for Semi-supervised VAD and Anticipation, CVPR 2023](https://openaccess.thecvf.com/content/CVPR2023/papers/Cao_A_New_Comprehensive_Benchmark_for_Semi-Supervised_Video_Anomaly_Detection_and_CVPR_2023_paper.pdf);
[arXiv](https://arxiv.org/abs/2305.13611); [project site](https://campusvad.github.io)).

**"Scene-dependent anomaly" is the concept the commercial world lives in and the
academic world discovered late.** Cycling is normal on the path and abnormal in
the lobby; a man in hi-vis kneeling at a cabinet is maintenance at 10:00 and
tamper at 03:00. Our behaviour catalogue already encodes this via zones, roles
and `suspicious.temporal.afterhours` — NWPU Campus is the citation that makes it
respectable. And its **anticipation** task (predict the anomaly before it
happens) is the honest academic framing of "intent", far better than the
pseudo-scientific framings in §4.

### 3.7 Skeleton / pose-based anomaly detection

This family matters to us because it is the only one that directly addresses
*"unusual postures or movements"* as the product brief phrases it, and because it
is the family a simulator can supervise perfectly (we emit ground-truth
keypoints).

- **GEPC** (Graph Embedded Pose Clustering): *"GEPC achieves AUC scores of 76.1
  on ShanghaiTech and 52.0 on UBnormal"*.
- **STG-NF** (Spatio-Temporal Graph Normalizing Flows): *"a normalizing flows
  model that can handle training data of only normal examples as well as
  supervised datasets with labeled normal and abnormal examples, reporting
  state-of-the-art results on the unsupervised ShanghaiTech dataset and the
  recent supervised UBnormal dataset"*
  ([STG-NF project page](https://orhir.github.io/STG_NF/);
  [Normalizing Flows for Human Pose Anomaly Detection](https://arxiv.org/pdf/2211.10946)).
- **MoCoDAD** (Multimodal Motion Conditioned Diffusion, ICCV 2023): *"MoCoDAD
  achieves an AUC of 68.3 on the full UBnormal dataset"*
  ([repo](https://github.com/aleflabo/MoCoDAD);
  [paper](https://arxiv.org/html/2307.07205v3);
  [journal version](https://www.sciencedirect.com/science/article/pii/S0031320324005685)).
- Generalisation is the live problem: see *Action Hints: Semantic Typicality and
  Context Uniqueness for Generalizable Skeleton-based Video Anomaly Detection*
  ([arXiv 2509.11058](https://arxiv.org/html/2509.11058)) and
  *Human Kinematics-inspired Skeleton-based VAD* ([arXiv 2309.15662](https://arxiv.org/pdf/2309.15662)).

**Read the 52.0 on UBnormal carefully: that is barely above chance (50.0).**
GEPC, a respected method, is effectively random on open-set synthetic anomalies.
MoCoDAD's 68.3 is the state of the art there and still far from usable. **Pose
anomaly detection does not currently generalise to unseen anomaly types.** That
is the single most useful number in this document for calibrating expectations
about "unusual posture" modules, and it is why our simulator must be able to
generate the *near-miss* postures (kneeling maintenance, tying a shoelace,
crouching to a child, picking up a dropped phone) that these methods confuse
with tampering and collapse.

**Why skeletons anyway?** Privacy and bandwidth: pose is a low-dimensional,
pseudonymised representation that survives ICO scrutiny better than raw video
(§9), runs at the edge, and is invariant to clothing and illumination. The
trade-off is total blindness to object-centric anomalies (bags, weapons,
vehicles) and to scene context.

### 3.8 Violence / aggression detection

**RWF-2000** is the reference CCTV-sourced benchmark: *"2000 videos from various
sources of CCTV cameras, with 1000 violent videos and 1000 non-violent videos,
with all videos being five seconds long and filmed at 30 fps"*, *"captured by
surveillance cameras from real-world scenes collected from YouTube"*, with *"an
80%-20% predefined train-test split which has been thoroughly checked for data
leakage between the splits"*, and it *"depicts a wide range of indoor and outdoor
settings, including streets, different athletic event sites, different rooms in
houses, and music performance stages, as well as various severe weather
conditions"*
([RWF-2000](https://arxiv.org/pdf/1911.05913);
[Semantic Scholar entry](https://www.semanticscholar.org/paper/RWF-2000:-An-Open-Large-Scale-Video-Database-for-Cheng-Cai/c9191d475b38c39a77551ff372e294d60ad262f9)).

**Hockey Fight** is the historic benchmark and its flaw is explicit: *"there are
1,000 clips captured in hockey games of the National Hockey League, though one of
its disadvantages is the lack of diversity because all the videos are captured in
a single scene"*
([A dataset for automatic violence detection in videos](https://pmc.ncbi.nlm.nih.gov/articles/PMC7725718/)).

**The numbers tell the whole story of the sub-field:**
*"ConvLSTM achieved 77.00% accuracy, X3D achieved 84.75%, and I3D achieved 83.40%
on the RWF-2000 dataset"*, whereas *"Violence 4D attains accuracy rates of 100%,
97.29%, and 100% in Hockey Fight, Crowd violence, and Movie datasets
respectively"*
([Exploring Personalized Federated Learning Architectures for Violence Detection](https://arxiv.org/pdf/2504.00857);
[Violence 4D, IET Computer Vision 2023](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/cvi2.12162);
[CUE-Net](https://arxiv.org/pdf/2404.18952);
[Two-stream Multi-dimensional ConvNet for Real-time Violence Detection](https://arxiv.org/pdf/2211.04255)).

**100% on Hockey Fight and ~85% on real CCTV, for the same task.** Any vendor
quoting a violence-detection accuracy above 95% is quoting Hockey Fight or Movies
and should be asked, politely, for RWF-2000 with a confusion matrix. Also note
that RWF-2000 clips are **five seconds long and pre-trimmed** — the real task
(finding 5 s of fight in 24 h of continuous multi-camera video, in real time,
without alarming on a hug, a rugby tackle, a shoulder-barge in a crowd, or
children play-fighting) is not measured by any public benchmark. That gap is the
single clearest product opportunity for a simulator with hard negatives:
`meet_and_greet`, `child_play`, `argument`, `crowd_form` in our catalogue are
precisely the confusers.

### 3.9 Falls and "person down"

**Datasets are small and clinical.** *"The UR Fall Detection Dataset… collects 60
depth video sequences, color video sequences and acceleration data sequences
through 2 Microsoft Kinect cameras and 1 wearable acceleration sensor"*; *"The
Le2i dataset contains 250 videos, of which 192 contain falls and 57 contain
everyday activities, showing the main difficulties an elderly person might
encounter in an enclosed environment"*
([Computer-Aided Fall Recognition, arXiv 2408.12211](https://arxiv.org/html/2408.12211v1);
[Deep Learning for CV-based Activity Recognition and Fall Detection of the
Elderly: a Systematic Review](https://arxiv.org/pdf/2401.11790)).

**Reported accuracies are near-perfect and near-meaningless for CCTV:** *"a fall
detection algorithm based on global and local feature extraction achieved
accuracies of 99.55% and 99.75% when tested with UP-Fall Detection Dataset and
Le2i Fall Detection Dataset respectively"*, while a more honest per-class
breakdown from an ensemble YOLO/DETR study reports *"perfect precision of 100%
for the 'Fall' class, with sensitivity for falls at 86.67%"*
([Fall detection algorithm based on global and local feature extraction, Measurement 2024](https://www.sciencedirect.com/science/article/abs/pii/S016786552400206X);
[An adaptive fall detection system based on ensemble learning, Sci Rep 2025](https://www.nature.com/articles/s41598-025-97634-8);
[Three-stream ST-GCN, Sci Rep 2025](https://www.nature.com/articles/s41598-025-95508-7)).

**86.67% sensitivity with 100% precision on a staged indoor dataset** is the real
state of the art, and it is achieved with a frontal, unoccluded, well-lit, single
actor 3 m from the lens. In a station concourse at 25 px/m, with a crowd closing
over the casualty within two seconds, the problem is different in kind. Note also
that falls are the behaviour where **false negatives cost lives and false
positives cost almost nothing** — the *only* behaviour in the catalogue where the
operating point should be pushed hard toward recall. Almost every other
behaviour's economics run the other way. `[lore]`

### 3.10 Crowd anomaly

The canonical dataset is UMN: *"11 sequences filmed in 3 different locations, with
each sequence beginning with a period of normal passive behaviour before a panic
event/anomaly occurs towards the end"*, *"one indoors and two outdoors"*, where
*"walking is normal, but running is considered abnormal"*
([Holistic Features For Real-Time Crowd Behaviour Anomaly Detection](https://arxiv.org/pdf/1606.05310);
[Abnormal Crowd Behavior Detection using Social Force Model, CVPR 2009](http://gamma.cs.unc.edu/LARGE/papers/abnormal_behavior_detection.pdf)).

The classical method is the **Social Force Model** applied to optical flow:
*"Research in sociology and behavioral sciences provide mathematical models of
pedestrian behavior patterns such as Social Force Model"*, evaluated on *"a
publicly available dataset from University of Minnesota for escape panic
scenarios and a challenging dataset of crowd videos taken from the web"*
([CRCV Abnormal Crowd project](https://www.crcv.ucf.edu/projects/Abnormal_Crowd/)).

This is a pleasing closed loop for our repository: **the same social-force
formalism that the planner layer in
[`docs/01_RESEARCH_LANDSCAPE.md`](../01_RESEARCH_LANDSCAPE.md) uses to *generate*
crowds is the formalism the 2009 detector uses to *detect* anomalies in them.** We
can therefore create anomalies that are, by construction, exactly at the boundary
of detectability — and we should be suspicious of any evaluation where the
generator and detector share a model. Good surveys for the taxonomy:
[Taxonomy of Anomaly Detection Techniques in Crowd Scenes](https://pmc.ncbi.nlm.nih.gov/articles/PMC9415874/),
[Deep crowd anomaly detection: state-of-the-art, challenges, and future research
directions](https://link.springer.com/article/10.1007/s10462-024-11092-8), and
texture-based approaches such as
[GLCM-based crowd violence detection](https://arxiv.org/pdf/1605.05106) and
[repulsive-force sparse reconstruction](https://arxiv.org/pdf/1808.06749).

`[unquoted]` "Walking normal, running abnormal" also exposes the whole
sub-field's weakness: UMN anomalies are **global motion-energy spikes**, and a
detector that simply thresholds mean optical-flow magnitude scores near-perfectly.
Most pre-2015 crowd-anomaly AUCs on UMN should be read as "my optical flow works".

### 3.11 Trajectory-based anomaly

`[unquoted — search budget exhausted before I could source this section; treat as
professional summary and verify each claim]` The trajectory family models
normality in **path space** rather than pixel space: cluster historical tracks
per scene, flag tracks with low likelihood under the mixture (counter-flow, loops,
fence-following, entry from a non-entrance). Modern versions borrow from the
pedestrian-forecasting literature (Social-LSTM, **Social-GAN**, Trajectron++) and
score anomaly as forecast error or as low likelihood under a generative
trajectory model; **TrajREC** and similar recent works reconstruct/forecast
skeleton trajectories for anomaly scoring. Trajectory methods are the most
*operationally* useful family because they are interpretable (you can draw the
anomalous path for the operator), cheap, privacy-friendly, and they map directly
onto the zone/route semantics real sites already have. Their weakness is that they
need a long, clean history per camera and break when the camera moves (PTZ) or
the scene's usage changes (roadworks, an event). Our simulator's world-space 3D
tracks and camera-topology truth make this family trivially trainable and are
arguably the best short-term modelling target for the project.

The relevant survey to anchor all of §3 is
[Video Anomaly Detection in 10 Years: A Survey and Outlook](https://arxiv.org/pdf/2405.19387),
with [Divide and Conquer in Video Anomaly Detection](https://arxiv.org/pdf/2309.14622),
[A Survey on Deep Learning Techniques for Video Anomaly Detection](https://arxiv.org/pdf/2009.14146),
[Networking Systems for Video Anomaly Detection: A Tutorial and Survey](https://github.com/fdjingliu/nsvad),
and [Unveiling the Unseen: Explainable Anomaly Detection in Images and Videos](https://arxiv.org/pdf/2302.06670)
as complements; [awesome-video-anomaly-detection](https://github.com/fjchange/awesome-video-anomaly-detection)
is the maintained leaderboard collection.

---

## 4. Intent: what is defensible and what is not

### 4.1 The only well-posed intent problem in computer vision

Pedestrian crossing-intent prediction is the field's one rigorous intent task,
because the intent is **operationalised as a future observable act** ("will this
person be in the road within N frames?"), so it can be labelled without mind
reading. The benchmarks are **JAAD** and **PIE**, standardised by
[Kotseruba et al., *Benchmark for Evaluating Pedestrian Action Prediction*, WACV 2021](https://openaccess.thecvf.com/content/WACV2021/papers/Kotseruba_Benchmark_for_Evaluating_Pedestrian_Action_Prediction_WACV_2021_paper.pdf).

Current numbers: on **PIE**, *"TCL yields the highest AUC (0.88), F1 score (0.92),
and Recall (0.96)"*; on **JAAD-all**, *"TCL achieves top-tier performance with an
AUC of 0.92"* and *"ACIT achieves the highest accuracy of 89%"*; but on the hard
behavioural subset **JAAD-beh**, *"ACIT achieves the highest accuracy and F1 score
of 70% and 79%, respectively, with the highest AUC and recall reaching 62% and
93%"*
([Temporal-contextual Event Learning (TCL)](https://arxiv.org/pdf/2504.06292);
[ACIT](https://arxiv.org/pdf/2511.20020);
[Coupling Intent and Action](https://arxiv.org/pdf/2105.04133);
[Zero-shot pedestrian intention prediction](https://arxiv.org/pdf/2507.21161)).

**The 0.92 → 0.62 AUC collapse from JAAD-all to JAAD-beh is the most instructive
number in intent prediction.** JAAD-all includes the many pedestrians who
obviously will not cross (standing at a bus stop, walking parallel to the road),
so a model that learns "is this person near a kerb and facing it" scores 0.92.
JAAD-beh keeps only the genuinely ambiguous cases and performance falls to barely
better than chance. **Every intent claim in security analytics has this structure:
the headline number is dominated by easy negatives.** When a vendor says "we
predict intent with 90% accuracy", the correct question is: *on what base rate,
and with the easy negatives removed?*

### 4.2 Hostile reconnaissance: the defensible doctrine

UK doctrine is unusually careful and is the right vocabulary to adopt. NPSA
defines hostile reconnaissance as:

> *"Purposeful observation with the intention of collecting information to inform
> the planning of a hostile act against a specific target."*
> — [NPSA Hostile Reconnaissance](https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance)

and deterrence as:

> *"The intelligent, co-ordinated promotion of protective security provision to
> the hostile that results in the perception and/or assessment that the
> reconnaissance or the attack itself will fail."*
> — [NPSA Disrupting Hostile Reconnaissance](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance)

Note what the definition is **not**: it is not a list of body-language tells. It
is defined by *purpose* and *information-gathering*, and NPSA's detection advice
is **geographic and contextual**, not physiognomic: *"a critical aspect of
detecting and deterring hostile reconnaissance at a site is knowing the threat
that you face and understanding where hostiles might conduct their reconnaissance
from, which will enable the effective targeting of protective security measures
to the area's most vulnerable to hostile reconnaissance"*
([NPSA](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance);
see also [ProtectUK hostile reconnaissance](https://www.protectuk.police.uk/hostile-reconnaissance)).
NPSA also explicitly frames CCTV control rooms as a **disruption** resource, not
merely a detection one: guidance covers *"utilising existing protective security
resources such as CCTV control rooms, security officers and corporate
communications more effectively to disrupt hostile reconnaissance"*
([NPSA](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance)).

**Project Servator** is the operational doctrine built on this — *"a strategic
method of policing to deter, detect and disrupt a wide range of criminal
activity, from pickpocketing and property theft to terrorism"*, *"developed,
tested, and refined over a five-year period by experts at the National Protective
Security Authority (NPSA) in partnership with the City of London Police"*, in
which *"Servator officers are trained to identify subtle non-verbal signs
indicative of anxiety and agitation, and they interact with individuals
displaying suspicious behaviours to negate or confirm suspicions"*, and where
*"deployments are unpredictable and intelligence-led"*
([NPSA Project Servator](https://www.npsa.gov.uk/national-security-act/countering-threat-sabotage-operations-uk-interests-national-security/project-servator);
[NPSA resource](https://www.npsa.gov.uk/resources/project-servator);
[Counter Terror Business: a decade of vigilance](https://counterterrorbusiness.com/features/project-servator-decade-vigilance-and-community-partnership)).

**The crucial architectural point for us:** Servator's behavioural-detection step
is *always followed by human engagement to "negate or confirm"*. The behaviour
observation is a **trigger for a conversation**, never a conclusion. An automated
system that skips the "negate or confirm" step is not implementing the doctrine,
it is implementing its most criticised fragment. An independent evaluation exists
and should be read before making claims: [A comparison of Project Servator and
routine stop and search outcomes in the City of London](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11755829/).

### 4.3 The scientific demolition: TSA SPOT

This is the citation to keep in your back pocket, and to deploy the moment anyone
proposes an "intent from micro-expressions" module.

> *"The GAO reviewed four meta-analyses that included over 400 studies from the
> past 60 years and found that the human ability to accurately identify deceptive
> behavior based on behavioral indicators is the same as or slightly better than
> chance"* — quantified as *"the same as or slightly better than chance (54
> percent)"*.
> — [GAO-14-159, *Aviation Security: TSA Should Limit Future Funding for Behavior Detection Activities*](https://www.gao.gov/products/gao-14-159)

> *"10 years after the development of the SPOT program, TSA cannot demonstrate the
> effectiveness of its behavior detection activities."*
> — [GAO-14-158T](https://gao.gov/products/GAO-14-158T)

> *"Available evidence does not support whether behavioral indicators, which are
> used in the Transportation Security Administration's (TSA) Screening of
> Passengers by Observation Techniques (SPOT) program, can be used to identify
> persons who may pose a risk to aviation security."*
> — [GAO](https://www.gao.gov/products/gao-14-159)

And the 2017 follow-up went further, finding TSA *"Does Not Have Valid Evidence
Supporting Most of the Revised Behavioral Indicators Used in Its Behavior
Detection Activities"* ([GAO-17-608R](https://www.gao.gov/products/gao-17-608r)).
The scale: *"By fiscal year 2012, about 3,000 behavior detection officers (BDO)
had been deployed to 176 of the more than 450 TSA-regulated airports… TSA has
expended a total of approximately $900 million on the program since it was fully
deployed in 2007"* ([GAO](https://www.gao.gov/products/gao-14-159)); the actual
checklist was later published
([The Intercept, 2015](https://theintercept.com/2015/03/27/revealed-tsas-closely-held-behavior-checklist-spot-terrorists/)),
and Congress reached the same conclusion
([House Homeland Security Democrats report](https://democrats-homeland.house.gov/news/reports/report-tsa-unable-scientifically-validate-behavior-detection-program)).

**What this means for a product that "classifies indicators of intent".**
Deception and emotional-state cues are **54% — chance.** Therefore:

- **Defensible** (observable, physically grounded, auditable): dwell time in a
  zone; revisit count across days; body/head orientation toward assets; proximity
  to a boundary; counter-flow against crowd; route that avoids camera coverage;
  presence in a zone outside permitted hours; loitering *followed by* a physical
  act; object left and owner departing; contact-then-separate handover geometry;
  running in a context where nobody runs; a person horizontal for >N seconds.
- **Not defensible** (inferential, culturally loaded, low base-rate, and in the
  EU partly illegal — §9): nervousness, "agitation", gaze aversion, sweating,
  micro-expressions, emotion classes, "aggressive-looking", intent-from-face,
  "pre-crime" scoring of individuals.

The base-rate argument finishes the case even if the cues worked. `[lore, but
arithmetic]` At a site with 50,000 daily visitors and a genuine hostile
reconnaissance rate of, generously, one per month, a cue with 90% sensitivity and
99% specificity yields ~15,000 false positives per month against ~0.9 true
positives — a positive predictive value near 6×10⁻⁵. **No behavioural cue can
survive that base rate.** This is why the only workable architecture is
*corroboration across time and sensors* (the same identity, revisiting, at
unusual hours, oriented at assets, avoiding cameras) — which is exactly the
multi-camera, multi-day, cross-sensor ground truth our simulator uniquely
provides — and why the output must be a lead for human enquiry, never a score
about a person.

### 4.4 Predictive policing as the cautionary precedent

`[unquoted — search budget exhausted; verify before external use]` The PredPol /
place-based predictive policing literature is the standard cautionary citation:
critiques centre on **feedback loops** (patrols generate arrests in the areas the
model sent them, which become training data confirming the prediction),
**proxy-label bias** (recorded crime ≠ crime), and **construct invalidity** (the
model predicts *police activity*, not crime). The lesson transfers exactly:
**any behaviour analytic whose training labels come from operator alarm history
learns the operators' attention patterns, including their biases, not the
underlying behaviour.** If we are ever asked to train on a customer's historic
alarm logs, this is the objection to raise first. A synthetic-data programme is
the principled answer, because the label comes from the generator's intent, not
from anyone's suspicion.

---

## 5. Human factors: the actual bottleneck

### 5.1 Vigilance decrement — the numbers everyone half-remembers

The canonical operational claim: *"In an operational setting, typically after 20
min of active monitoring CCTV operators will often fail to detect objects in a
video scene"*, and the more aggressive industry figures: *"After 12 min of
continuous video monitoring an operator is likely to miss up to 45% of screen
activity and after 22 min of viewing up to 95% of activity is overlooked"*; also
quoted as *"After just 20 minutes, a monitor's ability to detect critical events
drops by more than 45 percent. After 40 minutes of uninterrupted viewing, the
degradation approaches 90 percent"*
([IntelliSee: the human monitoring limit](https://intellisee.com/the-human-monitoring-limit-why-manufacturing-cctv-fails-every-20-minutes/);
[Vigilance (psychology)](https://en.wikipedia.org/wiki/Vigilance_(psychology))).

**Handle these figures with care.** The 12-min/45% and 22-min/95% pair is
enormously cited in the security trade press and its ultimate provenance is a
1990s study of unclear methodology; treat it as **industry lore with a
peer-reviewed core**. The peer-reviewed core is solid and should be cited
instead:

- *Work exposure and vigilance decrements in closed circuit television
  surveillance* — the primary ergonomics study on shift exposure and decrement
  ([Applied Ergonomics 2014](https://www.sciencedirect.com/science/article/abs/pii/S0003687014001847)).
- *Semi-automated CCTV surveillance: the effects of system confidence, system
  accuracy and task complexity on operator vigilance, reliance and workload*
  ([Applied Ergonomics 2012](https://www.sciencedirect.com/science/article/abs/pii/S0003687012000695)).
  **This is the most important paper in this section for our purposes**: it studies
  exactly the design variable we control — *how the machine communicates its own
  confidence* — and its effect on operator reliance.
- *Pirate Stealth or Inattentional Blindness? The Effects of Target Relevance and
  Sustained Attention on Security Monitoring for Experienced and Naïve Operators*
  ([PLOS ONE 2014](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0086157);
  [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3897661/)). The key finding to
  quote: sustained monitoring produces **inattentional blindness — the failure to
  detect clearly visible events** — and, notably, **experience does not immunise
  operators against it.**

And the finding that should govern our UI: *"a CCTV operator may not be aware that
their levels of vigilance have deteriorated and that they may have missed
something"*
([search extraction; see Applied Ergonomics 2014](https://www.sciencedirect.com/science/article/abs/pii/S0003687014001847)).
**Self-report is not a control.** Any human-in-the-loop design that relies on the
operator noticing their own degradation is broken by construction; the system must
inject verification tasks, rotate duties, and measure response latency as a proxy
for state.

### 5.2 Alarm fatigue and the acceptable false-alarm rate

The industry's own framing: alarm fatigue is *"the desensitization operators
develop when exposed to excessive, repetitive, and mostly false alarms, leading
to slower response times, missed genuine events, and higher operator turnover in
central monitoring stations, alarm receiving centres, and GSOCs"*
([Actuate: Alarm Fatigue in Security Monitoring](https://actuate.ai/alarm-fatigue/)).

Quantified targets, from the same industry literature: *"A false alarm rate below
5% of total incoming alerts is considered a benchmark for operations to avoid
alarm fatigue, along with operator handling time under 30 seconds for verified
events and a cameras-per-operator ratio of 500:1 or higher on active shifts"*
([Actuate](https://actuate.ai/alarm-fatigue/)).

And the trust threshold, which is the number to design against: *"Research shows
that after three or four false alarms, operators begin to distrust the system"*
([Actuate](https://actuate.ai/alarm-fatigue/)).

The baseline it is measured against: *"98% of Security Camera Alarms Are False"*
([IntelliSee](https://intellisee.com/98-of-security-camera-alarms-are-false-heres-what-thats-actually-costing-you/)),
and *"When 95%+ of incoming alerts are false, the human brain adapts by tuning
them out"*
([Actuate](https://actuate.ai/alarm-fatigue/); cf.
[Becklar on false-alarm cost](https://becklar.com/resources/monitoring/false-alarms-fatigue-cost/)).
For the wider science of nuisance alarms in physical security, the Sandia/DOE
literature is the durable reference: [*The Impact of False and Nuisance Alarms on
the Design* (OSTI)](https://www.osti.gov/servlets/purl/1347158); and for the SOC
analogue, [Alert Fatigue in Security Operations Centres: Research Challenges and
Opportunities](https://www.researchgate.net/publication/389782034_Alert_Fatigue_in_Security_Operations_Centres_Research_Challenges_and_Opportunities)
and [Quantifying and mitigating alarm fatigue caused by fault detection systems](https://www.sciencedirect.com/science/article/abs/pii/S0951832025010907).

**Do the arithmetic that vendors do not.** "3–4 false alarms destroys trust" and
"500 cameras per operator" are jointly brutal. At 500 cameras and a target of, say,
20 alarms per operator-shift (8 h) to stay actionable, the permitted false-alarm
rate is **0.005 FA per camera-hour** — i.e. one nuisance alarm per camera per
**eight days**. Compare ActEV's measured operating point of **0.1 FA/minute = 6
per camera-hour** (§2.4): the research operating point is roughly **1,200× looser
than the deployment requirement.** This single comparison is the most important
quantitative statement in this dossier, and the strongest possible argument that
progress must come from *verification architecture and corroboration*, not from
squeezing the last AUC point out of a detector.

### 5.3 What the false-alarm-filtering market actually sells

Calipsa's claim is the market standard: *"Calipsa's industry-leading, 100%
cloud-based False Alarm Filtering analytics remove over 90% of event-based video
false alarms using the latest deep learning technology"*, working by recognising
*"the cause of the alarm and [filtering] out any that are not caused by human and
vehicle movement"*, with false alarms *"caused by anything from lighting to the
weather to foliage in the camera view"*, and one station reporting *"Calipsa has
filtered out over 1.9m false alarms in the last 30 days"*
([Calipsa for monitoring stations](https://www.calipsa.io/solution/for-monitoring-stations);
[Milestone marketplace listing](https://www.milestonesys.com/marketplace/calipsa/calipsa-ai-false-alarm-filtering-analytics/);
[TMA press release](https://tma.us/calipsas-video-false-alarm-reduction-platform-selected-by-sirix/)).

Ambient.ai: *"Ambient.ai's approach has demonstrated 90–95% false alarm reduction
at enterprise scale"* and it can *"auto-clear and reduce 95% of false access
control alarms"*
([Ambient.ai platform overview](https://www.ambient.ai/platform-overview);
[Ambient.ai: Context is King, Intent is Queen](https://www.ambient.ai/blog/context-is-king)).
Hakimo: it *"automatically resolves door-forced alerts with near 100% accuracy"*
and *"escalates only genuine security threats to authorities, eliminating false
alarms"*; in March 2025 it *"announced a $10.5 million funding round and the
launch of AI Operator, a breakthrough autonomous security agent that monitors
existing security hardware, detects threats in real time, and executes response
protocols just like a human security professional"*
([Hakimo](https://www.hakimo.ai/);
[Hakimo funding announcement](https://www.hakimo.ai/blog/hakimo-secures-10-5m-to-transform-physical-security-with-human-like-autonomous-security-agent);
[Genetec partner listing](https://www.genetec.com/partners/partner-integration-hub/hakimo/alarm-monitoring)).

**How to read "90% false alarm reduction".** It is a *reduction relative to the
legacy motion-based system*, not a precision figure, and the denominator is the
legacy detector's output. If 98% of 1,000 alarms/day are false and you remove 90%
of the false ones, you still ship ~98 nuisance alarms/day. The claim is real and
valuable and **says nothing about recall** — the missing number in every one of
these datasheets is *how many genuine events were filtered out*. That is the
question to ask, and the metric to demand: **FA reduction at stated
zero-miss-rate on a sequestered event set.** Our simulator can produce exactly
that test set, with the benign confusers (foliage, headlights, rain, animals,
shadows) that these products are specifically built to reject — which is why
[`docs/06_REALISM_AND_SENSOR_MODEL.md`](../06_REALISM_AND_SENSOR_MODEL.md)'s
weather and lighting axes are not cosmetic.

### 5.4 Control-room ergonomics and alert design

`[unquoted, professional practice — verify standards references before bidding]`

- **Verification-first UI.** Given NPSA's "all alarms need to be verified
  quickly", the alert payload matters more than the score: pre- and post-roll
  clip (typically 10 s pre / 10 s post), the bounding box, the track's zone
  history, the nearest overlapping camera's synchronised view, and a one-line
  reason. An alert without pre-roll is unverifiable, because the operator needs
  to see what happened *before* the trigger.
- **Alarm de-duplication and grouping** by track identity and by site, since
  i-LIDS scoring already treats repeat alarms as FPs — the metric and the UX
  agree here.
- **Escalation, not alarm.** A three-tier structure (log / review-queue /
  immediate) lets low-precision behaviours (loitering, unusual posture) feed a
  queue while only high-precision ones (line crossing in a sterile zone at
  night) ring a bell.
- **Duty cycle.** The vigilance literature implies rotation on the order of
  20–30 minutes for active search tasks; NPSA's "viewed at least once every five
  minutes" is a *coverage* rule, not a *fatigue* rule, and the two must both be
  satisfied.
- **Never auto-dispatch on a behaviour analytic.** Servator's "negate or confirm"
  and NPSA's "verified before any security response is initiated" are the same
  instruction from two directions.

### 5.5 Explainability for operators

Explainability here is not SHAP values; it is **"show me the evidence in three
seconds"**. The ActEV programme institutionalises this by making *activity-object
detection* the primary task (§2.4) — localise the participants, not just the
time. The academic thread is
[Unveiling the Unseen: A Comprehensive Survey on Explainable Anomaly Detection in
Images and Videos](https://arxiv.org/pdf/2302.06670), and
[X-MAN: Explaining multiple sources of anomalies in video](https://arxiv.org/pdf/2106.08856)
is the paper to cite for attributing an anomaly score to *which* factor (object,
action, location) drove it. The operationally relevant conclusion from the
weakly-supervised-localisation critique is blunt: *"without localization, systems
cannot distinguish genuine anomalies from dataset artifacts"*
([Localizing to Debias](https://arxiv.org/html/2608.12045)) — and neither can an
operator.

The semi-automation literature closes the loop: because operator **reliance** is
modulated by displayed **system confidence** and **accuracy**
([Applied Ergonomics 2012](https://www.sciencedirect.com/science/article/abs/pii/S0003687012000695)),
a miscalibrated confidence number is not a cosmetic defect — it actively
mis-tunes human behaviour. **Calibration (reliability diagrams, ECE) is a
human-factors requirement, not an ML nicety.**

---

## 6. Video-language models and natural-language event search

### 6.1 The commercial state

BriefCam is attribute-search, as quoted in §1.1 (28 classes and attributes, plus
face/plate recognition, appearance similarity, colour, size, speed, path,
direction, dwell time), plus *"patented VIDEO SYNOPSIS® technology that condenses
hours of surveillance into a short summary by overlaying multiple events onto a
single frame"*
([Milestone](https://www.milestonesys.com/resources/content/articles/briefcam-video-analytics-software/);
[BriefCam](https://www.briefcam.com/)). Vintra *"delivers AI-powered video
analytics solutions that transform real-world video into actionable
intelligence… whether fixed or mobile"*
([SecurityInfoWatch](https://www.securityinfowatch.com/video-surveillance/video-analytics/product/21261692/vintra-vintra-inc-ai-powered-video-analytics-solutions)).
viisights Wise offers the object/action/event/scene ladder and *"violent activity
prediction, suspicious behavior recognition, crowd behavior"*
([viisights](https://viisights.com/technology/);
[Wise 3.0 announcement](https://viisights.com/news/viisights-wise-3-0-ushers-in-next-generation-of-behavioral-recognition-video-analytics/)).
Actuate positions against these as a false-alarm-reduction and threat-detection
layer ([Actuate](https://actuate.ai/alarm-fatigue/)). IPVM's public analytics
report is the vendor-neutral comparison point
([IPVM Video Analytics Show](https://ipvm.com/reports/jan2022-analytics-show)).

**The honest read on "natural language search".** The retrieved limitations are
specific and worth quoting: platforms *"lack natural language video search
capability, and face recognition accuracy varies across demographics"*;
*"integrated vision-language models may encounter challenges in certain
specialized visual tasks like precise object counting"*; and, decisively,
*"systems with natural language interfaces are easy to use but do not generalize
to datasets different from the training set"*
([Zelda: Video Analytics using Vision-Language Models](https://arxiv.org/pdf/2305.03785);
[Ava: Towards Agentic Video Analytics with Vision Language Models](https://arxiv.org/html/2505.00254v5);
[Technical Challenges of AI in Video Analysis](https://memories.ai/blogs/Technical_Challenges_of_AI_in_Video_Analysis);
[SketchQL](https://dl.acm.org/doi/pdf/10.1145/3677140)).

So the sales demo — *"man in red jacket loitering near gate B after 22:00"* — is
in practice compiled down to **attribute filters + a zone + a dwell threshold +
a time window**, i.e. §1.1's rule dialect wearing a language costume. That is not
a criticism; it is the correct engineering. It does mean the *evaluation* must be
a structured-query benchmark, and our repository's queryable event index (per
[`docs/01_RESEARCH_LANDSCAPE.md`](../01_RESEARCH_LANDSCAPE.md) §1) is exactly the
ground truth needed to score it.

### 6.2 The research benchmarks for language-grounded anomaly

- **HAWK** *"focuses on open-world video anomaly understanding, collecting videos
  from seven diverse datasets, and supports both event description and question
  answering tasks"*, *"explicitly integrat[ing] motion modality"*, drawing from
  *"crime (UCF-Crime), campus environments (ShanghaiTech and CUHK Avenue),
  pedestrian walkways (UCSD Ped1 and Ped2), traffic situations (DoTA), and human
  behavior (UBnormal)"*
  ([HAWK, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/fca83589e85cb061631b7ebc5db5d6bd-Paper-Conference.pdf)).
- **CUVA** *"targets causation understanding in real-world anomaly videos,
  offering detailed annotations that explain what happened, why, and how for each
  event"* — *"cause, description and result"*
  ([via FineVAU](https://arxiv.org/pdf/2601.17258)).
- **Holmes-VAD / Holmes-VAU** push toward *"unbiased and explainable"* and
  *"long-term… at any granularity"* anomaly understanding
  ([Holmes-VAD](https://arxiv.org/html/2406.12235);
  [Holmes-VAU](https://arxiv.org/pdf/2412.06171)).
- **VERA** does *"verbalized learning"* to make VLM anomaly decisions explainable
  ([VERA, CVPR 2025](https://arxiv.org/pdf/2412.01095)).
- Newer entries worth tracking: [VAGU & GtS](https://arxiv.org/pdf/2507.21507)
  (joint grounding + understanding), [VADER](https://arxiv.org/pdf/2511.07299)
  (causal, relation-aware LLM), [TAU-Bench](https://arxiv.org/html/2608.05699),
  [FineVAU](https://arxiv.org/pdf/2601.17258),
  [DeepSVU](https://arxiv.org/pdf/2602.18019),
  [SRVAU-R1](https://arxiv.org/pdf/2602.01004),
  [Text-guided Fine-Grained Video Anomaly Understanding](https://arxiv.org/pdf/2511.00524),
  and [Is Video Anomaly Detection Misframed? Evidence from LLM-Based and
  Multi-Scene Models](https://arxiv.org/pdf/2605.12725).

**The structural limitation of the whole VLM-VAD line, stated plainly.** These
systems are evaluated on **trimmed or short clips with a known anomaly present**,
and scored on **description quality**. Deployment needs **continuous 24/7 streams
across hundreds of cameras**, a **calibrated score**, **sub-second latency**, and
**bounded cost**. A 7B-parameter VLM captioning every 2-second window on 500
cameras is ~21,600 inferences/minute — economically impossible today. The
realistic architecture (and what Ambient/Hakimo are in fact doing) is **cheap
always-on detectors + expensive VLM on the triggered clip, for description,
corroboration and auto-triage**. In that architecture the VLM's job is **false
alarm suppression and alert writing**, not detection — which matches the market
evidence in §5.3.

---

## 7. Dataset table

Sizes/licences below are as retrieved; licence fields marked `?` need checking on
the dataset page before use in a deliverable.

| Dataset | Year | Content | Size | Classes | Supervision | Licence |
|---|---|---|---|---|---|---|
| [i-LIDS](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems) | 2006– | UK gov CCTV, all weather/ToD | ~24 h **per scenario**, 2–3 views, 30–60 min clips | 4 scenarios: abandoned baggage, parked vehicle, doorway, sterile zone | Event-level alarm GT | UK Gov controlled access |
| [PETS2006](http://www.cvg.reading.ac.uk/PETS2006/data.html) | 2006 | Station concourse, 4 synced views | 7 scenarios | Abandoned luggage (T=30 s rule) | Event alarm-time GT | Research use |
| [PETS2007](http://www.cvg.reading.ac.uk/PETS2007/data.html) | 2007 | Airport, loitering/theft | — | Loitering, theft, baggage | Event GT | Research use |
| [VIRAT](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation) | 2011 | Ground + aerial surveillance | ~29 h `[verify]` | 23 event types `[verify]` | Spatio-temporal | Research `?` |
| [MEVA / ActEV](https://actev.nist.gov/) | 2019– | Multi-camera staged activity, EO+IR | ~9,300 h collected, ~1,100 h annotated `[verify]` | **37 EO / 34 IR** | Spatio-temporal, sequestered test | MEVA data licence |
| [UCSD Ped1/Ped2](https://arxiv.org/html/2212.00789v2) | 2010 | One walkway, greyscale 240×360 | Ped2: 2,550 train / 2,010 test frames | 12 abnormal events (bikes, skaters, wheelchairs) | Normal-only train | Research |
| [CUHK Avenue](https://arxiv.org/pdf/2012.01468) | 2013 | One campus avenue, 360×640 | 15,328 train / 10,622 test frames | 47 events (throwing, loitering, running) | Normal-only train | Research |
| [ShanghaiTech Campus](https://arxiv.org/pdf/2303.13051) | 2017 | 13 campus scenes, 480×856 | 274,515 train / 42,883 test frames | 130 events incl. brawl, chase, snatch | Normal-only train | Research |
| [UCF-Crime](https://www.crcv.ucf.edu/projects/real-world/) | 2018 | Web/CCTV, untrimmed | 1,900 videos (~128 h `[verify]`) | 13 crime classes | Weak (video-level) | Research |
| [XD-Violence](https://link.springer.com/chapter/10.1007/978-3-030-58577-8_20) | 2020 | Movies, web, sport, CCTV; **audio** | 4,754 videos, **~217 h** | Violence (6 sub-types `[verify]`) | Weak + frame-level test | Research |
| [UBnormal](https://github.com/lilygeorgescu/UBnormal) | 2022 | **Synthetic (Cinema4D)**, real backgrounds | **543 clips / 236,902 frames, 29 scenes** | Open-set, disjoint train/test types | **Pixel-level at train time** | Check repo |
| [NWPU Campus](https://campusvad.github.io) | 2023 | 43 campus scenes, staged by 30+ volunteers | 305 train / 242 test videos, **16 h** | **28** classes, incl. scene-dependent | Semi-supervised + **anticipation** | Check site |
| [UMN](http://gamma.cs.unc.edu/LARGE/papers/abnormal_behavior_detection.pdf) | 2009 | 3 locations (1 indoor, 2 outdoor) | 11 sequences | Escape/panic (run vs walk) | Normal-then-anomaly | Research |
| [RWF-2000](https://arxiv.org/pdf/1911.05913) | 2019 | **Real CCTV** from YouTube | 2,000 clips × 5 s @30fps | Violent / non-violent (1,000 each) | Clip-level, 80/20 split | Research |
| [Hockey Fight](https://pmc.ncbi.nlm.nih.gov/articles/PMC7725718/) | 2011 | NHL games, single scene | 1,000 clips | Fight / no fight | Clip-level | Research |
| [UR Fall](https://arxiv.org/html/2408.12211v1) | 2014 | 2 Kinects + accelerometer | 60 sequences | Fall / ADL | Clip-level, multimodal | Research |
| [Le2i (ImViA)](https://arxiv.org/pdf/2401.11790) | 2013 | Staged indoor | 250 videos (192 falls, 57 ADL) | Fall / ADL | Clip + frame | Research |
| [MSAD](https://arxiv.org/html/2608.12045) | 2024 | Multi-scenario anomaly | `[verify]` | `[verify]` | Weak | `?` |
| [HAWK](https://proceedings.neurips.cc/paper_files/paper/2024/file/fca83589e85cb061631b7ebc5db5d6bd-Paper-Conference.pdf) | 2024 | Language over 7 VAD datasets | — | Description + VQA | Language annotation | Inherits sources |
| [UCF-Crime-DVS](https://arxiv.org/html/2503.12905) | 2025 | Event-camera (DVS) conversion of UCF-Crime | — | 13 | Weak | Research |

### 7.1 Synthetic and simulated anomaly data — the precedents for this repo

- **UBnormal** (above) — the flagship: Cinema4D characters on real backgrounds,
  pixel-level train-time anomaly labels, open-set protocol.
- **SIMCD** — simulated crowd-disaster data built with commercial crowd
  simulators (MassMotion/Pathfinder lineage)
  ([Expert Systems with Applications](https://www.sciencedirect.com/science/article/pii/S0957417422008065)).
- **CrowdSim2** — Unity crowd generation for detection
  ([arXiv 2304.05090](https://arxiv.org/pdf/2304.05090)).
- **Densely annotated photorealistic virtual dataset for abnormal event
  detection** ([Springer](https://link.springer.com/chapter/10.1007/978-3-030-68799-1_1)).
- **Abandoned Luggage Detection with Synthetic Scenario Generation**
  ([Springer 2025](https://link.springer.com/chapter/10.1007/978-3-032-13757-9_21)).

**What none of them has, and we will:** multi-camera synchronised views with
calibration, non-overlapping topologies with transit-time truth, runtime
appearance mutation, PTZ and sensor degradation, per-tick continuous attributes
(dwell seconds, distance-to-asset, aggression intensity), explicit hard negatives
tagged `hard_negative_for`, and multi-sensor (RF/audio/door) alignment. Those are
the differentiators to state in any write-up.

---

## 8. Evaluation protocols and their flaws

**8.1 Frame-level AUC is the wrong metric and the field knows it.** The three
protocols in use are *"frame-level (FL), i-LIDS, and edge-level (EL)"*
([PIDS survey](https://pubmed.ncbi.nlm.nih.gov/35591289/)); academia uses FL
almost exclusively, and government uses rate-based event scoring. Frame AUC
(a) ignores latency, (b) rewards long-duration anomalies quadratically (a 900-frame
anomaly contributes 900 positives; a 20-frame one contributes 20), (c) has no
operating point, and (d) cannot be converted into alarms per camera-hour. The
critique is now explicit in the literature — see
[Rethinking Metrics and Benchmarks of Video Anomaly Detection](https://arxiv.org/html/2505.19022v2)
and [Is Video Anomaly Detection Misframed?](https://arxiv.org/pdf/2605.12725).

**8.2 Temporal tolerance must be declared.** i-LIDS fixes it at 10 s with FP
penalties for repeats (§2.3). Academic FL protocols have *no* tolerance concept at
all, which is why a method can "win" by smearing its score over the whole video.

**8.3 Class imbalance demands AP, not AUC.** XD-Violence chose AP
([ECCV 2020](https://link.springer.com/chapter/10.1007/978-3-030-58577-8_20)) and
is right. With anomalies at ~10⁻⁴ of frames in real deployments, AUC is dominated
by the vast negative mass and a useless detector looks excellent.

**8.4 Scene / background bias is the field's dirty secret.** *"Deep networks tend
to learn background information rather than the pattern of anomalies to recognize
abnormal behavior, a phenomenon known as background bias"*
([Exploring Background-bias for Anomaly Detection in Surveillance Videos, ACM MM 2019](https://dl.acm.org/doi/10.1145/3343031.3350998)).
Because UCF-Crime is web-sourced, an "explosion" video looks different *as a
scene* from a "normal" video, so a model can score 85% AUC by recognising video
provenance. *"Scene bias in weakly supervised video anomaly detection (WSVAD)
algorithms is measurably reducible under spatial conditioning"*, and
*"without localization, systems cannot distinguish genuine anomalies from dataset
artifacts"*
([Localizing to Debias](https://arxiv.org/html/2608.12045)). Remedies in the
literature: re-annotation and new metrics — *"researchers have re-annotated
anomaly detection datasets and designed new evaluation metrics to measure whether
models really learn the essence of anomalies"*
([Rethinking Metrics and Benchmarks](https://arxiv.org/html/2505.19022v2)) — and
causal/consistency approaches
([CRCL](https://arxiv.org/pdf/2503.18808);
[context-aware shortcut exploration](https://www.sciencedirect.com/science/article/abs/pii/S0031320324006289)).

**8.5 Scene leakage and train/test hygiene.** RWF-2000 advertises that its split
*"has been thoroughly checked for data leakage between the splits"*
([RWF-2000](https://arxiv.org/pdf/1911.05913)) precisely because most predecessors
did not. Single-scene datasets (Ped2, Avenue, Hockey Fight) make the split
meaningless: the same camera, same background, same actors appear on both sides.
**Any evaluation must be split by scene/camera, not by clip.** For our simulator:
split by **environment instance and camera pose**, and ideally by **character
asset**, or we will simply measure memorisation.

**8.6 Scene-dependent normality breaks the whole i.i.d. framing.** NWPU Campus is
*"the only one considering scene-dependent anomaly"*
([CVPR 2023](https://openaccess.thecvf.com/content/CVPR2023/papers/Cao_A_New_Comprehensive_Benchmark_for_Semi-Supervised_Video_Anomaly_Detection_and_CVPR_2023_paper.pdf));
see also [Scene-dependent video anomaly detection: A benchmark and weakly
supervised model](https://www.sciencedirect.com/science/article/pii/S1110016825011342)
and [Knowledge-Graph decoupling of scene and action](https://arxiv.org/html/2409.03236).
Operationally this means **there is no such thing as a site-agnostic behaviour
model**, and the deployment metric that matters is *performance after N days of
on-site adaptation with zero labels* — a metric nobody publishes.

**8.7 Open-set is the only honest protocol.** UBnormal's disjoint train/test
anomaly types (§3.5) is the design to copy. A closed-set result tells you nothing
about the attack that has not happened yet, which is the only attack that matters.

**8.8 Statistical power.** Twelve events (Ped2) or 47 (Avenue) cannot support the
two-decimal AUC differences routinely claimed. A 1-point AUC difference on Ped2 is
noise. Ask for confidence intervals, or for per-event outcomes.

---

## 9. Legal and ethical constraints (UK/EU)

**9.1 UK: Surveillance Camera Code of Practice.** First published *"in June 2013
under provisions in the Protection of Freedoms Act 2012"*, it contains *"12
guiding principles"*, of which the first is: *"Use of a surveillance camera system
must always be for a specified purpose which is in pursuit of a legitimate aim
and necessary to meet an identified pressing need"*, and another: *"The user of a
surveillance camera system must take into account its effect on individuals and
their privacy, with regular reviews to ensure its use remains justified"*
([Amended Surveillance Camera Code of Practice](https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version);
[2013 Code PDF](https://assets.publishing.service.gov.uk/media/5a7b91a240f0b62826a046c0/Surveillance_Camera_Code_of_Practice_WEB.pdf)).
It was *"revised in 2021 and is overseen by the Biometrics and Surveillance Camera
Commissioner"*
([Biometrics and Surveillance Camera Commissioner](https://en.wikipedia.org/wiki/Biometrics_and_Surveillance_Camera_Commissioner);
[House of Lords Library: regret motion](https://lordslibrary.parliament.uk/surveillance-camera-code-of-practice-regret-motion/);
[local-authority guide](https://www.gov.uk/government/publications/surveillance-camera-code-of-practice-guidance-for-local-authorities/surveillance-camera-code-of-practice-a-guide-for-local-authorities-accessible)).
**"Specified purpose… pressing need" is a direct constraint on behaviour
analytics:** you cannot bolt an aggression detector onto an estate authorised for
"crime prevention at the goods entrance" and call it covered.

**9.2 UK: ICO video-surveillance guidance and DPIAs.** Organisations *"must take a
data protection by design and default approach and perform a Data Protection
Impact Assessment (DPIA) for any processing that is likely to result in a high
risk to individuals when using surveillance systems"*, and the guidance covers
*"the use of CCTV, Automatic Number Plate Recognition, Body Worn Video, Drones,
Facial Recognition Technology, dashcams and smart doorbell cameras"*, with
examples of high risk including *"surveillance cameras, such as body worn video,
that also record audio or CCTV fitted with automatic facial recognition
capabilities"*
([ICO: CCTV and video surveillance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/);
[ICO: complying with the data protection principles](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/how-can-we-comply-with-the-data-protection-principles-when-using-surveillance-systems/?q=DPIA);
[SCC/ICO DPIA guidance](https://assets.publishing.service.gov.uk/media/5ea6f1fc86650c031af37947/SCC___ICO_DPIA_guidance_V3_FINAL_PDF.pdf);
commentary: [Lewis Silkin](https://www.lewissilkin.com/insights/2022/07/04/nothing-we-do-is-ever-going-unnoticed-icos-video-surveillance-guidance-102hs06),
[Mills & Reeve](https://www.mills-reeve.com/blogs/technology/march-2022/new-ico-video-surveillance-guidance/),
[DWF](https://dwfgroup.com/en/news-and-insights/insights/2022/3/ico-guidance-video-surveillance)).
**A DPIA is effectively mandatory for behaviour analytics**, and the two flags to
watch are **audio** (relevant to XD-Violence-style audio-visual models — §3.3) and
**biometric identification**.

**9.3 EU AI Act.** Prohibitions under Article 5 *"include emotion recognition at
education and workplace, biometric categorisation to infer sensitive attributes
such as political opinion or sexual orientation, and real-time remote biometric
identification"*; the Commission clarified the emotion prohibition *"should be
limited to 'inferences based on a person's biometric data'"*, biometric data being
*"personal data resulting from specific technical processing relating to the
physical, physiological or behavioural characteristics of a natural person, such
as facial images or dactyloscopic data"*; Article 5(1)(g) bans systems that
categorise people *"based on their biometric data to deduce or infer their race,
political opinions, trade union membership, religious or philosophical beliefs,
sex life or sexual orientation"*; and the real-time RBI prohibition *"only applies
to real time remote biometric identification in publicly accessible spaces for
law enforcement"*
([AI Act Service Desk FAQ on Article 5](https://ai-act-service-desk.ec.europa.eu/en/ai-act/faq/what-systems-are-prohibited-under-article-5-ai-act-eg-social-scoring-emotion-recognition);
[FPF: Red Lines under the EU AI Act](https://fpf.org/blog/red-lines-under-eu-ai-act-unpacking-the-prohibition-of-emotion-recognition-in-the-workplace-and-education-institutions/);
[Bundesnetzagentur: prohibited practices](https://www.bundesnetzagentur.de/EN/Areas/Digitalisation/AI/08_ProhibitedPractices/start.html);
[European Commission AI Act portal](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai);
[State of Surveillance explainer](https://stateofsurveillance.org/news/eu-ai-act-august-2026-biometric-surveillance-explainer/)).

**Read against our product surface, three conclusions follow:**
1. **"Aggressive behaviour" detection is legal; "aggressive person" classification
   may not be.** Detecting a *physical act* (a strike, a shove, a fall) from
   motion is action recognition. Inferring an *emotional state* from face or body
   is emotion recognition, prohibited in workplace and education contexts (note
   that a staffed CNI site *is* a workplace) — with an exception *"for medical or
   safety purposes"* whose scope is untested. **Never label a module "emotion" or
   "anger" when it is in fact "rapid limb motion + proximity".** That is not a
   euphemism; it is an accurate description that also keeps you legal.
2. **Behaviour analytics for critical infrastructure is plausibly high-risk under
   Annex III.** `[unquoted — I could not retrieve Annex III text; the search
   result explicitly noted it "do not contain specific information about… Annex
   III high-risk classifications for critical infrastructure". Verify the exact
   Annex III point and whether a security analytic on a CNI site is caught as
   "safety component of critical infrastructure management".]` If caught: risk
   management, data governance, logging, human oversight, accuracy/robustness
   documentation and post-market monitoring all apply — which is, usefully, an
   argument *for* a simulator, since Annex-III-style robustness evidence across
   weather/lighting/demographics is exactly what synthetic data can produce.
3. **Demographic performance disparity is a documented, cited weakness** —
   *"face recognition accuracy varies across demographics"*
   ([Technical Challenges of AI in Video Analysis](https://memories.ai/blogs/Technical_Challenges_of_AI_in_Video_Analysis)).
   Behaviour analytics inherits it through detection and pose estimation; our
   catalogue's `disabled_mobility` row (wheelchair, crutches) exists precisely to
   test that a "crawling/unusual posture" detector does not criminalise
   disability. That is a fairness *test case*, and it should be a required one.

**9.4 GDPR/UK GDPR mechanics** `[unquoted, standard practice]`: lawful basis
(legitimate interests with an LIA, or public task), necessity and
proportionality, transparency (signage — hard for covert behaviour analytics),
purpose limitation (no repurposing alarm data for HR), retention (typically 31
days for CCTV unless evidentially required), data minimisation (skeleton or
metadata rather than raw video — see §3.7's privacy argument), and DSAR handling
(a behaviour score about an identified person is personal data and is disclosable,
including the reason for it). Synthetic training data sidesteps much of this,
which is a commercial argument for this project as well as an ethical one.

---

## 10. Open problems, 2024–2026

1. **Rate-based evaluation.** The field has no shared benchmark reporting
   `Pmiss @ FA-per-camera-hour` on long continuous multi-camera video. ActEV is
   the model; the data is sequestered. A synthetic, openly-shareable ActEV-style
   protocol is an unclaimed contribution.
2. **The 1,200× gap** between research operating points (0.1 FA/min) and
   deployment requirements (§5.2). Nobody is working on this as a stated problem.
3. **Open-set generalisation of pose anomaly.** 52.0–68.3 AUC on UBnormal (§3.7)
   is the real frontier, not 89.8 on UCF-Crime.
4. **Scene-dependent normality with zero on-site labels** — few-shot/continual
   site adaptation ([Continual Learning for Anomaly Detection in Surveillance
   Videos](https://arxiv.org/pdf/2004.07941)).
5. **Owner–object association** for abandonment across occlusion and handover;
   still unsolved at crowd density.
6. **Cross-camera behaviour** — loiter-leave-return, following, tailgating and
   revisit-over-days all require identity persistence across non-overlapping
   views, which is a ReID problem with clothing change; almost no VAD benchmark
   is multi-camera at all. **This is our repo's sharpest edge.**
7. **VLM cost/latency architecture** — where to put the expensive model (§6.2),
   and how to calibrate its confidence for operator reliance.
8. **Calibration and abstention.** No VAD paper reports ECE. Operators need
   "I don't know" as an output class.
9. **Adversarial and evasive behaviour** — camera-aware path planning, crowd
   cover, role disguise (our catalogue §4). Essentially unstudied, because you
   cannot collect it.
10. **Benchmark contamination** by web-scale VLM pretraining (§3.2 note 4); no
    accepted audit method exists.
11. **Anomaly anticipation** as a first-class task (NWPU Campus, §3.6) — the
    scientifically respectable version of "intent".
12. **Fairness of behaviour analytics** across body morphology, mobility aids,
    cultural dress and age; no benchmark exists.
13. **Event-camera / DVS and thermal** behaviour analytics for low light and
    privacy ([UCF-Crime-DVS](https://arxiv.org/html/2503.12905)).
14. **Sim-to-real for behaviour**, not just appearance: do motion priors learned
    from animation libraries transfer? UBnormal says partly; nobody has measured
    it for aggression or tampering.
15. **Standardising a behaviour ontology.** ONVIF Profile M names loitering and
    tamper; MEVA names 37 activities; no mapping exists between them. Publishing
    one would be cheap and disproportionately useful.

---


Each bullet is marked `[sourced]` (supported above), `[inference]` (derived from
sourced facts) or `[lore]` (field experience, unverifiable but worth knowing).

1. **There is no standard loitering threshold, and asking "what's the default?"
   marks you as new.** Axis's own documentation leaves it configurable
   `[sourced]`. The threshold is a *policy*, so the first design question is
   "who owns the number and who gets blamed when it's wrong?" `[lore]`
2. **Every dwell-based alarm has a hidden latency floor.** Axis requires an object
   *"completely visible in the detection zone for at least three seconds"* before
   tracking counts `[sourced]`, so alarm time = acquisition + dwell. Forensic
   timeline disputes usually resolve to this `[inference]`.
3. **The benchmark you can win and the test you must pass are 1,200× apart.**
   ActEV's operating point is 0.1 FA/min = 6/camera-hour `[sourced]`; a 500-camera
   estate with a trust budget of ~20 alarms/shift needs ~0.005/camera-hour
   `[inference]`. Quote this ratio and the room goes quiet `[lore]`.
4. **Operators stop trusting the system after three or four false alarms**
   `[sourced]`. Not after 30% precision — after *four events*. Trust is
   event-counted, not rate-integrated, which is why the first week of a
   deployment determines its fate `[inference]`.
5. **"90% false alarm reduction" is a reduction against the legacy detector, with
   no recall number attached** `[sourced claims; inference on the gap]`. Always ask
   for "FA reduction at zero missed events on a sequestered set."
6. **The customer's real requirement is verifiability, not accuracy.** NPSA:
   *"all alarms need to be verified quickly, before any security response is
   initiated"* `[sourced]`. Ship pre-roll, a box, and a one-line reason, and a
   mediocre detector becomes a usable product `[lore]`.
7. **Nobody can reduce headcount below the assurance floor.** NPSA requires each
   camera image *"actively viewed at least once every five minutes"* where the
   perimeter relies on assured measures `[sourced]`. That arithmetic, not AI,
   sets staffing `[inference]`.
8. **Tamper detection is solved; tamper *false alarms* are an environmental
   problem.** >96% of 350 tamper events at zero FA over 13 h and 20+ scenes
   `[sourced]`. The field failures are lorries, sunrise, spiders and thermal mast
   drift `[lore]`.
9. **Vendors' "idle object" does not model ownership.** It models "a blob stopped
   moving" `[sourced: Bosch]`. Abandonment as a *concept* requires owner
   association, which is the actual research problem `[sourced]`, and is why
   abandoned-baggage analytics disappoint in crowds `[lore]`.
10. **Line crossing beats area intrusion, and indoors beats outdoors, every time**
    `[sourced: IPVM]`. If the requirement permits a tripwire, use a tripwire.
11. **DORI is for human eyes, and there is no published pixels-per-metre figure for
    pose or behaviour analytics** `[sourced for DORI; inference for the gap]`. When
    someone asks "will fight detection work on that camera?", the honest answer is
    "unknown, and that's a measurable gap" — which is a project, not an excuse.
12. **Deception and emotion cues are chance-level (54%) across 400+ studies over 60
    years** `[sourced: GAO]`. $900m and 3,000 officers did not fix it `[sourced]`.
    Any "intent from demeanour" feature is a legal and reputational liability, and
    in EU workplace/education contexts it is prohibited `[sourced]`.
13. **The base rate kills everything.** 50,000 visitors/day and one real hostile
    recce a month means even 90%/99% cues give PPV ~6×10⁻⁵ `[inference]`. The only
    escapes are corroboration across time/cameras/sensors, and treating output as
    a lead for enquiry — exactly Servator's *"negate or confirm"* step `[sourced]`.
14. **Intent numbers are inflated by easy negatives.** JAAD-all AUC 0.92 →
    JAAD-beh AUC 0.62 for the same class of model `[sourced]`. Demand the hard
    subset.
15. **Fight detectors quoting >95% are quoting Hockey Fight.** Real CCCTV
    (RWF-2000) sits at ~83–85% on trimmed 5-second clips `[sourced]`, and nobody
    benchmarks "find the fight in 24 h of live multi-camera video" at all
    `[inference]`.
16. **Pose anomaly detection barely beats chance on unseen anomaly types**: GEPC
    52.0 on UBnormal, MoCoDAD 68.3 `[sourced]`. That is the honest ceiling for
    "unusual posture or movement" modules today.
17. **Falls are the one behaviour where you tune for recall** — misses cost lives,
    false positives cost a wasted look `[lore]`; and the best honest staged-data
    sensitivity is ~86.67% `[sourced]`, from a frontal well-lit 3 m view.
18. **Academic datasets are unit tests.** UCSD Ped2's whole test set is ~2,010
    frames (~67 s) with 12 events, and people report AUC on it to two decimals
    `[sourced]`. i-LIDS gave ~24 h per scenario, all weather, 2–3 views, in 2006
    `[sourced]`. Twenty years on, the academic community still does not use it.
19. **Half the AUC on web-sourced anomaly benchmarks is scene recognition, not
    behaviour recognition** — "background bias" `[sourced]`. If you cannot localise
    the anomaly, you cannot tell your model from a dataset artefact `[sourced]`.
20. **Split by camera and scene, never by clip** `[inference from RWF-2000's
    leakage-checked split, sourced]`. For synthetic data, split by environment
    instance, camera pose, and ideally character asset `[lore]`.
21. **There is no site-agnostic behaviour model.** NWPU Campus exists because
    normality is scene-dependent `[sourced]`. Budget for a commissioning period,
    and make "days-to-acceptable-precision" a contract metric `[lore]`.
22. **Evaluate events, not frames, with a declared tolerance.** i-LIDS: 10 s
    window, repeats counted as FPs `[sourced]`. That means **alarm
    de-duplication is scored**, so build it before you tune the model
    `[inference]`.
23. **"Natural language video search" is compiled into attribute filters + zone +
    dwell + time window.** BriefCam's own feature list is attributes including
    dwell time `[sourced]`; and NL interfaces *"do not generalize to datasets
    different from the training set"* `[sourced]`. Sell it honestly and it still
    sells `[lore]`.
24. **Put the expensive model after the trigger, not before it.** 500 cameras ×
    a 2-s VLM window is ~21,600 inferences/minute `[inference]`. The viable
    architecture is cheap always-on detection plus VLM for suppression,
    description and triage — which is what the market leaders are in fact doing
    `[inference from their own claims, sourced]`.
25. **Call the module what it measures.** "Rapid limb motion in proximity", not
    "anger"; "dwell exceeded in zone", not "suspicious intent". This is both more
    accurate and the difference between an Annex-III conversation and an Article-5
    problem `[sourced for the legal distinction; lore for the naming discipline]`.
26. **Never train on the customer's historical alarm log.** You will learn their
    operators' attention and their biases, not the behaviour — the predictive
    policing feedback-loop failure, transplanted `[inference; PredVol/PredPol
    critique unverified above]`.
27. **The operator cannot tell you when they have stopped seeing**
    *"a CCTV operator may not be aware that their levels of vigilance have
    deteriorated"* `[sourced]`. Design rotation and injected verification tasks;
    never rely on self-report `[inference]`.
28. **Displayed confidence changes operator behaviour** `[sourced: Applied
    Ergonomics 2012]`, therefore **calibration is a safety requirement**, not an
    ML nicety `[inference]`. No VAD paper reports ECE `[lore]`.
29. **Institutional names are a credibility tell.** PSDB → HOSDB → CAST; CPNI →
    NPSA `[sourced]`. Anyone still saying "CPNI approved" in 2026 is reading a
    2012 document `[lore]`.
30. **The winning move in this field for the last fifteen years has not been a
    better classifier; it has been a better *rule composition*** — Genetec's
    alarm/source/transport regions `[sourced]`, Bosch's radius-plus-time
    `[sourced]`, schedule and role context. Learned models earn their place by
    replacing a *feature* in that composition, not the composition itself
    `[lore]`.

---

## Sources

**UK government / standards**
- [i-LIDS: A Standard for Testing Video Based Detection Systems](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)
- [NPSA · Perimeter Intrusion Detection (PIDS)](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-pids) · [Guide to PIDS](https://www.npsa.gov.uk/system/files/documents/2c/80/Guide-to-PIDS.pdf) · [NPSA/HO Guide to PIDS](https://www.npsa.gov.uk/system/files/documents/NPSA%20HO%20Guide%20to%20PIDS.pdf) · [PIDS Evaluation Schemes](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-systems-pids-evaluation-schemes)
- [NPSA · CCTV for CNI Perimeter Security](https://www.npsa.gov.uk/system/files/documents/NPSA%20CCTV%20for%20CNI%20Perimeter.pdf) · [CPNI version](https://www.npsa.gov.uk/system/files/documents/ff/2f/CCTV%20for%20CNI%20Perimeter.pdf) · [NPSA CCTV](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/cctv)
- [NPSA · Hostile Reconnaissance](https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance) · [Disrupting Hostile Reconnaissance](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance) · [Specialised guidance](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance) · [Project Servator](https://www.npsa.gov.uk/national-security-act/countering-threat-sabotage-operations-uk-interests-national-security/project-servator) · [ProtectUK](https://www.protectuk.police.uk/hostile-reconnaissance) · [Servator evaluation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11755829/) · [Counter Terror Business](https://counterterrorbusiness.com/features/project-servator-decade-vigilance-and-community-partnership)
- [Surveillance Camera Code of Practice (amended)](https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version) · [2013 Code](https://assets.publishing.service.gov.uk/media/5a7b91a240f0b62826a046c0/Surveillance_Camera_Code_of_Practice_WEB.pdf) · [Local authority guide](https://www.gov.uk/government/publications/surveillance-camera-code-of-practice-guidance-for-local-authorities/surveillance-camera-code-of-practice-a-guide-for-local-authorities-accessible) · [Lords Library](https://lordslibrary.parliament.uk/surveillance-camera-code-of-practice-regret-motion/) · [BSCC](https://en.wikipedia.org/wiki/Biometrics_and_Surveillance_Camera_Commissioner)
- [ICO · CCTV and video surveillance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/) · [data protection principles](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/how-can-we-comply-with-the-data-protection-principles-when-using-surveillance-systems/?q=DPIA) · [SCC/ICO DPIA guidance](https://assets.publishing.service.gov.uk/media/5ea6f1fc86650c031af37947/SCC___ICO_DPIA_guidance_V3_FINAL_PDF.pdf)
- [IEC/EN 62676-4:2025 (Axis)](https://newsroom.axis.com/en-us/blog/iec-62676-4-video-surveillance) · [Pixel density per IEC 62676-4:2014](https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014) · [DORI explained](https://www.backstreet-surveillance.com/cctv-industry-experts/dori-cctv.html) · [Infiniti DORI](https://www.infinitioptics.com/whitepapers/dori-detection-observation-recognition-identification) · [JVSG on the 2025 revision](https://www.jvsg.com/iec-62676-4-oodpcvs/)
- [ONVIF Profile M](https://www.onvif.org/profiles/profile-m/) · [press release](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/) · [Analytics Service Spec](https://www.onvif.org/specs/srv/analytics/ONVIF-Analytics-Service-Spec.pdf)

**US evaluation programmes**
- [NIST ActEV](https://actev.nist.gov/) · [ActEV SRL leaderboard](https://actev.nist.gov/srl) · [NIST programme page](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation) · [2020 Sequestered Data Evaluation (WACVW 2021)](https://openaccess.thecvf.com/content/WACV2021W/HADCV/papers/Godil_2020_Sequestered_Data_Evaluation_for_Known_Activities_in_Extended_Video_WACVW_2021_paper.pdf) · [Argus++](https://arxiv.org/pdf/2201.05290) · [TRECVID 2020](https://arxiv.org/pdf/2104.13473) · [TRECVID 2022](https://arxiv.org/pdf/2306.13118) · [Fine-grained Activities of People Worldwide](https://arxiv.org/pdf/2207.05182)
- [GAO-14-159](https://www.gao.gov/products/gao-14-159) · [GAO-14-158T](https://gao.gov/products/GAO-14-158T) · [GAO-17-608R](https://www.gao.gov/products/gao-17-608r) · [House Homeland Security report](https://democrats-homeland.house.gov/news/reports/report-tsa-unable-scientifically-validate-behavior-detection-program) · [The Intercept: SPOT checklist](https://theintercept.com/2015/03/27/revealed-tsas-closely-held-behavior-checklist-spot-terrorists/)

**Vendors**
- [AXIS Loitering Guard](https://help.axis.com/en-us/axis-loitering-guard) · [AXIS Perimeter Defender](https://help.axis.com/en-us/axis-perimeter-defender) · [Perimeter Defender manual](https://www.a1securitycameras.com/content/product_documents/13284/axis-um_perimeterdefender_1587516_en_1702-A1.pdf)
- [Bosch IVA Pro configuration manual](https://www.networkwebcams.co.uk/content/pdf/bosch/bosch-iva-pro-traffic-user-manual.pdf) · [IVA task descriptions](https://knowledge.keenfinity-group.com/video-systems/article/what-does-do-each-task-of-video-analytics-bosch-se) · [Idle & removed object](https://knowledge.keenfinity-group.com/video-systems/article/how-to-configure-idle-removed-object-detection-on-) · [IVA 3.5 manual](https://objects.eanixter.com/PD513616.PDF) · [IVA capabilities per device](https://media.boschsecurity.com/fs/media/pb/media/products_1/video_systems_1/Whitepaper_IVA_CapabilitiesPerDevice_FW900.pdf) · [Bosch metadata in ONVIF](https://media.boschsecurity.com/fs/media/pb/media/partners_1/integration_tools_1/developer/bosch-metadata-and-iva-events.pdf)
- [Hikvision VCA configuration](https://www.hikvisioneurope.com/eu/portal/portal/Technical%20Materials/24%20How%20To/CCTV/How%20to%20configure%20VCA%20function.pdf) · [Genetec KiwiVision](https://www.genetec.com/products/unified-security/omnicast/video-analytics) · [KiwiVision custom intrusion scenario](https://techdocs.genetec.com/r/es-MX/Guia-del-usuario-de-KiwiVisionTM-para-Security-Center-5.12.2.0/Escenario-del-detector-de-intrusiones-personalizado-para-KiwiVision-video-analytics) · [Avigilon UMD](https://docs.avigilon.com/bundle/designing-site-for-analytics/page/umd/unusual-motion-detection.htm) · [Avigilon UAD](https://support.avigilon.com/s/article/Video-ACC-Unusual-Activity-Detection?language=en_US)
- [BriefCam](https://www.briefcam.com/) · [Milestone on BriefCam](https://www.milestonesys.com/resources/content/articles/briefcam-video-analytics-software/) · [BriefCam federal capabilities](https://www.briefcam.com/wp-content/uploads/2025/06/BriefCam-FederalCapabilitiesStatement-2023-1.pdf) · [Vintra](https://www.securityinfowatch.com/video-surveillance/video-analytics/product/21261692/vintra-vintra-inc-ai-powered-video-analytics-solutions) · [viisights](https://viisights.com/technology/) · [Wise 3.0](https://viisights.com/news/viisights-wise-3-0-ushers-in-next-generation-of-behavioral-recognition-video-analytics/) · [Calipsa](https://www.calipsa.io/solution/for-monitoring-stations) · [Calipsa on Milestone](https://www.milestonesys.com/marketplace/calipsa/calipsa-ai-false-alarm-filtering-analytics/) · [TMA/Sirix](https://tma.us/calipsas-video-false-alarm-reduction-platform-selected-by-sirix/) · [Ambient.ai](https://www.ambient.ai/platform-overview) · [Ambient: Context is King](https://www.ambient.ai/blog/context-is-king) · [Hakimo](https://www.hakimo.ai/) · [Hakimo AI Operator](https://www.hakimo.ai/blog/hakimo-secures-10-5m-to-transform-physical-security-with-human-like-autonomous-security-agent) · [Actuate: alarm fatigue](https://actuate.ai/alarm-fatigue/) · [IPVM analytics report](https://ipvm.com/reports/jan2022-analytics-show) · [IPVM loitering discussion](https://ipvm.com/discussions/loitering-analytics) · [IPVM analytics course](https://ipvm.com/course/analytics-course-on-demand/overview)

**Datasets**
- [PETS2006](http://www.cvg.reading.ac.uk/PETS2006/data.html) · [PETS2007](http://www.cvg.reading.ac.uk/PETS2007/data.html) · [Localized Detection of Abandoned Luggage](https://link.springer.com/article/10.1155/2010/675784/tables/1) · [Abandoned object in illumination changes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6928649/) · [Real-time DL abandoned luggage](https://arxiv.org/pdf/1803.01160) · [Synthetic abandoned-luggage scenarios](https://link.springer.com/chapter/10.1007/978-3-032-13757-9_21)
- [UCF-Crime (CVPR 2018)](https://openaccess.thecvf.com/content_cvpr_2018/papers/Sultani_Real-World_Anomaly_Detection_CVPR_2018_paper.pdf) · [CRCV project](https://www.crcv.ucf.edu/projects/real-world/) · [UCF-Crime overview](https://www.emergentmind.com/topics/ucf-crime-dataset) · [UCF-Crime-DVS](https://arxiv.org/html/2503.12905)
- [XD-Violence (ECCV 2020)](https://link.springer.com/chapter/10.1007/978-3-030-58577-8_20) · [Hyperbolic AVVD](https://arxiv.org/pdf/2305.18797) · [MACIL-SD](https://arxiv.org/pdf/2207.05500) · [Aligning First, Then Fusing](https://arxiv.org/html/2501.07496v2)
- [UBnormal](https://arxiv.org/abs/2111.08644) · [HTML](https://arxiv.org/html/2111.08644v3) · [repo](https://github.com/lilygeorgescu/UBnormal) · [NWPU Campus (CVPR 2023)](https://openaccess.thecvf.com/content/CVPR2023/papers/Cao_A_New_Comprehensive_Benchmark_for_Semi-Supervised_Video_Anomaly_Detection_and_CVPR_2023_paper.pdf) · [arXiv](https://arxiv.org/abs/2305.13611) · [site](https://campusvad.github.io)
- [Ped2/Avenue/ShanghaiTech statistics](https://arxiv.org/html/2212.00789v2) · [likelihood-of-representations](https://arxiv.org/pdf/2012.01468) · [Hierarchical Semantic Contrast](https://arxiv.org/pdf/2303.13051)
- [RWF-2000](https://arxiv.org/pdf/1911.05913) · [Hockey Fight / AVD dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC7725718/) · [Violence 4D](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/cvi2.12162) · [CUE-Net](https://arxiv.org/pdf/2404.18952) · [Two-stream 2D/3D](https://arxiv.org/pdf/2211.04255) · [Federated violence detection](https://arxiv.org/pdf/2504.00857)
- [UMN / Social Force Model (CVPR 2009)](http://gamma.cs.unc.edu/LARGE/papers/abnormal_behavior_detection.pdf) · [CRCV Abnormal Crowd](https://www.crcv.ucf.edu/projects/Abnormal_Crowd/) · [Holistic features](https://arxiv.org/pdf/1606.05310) · [Crowd taxonomy](https://pmc.ncbi.nlm.nih.gov/articles/PMC9415874/) · [Deep crowd anomaly detection](https://link.springer.com/article/10.1007/s10462-024-11092-8) · [GLCM crowd violence](https://arxiv.org/pdf/1605.05106) · [Repulsive forces + sparse reconstruction](https://arxiv.org/pdf/1808.06749)
- [UR Fall / Le2i via ST-GCN](https://arxiv.org/html/2408.12211v1) · [Fall detection review](https://arxiv.org/pdf/2401.11790) · [Global/local feature fall detection](https://www.sciencedirect.com/science/article/abs/pii/S016786552400206X) · [Ensemble YOLO/DETR fall detection](https://www.nature.com/articles/s41598-025-97634-8) · [Three-stream ST-GCN](https://www.nature.com/articles/s41598-025-95508-7)
- [SIMCD](https://www.sciencedirect.com/science/article/pii/S0957417422008065) · [CrowdSim2](https://arxiv.org/pdf/2304.05090) · [Densely annotated virtual abnormal-event dataset](https://link.springer.com/chapter/10.1007/978-3-030-68799-1_1)

**Methods, surveys and metric critiques**
- [VAD in 10 Years: Survey and Outlook](https://arxiv.org/pdf/2405.19387) · [Divide and Conquer in VAD](https://arxiv.org/pdf/2309.14622) · [DL techniques for VAD](https://arxiv.org/pdf/2009.14146) · [NSVAD tutorial/survey](https://github.com/fdjingliu/nsvad) · [awesome-video-anomaly-detection](https://github.com/fjchange/awesome-video-anomaly-detection) · [VAD for Smart Surveillance](https://arxiv.org/pdf/2004.00222) · [Continual learning for VAD](https://arxiv.org/pdf/2004.07941)
- [Holmes-VAU (CVPR 2025)](https://openaccess.thecvf.com/content/CVPR2025/papers/Zhang_Holmes-VAU_Towards_Long-term_Video_Anomaly_Understanding_at_Any_Granularity_CVPR_2025_paper.pdf) · [arXiv](https://arxiv.org/pdf/2412.06171) · [Holmes-VAD](https://arxiv.org/html/2406.12235) · [Fine-grained prompting for VLM-VAD](https://arxiv.org/html/2510.02155v1) · [VERA](https://arxiv.org/pdf/2412.01095) · [HAWK (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/fca83589e85cb061631b7ebc5db5d6bd-Paper-Conference.pdf) · [FineVAU](https://arxiv.org/pdf/2601.17258) · [VAGU & GtS](https://arxiv.org/pdf/2507.21507) · [VADER](https://arxiv.org/pdf/2511.07299) · [TAU-Bench](https://arxiv.org/html/2608.05699) · [DeepSVU](https://arxiv.org/pdf/2602.18019) · [SRVAU-R1](https://arxiv.org/pdf/2602.01004) · [Text-guided fine-grained VAU](https://arxiv.org/pdf/2511.00524)
- [STG-NF](https://orhir.github.io/STG_NF/) · [Normalizing flows for pose anomaly](https://arxiv.org/pdf/2211.10946) · [MoCoDAD](https://arxiv.org/html/2307.07205v3) · [MoCoDAD repo](https://github.com/aleflabo/MoCoDAD) · [Contracting skeletal kinematics](https://www.sciencedirect.com/science/article/pii/S0031320324005685) · [Action Hints](https://arxiv.org/html/2509.11058) · [Human kinematics-inspired skeleton VAD](https://arxiv.org/pdf/2309.15662)
- [Rethinking Metrics and Benchmarks of VAD](https://arxiv.org/html/2505.19022v2) · [Is VAD Misframed?](https://arxiv.org/pdf/2605.12725) · [Localizing to Debias](https://arxiv.org/html/2608.12045) · [Exploring Background-bias (ACM MM 2019)](https://dl.acm.org/doi/10.1145/3343031.3350998) · [Scene-dependent VAD benchmark](https://www.sciencedirect.com/science/article/pii/S1110016825011342) · [Knowledge-graph scene/action decoupling](https://arxiv.org/html/2409.03236) · [CRCL](https://arxiv.org/pdf/2503.18808) · [Context-aware shortcut exploration](https://www.sciencedirect.com/science/article/abs/pii/S0031320324006289) · [X-MAN](https://arxiv.org/pdf/2106.08856) · [Explainable AD survey](https://arxiv.org/pdf/2302.06670) · [DUAL-VAD](https://arxiv.org/pdf/2509.11605)
- [Perimeter Intrusion Detection by Video Surveillance: A Survey (Sensors 2022)](https://pubmed.ncbi.nlm.nih.gov/35591289/) · [Unified Camera Tamper Detection (Sensors 2015)](https://www.mdpi.com/1424-8220/15/5/10315) · [Real-Time Adaptive Camera Tamper Detection](https://www.researchgate.net/publication/221315328_Real-Time_Adaptive_Camera_Tamper_Detection_for_Video_Surveillance) · [Rapid detection of camera tampering (JVCI 2014)](https://www.sciencedirect.com/science/article/abs/pii/S1047320314001473) · [Camera sabotage detection](https://www.researchgate.net/publication/221501357_Camera_Sabotage_Detection_for_Surveillance_Systems)
- [Kotseruba et al., Pedestrian Action Prediction Benchmark (WACV 2021)](https://openaccess.thecvf.com/content/WACV2021/papers/Kotseruba_Benchmark_for_Evaluating_Pedestrian_Action_Prediction_WACV_2021_paper.pdf) · [TCL](https://arxiv.org/pdf/2504.06292) · [ACIT](https://arxiv.org/pdf/2511.20020) · [Coupling Intent and Action](https://arxiv.org/pdf/2105.04133) · [Zero-shot pedestrian intention](https://arxiv.org/pdf/2507.21161) · [ESIA](https://arxiv.org/pdf/2604.23728) · [Group crossing intention](https://pmc.ncbi.nlm.nih.gov/articles/PMC12215624/)
- [Zelda: VLM video analytics](https://arxiv.org/pdf/2305.03785) · [Ava: agentic video analytics](https://arxiv.org/html/2505.00254v5) · [SketchQL](https://dl.acm.org/doi/pdf/10.1145/3677140) · [Technical challenges of AI in video analysis](https://memories.ai/blogs/Technical_Challenges_of_AI_in_Video_Analysis) · [WISE multimodal search](https://www.robots.ox.ac.uk/~vgg/software/wise/)

**Human factors**
- [Work exposure and vigilance decrements in CCTV surveillance (Applied Ergonomics 2014)](https://www.sciencedirect.com/science/article/abs/pii/S0003687014001847)
- [Semi-automated CCTV surveillance: system confidence, accuracy, task complexity (Applied Ergonomics 2012)](https://www.sciencedirect.com/science/article/abs/pii/S0003687012000695)
- [Pirate Stealth or Inattentional Blindness? (PLOS ONE 2014)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0086157) · [PMC mirror](https://pmc.ncbi.nlm.nih.gov/articles/PMC3897661/)
- [Vigilance (psychology)](https://en.wikipedia.org/wiki/Vigilance_(psychology)) · [IntelliSee: the 20-minute limit](https://intellisee.com/the-human-monitoring-limit-why-manufacturing-cctv-fails-every-20-minutes/) · [IntelliSee: 98% of alarms are false](https://intellisee.com/98-of-security-camera-alarms-are-false-heres-what-thats-actually-costing-you/) · [Becklar: false alarm cost](https://becklar.com/resources/monitoring/false-alarms-fatigue-cost/)
- [The Impact of False and Nuisance Alarms on Design (OSTI)](https://www.osti.gov/servlets/purl/1347158) · [Alert Fatigue in SOCs](https://www.researchgate.net/publication/389782034_Alert_Fatigue_in_Security_Operations_Centres_Research_Challenges_and_Opportunities) · [Quantifying and mitigating alarm fatigue](https://www.sciencedirect.com/science/article/abs/pii/S0951832025010907) · [Praetorian on alert fatigue](https://www.praetorian.com/security-101/alert-fatigue-and-false-positives/) · [Vectra on alert fatigue](https://www.vectra.ai/topics/alert-fatigue)

**Law and policy**
- [EU AI Act Article 5 FAQ (AI Act Service Desk)](https://ai-act-service-desk.ec.europa.eu/en/ai-act/faq/what-systems-are-prohibited-under-article-5-ai-act-eg-social-scoring-emotion-recognition) · [FPF: Red Lines](https://fpf.org/blog/red-lines-under-eu-ai-act-unpacking-the-prohibition-of-emotion-recognition-in-the-workplace-and-education-institutions/) · [Bundesnetzagentur](https://www.bundesnetzagentur.de/EN/Areas/Digitalisation/AI/08_ProhibitedPractices/start.html) · [European Commission AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) · [State of Surveillance explainer](https://stateofsurveillance.org/news/eu-ai-act-august-2026-biometric-surveillance-explainer/)

**Product context**
- [a CCTV-analytics vendor]((vendor source removed)) · internal: [01 Research Landscape](../01_RESEARCH_LANDSCAPE.md) · [03 Behaviour Catalogue](../03_BEHAVIOUR_CATALOG.md) · [06 Realism and Sensor Model](../06_REALISM_AND_SENSOR_MODEL.md) · [07 Evaluation and Algo Sandbox](../07_EVALUATION_AND_ALGO_SANDBOX.md)

---

### Verification backlog (do these before external use)

1. Obtain the current **i-LIDS / NPSA assurance scheme document** for: pass
   thresholds, the primary/secondary terminology, and per-scenario FA-rate limits.
2. Confirm **Sultani et al.'s Table 3 AUC (75.41%)** and UCF-Crime total duration.
3. Confirm the **PETS2006 spatial threshold** (the "3 m" folk rule).
4. Confirm **EU AI Act Annex III** wording and whether CNI security analytics is
   caught as a safety component.
5. Confirm **TRECVID SED** event classes and the DCR≳1.0 results, and **VIRAT**'s
   event count and duration.
6. Confirm **MEVA** annotated-hours figures and **MSAD** dataset statistics.
7. Confirm **BS EN 50131 / EN 50132** applicability and current part numbers.
8. Source the **PredPol feedback-loop critique** properly (Lum & Isaac; Ensign et
   al.) before relying on §4.4.
