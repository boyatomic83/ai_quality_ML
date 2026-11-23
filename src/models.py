"""The three model families we compare.

1. Baselines   - naive (last known value) and seasonal naive (same weekday last week)
2. SARIMA      - one classical statistical model per city
3. LightGBM    - one global gradient-boosted tree model for all cities

Every model produces predictions for the same rows of the feature table,
so the comparison is apples-to-apples.
"""
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from src.features import FEATURE_COLS

# ---------------------------------------------------------------- baselines

def predict_naive(rows: pd.DataFrame) -> np.ndarray:
    """Tomorrow (and every day of next week) = today's AQI."""
    return rows["lag_1"].to_numpy()


def predict_seasonal_naive(rows: pd.DataFrame) -> np.ndarray:
    """AQI on the target day = AQI on the same weekday one week earlier."""
    return rows["seasonal_naive"].to_numpy()


# ------------------------------------------------------------------ SARIMA
# SARIMA(1,1,1)(1,0,1)[7] on log(1 + AQI):
#   - d=1 (one difference) removes the slowly-moving level, so the model
#     focuses on day-to-day changes.
#   - AR(1)/MA(1) capture short-term persistence and shocks.
#   - The seasonal (1,0,1) terms with period 7 capture the weekly cycle.
#   - A yearly season (period 365) is impractical for SARIMA (huge state
#     space), which is one of its weaknesses compared with LightGBM.
#   - log1p tames AQI's right skew and keeps forecasts positive.
SARIMA_ORDER = (1, 1, 1)
SARIMA_SEASONAL = (1, 0, 1, 7)


def fit_sarima(series: pd.Series):
    """Fit SARIMA on one city's daily AQI series (NaNs are handled by the Kalman filter)."""
    # Imported here, not at the top, so the API (which only uses LightGBM)
    # does not need statsmodels/scipy installed -> smaller Docker image.
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(np.log1p(series), order=SARIMA_ORDER,
                        seasonal_order=SARIMA_SEASONAL)
        return model.fit(disp=False)


def predict_sarima(fitted, full_series: pd.Series, rows: pd.DataFrame) -> np.ndarray:
    """Walk-forward 1..7-day forecasts with parameters fixed from training.

    `apply` runs the already-fitted model over the longer series WITHOUT
    re-estimating parameters. For each origin day we then forecast
    dynamically: after the origin the model only sees its own predictions,
    never the real future values (verified to equal forecasting from a series
    truncated at the origin).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        applied = fitted.apply(np.log1p(full_series))
    index = full_series.index
    out = pd.Series(np.nan, index=rows.index)
    for origin, grp in rows.groupby("origin_date"):
        o = index.get_loc(origin)
        pred = applied.get_prediction(start=o + 1, end=o + 7, dynamic=True).predicted_mean
        pred = np.expm1(pred.to_numpy())
        out.loc[grp.index] = pred[grp["horizon"].to_numpy() - 1]
    return out.to_numpy()


# ---------------------------------------------------------------- LightGBM
# Moderate settings that train in seconds on a CPU. Small learning rate +
# a few hundred trees, subsampling for robustness, min_child_samples to
# avoid fitting tiny groups of noisy days.
LGBM_PARAMS = dict(
    n_estimators=600,
    learning_rate=0.03,
    num_leaves=31,
    min_child_samples=50,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1,
)


def _X(rows: pd.DataFrame, cities: list[str]) -> pd.DataFrame:
    X = rows[FEATURE_COLS].copy()
    # A fixed category list keeps the city encoding identical at train and predict time.
    X["City"] = pd.Categorical(X["City"], categories=cities)
    return X


# Target transform: instead of raw AQI, LightGBM learns the RELATIVE change
# from today's value:  y = log(AQI[t+h] / AQI[t]).
#   - Puts all cities on one scale (Delhi ~260 vs Bengaluru ~95 average AQI),
#     so the shared seasonal/weekly/Diwali patterns are learned once.
#   - "No change" (y = 0) is the natural default, so the model starts from
#     the strong naive baseline and learns corrections to it.
#   - Quantiles survive monotone transforms, so the 10th/90th percentile
#     of y map straight back to 10th/90th percentile of AQI.
# Walk-forward comparison (MAE): raw AQI 30.96 -> relative change 30.26.

def _to_target(rows: pd.DataFrame) -> pd.Series:
    return np.log(rows["target"] / rows["lag_1"])


def _from_target(rows: pd.DataFrame, y: np.ndarray) -> np.ndarray:
    return rows["lag_1"].to_numpy() * np.exp(y)


def fit_lgbm(train: pd.DataFrame, cities: list[str], objective="regression_l1", alpha=None):
    """Train one LightGBM model.

    objective="regression_l1" (MAE loss) predicts the median, which is robust to
    AQI's extreme spikes (it beat squared-error loss in validation).
    objective="quantile" with alpha=0.1 / 0.9 gives the lower / upper edges of
    a nominal 80% prediction interval.
    """
    params = dict(LGBM_PARAMS, objective=objective)
    if alpha is not None:
        params["alpha"] = alpha
    model = lgb.LGBMRegressor(**params)
    model.fit(_X(train, cities), _to_target(train))
    return model


def predict_lgbm(model, rows: pd.DataFrame, cities: list[str]) -> np.ndarray:
    return _from_target(rows, model.predict(_X(rows, cities)))


def fit_lgbm_bundle(train: pd.DataFrame, cities: list[str]) -> dict:
    """Point model + 10th/90th percentile models."""
    return {
        "point": fit_lgbm(train, cities),
        "q10": fit_lgbm(train, cities, objective="quantile", alpha=0.1),
        "q90": fit_lgbm(train, cities, objective="quantile", alpha=0.9),
        "cities": cities,
        "features": FEATURE_COLS,
    }


def predict_lgbm_bundle(bundle: dict, rows: pd.DataFrame) -> pd.DataFrame:
    """Point forecast + interval. Quantile models are trained separately so they
    can occasionally 'cross'; we sort them so lower <= point <= upper."""
    cities = bundle["cities"]
    point = predict_lgbm(bundle["point"], rows, cities)
    lo = predict_lgbm(bundle["q10"], rows, cities)
    hi = predict_lgbm(bundle["q90"], rows, cities)
    lo, hi = np.minimum(lo, point), np.maximum(hi, point)
    return pd.DataFrame({"pred": point, "lower": np.clip(lo, 0, None), "upper": hi},
                        index=rows.index)
