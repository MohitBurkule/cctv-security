"""H25: label-noise injection on the synthetic part of the h14b-style mix
(60 real MOT20-01 x5 + 100 batch_v8 frames). Runs the `detection` arms, then
per noise cell the dose gain over real-only (paired by seed) and the gain
retained relative to the clean cell."""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import numpy as np

from . import detection


def cell_name(sigma: float, drop: float) -> str:
    return f"j{round(sigma * 100):02d}_d{round(drop * 100):02d}"


def analyse(res: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    key, seeds = cfg["primary_key"], cfg["seeds"]
    ap = {n: r["eval"][key]["AP"] for n, r in res["arms"].items() if key in r.get("eval", {})}
    base = np.array([ap[f"real_only_s{s}"] for s in seeds])
    clean = np.array([ap[f"{cell_name(0, 0)}_s{s}"] for s in seeds])
    g0 = clean - base
    rng = np.random.default_rng(25)
    bi = rng.integers(0, len(seeds), (10000, len(seeds)))

    def ci(x):
        b = x[bi].mean(1)
        return [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]

    cells = {}
    for sg in cfg["jitter_sigmas"]:
        for dr in cfg["drops"]:
            c = cell_name(sg, dr)
            v = np.array([ap[f"{c}_s{s}"] for s in seeds])
            g = v - base
            cells[c] = {"sigma": sg, "drop": dr, "AP": v.round(4).tolist(), "AP_mean": round(float(v.mean()), 4),
                        "gain": round(float(g.mean()), 4), "gain_boot95": ci(g),
                        "minus_clean": round(float((v - clean).mean()), 4), "minus_clean_boot95": ci(v - clean),
                        "retained": round(float(g.mean() / g0.mean()), 3) if g0.mean() != 0 else None}
    g0_ci = ci(g0)
    testable = g0_ci[0] > 0 and g0.mean() >= cfg["min_clean_gain"]
    out = {"real_only_AP": base.round(4).tolist(), "clean_gain": round(float(g0.mean()), 4),
           "clean_gain_boot95": g0_ci, "cells": cells, "testable": bool(testable)}
    if testable:
        r = {sg: cells[cell_name(sg, 0)]["retained"] for sg in cfg["jitter_sigmas"]}
        means = [cells[cell_name(sg, 0)]["AP_mean"] for sg in cfg["jitter_sigmas"]]
        mono = all(a >= b for a, b in itertools.pairwise(means))
        ok = all(r[sg] >= 0.5 for sg in cfg["jitter_sigmas"] if 0 < sg < 0.10) and r[0.10] < 0.5 and mono
        out["branch"] = "supported" if ok else "refuted"
        out["monotone_in_sigma"] = mono
    else:
        out["branch"] = "untestable: no clean dose gain to erode"
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    body = detection.run(cfg, out, None)
    body["analysis"] = analyse(body, cfg)
    return body


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    a = res["analysis"]
    L = [(f"real-only AP {a['real_only_AP']}; clean gain {a['clean_gain']:+.4f} {a['clean_gain_boot95']}; "
          f"branch: {a['branch']}"), "",
         "| cell | AP mean | gain vs real-only [95 %] | vs clean cell [95 %] | retained |", "|---|---|---|---|---|"]
    for c, v in a["cells"].items():
        L.append(f"| {c} | {v['AP_mean']:.4f} | {v['gain']:+.4f} {v['gain_boot95']} | "
                 f"{v['minus_clean']:+.4f} {v['minus_clean_boot95']} | {v['retained']} |")
    return "\n".join(L) + "\n"
