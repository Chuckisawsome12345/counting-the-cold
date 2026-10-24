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

    average: max(0, (tmax + tmin)/2 - base), with both clipped to upper (horizontal cutoff).
    single_sine: Zalom et al. 1983. Not implemented: it was only needed for hull split, which is cut.
    A day with a missing tmax or tmin stays NaN.
    """
    if method != "average":
        raise NotImplementedError("single_sine GDD isn't implemented (only the hull split model needed it)")
    if upper is not None:
        tmax, tmin = tmax.clip(upper=upper), tmin.clip(upper=upper)
    return ((tmax + tmin) / 2 - base).clip(lower=0)
