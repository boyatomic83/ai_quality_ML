"""Error metrics and walk-forward fold definitions."""
import numpy as np
import pandas as pd

# Walk-forward validation: four consecutive 3-month test windows covering the
# last year of data. For each fold the model is trained ONLY on rows whose
# target date is before the fold starts (expanding window), then tested on
# the fold. This mimics using the model in real life, quarter by quarter.
# The folds cover monsoon (Jul-Sep), the winter spike (Oct-Dec, Jan-Mar)
# and the COVID lockdown (Apr-Jun 2020).
FOLDS = [
    ("2019-07-01", "2019-09-30"),
    ("2019-10-01", "2019-12-31"),
    ("2020-01-01", "2020-03-31"),
    ("2020-04-01", "2020-07-01"),
]


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mape(y, p):
    # Safe here: the minimum AQI in the data is 20, so no division by ~0.
    return float(np.mean(np.abs((y - p) / y)) * 100)


def score(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": round(mae(y, p), 2), "RMSE": round(rmse(y, p), 2),
            "MAPE": round(mape(y, p), 2)}


def score_table(preds: pd.DataFrame, model_cols: list[str], by: str | None = None) -> pd.DataFrame:
    """Metrics for each model column, optionally grouped (e.g. by City)."""
    if by is None:
        return pd.DataFrame({m: score(preds["target"], preds[m]) for m in model_cols}).T
    rows = []
    for key, g in preds.groupby(by):
        for m in model_cols:
            rows.append({by: key, "model": m, **score(g["target"], g[m])})
    return pd.DataFrame(rows)
