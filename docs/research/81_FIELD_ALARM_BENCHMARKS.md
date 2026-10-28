# 81 — Field alarm benchmarks: where SurvSim's false-alarm numbers sit against the real world

*2026-09-27; audited AUDIT_81 (URLs re-fetched, table fixed: pooled ≈ 200/h, conformal ≈ 86/h, lenient-end 18–42×). Answers `77` §4 weak answer #1 ("every alarm number is from mock
trajectories") from the outside: what rates do police, alarm receiving centres
(ARCs), PIDS engineers and i-LIDS actually tolerate, and how far are we from them?
Tags: **[V]** fetched this session (URL given, text extracted and grepped);
**[V-corpus]** verified earlier in the corpus (row cited); **[A]** common practice,
not fetched; **[INF]** my derivation. WebSearch was exhausted; only known URLs
were fetched. Six fetches failed (404/403/socket): the NPCC policy at npcc.police.uk,
NSI police-response page, Secured by Design, POP Center false-alarm guide, NPSA
PIDS page, OSTI/Sandia. Nothing from them is tagged [V].*

## 0. The answer in four lines

1. The only hard, published, UK field threshold is **police-facing**: a URN'd
   alarm or BS 8418 CCTV system loses police response at **3 false calls in a
   rolling 12 months** [V NPCC 2024]. That is ≈ 3.4 × 10⁻⁴ false calls per
   *system*-hour — but it counts calls an ARC operator *passed to police*, not
   analytics alarms.
2. Our analytics-to-operator rates (A1 **2.915**, conformal **2.10–2.22**, pooled
   **5.033** FA/cam-h; line-cross twins **0.488**; fused **0.0047**) are
   operator-facing. They must be compared with an **operator** budget, and the
   police threshold is met by the human verification layer, not by the rule.
3. Against a PIDS-style "≈ 1 nuisance alarm per zone per day" [A] (0.042 per
   zone-hour), loiter is ~70× over, twins ~12× over, and the simulated fusion
   ~9× under — on mock tracks with assumed sensors.
4. Our **0.001 FA/cam-h budget is invented**: `A = 4` alarms per operator shift,
   `K = 500` cameras per operator, `H = 8` h, hard-coded in `alarms.py`
   (`28` §6). No field source supports K = 500 for alarm-verification work; a
   defence customer would specify **NAR per zone per day and Pd at a stated
   confidence per attack method**, not FA/cam-h.

## 1. External anchors

| # | Anchor | Unit as published | Source | Tag | Conversion to FA/cam-h [INF] |
|---|---|---|---|---|---|
| E1 | NPCC: intruder alarm system (IAS) with a URN gets Level 1 response "until 3 false calls have been received in a rolling 12 month period"; at 2 the customer is warned in writing; at 3 "LEVEL 3 will apply and police response will be withdrawn" (§3.2.1–3.2.3) | false calls / system / 12 months | https://www.policesecuritysystems.com/images/Policy%202024/NPCC%20Police%20Requirements%20for%20Security%20Systems%202024.pdf | [V] | < 3 / 8,760 h = **3.4 × 10⁻⁴ per system-hour**; spread over 40 cameras **8.6 × 10⁻⁶ per cam-h** of *police calls* |
| E2 | NPCC: detector-activated remotely monitored CCTV "installed to the standard BS 8418 … False alarm withdrawal thresholds for CCTV systems are the same as IAS" (§3.3) | same | same PDF, l. 499–500 of the extracted text | [V] | same as E1 |
| E3 | NPCC: reinstatement after "a period of 90 days free of false calls" (§3.2.4); hold-up alarms withdrawn at **2** false calls (§3.4.3) | days / count | same PDF | [V] | — |
| E4 | NPCC: a false alarm is "an alarm call from a compliant system which would normally be passed to the police" not resulting from a criminal attack (or other listed exemptions) (§2.10.2); ARCs must filter false calls per **BS 8473**, and forces "reserve the right to suspend companies who consistently exceed the force average" (§2.10.1) | definition | same PDF | [V] | The definition is at the police interface — it presupposes an ARC filter |
| E5 | US DOJ estimate: **94–98 %** of alarm calls to law enforcement are false; ~1 % involve a crime; ≥ 36 M activations/yr, ~$1.8 bn | % of calls | https://en.wikipedia.org/wiki/Security_alarm (citing Sampson 2011, *False Burglar Alarms* 2nd ed., US DOJ COPS) | [V] secondary (primary PDF fetch returned the wrong document) | precision at the police interface **0.02–0.06**; not a rate |
| E6 | i-LIDS: each event-detection dataset ≈ **24 h**; "Systems have ten seconds to report an alarm state after an alarm event begins … After this ten second window, any further alarms reported will be deemed 'false positives'"; repeat false alarms logged at most once per 5 s; F1 with recall bias α; commissioning at "an overall F1 score of **0.7** at the application phase" | F1, counts per ~24 h clip set | https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf (re-extracted this session) | [V] | Not a rate. With ~24 h per scenario, **each** false positive ≈ 0.04 FA per scenario-hour (per camera view) [INF] |
| E7 | i-LIDS datasets no longer distributed (from 30 Nov 2014); guidance withdrawn 3 Mar 2015; BRE still evaluates Sterile Zone commercially | status | https://www.gov.uk/guidance/imagery-library-for-intelligent-detection-systems | [V] | — |
| E8 | Operators detected **50 %** of target behaviours (Donald et al. 2015, Appl. Ergon. 47:220–228) | detection share | FACTS "Operations" row | [V-corpus] | human Pd baseline, not a rate |
| E9 | PIDS practice: specify **Pd** (per attack method × location × condition) and **NAR/FAR separately**, often as ≈ **1 nuisance alarm per zone per day** or less | alarms / zone / day | NPSA PIDS page 403; Sandia/OSTI socket error (`76` §2.2) | [A] | 1/24 = **0.042 per zone-hour**; if one camera ≈ one zone, 0.042 FA/cam-h |
| E10 | BS EN 50131 (intruder alarm grades) and BS EN 62676 (VSS) | — | paywalled | [A] | **Neither sets a numeric false-alarm rate** as far as the corpus knows; 62676-4 is the DORI pixel-density standard (`76` §2.3 [V-corpus]). Do not claim a 50131 FA rate |
| E11 | Vendor claims ("95 % fewer false alarms", "AI reduces nuisance alarms by X %") | % reduction | none fetched | [A] | Reductions without a base rate cannot be converted; ask for alarms/camera/day on a named site |

**What I could not anchor.** No published, fetched field trial gives an
analytics FA/cam-h on real CCTV for loitering. The PETS and i-LIDS literature
reports F1 or precision/recall on ~24 h clip sets, not operating rates on months of
footage. The honest statement: *the public field anchors are at the police
interface (E1–E5) and at the evaluation-protocol level (E6); the
operator-interface rate is something integrators hold privately.*

## 2. Where our operating points sit

Our numbers [V-corpus, FACTS H58/H42/H33/H45/H40b/H53]: all from 3,002 clean **mock**
camera-hours with perfect or assumed-noise tracks.

| Operating point | FA/cam-h | Alarms/h at 40 cams [INF] | vs 0.042 (E9 zone-day) | vs 0.001 (our assumed budget, `28` §6) | vs police interface (E1, 8.6 × 10⁻⁶) |
|---|---|---|---|---|---|
| Loiter, pooled θ 0.9 | 5.033 | ≈ 200 | 120× | 5,000× | not comparable directly (see below) |
| Loiter, A1 θ 0.95 | 2.915 | ≈ 120 | 70× | 2,900× | ″ |
| Loiter, conformal (CRC α 2.915) | 2.10–2.22 | ≈ 86 | ≈ 50× | ≈ 2,100× | ″ |
| Motion-only floor | 1.008 | ≈ 40 | 24× | 1,000× | ″ |
| Line-cross, H40b twins (patrol + maintenance) | 0.488 | ≈ 20 | 12× | 490× | ″ |
| Line-cross + H53 fusion | 0.0047 | ≈ 0.19 | **≈ 9× under** | 4.7× over | ″ |

**Reading it honestly.**

* **Police interface.** At A1, 40 cameras produce ≈ 120 alarms/h ≈ 1 M/year.
  E1 allows fewer than 3 of them to reach police as false calls in a year. So the
  ARC operator must dismiss all but ~3 × 10⁻⁶ of the false ones. That is not a
  failure of the rule. It is what BS 8418 verification exists for (E4). Our number
  sits upstream of the operator; never put it next to "3 per year" as if they were
  the same quantity. The red flag is an interviewer hearing "2.9 FA/cam-h" as
  "2.9 police call-outs".
* **Operator interface.** H22/H45 show that 1 operator on 40 cameras at A1 is
  0.88 utilised and realises 0.511–0.586 recall within 5 min. So the rate already
  saturates a human in simulation. A real ARC would not accept it for a single
  site's loiter channel.
* **PIDS-style zone budget.** Only the fused line-cross point beats ~1/zone/day,
  and it uses simulated sensors matched on **true positions** (FACTS H53).

**What closes the gap** (in the order a site would actually apply it):

1. **Zoning.** Arm a rule only where the behaviour is anomalous (sterile zone,
   perimeter, closed car park). H40b's fenced worlds gave **0** clean non-twin FA
   (≤ 0.001, rule of three). Most of loiter's 2.9 comes from places where
   standing is normal. We measured a zone-function context cut of ~21 % (`58` §7.2), not an order of magnitude.
2. **Scheduling.** Arm out of hours. It removes most commuter/smoke-break twins
   [INF]; the twin floor 1.008 is a *daytime* population.
3. **Fusion with non-video evidence.** H53: badge/tag/PIDS removed 99 % of twin
   FA for −0.023 recall (simulated). Tailgating defeats it (recall 0.007).
4. **Operator triage.** Ranked queues (+0.035 to +0.262 realised recall, H22/H45)
   decide which alarms get seen. The police threshold is met here.
5. **Only then** thresholds and learned rules: H33 shows the conformal
   floor at our sample size is 0.248–0.263, so 0.001 cannot be certified from
   338 worlds anyway.

## 3. The 0.001 FA/cam-h budget (assumed: A = 4, K = 500, H = 8) — provenance and defensibility

**Where it came from (grep, this session).** `docs/research/28_BEHAVIOUR_SCENE_DEEP_DIVE.md`
§6 derives `B = A/(K·H)` with `AlarmScore.operator_verdict` in `survsim/eval/alarms.py`
hard-coding **A = 4, K = 500, H = 8 ⇒ 0.001** (`DEFAULT_BUDGET_FA_PER_CAMERA_HOUR`,
also cited in `docs/13_BASELINES.md` l. 338). `28` itself says "The A, K and H figures
are assumptions, not sourced numbers" and gives a gentler `19` §5.3 alternative
of **0.12** (6 alarms per operator-hour, 50 cameras per operator). Every
"2,900× over" line in `13`, `19`, `23`, `46`, `57` inherits the invented
constants.

**Is it defensible?** Partly, as an order-of-magnitude *upper* stress test.

* K = 500 is a *passive watching* ratio (large public-space systems). Alarm
  verification at an ARC is measured per alarm handled, not per camera watched.
  So A/(K·H) mixes two jobs [INF].
* The NPCC threshold (E1) is per *system*, not per camera. Converting it per camera
  gives 10⁻⁵–10⁻⁶. The number is so small because it is post-verification.
  Our assumed 0.001 sits between the police and operator interfaces and matches neither.
* A defensible way to state it: "at 0.12 FA/cam-h an operator on 50 cameras sees
  6 alarms/h; at 0.001 (assumed, A = 4) an operator on 500 sees 4 per shift. Our points are ~18–42×
  over the lenient end and 2,000–5,000× over the strict end."

**What a defence / CNI customer would actually specify** [A, PIDS/OR practice, `76` §2.2]:

* An **Operational Requirement** naming the threat, attack methods (walk, run,
  crawl, log roll, ladder — the i-LIDS approach list [V-corpus]) and zones.
* **Pd ≥ 0.9 per attack method** (often 0.95), demonstrated at a stated
  confidence. By the zero-failure binomial: 22 successes out of 22 trials give Pd ≥ 0.9 at 90 %
  confidence; 29/29 give 95 % confidence [INF: n = ln(1−C)/ln(Pd)]. So a
  "Pd 0.9" claim is only as good as its trial count. Our H40b recall 0.782
  [0.736, 0.829] already fails the point estimate.
* **NAR ≤ ~1 per zone per day** (sometimes per week for sterile zones), with nuisance causes
  (wildlife, weather, vegetation) and false causes (equipment) **reported separately**.
  SurvSim's evaluator does not yet label causes.
* An **alarm assessment time**. i-LIDS gives the 10 s alarm window. Beyond that,
  operator assessment-to-response times go in the OR.

## 4. Ten interview Q&As

**Q1. Is 2.9 false alarms per camera-hour good or bad?**
Bad for a single-site ARC channel, and it is operator-facing: ≈ 120/h at 40
cameras. Compare it with an operator budget (0.12 lenient, 0.001 strict, both
our assumptions) or a PIDS zone-day budget (~0.04/h), never with police call-outs.
*Red flag:* "it's fine because a human checks it" without giving the operator load.

**Q2. What's the UK police rule for alarm systems?**
NPCC: Level 1 response until 3 false calls in a rolling 12 months; warning at 2;
withdrawal at 3; 90 days clean to reinstate; BS 8418 CCTV uses the same thresholds.
Hold-up alarms withdraw at 2. *Red flag:* "3 false alarms per year per camera".
It is per URN'd system, and it counts calls passed to police.

**Q3. Where does your 0.001 budget come from?** (our budget, assumed)
A/(K·H) with invented constants (4 alarms per shift, 500 cameras, 8 h), hard-coded
in `alarms.py`; `28` flags them as assumptions. I quote the 0.001–0.12 range.
*Red flag:* citing 0.001 as an industry standard.

**Q4. What's the false-alarm rate of real alarm systems?**
The US DOJ estimates 94–98 % of calls to police are false (via Sampson 2011). That is a
precision at the police interface of 0.02–0.06, not a per-hour rate.
*Red flag:* turning a percentage into a rate without a denominator.

**Q5. What does i-LIDS say about false alarms?**
Anything more than 10 s after the event starts is a false positive; repeats are
logged at most once per 5 s; it scores F1 with recall bias α; commissioning at F1 0.7; the datasets are about 24 h per
scenario. It is a protocol, not a field rate. *Red flag:* quoting an i-LIDS
"FA/hour" figure. None is published; the pass marks are not public.

**Q6. How would a defence customer write the requirement?**
An OR with attack methods per zone, Pd ≥ 0.9–0.95 per method at a stated confidence
(zero-failure trials: 22 for 0.9 at 90 %), NAR per zone per day with causes
split, and assessment time. *Red flag:* "95 % accuracy".

**Q7. Your fused line-cross hits 0.0047. Ship it?**
Not on that evidence. The sensors are simulated with assumed parameters and matched on true positions,
recall fell 0.782 → 0.758 below a 0.9 Pd bar, and tailgating goes through. It shows
the *architecture* that meets a zone-day budget; the site trial proves the number.
*Red flag:* calling 0.0047 a measured field rate.

**Q8. What closes the gap from 2.9 to something an ARC accepts?**
Zoning and scheduling first (they remove the innocent population), then fusion,
then ranked triage, and thresholds last. The conformal floor at our sample size is
~0.25, so thresholds alone cannot certify small budgets.
*Red flag:* "a better model".

**Q9. How would you find the real rate in the first month?**
Shadow mode: run the rule on a real site's tracks with no alarms delivered. Label
a stratified sample of alarms by cause (nuisance/false/true). Report FA per zone-day
with a Poisson CI and operator minutes per day. Then recompute the budget from the
customer's real A, K and H. *Red flag:* assuming mock constants transfer.

**Q10. Do BS EN 50131 or 62676 set a false-alarm rate?**
Not to my knowledge. 50131 grades intruder systems; 62676-4 is DORI pixel density.
The numeric thresholds in the UK come from the NPCC policy and the ARC's own KPIs.
*Red flag:* inventing a standard's FA number.

## 5. Sources

- NPCC Police Requirements for Security Systems 2024 — https://www.policesecuritysystems.com/images/Policy%202024/NPCC%20Police%20Requirements%20for%20Security%20Systems%202024.pdf [V, §2.10, §3.2, §3.3, §3.4]
- i-LIDS user guide — https://assets.publishing.service.gov.uk/media/5a7ac14d40f0b66eab99c6c0/ilids-user-guide.pdf [V]
- gov.uk i-LIDS page — https://www.gov.uk/guidance/imagery-library-for-intelligent-detection-systems [V]
- Security alarm (US DOJ 94–98 %) — https://en.wikipedia.org/wiki/Security_alarm [V secondary]
- Internal: `28` §6 (budget derivation), `51` §1 (standards chain), `76` §2 (i-LIDS, PIDS), FACTS H58/H42/H33/H45/H40b/H53, `77` §4 #1.
