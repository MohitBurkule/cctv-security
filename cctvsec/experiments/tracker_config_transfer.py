"""H71: does the full ByteTrack configuration chosen on renders rank the same on real MOT20?

Pre-registered docs/research/32 sec H71. 24-config grid (w x match_iou x max_lost
seconds x high) scored by TrackEval HOTA on the CC0 batch_v8 day sequences (cached
H24 dets/embeddings) and on MOT20-01/02/03/05 (first 300 frames; MOT20-02 cached by
H17/H24, the rest detected/embedded once here). MOT20 is non-commercial: measure only.
"""
from __future__ import annotations

import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, wait_for_gpu, write_json

KNOBS = ("w", "match_iou", "max_lost_s", "high")


def grid(cfg: dict[str, Any]) -> list[dict[str, float]]:
    g = cfg["grid"]
    return [dict(zip(KNOBS, v)) for v in itertools.product(*(g[k] for k in KNOBS))]


def cfg_label(c: dict[str, float]) -> str:
    return f"w{c['w']:g}_iou{c['match_iou']:g}_age{c['max_lost_s']:g}_hi{c['high']:g}"


# ------------------------------------------------------------------ stats (pure, unit-tested)

def spearman(a, b) -> float:
    from scipy.stats import spearmanr
    r = spearmanr(np.asarray(a, float), np.asarray(b, float)).correlation
    return float(r) if np.isfinite(r) else 0.0


def regret(render_scores, real_scores) -> float:
    """real HOTA of the real-best config minus real HOTA of the render-best config (>= 0)."""
    real = np.asarray(real_scores, float)
    return float(real.max() - real[int(np.argmax(render_scores))])


def marginal(scores, configs: list[dict[str, float]], knob: str) -> dict[str, Any]:
    """Mean score per level of `knob` (averaged over the other knobs) and the preferred level."""
    s = np.asarray(scores, float)
    levels = sorted({c[knob] for c in configs})
    means = [float(s[[c[knob] == lv for c in configs]].mean()) for lv in levels]
    return {"levels": levels, "means": means, "preferred": levels[int(np.argmax(means))],
            "delta_last_minus_first": means[-1] - means[0]}


def within_rho(render, real, configs, knob: str) -> float:
    """Mean Spearman rho computed inside each level of `knob` (removes that knob's ordering)."""
    r, q = np.asarray(render, float), np.asarray(real, float)
    rs = []
    for lv in sorted({c[knob] for c in configs}):
        m = np.array([c[knob] == lv for c in configs])
        rs.append(spearman(r[m], q[m]))
    return float(np.mean(rs))


def bootstrap(R: np.ndarray, Q: np.ndarray, configs, n: int = 2000, seed: int = 0) -> dict[str, Any]:
    """R[seq, config] render HOTA, Q[seq, config] real HOTA; resample sequences independently."""
    rng = np.random.default_rng(seed)
    rho, reg, marg = [], [], {k: [] for k in KNOBS}
    for _ in range(n):
        r = R[rng.integers(0, len(R), len(R))].mean(0)
        q = Q[rng.integers(0, len(Q), len(Q))].mean(0)
        rho.append(spearman(r, q))
        reg.append(regret(r, q))
        for k in KNOBS:
            marg[k].append((marginal(r, configs, k)["delta_last_minus_first"],
                            marginal(q, configs, k)["delta_last_minus_first"]))

    def ci(x):
        return [round(float(np.quantile(x, .025)), 4), round(float(np.quantile(x, .975)), 4)]
    return {"rho_ci95": ci(rho), "regret_ci95": ci(reg),
            "marginal_delta_ci95": {k: {"render": ci([a for a, _ in v]), "real": ci([b for _, b in v]),
                                        "p_same_sign": round(float(np.mean([np.sign(a) == np.sign(b)
                                                                            for a, b in v])), 4)}
                                    for k, v in marg.items()}}


def analyse(R: np.ndarray, Q: np.ndarray, configs, n_boot: int = 2000) -> dict[str, Any]:
    r, q = R.mean(0), Q.mean(0)
    margs = {k: {"render": marginal(r, configs, k), "real": marginal(q, configs, k)} for k in KNOBS}
    for m in margs.values():
        m["transfers"] = bool(m["render"]["preferred"] == m["real"]["preferred"]
                              and np.sign(m["render"]["delta_last_minus_first"])
                              == np.sign(m["real"]["delta_last_minus_first"]))
    dominant = max(KNOBS, key=lambda k: abs(margs[k]["render"]["delta_last_minus_first"]))
    boot = bootstrap(R, Q, configs, n=n_boot)
    rho, reg = spearman(r, q), regret(r, q)
    hn = margs["high"]
    return {
        "rho": round(rho, 4), "rho_ci95": boot["rho_ci95"],
        "regret": round(reg, 4), "regret_ci95": boot["regret_ci95"],
        "render_best": cfg_label(configs[int(np.argmax(r))]), "real_best": cfg_label(configs[int(np.argmax(q))]),
        "real_hota_render_best": round(float(q[int(np.argmax(r))]), 4), "real_hota_real_best": round(float(q.max()), 4),
        "render_rank": [int(x) for x in (-r).argsort().argsort() + 1],
        "real_rank": [int(x) for x in (-q).argsort().argsort() + 1],
        "marginals": margs, "marginal_boot": boot["marginal_delta_ci95"],
        "dominant_render_knob": dominant,
        "rho_within_dominant_knob": round(within_rho(r, q, configs, dominant), 4),
        "decision": {"D1_rho": bool(rho >= 0.6 and boot["rho_ci95"][0] > 0), "D2_regret": bool(reg <= 0.02)},
        "hard_negative": {"knob": "high", "predicted": "does not transfer",
                          "observed_transfers": hn["transfers"],
                          "prediction_held": not hn["transfers"]},
    }


# ------------------------------------------------------------------ data

def _mot20_seq(root: Path, name: str, max_frame: int) -> dict[str, Any]:
    from survsim.datasets.build import read_gt
    targets, ignore = read_gt(root / name / "gt" / "gt.txt")
    frames = list(range(1, max_frame + 1))
    keep = set(frames)
    gt = [r for r in targets if r["frame"] in keep]
    return {"key": f"{name}/{name}", "run": name, "cam": name, "frames": frames,
            "paths": {f: str(root / name / "img1" / f"{f:06d}.jpg") for f in frames},
            "gt": gt, "ignore": [r for r in ignore if r["frame"] in keep], "fps": 25.0}


def _load(det_path: Path, emb_path: Path) -> dict[int, list[dict]]:
    dets = {int(k): v for k, v in json.loads(det_path.read_text()).items()}
    z = np.load(emb_path, allow_pickle=False)
    for (f, i), e in zip(z["keys"].tolist(), z["osnet_imagenet"]):
        dets[int(f)][int(i)]["emb"] = e
    return dets


def _ensure_mot20(cfg, out: Path, seqs) -> dict[str, Any]:
    """Detect + embed MOT20 sequences not in the H17/H24 cache. Returns GPU/partial info."""
    from .tracking import detect_paths
    info: dict[str, Any] = {"fresh": [], "device": None}
    todo = []
    for s in seqs:
        sk = s["key"].replace("/", "__")
        cached = (rpath(cfg["h17_det_cache"]) / f"{sk}.json", rpath(cfg["h24_emb_cache"]) / f"{sk}.npz")
        if all(p.is_file() for p in cached):
            s["_det"], s["_emb"] = cached
            continue
        s["_det"], s["_emb"] = out / "dets" / f"{sk}.json", out / "emb" / f"{sk}.npz"
        if not (s["_det"].is_file() and s["_emb"].is_file()):
            todo.append(s)
    if not todo:
        return info
    import torch
    running = list(Path("/tmp/survsim_jobs").glob("*.running")) if Path("/tmp/survsim_jobs").is_dir() else []
    gpu = wait_for_gpu(cfg.get("min_free_mib", 3500), max_wait_s=300) if not running else {"skipped": "render running"}
    dev = "cuda" if (not running and torch.cuda.is_available()
                     and gpu.get("free_mib", 0) >= cfg.get("min_free_mib", 3500)) else "cpu"
    info.update(device=dev, gpu=gpu)
    from .reid_assoc import _crops
    from .reid_train import build, embed
    model = build(10).to(dev)
    model.eval()
    for s in todo:
        dets = detect_paths(str(rpath(cfg["detector"])), s["paths"], s["_det"], cfg["imgsz"], cfg["det_conf"],
                            batch=cfg.get("det_batch", 4))
        keys, crops = _crops(s, dets, cfg["emb_min_score"])
        feats = embed(model, crops, dev, bs=cfg.get("embed_batch", 32)) if crops else np.zeros((0, 512), np.float32)
        s["_emb"].parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(s["_emb"], keys=np.array(keys, int).reshape(-1, 2), osnet_imagenet=feats)
        info["fresh"].append(s["key"])
    del model
    if dev == "cuda":
        torch.cuda.empty_cache()
    return info


def _score_one(args) -> list[float]:
    """HOTA per sequence for one config (runs in a worker)."""
    seqs, c, ema = args
    from ..baselines.bytetrack import track_sequence
    from ..baselines.run import _drop_ignored
    from .reid_assoc import trackeval_score
    tracks = {}
    for s in seqs:
        dets = _load(s["_det"], s["_emb"])
        tr = track_sequence(dets, s["frames"], max_lost=max(1, round(c["max_lost_s"] * s["fps"])),
                            high=c["high"], low=0.1, new_track=0.6, match_iou=c["match_iou"],
                            app_weight=c["w"], ema=ema)
        tracks[s["key"]] = _drop_ignored(tr, s["ignore"]) if s["ignore"] else tr
    sc = trackeval_score(seqs, tracks)
    return [float(sc[s["key"].replace("/", "__")]["hota"]) for s in seqs]


def score_matrix(seqs, configs, ema: float, workers: int) -> np.ndarray:
    lite = [{k: v for k, v in s.items() if k != "paths"} for s in seqs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        cols = list(ex.map(_score_one, [(lite, c, ema) for c in configs]))
    return np.array(cols).T   # [seq, config]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from .tracking import v7_sequences
    configs = grid(cfg)
    render = v7_sequences({"batch_dir": cfg["batch_dir"], "runs": cfg["day_runs"],
                           "max_frame": cfg["max_frame"], "fps": cfg["batch_fps"]})
    h24 = rpath(cfg["h24_out"])
    for s in render:
        sk = s["key"].replace("/", "__")
        s["_det"] = h24 / "dets" / cfg["checkpoint"] / f"{sk}.json"
        s["_emb"] = h24 / "emb" / "batch_v8" / cfg["checkpoint"] / f"{sk}.npz"
    root = Path(rpath(cfg["mot20_root"]))
    real = [_mot20_seq(root, n, cfg["max_frame"]) for n in cfg["mot20_sequences"]]
    info = _ensure_mot20(cfg, out, real)
    w = int(cfg.get("workers", 6))
    R = score_matrix(render, configs, cfg.get("ema", 0.9), w)
    Q = score_matrix(real, configs, cfg.get("ema", 0.9), w)
    res = {"configs": [cfg_label(c) for c in configs], "grid": cfg["grid"],
           "render_seqs": [s["key"] for s in render], "real_seqs": [s["key"] for s in real],
           "hota_render": R.round(4).tolist(), "hota_real": Q.round(4).tolist(),
           "mot20_detection": info, "partial": False,
           "analysis": analyse(R, Q, configs, n_boot=int(cfg.get("n_boot", 2000)))}
    write_json(out / "partial.json", res)
    try:
        figure(res, rpath(cfg["figure"]))
    except Exception as e:  # noqa: BLE001 - figure is cosmetic
        res["figure_error"] = repr(e)
    return res


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    A = res["analysis"]
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    hi = [lbl.endswith("hi0.6") for lbl in res["configs"]]
    for flag, col, name in ((False, "#3b6ea5", "high=0.4"), (True, "#c44", "high=0.6")):
        xs = [a for a, h in zip(A["render_rank"], hi) if h == flag]
        ys = [b for b, h in zip(A["real_rank"], hi) if h == flag]
        ax.scatter(xs, ys, color=col, label=name, s=28)
    n = len(res["configs"])
    ax.plot([1, n], [1, n], color="#888", lw=0.8, ls="--")
    ax.set_xlabel("render rank (batch_v8, CC0)")
    ax.set_ylabel("real rank (MOT20)")
    ax.set_title(f"H71: rho={A['rho']:+.2f} [{A['rho_ci95'][0]:+.2f},{A['rho_ci95'][1]:+.2f}], "
                 f"regret={A['regret']:.3f}", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    A = res["analysis"]
    L = [(f"rho {A['rho']:+.4f} [{A['rho_ci95'][0]:+.4f},{A['rho_ci95'][1]:+.4f}]; regret {A['regret']:.4f} "
         f"[{A['regret_ci95'][0]:.4f},{A['regret_ci95'][1]:.4f}]; render-best {A['render_best']}, "
         f"real-best {A['real_best']}; decision {A['decision']}; hard negative {A['hard_negative']}"),
         f"rho within dominant render knob ({A['dominant_render_knob']}): {A['rho_within_dominant_knob']:+.4f}",
         "", "| knob | render pref | real pref | render d(last-first) | real d | P(same sign) | transfers |",
         "|---|---|---|---|---|---|---|"]
    for k, m in A["marginals"].items():
        b = A["marginal_boot"][k]
        L.append(f"| {k} | {m['render']['preferred']:g} | {m['real']['preferred']:g} | "
                 f"{m['render']['delta_last_minus_first']:+.4f} {b['render']} | "
                 f"{m['real']['delta_last_minus_first']:+.4f} {b['real']} | {b['p_same_sign']} | {m['transfers']} |")
    return "\n".join(L) + "\n"
