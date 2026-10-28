"""H69 — cross-site generalisation of detector recall and a pooled FA threshold.

Pre-registered in docs/research/32 (H69). Sites come from tools/infinite_sites.py
(`out/showcase/sites`, read-only here); only gate-PASS, commercial-ML-licensed
sites are used. Detector = the docs/13 operating point (YOLO11n, imgsz 1280,
conf 0.25, IoU 0.5). Detections are cached per site so the statistics can be
re-run without the GPU.

Pure functions (`recall_boot`, `between_sd`, `calibrate_theta`, `split_transfer`,
`ols_adj_r2`, `hard_negative`) take per-frame arrays so tests can run them on
synthetic inputs.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from ..eval.detection import iou_matrix

FPS = 10.0
TOD = {"day": 0, "dusk": 1, "night": 2}
COVARIATES = ("cam_height_m", "range_m", "density", "tod_ord")


# ---------------------------------------------------------------- site discovery
def scan_sites(root: Path, min_frames: int = 30) -> tuple[list[dict], list[dict]]:
    """Return (usable, excluded) site metadata; usable = gate summary 'PASS: 0 failed' + commercial_ml_ok + frames."""
    use, excl = [], []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        why = None
        meta = json.loads((d / "site.json").read_text()) if (d / "site.json").is_file() else None
        gate = (d / "gate.txt").read_text() if (d / "gate.txt").is_file() else ""
        last = [ln for ln in gate.splitlines() if ln.strip()][-1:] or [""]
        lic = d / "set" / "licences.json"
        if meta is None:
            why = "no site.json"
        elif not last[0].startswith("PASS: 0 failed") or " FAIL " in gate:
            why = "gate missing or not PASS"
        elif not lic.is_file() or not json.loads(lic.read_text()).get("commercial_ml_ok"):
            why = "licence not commercial_ml_ok"
        else:
            frames = sorted((d / "set" / "render" / meta["camera"]).glob("*.png"))
            if len(frames) < min_frames:
                why = f"{len(frames)} frames"
        if why:
            excl.append({"site": d.name, "why": why})
        else:
            use.append({**meta, "name": d.name, "dir": str(d)})
    return use, excl


def _gpu_used_mib() -> int:
    q = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, check=True)
    return int(q.stdout.split()[0])


def detect_site(site: dict, cache: Path, cfg: dict) -> dict[int, list]:
    """Per image index -> [[x, y, w, h, score], ...] (conf floor cfg['det_floor']); cached."""
    f = cache / f"{site['name']}.json"
    if f.is_file():
        return {int(k): v for k, v in json.loads(f.read_text()).items()}
    used = _gpu_used_mib()
    if used >= cfg["gpu_max_used_mib"]:
        raise RuntimeError(f"GPU has {used} MiB used >= {cfg['gpu_max_used_mib']}; not running YOLO")
    from ultralytics import YOLO
    net = YOLO(cfg["weights"])
    frames = sorted((Path(site["dir"]) / "set" / "render" / site["camera"]).glob("*.png"))
    out: dict[int, list] = {}
    for i in range(0, len(frames), cfg["batch"]):
        chunk = frames[i:i + cfg["batch"]]
        preds = net.predict([str(p) for p in chunk], classes=[0], conf=cfg["det_floor"], imgsz=cfg["imgsz"],
                            verbose=False, half=True, max_det=300)
        for p, r in zip(chunk, preds):
            xyxy, sc = r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()
            out[int(p.stem)] = [[float(a), float(b), float(x - a), float(y - b), float(s)]
                                for (a, b, x, y), s in zip(xyxy, sc)]
    cache.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out))
    return out


def read_mot(path: Path) -> dict[int, list]:
    """Targets (conf 1, class 1): frame -> [[id, x, y, w, h, vis], ...]."""
    g: dict[int, list] = {}
    for ln in Path(path).read_text().splitlines():
        if ln.strip():
            v = [float(x) for x in ln.split(",")]
            if v[6] >= 1 and int(v[7]) == 1:
                g.setdefault(int(v[0]), []).append([int(v[1]), *v[2:6], v[8] if len(v) > 8 else 1.0])
    return g


def match_frame(gt: np.ndarray, det: np.ndarray, theta: float, iou_thr: float = 0.5) -> tuple[int, int, int]:
    """Greedy score-ordered IoU match (as eval.detection). gt Mx4, det Nx5 -> (n_gt, tp, fp)."""
    d = det[det[:, 4] >= theta] if len(det) else det.reshape(0, 5)
    d = d[np.argsort(-d[:, 4])]
    ious = iou_matrix(d[:, :4], gt.reshape(-1, 4))
    used, tp = set(), 0
    for i in range(len(d)):
        cand = [(ious[i, j], j) for j in range(len(gt)) if j not in used and ious[i, j] >= iou_thr]
        if cand:
            used.add(max(cand)[1])
            tp += 1
    return len(gt), tp, len(d) - tp


def frame_table(gt: dict[int, list], dets: dict[int, list], thetas: np.ndarray, op: float,
                min_h: float = 20.0) -> dict[str, np.ndarray]:
    """Per image: n_gt, tp at op, n_gt/tp for boxes >= min_h, for (>= min_h and vis >= 0.5; post-hoc),
    and fp at every theta."""
    idx = sorted(dets)
    ng, tp, ng20, tp20, ngv, tpv, fp = [], [], [], [], [], [], []
    for i in idx:
        gv = np.array([b[1:6] if len(b) > 5 else [*b[1:5], 1.0] for b in gt.get(i, [])], float).reshape(-1, 5)
        g, vis = gv[:, :4], gv[:, 4]
        d = np.array(dets[i], float).reshape(-1, 5)
        n, t, _ = match_frame(g, d, op)
        tall = g[:, 3] >= min_h
        n2, t2, _ = match_frame(g[tall], d, op)
        n3, t3, _ = match_frame(g[tall & (vis >= 0.5)], d, op)
        ng.append(n); tp.append(t); ng20.append(n2); tp20.append(t2); ngv.append(n3); tpv.append(t3)
        fp.append([match_frame(g, d, th)[2] for th in thetas])
    return {"n_gt": np.array(ng), "tp": np.array(tp), "n_gt20": np.array(ng20), "tp20": np.array(tp20),
            "n_gt_vis": np.array(ngv), "tp_vis": np.array(tpv),
            "fp": np.array(fp, float).reshape(len(idx), len(thetas))}


# ---------------------------------------------------------------- statistics
def recall_boot(n_gt: np.ndarray, tp: np.ndarray, rng, n_boot: int) -> tuple[float, np.ndarray]:
    """Point recall and frame-bootstrap replicates."""
    r = tp.sum() / max(n_gt.sum(), 1)
    ix = rng.integers(0, len(n_gt), (n_boot, len(n_gt)))
    reps = tp[ix].sum(1) / np.maximum(n_gt[ix].sum(1), 1)
    return float(r), reps


def between_sd(recalls: np.ndarray, within_var: np.ndarray) -> float:
    """Noise-corrected between-site SD: sqrt(max(0, var(r) - mean within-site var))."""
    return float(np.sqrt(max(0.0, np.var(recalls, ddof=1) - np.mean(within_var))))


def two_stage_sd(tables: list[dict], rng, n_boot: int) -> np.ndarray:
    """Resample sites, then frames within each; corrected SD per replicate."""
    out = np.empty(n_boot)
    S = len(tables)
    for b in range(n_boot):
        rs, wv = [], []
        for s in rng.integers(0, S, S):
            t = tables[s]
            ix = rng.integers(0, len(t["n_gt"]), len(t["n_gt"]))
            rs.append(t["tp"][ix].sum() / max(t["n_gt"][ix].sum(), 1))
            wv.append(t["_wvar"])
        out[b] = between_sd(np.array(rs), np.array(wv))
    return out


def fa_per_cam_h(fp: np.ndarray, n_frames: int) -> np.ndarray:
    """fp: summed FP per theta over n_frames -> FA/cam-h at FPS."""
    return fp / max(n_frames, 1) * FPS * 3600.0


def calibrate_theta(fp_sum: np.ndarray, n_frames: int, thetas: np.ndarray, budget: float) -> float:
    """Smallest theta whose pooled FA/cam-h <= budget (max theta if none)."""
    ok = np.nonzero(fa_per_cam_h(fp_sum, n_frames) <= budget)[0]
    return float(thetas[ok[0]] if len(ok) else thetas[-1])


def split_transfer(tables: list[dict], thetas: np.ndarray, budget: float, n_splits: int, rng) -> dict[str, Any]:
    S = len(tables)
    k = S // 2
    rows = []
    for _ in range(n_splits):
        perm = rng.permutation(S)
        cal, hold = perm[:k], perm[k:]
        fp_c = sum(tables[s]["fp"].sum(0) for s in cal)
        th = calibrate_theta(fp_c, sum(len(tables[s]["n_gt"]) for s in cal), thetas, budget)
        j = int(np.argmin(np.abs(thetas - th)))
        fp_h = sum(tables[s]["fp"][:, j].sum() for s in hold)
        nf_h = sum(len(tables[s]["n_gt"]) for s in hold)
        fa_h = float(fa_per_cam_h(np.array(fp_h), nf_h))
        per_site_ok = [float(fa_per_cam_h(np.array(tables[s]["fp"][:, j].sum()), len(tables[s]["n_gt"]))) <= budget
                       for s in hold]
        rows.append({"theta": th, "fa_hold": fa_h, "within": fa_h <= budget,
                     "site_within_frac": float(np.mean(per_site_ok))})
    th = np.array([r["theta"] for r in rows])
    within = np.array([r["within"] for r in rows])
    return {"n_splits": n_splits, "k_cal": k, "within_frac": float(within.mean()),
            "theta_median": float(np.median(th)), "theta_range": [float(th.min()), float(th.max())],
            "theta_at_min_frac": float(np.mean(th <= thetas[0] + 1e-9)),
            "fa_hold_median": float(np.median([r["fa_hold"] for r in rows])),
            "fa_hold_p95": float(np.percentile([r["fa_hold"] for r in rows], 95)),
            "site_within_frac_mean": float(np.mean([r["site_within_frac"] for r in rows]))}


def ols_adj_r2(X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    n, p = X.shape
    A = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    ss_res = float(((y - A @ beta) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    adj = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n - p - 1 > 0 else float("nan")
    press = 0.0
    for i in range(n):
        m = np.arange(n) != i
        b, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
        press += float((y[i] - A[i] @ b) ** 2)
    return {"n": n, "p": p, "beta": beta.tolist(), "r2": r2, "adj_r2": adj,
            "loo_r2": 1 - press / ss_tot if ss_tot > 0 else float("nan")}


def hard_negative(sites: list[dict], reps: dict[str, np.ndarray], recalls: dict[str, float]) -> dict[str, Any]:
    by: dict[str, list[str]] = {}
    for s in sites:
        by.setdefault(s["type"], []).append(s["name"])
    pairs = []
    for typ, names in sorted(by.items()):
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                x, y = names[a], names[b]
                d = reps[x] - reps[y]
                lo, hi = np.percentile(d, [2.5, 97.5])
                pairs.append({"type": typ, "a": x, "b": y, "diff": recalls[x] - recalls[y],
                              "ci95": [float(lo), float(hi)], "covers_0": bool(lo <= 0 <= hi)})
    return {"pairs": pairs, "n_pairs": len(pairs),
            "passes": bool(pairs) and all(p["covers_0"] for p in pairs),
            "n_differ": sum(not p["covers_0"] for p in pairs)}


# ---------------------------------------------------------------- covariates
def covariates(site: dict) -> dict[str, float]:
    import pandas as pd
    d = Path(site["dir"])
    cal = json.loads((d / "run" / "calib" / f"{site['camera']}.json").read_text())
    cx, cy, cz = cal["position_world"]
    ids = json.loads((d / "run" / "meta" / "track_ids.json").read_text())
    gt = read_mot(d / "run" / "gt" / f"mot_{site['camera']}.txt")
    w = pd.read_parquet(d / "run" / "gt" / "world.parquet")
    w["tid"] = w["uid"].map(ids)
    boxed = {(f, b[0]) for f, bs in gt.items() for b in bs}
    m = w[[(f, t) in boxed for f, t in zip(w["frame"], w["tid"])]]
    rng_m = float(np.median(np.hypot(m["x"] - cx, m["y"] - cy))) if len(m) else float("nan")
    return {"cam_height_m": float(cz), "range_m": rng_m, "density": float(site["people"]),
            "tod_ord": float(TOD[site["tod"]])}


# ---------------------------------------------------------------- run
def analyse(sites: list[dict], tables: list[dict], covs: list[dict], cfg: dict) -> dict[str, Any]:
    rng = np.random.default_rng(int(cfg["seed"]))
    nb = int(cfg["n_boot"])
    thetas = np.round(np.arange(cfg["theta_grid"][0], cfg["theta_grid"][1] + 1e-9, cfg["theta_grid"][2]), 4)
    per, reps, recs = [], {}, {}
    for s, t, c in zip(sites, tables, covs):
        r, rp = recall_boot(t["n_gt"], t["tp"], rng, nb)
        r20, rp20 = recall_boot(t["n_gt20"], t["tp20"], rng, nb)
        rv_, rpv = recall_boot(t["n_gt_vis"], t["tp_vis"], rng, nb)
        t["_wvar"] = float(np.var(rp))
        reps[s["name"]], recs[s["name"]] = rp, r
        fa_op = float(fa_per_cam_h(t["fp"][:, int(np.argmin(np.abs(thetas - cfg["op_conf"])))].sum(), len(t["n_gt"])))
        per.append({"site": s["name"], "type": s["type"], "seed": s["seed"], "tod": s["tod"], **c,
                    "n_frames": len(t["n_gt"]), "n_gt": int(t["n_gt"].sum()),
                    "recall": r, "ci95": np.percentile(rp, [2.5, 97.5]).tolist(),
                    "recall_ge20px": r20, "ci95_ge20px": np.percentile(rp20, [2.5, 97.5]).tolist(),
                    "n_gt_ge20px": int(t["n_gt20"].sum()),
                    "posthoc_recall_ge20px_vis50": rv_, "posthoc_n_gt_ge20px_vis50": int(t["n_gt_vis"].sum()),
                    "posthoc_ci95_ge20px_vis50": np.percentile(rpv, [2.5, 97.5]).tolist(), "fa_per_cam_h_at_op": fa_op})
    rv = np.array([p["recall"] for p in per])
    sd = between_sd(rv, np.array([t["_wvar"] for t in tables]))
    sd_reps = two_stage_sd(tables, rng, nb)
    lo, hi = np.percentile(sd_reps, [2.5, 97.5])
    h69a = {"between_sd_corrected": sd, "ci95": [float(lo), float(hi)], "raw_sd": float(np.std(rv, ddof=1)),
            "mean_recall": float(rv.mean()), "met": bool(sd > 0.05 and lo > 0.05)}
    h69b = split_transfer(tables, thetas, float(cfg["budget_fa_per_cam_h"]), int(cfg["n_splits"]), rng)
    h69b["budget_fa_per_cam_h"] = cfg["budget_fa_per_cam_h"]
    h69b["vacuous"] = h69b["theta_at_min_frac"] > 0.5
    h69b["met"] = None if h69b["vacuous"] else bool(h69b["within_frac"] <= cfg["x_within_frac"])
    X = np.array([[c[k] for k in COVARIATES] for c in covs])
    h69c = {"covariates": list(COVARIATES), **ols_adj_r2(X, rv)}
    h69c["met"] = bool(h69c["adj_r2"] > 0.5)
    hn = hard_negative(sites, reps, recs)
    partial = len(sites) < int(cfg["min_sites"])
    return {"n_sites": len(sites), "partial": partial, "per_site": per,
            "H69a": h69a, "H69b": h69b, "H69c": h69c, "hard_negative": hn,
            "decision": f"PARTIAL (N < {cfg['min_sites']}): directional only" if partial else
            f"H69a {'met' if h69a['met'] else 'NOT met'}; H69b "
            f"{'vacuous' if h69b['vacuous'] else ('met' if h69b['met'] else 'NOT met')}; "
            f"H69c {'met' if h69c['met'] else 'NOT met'}; hard negative {'passes' if hn['passes'] else 'FAILS'}"}


def figure(res: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"day": "#e6a817", "dusk": "#8e5ec9", "night": "#1f3b73"}
    per = sorted(res["per_site"], key=lambda p: p["recall"])
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(per) + 1.5))
    for i, p in enumerate(per):
        ax.errorbar(p["recall"], i, xerr=[[p["recall"] - p["ci95"][0]], [p["ci95"][1] - p["recall"]]],
                    fmt="o", color=col[p["tod"]], capsize=3)
    ax.set_yticks(range(len(per)), [f"{p['site']}" for p in per], fontsize=8)
    ax.axvline(res["H69a"]["mean_recall"], color="grey", ls="--", lw=1)
    for k, c in col.items():
        ax.plot([], [], "o", color=c, label=k)
    ax.legend(title="time of day", fontsize=8, loc="lower right")
    a = res["H69a"]
    ax.set_xlabel("recall @ conf 0.25, IoU 0.5 (YOLO11n imgsz 1280), 95 % frame-bootstrap CI")
    ax.set_title(f"H69: per-site recall, N = {res['n_sites']}; between-site SD (corrected) "
                 f"{a['between_sd_corrected']:.3f} [{a['ci95'][0]:.3f}, {a['ci95'][1]:.3f}]", fontsize=9)
    ax.set_xlim(0, 1)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    sites, excluded = scan_sites(Path(cfg["sites_root"]))
    cache = out / "detections"
    thetas = np.round(np.arange(cfg["theta_grid"][0], cfg["theta_grid"][1] + 1e-9, cfg["theta_grid"][2]), 4)
    tables, covs = [], []
    for s in sites:
        dets = detect_site(s, cache, cfg)
        gt = read_mot(Path(s["dir"]) / "run" / "gt" / f"mot_{s['camera']}.txt")
        gt = {f - int(cfg["frame_offset"]): v for f, v in gt.items()}
        tables.append(frame_table(gt, dets, thetas, float(cfg["op_conf"])))
        covs.append(covariates(s))
    res = analyse(sites, tables, covs, cfg)
    res["excluded"] = excluded
    out.mkdir(parents=True, exist_ok=True)
    figure(res, Path(cfg["figure"]))
    return res


def markdown_rows(res: dict, cfg: dict) -> str:
    rows = ["| site | tod | h (m) | range (m) | people | GT | recall [95 % CI] | recall ≥ 20 px | FA/cam-h @0.25 |",
            "|---|---|---|---|---|---|---|---|---|"]
    for p in res["per_site"]:
        rows.append(f"| {p['site']} | {p['tod']} | {p['cam_height_m']:.1f} | {p['range_m']:.1f} | {p['density']:.0f} | "
                    f"{p['n_gt']} | {p['recall']:.3f} [{p['ci95'][0]:.3f}, {p['ci95'][1]:.3f}] | "
                    f"{p['recall_ge20px']:.3f} | {p['fa_per_cam_h_at_op']:.0f} |")
    return "\n".join(rows) + f"\n\ndecision: {res['decision']}\n"
