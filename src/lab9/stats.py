"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb
from numbers import Integral

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    cells = {(True, True): "tp", (False, True): "fp", (True, False): "fn", (False, False): "tn"}
    counts = dict.fromkeys(cells.values(), 0)
    for actual, predicted in zip(human, judge, strict=True):
        if actual not in {"PASS", POS} or predicted not in {"PASS", POS}:
            raise ValueError("judge calibration requires PASS or FAIL labels")
        counts[cells[actual == POS, predicted == POS]] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    counts = confusion(human, judge)
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    counts = confusion(human, judge)
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    total = tp + fp + fn + tn
    chance_pairs = (tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)
    if chance_pairs == total**2:
        raise ValueError("Cohen's kappa is undefined for these label margins")
    return ((tp + tn) * total - chance_pairs) / (total**2 - chance_pairs)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    informedness = sensitivity + specificity - 1
    # A zero denominator leaves the true prevalence unidentified.
    estimate = (observed_rate + specificity - 1) / informedness if informedness else observed_rate
    return max(0.0, min(1.0, estimate))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    sample, reference = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if sample.ndim != 1 or sample.shape != reference.shape or not sample.size:
        raise ValueError("paired bootstrap requires equally sized, nonempty 1D samples")
    if not (np.isfinite(sample).all() and np.isfinite(reference).all()):
        raise ValueError("paired bootstrap requires finite samples")
    if n_resamples < 1 or not 0 < confidence < 1:
        raise ValueError("paired bootstrap requires positive resamples and confidence in (0, 1)")

    differences = sample - reference
    delta = float(differences.mean())
    if (differences == differences[0]).all():
        return delta, delta, delta

    def mean_difference(left, right, axis):
        return (left - right).mean(axis=axis)

    result = bootstrap((sample, reference), mean_difference, paired=True, method="percentile",
                       n_resamples=n_resamples, rng=np.random.default_rng(rng),
                       confidence_level=confidence)
    interval = result.confidence_interval
    return delta, float(interval.low), float(interval.high)


def _validate_trial_counts(n: int, c: int, k: int) -> None:
    if any(isinstance(x, bool) or not isinstance(x, Integral) for x in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if not (0 <= c <= n and 1 <= k <= n):
        raise ValueError("expected 0 <= c <= n and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_trial_counts(n, c, k)
    total = comb(n, k)
    return (total - comb(n - c, k)) / total


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_trial_counts(n, c, k)
    return comb(c, k) / comb(n, k)
