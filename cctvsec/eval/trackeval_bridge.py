"""Bridge to the reference TrackEval (JonathonLuiten/TrackEval) for parity checks.

`write_motchallenge` lays our MOT rows (`frame`, `id`, `bbox` xywh) out in
TrackEval's MOTChallenge folder structure; `run_trackeval` scores that layout
with the official `Evaluator` + `HOTA`/`CLEAR`/`Identity` metrics, preprocessing
off (our callers already drop ignore regions / non-pedestrian GT themselves, so
both implementations must see identical boxes). TrackEval is an optional
dependency — import errors propagate to the caller.
"""

from __future__ import annotations

import configparser
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

BENCH = "SURVSIM"
TRACKER = "ours"


def _ids(rows: Sequence[dict[str, Any]]) -> dict[Any, int]:
    return {k: i + 1 for i, k in enumerate(sorted({r["id"] for r in rows}, key=str))}


def write_motchallenge(root: Path, seqs: Mapping[str, tuple[Sequence[dict], Sequence[dict]]]) -> Path:
    """Write `{name: (gt_rows, pred_rows)}` as TrackEval MOTChallenge layout under `root`.

    Frames are shifted so the earliest frame of each sequence becomes 1; ids are
    re-indexed to positive integers (TrackEval needs ints; mapping is 1:1 so no
    metric changes).
    """
    root = Path(root)
    gt_dir = root / "gt" / f"{BENCH}-train"
    tr_dir = root / "trackers" / f"{BENCH}-train" / TRACKER / "data"
    tr_dir.mkdir(parents=True, exist_ok=True)
    (root / "gt" / "seqmaps").mkdir(parents=True, exist_ok=True)
    for name, (gt, pred) in seqs.items():
        frames = [int(r["frame"]) for r in (*gt, *pred)]
        f0 = min(frames) if frames else 1
        n = (max(frames) - f0 + 1) if frames else 1
        sd = gt_dir / name
        (sd / "gt").mkdir(parents=True, exist_ok=True)
        ini = configparser.ConfigParser()
        ini.optionxform = str
        ini["Sequence"] = {"name": name, "seqLength": str(n), "frameRate": "25",
                           "imWidth": "1920", "imHeight": "1080"}
        with open(sd / "seqinfo.ini", "w") as fh:
            ini.write(fh)
        for rows, path, gt_file in ((gt, sd / "gt" / "gt.txt", True), (pred, tr_dir / f"{name}.txt", False)):
            idm = _ids(rows)
            lines = []
            for r in sorted(rows, key=lambda r: (int(r["frame"]), idm[r["id"]])):
                x, y, w, h = (float(v) for v in r["bbox"])
                tail = "1,1,1" if gt_file else "1,-1,-1,-1"
                lines.append(f"{int(r['frame']) - f0 + 1},{idm[r['id']]},{x!r},{y!r},{w!r},{h!r},{tail}")
            path.write_text("\n".join(lines) + ("\n" if lines else ""))
    (root / "gt" / "seqmaps" / f"{BENCH}-train.txt").write_text("name\n" + "".join(f"{s}\n" for s in seqs))
    return root


def run_trackeval(root: Path) -> dict[str, dict[str, float]]:
    """Score a `write_motchallenge` layout; returns {seq|'COMBINED': metrics}."""
    import numpy as np

    # TrackEval master still uses the aliases NumPy 1.24 removed; restore them
    # (they were exact synonyms, so behaviour is unchanged).
    for alias, typ in (("float", float), ("int", int), ("bool", bool)):
        if alias not in np.__dict__:
            setattr(np, alias, typ)
    import trackeval

    root = Path(root)
    ecfg = trackeval.Evaluator.get_default_eval_config()
    ecfg.update({"USE_PARALLEL": False, "PRINT_RESULTS": False, "PRINT_CONFIG": False,
                 "OUTPUT_SUMMARY": False, "OUTPUT_DETAILED": False, "PLOT_CURVES": False,
                 "PRINT_ONLY_COMBINED": True, "TIME_PROGRESS": False, "DISPLAY_LESS_PROGRESS": True})
    dcfg = trackeval.datasets.MotChallenge2DBox.get_default_dataset_config()
    dcfg.update({"GT_FOLDER": str(root / "gt"), "TRACKERS_FOLDER": str(root / "trackers"),
                 "BENCHMARK": BENCH, "SPLIT_TO_EVAL": "train", "DO_PREPROC": False,
                 "TRACKERS_TO_EVAL": [TRACKER], "PRINT_CONFIG": False})
    ev = trackeval.Evaluator(ecfg)
    ds = trackeval.datasets.MotChallenge2DBox(dcfg)
    mets = [trackeval.metrics.HOTA(), trackeval.metrics.CLEAR({"PRINT_CONFIG": False, "THRESHOLD": 0.5}),
            trackeval.metrics.Identity({"PRINT_CONFIG": False, "THRESHOLD": 0.5})]
    res, _ = ev.evaluate([ds], mets)
    out: dict[str, dict[str, float]] = {}
    for seq, cls in res["MotChallenge2DBox"][TRACKER].items():
        r = cls["pedestrian"]
        h, c, i = r["HOTA"], r["CLEAR"], r["Identity"]
        out["COMBINED" if seq == "COMBINED_SEQ" else seq] = {
            "hota": float(np.mean(h["HOTA"])), "deta": float(h["DetA"][9]),
            "assa": float(h["AssA"][9]), "hota_at_05": float(h["HOTA"][9]),
            "deta_mean": float(np.mean(h["DetA"])), "assa_mean": float(np.mean(h["AssA"])),
            "mota": float(c["MOTA"]), "motp": float(c["MOTP"]),
            "id_switches": int(c["IDSW"]), "fragmentations": int(c["Frag"]),
            "misses": int(c["CLR_FN"]), "false_positives": int(c["CLR_FP"]),
            "idf1": float(i["IDF1"]), "idp": float(i["IDP"]), "idr": float(i["IDR"]),
        }
    return out
