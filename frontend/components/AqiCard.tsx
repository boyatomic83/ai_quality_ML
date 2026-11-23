import type { Forecast } from "@/lib/api";
import { CATEGORIES, categoryInfo, formatDate } from "@/lib/aqi";

// One coloured tile: big AQI number + category badge.
function AqiTile({ label, date, aqi, category, range }: {
  label: string;
  date: string;
  aqi: number;
  category: string;
  range?: [number, number];
}) {
  const info = categoryInfo(category);
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface-2">
      {/* Coloured strip = category colour; the label below says it in words too. */}
      <div className="h-2" style={{ background: info.color }} />
      <div className="p-4 sm:p-5">
        <p className="text-sm font-medium text-muted">{label}</p>
        <p className="text-xs text-muted">{formatDate(date)}</p>
        <div className="mt-3 flex flex-wrap items-end gap-x-3 gap-y-2">
          <span className="text-5xl font-bold tabular-nums leading-none">{Math.round(aqi)}</span>
          <span className="rounded-full px-3 py-1 text-sm font-semibold" style={{ background: info.color, color: info.text }}>
            {info.name}
          </span>
        </div>
        {range && (
          <p className="mt-2 text-xs text-muted">
            Likely range {Math.round(range[0])}–{Math.round(range[1])} (80% interval)
          </p>
        )}
      </div>
    </div>
  );
}

export function AqiCard({ data }: { data: Forecast }) {
  const today = data.last_observed;
  const tomorrow = data.forecast[0];
  const tip = categoryInfo(tomorrow.category);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <AqiTile label="Today · last measured" date={today.date} aqi={today.aqi} category={today.category} />
        <AqiTile
          label="Tomorrow · forecast"
          date={tomorrow.date}
          aqi={tomorrow.predicted_aqi}
          category={tomorrow.category}
          range={[tomorrow.lower, tomorrow.upper]}
        />
      </div>

      <div className="rounded-xl border border-border p-4 text-sm" style={{ borderLeft: `4px solid ${tip.color}` }}>
        <p className="font-semibold">Health tip for tomorrow ({tip.name})</p>
        <p className="mt-1 text-muted">{tip.impact}</p>
        <p className="mt-1">{tip.tip}</p>
      </div>

      {/* CPCB scale for reference */}
      <div className="grid grid-cols-3 gap-1 text-[11px] sm:grid-cols-6">
        {CATEGORIES.map((c) => (
          <div key={c.name} className="rounded-md px-2 py-1 text-center font-medium" style={{ background: c.color, color: c.text }}>
            {c.name} <span className="opacity-80">{c.range}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
