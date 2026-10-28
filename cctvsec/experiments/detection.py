"""H1 / H2: sim-to-real person detection.

Fine-tune COCO-pretrained YOLOv8n on batch_v6 synthetic frames (and/or a small
real slice), then score every arm on real MOT20 with the same harness as
docs/13 (`baselines.run.detect` + `eval_det`), plus recall and AP by box height.

Leakage rule: an arm that trains on MOT20-01 frames is only reported on
MOT20-02 (`mot20_02` eval set). The `mot20_sub` set (both sequences) is only
reported for arms that saw no real frames.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .common import (
    ap50_by_height,
    batch_cameras,
    export_item,
    gpu_meter,
    read_mot_rows,
    recall_by_height,
    rpath,
    wait_for_gpu,
    write_data_yaml,
    write_json,
)


def _eval_manifests(cfg: dict[str, Any], out: Path) -> dict[str, Path]:
    """Real eval sets as manifests (frames referenced in place, never copied)."""
    src = json.loads(rpath(cfg["mot20_manifest"]).read_text())
    sets = {}
    for name, seqs in cfg["eval_sets"].items():
        d = out / "_eval" / name
        d.mkdir(parents=True, exist_ok=True)
        m = {**src, "runs": [r for r in src["runs"] if r["name"] in seqs]}
        (d / "manifest.json").write_text(json.dumps(m, indent=1))
        sets[name] = d
    return sets


def _synth_candidates(batch: Path, runs, sources) -> list[tuple[str, Path, list]]:
    """(name, png, rows) for every synthetic frame a source spec selects.

    A spec is {source, stride, phase} plus optional `runs` / `cameras` filters,
    `batch_dir` (overrides the config's), `gt_subdir` (e.g. "amodal") and `min_vis`
    (drop label rows with MOT visibility below it)."""
    items = []
    for s in sources:
        b = rpath(s["batch_dir"]) if s.get("batch_dir") else batch
        for run in s.get("runs", runs):
            for cam, c in batch_cameras(b, run, s["source"], s.get("gt_subdir"), s.get("min_vis")).items():
                if s.get("cameras") and cam not in s["cameras"]:
                    continue
                sel = [f for f in sorted(c["frames"])
                       if f >= 1 and f % s["stride"] == s.get("phase", 0) % s["stride"]]
                if not sel:
                    continue
                # GT is in raw-render pixels; frames can differ (1920x1080 raw disguise
                # cameras, 1280x720 degraded video). Labels are written in the image's pixels.
                wh = image_size(c["frames"][sel[0]])
                raw = sorted((b / run / "render" / cam).glob("*.png"))
                sx, sy = scale_to(image_size(raw[0]) if raw else wh, wh)
                for f in sel:
                    rows = [{**r, "bbox": [r["bbox"][0] * sx, r["bbox"][1] * sy,
                                           r["bbox"][2] * sx, r["bbox"][3] * sy]}
                            for r in c["gt"].get(f, [])]
                    items.append((f"{run}_{s['source']}_{cam}_{f:04d}", c["frames"][f],
                                  rows, s["source"], wh))
    return items


def image_size(p: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(p) as im:
        return im.size


def scale_to(src_wh, dst_wh) -> tuple[float, float]:
    return dst_wh[0] / src_wh[0], dst_wh[1] / src_wh[1]


def inject_label_noise(items, jitter_sigma: float, drop: float, seed: int):
    """H25: perturb synthetic labels. Each box edge moves by N(0, sigma * box
    width) (x edges) or N(0, sigma * box height) (y edges); a box is dropped
    when its uniform draw < `drop`. The draws depend only on `seed` and the box
    order, so across noise levels within a seed the same boxes are dropped
    (drop sets are nested) and jitter directions are shared (paired cells)."""
    import numpy as np
    rng = np.random.default_rng([seed, 25])
    out = []
    for name, png, rows, src, wh in items:
        new = []
        for r in rows:
            z = rng.standard_normal(4)
            u = rng.random()
            if u < drop:
                continue
            x, y, bw, bh = r["bbox"]
            x0, y0 = x + z[0] * jitter_sigma * bw, y + z[1] * jitter_sigma * bh
            x1, y1 = x + bw + z[2] * jitter_sigma * bw, y + bh + z[3] * jitter_sigma * bh
            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)
            new.append({**r, "bbox": [x0, y0, max(x1 - x0, 1.0), max(y1 - y0, 1.0)]})
        out.append((name, png, new, src, wh))
    return out


def build_train_set(arm: dict[str, Any], cfg: dict[str, Any], root: Path) -> dict[str, Any]:
    """Materialise one arm's YOLO dataset. Returns counts for the results JSON.

    `train.synthetic_limit: N` keeps a seeded random N of the selected synthetic
    frames (seed = the arm's training seed), for mixing-ratio sweeps."""
    import numpy as np

    if root.exists():
        shutil.rmtree(root)
    batch = rpath(cfg["batch_dir"])
    counts = {"train_images": 0, "train_boxes": 0, "val_images": 0, "by_source": {}}
    tr = arm.get("train", {})

    if tr.get("synthetic"):
        items = _synth_candidates(batch, cfg["synthetic_train_runs"], tr["synthetic"])
        counts["synthetic_candidates"] = len(items)
        lim = tr.get("synthetic_limit")
        if lim is not None and lim < len(items):
            rng = np.random.default_rng(int(arm.get("seed", cfg["train"]["seed"])))
            items = [items[i] for i in sorted(rng.choice(len(items), int(lim), replace=False))]
        noise = tr.get("label_noise")
        if noise:
            items = inject_label_noise(items, noise["jitter_sigma"], noise["drop"],
                                       int(noise.get("seed", arm.get("seed", cfg["train"]["seed"]))))
            counts["label_noise"] = dict(noise)
        mode = tr.get("synthetic_mode")
        if mode and mode != "true":
            from .dose_fixedstep import apply_synthetic_mode
            items = apply_synthetic_mode(items, mode, int(arm.get("seed", cfg["train"]["seed"])),
                                         root.parent / f"syn_{mode}", batch)
            counts["synthetic_mode"] = mode
        for name, png, rows, src, (w, h) in items:
            export_item(root, "train", name, png, rows, w, h)
            counts["train_images"] += 1
            counts["train_boxes"] += len(rows)
            counts["by_source"][src] = counts["by_source"].get(src, 0) + 1
    if tr.get("real"):
        r = tr["real"]
        seq = rpath(cfg["mot20_root"]) / "train" / r["sequence"]
        gt = read_mot_rows(seq / "gt" / "gt.txt")
        for rep in range(r.get("repeat", 1)):
            for f in range(1, r["frames"] + 1):
                export_item(root, "train", f"{r['sequence']}_{f:06d}_r{rep}",
                            seq / "img1" / f"{f:06d}.jpg", gt.get(f, []), 1920, 1080)
                counts["train_images"] += 1
                counts["train_boxes"] += len(gt.get(f, []))
                counts["by_source"]["real"] = counts["by_source"].get("real", 0) + 1
        counts["real_unique_frames"] = r["frames"]
    if tr.get("pad_to"):
        counts["padded"] = pad_train_list(root, int(tr["pad_to"]), int(arm.get("seed", cfg["train"]["seed"])))
        counts["train_images"] += counts["padded"]
    # Held-out *synthetic scenario* for the trainer's own val loop; checkpoint
    # selection does not use it (last.pt is scored), so no real data steers training.
    for name, png, rows, _, (w, h) in _synth_candidates(batch, cfg["synthetic_val_runs"], cfg["val_sources"]):
        export_item(root, "val", name, png, rows, w, h)
        counts["val_images"] += 1
    write_data_yaml(root)
    return counts


def pad_train_list(root: Path, target: int, seed: int) -> int:
    """H26: grow the train list to `target` images with seeded duplicates drawn
    without replacement from the arm's own list (so the mix proportions hold in
    expectation and no image is discarded). Returns the number added."""
    import numpy as np
    imgs = sorted((root / "images" / "train").iterdir())
    k = target - len(imgs)
    if k <= 0:
        return 0
    rng = np.random.default_rng([seed, 26])
    for i in sorted(rng.choice(len(imgs), k, replace=k > len(imgs))):
        ip = imgs[i]
        stem = f"{ip.stem}_pad{i}"
        (ip.parent / f"{stem}{ip.suffix}").symlink_to(ip.resolve())
        lp = root / "labels" / "train"
        (lp / f"{stem}.txt").write_text((lp / f"{ip.stem}.txt").read_text())
    return k


def train_arm(arm, cfg, work: Path, rec: dict[str, Any], base: str | None = None) -> Path:
    """Fine-tune one arm. `arm.train_opts` overrides cfg.train (epochs, freeze, lr0...).

    `arm.pretrain` ({train, train_opts}) first trains a stage on its own data and
    fine-tunes from that checkpoint (synthetic pre-training, then real fine-tune)."""
    from ultralytics import YOLO

    if arm.get("pretrain"):
        pre = {"name": arm["name"] + "_pretrain", "seed": arm.get("seed"), **arm["pretrain"]}
        pre = {k: v for k, v in pre.items() if v is not None}
        rec["pretrain"] = {}
        base = str(train_arm(pre, cfg, work / "pretrain", rec["pretrain"]))
    t = {**cfg["train"], **arm.get("train_opts", {})}
    root = work / "yolo_data"
    rec["dataset"] = build_train_set(arm, cfg, root)
    model = YOLO(str(base or rpath(cfg["base_model"])))
    extra = {k: t[k] for k in ("freeze", "warmup_epochs", "close_mosaic") if t.get(k) is not None}
    with gpu_meter(rec, "train_cost"):
        model.train(data=str(root / "data.yaml"), epochs=t["epochs"], imgsz=t["imgsz"],
                    batch=t["batch"], seed=arm.get("seed", t["seed"]), deterministic=True,
                    workers=t.get("workers", 4), project=str(work), name="train", exist_ok=True,
                    plots=False, val=False, verbose=False, lr0=t.get("lr0", 0.01),
                    optimizer=t.get("optimizer", "auto"), patience=0, cache=False, amp=True,
                    **extra)
    rec["train_opts"] = t
    return work / "train" / "weights" / "last.pt"


def eval_arm(weights: str, eval_dirs: dict[str, Path], imgszs, work: Path, rec: dict[str, Any],
             skip: set[str], bands) -> None:
    from ..baselines.run import _gt, _sequences, detect, eval_det
    from survsim.datasets.build import load_manifest

    rec["eval"] = {}
    for name, d in eval_dirs.items():
        if name in skip:
            rec["eval"][name] = {"skipped": "arm trained on frames of this set (leakage)"}
            continue
        m = load_manifest(d)
        for sz in imgszs:
            od = work / f"eval_{name}_{sz}"
            od.mkdir(parents=True, exist_ok=True)
            cost: dict[str, Any] = {}
            with gpu_meter(cost, "cost"):
                dets = detect(m, od, weights, sz)
            det = eval_det(m, dets)
            keys, G, I, P = [], {}, {}, {}
            for run, cam, c in _sequences(m):
                key = f"{run['name']}/{cam}"
                tg, ig = _gt(m, c)
                for r in tg:
                    G.setdefault((key, r["frame"]), []).append(r)
                for r in ig:
                    I.setdefault((key, r["frame"]), []).append(r)
                ks = [(key, int(f)) for f in c["frames"]]
                keys += ks
                P.update({(key, int(f)): v for f, v in dets[key].items()})
            rec["eval"][f"{name}@{sz}"] = {
                "AP": round(det["all"]["AP"], 4), "AP50": round(det["all"]["AP50"], 4),
                "AP75": round(det["all"]["AP75"], 4), "operating_point": det["operating_point"],
                "recall_at_0.25": recall_by_height({k: G.get(k, []) for k in keys}, P,
                                                   ignore_by_key=I, bands=bands),
                "ap_by_height": ap50_by_height(keys, G, I, P, bands),
                "n_frames": len(keys), **cost["cost"]}


def run(cfg: dict[str, Any], out: Path, arms: list[str] | None = None) -> dict[str, Any]:
    eval_dirs = _eval_manifests(cfg, out)
    results = {}
    for arm in cfg["arms"]:
        if arms and arm["name"] not in arms:
            continue
        ap = out / "arms" / f"{arm['name']}.json"
        if ap.is_file() and not cfg.get("force"):
            results[arm["name"]] = json.loads(ap.read_text())
            continue
        work = (out / "work" / arm["name"]).resolve()
        work.mkdir(parents=True, exist_ok=True)
        rec: dict[str, Any] = {"arm": arm["name"], "description": arm.get("description", ""),
                               "gpu_wait": wait_for_gpu()}
        if arm.get("train"):
            weights = str(train_arm(arm, cfg, work, rec))
        else:
            weights = str(rpath(cfg["base_model"]))
        rec["weights"] = weights
        skip = set(cfg.get("leaky_sets", [])) if (arm.get("train") or {}).get("real") else set()
        if (arm.get("pretrain") or {}).get("train", {}).get("real"):
            skip |= set(cfg.get("leaky_sets", []))
        dirs = {k: v for k, v in eval_dirs.items() if k in arm.get("eval_sets", eval_dirs)}
        eval_arm(weights, dirs, arm.get("eval_imgsz", cfg["eval_imgsz"]), work, rec, skip,
                 [tuple(b) for b in cfg["height_bands"]])
        write_json(ap, rec)
        results[arm["name"]] = rec
    # arms from earlier invocations count too: results.json always reflects every arm on disk
    for f in sorted((out / "arms").glob("*.json")):
        results.setdefault(f.stem, json.loads(f.read_text()))
    body = {"arms": results}
    body["seed_summary"] = {k: seed_summary(body, k) for k in
                            sorted({es for r in results.values() for es in r.get("eval", {})})}
    return body


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    lines = [("| arm | eval set | AP | AP50 | AP75 | R@.25 | P@.25 | AP50 80-120px | AP50 160-240px | "
             "train s | train VRAM MiB | train imgs |"),
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in res["arms"].items():
        tc = r.get("train_cost", {})
        for es, e in r.get("eval", {}).items():
            if "AP" not in e:
                continue
            hb = e["ap_by_height"]
            lines.append(
                f"| {name} | {es} | {e['AP']:.3f} | {e['AP50']:.3f} | {e['AP75']:.3f} | "
                f"{e['recall_at_0.25']['recall']:.3f} | {e['recall_at_0.25']['precision']:.3f} | "
                f"{hb.get('80-120', {}).get('AP50', float('nan')):.3f} | "
                f"{hb.get('160-240', {}).get('AP50', float('nan')):.3f} | "
                f"{tc.get('seconds', '-')} | {tc.get('peak_vram_mib', '-')} | "
                f"{r.get('dataset', {}).get('train_images', 0)} |")
    lines += ["", "Seed summary (training seeds; zero_shot has no training seed):", "",
              "| arm | eval | seeds | AP mean (sd) | AP50 mean (sd) |", "|---|---|---|---|---|"]
    for es, groups in res.get("seed_summary", {}).items():
        for base, v in groups.items():
            if v["n_seeds"] > 1:
                lines.append(f"| {base} | {es} | {v['n_seeds']} | {v['AP_mean']:.3f} ({v['AP_sd']:.3f}) | "
                             f"{v['AP50_mean']:.3f} ({v['AP50_sd']:.3f}) |")
    return "\n".join(lines) + "\n"


def seed_summary(res: dict[str, Any], key: str = "mot20_02@640") -> dict[str, Any]:
    """Mean and sample sd over training seeds (arm names `<base>` and `<base>_s<k>`)."""
    import re

    import numpy as np
    groups: dict[str, list] = {}
    for name, r in res["arms"].items():
        e = r.get("eval", {}).get(key)
        if e and "AP" in e:
            groups.setdefault(re.sub(r"_s\d+$", "", name), []).append(e)
    out = {}
    for base, es in groups.items():
        ap = np.array([e["AP"] for e in es])
        ap50 = np.array([e["AP50"] for e in es])
        out[base] = {"n_seeds": len(es), "AP_mean": round(float(ap.mean()), 4),
                     "AP_sd": round(float(ap.std(ddof=1)), 4) if len(es) > 1 else None,
                     "AP50_mean": round(float(ap50.mean()), 4),
                     "AP50_sd": round(float(ap50.std(ddof=1)), 4) if len(es) > 1 else None,
                     "AP50_values": ap50.round(4).tolist()}
    return out
