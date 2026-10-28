# Adversarial accuracy audit — reports 43–47 (2026-09-26)

Method as in AUDIT_25-38.md: every checkable claim was treated as wrong until
its primary source was fetched (GStreamer / NVIDIA / ONVIF docs, EUR-Lex,
legislation.gov.uk, ICO, EDPB, Gemini API docs, arXiv, licence pages by plain
`curl`) or, for 46, until the number was found in a **committed** repo file.
Reports were corrected in place, one commit per report. 32_EXPERIMENTS_LOG.md
was read-only (owned by the experiment agent).

## Scores (confirmed / total claim rows)

| Report | Confirmed | Total | Score | Commit(s) |
|---|---|---|---|---|
| 43 video pipeline | 22 | 27 | 81 % | `70c4117` |
| 44 privacy law & ethics | 30 | 36 | 83 % | `2dfd5ef` |
| 45 VLMs & foundation models | 17 | 22 | 77 % | `9b9e99e` |
| 46 STAR stories | 17 | 25 | 68 % | `4da089f`, `40bfd2e`, `f55c600` |
| 47 character & asset licensing | 9 | 14 | 64 % (3 corrected, 2 unverifiable) | `178108d`, `a0fa29a` |

## Corrections that change conclusions

* **43 Orin NX 16 GB decodes 18 × 1080p30 H.265, not 23** (23 is AGX Orin
  Industrial; AGX 64/32 GB = 22 was right, the "implausible" flag was on the
  wrong row). The 40-camera × 25 fps budget (1 000 fps decode) needs **three
  NX or two AGX** (~76 %), not two NX at 72 % (they would run at 93 %).
* **43 rtspsrc latency 2000 ms confirmed**, but it *is* the internal
  jitterbuffer latency — defaults do not add (2.0 s, not 2.2 s); glass-to-alarm
  with defaults 2.6–2.9 s [INF]. Transport order is unicast → multicast → TCP.
* **43 ONVIF Profile S**: "deprecation in process; last date of product
  conformance submissions is March 31, 2027" — confirmed verbatim.
* **45 Gemini's default video resolution is *low*** (66 tok/frame, ~100 tok/s);
  263 tok/s is the high-res case. Always-on at 1 fps = ~0.36M (default) –
  1.1M (high) tokens/cam-h. D07's 4.6M is a 2 fps × 640 tok/frame research
  protocol — both "right" under their own assumptions. Index fact 9 rewritten:
  always-on is **uneconomic, not infeasible** (~$31–74/camera-month on
  Flash-Lite); gating is ~170–400× cheaper (was 100–350×). D07 L164–167,
  17 L466 and 19 L191/197 carry the unqualified 4.6M — out of scope, left.
* **45 Holmes-VAU ~0.566 ms** is time-to-first-token in Table 4, not sampler
  latency; the fetched values look unit-garbled — do not quote.
* **44 Regulation (EU) 2026/1744 now primary-verified on EUR-Lex**: signed
  8 Jul 2026, OJ 24 Jul, in force 27 Jul 2026; Annex III 2 Dec 2027; Annex I
  2 Aug 2028; sandboxes 2 Aug 2027; Art 50(2) legacy gen-AI to 2 Dec 2026
  ("transparency did not move" was half right); new Art 5(1)(ba)/(bb) bans from
  2 Dec 2026.
* **44 DPIA**: ICO "invisible processing" is the Art 14 criterion and usually
  does not apply to own-camera CCTV; the trigger is innovative tech + tracking +
  Art 35(3)(c). Age/gender row now cites Art 5(1)(g) (age/gender *not* banned).
  6A003.b note exempts only broadcast cameras.
* **46 STAR numbers were pre-fix / uncommitted**: synthetic-only AP 0.161 (two
  seeds) → **0.152 ± 0.025** (3 seeds); synth + real 0.475 → **0.472 ± 0.005**;
  "300 real frames" → 60 frames × 5 repeats; OSNet cross-lighting **0.869 was the
  leaky same-frame protocol** → 0.444 vs histogram 0.245; probe 5's "results not
  landed" replaced by H6 (freeze10 0.221, loose GT tops +7 %). Story 13 (CC0
  cast, −0.013 recall, `8c3b03b`) added. All sources now committed files.
* **47 MetaHuman licence page is public** (plain `curl` 200; clause in FAQ
  JSON-LD). Verdict unchanged: characters/animation curves may not be used to
  "build or enhance any database or train or test" AI. Consequence carried into
  46: batch_v4–v6 and H1–H6 are internal engineering evidence only.

## Verbatim licence clauses (fetched 2026-09-26)

* MetaHuman — https://www.metahuman.com/license: "However, you may not use
  MetaHuman characters or animation curves to build or enhance any database or
  train or test artificial intelligence, machine learning, deep learning, neural
  networks, or similar technologies (as further detailed in the Unreal Engine
  EULA). This includes the use of rendered output from MetaHuman digital
  characters and animation curves, if created to replicate the functionality of
  MetaHuman." (UE EULA itself 403; Wayback unreachable.)
* SMPL-X — https://smpl-x.is.tue.mpg.de/modellicense.html: "Any other use, in
  particular any use for commercial, pornographic, military, or surveillance,
  purposes is prohibited." and "This license also prohibits the use of the
  Software to train methods/algorithms/neural networks/etc. for commercial,
  pornographic, military, surveillance, or defamatory use of any kind."
* Reallusion Content EULA (1 Aug 2025) — https://www.reallusion.com/Content/EULA/EULA.htm
  §2.1.2.C: "You may NOT use the Content or any Derivative Content in the
  following scenarios or applications: … 5. For machine learning, AI training,
  or AI-generated output."

## Claim tables

### Report 43

| claim | § | source fetched | verdict | note |
|---|---|---|---|---|
| RTSP 2.0 = RFC 7826, obsoletes 2326 | 1.1 | https://www.rfc-editor.org/rfc/rfc7826 | confirmed | |
| Session timeout "normally 60 seconds" | 1.1 | same | confirmed | |
| rtspsrc follows RFC 2326; ntp-sync false | 1.1–1.2 | https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html | confirmed | |
| RTP 90 kHz H.264; RTCP 5 % | 1.2 | RFC 6184/3550 | unverifiable | not refetched |
| Transport order multicast→unicast→TCP | 1.4 | rtspsrc | corrected | unicast→multicast→TCP |
| UDP 5 s / TCP 20 s timeouts | 1.4 | rtspsrc | confirmed | |
| Profile S deprecation, 31 Mar 2027 | 2 | https://www.onvif.org/profiles/profile-s/ | confirmed | verbatim |
| Profile T/M scope; Milestone M | 2 | onvif.org | unverifiable | |
| low-latency-mode default false | 3.2 | NVIDIA gst-nvvideo4linux2 | confirmed | |
| skip-frames options | 3.4 | same | corrected | non-ref skip Jetson-only |
| drop-frame-interval | 3.4 | same | confirmed | |
| NVDEC decode table | 4.1 | NVDEC app note (SDK 13.0) | confirmed | |
| RTX 2070 1 NVDEC | 4.1 | NVIDIA matrix (search) | confirmed | |
| num-extra-surfaces Jetson only | 4.1 | nvvideo4linux2 | corrected | dGPU and Jetson |
| AGX 22, NX 16 GB 23 × 1080p30 | 4.2 | https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/ | corrected | NX = 18 |
| 2 NX boxes at 72 % | 8.3 | derived | corrected | 3 NX / 2 AGX |
| nvstreammux behaviour | 6.2 | NVIDIA docs | confirmed | |
| nvinfer interval/process-mode/engine swap | 6.3 | NVIDIA docs | confirmed | |
| network-mode 0/1/2 | 6.3 | same | corrected | 3 = BEST |
| nvtracker types, ages | 6.4 | NVIDIA docs | corrected | MaskTracker added |
| nvmsgbroker protocols | 6.5 | NVIDIA docs | confirmed | |
| AGX 147 / L40S 1114 fps | 6.6 | DS_Performance | confirmed | |
| queue 200 buf / 10 MB / 1 s | 7.1 | gstreamer queue | confirmed | |
| rtpjitterbuffer 200 ms defaults | 7.1 | gstreamer rtpjitterbuffer | confirmed | |
| rtspsrc latency 2000 ms | 7.1 | rtspsrc | confirmed | not additive |
| Milestone 9090 / "Device not known" | 9.1 | Milestone MIP SDK | confirmed | |

(27 rows including the budget row counted with 4.2.)

### Report 44

36 rows, 30 confirmed; corrected rows: Code date (laid 16 Nov 2021 / in force
12 Jan 2022), invisible processing (×2), EDPB Example 4 after para 80, age/gender
Art 5(1)(g), transparency deadline, export-list naming, 6A003.b note. Sources:
legislation.gov.uk (DUAA 2025 c.18, UK GDPR Arts 9/35, DPA s.205), ICO video
surveillance / DPIA / biometric pages, gov.uk Surveillance Camera Code,
judiciary.uk Bridges press summary, EUR-Lex OJ:L_202401689 and OJ:L_202601744,
EDPB Guidelines 3/2019 PDF, UK export control list 2025, metahuman.com/license,
CG Channel June 2025. Full row list is in the 44 commit message context
(`2dfd5ef`); verdicts as above.

### Report 45

| claim | source | verdict |
|---|---|---|
| Grounding DINO 52.5 / 26.1 ODinW | arXiv 2303.05499 | confirmed |
| GDINO-T 48.4 / 57.2; B 56.7 | GitHub IDEA-Research | confirmed |
| OWLv2 31.2 → 44.6 | arXiv 2306.09683 | confirmed |
| OWL-ViT one-shot | arXiv 2205.06230 | confirmed (not refetched) |
| YOLO-World 35.4 @ 52 FPS V100 | arXiv 2401.17270 | confirmed |
| UCF-Crime 1 900 / 128 h / 13 | arXiv 1801.04264 | confirmed |
| LAVAD 80.28 etc. | arXiv 2404.01014 | confirmed |
| VadCLIP 88.02 / 84.51 | arXiv 2308.11681 | confirmed |
| Holmes-VAU 88.96 / 87.68, CVPR 2025 | CVF open access | confirmed |
| Holmes-VAU 0.566 ms sampler | arXiv Table 4 | corrected |
| POPE | arXiv 2305.10355 | confirmed (not refetched) |
| Gemini image 258 tok | ai.google.dev tokens | confirmed |
| 263 tok/s video, 32 audio | same | confirmed (high-res) |
| 258 default / 66 low | video-understanding | corrected (default = low = 66) |
| ~100/~300 tok/s, 1 fps | same | confirmed |
| Gemini prices | ai.google.dev pricing | confirmed |
| Claude prices | claude.com/pricing | confirmed |
| Scenario A $240/$74 | derived | confirmed at high res |
| 5 fps ~$1 200 | derived | corrected (~$1 100) |
| Scenario B $0.66 / $1.9 | derived | confirmed |
| gating 100–350× | derived | corrected (170–400×) |
| 0.95M vs D07 4.6M | derived | corrected (reconciled) |

### Report 46 (repo-sourced)

| claim | story | source | verdict | note |
|---|---|---|---|---|
| black render mean 157.6 / std 21.9 | 1 | `docs/BUG_black_render.md` l.28 | confirmed | |
| commits a329b36/84eca5c/25303ff/97325e4 subjects | 1 | git log | confirmed | |
| HOTA 0.545 → 0.434 | 2 | docs/13 l.80–81, `be9f52a` | confirmed | |
| MOTA 0.463 → 0.466; DetA 0.833 → 0.714 | 2 | docs/13 l.264, 293 | confirmed | |
| stuck 34.6 % / 49.1 % → 0 %; 1.08 m/s | 3 | docs/11 l.261–263, `e5af8cd` | confirmed | |
| peak 3.4 GB; guard 7 200 MB | 4 | docs/12 l.879–880, `d57db8c` | confirmed | |
| "two seeds", AP 0.161 | 5 | 32 §H1 `5e5f53d` | corrected | 3 seeds, 0.152 ± 0.025 |
| "300 real frames" | 5 | 32 §H1 | corrected | 60 frames × 5 repeats |
| real-only 0.491 | 5 | 32 §H1 | confirmed | ± 0.003 |
| synth + real 0.475 (sd 0.003) | 5 | 32 §H1 | corrected | 0.472 ± 0.005 |
| AP50 80–120 px 0.073 → 0.007 | 5 | 32 §H1 | confirmed | seed 0 |
| source = uncommitted row.md | 5,6,12 | — | corrected | now 32 + commit hashes |
| DwellRule 0/2, PathLoiter 2/2, seed 11 | 6 | `1a5322b` message | confirmed | |
| 0.8 recall at 51 FA/cam-h | 6 | 32 §H5 | confirmed | 51.43 default |
| 114 → 2 alarms, P 0.026 → 0.50, 27.75 → 0.25, 19×/111× | 7 | `38a8cb4` message | confirmed | |
| recall 0.50 → 0.17 | 7 | same | confirmed | |
| 18/18 gated | 8 | `19d2df4` | confirmed | |
| batch_v3 6/6, 5 400 frames | 8 | docs/12 l.759 | confirmed | |
| 5 restarts, 40 min, 150 % CPU, 4.6 GB | 10 | docs/12 l.60–64 | confirmed | |
| 62 s over 8 931 frames; 1 h 26 min | 11 | docs/13 l.86–130 | confirmed | |
| ~14 % Kalman cut; MOTA 0.4223 unchanged | 11 | docs/13 | confirmed | |
| histogram vs OSNet 0.291/0.251, 0.219/0.148, 0.584/0.512 | 12 | 32 §H4 | confirmed | |
| OSNet day↔night 0.869 vs 0.287 | 12 | 32 §H4 caveat | corrected | leaky; 0.444 vs 0.245 |
| probe 12 histogram 0.287 | 12 | 32 §H4 | corrected | 0.245 |
| probe 5 "results not landed" | 5 | 32 §H6 `4eac637` | corrected | stale; H6 added |

### Report 47

Full table is §6 of `47_CHARACTER_AND_ASSET_LICENSING.md` (`178108d`).
Corrected: MetaHuman page "login-walled" (it is public), BEDLAM "identical" to
SMPL-X (Data vs Model & Software; same surveillance ban), "22 bodies" → 22
rebaked / 16 verified (`9c87424`). Unverifiable: UE EULA body (403), Wayback.
Added: Epic forum claim that the UE Content EULA MetaHuman addendum's AI clause
was removed with the NoAI tag — does not change the verdict, since the current
metahuman.com page carries the ban.

## Cross-report consistency

* MetaHuman clause: 44 §8.1, 46 story 13 and 47 §0 now quote the same text.
* Tokens/camera-hour: 45 and index fact 9 agree; D07/17/19 still say 4.6M
  unqualified (out of scope).
* Orin NX decode: 43, FACTS and 42 now all say 18 × 1080p30.
* Synthetic transfer: 46, 42, FACTS and index fact 8 all use 0.152 ± 0.025.
