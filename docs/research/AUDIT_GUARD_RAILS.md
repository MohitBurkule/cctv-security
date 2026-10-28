# AUDIT_GUARD_RAILS — do tonight's retired-claim patterns bite? (2026-09-28)

Method: two plausible unqualified sentences per row R64–R76 (plus new R77), each
checked against the registry pattern *and* its exemption; qualified sentences from
the day-of docs checked for false positives. Fixtures: `tests/test_retired_patterns_bite.py`.

**Structural finding.** `load_registry()` parsed the exemption column but
`is_exempt()` never consulted it: every row's qualifier cell was dead, and rows only
stayed quiet because their patterns demanded the H-id on the same line (so they
also missed any sentence without it). The column is now honoured for R64+ only —
older cells hold context words (R19 `round.2`) that 77 #4 ruled insufficient.

| row | before | after | bad sentences caught (before → after) |
|---|---|---|---|
| R64 | needs "H63b" on line | also "naive suppression" / "live rule" | 1/2 → 2/2 |
| R65 | needs "H66" | "escalat…" + restores/recovers recall; exempt adds `post.hoc` | 1/2 → 2/2 |
| R66 | OK pattern, but 0.162 in the correct cell exempted "0.162 duty cycle" | 0.162 moved into parentheses (retired-value slot) | 1/2 → 2/2 |
| R67 | needs "H70" | bare "recall is detector-limited"; exempt adds assumption / wrapped "**by" | 1/2 → 2/2 |
| R68 | needs "H69" | also "low-recall sites" | 1/2 → 2/2 |
| R69 | needs "H70b" + "C1 met" | also CUSUM, "passes C1" | 1/2 → 2/2 |
| R70 | needs "H71" + exact phrase | any "render(s) do not / don't rank" | 1/2 → 2/2 |
| R71 | needs "H71" | match_iou / max_lost / tracker knobs + flip | 1/2 → 2/2 |
| R72 | needs "H3b" | any "1.8× / 1.8x upscale" | 1/2 → 2/2 |
| R73 | needs "real street" | also "6/14 … realism stats in band" | 1/2 → 2/2 |
| R74 | costs-no-recall only | also "sparse scenes only" | 1/2 → 2/2 |
| R75 | strong | unchanged | 2/2 → 2/2 |
| R76 | needs "confirmed/supported" | any "second instance/case of … H32" | 1/2 → 2/2 |
| R77 (new) | none | "far cameras/people … blind" without CC0/conf/render/synthetic | 0/2 → 2/2 |

Doc fix forced by R77: 106 table row "far cameras are blind" → "…on our sparse renders (H3)".

**Numbers test.** Added 93, 101, 102, 103, 104 and the six `drills/coding_hour/**/README.md`
(prose only) to `test_docs_numbers_in_facts.py`; 17 derived decimals allowlisted
(drill reference-solution outputs and fixture parameters, demo reel duration).
