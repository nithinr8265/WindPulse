# WindPulse Wind Analytics - Frontend

React dashboard for the WindPulse wind forecast evaluation platform. It helps a UK energy utility's purchasing team understand
how accurate **day-ahead wind generation forecasts** (Elexon BMRS `WINDFOR`) were compared with **actual wind
generation** (Elexon BMRS `FUELHH`, `fuelType == WIND`), and where missing data may affect decisions.

It talks to the existing FastAPI backend (`windpulse-backend`). The backend is **not** part of this
repository and is never modified by it.

## Features

- Header with app name, reporting period, **live API status** (from `GET /health`, re-checked every 30 s and on refresh), refresh button and last-refresh time.
- KPI cards: mean actual, mean forecast, MAE, RMSE, bias, nMAE, hourly coverage - all from the backend.
- Interactive Recharts time series of actual vs day-ahead forecast (MW, UTC) with tooltip (including forecast error and publish time) and legend.
- Forecast-accuracy section with plain-language metric definitions, correct bias interpretation and a MAPE caveat.
- Data coverage and quality panel that keeps these quantities separate: expected hourly periods, expected half-hourly periods, actual records retrieved, raw forecast revisions, eligible forecasts, matched hourly periods, missing hourly forecasts, missing hourly actuals, unmatched half-hourly actuals, coverage %.
- Date-range filter (initial range **1 Jan - 31 Jan 2026**) with validation.
- Loading, empty and error states with retry; responsive layout (permanent sidebar on desktop, drawer on mobile); skip link, labelled controls, keyboard-friendly.

## Backend endpoints used

| Endpoint | Query parameters sent | Used by |
| --- | --- | --- |
| `GET /health` | - | header connection status |
| `GET /api/v1/wind/evaluation` | `from_date`, `to_date`, `include_timeseries=true` (`cutoff_hour` supported by the client, not exposed in the UI) | KPIs, chart, accuracy, coverage |
| `GET /api/v1/wind/actuals` | `from_date`, `to_date`, `limit` | typed service function (tested; not used by the dashboard) |
| `GET /api/v1/wind/forecasts` | `from_date`, `to_date`, `limit` | typed service function (tested; not used by the dashboard) |

A single evaluation request feeds every dashboard section, so the backend only fetches from Elexon once per range.
The raw `actuals` and `forecasts` endpoints return large payloads and nothing on the dashboard needs them.

## Prerequisites

- Node.js 22.13+ (or 24+) and npm 10+ - required by the Vitest and ESLint versions used (developed with Node 22)
- The backend running locally (see below)

## Setup

```powershell
cd C:\windpulse\frontend
npm ci
copy .env.example .env
```

`.env` (never committed; contains no secrets):

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If `VITE_API_BASE_URL` is unset the app falls back to `http://127.0.0.1:8000`. Restart the dev server after editing `.env`.

## Run backend and frontend (two terminals)

**Terminal 1 - backend** (from the backend README):

```powershell
cd C:\windpulse\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - frontend:**

```powershell
cd C:\windpulse\frontend
npm run dev
```

Open <http://127.0.0.1:5173>. The backend's default CORS list already allows `localhost`/`127.0.0.1` on ports 3000 and 5173.
If you serve the frontend from another origin, add it to `ALLOWED_ORIGINS` in the backend `.env`.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server on port 5173 |
| `npm run build` | Type-check and production build into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript project check |
| `npm test` | Unit/component tests (hermetic: all HTTP is mocked) |

### Live integration tests (optional)

With the backend running:

```powershell
$env:VITE_RUN_LIVE_API_TESTS="1"; npm test
```

These call the real backend and check the response contract, consistency rules (e.g. coverage = matched / expected), error handling and that the dashboard renders backend values. Without the variable they are skipped.

## How the data is interpreted

- **UTC everywhere.** Date inputs are UTC calendar days, sent unchanged as `YYYY-MM-DD`; no local-time conversion is applied. All timestamps are displayed in UTC.
- **Day-ahead rule (done by the backend):** for a delivery hour on day D, the latest forecast published at or before 12:00 UTC on D-1 is used.
- **Bias = mean(forecast - actual).** Positive = over-forecasting, negative = under-forecasting.
- **Resolution mismatch:** forecasts are hourly, actuals half-hourly. Evaluation is at hourly resolution; the `:30` actuals have no forecast, are reported as *unmatched half-hourly actuals* and are never hidden - even at 100% hourly coverage.
- **Raw forecast revisions are not samples.** The sample count is the number of matched hourly periods.
- **Coverage** = matched hourly periods / expected hourly periods (24 per day).
- **MAPE** only covers periods with actual > 0 and can be misleading when generation is very low; the UI says so.
- When there are zero matched periods the backend returns `0` for every metric; the UI shows "-" instead of presenting those zeros as results.
- **No fabricated data:** values are never interpolated, defaulted or treated as zero. Where hourly periods are missing from the chart data, the lines break (a value-less marker is inserted purely to interrupt the line).

## Project structure

```
src/
  api/          axios client (base URL, timeout, error normalisation) and service functions
  components/   layout, header, KPI cards, chart, accuracy, coverage, date filter, states
  hooks/        useEvaluation (abortable, stale-response safe), useHealth
  pages/        DashboardPage
  types/        TypeScript types mirroring the backend Pydantic schemas
  utils/        formatters, chart data builder, date-range validation
tests/          Vitest + React Testing Library
```

## Known limitations

- The backend queries Elexon on every request and has no caching, so wide ranges can be slow (requests time out after 90 s; ranges over 62 days show a notice).
- The backend docs describe January 2026, but its code accepts any valid range; the UI does not restrict ranges beyond `start <= end`. Months with no published data simply show empty/zero-coverage states.
- The day-ahead cutoff hour is supported by the API client but not exposed in the UI.
- The main JS bundle is ~590 kB (MUI); the chart (Recharts) is split into a lazily loaded chunk.
- Visual/responsive behaviour was developed from MUI breakpoints and covered by component tests; it was not checked in a real browser during development.
