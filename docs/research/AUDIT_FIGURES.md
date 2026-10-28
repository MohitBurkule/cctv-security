# AUDIT_FIGURES — figures produced 2026-09-27

Every `fig_h*.png`, `fig_box_aspect.png` and `fig_tracking_stats.png` in
`docs/research/figures/` checked for: existence, a reference from `32`'s own
H section, a reference from `64` (Appendix A) or `13` (`docs/13_BASELINES.md`),
on-figure numbers matching `FACTS_VERIFIED.md`, and no retired claim form in
a title or caption (`RETIRED_CLAIMS.md`, `tests/test_docs_retired_claims.py`).

| figure | referenced from (before / after) | numbers verified against FACTS | fixed |
|---|---|---|---|
| fig_h22_h33.png | 64 Fig. 6 (already) | not re-checked (pre-existing Fig. 6, out of today's new set) | none |
| fig_h32.png | 32 §H32 (already); 64 body "Figure 7" but **not** in Appendix A | vis hold 2/13 (tune 9/13), thermal hold 3/13 (tune 10/13), `cctv_night_ir` vis hold R 0.37 — matches FACTS H32a row | added Figure 7 description to 64 Appendix A |
| fig_h34.png | 32 §H34 (already) / 13 (already, §H34 table row) | PSI/z_cal/embedding drift curves — qualitative, no numeric label to check; row numbers (PSI 1,440 etc.) live in 13's table, unchanged | none needed |
| fig_h39.png | 75 (already) / 32 §H39 (missing) | A0 ~0.2 m, A2 ~57 m rising with range, A2f (datasheet f) ~1–5 m — matches FACTS H39 row | added `Figure:` line to 32 §H39 results |
| fig_h40.png | 32 §H40 (already) | FA 70.96/66.48/5.11/4.20, recall 0.945→0.100 — matches | none |
| fig_h40b.png | 32 §H40b (already) | C clean FA ≈ 0, recall 0.782/0.852/0.899 — matches | none |
| fig_h42.png | 32 §H42 (already) | pooled 5.033/0.894, CRC 2.1–2.2/0.778–0.783 — matches | none |
| fig_h43.png | 32 §H43 (already) | recovery 0.415/0.424, per-ckpt 0.118–0.679 — matches | none |
| fig_h43b.png | 32 §H43b (already) | recovery 0.415 (P1) vs 0.366 (Q1) — matches | none |
| fig_h43c.png | 32 §H43c (already) | per-ckpt recovery 0.266/0.322/0.561/0.615/0.429, mean 0.439 — matches | none |
| fig_h43d.png | 32 §H43d (already) | pooled 0.439→0.374, per-ckpt incl. −0.500 on dose300_s1 — matches exactly | none |
| fig_h45.png | 32 §H45 (already) | A1 0.511/0.586, pooled 0.324/0.504, conformal 0.571/0.621, utilisation 0.88→0.40 — matches | none |
| fig_h46.png | 32 §H46 (already) | day argmax w=4 +0.0421, mot20 +0.0338, night arm negative CI-spans-0 — matches | none |
| fig_h46b.png | 32 §H46b (already) / 13 (already) | day argmax w=16 +0.0613, mot20 w=8 +0.0486, night +0.047 CI touches 0 — matches | none |
| fig_h47.png | 32 §H47 (already) | crowd_cover −0.201/−0.166, wall_hugging −0.054, slow +0.036 — matches | none |
| fig_h51.png | 32 §H51 (already) | real-only 0.4911, +0.0042/+0.0051, Holm p 0.0039 — matches | none |
| fig_h52.png | 32 §H52 (already) | dose300−shuf300 +0.0077 Holm p 0.0098, mask300−dose0 +0.0036 — matches | none |
| fig_h53.png | 32 §H53 (already) | twin FA 0.488→0.0047 (99.0% removed), recall 0.782→0.758 — matches | none |
| fig_h54.png | 32 §H54 (already) | 99.1% removal, tailgater 0.056 (C+abc) / 0.685 (C+abcg) — matches | none |
| fig_h56.png | 32 §H56 (already) | acquire@3s 0.901/0.802/0.727 (1 PTZ), missed-second 0.369 vs 0.057 — matches | none |
| fig_h59.png | 32 §H59 (already) | 99.1% removal both rates, recall loss +0.002, tailgater collapse 0.769→0.10 — matches | none |
| fig_h61.png | 32 §H61 (already) | real-only 0.4911, sil300 0.4891, true labels 0.4962 — matches | none |
| fig_h33b.png | 32 §H33b (already) | fixed-B certified point 2.187/0.783 (cap1 2.223/0.787 shown in h33c) — matches | none |
| fig_h33c.png | 32 §H33c (already) | cap1 2.223 [2.178,2.274], cap2 1.908/0.773 — matches | none |
| fig_box_aspect.png | 13 (already, §Box aspect) | pooled ratio 1.138 [1.062,1.213], per-bin 1.221/1.004/1.119 — matches exactly | none |
| fig_tracking_stats.png | 73 §tracking (already); **not** in 32/64/13 | qualitative distribution plot, no single number to check | added companion reference next to fig_box_aspect in 13 |

## Cross-cutting fixes made

1. **`docs/research/64_TECHNICAL_REPORT_SIM2REAL_AND_ALARMS.md`** — Appendix A
   silently stopped at Figure 6 even though the body cites a "Figure 7"
   (`fig_h32.png`, H32 night-realism paragraph, §4.2). Added a one-paragraph
   Figure 7 entry, plus a pointer sentence explaining that the remaining
   `fig_h*.png` files are single-hypothesis diagnostics indexed elsewhere
   (not part of this report's numbered series), so a reader isn't left
   assuming they were forgotten.
2. **`docs/13_BASELINES.md`** — appended a "Figures for the H-numbers above"
   index (one line per PNG) covering every figure that was referenced from
   `32` but had no link from `64` or `13`: h33b, h33c, h34, h39, h40, h40b,
   h42, h43/b/c/d, h45, h46/b, h47, h51–h54, h56, h59, h61, and the
   box-aspect/tracking-stats pair.
3. **`docs/research/32_EXPERIMENTS_LOG.md`** — added a `Figure:` line to the
   H39 results section (previously the figure existed and was cited from
   `75` only, not from `32` itself).
   to the audit table.

## Not touched / out of scope

- `survsim/`, `out/`, docs 03/58/66/71, and every other H section in `32`
  beyond the single added `Figure:` line for H39 — left untouched per the
  task's boundary.
- No figure needed re-rendering: every on-figure number checked against
  `FACTS_VERIFIED.md` matched; the defects found were missing
  cross-references, not wrong plots.
- `/tmp` is ~12 GB, dominated by `/tmp/claude-1000` (live session
  scratchpads for this and other agent sessions) and several running
  simulator/editor temp dirs (`survsim_render_editor`, `mongo-mem-*`,
  `env_*`). None of it is this task's output, and deleting another live
  session's scratch directory risks breaking a concurrent run, so it was
  left alone and is flagged here rather than force-cleaned.

## Tests

`pytest -q tests/test_docs_retired_claims.py tests/test_docs_numbers_in_facts.py`
— both pass (6 + 4 tests) after the edits above.
