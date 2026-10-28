# 106 · Compute and cost model for a 400-camera estate (whiteboard-ready)

Scope: a back-of-envelope an interviewer can check line by line. **Every measured number is from
`FACTS_VERIFIED.md`** (row named beside it); everything else is an **assumption with a name (A1…)**
in §0 and is said out loud as an assumption. All latencies are **desktop, shared GPU** (RTX 2070
Max-Q, 8 GB, often 84 % busy with the Unreal editor during timing; AUDIT_H3C). None is a Jetson,
TensorRT or datacenter number. The unit of the answer is therefore "**laptop-GPU equivalents**",
and the ratios (1280 vs tiles, K = 2 vs K = 3) travel better than the absolute counts.

## 0 · Assumptions (say these first)

| name | assumption | why this value | what breaks if wrong |
|---|---|---|---|
| A1 | Detect rate **5 fps per camera** (sub-stream) | a walker crosses a 10 s i-LIDS window in many frames (FACTS 20); 74 drill 1 uses 10 fps | GPU count scales linearly with it |
| A2 | 1280 input = **19.3 ms/frame** (H3c main run; 18.1 on re-time) | measured, shared GPU, YOLOv8n | absolute counts only |
| A3 | 2.0× tiles (320×240, H3's arm) = **143.3 ms/frame** (H3c; 114.1 on re-time) → "6–7× full_1280" | measured, shared GPU | absolute counts only |
| A4 | 640 input = **14.0 ms/frame** (H3b; **15.5** on the AUDIT_H3B re-run) | measured, shared GPU, unstable; same runs timed 1280 at 13.3 / 16.9 — **640 is not faster than 1280 here**: at batch 1 on this shared GPU, per-frame overhead (launch, pre/post-processing, NMS, host copies) dominates, not pixels | absolute counts only; an idle/TensorRT GPU would separate them |
| A5 | Tracker + ReID + decode overhead = **+20 %** on detector time | not measured end to end | cameras/GPU −/+ ~15 % |
| A6 | Plan the GPU at **70 % utilisation** (700 ms of GPU per wall-second) | queueing headroom for bursts | cameras/GPU |
| A7 | **20 % of cameras are "far"** (perimeter/long-throw; 80 of 400) | site-survey-dependent | tiling bill |
| A8 | Far cameras detect at **2 fps** (far people move few px/frame) | not tested for alarm timing | far recall/latency |
| A9 | Main stream **2.4 Mb/s** H.265 1080p; sub-stream 720p ≈ **1 Mb/s** | 74 drill 1 (2.4); 1 Mb/s assumed | bandwidth rows |
| A10 | Estate = H70's **40 sites × 10 cams**, budget B = 0.5 FA/cam-h per site | H70/H70b declared estate | operator sizing |
| A11 | INT8 on TensorRT is **1.5–2× FP16** | **vendor expectation, not measured by us**: H38/H43 measured AP cost only, never speed on this GPU (H38 CPU timings are contention noise, R46) | INT8 headroom row |
| A12 | Alarm clip = **10 s** at main-stream rate; alarm rate = budget B × cameras | not measured; B is a budget, not an observed FA rate | clip WAN row only |

Per-camera cost = fps × ms × 1.2 (A5). Cameras per GPU = 700 ms (A6) ÷ per-camera cost.

## 1 · Per-camera GPU budget → cameras per GPU

| input | ms/frame | GPU ms per camera-second (A1, A5) | cameras per laptop-GPU (A6) | far recall ≥ 20 px (CC0, H3c/H3d) |
|---|---|---|---|---|
| 640 | 14.0 / 15.5 (A4) | 5 × 14.0 × 1.2 = 84 (93) | **~8 (7)** — about the 1280 figure | 0.061 (blind far) |
| 1280 | 19.3 (A2) | 5 × 19.3 × 1.2 ≈ 116 | **~6** | 0.491 |
| 2.0× tiles | 143.3 (A3) | 5 × 143.3 × 1.2 ≈ 860 | **< 1** (0.8; 1.0 at the 114.1 re-time) | 0.681 |
| 2.0× tiles at 2 fps (A8) | 143.3 | 2 × 143.3 × 1.2 ≈ 344 | **~2** | 0.681 (timing untested at 2 fps) |

Estate of 400 (A7 split 320 near / 80 far):

| design | laptop-GPUs |
|---|---|
| 640 everywhere | 400 / 8 ≈ 50 — barely cheaper than 1280, and far cameras are blind on our sparse renders (H3) |
| 1280 everywhere | 400 / 6 ≈ 67 |
| 1280 near + tiles far at 2 fps | 320 / 6.04 + 80 / 2.03 ≈ 53 + 39 = **~93** |
| tiles everywhere at 5 fps | ≈ 400 × 1.2 ≈ **~490** |

Say: "the tiling bill is the far-camera count, not the estate size." Datacenter parts are faster
(FACTS 4: YOLO11n 1.5 ms on T4 TensorRT at 640, a vendor number), but I have not measured the
ratio, so I quote laptop-GPU units and the ratios.

## 2 · FP16 / INT8 headroom and its AP cost

| precision | AP cost (MOT20-02, yolov8n, 3–5 checkpoints) | speed |
|---|---|---|
| FP16 | **0.0000** AP loss (range −0.0002..+0.0003; H38) — take it | free headroom on any GPU with FP16 units; not measured by us |
| INT8 MinMax PTQ | AP −0.0117 (worst checkpoint 0.0154 > 0.015 bar); AP75 −0.030; AP50 ≈ unchanged (H38) | A11, unmeasured |
| INT8 Percentile PTQ | AP75 loss 0.0144 vs 0.0246 MinMax — recovers under half (0.415, H43) | A11 |
| INT8 learned-range QAT | AP75 loss 0.0138, recovery 0.439 (H43c); longer QAT refuted (H43d, 0.374) | A11 |

Reading: FP16 is a free default. INT8 costs **localisation** (AP75), not detection (AP50) — acceptable
for an alarm that needs "a person is there", less so for ReID crops or ground-plane position from box
feet. With A11 (unmeasured) INT8 would move 1280 from ~6 to ~9–12 cameras/GPU; I would buy it only after an
on-site calibration check (on-site calibration is untested, R46).

## 3 · Edge vs central vs operator wall

| tier | runs | why |
|---|---|---|
| Camera / NVR | encode main (A9 2.4 Mb/s → VMS/recording) + sub-stream; motion/tamper flags | recording is a legal duty independent of analytics |
| Site edge box (e.g. Orin NX) | decode sub-stream, detect at 640/1280, track, per-camera rules, clip cut | FACTS 34: 18 × 1080p30 decode is a ceiling; ~10–12 cams/NX with detect 640 @ 10 fps + ReID (38 §2.5) → 74's 4 NX per 40 cams. Jetson latency **unmeasured** by us |
| Central GPU | tiled far cameras (A7), cross-camera ReID, per-site θ, drift monitors (H70b), re-scoring | tiles are 6–7× cost; pooled infrastructure absorbs it |
| Operator wall | ranked alarm queue with clip + PTZ hand-off | H45c: ranked beats FIFO; H56: 1 PTZ is busy at arrival 0.382 of the time, 2 PTZs cut missed-second 0.369 → 0.057 |

Bandwidth (A9): recording backhaul 400 × 2.4 ≈ 960 Mb/s — stays on site with the NVR. Central
analytics on all sub-streams: 400 × 1 ≈ 400 Mb/s WAN. Edge analytics sending only far-camera
sub-streams (80 × 1 ≈ 80 Mb/s) plus alarm clips (A10, A12: 400 × 0.5 = 200 alarms/h × 10 s × 2.4 Mb/s ≈
1.3 Mb/s) is **~5× less WAN** — the reason detection lives at the edge and only tiling goes central.

## 4 · Operator wall sizing (H70, H45c)

- H70 (simulated, 40 sites × 400 cams, one K-operator wall, fatigue omitted): utilisation **0.842 at
  K = 2 → 0.563 at K = 3**, recall@300 s unchanged (≈ 0.70) — recall is detector-limited **by
  construction** (same score model everywhere).
- So K = 2 clears the queue on paper; K = 3 buys **resilience** (breaks, bursts, fatigue H70 left out),
  not recall. I would staff K = 3 per 400 cameras on a 24 h wall and say why.
- H45c: 1 operator / 40 cams, ranked queue realises 0.618 @5 min vs 0.584 FIFO (conformal capped θ);
  with ≥ 2 operators the capped conformal θ no longer beats H45c's arm "A1" (θ 0.95, still ranked; 2 ops −0.015 [−0.038, +0.008]) — H45c's A1 is an arm name, not assumption A1 here; operator model invented (H22), simulated. **Never pooled θ** (H70: ≈ 3
  sites above twice their assumed per-site budget).
- Per-site daily count monitors, not an estate total (H70b); a flat CUSUM false-flags a normal
  day/night pattern 0.896/site-week, so model hour of day.

## 5 · Where the 6–7× tiling cost is worth paying

- **Far cameras only, sparse scenes.** On CC0 far cameras 2.0× tiles lift far recall 0.491 → 0.681
  (+0.190 [+0.119, +0.265], H3c) — that is the alarm you otherwise miss on a perimeter.
- **Not near cameras:** near false positives rise 36 → 300 on the audit re-run (tile-border fragments);
  the H3d tile-border rule fixes that on renders.
- **Not dense real crowds:** on MOT20 the tile-border rule deletes real people (recall −0.118, H3e),
  and neither tile arm beats 1280 on AP50 there. Keep full 1280 on crowds; a density gate is untested.
- Cost framing: 80 far cameras at 2 fps tiled ≈ 40 laptop-GPUs vs ≈ 13 at 1280 (§1). Pay it where a
  missed far intruder is the costliest failure, i.e. fence lines.

## 6 · What changes at 4,000 cameras

Compute scales roughly linearly (~10× the GPU count, and decode, not inference, starts to cap each
server — FACTS 33: 38 FHD decodes per T4), so the design choice that matters is **what not to send
central**: edge detection becomes mandatory (4,000 × 1 Mb/s ≈ 4 Gb/s of sub-streams otherwise). The
operator wall becomes ~30 operators (my K = 3 per 400 staffing choice × 10, not a measurement) in regional pods, and per-site governance dominates: site-to-site
recall spread is large (H69 between-site SD 0.355), so per-site θ, per-site hour-of-day drift monitors,
staged model rollout with a hash per alarm, and a per-site calibration budget become the real cost —
people and process, not GPUs.

## 7 · Ten interviewer probes (≤ 5-line answers)

1. **"How many GPUs for 400 cameras?"** — In laptop-GPU units: ~67 at 1280 everywhere, ~93 if far
   cameras are tiled at 2 fps. Assumptions A1–A7; the ratio matters more than the count.
2. **"Why 5 fps?"** (A1) — The 10 s i-LIDS window needs several detections per crossing; 74's drill
   used 10 fps. Double the fps, double the GPUs.
3. **"Is 640 cheaper?"** — Not on this GPU: H3b timed 640 at 14.0 ms (15.5 re-run) vs 1280 at
   13.3 (16.9). At batch 1, per-frame overhead dominates, not pixels. On TensorRT with batching I
   would expect 640 to pull ahead, but that is unmeasured.
4. **"FP16 or INT8?"** — FP16 costs 0.0000 AP (H38): default. INT8 costs AP75 ~0.03 MinMax, ~0.014 with
   percentile or learned-range QAT; its speed gain is A11, unmeasured.
5. **"What runs on the edge?"** — Decode, detect, track, per-camera rules, clip cut. Central: tiles for
   far cameras, cross-camera ReID, per-site θ and drift. ~5× less WAN (§3).
6. **"How many operators?"** — H70: K = 2 at 0.842 utilisation, K = 3 at 0.563, same recall — by construction
   (one declared score model at every site, R67). Staff 3 for resilience; simulated, fatigue omitted.
7. **"Ranked or FIFO?"** — Ranked at 1 operator / 40 cams (0.618 vs 0.584 @5 min, H45c); with 2+ use H45c's arm
   A1 (θ 0.95, still ranked); simulated operator. Never pooled θ.
8. **"PTZ?"** — One PTZ is busy at arrival 0.382; a second cuts missed-second alarms 0.369 → 0.057
   (H56, assumed PTZ timings). Calibration, not motion, limits far acquisition.
9. **"What's the dominant cost?"** — Far cameras if tiled; otherwise operators. GPUs are linear and
   cheap to reason about; operators and per-site calibration are not.
10. **"What would you measure first?"** — Idle-GPU and TensorRT latency for 640/1280/tiles on the
    target part, then 1 week of per-site FA at the chosen θ.

## 8 · Three traps

- **"Your latencies are on a laptop GPU."** — Yes: RTX 2070 Max-Q, shared with the editor, 84 % busy
  on re-time. That is why I quote laptop-GPU units and the 6–7× ratio, not a server count. The ratio
  is what I would carry over; the absolute count I would re-measure.
- **"What about Jetson?"** — **Unmeasured.** I have vendor decode ceilings (FACTS 34) and a 10–12
  cams/NX estimate from 38 §2.5, not a latency. H38's CPU numbers are contention noise, not a device proxy.
- **"Why not just 1280 everywhere?"** — On this GPU I nearly would: 1280 costs about what 640 does
  (A4, per-frame overhead dominates). The catch is the other end: 1280 still misses half the far
  people (0.491), so sparse far cameras get tiles (§5). On a TensorRT part where 640 is genuinely
  cheaper, 640 on near cameras becomes worth it — re-measure first.
