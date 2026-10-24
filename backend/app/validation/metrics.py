"""Error metrics for validation.json."""
from collections.abc import Sequence


def mae(predicted: Sequence[float], actual: Sequence[float]) -> float:
    raise NotImplementedError
