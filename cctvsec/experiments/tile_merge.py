"""H3d: tile-merge strategies for H3c's 2.0x tiling arm, scored offline on cached detections.

Stage 1 (`cache_dets`) runs YOLOv8n once per frame: full frame at 1280 (baseline), full frame
at 640 (the tile arm's full-frame pass) and every 320x240 tile at 640, raw boxes at det conf,
saved to `dets_dir` so every merge strategy sees the SAME detections. Stage 2 applies
the pre-registered merges (docs/research/32 §H3d) and scores them with H3c's code:
(a) NMS 0.5 (H3c baseline), (b) NMS + intersection-over-min suppression, (c) weighted
boxes fusion, (d) tile-border rule, (e) tiles only on the calibration range-gated far ROI."""
from __future__ import annotations

import json
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np

from . import far_field_cc0 as base
from .common import ap50_by_height, band_name, batch_cameras, recall_by_height, rpath, write_json
from .far_field_h3c import collapse
from .farfield import tiles as tile_grid

BASE = "full_1280"
STRATS = ["a_nms05", "b_nms_iom", "c_wbf", "d_tile_border", "e_far_roi"]


# ---------------------------------------------------------------- box maths (numpy, CPU)
def _inter(b: np.ndarray, B: np.ndarray) -> np.ndarray:
    w = np.clip(np.minimum(b[2], B[:, 2]) - np.maximum(b[0], B[:, 0]), 0, None)
    h = np.clip(np.minimum(b[3], B[:, 3]) - np.maximum(b[1], B[:, 1]), 0, None)
    return w * h


def _area(B: np.ndarray) -> np.ndarray:
    return np.clip(B[..., 2] - B[..., 0], 0, None) * np.clip(B[..., 3] - B[..., 1], 0, None)


def nms(B: np.ndarray, iou: float = 0.5, iom: float | None = None) -> np.ndarray:
    """Greedy NMS on rows [x1,y1,x2,y2,score]; also suppress when intersection/min-area > iom."""
    if len(B) == 0:
        return np.zeros(0, int)
    order = np.argsort(-B[:, 4], kind="stable")
    ar = _area(B)
    keep = []
    while len(order):
        i, rest = order[0], order[1:]
        keep.append(i)
        if not len(rest):
            break
        it = _inter(B[i], B[rest])
        sup = it / np.maximum(ar[i] + ar[rest] - it, 1e-9) > iou
        if iom is not None:
            sup |= it / np.maximum(np.minimum(ar[i], ar[rest]), 1e-9) > iom
        order = rest[~sup]
    return np.array(keep, int)


def wbf(B: np.ndarray, iou: float = 0.55) -> np.ndarray:
    """Weighted boxes fusion (single model, many views): score-weighted mean coords, max score."""
    if len(B) == 0:
        return np.zeros((0, 5))
    order = np.argsort(-B[:, 4], kind="stable")
    fused: list[np.ndarray] = []
    members: list[list[np.ndarray]] = []
    for i in order:
        b = B[i]
        if fused:
            F = np.array(fused)
            it = _inter(b, F)
            ov = it / np.maximum(_area(b) + _area(F) - it, 1e-9)
            j = int(np.argmax(ov))
            if ov[j] > iou:
                members[j].append(b)
                M = np.array(members[j])
                w = M[:, 4:5]
                fused[j] = np.concatenate([(M[:, :4] * w).sum(0) / w.sum(), [M[:, 4].max()]])
                continue
        fused.append(b.astype(float).copy())
        members.append([b])
    return np.array(fused)


def touches_inner_edge(b: np.ndarray, rect: tuple, W: int, H: int, m: float) -> bool:
    x, y, tw, th = rect
    return bool((x > 0 and b[0] <= x + m) or (x + tw < W and b[2] >= x + tw - m)
                or (y > 0 and b[1] <= y + m) or (y + th < H and b[3] >= y + th - m))


def border_rule(full: np.ndarray, tl: np.ndarray, tidx: np.ndarray, rects: list, W: int, H: int,
                margin: float, iom: float) -> np.ndarray:
    """Drop tile boxes touching an inner tile edge when a full-frame box overlaps them (IoM >= iom)."""
    if len(tl) == 0 or len(full) == 0:
        return tl
    fa = _area(full)
    keep = []
    for b, ti in zip(tl, tidx):
        if touches_inner_edge(b, rects[int(ti)], W, H, margin):
            it = _inter(b, full)
            if (it / np.maximum(np.minimum(_area(b), fa), 1e-9) >= iom).any():
                continue
        keep.append(b)
    return np.array(keep).reshape(-1, 5)


# ---------------------------------------------------------------- calibration range gate
def person_height_by_row(calib: dict, person_m: float) -> np.ndarray:
    """Pixel height of a person_m tall person whose feet are at image row v (centre column).
    0 where the row's ray does not hit the ground (at/above the horizon)."""
    K, R, t = (np.array(calib[k], float) for k in ("K", "R", "t"))
    W, H = calib["resolution"]
    C = -R.T @ t
    Ki = np.linalg.inv(K)
    out = np.zeros(H)
    for v in range(H):
        d = R.T @ (Ki @ np.array([W / 2, v + 0.5, 1.0]))
        if d[2] >= -1e-9:
            continue
        P = C + d * (-C[2] / d[2])
        hc = K @ (R @ (P + np.array([0, 0, person_m])) + t)
        out[v] = max(0.0, v + 0.5 - hc[1] / hc[2])
    return out


def far_roi_tiles(rects: list, hrow: np.ndarray, gate_px: float) -> list[int]:
    """Tiles covering any row where a standing person would be > 0 and < gate_px tall."""
    far = (hrow > 0) & (hrow < gate_px)
    return [i for i, (x, y, tw, th) in enumerate(rects) if far[y:y + th].any()]


# ---------------------------------------------------------------- merges
def merge(strat: str, d: dict, cfg: dict, roi: list[int] | None = None) -> np.ndarray:
    full, tl, tidx = d["full_640"], d["tiles"][:, :5], d["tiles"][:, 5]
    m = cfg["merge"]
    if strat == "e_far_roi":
        sel = np.isin(tidx.astype(int), roi or [])
        tl, tidx = tl[sel], tidx[sel]
    if strat == "d_tile_border":
        tl = border_rule(full, tl, tidx, d["rects"], d["W"], d["H"], m["border_margin_px"], m["border_iom"])
    allb = np.concatenate([full.reshape(-1, 5), tl.reshape(-1, 5)])
    if strat == "c_wbf":
        return wbf(allb, m["wbf_iou"])
    if strat == "b_nms_iom":
        return allb[nms(allb, m["nms_iou"], m["iom"])]
    return allb[nms(allb, m["nms_iou"])]


def to_preds(B: np.ndarray) -> list[dict]:
    return [{"bbox": [float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])], "score": float(b[4])}
            for b in B]


# ---------------------------------------------------------------- stage 1: cache
def items_of(cfg: dict) -> list:
    batch = rpath(cfg["batch_dir"])
    cam_group = {c: g for g, cams in cfg["groups"].items() for c in cams}
    items = []
    for src in cfg["sources"]:
        for run_name in src["runs"]:
            for cam, c in batch_cameras(batch, run_name, src["source"]).items():
                if cam not in cam_group:
                    continue
                fs = [f for f in sorted(c["frames"]) if f >= 1 and f % cfg["stride"] == 0]
                if cfg.get("max_frames_per_stream"):
                    fs = fs[:cfg["max_frames_per_stream"]]
                calib = json.loads((batch / run_name / "calib" / f"{cam}.json").read_text())
                for f in fs:
                    rows = c["gt"].get(f, [])
                    items.append(((f"{run_name}/{src['source']}/{cam}", f), cam_group[cam], c["frames"][f],
                                  [r for r in rows if r["bbox"][3] >= cfg["min_gt_height"]],
                                  [r for r in rows if r["bbox"][3] < cfg["min_gt_height"]], calib))
    return items


def _arr(p, dx=0.0, dy=0.0) -> np.ndarray:
    xyxy = p.boxes.xyxy.cpu().numpy().astype(float)
    return np.concatenate([xyxy + [dx, dy, dx, dy], p.boxes.conf.cpu().numpy()[:, None]], 1).reshape(-1, 5)


def cache_dets(cfg: dict, items: list, ddir: Path) -> dict:
    """One pickle per stream: frame -> {full_1280, full_640, tiles (N,6 last=tile idx), rects, W, H}."""
    import cv2
    ddir.mkdir(parents=True, exist_ok=True)
    todo: dict[str, list] = {}
    for it in items:
        todo.setdefault(it[0][0], []).append(it)
    need = {s: v for s, v in todo.items() if not (ddir / (s.replace("/", "__") + ".pkl")).is_file()}
    if need:
        from ultralytics import YOLO
        model = YOLO(str(rpath(cfg["model"])))
        dev = cfg.get("device", "cpu")
        kw = {"classes": [0], "conf": cfg["det_conf"], "verbose": False, "max_det": 300, "device": dev,
              "half": dev != "cpu"}
        tw, th = cfg["tile"]
        for s, its in need.items():
            per = {}
            for (k, _g, png, *_rest) in its:
                img = cv2.imread(str(png))
                H, W = img.shape[:2]
                rects = tile_grid(W, H, tw, th, cfg["overlap"])
                d = {"full_1280": _arr(model.predict(img, imgsz=1280, **kw)[0]),
                     "full_640": _arr(model.predict(img, imgsz=640, **kw)[0]), "rects": rects, "W": W, "H": H}
                crops = [img[y:y + th, x:x + tw] for x, y, _, _ in rects]
                tl = [np.concatenate([_arr(p, x, y), np.full((len(p.boxes), 1), i)], 1).reshape(-1, 6)
                      for i, ((x, y, _, _), p) in enumerate(zip(rects, model.predict(crops, imgsz=cfg["tile_imgsz"], **kw)))]
                d["tiles"] = np.concatenate(tl) if tl else np.zeros((0, 6))
                per[k[1]] = d
            (ddir / (s.replace("/", "__") + ".pkl")).write_bytes(pickle.dumps(per))
        write_json(ddir / "manifest.json", {"model": cfg["model"], "device": dev, "half": kw["half"],
                                            "det_conf": cfg["det_conf"], "tile": cfg["tile"],
                                            "overlap": cfg["overlap"], "tile_imgsz": cfg["tile_imgsz"]})
    dets = {}
    for s in todo:
        per = pickle.loads((ddir / (s.replace("/", "__") + ".pkl")).read_bytes())
        dets.update({(s, f): v for f, v in per.items()})
    return dets


# ---------------------------------------------------------------- stage 2: score
def decide_h3d(res: dict, cfg: dict) -> dict:
    D = cfg["decision"]
    far = res["far"]["primary_ge20"]["recall"]
    fp, ap = res["near_op"], res["near_ap50"]
    fp_cap = D["near_fp_factor"] * fp[BASE]["fp"]
    out = {"cache_sanity_a_within": bool(abs(far["a_nms05"][0] - D["h3c_far_ge20"]) <= D["h3c_tolerance"]),
           "near_fp_cap": fp_cap, "per_strategy": {}}
    for s in STRATS:
        ok = {"far_ge20_ok": bool(far[s][0] >= D["far_min"]), "near_fp_ok": bool(fp[s]["fp"] <= fp_cap),
              "near_ap50_ok": bool(ap[BASE] - ap[s] <= D["ap50_max_drop"])}
        ok["all"] = all(ok.values())
        out["per_strategy"][s] = ok
    out["passing"] = [s for s in STRATS if out["per_strategy"][s]["all"]]
    out["decision_met"] = bool(out["passing"])
    hn = res["near_small"]["delta_e_vs_full_640"]
    out["HN_e_no_near_gain"] = bool(hn[0] <= D["hn_e_max_gain"])
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    batch = rpath(cfg["batch_dir"])
    runs = sorted({r for s in cfg["sources"] for r in s["runs"]})
    lic = base.check_licence(batch, runs)
    if not all(lic.values()):
        raise RuntimeError(f"licence check failed: {lic}")
    items = items_of(cfg)
    dets = cache_dets(cfg, items, rpath(cfg["dets_dir"]))
    bands = [tuple(b) for b in cfg["bands"]]
    G = {it[0]: it[3] for it in items}
    I = {it[0]: it[4] for it in items}
    gate = {}
    for it in items:
        cam = it[0][0]
        if cam not in gate:
            d = dets[it[0]]
            gate[cam] = far_roi_tiles(d["rects"], person_height_by_row(it[5], cfg["merge"]["person_m"]),
                                      cfg["merge"]["roi_gate_px"])
    preds: dict[str, dict] = {BASE: {k: to_preds(dets[k]["full_1280"]) for k in G},
                              "full_640": {k: to_preds(dets[k]["full_640"]) for k in G}}
    lat = {}
    for s in STRATS:
        t = 0.0
        preds[s] = {}
        for k in G:
            t0 = time.perf_counter()
            B = merge(s, dets[k], cfg, gate[k[0]])
            t += time.perf_counter() - t0
            preds[s][k] = to_preds(B)
        lat[s] = round(1000 * t / len(G), 3)
    counts = {a: base.frame_counts(G, I, preds[a], bands, cfg["op_conf"], cfg["iou"]) for a in preds}
    split = next(i for i, b in enumerate(cfg["bands"]) if b[0] >= cfg["primary_min_px"])
    cc = collapse(counts, split)
    res: dict[str, Any] = {"licence_commercial_ml_ok": lic, "n_frames": len(items),
                           "dets_manifest": json.loads((rpath(cfg["dets_dir"]) / "manifest.json").read_text()),
                           "merge_cpu_ms_per_frame": lat, "bands": [band_name(*b) for b in bands] + ["all"],
                           "far_roi_tiles": {c: len(v) for c, v in gate.items()},
                           "n_tiles_per_frame": len(next(iter(dets.values()))["rects"])}
    groups = {g: [k for k, gg, *_ in items if gg == g] for g in cfg["groups"]}
    for g, ks in groups.items():
        bl = base.make_blocks(ks, cfg["block"])
        bb = base.block_bootstrap({a: {k: cc[a][k] for k in ks} for a in cc}, bl, cfg["n_boot"], cfg["seed"], 2)
        res[g] = {"primary_ge20": {"recall": {a: v[1] for a, v in bb["recall"].items()},
                                   "delta_vs_full_1280": {a: v[1] for a, v in bb["delta_vs_full_640"].items()},
                                   "n": bb["n"][1]},
                  "n_blocks": len(bl)}
    ks = groups["near"]
    res["near_op"] = {}
    res["near_ap50"] = {}
    for a in preds:
        r = recall_by_height({k: G[k] for k in ks}, {k: preds[a][k] for k in ks}, conf=cfg["op_conf"],
                             thr=cfg["iou"], bands=bands, ignore_by_key={k: I[k] for k in ks})
        res["near_op"][a] = {"tp": r["tp"], "fp": r["fp"], "precision": round(r["tp"] / max(1, r["tp"] + r["fp"]), 4),
                             "recall": round(r["recall"], 4)}
        res["near_ap50"][a] = round(ap50_by_height(ks, {k: G[k] for k in ks}, {k: I[k] for k in ks},
                                                   {k: preds[a][k] for k in ks}, bands)["all"]["AP50"], 4)
    # hard negative for (e): near-camera recall on its small (< primary split upper) rows vs no tiles
    small = next(i for i, b in enumerate(cfg["bands"]) if b[0] >= cfg["hn_small_max_px"])
    cs = collapse({a: counts[a] for a in ("full_640", "e_far_roi")}, small)
    bb = base.block_bootstrap({a: {k: cs[a][k] for k in ks} for a in cs}, base.make_blocks(ks, cfg["block"]),
                              cfg["n_boot"], cfg["seed"], 2)
    res["near_small"] = {"max_px": cfg["hn_small_max_px"], "n": bb["n"][0],
                         "recall": {a: v[0] for a, v in bb["recall"].items()},
                         "delta_e_vs_full_640": bb["delta_vs_full_640"]["e_far_roi"][0]}
    res["decision"] = decide_h3d(res, cfg)
    if cfg.get("figure"):
        figure(res, rpath(cfg["figure"]))
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [(f"CC0 batch_v8, {res['n_frames']} frames, cached dets ({res['dets_manifest']['device']}); "
          "far recall [95% 30-frame block CI]"), "",
         "| arm | far >=20 px | near FP @0.25 | near precision | near AP50 | merge CPU ms/frame |",
         "|---|---|---|---|---|---|"]
    for a, p in res["far"]["primary_ge20"]["recall"].items():
        o = res["near_op"][a]
        L.append(f"| {a} | {p[0]:.3f} [{p[1]:.3f}, {p[2]:.3f}] | {o['fp']} | {o['precision']:.3f} | "
                 f"{res['near_ap50'][a]:.3f} | {res['merge_cpu_ms_per_frame'].get(a, '-')} |")
    return "\n".join(L + ["", f"near small rows: {res['near_small']}", f"decision: {res['decision']}"]) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    arms = [BASE] + STRATS
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    p = np.array([res["far"]["primary_ge20"]["recall"][a] for a in arms])
    x = np.arange(len(arms))
    axs[0].bar(x, p[:, 0], yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], capsize=3, color="#3a7")
    axs[0].axhline(0.65, ls=":", color="grey")
    axs[0].set_title(f"far recall, GT >= 20 px (n={res['far']['primary_ge20']['n']})")
    axs[0].set_ylim(0, 1)
    fp = [res["near_op"][a]["fp"] for a in arms]
    axs[1].bar(x, fp, color="#c64")
    axs[1].axhline(res["decision"]["near_fp_cap"], ls=":", color="grey")
    axs[1].set_title("near-cam false positives @ conf 0.25 (cap dotted)")
    ap = [res["near_ap50"][a] for a in arms]
    axs[2].bar(x, ap, color="#37a")
    axs[2].axhline(res["near_ap50"][BASE] - 0.02, ls=":", color="grey")
    axs[2].set_ylim(0.5, 1)
    axs[2].set_title("near-cam AP50 (floor dotted)")
    for ax in axs:
        ax.set_xticks(x, [a.replace("_", "\n", 1) for a in arms], fontsize=7)
    fig.suptitle("H3d tile-merge strategies on CC0 batch_v8 (same cached YOLOv8n dets)")
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
