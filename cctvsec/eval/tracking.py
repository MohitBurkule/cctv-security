"""Tracking and re-identification metrics.

Pure NumPy/SciPy, so nothing here needs torch or TrackEval.

Three families, because they answer different questions and the field routinely
confuses them:

* **MOTA** counts frame-level mistakes (misses, false positives, identity
  switches). It is dominated by detection quality, so a better detector flatters
  it even if the tracker is poor.
* **IDF1** measures how consistently one ground-truth identity maps to one
  predicted identity over its whole life. This is the number that reflects
  whether a track survives an occlusion or a camera hand-off.
* **HOTA** separates detection accuracy (DetA) from association accuracy (AssA),
  which is the decomposition you need to know *which half* to fix.

The surveillance-specific addition is `reid_by_epoch`: re-identification scored
separately within an appearance epoch and across an appearance change. Those are
different problems — appearance works within an epoch and is useless across one —
and averaging them produces a number that describes neither.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from .detection import iou_matrix

#: The 19 IoU thresholds the HOTA paper (arXiv 2009.07736, Eq. 16) integrates
#: over: 0.05, 0.10, ..., 0.95. `hota` is the mean of HOTA_alpha across these;
#: `hota_at_05` is kept for continuity with numbers already reported at the
#: single alpha = 0.5 operating point.
HOTA_ALPHAS: tuple[float, ...] = tuple(round(0.05 * i, 2) for i in range(1, 20))

#: Comparing a computed IoU to a threshold with a bare `>=` is a float-boundary
#: bug: an IoU that is conceptually exactly 0.9 (say) is usually 0.899999...94
#: after the box-area arithmetic, and fails `>= 0.9`, silently dropping a match
#: that should have counted. Every IoU-vs-threshold comparison in this module
#: goes through this epsilon so an intended-exact threshold is honoured.
_IOU_EPS = 1e-9


@dataclass
class TrackingResult:
    mota: float
    motp: float
    idf1: float
    idp: float
    idr: float
    hota: float
    deta: float
    assa: float
    id_switches: int
    fragmentations: int
    misses: int
    false_positives: int
    n_gt: int
    n_frames: int
    hota_at_05: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "mota": round(self.mota, 4), "motp": round(self.motp, 4),
            "idf1": round(self.idf1, 4), "idp": round(self.idp, 4), "idr": round(self.idr, 4),
            "hota": round(self.hota, 4), "deta": round(self.deta, 4), "assa": round(self.assa, 4),
            "hota_at_05": round(self.hota_at_05, 4),
            "id_switches": self.id_switches, "fragmentations": self.fragmentations,
            "misses": self.misses, "false_positives": self.false_positives,
            "n_gt": self.n_gt, "n_frames": self.n_frames,
        }


def _frames(rows: Iterable[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        out[int(r["frame"])].append(r)
    return dict(out)


def evaluate_mot(
    gt_rows: Sequence[dict[str, Any]],
    pred_rows: Sequence[dict[str, Any]],
    iou_threshold: float = 0.5,
) -> TrackingResult:
    """Score a single-camera tracker, matching the reference TrackEval exactly.

    Rows are dicts with `frame`, `id`, `bbox` (xywh). Each metric family uses
    its own matching, as in TrackEval (JonathonLuiten/TrackEval; parity is
    asserted by `tests/test_trackeval_parity.py`, docs/13 "TrackEval parity"):

    * **CLEAR (MOTA/MOTP/IDSW/Frag)** — per frame, Hungarian on
      `1000 * [same pred id as this GT in the previous frame] + IoU`, pairs
      below `iou_threshold` disallowed (Bernardin & Stiefelhagen 2008
      continuity). "Previous frame" is the last frame that had both GT and
      predictions; an IDSW compares against the last pred id the GT ever had.
      Frag = (number of tracked-run starts - 1) per GT. As in TrackEval, a
      frame with no GT or no predictions at all is skipped entirely, so it
      neither breaks a run nor resets the previous-frame continuity.
    * **Identity (IDF1/IDP/IDR)** — every GT/pred pair with IoU >= threshold
      in a frame is a potential match; one global Hungarian over identities
      maximises IDTP (Ristani et al. 2016). Not restricted to CLEAR matches.
    * **HOTA** — the paper's definition (Luiten et al., IJCV 2021, arXiv
      2009.07736): one matching per frame maximising
      `global_alignment_score * IoU`, thresholded at each of the 19 alphas
      0.05..0.95; DetA_a = TP/(TP+FN+FP), AssA_a = TP-weighted mean track
      Jaccard, HOTA = mean_a sqrt(DetA_a * AssA_a). `deta`/`assa`/`hota_at_05`
      are the alpha = 0.5 slice.
    """
    gt_by_frame = _frames(gt_rows)
    pred_by_frame = _frames(pred_rows)
    frames = sorted(set(gt_by_frame) | set(pred_by_frame))
    gid_ix = {k: i for i, k in enumerate(dict.fromkeys(r["id"] for r in gt_rows))}
    pid_ix = {k: i for i, k in enumerate(dict.fromkeys(r["id"] for r in pred_rows))}
    n_gid, n_pid = len(gid_ix), len(pid_ix)

    per_frame: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for frame in frames:
        gts = gt_by_frame.get(frame, [])
        preds = pred_by_frame.get(frame, [])
        g = np.array([gid_ix[r["id"]] for r in gts], dtype=int)
        p = np.array([pid_ix[r["id"]] for r in preds], dtype=int)
        gb = np.array([r["bbox"] for r in gts], dtype=float).reshape(-1, 4)
        pb = np.array([r["bbox"] for r in preds], dtype=float).reshape(-1, 4)
        per_frame.append((g, p, iou_matrix(pb, gb).T))   # sim: gt x pred

    total_gt = sum(len(g) for g, _, _ in per_frame)
    total_pred = sum(len(p) for _, p, _ in per_frame)
    # TrackEval's epsilon (machine eps), not `_IOU_EPS`: parity with the
    # reference beats honouring "conceptually exact" boundary IoUs.
    thr = iou_threshold - np.finfo(float).eps

    # ---- CLEAR -----------------------------------------------------------
    tp = fn = fp = switches = 0
    motp_sum = 0.0
    prev_ever = np.full(n_gid, -1)
    prev_step = np.full(n_gid, -1)
    run_starts = np.zeros(n_gid, dtype=int)
    for g, p, sim in per_frame:
        if len(g) == 0:
            fp += len(p)
            continue
        if len(p) == 0:
            fn += len(g)
            continue
        score = 1000.0 * (p[None, :] == prev_step[g][:, None]) + sim
        score[sim < thr] = 0.0
        r, c = linear_sum_assignment(-score)
        ok = score[r, c] > np.finfo(float).eps
        r, c = r[ok], c[ok]
        mg, mp = g[r], p[c]
        prev = prev_ever[mg]
        switches += int(np.sum((prev >= 0) & (prev != mp)))
        not_prev = prev_step < 0
        prev_ever[mg] = mp
        prev_step[:] = -1
        prev_step[mg] = mp
        run_starts += not_prev & (prev_step >= 0)
        tp += len(r)
        fn += len(g) - len(r)
        fp += len(p) - len(r)
        motp_sum += float(sim[r, c].sum())
    frags = int(np.sum(run_starts[run_starts > 0] - 1))
    mota = (tp - fp - switches) / max(1, tp + fn)
    motp = motp_sum / max(1, tp)

    # ---- Identity --------------------------------------------------------
    id_pairs: Counter[tuple[int, int]] = Counter()
    for g, p, sim in per_frame:
        gi, pi = np.nonzero(sim >= thr)
        id_pairs.update(zip(g[gi].tolist(), p[pi].tolist()))
    gt_counts = Counter(gid_ix[r["id"]] for r in gt_rows)
    pred_counts = Counter(pid_ix[r["id"]] for r in pred_rows)
    idtp = _id_true_positives(id_pairs, gt_counts, pred_counts)
    idp = idtp / max(total_pred, 1)
    idr = idtp / max(total_gt, 1)
    idf1 = idtp / max(1.0, 0.5 * (total_gt + total_pred)) if (total_gt + total_pred) else 0.0

    # ---- HOTA ------------------------------------------------------------
    hota_a, deta_a, assa_a = _hota_alphas(per_frame, n_gid, n_pid)
    i05 = HOTA_ALPHAS.index(0.5)

    return TrackingResult(
        mota=mota, motp=motp, idf1=idf1, idp=idp, idr=idr,
        hota=float(np.mean(hota_a)), deta=float(deta_a[i05]), assa=float(assa_a[i05]),
        hota_at_05=float(hota_a[i05]),
        id_switches=switches, fragmentations=frags,
        misses=fn, false_positives=fp, n_gt=total_gt, n_frames=len(frames),
    )


def _hota_alphas(per_frame, n_gid: int, n_pid: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """HOTA/DetA/AssA at each of the 19 alphas, TrackEval's `HOTA.eval_sequence`.

    The matching is done once per frame, maximising
    `global_alignment_score * IoU` so that pairs which are consistently
    associated over the whole sequence are preferred (paper Sec. 5); each alpha
    then keeps the matched pairs with IoU >= alpha.
    """
    na = len(HOTA_ALPHAS)
    alphas = np.array(HOTA_ALPHAS)
    gt_id_count = np.zeros(n_gid)
    pr_id_count = np.zeros(n_pid)
    potential = np.zeros((n_gid, n_pid))
    for g, p, sim in per_frame:
        if len(g) and len(p):
            denom = sim.sum(0)[None, :] + sim.sum(1)[:, None] - sim
            sim_iou = np.zeros_like(sim)
            m = denom > np.finfo(float).eps
            sim_iou[m] = sim[m] / denom[m]
            potential[g[:, None], p[None, :]] += sim_iou
        gt_id_count[g] += 1
        pr_id_count[p] += 1
    align = potential / np.maximum(1e-300, gt_id_count[:, None] + pr_id_count[None, :] - potential) \
        if potential.size else potential

    tp = np.zeros(na)
    fn = np.zeros(na)
    fp = np.zeros(na)
    counts = np.zeros((na, n_gid, n_pid))
    for g, p, sim in per_frame:
        if len(g) == 0 or len(p) == 0:
            fp += len(p)
            fn += len(g)
            continue
        r, c = linear_sum_assignment(-(align[g[:, None], p[None, :]] * sim))
        s = sim[r, c]
        for a, alpha in enumerate(alphas):
            ok = s >= alpha - np.finfo(float).eps
            k = int(ok.sum())
            tp[a] += k
            fn[a] += len(g) - k
            fp[a] += len(p) - k
            if k:
                np.add.at(counts[a], (g[r[ok]], p[c[ok]]), 1)
    assa = np.zeros(na)
    for a in range(na):
        mc = counts[a]
        jac = mc / np.maximum(1, gt_id_count[:, None] + pr_id_count[None, :] - mc)
        assa[a] = float(np.sum(mc * jac) / max(1.0, tp[a]))
    deta = tp / np.maximum(1.0, tp + fn + fp)
    return np.sqrt(deta * assa), deta, assa


def _id_true_positives(pair_counts, gt_counts, pred_counts) -> int:
    """Best one-to-one identity assignment, maximising frames correctly associated."""
    if not pair_counts:
        return 0
    gids = sorted(gt_counts)
    pids = sorted(pred_counts)
    gain = np.zeros((len(gids), len(pids)))
    for (g, p), n in pair_counts.items():
        gain[gids.index(g), pids.index(p)] = n
    rows, cols = linear_sum_assignment(-gain)
    return int(gain[rows, cols].sum())


def _association_accuracy(pair_counts, gt_counts, pred_counts) -> float:
    """Mean Jaccard overlap between matched ground-truth and predicted tracks."""
    if not pair_counts:
        return 0.0
    scores = []
    for (gid, pid), inter in pair_counts.items():
        union = gt_counts[gid] + pred_counts[pid] - inter
        scores.append(inter / union if union else 0.0)
    total_matched = sum(pair_counts.values())
    weights = [c / total_matched for c in pair_counts.values()]
    return float(np.average(scores, weights=weights))


# --------------------------------------------------------------------- MTMC


def evaluate_mtmc(
    gt_rows: Sequence[dict[str, Any]],
    pred_rows: Sequence[dict[str, Any]],
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    """Multi-camera tracking: identity must survive the hand-off between cameras.

    Scored globally — a predicted identity is expected to cover the same person in
    *every* camera, so a system that tracks perfectly within each view but fails to
    link across them scores badly here while looking excellent per camera. That
    difference is the whole point of the metric.
    """
    per_camera: dict[str, TrackingResult] = {}
    cameras = sorted({r.get("camera", "cam") for r in gt_rows})
    for cam in cameras:
        per_camera[cam] = evaluate_mot(
            [r for r in gt_rows if r.get("camera", "cam") == cam],
            [r for r in pred_rows if r.get("camera", "cam") == cam],
            iou_threshold,
        )

    # Global pass: frames are made unique per camera so identities must be
    # consistent across the whole rig, not merely within a view.
    def globalise(rows):
        return [{**r, "frame": f"{r.get('camera', 'cam')}:{r['frame']}"} for r in rows]

    gt_g = [{**r, "frame": hash(f"{r.get('camera','cam')}:{r['frame']}") % 10**9}
            for r in globalise(gt_rows)]
    pred_g = [{**r, "frame": hash(f"{r.get('camera','cam')}:{r['frame']}") % 10**9}
              for r in globalise(pred_rows)]
    overall = evaluate_mot(gt_g, pred_g, iou_threshold)

    return {
        "overall": overall.as_dict(),
        "per_camera": {c: r.as_dict() for c, r in per_camera.items()},
        "mean_single_camera_idf1": round(
            float(np.mean([r.idf1 for r in per_camera.values()])) if per_camera else 0.0, 4),
        # A large gap means identities are lost at hand-off, not within views.
        "handoff_gap": round(
            float(np.mean([r.idf1 for r in per_camera.values()]) - overall.idf1)
            if per_camera else 0.0, 4),
    }


# --------------------------------------------------------------------- ReID


@dataclass
class ReidResult:
    rank1: float
    rank5: float
    map_score: float
    n_queries: int
    scope: str = "all"
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"scope": self.scope, "rank1": round(self.rank1, 4),
                "rank5": round(self.rank5, 4), "mAP": round(self.map_score, 4),
                "n_queries": self.n_queries, **self.extra}


def evaluate_reid(
    query_ids: Sequence[Any],
    gallery_ids: Sequence[Any],
    similarity: np.ndarray,
    exclude: np.ndarray | None = None,
    scope: str = "all",
) -> ReidResult:
    """Standard closed-set ReID scoring from a query-by-gallery similarity matrix."""
    q = np.asarray(query_ids)
    g = np.asarray(gallery_ids)
    sim = np.asarray(similarity, dtype=float)
    if sim.size == 0:
        return ReidResult(0.0, 0.0, 0.0, 0, scope)

    r1 = r5 = 0.0
    aps: list[float] = []
    valid = 0
    for i in range(len(q)):
        scores = sim[i].copy()
        if exclude is not None:
            scores[exclude[i]] = -np.inf
        order = np.argsort(-scores)
        order = order[np.isfinite(scores[order])]
        if len(order) == 0:
            continue
        hits = (g[order] == q[i]).astype(int)
        if hits.sum() == 0:
            continue
        valid += 1
        r1 += float(hits[0])
        r5 += float(hits[:5].any())
        cum = np.cumsum(hits)
        precision = cum / (np.arange(len(hits)) + 1)
        aps.append(float((precision * hits).sum() / hits.sum()))

    n = max(valid, 1)
    return ReidResult(r1 / n, r5 / n, float(np.mean(aps)) if aps else 0.0, valid, scope)


def reid_by_epoch(
    features: np.ndarray,
    uids: Sequence[Any],
    epochs: Sequence[int],
    camera_ids: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Score re-identification within an appearance epoch and across a change.

    This split is the point of the whole simulator. Within an epoch, clothing
    colour alone nearly solves the task. Across an appearance change it is
    actively misleading, and only shape, height or gait survive. Reporting one
    averaged number hides exactly the failure a disguise is designed to cause.
    """
    feats = np.asarray(features, dtype=float)
    feats = feats / np.maximum(np.linalg.norm(feats, axis=1, keepdims=True), 1e-9)
    sim = feats @ feats.T
    uid_arr = np.asarray(uids)
    epoch_arr = np.asarray(epochs)
    n = len(uid_arr)

    self_mask = np.eye(n, dtype=bool)
    same_id = uid_arr[:, None] == uid_arr[None, :]
    same_ep = epoch_arr[:, None] == epoch_arr[None, :]
    if camera_ids is not None:
        cam = np.asarray(camera_ids)
        same_camera = cam[:, None] == cam[None, :]
    else:
        same_camera = np.zeros((n, n), dtype=bool)

    # Distractors from *other* identities must stay in the gallery, or the task is
    # trivial. Only the positives belonging to the other regime are removed, so
    # each score answers exactly one question.
    within = evaluate_reid(
        uid_arr, uid_arr, sim,
        exclude=self_mask | same_camera | (same_id & ~same_ep),
        scope="within_epoch")
    across = evaluate_reid(
        uid_arr, uid_arr, sim,
        exclude=self_mask | (same_id & same_ep),
        scope="cross_epoch")

    drop = within.rank1 - across.rank1
    return {
        "within_epoch": within.as_dict(),
        "cross_epoch": across.as_dict(),
        "rank1_drop_across_appearance_change": round(drop, 4),
        "interpretation": (
            "a large drop means the model is reading clothing, not identity; "
            "shape, height and gait are what survive a change of appearance"
        ),
    }
