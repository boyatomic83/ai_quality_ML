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

## Modelling (Stage 2)
- Train: `.venv/bin/python src/train.py` (~3 min CPU) → writes `models/{lgbm_bundle.joblib, metrics.json, aqi_history.csv, backtest_h1.csv}`
- `src/features.py` — direct multi-horizon table: one row per (city, origin day t, horizon h=1..7); lags/rolling use data <= t, calendar/Diwali describe t+h
- `src/models.py` — Naive, Seasonal Naive, SARIMA(1,1,1)(1,0,1)[7] on log1p per city, global LightGBM
- LightGBM target = log(AQI[t+h] / AQI[t]) (relative change), L1 loss; q10/q90 quantile models for the band; plus *_rel features (feature / lag_1)
- `src/evaluate.py` — 4 quarterly walk-forward folds, Jul 2019 – Jul 2020
- Result: LightGBM MAE 30.25 vs SARIMA 31.89 vs Naive 35.78; band coverage 72% (nominal 80%)
- Data ends 2020-07-01, so "forecast" = 2020-07-02..08

## Backend (Stage 3)
- `backend/app/main.py` (routes, CORS via ALLOWED_ORIGINS env, default `*`), `predictor.py` (loads models/ once, precomputes all 7-day forecasts at startup), `schemas.py` (Pydantic), `aqi.py` (CPCB bands, value rounded first)
- Reuses `src.features`/`src.models` so serving uses identical feature code; statsmodels import in `src/models.py` is lazy so the image doesn't need it
- Run: `.venv/bin/uvicorn backend.app.main:app --reload --port 7860`; tests: `.venv/bin/pytest` (pytest.ini sets pythonpath)
- /history serves out-of-sample h=1 walk-forward predictions (backtest_h1.csv), max 365 days
- Docker: build from repo root `docker build -f backend/Dockerfile -t aqi-api .`; runs as uid 1000 on port 7860 (HF Spaces)
- Codespace quirk: container HTTPS hangs (MTU). Build locally with `docker network create --opt com.docker.network.driver.mtu=1200 lowmtu` + `DOCKER_BUILDKIT=0 docker build --network lowmtu ...`

## Frontend (Stage 4)
- `frontend/` Next.js 15 App Router + Tailwind v4 + Recharts 2 + next-themes (class-based dark mode, tokens in `app/globals.css`)
- `app/page.tsx` is one client page (fetches from the browser → static site on Vercel); `lib/api.ts` types mirror backend schemas; `lib/aqi.ts` CPCB colours + health tips
- API base = `NEXT_PUBLIC_API_URL`. In Codespaces use `/backend` (`.env.local`) → Next rewrite proxies to `API_PROXY_TARGET` (default localhost:7860), so the API port can stay private
- Run: `cd frontend && npm run dev`; check: `npx tsc --noEmit && npm run lint && npm run build`
- Recharts ResponsiveContainer inside CSS grid needs `min-w-0` on the grid item (Card has it) or charts collapse
