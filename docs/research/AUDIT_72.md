# AUDIT_72 — vendor verification, ANPR/PPE gaps, arithmetic (2026-09-27)

Target: `72_INSIGHTS_AND_FORENSIC_SEARCH.md` @ 0fb8768. Method: WebFetch by URL
(WebSearch was **unavailable** — the session's 200-search budget was spent), so
alternates were tried only where the URL was obvious.

## 1 · [A] → [V]/[X]  (14 [V], 7 [X])
| Claim | Result | Fetched evidence |
|---|---|---|
| Avigilon Appearance Search attributes | [V] (partial) | "Filter by age, gender, clothing and faces…"; hair colour / embedding architecture not stated → [INF] |
| Avigilon UMD page | [X] | 404 |
| Alta = NL search, formerly Ava | [X] | Alta page lists Appearance Search, UMD, FR, LPR, PPE; no NL search, no Ava |
| Pritch et al. TPAMI 2008 | [X] unloadable | DOI → ieeexplore 4444355, empty body |
| BriefCam Review/Research/Respond | [X] + corrected | briefcam.com 301 → milestonesys.com/products/software/briefcam/ [V]: variants Investigator/Rapid Review/Protect/Insights |
| Genetec Security Center | [V] | Omnicast, Synergis, AutoVu, Clearance, forensic search |
| Genetec LPR page | [X] | 404 |
| Milestone VMS page | [X] | 404; home page [V] only "open-platform software" |
| ONVIF Profile M | [V] | "Analytics configuration and information query for metadata", "Generic object classification support" |
| Verkada search + onboard storage | [V] | "AI-powered search … face search … reverse image search"; "30 - 365 days" |
| Axis Object Analytics | [V] | "Detect, classify, track, and count humans, vehicles…", on camera, preinstalled free |
| Coram NL | [V] | "Build alerts in plain English", "Works with any IP camera" |
| Spot AI NL | [V] | "Iris … ask any camera a question in plain language" |
| Coram/Spot "publish per-camera pricing" | [X] | no pricing on either page |
| Ambarella CV7/N1/VLM search | [X] | homepage has only CVflow / edge AI |
| Hailo TOPS | [V] | 8: 26; 15: up to 20; 10H: 40 INT4; 8L: 13 |
| FAISS, HNSW 1603.09320 | [V] ×2 | tagline; Malkov & Yashunin |
| UK GDPR Art 5(1)(b), Art 35(3)(c) | [V] ×2 | quoted |
| Surveillance Camera Code (12 principles, P6) | [V] | updated 3 Mar 2022 |
| Bridges press summary | unchanged [V] via `44` | PDF fetched but binary; no text extractor on host |

## 2 · Gaps filled (72 §4b, §4c)
- **ANPR:** NASPLE v3.5 (Jul 2026) §9.7 static cameras "capture 98%… accurately
  read 95% of captured VRM" [V]; §10.4 retention 12 months national / 90 days
  local / 7 days third-party [V]; ICO private-operator rules [V]; gate design [INF].
- **PPE:** SH17 YOLOv9-e mAP > 70.9 % (arXiv 2407.04590) [V]; CHV YOLOv5x 86.55 %
  (authors' repo; MDPI 403) [V]; false-alarm economy argument [INF].

## 3 · Arithmetic and H37
- 2.4 Mbit/s × 86,400 / 8 = 25.92 GB/cam-day × 30 × 40 = **31.1 TB** ✓.
  Quiet: 600k tracks × 7 KiB = 4.3 GB + 3 M × 256 B = 0.77 + 600k × 3.2 KB = 1.92
  + 0.12 = **7.1 GB** (0.023 %) ✓; busy ×10 = 71 GB (0.23 %) ✓; PQ 3 M × 64 B = 0.19 GB ✓.
  Note the vector line uses KiB, the rest decimal — immaterial (<3 %).
- **H37 vs 49 §12:** 66/72 lacked a single primary metric, named control, test +
  multiplicity, numeric success, sample-size, confounds and abandon-if. Added to
  both copies (identical text); hypothesis unchanged.

## Score
Before **5/10** (every product claim unverified; 3 vendor URLs dead; BriefCam
product naming out of date; two unsupported claims; ANPR/PPE missing; H37
off-template). After **8/10** — residual: UMD, Ambarella, TPAMI and Milestone
search mechanism remain unsupported by a fetchable primary page.
