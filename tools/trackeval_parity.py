"""M1: parity of cctvsec.eval.tracking.evaluate_mot vs the reference TrackEval.

CPU only. Cases: three synthetic edge cases, the docs/13 MOT20 subset (cached
YOLO detections -> numpy ByteTrack, exactly `baselines.run.eval_mot`), and a
batch_v8 day GT vs a seeded perturbation of itself (no cached tracker output
exists for batch_v8). With `--old REV` also scores the implementation at git
revision REV to report the before-fix deltas.

    python tools/trackeval_parity.py --out out/experiments/m1_trackeval_parity [--old be9f52a]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cctvsec.eval.motchallenge import (
    add_false_positives,
    drop_fraction,
    jitter_boxes,
    parse_mot_rows,
    swap_identities,
)
from cctvsec.eval.trackeval_bridge import run_trackeval, write_motchallenge
from cctvsec.eval.tracking import TrackingResult, evaluate_mot

KEYS = ("hota", "deta", "assa", "hota_at_05", "mota", "motp", "idf1", "idp", "idr",
        "id_switches", "fragmentations", "misses", "false_positives")


def _box(x):
    return [float(x), 10.0, 20.0, 40.0]


def edge_cases() -> dict[str, tuple[list, list]]:
    """Empty frames, an ID switch, and fragmentation (with jittered boxes)."""
    gt = ([{"frame": f, "id": 1, "bbox": _box(0)} for f in (1, 2, 3, 8, 9, 10)]
          + [{"frame": f, "id": 2, "bbox": _box(100)} for f in (1, 2, 9, 10)])
    pr = ([{"frame": f, "id": 7, "bbox": _box(2)} for f in (1, 2, 3, 8, 9)]
          + [{"frame": f, "id": 8, "bbox": _box(105)} for f in (1, 10)]
          + [{"frame": 5, "id": 9, "bbox": _box(300)}])
    out = {"empty_frames": (gt, pr)}
    gt = [{"frame": f, "id": g, "bbox": _box(x)} for f in range(1, 21) for g, x in ((1, 0), (2, 50))]
    pr = [{"frame": f, "id": (10 if f <= 10 else 11) if g == 1 else (11 if f <= 10 else 10),
           "bbox": _box(x + f % 3)} for f in range(1, 21) for g, x in ((1, 0), (2, 50))]
    out["id_switch"] = (gt, pr)
    gt = [{"frame": f, "id": 1, "bbox": _box(f)} for f in range(1, 31)]
    pr = [{"frame": f, "id": 1 if f < 10 or f >= 20 else 2, "bbox": _box(f + (8 if f % 7 == 0 else 1))}
          for f in range(1, 31) if f not in (10, 11, 20)]
    pr += [{"frame": f, "id": 50, "bbox": _box(500)} for f in (10, 11, 20)]
    out["fragmentation"] = (gt, pr)
    return out


def mot20_subset(manifest="out/datasets/mot20_sub",
                 dets="out/datasets/mot20_sub/baselines/detections.json") -> dict[str, tuple[list, list]]:
    """Same GT/ignore/track inputs `baselines.run.eval_mot` scores (tracker on CPU)."""
    from cctvsec.baselines.bytetrack import track_sequence
    from cctvsec.baselines.run import _drop_ignored, _gt, _sequences
    from survsim.datasets.build import load_manifest

    m = load_manifest(ROOT / manifest)
    raw = json.loads((ROOT / dets).read_text())
    d = {k: {int(f): v for f, v in x.items()} for k, x in raw.items()}
    out = {}
    for run, cam, c in _sequences(m):
        key = f"{run['name']}/{cam}"
        frames = sorted(int(f) for f in c["frames"])
        tracks = track_sequence(d[key], frames, max_lost=int(c["fps"]))
        gt, ignore = _gt(m, c)
        out[run["name"]] = (gt, _drop_ignored(tracks, ignore))
    return out


def batch_v8_day(scn="out/batch_v8/street_crowd_day/gt") -> dict[str, tuple[list, list]]:
    out = {}
    for p in sorted((ROOT / scn).glob("mot_cam_*.txt")):
        gt = parse_mot_rows(p.read_text().splitlines(), is_ground_truth=True)
        if not gt:
            continue
        pr = jitter_boxes(drop_fraction(gt, 0.15, seed=1), 4.0, seed=2)
        ids = sorted({r["id"] for r in gt}, key=str)
        if len(ids) >= 2:
            mid = sorted({r["frame"] for r in gt})[len({r["frame"] for r in gt}) // 2]
            pr = swap_identities(pr, ids[0], ids[1], at_frame=mid)
        pr = add_false_positives(pr, max(1, len(gt) // 20), seed=3)
        out[f"v8day_{p.stem}"] = (gt, pr)
    return out


def load_old(rev: str):
    src = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{rev}:cctvsec/eval/tracking.py"], text=True)
    mod = types.ModuleType("old_tracking")
    sys.modules["old_tracking"] = mod
    exec(compile(src.replace("from .detection", "from cctvsec.eval.detection"), "old_tracking", "exec"),  # noqa: S102
         mod.__dict__)
    return mod.evaluate_mot


OURS_FIELDS = frozenset(TrackingResult.__dataclass_fields__)


def score(group: dict[str, tuple[list, list]], old=None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        write_motchallenge(Path(tmp), group)
        te = run_trackeval(Path(tmp))
    res = {}
    for name, (g, p) in group.items():
        res[name] = {"trackeval": te[name], "ours": {k: evaluate_mot(g, p).__dict__[k] for k in KEYS}}
        if old:
            res[name]["old"] = {k: old(g, p).__dict__[k] for k in KEYS}
    if len(group) > 1:   # concatenation (disjoint frames/ids) == TrackEval's COMBINED
        allg, allp = [], []
        for n, (g, p) in enumerate(group.values()):
            off = (n + 1) * 10_000_000
            allg += [{**r, "frame": r["frame"] + off, "id": f"{n}:{r['id']}"} for r in g]
            allp += [{**r, "frame": r["frame"] + off, "id": f"{n}:{r['id']}"} for r in p]
        # Only keys evaluate_mot defines: the bridge also emits bridge-only
        # summaries (deta_mean/assa_mean, added in 2fdecd6) with no counterpart.
        c = {k: v for k, v in te["COMBINED"].items() if k in OURS_FIELDS and k != "fragmentations"}
        res["COMBINED"] = {"trackeval": c, "ours": {k: evaluate_mot(allg, allp).__dict__[k] for k in c}}
        if old:
            res["COMBINED"]["old"] = {k: old(allg, allp).__dict__[k] for k in c}
    for r in res.values():
        for impl in ("ours", "old"):
            if impl in r:
                r[f"delta_{impl}"] = {k: r[impl][k] - v for k, v in r["trackeval"].items() if k in r[impl]}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/experiments/m1_trackeval_parity")
    ap.add_argument("--old", default=None, help="git rev of the pre-fix implementation")
    a = ap.parse_args()
    old = load_old(a.old) if a.old else None
    out = {name: score(fn(), old) for name, fn in
           (("edge", edge_cases), ("mot20_sub", mot20_subset), ("batch_v8_day", batch_v8_day))}
    od = ROOT / a.out
    od.mkdir(parents=True, exist_ok=True)
    (od / "results.json").write_text(json.dumps(out, indent=1, default=float))
    for grp, res in out.items():
        for seq, r in res.items():
            for impl in ("old", "ours"):
                d = r.get(f"delta_{impl}")
                if d is not None:
                    worst = max(d, key=lambda k: abs(d[k]))
                    print(f"{grp:13s} {seq:22s} {impl:4s} max|d|={abs(d[worst]):.3g} ({worst})  "
                          + " ".join(f"{k}={d[k]:+.4g}" for k in ("hota", "deta", "assa", "mota", "idf1")))


if __name__ == "__main__":
    main()
