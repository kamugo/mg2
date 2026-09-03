"""Document-level bootstrap confidence intervals and paired comparisons."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np

Document = Mapping[str, object]
Metric = Callable[[Sequence[Document]], float]


def percentile_interval(values: Sequence[float], confidence: float = 0.95) -> tuple[float, float]:
    """Return a two-sided percentile confidence interval."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between zero and one")
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(np.asarray(values, dtype=np.float64), [alpha, 1.0 - alpha])
    return float(low), float(high)


def bootstrap_score(
    documents: Sequence[Document],
    metric: Metric,
    samples: int = 2000,
    confidence: float = 0.95,
    seed: int = 20260903,
) -> dict[str, float | int]:
    """Estimate a metric interval by resampling whole documents."""
    if not documents:
        raise ValueError("documents cannot be empty")
    if samples < 1:
        raise ValueError("samples must be positive")
    generator = np.random.default_rng(seed)
    estimates = []
    for _ in range(samples):
        indices = generator.integers(0, len(documents), size=len(documents))
        estimates.append(metric([documents[index] for index in indices]))
    low, high = percentile_interval(estimates, confidence)
    return {
        "estimate": float(metric(documents)),
        "ci_low": low,
        "ci_high": high,
        "confidence": confidence,
        "samples": samples,
        "seed": seed,
    }


def paired_bootstrap_difference(
    system_a: Sequence[Document],
    system_b: Sequence[Document],
    metric: Metric,
    samples: int = 2000,
    confidence: float = 0.95,
    seed: int = 20260903,
) -> dict[str, float | int]:
    """Compare aligned systems using paired document bootstrap."""
    if not system_a or len(system_a) != len(system_b):
        raise ValueError("systems must contain the same positive number of documents")
    generator = np.random.default_rng(seed)
    differences = []
    for _ in range(samples):
        indices = generator.integers(0, len(system_a), size=len(system_a))
        a_sample = [system_a[index] for index in indices]
        b_sample = [system_b[index] for index in indices]
        differences.append(metric(a_sample) - metric(b_sample))
    low, high = percentile_interval(differences, confidence)
    observed = float(metric(system_a) - metric(system_b))
    return {
        "difference_a_minus_b": observed,
        "ci_low": low,
        "ci_high": high,
        "confidence": confidence,
        "samples": samples,
        "seed": seed,
        "two_sided_p": float(
            min(1.0, 2.0 * min(np.mean(np.asarray(differences) <= 0), np.mean(np.asarray(differences) >= 0)))
        ),
    }
