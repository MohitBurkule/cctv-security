"""H64 PTZ-tour timing simulator: fast invariants."""
import copy
import itertools
from pathlib import Path

import numpy as np
import yaml

from cctvsec.experiments import RUNNERS
from cctvsec.experiments import patrol_timing as P

CFG = yaml.safe_load(Path("cctvsec/experiments/configs/h64_patrol_timing.yaml").read_text())
W = CFG["world"]


def test_registered():
    assert RUNNERS["patrol_timing"] == "patrol_timing"


def test_fixed_tour_period_and_random_never_repeats_preset():
    f = P.tour("fixed", np.random.default_rng(0), W)
    assert all(abs((b[1] - a[1]) - 22.0) < 1e-9 for a, b in itertools.pairwise(f))
    r = P.tour("random", np.random.default_rng(0), W)
    assert all(a[0] != b[0] for a, b in itertools.pairwise(r))
    assert all(10.0 <= t1 - t0 <= 30.0 for _, t0, t1 in r)


def test_timed_attacker_beats_fixed_tour_by_construction():
    for s in range(50):
        iv = P.tour("fixed", np.random.default_rng(s), W)
        st = P.timed_start(iv, 2, 700.0, 3)
        assert not P.caught(iv, 2, st, 15.0, 2.0)          # min return gap 112 s > 16 s


def test_caught_needs_overlap():
    iv = [(0, 100.0, 120.0)]
    assert P.caught(iv, 0, 110.0, 10.0, 2.0) and not P.caught(iv, 0, 119.0, 10.0, 2.0)
    assert not P.caught(iv, 1, 110.0, 10.0, 2.0)


def test_calibration_and_small_summary():
    c = copy.deepcopy(CFG)
    c.update(n_calibration=200, worlds_per_block=40, n_blocks=2, n_boot=50)
    c["_tau"] = P.calibrate_tau(c)
    assert c["_tau"] > W["cross_s"][1]
    rows = P._block_job((0, c)) + P._block_job((1, c))
    r = P.summarise(rows, c)
    assert set(r["decision"]) == {"T1", "T2", "T3", "fa", "met"}
    assert r["catch"]["fixed/timed3"]["mean"] == 0.0
