"""Turn raw upstream series into one clean hourly PST series."""
import numpy as np
import pandas as pd

from app.config import PST

# Days missing more than this many hours get no tmin/tmax rather than a biased one.
MAX_MISSING_HOURS_PER_DAY = 6


def snap(lat: float, lon: float, step: float = 0.1) -> tuple[float, float]:
    """Round to the ERA5-Land grid so nearby pins share cache entries."""

    def to_grid(v: float) -> float:
        return round(round(v / step) * step, 6)

    return to_grid(lat), to_grid(lon)


def to_pst(series_utc: pd.Series) -> pd.Series:
    """Convert a tz-aware (UTC) series to config.PST (fixed UTC-8, no daylight saving)."""
    if series_utc.index.tz is None:
        raise ValueError("expected a tz-aware index (fetch Open-Meteo with timezone=GMT)")
    return series_utc.tz_convert(PST)


def merge_archive_forecast(archive: pd.Series, forecast: pd.Series) -> pd.DataFrame:
    """One complete hourly frame [temp_f, source]; archive wins where both have a value.

    The index covers every hour from the first to the last timestamp, so hours neither
    source has are NaN (calc.gaps.fill_gaps deals with them). `source` names where each
    value came from; for missing hours it is "archive" up to the last archive reading
    and "forecast" after.
    """
    if archive.index.tz is None or forecast.index.tz is None:
        raise ValueError("expected tz-aware indexes")
    forecast = forecast.tz_convert(archive.index.tz)

    frame = pd.DataFrame({"archive": archive, "forecast": forecast})
    full = pd.date_range(frame.index.min(), frame.index.max(), freq="h", name=frame.index.name)
    frame = frame.reindex(full)

    has_archive = frame["archive"].notna()
    has_forecast = frame["forecast"].notna()
    archive_cutoff = frame.index[has_archive].max() if has_archive.any() else None
    before_cutoff = frame.index <= archive_cutoff if archive_cutoff is not None else np.zeros(len(frame), bool)

    source = np.where(
        has_archive,
        "archive",
        np.where(has_forecast, "forecast", np.where(before_cutoff, "archive", "forecast")),
    )
    return pd.DataFrame(
        {"temp_f": frame["archive"].combine_first(frame["forecast"]), "source": source},
        index=frame.index,
    )


def daily_min_max(hourly: pd.Series) -> pd.DataFrame:
    """Daily [tmin, tmax, hours] in °F from an hourly PST series, using PST calendar days.

    Indexed by naive dates (midnight timestamps), like the daily inputs calc.gdd expects.
    A day with more than MAX_MISSING_HOURS_PER_DAY missing hours gets NaN tmin/tmax.
    """
    if str(hourly.index.tz) != PST:
        raise ValueError(f"expected an index in {PST}; call to_pst first")
    days = hourly.index.normalize().tz_localize(None)
    grouped = hourly.groupby(days)
    out = pd.DataFrame({"tmin": grouped.min(), "tmax": grouped.max(), "hours": grouped.count()})
    out.index.name = "date"
    too_sparse = out["hours"] < 24 - MAX_MISSING_HOURS_PER_DAY
    out.loc[too_sparse, ["tmin", "tmax"]] = np.nan
    return out
