"""H70 fast checks: calibration meets budgets in-sample (by construction), queue and drift monitor behave."""
import numpy as np

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments.alarm_budget_scale import calibrate, make_world, queue, run_scheme


def _small():
    cfg = load_config("h70_alarm_budget_scale")
    cfg.update(sites=6, week_h=48, drift_hour=24)
    return cfg


def test_registered():
    assert RUNNERS["alarm_budget_scale"] == "alarm_budget_scale"


def test_calibration_in_sample_budgets():
    cfg = _small()
    w = make_world(0, cfg, 0.6)
    cal = calibrate(w["cal"], cfg)
    B = cfg["budget"]
    assert cal["expected"]["a_pooled"].mean() <= B + 1e-9          # global budget, in-sample
    assert np.all(cal["expected"]["b_per_site"] <= B + 1e-9)       # every site, in-sample
    assert cal["expected"]["c_realloc"].mean() <= B + 1e-9
    assert np.ptp(cal["theta"]["a_pooled"]) == 0


def test_queue_bulk_ack_and_horizon():
    op = {"review_s": 30.0, "review_cv": 0.3, "miss": 0.0, "bulk_ack_per_op": 10}
    # one intrusion alone is reviewed in time
    assert queue(np.array([]), np.array([100.0]), 1, op, [0], 300.0, 1e4)["hits"] == 1
    # waiting behind one FA when a burst of 50 FAs arrives: bulk-ack clears it unseen
    assert queue(np.r_[99.0, np.full(50, 101.0)], np.array([100.0]), 1, op, [0], 300.0, 1e4)["hits"] == 0


def test_drift_site_is_flagged_per_site():
    cfg = _small()
    cfg["drift_x"] = 10.0
    w = make_world(1, cfg, 0.3)
    r = run_scheme(w, calibrate(w["cal"], cfg), "b_per_site", cfg)
    assert (1, w["drift"]) in r["flags"]
