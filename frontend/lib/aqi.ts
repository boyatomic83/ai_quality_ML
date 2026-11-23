// CPCB AQI categories: official colours plus health guidance.
// The backend decides the category; this file only says how to display it.

export type CategoryInfo = {
  name: string;
  range: string;
  color: string; // CPCB colour, used as the card accent
  text: string; // readable text colour on top of `color`
  impact: string; // CPCB health impact statement
  tip: string; // practical advice
};

export const CATEGORIES: CategoryInfo[] = [
  {
    name: "Good", range: "0–50", color: "#00b050", text: "#ffffff",
    impact: "Minimal impact.",
    tip: "Great day to be outdoors. Open the windows and enjoy the fresh air.",
  },
  {
    name: "Satisfactory", range: "51–100", color: "#92d050", text: "#14290a",
    impact: "Minor breathing discomfort to sensitive people.",
    tip: "Fine for most people. If you're very sensitive, take it easy on long workouts outside.",
  },
  {
    name: "Moderate", range: "101–200", color: "#ffd500", text: "#332a00",
    impact: "Breathing discomfort for people with asthma, lung or heart disease, children and older adults.",
    tip: "Sensitive groups should cut down on prolonged outdoor exertion.",
  },
  {
    name: "Poor", range: "201–300", color: "#ff9900", text: "#331f00",
    impact: "Breathing discomfort to most people on prolonged exposure.",
    tip: "Limit time outdoors, avoid exercising near traffic, and consider an N95 mask.",
  },
  {
    name: "Very Poor", range: "301–400", color: "#ff0000", text: "#ffffff",
    impact: "Respiratory illness on prolonged exposure.",
    tip: "Stay indoors where possible, run an air purifier, and wear an N95 mask outside.",
  },
  {
    name: "Severe", range: "401+", color: "#c00000", text: "#ffffff",
    impact: "Affects healthy people and seriously impacts those with existing diseases.",
    tip: "Avoid all outdoor activity. Keep windows closed. Seek medical help if you have symptoms.",
  },
];

export function categoryInfo(name: string): CategoryInfo {
  return CATEGORIES.find((c) => c.name === name) ?? CATEGORIES[0];
}

// "2020-07-02" -> "Thu, 2 Jul 2020". Parsed as UTC so the date never shifts with the viewer's timezone.
export function formatDate(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "short", day: "numeric", month: "short", year: "numeric" }) {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-IN", { ...opts, timeZone: "UTC" });
}
