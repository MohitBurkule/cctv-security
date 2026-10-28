# Audit of 52 and 53 (2026-09-26, HEAD `cce28af`)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** HOTA 0.434 / 0.539 are pre-parity (now 0.443 / 0.537, AUDIT_M1_PARITY, R41–R43); h14b +0.0121 compared unequal steps (+0.004–0.005 at equal steps, AUDIT_H26, R51).

Method as `AUDIT_48-51.md`: every number checked against the committed source
(`git log`/`git show <hash>`, docs/11–13, docs/15, `32`), prices and formulas
re-fetched. Score = share of checkable claims correct.

## 52 — score 7/10 before, 9.5/10 after

| # | Was | Now | Evidence |
|---|---|---|---|
| 1 | Tests "caller-reported 797", 832 incl. uncommitted file | 832 collected / 810 selected at committed `cce28af` | clean worktree `pytest --collect-only -q` |
| 2 | Gate "~19 rows", "30–39 unverified" | 20 / 29 / 38 rows for 2 / 3 / 4-camera sets | `out/batch_v7/*/check_render.txt`, 10 sets |
| 3 | v6/v7 failure "far-night fails exposure", l.1038 (that is batch_v5) | `cam_02:motion` 72.6 % / 71.6 % frozen, l.1081 / l.1183 | docs/12 |
| 4 | H4 labelled "does epoch truth matter"; 0.219 vs 0.148 as an epoch effect | HSV vs OSNet cross-camera mAP | `32` §H4 |
| 5 | H7 "+0.01" | +0.010–0.011 (2 seeds) | `32` §H7 |
| 6 | H9–H11 one vague row | H9a −0.171 HOTA, night n.s.; H9b rejected; H10 blocked; H11 IR −0.61 | `32` §H9–H11, `4a51207` |
| 7 | Tight GT "in progress, uncommitted" | committed `0213002`, retraining not re-run | `git show 0213002` |
| 8 | Roadmap "from 23 §8" | 23 §10–11 | `23` l.462–494 |
| 9 | Pitch: "the cause was loose box tops"; "HOTA inflated from 0.434 to 0.545" | "one cause"; "inflated to 0.545; correct 0.434"; retrain caveat | `32` §H6, `be9f52a` |
| 10 | H3 "13–30 px" | 13–45 px (15 GT > 30 px), matches FACTS | `32` §H3 |
| 11 | "8 sets × 300 frames × cameras" | 24 camera sequences × 300 | docs/12 |
All 25 cited hashes exist with matching subjects. Evasion 52 techniques
confirmed (`len(evasion.ALL) == 52`).

## 53 — arithmetic re-derived, prices re-fetched

Correct: per-camera GB/day, fleet volumes, hot 72.6 TB / warm 238 TB, ×1.4 raw,
IA/B2/Wasabi monthly costs, IVFPQ 72 B → 7.5 GB, flat 213 GB, halfvec 107 GB,
104 M vectors (40/s × 86 400 × 30), incident 270 MB / ~2 TB/yr. Re-fetched:
B2 $6.95/TB, free egress 3×, $0.01/GB beyond [V]; Wasabi $7.99/TB, no egress/API
fees [V]; FAISS formulas [V]; SemDeDup 50 % and label-error 3.3 % / 6 % match
the abstracts. AWS page did not render prices in fetch; list prices kept.

Fixed: S3 Standard 311 TB is tiered (50 TB × $23 + 261 TB × $22 ≈ $6 890, not
$7 150); FAISS HNSW formula carries an `x` level factor (row is now a lower
bound); dual-rate sub-stream rate (1.0 Mbit/s) stated; the "H4 epoch-aware
truth" claim was wrong and is replaced by H10 "not measurable".

## Consistency sweep

Agree across 52 / FACTS / 42 / 48 / 35: HOTA 0.434 / 0.539 / 0.545, H1
0.152 ± 0.025, CC0 −0.013, realism 6/14 & 3/14. Added to FACTS and 42 (were
only in 52): H7, H9–H11, 0.758 vs 0.577, tight GT 0.781 → 0.884, test count.

For the coordinator (files not owned here):
- `35` l.41, l.96, l.283 and `48` l.307: "600+ tests" — measured 832 collected.
- `docs/11_IMPLEMENTATION_STATUS.md` l.32: "40 techniques" — code and CLAUDE.md say 52.
- Orin NX 18 streams appears only in `48` (l.486, l.593); VLM ratios appear in
  none of the swept files — nothing to reconcile here.
