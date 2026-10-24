"""Error metrics for validation.json."""
from collections.abc import Sequence

import numpy as np


def mae(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Mean absolute error over pairs where both values exist. NaN if there are none."""
    p = np.asarray(predicted, dtype=float)
    a = np.asarray(actual, dtype=float)
    if p.shape != a.shape:
        raise ValueError(f"predicted has {p.size} values, actual has {a.size}")
    ok = ~(np.isnan(p) | np.isnan(a))
    return float(np.abs(p[ok] - a[ok]).mean()) if ok.any() else float("nan")


def bias(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Mean signed error (predicted - actual) over pairs where both values exist."""
    p = np.asarray(predicted, dtype=float)
    a = np.asarray(actual, dtype=float)
    ok = ~(np.isnan(p) | np.isnan(a))
    return float((p[ok] - a[ok]).mean()) if ok.any() else float("nan")
