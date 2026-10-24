"""CIMIS Web API client. Used only by offline scripts (scripts/fetch_cimis.py), never on the request path.

The key comes from config.CIMIS_KEY and travels in a header; never log it.
"""
from datetime import date

import pandas as pd

DATA_URL = "https://et.water.ca.gov/StationWeb/GetDataByStationNumber"
STATION_URL = "https://et.water.ca.gov/api/station"  # no key needed
KEY_HEADER = "Ocp-Apim-Subscription-Key"
HOURLY_ITEMS = "hly-air-tmp"
DAILY_ITEMS = "day-air-tmp-max,day-air-tmp-min"

# QC flags treated as missing. Blank is good; "Y" (moderately out of range) is kept but flagged.
MISSING_QC = {"M", "R", "Q", "S", "N"}


def fetch_station(station: int, start: date, end: date, hourly: bool, key: str) -> dict:
    """Raw JSON for one station and date range.

    Params: stationNbrs, startDate, endDate (YYYY-MM-DD), isHourly, unitOfMeasure=E, dataItems.
    One station-season per request; large requests are refused, so callers fall back to monthly chunks.
    """
    raise NotImplementedError


def parse_hourly(raw: dict) -> pd.DataFrame:
    """Records at Data > Providers > Records -> DataFrame[temp_f, qc] indexed by PST timestamp.

    CIMIS hours are hour-ending in PST; "2400" is 00:00 the next day.
    """
    raise NotImplementedError


def parse_daily(raw: dict) -> pd.DataFrame:
    """Daily records -> DataFrame[tmax_f, tmin_f, qc_max, qc_min] indexed by date."""
    raise NotImplementedError
