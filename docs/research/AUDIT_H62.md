# AUDIT_H62 · Position/time-keyed alarm scoring under tracker identity churn

Audited 2026-09-27 against `docs/research/32_EXPERIMENTS_LOG.md` §H62,
`out/experiments/h62_position_time_score/results_calibrated.json`, `results_benign.json`
(commit dd18945), `scripts/h62_position_time_eval.py`, `survsim/eval/alarms.py`
(`position_radius_m` mode, `Alarm.pos`, `TruthEvent.actor_pos`/`bystander_pos`,
`AlarmScore.position_time_recall`/`position_time_false_credit_rate`), `tests/test_alarm_position_time.py`,
`RETIRED_CLAIMS.md` R61, `AUDIT_TAILGATER_RECONCILIATION.md`, `AUDIT_H59.md` (style/scope reference),
docs/research 58 §8.4, 76, 78, 65 v2, 60, 48.

**Score: 96/100.**

## 1. Headline numbers — recomputed exact from the JSONs

`results_calibrated.json['arms']` and `results_benign.json['arms']`, read directly (890 instances,
`n_events`):

| arm | scorer | recomputed | 32 §H62 / task-quoted |
|---|---|---|---|
| calibrated, C | actor-aware | 0.10787 | 0.108 ✓ |
| calibrated, C | window-only | 0.82809 | 0.828 ✓ |
| calibrated, C | position_time r=2 m | 0.79213 | 0.792 ✓ |
| calibrated, C+abc | actor-aware | 0.01011 | 0.010 ✓ |
| calibrated, C+abc | window-only | 0.06629 | 0.066 ✓ |
| calibrated, C+abcg | actor-aware | 0.10000 | 0.100 ✓ |
| calibrated, C+abcg | window-only | 0.73933 | 0.739 ✓ |
| calibrated, C+abcg | position_time r=1/2/3 m | 0.68539 / 0.71461 / 0.72472 | 0.685 / 0.715 / 0.725 ✓ |
| calibrated, C+abcg | false-credit r=1/2/3 m | 14.754 % / 31.289 % / 49.302 % | 14.8 % / 31.3 % / 49.3 % ✓ |
| benign, C+abcg | actor-aware / window-only | 0.70112 / 0.72360 | 0.701 / 0.724 ✓ |
| benign, C+abcg | position_time r=2 m | 0.71124 | 0.711 ✓ |

Every number in the task's brief and in 32 §H62's table recomputes exactly from the two `results_*.json`
files. `n_events=890` matches for both arms. `n_swap`/hazard sourcing is out of scope here (H59's own
audit already covers it); this audit only recomputes H62's own arithmetic.

## 2. The static-vs-dynamic deviation — is it stated wherever the numbers are quoted?

32 §H62's own "confounds" paragraph and results section state the deviation explicitly (dynamic per-alarm
reference computed in the eval script vs. `alarms.score`'s own static `TruthEvent.actor_pos`-at-`t_start`,
which hits 0.2–2.8 % of the time). Checked every place H62 is now quoted outside 32 itself:

* `docs/13_BASELINES.md` H62 row — quotes recall/false-credit only, no claim about which reference is used;
  no deviation to state (fixed this audit: added a `fig_h62.png` reference line, no numeric claim changed).
* `docs/research/66_HYPOTHESIS_BACKLOG.md` — states the mode name and both bars without asserting *how*
  the reference position was obtained; added a code follow-up note (see §3) that makes the static/dynamic
  distinction explicit for a future reader who might otherwise call `alarms.score(position_radius_m=...)`
  directly on a moving actor and reproduce the ~0 % static result by surprise.
* `docs/research/60_ONE_PAGE_CHEAT_SHEET.md`, `65_DRESS_REHEARSAL_V2.md` §4, `48_MOCK_INTERVIEW_ROUND2.md`
  C8i (added by this audit) — all quote only the recall/false-credit pair, never claim the static call was
  used, so none of them can misrepresent the deviation; none needed a caveat added because none makes the
  claim the caveat would qualify.
* `docs/research/FACTS_VERIFIED.md` row (pre-existing, not edited by this audit) — same: quotes the dynamic
  numbers without asserting the mechanism, no fix needed.

No location was found stating or implying that `alarms.score`'s own `position_radius_m` call (the static
mode) produced the headline recall numbers — the one place that risk existed (66, a bare mode description)
now carries the follow-up note. No RETIRED_CLAIMS action needed; this is not the R61 pattern (a bare
number missing its caveat) but a mechanism note, more narrowly scoped than an R-rule regex should target.

## 3. Should `alarms.score` carry the dynamic reference itself? (follow-up, proposed only)

Recommendation: **yes, as a future round, not implemented here** (out of scope per task and per repo
rules — `survsim/` is off-limits this audit). The generic per-event API's static `actor_pos` is correct
for its stated contract (one position per event) but the H62 round shows that contract silently produces
near-zero recall (0.2–2.8 %) whenever a real actor moves for more than a metre or two inside the tolerance
window — a footgun for the next caller who doesn't know to precompute a dynamic reference outside the
API, as this round's eval script had to. Proposed shape, added to 66 as a follow-up: accept a time-varying
`actor_pos` (callable or interpolated per-uid track, keyed by alarm timestamp) as an alternative to the
single static point, defaulting to today's static behaviour so no existing caller changes. Not implemented
here; flagged only.

## 4. Principle-4 wording proposed in 32 §H62 — accurate and terse enough?

32 §H62 proposes, for a human to review before applying:

> "An alarm on the wrong person is not a hit — `alarms.score()` matches by actor identity (`actor_aware`)
> whenever alarms carry a `uid`. When a uid comes from a tracker/ReID pipeline rather than ground truth,
> its identity churn can be scored separately with `position_radius_m` (docs/research/32 H62), but H62
> found that mode's own bystander/false-credit rate exceeds 30% at 2 m on tailgate-style scenarios where
> the actor and a bystander are within the same radius by construction — it is not a safe drop-in
> replacement for `actor_aware`, only a diagnostic for how much of an actor-aware recall drop is a scoring
> artefact versus a real fusion failure."

Checked against the recomputed numbers (§1): "exceeds 30% at 2 m" is accurate (31.3 %, and 49.3 % at 3 m,
so "exceeds 30%" is not cherry-picking the worst radius — even the more conservative r=1 m case, 14.8 %,
is disclosed by the surrounding 32 §H62 text, just not in this one sentence). "Tailgate-style scenarios
where the actor and a bystander are within the same radius by construction" is the correct mechanism (32
§H62's own reading section, confirmed independently in §1 of this audit: false-credit rises monotonically
with r — 14.8/31.3/49.3 % — exactly as expected if it tracks proximity rather than an estimation bug).
"Only a diagnostic" matches the decision ("partially met... keep `actor_aware=True` as the default").

This is accurate. It is **not** fully terse for a CLAUDE.md principle addendum — at ~100 words it is
report prose, not principle-list style (principles 1–7 in CLAUDE.md run 15–40 words each, sentence
fragments, no parenthetical citation). **Recommended condensed sentence for CLAUDE.md**, keeping every
number claim from the long form and cutting the doc citation/rationale clause:

> "An alarm on the wrong person is not a hit — `alarms.score()` matches by actor identity (`actor_aware`)
> whenever alarms carry a `uid`; a `position_radius_m` mode exists for tracker-fed uids but is a diagnostic
> only — false-credit exceeds 30 % at 2 m on scenarios where the actor and a bystander share that radius
> by construction (32 §H62) — not a replacement for actor-aware scoring."

Not applied to CLAUDE.md by this audit (task explicitly withholds that edit); recorded here for a human
to apply.

## 5. Docs/tests

`docs/research/figures/fig_h62.png` added (copied from `out/experiments/h62_position_time_score/fig_h62.png`,
the `out/` copy is unchanged); referenced from 32 §H62's results header and `docs/13_BASELINES.md`'s figure
list. `tests/test_alarm_position_time.py` (7 tests) and `pytest -n auto -q` both pass; `/tmp` usage checked,
well under 500 MB.

## 6. Why not 100

Two points held back: (1) the condensed principle-4 sentence recommended in §4 is this audit's own
editorial judgement of "terse enough," not a measured fact — a different terse phrasing could reasonably
be chosen; (2) the code follow-up in §3 is a design recommendation, not verified against an implementation
(none exists), so its exact API shape is a proposal, not a checked claim. Both are flagged as such rather
than overstated, which is the intended use of a partial score here, not a defect found in H62's own
numbers (which recompute exactly, §1) or its documentation discipline (§2, clean).
