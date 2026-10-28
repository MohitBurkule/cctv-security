# Today (2026-09-28): read in this order, nothing else first
0. [`110_MORNING_QUIZ.md`](110_MORNING_QUIZ.md) — 15-min phone self-test before leaving (40 Qs, 10 sentences, 3-min story).
1. [`107_OVERNIGHT_BRIEFING.md`](107_OVERNIGHT_BRIEFING.md) — overnight demo, experiments, audits, 5 do-not-says (phone).
2. [`104_DAY_OF_RUN_SHEET.md`](104_DAY_OF_RUN_SHEET.md) — the timed run sheet for the day and its 13 sentences.
3. [`65_DRESS_REHEARSAL_V2.md`](65_DRESS_REHEARSAL_V2.md) §0 items 1–22 — what changed; honest sentences as written.
4. [`interview_pocket.pdf`](interview_pocket.pdf) (6 pp) — pocket numbers; `interview_pack.pdf` (22 pp) is the full pack.
5. [`108_WHITEBOARD_SCRIPT_30MIN.md`](108_WHITEBOARD_SCRIPT_30MIN.md) — 30-min board: 8 boxes, minute plan; pushback in `109`, cost in `106` (A1–A12, ratios).
6. [`101_DEMO_WALKTHROUGH_QA.md`](101_DEMO_WALKTHROUGH_QA.md) — reel questions (`demo/survsim_demo_v2.mp4`).
7. [`105_MOCK_TECHNICAL_CHAT_OVERNIGHT.md`](105_MOCK_TECHNICAL_CHAT_OVERNIGHT.md) — technical-chat mock + "stop talking" list.
7b. [`111_MOCK_WHAT_IS_WRONG_WITH_YOUR_SIM.md`](111_MOCK_WHAT_IS_WRONG_WITH_YOUR_SIM.md) — 20 "what is wrong with this" questions (honest / avoid / concede) + 10 do-differently.
8. Drills: [`88_CODING_DRILLS.md`](88_CODING_DRILLS.md), `drills/coding_hour/task*/TIMEBOX.md` — read, do not solve.

Where any file disagrees with `FACTS_VERIFIED.md`, FACTS wins.

# Reference

- [`112_FAR_FIELD_AND_DEGRADE_NUMBERS.md`](112_FAR_FIELD_AND_DEGRADE_NUMBERS.md) — one table reconciling every far-field / degrade recall, precision and latency number (arm, denominator, frames, conf, stream, licence) + which to say when.
- [`113_ALARM_AND_OPERATOR_NUMBERS.md`](113_ALARM_AND_OPERATOR_NUMBERS.md) — one table reconciling every alarm-budget, θ, operator, fusion and rule number (unit, identities, operator model, what is simulated) + which to say when.

## Start here

This is the research corpus behind SurvSim: ~834k words across 16 R/D/H
dossiers, 76 numbered report files (`17`–`91`), 65 `AUDIT_*.md` files, and
`FACTS_VERIFIED.md` (run `python tools/corpus_stats.py` to refresh these
numbers), written to prepare for an the vendor interview (UK
defence AI, CCTV/CNI analytics) and to ground every design claim in the actual
simulator behind it. **Where any file disagrees with `FACTS_VERIFIED.md`,
FACTS wins** — everything else is working material, not the source of truth.

## The 1-hour path (the night before, or the morning of)

Verbatim from `00_INDEX_AND_READING_ORDER.md` (~55 min total):

1. `60_ONE_PAGE_CHEAT_SHEET.md` (15 min) — all 40 numbers in arc order, formulas, stories, "not to say".
2. `65_DRESS_REHEARSAL_V2.md` §1, §3–§7 (15 min) — opener aloud twice, 30-s cut, ship answer, gaps, H26 retraction story, 10 hard Qs.
3. `FACTS_VERIFIED.md` "The forty to know cold" (12 min) — cover and recall.
4. `removed-vendor-doc.md` §0 + §3 (3 min) — headline correction, products.
5. `80_FIGURE_PACK.md` §2–3 (4 min) — the two lead figures, read each "Trap" line.
6. `84_COLD_READ_REVIEW_V3.md` §3 + §4 (4 min) — 10 questions, closed vs open gaps.

`00_INDEX_AND_READING_ORDER.md` also has 4-hour, 1-day, and full-corpus paths.

## Day-of files

- `65_DRESS_REHEARSAL_V2.md` — the rehearsal script (§2 is `60` re-ordered, skip it).
- `102_OPERATOR_PROCEDURE_AND_ATTACKS_MOCK.md` — 30-min system-design whiteboard mock: operator layer under decoy flooding, uniformed intruder, tailgating, tamper (6-step board, 15 probes, 5 traps).
- `60_ONE_PAGE_CHEAT_SHEET.md` — the one page to have open.
- `interview_pack.pdf` (22 pp) — the compiled PDF for the day (regenerated reproducibly, see `AUDIT_84_85`).
- `figures/pack/pack.pdf` — the 10-figure pack (`80_FIGURE_PACK.md` is the source; figures `01`–`10`).
- Demo reel: `89_DEMO_REEL_SCRIPT.md` + `tools/demo_reel.py` build `survsim_demo.mp4` from `out/batch_v8/` CC0 renders only — never MetaHuman batch_v4–v6 frames.

## How claims are kept honest

- **`FACTS_VERIFIED.md`** — the numbers allowed to be said out loud, each tagged
  by source and confidence; the single tiebreaker when files disagree.
- **`RETIRED_CLAIMS.md`** — claims that were said once, then found wrong or
  overclaimed, with the correction. Checked before repeating any "we proved…"
  line. 80 retired so far (R01–R80); ledger 233 rows.
- **Two doc tests** (`pytest tests/test_docs_retired_claims.py
  tests/test_docs_numbers_in_facts.py`) — mechanically check that numbers in
  the corpus trace back to `FACTS_VERIFIED.md` and that retired claims don't
  silently reappear. Run these after editing any report file.
- **`AUDIT_*.md` files + `AUDIT_LEDGER.md`** — every audit round's findings
  (overclaims, stale numbers, mislabelled metrics) folded into one ledger, so a
  correction made once doesn't need rediscovering.

**Weak spots, rehearsed:** `103_SIM2REAL_AND_NIGHT_HONEST_STATUS.md` — sim-to-real tracking/ReID and night/IR, honest answers and probes.

## Licence rule

Anything **shown** (renders, demo reel, screenshots) must be CC0 —
Quaternius bodies + Kenney/ambientCG/Poly Haven assets (`tools/import_characters.py
--cc0`, the default since 2026-09-26). MetaHuman and SMPL-X renders exist as
internal engineering evidence only (batch_v4–v6, `AS_MH_*` clips) and may
**never** appear in ML training/eval, in the demo reel, or in front of a
customer — see CLAUDE.md "Licensing" and `47_CHARACTER_AND_ASSET_LICENSING.md`.

## For a reader from the vendor (15 minutes)

Skip the interview-prep framing and go straight to the engineering substance:

1. `52_SURVSIM_TECHNICAL_BRIEF.md` §5b — verified/attempted/broken ([V]/[A]/[X])
   capability table: what's actually built vs. claimed.
2. `80_FIGURE_PACK.md` figures — the architecture diagram and the two headline
   result figures, each with its "Trap" (the caveat a careful reader would ask
   about).
3. `63_CODE_TOUR_AND_LIVE_DEMO.md` — a guided tour of the real code (Director,
   backend, GT writers, degrade, eval) with commands to run it live.
4. `tools/demo_reel.py` — run it, or watch `survsim_demo.mp4`, for GT
   triptychs, appearance epochs, and PTZ/tamper behaviour on CC0 renders.

- Demo reel v2 Q&A (also item 6 above): `101_DEMO_WALKTHROUGH_QA.md` — 25 timestamped interviewer questions on `survsim_demo_v2.mp4`, model answers and 5 weak-answer critiques; Part 2: 30 questions on segments 13–34 and the 27-site mosaic (answer / trap / fallback) and a 3-segment guide (26, 20, 34); caption audit in `AUDIT_DEMO_REEL_V2.md`.
