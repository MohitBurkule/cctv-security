"""H17: does the small-dose detection gain carry to tracking?

Runs each listed detector (weights on disk, no training) through the H9
harness on MOT20-02 (docs/13 subset), default numpy ByteTrack, and scores
corrected HOTA / MOTA / IDF1. Contrasts are paired by training seed
(`<b>_s<k>` - `<a>_s<k>`): percentile bootstrap CI of the mean difference and
exact two-sided sign-flip p."""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import numpy as np

from .common import wait_for_gpu
from .tracking import detect_paths, mot20_sequences, score

METRICS = ("hota", "deta", "assa", "mota", "idf1", "id_switches")


def paired(a: list[float], b: list[float], n: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Mean of b - a over paired units; bootstrap CI and exact sign-flip p."""
    d = np.asarray(b, float) - np.asarray(a, float)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    flips = np.array(list(itertools.product([1, -1], repeat=len(d))))
    p = float((np.abs((flips * d).mean(1)) >= abs(d.mean()) - 1e-12).mean())
    return {"diffs": [round(float(x), 4) for x in d], "mean_diff": round(float(d.mean()), 4),
            "boot95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "signflip_p": round(p, 4), "n": len(d)}


def contrasts(res: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for a, b in cfg["contrasts"]:
        seeds = [s for s in cfg["seeds"] if f"{a}_s{s}" in res["arms"] and f"{b}_s{s}" in res["arms"]]
        if len(seeds) < 2:
            continue
        row = {"contrast": f"{b} - {a}", "seeds": seeds}
        for m in METRICS:
            row[m] = paired([res["arms"][f"{a}_s{s}"][m] for s in seeds],
                            [res["arms"][f"{b}_s{s}"][m] for s in seeds])
        out.append(row)
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    gpu = wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=900)
    seqs = [s for s in mot20_sequences(cfg) if s["run"] in cfg["sequences"]]
    res: dict[str, Any] = {"gpu_wait": gpu, "arms": {}}
    for arm in cfg["arms"]:
        for s in seqs:
            dets = detect_paths(arm["weights"], s["paths"],
                                out / "dets" / arm["name"] / (s["key"].replace("/", "__") + ".json"),
                                cfg["imgsz"], cfg["det_conf"])
            m = score(s, dets, cfg.get("tracker", {}))["metrics"]
            res["arms"][arm["name"]] = {"weights": arm["weights"], "sequence": s["key"],
                                        "n_frames": len(s["frames"]), "n_gt": len(s["gt"]),
                                        **{k: m[k] for k in METRICS}}
    res["contrasts"] = contrasts(res, cfg)
    return res


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = ["| arm | HOTA | DetA | AssA | MOTA | IDF1 | IDsw |", "|---|---|---|---|---|---|---|"]
    for k, v in res["arms"].items():
        L.append(f"| {k} | {v['hota']:.4f} | {v['deta']:.4f} | {v['assa']:.4f} | {v['mota']:.4f} | "
                 f"{v['idf1']:.4f} | {v['id_switches']} |")
    L += ["", "| contrast (paired by seed) | metric | mean diff | 95 % bootstrap | sign-flip p |",
          "|---|---|---|---|---|"]
    for c in res["contrasts"]:
        for m in METRICS:
            x = c[m]
            L.append(f"| {c['contrast']} | {m} | {x['mean_diff']:+.4f} | "
                     f"[{x['boot95'][0]:+.4f}, {x['boot95'][1]:+.4f}] | {x['signflip_p']} |")
    return "\n".join(L) + "\n"
