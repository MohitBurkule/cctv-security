"""Small-sample inference helpers used by H12-H14 (report 49 §5, §3, §4).

Kept dependency-light (numpy + scipy.stats) and deterministic (explicit seeds).
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Sequence

import numpy as np


def garwood(k: int, exposure: float, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Garwood 1936) two-sided CI for a Poisson rate k / exposure.

    lower = chi2_{a/2}(2k) / 2T (0 when k == 0), upper = chi2_{1-a/2}(2k+2) / 2T."""
    from scipy.stats import chi2
    lo = 0.0 if k == 0 else float(chi2.ppf(alpha / 2, 2 * k)) / (2 * exposure)
    hi = float(chi2.ppf(1 - alpha / 2, 2 * k + 2)) / (2 * exposure)
    return lo, hi


def rule_of_three(exposure: float, alpha: float = 0.05) -> float:
    """One-sided upper bound on a Poisson rate after zero events: -ln(alpha) / T."""
    return -math.log(alpha) / exposure


def bootstrap_ratio(num: Sequence[float], den: Sequence[float], n_boot: int = 2000,
                    seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile CI of sum(num)/sum(den), resampling clusters (rows) with replacement."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), size=(n_boot, len(num)))
    d = den[idx].sum(axis=1)
    r = np.where(d > 0, num[idx].sum(axis=1) / np.where(d > 0, d, 1), np.nan)
    return float(np.nanpercentile(r, 100 * alpha / 2)), float(np.nanpercentile(r, 100 * (1 - alpha / 2)))


def bootstrap_mean_diff(a: Sequence[float], b: Sequence[float], n_boot: int = 10000,
                        seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile CI of mean(b) - mean(a), each arm resampled independently."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    da = a[rng.integers(0, len(a), (n_boot, len(a)))].mean(axis=1)
    db = b[rng.integers(0, len(b), (n_boot, len(b)))].mean(axis=1)
    d = db - da
    return float(np.percentile(d, 100 * alpha / 2)), float(np.percentile(d, 100 * (1 - alpha / 2)))


def permutation_p(a: Sequence[float], b: Sequence[float]) -> float:
    """Exact two-sided unpaired permutation p for mean(b) - mean(a) (all C(n, k) splits)."""
    a, b = list(map(float, a)), list(map(float, b))
    pool = np.array(a + b)
    obs = abs(np.mean(b) - np.mean(a))
    n, k = len(pool), len(b)
    tot = hits = 0
    for comb in itertools.combinations(range(n), k):
        m = np.zeros(n, bool)
        m[list(comb)] = True
        hits += abs(pool[m].mean() - pool[~m].mean()) >= obs - 1e-12
        tot += 1
    return hits / tot


def spearman(x: Sequence[float], y: Sequence[float], n_boot: int = 10000, n_perm: int = 20000,
             seed: int = 0, alpha: float = 0.05) -> dict[str, float]:
    """Spearman rho, percentile bootstrap CI (pairs resampled), two-sided permutation p."""
    from scipy.stats import spearmanr
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho = float(spearmanr(x, y).statistic)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(x), len(x))
        if len(set(x[i])) > 1 and len(set(y[i])) > 1:
            bs.append(spearmanr(x[i], y[i]).statistic)
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    rxc = rx - rx.mean()
    perm = np.array([np.corrcoef(rxc, ry[rng.permutation(len(y))])[0, 1] for _ in range(n_perm)])
    p = float((np.sum(np.abs(perm) >= abs(rho) - 1e-12) + 1) / (n_perm + 1))
    return {"rho": round(rho, 4), "ci_lo": round(float(np.percentile(bs, 100 * alpha / 2)), 4),
            "ci_hi": round(float(np.percentile(bs, 100 * (1 - alpha / 2))), 4),
            "perm_p": round(p, 5), "n": len(x)}
