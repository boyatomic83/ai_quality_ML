"use client";

// The whole dashboard is one client page: it calls the FastAPI backend from
// the browser, so the frontend can be a static site on Vercel.
import { useCallback, useEffect, useState } from "react";
import { AqiCard } from "@/components/AqiCard";
import { ForecastChart, HistoryChart } from "@/components/charts";
import { HowItWorks } from "@/components/HowItWorks";
import { MetricsTable } from "@/components/MetricsTable";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Card, ErrorState, Skeleton } from "@/components/ui";
import { api, type Forecast, type History } from "@/lib/api";
import { formatDate } from "@/lib/aqi";

const GITHUB_URL = "https://github.com/boyatomic83/ai_quality_ML";
const DEFAULT_CITY = "Delhi";

type Async<T> = { data?: T; error?: string; loading: boolean };

/** Runs `load` whenever its dependencies change; returns data/error/loading + a retry. */
function useAsync<T>(load: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<Async<T>>({ loading: true });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false; // ignore stale responses if the city changes mid-request
    setState((s) => ({ data: s.data, loading: true }));
    load()
      .then((data) => !cancelled && setState({ data, loading: false }))
      .catch((e: Error) => !cancelled && setState({ error: e.message, loading: false }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);
  return { ...state, retry: () => setAttempt((a) => a + 1) };
}

export default function Home() {
  const [city, setCity] = useState(DEFAULT_CITY);

  const cities = useAsync(api.cities, []);
  const metrics = useAsync(api.metrics, []);
  // Fetch forecast + history together so the forecast chart can show recent actuals.
  const cityData = useAsync<{ forecast: Forecast; history: History }>(
    useCallback(async () => {
      const [forecast, history] = await Promise.all([api.forecast(city), api.history(city, 90)]);
      return { forecast, history };
    }, [city]),
    [city],
  );

  // Show skeletons on first load or when switching city (old data would be misleading).
  const showCity = cityData.data && cityData.data.forecast.city === city ? cityData.data : undefined;

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      {/* 1. Header */}
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-accent">Machine learning · Time series</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-4xl">AQI Forecast for Indian Cities</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted sm:text-base">
            7-day air quality forecasts for 9 cities, made by a LightGBM model trained on 5 years of
            CPCB data, with an 80% prediction interval.
          </p>
        </div>
        <ThemeToggle />
      </header>

      {/* 2. City selector */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <label className="flex items-center gap-3 text-sm font-medium">
          City
          {cities.error ? (
            <span className="text-red-600 dark:text-red-400">unavailable</span>
          ) : (
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={!cities.data}
              className="min-w-48 rounded-xl border border-border bg-surface px-3 py-2 text-base shadow-sm focus:outline-2 focus:outline-accent"
            >
              {(cities.data ?? [DEFAULT_CITY]).map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          )}
        </label>
        {showCity && (
          <p className="text-xs text-muted">
            The dataset ends on {formatDate(showCity.forecast.last_observed.date)}, so that day is
            &ldquo;today&rdquo; and the forecast covers the following week.
          </p>
        )}
      </div>

      {cityData.error ? (
        <ErrorState message={cityData.error} onRetry={cityData.retry} />
      ) : (
        <>
          {/* 3. Today / Tomorrow */}
          <Card title={`Air quality in ${city}`}>
            {showCity ? <AqiCard data={showCity.forecast} /> : <Skeleton className="h-72" />}
          </Card>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* 4. 7-day forecast */}
            <Card title="7-day forecast" subtitle="Last two weeks of measurements, then the forecast with its likely range">
              {showCity ? (
                <ForecastChart forecast={showCity.forecast} recent={showCity.history.points} />
              ) : (
                <Skeleton className="h-[340px]" />
              )}
            </Card>

            {/* 5. Actual vs predicted */}
            <Card title="Actual vs predicted · last 90 days" subtitle="How the model did on days it had never seen">
              {showCity ? <HistoryChart points={showCity.history.points} /> : <Skeleton className="h-[340px]" />}
            </Card>
          </div>
        </>
      )}

      {/* 6. Model comparison */}
      <Card title="Model comparison" subtitle="Average forecast error in AQI points (walk-forward validation, Jul 2019 – Jul 2020)">
        {metrics.error ? (
          <ErrorState message={metrics.error} onRetry={metrics.retry} />
        ) : metrics.data ? (
          <MetricsTable metrics={metrics.data} city={city} />
        ) : (
          <Skeleton className="h-64" />
        )}
      </Card>

      {/* 7. How it works */}
      <Card title="How it works">
        <HowItWorks />
      </Card>

      {/* 8. Footer */}
      <footer className="mt-auto flex flex-col gap-2 border-t border-border pt-6 text-sm text-muted sm:flex-row sm:justify-between">
        <p>Data: Kaggle &ldquo;Air Quality Data in India&rdquo; (CPCB). Built with FastAPI, LightGBM and Next.js.</p>
        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="font-medium text-accent hover:underline">
          View source on GitHub →
        </a>
      </footer>
    </div>
  );
}
