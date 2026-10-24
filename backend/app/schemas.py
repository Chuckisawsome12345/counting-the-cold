"""API response shapes. Mirrors docs/api-contract.md and frontend/src/api/types.ts.

Change these only through a `contract` PR (see docs/CONTRIBUTING.md).
"""
from typing import Literal

from pydantic import BaseModel

Metric = Literal["chill_portions", "chill_hours", "utah_units", "gdd"]


class Totals(BaseModel):
    chill_portions: float
    chill_hours: float
    utah_units: float
    gdd: float


class Location(BaseModel):
    lat: float
    lon: float
    grid_lat: float
    grid_lon: float


class SeasonInfo(BaseModel):
    label: str  # "2025-26"
    portions_start: str  # ISO dates
    hours_start: str
    gdd_start: str
    end: str  # Aug 31
    as_of: str
    complete: bool


class PointSettings(BaseModel):
    crop: str
    gdd_base_f: float
    gdd_upper_f: float | None
    corrected: bool


class DailyRow(BaseModel):
    date: str
    tmin: float | None
    tmax: float | None
    # Metric values are cumulative season-to-date (0 before each metric's start date).
    chill_portions: float
    chill_hours: float
    utah_units: float
    gdd: float
    source: Literal["archive", "forecast"]
    filled: bool  # true if any hour that day was interpolated


class Forecast(BaseModel):
    daily: list[DailyRow]
    plus7: Totals
    plus14: Totals


class HistoryPoint(BaseModel):
    day: int  # days since Sep 1 of that season
    chill_portions: float
    chill_hours: float
    utah_units: float
    gdd: float


class HistorySeason(BaseModel):
    season: str
    totals: Totals
    cumulative: list[HistoryPoint]


class Percentiles(BaseModel):
    p10: float
    p50: float
    p90: float


class Climatology(BaseModel):
    chill_portions: Percentiles
    chill_hours: Percentiles
    utah_units: Percentiles
    gdd: Percentiles


class GapSpan(BaseModel):
    start: str
    end: str
    hours: int


class Quality(BaseModel):
    missing_hours: int
    interpolated_hours: int
    long_gaps: list[GapSpan]
    stale: bool


class StationRef(BaseModel):
    id: int
    name: str
    active: bool
    distance_km: float


class CorrectionStation(StationRef):
    weight: float


class Correction(BaseModel):
    applied: bool
    stations: list[CorrectionStation]
    expected_error: Totals | None


class PointResponse(BaseModel):
    mock: bool = False
    location: Location
    season: SeasonInfo
    settings: PointSettings
    totals: Totals
    daily: list[DailyRow]
    forecast: Forecast | None  # null once the season is over
    history: list[HistorySeason]  # the 10 seasons before this one, oldest first
    climatology: Climatology | None  # end-of-season range; null once the season is over
    quality: Quality
    correction: Correction
    nearest_station: StationRef


class MetricError(BaseModel):
    raw_mae: float
    corrected_mae: float


class Station(BaseModel):
    id: int
    name: str
    city: str
    county: str
    lat: float
    lon: float
    elevation_ft: int
    active: bool
    connect_date: str
    disconnect_date: str | None
    group: str  # "core" | "durham" | "durham-neighbor"
    validation: dict[Metric, MetricError] | None = None


class StationsResponse(BaseModel):
    stations: list[Station]


class SeasonValidation(BaseModel):
    season: str
    cimis: Totals
    raw: Totals
    corrected: Totals


class StationValidation(BaseModel):
    id: int
    name: str
    seasons: list[SeasonValidation]
    mae: dict[Metric, MetricError]


class ValidationResponse(BaseModel):
    built_at: str | None
    summary: dict[Metric, MetricError]
    stations: list[StationValidation]


class Crop(BaseModel):
    id: str
    label: str
    base_f: float
    upper_f: float | None


class CropsResponse(BaseModel):
    crops: list[Crop]


class HealthResponse(BaseModel):
    ok: bool
    demo_mode: bool
    cache_entries: int
