"""H6 (c, d): why does synthetic-only fine-tuning hurt real AP?

(c) Label quality. Zero-shot COCO YOLOv8n boxes are a reference "what a
    detector thinks a person box is". For sampled synthetic frames and for real
    MOT20 frames, match every GT box to its best zero-shot box and record IoU
    and the normalised edge offsets. If synthetic GT boxes were loose or offset
    relative to where the pixels are, the IoU distribution would be much worse
    than on MOT20 (whose GT is hand-annotated) and the offsets would be biased.
    Overlay images (GT green, YOLO red) are written for eyeballing.

(d) Image statistics. docs/15 realism stats of each training set vs MOT20-02,
    tabulated against that set's real AP from earlier experiments.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import batch_cameras, read_mot_rows, rpath, write_json


def _yolo_boxes(model, img, conf):
    p = model.predict(img, imgsz=1280, classes=[0], conf=conf, verbose=False, half=True)[0]
    xyxy = p.boxes.xyxy.cpu().numpy()
    return np.c_[xyxy[:, :2], xyxy[:, 2:] - xyxy[:, :2]] if len(xyxy) else np.zeros((0, 4))


def box_agreement(gt: np.ndarray, pred: np.ndarray) -> list[dict[str, float]]:
    """Per GT box (xywh): best-IoU prediction and normalised offsets (/GT height)."""
    from ..eval.detection import iou_matrix
    out = []
    if len(gt) == 0:
        return out
    iou = iou_matrix(gt, pred) if len(pred) else np.zeros((len(gt), 0))
    for i, g in enumerate(gt):
        if iou.shape[1] == 0 or iou[i].max() <= 0:
            out.append({"iou": 0.0, "h": float(g[3])})
            continue
        j = int(iou[i].argmax())
        p = pred[j]
        h = g[3]
        out.append({"iou": float(iou[i, j]), "h": float(h),
                    "d_cx": float((p[0] + p[2] / 2 - g[0] - g[2] / 2) / h),
                    "d_top": float((p[1] - g[1]) / h),
                    "d_bottom": float((p[1] + p[3] - g[1] - g[3]) / h),
                    "h_ratio": float(p[3] / h), "w_ratio": float(p[2] / max(g[2], 1e-6))})
    return out


def summarise(recs: list[dict[str, float]]) -> dict[str, Any]:
    iou = np.array([r["iou"] for r in recs])
    m = [r for r in recs if r["iou"] >= 0.3]   # "the same person" - offsets only for these
    s: dict[str, Any] = {"n_gt": len(recs), "iou_median": round(float(np.median(iou)), 3),
                         "iou_p10": round(float(np.percentile(iou, 10)), 3),
                         "iou_p90": round(float(np.percentile(iou, 90)), 3),
                         "frac_iou_ge_0.5": round(float((iou >= 0.5).mean()), 3),
                         "frac_iou_ge_0.7": round(float((iou >= 0.7).mean()), 3),
                         "frac_unmatched_lt_0.3": round(float((iou < 0.3).mean()), 3),
                         "n_matched": len(m)}
    for k in ("d_cx", "d_top", "d_bottom", "h_ratio", "w_ratio"):
        v = np.array([r[k] for r in m])
        s[k] = {"median": round(float(np.median(v)), 3), "p10": round(float(np.percentile(v, 10)), 3),
                "p90": round(float(np.percentile(v, 90)), 3)} if len(v) else None
    # tight-match IoU (only matched pairs): isolates box-fit from detection misses
    s["iou_median_matched"] = round(float(np.median([r["iou"] for r in m])), 3) if m else None
    return s


def _draw(img, gt, pred, path: Path):
    import cv2
    im = img.copy()
    for x, y, w, h in pred:
        cv2.rectangle(im, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 1)
    for x, y, w, h in gt:
        cv2.rectangle(im, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), im)


def label_quality(cfg, out: Path) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    lq = cfg["label_quality"]
    model = YOLO(str(rpath(cfg["model"])))
    rng = np.random.default_rng(int(cfg.get("seed", 0)))
    batch = rpath(cfg["batch_dir"])
    res: dict[str, Any] = {}
    for src in lq["synthetic_sources"]:
        pool = []
        for run in lq["synthetic_runs"]:
            for cam, c in batch_cameras(batch, run, src).items():
                pool += [(run, cam, f, c["frames"][f], c["gt"][f]) for f in sorted(c["frames"])
                         if f >= 1 and c["gt"].get(f)]
        pick = [pool[i] for i in sorted(rng.choice(len(pool), min(lq["n_frames"], len(pool)), replace=False))]
        recs = []
        for k, (run, cam, f, png, rows) in enumerate(pick):
            img = cv2.imread(str(png))
            rows = [r for r in rows if r["bbox"][3] >= lq["min_h"] and r.get("vis", 1) >= lq["min_vis"]]
            g = np.array([r["bbox"] for r in rows], float).reshape(-1, 4)
            p = _yolo_boxes(model, img, lq["conf"])
            recs += box_agreement(g, p)
            if k < lq.get("n_overlays", 30):
                _draw(img, g, p, out / "overlays" / src / f"{run}_{cam}_{f:04d}.jpg")
        res[f"synthetic_{src}"] = summarise(recs)
    for seq in lq["real_sequences"]:
        d = rpath(cfg["mot20_root"]) / "train" / seq
        gt = read_mot_rows(d / "gt" / "gt.txt")
        frames = sorted(rng.choice(np.arange(1, 301), lq["n_frames"], replace=False))
        recs = []
        for k, f in enumerate(frames):
            img = cv2.imread(str(d / "img1" / f"{int(f):06d}.jpg"))
            rows = [r for r in gt.get(int(f), []) if r["bbox"][3] >= lq["min_h"] and r.get("vis", 1) >= lq["min_vis"]]
            g = np.array([r["bbox"] for r in rows], float).reshape(-1, 4)
            p = _yolo_boxes(model, img, lq["conf"])
            recs += box_agreement(g, p)
            if k < 5:
                _draw(img, g, p, out / "overlays" / "real" / f"{seq}_{int(f):06d}.jpg")
        res[f"real_{seq}"] = summarise(recs)
    return res


def image_stats(cfg, out: Path) -> dict[str, Any]:
    import cv2

    from survsim.realism.stats import FrameStats, band, frame_stats
    st = cfg["image_stats"]
    rng = np.random.default_rng(int(cfg.get("seed", 0)))
    batch = rpath(cfg["batch_dir"])

    def measure(paths):
        paths = [paths[i] for i in sorted(rng.choice(len(paths), min(st["n_frames"], len(paths)), replace=False))]
        rows = [frame_stats(cv2.imread(str(p))).as_dict() for p in paths]
        return {k: band(r[k] for r in rows) for k in FrameStats.keys()}  # noqa: SIM118 - dataclass classmethod

    ref_dir = rpath(cfg["mot20_root"]) / "train" / st["reference"] / "img1"
    ref = measure(sorted(ref_dir.glob("*.jpg"))[:300])
    sets = {}
    for name, spec in st["sets"].items():
        paths = []
        for src in spec.get("sources", []):
            for run in st["synthetic_runs"]:
                for c in batch_cameras(batch, run, src).values():
                    paths += [p for f, p in sorted(c["frames"].items()) if f >= 1]
        if spec.get("real"):
            paths += sorted((rpath(cfg["mot20_root"]) / "train" / spec["real"] / "img1").glob("*.jpg"))[:60]
        sets[name] = measure(paths)
    res: dict[str, Any] = {"reference": st["reference"], "reference_band": ref, "sets": {}}
    for name, s in sets.items():
        z, inb = {}, 0
        for k in FrameStats.keys():  # noqa: SIM118
            r = ref[k]
            spread = max(r["p90"] - r["p10"], 1e-9)
            z[k] = round((s[k]["median"] - r["median"]) / spread, 3)
            inb += int(r["p10"] <= s[k]["median"] <= r["p90"])
        ap = None
        src = st["sets"][name].get("ap_from")
        if src:
            f = rpath(src[0])
            if f.is_file():
                e = json.loads(f.read_text())["arms"].get(src[1], {}).get("eval", {}).get(src[2])
                ap = e and {"AP": e["AP"], "AP50": e["AP50"], "from": "/".join(src[1:])}
        res["sets"][name] = {"medians": {k: round(s[k]["median"], 4) for k in FrameStats.keys()},  # noqa: SIM118
                             "z": z, "mean_abs_z": round(float(np.mean(np.abs(list(z.values())))), 3),
                             "in_band": inb, "n_stats": len(z), "real_ap": ap}
    return res


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    res = {"label_quality": label_quality(cfg, out)}
    write_json(out / "partial.json", res)
    res["image_stats"] = image_stats(cfg, out)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [("Label quality: GT vs best zero-shot YOLOv8n box (imgsz 1280, conf "
         f"{cfg['label_quality']['conf']}), GT >= {cfg['label_quality']['min_h']} px, "
         f"vis >= {cfg['label_quality']['min_vis']}; offsets / GT height, over pairs with IoU >= 0.3"), "",
         ("| set | GT | IoU med | IoU p10 | IoU>=.5 | IoU>=.7 | no match | IoU med (matched) | "
         "d_top med | d_bottom med | d_cx med | h ratio med | w ratio med |"),
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, s in res["label_quality"].items():
        f = lambda k, s=s: f"{s[k]['median']:+.3f}" if s.get(k) else "-"
        L.append(f"| {name} | {s['n_gt']} | {s['iou_median']:.3f} | {s['iou_p10']:.3f} | "
                 f"{s['frac_iou_ge_0.5']:.3f} | {s['frac_iou_ge_0.7']:.3f} | {s['frac_unmatched_lt_0.3']:.3f} | "
                 f"{s['iou_median_matched']} | {f('d_top')} | {f('d_bottom')} | {f('d_cx')} | "
                 f"{s['h_ratio']['median']:.3f} | {s['w_ratio']['median']:.3f} |")
    im = res["image_stats"]
    L += ["", (f"Image statistics vs {im['reference']} (docs/15 frame stats; z = (median - real median) / "
          "real p10-p90 spread)"), "",
          ("| training set | in real band | mean abs z | noise z | lap_var z | mtf z | chroma z | "
          "luma z | real AP (arm) |"), "|---|---|---|---|---|---|---|---|---|"]
    for name, s in im["sets"].items():
        z = s["z"]
        ap = s["real_ap"]
        L.append(f"| {name} | {s['in_band']}/{s['n_stats']} | {s['mean_abs_z']:.2f} | "
                 f"{z['noise_sigma']:+.2f} | {z['lap_var_log10']:+.2f} | {z['mtf_ratio']:+.2f} | "
                 f"{z['chroma_mean']:+.2f} | {z['luma_mean']:+.2f} | "
                 + (f"{ap['AP']:.3f} ({ap['from']})" if ap else "-") + " |")
    return "\n".join(L) + "\n"
