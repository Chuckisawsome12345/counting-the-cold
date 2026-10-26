"""Growing degree days (°F-days). Pure functions."""
import pandas as pd


def daily_gdd(tmax: pd.Series, tmin: pd.Series, base: float, upper: float | None = None) -> pd.Series:
    """Per-day degree days, indexed by date, by the average method:
    max(0, (tmax + tmin)/2 - base), with both clipped to upper (horizontal cutoff).
    A day with a missing tmax or tmin stays NaN.
    """
    if upper is not None:
        tmax, tmin = tmax.clip(upper=upper), tmin.clip(upper=upper)
    return ((tmax + tmin) / 2 - base).clip(lower=0)
