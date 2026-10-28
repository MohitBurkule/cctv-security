"""H20: can synthetic crops train a ReID embedding?

Fine-tunes torchreid OSNet x1.0 (ImageNet init) on batch_v8 GT crops with
identity labels (softmax-CE + batch-hard triplet, PK batches), holding out
scenes, then scores it against OSNet-ImageNet and an HSV histogram on
(a) held-out synthetic scenes (cross-camera, cross-time) and (b) the real
MOT20 subset with the docs/13 cross-time protocol. CIs are bootstrapped over
query identities, never over crops."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, wait_for_gpu, write_json
from .reid import collect, crops, hsv_hist
from .reid_epochs import ranks

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


# ------------------------------------------------------------------ data

def synth_items(cfg: dict[str, Any], runs: dict[str, str], per: int, epoch_ids: bool) -> list[dict[str, Any]]:
    """GT crops per run; identity = world:uid (+ :e<epoch> when epoch_ids)."""
    import pandas as pd
    batch = rpath(cfg["batch_dir"])
    out = []
    for run, world in runs.items():
        its = collect({**cfg, "runs": {run: world}, "per_id_per_cam": per})
        ep = {}
        if epoch_ids:
            w = pd.read_parquet(batch / run / "gt" / "world.parquet", columns=["frame", "uid", "appearance_epoch"])
            ep = {(int(f), u): int(e) for f, u, e in w.itertuples(index=False)}
        for it in its:
            uid = it["identity"].split(":", 1)[1]
            it["run"] = run
            it["epoch"] = ep.get((it["frame"], uid), 0)
            if epoch_ids:
                it["identity"] = f"{it['identity']}:e{it['epoch']}"
            it["camera"] = f"{run}/{it['camera']}"   # a view is per run: day/night = other lighting
            out.append(it)
    return out


def mot20_items(cfg: dict[str, Any]) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, str]:
    """Real crops (BGR) + ids + exclusion mask, exactly as docs/13's eval_reid samples them."""
    import cv2

    from ..baselines.run import reid_protocol, sample_crops
    from survsim.datasets.build import load_manifest
    m = load_manifest(rpath(cfg["mot20_subset"]))
    items = sample_crops(m)
    out, cache = [], {}
    for _pid, _cam, _f, path, (x, y, w, h), _ in items:
        img = cache.get(path)
        if img is None:
            img = cv2.imread(path)
            cache = {path: img}
        H, W = img.shape[:2]
        x0, y0, x1, y1 = max(int(x), 0), max(int(y), 0), min(int(x + w), W), min(int(y + h), H)
        out.append(img[y0:max(y1, y0 + 2), x0:max(x1, x0 + 2)].copy())
    pids, excl, mode = reid_protocol(items)
    return out, pids, excl | np.eye(len(items), dtype=bool), mode


def synth_protocols(items) -> dict[str, np.ndarray]:
    cam = np.array([i["camera"].split("@")[-1] + "|" + i["condition"] for i in items])
    view = np.array([i["camera"].split("@")[-1] for i in items])
    cond = np.array([i["condition"] for i in items])
    fr = np.array([i["frame"] for i in items])
    eye = np.eye(len(items), dtype=bool)
    near = np.abs(fr[:, None] - fr[None]) < 5 * items[0]["fps"]
    same_view, same_cond = view[:, None] == view[None], cond[:, None] == cond[None]
    del cam
    return {"cross_camera": eye | ~same_cond | same_view,
            "cross_time (same camera, >=5 s)": eye | ~same_cond | ~same_view | near}


def _prep(bgr: np.ndarray, size=(128, 256)) -> np.ndarray:
    import cv2
    x = cv2.resize(bgr, size)[:, :, ::-1].astype(np.float32) / 255
    return ((x - MEAN) / STD).transpose(2, 0, 1)


# ------------------------------------------------------------------ model

def build(num_classes: int):
    import torchreid
    return torchreid.models.build_model("osnet_x1_0", num_classes=num_classes, loss="triplet", pretrained=True)


def embed(model, bgr_crops, dev, bs: int = 64) -> np.ndarray:
    import torch
    model.eval()
    F = []
    with torch.no_grad(), torch.autocast("cuda", enabled=dev == "cuda"):
        for i in range(0, len(bgr_crops), bs):
            x = torch.from_numpy(np.stack([_prep(c) for c in bgr_crops[i:i + bs]])).to(dev)
            F.append(model(x).float().cpu().numpy())
    F = np.concatenate(F)
    return F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)


def batch_hard_triplet(f, y, margin: float):
    import torch
    d = torch.cdist(f, f)
    pos = y[:, None] == y[None]
    hp = (d * pos).max(1).values
    hn = (d + 1e5 * pos).min(1).values
    return torch.relu(hp - hn + margin).mean()


def pk_batches(labels: np.ndarray, P: int, K: int, rng) -> list[np.ndarray]:
    """One pass: shuffled identities in groups of P, K samples each (with replacement if short)."""
    by = {c: np.where(labels == c)[0] for c in np.unique(labels)}
    ids = rng.permutation(list(by))
    n_rounds = max(1, int(np.ceil(len(labels) / (P * K))))
    out = []
    for r in range(n_rounds):
        chosen = [ids[(r * P + j) % len(ids)] for j in range(P)]
        idx = [rng.choice(by[c], K, replace=len(by[c]) < K) for c in chosen]
        out.append(np.concatenate(idx))
    return out


def _augment(x: np.ndarray, rng) -> np.ndarray:
    """flip, pad-10 random crop, random erasing; x is CHW normalised."""
    if rng.random() < 0.5:
        x = x[:, :, ::-1]
    C, H, W = x.shape
    p = np.pad(x, ((0, 0), (10, 10), (10, 10)))
    i, j = rng.integers(0, 21, 2)
    x = p[:, i:i + H, j:j + W].copy()
    if rng.random() < 0.5:
        a = rng.uniform(0.02, 0.2) * H * W
        r = rng.uniform(0.3, 3.3)
        h, w = int(min(H, np.sqrt(a * r))), int(min(W, np.sqrt(a / r)))
        y0, x0 = rng.integers(0, H - h + 1), rng.integers(0, W - w + 1)
        x[:, y0:y0 + h, x0:x0 + w] = rng.normal(size=(C, h, w))
    return x


def train(bgr, labels, cfg: dict[str, Any], seed: int, dev: str) -> tuple[Any, dict[str, Any]]:
    import torch
    t = cfg["train"]
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    classes = sorted(set(labels))
    y = np.array([classes.index(v) for v in labels])
    X = np.stack([_prep(c) for c in bgr])
    model = build(len(classes)).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=t["lr"], weight_decay=5e-4)
    scaler = torch.amp.GradScaler(enabled=dev == "cuda")
    ce = torch.nn.CrossEntropyLoss(label_smoothing=0.1)
    t0, log, step = time.time(), [], 0
    for ep in range(t["epochs"]):
        model.train()
        tot = []
        for b in pk_batches(y, t["P"], t["K"], rng):
            xb = torch.from_numpy(np.stack([_augment(X[i], rng) for i in b])).to(dev)
            yb = torch.from_numpy(y[b]).to(dev)
            with torch.autocast("cuda", enabled=dev == "cuda"):
                logits, feat = model(xb)
                loss = ce(logits.float(), yb) + batch_hard_triplet(feat.float(), yb, t["margin"])
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            tot.append(float(loss))
            step += 1
        log.append({"epoch": ep, "loss": round(float(np.mean(tot)), 4), "t": round(time.time() - t0, 1)})
        if time.time() - t0 > t["max_seconds"]:
            break
    peak = torch.cuda.max_memory_allocated() // 2**20 if dev == "cuda" else 0
    return model, {"epochs_run": len(log), "steps": step, "seconds": round(time.time() - t0, 1),
                   "peak_vram_mib": int(peak), "n_classes": len(classes), "log": log}


# ------------------------------------------------------------------ scoring

def per_id_scores(ids, S, excl) -> dict[str, dict[str, float]]:
    """identity -> mean rank-1 and mean AP over its valid queries."""
    h, a, qi = ranks(np.asarray(ids), S, excl)
    out: dict[str, list] = {}
    for hit, ap, q in zip(h, a, qi):
        out.setdefault(str(ids[q]), []).append((hit, ap))
    return {k: {"r1": float(np.mean([v[0] for v in L])), "ap": float(np.mean([v[1] for v in L])), "n": len(L)}
            for k, L in out.items()}


def summarise(pid: dict[str, dict[str, float]], n_boot: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Query-weighted rank-1/mAP (the usual numbers) + bootstrap CI over identities (id-weighted)."""
    if not pid:
        return {"n_ids": 0}
    rng = np.random.default_rng(seed)
    keys = sorted(pid)
    r1 = np.array([pid[k]["r1"] for k in keys])
    ap = np.array([pid[k]["ap"] for k in keys])
    n = np.array([pid[k]["n"] for k in keys])
    B = rng.integers(0, len(keys), (n_boot, len(keys)))
    q = lambda v: [round(float(np.quantile(v, .025)), 4), round(float(np.quantile(v, .975)), 4)]
    return {"n_ids": len(keys), "n_queries": int(n.sum()),
            "rank1": round(float((r1 * n).sum() / n.sum()), 4), "mAP": round(float((ap * n).sum() / n.sum()), 4),
            "rank1_id_mean": round(float(r1.mean()), 4), "rank1_boot95": q(r1[B].mean(1)),
            "mAP_id_mean": round(float(ap.mean()), 4), "mAP_boot95": q(ap[B].mean(1))}


def paired_diff(a: dict, b: dict, key: str = "ap", n_boot: int = 10000, seed: int = 0) -> dict[str, Any]:
    """b - a over identities present in both, bootstrap over identities."""
    ks = sorted(set(a) & set(b))
    d = np.array([b[k][key] - a[k][key] for k in ks])
    if len(d) == 0:
        return {"n_ids": 0}
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (n_boot, len(d)))].mean(1)
    return {"n_ids": len(ks), "mean": round(float(d.mean()), 4),
            "boot95": [round(float(np.quantile(m, .025)), 4), round(float(np.quantile(m, .975)), 4)]}


def _cos(F):
    F = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    return F @ F.T


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tr_items = synth_items(cfg, cfg["train_runs"], cfg["train_per_id_per_cam"], epoch_ids=False)
    te_items = synth_items(cfg, cfg["test_runs"], cfg["test_per_id_per_cam"], epoch_ids=True)
    tr_bgr, te_bgr = crops(tr_items), crops(te_items)
    mot_bgr, mot_ids, mot_excl, mot_mode = mot20_items(cfg)
    te_ids = np.array([i["identity"] for i in te_items])
    te_prot = synth_protocols(te_items)
    res: dict[str, Any] = {
        "train": {"n_crops": len(tr_items), "n_ids": len({i["identity"] for i in tr_items}),
                  "ids": sorted({i["identity"] for i in tr_items})},
        "test_synth": {"n_crops": len(te_items), "n_ids": len(set(te_ids)), "ids": sorted(set(te_ids))},
        "mot20": {"n_crops": len(mot_bgr), "n_ids": len(set(mot_ids)), "protocol": mot_mode},
        "gpu_wait": wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=1800)}

    def score(S_te, S_mot):
        per = {p: per_id_scores(te_ids, S_te, ex) for p, ex in te_prot.items()}
        per["mot20_cross_time"] = per_id_scores(mot_ids, S_mot, mot_excl)
        return per

    per: dict[str, dict] = {}
    per["hsv_histogram"] = score(_cos(hsv_hist(te_bgr)), _cos(hsv_hist(mot_bgr)))
    base = build(10).to(dev)
    per["osnet_imagenet"] = score(_cos(embed(base, te_bgr, dev)), _cos(embed(base, mot_bgr, dev)))
    del base
    res["training"] = {}
    tr_labels = [i["identity"] for i in tr_items]
    for s in cfg["seeds"]:
        torch.cuda.reset_peak_memory_stats() if dev == "cuda" else None
        model, info = train(tr_bgr, tr_labels, cfg, s, dev)
        res["training"][f"s{s}"] = info
        per[f"osnet_synth_ft_s{s}"] = score(_cos(embed(model, te_bgr, dev)), _cos(embed(model, mot_bgr, dev)))
        del model
        torch.cuda.empty_cache() if dev == "cuda" else None
    res["scores"] = {m: {p: summarise(v) for p, v in d.items()} for m, d in per.items()}
    # fine-tuned - ImageNet, paired over identities: per seed and seed-mean
    seeds = [f"osnet_synth_ft_s{s}" for s in cfg["seeds"]]
    res["contrasts"] = {}
    for p in per["osnet_imagenet"]:
        mean_ft = {k: {m: float(np.mean([per[s][p][k][m] for s in seeds])) for m in ("ap", "r1")}
                   for k in per[seeds[0]][p] if all(k in per[s][p] for s in seeds)}
        res["contrasts"][p] = {
            "ft_mean - imagenet (mAP)": paired_diff(per["osnet_imagenet"][p], mean_ft, "ap"),
            "ft_mean - imagenet (rank-1)": paired_diff(per["osnet_imagenet"][p], mean_ft, "r1"),
            "per_seed_mAP": {s: paired_diff(per["osnet_imagenet"][p], per[s][p], "ap") for s in seeds},
            "imagenet - hsv (mAP)": paired_diff(per["hsv_histogram"][p], per["osnet_imagenet"][p], "ap")}
    write_json(out / "per_identity.json", per)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [(f"train {res['train']['n_crops']} crops / {res['train']['n_ids']} ids; held-out synthetic "
         f"{res['test_synth']['n_crops']} crops / {res['test_synth']['n_ids']} ids; MOT20 {res['mot20']['n_crops']} "
         f"crops / {res['mot20']['n_ids']} ids ({res['mot20']['protocol']})"), "",
         "| embedding | protocol | ids | queries | rank-1 | mAP | mAP id-mean [95% boot over ids] |",
         "|---|---|---|---|---|---|---|"]
    for m, d in res["scores"].items():
        for p, v in d.items():
            if not v.get("n_ids"):
                continue
            L.append(f"| {m} | {p} | {v['n_ids']} | {v['n_queries']} | {v['rank1']:.3f} | {v['mAP']:.3f} | "
                     f"{v['mAP_id_mean']:.3f} [{v['mAP_boot95'][0]:.3f}, {v['mAP_boot95'][1]:.3f}] |")
    L += ["", "| protocol | contrast | Δ | 95% boot over ids | per seed |", "|---|---|---|---|---|"]
    for p, c in res["contrasts"].items():
        for k in ("ft_mean - imagenet (mAP)", "ft_mean - imagenet (rank-1)", "imagenet - hsv (mAP)"):
            v = c[k]
            if v.get("n_ids"):
                ps = ", ".join(f"{x['mean']:+.3f}" for x in c["per_seed_mAP"].values()) if "ft" in k and "mAP" in k else ""
                L.append(f"| {p} | {k} | {v['mean']:+.4f} | [{v['boot95'][0]:+.4f}, {v['boot95'][1]:+.4f}] | {ps} |")
    return "\n".join(L) + "\n"
