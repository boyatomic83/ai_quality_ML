# AQI Forecast — frontend

Next.js (App Router) + TypeScript + Tailwind CSS + Recharts dashboard for the FastAPI backend.

```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL
npm run dev                  # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` is the backend URL. Setting it to `/backend` routes calls
through the Next.js dev proxy in `next.config.ts` (handy in Codespaces).
