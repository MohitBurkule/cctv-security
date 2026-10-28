"""H69 runner statistics on synthetic inputs (no GPU, no sites)."""
import json

import numpy as np

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments.site_generalisation import (
    between_sd,
    calibrate_theta,
    hard_negative,
    match_frame,
    ols_adj_r2,
    recall_boot,
    scan_sites,
    split_transfer,
)


def test_registered():
    assert RUNNERS["site_generalisation"] == "site_generalisation"
    assert load_config("h69_site_generalisation")["runner"] == "site_generalisation"


def test_match_frame_threshold_and_iou():
    gt = np.array([[0, 0, 10, 20], [50, 0, 10, 20]], float)
    det = np.array([[0, 0, 10, 20, 0.9], [100, 0, 10, 20, 0.8], [50, 0, 10, 20, 0.1]], float)
    assert match_frame(gt, det, 0.25) == (2, 1, 1)
    assert match_frame(gt, det, 0.05) == (2, 2, 1)
    assert match_frame(gt, np.zeros((0, 5)), 0.25) == (2, 0, 0)


def test_between_sd_zero_when_sites_identical_and_positive_when_not():
    rng = np.random.default_rng(0)
    n = np.full(30, 10)
    same = [recall_boot(n, rng.binomial(10, 0.7, 30), rng, 500) for _ in range(12)]
    r = np.array([s[0] for s in same]); w = np.array([np.var(s[1]) for s in same])
    assert between_sd(r, w) < 0.03                         # the hard-negative situation: noise only
    diff = [recall_boot(n, rng.binomial(10, p, 30), rng, 500) for p in np.linspace(0.2, 0.9, 12)]
    r = np.array([s[0] for s in diff]); w = np.array([np.var(s[1]) for s in diff])
    assert between_sd(r, w) > 0.15


def test_calibrate_theta_smallest_within_budget():
    th = np.array([0.1, 0.2, 0.3])
    fp = np.array([10.0, 3.0, 0.0])                          # FP summed over 100 frames
    assert calibrate_theta(fp, 100, th, 1800.0) == 0.2  # 3/100*36000 = 1080 <= 1800
    assert calibrate_theta(np.array([99.0, 99.0, 99.0]), 100, th, 1.0) == 0.3


def test_split_transfer_homogeneous_sites_always_within():
    th = np.round(np.arange(0.05, 0.96, 0.01), 4)
    fp = np.tile(np.clip(1.0 - th, 0, None) * 0.2, (30, 1))   # same FP curve everywhere
    tables = [{"fp": fp, "n_gt": np.ones(30)} for _ in range(10)]
    r = split_transfer(tables, th, 3600.0, 50, np.random.default_rng(1))
    assert r["within_frac"] == 1.0 and r["theta_at_min_frac"] == 0.0


def test_ols_adj_r2_recovers_linear_signal():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(20, 3))
    y = X @ [0.3, -0.2, 0.1] + rng.normal(0, 0.01, 20)
    r = ols_adj_r2(X, y)
    assert r["adj_r2"] > 0.95 and r["loo_r2"] > 0.9
    assert ols_adj_r2(X, rng.normal(size=20))["adj_r2"] < 0.5


def test_hard_negative_can_fail():
    rng = np.random.default_rng(3)
    sites = [{"name": "a", "type": "t"}, {"name": "b", "type": "t"}, {"name": "c", "type": "u"}]
    reps = {"a": rng.normal(0.5, 0.02, 500), "b": rng.normal(0.5, 0.02, 500), "c": rng.normal(0.9, 0.02, 500)}
    assert hard_negative(sites, reps, {"a": 0.5, "b": 0.5, "c": 0.9})["passes"]
    reps["b"] = rng.normal(0.9, 0.02, 500)
    assert not hard_negative(sites, reps, {"a": 0.5, "b": 0.9, "c": 0.9})["passes"]


def test_scan_sites_filters_gate_and_licence(tmp_path):
    for name, gate, ok in [("00_a_s1", "PASS: 0 failed of 13 checks", True),
                           ("01_a_s2", "FAIL: 1 failed of 13 checks -> x", True),
                           ("02_a_s3", "PASS: 0 failed of 13 checks", False)]:
        d = tmp_path / name
        (d / "set" / "render" / "cam_00").mkdir(parents=True)
        for i in range(30):
            (d / "set" / "render" / "cam_00" / f"{i:04d}.png").write_bytes(b"")
        (d / "site.json").write_text(json.dumps({"type": "a", "seed": 1, "camera": "cam_00", "tod": "day", "people": 3}))
        (d / "gate.txt").write_text("hdr\n---\n" + gate + "\n")
        (d / "set" / "licences.json").write_text(json.dumps({"commercial_ml_ok": ok}))
    use, excl = scan_sites(tmp_path)
    assert [u["name"] for u in use] == ["00_a_s1"] and len(excl) == 2
