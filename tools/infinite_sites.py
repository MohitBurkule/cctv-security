#!/usr/bin/env python3
"""Demo segment 19 "infinite sites": N seeded scenes from the scene generator,
each rendered for ~3 s through the persistent Unreal editor (tools/render_run.py),
then a filling mosaic + a ~1 s/site fly-through.

    .venv/bin/python tools/infinite_sites.py prep  <i>      # scenario + mock run + export
    .venv/bin/python tools/infinite_sites.py render <i>     # one editor job + render gate
    .venv/bin/python tools/infinite_sites.py video [--n 32] # mp4 + contact sheet

Sites go to out/showcase/sites/<nn>_<type>_s<seed>/{scenario.yaml,run,set}.
The generator has 6 site families (survsim.generator.spec.SiteType); every seed
draws a different layout variant, rig and population — that is the claim shown.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "out" / "showcase" / "sites"
PY = sys.executable
FAMILIES = ["car_park", "perimeter_site", "retail_street", "transit_station",
            "office_building", "event_plaza"]
# (hour string, render_run --lighting, label)
TOD = [("11:00", "day", "day"), ("14:30", "day", "day"), ("19:15", "overcast", "dusk"),
       ("22:30", "night", "night")]
# Re-seeds after a failed gate: {index: seed}; recorded in the doc too.
_RS = OUT / "reseed.json"
RESEED: dict[int, int] = ({int(k): v for k, v in json.loads(_RS.read_text()).items()}
                          if _RS.is_file() else {})


def auto(i: int) -> int:
    """prep + render, re-rolling the env seed / camera bearing on near-field clutter."""
    s = site(i)
    for yaw_off, ds in ((0, 100), (0, 70), (90, 100), (180, 100), (270, 100), (90, 70)):
        if prep(i, yaw_off, ds):
            return 2
        for es in (s["seed"], s["seed"] + 1):
            rc = render(i, es)
            log = (s["dir"] / "render.log").read_text()
            if "first 10 m" not in log:
                meta = json.loads((s["dir"] / "site.json").read_text())
                meta.update(yaw_off=yaw_off, dist_scale=ds)
                (s["dir"] / "site.json").write_text(json.dumps(meta, indent=1))
                return rc
    return 3


def site(i: int) -> dict:
    fam = FAMILIES[i % len(FAMILIES)]
    seed = RESEED.get(i, 1000 + 37 * i)
    hour, light, tod = TOD[(i + i // 6) % len(TOD)]
    n_people = 3 + (seed * 7) % 6          # 3..8
    d = OUT / f"{i:02d}_{fam}_s{seed}"
    return {"i": i, "type": fam, "seed": seed, "hour": hour, "lighting": light, "tod": tod,
            "people": n_people, "dir": d}


def prep(i: int, yaw_off: int = 0, dist_scale: int = 100) -> int:
    import yaml

    from cctvsec.experiments import alarm_scale as AS
    from survsim.generator.spec import CameraPlan, PopulationPlan, SceneSpec, SiteSpec
    s = site(i)
    s["dir"].mkdir(parents=True, exist_ok=True)
    spec = SceneSpec(name=s["dir"].name, seed=s["seed"], duration_s=4, fps=10, engine="unreal",
                     site=SiteSpec(type=s["type"], footprint_m=(40, 30)),
                     cameras=CameraPlan(count=3, target_coverage=0.3, resolution=(640, 360)),
                     population=PopulationPlan(count=s["people"], evasion_techniques_per_actor=0))
    sc = AS._compose_valid(spec).scenario
    sc.population.hero = sc.population.hero[:8]
    d = sc.model_dump(mode="json", exclude_defaults=True)
    d.setdefault("population", {}).pop("background", None)
    d["population"].pop("generators", None)
    d["time_of_day"] = {"start": f"2026-09-27T{s['hour']}:00+00:00"}
    d["output"] = {"modalities": ["rgb"], "gt": ["mot", "events", "world_parquet", "calib"]}
    y = s["dir"] / "scenario.yaml"
    y.write_text(yaml.safe_dump(d, sort_keys=False, width=120))
    run = s["dir"] / "run"
    best = _run(y, run)
    # re-run with only the chosen camera: the editor's near-field check covers every
    # manifest camera, and one camera is all a tile shows
    d["n_rig_cameras"] = len(d.get("cameras", []))
    rig = d.pop("n_rig_cameras")
    d["cameras"] = [c for c in d["cameras"] if c["id"] == best[0]]
    # re-aim the rig camera at where people actually walked (keeps its bearing),
    # so a 160x90 tile shows people rather than a 20 px speck
    import math

    import numpy as np
    import pandas as pd
    w = pd.read_parquet(run / "gt" / "world.parquet")
    w = w[w["object_class"] == "person"] if "object_class" in w else w
    cx, cy = float(w["x"].median()), float(w["y"].median())
    spread = float(np.hypot(w["x"] - cx, w["y"] - cy).quantile(0.8))
    dist = min(22.0, max(9.0, 1.6 * spread + 4.0)) * dist_scale / 100.0
    m = d["cameras"][0]["mount"]
    m["yaw"] = (m["yaw"] + yaw_off) % 360
    yaw = math.radians(m["yaw"])
    m["pos"] = [cx - dist * math.cos(yaw), cy - dist * math.sin(yaw), 4.5]
    m["pitch"] = -round(math.degrees(math.atan2(4.5 - 0.9, dist)), 1)
    d["cameras"][0]["optics"] = {"hfov_deg": 62.0}
    y.write_text(yaml.safe_dump(d, sort_keys=False, width=120))
    import shutil
    shutil.rmtree(run)
    best = _run(y, run)
    meta = {k: (str(v) if isinstance(v, Path) else v) for k, v in s.items()}
    meta.update(camera=best[0], gt_rows=best[1], n_cameras=rig)
    (s["dir"] / "site.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))
    return 0


def _run(y: Path, run: Path):
    for cmd in (["survsim", "run", str(y), "--out", str(run)], ["survsim", "export", str(run)]):
        r = subprocess.run([str(ROOT / ".venv/bin" / cmd[0])] + cmd[1:], capture_output=True, check=False,
                           text=True, cwd=ROOT)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit(1)
    # the camera that sees the most people-frames
    import glob
    best, n = None, -1
    for f in glob.glob(str(run / "gt" / "mot_*.txt")):
        rows = len([ln for ln in Path(f).read_text().splitlines() if ln.strip()])
        if rows > n:
            best, n = Path(f).stem[4:], rows
    return best, n


def render(i: int, env_seed: int | None = None) -> int:
    s = site(i)
    meta = json.loads((s["dir"] / "site.json").read_text())
    env_seed = s["seed"] if env_seed is None else env_seed
    import shutil
    shutil.rmtree(s["dir"] / "set", ignore_errors=True)
    cmd = [PY, str(ROOT / "tools/render_run.py"), str(s["dir"] / "run"), "--frames", "30",
           "--cameras", meta["camera"], "--lighting", s["lighting"], "--wait", "600", "--rebuild-env",
           "--site", s["type"], "--env-seed", str(env_seed), "--entrance-gate", "warn",
           "--out", str(s["dir"] / "set" / "render")]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
    (s["dir"] / "render.log").write_text(r.stdout + r.stderr)
    gate = subprocess.run([PY, str(ROOT / "scripts/check_render.py"), str(s["dir"] / "set/render"),
                           "--gt", str(s["dir"] / "run")], capture_output=True, text=True, cwd=ROOT, check=False)
    (s["dir"] / "gate.txt").write_text(gate.stdout + gate.stderr)
    meta.update(env_seed=env_seed, render_rc=r.returncode, gate_rc=gate.returncode)
    (s["dir"] / "site.json").write_text(json.dumps(meta, indent=1))
    print(r.stdout[-600:])
    if "first 10 m" in r.stdout + r.stderr:
        print("NEAR_GEOMETRY")
    print("GATE", gate.returncode, "\n".join(l for l in gate.stdout.splitlines() if "FAIL" in l))
    return gate.returncode


FONT = "/usr/share/fonts/TTF/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
VARIANT_KEYS = ("street", "event", "shape", "boundary", "centrepiece")


def _ok_sites(n: int) -> list[dict]:
    out = []
    for d in sorted(OUT.glob("[0-9][0-9]_*")):
        m = d / "site.json"
        if not m.is_file():
            continue
        meta = json.loads(m.read_text())
        if meta.get("gate_rc") != 0:
            continue
        frames = sorted((d / "set" / "render" / meta["camera"]).glob("*.png"))
        if len(frames) < 30:
            continue
        env = json.loads((d / "set" / "env_plan.json").read_text())
        var = env.get("variant") or {}
        meta["variant"] = next(((f"{k} {var[k]}" if k == "shape" else str(var[k]))
                                for k in VARIANT_KEYS if k in var and var[k] not in ("none", None)), "")
        meta["frames"] = frames
        out.append(meta)
    return out[:n]


def _label(img, meta, big: bool):
    from PIL import ImageDraw, ImageFont
    dr = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    fs = 15 if big else (8 if img.size[1] >= 90 else 7)
    f = ImageFont.truetype(FONT_B if big else FONT, fs)
    t1 = f"{meta['type'].replace('_', ' ')}" + (f" / {meta['variant'].replace('_', ' ')}"
                                                if meta["variant"] else "")
    t2 = f"seed {meta['seed']}  {meta['n_cameras']} cams  {meta['tod']} {meta['hour']}"
    h = 2 * fs + 6
    dr.rectangle([0, H - h, W, H], fill=(0, 0, 0, 170))
    dr.text((3, H - h + 1), t1, font=f, fill=(255, 255, 255))
    dr.text((3, H - h + fs + 3), t2, font=ImageFont.truetype(FONT, fs), fill=(255, 215, 90))
    if big:
        dr.text((W - 70, 6), f"{meta['i'] + 1:02d} / {meta.get('of', 32)}", font=f, fill=(255, 255, 255))
    return img


def video(n: int = 32) -> int:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sites = _ok_sites(n)
    n = len(sites)
    # tiles keep 16:9: 4x4 of 160x90 up to 16 sites, 6x6 of 106x60 above that
    cols, rows = (4, 4) if n <= 16 else (6, 6)
    tw, th = 640 // cols, 360 // rows
    print(f"{n} sites -> {cols}x{rows} mosaic, tiles {tw}x{th}")
    cache = {}

    def tile(k, f):
        key = (k, f % 30)
        if key not in cache:
            im = Image.open(sites[k]["frames"][f % 30]).convert("RGB").resize((tw, th), Image.LANCZOS)
            cache[key] = _label(im, sites[k], False)
        return cache[key]

    frames = []
    fill_per = 2 if n > 16 else 4                       # frames per new tile (10 fps)
    total_fill = n * fill_per + 20
    hdr = ImageFont.truetype(FONT_B, 13)
    for f in range(total_fill):
        can = Image.new("RGB", (640, 360), (12, 12, 14))
        shown = min(n, f // fill_per + 1)
        for k in range(shown):
            can.paste(tile(k, f), ((k % cols) * tw, (k // cols) * th))
        ImageDraw.Draw(can).text((6, 346 - 0), "", font=hdr)
        dr = ImageDraw.Draw(can, "RGBA")
        dr.rectangle([0, 0, 372, 18], fill=(0, 0, 0, 180))
        dr.text((5, 2), f"{shown} generated sites, Unreal render (SIMULATED, CC0)", font=hdr, fill=(255, 255, 255))
        frames.append(can)
    for k, s in enumerate(sites):                       # fly-through, 0.9 s per site
        for f in range(9):
            im = Image.open(s["frames"][(f * 3) % 30]).convert("RGB").resize((640, 360))
            frames.append(_label(im, dict(s, i=k, of=n), True))
    card = Image.new("RGB", (640, 360), (10, 10, 12))
    mos = frames[total_fill - 1].resize((320, 180))
    card.paste(mos, (160, 30))
    dr = ImageDraw.Draw(card)
    fb, fr = ImageFont.truetype(FONT_B, 20), ImageFont.truetype(FONT, 14)
    dr.text((320, 240), f"{n} shown; each new seed gives another site", font=fb, fill=(255, 255, 255), anchor="mm")
    dr.text((320, 275), "every site generated from a seed (scene generator), CC0 assets",
            font=fr, fill=(220, 220, 220), anchor="mm")
    dr.text((320, 300), f"{len({s['type'] for s in sites})} site families x per-seed layout, rig, "
            "people and time of day", font=fr, fill=(160, 160, 160), anchor="mm")
    if n < 32:
        dr.text((320, 325), f"(32 seeded; {32 - n} failed the render gate and were dropped, 1 re-seed passed)",
                font=ImageFont.truetype(FONT, 11), fill=(140, 140, 140), anchor="mm")
    frames += [card] * 30
    tmp = OUT / "_frames"
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    for j, im in enumerate(frames):
        im.save(tmp / f"{j:05d}.png")
    dst = ROOT / "docs/research/demo/segments/19_infinite_sites.mp4"
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i",
                    str(tmp / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24",
                    "-preset", "slow", str(dst)], check=True)
    shutil.rmtree(tmp)
    print(f"{dst}: {len(frames) / 10:.1f} s, {dst.stat().st_size / 1e6:.2f} MB")
    # contact sheet: frame 15 of every site at 320x180
    cw, ch = 320, 180
    cols, rows = 8, -(-n // 8)
    sheet = Image.new("RGB", (cw * cols, ch * rows), (12, 12, 14))
    for k, s in enumerate(sites):
        im = Image.open(s["frames"][15]).convert("RGB").resize((cw, ch), Image.LANCZOS)
        sheet.paste(_label(im, dict(s, i=k, of=n), True), ((k % cols) * cw, (k // cols) * ch))
    g = ROOT / "docs/research/demo/gallery/infinite_sites.png"
    g.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(g, optimize=True)
    print(g, np.asarray(sheet).shape)
    return 0


if __name__ == "__main__":
    op = sys.argv[1]
    if op in ("prep", "render", "auto"):
        a = [int(x) for x in sys.argv[2:]]
        raise SystemExit({"prep": prep, "render": render, "auto": auto}[op](*a))
    if op == "video":
        raise SystemExit(video(int(sys.argv[2]) if len(sys.argv) > 2 else 32))
