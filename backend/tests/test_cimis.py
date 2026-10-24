"""CIMIS client and fetcher, offline: a fake CIMIS answers through httpx.MockTransport."""
import gzip
import json
from datetime import date, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

from app.config import PST
from app.sources import cache, cimis
from scripts import fetch_cimis

KEY = "secret-key-123"
SAMPLE = json.loads((Path(__file__).parent / "fixtures" / "cimis_sample.json").read_text())


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Own empty L1 cache per test, and no real sleeping between retries."""
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "http.sqlite")
    monkeypatch.setattr(cimis, "RETRY_DELAYS", (0, 0, 0))


def fake_cimis(seen: list, limit: int = 1750, api: str = "legacy"):
    """A CIMIS that checks the key, refuses requests over `limit` records, and returns 50°F everywhere."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        p = request.url.params
        sent_key = p.get("appKey") if api == "legacy" else request.headers.get(cimis.KEY_HEADER)
        if sent_key != KEY:
            return httpx.Response(403, json=f"[ERR1006-INVALID APP KEY] Invalid application key [{sent_key}].")
        start, end = date.fromisoformat(p["startDate"]), date.fromisoformat(p["endDate"])
        hourly = p["dataItems"] == cimis.HOURLY_ITEMS
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        if len(days) * (24 if hourly else 1) > limit:
            return httpx.Response(400, json="[ERR2112-DATA VOLUME VIOLATION] The request exceeds data limitations.")
        reading = {"Value": "50.0", "Qc": " ", "Unit": "(F)"}
        if hourly:
            recs = [
                {"Date": d.isoformat(), "Hour": f"{h:02d}00", "ZipCodes": "95616", "HlyAirTmp": reading}
                for d in days
                for h in range(1, 25)
            ]
        else:
            recs = [{"Date": d.isoformat(), "DayAirTmpMax": reading, "DayAirTmpMin": reading} for d in days]
        return httpx.Response(200, json={"Data": {"Providers": [{"Name": "cimis", "Records": recs}]}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def responding(*responses, seen=None):
    """A client that returns the given responses in order."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return httpx.Client(transport=httpx.MockTransport(handler))


# --- parsing ---------------------------------------------------------------


def at(hhmm: str, day: str = "2024-01-01") -> pd.Timestamp:
    return pd.Timestamp(f"{day} {hhmm}", tz=PST)


def test_parse_hourly_is_hour_ending_pst_with_2400_as_next_midnight():
    f = cimis.parse_hourly(SAMPLE["hourly"])
    assert str(f.index.tz) == PST
    assert f.index[0] == at("01:00")
    assert f.index[-1] == at("00:00", day="2024-01-02")
    assert f.loc[at("01:00"), "temp_f"] == 38.4
    assert f.loc[at("01:00"), "qc"] == ""
    assert f.index.is_monotonic_increasing


def test_parse_hourly_qc_flags():
    f = cimis.parse_hourly(SAMPLE["hourly"])
    assert np.isnan(f.loc[at("02:00"), "temp_f"]) and f.loc[at("02:00"), "qc"] == "M"
    assert f.loc[at("03:00"), "temp_f"] == 36.9 and f.loc[at("03:00"), "qc"] == "Y"  # kept, flagged
    assert np.isnan(f.loc[at("04:00"), "temp_f"]) and f.loc[at("04:00"), "qc"] == "R"  # far out: missing


def test_parse_daily():
    f = cimis.parse_daily(SAMPLE["daily"])
    assert list(f.columns) == ["tmax_f", "tmin_f", "qc_max", "qc_min"]
    assert f.loc["2024-01-01", "tmax_f"] == 57.3 and f.loc["2024-01-01", "tmin_f"] == 29.8
    assert f.loc["2024-01-02", "tmax_f"] == 55.0 and f.loc["2024-01-02", "qc_max"] == "Y"
    assert np.isnan(f.loc["2024-01-02", "tmin_f"]) and f.loc["2024-01-02", "qc_min"] == "M"


def test_parse_empty_response():
    assert cimis.parse_hourly({"Data": {"Providers": []}}).empty
    assert cimis.parse_daily({}).empty


def test_month_chunks():
    assert cimis.month_chunks(date(2024, 1, 15), date(2024, 3, 2)) == [
        (date(2024, 1, 15), date(2024, 1, 31)),
        (date(2024, 2, 1), date(2024, 2, 29)),
        (date(2024, 3, 1), date(2024, 3, 2)),
    ]
    assert len(cimis.month_chunks(date(2024, 9, 1), date(2025, 8, 31))) == 12


# --- requests ----------------------------------------------------------------


def test_legacy_request_params():
    seen = []
    cimis.fetch_station(6, date(2024, 1, 1), date(2024, 1, 2), True, KEY, "legacy", fake_cimis(seen))
    req = seen[0]
    assert (req.url.host, req.url.path) == ("et.water.ca.gov", "/api/data")
    p = req.url.params
    assert p["appKey"] == KEY and p["targets"] == "6" and p["dataItems"] == "hly-air-tmp"
    assert (p["startDate"], p["endDate"], p["unitOfMeasure"]) == ("2024-01-01", "2024-01-02", "E")
    assert req.headers["Accept"] == "application/json"


def test_stationweb_sends_key_in_header_only():
    seen = []
    cimis.fetch_station(6, date(2024, 1, 1), date(2024, 1, 1), False, KEY, "stationweb", fake_cimis(seen, api="stationweb"))
    req = seen[0]
    assert req.url.path == "/StationWeb/GetDataByStationNumber"
    assert req.headers[cimis.KEY_HEADER] == KEY
    assert "appKey" not in req.url.params and KEY not in str(req.url)
    assert req.url.params["stationNbrs"] == "6" and req.url.params["isHourly"] == "false"


def test_rejected_key_raises_auth_error_without_leaking_the_key():
    client = fake_cimis([])
    with pytest.raises(cimis.CimisAuthError) as err:
        cimis.fetch_station(6, date(2024, 1, 1), date(2024, 1, 1), True, "wrong-key-999", "legacy", client)
    assert err.value.code == "ERR1006"
    assert "wrong-key-999" not in str(err.value)


def test_network_errors_are_retried_then_scrubbed():
    seen = []
    boom = httpx.ConnectError(f"connect failed for https://et.water.ca.gov/api/data?appKey={KEY}")
    client = responding(boom, boom, boom, boom, seen=seen)
    with pytest.raises(cimis.CimisError) as err:
        cimis.fetch_station(6, date(2024, 1, 1), date(2024, 1, 1), True, KEY, "legacy", client)
    assert len(seen) == 4  # 1 try + 3 retries
    assert KEY not in str(err.value)


def test_server_errors_are_retried():
    seen = []
    ok = httpx.Response(200, json={"Data": {"Providers": [{"Records": []}]}})
    client = responding(httpx.Response(500, text="E90002: Unhandled server exception"), ok, seen=seen)
    assert cimis.fetch_station(6, date(2024, 1, 1), date(2024, 1, 1), True, KEY, "legacy", client)
    assert len(seen) == 2


def test_volume_error_is_not_retried():
    seen = []
    with pytest.raises(cimis.CimisError) as err:
        cimis.fetch_station(6, date(2023, 9, 1), date(2024, 8, 31), True, KEY, "legacy", fake_cimis(seen))
    assert err.value.code == cimis.VOLUME_ERROR and err.value.status == 400
    assert not isinstance(err.value, cimis.CimisAuthError)
    assert len(seen) == 1


def test_rejects_non_fahrenheit():
    body = {"Data": {"Providers": [{"Records": [{"Date": "2024-01-01", "Hour": "0100", "HlyAirTmp": {"Value": "3.5", "Qc": " ", "Unit": "(C)"}}]}]}}
    with pytest.raises(cimis.CimisError, match="°F"):
        cimis.fetch_station(6, date(2024, 1, 1), date(2024, 1, 1), True, KEY, "legacy", responding(httpx.Response(200, json=body)))


def test_detect_api_falls_back_to_stationweb():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/data":
            return httpx.Response(403, json=f"[ERR1006-INVALID APP KEY] Invalid application key [{KEY}].")
        return httpx.Response(200, json={"Data": {"Providers": [{"Records": []}]}})

    assert cimis.detect_api(KEY, httpx.Client(transport=httpx.MockTransport(handler))) == "stationweb"


def test_detect_api_gives_up_when_both_reject_the_key():
    with pytest.raises(cimis.CimisAuthError, match="both APIs"):
        cimis.detect_api(KEY, responding(httpx.Response(403, json="[ERR1006-INVALID APP KEY] x"), httpx.Response(401, json={})))


# --- fetcher script -----------------------------------------------------------------


def test_plan_tasks_clamps_to_service_dates():
    meta = fetch_cimis.load_station_meta()
    tasks, notes = fetch_cimis.plan_tasks([12, 250, 6], [2015, 2024, 2025, 2026], ["daily"], meta, date(2026, 10, 24))
    by = {(t.station, t.season): t for t in tasks}

    assert (12, 2025) not in by and (12, 2026) not in by  # Durham closed 2025-07-30
    assert any("#12 2025-26" in n for n in notes)
    assert by[(12, 2024)].end == date(2025, 7, 30) and by[(12, 2024)].complete
    assert by[(250, 2015)].start == date(2016, 8, 9)  # Williams connected mid-season
    assert by[(6, 2025)] == fetch_cimis.Task(6, 2025, "daily", date(2025, 9, 1), date(2026, 8, 31), True)
    in_progress = by[(6, 2026)]
    assert in_progress.end == date(2026, 10, 23) and not in_progress.complete


def test_parse_seasons():
    assert fetch_cimis.parse_seasons("2015-2018") == [2015, 2016, 2017, 2018]
    assert fetch_cimis.parse_seasons("2023") == [2023]


def test_refused_season_falls_back_to_months_and_writes_a_parseable_file(tmp_path):
    seen = []
    client = fake_cimis(seen, limit=800)  # a 2-month range (1,464 hours) is refused, one month (<=744) isn't
    state = fetch_cimis.RunState()
    task = fetch_cimis.Task(6, 2023, "hourly", date(2023, 9, 1), date(2023, 10, 31), True)

    summary = fetch_cimis.run_task(task, KEY, "legacy", client, state, tmp_path)

    assert summary == "1,464/1,464 hours (100.0%)"
    assert len(seen) == 3 and state.hourly_needs_chunks  # refused whole range, then Sep + Oct
    body = (tmp_path / "6_2023_hourly.json.gz").read_bytes()
    text = gzip.decompress(body).decode()
    assert KEY not in text and "ZipCodes" not in text  # trimmed, no secrets
    payload = json.loads(text)
    assert payload["_meta"]["records"] == 1464 and payload["_meta"]["api"] == "legacy"
    frame = cimis.parse_hourly(payload)
    assert frame.index[0] == pd.Timestamp("2023-09-01 01:00", tz=PST)
    assert frame.index[-1] == pd.Timestamp("2023-11-01 00:00", tz=PST)

    # The next hourly season skips the doomed whole-season request.
    seen.clear()
    fetch_cimis.run_task(fetch_cimis.Task(6, 2022, "hourly", date(2022, 9, 1), date(2022, 10, 31), True), KEY, "legacy", client, state, tmp_path)
    assert len(seen) == 2


def test_rerun_is_served_from_the_cache(tmp_path):
    seen = []
    client = fake_cimis(seen, limit=800)
    task = fetch_cimis.Task(6, 2023, "hourly", date(2023, 9, 1), date(2023, 10, 31), True)
    fetch_cimis.run_task(task, KEY, "legacy", client, fetch_cimis.RunState(), tmp_path)
    first = (tmp_path / task.filename).read_bytes()
    seen.clear()

    fetch_cimis.run_task(task, KEY, "legacy", client, fetch_cimis.RunState(hourly_needs_chunks=True), tmp_path)

    assert seen == []  # every month came from the L1 cache
    assert cimis.parse_hourly(json.loads(gzip.decompress((tmp_path / task.filename).read_bytes()))).equals(
        cimis.parse_hourly(json.loads(gzip.decompress(first)))
    )


def test_daily_season_is_one_request(tmp_path):
    seen = []
    task = fetch_cimis.Task(39, 2023, "daily", date(2023, 9, 1), date(2024, 8, 31), True)
    summary = fetch_cimis.run_task(task, KEY, "legacy", fake_cimis(seen), fetch_cimis.RunState(), tmp_path)
    assert len(seen) == 1 and summary == "366/366 days (100.0%)"


def test_auth_failure_stops_the_run(tmp_path):
    state = fetch_cimis.RunState()
    task = fetch_cimis.Task(6, 2023, "daily", date(2023, 9, 1), date(2023, 9, 30), True)
    with pytest.raises(cimis.CimisAuthError):
        fetch_cimis.run_task(task, "wrong-key", "legacy", fake_cimis([]), state, tmp_path)
    assert state.auth_failed
    assert not (tmp_path / task.filename).exists()


def test_main_needs_a_key(monkeypatch, capsys):
    monkeypatch.setattr(fetch_cimis.config, "CIMIS_KEY", "")
    assert fetch_cimis.main(["--probe"]) == 2
    assert "CIMIS_KEY is empty" in capsys.readouterr().out
