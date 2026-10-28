"""Tests for FID reporting.

FID is the metric most easily misreported, because `sqrtm` returns a
plausible-looking float for a rank-deficient covariance and nothing downstream
can tell that number apart from a real one. Our first attempt would have
computed FID from 12 frames and published it.

So the properties pinned here are about *honesty* rather than about the
distance: an under-sampled result must be flagged, a missing backend must return
None rather than zero, and the number must arrive with the noise floor that
makes it interpretable.

The Frechet distance itself is tested on hand-built Gaussians where the answer
is known in closed form, so these run without torch or any image data.
"""

from __future__ import annotations

import numpy as np
import pytest

from survsim.realism.fid import (
    FID_FEATURE_DIM,
    FID_MIN_SAMPLES,
    fid_report,
    frechet_distance,
)

# ------------------------------------------------------ the distance itself


def test_identical_distributions_are_zero_apart() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal(size=(500, 8))
    assert frechet_distance(a, a) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.slow
def test_a_pure_shift_costs_the_squared_distance_between_means() -> None:
    """Closed form: with equal covariances, FID reduces to ||mu1-mu2||^2."""
    rng = np.random.default_rng(1)
    base = rng.normal(size=(2000, 4))
    shifted = base + np.array([3.0, 0.0, 0.0, 0.0])

    assert frechet_distance(base, shifted) == pytest.approx(9.0, abs=0.05)


@pytest.mark.slow
def test_distance_grows_with_separation() -> None:
    rng = np.random.default_rng(2)
    base = rng.normal(size=(1000, 4))
    near = base + 1.0
    far = base + 4.0
    assert frechet_distance(base, far) > frechet_distance(base, near)


def test_distance_is_symmetric() -> None:
    rng = np.random.default_rng(3)
    a, b = rng.normal(size=(600, 5)), rng.normal(size=(600, 5)) + 0.7
    assert frechet_distance(a, b) == pytest.approx(frechet_distance(b, a), rel=1e-6)


@pytest.mark.slow
def test_the_fast_path_equals_an_explicit_matrix_square_root() -> None:
    """The optimisation is an identity, so it must agree to numerical precision.

    trace(sqrtm(S1 S2)) is computed as the sum of singular values of Ac Bcᵀ,
    which is sized by the number of images rather than by the 2048 feature
    dimensions — 53x faster on a realistic set, and better conditioned where the
    covariance is singular. Checked against scipy's `sqrtm` because an identity
    implemented with the wrong matrix orientation still returns a plausible
    float; the first attempt here did exactly that and was out by a factor of 7.
    """
    scipy_linalg = pytest.importorskip("scipy.linalg")
    rng = np.random.default_rng(42)

    for d, n in [(8, 400), (32, 300), (128, 80)]:
        a = rng.normal(size=(n, d))
        b = rng.normal(size=(n, d)) + 0.4

        mu1, mu2 = a.mean(0), b.mean(0)
        s1, s2 = np.cov(a, rowvar=False), np.cov(b, rowvar=False)
        covmean = scipy_linalg.sqrtm(s1.dot(s2))
        if isinstance(covmean, tuple):
            covmean = covmean[0]
        expected = float(((mu1 - mu2) ** 2).sum()
                         + np.trace(s1 + s2 - 2 * np.real(covmean)))

        assert frechet_distance(a, b) == pytest.approx(expected, rel=1e-6), (
            f"fast path disagrees with sqrtm at d={d}, n={n}")


@pytest.mark.slow
def test_a_covariance_difference_alone_is_detected() -> None:
    """Same mean, different spread — invisible to a mean-only comparison."""
    rng = np.random.default_rng(4)
    tight = rng.normal(scale=1.0, size=(2000, 4))
    wide = rng.normal(scale=3.0, size=(2000, 4))
    assert frechet_distance(tight, wide) > 1.0


# -------------------------------------------------------------- reporting


def test_missing_torch_reports_none_with_a_reason_not_zero(monkeypatch) -> None:
    """Zero would read as a perfect score for a metric that never ran."""
    def boom(*a, **k):
        raise ImportError("no torch")
    monkeypatch.setattr("survsim.realism.fid._inception_features", boom)

    out = fid_report([object()] * 5, [object()] * 5)
    assert out["fid"] is None
    assert out["reliable"] is False
    assert "torch" in out["reason"]


def test_too_few_images_is_reported_as_none(monkeypatch) -> None:
    monkeypatch.setattr("survsim.realism.fid._inception_features",
                        lambda p, **k: np.zeros((1, FID_FEATURE_DIM)))
    out = fid_report([1], [1])
    assert out["fid"] is None
    assert out["reliable"] is False


def test_an_undersampled_fid_is_flagged_rather_than_returned_bare(monkeypatch) -> None:
    """The exact failure we nearly shipped: a confident number from 12 frames."""
    rng = np.random.default_rng(5)
    monkeypatch.setattr("survsim.realism.fid._inception_features",
                        lambda p, **k: rng.normal(size=(len(p), FID_FEATURE_DIM)))

    out = fid_report(list(range(12)), list(range(12)))
    assert out["fid"] is not None, "still computed, but must be labelled"
    assert out["reliable"] is False
    assert str(FID_MIN_SAMPLES) in out["reason"]
    assert "rank-deficient" in out["reason"]


def test_a_well_sampled_comparison_is_marked_reliable(monkeypatch) -> None:
    rng = np.random.default_rng(6)
    monkeypatch.setattr("survsim.realism.fid._inception_features",
                        lambda p, **k: rng.normal(size=(len(p), 16)))

    out = fid_report(list(range(FID_MIN_SAMPLES)), list(range(FID_MIN_SAMPLES)))
    assert out["reliable"] is True
    assert out["reason"] is None


def test_the_report_carries_a_noise_floor(monkeypatch) -> None:
    """Without it, "FID 38" cannot be called good or bad by anyone."""
    rng = np.random.default_rng(7)
    monkeypatch.setattr("survsim.realism.fid._inception_features",
                        lambda p, **k: rng.normal(size=(len(p), 16)))

    out = fid_report(list(range(400)), list(range(400)))
    assert out["floor"] is not None
    assert out["ratio_to_floor"] is not None
    assert out["n_real"] == 400 and out["n_fake"] == 400


def test_two_samples_of_one_distribution_sit_near_their_own_floor(monkeypatch) -> None:
    """The sanity property: same distribution means ratio near 1."""
    rng = np.random.default_rng(8)
    monkeypatch.setattr("survsim.realism.fid._inception_features",
                        lambda p, **k: rng.normal(size=(len(p), 16)))

    out = fid_report(list(range(1000)), list(range(1000)))
    assert out["ratio_to_floor"] == pytest.approx(1.0, abs=1.5)


def test_a_genuinely_different_set_scores_far_above_the_floor(monkeypatch) -> None:
    rng = np.random.default_rng(9)

    def features(paths, **kwargs):
        # Fake paths are the ones tagged "fake"; shift them well away.
        offset = 5.0 if any(str(p).startswith("fake") for p in paths) else 0.0
        return rng.normal(size=(len(paths), 16)) + offset

    monkeypatch.setattr("survsim.realism.fid._inception_features", features)
    out = fid_report([f"real{i}" for i in range(800)],
                     [f"fake{i}" for i in range(800)])
    assert out["ratio_to_floor"] > 5.0
