"""H3c: H3's exact tiling arm (320x240, 2.0x) vs a 1.5x arm vs full_1280 on CC0 batch_v8.

Reuses the H3b loop (`far_field_cc0.run`) with full_1280 as the base arm; adds the
principle-5 primary outcome (recall on >= 20 px rows, 30-frame block bootstrap),
near-camera AP50 per arm and the pre-registered decision (docs/research/32 §H3c)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import far_field_cc0 as base
from .common import ap50_by_height

BASE, H3ARM, ARM15 = "full_1280", "tiles_2p0x_320x240", "tiles_1p5x_427x320"


def collapse(counts: dict, split: int) -> dict:
    """Per-frame counts over bands -> [bins below split, bins at/after split] (2 bands)."""
    return {a: {k: {"hit": [sum(c["hit"][:split]), sum(c["hit"][split:])],
                    "n": [sum(c["n"][:split]), sum(c["n"][split:])], "tp": c["tp"], "fp": c["fp"]}
                for k, c in ck.items()} for a, ck in counts.items()}


def native_scale(tile_w: int, tile_imgsz: int = 640) -> float:
    return tile_imgsz / tile_w


def make_post(cfg: dict[str, Any]):
    split = next(i for i, b in enumerate(cfg["bands"]) if b[0] >= cfg["primary_min_px"])

    def post(res, counts, items, G, I, preds):
        cc = collapse(counts, split)
        for g in cfg["groups"]:
            ks = [k for k, gg, *_ in items if gg == g]
            bb = base.block_bootstrap({a: {k: cc[a][k] for k in ks} for a in cc},
                                      base.make_blocks(ks, cfg["block"]), cfg["n_boot"], cfg["seed"], 2)
            res[g]["primary_ge20"] = {"recall": {a: v[1] for a, v in bb["recall"].items()},
                                      "delta_vs_full_1280": {a: v[1] for a, v in bb["delta_vs_full_640"].items()},
                                      "n": bb["n"][1]}
            res[g]["delta_vs_full_1280"] = res[g].pop("delta_vs_full_640")
            res[g]["ap50_all"] = {a: ap50_by_height(ks, {k: G[k] for k in ks}, {k: I[k] for k in ks},
                                                    {k: preds[a][k] for k in ks},
                                                    [tuple(b) for b in cfg["bands"]])["all"]
                                  for a in preds}
    return post


def _ap(v):
    return v.get("AP50") if isinstance(v, dict) else v


def decide_h3c(res: dict[str, Any], lat: dict[str, float], margin: float = 0.05,
               hn_drop: float = 0.05) -> dict[str, Any]:
    far, near = res["far"]["primary_ge20"], res["near"]
    d = far["delta_vs_full_1280"][H3ARM]
    D = {"D_h3arm_beats_1280_ge20": bool(d[0] >= margin and d[1] > 0),
         "D_h3arm_delta": d, "D_1p5x_delta": far["delta_vs_full_1280"][ARM15]}
    ap = {a: _ap(v) for a, v in near["ap50_all"].items()}
    D["near_ap50"] = ap
    D["HN_near_ap50_drop_ok"] = {a: bool(ap[BASE] - ap[a] <= hn_drop) for a in (H3ARM, ARM15)}
    D["decision_met"] = D["D_h3arm_beats_1280_ge20"]
    D["latency_ms_shared_gpu_unstable"] = lat
    return D


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    assert cfg["methods"][0]["name"] == BASE
    return base.run(cfg, out, post_fn=make_post(cfg),
                    decide_fn=lambda r, lat: decide_h3c(r, lat, cfg["decision_margin"], cfg["hn_max_ap50_drop"]))


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [f"CC0 batch_v8, {res['n_frames']} frames; recall [95% 30-frame block CI]", "",
         "| arm | far >=20 px | far d vs 1280 | far all | near AP50 | ms/frame (shared GPU, unstable) |",
         "|---|---|---|---|---|---|"]
    f = res["far"]
    for a in f["recall"]:
        p = f["primary_ge20"]["recall"][a]
        dd = f["primary_ge20"]["delta_vs_full_1280"].get(a)
        L.append(f"| {a} | {p[0]:.3f} [{p[1]:.3f}, {p[2]:.3f}] | "
                 + ("-" if dd is None else f"{dd[0]:+.3f} [{dd[1]:+.3f}, {dd[2]:+.3f}]")
                 + f" | {f['recall'][a][-1][0]:.3f} | {_ap(res['near']['ap50_all'][a]):.3f} | "
                 f"{res['latency_ms_per_frame'][a]} |")
    return "\n".join(L + ["", f"decision: {res['decision']}"]) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    arms = list(res["far"]["recall"])
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    p = np.array([res["far"]["primary_ge20"]["recall"][a] for a in arms])
    axs[0].bar(range(len(arms)), p[:, 0], yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], capsize=3,
               color=["#888", "#3a7", "#37a"])
    axs[0].axhline(0.629, ls=":", color="grey")
    axs[0].text(-0.4, 0.635, "H3 MetaHuman 320x240 (all rows, eng-only) 0.629", fontsize=7, color="grey")
    axs[0].set_xticks(range(len(arms)), [a.replace("_", "\n", 1) for a in arms], fontsize=8)
    axs[0].set_title(f"far cams, recall on >=20 px GT (n={res['far']['primary_ge20']['n']})")
    axs[0].set_ylim(0, 1)
    ap = [_ap(res["near"]["ap50_all"][a]) for a in arms]
    axs[1].bar(range(len(arms)), ap, color=["#888", "#3a7", "#37a"])
    axs[1].set_xticks(range(len(arms)), [a.replace("_", "\n", 1) for a in arms], fontsize=8)
    axs[1].set_title("near cam AP50 (hard negative: drop <= 0.05)")
    axs[1].set_ylim(0, 1)
    fig.suptitle("H3c tiling arms on CC0 batch_v8 (YOLOv8n zero-shot); 95% 30-frame block CI")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
