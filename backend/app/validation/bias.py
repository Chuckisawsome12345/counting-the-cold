"""Station bias tables: mean (CIMIS - gridded) °F by month x hour of day, and blending them for a pin."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS = range(1, 13)
HOURS = range(24)
# A closed station this close to the pin, with this much history, calibrates the pin on its own.
CLOSED_STATION_KM = 10.0
CLOSED_STATION_MIN_SEASONS = 3
CLOSED_STATION_WEIGHT = 0.9
# Distances below this count as this (a pin on top of a station would otherwise divide by zero).
MIN_DISTANCE_KM = 0.5


@dataclass
class BiasCandidate:
    station_id: int
    table: pd.DataFrame  # index month 1-12, columns hour 0-23
    distance_km: float
    active: bool
    seasons: int  # seasons of history behind the table


def fit_bias_table(gridded: pd.Series, observed: pd.Series) -> pd.DataFrame:
    """12 x 24 table of mean (observed - gridded), aligned hourly on the PST index.

    Only hours where both series have a value count. A month-hour cell with no data takes that
    hour's mean over the other months (then the overall mean, then 0), so the table has no holes.
    """
    diff = (observed - gridded).dropna()
    if diff.empty:
        return pd.DataFrame(0.0, index=MONTHS, columns=HOURS)
    table = diff.groupby([diff.index.month, diff.index.hour]).mean().unstack()
    table = table.reindex(index=MONTHS, columns=HOURS)
    table.index.name, table.columns.name = None, None
    table = table.fillna(table.mean(axis=0)).fillna(float(diff.mean())).fillna(0.0)
    return table.astype(float)


def apply_bias(t: pd.Series, table: pd.DataFrame) -> pd.Series:
    """Add each hour's (month, hour) offset to t. NaN stays NaN."""
    offsets = table.reindex(index=MONTHS, columns=HOURS).to_numpy(dtype=float)
    month = np.asarray(t.index.month) - 1
    hour = np.asarray(t.index.hour)
    return t + offsets[month, hour]


def blend_tables(
    candidates: list[BiasCandidate], max_km: float = 150.0, power: float = 2.0
) -> tuple[pd.DataFrame, list[float]] | None:
    """Inverse-distance-weighted table plus one weight per candidate (0 if beyond max_km).

    A closed station within 10 km with at least 3 seasons of history gets most of the weight
    (at least CLOSED_STATION_WEIGHT; the rest is shared by inverse distance). Returns None when
    no candidate is within max_km, so the caller leaves the pin uncorrected.
    """
    raw = np.array(
        [
            1.0 / max(c.distance_km, MIN_DISTANCE_KM) ** power if c.distance_km <= max_km else 0.0
            for c in candidates
        ]
    )
    if raw.sum() == 0:
        return None
    weights = raw / raw.sum()

    anchors = [
        i
        for i, c in enumerate(candidates)
        if not c.active and c.distance_km <= CLOSED_STATION_KM and c.seasons >= CLOSED_STATION_MIN_SEASONS
    ]
    if anchors:
        anchor = min(anchors, key=lambda i: candidates[i].distance_km)
        if weights[anchor] < CLOSED_STATION_WEIGHT:
            others = raw.copy()
            others[anchor] = 0.0
            weights = (others / others.sum() * (1 - CLOSED_STATION_WEIGHT)) if others.sum() else others
            weights[anchor] = CLOSED_STATION_WEIGHT if others.sum() else 1.0

    table = sum(
        w * c.table.reindex(index=MONTHS, columns=HOURS).astype(float)
        for c, w in zip(candidates, weights)
        if w > 0
    )
    return table, [float(w) for w in weights]
