"""H26: dose curve with the step count held fixed. Arms `dose{N}_s{k}` train on
60 real MOT20-01 x5 + N batch_v8 frames; each arm's epochs (and a pad of seeded
duplicates) are set so image-list length x epochs is the same for every arm,
i.e. the same optimiser steps. Contrasts are `dose.contrasts` (each dose vs 0,
unpaired exact permutation, bootstrap CI, Holm)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import detection, dose


def schedule(n_images: int, presentations: int, warmup_iters: int, batch: int) -> dict[str, Any]:
    """Epochs E = floor(P / n), padded list L = P / E (>= n), warm-up in epochs.
    L * E == P exactly iff P is divisible by E (asserted)."""
    e = max(presentations // n_images, 1)
    assert presentations % e == 0, (n_images, presentations)
    L = presentations // e
    return {"epochs": e, "list_len": L, "pad": L - n_images, "steps": e * L // batch,
            "warmup_epochs": round(warmup_iters * batch / L, 6)}


SYNTHETIC_MODES = ("true", "shuffled_labels", "masked", "silhouette")


def shuffle_labels(items, seed: int):
    """H52 (b): each synthetic image keeps its pixels but receives another image's
    boxes (a seeded derangement, so no image keeps its own labels). Boxes are
    rescaled between image sizes (raw 1920x1080 vs degraded 1280x720)."""
    n = len(items)
    if n < 2:
        return list(items)
    rng = np.random.default_rng([seed, 52])
    while True:
        perm = rng.permutation(n)
        if not (perm == np.arange(n)).any():
            break
    out = []
    for i, (name, png, _, src, wh) in enumerate(items):
        _, _, rows, _, swh = items[perm[i]]
        sx, sy = wh[0] / swh[0], wh[1] / swh[1]
        out.append((name, png, [{**r, "bbox": [r["bbox"][0] * sx, r["bbox"][1] * sy,
                                               r["bbox"][2] * sx, r["bbox"][3] * sy]} for r in rows], src, wh))
    return out


def mask_people(img: np.ndarray, rows, pad: float = 0.1, scale: int = 4) -> np.ndarray:
    """H52 (c): remove every labelled person. Each GT box (grown by `pad` of its
    size per side) is filled by Telea inpainting computed at 1/`scale` resolution
    and upsampled, so only background texture remains. Pixels outside boxes are
    untouched."""
    import cv2
    h, w = img.shape[:2]
    m = np.zeros((h, w), np.uint8)
    for r in rows:
        x, y, bw, bh = r["bbox"]
        x0, y0 = int(max(x - pad * bw, 0)), int(max(y - pad * bh, 0))
        x1, y1 = int(min(x + bw * (1 + pad), w)), int(min(y + bh * (1 + pad), h))
        m[y0:y1, x0:x1] = 255
    if not m.any():
        return img.copy()
    sw, sh = max(w // scale, 1), max(h // scale, 1)
    small = cv2.inpaint(cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA),
                        (cv2.resize(m, (sw, sh), interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8) * 255,
                        5, cv2.INPAINT_TELEA)
    big = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    out = img.copy()
    out[m > 0] = big[m > 0]
    return out


def _parse_item_name(name: str) -> tuple[str, str, str, int] | None:
    """Inverse of `f"{run}_{source}_{cam}_{f:04d}"` from `_synth_candidates`.
    `source` is `raw` or `degraded`; `cam` starts with `cam_`. Returns
    (run, source, cam, frame) or None if the name doesn't parse."""
    parts = name.rsplit("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    head, frame = parts[0], int(parts[1])
    for src in ("raw", "degraded"):
        marker = f"_{src}_cam_"
        i = head.find(marker)
        if i == -1:
            continue
        return head[:i], src, head[i + 1 + len(src) + 1:], frame
    return None


def mask_people_silhouette(img: np.ndarray, mask_path: Path) -> np.ndarray:
    """H61 (c'): remove every person by their *rendered silhouette mask* (no
    inpainting, no box shape). Masked pixels are set to the per-channel median
    of the frame's remaining background pixels -- a flat fill, not a learnable
    box-shaped patch. `mask_path` is the raw-resolution ID-mask PNG for this
    frame; it is resized to `img`'s size with nearest-neighbour (label-like,
    not interpolated)."""
    import cv2

    from survsim.gt.mask_boxes import decode_ids

    h, w = img.shape[:2]
    mimg = cv2.imread(str(mask_path), cv2.IMREAD_COLOR)
    if mimg is None:
        return img.copy()
    ids = decode_ids(cv2.cvtColor(mimg, cv2.COLOR_BGR2RGB))
    fg = (ids != 0).astype(np.uint8)
    if fg.shape[:2] != (h, w):
        fg = cv2.resize(fg, (w, h), interpolation=cv2.INTER_NEAREST)
    m = fg > 0
    out = img.copy()
    if not m.any():
        return out
    bg = ~m
    fill = (np.median(img[bg], axis=0) if bg.any() else np.median(img.reshape(-1, 3), axis=0))
    out[m] = fill.astype(img.dtype)
    return out


def apply_synthetic_mode(items, mode: str, seed: int, cache: Path, batch: Path | None = None):
    """H52/H61: transform the selected synthetic items. `true` is a no-op
    (H26/H51); `shuffled_labels` deranges labels across images; `masked`
    writes Telea-inpainted, box-shaped person-free copies under `cache`
    (H52 (c)); `silhouette` writes flat-median-fill, silhouette-shaped
    person-free copies (H61 (c'), no inpainting, no box). Both mask modes
    give the transformed images no boxes."""
    if mode == "true":
        return list(items)
    if mode == "shuffled_labels":
        return shuffle_labels(items, seed)
    if mode not in ("masked", "silhouette"):
        raise ValueError(f"unknown synthetic_mode {mode!r}; expected one of {SYNTHETIC_MODES}")
    import cv2
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for name, png, rows, src, wh in items:
        dst = cache / f"{name}.png"
        if not dst.is_file():
            img = cv2.imread(str(png), cv2.IMREAD_COLOR)
            if mode == "masked":
                new = mask_people(img, rows)
            else:
                parsed = _parse_item_name(name)
                if parsed is None or batch is None:
                    raise ValueError(f"silhouette mode: cannot locate mask for item {name!r}")
                run, _src, cam, f = parsed
                mask_path = Path(batch) / run / "mask" / cam / f"{f:04d}.png"
                new = mask_people_silhouette(img, mask_path)
            cv2.imwrite(str(dst), new)
        out.append((name, dst, [], src, wh))
    return out


def paired_contrasts(res: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """H51: each primary contrast paired by seed. Per-seed differences b - a for
    AP/AP50/AP75; exact two-sided sign-flip p (all 2^n sign patterns) and a
    seed-resampling bootstrap CI of the mean difference; Holm over the family
    on the AP sign-flip p. Only seeds present in both arms are used."""
    key, arms = cfg["primary_key"], res["arms"]
    out = []
    for a, b in cfg["primary_contrasts"]:
        seeds = [s for s in cfg["seeds"] if f"{a}_s{s}" in arms and f"{b}_s{s}" in arms]
        if len(seeds) < 2:
            continue
        row: dict[str, Any] = {"contrast": f"{b} - {a} (paired by seed)", "seeds": seeds}
        for m in ("AP", "AP50", "AP75"):
            d = np.array([arms[f"{b}_s{s}"]["eval"][key][m] - arms[f"{a}_s{s}"]["eval"][key][m] for s in seeds])
            rng = np.random.default_rng(51)
            bs = d[rng.integers(0, len(d), (10000, len(d)))].mean(1)
            signs = np.array(np.meshgrid(*[[1, -1]] * len(d))).reshape(len(d), -1).T
            p = float((np.abs((signs * d).mean(1)) >= abs(d.mean()) - 1e-12).mean())
            row[m] = {"diffs": [round(float(x), 4) for x in d], "mean_diff": round(float(d.mean()), 4),
                      "boot95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                      "signflip_p": round(p, 5)}
        out.append(row)
    order = sorted(range(len(out)), key=lambda i: out[i]["AP"]["signflip_p"])
    m, run_max = len(out), 0.0
    for rank, i in enumerate(order):
        run_max = max(run_max, min(1.0, (m - rank) * out[i]["AP"]["signflip_p"]))
        out[i]["holm_p"] = round(run_max, 5)
        out[i]["holm_reject_at_0.05"] = run_max < 0.05
    return out


def run(cfg: dict[str, Any], out: Path, arms: list[str] | None = None) -> dict[str, Any]:
    body = detection.run(cfg, out, arms)
    body["contrasts"] = dose.contrasts(body, cfg)
    if cfg.get("paired_primary"):
        body["paired"] = paired_contrasts(body, cfg)
    key = cfg["primary_key"]
    curve = {}
    for d in cfg["doses"]:
        v = [body["arms"][f"dose{d}_s{s}"]["eval"][key]["AP"] for s in cfg["seeds"]
             if f"dose{d}_s{s}" in body["arms"]]
        if v:
            rng = np.random.default_rng(26)
            b = np.array(v)[rng.integers(0, len(v), (10000, len(v)))].mean(1)
            curve[d] = {"AP": v, "mean": round(float(np.mean(v)), 4),
                        "boot95": [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]}
    body["curve"] = curve
    if cfg.get("arm_groups"):
        body["groups"] = group_summary(body, cfg)
        if cfg.get("h52_rule") and body.get("paired"):
            body["h52_decision"] = h52_decision(body, cfg["h52_rule"])
    return body


def group_summary(res: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Per arm group (`name_s{seed}` prefixes): AP per seed, mean, seed-bootstrap 95 %."""
    key, out = cfg["primary_key"], {}
    for g in cfg["arm_groups"]:
        v = [res["arms"][f"{g}_s{s}"]["eval"][key]["AP"] for s in cfg["seeds"] if f"{g}_s{s}" in res["arms"]]
        if v:
            rng = np.random.default_rng(52)
            b = np.array(v)[rng.integers(0, len(v), (10000, len(v)))].mean(1)
            out[g] = {"AP": v, "n": len(v), "mean": round(float(np.mean(v)), 4),
                      "boot95": [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]}
    return out


def h52_decision(res: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    """Apply the pre-registered H52 rule (docs/research/32 H52). X ~ Y iff the paired
    |mean diff| < `approx` AND Holm p >= 0.05. Rules are checked in order; more than
    one may hold, all are reported, the first is the selected label."""
    P = {c["contrast"].split(" (")[0]: c for c in res["paired"]}

    def c(a, b):   # b - a
        return P.get(f"{b} - {a}")
    thr, apx = rule["min_gain"], rule["approx"]

    def sig(x):
        return x is not None and x["AP"]["mean_diff"] >= thr and x["holm_p"] < 0.05

    def approx(x):
        return x is not None and abs(x["AP"]["mean_diff"]) < apx and x["holm_p"] >= 0.05
    ab, b0, da = c(rule["b"], rule["a"]), c(rule["real"], rule["b"]), c(rule["d"], rule["a"])
    held = {"label-driven": sig(ab), "image-level": approx(ab) and sig(b0), "diversity-only": approx(da)}
    sel = [k for k, v in held.items() if v]
    return {"rules": held, "selected": sel[0] if sel else "unresolved", "all_holding": sel}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = ["| dose | AP mean [95 %] | per seed |", "|---|---|---|"]
    L += [f"| {d} | {v['mean']:.4f} {v['boot95']} | {v['AP']} |" for d, v in res["curve"].items()]
    txt = "\n".join(L) + "\n\n" + dose.markdown_rows(res, cfg)
    if res.get("groups"):
        G = ["| arm | n | AP mean [95 %] |", "|---|---|---|"]
        G += [f"| {g} | {v['n']} | {v['mean']:.4f} {v['boot95']} |" for g, v in res["groups"].items()]
        txt += "\n\n" + "\n".join(G)
    if res.get("paired"):
        P = ["| paired contrast | n | AP diff [95 %] | sign-flip p | Holm p | AP50 diff | AP75 diff |",
             "|---|---|---|---|---|---|---|"]
        P += [f"| {c['contrast']} | {len(c['seeds'])} | {c['AP']['mean_diff']:+.4f} {c['AP']['boot95']} | "
              f"{c['AP']['signflip_p']} | {c['holm_p']} | {c['AP50']['mean_diff']:+.4f} | {c['AP75']['mean_diff']:+.4f} |"
              for c in res["paired"]]
        txt += "\n\n" + "\n".join(P)
    return txt
