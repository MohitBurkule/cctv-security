"""H3e: sim-to-real check of H3d's tile-merge choice on MOT20 (measurement only, never training).

H3d picked the tile-border rule (d) on CC0 renders. H3e re-runs full_1280 and the 2.0x tile arm
(full frame at 640 + 320x240 tiles at imgsz 640, 20 % overlap) on MOT20-02/03/05, caches the raw
YOLOv8n detections once on CPU, and scores (a) NMS 0.5 vs (d) the tile-border rule with H3d's own
merge code (`tile_merge.merge`). Pre-registered in docs/research/32 §H3e. MOT20 is non-commercial:
these numbers are measurement only."""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from . import far_field_cc0 as base
from .common import ap50_by_height, band_name, recall_by_height, rpath, write_json
from .farfield import tiles as tile_grid
from .tile_merge import _arr, merge, to_preds

BASE = "full_1280"
ARMS = [BASE, "full_640", "a_nms05", "d_tile_border"]


def items_of(cfg: dict) -> list:
    """[(key=(seq, frame), jpg, gt rows >= min_gt_height, ignore rows)] for the scored frames."""
    from survsim.datasets.build import read_gt
    root = rpath(cfg["mot_root"])
    out = []
    for seq, spec in cfg["sequences"].items():
        d = root / seq
        tg, ig = read_gt(d / "gt" / "gt.txt")
        G: dict[int, list] = {}
        I: dict[int, list] = {}
        for r in tg:
            (G if r["bbox"][3] >= cfg["min_gt_height"] else I).setdefault(r["frame"], []).append(r)
        for r in ig:
            I.setdefault(r["frame"], []).append(r)
        frames = [f for f in range(spec["first"], spec["last"] + 1) if f % cfg["stride"] == 0]
        for f in frames[:cfg.get("max_frames_per_seq") or None]:
            out.append(((seq, f), d / "img1" / f"{f:06d}.jpg", G.get(f, []), I.get(f, [])))
    return out


def cache_dets(cfg: dict, items: list, ddir: Path) -> dict:
    """One pickle per sequence: frame -> {full_1280, full_640, tiles (N,6), rects, W, H}; resumable."""
    import cv2
    ddir.mkdir(parents=True, exist_ok=True)
    by: dict[str, list] = {}
    for it in items:
        by.setdefault(it[0][0], []).append(it)
    model = None
    tw, th = cfg["tile"]
    dets = {}
    for seq, its in by.items():
        p = ddir / f"{seq}.pkl"
        per = pickle.loads(p.read_bytes()) if p.is_file() else {}
        missing = [it for it in its if it[0][1] not in per]
        if missing:
            if model is None:
                from ultralytics import YOLO
                model = YOLO(str(rpath(cfg["model"])))
                kw = {"classes": [0], "conf": cfg["det_conf"], "verbose": False, "max_det": cfg["max_det"],
                      "device": cfg.get("device", "cpu")}
            for n, (k, jpg, *_r) in enumerate(missing):
                img = cv2.imread(str(jpg))
                H, W = img.shape[:2]
                rects = tile_grid(W, H, tw, th, cfg["overlap"])
                d = {"full_1280": _arr(model.predict(img, imgsz=1280, **kw)[0]),
                     "full_640": _arr(model.predict(img, imgsz=640, **kw)[0]), "rects": rects, "W": W, "H": H}
                tl = []
                for i0 in range(0, len(rects), cfg["tile_batch"]):
                    rs = rects[i0:i0 + cfg["tile_batch"]]
                    ps = model.predict([img[y:y + h_, x:x + w_] for x, y, w_, h_ in rs], imgsz=cfg["tile_imgsz"], **kw)
                    tl += [np.concatenate([_arr(q, x, y), np.full((len(q.boxes), 1), i0 + j)], 1).reshape(-1, 6)
                           for j, ((x, y, _, _), q) in enumerate(zip(rs, ps))]
                d["tiles"] = np.concatenate(tl) if tl else np.zeros((0, 6))
                per[k[1]] = d
                if (n + 1) % 10 == 0 or n + 1 == len(missing):
                    p.write_bytes(pickle.dumps(per))
        dets.update({(seq, f): per[f] for f in (it[0][1] for it in its)})
    write_json(ddir / "manifest.json", {"model": cfg["model"], "device": cfg.get("device", "cpu"), "half": False,
                                        "det_conf": cfg["det_conf"], "tile": cfg["tile"], "overlap": cfg["overlap"],
                                        "tile_imgsz": cfg["tile_imgsz"], "max_det": cfg["max_det"]})
    return dets


def fp_cut_boot(fp_a: dict, fp_d: dict, blocks: list[list], n_boot: int, seed: int) -> list[float]:
    """1 - FP(d)/FP(a) with a paired block-bootstrap 95 % CI."""
    A = np.array([sum(fp_a[k] for k in b) for b in blocks], float)
    D = np.array([sum(fp_d[k] for k in b) for b in blocks], float)
    idx = np.random.default_rng(seed).integers(0, len(blocks), (n_boot, len(blocks)))
    bs = 1 - D[idx].sum(1) / np.maximum(A[idx].sum(1), 1e-9)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return [round(float(1 - D.sum() / max(A.sum(), 1e-9)), 4), round(float(lo), 4), round(float(hi), 4)]


def decide_h3e(res: dict, cfg: dict) -> dict:
    D = cfg["decision"]
    cut = res["fp_cut_d_vs_a"][0]
    dr = res["recall_delta_d_minus_a_all"][0]
    hn = res["hn_ge80_delta_d_minus_1280"][0]
    out = {"fp_cut_ok": bool(cut >= D["fp_cut_min"]), "recall_ok": bool(dr >= -D["recall_max_drop"])}
    out["decision_met"] = out["fp_cut_ok"] and out["recall_ok"]
    out["HN_tiles_not_better_ge80"] = bool(hn is not None and hn <= D["hn_max_gain"])
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    items = items_of(cfg)
    dets = cache_dets(cfg, items, rpath(cfg["dets_dir"]))
    bands = [tuple(b) for b in cfg["bands"]]
    G = {it[0]: it[2] for it in items}
    I = {it[0]: it[3] for it in items}
    preds = {BASE: {k: to_preds(dets[k]["full_1280"]) for k in G},
             "full_640": {k: to_preds(dets[k]["full_640"]) for k in G}}
    for s in ("a_nms05", "d_tile_border"):
        preds[s] = {k: to_preds(merge(s, dets[k], cfg)) for k in G}
    counts = {a: base.frame_counts(G, I, preds[a], bands, cfg["op_conf"], cfg["iou"]) for a in ARMS}
    keys = list(G)
    blocks = base.make_blocks(keys, cfg["block"])
    nb = len(bands)
    # recall per bin; paired deltas vs the first arm listed
    bb_1280 = base.block_bootstrap({a: counts[a] for a in ARMS}, blocks, cfg["n_boot"], cfg["seed"], nb)
    bb_a = base.block_bootstrap({a: counts[a] for a in ("a_nms05", "d_tile_border")}, blocks,
                                cfg["n_boot"], cfg["seed"], nb)
    res: dict[str, Any] = {"data_licence": "MOT20 CC BY-NC-SA: measurement only", "n_frames": len(items),
                           "frames_per_seq": {s: sum(1 for k in keys if k[0] == s) for s in cfg["sequences"]},
                           "n_blocks": len(blocks), "bands": [band_name(*b) for b in bands] + ["all"],
                           "n_gt": bb_1280["n"],
                           "tiles_per_frame": {s: len(dets[next(k for k in keys if k[0] == s)]["rects"])
                                               for s in cfg["sequences"]},
                           "dets_manifest": json.loads((rpath(cfg["dets_dir"]) / "manifest.json").read_text()),
                           "recall_by_bin": bb_1280["recall"],
                           "delta_vs_full_1280": bb_1280["delta_vs_full_640"],
                           "recall_delta_d_minus_a_all": bb_a["delta_vs_full_640"]["d_tile_border"][-1],
                           "hn_ge80_delta_d_minus_1280": bb_1280["delta_vs_full_640"]["d_tile_border"][nb - 1],
                           "hn_ge80_delta_a_minus_1280": bb_1280["delta_vs_full_640"]["a_nms05"][nb - 1]}
    res["op"] = {}
    res["ap50"] = {}
    for a in ARMS:
        r = recall_by_height(G, preds[a], conf=cfg["op_conf"], thr=cfg["iou"], bands=bands, ignore_by_key=I)
        res["op"][a] = {"tp": r["tp"], "fp": r["fp"], "precision": round(r["tp"] / max(1, r["tp"] + r["fp"]), 4),
                        "recall": round(r["recall"], 4)}
        res["ap50"][a] = round(ap50_by_height(keys, G, I, preds[a], bands)["all"]["AP50"], 4)
    res["fp_cut_d_vs_a"] = fp_cut_boot({k: counts["a_nms05"][k]["fp"] for k in keys},
                                       {k: counts["d_tile_border"][k]["fp"] for k in keys}, blocks,
                                       cfg["n_boot"], cfg["seed"])
    render = rpath(cfg["render_results"])
    if render.is_file():
        r = json.loads(render.read_text())
        res["render_h3d_near"] = {a: {**r["near_op"][a], "ap50": r["near_ap50"][a]}
                                  for a in (BASE, "a_nms05", "d_tile_border")}
        res["render_h3d_fp_cut_d_vs_a"] = round(1 - r["near_op"]["d_tile_border"]["fp"] / r["near_op"]["a_nms05"]["fp"], 4)
    res["decision"] = decide_h3e(res, cfg)
    if cfg.get("figure"):
        figure(res, rpath(cfg["figure"]))
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [f"MOT20, measurement only. {res['n_frames']} frames, {res['n_blocks']} 30-frame blocks", "",
         "| arm | recall all >=20 px [CI] | recall >=80 px | FP @0.25 | precision | AP50 |", "|---|---|---|---|---|---|"]
    for a in ARMS:
        r = res["recall_by_bin"][a]
        L.append(f"| {a} | {r[-1][0]:.3f} [{r[-1][1]:.3f}, {r[-1][2]:.3f}] | {r[-2][0]:.3f} | {res['op'][a]['fp']} | "
                 f"{res['op'][a]['precision']:.3f} | {res['ap50'][a]:.3f} |")
    return "\n".join(L + ["", f"fp cut d vs a: {res['fp_cut_d_vs_a']}", f"decision: {res['decision']}"]) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    arms = [BASE, "a_nms05", "d_tile_border"]
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    x = np.arange(len(arms))
    w = 0.38
    rn = res.get("render_h3d_near", {})
    for ax, key, title in ((axs[0], "fp", "false positives @ conf 0.25"), (axs[1], "precision", "precision @ 0.25"),
                           (axs[2], "recall", "recall @ 0.25 (GT >= 20 px real, >= 13 px render)")):
        real = [res["op"][a][key] for a in arms]
        rend = [rn.get(a, {}).get(key, np.nan) for a in arms]
        ax.bar(x - w / 2, rend, w, label="render (H3d near cam, CC0)", color="#999")
        ax.bar(x + w / 2, real, w, label="real (MOT20-02/03/05)", color="#37a")
        ax.set_xticks(x, arms, fontsize=8)
        ax.set_title(title, fontsize=9)
    axs[0].legend(fontsize=7)
    fig.suptitle(f"H3e tile merge render vs real: FP cut (d) vs (a) render {res.get('render_h3d_fp_cut_d_vs_a')}, "
                 f"real {res['fp_cut_d_vs_a'][0]} [{res['fp_cut_d_vs_a'][1]}, {res['fp_cut_d_vs_a'][2]}]", fontsize=10)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
