"""Data loading and cleaning.

Pipeline:  raw CSV -> pick well-covered cities -> full daily calendar
           -> time interpolation of short gaps -> clean DataFrame
"""
import pandas as pd

from src.config import (DATA_PATH, MAX_INTERP_GAP, MIN_AQI_DAYS,
                        MIN_COVERAGE, POLLUTANTS)


def load_raw(path=DATA_PATH) -> pd.DataFrame:
    """Read the Kaggle CSV with Date parsed as a datetime."""
    return pd.read_csv(path, parse_dates=["Date"])


def city_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Per-city AQI coverage stats, used to choose which cities to model."""
    g = df.groupby("City")
    cov = pd.DataFrame({
        "first_date": g["Date"].min(),
        "last_date": g["Date"].max(),
        "aqi_days": g["AQI"].count(),
    })
    span = (cov["last_date"] - cov["first_date"]).dt.days + 1
    cov["coverage"] = (cov["aqi_days"] / span).round(3)
    return cov.sort_values("aqi_days", ascending=False)


def select_cities(df: pd.DataFrame) -> list[str]:
    """Cities that pass both the volume and coverage thresholds."""
    cov = city_coverage(df)
    keep = cov[(cov["aqi_days"] >= MIN_AQI_DAYS) & (cov["coverage"] >= MIN_COVERAGE)]
    return keep.index.tolist()


def _clean_one_city(city_df: pd.DataFrame) -> pd.DataFrame:
    """Reindex one city to every calendar day and fill short gaps."""
    s = city_df.set_index("Date").sort_index()
    # Start at the first day with an AQI value (earlier rows have no target).
    s = s.loc[s["AQI"].first_valid_index():]
    # asfreq("D") inserts rows for missing dates so gaps become explicit NaNs.
    s = s.asfreq("D")
    num_cols = ["AQI"] + POLLUTANTS
    # method="time" weights by the actual time distance between points;
    # limit_area="inside" means we never extrapolate past the ends; and
    # the gap-length mask stops us from bridging long outages.
    for col in num_cols:
        filled = s[col].interpolate(method="time", limit_area="inside")
        is_na = s[col].isna()
        gap_len = is_na.groupby((~is_na).cumsum()).transform("sum")
        s[col] = filled.where(~(is_na & (gap_len > MAX_INTERP_GAP)))
    s["City"] = city_df["City"].iloc[0]
    return s.reset_index()


def load_clean(cities: list[str] | None = None) -> pd.DataFrame:
    """Return the cleaned daily data for the selected cities.

    Columns: Date, City, AQI, pollutants. AQI may still be NaN inside long gaps.
    """
    raw = load_raw()
    if cities is None:
        cities = select_cities(raw)
    raw = raw[raw["City"].isin(cities)]
    parts = [_clean_one_city(g) for _, g in raw.groupby("City")]
    out = pd.concat(parts, ignore_index=True)
    return out[["Date", "City", "AQI"] + POLLUTANTS]
