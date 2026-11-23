const STEPS = [
  {
    title: "1. Data",
    body: "Daily AQI for 2015–2020 from India's Central Pollution Control Board (Kaggle). We keep the 9 cities with the most complete records and fill gaps of up to 7 days by interpolation.",
  },
  {
    title: "2. Features",
    body: "Recent AQI (1, 2, 3, 7, 14 and 30 days ago), rolling averages, and the calendar: weekday, month, winter, and Diwali. Only information available on the forecast day is used.",
  },
  {
    title: "3. Models",
    body: "Four models compete: two simple baselines, SARIMA (a classic time-series model) and LightGBM (gradient-boosted trees, one model shared by all cities).",
  },
  {
    title: "4. Validation",
    body: "Walk-forward testing: train on the past, predict the next 3 months, then move forward and repeat. The model never sees the future, just like in real life.",
  },
  {
    title: "5. Uncertainty",
    body: "Two extra LightGBM models predict the 10th and 90th percentiles, giving the shaded band: the likely range for each day.",
  },
  {
    title: "6. Serving",
    body: "A FastAPI backend (Docker, Hugging Face Spaces) serves forecasts as JSON. This Next.js dashboard on Vercel draws the charts.",
  },
];

export function HowItWorks() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {STEPS.map((s) => (
        <div key={s.title} className="rounded-xl border border-border bg-surface-2 p-4">
          <h3 className="font-semibold">{s.title}</h3>
          <p className="mt-1 text-sm text-muted">{s.body}</p>
        </div>
      ))}
    </div>
  );
}
