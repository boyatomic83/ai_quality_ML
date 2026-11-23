"""Feature engineering for direct multi-horizon forecasting.

Setup ("direct" strategy):
    For every city and every forecast ORIGIN day t (the last day we have data
    for), we create HORIZON rows, one per h = 1..7. Each row says:
        "Given what we know at the end of day t, predict AQI on day t + h."

    - Lag / rolling features only use AQI up to and including day t,
      so they are always known at forecast time -> no data leakage.
    - Calendar / festival features describe the TARGET day t + h,
      which is fine because the calendar is known in advance.
    - `horizon` (h) is itself a feature, so one model learns that predicting
      7 days ahead is harder than predicting tomorrow.

Naming: lag_k = AQI k days before the first forecast day (t + 1),
so lag_1 = AQI on day t (the latest known value), lag_7 = AQI on t - 6, etc.
"""
import numpy as np
import pandas as pd

from src.config import DIWALI_DATES, HORIZON

LAGS = [1, 2, 3, 7, 14, 30]
ROLL_WINDOWS = [7, 14, 30]
WINTER_MONTHS = {11, 12, 1}

_DIWALI = pd.to_datetime(DIWALI_DATES)

# Features that also get a "relative to today's AQI" version.
REL_BASE = ([f"lag_{k}" for k in LAGS if k > 1]
            + [f"roll_{s}_{w}" for w in ROLL_WINDOWS for s in ("mean", "std")])


def _days_from_nearest_diwali(dates: pd.Series) -> np.ndarray:
    """Signed distance in days to the closest Diwali (negative = before)."""
    d = dates.values.astype("datetime64[D]")[:, None]
    diffs = (d - _DIWALI.values.astype("datetime64[D]")[None, :]).astype(int)
    idx = np.abs(diffs).argmin(axis=1)
    return diffs[np.arange(len(diffs)), idx]


def add_calendar_features(df: pd.DataFrame, date_col: str = "target_date") -> pd.DataFrame:
    """Calendar + festival features for the day being predicted."""
    d = df[date_col]
    df["day_of_week"] = d.dt.dayofweek
    df["month"] = d.dt.month
    df["day_of_year"] = d.dt.dayofyear
    df["is_winter"] = d.dt.month.isin(WINTER_MONTHS).astype(int)
    dist = _days_from_nearest_diwali(d)
    df["is_diwali"] = (dist == 0).astype(int)
    df["is_post_diwali"] = (dist == 1).astype(int)   # 24h-average AQI peaks the day after
    df["near_diwali"] = (np.abs(dist) <= 3).astype(int)
    return df


def _origin_features(s: pd.Series) -> pd.DataFrame:
    """Features known at the end of each origin day, for one city's daily series."""
    f = pd.DataFrame(index=s.index)
    for k in LAGS:
        f[f"lag_{k}"] = s.shift(k - 1)
    for w in ROLL_WINDOWS:
        # Window ends at day t (inclusive). min_periods tolerates a few NaNs.
        roll = s.rolling(w, min_periods=w // 2)
        f[f"roll_mean_{w}"] = roll.mean()
        f[f"roll_std_{w}"] = roll.std()
    # Relative versions: each feature divided by today's AQI. The model predicts
    # the *relative* change from today (see models.py), so it helps to see
    # e.g. "last week was 30% higher than today" directly; a tree cannot easily
    # compute a ratio of two columns by itself.
    for c in REL_BASE:
        f[f"{c}_rel"] = f[c] / f["lag_1"]
    return f


def make_features(clean: pd.DataFrame) -> pd.DataFrame:
    """Build the long (city, origin, horizon) feature table.

    `clean` is the output of src.data.load_clean (one row per city per day).
    The `target` column is NaN where the future AQI is unknown (e.g. the
    last 7 days of data, or inside long gaps); callers filter as needed.
    """
    parts = []
    for city, g in clean.groupby("City"):
        s = g.set_index("Date")["AQI"].asfreq("D")
        base = _origin_features(s)
        for h in range(1, HORIZON + 1):
            part = base.copy()
            part["horizon"] = h
            part["target"] = s.shift(-h)
            # Seasonal-naive baseline: AQI exactly 7 days before the target day.
            # Since h <= 7, that day is always <= t, so it's known at forecast time.
            part["seasonal_naive"] = s.shift(7 - h)
            part["City"] = city
            part["origin_date"] = part.index
            part["target_date"] = part.index + pd.Timedelta(days=h)
            parts.append(part)
    out = pd.concat(parts, ignore_index=True)
    return add_calendar_features(out)


def future_feature_rows(clean: pd.DataFrame, city: str) -> pd.DataFrame:
    """The 7 rows needed to forecast the next HORIZON days for one city."""
    city_df = clean[clean["City"] == city]
    feats = make_features(city_df)
    last = city_df["Date"].max()
    return feats[feats["origin_date"] == last].sort_values("horizon").reset_index(drop=True)


FEATURE_COLS = (
    [f"lag_{k}" for k in LAGS]
    + [f"roll_{s}_{w}" for w in ROLL_WINDOWS for s in ("mean", "std")]
    + [f"{c}_rel" for c in REL_BASE]
    + ["horizon", "day_of_week", "month", "day_of_year", "is_winter",
       "is_diwali", "is_post_diwali", "near_diwali", "City"]
)
