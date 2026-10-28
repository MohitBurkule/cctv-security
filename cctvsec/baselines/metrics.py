"""COCO mAP via pycocotools, with MOT ignore regions mapped to `iscrowd`."""
from __future__ import annotations

import contextlib
import io
from collections.abc import Sequence
from typing import Any


def coco_map(images: Sequence[Any], gt: dict[Any, list[dict]], ignore: dict[Any, list[dict]],
             preds: dict[Any, list[dict]]) -> dict[str, float]:
    """images: keys; gt/ignore/preds map key -> rows with xywh `bbox` (+ `score`)."""
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    idx = {k: i + 1 for i, k in enumerate(images)}
    anns, dets = [], []
    for k, i in idx.items():
        for crowd, rows in ((0, gt.get(k, [])), (1, ignore.get(k, []))):
            for r in rows:
                x, y, w, h = map(float, r["bbox"])
                anns.append({"id": len(anns) + 1, "image_id": i, "category_id": 1, "bbox": [x, y, w, h],
                             "area": w * h, "iscrowd": crowd})
        for r in preds.get(k, []):
            dets.append({"image_id": i, "category_id": 1, "bbox": list(map(float, r["bbox"])),
                         "score": float(r["score"])})
    if not anns or not dets:
        return {"AP": 0.0, "AP50": 0.0, "AP75": 0.0, "AR100": 0.0}
    with contextlib.redirect_stdout(io.StringIO()):
        g = COCO()
        g.dataset = {"images": [{"id": i} for i in idx.values()], "annotations": anns,
                     "categories": [{"id": 1, "name": "person"}]}
        g.createIndex()
        d = g.loadRes(dets)
        e = COCOeval(g, d, "bbox")
        e.params.maxDets = [1, 10, 1000]   # MOT20 frames hold >100 people
        e.evaluate(); e.accumulate()
    # Read the arrays directly: summarize() hard-codes maxDets=100 for AP, which
    # would silently cap recall on crowded frames. [T, R, K, A, M], area=all, M=1000.
    prec = e.eval["precision"][:, :, 0, 0, -1]
    rec = e.eval["recall"][:, 0, 0, -1]

    def _m(a):
        a = a[a > -1]
        return float(a.mean()) if a.size else 0.0
    return {"AP": _m(prec), "AP50": _m(prec[0]), "AP75": _m(prec[5]), "AR_max": _m(rec)}
