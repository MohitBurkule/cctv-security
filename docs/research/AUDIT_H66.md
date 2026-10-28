# AUDIT_H66 — decoy flooding vs. operator queue

Scope: pre-registration aa80867 (2026-09-28 02:27), results 2879e65 (02:32), `survsim/experiments/decoy_flooding.py`,
`survsim/experiments/configs/h66_decoy_flooding.yaml`, `out/experiments/h66_decoy_flooding/{results,sensitivity}.json`,
`figures/h66_decoy_flooding.png`, FACTS row. Precedence confirmed: the pre-registration commit touches only 32 and
predates the code and every number.

Reduced rerun (100 worlds × 3 operator seeds, same code): fifo@300 s 0.723 (k = 0) → 0.570 (k = 16); ranked 0.563;
escalate 0.703 with the bulk-ack exemption, 0.603 without; hard-negative escalations 0.00125 /cam-h; added
genuine-incident delay 0 in every world. Direction reproduces; the drop is smaller at this n (not significant evidence
either way, n is 10× smaller).

| # | Claim | Verdict | Fix |
|---|---|---|---|
| 1 | "Decision: met (3 of 3)" | **FAIL.** Registered operator: "bulk-acknowledge (queue cleared, alarms lost)", no exemption. The exemption (`escalated_exempt_bulk_ack`, default True) was added in code after registration. As registered escalate@16 = 0.538 [0.514, 0.563]; (2) needs ≥ 0.640 → not met. | 32 + FACTS reworded "NOT met as registered"; R65 |
| 2 | Escalation restores recall | **Mostly construction.** Of the 0.203 recovery, 0.151 is the exemption (escalated alarms survive a clear-all); the queue jump adds 0.052. The qualification in 32 said so; the headline did not. | reworded |
| 3 | Bulk-ack behaviour from H22 | **OK.** `operator_queue.py` clears the queue at > 10, same threshold; itself an invented operator (H22 is declared assumption). | none |
| 4 | Escalation rule is realistic | **Oracle-clean.** In recall worlds the intruder is never badged and always inside the 180 s window (lead ≤ 90 s), so every detected intrusion escalates; no tailgating or borrowed badge. | noted in 32 |
| 5 | Ranked arm uses H45c scoring | **No — stand-in.** Scores are Beta(2,5)/Beta(5,3)/Beta(8,2) draws. "Ranked no better than FIFO" is a property of those laws. | noted in 32 |
| 6 | Holm / bootstrap units | **OK with note.** World-level resampling, operator seeds averaged within world (correct unit). Holm p 0.0015 = 3 × 1/2001, the bootstrap floor — "at least this small", not an estimate. | noted |
| 7 | Hard negative is a true hard negative | **Partly.** The crossing is innocent and co-timed, good. But it always follows the incident's first alarm, so it can never delay that first review: "0 s added delay" is structural. Cost reduces to (1 − p_swipe) × p_detect. | noted |
| 8 | 0.98 badge assumption dominates (3) | **Yes**, already qualified (p_swipe 0.80 → 9× escalations, still under bar). Escalation-count half of (3) is honest; delay half is vacuous (row 7). | none |
| 9 | FACTS row / 32 qualifications honest | Qualifications honest; headline "Decision met" contradicted them. | fixed |

Honest interview sentence: *in a simulated one-operator wall (H22's invented operator), a 16-alarm decoy cuts FIFO
realised intrusion recall by about 0.20 (0.690 → 0.486); what saves the intrusion is a procedure — never bulk-clear an
un-badged perimeter alarm — not a smarter ranking, and that fix was chosen after pre-registration.*
