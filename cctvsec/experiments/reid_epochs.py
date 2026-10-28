"""H10: ReID across appearance epochs on disguise_and_tamper (batch_v7).

Cues: OSNet-ImageNet, HSV histogram, and a gait signature (a *simulated*
measurement of each identity's gait parameters via survsim.gait.signature.observe,
not extracted from pixels). Protocols: same-epoch, cross-epoch, cross-camera."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, wait_for_gpu, write_json
from .reid import collect, crops, hsv_hist
from .tracking import boot_ci, wilson


def _epochs(items, cfg) -> None:
    """Attach the GT appearance epoch (world.parquet, the frame's actual state)."""
    import pandas as pd
    batch = rpath(cfg["batch_dir"])
    look: dict[tuple, int] = {}
    for run in cfg["runs"]:
        w = pd.read_parquet(batch / run / "gt" / "world.parquet", columns=["frame", "uid", "appearance_epoch"])
        for f, u, e in w.itertuples(index=False):
            look[(run, int(f), u)] = int(e)
    for it in items:
        uid = it["identity"].split(":", 1)[1]
        it["uid"] = uid
        it["epoch"] = look.get((it["run"], it["frame"], uid), -1)


def ranks(ids, sim, excl) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per valid query: rank-1 hit, AP, query index."""
    hits, aps, qi = [], [], []
    for i in range(len(ids)):
        s = sim[i].copy()
        s[excl[i]] = -np.inf
        o = np.argsort(-s)
        o = o[np.isfinite(s[o])]
        h = (ids[o] == ids[i]).astype(int)
        if len(o) == 0 or h.sum() == 0:
            continue
        prec = np.cumsum(h) / (np.arange(len(h)) + 1)
        hits.append(h[0])
        aps.append(float((prec * h).sum() / h.sum()))
        qi.append(i)
    return np.array(hits, int), np.array(aps), np.array(qi, int)


def first_positive_ranks(ids, sim, excl, qmask) -> list[dict[str, Any]]:
    """For each masked query: 1-based rank of its first true match among the
    non-excluded gallery, gallery size, and distinct distractor identities."""
    out = []
    for i in np.where(qmask)[0]:
        s = sim[i].copy()
        s[excl[i]] = -np.inf
        o = np.argsort(-s)
        o = o[np.isfinite(s[o])]
        h = ids[o] == ids[i]
        if not h.any():
            continue
        out.append({"query": int(i), "rank": int(np.argmax(h)) + 1, "gallery": len(o),
                    "distractor_ids": len(set(ids[o][~h]))})
    return out


def _gait_feats(items, cfg):
    import pandas as pd

    from survsim.gait.signature import GaitSignature, gait_similarity_matrix, observe, population_spread
    batch = rpath(cfg["batch_dir"])
    p = pd.read_parquet(batch / cfg["runs"][0] / "gt" / "identities.parquet")
    sig = {}
    for r in p.itertuples():
        sig[r.uid] = GaitSignature(r.gait_cadence_spm, r.gait_step_length_m, r.gait_asymmetry,
                                   r.gait_arm_swing, r.gait_sway_amplitude_m, r.gait_stance_width_m,
                                   r.gait_style)
    obs = [observe(sig[it["uid"]], noise=cfg["gait_noise"], seed=i) for i, it in enumerate(items)]
    return gait_similarity_matrix(obs, obs, population_spread(list(sig.values())))


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    from ..baselines.run import _embedder
    cfg = {**cfg, "runs": list(cfg["runs"])}
    items = collect({**cfg, "runs": {r: cfg["world"] for r in cfg["runs"]}})
    run_of = {}
    for r in cfg["runs"]:
        run_of["night" if r.endswith("night") else "day"] = r
    for it in items:
        it["run"] = run_of[it["condition"]]
    _epochs(items, cfg)
    import pandas as pd
    idp = pd.read_parquet(rpath(cfg["batch_dir"]) / cfg["runs"][0] / "gt" / "identities.parquet")
    res: dict[str, Any] = {
        "n_crops": len(items), "n_identities": len({i["uid"] for i in items}),
        "epochs_in_gt_identities": {u: sorted(g["epoch"].tolist()) for u, g in idp.groupby("uid") if len(g) > 1},
        "epoch_change_times_s": {r.uid: r.t_from for r in idp.itertuples() if r.epoch > 0},
        "rendered_time_span_s": [1 / cfg["fps"], cfg["max_frame"] / cfg["fps"]],
        "crops_per_epoch": {str(e): int(sum(i["epoch"] == e for i in items)) for e in sorted({i["epoch"] for i in items})},
    }
    multi = {u for u in {i["uid"] for i in items} if len({i["epoch"] for i in items if i["uid"] == u}) > 1}
    res["identities_with_crops_in_2_epochs"] = sorted(multi)
    bgr = crops(items)
    gpu = wait_for_gpu(cfg.get("min_free_mib", 2048), max_wait_s=900)
    name, embed = _embedder()
    F = np.concatenate([embed([c[:, :, ::-1].copy() for c in bgr[i:i + 64]])
                        for i in range(0, len(bgr), 64)]) if name.startswith("osnet") else \
        np.concatenate([embed(bgr[i:i + 64]) for i in range(0, len(bgr), 64)])
    res["gpu_wait"] = gpu

    def cos(X):
        X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
        return X @ X.T
    sims = {name: cos(F), "hsv_histogram": cos(hsv_hist(bgr)), "gait_signature (simulated obs)": _gait_feats(items, cfg)}
    ids = np.array([i["uid"] for i in items])
    ep = np.array([i["epoch"] for i in items])
    cam = np.array([i["camera"] for i in items])
    cond = np.array([i["condition"] for i in items])
    fr = np.array([i["frame"] for i in items])
    eye = np.eye(len(items), dtype=bool)
    sid, sep = ids[:, None] == ids[None], ep[:, None] == ep[None]
    scam, scond = cam[:, None] == cam[None], cond[:, None] == cond[None]
    near = np.abs(fr[:, None] - fr[None]) < 5 * cfg["fps"]
    base = eye | ~scond
    prot = {"i_same_epoch (>=5 s or other camera)": base | (sid & ~sep) | (scam & near),
            "ii_cross_epoch": base | (sid & sep),
            "iii_cross_camera_same_epoch": base | scam | (sid & ~sep)}
    res["cues"] = {}
    for cname, S in sims.items():
        rc: dict[str, Any] = {}
        for pname, ex in prot.items():
            h, a, qi = ranks(ids, S, ex)
            if len(h) == 0:
                rc[pname] = {"n_queries": 0, "note": "no query has a valid positive — not measurable"}
                continue
            per_id = {}
            for q, ap in zip(qi, a):
                per_id.setdefault(ids[q], []).append(ap)
            rc[pname] = {"n_queries": len(h), "n_identities": len(per_id),
                         "rank1": wilson(int(h.sum()), len(h)),
                         "mAP": round(float(a.mean()), 4),
                         "mAP_boot_over_identities": boot_ci([np.mean(v) for v in per_id.values()])}
        # distractor-set ranking for the identities that change outfit (n is tiny)
        dr = {}
        for u in multi:
            fr_ = first_positive_ranks(ids, S, prot["ii_cross_epoch"], ids == u)
            if fr_:
                rk = np.array([x["rank"] for x in fr_])
                dr[u] = {"n_queries": len(fr_), "median_rank": float(np.median(rk)),
                         "rank_range": [int(rk.min()), int(rk.max())], "frac_rank1": round(float((rk == 1).mean()), 3),
                         "median_gallery": float(np.median([x["gallery"] for x in fr_])),
                         "distractor_ids": int(max(x["distractor_ids"] for x in fr_)),
                         "chance_median_rank": round(float(np.median([(x["gallery"] + 1) / 2 for x in fr_])), 1),
                         "by_epoch": {str(e): float(np.median([x["rank"] for x in fr_ if ep[x["query"]] == e]))
                                      for e in sorted({int(ep[x["query"]]) for x in fr_})}}
        rc["changer_cross_epoch_ranking"] = dr
        # exploratory: same body mesh, different uid/outfit
        rc["same_mesh_other_outfit"] = _mesh(items, S, cfg, scond, sid)
        res["cues"][cname] = rc
    res["embedder"] = name
    write_json(out / "items.json", items)
    return res


def _mesh(items, S, cfg, scond, sid) -> dict[str, Any]:
    import pandas as pd
    p = pd.read_parquet(rpath(cfg["batch_dir"]) / cfg["runs"][0] / "identities_rendered.parquet")
    char = {r.uid: r.asset_licences.split("|")[-1] for r in p.itertuples()}
    ch = np.array([char.get(i["uid"], "?") for i in items])
    smesh = ch[:, None] == ch[None]
    iu = np.triu(np.ones_like(S, bool), 1) & scond & ~sid
    a, b = S[iu & smesh], S[iu & ~smesh]
    same_id = S[np.triu(np.ones_like(S, bool), 1) & scond & sid]
    return {"sim_same_mesh_diff_uid": round(float(a.mean()), 4) if len(a) else None, "n_pairs_same_mesh": len(a),
            "sim_diff_mesh": round(float(b.mean()), 4), "n_pairs_diff_mesh": len(b),
            "sim_same_uid": round(float(same_id.mean()), 4) if len(same_id) else None,
            "shared_meshes": {c: sorted({u for u, cc in char.items() if cc == c})
                              for c in set(char.values()) if list(char.values()).count(c) > 1}}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    L = [(f"{res['n_crops']} crops, {res['n_identities']} identities; crops per epoch {res['crops_per_epoch']}; "
          f"identities with crops in 2 epochs: {res['identities_with_crops_in_2_epochs']}"), "",
         "| cue | protocol | queries | ids | rank-1 [95% Wilson] | mAP [boot over ids] |", "|---|---|---|---|---|---|"]
    for c, rc in res["cues"].items():
        for p, v in rc.items():
            if p in ("same_mesh_other_outfit", "changer_cross_epoch_ranking"):
                continue
            if not v["n_queries"]:
                L.append(f"| {c} | {p} | 0 | 0 | not measurable | – |")
                continue
            r, m = v["rank1"], v["mAP_boot_over_identities"]
            L.append(f"| {c} | {p} | {v['n_queries']} | {v['n_identities']} | {r['p']:.3f} [{r['lo']:.3f}, {r['hi']:.3f}] | "
                     f"{v['mAP']:.3f} [{m['lo']:.3f}, {m['hi']:.3f}] |")
    L += ["", "Changer cross-epoch ranking (rank of first true match among distractors):", "```",
          json.dumps({c: rc.get("changer_cross_epoch_ranking") for c, rc in res["cues"].items()}, indent=1), "```"]
    L += ["", "```", json.dumps({c: rc["same_mesh_other_outfit"] for c, rc in res["cues"].items()}, indent=1), "```"]
    return "\n".join(L) + "\n"
