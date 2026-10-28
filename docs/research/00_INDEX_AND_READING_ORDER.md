# 00 · Research Corpus — Index, Reading Order, Provenance Rules

New here? See [`README_START_HERE.md`](README_START_HERE.md) for the short
orientation (what this is, the 1-hour path, day-of files, how claims are kept
honest, the licence rule).

~834k words: 16 dossiers (R/D/H), 76 report files (17–91), 65 `AUDIT_*.md` files and
`FACTS_VERIFIED.md`, written in about 24 hours (Sept 2026). Run
`python tools/corpus_stats.py` to refresh these numbers. Purpose: prepare for
an interview at the vendor (UK defence AI; CCTV/CNI analytics line) and ground
every design decision in the SurvSim simulator. **Where any file disagrees with
`FACTS_VERIFIED.md`, FACTS wins.**

## Start here: how much time do you have?

Minutes assume ~200 words/min for targeted reading and include saying things
aloud. "§" means read only that section.

### 1 hour (the night before, or the morning of)
Rebuilt 2026-09-27 by `84` (third cold read; `77` built the previous path); re-timed and spot-fixed
by `92` (fourth cold read, same evening — H61's stale "not run" line in `78` and the pocket's
tailgater sentence missing H59's caveat, no restructure needed). Timed by word count:
~8,235 words (`92`'s recount, reproduced independently at AUDIT_92) at 200 words/min ≈ 41 min reading,
plus ~7 min aloud at 150 words/min and ~6 min recall ≈ 54 min.
Duplicates were cut: `65` v2 §2 is `60` re-ordered, `78` §2 is `65` v2 §1a, and `52` §6 / `68` §3 / `77` §4 were older copies of `84` §4.

**New for 2026-09-27 evening: the interview is three separate rounds (30-min technical chat,
1-hour VS Code coding block, 30-min whiteboard), not one 60-min panel — read
`93_INTERVIEW_FORMAT_PLAN.md` first; it re-times everything below for that shape and
supersedes `90` as the day-of rehearsal.**
| # | File | Min | Do |
|---|---|---|---|
| 0 | `93_INTERVIEW_FORMAT_PLAN.md` | 10 | The 8-of-40 numbers and 45-s opener for the technical chat; the coding-block time plan and offline snippets (`offline_snippets.pdf`, 3 pages); the 25-min whiteboard script; the revised checklist |
| 1 | `60_ONE_PAGE_CHEAT_SHEET.md` | 15 | Read all 40 numbers in arc order (A built → H the twin answer) with their *so what* and ✗ partner; formulas, stories, "not to say" |
| 2 | `65_DRESS_REHEARSAL_V2.md` §1, §3–§7 (skip §2: it is `60` re-ordered; skip §8–10) | 15 | Opener aloud twice (< 105 s; = `78` §2), 30-s cut, ship answer, closed/open gaps, H26 retraction story, 10 hard Qs, drill-1 sketch |
| 3 | `FACTS_VERIFIED.md` "The forty to know cold" | 12 | Cover the value, recall it (public benchmarks and law — 60 carries our own numbers) |
| 4 | `removed-vendor-doc.md` §0 + §3 | 3 | The headline correction; products (then `78` §1 in the 4-hour path) |
| 5 | `80_FIGURE_PACK.md` §2–3 (figures 02, 03) | 4 | The two figures you lead with; read each "Trap" line |
| 6 | `84_COLD_READ_REVIEW_V3.md` §3 (10 questions) + §4 (closed vs 5 open gaps) | 4 | Know where the corpus is thin *before* they find it |
| — | slack | 5 | Re-read only what you missed in 1–3 |

### 4 hours (the day before)
Everything in the 1-hour list (60 min), then 180 min (total 240; `AUDIT_84_85` trimmed step 13 by 10 min after 15b pushed it to 250; `86` added as 15c for 10 min by trimming step 10 45 → 40 and step 15 15 → 10; `87` added as 15d for 10 min by trimming step 10 40 → 30, Q1–Q18 aloud, Q19–Q25 read only; `88` added as 15e for 10 min by trimming step 12 (`67`) 20 → 10 — gaps table + "what to say if you don't know" only, §5 moves to the 1-day path; `91` added as 15f for 10 min by trimming step 9 (`46`) 25 → 20 and step 11 (`74` Drill 1) 25 → 20 — the multiplicity/bootstrap-unit traps are worth more than one more story rehearsal and 5 min off a drill you already know cold):
| # | File | Min | Do |
|---|---|---|---|
| 8 | `52` (all; §5 V/A/X table, §6 gaps — moved here from the 1-hour path by `84`) | 25 | Architecture diagram; 5-min pitch |
| 9 | `46_STAR_STORIES_FROM_SURVSIM.md` stories 1, 2, 5, 14, 16, 17 | 20 | Each aloud in ≤ 70 s |
| 10 | `68` §2 (Q1–Q18 aloud; Q19–Q25 read only) | 30 | Answer aloud before reading (supersedes `35` §2, which predates H12–H40) |
| 11 | `74_SYSTEM_DESIGN_DRILLS.md` Drill 1 (40-cam perimeter), timed, scored on its rubric | 20 | 4 NX, 120 → ~91 alarms/h at θ 0.9618 (H33c), realised 0.618 ranked (H45c) |
| 12 | `67_ADVERSARIAL_PANEL_GAPS.md` gaps table + "What to say if you don't know" (§5 dropped for `88`) | 10 | Conformal θ, Art 22A–D, ALARP, JSP 936 |
| 13 | `17_SYSTEM_DESIGN_OVERVIEW.md` — the nine-stage diagram only (skim; `52`'s architecture diagram in step 8 already covers the prose) | 10 | The nine-stage pipeline you will draw |
| 14 | `58_LOITER_RULE_REDESIGN.md` §6 (round 3 is the shipped rule; round 2 is superseded) | 10 | A1 2.915 / 0.825 and the twin floor |
| 15 | `55_FORMULA_SHEETS.md` (tracking, alarm stats, geometry) | 10 | Write 4 formulas from memory |
| 15b | `85_DEFENCE_CONTEXT_PRACTICALITIES.md` §0 + §10 | 10 | Three things never to claim (clearance, customer sites, legal rulings); 10 Q&As with red flags |
| 15c | `86_ALARM_EVIDENCE_AND_EXPLAINABILITY.md` §0 + §7 + §8 | 10 | Alarm card for a 30 s decision; rule trace vs saliency; WORM log for Art 22A–D; schema fields SurvSim fills; 10 red-flag Q&As |
| 15d | `87_MOCK_INTERVIEW_ROUND7_SECURITY_ASSURANCE.md` Q1, Q2, Q4, Q6, Q7, Q15 + the three never-say words | 10 | Tamper-*evident* not tamper-proof; anchored head; public salt reversible; hash of GT is GT; what the pack does not cover |
| 15e | `88_CODING_DRILLS.md` Drills 1, 3, 7 — cover the code, write each on paper, say (d) and (e) aloud; then `pytest -q tests/test_coding_drills.py` | 10 | IoU matrix, Hungarian vs greedy counter-example, MOTA vs IDF1 on the swap toy |
| 15f | `91_MOCK_INTERVIEW_ROUND9_STATISTICS.md` Q1–Q10 aloud, Q11–Q15 read only | 10 | Pre-registration vs peeking; frame vs clip bootstrap (H47); sign-flip floor at n=4; Holm not applied to H46's argmax; min–max at n=3 is not a CI (H38); conformal B must be enforced, not assumed (H33b→H33c) |
| 15g | `100_INFILTRATION_PLAYBOOK.md` §0 + §1 table + §5 (optional — read in place of step 15 `55` if short on time) | 10 | Tactic → camera signal → closer; GAO 10/10 through the front checkpoint; count people not badges (H54 0.685) |
| 15h | `99_QA_HOMOGRAPHY_ANOMALY_UNIFORM.md` (optional, skim) | 5 | Auto-homography from stature (H39 degenerate free-f); anomaly as ranking not primary (H63 pre-registered); a uniformed intruder needs corroboration, not appearance |

### 1 day (~7.5 h)
Everything in the 4-hour list (240 min), then:
| # | File | Min | Do |
|---|---|---|---|
| 16 | `74` Drills 2–3 (forensic search, 20-site drift loop) | 40 | Aloud, timed; replaces `40` Round B in this path |
| 17 | `18_PERCEPTION_STACK.md` + `19_BEHAVIOUR_INTENT_ANALYTICS.md` §FA budget | 40 | Detector/tracker/ReID choices; base-rate argument |
| 18 | `73` §summary + `75` H39 section + `76` H40 section | 25 | Tracking sim2real, auto-calibration (not met), line-cross (not met, FA optimistic) |
| 19 | `43_VIDEO_PIPELINE_ENGINEERING.md` §7–8 | 15 | Decode-bound sizing (Orin NX 18× 1080p30 ceiling, 4 NX budget) |
| 20 | `44_PRIVACY_LAW_AND_ETHICS_UK_EU.md` §3, §6.5 + `47` §0 | 20 | Bridges; AI Act dates; MetaHuman clause |
| 21 | `51_OPERATOR_HUMAN_FACTORS_AND_INSIGHTS_PRODUCTS.md` (skim) | 15 | BS 8418, NPCC 3-false-calls rule, U = C·B·t/3600 |
| 22 | `49_EVALUATION_STATISTICS_AND_EXPERIMENT_DESIGN.md` §0 | 10 | Rule of three, seeds per arm, Holm |
| 23 | `57_MOCK_INTERVIEW_ROUND3_BEHAVIOURAL.md` §A–B (check any number against `60` first) | 15 | Behavioural answers; 12 sceptic rebuttals |
| 24 | `42` derivations 4, 10, 11, 12, closed book | 30 | Check against the key |

Retired from these paths (superseded, not wrong to read later): `35` §2 → `68` §2; `40` Round B → `74`;
`57` §E.3 "not to say" → `60` ✗ partners + `RETIRED_CLAIMS.md`; `61` → `77` (first review's items resolved in AUDIT_61-63);
`77` §3–4 and `68` §3 → `84` §3–4; `78` §2 opener → `65` v2 §1a (same text).

### 3 days
Follow `42_STUDY_PLAN.md` (Day 1–3 tables, derivations, three design prompts,
day-of schedule). Use the R/D/H dossiers only by section, via the table below.

## Every report, with role and payoff

Role: **must** = in the 1-day path; **ref** = open by section when a topic comes
up; **arch** = superseded or process record, read only to trace a correction.
Words measured with `wc -w` on 2026-09-27.

| File | Words | Role | After reading it you can say… |
|---|---|---|---|
| 17 System design overview | 4,878 | must | "Here is the nine-stage pipeline, its data contracts and latency budget." |
| 18 Perception stack | 4,807 | must | "I'd pick this detector/tracker/ReID and here is how I'd handle 20–60 px people." |
| 19 Behaviour & intent analytics | 7,116 | must | "Base rates make a 7 %-precision alarm unusable; here is the FA funnel." |
| 20 Degraded imagery & fusion | 6,107 | ref | "Night/IR/codec/tamper each break detection this way; AND-fusion fails on correlated nuisances." |
| 21 Data, MLOps & governance | 5,365 | ref | "Splits, mixing, eval gates, drift, and where UK GDPR bites." |
| 22 Deployment & operations | 5,562 | ref | "Streams per box, health monitoring, per-camera cost, commissioning." |
| 23 Roadmap & gap analysis | 4,785 | ref | "SurvSim's gaps and M1–M11 with acceptance criteria." |
| 24 Synthetic-to-real evidence | 5,596 | ref | "MOTSynth/BEDLAM/PeopleSansPeople show when synthetic helps — diversity, not polish." |
| 25 Detection deep dive | 6,143 | ref | "YOLO/DETR losses, TAL, INT8 PTQ vs QAT, and AP by hand." |
| 26 MOT deep dive | 6,454 | ref | "Kalman+Hungarian through BoT-SORT, and MOTA/IDF1/HOTA worked." |
| 27 ReID deep dive | 5,620 | ref | "Triplet/BNNeck, clothes-change drops ~45 points, re-ranking." |
| 28 Behaviour & scene deep dive | 8,181 | ref | "i-LIDS/ActEV scoring and why frame-AUC VAD benchmarks mislead." |
| 29 Camera geometry & calibration | 6,618 | ref | "Pinhole, homography, DORI px/m, and the calibration error budget." |
| 30 Synthetic data & sim2real | 7,494 | ref | "DR vs photorealism, FID limits, and the gaps in our degrade chain." |
| 31 Interview Q&A | 9,329 | ref | "60 model answers and 10 whiteboard prompts" (overlaps 35; use 35 first) |
| 32 Experiments log | 12,405 | ref | "H1–H34 register (H1–H22, H25, H32–H34) with commits: what we measured, and the caveats." Source of truth for SurvSim numbers |
| 33 the vendor company brief | 1,960 | must | "[vendor product], [vendor product], [vendor product], the CNI line, who the directors are." |
| 34 Market & competitors | 1,629 | ref | "Where the vendor sits against Calipsa, Ipsotek, Vaion, Anduril etc." |
| 35 Interview playbook | 4,158 | arch (§1–2 pre-H12; use `68` §2) | "40 likely questions answered; traps; defence-context answers." |
| 36 Neuromorphic & SNN | 4,773 | ref | "What spiking/event sensing is honestly good for ([vendor product])." |
| 37 Multi-sensor fusion & tracking | 5,918 | ref | "JPDA/MHT, SAPIENT/BSI Flex 335, radar/RF fusion at a perimeter." |
| 38 Edge deployment for defence | 5,134 | ref | "Jetson/Hailo power budgets, INT8 calibration, offline updates." |
| 39 Audit round 3 | 864 | arch | Which "unverifiable" rows were resolved (applied in 41) |
| 40 Mock interview (round 1) | 6,817 | must | "Maths (A), CNI design (B), SurvSim sceptic (C) — ideal vs weak answers." |
| 41 Audit round 4 | 1,583 | ref | The numbers you must *not* quote (77.7 HOTA, 70 mW …) |
| 42 Study plan | 3,072 | must | The 3-day plan, 12 derivations, 3 design prompts, day-of schedule |
| 43 Video pipeline engineering | 6,205 | must (§7–8) | "RTSP/ONVIF/GOP; 40 cams → 4 Orin NX once detect+ReID compute is counted (3 = decode ceiling only)." |
| 44 Privacy law & ethics UK/EU | 7,415 | must (§3, §6.5) | "Bridges, SC Code, AI Act Annex III to 2 Dec 2027." |
| 45 VLMs & foundation models | 4,902 | ref | "Always-on VLM is ~0.36–1.1M tokens/cam-h; gate it on triggers." |
| 46 STAR stories | 6,139 | must | Twenty-six stories (18–24 from H32/H39/H40/M1/H22–H33/retired-claims registry/H26 retraction, each with a competency) plus rules for presenting negative results |
| 47 Character & asset licensing | 2,179 | ref | "MetaHuman bars AI train/test; SMPL-X bars surveillance; CC0 cast." |
| 48 Mock interview round 2 | 6,001 | ref | "Hostile follow-ups on synthetic value, engineering judgement, defence curveballs." |
| 49 Evaluation statistics | 4,794 | must (§0) | "Rule of three, ~25 seeds/arm for 0.02 AP, Holm, site leakage." |
| 50 Evasion, adversarial, tamper | 5,338 | ref | "Adversarial patches mostly fail physically; tamper detection needs cam-hours." |
| 51 Operator human factors & insights | 5,753 | must (skim) | "BS 8418, NPCC 3 false calls ⇒ response withdrawn, operator load." |
| 52 SurvSim technical brief | 4,462 | must | "What SurvSim is, [V]/[A]/[X], every number with a commit; 90 s/5 min/20 min pitch." |
| 53 Video data engineering at scale | 4,557 | ref | "400 cams × 30 d ≈ 311 TB; vector index sizing; WORM retention." |
| 54 State of the art 2025–2026 | 4,427 | ref | "YOLO26, D-FINE/DEIM, SAM 3, Qwen3-VL, Jetson Thor — current numbers." |
| 55 Formula sheets | 2,555 | must (part) | Every whiteboard formula with units and the sentence to say |
| 56 Glossary | 2,989 | ref | ~137 terms, 1–2 lines each, with doc § pointers |
| 57 Mock round 3 (behavioural) | 3,985 | must | "Ownership, founder disagreement, clearance, why-me; 12 sceptic rebuttals; logistics." |
| 58 Loiter rule redesign | 3,243 | must (§6, round 3) | "Shipped rule A1 (round 3) 2.915 FA/cam-h at actor-aware recall 0.825; still ~2,900× over our assumed budget. Round 4 (§8): A1 stays; its 2.915 is a θ-selection draw (5.033 at the adjacent θ)." |
| 59 Explainability, assurance, audit | 5,407 | ref | "Evidence packs, AMLAS, JSP 936, hash-chained audit logs." |
| 60 One-page cheat sheet | 2,445 | must | The last-hour sheet: 40 numbers in story order (built → buys → doesn't → operator → law → next → drift → twin answer), each with *so what* and ✗ retired partner; 10 formulas, 6 stories, pitch |
| 61 Cold-read review | 2,113 | arch | A fresh reader's 30 objections to the corpus (resolved in AUDIT_61-63; superseded by 77) |
| 62 Site context & zone semantics | 5,126 | ref | "Zone function cut FA 20.7 % vs a track-only GBM — short of the 25 % bar." |
| 63 Code tour & live demo | 3,064 | ref | "Show me the code", refreshed 2026-09-27 evening: today's module map (module → H → test), H53 experiments-framework read (run live, 27 s), fences + twins, TrackEval parity / actor-aware / conformal θ, doc-integrity tests, 3 "what would you change" answers; original 12-file tour + CPU demo condensed |
| 64 Technical report: sim2real & alarms | 7,933 | ref | arXiv-style report over H1–H20 + H58 r1–3 |
| 65 Dress rehearsal (v1, superseded by 65 v2) | 5,771 | ref | One timed 60-minute mock with derivations |
| 65 v2 Dress rehearsal — final-hour script | 4,283 | must | Post-H26/H45/H40b/H24/H51/H53/H54 script for interview day; 1-hour path reads §1, §3–§7 |
| 66 Hypothesis backlog | 2,893 | ref | Pre-registrable H21+ in the 49 §12 template |
| 67 Adversarial panel gaps | 3,637 | must | 5 interviewers × 12 questions; conformal θ, Art 22, ALARP |
| 68 Mock interview round 4 (technical) | 4,991 | must | Full 60-min panel, Q1–Q25, with hedges |
| 69 Night & thermal surveillance | 3,437 | ref | "Renders aren't dark (luma 90); 3/13 vis · 2/13 thermal vs LLVIP." |
| 70 Clothes-change ReID | 4,557 | ref | "CC-ReID collapses (MEVID 3.5 %); height + gait + topology." |
| 72 Insights & forensic search | 4,794 | ref | "Attribute search products, 40-cam index budget, attribute-vs-biometric line." |
| 71 Drift & MLOps for CCTV | 2,000 | should | "Per-camera monitors calibrated on the camera's own null. H34: PSI at 0.2 fires on every 1-s null window; z_cal detects 6/12 at 9.2 FA/24 cam-h; ρ 0.61." |
| 73 Tracking sim-to-real | 3,016 | should | "Association sees geometry, not texture: v8 5.4 vs MOT20 123.5 people/frame, vis 0.92 vs 0.57; box aspect +14 %; MOTSynth like-for-like IDF1 +1.7, not −4.3." |
| 74 System-design drills | 4,552 | must | "Three timed whiteboards: 40-cam perimeter (4 NX, 120 alarms/h at A1 → ~91 with the capped conformal θ 0.9618 (H33c), realised 0.618 ranked (H45c)), 3-site forensic search, 20-site drift/retrain loop with the licence gate." |
| 75 Camera geometry and calibration | 3,700 | should | Auto-calibration families (Sochor, GeoCalib, Vuong…), H39 known-height result (free f 57 m, not met; 0.21 m floor; height = trap metric), world tracking gates, PTZ re-cal, field failures, 10 Q&As |
| 76 Intrusion behaviours beyond loiter | 4,500 | should | Perimeter alarm classes, i-LIDS timing/α/distraction list, rule vs learned, SurvSim gap table, H40 line-cross result (not met; FA optimistic), H40b fenced-world result (0 clean FA, recall 0.782, twins ≈ 490× our assumed budget) + real-site caveat, 10 Q&As |
| 77 Cold-read review v2 | 2,033 | ref (superseded by 84) | Second interviewer-eye review: frictions fixed, 10 likely questions, 5 answers the corpus still can't give well |
| 81 Field alarm benchmarks | 2,500 | must (§2–3) | External FA anchors by interface: NPCC 3 false calls/12 months per system [V], i-LIDS 10 s/F1 0.7 [V], DOJ 94–98 % [V sec.], PIDS ~1/zone/day [A]; our 2.1–5.0 / 0.488 / 0.0047 placed against them; 0.001 budget provenance (invented A/K/H); defence OR (Pd at confidence, NAR/zone/day); 10 Q&As Audited AUDIT_81 (8.5/10; R56: every budget ratio now says *assumed*). |
| 82 Mock interview round 6 — process | 3,450 | must | Panel on *how you work*: 20 Qs on the H26 retraction, pre-registration (H32, H53 bar flaw, H42/H47 caveats), retired-claims registry + doc tests (39 / 31 / 105 hits), audit ledger (125 rows, 14 contradictions), shared-file collisions, disk full, PID/VRAM guards, weakest numbers; 1-page process narrative |
| 83 PTZ auto-track and hand-off | 3,500 | should | ONVIF PTZ (MoveAndStartTracking [V]), fixed→PTZ chain, zoom/latency budgets, contention; H56: 1 PTZ/40 cams misses 0.369 of alarms at 120/h vs 0.057 with 2; > 30 m acquire 0.727 (cause untested) |
| 80 Figure pack | 1,640 | must (§2–3) | Ten printable one-panel figures with 3 sentences + 1 trap each; lead with 02 (sim-to-real) and 03 (operating points) |
| interview_pack.pdf | 18 pp | must (bring) | Printable pack: openers, ship sentence, the 40 numbers with so-what/don't-say, the five gaps, the H26 retraction, drill-1 whiteboard, questions to ask, ten hardest questions, never-say list, then `80`'s ten figures — see `65` v2 §10 |
| interview_pocket.pdf | 2 pp | must (bring) | 2-page, large-type pocket version: openers, the ship/tracker/edge/tailgater sentences, the 12 most-used numbers, never-say list — see `65` v2 §10 |
| 84 Cold-read review v3 | 2,080 | must (§3–4) | Third interviewer-eye review: 15 frictions fixed, 1-hour path timed (11,598 → ~7,480 words), 10 questions, closed vs 5 open gaps (real-site alarms, night, clothing-change identity, Jetson latency, drift certification) |
| 92 Cold-read review v4 | short | must (§ frictions) | Fourth interviewer-eye review, same evening as `91`/H43d/H59/H61: fixed 78's stale "H61 not run" line and the pocket PDF's tailgater sentence (missing H59's 0.10 caveat); path re-measured at ≈ 8.2k words (≈ 54 min incl. aloud/recall, still ≤ 55); 5 questions to ask, 5 open gaps unchanged |
| 85 Defence context practicalities | 2,000 | should (§0, §10) | Vetting BPSS/CTC/SC/DV [V], classifications + FSC, export control incl. intangible transfers [V], DASA→UK Defence Innovation Feb 2026 [V], DEFCON 658, Cyber Essentials, DPA s.26 [V], Defence AI Strategy / ASR (15 Jun 2022) [V], STANAG 4676/4607 [A]; synthetic data under handling constraints; 10 Q&As |
| 86 Alarm evidence and explainability | 3,490 | should (§0, §7, §8) | Alarm card (30 s, H22) vs evidence pack vs WORM log; rule trace faithful, saliency not [V]; CRC guarantee is on the rate; ACPO v5 principle 3, BS 10008-1:2020, SCC §11.2 [V]; NIST AI RMF, ISO/IEC 42001:2023 and 27001:2022 [V], JSP 441 [A]; VLM caption on triggers only; SurvSim schema (AUDIT_86: emitted / join / not-emitted; GT match sim-only); 10 Q&As |
| 87 Mock interview round 7 — security and assurance | 2,670 | should | 15 Qs from a defence-AI security engineer on the H60 evidence pack: hash chain vs anchored head (tail truncation, re-chain), unsigned head / no trusted time, salted ids (public salt reversible), GT guard by key and value (hash of GT is GT), threat model in/out of scope, model_hash limits, DPIA/Art 22A–D, JSP 936, secure dev (no secret scanner, unpinned deps), first steps on a real site; never say tamper-proof / compliant / secure |
| 88 Coding drills | 4,620 | should (Drills 1, 3, 7; all 10 for a CV panel) | 10 whiteboard exercises (IoU/NMS/Hungarian/KF/ByteTrack two-stage/DLT/MOTA+IDF1/loiter hysteresis/conformal θ/bootstrap + sign-flip), each prompt, clarifiers, ≤ 40-line numpy, tests aloud, trap; runnable `drills/drills.py`, `tests/test_coding_drills.py` (19; AUDIT_88) asserts parity with survsim's `iou_matrix`, `_KF`, `dlt_homography`, `evaluate_mot`, `choose_crc`, `paired_contrasts` |
| 89 Demo reel script | short | should (if a screen-share demo is wanted) | 90-s voice-over + 30-s cut list for `out/demo_reel/survsim_demo.mp4` (built by `tools/demo_reel.py` from batch_v8 CC0 renders only — never batch_v4–v6 MetaHuman); GT-alignment gotchas found while building it (per-camera track ids, windowed-render absolute-tick filenames); all six numbers on the closing card grep-checked against `FACTS_VERIFIED.md` |
| 90 Mock interview round 8 — full 60-min run | 3,224 | should (day-of only) | One complete panel simulated end-to-end with a running clock: intro pitch, 8 technical Q&As (`68`/`79`) with pushback + 20-word replies, `74` Drill 1 as a live 3-box exchange with interrupt points, H26 retraction + `46` story 9 (MOT20 licence, chosen for a defence customer) + disagree-with-a-senior, the demo reel moment (`89`'s 30-s cut + 3 sentences), top-4 questions to ask (`78`), a 5-row scorecard (2/5 vs 4/5), and a 10-item night-before checklist |
| 93 Interview format plan | 2,785 | must (day-of) | New information on the real format (30-min technical chat, 1-hour VS Code coding block, 30-min whiteboard, not one 60-min panel): the 8 of 40 numbers to lead with, a 45-s opener, 3 questions for the chat; coding-task archetypes, a 60-min time plan, AI-tool-use etiquette, the 10 offline reference snippets from `88`, VS Code hygiene; `74` Drill 1 compressed to a 25-min whiteboard script with 5 pre-drawing questions; a revised night-before checklist that supersedes `90`'s |
| 94 Coding hour mocks | 1,038 | should (before the coding block) | Three complete ~50-min mock tasks for the 1-hour VS Code block under `docs/research/drills/coding_hour/`: tracker (IoU+Kalman, MOTA 0.908/IDF1 0.830/HOTA 0.671), loiter dwell rule (recall 1.0, precision 0.5 — still false-alarms on the hard negative, on purpose), video line-crossing counter (OpenCV + cached-detector stub, exact count 2); each with real mock-generated data, starter+tests+solution, a `TIMEBOX.md` and an `AI_TOOLS.md` naming the traps a generated first draft tends to have |
| 91 Mock interview round 9 — statistics | 3,277 | should | 15 Qs from an ML lead on how we know what we know: pre-registration vs peeking (H26), paired vs unpaired (H1), bootstrap unit = frames vs clips and why it matters (H47's clip-cluster CI), exact sign-flip tests and the n=4 floor (H47), Holm vs Bonferroni and when applied (H26/H51/H52/H46), min–max "CI" at n=3 is not one (H38), conformal B must be enforced not assumed (H33b→H33c), LOFO pooling overlap caveat (H42), garden of forking paths on a post-hoc argmax (H46→H46b), scoring artefact vs effect (H59), power of a null result (H24 vs the night arm), the retired-claims registry as a hygiene tool, and the false-positive I'd bet on (H51's mechanism story, not its number); 10-line glossary of the exact test functions used in `survsim/experiments/` |
| 78 the vendor talk tracks | 2,800 | must | Company facts re-fetched 2026-09-27 (Maven release [V], Matthews = Maven partner); per-product track (likely function, our H-numbers, 2 questions, 1 don't); 90-s defence-CCTV opener; first-90-days plan tied to 23 and 77 §4 |
| FACTS_VERIFIED | 7,815 | must (top-40) | The crib sheet; overrides every other file |
| AUDIT_01-16 | 4,116 | arch | Claim-by-claim audit of the R/D/H dossiers |
| AUDIT_17-24 | 6,458 | arch | Audit of the system-design series |
| AUDIT_25-38 | 9,930 | arch | Audit of the deep dives and playbook |
| AUDIT_43-47 | 2,159 | arch | Orin NX decode 18, Gemini tokens, 2026/1744 dates, licence clauses |
| AUDIT_48-51 | 1,239 | arch | Audit of 48–51 |
| AUDIT_52-53 | 573 | arch | Every 52/53 number traced to a commit |
| AUDIT_54 | 746 | arch | 2025–26 SOTA numbers re-fetched |
| AUDIT_55-56 | 822 | arch | Formula and glossary check |
| AUDIT_58_and_H12-H16 | 1,910 | ref | Recomputed H12–H16 headlines from results JSON (read if quoting H58/H14) |
| AUDIT_59-60 | 923 | arch | Assurance dossier and cheat-sheet check |
| AUDIT_LEDGER | 8,668 | must | One row per 2026-09-27 correction (194: 47 headline / 102 supporting / 45 cosmetic), by theme incl. fusion/twins, evidence pack/security, quantisation, PTZ/calibration, forensic search; process, open items, cross-audit reconciliation. Start here for "show me your process" |
| AUDIT_STALENESS_SWEEP | 713 | arch | Staleness sweep v2: night realism vs LLVIP, NX sizing, GREW/LTCC, register ranges, test counts swept against FACTS (v1 in git history) |
| RETIRED_CLAIMS | 982 | must | Registry of retired numbers (regex → correct form → audit); grep before quoting; `tests/test_docs_retired_claims.py` enforces |
| AUDIT_67-69 | 1,000 | arch | 67/68/69 audit: LLVIP per-modality training, Art 22B text, retired GBM −33 %, PRCC drop, night realism propagated; 78–80 → 96 |
| AUDIT_61-63 | 1,446 | arch | 61 cold-read items resolved; 62 sources fetched |
| AUDIT_64 | 867 | arch | Report 64: 96 numbers recomputed vs 32/58 (0 errors); H14b/H17 rows now unequal-step/pre-parity (see ledger) |
| AUDIT_65 | 839 | arch | 65 v1 re-traced: TrackEval/paired/D8 false claims fixed (superseded by AUDIT_65_V2) |
| AUDIT_65_V2 | 700 | arch | 65 v2: 115/115 decimals in FACTS, R54 overclaims row, fusion claims gated on H53, number test (85 → 100) |
| AUDIT_13_12 | 874 | ref | docs/13 + docs/12 vs FACTS/RETIRED: 11 stale forms fixed (HOTA 0.55 as current, "shipped" loiter labels, H16/H17/H25 step caveats, H32b 12→9 cams); 13 one-liners → one Experiments summary table; number test extended to docs/13 (137 RATCHET, not verified); 13 74 → 95, 12 88 → 94 |
| AUDIT_H19_H20 | 890 | ref | H19/H20 recomputed (ReID 0.228→0.249 corrected to 0.243; 23 ids retired → 28) |
| AUDIT_H22_H33 | 1,046 | ref | H22 operator queue, H33 conformal θ (338 simulated worlds, not sites) |
| AUDIT_ROUND4 | 1,127 | ref | Loiter round 4 (H21 + H23) recomputed from the JSONs; A1's 2.915 is a θ-selection draw |
| AUDIT_76_H40 | 1,096 | ref | H40 line-cross recomputed from results.json (all match; 6/100 re-derived); 76 URLs re-fetched; noise model labelled assumed; arm-C door-prop deviation; 74 → 99 |
| AUDIT_H40B | 1,151 | ref | H40b recomputed (all match); corrected: noise-free N residue is wildlife not commuters, recall loss is mostly the rule (10.1 pts noise-free) not fragments (7.0), gate-exemption nuance, 76 hard-negatives row restored; principle 1 holds for fence clamping; wildlife MOT 0,8 and excluded from dataset COCO (demo COCO path unfiltered); H49/H50 added; 73 → 97 |
| AUDIT_H53 | 900 | ref | H53 fusion recomputed (all match); corrected 2-4 pt recall cost → 2.3 combined, "robust" wording; true-position matching and the zero-loss bar design flaw stated everywhere; 78 claim reinstated in qualified form (R55); H54 added; 88 → 100 |
| AUDIT_H54 | 800 | ref | H54 tailgate + est-matching recomputed (all match; true leaves 18, est 19); 99.1 % stated as an upper bound (no-IDSW noise), prediction wrong optimistically; counter/GT caveats; 78 R55 sentence extended; H59 |
| AUDIT_H59 | 950 | ref | H59 (identity switches, calibrated/3x IDSW) recomputed (all match; verdict unchanged, not met, 3/4 criteria); traced code path + empirical extreme-hazard rerun proves swapped labels reach fusion matching and actor-aware scoring (1,322 swaps, 1 alarm scored under a swapped label); IDSW-rate arithmetic exact (83.4/1,904.6 = 157.6/track-h, h = 0.132029/close-pair-s); twin-removal insensitivity confirmed as a structural property of position-gated fusion, not an untested code path; tailgater collapse confirmed as an actor-aware scoring-denominator effect on C alone, not fusion or dwell breakage; batch_v8-vs-mot20 IDSW-source distinction noted |
| AUDIT_H47 | 1,100 | ref | H47 evasion recomputed (point estimates match); headline CI replaced by clip-cluster bootstrap (crowd −0.201 [−0.254, −0.154]; frame CI and Holm p 0.003 too narrow, 4 clips ⇒ p ≥ 1/16); "agree on every sign", VRAM 5.18 → 5,593 MB, "halves exposure" corrected; hood = colour proxy, props/crawl untested; runner registered; H55 added; 80 → 100 |
| AUDIT_83_H56 | 1,100 | ref | H56 rerun reproduces results.json; ≤ 20 m met on point only, 2-PTZ geometry explanation removed, missed ≈ busy share, far-field cause untested; 5 ONVIF [A]→[V], auto-tracking claim [X]; `ptz_slew` registered |
| AUDIT_84_85 | 1,100 | ref | 85: 11/11 [V] re-fetched (DEFCON 658 slug moved), ASR principles, CE+, ITAR/EAR (LII CFR), sponsorship → [V]; STANAG stays [A]; Q10 legal-determination fix. 84: 9 fixes hold, 1-hour path 7,477 words, gaps mirrored. 4-hour path trimmed to 240 (step 13 `17` 20 → 10 min); 42 Day 2 445 min |
| AUDIT_H60 | 564 | ref | H60 slice 1: leak 0/2 by key and value; guard missed zone names, verifier missed tail truncation / rehashed reason-less dismiss (fixed + tests); public default salt; 7/10 |
| AUDIT_87 | 1,150 | ref | 87 security round: Q5 leak guard over-stated (no identities cells; whole-string match) and Q7/63 "after the card is written" (verify never checks `cards.jsonl`) fixed; `!include` traversal reproduced at 70a4545, closed in a633a1d; R58 registry row (never say tamper-proof / bare compliant); 8/10 |
| AUDIT_88 | 947 | ref | 88 live-coding round: 3 reference bugs fixed (Drill 7 continuity used last-ever id → IDSW 0 vs survsim 1; Drill 3 solve-then-filter gate; Drill 6 unnormalised DLT claimed Hartley parity); conformal ⌈(n+1)(1−α)⌉ exact over n≤299; (f) line + 10/25-min slots; 19 tests; 7/10 |
| AUDIT_86 | 1,140 | ref | 86: 10/10 [V] re-fetched (NIST "role-appropriate" not on page; Adebayo is "some" methods); ISO 42001:2023 and 27001:2022 [A]→[V], JSP 441 stays [A]; 10 schema fields over-tagged fillable vs code; GT-match callout; 74 drill 1 log fields reconciled; H60 pre-registered in 66; 7/10 |
| AUDIT_78 | 900 | ref | 78 talk tracks as their CTO: all company claims re-fetched; opener H33 comparison inverted and H32 0.938 mis-sourced, fixed; architecture guesses and "your Ukraine set" removed; 30/60/90 carries 23 ranks; 6.5 → 9 |
| AUDIT_78_EVENING | 901 | ref | Evening staleness pass on 78 against 65 v2/32/38/58/73/84: opener byte-matched to 65 v2 §1a; added H24/H46b tracker recommendation and night-arm caveat; added H43/H43c/H43d edge status; fixed [vendor product]'s bare H54 0.685 (R61) with the H59 reconciliation; fixed [vendor product]'s stale H34 "no number" to its actual inconclusive result; named H61/H62/H36/H29 in the 90-day plan |
| AUDIT_93_94 | 900 | ref | Candidate run of 94's task 1 (tracker) end-to-end, no peek at solution/ until scoring: hit a real friction (unsmoothed carry-forward velocity fragments a real track into 17-25 ids on this jittered data, distinct from the FP-track trap the docs already named) — fixed in AI_TOOLS.md, README.md and test_tracker.py's assertion message, not in solution/; tasks 2/3 spot-checked at half depth (solution/ scores match each README exactly; clip.mp4 opens with OpenCV at 125 frames/12.5fps matching cached_detections.json's 1-based 1-125 key range); 93's 9 offline snippets confirmed present in drills.py, all ≤ 40 lines; 93's 5-min "tests first" phase has no counterpart in any of the three TIMEBOX.md files (flagged, not fixed — a style choice, not a factual error) |
| AUDIT_92 | 450 | ref | 92 audited: pack/pocket PDFs re-extracted and diffed against the six canonical sentences, all present with required caveats, no generator fix needed; 8,235-word recount reproduced independently (8,262, boundary rounding only); five open gaps and five questions confirmed to match 84 §4/65 v2 §4/78 §3; 00's stale 7,480-word 1-hour-path line updated to 8,235 |
| AUDIT_79 | 700 | ref | 79 round 5 audited: FACTS count 318 (was 282/279), realism + H11 rows fixed, R47 (H11 night figure) and tightened "was" exemption; H24 status, night weak answer, 6 overclaims; 7 → 9 |
| AUDIT_82 | 800 | ref | 82 process panel audited: all counts traced (31 is commit-message-only), H26 timeline matches git, 10 FACTS process rows (count 350), Q1/Q20 "wrong" → confounded, 46 story 23 registry 43 → 56 rows; 8 → 9.5 |
| AUDIT_75_H39 | 900 | ref | H39 recomputed from errors.parquet (all table numbers match); "8/10 at f bound" → 5/10; PTZ 48° → 30–35°; phantom IoU 0.90 cite; datasheet-f arm post hoc everywhere; regression test mutation-checked |
| AUDIT_H32 | 753 | ref | H32a/b night profiles: 9/13→2/13, 10/13→3/13 = overfit |
| AUDIT_H25 | 562 | ref | H25 label noise recomputed (27 runs, 6,879 s); "explains H15" retired → consistent with (dose 100 vs 300); unique-box share 16.9 % |
| AUDIT_H26 | 1,229 | ref | H26 fixed-step dose recomputed 14/21 (all numbers match); "pads seen 1-2×" wrong (2× / 4×), "60 % was steps" → equal-step gain is a third to a half of h14b's; 0.4857 is h14b seed 0 (paired step effect +0.0049); new headline +0.004–0.005 at equal steps, n.s. after Holm, propagated to 19 docs (R51); H51/H52 added |
| AUDIT_H51 | 1130 | ref | H51 equal-step re-run recomputed 19/26 (every number exact, Holm p 0.0039 both); h14b and H15 trained with mosaic off (close_mosaic 10 over 6 epochs) so the h14b/H15 gaps and real-only's +0.0049 mix steps, warm-up and mosaic; story now "+0.004–0.005 at equal steps, Holm-significant, small" in 20+ docs; R57; H52 unblocked |
| AUDIT_H52 | 900 | ref | H52 label/image/diversity ablation recomputed (all numbers match; label-driven); (b) < real is n.s., a − c exploratory (p 0.057), (c)'s box inpainting may leave a learnable artefact, (d) is a list-construction control; story sentence in 13 docs; H61 |
| AUDIT_H61 | 900 | ref | H61 silhouette-mask ablation recomputed (all numbers match: (a) − (c′) +0.0071 Holm p 0.0039, (c′) − real −0.0020 Holm p 0.074, (c) − (c′) +0.0056 context); dose0/dose300 reuse from H51 confirmed byte-identical; silhouette-mask mechanism (rendered ID-mask decode, per-frame median fill, no inpainting, no box) verified against `survsim/experiments/dose_fixedstep.py`; pre-registered rule selects box-fill-artefact, not background-real — H52 (c)'s +0.0036 was the box-shaped Telea-inpainted fill; one consistent H52/H61 sentence replaces the old "~70 % survives / background contributes" wording in all 13 docs (R63); (c'') ignore-region arm still not run; 9/10 |
| AUDIT_NARRATIVE_POST_H26 | 1,050 | ref | Post-H26 sim-to-real story (52 §5b + 9 mirrors) audited 17/27: all numbers match FACTS; H37/H47 removed from "reliably buys", "proved"/"came mostly from steps" overclaims fixed, commits cited; H16/H17 unequal-step caveat propagated (R52/R53); FACTS recount 324 |
| AUDIT_H34 | 700 | ref | H34 drift monitor recomputed from results.json (all numbers match); 1-check/min cadence and bootstrap CI method stated; emb "above every window mean" and codec-threat claims corrected; H44 added |
| AUDIT_H38 | 763 | ref | H38 quantised export recomputed: all AP/loss values match; n = 3 "bootstrap CI" = range; INT8-vs-FP16 CPU speed retracted; site-footage calibration claim scoped to off-site; results section restored to 32; 14.5/21 |
| AUDIT_H42 | 844 | ref | H42 θ-selection policy recomputed: all numbers match, LOFO confirmed; zero pooled spread partly by construction (LOFO overlap 8/9); θ 0.9 is a coarse-grid artefact; ship point reframed as operator-budget trade-off (58 §8.4), H45 added; 19/21 |
| AUDIT_H43 | 1135 | ref | H43 PTQ-calibration recomputed: per-checkpoint and corpus AP75 recovery all match (0.510/0.314/0.434/0.118/0.679, mean-loss-based 0.415 all 5 / 0.424 h14b-only, both < 0.50 bar → not met, 0/5 regressed vs MinMax); n = 5 bootstrap confirmed genuine (not min/max like H38's n = 3); Entropy/QAT n = 1 not scored, no latency claim (R46); stale downstream status (60 item 37, 66 row 15b) updated, H43b added; 9/10 |
| AUDIT_H43BC | — | ref | H43b (QAT, full 5-checkpoint corpus) and H43c (learned-range QDQ export fix) recomputed: per-checkpoint AP75 recovery 0.072/0.433/0.451/0.450/0.442 (H43b, pooled 0.366) and 0.266/0.322/0.561/0.615/0.429 (H43c, pooled 0.439) all match; AP-loss bar 3/5 over (H43b) and 4/5 under (H43c); "ranges carried" is a real byte/float check, 5/5; no pytest regression test guards the Conv-order weight-byte-matching fix (flagged, out of scope to add); the "shortfall is the recipe, not the export" line was a one-data-point inference stated as fact in 5 places — hedged and given a follow-up, H43d (66); edge-deployment answer unified to one sentence across 38 §2.5/60/65 v2/68/77; no latency claim anywhere (R46); 8/10 |
| AUDIT_H43D | 1281 | ref | H43d (600-iteration QAT fine-tune, same learned-range export) recomputed: per-checkpoint AP75 recovery 0.331/0.531/0.782/0.077/−0.500 and pooled 0.374 (vs H43c's 0.439) all match `results.json`; `qat_fp32` beats `fp32_torch` on all 5 (confound check, no degradation); "hypothesis not supported" tightened to "refuted" in `32`; the −0.500 on `dose300_s1` explained as INT8-quantisation-specific (its `qat_fp32` loss is exactly 0.0000, ruling out generic overfit) and tied to `dose300` being H51 `equal_steps` checkpoints vs `mix_300`'s h14b recipe (config-verified); 600-iter LR (1.19e-05) matches H43c's recipe scaled, not a different/riskier LR; QAT-closing clause ("longer QAT (600 it) does not help and hurts two checkpoints (H43d) — remaining loss is INT8 quantisation of this architecture, not the fine-tune") added to `38` §2.5/`68` Q10/`65 v2` §4/`77` #3/`78` (78 was stale, still said H43d "running, not yet resolved"); `66` gets H43e (TensorRT INT8 on real Jetson hardware, the un-run arm of H43, needs hardware); no latency claim (R46); 9/10 |
| AUDIT_H24 | 870 | ref | H24 ReID-in-ByteTrack recomputed: all numbers match; verdict (not met by 0.0006) on the registered per-sequence statistic, pooled +0.0338 exploratory; MOT20 rise n = 5 (sign-flip p 0.19), GT-box CI spans 0, "never lowered AssA" → means only (R49), night arm omission → H46; 73 'only through detection' revised to synthetic *data*; 18/22 |
| AUDIT_H46 | 880 | ref | H46 w-sweep + night arm recomputed: ΔAssA/ΔDetA/ΔHOTA rise and ΔIDSW falls together at every w on both sets (no trade-off); w = 4's argmax "clears H24's bar" is a post-hoc pick from the same 5-arm sweep and does not survive Holm correction (p 0.025 vs threshold 0.010) — deferred to H46b's cross-set validation; night arm (−0.0147, CI 0.15 wide) honestly called underpowered; w → ∞ in `bytetrack.py` is appearance-only assignment with the IoU gate still enforced after, not gate removal; RETIRED_CLAIMS R62 added; 8.5/10 |
| AUDIT_H46B | 881 | ref | H46b extended sweep (w∈{8,16,32}+app_only) + cross-set validation + full night arm recomputed exactly from `results.json`: day argmax w=16 (+0.0613, IDSW −0.22 n.s.), mot20 argmax w=8 (+0.0486, IDSW +15.8 CI excl. 0); app_only worst arm (ΔIDSW +162.0 mot20, ΔDetA −0.0109); cross-validation confirmed no-peeking (argmax and held-out evaluation on disjoint sets, both directions clear +0.02); all 3 pre-registered verdicts (ceiling yes / held-out met / night CI not met) match; ΔHOTA already reported per row (H46's gap, fixed here); `fig_h46b.png` had never been generated despite being named in prose — generated and referenced from 32/13; reference-tracker sentence ("w≈8, cross-validated, never appearance-only") folded into 73/60/48/65v2/79/23/66, R62 updated; 9/10 |
| AUDIT_H45 | 972 | ref | H45 operator sim at the three H42 points recomputed: all numbers match; streams reproduce H42 model points and H22 A1 cells exactly; H22 behaviour unchanged; 'modal' CRC draw = most permissive of 10 distinct draws; 2-op conformal loss is consistent (0/10), not a tie; ship recommendation made measured in 58 §8.4 and propagated; H48 (real SOC review times) added; 18/20 |
| AUDIT_H33B | 900 | ref | H33b fixed-B conformal recomputed: all numbers match, but B = 123.5 is not a valid a-priori bound (the ≤ 1-alarm-per-visitor cap is unenforced; up to 21 episodes per visitor) — guarantee exact for min(L, B) only; certified θ 0.963436 = 2.187 / 0.783; H45b measured it: 0.617 ranked @5 min, 1 operator, ship rule unchanged; 15/20 |
| AUDIT_H33C | 905 | ref | H33c/H45c capped-conformal recomputed: all numbers match results.json (uncapped 2.216/0.784; capped1 2.223/0.787 +0.004 recall; capped2 1.908/0.773; equal-θ FA cut 3.4 % vs ≥ 20 % predicted → partial; 10/10 splits ≤ α; B valid for capped1; certified θ 0.961780 = 2.196/0.789, 90.6 alarms/h, H45c realised 0.618 ranked @5 min, +0.032 vs A1); reconciled AUDIT_H33B's 53 % repeat-visitor *episode* share with the 3.4 % FA cut — only 28.8 % of alarms at θ ≈ 0.9618 are repeat-visitor alarms; H59 line added to §H33c caveat (label-keyed cap not tested by H59, whose fusion legs are position-keyed); ship story canonicalised once in 58 §8.4 and mirrored in 60/48/65v2/78/74; figure 3 regenerated at the capped point; 20/20 |
| AUDIT_91 | — | ref | Mock-interview-round-9 statistics doc (91) audited as a panel statistician against AUDIT_H26/H47/H51/H38/H33B/H33C/H42/H46/H59: Q4's n=5/n=6 sign-flip floors had the one-sided/two-sided numerator swapped (1/2^n vs 2/2^n) — fixed; Q7 compared the wrong "fixed, invalid" θ (0.9629, H45's pre-B-fix point, not AUDIT_H33B's own 0.963436) and mixed a pooled FA with a held-out-mean recall — fixed; two glossary rows misnamed/mislabelled a function (`boot_p_two_sided()` unnamed; `bootstrap_delta()` called "clip-cluster" when it is frame-level and exactly the CI AUDIT_H47 found too narrow) — fixed; Q13's "false positive" bet was checked against AUDIT_H51's actual scope (mosaic confounds the h14b/H15 cross-study story, not H51's own ten-seed contrast) and found already correctly framed, no fix needed; 26/30 |
| AUDIT_FIGURES | — | ref | Audited every `fig_h*.png`/`fig_box_aspect.png`/`fig_tracking_stats.png` produced 2026-09-27 against `32`, `64`'s Appendix A and `13`'s figures index: all files exist and all on-figure numbers match `FACTS_VERIFIED.md` (10-point abstract spot-check also clean, no defects); the only real gaps were missing cross-references, not wrong numbers — `fig_h32.png` was Figure 7 in `64`'s body but absent from its Appendix A list (added); `fig_h34.png`/`fig_h39.png`/`fig_tracking_stats.png` and 20 single-hypothesis diagnostic PNGs (h33b/c, h40/h40b, h42, h43/b/c/d, h45, h46/b, h47, h51–h54, h56, h59, h61, box_aspect) were referenced from `32` but not from `64` or `13` — a new figures index appended to `docs/13_BASELINES.md` and an `H39` figure line in `32` close the gap; no retired-claims regex hits in the new text (`test_docs_retired_claims.py` and `test_docs_numbers_in_facts.py` both pass); no figure needed re-rendering. See `docs/research/AUDIT_FIGURES.md` |
| AUDIT_70_73 | 700 | arch | 70/73 audit: MOTSynth 53.8-vs-58.1 re-retired, 11 not 12 cams, GaitV2 FLOPs per frame, CAL Table 6 reading; 70: 84 → 96, 73: 76 → 95 |
| AUDIT_74 | 650 | arch | 74 drills audit: 5-NX spare fix, PAR/CLIP off the NX, alarm→audit + human-decision box, DUAA/JSP/PSTI instruments, observable rubrics; 74 → 93 |
| AUDIT_M1_PARITY | 900 | ref | M1 TrackEval parity re-run: max \|Δ\| 1e-15 all cases, old code = 0.4342; 1e-3 test tolerance; H9/H17 pre-parity; 88/100 |
| AUDIT_72 | 623 | arch | 72 vendor claims fetch-verified (BriefCam → Milestone names) |
| AUDIT_90 | 950 | ref | 90 mock-interview-round-8 audited: found and fixed a self-contradicting θ mislabel (pooled θ 0.9, not A1 θ 0.95, floods the operator queue — matches 74/65v2); word budgets, retired-claims scan, H26/H51 framing, ship/fusion canonical sentences, 74 drill-1, 46 story 9, 89 reel moment all check out; R56/R05/R18/R54 registry rows confirmed accurate on 90's actual text, no regex tightening needed; H54/H59 tailgater nuance flagged as a watch item; 9/10 |
| AUDIT_TAILGATER_RECONCILIATION | 550 | ref | Re-verified H59's attribution of the tailgater collapse to actor-aware scoring, not fusion (calibrated-arm C alone recall@10 0.108 vs C+abcg 0.100, from `h59_idsw_fusion` results.json); computed a label-agnostic (window-only, position/time) recall from the same cached alarms in `fused_worlds.jsonl`: 0.828 (C) / 0.739 (C+abcg), confirming most of the 0.685→0.10 collapse is a scoring artefact of crediting the alarm to a swapped `uid`; one reconciled sentence added to 32 §H59 and mirrored in 76/78 (R55)/65v2/74/48/60/90/13/52/64/84; RETIRED_CLAIMS R61 added (bare "tailgater … 0.685" without an H59/ID-switch marker); 66 H62 pre-registered (position/time-keyed alarm scoring as the tracker-fed default) |
| AUDIT_H62 | 1,050 | ref | H62 (position/time-keyed scoring) recomputed from `results_calibrated.json`/`results_benign.json` — all match exactly (recall 0.685/0.715/0.725, false-credit 14.8/31.3/49.3 %); confirmed the static-vs-dynamic actor-position deviation is stated everywhere H62 is quoted; added `fig_h62.png` to `docs/research/figures/` and referenced it from 32/13; proposed (not implemented) a time-varying-`actor_pos` follow-up for `alarms.score` and a condensed principle-4 sentence for CLAUDE.md; verdict unchanged, partially met; 96/100 |
| AUDIT_H37 | 890 | ref | H37 forensic-search mock slice recomputed exactly from `results.json` (diffs +0.0004/−0.0118); fixed the imprecise "CI includes 0 at both noise levels" claim (true only at 10 % noise; not-met verdict rests on the 0.15 magnitude bar regardless); added the missing mechanism — relevant-set sizes mean 2.67/max 9, all ≤10, so recall@10 is a ceiling metric by construction, explaining the 137 unscored queries and why the unit-confirmed pooling trap doesn't register at population level; filed H37b (recall@1/MRR or larger identity pool, CLIP arms) in 66; corrected 6 stale "H37 has no number"/"pre-registered" mentions in 60/65v2/78/79; 100/100 |
| AUDIT_H63 | 700 | ref | H63 uniformed-intruder recomputed from `h63_uniform_mismatch/results.json` (all numbers match); confirmed the pre-registered 0.8 absolute recall bar for arm (b) sits above line-cross arm C's own 0.775 ceiling and is recorded as a registration error, not re-scored (32 already stated this correctly); confirmed the "time leg never fires" caveat (roster = every twin on shift the whole world) and the 95 %/2 % role-classifier assumption are both stated; position-keyed = actor-aware because H54's noise model has no ID switches; folded the numbers into 60 (item 14 replaced), 65 v2 §6, 78 §1.5, 79 (already correct), 99 §3 (already correct), 100 (already correct), FACTS (already correct); H63b (rostered-hours + role-classifier sweep) filed in 66; 100/100 |
| AUDIT_02_03 | 521 | arch | docs/02 and docs/03 checked against `director/behaviours.py`/`fences.py`/`eval/*`/`experiments/*`/`sensors/degrade.py`: fixed stale catalogue rows (`vendor`, `worker_patrol`, `graffiti_vandalism`→`vandalism`, `mass_rush`→`crowd_rush`, `drone_intrusion`→`drone_overflight`), added the missing `fence_tailgate`/`staff_escort` twin, added fences/appearance-epochs/alarm-cards/evidence-pack/TrackEval/experiments/7 degrade profiles (2 night ones LLVIP-overfit)/licence gate/principles to 02, and corrected 02's backend section off "UnrealCV+ over TCP" to the editor+job-runner route |

The R/D/H dossiers (R01–R06, D01–D08, H01–H02; 9k–24k words each) are **ref**
for section lookup only; their table is below.

## Provenance tags (read this first)
Every dossier states its sourcing conditions in its §0. Tags used throughout:
- **"quoted text" + link** — text retrieved from a source (mostly via search-index extracts; primary pages were often blocked by the network proxy).
- **[VERIFY]** / **[V?]** / **[unverified]** — real source, wording or figure not re-verified. Check before quoting externally. Counts per doc are listed below.
- **[paraphrase]** / **[secondary]** — accurate summary of a linked source.
- **[INF]** / **[inference]** — the author's inference, marked as such.
- **[lore]** / **[expert-knowledge]** — practitioner knowledge, not from a document.
- **[derived]** / **[BOE]** / **[ARITHMETIC]** — first-principles calculation shown inline.
- **[NR]** — not researched (budget). Each doc ends with a verification backlog.

Environment constraint disclosed: the session's web-search allowance (200 calls) was
shared by all agents and ran out partway through waves 1 and 2; most non-GitHub
domains were blocked by the egress proxy. No quotations were fabricated; gaps are
flagged rather than filled. A second pass with a larger search budget should work
the verification backlogs (see each doc's final section).

## The corpus (R/D/H dossiers)

| Doc | Words | [VERIFY] | One-line content |
|---|---|---|---|
| R01 detection & single-camera MOT | 11k | 0 | What CCTV footage really is; detector/tracker history to 2026; metrics; edge deployment; failure modes; sim2real numbers |
| R02 multi-camera tracking & ReID | 11k | 0 | Overlapping vs non-overlapping MTMC, calibration in the wild (error budgets), ReID incl. clothes-change/gait, disguise, face in CCTV & law |
| R03 behaviour / intent / anomaly | 16k | 0 | Industry definitions (loiter, tamper, abandoned object), i-LIDS/ActEV protocols, VAD SOTA, hostile-recon science, human factors, law |
| R04 degraded imaging & sim2real | 15k | 0 | Imaging chain physics, quantified degradation, mitigations, IQA/tamper, full synthetic-data history & evidence |
| R05 multi-sensor fusion & NL retrieval | 17k | 9 | PIDS/RF/audio/radar/DAS, fusion methods & standards, video-language retrieval, live monitoring, failure modes |
| R06 the vendor company & people | 9k | 0 | public registry facts, products ([vendor product], [vendor product], [vendor product]), staff, UK ecosystem, competitors, interview cheat sheet |
| D01 history & evolution | 23k | 7 | 1942→2026 institutional history, timeline table, 18 dead ends, 18 predictions, hop chains |
| D02 people & labs map | 16k | 79 | Researchers/lineages by subfield, who to follow, venues calendar, 60-paper reading order |
| D03 industry map & market | 23k | 34 | Market sizing caveats, ~100 company profiles, M&A/funding, buyers & tender language, the vendor positioning, 15 product implications |
| D04 deployment system architecture | 19k | 11 | Camera→network→VMS→edge/cloud inference→messaging→fusion/C2→operator; standards; security; 3 sized reference architectures; how SurvSim plugs in |
| D05 spiking nets & neuromorphic | 18k | 51 | SNN/event-camera history, SOTA, defence programmes, honest assessment, [vendor product] read, event-sim plan, 6 experiments |
| D06 users & field reality | 18k | 55 | Operators, CNI, border, police, MOD, events; requirements table; pilot-failure causes; 8 personas; interview questions |
| D07 frontier & future | 16k | 27 | Foundation/video models, agentic surveillance, world models, privacy tech, obsolete/easy/hard, 25 features to add, 15 not to build, 2026-35 scenarios |
| D08 simulator engineering craft | 20k | 7 | UE5/UnrealCV/MetaHuman/Mass pitfalls (61), GT correctness tests, storage math, licences, week 0-8 build recipe |
| H01 veteran questions: perception | 22k | 0 | 165 Q / naive / veteran / SurvSim items + Top-25 + 15 testable hypotheses |
| H02 veteran questions: behaviour, fusion, ops | 22k | 14 | 156 items + 25 the vendor-specific + Top-25 + 15 hypotheses + how to talk to Dstl vs operator vs bid writer |

## System-design series (17–23, added 2026-09-26)

A second pass that turns the 16 dossiers into a design for the real product and
a plan for SurvSim. Same provenance tags; figures recalled from primary papers
but not re-fetched are **[VERIFY]**. Each report cites repo numbers
(docs/11, 13, 15, 12) and states what SurvSim must emit for each component.

| Doc | Words | One-line content |
|---|---|---|
| 17 system design overview | 4.7k | Nine-stage pipeline (ingest→decode→detect→MOT→MTMC→behaviour→alarm policy→UI→audit), data contracts, latency/throughput budgets, edge/on-prem/cloud placement, failure modes |
| 18 perception stack | 4.7k | Detector/MOT/ReID choices with benchmark tables, 20–60 px strategy, calibration error budget, PTZ, sim→real recipes, export/quantisation, failure-analysis order |
| 19 behaviour & intent analytics | 6.5k | Taxonomy with hard negatives, rule vs learned, i-LIDS scoring, FA budget arithmetic, worked alarm funnel, recon indicators, labelled-data spec |
| 20 degraded imagery & fusion | 6.0k | Night/IR/thermal/weather/codec/tamper, RF/radar/PIDS/audio, fusion levels, correlated nuisances, consistent sensor simulation, augmentation recipe |
| 21 data, MLOps & governance | 5.3k | Splits, synthetic+real mixing, active learning, evaluation harness and gates, drift, registry, UK GDPR/Surveillance Camera Code/EU AI Act, coverage-driven verification |
| 22 deployment & operations | 5.4k | Streams per GPU/Jetson, DeepStream graph, resilience, health monitoring, operator workflow, SLAs, per-camera cost model, commissioning |
| 23 roadmap & gap analysis | 4.7k | Component-by-component gaps vs repo state; milestones M1–M11 with measurable acceptance criteria; risks |
| 24 synthetic-to-real evidence | 5.0k | Verified survey (20 sources) of sim2real for pedestrian det/MOT/ReID: MOTSynth, JTA, PeopleSansPeople, BEDLAM, PersonX, RandPerson, UnrealPerson, ClonedPerson, Alice, etc.; numbers and implications for the training mix |

## Interview deep-dive series (25–31, added 2026-09-26)

First-principles explanations (intuition → equations → worked numbers), every
fact cited to a primary source fetched in-session; unfetched items are
**[VERIFY]**, arithmetic **[derived]**. Each ends with "how to say this in an interview".

| Doc | Words | Fetched cites | One-line content |
|---|---|---|---|
| 25 detection deep dive | 6.1k | 21 | Anchor-based/anchor-free/DETR; YOLOv8/11 losses & TAL; RT-DETR; small objects (SAHI, P2); INT8 PTQ/QAT; ECE; hand-worked AP; how to read docs/12–13 recall tables |
| 26 MOT deep dive | 6.4k | 9 | Kalman/Hungarian; SORT→DeepSORT→ByteTrack→OC-SORT→BoT-SORT equations; CMC; MOTA/IDF1/HOTA worked 3-frame example; MOT20; audit of repo ByteTrack (repo DetA ignores FPs → HOTA optimistic) |
| 27 ReID deep dive | 5.6k | 15 | ID/triplet/circle/BNNeck; OSNet, TransReID, CLIP-ReID; clothes-change (PRCC/LTCC); ST priors; re-ranking; worked CMC/mAP; biometric law; gait module & appearance epochs |
| 28 behaviour & scene | 7.8k | 13 | i-LIDS/PETS/ActEV definitions & scoring; rules vs trajectory models; social force vs crowd.py; VAD methods & benchmark flaws; false-alarm economics |
| 29 camera geometry | 6.5k | 9 | Pinhole/K/[R|t], ground homography, Zhang, Brown–Conrady, PTZ; DORI vs IEC 62676-4:2025 levels; coverage & error maths on repo rigs |
| 30 synthetic data & sim2real | 7.4k | 20 | DR vs SDR vs photorealism; FID/KID equations & limits; generative P/R; critique of docs/15 stats; CCTV render chain vs degrade.py gaps |
| 31 interview Q&A | 9.2k | 22 | 60 model answers (100–250 words) + 10 whiteboard design prompts with probes |

## Audit and prep (39–42, added 2026-09-26)

| Doc | One-line content |
|---|---|
| 39 audit round 3 | Re-checks of the AUDIT_01-16 "unverifiable" rows against primary sources (the corrections are applied in 41) |
| 40 mock interview | Three adversarial 45-min rounds (maths, system design, behaviour/company) with ideal, weak and follow-up answers |
| 48 mock interview round 2 | A second adversarial pass (C1–C6+) reconciling prior rounds against later audits — Orin NX decode, VLM cost model, gated-VLM ratio consistency — ideal/weak/follow-up scorecard |
| 41 audit round 4 | Round-3 corrections applied to R/D/H; the rest of the AUDIT_01-16 queue cleared (GAO towers, mmWave, φ-OTDR, D01 dates, D02 affiliations); a list of what is still unverifiable |
| 42 study plan | A 2–3 day timed prep plan: reading minutes, the 12 derivations with an answer key, 3 design prompts, the pitch, and a final-hour checklist. **Start here if the interview is soon.** |
| 43 video pipeline engineering | RTSP/RTP, ONVIF S/T/M (Profile S retiring 2027), GOP/B-frames and I-frame-only inference, NVDEC limits, DeepStream graph, clock sync, backpressure, Milestone/Genetec integration, worked 40-camera budget (4 Orin NX with compute; 3 NX / 2 AGX = decode ceiling only), health metrics |
| 44 privacy law and ethics (UK/EU) | UK GDPR/DPA 2018, ICO guidance, Surveillance Camera Code, biometric definitions, Bridges holdings, EU AI Act + Digital Omnibus 2026/1744 (Annex III to 2 Dec 2027), MetaHuman licence bars AI training/testing use, export control; 13-step checklist |
| 45 VLMs and foundation models | Open-vocabulary detection (Grounding DINO, OWLv2, YOLO-World), VLM anomaly detection (LAVAD, VadCLIP, Holmes-VAU), per-camera-hour cost model (~0.36M tokens/cam-hr at 1 fps default resolution, ~1.1M high-res; audited), VLM as verification stage, hype check |
| 46 STAR stories | Twenty-six behavioural stories from this repo (black render, HOTA fix, stuck agents, VRAM guard, synthetic-hurt, loiter rule, alarm funnel, variety gate, MOT20 licence, hung engine, profiling, histogram-vs-OSNet, CC0 cast), numbers reconciled with committed `32` with metric, lesson and two levels of follow-up |
| 47 character and asset licensing | MetaHuman (bars AI train/test), SMPL-X/BEDLAM (bars surveillance), Reallusion §2.1.2.C.5 (bars ML), CC0 stack (Quaternius, ambientCG, Poly Haven, Kenney) as render default |
| 49 evaluation statistics and experiment design | Bootstrap CIs for AP (images vs blocks vs sequences), binomial recall on small n, seed counts from H1 sd 0.025 (~25 seeds/arm for 0.02 AP), paired vs unpaired, Holm/BH, rule of three (400 cam-h ⇒ < 0.0075 FA/cam-h; 0.001 needs ~3,000), McNemar, MOT20-01/02 site leakage, calibration/ECE for thresholds, CUSUM drift, pre-registration template applied to H1 and the tight-GT rerun; resolves the 50–150× vs 170–400× VLM gating ratio |
| 50 evasion, adversarial robustness and tamper | Thys 2019 (YOLOv2 recall 100→26.46 %), adversarial T-shirt (57 % physical), Wu 2020 transfer asymmetry, Hu 2022 (mASR 0.79→0.26 over 1.6–7 m), patch-defence benchmark, thermal bulbs, laser; tamper detection (Ribnick, Mantini & Shah, 2026 streaming: 0 FA in 9.09 cam-h ⇒ only < 0.33/cam-h); red-team protocol; all 52 evasion.py techniques mapped to literature and testability |
| 51 operator human factors and insights | BS 8418:2021, NPCC Mar 2024 (3 false calls/12 months ⇒ response withdrawn; App. R RVRC rules), vigilance evidence (Donald 2015 50 % detected; screens delay detection), operator utilisation U = C·B·t/3600, alarm-card UI patterns, insights (counting, occupancy, dwell, flow, heatmap, PPE, near-miss) with SurvSim GT validation and privacy posture |
| 52 SurvSim technical brief | One 20-minute read: architecture diagram, [V]/[A]/[X] table, every number with commit hash (44/49 behaviours, 52 evasion, 0/60 scene misclassified, 7 200 frames ≈ 46 min, stuck 34.6/49.1 % → 0 %, realism 6/14 · 3/14 (3/13 vis · 2/13 thermal vs LLVIP), H1–H22 + H32/H33, HOTA 0.545→0.434→0.443 (TrackEval parity), tight-GT IoU 0.781→0.884 in progress), gaps, M1–M11, 90 s / 5 min / 20 min pitches |
| 53 video data engineering at scale | 1080p H.265 2.4 Mbit/s ⇒ 311 TB for 400 cams × 30 d; S3/B2/Wasabi prices; FAISS/pgvector sizing (104 M 512-d vectors: 213 GB flat, 7.5 GB IVFPQ); Object Lock WORM + BS 10008-1:2020; label noise ≥ 3.3 % (Northcutt 2021), SemDeDup 50 %; loose-box QA; SC Code P6/ICO retention, DPIA Art 35(3); 400-camera design; 8 Q&As |
| 54 state of the art 2025–2026 | Fetched-number update: YOLO26 (n 40.9→x 57.5 COCO, NMS-free) vs YOLO11; D-FINE/DEIM/DEIMv2 (X 57.8); YOLOE, DINO-X; SAM 3 (Nov 2025); DanceTrack 71.3 (MAT) vs SORT 67.9; SAM2MOT; CC-ReID 2025–26; UCF-Crime ~89.9 (NOVA) + frame-AUC critique; Qwen3-VL 256K, SmolVLM; Gen1 SNN 26.9; Jetson Thor $3,499, Orin Super, Hailo-10H; DUAA s.80, Omnibus 2026/1744; re-baseline table; 8 Q&As |
| 55 formula sheets | Whiteboard-from-memory formulas, each with symbols, units, the sentence to say and a § citation: IoU/CIoU/NMS, COCO AP, focal/DFL, Kalman, Hungarian+gating, ByteTrack, MOTA/IDF1/HOTA worked, ReID losses/metrics, pinhole/H/Brown, DORI, EV100, GOP/bitrate, Wilson/rule of three/power/McNemar/Holm, JPDA, GM-PHD, INT8, LIF; unfetched forms tagged [VERIFY] |
| 56 glossary | ~137 interview terms (ops/standards, video pipeline, detection, MOT, ReID, sim2real, behaviour, defence, neuromorphic, UK/EU law, data/statistics, SurvSim) with 1–2 line definitions and the doc § where each is treated |
| 57 mock interview round 3 (behavioural) | 15 behavioural/culture Qs (ownership, unseen data, founder disagreement, clearance SC/DV from gov.uk UKSV pages, remote) with STAR ideals from 46 and weak answers; 12 sceptic claims with hash rebuttals; 3 role shapes + why-me; 12 questions to ask; day-before/day-of; 10 things not to say |
| 59 explainability, assurance and audit trails | Saliency vs TCAV vs rule trace (Adebayo 2018 sanity checks), per-alarm evidence pack, model cards (Mitchell 2019) and datasheets (Gebru 2021), GSN v3 / CAE, AMLAS six stages (York 2021), JSP 936 checklist, what SurvSim gates/pre-registration provide vs gaps, hash chains + RFC 6962 Merkle logs + BS 10008-1:2020, drift/CUSUM and incident loop, HITL accountability; worked loiter-alarm assurance case (C4 2.92 FA/cam-h, floor 1.008, 6/14 realism, CC0 provenance); 8 Q&As |
| 60 one-page cheat sheet | The last-hour sheet (~2,400 words): 40 numbers in story order copied from FACTS_VERIFIED (test-enforced), each with *so what* and ✗ retired partner, 10 formulas from 55, 6 stories from 46, 7 things not to say, the 90-second pitch, 3 questions to ask |
| 62 site context and zone semantics | Site-profile design (7 layers: geometry, typed zone function vs policy, portals, timetables, occupancy prior, patrols, roles); ONVIF LoiteringDetector = polygon + TimeThreshold only, Axis OA/Perimeter Defender schedules and conditional zones, Milestone MAD events; zone-function inference from tracks (Stauffer–Grimson 2000, Makris–Ellis 2005, Morris–Trivedi 2008, Wang 2009); OSM entrance/indoor/opening_hours + IFC occupancy import; SiteProfile schema + Director clock; context-ablation ladder D1–D8 with leakage gates (round 3: 3.114→2.468 FA/cam-h, −20.7 %, P8 fails); ICO DPIA implications; 8 Q&As |
| 63 code tour and live demo | "Show me the code" (refreshed 2026-09-27 evening: Part 0 module→H→test map for today's code, Part A H53 framework read run live 27 s, Part B fences + twins, Part C eval stack, Part D doc-integrity tests, Part E three "what would you change"). Original: 12-file 10-minute tour (function to open, excerpt, guarding test, CLAUDE.md principle each); 5-minute CPU-only demo with every command timed 2026-09-27 (validate 0.4 s, smoke run 15.6 s, rig 0.7 s, eval actor-aware vs window-only 0.9 s, audit-motion 0.8 s, render gate on batch_v8 18 s / 22 checks, realism compare 6.4 s, targeted pytest 46 s / 51 passed) with "if it fails, say this" lines; 6 code-reading Q&As; what not to open live |
| 64 technical report: sim2real and alarms | Self-contained arXiv-style report (~6k words) over H1–H20 + H58 rounds 1–3: synthetic-only hurts (0.276→0.152), small dose +0.0121 [0.0111,0.0130] at unequal steps (H26 equal-step +0.004–0.005, n.s.), realism distance ρ −0.60, far/night/ReID, loiter FA floor ~1 FA/cam-h vs shipped 2.915; limitations (licence, one MOT20 site, seeds, GT-track alarms); what publication needs; 5 figures in figures/64/ |
| 65 dress rehearsal | One timed 60-minute mock (~5k words): opener + 90-s pitch, 6 paper derivations from 55, 40-camera SAPIENT CNI design (10 steps, 8 probes), 10 hardest SurvSim questions deduped from 40/48/57/61 with commit-cited answers, 3 behavioural, 5 questions to ask; latest numbers only (h14b +0.0121 — unequal steps, H26 equal-step +0.004–0.005, A1 2.915/0.825, H17 +0.0103, H15 null, H16 YOLO26n, batch_v8, MetaHuman licence, 6/14); 10-row rubric, red flags, recovery lines |
| 66 hypothesis backlog | 12 ranked pre-registrable hypotheses H21–H32 in the 49 §12 template (≤ 120 words each: hypothesis, arms, seeds, metric, stopping rule, cost, decision), from open caveats in 32/58/64: calibrated-GBM θ grid, operator review queue, frozen vs retrained loiter weights, ReID association, label-noise sensitivity, dose curve beyond 300, far synthetic-only at 1280, degrade retune on batch_v8, clothes-change ReID, multi-site real eval, gait from pixels, real-IR night; ranks 1–3 CPU-only today |
| 67 adversarial panel gaps | 5 interviewers × 12 questions (ML lead, edge engineer, SOC manager, MOD lead, CTO), each grep-checked against the corpus; gaps table (conformal 0 hits, ALARP 0, PSTI 0, Art 22A–D 2, Cyber Essentials 1, TRL 1); fetched-source answers (Conformal Risk Control, PSTI 2023 Sch 1, DUAA s.80, JSP 936 13 Nov 2024, SCC 12 principles); 'what to say if you don't know'; feeds H33–H35 |
| [68 mock interview round 4 — technical (full panel)](68_MOCK_INTERVIEW_ROUND4_TECHNICAL.md) | Full 60-minute the vendor panel (~4.6k words): ≤150-word intro pitch; 25 questions in panel order (warm-up, CV depth — range, tracking, clothing-change ReID, night/IR, degradation, VLMs; system design — 40-camera edge, Orin NX budget, H22 review queue, H33 conformal θ, drift; evaluation — FA/cam-h, i-LIDS, hard negatives, HOTA vs MOTA; sim-to-real H1/h14b/H17/H19/H20; JSP 936, DUAA Arts 22A–D, PSTI, SC Code; STAR; 2 reverse questions), each with a ≤120-word FACTS-traced answer, 2 follow-ups and red flags; 6 weakest answers with hedges; 10 rapid-fire lines |
| [79 mock interview round 5 — post-68 material](79_MOCK_INTERVIEW_ROUND5.md) | 25 questions (~4.5k words) on material after `68`: forensic search + H37 epoch trap (pre-reg), H34 label-free drift, H38 FP16/INT8 export, Orin NX sizing, H39 auto-calibration and the height-consistency trap, PTZ live pose, H40 line-crossing, twins, i-LIDS sterile-zone timing, H23/H21 θ-selection variance, H33 conformal θ, CC-ReID + gait, H22 queue and bulk-ack, M1 parity, H24 (pre-reg), H32 night; 5 ⚠ traps with the retired answer and its correction; 6 weakest answers; 10 one-liners |
| [69 night and thermal surveillance](69_NIGHT_AND_THERMAL_SURVEILLANCE.md) | ICR day/night switching and failure modes, 850 vs 940 nm IR, gain/3DNR smear, insects/rain bloom; LWIR microbolometer (NETD, 640×512, halo/AGC/crossover/NUC); LLVIP/KAIST/FLIR ADAS/M3FD with licence verdicts (all NC or unverified); RGB-T fusion; night failure table; CNI perimeter (PIDS + radar + thermal + slew-to-cue PTZ); H32 step 0 on 50 LLVIP frames (night_ir 3/13 vis, 2/13 thermal; renders not dark); 10 Q&As |
| [70 clothes-change ReID](70_CLOTHES_CHANGE_REID.md) | Short- vs long-term ReID; why appearance collapses (CAL PRCC 100→55.2, body-only 24.5; MEVID different-clothes 3.5 R1); PRCC/LTCC/Celeb-reID/DeepChange/CCVID/LaST/MEVID with licences (only MEVID/MEVA CC BY 4.0); SOTA checked (Ortho-ReID PRCC CC 74.4/70.2, LTCC ~56/30, DLCR +11.3); gait under clothing (GREW R1 ~79, SUSTech1K clothing ~46–50); design: height + gait + time-topology gating, appearance within an epoch; H29 full design; 10 Q&As |
| [72 insights & forensic search](72_INSIGHTS_AND_FORENSIC_SEARCH.md) | The "insights" half: coverage audit; what Avigilon/BriefCam/Genetec/Milestone/Verkada/Axis/Coram/Spot AI/Ambarella/Hailo ship (vendor claims [A]); attributes, per-track embeddings, CLIP search, FAISS/HNSW, event store, MTMC journeys, ANPR, PPE; index budget 40 cams × 30 d ≈ 7 GB (quiet) – 71 GB (busy) vs 31.1 TB video; SurvSim eval (uid recall@k, epoch trap, journey edit distance); H37; DPIA/purpose limitation/Bridges/attribute-vs-biometric line; 10 Q&As + whiteboard |
| [73 tracking sim-to-real](73_TRACKING_SIM2REAL.md) | Why tracking transfers differently from detection (fps, tilt, density, occlusion, box convention); MOTSynth/PersonPath22/DanceTrack/SportsMOT/ByteTrack/OC-SORT/BoT-SORT/Deep OC-SORT/HOTA; our H9/H17 + batch_v8 vs MOT20 crowd stats (5.4 vs 123.5 people/frame, visibility 0.915 vs 0.572, 44 % vs 2.4 % boxes < 0.5 visible); defence-site tracker design; H24 refinements; 10 Q&As |
| [80 interview figure pack](80_FIGURE_PACK.md) | 10 printable one-panel figures (`figures/pack/`, `pack.pdf`) for pipeline, sim2real, operating points, alarm path, tracking, night, edge, drift, line-crossing, evasion. Every number is checked against FACTS by the script; each figure has 3 sentences to say and 1 trap |
| [74 system-design drills](74_SYSTEM_DESIGN_DRILLS.md) | Three timed whiteboard drills (perimeter alarms, forensic search, fleet MLOps): prompt, clarifying questions, ASCII design, FACTS-traced capacity arithmetic, failure modes, JSP 936/DUAA/SCC/DPIA overlay, rubric + 3 traps each |
| [AUDIT_70_73](AUDIT_70_73.md) | Adversarial audit of 70 and 73 + docs/13 Box aspect: script re-run bit-exact; papers re-fetched; 11 fixes |
| [AUDIT_74](AUDIT_74.md) | Adversarial audit of 74: arithmetic re-derived (31.1 TB, 93.3 TB, 31.1 bn tokens ✓); 6 fixes; 74 → 93 |
| [AUDIT_M1_PARITY](AUDIT_M1_PARITY.md) | Audit of M1 TrackEval parity: re-run confirms \|Δ\| ≤ 1e-15; HOTA 0.4342 → 0.4428 propagated; H9/H17 marked pre-parity; 88/100 |
| [AUDIT_72](AUDIT_72.md) | Fetch-verified 72: 14 [V] / 7 [X] vendor claims (BriefCam now under Milestone, 3 dead URLs); adds §4b ANPR (NASPLE v3.5: 98 % capture, 95 % read, 12 mo/90 d retention) and §4c PPE (SH17 70.9, CHV 86.55 mAP); arithmetic ✓; H37 brought to 49 §12; 5→8/10 |
| AUDIT_43-47 | Adversarial audit of 43–47: claim tables, scores, conclusion-changing corrections (Orin NX decode 18, Gemini default low-res tokens, 2026/1744 dates from EUR-Lex, MetaHuman/SMPL-X/Reallusion clauses verbatim) |

`FACTS_VERIFIED.md` is the crib sheet. Where a dossier and FACTS disagree, FACTS wins.

Reading order: 17 → 23 (the plan) → 18–22 as needed. 17 does not repeat D04;
read D04 for physical network/VMS architecture.

## Original dossier reading order (≈ 3 days; superseded by the decision tree above for interview prep)
**Day 1 — the problem and the people.** R06 → D01 (skim timeline, read dead ends) → D06 (personas, requirements) → D03 §buyers + §the vendor positioning → H02 Top-25.
**Day 2 — the technology.** R01 → R02 → R03 → R04 → R05 → H01 Top-25 → D07 §obsolete/easy/hard.
**Day 3 — building it.** D04 (architecture) → D08 (craft, pitfalls, recipe) → D05 (SNN, event cams) → D02 (who to follow, reading list) → full H01/H02.
Then: docs/01–09 (the SurvSim plan) with fresh eyes; expect to revise docs/02, 06, 07, 08 using D04, D08 and H01/H02 findings.

## Ten load-bearing facts the corpus keeps returning to
Spot-checked against `FACTS_VERIFIED.md` on 2026-09-27: ✓ = matches a FACTS row;
[derived]/[secondary] = not a FACTS row, argued in the cited dossier.
1. ✓ Research false-alarm operating points (ActEV RFA 0.1/min = 6 FA/camera-hour) are ~3 orders of magnitude looser than what a 500-camera control room tolerates; SurvSim's own H12 puts every loiter rule 4,500–87,000× over our assumed 0.001 FA/cam-h, and the H58 learned rule is still ~3,700× over. (R03, 32, 58)
2. ✓ i-LIDS: 10 s alarm window, repeat alarms disregarded — a correct-but-late alarm is a false alarm. (R03, R05)
3. ✓ Pilot failures are configuration, video quality, integration, communication and camera:operator ratio — not accuracy (Keval & Sasse: 13 managers, 38 operators, 13 control rooms). (D06)
4. [derived] Calibration error dominates multi-camera fusion: ground error from pitch error scales as ΔX ≈ R²θ/h, so 1° at 30 m range from a 4 m mount ≈ 3.9 m on the ground plane, 8× the 0.5 m MODA tolerance (a 1° *yaw* error is only R·tan 1° ≈ 0.5 m). (R02 §2.6, H01, 29 §8)
5. [secondary] Tracking collapses below ~3 fps; WILDTRACK's 2 fps sits on the cliff. (R01)
6. ✓ Clothes-changing ReID: CAL on LTCC 40.1 R1 / 18.0 mAP (PRCC 55.2 vs 100 same-clothes); gait on GREW now 77.7–79.4 % R1 (86 was DeepGaitV2 rank-10; 70) (DeepGaitV2, SkeletonGait++) — "gait fails in the wild" is out of date; disguise is under-benchmarked. (R02, 27)
7. [secondary] Enhancement (dehaze/low-light) often hurts un-retrained detectors; degradation-aware training beats pre-processing. (R04)
8. ✓ Synthetic data works when diverse (MOTSynth 768 seq / 1.38 M frames) — SurvSim's synthetic-only fine-tune *hurt* real AP (0.276 → 0.152 ± 0.025, `32` §H1); the only positive is +0.004–0.005 AP at equal steps (H51, 10 paired seeds, Holm p 0.0039; h14b's +0.0121 compared unequal steps) from 100–300 renders added to 60 real frames (labels fixed; the buggy H14 run had +0.0107). (R04, 32)
9. ✓ Always-on VLM analytics: ~0.36M (default) – 1.1M (high-res) tokens/camera-hour at 1 fps on Gemini; D07's 4.6M is a 2 fps × 640 tok/frame research protocol; trigger-gating is ~170–400× cheaper in dollars at 20 triggers/camera-day. (45, 49 §0)
10. [derived] Event cameras are blind to stationary targets: a loiterer who stops moving disappears — physics, not an algorithm gap. (D05, 36)

## Corrections the agents made to the original briefs (do not repeat the errors)
- Westminster public-realm CCTV is ~100–200 monitored cameras, not ~5,000. (D06)
- Vintra was an asset purchase by Alarm.com in April 2023; Eagle Eye merged into Brivo Dec 2025. (D03)
- Ipsotek founded 2001, no confirmed Kingston University link. (D01)
- No source confirms an i-LIDS "primary/secondary detection" classification. (R03, D01)
- the vendor ≠ Applied Intuition (both in UK defence). (R06, D03)
- BrainChip–Raytheon/AFRL confirmed; BrainChip–Lockheed not found. (D05)
- North Hyde substation fire (2025) reported as equipment fault, not arson. (D06)
