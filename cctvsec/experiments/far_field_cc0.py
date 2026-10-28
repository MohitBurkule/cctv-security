"""H3b: H3 far-field replication on the CC0 batch_v8 set (customer-safe licence).

Reuses H3's detector path (`farfield.predict`, `farfield.tiles`) and scoring
(`common.recall_by_height`, `common.ap50_by_height`); adds per-frame counts so
recall per height bin gets a frame-block bootstrap CI, a near-camera hard
negative and the pre-registered decision (docs/research/32 §H3b)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .common import ap50_by_height, band_name, batch_cameras, recall_by_height, rpath, write_json


def check_licence(batch: Path, runs: list[str]) -> dict[str, bool]:
    ok = {}
    for r in runs:
        p = Path(batch) / r / "licences.json"
        ok[r] = bool(p.is_file() and json.loads(p.read_text()).get("commercial_ml_ok") is True)
    return ok


def frame_counts(G: dict, I: dict, preds: dict, bands, conf: float, thr: float) -> dict:
    """key -> {"hit": [per band], "n": [per band], "tp", "fp"} (one frame each)."""
    out = {}
    for k, gk in G.items():
        r = recall_by_height({k: gk}, {k: preds.get(k, [])}, conf=conf, thr=thr, bands=bands,
                             ignore_by_key={k: I.get(k, [])})
        rb = r["recall_by_height"]
        n = [rb[band_name(*b)]["n"] for b in bands]
        hit = [round((rb[band_name(*b)]["recall"] or 0) * rb[band_name(*b)]["n"]) for b in bands]
        out[k] = {"hit": hit, "n": n, "tp": r["tp"], "fp": r["fp"]}
    return out


def make_blocks(keys: list, block: int) -> list[list]:
    """Group keys (stream, frame) into runs of `block` consecutive sampled frames per stream."""
    by: dict = {}
    for k in sorted(keys):
        by.setdefault(k[0], []).append(k)
    return [ks[i:i + block] for ks in by.values() for i in range(0, len(ks), block)]


def block_bootstrap(counts: dict[str, dict], blocks: list[list], n_boot: int, seed: int,
                    nb: int) -> dict[str, Any]:
    """Paired block bootstrap of recall per band (+ 'all') for each arm and arm-minus-full_640 Δs.

    counts: arm -> key -> frame counts. Returns arm -> {band_idx|'all': (pt, lo, hi)} and deltas."""
    arms = list(counts)
    # block-level sums: arm -> (n_blocks, nb) hits, (n_blocks, nb) n
    H = {a: np.array([[sum(counts[a][k]["hit"][j] for k in b) for j in range(nb)] for b in blocks], float)
         for a in arms}
    N = np.array([[sum(counts[arms[0]][k]["n"][j] for k in b) for j in range(nb)] for b in blocks], float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(blocks), size=(n_boot, len(blocks)))

    def rec(h, n):
        with np.errstate(invalid="ignore", divide="ignore"):
            per = h / n
            allr = h.sum(-1) / n.sum(-1)
        return np.concatenate([per, allr[..., None]], -1)

    def ci(pt, bs):
        lo, hi = np.nanpercentile(bs, [2.5, 97.5], axis=0) if len(bs) else (pt, pt)
        return [[None if np.isnan(p) else round(float(p), 4), None if np.isnan(p) else round(float(a), 4),
                 None if np.isnan(p) else round(float(c), 4)] for p, a, c in zip(pt, lo, hi)]

    Nb = N[idx].sum(1)
    out: dict[str, Any] = {"recall": {}, "delta_vs_full_640": {}}
    boots = {}
    for a in arms:
        pt = rec(H[a].sum(0), N.sum(0))
        boots[a] = rec(H[a][idx].sum(1), Nb)
        out["recall"][a] = ci(pt, boots[a])
    base = arms[0]
    for a in arms[1:]:
        pt = rec(H[a].sum(0), N.sum(0)) - rec(H[base].sum(0), N.sum(0))
        out["delta_vs_full_640"][a] = ci(pt, boots[a] - boots[base])
    out["n"] = [int(x) for x in N.sum(0)] + [int(N.sum())]
    return out


def decide(res: dict[str, Any], lat: dict[str, float]) -> dict[str, Any]:
    """Pre-registered decision (docs/32 §H3b). Index -1 = 'all' bins; index 0 = < 20 px bin."""
    far, near = res["far"], res["near"]
    d1 = far["recall"]["full_640"][0][0] is not None and far["recall"]["full_640"][0][0] < 0.5
    d2 = far["delta_vs_full_640"]["full_1280"][-1]
    d3 = far["delta_vs_full_640"]["tiled_2x2"][-1]
    hn = near["delta_vs_full_640"]["tiled_2x2"][-1]
    D = {"D1_640_blind_lt20": bool(d1),
         "D2_1280_recovers": bool(d2[0] >= 0.15 and d2[1] > 0),
         "D3_tiled_recovers": bool(d3[0] >= 0.15 and d3[1] > 0),
         "D4_tiled_cost_2x": bool(lat["tiled_2x2"] >= 2 * lat["full_640"]),
         "HN_near_tiling_no_gain": bool(hn[1] <= 0)}
    D["decision_met"] = all(D[k] for k in ("D1_640_blind_lt20", "D2_1280_recovers",
                                           "D3_tiled_recovers", "D4_tiled_cost_2x"))
    D["h3_conclusion_holds_on_cc0"] = D["D1_640_blind_lt20"] and D["D2_1280_recovers"] and D["D3_tiled_recovers"]
    return D


def run(cfg: dict[str, Any], out: Path, decide_fn=None, post_fn=None) -> dict[str, Any]:
    """decide_fn(res, lat) / post_fn(res, counts, items, G, I, preds_by_arm) are H3c hooks."""
    import cv2
    import torch
    from ultralytics import YOLO

    from .farfield import predict

    batch = rpath(cfg["batch_dir"])
    runs = sorted({r for s in cfg["sources"] for r in s["runs"]})
    lic = check_licence(batch, runs)
    if cfg.get("require_commercial_ml_ok", True) and not all(lic.values()):
        raise RuntimeError(f"licence check failed: {lic}")
    bands = [tuple(b) for b in cfg["bands"]]
    min_h = cfg["min_gt_height"]
    cam_group = {c: g for g, cams in cfg["groups"].items() for c in cams}
    items = []  # (key=(stream, f), group, png, targets, ignore)
    for src in cfg["sources"]:
        for run_name in src["runs"]:
            for cam, c in batch_cameras(batch, run_name, src["source"]).items():
                if cam not in cam_group:
                    continue
                fs = [f for f in sorted(c["frames"]) if f >= 1 and f % cfg["stride"] == 0]
                if cfg.get("max_frames_per_stream"):
                    fs = fs[:cfg["max_frames_per_stream"]]
                for f in fs:
                    rows = c["gt"].get(f, [])
                    items.append(((f"{run_name}/{src['source']}/{cam}", f), cam_group[cam], c["frames"][f],
                                  [r for r in rows if r["bbox"][3] >= min_h],
                                  [r for r in rows if r["bbox"][3] < min_h]))
    model = YOLO(str(rpath(cfg["model"])))
    G = {k: tg for k, _, _, tg, _ in items}
    I = {k: ig for k, _, _, _, ig in items}
    res: dict[str, Any] = {"licence_commercial_ml_ok": lic, "n_frames": len(items),
                           "partial": bool(cfg.get("max_frames_per_stream")),
                           "latency_note": "desktop only: RTX 2070 Max-Q shared with the Unreal editor",
                           "methods": {}}
    counts: dict[str, dict] = {}
    all_preds: dict[str, dict] = {}
    lat = {}
    for meth in cfg["methods"]:
        preds = {}
        predict(model, cv2.imread(str(items[0][2])), meth, cfg["det_conf"])  # warm-up
        t = 0.0
        for k, _, png, _, _ in items:
            img = cv2.imread(str(png))
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            preds[k] = predict(model, img, meth, cfg["det_conf"])
            torch.cuda.synchronize()
            t += time.perf_counter() - t0
        lat[meth["name"]] = round(1000 * t / len(items), 1)
        all_preds[meth["name"]] = preds
        counts[meth["name"]] = frame_counts(G, I, preds, bands, cfg["op_conf"], cfg["iou"])
        r = {"ms_per_frame": lat[meth["name"]]}
        for g in cfg["groups"]:
            ks = [k for k, gg, *_ in items if gg == g]
            r[g] = {"ap_by_height": ap50_by_height(ks, {k: G[k] for k in ks}, {k: I[k] for k in ks},
                                                   {k: preds[k] for k in ks}, bands),
                    "op": recall_by_height({k: G[k] for k in ks}, {k: preds[k] for k in ks},
                                           conf=cfg["op_conf"], thr=cfg["iou"], bands=bands,
                                           ignore_by_key={k: I[k] for k in ks})}
            if g == "far":
                r[g]["per_source"] = {}
                for s in sorted({k[0].rsplit("/", 1)[0] for k in ks}):
                    sk = [k for k in ks if k[0].startswith(s + "/")]
                    r[g]["per_source"][s] = recall_by_height(
                        {k: G[k] for k in sk}, {k: preds[k] for k in sk}, conf=cfg["op_conf"],
                        thr=cfg["iou"], bands=bands, ignore_by_key={k: I[k] for k in sk})["recall"]
        res["methods"][meth["name"]] = r
        write_json(out / "partial.json", res)
    res["bands"] = [band_name(*b) for b in bands] + ["all"]
    for g in cfg["groups"]:
        ks = [k for k, gg, *_ in items if gg == g]
        res[g] = block_bootstrap({a: {k: counts[a][k] for k in ks} for a in counts},
                                 make_blocks(ks, cfg["block"]), cfg["n_boot"], cfg["seed"], len(bands))
    res["latency_ms_per_frame"] = lat
    if post_fn:
        post_fn(res, counts, items, G, I, all_preds)
    res["decision"] = (decide_fn or decide)(res, lat)
    res["h3_reference_metahuman_engineering_only"] = cfg.get("h3_reference", {})
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    bn = res["bands"]
    lines = [f"CC0 (batch_v8, customer-safe), {res['n_frames']} frames; recall [95% block-bootstrap CI]", ""]
    for g in cfg["groups"]:
        lines += [f"**{g}** (n per bin {res[g]['n']})", "",
                  "| arm | " + " | ".join(bn) + " | ms/frame |", "|---|" + "---|" * (len(bn) + 1)]
        for a, cells in res[g]["recall"].items():
            lines.append(f"| {a} | " + " | ".join("-" if c[0] is None else f"{c[0]:.3f} [{c[1]:.3f}, {c[2]:.3f}]"
                                                  for c in cells) + f" | {res['latency_ms_per_frame'][a]} |")
        lines.append("")
    lines.append(f"decision: {res['decision']}")
    return "\n".join(lines) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bn = res["bands"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, g in zip(axs, ("far", "near")):
        arms = list(res[g]["recall"])
        w = 0.8 / len(arms)
        for i, a in enumerate(arms):
            c = res[g]["recall"][a]
            xs = [j for j, v in enumerate(c) if v[0] is not None]
            pts = np.array([c[j][0] for j in xs])
            err = np.array([[c[j][0] - c[j][1], c[j][2] - c[j][0]] for j in xs]).T
            ax.bar(np.array(xs) + (i - 1) * w, pts, w, yerr=err, capsize=2,
                   label=f"{a} ({res['latency_ms_per_frame'][a]} ms, desktop)")
        ax.set_xticks(range(len(bn)), [f"{b}\n(n={n})" for b, n in zip(bn, res[g]["n"])])
        ax.set_title(f"{g} camera{'s' if g == 'far' else ''}")
        ax.set_xlabel("GT height (px)")
    ref = res.get("h3_reference_metahuman_engineering_only", {})
    for k, v in ref.items():
        if k in ("full_640", "full_1280"):
            axs[0].axhline(v, ls=":", lw=1, color="grey")
            axs[0].text(len(bn) - 1.4, v + 0.01, f"H3 MetaHuman {k} {v}", fontsize=7, color="grey")
    axs[0].set_ylabel("recall @ conf 0.25, IoU 0.5")
    axs[0].legend(fontsize=7)
    fig.suptitle("H3b far-field recall on CC0 batch_v8 (customer-safe); 95% frame-block bootstrap CI")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
