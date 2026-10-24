"""Growing degree days (°F-days). Pure functions."""
from typing import Literal

import pandas as pd


def daily_gdd(
    tmax: pd.Series,
    tmin: pd.Series,
    base: float,
    upper: float | None = None,
    method: Literal["average", "single_sine"] = "average",
) -> pd.Series:
    """Per-day degree days, indexed by date.

    average: max(0, (tmax + tmin)/2 - base), with tmax clipped to upper (horizontal cutoff).
    single_sine: Zalom et al. 1983, used by UC IPM and the hull split model.
    """
    raise NotImplementedError
