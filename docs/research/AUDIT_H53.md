# AUDIT_H53 · Late sensor fusion on the line-cross rule

Audited 2026-09-27 against `out/experiments/h53_sensor_fusion/{results.json,fused_worlds.jsonl}`,
`survsim/experiments/sensor_fusion.py`, config `h53_sensor_fusion.yaml`, pre-registration `6766666`
(32 §H53), runner `0c492ba`, results `4e32862`. No GPU, nothing re-run; recomputed from the JSON.

**Score: 88 → 100** (every headline number matched; four imprecise claims corrected; one design flaw and
one matching limitation made explicit everywhere the result is quoted).

## 1. Numbers recomputed (all match)

| claim | recomputed | ok |
|---|---|---|
| C twin FA 0.488 [0.447, 0.533] | 1,465 / 3,002 cam-h = 0.4880, boot [0.4472, 0.5331] | ✓ |
| C+a / C+b / C+c twin FA 0.0100 / 0.0227 / 0.0043 | 30 / 68 / 13 alarms → 0.0100 / 0.0227 / 0.0043 | ✓ |
| C+abc 0.0047 [0.0023, 0.0075], 99.0 % [98.5, 99.5] removed | 14 alarms → 0.0047 [0.0023, 0.0075]; 0.9904 [0.9846, 0.9954] | ✓ |
| recall@10 0.782 / 0.745 / 0.621 / 0.681 / 0.758 [0.710, 0.805] | 233 / 222 / 185 / 203 / 226 of 298 | ✓ |
| −0.023 = 7 detections | 233 − 226 = 7; 7/298 = 0.0235 | ✓ |
| tailgate C+a 0.000, C+abc 0.007 | 0 / 298, 2 / 298 | ✓ |
| stolen tag C+b 0.000, C+abc 0.701 | 0 / 298, 209 / 298 | ✓ |
| non-twin clean FA 0 on every arm | `primary_fa` = 0 on all five; total = twin | ✓ |
| 259 intruder alarms; RF matches 52, badge 11; 7 lost | from `fused_worlds.jsonl` flags: 259 / 52 / 11; (a or b) and not c = 7 | ✓ |
| decision | `twin_fa_ok` true, `recall_ok` false, `met` false, secondary ≤ 0.02 false | ✓ |

## 2. Design checks

* **Every sensor parameter is declared as an assumption** — pre-reg `sensors (every parameter is an
  ASSUMPTION …)` lists p_swipe 0.98, jitter 1 s, ±15 s; p_carry 0.95, 0 dBm, 1 Hz, 15 % miss, n 2.8,
  4 dB, −80 dBm, ±5 s; p_detect 0.9, lead U(0, 10) s, wind 1/zone-h, [−30, +5] s; tailgate lead U(1, 5) s.
  The config carries the same values under `# simulated sensors: ASSUMPTIONS, not fitted`. ✓
* **Fusion is genuinely late**: `fuse_world` takes arm C's recorded alarms and keeps/drops each one
  (alarm-level gate); no track or detection is changed and nothing is re-simulated. ✓
* **Matching uses ground truth** (limitation, now stated in 32, 37, 52, 60, 64, 74, 76, FACTS, 48, 78):
  each alarm carries the true uid; the crossing time/zone for (a) and (c) comes from that person's TRUE
  track, and the RF range is measured at the TRUE position. A real system associates by estimated
  position and will keep less than 99 %. The pre-reg confounds line said "association uses true
  positions", so this is registered, not hidden — but most downstream quotes had dropped it.
* **The "≥ 0.782" recall bar** was pre-registered as written ("Fusion only removes alarms, so the recall
  leg means no intruder detection lost"). It is a **design flaw**: a gate that can only remove alarms,
  run on worlds that deliberately place a tagged/badged twin beside the intruder, can essentially never
  score zero loss, and the prediction itself expected "< 1 pt" loss. The ≤ 0.02 secondary (H49's bar)
  was the sensible primary; H53 misses it too (0.023). Verdict "not met" stands.
* **Tailgate is a stream injection**, not a behaviour (registered); H54 connects `tailgate` to the gate.

## 3. Corrections (Edit in place)

| # | where | was | now |
|---|---|---|---|
| 1 | 32 §H53 Reading | "recall cost of 2-4 points" | 2.3 combined; single gates 3.7 / 10.1 / 16.1 |
| 2 | 32 §H53 Reading, 66 | "≥ 0.782 bar near-unreachable" only | stated as a registration design flaw; true-track matching spelled out |
| 3 | 66 H53 status | "target ≥ 90 % met, robust" | twin leg met (boot upper ≤ 0.0488); `robust` in the JSON is false because recall failed |
| 4 | 37 §8, 76 row, FACTS | no matching caveat | "matched on true tracks/positions" |

## 4. Fold-in

FACTS H53 row qualified + audit row; 52/64 register rows and 64 paragraph; 60 item 40; 48 C8 follow-up 4
("how do you handle the patrol guard?"); 65 v2 §2 item 4, Q2, Q4, §7, §10; 74 drill 1; 78 opener and §1.5;
77 weak #1 note; 66 H49 status (gate-log arm answered by C+a: 49× cut, −0.037 recall) and new H54.
79 has no fusion Q&A (its Q2/Q4 are forensic search and PSI); the Q2/Q4 updates are in 65 v2's table.

**Reinstated (78 opener), exact form only:** "context and a second sensor remove 99 % of authorised-crosser
FA (0.488 → 0.0047/cam-h, H53) at a 2.3-point recall cost, all sensors simulated; a tailgater defeats it".
RETIRED_CLAIMS R55 flags "context and a second sensor" on any line without H53 + simulated + tailgat…;
fixtures added to `tests/test_docs_retired_claims.py`. Both doc tests pass.
