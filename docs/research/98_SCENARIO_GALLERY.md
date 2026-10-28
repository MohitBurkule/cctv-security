# 98 · Scenario gallery — breadth, not just the 9 rendered scenarios

Before this pass, only 9 scenario yamls (`configs/scenarios/*.yaml`) had ever
been rendered for demos. That understates what the simulator can do: the
behaviour catalogue alone is 55 names / 50 classes (`docs/03_BEHAVIOUR_CATALOG.md`),
the scene generator has 6 site types (`survsim/generator/layout.py`), the
camera director has 6 tamper kinds (`survsim/director/camera_director.py`),
and the evasion taxonomy has 52 techniques (`survsim/director/evasion.py`).

Four galleries make that breadth visible directly, built by:

- `tools/scenario_gallery.py` -> `docs/research/demo/gallery/behaviour_gallery.{mp4,png}`
- `tools/site_gallery.py` -> `docs/research/demo/gallery/site_gallery.{mp4,png}`
- `tools/tamper_gallery.py` -> `docs/research/demo/gallery/tamper_gallery.png`
- `tools/evasion_gallery.py` -> `docs/research/demo/gallery/evasion_gallery.png`

Full listing of what each gallery contains: `docs/research/demo/gallery/README.md`.

## 1. Behaviour gallery

Every REGISTRY-implemented catalogue behaviour (55/55, 0 failed) run as an
18 s mock-backend scenario in one shared environment (gate, restricted zone +
asset, fenced perimeter with cuttable panel, blindspot, bench, wall, door),
capturing the last 3 s of `MockBackend.render_topdown`. Where the catalogue
names a hard-negative twin (e.g. `loiter`/`commute_wait`, `patrol_guard`/
`fence_climb`, `staff_escort`/`fence_tailgate`, `sit_rest`/`person_down`), both
agents run together in the tile. Tiled 4x3 per grid into
`behaviour_gallery.mp4`; all 55 final frames tiled 6xN into
`behaviour_gallery.png`.

This is a breadth demo, not a fidelity one: intent specs use generic defaults
(short durations, one shared site) rather than the tuned parameters a real
scenario config would use — see `configs/scenarios/disguise_and_tamper.yaml`
for what a hand-built scenario with a real hard-negative population looks like.

## 2. Site gallery

`survsim/generator/layout.py::build_layout(site_type, seed)` for all 6 site
types x seeds 1-3, plotted in plan view: building/prop footprints, entrances
(green triangles), and the installer-placed camera rig's frusta (cyan) from
`place_installer_cameras`. Confirms the generator produces genuinely different
layouts per seed (item counts range 85-254 across the 18 plans) and that
camera placement adapts to each site's geometry rather than using a fixed rig.

## 3. Tamper gallery

All 6 `TAMPER_KINDS` (`cover`, `spray`, `tilt`, `unplug`, `glare`, `defocus`) as
before/after stills on one real render frame
(`out/batch_v8/disguise_and_tamper_day/render/cam_gate/0019.png`). `defocus`
and `spray` call `survsim/sensors/degrade.py` directly (`defocus`, `lens_dirt`)
— **[code]**. `cover`/`unplug` (black frame), `glare` (blown-out highlight) and
`tilt` (affine warp, standing in for the camera's pose actually moving) are
**[emulated]** for this gallery: the mock backend's own tamper handling
changes camera *state* (the `blind` flag, live pose fed to GT) rather than
producing a rendered pixel effect, since the mock backend never renders RGB.
A real pixel-level tamper render needs the Unreal backend.

## 4. Evasion gallery

All 52 techniques from `evasion.py::BY_ID`, grouped by category, with the 6
techniques H47 actually pixel-rendered and measured against a zero-shot
detector marked (`hi_vis_worker`, `hood_up`, `slow_deliberate`, `crowd_cover`,
`wall_hugging`, and `reversible_jacket` as the closest id to H47's
`dark_lowcontrast`, which has no single technique id of its own). See
`docs/research/50_EVASION_ADVERSARIAL_ROBUSTNESS_AND_TAMPER.md` §6 for the
full literature mapping and `docs/research/32_EXPERIMENTS_LOG.md` H47 for the
measurement (verdict: NOT MET, 1/6 techniques cleared the -0.10 recall bar —
`crowd_cover`).

## Regenerating

```bash
source .venv/bin/activate
python tools/scenario_gallery.py   # ~2 min, CPU only
python tools/site_gallery.py       # ~10 s
python tools/tamper_gallery.py     # ~5 s
python tools/evasion_gallery.py    # ~2 s
```
