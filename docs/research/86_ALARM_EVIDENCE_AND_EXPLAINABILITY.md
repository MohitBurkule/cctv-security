# 86 · Alarm evidence and explainability: the alarm card, the evidence pack and the log

Written 2026-09-27. This doc builds on `59` (assurance and audit trails), `74` drill 1 (the
alarm path), `58` §8.4–8.5 (ranked queue), `32` §H22/§H33/§H45, `44` (law), `45` (VLM cost),
`72` (forensic search) and `85` (defence context). `59` §2 already lists an evidence pack.
This doc splits it into what the operator needs in 30 s (the **card**) and what a court or
auditor needs months later (the **pack** plus the **log**). It then proposes a SurvSim schema.

Tags: **[V]** fetched from the primary URL for this doc (2026-09-27) or already a FACTS row;
**[A]** named but not fetched (the page returned 403/404, or only a secondary page was
fetched); **[X]** checked and false; **[INF]** my own reasoning or arithmetic.

---

## 0. The answer in seven sentences

1. An alarm card has one job: let an operator make a **dispatch / dismiss / escalate**
   decision in about 30 s. That is the mean review time in H22's operator model, and it is an
   invented parameter, not a measurement (`32` §H22) [INF].
2. For a track-rule alarm, the explanation is the **rule trace**: zone, dwell clock, score, θ
   and the track on a map. It is cheap and it is *faithful*, because it is the computation
   that raised the alarm.
3. For a learned model, a saliency map is not a faithful explanation. Adebayo et al. found
   some saliency methods "independent both of the model and of the data generating process"
   [V]. So show the model's **calibrated score and rank**, plus the conformal guarantee on θ
   (H33), and never call the detector "interpretable".
4. For later legal use, the **pack** needs hashes, a reliable time and place, and an audit
   trail that a third party could replay to get the same result. That is ACPO principle 3
   [V], BS 10008-1:2020 [V] and SCC §11.2 [V].
5. The **WORM log** records each human verdict with the alarm id, clip hash, model hash, θ
   and operator. That record is the evidence we would offer that a decision had "meaningful human
   involvement" (UK GDPR Art 22A, via DUAA s.80 [V, FACTS]), and it is also the in-service
   evidence JSP 936 asks for (`59` §4.3).
6. A VLM caption helps the operator read the clip. It is not an explanation of why the alarm
   fired, and it must never raise or clear an alarm (`59` §1.3, `74` drill 1).
7. In SurvSim the card can also carry the ground-truth match (hit / late / wrong actor).
   **That field is simulator-only and must never appear on a real card, pack or log** (§7).

---

## 1. The 30-second budget: what the card must carry

H22 gives the operator a gamma-distributed review time with mean 30 s and cv 0.3. The
operator slows by ×1.25 after 2 h and bulk-acknowledges the whole queue once it holds more
than 10 alarms (`32` §H22) [INF, invented operator]. At A1's θ 0.95, 40 cameras produce about
120 alarms/h and the operator is 0.88 utilised. Realised recall at 5 min is 0.511 with a FIFO
queue and 0.586 with a ranked queue, against a model recall of 0.825 (`32` §H22). At the
conformal point the rate falls to about 92 alarms/h, and ranked recall at 5 min rises to 0.621
(`32` §H45, `58` §8.5).

The card design follows directly. **Every second of review time costs recall.** H22 did not
vary review time, so the size of that cost is untested [INF]. The card must answer three
questions, in this order:

| # | Operator question | Card element | Source of the element |
|---|---|---|---|
| 1 | *Is there a person, and where?* | Keyframe with the track box. A 10 s pre / 5 s post clip that loops automatically. The camera name, and the zone drawn on a site map | detector/tracker; calib |
| 2 | *Why did it fire?* | One line: "in **Zone B-fence** for **74 s** (rule ≥ 60 s); score **0.97**, θ 0.96 → rank **2 of 7**" | the rule trace (§2) |
| 3 | *Should I trust this camera right now?* | A health badge (OK / tamper / blinded / PTZ off-preset), and any hard-negative context such as "bus stop 12 m away" | camera director; `62` zone semantics |
| — | Decision | Three buttons: **Dispatch / Dismiss (reason code) / Escalate**. Nothing is dispatched without a click | `74` drill 1 |

What stays **off** the card: heat maps, raw feature vectors, the full model card, and the VLM
paragraph unless the operator expands it. These all belong in the pack. Putting them on the
card adds reading time and adds no correct decisions [INF]. `51` covers the human-factors
side: alarm fatigue, and giving suppressions an expiry.

**The queue is part of the card.** H22 found that ranked beats FIFO by +0.262 at 30 s for A1
(`32` §H22). The rank and score on the card are therefore themselves the most useful
"explanation" the operator gets: they say *why this one first*.

---

## 2. What "explanation" means, by alarm type

NIST separates *explainability*, "a representation of the mechanisms underlying AI systems'
operation", from *interpretability*, "the meaning of AI systems' output in the context of
their designed functional purposes" [V, NIST AIRC AI RMF §3]. An alarm card needs the
second: what the output means for this site. An audit needs the first.

### 2.1 Track-rule alarm (dwell / zone / line-cross)

The trace **is** the mechanism. Record:
`rule_id@version`, zone polygon hash, entry time, dwell clock at firing, the threshold, each
feature value against its cut-off, the i-LIDS coalescing window, and the track IDs across any
hand-off. This is **faithful by construction**, because it is the computation that raised
the alarm. It is **cheap**: a few hundred bytes. It can be **replayed**, so the same frames
plus the same config hash give the same trace. That replay is exactly ACPO principle 3's test
that an "independent third party should be able to examine those processes and achieve the
same result" [V].

A **counterfactual** is also cheap and faithful for a rule: "it would not have fired with
dwell < 60 s" or "it would not have fired outside zone B". It is computed from the trace, not
estimated [INF].

### 2.2 Learned score (A1-style learned loiter rule, or a detector)

* **Saliency (Grad-CAM, integrated gradients) is not evidence.** Adebayo 2018 (arXiv
  1810.03292) [V] showed that *some* saliency methods fail the model- and data-randomisation
  sanity checks. That is a result about some methods, not all: a method that passes those
  checks has shown only that it depends on the model, not that it explains why *this* alarm
  fired [INF, AUDIT_86]. No saliency method is shown on the card or used as a reason. Keep it
  as an ML-team debugging tool (`59` §1.1).
* Rudin argues that "trying to explain black box models, rather than creating models that are
  interpretable in the first place, is likely to perpetuate bad practices" in high-stakes use
  (arXiv 1811.10154; Nature Machine Intelligence 2019) [V]. This is the design argument for
  keeping **the rule outer and the learned part inner**. A1 is a learned score gated by a
  dwell clock ≥ 5 s, so the trace can still show clock, zone and score (`58` §7.2).
* What to show instead is the **score, the θ that was in force, the rank, and a calibration
  statement**. For θ picked by conformal risk control (CRC), the statement is a guarantee on
  *expected* false alarms per camera-hour at the chosen α, valid only when sites are
  exchangeable. CRC "extend[s] conformal prediction to control the expected value of any
  monotone loss function" (Angelopoulos et al., arXiv 2208.02814) [V]. H33: at α 2.915, CRC
  exceeded α in 0/10 splits (test FA 2.312, recall 0.789), and the plain split exceeded it in
  6/10 (`32` §H33). This is a statement about the **alarm rate**. It says nothing about why
  *this* alarm fired, and the card should word it that way: "this camera is tuned to ≤ α
  expected false alarms/h".
  *Caveat (AUDIT_88):* CRC guarantee holds for a loss bounded by a B fixed in advance; H33 used the empirical max B (84–89, approximate); H33b uses a fixed B = 123.5 FA/cam-h — θ 0.9615–0.9642, held-out FA 2.216 ≤ 2.915 in 10/10 splits, recall −0.006 vs empirical B (32 §H33b).
* A **feature-level trace** is only honest when the features are named quantities (speed,
  heading change, dwell, distance to fence). Then say "top features by the model's own
  weights" for a linear model, or omit it. Do not present SHAP values on raw pixels as a
  reason [INF].

### 2.3 Detector and tracker below the rule

The detector's own decision (is there a person?) is not explained. It is **shown**: the box,
the mask-derived visibility fraction and the clip. The operator verifies with their own eyes.
That is the whole point of keeping a human in the loop [INF].

---

## 3. Later legal use: the evidence pack and chain of custody

| Requirement | Primary source | What it asks of the pack |
|---|---|---|
| Don't change the data; keep an audit trail a third party can replay; the person in charge is responsible | ACPO *Good Practice Guide for Digital Evidence* v5 (Oct 2011, published Mar 2012), principles 1–4 [V, PDF text] | Store the original clip bytes with their SHA-256. Analytics work on a copy. Every process applied (transcode, crop, redaction) is logged with its hash in and hash out |
| Evidential weight: ESI "demonstrably trustworthy about its authenticity and integrity"; transfer, identity linking, authenticity verification | BS 10008-1:2020, 31 May 2020, current; supersedes the 2014 edition [V, BSI page] | A hash-chained log (`59` §6.2). The export carries its hashes and a verification procedure |
| "Recorded material should be stored in a way that maintains the integrity of the image and information, with particular importance attached to ensuring that meta data (e.g. time, date and location) is recorded reliably"; exports "interoperable and can be readily accessed and replayed" | Surveillance Camera Code (amended, in effect 12 Jan 2022), §11.2 [V] | A trusted clock with its NTP/PTP state recorded; camera location and calibration at alarm time; export in a replayable open format |
| Retention: store no more than "strictly required for the stated purpose" and delete "once their purposes have been discharged" | SCC principle 6 [V] | Separate TTLs: continuous video (e.g. 30 d ring in `74`), alarm packs (until disposition plus the review period), and incident packs (held while the incident is open). ~31 days is common practice, not a rule (`44` §5.1) |
| Review and audit: "effective review and audit mechanisms … and regular reports should be published" | SCC principle 10 [V] | Supervisor samples of dismissals (`74` drill 1); periodic FA/cam-h and time-to-verdict reports |
| Defence records management | MOD JSP 441 [A — no gov.uk or National Archives URL resolved, AUDIT_86] | Retention and disposal schedules for the log and packs follow the site's JSP 441 schedule. Don't invent periods |

SCC binds relevant authorities only (PoFA 2012). For a private or defence site it is a good
baseline, not law (`44`, FACTS) [V, FACTS].

---

## 4. The WORM log: contestability and assurance

The log entry for each alarm is the one in `74` drill 1 (reconciled with this doc by
AUDIT_86): **alarm id · pack hash · clip hash · model + config hash · θ · operator id
(hashed) · verdict (dispatch / dismiss / escalate / bulk_ack) · reason code ·
time-to-verdict · prev/entry hash**. Each entry is chained with `h_i = SHA-256(h_{i−1} ‖ entry_i)`, and the
head hash is anchored off-box (`59` §6.2) [INF].

* **Art 22A–D (UK GDPR as amended by DUAA 2025 s.80, fully in force 5 Feb 2026).** A
  decision is solely automated "if there is no meaningful human involvement". Significant
  solely-automated decisions need safeguards, including the right to contest and to obtain
  human intervention [V, FACTS rows from legislation.gov.uk]. The log shows that a named
  human made each dispatch decision, what they saw (the card, identified by the pack hash),
  and how long they took. **A 0.4 s median time-to-verdict, or a bulk-ack, is evidence
  *against* meaningful involvement.** So log bulk-acks as their own verdict type, never as
  dismissals [INF]. H22's 25 % bulk-ack share at A1 FIFO is the number to worry about here
  (`32` §H22).
* **Contestability.** A data subject or their lawyer can ask why a guard was sent. Answer
  with the rule trace and the operator's verdict, both replayable from the hashes. Whether
  something is a "significant decision" is a legal call, not an engineering one (`85` never-claim).
* **JSP 936 Part 1** (MOD, 13 Nov 2024) is the MOD's framework for AI capabilities "which have
  the right level of human oversight" [V, gov.uk]. The log supplies the evidence `59` §4.3
  maps to its paras: model hashes on the model card, in-service monitoring, and regression on
  retrain.
* **ISO/IEC 27001:2022** (the information security management system) [V, BSI page; iso.org 403]: this is
  the standard that governs the log's *store*, meaning access control, key management,
  backup and logging of admin access. Say "run under an ISO 27001 ISMS". Don't claim the
  product is "27001 certified", because organisations are certified, not products [INF].

---

## 5. What a VLM caption adds and costs

**What it adds.** A sentence such as "one adult in dark clothing walking along the inner fence
line, stops twice, looks at the gate". This helps a tired operator orient faster, and it gives
free-text search later (`72`). It can also speed up the "is this a person" check at night
[INF, unmeasured].

**What it costs.**
* **Tokens.** Always-on at ~100 tokens/s, Gemini's default media resolution, is 360,000
  tokens per camera-hour, or $0.036–$0.108/cam-h input (`45` §5.2). On triggers only, a 15 s
  clip is about 1,500 tokens. At ~92 alarms/h over 40 cameras that is ~0.14 M tokens/h for
  the whole site, against ~14.4 M always-on [INF, arithmetic on `45`'s rates]. Triggered use
  is the only sensible design.
* **Latency.** The caption arrives after the card. It must never block the buttons [INF].
* **Faithfulness.** The caption describes the clip. It does not describe the alarm's
  computation. It can hallucinate, and it is a second model that needs its own hash in the
  log (`59` §1.3). It must never raise, clear or re-rank an alarm.
* **Governance.** A generative component brings NIST AI 600-1, the Generative AI Profile
  (26 Jul 2024) [V, NIST page], into scope. On a defence site it must run on-site (`74`,
  `85`).

---

## 6. Standards to name, and how to name them

| Standard | Status here | What to say |
|---|---|---|
| NIST AI RMF 1.0 (NIST AI 100-1, 26 Jan 2023, voluntary; Govern / Map / Measure / Manage) | [V] | "The card and log are evidence we would offer for *Measure* and *Manage*." The operator-level card matches NIST's transparency "tailored to the role or knowledge of AI actors" [V, AIRC §3]. (NIST does not use the phrase "role-appropriate"; AUDIT_86 removed it) |
| NIST AI 600-1 GenAI profile (26 Jul 2024) | [V] | Only if a VLM is in the loop |
| ISO/IEC 42001:2023 (AI management system) | [V] (BSI page: a standard to "establish, implement, maintain and continually improve an AI management system"; BSI Knowledge: BS ISO/IEC 42001:2023, dated 31 Dec 2023, now superseded by BS EN ISO/IEC 42001:2026 with "no technical differences"; iso.org still 403) | "An organisation-level AI management system. The log is an input to its monitoring." No clause numbers from memory |
| ISO/IEC 27001:2022 | [V] (BSI page: "the global information security management system (ISMS) standard"; transition deadline 31 Oct 2025; certification is of organisations) | ISMS for the log store (§4) |
| BS 10008-1:2020 | [V] | Evidential weight of the log and packs |
| ACPO Good Practice Guide v5 | [V] | The four principles, especially 3 |
| SCC (amended 2022) principles 6, 10, 11; §11.2 | [V] | Retention, audit, evidential integrity |
| JSP 936 Part 1 | [V] | Human oversight; model-card hashes (`59` §4.3) |
| JSP 441 | [A] (AUDIT_86 retried two gov.uk slugs, the National Archives web archive and the gov.uk search API: all 404 or no hit) | Records retention on defence sites |
| UK GDPR Arts 22A–D (DUAA s.80) | [V, FACTS] | Meaningful human involvement; contestability |

---

## 7. Proposed SurvSim alarm-card / evidence-pack schema

This is a proposal. **None of this is written per alarm today**: `59` §2 lists per-alarm pack
export and a hash-chained log as gaps, and they remain gaps.

> **SIM-ONLY FIELD — `gt_match` must never reach a real card, pack or log.** It is computed
> from ground truth that a deployment does not have. On a real site it would be a fabricated
> label presented as evidence. A card generator must drop it (and any `event_id`) whenever it
> runs in real mode; H60 (`66`) proposes a test that enforces this.

Tags on each field were checked against the code by AUDIT_86: `survsim/eval/alarms.py`
(`Alarm` = `t, label, camera, uid` only), `survsim/eval/rules.py`, `survsim/eval/pipeline.py`,
`survsim/gt/writers.py`, `survsim/director/world.py` (`Event.as_dict`),
`survsim/director/camera_director.py` (status rows) and
`survsim/experiments/operator_queue.py`. **[fillable]** means a writer or runner emits the
value today; **[join]** means it can be derived by joining emitted files, with no code that
does it yet; **[not emitted]** means it exists only inside a runner's memory.

```yaml
alarm_card:            # shown to the operator (≤ 30 s)
  alarm_id: uuid                # H60: sha256(run|camera|t|track|label|idx)[:16] [emitted, card]
  t_raised_utc: float           # Alarm.t (sim s); no UTC epoch written  [fillable as sim t]
  camera_id: str                # Alarm.camera: set by eval/pipeline alarms only;
                                # GT rules (rules.py) emit camera=None   [partial]
  zone_id: str                  # not on Alarm; world.parquet `zone` at (uid, t) [join -> emitted by H60, sim only]
  track_uid: str                # Alarm.uid: set by rules.py only;
                                # pipeline alarms emit uid=None          [partial]
  keyframe_ref / clip_ref: path # frames exist per run; no clip export    [gap]
  box_xywh, visibility: [..]    # gt/mot_<cam>.txt: left,top,w,h + visible_frac [emitted by H60, sim only: GT box]
  rule_trace:
    rule_id, rule_version: str  # Alarm.label only; no version            [partial]
    dwell_s, threshold_s, zone_hash, features: {name: value}  # rule-internal [not emitted]
    score, theta                # H22 run writes alarms_scored.jsonl; carded via --alarms [emitted, H60 s2: H22 only]
    alpha_crc                   # H33 results.json, per split, not per alarm [partial]
    rank_in_queue               # H22 simulated queue, rank at arrival     [emitted, H60 s2: H22 only]
  camera_health: ok|tamper:<kind>|blinded|ptz_off_preset  # camera_status.jsonl has
                                # t, camera, yaw, pitch, hfov_deg, tamper, blind;
                                # "off preset" = compare with calib pose [fillable; preset: join]
  hard_negative_context: str    # zone semantics (62)                      [partial]
  vlm_caption: {text, model_hash}                                           [gap]
evidence_pack:         # for audit / court
  clip_sha256, frames_sha256[]  # card clip_hash over frames/<cam> in t±5 s [emitted if frames exist; mock: "not emitted"]
  model_hashes: {detector, tracker, reid, rule}; config_sha256  # model_hash (one --model file), config_hash [partial, H60 s2]
  calib_at_t: path              # calib/ + live PTZ pose                    [fillable]
  clock_source, clock_state                                                 [gap; sim clock exact]
  i_lids_delay_s: float         # AlarmScore.latencies_s is an unkeyed list [join -> emitted by H60 per alarm, sim only]
  processes: [{op, in_sha256, out_sha256}]  # ACPO principle 3              [gap]
  licences_ref: licences.json   # training/render provenance                [emitted by H60]
  gt_match: {event_id, hit|late|wrong_actor|false}  # SIM ONLY, NEVER IN mode=real
                                # score() returns counts only; operator_queue._event_index
                                # gives event index or −1 per alarm; late / wrong_actor
                                # are not labelled per alarm             [partial]
log_entry:             # WORM, chained
  alarm_id, pack_sha256, operator_id_hash, verdict (dispatch|dismiss|escalate|bulk_ack),
  reason_code, t_verdict, time_to_verdict_s, prev_hash, entry_hash          [emitted, H60; head.json
                                # anchored + JCS-style canonical since slice 2; H22 per-alarm verdict emitted]
```

**H60 update (2026-09-27, `survsim/eval/alarm_card.py`, `evidence_pack.py`, `survsim alarm-cards`):**
now emitted per alarm — `alarm_id`, t, label, camera, tracker `track_id` (only when the alarm source
supplies one), `calib_ref`, live PTZ pose (`camera_pose`, from `camera_status.jsonl`), `licences_ref`,
score/θ/rank when a runner passes them, and in **sim mode only** `zone_id`, `box_xywh` + `visibility`,
`camera_health` (tamper/blind truth), `gt_uid`, `gt_match` {hit|repeat|late|wrong_actor|false,
event_id} and `i_lids_delay_s`. The log entry is emitted (`alarm_id`, `card_sha256`,
`operator_id_hash`, verdict ∈ dispatch/dismiss(reason)/escalate/bulk_ack, `t_verdict`,
`time_to_verdict_s`, `prev_hash`, `entry_hash`). Still not emitted: clip/frame hashes, model/config
hashes, rule trace/features, `vlm_caption`, process log; score/θ/rank are still not *written* by the
H22/H33 runners, only accepted by the generator. For GT-rule alarms in real mode, camera, box, zone
and identity are empty — they need a tracker's output, not a join (66 H60 "abandon if", per field).
AUDIT_H60: `log_entry` is [emitted] but tamper-evident only against an externally anchored head
(tail truncation and a full re-chain verify otherwise); `operator_id_hash` is [partial] — the salt is a
public CLI default, not a per-site secret; `gt_match` stays sim-only and was 0/2 in real cards by key and value.
**H60 slice 2 (32 §H60 slice 2):** `operator_id_hash` is now [emitted] with a per-site `--salt-file`
(real mode refuses the public default); the pack writes `head.json` and `verify` fails closed without
it (truncation and re-chain caught — still only as strong as the out-of-band copy of the head);
canonical form is RFC 8785-compatible for the subset used; score/θ/rank_in_queue and the operator
verdict are written per alarm by the H22 runner (`alarms_scored.jsonl`) and carded (9 654/9 654 filled
for A1/FIFO, leak 0); `config_hash`, `model_hash`, `clip_hash` on every card (clip "not emitted" on
frame-less runs). Still gaps: H33 per-alarm output, rule trace, VLM caption, process log, signed head.

**What SurvSim emits today (AUDIT_86, checked in code):** alarm time and label (`Alarm`);
*either* camera (pipeline alarms) *or* track uid (GT rules), not both on one alarm; boxes as
MOT `left,top,w,h` with `visible_frac` (mask-derived on Unreal); calibration (`calib/`) and live
PTZ/tamper/blind state (`camera_status.jsonl`); licence provenance (`meta/licences.json`); and
run-level CRC α / θ (`h33` results). **Derivable by a join no code does yet:** zone at alarm
time (`world.parquet`), per-alarm i-LIDS delay (`events.jsonl`), off-preset flag. **Not
emitted, only inside runners:** per-alarm score, rank in queue, dwell/feature trace, per-alarm
hit/late/wrong-actor label, operator verdicts. **What only a simulator can fill** is
`gt_match`, and it must never ship to a real deployment's card (callout above). **What is
missing** is alarm ids, clip export and hashes, per-component model hashes, the process log
and the chained log itself.

The useful experiment this enables [INF]: vary the simulated review time with card content
(trace-only vs trace + VLM) in H22's operator model, and see whether realised recall moves.
The review times would still be invented, so any result is a sensitivity study, not a
measurement.

---

## 8. Q&As with red flags

**Q1. Is your system explainable?**
"For the alarm, yes. It is a rule over tracks, and the card shows the zone, dwell, score, θ
and rank that fired it, which you can replay from hashes. The detector underneath isn't
interpretable, and I don't claim it is. The operator verifies the detection from the clip."
*Red flag:* "we use explainable AI so the model is interpretable."

**Q2. Why not show Grad-CAM to the operator?**
"Some saliency methods pass the eye test but fail randomisation checks (Adebayo 2018). A
heat map that doesn't depend on the model isn't evidence, and it costs review seconds."
*Red flag:* presenting a heat map as the reason for dispatch.

**Q3. What does the operator see in 30 s?**
The keyframe with box, a looping clip, the zone on a map, one trace line, a health badge,
rank, and three buttons. *Red flag:* claiming 30 s is measured. It is H22's assumed parameter.

**Q4. How is the alarm usable in court?**
"Originals are hashed and untouched. Every process is logged in and out, so a third party can
replay it (ACPO principle 3). The log is hash-chained (BS 10008 for evidential weight). Time
and location metadata are recorded reliably (SCC §11.2)." *Red flag:* saying the footage "is
admissible". Admissibility is for the court.

**Q5. How long do you keep things?**
Per store and per purpose (SCC principle 6). On defence sites, per the JSP 441 schedule.
*Red flag:* "31 days is the legal limit". It isn't (`44` §5.1).

**Q6. How do you show a human decided?**
The WORM log entry: operator, pack hash, verdict, time-to-verdict. Bulk-acks are logged as
their own verdict type. *Red flag:* claiming the system is Art 22-compliant. That is a legal
determination (`85`).

**Q7. What guarantee does θ come with?**
CRC bounds the *expected* FA/cam-h at α on exchangeable sites. In H33: 0/10 exceedances vs
6/10 for the plain split, at −0.035 recall. *Red flag:* calling it a per-night or worst-case
guarantee, or a statement about one alarm.
*Caveat (AUDIT_88):* CRC guarantee holds for a loss bounded by a B fixed in advance; H33 used the empirical max B (84–89, approximate); H33b uses a fixed B = 123.5 FA/cam-h — θ 0.9615–0.9642, held-out FA 2.216 ≤ 2.915 in 10/10 splits, recall −0.006 vs empirical B (32 §H33b).

**Q8. Would a VLM caption help?**
It can help orientation and search, on triggers only (~0.14 M vs ~14.4 M tokens/h for a
40-camera site). It needs its own hash, it must not block the buttons, and it must never
raise or clear an alarm. *Red flag:* "the VLM explains the alarm".

**Q9. Which standards?**
NIST AI RMF (Measure/Manage evidence), ISO/IEC 42001 at organisation level, ISO 27001 for the
log store, BS 10008, and JSP 936. *Red flag:* "the product is ISO 42001/27001 certified".
Organisations are certified, not products, and SurvSim is neither.

**Q10. What does SurvSim fill today?**
Emitted: time, label, camera *or* uid (not both on one alarm), MOT boxes and visibility,
calibration and tamper/PTZ state, licences, run-level θ/α. By a join not yet written: zone,
i-LIDS delay. Not emitted per alarm: score, rank, rule trace, verdicts. Gaps: alarm ids, clip
and model hashes, the chained log. The GT match is sim-only and never goes on a real card.
*Red flag:* saying SurvSim produces evidence packs, or cards, today.

---

## 9. Sources (fetched 2026-09-27 unless marked)

1. NIST AI RMF page. https://www.nist.gov/itl/ai-risk-management-framework [V]
2. NIST AIRC, AI RMF §3 trustworthiness characteristics. https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/ [V]
3. Adebayo et al., *Sanity Checks for Saliency Maps*. https://arxiv.org/abs/1810.03292 [V]
4. Rudin, *Stop Explaining Black Box ML Models…*. https://arxiv.org/abs/1811.10154 [V]
5. Angelopoulos et al., *Conformal Risk Control*. https://arxiv.org/abs/2208.02814 [V]
6. ACPO Good Practice Guide for Digital Evidence v5. https://www.digital-detective.net/digital-forensics-documents/ACPO_Good_Practice_Guide_for_Digital_Evidence_v5.pdf [V, PDF text]
7. BSI, BS 10008-1:2020. https://knowledge.bsigroup.com/products/evidential-weight-and-legal-admissibility-of-electronically-stored-information-esi-specification [V]
8. Amended Surveillance Camera Code. https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version [V]
9. JSP 936 Part 1. https://www.gov.uk/government/publications/jsp-936-dependable-artificial-intelligence-ai-in-defence-part-1-directive [V]
10. BSI ISO/IEC 42001 page. https://www.bsigroup.com/en-GB/products-and-services/standards/iso-42001-ai-management-system/ [V scope]; year via BSI Knowledge https://knowledge.bsigroup.com/products/information-technology-artificial-intelligence-management-system [V, AUDIT_86: BS ISO/IEC 42001:2023, superseded by BS EN ISO/IEC 42001:2026]
10a. BSI ISO/IEC 27001 page. https://www.bsigroup.com/en-GB/products-and-services/standards/iso-iec-27001-information-security-management-system/ [V, AUDIT_86: ISO/IEC 27001:2022]
11. DUAA 2025 s.80. https://www.legislation.gov.uk/ukpga/2025/18/section/80 [V via FACTS rows 389–391; not re-fetched]
12. iso.org pages for 27001 and 42001 (403, incl. /obp), JSP 441 (gov.uk 404 on two slugs; National Archives 404) [A for JSP 441 only]
