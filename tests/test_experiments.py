"""cctvsec.experiments: metric helpers and config plumbing (no GPU, no model, no renders)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cctvsec.experiments import available, load_config
from cctvsec.experiments.common import _label_lines, ap50_by_height, match_frame, recall_by_height
from cctvsec.experiments.farfield import tiles
from cctvsec.experiments.reid import kmeans, nmi, protocols, purity


def _scene(seed=0, n_frames=30):
    rng = np.random.default_rng(seed)
    keys, G, P = [], {}, {}
    for f in range(n_frames):
        k = ("s", f)
        keys.append(k)
        gt = [{"bbox": [float(x), 50.0, h / 2.5, float(h)]} for x, h in
              zip(rng.uniform(0, 1500, 6), rng.uniform(15, 300, 6))]
        G[k] = gt
        pr = []
        for g in gt:
            if rng.random() < 0.8:   # detected, jittered
                b = np.array(g["bbox"]) + rng.normal(0, 0.06 * g["bbox"][3], 4) * [1, 1, 0.3, 0.3]
                pr.append({"bbox": b.tolist(), "score": float(rng.uniform(0.3, 1))})
        pr += [{"bbox": [float(rng.uniform(0, 1500)), 400.0, 30.0, 80.0], "score": float(rng.uniform(0, 0.6))}
               for _ in range(2)]
        P[k] = pr
    return keys, G, P


def test_numpy_ap50_all_band_agrees_with_pycocotools():
    pytest.importorskip("pycocotools")
    from cctvsec.baselines.metrics import coco_map
    keys, G, P = _scene()
    ref = coco_map(keys, G, {}, P)["AP50"]
    ours = ap50_by_height(keys, G, {}, P, bands=[(0, 100), (100, 1e9)])
    assert ours["all"]["AP50"] == pytest.approx(ref, abs=0.01)
    assert ours["0-100"]["n"] + ours["100+"]["n"] == ours["all"]["n"]


def test_banded_ap_is_one_for_perfect_predictions():
    keys, G, _ = _scene()
    P = {k: [{"bbox": g["bbox"], "score": 1.0} for g in v] for k, v in G.items()}
    r = ap50_by_height(keys, G, {}, P, bands=[(0, 60), (60, 1e9)])
    assert r["all"]["AP50"] == pytest.approx(1.0) and r["0-60"]["AP50"] == pytest.approx(1.0)


def test_recall_by_height_counts_and_ignore():
    G = {1: [{"bbox": [0, 0, 10, 30]}, {"bbox": [100, 0, 40, 100]}]}
    P = {1: [{"bbox": [100, 0, 40, 100], "score": 0.9}, {"bbox": [300, 0, 10, 30], "score": 0.9}]}
    r = recall_by_height(G, P, bands=[(0, 50), (50, 1e9)])
    assert r["recall"] == 0.5 and r["fp"] == 1
    assert r["recall_by_height"]["0-50"]["recall"] == 0.0
    r2 = recall_by_height(G, P, bands=[(0, 50), (50, 1e9)], ignore_by_key={1: [{"bbox": [300, 0, 10, 30]}]})
    assert r2["fp"] == 0


def test_match_frame_is_one_to_one():
    g = np.array([[0, 0, 10, 10]], float)
    p = np.array([[0, 0, 10, 10], [0, 0, 10, 10]], float)
    gm, pm = match_frame(g, p, np.array([0.5, 0.9]))
    assert gm.all() and pm.tolist() == [False, True]


def test_yolo_labels_clip_and_drop_tiny():
    rows = [{"bbox": [-10, 10, 20, 40]}, {"bbox": [5, 5, 2, 2]}]
    lines = _label_lines(rows, 100, 100)
    assert len(lines) == 1
    c, cx, _cy, w, _h = map(float, lines[0].split())
    assert c == 0 and cx == pytest.approx(0.05) and w == pytest.approx(0.10)


def test_tiles_cover_the_frame():
    ts = tiles(1280, 720, 512, 384, 0.2)
    cover = np.zeros((720, 1280), bool)
    for x, y, w, h in ts:
        assert x + w <= 1280 and y + h <= 720
        cover[y:y + h, x:x + w] = True
    assert cover.all()


def test_cluster_metrics():
    X = np.concatenate([np.random.default_rng(0).normal(m, 0.05, (20, 2)) for m in (0, 5)])
    lab = np.array(["a"] * 20 + ["b"] * 20)
    cl = kmeans(X, 2, seed=0)
    assert purity(cl, lab) == 1.0 and nmi(cl, lab) == pytest.approx(1.0)


def test_reid_protocols_are_disjoint_views():
    items = [{"camera": c, "condition": d, "frame": f, "fps": 10}
             for c, d, f in [("A", "day", 1), ("A", "day", 100), ("B", "day", 1), ("A", "night", 100)]]
    P = protocols(items)
    pick = lambda w: next(v for k, v in P.items() if k.startswith(w))
    cam, time_, light = pick("cross_camera"), pick("cross_time"), pick("cross_lighting")
    # query 0: cross-camera gallery = {2}; cross-time = {1}; cross-lighting = {3}
    assert np.where(~cam[0])[0].tolist() == [2]
    assert np.where(~time_[0])[0].tolist() == [1]
    assert np.where(~light[0])[0].tolist() == [3]


def test_all_configs_load_and_name_a_runner():
    from cctvsec.experiments import RUNNERS
    names = available()
    assert {"h1_sim2real", "h2_degradation", "h3_farfield", "h4_reid", "h5_alarms"} <= set(names)
    for n in names:
        cfg = load_config(n)
        assert cfg["runner"] in RUNNERS and cfg.get("hypothesis")


def test_rpath_expands_path_variables(monkeypatch):
    from cctvsec.experiments.common import REPO, rpath
    monkeypatch.delenv("SURVSIM_MOT20_SUBSET", raising=False)
    assert rpath("$SURVSIM_MOT20_SUBSET/manifest.json") == REPO / "out/datasets/mot20_sub/manifest.json"
    monkeypatch.setenv("SURVSIM_MOT20_SUBSET", "/data/x")
    assert rpath("${SURVSIM_MOT20_SUBSET}/manifest.json") == Path("/data/x/manifest.json")


def test_configs_reference_no_session_scratch_paths():
    for n in available():
        text = Path(load_config(n)["_config_path"]).read_text()
        assert "/tmp/" not in text and "scratchpad" not in text, n


def test_box_agreement_offsets():
    from cctvsec.experiments.diagnose import box_agreement, summarise
    gt = np.array([[100, 100, 50, 100], [400, 400, 20, 40]], float)
    pred = np.array([[100, 110, 50, 100]], float)   # same box shifted down 10 % of height
    r = box_agreement(gt, pred)
    assert r[0]["d_top"] == pytest.approx(0.1) and r[0]["d_bottom"] == pytest.approx(0.1)
    assert r[0]["h_ratio"] == pytest.approx(1.0) and r[1]["iou"] == 0.0
    s = summarise(r)
    assert s["n_matched"] == 1 and s["frac_unmatched_lt_0.3"] == 0.5


# ------------------------------------------------------------------ H9-H11

def _dets_stream(seed=0, n=40):
    rng = np.random.default_rng(seed)
    out = {}
    for f in range(1, n + 1):
        out[f] = [{"bbox": [10 + 3 * f + rng.normal(0, 2), 50, 20, 60], "score": float(rng.uniform(0.2, 0.9))},
                  {"bbox": [200 - 2 * f + rng.normal(0, 2), 55, 22, 58], "score": float(rng.uniform(0.2, 0.9))},
                  {"bbox": [rng.uniform(0, 300), rng.uniform(0, 100), 15, 40], "score": float(rng.uniform(0.1, 0.7))}]
    return out


def test_bytetrack_default_path_is_the_original_algorithm():
    """Default ByteTracker == explicit original parameters (high 0.5, no gate)."""
    from cctvsec.baselines.bytetrack import track_sequence
    d = _dets_stream()
    a = track_sequence(d, sorted(d))
    b = track_sequence(d, sorted(d), high=0.5, gate=False)
    assert a == b and len(a) > 0


def test_bytetrack_fixed_flag_sets_tau_and_gate():
    from cctvsec.baselines.bytetrack import ByteTracker
    t = ByteTracker(fixed=True)
    assert t.high == 0.6 and t.gate
    t = ByteTracker()
    assert t.high == 0.5 and not t.gate


def test_gate_before_solve_prefers_valid_pair():
    """Hungarian on raw -IoU can take a sub-threshold pair; gating first must not."""
    from cctvsec.baselines.bytetrack import _match

    class T:
        def __init__(self, box):
            self.kf = type("K", (), {"xywh": box})()
    # track0 overlaps det0 strongly and det1 weakly; track1 overlaps only det0 moderately.
    tracks = [T([0, 0, 10, 10]), T([4, 0, 10, 10])]
    boxes = [[1, 0, 10, 10], [8.5, 0, 10, 10]]
    m_old, _, _ = _match(tracks, boxes, 0.3)
    m_new, _, _ = _match(tracks, boxes, 0.3, gate=True)
    assert len(m_new) >= len(m_old)
    assert all(i in (0, 1) for i, _ in m_new)


def test_stats_helpers():
    from cctvsec.experiments.tracking import boot_ci, holm, wilson
    c = boot_ci([1.0, 1.0, 1.0])
    assert c["mean"] == 1.0 and c["lo"] == 1.0 and c["hi"] == 1.0
    w = wilson(5, 10)
    assert w["lo"] < 0.5 < w["hi"]
    assert wilson(0, 0)["p"] is None
    h = holm({"a": 0.01, "b": 0.04})
    assert h == {"a": True, "b": True}
    assert holm({"a": 0.03, "b": 0.04}) == {"a": False, "b": False}


def test_reid_ranks_excludes_and_counts():
    from cctvsec.experiments.reid_epochs import ranks
    ids = np.array(["a", "a", "b", "b"])
    sim = np.array([[1, .9, .1, .1], [.9, 1, .1, .1], [.1, .1, 1, .8], [.1, .1, .8, 1]], float)
    eye = np.eye(4, dtype=bool)
    h, ap, _q = ranks(ids, sim, eye)
    assert h.tolist() == [1, 1, 1, 1] and np.allclose(ap, 1)
    # excluding every positive leaves no valid query
    h, _, _ = ranks(ids, sim, eye | (ids[:, None] == ids[None]))
    assert len(h) == 0


def test_ir_scale_follows_render_width(tmp_path):
    """batch_v7 renders are 1280 or 1920 wide; a fixed 2/3 scale silently broke H11's first run."""
    import cv2

    from cctvsec.experiments.night import _ir_scale
    for w, h in ((1920, 1080), (1280, 720)):
        p = tmp_path / f"{w}.png"
        cv2.imwrite(str(p), np.zeros((h, w, 3), np.uint8))
        assert abs(_ir_scale(p, {"ir_width": 1280}) - 1280 / w) < 1e-9


# ------------------------------------------------------------------ H12-H14 helpers

def test_garwood_and_rule_of_three_match_report_49():
    from cctvsec.experiments.inference import garwood, rule_of_three
    assert rule_of_three(3000) == pytest.approx(0.000999, rel=1e-3)
    _lo, hi = garwood(1, 3000)
    assert hi == pytest.approx(0.0019, abs=5e-5)     # 49 §5 table: 3,000 cam-h with 1 FA
    assert garwood(0, 10)[0] == 0.0


def test_permutation_and_spearman():
    from cctvsec.experiments.inference import permutation_p, spearman
    assert permutation_p([0, 0, 0], [1, 1, 1]) == pytest.approx(0.1)   # 2 of C(6,3)=20
    assert permutation_p([1, 2, 3], [1, 2, 3]) == 1.0
    s = spearman([1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1], n_boot=200, n_perm=2000)
    assert s["rho"] == -1.0 and s["perm_p"] < 0.01


def test_fast_path_loiter_and_zones_equal_reference():
    """alarm_scale's vectorised zone lookup and cheaper p90 must not change a single alarm."""
    import pandas as pd

    from cctvsec.eval.rules import PathLoiterRule
    from cctvsec.experiments import alarm_scale as S
    cfg = {"duration_s": 120.0, "fps": 5.0}
    sc = S._compose_valid(S._site_spec(1, 5, cfg, [])).scenario
    sc.population.hero = []
    rng = np.random.default_rng(0)
    ppl = S.innocent_people(sc.environment, rng, 15,
                            {"transit": 1, "commute_wait": 1, "smoke_break": 1, "phone_stop": 1, "queue": 1},
                            {"commute_wait": [20, 60], "queue": [20, 60], "phone_stop": [20, 60],
                             "smoke_break": [30, 90]})
    sc.population.warmup_s = 60.0
    df, w = S._simulate(sc, [p for p, _ in ppl])
    ref = [w.zone_of(np.array([x, y])) for x, y in zip(df.x, df.y)]
    assert list(df.zone) == ref
    zones = sc.model_dump(mode="json")["environment"]["zones"]
    roles = {a.uid: a.spec.role for a in w.roster.values()}
    for thr in (15, 25):
        rule = {"name": "p", "kind": "path", "threshold_s": thr, "radius_m": 4, "reentry_gap_s": 15}
        slow = sorted(a.t for a in PathLoiterRule(threshold_s=thr, radius_m=4, reentry_gap_s=15).run(
            pd.DataFrame(df), zones, roles))
        fast = sorted(a["t"] for a in S._rule_alarms(rule, df, zones, roles))
        assert slow == fast and len(slow) > 0


def test_h12_to_h14_configs_load():
    for n in ("h12_alarm_scale", "h13_realism_transfer", "h14_dose"):
        cfg = load_config(n)
        assert cfg["runner"] in ("alarm_scale", "realism_transfer", "dose")
    assert len(load_config("h14_dose")["arms"]) == 35


# ------------------------------------------------------------------ H15 / label-geometry regressions

def _fake_run(root, run="r", cam="cam_a", raw_wh=(1920, 1080), deg_wh=(1280, 720)):
    import cv2
    rd = root / run
    for sub, (w, h) in (("render", raw_wh), ("video/degraded", deg_wh)):
        d = rd / sub / cam
        d.mkdir(parents=True)
        cv2.imwrite(str(d / "0001.png"), np.zeros((h, w, 3), np.uint8))
    (rd / "gt" / "amodal").mkdir(parents=True)
    # visible box, and an amodal box with visibility 0.2 for a second id
    (rd / "gt" / f"mot_{cam}.txt").write_text("1,1,960,540,96,216,1,1,1.0\n1,2,100,100,50,60,1,1,0.9\n")
    (rd / "gt" / "amodal" / f"mot_{cam}.txt").write_text("1,1,960,540,96,216,1,1,1.0\n1,2,100,100,50,150,1,1,0.2\n")
    return rd


def test_synth_labels_follow_image_size_not_a_fixed_1280(tmp_path):
    """1920x1080 raw renders were normalised by 1280x720 (and degraded 1280x720 frames got
    1920-pixel GT) -- every disguise gate/ptz/sub label in H1-H14 was wrong."""
    from cctvsec.experiments.detection import _synth_candidates
    _fake_run(tmp_path)
    for src, (w, h) in (("raw", (1920, 1080)), ("degraded", (1280, 720))):
        (_name, _png, rows, _s, wh), = _synth_candidates(tmp_path, ["r"], [{"source": src, "stride": 1}])
        assert wh == (w, h)
        line = _label_lines(rows[:1], *wh)[0].split()
        assert [float(v) for v in line[1:]] == pytest.approx([0.525, 0.6, 0.05, 0.2], abs=1e-6)


def test_gt_subdir_and_min_vis(tmp_path):
    from cctvsec.experiments.detection import _synth_candidates
    _fake_run(tmp_path)
    spec = {"source": "raw", "stride": 1}
    vis = _synth_candidates(tmp_path, ["r"], [spec])[0][2]
    amo = _synth_candidates(tmp_path, ["r"], [{**spec, "gt_subdir": "amodal"}])[0][2]
    flt = _synth_candidates(tmp_path, ["r"], [{**spec, "gt_subdir": "amodal", "min_vis": 0.3}])[0][2]
    assert vis[1]["bbox"][3] == 60 and amo[1]["bbox"][3] == 150
    assert [r["id"] for r in flt] == [1]


def test_h17_paired_signflip_and_contrasts():
    from cctvsec.experiments.tracking_transfer import contrasts, paired
    r = paired([0.1, 0.2, 0.3], [0.2, 0.3, 0.4])
    assert r["mean_diff"] == 0.1 and r["signflip_p"] == 0.25 and r["n"] == 3
    m = {k: 0.0 for k in ("hota", "deta", "assa", "mota", "idf1", "id_switches")}
    res = {"arms": {f"a_s{s}": dict(m) for s in (0, 1)} | {f"b_s{s}": {**m, "hota": 0.1 + s} for s in (0, 1)}}
    c = contrasts(res, {"contrasts": [["a", "b"]], "seeds": [0, 1, 2]})
    assert c[0]["seeds"] == [0, 1] and c[0]["hota"]["diffs"] == [0.1, 1.1]


def test_h18_contrasts_pair_by_seed_and_treat_zero_shot_as_constant():
    from cctvsec.experiments.farreal import contrasts

    def rec(ap):
        return {"eval": {"x0.25/full_640": {"ap_by_height": {"all": {"AP50": ap}}}}}
    res = {"arms": {"zero_shot": rec(0.5), "r_s0": rec(0.4), "r_s1": rec(0.5),
                    "f_s0": rec(0.3), "f_s1": rec(0.3)}}
    c = contrasts(res, {"contrasts": [["r", "f"], ["zero_shot", "f"]], "seeds": [0, 1]})
    assert [x["diffs"] for x in c] == [[-0.1, -0.2], [-0.2, -0.2]]


def test_h17_h18_configs_load():
    from cctvsec.experiments import RUNNERS, load_config
    for n in ("h17_tracking_transfer", "h18_farreal_v2"):
        assert load_config(n)["runner"] in RUNNERS


def test_h20_pk_batches_triplet_and_id_bootstrap():
    import torch

    from cctvsec.experiments.reid_train import (
        batch_hard_triplet,
        paired_diff,
        pk_batches,
        summarise,
    )
    y = np.array([0] * 10 + [1] * 2 + [2] * 6)
    for b in pk_batches(y, P=2, K=4, rng=np.random.default_rng(0)):
        assert len(b) == 8 and len(set(y[b])) == 2 and all((y[b] == c).sum() == 4 for c in set(y[b]))
    f = torch.tensor([[0., 0], [0, .1], [5, 5], [5, 5.1]])
    lab = torch.tensor([0, 0, 1, 1])
    assert float(batch_hard_triplet(f, lab, 0.3)) == 0.0          # well separated
    assert float(batch_hard_triplet(f, torch.tensor([0, 1, 0, 1]), 0.3)) > 0
    a = {"x": {"ap": .2, "r1": 0, "n": 3}, "y": {"ap": .4, "r1": 1, "n": 1}}
    b = {"x": {"ap": .3, "r1": 1, "n": 3}, "y": {"ap": .6, "r1": 1, "n": 1}, "z": {"ap": 1, "r1": 1, "n": 1}}
    d = paired_diff(a, b)
    assert d["n_ids"] == 2 and abs(d["mean"] - 0.15) < 1e-9 and d["boot95"][0] >= 0.1 - 1e-9
    s = summarise(a)
    assert s["n_queries"] == 4 and abs(s["mAP"] - 0.25) < 1e-9 and abs(s["mAP_id_mean"] - 0.3) < 1e-9


def test_h19_h20_configs_load():
    from cctvsec.experiments import RUNNERS, load_config
    c = load_config("h19_farreal_v3")
    assert c["runner"] in RUNNERS and {a["name"] for a in c["arms"]} >= {"v6_syn_s0", "v8_syn_s2", "v8_mix1280_s1"}
    assert all(s.get("batch_dir") == "out/batch_v6" for a in c["arms"] if a["name"].startswith("v6")
               for s in a["train"]["synthetic"])
    c = load_config("h20_reid_train")
    assert c["runner"] in RUNNERS and not set(c["train_runs"]) & set(c["test_runs"])
    assert not {w for w in c["train_runs"].values()} & {w for w in c["test_runs"].values()}   # held out by scene


def test_h22_operator_queue_matching_twin_floor_and_queue():
    from cctvsec.experiments.operator_queue import (
        add_twin_floor,
        model_metrics,
        simulate,
        tag_alarms,
    )
    truth = [{"t_start": 10.0, "actors": ["a"]}, {"t_start": 12.0, "actors": ["b"]}]
    # wrong person in window is not a hit; late alarm is not a hit; repeat keeps its event
    assert tag_alarms(truth, [(15.0, "c"), (20.0, "b"), (25.0, "a"), (26.0, "a"), (50.0, "a")]) == [-1, 1, 0, 0, -1]
    worlds = [{"mode": "recall", "camera_hours": 1.0, "n_truth": 2,
               "arms": {"A1": [[20.0, 0.9, 1], [25.0, 0.95, 0], [30.0, 0.2, -1]]}},
              {"mode": "clean", "camera_hours": 10.0, "n_truth": 0,
               "arms": {"A1": [[float(t), s, -1] for t, s in zip(range(0, 1000, 100), np.linspace(0.1, 1, 10))]}}]
    m = model_metrics(worlds, "A1")
    assert m["recall"] == 1.0 and m["fa_per_cam_h"] == 1.0
    add_twin_floor(worlds, 0.3)
    assert model_metrics(worlds, "twin_floor")["fa_per_cam_h"] == pytest.approx(0.3)
    assert len(worlds[0]["arms"]["twin_floor"]) == 2          # the low-score recall-world FP is thinned
    op = {"cameras": 1, "review_s": 30.0, "review_cv": 0.01, "shift_h": 8, "fatigue_after_h": 8,
          "fatigue_review_x": 1.0, "miss": 0.0, "miss_fatigued": 0.0, "bulk_ack_queue": 100,
          "horizons_s": [30, 300]}
    r = simulate(worlds[:1], "A1", "fifo", 0, op)
    # alarms at 20 (ev1) and 25 (ev0): FIFO takes 20 at once, 25 waits ~25 s -> both within 30 s
    assert r["per_world"]["30"] == [2.0] and r["per_world"]["300"] == [2.0]
    # queue capacity 0 extra: bulk-ack drops the second alarm
    r2 = simulate(worlds[:1], "A1", "fifo", 0, {**op, "bulk_ack_queue": 0})
    assert r2["bulk_acks"] >= 1 and r2["per_world"]["300"][0] < 2


def test_h45_operator_points_multi_operator_and_config():
    import yaml

    from cctvsec.experiments.operator_queue import _paired, simulate
    worlds = [{"mode": "recall", "camera_hours": 1.0, "n_truth": 3,
               "arms": {"x": [[10.0, 0.9, 0], [10.5, 0.8, 1], [11.0, 0.7, 2]]}}]
    op = {"cameras": 1, "review_s": 30.0, "review_cv": 0.01, "shift_h": 8, "fatigue_after_h": 8,
          "fatigue_review_x": 1.0, "miss": 0.0, "miss_fatigued": 0.0, "bulk_ack_queue": 100,
          "horizons_s": [30, 300]}
    one = simulate(worlds, "x", "fifo", 0, op)
    three = simulate(worlds, "x", "fifo", 0, {**op, "operators": 3})
    assert one["per_world"]["30"] == [2.0]            # third alarm waits ~60 s with one operator
    assert three["per_world"]["30"] == [3.0]          # three operators take all three at once
    assert three["utilisation"] == pytest.approx(one["utilisation"] / 3, rel=0.05)
    assert simulate(worlds, "x", "fifo", 0, {**op, "operators": 1}) == one   # H22 default unchanged
    d = _paired(np.array([[1.0, 0.0]]), np.array([[1.0, 1.0]]), np.array([1.0, 1.0]), np.array([0, 1]), 0)
    assert d["diff"] == 0.5 and d["seeds_positive"] == 1
    cfg = yaml.safe_load(Path("cctvsec/experiments/configs/h45_operator_points.yaml").read_text())
    h22 = yaml.safe_load(Path("cctvsec/experiments/configs/h22_operator_queue.yaml").read_text())
    assert cfg["operator"] == h22["operator"] and cfg["operator_seeds"] == h22["operator_seeds"]
    assert cfg["operating_points"] == {"A1": 0.95, "pooled": 0.90, "conformal": 0.962851}
    assert "operating_points" not in h22


def test_h25_label_noise_is_paired_nested_and_analysed():
    from cctvsec.experiments.detection import inject_label_noise
    from cctvsec.experiments.label_noise import analyse, cell_name
    rows = [{"bbox": [10.0 * i, 20.0, 30.0, 90.0]} for i in range(200)]
    items = [("a", None, rows, "raw", (1920, 1080))]
    assert inject_label_noise(items, 0.0, 0.0, 3)[0][2] == rows
    d10 = inject_label_noise(items, 0.0, 0.10, 3)[0][2]
    j10 = inject_label_noise(items, 0.10, 0.10, 3)[0][2]
    assert 160 < len(d10) < 195 and len(j10) == len(d10)                # same boxes dropped at every jitter
    assert [r["bbox"][0] for r in d10] != [r["bbox"][0] for r in j10]
    dh = np.array([r["bbox"][3] - 90 for r in inject_label_noise(items, 0.05, 0.0, 3)[0][2]])
    assert 0.03 * 90 < dh.std() < 0.1 * 90                            # two y edges, sigma 5 % of h
    cfg = {"primary_key": "k", "seeds": [0, 1, 2], "jitter_sigmas": [0.0, 0.02, 0.05, 0.10], "drops": [0.0],
           "min_clean_gain": 0.002}
    ap = {0.0: 0.51, 0.02: 0.508, 0.05: 0.506, 0.10: 0.503}
    arms = {f"real_only_s{s}": {"eval": {"k": {"AP": 0.50 + 0.001 * s}}} for s in range(3)}
    arms |= {f"{cell_name(g, 0)}_s{s}": {"eval": {"k": {"AP": v + 0.001 * s}}} for g, v in ap.items() for s in range(3)}
    a = analyse({"arms": arms}, cfg)
    assert a["testable"] and a["branch"] == "supported" and a["cells"]["j10_d00"]["retained"] == pytest.approx(0.3)


def test_h33_conformal_theta_core():
    from cctvsec.experiments.conformal_theta import (
        choose_crc,
        choose_plain,
        counts_at,
        decide,
        heldout_fa,
    )
    peaks = [np.array([0.2, 0.6, 0.9]), np.array([0.5]), np.array([])]
    camh = np.array([1.0, 1.0, 2.0])
    assert counts_at(peaks, [0.5, 0.95]).tolist() == [[2, 0], [1, 0], [0, 0]]
    # plug-in: pooled FA/cam-h <= 0.5 needs <= 2 alarms over 4 cam-h -> θ = 0.6
    assert choose_plain(peaks, camh, 0.5) == 0.6
    # CRC is at least as conservative as the plug-in, and infeasible when B/(n+1) > α
    c = choose_crc(peaks, camh, 0.5)
    assert c["B"] == 3.0 and c["floor"] == 0.75 and not c["feasible"] and c["theta"] > 1.0
    many = peaks * 20
    c2 = choose_crc(many, np.tile(camh, 20), 0.5)
    assert c2["feasible"] and c2["theta"] >= choose_plain(many, np.tile(camh, 20), 0.5)
    h = heldout_fa(peaks, camh, 0.55)
    assert h["fa"] == 2 and h["fa_per_cam_h"] == 0.5 and h["garwood95"][0] < 0.5 < h["garwood95"][1]
    assert decide(1, 3) == "supported" and decide(3, 9) == "refuted" and decide(2, 5) == "inconclusive"


def test_h33b_fixed_B_mode_real():
    from cctvsec.experiments.conformal_theta import choose_crc, decide_h33b, fixed_B
    peaks = [np.array([0.2, 0.6, 0.9]), np.array([0.5]), np.array([])] * 20
    camh = np.tile([1.0, 1.0, 2.0], 20)
    with pytest.raises(ValueError):
        choose_crc(peaks, camh, 0.5, mode="real")          # B must be given in advance
    emp = choose_crc(peaks, camh, 0.5)
    assert emp["mode"] == "empirical" and emp["B"] == 3.0   # old default unchanged
    fx = choose_crc(peaks, camh, 0.5, B=5.0, mode="real")
    assert fx["B"] == 5.0 and fx["n_clipped"] == 0 and fx["theta"] >= emp["theta"]
    cl = choose_crc(peaks, camh, 0.5, B=2.0, mode="real")  # losses above B are clipped and counted
    assert cl["n_clipped"] == 20
    assert fixed_B({"arrivals_per_min_max": 6.0, "duration_s": 1800, "min_camera_hours": 2.0,
                    "tail": 1e-6}) == 123.5
    assert decide_h33b(0, -0.006, True) == "supported" and decide_h33b(1, 0.0, True) == "refuted"
    assert decide_h33b(0, -0.03, True) == "partial"


def test_h45b_config_extends_h45_and_fixed_B_docstring_is_honest():
    """AUDIT_H33B: H45b adds exactly one point (the H33b certified θ) to H45's unchanged config, and
    fixed_B's per-visitor cap is documented as an unenforced assumption (A1 alarms per dwell episode)."""
    import yaml

    from cctvsec.experiments import conformal_theta
    h45 = yaml.safe_load(Path("cctvsec/experiments/configs/h45_operator_points.yaml").read_text())
    b = yaml.safe_load(Path("cctvsec/experiments/configs/h45b_operator_points_fixedB.yaml").read_text())
    assert b["operator"] == h45["operator"] and b["operator_seeds"] == h45["operator_seeds"]
    assert b["operating_points"] == {**h45["operating_points"], "conformal_fixedB": 0.963436}
    assert b["paired_extra"] == ["conformal_fixedB", "conformal"]
    assert "not enforced" in conformal_theta.fixed_B.__doc__


def test_h32_night_profiles_helpers_and_config():
    import yaml

    from cctvsec.experiments import CONFIG_DIR, RUNNERS
    from cctvsec.experiments.night_profiles import STATS, cluster_boot, in_band, split_real
    cfg = yaml.safe_load((CONFIG_DIR / "h32_night_profiles.yaml").read_text())
    assert RUNNERS[cfg["runner"]] == "night_profiles"
    assert cfg["targets"]["cctv_night_lowlight"] == ["vis", 9]
    assert cfg["targets"]["cctv_thermal"] == ["ir", 8]
    # tune/hold-out split is by sorted name and disjoint
    from pathlib import Path
    t, h = split_real([Path(f"{i:02d}.jpg") for i in (3, 1, 2, 0, 4)], 3)
    assert [p.stem for p in t] == ["00", "01", "02"] and [p.stem for p in h] == ["03", "04"]
    assert len(STATS) == 13
    real = {k: {"p10": 0.0, "p90": 1.0} for k in STATS}
    ib = in_band(real, {**{k: 0.5 for k in STATS}, "luma_mean": 2.0, "cast_a": 0.0})
    assert sum(ib.values()) == 12 and not ib["luma_mean"] and ib["cast_a"]   # inclusive edges
    per_cam = {"a": {"raw": (8, 10), "x": (4, 10)}, "b": {"raw": (5, 10), "x": (5, 10)}}
    r = cluster_boot(per_cam, ["raw", "x"], "raw", n=500)
    assert r["raw"]["recall"] == 0.65 and r["x"]["recall"] == 0.45
    assert r["x"]["delta_vs_raw"]["d"] == -0.2 and r["raw"]["delta_vs_raw"]["d"] == 0.0
    assert r["x"]["lo"] <= 0.45 <= r["x"]["hi"]


def test_h26_fixed_step_schedule_and_padding(tmp_path):
    import yaml

    from cctvsec.experiments.common import rpath
    from cctvsec.experiments.detection import pad_train_list
    from cctvsec.experiments.dose_fixedstep import schedule
    cfg = yaml.safe_load(rpath("cctvsec/experiments/configs/h26_dose_fixedstep.yaml").read_text())
    for a in cfg["arms"]:
        n = 300 + a["train"].get("synthetic_limit", 0)
        L = a["train"].get("pad_to", n)
        assert L >= n and L * a["train_opts"]["epochs"] // 8 == 450          # same optimiser steps
        assert L * a["train_opts"]["warmup_epochs"] == pytest.approx(1800)   # 225 warm-up iterations
    assert schedule(1300, 3600, 225, 8) == {"epochs": 2, "list_len": 1800, "pad": 500, "steps": 450,
                                            "warmup_epochs": 1.0}
    for i in range(10):
        for d, ext in (("images", ".png"), ("labels", ".txt")):
            p = tmp_path / d / "train" / f"x{i}{ext}"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(i))
    assert pad_train_list(tmp_path, 15, 0) == 5
    assert len(list((tmp_path / "labels" / "train").iterdir())) == 15


def test_h51_equal_steps_config_and_paired_holm():
    import yaml

    from cctvsec.experiments.common import rpath
    from cctvsec.experiments.dose_fixedstep import paired_contrasts
    cfg = yaml.safe_load(rpath("cctvsec/experiments/configs/h51_equal_steps.yaml").read_text())
    h26 = yaml.safe_load(rpath("cctvsec/experiments/configs/h26_dose_fixedstep.yaml").read_text())
    assert cfg["train"] == h26["train"] and cfg["seeds"] == list(range(10))
    names = {a["name"] for a in cfg["arms"]}
    assert all(f"dose{d}_s{s}" in names for d in (0, 100, 300) for s in range(10))
    assert {f"v7dose100_s{s}" for s in range(5)} <= names and len(names) == 35
    for a in cfg["arms"]:
        n = 300 + a["train"].get("synthetic_limit", 0)
        assert n * a["train_opts"]["epochs"] // 8 == 450
        assert n * a["train_opts"]["warmup_epochs"] == pytest.approx(1800)
        syn = a["train"].get("synthetic") or []
        assert all(x.get("batch_dir", cfg["batch_dir"]) == ("out/batch_v7" if a["name"].startswith("v7")
                                                            else "out/batch_v8") for x in syn)
    ev = lambda ap: {"eval": {"k": {"AP": ap, "AP50": ap, "AP75": ap}}}
    arms = {f"a_s{s}": ev(0.5) for s in range(4)}
    arms |= {f"b_s{s}": ev(0.51) for s in range(4)} | {f"c_s{s}": ev(0.5 + (0.01 if s % 2 else -0.01)) for s in range(4)}
    out = paired_contrasts({"arms": arms}, {"primary_key": "k", "seeds": [0, 1, 2, 3],
                                           "primary_contrasts": [["a", "b"], ["a", "c"]]})
    assert out[0]["AP"]["signflip_p"] == pytest.approx(0.125) and out[0]["holm_p"] == pytest.approx(0.25)
    assert out[1]["holm_p"] == 1.0 and not out[0]["holm_reject_at_0.05"]


def test_h38_quant_export_core():
    from cctvsec.experiments import load_config
    from cctvsec.experiments.quant_export import (
        ARMS,
        decide,
        evenly_spaced,
        head_decode_nodes,
        paired_summary,
    )

    assert evenly_spaced(list(range(10)), 3) in ([0, 4, 9], [0, 5, 9])
    assert evenly_spaced([1, 2], 5) == [1, 2]
    nodes = [("/model.22/cv2.0/cv2.0.0/conv/Conv", "Conv"), ("/model.22/cv2.0/cv2.0.0/act/Mul", "Mul"),
             ("/model.22/dfl/Softmax", "Softmax"), ("/model.22/dfl/conv/Conv", "Conv"),
             ("/model.22/Concat_3", "Concat"), ("/model.21/Concat", "Concat")]
    assert head_decode_nodes(nodes) == ["/model.22/dfl/Softmax", "/model.22/Concat_3"]
    s = paired_summary([0.5, 0.5, 0.5], [0.49, 0.495, 0.5])
    assert s["loss"] == [0.01, 0.005, 0.0] and s["max"] == 0.01 and s["ci95"][0] <= s["mean"] <= s["ci95"][1]
    cfg = load_config("h38_quant_export")
    assert cfg["runner"] == "quant_export" and len(cfg["checkpoints"]) == 3
    ap = {"fp32_torch": [0.50, 0.50, 0.50], "onnx_fp32": [0.50, 0.5005, 0.50],
          "onnx_fp16": [0.499, 0.50, 0.496], "int8_real": [0.49, 0.488, 0.486],
          "int8_syn": [0.47, 0.475, 0.479]}
    d = decide(ap, cfg)
    assert d["reference"] == "fp32_torch" and d["fp16_met"] and d["int8_met"] and not d["calib_met"]
    ap["onnx_fp32"] = [0.49, 0.49, 0.49]           # broken export -> reference switches to ONNX FP32
    d = decide(ap, cfg)
    assert d["reference"] == "onnx_fp32" and "onnx_fp32" not in d["loss_vs_reference"]
    assert set(ARMS) >= set(d["loss_vs_reference"])


def test_h24_appearance_reranks_feasible_pairs_and_w0_is_control():
    """H24: w=0 ignores embeddings (control bit-identical); w>0 flips an IoU-preferred
    swap when appearance disagrees, but never accepts an IoU-infeasible pair."""
    import numpy as np

    from cctvsec.baselines.bytetrack import ByteTracker, _match, track_sequence
    from cctvsec.experiments import load_config
    from cctvsec.experiments.reid_assoc import gt_dets, two_way_boot

    rng = np.random.default_rng(0)
    dets = {f: [{"bbox": [float(x + 3 * f + rng.normal()), 0.0, 20.0, 40.0], "score": 0.9,
                 "emb": rng.normal(size=4)} for x in (0, 15, 200)] for f in range(1, 12)}
    strip = {f: [{k: v for k, v in d.items() if k != "emb"} for d in ds] for f, ds in dets.items()}
    assert track_sequence(strip, range(1, 12)) == track_sequence(dets, range(1, 12), app_weight=0.0)

    tr = ByteTracker(app_weight=1.0)
    tr.update([{"bbox": [0, 0, 20, 40], "score": 0.9, "emb": [1, 0]},
               {"bbox": [12, 0, 20, 40], "score": 0.9, "emb": [0, 1]}])
    ta, tb = tr.tracks
    boxes = [[10, 0, 20, 40], [1, 0, 20, 40]]       # det0 overlaps track A less than track B
    A = tr._app_cost([{"bbox": boxes[0], "emb": [1, 0]}, {"bbox": boxes[1], "emb": [0, 1]}])
    assert abs(A[0, 0]) < 1e-9 and abs(A[0, 1] - 1) < 1e-9
    m_iou, _, _ = _match([ta, tb], boxes, 0.2)
    m_app, _, _ = _match([ta, tb], boxes, 0.2, app=A, app_weight=1.0)
    assert sorted(m_iou) == [(0, 1), (1, 0)] and sorted(m_app) == [(0, 0), (1, 1)]
    far = [[500, 0, 20, 40], [1, 0, 20, 40]]          # det0 infeasible for both tracks
    m, _, left = _match([ta, tb], far, 0.2, app=A, app_weight=1.0)
    assert 0 in left and all(j != 0 for _, j in m)

    b = two_way_boot(np.full((2, 3), 0.1), n=200)
    assert b["mean"] == 0.1 and b["boot95"] == [0.1, 0.1]
    seq = {"frames": [1, 2], "gt": [{"frame": 1, "id": 1, "bbox": [0, 0, 10, 20]}]}
    assert gt_dets(seq, 0.05, 0) == gt_dets(seq, 0.05, 0)
    cfg = load_config("h24_reid_assoc")
    assert cfg["runner"] == "reid_assoc" and cfg["control"] == "bytetrack" and len(cfg["checkpoints"]) == 5


def test_h42_theta_policy_core():
    from cctvsec.experiments import load_config
    from cctvsec.experiments.theta_policy import FINE_GRID, decide, draws, pick, pool

    def g(th, clk, fa, tp):
        return {"theta": th, "clock": clk, "fa": fa, "cam_h": 1.0, "tp": tp, "truth": 10}

    lo = [g(0.9, 5.0, 5, 9), g(0.95, 5.0, 3, 8)]   # this fold: 0.95 misses the 0.85 floor
    hi = [g(0.9, 5.0, 5, 9), g(0.95, 5.0, 3, 9)]   # this fold: 0.95 qualifies
    assert pick(lo, (0.9, 0.95), 0.85)["theta"] == 0.9
    assert pick(hi, (0.9, 0.95), 0.85)["theta"] == 0.95
    assert pick(lo, (0.9, 0.95), 0.80)["theta"] == 0.95
    assert pool([lo, hi])[1] == {"theta": 0.95, "clock": 5.0, "fa": 6, "cam_h": 2.0, "tp": 17, "truth": 20}
    folds = [{"grid": lo, "peaks": [[0.5]], "camh": [1.0]}] * 3 + [{"grid": hi, "peaks": [[0.5]], "camh": [1.0]}] * 7
    pf = [d["theta"] for d in draws("per_fold", folds)]
    assert pf == [0.9] * 3 + [0.95] * 7
    # pooled LOFO: recall 0.87-0.88 at 0.95 in every draw -> no spread
    assert {d["theta"] for d in draws("pooled", folds)} == {0.95}
    assert len(FINE_GRID) == 15 and FINE_GRID[0] == 0.85 and FINE_GRID[-1] == 0.99
    fa = {"range": 2.0, "sd": 1.0}
    summ = {"per_fold": {"fa": fa, "recall_ge_080": 10, "modal": {"fa_per_cam_h": 5.0}},
            "pooled": {"fa": {"range": 0.0, "sd": 0.0}, "recall_ge_080": 10, "modal": {"fa_per_cam_h": 2.9}},
            "crc": {"fa": {"range": 0.5, "sd": 0.2}, "recall_ge_080": 8, "modal": {"fa_per_cam_h": 2.0}},
            "pooled_floor": {"fa": {"range": 1.5, "sd": 0.6}, "recall_ge_080": 10, "modal": {"fa_per_cam_h": 2.5}}}
    d = decide(summ)
    assert d["hypothesis_met"] and d["met_by"] == ["pooled"] and d["shipped_policy"] == "pooled"
    cfg = load_config("h42_theta_policy")
    assert cfg["runner"] == "theta_policy" and cfg["alpha"] == 2.915 and len(cfg["fold_seeds"]) == 10


def test_h52_ablation_config_modes_and_rule(tmp_path):
    import numpy as np
    import yaml

    from cctvsec.experiments.common import rpath
    from cctvsec.experiments.dose_fixedstep import (
        apply_synthetic_mode,
        h52_decision,
        mask_people,
        shuffle_labels,
    )
    cfg = yaml.safe_load(rpath("cctvsec/experiments/configs/h52_ablation.yaml").read_text())
    h51 = yaml.safe_load(rpath("cctvsec/experiments/configs/h51_equal_steps.yaml").read_text())
    assert cfg["train"] == h51["train"] and cfg["seeds"] == list(range(10))
    by = {a["name"]: a for a in h51["arms"]}
    names = {a["name"] for a in cfg["arms"]}
    assert names == {f"{g}_s{s}" for g in ("shuf300", "mask300", "dup") for s in range(10)}
    for a in cfg["arms"]:
        n = 60 * a["train"]["real"]["repeat"] + a["train"].get("synthetic_limit", 0)
        assert n * a["train_opts"]["epochs"] // 8 == 450 and n * a["train_opts"]["warmup_epochs"] == pytest.approx(1800)
        if a["name"].startswith(("shuf", "mask")):   # same 300 frames as H51 dose300 (paired by seed)
            ref = by[f"dose300_s{a['seed']}"]["train"]
            assert {k: v for k, v in a["train"].items() if k != "synthetic_mode"} == ref
    items = [(f"i{i}", None, [{"bbox": [10.0 * i, 0, 10, 20]}] * (i + 1), "raw", (100, 100)) for i in range(5)]
    items[0] = ("i0", None, items[0][2], "raw", (200, 50))
    sh = shuffle_labels(items, 3)
    assert all(len(s[2]) != len(o[2]) for s, o in zip(sh, items))           # derangement: nobody keeps own boxes
    assert sorted(len(s[2]) for s in sh) == [1, 2, 3, 4, 5] and sh == shuffle_labels(items, 3)
    img = np.full((60, 80, 3), 100, np.uint8)
    img[20:40, 30:40] = 250
    out = mask_people(img, [{"bbox": [30, 20, 10, 20]}], scale=1)
    assert out[30, 35].max() < 150 and (out[:10] == 100).all()
    import cv2
    p = tmp_path / "a.png"
    cv2.imwrite(str(p), img)
    m = apply_synthetic_mode([("a", p, [{"bbox": [30, 20, 10, 20]}], "raw", (80, 60))], "masked", 0, tmp_path / "c")
    assert m[0][2] == [] and m[0][1].is_file() and m[0][1] != p
    with pytest.raises(ValueError):
        apply_synthetic_mode(items, "bogus", 0, tmp_path)
    ev = lambda d, p: {"contrast": d + " (paired by seed)", "AP": {"mean_diff": p[0]}, "holm_p": p[1]}
    res = {"paired": [ev("dose300 - shuf300", (0.001, 0.6)), ev("shuf300 - dose0", (0.004, 0.01)),
                      ev("dose300 - dup", (0.005, 0.01))]}
    d = h52_decision(res, cfg["h52_rule"])
    assert d["selected"] == "image-level" and not d["rules"]["diversity-only"]


def test_h43_qat_core():
    """H43: recovery fraction, decision bars, config shape; H38 dispatch untouched."""
    import math

    from cctvsec.experiments import load_config
    from cctvsec.experiments.quant_export import H43_ARMS, decide_h43, recovery

    assert recovery(0.03, 0.015) == 0.5 and recovery(0.03, 0.0) == 1.0 and recovery(0.03, 0.04) < 0
    assert math.isnan(recovery(0.0, 0.01))
    cfg = load_config("h43_qat")
    assert cfg["runner"] == "quant_export" and cfg["mode"] == "h43" and len(cfg["checkpoints"]) == 5
    assert cfg["qat"]["iters"] <= 150 and cfg["qat"]["lr"] == 1.19e-5
    assert "mode" not in load_config("h38_quant_export")
    base = {"fp32_torch": 0.50, "int8_minmax": 0.488, "int8_percentile": 0.492, "int8_entropy": 0.49,
            "qat_fp32": 0.50, "int8_qat": 0.497}
    b75 = {"fp32_torch": 0.54, "int8_minmax": 0.51, "int8_percentile": 0.525, "int8_entropy": 0.52,
           "qat_fp32": 0.54, "int8_qat": 0.536}
    m = {"AP": {a: [base[a]] * 5 for a in H43_ARMS}, "AP50": {a: [0.83] * 5 for a in H43_ARMS},
         "AP75": {a: [b75[a]] * 5 for a in H43_ARMS}}
    d = decide_h43(m, cfg)
    assert d["recovery"]["AP75"]["int8_percentile"] == 0.5 and d["ptq_met"]
    assert d["recovery"]["AP75"]["int8_qat"] > 0.8 and d["qat_met"]
    m["AP"]["int8_qat"] = [0.497, 0.497, 0.497, 0.497, 0.494]     # one checkpoint over 0.005
    assert not decide_h43(m, cfg)["qat_met"]
