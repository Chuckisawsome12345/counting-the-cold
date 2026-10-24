"""CIMIS Web API client. Used only by offline scripts (scripts/fetch_cimis.py), never on the request path.

CIMIS has two data endpoints, and a key from et.water.ca.gov works on one of them:
- "legacy": the documented REST API (https://et.water.ca.gov/Rest/Index), key in the appKey param.
- "stationweb": the newer gateway, key in the Ocp-Apim-Subscription-Key header.
detect_api() finds out which. Both answer with records at Data > Providers > Records.

The key comes from config.CIMIS_KEY; never log it. CIMIS echoes the key in some error messages, so
every CimisError message has it scrubbed out, and no message includes a request URL.
"""
import time
from datetime import date, timedelta

import httpx
import numpy as np
import pandas as pd

from app.config import PST

LEGACY_URL = "https://et.water.ca.gov/api/data"
DATA_URL = "https://et.water.ca.gov/StationWeb/GetDataByStationNumber"
STATION_URL = "https://et.water.ca.gov/api/station"  # no key needed
KEY_HEADER = "Ocp-Apim-Subscription-Key"
APIS = ("legacy", "stationweb")
HOURLY_ITEMS = "hly-air-tmp"
DAILY_ITEMS = "day-air-tmp-max,day-air-tmp-min"
# Record fields for those items.
HOURLY_FIELD = "HlyAirTmp"
DAILY_FIELDS = ("DayAirTmpMax", "DayAirTmpMin")

# QC flags treated as missing. Blank is good; "Y" (moderately out of range) is kept but flagged.
MISSING_QC = {"M", "R", "Q", "S", "N"}
# Too many records in one request. The legacy API caps a request at about 1,750 records, so a
# season of hourly data (8,760) is refused and callers fall back to monthly chunks.
VOLUME_ERROR = "ERR2112"
INVALID_KEY_ERROR = "ERR1006"

TIMEOUT_SECONDS = 60.0
# CIMIS goes down for stretches (E90002 on Oct 23), so back off longer than for Open-Meteo.
RETRY_DELAYS = (2.0, 5.0, 15.0, 30.0)
RETRY_STATUSES = {429, 500, 502, 503, 504}


class CimisError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


class CimisAuthError(CimisError):
    """CIMIS rejected the key. Retrying won't help."""


def fetch_station(
    station: int,
    start: date,
    end: date,
    hourly: bool,
    key: str,
    api: str = "legacy",
    client: httpx.Client | None = None,
) -> dict:
    """Raw JSON for one station and date range (inclusive), in °F.

    One station-season per request; large requests are refused (CimisError with code
    VOLUME_ERROR on the legacy API), so callers fall back to monthly chunks.
    Retries 429/5xx and network errors with backoff; raises CimisAuthError for a rejected key.
    """
    items = HOURLY_ITEMS if hourly else DAILY_ITEMS
    if api == "legacy":
        url, headers = LEGACY_URL, {"Accept": "application/json"}
        params = {"appKey": key, "targets": str(station), "dataItems": items}
    elif api == "stationweb":
        url, headers = DATA_URL, {"Accept": "application/json", KEY_HEADER: key}
        params = {"stationNbrs": str(station), "isHourly": str(hourly).lower(), "dataItems": items}
    else:
        raise ValueError(f"unknown CIMIS api {api!r}; expected one of {APIS}")
    params |= {"startDate": start.isoformat(), "endDate": end.isoformat(), "unitOfMeasure": "E"}
    payload = _get(url, params, headers, key, client)
    _check_units(payload)
    return payload


def detect_api(key: str, client: httpx.Client | None = None) -> str:
    """Which endpoint accepts this key: "legacy" or "stationweb". One tiny request each at most.

    Keys issued since the gateway launched (32 hex characters) only work on "stationweb"; the
    legacy endpoint's firewall answers them with a "Request Rejected" HTML page.
    """
    day = date(2024, 1, 1)
    errors = []
    for api in APIS:
        try:
            fetch_station(6, day, day, hourly=False, key=key, api=api, client=client)
            return api
        except CimisError as e:
            errors.append(f"{api}: {e}")
    if all("401" in e or "403" in e or INVALID_KEY_ERROR in e for e in errors):
        raise CimisAuthError("CIMIS rejected the key on both APIs. Check CIMIS_KEY in the repo-root .env.")
    raise CimisError("Neither CIMIS API answered with data. " + " | ".join(errors))


def records(raw: dict) -> list[dict]:
    """All records at Data > Providers > Records, across providers."""
    data = field(raw, "Data") or {}
    out: list[dict] = []
    for provider in field(data, "Providers") or []:
        out.extend(field(provider, "Records") or [])
    return out


def parse_hourly(raw: dict) -> pd.DataFrame:
    """Records at Data > Providers > Records -> DataFrame[temp_f, qc] indexed by PST timestamp.

    CIMIS hours are hour-ending in PST; "2400" is 00:00 the next day. Values with a QC flag in
    MISSING_QC become NaN (the flag stays in `qc`); blank QC is "".
    """
    rows = records(raw)
    times, temps, qcs = [], [], []
    for r in rows:
        hour = int(str(field(r, "Hour")).strip())
        times.append(pd.Timestamp(field(r, "Date")) + pd.Timedelta(hours=hour // 100))
        value, qc = _reading(field(r, HOURLY_FIELD))
        temps.append(value)
        qcs.append(qc)
    index = pd.DatetimeIndex(times, name="time").tz_localize(PST) if times else pd.DatetimeIndex([], tz=PST, name="time")
    frame = pd.DataFrame({"temp_f": np.array(temps, dtype=float), "qc": qcs}, index=index)
    return _sorted_unique(frame)


def parse_daily(raw: dict) -> pd.DataFrame:
    """Daily records -> DataFrame[tmax_f, tmin_f, qc_max, qc_min] indexed by date.

    Missing-flagged values become NaN as in parse_hourly.
    """
    rows = records(raw)
    days, tmax, tmin, qc_max, qc_min = [], [], [], [], []
    for r in rows:
        days.append(pd.Timestamp(field(r, "Date")))
        hi, hi_qc = _reading(field(r, DAILY_FIELDS[0]))
        lo, lo_qc = _reading(field(r, DAILY_FIELDS[1]))
        tmax.append(hi)
        tmin.append(lo)
        qc_max.append(hi_qc)
        qc_min.append(lo_qc)
    frame = pd.DataFrame(
        {
            "tmax_f": np.array(tmax, dtype=float),
            "tmin_f": np.array(tmin, dtype=float),
            "qc_max": qc_max,
            "qc_min": qc_min,
        },
        index=pd.DatetimeIndex(days, name="date"),
    )
    return _sorted_unique(frame)


def month_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Split [start, end] (inclusive) at calendar-month boundaries."""
    chunks = []
    cur = start
    while cur <= end:
        next_month = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        chunk_end = min(end, next_month - timedelta(days=1))
        chunks.append((cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return chunks


def _get(url: str, params: dict, headers: dict, key: str, client: httpx.Client | None) -> dict:
    owned = client is None
    client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        for delay in (*RETRY_DELAYS, None):
            try:
                response = client.get(url, params=params, headers=headers)
            except httpx.HTTPError as e:
                if delay is None:
                    # str(e) can include the URL, which carries the key on the legacy API.
                    raise CimisError(_scrub(f"CIMIS request failed: {type(e).__name__}: {e}", key)) from None
            else:
                if response.status_code not in RETRY_STATUSES or delay is None:
                    break
            time.sleep(delay)
    finally:
        if owned:
            client.close()
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            # e.g. the legacy endpoint's firewall page: <title>Request Rejected</title>
            title = response.text.split("<title>", 1)[-1].split("</title>", 1)[0] if "<title>" in response.text else ""
            detail = f" ({_scrub(title.strip()[:80], key)})" if title else ""
            raise CimisError(f"CIMIS returned a 200 that isn't JSON{detail}", status=200) from None
    text = _scrub(response.text.strip()[:300], key)
    code = next((c for c in (VOLUME_ERROR, INVALID_KEY_ERROR) if c in text), None)
    if code is None and "[ERR" in text:
        code = text.split("[", 1)[1].split(" ", 1)[0].split("-", 1)[0]
    if response.status_code == 401 or code == INVALID_KEY_ERROR:
        raise CimisAuthError(f"CIMIS {response.status_code}: {text}", response.status_code, code)
    raise CimisError(f"CIMIS {response.status_code}: {text}", response.status_code, code)


def _check_units(payload: dict) -> None:
    # unitOfMeasure=E gives "(F)" on the legacy API and "(°F)" on stationweb; checked before anything is stored.
    for r in records(payload):
        for name in (HOURLY_FIELD, *DAILY_FIELDS):
            item = field(r, name)
            if isinstance(item, dict):
                unit = (field(item, "Unit") or "").strip()
                if unit and unit.strip("()").replace("°", "").strip().upper() != "F":
                    raise CimisError(f"expected °F from CIMIS, got {unit} for {name}")


def _reading(item) -> tuple[float, str]:
    """(value °F or NaN, qc flag) from {"Value": "57.3", "Qc": " "}."""
    if not isinstance(item, dict):
        return np.nan, ""
    qc = (field(item, "Qc") or "").strip()
    raw = field(item, "Value")
    try:
        value = float(raw) if raw not in (None, "") else np.nan
    except (TypeError, ValueError):
        value = np.nan
    if qc in MISSING_QC:
        value = np.nan
    return value, qc


def field(d: dict, name: str):
    """d[name], falling back to a case-insensitive match (the newer endpoint may differ in case)."""
    if not isinstance(d, dict):
        return None
    if name in d:
        return d[name]
    lower = name.lower()
    return next((v for k, v in d.items() if k.lower() == lower), None)


def _sorted_unique(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_index()
    return frame[~frame.index.duplicated(keep="last")]


def _scrub(text: str, key: str) -> str:
    return text.replace(key, "***") if key else text
