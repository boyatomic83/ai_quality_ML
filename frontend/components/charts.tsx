"use client";

// Both charts use the same colours: blue = model prediction (+ shaded band),
// orange = measured AQI. Colours come from CSS variables in globals.css so
// they switch automatically in dark mode.
import {
  Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Forecast, HistoryPoint } from "@/lib/api";
import { formatDate } from "@/lib/aqi";

type Row = {
  date: string;
  actual?: number | null;
  predicted?: number;
  band?: [number, number]; // [lower, upper] -> Recharts draws a range area
};

const shortDate = (d: string) => formatDate(d, { day: "numeric", month: "short" });

function Legend({ showActual = true }: { showActual?: boolean }) {
  const item = (color: string, label: string, kind: "line" | "band") => (
    <span className="flex items-center gap-2">
      {kind === "line" ? (
        <span className="h-0.5 w-5 rounded" style={{ background: color }} />
      ) : (
        <span className="h-3 w-5 rounded-sm opacity-25" style={{ background: color }} />
      )}
      {label}
    </span>
  );
  return (
    <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
      {showActual && item("var(--chart-actual)", "Actual AQI", "line")}
      {item("var(--chart-pred)", "Predicted AQI (LightGBM)", "line")}
      {item("var(--chart-band)", "80% interval", "band")}
    </div>
  );
}

// Custom tooltip so the band shows as "low–high" and values are rounded.
function ChartTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { payload: Row }[];
  label?: string;
}) {
  if (!active || !payload?.length || !label) return null;
  const r = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold">{formatDate(label)}</p>
      {r.actual != null && <p>Actual: <b className="tabular-nums">{Math.round(r.actual)}</b></p>}
      {r.predicted != null && <p>Predicted: <b className="tabular-nums">{Math.round(r.predicted)}</b></p>}
      {r.band && <p className="text-muted">Interval: {Math.round(r.band[0])}–{Math.round(r.band[1])}</p>}
    </div>
  );
}

function BaseChart({ data, height }: { data: Row[]; height: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={24}
          tick={{ fill: "var(--chart-axis)", fontSize: 12 }} stroke="var(--chart-grid)" />
        <YAxis tick={{ fill: "var(--chart-axis)", fontSize: 12 }} stroke="var(--chart-grid)"
          domain={[0, "auto"]} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--chart-axis)", strokeDasharray: "3 3" }} />
        <Area dataKey="band" stroke="none" fill="var(--chart-band)" fillOpacity={0.18}
          isAnimationActive={false} connectNulls />
        <Line dataKey="actual" stroke="var(--chart-actual)" strokeWidth={2} dot={false}
          isAnimationActive={false} connectNulls={false} />
        <Line dataKey="predicted" stroke="var(--chart-pred)" strokeWidth={2} dot={false}
          isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/** Last two weeks of measured AQI, then the 7-day forecast with its band. */
export function ForecastChart({ forecast, recent }: { forecast: Forecast; recent: HistoryPoint[] }) {
  const last = forecast.last_observed;
  const rows: Row[] = [
    ...recent.slice(-14, -1).map((p) => ({ date: p.date, actual: p.actual })),
    // The last measured day is where the forecast starts, so the lines join up.
    { date: last.date, actual: last.aqi, predicted: last.aqi, band: [last.aqi, last.aqi] as [number, number] },
    ...forecast.forecast.map((p) => ({ date: p.date, predicted: p.predicted_aqi, band: [p.lower, p.upper] as [number, number] })),
  ];
  return (
    <div>
      <Legend />
      <BaseChart data={rows} height={300} />
      <p className="mt-2 text-xs text-muted">
        The band widens further out: forecasting 7 days ahead is harder than forecasting tomorrow.
      </p>
    </div>
  );
}

/** Out-of-sample 1-day-ahead predictions vs what was actually measured. */
export function HistoryChart({ points }: { points: HistoryPoint[] }) {
  const rows: Row[] = points.map((p) => ({
    date: p.date, actual: p.actual, predicted: p.predicted, band: [p.lower, p.upper],
  }));
  // MAE over the visible window, computed on days that have a measurement.
  const errs = points.filter((p) => p.actual != null).map((p) => Math.abs(p.predicted - (p.actual as number)));
  const mae = errs.reduce((a, b) => a + b, 0) / Math.max(errs.length, 1);
  return (
    <div>
      <Legend />
      <BaseChart data={rows} height={300} />
      <p className="mt-2 text-xs text-muted">
        Each prediction was made by a model that had not seen that day (walk-forward validation).
        Average error over these {points.length} days: <b className="tabular-nums text-text">{mae.toFixed(1)} AQI points</b>.
      </p>
    </div>
  );
}
