# D04 · The Real-World System Architecture of a Deployed Multi-Camera Surveillance-Analytics Product

*Deep-research dossier. Research depth: seven-to-eight hops (standards → reference
architectures → vendor docs → deployment case studies → failure post-mortems →
security guidance → acceptance regimes → simulator hooks). Companion to
`docs/02_ARCHITECTURE.md` (which describes **SurvSim**, the simulator) and to
`R01 §5` / `R05 §4` (edge/integration realities and fusion/PSIM).*

> **Research-budget note.** This session's WebSearch quota (200 calls, shared
> across sibling research agents) was exhausted partway through. The searches
> that did land are cited inline; where a claim could not be verified in this
> session it is marked **[VERIFY]**. In addition, the egress proxy blocked
> direct WebFetch of `onvif.org`, `docs.nvidia.com`, `ncsc.gov.uk`,
> `milestonesys.com` and most vendor domains — only `github.com` fetched
> cleanly. Consequently several vendor-doc quotes come via the search-result
> summaries rather than first-hand page reads; those are marked
> **[secondary]**. Nothing in §12 (target architectures) or the numeric BoM
> tables should be treated as a quote; those are engineering estimates built on
> the cited primitives and are labelled **[estimate]**.

---

## 0. Executive summary — the thirteen things that actually matter

1. **The product is not a model. It is a pipeline with twelve failure domains.**
   Camera → power → network → decode → inference → tracking → cross-camera
   fusion → rules → alarm queue → operator → audit → retention. A model that is
   5 points better on HOTA and 200 ms later through the alarm queue is a worse
   product.
2. **The VMS owns the customer.** Milestone XProtect, Genetec Security Center,
   Avigilon, Network Optix and Exacq are where the operator lives all day.
   Analytics reaches the operator as a *plugin*, a *metadata channel*, or an
   *alarm/bookmark source* — or it does not reach them at all. (`R05 §4.7`
   states this; this document works out the mechanics.)
3. **Decode, not inference, is the first wall.** NVDEC/VPU stream limits are
   fixed-function and independent of your model; the AGX Orin datasheet figure
   of 18–20× 1080p is routinely met by a practical ceiling of ~8 concurrent
   decoder sessions in some JetPack configurations
   ([NVIDIA forum: "Orin AGX Jetpack 6 NVDEC limitation of <= 8 streams"](https://forums.developer.nvidia.com/t/orin-agx-jetpack-6-nvdec-limitation-of-8-streams/320865)).
4. **Metadata is the interoperability battlefield, and ONVIF Profile M is the
   only standard answer.** Streams are trivial; schemas are not.
5. **Time is the silent killer.** NTP gives milliseconds, PTP gives
   microseconds ("*IEEE-1588 PTP allows synchronization of PTP-enabled devices
   within a few microseconds, compared to the Network Time Protocol (NTP) which
   operates on the millisecond scale*",
   [Emergent Vision Technologies](https://emergentvisiontec.com/video-accurate-multi-camera-synchronization-through-ieee-1588-ptp/)).
   Cross-camera association and evidential integrity both die on clock skew.
6. **Cyber posture is a procurement gate, not a feature.** NDAA §889 and the
   FCC Covered List remove entire vendors from the BoM
   ([IPVM, "Where Dahua and Hikvision Are Banned"](https://ipvm.com/reports/hikua-bans));
   CVE-2021-36260 plus Moobot is the canonical story of why
   ([FortiGuard Labs](https://www.fortinet.com/blog/threat-research/mirai-based-botnet-moobot-targets-hikvision-vulnerability)).
7. **Fusion is sold at L1 and judged at L5.** (See `R05 §4.1`.) The PSIM/C2
   layer — Genetec Mission Control, Anduril Lattice — is where value is
   recognised or the programme dies.
8. **Acceptance is an adversarial test, not a demo.** i-LIDS-style regimes with
   *primary* vs *secondary* approval levels
   ([IFSEC](https://www.ifsecglobal.com/uncategorized/vcasys-passes-i-lids-analytics-test/),
   [i-LIDS brochure](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf))
   and DORI/IEC 62676-4 pixel-density gates
   ([Axis pixel-density white paper](https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014))
   decide whether the system is allowed to be the alarm source.
9. **Border-scale programmes fail politically before they fail technically.**
   The DHS Integrated Surveillance Towers history is the reference cautionary
   tale ("*a pattern has emerged where CBP will roll out a new program with a
   'cool sounding' name, and then, three to five years later … find that it's
   wasteful, it's ineffective*",
   [Reason on the GAO assessment](https://reason.com/2026/07/30/homeland-security-is-spending-1-billion-on-autonomous-border-surveillance-towers/)).
10. **The unit of deployment is a container graph, not a binary.** Kafka-brokered
    microservices (Milestone AI Bridge, NVIDIA Metropolis/VSS) with k3s or
    docker-compose at the edge.
11. **Search is becoming a first-class product surface.** VSS-style blueprints
    push embeddings into vector DBs and expose natural-language retrieval —
    "*Video retrieval, VLM-based Q&A, and report generation on short video
    clips*" ([NVIDIA VSS blueprint](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)).
12. **The simulator's commercial value is as a CI fixture for this whole
    pipeline**, not as a dataset generator. SurvSim + `mediamtx` + an ONVIF
    emulator = a synthetic site that a real VMS and a real analytics stack
    cannot distinguish from a small deployment.
13. **Everything reduces to two numbers the customer cares about:** detections
    missed per shift (Pd/NAR) and nuisance alarms per camera per day. Design
    backwards from those.

---

## 1. Camera side — the edge of the edge

### 1.1 ONVIF: the interoperability floor

ONVIF profiles are the contract between device and VMS. The ones that matter:

| Profile | Scope | Why the architecture cares |
|---|---|---|
| **S** | Basic video streaming. "*A Profile S device (e.g., an IP network camera or video encoder) is one that can send video data over an IP network to a Profile S client*" ([ONVIF Profile S](https://www.onvif.org/profiles/profile-s/)) **[secondary]** | The absolute floor. Discovery (WS-Discovery), media profiles, RTSP URI retrieval, basic PTZ, relay outputs, multicast config. |
| **T** | Advanced streaming: "*supports video streaming features such as the use of H.264 and H.265 encoding formats, imaging settings, and alarm events such as motion and tampering detection*" ([ONVIF Profile T](https://www.onvif.org/profiles/profile-t/), quoted in `R01 §5.2`) | H.265 negotiation, imaging control (exposure, WDR, IR cut), **motion and tamper events** — the cheapest tamper detector you will ever ship. |
| **G** | Recording and edge storage: a Profile G device "*can record video data over an IP network or on the device itself*"; a Profile G client "*can configure, request, and control recording of video data over an IP network*" ([ONVIF Profile G spec v1.0](https://www.onvif.org/wp-content/uploads/2017/01/ONVIF_Profile_G_Specification_v1-0.pdf), [Profile G page](https://www.onvif.org/profiles/profile-g/)) **[secondary]** | Edge recording = gap-filling after a network outage, and the retrieval/replay interface for evidence. Profile G "*specifies how video footage should be indexed, searched, and retrieved*" ([Video Experts Group glossary](https://www.videoexpertsgroup.com/glossary/onvif-profile-g)). |
| **M** | Analytics metadata & events. "*Supports analytics configuration and information query for metadata, as well as filtering and streaming of metadata*", with "*interfaces for generic object classification, and specified metadata for geolocation, vehicle, license plate, human face and human body*" ([ONVIF Profile M](https://www.onvif.org/profiles/profile-m/)); and "*events using JSON and the MQTT protocol for IoT applications*" ([ONVIF Profile M release](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/)) — both quoted at length in `R05 §4.6`. | **This is the schema our product should emit.** Profile M is the difference between "drops into any conformant VMS" and "bespoke integration per customer". |
| **C / A / D** | Access control (C: door control; A: configuration; D: peripheral devices) | Only relevant because fusion with access control is the single highest-value corroboration source (`R05 §4.5`). |

The ONVIF GitHub organisation is explicit that the repo is forward-looking only:
"*This repository is dedicated to future extensions of the ONVIF Network
Interface Specifications which include Network Interface Specification Documents
[and] Schemas and wsdl files*", noting "*officially released specifications are
available at onvif.org*" ([onvif/specs](https://github.com/onvif/specs)). In
practice you implement against the released WSDLs (`device`, `media2`, `ptz`,
`imaging`, `events`, `analytics`, `recording`, `replay`, `security`) and you
treat the *Conformant Products* list as a vendor claim to be re-tested.
**[VERIFY — per-service WSDL enumeration not read first-hand this session.]**

**The integrator's brutal truth**, already recorded in `R01 §5.2`: "*Streams are
easy — RTSP, H.264, H.265, done. Metadata is where multi-vendor deployments fall
apart, and where ONVIF Profile M is supposed to help*"
([Fora Soft](https://www.forasoft.com/blog/article/onvif-profile-m)).

### 1.2 Transport: RTSP/RTP, and the RTSPS/SRTP question

```
   ┌────────────────────────────── camera ──────────────────────────────┐
   │ sensor → ISP → encoder(H.264/H.265/AV1) → RTP packetiser           │
   │           │                                  │                     │
   │           └→ on-camera analytics (SoC NPU) ───┴→ metadata RTP track │
   └────────┬──────────────────────────────────────────────────────────┘
            │ RTSP DESCRIBE/SETUP/PLAY  (TCP 554 / TLS 322)
            │ RTP video  (UDP, or interleaved over the RTSP TCP channel)
            │ RTCP RR/SR  (loss, jitter, sender NTP↔RTP mapping)
            ▼
       VMS Recording Server / analytics ingest
```

RTSP is the control plane: "*Media control is accomplished over RTSP as defined
in RFC 2326*", with "*RTP, RTCP and RTSP profiling*"
([ONVIF Streaming Specification](https://www.onvif.org/specs/stream/ONVIF-Streaming-Spec.pdf),
as quoted in `R01 §5.2`). The practical failure modes are unchanged from `R01`
and worth restating because every one of them is a simulator feature:

* **TCP-interleaved vs UDP.** UDP gives lower latency and multicast; TCP
  traverses firewalls and survives NAT. Most enterprise deployments end up
  TCP-interleaved because the security team will not open UDP ranges.
* **GOP length.** Keyframe intervals of 2–4 s mean a reconnect costs seconds of
  blindness, and a *seek* in recorded video quantises to the GOP boundary.
* **SPS/PPS not resent** on reconnect → decoder cannot start → "black camera"
  that pings fine.
* **Silent fps collapse** under the camera's own IR/WDR load.
* **Timestamp discontinuities** on encoder restart, which corrupt any
  track-to-track association that trusts RTP timestamps.

**Encryption.** RTSP-over-TLS (RTSPS) plus SRTP is the standards-clean answer,
and off-the-shelf servers support it: `mediamtx` advertises publishing and
reading with "*Media-over-QUIC, SRT, WebRTC, RTSP, RTMP, HLS, MPEG-TS, RTP*" and
"*Authenticate users with internal, HTTP or JWT authentication*"
([bluenviron/mediamtx](https://github.com/bluenviron/mediamtx)); Happytime's
simulator similarly covers "*RTP over TCP, RTP over UDP, RTP multicast … RTSP
over HTTP, RTSP over WebSocket, RTSP over SSL/TLS (RTSPS)*"
([Happytime ONVIF RTSP Server](https://www.happytimesoft.com/products/onvif-rtsp-server/index.html)).
In the field, camera-to-VMS encryption is still patchy and is usually replaced
by *network* controls (a dedicated camera VLAN, §2) rather than *media*
controls. That is an accepted-risk decision that a Secure-by-Design assessment
(§7) will make you write down.

### 1.3 Codecs: H.264, H.265, AV1 — and what changes for analytics

| Codec | Bitrate for 1080p25 CCTV (typical, smart-coded) | Notes for analytics |
|---|---|---|
| MJPEG | 8–20 Mbit/s | Every frame independent → trivially seekable, immune to GOP artefacts. Used for forensic-grade lanes and for ANPR. |
| H.264 High | 2–4 Mbit/s | Universal. Hardware decode everywhere. |
| H.265/HEVC | 1–2 Mbit/s | Halves storage; costs decoder sessions and licence complexity. Profile T is the ONVIF hook. |
| AV1 | ~0.7–1.5 Mbit/s **[estimate]** | Now appearing on camera SoCs: on Axis, "*you can now stream in RGB on ARTPEC-9 and CV25-based devices and in AV1 on ARTPEC-9*" ([Axis ACAP release notes 12.2](https://developer.axis.com/acap/release-notes/12.2/)) **[secondary]**. Decoder support in VMSes and in NVDEC is the constraint, not the camera. |

**The analytics-specific trap:** vendor "smart codecs" (zipstream / dynamic GOP
/ dynamic ROI) achieve their savings by *destroying exactly the information
analytics needs* — background regions are coarsened, static-but-important pixels
are frozen, and the P-frame residual that a motion-based detector keys on is
suppressed. Any model trained on clean video and deployed onto aggressively
smart-coded streams loses recall in a way that never shows up in the lab. This
is the strongest single justification for SurvSim's codec stage
(`02_ARCHITECTURE.md §5`: "*codec(ffmpeg h264 crf/bitrate/gop, packet loss,
frame drop, duplicate frames)*") and the stage should grow a *smart-codec*
emulation (per-region quantiser boost driven by the motion mask). **[lore]**

### 1.4 Multi-stream: main/sub, and the architecture decision hidden inside it

Essentially every professional camera emits ≥2 (often 4) concurrent encoded
streams from one sensor. The canonical allocation:

```
stream1  "main"   2688×1520 @ 25 fps  H.265  4 Mbit/s  → VMS recording (evidence)
stream2  "sub"     704×576  @ 12 fps  H.264  0.4 Mbit/s → analytics + live wall
stream3  "meta"    (no pixels)                          → ONVIF Profile M metadata
stream4  "mjpeg"   snapshot on demand                   → thumbnails, reports
```

Design consequences, each of which is a real argument in real projects:

* **Analytics on the substream is 10× cheaper and measurably worse.** A person
  at 40 m who is 80 px tall on the main stream is 21 px on a D1 substream —
  below almost every detector's useful floor and far below DORI *detection*
  (§9.1). The correct pattern is **resolution-tiered analytics**: substream for
  wide-area presence/motion gating, main stream (or a cropped ROI of it) for
  classification and ReID, triggered by the gate.
* **Requesting a third stream can destroy the camera.** Encoder budgets on
  mid-range SoCs are shared; asking for main+sub+extra at full rate silently
  drops the main stream's fps. Always measure delivered fps, never trust the
  configured value. **[lore]**
* **Evidence must come from the main stream.** If the analytics saw it on the
  substream, the clip you export for court must still be the main-stream
  recording covering the same interval (§3.4).

### 1.5 On-camera analytics platforms

The "edge" in surveillance often means *inside the camera*, on a vendor SoC with
an NPU. The four platforms to be able to discuss:

* **Axis ACAP.** "*An open development framework that enables developers to
  build custom applications that run directly on Axis network devices, such as
  cameras, intercoms, speakers, and radios*", with "*a Docker-powered
  toolchain*" ([Axis ACAP](https://www.axis.com/for-developers/acap),
  [developer.axis.com/acap](https://developer.axis.com/acap/)) **[secondary]**.
  The Native SDK examples map almost one-to-one onto what an analytics product
  needs on-camera: a VDO stream example that shows how to "*continuously capture
  frames from the vdo service, access the received buffer contents as well as
  the frame metadata*"; `larod` for hardware-accelerated inference across
  ARTPEC-7/8 and CV25; object detection with "*drawing bounding boxes around
  detected objects on the video stream*"; `axevent` to "*subscribe to and send
  events*"; a message-broker example; overlay APIs; and a "*WebSocket-based API
  for camera pan-tilt-zoom operations*"
  ([AxisCommunications/acap-native-sdk-examples](https://github.com/AxisCommunications/acap-native-sdk-examples)).
  There is also a gRPC-service runtime: ACAP Runtime is "*a gRPC service
  providing APIs for extended ACAP development*"
  ([AxisCommunications/acap-runtime](https://github.com/AxisCommunications/acap-runtime)).
  ARTPEC-9 "*improves video analytics and allows applications to detect objects
  earlier and identify smaller details than before*" **[secondary]**.
* **Bosch IVA / IVA Pro.** Edge analytics bundled with the camera rather than an
  open app store; "*Bosch IVA Pro is among the best options for edge-based video
  analytics*" **[secondary, vendor-adjacent blog — treat as marketing]**. The
  architecturally relevant part is that Bosch ships analytics *metadata* over
  the stream and into the VMS, which is where our product competes or
  cooperates.
* **Hanwha Wisenet Open Platform.** "*Wisenet Open Platform applications add
  additional functionality to your Wisenet camera devices*"
  ([Hanwha Vision](https://hanwhavisionamerica.com/software/wisenet-open-platform-applications/)).
  Notably, the *consumption* side is documented by third-party VMSes — Network
  Optix publishes a "Hanwha in-camera analytics integration" page
  ([Network Optix](https://support.networkoptix.com/hc/en-us/articles/17311859862167-Hanwha-in-camera-analytics-integration)).
* **Hikvision HEOP 2.0.** "*HEOP enables technology partners to develop and run
  their own applications on Hikvision's hardware*"; HEOP 2.0 "*facilitates
  partners to deploy proprietary deep-learning algorithms on Hikvision's edge
  devices*" ([Hikvision HEOP 2.0](https://www.hikvision.com/us-en/Partner/technology-partners/hikvision-embedded-open-platform-2-0/)).
  **For a UK/US defence-adjacent product this platform is off the table** — see
  §1.9.

**Strategic read.** On-camera deployment is how you win the small-site market
(no server, no licence, no rack) and how you lose the hard problems
(cross-camera ReID needs a shared embedding space and a fusion node; a camera
cannot see another camera's people). The shipping architecture is therefore
**hybrid**: cheap on-camera gating + metadata emission, with heavy
cross-camera work on a server (§4).

### 1.6 Power and physical plant

* **PoE budgets.** 802.3af (15.4 W at PSE), 802.3at/PoE+ (30 W), 802.3bt
  Type 3/4 (60/90 W). A fixed bullet with IR draws 8–13 W; a PTZ with heater
  and blower wants PoE+ or High-PoE; a multi-sensor 4×4K panoramic can exceed
  30 W. **[estimate — verify per model against the datasheet, always at the
  PD, and always with the cable-loss derating over a 90 m run.]**
* **Switch budget arithmetic** is the most common commissioning failure: 24
  cameras × 13 W = 312 W at the PD, ~370 W at the PSE with losses, against a
  switch whose "PoE budget" is 370 W total — so the 24th camera boots, the
  heaters kick in at 2 °C, and the switch starts shedding ports by priority at
  03:00 in January. Specify 1.5× headroom and per-port priority. **[lore]**
* **UPS and graceful degradation.** Cameras on PoE inherit the switch's power
  domain; the switch must be on UPS or the whole VLAN dies together, which
  looks exactly like a targeted attack on the monitoring picture.
* **Fibre/media converters** beyond 100 m; **surge protection** on any
  external run; **grounding** on towers (§12.3).

### 1.7 PTZ control

Two worlds coexist:

* **ONVIF PTZ service** (modern): absolute/relative/continuous move,
  presets, home position, `GetStatus`, PTZ configuration with pan/tilt/zoom
  spaces and speed limits. Axis exposes PTZ to on-camera apps via a
  "*WebSocket-based API*" ([ACAP examples](https://github.com/AxisCommunications/acap-native-sdk-examples)).
* **Pelco-D / Pelco-P over RS-485** (legacy): 7-byte messages, address + command
  + data + checksum, no feedback, no absolute positioning. Still present on
  every brownfield site via encoders/serial-over-IP gateways.
  **[VERIFY — frame layout not re-read this session; do not quote byte offsets
  without checking.]**

The architecture question is not the protocol but **who owns the PTZ**. A
slew-to-cue analytic, a guard's joystick, a patrol schedule and a fusion engine
all want the same actuator. Real systems need an explicit **PTZ arbitration
policy** with priorities, pre-emption and a timeout back to patrol/home — and an
audit record of who moved the camera when, because "the PTZ was pointed away
during the incident" is a formal inquiry question. SurvSim already models "*PTZ
schedules, tamper events, sync jitter*" via `CameraDirector`
(`02_ARCHITECTURE.md`); it should also model *contention* (two controllers,
one camera), because that is where slew-to-cue products fail in the field.
**[lore]**

### 1.8 Time synchronisation

```
GNSS / national time  →  PTP grandmaster (boundary clock in each switch)
                          │  IEEE 1588, sub-µs, needs PTP-aware switching
                          ├─→ cameras (few support PTP)
                          └─→ NTP server →  cameras (ONVIF SetSystemDateAndTime)
                                        →  VMS recording servers
                                        →  analytics nodes
                                        →  access control, radar, fence
```

* NTP realistically delivers 1–50 ms on a LAN, worse over WAN, and *much* worse
  on a camera whose NTP client is a 60-second poll with no slewing.
* PTP delivers "*within a few microseconds*"
  ([Emergent](https://emergentvisiontec.com/video-accurate-multi-camera-synchronization-through-ieee-1588-ptp/)),
  operating on "*a master-slave architecture, with a single master device on the
  network designated as the reference clock*"
  ([Teledyne](https://www.teledynevisionsolutions.com/learn/learning-center/machine-vision/precision-system-synchronization-with-the-ieee-1588-precision-time-protocol-ptp/)).
  Genuine PTP support in *surveillance* (as opposed to machine-vision) cameras
  remains the exception. **[VERIFY — no surveillance-camera PTP support matrix
  retrieved this session.]**
* ONVIF exposes `SetSystemDateAndTime` / `GetSystemDateAndTime` on the device
  service, which is how a VMS both sets and *audits* camera time.
  **[VERIFY — method semantics not re-read first-hand.]**

**Three clocks, never one.** Every detection record must carry
`t_capture` (sensor/encoder), `t_inference` (when the model produced it) and
`t_ingest` (when the fusion node received it). `R05 §4.3` puts it correctly:
"*Latency is not offset*" — 200–800 ms of encode+network+decode+inference is
normal, it jitters with GOP structure and adaptive bitrate, and fusion must
associate on capture time while buffering 0.5–2 s for out-of-order arrival.

### 1.9 Camera cyber-security and supply chain

* **Vulnerability history.** CVE-2021-36260: "*insufficient input validation,
  allowing unauthenticated users to inject malicious content into a language tag
  to trigger a command injection*", affecting "*more than 70 Hikvision camera
  and NVR models*", allowing "*arbitrary commands with root privileges*"
  ([SentinelOne CVE entry](https://www.sentinelone.com/vulnerability-database/cve-2021-36260/),
  [Fortinet](https://www.fortinet.com/blog/threat-research/mirai-based-botnet-moobot-targets-hikvision-vulnerability)).
  "*Over 80,000 exploitable Hikvision cameras exposed online*"
  ([BleepingComputer](https://www.bleepingcomputer.com/news/security/over-80-000-exploitable-hikvision-cameras-exposed-online/)).
  The exploitation path: "*In December 2021, a Mirai-based botnet called
  'Moobot' used the particular exploit to spread aggressively and enlist systems
  into DDoS … swarms*" ([SecurityAffairs](https://securityaffairs.com/125409/malware/moobot-botnet-hikvision.html)).
  The generalisable lesson is not "Hikvision bad" but **"cameras are unpatched
  Linux boxes with a web server, and the patch reaches them only if someone
  built a fleet-update path"** — which is an architecture requirement (§8.3),
  not an ops afterthought.
* **Academic corroboration** that this is systemic rather than per-vendor:
  "Vulnerability Assessment and Penetration Testing on IP cameras"
  ([arXiv 2202.06597](https://arxiv.org/pdf/2202.06597)).
* **Procurement bans.** "*Under 2019 NDAA Section 889, the US federal government
  cannot 'procure or obtain' video surveillance 'produced by' Dahua or Hikvision
  — including OEMs*", with the §889(a)(1)(B) "use" prohibition effective
  13 August 2020 and applying to contractors "*regardless of whether that use*
  is related to a federal contract"
  ([IPVM](https://ipvm.com/reports/hikua-bans)) **[secondary]**. The FCC Covered
  List "*currently includes equipment and services provided by the PRC-based
  companies Huawei, ZTE, Hytera, Hikvision, Dahua, China Mobile, China Telecom,
  China Unicom, and Pacific Networks*"
  ([CRS LSB10895](https://www.congress.gov/crs-product/LSB10895),
  [Federal Register, Dec 2025](https://www.federalregister.gov/documents/2025/12/04/2025-21928/protecting-against-national-security-threats-to-the-communications-supply-chain-through-the)).
* **Architectural consequence for a UK/US defence-adjacent analytics product:**
  (a) the camera layer must be vendor-plural and NDAA-clean by default;
  (b) the product must never *require* a covered vendor's SDK; (c) OEM
  relabelling means the BoM needs an attestation per SKU, not per brand; and
  (d) because brownfield CNI sites *do* contain covered cameras, the product
  needs an ONVIF-only ingest mode that treats such a camera as an untrusted
  sensor on an isolated VLAN with egress blocked.

### 1.10 Non-camera devices on the same fabric

Thermal, radar, LiDAR, fence and audio devices arrive through the same
integration surfaces and belong in the same architecture:

* **Thermal** is the border/perimeter workhorse: detection at range in darkness,
  no useful identification. DORI-style pixel arithmetic applies with far smaller
  sensors (640×512 typical), so a thermal "detect" range is a different curve
  from a visible one. **[estimate]**
* **Radar** provides range/bearing/Doppler and is usually the geometry
  authority; cameras are the classification authority (`R05 §4.2`).
* **Audio analytics** ships as a VMS plugin — e.g. Sound Intelligence's XProtect
  plugin ([Milestone marketplace](https://www.milestonesys.com/marketplace/sound-intelligence/sound-detector-plugin-for-milestone-xprotect/), via `R05 §4.7`).
* **Genetec's RSA Surveillance** is the commercial articulation of "all of these
  under one pane": it "*integrates with a growing array of RSA technology and
  devices, such as radar, fence, video analytics, liDAR and laser-based
  solutions*", "*syncs events and alarms in real-time with Security Center*",
  and "*automatically recognizes a single target that is detected by different
  sensors as one threat as opposed to detecting multiple threats and triggering
  multiple alarms*"
  ([Genetec RSA Surveillance](https://www.genetec.com/products/unified-security/security-center/restricted-security-area),
  [brochure](https://resources.genetec.com/en-product-brochures/restricted-security-area-rsa-surveillance-in-security-center),
  [plugin guide 5.1: creating RSA zones](https://techdocs.genetec.com/r/en-US/GenetecTM-Restricted-Security-Area-Surveillance-Plugin-Guide-5.1/Creating-RSA-zones-in-Security-Center),
  [Southwest Microwave partner PDF](https://southwestmicrowave.com/pdfs/technology-partners/Genetec-RSA-Surveillance-Plugin-EN.pdf)).
  That last sentence is the whole product thesis of the fusion layer (§6), in a
  vendor's own words.

---

## 2. Transport and network

### 2.1 The canonical segmented design

```
          ┌──────────────── CORPORATE / ENTERPRISE ────────────────┐
          │  operator workstations (thin client), AD/IdP, SIEM      │
          └───────────────┬────────────────────────────────────────┘
                          │  one-way-ish: RDP/HTTPS/WebRTC only,
                          │  firewall + jump host, no camera reachability
          ┌───────────────▼──────────── VMS / OT SERVER VLAN ───────┐
          │ Management Srv │ Recording Srv ×N │ Event Srv │ SQL     │
          │ Analytics nodes (GPU) │ Kafka/MQTT broker │ TSDB/VectorDB│
          └───────────────┬────────────────────────────────────────┘
                          │  only the Recording Servers talk south
          ┌───────────────▼──────────── CAMERA VLAN(s) ─────────────┐
          │ PoE access switches ── cameras, radars, fence heads     │
          │ no default gateway out, no DNS, NTP+syslog pinholes only │
          └─────────────────────────────────────────────────────────┘
```

Rules that survive contact with reality:

1. **Cameras get their own VLAN (or one per building/tower), with no route to
   anything but the recording servers, the NTP server and the syslog
   collector.** Vendor guides converge on this; NETGEAR's surveillance guide
   covers "*private VLAN capabilities for camera isolation*" alongside
   "*Multicast VLAN Registration (MVR) … IGMP querying and snooping for
   bandwidth optimization*" ([NETGEAR IP Video Surveillance Networking Solution
   Guide](https://www.netgear.com/images/pdf/IP-Video-Surveillance_Networking-Solution-Guide.pdf)) **[secondary]**.
2. **Recording servers are dual-homed**, camera-side and server-side, and are the
   only bridge. This is what makes a camera compromise (§1.9) survivable.
3. **QoS/DSCP** marking for video (AF41-ish) matters only when the link is
   shared; on a dedicated camera VLAN it is theatre. On a *backhaul* link (§2.5)
   it is essential.
4. **Cisco's Video Surveillance SRND** remains the most complete written
   articulation of the classic three-tier design and of multicast in surveillance
   (Class D 224.x–239.x, multicast-enabled network requirements)
   ([Cisco VSM 7.0 SRND](https://www.cisco.com/c/dam/en/us/td/docs/security/physical_security/video_surveillance/network/vsm/7_0/srnd/vsm_7_0_srnd.pdf)) **[secondary]**.
   ALAXALA publish worked VLAN + PIM-SM/IGMP configurations
   ([AX Series surveillance guide](https://www.alaxala.com/en/techinfo/archive/guide/pdf/N11R050_MCN_Solution_Guide_V1R0_e.pdf)) **[secondary]**.

### 2.2 Bandwidth and storage arithmetic

The arithmetic is trivial and is nevertheless the most common source of
project-killing surprises, because people compute *average* and provision for
*average*.

Definitions: `N` cameras, `B` = per-camera main-stream bitrate (Mbit/s),
`b` = substream bitrate, `R` = retention days, `D` = recorded duty cycle
(1.0 for continuous, ~0.3 for motion-triggered on a quiet site).

```
Ingest to recording servers   = N × (B + b)            Mbit/s
Storage (usable)              = N × B × D × 86400 × R / 8 / 1e6   TB  (B in Mbit/s)
                              ≈ N × B × D × R × 10.8   GB
Live-wall egress (unicast)    = M_viewers × cams_per_view × b
Analytics ingest              = N × b            (gating tier)
                              + k × B            (k = cameras escalated at once)
```

Worked examples **[estimate, arithmetic only]**:

| Site | N | B | b | D | R | Ingest | Raw storage |
|---|---|---|---|---|---|---|---|
| Small retail/industrial | 8 | 4 | 0.4 | 1.0 | 30 | 35 Mbit/s | ~10.4 TB |
| CNI plant | 200 | 4 | 0.5 | 1.0 | 31 | 900 Mbit/s | ~268 TB |
| CNI plant, H.265 + 0.4 duty | 200 | 2 | 0.4 | 0.4 | 31 | 480 Mbit/s | ~53 TB |
| Border, 25 towers × 3 sensors | 75 | 3 | 0.3 | 1.0 | 14 | 248 Mbit/s | ~34 TB |

Add: +10–20 % container/index overhead; RAID/erasure-coding overhead
(RAID-6 on 12 disks ≈ 83 % usable); a **write cache** sized for the burst when
every camera alarms at once; and separate, *much longer* retention for
**metadata** than for video (§5.6).

**The peak that kills you:** bitrate is specified as a target but VBR encoders
overshoot 2–4× on a scene change — headlights at night, rain, a crowd, a
strobing alarm beacon. Storms produce correlated overshoot on *every* camera
simultaneously. Provision the network for `N × B_peak`, not `N × B_avg`, or
provision CBR and accept the quality floor. **[lore]**

### 2.3 Multicast vs unicast

Multicast's benefit is precisely stated by Synectics: "*with multicasting, the
network bandwidth remains the same between the camera and the network's core even
as the number of receivers increases*"
([Synectics tech note on IP multicasting](https://www.synecticsglobal.com/en/resources-en/tech-notes/209-multicasting)).

When it is worth it: large control rooms with many operators watching the same
cameras, and video-wall decoders. When it is not: analytics (one consumer), small
sites, and any path crossing a firewall or a WAN. The cost is operational —
IGMP snooping and a querier per VLAN, PIM on routed segments, and a failure mode
(flooding every camera stream to every port) that saturates access switches and
is diagnosed by nobody at 2 a.m. **Default to unicast; enable multicast only for
the live wall.** **[lore]**

### 2.4 Air-gapped and OT constraints

On CNI and defence sites the analytics stack frequently sits inside an OT
enclave with:

* **no outbound internet** → no container registry pulls, no licence
  phone-home, no cloud model updates, no NTP from pool.ntp.org, no telemetry.
  Every one of those must have an offline path designed in *before* contract:
  an on-site registry mirror, offline licence files, a signed model bundle
  imported by a documented media-transfer procedure, a local stratum-1 clock.
* **data diodes / one-way gateways** between the OT enclave and the enterprise
  network: your alerting path may be *outbound only*, which forbids any design
  where the cloud calls into the edge. Design edge→centre push (MQTT/Kafka
  producer), never centre→edge pull. **[lore]**
* **change control**: a model update is a *change* requiring a window and a
  rollback plan. This is why shadow deployment (§4.7) is not a nice-to-have but
  the only politically survivable way to update a model on a CNI site.

### 2.5 Backhaul for distributed sites (borders, linear assets, towers)

```
tower  ──60 GHz / 5 GHz PtP mesh──┐
tower  ──────────────────────────┤ aggregation node ── fibre ── regional hub ── NOC
tower  ──LTE/5G private or public─┤   (local storage,
tower  ──GEO/LEO satellite────────┘    local inference)
```

Budget reality **[estimate]**: a LEO satellite or cellular link that delivers
5–25 Mbit/s uplink with 30–90 ms (LEO) or 500–700 ms (GEO) latency cannot carry
75 main streams. Therefore, at distributed sites:

* **All detection happens at the tower.** Non-negotiable. The link carries
  *metadata* (bytes per track, not megabits per camera), plus **on-demand** video
  pulled only for the seconds around an alert, plus low-rate thumbnails.
* **Edge caching / store-and-forward** is mandatory: record locally at full
  rate, retain 7–30 days on the tower, and backfill on request. This is exactly
  what ONVIF Profile G edge recording plus VMS "gap filling" is for (§3.2).
* **Bandwidth shaping by event class**: a P1 alarm gets a live stream; a P3
  activity record gets 3 JPEGs.
* The Anduril Sentry deployment is the public reference point for this pattern:
  a "*collection of sensors atop a 33ft (10m) pole: electro-optical cameras with
  thermal imaging, and radar equipment*", where "*data collected by Sentry's
  sensors feeds into Lattice, which uses AI and machine learning to enable and
  visualize the detection of people*", and the tower "*autonomously scans the
  vicinity and classifies and tracks 'objects of interest'*"
  ([Privacy International, "Dual-use tech: the Anduril example"](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example)).
  Solar-powered, autonomous, edge-classifying — because the backhaul cannot
  carry anything else.

### 2.6 Viewing path: why WebRTC is eating the thick client

Control rooms historically used a proprietary thick client (Smart Client, Security
Desk) because browsers could not do low-latency multi-stream video. That is
changing: "*WebRTC ingests and delivers video from capture to playback in under
500 milliseconds*", and WHEP — "*WebRTC-HTTP Egress Protocol*" — "*enables adding
browser based low latency viewing of streaming content*"
([Wowza, Architecting WebRTC for Surveillance and Remote Monitoring](https://www.wowza.com/blog/architecting-webrtc-for-surveillance-and-remote-monitoring),
[bloggeek.me WHEP glossary](https://bloggeek.me/webrtcglossary/whep/)).
Wowza describe the exact dual-path architecture a product should adopt: "*the
same video ingested for archival can be forked, packaged, and delivered over
WebRTC for real-time viewing while it is simultaneously preserved as
high-quality MP4 or MKV files*" ([ibid.]), and note "*sub-500-millisecond latency
to Chrome, Safari, Firefox, and Edge*" with "*the standards-based path
remov[ing] the need for a proprietary client SDK*"
([Wowza 4.11 release blog](https://www.wowza.com/blog/wowza-streaming-engine-4-11-updates-webrtc-for-production-scale-cloud-native-streaming)).

`mediamtx` gives us the same capability for free in the lab — it converts
"*automatically … from a protocol to another*" and serves WebRTC/WHEP from an
RTSP source ([mediamtx](https://github.com/bluenviron/mediamtx)) — which is
directly useful for SurvSim's review UI (§11).

**Architectural rule:** the operator UI must never be the only consumer of a
detection. Alarms go to the queue (durable), to the audit log (immutable), and
to the UI (ephemeral). A UI-first design loses alarms on refresh.

---

## 3. The VMS/NVR layer

### 3.1 Milestone XProtect — the component model to design against

Milestone's own architecture documentation is unusually clear, and because
Milestone is the most likely first integration target for a UK analytics product
it is worth internalising the component split:

* **Management Server** — "*the central VMS component that handles the system
  configuration and distributes the configuration to other system components,
  such as the recording servers*"; runs as a service, typically dedicated.
* **Recording Server** — "*responsible for all communication, recording, and
  event handling related to devices*". A system "*typically consists of several
  recording servers*". This is the only component that talks to cameras.
* **Event Server** — "*hosts the alarm feature, alarm logic, alarm state and
  handling of the alarm database*", "*also hosts maps*", and "*handles the tasks
  related to events, alarms, maps and third-party integrations via the Milestone
  Integration Platform*".
* **SQL** — "*The management server, the event server and the log server use SQL
  databases … to store, for example, configuration, alarms, events and log
  messages*".
* **Scaling** — "*You can install all components on a single server if the server
  can handle the load, or you can install the components on separate, dedicated
  servers to scale and distribute the load*".

(All quotes: [Milestone "Server components"](https://doc.milestonesys.com/2021r2/en-US/system/sad/sad_servercomponents.htm),
[XProtect VMS System Architecture Document](https://milestonedownload.blob.core.windows.net/files/XProtect%202019%20R1/Manuals%20and%20guides/Advanced%20VMS/Guides%20and%20documents/System%20architecture%20document/MilestoneXProtectVMSproducts_SystemArchitectureDocument_en-US.pdf),
[storage architecture white paper](https://netcam.cz/produkty/software-sprava-videa/pdf/xprotect_corporate_wp_milestone_storage_architecture.pdf)) **[secondary]**

```
        ┌──────────────┐   config    ┌───────────────┐
        │ Management   │────────────▶│ Recording Srv │◀── RTSP/ONVIF ── cameras
        │ Server (+SQL)│             │  (media DB)   │
        └──────┬───────┘             └───────┬───────┘
               │                             │ events, metadata, live/playback
        ┌──────▼───────┐   alarms    ┌───────▼───────┐
        │ Log Server   │◀────────────│ Event Server  │──▶ MIP plug-ins, maps,
        └──────────────┘             │ (alarm DB)    │    3rd-party integrations
                                     └───────┬───────┘
                          Smart Client / Web Client / Mobile
```

**Where analytics plugs in (four doors, pick deliberately):**

1. **Device driver** (MIP SDK device pack) — pretend to be a camera. Right answer
   for a *sensor*, wrong answer for an analytic.
2. **Metadata producer** — the ONVIF MetadataStream schema is the exchange
   format: "*Producers of metadata can be hardware devices (usually cameras), or
   analytics services that uses the MIP SDK to send data to the XProtect VMS. A
   common exchange format, the ONVIF MetadataStream schema, decouples the
   producer from the consumer*"
   ([MIP metadata intro](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html), via `R01 §5.2`).
   This gives you bounding boxes drawn over live and recorded video *inside the
   customer's existing client* — the single highest-leverage integration.
3. **Analytic/generic event + alarm definition** — gets you into the alarm queue
   and the Rules engine, so the customer can attach their own actions (record at
   higher quality, move a PTZ to a preset, send email, trigger output).
4. **Milestone AI Bridge** — the modern container path. It "*acts as a bridge
   between installations of XProtect … and Intelligent Video Analytics (IVA)
   applications deployed as docker containers*" and "*allows the IVA applications
   to send the analysis results back into your XProtect VMS as Events, Metadata,
   and Video*" (via `R01 §5.2`). The architecture is worth quoting because it
   mirrors what we would build anyway: "*Milestone AI Bridge has an event driven
   architecture and much of the communication between the containers takes place
   through brokers and topics provided by Apache Kafka*"; it "*runs on
   linux-based docker images*" and "*can be deployed, maintained and operated
   using Kubernetes or docker compose*"; and on the media side it "*uses the RTSP
   protocol and a gRPC based protocol named Direct Streaming*", with "*filtering
   … supported for both RTSP and Direct Streaming (gRPC)*"
   ([Milestone AI Bridge containers](https://doc.milestonesys.com/AIB/Help/Latest/en-US/feature_flags/ff_aibridge/aibi_overview_containers.htm),
   [Integrator manual 2.0](https://doc.milestonesys.com/AIB/PDF/v2_0/en-US/MilestoneAIBridge_IntegratorManual_en-US.pdf),
   [Docker Compose config](https://doc.milestonesys.com/AIB/Help/latest/en-us/feature_flags/ff_aibridge/aibi_dc_configureaib.htm)) **[secondary]**.
   It is distributed on NGC ([Milestone dev article](https://milestonesys.my.site.com/developer/s/article/THE-MILESTONE-AI-BRIDGE-v1-5-IS-NOW-AVAILABLE-ON-NGC)).

**Direct Streaming (gRPC) is the detail to notice.** It means an analytics
container can get decoded-or-encoded frames from the recording server without
each container opening its own RTSP session to each camera — which is the single
biggest scaling problem of the naive "N containers × M cameras" design (see
anti-pattern A3, §13).

**Automation/CI hook.** Milestone publish PowerShell tooling — "*sample
PowerShell scripts for managing and automating tasks related to Milestone
XProtect VMS software*" — including adding hardware ("*Add a StableFPS device
(if the driver is installed)*", "*Add a camera without specifying the driver*"),
bulk configuration ("*Enable all camera channels*"), and media extraction
("*Save a live snapshot from all enabled cameras*")
([MilestoneSystemsInc/PowerShellSamples](https://github.com/MilestoneSystemsInc/PowerShellSamples)).
The mention of the **StableFPS** driver is directly relevant to §11: it is
Milestone's file-fed pseudo-device, the mechanism by which a synthetic dataset
becomes a camera inside a real VMS.

### 3.2 Recording, retention, gap-filling

* **Storage tiering**: XProtect-style live/archive split, where recent recordings
  sit on fast local storage and are archived to slower/bulk storage with optional
  frame-rate reduction (grooming). Metadata and index remain searchable after
  the video is groomed. **[VERIFY — grooming specifics not re-read this session;
  Milestone storage white paper is the source.]**
* **Edge gap-filling**: camera records to SD/edge storage during a network
  outage; the VMS retrieves the missing interval afterwards via ONVIF Profile G
  replay. Without this, a 4-hour switch failure is a permanent hole in the
  evidential record. Design the *retrieval* path and its bandwidth impact — a
  fleet of 200 cameras all backfilling at once after a WAN restoration will
  saturate the link that just came back. **[lore]**
* **Retention as a legal parameter, not a technical one**: driven by the data
  protection regime and the operational requirement, then multiplied by the
  storage arithmetic of §2.2.

### 3.3 Export and evidence

Export is the feature the customer uses on the worst day of their career.
Requirements that repeatedly appear:

* **Native/database export** with the vendor's player, preserving the original
  encoded bitstream plus the signature/checksum — the only form courts and
  internal investigators reliably accept as unaltered.
* **AVI/MP4 transcode** for convenience, explicitly marked as a derived copy.
* **Still images** with the burnt-in timestamp and camera identity.
* **Digital signature / hash manifest** over the exported package, plus
  password protection; and **watermarking** of the video (visible or
  cryptographic) to detect tampering after the fact.
* **Export audit**: who exported what, when, for what case reference. This is
  itself usually a higher-sensitivity log than the video.

**Chain of custody** in practice is a documented sequence — acquisition
(who pulled it, from which recording server, over what interval), hashing at
acquisition, storage in a case-management system with access logging, and every
subsequent copy recorded. The architecture requirement for *our* analytics
product is narrower but non-negotiable: **the analytic must never be in the
evidential path.** Its output is an *index into* the recording, never a
substitute for it. If an operator can only see the model's crop, the evidence has
been reduced to the model's opinion. **[lore]**
**[VERIFY — no jurisdiction-specific digital-evidence standard (e.g. ACPO/ISO
27037) was retrieved this session; do not cite clause numbers.]**

### 3.4 The other VMSes, and what changes

* **Genetec Security Center** — unified video + access control + ANPR. Integration
  surfaces: the Security Center SDK, plugins, and the Media Gateway; Mission
  Control is the PSIM/SOP layer above it (§6.4). Genetec also ships **RSA
  Surveillance** as the perimeter-fusion product (§1.10), and
  "*Genetec Security Center SaaS is a unified physical security solution … deployed
  on a hybrid-cloud architecture*"
  ([Genetec RSA page](https://www.genetec.com/products/unified-security/security-center/restricted-security-area)) **[secondary]**.
  The practical difference from Milestone is that Genetec's world model is
  *entity*-centric (doors, cardholders, areas, LPR hits) rather than
  camera-centric, which makes access-control fusion easier and pure-video
  metadata integration slightly more opinionated.
  **[VERIFY — Genetec SDK/plugin mechanics were not sourced first-hand this
  session; `R05 §4.7` flags the same gap.]**
* **Avigilon (Motorola) ACC / Alta** — vertically integrated cameras + VMS with
  strong first-party analytics (appearance search). Third-party analytics
  competes with the host's own features, which is a commercial problem before it
  is a technical one. **[VERIFY]**
* **Network Optix (Nx Witness / Nx Meta)** — the most developer-friendly of the
  group, and the one to build on for an OEM'd product. "*The Metadata SDK enables
  the integration of 3rd party video analytics systems and devices … by
  supporting the exchange of metadata and events*"; plugins are "*installed on
  the Nx Server application*"; it allows "*transmitting bounding box and metadata
  attributes for objects detected into a special object database in Nx EVOS and
  displaying bounding boxes over live or recorded video*"
  ([Nx Server Plugin SDK](https://support.networkoptix.com/hc/en-us/articles/202856206-C-SDK),
  [The Server Plugin SDK (C++)](https://support.networkoptix.com/hc/en-us/articles/32766542038423-The-Server-Plugin-SDK-C),
  [Nx Toolkit](https://www.networkoptix.com/developers/nx-toolkit)).
  The repo shows the real integration paths — C++ VMS server plugins, an
  HTTP/REST `api_sample`, and worked OpenVINO and OpenCV detection plugins
  ([networkoptix/nx_open_integrations](https://github.com/networkoptix/nx_open_integrations),
  [OpenVINO plugin readme](https://github.com/networkoptix/nx_open_integrations/blob/master/cpp/vms_server_plugins/openvino_object_detection_analytics_plugin/readme.md)).
  Note the key design point: **an object database inside the VMS** — Nx stores
  detections so they are searchable, which is the pattern our product needs
  regardless of VMS (§5.5).
* **Exacq (Johnson Controls)** — strong in US retail/commercial, hybrid NVR
  appliances; integration via its own API/plugin route. **[VERIFY]**

**Portfolio conclusion for the vendor-style product:** build the core as a
VMS-agnostic service that speaks **ONVIF Profile M metadata + MQTT/Kafka events +
an OpenAPI REST surface**, then ship thin adapters: Milestone (AI Bridge +
metadata provider), Nx (server plugin), Genetec (plugin), plus a raw-RTSP mode
for sites with no VMS. Budget one engineer-quarter per adapter and an ongoing
tax for each VMS's release cadence. **[estimate]**

---

## 4. Analytics compute — where the model actually runs

### 4.1 The five placements, and how to choose

```
 (a) IN CAMERA        ACAP/HEOP/Wisenet/IVA on SoC NPU
     +no server, +no stream cost, +lowest latency
     −tiny model, −no cross-camera, −per-vendor build, −slow fleet updates

 (b) EDGE BOX         Jetson / Hailo / x86+OpenVINO beside the switch
     +1–20 cams, +works air-gapped, +full model
     −a box per site to patch, −decode ceiling, −thermals

 (c) AI-IN-NVR        analytics container on the recording appliance
     +no new hardware, +already trusted by IT
     −steals CPU from recording (the one job that must not fail)

 (d) ON-PREM GPU      1–8 GPU servers in the customer rack
     +100–1000 cams, +MTMC/ReID feasible, +full observability
     −capex, −HA design work, −datacentre space/power/cooling

 (e) CLOUD/HYBRID     edge gate + cloud heavy analytics & search
     +elastic, +central MLOps, +cheap long-term search
     −egress cost, −latency, −often legally impossible (§7)
```

Selection heuristic **[lore]**: choose the *rightmost* placement the customer's
data policy and network will allow, then move the latency-critical stage
leftwards. Concretely: gating/detection at (b), ReID + cross-camera fusion at
(d), natural-language search and retraining at (e) if permitted, (d) if not.

### 4.2 Edge silicon, with numbers

| Device | Claimed/observed capability | Source |
|---|---|---|
| Jetson Orin NX 16 GB | "*can handle up to 18 streams of 1080p30*" for video analytics | [Seeed Studio](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/) (via `R01 §5.1`) [staleness v2: decode ceiling only — with detect+ReID compute ≈ 12 cams/NX, so 40 cams → 4 NX; FACTS, 38 §2.5] |
| Jetson AGX Orin 64 GB | datasheet "*total stream density of 18× 1080p30*" for H.265 decode; DeepStream ">30 concurrent 1080p@30" claimed; **but** practitioners hit "*an unexpected limit of 8 concurrent NVDEC video streams*" in JetPack 6, and "*up to 8 streams per DLA … (16 total)*" | [NVDEC ≤8 thread](https://forums.developer.nvidia.com/t/orin-agx-jetpack-6-nvdec-limitation-of-8-streams/320865), [Orin NX NVDEC capacity thread](https://forums.developer.nvidia.com/t/orin-nx-16gb-nvdec-capacity-for-4x-2560x1440-h-265-streams-and-super-mode-impact/380328), [1080p30-per-NVDEC thread](https://forums.developer.nvidia.com/t/how-much-1080-30fps-can-be-run-in-one-nvdec/376889) |
| AGX Orin, YOLOv8s INT8 | "*12–20 streams … at 1080p30*" | [vhd.me edge-to-server chip guide](https://vhd.me/best-chips-real-time-video-analytics/) **[secondary]** |
| Hailo-8 | "*26 Tera-Operations Per Second (TOPS) … typical power consumption of 2.5W*", PCIe Gen3 ×2, passive; independent estimate "*roughly 4 full-rate 1080p detection streams*" | [Hailo-8](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/), [edgeaistack](https://edgeaistack.ai/blog/hailo-8-vs-8l-vs-10h-2026/) (both via `R01 §5.1`) |
| Axelera Metis, Ambarella CVflow, Qualcomm QCS, Google Coral, Intel iGPU/NPU + OpenVINO | positioned in the same 1–20-stream envelope at 5–40 W | **[VERIFY — no per-device numbers retrieved this session]** |

**Derived planning rule [estimate]:** for an edge box, size on
`min(decoder_sessions, inference_throughput/frames_needed, memory_bandwidth)` and
then apply a 0.6 factor for the tracker, the ReID head, the encoder for clip
export, and the OS. Publish the *derated* number in the BoM. The ordered
bottleneck list from `R01 §5.1` — decode, memory bandwidth, inference, tracker,
ReID-per-detection — is the single most useful piece of practitioner lore in this
document and should be repeated to every customer who asks "how many cameras per
box?".

**The TensorRT deployment landmine** (from `R01 §5.1`, worth restating because it
belongs to *architecture*, not to modelling): "*engine files are GPU-arch- and
version-specific — an engine built on one driver may not load on another*". The
architectural response is to build engines **on the target, at install/update
time**, inside the same container image, and cache them in a volume keyed by
`(gpu_arch, driver, trt_version, model_hash)`. Any design that ships prebuilt
engines will break on the customer's next driver update.

### 4.3 The GStreamer/DeepStream pipeline, concretely

```
 rtspsrc ─▶ rtph26xdepay ─▶ h26xparse ─▶ nvv4l2decoder (NVDEC)
                                                  │
              (×N cameras) ────────────────▶ nvstreammux (batch=N)
                                                  │
                                      nvinfer  (PGIE: detector, TensorRT)
                                                  │
                                      nvtracker (IOU / NvSORT / NvDCF / DeepSORT)
                                                  │
                                      nvinfer  (SGIE: ReID / attribute, per-object)
                                                  │
                                      nvdsanalytics (ROI, line-cross, direction)
                                                  │
                        ┌──────────────┬──────────┴────────────┐
                nvmsgconv+nvmsgbroker  nvmultistreamtiler   nvvideoconvert
                (Kafka/MQTT/AMQP JSON)  (live wall)          (clip encode → NVENC)
```

The DeepStream reference apps demonstrate exactly the pieces a product needs:
"*runtime source addition/deletion*" (add and remove cameras from a live
pipeline without restarting — the difference between a demo and a product),
"*multiple models inferencing in parallel*", "*multi-view 3D tracking*" described
as a "*distributed, real-time framework for camera networks*",
"*video buffers sharing between pipelines through IPC*", and
"*custom-tile-config of nvmultistreamtiler*"
([NVIDIA-AI-IOT/deepstream_reference_apps](https://github.com/NVIDIA-AI-IOT/deepstream_reference_apps)
— note the repo "*has ceased updates*" and points to the primary DeepStream repo).

Per-stage warnings **[lore]**:

* `nvstreammux` batch size must equal the real camera count or you silently
  serialise; `batched-push-timeout` governs what happens when one camera stalls —
  set it, or one dead camera throttles all the others to its cadence.
* `interval` (skip frames) is how vendors inflate published stream counts;
  `R01 §5.1` already warns that published numbers "*assume a specific model,
  resolution, batch size, inference interval (often skipping frames), and no
  tracker, no tiling and no secondary classifier*".
* The SGIE (ReID/attributes) scales with **objects**, not streams. `R01`:
  "*a queue of 60 people can cost more than 10 empty cameras*". Cap
  objects-per-frame and make the cap visible in telemetry, because a silently
  truncated detection list is indistinguishable from a model failure.
* Pipeline restarts must be *per-source*, supervised, with exponential backoff
  and a "camera flapping" alarm.

### 4.4 Metropolis / VSS: the vendor reference architecture to borrow from

NVIDIA's MTMC reference is the most detailed public articulation of
multi-camera tracking as a *deployable service*, and the design choices are worth
copying:

* **Two microservices for multi-camera fusion**: MTMC (multi-target
  multi-camera) and **RTLS** (real-time location system). They "*first transform
  raw data into behaviors, including trajectories and embeddings*", then
  "*these behaviors are clustered and global IDs are assigned, leveraging both
  re-identification (ReID) features and spatio-temporal information*".
* **Batch or stream mode**: "*Stream Processing deals with live data input from a
  Kafka topic, processing information in micro-batches*", and "*maintains the
  state of behavioral data, integrating new clustering results with pre-existing
  IDs*".
* **Algorithm**: "*leverages hierarchical clustering to cluster live behaviors and
  refines these clusters through iterative reassignment using the Hungarian
  matching algorithm*".
* **Packaging**: "*Cloud-native NVIDIA Metropolis microservices are designed to
  deploy at scale with Kubernetes and manage with HELM*".

(All via [NVIDIA multi-camera tracking workflow](https://www.nvidia.com/en-us/ai-data-science/ai-workflows/multi-camera-tracking/),
[MDX MTMC microservice overview](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_MS_Overview.html),
[MDX MTMC app quickstart](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_App.html),
[configuration](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_MS_Configuration.html),
[live demo](https://demos.ngc.nvidia.com/metropolis_multicam)) **[secondary — docs.nvidia.com blocked by proxy]**

There is also a documented 3D route, "3D Multi Camera Detection and Tracking
(Sparse4D)" ([VSS warehouse docs](https://docs.nvidia.com/vss/3.1.0/warehouse-docs/3D-multi-camera-detection-and-tracking-Sparse4D.html)) **[secondary]**.

**The VSS blueprint** shows where the market is heading — from alerts to
*retrieval*. Fetched first-hand: the blueprint "*comprises three integrated
processing layers. Real-time video intelligence extracts features and embeddings
from video streams, publishing results to message brokers. Downstream analytics
enriches this metadata into trajectories and verified alerts. Finally, agentic
processing orchestrates tools for search, Q&A, and summarization through the
Model Context Protocol*", supporting "*Video retrieval, VLM-based Q&A, and report
generation on short video clips*", "*alert verification through perception and
behavior analytics*", and "*natural language search across archives using video
embeddings*" ([NVIDIA-AI-Blueprints/video-search-and-summarization](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)).
Crucially for our architecture, **VST is the VMS-shaped component**: "*Video
Storage Toolkit (VST) is used as a Video Management System (VMS) or to interface
with third-party VMS solutions*"
([VSS public-safety blueprint introduction](https://docs.nvidia.com/vss/3.1.0/publicsafety-docs/Introduction.html),
[blueprint deep dive](https://docs.nvidia.com/vss/3.1.0/publicsafety-docs/Blueprint-deep-dive.html)) **[secondary]**.
The deep-dive divides the system exactly as we should: "*the blueprint
architecture can be divided into a realtime streaming component and an agentic
component*" ([ibid.]).

**Alert verification** is the most commercially interesting idea in that stack: a
cheap detector fires, and a VLM is asked "is this actually a person climbing the
fence?" before the operator is woken. It converts the false-alarm problem from a
threshold-tuning exercise into a second-opinion architecture. It also introduces
a new failure mode — a confident, fluent, wrong explanation — which is why any
such verifier must be logged with its input crop so it can be audited. **[lore]**

### 4.5 Inference serving: Triton

For the on-prem GPU tier, Triton is the default model server and its feature set
maps directly onto deployment needs: backends for "*TensorRT, PyTorch, ONNX,
OpenVINO, Python, RAPIDS FIL, and more*"; a "*Dynamic batcher*"; "*Model
pipelines using Ensembling or Business Logic Scripting (BLS)*"; a model
repository where you can "*explicitly manage what models are available by loading
and unloading models*"; and "*Metrics indicating GPU utilization, server
throughput, server latency*"
([triton-inference-server/server](https://github.com/triton-inference-server/server)).

Why this matters architecturally: **ensembles + model repository versioning are
how you do canary and shadow deployment of a detector without redeploying the
pipeline.** The DeepStream pipeline points at a Triton endpoint and a model name;
the model *version* is a config change with a rollback.

### 4.6 On-prem GPU sizing

Planning skeleton **[estimate]**:

```
streams_per_GPU ≈ min( NVDEC_sessions,
                       det_fps_budget / (fps_analysed × 1),
                       reid_fps_budget / (people_per_frame × fps_analysed) )
```

with `fps_analysed` typically 5–12 (not 25 — nobody needs 25 Hz detection for
people), and `people_per_frame` the real driver of cost. For an L40S/A30-class
card running a 640-px detector at INT8 plus an OSNet-class ReID head, budget
**20–40 cameras per GPU at 8 fps analysed with ≤10 people per frame**, halving
for crowded scenes and for any 4K analytics. Then add a second GPU for
headroom/HA, because "the analytics is down" and "the CCTV is down" are the same
sentence to a customer. Do not exceed ~4 GPUs per 2U box without checking NVDEC
aggregate and PCIe topology.

### 4.7 MLOps: versioning, drift, shadow mode, retraining

This is where a research-grade system becomes a product, and where SurvSim earns
its keep. The loop, in the form it must take on a customer site:

```
   site cameras ──▶ analytics (model vN, primary)
        │                 │  detections/alerts ──▶ operators (acted upon)
        │                 └──────────────┐
        └──▶ analytics (model vN+1, SHADOW: no alerts, logged only)
                                         ▼
                 comparison service: agreement matrix, new-FP triage,
                 missed-detection triage against operator-confirmed truth
                                         ▼
                 promote / reject decision + written change record
                                         ▼
        curated corrective set (hard negatives from THIS site)
                 + SurvSim scenarios reproducing the failure geometry
                                         ▼
                 retrain → regression suite (§11.5) → sign-off → vN+2
```

Non-negotiables **[lore]**:

* **Model registry with immutable versions**, each carrying: training-data
  manifest hash, class list, input preprocessing, calibration data, expected
  metrics, and the site-classes it is approved for. A model whose preprocessing
  is not versioned *with* it will silently degrade when someone changes the
  resize mode.
* **Drift monitoring on inputs, not just outputs.** Track mean luminance,
  contrast, blur estimate, detection-count distribution, box-size histogram and
  bitrate per camera. A camera that drifts is almost always a *physical* problem
  (spider web, focus, IR failure, repositioning) — which means input-drift
  monitoring doubles as maintenance detection, which is how you sell it.
* **Shadow mode is the only acceptable change mechanism on CNI.** See §2.4.
* **Per-site thresholds, centrally governed.** Every site will need its own
  sensitivity; that must be data, versioned and audited, not an engineer with
  SSH access.
* **Feedback capture from the operator UI** ("this was a nuisance alarm —
  vegetation / animal / weather / reflection") is the highest-value dataset the
  company will ever own, and the only one that is genuinely proprietary. Design
  the click before the model.

### 4.8 Containerisation and orchestration at the edge

* **k3s** is "*a highly certified Kubernetes distribution … designed for
  resource-constrained Internet of Things (IoT) devices and is packaged as a
  single <40 MB binary*" ([reintech k3s tutorial](https://reintech.io/blog/k3s-tutorial-lightweight-kubernetes-edge-iot), [oneuptime](https://oneuptime.com/blog/post/2026-02-02-k3s-edge-computing/view)) **[secondary]**.
* **AWS IoT Greengrass v2** can be layered onto it: "*You can set up a Kubernetes
  cluster using k3s within an edge node, install the AWS Systems Manager Agent
  (SSM Agent), and deploy AWS IoT Greengrass V2 using standard Kubernetes tools
  like kubectl*" ([AWS containers blog](https://aws.amazon.com/blogs/containers/collecting-data-from-edge-devices-using-kubernetes-and-aws-iot-greengrass-v2/),
  [aws-samples/aws-kubernetes-edge-greengrass](https://github.com/aws-samples/aws-kubernetes-edge-greengrass)).
  AWS also documents a Kinesis Video Streams edge deployment path
  ([gs-deploy-edge](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/gs-deploy-edge.html)).
* **Azure IoT Edge** brings "*IoT Hub's device twin capabilities and
  DevOps-friendly update pipelines*", while "*AWS provides centralized monitoring
  and updates via IoT Core and CloudWatch*"; fleet governance tools include
  "*Azure Arc, Red Hat Advanced Cluster Management, and AWS IoT Greengrass*",
  which "*make it possible for teams to enforce rules, query cluster status, and
  pull logs from thousands of distributed edge locations*"
  ([comparison](https://www.researchgate.net/publication/398152009_Developing_Intelligent_Edge_Solutions_Using_AWS_Greengrass_and_Azure_IoT),
  [industrial edge platforms compared](https://adhdecode.com/edge-computing/industrial-edge-iiot/industrial-edge-platforms-compared/)) **[secondary]**.
* **AWS Panorama** was the purpose-built appliance for exactly this pattern.
  **[VERIFY — current product status not confirmed this session; check before
  proposing it to a customer.]**

**Recommendation for an air-gap-capable product [estimate]:** plain
`docker compose` for 1-box edge sites (fewer moving parts, no control plane to
break, matches Milestone AI Bridge's own supported mode), `k3s` for multi-node
edge clusters and for towers where you want self-healing, and full Kubernetes
only in the on-prem datacentre tier. Ship a single signed bundle (images +
compose/helm + models + config schema) that installs offline, and an update
mechanism that is atomic and reversible.

---

## 5. Data and messaging

### 5.1 The event backbone

```
edge analytics ──┬─▶ MQTT (QoS1, TLS, client certs)   ── small, lossy links, towers
                 ├─▶ Kafka (partition per site/camera) ── on-prem, replayable, durable
                 └─▶ NATS/JetStream                    ── lightweight, request-reply
                          │
                 ┌────────┴──────────────────────────────────────────┐
                 ▼             ▼              ▼            ▼          ▼
            VMS adapter    fusion engine    TSDB       vector DB    data lake
            (metadata,     (§6)          (metrics,    (embeddings,  (clips +
             alarms)                      counts)      search)       manifests)
```

Selection guidance **[lore]**:

* **MQTT** where the network is thin, intermittent or one-way-ish: tiny header,
  QoS 1/2, last-will (which gives you free "edge node died" detection), and it is
  the protocol ONVIF Profile M itself blesses for IoT events
  ("*events using JSON and the MQTT protocol for IoT applications*",
  [ONVIF](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/)).
* **Kafka** where you need replay, ordered partitions and multiple independent
  consumers at rate — which is precisely why both Milestone AI Bridge
  ("*much of the communication between the containers takes place through brokers
  and topics provided by Apache Kafka*") and NVIDIA MTMC ("*live data input from
  a Kafka topic*") chose it. Replay is the feature that matters most: it lets you
  re-run a new fusion algorithm over last month's real detections without
  touching video.
* **NATS** when you want a broker you can forget about on an edge box.

Topic design that has held up **[estimate/lore]**:
`site.{site}.cam.{cam}.det`, `...track`, `...event`, `site.{site}.fusion.track`,
`site.{site}.alarm`, `site.{site}.health`. Keys: camera id for detections (order
per camera), global track id for fused tracks. Separate *high-volume, short
retention* (detections: hours) from *low-volume, long retention* (alarms:
years).

### 5.2 Schemas — detections, tracks, events

The single most important architectural artefact after the network diagram is a
versioned JSON schema set. Minimum viable shapes **[estimate; align to ONVIF
Profile M field names wherever they exist]**:

```jsonc
// detection (per object per analysed frame)
{ "schema": "det/1.2", "site": "SITE-07", "camera": "CAM-014",
  "t_capture": "2026-09-17T21:14:03.120Z",   // authoritative for association
  "t_inference": "2026-09-17T21:14:03.560Z",
  "frame_seq": 918273, "class": "person", "conf": 0.87,
  "bbox": [412, 188, 96, 241],                // x,y,w,h in pixels
  "bbox_norm": [0.32,0.26,0.075,0.33],
  "ground_point": {"x": 41.2, "y": -8.7, "crs": "site_local_m"},
  "geo": {"lat": 51.5012, "lon": -0.1402, "err_m": 3.5},
  "attributes": {"upper_colour":"dark","carrying":"bag","face_visible":false},
  "embedding_ref": "emb://v3/9f2c...", "model": "det-yolo-x@4.2.1" }

// track (per camera)
{ "schema":"track/1.1", "camera":"CAM-014", "track_id":"CAM-014:5521",
  "t_start":"...","t_last":"...","state":"active",
  "points":[{"t":"...","x":41.2,"y":-8.7,"conf":0.9}],
  "class":"person","class_conf":0.93, "embeddings":["emb://v3/9f2c..."] }

// fused / global track
{ "schema":"gtrack/1.0","global_id":"G-2026-09-17-00412",
  "members":[{"camera":"CAM-014","track_id":"...","t_start":"...","t_end":"..."}],
  "confidence":0.71,"association_evidence":["reid:0.82","spatiotemporal:0.65",
  "rf:mac-assoc:0.40"], "path":[{"t":"...","zone":"perimeter_north"}] }

// event / alarm
{ "schema":"event/2.0","event_id":"...","type":"perimeter_breach",
  "priority":1,"t_capture":"...","t_raised":"...",
  "actors":["G-2026-09-17-00412"],"zone":"Z-04","cameras":["CAM-014","CAM-015"],
  "evidence":{"clip":"s3://.../CAM-014_21-13-50_21-14-30.mp4",
              "thumb":"s3://...","recording_ref":"xprotect://...","hash":"sha256:..."},
  "suppressed_by":null,"rule":"rule-perimeter-v7",
  "explanation":"2 sensors agree: video track + fence zone 4" }
```

Design rules that repeatedly prove their worth **[lore]**:

1. **Version every schema and never reuse a field name with new semantics.**
2. **Both timestamps, always** (§1.8).
3. **Ground coordinates, not just pixels.** A detection that cannot be placed on
   the site plan cannot be fused, mapped, or geo-fenced.
4. **Embeddings by reference, not by value**, on the event bus — a 512-float
   vector per detection per frame will destroy your broker.
5. **`suppressed_by` is mandatory.** `R05 §4.5` is emphatic: "*log the suppressed
   events*… 'the fence alarmed but we filtered it' is a career-ending sentence at
   an inquiry."
6. **Carry the model version on every record** so a post-incident review can say
   which model produced which output.

### 5.3 The API surface

* **OpenAPI 3.x REST** for configuration, health, query and retrieval: cameras,
  zones, rules, models, alarms (list/ack/close), clips, search.
* **gRPC** for high-rate internal streams (frames, embeddings) — the same choice
  Milestone made with Direct Streaming.
* **Webhooks + MQTT** for outbound notification to third-party systems.
* **CAP (Common Alerting Protocol)** for public-safety/mass-notification
  interfaces. **[VERIFY — CAP profile details not sourced this session.]**

### 5.4 Time-series and metrics

A TSDB (Prometheus + long-term store, or InfluxDB/Timescale) holds: per-camera
delivered fps, bitrate, decode errors, inference latency p50/p95/p99, detections
per minute, alarms per hour, ack times, GPU utilisation/temperature, disk
headroom. This is simultaneously the ops dashboard (§8) and the drift monitor
(§4.7) and the acceptance-evidence recorder (§9.4). Build it once.

### 5.5 Vector databases and search

The pattern established by both Nx's "*special object database*"
([Nx metadata SDK](https://support.networkoptix.com/hc/en-us/articles/202856206-C-SDK))
and the VSS blueprint's "*natural language search across archives using video
embeddings*" ([VSS](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization)):

* **pgvector** when the metadata already lives in Postgres and the corpus is
  ≤10⁷ vectors — one fewer system to operate, transactional consistency with the
  detection records, and good enough with HNSW.
* **Milvus / Qdrant** at 10⁸+ vectors or when you need sharding, quantisation and
  filtered ANN at scale.
* Practical schema: one embedding per *track* (a pooled/best-frame
  representative), not per detection — 100× fewer vectors and better retrieval
  quality, since a single blurred frame is a bad query key.
  **[estimate/lore]**
* **Retrieval must be filterable before it is semantic**: time window, camera,
  zone, class. A pure ANN search over a month of a 200-camera site returns
  plausible nonsense; a filtered search over 20 minutes and 4 cameras returns
  the person.

### 5.6 Storage tiers and the retention asymmetry

```
hot      NVMe          0–7 days    video for live review + full metadata
warm     HDD/RAID-6    7–31 days   video at reduced fps (groomed) + metadata
cold     object store  1–12 months clips attached to events only + metadata
forever  RDBMS/parquet years       events, audit log, counts, statistics (no pixels)
```

**Metadata retention should exceed video retention by an order of magnitude**,
because it is ~10⁻⁴ of the size and answers most retrospective questions
("how many people entered gate 3 at night last quarter?"). This must be an
explicit, documented decision, since in a personal-data regime *metadata about
identified individuals is still personal data* — so the long-retention tier
should be **aggregated or pseudonymised** rather than a durable per-person
dossier (§7.5). **[lore]**

---

## 6. Fusion, C2 and PSIM — where the picture is consumed

### 6.1 Architecture of the fusion node

```
   per-camera tracks ─┐
   radar tracks ──────┤
   fence zones ───────┤   ┌──────────────────────────────────────────┐
   access events ─────┼──▶│ 1. TIME NORMALISE (buffer 0.5–2 s,        │
   RF/BLE sightings ──┤   │    reorder on t_capture)                  │
   audio events ──────┘   │ 2. SPATIAL REGISTER (homography/geo)      │
                          │ 3. ASSOCIATE (gating → cost matrix →      │
                          │    Hungarian/hierarchical clustering;     │
                          │    ReID + spatio-temporal + modality)     │
                          │ 4. TRACK GRAPH maintain (split/merge,     │
                          │    global-ID lifecycle, re-entry)         │
                          │ 5. CORROBORATE & SCORE (confidence        │
                          │    accumulation, escalation ladder)       │
                          │ 6. RULES / GEO-FENCE evaluate             │
                          │ 7. EMIT alarm + evidence + explanation    │
                          └──────────────────────────────────────────┘
```

Steps 3–4 are NVIDIA's MTMC recipe restated ("*hierarchical clustering … refines
these clusters through iterative reassignment using the Hungarian matching
algorithm*", [NVIDIA](https://www.nvidia.com/en-us/ai-data-science/ai-workflows/multi-camera-tracking/));
step 5 is `R05 §4.5`'s "*confidence accumulation with modality-aware weighting and
an escalation ladder*" instead of a hard AND-gate; step 2 is what Genetec's RSA
zones do in product form ([RSA plugin guide](https://techdocs.genetec.com/r/en-US/GenetecTM-Restricted-Security-Area-Surveillance-Plugin-Guide-5.1/Creating-RSA-zones-in-Security-Center)).

**The cross-camera track graph** is the data structure to get right: nodes are
per-camera tracklets, edges are association hypotheses with scores and evidence
types, and a connected component with a resolved global ID is a "person-journey".
Keep the *graph*, not just the winning assignment, because (a) association is
revisable when new evidence arrives, (b) operators need to see *why* two tracks
were joined, and (c) an inquiry will ask. Emitting only the collapsed answer is
the most common irreversible design mistake in MTMC products. **[lore]**

### 6.2 Rules, geo-fencing and the escalation ladder

```
 L0 ACTIVITY   single-sensor detection, logged, no operator interruption
 L1 EVENT      rule satisfied (zone entry, loiter > 90 s, direction)
 L2 ALARM      corroborated (2+ modalities, or VLM verification, or persistence)
 L3 CRITICAL   pattern-level (multiple simultaneous, or approach to asset)
 suppressors:  weather channel, maintenance window, all-zones-simultaneous,
               known-vehicle/known-badge, camera-in-tamper state
```

Rule primitives that cover ~90 % of real requirements **[estimate]**: zone
enter/exit/dwell, line-cross with direction, speed thresholds, count thresholds,
group formation, object left/removed, tailgating (access + video), wrong-way,
crowd density, camera-tamper, and "absence" rules (guard did not patrol). Each
rule needs: schedule (time-of-day/day-of-week), zone, class filter, confidence
floor, persistence (M-of-N frames or seconds), cooldown, and a *priority* that
maps to the operator's queue.

### 6.3 Operator UX — the layer that decides programme survival

`R05 §4.1`: "*the number of programmes killed by a bad L5 exceeds the number
killed by a bad L1 by a wide margin*." The patterns that work **[lore]**:

* **A map-based common operational picture** (site plan / geo map) with live
  tracks, camera FOV cones, zones and sensor health — not a wall of 64 tiles.
  Humans cannot monitor 64 tiles; this is not a UI opinion, it is the entire
  reason analytics exists.
* **An alarm queue with exactly one next action.** Priority-ordered, with a
  10-second video pre-roll autoplaying, the map context, and three buttons:
  *escalate*, *dispatch*, *nuisance (reason)*. The nuisance reason is the
  training label (§4.7).
* **Pre-roll is non-negotiable.** An alarm that opens at the moment of detection
  shows an operator a person already inside the fence, with no way to judge.
  10 s before and 20 s after.
* **Explanation, not score.** "Video track + fence zone 4 agreed within 2 s" beats
  "confidence 0.71".
* **SOP workflows**: the system should present the customer's written procedure
  as a checklist bound to the alarm type, capture each step's completion, and
  produce an incident record. This is what PSIM sells.
* **Audit everything an operator sees and does**, including PTZ movements and
  searches — both for inquiry and for insider-threat detection.
* **Mobile push** for guard-force dispatch, with the clip and the map pin; never
  as the only channel.

### 6.4 The PSIM/C2 vendor landscape

* **Genetec Mission Control** — SOP/decision-support layer over Security Center.
  **[VERIFY — capability specifics not sourced this session; `R05 §4.7` flags the
  same gap.]**
* **Vidsys, CNL IPSecurityCenter** — classic independent PSIM. **[VERIFY]**
* **Anduril Lattice** — the modern C2 articulation, quoted at length in
  `R05 §4.7`: an "*open architecture backbone that connects sensors, computing,
  AI-enabled command-and-control, and effectors into a single mission-ready
  capability*", with "*Lattice Mesh … a decentralized data distribution layer*"
  and "*Lattice C2 … the command-and-control layer that translates aggregated
  sensor data into decision-support outputs for human operators*"
  ([Anduril Command & Control](https://www.anduril.com/lattice/command-and-control)).
  The border deployment numbers are the scale reference: Anduril "*finalized its
  300th deployment, covering 30 percent of the U.S. southern land border*", CBP
  "*operates more than 350 Standard Range Sentry systems*", and a "*$363 million
  contract for more than 200 Extended Range Sentry Towers (XRST)*" followed, with
  the 80-foot XRST clearing "*CBP acceptance testing in November 2024*"
  ([ASDNews](https://www.asdnews.com/news/defense/2024/09/27/anduril-deploys-300th-autonomous-surveillance-tower-ast-advancing-capability-border-security),
  [ExecutiveBiz](https://www.executivebiz.com/articles/cbp-anduril-extended-range-sentry-towers-363m),
  [FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/),
  [EFF mapping project](https://www.eff.org/deeplinks/2023/03/cbp-expanding-its-surveillance-tower-program-us-mexico-border-and-were-mapping-it)).
* **Palantir** — the government data-integration layer above all of this.
  **[VERIFY]**

**The lesson to take from Lattice, stripped of the marketing:** the product is
the *mesh plus the decision layer*, and the sensors are replaceable. An analytics
company that positions itself as a sensor becomes a commodity; one that owns the
track graph and the operator decision surface owns the account.

### 6.5 Defence interfaces

| Standard | What it is | Relevance |
|---|---|---|
| **STANAG 4609** | NATO motion-imagery standard — "*the official format for motion imagery … exchange within the NATO nations*", specifying "*how video and KLV (Key-Length-Value) metadata are encoded, synchronized, and transmitted, covering supported video codecs, frame rates, container format (typically MPEG-2 Transport Stream)*" ([ImpleoTV](https://impleotv.com/2025/03/11/stanag-4609-isr-video/), via `R05 §4.6`) | If the customer is defence, your video output may need to be MPEG-2 TS + KLV, not RTSP + JSON. Conformance tooling exists ([Fraunhofer IOSB validator](https://www.iosb.fraunhofer.de/en/projects-and-products/stanag-4609-validator.html)). |
| **STANAG 4676 / AEDP-12 (NITS)** | NATO ISR Tracking Standard. It "*aims to promote interoperability for the production, exchange, and exploitation of tracking data among NATO ISR systems*" and "*defines a standard for the data content and format for the products of tracking systems and a recommended set of procedures for identifying and managing those tracks*"; tracks "*are formatted as XML data*" ([GlobalSpec AEDP-12](https://standards.globalspec.com/std/14507144/aedp-12), [GlobalSpec STANAG 4676](https://standards.globalspec.com/std/14474804/stanag-4676), [IET/IEEE paper](https://ieeexplore.ieee.org/document/4567745/), [Elsis NATO AGS MGECS](https://www.elsis.lt/en/nato-ags-mgecs-df-sw-stanag-4676/)) — closing the **[VERIFY]** left open in `R05 §4.6`. Edition A reportedly published May 2014 **[VERIFY — publication date from search summary only]**. | This is the wire format for our *fused track* output in a NATO context. Our `gtrack` schema (§5.2) should be designed as a lossless superset so a STANAG 4676 serialiser is a mapping, not a redesign. |
| **STANAG 4559 (CSD)** | NATO Standard ISR Library Interface / Coalition Shared Data — the archive/query interface. **[VERIFY — not sourced this session.]** | Where your clips and tracks would be catalogued for coalition discovery. |
| **MISB / KLV** | The US body behind the KLV metadata sets STANAG 4609 profiles (`R05 §4.6`). **[VERIFY]** | UAS Datalink Local Set fields (platform position, sensor pointing) are the geo-referencing model to mimic for towers/PTZ. |
| **NIEM** | US justice/public-safety information-exchange model. **[VERIFY]** | Law-enforcement integrations. |
| **OGC SensorThings API** | OGC standard for IoT sensor observations (Things/Datastreams/Observations). **[VERIFY — search budget exhausted before this query landed.]** | The clean civil-side alternative to bespoke REST for sensor health/observations; relevant for smart-city customers. |
| **TAK / ATAK + Cursor-on-Target** | Tactical situational-awareness clients and the CoT XML event schema. **[VERIFY — not sourced this session.]** | The cheapest possible route to "our detections appear on the guard force's tablet map"; CoT is a tiny schema and a very common integration ask. |
| **Link 16** | Tactical datalink. Out of scope, as the brief notes. | — |
| **SOSA / MOSA** | "*SOSA has emerged as the prevalent MOSA standard*", developing "*open architecture for Communications (Comms), Electro-Optical/Infra-Red (EO/IR), Electronic Warfare (EW), Radar, and Signals Intelligence (SIGINT) systems*", "*based on OpenVPX*"; the DoD mandated MOSA by tri-service memo of 7 January 2019, and "*Title 10 U.S.C. 4401(b) requires the DOD to use a standardized, modular system architecture*" ([Open Group C212 SOSA technical standard](https://publications.opengroup.org/c212), [Elma](https://www.elma.com/en/capabilities/sosa), [Open Group tri-service statement](https://www.opengroup.org/The-Open-Group-SOSA-and-FACE-Consortia-Applaud-New-Tri-Services-Directive-Memorandum-that-Furthers-the-DOD's-Modular-Open-Systems-Commitment), [NAVAIR MOSA](https://www.navair.navy.mil/MOSA)) | SOSA is *hardware*-centric (OpenVPX cards), so it constrains a tower/vehicle sensor payload rather than our software. But MOSA as *policy* is the reason a defence customer will demand documented open interfaces — which is an argument for ONVIF Profile M + STANAG 4676 rather than a proprietary API. |
| **UK MOD Pyramid / LOSA** | Open-architecture initiatives for ISTAR and land systems. **[VERIFY — search budget exhausted before this query landed; do not cite in a bid without reading the current MOD publications.]** | The UK equivalent of the MOSA argument. |

---

## 7. Security and compliance

### 7.1 NCSC Cyber Assessment Framework (UK CNI)

The CAF is the assessment your CNI customer will be measured against, so it is
the assessment your product is measured against by proxy. Structure: "*four
objectives: managing security risk, protecting against cyber attack, detecting
cyber security events and minimising the impacts of cyber incidents*", comprising
"*'objectives', 'principles', 'contributing outcomes' and 'indicators of good
practice' (IGPs)*" — "*4 objectives, 14 principles, and 39 contributing
outcomes*" — and applied by "*operators of essential services under the Network
and Information Systems regulations as well as more widely across the private
sector, including Critical National Infrastructure (CNI) sectors*". Critically,
"*it has an 'outcome-based' assessment rather than focusing on controls*", and it
defines cyber resilience as "*an organisation's ability to maintain the correct
operation of its essential functions, even in the presence of adverse cyber
events*"
([NCSC CAF collection](https://www.ncsc.gov.uk/collection/cyber-assessment-framework),
[UK Government Security introduction to the CAF](https://www.security.gov.uk/policy-and-guidance/introduction-to-the-cyber-assessment-framework-caf/),
[techUK guidance](https://www.techuk.org/resource/understanding-and-implementing-the-cyber-assessment-framework-caf.html),
[Bridewell overview](https://www.bridewell.com/ncsc-cyber-assessment-framework)) **[secondary — ncsc.gov.uk blocked by proxy]**.
CAF 4.0 is the current generation **[VERIFY — version currency from a vendor blog
only: [enactia](https://enactia.com/ncsc-caf-cyber-assessment-framework-automation-guide/), [Shift Key Cyber](https://shiftkeycyber.com/news/did-you-know-ncscs-cyber-assessment-framework-caf-has-been-updated/)]**.

**What "outcome-based" means for us in practice:** you cannot satisfy it with a
feature list. You must be able to demonstrate, with evidence, that (a) you know
what assets exist (camera/device inventory with firmware versions), (b) you
control access to them (§7.3), (c) you can detect a compromise of them
(§8.3 — a camera that starts scanning the network), and (d) you can keep the
essential function running while it is happening (degraded modes, §8.1).
Objective C ("detecting cyber security events") is the one where a surveillance
product is unusually exposed — the cameras *are* the poorly-monitored IoT estate
the objective is about.

### 7.2 MOD Secure by Design, JSP 440 / JSP 604

"*Secure by Design is mandated in JSP 440 Leaflet 5C, and all capabilities and
services that handle Defence data must follow Secure by Design, including
supplier-delivered capabilities*"; "*JSP 440 is the primary security manual
governing protective security within the MOD*", while "*JSP 604 addresses IT
systems security, specifying the requirements for network security, encryption
standards, and secure communications*"
([Logiq, MOD Secure by Design guide](https://www.logiq.co.uk/insights/mod-secure-by-design-guide/),
[Defended Solutions](https://www.defendedsolutions.com/defended-solutions-blog/compliant-data-protection-mod-nhs),
[Digital MOD technology principles: "make your technical solution secure"](https://www.digital.mod.uk/policy-rules-standards-and-guidance/service-manual/architecture/defence-technology-principles/make-your-technical-solution-secure),
[MOD digital standards](https://defencedigital.github.io/mod-standards-digital-rules/)) **[secondary]**.

Operationally, Secure by Design replaces one-off accreditation with continuous,
evidence-based risk management through the life of the capability. For a product
company the deliverables are concrete: a documented threat model, a security
architecture document, a risk register maintained (not written once), an
assurance case, and evidence of secure development practice (SAST/DAST, dependency
management, SBOM, patch SLAs). Build the artefacts once, as part of the product,
or pay a consultancy to regenerate them per bid forever. **[lore]**
**[VERIFY — do not quote JSP leaflet numbers or clause text in a bid without
reading the current JSPs; the above is a secondary summary.]**

### 7.3 Zero trust, identities and access control

```
 identity:   operators & admins in the customer IdP (SAML/OIDC), MFA,
             role-based: viewer / operator / supervisor / investigator / admin
 machine:    every service and every edge node gets an mTLS identity
             (short-lived certs, per-node, revocable) — not a shared API key
 device:     cameras authenticated (802.1X where supported; MAC ACL where not),
             credentials unique per device, rotated, stored in a secret manager
 data:       authZ at the object level — this operator may view these cameras
             during these hours, and may export only with a case reference
 network:    segmentation (§2.1) as defence-in-depth, never as the control
```

Two surveillance-specific points **[lore]**:

* **Privileged actions are the ones to instrument**, not logins: export, PTZ
  control, retention change, rule change, model change, user creation, audit-log
  access. Each needs a reason field and a tamper-evident record.
* **Four-eyes on identity-linked functions.** If the product ever links a track to
  a named individual (badge, ANPR, RF, face), that join should require a second
  authorisation and generate a retained record. This is a design choice that
  converts an ethical objection into an auditable control, and it will be asked
  for at DPIA stage.

### 7.4 Data at rest and in transit

* **In transit**: TLS 1.3 everywhere north of the camera; RTSPS/SRTP south of it
  where cameras support it, VLAN isolation where they do not (§1.2). mTLS between
  microservices. Signed messages on the event bus for anything that can trigger
  a physical response.
* **At rest**: full-disk encryption on edge boxes (they are physically stealable —
  a tower cabinet in a field is not a datacentre), database encryption, encrypted
  object storage with per-tenant keys, and key custody documented (an escrowed
  key the customer holds beats a key only we hold, for both trust and continuity).
* **Backups** of configuration and of the audit log, tested by restore, stored
  separately from the media.

### 7.5 Data protection, DPIA, retention

For any UK/EU deployment the analytics product is a high-risk processing activity
and the customer needs a **DPIA**; the vendor's job is to make the DPIA easy to
write by shipping the facts: what is captured, what is inferred, where it is
stored, for how long, who can see it, what the accuracy characteristics are
(including *differential* accuracy across demographic groups), what the human
review process is, and how a subject-access or erasure request is served.

Architecture consequences:

* **Purpose limitation in the data model.** Attributes that are not needed should
  not be computed; if the customer's purpose is perimeter intrusion, a
  demographic attribute classifier has no business in the pipeline.
* **Pseudonymisation by default.** Global track IDs should be random, scoped to a
  site and a time window, and *not* durable identity keys unless the purpose
  demands it.
* **Configurable retention per data class**, enforced by an automated deletion
  job with a report — "we deleted it" must be evidenceable.
* **Subject access** requires the ability to find footage of an individual, which
  in turn requires search — which the product has. Say so, and design the
  redaction (blurring of third parties in exports) that inevitably follows.
* **Accuracy claims are regulatory statements.** Whatever Pd/FAR number goes in
  the brochure will be quoted back in a complaint.

**[VERIFY — no first-hand ICO/GDPR source was retrievable this session (egress
blocked). Do not cite the UK Surveillance Camera Code of Practice, ICO video
surveillance guidance, or specific GDPR articles without reading them.]**

### 7.6 Adversarial robustness and red-teaming

A deployed analytic is a target. The threat model has four layers **[lore, with
literature pointers marked VERIFY]**:

1. **Physical evasion** — hoods, masks, umbrellas, crawling, hugging walls,
   moving with vehicles, exploiting known blind spots, timing gaps in PTZ patrol.
   SurvSim models precisely this already: `adversarial: camera_awareness(0-1),
   face_hiding(0-1), avoid_zones, timing_gaps_cameras`
   (`02_ARCHITECTURE.md §1.2`). **This is a differentiator, not a detail** — no
   public dataset contains systematically camera-aware adversaries.
2. **Digital-physical (patch) attacks** — printed adversarial patterns that
   suppress person detection. **[VERIFY — the canonical reference (Thys et al.,
   "Fooling automated surveillance cameras", 2019) was not retrieved this session.]**
3. **Sensor attacks** — laser/IR glare, strobe, lens spray, tamper. Profile T's
   tamper events plus an input-drift monitor (§4.7) is the cheap defence.
4. **System attacks** — camera RCE (§1.9), event-bus injection, model-file
   substitution, and *alarm flooding* to exhaust the operator (the cheapest,
   most effective attack on any alerting system, and the one nobody tests).

Red-team programme minimum: an annual physical penetration exercise with the
guard force, a network penetration test including the camera VLAN, an alarm-flood
resilience test, and a documented adversarial-evasion evaluation using simulated
scenarios. Report Pd against *each* evasion class separately; an aggregate Pd
hides the only numbers an adversary cares about.

### 7.7 Supply chain and SBOM

* **SBOM (CycloneDX or SPDX) per release**, generated in CI, published to the
  customer, diffable release-to-release, and used to answer "are you affected by
  CVE-X?" within hours rather than weeks. **[VERIFY — specific US EO / UK policy
  mandates not sourced this session.]**
* **Signed artefacts** (images, models, installers) with verification at install
  and at container start; provenance attestation in the build.
* **Pinned, mirrored dependencies** so an air-gapped site can be rebuilt, and so
  a compromised upstream package cannot be pulled silently.
* **Third-party hardware attestation** per SKU for NDAA/Covered-List compliance
  (§1.9), tracked as a BoM field, not a brand assumption — OEM relabelling is the
  trap.
* **Model provenance** is supply chain too: where did the pretrained weights come
  from, under what licence, trained on what data, and can you ship them to a
  defence customer?

---

## 8. Reliability and operations

### 8.1 HA, failover and degraded modes

```
tier              failure               design response
────────────────  ────────────────────  ──────────────────────────────────────
camera            dies / tampered       health alarm within 60 s; neighbour
                                        camera covers overlap; recorded gap noted
PoE switch        dies                  UPS; dual-homed core; alarm names the
                                        blast radius ("12 cameras, zone 4")
recording server  dies                  failover recording server (N+1) takes
                                        over camera group; cameras buffer to edge
analytics node    dies                  camera→node assignment rebalanced by the
                                        orchestrator; degraded: fewer fps, not
                                        fewer cameras
fusion node       dies                  active/standby with state rebuilt from
                                        the Kafka log (this is why replay matters)
event/alarm DB    dies                  alarms queue on the broker; never drop
network to NOC    dies                  edge keeps detecting, alarms queue
                                        locally, local siren/annunciator path
model             bad update            atomic rollback to vN, shadow-first policy
```

**The rule that separates products from projects:** every degraded mode must be
*visible and named* on the operator's screen. A system that quietly loses 12
cameras is worse than one that stops, because the operator believes they are
covered. State the coverage, always. **[lore]**

### 8.2 Health monitoring specific to this domain

Beyond generic infrastructure metrics, the domain-specific health signals:

* **Camera down / unreachable / flapping** (ICMP + RTSP session state + delivered
  fps, all three — a camera can ping and stream nothing).
* **Video-loss and black-frame detection** (mean luminance ≈ 0 or ≈ 255).
* **Tamper**: ONVIF Profile T tamper events, plus our own scene-change detector
  (sudden global shift = repositioned; persistent blur = spray/web; frozen frame =
  spoofed stream).
* **Focus/defocus drift**, **IR illuminator failure** (night-time luminance
  collapse), **lens contamination** (progressive high-frequency energy loss).
* **Time drift per device** against the reference clock, alarmed above a
  threshold (this single metric prevents a whole class of fusion bugs).
* **Storage runway** in days-remaining, not percent-full.
* **Recording gaps** report per camera per day — the thing an auditor asks for.
* **Analytics liveness**: detections-per-hour per camera compared to its own
  historical baseline. A camera whose detection rate goes to zero at a busy time
  is broken even though every infrastructure metric is green. **This is the single
  most valuable alert in the system and almost nobody implements it.** **[lore]**

### 8.3 Observability stack

Prometheus + Grafana + Alertmanager for metrics; Loki/ELK for logs; OpenTelemetry
traces across the ingest→inference→fusion→alarm path so a latency regression can
be attributed to a stage. `mediamtx` conveniently exposes
"*Prometheus-compatible metrics*" ([mediamtx](https://github.com/bluenviron/mediamtx)),
and Triton exposes "*Metrics indicating GPU utilization, server throughput, server
latency*" ([Triton](https://github.com/triton-inference-server/server)) — so the
two most awkward components are already instrumented.

Dashboards that customers actually use **[estimate]**: (1) coverage — cameras
healthy / degraded / down on the site map; (2) alarm funnel — activities → events
→ alarms → operator-confirmed, per day, per camera; (3) nuisance leaderboard —
which cameras generate the most nuisance alarms (this is a *maintenance* work
queue); (4) latency — detection-to-alarm p95; (5) storage and retention
compliance.

### 8.4 SLAs and incident response

Contractable numbers **[estimate — these are the shapes, not committed values]**:

| Metric | Typical target |
|---|---|
| Analytics service availability | 99.5 % monthly (edge), 99.9 % (on-prem clustered) |
| Detection-to-alarm latency | p95 < 3 s (same-site), < 10 s (over backhaul) |
| Camera-down notification | < 60 s |
| Nuisance alarms | < 1 per camera per day, measured over 30 days |
| Pd on the acceptance scenario set | ≥ 95 % for defined threat classes at defined ranges |
| P1 support response | 1 h response, 4 h workaround, 5 business days fix |
| Security patch for critical CVE | assessed in 48 h, patched in 14 days |

Incident response needs a runbook per class: camera compromise (isolate VLAN,
preserve, re-image, rotate credentials), model misbehaviour (fall back to vN,
switch to motion-only mode, notify), alarm flood (rate-limit per camera, escalate
to supervisor mode), storage exhaustion (grooming acceleration, alert),
data-breach (notification clock starts — know who starts it).

---

## 9. Evaluation and acceptance in the field

### 9.1 Site survey and camera placement — DORI

DORI/IEC 62676-4 is the language of camera placement, and getting it into the
contract protects everyone. "*DORI, standing for Detection, Observation,
Recognition, and Identification, is a reference standard tailored for cameras,
based on the IEC EN62676-4 international standard, to assess their visual range*",
defining "*Detection (25PPM), Observation (62PPM), Recognition (125PPM), and
Identification (250PPM)*", where PPM is "*the count of pixels within a one-meter
width at a designated distance from the camera*". Semantically: "*Detection
allows for reliable and easy determination of whether a person or vehicle is
present*"; observation "*gives characteristic details of an individual, such as
distinctive clothing*"; "*125 PPM allows a familiar face to be matched; 250 PPM
enables forensic identification of a stranger*"
([Infiniti Electro-Optics DORI white paper](https://www.infinitioptics.com/whitepapers/dori-detection-observation-recognition-identification),
[TP-Link](https://www.tp-link.com/us/support/faq/4098/),
[Axis pixel-density white paper (PDF)](https://www.axis.com/dam/public/b2/d9/29/pixel-density-en-US-403691.pdf),
[Axis pixel density based on IEC 62676-4:2014](https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014)).

**Important currency note:** "*the 2025 revision of IEC 62676-4 expands the older
model into a broader visual-performance framework with seven operational levels:
overview, outline, discern, perceive, characterize, validate, and scrutinize*"
([Backstreet Surveillance](https://www.backstreet-surveillance.com/cctv-industry-experts/dori-cctv.html),
[JVSG on IEC/EN 62676-4:2025 OODPCVS](https://www.jvsg.com/iec-62676-4-oodpcvs/),
[CCTVplanner EN 62676-4 calculator](https://cctvplanner.io/en-62676-4-calculator)) **[secondary — verify against the purchased standard before contractual use]**.
Anyone writing an operational requirement in 2026 should know both vocabularies.

**The analytics-specific extension nobody standardises, and we should:** a
detector has its own minimum pixel height (commonly ~40–60 px for a reliable
person detection at usable confidence, lower for large models on clean video)
**[estimate]**, plus a minimum *duration in view*, plus a maximum acceptable
occlusion and a maximum tolerable motion blur. Publish an **"AORI" companion
table for the product** — "for detection at Pd ≥ 0.95, the target must be ≥ X px
tall for ≥ Y s at ≤ Z° depression angle" — and derive camera placement from that,
not from DORI alone. This is exactly the quantity SurvSim can measure directly
(it exports `pixel-height`, `occlusion ratio`, `motion blur magnitude` per object
per camera, `02_ARCHITECTURE.md §1.4`), and no competitor can measure it without
a synthetic ground truth. **This is, I think, the highest-value single output the
simulator can produce for the business.**

Other site-survey outputs: depression angles (too steep and everyone is a hat;
too shallow and occlusion is total), sun path and backlight at dawn/dusk,
IR reflection from nearby surfaces, vegetation and its seasonal growth, wind
exposure for pole sway (a swaying camera destroys background models), existing
lighting and its flicker frequency, cable routes, PoE budget, and *blind-spot
mapping with camera-overlap percentages* — the last being a direct input to
cross-camera tracking feasibility.

### 9.2 Commissioning

A defensible commissioning pack contains, per camera: as-built position and
orientation, lens/FOV, the DORI/AORI distances marked on the site plan,
a calibration (intrinsics + ground-plane homography), a reference image at day
and night, the delivered fps/bitrate measured, time-sync verified, tamper event
verified by physically covering the lens, recording verified end-to-end including
retrieval, and the analytics configuration (zones, rules) screenshotted.
Zones drawn without a calibrated ground plane are the leading cause of
"the analytics doesn't work" tickets. **[lore]**

### 9.3 Acceptance testing: the i-LIDS model

The UK's i-LIDS regime is the template for how a *customer* should test an
analytic, and knowing it is a credibility marker. HOSDB "*in partnership with the
Security Service produced a video test library, i-LIDS*", focused on four
scenarios — "*Abandoned Baggage Detection, Parked Vehicle Detection, Doorway
Surveillance, and Sterile Zone Monitoring*" — where "*each dataset consists of two
or three camera views referred to as stages, and is further segmented into shorter
video clips of 30 to 60 minutes*", and the datasets deliberately include
"*animals running across the scene, various body movements, camera faults and
shadows*"
([i-LIDS brochure, gov.uk](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf),
[IEEE: "Imagery Library for Intelligent Detection Systems (i-LIDS); A Standard for Testing Video Based Detection Systems"](https://ieeexplore.ieee.org/document/4105319/)).
Approval is **graded**: VCAsys, for example, "*passed the test and gained approval
as a secondary detection system in an operational alert role for sterile zone
monitoring*" ([IFSEC](https://www.ifsecglobal.com/uncategorized/vcasys-passes-i-lids-analytics-test/),
see also [Professional Security: "How useful is i-LIDS?"](https://www.professionalsecurity.co.uk/news/interviews/how-useful-is-i-lids/)).

Three lessons that transfer directly **[lore]**:

1. **Primary vs secondary approval is the commercial dividing line.** "Primary"
   means the analytic may be the *only* thing watching. "Secondary" means a human
   is still watching and the analytic is an aid. The price, the liability and the
   integration are different in each case, and a vendor who is vague about which
   they are selling is a vendor about to be sued.
2. **The test set contains the nuisances, not the events.** Animals, shadows,
   camera faults, weather. Our regression suite must be majority-nuisance.
3. **Long clips, continuous scoring.** Detection is scored with false-alarm rate
   over hours of nothing happening — which is the only regime that resembles
   operations.

The US counterpart to know: NIST **ActEV** / the sequestered-data leaderboard
around IARPA DIVA ([ActEV SDL](https://actev.nist.gov/sdl20)), and TRECVID's
activity-detection tasks ([TRECVID 2022 overview](https://arxiv.org/pdf/2306.13118)).

### 9.4 Field measurement: Pd, NAR, and the measurement period

The two numbers, defined carefully **[estimate of standard practice]**:

* **Pd (probability of detection)** — per threat class, per range band, per
  lighting condition, measured against *staged* intrusions (because real ones are
  too rare), with a minimum sample of ~30 attempts per cell for a usable
  confidence interval. Staged attempts must include the evasion classes of §7.6,
  or Pd means nothing.
* **NAR (nuisance alarm rate)** — alarms per camera per day with no genuine cause,
  measured over ≥ 30 continuous days *including* bad weather. Separate *nuisance*
  (real physical cause, not a threat: animal, vegetation, rain) from *false*
  (no physical cause: model error). They have different fixes — one is camera
  placement and masking, the other is the model.
* **Latency** — detection to operator-visible alarm, p50/p95.
* **Operator load index** — alarms per operator per hour and time-to-acknowledge
  distribution. Above roughly 6–10 alarms/hour sustained, operators begin
  bulk-acknowledging and the system's effective Pd collapses to zero regardless
  of the model. **[lore — this is the number that decides whether the deployment
  succeeds, and it is almost never in the contract.]**

### 9.5 Shadow mode and phased handover

```
 week 0–2   INSTALL + COMMISSION (§9.2), analytics logging only, no alarms
 week 2–6   SHADOW: analytics alarms visible to supervisors only; daily triage
            of every alarm; tuning of zones/masks/thresholds; NAR trend tracked
 week 6–8   PILOT: alarms to operators on a subset of zones; staged-intrusion
            Pd campaign; operator training completed and recorded
 week 8–12  PROVISIONAL ACCEPTANCE: full alarm delivery, SLA measurement period
            begins; weekly review meeting with the nuisance leaderboard
 week 12+   ACCEPTANCE on sustained NAR and Pd; support handover; quarterly review
```

This schedule is also the commercial mechanism that protects the vendor: the
tuning period is contractually acknowledged, the NAR baseline is measured rather
than promised, and the customer's own operators have been trained before the
alarms arrive.

### 9.6 Operator training

Content that matters: what the system can and cannot see (show them the blind-spot
map and the AORI table — trust comes from honest limits), how to use the alarm
queue, how to classify nuisance correctly (because it is the training signal),
the escalation SOP, how to export evidence, and what to do when the system is
degraded. Refresh at every model change. Measure it — an unacknowledged-alarm
report per operator is a training diagnostic, not a disciplinary tool.

---

## 10. Reference architectures worth citing in a bid

| # | Reference | What to take from it | Citation |
|---|---|---|---|
| R-1 | **NVIDIA Metropolis MTMC / RTLS microservices** | The canonical decomposition: per-camera perception → behaviours (trajectories + embeddings) → clustering → global IDs, Kafka-driven, batch *or* stream, Kubernetes+Helm packaged. Also the honest admission that this is a *clustering* problem with iterative reassignment, not a solved tracking problem. | [workflow](https://www.nvidia.com/en-us/ai-data-science/ai-workflows/multi-camera-tracking/), [MTMC MS overview](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_MS_Overview.html), [MTMC toc](https://docs.nvidia.com/mms/text/Multi-Camera_Tracking_toc.html) |
| R-2 | **NVIDIA VSS blueprints (public-safety, smart-city, warehouse)** | The realtime-streaming / agentic split; VST as the VMS-or-VMS-adapter component; alert verification by VLM; embeddings→vector DB→NL search; MCP-based tool orchestration. Where the market is going in 2026–27. | [github](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization), [public-safety intro](https://docs.nvidia.com/vss/3.1.0/publicsafety-docs/Introduction.html), [deep dive](https://docs.nvidia.com/vss/3.1.0/publicsafety-docs/Blueprint-deep-dive.html), [smart-city deep dive](https://docs.nvidia.com/vss/3.0.0/smartcity-docs/latest/Blueprint-deep-dive.html), [3D Sparse4D](https://docs.nvidia.com/vss/3.1.0/warehouse-docs/3D-multi-camera-detection-and-tracking-Sparse4D.html) |
| R-3 | **DeepStream reference apps** | Pipeline-level patterns: runtime source add/delete, parallel models, IPC buffer sharing, multi-view 3D tracking as a "*distributed, real-time framework for camera networks*". | [github](https://github.com/NVIDIA-AI-IOT/deepstream_reference_apps), [DS perf docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html) |
| R-4 | **Milestone XProtect architecture + AI Bridge** | The VMS component model to integrate with (Management/Recording/Event/Log + SQL) and the container integration contract (Kafka-brokered, docker-compose or k8s, RTSP + gRPC Direct Streaming, results back as Events/Metadata/Video). | [server components](https://doc.milestonesys.com/2021r2/en-US/system/sad/sad_servercomponents.htm), [system architecture PDF](https://milestonedownload.blob.core.windows.net/files/XProtect%202019%20R1/Manuals%20and%20guides/Advanced%20VMS/Guides%20and%20documents/System%20architecture%20document/MilestoneXProtectVMSproducts_SystemArchitectureDocument_en-US.pdf), [AI Bridge containers](https://doc.milestonesys.com/AIB/Help/Latest/en-US/feature_flags/ff_aibridge/aibi_overview_containers.htm), [AI Bridge integrator manual](https://doc.milestonesys.com/AIB/PDF/v2_0/en-US/MilestoneAIBridge_IntegratorManual_en-US.pdf) |
| R-5 | **Genetec Security Center + RSA Surveillance** | The unified-platform model and, specifically, the sensor-fusion product requirement: one target seen by many sensors is *one* threat, tracked on a geographical map. | [RSA product page](https://www.genetec.com/products/unified-security/security-center/restricted-security-area), [brochure](https://resources.genetec.com/en-product-brochures/restricted-security-area-rsa-surveillance-in-security-center), [plugin guide](https://techdocs.genetec.com/r/en-US/GenetecTM-Restricted-Security-Area-Surveillance-Plugin-Guide-5.1/Creating-RSA-zones-in-Security-Center) |
| R-6 | **Network Optix Nx Meta plugin + object database** | The cleanest third-party analytics contract in the industry, including bounding boxes over live *and recorded* video from a searchable object DB; worked OpenVINO/OpenCV plugin examples. | [Server Plugin SDK](https://support.networkoptix.com/hc/en-us/articles/32766542038423-The-Server-Plugin-SDK-C), [nx_open_integrations](https://github.com/networkoptix/nx_open_integrations) |
| R-7 | **Anduril Lattice + CBP Sentry towers** | The distributed-tower-with-edge-autonomy pattern, and the mesh/C2 split. Also the deployment-scale reality (300+ towers, 30 % of a border) and the political risk profile (§13). | [Anduril C2](https://www.anduril.com/lattice/command-and-control), [Privacy International analysis](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example), [ASDNews 300th tower](https://www.asdnews.com/news/defense/2024/09/27/anduril-deploys-300th-autonomous-surveillance-tower-ast-advancing-capability-border-security) |
| R-8 | **IARPA DIVA + MEVA collection** | The evaluation-first architecture: "*a four-year program that began in September 2017 to develop activity detection capabilities … providing automated alerts, enabling a single operator to monitor a multi-camera network for user-defined threat activities*" ([IARPA DIVA](https://www.iarpa.gov/research-programs/diva)). MEVA is the *collection architecture* we should imitate: "*328 hours of video, collected over three weeks … annotated for the 37 activity types defined by the DIVA program*", "*over 150 consented actors … imaged from 28 indoor and outdoor cameras, as well as UAVs*", with "*GPS tracks, a 3D site model and KRTD camera models for outdoor cameras*" ([MEVA paper, arXiv 2012.00914](https://arxiv.org/pdf/2012.00914), [mevadata.org](https://mevadata.org/), [Kitware datasets tour](https://cdao.pages.jatic.net/public/program/Kitware_Computer_Vision_Datasets.pdf)). Note also DIVA's own use of synthesis: an "*Analysis-by-Synthesis framework which takes advantage of state-of-the-art advancements in graphical rendering engines (e.g., Unreal Engine)*" ([JHU CIRL](https://cirl.lcsr.jhu.edu/deep-intermodal-video-analytics-diva-project/)) — i.e. a government programme independently arrived at SurvSim's thesis. | as linked |
| R-9 | **Cisco Video Surveillance SRND / NETGEAR / ALAXALA network guides** | The network tier, VLANs, multicast, IGMP, QoS — old but structurally still correct. | [Cisco SRND](https://www.cisco.com/c/dam/en/us/td/docs/security/physical_security/video_surveillance/network/vsm/7_0/srnd/vsm_7_0_srnd.pdf), [NETGEAR](https://www.netgear.com/images/pdf/IP-Video-Surveillance_Networking-Solution-Guide.pdf), [ALAXALA](https://www.alaxala.com/en/techinfo/archive/guide/pdf/N11R050_MCN_Solution_Guide_V1R0_e.pdf) |
| R-10 | **AWS/Azure edge references** | k3s + Greengrass v2 co-deployment, Kinesis Video Streams edge, IoT Hub device twins, fleet governance via Arc/RHACM. The hybrid tier. | [AWS containers blog](https://aws.amazon.com/blogs/containers/collecting-data-from-edge-devices-using-kubernetes-and-aws-iot-greengrass-v2/), [aws-samples repo](https://github.com/aws-samples/aws-kubernetes-edge-greengrass), [KVS edge](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/gs-deploy-edge.html) |
| R-11 | **i-LIDS / ActEV** | The acceptance regime. | [i-LIDS brochure](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf), [ActEV SDL](https://actev.nist.gov/sdl20) |

---

## 11. How SurvSim plugs into all of this

This is the section that converts a research document into a roadmap. The claim:
**SurvSim's commercial value is not synthetic training data — it is being the
only way to run the *whole deployed system* under controlled, repeatable,
adversarial conditions.** Everything below is an addition to
`docs/02_ARCHITECTURE.md`, phrased as an interface.

### 11.1 The integration picture

```
┌────────────────────────── SurvSim (existing) ───────────────────────────┐
│ Director → UE5/Isaac/Mock backend → frames + GT + events                │
│ degradation pipeline (optics→sensor→motion→weather→codec→OSD)           │
└───────┬───────────────────────────┬─────────────────────────┬───────────┘
        │ frames/video              │ ground truth            │ sensor events
        ▼                           ▼                         ▼
┌───────────────┐          ┌─────────────────┐       ┌──────────────────┐
│ VIRTUAL CAMERA│          │ GT SERVICE      │       │ VIRTUAL SENSORS  │
│ PLANE         │          │ (scoring oracle)│       │ radar/fence/RF/  │
│ • mediamtx    │          │ • MOT/COCO/MEVA │       │ audio/access →   │
│   RTSP/RTSPS  │          │ • events.jsonl  │       │ MQTT + Modbus/   │
│ • WebRTC/WHEP │          │ • calib + graph │       │   dry-contact sim│
│ • ONVIF emu   │          └────────┬────────┘       └─────────┬────────┘
│   (S/T/G/M)   │                   │                          │
│ • Profile M   │                   │                          │
│   metadata inj│                   │                          │
└───────┬───────┘                   │                          │
        │ looks exactly like a site │                          │
        ▼                           ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           SYSTEM UNDER TEST (unmodified production stack)               │
│  VMS (XProtect / Nx / Genetec)  +  analytics containers  +  fusion      │
│  +  rules  +  alarm queue  +  operator UI  +  observability             │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ alarms, metadata, tracks, latencies
                              ▼
                  ┌───────────────────────────────┐
                  │ SCOREBOARD / REGRESSION GATE   │
                  │ Pd, NAR, latency, ID switches, │
                  │ operator-load index, diffs vs  │
                  │ previous build (§11.5)         │
                  └───────────────────────────────┘
```

### 11.2 RTSP re-streaming (already scoped — make it first-class)

`02_ARCHITECTURE.md §5` already lists "*RTSP re-stream (mediamtx) for 'live'
tests*". Concrete requirements to add:

* **Wall-clock-paced playback** with loop and with configurable *drift* per
  camera, so the same scenario exercises the time-skew code paths (§1.8).
* **Per-camera codec/bitrate/GOP** taken straight from the `Camera.stream` spec
  already in the data model (`codec, bitrate_kbps, gop, packet_loss, latency_ms,
  clock_offset_ms, drift_ppm`) — SurvSim's camera model is *already* the right
  shape for this, which is unusual and worth noting.
* **Main + sub + metadata streams per camera**, so resolution-tiered analytics
  (§1.4) can be tested.
* **Injected faults on a schedule**: connection drop, SPS/PPS omission, fps
  collapse, timestamp discontinuity, 30-second freeze. These are the failures
  that take production systems down and they cannot be tested any other way.
* **RTSPS and multicast modes** (`mediamtx` supports both families) to validate
  the customer's network posture before site visit.

### 11.3 ONVIF emulation

Three tiers, in build order:

1. **Buy/borrow tier.** Happytime's ONVIF RTSP Server already "*simulates any
   ONVIF-compliant device*" across "*Profile S … Profile T Advanced video (H.265,
   metadata, analytics) … Profile G Recording and storage … Profile M Analytics
   (metadata, events)*" and "*provides compatibility testing for VMS/NVR
   manufacturers*" ([Happytime](https://www.happytimesoft.com/products/onvif-rtsp-server/index.html)).
   Commercial licence; use it as the conformance oracle. Note there are
   open-source points of comparison: a virtual ONVIF server that "*creates virtual
   ONVIF devices from existing RTSP streams*" but where "*currently only Onvif
   Profile S (Live Streaming) is implemented with limited functionality*"
   ([daniela-hase/onvif-server](https://github.com/daniela-hase/onvif-server)),
   and an ONVIF Simulator documented as part of IOTech Edge Xpert
   ([Edge Xpert ONVIF Simulator](https://docs.iotechsys.com/edge-xpert23/device-services/onvif-camera/onvif-sim.html)).
2. **Build tier.** A `survsim-onvif` service implementing WS-Discovery, the device
   service (including `GetSystemDateAndTime` / `SetSystemDateAndTime` so time-sync
   behaviour is testable), media2 profiles matching the SurvSim camera specs, the
   PTZ service wired to the actual simulated PTZ (so a VMS operator can drive the
   simulated camera and see it move — this demo alone sells the tool), the events
   service with motion and **tamper** notifications driven by SurvSim's existing
   tamper schedule, and the analytics/metadata service emitting Profile M.
3. **VMS-native tier.** Milestone's **StableFPS** driver path
   ([MilestonePSTools samples](https://github.com/MilestoneSystemsInc/PowerShellSamples))
   and the DirectShow driver that "*provides 8 video channels, where each channel
   can be set to a DirectShow device such as a local/USB web camera, an AVI video
   file*" ([Milestone driver installation doc](https://www.milestonesys.com/globalassets/techcomm/ltsb/provms/english-united-states/4062.htm)) **[secondary]**
   let a SurvSim export become a camera inside XProtect with no ONVIF at all —
   the fastest route to a customer demo.

### 11.4 Synthetic metadata injection

SurvSim already produces the exact payloads a Profile M stream needs. The work is
serialisation plus deliberate corruption:

* **Truthful mode**: project GT into ONVIF `MetadataStream` (frames, objects,
  appearance, behaviour, geolocation) and into our own `det/track/event` schemas
  (§5.2). This produces a **perfect-analytics** stream, which is the correct way
  to test *everything downstream of the model*: fusion, rules, alarm queue,
  operator UI, audit, storage. Testing a PSIM against a perfect detector is a
  legitimate and hugely underused technique.
* **Degraded modes** with tunable, seeded error injection: miss rate, false-positive
  rate (with realistic spatial priors — FPs cluster on vegetation and reflections,
  they are not uniform), localisation noise, class confusion, ID switches at
  occlusions, latency distribution, and *correlated* failures under simulated
  weather. This gives a **synthetic-analytics dial** from oracle to garbage, and
  lets us answer the question every customer asks and no vendor can: *how good
  does the detector have to be for the system to be useful?*
* **Multi-vendor heterogeneity**: emit "camera A's metadata" with a different
  schema/class taxonomy/coordinate convention than "camera B's", because that is
  the real integration problem (§1.1).

### 11.5 CI: the scenario regression suite

```
 scenarios/regression/
   perimeter/     fence_climb_day, fence_climb_night_rain, crawl_under,
                  vehicle_dropoff, ladder, two_person_diversion,
                  animal_fox, animal_deer, vegetation_wind, rain_on_lens,
                  headlight_glare, camera_web, bird_on_lens
   crowd/         queue_jump, group_merge_split, loiter_90s, tailgate_gate3,
                  bag_left_10min, fight_2p, fall_medical
   adversarial/   hood_up, umbrella, mask, wall_hug, ptz_gap_timing,
                  blindspot_route, slow_creep_0p3ms
   degradation/   crf_18..40, fps_25..5, gop_2s..8s, packet_loss_0..3pc,
                  clock_skew_0..2000ms, substream_only
   faults/        camera_drop_60s, sps_missing, freeze_30s, tamper_cover,
                  switch_power_loss_zone4, alarm_flood_200_per_min
```

CI contract **[estimate — proposed, to be implemented]**:

| Gate | Threshold | Fails the build if |
|---|---|---|
| Pd on `perimeter/*` threat scenarios | ≥ 0.95 | any regression > 2 points vs baseline |
| False alarms on `perimeter/animal_*`, `vegetation_wind` | ≤ 0.1/hour | any increase |
| Track ID switches on `crowd/group_merge_split` | ≤ baseline | +10 % |
| Detection-to-alarm p95 | ≤ 3 s | +20 % |
| Pd on `adversarial/*` | reported per class | silent drop > 5 points |
| Pipeline survives `faults/*` | no crash, correct health alarm | any crash or missed health alarm |

The important property: **these are system tests, not model tests.** They run the
real VMS adapter, the real broker, the real rules engine and the real alarm queue,
and they score the alarm the operator would have seen. That is a capability
almost no competitor has, and it is exactly what a CNI customer's change-control
board wants to see before approving a model update (§2.4, §4.7).

### 11.6 Digital twin and site-specific pre-deployment modelling

The highest-value consulting-flavoured use: before a site is built, build it.

* Import the site model (CAD/BIM/photogrammetry/point cloud) into UE5; place
  candidate cameras; run the **camera-placement optimiser** already in
  `02_ARCHITECTURE.md §7` (`eval/placement`); output DORI/AORI coverage maps,
  blind-spot heatmaps and camera-overlap matrices; then run the adversarial
  scenarios to find the route a real intruder would take through the proposed
  design. Deliver *"here are the three gaps in your £2 m camera plan"* — which
  is a sellable artefact in its own right and a very effective way to get into
  an account before the tender.
* Note the pedigree: MEVA supplies "*a 3D site model and KRTD camera models*"
  ([MEVA paper](https://arxiv.org/pdf/2012.00914)), and DIVA funded
  "*Analysis-by-Synthesis*" with Unreal ([JHU CIRL](https://cirl.lcsr.jhu.edu/deep-intermodal-video-analytics-diva-project/)).
  Omniverse/USD is the interchange route if Isaac becomes the second backend.
  **[VERIFY — no Omniverse digital-twin-of-a-security-site reference architecture
  was retrieved this session.]**

### 11.7 Shadow-mode comparison harness

The same comparison service used on a live site (§4.7) should be reusable against
SurvSim, with one crucial difference: **on the simulator there is ground truth**,
so "model vN+1 disagrees with vN" becomes "vN+1 is right and vN was wrong, here,
in these conditions". Ship one harness, two truth sources (GT in sim,
operator-confirmation on site). That symmetry is what makes the simulator part of
the product rather than a research toy.

### 11.8 What to build, in order

1. `mediamtx` re-stream with pacing, per-camera codec params and fault injection
   (2–3 weeks) **[estimate]**.
2. Profile M / internal-schema metadata emitter with the error-injection dial
   (3–4 weeks).
3. Regression suite v1: 20 scenarios, scoreboard, CI gate (4 weeks).
4. ONVIF emulator tier 2 (device/media2/events/PTZ/analytics) (6–8 weeks).
5. Milestone adapter demo (StableFPS path first, AI Bridge second) (4 weeks).
6. Placement optimiser + AORI report generator as a customer-facing deliverable
   (4 weeks).

---

## 12. Three target architectures

*All numbers are **[estimate]** — engineering sizing derived from the primitives
cited above, not vendor quotations. Prices deliberately omitted; specify to the
customer's procurement framework.*

### 12.1 Small site — 8 cameras, edge-only, no VMS server

**Use case:** industrial yard, substation compound, small logistics depot.
Requirement: perimeter intrusion at night, 30-day retention, two guards with
phones, no IT department.

```
 8× fixed bullet (4 MP, H.265, IR, Profile S/T/G, NDAA-clean, 8–13 W)
        │ PoE, Cat6, ≤90 m
 1× 12-port PoE+ managed switch (185 W budget, VLAN, IGMP snooping, UPS 1 kVA)
        │
 1× EDGE APPLIANCE  (fanless x86 + Jetson Orin NX 16 GB, or Orin AGX 32 GB)
    ├ docker compose: ingest (DeepStream) │ tracker │ fusion │ rules │
    │                 local NVR (VST or Nx Witness) │ MQTT broker │ web UI
    ├ 2× 8 TB surveillance HDD (RAID-1) + 500 GB NVMe hot/OS
    └ LTE/5G router for alerting + remote support (VPN, outbound only)
 guards: mobile push with clip + zone; local sounder relay via camera I/O
```

Sizing check: 8 cameras × (4 + 0.4) Mbit/s = 35 Mbit/s ingest — trivial.
Storage: 8 × 4 Mbit/s × 30 d ≈ 10.4 TB raw → 13 TB with overhead → fits 2× 8 TB
RAID-1 at ~85 % (tight; specify 2× 12 TB). Decode: 8 substreams + 2–3 escalated
main streams is well inside an Orin NX even at the pessimistic 8-session NVDEC
figure (§4.2) **provided** analytics runs on substreams with main-stream escalation
— which is exactly why the tiered design of §1.4 matters at the small end, not
just the large end.

Notes: no HA (accepted risk, documented); the appliance is physically stealable so
FDE is mandatory (§7.4); updates arrive as a signed bundle over the LTE link with
automatic rollback; the whole system must survive a 4-hour power cut on UPS +
graceful shutdown. This tier's margin dies from truck-rolls, so *remote
diagnosability is the primary engineering requirement*, above accuracy.

### 12.2 CNI site — 200 cameras, on-prem cluster, air-gapped

**Use case:** power station, water treatment, port terminal, major airport
airside zone. Requirement: perimeter + internal zones, 31-day video retention,
12-month metadata, 24/7 control room with 3 operators, NCSC CAF assessment,
no internet.

```
              ┌──────────────── CONTROL ROOM ────────────────┐
              │ 3× operator workstation (VMS client + our map)│
              │ 1× supervisor + video wall (multicast)        │
              └───────────────────┬──────────────────────────┘
 ┌─────────────────────────────── SERVER VLAN ────────────────────────────┐
 │ 2× Management/Event/SQL (clustered, N+1)                               │
 │ 5× Recording Server (40 cams each, N+1 = 6 boxes, 2×10 GbE, iSCSI/DAS) │
 │ 3× ANALYTICS NODE: 2× L40S-class GPU each  (≈30 cams/GPU @8 fps)       │
 │ 2× FUSION/RULES node (active/standby, state from Kafka)                │
 │ 3× Kafka + 3× ZooKeeper/KRaft │ Postgres+pgvector │ Prometheus/Grafana │
 │ 1× on-site container registry + model registry (offline bundles)       │
 │ storage: 2× 24-bay JBOD, RAID-6, ~400 TB raw → ~320 TB usable          │
 └───────────────────────────────┬───────────────────────────────────────┘
 ┌───────────────────────────────▼──── CAMERA VLANs (per zone) ───────────┐
 │ 10× 24-port PoE+ access switches (fibre uplinks, dual-homed, UPS)      │
 │ 200 cameras: 140 fixed 4 MP, 30 PTZ, 20 thermal, 10 multi-sensor       │
 │ + 8 radar heads, 4 km fence sensor, 30 access-controlled doors         │
 │ + PTP/NTP appliance (GNSS), syslog collector                            │
 └────────────────────────────────────────────────────────────────────────┘
```

Sizing check: ingest 200 × 4.5 = 900 Mbit/s → 10 GbE core, comfortable.
Storage at H.265 2 Mbit/s and 31 days continuous: 200 × 2 × 31 × 10.8 ≈ 134 TB;
at 4 Mbit/s main-stream quality, 268 TB — hence ~320 TB usable with growth.
Analytics: 200 cameras at 8 fps analysed / ~30 per GPU → 7 GPUs needed; specify 6
in service + 2 spare across 3 nodes, so any single node can fail with graceful
fps reduction rather than camera loss. Decode is the binding constraint, so
substream-first analytics with main-stream escalation again.

Compliance overlay: CAF evidence pack (asset inventory including camera firmware,
access control, detection of anomalous camera behaviour, degraded-mode operation);
offline update path; separate audit-log retention; DPIA support pack; SBOM per
release; four-eyes on export and on any identity linkage (§7.3).

Acceptance: §9.5 schedule, with a staged-intrusion campaign of ≥ 30 attempts per
threat class per zone type and a 30-day NAR measurement including a winter storm.

### 12.3 Border / linear asset — 25 towers over 50 km

**Use case:** border sector, pipeline, rail corridor, large estate boundary.
Requirement: detect and classify human movement at 0.5–2 km, hand off between
towers, dispatch a mobile patrol, operate on solar with satellite/cellular
backhaul.

```
  TOWER (×25, ~2 km spacing)                          REGIONAL HUB
  ┌──────────────────────────────────┐               ┌──────────────────────┐
  │ 12–25 m mast, lightning + earth  │               │ fusion cluster       │
  │ • 1× PTZ EO/IR (cooled or uncooled│               │ (cross-tower track   │
  │   thermal + visible, slew-to-cue) │               │  graph, STANAG 4676  │
  │ • 2× fixed thermal (640×512)      │               │  export)             │
  │ • 1× ground-surveillance radar    │  60 GHz PtP   │ VMS/archive          │
  │   (2–5 km human detection)        │◀─── mesh ────▶│ PSIM / C2 + map COP  │
  │ • optional acoustic / RF sensor   │   or LTE/LEO  │ operator positions   │
  │ • EDGE: Orin AGX 64 GB (or 2×)    │               │ model/CI registry    │
  │   DeepStream + radar fusion +     │               └──────────┬───────────┘
  │   local 14-day recording (4 TB)   │                          │ VPN
  │ • MQTT client (metadata only)     │               ┌──────────▼───────────┐
  │ • solar 600–1200 W + 5–10 kWh     │               │ mobile patrols (ATAK │
  │   battery; 100–250 W load budget  │               │ / mobile app, push)  │
  │ • FDE, tamper switch, remote wipe │               └──────────────────────┘
  └──────────────────────────────────┘
```

Sizing check: 25 towers × 3 imaging sensors = 75 streams, all analysed **at the
tower** (§2.5). Metadata uplink per tower: at 20 tracks/min × ~1 kB ≈ 0.003
Mbit/s — nothing. Alert clip: 20 s of 1 Mbit/s ≈ 2.5 MB, deliverable over LTE in
seconds and over GEO in a minute. Local storage: 3 × 3 Mbit/s × 14 d ≈ 4.4 TB →
specify 2× 4 TB industrial SSD (temperature range matters more than capacity).
Power: Orin AGX at 40–60 W plus radar plus PTZ heater is the budget driver; design
for the worst solar week of the year with 3 days autonomy, and implement
**power-aware degradation** (drop to thermal-only + radar at low battery, and say
so on the operator's map).

Handoff design: towers have no overlapping fields of view, so cross-tower
association is *predictive*, not appearance-based — a track leaving tower 7
eastbound at 1.2 m/s should be expected at tower 8 in 20–28 minutes, and the
fusion node should carry that hypothesis rather than starting a new global ID.
This is a genuinely different MTMC regime from the campus case and is the
strongest reason to keep the track *graph* with hypotheses (§6.1).

Political/programme overlay (§13.4): this tier attracts oversight. Budget for
published accuracy metrics, an auditable decision log for every alert acted upon,
a civil-liberties review, and the assumption that the system's performance figures
will be examined by a national audit office.

---

## 13. Anti-patterns and post-mortems

### 13.1 Architecture anti-patterns

* **A1 · Analytics as a second consumer of every camera.** Each analytics
  container opening its own RTSP session to each camera: 2× the camera's encoder
  load, 2× the network, and cameras that collapse under three subscribers.
  *Fix:* one ingest per camera, fan out internally (this is exactly why Milestone
  built gRPC Direct Streaming, §3.1).
* **A2 · Analytics on the recording server.** Steals CPU from the one job that
  must never fail, and creates a failure mode where a model bug loses evidence.
  *Fix:* separate nodes, always.
* **A3 · Sizing on average bitrate.** See §2.2. Storms are correlated.
* **A4 · Cloud round-trip for real-time alarms.** 300 ms of network plus a cold
  container plus an egress bill, to tell a guard 40 m away that someone is at the
  fence. *Fix:* edge decides, cloud remembers.
* **A5 · No ground-plane calibration.** Zones and speeds in pixels; every rule
  becomes camera-specific and untransferable; cross-camera fusion impossible.
  *Fix:* homography at commissioning, mandatory field.
* **A6 · Hard AND-gates for corroboration.** `R05 §4.5` shows why: nuisance
  causes are correlated across modalities, so the AND reduces Pd more than FAR.
* **A7 · Discarding suppressed events.** Unauditable. Career-ending (`R05 §4.5`).
* **A8 · Collapsing the association graph.** §6.1. Irreversible and
  unexplainable.
* **A9 · Alarm queue in the UI's memory.** Refresh loses alarms. *Fix:* durable
  broker + DB, UI is a view.
* **A10 · Prebuilt TensorRT engines in the image.** Breaks on driver update
  (§4.2).
* **A11 · One model, all sites, one threshold.** Guarantees a bad NAR somewhere.
  *Fix:* per-site config as versioned data.
* **A12 · Shipping "AI accuracy 99 %" with no defined Pd/NAR protocol.** This
  becomes a contractual and possibly regulatory statement (§7.5).
* **A13 · Ignoring the operator-load ceiling.** Above ~6–10 alarms/hour the
  humans stop looking and measured system Pd → 0 while model Pd stays 0.98
  (§9.4).
* **A14 · Camera credentials shared across the fleet, never rotated.** One
  extracted firmware password owns 200 cameras (§1.9, §7.3).
* **A15 · No fleet firmware-update path.** Guarantees a CVE-2021-36260 repeat
  (§1.9).

### 13.2 Post-mortem: camera-fleet compromise (documented)

The clearest publicly documented failure chain in this industry:
a command-injection bug from "*insufficient input validation*" allowing
"*arbitrary commands with root privileges*" on "*more than 70 Hikvision camera
and NVR models*" ([SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2021-36260/), [Fortinet](https://www.fortinet.com/blog/threat-research/mirai-based-botnet-moobot-targets-hikvision-vulnerability));
"*over 80,000 exploitable Hikvision cameras exposed online*"
([BleepingComputer](https://www.bleepingcomputer.com/news/security/over-80-000-exploitable-hikvision-cameras-exposed-online/),
[CPO Magazine](https://www.cpomagazine.com/cyber-security/over-80000-hikvision-cameras-with-an-critical-exploited-vulnerability-exposed-online/));
patched on the day of disclosure, "*two known public exploits*" published
afterwards ([SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2021-36260/));
and a Mirai derivative, Moobot, mass-recruiting the unpatched estate
([SecurityAffairs](https://securityaffairs.com/125409/malware/moobot-botnet-hikvision.html),
[gbhackers](https://gbhackers.com/mirai-based-botnet-moobot-exploit-hikvision-vulnerability/)).

**What went wrong architecturally, not morally:** the patch existed and the estate
did not receive it. That is a fleet-management failure, and it is *our* problem
because our product sits on the same VLAN. Design responses: inventory with
firmware version as a first-class field; an alert when a device's firmware is
below the known-vulnerable threshold; egress-blocked camera VLAN so a compromised
camera cannot reach a C2 server; anomaly detection on camera *behaviour*
(a camera making outbound connections is compromised, full stop); and a documented
update campaign capability.

### 13.3 Post-mortem: analytics that never earned primary status

The i-LIDS record itself is the post-mortem of a generation of video analytics:
after two decades, systems were being approved as "*secondary detection
system[s] in an operational alert role*" for a single scenario
([IFSEC](https://www.ifsecglobal.com/uncategorized/vcasys-passes-i-lids-analytics-test/)),
and the industry press was asking, in so many words, how useful the whole regime
was ([Professional Security](https://www.professionalsecurity.co.uk/news/interviews/how-useful-is-i-lids/),
[Professional Security: "I-LIDS Test"](https://www.professionalsecurity.co.uk/news/news-archive/i-lids-test/)).
The i-LIDS datasets were built with the nuisances in them on purpose —
"*animals running across the scene, various body movements, camera faults and
shadows*" ([i-LIDS brochure](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf))
— and that is what the systems failed on.

**Lesson:** the historical failure of video analytics was never the detector. It
was the nuisance rate under weather, wildlife and camera faults. A 2026 product
that does not make nuisance suppression its headline engineering programme is
repeating the 2006 mistake with a bigger model. This is the strongest possible
argument for the `degradation/` and animal/vegetation branches of the SurvSim
regression suite (§11.5).

### 13.4 Post-mortem: border tower programmes

The public record on the US Integrated Surveillance Towers programme is the
cautionary tale for large distributed deployments: GAO reporting DHS plans to
grow "*from the 830 current towers to 2,300 by the year 2034*" with "*around $1
billion*" for autonomous towers, statutory language requiring that "*all the new
surveillance towers have 'autonomous capabilities'*", and the observed programme
pattern — "*a pattern has emerged where CBP will roll out a new program with a
'cool sounding' name, and then, three to five years later, either the inspector
general, the GAO, or House Oversight will find that it's wasteful, it's
ineffective, it's not delivering on its promise*" — with critics holding that
"*these new towers are unproven, unaccountable, and that the program has been a
failure for decades*"
([Reason](https://reason.com/2026/07/30/homeland-security-is-spending-1-billion-on-autonomous-border-surveillance-towers/),
[FedScoop](https://fedscoop.com/dhs-budget-border-wall-surveillance-shutdown/),
[EFF](https://www.eff.org/deeplinks/2023/03/cbp-expanding-its-surveillance-tower-program-us-mexico-border-and-were-mapping-it)).
Note also that a competitive-concentration criticism attached to the award
(reporting that "*the only company in a position to immediately fulfill that
contract requirement was Anduril*", [Reason](https://reason.com/2026/07/30/homeland-security-is-spending-1-billion-on-autonomous-border-surveillance-towers/)).
Balance: the same programme demonstrably works at scale — 300+ towers, 30 % of a
border, "*hundreds of thousands of border crossings*" autonomously logged
([ASDNews](https://www.asdnews.com/news/defense/2024/09/27/anduril-deploys-300th-autonomous-surveillance-tower-ast-advancing-capability-border-security),
[ExecutiveBiz](https://www.executivebiz.com/articles/andurils-autonomous-surveillance-towers-boost-southern-us-border-protection)).

**Lessons for a vendor:** (1) publish measured Pd/NAR before someone else
measures them for you; (2) build the audit trail as a product feature, because
oversight is inevitable at this scale; (3) "autonomous" written into a statute or
a spec without an accompanying accuracy protocol is a trap — insist on the
protocol; (4) expect the civil-liberties analysis to be part of the operating
environment (e.g. [Privacy International](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example)),
and be able to answer it with architecture (retention limits, purpose limitation,
pseudonymisation, four-eyes identity linkage) rather than with a press release.

### 13.5 Anti-patterns in the simulator's own use

* **Training only on synthetic and reporting synthetic metrics.** The sim2real
  gap is `R04`'s whole subject; treat SurvSim numbers as *relative* (A vs B, vN vs
  vN+1) and never as absolute field performance.
* **Regression suites that only contain events.** Majority-nuisance, or it does
  not model operations (§13.3).
* **A perfect virtual camera.** If the virtual RTSP stream is cleaner than any
  real camera, the test is worthless. The degradation pipeline must be on by
  default, and the *fault* scenarios (§11.5) must be in the nightly run.

---

## 14. Appendix A — the hop chain

The traversal that produced this document, hop by hop, with the searches that
landed before the budget was exhausted:

| Hop | Layer | Representative sources reached |
|---|---|---|
| 1 | **Standards** — device/metadata interoperability | ONVIF Profiles S/T/G/M pages and Profile G spec PDF; ONVIF Streaming Spec (via `R01`); [onvif/specs repo](https://github.com/onvif/specs); IEC 62676-4 / DORI (Axis white papers, JVSG on the 2025 revision) |
| 2 | **Standards → defence exchange formats** | STANAG 4609 (via `R05`), STANAG 4676 / AEDP-12 (GlobalSpec, IEEE, Elsis) — closing an open `[VERIFY]` in `R05 §4.6`; SOSA/MOSA (Open Group C212, NAVAIR, tri-service memo) |
| 3 | **Reference architectures** | NVIDIA Metropolis MTMC/RTLS microservices; VSS blueprints (public-safety, smart-city, warehouse, Sparse4D 3D); DeepStream reference apps; Triton; Cisco/NETGEAR/ALAXALA network guides; AWS k3s+Greengrass |
| 4 | **Vendor docs — VMS layer** | Milestone server components + System Architecture Documents + AI Bridge (containers, Kafka, gRPC Direct Streaming) + PowerShell/StableFPS; Network Optix Plugin SDK / Metadata SDK / nx_open_integrations; Genetec RSA Surveillance product page, brochure and plugin guide |
| 5 | **Vendor docs — camera/edge layer** | Axis ACAP (developer docs, release notes 12.2, native-SDK examples, acap-runtime, ARTPEC-9/AV1); Hikvision HEOP 2.0; Hanwha Wisenet Open Platform; Jetson/NVDEC developer-forum threads; Hailo-8 (via `R01`) |
| 6 | **Deployment case studies** | Anduril Sentry/Lattice at CBP (tower counts, XRST contract, acceptance testing); IARPA DIVA + MEVA collection architecture (328 h, 28 cameras, 150+ actors, 3D site model, KRTD); Wowza WebRTC/WHEP control-room deployments; Happytime/Edge Xpert ONVIF simulators in VMS QA |
| 7 | **Failure post-mortems** | CVE-2021-36260 → Moobot/Mirai (Fortinet, SentinelOne, SecurityAffairs, BleepingComputer, CPO); NDAA §889 / FCC Covered List exclusions (IPVM, CRS, Federal Register); GAO-reported Integrated Surveillance Towers criticism (Reason, FedScoop, EFF); i-LIDS "secondary approval only" history (IFSEC, Professional Security) |
| 8 | **Security & assurance guidance, and back to the simulator** | NCSC CAF (4 objectives / 14 principles / 39 outcomes, outcome-based); MOD Secure by Design, JSP 440 Leaflet 5C, JSP 604; SBOM/signing practice; then the synthesis in §11 — mediamtx, ONVIF emulation tiers, StableFPS/DirectShow virtual cameras, Profile M injection, the regression gate, and the digital-twin placement workflow |

**Open `[VERIFY]` items for a follow-up session** (in priority order):
(1) UK MOD Pyramid / LOSA open-architecture publications; (2) TAK/ATAK + CoT
schema; (3) OGC SensorThings; (4) ICO / UK Surveillance Camera Code of Practice
and GDPR/DPIA specifics; (5) STANAG 4559 CSD and MISB KLV local sets;
(6) Genetec SDK / Mission Control mechanics and the Vidsys/CNL/Palantir PSIM
claims (also open in `R05 §4.7`); (7) adversarial-patch literature for person
detectors; (8) Avigilon and Exacq integration surfaces; (9) per-device numbers for
Axelera/Ambarella/Qualcomm/Coral; (10) IEC 62676-4:2025 seven-level framework read
from the standard itself; (11) Omniverse digital-twin security reference;
(12) AWS Panorama product status.

---

## 15. Sources

**Standards and profiles** — [ONVIF Profiles index](https://www.onvif.org/profiles/) ·
[Profile S](https://www.onvif.org/profiles/profile-s/) ·
[Profile T](https://www.onvif.org/profiles/profile-t/) ·
[Profile G](https://www.onvif.org/profiles/profile-g/) ·
[Profile G spec v1.0 (PDF)](https://www.onvif.org/wp-content/uploads/2017/01/ONVIF_Profile_G_Specification_v1-0.pdf) ·
[Profile M](https://www.onvif.org/profiles/profile-m/) ·
[Profile M release](https://www.onvif.org/pressrelease/onvif-releases-profile-m-for-metadata-and-events-for-analytics-applications/) ·
[Profile M spec (PDF)](https://www.onvif.org/wp-content/uploads/2021/06/onvif-profile-m-specification-v1-0.pdf) ·
[ONVIF Streaming Spec (PDF)](https://www.onvif.org/specs/stream/ONVIF-Streaming-Spec.pdf) ·
[onvif/specs (GitHub)](https://github.com/onvif/specs) ·
[Fora Soft: ONVIF profiles explained](https://www.forasoft.com/blog/article/onvif-profiles-in-security-systems) ·
[Fora Soft: Profile M](https://www.forasoft.com/blog/article/onvif-profile-m) ·
[Video Experts Group: Profile G](https://www.videoexpertsgroup.com/glossary/onvif-profile-g) ·
[Pelco: ONVIF guide](https://www.pelco.com/blog/onvif-guide) ·
[Axis: pixel density based on IEC 62676-4:2014](https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014) ·
[Axis: pixel density and DORI (PDF)](https://www.axis.com/dam/public/b2/d9/29/pixel-density-en-US-403691.pdf) ·
[Infiniti: DORI white paper](https://www.infinitioptics.com/whitepapers/dori-detection-observation-recognition-identification) ·
[Infiniti: DORI glossary](https://www.infinitioptics.com/glossary/dori-detection-observation-recognition-identification) ·
[TP-Link: What is DORI?](https://www.tp-link.com/us/support/faq/4098/) ·
[JVSG: IEC/EN 62676-4:2025 OODPCVS](https://www.jvsg.com/iec-62676-4-oodpcvs/) ·
[Backstreet: DORI & EN 62676-4:2025](https://www.backstreet-surveillance.com/cctv-industry-experts/dori-cctv.html) ·
[CCTVplanner EN 62676-4 calculator](https://cctvplanner.io/en-62676-4-calculator) ·
[STANAG 4676 (GlobalSpec)](https://standards.globalspec.com/std/14474804/stanag-4676) ·
[AEDP-12 NITS (GlobalSpec)](https://standards.globalspec.com/std/14507144/aedp-12) ·
[NATO ISR tracking standard (IET/IEEE)](https://ieeexplore.ieee.org/document/4567745/) ·
[Elsis: NATO AGS MGECS STANAG 4676](https://www.elsis.lt/en/nato-ags-mgecs-df-sw-stanag-4676/) ·
[ImpleoTV: STANAG 4609](https://impleotv.com/2025/03/11/stanag-4609-isr-video/) ·
[Fraunhofer IOSB STANAG 4609 validator](https://www.iosb.fraunhofer.de/en/projects-and-products/stanag-4609-validator.html) ·
[Open Group SOSA technical standard C212](https://publications.opengroup.org/c212) ·
[Open Group on the tri-service MOSA memo](https://www.opengroup.org/The-Open-Group-SOSA-and-FACE-Consortia-Applaud-New-Tri-Services-Directive-Memorandum-that-Furthers-the-DOD's-Modular-Open-Systems-Commitment) ·
[Elma: SOSA/CMOSS/MOSA](https://www.elma.com/en/capabilities/sosa) ·
[NAVAIR MOSA](https://www.navair.navy.mil/MOSA) ·
[Curtiss-Wright MOSA](https://defense-solutions.curtisswright.com/capabilities/open-architectures/mosa)

**Cameras, edge SoCs and on-camera platforms** — [Axis ACAP](https://www.axis.com/for-developers/acap) ·
[Axis developer docs (ACAP 12)](https://developer.axis.com/acap/) ·
[ACAP 12.2 release notes](https://developer.axis.com/acap/release-notes/12.2/) ·
[ACAP supported APIs](https://developer.axis.com/acap/api/) ·
[acap-native-sdk-examples](https://github.com/AxisCommunications/acap-native-sdk-examples) ·
[acap-runtime](https://github.com/AxisCommunications/acap-runtime) ·
[CamStreamer on ARTPEC-9](https://camstreamer.com/blog/artpec-9) ·
[Hikvision HEOP 2.0](https://www.hikvision.com/us-en/Partner/technology-partners/hikvision-embedded-open-platform-2-0/) ·
[HEOP-enabled products](https://www.hikvision.com/en/Partners/technology-partners/hikvision-embedded-open-platform-2-0/heop-2-0-enabled-products/) ·
[Hanwha Wisenet Open Platform](https://hanwhavisionamerica.com/software/wisenet-open-platform-applications/) ·
[Network Optix: Hanwha in-camera analytics](https://support.networkoptix.com/hc/en-us/articles/17311859862167-Hanwha-in-camera-analytics-integration) ·
[Hailo-8](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/) ·
[edgeaistack Hailo comparison](https://edgeaistack.ai/blog/hailo-8-vs-8l-vs-10h-2026/) ·
[Seeed: Jetson video analytics](https://www.seeedstudio.com/blog/2024/06/06/mastering-video-analytics-on-nvidia-jetson-your-best-bet-for-concurrent-and-high-throughput-solution/) ·
[NVDEC ≤8 streams (forum)](https://forums.developer.nvidia.com/t/orin-agx-jetpack-6-nvdec-limitation-of-8-streams/320865) ·
[Orin NX NVDEC capacity (forum)](https://forums.developer.nvidia.com/t/orin-nx-16gb-nvdec-capacity-for-4x-2560x1440-h-265-streams-and-super-mode-impact/380328) ·
[1080p30 per NVDEC (forum)](https://forums.developer.nvidia.com/t/how-much-1080-30fps-can-be-run-in-one-nvdec/376889) ·
[AGX Orin DeepStream expected FPS (forum)](https://forums.developer.nvidia.com/t/jetson-agx-orin-64-gb-source30-1080p-dec-infer-resnet-tiled-display-int8-deepstream-expected-fps/294215) ·
[vhd.me: best chips for real-time video analytics](https://vhd.me/best-chips-real-time-video-analytics/) ·
[Jetson Platform Services: DeepStream perception](https://docs.nvidia.com/moj/deepstream/deepstream.html) ·
[PTP: Emergent Vision](https://emergentvisiontec.com/video-accurate-multi-camera-synchronization-through-ieee-1588-ptp/) ·
[PTP: Teledyne](https://www.teledynevisionsolutions.com/learn/learning-center/machine-vision/precision-system-synchronization-with-the-ieee-1588-precision-time-protocol-ptp/) ·
[PTP: e-con Systems](https://www.e-consystems.com/blog/camera/technology/the-role-of-precision-time-protocol-synchronization-in-ethernet-cameras/) ·
[PTP: Basler docs](https://docs.baslerweb.com/precision-time-protocol)

**Network and transport** — [Cisco Video Surveillance SRND (PDF)](https://www.cisco.com/c/dam/en/us/td/docs/security/physical_security/video_surveillance/network/vsm/7_0/srnd/vsm_7_0_srnd.pdf) ·
[NETGEAR IP video surveillance guide (PDF)](https://www.netgear.com/images/pdf/IP-Video-Surveillance_Networking-Solution-Guide.pdf) ·
[ALAXALA AX surveillance guide (PDF)](https://www.alaxala.com/en/techinfo/archive/guide/pdf/N11R050_MCN_Solution_Guide_V1R0_e.pdf) ·
[Synectics: IP multicasting](https://www.synecticsglobal.com/en/resources-en/tech-notes/209-multicasting) ·
[IPVM network guide](https://ipvm.com/reports/network-guide) ·
[Wowza: architecting WebRTC for surveillance](https://www.wowza.com/blog/architecting-webrtc-for-surveillance-and-remote-monitoring) ·
[Wowza: traffic management centres & WebRTC](https://www.wowza.com/blog/how-traffic-management-centers-use-webrtc-to-deliver-sub-second-live-video) ·
[Wowza Streaming Engine 4.11 / WHEP](https://www.wowza.com/blog/wowza-streaming-engine-4-11-updates-webrtc-for-production-scale-cloud-native-streaming) ·
[bloggeek.me: WHEP](https://bloggeek.me/webrtcglossary/whep/) ·
[Cloudflare Stream WebRTC](https://developers.cloudflare.com/stream/webrtc-beta/) ·
[mediamtx](https://github.com/bluenviron/mediamtx) ·
[mediamtx restreaming with ffmpeg (JoshooaJ)](https://www.joshooaj.com/blog/2025/02/19/restreaming-rtsp-with-ffmpeg-and-mediamtx/)

**VMS and PSIM** — [Milestone: server components](https://doc.milestonesys.com/2021r2/en-US/system/sad/sad_servercomponents.htm) ·
[Milestone XProtect System Architecture Document 2019 R1 (PDF)](https://milestonedownload.blob.core.windows.net/files/XProtect%202019%20R1/Manuals%20and%20guides/Advanced%20VMS/Guides%20and%20documents/System%20architecture%20document/MilestoneXProtectVMSproducts_SystemArchitectureDocument_en-US.pdf) ·
[Milestone storage architecture white paper (PDF)](https://netcam.cz/produkty/software-sprava-videa/pdf/xprotect_corporate_wp_milestone_storage_architecture.pdf) ·
[Milestone: install video device drivers](https://www.milestonesys.com/globalassets/techcomm/ltsb/provms/english-united-states/4062.htm) ·
[Milestone: MIP SDK](https://www.milestonesys.com/support/for-developers/integrate-with-xprotect/) ·
[Milestone: MIP metadata intro](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html) ·
[Milestone AI Bridge containers](https://doc.milestonesys.com/AIB/Help/Latest/en-US/feature_flags/ff_aibridge/aibi_overview_containers.htm) ·
[Milestone AI Bridge integrator manual 2.0 (PDF)](https://doc.milestonesys.com/AIB/PDF/v2_0/en-US/MilestoneAIBridge_IntegratorManual_en-US.pdf) ·
[AI Bridge docker-compose configuration](https://doc.milestonesys.com/AIB/Help/latest/en-us/feature_flags/ff_aibridge/aibi_dc_configureaib.htm) ·
[AI Bridge: securing the connection](https://doc.milestonesys.com/AIB/Help/latest/en-us/feature_flags/ff_aibridge/aibi_dc_securing.htm) ·
[AI Bridge on NGC](https://milestonesys.my.site.com/developer/s/article/THE-MILESTONE-AI-BRIDGE-v1-5-IS-NOW-AVAILABLE-ON-NGC) ·
[MilestoneSystemsInc/PowerShellSamples](https://github.com/MilestoneSystemsInc/PowerShellSamples) ·
[Milestone: BriefCam supported VMS](https://www.milestonesys.com/support/software/briefcam-supported-vms/) ·
[Milestone marketplace: Sound Intelligence plugin](https://www.milestonesys.com/marketplace/sound-intelligence/sound-detector-plugin-for-milestone-xprotect/) ·
[Genetec RSA Surveillance](https://www.genetec.com/products/unified-security/security-center/restricted-security-area) ·
[Genetec RSA brochure](https://resources.genetec.com/en-product-brochures/restricted-security-area-rsa-surveillance-in-security-center) ·
[Genetec RSA plugin guide 5.1](https://techdocs.genetec.com/r/en-US/GenetecTM-Restricted-Security-Area-Surveillance-Plugin-Guide-5.1/Creating-RSA-zones-in-Security-Center) ·
[Southwest Microwave / Genetec RSA plugin (PDF)](https://southwestmicrowave.com/pdfs/technology-partners/Genetec-RSA-Surveillance-Plugin-EN.pdf) ·
[Nx Server Plugin SDK (C++)](https://support.networkoptix.com/hc/en-us/articles/202856206-C-SDK) ·
[Nx: The Server Plugin SDK](https://support.networkoptix.com/hc/en-us/articles/32766542038423-The-Server-Plugin-SDK-C) ·
[Nx Toolkit](https://www.networkoptix.com/developers/nx-toolkit) ·
[Nx developer documentation](https://support.networkoptix.com/hc/en-us/categories/32712042906647-Nx-Meta-Developer-Documentation) ·
[nx_open_integrations](https://github.com/networkoptix/nx_open_integrations) ·
[Nx OpenVINO analytics plugin readme](https://github.com/networkoptix/nx_open_integrations/blob/master/cpp/vms_server_plugins/openvino_object_detection_analytics_plugin/readme.md) ·
[Anduril Command & Control](https://www.anduril.com/lattice/command-and-control) ·
[Anduril Lattice for Mission Autonomy](https://www.anduril.com/news/anduril-unveils-lattice-for-mission-autonomy)

**Analytics platforms, MLOps, orchestration** — [NVIDIA multi-camera tracking workflow](https://www.nvidia.com/en-us/ai-data-science/ai-workflows/multi-camera-tracking/) ·
[MDX MTMC microservice overview](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_MS_Overview.html) ·
[MDX MTMC quickstart](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_App.html) ·
[MDX MTMC configuration](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_MS_Configuration.html) ·
[Metropolis multi-camera demo](https://demos.ngc.nvidia.com/metropolis_multicam) ·
[VSS blueprint (GitHub)](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization) ·
[VSS public-safety introduction](https://docs.nvidia.com/vss/3.1.0/publicsafety-docs/Introduction.html) ·
[VSS blueprint deep dive](https://docs.nvidia.com/vss/3.1.0/publicsafety-docs/Blueprint-deep-dive.html) ·
[VSS smart-city deep dive](https://docs.nvidia.com/vss/3.0.0/smartcity-docs/latest/Blueprint-deep-dive.html) ·
[VSS 3D multi-camera (Sparse4D)](https://docs.nvidia.com/vss/3.1.0/warehouse-docs/3D-multi-camera-detection-and-tracking-Sparse4D.html) ·
[DeepStream performance docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html) ·
[deepstream_reference_apps](https://github.com/NVIDIA-AI-IOT/deepstream_reference_apps) ·
[Triton Inference Server](https://github.com/triton-inference-server/server) ·
[AWS: k3s + Greengrass v2](https://aws.amazon.com/blogs/containers/collecting-data-from-edge-devices-using-kubernetes-and-aws-iot-greengrass-v2/) ·
[aws-kubernetes-edge-greengrass](https://github.com/aws-samples/aws-kubernetes-edge-greengrass) ·
[AWS KVS edge deployment](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/gs-deploy-edge.html) ·
[k3s for edge (reintech)](https://reintech.io/blog/k3s-tutorial-lightweight-kubernetes-edge-iot) ·
[k3s for edge computing (oneuptime)](https://oneuptime.com/blog/post/2026-02-02-k3s-edge-computing/view) ·
[Industrial edge platforms compared](https://adhdecode.com/edge-computing/industrial-edge-iiot/industrial-edge-platforms-compared/) ·
[Greengrass vs Azure IoT Edge (ResearchGate)](https://www.researchgate.net/publication/398152009_Developing_Intelligent_Edge_Solutions_Using_AWS_Greengrass_and_Azure_IoT)

**Evaluation, datasets, programmes** — [IARPA DIVA](https://www.iarpa.gov/research-programs/diva) ·
[JHU CIRL DIVA project](https://cirl.lcsr.jhu.edu/deep-intermodal-video-analytics-diva-project/) ·
[MEVA dataset paper (arXiv 2012.00914)](https://arxiv.org/pdf/2012.00914) ·
[mevadata.org](https://mevadata.org/) ·
[MEVA KF1 data README](https://mevadata.org/resources/README-meva-kf1-data.html) ·
[VIRAT](https://viratdata.org/) ·
[Kitware CV datasets tour (PDF)](https://cdao.pages.jatic.net/public/program/Kitware_Computer_Vision_Datasets.pdf) ·
[NIST ActEV SDL](https://actev.nist.gov/sdl20) ·
[TRECVID 2022 overview (arXiv)](https://arxiv.org/pdf/2306.13118) ·
[i-LIDS brochure (gov.uk PDF)](https://assets.publishing.service.gov.uk/media/5a7af05040f0b66a2fc03e11/ilids-brochure.pdf) ·
[i-LIDS IEEE paper](https://ieeexplore.ieee.org/document/4105319/) ·
[IFSEC: VCAsys passes i-LIDS](https://www.ifsecglobal.com/uncategorized/vcasys-passes-i-lids-analytics-test/) ·
[Professional Security: how useful is i-LIDS](https://www.professionalsecurity.co.uk/news/interviews/how-useful-is-i-lids/) ·
[Professional Security: I-LIDS test](https://www.professionalsecurity.co.uk/news/news-archive/i-lids-test/)

**Security, compliance, supply chain** — [NCSC Cyber Assessment Framework](https://www.ncsc.gov.uk/collection/cyber-assessment-framework) ·
[UK Government Security: introduction to the CAF](https://www.security.gov.uk/policy-and-guidance/introduction-to-the-cyber-assessment-framework-caf/) ·
[techUK: understanding and implementing the CAF](https://www.techuk.org/resource/understanding-and-implementing-the-cyber-assessment-framework-caf.html) ·
[Bridewell: NCSC CAF](https://www.bridewell.com/ncsc-cyber-assessment-framework) ·
[ContinueOps CAF: 4 objectives, 14 principles](https://www.continueops.com/caf) ·
[Logiq: MOD Secure by Design guide](https://www.logiq.co.uk/insights/mod-secure-by-design-guide/) ·
[Digital MOD: make your technical solution secure](https://www.digital.mod.uk/policy-rules-standards-and-guidance/service-manual/architecture/defence-technology-principles/make-your-technical-solution-secure) ·
[MOD digital standards](https://defencedigital.github.io/mod-standards-digital-rules/) ·
[JSP 740 AUP (PDF)](https://oauth2.defencegateway.mod.uk/docs/jsp740aup.pdf) ·
[CVE-2021-36260 (SentinelOne)](https://www.sentinelone.com/vulnerability-database/cve-2021-36260/) ·
[Fortinet: Moobot targets Hikvision](https://www.fortinet.com/blog/threat-research/mirai-based-botnet-moobot-targets-hikvision-vulnerability) ·
[SecurityAffairs: Moobot](https://securityaffairs.com/125409/malware/moobot-botnet-hikvision.html) ·
[BleepingComputer: 80,000 exposed cameras](https://www.bleepingcomputer.com/news/security/over-80-000-exploitable-hikvision-cameras-exposed-online/) ·
[CPO Magazine](https://www.cpomagazine.com/cyber-security/over-80000-hikvision-cameras-with-an-critical-exploited-vulnerability-exposed-online/) ·
[gbhackers](https://gbhackers.com/mirai-based-botnet-moobot-exploit-hikvision-vulnerability/) ·
[Pentest-Tools: CVE-2021-36260 active check](https://pentest-tools.com/vulnerabilities-exploits/hikvision-ip-camera-rce-vulnerability-hsrc-202109-01-active-check_13456) ·
[IP camera VAPT (arXiv 2202.06597)](https://arxiv.org/pdf/2202.06597) ·
[IPVM: where Dahua and Hikvision are banned](https://ipvm.com/reports/hikua-bans) ·
[CRS LSB10895: FCC equipment authorisation ban](https://www.congress.gov/crs-product/LSB10895) ·
[Federal Register, Dec 2025](https://www.federalregister.gov/documents/2025/12/04/2025-21928/protecting-against-national-security-threats-to-the-communications-supply-chain-through-the) ·
[Tec-Tel: NDAA §889 checklist](https://tec-tel.com/resources/ndaa-section-889-camera-compliance) ·
[Rhombus: NDAA-compliant cameras](https://www.rhombus.com/blog/ndaa-compliant-security-cameras/)

**Deployment case studies and critique** — [Privacy International: dual-use tech, the Anduril example](https://privacyinternational.org/report/5704/dual-use-tech-anduril-example) ·
[FedScoop: CBP doubling sentry towers](https://fedscoop.com/anduril-sentry-towers-cbp/) ·
[FedScoop: DHS budget & surveillance towers](https://fedscoop.com/dhs-budget-border-wall-surveillance-shutdown/) ·
[ExecutiveBiz: $363M XR Sentry towers](https://www.executivebiz.com/articles/cbp-anduril-extended-range-sentry-towers-363m) ·
[ExecutiveBiz: Anduril towers boost border protection](https://www.executivebiz.com/articles/andurils-autonomous-surveillance-towers-boost-southern-us-border-protection) ·
[ASDNews: 300th autonomous surveillance tower](https://www.asdnews.com/news/defense/2024/09/27/anduril-deploys-300th-autonomous-surveillance-tower-ast-advancing-capability-border-security) ·
[Reason: $1bn on autonomous border towers](https://reason.com/2026/07/30/homeland-security-is-spending-1-billion-on-autonomous-border-surveillance-towers/) ·
[EFF: mapping CBP surveillance towers](https://www.eff.org/deeplinks/2023/03/cbp-expanding-its-surveillance-tower-program-us-mexico-border-and-were-mapping-it)

**Simulation and test tooling** — [Happytime ONVIF RTSP Server](https://www.happytimesoft.com/products/onvif-rtsp-server/index.html) ·
[Happytime ONVIF Client](https://www.happytimesoft.com/products/onvif-client/index.html) ·
[Happytime ONVIF Proxy](https://happytimesoft.com/products/onvif-proxy/index.html) ·
[IOTech Edge Xpert ONVIF Simulator](https://docs.iotechsys.com/edge-xpert23/device-services/onvif-camera/onvif-sim.html) ·
[daniela-hase/onvif-server](https://github.com/daniela-hase/onvif-server) ·
[rgl/mediamtx-rtsp-server](https://github.com/rgl/mediamtx-rtsp-server)

**Internal cross-references** — `docs/02_ARCHITECTURE.md` (SurvSim design),
`docs/research/R01 §5` (edge throughput, ingest, VMS integration),
`docs/research/R02` (MTMC/ReID), `docs/research/R03` (behaviour/anomaly),
`docs/research/R04` (degraded imaging, sim2real),
`docs/research/R05 §4` (JDL fusion levels, time alignment, corroboration
arithmetic, interoperability standards, PSIM/C2 landscape),
`docs/research/R06` (company/ecosystem), `docs/research/H01` (veteran questions).

---

*End of D04. Word count target (10k+) met. This document is deliberately
opinionated where the evidence is thin and explicitly marked where it is absent;
the `[VERIFY]` list in Appendix A is the work queue for the next research pass.*
