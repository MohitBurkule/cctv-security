"""H4: how much identity and clothing-palette signal a generic ImageNet OSNet
recovers from batch_v6 GT crops, per protocol, next to a colour-histogram
baseline and the MOT20 subset numbers from docs/13."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import batch_cameras, rpath, write_json


def collect(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    batch = rpath(cfg["batch_dir"])
    items = []
    seen: set = set()
    for run, world in cfg["runs"].items():
        rd = batch / run
        tid = json.loads((rd / "meta" / "track_ids.json").read_text())
        uid_of = {v: k for k, v in tid.items()}
        app = json.loads((rd / "render_appearance.json").read_text())
        cond = "night" if run.endswith("night") else "day"
        for cam, c in batch_cameras(batch, run, "raw").items():
            # A camera *view* is identified by its GT: street_crowd and street_crowd_far
            # share cam_01 exactly, and must not be scored as two cameras.
            import hashlib
            view = hashlib.md5((rd / "gt" / f"mot_{cam}.txt").read_bytes()).hexdigest()[:8]
            by_id: dict[int, list] = {}
            for f, rows in c["gt"].items():
                if f < 1 or f not in c["frames"]:
                    continue
                for r in rows:
                    if r["bbox"][3] >= cfg["min_h"] and r["vis"] >= cfg["min_vis"]:
                        by_id.setdefault(r["id"], []).append((f, r["bbox"]))
            for pid, rows in by_id.items():
                rows.sort()
                k = min(cfg["per_id_per_cam"], len(rows))
                for i in np.linspace(0, len(rows) - 1, k).round().astype(int):
                    f, bb = rows[i]
                    uid = uid_of.get(pid, str(pid))
                    dkey = (world, uid, view, cond, f)
                    if dkey in seen:
                        continue
                    seen.add(dkey)
                    o = app.get(uid, {}).get("outfit", {})
                    items.append({"identity": f"{world}:{uid}", "camera": f"{world}/{cam}@{view}",
                                  "condition": cond, "frame": f, "png": str(c["frames"][f]),
                                  "bbox": bb, "fps": cfg["fps"],
                                  "top": o.get("top"), "bottom": o.get("bottom"),
                                  "outfit": f"{o.get('top')}|{o.get('bottom')}"})
    return items


def crops(items) -> list[np.ndarray]:
    import cv2
    cache: dict[str, np.ndarray] = {}
    out = []
    for it in items:
        img = cache.get(it["png"])
        if img is None:
            img = cv2.imread(it["png"])
            cache = {it["png"]: img}
        H, W = img.shape[:2]
        x, y, w, h = it["bbox"]
        x0, y0, x1, y1 = max(int(x), 0), max(int(y), 0), min(int(x + w), W), min(int(y + h), H)
        out.append(img[y0:max(y1, y0 + 2), x0:max(x1, x0 + 2)].copy())   # BGR
    return out


def hsv_hist(bgr_crops) -> np.ndarray:
    """Colour baseline: HSV histograms (8x4x4) of the upper and lower body halves."""
    import cv2
    feats = []
    for c in bgr_crops:
        hsv = cv2.cvtColor(cv2.resize(c, (64, 128)), cv2.COLOR_BGR2HSV)
        f = []
        for part in (hsv[16:64], hsv[64:120]):
            h = cv2.calcHist([part], [0, 1, 2], None, [8, 4, 4], [0, 180, 0, 256, 0, 256]).ravel()
            f.append(np.sqrt(h / max(h.sum(), 1)))
        feats.append(np.concatenate(f))
    return np.array(feats, np.float32)


def protocols(items) -> dict[str, np.ndarray]:
    """name -> exclusion mask (True = not in the gallery for that query)."""
    cam = np.array([i["camera"] for i in items])
    cond = np.array([i["condition"] for i in items])
    fr = np.array([i["frame"] for i in items])
    fps = items[0]["fps"]
    same_cam = cam[:, None] == cam[None, :]
    same_cond = cond[:, None] == cond[None, :]
    eye = np.eye(len(items), dtype=bool)
    near = np.abs(fr[:, None] - fr[None, :]) < 5 * fps
    return {
        "cross_camera (same lighting)": same_cam | ~same_cond | eye,
        "cross_time (same camera, >=5 s)": ~same_cam | ~same_cond | near | eye,
        # Day and night renders of one world share every pose and position frame for
        # frame, so a same-frame day/night pair is a near-duplicate; require >= 5 s.
        "cross_lighting (same camera, day<->night, >=5 s)": ~same_cam | same_cond | near | eye,
        # Reported only to show how much the near-duplicate pairs inflate the number.
        "LEAKY cross_lighting incl. same-frame pairs": ~same_cam | same_cond | eye,
    }


def kmeans(X: np.ndarray, k: int, seed: int, iters: int = 100, restarts: int = 10) -> np.ndarray:
    rng = np.random.default_rng(seed)
    best, best_inertia = None, np.inf
    for _ in range(restarts):
        c = [X[rng.integers(len(X))]]
        for _ in range(k - 1):   # k-means++
            d = np.min(((X[:, None] - np.array(c)[None]) ** 2).sum(-1), axis=1)
            c.append(X[rng.choice(len(X), p=d / d.sum())])
        C = np.array(c)
        for _ in range(iters):
            lab = np.argmin(((X[:, None] - C[None]) ** 2).sum(-1), axis=1)
            newC = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
            if np.allclose(newC, C):
                break
            C = newC
        inertia = ((X - C[lab]) ** 2).sum()
        if inertia < best_inertia:
            best, best_inertia = lab, inertia
    return best


def purity(clusters, labels) -> float:
    labels = np.asarray(labels)
    tot = 0
    for c in set(clusters):
        _, n = np.unique(labels[clusters == c], return_counts=True)
        tot += n.max()
    return tot / len(labels)


def nmi(a, b) -> float:
    a, b = np.unique(a, return_inverse=True)[1], np.unique(b, return_inverse=True)[1]
    n = len(a)
    M = np.zeros((a.max() + 1, b.max() + 1))
    np.add.at(M, (a, b), 1)
    P = M / n
    pa, pb = P.sum(1), P.sum(0)
    nz = P > 0
    mi = (P[nz] * np.log(P[nz] / (pa[:, None] * pb[None])[nz])).sum()
    ha, hb = -(pa[pa > 0] * np.log(pa[pa > 0])).sum(), -(pb[pb > 0] * np.log(pb[pb > 0])).sum()
    return float(2 * mi / max(ha + hb, 1e-12))


def palette_analysis(F: np.ndarray, items, seed: int, n_perm: int = 50) -> dict[str, Any]:
    """Is clothing palette recoverable from the embedding, beyond identity?"""
    rng = np.random.default_rng(seed)
    ids = np.array([i["identity"] for i in items])
    res: dict[str, Any] = {}
    for key in ("outfit", "top", "bottom"):
        lab = np.array([i[key] for i in items])
        k = len(set(lab))
        cl = kmeans(F, k, seed)
        perm = [purity(cl, rng.permutation(lab)) for _ in range(n_perm)]
        # nearest neighbour among *other identities* shares the palette label?
        S = F @ F.T
        S[ids[:, None] == ids[None, :]] = -np.inf
        nn = np.argmax(S, axis=1)
        agree = float((lab[nn] == lab).mean())
        other = ids[:, None] != ids[None, :]
        chance = float(np.mean(((lab[:, None] == lab[None, :]) & other).sum(1) / np.maximum(other.sum(1), 1)))
        res[key] = {"n_labels": k, "kmeans_purity": round(purity(cl, lab), 4),
                    "purity_permuted_mean": round(float(np.mean(perm)), 4),
                    "nmi": round(nmi(cl, lab), 4),
                    "nn_other_identity_same_label": round(agree, 4),
                    "nn_chance": round(chance, 4)}
    return res


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from ..baselines.run import _embedder
    from ..eval.tracking import evaluate_reid
    from .common import gpu_meter

    items = collect(cfg)
    bgr = crops(items)
    res: dict[str, Any] = {"n_crops": len(items), "n_identities": len({i["identity"] for i in items}),
                           "n_outfits": len({i["outfit"] for i in items}),
                           "n_cameras": len({i["camera"] for i in items}), "models": {}}
    name, embed = _embedder()
    cost: dict[str, Any] = {}
    with gpu_meter(cost, "embed"):
        F = np.concatenate([embed([c[:, :, ::-1].copy() for c in bgr[i:i + 64]])
                            for i in range(0, len(bgr), 64)]) if name.startswith("osnet") else \
            np.concatenate([embed(bgr[i:i + 64]) for i in range(0, len(bgr), 64)])
    feats = {name: F, "hsv_histogram (colour baseline)": hsv_hist(bgr)}
    ids = np.array([i["identity"] for i in items])
    for mname, X in feats.items():
        X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
        r: dict[str, Any] = {"protocols": {}}
        for pname, excl in protocols(items).items():
            v = evaluate_reid(ids, ids, X @ X.T, exclude=excl, scope=pname).as_dict()
            r["protocols"][pname] = {k: (round(x, 4) if isinstance(x, float) else x) for k, x in v.items()}
        r["palette"] = palette_analysis(X, items, cfg["seed"])
        res["models"][mname] = r
    res["embed_cost"] = cost["embed"]
    ref = rpath(cfg["mot20_reference"])
    if ref.is_file():
        m = json.loads(ref.read_text())["reid"]
        res["mot20_reference"] = {k: m[k] for k in ("model", "scope", "n_identities", "rank1", "rank5", "mAP")}
    write_json(out / "items.json", items)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    lines = [(f"{res['n_crops']} crops, {res['n_identities']} identities, {res['n_outfits']} outfits, "
             f"{res['n_cameras']} camera views"), "",
             "| embedding | protocol | queries | rank-1 | rank-5 | mAP |", "|---|---|---|---|---|---|"]
    for m, r in res["models"].items():
        for p, v in r["protocols"].items():
            lines.append(f"| {m} | {p} | {v.get('n_queries', v.get('queries', '-'))} | {v['rank1']:.3f} | "
                         f"{v['rank5']:.3f} | {v['mAP']:.3f} |")
    if "mot20_reference" in res:
        v = res["mot20_reference"]
        lines.append(f"| {v['model']} (MOT20 subset, docs/13) | {v['scope']} | {v['n_identities']} ids | "
                     f"{v['rank1']:.3f} | {v['rank5']:.3f} | {v['mAP']:.3f} |")
    lines += ["", ("| embedding | label | #labels | k-means purity | permuted purity | NMI | "
              "NN(other id) same label | chance |"), "|---|---|---|---|---|---|---|---|"]
    for m, r in res["models"].items():
        for k, v in r["palette"].items():
            lines.append(f"| {m} | {k} | {v['n_labels']} | {v['kmeans_purity']:.3f} | "
                         f"{v['purity_permuted_mean']:.3f} | {v['nmi']:.3f} | "
                         f"{v['nn_other_identity_same_label']:.3f} | {v['nn_chance']:.3f} |")
    return "\n".join(lines) + "\n"
