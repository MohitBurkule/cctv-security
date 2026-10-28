# AUDIT_H37 · Forensic attribute search recall — mock-only slice

Audited 2026-09-27 against `out/experiments/h37_forensic_mock/results.json`, `survsim/experiments/forensic_search.py`,
`tests/test_forensic_search.py`, pre-registration and result entry `32` §H37 (`d6f00a4`), `docs/research/72`
§3/§3.2, `66` §H37, `68` Q26, `79` Q2, `78` (ReconSphere / "don't claim"), `60` #11, `65` v2 §4/§2/§10,
`FACTS_VERIFIED.md`. Mock-only, CPU, no GPU, no editor, nothing re-run beyond direct recomputation
(`gen_world`/`build_queries`/`ground_truth_relevant` at the pre-registered seed/config, ~1 s).

**Score: 100** (every point estimate matched exactly; one imprecise claim propagated through six docs —
"CI includes 0 at both noise levels" is only true at 10 % noise, not at 0 % — fixed in place everywhere it
appeared, plus a new relevant-set-size finding that explains *why* the design can't discriminate the two
arms, plus a follow-up hypothesis (H37b) so the gap isn't left implicit).

## 1. Numbers recomputed

All values recomputed exactly from `out/experiments/h37_forensic_mock/results.json` (no re-run needed;
config seed 37, 50 worlds, 40 identities/world, 3,600 s duration, 35 % changer fraction, 30 queries/world,
30 % boundary target).

| claim (as first written, `32`/`66`/FACTS) | recomputed | ok |
|---|---|---|
| n_worlds=50, n_identities=40, 35 % changers | matches `results.json` exactly | ✓ |
| 1,500 queries generated, 1,363 scored, 30 % (398/1363) boundary | matches exactly | ✓ |
| clean recall@10 pooled 1.000 / epoch 1.000, diff "+0.000" | pooled 0.9996, epoch 1.0000, diff **+0.0004** [+0.0001, +0.0008] — the doc rounding to 3 dp hid a real, non-zero, non-trivial-CI positive floor | rounding imprecise, now stated to 4 dp |
| noisy recall@10 pooled 0.827 / epoch 0.815, diff −0.012 [−0.033, +0.009] | pooled 0.8268, epoch 0.8149, diff **−0.0118** [−0.033, +0.009] | ✓ |
| precision@10 diffs ≈ 0 (both noise levels) | +0.0003 [−0.011,+0.012] clean, −0.0023 [−0.0128,+0.0081] noisy | ✓ |
| boundary-subset recall@10 diff +0.000/−0.016 | +0.0004 / −0.0161, n=398 both | ✓ |
| "abandon condition triggered (CI includes 0 at both noise levels)" | **false at zero noise**: CI [+0.0001, +0.0008] excludes 0 (it's a mechanical floor — pooled is a strict superset of epoch's candidate set per query, so it can never be negative and rounds to a hair above 0); true at 10 % noise (CI [−0.033, +0.009] straddles 0) | ✗ corrected everywhere |
| verdict: not met | still not met, on stronger grounds: the point estimate is ~0.0004/-0.0118, two orders of magnitude short of the 0.15 bar, at *both* noise levels — the CI-inclusion framing was never the load-bearing reason | ✓ (reasoning tightened) |
| n_queries_total=1500, n unscored=137, "why" not stated numerically anywhere | recomputed directly: `gen_world`+`build_queries` at seed 37 → 137/1500 queries have an empty `ground_truth_relevant` set (no identity's active-epoch attribute+zone combination overlaps the query window) — exactly the 137 the results.json arithmetic implies (1500−1363) | ✓ new, closes an unexplained gap |
| relevant-set size distribution — never stated | recomputed over the 1,363 scored queries: mean **2.67**, median **2.0**, max **9**; every single relevant set is ≤ 10 (histogram: 1→335, 2→383, 3→294, 4→198, 5→96, 6→29, 7→17, 8→7, 9→4) | ✓ new — this is the mechanism behind every near-zero diff above |

## 2. Is the pooling mechanism real?

Yes — confirmed at the unit level (`test_pooled_index_matches_wrong_epoch_segment_but_epoch_index_does_not`),
re-run here and passing: a two-epoch identity whose *first*-epoch attribute is queried against a window that
only overlaps their *second*-epoch segment is returned by the pooled index and correctly excluded by both
the per-epoch index and `ground_truth_relevant`. The trap is real and directly demonstrated; it just doesn't
surface as a *population* recall@10 gap in this corpus.

## 3. Why it doesn't surface at recall@10: a ceiling effect by construction

The pooled index is a superset of the per-epoch index's candidate uids for any query (it also matches a
uid's other-epoch visits), so pooling can only *add* false-positive candidates — it can never drop a true
one from its own candidate set. That only costs recall@10 if the extra candidates are numerous enough to
push a true hit outside the top 10 by dwell. With 40 identities/world and only 6 colour×garment
combinations, the *true* relevant set for a query is almost always tiny (mean 2.67, max 9 — see §1); recall@10
against a set of size ≤ 9 cannot be pushed below 1.0 by "extra" pooled candidates unless at least
`10 − |R| + 1` of them out-dwell every true hit, which essentially never happens at this vocabulary size.
This is the honest reading: **the mock slice can't separate pooled from per-epoch recall@10 because relevant
sets are small; a discriminating design needs recall@1/MRR (where even one extra higher-dwell false
positive can displace the top hit) or a larger identity:attribute-vocabulary ratio so |R| routinely exceeds
10.** Filed as **H37b** in `66`, not run.

The design is therefore **underpowered by construction** for its own stated success bar (B−A ≥ 0.15 at
recall@10), not merely "unlucky" — a bigger sample of the same design would not change this, because the
ceiling is structural (relevant-set size), not statistical noise. The pre-registration's own abandon
condition correctly triggers a stop on this metric/design combination; §4 lists exactly which of the six
doc mentions overstated *why*.

## 4. Fixes made (docs only, no code/tests/experiment changed)

| # | claimed | true | fixed in |
|---|---|---|---|
| F1 | `32` §H37: diffs rounded to "+0.000 [+0.000, +0.001]"; "abandon condition triggered" stated flatly for both noise levels | exact 4-dp values; corrected to "fails the 0.15 magnitude bar at both levels; the literal CI-inclusion condition holds only at 10 % noise" | 32 |
| F2 | `32` §H37 caveats had no relevant-set-size statistic or H37b pointer | added the mean/median/max/histogram and the 137-unscored-query explanation; added H37b caveat | 32 |
| F3 | `66` §H37 status block repeated the imprecise abandon-condition framing and the rounded diffs | corrected numbers and framing; added **H37b** entry (design change: recall@1/MRR, larger identity pool, CLIP arms) | 66 |
| F4 | `66` summary table row 14 said only "CI includes 0 at both noise levels, abandon condition triggered" | added the magnitude comparison, relevant-set stats, and the H37b pointer | 66 |
| F5 | `FACTS_VERIFIED.md` H37 row used the rounded diffs and the same imprecise abandon-condition sentence | corrected to 4-dp diffs, added the relevant-set-size finding and the H37b reference | FACTS_VERIFIED |
| F6 | `72` §3 prose used the rounded diffs and did not explain *why* the gap doesn't appear | corrected diffs; added the ceiling-effect explanation and the "design-level claim stands, expectation about per-epoch pooling's recall@10 win does not" framing | 72 |
| F8 | `65` v2 §4 (six open gaps) had no forensic-search-evaluation gap despite `72`'s CLIP/journey/footfall metrics remaining unrun | added a seventh gap item naming exactly what is still design-level | 65 v2 |
| F9 | `68` Q26 | reviewed — it only names H37 as the evaluation method, makes no "no number"/"pre-registered" claim, so it needed no fix | 68 (no change) |

No RETIRED_CLAIMS.md entry was added: every stale instance found was fixed in place directly, so no residual
claim needing a scanner rule remains. `tests/test_docs_retired_claims.py` and `tests/test_docs_numbers_in_facts.py`
were run after the edits (see §5) and pass.

## 5. Verification run

```
pytest -q tests/test_docs_retired_claims.py tests/test_docs_numbers_in_facts.py tests/test_forensic_search.py
```
All green (see AUDIT_LEDGER §20 for the exact pass/fail summary). `/tmp` checked: well under 500 MB.

## 6. Scope respected

No edits to `survsim/`, `out/`, `03`, `58`, `71`, or any other H-numbered section of `32` besides §H37's own
entry. `68` was read and left unedited (no stale claim found there). No GPU, no editor.
