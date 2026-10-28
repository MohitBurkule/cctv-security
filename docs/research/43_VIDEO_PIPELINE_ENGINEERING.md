# 43 — Video Pipeline Engineering: the plumbing an interviewer will probe

**Purpose.** Most of this corpus is about what a model sees. This report is about
how pixels get from a camera to a model and how an alarm gets from a model to an
operator — the part of a CCTV analytics product that actually breaks in the
field (D06: pilot failures are integration and video quality, not accuracy).
It covers transport (RTSP/RTP, ONVIF), codecs (GOP structure and its effect on
latency and detection), hardware decode limits, the DeepStream/GStreamer graph,
frame-dropping and backpressure, multi-camera time, VMS integration, edge-to-cloud
messages, a worked 40-camera budget, and health metrics.

**Sourcing convention.** Every factual claim below is cited to a primary source
fetched on **2026-09-26** (standards body, RFC editor, vendor documentation).
Anything I derived, estimated or assumed is tagged **[INF]**. Numbers in the
worked budget that are assumptions rather than datasheet values are tagged
[INF] individually so an interviewer cannot catch a guessed number dressed as a
fact.

**Relation to SurvSim.** SurvSim's Recorder writes clean frames and ground truth;
`survsim/sensors/degrade.py` imitates what a codec and a cheap sensor do to them.
Nothing in the repo today models *transport* — packet loss, jitter-buffer
latency, GOP-induced smearing, or decode-side frame dropping. §11 lists what a
faithful "transport degradation" stage would add, and why it matters for
evaluating i-LIDS-style timing, where a late alarm counts as a false alarm.

---

## 1. Transport: RTSP, RTP, RTCP

### 1.1 RTSP is control, RTP is media

RTSP is the control channel only; the media itself is carried in RTP. RTSP 1.0
is RFC 2326; **RTSP 2.0 is RFC 7826 (December 2016), which obsoletes RFC 2326**
([RFC 7826](https://www.rfc-editor.org/rfc/rfc7826), fetched 2026-09-26). The
methods an engineer must know (RFC 7826 §13):

| Method | Role in a camera session |
|---|---|
| `DESCRIBE` | Fetch the SDP describing the tracks (video, audio, metadata) |
| `SETUP` | Negotiate transport (UDP unicast, multicast, or interleaved over TCP) per track |
| `PLAY` | Start delivery |
| `TEARDOWN` | End the session |
| `GET_PARAMETER` | Retrieve parameters; also usable as a keep-alive |

Liveness matters operationally: RFC 7826 states that "if the client fails to
show liveness for more than the established session timeout value (normally 60
seconds), the server may terminate the context," and that liveness can be shown
by RTCP or by any RTSP request that references the session
([RFC 7826](https://www.rfc-editor.org/rfc/rfc7826), fetched 2026-09-26).

In practice, nearly every IP camera still speaks RTSP 1.0 [INF — based on field
experience; GStreamer's `rtspsrc` documentation says the element "follows RFC
2326 strictly" ([rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html),
fetched 2026-09-26)]. A client that forgets keep-alives gets a stream that dies
silently at ~60 s — one of the classic "works in the demo, drops overnight"
bugs [INF].

### 1.2 RTP timestamps and RTCP sender reports

RTP (RFC 3550) timestamps reflect the sampling instant of the first octet in
the packet, and the clock rate is fixed by the payload format
([RFC 3550](https://www.rfc-editor.org/rfc/rfc3550), fetched 2026-09-26). For
H.264, RFC 6184 requires "a 90 kHz clock rate"
([RFC 6184](https://www.rfc-editor.org/rfc/rfc6184), fetched 2026-09-26).

The RTP timestamp is **relative** — it starts at a random offset and has no
wall-clock meaning. The link to wall-clock time is the RTCP **Sender Report**,
which pairs an RTP timestamp with an NTP timestamp; per RFC 3550 "the timestamp
pairs are not transmitted in every data packet, but at a lower rate in RTCP SR
packets" ([RFC 3550](https://www.rfc-editor.org/rfc/rfc3550), fetched
2026-09-26). RFC 3550 recommends RTCP be fixed at 5 % of session bandwidth, with
a quarter of that reserved for senders (same source).

**Why this is the interview answer to "how do you timestamp a frame?"** The
right answer is: the capture time is the RTP timestamp mapped through the most
recent RTCP SR onto the *camera's* wall clock, which is only as good as the
camera's NTP/PTP discipline (§5). Stamping frames with the *receiver's* arrival
time bakes network jitter, jitter-buffer delay and decode queueing into the
timestamp — tolerable for one camera, fatal for cross-camera association [INF].
GStreamer exposes this choice explicitly: `rtspsrc` has an `ntp-sync` property
that is **disabled by default**, and an `ntp-time-source` property
([rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html),
fetched 2026-09-26).

### 1.3 H.264 over RTP

RFC 6184 (May 2011, obsoletes RFC 3984) defines three packetization modes:
single NAL unit, non-interleaved (with STAP-A aggregation and FU-A
fragmentation, preserving decoding order), and interleaved (STAP-B, MTAP,
FU-B, with a decoding-order number)
([RFC 6184](https://www.rfc-editor.org/rfc/rfc6184), fetched 2026-09-26).
A 1080p I-frame is far larger than an Ethernet MTU, so it is always fragmented
with FU-A [INF]. Consequence: **losing one UDP packet of an I-frame corrupts
the whole I-frame, and every P-frame that references it until the next IDR** —
the grey-smear / "melting" artefact every operator has seen [INF].

### 1.4 UDP vs TCP-interleaved

GStreamer's `rtspsrc` tries transports in the fixed order UDP unicast, UDP
multicast, TCP (its `protocols` default `tcp+udp-mcast+udp` allows all three;
the order itself cannot be changed) *(audit 2026-09-26: order corrected — was
given as multicast first)*, waits 5 s for UDP data before
falling back to TCP, and has a 20 s TCP timeout
([rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html),
fetched 2026-09-26).

Trade-off [INF]:
- **UDP**: lowest latency, but loss becomes visible artefacts; NAT and firewalls
  often block it on enterprise networks.
- **TCP interleaved** (RTP inside the RTSP connection): no packet loss, but loss
  becomes *latency* — head-of-line blocking stalls the whole stream and, if the
  receiver cannot keep up, the camera's send buffer fills and frames are dropped
  camera-side, invisibly.

For analytics, TCP is usually the right default on a LAN you do not control;
the monitoring consequence is that you must watch *inter-arrival time*, not only
packet loss (§9).

---

## 2. ONVIF: Profiles S, T, M

ONVIF is the interoperability layer that lets a VMS discover a camera, find its
RTSP URI, configure encoders, and subscribe to events. The profiles an
interviewer will name:

| Profile | Scope (quoted from onvif.org) | Status |
|---|---|---|
| **S** | "Basic video streaming"; "video streaming and configuration", plus PTZ, audio in, multicast, relay outputs | "Profile deprecation in process; last date of product conformance submissions is March 31, 2027" ([Profile S](https://www.onvif.org/profiles/profile-s/), fetched 2026-09-26) |
| **T** | "H.264 / H.265 video compression", "Imaging settings", "Motion alarm and tampering events", "Metadata streaming", "Bi-directional audio"; also HTTPS streaming ([Profile T](https://www.onvif.org/profiles/profile-t/), fetched 2026-09-26) | Successor to S for video [INF from the S deprecation note] |
| **M** | "Analytics configuration and information query for metadata", "Configuration and streaming of metadata", object classes incl. faces, human bodies, vehicles, plates; events "through metadata stream, ONVIF event service or over MQTT" ([Profile M](https://www.onvif.org/profiles/profile-m/), fetched 2026-09-26) | Current |

**Talking points.**
- *Profile S is being retired.* Saying "we're ONVIF Profile S compliant" in 2026
  signals stale knowledge; the correct answer is T for video + M for analytics
  metadata.
- *Profile T brings H.265 into the interoperable baseline* and makes tamper
  events a first-class event type — directly relevant to SurvSim's six tamper
  kinds: a camera that reports its own tamper event and an analytics server that
  detects tamper from pixels are two independent signals worth fusing [INF].
- *Profile M is what an analytics vendor produces.* If an analytics box emits
  ONVIF MetadataStream XML and M-style events, any M-conformant VMS can overlay
  and search it without a bespoke plug-in. Milestone states XProtect uses "the
  mandatory feature framework of Profile M for metadata communication and for
  handling events" (ONVIF blog summarised in search results:
  [onvif.org blog 2022-02-02](https://www.onvif.org/blog/2022/02/02/milestone-adds-profile-m-support-for-xprotect-plat/),
  fetched via search 2026-09-26).

---

## 3. Codecs: GOP, B-frames, and what they do to latency and detection

### 3.1 The structure

H.264 (ITU-T H.264 / ISO 14496-10) and H.265/HEVC encode a **GOP**: one intra
(I/IDR) frame decodable on its own, followed by predicted P-frames and,
optionally, bi-predicted B-frames that reference *future* frames [INF — textbook
material; the ITU recommendation page returned HTTP 500 when fetched on
2026-09-26, so no primary citation is claimed here].

Surveillance encoders typically run long GOPs (1–4 s, and "smart"/dynamic GOP
modes stretch to many seconds on static scenes) because the I-frame dominates
bitrate [INF]. Axis's datasheet for the P3265-LVE, for example, lists H.264
(Baseline, Main, High) and H.265 plus its **Zipstream** bitrate-reduction
technology, at up to 1920×1080 and 50/60 fps
([Axis P3265-LVE](https://www.axis.com/products/axis-p3265-lve/support), fetched
2026-09-26); Zipstream-class features work partly by lengthening the GOP on
static scenes [INF].

### 3.2 B-frames and latency

A B-frame cannot be decoded until the later reference frame it points to has
arrived, so each consecutive B-frame adds at least one frame period of
reorder delay at the encoder and the decoder [INF]. At 25 fps with two B-frames
that is ≥ 80 ms before anything else happens [INF]. NVIDIA's decoder exposes
exactly this: the Jetson `nvv4l2decoder` has a `low-latency-mode` property "for
bitstreams with I and IPPP frames containing no B frames" (default false)
([Gst-nvvideo4linux2](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvvideo4linux2.html),
fetched 2026-09-26). **Most surveillance cameras ship with B-frames disabled on
the main profile**, which is why this mode is usable [INF].

### 3.3 GOP length and detection quality

Three effects an interviewer may probe [all INF, reasoned from codec mechanics]:

1. **Quality breathing.** The I-frame is encoded at higher quality than the
   P-frames that follow; detection confidence visibly pulses with the GOP.
   A detector evaluated on I-frames only will overstate field accuracy.
2. **Error propagation.** A lost packet in a reference frame damages every
   frame to the next IDR. Longer GOP = longer outage per loss event.
3. **Motion vs. static.** Encoders spend bits on motion; a small, slow-moving
   intruder at distance (i-LIDS sterile-zone crawl) is exactly what rate control
   quantises away first.

### 3.4 "Just run inference on I-frames" — the trap

The decoder can be told to skip work: `nvv4l2decoder`'s `skip-frames` property
can "decode all frames, skip non-reference frames, or decode only key frames" (non-reference skipping is Jetson-only)
([Gst-nvvideo4linux2](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvvideo4linux2.html),
fetched 2026-09-26). Key-frame-only decode is almost free. The arithmetic
kills it:

- GOP of 50 at 25 fps → **0.5 fps** of analysable frames [INF].
- The corpus fact #5 (00_INDEX): tracking collapses below ~3 fps.
- A 2 s gap is a person walking ~3 m [INF, at 1.4 m/s].

So I-frame-only inference is fine for **periodic scene checks** (tamper,
defocus, scene-change, occupancy counts) and wrong for **tracking or
tripwires**. The distinction to make out loud: *decode cost scales with the
bitstream, not with what you infer on.* To infer at 5 fps from a 25 fps P-frame
stream you must still decode all 25 (P-frames depend on predecessors); the
saving comes from `nvinfer interval`, not from the decoder. The decoder's
`drop-frame-interval` ("a value of 5 means the decoder outputs every fifth
frame" — same source) saves *downstream* copies and conversion, not decode.

The practical alternative is to ask the camera for a **second stream**:
full-resolution main stream to the VMS for recording, and a lower-resolution,
lower-fps, short-GOP sub-stream for analytics [INF — standard ONVIF media
profile practice; Profile S/T both cover multiple encoder configurations].

---

## 4. Hardware decode: NVDEC limits

### 4.1 Discrete GPUs

NVDEC is a fixed-function block separate from the CUDA cores: "with complete
decoding offloaded to NVDEC, the graphics engine and CPU are free for other
operations," and it "natively supports multiple hardware decoding contexts with
negligible context-switching penalty"
([NVDEC Application Note, Video Codec SDK 13.0](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvdec-application-note/index.html),
fetched 2026-09-26).

The same note gives 1080p decode throughput **per NVDEC engine at maximum video
clock** (same source):

| Architecture | H.264 fps | HEVC fps | HEVC Main10 fps |
|---|---|---|---|
| Pascal | 694 | 810 | 789 |
| **Turing** | **771** | **1316** | 1158 |
| Ampere | 748 | 1415 | 1299 |
| Ada | 903 | 1641 | 1520 |
| Blackwell | 2172 | 1872 | 1818 |

The GeForce **RTX 2070 (Turing TU106), the GPU on this machine, has 1 NVDEC**
([NVIDIA encode/decode support matrix](https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new),
fetched 2026-09-26). Note the "at maximum video clock" caveat: the Max-Q laptop
part runs lower clocks, and the note says performance "scales proportionally
with clock frequency" (NVDEC note, same source). Budget at ~70 % of the table
figure for a Max-Q part [INF].

Two things that surprise people [INF]:
- **H.264 decodes slower than HEVC on NVDEC** in this table (771 vs 1316 on
  Turing) — the opposite of the CPU intuition.
- **NVDEC counts, not VRAM, often caps stream count.** Each decode context also
  needs surfaces (`num-extra-surfaces`, default 0, range 1–24, dGPU and Jetson —
  [Gst-nvvideo4linux2](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvvideo4linux2.html)),
  so on an 8 GB card with a detector resident, per-stream surface memory is the
  second ceiling.

### 4.2 Jetson Orin

NVIDIA's Jetson Orin page lists decode by module (fetched 2026-09-26,
[Jetson Orin](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)):

| Module | Decode (H.265) as rendered on the page | AI TOPS |
|---|---|---|
| AGX Orin 64GB & 32GB | 1× 8K30, 3× 4K60, 7× 4K30, 11× 1080p60, 22× 1080p30 | 275 (64GB) |
| AGX Orin Industrial | same, but 23× 1080p30 | — |
| Orin NX 16GB & 8GB | 1× 8K30, 2× 4K60, 4× 4K30, 9× 1080p60, 18× 1080p30 | up to 157 (16GB, Super mode; [Jetson modules](https://developer.nvidia.com/embedded/jetson-modules)) |
| Orin Nano 8GB & 4GB | 1× 4K60, 2× 4K30, 5× 1080p60, 11× 1080p30 | — |

*(Audit 2026-09-26, re-fetched: the earlier table had shifted rows — the
"23× 1080p30" row is AGX Orin **Industrial**, and the NX 16GB shares the NX
8GB figures, **18× 1080p30**. The AGX is not lower than the NX; the
"implausible" caveat is withdrawn.)* The interview point: **an Orin NX 16GB
tops out around 18 × 1080p30 H.265 decodes (an AGX Orin at 22), so a 40-camera
site needs two or three edge boxes or a sub-stream strategy** before a single
inference is run.

---

## 5. Multi-camera time: NTP, PTP, and what "synchronised" means

### 5.1 NTP

NTPv4 is RFC 5905 (June 2010). It claims "typical primary servers … precise
within a few tens of microseconds", "secondary servers and clients on fast LANs
… within a few hundred microseconds", and "a few tens of milliseconds" over
broader networks. Timestamps are 64-bit (32-bit seconds from 1900, 32-bit
fraction resolving ~232 ps); era 0 wraps in 2036
([RFC 5905](https://www.rfc-editor.org/rfc/rfc5905), fetched 2026-09-26).

### 5.2 PTP

IEEE 1588 (PTP) "supports system-wide synchronization accuracy in the
sub-microsecond range with minimal network and local clock computing
resources" ([IEEE 1588-2008 abstract](https://standards.ieee.org/standard/1588-2008.html),
fetched 2026-09-26). It needs hardware timestamping in NICs and, for the
accuracy claim, PTP-aware switches [INF].

### 5.3 What accuracy you actually need

[INF throughout.] A walker at 1.4 m/s moves 14 cm in 100 ms. Cross-camera
association with ground-plane fusion has a calibration error floor already —
corpus fact #4: 1° of extrinsic error at 30 m ≈ 3.9 m. So:

- **Clock error of ~10 ms is negligible** against calibration error; NTP on a
  LAN is enough for ground-plane fusion.
- The real problem is not clock *accuracy* but **which clock stamps the frame**.
  Cameras stamp at encode; receivers stamp at arrival; the gap is variable
  (jitter buffer, TCP retransmits, decode queue) and can be hundreds of ms
  (§8's budget). Using arrival time, two cameras seeing the same person step
  across a line can disagree by ~0.5 s.
- **Cheap cameras drift and some ignore NTP.** A health check that compares
  RTCP-SR-derived camera time to the receiver's NTP-disciplined clock and alarms
  on skew > 1 s catches this [INF].
- PTP earns its cost only for genuine frame-level fusion (stereo, triangulated
  3D pose) or when mixing with radar/RF at high rate — relevant to the
  multi-sensor work in report 37, not to ordinary multi-camera ReID.

**One-liner:** "NTP on the cameras, RTCP SR mapping at the receiver, never
arrival time; PTP only if we triangulate."

SurvSim link: the simulator has a single perfect clock. A faithful stage would
inject per-camera clock offset and drift so that multi-camera association is
tested against realistic skew [INF — not implemented].

---

## 6. The GStreamer / DeepStream graph

### 6.1 Canonical graph

```
rtspsrc ─► rtph265depay ─► h265parse ─► nvv4l2decoder ─┐
rtspsrc ─► ...                                        ├─► nvstreammux ─► nvinfer(PGIE) ─► nvtracker
rtspsrc ─► ...                                        ┘        │                              │
                                                                                  nvinfer(SGIE, ReID/attr)
                                                                                              │
                                                              nvmsgconv ─► nvmsgbroker (Kafka/MQTT)
                                                              nvdsosd ─► encoder ─► RTSP out (optional)
```

### 6.2 nvstreammux — batching

nvstreammux gathers frames from N sources into one batch. Key properties
([Gst-nvstreammux](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvstreammux.html),
fetched 2026-09-26):

- `batch-size` — maximum frames per batch.
- `batched-push-timeout` — "timeout in microseconds to wait after the first
  buffer is available to push the batch even if a complete batch is not
  formed." The muxer pushes "when the batch is filled, or the batch formation
  timeout … is reached."
- `width`/`height` — scale everything to one resolution: "the muxer outputs a
  single resolution (i.e. all frames in the batch have the same resolution)."
- `live-source` — for live feeds; the muxer then attaches the PTS of the last
  copied input buffer to the batch.
- `sync-inputs` — synchronise input frames using PTS.

**The batching trade-off [INF].** Batch size = number of cameras maximises GPU
efficiency, but the batch waits for the *slowest* camera. Set
`batched-push-timeout` to about one frame interval of the target inference rate
(e.g. 40 000 µs at 25 fps); if a camera dies, the timeout keeps the other 39
flowing instead of stalling. Setting it too high is the most common cause of
"one bad camera froze the whole site."

### 6.3 nvinfer — inference

Properties ([Gst-nvinfer](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html),
fetched 2026-09-26):

- `interval` — "the number of consecutive batches to be skipped for inference."
  (So `interval=0` infers every batch; `interval=4` infers one in five.)
- `batch-size` — frames (primary) or objects (secondary) per inference.
- `network-mode` — 0 FP32, 1 INT8 (needs a calibration file), 2 FP16, 3 BEST (audit: value 3 added).
- `process-mode` — 1 primary (full frame), 2 secondary (on detected objects).
- `model-engine-file` — a serialised TensorRT engine; supports "on-the-fly
  model update (Engine file only)" without pipeline restart. That last point is
  the MLOps hook for shipping a new model to a live site (cf. report 21).

### 6.4 nvtracker — bridging skipped frames

DeepStream ships IOU, NvSORT, NvDeepSORT (ReID-based), NvDCF (correlation
filter, can track "even without detections") and, in current releases, a
SAM2-based MaskTracker
([Gst-nvtracker](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvtracker.html),
fetched 2026-09-26). Crucially: "when PGIE's `interval` parameter exceeds zero,
the tracker receives detector objects only on inferenced frames"; on the others
tracking continues by prediction (same source). Tracks survive missed detections
for `maxShadowTrackingAge` frames, and new tracks sit in probation for
`probationAge` frames before being output (same source).

**This is the real answer to the compute budget question.** Detect at 5 fps
(`interval=4` at 25 fps), track at 25 fps with NvDCF. That cuts detector load
5× with a small loss on fast-moving objects [INF]. `probationAge` also adds
fixed latency to *first* detection — at 25 fps a probation of 3 frames is
120 ms, which counts against an i-LIDS-style timing window [INF].

### 6.5 nvmsgconv / nvmsgbroker — out of the box

`nvmsgbroker` ships adapters for **Kafka, MQTT (Mosquitto v5), AMQP, Azure IoT
and Redis Streams**, takes JSON payloads, and its wrapper library adds
auto-reconnection and multi-broker support
([Gst-nvmsgbroker](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvmsgbroker.html),
fetched 2026-09-26).

### 6.6 Measured throughput

NVIDIA's performance page reports end-to-end on `sample_1080p_h265.mp4`: Jetson
AGX Orin, PeopleNet 2.6.3 + MV3DT tracker, **147 fps**; TrafficCamNet
Transformer Lite + NvDCF, **105 fps**; on an L40S, 1,114 fps and 643 fps
respectively
([DeepStream performance](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html),
fetched 2026-09-26). 147 fps ÷ 25 fps ≈ **5.9 cameras at full rate on an AGX
Orin**, or ~29 cameras at 5 fps inference [INF — arithmetic; the page reports
fps, not stream counts, and real pipelines lose some to overhead].

---

## 7. Frame dropping and backpressure

### 7.1 What GStreamer does by default

A `queue` holds up to 200 buffers, 10 MB, or 1 s — whichever first — and when
full **blocks** upstream unless `leaky` is set; `leaky=upstream` drops new
buffers, `leaky=downstream` drops old ones
([queue](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html),
fetched 2026-09-26).

`rtpjitterbuffer` defaults to **200 ms latency**, `drop-on-latency=false`, and
mode `slave` (receiver slaved to sender clock)
([rtpjitterbuffer](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpjitterbuffer.html),
fetched 2026-09-26). `rtspsrc` defaults to **2000 ms latency**
([rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html),
re-fetched and confirmed 2026-09-26). The two are **not additive**: `rtspsrc`
builds an `rtpbin` and its `latency` becomes the latency of that internal
jitterbuffer, so a default `rtspsrc` pipeline buffers ~2 s, not 2.2 s [INF —
from rtpbin's documented latency propagation; audit note].

**Interview trap.** "Why does our pipeline have two seconds of lag?" First
answer: `rtspsrc latency` defaults to 2000 ms. Set it to 100–300 ms on a LAN
[INF].

### 7.2 Policy: what should be dropped

For a live alarm pipeline the principle is **freshness beats completeness**
[INF]:

1. **Never block the network reader.** A blocked `rtspsrc` over TCP stops
   reading the socket; the camera's buffer fills and the camera drops frames
   (or disconnects) where you cannot see it. Put a `leaky=downstream` queue
   directly after decode.
2. **Drop old, not new** (`leaky=downstream`): an alarm on a frame from 3 s ago
   is, under i-LIDS rules, probably already a false alarm.
3. **Drop at the cheapest point.** Drop decoded frames before colour
   conversion and inference, never compressed packets before decode (breaks the
   reference chain → smearing until next IDR).
4. **Degrade uniformly, not by starvation.** If the GPU is saturated, raise
   `interval` for all streams (5 → 3 fps) rather than letting the slowest
   cameras starve. Report the effective fps per camera as a health metric.
5. **Recording is a separate path.** The VMS records the main stream; the
   analytics path may drop. Evidence integrity never depends on analytics
   keeping up.

### 7.3 Backpressure downstream of inference

If the message broker is down, `nvmsgbroker` must not stall the video
pipeline [INF]. Pattern: local bounded disk spool (e.g. SQLite/WAL or Kafka
producer buffer) with a high-water mark; above it, drop **low-priority
metadata** (per-frame tracks) before **alarms**. Alarms should be idempotent
(stable event ID) so replay after reconnect does not double-count in the
false-alarm metric [INF].

---

## 8. Worked budget: a 40-camera site

### 8.1 Assumptions

| Item | Value | Source |
|---|---|---|
| Cameras | 40 × 1080p, H.265, 25 fps main stream | brief; camera capability per [Axis P3265-LVE](https://www.axis.com/products/axis-p3265-lve/support) (1080p, 50/60 fps, H.264/H.265) |
| Main-stream bitrate | 4 Mbit/s each | **[INF]** — typical VBR figure; Zipstream-class savings vary by scene |
| Analytics sub-stream | 1280×720, 10 fps, H.265, 1 Mbit/s | **[INF]** |
| Detector rate | 5 fps per camera (interval=1 on the 10 fps sub-stream), tracker at 10 fps | [INF], mechanics per [nvinfer](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html)/[nvtracker](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvtracker.html) |
| GOP | 1 s (IDR every 25 frames main, 10 frames sub) | [INF] |

### 8.2 Network

- Main streams to VMS: 40 × 4 = **160 Mbit/s** [INF]. Fine on 1 GbE core;
  watch PoE-switch uplinks (a 24-port switch with 20 cameras is 80 Mbit/s).
- Sub-streams to analytics: 40 × 1 = **40 Mbit/s** [INF].
- RTCP overhead ~5 % per RFC 3550 recommendation
  ([RFC 3550](https://www.rfc-editor.org/rfc/rfc3550)) — negligible.
- Pulling the *main* stream twice (VMS and analytics) doubles camera load; many
  cameras cap concurrent streams. Prefer the VMS re-streaming or the sub-stream
  [INF].

### 8.3 Decode

Option A — decode main streams: 40 × 25 = **1,000 fps of 1080p HEVC**.
- One Turing NVDEC: 1,316 fps HEVC at max clock
  ([NVDEC note](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvdec-application-note/index.html)) →
  76 % utilisation at max clock; at a Max-Q ~70 % clock [INF] it is ~109 % —
  **does not fit on this laptop's RTX 2070 Max-Q**.
- Orin NX 16GB: 18 × 1080p30 H.265
  ([Jetson Orin](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/))
  ≈ 540 fps → two NX boxes would run at ~93 % each (no headroom), so plan
  **three NX boxes** or two AGX Orins (22 × 30 = 660 fps, ~76 % each) [INF
  arithmetic; audit-corrected from "two NX at ~72 %", which used the
  mis-extracted 23-stream figure].

Option B — decode sub-streams: 40 × 10 fps × (720p ≈ 0.44 × 1080p pixels) ≈
**178 1080p-equivalent fps** [INF]. Fits a single NVDEC with large headroom,
or a single Orin NX. **This is why the sub-stream is the design answer.**

### 8.4 Inference

- 40 × 5 = **200 inferences/s**.
- DeepStream reference: AGX Orin PeopleNet+tracker 147 fps end to end
  ([DeepStream performance](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html)).
  200 > 147 → one AGX Orin **does not** carry 40 cameras at 5 fps with that
  model; drop to ~3.5 fps, use a lighter model/INT8, or two boxes [INF].
- L40S reference: 1,114 fps — a single datacentre card carries 40 cameras at
  25 fps with headroom [same source; INF arithmetic]. The edge-vs-server
  decision is therefore about bandwidth, privacy and site power, not raw
  compute.

### 8.5 Latency (glass-to-alarm), sub-stream path

| Stage | Estimate | Basis |
|---|---|---|
| Sensor exposure + ISP + encode | 30–60 ms | [INF] |
| Network (LAN) | 1–5 ms | [INF] |
| Jitter buffer (set *via* `rtspsrc latency` when using rtspsrc; not additive with the next row) | 200 ms standalone default → tune to 100 ms | [rtpjitterbuffer](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpjitterbuffer.html) default; tuned value [INF] |
| `rtspsrc latency` | 2000 ms default → **must** be tuned | [rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html) |
| B-frame reorder | 0 (B-frames off; `low-latency-mode`) | [nvv4l2decoder](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvvideo4linux2.html) |
| Decode | ~5–10 ms | [INF] |
| Mux batch wait | ≤ `batched-push-timeout`, set 100 ms (one 10 fps frame) | [nvstreammux](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvstreammux.html); value [INF] |
| Inference cadence | avg +100 ms (half of 200 ms at 5 fps) | [INF] |
| Inference | 10–30 ms (batched) | [INF] |
| Tracker probation | 3 frames @ 10 fps = 300 ms (first detection only) | parameter per [nvtracker](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvtracker.html); value [INF] |
| Behaviour rule dwell (e.g. loiter) | seconds — by design | [INF] |
| Broker + VMS alarm | 20–100 ms | [INF] |
| **Total to first trackable detection** | **≈ 0.7–1.0 s tuned; ≈ 2.6–2.9 s with defaults** (the 2000 ms replaces, not adds to, the 100 ms jitter row) | [INF] |

The headline: **defaults alone cost ~2 s** — more than the whole remaining
pipeline. Against a 10 s i-LIDS-style window that is survivable; against a
tripwire it is the difference between an alarm and a clip of an empty fence.

### 8.6 Storage (VMS side, for completeness)

160 Mbit/s × 86,400 s / 8 ≈ **1.73 TB/day**; 30 days ≈ 52 TB before RAID
overhead [INF arithmetic]. Retention is a legal question (report 44), not an
engineering default.

---

## 9. VMS integration

The analytics server is not the product the operator uses; the VMS is. An
interviewer from a company that sells into control rooms will expect specifics.

### 9.1 Milestone XProtect (MIP SDK)

- **Analytics Events** can be sent as raw XML to the event server's Analytics
  Receive port (**default 9090**) or as an HTTP POST
  ([MIP SDK — Analytics Event and MAD protocol](https://doc.developer.milestonesys.com/mipsdk/reference/protocols/analytics_and_mad_events.html),
  fetched 2026-09-26).
- The **`Message` element in the `EventHeader`** "is used to match against the
  alarm definition" — i.e. whether an alarm fires is configured in XProtect's
  Management Client, not by the sender (same source).
- Pass a **zero GUID** as the event ID and the server assigns one (same
  source). Source is identified by camera IP or Fully Qualified ID.
- **Bounding boxes are normalised 0–1** (Top/Left/Bottom/Right) (same source).
- Responses: 200 (including "device/message not known" as a warning — so a 200
  does *not* prove the alarm fired), 400 bad XML, 403 not authorised, 500
  (same source). **Health check: treat "200 + unknown device" as a failure.**
- **Metadata streams**: XProtect ingests metadata from cameras or MIP-SDK
  analytics services and the recording server stores it alongside video; the
  format is the ONVIF MetadataStream XML; Smart Client draws ONVIF bounding
  boxes natively; developers should "close the MetadataStream XML document as
  soon as possible, preferably within one RTP packet"; metadata search is a
  Smart Client plug-in
  ([MIP SDK — Introduction to metadata](https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html),
  fetched 2026-09-26).
- **Generic Events** (a string over TCP/UDP) are the simplest integration and
  "can work well for smaller installations" (Milestone MIP docs, summarised via
  search 2026-09-26:
  [Protocol integrations (Events)](https://doc.developer.milestonesys.com/mipvmsapi/api-overview/integrations/events/)).

### 9.2 Genetec Security Center

Genetec's SDK is gated behind the **Development Acceleration Program (DAP)**;
joining gives SDK documentation, installer and a development licence. The
Security Center SDK comprises the **Platform SDK** (entities, events,
reporting — the base for the others), **Media SDK** (streaming, playback, PTZ),
**Web SDK**, and **Workspace SDK** (Security Desk / Config Tool UI extensions)
([Genetec/DAP on GitHub](https://github.com/Genetec/DAP) and
[Security-Center-SDK-Samples](https://github.com/Genetec/Security-Center-SDK-Samples),
via search 2026-09-26; [developer.genetec.com](https://developer.genetec.com/)
fetched 2026-09-26 but the landing page states only that API/SDK docs are
available).

### 9.3 Integration design choices [INF]

| Choice | When |
|---|---|
| ONVIF Profile M metadata + events | Vendor-neutral; works with any M-conformant VMS; least bespoke code |
| Milestone Analytics Event (port 9090 XML) | Fast win on XProtect sites; alarm rules owned by the customer |
| Milestone MIP plug-in / Genetec Workspace SDK | When you need custom UI (e.g. ReID search panel) — highest cost, per-version maintenance |
| Webhook/MQTT to PSIM | Multi-VMS estates; PSIM correlates |

The strategic point: **alarm definitions live in the VMS**, so an analytics
vendor's false-alarm rate is partly controlled by how the integrator configured
alarm matching. Evaluation must be done at the VMS alarm, not at the model
output [INF, consistent with corpus principle 4].

---

## 10. Edge-to-cloud message design

### 10.1 Three message classes [INF]

| Class | Rate | Size | Delivery | Example |
|---|---|---|---|---|
| **Alarm** | rare (target ≪ 1/camera-hour) | ~1–5 kB + clip ref | at-least-once, idempotent, persisted | `intrusion`, `loiter`, `tamper` |
| **Track summary** | per track end | ~1 kB | at-least-once, best effort under backpressure | trajectory, appearance embedding ref |
| **Telemetry/health** | every 10–60 s per camera | < 1 kB | lossy acceptable | fps, decode errors, skew |

Per-frame detections should **not** leave the site by default: 40 cameras ×
5 fps × ~20 objects × ~100 B ≈ 400 kB/s ≈ 35 GB/day of low-value data, and it
is personal data (report 44) [INF arithmetic].

### 10.2 Alarm message fields [INF]

```json
{
  "event_id": "uuid-v7",            // stable, for idempotent replay
  "site_id": "…", "camera_id": "…",
  "rule": "loiter", "rule_version": "2026.09.1", "model_version": "det-…",
  "t_event_start": "…Z", "t_event_trigger": "…Z", "t_emitted": "…Z",
  "clock_source": "rtcp_sr|arrival", "clock_skew_ms": 12,
  "track_ids": [..], "bbox_norm": [l,t,r,b],
  "confidence": 0.83, "evidence": {"clip_uri": "vms://…", "pre_s": 10, "post_s": 5},
  "health": {"eff_fps": 4.8, "dropped_frames_pct": 0.3}
}
```

Rationale for each non-obvious field:
- **three timestamps** — `t_event_start` (behaviour began), `t_event_trigger`
  (rule fired), `t_emitted` (left the box). i-LIDS-style scoring needs
  trigger − start; latency monitoring needs emitted − trigger.
- **clock_source/skew** — lets the cloud discard or down-weight events from a
  camera whose clock is wrong (§5).
- **rule/model version** — alarm-rate regressions are almost always a deploy;
  you cannot bisect without versions (report 21/22).
- **health snapshot** — an alarm from a camera running at 1 fps is less
  trustworthy; make it visible to the verifier.
- **bbox normalised** — matches Milestone's convention (§9.1), resolution-free.

### 10.3 Transport [INF]

MQTT (with QoS 1 and a persistent session) for constrained sites; Kafka for
server rooms with many producers — both available out of the box in
`nvmsgbroker`
([Gst-nvmsgbroker](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvmsgbroker.html)).
Profile M also allows events over MQTT
([Profile M](https://www.onvif.org/profiles/profile-m/)), which gives a
standards-based story.

---

## 11. Failure modes and health metrics

### 11.1 Failure catalogue [INF unless cited]

| Failure | Symptom | Detection metric |
|---|---|---|
| RTSP session timeout (no keep-alive) | stream dies at ~60 s | reconnects/hour ([RFC 7826](https://www.rfc-editor.org/rfc/rfc7826) 60 s default) |
| UDP blocked → TCP fallback | +5 s start delay, higher latency | transport type per camera ([rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html) 5 s UDP timeout) |
| Packet loss in I-frame | smearing until next IDR | RTP seq gaps; decode error count |
| TCP head-of-line stall | periodic freezes, then bursts | inter-frame arrival p99 |
| Default 2 s latency | alarms late | glass-to-alarm probe (§11.3) |
| One camera dead in a batch | whole site slows by timeout | per-source last-frame age |
| GPU saturated | effective fps falls unevenly | eff_fps per camera vs target |
| NVDEC saturated | decode queue grows, latency climbs | decoder utilisation (nvidia-smi `dec`) |
| Camera clock drift / NTP ignored | cross-camera association fails | RTCP-SR time − receiver NTP |
| Camera reboot / encoder change | resolution or codec switch mid-stream | caps renegotiation events |
| Night mode switch | detector recall drops, bitrate spikes | bitrate step + IR flag; alarm-rate shift |
| Tamper (moved / covered / defocused) | valid stream, useless pixels | image-statistics checks on I-frames (§3.4 — the one good use of I-frame-only) |
| Broker down | alarms queued or lost | spool depth; oldest-unsent age |
| VMS "200 but unknown device" | alarm silently not raised | parse response, not status code ([MIP SDK](https://doc.developer.milestonesys.com/mipsdk/reference/protocols/analytics_and_mad_events.html)) |
| Engine file mismatch after driver update | pipeline fails to start or rebuilds engine for minutes | startup time, engine-build events |

### 11.2 The five health metrics to put on one dashboard [INF]

1. **Per-camera effective analysed fps** vs target.
2. **Last-frame age** per camera (seconds since newest analysed frame).
3. **Glass-to-alarm latency p50/p99** (synthetic probe, below).
4. **Alarms per camera-hour**, by rule, against the operator budget — the
   corpus's core operational metric; a step change is usually a camera or
   deploy change, not a behaviour change.
5. **Clock skew** per camera.

### 11.3 Synthetic end-to-end probe [INF]

Scheduled, known events are the only way to measure glass-to-alarm latency in
production: e.g. a PTZ preset move to a scene with a fixed test target, or an
on-screen timestamp overlay compared with the alarm timestamp. This is also
where SurvSim fits: a simulator can **inject known events with known ground-
truth times into a real pipeline** (rendered frames served over RTSP), turning
latency and dropped-frame behaviour into a regression test.

### 11.4 What SurvSim would add (not built) [INF]

- A `transport` degrade stage: FU-A packet loss with GOP-aware error
  propagation, jitter, TCP stalls, per-camera clock offset/drift.
- Serve renders over RTSP (e.g. GStreamer `rtsp-server`) so a DeepStream graph
  under test consumes them unchanged.
- Score with i-LIDS timing using `t_event_start` from ground truth and
  `t_event_trigger` from the pipeline — making "defaults cost 2 s" a failing
  test instead of an anecdote.

---

## 12. Likely interview questions (with short answers)

1. **"Why is our alarm 2 seconds late?"** — `rtspsrc` defaults to 2000 ms
   latency; jitter buffer 200 ms; then check B-frames, mux timeout, probation.
2. **"Can we save compute by only inferring on I-frames?"** — Decode yes,
   tracking no: GOP 50 @ 25 fps = 0.5 fps, below the ~3 fps tracking cliff.
   Use I-frames for tamper/scene checks; use `interval` + tracker for tracking.
3. **"How many cameras per GPU?"** — Two ceilings: NVDEC (Turing ~1,316 fps
   1080p HEVC per engine at max clock) and inference (AGX Orin PeopleNet +
   tracker 147 fps). Usually inference binds first; use sub-streams.
4. **"H.264 or H.265?"** — H.265 halves bandwidth-ish [INF] and, on NVDEC,
   decodes *faster* (Turing 1,316 vs 771 fps). Profile T standardises H.265.
5. **"How do you sync 12 cameras?"** — NTP on cameras, RTCP SR mapping, never
   arrival time; monitor skew; PTP only for triangulation.
6. **"One camera goes offline — what happens?"** — Without a sensible
   `batched-push-timeout`, the batch stalls; with it, the batch ships short.
   Alert on last-frame age.
7. **"How would you integrate with Milestone?"** — Analytics Event XML to port
   9090 with a `Message` matching a customer-defined alarm; ONVIF MetadataStream
   for overlays and search; parse responses for "unknown device".
8. **"What leaves the site?"** — Alarms and health, not per-frame detections;
   bandwidth and data-protection reasons.
9. **"How do you ship a new model without downtime?"** — `nvinfer` supports
   on-the-fly engine file update; version-tag every alarm; canary one camera
   group and watch alarms/camera-hour.
10. **"What is ONVIF Profile S?"** — Basic streaming; *being deprecated* (last
    conformance submissions 31 March 2027). Say T + M.

---

## Citation list (all fetched 2026-09-26)

1. RFC 7826 — RTSP 2.0 — https://www.rfc-editor.org/rfc/rfc7826
2. RFC 3550 — RTP — https://www.rfc-editor.org/rfc/rfc3550
3. RFC 6184 — RTP payload for H.264 — https://www.rfc-editor.org/rfc/rfc6184
4. RFC 5905 — NTPv4 — https://www.rfc-editor.org/rfc/rfc5905
5. IEEE 1588-2008 abstract — https://standards.ieee.org/standard/1588-2008.html
6. ONVIF Profile S — https://www.onvif.org/profiles/profile-s/
7. ONVIF Profile T — https://www.onvif.org/profiles/profile-t/
8. ONVIF Profile M — https://www.onvif.org/profiles/profile-m/
9. ONVIF blog, Milestone Profile M (via search) — https://www.onvif.org/blog/2022/02/02/milestone-adds-profile-m-support-for-xprotect-plat/
10. NVIDIA NVDEC Application Note (Video Codec SDK 13.0) — https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvdec-application-note/index.html
11. NVIDIA encode/decode support matrix — https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new
12. NVIDIA Jetson Orin specifications — https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/
13. NVIDIA Jetson modules — https://developer.nvidia.com/embedded/jetson-modules
14. DeepStream Gst-nvstreammux — https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvstreammux.html
15. DeepStream Gst-nvinfer — https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html
16. DeepStream Gst-nvtracker — https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvtracker.html
17. DeepStream Gst-nvvideo4linux2 — https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvvideo4linux2.html
18. DeepStream Gst-nvmsgbroker — https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvmsgbroker.html
19. DeepStream performance — https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html
20. GStreamer rtspsrc — https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html
21. GStreamer rtpjitterbuffer — https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpjitterbuffer.html
22. GStreamer queue — https://gstreamer.freedesktop.org/documentation/coreelements/queue.html
23. Milestone MIP SDK — Analytics Event and MAD protocol — https://doc.developer.milestonesys.com/mipsdk/reference/protocols/analytics_and_mad_events.html
24. Milestone MIP SDK — Introduction to metadata — https://doc.developer.milestonesys.com/mipsdk/gettingstarted/intro_metadata.html
25. Milestone MIP — Protocol integrations (Events) (via search) — https://doc.developer.milestonesys.com/mipvmsapi/api-overview/integrations/events/
26. Genetec Developer — https://developer.genetec.com/
27. Genetec DAP / SDK samples (via search) — https://github.com/Genetec/DAP ; https://github.com/Genetec/Security-Center-SDK-Samples
28. Axis P3265-LVE datasheet — https://www.axis.com/products/axis-p3265-lve/support

**Not obtained:** ITU-T H.264 recommendation page (HTTP 500 on 2026-09-26);
GOP/B-frame mechanics are therefore tagged [INF]. The Jetson AGX Orin decode
row was re-fetched in the 2026-09-26 audit and the table corrected (NX 16GB = 18× 1080p30).
