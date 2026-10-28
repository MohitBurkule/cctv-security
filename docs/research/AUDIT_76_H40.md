# AUDIT_76_H40 · Intrusion behaviours (76) and the line-crossing experiment (32 §H40)

Audited 2026-09-27 against `2323de7`. Method as AUDIT_H22_H33: every H40 number recomputed in Python
(`.venv`) from `out/experiments/h40_line_cross/results.json` (`noisy_*`, `free_*`,
`noisy_ratio_N_over_C`, `decision`, `wall_s`) and, for the depth claims, from the cached recall tracks
(`recall_tracks/*.parquet` + `.json`) with `line_cross.zone_state`; method checked against
`survsim/experiments/line_cross.py` and the pre-registration (`02b51ae`). Every 76 URL re-fetched by
WebFetch this session (WebSearch exhausted); PDFs (i-LIDS guide, ST-GCN, UCF-Crime) extracted with
`pdftotext` and grepped.

## 1. H40 — recomputed

| claim | recomputed | result |
|---|---|---|
| clean FA/cam-h N / A / B / C 70.96 / 66.48 / 5.11 / 4.20 | 213,034 / 199,585 / 15,343 / 12,597 over 3,002.0 cam-h = 70.964 / 66.484 / 5.111 / 4.196 | match |
| world-boot 95 % N [63.80, 78.30], C [3.84, 4.57] | [63.798, 78.297], [3.842, 4.569] | match |
| recall@10 0.945 / 0.925 / 0.120 / 0.100 | 189 / 185 / 24 / 20 of 200 | match |
| C recall CI [0.060, 0.145]; intrusion / probe 0.000 / 0.200 | same | match |
| N/C 16.9× [15.3, 18.6]; noise-free 3.85 | 16.911 [15.308, 18.566]; 3.853 | match |
| "71,000×" budget | 70.964 / 0.001 = 70,964 | match (rounded) |
| "every arm 4,000×+" | C 4,196× | match |
| ghosts < 1 % of naive alarms; A removes 96 % | 1,873 / 213,034 = 0.88 %; 1 − 71/1,873 = 96.2 % | match |
| B removes 92 % of N; noisy N 4.2× noise-free | 1 − 15,343/213,034 = 92.8 %; 70.96/16.98 = 4.18 | match |
| fragments 109,445, commuters 101,716 | `clean_fa_by_source` | match |
| "6/100 intrusion actors ≥ 1.5 m deep within 10 s (35 ever)"; probe 25/100 | re-derived from true positions: 6 / 35; probe 25 within 10 s | match |
| wall 11 min | 681.6 s | match |
| decision (i) met, (ii) met robustly, (iii) failed | `decision` dict | match |

**Code vs registration.** Arm C's registered exclusion is "within 4 m of a gate- or queue-tagged zone
**or a door prop**"; `near_context` uses gate/queue zones only. Undisclosed before this audit;
now disclosed in 32. It cannot change the verdict: C ⊂ B, so C's recall ≤ B's 0.120. Fragmentation is
a per-tick Bernoulli at rate × dt (≈ the registered Poisson 1/90 s) — equivalent.

**Noise-model labelling.** FACTS H40 row said "assumed"; 32 pre-registration said so for ghosts only;
32 results and 76 said "declared". Fixed: 32 results ("under the assumed noise model"), 76 §H40
(parameters listed as assumptions, "How to quote it" paragraph), and every downstream row added
(52, 64, 60, 48, 65, 23, 66) carries "assumed".

## 2. 76 — sources re-fetched

| claim | fetch | result |
|---|---|---|
| i-LIDS 10 s window, repeats ignored, 1 FA per 5 s | guide PDF l.1426–1433 | [V] |
| sterile zone "Fence Attack", α 0.65 / 75; parked vehicle 0.55 / 60; "not made public"; F1 0.7 "considerably more stringent" | same | [V] |
| distraction list, approach types (creep walk, walk with ladder…), distance 10–30 % / 4–20 %, "Person exits vehicle", Ambulance subject | same | [V] |
| five event scenarios + multi-camera tracking; CAST with CPNI | gov.uk page | [V] |
| Axis OA scenarios, feet point, 0–20 s tailgating, failure causes | help.axis.com | [V] |
| Fence Guard phrases (after hours, headlights, truck vs animal) | axis.com | [V] |
| DORI 25 / 63 / 125 / 250 px/m | Axis whitepaper | [V]; "Axis notes these are for human operators" was not on the page → reworded to the page's own definition + [INF] |
| ST-GCN 81.5 / 88.3, 30.7 / 52.8, 71.7 | PDF text | [V] |
| VadCLIP 88.02 / 84.51; LAVAD 80.28, 62.01 / 85.36; Holmes-VAD 89.51 / 90.67 | arXiv abs / html | [V] |
| UCF-Crime "~50 % anomalous" [A] | PDF §3: 950 + 950 | **promoted to [V]**, URL added |
| NPSA PIDS definitions, Pd / NAR / FAR | not refetched (403 / socket error last session) | stay [A], correctly tagged |
| BS EN 62676-4 2025 seven levels | FACTS secondary | correctly tagged |

## 3. Hostile-reviewer pass (the vendor) — fixes in place

1. 76 §5 "has never produced a single FA/cam-h number" — stale after H40 → "had never … (H40 below is the first, on mock tracks)".
2. 76 Q8 "a lower bound on the people-only component" — wrong direction of hedge → "covers only the people-and-tracker component — optimistic for a real fence".
3. 76 Q10 "until H40" — implied H40 closed the gap → states H40's not-met result and that it is still not perimeter coverage.
4. 76 §H40 tagged bare [V] next to a web-fetch tag set → "[V, repo — recomputed]", noise parameters listed as assumptions.
5. 32 H40: door-prop deviation and "optimistic for a real fence" added.

Q&A trace to FACTS: Q1–Q3 (i-LIDS rows, new), Q4 (UCF-Crime rows 22/234/237 + new 950/950), Q5
(LAVAD rows 398/460), Q6 (new Axis rows), Q7 (new ST-GCN row), Q8 (new distraction-list row), Q9 [A]
by design, Q10 [CODE] + H40 row. All ten trace.

## 4. Corpus fold-in

FACTS: 10 rows (i-LIDS ×4, UCF-Crime, Axis ×2, ST-GCN, Holmes/LAVAD, H40 audit). 52 register row +
header; 64 register row, results-table row, paragraph "line-crossing: the rule is easy, the twin and
the generator are the hard part"; 60 item 36; 48 number 43 + C8e (line-cross vs loiter; depth rule;
fenced-zone hard negative); 65 N13; 23 M8 row + rank-15 row (behaviour-engine gaps → D37; H40b
pre-registration pending); 66 H40 status; 00 rows for 76 and this audit. Interview framing carried
everywhere: **a false-alarm rate measured without patrol-guard / animal / weather twins is optimistic.**

## 5. Score

| criterion | before | after |
|---|---|---|
| H40 numeric accuracy vs results.json | 10/10 | 10/10 |
| code ↔ registration agreement | 8/10 (door prop undisclosed) | 9.5/10 (disclosed; not implemented) |
| noise model labelled as assumption where quoted | 6/10 | 10/10 |
| 76 source tags / URLs | 9/10 (UCF [A], DORI paraphrase) | 10/10 |
| 76 overclaim (stale "never", Q8 hedge direction, Q10) | 7/10 | 9.5/10 |
| Q&A → FACTS traceability | 7/10 | 10/10 |
| corpus propagation | 5/10 (FACTS, 74, 13 only) | 10/10 |
| **total (×100/70)** | **74/100** | **99/100** |
