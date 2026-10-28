# AUDIT_NARRATIVE_POST_H26 · The rewritten sim-to-real story (commit `e299c88`)

Audited 2026-09-27 as a hostile the vendor ML lead. Scope: `52` §5b and its nine mirrors
(42 pitch, 46 story 24, 60 section B, 64 §4 intro, 68 Q18, 77 #2, 78 opener/[vendor product], 79 Q26,
80 figure 2), plus the H16/H17 unequal-step confound that AUDIT_H26 §4 left caveated only
beside the headline. Every number was checked against `FACTS_VERIFIED.md`; H51/H47 status
against the working tree (`out/experiments/h51_equal_steps` training live, `h47_evasion`
rendering, uncommitted runner) — so "running" / "in progress" is accurate and no doc gives
either a result.

## 1. Checks

| # | claim | source | result |
|---|---|---|---|
| 1 | H1 0.276 → 0.152 ± 0.025, 3 seeds | FACTS H1 row | match |
| 2 | H19 synthetic-only far 0.000, zero-shot 0.613, +60 real → 0.817 | FACTS H19 | match |
| 3 | H26 real-only 0.4911; +0.0041 [+0.0012, +0.0071]; +0.0045 [+0.0015, +0.0074] | FACTS H26 | match |
| 4 | H26 600 +0.0015, 1,000 −0.0003; p 0.048 / 0.040; none Holm | FACTS H26 | match |
| 5 | real-only gains +0.0049 from extra steps; ~228 vs 300–450 iterations | FACTS H26 / h14b | match |
| 6 | h14b "5 seeds, Holm-significant" (46 story 24 S) | FACTS h14b | match |
| 7 | batch_v8 gate 9/9, tightness IoU 0.876–0.932 | FACTS batch_v8 (`94145fa`) | match |
| 8 | H40b arm C clean FA 0; twins patrol 0.389, maintenance 0.099 | FACTS H40b (`d51e5f9`) | match |
| 9 | H21 2/5 GBM seeds clear the bar | FACTS H21 (`bd4c028`) | match |
| 10 | H23 R − F −0.380 [−0.896, +0.203] | FACTS H23 | match |
| 11 | H42 θ selection spans 2.118 (2.915–5.033) | FACTS H42 (`0b4f5d9`) | match |
| 12 | H32 lowlight 9/13 tune → 2/13 hold-out | FACTS H32a | match |
| 13 | H20 MOT20 +0.021 [−0.047, +0.097], 15 ids | FACTS H20 | match |
| 14 | H17 AssA −0.0051 n.s.; H24 ΔAssA +0.0139, IDSW −5.6 | FACTS H17/H24 | match |
| 15 | H51 = 10 seeds, running; H37 pre-registered, not run; H47 no number | 66, working tree | match |
| 16 | "reliably buys" includes H37 and H47 (52, 60 #11, 64 §4, 79 Q26) | nothing measured | **overclaim** → moved to "not yet measured, no number" in all four |
| 17 | "reliably buys" items carry an H/commit (brief requirement) | — | **missing** → 52 now cites `94145fa`, `d51e5f9`, `bd4c028`, `0b4f5d9`, AUDIT_H40B `f45cf1b`; 46/60/64/79 name batch_v8 / H40b / H21–H42 |
| 18 | identities across outfits, true calibration, act-time alarm scoring as a "buy" | no measured gain | **overclaim** → 52 states them as capabilities, not a measured gain |
| 19 | h14b gain "came mostly from" / "came from" extra steps (68 Q18, 79 Q26) | AUDIT_H26 §1: decomposition not clean; a third to a half survives | **overclaim** → "compared unequal steps; a third to a half survives at equal steps" |
| 20 | pitch: "the experiment where I **proved** that" (42, 52, 79; 68 paraphrase) | H26 is n.s.; H51 open | **overclaim + rehearsed** (verbatim ×3) → one plainer line everywhere: "H26 is the experiment that made me retract my own earlier number" |
| 21 | 80: h14b real-only "trained half as long" | ~228 vs 300 / 450 | **imprecise** → iterations stated |
| 22 | 46 story 24 "0 at 1,000" | −0.0003 | acceptable; reworded "nothing at 1,000" |
| 23 | 46 follow-up "ground truth, twins and rule variance" unsourced | — | **vague** → batch_v8 / H40b / H21/H23/H42 named |
| 24 | 64 evidence table "+300 (YOLOv8n) +0.0095" with no equal-step value | FACTS H26 | **stale** → +0.0045 equal-step added beside it |
| 25 | H16 +0.0092 / +0.0169 and H17 HOTA +0.0103 quoted as current gains | same unequal-step arms as h14b | **confound unflagged** → §2 |
| 26 | consistency of the headline "+0.004–0.005 AP at equal steps, n.s. after Holm" across the 10 places | diffed | match (all ten) |
| 27 | retraction framed as a strength without sounding rehearsed | — | 46/68/78/79 each say it once in plain words; after #20 no line is repeated verbatim outside 42/52/68/79's labelled "pitch line" |

**Score: 17 / 27 (63 %)** — every number matched FACTS (15/15 numeric checks plus #26, #27 wording
checks after fix), but the *argument* overreached in 10 places: unmeasured items sold as reliable
value, a decomposition stated more cleanly than AUDIT_H26 allows, and "proved" on an n.s. result.

## 2. H16 / H17 confound (AUDIT_H26 §4 follow-through)

Both reuse the h14b design: mix_0 is the H14 real-only arm (6 epochs on 300 images, ~228
iterations) vs mix_100 300 / mix_300 450 iterations. H16 (YOLO26n +0.0092 / +0.0169) has no
FACTS row; H17's FACTS row now carries the caveat. One-line notes appended to 32 §H16 results
and §H17 results. Registry: **R52** (H16 values) and **R53** (H17 HOTA +0.0103), each firing on
a line that lacks `unequal` / `equal-step` / `H26`. Hits fixed: 52 register H16/H17 rows; 64
abstract, register H16/H17, §4.1 H16 (2 lines), §4.3 H17, §4 intro, evidence table (3 rows),
conclusion; 68 Q-HOTA; 79 parity answer and Q26; 60 #12; 23; 48 #37; 65 N4/N6/story; 73 table and
Q1; 78 tracking bullet; FACTS H17. `tests/test_docs_retired_claims.py` passes (5/5).

## 3. Housekeeping

* 60: 39 numbers (≤ 40), header "39 numbers" correct; HEAD stamp was `ff76386` (pre-H26) →
  `e299c88`.
* FACTS recounted by script: 17 `| Fact |` tables, **324** data rows (header said 321 — three
  rows added since without a recount), 17 snippet-only; header and footer updated.
