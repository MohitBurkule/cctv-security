# AUDIT_02_03 · docs/02 and docs/03 against code

Audited 2026-09-27 against `299e649`. No GPU/editor/`out/` use; `survsim/`,
`docs/32,58,66,71`, `FACTS_VERIFIED.md` untouched. Scope: the two "design
`survsim/director/behaviours.py` (`REGISTRY`), `survsim/director/fences.py`,
`survsim/eval/{alarms,alarm_card,evidence_pack,trackeval_bridge}.py`,
`survsim/experiments/__init__.py` (`RUNNERS`), `survsim/sensors/degrade.py`
(`PROFILES`), and `tests/test_catalogue_behaviours.py`.

## docs/03 — Behaviour & Intent Catalogue

* **Stale rows, no matching class**: `vendor`, `worker_patrol` (no `REGISTRY`
  entry at all — removed); `graffiti_vandalism` (class is `Vandalism`,
  registry key `vandalism`); `mass_rush` (class is `CrowdRush`, key
  `crowd_rush`); `drone_intrusion` (class is `DroneOverflight`, key
  `drone_overflight`, label `hostile.airspace.drone` not `hostile.airspace`).
  `assault_weapon_like` and `push_over_barrier` have no class at all —
  re-tagged "not yet" rather than deleted, since the row itself may still be
  wanted.
* **Classes with no catalogue row**: `fence_tailgate` and its twin
  `staff_escort` (H54 — the twin pairing the task asked to check was simply
  missing from the doc) and `vehicle_move` (background vehicle transit, twin
  of `vehicle_ram`'s cruise phase).
* Twin pairings verified correct where the doc already stated them:
  `patrol_guard` ↔ probe/cut/climb, `maintenance_visit` ↔ `zone_intrusion`.
  Added the missing `staff_escort` ↔ `fence_tailgate` pairing.
* Fence semantics (`fenced: false` opt-out, merged overlapping polygons, one
  gate per component) match `survsim/director/fences.py` exactly — no change
  needed there.
* `wildlife` row (non-person, MOT class 8/distractor, never a truth event)
  matches the `Wildlife` behaviour and its i-LIDS-distractor framing — no
  change needed.
* Count: `REGISTRY` has 50 distinct classes behind 55 catalogue names,
  matching `tests/test_catalogue_behaviours.py::test_the_catalogue_is_complete`
  (which already asserts 50 — the "still asserts 48" note in docs/11 is a
  separate, pre-existing staleness in a file this audit did not touch).

## docs/02 — Architecture

Missing entirely before this pass:
* **Fences** and **appearance epochs** as Director components (added to the
  pipeline diagram).
* **Alarm cards / evidence pack** (`eval/alarm_card.py`, `eval/evidence_pack.py`)
  and the **TrackEval bridge** (`eval/trackeval_bridge.py`) in the eval-stage
  box — the doc previously named only baselines and generic metrics.
* The **experiments framework** (`survsim/experiments/`, `RUNNERS` — detection,
  tracking, reid, alarms, night, dose, autocalib, evasion, ...).
* **Degrade profiles**: the doc described the pipeline stages but never
  enumerated the 7 shipped `PROFILES`, and did not flag that
  `cctv_night_ir`/`cctv_night_lowlight` are tuned against a 15-frame LLVIP
  slice (non-commercial, measure-only) and are overfit (H32/H36).
* **Licensing gate** (`licences.json`, `commercial_ml_ok`, CC0 default,
  MetaHuman opt-in) — present in CLAUDE.md and docs/11 but absent from the
  architecture doc.
* **Principles list** — docs/02 had none; CLAUDE.md's 7 non-negotiables plus
  the licensing rule are now mirrored as §7.

Backend section (§4) previously said "Implementations: `UnrealBackend`
(UnrealCV+ over TCP, batched commands)" as the primary description — **this
is the corrected-false claim CLAUDE.md itself flags**: the packaged
UnrealCV+ server hangs at frame 1 and executes nothing (docs/12). Rewrote §4
to describe the real route: UE 5.8 editor driven headless via job scripts
that write a result file, gated by `scripts/check_job_result.py` /
`scripts/check_render.py`.

## Tests run

* `pytest -q tests/test_catalogue_behaviours.py` — pass.
* `pytest -q tests/test_docs_retired_claims.py tests/test_docs_numbers_in_facts.py`
  ("both doc tests") — pass; neither test reads docs/02 or docs/03, so this
  pass adds no new coverage for the two files it edits (a gap, not fixed
  here — out of scope).

## Fixes

Docs only: `docs/02_ARCHITECTURE.md`, `docs/03_BEHAVIOUR_CATALOG.md` (Edit,
in place); this file; `docs/research/AUDIT_LEDGER.md`;
touched.
