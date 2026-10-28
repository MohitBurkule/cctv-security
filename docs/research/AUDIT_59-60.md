# AUDIT 59–60 · explainability/assurance dossier and last-hour cheat sheet (2026-09-27)

Method follows `AUDIT_55-56.md`: every [INF]/memory item in `59` re-fetched from a
primary source where one could be reached; 10 further claims spot-checked
against their sources; the worked operator-load number re-derived; `60`
checked number-by-number against `FACTS_VERIFIED.md`. No engine/GPU. Web search
was unavailable (session quota), so sources were fetched directly (curl /
arXiv export / Crossref).

**Score: 59 — 10/10 spot-checked claims correct as written; of 4 [INF]/memory
items, 1 upgraded to [F] (NeurIPS), 1 clarified (hash chain is not RFC 6962's;
§2.1 leaf/node hashing added as [F]), 1 partly sourced (CAE: bibliographic
record only), 1 still unverifiable (GSN v3 element list — PDF download reset
by scsc.uk). Worked arithmetic reproduces. One block superseded by later data
(the §9 loiter case, round 1 → round 2) and rewritten. 60 — every number
found in FACTS; one line (H12 dwell_25 recall 0.900) now misleading and
replaced; realism line restored.**

## 59 · [INF] / memory items

| Claim | Source | Verdict |
|---|---|---|
| Adebayo et al. 2018 venue = NeurIPS 2018 | papers.nips.cc 2018 proceedings page (title "Sanity Checks for Saliency Maps"); arXiv abs quote re-read | **Confirmed**; tag changed to [F] |
| Hash chain `h_i = SHA-256(h_{i−1} ‖ e_i)` | RFC 6962 §2.1 (datatracker, fetched) | RFC 6962 defines a **Merkle tree**, not a linear chain (MTH leaf `SHA-256(0x00‖d)`, node `SHA-256(0x01‖l‖r)`). The chain stays [INF, standard construction]; 59 now says it is not from RFC 6962 and adds §2.1 as [F]. Both RFC quotes in 59 verified verbatim |
| GSN v3 elements (Goal, Strategy, Solution, Context, Assumption, Justification) | scsc.uk/gsn reachable; v3 PDF (`/publications/download?ref=141&stream=1`) reset connection twice; goalstructuringnotation.info unreachable | **Not verifiable**; stays [INF]. Added secondary (Wikipedia): York origin, Community Standard 2011 |
| CAE, Adelard, Bloomfield–Bishop | Crossref + Semantic Scholar: *Safety and Assurance Cases: Past, Present and Possible Future — an Adelard Perspective*, Bloomfield & Bishop, SSS 2010, doi 10.1007/978-1-84996-086-1_4; text closed-access | **Paper exists as cited**; its content (three elements, nuclear/defence use) not read — stays [INF]. Added as source 10 |

## 59 · spot checks (10)

| # | Claim | Source | Verdict |
|---|---|---|---|
| 1 | Adebayo quote "independent both of the model and of the data generating process" | arXiv 1810.03292 abs | Correct |
| 2 | TCAV ICML 2018; "human-friendly concepts" | arXiv 1711.11279 (journal-ref ICML 2018) | Correct |
| 3 | Model cards: 9 authors, FAT* 2019, both quotes (Fitzpatrick; "context in which models are intended…") | arXiv 1810.03993, doi 10.1145/3287560.3287596 | Correct |
| 4 | Datasheets: CACM Dec 2021, authors, "motivation, composition, collection process, recommended uses" | arXiv 1803.09010 (comment "Published in CACM in December, 2021") | Correct |
| 5 | AMLAS Version 1, February 2021; "comprises a set of safety case patterns…" | arXiv 2102.01564 PDF | Correct |
| 6 | AMLAS six stage names | same PDF (Stages 1–6: Scoping, Requirements, Data Management, Model Learning, Model Verification, Model Deployment) | Correct |
| 7 | AMLAS "relevance, completeness, accuracy and balance"; "sufficiently independent from the development activities" | same PDF, verbatim | Correct |
| 8 | BS 10008-1:2020 published 31 May 2020, current; "demonstrably trustworthy about its authenticity and integrity" | BSI Knowledge product page (publishedAt 2020-05-31, validity current) | Correct |
| 9 | BS 10008:2008 withdrawn 8 Dec 2014 | BSI Knowledge (Published 30 Nov 2008 • Withdrawn 8 Dec 2014) | Correct |
| 10 | Commit hashes: 98b7c03 (H12–H14 pre-reg), 0c0976f (h58 pre-reg), 9c87424 (CC0 + `commercial_ml_ok`), 1fd38df (mask decode), 92e1e97 (1.70 m fix) | `git show` | Correct |

## 59 · worked operator-load number

Formula (51): U = C · B · t / 3600.

* As written (round 1): 40 × 2.92 = 116.8 cues/h; × 30 s = 3,504 s; / 3,600 = **0.973** → "≈ 0.97" **reproduces** (0.972 with the unrounded 2.915).
* With the round-2 rate that FACTS now carries (3.745 FA/cam-h, `44e34f5`): 40 × 3.745 = 149.8; × 30 = 4,494 s; / 3,600 = **1.248 ≈ 1.25 operators**. 59 now quotes this, with the round-1 derivation kept in brackets.

## 59 · corrections made (`40fea72`)

1. §4.1 GSN/CAE tags made precise; Bloomfield–Bishop cited.
2. §6.2 hash chain explicitly not RFC 6962; RFC 6962 §2.1 leaf/node hashing added [F].
3. §1.1 and source 7: NeurIPS venue now confirmed, not memory.
4. §9 worked case, "What this case supports", operator-load check and Q4 moved from h58 round 1 (2.915 FA/cam-h, recall 0.867, 2.06×, 2,915× budget, recall@10 0.472) to round 2 (3.745 [3.676, 3.815], actor-aware recall 0.831 [0.792, 0.869], precision 0.326, 1.60×, ~3,700× budget, recall@10 0.097, twin floor ~830× at r = 0.831; dwell_25 actor-aware recall 0.367).

## 60 · number check (`46ebeba`)

All 25 numbers and the pitch figures found verbatim in `FACTS_VERIFIED.md`
(formulas are from `55`, audited in `AUDIT_55-56.md`). Changes:
* #20 "H12 recall @30 s dwell_25 0.900; at 10 s 0.125" is window-only scoring;
  replaced with the round-2 actor-aware line.
* Added #26 twin floor 1.008 [0.973, 1.045] and #27 realism 6/14 day · 3/14 night (now a FACTS row).
* "Things not to say" gains dwell_25 0.900 and "photoreal".

## FACTS additions (`00cd138`)

Rows for h58 round 2 (headline + baselines), h58 round 1 marked superseded
(`070cf97`; round 2 was pending after `473ace3` and landed in `44e34f5`), and
realism 6/14 · 3/14 (table in `docs/15`, measured in `a9ec608`; `52` §4.3;
12/14 correction `d9d1c5c`). The H12 recall row now carries a pointer that its
dwell recalls are window-only.
