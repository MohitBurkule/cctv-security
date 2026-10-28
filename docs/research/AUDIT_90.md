# AUDIT_90 — panel-chair audit of `90_MOCK_INTERVIEW_ROUND8_FULL_RUN.md`

## Scope

(1) Audit `90` as the panel chair: every number against `FACTS_VERIFIED.md`
and `tests/test_docs_retired_claims.py`; every "answer to give aloud" ≤ 80
words and consistent with `65` v2/`68`/`79` model answers; the drill-1
exchange against `74`; the STAR story against `46`; the reel moment against
`89`; overclaiming and retired-form red flags.

(2) Check whether `RETIRED_CLAIMS.md` rows R56, R05, R18, R54 (the ones the
author reworded `90` around) still match accurate prose, or whether the
regexes themselves need tightening.

## (1) Findings

**Word counts.** All 8 technical-block answers (§5–25 min) measured
programmatically: 60, 53, 61, 63, 61, 39, 60, 60 words. All ≤ 80. ✓.

**Retired-claims scan.** `pytest tests/test_docs_retired_claims.py` passes.
A line-by-line dry run of every registry pattern against `90` finds exactly
two matches, both on the scorecard row that explicitly narrates the retired
form as the "2/5" example (`retired HOTA 0.545`, `retired window-only dwell_25
recall 0.900 — actor-aware is 0.367`) — both correctly exempted by the
registry's own "states the correction" rule (R16, R18). No unexempted hits.

**Real bug found and fixed — threshold mislabelled as the one that "floods
the queue".** `74`'s reference-design table and `65` v2 §3's ship table both
say the operating point that floods the operator queue is **pooled θ 0.9**
(5.033 FA/cam-h, ~205 alarms/h, 0.504/0.324 realised) — not A1's stricter
θ 0.95 (2.915 FA/cam-h, 120 alarms/h, 0.586/0.511 realised, the point kept for
≥ 2 operators). `90`'s Drill-1 walkthrough (old line 142) said the opposite:
"better than the looser θ 0.95 point, which floods the queue instead." The
same file's own §40–50 behavioural answer (line ~203) gets this right,
attributing the flooding to "the pooled-θ operating point" — so `90` was
internally inconsistent as well as wrong against `74`/`65` v2. **Fixed**: the
Drill-1 line now reads "better than the pooled θ 0.9 point, which floods the
queue instead (5.033 FA/cam-h, 205 alarms/h, only 0.504 realised)."

**H26/H51 framing.** Checked for the contradiction pattern named in the task
("H26 not significant, then H51 significant, small"): `90` states H26's
equal-step gain "did not clear Holm" and separately, correctly scoped to H51's
ten paired seeds, "+0.0042 and +0.0051, Holm p 0.0039." These are not
inconsistent — H26 (5 seeds) and H51 (10 seeds, re-run) are different
experiments with different outcomes, and the doc marks which is which in
every instance. This matches R57's required framing exactly (dose gain must
carry an "H26"/"before H51" marker when called n.s., or an "H51"/Holm-p marker
when called significant). ✓.

**Ship sentence.** The two `90` occurrences of the ship-point sentence
("conformal θ ≈ 0.9634 ... realises about 0.62 recall at 5 minutes", process
block's "0.621" vs "stricter conformal point (0.621)") both round the
canonical `65` v2 §3 numbers (θ 0.963436 → 0.617 ranked; θ 0.9618/0.9629 →
0.618/0.621 ranked) consistently; no digit is invented. ✓.

**Fusion sentence (R55 form).** The one literal "context and a second sensor"
occurrence (pitch, and Q4 pushback) carries H53, the qualified 2.3-point
recall cost, "all sensors simulated", and the tailgater-defeats-it clause with
the H54 gate-counter fix (0.685 recall) — the exact `R55`/`AUDIT_78` canonical
form, word for word against the `OK_FIXTURES` entry in the test file. ✓.

**Drill-1 vs `74`.** Cross-checked against `74` §Drill 1 (c): the 5×Orin-NX
box (4 active + 1 spare), the human-decision box (`dispatch/dismiss/escalate`,
"nothing is dispatched without this click"), and the WORM audit-log box
(model hash, θ, verdict — a subset of `74`'s full field list, which also has
clip hash, operator id, reason, chained hashes; `90`'s summary is a compressed
but non-contradictory subset) all match. The decode-vs-compute trap answer
matches `79` Q9 verbatim in substance (18-stream decode ceiling ≠ capacity;
4 NX for compute). ✓.

**STAR story vs `46` story 9.** S/T/A/R structure, the three reclassified
licences (MOT17/MOT20 CC BY-NC-SA 3.0, Stanford Drone, UR Fall, non-commercial;
AMASS research-only), the risk-table and "evaluation only" actions, and the
lesson line all match `46` story 9 verbatim in substance. `90` adds one
sentence not in `46` ("the same discipline is why our render cast is now CC0
Quaternius, not MetaHuman") — checked against `CLAUDE.md`'s licensing section
and it is accurate (batch_v7 CC0 is now the default; MetaHuman's own terms
forbid ML training/testing), so this is an accurate elaboration, not a
contradiction. ✓.

**Reel moment vs `89`.** The 30-second cut order (title → `disguise_and_
tamper_day` triptych → appearance-epoch clip → closing card, two facts) and
all three quoted numbers (0.276→0.152 AP; 0.488→0.0047 FA/cam-h) match `89`'s
30-second-cut section and closing-card bullets exactly. ✓.

**Overclaiming / red-flag scan.** Grepped `90` for `compliant`, `tamper-proof`
and bare `secure` — zero hits. The night-before checklist's item 7 explicitly
lists things not to claim (wardrobe finished, Jetson latency, SNN expertise,
render-replaces-real-data, H37). No instance of the R54-listed overclaim
phrases ("synthetic improves detectors", "renders can replace real data",
"line-cross is solved", "wardrobe works end to end", etc.) appears anywhere
in the file.

**Residual watch item, not fixed (out of the audit's numeric-error scope):**
the pitch and Q4 answer cite H54's tailgater fix (0.685 recall with a gate
people-counter) without H59's later, more pessimistic finding — under
calibrated identity-switch noise the same fix's tailgater recall collapses to
0.100, an actor-aware-scoring effect, not a fusion break (`FACTS_VERIFIED.md`
row H59, `AUDIT_H59`). The 0.685 figure itself is not retired and is stated
correctly (H54's own benign-noise-model number), so this is not an
unexempted retired claim; it is a nuance a sharp panelist could raise as a
follow-up, and the doc's existing "all alarm numbers are simulated" caveat
partially covers it. Left as-is given the 80-word budget and because editing
would risk contradicting `65` v2, which also states the H54 number
unqualified in its own numbers list.

## (2) RETIRED_CLAIMS registry rows R56, R05, R18, R54

Checked each row's pattern against `90`'s actual text (not a hypothetical
earlier draft — no git history of an unfixed version exists; `90` was added
in a single commit, c0a0741) and against plausible accurate phrasings of the
same fact, to decide whether the *regex* is too eager or the *prose* was
wrong.

* **R56 (0.001 budget wording).** `90` states the budget three times, every
  time with an "assumed"/"our assumed"/"(28 §6)" marker on the same line
  (pitch line, Q4 answer, drill close line). This is exactly the required
  form (`assumed`/`our budget`/`28 §6`/`A ?= ?4`/`zone/day` exemption). No
  false positive on `90`, and the exemption list is broad enough that
  accurate phrasing naturally survives it. **No regex change.**
* **R05 (`\b3 (Orin )?NX\b`, decode-only ceiling).** `90` never writes a bare
  "N NX" other than "4 NX"/"5 × Orin NX", so it never touches the pattern.
  The scenario the task names — a natural, accurate phrase like "2–3 NX for
  decode alone" — genuinely would trip `\b3 NX\b` (the en-dash is not a word
  character, so `\b` still fires before the "3"), but the row's own exempt
  clause already covers it: any such sentence needs to say why the number is
  3 (decode, not compute), and "decode" is required for the exemption to
  fire. Since the accurate phrasing FACTS itself uses ("3 NX or 2 AGX **for
  decode only**", FACTS row on Orin decode streams) always puts "decode" on
  the same line, the exemption already catches genuinely correct prose.
  **No regex change** — verified with the existing prose in FACTS and `74`,
  which both pass.
* **R18 (`dwell_25` 0.900).** `90`'s one occurrence is in the scorecard's
  "2/5 looks like" column, explicitly labelled "retired window-only" with the
  correct value (0.367) on the same line — the intended, correct use of the
  registry (cite the wrong number only as the stated "before"). Accurate and
  correctly exempted. **No regex change.**
* **R54 (overclaim phrase list).** `90`'s wardrobe line ("the MetaHuman
  wardrobe pipeline is finished (it's [A])") does not match any of R54's
  listed phrases (`wardrobe works end to end`, etc.) because it is phrased as
  a *prohibition* ("do not claim... is finished"), which is accurate per
  `CLAUDE.md`'s `[A]`/`[V]` state and was never going to trip the regex in
  the first place — R54 only flags the affirmative overclaim, not its
  negation. **No regex change**; the prose the author chose is accurate on
  its own merits, not merely regex-avoidant.

**Conclusion for (2):** none of the four named rows needed tightening for
`90` — in every case the reworded prose is both accurate and already the
form the registry's exemption clause was designed to allow. No fixture added,
since no genuine false positive was reproduced against real (not
hypothetical) text in this repo. If a future doc writes a numeric range that
straddles a retired single value (e.g. "2–3 NX" without the word "decode" on
the same line), R05's exemption would need a companion regex test — flagged
here for the next audit round if it recurs, but not created speculatively
against no observed failure.

## Fixes applied to `90`

1. Drill-1 walkthrough: corrected which θ point "floods the queue" — was
   wrongly attributed to A1 θ 0.95, is actually pooled θ 0.9 (matches `74`
   and `65` v2's ship table, and `90`'s own later, correct statement of the
   same fact).

## Score

**9/10.** One real, self-contradicting numeric error found and fixed
(θ-flooding mislabel); everything else — word budgets, retired-claims scan,
H26/H51 framing, ship/fusion canonical sentences, Drill-1 vs `74`, STAR story
vs `46`, reel moment vs `89`, overclaim scan — checks out clean. Docked one
point for the found-and-fixed error rather than 10/10, and a half-point held
back for the H54/H59 tailgater nuance left as a watch item rather than
resolved.

## Registry / test status

`pytest docs/research/../..` — both doc tests run and pass after the fix:
`tests/test_docs_retired_claims.py` (6 passed) and the `60`-numbers-vs-FACTS
test bundled in the same file (unaffected by this audit; not touched).
