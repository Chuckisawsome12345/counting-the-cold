import pytest
from fastapi.testclient import TestClient

from app.main import app
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
