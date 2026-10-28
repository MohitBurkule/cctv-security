"""H34: label-free drift monitor on per-frame image statistics (docs/research/32).

Per camera stream: degrade raw batch renders with the baseline profile; from the
shift point on, substitute the same stream degraded with a shifted profile (dusk
exposure drop, defocus, codec, lens dirt). A monitor compares a trailing window of
the 13 `realism.stats` numbers (or a detector-backbone embedding) against the
first ``ref`` samples of the same camera and triggers on a threshold.

Run: ``python -m cctvsec.experiments.drift_monitor [--out DIR]`` (the runner is
registered into ``RUNNERS`` at import, so ``run_experiment`` works too).
"""
from __future__ import annotations

import dataclasses
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from .common import read_mot_rows, rpath

STAT_KEYS = ["noise_sigma", "lap_var_log10", "mtf_ratio", "edge_width", "luma_mean",
             "rms_contrast", "dynamic_range", "luma_skew", "hist_entropy", "chroma_mean",
             "cast_a", "cast_b", "blockiness"]


# ------------------------------------------------------------------ monitor scores

def psi(ref: np.ndarray, win: np.ndarray, bins: int = 10, eps: float = 1e-4) -> float:
    """Population stability index of ``win`` against reference-quantile bins of ``ref``."""
    ref, win = np.asarray(ref, float), np.asarray(win, float)
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)[1:-1]))
    r = np.bincount(np.searchsorted(edges, ref, side="right"), minlength=len(edges) + 1) / len(ref)
    w = np.bincount(np.searchsorted(edges, win, side="right"), minlength=len(edges) + 1) / len(win)
    r, w = np.maximum(r, eps), np.maximum(w, eps)
    return float(((w - r) * np.log(w / r)).sum())


def psi_max(ref: np.ndarray, win: np.ndarray, bins: int = 10) -> float:
    return max(psi(ref[:, j], win[:, j], bins) for j in range(ref.shape[1]))


def ks_min_p(ref: np.ndarray, win: np.ndarray) -> float:
    from scipy.stats import ks_2samp
    return min(float(ks_2samp(ref[:, j], win[:, j]).pvalue) for j in range(ref.shape[1]))


def z_max(ref: np.ndarray, win: np.ndarray) -> float:
    sd = ref.std(axis=0) + 1e-9
    return float(np.max(np.abs(win.mean(axis=0) - ref.mean(axis=0)) / sd))


def emb_score(ref: np.ndarray, win: np.ndarray) -> float:
    mu = ref.mean(axis=0)
    scale = float(np.median(np.linalg.norm(ref - mu, axis=1))) + 1e-9
    return float(np.linalg.norm(win.mean(axis=0) - mu) / scale)


def score_series(x: np.ndarray, ref: tuple[int, int], window: int, kind: str,
                 bins: int = 10) -> np.ndarray:
    """Score at every sample t >= ref_end + window - 1 (NaN before), window = x[t-window+1..t]."""
    r = x[ref[0]:ref[1]]
    fn = {"psi": lambda a, b: psi_max(a, b, bins), "ks": ks_min_p, "z": z_max,
          "emb": emb_score}[kind]
    out = np.full(len(x), np.nan)
    for t in range(ref[1] + window - 1, len(x)):
        out[t] = fn(r, x[t - window + 1:t + 1])
    return out


def triggers(scores: np.ndarray, thr: float, lower_is_alarm: bool = False) -> np.ndarray:
    s = np.nan_to_num(scores, nan=np.inf if lower_is_alarm else -np.inf)
    return s < thr if lower_is_alarm else s > thr


def first_delay(trig: np.ndarray, shift_at: int) -> int | None:
    idx = np.where(trig[shift_at:])[0]
    return int(idx[0]) if len(idx) else None


def per_24h(rate: float, evals_per_24h: int = 1440) -> float:
    return rate * evals_per_24h


# ------------------------------------------------------------------ stream workers

def shifted_profile(base, params: dict[str, float]):
    p = dict(params)
    kw = {}
    if "iso_mult" in p:
        kw["iso_gain"] = base.iso_gain * p.pop("iso_mult")
    kw.update(p)
    if "crf" in kw:
        kw["crf"] = int(kw["crf"])
    return dataclasses.replace(base, **kw)


def _embedder(imgsz: int):
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(1)
    m = YOLO("yolov8n.pt")
    feats: list[np.ndarray] = []
    m.model.model[9].register_forward_hook(
        lambda _m, _i, o: feats.append(o.mean(dim=(2, 3)).detach().cpu().numpy()))

    def f(imgs):
        feats.clear()
        for i in range(0, len(imgs), 16):
            m.predict(imgs[i:i + 16], imgsz=imgsz, device="cpu", verbose=False)
        return np.concatenate(feats, 0)
    return f


def stream_job(spec: dict[str, Any]) -> dict[str, Any]:
    """Degrade one camera stream with one profile; return stats + embedding (+ kept frames)."""
    import cv2

    from survsim.realism.stats import frame_stats
    from survsim.sensors.degrade import PROFILES, apply_sequence
    cv2.setNumThreads(1)
    cache = Path(spec["cache"])
    if cache.is_file():
        d = np.load(cache)
        return {"stats": d["stats"], "emb": d["emb"]}
    base = PROFILES[spec["base_profile"]]
    prof = shifted_profile(base, spec["params"]) if spec["params"] else base
    frames = [cv2.imread(str(p)) for p in spec["paths"]]
    bad = [p for p, f in zip(spec["paths"], frames) if f is None]
    if bad:
        # cv2.imread returns None (no exception) for a missing/unreadable file, and
        # apply_sequence then fails deep inside with "'NoneType' is not subscriptable".
        raise FileNotFoundError(f"{len(bad)}/{len(frames)} unreadable frames, first {bad[0]}")
    deg = list(apply_sequence(frames, prof, sequence_seed=spec["seed"]))
    stats = np.array([[getattr(fs, k) for k in STAT_KEYS]
                      for fs in (frame_stats(x) for x in deg)], np.float64)
    emb = _embedder(spec["emb_imgsz"])(deg)
    keep_dir = Path(spec["keep_dir"])
    keep_dir.mkdir(parents=True, exist_ok=True)
    for s in spec["keep"]:
        cv2.imwrite(str(keep_dir / f"{s:04d}.png"), deg[s])
    np.savez(cache, stats=stats, emb=emb)
    return {"stats": stats, "emb": emb}


# ------------------------------------------------------------------ recall

def recall_frames(cams: list[str], n: int, shift_at: int, n_samples: int) -> dict[str, list[int]]:
    """Deterministic post-shift sample indices, spread over cameras."""
    out: dict[str, list[int]] = {c: [] for c in cams}
    span = n_samples - shift_at
    for j in range(n):
        c = cams[j % len(cams)]
        k = j // len(cams)
        out[c].append(shift_at + 3 + (k * 23 + (j % len(cams)) * 2) % (span - 3))
    return out


def detect_recall(img_paths: list[Path], gts: list[list[dict]], rcfg: dict) -> dict[str, Any]:
    from ultralytics import YOLO

    from .common import match_frame
    m = YOLO(str(rpath(rcfg["weights"])))
    tp = n = 0
    for i in range(0, len(img_paths), 8):
        res = m.predict([str(p) for p in img_paths[i:i + 8]], imgsz=rcfg["imgsz"], device="cpu",
                        conf=rcfg["conf"], classes=[0], verbose=False)
        for r, g in zip(res, gts[i:i + 8]):
            xyxy = r.boxes.xyxy.cpu().numpy()
            p = np.c_[xyxy[:, :2], xyxy[:, 2:] - xyxy[:, :2]] if len(xyxy) else np.zeros((0, 4))
            ga = np.array([row["bbox"] for row in g], float).reshape(-1, 4)
            gm, _ = match_frame(ga, p, r.boxes.conf.cpu().numpy(), rcfg["iou"])
            tp += int(gm.sum())
            n += len(ga)
    return {"recall": tp / max(1, n), "tp": tp, "n_gt": n}


# ------------------------------------------------------------------ run

def conditions(cfg) -> list[tuple[str, dict]]:
    return [(f"{k}_{i + 1}", p) for k, lst in cfg["shifts"].items() for i, p in enumerate(lst)]


def stream_cams(cfg: dict[str, Any]) -> list[str]:
    """`cams` is a list shared by every run, or a {run: [cams]} map (runs differ in
    camera names: disguise_and_tamper_* uses cam_gate/cam_sub/..., not cam_NN)."""
    cc = cfg["cams"]
    return [f"{r}/{c}" for r in cfg["runs"] for c in (cc[r] if isinstance(cc, dict) else cc)]


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from .inference import rule_of_three, spearman
    batch = rpath(cfg["batch"])
    stride, n_s, sh = cfg["stride"], cfg["n_samples"], cfg["shift_at"]
    ref, W = tuple(cfg["ref"]), cfg["window"]
    cams = stream_cams(cfg)
    rf = recall_frames(cams, cfg["recall"]["frames_per_condition"], sh, n_s)
    conds = conditions(cfg)
    (out / "cache").mkdir(parents=True, exist_ok=True)
    specs = {}
    for cam in cams:
        run_, c = cam.split("/")
        paths = [batch / run_ / "render" / c / f"{i * stride:04d}.png" for i in range(n_s)]
        for s in cfg["null_seeds"]:
            specs[(cam, "null", s)] = {"params": None, "seed": s}
        for name, p in conds:
            specs[(cam, name, 0)] = {"params": p, "seed": 0}
        for key, sp in specs.items():
            if key[0] != cam:
                continue
            tag = f"{cam.replace('/', '__')}__{key[1]}__s{key[2]}"
            sp.update(paths=[str(p) for p in paths], base_profile=cfg["base_profile"],
                      emb_imgsz=cfg["emb_imgsz"], cache=str(out / "cache" / f"{tag}.npz"),
                      keep=rf[cam] if key[2] == 0 else [], keep_dir=str(out / "frames" / tag))
    keys = list(specs)
    with ProcessPoolExecutor(cfg["workers"]) as ex:
        res = dict(zip(keys, ex.map(stream_job, [specs[k] for k in keys])))

    def spliced(cam, cond, what):
        base = res[(cam, "null", 0)][what]
        if cond == "null":
            return base
        return np.concatenate([base[:sh], res[(cam, cond, 0)][what][sh:]])

    arms = {f"psi_{t:.2f}": ("psi", t) for t in cfg["psi_thresholds"]}
    arms.update(ks=("ks", cfg["ks_alpha"] / len(STAT_KEYS)), z_cal=("z", None), emb=("emb", None))
    kinds = ("psi", "ks", "z", "emb")
    series: dict[tuple, np.ndarray] = {}
    for cam in cams:
        for s in cfg["null_seeds"]:
            for k in kinds:
                x = res[(cam, "null", s)]["emb" if k == "emb" else "stats"]
                series[(cam, "null", s, k)] = score_series(x, ref, W, k, cfg["psi_bins"])
        for name, _ in conds:
            for k in kinds:
                x = spliced(cam, name, "emb" if k == "emb" else "stats")
                series[(cam, name, 0, k)] = score_series(x, ref, W, k, cfg["psi_bins"])
    # calibrated thresholds from calibration-seed null streams
    cal = cfg["calib_seed"]
    for a, k in (("z_cal", "z"), ("emb", "emb")):
        mx = max(np.nanmax(series[(c, "null", cal, k)]) for c in cams)
        arms[a] = (k, float(mx * cfg["cal_margin"]))
    t0 = ref[1] + W - 1
    body: dict[str, Any] = {"arms": {}, "thresholds": {a: v[1] for a, v in arms.items()}}
    for a, (k, thr) in arms.items():
        low = k == "ks"
        # false triggers: null streams (test seeds for calibrated arms) + pre-shift evals
        seeds = [s for s in cfg["null_seeds"] if not (a in ("z_cal", "emb") and s == cal)]
        null_tr = [triggers(series[(c, "null", s, k)], thr, low)[t0:] for c in cams for s in seeds]
        null_tr += [triggers(series[(c, n, 0, k)], thr, low)[t0:sh] for c in cams for n, _ in conds]
        allv = np.concatenate(null_tr)
        n_ind = sum(len(v) // W for v in null_tr)
        n_ind_fire = sum(int(v[: (len(v) // W) * W].reshape(-1, W)[:, -1].sum()) for v in null_tr)
        rate = float(allv.mean())
        delays = {}
        for n, _ in conds:
            d = [first_delay(triggers(series[(c, n, 0, k)], thr, low), sh) for c in cams]
            det = [x for x in d if x is not None]
            delays[n] = {"median_delay_samples": (float(np.median(det)) if len(det) > len(cams) / 2
                                                  else None),
                         "detected_cams": len(det), "delays": d}
        body["arms"][a] = {
            "threshold": thr, "null_evals": len(allv), "null_fires": int(allv.sum()),
            "fa_rate_per_eval": rate, "fa_per_24h": per_24h(rate, cfg["evals_per_24h"]),
            "independent_windows": n_ind, "independent_fires": n_ind_fire,
            "fa_per_24h_ro3_upper": (per_24h(rule_of_three(n_ind) , cfg["evals_per_24h"])
                                     if n_ind_fire == 0 else None),
            "conditions_detected": sum(v["median_delay_samples"] is not None for v in delays.values()),
            "delays": delays}
    # recall on kept post-shift frames
    rcfg = cfg["recall"]
    gtc = {}
    items = []
    for cam in cams:
        run_, c = cam.split("/")
        gt = read_mot_rows(batch / run_ / "gt" / f"mot_{c}.txt")
        for s in rf[cam]:
            rows = [r for r in gt.get(s * stride, []) if r["bbox"][3] >= rcfg["min_h"]]
            items.append((cam, s, rows))
    for cond in ["null"] + [n for n, _ in conds]:
        paths = [out / "frames" / f"{cam.replace('/', '__')}__{cond}__s0" / f"{s:04d}.png"
                 for cam, s, _ in items]
        gtc[cond] = detect_recall(paths, [r for _, _, r in items], rcfg)
    body["recall"] = gtc
    drop = [gtc["null"]["recall"] - gtc[n]["recall"] for n, _ in conds]
    body["correlation"] = {}
    for a, (k, _) in arms.items():
        if a.startswith("psi_") and a != f"psi_{cfg['psi_thresholds'][0]:.2f}":
            continue
        post = [float(np.nanmean([np.nanmean(series[(c, n, 0, k)][sh:]) for c in cams]))
                for n, _ in conds]
        if k == "ks":
            post = [-np.log10(max(p, 1e-300)) for p in post]
        sp = spearman(post, drop, n_boot=4000, n_perm=10000)
        body["correlation"]["psi" if k == "psi" else a] = {"post_mean_score": post, **sp}
    body["recall_drop"] = dict(zip([n for n, _ in conds], drop))
    ex_cam = cams[0]
    body["figure_series"] = {k: {n: np.nan_to_num(series[(ex_cam, n, 0, k)], nan=0).tolist()
                                 for n in ("dusk_2", "blur_2", "codec_2", "dirt_2")
                                 if (ex_cam, n, 0, k) in series}
                             for k in kinds}
    body["figure_cam"] = ex_cam
    body["verdict"] = verdict(body, len(conds))
    return body


def verdict(body: dict, n_conds: int) -> dict[str, Any]:
    per = {}
    for a, r in body["arms"].items():
        k = "psi" if a.startswith("psi") else a
        rho = body["correlation"].get(k, {}).get("rho", float("nan"))
        per[a] = {"detect_ok": r["conditions_detected"] >= 10, "fa_ok": r["fa_per_24h"] <= 1.0,
                  "rho_ok": bool(rho >= 0.5), "rho": rho}
        per[a]["supported"] = all(per[a][x] for x in ("detect_ok", "fa_ok", "rho_ok"))
    if any(v["supported"] for v in per.values()):
        v = "SUPPORTED"
    elif all(not v["fa_ok"] for v in per.values()) or all(not v["rho_ok"] for v in per.values()):
        v = "REFUTED"
    else:
        v = "INCONCLUSIVE"
    return {"overall": v, "per_arm": per}


def markdown_rows(body: dict[str, Any], cfg: dict[str, Any]) -> str:
    conds = [n for n, _ in conditions(cfg)]
    lines = ["| arm | thr | " + " | ".join(conds) + " | FA/eval | FA/24 cam-h | ρ(score, recall drop) |",
             "|---|---|" + "---|" * len(conds) + "---|---|---|"]
    for a, r in body["arms"].items():
        k = "psi" if a.startswith("psi") else a
        c = body["correlation"].get(k, {})
        d = [("miss" if r["delays"][n]["median_delay_samples"] is None
              else f"{r['delays'][n]['median_delay_samples']:.0f}") for n in conds]
        lines.append(f"| {a} | {r['threshold']:.3g} | " + " | ".join(d)
                     + f" | {r['fa_rate_per_eval']:.3f} | {r['fa_per_24h']:.1f} | "
                     + (f"{c['rho']:.2f} [{c.get('ci_lo', float('nan')):.2f}, "
                        f"{c.get('ci_hi', float('nan')):.2f}]" if c else "") + " |")
    rec = body["recall"]
    lines.append("")
    lines.append("recall: " + ", ".join(f"{k} {v['recall']:.3f}" for k, v in rec.items()))
    lines.append(f"\nverdict: {body['verdict']['overall']}")
    return "\n".join(lines) + "\n"


def figure(body: dict[str, Any], cfg: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    kinds = [("psi", "PSI (max over 13 stats)", body["thresholds"]["psi_0.20"]),
             ("z", "z_cal (max |Δmean|/sd)", body["thresholds"]["z_cal"]),
             ("emb", "embedding drift", body["thresholds"]["emb"])]
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.6), sharex=True)
    t0 = cfg["ref"][1] + cfg["window"] - 1
    for ax, (k, title, thr) in zip(axs, kinds):
        for n, s in body["figure_series"][k].items():
            y = np.array(s)
            ax.plot(np.arange(t0, len(y)), y[t0:], lw=1.2, label=n)
        ax.axvline(cfg["shift_at"], color="k", ls="--", lw=1, label="shift")
        ax.axhline(thr, color="grey", ls=":", lw=1, label="threshold")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("sample (2 frames each)")
        ax.set_yscale("log")
    axs[0].legend(fontsize=7)
    fig.suptitle(f"H34 drift score vs time, {body['figure_cam']} (severity 2 shifts)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def main(argv=None) -> None:
    import argparse

    from cctvsec.experiments import RUNNERS, run_experiment
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/experiments/h34_drift_monitor")
    ap.add_argument("--fig", default="docs/research/figures/fig_h34.png")
    a = ap.parse_args(argv)
    RUNNERS.setdefault("drift_monitor", "drift_monitor")
    res = run_experiment("h34_drift_monitor", out=Path(a.out))
    figure(res, res["config"], rpath(a.fig))
    print(json.dumps({"verdict": res["verdict"], "correlation": {k: v["rho"] for k, v in
                                                                 res["correlation"].items()}}))


if __name__ == "__main__":
    main()
