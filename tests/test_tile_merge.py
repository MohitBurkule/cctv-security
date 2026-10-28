"""H3d merge strategies on synthetic boxes (no detector, no GPU)."""
import numpy as np
import pytest

from cctvsec.experiments import tile_merge as tm

CFG = {"merge": {"nms_iou": 0.5, "iom": 0.6, "wbf_iou": 0.55, "border_margin_px": 3, "border_iom": 0.5}}


def frame(full, tiles):
    rects = [(0, 0, 320, 240), (256, 0, 320, 240)]
    return {"full_640": np.array(full, float).reshape(-1, 5), "tiles": np.array(tiles, float).reshape(-1, 6),
            "rects": rects, "W": 576, "H": 240}


def test_nms_matches_torchvision():
    torch = pytest.importorskip("torch")
    from torchvision.ops import nms as tvn
    rng = np.random.default_rng(0)
    xy = rng.uniform(0, 100, (60, 2))
    B = np.concatenate([xy, xy + rng.uniform(5, 40, (60, 2)), rng.uniform(0, 1, (60, 1))], 1)
    ref = tvn(torch.tensor(B[:, :4]), torch.tensor(B[:, 4]), 0.5).numpy()
    assert sorted(tm.nms(B, 0.5)) == sorted(ref)


def test_plain_nms_keeps_fragment_iom_and_border_drop_it():
    # fragment 200..319 x 20..120 vs full box: IoU 0.457 < 0.5, IoM 1.0
    f = frame([[200, 20, 300, 220, 0.9]], [[200, 20, 319, 120, 0.8, 0], [100, 50, 110, 75, 0.7, 0]])
    assert len(tm.merge("a_nms05", f, CFG)) == 3          # fragment survives NMS 0.5
    assert len(tm.merge("b_nms_iom", f, CFG)) == 2
    assert len(tm.merge("d_tile_border", f, CFG)) == 2
    # the small far person (not on a tile edge, no full box) survives every strategy
    for s in ("a_nms05", "b_nms_iom", "c_wbf", "d_tile_border"):
        assert any(abs(b[0] - 100) < 1 for b in tm.merge(s, f, CFG))


def test_wbf_fuses_duplicates_weighted():
    B = np.array([[0, 0, 10, 10, 0.9], [1, 0, 11, 10, 0.3], [50, 50, 60, 60, 0.5]])
    F = tm.wbf(B, 0.55)
    assert len(F) == 2 and F[0, 4] == 0.9 and F[0, 0] == pytest.approx(0.25)


def test_border_rule_only_inner_edges():
    # box touching the image edge x=0 of tile 0 is not an inner-edge touch
    assert not tm.touches_inner_edge(np.array([0, 10, 50, 100]), (0, 0, 320, 240), 576, 240, 3)
    assert tm.touches_inner_edge(np.array([200, 10, 319, 100]), (0, 0, 320, 240), 576, 240, 3)


def test_far_roi_gate_and_calibration():
    calib = {"K": [[790.33, 0, 640], [0, 790.33, 360], [0, 0, 1]], "resolution": [1280, 720],
             "R": [[0.6428, 0.7660, 0], [0.2620, -0.2198, -0.9397], [-0.7198, 0.6040, -0.3420]],
             "t": [-1.3386, -2.1077, 17.4862]}
    h = tm.person_height_by_row(calib, 1.7)
    assert h[0] == 0 and h[-1] > h[400] > 0             # above horizon 0; grows towards the bottom
    rects = [(0, 0, 320, 240), (0, 480, 320, 240)]
    hrow = np.zeros(720)
    hrow[100:200] = 30
    hrow[480:] = 150
    assert tm.far_roi_tiles(rects, hrow, 64) == [0]
    f = frame([], [[10, 10, 20, 40, 0.8, 0], [10, 10, 20, 40, 0.8, 1]])
    assert len(tm.merge("e_far_roi", f, CFG, roi=[1])) == 1


def test_config_registered():
    from cctvsec.experiments import RUNNERS, load_config
    cfg = load_config("h3d_tile_merge")
    assert RUNNERS[cfg["runner"]] == "tile_merge"
