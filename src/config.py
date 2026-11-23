"""Project-wide constants: paths, chosen cities, festival dates.

Keeping these in one place means the notebook, training script and API
all agree on the same settings.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "city_day.csv"
MODELS_DIR = ROOT / "models"

# Selection rule (see notebooks/eda.ipynb): a city needs >= 1100 days with an
# AQI value AND >= 75% coverage over its own date range.
MIN_AQI_DAYS = 1100
MIN_COVERAGE = 0.75

# Gaps up to this many consecutive days are filled by time interpolation.
# Longer gaps (e.g. sensor outages of several months) stay missing, because
# a straight line across months would be invented data.
MAX_INTERP_GAP = 7

POLLUTANTS = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3",
              "Benzene", "Toluene", "Xylene"]

# Diwali dates (the main firecracker night). 2020/2021 are included so
# future forecast dates can also be flagged.
DIWALI_DATES = ["2015-11-11", "2016-10-30", "2017-10-19", "2018-11-07",
                "2019-10-27", "2020-11-14", "2021-11-04"]

# Start of India's nationwide COVID-19 lockdown.
LOCKDOWN_START = "2020-03-25"

# Forecast horizon in days.
HORIZON = 7
