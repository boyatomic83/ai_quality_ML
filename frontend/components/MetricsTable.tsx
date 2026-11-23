"use client";

import { useState } from "react";
import type { Metrics } from "@/lib/api";

const DESCRIPTIONS: Record<string, string> = {
  Naive: "Tomorrow = today",
  "Seasonal Naive": "Same weekday last week",
  SARIMA: "Classical statistical model, one per city",
  LightGBM: "Gradient-boosted trees, one model for all cities",
};

export function MetricsTable({ metrics, city }: { metrics: Metrics; city: string }) {
  const [view, setView] = useState<"overall" | "city">("overall");
  const rows = view === "overall" ? metrics.overall : metrics.per_city[city] ?? metrics.overall;
  // Highlight the lowest MAE in the current view (can differ per city).
  const best = rows.reduce((a, b) => (b.MAE < a.MAE ? b : a)).model;

  const tab = (key: "overall" | "city", label: string) => (
    <button
      onClick={() => setView(key)}
      aria-pressed={view === key}
      className={`rounded-lg px-3 py-1.5 text-sm font-medium ${view === key ? "bg-accent text-white" : "text-muted hover:bg-surface-2"}`}
    >
      {label}
    </button>
  );

  return (
    <div>
      <div className="mb-4 inline-flex gap-1 rounded-xl border border-border p-1">
        {tab("overall", "All cities")}
        {tab("city", city)}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <th className="py-2 pr-4 font-medium">Model</th>
              <th className="py-2 pr-4 text-right font-medium">MAE</th>
              <th className="py-2 pr-4 text-right font-medium">RMSE</th>
              <th className="py-2 text-right font-medium">MAPE %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isBest = r.model === best;
              return (
                <tr key={r.model} className={`border-b border-border last:border-0 ${isBest ? "bg-accent/10" : ""}`}>
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2 font-medium">
                      {r.model}
                      {isBest && <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-semibold text-white">Best</span>}
                    </div>
                    <div className="text-xs text-muted">{DESCRIPTIONS[r.model]}</div>
                  </td>
                  <td className={`py-3 pr-4 text-right tabular-nums ${isBest ? "font-semibold" : ""}`}>{r.MAE.toFixed(2)}</td>
                  <td className="py-3 pr-4 text-right tabular-nums">{r.RMSE.toFixed(2)}</td>
                  <td className="py-3 text-right tabular-nums">{r.MAPE.toFixed(1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-muted">
        Lower is better. Errors are averaged over all forecast horizons (1–7 days) using {metrics.validation}.
        Best model chosen by {metrics.selection_metric}. The LightGBM 80% interval contained the real value{" "}
        {Math.round(metrics.interval_coverage * 100)}% of the time.
      </p>
    </div>
  );
}
