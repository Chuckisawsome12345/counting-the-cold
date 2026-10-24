"""Where the season is heading: forecast continuation and analog-season ranges."""
import pandas as pd


def analog_percentiles(
    current_value: float, day_of_season: int, history: list[pd.Series]
) -> dict[str, float]:
    """End-of-season p10/p50/p90 for one metric.

    For each past season (a cumulative Series indexed by day of season), add what it gained
    from day_of_season to season end onto current_value, then take percentiles.
    """
    raise NotImplementedError
