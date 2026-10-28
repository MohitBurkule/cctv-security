import numpy as np

from cctvsec.experiments import RUNNERS, load_config
from cctvsec.experiments import tracker_config_transfer as t


def test_registered_and_grid_size():
    assert RUNNERS["tracker_config_transfer"] == "tracker_config_transfer"
    cfg = load_config("h71_tracker_config_transfer")
    g = t.grid(cfg)
    assert len(g) == 24
    assert len({t.cfg_label(c) for c in g}) == 24


def test_identical_rankings_transfer_and_hard_negative_can_fail():
    cfg = load_config("h71_tracker_config_transfer")
    configs = t.grid(cfg)
    rng = np.random.default_rng(0)
    base = np.array([0.3 + 0.02 * c["w"] - 0.05 * c["match_iou"] + 0.01 * c["max_lost_s"]
                     + 0.03 * c["high"] for c in configs])
    R = base + rng.normal(0, 1e-4, (5, 24))
    Q = base + rng.normal(0, 1e-4, (4, 24))
    a = t.analyse(R, Q, configs, n_boot=50)
    assert a["rho"] > 0.99 and a["regret"] < 1e-3
    assert a["decision"] == {"D1_rho": True, "D2_regret": True}
    # high transfers here, so the "does not transfer" prediction must be reported as failed
    assert a["hard_negative"]["prediction_held"] is False


def test_regret_and_flipped_knob():
    assert t.regret([1, 0, 0], [0.1, 0.5, 0.2]) == 0.4
    configs = t.grid(load_config("h71_tracker_config_transfer"))
    r = np.array([c["high"] for c in configs], float)
    m_r, m_q = t.marginal(r, configs, "high"), t.marginal(-r, configs, "high")
    assert m_r["preferred"] == 0.6 and m_q["preferred"] == 0.4
