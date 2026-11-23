"""Pydantic response models.

These define the exact JSON shape of every endpoint. FastAPI uses them to
validate our output and to generate the interactive docs at /docs.
"""
from datetime import date

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    model: str
    data_end_date: date


class CityList(BaseModel):
    cities: list[str]


class ForecastPoint(BaseModel):
    date: date
    predicted_aqi: float
    lower: float          # 10th percentile
    upper: float          # 90th percentile
    category: str


class LastObserved(BaseModel):
    date: date
    aqi: float
    category: str


class Forecast(BaseModel):
    city: str
    model: str
    interval: str
    last_observed: LastObserved
    forecast: list[ForecastPoint]


class HistoryPoint(BaseModel):
    date: date
    actual: float | None      # None if the sensor had no data that day
    predicted: float
    lower: float
    upper: float


class History(BaseModel):
    city: str
    model: str
    note: str
    points: list[HistoryPoint]


class ModelScore(BaseModel):
    model: str
    MAE: float
    RMSE: float
    MAPE: float


class Metrics(BaseModel):
    best_model: str
    selection_metric: str
    validation: str
    interval_coverage: float     # share of actuals that fell inside the 80% band
    overall: list[ModelScore]
    per_city: dict[str, list[ModelScore]]
