"""Loads the saved artifacts once and answers forecast/history/metrics queries.

The dataset ends on a fixed date (2020-07-01), so the 7-day forecast for each
city never changes. We compute all of them once at startup and serve them
from memory. That keeps every request fast and makes the API deterministic.
"""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))  # so `src.*` (shared with training) is importable

from src.config import HORIZON, MODELS_DIR  # noqa: E402
from src.features import future_feature_rows  # noqa: E402
from src.models import predict_lgbm_bundle  # noqa: E402

from .aqi import aqi_category  # noqa: E402

MODEL_ORDER = ["Naive", "Seasonal Naive", "SARIMA", "LightGBM"]


class Predictor:
    def __init__(self, models_dir: Path = MODELS_DIR):
        self.bundle = joblib.load(models_dir / "lgbm_bundle.joblib")
        self.metrics = json.loads((models_dir / "metrics.json").read_text())
        self.history = pd.read_csv(models_dir / "aqi_history.csv", parse_dates=["Date"])
        self.backtest = pd.read_csv(models_dir / "backtest_h1.csv", parse_dates=["Date"])
        self.cities: list[str] = self.bundle["cities"]
        self.data_end = self.history["Date"].max().date()
        self._forecasts = {c: self._compute_forecast(c) for c in self.cities}

    # ------------------------------------------------------------- forecast
    def _compute_forecast(self, city: str) -> dict:
        # Same feature code as training, so train and serve cannot drift apart.
        rows = future_feature_rows(self.history, city)
        pred = predict_lgbm_bundle(self.bundle, rows)
        last = self.history[self.history["City"] == city].iloc[-1]
        points = [
            {
                "date": r.target_date.date(),
                "predicted_aqi": round(float(p.pred), 1),
                "lower": round(float(p.lower), 1),
                "upper": round(float(p.upper), 1),
                "category": aqi_category(p.pred),
            }
            for r, p in zip(rows.itertuples(), pred.itertuples())
        ]
        return {
            "last_observed": {
                "date": last["Date"].date(),
                "aqi": float(last["AQI"]),
                "category": aqi_category(last["AQI"]),
            },
            "points": points,
        }

    def forecast(self, city: str, days: int = HORIZON) -> dict:
        f = self._forecasts[city]
        return {
            "city": city,
            "model": "LightGBM",
            "interval": "80% (10th-90th percentile, quantile regression)",
            "last_observed": f["last_observed"],
            "forecast": f["points"][:days],
        }

    # -------------------------------------------------------------- history
    def history_points(self, city: str, days: int) -> dict:
        """Last `days` of out-of-sample 1-day-ahead backtest predictions.

        These come from walk-forward validation: each prediction was made by a
        model that had NOT seen that day, so this is an honest picture of how
        the model would have performed live.
        """
        bt = self.backtest[self.backtest["City"] == city].tail(days)
        points = [
            {
                "date": r.Date.date(),
                "actual": None if pd.isna(r.actual) else float(r.actual),
                "predicted": float(r.LightGBM),
                "lower": float(r.LightGBM_lower),
                "upper": float(r.LightGBM_upper),
            }
            for r in bt.itertuples()
        ]
        return {
            "city": city,
            "model": "LightGBM",
            "note": "Out-of-sample 1-day-ahead predictions from walk-forward validation",
            "points": points,
        }

    # -------------------------------------------------------------- metrics
    def metrics_table(self) -> dict:
        m = self.metrics

        def rows(scores: dict) -> list[dict]:
            return [{"model": name, **scores[name]} for name in MODEL_ORDER]

        return {
            "best_model": m["best_model"],
            "selection_metric": m["selection_metric"],
            "validation": m["validation"]["method"],
            "interval_coverage": m["lightgbm_interval"]["empirical_coverage"],
            "overall": rows(m["overall"]),
            "per_city": {city: rows(s) for city, s in m["per_city"].items()},
        }
