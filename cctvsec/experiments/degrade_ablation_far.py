"""H3f: which stage of the cctv_day_720p degrade profile kills far-field recall?

Leave-one-out (full profile minus one stage group) and add-one-in (raw plus one stage group)
ablation on the far cameras of CC0 batch_v8 street_crowd_far_day. Detector arms (YOLOv8n,
zero-shot, CPU fp32): full frame at 1280, and H3d's 2.0x tiles merged with the tile-border
rule (d). Raw and the as-shipped degraded stream reuse H3d's cached detections; every
ablation variant is re-degraded from the raw PNGs with the profile's own code path
(`Profile._pre_codec` + `h264_sequence`, the same calls `apply_sequence` makes, same seeds as
`survsim/video.py`) and detected once into `dets_dir`. Pre-registered in docs/research/32 §H3f.

Stage groups (profile fields switched to their no-op values):
  optics   : defocus, vignette, chromatic aberration, lens dirt
  noise    : shot/read noise, fixed-pattern noise, hot pixels, spatial grain
  isp      : bilateral denoise, unsharp mask, dark-flat quantisation
  exposure : metered AE, auto-levels, AE/AWB drift, rolling banding
  codec    : H.264 GOP round trip (crf 29, gop 8, bf 0)
`resample` (cv2.resize to 1280x720) is not a group: the raw renders are already 1280x720,
so it is the identity by construction (asserted in the test), and the OSD overlay is left
off in every variant (the sanity gate compares against the shipped stream, which has it).
"""
from __future__ import annotations

import dataclasses
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from . import far_field_cc0 as base
from .common import batch_cameras, rpath, write_json
from .far_field_h3c import collapse
from .tile_merge import _arr, merge

GROUPS: dict[str, dict[str, Any]] = {
    "optics": {"defocus": 0.0, "vignette": 0.0, "chroma_px": 0.0, "dirt": 0.0},
    "noise": {"iso_gain": 1e-6, "read_noise": 0.0, "fpn": 0.0, "hot_pixels": 0.0, "grain_sigma": 0.0},
    "isp": {"denoise": 0.0, "sharpen": 0.0, "dark_flatten": 0.0},
    "exposure": {"ae_target": 0.0, "auto_levels": 0.0, "ae_drift_ev": 0.0, "awb_drift": 0.0, "rolling": 0.0},
    "codec": {},   # handled by the `codec` flag, not a profile field
}
ARMS = ["full_1280", "tiles_d"]


def variants(groups=None) -> list[str]:
    gs = list(groups or GROUPS)
    return ["full"] + [f"loo_{g}" for g in gs] + [f"aoi_{g}" for g in gs]


def present(R: dict) -> list[str]:
    """Groups with both a LOO and an AOI variant (a partial run scores only those)."""
    return [g for g in GROUPS if f"loo_{g}" in R and f"aoi_{g}" in R]


def variant_spec(name: str, profile: str = "cctv_day_720p", fps: float = 12.5):
    """-> (Profile, codec_on). full = every group on; loo_g = all but g; aoi_g = only g."""
    from survsim.sensors.degrade import PROFILES
    if name == "full":
        on = set(GROUPS)
    elif name.startswith("loo_"):
        on = set(GROUPS) - {name[4:]}
    elif name.startswith("aoi_"):
        on = {name[4:]}
    else:
        raise ValueError(name)
    if name != "full" and name[4:] not in GROUPS:
        raise ValueError(name)
    kw: dict[str, Any] = {"osd": False, "fps": fps}
    for g, fields in GROUPS.items():
        if g not in on:
            kw.update(fields)
    return dataclasses.replace(PROFILES[profile], **kw), "codec" in on


def degrade_stream(paths: list[Path], name: str, seq_seed: int, keep: list[int], profile: str = "cctv_day_720p",
                   fps: float = 12.5) -> dict[int, np.ndarray]:
    """Degrade a whole camera sequence exactly as apply_sequence does; return only `keep` frames.

    With the codec on every frame must go through pre-codec (the GOP predicts across frames);
    with it off frames are independent, so only `keep` is computed."""
    import cv2

    from survsim.sensors.degrade import h264_sequence
    p, codec = variant_spec(name, profile, fps)
    idx = list(range(len(paths))) if codec else sorted(keep)

    def pre(i):
        x = p._pre_codec(cv2.imread(str(paths[i])), seed=hash((seq_seed, i)) & 0x7FFFFFFF, frame_index=i,
                         sequence_seed=seq_seed)
        return np.clip(x, 0, 255).astype(np.uint8)

    frames = [pre(i) for i in idx]
    if codec:
        frames = h264_sequence(frames, p.crf, p.fps, p.codec_scale, gop=p.gop, bf=p.bf)
    ks = set(keep)
    return {i: np.clip(f, 0, 255).astype(np.uint8) for i, f in zip(idx, frames) if i in ks}


def _degrade_job(args) -> str:
    import cv2
    name, cam, rdir, seq_seed, keep, fdir, profile, fps, ref = args
    out = Path(fdir) / name / cam
    if out.is_dir() and all((out / f"{i:04d}.png").is_file() for i in keep):
        return f"{name}/{cam} cached"
    out.mkdir(parents=True, exist_ok=True)
    paths = sorted(Path(rdir).glob("*.png"))
    fr = degrade_stream(paths, name, seq_seed, keep, profile, fps)
    diffs = []
    for i, x in fr.items():
        cv2.imwrite(str(out / f"{i:04d}.png"), x)
        if ref and name == "full":
            r = cv2.imread(str(Path(ref) / f"{i:04d}.png"))
            diffs.append(float(np.median(np.abs(r.astype(int) - x.astype(int)))))
    if diffs:
        write_json(out / "vs_shipped.json", {"median_abs_diff_mean": float(np.mean(diffs)), "n": len(diffs)})
    return f"{name}/{cam} done"


# ---------------------------------------------------------------- detection
def detect_dir(cfg: dict, fdir: Path, keep: list[int], cache: Path) -> dict[int, dict]:
    """Same per-frame dict as H3d's cache (full_1280, full_640, tiles, rects, W, H)."""
    if cache.is_file():
        per = pickle.loads(cache.read_bytes())
        if all(f in per for f in keep):
            return per
    import cv2
    from ultralytics import YOLO

    from .farfield import tiles as tile_grid
    model = YOLO(str(rpath(cfg["model"])))
    kw = {"classes": [0], "conf": cfg["det_conf"], "verbose": False, "max_det": 300, "device": cfg["device"],
          "half": cfg["device"] != "cpu"}
    tw, th = cfg["tile"]
    per = {}
    for f in keep:
        img = cv2.imread(str(fdir / f"{f:04d}.png"))
        H, W = img.shape[:2]
        rects = tile_grid(W, H, tw, th, cfg["overlap"])
        d = {"full_1280": _arr(model.predict(img, imgsz=1280, **kw)[0]),
             "full_640": _arr(model.predict(img, imgsz=640, **kw)[0]), "rects": rects, "W": W, "H": H}
        crops = [img[y:y + th, x:x + tw] for x, y, _, _ in rects]
        tl = [np.concatenate([_arr(p, x, y), np.full((len(p.boxes), 1), i)], 1).reshape(-1, 6)
              for i, ((x, y, _, _), p) in enumerate(zip(rects, model.predict(crops, imgsz=cfg["tile_imgsz"], **kw)))]
        d["tiles"] = np.concatenate(tl) if tl else np.zeros((0, 6))
        per[f] = d
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(per))
    return per


def arm_preds(d: dict, cfg: dict) -> dict[str, list]:
    from .tile_merge import to_preds
    return {"full_1280": to_preds(d["full_1280"]), "tiles_d": to_preds(merge("d_tile_border", d, cfg))}


# ---------------------------------------------------------------- statistics
def shares(R: dict[str, np.ndarray]) -> dict[str, Any]:
    """R: variant -> recall (scalar or bootstrap vector). Loss and per-group attribution.

    loo share(g) = (R[loo_g] - R[full]) / (R[raw] - R[full])  -- recall recovered by removing g
    aoi share(g) = (R[raw] - R[aoi_g]) / (R[raw] - R[full])    -- loss caused by g alone"""
    loss = np.asarray(R["raw"], float) - np.asarray(R["full"], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        den = np.where(loss > 0, loss, np.nan)
        return {"loss": loss,
                "loo": {g: (np.asarray(R[f"loo_{g}"], float) - np.asarray(R["full"], float)) / den for g in present(R)},
                "aoi": {g: (np.asarray(R["raw"], float) - np.asarray(R[f"aoi_{g}"], float)) / den for g in present(R)}}


def decide(pt: dict[str, Any], D: dict[str, Any]) -> dict[str, Any]:
    loo = {g: float(v) for g, v in pt["loo"].items()}
    aoi = {g: float(v) for g, v in pt["aoi"].items()}
    culprit = max(loo, key=lambda g: -1e9 if np.isnan(loo[g]) else loo[g])
    ok_loss = bool(pt["loss"] >= D["min_loss"])
    met = bool(ok_loss and loo[culprit] >= D["share_min"] and aoi[culprit] >= D["share_min"])
    return {"loss_ok": ok_loss, "culprit": culprit, "culprit_loo_share": round(loo[culprit], 4),
            "culprit_aoi_share": round(aoi[culprit], 4), "decision_met": met,
            "predicted": D["predicted_culprit"], "prediction_correct": bool(met and culprit == D["predicted_culprit"])}


def _ci(pt, bs) -> list:
    bs = np.asarray(bs, float)
    bs = bs[~np.isnan(bs)]
    lo, hi = (np.percentile(bs, [2.5, 97.5]) if len(bs) else (np.nan, np.nan))
    return [round(float(pt), 4), round(float(lo), 4), round(float(hi), 4)]


def bootstrap(hits: dict[str, np.ndarray], n: np.ndarray, n_boot: int, seed: int) -> dict[str, Any]:
    """hits: variant -> per-block hit counts; n: per-block GT counts (same for every variant)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(n), size=(n_boot, len(n)))
    Rp = {v: h.sum() / n.sum() for v, h in hits.items()}
    Rb = {v: h[idx].sum(1) / n[idx].sum(1) for v, h in hits.items()}
    sp, sb = shares(Rp), shares(Rb)
    return {"recall": {v: _ci(Rp[v], Rb[v]) for v in hits}, "loss": _ci(sp["loss"], sb["loss"]),
            "loo": {g: _ci(sp["loo"][g], sb["loo"][g]) for g in sp["loo"]},
            "aoi": {g: _ci(sp["aoi"][g], sb["aoi"][g]) for g in sp["aoi"]},
            "loo_sum": round(float(sum(sp["loo"].values())), 4), "aoi_sum": round(float(sum(sp["aoi"].values())), 4),
            "_pt": sp}


# ---------------------------------------------------------------- run
def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from multiprocessing import Pool
    batch = rpath(cfg["batch_dir"])
    run_name = cfg["run"]
    lic = base.check_licence(batch, [run_name])
    if not all(lic.values()):
        raise RuntimeError(f"licence check failed: {lic}")
    raw = batch_cameras(batch, run_name, "raw")
    fdir, ddir, h3d = rpath(cfg["frames_dir"]), rpath(cfg["dets_dir"]), rpath(cfg["h3d_dets_dir"])
    keep = {c: [f for f in sorted(raw[c]["frames"]) if f >= 1 and f % cfg["stride"] == cfg["offset"]]
            for c in cfg["far_cams"]}
    # Partial-run knobs (added after registration, default = registered design; a run that uses
    # them is labelled partial): score every n-th registered frame, and only some stage groups.
    groups = cfg.get("groups_subset") or list(GROUPS)
    keep = {c: v[::cfg.get("frames_every", 1)] for c, v in keep.items()}
    jobs = [(v, c, str(batch / run_name / "render" / c), cfg["seq_seeds"][c], keep[c], str(fdir), cfg["profile"],
             cfg["fps"], str(batch / run_name / "video" / "degraded" / c)) for v in variants(groups) for c in cfg["far_cams"]]
    with Pool(cfg.get("degrade_workers", 4)) as pool:
        for msg in pool.imap_unordered(_degrade_job, jobs):
            print("degrade", msg, flush=True)
    dets: dict[str, dict] = {}
    for c in cfg["far_cams"]:
        hr = pickle.loads((h3d / f"{run_name}__raw__{c}.pkl").read_bytes())
        hd = pickle.loads((h3d / f"{run_name}__degraded__{c}.pkl").read_bytes())
        dets.setdefault("raw", {}).update({(c, f): hr[f] for f in keep[c]})
        dets.setdefault("shipped", {}).update({(c, f): hd[f] for f in keep[c]})
        for v in variants(groups):
            ck = ddir / f"{v}__{c}.pkl"
            done = pickle.loads(ck.read_bytes()) if ck.is_file() else {}
            per = done if all(f in done for f in keep[c]) else detect_dir(cfg, fdir / v / c, keep[c], ck)
            dets.setdefault(v, {}).update({(c, f): per[f] for f in keep[c]})
            print("detect", v, c, flush=True)
    bands = [tuple(b) for b in cfg["bands"]]
    split = next(i for i, b in enumerate(cfg["bands"]) if b[0] >= cfg["primary_min_px"])
    mh = cfg["min_gt_height"]
    G = {(c, f): [r for r in raw[c]["gt"].get(f, []) if r["bbox"][3] >= mh] for c in keep for f in keep[c]}
    I = {(c, f): [r for r in raw[c]["gt"].get(f, []) if r["bbox"][3] < mh] for c in keep for f in keep[c]}
    blocks = base.make_blocks(list(G), cfg["block_sampled"])
    res: dict[str, Any] = {"licence_commercial_ml_ok": lic, "n_far_frames": len(G), "n_blocks": len(blocks),
                           "variants": ["raw", "shipped"] + variants(groups), "arms": {},
                           "partial": {"frames_every": cfg.get("frames_every", 1), "groups": groups}}
    for arm in ARMS:
        preds = {v: {k: arm_preds(d, cfg)[arm] for k, d in dv.items()} for v, dv in dets.items()}
        cc = collapse({v: base.frame_counts(G, I, preds[v], bands, cfg["op_conf"], cfg["iou"]) for v in preds}, split)
        hits = {v: np.array([sum(cc[v][k]["hit"][1] for k in b) for b in blocks], float) for v in preds}
        n = np.array([sum(cc["raw"][k]["n"][1] for k in b) for b in blocks], float)
        bs = bootstrap(hits, n, cfg["n_boot"], cfg["seed"])
        pt = bs.pop("_pt")
        bs["n_gt_ge20"] = int(n.sum())
        bs["decision"] = decide(pt, cfg["decision"])
        res["arms"][arm] = bs
    res["sanity_full_vs_shipped"] = {
        a: round(abs(res["arms"][a]["recall"]["full"][0] - res["arms"][a]["recall"]["shipped"][0]), 4) for a in ARMS}
    res["sanity_ok"] = bool(max(res["sanity_full_vs_shipped"].values()) <= cfg["decision"]["sanity_tol"])
    px = [json.loads(p.read_text()) for p in sorted((fdir / "full").glob("*/vs_shipped.json"))]
    res["full_vs_shipped_median_abs_px"] = [round(p["median_abs_diff_mean"], 3) for p in px]
    res["near_hn"] = near_hard_negative(cfg, batch, run_name, h3d, bands)
    prim = res["arms"][cfg["decision"]["primary_arm"]]["decision"]
    res["decision"] = {**prim, "primary_arm": cfg["decision"]["primary_arm"], "sanity_ok": res["sanity_ok"],
                       "HN_near_ok": res["near_hn"]["ok"]}
    if cfg.get("figure"):
        figure(res, rpath(cfg["figure"]))
    return res


def near_hard_negative(cfg: dict, batch: Path, run_name: str, h3d: Path, bands) -> dict[str, Any]:
    """Near camera, >= hn_min_px rows: raw vs shipped full profile, both from H3d's cache."""
    c = cfg["near_cam"]
    raw = batch_cameras(batch, run_name, "raw")[c]
    hr = pickle.loads((h3d / f"{run_name}__raw__{c}.pkl").read_bytes())
    hd = pickle.loads((h3d / f"{run_name}__degraded__{c}.pkl").read_bytes())
    ks = [(c, f) for f in sorted(hr) if f in hd]
    G = {k: [r for r in raw["gt"].get(k[1], []) if r["bbox"][3] >= cfg["min_gt_height"]] for k in ks}
    I = {k: [r for r in raw["gt"].get(k[1], []) if r["bbox"][3] < cfg["min_gt_height"]] for k in ks}
    split = next(i for i, b in enumerate(cfg["bands"]) if b[0] >= cfg["hn_min_px"])
    blocks = base.make_blocks(ks, cfg["hn_block_sampled"])
    out: dict[str, Any] = {"n_frames": len(ks), "min_px": cfg["hn_min_px"], "max_drop": cfg["decision"]["hn_max_drop"]}
    for arm in ARMS:
        preds = {"raw": {k: arm_preds(hr[k[1]], cfg)[arm] for k in ks},
                 "full": {k: arm_preds(hd[k[1]], cfg)[arm] for k in ks}}
        cc = collapse({v: base.frame_counts(G, I, preds[v], bands, cfg["op_conf"], cfg["iou"]) for v in preds}, split)
        hits = {v: np.array([sum(cc[v][k]["hit"][1] for k in b) for b in blocks], float) for v in preds}
        n = np.array([sum(cc["raw"][k]["n"][1] for k in b) for b in blocks], float)
        rng = np.random.default_rng(cfg["seed"])
        idx = rng.integers(0, len(n), size=(cfg["n_boot"], len(n)))
        R = {v: (h.sum() / n.sum(), h[idx].sum(1) / n[idx].sum(1)) for v, h in hits.items()}
        drop = R["raw"][0] - R["full"][0]
        out[arm] = {"n_gt": int(n.sum()), "raw": _ci(*R["raw"]), "full": _ci(*R["full"]),
                    "drop": _ci(drop, R["raw"][1] - R["full"][1])}
    out["ok"] = bool(all(out[a]["drop"][0] < cfg["decision"]["hn_max_drop"] for a in ARMS))
    return out


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [(f"CC0 batch_v8 {cfg['run']} far cams, {res['n_far_frames']} frames, {res['n_blocks']} blocks; "
          "recall on GT >= 20 px at conf 0.25 [95% block CI]"), ""]
    for arm, r in res["arms"].items():
        L += [f"**{arm}** (n GT = {r['n_gt_ge20']}; loss raw->full {r['loss']})", "",
              "| variant | recall |", "|---|---|"]
        L += [f"| {v} | {r['recall'][v]} |" for v in res["variants"]]
        L += ["", "| group | LOO share | AOI share |", "|---|---|---|"]
        L += [f"| {g} | {r['loo'][g]} | {r['aoi'][g]} |" for g in r["loo"]]
        L += ["", f"sums: LOO {r['loo_sum']}, AOI {r['aoi_sum']}; decision {r['decision']}", ""]
    L += [f"near HN: {res['near_hn']}", (f"sanity: {res['sanity_full_vs_shipped']} ok={res['sanity_ok']}; "
          f"px {res['full_vs_shipped_median_abs_px']}"), f"decision: {res['decision']}"]
    return "\n".join(L) + "\n"


def figure(res: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
    vs = res["variants"]
    x = np.arange(len(vs))
    for j, (arm, col) in enumerate((("full_1280", "#888"), ("tiles_d", "#3a7"))):
        p = np.array([res["arms"][arm]["recall"][v] for v in vs], float)
        axs[0].bar(x + (j - 0.5) * 0.4, p[:, 0], 0.4, yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], capsize=2,
                   color=col, label=arm)
    axs[0].set_xticks(x, vs, rotation=60, fontsize=7)
    axs[0].set_ylim(0, 1)
    axs[0].legend(fontsize=8)
    axs[0].set_title("far recall, GT >= 20 px, conf 0.25")
    arm = res["decision"]["primary_arm"]
    gs = list(res["arms"][arm]["loo"])
    x = np.arange(len(gs))
    for j, (k, col) in enumerate((("loo", "#37a"), ("aoi", "#c64"))):
        p = np.array([res["arms"][arm][k][g] for g in gs], float)
        axs[1].bar(x + (j - 0.5) * 0.4, p[:, 0], 0.4, yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], capsize=2,
                   color=col, label={"loo": "leave-one-out", "aoi": "add-one-in"}[k])
    axs[1].axhline(0.6, ls=":", color="grey")
    axs[1].axhline(0, color="k", lw=0.5)
    axs[1].set_xticks(x, gs)
    axs[1].legend(fontsize=8)
    axs[1].set_title(f"share of raw->full recall loss ({arm}); decision line 0.60")
    fig.suptitle("H3f cctv_day_720p stage ablation on CC0 far cameras (YOLOv8n, CPU)")
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
