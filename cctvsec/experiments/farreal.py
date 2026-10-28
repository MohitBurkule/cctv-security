"""H8: far-field on *real* pixels. Does fine-tuning on SurvSim's far-camera
renders help a detector on real people under 60 px?

MOT20-02 has no GT box under 89 px at 1080p, so small real people are made by
downscaling whole frames (INTER_AREA) by `scales`; GT boxes are scaled with
them. Only GT under `max_h` px after scaling are targets; the rest are ignore
regions (a detection on them is neither TP nor FP). Each arm's weights are
scored with full-frame inference at the downscaled frame's own size (no
upsampling) and with SAHI-style tiling (farfield.predict), which upsamples tiles.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import ap50_by_height, read_mot_rows, recall_by_height, rpath, wait_for_gpu, write_json


def _frames(cfg):
    import cv2
    d = rpath(cfg["mot20_root"]) / "train" / cfg["eval_sequence"]
    gt = read_mot_rows(d / "gt" / "gt.txt")
    for f in range(cfg["eval_stride"], cfg["eval_frames"] + 1, cfg["eval_stride"]):
        yield f, cv2.imread(str(d / "img1" / f"{f:06d}.jpg")), gt.get(f, [])


def evaluate(weights: str, cfg: dict[str, Any]) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    from .farfield import predict
    model = YOLO(weights)
    bands = [tuple(b) for b in cfg["bands"]]
    frames = list(_frames(cfg))
    out = {}
    for s in cfg["scales"]:
        G, I, imgs = {}, {}, {}
        for f, img, rows in frames:
            im = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            sc = [{**r, "bbox": [v * s for v in r["bbox"]]} for r in rows]
            G[f] = [r for r in sc if r["bbox"][3] < cfg["max_h"]]
            I[f] = [r for r in sc if r["bbox"][3] >= cfg["max_h"]]
            imgs[f] = im
        n_gt = sum(len(v) for v in G.values())
        w = max(imgs[frames[0][0]].shape[:2])
        for meth in cfg["methods"]:
            m = dict(meth)
            if m.get("imgsz") == "native":
                m["imgsz"] = int(np.ceil(w / 32) * 32)
            P = {f: predict(model, im, m, cfg["det_conf"]) for f, im in imgs.items()}
            keys = list(G)
            out[f"x{s}/{meth['name']}"] = {
                "scale": s, "method": m, "n_gt": n_gt,
                "ap_by_height": ap50_by_height(keys, G, I, P, bands),
                "recall_at_op": recall_by_height(G, P, conf=cfg["op_conf"], thr=0.5, bands=bands,
                                                 ignore_by_key=I)}
    return out


def _run_arms(cfg: dict[str, Any], out: Path, arms: list[str] | None = None) -> dict[str, Any]:
    from .detection import train_arm
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
        if arm.get("weights"):
            weights = str(rpath(arm["weights"]))
        elif arm.get("train"):
            weights = str(train_arm(arm, cfg, work, rec))
        else:
            weights = str(rpath(cfg["base_model"]))
        rec["weights"] = weights
        rec["eval"] = evaluate(weights, cfg)
        write_json(ap, rec)
        results[arm["name"]] = rec
    for f in sorted((out / "arms").glob("*.json")):
        results.setdefault(f.stem, json.loads(f.read_text()))
    return {"arms": results}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [(f"MOT20-{cfg['eval_sequence'][-2:]} frames {cfg['eval_stride']}..{cfg['eval_frames']} "
         f"step {cfg['eval_stride']}, downscaled; targets = GT < {cfg['max_h']} px after scaling. "
         f"AP50 over targets; recall/precision at conf {cfg['op_conf']}, IoU 0.5."), "",
         "| arm | scale | method | GT | AP50 | R | P | R <30px | R 30-45px | R 45-60px |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in res["arms"].items():
        for e in r["eval"].values():
            rb = e["recall_at_op"]["recall_by_height"]
            c = lambda b, rb=rb: f"{rb[b]['recall']:.3f}" if rb.get(b, {}).get("recall") is not None else "-"
            L.append(f"| {name} | {e['scale']} | {e['method']['name']} | {e['n_gt']} | "
                     f"{e['ap_by_height']['all'].get('AP50', float('nan')):.3f} | "
                     f"{e['recall_at_op']['recall']:.3f} | {e['recall_at_op']['precision']:.3f} | "
                     f"{c('0-30')} | {c('30-45')} | {c('45-60')} |")
    if res.get("contrasts"):
        L += ["", "| contrast | eval | mean ΔAP50 | 95 % bootstrap | sign-flip p | per-seed |", "|---|---|---|---|---|---|"]
        for x in res["contrasts"]:
            L.append(f"| {x['contrast']} | {x['key']} | {x['mean_diff']:+.4f} | "
                     f"[{x['boot95'][0]:+.4f}, {x['boot95'][1]:+.4f}] | {x['signflip_p']} | {x['diffs']} |")
    return "\n".join(L) + "\n"


def _ap50(rec: dict[str, Any], key: str) -> float | None:
    e = rec.get("eval", {}).get(key)
    return None if e is None else e["ap_by_height"]["all"].get("AP50")


def contrasts(res: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """H18: `b - a` AP50 per eval key. Seeded arms (`<x>_s<k>`) are paired by seed;
    an unseeded arm (zero_shot) is a constant, so the CI is over b's seeds only."""
    from .tracking_transfer import paired
    arms, seeds, out = res["arms"], cfg.get("seeds", []), []
    keys = sorted({k for r in arms.values() for k in r.get("eval", {})})
    for a, b in cfg.get("contrasts", []):
        for key in keys:
            sa = [s for s in seeds if f"{a}_s{s}" in arms and f"{b}_s{s}" in arms]
            if a in arms:
                sb = [s for s in seeds if f"{b}_s{s}" in arms]
                va, vb = [_ap50(arms[a], key)] * len(sb), [_ap50(arms[f"{b}_s{s}"], key) for s in sb]
            else:
                va = [_ap50(arms[f"{a}_s{s}"], key) for s in sa]
                vb = [_ap50(arms[f"{b}_s{s}"], key) for s in sa]
            if len(vb) < 2 or None in va + vb:
                continue
            out.append({"contrast": f"{b} - {a}", "key": key, "a": va, "b": vb, **paired(va, vb)})
    return out


def run(cfg: dict[str, Any], out: Path, arms: list[str] | None = None) -> dict[str, Any]:
    body = _run_arms(cfg, out, arms)
    if cfg.get("contrasts"):
        body["contrasts"] = contrasts(body, cfg)
    return body
