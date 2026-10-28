"""H13: does docs/15 image-statistics distance to MOT20 predict transfer?

For every distinct (batch, run, raw|degraded) synthetic source: mean |z| of the
13 frame stats vs MOT20-02 (the H6d measure), and the real MOT20-02 AP@640 of a
yolov8n fine-tuned for a few epochs on a seeded 300-frame sample of it. Then
Spearman(mean |z|, AP) with a bootstrap CI and permutation p.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import batch_cameras, rpath, wait_for_gpu, write_json
from .inference import spearman


def enumerate_sources(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(eligible distinct sources, rejected with reason). Deterministic order."""
    ok, rej, seen = [], [], {}
    for b in cfg["batches"]:
        bd = rpath(b)
        for run in sorted(p.name for p in bd.iterdir() if p.is_dir()):
            if any(x in run for x in cfg["exclude_run_substrings"]):
                rej.append({"batch": b, "run": run, "why": "excluded by name"})
                continue
            for src in ("raw", "degraded"):
                cams = batch_cameras(bd, run, src)
                frames = [(c, f, p) for c, v in cams.items() for f, p in sorted(v["frames"].items()) if f >= 1]
                key = {"batch": b, "run": run, "source": src, "frames": len(frames)}
                if len(frames) < cfg["train_frames"]:
                    rej.append({**key, "why": f"< {cfg['train_frames']} frames"})
                    continue
                probe = sorted(frames, key=lambda x: (x[0], x[1]))[len(frames) // 2][2]
                h = hashlib.md5(Path(probe).read_bytes()).hexdigest()
                if h in seen:
                    rej.append({**key, "why": f"pixel duplicate of {seen[h]}"})
                    continue
                seen[h] = f"{b}/{run}/{src}"
                ok.append(key)
    return ok, rej


def _stats(paths, ref, rng, n):
    import cv2

    from survsim.realism.stats import FrameStats, band, frame_stats
    pick = [paths[i] for i in sorted(rng.choice(len(paths), min(n, len(paths)), replace=False))]
    rows = [frame_stats(cv2.imread(str(p))).as_dict() for p in pick]
    s = {k: band(r[k] for r in rows) for k in FrameStats.keys()}  # noqa: SIM118
    z, inb = {}, 0
    for k in FrameStats.keys():  # noqa: SIM118
        r = ref[k]
        z[k] = round((s[k]["median"] - r["median"]) / max(r["p90"] - r["p10"], 1e-9), 3)
        inb += int(r["p10"] <= s[k]["median"] <= r["p90"])
    return {"z": z, "mean_abs_z": round(float(np.mean(np.abs(list(z.values())))), 4), "in_band": inb}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import cv2

    from survsim.realism.stats import FrameStats, band, frame_stats
    from .detection import _eval_manifests, eval_arm, train_arm
    sources, rejected = enumerate_sources(cfg)
    n_all = len(sources)
    if len(sources) > cfg["max_sources"]:
        rng = np.random.default_rng(int(cfg["seed"]))
        sources = [sources[i] for i in sorted(rng.choice(len(sources), cfg["max_sources"], replace=False))]
    ref_dir = rpath(cfg["mot20_root"]) / "train" / cfg["reference"] / "img1"
    ref_rows = [frame_stats(cv2.imread(str(p))).as_dict()
                for p in sorted(ref_dir.glob("*.jpg"))[:300][::300 // cfg["stats_frames"]][:cfg["stats_frames"]]]
    ref = {k: band(r[k] for r in ref_rows) for k in FrameStats.keys()}  # noqa: SIM118
    eval_dirs = _eval_manifests(cfg, out)
    bands = [tuple(b) for b in cfg["height_bands"]]
    rows = []
    for s in sources:
        name = f"{Path(s['batch']).name}__{s['run']}__{s['source']}"
        ap_file = out / "arms" / f"{name}.json"
        if ap_file.is_file():
            rows.append(json.loads(ap_file.read_text()))
            continue
        bd = rpath(s["batch"])
        cams = batch_cameras(bd, s["run"], s["source"])
        paths = [p for v in cams.values() for f, p in sorted(v["frames"].items()) if f >= 1]
        rec: dict[str, Any] = {**s, "name": name,
                               "stats": _stats(paths, ref, np.random.default_rng(int(cfg["seed"])),
                                               cfg["stats_frames"])}
        c2 = {**cfg, "batch_dir": s["batch"], "synthetic_train_runs": [s["run"]],
              "synthetic_val_runs": [s["run"]], "val_sources": [{"source": s["source"], "stride": 100, "phase": 50}]}
        arm = {"name": name, "seed": int(cfg["train"]["seed"]),
               "train": {"synthetic": [{"source": s["source"], "stride": 1, "phase": 0}],
                         "synthetic_limit": int(cfg["train_frames"])}}
        work = (out / "work" / name).resolve()
        work.mkdir(parents=True, exist_ok=True)
        rec["gpu_wait"] = wait_for_gpu(min_free_mib=int(cfg.get("min_free_mib", 2048)))
        w = train_arm(arm, c2, work, rec)
        eval_arm(str(w), eval_dirs, cfg["eval_imgsz"], work, rec, set(), bands)
        write_json(ap_file, rec)
        rows.append(rec)
    key = f"mot20_02@{cfg['eval_imgsz'][0]}"
    x = [r["stats"]["mean_abs_z"] for r in rows]
    y = [r["eval"][key]["AP"] for r in rows]
    corr = spearman(x, y, seed=int(cfg["seed"])) if len(rows) >= 4 else None
    corr_band = spearman([r["stats"]["in_band"] for r in rows], y, seed=int(cfg["seed"])) if len(rows) >= 4 else None
    return {"n_eligible": n_all, "rejected": rejected, "sources": rows, "eval_key": key,
            "spearman_meanabsz_vs_ap": corr, "spearman_inband_vs_ap": corr_band}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    k = res["eval_key"]
    L = [f"{len(res['sources'])} sources (of {res['n_eligible']} eligible distinct); AP = {k}", "",
         "| source | frames | in band | mean abs z | AP | AP50 |", "|---|---|---|---|---|---|"]
    for r in sorted(res["sources"], key=lambda r: r["stats"]["mean_abs_z"]):
        e = r["eval"][k]
        L.append(f"| {r['name']} | {r['frames']} | {r['stats']['in_band']}/13 | {r['stats']['mean_abs_z']:.2f} | "
                 f"{e['AP']:.3f} | {e['AP50']:.3f} |")
    c, cb = res["spearman_meanabsz_vs_ap"], res["spearman_inband_vs_ap"]
    if c:
        L += ["", (f"Spearman(mean |z|, AP) = {c['rho']} [95 % bootstrap {c['ci_lo']}, {c['ci_hi']}], "
                   f"permutation p = {c['perm_p']}, n = {c['n']}"),
              f"Spearman(in-band count, AP) = {cb['rho']} [{cb['ci_lo']}, {cb['ci_hi']}], p = {cb['perm_p']}"]
    return "\n".join(L) + "\n"
