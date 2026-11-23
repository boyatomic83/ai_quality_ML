"""FastAPI app for the AQI forecast.

Run locally (from the project root):
    .venv/bin/uvicorn backend.app.main:app --reload --port 7860
Interactive docs: http://localhost:7860/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .predictor import Predictor
from .schemas import CityList, Forecast, Health, History, Metrics

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models + data once when the server starts, not on every request.
    state["predictor"] = Predictor()
    yield
    state.clear()


app = FastAPI(
    title="AQI Forecast API",
    description="7-day AQI forecasts for 9 Indian cities (LightGBM, walk-forward validated).",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: the browser blocks a page on one domain (Vercel) from calling an API
# on another (Hugging Face) unless the API allows it. The API is read-only and
# public, so "*" is fine; set ALLOWED_ORIGINS to lock it to the frontend URL.
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"],
                   allow_headers=["*"])


def get_predictor() -> Predictor:
    return state["predictor"]


def resolve_city(city: str) -> str:
    """Case-insensitive city lookup ('delhi' -> 'Delhi'); 404 if not modelled."""
    lookup = {c.lower(): c for c in get_predictor().cities}
    name = lookup.get(city.strip().lower())
    if name is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown city '{city}'. Available: {', '.join(get_predictor().cities)}",
        )
    return name


@app.get("/", include_in_schema=False)
def root():
    return {"message": "AQI Forecast API. See /docs for endpoints."}


@app.get("/health", response_model=Health)
def health():
    p = get_predictor()
    return {"status": "ok", "model": p.metrics["best_model"], "data_end_date": p.data_end}


@app.get("/cities", response_model=CityList)
def cities():
    return {"cities": get_predictor().cities}


@app.get("/forecast", response_model=Forecast)
def forecast(
    city: str = Query(..., description="City name, e.g. Delhi"),
    days: int = Query(7, ge=1, le=7, description="Days ahead (1-7)"),
):
    return get_predictor().forecast(resolve_city(city), days)


@app.get("/history", response_model=History)
def history(
    city: str = Query(..., description="City name, e.g. Delhi"),
    days: int = Query(90, ge=1, le=365, description="Days of past data (1-365)"),
):
    return get_predictor().history_points(resolve_city(city), days)


@app.get("/metrics", response_model=Metrics)
def metrics():
    return get_predictor().metrics_table()
