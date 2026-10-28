# 22 · Deployment & Operations — sizing, video pipeline, resilience, operator workflow, SLAs, cost

*Series 17–23. D04 already maps the physical architecture (camera → network →
VMS → edge/cloud → messaging → C2) and gives three sized reference
architectures. This report adds what D04 does not cover: sizing arithmetic for
the analytics, a concrete GStreamer/DeepStream pipeline and its config, the
message and health schemas, how to handle resilience, the operator workflow,
SLAs, a vendor comparison, and a per-camera cost model. It ends with a
checklist of what SurvSim must emit to test all of it.*

**Sourcing conditions (revised 2026-09-26).** Every hardware, software and
price figure has been checked against the reference given in §13, fetched on
2026-09-26. Figures that could not be confirmed have been removed or are
marked **[unverified]**. Price information from resellers or third-party
aggregators, rather than the vendor, is marked **[secondary]**. Arithmetic
is tagged **[BOE]** and shows its inputs; inference is **[INF]**;
practitioner knowledge is **[lore]**. Prices are in USD as published unless
stated otherwise. Jetson list prices rose 57–101 % in July 2026 [R9], so any
Jetson figure from before that date understates today's cost.

---

## 0. Summary

* **Decode is often the first bottleneck, not inference.** A T4 is specified
  to decode "up to 38 full-HD video streams" [R4]. At 10 inference fps, a small
  detector on the same card can serve about 40 streams [BOE, §1.1]. So decode
  and compute run out at roughly the same point, and decode sessions have to
  be sized as carefully as TOPS.
* **Streams per device, 1080p input analysed at 10 fps with a small detector
  [BOE].** Jetson Orin Nano: 4–8. Orin NX 16 GB: 8–16. AGX Orin: 14–22
  (decode-capped at 22× 1080p30 H.265 [R3]). One T4/L4-class card: 30–60.
  These are estimates. §1 shows how they were derived and §11 lists them as
  things to measure.
* **DeepStream (GStreamer + TensorRT) is the default production pipeline on
  NVIDIA hardware** [R5]. Intel's equivalent is DL Streamer, which runs on
  OpenVINO [R11]. Savant offers a Python layer over DeepStream, with 0.5.x as
  the production release on DeepStream 7.0 [R12].
* **Health monitoring is a product feature.** A blinded camera produces no
  output, and silence looks exactly like a quiet scene (SurvSim principle 2).
* **SLAs cover availability and alarm latency.** Accuracy is contracted as a
  verified performance envelope (report 21 §10).
* **Cost.** Analytics hardware amortises to roughly $100–200 per camera per
  year on-prem [BOE, §8]. VMS licences alone cost around $110–250 per camera
  one-off (retail/third-party figures, not vendor lists), or $149–199 per camera per year as Genetec SaaS [R14–R16, secondary].
  People (commissioning and support) usually cost more than hardware.

---

## 1. Hardware sizing

### 1.1 Compute per stream

Measured by the vendor, from the Ultralytics YOLO11 table [R1], COCO val at
640 px on a T4 with TensorRT 10:

| Model | mAP50-95 | T4 TRT latency | Params | FLOPs |
|---|---|---|---|---|
| YOLO11n | 39.5 | 1.5 ms | 2.6 M | 6.5 G |
| YOLO11s | 47.0 | 2.5 ms | 9.4 M | 21.6 G |
| YOLO11m | 51.5 | 4.7 ms | 20.1 M | 68.1 G |
| YOLO11l | 53.4 | 6.2 ms | 25.3 M | 87.2 G |
| YOLO11x | 54.7 | 11.3 ms | 56.9 M | 195.3 G |

**[BOE] Streams per T4 with YOLO11s.** At 2.5 ms per inference (batch 1) the
card does 400 inferences/s, which is 40 streams at 10 fps. Batching usually
gains another 1.5–3× [lore]. At 1280 px, the small-object mode recommended in
report 18, there are 4× the pixels, so expect roughly ¼–⅓ of that: 10–15
streams per T4 before batching. The "small-object mode everywhere" design is
therefore about 3× more expensive than 640 px. Use 1280 px only on cameras
whose far field matters, as `survsim rig`'s pixel-height analysis should
decide.

**ReID.** OSNet x1.0 costs about 1 G multiply-adds (≈ 0.98 G, 2.2 M params) per 256×128
crop (Zhou et al., ICCV 2019 [R17]). Assume 10 tracks per view and 2 crops per
track per second. That is 20 G multiply-adds ≈ 40 GFLOP/s per stream, about
19 % of YOLO11s at 10 fps (216 GFLOP/s; Ultralytics FLOPs count 2 per MAC) [BOE].

**Tracker.** ByteTrack-class association runs on the CPU and is under 1 ms per
frame at CCTV densities. docs/13 measured the repo's Python `ByteTracker` at
about 6 ms per frame on full MOT20 (46–195 boxes per frame, 55.7 s for 8,931
frames) and explicitly retracted an earlier, unmeasured "O(n²) association is
the bottleneck" diagnosis.

### 1.2 Decode capacity (vendor-verified)

| Device | Video decode as published | Source |
|---|---|---|
| NVIDIA T4 (70 W) | "decode up to 38 full-HD video streams" | [R4] |
| NVIDIA A2 (40–60 W) | 2 NVDEC (incl. AV1), 1 NVENC | [R6] |
| NVIDIA L4 (72 W) | 4 NVDEC, 2 NVENC, 4 JPEG decoders; "up to 1,040 concurrent AV1 720p30 streams" in an **8-GPU server** (≈130 per card) | [R2] |
| Jetson Orin Nano 8 GB | 11× 1080p30 H.265 | [R3] |
| Jetson Orin NX 16 GB | 18× 1080p30 H.265 (the 23× figure is the AGX Orin Industrial) | [R3] |
| Jetson AGX Orin 64 GB | 22× 1080p30 H.265 | [R3] |

Most installed CCTV cameras stream H.264. NVDEC's H.264 throughput is
generally a little below its H.265 throughput, and vendor figures are
best-case [lore]. Plan for 70 % of the published count [INF]. To reconstruct
P/B frames, every frame has to be decoded even when inference runs on only
one in k. I-frame-only decoding (skipping P/B) is roughly GOP-length times
cheaper, but it limits analysis to the I-frame rate (0.5–1 fps at typical
GOPs). That is fine for occupancy counting and unusable for tracking, which
fails below about 3 fps (R01).

### 1.3 Accelerators and on-camera compute (public specs)

| Device | AI compute (vendor figure) | Power | Public price | Notes |
|---|---|---|---|---|
| Jetson Orin Nano 8 GB | 67 sparse INT8 TOPS ("Super" mode; 40 before the JetPack 6.2 uplift [unverified]) | 7–25 W | Super dev kit $399 (was $249) | [R3], [R9] |
| Jetson Orin NX 16 GB | 157 sparse INT8 TOPS | 10–40 W | module price not published on NVIDIA page | [R3] |
| Jetson AGX Orin 32 GB module | — | [unverified] (NVIDIA page power row is ambiguous) | $1,799 (was $899) | [R9] |
| Jetson AGX Orin 64 GB | 275 sparse INT8 TOPS | 15–60 W | dev kit $3,499 (was $1,999); module +88 % | [R3], [R9] |
| NVIDIA T4 | 65 FP16 TFLOPS, 130 INT8 TOPS, 16 GB | 70 W | server-OEM | [R4] |
| NVIDIA A2 | 36 INT8 TOPS dense (72 sparse), 16 GB | 40–60 W | server-OEM | [R6] |
| NVIDIA L4 | 485 INT8 TOPS *with sparsity*, 242 FP16 TFLOPS sparse, 24 GB, 300 GB/s | 72 W | cloud ≈ $0.70/h on GCP G2 | [R2], [R10] |
| Hailo-8 (M.2) | 26 TOPS, typical 2.5 W | 2.5 W | ~$200–275 retail (2026-09 listings) | [R7], [R18] |
| Axis ARTPEC-8 DLPU | not published: Axis says speed depends on the model and points to its model-zoo benchmarks | in-camera | in camera price | [R8] |
| Ambarella CV72S | 5 nm, 4K, "6× AI performance of predecessor" | < 3 W | OEM | [R19] |

Two cautions. First, NVIDIA's headline TOPS figures assume 2:4 structured
sparsity, which a standard YOLO export does not use, so halve them for
realistic comparisons. Second, TOPS figures from different vendors are not
comparable. The only honest comparison is measured end-to-end fps for *your*
model at *your* input size, taken from the same harness (docs/13's
`survsim baseline` run against the exported engine; report 18 §8).

DeepStream's own performance page publishes end-to-end fps rather than stream
counts [R5]. For example, PeopleNet 2.6.3 at 640×640 FP16 runs at 147 fps on
Jetson AGX Orin (with the MV3DT tracker), and RT-DETR with the NvDCF tracker at 96 fps. At 10 fps per
camera, 147 fps is about 14 cameras on an AGX Orin with a 640 px detector.
That fits the 16–22 estimate above only if the model is smaller than
PeopleNet or batching helps [BOE].

### 1.4 Sizing table used in this report

| Tier | Example | Streams (1080p in, 10 fps, YOLO11s-class @ 640, tracker, sampled ReID) [BOE] | Binding limit |
|---|---|---|---|
| On-camera | ARTPEC-8, CV72S | 1 (its own), model-restricted | DLPU model support |
| Small edge | Orin Nano 8 GB | 4–8 | compute |
| Mid edge | Orin NX 16 GB | 8–16 | compute |
| Large edge | AGX Orin 64 GB | 14–22 | decode (22×1080p30) / compute |
| Server card | T4 | 30–40 | decode (38 FHD) ≈ compute |
| Server card | L4 | 40–60 | compute (4 NVDEC is ample) |
| Server | 2U, 4× L4 | 160–240 | CPU, PCIe, network |

### 1.5 Other resources [lore/BOE]

* **CPU:** 0.1–0.2 cores per stream for RTSP, demux, tracking and bus clients.
* **GPU memory:** about 50–100 MB per 1080p stream for decode surfaces and
  batching buffers. The L4's 24 GB is not the limit.
* **Network:** 2–6 Mb/s per 1080p H.264 stream. 200 cameras need about
  0.4–1.2 Gb/s, so use 10 GbE uplinks to the analytics nodes.
* **Metadata storage:** 20 objects × 10 fps × 60 bytes ≈ 12 kB/s ≈ 31 GB per
  camera per month uncompressed. Columnar compression (Parquet/zstd) typically
  cuts that 5–10× [BOE]. Keep full-rate metadata for 30 days and downsampled
  tracks for longer, subject to the retention policy (report 21 §7.4).
* **Alarm clips:** 15 s at 4 Mb/s ≈ 7.5 MB each.

### 1.6 SurvSim's development machine is not a sizing reference

The 8 GB RTX 2070 Max-Q (CLAUDE.md) is a Turing laptop part. The repo keeps
capture at 720p with at most 12 hero agents, and ue_job fails any render over
7,200 MB of VRAM (commit d57db8c). Throughput measured on it says nothing
about deployment hardware [INF].

---

## 2. Worked sizing on our own scenarios

### 2.1 `configs/scenarios/disguise_and_tamper.yaml`

| Camera | Type | Resolution | fps | Notes from the YAML |
|---|---|---|---|---|
| cam_gate | fixed bullet, 70° HFOV, 4.5 m | 1920×1080 | 10 | gate: tailgating and loitering |
| cam_yard | dome, 95° HFOV, 5.0 m | 1280×720 | 10 | wide yard |
| cam_sub | fixed bullet, 60° HFOV, 4.0 m | 1920×1080 | 10 | **sprayed at t = 150 s**, blind afterwards |
| cam_ptz | PTZ, 3–60° HFOV, 9.0 m | 1920×1080 | 10 | slews on cue |

**Load:** 4 streams × 10 fps = 40 inferences/s at 640 px. With YOLO11s that
is 40 × 21.6 G ≈ 0.86 TFLOP/s. Decode is 3× 1080p + 1× 720p at 10 fps, well
inside an Orin Nano's 11× 1080p30 [R3] [BOE].

**Deployment:** a single Orin Nano 8 GB box, or an Orin NX for headroom to
run the gate camera at 1280 px. The substation-perimeter site class this
scenario represents is usually remote with thin backhaul, which argues for
edge placement and sending only metadata and alarm clips upstream (report 17
§7).

**What this scenario tests beyond sizing:**

1. **Tamper handling.** From t = 150 s, cam_sub's detections must stop. The
   health pipeline must raise `camera.tamper{kind: spray}` within the SLA
   (§6). `survsim rig` can report which zones lost coverage.
2. **PTZ state.** Rules on cam_ptz defined in image space must pause while it
   slews. Cue-to-acquire latency goes against the ≤ 2 s budget (report 17 §5).
3. **Hard negatives.** The worker has to be suppressed by role or context,
   not by lowering sensitivity.

### 2.2 `configs/scenarios/street_crowd.yaml`

Three cameras (cam_01–03), all 1280×720 at 10 fps. Population: two heroes at
gate_A with identical 25 s dwell (`loiterer_1` loiter, `commuter_1`
`commute_wait`), plus generated 12 passers-by in the yard, 3 `commute_wait`
hard negatives at gate_A (dwell 20–40 s), and 1 loiterer at gate_A (30–50 s).

**Load:** 30 inferences/s at 720p, about 0.65 TFLOP/s with YOLO11s. One Orin
Nano is enough [BOE].

**Operationally,** this is the loitering precision test. With a dwell
threshold T ≤ 20 s, all four commuters alarm. With T = 30 s, the 25 s hero loiterer never
alarms, and the generated loiterer alarms only on draws where their dwell
exceeds 30 s by more than the persistence window. That makes it the smallest scenario in the repo where
the dwell/persistence setting visibly trades Pd against false alarms. Run it
with `survsim eval --threshold-s` for i-LIDS timing.

**Scaling [BOE]:** a transport concourse with 60 cameras like these is
60 × 10 = 600 inferences/s ≈ 13 TFLOP/s effective. That is two L4 cards with
margin, or a single 4× L4 server kept N+1 by spreading load across cards.

### 2.3 A 200-camera estate (the cost-model case, §8)

Assume 150 cameras at 1080p and 50 at 720p, 10 fps, YOLO11s at 640 px, with
20 wide-area cameras at 1280 px.

* Inference load: 180 × 10 × 21.6 G + 20 × 10 × 86 G ≈ 56 TFLOP/s
  effective.
* Throughput: about 45 streams per L4 at 640 px, with the 1280 px streams
  counted as 3× cost. That gives 180 + 60 = 240 stream-equivalents, so 6 L4s.
  Decode is comfortable at 4 NVDEC per card.
* Hardware: two 4× L4 servers (8 cards), leaving N+1 headroom.

---

## 3. The video pipeline

### 3.1 DeepStream reference graph

```
nvurisrcbin (RTSP, rtsp-reconnect-interval) ×N
   → nvstreammux (batch-size N, width/height, live-source=1, attach NTP ts)
   → nvinfer  (PGIE: detector engine, interval=k)
   → nvtracker (NvDCF / NvDeepSORT / IOU, or custom low-level lib)
   → nvinfer  (SGIE: ReID/attributes on objects, classifier-async-mode)
   → nvdsanalytics (ROI, line-crossing, overcrowding, direction)
   → nvmsgconv → nvmsgbroker (Kafka / MQTT / AMQP / Redis adaptors)
   → [debug] nvstreamdemux → nvdsosd → encoder → RTSP out
```
DeepStream documentation: [R5]. The `interval` parameter on `nvinfer`
decodes every frame but infers only every (k+1)-th, with the tracker
interpolating between. `nvdsanalytics` handles image-space ROI and line
rules. Ground-plane, cross-camera and context logic (report 19) belongs
downstream on the bus.

### 3.2 A concrete configuration

A DeepStream-style application config for the four-camera
`disguise_and_tamper` site. Keys follow DeepStream's documented group/key
format; values are the ones this report recommends.

```ini
[application]
enable-perf-measurement=1
perf-measurement-interval-sec=10

[source0]            # cam_gate
enable=1
type=4               # RTSP
uri=rtsp://mediamtx:8554/cam_gate
rtsp-reconnect-interval-sec=5
latency=200
select-rtp-protocol=4   # TCP interleaved on lossy links
# source1..3 identical for cam_yard, cam_sub, cam_ptz

[streammux]
batch-size=4
width=1280
height=720
live-source=1
batched-push-timeout=40000
attach-sys-ts-as-ntp=0   # use RTCP sender-report NTP, not local clock

[primary-gie]
enable=1
config-file=pgie_yolo11s_fp16.txt
interval=0              # 10 fps sources: infer every frame
gie-unique-id=1

[tracker]
enable=1
ll-lib-file=/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so
ll-config-file=config_tracker_NvDCF_accuracy.yml
tracker-width=960
tracker-height=544

[secondary-gie0]
enable=1
config-file=sgie_osnet_reid.txt
operate-on-gie-id=1
operate-on-class-ids=0

[nvds-analytics]
enable=1
config-file=analytics_zones.txt

[message-converter]
enable=1
msg-conv-payload-type=1   # minimal schema; we remap to ours below

[message-broker]
enable=1
proto-lib=/opt/nvidia/deepstream/deepstream/lib/libnvds_mqtt_proto.so
conn-str=broker.site.local;1883
topic=site/demo/det
```
Treat this as a template to check against the installed DeepStream
version's reference configs, not a drop-in file. Key names can change
between releases [INF].

**Timing.** Leaving `attach-sys-ts-as-ntp=1` (stamping frames with the
analytics host clock) is a known cause of multi-camera skew [lore]. RTCP
sender-report timestamps carry the camera's own NTP-synchronised time and
should be used instead. SurvSim's timing sidecars (`survsim/gt/video.py:
plan_timing`, `write_timing_sidecar`, `camera_clock`) inject camera-side
offset and drift, so they are the test vectors for exactly this setting.

### 3.3 Message topics and schema

Use MQTT at the edge and Kafka (or NATS) at the site. Topics are
hierarchical: `site/{site_id}/{kind}/{camera_id}`.

| Topic | Rate | Payload |
|---|---|---|
| `site/{s}/det/{cam}` | per analysed frame | Detection batch (report 17 §3.3) |
| `site/{s}/trk/{cam}` | 1–5 Hz per active track | Tracklet update |
| `site/{s}/gtrk` | ~1 Hz | GlobalTrack revisions |
| `site/{s}/evt` | on event | CandidateEvent |
| `site/{s}/alarm` | on alarm | Alarm (after policy) |
| `site/{s}/health/{cam}` | 0.1 Hz and on change | CameraHealth |
| `site/{s}/node/{node}` | 0.1 Hz | NodeHealth |
| `site/{s}/disposition` | on operator action | Disposition |

```json
// site/demo/health/cam_sub  (JSON shown; protobuf on the wire)
{
  "schema": "camera_health/1",
  "camera_id": "cam_sub",
  "utc_ns": 1790000150000000000,
  "stream": {"up": true, "fps_rx": 10.0, "fps_analysed": 10.0,
             "bitrate_kbps": 3100, "res": [1920, 1080], "decode_errors": 0},
  "clock": {"offset_ms": 42.0, "drift_ppm": 3.1, "source": "rtcp_sr"},
  "iqa": {"noise_sigma": 0.31, "lap_var_log10": 1.12, "mtf_ratio": 0.004,
          "edge_width": 9.8, "luma_mean": 96.0, "blockiness": 1.02},
  "tamper": {"state": "suspected", "kind": "spray", "since_utc_ns": 1790000151200000000,
             "score": 0.93},
  "calibration": {"valid": true, "residual_m": 0.21},
  "producer": {"name": "iqa-tamper", "version": "0.4.2", "config_hash": "9f1c…"}
}
```
The IQA field names are deliberately the ones in `survsim/realism/stats.py`
(docs/15), so production telemetry and simulator realism statistics can be
compared directly [INF].

```json
// site/demo/alarm
{
  "schema": "alarm/1", "alarm_id": "a-000731", "revision": 0,
  "type": "suspicious.loiter", "priority": 2,
  "zone_id": "zone.gate_A", "subjects": ["g-118"],
  "t_event_start_utc_ns": 1790000030000000000,
  "t_detectable_utc_ns": 1790000060000000000,
  "t_raised_utc_ns": 1790000064100000000,
  "evidence": [{"camera_id": "cam_gate", "pts_from": 300, "pts_to": 700,
                "bbox_track": "trk/cam_gate/57"}],
  "corroboration": [{"sensor": "cam_ptz", "kind": "visual", "score": 0.71}],
  "policy_trace": ["threshold:0.62>0.5", "context:armed", "persistence:4.1s",
                   "corroboration:1", "budget:ok(0.08/cam-h)"],
  "producers": {"detector": "yolo11s-demo-2.1+trt10-fp16",
                "tracker": "nvdcf-acc-7.1", "rules": "loiter-v3@c0ffee"}
}
```
`policy_trace` mirrors the stages of SurvSim's `eval/pipeline.py`
(threshold → context → persistence → corroboration → budget). The field is
what makes an alarm explainable to an operator and reproducible to an
auditor.

### 3.4 Alternatives to DeepStream

* **Intel DL Streamer.** GStreamer plus OpenVINO for Intel CPU, GPU and NPU.
  It is now part of Intel's Open Edge Platform and includes a Pipeline Server
  that exposes REST-managed pipelines as microservices [R11].
* **Savant.** A Python framework over DeepStream. 0.5.x is the production
  release on DeepStream 7.0; 0.6.x is in development on DeepStream 7.1 /
  TensorRT 10.9 with Blackwell support [R12].
* **Triton Inference Server** [R13], for many models sharing GPUs centrally,
  such as a VLM verifier on triggered clips.
* **FFmpeg/PyAV + ONNX Runtime/TensorRT.** Fine below about 16 streams and
  for research. At scale it ends up re-implementing batching and zero-copy.

### 3.5 Testing the pipeline with SurvSim

`survsim/gt/video.py` already writes per-camera video (`write_video`), timing
sidecars (`write_timing_sidecar`) and ONVIF-style metadata
(`onvif_metadata`), and `export_camera` packages them. `rtsp_command` returns
the command to serve a camera over RTSP on port 8554; running the server is
left to the caller (docs/11). **The hardware-in-the-loop rig [INF]:**
mediamtx [R20] serves the degraded SurvSim streams, the pipeline above
consumes them, and a scorer subscribes to `site/+/alarm` and
`site/+/health/+` and compares against `events.jsonl` and the tamper
schedule. This measures latency, reconnect behaviour and clock-skew effects
end to end. It is milestone M3 in report 23.

---

## 4. Resilience

| Failure | Design response |
|---|---|
| Camera stream lost | reconnect with backoff (`rtsp-reconnect-interval-sec`); mark the gap in metadata; camera-health alarm after N s |
| Analytics node fails | N+1 nodes; a scheduler (K3s/Kubernetes or vendor fleet manager) reassigns streams; track state is lost and rebuilds within seconds |
| Site server fails (association/alarms) | active/passive pair; bus retention (Kafka) allows replay |
| Bus outage | edge buffers to disk and replays; delayed alarms carry a `delayed=true` flag |
| WAN outage to the SOC | local alarm handling continues; store and forward |
| GPU fault or thermal throttle | DCGM telemetry on servers, tegrastats/jtop on Jetson; shed load by lowering inference rate on low-priority cameras |
| Bad model release | staged rollout (shadow → canary → all); instant rollback to the previous signed artefact |
| Clock failure | NTP/PTP monitoring; alarm when skew > 200 ms |
| Power | UPS sized for graceful shutdown; edge boxes with wide-range inputs |

**Order of graceful degradation [INF]:**
1. Lower the analysis fps on low-priority cameras (but not below about 3 fps,
   where tracking fails).
2. Switch off secondary models (attributes).
3. Switch off ReID.
4. Never switch off the primary detector on cameras watching armed sterile
   zones.

Every step down is published as a `NodeHealth.degraded_mode` event, so an
operator knows coverage has changed.

---

## 5. Health monitoring

Metrics are Prometheus-style names, exported per camera:

| Metric | Type | Alert when [INF] |
|---|---|---|
| `cam_stream_up` | gauge 0/1 | 0 for > 30 s on an armed camera |
| `cam_fps_received`, `cam_fps_analysed` | gauge | < 80 % of configured |
| `cam_decode_errors_total` | counter | rate > 1/min |
| `cam_resolution_changed_total` | counter | any increment (firmware reset breaks homography) |
| `cam_latency_ms` (camera→alarm, p95) | histogram | > SLA |
| `cam_iqa_{noise_sigma,lap_var_log10,blockiness,luma_mean}` | gauge | outside the camera's own 30-day band |
| `cam_tamper_state` | enum | ≠ ok |
| `cam_detections_per_min`, `cam_tracks_per_min` | gauge | falls to 0 when the time-of-day baseline says > 0 |
| `cam_track_len_s_median` | gauge | falls by 50 % (fragmentation) |
| `cam_alarms_per_hour{type}` | gauge | over budget |
| `cam_disposition_false_ratio{type}` | gauge | rising trend |
| `cam_calib_residual_m` | gauge | > 0.5 m |
| `node_gpu_util`, `node_gpu_temp_c`, `node_nvdec_sessions`, `node_bus_lag_ms` | gauge | thresholds |

Two alerts do most of the work. `cam_detections_per_min` dropping to zero
against its time-of-day baseline catches blinding. `cam_resolution_changed`
catches the silent firmware reset that invalidates calibration.
`disguise_and_tamper`'s spray at t = 150 s should trip the first within the
tamper SLA.

---

## 6. Operator workflow and UI

### 6.1 Alarm lifecycle

```
raised → presented → acknowledged → assessed (live / clip / PTZ) →
   dispatched | escalated | closed(true | false | nuisance, reason) → audited
```
Every transition is timestamped for SLA reporting and human-factors
analysis, and published on `site/{s}/disposition`.

### 6.2 UI principles

* **One incident, one card.** The card shows a clip (5 s before, 10 s after),
  the subject highlighted, a map pin, the rule and parameters that fired
  (rendered from `policy_trace`), any corroborating sensors, and links to
  nearby cameras.
* **Deduplicate and group** alarms that belong to the same incident.
* **Priority** = zone criticality × event type × number of corroborations.
* **Keyboard-first triage**, with a one-key disposition and a short list of
  reason codes (animal, staff, weather, reflection, system fault).
* **PTZ slew-to-cue** from the card, with auto-follow and manual override.
* **Search.** "This person on other cameras in the last 10 min" (MTMC/ReID),
  attribute search, and natural-language search (R05; `eval/retrieval.py`
  measures recall@k and MRR).
* **Workload guardrail.** Show the alarm rate against the budget. When it goes
  over budget, escalate to a supervisor rather than silently suppressing.

**Vigilance evidence.** Donald, Donald & Thatcher (Applied Ergonomics 47,
2015) found vigilance decrements in novices and generalists on a 90-minute CCTV
task, while specialists held performance for the first hour and then improved;
only about 50 % of target behaviours were detected overall [R21]. (The onset
time is not in the abstract [unverified].) The often
repeated "95 % missed after 22 minutes" figure traces to trade-press
citations of a 2002 study whose primary source could not be located. It has
been dropped here. The design point stands: analytics should shorten
continuous monitoring, not add screens to it.

### 6.3 Escalation matrix (example)

| Alarm | First action | Escalation |
|---|---|---|
| Perimeter breach (intrusion, climb, cut) | PTZ confirm; dispatch guard | police if confirmed; adjacent cameras to high sensitivity |
| Camera tamper | maintenance ticket; flag zones that lost coverage | guard patrol to the camera if a sterile zone is uncovered |
| Loiter / recon indicators | watch list; low-priority queue | supervisor review; share with site security manager |
| Person down | live assess | first aid or ambulance |
| Fight | live assess; audio corroboration | police |
| Crowd density band 4+ | event control | stewarding plan |

Integrate outward through a PSIM or the VMS alarm manager, or through ONVIF
events [R22] (D04 §6).

---

## 7. SLAs

| SLA | Target [INF] | How measured |
|---|---|---|
| Analytics availability per armed camera | ≥ 99.5 % per month | `cam_stream_up ∧ cam_fps_analysed ≥ 0.8×target` |
| Alarm delivery latency | p95 ≤ 10 s from the time the event becomes detectable | injected SurvSim clips over RTSP (§3.5) plus field walk tests |
| Camera-fault notification | ≤ 5 min | health events |
| False-alarm rate | ≤ the agreed rate per camera-hour per analytic, after commissioning | disposition data |
| Detection performance | Pd ≥ agreed within the verified envelope (DORI band, conditions) | periodic walk tests plus the SurvSim regression suite |
| Support response | P1 ≤ 1 h, P2 ≤ 4 h | ticketing |

Periodic walk tests (staff performing scripted intrusions and loiters) are
the field counterpart of SurvSim scenarios, and one scenario definition can
script both [INF].

---

## 8. Vendor landscape and cost

### 8.1 VMS licensing (the platform analytics must integrate with)

| VMS | Licence model | Public price information | Source |
|---|---|---|---|
| Milestone XProtect | per device licence by edition (Essential+, Express+, Professional+, Expert, Corporate) | Milestone does not publish prices (sold via integrators); retailer listings $109–177+ per device licence (Professional+ device licence XPPPLUSDL listed at $177, B&H / education list, checked 2026-09-26) | [R14] (vendor pricing page confirms no public prices) |
| Genetec Security Center | base package + per-camera; SaaS subscription | third-party guide: on-prem camera licence $150–400 one-time + 18–22 %/yr maintenance; SaaS Standard $149, Premium $199 per camera per year | [R15] [secondary] |
| Network Optix Nx Witness | Enterprise (subscription) and Professional (perpetual, select regions); per-channel structure [unverified on FAQ] | prices not published by vendor | [R16] |

Analytics are sold either as a VMS plugin (Milestone MIP SDK, Genetec SDK,
Nx Metadata SDK) or as a standalone product that pulls from the VMS and pushes
alarms back. Plugins are easier to sell and harder to engineer, because each
VMS has its own threading and metadata model [lore; D04].

### 8.2 Cost model: on-prem, 200 cameras (§2.3 sizing) [BOE]

| Item | Qty | Unit | Capex | Annualised over 5 years |
|---|---|---|---|---|
| GPU servers, 4× L4 each | 2 (+1 cold spare) | ~$40,000 [lore; L4 cards are sold through server OEMs] | $120,000 | $24,000 |
| Site server pair (association, alarms, DB) | 2 | $10,000 | $20,000 | $4,000 |
| 10 GbE networking | — | — | $12,000 | $2,400 |
| Power: 2 × 0.8 kW × 8,760 h × $0.30/kWh | — | — | — | $4,200 |
| Commissioning: 1.5 h/camera at $100/h | 200 | $150 | $30,000 | $6,000 |
| Analytics software licence (market range $5–40/camera/month [lore/D03]) | 200 | $240/yr | — | $48,000 |
| Support (15 % of hardware per year) | — | — | — | $22,800 |
| **Total** | | | | **≈ $111,000/yr ≈ $555 per camera per year** |

Hardware comes to about $150 per camera-year. Licence and people dominate.
VMS licences are extra, and usually already owned.

### 8.3 Edge variant, 200 cameras

With Orin NX boxes at about 12 streams each, 17 boxes are needed. Industrial
Orin NX boxes are typically $1,500–3,000 each after the July 2026 Jetson
price increases [R9; box prices lore]. That is $25–50k capex, or $5–10k per
year, plus the site server. Power is lower (17 × 25 W ≈ 0.4 kW).
Distributed boxes cost more to maintain in the field. The trade-off: cheaper
hardware and bandwidth, better suited to remote and air-gapped sites, but
dearer operations [INF].

### 8.4 Cloud variant

On-demand L4 on GCP G2 (g2-standard-4) is about $0.707 per hour in
us-central1 [R10; figure via third-party aggregators, secondary]. At 45 streams per L4, 200 cameras need about 5 instances ×
8,760 h × $0.70 ≈ $30.7k per year for compute [BOE]. Add 200 × 3 Mb/s =
600 Mb/s of continuous uplink and any egress. It is competitive only where
connectivity is cheap and data-protection policy permits.

### 8.5 Where SurvSim reduces cost

* **Commissioning.** `survsim rig` checks pixel density and blind spots.
* **Fewer field walk tests.** Scenario suites pre-validate configurations.
* **Faster false-alarm tuning.** Alarm policies can be pre-tuned per site
  class (the `street_crowd` dwell sweep is the smallest example).

The company should measure these savings on its first three deployments.

---

## 9. Commissioning checklist

1. **Camera survey:** model, lens, mounting height, stream configuration,
   NTP source.
2. **Calibration:** intrinsics from the model library; at least 6 surveyed
   ground points per camera; residual ≤ 0.5 m inside zones.
3. **Pixel density per zone** against the DORI requirement (the `survsim rig`
   equivalent).
4. **Zones and rules** from the site risk assessment, with arming schedules.
5. **Baselines:** IQA bands and tamper reference images.
6. **Walk tests** for each rule type, by day and by night; record Pd and
   latency.
7. **Tuning period** of 2–4 weeks with dispositions; then lock thresholds and
   sign off.
8. **Compliance:** DPIA and signage confirmed (report 21).

---

## 10. What SurvSim must emit to test deployment and operations

| # | Requirement | Module | State |
|---|---|---|---|
| 1 | Per-camera encoded video at the configured resolution and fps | `survsim/gt/video.py: write_video, export_camera` | have |
| 2 | Per-frame timing with camera clock offset and drift | `survsim/gt/video.py: camera_clock, plan_timing, write_timing_sidecar` | have |
| 3 | ONVIF-style analytics metadata alongside video | `survsim/gt/video.py: onvif_metadata` | have |
| 4 | RTSP serving command per camera | `survsim/gt/video.py: rtsp_command` | have (not run) |
| 5 | CCTV-realistic codec with GOP structure | `survsim/sensors/degrade.py: apply_sequence / h264_sequence` | have (docs/15) |
| 6 | Stream faults: freeze, drop, packet-loss corruption, resolution change | `survsim/sensors/degrade.py`, `director/camera_director.py` | drop/freeze partial; **corruption and resolution-change missing** |
| 7 | Tamper schedule and live camera pose (configured vs actual) | `survsim/director/camera_director.py` | have (6 kinds) |
| 8 | Per-frame IQA values matching production telemetry names | `survsim/realism/stats.py` | have, **not yet written as a GT sidecar** |
| 9 | Events with `t_detectable_from` per camera (for latency SLAs) | `survsim/gt/writers.py` (events.jsonl) | **missing** (report 19 §7) |
| 10 | Alarm-policy trace per candidate | `survsim/eval/pipeline.py` | stages exist; **per-alarm trace export missing** |
| 11 | Coverage loss when a camera fails | `survsim rig` | have (static); **time-varying coverage missing** |
| 12 | Operator dispositions (simulated) for SLA and false-alarm reporting | — | **missing** (report 21 §3.4) |
| 13 | Long-duration runs (≥ 8 camera-hours) that don't need rendering | mock backend | have; realism validation pending (report 23 M6) |
| 14 | Scorer that consumes a live bus (MQTT) against GT | — | **missing** (report 23 M3) |

---

## 11. Numbers to replace with measurements

Every [BOE] throughput figure in §1.4 should be replaced by measurement on
the hardware-in-the-loop rig (§3.5), in this order:

1. YOLO11s at 640 and 1280 px, FP16 and INT8, on Orin Nano, Orin NX and L4.
2. Decode ceiling for H.264 1080p10 per device.
3. End-to-end latency p50/p95 at 50 %, 80 % and 100 % load.

Record the results in docs/13 next to the accuracy baselines.

---

## 12. Relation to other reports

* Report 17: the pipeline stages and contracts this report deploys.
* Report 18 §8: export and quantisation parity.
* Report 21: rollout, registry and retention.
* Report 23: HIL rig (M3) and degradation speed (M11).
* D04: networks, VMS/NVR, security and reference architectures.

---

## 13. References

All accessed 2026-09-26.

* [R1] Ultralytics, "YOLO11" model documentation (performance table: mAP, T4 TensorRT10 latency, params, FLOPs). https://docs.ultralytics.com/models/yolo11/
* [R2] NVIDIA, "NVIDIA L4 Tensor Core GPU" product page (TOPS, 24 GB, 72 W, 4 NVDEC/2 NVENC). https://www.nvidia.com/en-us/data-center/l4/
* [R3] NVIDIA, "Jetson Orin" module specifications (TOPS, power, video decode). https://www.nvidia.com/en-gb/autonomous-machines/embedded-systems/jetson-orin/ ; module index https://developer.nvidia.com/embedded/jetson-modules
* [R4] NVIDIA, "NVIDIA T4 Tensor Core GPU" product page ("decode up to 38 full-HD video streams", 70 W, 130 INT8 TOPS). https://www.nvidia.com/en-us/data-center/tesla-t4/
* [R5] NVIDIA, DeepStream SDK Developer Guide, and "Performance" page (end-to-end fps, e.g. PeopleNet 2.6.3 147 fps on AGX Orin). https://docs.nvidia.com/metropolis/deepstream/dev-guide/ ; https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Performance.html
* [R6] NVIDIA, "NVIDIA A2 Tensor Core GPU" product page. https://www.nvidia.com/en-us/data-center/products/a2/
* [R7] Hailo, "Hailo-8 AI Accelerator" (26 TOPS, 2.5 W typical). https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/
* [R8] Axis Communications, "Axis Deep Learning Processing Unit (DLPU)", developer documentation. https://developer.axis.com/computer-vision/computer-vision-on-device/axis-dlpu/
* [R9] Hardware Busters, "NVIDIA Jetson Prices Jump Up to 101% — the $249 Orin Nano Super Is Now $399" (July 2026). https://hwbusters.com/news/nvidia-jetson-prices-jump-up-to-101-the-249-orin-nano-super-is-now-399/
* [R10] Google Cloud, "Accelerator-optimized VM pricing" (G2/L4 ≈ $0.70/h on demand, region-dependent). https://cloud.google.com/products/compute/pricing/accelerator-optimized
* [R11] Intel / Open Edge Platform, "Deep Learning Streamer (DL Streamer)". https://github.com/open-edge-platform/dlstreamer ; docs https://docs.openedgeplatform.intel.com/dev/edge-ai-libraries/dlstreamer/index.html
* [R12] Insight Platform, "Savant" (Python framework over DeepStream). https://github.com/insight-platform/Savant
* [R13] NVIDIA, Triton Inference Server. https://github.com/triton-inference-server/server
* [R14] Milestone Systems, "XProtect pricing" (sold via partners; no public list). https://www.milestonesys.com/pricing/xprotect/
* [R15] Surveillant.ai, "Genetec Pricing 2026" (third-party estimate) [secondary]. https://surveillant.ai/guides/genetec-pricing ; Genetec SaaS pricing https://www.genetec.com/products/unified-security/security-center-saas/saas-pricing
* [R16] Network Optix, "Nx Witness FAQ" (licensing model). https://www.networkoptix.com/nx-witness/faq
* [R17] K. Zhou, Y. Yang, A. Cavallaro, T. Xiang, "Omni-Scale Feature Learning for Person Re-Identification", ICCV 2019. https://arxiv.org/abs/1905.00953
* [R18] Hailo-8 M.2 retail listings ~$200–275 (Waveshare module $204 + shipping, eBay/Micro Center, 2026-09; earlier "$120–150" not reproducible) [secondary]. https://hailo.ai/products/ai-accelerators/hailo-8-m2-ai-acceleration-module/
* [R19] Ambarella, "Ambarella Launches 4K, 5nm Edge AI SoC for Mainstream Security Cameras" (CV72S, ~3 W). https://www.ambarella.com/news/ambarella-launches-4k-5nm-edge-ai-soc-for-mainstream-security-cameras-with-new-highs-in-ai-performance-per-watt-image-quality-and-sensor-fusion/
* [R20] bluenviron, mediamtx (RTSP/RTMP/WebRTC media server). https://github.com/bluenviron/mediamtx
* [R21] F. Donald, C. Donald, A. Thatcher, "Work exposure and vigilance decrements in closed circuit television surveillance", Applied Ergonomics 47:220–228, 2015. https://pubmed.ncbi.nlm.nih.gov/25479991/
* [R22] ONVIF, "Profiles" (S, T, M, G). https://www.onvif.org/profiles/
* In-repo: `configs/scenarios/disguise_and_tamper.yaml`, `configs/scenarios/street_crowd.yaml`, `survsim/gt/video.py`, `survsim/realism/stats.py`, `survsim/eval/pipeline.py`; docs/11, docs/13, docs/15; research D03, D04, D06, 17–21, 23.
