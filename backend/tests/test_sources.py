from datetime import date

import httpx
import numpy as np
import pytest

from app.sources import cache, openmeteo


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Each test gets its own empty SQLite cache and L2."""
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "http.sqlite")
    cache.clear_results()

# Trimmed from a real archive response (Durham, 2025-11-01, timezone=GMT).
ARCHIVE_PAYLOAD = {
    "latitude": 39.613354,
    "longitude": -121.83078,
    "timezone": "GMT",
    "hourly_units": {"time": "iso8601", "temperature_2m": "°F"},
    "hourly": {
        "time": ["2025-11-01T00:00", "2025-11-01T01:00", "2025-11-01T02:00", "2025-11-01T03:00"],
        "temperature_2m": [61.3, 58.9, None, 54.2],
    },
}


def client_returning(payload, status=200, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_archive_parses_hourly_fahrenheit_in_utc():
    seen = []
    s = openmeteo.fetch_archive_hourly(
        39.6, -121.8, date(2025, 11, 1), date(2025, 11, 1), client=client_returning(ARCHIVE_PAYLOAD, seen=seen)
    )
    assert str(s.index.tz) == "UTC"
    assert s.index[0].isoformat() == "2025-11-01T00:00:00+00:00"
    assert s.iloc[0] == 61.3
    assert np.isnan(s.iloc[2])  # null -> NaN

    params = seen[0].url.params
    assert seen[0].url.host == "archive-api.open-meteo.com"
    assert params["temperature_unit"] == "fahrenheit"
    assert params["timezone"] == "GMT"
    assert params["start_date"] == "2025-11-01"
    assert params["models"] == "best_match"


def test_forecast_requests_past_and_future_days():
    seen = []
    openmeteo.fetch_forecast_hourly(39.6, -121.8, client=client_returning(ARCHIVE_PAYLOAD, seen=seen))
    params = seen[0].url.params
    assert seen[0].url.host == "api.open-meteo.com"
    assert (params["past_days"], params["forecast_days"]) == ("10", "16")


def test_bad_request_raises_with_reason():
    payload = {"error": True, "reason": "Latitude must be in range of -90 to 90°."}
    with pytest.raises(openmeteo.OpenMeteoError, match="Latitude must be"):
        openmeteo.fetch_forecast_hourly(999, 0, client=client_returning(payload, status=400))


def test_wrong_unit_rejected():
    payload = {**ARCHIVE_PAYLOAD, "hourly_units": {"time": "iso8601", "temperature_2m": "°C"}}
    with pytest.raises(openmeteo.OpenMeteoError, match="°F"):
        openmeteo.fetch_forecast_hourly(39.6, -121.8, client=client_returning(payload))


def test_archive_end_trails_today():
    assert openmeteo.archive_end(date(2026, 10, 23)) == date(2026, 10, 17)


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_cache_hit_skips_fetch(monkeypatch):
    calls = []
    fetch = lambda: calls.append(1) or {"v": len(calls)}
    assert cache.get_or_fetch("k", fetch, ttl_seconds=60) == ({"v": 1}, False)
    assert cache.get_or_fetch("k", fetch, ttl_seconds=60) == ({"v": 1}, False)
    assert len(calls) == 1
    assert cache.entry_count() == 1


def test_cache_expires_after_ttl(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(cache, "now", clock)
    calls = []
    fetch = lambda: calls.append(1) or {"v": len(calls)}
    cache.get_or_fetch("k", fetch, ttl_seconds=60)
    clock.t += 61
    assert cache.get_or_fetch("k", fetch, ttl_seconds=60) == ({"v": 2}, False)


def test_forever_never_expires(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(cache, "now", clock)
    cache.get_or_fetch("k", lambda: {"v": 1}, ttl_seconds=cache.FOREVER)
    clock.t += 10**9
    assert cache.get_or_fetch("k", lambda: {"v": 2}, ttl_seconds=cache.FOREVER) == ({"v": 1}, False)


def test_stale_copy_served_when_refresh_fails(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(cache, "now", clock)
    cache.get_or_fetch("k", lambda: {"v": 1}, ttl_seconds=60)
    clock.t += 61

    def broken():
        raise openmeteo.OpenMeteoError("down")

    assert cache.get_or_fetch("k", broken, ttl_seconds=60) == ({"v": 1}, True)


def test_failure_without_cached_copy_raises():
    def broken():
        raise openmeteo.OpenMeteoError("down")

    with pytest.raises(openmeteo.OpenMeteoError):
        cache.get_or_fetch("missing", broken, ttl_seconds=60)


def test_openmeteo_second_call_served_from_cache():
    seen = []
    client = client_returning(ARCHIVE_PAYLOAD, seen=seen)
    first = openmeteo.fetch_archive_hourly(39.6, -121.8, date(2025, 11, 1), date(2025, 11, 1), client=client)
    second = openmeteo.fetch_archive_hourly(39.6, -121.8, date(2025, 11, 1), date(2025, 11, 1), client=client)
    assert len(seen) == 1
    assert second.equals(first)
    assert second.attrs["stale"] is False


def test_bad_payload_is_not_cached():
    payload = {**ARCHIVE_PAYLOAD, "hourly_units": {"time": "iso8601", "temperature_2m": "°C"}}
    with pytest.raises(openmeteo.OpenMeteoError):
        openmeteo.fetch_forecast_hourly(39.6, -121.8, client=client_returning(payload))
    assert cache.entry_count() == 0


def test_remember_reuses_result_until_ttl(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(cache, "now", clock)
    calls = []
    compute = lambda: calls.append(1) or len(calls)
    assert cache.remember("p", compute) == 1
    assert cache.remember("p", compute) == 1
    clock.t += cache.RESULT_TTL_SECONDS + 1
    assert cache.remember("p", compute) == 2
