
> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** item 8's h14b +0.0121 headline is retired as the dose gain — +0.004–0.005 at equal steps (AUDIT_H26, R51).

Method (same as AUDIT_55-56): I fetched every external source in 62 §9 and
compared each quote word for word. I checked every repo claim in 62 against
`survsim/core/models.py`, `generator/site.py`, `generator/layout.py` and
`export/env_plan.py`. I re-ran every command in 63 in a fresh shell (the long
ones in the background) at HEAD `9d89b4d`, then checked each excerpt's line
numbers against `git show HEAD:`. Test names were checked with
`pytest --collect-only -q`. 61 was not edited. Its part-6 table was re-checked
against 52 as it stands after E2 (`304fd6d`) and later commits.

**Score: 62: 38/44 claims correct as written (86 %), 6 corrected. 63: 52/58
correct as written (90 %), 6 corrected. Overall 90/102 (88 %).**

## 62 · external sources (14/14 fetched)

| Claim | Verdict |
|---|---|
| ONVIF Analytics spec v26.06; §A.2 Line, §A.3 Field, §A.4 Loitering; Line/Field/Loitering quotes; topic `ObjectIsLoitering` + `Since`; "normalized coordinates"; GeoLocation/GeoOrientation | Correct |
| LoiteringDetector `Field [tt:Polygon]` | **Refined**: the spec marks `Field` *optional* |
| "should contain a parameter 'Field' ElementItem" [§A.3] | **Corrected**: quote is in §A.1.2.1 (Generic parameters) |
| Axis OA: Time in area quote, 5 exclude areas, schedule, vertical-bar perspective | Correct |
| Axis Perimeter Defender conditional zone | Correct; ellipsis replaced by the full text ("defined on the ground") |
| Milestone MAD `Location Name`, `Message` quote | Correct |
| Stauffer & Grimson TPAMI 22(8) 2000; Makris & Ellis TSMC-B 2005 (35(3)); Morris & Trivedi TCSVT 2008 (18(8)); Wang, Ma & Grimson TPAMI 2009 (31(3)): venues, years, abstract quotes | Correct (OpenAlex) |
| OSM entrance values and quotes; SIT indoor/level | Correct (SIT also lists wall, door, level) |
| OSM opening_hours "Mo-Sa 10:00-20:00; Su off" | **Wrong**: the wiki example is "…; Tu off". Fixed |
| IFC4.3 OccupancyNumberPeak / OccupancyTimePerDay definitions | Correct |
| ICO high-risk examples (geolocation/behaviour, workplace, employee location; combining sources; novel technology "when combined with any other criterion") | Correct ("data processing at the workplace" is listed, but I could not get it back verbatim) |
| ICO surveillance: DPIA "legal requirement…", "minimum amount", consult workforce | Correct |
| ICO reuse "lawful only if compatible" | **Overstated**: compatibility is one of three routes (the others are consent and a legal obligation). Fixed |

## 62 · repo claims

| Claim | Verdict |
|---|---|
| `Zone.tag` literal set (8 values), `allowed_roles` in models.py | Correct |
| Zone ids per site type, gateline/entrance share `gate`, platform/reception share `queue` | Correct |
| Function vocabulary = round-3 one-hot | **Refined**: the one-hot also has `none` (58 §7.1, `loiter_features.zone_function`) |
| allowed_roles "in embryo" | **Refined**: only `zone.stage` and `zone.restricted_k` set it, to `["worker","guard"]` |
| `env_plan.SITE_TYPES` (6); `infer_site_type` keywords "in zone ids and tags" | **Refined**: it also uses the env id and prop types, and defaults to `event_plaza` |
| Layout entrances side/along/yaw; 3 m throat refusal | Correct (`_blocks_entrance`, t ∈ {−3, −1.5, 0}) |
| `pick_time` + `solar_position`; "renderer has a clock, Director does not"; §5.2 reuse `pick_time` for night worlds | **Corrected**: `pick_time` is daytime only (07:00–18:30, sun ≥ 12°). The clock that already exists is `Scenario.time_of_day.start`, which `env_plan.lighting_for` reads for day/night. §5.2 now writes the world clock there |
| round-3 numbers 3.114/2.468, CIs, recalls, 20.7 %, arm C 0.335 @ 0.553 | Correct (`round3_results.md`; ratio 0.7926) |
| 1.008 floor (58 §6.2), ~2,900× (58 §5), 58 §7.1 quote, 1,800 s vs 300 s, centroid leak (58 §5) | Correct |

## 63 · demo re-run (fresh shell, HEAD `9d89b4d`)

| Step | Doc | Measured | Verdict |
|---|---|---|---|
| 1 validate | 0.4 s, table | 0.37 s, identical | OK |
| 2 run | 15.6 s / 8.7 s | 13.9 s / 8.9 s, `events=8`, same file list | OK |
| 3 rig | 0.7 s | 0.57 s, identical numbers | OK |
| 4a eval smoke | 0.75 s, 60.0 FA/cam-h | 0.70 s, identical | OK |
| 4b eval disguise auto / window-only | 0.9 s | 0.75 s, identical (8 alarms, 2 bystander hits, 30.0 / 26.25) | OK |
| 5 audit-motion | 0.8 s | 0.70 s, identical | OK |
| 6 check_render | 18 s, height **SKIP**, 17.5 s | 14.1 s; **height PASS 0/3** since `9d89b4d` | **Drifted, fixed** |
| 7 realism | 6.4 s / 54 s, 7/14 → 11/14 | 5.7 s, identical stats | OK |
| 8 pytest | 46 s, 51 passed | **40 s, 55 passed** | **Drifted, fixed** |
| pre-warm disguise run | 145–165 s | 151 s, `events=32` | OK |

## 63 · code and tests

* Line numbers checked at HEAD (world.step 487, Loiter 91, dwell_label 150, CommuteWait 154, steer 16, apply 84, add_world 35, observe 90, gate 1296, plan_from_layout 481, check_motion 137, score 148, run_baseline 88, evaluate_mot 86, PROFILES 640, apply_profile 704). All correct. File lengths are correct except **rules.py: 399 at HEAD**. The 427 in the doc was the uncommitted working tree. Fixed.
* 26 named tests exist. **`test_run_is_deterministic` is in `tests/test_core.py`, not test_director.py**, and it and `test_disguise_scenario_records_two_epochs` are marked `slow` (deselected by default). Fixed. `tests/test_rules_round3.py` is **untracked**, so the doc no longer cites it as a guard.
* Q4 "47 cm" is now "up to 47.6 cm" (FACTS l.182). "Variety must be a test…" has no source in docs and is left as the author's own wording.
* Six Q-answers against CLAUDE.md: Q1 (engine-agnostic Director; ×100 / −Y / −yaw at the backend, principle 7), Q2 (RngHub, blake2b in `core/rng.py`, principle 6), Q3 (mask boxes, principle 1; 0.876–0.932, 0.664 → 0.696, 4,168 s → 33 s match FACTS/52), Q4 (black render = Rotator order, CLAUDE.md), Q5 (`741b025` H9–H11 and `98b7c03` H12–H14 pre-registrations exist; +0.012 = h14b), Q6 (MetaHuman clause, `commercial_ml_ok`). **All consistent.**

## 61 · part-6 pointers after E2

| # | 61 status | Now |
|---|---|---|
| 1 three HEADs | unclear | **Resolved**: 52 carries a single "True at HEAD `cec3317`" |
| 2 evasion 52 vs 40 | wrong | **Resolved**: CLAUDE.md now says 52 |
| 3 22 deselected | count only | **Resolved**: 52 names them as `slow` tests (> 10 s); 868/890 collected at this HEAD |
| 4 v8 3× slower | unclear | **Resolved**: 52 §4.1 explains (ID-mask pass + 70-min decoder + failed attempts) |
| 5 17 min vs 70 min | unclear | **Resolved**: 4,168 s measured for 4 cameras ≈ 17 min/camera |
| 7 0.290 > 0.276 | unclear | **Resolved**: 52 l.293 reconciles |
| 8 h14b | resolved elsewhere | **Now in 52 itself** (+0.0121 / +0.0095, headline) |
| 11 360 events | unclear | **Resolved**: terms box (300 recall worlds) |
| 12 reset-gap bug | unclear | **Resolved**: reported on purpose as the baseline's parameter flaw; C2 is the fix |
| 13 twin floor / oracle | thin | **Resolved**: terms box |
| 14 precision denominator | unclear | **Resolved**: terms box, alarms in the 360-event recall worlds |
| 15 H58 / H11-B | partly | **Resolved**: register H1–H16 + "loiter redesign"; H11-B defined |
| 16 amodal ranges | unclear | **Resolved**: 52 l.253 separates v8 0.879–0.914 from v7 0.921/0.907 |
| 17 72 vs 67 | unclear | **Resolved**: 52 l.274 (≥ 40 px, vis ≥ 0.7 filter) |
| 18 detector-IoU circularity | not addressed | **Addressed**: 52 l.282 "Why a detector is the reference, and its limit" |
| 20 TrackEval parity | unclear | **Resolved**: 52 l.376 "not done — roadmap M1" |
| 23 MetaHuman licence vs MH experiments | unclear | **Still open**: 52 cites the clause and the CC0 response but does not say whether the early MetaHuman recall comparisons were compliant |
| 24 CI wording | unclear | **Resolved**: 52 H12 row states cluster bootstrap ~3× wider and calls it the honest one |
| 25 60 numbering / Omnibus | wrong | Numbering **resolved** (1–7). The "Omnibus" string is gone from 60 |
| 26 "7,200" in §6 | wrong | **Resolved**: now "7,200 (v6/v7) to 10,000" |
| 9 H3 0.83 | unclear | **Resolved**: 52 names the setting (320×240 tiling, raw day) |
| 6, 10, 19, 21, 22 | resolved | Still hold |

Still open: **#23** only.

## Commits
- 62 fixes: landed inside `9d89b4d`. My staged 62 edit was swept into another agent's concurrent commit ("fix: standalone check_render.py…"). The content is correct, but the commit message does not describe it.
- 63 fixes: `6773abc`
- this file: see git log
