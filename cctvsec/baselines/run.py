"""Run det / MOT / ReID baselines over a dataset manifest and write JSON + markdown."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from survsim.datasets.build import load_manifest, read_gt
from .bytetrack import track_sequence
from .metrics import coco_map

DET_CONF = 0.01          # low floor for mAP; operational metrics use OPERATING_CONF
OPERATING_CONF = 0.25


def _abs(root: str, p: str) -> str:
    return p if Path(p).is_absolute() else str(Path(root) / p)


def _sequences(m: dict[str, Any]):
    for run in m["runs"]:
        for cam, c in run["cameras"].items():
            yield run, cam, c


def detect(m: dict[str, Any], out: Path, model: str = "yolo11n.pt", imgsz: int = 1280,
           batch: int = 8) -> dict[str, dict[int, list[dict]]]:
    """Run (or load cached) person detections for every sequence."""
    cache = out / "detections.json"
    if cache.is_file():
        raw = json.loads(cache.read_text())
        return {k: {int(f): v for f, v in d.items()} for k, d in raw.items()}
    from ultralytics import YOLO

    net = YOLO(model)
    result: dict[str, dict[int, list[dict]]] = {}
    for run, cam, c in _sequences(m):
        key = f"{run['name']}/{cam}"
        frames = sorted(c["frames"], key=int)
        per: dict[int, list[dict]] = {}
        for i in range(0, len(frames), batch):
            chunk = frames[i:i + batch]
            preds = net.predict([_abs(m["_root"], c["frames"][f]) for f in chunk], classes=[0],
                                conf=DET_CONF, imgsz=imgsz, verbose=False, half=True, max_det=1000)
            for f, p in zip(chunk, preds):
                xyxy = p.boxes.xyxy.cpu().numpy()
                sc = p.boxes.conf.cpu().numpy()
                per[int(f)] = [{"bbox": [float(a), float(b), float(x - a), float(y - b)], "score": float(s)}
                               for (a, b, x, y), s in zip(xyxy, sc)]
        result[key] = per
    cache.write_text(json.dumps(result))
    return result


def _gt(m, c):
    targets, ignore = read_gt(Path(_abs(m["_root"], c["gt"])))
    keep = {int(f) for f in c["frames"]}
    return [r for r in targets if r["frame"] in keep], [r for r in ignore if r["frame"] in keep]


def _group(rows):
    out: dict[int, list] = {}
    for r in rows:
        out.setdefault(r["frame"], []).append(r)
    return out


def eval_det(m, dets) -> dict[str, Any]:
    from ..eval.detection import evaluate

    per_seq, keys, G, I, P = {}, [], {}, {}, {}
    op_gt, op_pred = {}, {}
    for run, cam, c in _sequences(m):
        key = f"{run['name']}/{cam}"
        tg, ig = _group(_gt(m, c)[0]), _group(_gt(m, c)[1])
        k = [(key, int(f)) for f in c["frames"]]
        g = {(key, f): v for f, v in tg.items()}
        i = {(key, f): v for f, v in ig.items()}
        p = {(key, f): v for f, v in dets[key].items()}
        per_seq[key] = coco_map(k, g, i, p)
        keys += k; G.update(g); I.update(i); P.update(p)
        op_gt.update(g)
        op_pred.update({kk: [d for d in v if d["score"] >= OPERATING_CONF] for kk, v in p.items()})
    fps = float(np.mean([c["fps"] for _, _, c in _sequences(m)]))
    op = evaluate(op_gt, op_pred, fps=fps, stratify=None).as_dict()
    return {"all": coco_map(keys, G, I, P), "per_sequence": per_seq,
            "operating_point": {"conf": OPERATING_CONF, **{k: op[k] for k in
                                ("precision", "recall", "fppi", "false_alarms_per_camera_hour")}}}


def eval_mot(m, dets) -> dict[str, Any]:
    from ..eval.tracking import evaluate_mot

    per_seq, all_g, all_p = {}, [], []
    for n, (run, cam, c) in enumerate(_sequences(m)):
        key = f"{run['name']}/{cam}"
        frames = sorted(int(f) for f in c["frames"])
        tracks = track_sequence(dets[key], frames, max_lost=int(c["fps"]))
        gt, ignore = _gt(m, c)
        tracks = _drop_ignored(tracks, ignore)
        per_seq[key] = evaluate_mot(gt, tracks).as_dict()
        off = (n + 1) * 10_000_000
        all_g += [{**r, "frame": r["frame"] + off, "id": f"{n}:{r['id']}"} for r in gt]
        all_p += [{**r, "frame": r["frame"] + off, "id": f"{n}:{r['id']}"} for r in tracks]
    return {"all": evaluate_mot(all_g, all_p).as_dict(), "per_sequence": per_seq,
            "tracker": "ByteTrack (numpy, cctvsec.baselines.bytetrack), no CMC"}


def _drop_ignored(tracks, ignore, thr=0.5):
    """MOTChallenge preprocessing: predictions on ignore regions are not FPs."""
    from ..eval.detection import iou_matrix

    ig = _group(ignore)
    out = []
    for t in tracks:
        g = ig.get(t["frame"])
        if g and iou_matrix(np.array([t["bbox"]]), np.array([r["bbox"] for r in g])).max() >= thr:
            continue
        out.append(t)
    return out


# ------------------------------------------------------------------ ReID

def _embedder():
    """OSNet (torchreid) if its weights load, else ResNet50-ImageNet pooled features."""
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        try:
            from torchreid.reid.utils import FeatureExtractor
        except ImportError:
            from torchreid.utils import FeatureExtractor
        fx = FeatureExtractor(model_name="osnet_x1_0", device=dev)
        return "osnet_x1_0 (torchreid, ImageNet-pretrained)", lambda crops: fx(crops).cpu().numpy()
    except Exception as exc:  # noqa: BLE001 - any weight/download failure -> fallback
        import torchvision
        net = torchvision.models.resnet50(weights="IMAGENET1K_V2")
        net.fc = torch.nn.Identity()
        net.eval().to(dev)
        mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)

        def f(crops):
            import cv2
            x = np.stack([cv2.resize(c[:, :, ::-1], (128, 256)) for c in crops]).astype(np.float32) / 255
            t = (torch.from_numpy(x).permute(0, 3, 1, 2).to(dev) - mean) / std
            with torch.no_grad():
                return net(t).cpu().numpy()
        return f"resnet50 ImageNet (fallback: {type(exc).__name__})", f


def sample_crops(m, per_id: int = 4, min_h: float = 48, min_vis: float = 0.6):
    """Pick up to `per_id` well-spaced GT crops per (identity, camera)."""
    items = []   # (pid, camera, frame, path, bbox)
    for run, cam, c in _sequences(m):
        gt, _ = _gt(m, c)
        by_id: dict[Any, list] = {}
        for r in gt:
            if r["bbox"][3] >= min_h and r["vis"] >= min_vis and str(r["frame"]) in c["frames"]:
                by_id.setdefault(r["id"], []).append(r)
        for pid, rows in by_id.items():
            rows.sort(key=lambda r: r["frame"])
            pick = [rows[int(i)] for i in np.linspace(0, len(rows) - 1, min(per_id, len(rows)))]
            for r in pick:
                items.append((f"{run['name']}:{pid}", cam, r["frame"],
                              _abs(m["_root"], c["frames"][str(r["frame"])]), r["bbox"], c["fps"]))
    return items


def reid_protocol(items) -> tuple[np.ndarray, np.ndarray, str]:
    """Query set + exclusion mask.

    Cross-camera when identities appear on >1 camera (the real re-id question);
    otherwise cross-time: same-camera gallery entries within 5 s of the query are
    excluded, so a match cannot come from a near-identical neighbouring frame.
    """
    pids = np.array([i[0] for i in items])
    cams = np.array([i[1] for i in items])
    frames = np.array([i[2] for i in items])
    fps = np.array([i[5] for i in items])
    multi = len(set(cams)) > 1 and any(len(set(cams[pids == p])) > 1 for p in set(pids))
    if multi:
        excl = cams[:, None] == cams[None, :]
        mode = "cross-camera"
    else:
        excl = (cams[:, None] == cams[None, :]) & (np.abs(frames[:, None] - frames[None, :]) < 5 * fps[:, None])
        mode = "cross-time (>=5 s apart, single camera)"
    return pids, excl, mode


def eval_reid(m, max_items: int = 4000, seed: int = 0) -> dict[str, Any]:
    import cv2

    from ..eval.tracking import evaluate_reid

    items = sample_crops(m)
    if len(items) > max_items:
        rng = np.random.default_rng(seed)
        items = [items[i] for i in sorted(rng.choice(len(items), max_items, replace=False))]
    if not items:
        return {"error": "no usable crops"}
    name, embed = _embedder()
    feats, cache = [], {}
    crops = []
    for pid, cam, f, path, (x, y, w, h), _ in items:
        img = cache.setdefault(path, cv2.imread(path))
        if len(cache) > 64:
            cache.pop(next(iter(cache)))
        H, W = img.shape[:2]
        x0, y0 = max(int(x), 0), max(int(y), 0)
        x1, y1 = min(int(x + w), W), min(int(y + h), H)
        crops.append(img[y0:max(y1, y0 + 2), x0:max(x1, x0 + 2)][:, :, ::-1].copy()
                     if name.startswith("osnet") else img[y0:max(y1, y0 + 2), x0:max(x1, x0 + 2)])
    for i in range(0, len(crops), 64):
        feats.append(embed(crops[i:i + 64]))
    F = np.concatenate(feats)
    F /= np.linalg.norm(F, axis=1, keepdims=True) + 1e-9
    pids, excl, mode = reid_protocol(items)
    excl = excl | np.eye(len(items), dtype=bool)
    res = evaluate_reid(pids, pids, F @ F.T, exclude=excl, scope=mode).as_dict()
    return {"model": name, "n_crops": len(items), "n_identities": len(set(pids)), **res}


# ------------------------------------------------------------------ report

class NonCommercialDatasetError(RuntimeError):
    """A dataset manifest's `commercial_ml_ok` is false and --allow-noncommercial was not passed."""


def run_baselines(dataset_dir: Path, task: str = "all", out: Path | None = None,
                  model: str = "yolo11n.pt", imgsz: int = 1280,
                  allow_noncommercial: bool = False) -> dict[str, Any]:
    m = load_manifest(dataset_dir)
    commercial_ml_ok = bool(m.get("commercial_ml_ok", False))
    if not commercial_ml_ok and not allow_noncommercial:
        blockers = sorted({i for r in m.get("runs", []) for i in r.get("licences", {}).get("asset_licences", [])}
                          | set(m.get("asset_licences", [])))
        raise NonCommercialDatasetError(
            f"dataset {dataset_dir} is not commercial_ml_ok (asset licences: {blockers or ['unknown']}, "
            "docs/research/47): refusing to produce baseline numbers from non-commercial/unlicensed "
            "assets. Pass --allow-noncommercial to compute them anyway as internal evidence only.")
    out = Path(out or Path(dataset_dir) / "baselines")
    out.mkdir(parents=True, exist_ok=True)
    res: dict[str, Any] = {"dataset": m["_root"], "kind": m["kind"],
                           "synthetic_topdown": m.get("synthetic_topdown", False),
                           "commercial_ml_ok": commercial_ml_ok,
                           "asset_licences": m.get("asset_licences", []),
                           "note": m.get("note"), "detector": model, "imgsz": imgsz,
                           "n_sequences": sum(1 for _ in _sequences(m)),
                           "n_frames": sum(len(c["frames"]) for *_, c in _sequences(m))}
    t0 = time.time()
    if task in ("det", "mot", "all"):
        dets = detect(m, out, model, imgsz)
        if task in ("det", "all"):
            res["det"] = eval_det(m, dets)
        if task in ("mot", "all"):
            res["mot"] = eval_mot(m, dets)
    if task in ("reid", "all"):
        res["reid"] = eval_reid(m)
    res["seconds"] = round(time.time() - t0, 1)
    (out / f"results_{task}.json").write_text(json.dumps(res, indent=1))
    (out / f"results_{task}.md").write_text(markdown(res))
    return res


def markdown(r: dict[str, Any]) -> str:
    flag = " **(synthetic_topdown: mock silhouettes, not a model result)**" if r["synthetic_topdown"] else ""
    lines = [f"# Baselines: {Path(r['dataset']).name}{flag}", ""]
    if not r.get("commercial_ml_ok", True):
        licences = ', '.join(r.get('asset_licences', [])) or 'unknown licence'
        lines += [("> **INTERNAL EVIDENCE ONLY — non-commercial assets "
                   f"({licences})**  "
                   "These numbers must not be reported as product performance "
                   "(docs/research/47; run with `--allow-noncommercial` was required)."), ""]
    lines += [f"{r['n_sequences']} sequences, {r['n_frames']} frames; detector {r['detector']} @ {r['imgsz']}", ""]
    if "det" in r:
        a, op = r["det"]["all"], r["det"]["operating_point"]
        lines += ["| Detection | AP | AP50 | AP75 | AR | P@0.25 | R@0.25 | FA/cam-h |", "|---|---|---|---|---|---|---|---|",
                  (f"| all | {a['AP']:.3f} | {a['AP50']:.3f} | {a['AP75']:.3f} | {a.get('AR_max', 0):.3f} | "
                   f"{op['precision']:.3f} | {op['recall']:.3f} | {op['false_alarms_per_camera_hour']:.0f} |"), ""]
    if "mot" in r:
        lines += ["| MOT | MOTA | IDF1 | HOTA | DetA | AssA | IDsw |", "|---|---|---|---|---|---|---|"]
        for k, v in [("all", r["mot"]["all"]), *r["mot"]["per_sequence"].items()]:
            lines.append(f"| {k} | {v['mota']:.3f} | {v['idf1']:.3f} | {v['hota']:.3f} | {v['deta']:.3f} | "
                         f"{v['assa']:.3f} | {v['id_switches']} |")
        lines.append("")
    if "reid" in r and "rank1" in r["reid"]:
        v = r["reid"]
        lines += ["| ReID | model | protocol | ids | rank-1 | rank-5 | mAP |", "|---|---|---|---|---|---|---|",
                  (f"| all | {v['model']} | {v['scope']} | {v['n_identities']} | {v['rank1']:.3f} | "
                   f"{v['rank5']:.3f} | {v['mAP']:.3f} |"), ""]
    return "\n".join(lines) + "\n"
