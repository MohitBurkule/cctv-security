# AUDIT_86 · Alarm evidence and explainability (86), from a hostile assurance lead

Audited 2026-09-27 against `6896b30`. Method as AUDIT_84_85: every [V] source in `86` was
re-fetched by WebFetch the same day and the quote compared; each [A] was retried on
alternative primary URLs; every "SurvSim can fill today" tag in `86` §7 was checked against
the code that writes alarms, events and GT. No GPU, editor or `survsim/` change.

## 1. The ten [V] sources re-fetched

| claim (86 §) | page | result |
|---|---|---|
| NIST AI RMF 1.0, 26 Jan 2023, voluntary; AI 600-1 26 Jul 2024 (§5, §6) | nist.gov AI RMF | **[V]** |
| Explainability / interpretability definitions (§2) | AIRC AI RMF §3 | **[V]** verbatim. **But §6's "NIST's 'role-appropriate' transparency" is not on the page**: NIST says "tailored to the role or knowledge of AI actors". Fixed |
| Adebayo: "independent both of the model and of the data generating process" (§0, §2.2) | arXiv 1810.03292 | **[V]** — the sentence says *some* methods. §2.2 named Grad-CAM and integrated gradients as "unfaithful", which the quote does not support method by method. Reworded: saliency is not evidence, and passing the checks would not make it an explanation of one alarm |
| Rudin quote; NMI 2019 (§2.2) | arXiv 1811.10154 | **[V]**; NMI 1, May 2019, 206–215 |
| CRC "control the expected value of any monotone loss function" (§2.2) | arXiv 2208.02814 | **[V]** (the page reads "We extend conformal prediction to control…"; 86's "extend[s]" is a fair bracketed edit) |
| ACPO v5 principle 3; Oct 2011, published Mar 2012 (§2.1, §3) | ACPO PDF (pdftotext) | **[V]** verbatim; cover "March 2012", footer "Version 5 (October 2011)" |
| BS 10008-1:2020, 31 May 2020, current, supersedes 2014 (§3) | BSI Knowledge | **[V]** |
| SCC §11.2, principles 6 and 10; in effect 12 Jan 2022 (§3) | gov.uk accessible version | **[V]** quotes verbatim; the in-effect date is on the parent page (existing FACTS row) |
| JSP 936 Part 1, 13 Nov 2024, "right level of human oversight" (§4) | gov.uk | **[V]** |
| DUAA s.80 / Arts 22A–D (§0, §4) | FACTS rows (legislation.gov.uk) | **[V]** via FACTS; not re-fetched, as 86 said |

## 2. [A] items retried

| item | tried | move |
|---|---|---|
| ISO/IEC 42001 year | iso.org/standard/42001 and /obp (403); BSI Knowledge product page | **[A]→[V]**: BS ISO/IEC 42001:2023 (31 Dec 2023); now superseded by BS EN ISO/IEC 42001:2026, "no technical differences". Quote corrected to "maintain and continually improve" (no comma) |
| ISO/IEC 27001 | iso.org (403); bsigroup.com ISO/IEC 27001 page | **[A]→[V]**: ISO/IEC 27001:2022, "the global information security management system (ISMS) standard", transition deadline 31 Oct 2025; certification is of organisations, which backs 86's "organisations are certified, not products" |
| JSP 441 | two gov.uk slugs (404), National Archives web archive (404), gov.uk search API (no JSP 441 document) | **stays [A]**. 86 already says "don't invent periods" |

## 3. Schema check: "SurvSim can fill today" vs the code

Code read: `survsim/eval/alarms.py` (`Alarm` = `t, label, camera, uid`), `eval/rules.py`,
`eval/pipeline.py`, `gt/writers.py`, `director/world.py` (`Event.as_dict`),
`director/camera_director.py` (`as_dict`), `experiments/operator_queue.py`.

**Fields 86 tagged fillable that the writers do not emit:**

| 86 field (old tag) | what the code does | new tag |
|---|---|---|
| `alarm_id` (untagged, implied) | no alarm id anywhere | gap |
| `camera_id` (fillable, "Alarm.camera") | only `pipeline.py` alarms set camera; GT rules emit `camera=None` | partial |
| `track_uid` (fillable) | only `rules.py` alarms set uid; pipeline alarms emit `uid=None`. No alarm carries both camera and uid | partial |
| `zone_id` (fillable) | not on `Alarm`; `world.parquet` has `zone` per agent-tick | join |
| `box_xyxy` (fillable) | MOT rows are `left,top,w,h` | renamed `box_xywh`, fillable |
| `score, theta, rank_in_queue` (fillable from runners) | H22 holds A1 score and the simulated queue in memory; nothing per alarm is written; CRC α is per split | not emitted (α partial) |
| `camera_health: ptz_off_preset` (fillable) | status rows carry yaw/pitch/hfov/tamper/blind, no preset flag | derivable by join |
| `i_lids_delay_s` (fillable, eval.alarms) | `AlarmScore.latencies_s` is an unkeyed list | join |
| `gt_match` hit/late/wrong_actor (fillable) | `score()` returns counts; `operator_queue._event_index` gives an event index or −1 per alarm; late / wrong-actor are not labelled per alarm | partial |
| log verdicts ("H22 sim has verdicts") | H22 keeps aggregate counts (reviewed, bulk_acks), no per-alarm verdict | gap |

Held: calibration (`calib/`), live PTZ/tamper/blind (`camera_status.jsonl`),
`visible_frac` (MOT), `meta/licences.json`. §7's paragraph and Q10 were rewritten to the
emitted / join / not-emitted split.

## 4. Red flags

* **GT match warning.** Before: one inline comment "# SIM ONLY" and one sentence after the
  schema. Now: §0 sentence 7, a bold callout at the top of §7, `NEVER IN mode=real` on the
  field, and Q10. H60 (`66`) pre-registers a test that enforces it.
* **Saliency helps?** No sentence says it helps the operator; §2.2's method-level overclaim
  was the only issue (fixed above).
* **"Compliant with".** None. The only "compliant" is Q6's red flag. §0 sentence 5 said the
  log "is the evidence that" a decision had meaningful human involvement; softened to "the
  evidence we would offer", because whether it suffices is a legal determination (`85`).

## 5. Consistency with 74 drill 1

74's WORM box listed alarm id, clip hash, model+config hash, θ, operator id, verdict, reason,
time-to-verdict. 86 §4 quoted it as also carrying pack hash and a hashed operator id, and
§7 adds `bulk_ack` and the chain hashes. **74's box now carries 86's full list** (pack hash,
hashed operator id, the four verdict types, prev/entry hash) with a pointer to 86 §4/§7; 86 §4
now says "reconciled", not "sketched". Box width unchanged.

## 6. Numbers

Every number in 86 is in FACTS: H22/H33/H45 rows already were; the ten source quotes/dates,
the two standards editions, the VLM cost chain (`45` §5.2 arithmetic) and the code-read field
lists are new rows under "Report 86". Arithmetic rechecked: 92 × 1,500 = 138,000 ≈ 0.14 M;
40 × 360,000 = 14.4 M.

## 7. H60

`66` gains H60 `h60_alarm_card` in the `49` §12 template: a card/pack/log generator from GT
and runner outputs with a hash chain and an i-LIDS verdict in sim mode, primary metric a leak
count that must be 0 in `mode=real`, and a first test (`tests/test_alarm_card_real_mode.py`)
written before code. Not implemented.

## Scores

| file | sources | code claims | honesty/tone | score |
|---|---|---|---|---|
| 86 | 10/10 [V] hold (one invented NIST phrase, one method-level overreach); 2 of 3 [A] → [V] | 10 fields over-tagged as fillable (of ~25) | no "compliant" claim; GT warning was present but not prominent | **7/10** |
| 74 drill 1 | n/a | n/a | log fields now match 86 | reconciled |
