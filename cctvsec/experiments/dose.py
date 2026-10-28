"""H14: tiny synthetic dose, replicated. Runs the `detection` arms, then the
pre-registered contrasts: each dose vs real-only (unpaired exact permutation
p, bootstrap CI, Holm over the two primary contrasts) and tight vs loose GT at
the same dose (paired by seed: same subset indices, same pixels on
street_crowd_day)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import detection
from .inference import bootstrap_mean_diff, permutation_p


def _ap(res, arm, key):
    return res["arms"][arm]["eval"][key]["AP"]


def contrasts(res: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    key, seeds = cfg["primary_key"], cfg["seeds"]
    out: dict[str, Any] = {"primary": [], "secondary": []}
    have = res["arms"]

    def arm_vals(prefix):
        return [_ap(res, f"{prefix}_s{s}", key) for s in seeds if f"{prefix}_s{s}" in have]

    for a, b in cfg["primary_contrasts"]:
        va, vb = arm_vals(a), arm_vals(b)
        if len(va) < 2 or len(vb) < 2:
            continue
        lo, hi = bootstrap_mean_diff(va, vb, seed=0)
        out["primary"].append({"contrast": f"{b} - {a}", "a": va, "b": vb,
                               "mean_a": round(float(np.mean(va)), 4), "mean_b": round(float(np.mean(vb)), 4),
                               "sd_a": round(float(np.std(va, ddof=1)), 4), "sd_b": round(float(np.std(vb, ddof=1)), 4),
                               "diff": round(float(np.mean(vb) - np.mean(va)), 4),
                               "boot95": [round(lo, 4), round(hi, 4)], "perm_p": round(permutation_p(va, vb), 4)})
    # Holm over the primary family
    ps = sorted(range(len(out["primary"])), key=lambda i: out["primary"][i]["perm_p"])
    m, stop = len(ps), False
    for rank, i in enumerate(ps):
        thr = 0.05 / (m - rank)
        rej = (not stop) and out["primary"][i]["perm_p"] <= thr
        stop = stop or not rej
        out["primary"][i]["holm_reject_at_0.05"] = bool(rej)
    for a, b in cfg["secondary_contrasts"]:
        pairs = [(_ap(res, f"{a}_s{s}", key), _ap(res, f"{b}_s{s}", key)) for s in seeds
                 if f"{a}_s{s}" in have and f"{b}_s{s}" in have]
        if len(pairs) < 2:
            continue
        d = np.array([y - x for x, y in pairs])
        rng = np.random.default_rng(0)
        bs = d[rng.integers(0, len(d), (10000, len(d)))].mean(1)
        signs = np.array(np.meshgrid(*[[1, -1]] * len(d))).reshape(len(d), -1).T
        flip = np.abs((signs * d).mean(1))
        out["secondary"].append({"contrast": f"{b} - {a} (paired by seed)", "diffs": [round(x, 4) for x in d],
                                 "mean_diff": round(float(d.mean()), 4),
                                 "boot95": [round(float(np.percentile(bs, 2.5)), 4),
                                            round(float(np.percentile(bs, 97.5)), 4)],
                                 "signflip_p": round(float((flip >= abs(d.mean()) - 1e-12).mean()), 4),
                                 "also_unpaired_perm_p": round(permutation_p([x for x, _ in pairs],
                                                                             [y for _, y in pairs]), 4)})
    return out


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    body = detection.run(cfg, out, None)
    body["contrasts"] = contrasts(body, cfg)
    return body


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [detection.markdown_rows(res, cfg), "", "| contrast | mean a | mean b | diff | 95 % bootstrap | p | Holm |",
         "|---|---|---|---|---|---|---|"]
    for c in res["contrasts"]["primary"]:
        L.append(f"| {c['contrast']} | {c['mean_a']:.4f} ({c['sd_a']:.4f}) | {c['mean_b']:.4f} ({c['sd_b']:.4f}) | "
                 f"{c['diff']:+.4f} | [{c['boot95'][0]:+.4f}, {c['boot95'][1]:+.4f}] | {c['perm_p']} | "
                 f"{'reject' if c['holm_reject_at_0.05'] else 'keep'} |")
    for c in res["contrasts"]["secondary"]:
        L.append(f"| {c['contrast']} | | | {c['mean_diff']:+.4f} | [{c['boot95'][0]:+.4f}, {c['boot95'][1]:+.4f}] | "
                 f"sign-flip {c['signflip_p']} | secondary |")
    return "\n".join(L) + "\n"
