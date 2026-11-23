"""Endpoint tests. Run from the project root:  .venv/bin/pytest"""
import pytest
from fastapi.testclient import TestClient

from backend.app.aqi import aqi_category
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    # Using TestClient as a context manager runs the startup (model loading).
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------ /health
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model"] == "LightGBM"
    assert body["data_end_date"] == "2020-07-01"


# ------------------------------------------------------------------ /cities
def test_cities(client):
    r = client.get("/cities")
    assert r.status_code == 200
    cities = r.json()["cities"]
    assert len(cities) == 9
    assert "Delhi" in cities


# ---------------------------------------------------------------- /forecast
def test_forecast_default_7_days(client):
    r = client.get("/forecast", params={"city": "Delhi"})
    assert r.status_code == 200
    body = r.json()
    assert body["city"] == "Delhi"
    assert body["last_observed"]["date"] == "2020-07-01"
    pts = body["forecast"]
    assert len(pts) == 7
    assert pts[0]["date"] == "2020-07-02" and pts[-1]["date"] == "2020-07-08"
    for p in pts:
        assert 0 <= p["lower"] <= p["predicted_aqi"] <= p["upper"]
        assert p["category"] == aqi_category(p["predicted_aqi"])


def test_forecast_days_and_case_insensitive_city(client):
    r = client.get("/forecast", params={"city": "  delhi ", "days": 3})
    assert r.status_code == 200
    assert r.json()["city"] == "Delhi"
    assert len(r.json()["forecast"]) == 3


@pytest.mark.parametrize("days", [0, 8, "abc"])
def test_forecast_invalid_days(client, days):
    r = client.get("/forecast", params={"city": "Delhi", "days": days})
    assert r.status_code == 422


def test_forecast_unknown_city(client):
    r = client.get("/forecast", params={"city": "Atlantis"})
    assert r.status_code == 404
    assert "Available" in r.json()["detail"]


def test_forecast_missing_city(client):
    assert client.get("/forecast").status_code == 422


# ----------------------------------------------------------------- /history
def test_history_default_90_days(client):
    r = client.get("/history", params={"city": "Bengaluru"})
    assert r.status_code == 200
    pts = r.json()["points"]
    assert len(pts) == 90
    assert pts[-1]["date"] == "2020-07-01"
    dates = [p["date"] for p in pts]
    assert dates == sorted(dates)
    assert all(p["predicted"] > 0 for p in pts)


def test_history_invalid(client):
    assert client.get("/history", params={"city": "Delhi", "days": 0}).status_code == 422
    assert client.get("/history", params={"city": "Delhi", "days": 366}).status_code == 422
    assert client.get("/history", params={"city": "Nowhere"}).status_code == 404


# ----------------------------------------------------------------- /metrics
def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["best_model"] == "LightGBM"
    models = {row["model"]: row for row in body["overall"]}
    assert set(models) == {"Naive", "Seasonal Naive", "SARIMA", "LightGBM"}
    # The best model must actually have the lowest MAE.
    assert min(models, key=lambda m: models[m]["MAE"]) == "LightGBM"
    assert len(body["per_city"]) == 9
    assert 0 < body["interval_coverage"] < 1


# ------------------------------------------------------------- CORS + utils
def test_cors_header(client):
    r = client.get("/cities", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")


@pytest.mark.parametrize("aqi,expected", [
    (0, "Good"), (50, "Good"), (50.4, "Good"), (51, "Satisfactory"),
    (100, "Satisfactory"), (101, "Moderate"), (200, "Moderate"), (201, "Poor"),
    (300, "Poor"), (301, "Very Poor"), (400, "Very Poor"), (401, "Severe"), (999, "Severe"),
])
def test_aqi_category(aqi, expected):
    assert aqi_category(aqi) == expected
