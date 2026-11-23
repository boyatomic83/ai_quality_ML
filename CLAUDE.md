# AQI Forecast — project notes

Daily AQI forecasting (7-day horizon) for 9 Indian cities. Built in stages (EDA → model → FastAPI → Next.js → deploy → docs); the user approves each stage before the next.

## Setup
- venv: `.venv` built with `/usr/local/python/3.13.8/bin/python3` (system 3.12 lacks ensurepip; 3.14 lacks some wheels)
- `.venv/bin/pip install -r requirements.txt`
- Data: `data/city_day.csv` (gitignored, Kaggle "Air Quality Data in India")

## Structure
- `src/config.py` — constants (paths, city-selection thresholds, Diwali dates, horizon)
- `src/data.py` — load, select cities, daily reindex + interpolation
- `notebooks/eda.ipynb` — EDA; re-run with `.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/eda.ipynb`

## Decisions
- Cities: >=1100 AQI days and >=75% coverage → Delhi, Bengaluru, Lucknow, Chennai, Hyderabad, Patna, Gurugram, Visakhapatnam, Amritsar
- Missing values: time interpolation for gaps <= 7 days only; longer gaps stay NaN
- Classical model: SARIMA (statsmodels) rather than Prophet (avoids CmdStan in Docker)
- No same-day pollutants as features (unknown at forecast time); only past AQI + calendar
