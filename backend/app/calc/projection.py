"""Where the season is heading: forecast continuation and analog-season ranges."""
import numpy as np
import pandas as pd


def analog_percentiles(
    current_value: float, day_of_season: int, history: list[pd.Series]
) -> dict[str, float]:
    """End-of-season p10/p50/p90 for one metric.

    For each past season (a cumulative Series indexed by day of season), add what it gained
    from day_of_season to season end onto current_value, then take percentiles.

    day_of_season is how many days the current season has counted so far (current_value is the
    total at the end of day day_of_season - 1), so each analog contributes
    history[-1] - history[day_of_season - 1], or its whole season when day_of_season is 0. Seasons
    shorter than that (Feb 29) use their last value. Gains can be negative (Utah units fall in
    warm spells). Percentiles interpolate linearly; with no history the range collapses to
    current_value.
    """
    finals = []
    for curve in history:
        values = pd.Series(curve, dtype=float).dropna().to_numpy()
        if len(values) == 0:
            continue
        before = values[min(day_of_season, len(values)) - 1] if day_of_season > 0 else 0.0
        finals.append(current_value + values[-1] - before)
    if not finals:
        return {"p10": float(current_value), "p50": float(current_value), "p90": float(current_value)}
    p10, p50, p90 = np.percentile(finals, [10, 50, 90])
    return {"p10": round(float(p10), 1), "p50": round(float(p50), 1), "p90": round(float(p90), 1)}
