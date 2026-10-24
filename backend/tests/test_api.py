from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
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
    assert body["climatology"] is not None


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
