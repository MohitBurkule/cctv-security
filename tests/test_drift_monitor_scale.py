import numpy as np

from cctvsec.experiments import RUNNERS
from cctvsec.experiments import drift_monitor_scale as dm


def test_registered():
    assert RUNNERS["drift_monitor_scale"] == "drift_monitor_scale"


def test_diurnal_mean_one_ratio_two():
    m = dm.diurnal({"day_hours": [7, 19], "day_night_ratio": 2.0})
    assert abs(m.mean() - 1) < 1e-12 and abs(m.max() / m.min() - 2) < 1e-12


def test_daily_invisible_to_diurnal_by_construction():
    m = dm.diurnal({"day_hours": [7, 19], "day_night_ratio": 2.0})
    assert np.allclose(m.reshape(7, 24).sum(1), 24)


def test_cusum_flags_step_and_resets():
    x = np.array([[0] * 10 + [10] * 10], float)
    f = dm.cusum_flags(x, np.array([[2.0]]), np.array([15.0]))
    assert not f[0, :10].any() and f[0].sum() >= 2


def test_analytic_monotone_and_null_rate():
    a = [dm.analytic_daily(5.0, d, 0.001)["det48"] for d in (1.25, 1.5, 2.0, 3.0)]
    assert all(np.diff(a) > 0) and a[-1] > 0.99
    assert dm.analytic_daily(5.0, 1.5, 0.001)["null_ff_site_week"] < 0.007


def test_cusum_h_hits_target_week_fa():
    rng = np.random.default_rng(0)
    lam = np.full((2, dm.H), 5.0)
    k = dm.cusum_k(np.array([5.0, 5.0]), 1.5)[:, None]
    h = dm.cusum_h(lam, k, 2000, 0.05, rng)
    x = rng.poisson(np.full((2000, dm.H), 5.0))
    f = dm.cusum_flags(x, np.full((2000, 1), k[0, 0]), np.full(2000, h[0]))
    assert abs(f.any(1).mean() - 0.05) < 0.02
