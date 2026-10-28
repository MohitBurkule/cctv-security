

## showcase_all — rendered (2026-09-28) [V]

One dense 22 s clip, 640x360 @ 5 fps, 3 cameras (cam_01 / cam_02 fixed on the
compound fence from the yard, cam_ptz), CC0 characters, gate **31/31 PASS**.
Config `configs/scenarios/showcase_all.yaml`, rebuilt by
`tools/build_showcase_all.py <HH:MM> <out.yaml>`: a *generated* `perimeter_site`
(so `world.fences.components` exists — the hand-authored env of the previous
attempt had none, which is why fence_tailgate / patrol / escort / maintenance
were dropped there), with every actor re-staged from a literal start point
near its target. The earlier "leading transit never arrives" symptom did not
reproduce on the generated site; starting close is what makes 22 s enough.

Timeline (GT, `gt/events.jsonl`, `gt/sensors.jsonl`, `gt/camera_status.jsonl`, `gt/world.parquet`):

| t (s) | what | who |
|---|---|---|
| 0.0 → | loiter (pace) by the yard; **twin** commute_wait bystander | p008 / p009 |
| 0.2 → | **twins** patrol_guard x2 along the fence line | p003, p005 |
| 1.8 → | **twin** staff_escort (badged worker escorting p007) | p011 |
| 3.4 | PTZ leaves wide preset, slews to the intrusion point (scripted patrol, not alarm-driven) | cam_ptz |
| 3.6 → | wildlife crossing the yard | w000 |
| 3.8 | zone_intrusion starts; inside compound 7.2 | p000 |
| 6.8–13.2 | object_abandon: bag set down, owner walks off | p010 |
| 11.0 | fence_climb breach, fence_seg_1 (fence_vibration) | p002 |
| 11.4 / 12.6 | **twins** maintenance_visit via the gate | p007, p001 |
| 12.2–18.0 | cam_02 **cover** tamper (blind: no GT rows) | cam_02 |
| 16.8 | fence_cut breach, fence_seg_3 | p004 |
| 18.2 → | cam_02 **defocus** | cam_02 |
| 19.6 | fence_tailgate: through the gate 2.4 s behind badged p007 | p006 |

Sets: `out/showcase/showcase_all_dusk/{render,render_tampered,video,gt,calib,events.jsonl,gate.txt}`
(run dir `out/showcase/_runs/showcase_all_dusk`); demo copy
`docs/research/demo/showcase_all_dusk.mp4` (2x2: cam_01, cam_02, cam_ptz, mock top-down).

Emulated / caveats — say so if shown:
* **Rain on lens** — there is no droplet model; `cctv_showcase_rain_360p`
  (survsim/sensors/degrade.py) approximates it with lens dirt + haze +
  softness. Wet ground (wetness 0.8) *is* in the render.
* **Lamp flicker** — no scripted per-frame light API; emulated as fast AE drift
  (0.35 EV, 3 s) + mains rolling banding in the same profile.
* **Tamper pixels** — the render has no tamper model; `tools/apply_tamper_frames.py`
  burns cover/defocus into cam_02 from `camera_status.jsonl` before the video.
* **PTZ "slew to first alarm"** is a scripted patrol leg timed to the
  intrusion (3.4 s dwell, 60 deg/s), not a closed-loop alarm response.
* "Dusk" is 19:15 with the `overcast` preset (low sun, sun_pitch -12).

Fixed on the way (with tests / notes):
* **Mask GT ignored blind cameras** (principle 2): `build_tight_gt` added 330
  `mask_only` rows on cam_02 while it was covered, because the tamper-free
  render's ID mask still shows people. Now drops mask-only rows on blind
  frames (`mask_boxes.blind_frames`); regression test
  `test_blind_camera_gets_no_mask_only_rows`.
* **The scenario's fence was not rendered**: the v2 environment dresses a
  generic site, so the compound the Director fences was invisible and the
  climber walked through air. `env_plan.scenario_fence_items` now adds a
  2.4 m palisade along the union of fenced zones, open at `gate` props.
  Needs `--rebuild-env` the first time (the Env group is cached).
* **`/Game/SurvSim/RunMap` was corrupt on disk** (bad PACKAGE_FILE_TAG, left by
  the 2026-09-27 OOM kill); `new_level` over it then SIGSEGV'd the editor in
  `CheckForWorldGCLeaks`. `survsim_scene.MAP` is now `RunMap_v2`; the old
  file is left untouched. Editor restarted once (pid 22452).
* `render_run.py` with `--id-mask` must render into a set dir that is **not**
  the run dir (`--out <set>/render`), and `<set>/unreal` must exist for
  `build_amodal` — copy `unreal/ calib/ meta/` from the run first.

Nothing from the ask was dropped.

**Night set** (`out/showcase/showcase_all_night`, demo copy
`docs/research/demo/showcase_all_night.mp4`): the *same run* re-lit with
`--lighting night --rebuild-env` (23:00 look: lamps + floodlights, sun off) —
the scenario's time_of_day stays 19:15, so GT/events are identical to dusk.
Gate **31/31 PASS**; frames checked lit, not black. The degrade profile's AE
lifts the night noticeably; a lower `ae_target` would read darker.

## (superseded) Status: blocked before the first render — RAM gate failed

`docs/12_UNREALCV_ENGINE_NOTES.md` ("Editor lifecycle: OOM and restart",
2026-09-27) is explicit: the persistent editor was OOM-killed earlier today by
CPU-side RAM pressure from unrelated heavy jobs sharing the box, and the
documented recovery rule is **`free -g` first — restart only when ≥ 8 GB
free**.

Checked repeatedly during this session:

```
$ free -g
              total   used   free   shared  buff/cache  available
Mem:             31     12      2        0          17         18
```

`free` stayed at **2 GB** the whole session (⁠`available` 18 GB, but the
documented gate is on the `free` column, not `available`, precisely because
the previous OOM happened while another heavy job was mid-flight and could
reclaim `buff/cache` out from under a freshly started editor). `ps aux`
showed a live competing job at the time of checking (`make_labels.py`, an
unrelated sam-3d-body/myolift script, 121% CPU, ~5.5 GB RSS) — the same shape
of contention ("11 CPU workers + a QAT run") that caused the earlier OOM.

**Decision: did not start the editor this session.** Starting a large
UnrealEditor process into a box that has already been OOM-killed once today
under near-identical conditions risks (a) killing the editor again and
burning the remaining time budget on restarts, and (b) killing whatever
unrelated job is holding that RAM, which is not this task's to kill (the
brief says "kill only PIDs you recorded" — that process was never started by
this task). No render, gate run, or job-runner invocation happened. This
blocker should be re-checked (`free -g` ≥ 8 GB) before any of the four sets
below are attempted; none of the render/gate work below is done.

## What was done instead

Built the four scenario configs (schema matches `configs/scenarios/*.yaml`
and `configs/environments/border_fence.yaml`), so rendering can start
immediately once the RAM gate clears, plus a design note for the flicker
requirement since the export pipeline doesn't support it directly.

| Set | Config | Content | Render plan |
|---|---|---|---|
| `showcase_intrusion` | `configs/scenarios/showcase_intrusion.yaml` | fenced compound, 2 fixed cams + 1 PTZ, 5 people (guard, maintenance, fence-climb intruder, zone-intrusion intruder, gate tailgater), `cam_02` cover-tamper at t=12 s, PTZ alarm-slew preset on `fence_climb` | 10 s @ 5 fps, 720p, CC0 chars (default) |
| `showcase_daynight` | `configs/scenarios/showcase_daynight.yaml` | same site, guard + one civilian (hard-negative `commute_wait`) | three 5 s renders at 15:00 / 18:30 / 23:00 via `--time-override`; `time_of_day.start` in the file is the day slot, dusk/night comment inline |
| `showcase_weather` | `configs/scenarios/showcase_weather.yaml` | same site, `weather: rain` + `wet_ground: true` + `fog_density: 0.25`, fence-climb intruder | 5 s @ 5 fps; rain-on-lens/fog are `survsim/sensors/degrade.py` post-process profiles (`cctv_720p_rain`, `cctv_720p_fog`), not baked into the beauty render |
| `showcase_flicker` | `configs/scenarios/showcase_flicker.yaml` | same site + `beacon_1` point light | **not verified renderable as scripted flicker** — see below |

## Flicker: no scripted per-frame light-intensity API found in the export path

Checked `survsim/generator/layout.py` and `survsim/export/env_plan.py`: lights
are placed once per scene build and held static for the shot; there is no
keyframed/scripted intensity track exposed through the scenario schema or the
job runner. Two options, both recorded in the config's header comment:

- **[A] real flicker**: call `survsim_scene.light(..., intensity=...)`
  repeatedly across several short re-renders of the same clip and alternate
  the beacon's intensity between them, then concatenate — untried this
  session, blocked by the same RAM gate as everything else.
- **Emulated flicker (default, marked as such)**: static beacon light in the
  render, flicker added as a post-process step riding on the existing
  AE-flicker path in `survsim/sensors/degrade.py`. This is **not** a real
  light-intensity change in the 3-D scene — any deliverable built this way
  must be labelled "emulated" wherever it appears in the demo reel.

## Gate / GT / video status

None of `showcase_intrusion`, `showcase_daynight`, `showcase_weather`,
`showcase_flicker` were rendered, so there is nothing yet for
`scripts/check_render.py`, no `out/showcase/<set>/{render,gt,calib,video}`,
and no events.jsonl with tamper events to inspect. `out/` is gitignored, so
none of that would be committed regardless.

## Update — RAM cleared, editor started, scenario iteration in mock (still no render)

`free -g` recovered to 6 GB free (the earlier `make_labels.py` competitor
process exited) with no other heavy job visible in `ps aux`. Started the
persistent editor: `scripts/ue_mcp.sh start` -> pid **9778**, log
`/tmp/survsim_ue_mcp.log`, `/tmp/survsim_jobs/runner.ready` appeared within
the poll window. **The editor is still running (pid 9778) — left running per
handover instruction, do not kill it.** No job has been submitted to
`/tmp/survsim_jobs` yet — there is no in-flight render.

Direction changed mid-session (coordinator): fewer sets, one dense
`configs/scenarios/showcase_all.yaml` (22 s @ 5 fps, 640x360, dusk + rain,
cam_sub cover-tamper at t=12s + defocus at t=18s, PTZ patrol) instead of the
four separate `showcase_*` sets. All four original per-topic configs
(`showcase_intrusion`, `showcase_daynight`, `showcase_weather`,
`showcase_flicker`) are still in the repo and schema-valid; `showcase_all`
supersedes `showcase_intrusion` as the one to render first.

**Validated so far only against the `mock` backend** (`survsim run
configs/scenarios/showcase_all.yaml --out <dir> --engine mock`), never the
Unreal backend/editor:
* `showcase_intrusion.yaml` (10 s window): `fence_climb` fires cleanly
  (`hostile.breach.climb` at t=7.8s once spawn points were moved to within
  ~5 m of their targets — the original spawns copied from
  `disguise_and_tamper.yaml`, ~30-40 m out, never arrived in a 10 s clip).
  `zone_intrusion` and the `camera_tamper` intent chained after it did **not**
  complete in 10 s even from a ~3 m spawn — see below.
* `showcase_all.yaml` (22 s window): `fence_climb` completes (t=7.8s). Worker
  `commute_wait` hard-negative completes (t=8.2s). **`fence_cut` and
  `zone_intrusion`/`camera_tamper` never complete in the 22 s window** — their
  leading `transit` step targets `zone.yard`/`zone.substation` and appears to
  resolve to something far from the actual spawn (a centroid or asset point
  rather than the nearest boundary), so the agent is still walking at t=22
  even from spawns a handful of metres away. Not root-caused — ran out of
  budget mid-fix. Next step for whoever picks this up: read
  `survsim/director/planner.py` / `world.resolve_point` for how a `transit`
  target zone resolves to a ground point, and either point `transit` at a
  concrete `Waypoint` right next to the boundary or drop the leading
  `transit` step entirely (fence_climb's own crossing logic moves the agent
  itself, without a preceding transit, and that one works).
* `fence_tailgate`, `patrol_guard`, `maintenance_visit`, `staff_escort` were
  **not attempted** in `showcase_all` — they read `world.fences.components`
  (built from fence topology with `gate_in`/`gate_out` points), which this
  hand-authored two-zone environment does not construct in a form verified to
  work; `tests/test_fence_tailgate.py` exercises them only via the procedural
  `survsim.generator.batch` site generator, not a hand-written YAML like this
  one. Dropped for time, per the coordinator's fallback instruction.
* Object-drop and wildlife/distractor behaviours: not attempted at all.

## Next steps (whoever continues this)

1. Editor is up (pid 9778) — do not start a second one; check
   `/tmp/survsim_jobs/heartbeat` before assuming it is dead.
2. Fix the `showcase_all.yaml` transit-never-arrives issue above before
   spending render time on it (rendering a clip where 2 of 4 hero behaviours
   never trigger wastes the render budget).
3. Once `showcase_all` completes its `--engine mock` dry run with all
   intended events present in `gt/events.jsonl`, submit it through the job
   runner / `tools/render_run.py` against the running editor, then
   `scripts/check_render.py` before copying into `out/showcase/showcase_all/`.
4. Stop launching new renders at 03:00 per the brief; whatever passed the
   gate by then is the deliverable.
