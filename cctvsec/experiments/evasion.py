"""H47: renderable evasion techniques vs zero-shot person recall (32 §H47).

    python -m cctvsec.experiments.evasion build  [--config h47_evasion]   # scenarios + mock runs
    python -m cctvsec.experiments.evasion render [--only tech] [--seed s]  # one set at a time
    python -m cctvsec.experiments.evasion score                            # recall, bootstrap, Holm

Six walkers on parallel lanes across the smoke_yard geometry, 2 cameras. The
three appearance techniques re-render the control run (identical GT, only the
palette differs, via SURVSIM_OUTFIT_OVERRIDE); the three path/gait techniques
are their own mock runs from the same seed and spawn side.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
APPEARANCE = ("dark_lowcontrast", "hivis", "hood_up")
PATH = ("slow_deliberate", "crowd_cover", "wall_hugging")
TECHNIQUES = APPEARANCE + PATH

# Linear-RGB palette overrides (survsim/export/outfits.py colour space).
DARK = (0.012, 0.012, 0.014)
OUTFIT_OVERRIDES: dict[str, dict[str, Any]] = {
    "dark_lowcontrast": {"top": "black", "top_rgb": DARK, "bottom": "black", "bottom_rgb": DARK,
                         "shoes": "black", "shoes_rgb": (0.01, 0.01, 0.01), "sleeve": "long",
                         "sleeve_u": 0.80, "leg_cut": "trousers", "hem_h": 0.055},
    "hivis": {"top": "hivis_yellow", "top_rgb": (0.75, 0.80, 0.02), "sleeve": "long",
              "sleeve_u": 0.80},
    "hood_up": {"face_cover": {"kind": "hood", "rgb": (0.03, 0.03, 0.035)},
                "hair_rgb": (0.03, 0.03, 0.035)},
}

CAMERAS = [
    {"id": "cam_01", "type": "fixed_bullet", "mount": {"pos": [16.0, -12.0, 4.0], "yaw": 120, "pitch": -18},
     "optics": {"hfov_deg": 78}, "capture": {"res": [1280, 720], "fps": 10}},
    {"id": "cam_02", "type": "dome", "mount": {"pos": [-14.0, 6.0, 3.5], "yaw": -30, "pitch": -22},
     "optics": {"hfov_deg": 95}, "capture": {"res": [1280, 720], "fps": 10}},
]


def lanes(technique: str, seed: int, n: int = 6) -> list[float]:
    """Lane y (m) per walker. Control: spread across the yard's middle."""
    rng = random.Random(f"h47:lanes:{seed}")
    jit = [rng.uniform(-0.8, 0.8) for _ in range(n)]
    if technique == "wall_hugging":
        base = [-17.5, -16.3, -15.1, 15.1, 16.3, 17.5]
        return [b + 0.2 * j for b, j in zip(base, jit)]
    if technique == "crowd_cover":
        return [0.0 + 0.3 * j for j in jit]
    return [-10.0 + 4.0 * i + j for i, j in enumerate(jit)]


def scenario(technique: str, seed: int, duration_s: float = 30.0, n: int = 6) -> dict:
    """The scenario dict for one arm (control = "control")."""
    ys = lanes(technique, seed, n)
    speed = 0.6 if technique == "slow_deliberate" else 1.35
    spawns, exits, hero = [], [], []
    for i, y in enumerate(ys):
        east = i % 2 == 0          # alternate walking direction
        x0, x1 = (-15.0, 15.0) if east else (15.0, -15.0)
        if technique == "crowd_cover":
            x0, x1 = -15.0, 15.0   # one group, one direction, one spawn cluster
        spawns.append({"id": f"spawn.l{i}", "pos": [x0, round(y, 3), 0.0]})
        exits.append({"id": f"exit.l{i}", "pos": [x1, round(y, 3), 0.0]})
        hero.append({
            "id": f"walker_{i}", "role": "commuter",
            "body": {"height_m": round(1.62 + 0.05 * i, 2), "skin_tone": 1 + i},
            "gait": {"style": "slow" if technique == "slow_deliberate" else "normal",
                     "speed_mps": speed},
            "intent": [{"type": "transit", "from": f"spawn.l{i}", "to": f"exit.l{i}"},
                       {"type": "transit", "to": f"spawn.l{i}"}]})
    return {
        "schema_version": 1, "name": f"h47_{technique}_s{seed}", "seed": int(seed),
        "duration_s": float(duration_s), "fps": 10, "engine": "mock",
        "environment": {"id": "smoke_yard", "zones": [
            {"id": "zone.yard", "tag": "public",
             "polygon": [[-20, -20], [20, -20], [20, 20], [-20, 20]]}],
            "spawn_points": spawns, "exits": exits},
        "cameras": CAMERAS, "population": {"hero": hero},
        "output": {"modalities": ["rgb"], "gt": ["mot", "events", "world_parquet", "calib"]},
    }


def run_of(technique: str) -> str:
    """Appearance techniques share the control run's GT."""
    return "control" if technique in APPEARANCE else technique


# ------------------------------------------------------------------ statistics


def frame_hits(gt_rows: dict[int, list], det: dict[int, tuple[list, list]], min_h: float = 20.0,
               thr: float = 0.5) -> list[tuple[int, int]]:
    """Per frame (tp, n_gt) for GT boxes >= min_h px; frames with no such GT dropped."""
    from tools.eval_recall import match_frame
    out = []
    for f, gts in sorted(gt_rows.items()):
        gts = [g for g in gts if g[3] >= min_h]
        if not gts:
            continue
        boxes, scores = det.get(f, ([], []))
        tp, _fp, _u = match_frame(gts, boxes, scores, thr)
        out.append((tp, len(gts)))
    return out


def read_visible_mot(path: Path) -> dict[int, list]:
    """MOT rows -> {frame: [[x, y, w, h], ...]}; conf 0 (no visible pixels) dropped."""
    gt: dict[int, list] = {}
    for line in Path(path).read_text().splitlines():
        p = line.strip().split(",")
        if len(p) >= 7 and float(p[6]) > 0:
            gt.setdefault(int(float(p[0])), []).append([float(v) for v in p[2:6]])
    return gt


def pooled_recall(strata: dict[Any, np.ndarray]) -> float:
    tp = sum(float(a[:, 0].sum()) for a in strata.values())
    n = sum(float(a[:, 1].sum()) for a in strata.values())
    return tp / n if n else float("nan")


def bootstrap_delta(tech: dict[Any, np.ndarray], ctrl: dict[Any, np.ndarray], n_boot: int = 2000,
                    seed: int = 0, cluster: str = "clip") -> dict[str, float]:
    """Δ = R_tech − R_ctrl, paired-resampled, arms sharing the resample draw.

    Each dict maps stratum (seed, camera) -> array (n_frames, 2) of (tp, n_gt).

    ``cluster="clip"`` (the default) resamples whole (seed, camera) *clips* with
    replacement — the unit AUDIT_H47 §2 found was needed, since frames of a 30 s
    clip are strongly autocorrelated and a frame-level resample understates the
    true variance (a clip with perfectly correlated frames gives a frame CI that
    is too narrow — see test_bootstrap_clip_vs_frame_cluster). ``cluster="frame"``
    keeps the previous (too-narrow-for-clip-clustered-data) behaviour and must be
    requested explicitly.
    """
    rng = np.random.default_rng(seed)
    d0 = pooled_recall(tech) - pooled_recall(ctrl)
    ds = np.empty(n_boot)
    if cluster == "clip":
        keys = list(tech)
        nk = len(keys)
        for b in range(n_boot):
            pick = keys if nk == 0 else [keys[i] for i in rng.integers(0, nk, nk)]
            r = []
            for arm in (tech, ctrl):
                tp = n = 0.0
                for k in pick:
                    s = arm[k].sum(axis=0)
                    tp, n = tp + s[0], n + s[1]
                r.append(tp / n if n else np.nan)
            ds[b] = r[0] - r[1]
    elif cluster == "frame":
        for b in range(n_boot):
            r = []
            for arm in (tech, ctrl):
                tp = n = 0.0
                for a in arm.values():
                    idx = rng.integers(0, len(a), len(a))
                    s = a[idx].sum(axis=0)
                    tp, n = tp + s[0], n + s[1]
                r.append(tp / n if n else np.nan)
            ds[b] = r[0] - r[1]
    else:
        raise ValueError(f"cluster must be 'clip' or 'frame', got {cluster!r}")
    return {"delta": float(d0), "lo": float(np.nanpercentile(ds, 2.5)),
            "hi": float(np.nanpercentile(ds, 97.5)),
            "p_one_sided": float((np.sum(ds >= 0) + 1) / (n_boot + 1))}


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (monotone)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def verdict(deltas: dict[str, dict], adj: dict[str, float], bar: float = -0.10,
            alpha: float = 0.05) -> dict[str, Any]:
    counted = [k for k, d in deltas.items() if d["delta"] <= bar and adj[k] < alpha]
    need = (len(deltas) + 1) // 2
    return {"counted": counted, "need": need, "met": len(counted) >= need}


# ------------------------------------------------------------------ pipeline


def _paths(cfg: dict) -> tuple[Path, Path]:
    out = ROOT / cfg.get("out", "out/experiments/h47_evasion")
    return out / "runs", out / "sets"


def cmd_build(cfg: dict) -> None:
    runs, _ = _paths(cfg)
    for seed in cfg["seeds"]:
        for tech in ("control",) + PATH:
            d = runs / f"{tech}_s{seed}"
            if (d / "unreal" / "manifest.json").is_file():
                continue
            d.mkdir(parents=True, exist_ok=True)
            y = d.parent / f"{tech}_s{seed}.yaml"
            y.write_text(yaml.safe_dump(scenario(tech, seed, cfg["duration_s"]), sort_keys=False))
            sv = str(Path(sys.executable).parent / "survsim")
            subprocess.run([sv, "run", str(y), "--out", str(d)], check=True)
            subprocess.run([sv, "export", str(d)], check=True)
            print("built", d)


def cmd_render(cfg: dict, only: str | None, seed_only: int | None) -> None:
    runs, sets = _paths(cfg)
    for seed in cfg["seeds"]:
        if seed_only is not None and seed != seed_only:
            continue
        for tech in ("control",) + TECHNIQUES:
            if only and tech != only:
                continue
            s = sets / f"{tech}_s{seed}"
            if (s / "check_render.txt").is_file() and (s / "render_result.json").is_file():
                continue
            env = dict(os.environ)
            if tech in OUTFIT_OVERRIDES:
                ov = s.parent / f"override_{tech}.json"
                ov.parent.mkdir(parents=True, exist_ok=True)
                ov.write_text(json.dumps({"all": OUTFIT_OVERRIDES[tech]}))
                env["SURVSIM_OUTFIT_OVERRIDE"] = str(ov)
            cmd = [sys.executable, str(ROOT / "tools/render_run.py"), str(runs / f"{run_of(tech)}_s{seed}"),
                   "--frames", str(int(cfg["duration_s"] * 10)), "--id-mask", "--lighting", "day",
                   "--out", str(s / "render"), "--wait", "1500", "--entrance-gate", "warn"]
            print("render", tech, seed, flush=True)
            s.mkdir(parents=True, exist_ok=True)
            for sub in ("unreal", "calib"):     # survsim.gt.amodal reads <set>/unreal, <set>/calib
                if not (s / sub).exists():
                    (s / sub).symlink_to((runs / f"{run_of(tech)}_s{seed}" / sub).resolve())
            used = vram_used_mb()
            if used > cfg.get("vram_start_max_mb", 6000):
                print(f"VRAM guard: {used} MB in use > {cfg.get('vram_start_max_mb', 6000)}; not starting")
                return
            with open(s.parent / f"{tech}_s{seed}.log", "w") as log:
                subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
            g = subprocess.run([sys.executable, str(ROOT / "scripts/check_render.py"), str(s / "render"),
                                "--gt", str(s)], capture_output=True, text=True, check=False)
            (s / "check_render.txt").write_text(g.stdout + g.stderr)
            print("gate", tech, seed, "PASS" if gate_passed(s) else "FAIL", flush=True)
            return   # one set per call: the caller checks VRAM/gate between sets


def vram_used_mb() -> int:
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, check=True).stdout
        return int(o.split()[0])
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        return 0


def gate_passed(set_dir: Path) -> bool:
    """The render gate's summary line ("PASS: 0 failed of N checks")."""
    f = set_dir / "check_render.txt"
    return f.is_file() and any(line.startswith("PASS:") for line in f.read_text().splitlines())


def detections(model_path: str, frames: list[Path]) -> dict[int, tuple[list, list]]:
    from ultralytics import YOLO
    m = YOLO(model_path)
    out = {}
    for p in frames:
        r = m.predict(str(p), classes=[0], conf=0.25, verbose=False, device=os.environ.get("H47_DEVICE", "cpu"), imgsz=1280)[0]
        b = r.boxes.xyxy.cpu().numpy()
        out[int(p.stem)] = ([[x0, y0, x1 - x0, y1 - y0] for x0, y0, x1, y1 in b],
                            r.boxes.conf.cpu().numpy().tolist())
    return out


def cmd_score(cfg: dict) -> dict:
    _runs, sets = _paths(cfg)
    out = sets.parent
    cache = out / "det_cache"
    cache.mkdir(exist_ok=True)
    gate = {}
    per: dict[str, dict[str, dict]] = {}
    for model in cfg["models"]:
        per[model] = {}
        for tech in ("control",) + TECHNIQUES:
            strata = {}
            for seed in cfg["seeds"]:
                s = sets / f"{tech}_s{seed}"
                ok = gate_passed(s)
                gate[f"{tech}_s{seed}"] = ok
                if not ok:
                    continue
                for cam in cfg["cameras"]:
                    gt = read_visible_mot(s / "gt" / f"mot_{cam}.txt")
                    cf = cache / f"{Path(model).stem}_{tech}_s{seed}_{cam}.json"
                    if cf.is_file():
                        det = {int(k): v for k, v in json.loads(cf.read_text()).items()}
                    else:
                        frames = sorted((s / "render" / cam).glob("*.png"))
                        det = detections(str(ROOT / model), frames)
                        cf.write_text(json.dumps({k: [np.asarray(v[0]).tolist(), v[1]]
                                                  for k, v in det.items()}))
                    # MOT frames are 1-based; render files are 0-based GT frame numbers.
                    det1 = {k + 1: v for k, v in det.items()}
                    strata[(seed, cam)] = np.array(frame_hits(gt, det1) or [(0, 0)], float)
            per[model][tech] = strata
    res: dict[str, Any] = {"config": {k: v for k, v in cfg.items() if not k.startswith("_")},
                           "gate": gate, "models": {}}
    for model, arms in per.items():
        ctrl = arms["control"]
        m: dict[str, Any] = {"recall": {t: pooled_recall(a) if a else None for t, a in arms.items()},
                             "gt_person_frames": {t: int(sum(a[:, 1].sum() for a in v.values()))
                                                  for t, v in arms.items()},
                             "per_camera": {t: {f"s{k[0]}_{k[1]}": float(a[:, 0].sum() / max(1, a[:, 1].sum()))
                                                for k, a in v.items()} for t, v in arms.items()},
                             "delta": {}, "delta_frame_level": {}}
        for t in TECHNIQUES:
            if arms.get(t):
                keys = set(arms[t]) & set(ctrl)
                a_t = {k: arms[t][k] for k in keys}
                a_c = {k: ctrl[k] for k in keys}
                # Clip-level (resample seed×camera clips) is the primary CI: AUDIT_H47 §2
                # found the frame-level resample too narrow for clip-clustered data. The
                # frame-level CI is kept under "delta_frame_level" for comparison only.
                m["delta"][t] = bootstrap_delta(a_t, a_c, cfg.get("n_boot", 2000),
                                                cfg.get("seed", 47), cluster="clip")
                m["delta_frame_level"][t] = bootstrap_delta(a_t, a_c, cfg.get("n_boot", 2000),
                                                            cfg.get("seed", 47), cluster="frame")
        adj = holm({t: d["p_one_sided"] for t, d in m["delta"].items()})
        for t in adj:
            m["delta"][t]["p_holm"] = adj[t]
        m["verdict"] = verdict(m["delta"], adj)
        res["models"][Path(model).stem] = m
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: {"recall": v["recall"], "delta": v["delta"], "verdict": v["verdict"]}
                      for k, v in res["models"].items()}, indent=1, default=str))
    return res


def cmd_figures(cfg: dict, frame: int = 120, seed: int = 1) -> None:
    """figures/fig_h47.png (Δ recall ± CI) and figures/h47_examples.png (contact sheet)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image, ImageDraw
    _, sets = _paths(cfg)
    res = json.loads((sets.parent / "results.json").read_text())
    figdir = ROOT / "docs/research/figures"
    fig, ax = plt.subplots(figsize=(7, 3.6))
    models = list(res["models"])
    for j, mname in enumerate(models):
        d = res["models"][mname]["delta"]
        ts = [t for t in TECHNIQUES if t in d]
        x = np.arange(len(ts)) + (j - (len(models) - 1) / 2) * 0.3
        y = np.array([d[t]["delta"] for t in ts])
        err = np.array([[y[i] - d[t]["lo"], d[t]["hi"] - y[i]] for i, t in enumerate(ts)]).T
        ax.errorbar(x, y, yerr=err, fmt="o", capsize=3, label=mname)
    ax.axhline(0, color="#888", lw=0.8)
    ax.axhline(-0.10, color="#c33", lw=0.8, ls="--", label="bar -0.10")
    ax.set_xticks(np.arange(len(TECHNIQUES)), TECHNIQUES, rotation=20, fontsize=8)
    ax.set_ylabel("Δ recall vs control (95 % CI)")
    ax.set_title("H47: evasion technique vs zero-shot person recall (3 seeds × 2 cams)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figdir / "fig_h47.png", dpi=130)
    tw, th = 480, 270
    rows = ("control",) + TECHNIQUES
    sheet = Image.new("RGB", (tw * 2 + 150, th * len(rows)), "white")
    dr = ImageDraw.Draw(sheet)
    for r, t in enumerate(rows):
        dr.text((6, r * th + th // 2), t, fill="black")
        for c, cam in enumerate(cfg["cameras"]):
            f = sets / f"{t}_s{seed}" / "render" / cam / f"{frame:04d}.png"
            if f.is_file():
                sheet.paste(Image.open(f).convert("RGB").resize((tw, th)), (150 + c * tw, r * th))
    sheet.save(figdir / "h47_examples.png")
    print("wrote", figdir / "fig_h47.png", figdir / "h47_examples.png")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["build", "render", "score", "figures"])
    ap.add_argument("--config", default="h47_evasion")
    ap.add_argument("--only", default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from cctvsec.experiments import load_config
    cfg = load_config(a.config)
    if a.step == "build":
        cmd_build(cfg)
    elif a.step == "render":
        cmd_render(cfg, a.only, a.seed)
    elif a.step == "score":
        cmd_score(cfg)
    else:
        cmd_figures(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
