# 34 · Intrusion-detection & video-analytics market — competitors and positioning

Companion to `removed-vendor-doc.md`. Tags: **[F]** checked this
session (2026-09-26) with URL; **[VERIFY]** from general knowledge, not
re-checked — hedge it aloud; **[INF]** my analysis.

---

## 1. How the market actually makes money — four business models

| Model | Buyer | What is sold | Metric that matters |
|---|---|---|---|
| **A. False-alarm filtering for monitoring centres (ARCs / central stations)** | Alarm Receiving Centres, remote-monitoring firms, integrators | Cloud or edge AI that screens detector/camera-triggered clips before a human sees them | % nuisance alarms removed at ~zero missed intruders; operator alarms/hour; cost per camera per month |
| **B. AI "virtual guard" / remote guarding** | Sites (construction, car dealers, multifamily, logistics yards) | Detection + human verification + talk-down audio, sold as a service replacing guards | Deterrence incidents, response time, price vs. a guard-hour |
| **C. Enterprise VMS / cloud video platform with analytics** | Corporate security, campuses, retail chains | Cameras + VMS + analytics (search, alerts, "insights") | Seats/cameras, forensic search time, dashboards |
| **D. High-assurance perimeter / CNI / defence** | Utilities, nuclear, airports, ports, prisons, MOD, border | Graded perimeter detection (often fused with radar/fence/thermal), accredited | Probability of detection on standard intrusion tests, nuisance alarm rate, NPSA/CSE grading, cyber assurance |

**[INF]** the vendor's public posture (multi-sensor, SWaP edge, MOD, border &
CNI, "high false alarm rates and operator fatigue") sits in **D**, with a
possible push into **A** via its CCTV false-alarm messaging.

## 2. Competitors

| Company | HQ / owner | Model | Edge vs cloud | Distinguishing points | Tag |
|---|---|---|---|---|---|
| **Calipsa** | London (2016); **acquired by Motorola Solutions, Apr 2022** (not Chubb) | A | Cloud | ">90%" false-alarm reduction; alarm verification, tamper and camera-health checks; sold into ARCs | [F] [Motorola PR](https://www.motorolasolutions.com/newsroom/press-releases/motorola-solutions-acquires-calipsa.html), [Euronews](https://www.euronews.com/next/2022/04/19/motorola-m-a-calipsa) |
| **Avigilon** (Motorola) | Vancouver; Motorola since 2018 (US$1.0 bn, FACTS_VERIFIED) | C/D | On-prem (Unity) + cloud (Alta) | Self-learning analytics, "Appearance Search", camera-embedded analytics | [VERIFY] |
| **Ipsotek** | London; Atos 2021 → **Eviden** | D/C | On-prem/server | VISuite: intrusion, perimeter, crowd, face, ANPR; CNI, airports, stadia; VISuite Core for large multi-site regulated deployments | [F] [Ipsotek CNI](https://www.ipsotek.com/protecting-the-uks-critical-national-infrastructure-with-ai-video-analytics/), [Eviden PR](https://eviden.com/insights/press-releases/ipsotek-launches-visuite-core-to-transform-scalable-ai-video-analytics-deployments/) |
| **VCA Technology** | UK, since 2009 | A/D (OEM) | Edge (VCAedge) + server (VCA Server) | Classic rule-based analytics upgraded with a "Deep Learning Filter"; OEM'd into VMS (e.g. Digifort) | [F] [VCA](https://vcatechnology.com/news/vca-technology-launches-brand-new-powerful-ai-video-analytics-solution/) |
| **BriefCam** | Israel; **Canon** since 2018 | C | On-prem/cloud | Video synopsis, forensic search, dashboards — the archetype of "insights" | [VERIFY] |
| **Genetec** | Montreal, private | C | Hybrid | Security Center unified platform; analytics mostly via partners | [VERIFY] |
| **Milestone XProtect** | Copenhagen; Canon group | C | On-prem, open platform | Largest open VMS ecosystem; analytics via marketplace plug-ins (the integration target for A-type vendors) | [VERIFY] |
| **Verkada** | US | C | Cloud-managed cameras (edge compute on camera) | Vertical hardware+SaaS, per-camera licences; people/vehicle search | [VERIFY] |
| **Rhombus** | US | C | Cloud-managed cameras | Similar to Verkada, more open (ONVIF adds) | [VERIFY] |
| **Spot AI** | US | C | Cloud + on-prem box, works with existing cameras | "Video AI agents"; $93 M raised as of the $31 M round (Oct 2024; later totals unverified); 100% channel | [F] [SiliconANGLE](https://siliconangle.com/2024/10/31/spot-ai-reels-31m-ai-powered-video-processing-platform/), [Spot AI blog](https://www.spot.ai/blog/spot-ai-goes-100-channel-launches-industry-first-2m-equity-program-as-video-ai-evolves-from-task-completion-to-full-ai-coworker) |
| **Coram** | US | C/B | Cloud on existing cameras | Series A $13.8 M (16 Jan 2025, Battery lead), Series B $35 M (June 2026), $66 M total; "autonomous agents" | [F] [BusinessWire](https://www.businesswire.com/news/home/20250115943800/en/Coram-AI-Raises-$13.8-Million-in-Series-A-Funding-to-Bring-AI-to-Video-Security-Boosting-Workplace-Safety-and-Efficiency), [Coram](https://www.coram.ai/post/coram-series-b-fundraise) |
| **Ambient.ai** | US | C/B | Cloud on existing cameras | "Computer-vision intelligence" for enterprise SOCs; Series B Apr 2025 (Tracxn extract; amount unverified); staff count and ownership unverified | [F2] [Tracxn](https://tracxn.com/d/companies/ambient-ai/__o3P0l5V7BKOZZr3yfissd1iMGgTNb4kFRNlvBdq9MNg) |
| **Hakimo** | US (2020) | B | Cloud | "AI Operator" (CV + generative AI) + remote operators; $10.5 M Series A Mar 2025, $20.5 M total; >100 clients | [F] [SiliconANGLE](https://siliconangle.com/2025/03/27/hakimo-secures-10-5m-new-funding-launches-autonomous-ai-security-agent/) |
| **Actuate** | US | A | Cloud, any camera | "Intruder" analytics for central stations via Patriot, Brivo, DICE; claims 95%+ FP reduction ([F] actuate.ai) and a **$10,000 reimbursement for missed detections** ([F2] search extract); Brivo/DICE integrations and ~20,000 cameras / 1,200 sites not found on fetched pages — unverified | [F]/[F2] [SecurityInfoWatch](https://www.securityinfowatch.com/alarms-monitoring/central-station-alarm-monitoring/press-release/55313670/actuate-actuate-patriot-systems-partner-to-bring-ai-powered-intruder-analytics-to-monitoring-centers), [actuate.ai](https://actuate.ai/) |
| **Evolon** | Dallas; ex-Jemez Technology (2001, Los Alamos alumni) | A | Cloud + Evolon Edge | Claims 90%+ false-alarm reduction and "98.5% accuracy" (audit: 98.5 % is an accuracy claim, not a reduction figure); Immix/UCC integration and Jemez/Los Alamos history not on fetched home page — unverified | [F] [evolontech.com](https://www.evolontech.com/), [SDM](https://www.sdmmag.com/articles/103081-evolon-introduces-ai-powered-video-monitoring-service) |
| **SentryAI** | US | A | Cloud | False-alarm filtering + "virtual patrol" for monitoring centres | [VERIFY] |
| **Iveda** | US (Nasdaq: IVDA) | C | Cloud + edge devices | Smart-city / IoT, strong in Taiwan | [VERIFY] |
| **IronYun (Vaidio)** | US/Taiwan | C | On-prem/edge | Vaidio platform, forensic search, NVIDIA-partnered | [VERIFY] |
| **DeepSight** | — | — | — | Could not identify a single clear security-video vendor under this name; do not cite | [VERIFY] |
| **Bosch (IVA Pro), Axis (AXIS Object Analytics, Perimeter Defender)** | DE / SE | On-camera | Edge | Free-ish analytics in the camera; "good enough" baseline every startup must beat on nuisance rate | [VERIFY] |
| **Davantis, DFUSION, KiwiVision (Genetec)** | ES / — | D | Edge/server | Perimeter-specialist analytics; DFUSION and KiwiVision Intrusion Detector are **NPSA CSE-listed** | [F] [NPSA DFUSION](https://www.npsa.gov.uk/cse/dfusion), [NPSA KiwiVision](https://www.npsa.gov.uk/cse/kiwivision-intrusion-detector) |
| **Scylla** | US/AM | A/D | Edge/on-prem | Perimeter intrusion, weapons, face | [F2] [Scylla](https://www.scylla.ai/perimeter-intrusion-detection/) |

## 3. Positioning matrix

```
                    CLOUD, any camera                     EDGE / on-prem, accredited
   ARC / service   Calipsa, Actuate, Evolon, SentryAI,    VCA (edge), Davantis, Evolon Edge,
   (alarm verify)  Hakimo (+ humans)                      Axis/Bosch on-camera
   Enterprise      Verkada, Rhombus, Spot AI, Coram,      Avigilon Unity, Genetec, Milestone +
   platform        Ambient.ai                             BriefCam, IronYun, Ipsotek
   CNI / defence   (rare - data sovereignty blocks it)     Ipsotek, DFUSION, KiwiVision,
                                                           radar/fence fusion vendors,
                                                           ** the vendor (multi-sensor, SWaP) ** [INF]
```

**[INF] Where the vendor can win.** Everyone in the top rows fights on "90–98 % false
alarms removed" for visible-light cameras. Few offer genuine **multi-sensor
fusion** (radar + RF + acoustic + EO/IR) at the **edge**, with UK **sovereignty**
and clearance. That is a CNI/border/defence niche with higher prices and higher
evidence bars — and the evidence bar is where simulation earns money.

## 4. Standards and accreditation that shape the UK market

* **BS 8418** — code of practice for installation and remote monitoring of
  **detector-activated** CCTV; systems installed by **NSI** or **SSAIB**
  certified firms can get police response; monitored at a BS 8418-compliant ARC
  ([NSI](https://www.nsi.org.uk/detector-activated-cctv-systems-realise-protective-potential-through-updated-british-standard-bs-8418/), [BSIA user guide PDF](https://www.bsia.co.uk/zappfiles/bsia-front/Pdfs/196%20user%20guide%20to%20bs8418%20detector%20activated.pdf)) **[F2]**. Consequence: false alarms cost the ARC operator time *and* police-response status — the core economic pain for model A.
* **NPSA** PIDS evaluation (graded, CSE listing) and **CAPSS** (pass/fail cyber
  assurance for physical-security products) **[F2]**, see file 33 §5.
* **i-LIDS** (Home Office, via CAST/NPSA) — scenario datasets and evaluation
  protocol: sterile zone, parked vehicle, abandoned baggage, doorway
  surveillance, multiple-camera tracking, plus new-technology (thermal/IR)
  scenarios. **There is no loitering scenario** — see docs/research/31 [21].
* **Surveillance Camera Code**, **UK GDPR** / ICO video guidance, BS EN 62676
  (CCTV systems), ONVIF Profiles S/T/M (M = analytics metadata) **[VERIFY
  numbering]**.

## 5. Pricing models (public-domain patterns)

| Model | Typical structure | Tag |
|---|---|---|
| ARC filtering (A) | per camera per month SaaS, sometimes per-alarm-processed; sold through the ARC's software (Immix, Patriot, SureView, Sentinel) | [VERIFY] ranges ~£/$ single digits–tens per camera-month |
| Virtual guard (B) | per site per month, benchmarked against a guard-hour | [VERIFY] |
| Cloud platforms (C) | camera hardware + per-camera annual licence (Verkada/Rhombus); or per-camera analytics licence on existing cameras (Spot AI, Coram) | [VERIFY] |
| VMS plug-ins | perpetual per-channel licence + annual care (Milestone/Genetec ecosystem) | [VERIFY] |
| CNI / defence (D) | project + integration + support contract; framework/tender; evaluation trials paid by customer | [INF] |
| Guarantees | Actuate's $10k missed-detection reimbursement — a sign the market sells *risk transfer*, not accuracy | [F2] |

## 6. What "insights" means commercially

"Insights" is analytics sold to non-security budgets (operations, H&S,
marketing, facilities) to justify camera spend:
* **Occupancy / footfall / people counting**, queue length and wait time.
* **Dwell and heat maps** — where people spend time; retail layout, shelf engagement.
* **Compliance** — PPE, restricted-zone entry, forklift/pedestrian near-miss, vehicle speeding, loading-bay utilisation.
* **Forensic search / video synopsis** — "red jacket after 22:00", which is the "cueing and retrieval" the vendor describes for media monitoring.
* **Operational KPIs for security itself** — alarms per camera-hour, time-to-acknowledge, camera health/tamper — which is what an ARC buys.

**[INF]** For a CNI/defence buyer "insights" instead means **pattern-of-life**:
repeated reconnaissance (hostile recon), approach patterns before an intrusion,
drone activity correlation — the vendor's "behaviour, activity and change detection".

## 7. Five market truths to drop in conversation

1. Nuisance alarms, not missed intruders, are what kills deployments; the
   metric is **false alarms per camera-hour** against an operator budget.
2. Vendor "%-of-false-alarms-removed" numbers are unfalsifiable without a
   shared test set — hence NPSA/i-LIDS style scenario testing and the value of
   simulation with ground truth.
3. Cloud wins SMB; **CNI/defence refuses cloud** for sovereignty — edge + air-gap.
4. The integration moat is the **VMS/ARC software** (Milestone, Genetec, Immix,
   Patriot, SureView) — alarms must land where operators already work.
5. Generative-AI "agents" (Hakimo, Spot AI, Coram) are the 2025–26 marketing
   wave; the hard part is still detection quality at night, rain, small targets.
