# 51 — Operator human factors and "insights" products

*What monitoring-centre operators actually do, why they miss things, how
analytics should present alarms to them, and the non-security "insights"
product class — with how SurvSim ground truth could validate each. Written
2026-09-26.*

**Evidence tags.** External claims carry the URL fetched and the date (all
2026-09-26). **[INF]** = my inference. **[repo]** = read from this repository.
**[unverified]** = found only via a secondary listing. `FACTS_VERIFIED.md` wins
over this file where they differ; in particular this file follows FACTS on the
Donald et al. 2015 correction (decrement in novices/generalists, not
specialists; the popular "operators lose it after 20–30 minutes" line is *not*
what that study showed).

---

## 0. The one-paragraph answer

In the UK, remotely monitored detector-activated CCTV is governed by a chain:
**BS 8418** (how the system is designed, installed and monitored), **BS EN
50518 / BS 5979** (the monitoring centre itself), and the **NPCC Security
Systems Policy** (when the police will come). The NPCC rule is blunt: a URN
system gets immediate response until **3 false calls in a rolling 12 months**,
then response is withdrawn. So the operator's job is not "watch screens"; it is
*verify or dismiss detector-triggered clips fast, and only call the police with
evidence of criminal activity in progress*. Humans are poor, tiring watchers —
Donald et al. found operators detected **50 %** of target behaviours with high
false alarms, and multi-screen displays delay detection — so the analytics
product's real job is to shrink the alarm stream to something a human can
verify well, and present each alarm clip-first with its reason. "Insights"
(occupancy, dwell, flow, heatmaps, PPE, near-miss) reuse the same detection and
tracking to sell to operations budgets, and each has a ground-truth definition
SurvSim can produce exactly.

---

## 1. What monitoring-centre operators actually do

### 1.1 The standards chain (UK)

**BS 8418:2021** — *Design, installation, commissioning and maintenance of
detection-activated video surveillance systems (VSS) — Code of practice*.
NSI's publication notice (<https://www.nsi.org.uk/publication-of-british-standard-bs-84182021/>,
fetched 2026-09-26) records:

* published with a **12-month transition ending 31 July 2022** (2015 or 2021
  edition acceptable during it);
* a tiered **Type A / Type A+** framework (A+ for elevated-risk sites);
* **RVRC (remote video response centre) recommendations were removed and moved
  to BS 9518**;
* "a VSS must have a Unique Reference Number (URN) and comply with the
  recommendations in BS 8418" for police response, and the installer must be
  approved by a UKAS-accredited certification body such as NSI.

**NPCC "Police Operational Advice and Security Industry Requirements for
Response to Security Systems"**, revised **March 2024** (66-page PDF,
<https://www.policesecuritysystems.com/images/Policy%202024/NPCC%20Police%20Requirements%20for%20Security%20Systems%202024.pdf>,
fetched 2026-09-26; text extracted with `pdftotext`):

* §3.1.1 — Type A systems get **LEVEL 1 – Immediate** or **LEVEL 3 –
  Withdrawn** ("No police attendance, keyholder response only").
* §3.2.1–3.2.3 — intruder alarms keep Level 1 "until 3 false calls have been
  received in a rolling 12 month period"; a warning letter after 2; withdrawal
  after 3, "not less than 14 days from the date of the withdrawal letter".
* §3.2.4 — reinstatement for confirmed systems needs cause identified, remedial
  action, and "**90 days free of false calls**"; §3.2.5 — if restoration is
  delayed more than 6 months the URN is deleted.
* §3.3.1 — detector-activated CCTV must be installed to **BS 8418** and
  Appendix R; "**False alarm withdrawal thresholds for CCTV systems are the
  same as IAS.**"
* Appendix R (March 2024): monitoring companies are "known as RVRCs"; RVRCs
  conform to **BS 5979 (Cat II) or BS EN 50518** and BS 8418 (§2.2); the
  system "will have the capability of **audio challenge**" (§4.4); "The RVRC
  will only call the police if there is **sufficient evidence in the images of
  unauthorised access** to the site/premises and there is criminal activity (or
  attempt) in progress" (§4.5); the operator provides location and activity
  information (§4.6); the RVRC "will employ **filtering techniques** to avoid
  unnecessary calls" (§4.7); and must supply management information on calls
  passed to police (§5).
* §3.1.3 — electronic transfer of IAS/HUA activations to police (ECHO) became
  mandatory from 1 April 2021 where forces could accept it.
* Keyholders must be able to attend within 20 minutes (§ keyholder clause,
  PDF line "attend within 20 minutes of being notified").

**BS 8591:2014 → BS 9518:2021.** BSI Knowledge product page
(<https://knowledge.bsigroup.com/products/processing-of-alarm-signals-by-an-alarm-receiving-centre-code-of-practice>,
fetched 2026-09-26; the page embeds the foreword and scope preview):
*BS 9518:2021 Processing of alarm signals by an alarm receiving centre. Code of
practice*, published **31 Jul 2021**, status "Current, Under Review".
Supersession: "This British Standard supersedes BS 8591:2014, which will be
withdrawn on 31 July 2022." Scope: "recommendations for the processing of
signals by an alarm receiving centre (ARC) from alarm systems, such as … intrusion
and holdup alarm systems, **video surveillance systems**, social alarms systems,
lone worker". It was "produced following the publication of BS EN 50518:2019
and is intended to complement that standard by providing UK-specific
recommendations"; the NOTE says BS EN 50518:2019 covers planning,
construction, management and staffing of the ARC. So: **BS EN 50518 = the
building and organisation; BS 9518 = how signals, including video alarms, are
handled** [V].

**NSI.** The 2018 criteria PDF previously cited
(`…/2020/02/SF-006-Issue-3-ARC-Gold-approval-criteria-Oct-18.pdf`) now returns
**HTTP 404** (2026-09-26), so the old "BS 5979 or BS 8591 incl. BS EN 50518"
wording is **withdrawn from this report**. The current NSI page
(<https://www.nsi.org.uk/approved-companies/arcs-rvrcs/>, fetched 2026-09-26)
describes **NSI ARC Gold** as certifying "Alarm Receiving Centres (ARCs) to
meet the highest technical and quality standards for security monitoring
services", with a commitment to **ISO 9001**, and lists the standards as
"BS 5979: The standard for Alarm Receiving Centres. **BS 8418: For the use of
detector-activated CCTV systems.** BS 8484: For lone worker device
monitoring" [V]. The page does not name BS EN 50518 or BS 9518; whether the
current Gold criteria reference them is **[unverified]**. NSI's "codes" in
practice are these UKAS-accredited certification schemes [INF].

### 1.2 The workflow, step by step [INF, assembled from the above]

1. **Detection** on site (PIR, beam, video analytic) triggers; the system is
   *armed* only in set periods (BS 8418 systems are detector-activated, not
   continuously watched).
2. **Signal + pre/post-alarm clip** go to the RVRC; the alarm lands in an
   operator's queue with site, camera and zone.
3. **Verification.** The operator reviews the clip and live view. Outcomes:
   false (animal, weather, foliage, lighting), authorised (keyholder, cleaner,
   known contractor on the site schedule), or suspicious/criminal.
4. **Intervention.** Audio challenge through site speakers (Appendix R §4.4);
   many intruders leave at this stage.
5. **Escalation.** Call police only with *image evidence of unauthorised access
   and criminal activity in progress* (§4.5), giving location and activity
   (§4.6); notify keyholder (20-minute attendance).
6. **Evidence.** Supply images with continuity statement (App. R §4.9).
7. **Management information.** Calls passed to police per URN (§5) — the
   denominator for the 3-strikes rule.

**The economic core [INF]:** the RVRC carries the false-call risk for its
customers. Every analytic false positive costs operator seconds; every operator
mistake that reaches the police moves a site one step towards Level 3. That is
why ARCs buy false-alarm filtering (see doc 34: Calipsa, acquired by Motorola
Solutions 2022, sold "alarm verification, tamper and camera-health checks" into
ARCs).

### 1.3 Mapping to SurvSim

SurvSim's `survsim/eval/` scores alarms "the way security evaluations do" —
i-LIDS timing and false alarms per camera-hour [repo, CLAUDE.md]. The NPCC rule
adds a third, *site-year* metric worth computing [INF]: **expected false calls
passed to police per site per 12 months** = (analytic FA/cam-h) × (armed hours)
× (cameras) × P(operator escalates a false alarm). The analytic sets the first
three; the operator UI sets the last.

---

## 2. Vigilance decrement: what the evidence says

### 2.1 Fetched studies

* **Donald, Donald & Thatcher 2015**, *Work exposure and vigilance decrements in
  closed circuit television surveillance*, Applied Ergonomics 47:220–228.
  Europe PMC record <https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:25479991&resultType=core&format=json>
  (fetched 2026-09-26). 42 full-time operators, extended to 73. "**Fifty
  percent of target behaviours were detected and false alarms were high.**"
  Experienced **specialists maintained performance for the first hour and then
  improved**; **novices and generalists showed vigilance decrements**. Authors
  attribute differences to surveillance background, experience, training
  transfer, selection, training quality and motivation. (Matches FACTS line on
  this paper.)
* **Warm, Parasuraman & Matthews 2008**, *Vigilance requires hard mental work
  and is stressful*, Human Factors 50(3):433–441, PMID 18689050
  (<https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=vigilance%20%22hard%20mental%20work%22%20Warm&resultType=core&format=json&pageSize=3>,
  fetched 2026-09-26). Review across task types, workload ratings, transcranial
  Doppler and stress measures: vigilance is effortful and stressful — it is not
  "under-arousal" that more coffee fixes.
* **Aitken, Champion & Stainer 2019**, *Anxious individuals predict the onset
  of aggression earlier in a CCTV surveillance task*, J Exp Psychol: Applied,
  PMID 30394769 (Europe PMC, fetched 2026-09-26). Displays of **1, 4 or 9
  simultaneous feeds** (GTA V-rendered incidents); "**increasing the number of
  screens … associated with detecting events later**"; higher anxiety ⇒ earlier
  responses with no accuracy change. (Note for SurvSim: a peer-reviewed study
  already used *game-engine rendered* CCTV as stimuli.)
* **Tatler 2021**, *Searching in CCTV: effects of organisation in the
  multiplex*, Cognitive Research: Principles and Implications, PMID 33599890
  (fetched 2026-09-26). Searching for a scene in a CCTV array "was faster when
  scenes were arranged by semantic category" than by geography.
* **Luna et al. 2022**, Psychonomic Bulletin & Review 29(5):1831–1843,
  PMID 35477850 (fetched 2026-09-26): with N = 617, the vigilance decrement
  comes with an executive-control decrement (small effects).

### 2.1a Classic human-factors sources (fetched 2026-09-26)

* **Mackworth 1948**, "The Breakdown of Vigilance during Prolonged Visual
  Search", *Q. J. Exp. Psychol.* 1(1):6–21, doi:10.1080/17470214808416738
  (Crossref). The clock test: a pointer jumping ~once a second, with rare
  double jumps to detect, for two hours. Detection "declined between 10 and 15
  percent in the first 30 minutes and then continued to decline more
  gradually" — **[V secondary: Wikipedia "Vigilance (psychology)"; paper body
  paywalled]**. This, not Donald 2015, is the lab origin of the "30 minutes"
  folklore — and it is a 2-hour monotonous lab task, not CCTV work.
* **Wolfe, Horowitz & Kenner 2005**, "Rare items often missed in visual
  searches", *Nature* 435:439–440, doi:10.1038/435439a; full text PMC4224304
  (fetched). Miss errors: **7 % at 50 % target prevalence, 16 % at 10 %,
  30 % at 1 %**; false alarms "vanishingly rare (0.03 %)". 12 observers; at 1 %
  prevalence each ran 2,000 trials for 20 targets. **This is the quantitative
  basis for §3.2's prevalence hazard** — and an alarm queue after good
  analytics filtering sits *below* 1 % true-alarm prevalence (§3.1a).
* **Parasuraman & Riley 1997**, "Humans and Automation: Use, Misuse, Disuse,
  Abuse", *Human Factors* 39(2):230–253, doi:10.1518/001872097778543886
  (Crossref); **Parasuraman & Manzey 2010**, "Complacency and bias in human use
  of automation", *Human Factors* 52(3):381–410, PMID 21077562 (Europe PMC
  abstract fetched): complacency "occurs under conditions of multiple-task
  load"; it "is found in both naive and expert participants and cannot be
  overcome with simple practice"; automation bias yields "both omission and
  commission errors when decision aids are imperfect" and "cannot be prevented
  by training or instructions". Direct consequence: an operator who trusts a
  suppressing analytic will not catch its misses (§5A.1 MISSED-LATER).
* **Wickens 2002**, "Multiple resources and performance prediction",
  *Theor. Issues Ergon. Sci.* 3(2):159–177, doi:10.1080/14639220210123806
  (Crossref; S2 summary): interference between two tasks is greater "to the
  extent that they share stages, sensory modalities, codes and channels of
  visual information". Design reading [INF]: put the alarm cue on a different
  channel (audio tone) from the visual verification task; do not make the
  operator read text overlays while scanning video.
* **NASA-TLX** — Hart & Staveland 1988, *Advances in Psychology* (Human Mental Workload), pp. 139–183,
  doi:10.1016/S0166-4115(08)62386-9 (Crossref); six subscales (Mental,
  Physical, Temporal Demand, Performance, Effort, Frustration), each rated on a
  100-point range in 5-point steps (Wikipedia "NASA-TLX", fetched). Use it as
  the subjective-workload arm of the §5A.3 HITL harness next to objective
  time-to-verify.

### 2.2 What not to say

The widely repeated "operators miss 95 % of activity after 22 minutes" / "after
20–30 minutes attention collapses" is not supported by the fetched evidence,
and FACTS records the correction that the Donald study's decrement applied to
novices and generalists, not specialists. Say instead [INF]: *detection of
rare targets by humans watching live video is poor — about half in the one
field-realistic study — it gets worse with more screens and for less
experienced operators, and sustained watching is demanding work. So design the
system so humans verify alarms rather than search for them.*

---

## 3. Alarm fatigue and the nuisance-alarm budget in operator terms

### 3.1 The maths

Let an operator handle **C** cameras, each producing **B** false alarms per
camera-hour, and let verification take **t** seconds per alarm. Operator
utilisation from false alarms alone is

    U = C · B · t / 3600.

Worked [INF, numbers illustrative]:

| Cameras per operator C | FA/cam-h B | t (s) | False alarms per operator-hour | U |
|---|---|---|---|---|
| 50 | 0.1 | 20 | 5 | 2.8 % |
| 200 | 0.1 | 20 | 20 | 11 % |
| 200 | 1.0 | 20 | 200 | 111 % — queue grows without bound |
| 500 | 0.05 | 30 | 25 | 21 % |

### 3.1a Worked example with cited inputs

Inputs, each with its source:

| input | value | source |
|---|---|---|
| false-call tolerance | < 3 per rolling 12 months, else police response withdrawn | NPCC 2024 §3.2.1/§3.2.3, CCTV "same as IAS" (fetched PDF, l. 452/459/500) |
| reinstatement | 90 days free of false calls | NPCC §3.2.4 |
| keyholder attendance | within 20 minutes of notification | NPCC keyholder clause (PDF l. 302) |
| human detection when *watching* | ~50 % of target behaviours | Donald et al. 2015 |
| miss rate vs prevalence | 7 % @ 50 %, 16 % @ 10 %, 30 % @ 1 % | Wolfe et al. 2005 |
| site | 16 cameras, armed 14 h/night × 365 = 5,110 h | illustrative [INF] |
| verification time | t = 20 s | illustrative [INF] |

Arithmetic [INF]:

1. **Analytic false alarms per site-year** = 16 × 5,110 × B. At B = 0.1
   FA/cam-h: **8,176**; at B = 0.01: 818.
2. **Escalation budget.** To stay under 3 false police calls/year the
   operator's false-escalation probability must be < 3/8,176 = **3.7 × 10⁻⁴**
   at B = 0.1, or < 3.7 × 10⁻³ at B = 0.01. A 10× better analytic buys the
   operator a 10× larger error margin — this is the NPCC rule expressed in ML
   terms.
3. **True-alarm prevalence in the queue.** With, say, 2 genuine intrusions per
   site-year, prevalence = 2/(8,176 + 2) ≈ **0.024 %** at B = 0.1, 0.24 % at
   B = 0.01 — both far below Wolfe's 1 % condition where misses already
   reached 30 %. The operator's *miss* rate on true alarms is therefore the
   dominant risk, not the false call; seeded test alarms (§5A.2) are the
   countermeasure, raising effective prevalence.
4. **Utilisation.** A 200-camera operator at B = 0.1, t = 20 s: 200 × 0.1 × 20
   / 3600 = **11 %**. At B = 1: 111 % (unstable).
5. **Time budget.** If the alarm must reach the keyholder in time for the 20-min
   attendance to matter, verification queueing is second-order at 11 %
   utilisation (M/M/1 mean wait = ρ/(1−ρ) × t ≈ 2.5 s), but a weather burst that
   pushes ρ to 0.9 gives 180 s — still fine against 20 minutes, **not** fine
   against a 25-s i-LIDS-style tolerance.
6. **Why "watching" is not the fallback.** Donald's ~50 % is detection under
   *search*; replacing the analytic with live watching halves recall on day
   one, before any decrement.

Doc 19 §6.2 derives 0.1 FA/min = 6 FA per camera-hour from an i-LIDS-style
rate; at that rate a single operator is saturated by ~30 cameras at 20 s per
alarm [INF: 30 × 6 × 20 / 3600 = 1.0]. That is why vendors quote FA
*reductions* of an order of magnitude or more: the headcount maths only works
below ~0.1 FA/cam-h at scale.

### 3.1b Plugging in measured rates (H12, `9dea4f9`)

The B values above are illustrative. SurvSim's H12 measured B for its own
loiter rules on **3,002 clean mock camera-hours** (676 worlds, 74,989 innocent
people, zero loiterers, perfect tracks; `32` §H12,
`out/experiments/h12_alarm_scale/results.json`). This replaces the H5
0.35-camera-hour figures. Same 16-camera, 5,110 h site and t = 20 s [INF]:

| rule | B (FA/cam-h) | × assumed 0.001 budget | FA per site-year | max false-escalation prob. for < 3 calls/yr | cameras that saturate one operator (U = 1) | U at 200 cams |
|---|---|---|---|---|---|---|
| dwell_60 | 4.55 | 4,552 | ~372,000 | 8.1 × 10⁻⁶ | ~40 | 506 % |
| dwell_25 | 6.01 | 6,007 | ~491,000 | 6.1 × 10⁻⁶ | 30 | 667 % |
| path_loiter_25 | 20.7 | 20,651 | ~1.69 M | 1.8 × 10⁻⁶ | ~9 | 2,295 % |
| path_loiter_15 | 87.4 | 87,440 | ~7.15 M | 4.2 × 10⁻⁷ | ~2 | 9,716 % |
| **learned (H58 round 2; superseded by round-3 A1 2.915)** | **3.745** | 3,745 | ~306,000 | 9.8 × 10⁻⁶ | ~48 | 416 % |

The learned row is `LearnedLoiterRule` from doc 58 §6 round 2 (`44e34f5`,
`out/experiments/h58_round2/round2_results.json`): round-2 (superseded) 3.745 FA/cam-h [3.676,
3.815] on the same 3,002 clean cam-h, actor-aware recall 0.831 [0.792, 0.869],
precision 0.326 — 1.60× fewer false alarms than dwell_25 (round 1's 2.06× is
superseded). In the doc-58 operator framing (40 cameras, t = 30 s):
round 2 (superseded): 40 × 3.745 × 30 / 3,600 ≈ **1.25 operators** of pure dismissal work; shipped round-3 A1: 40 × 2.915 × 30 / 3,600 ≈ **0.97 operators**.

Readings [INF on the operator side; rates measured]:
* dwell_25 sits exactly on doc 19's 6 FA/cam-h research point, so the "~30
  cameras per operator" line above is now a measured ceiling, not a BOE.
* Even the quietest rule needs a ~4,500× reduction to reach 0.001, and dwell_60
  buys its lower rate by losing recall. Scored **actor-aware** (the alarm
  must be on the loiterer), dwell_60's recall at a 30 s tolerance is **0.000**
  and dwell_25's **0.367** (360 events, H58 round 2); the H12 window-only
  figures (0.16, 0.90) were mostly alarms on bystanders who happened to be in
  the event window, and are not detection numbers. The learned rule keeps
  0.831. Even it is ~3,700× over, and the motion-only kinematic-twin floor is
  1.008 FA/cam-h. The gap is 3.6–4.9 orders of magnitude — no threshold
  tweak closes it; it is a corroboration/context problem (doc 19 §5.3).
* i-LIDS 5 s coalescing reduces the queue by 7–59 % (repeats), not by
  improving the analytic — useful for U, irrelevant to the NPCC count if the
  operator still escalates per incident.
* **Bursts are real in the data**: H12's world-cluster bootstrap CI is ~3×
  wider than the Poisson (Garwood) CI — false alarms cluster by world (crowded
  worlds make many), the §3.2 queueing hazard in measured form. Size staffing
  on the high-percentile world, not the mean.
* Caveat: absolute rates depend on the mock archetype mix (55 % transit), not
  validated against real dwell distributions; the ordering is a property of the
  rules.

### 3.2 Why utilisation isn't the whole story [INF]

* **Prevalence effect** (Wolfe et al. 2005: misses 7 % → 30 % as target
  prevalence falls from 50 % to 1 %; §2.1a). When nearly every alarm is false, operators learn to
  dismiss quickly; the rare true alarm is dismissed too. The low true-alarm
  prevalence that analytics produce is itself a hazard — more filtering raises
  precision, but the human's prior still has to be kept honest (e.g. seeded
  test alarms / "phantom" events, used in aviation screening as threat-image
  projection).
* **Queue waiting.** At 80 % utilisation, M/M/1 waiting time is 4× service time;
  a true alarm behind a burst of rain-triggered false alarms is verified late,
  which under i-LIDS timing is *a miss*. Bursts matter more than means —
  weather correlates false alarms across all cameras at a site.
* **Budget ⇒ threshold.** Pick the operating point from the budget, then report
  recall at that point (doc 49's calibration/threshold section), not AUC.

### 3.3 Mapping to SurvSim

`survsim eval out/run --threshold-s 25` already reports alarms per camera-hour
[repo, CLAUDE.md]. Adding a queue simulator — replay the timestamped alarm
stream through k operators with service time t and report *time-to-verify* of
true alarms — would turn the budget into the metric operators feel [INF;
straightforward over existing `events.jsonl`].

---

## 4. UI/UX patterns that reduce misses

Evidence-linked where possible; the rest is [INF] design reasoning.

1. **Clip-first review.** Present the pre/post-alarm clip, looped, with the
   triggering object boxed, before the live view. BS 8418 workflows are built on
   the alarm clip; verification is recognition of a short event, not search
   (§2.2) [INF].
2. **Fewer simultaneous tiles.** Aitken 2019: more screens ⇒ later detection.
   Show one alarm at a time; return the video wall to overview duty.
3. **Semantic grouping.** Tatler 2021: arrange by category (entrances, yards,
   perimeter) rather than geography when operators must find a scene.
4. **Reason codes, not only scores.** "Person, crossed fence line east→west,
   dwell 40 s in sterile zone, 02:14" is checkable; "0.87" is not. Explanations
   let the operator verify the analytic's claim against the clip [INF].
5. **Calibrated confidence, banded.** If shown, confidence must be calibrated
   (ECE; doc 49) and coarse (high/medium/low). An uncalibrated 0.9 on
   foliage trains operators to ignore the number [INF].
6. **Context overlays.** Site schedule (cleaners 06:00–07:00), known
   contractors, weather, and whether the camera is currently tamper-flagged —
   these are exactly the facts operators use to dismiss authorised activity.
7. **Suppression with memory.** One-click "same cause" suppression (e.g. a
   flapping banner) with an expiry and an audit trail, so a nuisance source
   stops costing seconds without silently creating a blind zone.
8. **Tamper as a first-class alarm.** Camera blinded at night is escalated like
   an intrusion (doc 50 §4).
9. **Measure the UI.** Time-to-acknowledge, time-to-verify, dismissal accuracy
   on seeded events, per operator and per hour-of-shift.

**SurvSim angle [INF]:** because SurvSim knows the truth for every alarm, it can
generate *seeded verification sets* — balanced true/false clips with matched
hard negatives (`commute_wait` vs `loiter`) — for operator-training and UI A/B
tests, which real sites cannot supply without staging intrusions.

---

## 5. The "insights" product class

Doc 34 §6 defines "insights" commercially: analytics sold to non-security
budgets (operations, H&S, retail) [repo]. Axis's current object-analytics
product lists the canonical scenario set: **Object in area, Line crossing, Time
in area (dwell), Crossline counting, Occupancy in area, Tailgating detection,
Hard-hat detection (beta)**, and positions it for both security and "visitor
counting, traffic flow analysis, queue management"
(<https://www.axis.com/products/axis-object-analytics>, fetched 2026-09-26; the
older AXIS People Counter page says it has been replaced by Object Analytics,
<https://www.axis.com/products/axis-people-counter>, fetched 2026-09-26).

### 5.1 Definitions, metrics and SurvSim validation

| Insight | Definition [INF unless cited] | Headline metric | Common error source | How SurvSim GT validates it |
|---|---|---|---|---|
| **Line / crossline counting** | count of track crossings of a directed line per interval (Axis scenario, cited) | count error %, per-direction; MAE per 15-min bin | ID switches at the line double-count; occlusion in groups under-counts | `world.parquet` has true positions every tick ⇒ exact true crossings per direction; compare bins |
| **Occupancy** | number of people inside a polygon at time t (Axis "Occupancy in area") | MAE / MAPE of occupancy time series; max error at peaks | drift of in/out counting; crowd occlusion at peaks | true occupancy = point-in-polygon on GT positions each tick |
| **Dwell / time-in-area** | per-track duration inside polygon (Axis "Time in area") | distribution error (median, p90), threshold alarm P/R | track fragmentation cuts dwell; ID switches merge people | true per-identity dwell from GT; fragmentation shows as short false dwells |
| **Queue length / wait** | people in queue region; wait = entry→service time | MAE of length; wait error | same as dwell; queue shape | behaviour engine's `commute_wait`-type behaviours give true waits |
| **Flow / OD matrices** | counts between entry and exit zones | matrix error (L1), per-OD-pair | needs cross-camera ReID for multi-camera OD | GT identity across cameras (`identities.parquet`) gives the true OD matrix |
| **Heatmaps** | time-integrated occupancy density on the ground plane | correlation / EMD vs true density | image-plane heatmaps ignore perspective; must be ground-plane | ground-plane GT density from `world.parquet`; tests homography too (doc 29) |
| **PPE / compliance** | fraction of person-time in zone wearing required PPE (Axis hard-hat beta) | per-person-event P/R; compliance % error | small heads at distance; hi-vis confusion with other yellow clothing | appearance state carries headwear/outer (`hi_vis_worker`: `hardhat`, `hi_vis_vest`) [repo]; pixel test needs wardrobe — **blocked** |
| **Near-miss (person–vehicle)** | min distance / time-to-collision below threshold | event P/R at a distance threshold | depth error from monocular boxes | exact 3-D distances in GT; needs vehicle agents (not currently a focus) |
| **Tailgating** | two people through an access point on one authorised event (Axis scenario) | event P/R | groups walking together legitimately | scripted behaviour pairs: tailgate vs couple-walking-together hard negative |

**Key validation insight [INF]:** every insight is a function of *tracks in
world coordinates*. Real-site validation needs hours of manual counting (and
still can't give true dwell under occlusion); SurvSim gives exact answers for
every tick, so the error can be decomposed into detection misses, ID switches
and homography error — which is what a product team needs to fix the right
stage. The caveat is the usual one: validity of the error *magnitudes* depends
on renders being realistic enough (doc 30); the mock backend validates the
*logic* (polygon, line direction, binning, fragmentation handling) exactly.

### 5.2 Privacy posture

The ICO's video-surveillance guidance
(<https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/>,
fetched 2026-09-26) says such systems "process the personal data of large
numbers of the general public for security, crime prevention or for other
specified purposes such as digital advertising", and that CCTV is evolving
"into more complex artificial intelligence (AI) based surveillance systems"
that "can process more sensitive categories of personal data". Insights
products therefore still process personal data even when the output is a count
[INF: the video frames are personal data; the aggregate may not be].

Privacy-preserving posture [INF; see doc 44 for law]:

* **Edge aggregation** — compute counts on camera, emit only aggregates; no
  video leaves site.
* **No identity** — tracks with ephemeral IDs, no face recognition, no
  cross-day re-identification; OD matrices within a visit only.
* **Minimum bin sizes** — suppress bins with small counts to avoid singling
  people out.
* **Purpose limitation** — an occupancy feed must not quietly become a
  staff-productivity monitor; DPIA before deployment (doc 44 checklist).
* **Why SurvSim helps** — synthetic people have no data-protection status, so
  insight pipelines can be developed and validated end-to-end without
  processing real people [INF; subject to asset licences, doc 47].

---

## 5A. Dispositions, feedback and operator metrics [INF]

### 5A.1 A disposition taxonomy that doubles as training data

Every verified alarm ends with an operator disposition. If the product records
it in a fixed vocabulary, the ARC's daily work becomes a labelled dataset for
the analytic at no extra cost. A workable vocabulary:

| Disposition | Meaning | What the model should learn |
|---|---|---|
| FALSE-ENV | weather, foliage, insects, light change, reflections | nuisance source; candidate for per-camera suppression or retraining |
| FALSE-ANIMAL | fox, cat, bird, deer | class confusion; size/shape filter check (doc 50 §3.3 warns this filter can hide crawlers) |
| FALSE-TECH | camera fault, tamper-like artefact, compression glitch | camera-health, not detection |
| AUTHORISED | keyholder, cleaner, scheduled contractor | a **hard negative**: correct detection, wrong alarm — fix with site context, not the detector |
| SUSPICIOUS-NO-ACTION | person present, not clearly criminal | ambiguous; keep for review, do not train as negative |
| CHALLENGED | audio challenge issued, subject left | true alarm, resolved on site |
| POLICE | escalated with image evidence (NPCC App. R §4.5) | true alarm, confirmed |
| MISSED-LATER | discovered after the fact (e.g. damage found at dawn) | a **false negative** — the only way misses enter the data at all |

Two cautions. First, dispositions are biased labels: a fatigued operator's
"FALSE-ENV" is sometimes a missed intruder, so the label noise is highest on
exactly the events that matter. Second, only alarms get dispositions — the
detector's misses never appear unless something like MISSED-LATER exists. Real
ARC data therefore measures precision well and recall barely at all. That
asymmetry is the strongest argument for simulation: SurvSim's recall numbers
come from ground truth, not from what an operator happened to notice.

### 5A.2 Operator-side metrics worth instrumenting

* **Time-to-acknowledge** (alarm arrives → operator opens it) — a queueing
  metric, dominated by bursts.
* **Time-to-verify** (opened → disposition) — dominated by clip quality and UI.
* **Dismissal accuracy** on seeded events (known-true clips injected at a low
  rate) — the only live measure of human recall.
* **Escalation precision** — fraction of police calls that were genuine; this is
  what the NPCC three-strikes rule counts.
* **Per-hour-of-shift curves** of all of the above — where a decrement, if any,
  would appear, and the evidence base to set breaks rather than a folk
  "20-minute" rule.

### 5A.3 How SurvSim would measure them

A **human-in-the-loop harness** needs no new engine capability: render or mock a
set of alarm clips from scenarios with known truth, stratified into true
intrusions, hard negatives (authorised workers, commuters waiting, animals when
modelled) and environmental nuisance; serve them through a prototype alarm card
at a controlled rate with seeded bursts; log acknowledge/verify times and
dispositions; score against ground truth. Two UI variants (e.g. score-only vs
reason-code + banded confidence) can then be compared with a paired design and
the statistics in doc 49 (McNemar on paired dispositions, bootstrap on
latencies). Aitken et al. 2019 used game-engine footage for a comparable
surveillance-task experiment, which is a precedent for rendered stimuli being
acceptable in operator studies — though their scenes were not built for ground
truth, and the external validity of rendered clips for trained operators should
itself be checked against a small set of real clips.

### 5A.4 Shift and staffing implications

The utilisation formula in §3.1 sets a staffing floor; the vigilance evidence
sets a ceiling on how much of that time should be continuous watching. Combining
them: size the operator pool so false-alarm utilisation stays well below
saturation *during weather bursts*, rotate operators between alarm handling and
lower-demand duties, and treat an analytic upgrade that halves false alarms as
either a headcount saving or, better, a margin that keeps time-to-verify of true
alarms inside the i-LIDS tolerance on the worst night of the year.

---


**Q1. Walk me through what happens when a BS 8418 system alarms at 02:00.**
A detector triggers in an armed period; the clip and signal go to the RVRC;
an operator verifies it — false, authorised or suspicious. If suspicious, audio
challenge; if there is image evidence of unauthorised access and crime in
progress, call police with location and activity, and alert the keyholder
(20-minute attendance). The NPCC 2024 policy withdraws police response after 3
false calls in 12 months, so the RVRC filters hard before escalating.

**Q2. Why should an ML engineer care about the NPCC "three strikes"?**
Because it converts our false-alarm rate into a customer losing police
response. Expected false calls per site-year = FA/cam-h × armed hours × cameras
× P(operator escalates a false one). The analytic owns the first term; the UI
owns the last. Both need to be measured.

**Q3. Do operators lose attention after 20 minutes?**
Not as a clean law. The field study I trust — Donald et al. 2015, 73 operators
— found about 50 % of target behaviours detected and high false alarms;
novices and generalists showed decrements while specialists held for an hour
then improved. Lab work shows more screens delays detection (Aitken 2019) and
vigilance is effortful (Warm 2008). The design conclusion is the same: make
humans verify alarms, not search screens.

**Q4. An operator covers 200 cameras. What false-alarm rate can you afford?**
U = C·B·t/3600. At 20 s per verification and a target of ~10 % utilisation from
false alarms, B ≈ 0.09 FA/cam-h. And bursts matter: rain raises every camera at
once, so test with correlated weather, not averages.

**Q5. What would you put on the alarm card?**
The looped clip with the object boxed; a reason code (rule, direction, dwell);
a banded, calibrated confidence; site context (schedule, contractors, weather);
camera health/tamper status; and one-click dispositions that feed back as
labels.

**Q6. How would you validate an occupancy-counting product?**
Define it as point-in-polygon on ground-plane tracks; report MAE and peak error
on 15-minute bins and per-direction line counts. Use SurvSim to generate
scenes with known occupancy, crowd peaks and group walking, decompose errors
into missed detections, ID switches and homography, then confirm magnitudes on
a short hand-counted real sample.

**Q7. Is a people counter a privacy problem?**
It processes video of identifiable people, so yes, it's personal data
processing even if the output is a count — the ICO frames AI surveillance as
potentially processing more sensitive data. Mitigate with edge aggregation,
ephemeral IDs, no face recognition, minimum bin sizes, a DPIA and purpose
limitation.

**Q8. How does SurvSim help the operator side, not just the model?**
It knows the truth for every alarm, so it can generate balanced verification
sets with matched hard negatives for operator training and UI A/B tests, and
its timestamped alarm stream can be replayed through a queue model to report
time-to-verify of true alarms under realistic bursts — the metric operators
actually feel.

---

## Sources fetched (2026-09-26)

* NSI, BS 8418:2021 publication notice — <https://www.nsi.org.uk/publication-of-british-standard-bs-84182021/>
* NPCC Police Requirements for Security Systems (Mar 2024) — <https://www.policesecuritysystems.com/images/Policy%202024/NPCC%20Police%20Requirements%20for%20Security%20Systems%202024.pdf>
* Donald, Donald & Thatcher 2015 — Europe PMC EXT_ID 25479991
* Warm, Parasuraman & Matthews 2008; Luna et al. 2022 — Europe PMC search (PMIDs 18689050, 35477850)
* Aitken, Champion & Stainer 2019; Tatler 2021 — Europe PMC (PMIDs 30394769, 33599890)
* Axis Object Analytics — <https://www.axis.com/products/axis-object-analytics>; AXIS People Counter — <https://www.axis.com/products/axis-people-counter>
* ICO video surveillance guidance — <https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/>
* BSI Knowledge, BS 9518:2021 product page (foreword + scope preview) — <https://knowledge.bsigroup.com/products/processing-of-alarm-signals-by-an-alarm-receiving-centre-code-of-practice>
* NSI ARCs/RVRCs page — <https://www.nsi.org.uk/approved-companies/arcs-rvrcs/> (old SF-006 criteria PDF: 404)
* Mackworth 1948 doi:10.1080/17470214808416738 (Crossref; numbers via Wikipedia "Vigilance (psychology)")
* Wolfe, Horowitz & Kenner 2005 — <https://pmc.ncbi.nlm.nih.gov/articles/PMC4224304/>
* Parasuraman & Riley 1997 doi:10.1518/001872097778543886; Parasuraman & Manzey 2010 PMID 21077562
* Wickens 2002 doi:10.1080/14639220210123806
* Hart & Staveland 1988 doi:10.1016/S0166-4115(08)62386-9; <https://en.wikipedia.org/wiki/NASA-TLX>
