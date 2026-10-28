"""H33c (docs/research/32 §H33c): per-visitor alarm cap and capped conformal θ."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from cctvsec.experiments.conformal_theta import choose_crc, counts_at, decide_h33c, fixed_B

_spec = importlib.util.spec_from_file_location(
    "loiter_eval_h33c", Path(__file__).resolve().parents[1] / "tools" / "loiter_eval.py")
LE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LE)


def test_cap_per_uid_keeps_first_k_in_time_order():
    al = {0: [(30.0, "k", "a"), (10.0, "k", "a"), (20.0, "k", "b"), (40.0, "k", "a")]}
    assert LE.cap_per_uid(al, None) is al
    assert LE.cap_per_uid(al, 1)[0] == [(10.0, "k", "a"), (20.0, "k", "b")]
    assert LE.cap_per_uid(al, 2)[0] == [(10.0, "k", "a"), (20.0, "k", "b"), (30.0, "k", "a")]


def test_counts_at_cap_none_reproduces_uncapped():
    pk = [np.array([0.99, 0.97, 0.5, 0.96]), np.array([])]
    uid = [["a", "a", "b", "a"], []]
    th = [0.0, 0.96, 0.98]
    np.testing.assert_array_equal(counts_at(pk, th), counts_at(pk, th, uid, None))
    np.testing.assert_array_equal(counts_at(pk, th, uid, 1), [[2, 1, 1], [0, 0, 0]])
    np.testing.assert_array_equal(counts_at(pk, th, uid, 2), [[3, 2, 1], [0, 0, 0]])


def test_capped_loss_bounded_by_visitors_so_B_valid():
    rng = np.random.default_rng(0)
    peaks, uids, camh = [], [], []
    for _ in range(50):
        n = rng.integers(1, 40)
        u = [f"v{j}" for j in rng.integers(0, 10, n)]
        peaks.append(rng.uniform(0.8, 1.0, n)); uids.append(u); camh.append(2.0)
    L = counts_at(peaks, [0.0], uids, 1)[:, 0]
    assert (L <= np.array([len(set(u)) for u in uids])).all()
    B = fixed_B({"arrivals_per_min_max": 6.0, "duration_s": 1800, "min_camera_hours": 2.0, "tail": 1e-6})
    assert B == 123.5
    r = choose_crc(peaks, camh, 2.915, B=B, mode="real", uids=uids, cap=1)
    assert r["n_clipped"] == 0
    # capping can only make the CRC θ more permissive (lower or equal)
    assert r["theta"] <= choose_crc(peaks, camh, 2.915, B=B, mode="real")["theta"]


def test_decide_h33c():
    assert decide_h33c(0.3, -0.01, 0, 0) == "supported"
    assert decide_h33c(0.3, -0.01, 1, 0) == "refuted"
    assert decide_h33c(0.1, -0.01, 0, 0) == "partial"
    assert decide_h33c(0.3, -0.06, 0, 0) == "refuted"


def test_cap_per_uid_operator_stream_layout():
    # operator_queue.build_point_streams tuples are (t, uid, p)
    al = {3: [(5.0, "u", 0.97), (1.0, "u", 0.99), (2.0, "v", 0.96)]}
    assert LE.cap_per_uid(al, 1, uid_pos=1)[3] == [(1.0, "u", 0.99), (2.0, "v", 0.96)]


def test_top_per_uid_matches_bruteforce():
    from cctvsec.experiments.conformal_theta import top_per_uid
    rng = np.random.default_rng(1)
    pk = rng.uniform(size=60)
    u = [f"v{j}" for j in rng.integers(0, 7, 60)]
    th = np.linspace(0, 1, 41)
    for cap in (1, 2, 3):
        brute = sum(np.minimum(cap, (pk[np.array(u) == v][:, None] >= th).sum(0)) for v in set(u))
        s = np.sort(top_per_uid(pk, u, cap))
        np.testing.assert_array_equal(len(s) - np.searchsorted(s, th, side="left"), brute)
