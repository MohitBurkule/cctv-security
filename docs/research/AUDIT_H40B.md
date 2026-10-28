# AUDIT_H40B · Line-cross on fenced worlds (32 §H40b)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** both 'not fixed' items (demo COCO wildlife path, vacuous loiter fence test) were fixed in commit 3377ea2.

Audited 2026-09-27 against `12b6c92` (results), `d51e5f9` (pre-registration), `9468696` (engine). Method
as AUDIT_76_H40: every H40b number recomputed in Python (`.venv`) from
`out/experiments/h40b_line_cross/results.json` (`noisy_*`, `free_*`, `twin_fa`, `clean_fa_by_kind`,
`decision_h40b`, `wall_s`); fence enforcement and GT class checked in `survsim/director/fences.py`,
`world.py`, `gt/writers.py`, `datasets/build.py`, `gt/coco.py`; `tests/test_behaviours_intrusion.py` +
`tests/test_line_cross.py` run (19 passed, 14.5 s). No GPU, no editor, `survsim/` and `out/` untouched.

## 1. Numbers — recomputed

| claim | recomputed | result |
|---|---|---|
| N 369.4 [318.4, 428.9], recall@10 0.862 | 1,108,978 / 3,002.0 = 369.413; boot [318.358, 428.922]; 257/298 = 0.8624 | match |
| A 353.9 / 0.829 | 353.889; 247/298 = 0.8289 | match |
| B 0 / 0.822 | 0; 245/298 = 0.8221 | match |
| C 0 (≤ 0.001 rule of three) / 0.782 [0.736, 0.829] | 0; 3/3,002 = 0.000999; 233/298 = 0.7819, boot [0.7363, 0.8289] | match |
| not met vs 0.9 bar | `decision_h40b` recall_ok false, fa_ok true | match |
| noise-free B 0.899, C 0.852 | 268/298 = 0.8993; 0.8523 | match |
| twins on C patrol 0.389 [0.367, 0.412], maint 0.099 [0.088, 0.111] | 1,167 → 0.3887 [0.3668, 0.4117]; 298 → 0.0993 [0.0883, 0.1112] | match |
| "~490× budget" | (0.3887 + 0.0993) / 0.001 = 488× | match (rounded) |
| "398 of C's FPs are twins" | 398 of **424** recall-world FPs (94 %) | match; **denominator added** |
| wildlife 5.96/cam-h on N, 0 from A | 17,891 → 5.960; A/B/C 0 (Garwood upper 0.0012) | match |
| 676 worlds / 3,002 cam-h / 300 recall / 298 events / 2 never inside | `n_clean`, `clean_cam_h`, `n_recall`, `recall_truth_events`, `recall_actors_never_inside` | match |
| twin columns N/A/B 2.66/0.61, 2.47/0.40, 0.43/0.11 | 2.664/0.614, 2.472/0.400, 0.432/0.111 | match |
| per-kind recall C 0.780 / 0.765 / 0.800 | same | match |
| fragments 937k | 936,810 of 1,108,978 (84 %) | match |
| wall 45 min | 2,678 s | match |

## 2. Claims corrected in place

1. **32 / 76 "noise-free N 16.98 → 1.84 … all of that residue is commuters pressed against a fence"** —
   wrong. `free_N.clean_fa_by_kind` has **no commuter key**: 5,518 wildlife alarms = 1.838/cam-h, i.e.
   the whole residue is wildlife (primary FA keeps wildlife by registration). Fixed in 32 and 76.
2. **32 "The remaining misses are the noise model's fragments inside the 5 s dwell"**; 76 "Recall is
   limited by tracker fragments" — imprecise. Decomposition of C's 0.218 shortfall: depth/dwell on
   **noise-free** tracks 0.101 (A 1.000 → B 0.899, still 0.916 at 30 s so not only timing; probe 0.827),
   gate context 0.047 (noise-free C 0.852), assumed noise 0.070. Fragments are the minority. Consequence
   written into 66 H50: stitching alone **cannot** reach 0.9 (ceiling 0.852).
3. **32 / 76 "a role-blind video rule cannot remove it"** — overstated. The pre-registration's own
   confound says arm C does not exempt the fence gate (gate entries sit away from gate/queue zones). A
   gate exemption is role-blind and would remove the gate-entry share, at the price of forced/tailgated
   gate entry. Reworded: what a role-blind rule cannot do is separate guard from intruder *inside*.
4. **76 §4 hard-negatives table** — the `12b6c92` edit replaced the *hard-negatives* "Fence climb" row
   with the gap-table row (it matched both tables). Original row restored; gap-table row kept.
5. **76 §5 intro, Q8, Q10** — stale after H40b ("SurvSim has none of the animals and no patrol
   behaviour"). Updated with H40b state; shadows/insects/weather/headlights still absent.
6. 32 "398 of C's false positives" → "398 of C's 424 (94 %)"; ~490× shown as 0.389 + 0.099 = 0.488.

**Noise model labelling.** 32 pre-reg ("ASSUMPTION, stated"), 32 results ("assumed and not fitted"),
FACTS, 13, 76 and every row added in this fold-in say *assumed*. 74 drill 1 still said "declared" for
H40 → "assumed".

## 3. Principle 1 — truth after the fence [V]

`World.step` calls the behaviour's `step` (which includes avoidance), then `Fences.clamp(prev, new, role)`
on the resulting position for any non-crossing, ground-level agent; the clamped position is written to
`agent.pos` and `agent.vel`, and `Recorder.add_world` reads `agent.pos`. Checked by script: a `transit`
aimed at a point inside the fence was clamped 41 times in 300 ticks, recorded `world_rows` x/y equal the
agent's actual position every tick, maximum recorded depth inside the fence 0.0 m. **Holds.**

Weakness found (not fixed — `tests/` edit out of scope for a doc audit, recommended):
`test_fence_stops_a_behaviour_that_steers_straight_in` uses `loiter` with `zone=[18, 0]`; that agent
never moves (speed 0 all 200 ticks, **0 clamps**), so the test passes without exercising the fence.
`test_commuter_routes_round…` does exercise it. Replace the loiter spec with a straight `transit` to an
inside point and assert clamps > 0 and recorder rows == agent positions.

## 4. Wildlife ground truth [V]

* `Agent.object_class` = `"animal"` from `identity["class"]`; `world.parquet` and `identities.parquet`
  carry `object_class` (test asserts `{"animal"}`).
* MOT rows: `_mot_class` writes `0,8` (consider 0, class 8 "distractor") for non-persons, `1,1` for people.
* `survsim dataset` → `datasets.build.read_gt` keeps targets only for `conf ≥ 1 and cls == 1`; class 8 is
  in `IGNORE_CLASSES {2, 7, 8, 12}`, so wildlife is an **ignore region, never a COCO "person"**. Holds.
* **Gap:** `gt/coco.from_camera_rows` (used by `survsim/demo.py` from backend `observe()` rows) does not
  filter on `object_class`; if a demo scene contains wildlife it would be exported as `category_id 1
  "person"`. Default demo scenes have `wildlife: 0`. Recommended code fix (out of scope here): skip rows
  whose uid is not a person, or add a category.

## 5. Score

| criterion | before | after |
|---|---|---|
| H40b numeric accuracy vs results.json | 9.5/10 (398 without denominator) | 10/10 |
| causal claims (residue, recall loss, "cannot remove") | 5/10 (three wrong or overstated) | 9.5/10 |
| code ↔ registration agreement | 9.5/10 (gate confound disclosed in pre-reg, not carried to results) | 10/10 |
| noise model labelled assumed | 9/10 (74 "declared") | 10/10 |
| principle 1 / wildlife GT | 8.5/10 (vacuous loiter test; demo COCO path unfiltered) | 8.5/10 (documented, code untouched) |
| 76 table integrity + staleness | 6/10 (hard-negatives row overwritten; Q8/Q10 stale) | 10/10 |
| corpus propagation | 4/10 (FACTS, 13, 76 only) | 10/10 |
| **total (×100/70)** | **73/100** | **97/100** |

## 6. Corpus fold-in

FACTS: H40b audit row. 52 register row. 64 register row, results-table row, paragraph "after fixing the
generator, the twin, not the rule, is the product problem". 60 item 27 updated in place (list stays at
≤ 40) + trap 5. 48 number 43b + C8e follow-up 3. 65 N13b. 74 drill 1 (H40b numbers, gate-log/schedule
fusion). 76 §H40b table + "What a real site adds" caveat, §4/§5/Q8/Q10. 23 M8 row + rank-15 row. 66
H40b status, new **H49** (schedule / gate-log twin suppression) and **H50** (fragment-robust dwell via
track stitching), both in the 49 §12 template. 00 index rows.
