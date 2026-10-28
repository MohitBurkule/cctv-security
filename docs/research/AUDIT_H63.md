# AUDIT_H63 · Uniformed intruder vs. corroboration mismatch

Audited 2026-09-28 against `out/experiments/h63_uniform_mismatch/results.json`,
`survsim/experiments/uniform_disguise.py`, `uniformed_intruder_arc` in the narrative module,
`tests/test_uniform_disguise.py`, pre-registration in `32` §H63 (commit d411fb2) and the run
write-up (commit f0fd0ea). No GPU, nothing re-run; recomputed from the JSON.

**Score: 100/100** (every headline number matched exactly; no wrong claims found; the doc that
carries the result, `32` §H63, was already accurate and precise — this audit's job was folding
the same numbers into every other place the result is quoted, and filing a follow-up).

## 1. Numbers recomputed (all match)

| claim | recomputed from `results.json` | ok |
|---|---|---|
| (a) role-suppress recall@10 0.027 [0.010, 0.047] | 8/298 = 0.026846, boot95 [0.010033, 0.046827] | ✓ |
| (b) corroboration-mismatch recall@10 0.745 [0.694, 0.794] | 222/298 = 0.744966, boot95 [0.693871, 0.793936] | ✓ |
| (b) twin FA 0.018/cam-h [0.014, 0.024] | 55/3,002 cam-h = 0.018321, garwood95 [0.013802, 0.023847], boot95 [0.013021, 0.024237] | ✓ |
| line-cross baseline C recall@10 0.775 [0.726, 0.822] at 0.375 FA/cam-h | 231/298 = 0.775168, boot95 [0.725744, 0.822148]; 1,111/3,002 = 0.375083 | ✓ |
| (c) (b) + route prior 0.198 at 0.007 FA/cam-h | 59/298 = 0.197987 [0.151515, 0.241611]; 22/3,002 = 0.007328 | ✓ |
| 298 events / 300 recall worlds / 676 clean worlds | `config.n_recall_per_kind` 100 × 3 kinds = 300 worlds, 298 scored events; `n_clean` 676 | ✓ |
| decision: not met, 2/3 | `decision.met` false; `b_recall_ge_0.8` false; `b_twin_fa_le_0.05` true; `a_recall_le_0.1` true → 2 of 3 sub-criteria hold | ✓ |

Position-keyed and actor-aware recall are identical in every arm (`recall.*.pos.recall ==
recall.*.actor.recall`) because H54's noise model injects no ID switches, so there is no
swapped-label case for position-keyed scoring to recover that actor-aware scoring would miss
(H59's distinction does not apply here).

## 2. Registration-error handling checked, not re-scored

The pre-registered bar for arm (b) was recall@10 ≥ 0.8. The recomputed line-cross baseline C —
the *unmodified* rule with no role logic at all — only reaches 0.775 on these same worlds. A
bar above the best the underlying rule can do on its own worlds cannot be met by a strictly
more conservative arm (b only *removes* alarms relative to C, it never adds one), so 0.8 was
unreachable by construction. `32` §H63 already states this in exactly these terms — "The
pre-registered absolute 0.8 bar was above C's own ceiling — a registration error, reported, not
re-scored" — and the decision block correctly reports `met: false` rather than silently raising
or lowering the bar to make it pass. No change needed; this audit confirms the framing is
correct and leaves the verdict as registered.

## 3. Caveats checked

* **"Time leg never fires."** The roster model has every guard/worker twin on shift for the
  whole world (`h54_config` reused verbatim; no schedule). So arm (b)'s roster/on-shift check
  never has an off-shift case to reject, and the badge/RF corroboration windows (±15 s, ≤ 8 m)
  do all the discriminating work in this run. Stated in `32` §H63 caveats and in `66`'s H63
  entry; now also the subject of the new H63b backlog item (§4).
* **Role-classifier assumption.** `config.role` = `p_guard_given_uniform: 0.95`,
  `p_guard_given_other: 0.02`, drawn per alarmed track — an explicit simulated assumption, not a
  measured classifier, stated in the pre-registration's `role model: ASSUMPTION` line and in
  `32`'s results table caveats.
* **Position-keyed = actor-aware.** Confirmed in §1 above; the reason (H54's noise model has no
  ID switches) is stated in `32` §H63 and is now also repeated in FACTS/60/65v2/78 wherever the
  numbers are quoted, so a reader hitting any of them gets the same caveat.

## 4. Fold-in

* `FACTS_VERIFIED.md` H63 row — already correct, no edit needed.
* `docs/research/60_ONE_PAGE_CHEAT_SHEET.md` — item 14 (MOTSynth like-for-like) replaced with the
  H63 result; the MOTSynth number is still available via `docs/13`/70 and was the weakest of the
  40 (a pure external anchor with no product tie), so nothing load-bearing was lost. Still 40
  items.
  0.745 [0.694, 0.794] / 96 % / 0.018 numbers inline instead of only pointing at `99`.
* `removed-vendor-doc.md` §1.5 ([vendor product]) — one sentence added tying H63
  to [vendor product]'s multi-sensor-fusion pitch: corroboration, not appearance, is what catches a
  uniformed intruder.
  full numeric answer); no change needed.
* `docs/research/99_QA_HOMOGRAPHY_ANOMALY_UNIFORM.md` §3 (Q3) — already carries the exact
  numbers; no change needed.
* `docs/research/100_INFILTRATION_PLAYBOOK.md` — the H63 table row already carries the exact
  numbers; no change needed.
* `docs/research/66_HYPOTHESIS_BACKLOG.md` — H63 entry marked done (already was); new backlog
  item **H63b** filed: rostered-hours realism (so the time leg can actually fire) + a
  role-classifier error-rate sweep, not registered pending a schedule model on H54's worlds.
* `docs/research/AUDIT_LEDGER.md` — row added for this audit.

Neither `docs/research/demo/` nor `tools/demo_reel_v2.py` were touched (owned by X170).

Both `tests/test_docs_retired_claims.py` and `tests/test_docs_numbers_in_facts.py` pass after
these edits.
