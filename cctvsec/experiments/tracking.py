"""H9: zero-shot yolov8n + numpy ByteTrack on batch_v7 vs GT, and the docs/13
ByteTrack fix (tau 0.6 + gate-before-solve) as a flag, on batch_v7 and MOT20."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import batch_cameras, rpath, wait_for_gpu, write_json

VARIANTS = {"old": {}, "fixed": {"fixed": True}, "gate_only": {"gate": True},
            "tau_only": {"high": 0.6}}


# ------------------------------------------------------------------ stats

def boot_ci(x, n: int = 10000, seed: int = 0, alpha: float = 0.05) -> dict[str, Any]:
    """Mean and percentile-bootstrap CI over the units in x."""
    x = np.asarray([v for v in x if v is not None], float)
    if len(x) == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0}
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return {"mean": round(float(x.mean()), 4), "lo": round(float(np.quantile(m, alpha / 2)), 4),
            "hi": round(float(np.quantile(m, 1 - alpha / 2)), 4), "n": len(x)}


def boot_diff(a, b, n: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Unpaired difference of means mean(a) - mean(b), bootstrap each group."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    d = (a[rng.integers(0, len(a), (n, len(a)))].mean(1)
         - b[rng.integers(0, len(b), (n, len(b)))].mean(1))
    return {"diff": round(float(a.mean() - b.mean()), 4), "lo": round(float(np.quantile(d, .025)), 4),
            "hi": round(float(np.quantile(d, .975)), 4), "n_a": len(a), "n_b": len(b)}


def boot_p_two_sided(x, n: int = 10000, seed: int = 0) -> float:
    """Bootstrap p for mean(x) == 0 (sign-flip of the centred resamples)."""
    x = np.asarray(x, float)
    if len(x) < 2:
        return 1.0
    rng = np.random.default_rng(seed)
    m = (x - x.mean())[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return float(min(1.0, (np.abs(m) >= abs(x.mean())).mean() + 1 / n))


def holm(ps: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    out, k = {}, len(ps)
    stop = False
    for i, (name, p) in enumerate(sorted(ps.items(), key=lambda kv: kv[1])):
        ok = (not stop) and p <= alpha / (k - i)
        stop = stop or not ok
        out[name] = ok
    return out


def wilson(k: int, n: int, z: float = 1.96) -> dict[str, Any]:
    if n == 0:
        return {"p": None, "lo": None, "hi": None, "n": 0}
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"p": round(p, 4), "lo": round(float(c - h), 4), "hi": round(float(c + h), 4), "n": n}


# ------------------------------------------------------------------ detection

def detect_paths(model: str, paths: dict[int, str], cache: Path, imgsz: int, conf: float,
                 batch: int = 8) -> dict[int, list[dict]]:
    """frame -> [{bbox xywh, score}] for person class; cached as JSON."""
    if cache.is_file():
        return {int(k): v for k, v in json.loads(cache.read_text()).items()}
    from ultralytics import YOLO
    net = YOLO(str(rpath(model)))
    frames = sorted(paths)
    out: dict[int, list[dict]] = {}
    for i in range(0, len(frames), batch):
        ch = frames[i:i + batch]
        preds = net.predict([str(paths[f]) for f in ch], classes=[0], conf=conf, imgsz=imgsz,
                            verbose=False, half=True, max_det=1000)
        for f, p in zip(ch, preds):
            xyxy = p.boxes.xyxy.cpu().numpy()
            sc = p.boxes.conf.cpu().numpy()
            out[f] = [{"bbox": [float(a), float(b), float(x - a), float(y - b)], "score": float(s)}
                      for (a, b, x, y), s in zip(xyxy, sc)]
    write_json(cache, out)
    return out


def v7_sequences(cfg) -> list[dict[str, Any]]:
    batch = rpath(cfg["batch_dir"])
    seqs = []
    for run in cfg["runs"]:
        for cam, c in batch_cameras(batch, run, "raw").items():
            frames = sorted(f for f in c["frames"] if 1 <= f <= cfg["max_frame"])
            gt = [{**r, "frame": f} for f in frames for r in c["gt"].get(f, [])]
            hs = [r["bbox"][3] for r in gt]
            seqs.append({"key": f"{run}/{cam}", "run": run, "cam": cam,
                         "scenario": run.rsplit("_", 1)[0], "light": run.rsplit("_", 1)[1],
                         "frames": frames, "paths": {f: str(c["frames"][f]) for f in frames},
                         "gt": gt, "ignore": [], "fps": cfg["fps"],
                         "median_gt_h": float(np.median(hs)) if hs else None})
    return seqs


def mot20_sequences(cfg) -> list[dict[str, Any]]:
    from ..baselines.run import _abs, _gt, _sequences
    from survsim.datasets.build import load_manifest
    m = load_manifest(rpath(cfg["mot20_subset"]))
    seqs = []
    for run, cam, c in _sequences(m):
        gt, ign = _gt(m, c)
        frames = sorted(int(f) for f in c["frames"])
        seqs.append({"key": f"{run['name']}/{cam}", "run": run["name"], "cam": cam,
                     "scenario": "MOT20", "light": "day", "frames": frames,
                     "paths": {int(f): _abs(m["_root"], p) for f, p in c["frames"].items()},
                     "gt": gt, "ignore": ign, "fps": c["fps"],
                     "median_gt_h": float(np.median([r["bbox"][3] for r in gt]))})
    return seqs


def score(seq, dets, variant: dict[str, Any]) -> dict[str, Any]:
    from ..baselines.bytetrack import track_sequence
    from ..baselines.run import _drop_ignored
    from ..eval.tracking import evaluate_mot
    tr = track_sequence(dets, seq["frames"], max_lost=int(seq["fps"]), **variant)
    tr = _drop_ignored(tr, seq["ignore"]) if seq["ignore"] else tr
    return {"metrics": evaluate_mot(seq["gt"], tr).as_dict(), "tracks": tr}


def pooled(seqs, tracks_by_key) -> dict[str, Any]:
    from ..eval.tracking import evaluate_mot
    g, p = [], []
    for n, s in enumerate(seqs):
        off = (n + 1) * 10_000_000
        g += [{**r, "frame": r["frame"] + off, "id": f"{n}:{r['id']}"} for r in s["gt"]]
        p += [{**r, "frame": r["frame"] + off, "id": f"{n}:{r['id']}"} for r in tracks_by_key[s["key"]]]
    return evaluate_mot(g, p).as_dict()


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    gpu = wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=900)
    datasets = {"batch_v7": v7_sequences(cfg), "mot20_sub": mot20_sequences(cfg)}
    res: dict[str, Any] = {"gpu_wait": gpu, "sequences": {}, "pooled": {}}
    for dname, seqs in datasets.items():
        tracks: dict[str, dict] = {v: {} for v in VARIANTS}
        for s in seqs:
            dets = detect_paths(cfg["model"], s["paths"], out / "dets" / (s["key"].replace("/", "__") + ".json"),
                                cfg["imgsz"], cfg["det_conf"])
            row = {k: s[k] for k in ("run", "cam", "scenario", "light", "median_gt_h")}
            row["n_gt"] = len(s["gt"])
            row["n_frames"] = len(s["frames"])
            for v, kw in VARIANTS.items():
                r = score(s, dets, kw)
                row[v] = r["metrics"]
                tracks[v][s["key"]] = r["tracks"]
            res["sequences"][f"{dname}:{s['key']}"] = row
        res["pooled"][dname] = {v: pooled(seqs, tracks[v]) for v in VARIANTS}
    res["analysis"] = analyse(res, cfg)
    return res


def analyse(res, cfg) -> dict[str, Any]:
    rows = {k: v for k, v in res["sequences"].items() if k.startswith("batch_v7:") and v["n_gt"] > 0}
    mot = {k: v for k, v in res["sequences"].items() if k.startswith("mot20_sub:")}
    a: dict[str, Any] = {}
    # night - day, paired by (scenario, cam)
    pairs = []
    for k, v in rows.items():
        if v["light"] == "day":
            nk = k.replace("_day/", "_night/")
            if nk in rows:
                pairs.append((k, nk))
    for metric in ("hota", "mota", "idf1", "deta", "assa"):
        d = [rows[n]["old"][metric] - rows[d_]["old"][metric] for d_, n in pairs]
        a[f"night_minus_day_{metric}"] = {**boot_ci(d), "p": round(boot_p_two_sided(d), 4)}
    dedup = [(d_, n) for d_, n in pairs if not (d_.startswith("batch_v7:street_crowd_far_day/cam_01"))]
    d = [rows[n]["old"]["hota"] - rows[d_]["old"]["hota"] for d_, n in dedup]
    a["night_minus_day_hota_dedup_cam01"] = boot_ci(d)
    a["n_pairs"] = len(pairs)
    far = [v["old"]["hota"] for v in rows.values() if v["median_gt_h"] < cfg["far_px"]]
    near = [v["old"]["hota"] for v in rows.values() if v["median_gt_h"] >= cfg["far_px"]]
    a["far_minus_near_hota"] = boot_diff(far, near) if far and near else None
    if far and near:
        rng = np.random.default_rng(0)
        allv = np.array(far + near)
        obs = np.mean(far) - np.mean(near)
        perm = [np.mean(p[:len(far)]) - np.mean(p[len(far):])
                for p in (rng.permutation(allv) for _ in range(10000))]
        a["far_minus_near_hota"]["p_perm"] = round(float((np.abs(perm) >= abs(obs)).mean()), 4)
    ps = {"night_minus_day": a["night_minus_day_hota"]["p"]}
    if a["far_minus_near_hota"]:
        ps["far_minus_near"] = a["far_minus_near_hota"]["p_perm"]
    a["holm_reject"] = holm(ps)
    for name, rr in (("batch_v7", rows), ("mot20_sub", mot)):
        det_lim = [v["old"]["deta"] < v["old"]["assa"] for v in rr.values()]
        a[f"{name}_detection_limited_frac"] = round(float(np.mean(det_lim)), 4) if det_lim else None
    for v in ("fixed", "gate_only", "tau_only"):
        for name, rr in (("batch_v7", rows), ("mot20_sub", mot)):
            d = [x[v]["hota"] - x["old"]["hota"] for x in rr.values()]
            a[f"{v}_minus_old_hota_{name}"] = boot_ci(d)
    po = res["pooled"]
    adopt = all(po[n]["fixed"]["hota"] > po[n]["old"]["hota"]
                and po[n]["fixed"]["idf1"] >= po[n]["old"]["idf1"] - 0.005 for n in po)
    a["adopt_fixed"] = bool(adopt)
    return a


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = ["| sequence | light | med GT h | n_gt | HOTA | DetA | AssA | MOTA | IDF1 | IDsw | HOTA fixed |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["sequences"].items():
        o = v["old"]
        L.append(f"| {k} | {v['light']} | {v['median_gt_h'] or 0:.0f} | {v['n_gt']} | {o['hota']:.3f} | "
                 f"{o['deta']:.3f} | {o['assa']:.3f} | {o['mota']:.3f} | {o['idf1']:.3f} | "
                 f"{o['id_switches']} | {v['fixed']['hota']:.3f} |")
    L += ["", "| dataset | variant | HOTA | DetA | AssA | MOTA | IDF1 | IDsw |", "|---|---|---|---|---|---|---|---|"]
    for d, vv in res["pooled"].items():
        for v, o in vv.items():
            L.append(f"| {d} | {v} | {o['hota']:.4f} | {o['deta']:.4f} | {o['assa']:.4f} | {o['mota']:.4f} | "
                     f"{o['idf1']:.4f} | {o['id_switches']} |")
    L += ["", "```", json.dumps(res["analysis"], indent=1), "```"]
    return "\n".join(L) + "\n"
