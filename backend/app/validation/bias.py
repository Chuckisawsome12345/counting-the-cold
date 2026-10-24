"""Station bias tables: mean (CIMIS - gridded) °F by month x hour of day, and blending them for a pin."""
from dataclasses import dataclass

import pandas as pd


@dataclass
class BiasCandidate:
    station_id: int
    table: pd.DataFrame  # index month 1-12, columns hour 0-23
    distance_km: float
    active: bool
    seasons: int  # seasons of history behind the table


def fit_bias_table(gridded: pd.Series, observed: pd.Series) -> pd.DataFrame:
    """12 x 24 table of mean (observed - gridded), aligned hourly on the PST index."""
    raise NotImplementedError


def apply_bias(t: pd.Series, table: pd.DataFrame) -> pd.Series:
    """Add each hour's (month, hour) offset to t."""
    raise NotImplementedError


def blend_tables(
    candidates: list[BiasCandidate], max_km: float = 150.0, power: float = 2.0
) -> tuple[pd.DataFrame, list[float]]:
    """Inverse-distance-weighted table plus one weight per candidate (0 if beyond max_km).

    A closed station within 10 km with at least 3 seasons of history gets most of the weight.
    """
    raise NotImplementedError
