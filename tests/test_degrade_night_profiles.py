"""H32 night profiles: cctv_night_lowlight (visible) and cctv_thermal (LWIR)."""
from pathlib import Path

import cv2
import numpy as np
import pytest

from survsim.sensors.degrade import PROFILES, apply_sequence, person_mask, thermal


def _scene(seed=0):
    rng = np.random.default_rng(seed)
    img = np.full((360, 640, 3), 90, np.uint8)
    img[200:] = 60
    img += rng.integers(0, 20, img.shape, dtype=np.uint8)
    mask = np.zeros((360, 640, 4), np.uint8)
    mask[150:300, 300:340, 2] = 200
    mask[..., 3] = 255
    return img, mask


def test_person_mask_from_colour_instance_mask():
    _, m = _scene()
    pm = person_mask(m, (180, 320))
    assert pm.shape == (180, 320) and pm.max() == 1.0 and 0 < pm.mean() < 0.1


def test_thermal_people_hot_and_grey():
    img, m = _scene()
    t = thermal(img.astype(np.float32), np.random.default_rng(0), mask=m, sensor_w=320)
    assert np.allclose(t[..., 0], t[..., 2])
    assert t[160:290, 305:335].mean() > t[:, :200].mean() + 80


def test_thermal_profile_output_is_exactly_mono_and_deterministic():
    img, m = _scene()
    a = list(apply_sequence([img, img], "cctv_thermal", sequence_seed=3, masks=[m, m]))
    b = list(apply_sequence([img, img], "cctv_thermal", sequence_seed=3, masks=[m, m]))
    assert np.array_equal(a[0], b[0])
    assert (a[0][..., 0] == a[0][..., 1]).all() and (a[0][..., 1] == a[0][..., 2]).all()


def test_lowlight_is_darker_and_less_chromatic():
    img, _ = _scene()
    img[..., 2] = 160
    out = next(apply_sequence([img], "cctv_night_lowlight", sequence_seed=0))
    lab_in = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(float)
    lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB).astype(float)
    chroma = lambda x: np.hypot(x[..., 1] - 128, x[..., 2] - 128).mean()
    assert out.mean() < img.mean() and chroma(lab) < chroma(lab_in)


REAL = Path.home() / "data/real_cctv_night"
REND = Path(__file__).resolve().parents[1] / "out/batch_v8/street_crowd_night"


@pytest.mark.slow
@pytest.mark.skipif(not (REAL.is_dir() and REND.is_dir()), reason="needs LLVIP + batch_v8")
@pytest.mark.parametrize("profile,sub,floor", [("cctv_night_lowlight", "llvip_vis", 9),
                                               ("cctv_thermal", "llvip_ir", 10)])
def test_tune_band_count_pinned(profile, sub, floor):
    """Pins the tune-set fit (H32a). The hold-out band is NOT met (2/13, 3/13; 32 H32a)."""
    from cctvsec.experiments.night_profiles import STATS, _bands, in_band, split_real
    from survsim.realism.stats import frame_stats, list_images
    tune, _ = split_real(list_images(REAL / sub), 15)
    fr = list(range(5, 300, 30))
    im = [cv2.imread(str(REND / "render/cam_02" / f"{f:04d}.png")) for f in fr]
    mk = [cv2.imread(str(REND / "mask/cam_02" / f"{f:04d}.png"), -1) for f in fr]
    rows = [frame_stats(o).as_dict() for o in apply_sequence(im, PROFILES[profile], 0, masks=mk)]
    med = {k: float(np.median([r[k] for r in rows])) for k in STATS}
    assert sum(in_band(_bands(tune), med).values()) >= floor
