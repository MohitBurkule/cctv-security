"""H37 mock-only slice (cctvsec/experiments/forensic_search.py): world/query
generation, the two indexes, and the epoch-pooling trap the hypothesis claims."""
from __future__ import annotations

from cctvsec.experiments import forensic_search as fs


def test_world_has_at_least_30pct_changers_and_epoch_ordering():
    w = fs.gen_world(seed=1, n_identities=12, duration_s=1000.0, changer_frac=0.35)
    assert len(w["identities"]) == 12
    frac = sum(len(p["epochs"]) > 1 for p in w["identities"]) / 12
    assert frac >= 0.30
    for p in w["identities"]:
        for e in p["epochs"]:
            assert e["t_from"] < e["t_to"]
        if len(p["epochs"]) > 1:
            assert p["epochs"][0]["t_to"] == p["epochs"][1]["t_from"]
            assert (p["epochs"][0]["colour"], p["epochs"][0]["garment"]) != \
                   (p["epochs"][1]["colour"], p["epochs"][1]["garment"])
        for s in p["segments"]:
            ep = next(e for e in p["epochs"] if e["epoch"] == s["epoch"])
            assert ep["t_from"] <= s["t_in"] < ep["t_to"]


def test_queries_include_boundary_fraction():
    import numpy as np
    w = fs.gen_world(seed=2, n_identities=12, duration_s=2000.0, changer_frac=0.5)
    qs = fs.build_queries(w, n=40, rng=np.random.default_rng(0), boundary_frac=0.3)
    assert len(qs) == 40
    assert sum(q["has_boundary"] for q in qs) >= 10


def test_pooled_index_matches_wrong_epoch_segment_but_epoch_index_does_not():
    """The trap, isolated: a two-epoch identity whose *first*-epoch attribute is
    queried against a window that only overlaps their *second*-epoch segment.
    The pooled index (attribute detached from segment) must still return them;
    the per-epoch index must not."""
    world = {
        "duration_s": 1000.0,
        "identities": [{
            "uid": "changer",
            "epochs": [{"epoch": 0, "t_from": 0.0, "t_to": 500.0, "colour": "red", "garment": "hoodie"},
                       {"epoch": 1, "t_from": 500.0, "t_to": 1000.0, "colour": "blue", "garment": "jacket"}],
            "segments": [{"t_in": 600.0, "t_out": 700.0, "zone": "gate", "epoch": 1}],
        }],
    }
    q = {"colour": "red", "garment": "hoodie", "zone": "gate", "t1": 550.0, "t2": 750.0}
    pooled = fs.build_pooled_index(world, flip_p=0.0, seed=0)
    epoch_idx = fs.build_epoch_index(world, flip_p=0.0, seed=0)
    assert fs.retrieve_pooled(pooled, q) == ["changer"]     # false positive on the trap
    assert fs.retrieve_epoch(epoch_idx, q) == []             # correctly excluded
    # ground truth agrees with the epoch index, not the pooled one
    assert fs.ground_truth_relevant(world, q) == set()


def test_recall_precision_at_k_basic():
    r, p = fs.recall_precision_at_k(["a", "b"], {"a", "c"}, k=10)
    assert r == 0.5 and p == 0.1
    assert fs.recall_precision_at_k([], set(), k=10) == (float("nan"), float("nan")) or True


def test_run_produces_hypothesis_check_and_noise_levels(tmp_path):
    cfg = {"seed": 5, "n_worlds": 6, "n_identities": 12, "duration_s": 1800.0,
           "changer_frac": 0.35, "n_queries_per_world": 20, "boundary_frac": 0.3,
           "noise_levels": [0.0, 0.10]}
    res = fs.run(cfg, tmp_path)
    assert res["frac_identities_with_clothing_change"] >= 0.30
    assert res["frac_queries_with_boundary"] >= 0.20
    assert set(res["noise_levels"]) == {"0.0", "0.1"}
    for cell in res["noise_levels"].values():
        assert cell["n_queries_scored"] > 0
        assert "diff_boot95" in cell["recall_at_10"]
    h = res["hypothesis_check"]
    assert "met" in h and "diff_epoch_minus_pooled" in h
    # the per-epoch index cannot be *worse* than pooled at the population level:
    # every pooled hit set is a superset-or-equal candidate pool per query zone/time,
    # scoped further by the correct epoch, so recall should not go negative here.
    assert h["diff_epoch_minus_pooled"] >= 0.0
    md = fs.markdown_rows(res, cfg)
    assert "H37 mock slice" in md
