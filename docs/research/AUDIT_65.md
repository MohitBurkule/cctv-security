# AUDIT_65 · Dress rehearsal (65)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** 65 v1 is superseded by 65 v2 and AUDIT_65_V2. The N-table values listed as matching FACTS here include forms since retired: 0.0121 (R51), HOTA 0.434 (R41), HOTA +0.0103 (R53), 3/14 night (R02), 'A1 ships' (R48).

Audited 2026-09-27 against `e0870e6` (65 as written); fixes in `2df47ab`. Method as AUDIT_64:
every number in the N-table and in every answer matched against `FACTS_VERIFIED.md` (and `32`, `52`,
`55`, `58` §7.2 where FACTS is silent); the six derivations recomputed in Python (`.venv`);
SAPIENT names checked against `37` §5; retired numbers against `AUDIT_STALENESS_SWEEP.md`;
every commit hash checked with `git cat-file -t`.

## 1. Derivations (recomputed)

| item | 65 says | recomputed | result |
|---|---|---|---|
| F1 Kalman | x⁻ [11, 1], P⁻ [[5,1],[1,1]], S 6, K [5/6, 1/6], x [11.833, 1.167], P [[0.833, 0.167],[0.167, 0.833]] | same | match |
| F2 Hungarian | greedy 6, optimal 5 (r1→c2, r2→c1, r3→c3) | min over 6 permutations = 5; greedy 0+2+4 = 6 | match; O(n⁴)/O(n³) matches `55` §5 |
| F3 HOTA toy | MOTA 0.333, IDF1 0.500, DetA 0.714, AssA 0.340, HOTA 0.493 | √(5/7 × 1.7/5) = 0.4928; test asserts 0.4928 | match |
| F4 focal | 100× at p_t 0.9, 4× at 0.5 | 0.105 → 0.00105 | match, but **α not evaluated** — fixed: α_t = 0.75 for a negative → 0.00079 (~133×); `55`'s 0.00026 is α_t = 0.25 |
| F5 pinhole/DORI | f_x 1371, 47 px @ 50 m, 11 m recognise, 55 m detect, 117 m @ 20 px | 1371.0, 46.6, 10.97, 54.8, 116.5 | match |
| F6 rule of three / seeds | 3,000 cam-h; 25 per arm | ln 20 / 0.001 = 2,996; 24.5 | match. H12 "sized from this formula": prereg `32` l.784–808 (≥ 3,000, rule of three) supports it |

## 2. Numbers

N1, N3–N10 and D1–D10, B1–B3 match FACTS_VERIFIED exactly (0.0121 [0.0111, 0.0130], 0.0095, 0.4862,
2.915 [2.854, 2.977], 0.825 [0.789, 0.862], 0.329, 1.008 [0.973, 1.045], HOTA +0.0103 [+0.0008, +0.0197],
DetA +0.0342, AssA −0.0051, −0.0005 [−0.0012, +0.0001] p 0.31, +0.0092 / +0.0169, 0.459, 9/9, 0.876–0.932,
0.879–0.914, 0.652 vs 0.665, 6/14, 3/14, 0.152 ± 0.025, 0.434, 3,002, 4,500–87,000×, H3 0.021/0.405/0.629,
ρ −0.60, 0.367, 0.0006, 18 × 1080p30). System-design arithmetic (0.1 × 40 = 4/h, 96/day; 0.01 × 5 × 3,600 = 180,
1,800×; 3/30 = 0.1) recomputed, correct.

Errors and framing faults found:

| # | where | problem | fix |
|---|---|---|---|
| 1 | D10 | "validated … against TrackEval on real MOT20" — **false**: `52` §5 lists TrackEval parity as *not done* (roadmap M1) | rewritten; TrackEval parity added to the retired list |
| 2 | F6 follow-up | "It is paired" — h14b's p 0.0079 is an exact **unpaired** permutation (2/252); a paired n = 5 test floors at 0.0625 | corrected, with Δ/σ ≈ 20 arithmetic |
| 3 | D8 | "quarantined … not used for any reported result" — false: H1–H8 and 0.758 used batch_v4/v6 MetaHuman | rewritten to `52`'s position (internal engineering evidence; no product model trained/selected/benchmarked; no MetaHuman renders since CC0 default; custom Epic terms needed) |
| 4 | D6 | "can't be fully reconciled" — `52` §4 does explain it | replaced with batch_v6 (MetaHuman, 5 scenes incl. night/far, 1,258 images, label bug) vs batch_v7 (CC0, 2 day scenes, 370 images, no bug); cast, scenes and bug differ at once, no single cause isolated |
| 5 | N2, P2, D3 | "zone context −21 % FA" read as vs A1; FACTS: arm D −20.7 % vs **arm B** (GBM track-only), P8 ≥ 25 % **failed**, needs per-site profile | qualified in N2 and P2 (D3 left short; N2 carries the caveat) |
| 6 | §2 step 7, P6 | SAPIENT "capability reduced" state does not exist in `37` | now `StatusReport` `EXTERNAL_FAULT` / `NOT_DETECTING`, shrunk `coverage`, `PD`/`FAR`; added `Alert`, `Task`/`TaskAck` (`look_at`) |
| 7 | D1, D4, D5 | own-reasoning claims unmarked | marked **[derived]** with arithmetic: 0.0121/0.4862 ≈ 2.5 %; 0.825 × 1.008 = 0.83, 2.915/0.83 = 3.5×; 1.008/0.001 ≈ 1,000× = 10³ |
| 8 | header | answers quote numbers absent from N1–N10 (H3, H13, 0.367, 0.0006, 0.290/0.266, 0.758), against the doc's own rule | N11 "supporting" row added, all FACTS-sourced |
| 9 | retired line | missing H1 two-seed 0.161, synth+real 0.475, H14 +0.0089; no rule for "before" values used in D10/B2 | added, with the staleness-sweep rule |

## 3. Commits

All 10 hashes in 65 resolve to commits (`471030b 549f433 5e5f53d 829feb4 8c3b03b 94145fa a9ec608 b6c735e bcbe9d2 be9f52a`);
N11 adds `d0d00ac 9dea4f9 44e34f5 19afe95`, all cited in FACTS. `b6c735e` is the H15 results commit (`64` l.379).

## 4. Score

| criterion | before | after |
|---|---|---|
| numeric accuracy vs FACTS | 9/10 | 10/10 |
| derivations | 9/10 (α unused) | 10/10 |
| claim truth (TrackEval, paired, D8) | 5/10 | 10/10 |
| reconciliation (D6) | 5/10 | 9.5/10 |
| derived-vs-measured tagging | 6/10 | 10/10 |
| SAPIENT fidelity to 37 | 7/10 | 10/10 |
| retired-number discipline | 8/10 | 10/10 |
| provenance (hashes) | 10/10 | 10/10 |
| **total (×1.25)** | **74/100** | **99/100** |
