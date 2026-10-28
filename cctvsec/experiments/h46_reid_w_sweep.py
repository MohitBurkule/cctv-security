"""H46: appearance-weight sweep + night arm for ByteTrack + OSNet-ImageNet.

Reuses H24's cached detections/embeddings for day + MOT20-02 (no re-detection,
no re-embedding). Night sequences (disguise_and_tamper_night, smoke_mock_night)
get fresh detections/embeddings at the single best w from the day/MOT20 sweep.
Pre-registered in docs/research/32 §H46 / 66 §H46.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, wait_for_gpu, write_json
from .reid_assoc import gt_dets, track, trackeval_score, two_way_boot, unit_boot  # noqa: F401
from .tracking import detect_paths, mot20_sequences, v7_sequences

H24_OUT = Path("out/experiments/h24_reid_assoc")
KEYS = ("hota", "deta", "assa", "assa_mean", "deta_mean", "idf1", "id_switches", "mota")


def _load_cached(ds: str, ckpt: str, seq_key: str) -> tuple[dict[int, list[dict]], list[tuple[int, int]], np.ndarray]:
    sk = seq_key.replace("/", "__")
    det_cache = (H24_OUT / "dets" / ckpt / f"{sk}.json") if ds == "batch_v8" else \
        rpath(f"out/experiments/h17_tracking_transfer/dets/{ckpt}") / f"{sk}.json"
    import json
    dets = {int(k): v for k, v in json.loads(det_cache.read_text()).items()}
    emb_cache = H24_OUT / "emb" / ds / ckpt / f"{sk}.npz"
    z = np.load(emb_cache, allow_pickle=False)
    keys = [tuple(int(x) for x in k) for k in z["keys"].tolist()]
    feats = z["osnet_imagenet"]
    return dets, keys, feats


def _attach(dets, keys, feats) -> dict[int, list[dict]]:
    out = {f: [dict(d) for d in v] for f, v in dets.items()}
    for (f, i), e in zip(keys, feats):
        out[f][i]["emb"] = e
    return out


def _score_ds(seqs, checkpoints: list[str], ds: str, weights: list[float], ema: float,
             fresh: dict[str, dict] | None = None) -> dict[str, Any]:
    """scores[ckpt][w] = {seq_key: metrics}; fresh overrides dets/keys/feats per (ckpt, seq_key)."""
    scores: dict[str, dict] = {}
    for ck in checkpoints:
        scores[ck] = {}
        tracks_by_w: dict[float, dict[str, list]] = {w: {} for w in weights}
        for s in seqs:
            if fresh is not None:
                dets, keys, feats = fresh[(ck, s["key"])]
            else:
                dets, keys, feats = _load_cached(ds, ck, s["key"])
            d = _attach(dets, keys, feats)
            for w in weights:
                tracks_by_w[w][s["key"]] = track(s, d if w > 0 else dets, w, ema)
        for w in weights:
            sc = trackeval_score(seqs, tracks_by_w[w])
            scores[ck][w] = {k.replace("__", "/"): {m: v[m] for m in KEYS} for k, v in sc.items()}
    return scores


def _delta_analysis(scores: dict[str, dict], weights: list[float]) -> dict[str, Any]:
    ckpts = sorted(scores)
    seqs = sorted(k for k in scores[ckpts[0]][weights[0]] if k != "COMBINED")
    out: dict[str, Any] = {}
    for w in weights:
        D = np.array([[scores[c][w][s]["assa_mean"] - scores[c][0.0][s]["assa_mean"] for c in ckpts] for s in seqs])
        Di = np.array([[scores[c][w][s]["id_switches"] - scores[c][0.0][s]["id_switches"] for c in ckpts] for s in seqs])
        out[str(w)] = {
            "assa_mean_delta": two_way_boot(D) if len(seqs) > 1 else unit_boot(D[0]),
            "idsw_delta": two_way_boot(Di) if len(seqs) > 1 else unit_boot(Di[0]),
            "n_seq": len(seqs), "n_ckpt": len(ckpts),
        }
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import torch
    ckpts = cfg["checkpoints"]
    weights = cfg["weights"]
    res: dict[str, Any] = {"weights": weights}

    # (a) day + MOT20-02 sweep, fully cached
    batch_seqs = v7_sequences({"batch_dir": cfg["batch_dir"], "runs": cfg["day_runs"],
                               "max_frame": cfg["max_frame"], "fps": cfg["batch_fps"]})
    mot_cfg = {"mot20_subset": cfg["mot20_subset"]}
    mot_seqs = [s for s in mot20_sequences(mot_cfg) if s["run"] in cfg["mot20_sequences"]]

    # control is w=0.0 read from cache too (app_weight 0 == IoU-only; cheap to include in sweep for consistency)
    sweep_w = [0.0] + list(weights)
    day_scores = _score_ds(batch_seqs, ckpts, "batch_v8", sweep_w, cfg.get("ema", 0.9))
    mot_scores = _score_ds(mot_seqs, ckpts, "mot20", sweep_w, cfg.get("ema", 0.9))
    res["day"] = {"scores": day_scores, "analysis": _delta_analysis(day_scores, weights)}
    res["mot20"] = {"scores": mot_scores, "analysis": _delta_analysis(mot_scores, weights)}
    write_json(out / "partial.json", res)

    best_w = None
    day_gains = {w: res["day"]["analysis"][str(w)]["assa_mean_delta"]["mean"] for w in weights}
    best_w = max(day_gains, key=day_gains.get)
    res["best_w_day"] = best_w
    mot_gains = {w: res["mot20"]["analysis"][str(w)]["assa_mean_delta"]["mean"] for w in weights}
    res["best_w_mot20"] = max(mot_gains, key=mot_gains.get)

    # (b) night arm at best_w, fresh detections + embeddings, bounded (1 checkpoint to fit budget)
    night_ckpts = cfg.get("night_checkpoints", ckpts[:1])
    gpu = wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=300)
    dev = "cuda" if torch.cuda.is_available() and gpu.get("free_mib", 0) >= cfg.get("min_free_mib", 2048) else "cpu"
    res["night_gpu"] = gpu
    night_seqs = v7_sequences({"batch_dir": cfg["batch_dir"], "runs": cfg["night_runs"],
                               "max_frame": cfg["max_frame"], "fps": cfg["batch_fps"]})
    from .reid_train import build, embed
    model = build(10).to(dev)
    model.eval()

    def embedder(crops):
        return embed(model, crops, dev, bs=cfg.get("embed_batch", 32))

    from .reid_assoc import _crops
    ck_weights = {c["name"]: c["weights"] for c in cfg["checkpoint_specs"]}
    fresh: dict[tuple[str, str], tuple] = {}
    for ck in night_ckpts:
        for s in night_seqs:
            sk = s["key"].replace("/", "__")
            dcache = out / "dets" / ck / f"{sk}.json"
            dets = detect_paths(ck_weights[ck], s["paths"], dcache, cfg["imgsz"], cfg["det_conf"],
                                batch=cfg.get("det_batch", 4))
            ecache = out / "emb" / "night" / ck / f"{sk}.npz"
            if ecache.is_file():
                z = np.load(ecache, allow_pickle=False)
                keys = [tuple(int(x) for x in k) for k in z["keys"].tolist()]
                feats = z["osnet_imagenet"]
            else:
                keys, crops = _crops(s, dets, cfg["emb_min_score"])
                feats = embedder(crops) if crops else np.zeros((0, 512), np.float32)
                ecache.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(ecache, keys=np.array(keys, int).reshape(-1, 2), osnet_imagenet=feats)
            fresh[(ck, s["key"])] = (dets, keys, feats)
    night_w = [0.0, float(best_w)]
    night_scores = _score_ds(night_seqs, night_ckpts, "batch_v8", night_w, cfg.get("ema", 0.9), fresh=fresh)
    res["night"] = {"scores": night_scores, "analysis": _delta_analysis(night_scores, [float(best_w)]),
                    "checkpoints_used": night_ckpts, "w": best_w}
    write_json(out / "results.json", res)
    try:
        figure(res, weights, out / "fig_h46.png")
    except Exception as e:  # noqa: BLE001 - figure is cosmetic
        res["figure_error"] = repr(e)
    return res


def figure(res: dict[str, Any], weights: list[float], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, ds in zip(axes, ("day", "mot20")):
        A = res[ds]["analysis"]
        means = [A[str(w)]["assa_mean_delta"]["mean"] for w in weights]
        los = [A[str(w)]["assa_mean_delta"]["boot95"][0] for w in weights]
        his = [A[str(w)]["assa_mean_delta"]["boot95"][1] for w in weights]
        ax.errorbar(range(len(weights)), means, yerr=[np.array(means) - np.array(los), np.array(his) - np.array(means)],
                    fmt="o-", color="#3b6ea5", capsize=4)
        ax.axhline(0, color="#888", lw=0.8)
        ax.axhline(0.02, color="#c44", lw=0.8, ls="--")
        ax.set_xticks(range(len(weights)), [str(w) for w in weights])
        ax.set_title(ds)
        ax.set_xlabel("appearance weight w")
        ax.set_ylabel("ΔAssA vs w=0")
    ax = axes[2]
    A = res["night"]["analysis"]
    w = res["night"]["w"]
    r = A[str(float(w))]["assa_mean_delta"]
    ax.errorbar(0, r["mean"], yerr=[[r["mean"] - r["boot95"][0]], [r["boot95"][1] - r["mean"]]],
                fmt="o", color="#c44", capsize=4)
    ax.axhline(0, color="#888", lw=0.8)
    ax.set_xticks([0], [f"night w={w}"])
    ax.set_title("night arm")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    weights = res["weights"]
    L = ["| set | w | dAssA [95%] | dIDSW [95%] | n_seq | n_ckpt |", "|---|---|---|---|---|---|"]
    for ds in ("day", "mot20"):
        A = res[ds]["analysis"]
        for w in weights:
            a = A[str(w)]
            r = a["assa_mean_delta"]
            ri = a["idsw_delta"]
            L.append(f"| {ds} | {w} | {r['mean']:+.4f} [{r['boot95'][0]:+.4f}, {r['boot95'][1]:+.4f}] | "
                     f"{ri['mean']:+.2f} [{ri['boot95'][0]:+.2f}, {ri['boot95'][1]:+.2f}] | "
                     f"{a['n_seq']} | {a['n_ckpt']} |")
    L.append(f"\nbest w (day argmax dAssA): {res['best_w_day']}; best w (mot20 argmax dAssA): {res['best_w_mot20']}")
    if "night" in res:
        w = res["night"]["w"]
        r = res["night"]["analysis"][str(float(w))]["assa_mean_delta"]
        L.append(f"\nnight arm at w={w}: dAssA {r['mean']:+.4f} [{r['boot95'][0]:+.4f}, {r['boot95'][1]:+.4f}] "
                 f"(checkpoints: {res['night']['checkpoints_used']})")
    return "\n".join(L) + "\n"
