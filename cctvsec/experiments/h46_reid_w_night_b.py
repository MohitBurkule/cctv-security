"""H46b: extend the appearance-weight sweep, cross-validate w*, full night arm.

Follow-up to H46 (`h46_reid_w_sweep.py`): reuses H24/H46's cached day/MOT20-02
detections and embeddings (no re-detection, no re-embedding for those two
sets). Adds w in {8, 16, 32} and a true appearance-only cost arm
(`app_only=True` in `cctvsec.baselines.bytetrack`, geometry term dropped, the
IoU >= 0.2 gate unchanged), chooses w* by cross-set validation, and runs the
night arm at all 5 h14b checkpoints (H46 used 1). Pre-registered in
docs/research/32 sec H46b / 66 sec H46b.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, wait_for_gpu, write_json
from .h46_reid_w_sweep import _attach, _load_cached
from .reid_assoc import track, trackeval_score, two_way_boot, unit_boot
from .tracking import detect_paths, mot20_sequences, v7_sequences

KEYS = ("hota", "deta", "assa", "assa_mean", "deta_mean", "idf1", "id_switches", "mota")

# arm labels used throughout: numeric weights as their float value, appearance-only as "app_only"


def _arms(cfg: dict[str, Any]) -> list[float | str]:
    arms: list[float | str] = [0.0, *cfg["base_weights"], *cfg["new_weights"]]
    if cfg.get("app_only"):
        arms.append("app_only")
    return arms


def _track_arm(seq, dets, arm: float | str, ema: float) -> list[dict]:
    if arm == "app_only":
        return track(seq, dets, app_weight=1.0, ema=ema, app_only=True)
    return track(seq, dets, app_weight=float(arm), ema=ema)


def _score_ds(seqs, checkpoints: list[str], ds: str, arms: list[float | str], ema: float,
             fresh: dict[str, dict] | None = None) -> dict[str, Any]:
    scores: dict[str, dict] = {}
    for ck in checkpoints:
        scores[ck] = {}
        tracks_by_arm: dict[Any, dict[str, list]] = {a: {} for a in arms}
        for s in seqs:
            if fresh is not None:
                dets, keys, feats = fresh[(ck, s["key"])]
            else:
                dets, keys, feats = _load_cached(ds, ck, s["key"])
            d = _attach(dets, keys, feats)
            for a in arms:
                tracks_by_arm[a][s["key"]] = _track_arm(s, d if a != 0.0 else dets, a, ema)
        for a in arms:
            sc = trackeval_score(seqs, tracks_by_arm[a])
            scores[ck][str(a)] = {k.replace("__", "/"): {m: v[m] for m in KEYS} for k, v in sc.items()}
    return scores


def _delta_analysis(scores: dict[str, dict], arms: list[float | str]) -> dict[str, Any]:
    ckpts = sorted(scores)
    seqs = sorted(k for k in scores[ckpts[0]][str(arms[0])] if k != "COMBINED")
    out: dict[str, Any] = {}
    for a in arms:
        sa, s0 = str(a), str(0.0)
        for m, key in (("assa_mean", "assa_mean_delta"), ("deta_mean", "deta_mean_delta"),
                       ("hota", "hota_delta"), ("id_switches", "idsw_delta")):
            D = np.array([[scores[c][sa][s][m] - scores[c][s0][s][m] for c in ckpts] for s in seqs])
            out.setdefault(sa, {})[key] = two_way_boot(D) if len(seqs) > 1 else unit_boot(D[0])
        out[sa]["n_seq"], out[sa]["n_ckpt"] = len(seqs), len(ckpts)
    return out


def _cross_validate(day_analysis: dict[str, Any], mot_analysis: dict[str, Any],
                    arms: list[float | str]) -> dict[str, Any]:
    """Choose w* on one set (argmax dAssA), report the OTHER set's dAssA at that w*, both ways."""
    def argmax(analysis):
        return max((str(a) for a in arms if str(a) != "0.0"),
                   key=lambda k: analysis[k]["assa_mean_delta"]["mean"])
    w_from_day = argmax(day_analysis)
    w_from_mot = argmax(mot_analysis)
    return {
        "w_star_from_day": w_from_day,
        "day_dAssA_at_w_star_from_day": day_analysis[w_from_day]["assa_mean_delta"],
        "mot20_dAssA_at_w_star_from_day": mot_analysis[w_from_day]["assa_mean_delta"],
        "w_star_from_mot20": w_from_mot,
        "mot20_dAssA_at_w_star_from_mot20": mot_analysis[w_from_mot]["assa_mean_delta"],
        "day_dAssA_at_w_star_from_mot20": day_analysis[w_from_mot]["assa_mean_delta"],
    }


def _ceiling(day_analysis: dict[str, Any], mot_analysis: dict[str, Any],
            weights: list[float]) -> dict[str, Any]:
    """Does dAssA peak at an interior w (not the largest tried)?"""
    def peak(analysis):
        vals = [analysis[str(w)]["assa_mean_delta"]["mean"] for w in weights]
        i = int(np.argmax(vals))
        return {"weights": weights, "means": vals, "argmax_w": weights[i],
                "ceiling_found": i < len(weights) - 1}
    return {"day": peak(day_analysis), "mot20": peak(mot_analysis)}


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    import torch
    ckpts = cfg["checkpoints"]
    arms = _arms(cfg)
    numeric_weights = [0.0, *cfg["base_weights"], *cfg["new_weights"]]
    res: dict[str, Any] = {"arms": [str(a) for a in arms]}

    # (a) extended day + MOT20-02 sweep, fully cached, CPU only
    batch_seqs = v7_sequences({"batch_dir": cfg["batch_dir"], "runs": cfg["day_runs"],
                               "max_frame": cfg["max_frame"], "fps": cfg["batch_fps"]})
    mot_cfg = {"mot20_subset": cfg["mot20_subset"]}
    mot_seqs = [s for s in mot20_sequences(mot_cfg) if s["run"] in cfg["mot20_sequences"]]

    day_scores = _score_ds(batch_seqs, ckpts, "batch_v8", arms, cfg.get("ema", 0.9))
    mot_scores = _score_ds(mot_seqs, ckpts, "mot20", arms, cfg.get("ema", 0.9))
    day_analysis = _delta_analysis(day_scores, arms)
    mot_analysis = _delta_analysis(mot_scores, arms)
    res["day"] = {"scores": day_scores, "analysis": day_analysis}
    res["mot20"] = {"scores": mot_scores, "analysis": mot_analysis}
    res["ceiling"] = _ceiling(day_analysis, mot_analysis, numeric_weights)
    write_json(out / "partial.json", res)

    # (b) cross-set validation
    res["cross_validation"] = _cross_validate(day_analysis, mot_analysis, arms)
    w_star = res["cross_validation"]["w_star_from_day"]
    res["w_star_for_night"] = w_star
    write_json(out / "partial.json", res)

    # (c) full night arm at w_star, all 5 checkpoints (reuse H46's mix_300_s0 cache)
    night_ckpts = cfg.get("night_checkpoints", ckpts)
    h46_cache = rpath(cfg["h46_night_cache"]) if cfg.get("h46_night_cache") else None
    night_seqs = v7_sequences({"batch_dir": cfg["batch_dir"], "runs": cfg["night_runs"],
                               "max_frame": cfg["max_frame"], "fps": cfg["batch_fps"]})

    need_fresh = []
    fresh: dict[tuple[str, str], tuple] = {}
    for ck in night_ckpts:
        for s in night_seqs:
            sk = s["key"].replace("/", "__")
            dcache = out / "dets" / ck / f"{sk}.json"
            ecache = out / "emb" / "night" / ck / f"{sk}.npz"
            if h46_cache is not None and not dcache.is_file():
                src_d = h46_cache / "dets" / ck / f"{sk}.json"
                src_e = h46_cache / "emb" / "night" / ck / f"{sk}.npz"
                if src_d.is_file() and src_e.is_file():
                    dcache.parent.mkdir(parents=True, exist_ok=True)
                    ecache.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(src_d, dcache)
                    shutil.copy(src_e, ecache)
            if dcache.is_file() and ecache.is_file():
                import json
                dets = {int(k): v for k, v in json.loads(dcache.read_text()).items()}
                z = np.load(ecache, allow_pickle=False)
                keys = [tuple(int(x) for x in k) for k in z["keys"].tolist()]
                feats = z["osnet_imagenet"]
                fresh[(ck, s["key"])] = (dets, keys, feats)
            else:
                need_fresh.append((ck, s))

    res["night_gpu"] = None
    if need_fresh:
        gpu = wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=300)
        dev = "cuda" if torch.cuda.is_available() and gpu.get("free_mib", 0) >= cfg.get("min_free_mib", 2048) else "cpu"
        res["night_gpu"] = gpu
        from .reid_train import build, embed
        model = build(10).to(dev)
        model.eval()

        def embedder(crops):
            return embed(model, crops, dev, bs=cfg.get("embed_batch", 32))

        from .reid_assoc import _crops
        ck_weights = {c["name"]: c["weights"] for c in cfg["checkpoint_specs"]}
        for ck, s in need_fresh:
            sk = s["key"].replace("/", "__")
            dcache = out / "dets" / ck / f"{sk}.json"
            dets = detect_paths(ck_weights[ck], s["paths"], dcache, cfg["imgsz"], cfg["det_conf"],
                                batch=cfg.get("det_batch", 4))
            ecache = out / "emb" / "night" / ck / f"{sk}.npz"
            keys, crops = _crops(s, dets, cfg["emb_min_score"])
            feats = embedder(crops) if crops else np.zeros((0, 512), np.float32)
            ecache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(ecache, keys=np.array(keys, int).reshape(-1, 2), osnet_imagenet=feats)
            fresh[(ck, s["key"])] = (dets, keys, feats)

    night_arm_val: float | str = "app_only" if w_star == "app_only" else float(w_star)
    night_scores = _score_ds(night_seqs, night_ckpts, "batch_v8", [0.0, night_arm_val], cfg.get("ema", 0.9),
                             fresh=fresh)
    res["night"] = {"scores": night_scores, "analysis": _delta_analysis(night_scores, [night_arm_val]),
                    "checkpoints_used": night_ckpts, "w": w_star, "n_seq": len(night_seqs)}
    write_json(out / "results.json", res)
    try:
        figure(res, numeric_weights, out / "fig_h46b.png")
    except Exception as e:  # noqa: BLE001 - figure is cosmetic
        res["figure_error"] = repr(e)
    return res


def figure(res: dict[str, Any], weights: list[float], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    labels = [str(w) for w in weights[1:]] + (["app_only"] if "app_only" in res["day"]["analysis"] else [])
    for ax, ds in zip(axes, ("day", "mot20")):
        A = res[ds]["analysis"]
        means = [A[k]["assa_mean_delta"]["mean"] for k in labels]
        los = [A[k]["assa_mean_delta"]["boot95"][0] for k in labels]
        his = [A[k]["assa_mean_delta"]["boot95"][1] for k in labels]
        ax.errorbar(range(len(labels)), means, yerr=[np.array(means) - np.array(los), np.array(his) - np.array(means)],
                    fmt="o-", color="#3b6ea5", capsize=4)
        ax.axhline(0, color="#888", lw=0.8)
        ax.axhline(0.02, color="#c44", lw=0.8, ls="--")
        ax.set_xticks(range(len(labels)), labels, rotation=45)
        ax.set_title(ds)
        ax.set_xlabel("arm")
        ax.set_ylabel("dAssA vs w=0")
    ax = axes[2]
    A = res["night"]["analysis"]
    w = res["night"]["w"]
    r = A[str(w) if isinstance(w, str) else str(float(w))]["assa_mean_delta"]
    ax.errorbar(0, r["mean"], yerr=[[r["mean"] - r["boot95"][0]], [r["boot95"][1] - r["mean"]]],
                fmt="o", color="#c44", capsize=4)
    ax.axhline(0, color="#888", lw=0.8)
    ax.set_xticks([0], [f"night w*={w} (5 ckpt)"])
    ax.set_title("full night arm")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = ["| set | arm | dAssA [95%] | dDetA [95%] | dHOTA [95%] | dIDSW [95%] | n_seq | n_ckpt |",
         "|---|---|---|---|---|---|---|---|"]
    for ds in ("day", "mot20"):
        A = res[ds]["analysis"]
        for a in res["arms"]:
            if a == "0.0":
                continue
            r = A[a]
            aa, dd, hh, ii = r["assa_mean_delta"], r["deta_mean_delta"], r["hota_delta"], r["idsw_delta"]
            L.append(f"| {ds} | {a} | {aa['mean']:+.4f} [{aa['boot95'][0]:+.4f},{aa['boot95'][1]:+.4f}] | "
                     f"{dd['mean']:+.4f} [{dd['boot95'][0]:+.4f},{dd['boot95'][1]:+.4f}] | "
                     f"{hh['mean']:+.4f} [{hh['boot95'][0]:+.4f},{hh['boot95'][1]:+.4f}] | "
                     f"{ii['mean']:+.2f} [{ii['boot95'][0]:+.2f},{ii['boot95'][1]:+.2f}] | "
                     f"{r['n_seq']} | {r['n_ckpt']} |")
    cv = res["cross_validation"]
    L.append(f"\nceiling: day argmax w={res['ceiling']['day']['argmax_w']} "
             f"(ceiling_found={res['ceiling']['day']['ceiling_found']}); "
             f"mot20 argmax w={res['ceiling']['mot20']['argmax_w']} "
             f"(ceiling_found={res['ceiling']['mot20']['ceiling_found']})")
    L.append(f"\ncross-validation: w*(day)={cv['w_star_from_day']} -> mot20 held-out dAssA "
             f"{cv['mot20_dAssA_at_w_star_from_day']['mean']:+.4f} "
             f"[{cv['mot20_dAssA_at_w_star_from_day']['boot95'][0]:+.4f},"
             f"{cv['mot20_dAssA_at_w_star_from_day']['boot95'][1]:+.4f}]; "
             f"w*(mot20)={cv['w_star_from_mot20']} -> day held-out dAssA "
             f"{cv['day_dAssA_at_w_star_from_mot20']['mean']:+.4f} "
             f"[{cv['day_dAssA_at_w_star_from_mot20']['boot95'][0]:+.4f},"
             f"{cv['day_dAssA_at_w_star_from_mot20']['boot95'][1]:+.4f}]")
    if "night" in res:
        w = res["night"]["w"]
        r = res["night"]["analysis"][str(w) if isinstance(w, str) else str(float(w))]["assa_mean_delta"]
        L.append(f"\nfull night arm (w*={w}, {res['night']['n_seq']} seqs x "
                 f"{len(res['night']['checkpoints_used'])} ckpt): dAssA {r['mean']:+.4f} "
                 f"[{r['boot95'][0]:+.4f},{r['boot95'][1]:+.4f}]")
    return "\n".join(L) + "\n"
