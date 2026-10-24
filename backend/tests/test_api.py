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


def test_public_models_api_describes_every_model():
    body = client.get("/api/v1/models", params=DURHAM_PIN).json()
    assert set(body["models"]) == {"chill_portions", "chill_hours", "utah_units", "gdd"}
    assert body["models"]["chill_portions"]["model"].startswith("Dynamic Model")
    assert body["models"]["gdd"]["unit"] == "°F-days" and "base 55" in body["models"]["gdd"]["model"]
    assert body["season"] == "2025-26" and body["nearest_station"]["name"] == "Durham"


def test_grid_empty_until_built(monkeypatch, tmp_path):
    from app.routes import grid as grid_route

    monkeypatch.setattr(grid_route, "GRID_DIR", tmp_path)
    body = client.get("/api/grid").json()
    assert body["built_at"] is None and body["cells"] == []


def test_grid_serves_one_metric(monkeypatch, tmp_path):
    import json

    from app.routes import grid as grid_route

    monkeypatch.setattr(grid_route, "GRID_DIR", tmp_path)
    (tmp_path / "2025.json").write_text(json.dumps({
        "season": "2025-26", "step_deg": 0.25, "built_at": "2026-10-24T02:00:00+00:00",
        "cells": [{"lat": 39.5, "lon": -121.75, "chill_portions": 61.8, "chill_hours": 980, "utah_units": 1300, "gdd": 2400}],
    }))
    body = client.get("/api/grid", params={"metric": "gdd"}).json()
    assert body["unit"] == "°F-days" and body["cells"] == [{"lat": 39.5, "lon": -121.75, "value": 2400}]
    assert client.get("/api/grid", params={"metric": "rainfall"}).status_code == 422


# --- text-message access (/api/sms) ---

import re  # noqa: E402

from app.routes import sms as sms_route  # noqa: E402


def text(body, **headers):
    r = client.post("/api/sms", data={"Body": body, "From": "+15550001111"}, headers=headers)
    m = re.search(r"<Message>(.*)</Message>", r.text, re.S)
    return r, (m.group(1) if m else None)


def test_sms_help_and_empty():
    for body in ("", "help", "  HELP "):
        r, msg = text(body)
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/xml")
        assert msg.startswith("Counting the Cold: text your orchard")


def test_sms_latlon_reply_fits_one_text():
    r, msg = text("39.64,-121.79")
    assert msg.startswith("Orchard near Durham ") and "chill portions" in msg and "chill hrs" in msg
    assert re.search(r"\d{4}-\d{2}:", msg)
    assert len(msg) <= 160 and msg.isascii()


def test_sms_place_name_and_parenthesised_latlon():
    assert text("Durham")[1].startswith("Durham ")
    assert text("(36.6, -119.5)")[1].startswith("Orchard near Parlier ")


def test_sms_outside_california_and_gibberish():
    assert "outside California" in text("47.6,-122.3")[1]
    assert text("what is chill")[1].startswith("Sorry, I didn't get that")


def test_sms_stop_gets_no_reply():
    r, msg = text("STOP")
    assert r.status_code == 200 and msg is None and "<Response></Response>" in r.text


def test_sms_signature_required_when_token_set(monkeypatch):
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "test-token")
    params = {"Body": "help", "From": "+15550001111"}
    good = sms_route.signature("http://testserver/api/sms", params, "test-token")
    assert client.post("/api/sms", data=params, headers={"X-Twilio-Signature": good}).status_code == 200
    assert client.post("/api/sms", data=params, headers={"X-Twilio-Signature": "forged"}).status_code == 403
    assert client.post("/api/sms", data=params).status_code == 403


def test_sms_signature_matches_twilio_reference():
    # Worked example from https://www.twilio.com/docs/usage/security ("Explore the algorithm yourself").
    params = {"Digits": "1234", "To": "+18005551212", "From": "+14158675310", "Caller": "+14158675310", "CallSid": "CA1234567890ABCDE"}
    assert sms_route.signature("https://example.com/myapp.php?foo=1&bar=2", params, "12345") == "L/OH5YylLD5NRKLltdqwSvS0BnU="


def test_sms_mentions_last_season_before_chill_starts():
    p = point_route._mock(2026)
    p["totals"] = dict.fromkeys(p["totals"], 0.0)
    msg = sms_route.summarize(p, "Durham")
    last = p["history"][-1]
    assert f"Last season ({last['season']}): {last['totals']['chill_hours']:.0f} chill hrs" in msg
    assert len(msg) <= 160


# --- Telegram bot (/api/telegram) ---

from app.routes import telegram as tg_route  # noqa: E402

TOKEN = "123456:test-token"


def tg(update, secret=None):
    headers = {"X-Telegram-Bot-Api-Secret-Token": tg_route.webhook_secret(TOKEN) if secret is None else secret}
    return client.post("/api/telegram", json=update, headers=headers)


def tg_text(text):
    return {"update_id": 1, "message": {"message_id": 7, "chat": {"id": 42, "type": "private"}, "text": text}}


def test_telegram_needs_token(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    assert tg(tg_text("/start")).status_code == 503


def test_telegram_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    assert tg(tg_text("/start"), secret="nope").status_code == 403


def test_telegram_start_place_and_location(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    start = tg(tg_text("/start")).json()
    assert start["method"] == "sendMessage" and start["chat_id"] == 42 and "Share your orchard's location" in start["text"]
    assert tg(tg_text("/durham@CountingTheColdBot")).json()["text"].startswith("Durham ")
    assert tg(tg_text("39.64, -121.79")).json()["text"].startswith("Orchard near Durham ")
    shared = {"update_id": 2, "message": {"message_id": 8, "chat": {"id": 42}, "location": {"latitude": 36.6, "longitude": -119.5}}}
    assert tg(shared).json()["text"].startswith("Orchard near Parlier ")
    assert "outside California" in tg(tg_text("47.6,-122.3")).json()["text"]


def test_telegram_ignores_non_message_updates(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    assert tg({"update_id": 3, "my_chat_member": {}}).json() == {}


def test_telegram_setup_registers_webhook_with_secret(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    calls = []
    monkeypatch.setattr(tg_route, "telegram_api", lambda token, method, payload: calls.append((method, payload)) or {"ok": True, "description": "Webhook was set"})
    body = client.get("/api/telegram/setup").json()
    assert body == {"ok": True, "webhook": "https://testserver/api/telegram", "telegram": "Webhook was set"}
    method, payload = calls[0]
    assert method == "setWebhook" and payload["secret_token"] == tg_route.webhook_secret(TOKEN)
    assert TOKEN not in str(body)
