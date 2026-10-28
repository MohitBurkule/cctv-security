# AUDIT_H60 · Alarm-card slice 1, from a hostile security reviewer

Audited 2026-09-27 against `39da635` (pre-registration `f941b44`). Fresh
`survsim run configs/scenarios/smoke_mock.yaml` to scratchpad, then `survsim alarm-cards --mode sim|real`.
No GPU, editor or `out/` use. **Score: 7/10** — no leak, but the chain and the salt were over-sold.

## 1. Leak check (real mode)

| check | result |
|---|---|
| sim-only keys in real `cards.jsonl` | 0 of 10 keys, 0/2 cards |
| by value: every uid (`track_ids.json`, events `actors`), event id, `world.parquet` zone, `identities.parquet` cell | 0 hits (only `loiter`, a substring of the rule's own label `suspicious.loiter`) |
| shipped guard `gt_values` | **defect:** omitted zone names; would not have caught a zone leak. Fixed; test `test_gt_values_include_zone_names` |
| `alarm_id` | sha256(run_id, camera, t ms, tracker id, label, index); no GT uid. `run_id` hashes `scenario.resolved.json` (config, not GT). `t` of a GT-rule alarm is GT-derived timing, but it *is* the alarm |
| CLI `leak_count` after fix | 0 |

## 2. Hash chain

| property | finding |
|---|---|
| canonical JSON | sorted keys, `(",", ":")` separators, ASCII. Floats = Python shortest repr (deterministic in Python, **not** RFC 8785 JCS). NaN was accepted; now refused (`allow_nan=False`) |
| single-record edit | caught at that index, 5/5 |
| reorder (swap 0/1) | caught at 0 (new test) |
| replaced first record | caught at 0 unless whole log is re-chained from genesis — then **passes** |
| tail truncation | **defect: passed.** `verify(..., expected_head=)` added; mismatch reported at `len(entries)`. The CLI already writes `chain_head` to `summary.json`, but a head on the same disk is not an anchor |
| dismiss requires reason | enforced in `make_entry`, **not** in `verify`: a rehashed reason-less dismiss verified. Fixed + test |
| operator id | `sha256(salt|id)`; salt is a public CLI default `survsim-h60`, stored nowhere, not per site. A 30-name roster is reversible by enumeration. Doc-only finding (CLI out of scope) |

## 3. Claims in 32 §H60 vs tests

| claim | proved by | verdict |
|---|---|---|
| leak 0 of 2 | `test_real_mode_leak_count_is_zero`, CLI run | holds; guard now includes zones |
| sim guard counts 2/2 | `test_sim_cards_would_leak_and_carry_gt` | holds |
| 2 cards = 2 alarms, ids identical across modes/reruns | `test_alarm_ids_identical_across_modes_and_reruns` | holds |
| hit delays = `alarms.score` latencies | `test_gt_match_hits_agree_with_score` (synthetic events) | holds, synthetic only |
| edit any of 5 → fails at index | parametrised test | holds (synthetic cards) |
| "deleting a record fails at the gap" | middle deletion only | **imprecise** → reworded: tail truncation needs an anchored head |
| identical heads on rerun | unit test | holds, not CLI-level |
| prediction held / "abandon if" per field | — | **re-scoped**: literally, 66's clause triggers for GT-rule alarms; 32 now says real mode is a guard only, with no tracker-sourced alarm or runner score carded yet |

## 4. Fixes (code: `survsim/eval/alarm_card.py`, `evidence_pack.py` only)

`gt_values` + zone names; `_canon` `allow_nan=False`; `verify` rejects dismiss without reason and
accepts `expected_head`. Four regression tests (`tests/test_alarm_card.py`, 13 → 17).
Docs: 32 §H60 result, 86 §7, 66 (slice 1 done; slice 2 = runner score/θ/rank + clip/model hashes +
per-site salt + anchored head), 74 drill 1 log box, 63 Part 0 + B2, 65 v2 §10 (no printed sim card
as a prop), FACTS row, 00.
