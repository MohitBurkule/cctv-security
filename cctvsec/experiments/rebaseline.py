"""H16: zero-shot re-baseline of one detector against another (report 54 §9).

For each model: MOT20 subset AP / AP50 / AP75 (docs/13 harness, per eval set and
imgsz) and recall by GT height on batch_v7 raw frames (every `stride`-th frame,
conf 0.25, IoU 0.5). Per-sequence recalls are kept so model differences can be
paired by camera-sequence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .common import band_name, batch_cameras, recall_by_height, rpath, wait_for_gpu, write_json
from .detection import _eval_manifests, eval_arm


def _batch_recall(model, cfg, imgsz) -> dict[str, Any]:
    bands = [tuple(b) for b in cfg["height_bands"]]
    G, P, per_seq = {}, {}, {}
    for run in cfg["recall_runs"]:
        for cam, c in batch_cameras(rpath(cfg["batch_dir"]), run, "raw").items():
            keys = [f for f in sorted(c["frames"]) if f >= 1 and f % cfg["stride"] == 0]
            g, p = {}, {}
            for i in range(0, len(keys), 8):
                ks = keys[i:i + 8]
                res = model.predict([str(c["frames"][f]) for f in ks], imgsz=imgsz, classes=[0],
                                    conf=0.01, verbose=False, half=True, max_det=300)
                for f, r in zip(ks, res):
                    xyxy, sc = r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()
                    p[(run, cam, f)] = [{"bbox": [a, b, cc - a, d - b], "score": float(s)}
                                        for (a, b, cc, d), s in zip(xyxy, sc)]
                    g[(run, cam, f)] = c["gt"].get(f, [])
            G.update(g)
            P.update(p)
            per_seq[f"{run}/{cam}"] = recall_by_height(g, p, bands=bands)["recall"]
    out = recall_by_height(G, P, bands=bands)
    out["per_sequence_recall"] = per_seq
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from ultralytics import YOLO
    eval_dirs = _eval_manifests(cfg, out)
    body: dict[str, Any] = {"models": {}}
    for name, w in cfg["models"].items():
        rec: dict[str, Any] = {"weights": w, "gpu_wait": wait_for_gpu(cfg.get("min_free_mib", 2048))}
        work = (out / "work" / name).resolve()
        work.mkdir(parents=True, exist_ok=True)
        eval_arm(str(rpath(w)), eval_dirs, cfg["eval_imgsz"], work, rec, set(),
                 [tuple(b) for b in cfg["height_bands"]])
        model = YOLO(str(rpath(w)))
        rec["batch_recall"] = {str(sz): _batch_recall(model, cfg, sz) for sz in cfg["eval_imgsz"]}
        write_json(out / "models" / f"{name}.json", rec)
        body["models"][name] = rec
    a, b = cfg["contrast"]
    body["contrast"] = {}
    for sz in cfg["eval_imgsz"]:
        ra = body["models"][a]["batch_recall"][str(sz)]["per_sequence_recall"]
        rb = body["models"][b]["batch_recall"][str(sz)]["per_sequence_recall"]
        d = np.array([rb[k] - ra[k] for k in ra])
        rng = np.random.default_rng(0)
        bs = d[rng.integers(0, len(d), (10000, len(d)))].mean(1)
        body["contrast"][f"batch_recall@{sz}"] = {
            "contrast": f"{b} - {a}", "n_sequences": len(d), "mean_diff": round(float(d.mean()), 4),
            "boot95_paired": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]}
    return body


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    bands = [band_name(*b) for b in cfg["height_bands"]]
    L = ["| model | eval | AP | AP50 | AP75 |", "|---|---|---|---|---|"]
    for n, r in res["models"].items():
        for es, e in r["eval"].items():
            L.append(f"| {n} | {es} | {e['AP']:.3f} | {e['AP50']:.3f} | {e['AP75']:.3f} |")
    L += ["", "| model | imgsz | R all | P | " + " | ".join(f"R {b}" for b in bands) + " |",
          "|---|---|---|---|" + "---|" * len(bands)]
    for n, r in res["models"].items():
        for sz, e in r["batch_recall"].items():
            rb = e["recall_by_height"]
            L.append(f"| {n} | {sz} | {e['recall']:.3f} | {e['precision']:.3f} | " + " | ".join(
                f"{rb[b]['recall']:.3f} (n={rb[b]['n']})" if rb[b]["recall"] is not None else "-" for b in bands) + " |")
    L += ["", "| contrast | n seq | mean diff | 95 % paired bootstrap |", "|---|---|---|---|"]
    for k, c in res["contrast"].items():
        L.append(f"| {k} {c['contrast']} | {c['n_sequences']} | {c['mean_diff']:+.4f} | "
                 f"[{c['boot95_paired'][0]:+.4f}, {c['boot95_paired'][1]:+.4f}] |")
    return "\n".join(L) + "\n"
