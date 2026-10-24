import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.routes import point as point_route
from app.sources import snapshots
from app.sources.openmeteo import OpenMeteoError
from app.pipeline import build_point
from app.sources import cache
from tests.test_pipeline import synthetic_hourly

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """No network in CI: once B's calc lands, /api/point runs on synthetic weather."""
    monkeypatch.setattr(build_point, "load_hourly", synthetic_hourly)
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "http.sqlite")
    cache.clear_results()
    monkeypatch.setattr(snapshots, "SNAPSHOT_DIR", tmp_path / "snapshots")


DURHAM_PIN = {"lat": 39.64, "lon": -121.79}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_point_complete_season():
    body = client.get("/api/point", params=DURHAM_PIN).json()
    assert body["season"]["label"] == "2025-26"
    assert set(body["totals"]) == {"chill_portions", "chill_hours", "utah_units", "gdd"}
    assert len(body["history"]) == 10
    assert body["forecast"] is None


def test_point_current_season_has_forecast():
    body = client.get("/api/point", params={**DURHAM_PIN, "season": 2026}).json()
    assert body["season"]["label"] == "2026-27"
    assert len(body["forecast"]["daily"]) == 16
    assert "climatology" in body  # null until B's projection lands


def test_point_rejects_outside_california():
    assert client.get("/api/point", params={"lat": 47.6, "lon": -122.3}).status_code == 422


def test_stations_include_closed_durham():
    stations = {s["id"]: s for s in client.get("/api/stations").json()["stations"]}
    assert len(stations) == 9
    assert stations[12]["active"] is False
    assert stations[12]["disconnect_date"] == "2025-07-30"


def test_crops_and_validation():
    assert any(c["id"] == "almond" for c in client.get("/api/crops").json()["crops"])
    assert client.get("/api/validation").status_code == 200


def test_point_rejects_unknown_crop():
    assert client.get("/api/point", params={**DURHAM_PIN, "crop": "kiwi"}).status_code == 422


def saved_snapshot(season=2025):
    body = point_route._mock(season)
    snapshots.save_snapshot(DURHAM_PIN["lat"], DURHAM_PIN["lon"], season, body)
    return body


def test_demo_mode_serves_snapshot(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    body = saved_snapshot()
    assert client.get("/api/point", params=DURHAM_PIN).json()["totals"] == body["totals"]


def test_demo_mode_refuses_spots_without_snapshot(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    r = client.get("/api/point", params={"lat": 36.6, "lon": -119.5})
    assert r.status_code == 503 and "demo pins" in r.json()["detail"]


def outage(*args, **kwargs):
    raise OpenMeteoError("Open-Meteo 503: down")


def test_outage_falls_back_to_snapshot_marked_stale(monkeypatch):
    monkeypatch.setattr(point_route, "build_point", outage)
    saved_snapshot()
    body = client.get("/api/point", params=DURHAM_PIN).json()
    assert body["quality"]["stale"] is True


def test_outage_without_snapshot_is_clear_503(monkeypatch):
    monkeypatch.setattr(point_route, "build_point", outage)
    r = client.get("/api/point", params=DURHAM_PIN)
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]
