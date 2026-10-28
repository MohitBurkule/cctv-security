"""H24: does appearance (ReID) in ByteTrack association raise AssA?

Arms differ only in the stage-1 cost of the numpy ByteTrack
(`cctvsec/baselines/bytetrack.py`, `app_weight`): control IoU-only vs
(1 - IoU) + w * (1 - cos) with OSNet-ImageNet, an HSV histogram, or an OSNet
fine-tuned on synthetic crops (H20 recipe, seed 0, retrained because H20 kept
no weights). Detections: the 5 h14b mix_300 checkpoints (cached from H17 on
MOT20-02; run once and cached on batch_v8 day). A GT-box arm (jittered GT, no
detector) separates association from detection (73 §6). Every metric is the
reference TrackEval through `cctvsec.eval.trackeval_bridge`. Pre-registered in
docs/research/32 §H24."""
from __future__ import annotations

import itertools
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, wait_for_gpu, write_json
from .tracking import detect_paths, mot20_sequences, v7_sequences

KEYS = ("hota", "deta", "assa", "assa_mean", "deta_mean", "idf1", "id_switches", "mota")


# ------------------------------------------------------------------ embeddings

def _crops(seq: dict[str, Any], dets: dict[int, list[dict]], min_score: float):
    """(frame, det index) keys and BGR crops of dets with score >= min_score."""
    import cv2
    keys, out = [], []
    for f in seq["frames"]:
        ds = [(i, d) for i, d in enumerate(dets.get(f, [])) if d["score"] >= min_score]
        if not ds:
            continue
        img = cv2.imread(str(seq["paths"][f]))
        H, W = img.shape[:2]
        for i, d in ds:
            x, y, w, h = d["bbox"]
            x0, y0 = min(max(int(x), 0), W - 2), min(max(int(y), 0), H - 2)
            x1, y1 = min(int(x + w), W), min(int(y + h), H)
            out.append(img[y0:max(y1, y0 + 2), x0:max(x1, x0 + 2)].copy())
            keys.append((f, i))
    return keys, out


def embedders(cfg: dict[str, Any], out: Path, dev: str) -> dict[str, Any]:
    """name -> callable(list[bgr]) -> (n, d) float32 unit rows."""
    from .reid import hsv_hist
    from .reid_train import build
    E: dict[str, Any] = {}
    for arm in cfg["arms"]:
        kind = arm.get("embedding")
        if kind is None:
            continue
        if kind == "hsv":
            E[arm["name"]] = lambda c: _norm(hsv_hist(c)) if c else np.zeros((0, 256), np.float32)
        elif kind == "osnet_imagenet":
            E[arm["name"]] = _osnet(build(10).to(dev), dev, cfg.get("embed_batch", 32))
        elif kind == "osnet_h20":
            E[arm["name"]] = _osnet(h20_model(cfg, out, dev), dev, cfg.get("embed_batch", 32))
        else:
            raise ValueError(kind)
    return E


def _osnet(model, dev: str, bs: int):
    from .reid_train import embed
    return lambda c: embed(model, c, dev, bs=bs)


def _norm(F):
    F = np.asarray(F, np.float32)
    return F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)


def h20_model(cfg: dict[str, Any], out: Path, dev: str):
    """H20 synthetic fine-tune, seed 0, same config; weights cached under out/weights."""
    import torch

    from cctvsec.experiments import load_config
    from .reid import crops
    from .reid_train import build, synth_items, train
    wp = out / "weights" / "osnet_h20_s0.pt"
    h20 = load_config(cfg["h20_config"])
    if wp.is_file():
        info = None
        sd = torch.load(wp, map_location=dev)
        m = build(sd["classifier.weight"].shape[0]).to(dev)
        m.load_state_dict(sd)
    else:
        wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=1800)
        items = synth_items(h20, h20["train_runs"], h20["train_per_id_per_cam"], epoch_ids=False)
        m, info = train(crops(items), [i["identity"] for i in items], h20, cfg.get("h20_seed", 0), dev)
        wp.parent.mkdir(parents=True, exist_ok=True)
        torch.save(m.state_dict(), wp)
        write_json(out / "weights" / "osnet_h20_s0.json", info)
    m.eval()
    return m


def attach(dets: dict[int, list[dict]], keys, F) -> dict[int, list[dict]]:
    """Copy of dets with d['emb'] set for the keyed ones."""
    out = {f: [dict(d) for d in v] for f, v in dets.items()}
    for (f, i), e in zip(keys, F):
        out[f][i]["emb"] = e
    return out


# ------------------------------------------------------------------ data

def gt_dets(seq: dict[str, Any], sigma: float, seed: int, score: float = 0.9) -> dict[int, list[dict]]:
    """GT boxes jittered by sigma * h on centre and size (seeded) as detections."""
    rng = np.random.default_rng(seed)
    out: dict[int, list[dict]] = {f: [] for f in seq["frames"]}
    for r in sorted(seq["gt"], key=lambda r: (r["frame"], str(r["id"]))):
        x, y, w, h = r["bbox"]
        dx, dy, dw, dh = rng.normal(0, sigma, 4) * h
        w2, h2 = max(w + dw, 2.0), max(h + dh, 2.0)
        cx, cy = x + w / 2 + dx, y + h / 2 + dy
        out.setdefault(r["frame"], []).append({"bbox": [cx - w2 / 2, cy - h2 / 2, w2, h2], "score": score})
    return out


def datasets(cfg: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    mot = [s for s in mot20_sequences(cfg) if s["run"] in cfg["mot20_sequences"]]
    bv = v7_sequences({"batch_dir": cfg["batch_dir"], "runs": cfg["batch_runs"],
                       "max_frame": cfg["max_frame"], "fps": cfg["batch_fps"]})
    return {"mot20": mot, "batch_v8": bv}


# ------------------------------------------------------------------ tracking + scoring

def track(seq, dets, app_weight: float, ema: float, app_only: bool = False) -> list[dict]:
    from ..baselines.bytetrack import track_sequence
    from ..baselines.run import _drop_ignored
    tr = track_sequence(dets, seq["frames"], max_lost=int(seq["fps"]), app_weight=app_weight, ema=ema,
                        app_only=app_only)
    return _drop_ignored(tr, seq["ignore"]) if seq["ignore"] else tr


def trackeval_score(seqs, tracks_by_key) -> dict[str, dict[str, float]]:
    from ..eval.trackeval_bridge import run_trackeval, write_motchallenge
    with tempfile.TemporaryDirectory() as td:
        lay = {s["key"].replace("/", "__"): (s["gt"], tracks_by_key[s["key"]]) for s in seqs}
        write_motchallenge(Path(td), lay)
        return run_trackeval(Path(td))


# ------------------------------------------------------------------ stats

def two_way_boot(D: np.ndarray, n: int = 10000, seed: int = 0) -> dict[str, Any]:
    """D[seq, unit]: mean and CI resampling sequences and units independently."""
    rng = np.random.default_rng(seed)
    S, U = D.shape
    bs = np.array([D[np.ix_(rng.integers(0, S, S), rng.integers(0, U, U))].mean() for _ in range(n)])
    return {"mean": round(float(D.mean()), 4), "boot95": [round(float(np.quantile(bs, .025)), 4),
                                                        round(float(np.quantile(bs, .975)), 4)],
            "n_seq": S, "n_units": U, "per_unit": [round(float(x), 4) for x in D.mean(0)]}


def unit_boot(d, n: int = 10000, seed: int = 0) -> dict[str, Any]:
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    flips = np.array(list(itertools.product([1, -1], repeat=len(d))))
    p = float((np.abs((flips * d).mean(1)) >= abs(d.mean()) - 1e-12).mean())
    return {"mean": round(float(d.mean()), 4), "boot95": [round(float(np.quantile(bs, .025)), 4),
                                                        round(float(np.quantile(bs, .975)), 4)],
            "signflip_p": round(p, 4), "diffs": [round(float(x), 4) for x in d], "n": len(d)}


def analyse(res: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    ctrl = cfg["control"]
    arms = [a["name"] for a in cfg["arms"] if a["name"] != ctrl]
    A: dict[str, Any] = {}
    for ds, block in res["scores"].items():
        units = sorted(block)
        seqs = sorted(k for k in block[units[0]][ctrl] if k != "COMBINED")
        A[ds] = {}
        for arm in arms:
            only = cfg.get("arm_sequences", {}).get(arm, {}).get(ds.split(":")[0])
            ss = [s for s in seqs if only is None or any(s.startswith(o) for o in only)]
            row: dict[str, Any] = {"sequences": ss}
            for m in ("assa_mean", "assa", "hota", "deta", "idf1", "id_switches"):
                D = np.array([[block[u][arm][s][m] - block[u][ctrl][s][m] for u in units] for s in ss])
                row[m] = two_way_boot(D) if len(ss) > 1 else unit_boot(D[0])
                row[m + "_combined"] = unit_boot([block[u][arm]["COMBINED"][m] - block[u][ctrl]["COMBINED"][m]
                                                  for u in units]) if len(ss) == len(seqs) else None
            dense = [s for s in ss if s.startswith(cfg.get("dense_prefix", "street_crowd_day"))]
            if dense and len(ss) > 1:
                D = np.array([[block[u][arm][s]["assa_mean"] - block[u][ctrl][s]["assa_mean"] for u in units]
                              for s in dense])
                row["assa_mean_dense"] = two_way_boot(D)
            A[ds][arm] = row
    # decision (pre-registered): batch_v8 dAssA >= 0.02 and CI lo > 0; MOT20 CI lo >= -0.005
    A["decision"] = {}
    for arm in arms:
        b, m = A.get("batch_v8", {}).get(arm), A.get("mot20", {}).get(arm)
        if not b or not m:
            continue
        bv = b["assa_mean"]["mean"] >= 0.02 and b["assa_mean"]["boot95"][0] > 0
        mv = m["assa_mean"]["boot95"][0] >= -0.005
        A["decision"][arm] = {"batch_v8_gain": bool(bv), "mot20_no_decrease": bool(mv), "met": bool(bv and mv)}
    return A


# ------------------------------------------------------------------ run

def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import torch
    gpu = wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=900)
    dev = "cuda" if torch.cuda.is_available() and gpu.get("free_mib", 0) >= cfg.get("min_free_mib", 2048) else "cpu"
    D = datasets(cfg)
    E = embedders(cfg, out, dev)
    res: dict[str, Any] = {"gpu_wait": gpu, "device": dev, "scores": {}, "n": {}}
    sources: list[tuple[str, str, Any]] = []   # (dataset label, unit, dets fn)
    for ck in cfg["checkpoints"]:
        for ds in ("mot20", "batch_v8"):
            sources.append((ds, ck["name"], ck))
    for s in cfg.get("gt_box_seeds", []):
        sources.append(("batch_v8:gt_boxes", f"gt_s{s}", s))
    for ds, unit, src in sources:
        seqs = D[ds.split(":")[0]]
        tracks: dict[str, dict[str, list]] = {a["name"]: {} for a in cfg["arms"]}
        for s in seqs:
            sk = s["key"].replace("/", "__")
            if ds.endswith("gt_boxes"):
                dets = gt_dets(s, cfg["gt_sigma"], int(src))
            else:
                cache = rpath(src["det_cache"][ds]) / f"{sk}.json" if ds in src.get("det_cache", {}) \
                    else out / "dets" / src["name"] / f"{sk}.json"
                dets = detect_paths(src["weights"], s["paths"], cache, cfg["imgsz"], cfg["det_conf"],
                                    batch=cfg.get("det_batch", 4))
            ecache = out / "emb" / ds.replace(":", "_") / unit / f"{sk}.npz"
            if ecache.is_file():
                z = np.load(ecache, allow_pickle=False)
                keys = [tuple(k) for k in z["keys"].tolist()]
                feats = {n: z[n] for n in E}
            else:
                keys, crops = _crops(s, dets, cfg["emb_min_score"])
                feats = {n: f(crops) for n, f in E.items()}
                ecache.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(ecache, keys=np.array(keys, int).reshape(-1, 2), **feats)
            res["n"].setdefault(ds, {}).setdefault(s["key"], {})[unit] = {
                "dets": sum(len(v) for v in dets.values()), "embedded": len(keys), "gt": len(s["gt"])}
            for a in cfg["arms"]:
                name = a["name"]
                d = attach(dets, keys, feats[name]) if name in E else dets
                tracks[name][s["key"]] = track(s, d, a.get("app_weight", 0.0), cfg.get("ema", 0.9))
        for a in cfg["arms"]:
            sc = trackeval_score(seqs, tracks[a["name"]])
            res["scores"].setdefault(ds, {}).setdefault(unit, {})[a["name"]] = {
                k.replace("__", "/"): {m: v[m] for m in KEYS} for k, v in sc.items()}
        write_json(out / "partial.json", res)
    res["analysis"] = analyse(res, cfg)
    try:
        figure(res, cfg, out / "fig_h24.png")
    except Exception as e:  # noqa: BLE001 - figure is cosmetic
        res["figure_error"] = repr(e)
    return res


def figure(res: dict[str, Any], cfg: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    A = res["analysis"]
    blocks = [b for b in ("mot20", "batch_v8", "batch_v8:gt_boxes") if b in A]
    fig, axes = plt.subplots(1, len(blocks), figsize=(4.2 * len(blocks), 3.4), sharey=False)
    for ax, b in zip(np.atleast_1d(axes), blocks):
        arms = list(A[b])
        for i, arm in enumerate(arms):
            r = A[b][arm]["assa_mean"]
            ax.errorbar(i, r["mean"], yerr=[[r["mean"] - r["boot95"][0]], [r["boot95"][1] - r["mean"]]],
                        fmt="o", color="#3b6ea5", capsize=4)
        ax.axhline(0, color="#888", lw=0.8)
        if b == "batch_v8":
            ax.axhline(0.02, color="#c44", lw=0.8, ls="--", label="H24 bar +0.02")
            ax.legend(fontsize=7, frameon=False)
        ax.set_xticks(range(len(arms)), arms, rotation=20, fontsize=8)
        ax.set_title(b, fontsize=9)
        ax.set_ylabel("ΔAssA vs ByteTrack (TrackEval, α-mean)", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = ["| set | unit | arm | HOTA | DetA | AssA(α-mean) | IDF1 | IDSW |", "|---|---|---|---|---|---|---|---|"]
    for ds, block in res["scores"].items():
        for arm in (a["name"] for a in cfg["arms"]):
            v = [block[u][arm]["COMBINED"] for u in sorted(block)]
            mean = {k: float(np.mean([x[k] for x in v])) for k in KEYS}
            L.append(f"| {ds} | mean of {len(v)} | {arm} | {mean['hota']:.4f} | {mean['deta_mean']:.4f} | "
                     f"{mean['assa_mean']:.4f} | {mean['idf1']:.4f} | {mean['id_switches']:.1f} |")
    L += ["", "| set | arm − control | ΔAssA [95 %] | ΔHOTA [95 %] | ΔIDF1 | ΔIDSW [95 %] | seqs |",
          "|---|---|---|---|---|---|---|"]
    fmt = lambda r: f"{r['mean']:+.4f} [{r['boot95'][0]:+.4f}, {r['boot95'][1]:+.4f}]"
    for ds, arms in res["analysis"].items():
        if ds == "decision":
            continue
        for arm, r in arms.items():
            L.append(f"| {ds} | {arm} | {fmt(r['assa_mean'])} | {fmt(r['hota'])} | {fmt(r['idf1'])} | "
                     f"{fmt(r['id_switches'])} | {len(r['sequences'])} |")
            if "assa_mean_dense" in r:
                L.append(f"| {ds} street_crowd_day only | {arm} | {fmt(r['assa_mean_dense'])} | | | | "
                         f"{r['assa_mean_dense']['n_seq']} |")
    L += ["", "decision: " + ", ".join(f"{k}: {v}" for k, v in res["analysis"]["decision"].items())]
    return "\n".join(L) + "\n"
