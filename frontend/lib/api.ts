// Typed client for the FastAPI backend. Types mirror backend/app/schemas.py.

// NEXT_PUBLIC_* variables are inlined into the browser bundle at build time.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860").replace(/\/$/, "");

export type ForecastPoint = {
  date: string;
  predicted_aqi: number;
  lower: number;
  upper: number;
  category: string;
};

export type Forecast = {
  city: string;
  model: string;
  interval: string;
  last_observed: { date: string; aqi: number; category: string };
  forecast: ForecastPoint[];
};

export type HistoryPoint = {
  date: string;
  actual: number | null;
  predicted: number;
  lower: number;
  upper: number;
};

export type History = { city: string; model: string; note: string; points: HistoryPoint[] };

export type ModelScore = { model: string; MAE: number; RMSE: number; MAPE: number };

export type Metrics = {
  best_model: string;
  selection_metric: string;
  validation: string;
  interval_coverage: number;
  overall: ModelScore[];
  per_city: Record<string, ModelScore[]>;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    // FastAPI puts error messages in `detail`.
    const body = await res.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  cities: () => get<{ cities: string[] }>("/cities").then((r) => r.cities),
  forecast: (city: string, days = 7) =>
    get<Forecast>(`/forecast?city=${encodeURIComponent(city)}&days=${days}`),
  history: (city: string, days = 90) =>
    get<History>(`/history?city=${encodeURIComponent(city)}&days=${days}`),
  metrics: () => get<Metrics>("/metrics"),
};
