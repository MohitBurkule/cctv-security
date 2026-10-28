# D01 · The Complete History and Evolution of Automated Video Surveillance Analytics (Intelligent CCTV), 1942 → 2026, and Where It Goes Next

**Dossier type:** longitudinal / institutional history. **Companion to** R01 (detection & single-camera tracking), R02 (multi-camera & re-ID), R03 (behaviour/intent/anomaly), R04 (degraded imaging & sim2real), R05 (fusion & NL retrieval), R06 (company/people ecosystem).

**Division of labour with the R-series.** R01 and R03 carry the algorithm-level
and metric-level detail (HOG/DPM/deep detectors; MOTA/IDF1/HOTA; i-LIDS scoring
mechanics; UCF-Crime numbers). This dossier deliberately does **not** re-derive
them. D01's job is the **causal industrial and institutional history**: which
funder wanted what, which company was born from which lab, which product
category died and why, which standard locked in which architecture, and what the
shape of the past implies for 2026–2035. Where R01/R03 already establish a fact
with a citation, D01 cross-references rather than re-quotes.

> **Methodological disclosure, up front.** This dossier was researched under a
> hard tool budget. The session's WebSearch allocation (200 calls, shared with
> R01–R06) was **exhausted** partway through D01's research, and the network
> egress proxy **blocked** `en.wikipedia.org`, `arxiv.org`, `nist.gov`,
> `onvif.org`, `assets.publishing.service.gov.uk` and most other non-GitHub
> hosts for direct fetching. Everything below that carries a markdown link is
> quoted from material actually retrieved. Everything that does not is marked
> **[VERIFY]** and must be confirmed before external use. There are roughly
> twenty such marks, concentrated in the standards timeline (IEC 62676, NPSA
> CAPSS), the 1960s municipal-CCTV record, and the fates of several 2000s-era
> vendors. Do not launder a [VERIFY] into a claim.

---

## 0. The thesis in one page

Automated video analytics has been reinvented, under different names, at least
six times: **VMD** (1970s), **"intelligent CCTV"** (VSAM-era research,
1997–2000), **"video content analysis / VCA"** (post-9/11 commercial,
2001–2008), **"behavioural analytics"** (2008–2015), **"AI video"**
(2016–2022), and **"video agents"** (2023–2026). Each cycle followed the same
arc:

1. **A security shock or a cost shock** creates demand for watching more cameras
   with fewer eyes.
2. **A technology becomes cheap** (transistorised comparators; the DSP; the DVR;
   the GPU; the transformer; the VLM).
3. **Vendors over-promise on the hardest capability** (intent, prediction,
   "abnormality") and under-deliver on the *boring* capability that actually
   sells (fewer false alarms, faster forensic search).
4. **Operators experience false-alarm fatigue**, the category acquires a bad
   name, the incumbent vendors consolidate or die, and the survivors quietly
   ship the narrow thing that worked.
5. **The narrow thing that worked becomes a free feature** in the next
   generation of cameras/VMS, destroying the specialist's margin.

Step 5 is the single most important commercial law in this field. **Every
analytics capability that works eventually becomes a checkbox in a camera
datasheet and stops being a business.** Line-crossing did this by ~2012.
Person/vehicle classification did it by ~2020. Licence-plate reading did it by
~2022 in most geographies. "Search this archive in English" is doing it right
now, in 2025–2026.

The corresponding scientific law: **detection got solved, association got
tractable, and semantics did not.** What a camera sees is now largely a
commodity; what it *means* is not. Everything in §14 and §16 follows from that
asymmetry.

---

## 1. Era 0 — Analogue prehistory: closed circuits with humans in the loop (1942–1969)

### 1.1 1942, Peenemünde: the founding use case was *remote presence*, not detection

The first recognisable CCTV installation had nothing to do with crime. It existed
because the thing being watched would kill the watcher.

> *"The first widely recognized security camera system was developed in 1942 by
> German engineer Walter Bruch, who designed a closed-circuit television system
> for Siemens AG to monitor V-2 rocket launches."*
> — [Lynztel, *The History of Video Surveillance: From Military CCTV to AI*](https://lynztel.com/en/blog/historia-de-los-sistemas-de-videovigilancia-del-cctv-militar-a-la-ia/)

> *"The system was installed at Test Stand VII in Peenemünde, Nazi Germany, in
> 1942, for observing the launch of V-2 rockets."*
> — [Wikipedia, *Closed-circuit television*](https://en.wikipedia.org/wiki/Closed-circuit_television) (retrieved via search snippet; direct fetch blocked)

And critically:

> *"It was purely analog technology — bulky vacuum-tube cameras — with zero
> recording capability. Monitoring had to happen live, with a human operator
> watching the screen in real time."*
> — [Lynztel](https://lynztel.com/en/blog/historia-de-los-sistemas-de-videovigilancia-del-cctv-militar-a-la-ia/)

**Why this matters for analytics.** The 1942 architecture is *synchronous*: one
camera, one screen, one human, zero latency budget, zero storage. Every
subsequent advance in surveillance is an attack on one of those four constraints
— and *analytics is specifically the attack on the "one human" constraint*.
Recording (1950s–60s) attacked storage. Multiplexing (1970s–90s) attacked the
one-camera-one-screen link and thereby *created* the operator-overload problem
that analytics exists to solve. The order matters: **multiplexing created the
market for analytics before analytics could work.** That eighteen-year gap
(roughly 1975–1993) is the origin of the field's chronic credibility deficit.

Walter Bruch's own later career is a useful hop: he went on to develop the PAL
colour television standard at Telefunken, which is to say **the man who built the
first surveillance camera also built the broadcast standard that would define
surveillance video's resolution ceiling (625 lines, 4CIF at best) for the next
fifty years.** [VERIFY — the PAL attribution is well-established but I could not
retrieve a primary source in this session; see
[Wikipedia: Walter Bruch](https://en.wikipedia.org/wiki/Walter_Bruch).] The
consequence is concrete and appears throughout R04: analytics vendors spent
1995–2010 doing pedestrian detection on interlaced, heavily-compressed, ~576i
imagery whose format was fixed by a 1960s broadcast committee.

### 1.2 1949, Vericon: the first commercial product

> *"In the United States, the first commercial closed-circuit television system
> became available in 1949 from Remington Rand and designed by CBS Laboratories,
> called 'Vericon'."*
> — [Lynztel](https://lynztel.com/en/blog/historia-de-los-sistemas-de-videovigilancia-del-cctv-militar-a-la-ia/)

Vericon's marketed use cases were industrial observation and, notably, *remote
inspection of hazardous processes* — again, remote presence rather than security.
The security framing arrives with the 1960s.

### 1.3 The 1960s: municipal CCTV and the birth of the operator-overload problem

The canonical milestones of 1960s public-space CCTV — the Metropolitan Police's
temporary installation in Trafalgar Square (1960, for a royal visit / Guy Fawkes
Night crowd), the 1968 municipal installation in Olean, New York (widely cited
as the first US city to put cameras on its main street to fight crime), and New
York City's early deployments in Times Square (1973) — are consistently reported
across the secondary literature but I was unable to fetch a primary or
encyclopaedic source for them in this session. **[VERIFY all four dates.]** `[audit 2026-09-26]` Olean confirmed: cameras on North Union Street, September 1968 ([Olean Times Herald](https://www.oleantimesherald.com/news/nation-s-first-surveillance-cameras-were-installed-in-olean/article_fa09f59d-4ce3-558d-b713-1aa287a57d7e.html)); `[audit R4 2026-09-26]` Trafalgar Square confirmed (secondary, citing National Archives file MEPO 2/9956): Met Police EMI cameras for the Thai royal state visit, **19–20 July 1960**, with a Guy Fawkes Night demonstration planned that November ([Professional Security, part 1](https://professionalsecurity.co.uk/news/case-studies/polices-1960s-cctv-experiments-part-1/)). Times Square 1973 confirmed only at secondary level: "pilot surveillance program in Times Square. Abandonned after 18 months. Only 10 arrests, all for trivial offenses" ([NYC Surveillance Camera Players timeline](https://www.notbored.org/nyc-history.html)) — an activist source; no NYPD primary found. The
secondary account is:

> *"By the 1970s, CCTV began entering public and commercial settings, with
> businesses, banks, and municipal authorities realizing the potential for
> monitoring environments to deter crime and improve public safety. During this
> decade, black-and-white cameras connected by wired systems became the norm."*
> — [DTiQ, *History of Security Cameras: How Did CCTV Evolve*](https://www.dtiq.com/blog/video-surveillance/history-of-security-cameras)

The structurally important 1960s development was not any single camera but the
**control room**: banks of monitors, one operator to many screens. Once the ratio
went above roughly 1:4, the human visual system stopped being a detector and
became a *sampler*. R03 §5.1 documents the vigilance-decrement literature that
quantifies this. The institutional response to the vigilance problem was, for
fifteen years, purely procedural (rotas, patrol patterns, guard tours). VMD was
the first technical response.

---

## 2. Era 1 — Video Motion Detection, 1972–1990: the first automation, and the first false-alarm crisis

### 2.1 What VMD actually was

VMD in its original analogue form was not image processing in any modern sense.
It was **a comparator on a sampled subset of the video waveform**: select one or
more rectangular zones of the raster by gating on line number and horizontal
timing, integrate luminance within the gate, store it, compare successive
frames/fields, and trip a relay if the difference exceeded a threshold. Early
units had a handful of zones and one or two knobs (sensitivity, delay). The
entire signal chain was analogue; the "algorithm" was a differencing circuit.

The trade press retrospective is unusually candid about what happened next:

> *"Even in the days of analogue technology, VMD offered much to high risk
> applications, though the quality of VMD performance hinged on two things:
> discriminations to filter out nuisance activations and careful installation."*
> — [SMART Security Solutions / XtraVision, *Going through the motions: looking at the history of video motion detection (VMD)*, CCTV Handbook 2007](http://www.securitysa.com/regular.aspx?pklregularid=2904)

> *"Initially, the enthusiasm amongst installers and end-users alike was matched
> only by the enthusiasm of manufacturers that seemed to suddenly fill the
> marketplace, but end-users began to experience unacceptable levels of false
> alarms, and the time to install VMD systems took too long."*
> — [SMART Security Solutions, *Going through the motions*](http://www.securitysa.com/regular.aspx?pklregularid=2904)

That paragraph, written in 2007 about the 1980s, is the template for every
subsequent hype cycle in this dossier. Read it again in §7 (the 2008–2012
disillusionment) and §13 (the 2016–2020 startup wave). The two named failure
causes — **insufficient nuisance discrimination** and **installation labour** —
are *still* the two leading causes of analytics project failure in 2026. Nothing
about deep learning changed the second one at all.

### 2.2 What problem drove it, what tech enabled it

- **Problem:** the 1970s spread of multiplexers and time-lapse VCRs meant one
  operator nominally "covered" 8–16 cameras, and tape was expensive. VMD was
  sold on two value propositions: *alert the sampling human*, and *don't record
  empty scenes*.
- **Enabler:** cheap analogue comparators, then (mid-1980s) 8-bit
  microcontrollers and the first frame-store ICs, which made multi-zone
  differencing and simple persistence/size filters economic.
- **The recording tie-in:** *"motion detection technology also became
  cost-effective, reducing storage needs by recording only when activity is
  detected"* — [DTiQ](https://www.dtiq.com/blog/video-surveillance/history-of-security-cameras),
  and later *"In the 1990s, digital multiplexing let a series of cameras record
  simultaneously with time-lapse and motion-only options"*
  — [DTiQ](https://www.dtiq.com/blog/video-surveillance/history-of-security-cameras).

**The commercially decisive fact about VMD is that it succeeded at the storage
job and failed at the alerting job.** "Record on motion" is the single most
widely deployed video analytic in history — it is on essentially every DVR and
NVR ever sold — and nobody calls it analytics, because its false positives are
merely *wasteful* rather than *alarming*. "Alarm on motion" shares the same
algorithm and the same false positives, but its false positives cost a guard
patrol. **Same detector, two cost functions, two completely different market
outcomes.** This is the earliest and cleanest demonstration of R03's central
claim that the false-alarm *cost model*, not the detector, determines
deployability.

### 2.3 What made VMD obsolete — and what did not

Obsolete: single-threshold luminance differencing with no object model; per-zone
manual tuning as the only configuration mechanism; relay-contact outputs as the
only integration path.

**Not obsolete, ever:** the *idea* of VMD as a cheap pre-filter. In 2026, a
large fraction of edge deep-learning pipelines still gate the neural network on a
motion/change signal to save compute, and a large fraction of cloud pipelines
still use camera-side motion events to decide what to upload. R01 §2.1 notes that
background subtraction is *"still shipping"* — the reason is economic, not
scientific. **The pre-filter survives because bandwidth and watts are still
scarce even when FLOPs are not.**

---

## 3. Era 2 — The digital transition, 1990–2000: DVRs, DSPs, and the conditions for real analytics

Three enabling shifts, none of them about algorithms:

1. **Digitisation of storage.** The DVR replaced the time-lapse VCR, which made
   *random access* to archive possible for the first time. Random access is the
   precondition for forensic search, which is the precondition for the metadata
   business model that IBM would articulate in 2004 (§5.2).
2. **Compression standards.** MJPEG then MPEG-4 then (2003) H.264 made
   networked video economic. Compression is also the field's great unacknowledged
   adversary: every analytic after 1995 operates on *decoded lossy video with
   motion-compensation artefacts*, which is why R04 exists.
3. **The DSP.** Texas Instruments' and Philips' video DSPs put roughly a
   general-purpose-CPU's worth of integer throughput next to the sensor. This
   created the *on-camera analytics* architecture that dominated 2005–2015 and
   then largely died (§7.4).

By the late 1990s, therefore: the video was digital, addressable, networked, and
there was silicon at the edge. The research community walked into that
environment with a specific, generously funded agenda.

---

## 4. Era 3 — DARPA VSAM (1997–2000): where the modern field was actually invented

### 4.1 The programme

> *"Under the three-year Video Surveillance and Monitoring (VSAM) project
> (1997-1999), the Robotics Institute at Carnegie Mellon University (CMU) and
> the Sarnoff Corporation developed a system for autonomous Video Surveillance
> and Monitoring."*
> — [CMU Robotics Institute, *A System for Video Surveillance and Monitoring* (CMU VSAM Final Report)](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)

> *"The technical approach uses multiple, cooperative video sensors to provide
> continuous coverage of people and vehicles in a cluttered environment."*
> — [CMU VSAM Final Report](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)

> *"This work was funded by the DARPA Image Understanding under contract
> DAAB07-97-C-J031, and by the Office of Naval Research under grant
> N00014-99-1-0646."*
> — [CMU VSAM Final Report](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)

> *"The thrust of CMU research under the DARPA Video Surveillance and Monitoring
> (VSAM) project is cooperative multi-sensor surveillance to support battlefield
> awareness."*
> — [CMU VSAM Final Report](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)

Read the last quote carefully. **The modern intelligent-CCTV stack was specified
as a battlefield-awareness system, not a crime-prevention system.** Its
requirements were: wide-area coverage from few sensors, automatic hand-off
between cameras, geo-registration onto a common terrain model, and classification
of *human vs vehicle* at long range. It was *not*: low false-alarm-rate alerting
in a retail store, or evidential-quality identification. The civilian industry
inherited the architecture and then spent a decade discovering that the
requirements were different — a mismatch that recurs in §15 with Project Maven.

### 4.2 What VSAM actually established — the template that lasted 15 years

The VSAM pipeline is, essentially unchanged, the architecture of every commercial
VCA product from 2001 to about 2015:

1. **Adaptive background modelling** per pixel → foreground blobs.
2. **Blob tracking** with a simple motion model and appearance template.
3. **Classification** of the tracked blob into {human, group of humans, vehicle,
   clutter} using shape/size/dispersedness features plus a small neural net or
   linear classifier.
4. **Geo-registration**: map image coordinates to a site model so that tracks
   from multiple cameras live in one coordinate frame.
5. **Multi-camera hand-off / sensor tasking**: slave a PTZ to a wide-angle
   detection.
6. **A symbolic event layer** on top of the tracks (enters region, stops, meets).

Every one of those six is still a module name in commercial products. Layers 1–3
were replaced wholesale by deep learning after 2014 (R01 §2). Layer 4 is still,
in 2026, the most under-appreciated and most-skipped step, and skipping it is the
main reason cross-camera analytics degrades (R02). Layers 5–6 are where the
field's real, unsolved problem lives.

**What VSAM proved:** that the pipeline could be built and run in real time on
1990s hardware over a real site. **What VSAM did not address:** how often it
would be wrong per camera per day, and what that costs. There was no
false-alarm-rate-per-camera-hour figure of merit in the civilian sense, because
in a battlefield-awareness framing a human analyst was always going to
adjudicate. **The civilian industry adopted the pipeline and discarded the
analyst, and that is the original sin of commercial video analytics.**

### 4.3 The Sarnoff hop, and why it matters

The industrial partner, **Sarnoff Corporation** (the former RCA Labs, Princeton),
is the single most productive node in this field's genealogy. Sarnoff's
video-processing lineage produced the pyramid-based image-alignment and
video-mosaicking work that underpins (a) electronic image stabilisation in
surveillance cameras, (b) aerial video registration for WAMI (§15.2), and (c) the
Acadia vision processor family. Sarnoff's assets were split between **SRI
International** (acquired 2011) and its own spin-outs. **[VERIFY the SRI
acquisition date and the exact Acadia lineage — I could not fetch a primary
source in this session.]** The practical point: **the aerial/ISR branch and the
fixed-CCTV branch of video analytics share a common ancestor in Sarnoff's
registration work**, which is why the two communities keep rediscovering each
other's tricks (camera-motion compensation in BoT-SORT, R01 §3.4, is a direct
descendant of aerial-registration thinking).

---

## 5. Era 4 — The post-9/11 commercial boom, 2001–2008

### 5.1 ObjectVideo: the archetype, and the patent war

ObjectVideo is the most consequential company in the history of this field, and
it never became a large product business. It was founded out of DARPA-adjacent
work in the Washington DC beltway area and productised the VSAM-style pipeline as
**VEW (Video Early Warning)** and later **OV Ready**, with the configuration
metaphor that defined the entire category: **the drawn tripwire and the drawn
region of interest, with rules attached.**

That metaphor — *draw a line, choose a direction, choose an object class, get an
alarm* — is ObjectVideo's real legacy. It is still the primary UI of Axis,
Bosch, Hanwha, Hikvision, Dahua, Avigilon, Genetec and Milestone analytics in
2026. **The industry standardised on ObjectVideo's interaction model before it
standardised on anything else, including ONVIF.**

ObjectVideo then converted its patent estate into its business model:

> *"ObjectVideo filed a lawsuit on April 11, 2011, against three top IP video
> surveillance camera manufacturers—Bosch, Sony, and Samsung—alleging
> infringement of ObjectVideo's intellectual property in the area of video
> analytics."*
> — [SecurityInfoWatch, *ObjectVideo sues Bosch, Sony and Samsung*](https://www.securityinfowatch.com/video-surveillance/news/10485600/objectvideo-sues-bosch-sony-and-samsung-over-alleged-patent-infringement-in-the-area-of-video-content-analytics)

> *"ObjectVideo later filed a U.S. trade complaint with the International Trade
> Commission (ITC) against Sony, Samsung Techwin, and Robert Bosch, alleging
> infringement of patents for video analytics software and seeking to block
> imports of their video products. The patents in the suit dealt with video
> analytic software for security camera systems, such as metadata, tripwire and
> slip-and-fall technology."*
> — [Bloomberg, *Sony, Samsung Techwin Targeted by ObjectVideo in ITC Patent Case*](https://www.bloomberg.com/news/articles/2011-06-30/sony-samsung-techwin-targeted-by-objectvideo-in-itc-patent-case)

Outcomes:

> *"Sony signed a patent license agreement with ObjectVideo, and as a result,
> ObjectVideo asked the ITC to terminate its investigation against Sony, with
> the two companies settling all outstanding claims."*
> — [Security Sales & Integration, *ObjectVideo, Sony Enter Into Patent License Agreement*](https://www.securitysales.com/news/objectvideo-sony-enter-into-patent-license-agreement/28451/)

> *"A day before the July 18 ITC trial began, ObjectVideo filed an unopposed
> motion to terminate the ITC's investigation against Samsung."*
> — [Security Sales & Integration, *ObjectVideo Drops Patent Infringement Case Against Samsung*](https://www.securitysales.com/news/objectvideo-drops-patent-infringement-case-against-samsung/)

And the strategic pivot that followed:

> *"In new strategy, ObjectVideo agrees to license its video analytic patents to
> American Dynamics"*
> — [Government Security News](https://www.gsnmagazine.com/article/25564/new_strategy_objectvideo_agrees_license_its_video_)

**The lesson, and it is brutal.** ObjectVideo's licensing programme
*accelerated the commoditisation it was trying to monetise.* Once every major
camera OEM held a licence to tripwire/ROI/metadata patents, every major camera
OEM shipped tripwire/ROI/metadata for free in firmware. The patent estate
converted a product company into a royalty stream and then the royalty stream
matured. The residual business was later absorbed into Alarm.com's Avigilon-era
orbit **[VERIFY — I could not retrieve a source for ObjectVideo's final
disposition in this session; the commonly-cited outcome is the 2016 transfer of
the ObjectVideo product business to Alarm.com, with the patent entity continuing
separately as ObjectVideo Labs]**.

Also note *what was patented*: **"metadata, tripwire and slip-and-fall"**
([Bloomberg](https://www.bloomberg.com/news/articles/2011-06-30/sony-samsung-techwin-targeted-by-objectvideo-in-itc-patent-case)).
"Slip-and-fall" in 2011 is "person down" in 2026 (R03 §3.9). The category of
*things customers ask for* has barely moved in fifteen years. What moved is the
accuracy at which they can be delivered.

### 5.2 IBM Smart Surveillance System (S3): the correct architecture, a decade early

IBM Research's S3 is the most intellectually important commercial system of the
2000s because it got the *data model* right while everyone else was arguing about
detectors.

> *"S3-R1 (The IBM smart surveillance system-release 1) was published in October
> 2004 by Arun Hampapur, Lisa Brown, Jonathan Connell, and Yingli Tian."*
> — [ResearchGate: *S3-R1: The IBM smart surveillance system-release 1*](https://www.researchgate.net/publication/261847464_S3-R1_The_IBM_smart_surveillance_system-release_1)

> *"The system comprises: (1) the Smart Surveillance Engine which provides the
> front end video analysis capabilities; (2) Middleware for Large Scale
> Surveillance (MILS) which provides data management and retrieval
> capabilities."*
> — [Springer, *IBM smart surveillance system (S3): event based video surveillance system with an open and extensible framework*, Machine Vision and Applications](https://link.springer.com/article/10.1007/s00138-008-0153-z)

> *"The IBM S3 system provides not only the capability to automatically monitor a
> scene but also the capability to manage the surveillance data, perform event
> based retrieval, receive real time event alerts thru standard web
> infrastructure and extract long term statistical patterns of activity."*
> — [Springer, MVA](https://link.springer.com/article/10.1007/s00138-008-0153-z)

> *"IBM:MILS can convert video event information into relational tables, enabling
> SQL-based querying across third-party relational databases."*
> — [Springer, MVA](https://link.springer.com/article/10.1007/s00138-008-0153-z)

And the framing, from the paper title itself: **"From Transactional Systems to
Observational Systems"**
([Academia.edu copy](https://www.academia.edu/5582040/S3_The_IBM_Smart_Surveillance_System_From_Transactional_Systems_to_Observational_Systems)).

**Three claims IBM made in 2004 that the market only accepted in ~2020:**

1. *Video analytics is a database problem.* The output of the vision layer is
   rows. The product is the query. This is exactly the architecture of Verkada,
   Ambient.ai, Coram and the NVIDIA VSS blueprint (§16) two decades later.
2. *Analytics must be an open, extensible framework, not a fixed rule set.*
   ONVIF Profile M (§11.3) is this argument, standardised, seventeen years later.
3. *Long-term statistics matter as much as real-time alerts.* The "how many
   people, where, when" business — retail footfall, occupancy, queue management
   — turned out to be a far larger and more durable revenue pool than security
   alerting. IBM saw it first and did not capture it.

**Why IBM did not win it.** S3 needed a server room per site, systems
integrators who understood J2EE, and a customer with a data-warehouse budget. The
security channel in 2004 consisted of installers who terminated coax. The
architecture was right and the distribution was impossible. **This is the single
most common way good video analytics dies: the right architecture arrives before
the channel that can sell it.**

### 5.3 The 2001–2008 cohort, and what happened to each

Post-9/11 money, plus the DVR-to-IP transition, produced a dense field. The
fates are instructive because they cluster into exactly three outcomes:
*absorbed by a hardware OEM*, *absorbed by a VMS/PSIM*, or *dead*.

**NICE Systems (NiceVision).** An Israeli call-recording company that entered
video. *"NICE's physical offering consisted primarily of VMS software, PSIM/
situation management software (originally acquired from Orsus in 2009), and video
analytics software"*; NICE had *"enhanced its NiceVision video surveillance
solution to include crowd detection and camera tampering content analytics
applications"* — [IPVM, *NICE Is Out Of the Video Surveillance Business / Now
Qognify*](https://ipvm.com/reports/nice-is-out-of-the-video-surveillance-business).
NICE **exited** in 2015: *"Battery Ventures established an independently
operating business called Qognify to replace the Nice Security brand following
the acquisition of NICE Systems' Physical Security Business Unit"* — [IPVM](https://ipvm.com/reports/nice-is-out-of-the-video-surveillance-business);
see also [IFSEC Insider](https://www.ifsecglobal.com/video-surveillance/qognify-launches-object-origin-acquiring-nice-systems-physical-security-business-unit/).
Qognify was then sold onward: *"Hexagon AB announced the acquisition of Qognify
on December 19, 2022… Qognify was acquired by Hexagon from tech company Battery
Ventures"* — [Hexagon press release](https://hexagon.com/company/newsroom/press-releases/2022/hexagon-strengthens-its-physical-security-and-incident-management-capabilities-with-the-acquisition-of-qognify);
[Help Net Security](https://www.helpnetsecurity.com/2022/12/20/hexagon-qognify/).
**Trajectory: analytics → VMS+PSIM → private equity → geospatial/public-safety
conglomerate.** Three owners in seven years is what a category looks like when
it has value but no growth.

**Verint.** The other Israeli lineage (Comverse family), which built
**Verint Situational Awareness** — *"an open, unified software solution that
helps enhance industry-standard workflows and supports operators in responding to
both routine and emergency events… unifying a wide range of sensors and systems
into a centralized, intuitive security and situation intelligence solution"*
— [Verint CIS](https://cis.verint.com/product/situational-intelligence/situational-awareness-platform/).
Note the language: by the 2010s Verint had stopped selling *detection* and
started selling *situational awareness* — i.e. it retreated up the stack to
workflow, where the margins were defensible against camera-OEM commoditisation.
Verint's video business was subsequently separated from its customer-engagement
business **[VERIFY the exact corporate separation dates — the Cognyte spin-off
(2021) covered intelligence analytics; the physical-security video line's final
home needs confirmation]**.

**ioimage.** The purest expression of the *edge-DSP analytics* thesis: put the
VSAM pipeline on a TI DSP inside an encoder or camera, sell it as an
"intelligent video appliance" with very low false alarms on perimeter tasks. It
was acquired by **DVTel** in 2010, which was itself acquired by **FLIR** in 2015,
whose security business was later sold to **Teledyne**'s orbit and partly to
**Motorola Solutions** **[VERIFY this entire chain — I could not retrieve
sources for the ioimage→DVTel→FLIR→(Teledyne/Motorola) sequence in this
session]**. The technology thesis was sound for one narrow task (outdoor
perimeter, fixed camera, clear sterile zone) and was defeated not by a competitor
but by **Moore's law moving the compute to a different place** (§7.4).

**Vidient.** The clearest documented death in the cohort:

> *"Vidient was a spin-off of CA-based NEC labs, with SmartCatch software that
> had been in beta form at several high-profile facilities including the San
> Francisco International Airport."*
> — [SecurityInfoWatch, *Intelligence and Convergence: Leading the way at ASIS*](https://www.securityinfowatch.com/video-surveillance/article/10592117/intelligence-and-convergence-leading-the-way-at-asis)

> *"Vidient's operations ceased in November 2010; originally a spin-out of NEC in
> 2003, Vidient raised over $30 Million USD of venture funding."*
> — [IPVM, *Vidient's Analytics Acquired by Agilence*](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence)

> *"Agilence acquired Vidient's video analytic technology after Vidient shut down
> operations, planning to incorporate it into their solutions for retail and
> transportation markets."*
> — [Business Wire, *Agilence Purchases Assets of Video Analytics Company Vidient Systems*](https://www.businesswire.com/news/home/20110412005330/en/Agilence-Purchases-Assets-Video-Analytics-Company-Vidient)

**$30M of venture funding, an SFO deployment, and a zero.** Vidient is the
canonical case study for the proposition that *a marquee airport reference
account is not a business*. Airports buy one system, tender it once a decade,
demand endless customisation, and generate no repeatable product.

**Cernium.** *"Cernium introduced Perceptrak, a solution that incorporates
behavior recognition into a video management suite"*
— [SecurityInfoWatch](https://www.securityinfowatch.com/video-surveillance/article/10592117/intelligence-and-convergence-leading-the-way-at-asis).
Cernium then repeatedly repositioned — see [IPVM, *Cernium Shifts Strategy Again
(CheckVideo)*](https://ipvm.com/reports/cernium-shifts-strategy-again-checkvideo)
— ending as **CheckVideo**, a *verified-alarm service for the small-business
market*. **That pivot is the single most under-studied success pattern in this
history:** when enterprise analytics margins collapsed, the surviving value was in
**alarm verification as a monitoring-centre service**, where the analytic doesn't
have to be right, it only has to be right *often enough to beat a human
pre-screening every alarm*. The business is sold per-camera-per-month to a
central station, not per-licence to an integrator. Everything about Verkada's and
Ambient's economics in §13 is a rediscovery of CheckVideo's insight.

**IntelliVid.** *"Tyco International acquired the assets of IntelliVid, a
developer of retail-focused intelligent video analysis solutions, which since
2003 had provided retail customers with business intelligence applications using
video analytics"*
— [Security Systems News, *Tyco acquires retail-focused analytics vendor
IntelliVid*](https://www.securitysystemsnews.com/article/tyco-acquires-retail-focused-analytics-vendor-intellivid).
IntelliVid is important because it was **retail-first, loss-prevention-focused,
and business-intelligence-framed** from 2003. Tyco/Sensormatic folded it into the
EAS-and-shrink business. Retail analytics thereafter evolved almost completely
separately from security analytics, with its own metrics (conversion, dwell,
shrink) and its own vendors, and it has been consistently more profitable.

**3VR.** *"3VR started out being a facial recognition and video management
solution for many markets, but became more focused with a product optimized for
banking"* — [IPVM, *3VR Firesale to Identiv*](https://ipvm.com/reports/3v-identiv).
The blunt epitaph, from the same publication: *"3VR bet on facial recognition and
video analytics and failed, along with companies like Cernium, Object Video, and
Vidient"* — [IPVM](https://ipvm.com/reports/3v-identiv). 3VR's asset sale to
Identiv closed the 2000s analytics cohort.

**Agent Vi (Agent Video Intelligence).** Israeli; distinctive for a genuinely
different architecture — **distributed analytics**, splitting the pipeline between
camera-side pre-processing and server-side event detection, to get server-class
rules at edge-class cost. It survived longer than the cohort and was consolidated
into a Nordic buyer: *"In October 2021, Irisity acquired Agent Vi to become the
leading global provider of open architecture, video analytics software"*, for
*"SEK 650 million"* — [Irisity, *About Us*](https://irisity.com/about-us/);
[Security Systems News](https://www.securitysystemsnews.com/article/agent-vi-acquired-by-swedish-ai-company-irisity).

**Siemens Siveillance, Honeywell, Pelco.** The large industrial incumbents all
fielded analytics lines (Siveillance Vantage/VMS; Honeywell's Active Alert and
later Intelligent Video; Pelco's Analytics Suite / Sarix-era on-camera
analytics), typically by OEM-ing a specialist engine rather than building one.
**[VERIFY all product names and dates — I could not retrieve sources for the
Siveillance, Honeywell and Pelco analytics lines in this session.]** The
structural point is documented elsewhere in this dossier: the incumbents' role
was to *distribute* other people's analytics, which is precisely how tripwire
became free. Pelco's later trajectory — sold by Schneider Electric to Transom
Capital (2019), then acquired by Motorola Solutions (2020) **[VERIFY]** — is
representative of the analogue-era leaders' decline.

**Ioimage/Vidient/Cernium/3VR/ObjectVideo in one sentence:** of the six
best-funded pure-play video-analytics companies of the 2000s, **none became a
standalone durable business**; the two that returned capital did so through
patents (ObjectVideo) and a services pivot (Cernium/CheckVideo), not through
enterprise software licences.

### 5.4 BRS Labs / AISight: the cautionary tale, and a fair reading of it

BRS Labs sold the most ambitious claim in the industry's history: **unsupervised
behavioural learning that needs no rules.**

> *"Behavioral Recognition Systems, Inc. (BRS Labs) was founded in 2005 and sold
> video analytic software that allows linked video cameras or other systems to
> recognize certain abnormal or suspicious events chosen by the user. The company
> marketed proprietary artificial intelligence software called 'AISight' to
> detect suspicious behavior in video surveillance footage."*
> — [SEC Litigation Release 24013, *Ray C. Davis and Behavioral Recognition Systems, Inc., n/k/a Giant Gray, Inc.*](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm)

The company ended in an SEC fraud action:

> *"Ray C. Davis and Behavioral Recognition Systems, Inc. (now known as Giant
> Gray, Inc.) engaged in a fraudulent scheme that began as early as March 2010,
> soliciting over $28 million from investors in seven equity security offerings
> between January 2013 and July 2015."*
> — [SEC Litigation Release 24013](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm)

> *"BRS and Davis secretly diverted millions of dollars of investor money for
> Davis's personal use, including to purchase ancient jewelry, gold, and other
> artifacts."*
> — [SEC complaint (PDF)](https://www.sec.gov/files/litigation/complaints/2017/comp24013.pdf)

> *"BRS and Davis allegedly covered their tracks using fake invoices in the names
> of two shell companies Davis controlled, the Blackstone Group, Inc. and Afcon
> Communications, Inc."*
> — [SEC complaint (PDF)](https://www.sec.gov/files/litigation/complaints/2017/comp24013.pdf)

**Be precise about what failed.** The SEC action is about **securities fraud, not
about the algorithm**. It is intellectually lazy — and factually unsupported — to
say "AISight failed because unsupervised anomaly detection doesn't work." What
the record supports is:

- The **commercial** claim failed. A rules-free, self-learning system that you
  point at any camera and which then tells you what is abnormal, is a claim about
  *the customer's cost of configuration going to zero*. That is what sold; that
  is what did not deliver, for a reason R03 §3 explains in detail: **statistical
  rarity is not operational significance.** A cleaner at 3am is rare and
  irrelevant. A reconnaissance walk-past at 2pm is common-looking and relevant.
  An unsupervised model optimises rarity.
- The **technical** claim was partly real and has been vindicated in a narrow
  form. "Learn the scene's normal motion patterns and flag departures" is a
  genuinely useful *triage* signal in fixed-camera, high-camera-count estates —
  and it is exactly what modern trajectory-based and scene-conditioned anomaly
  methods do (R03 §3.11, §3.6). The 2026 version of AISight's pitch, done
  honestly, is "**unsupervised prior + a VLM to adjudicate**". The prior finds
  candidates; the language model decides whether the candidate is *interesting*.
  BRS had the first half and nothing for the second half, so every candidate went
  to the operator.
- The **evaluation** claim failed hardest. Nobody could measure AISight, because
  "abnormal" had no ground truth, so procurement had no way to fail it. R03 §2
  shows why i-LIDS-style event-level scoring at a specified false-alarm rate per
  camera-hour is the only defence. **An unfalsifiable product specification is a
  fraud vector regardless of the founder's intent.** That is the durable lesson.

---

## 6. Era 5 — The UK and European institutional strand

### 6.1 The UK: PSDB → HOSDB → CAST, and the i-LIDS instrument

Britain's distinctive contribution to this field was not a product; it was **an
evaluation regime**, built because the UK had the highest camera-per-capita
density in the Western world and a Home Office research branch willing to
sequester data.

> *"The Home Office Scientific Development Branch (HOSDB) evaluates intelligent
> CCTV and video-based detection systems (VBDS) for security and policing
> purposes. In order to be able to rapidly and reliably assess the performance of
> VBDS, HOSDB in partnership with the Security Service has produced a video test
> library, i-LIDS (Imagery Library for Intelligent Detection Systems), a sample
> of which was released on DVD in 2005."*
> — [Imagery Library for Intelligent Detection Systems (i-LIDS): A Standard for Testing Video Based Detection Systems, IEEE](https://ieeexplore.ieee.org/document/4123801)

> [historical quote; released library has five] *"i-LIDS is currently focused on four scenarios: Abandoned Baggage Detection,
> Parked Vehicle Detection, Doorway Surveillance, and Sterile Zone Monitoring.
> Each scenario contains a variety of 'alarm' and 'non-alarm' events."*
> — [i-LIDS standard paper](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)
>
> `[audit 2026-09-26]` The released library has **five** scenarios: the four event-detection ones above plus **Multiple-Camera Tracking** ([i-LIDS User Guide](https://www.securityindustry.org/wp-content/uploads/2017/08/iLids-User-Guide.pdf)).

> *"The i-LIDS datasets are widely regarded as the most comprehensive of their
> kind and have achieved substantial recognition since their launch in 2006."*
> — [i-LIDS brochure, UK Government](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf) (retrieved via search snippet; direct fetch blocked by egress proxy)

> *"The i-LIDS User Guide was produced by CAST as part of a programme of research
> and development funded and directed by the Centre for the Protection of
> National Infrastructure (CPNI)."*
> — [i-LIDS User Guide (PDF)](https://www.securityindustry.org/wp-content/uploads/2017/08/iLids-User-Guide.pdf)

R03 §2.1–2.3 covers the institutional lineage (PSDB → HOSDB → CAST; CPNI → NPSA)
and the 10-second-window scoring protocol in full, and I do not repeat it. The
**historical** significance for D01 is fourfold:

1. **i-LIDS made "does it work?" a procurement question with an answer.** Before
   2006, an integrator's only evidence was a vendor demo on the vendor's footage.
   After 2006, a UK CNI buyer could require a scenario-specific, independently
   scored result on sequestered video. This is the only place in the field's
   history where the buyer side got structurally stronger.
2. **It created a moat for the vendors who invested in passing it.** Ipsotek,
   Digital Barriers, ioimage and a handful of others built UK CNI businesses
   substantially on i-LIDS-family approval. Approval regimes always
   professionalise a market *and* raise its barriers to entry; both effects are
   real.
3. **It froze the taxonomy.** Because the corpus has four scenarios, UK CNI
   tenders have specified those four scenarios for twenty years. Abandoned
   baggage, parked vehicle, doorway, sterile zone. The regime that made analytics
   accountable also made it *conservative*, and there is still no comparable
   sequestered corpus for, say, aggression detection or hostile reconnaissance.
4. **Access control killed its scientific influence.** i-LIDS is the most
   operationally representative surveillance corpus ever built and the academic
   literature barely uses it, because you cannot download it. Compare with
   UCSD/Avenue/ShanghaiTech, which are trivially downloadable, tiny, and
   therefore define the published state of the art (R03 §3.4). **Open, bad data
   beats closed, good data at setting a research agenda — every time.**

### 6.2 The UK vendors: Ipsotek, Digital Barriers, BAE/Detica

**Ipsotek.** *"Ipsotek was established in 2001 and based in London"*; its
*"scalable AI platform called VISuite… enables users to efficiently manage
automatically-generated alerts in real-time, and can be used across a range of
use cases including crowd management, smoke detection, intrusion detection,
perimeter protection, number plate recognition and traffic management"*
— [Ipsotek profile, International Security Journal](https://internationalsecurityjournal.com/security-business-index/ipsotek/);
[Mergr](https://mergr.com/company/ipsotek). Note that the task brief's "founded
2004, Kingston University" framing did not survive checking: the retrieved
sources say **2001** and make no Kingston connection. **[VERIFY the academic
provenance claim; the founding date per retrieved sources is 2001, not 2004.]**
Ipsotek's exit: *"Ipsotek was acquired by Atos… the acquisition was completed on
April 20, 2021"*, positioned as Atos reinforcing *"its leading position in the
Edge and Computer Vision market"*
— [Atos press release](https://atos.net/en/2021/press-release_2021_04_20/atos-reinforces-its-leading-position-in-the-edge-and-computer-vision-market-through-the-acquisition-of-ipsotek);
[Consultancy.uk](https://www.consultancy.uk/news/27670/atos-acquires-video-analytics-software-provider-ipsotek).
It now trades as *"Ipsotek, an Eviden business"*
— [LinkedIn](https://www.linkedin.com/company/ipsotek-ltd). **Trajectory:
specialist analytics → IT-services conglomerate's edge-computing story.** The
same trajectory as Qognify→Hexagon: analytics is worth more as a *component of a
systems-integration narrative* than as a product line.

**Digital Barriers**, and a genuinely revealing hop:

> *"SafeZone-edge derives from a product that was brought into Digital Barriers
> with the acquisition of Keeneo, a video analysis business based in
> Sophia-Antipolis, France."*
> — [Digital Barriers support: *What is SafeZone-edge?*](https://safezone-support.digitalbarriers.com/support/solutions/articles/4000019371-what-is-safezone-edge-)

Keeneo is the hop that connects the UK commercial strand to the French public
research strand:

> *"Keeneo was created in July 2005 for the industrialization and exploitation of
> Orion and Pulsar results in video analytic, including the VSIP library. Keeneo
> was bought by Digital Barriers in August 2011 and is now independent from
> Inria."*
> — [Inria Pulsar activity report: *Software Engineering for Activity Recognition*](https://raweb.inria.fr/rapportsactivite/RA2010/pulsar/uid14.html)

> *"VSIP is a library of real-time video understanding modules that was developed
> in the former project team Orion. VSIP is an activity monitoring framework
> enabling behavior recognition in different environments, and it separates
> algorithms from a priori knowledge to allow end-users to actively participate in
> the development of a new application."*
> — [Inria activity report](http://www-sop.inria.fr/stars/Documents/Activity%20Report/FullActivityReportStars2012.html)

> *"In 2005, Monique Thonnat created Keeneo together with other members of the
> Orion team, a start-up specialized in video surveillance in charge of the
> industrialization of the videosurveillance platform VSIP developed by the Orion
> team."*
> — [Monique Thonnat, Inria](http://www-sop.inria.fr/members/Monique.Thonnat/Monique.Thonnatfr.html)

So: **Inria Orion (Thonnat, Brémond) → VSIP → Keeneo (2005) → Digital Barriers
(2011) → SafeZone-edge**, and Inria Orion → Pulsar → **STARS** continues as the
lab today ([STARS 2024 activity report](https://radar.inria.fr/report/2024/stars/index.html)).
The *"separates algorithms from a priori knowledge"* design principle in VSIP is
the same principle IBM stated as *"open and extensible framework"* and ONVIF
later standardised as Profile M. **Three independent groups converged on
"decouple the detector from the semantics" between 2004 and 2021, and the
industry still mostly ships them coupled.**

Digital Barriers subsequently abandoned video entirely: *"Digital Barriers
offloads video unit, changes focus to Thruvision screening"* —
[Sharecast](https://www.sharecast.com/news/aim-bulletin/digital-barriers-offloads-video-unit-changes-focus-to-thruvision-screening--2902970.html);
*"Thruvision, which became the group's trading name, is a camera technology used
by police or security forces for 'people-screening'"* —
[Sharecast](https://www.sharecast.com/news/aim-bulletin/digital-barriers-offloads-video-unit-changes-focus-to-thruvision-screening--2902970.html).
A listed UK analytics champion concluded that **terahertz body-scanning hardware
was a better business than video analytics software.** That is a datapoint about
the category, not about the company.

**BAE Systems Detica.** Detica (acquired by BAE in 2008, later BAE Systems
Applied Intelligence) is the UK's data-analytics-for-government node and appears
in CCTV programmes principally as an integrator and data-fusion layer rather than
a computer-vision developer. **[VERIFY — I could not retrieve sources on
Detica's specific video-analytics work in this session. Do not assert a Detica
CV capability without evidence.]**

### 6.3 The EU framework programmes: ADVISOR → PRISMATICA → CARETAKER → SAMURAI → INDECT

The EU strand is distinctive in three ways: it was **transport-led**, it was
**consortium-led** (so every project shipped a demonstrator and a deliverable
rather than a product), and it collided with **fundamental-rights politics** in a
way the US programmes did not.

**ADVISOR** (FP5) — *"Annotated Digital Video for Intelligent Surveillance and
Optimised Retrieval"*:

> *"ADVISOR is an automated visual surveillance system for metro stations…
> ADVISOR allows the analysis of both real-time and recorded video feeds from
> surveillance cameras and generates alerts of unusual behaviour or dangerous
> conditions. ADVISOR was successfully deployed and tested in Spain and Belgium."*
> — [CORDIS, *Automated visual surveillance systems | ADVISOR Project*](https://cordis.europa.eu/article/id/81538-automated-visual-surveillance-systems);
> see also [TRIMIS project record](https://trimis.ec.europa.eu/project/annotated-digital-video-surveillance-and-optimised-retrieval)

Note the name: **"annotated… and optimised retrieval"**. ADVISOR, like IBM S3,
put *retrieval* in the title in ~2000. Retrieval — not alerting — is the thing
the field would eventually be good at.

**PRISMATICA** — *"The Proactive Integrated Systems for Security Management by
Technological, Institutional, and Communication Assistance (PRISMATICA) has
deployed video analytic systems in France… PRISMATICA system has been proposed to
improve passenger security and safety in the public transport system"*
— [PRISMATICA: A multi-sensor surveillance system for public transport networks](https://www.researchgate.net/publication/4095097_PRISMATICA_A_multi-sensor_surveillance_system_for_public_transport_networks).
PRISMATICA's distinctive element was **institutional and communication
assistance** in the title: it treated the control room and staff procedures as
part of the system. The EU strand consistently took human factors more seriously
than the US strand, which is why R03 §5's human-factors material has more European
provenance than American.

**CARETAKER** — *"The Content Analysis and Retrieval Technologies to Apply
Knowledge Extraction to Massive Recording (CARETAKER) project was deployed in
Italy"*
— [Understanding Transit Scenes: A Survey on Human Behavior-Recognition Algorithms (PDF)](https://www.candamo.org/articles/understanding-transit-scenes-a-survey-on-human-behavior-recognition-algorithms.pdf).
CARETAKER's framing — *knowledge extraction from massive recording* — is the
mid-2000s recognition that the archive, not the live feed, is where the data is.

**SAMURAI** (FP7, 2008–2011) — *"Suspicious and Abnormal Behaviour Monitoring
Using a Network of Cameras & Sensors for Situation Awareness Enhancement"*:

> *"The aim of SAMURAI is to develop and integrate an innovative intelligent
> surveillance system for robust monitoring of both inside and surrounding areas
> of a critical public infrastructure site. SAMURAI is to employ networked
> heterogeneous sensors rather than CCTV cameras alone so that multiple
> complementary sources of information can be fused to create a visualisation of
> a more complete 'big picture' of a crowded public space."*
> — [CORDIS, SAMURAI project fact sheet (FP7, project ID 217899)](https://cordis.europa.eu/project/id/217899);
> see also [CORDIS results in brief](https://cordis.europa.eu/article/id/85970-developing-intelligent-video-surveillance)
> and the contemporary press coverage in [Singularity Hub, *SAMURAI Project – Smart CCTV Security*](https://singularityhub.com/2009/12/23/samurai-project-smart-cctv-security-video/).

SAMURAI's genuinely novel and under-credited idea was **operator feedback in the
loop**: the system proposed, the operator corrected, and the model updated
online. That is *human-in-the-loop active learning for surveillance, in 2009*.
It is also the correct architecture for 2026 VLM systems, where the expensive
resource is the operator's adjudication and the cheap resource is candidate
generation. The field abandoned it for a decade because offline-trained deep nets
made online adaptation look unnecessary — and is now rebuilding it.

**INDECT** (FP7, 2009–2014) — the project that broke the EU's political
tolerance for this research line:

> *"The INDECT Project, funded with almost 11 million euros, aims to research on
> 'Intelligent information system supporting observation, searching and detection
> for security of citizens in urban environment'."*
> — [EDRi, *INDECT - privacy ethics in a secret project*](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)

> *"Under the Seventh Framework Research Programme, the INDECT project received
> 10.91 million euros and has been working since the beginning of 2009 to develop
> a platform which automatically recognizes threats or reports abnormal behaviour
> through registration and exchange of operational data."*
> — [EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)

> *"It was qualified by The Telegraph as the \"'Orwellian' artificial
> intelligence plan to monitor public for 'abnormal behaviour'\". Following the
> article, a lot of public pressure was put from media, civil society and the
> European Parliament, with MEPs addressing to the European Commission 10
> questions related to the project and its privacy ethics."*
> — [EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)

> *"Critics questioned how the Commission could justify approving and financing a
> programme that would in effect remove the presumption of innocence, since
> blanket surveillance would make all EU citizens potential suspects."*
> — [Reuters via Investing.com, *Irked by U.S., but EU keeps own spy projects quiet*](https://www.investing.com/news/world-news/irked-by-u.s.,-but-eu-keeps-own-spy-projects-quiet-351693)

> *"INDECT, which ran for five years until 2014, developed ways to identify
> potential criminals using software to collate and analyze disparate information
> collected from CCTV, drones, GPS location services on phones."*
> — [Reuters via Investing.com](https://www.investing.com/news/world-news/irked-by-u.s.,-but-eu-keeps-own-spy-projects-quiet-351693)

And the governance failure that made it indefensible:

> *"The Ethics board was dominated by Police Officers and had no privacy experts,
> though the European Commission later recommended adding independent experts
> with expertise in ethical and data protection issues."*
> — [EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)

The European Parliament record confirms the political salience: see
[Parliamentary question E-6084/2009, *INDECT research programme on interlinked
citizen surveillance systems*](https://www.europarl.europa.eu/doceo/document/E-7-2009-6084_EN.html?redirect)
and [the Commission's answer to E-8217/2010](https://www.europarl.europa.eu/sides/getAllAnswers.do?language=EN&reference=E-2010-8217).

**Why INDECT matters more than its deliverables.** INDECT is the moment the EU
learned that *the words you use to describe an analytics programme are part of
its risk surface*. "Automatically recognises abnormal behaviour of citizens in
urban environments" is a technically accurate description of what the field had
been doing since ADVISOR, and it is politically fatal when stated plainly. The
observable consequence: **every subsequent EU security-research call and every
subsequent European vendor rebranded away from "abnormal behaviour of people"
and toward "asset protection", "safety", "operational efficiency" and
"privacy-by-design".** Later, smaller projects such as **P-REACT** (petty crime
in small businesses) and **SURVEIRON** (UAV-based surveillance for civil
protection) are visibly framed in this post-INDECT register — narrow scope,
named beneficiary, explicit ethics work-package. **[VERIFY P-REACT and SURVEIRON
details — I had no search budget remaining to retrieve their CORDIS records.]**
That rhetorical retreat then hardened into law in the EU AI Act's treatment of
biometric categorisation and real-time remote biometric identification (§12.4).

---

## 7. Era 5b — The great disillusionment, 2008–2013

Between the financial crisis and the deep-learning inflection, commercial video
analytics went through its second false-alarm crisis — an exact rhyme of the VMD
crisis of the 1980s (§2.1). The evidence is in the corporate record assembled in
§5.3: Vidient ceased operations November 2010
([IPVM](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence));
Cernium repositioned repeatedly
([IPVM](https://ipvm.com/reports/cernium-shifts-strategy-again-checkvideo));
3VR narrowed to banking and then fire-saled to Identiv
([IPVM](https://ipvm.com/reports/3v-identiv)); ObjectVideo went to litigation
([Bloomberg](https://www.bloomberg.com/news/articles/2011-06-30/sony-samsung-techwin-targeted-by-objectvideo-in-itc-patent-case));
NICE exited in 2015
([IPVM](https://ipvm.com/reports/nice-is-out-of-the-video-surveillance-business)).

### 7.1 The five causes, ranked by how much damage they did

1. **Background subtraction does not survive the outdoors.** The entire pipeline
   rested on per-pixel background models. Rain, snow, headlights, shadows,
   foliage, water reflections, camera shake and automatic-gain-control steps all
   produce foreground. Vendors responded with ever-more-elaborate discriminators
   (shadow suppression, texture-based models, multi-modal Gaussians), each of
   which fixed one nuisance and added two tuning parameters. R01 §2.1 has the
   algorithmic detail. The *commercial* consequence is that **field performance
   was a function of site, weather and installer skill, and was therefore
   unforecastable at tender time.**
2. **Handcrafted features hit a hard ceiling on classification.** Distinguishing
   person from dog from bin-bag from shadow at 40 pixels of height, using
   shape/aspect/dispersedness features, tops out somewhere well below what an
   operator will tolerate. Cameras could see; they could not say what.
3. **Configuration labour was the real cost.** The 1980s complaint *"the time to
   install VMD systems took too long"*
   ([SMART Security Solutions](http://www.securitysa.com/regular.aspx?pklregularid=2904))
   applied unchanged: calibrate the ground plane, draw the zones, set the
   object-size filters per zone per camera, tune per time-of-day. On a 500-camera
   estate this is a multi-month professional-services engagement with no residual
   value, and it must be redone whenever a camera is nudged.
4. **The value proposition was inverted.** Analytics was sold as *headcount
   reduction*, which security directors cannot bank (you cannot fire half a guard)
   and which unions resist. The propositions that actually pay — insurance
   premium reduction, verified-alarm police response, forensic search time,
   footfall data for merchandising — were understood only patchily.
5. **No credible evaluation outside the UK.** With i-LIDS access restricted and no
   US equivalent until DIVA/ActEV (§8.4), buyers could not compare vendors, so
   they bought on demo. Demos favour the vendor with the best salesperson and the
   most cooperative pilot site, which selects *against* the vendor who has
   invested in robustness.

### 7.2 What became permanently obsolete in this era

- **Per-pixel background subtraction as the primary detector.** Survives as a
  pre-filter (§2.3); dead as a detector.
- **Blob-shape classification.** Completely replaced by learned classifiers.
- **Rule-engines as the *only* semantic layer.** Rules survive and are excellent
  for the four i-LIDS scenarios; they are hopeless for anything needing context.
- **The "analytics appliance"** — a 1U box that took 4–16 analogue or IP feeds and
  produced alarms. Killed by both edge (camera firmware) and, later, cloud.
- **Analytics as a separately-priced per-camera software licence** in the
  mid-market. Killed by camera OEMs bundling it.

### 7.3 What survived, and why

Exactly three things, all of which share the property that **the cost of a false
positive is low or is absorbed by someone other than the operator**:

- **Record-on-motion.** False positives cost disk.
- **Perimeter intrusion in a sterile zone, with a PTZ hand-off.** The scene is
  controlled by design, so the background model is valid; and the analytic is the
  *secondary* verification layer behind a physical PIDS, so a false positive
  costs a glance (R03 §1.4).
- **ANPR/LPR.** Constrained geometry, high-contrast retroreflective target,
  built-in checksum in the form of plate syntax, and a database lookup that
  discards non-matches. **ANPR is the only 20th-century video analytic that has
  never had a credibility crisis**, and the reason is that it has a *verifiable
  output* (§12.2).

### 7.4 The on-camera DSP era and its obsolescence

Between roughly 2005 and 2015, the dominant architectural belief was **analytics
belongs in the camera**: it saves bandwidth (send metadata, not video), it scales
linearly with camera count, and it needs no server room. ioimage, Axis's ACAP
ecosystem, Bosch's IVA, Pelco's Sarix, and Agent Vi's distributed split all
expressed this belief.

It was right about the economics and wrong about the substrate. The fixed-function
video DSP had a few hundred MIPS of integer throughput and no efficient
matrix-multiply. When the field moved to convolutional networks in 2014–2016,
**the installed base of DSP cameras could not be upgraded by a firmware update**,
because the workload changed character, not just size. The entire 2005–2015 edge
investment was stranded, and the analytics workload moved *back* to the server —
first to GPU servers on-premise (2016–2020), then to the cloud (2019–2024), and
only after about 2019 back to the edge again on a *different* substrate (NPU/VPU:
Ambarella CVflow, Hailo, Ambarella/Novatek SoCs with tensor engines, NVIDIA
Jetson).

**The lesson is about substrate risk, not about edge vs cloud.** The edge thesis
was correct twice (2005 and 2021) and the companies that bet on it in 2005 still
lost, because they bet on a *specific* silicon architecture with a 10-year
product life against an algorithmic change with a 3-year cycle. In 2026 the same
risk is live: whoever has just shipped a camera with a fixed 8-bit-INT NPU sized
for a CNN detector is exposed to the transformer/VLM workload the same way ioimage
was exposed to CNNs.

---

## 8. Era 6 — The government evaluation lineage, 2000–2026: PETS, VACE/CLEAR, TRECVID, VIRAT, Mind's Eye, DIVA/ActEV

This strand is the field's scientific conscience. It is also where the honest
numbers live.

### 8.1 PETS: eighteen years of "how do we even score this?"

> *"The goal of the PETS workshop has been to foster the emergence of
> methodologies for performance evaluation of tracking and surveillance,
> including development of performance evaluation metrics as well as a
> quantitative evaluation of tracking and surveillance results based on a common
> dataset."*
> — [PETS@CVG, University of Reading](http://www.cvg.reading.ac.uk/slides/pets.html)

> *"The 2017 International Workshop on Performance Evaluation of Tracking and
> Surveillance (PETS 2017) continues the series of highly successful PETS
> workshops held for almost twenty years, starting from FG 2000 onwards."*
> — [PETS 2017: dataset and challenge (PDF, Reading CentAUR)](https://centaur.reading.ac.uk/75249/1/PETS2017_Dataset_Description7.pdf)

The dataset progression tells the story of what the community thought was hard, in
order:

- **PETS'2000** — *"Outdoor people and vehicle tracking (single camera)"*
  ([PETS@CVG](http://www.cvg.reading.ac.uk/slides/pets.html)).
- **PETS'2001** — *"multi-view (2 cameras) and are significantly more challenging
  than for PETS'2000 in terms of significant lighting variation, occlusion, scene
  activity and use of multi-view data"*
  ([PETS'2001 dataset page](http://www.cvg.reading.ac.uk/PETS2001/pets2001-dataset.html)).
- **PETS 2009** — crowds. *"The PETS2009 outdoor crowd image analysis
  surveillance dataset includes performance evaluation of people counting,
  detection and tracking"*, evaluated *"using well established metrics developed
  in the Video Analysis and Content Extraction (VACE) programme and the
  CLassification of Events, Activities, and Relationships (CLEAR) consortium"*
  ([PETS@CVG](http://www.cvg.reading.ac.uk/slides/pets.html)).
- **PETS 2014/2015** — vehicle-mounted / maritime and protection scenarios
  ([PETS 2014: Dataset and challenge](https://www.academia.edu/55727626/PETS_2014_Dataset_and_challenge);
  [PETS2015 tracking challenge evaluation](https://centaur.reading.ac.uk/46541/1/2015_AVSS_PETS2015TrackingChallenge_Nawaz_Boyle_Li_Ferryman.pdf)).
- **PETS 2017** — final edition ([IEEE](https://ieeexplore.ieee.org/document/8014998/)).

Two historical facts of first-order importance are embedded there. First, **the
metric infrastructure the whole field still uses came out of VACE and CLEAR**, not
out of a vision conference: CLEAR MOT (and therefore MOTA/MOTP, and therefore the
arguments that produced IDF1 and HOTA — R01 §4) is a *government-evaluation*
artefact. Second, **PETS ended in 2017**, the same period in which MOTChallenge,
UCF-Crime and the DIVA/ActEV programme took over. The surveillance-specific
evaluation community was absorbed into the generic video-understanding community,
and R03 §8 documents the cost of that absorption: frame-level AUC on tiny
datasets replaced event-level detection at a specified false-alarm rate.

The associated conference series, **IEEE AVSS** (Advanced Video and Signal-based
Surveillance), ran alongside from 2001 onwards and remains the field's only
dedicated venue; PETS was for many years co-located with it
([PETS2015 evaluation, published at AVSS](https://centaur.reading.ac.uk/46541/1/2015_AVSS_PETS2015TrackingChallenge_Nawaz_Boyle_Li_Ferryman.pdf)).
**[VERIFY AVSS's founding year and continuity — I could not retrieve a source in
this session.]**

### 8.2 TRECVID and the retrieval tradition

NIST's TRECVID campaign, and specifically its **Surveillance Event Detection
(SED)** task (built on the **i-LIDS multi-camera airport corpus**), was the US
bridge between the information-retrieval community and surveillance. TRECVID's
later structure absorbed ActEV directly: see
[*TRECVID 2019: An Evaluation Campaign to Benchmark Video Activity Detection,
Video Captioning and Matching, and Video Search & Retrieval*](https://arxiv.org/pdf/2009.09984)
and [*TRECVID 2020*](https://arxiv.org/pdf/2104.13473),
[*TRECVID 2022 overview*](https://arxiv.org/pdf/2306.13118).
**TRECVID's cultural contribution was the discipline of a sequestered test set
with a fixed submission deadline and published per-team results** — the norm the
commercial market never adopted. **[VERIFY SED's exact years of operation
(commonly cited as 2008–2017) and the i-LIDS airport subset's licensing — no
search budget remained.]**

### 8.3 VIRAT and Mind's Eye: the move to "activities", and to aerial

> *"The VIRAT dataset contains about 550 videos, recorded from static and moving
> cameras covering 23 event types over 29 hours. A Large-scale Benchmark Dataset
> for Event Recognition in Surveillance Video was presented at the IEEE
> Conference on Computer Vision and Pattern Recognition 2011."*
> — [UCF CRCV, VIRAT](https://www.crcv.ucf.edu/research/data-sets/virat/)

> *"The aerial videos were provided by DARPA and were recorded using
> Electro-Optical/Infra-Red (EO/IR) sensor from a military aircraft flying at a
> height of over 1000 meters. The VIRAT aerial dataset has a low resolution of
> 480 × 720."*
> — [UCF CRCV](https://www.crcv.ucf.edu/data/VIRAT.php)

> *"VIRAT Ground 2.0… comprising 329 surveillance videos captured through
> stationary ground cameras mounted at significant heights (mostly at the top of
> buildings) across 11 different scenes, with recorded scenes including
> construction sites, parking lots, streets, and open outdoor areas."*
> — [UCF CRCV](https://www.crcv.ucf.edu/research/data-sets/virat/)

VIRAT is the hinge dataset. Before VIRAT, surveillance benchmarks were about
**tracks** (where is the blob). VIRAT made them about **events with participating
objects** (person loads object into vehicle). That reframing produced the
activity-detection task definitions that ActEV still uses (§8.4), and it created
the tiny-object regime that R01 §1.3 treats as central. It also produced the
first widely-used *aerial* surveillance benchmark, which is why the ISR and CCTV
communities converge again here (and why OD-VIRAT is still being published in
2025: [*OD-VIRAT: A Large-Scale Benchmark for Object Detection in Realistic
Surveillance Environments*](https://arxiv.org/pdf/2507.12396)).

**DARPA Mind's Eye** (2010–2013) attacked the next layer up:

> *"The US Defense Advanced Research Projects Agency (DARPA) initiated the Mind's
> Eye program, with several teams developing algorithms that were tested on
> thousands of video recordings of 48 selected activities, such as walking,
> running, pickup, exchange, and digging."*
> — [SPIE, *Automated recognition of human activities in video streams in real time*](https://spie.org/news/5489-automated-recognition-of-human-activities-in-video-streams-in-real-time);
> see also [Airforce Technology, *Mind's Eye: Visual Intelligence Takes to the Battlefield*](https://www.airforce-technology.com/features/feature122432/)

Mind's Eye's explicit goal was **visual *intelligence*** — not recognition of what
happened but description and inference about it, including reasoning about verbs
and about what was *about* to happen. It is, in hindsight, a 2010 attempt at what
VLMs do in 2025, using formal verb ontologies and neuromorphic architectures
(see e.g. the patent lineage: [*Neuromorphic system for real-time visual activity
recognition*, US 10,997,421](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10997421),
and [*Video access system and method based on action type detection*,
US 9,554,081](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9554081)).
**Mind's Eye failed for a reason worth internalising: it tried to get to
semantics by building the ontology first, and the ontology is the part that cannot
be hand-built.** The VLM route got there by learning the ontology implicitly from
web-scale text-image pairs. The 48-verb list was the bottleneck, not the vision.

### 8.4 IARPA DIVA → NIST ActEV → MEVA: the modern evaluation regime

> *"NIST developed the Activities in Extended Video (ActEV) evaluations series to
> support the needs of the Intelligence Advanced Research Projects Activity
> (IARPA) Deep Intermodal Video Analytics (DIVA) Program."*
> — [NIST, *Activities in Extended Videos Evaluation*](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)

> *"The Activities in Extended Video (ActEV) evaluation series are designed to
> accelerate the development of robust, multi-camera, automatic human activity
> detection systems for forensic and real-time alerting applications. A primary
> goal of the DIVA program is to support activity detection in multi-camera
> environments."*
> — [NIST ActEV](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation); [NIST NLPIR ActEV](https://www-nlpir.nist.gov/projects/tv2024/actev.html)

> *"The ActEV challenge defines three tasks: Activity Detection (AD) with no
> spatial localization in the video, Activity and Object Detection (AOD) where
> the activity and participating objects are spatially localized within a frame
> but not necessarily correlated across frames, and Activity / Object Detection
> and Tracking (AODT), which extends AOD to establish real-world activity and
> object identity across frames."*
> — [NIST ActEV](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)

> *"The MEVA KF data were collected and annotated for the Intelligence Advanced
> Research Projects Activity (IARPA) Deep Intermodal Video Analytics (DIVA)
> program. The MEVA KF data was collected at the Muscatatuck Urban Training
> Center (MUTC) with a team of over 100 actors performing in various scenarios."*
> — [MEVA data](https://mevadata.org/); [*MEVA: A Large-Scale Multiview, Multimodal Video Dataset for Activity Detection*](https://arxiv.org/pdf/2012.00914)

ActEV continues to run as a self-reported leaderboard
([ActEV SRL](https://actev.nist.gov/srl); [ActEV SDL evaluation plan
(PDF)](https://actev.nist.gov/pub/Draft_ActEV_SDL_EvaluationPlan_Test3.pdf)).
R03 §2.4 covers the metric mechanics (P_miss at a specified rate of false alarms;
nAUDC) and the operational lesson. The **historical** points for D01 are:

1. **DIVA/MEVA is the first US programme to do what i-LIDS did in 2006** —
   scripted alarm and non-alarm events, multi-camera, sequestered scoring, staged
   at a real urban training facility with >100 actors. It took the US fifteen
   years to build the UK's instrument, in a deep-learning idiom.
2. **DIVA's multi-camera framing was ahead of the commercial market and still is.**
   AODT — maintaining *real-world object identity across cameras while detecting
   activities* — is the task R02 exists to address and which almost no shipping
   product does well.
3. **MEVA is staged, not found.** A hundred actors at Muscatatuck performing
   scripted activities is *synthetic data made of people*. The programme
   concluded, implicitly, that the only way to get labelled surveillance events at
   scale with consent is to **stage them**. That is a direct institutional
   precedent for the simulation approach this repository takes (R04 §7, R01 §7):
   if the US intelligence community's answer to "where do we get activity data"
   was "rent a training town and hire actors", then "build the town in a
   simulator" is the obvious next step, and the argument against it is a sim2real
   argument, not a legitimacy argument.

---

## 9. Era 7 — The 2012 deep-learning inflection, and what it actually changed in surveillance

The AlexNet result (ILSVRC 2012) is the field's discontinuity, but **it did not
reach surveillance products until 2016–2018**, and it reached them unevenly. The
adoption sequence, which R01 §2.3 details algorithmically, was:

- **2012–2014: nothing changes in the industry.** GPUs are not in cameras or
  NVRs; the security channel has no ML capability; the market is mid-crisis
  (§7).
- **2014–2016: detection is re-based.** R-CNN → Fast/Faster R-CNN → SSD/YOLO
  replaces background-subtraction-plus-blob-classification. The immediate product
  consequence is the single most valuable feature in the industry's history:
  **person/vehicle classification good enough to suppress non-human motion.**
  That one capability cut outdoor false alarms by an order of magnitude and
  restored the category's credibility. Note what it is: **not a new capability,
  but a reliability fix for a 1990s capability.**
- **2016–2019: appearance search.** Deep re-ID embeddings make "find this person
  across my archive by clicking on them" a shipping feature (Avigilon Appearance
  Search is the canonical example — the technology was a principal rationale for
  its acquisition: *"Motorola Solutions to Acquire Avigilon, Leader in Advanced
  Video Surveillance and Analytics"*,
  [Motorola Solutions](https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-to-acquire-avigilon-leader-in-advanced-video-surveillanc.html),
  completed 28 March 2018 at *"a total enterprise value of approximately
  USD$1.0 billion"*,
  [Motorola Solutions](https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-completes-acquisition-avigilon.html)).
  Forensic search, not alerting, is where deep learning first paid.
- **2019–2022: edge NPUs return** (§7.4) and analytics-in-camera becomes free and
  universal, completing the commoditisation.
- **2023–2026: language enters** (§16).

### 9.1 What got easier, precisely

- **Detection and classification of people and vehicles** in unconstrained
  outdoor scenes: from "unreliable" to "effectively solved above ~50 px height in
  daylight". R01 §1.3 documents where it still breaks (the tiny-person regime).
- **Re-identification within a short time window and consistent lighting**: from
  "impossible" to "useful with a human adjudicating". R02 documents the
  cross-camera, cross-day limits.
- **Forensic retrieval**: from "scrub the tape" to "attribute filter + appearance
  search" to (2025) "ask in English".
- **Face recognition at scale**: from a laboratory curiosity to a commodity, with
  a reliability profile good enough that the binding constraints became legal and
  political rather than technical (§12).

### 9.2 What did not get easier at all

- **Intent.** R03 §4 is unambiguous: the only well-posed intent problem in
  computer vision is *short-horizon trajectory/action anticipation*. "Is this
  person planning to do harm" is not a vision problem and the field's most
  expensive failures (TSA SPOT, R03 §4.3) are attempts to make it one.
- **Rare events.** You cannot train on what you have never recorded. This is
  structural, not a data-collection budget problem: a specific scenario (a
  suicide-vest wearer, a specific machine failure mode) may have zero global
  instances on camera.
- **False alarms in the tail.** Deep detectors removed the *common* nuisances.
  What remains — reflections in wet glass, a mannequin, a poster of a person, a
  person on a screen inside the scene, an inflatable — is precisely the set of
  things that look like people to a model trained on pictures of people.
- **Cross-camera identity over long horizons.** R02.
- **Evaluation.** The field regressed here between 2000 and 2020 (§8.1) and is
  only now, with ActEV-style protocols and R03's argument, recovering.
- **Configuration labour.** See §7.1(3). No change.

---

## 10. Era 8 — The Chinese ascendancy and the geopolitical rupture, 2010–2026

### 10.1 The state programmes that created the demand

> *"China launched a national video surveillance system called Skynet in 2005 to
> 'fight crime and prevent possible disasters.'"*
> — [Grey Dynamics, *The Xueliang Project*](https://greydynamics.com/the-xeuliang-project-expansion-of-chinas-state-surveillance-programme/)

> *"Sharp Eyes, or the 'Xueliang' Project in Chinese, is China's latest mass
> video surveillance program. It was called the 'Xueliang Project,' or Sharp
> Eyes, a reference to a quote from communist China's former revolutionary leader
> Mao Zedong who once wrote that 'the people have sharp eyes'."*
> — [CSET Georgetown, *China's 'Sharp Eyes' Program Aims to Surveil 100% of Public Space*](https://cset.georgetown.edu/article/chinas-sharp-eyes-program-aims-to-surveil-100-of-public-space/)

> *"Sharp Eyes was launched after China's top planning authority, the National
> Development and Reform Commission, mandated in 2015 that video surveillance
> cover '100%' of China's public areas and key industries by 2020."*
> — [CSET Georgetown](https://cset.georgetown.edu/article/chinas-sharp-eyes-program-aims-to-surveil-100-of-public-space/)

> *"Projects like the Golden Shield Project, Safe Cities, SkyNet, Smart Cities,
> and now Sharp Eyes mean that there are more than 200 million public and private
> security cameras installed across China."*
> — [IPVM, *China Public Video Surveillance Guide: From Skynet to Sharp Eyes*](https://ipvm.com/reports/sharpeyes)

> *"According to Sichuan authorities, by December 2017, 14,087 villages have been
> connected to the Sharp Eyes project and 41,695 surveillance cameras were
> installed."*
> — [CSET Georgetown](https://cset.georgetown.edu/article/chinas-sharp-eyes-program-aims-to-surveil-100-of-public-space/)

The distinctive element of Sharp Eyes, and the one Western analysts most often
miss, is that it is **not purely automated**: it deliberately routes feeds to
*residents' own televisions and phones* so that the public participates in
monitoring. **It is a human-computation system with a video-analytics substrate.**
That is a different design point from the Western "replace the operator" framing,
and it is arguably a better-engineered response to the semantics problem: use
machines for indexing and coverage, use a very large number of humans for meaning.

### 10.2 Why Hikvision and Dahua won the hardware layer

The causal chain is economic, not technological: a state mandate for near-total
coverage produced a domestic demand curve no other market could match; that volume
funded vertical integration (own SoCs, own ISP tuning, own manufacturing) and
brutal unit costs; the cost advantage then took the global mid-market, where
analytics-in-firmware was bundled for free. The result by the late 2010s was that
**the free analytics in a $120 camera was better than the paid analytics an
enterprise vendor had sold for $600/channel in 2008** — which is the mechanism
that finished off the 2000s cohort (§7).

### 10.3 The rupture: NDAA 889 and the UK ban

> *"Section 889 of the US National Defense Authorization Act bans the use of
> surveillance equipment manufactured by specific Chinese companies including
> Hikvision, Dahua, Huawei, Hytera, and ZTE."*
> — [Clearway, *NDAA Compliant Security Cameras*](https://www.clearway.co.uk/news/ndaa-compliant-security-cameras-a-guide-for-uk-organisations/)

> *"Under 2019 NDAA Section 889, the US federal government cannot 'procure or
> obtain' video surveillance 'produced by' Dahua or Hikvision - including OEMs -
> due to national security concerns."*
> — [IPVM, *Where Dahua and Hikvision Are Banned*](https://ipvm.com/reports/hikua-bans)

> *"In November 2022, the UK government directed departments to stop installing
> Chinese-made surveillance cameras in sensitive government sites. Following
> concern over visual surveillance equipment from companies subject to China's
> National Intelligence Law, the Cabinet Office issued a directive in 2022
> mandating removal from all 'sensitive' government sites. The April 2025 deadline
> was enforced."*
> — [Clearway](https://www.clearway.co.uk/news/ndaa-compliant-security-cameras-a-guide-for-uk-organisations/)

See also the official compliance framing in
[NDAA 889 Compliance Requirement (US Embassy, PDF)](https://ae.usembassy.gov/wp-content/uploads/sites/18/2025/05/NDAA-889-Compliance-Requirement.pdf)
and [US EAC, *What is Section 889 of the FY 2019 NDAA?*](https://www.eac.gov/what-section-889-fy-2019-ndaa).

**Three second-order consequences that matter more than the bans themselves:**

1. **"NDAA-compliant" became a product category and a marketing moat.** Vendors
   now lead with compliance, not capability — see the framing in
   [Rhombus, *NDAA Compliant Security Cameras*](https://www.rhombus.com/blog/ndaa-compliant-security-cameras/)
   and [Tec-Tel's Section 889 checklist](https://tec-tel.com/resources/ndaa-section-889-camera-compliance).
   For the first time since the 1980s, **provenance rather than performance is a
   primary purchase criterion in the Western public sector.**
2. **It re-opened the hardware market that commoditisation had closed**, which is
   the single largest reason Verkada, Rhombus, Eagle Eye, Axis and Motorola grew
   in 2019–2026. The startup wave of §13 is partly a *trade-policy* phenomenon.
3. **OEM opacity became the central due-diligence problem.** Because the ban
   covers *"including OEMs"*
   ([IPVM](https://ipvm.com/reports/hikua-bans)), buyers must trace the actual
   manufacturer behind a badge — a problem the industry had spent thirty years
   making deliberately hard.

---

## 11. The VMS layer and the standards timeline

### 11.1 Why the VMS, not the camera, became the control point

The video management system — Genetec Security Center, Milestone XProtect, Axis
Camera Station, Avigilon Control Center, Verint/Qognify, Bosch BVMS — is where the
analytics *business* ended up, for a simple structural reason: **the VMS owns the
alarm queue, the user, the archive and the integration to access control.** An
analytic without a place to send its output is not a product. Every specialist of
the 2000s discovered that it had to either become a VMS (NICE, 3VR, Avigilon) or
be OEM'd into one (Agent Vi, Ipsotek, ioimage) — and the second path means the VMS
vendor owns the customer and can replace you.

Genetec (founded 1997, Montreal) and Milestone (founded 1998, Denmark; acquired by
Canon in 2014, joining Axis which Canon acquired in 2015) are the two independent
survivors, and both won by being **open**: documented APIs, a large certified
device list, and a third-party analytics marketplace. **[VERIFY all founding and
acquisition dates in this paragraph — no search budget remained.]** Irisity's
presence in [Milestone's marketplace](https://www.milestonesys.com/marketplace/irisity/)
is a live example of the pattern: the analytics vendor is a listing in the
platform vendor's catalogue.

**The historical lesson:** in every era, the layer that owns the *operator's
attention* captures the value, and the layer that produces the *detection*
commoditises. 1990s: the multiplexer/DVR. 2000s: the VMS. 2010s: the VMS and the
camera OEM. 2020s: the cloud console. 2026+: whatever owns the natural-language
query box (§16, and prediction P7).

### 11.2 ONVIF and the interoperability settlement

> *"ONVIF was founded in 2008 and is a leading industry forum driving
> interoperability for IP-based physical security products."*
> — [ONVIF Profile M press release](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/)

ONVIF was founded by Axis, Bosch and Sony. **[VERIFY — the retrieved source
confirms the 2008 founding but explicitly did not confirm the founder list; see
the note in the ONVIF search result.]** The profile sequence — S (streaming), C
(access control), G (recording/archive), Q (quick install), A (access-control
configuration), T (advanced streaming, H.264/H.265), D (access-control
peripherals), M (metadata/analytics) — encodes the industry's priority order over
thirteen years. **[VERIFY the individual profile release years; only Profile M's
date was retrievable in this session.]** The revealing fact is the ordering:
**analytics metadata was standardised last, in 2021, thirteen years after
streaming.**

### 11.3 ONVIF Profile M (2021): the standard that finally decoupled analytics

> *"ONVIF released Profile M on June 30, 2021, which standardizes metadata and
> events for analytics applications. This new profile addresses the dynamic video
> analytics market and expands the pathways for the use of metadata and event
> handling into other systems such as access control, cloud services and IoT
> platforms."*
> — [ONVIF](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/);
> [ONVIF blog](https://www.onvif.org/blog/2021/06/30/onvif-announces-the-release-of-profile-m/)

> *"Profile M provides a standard way of communicating metadata and events between
> analytics-capable services and devices like IP cameras, and clients like video
> management software or server- or cloud-based services."*
> — [ONVIF](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/);
> the normative document is the
> [ONVIF Profile M Specification v1.0 (PDF, June 2021)](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf).

Profile M is the standardisation of the idea IBM published in 2004 (§5.2) and
Inria's VSIP embodied in 2005 (§6.2): **the detector and the semantics are
separate components communicating over a defined schema.** Its practical effect,
five years on, is real but partial — object classification metadata (person,
vehicle, plus attributes) flows reasonably well between conformant cameras and
VMSes, which is what makes cross-vendor "person-only" filtering possible. Its
limits are equally real: the schema is object- and event-shaped, so it has no
natural place to carry an *embedding* or a *natural-language description*, which is
exactly what 2026 pipelines want to move around. See
[Forasoft, *ONVIF Profile M in 2026*](https://www.forasoft.com/blog/article/onvif-profile-m)
for the current integrator's-eye view. **Prediction P9 in §19 follows directly:
the next profile has to carry vectors and text.**

### 11.4 The rest of the standards landscape

- **IEC 62676** (*Video surveillance systems for use in security applications*),
  the multi-part international standard covering system requirements, transmission
  protocols, analogue and digital interfaces, and image-quality/application
  guidelines, which superseded/absorbed the European **EN 50132** series. It is
  the document that UK/EU specifiers cite for *operational requirements* and
  pixels-on-target. **[VERIFY publication dates of each part and the exact
  EN 50132 relationship — my search budget was exhausted before I could retrieve
  a source, and R01/R04 do not cover it.]**
- **i-LIDS** (2005 sample / 2006 launch) — §6.1, and R03 §2.
- **NPSA CAPSS** (Catalogue of Approved Physical Security / the CPNI-era approval
  scheme for security products, now run by the National Protective Security
  Authority) — the UK route by which a detection product becomes citable in a CNI
  specification. **[VERIFY the scheme's current name, scope and whether video
  analytics products are in scope — unretrieved in this session. R03 §2.1
  establishes the CPNI → NPSA renaming with a citation.]**
- **NIST FRVT/FRTE** for face recognition, and **NIST ActEV** for activity
  detection ([NIST ActEV](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)) —
  the two genuinely load-bearing evaluation instruments in the field in 2026.
- **BS 7958 / SCC Code of Practice** (UK CCTV operation and the Surveillance
  Camera Code) — governance rather than performance. **[VERIFY.]**

**The structural observation about standards in this field:** *interoperability*
got standardised (ONVIF), *installation quality* got standardised (IEC 62676
operational requirements), and *analytic performance* did not — except inside
closed government schemes. There is still no publicly citable, vendor-neutral,
pass/fail conformance test for "does this person-detection analytic work". That
vacuum is why the market has been re-fooled roughly every eight years.

---

## 12. Biometrics, plates, bodycams and the law, 2015–2026

### 12.1 Live facial recognition: the capability that forced the legal system to engage

LFR is where video analytics stopped being a procurement matter and became a
constitutional one. The landmark:

> *"The Court of Appeal held in R (on the application of Bridges) v Chief
> Constable of South Wales Police ([2020] EWCA Civ 1058) that the live automated
> facial recognition technology (AFR) used by South Wales Police Force was
> unlawful as it was not 'in accordance with law' for the purposes of Article 8 of
> the ECHR."*
> — [Inforrm / Hugh Tomlinson QC](https://inforrm.org/2020/08/17/case-law-r-on-the-application-of-bridges-v-chief-constable-of-south-wales-police-use-of-automatic-facial-recognition-technology-unlawful-hugh-tomlinson-qc/);
> the judgment itself: [*R (Bridges) v CC South Wales* (PDF, judiciary.uk)](https://www.judiciary.uk/wp-content/uploads/2020/08/R-Bridges-v-CC-South-Wales-ors-Judgment.pdf)

> *"The SWP had failed to carry out a proper Data Protection Impact Assessment
> (DPIA) and had not complied with the public sector equality duty (PSED)."*
> — [Hunton, *UK Court of Appeal Finds Automated Facial Recognition Technology Unlawful*](https://www.hunton.com/privacy-and-information-security-law/uk-court-of-appeal-finds-automated-facial-recognition-technology-unlawful-in-bridges-v-south-wales-police)

> *"Mr. Bridges… brought the original judicial review proceedings after South
> Wales Police launched a project involving the use of AFR (AFR Locate), which
> deployed AFR technology at certain events and in certain public locations where
> crime was considered likely to occur, capturing images of up to 50 faces per
> second."*
> — [Data Protection Report](https://www.dataprotectionreport.com/2020/08/key-takeaways-for-the-private-sector-from-the-bridges-v-south-wales-police-facial-recognition-case/)

> *"This is the first successful legal challenge to AFR technology and an
> important decision in relation to the regulation of state surveillance."*
> — [Osborne Clarke](https://www.osborneclarke.com/insights/appeals-court-hands-uks-first-judgment-automated-facial-recognition);
> see also [Liberty's case page](https://www.libertyhumanrights.org.uk/issue/legal-challenge-ed-bridges-v-south-wales-police/)
> and [Ada Lovelace Institute, *Facial recognition technology needs proper regulation*](https://www.adalovelaceinstitute.org/blog/facial-recognition-technology-needs-proper-regulation/).

**Read the holding precisely, because the industry consistently misreports it.**
The Court of Appeal did **not** hold that LFR is inherently unlawful. It held that
*this deployment* was unlawful because the legal framework left too much
discretion to individual officers over **who goes on the watchlist** and **where
the cameras are deployed** — plus the DPIA and PSED failures. The remedy is a
tighter framework, not abolition. The official UK response acknowledged exactly
this: see the Home Office's own blog, [*What next for automated facial
recognition*](https://videosurveillance.blog.gov.uk/2020/08/11/what-next-for-automated-facial-recognition).
The consequence, visible through 2021–2026, is that **UK LFR expanded after
Bridges, under a more codified authorisation regime** — a pattern worth
remembering when reasoning about the regulatory future in §19.

### 12.2 Clearview: the data-provenance reckoning

> *"On 23 May 2022, the UK's Information Commissioner (ICO) fined Clearview AI
> £7,552,800 for using images of people in the UK that were collected from the
> internet and social media to create a global online database for facial
> recognition."*
> — [ICO newsroom](https://ico-newsroom.prgloo.com/news/ico-fines-facial-recognition-database-company-clearview-ai-inc-more-than-gbp-7-5m-and-orders-uk-data-to-be-deleted);
> [DAC Beachcroft](https://www.dacbeachcroft.com/en/gb/articles/2022/may/facial-recognition-clearview-ai-fined-more-than-75m-by-the-ico/)

> *"The Italian DPA (the Garante) fined Clearview AI €20 million in March 2022 for
> the unlawful processing of biometric and geolocation data and ordered Clearview
> AI to prohibit any collection and processing activities in Italy."*
> — [EDPB](https://www.edpb.europa.eu/news/national-news/2022/facial-recognition-italian-sa-fines-clearview-ai-eur-20-million_en)

> *"On 20 October 2022, the French Data Protection Agency – CNIL, imposed a €20
> million fine on Clearview AI over their facial recognition technology."*
> — [Data Privacy Manager, *CNIL issues €20 million GDPR fine to Clearview AI*](https://dataprivacymanager.net/cnil-issues-e20-million-gdpr-fine-to-clearview-ai/)

And the twist that most commentary omits:

> *"Clearview AI wins appeals GDPR case against UK's ICO"*
> — [Digital Watch Observatory](https://dig.watch/updates/clearview-ai-wins-appeals-gdpr-case-against-uks-ico);
> [DLA Piper, *Clearview AI -v- Information Commissioner*](https://privacymatters.dlapiper.com/2023/10/clearview-ai-v-information-commissioner/)

The First-tier Tribunal's 2023 decision turned on **jurisdiction** — whether the
UK GDPR reached a US company providing services only to foreign law enforcement —
not on whether the scraping was lawful. **[VERIFY the subsequent appellate history;
the ICO appealed and the position has moved since 2023, and I had no budget to
retrieve the current status.]** See also
[Privacy International's Europe-wide challenge](https://privacyinternational.org/legal-action/challenge-against-clearview-ai-europe)
and the academic treatment in
[*Privacy and data protection regulations for AI using publicly available data:
Clearview AI case* (ACM ICEGOV 2024)](https://dl.acm.org/doi/10.1145/3680127.3680200).

**The durable lesson for analytics generally, not just faces:** the binding
constraint on a video-AI product is increasingly **the provenance of its training
data and its reference database**, not its accuracy. A model trained on scraped
imagery and a watchlist assembled without a lawful basis are both liabilities that
no amount of benchmark performance offsets. This will generalise from faces to
gait, to body-appearance re-ID (directly relevant to R02), and to
behaviour-profiling.

### 12.3 ALPR/ANPR: the quiet success, and its own reckoning

> *"Automatic Number Plate Recognition (ANPR) was invented in 1976 at the Police
> Scientific Development Branch (PSDB), the Home Office's own research unit in the
> UK. A small team led by Dr. Paul Wilkins and John Aston began experimenting with
> the idea of using optical character recognition (OCR) on video feeds to identify
> vehicles by their license plates."*
> — [Traffic Technology Today, *Who invented ANPR? The untold British story*](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)

> *"Prototype systems were working by 1979, and contracts were let to produce
> industrial systems, first at EMI Electronics, and then at Computer Recognition
> Systems (CRS) in Wokingham, UK. Early trial systems were deployed on the A1 road
> and at the Dartford Tunnel."*
> — [Traffic Technology Today](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)

> *"The first arrest using ANPR evidence came in 1981."*
> — [Traffic Technology Today](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)

> *"The first documented case of ANPR in helping solve a murder occurred in
> November 2005 after the murder of Sharon Beshenivsky, in which City of Bradford
> based ANPR played a vital role in locating and subsequently convicting her
> killers."*
> — [Traffic Technology Today](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)

> *"The technology did not become widely used until new developments in cheaper and
> easier to use software was pioneered during the 1990s."*
> — [Traffic Technology Today](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)

**ANPR is the counter-example that proves the thesis of this dossier.** Same
country, same research branch, same decade as VMD — and it worked, because:

1. The target is **cooperative and standardised** (a legally-mandated
   high-contrast retroreflective plate with a defined character set).
2. The geometry is **constrained** (vehicles travel in lanes, at known ranges).
3. The output is **verifiable against an external register** (DVLA/DMV), so a
   misread usually produces a *no-match* rather than a *wrong match*.
4. The false-positive cost is **absorbed by a database query**, not by a human.

Every successful video analytic in history has at least three of those four
properties. Every failed one has at most one. **When assessing any new analytic
claim, score it on those four axes first.** (Face recognition has 1, 3 and
partially 4 — hence its technical success and its *political* problem, which is
precisely that property 3's "external register" is a watchlist of people.)

ANPR's own reckoning is about **retention and aggregation**, not accuracy: a
national network that records every vehicle movement is a location-history
database, which is why the modern ALPR debate (Flock Safety, Motorola's Vigilant,
Axon's new fixed ALPR line — *"Axon announces new fixed ALPR camera solutions and
next-gen AI advancements to expand real-time public safety ecosystem"*,
[Axon](https://www.axon.com/newsroom/press-releases/axon-announces-new-fixed-ALPR-camera-solutions-and-next-gen-AI-advancements-to-expand-real-time-public-safety-ecosystem))
is a data-governance debate.

### 12.4 Body-worn video and Axon: the other camera estate

Body cameras created a second, separate video estate — tens of millions of hours
per year, first-person, moving, with consent and disclosure obligations — and Axon
converted it into a software business.

> *"Axon, formerly TASER, Inc., has staked its entire business on body cameras and
> AI since it rebranded in 2017. Today, the company's product suite spans conducted
> energy weapons (TASER 7 and TASER 10), body-worn cameras (Axon Body 4), in-car
> fleet cameras, the Evidence.com digital evidence management platform, drone
> systems (Axon Air / Skydio), AI-powered report writing (Draft One), and real-time
> crime center software (Fusus)."*
> — [Times Square Investment Journal / CUNY, *Axon trades Tasers for tech in software and AI push*](https://coveringcompanies.journalism.cuny.edu/2025/11/05/axon-trades-tasers-for-tech-in-software-and-ai-push/)

> *"Axon reimagines report writing with Draft One, a first-of-its-kind AI-powered
> force multiplier for public safety"* (23 April 2024)
> — [Axon investor relations](https://investor.axon.com/2024-04-23-Axon-reimagines-report-writing-with-Draft-One,-a-first-of-its-kind-AI-powered-force-multiplier-for-public-safety)

> *"Audio from Axon Body 3 and 4 camera footage is uploaded over LTE and
> transcribed automatically, so report drafts are available within five minutes of
> an incident ending."*
> — [Axon](https://www.axon.com/resources/beyond-battery-life-how-the-ecosystem-brings-out-the-best-in-the-axon-body-4)

> *"By the end of 2025, Axon's AI report writing tool had processed over 100,000
> police incident reports. In late 2024, Axon launched the AI Era Plan with
> Unlimited Auto-Transcribe and Draft One—the fastest-selling product in Axon's
> history."*
> — [CUNY Journalism](https://coveringcompanies.journalism.cuny.edu/2025/11/05/axon-trades-tasers-for-tech-in-software-and-ai-push/)

> *"In 2024, Axon acquired Fusus, a platform that aggregates disparate video and
> sensor surveillance feeds, with AI now embedded… Fusus operates what it calls
> 'real time crime centers (RTCC)' which allow police and other public agencies to
> analyze a wide array of video sources at a single point and apply AI that detects
> objects and people."*
> — [Vice, *Bodycam Maker Axon Is on a Mission to Surveil America with AI*](https://www.vice.com/en/article/axon-acquires-fusus-ai-surveillance-retail-healthcare/)

**Two historically significant things here.** First, *Draft One is the first mass
deployment of generative AI in the surveillance chain, and it operates on **audio
and text**, not video.* The fastest-selling product in the history of the largest
public-safety technology company is a transcription-and-drafting tool. That is a
strong empirical signal about where the near-term value of LLMs in this domain
actually sits: **not in seeing, in writing.** Second, *Fusus is the Real-Time
Crime Center pattern* — aggregate every camera in a city, public and private,
including private businesses and residents who opt in, into one operator console.
The RTCC is the 2020s answer to the same question the 1960s control room asked, and
it has the same scaling problem, which is why every RTCC vendor is now buying or
building a video-agent layer (§16).

### 12.5 The regulatory frame as of 2026

The three instruments that now bound the field in the West: **UK** — the
*Bridges* framework plus the Surveillance Camera Code and the ICO's biometrics
guidance; **EU** — the AI Act's prohibition/high-risk classification of
real-time remote biometric identification in public spaces, emotion recognition in
certain contexts, and biometric categorisation, layered on GDPR Art. 9; **US** —
no federal framework, a patchwork of state biometric statutes (Illinois BIPA being
the consequential one) plus procurement-side controls (NDAA 889). **[VERIFY the EU
AI Act article-level detail and dates — R03 §9 carries the cited version of this
material; prefer R03's citations over this summary.]**

---

## 13. Era 9 — The cloud shift and the 2016–2026 startup wave

### 13.1 Why cloud won where the 2000s server products lost

The 2000s analytics products failed partly on distribution (§5.2). The cloud
generation solved distribution by changing the *unit of sale*: not a per-channel
licence sold through an integrator, but a **per-camera-per-month subscription with
the camera included**, sold increasingly direct. That single change fixed four of
the five causes of the 2008–2013 collapse (§7.1): configuration labour becomes the
vendor's problem, not the customer's; models improve continuously without a truck
roll; the value proposition becomes "fewer things to manage" rather than "fewer
guards"; and the vendor sees every customer's failure modes, which is the only way
to actually fix the false-alarm tail.

Verkada is the clearest instance of the model's success:

> *"In September 2022, Verkada announced a $205 million Series D funding round
> that valued the company at $3.2 billion."*
> — [Security Sales & Integration](https://www.securitysales.com/news/verkada-raises-205m-valued-3-2b/146112/)

> *"Verkada reached a $5.8 billion valuation after a new funding round led by
> CapitalG, Alphabet's venture capital arm."*
> — [CNBC (3 December 2025)](https://www.cnbc.com/2025/12/03/verkada-capitalg-valuation-security.html);
> [Verkada's own announcement](https://www.verkada.com/blog/our-new-valuation-dec-2025/);
> [PR Newswire](https://www.prnewswire.com/news-releases/verkada-reaches-5-8b-valuation-with-investment-from-capitalg-302631378.html)

> *"The investment comes as Verkada surpasses $1 billion in annualized bookings,
> and customers have deployed over 2 million devices across 171 countries."*
> — [PR Newswire](https://www.prnewswire.com/news-releases/verkada-reaches-5-8b-valuation-with-investment-from-capitalg-302631378.html)

> *"Verkada provides physical security technology connected under a single
> cloud-based software platform. Its six product lines include video security
> cameras, access control, environmental sensors, alarms, workplace, and
> intercoms."*
> — [SiliconANGLE](https://siliconangle.com/2025/12/03/security-device-startup-verkada-raises-funding-5-8b-valuation/)

Read that product list. **Verkada is not an analytics company; it is a building-
systems company that uses analytics as a feature.** That is the third distinct
successful business model in this history, after "patents" (ObjectVideo) and
"verified alarms as a service" (CheckVideo): **sell the whole estate, and let
analytics be the reason the estate is pleasant to own.** The 2000s pure-plays had
no estate to sell.

Alongside: **Rhombus** (cloud cameras, NDAA-compliance-forward positioning —
[Rhombus on NDAA compliance](https://www.rhombus.com/blog/ndaa-compliant-security-cameras/)),
**Eagle Eye Networks** (cloud VMS, the earliest of the group), and the
consolidation that followed — *"Brivo merged with Eagle Eye Networks in
2024/2025, adding a full cloud VMS and AI video layer"*
([Coram](https://www.coram.ai/post/ambient-ai-competitors)) **[VERIFY this
merger — the claim comes from a competitor's marketing page, which is a weak
source]**.

### 13.2 The AI-native analytics cohort

The 2016–2026 cohort — **Ambient.ai, Hakimo, Coram, Spot AI, Lumana, Camio,
Vintra, viisights, Actuate** — differs from the 2000s cohort in three ways: it
assumes deep learning as a substrate rather than a differentiator; it sells
*outcomes at the monitoring centre* (verified alarms, reduced guard hours) rather
than software licences; and several of them are explicitly
**camera-agnostic-overlay** plays, running on the customer's existing estate.

> *"Ambient AI has raised a total funding of $146M over 4 rounds from 18
> investors. Their latest funding round was of $74M on Apr 01, 2025. Investors
> include Western Technology Investment, Andreessen Horowitz and 16 others.
> Ambient.ai provides a security platform that applies AI to existing camera
> infrastructure to sensor and prevent incidents."*
> — [Tracxn, Ambient AI funding](https://tracxn.com/d/companies/ambient-ai/__o3P0l5V7BKOZZr3yfissd1iMGgTNb4kFRNlvBdq9MNg/funding-and-investors);
> see also [Crunchbase](https://www.crunchbase.com/organization/ambient-ai)

> *"Ambient.ai, Coram AI, Verkada, Milestone Systems, and Spot AI are some
> competitors of Lumana."*  *"Wing Venture Capital, Norwest, and S Capital VC have
> invested in Lumana."*
> — [PitchBook, Lumana profile](https://pitchbook.com/profiles/company/510191-56)

**Vintra** (video analytics for law enforcement and re-ID-driven investigation)
and **viisights** (behavioural recognition — a genuine attempt at the AISight
proposition with modern methods) are the two closest to the historical thread of
this dossier. **[VERIFY Vintra's and viisights' current corporate status and
funding — I had no search budget remaining; Vintra in particular is reported to
have been acquired, which I could not confirm.]**

**"Applies AI to existing camera infrastructure"**
([Tracxn](https://tracxn.com/d/companies/ambient-ai/__o3P0l5V7BKOZZr3yfissd1iMGgTNb4kFRNlvBdq9MNg/funding-and-investors))
is the most important phrase in this section, and it is exactly the ObjectVideo
2003 pitch. The difference is that in 2003 the overlay had to run on a rack in the
customer's basement and produced tripwire alarms; in 2025 it runs in a VPC and
produces *"signatures"* of composite behaviour with a VLM adjudicating. **Same
architecture, 10^4 more compute, and a customer base that has already accepted
subscription pricing.** The architecture was never the problem.

---

## 14. The obsolescence ledger: what died, what got easy, what is still hard

### 14.1 Dead or terminally narrow

| Thing | Peak | Why it died |
|---|---|---|
| Analogue VMD (zone differencing, relay out) | 1980s | No object model; nuisance alarms; per-site tuning |
| Per-pixel background subtraction as primary detector | 1999–2012 | Outdoor scenes violate the stationarity assumption (R01 §2.1) |
| Handcrafted features (HOG/DPM) for classification | 2005–2014 | Learned features dominate at every operating point (R01 §2.2) |
| Blob shape/dispersedness classifiers | 1997–2012 | Ambiguous at small object sizes |
| Fixed-function video DSP as the analytics substrate | 2005–2015 | Could not run convolutions; installed base stranded (§7.4) |
| The standalone "analytics appliance" (1U, 4–16 ch) | 2004–2012 | Squeezed from both edge and cloud |
| Rules-only semantics as the whole product | 2001–2015 | No context; cannot express anything interesting |
| Per-channel perpetual analytics licences in the mid-market | 2003–2016 | OEMs bundled the capability into firmware |
| Unsupervised "learn what's normal, alert on rare" as a standalone product | 2008–2017 | Rarity ≠ significance; unfalsifiable spec (§5.4) |
| Hand-built verb/activity ontologies | Mind's Eye era | Ontology construction does not scale (§8.3) |
| Marquee-airport-reference-as-a-business-model | 2005–2010 | Vidient: $30M in, zero out (§5.3) |
| Frame-level AUC on 60-second test sets as the field's headline metric | 2013–2023 | Does not predict field behaviour (R03 §8) |

### 14.2 Genuinely easy now (2026)

Person/vehicle detection and classification in daylight above ~50 px; camera
tampering and defocus detection; line-crossing and region occupancy with class
filters; plate reading in constrained geometry; face matching against a curated
gallery; short-horizon within-camera tracking; attribute-based and
appearance-based forensic retrieval; natural-language search over an indexed
archive; automatic transcription and drafting of incident narratives (§12.4).

### 14.3 Still hard, and structurally so

1. **Intent.** Not a vision problem beyond the short anticipation horizon
   (R03 §4).
2. **Rare events.** Zero-shot by necessity; the training distribution cannot
   contain them.
3. **The false-alarm tail.** The residual nuisances are adversarially
   person-shaped (§9.2).
4. **Cross-camera, cross-day identity.** R02 in full; and note that the *legal*
   path to solving it (biometric enrolment) is closing as the *technical* path
   opens (§12.2).
5. **Evaluation.** No public, vendor-neutral conformance regime (§11.4).
6. **Configuration and commissioning labour.** Unchanged since 1985
   (§2.1, §7.1).
7. **Grounding a language model's confident sentence in pixels.** VLMs will
   describe an event that did not occur, fluently. §16.
8. **Cost per camera-hour of continuous semantic analysis.** The reason §16's
   architectures are all two-stage.

---

## 15. The defence strand: ISR full-motion video, WAMI, and Maven

### 15.1 Why the defence strand is a separate history

The military problem is the inverse of the CCTV problem. CCTV: fixed cameras,
static scenes, years of footage of the same pixels, a small number of operators,
and a low tolerance for false alarms. ISR: moving sensor, moving scene, an
enormous volume of never-to-be-seen-again footage, a *large* number of analysts,
and a tolerance for false alarms because a human always adjudicates. The two
strands share ancestors (Sarnoff, §4.3), share benchmarks (VIRAT aerial, §8.3),
and share almost no product.

### 15.2 WAMI: Constant Hawk → ARGUS-IS → Gorgon Stare

> *"The ARGUS-IS, or the Autonomous Real-Time Ground Ubiquitous Surveillance
> Imaging System, is a DARPA project contracted to BAE Systems that uses hundreds
> of cellphone cameras in a mosaic to video- and auto-track every moving object
> within a 15 sq mi (39 km2) area."*
> — [Wikipedia, ARGUS-IS](https://en.wikipedia.org/wiki/ARGUS-IS) (search snippet; direct fetch blocked)

> *"Gorgon Stare is a video capture technology developed by the United States
> military, manufactured by Sierra Nevada Corporation and designed by DARPA, which
> was introduced in 2011. It is a spherical array of nine cameras attached to an
> aerial drone."*
> — [Wikipedia, Gorgon Stare](https://en.wikipedia.org/wiki/Gorgon_Stare) (search snippet)

> *"Hosted and flown on General Atomics MQ-9 Reaper remotely piloted aircraft,
> Gorgon Stare includes the USAF's only operational day/night persistent wide-area
> motion imagery (WAMI) capability."*
> — [Sierra Nevada Corporation, *Gorgon Stare Increment 2* milestone release](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/)

> *"The system features two state-of-the-art imaging sensor turrets—an
> electro-optical (EO) sensor derived from DARPA's ARGUS technology and
> manufactured by BAE Systems, and an infrared (IR) sensor integrating the largest
> IR arrays available manufactured by Exelis."*
> — [Sierra Nevada Corporation](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/)

> *"Wide Area Motion Imagery expands the aperture so you can watch an entire city
> at once and zoom in on any one part of the imagery with a decent amount of
> detail, while still recording everything else."*
> — [Lexington Institute, *Wide Area Persistent Surveillance Revolutionizes Tactical ISR*](https://lexingtoninstitute.org/wide-area-persistent-surveillance-revolutionizes-tactical-isr/)

> *"The system has flown long duration sorties daily in Afghanistan since March
> 2011, providing over 10,000 hours of direct combat support."*
> — [Sierra Nevada Corporation](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/)

The predecessor, **Constant Hawk**, established the pattern of *forensic
backtracking*: record a whole city persistently, and when an IED detonates, run the
imagery backwards to find who placed it and where they came from
([Wikipedia, Constant Hawk](https://en.wikipedia.org/wiki/Constant_Hawk), snippet;
and the general treatment in
[Wikipedia, Wide-area motion imagery](https://en.wikipedia.org/wiki/Wide-area_motion_imagery)).
The candid operator's account is worth reading in full:
[*'Nothing Kept Me Up At Night the Way the Gorgon Stare Did.'*, Longreads](https://longreads.com/2019/06/21/nothing-kept-me-up-at-night-the-way-the-gorgon-stare-did/),
and the technology's civilian implications in
[Big Think, *The surveillance technology that will watch us all, all the time*](https://bigthink.com/the-present/gorgon-stare-surveillance/).

**Why WAMI is the most important precedent for 2026 CCTV.** WAMI is the only
operational system in history that has confronted the *true* scaling limit: the
data rate exceeded any possible number of analysts by orders of magnitude, so
**the imagery was collected and never looked at unless something happened**. The
institutional response was *forensic-first analytics* — automatic moving-target
indication (VMTI) to produce tracks, then archive them, then query on demand. See
[VMTI detection examples on the VIRAT aerial dataset](https://www.researchgate.net/figure/MTI-Detection-Examples-on-VIRAT-Aerial-Dataset-C-DARPA_fig3_280560670).
That is exactly the architecture that large CCTV estates converged on twenty years
later: **index everything, alert on almost nothing, make retrieval instant.**
Everyone who tries to build "alert me on everything interesting" across a
thousand-camera estate is re-fighting the battle WAMI lost in 2008.

### 15.3 Project Maven: the FMV-analytics programme, and the 2024–2026 pivot to a platform

> *"Project Maven was launched in 2017 to address major challenges with existing
> AI solutions in the US military inventory. The Algorithmic Warfare
> Cross-Functional Team (Project Maven) was established in 2017 under Deputy
> Secretary Robert Work."*
> — [GlobalSecurity.org, *Algorithmic Warfare Cross-Functional Team (AWCFT) / Project Maven*](https://www.globalsecurity.org/intell/systems/maven.htm);
> [Wikipedia, Project Maven](https://en.wikipedia.org/wiki/Project_Maven) (snippet)

Maven's original task was narrow and *exactly* the CCTV industry's task: **detect
and classify objects in full-motion video from tactical drones, so analysts stop
watching screens.** It is the single largest object-detection-in-video procurement
ever undertaken, and it is instructive that it began with the boring capability
(detection, labelling, track generation), not with intent inference.

The 2024–2026 evolution is the important part:

> *"In May 2024, the United States Army awarded Palantir USG a five-year
> indefinite-delivery, indefinite-quantity contract worth $480 million to build
> the MSS prototype, with completion scheduled by 28 May 2029."*
> — [The Defense Post](https://thedefensepost.com/2024/05/30/palantir-maven-battlefield-analyzer/);
> [C4ISRNET](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/)

> *"The five-year firm-fixed-price contract… will allow the Defense Department to
> expand its use to thousands of users at five combatant commands: U.S. Central
> Command, European Command, Indo-Pacific Command, Northern Command, and
> Transportation Command."*
> — [C4ISRNET](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/)

> *"The Maven Smart System is part of Project Maven, the Pentagon's marquis
> artificial intelligence program, which ingests and processes data from multiple
> sources, like satellite imagery and geolocation data, and uses it to
> automatically detect potential targets."*
> — [The Register](https://www.theregister.com/2024/05/30/palantir_us_army/)

> *"Pentagon leaders opted to boost the existing contract ceiling for Palantir
> Technologies' Maven Smart System by $795 million to prepare for what they expect
> will be a significant influx in demand from military users."*
> — [DefenseScoop (23 May 2025)](https://defensescoop.com/2025/05/23/dod-palantir-maven-smart-system-contract-increase/);
> further expansion reported in [Military.com (March 2026)](https://www.military.com/feature/2026/03/22/pentagon-expands-palantirs-role-ai-contract.html)

> *"Palantir Technologies provided the data integration layer that would later
> become the foundation of the Maven Smart System. Amazon Web Services supplied
> commercial cloud infrastructure. ECS Federal served as the prime AI Integration
> contractor, a role it has retained continuously since 2017."*
> — [Medium, *Project Maven: The Architecture of Algorithmic Warfare*](https://medium.com/@m.salah2405/project-maven-the-architecture-of-algorithmic-warfare-3ff147e7b520) **[weak source — VERIFY the contractor roles against a primary document]**

**The single most important observation in this dossier about the future of
commercial video analytics:** *Maven's centre of gravity moved from the detector to
the data-integration-and-workflow layer, and the money followed.* The
computer-vision models were the 2017 problem; by 2024 the contract of record was
awarded to a **data platform company**, and the thing being bought was *"the data
integration layer"* and access for *"thousands of users at five combatant
commands"*
([C4ISRNET](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/)).
This is the same movement as VMS-captures-value (§11.1), IBM-MILS-was-right
(§5.2), and Verkada-sells-the-estate (§13.1). **Four independent confirmations, in
four decades, that in video analytics the vision model is the commodity and the
data/workflow layer is the asset.**

Maven also carries the field's defining ethical episode: the 2018 employee revolt
at Google over its Maven participation, which produced Google's AI Principles and
the withdrawal from the contract. **[VERIFY dates and specifics — I had no search
budget; the episode is well documented and should be cited from a primary source
before external use.]** Its practical legacy is that the defence-AI supply chain
reorganised around vendors constituted to do defence work (Palantir, Anduril, Scale
AI), which is the direct cause of §15.4.

### 15.4 Anduril Lattice: autonomy at the sensor, at the border

> *"Anduril's Lattice is a software platform that ingests visual, radar and thermal
> sensor information and processes it with machine learning to model a 3D
> environment. The Autonomous Surveillance Towers use AI, machine learning and
> computer vision to identify border crossings."*
> — [Privacy International, *Dual-use tech: the Anduril example*](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example);
> [GovConWire](https://www.govconwire.com/articles/anduril-uav-uuv-lattice-homeland-security)

> *"The company announced in late 2024 that it had deployed its 300th Autonomous
> Surveillance Tower to CBP. Anduril Industries estimates that its Autonomous
> Surveillance Towers now cover 30 percent of the U.S. southern land border."*
> — [FedScoop, *CBP more than doubling autonomous sentry towers along Southwest border*](https://fedscoop.com/anduril-sentry-towers-cbp/)

> *"Anduril received a $363 million contract from Customs and Border Protection for
> more than 200 Extended Range Sentry Towers for autonomous surveillance along the
> U.S. southwest border."*
> — [Defense Daily](https://www.defensedaily.com/cbp-awards-anduril-363-million-for-extended-range-surveillance-towers/homeland-security/)

> *"The system uses radar to detect movement, then swivels a camera to classify
> what it sees using computer vision."*
> — [FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/)

> *"All new surveillance towers are required to be certified autonomous by CBP, and
> only Anduril's technology currently has this certification, meaning it enjoys an
> effective monopoly."*
> — [State of Surveillance](https://stateofsurveillance.org/news/anduril-border-surveillance-monopoly-big-beautiful-bill-2026/)

> *"Trump's One Big Beautiful Bill Act, signed into law in July 2025, grants a
> further $6bn for border security technology."*
> — [Privacy International](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example);
> see also [The Intercept, *Trump's Big Beautiful Gift to Anduril*](https://theintercept.com/2025/07/09/trump-big-beautiful-bill-anduril/)
> and the civil-liberties objection in [EFF, *California Coastal Community Must Reject CBP's AI-Powered Surveillance Tower*](https://www.eff.org/deeplinks/2026/04/california-coastal-community-must-reject-cbps-ai-powered-surveillance-tower).

**Note the architecture: "uses radar to detect movement, then swivels a camera to
classify what it sees"**
([FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/)). That is **VSAM's
layer 5 — sensor cueing and PTZ hand-off (§4.2) — deployed at national scale in
2025.** Twenty-eight years after the CMU/Sarnoff final report, the winning
architecture for wide-area outdoor surveillance is still *cheap wide-area
non-imaging detector cues an expensive narrow imaging classifier.* Not a
transformer end-to-end on video. The radar does the detection because radar is
robust to the things that break background models: weather, darkness, foliage.
**The single most reliable engineering lesson in this entire history is that a
second, physically-different sensor beats a better algorithm on the same sensor**
— which is R05's whole subject, and which SAMURAI argued in 2008
([CORDIS](https://cordis.europa.eu/project/id/217899)).

Also note the certification point: *"only Anduril's technology currently has this
certification"*
([State of Surveillance](https://stateofsurveillance.org/news/anduril-border-surveillance-monopoly-big-beautiful-bill-2026/)).
This is the i-LIDS effect (§6.1(2)) at ten thousand times the contract value: **an
approval regime professionalises a market and then hands it to whoever passed
first.**

### 15.5 NGA, Dstl and the allied research estate

The US **National Geospatial-Intelligence Agency** is the institutional owner of
the imagery-analysis mission and has run successive automation programmes
(including public challenges on object detection in overhead imagery), and the
UK's **Defence Science and Technology Laboratory (Dstl)** runs the corresponding
UK programme, distinct from the Home Office/NPSA CCTV lineage (a distinction R03
§2.1 is careful about). **[VERIFY all specifics on NGA and Dstl video-analytics
programmes — unretrieved in this session. Do not attribute a specific programme to
either body without a source.]**

---

## 16. Era 10 — 2023–2026: video-language models, "video agents", and world models

### 16.1 What actually changed

The 2023–2026 shift is not a better detector. It is the arrival of a **general
semantic layer that can be pointed at a video without being trained for the task**,
and a **natural-language interface** to it. Three concrete capability changes:

1. **Open-vocabulary description and search.** You no longer enumerate classes and
   rules. "Man in a red jacket carrying a ladder near the substation fence after
   dark" is now a query, not a development project. R05 covers the retrieval
   machinery; R03 §6 covers the language-grounded anomaly benchmarks.
2. **Alert adjudication.** The highest-value production use of a VLM in 2026 is not
   detection. It is **looking at a clip that a cheap detector already flagged and
   deciding whether to wake a human.** This is explicit in the reference
   architecture: the workflow *"combines 'perception (object detection, tracking)'
   with behavior analytics to generate initial alerts, then employs VLMs to verify
   and reduce false positives before surfacing them to users"*
   ([NVIDIA VSS Blueprint repository](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization), read directly).
3. **Summarisation of long video.** The blueprint is described as *"a
   GPU-accelerated reference architecture for building video analytics agents with
   real-time verified alerts, visual Q&A, and automated reporting"* using *"vision
   language models (VLMs) such as NVIDIA Cosmos, LLMs such as NVIDIA Nemotron,
   RAG, and NVIDIA NIMs"*
   ([NVIDIA VSS repository](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)).
   As of this reading the repository's develop branch pairs a **"Cosmos3 Nano
   Reasoner"** VLM with **"NVIDIA Nemotron 3.5 Lightning 30B A3B"** as the LLM,
   and ships three developer profiles — `dev-profile-base`, `dev-profile-search`,
   `dev-profile-alerts` — with the archive-search path marked *alpha*
   ([repository, read 2026-09](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)).

The vendor framing: *"NVIDIA made the AI Blueprint for video search and
summarization (VSS), powered by the NVIDIA Metropolis platform, generally
available — giving developers the tools to create and deploy highly capable AI
agents for analyzing vast sums of real-time and archived videos"*
([NVIDIA blog](https://blogs.nvidia.com/blog/ai-blueprint-video-search-and-summarization/));
*"This can be used to create vision AI agents that can be applied to use cases such
as monitoring smart spaces, warehouse automation, and SOP validation"*
([NVIDIA developer blog](https://developer.nvidia.com/blog/build-a-video-search-and-summarization-agent-with-nvidia-ai-blueprint/));
see also [Edge AI and Vision Alliance's coverage](https://www.edge-ai-vision.com/2025/05/ai-blueprint-for-video-search-and-summarization-now-available-to-deploy-video-analytics-ai-agents-across-industries/)
and [*Advance Video Analytics AI Agents Using the NVIDIA AI Blueprint for VSS*](https://developer.nvidia.com/blog/advance-video-analytics-ai-agents-using-the-nvidia-ai-blueprint-for-video-search-and-summarization/).

**Note which use cases NVIDIA leads with: smart spaces, warehouse automation, SOP
validation.** Not "detect crime". The industrial/operational market is where the
2020s semantic layer is monetising first, exactly as retail analytics (§5.3,
IntelliVid) monetised before security analytics in the 2000s. **The security use
case has always been the hardest to sell and the last to pay.**

### 16.2 World models: the supply side of the data problem

> *"NVIDIA's latest Cosmos-Predict2.5 is built on a flow-based architecture that
> unifies Text2World, Image2World, and Video2World generation in a single model and
> leverages Cosmos-Reason1, a Physical AI vision-language model, to provide richer
> text grounding and finer control of world simulation."*
> — [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/); the technical report is
> [*World Simulation with Video Foundation Models for Physical AI* (arXiv:2511.00062)](https://arxiv.org/abs/2511.00062) /
> [NVIDIA Research](https://research.nvidia.com/publication/2025-09_world-simulation-video-foundation-models-physical-ai)

> *"Cosmos-Predict2.5 was trained on 200M curated video clips and refined with
> reinforcement learning-based post-training, achieving substantial improvements
> over Cosmos-Predict1 in video quality and instruction alignment, with models
> released at 2B and 14B scales."*
> — [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/)

> *"Cosmos World Foundation Models are purpose-built for physical AI research and
> development, and can generate physics-based videos from a combination of inputs,
> like text, image and video, as well as robot sensor or motion data."*
> — [NVIDIA newsroom](https://nvidianews.nvidia.com/news/nvidia-launches-cosmos-world-foundation-model-platform-to-accelerate-physical-ai-development)

> *"The Cosmos family also includes Cosmos-Transfer2.5, a control-net style
> framework for Sim2Real and Real2Real world translation."*
> — [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/)

> *"NVIDIA Cosmos 3 serves as the backbone for World Action Models (WAMs) to
> accelerate robot policy learning."*
> — [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/);
> see also [NVIDIA Cosmos Lab](https://research.nvidia.com/labs/cosmos-lab)
> and [*Rethinking Video Generation Model for the Embodied World* (arXiv:2601.15282)](https://arxiv.org/pdf/2601.15282).

**Why this matters to *surveillance* specifically, and why it matters to this
repository.** The field's binding constraint, established repeatedly above, is
**labelled examples of rare events in operationally representative conditions**.
The three historical answers were: collect for years and hope (i-LIDS, 24 h per
scenario); stage it with actors (MEVA at Muscatatuck, §8.4); or accept tiny
academic proxies (R03 §3.4). **World models are the fourth answer**, and
`Cosmos-Transfer2.5`'s *"Sim2Real and Real2Real world translation"*
([NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/)) is precisely the
domain-gap tool R04 is about. The honest caveat is that a generative model's
physics and statistics are inherited from its training distribution, so
**generated rare events are rare events as the internet depicts them**, which is
not the same distribution as rare events as a car park experiences them. R04's
sim2real evidence base (MOTSynth, PeopleSansPeople) is the right prior for how
much of that gap can be closed.

### 16.3 The honest limits of the 2026 state of the art

- **Hallucinated description.** A VLM asked "what is happening" will answer
  fluently whether or not it knows. In an alerting system this is a
  false-positive generator with excellent prose. The mitigation in every serious
  architecture is to make the VLM a *verifier of a detector's hypothesis* rather
  than a generator of hypotheses (§16.1(2)).
- **Cost.** Continuous VLM inference on a thousand cameras is not affordable at
  2026 prices, which is why every shipping design is *cheap detector → cheap
  tracker → expensive model on a few clips*. The economics, not the accuracy, set
  the architecture.
- **Temporal reasoning over long horizons.** "Has this van passed here before this
  week?" is a database question that the language layer must be *given*, not one it
  can perceive. The metadata store is still the product (§5.2, §15.3).
- **Evaluation, again.** There is no i-LIDS for video agents. Nothing prevents a
  2026 vendor from making an AISight-class unfalsifiable claim in VLM clothing —
  and the market's memory is eight years long (§0).

---

## 17. Timeline table

| Year | Event | Significance |
|---|---|---|
| 1942 | Walter Bruch's CCTV at Test Stand VII, Peenemünde, for Siemens ([Lynztel](https://lynztel.com/en/blog/historia-de-los-sistemas-de-videovigilancia-del-cctv-militar-a-la-ia/)) | First CCTV; use case is remote presence, not security; live-only, no recording |
| 1949 | Vericon, Remington Rand / CBS Laboratories ([Lynztel](https://lynztel.com/en/blog/historia-de-los-sistemas-de-videovigilancia-del-cctv-militar-a-la-ia/)) | First commercial CCTV product |
| 1960 | Trafalgar Square temporary police cameras, 19–20 Jul 1960 (Thai state visit; MEPO 2/9956, secondary) `[audit R4]` | First widely-cited public-space policing use |
| 1968 | Olean, NY municipal street cameras (Sept 1968, verified in audit 2026-09-26) | First US city crime-prevention deployment |
| 1970s | CCTV into banks/commerce; VCRs; multiplexers ([DTiQ](https://www.dtiq.com/blog/video-surveillance/history-of-security-cameras)) | Creates the one-operator-many-cameras problem that analytics exists to solve |
| 1976 | ANPR invented at Home Office PSDB (Wilkins, Aston) ([Traffic Technology Today](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)) | First *successful* video analytic; constrained target + external register |
| 1979 | ANPR prototypes working; A1 and Dartford Tunnel trials ([TTT](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)) | Industrialisation via EMI Electronics and CRS |
| 1981 | First arrest on ANPR evidence ([TTT](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)) | Evidential use established |
| 1980s | VMD boom and false-alarm bust ([SMART Security Solutions](http://www.securitysa.com/regular.aspx?pklregularid=2904)) | The template for every later hype cycle |
| 1990s | Digital multiplexing, motion-only recording ([DTiQ](https://www.dtiq.com/blog/video-surveillance/history-of-security-cameras)); DVR; MPEG | Random-access archive enables forensic search and metadata |
| 1997–1999 | **DARPA VSAM**, CMU + Sarnoff ([CMU final report](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)) | Defines the pipeline used commercially for ~15 years; framed for *battlefield awareness* |
| 2000 | **PETS'2000** begins (FG 2000) ([PETS@CVG](http://www.cvg.reading.ac.uk/slides/pets.html)) | Performance evaluation becomes a subfield |
| 2000–2003 | EU **ADVISOR** (metro, Spain & Belgium) ([CORDIS](https://cordis.europa.eu/article/id/81538-automated-visual-surveillance-systems)); **PRISMATICA** | Transport-led European strand; "retrieval" in the title from the start |
| 2001 | Ipsotek founded ([ISJ](https://internationalsecurityjournal.com/security-business-index/ipsotek/)); IEEE **AVSS** series begins **[VERIFY]** | UK vendor lineage; the field's dedicated venue |
| 2001–2008 | Post-9/11 VCA boom: ObjectVideo VEW, ioimage, Vidient SmartCatch, Cernium Perceptrak, IntelliVid, 3VR, Agent Vi, NiceVision | Tripwire/ROI becomes the universal UI metaphor |
| 2003 | IntelliVid founded/retail analytics ([SSN](https://www.securitysystemsnews.com/article/tyco-acquires-retail-focused-analytics-vendor-intellivid)); Vidient spun out of NEC ([IPVM](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence)) | Retail BI diverges from security alerting |
| 2004 | **IBM S3 / MILS** ([Springer MVA](https://link.springer.com/article/10.1007/s00138-008-0153-z)) | "Video analytics is a database problem" — correct 16 years early |
| 2005 | i-LIDS sample released on DVD ([IEEE](https://ieeexplore.ieee.org/document/4123801)); **Keeneo** founded from Inria Orion/VSIP ([Inria](https://raweb.inria.fr/rapportsactivite/RA2010/pulsar/uid14.html)); BRS Labs founded ([SEC](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm)); China's **Skynet** launched ([Grey Dynamics](https://greydynamics.com/the-xeuliang-project-expansion-of-chinas-state-surveillance-programme/)) | The single densest year in this history |
| 2006 | **i-LIDS launched** ([i-LIDS brochure](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf)) | First real procurement-grade evaluation instrument; four scenarios fixed for 20 years |
| 2008 | **ONVIF founded** ([ONVIF](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/)); EU **SAMURAI** starts ([CORDIS 217899](https://cordis.europa.eu/project/id/217899)); Constant Hawk/WAMI in theatre | Interoperability begins; operator-in-the-loop learning proposed |
| 2009 | **INDECT** begins, €10.91m ([EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)); PETS 2009 crowd dataset | Politics of "abnormal behaviour" detonates in Europe |
| 2010 | **Vidient ceases operations** ([IPVM](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence)); DARPA **Mind's Eye** begins ([SPIE](https://spie.org/news/5489-automated-recognition-of-human-activities-in-video-streams-in-real-time)) | Commercial bust; research moves to "visual intelligence" |
| 2011 | **VIRAT** at CVPR ([UCF CRCV](https://www.crcv.ucf.edu/research/data-sets/virat/)); **Gorgon Stare** fielded ([SNC](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/)); **ObjectVideo sues Bosch/Sony/Samsung** ([SecurityInfoWatch](https://www.securityinfowatch.com/video-surveillance/news/10485600/objectvideo-sues-bosch-sony-and-samsung-over-alleged-patent-infringement-in-the-area-of-video-content-analytics)); Keeneo → Digital Barriers ([Inria](https://raweb.inria.fr/rapportsactivite/RA2010/pulsar/uid14.html)) | Events replace tracks as the benchmark unit; patents replace products |
| 2012 | AlexNet (ILSVRC) | Inflection — but no product impact for ~4 years |
| 2014 | INDECT ends ([Reuters](https://www.investing.com/news/world-news/irked-by-u.s.,-but-eu-keeps-own-spy-projects-quiet-351693)); Canon acquires Milestone **[VERIFY]** | European retreat from behaviour-profiling language |
| 2015 | NDRC mandates 100% public-space coverage → **Sharp Eyes** ([CSET](https://cset.georgetown.edu/article/chinas-sharp-eyes-program-aims-to-surveil-100-of-public-space/)); NICE exits video → **Qognify** ([IPVM](https://ipvm.com/reports/nice-is-out-of-the-video-surveillance-business)) | Chinese demand curve set; Western incumbent exits |
| 2016–2018 | Deep detectors and re-ID reach product; **Avigilon Appearance Search** | Forensic search is where deep learning first pays |
| 2017 | **Project Maven** established ([GlobalSecurity](https://www.globalsecurity.org/intell/systems/maven.htm)); **PETS ends** ([IEEE](https://ieeexplore.ieee.org/document/8014998/)); SEC charges BRS Labs/Giant Gray ([SEC](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm)) | ISR automation at scale; surveillance-specific evaluation community dissolves; the behaviour-learning story ends in fraud charges |
| 2018 | **Motorola acquires Avigilon, ~$1.0bn** ([Motorola](https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-completes-acquisition-avigilon.html)); **NDAA FY2019 §889** ([EAC](https://www.eac.gov/what-section-889-fy-2019-ndaa)) | Analytics consolidates into radio/public-safety; geopolitics enters procurement |
| 2018–2020 | **IARPA DIVA** / NIST **ActEV** / **MEVA** at Muscatatuck ([NIST](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation), [MEVA](https://mevadata.org/)) | US builds its i-LIDS, fifteen years late, in a deep-learning idiom; staged data legitimised |
| 2020 | **Bridges v South Wales Police** [2020] EWCA Civ 1058 ([judgment](https://www.judiciary.uk/wp-content/uploads/2020/08/R-Bridges-v-CC-South-Wales-ors-Judgment.pdf)) | First successful legal challenge to AFR; framework, not abolition |
| 2021 | **ONVIF Profile M** ([ONVIF](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/)); **Atos acquires Ipsotek** ([Atos](https://atos.net/en/2021/press-release_2021_04_20/atos-reinforces-its-leading-position-in-the-edge-and-computer-vision-market-through-the-acquisition-of-ipsotek)); **Irisity acquires Agent Vi, SEK 650m** ([Irisity](https://irisity.com/about-us/)) | Analytics metadata finally standardised; last independent specialists absorbed |
| 2022 | **Clearview fined** £7.5m ICO / €20m Garante / €20m CNIL ([ICO](https://ico-newsroom.prgloo.com/news/ico-fines-facial-recognition-database-company-clearview-ai-inc-more-than-gbp-7-5m-and-orders-uk-data-to-be-deleted), [EDPB](https://www.edpb.europa.eu/news/national-news/2022/facial-recognition-italian-sa-fines-clearview-ai-eur-20-million_en), [CNIL via DPM](https://dataprivacymanager.net/cnil-issues-e20-million-gdpr-fine-to-clearview-ai/)); **UK bans Chinese cameras at sensitive sites** ([Clearway](https://www.clearway.co.uk/news/ndaa-compliant-security-cameras-a-guide-for-uk-organisations/)); **Hexagon acquires Qognify** ([Hexagon](https://hexagon.com/company/newsroom/press-releases/2022/hexagon-strengthens-its-physical-security-and-incident-management-capabilities-with-the-acquisition-of-qognify)); Verkada at $3.2bn ([SSI](https://www.securitysales.com/news/verkada-raises-205m-valued-3-2b/146112/)) | Data provenance becomes the binding constraint; cloud model validated |
| 2023 | Clearview wins jurisdictional appeal vs ICO ([Digital Watch](https://dig.watch/updates/clearview-ai-wins-appeals-gdpr-case-against-uks-ico)); VLMs enter video products | The legal position is less settled than reported |
| 2024 | **Palantir wins $480m Maven Smart System** ([C4ISRNET](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/)); **Axon Draft One** ([Axon](https://investor.axon.com/2024-04-23-Axon-reimagines-report-writing-with-Draft-One,-a-first-of-its-kind-AI-powered-force-multiplier-for-public-safety)); **Axon acquires Fusus** ([Vice](https://www.vice.com/en/article/axon-acquires-fusus-ai-surveillance-retail-healthcare/)); Anduril's 300th CBP tower ([FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/)) | The value moves to the data/workflow layer; genAI's first mass deployment is *writing*, not seeing |
| 2025 | **NVIDIA VSS blueprint GA** ([NVIDIA](https://blogs.nvidia.com/blog/ai-blueprint-video-search-and-summarization/)); **Cosmos** WFM platform ([NVIDIA](https://nvidianews.nvidia.com/news/nvidia-launches-cosmos-world-foundation-model-platform-to-accelerate-physical-ai-development)); Maven ceiling +$795m ([DefenseScoop](https://defensescoop.com/2025/05/23/dod-palantir-maven-smart-system-contract-increase/)); Anduril $363m ER towers ([Defense Daily](https://www.defensedaily.com/cbp-awards-anduril-363-million-for-extended-range-surveillance-towers/homeland-security/)); UK Chinese-camera removal deadline enforced ([Clearway](https://www.clearway.co.uk/news/ndaa-compliant-security-cameras-a-guide-for-uk-organisations/)); Ambient.ai $74m ([Tracxn](https://tracxn.com/d/companies/ambient-ai/__o3P0l5V7BKOZZr3yfissd1iMGgTNb4kFRNlvBdq9MNg/funding-and-investors)); **Verkada $5.8bn, >$1bn bookings, >2m devices** ([CNBC](https://www.cnbc.com/2025/12/03/verkada-capitalg-valuation-security.html), [PRN](https://www.prnewswire.com/news-releases/verkada-reaches-5-8b-valuation-with-investment-from-capitalg-302631378.html)) | The "video agent" architecture becomes a reference design; world models become a data-supply strategy |
| 2026 | Pentagon expands Palantir's AI role ([Military.com](https://www.military.com/feature/2026/03/22/pentagon-expands-palantirs-role-ai-contract.html)); Cosmos 3 / WAMs ([NVIDIA](https://www.nvidia.com/en-us/ai/cosmos/)); local resistance to AI towers ([EFF](https://www.eff.org/deeplinks/2026/04/california-coastal-community-must-reject-cbps-ai-powered-surveillance-tower)) | Consolidation of the agent/platform pattern; the legitimacy fight localises |

---

## 18. Dead ends and lessons (eighteen, ranked by how expensive the lesson was)

**L1. An unfalsifiable product specification is a fraud vector, whatever the
founder intends.** BRS Labs sold "detects abnormal behaviour" with no definition of
abnormal, therefore no acceptance test, therefore no way for procurement to fail
it; the story ends in an SEC complaint alleging *"over $28 million"* raised through
*"repeated lies"* ([SEC](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm)).
**Rule: if you cannot write the acceptance test before the contract, do not sign
the contract.** (R03 §2.3 has the test to write.)

**L2. Statistical rarity is not operational significance.** The entire
unsupervised-anomaly product category foundered on this. The cleaner at 3 am is
rare; the hostile reconnaissance walk-past at 2 pm is not. Optimise for
significance, and you need supervision or a semantic layer; optimise for rarity, and
you ship an alarm generator.

**L3. Detection is not the product; the alarm queue is.** Every 2000s pure-play
that OEM'd its engine into someone else's VMS lost the customer relationship and
then the margin (§5.3, §11.1). Four decades, four confirmations, most recently
Maven's money moving to *"the data integration layer"*
([Medium synthesis](https://medium.com/@m.salah2405/project-maven-the-architecture-of-algorithmic-warfare-3ff147e7b520) **[weak source]**,
and structurally in the [C4ISRNET account](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/)).

**L4. The right architecture arriving before the channel that can sell it is
indistinguishable from the wrong architecture.** IBM S3 in 2004 had the 2024
architecture and the 1994 distribution model ([Springer MVA](https://link.springer.com/article/10.1007/s00138-008-0153-z)).
It lost to products that were worse and installable by an electrician.

**L5. Substrate bets have shorter half-lives than product cycles.** The
on-camera-DSP generation was right about economics and lost anyway, because the
workload changed character in three years and the hardware had a ten-year life
(§7.4). **Corollary for 2026: a camera shipping a fixed INT8 CNN NPU today is
exposed to the transformer workload exactly as ioimage was exposed to CNNs.**

**L6. A marquee reference account is not a business.** Vidient: an SFO deployment,
*"over $30 Million USD of venture funding"*, operations ceased November 2010
([IPVM](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence)).
Airports tender once a decade and demand bespoke work.

**L7. Licensing your patents to your customers accelerates the commoditisation you
are trying to tax.** ObjectVideo's ITC campaign ended with the major OEMs licensed
and shipping tripwire for free
([Bloomberg](https://www.bloomberg.com/news/articles/2011-06-30/sony-samsung-techwin-targeted-by-objectvideo-in-itc-patent-case);
[GSN](https://www.gsnmagazine.com/article/25564/new_strategy_objectvideo_agrees_license_its_video_)).

**L8. Hand-built ontologies do not scale to semantics.** DARPA Mind's Eye's 48
verbs ([SPIE](https://spie.org/news/5489-automated-recognition-of-human-activities-in-video-streams-in-real-time))
were the bottleneck, not the perception. The ontology has to be *learned*, which is
what VLMs do and what 2010 could not do.

**L9. Open, mediocre data beats closed, excellent data at setting the research
agenda.** i-LIDS is *"widely regarded as the most comprehensive of their kind"*
([i-LIDS brochure](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf))
and academically almost unused; 67 seconds of UCSD Ped2 defines the published state
of the art (R03 §3.4, §7). If you want to influence the field, publish the data.

**L10. The words you use are part of the risk surface.** INDECT described
accurately what the field had been doing since ADVISOR and was destroyed for it —
*"'Orwellian' artificial intelligence plan to monitor public for 'abnormal
behaviour'"* ([EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)),
with an ethics board *"dominated by Police Officers and had no privacy experts"*
([EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)).
Governance theatre is worse than no governance, because it is evidence of intent.

**L11. A second, physically different sensor beats a better algorithm on the same
sensor.** SAMURAI argued it in 2008 (*"networked heterogeneous sensors rather than
CCTV cameras alone"*, [CORDIS](https://cordis.europa.eu/project/id/217899));
Anduril is winning a national border programme with it in 2025 (*"uses radar to
detect movement, then swivels a camera to classify"*,
[FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/)). This is R05's thesis
and the most reliable engineering lesson in the dossier.

**L12. Same detector, two cost functions, two markets.** Record-on-motion succeeded
and alarm-on-motion failed with identical algorithms (§2.2). **Always ask who pays
for the false positive before asking how accurate it is.**

**L13. Approval regimes professionalise a market and then hand it to whoever passed
first.** i-LIDS built a UK CNI moat (§6.1); CBP's autonomy certification produced
*"an effective monopoly"* ([State of Surveillance](https://stateofsurveillance.org/news/anduril-border-surveillance-monopoly-big-beautiful-bill-2026/)).
Both effects are real and you cannot have the first without the second.

**L14. "Replace the operator" is unsellable; "make the operator's shift bearable" is
sellable.** Headcount-reduction ROI cannot be banked by a security director. The
propositions that pay are verified-alarm police response, insurance, forensic-search
hours, and merchandising data — i.e. **Cernium's CheckVideo pivot and IntelliVid's
retail framing were right, and the enterprise-licence model was wrong.**

**L15. Analytics performance was never standardised, and that vacuum is why the
market gets re-fooled every eight years.** ONVIF standardised interfaces in 2008 and
metadata in 2021 ([ONVIF](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/));
nobody standardised *accuracy* outside closed government schemes (§11.4).

**L16. Index everything, alert on almost nothing.** WAMI lost the
alert-on-everything battle at a data rate no analyst pool could absorb, and the
institutional answer was forensic-first: automatic track generation, archive,
query on demand ([Lexington Institute](https://lexingtoninstitute.org/wide-area-persistent-surveillance-revolutionizes-tactical-isr/)).
Large CCTV estates converged on the same answer twenty years later. Anyone pitching
"alerts on everything interesting across 2,000 cameras" is re-fighting a lost war.

**L17. Staging data is legitimate and sometimes the only option.** IARPA's answer to
"where do we get labelled activity data" was to hire *"over 100 actors"* at a real
urban training centre ([MEVA](https://mevadata.org/)). The objection to simulation is
therefore a sim2real *fidelity* argument, not a legitimacy argument — which is
exactly the argument R04 engages.

**L18. Generative AI's first mass success in this domain was writing, not seeing.**
Draft One — *"the fastest-selling product in Axon's history"*
([CUNY Journalism](https://coveringcompanies.journalism.cuny.edu/2025/11/05/axon-trades-tasers-for-tech-in-software-and-ai-push/))
— is transcription and narrative drafting. **When a new general capability arrives,
its first money is in the paperwork, not in the perception.** Expect the same for
video agents: incident reports, handover summaries, and audit trails before
detection.

---

## 19. What gets added next: 2026–2035, eighteen argued predictions

Each prediction states the mechanism, the evidence from this history, and what
would falsify it.

**P1. Two-stage cheap-detector/expensive-verifier becomes the universal
architecture, and the "analytics engine" stops being a distinct product.**
*Mechanism:* the cost asymmetry between a CNN detector (fractions of a watt per
stream) and a VLM (GPU-seconds per clip) is structural, not transient, so the
economically optimal design is always to spend the expensive model only on
candidates. *Evidence:* it is already the reference design — the VSS workflow
*"employs VLMs to verify and reduce false positives before surfacing them to
users"* ([NVIDIA VSS repo](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)).
*Falsified if:* per-token inference cost falls enough that continuous
frame-by-frame semantic parsing of 1,000 streams costs less than the storage does.

**P2. Alarm adjudication becomes a metered utility (a "second opinion API"),
priced per adjudication.** *Mechanism:* it is the one task with a clean
input (a clip plus a hypothesis), a clean output (confirm/deny plus a sentence),
and a directly measurable saving (guard dispatches avoided). *Evidence:* the entire
monitoring-centre economics of CheckVideo (§5.3) and of the current cohort (§13.2)
already price on verified alarms. *Falsified if:* liability law makes third-party
adjudication uninsurable.

**P3. Natural-language search fully commoditises by ~2029 and stops being a
differentiator, exactly as tripwire did by 2012.** *Mechanism:* step 5 of §0. The
capability is a thin layer over an embedding index and a VLM; both become
commodities. *Evidence:* the capability is already a downloadable reference
blueprint ([NVIDIA](https://blogs.nvidia.com/blog/ai-blueprint-video-search-and-summarization/)),
which is what "about to be free" looks like. *Falsified if:* proprietary
domain-specific video encoders prove durably better than general ones on
surveillance imagery.

**P4. The durable moat moves to the *index*, not the model: whoever holds the
multi-year, cross-camera, geo-registered metadata store wins.** *Mechanism:* the
questions operators actually ask are historical and relational ("has this vehicle
been here before?", "is this the same person as Tuesday?"), and those are database
questions. *Evidence:* four independent confirmations across four decades — MILS
(2004), the VMS layer (2000s), WAMI's forensic-first pivot, and Maven's money going
to the integration layer (§15.3). *Falsified if:* privacy law forces short retention
across the board, destroying the asset (see P14 — these two predictions are in
direct tension, and that tension is the central commercial uncertainty of the
decade).

**P5. Operator-in-the-loop online adaptation returns as a first-class feature, and
is the main source of accuracy gains after 2027.** *Mechanism:* with a general
semantic layer, the scarce resource is site-specific adjudication, and every
operator dismissal is a free label. *Evidence:* SAMURAI proposed exactly this in
2008 ([CORDIS](https://cordis.europa.eu/project/id/217899)); the field abandoned it
because offline-trained nets seemed sufficient, and the residual false-alarm tail
(§9.2) is precisely site-specific. *Falsified if:* per-site fine-tuning proves to
cost more than it saves at realistic estate sizes.

**P6. Geo-registration and calibration become automated and therefore universal —
which is the biggest single unlock for cross-camera analytics.** *Mechanism:*
monocular metric depth, learned camera-pose estimation and SfM over archive footage
can now recover ground planes and inter-camera geometry without a surveyor.
*Evidence:* VSAM specified geo-registration as layer 4 in 1999
([CMU](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/))
and the industry has skipped it for 25 years because it required manual work; §7.1(3)
says manual work is the binding cost. *Falsified if:* automatic calibration remains
too inaccurate for metric reasoning in the >30 m regime.

**P7. The natural-language query box becomes the new control point, and the VMS
vendors will fight to own it rather than expose it.** *Mechanism:* §11.1's law — the
layer owning operator attention captures value. *Evidence:* the historical sequence
multiplexer → VMS → cloud console. *Falsified if:* an open protocol for video-agent
queries is adopted before the platform vendors close it (see P9).

**P8. Behaviour-learning returns, rebranded and *bounded*: unsupervised prior for
candidate generation, VLM for significance, with a published false-alarm-rate
figure.** *Mechanism:* the 2008 pitch was right about the prior and had nothing for
significance (§5.4). Both halves now exist. *Evidence:* viisights and the
scene-conditioned anomaly literature (R03 §3.6, §3.11). *Falsified if:* the
significance judgement proves to require site context that no VLM has access to —
which is the serious objection.

**P9. ONVIF (or a successor) must standardise the transport of embeddings and
natural-language descriptions, and will do so by ~2028.** *Mechanism:* Profile M's
schema is object-and-event shaped ([spec](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf))
and cannot carry a vector or a caption, so multi-vendor agent pipelines currently
cannot interoperate at the semantic layer. *Evidence:* the 2008→2021 lag for
metadata shows the forum moves only when the market's pain is acute, and the pain is
becoming acute. *Falsified if:* the market accepts vertical lock-in at the semantic
layer, which on the evidence of §11.2 is quite possible.

**P10. Synthetic and generated data become the default source of rare-event
training data, with a formal sim2real validation step in procurement.**
*Mechanism:* the constraint is labelled rare events (§14.3(2)) and world models are
the fourth answer after "wait", "stage it", and "use a tiny proxy" (§16.2).
*Evidence:* MEVA's staged-actor precedent ([MEVA](https://mevadata.org/));
Cosmos-Transfer2.5 as an explicit *"Sim2Real and Real2Real"* tool
([NVIDIA](https://www.nvidia.com/en-us/ai/cosmos/)); R04's measured sim2real
results. *Falsified if:* generated-event distributions prove so biased that
models trained on them degrade on real data — R04's evidence says partially, not
fatally.

**P11. A public, vendor-neutral conformance regime for video analytics finally
appears — driven by insurance and by the EU AI Act's conformity-assessment
machinery, not by the security industry.** *Mechanism:* the industry has had thirty
years to build one and has not (L15); regulators and insurers have the incentive and
the leverage. *Evidence:* NDAA 889 showed that *compliance* can become the primary
purchase criterion (§10.3); the AI Act creates a conformity-assessment apparatus
looking for technical standards to point at. *Falsified if:* the AI Act's
high-risk obligations are diluted to documentation-only.

**P12. Edge NPUs sized for transformers arrive, the workload moves back to the
camera again, and a second generation of stranded hardware is created.**
*Mechanism:* the oscillation edge→server→cloud→edge is driven by where the newest
workload's compute is cheapest, and it has a ~7-year period. *Evidence:* §7.4's
history. *Falsified if:* cameras become pure sensors with all compute pooled — which
is the cloud vendors' explicit strategy and could break the cycle.

**P13. Multi-sensor becomes the default for outdoor detection, and camera-only
outdoor perimeter analytics becomes a legacy category.** *Mechanism:* L11, plus
collapsing costs for mmWave radar and cheap LiDAR. *Evidence:* Anduril's
radar-cues-camera design winning at national scale
([FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/)); R05. *Falsified if:*
thermal-plus-VLM proves cheap enough to dominate radar on cost.

**P14. Retention limits, not accuracy limits, become the main constraint on
capability in Europe and the UK by ~2030.** *Mechanism:* the most valuable analytics
(cross-camera identity, revisit detection, pattern-of-life) all require long
retention of person-linked data, which is what data-protection law most directly
restricts. *Evidence:* the Clearview actions were about *provenance and retention*,
not accuracy ([ICO](https://ico-newsroom.prgloo.com/news/ico-fines-facial-recognition-database-company-clearview-ai-inc-more-than-gbp-7-5m-and-orders-uk-data-to-be-deleted));
the *Bridges* holding was about *watchlist discretion*, not error rate
([judgment](https://www.judiciary.uk/wp-content/uploads/2020/08/R-Bridges-v-CC-South-Wales-ors-Judgment.pdf)).
*Falsified if:* privacy-preserving indexing (on-device embeddings, irreversible
templates, differential-privacy aggregates) satisfies regulators — which is the
research direction to watch.

**P15. Live facial recognition expands in the UK under a codified authorisation
regime, and the fight moves to *what goes on the watchlist*.** *Mechanism:*
*Bridges* required a tighter framework, not abolition, and the Home Office responded
by building one ([*What next for automated facial recognition*](https://videosurveillance.blog.gov.uk/2020/08/11/what-next-for-automated-facial-recognition)).
*Evidence:* deployments grew after the judgment. *Falsified if:* primary legislation
imposes a moratorium.

**P16. Real-Time Crime Centres consolidate private camera estates into public
operations, and this becomes the central civil-liberties battleground of the late
2020s — fought locally, council by council.** *Mechanism:* the marginal cost of
adding a private camera to a public console is near zero once the platform exists
(Fusus: *"allow police and other public agencies to analyze a wide array of video
sources at a single point"*, [Vice](https://www.vice.com/en/article/axon-acquires-fusus-ai-surveillance-retail-healthcare/)),
and it is procured municipally, below the threshold of national debate. *Evidence:*
the localisation is already visible ([EFF on a single Californian tower](https://www.eff.org/deeplinks/2026/04/california-coastal-community-must-reject-cbps-ai-powered-surveillance-tower)).
*Falsified if:* state-level laws pre-empt municipal aggregation.

**P17. "Video agent" hype produces at least one AISight-class scandal before
2030.** *Mechanism:* the preconditions are identical — an unfalsifiable claim
("our agent understands what's happening"), no conformance regime (L15), a
credulous capital market, and an eight-year market memory. *Evidence:* six cycles
of §0's arc; the 1980s VMD language reading identically to 2000s and 2010s language
([SMART Security Solutions](http://www.securitysa.com/regular.aspx?pklregularid=2904)).
*Falsified if:* P11's conformance regime arrives first — which is the strongest
practical argument for building it.

**P18. The profitable centre of gravity moves out of security entirely — into
industrial safety, SOP compliance, logistics and retail operations — as it did in
the 2000s.** *Mechanism:* those buyers have measurable throughput and safety
economics, tolerate false positives better, and have no civil-liberties exposure.
*Evidence:* NVIDIA leads its video-agent marketing with *"monitoring smart spaces,
warehouse automation, and SOP validation"*
([NVIDIA developer blog](https://developer.nvidia.com/blog/build-a-video-search-and-summarization-agent-with-nvidia-ai-blueprint/)),
and IntelliVid's retail framing outlived every security pure-play of its generation
(§5.3). *Falsified if:* insurance-driven security ROI (P11) matures faster than
industrial adoption.

### 19.1 Three things I predict will *not* happen, and why

- **Reliable machine inference of hostile intent.** Not by 2035. R03 §4's argument
  is not about model capacity; it is that the target variable is unobservable and
  the base rate is vanishing. The failures (TSA SPOT) were failures of the problem
  statement.
- **Fully unattended alerting on open public space at acceptable false-alarm
  rates.** The residual nuisance set is adversarially person-shaped (§9.2), and the
  cost of a false dispatch is borne by the operator, not the vendor (L12).
- **A single end-to-end model replacing the pipeline.** The two-stage economics
  (P1) and the index moat (P4) are both structural. Expect the pipeline to persist
  and the *components* to be replaced.

---

## 20. Appendix: hop-chain provenance

How this dossier reached eight hops from its seeds. Each chain lists the
information hop, not the search query.

### Chain A — the research lineage (8 hops)
1. **Seed:** "DARPA VSAM 1997–2000" → [CMU VSAM Final Report](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)
   (Kanade, Collins; contract DAAB07-97-C-J031).
2. → **Sarnoff** as the industrial partner → registration/mosaicking lineage →
   §4.3, and the aerial branch.
3. → Aerial branch → **VIRAT aerial** provided by DARPA
   ([UCF CRCV](https://www.crcv.ucf.edu/data/VIRAT.php)).
4. → VIRAT's event framing → **DARPA Mind's Eye** 48 activities
   ([SPIE](https://spie.org/news/5489-automated-recognition-of-human-activities-in-video-streams-in-real-time)).
5. → Mind's Eye's successor in activity detection → **IARPA DIVA**
   ([NIST ActEV](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)).
6. → DIVA's data → **MEVA at Muscatatuck, >100 actors** ([MEVA](https://mevadata.org/)).
7. → "staged data is legitimate" → **world models as the next staging mechanism**
   → [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/),
   [Cosmos technical report (arXiv:2511.00062)](https://arxiv.org/abs/2511.00062).
8. → Cosmos-Transfer2.5's *"Sim2Real and Real2Real world translation"* → closes
   onto **R04's sim2real evidence base** — i.e. the 1997 battlefield-awareness
   programme and this repository's simulator are eight hops apart on one chain.

### Chain B — the Franco-British commercial lineage (8 hops)
1. **Seed:** "Digital Barriers, UK video analytics" → SafeZone-edge.
2. → *"SafeZone-edge derives from a product… brought into Digital Barriers with the
   acquisition of Keeneo"* ([Digital Barriers support](https://safezone-support.digitalbarriers.com/support/solutions/articles/4000019371-what-is-safezone-edge-)).
3. → **Keeneo** → *"created in July 2005 for the industrialization and exploitation
   of Orion and Pulsar results… including the VSIP library"*
   ([Inria Pulsar report](https://raweb.inria.fr/rapportsactivite/RA2010/pulsar/uid14.html)).
4. → **Inria Orion/Pulsar** → **Monique Thonnat** and **François Brémond**
   ([Thonnat, Inria](http://www-sop.inria.fr/members/Monique.Thonnat/Monique.Thonnatfr.html);
   [Brémond CV](http://www-sop.inria.fr/members/Francois.Bremond/Postscript/cv-2018-en.pdf)).
5. → **VSIP's design principle**: *"separates algorithms from a priori knowledge"*
   ([Inria activity report](http://www-sop.inria.fr/stars/Documents/Activity%20Report/FullActivityReportStars2012.html)).
6. → the same principle in **IBM MILS** (*"open and extensible framework"*,
   [Springer MVA](https://link.springer.com/article/10.1007/s00138-008-0153-z)).
7. → the same principle standardised as **ONVIF Profile M** (2021)
   ([spec](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf)).
8. → Profile M's inability to carry embeddings/captions → **prediction P9**, and
   the lab itself continues as **Inria STARS**
   ([STARS 2024](https://radar.inria.fr/report/2024/stars/index.html)).

### Chain C — the evaluation lineage (8 hops)
1. **Seed:** "Home Office i-LIDS 2006" → [IEEE i-LIDS paper](https://ieeexplore.ieee.org/document/4123801).
2. → **HOSDB + the Security Service**; CAST + CPNI as owners
   ([i-LIDS User Guide](https://www.securityindustry.org/wp-content/uploads/2017/08/iLids-User-Guide.pdf)).
3. → i-LIDS scoring → the 10-second event window (R03 §2.3, citing the
   [Sensors 2022 PIDS survey](https://pubmed.ncbi.nlm.nih.gov/35591289/)).
4. → the metric ancestry → **VACE and CLEAR** consortia, via PETS 2009
   ([PETS@CVG](http://www.cvg.reading.ac.uk/slides/pets.html)).
5. → **PETS series 2000→2017** ([PETS 2017](https://ieeexplore.ieee.org/document/8014998/)),
   and its end.
6. → the successor: **TRECVID** absorbing ActEV
   ([TRECVID 2019](https://arxiv.org/pdf/2009.09984)).
7. → **ActEV's AD/AOD/AODT task ladder** ([NIST](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)),
   whose top rung is cross-camera identity.
8. → cross-camera identity → **R02**, and the observation that the legal route to
   it is closing as the technical route opens (§12.2) → **P14**.

### Chain D — the geopolitical/commercial lineage (8 hops)
1. **Seed:** "ObjectVideo patents" → [SecurityInfoWatch](https://www.securityinfowatch.com/video-surveillance/news/10485600/objectvideo-sues-bosch-sony-and-samsung-over-alleged-patent-infringement-in-the-area-of-video-content-analytics).
2. → ITC action and licences to Sony/OEMs
   ([Bloomberg](https://www.bloomberg.com/news/articles/2011-06-30/sony-samsung-techwin-targeted-by-objectvideo-in-itc-patent-case);
   [SSI](https://www.securitysales.com/news/objectvideo-sony-enter-into-patent-license-agreement/28451/)).
3. → OEMs ship analytics in firmware → commoditisation → the 2008–2013 bust
   ([IPVM on Vidient](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence),
   [Cernium](https://ipvm.com/reports/cernium-shifts-strategy-again-checkvideo),
   [3VR](https://ipvm.com/reports/3v-identiv),
   [NICE](https://ipvm.com/reports/nice-is-out-of-the-video-surveillance-business)).
4. → commoditisation's winners: Chinese volume manufacturers, driven by
   **Skynet/Sharp Eyes** demand ([CSET](https://cset.georgetown.edu/article/chinas-sharp-eyes-program-aims-to-surveil-100-of-public-space/),
   [IPVM](https://ipvm.com/reports/sharpeyes)).
5. → **NDAA §889** and the UK 2022 directive
   ([IPVM](https://ipvm.com/reports/hikua-bans);
   [Clearway](https://www.clearway.co.uk/news/ndaa-compliant-security-cameras-a-guide-for-uk-organisations/)).
6. → "NDAA-compliant" as a category → re-opened Western hardware market →
   **Verkada at $5.8bn** ([CNBC](https://www.cnbc.com/2025/12/03/verkada-capitalg-valuation-security.html)),
   Rhombus's compliance-forward positioning ([Rhombus](https://www.rhombus.com/blog/ndaa-compliant-security-cameras/)).
7. → cloud consoles need a semantic layer → **the AI-native cohort**
   (Ambient.ai's *"applies AI to existing camera infrastructure"*,
   [Tracxn](https://tracxn.com/d/companies/ambient-ai/__o3P0l5V7BKOZZr3yfissd1iMGgTNb4kFRNlvBdq9MNg/funding-and-investors)).
8. → that semantic layer's reference design → **NVIDIA VSS**, with the VLM as
   *verifier* ([repo, read directly](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)) →
   **P1 and P3**.

### Chain E — the defence/civil convergence (7 hops)
1. **Seed:** "Gorgon Stare" → [SNC Increment 2](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/).
2. → its EO sensor *"derived from DARPA's ARGUS technology… manufactured by BAE
   Systems"* ([SNC](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/)).
3. → WAMI's analyst-saturation problem → forensic-first analytics
   ([Lexington](https://lexingtoninstitute.org/wide-area-persistent-surveillance-revolutionizes-tactical-isr/)).
4. → the FMV-automation programme response: **Project Maven** 2017
   ([GlobalSecurity](https://www.globalsecurity.org/intell/systems/maven.htm)).
5. → Maven's value migrating to the platform: **Palantir MSS $480m → +$795m**
   ([C4ISRNET](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/);
   [DefenseScoop](https://defensescoop.com/2025/05/23/dod-palantir-maven-smart-system-contract-increase/)).
6. → the defence-native vendor ecosystem → **Anduril Lattice** and CBP towers
   ([FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/);
   [Defense Daily](https://www.defensedaily.com/cbp-awards-anduril-363-million-for-extended-range-surveillance-towers/homeland-security/)).
7. → Lattice's *radar-cues-camera* design = **VSAM layer 5 in 2025** (§4.2, §15.4),
   closing Chain E onto Chain A's seed → **L11 and P13**.

### Chain F — the failure lineage (7 hops)
1. **Seed:** "BRS Labs AISight" → [SEC LR-24013](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm).
2. → the complaint's specifics ([SEC complaint PDF](https://www.sec.gov/files/litigation/complaints/2017/comp24013.pdf)).
3. → the unfalsifiability of "abnormal" → i-LIDS as the instrument that would have
   caught it (Chain C, R03 §2.3).
4. → the same rhetoric in EU policy: **INDECT's "abnormal behaviour"**
   ([EDRi](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)).
5. → the political consequence: Parliamentary questions
   ([E-6084/2009](https://www.europarl.europa.eu/doceo/document/E-7-2009-6084_EN.html?redirect)).
6. → post-INDECT rebranding toward safety/efficiency framing (§6.3) → the modern
   vendor register (*"smart spaces, warehouse automation, SOP validation"*,
   [NVIDIA](https://developer.nvidia.com/blog/build-a-video-search-and-summarization-agent-with-nvidia-ai-blueprint/)).
7. → and to **P17**: the same preconditions still exist.

---

## 21. Sources

### Prehistory, CCTV and VMD
- [Lynztel, *The History of Video Surveillance: From Military CCTV to AI*](https://lynztel.com/en/blog/historia-de-los-sistemas-de-videovigilancia-del-cctv-militar-a-la-ia/)
- [Wikipedia, *Closed-circuit television*](https://en.wikipedia.org/wiki/Closed-circuit_television) (snippet only; egress blocked)
- [Wikipedia, *Walter Bruch*](https://en.wikipedia.org/wiki/Walter_Bruch) (snippet only)
- [DTiQ, *History of Security Cameras: How Did CCTV Evolve*](https://www.dtiq.com/blog/video-surveillance/history-of-security-cameras)
- [SMART Security Solutions / XtraVision, *Going through the motions: the history of video motion detection (VMD)*, CCTV Handbook 2007](http://www.securitysa.com/regular.aspx?pklregularid=2904)
- [Benchmark Magazine, *CCTV Test: External Video Motion Detection*](https://benchmarkmagazine.com/cctv-test-external-video-motion-detection/)
- [Ajax, *When did security cameras come out?*](https://ajax.systems/blog/when-did-security-cameras-come-out/)
- [Fastech, *A History of CCTV: From Military Origins to AI Surveillance*](https://fastechltd.co.uk/blogs/a-history-of-cctv-from-military-origins-to-ai-surveillance/)

### DARPA VSAM and the research founding
- [CMU Robotics Institute, *A System for Video Surveillance and Monitoring* (CMU VSAM Final Report)](https://www.ri.cmu.edu/publications/a-system-for-video-surveillance-and-monitoring/)
- [Semantic Scholar record, CMU VSAM Final Report (Kanade, Collins)](https://www.semanticscholar.org/paper/A-System-for-Video-Surveillance-and-Monitoring-CMU-Kanade-Collins/59f381a64bc500c5c040a17d6e46c021c2d59bce)
- [ResearchGate, *A System for Video Surveillance and Monitoring CMU VSAM Final Report*](https://www.researchgate.net/publication/235128212_A_System_for_Video_Surveillance_and_Monitoring_CMU_VSAM_Final_Report)

### IBM S3 / MILS
- [Springer, *IBM smart surveillance system (S3): event based video surveillance system with an open and extensible framework*, Machine Vision and Applications](https://link.springer.com/article/10.1007/s00138-008-0153-z)
- [ResearchGate, *S3-R1: The IBM smart surveillance system-release 1*](https://www.researchgate.net/publication/261847464_S3-R1_The_IBM_smart_surveillance_system-release_1)
- [Academia.edu, *S3: The IBM Smart Surveillance System: From Transactional Systems to Observational Systems*](https://www.academia.edu/5582040/S3_The_IBM_Smart_Surveillance_System_From_Transactional_Systems_to_Observational_Systems)
- [SDM Magazine, *IBM "Big Blue" Introduces Advanced Video Surveillance Product*](https://www.sdmmag.com/articles/84245-ibm-a-big-blueatm-introduces-advanced-video-surveillance-product)

### ObjectVideo and the patent war
- [SecurityInfoWatch, *ObjectVideo sues Bosch, Sony and Samsung*](https://www.securityinfowatch.com/video-surveillance/news/10485600/objectvideo-sues-bosch-sony-and-samsung-over-alleged-patent-infringement-in-the-area-of-video-content-analytics)
- [Bloomberg, *Sony, Samsung Techwin Targeted by ObjectVideo in ITC Patent Case*](https://www.bloomberg.com/news/articles/2011-06-30/sony-samsung-techwin-targeted-by-objectvideo-in-itc-patent-case)
- [Security Sales & Integration, *ObjectVideo, Sony Enter Into Patent License Agreement*](https://www.securitysales.com/news/objectvideo-sony-enter-into-patent-license-agreement/28451/)
- [Security Sales & Integration, *ObjectVideo Drops Patent Infringement Case Against Samsung*](https://www.securitysales.com/news/objectvideo-drops-patent-infringement-case-against-samsung/)
- [IPVM, *ObjectVideo Sues Bosch, Samsung and Sony*](https://ipvm.com/reports/objectvideo-lawsuit-bosch-samsung-and-sony)
- [SecurityWorldMarket, *The story behind why Object Video sued Bosch and Samsung*](https://www.securityworldmarket.com/me/Newsarchive/the-story-behind-why-object-video-sued-bosch-and-samsung)
- [ASIS Security Management, *ObjectVideo Files Suit With The ITC To Protect Patents*](https://www.asisonline.org/security-management-magazine/articles/2011/07/objectvideo-files-suit-with-the-itc-to-protect-patents/)
- [Government Security News, *ObjectVideo agrees to license its video analytic patents to American Dynamics*](https://www.gsnmagazine.com/article/25564/new_strategy_objectvideo_agrees_license_its_video_)

### The 2000s cohort and its fates
- [IPVM, *Vidient's Analytics Acquired by Agilence*](https://ipvm.com/reports/vidients-analytics-acquired-by-agilence)
- [Business Wire, *Agilence Purchases Assets of Video Analytics Company Vidient Systems*](https://www.businesswire.com/news/home/20110412005330/en/Agilence-Purchases-Assets-Video-Analytics-Company-Vidient)
- [asmag, *Agilence Acquires Video Analytics Provider Vidient Systems*](https://www.asmag.com/showpost/11553.aspx)
- [IPVM, *Cernium Shifts Strategy Again (CheckVideo)*](https://ipvm.com/reports/cernium-shifts-strategy-again-checkvideo)
- [IPVM, *3VR Firesale to Identiv*](https://ipvm.com/reports/3v-identiv)
- [Security Systems News, *Tyco acquires retail-focused analytics vendor IntelliVid*](https://www.securitysystemsnews.com/article/tyco-acquires-retail-focused-analytics-vendor-intellivid)
- [SecurityInfoWatch, *Intelligence and Convergence: Leading the way at ASIS*](https://www.securityinfowatch.com/video-surveillance/article/10592117/intelligence-and-convergence-leading-the-way-at-asis)
- [IPVM, *NICE Is Out Of the Video Surveillance Business / Now Qognify*](https://ipvm.com/reports/nice-is-out-of-the-video-surveillance-business)
- [IPVM, *Examining NICE's NiceVision VMS*](https://ipvm.com/reports/nice-nicevision-vms)
- [IFSEC Insider, *Qognify Launches Object Origin After Acquiring NICE Systems' Physical Security Business Unit*](https://www.ifsecglobal.com/video-surveillance/qognify-launches-object-origin-acquiring-nice-systems-physical-security-business-unit/)
- [Hexagon, *Hexagon strengthens its physical security and incident management capabilities with the acquisition of Qognify*](https://hexagon.com/company/newsroom/press-releases/2022/hexagon-strengthens-its-physical-security-and-incident-management-capabilities-with-the-acquisition-of-qognify)
- [Help Net Security, *Hexagon acquires Qognify*](https://www.helpnetsecurity.com/2022/12/20/hexagon-qognify/)
- [Security Systems News, *Qognify becomes part of Hexagon division*](https://www.securitysystemsnews.com/article/qognify-becomes-part-of-hexagon-division)
- [Verint CIS, *Situational Awareness Platform*](https://cis.verint.com/product/situational-intelligence/situational-awareness-platform/)
- [Verint, *Verint Adds New Intelligence Capabilities*](https://www.verint.com/press-room/2018-press-releases/verint-adds-new-intelligence-capabilities-to-help-organizations-anticipate-identify-and-mitigate-risk/)
- [Irisity, *About Us*](https://irisity.com/about-us/)
- [Security Systems News, *Agent Vi acquired by Swedish AI company, Irisity AB*](https://www.securitysystemsnews.com/article/agent-vi-acquired-by-swedish-ai-company-irisity)
- [SecurityInfoWatch, *Agent Vi acquired by Irisity*](https://www.securityinfowatch.com/video-surveillance/video-analytics/news/21236936/agent-vi-acquired-by-irisity)
- [Milestone Marketplace, Irisity listing](https://www.milestonesys.com/marketplace/irisity/)
- [Motorola Solutions, *Motorola Solutions to Acquire Avigilon*](https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-to-acquire-avigilon-leader-in-advanced-video-surveillanc.html)
- [Motorola Solutions, *Motorola Solutions Completes Acquisition of Avigilon*](https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-completes-acquisition-avigilon.html)
- [Motorola Solutions FY2018 Form 10-K (SEC)](https://www.sec.gov/Archives/edgar/data/68505/000006850519000006/msi201810-k.htm)

### BRS Labs / Giant Gray
- [SEC Litigation Release 24013](https://www.sec.gov/litigation/litreleases/2017/lr24013.htm)
- [SEC complaint (PDF)](https://www.sec.gov/files/litigation/complaints/2017/comp24013.pdf)
- [Kehoe Law Firm investor notice](https://kehoelawfirm.com/behavioral-recognition-systems-charged/)
- [Rex Securities Law, BRS/Giant Gray](https://rexsecuritieslaw.com/recover-loss-on-brs-giant-gray/)
- [Goodman & Nekvasil investor notice](https://rightsforinvestors.com/behavioral-recognition-systems-inc-brs-labs-giant-gray-ray-davis-bankruptcy-sec/)

### UK: i-LIDS, CAST, and UK vendors
- [IEEE, *Imagery Library for Intelligent Detection Systems (i-LIDS)*](https://ieeexplore.ieee.org/document/4123801)
- [i-LIDS: A Standard for Testing Video Based Detection Systems (ResearchGate)](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)
- [i-LIDS brochure (UK Government, PDF)](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf)
- [i-LIDS User Guide (PDF, via SIA)](https://www.securityindustry.org/wp-content/uploads/2017/08/iLids-User-Guide.pdf)
- [i-LIDS User Guide (UK Government copy, PDF)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/143875/ilids-user-guide.pdf)
- [Atos, *Atos reinforces its leading position in the Edge and Computer Vision market through the acquisition of Ipsotek*](https://atos.net/en/2021/press-release_2021_04_20/atos-reinforces-its-leading-position-in-the-edge-and-computer-vision-market-through-the-acquisition-of-ipsotek)
- [Consultancy.uk, *Atos acquires video analytics software provider Ipsotek*](https://www.consultancy.uk/news/27670/atos-acquires-video-analytics-software-provider-ipsotek)
- [International Security Journal, Ipsotek profile](https://internationalsecurityjournal.com/security-business-index/ipsotek/)
- [Mergr, Ipsotek ownership overview](https://mergr.com/company/ipsotek)
- [Digital Barriers, *What is SafeZone-edge?*](https://safezone-support.digitalbarriers.com/support/solutions/articles/4000019371-what-is-safezone-edge-)
- [Sharecast, *Digital Barriers offloads video unit, changes focus to Thruvision screening*](https://www.sharecast.com/news/aim-bulletin/digital-barriers-offloads-video-unit-changes-focus-to-thruvision-screening--2902970.html)
- [MoneyWeek, *Digital Barriers acquires ThruVision*](https://moneyweek.com/22646/digital-barriers-acquires-thruvision-120309-0827-82676)
- [SecurityInfoWatch, Digital Barriers SafeZone-edge product record](https://www.securityinfowatch.com/perimeter-security/physical-hardening/product/11363775/digital-barriers-digital-barrierss-safezone-edge)

### Inria / Keeneo lineage
- [Inria Pulsar 2010 activity report, *Software Engineering for Activity Recognition*](https://raweb.inria.fr/rapportsactivite/RA2010/pulsar/uid14.html)
- [Inria STARS 2012 full activity report](http://www-sop.inria.fr/stars/Documents/Activity%20Report/FullActivityReportStars2012.html)
- [Inria STARS 2013 activity report](http://www-sop.inria.fr/stars/Documents/Activity%20Report/FullActivityReportStars2013.html)
- [Inria STARS 2023 annual activity report](https://radar.inria.fr/report/2023/stars/index.html)
- [Inria STARS 2024 annual activity report](https://radar.inria.fr/report/2024/stars/index.html)
- [Monique Thonnat, Inria](http://www-sop.inria.fr/members/Monique.Thonnat/Monique.Thonnatfr.html)
- [Monique Thonnat, Orion-era page](http://www-sop.inria.fr/orion/personnel/Monique.Thonnat/oldMonique.Thonnat-eng.html)
- [François Brémond CV (PDF)](http://www-sop.inria.fr/members/Francois.Bremond/Postscript/cv-2018-en.pdf)
- [Inria HAL, *Video Understanding Framework For Automatic Behavior Recognition*](https://inria.hal.science/inria-00276938)

### EU projects
- [CORDIS, ADVISOR results in brief](https://cordis.europa.eu/article/id/81538-automated-visual-surveillance-systems)
- [TRIMIS, *Annotated digital video surveillance and optimised retrieval* (ADVISOR)](https://trimis.ec.europa.eu/project/annotated-digital-video-surveillance-and-optimised-retrieval)
- [PRISMATICA: A multi-sensor surveillance system for public transport networks](https://www.researchgate.net/publication/4095097_PRISMATICA_A_multi-sensor_surveillance_system_for_public_transport_networks)
- [CORDIS, SAMURAI project fact sheet (FP7 217899)](https://cordis.europa.eu/project/id/217899)
- [CORDIS, SAMURAI results in brief](https://cordis.europa.eu/article/id/85970-developing-intelligent-video-surveillance)
- [Singularity Hub, *SAMURAI Project – Smart CCTV Security*](https://singularityhub.com/2009/12/23/samurai-project-smart-cctv-security-video/)
- [*Understanding Transit Scenes: A Survey on Human Behavior-Recognition Algorithms* (PDF)](https://www.candamo.org/articles/understanding-transit-scenes-a-survey-on-human-behavior-recognition-algorithms.pdf)
- [*Evaluation of Smart Video for Transit Event Detection* (FDOT BD549-49, PDF)](https://www.candamo.org/articles/evaluation-of-smart-video-for-transit-event-detection.pdf)
- [EDRi, *INDECT - privacy ethics in a secret project*](https://edri.org/our-work/edrigramnumber8-17indect-secrecy-privacy-ethics/)
- [European Parliament, written question E-6084/2009 on INDECT](https://www.europarl.europa.eu/doceo/document/E-7-2009-6084_EN.html?redirect)
- [European Parliament, answer to written question E-8217/2010 on INDECT](https://www.europarl.europa.eu/sides/getAllAnswers.do?language=EN&reference=E-2010-8217)
- [Reuters via Investing.com, *Irked by U.S., but EU keeps own spy projects quiet*](https://www.investing.com/news/world-news/irked-by-u.s.,-but-eu-keeps-own-spy-projects-quiet-351693)
- [*European 'smart' surveillance: What's at stake for data protection* (PDF)](https://www.shrmonitor.org/assets/uploads/2023/02/European-%E2%80%98smart-surveillance.pdf)

### Evaluation programmes: PETS, TRECVID, VIRAT, Mind's Eye, DIVA/ActEV/MEVA
- [PETS@CVG, University of Reading](http://www.cvg.reading.ac.uk/slides/pets.html)
- [PETS'2001 dataset page](http://www.cvg.reading.ac.uk/PETS2001/pets2001-dataset.html)
- [PETS 2017: dataset and challenge (PDF, CentAUR)](https://centaur.reading.ac.uk/75249/1/PETS2017_Dataset_Description7.pdf)
- [PETS 2017: Dataset and Challenge (IEEE)](https://ieeexplore.ieee.org/document/8014998/)
- [PETS 2014: Dataset and challenge](https://www.academia.edu/55727626/PETS_2014_Dataset_and_challenge)
- [Tracking performance evaluation on PETS 2015 Challenge datasets (PDF)](https://centaur.reading.ac.uk/46541/1/2015_AVSS_PETS2015TrackingChallenge_Nawaz_Boyle_Li_Ferryman.pdf)
- [*Performance Evaluation of a People Tracking System on PETS2009 Database*](https://www.researchgate.net/publication/232644259_Performance_Evaluation_of_a_People_Tracking_System_on_PETS2009_Database)
- [NIST, *Activities in Extended Videos Evaluation* (ActEV)](https://www.nist.gov/programs-projects/activities-extended-videos-evaluation)
- [NIST NLPIR, ActEV at TRECVID 2024](https://www-nlpir.nist.gov/projects/tv2024/actev.html)
- [ActEV Self-Reported Leaderboard](https://actev.nist.gov/srl)
- [Draft ActEV SDL Evaluation Plan (PDF)](https://actev.nist.gov/pub/Draft_ActEV_SDL_EvaluationPlan_Test3.pdf)
- [MEVA data portal](https://mevadata.org/)
- [*MEVA: A Large-Scale Multiview, Multimodal Video Dataset for Activity Detection* (arXiv)](https://arxiv.org/pdf/2012.00914)
- [*TRECVID 2019* overview (arXiv)](https://arxiv.org/pdf/2009.09984)
- [*TRECVID 2020* overview (arXiv)](https://arxiv.org/pdf/2104.13473)
- [*TRECVID 2022* overview (arXiv)](https://arxiv.org/pdf/2306.13118)
- [UCF CRCV, VIRAT dataset](https://www.crcv.ucf.edu/research/data-sets/virat/)
- [UCF CRCV, VIRAT (legacy page)](https://www.crcv.ucf.edu/data/VIRAT.php)
- [*OD-VIRAT: A Large-Scale Benchmark for Object Detection in Realistic Surveillance Environments* (arXiv 2507.12396)](https://arxiv.org/pdf/2507.12396)
- [SPIE, *Automated recognition of human activities in video streams in real time* (Mind's Eye)](https://spie.org/news/5489-automated-recognition-of-human-activities-in-video-streams-in-real-time)
- [Airforce Technology, *Mind's Eye: Visual Intelligence Takes to the Battlefield*](https://www.airforce-technology.com/features/feature122432/)
- [US 10,997,421, *Neuromorphic system for real-time visual activity recognition*](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10997421)
- [US 9,554,081, *Video access system and method based on action type detection*](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9554081)

### Standards
- [ONVIF, *ONVIF Releases Profile M for Metadata and Events for Analytics Applications*](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/)
- [ONVIF blog, *ONVIF announces the release of Profile M*](https://www.onvif.org/blog/2021/06/30/onvif-announces-the-release-of-profile-m/)
- [ONVIF Profile M Specification v1.0 (PDF)](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf)
- [ONVIF Profile M page](https://www.onvif.org/profiles/profile-m/)
- [SDM Magazine, ONVIF Profile M release](https://www.sdmmag.com/articles/99629-onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications)
- [Security Today, ONVIF Profile M release](https://securitytoday.com/articles/2021/06/30/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications.aspx)
- [Forasoft, *ONVIF Profile M in 2026: The Metadata Standard That Ends Multi-Vendor Analytics Chaos*](https://www.forasoft.com/blog/article/onvif-profile-m)

### China
- [IPVM, *China Public Video Surveillance Guide: From Skynet to Sharp Eyes*](https://ipvm.com/reports/sharpeyes)
- [CSET Georgetown, *China's 'Sharp Eyes' Program Aims to Surveil 100% of Public Space*](https://cset.georgetown.edu/article/chinas-sharp-eyes-program-aims-to-surveil-100-of-public-space/)
- [Grey Dynamics, *The Xueliang Project: Expansion of China's State Surveillance Programme*](https://greydynamics.com/the-xeuliang-project-expansion-of-chinas-state-surveillance-programme/)
- [RFA, *China ramps up surveillance of residents through video cameras*](https://www.rfa.org/english/china/2025/03/10/china-chongqing-district-surveillance-cameras/)
- [US News/AP, *From Beaches to Ski Slopes, Photos Show How Cameras Keep Watch All Over China*](https://www.usnews.com/news/us/articles/2025-10-29/from-beaches-to-ski-slopes-photos-show-how-cameras-keep-watch-all-over-china)

### Bans and procurement
- [IPVM, *Where Dahua and Hikvision Are Banned*](https://ipvm.com/reports/hikua-bans)
- [US EAC, *What is Section 889 of the FY 2019 NDAA?*](https://www.eac.gov/what-section-889-fy-2019-ndaa)
- [NDAA 889 Compliance Requirement (US Embassy, PDF)](https://ae.usembassy.gov/wp-content/uploads/sites/18/2025/05/NDAA-889-Compliance-Requirement.pdf)
- [Clearway, *NDAA Compliant Security Cameras: A Guide for UK Organisations*](https://www.clearway.co.uk/news/ndaa-compliant-security-cameras-a-guide-for-uk-organisations/)
- [Rhombus, *NDAA Compliant Security Cameras*](https://www.rhombus.com/blog/ndaa-compliant-security-cameras/)
- [Tec-Tel, *NDAA Section 889 camera compliance checklist*](https://tec-tel.com/resources/ndaa-section-889-camera-compliance)
- [NDAAz.com, banned-entity list](https://ndaaz.com/banned-list/)

### Biometrics, ALPR, bodycams and law
- [*R (Bridges) v Chief Constable of South Wales Police* [2020] EWCA Civ 1058 (judgment PDF)](https://www.judiciary.uk/wp-content/uploads/2020/08/R-Bridges-v-CC-South-Wales-ors-Judgment.pdf)
- [Inforrm / Hugh Tomlinson QC, case note on Bridges](https://inforrm.org/2020/08/17/case-law-r-on-the-application-of-bridges-v-chief-constable-of-south-wales-police-use-of-automatic-facial-recognition-technology-unlawful-hugh-tomlinson-qc/)
- [Hunton, *UK Court of Appeal Finds Automated Facial Recognition Technology Unlawful*](https://www.hunton.com/privacy-and-information-security-law/uk-court-of-appeal-finds-automated-facial-recognition-technology-unlawful-in-bridges-v-south-wales-police)
- [Liberty, *Legal Challenge: Ed Bridges v South Wales Police*](https://www.libertyhumanrights.org.uk/issue/legal-challenge-ed-bridges-v-south-wales-police/)
- [Data Protection Report, key takeaways from Bridges](https://www.dataprotectionreport.com/2020/08/key-takeaways-for-the-private-sector-from-the-bridges-v-south-wales-police-facial-recognition-case/)
- [Osborne Clarke, *Appeals court hands down the UK's first judgment on automated facial recognition*](https://www.osborneclarke.com/insights/appeals-court-hands-uks-first-judgment-automated-facial-recognition)
- [Ada Lovelace Institute, *Facial recognition technology needs proper regulation*](https://www.adalovelaceinstitute.org/blog/facial-recognition-technology-needs-proper-regulation/)
- [UK Government video surveillance blog, *What next for automated facial recognition*](https://videosurveillance.blog.gov.uk/2020/08/11/what-next-for-automated-facial-recognition)
- [ICO newsroom, Clearview AI fine](https://ico-newsroom.prgloo.com/news/ico-fines-facial-recognition-database-company-clearview-ai-inc-more-than-gbp-7-5m-and-orders-uk-data-to-be-deleted)
- [DAC Beachcroft, *Clearview AI fined more than £7.5m by the ICO*](https://www.dacbeachcroft.com/en/gb/articles/2022/may/facial-recognition-clearview-ai-fined-more-than-75m-by-the-ico/)
- [RPC, ICO fines Clearview AI](https://www.rpclegal.com/snapshots/data-protection/summer-2022/ico-fines-clearview-ai-for-facial-recognition-database/)
- [EDPB, *Italian SA fines Clearview AI EUR 20 million*](https://www.edpb.europa.eu/news/national-news/2022/facial-recognition-italian-sa-fines-clearview-ai-eur-20-million_en)
- [Data Privacy Manager, *CNIL issues €20 million GDPR fine to Clearview AI*](https://dataprivacymanager.net/cnil-issues-e20-million-gdpr-fine-to-clearview-ai/)
- [Privacy International, challenge against Clearview AI in Europe](https://privacyinternational.org/legal-action/challenge-against-clearview-ai-europe)
- [DLA Piper, *Clearview AI -v- Information Commissioner*](https://privacymatters.dlapiper.com/2023/10/clearview-ai-v-information-commissioner/)
- [Digital Watch Observatory, *Clearview AI wins appeals GDPR case against UK's ICO*](https://dig.watch/updates/clearview-ai-wins-appeals-gdpr-case-against-uks-ico)
- [ACM ICEGOV 2024, *Privacy and data protection regulations for AI using publicly available data: Clearview AI case*](https://dl.acm.org/doi/10.1145/3680127.3680200)
- [Traffic Technology Today, *Who invented ANPR? The untold British story*](https://www.traffictechnologytoday.com/features/feature-who-invented-anpr-the-untold-british-story-behind-a-global-traffic-technology-revolution.html)
- [NGSC, *The History of License Plate Recognition Technology*](https://ngscinc.com/history-license-plate-recognition)
- [Nortech, *What Is ANPR? How Automatic Number Plate Recognition Works*](https://blog.nortechcontrol.com/what-is-anpr/)
- [Axon investor relations, *Axon reimagines report writing with Draft One*](https://investor.axon.com/2024-04-23-Axon-reimagines-report-writing-with-Draft-One,-a-first-of-its-kind-AI-powered-force-multiplier-for-public-safety)
- [Axon, *Beyond Battery Life: Axon Body 4*](https://www.axon.com/resources/beyond-battery-life-how-the-ecosystem-brings-out-the-best-in-the-axon-body-4)
- [Axon, *New fixed ALPR camera solutions and next-gen AI advancements*](https://www.axon.com/newsroom/press-releases/axon-announces-new-fixed-ALPR-camera-solutions-and-next-gen-AI-advancements-to-expand-real-time-public-safety-ecosystem)
- [CUNY Journalism, *Axon trades Tasers for tech in software and AI push*](https://coveringcompanies.journalism.cuny.edu/2025/11/05/axon-trades-tasers-for-tech-in-software-and-ai-push/)
- [Vice, *Bodycam Maker Axon Is on a Mission to Surveil America with AI*](https://www.vice.com/en/article/axon-acquires-fusus-ai-surveillance-retail-healthcare/)

### Cloud and the startup wave
- [CNBC, *Security startup Verkada hits $5.8 billion valuation*](https://www.cnbc.com/2025/12/03/verkada-capitalg-valuation-security.html)
- [Verkada, *Announcing our $5.8B Valuation*](https://www.verkada.com/blog/our-new-valuation-dec-2025/)
- [PR Newswire, *Verkada Reaches $5.8B Valuation with Investment from CapitalG*](https://www.prnewswire.com/news-releases/verkada-reaches-5-8b-valuation-with-investment-from-capitalg-302631378.html)
- [SiliconANGLE, Verkada at $5.8B](https://siliconangle.com/2025/12/03/security-device-startup-verkada-raises-funding-5-8b-valuation/)
- [Security Sales & Integration, *Verkada Raises $205M, Now Valued at $3.2B*](https://www.securitysales.com/news/verkada-raises-205m-valued-3-2b/146112/)
- [PR Newswire, *Verkada raises $200M*](https://www.prnewswire.com/news-releases/verkada-raises-200m-in-funding-to-continue-delivering-category-defining-security-solutions-302379927.html)
- [Tracxn, Ambient AI funding and investors](https://tracxn.com/d/companies/ambient-ai/__o3P0l5V7BKOZZr3yfissd1iMGgTNb4kFRNlvBdq9MNg/funding-and-investors)
- [Crunchbase, Ambient.ai](https://www.crunchbase.com/organization/ambient-ai)
- [PitchBook, Lumana profile](https://pitchbook.com/profiles/company/510191-56)
- [Coram, *9 Best Ambient.ai Competitors & Alternatives in 2026*](https://www.coram.ai/post/ambient-ai-competitors) **[competitor marketing — weak source]**

### Defence / ISR
- [Sierra Nevada Corporation, *Gorgon Stare Increment 2* milestone](https://www.sncorp.com/news-archive/sierra-nevada-corporation-achieves-milestone-for-usaf-s-advanced-wide-area-airborne-persistent-surveillance-system-gorgon-stare-increment-2/)
- [Lexington Institute, *Wide Area Persistent Surveillance Revolutionizes Tactical ISR*](https://lexingtoninstitute.org/wide-area-persistent-surveillance-revolutionizes-tactical-isr/)
- [Wikipedia, *Gorgon Stare*](https://en.wikipedia.org/wiki/Gorgon_Stare) (snippet only)
- [Wikipedia, *ARGUS-IS*](https://en.wikipedia.org/wiki/ARGUS-IS) (snippet only)
- [Wikipedia, *Constant Hawk*](https://en.wikipedia.org/wiki/Constant_Hawk) (snippet only)
- [Wikipedia, *Wide-area motion imagery*](https://en.wikipedia.org/wiki/Wide-area_motion_imagery) (snippet only)
- [Longreads, *'Nothing Kept Me Up At Night the Way the Gorgon Stare Did.'*](https://longreads.com/2019/06/21/nothing-kept-me-up-at-night-the-way-the-gorgon-stare-did/)
- [Big Think, *The surveillance technology that will watch us all, all the time*](https://bigthink.com/the-present/gorgon-stare-surveillance/)
- [ResearchGate, VMTI detection examples on the VIRAT aerial dataset (© DARPA)](https://www.researchgate.net/figure/MTI-Detection-Examples-on-VIRAT-Aerial-Dataset-C-DARPA_fig3_280560670)
- [GlobalSecurity.org, *Algorithmic Warfare Cross-Functional Team (AWCFT) / Project Maven*](https://www.globalsecurity.org/intell/systems/maven.htm)
- [Wikipedia, *Project Maven*](https://en.wikipedia.org/wiki/Project_Maven) (snippet only)
- [C4ISRNET, *Palantir wins contract to expand access to Project Maven AI tools*](https://www.c4isrnet.com/artificial-intelligence/2024/05/30/palantir-wins-contract-to-expand-access-to-project-maven-ai-tools/)
- [The Defense Post, *Palantir Awarded $480M to Prototype US Army's 'Maven'*](https://thedefensepost.com/2024/05/30/palantir-maven-battlefield-analyzer/)
- [The Register, *Palantir / US Army Maven contract*](https://www.theregister.com/2024/05/30/palantir_us_army/)
- [DefenseScoop, *'Growing demand' sparks DOD to raise Palantir's Maven contract to more than $1B*](https://defensescoop.com/2025/05/23/dod-palantir-maven-smart-system-contract-increase/)
- [Military.com, *Pentagon Expands Use of Palantir AI in New Defense Contract*](https://www.military.com/feature/2026/03/22/pentagon-expands-palantirs-role-ai-contract.html)
- [Medium, *Project Maven: The Architecture of Algorithmic Warfare*](https://medium.com/@m.salah2405/project-maven-the-architecture-of-algorithmic-warfare-3ff147e7b520) **[weak source]**
- [FedScoop, *CBP more than doubling autonomous sentry towers along Southwest border*](https://fedscoop.com/anduril-sentry-towers-cbp/)
- [Defense Daily, *CBP Awards Anduril $363 Million For Extended Range Surveillance Towers*](https://www.defensedaily.com/cbp-awards-anduril-363-million-for-extended-range-surveillance-towers/homeland-security/)
- [Privacy International, *Dual-use tech: the Anduril example*](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example)
- [GovConWire, *How Anduril Is Driving National Security Innovation*](https://www.govconwire.com/articles/anduril-uav-uuv-lattice-homeland-security)
- [ExecutiveBiz, *Anduril Surveillance Towers Boost Southern US Border Security*](https://www.executivebiz.com/articles/andurils-autonomous-surveillance-towers-boost-southern-us-border-protection)
- [The Intercept, *Trump's Big Beautiful Gift to Anduril*](https://theintercept.com/2025/07/09/trump-big-beautiful-bill-anduril/)
- [State of Surveillance, *Anduril Built a Border Surveillance Empire*](https://stateofsurveillance.org/news/anduril-border-surveillance-monopoly-big-beautiful-bill-2026/)
- [EFF, *California Coastal Community Must Reject CBP's AI-Powered Surveillance Tower*](https://www.eff.org/deeplinks/2026/04/california-coastal-community-must-reject-cbps-ai-powered-surveillance-tower)

### VLMs, video agents, world models
- [NVIDIA-AI-Blueprints/video-search-and-summarization (GitHub — read directly)](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)
- [NVIDIA blog, *AI Blueprint for Video Search and Summarization Now Available*](https://blogs.nvidia.com/blog/ai-blueprint-video-search-and-summarization/)
- [NVIDIA developer blog, *Build a Video Search and Summarization Agent with NVIDIA AI Blueprint*](https://developer.nvidia.com/blog/build-a-video-search-and-summarization-agent-with-nvidia-ai-blueprint/)
- [NVIDIA developer blog, *Advance Video Analytics AI Agents Using the NVIDIA AI Blueprint for VSS*](https://developer.nvidia.com/blog/advance-video-analytics-ai-agents-using-the-nvidia-ai-blueprint-for-video-search-and-summarization/)
- [Edge AI and Vision Alliance, coverage of the VSS blueprint GA](https://www.edge-ai-vision.com/2025/05/ai-blueprint-for-video-search-and-summarization-now-available-to-deploy-video-analytics-ai-agents-across-industries/)
- [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/)
- [NVIDIA newsroom, *NVIDIA Launches Cosmos World Foundation Model Platform*](https://nvidianews.nvidia.com/news/nvidia-launches-cosmos-world-foundation-model-platform-to-accelerate-physical-ai-development)
- [NVIDIA newsroom, *Major Release of Cosmos World Foundation Models and Physical AI Data Tools*](https://nvidianews.nvidia.com/news/nvidia-announces-major-release-of-cosmos-world-foundation-models-and-physical-ai-data-tools)
- [*World Simulation with Video Foundation Models for Physical AI* (arXiv:2511.00062)](https://arxiv.org/abs/2511.00062)
- [NVIDIA Research, *World Simulation with Video Foundation Models for Physical AI*](https://research.nvidia.com/publication/2025-09_world-simulation-video-foundation-models-physical-ai)
- [NVIDIA Cosmos Lab](https://research.nvidia.com/labs/cosmos-lab)
- [*Rethinking Video Generation Model for the Embodied World* (arXiv:2601.15282)](https://arxiv.org/pdf/2601.15282)
- [AWS HPC blog, *Running NVIDIA Cosmos world foundation models on AWS*](https://aws.amazon.com/blogs/hpc/running-nvidia-cosmos-world-foundation-models-on-aws/)

### Internal cross-references (this repository)
- `docs/research/R01_detection_and_single_camera_tracking.md` — detectors, trackers, metrics, sim2real for MOT.
- `docs/research/R02_multicamera_tracking_and_reid.md` — cross-camera identity.
- `docs/research/R03_behaviour_intent_anomaly_detection.md` — i-LIDS scoring mechanics, ActEV metrics, anomaly benchmarks, intent, human factors, legal constraints.
- `docs/research/R04_degraded_imaging_and_sim2real.md` — imaging degradation, synthetic-data evidence.
- `docs/research/R05_multisensor_fusion_and_nl_retrieval.md` — sensor fusion, NL retrieval.
- `removed-vendor-doc.md` — current company/people map.

---

## 22. Verification backlog (do these before any external use)

1. 1960s municipal CCTV dates: Trafalgar Square 1960, Olean NY 1968, Times Square 1973.
2. Walter Bruch's PAL attribution from a primary source.
3. Sarnoff → SRI International acquisition date; Acadia processor lineage.
4. ObjectVideo's final corporate disposition (Alarm.com / ObjectVideo Labs split).
5. ioimage → DVTel → FLIR → (Teledyne / Motorola) chain, with dates.
6. Verint's physical-security video separation; Cognyte spin-off scope.
7. Siemens Siveillance, Honeywell and Pelco analytics product names and dates; Pelco → Transom → Motorola chain.
8. Ipsotek's academic provenance (the Kingston University claim) — retrieved sources say founded 2001 and are silent on Kingston.
9. BAE Systems Detica's actual video-analytics role, if any.
10. P-REACT and SURVEIRON CORDIS records.
11. IEC 62676 part-by-part publication dates and the EN 50132 relationship.
12. NPSA CAPSS current name, scope, and whether analytics is in scope.
13. BS 7958 / Surveillance Camera Code current status.
14. ONVIF founding members; per-profile release years for S/C/G/Q/A/T/D.
15. IEEE AVSS founding year and continuity.
16. TRECVID SED's years of operation and the i-LIDS airport subset licensing.
17. Genetec and Milestone founding dates; Canon's Milestone (2014) and Axis (2015) acquisitions.
18. Brivo/Eagle Eye Networks merger (currently sourced only to a competitor's blog).
19. Vintra and viisights current corporate status.
20. Clearview AI's post-2023 UK appellate history.
21. EU AI Act article-level provisions on remote biometric identification (prefer R03 §9's citations).
22. The 2018 Google/Maven employee revolt specifics, from a primary source.
23. NGA and Dstl video-analytics programme specifics.
24. Whether Section 889's UK analogue extends beyond "sensitive sites" to all public-sector procurement (sources conflict).

*End of D01.*
