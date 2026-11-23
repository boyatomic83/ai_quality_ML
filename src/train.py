"""Train, evaluate and save all models.

Usage:  python src/train.py      (from the project root)

Steps
  1. Load + clean data for the selected cities.
  2. Build the (city, origin, horizon) feature table.
  3. Walk-forward validation over 4 quarterly folds: fit each model on the
     past, predict the next quarter, collect out-of-sample predictions.
  4. Compute MAE / RMSE / MAPE overall, per city, per horizon, per fold.
  5. Retrain the final LightGBM models (point + 10th/90th quantiles) on ALL
     data and save them, plus everything the API needs, to models/.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))  # allow `python src/train.py`

from src.config import HORIZON, MODELS_DIR  # noqa: E402
from src.data import load_clean  # noqa: E402
from src.evaluate import FOLDS, score, score_table  # noqa: E402
from src.features import make_features  # noqa: E402
from src.models import (fit_lgbm_bundle, fit_sarima, predict_lgbm_bundle,  # noqa: E402
                        predict_naive, predict_sarima, predict_seasonal_naive)

MODEL_NAMES = ["Naive", "Seasonal Naive", "SARIMA", "LightGBM"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_fold(clean, feats, cities, start, end):
    """Train on everything before `start`, predict rows whose target is in [start, end]."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    has_inputs = feats["target"].notna() & feats["lag_1"].notna()

    # Training rows: the TARGET must be before the fold, so no future label leaks in.
    train = feats[has_inputs & (feats["target_date"] < start)]
    # Test rows: forecasts made during the fold (origin >= day before fold start).
    test = feats[has_inputs & feats["seasonal_naive"].notna()
                 & (feats["origin_date"] >= start - pd.Timedelta(days=1))
                 & (feats["target_date"] <= end)].copy()

    test["Naive"] = predict_naive(test)
    test["Seasonal Naive"] = predict_seasonal_naive(test)

    # SARIMA: one model per city, fitted on that city's history before the fold.
    test["SARIMA"] = np.nan
    for city in cities:
        s = clean[clean["City"] == city].set_index("Date")["AQI"].asfreq("D")
        fitted = fit_sarima(s[: start - pd.Timedelta(days=1)])
        rows = test[test["City"] == city]
        test.loc[rows.index, "SARIMA"] = predict_sarima(fitted, s[:end], rows)

    # LightGBM: one global model across all cities.
    bundle = fit_lgbm_bundle(train, cities)
    lgb_pred = predict_lgbm_bundle(bundle, test)
    test["LightGBM"] = lgb_pred["pred"]
    test["LightGBM_lower"] = lgb_pred["lower"]
    test["LightGBM_upper"] = lgb_pred["upper"]
    test["fold"] = f"{start.date()}..{end.date()}"
    return test


def nested(table: pd.DataFrame, key: str) -> dict:
    """Long metrics table -> {key_value: {model: {MAE, RMSE, MAPE}}}."""
    out = {}
    for _, r in table.iterrows():
        out.setdefault(str(r[key]), {})[r["model"]] = {m: r[m] for m in ("MAE", "RMSE", "MAPE")}
    return out


def main():
    MODELS_DIR.mkdir(exist_ok=True)

    log("Loading and cleaning data")
    clean = load_clean()
    cities = sorted(clean["City"].unique())
    feats = make_features(clean)
    log(f"{len(cities)} cities, {len(feats):,} feature rows")

    # ---- 1. Walk-forward validation
    results = []
    for start, end in FOLDS:
        log(f"Fold {start} -> {end}")
        results.append(run_fold(clean, feats, cities, start, end))
    bt = pd.concat(results, ignore_index=True)

    # ---- 2. Metrics
    overall = score_table(bt, MODEL_NAMES)
    best = overall["MAE"].idxmin()
    coverage = float(((bt["target"] >= bt["LightGBM_lower"])
                      & (bt["target"] <= bt["LightGBM_upper"])).mean())
    per_city = score_table(bt, MODEL_NAMES, by="City")
    per_h = score_table(bt, MODEL_NAMES, by="horizon")
    per_fold = score_table(bt, MODEL_NAMES, by="fold")

    print("\n=== Overall (walk-forward, all horizons 1-7) ===")
    print(overall.sort_values("MAE").to_string())
    print(f"\nBest model by MAE: {best}")
    print(f"LightGBM 80% interval coverage: {coverage:.1%}")
    print("\n=== MAE per city ===")
    print(per_city.pivot(index="City", columns="model", values="MAE")[MODEL_NAMES].to_string())
    print("\n=== MAE per horizon ===")
    print(per_h.pivot(index="horizon", columns="model", values="MAE")[MODEL_NAMES].to_string())
    print("\n=== MAE per fold ===")
    print(per_fold.pivot(index="fold", columns="model", values="MAE")[MODEL_NAMES].to_string())

    metrics = {
        "best_model": best,
        "selection_metric": "MAE",
        "validation": {
            "method": "walk-forward, expanding window, 4 quarterly folds",
            "folds": [{"start": s, "end": e} for s, e in FOLDS],
            "horizon_days": HORIZON,
            "n_test_rows": int(len(bt)),
        },
        "overall": {m: overall.loc[m].to_dict() for m in MODEL_NAMES},
        "per_city": nested(per_city, "City"),
        "per_horizon": nested(per_h, "horizon"),
        "per_fold": nested(per_fold, "fold"),
        "lightgbm_interval": {"nominal": 0.8, "empirical_coverage": round(coverage, 3)},
        "cities": cities,
        "data_end_date": str(clean["Date"].max().date()),
    }
    (MODELS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # ---- 3. Final model on all available data
    log("Training final LightGBM models on all data")
    train_all = feats[feats["target"].notna() & feats["lag_1"].notna()]
    bundle = fit_lgbm_bundle(train_all, cities)
    joblib.dump(bundle, MODELS_DIR / "lgbm_bundle.joblib")

    # ---- 4. Data the API needs
    # Cleaned daily AQI history (to build features for new forecasts).
    clean[["Date", "City", "AQI"]].to_csv(MODELS_DIR / "aqi_history.csv", index=False)
    # Out-of-sample 1-day-ahead backtest predictions for the "actual vs predicted" chart.
    h1 = bt[bt["horizon"] == 1][["target_date", "City", "target"] + MODEL_NAMES
                                 + ["LightGBM_lower", "LightGBM_upper"]]
    h1 = h1.rename(columns={"target_date": "Date", "target": "actual"}).round(1)
    h1.sort_values(["City", "Date"]).to_csv(MODELS_DIR / "backtest_h1.csv", index=False)

    log(f"Saved models and metrics to {MODELS_DIR}")


if __name__ == "__main__":
    main()
