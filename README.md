# WindPulse - UK Wind Generation Forecast Evaluation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8%20%2F%206.0-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6%20%2F%208-646CFF.svg)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey.svg)]()

**WindPulse** is an end-to-end analytics platform designed for UK electricity utility trading desks and energy analysts. It evaluates the performance of day-ahead wind generation forecasts against actual metered wind output across the National Grid, enforcing strict temporal cutoff rules to prevent lookahead bias and data leakage.

The platform consumes real-time and historical datasets from the **Elexon BMRS API** (`WINDFOR` and `FUELHH`), reconciles hourly forecast revisions against half-hourly actual settlement periods, calculates standardized quantitative accuracy metrics (MAE, RMSE, Bias, nMAE, MAPE), and displays actionable insights through a responsive React dashboard.

---

## Deployment Status

- **Frontend**: Not deployed yet
- **Backend API**: Not deployed yet

*Note: Containerization files (`Dockerfile` in `backend/`) and production build targets (`npm run build` in `frontend/`) are configured and verified for deployment to cloud container or static hosting platforms.*

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Local Installation & Startup](#local-installation--startup)
  - [Terminal 1: Backend Setup (FastAPI)](#terminal-1-backend-setup-fastapi)
  - [Terminal 2: Frontend Setup (React + Vite)](#terminal-2-frontend-setup-react--vite)
- [Backend API Endpoints](#backend-api-endpoints)
- [Testing & Quality Verification](#testing--quality-verification)
  - [Backend Tests (pytest)](#backend-tests-pytest)
  - [Frontend Tests & Linting (vitest & eslint)](#frontend-tests--linting-vitest--eslint)
- [Environment Configuration & Security](#environment-configuration--security)
- [Troubleshooting](#troubleshooting)

---

## Overview & Architecture

Utility power trading teams make binding commitments in day-ahead electricity auctions (such as EPEX SPOT GB or Nord Pool). Because day-ahead auctions clear before delivery, market participants need accurate forecasts while avoiding retrospective bias.

```
                              ELEXON BMRS API
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
  FUELHH Stream                                        WINDFOR Stream
  (Actuals: fuelType=WIND,                             (Forecasts: hourly startTimes,
   half-hourly periods :00 & :30)                       multiple publication revisions)
           │                                                   │
           │                                                   ▼
           │                                      Day-Ahead Decision Filter
           │                                      (publishTime <= D-1 at 12:00 UTC)
           │                                                   │
           │                                                   ▼
           │                                      Select Latest Pre-Cutoff Forecast
           │                                      max(publishTime) per target startTime
           │                                                   │
           └─────────────────────────┬─────────────────────────┘
                                     ▼
                      Target startTime Matcher & Audit
                      (Matches :00 hourly periods; tracks
                       :30 actuals as unmatched half-hourly)
                                     │
                                     ▼
                         Accuracy Metrics Service
                         (MAE, RMSE, Bias, nMAE, MAPE)
                                     │
                                     ▼
                          FastAPI REST Service
             GET /health │ /actuals │ /forecasts │ /evaluation
                                     │
                                     ▼  (HTTP / JSON)
                     React 19 + TypeScript Dashboard
             (KPI Cards, Recharts Time-Series, Coverage Audit)
```

### Core Evaluation Principles

1. **Temporal Gate Closure (Zero Data Leakage)**: For any target delivery timestamp on date $D$, only forecasts published on or before Day $D-1$ at the cutoff hour (default `12:00 UTC`, noon) are eligible. Forecasts published after gate closure are strictly excluded.
2. **Latest Pre-Cutoff Forecast**: Among all eligible forecasts published prior to gate closure, the one with the maximum `publishTime` is selected, representing the most up-to-date information available to a trader at auction time.
3. **Transparent Resolution Handling & No Data Fabrication**:
   - `FUELHH` actuals are reported half-hourly (48 periods per standard day: `:00` and `:30`).
   - `WINDFOR` forecasts are published at hourly resolution (`:00`).
   - In accordance with utility audit requirements, data is never artificially interpolated or fabricated. Top-of-the-hour periods (`:00`) match cleanly. Half-hour periods (`:30`) are faithfully documented as `unmatchedHalfHourlyActualsCount`.
4. **Strict UTC Calendar Windowing**: All date boundaries and calculations operate strictly in UTC (`[start_utc, end_utc)`), avoiding missing periods or distortion during British Summer Time (BST) transitions.

---

## Key Features

- **Day-Ahead Auction Cutoff Rule**: Strict filtering at $D-1$ 12:00 UTC prevents lookahead bias.
- **Comprehensive Error Metrics**:
  - **MAE (Mean Absolute Error)**: Average absolute miss magnitude in Megawatts (MW).
  - **RMSE (Root Mean Squared Error)**: Quadratic penalty highlighting large forecast deviations.
  - **Bias (Mean Error)**: Directional skew ($>0$ indicates systematic over-forecasting, $<0$ under-forecasting).
  - **nMAE (%)**: Normalized MAE relative to average actual wind generation.
  - **MAPE (%)**: Mean Absolute Percentage Error computed over non-zero generation periods.
- **Interactive Recharts Visualization**: Side-by-side time-series rendering of actual vs. forecast output, interactive tooltips with error calculations and publish timestamps, and visual breaks over missing data periods.
- **Data Completeness & Coverage Audit**: Independent tracking of expected hourly periods, eligible forecasts, matched periods, missing hourly actuals/forecasts, and unmatched half-hourly records.
- **Live Health Monitoring**: Heartbeat monitor in the dashboard header polling `GET /health` every 30 seconds with instant retry and status indicator.
- **Configurable UTC Date Range Filter**: Full support for single days, multi-week windows, or monthly audits (defaulting to January 2026).

---

## Technology Stack

### Backend
- **Language**: Python >= 3.11
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (>= 0.110.0) with [Uvicorn](https://www.uvicorn.org/) (>= 0.28.0)
- **Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/latest/) (>= 2.6.0) and `pydantic-settings` (>= 2.2.0)
- **HTTP Client**: [HTTPX](https://www.python-httpx.org/) (>= 0.27.0) for asynchronous upstream requests
- **Testing**: [Pytest](https://docs.pytest.org/) (>= 8.0.0), `pytest-asyncio` (>= 0.23.0)

### Frontend
- **Runtime & Package Manager**: Node.js `^22.13.0 || >=24`, npm `10+`
- **UI Library**: [React 19](https://react.dev/) (19.3.1)
- **Language**: [TypeScript](https://www.typescriptlang.org/) (5.8 / 6.0)
- **Build Tool**: [Vite](https://vitejs.dev/) (Vite 6 / 8)
- **Component System**: [Material UI (MUI)](https://mui.com/) (v6 / v9) with Emotion styling
- **Charts**: [Recharts](https://recharts.org/) (3.10.1) with responsive containers
- **HTTP Client**: [Axios](https://axios-http.com/) (>= 1.20.0)
- **Testing**: [Vitest](https://vitest.dev/) (5.0.5) and [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)

### External Upstream Data Source
- **Elexon BMRS API** (`https://data.elexon.co.uk/bmrs/api/v1`):
  - `datasets/FUELHH`: Outturn half-hourly generation by fuel type (`fuelType=WIND`).
  - `datasets/WINDFOR`: Wind generation forecast updates for national delivery.

---

## Repository Structure

```text
C:\windpulse\
├── backend\                             # Python FastAPI Backend
│   ├── app\
│   │   ├── api\
│   │   │   ├── __init__.py
│   │   │   └── routes.py                # Endpoints: /health, /actuals, /forecasts, /evaluation
│   │   ├── clients\
│   │   │   ├── __init__.py
│   │   │   └── elexon_client.py         # Async HTTP client for Elexon BMRS FUELHH & WINDFOR
│   │   ├── models\
│   │   │   ├── __init__.py
│   │   │   └── schemas.py               # Pydantic schemas for requests, responses & records
│   │   ├── services\
│   │   │   ├── __init__.py
│   │   │   ├── forecast_service.py      # Cutoff rules, forecast deduplication & timeseries matching
│   │   │   └── metrics_service.py       # Calculation of MAE, RMSE, Bias, nMAE, and MAPE
│   │   ├── __init__.py
│   │   ├── config.py                    # Environment settings loaded via Pydantic BaseSettings
│   │   └── main.py                      # FastAPI app instance, CORS middleware & exception handlers
│   ├── tests\
│   │   ├── __init__.py
│   │   ├── conftest.py                  # Pytest fixtures and mock client records
│   │   ├── test_forecast_selection.py   # Gate closure & data leakage prevention tests
│   │   ├── test_live_elexon_reconciliation.py # Live upstream API reconciliation (opt-in)
│   │   ├── test_metrics.py              # Quantitative metric mathematical verification tests
│   │   ├── test_routes.py               # Integration tests for API routes with mock clients
│   │   └── test_utc_boundaries_and_reconciliation.py # UTC/BST calendar boundary tests
│   ├── .env.example                     # Backend environment configuration template
│   ├── .gitignore                       # Backend git ignore rules
│   ├── Dockerfile                       # Production container build specification
│   ├── pyproject.toml                   # Project metadata and build configuration
│   ├── requirements.txt                 # Pinned dependencies
│   └── README.md                        # Backend service documentation
├── frontend\                            # React + TypeScript + Vite Frontend
│   ├── public\
│   │   └── favicon.svg                  # Application branding icon
│   ├── src\
│   │   ├── api\
│   │   │   ├── client.ts                # Axios instance configuration, base URL & timeouts
│   │   │   └── windService.ts           # Typed API client methods for backend communication
│   │   ├── components\
│   │   │   ├── AccuracyMetrics.tsx      # Accuracy KPI grid and metric formula definitions
│   │   │   ├── ActualForecastChart.tsx  # Interactive Recharts wind timeseries visualization
│   │   │   ├── AppLayout.tsx            # Responsive layout wrapper with sidebar & app bar
│   │   │   ├── DataCoverage.tsx         # Data completeness and reconciliation table
│   │   │   ├── DateRangeFilter.tsx      # UTC date selection controls with ISO validation
│   │   │   ├── ErrorBoundary.tsx        # React lifecycle error boundary component
│   │   │   ├── ErrorState.tsx           # Error display with manual retry action
│   │   │   ├── Header.tsx               # App title, live connection status & refresh trigger
│   │   │   ├── KpiCard.tsx              # Individual KPI summary card component
│   │   │   ├── LoadingState.tsx         # Skeleton placeholders during data fetching
│   │   │   └── SectionCard.tsx          # Reusable styled card container
│   │   ├── hooks\
│   │   │   ├── useEvaluation.ts         # Query hook managing evaluation state & abort controller
│   │   │   └── useHealth.ts             # Health check polling hook (30s heartbeat)
│   │   ├── pages\
│   │   │   └── DashboardPage.tsx        # Primary dashboard layout combining all UI sections
│   │   ├── types\
│   │   │   └── wind.ts                  # TypeScript types mirroring backend Pydantic models
│   │   ├── utils\
│   │   │   ├── chartData.ts             # Gap-preserving chart data transformer
│   │   │   ├── dateRange.ts             # Date validation and ISO string utilities
│   │   │   └── formatters.ts            # Formatting for MW, percentages, and timestamps
│   │   ├── App.tsx                      # Top-level React component tree
│   │   ├── main.tsx                     # DOM mounting entry point
│   │   ├── theme.ts                     # Material UI theme customizations
│   │   └── vite-env.d.ts                # Vite environment typings
│   ├── tests\
│   │   ├── api.test.ts                  # Frontend API client and error handling tests
│   │   ├── chartData.test.ts            # Chart transformation and missing-data break tests
│   │   ├── coverage.test.tsx            # Data coverage panel unit tests
│   │   ├── dateFilter.test.tsx          # Date range filter component tests
│   │   ├── dateRange.test.ts            # UTC date arithmetic and boundary tests
│   │   ├── fixtures.ts                  # Mock data payloads for frontend unit tests
│   │   ├── formatters.test.ts           # Value formatting tests
│   │   ├── integration.live.test.tsx    # Live end-to-end integration tests (opt-in)
│   │   ├── kpis.test.tsx                # KPI card rendering and styling tests
│   │   ├── layout.test.tsx              # App layout structure and navigation tests
│   │   ├── reliability.test.tsx         # Error boundary, network failure & retry tests
│   │   └── setup.ts                     # Vitest test setup and jest-dom matchers
│   ├── .env.example                     # Frontend environment configuration template
│   ├── .gitignore                       # Frontend git ignore rules
│   ├── eslint.config.js                 # ESLint rules and configuration
│   ├── index.html                       # HTML document template
│   ├── package.json                     # Frontend scripts and npm package dependencies
│   ├── tsconfig.json                    # Base TypeScript compiler settings
│   ├── tsconfig.app.json                # Application TypeScript configuration
│   ├── tsconfig.node.json               # Vite node tooling TypeScript configuration
│   ├── vite.config.ts                   # Vite build configuration
│   └── README.md                        # Frontend documentation
├── .gitignore                           # Repository-level git ignore rules
└── README.md                            # Root project documentation (this file)
```

---

## Prerequisites

Before running the application locally, ensure your environment meets the following requirements:

1. **Python**:
   - Python **3.11+** (tested and verified with Python 3.11).
   - Verify in PowerShell:
     ```powershell
     py -3.11 --version
     # or
     python --version
     ```
2. **Node.js & npm**:
   - Node.js **^22.13.0** or **>=24** (tested and verified with Node.js v22).
   - npm **10+**.
   - Verify in PowerShell:
     ```powershell
     node --version
     npm --version
     ```
3. **Network**:
   - Outbound HTTPS access to `https://data.elexon.co.uk` (no API key required for public BMRS access).

---

## Local Installation & Startup

To run the complete WindPulse platform locally on Windows, open **two separate PowerShell terminals**.

### Terminal 1: Backend Setup (FastAPI)

1. Open PowerShell and navigate to the backend directory:
   ```powershell
   cd C:\windpulse\backend
   ```

2. Create and activate a Python 3.11 virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(If script execution is disabled on your system, enable it for the current process: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*

3. Upgrade `pip` and install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create the backend `.env` configuration file:
   ```powershell
   Copy-Item .env.example .env
   ```

5. Launch the FastAPI development server:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

The backend server is now running:
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### Terminal 2: Frontend Setup (React + Vite)

1. Open a second PowerShell terminal and navigate to the frontend directory:
   ```powershell
   cd C:\windpulse\frontend
   ```

2. Install dependencies cleanly using `npm ci`:
   ```powershell
   npm ci
   ```

3. Create the frontend `.env` configuration file:
   ```powershell
   Copy-Item .env.example .env
   ```
   *Ensure `VITE_API_BASE_URL=http://127.0.0.1:8000` is present in `.env`.*

4. Start the Vite development server:
   ```powershell
   npm run dev
   ```

The frontend dashboard is now running:
- **Dashboard URL**: [http://localhost:5173](http://localhost:5173) (or `http://127.0.0.1:5173`)
- The header will display an **"API connected"** status badge indicating active communication with the backend.

---

## Backend API Endpoints

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | None | Returns operational status, environment name, and server UTC timestamp. |
| `GET` | `/api/v1/wind/actuals` | `from_date`, `to_date`, `limit` | Retrieves actual half-hourly wind generation records from Elexon BMRS `FUELHH`. |
| `GET` | `/api/v1/wind/forecasts` | `from_date`, `to_date`, `limit` | Retrieves raw hourly wind forecast revisions from Elexon BMRS `WINDFOR`. |
| `GET` | `/api/v1/wind/evaluation` | `from_date`, `to_date`, `cutoff_hour`, `include_timeseries` | Executes the day-ahead evaluation pipeline, returning accuracy metrics, coverage statistics, and matched timeseries. |

### Example Query

Retrieve evaluation metrics for January 2026 without downloading the full timeseries payload:

```powershell
curl.exe -X GET "http://127.0.0.1:8000/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-31&include_timeseries=false"
```

**Example JSON Response**:
```json
{
  "status": "success",
  "summary": {
    "targetPeriodStart": "2026-01-01T00:00:00Z",
    "targetPeriodEnd": "2026-01-31T23:30:00Z",
    "decisionCutoffRule": "Day-Ahead (D-1 at 12:00 UTC)",
    "totalExpectedHourlyPeriods": 744,
    "totalActualHalfHourlyPeriods": 1488,
    "rawForecastRevisionsCount": 18080,
    "eligibleForecastsCount": 744,
    "matchedCount": 744,
    "missingHourlyForecastCount": 0,
    "missingHourlyActualCount": 0,
    "unmatchedHalfHourlyActualsCount": 744,
    "coveragePercentage": 100.0,
    "totalExpectedPeriods": 744,
    "actualRecordsCount": 1488,
    "forecastRecordsCount": 18080,
    "missingForecastCount": 0,
    "missingActualCount": 0
  },
  "metrics": {
    "sampleCount": 744,
    "maeMW": 1845.23,
    "rmseMW": 2312.65,
    "biasMW": 412.18,
    "nmaePercentage": 14.82,
    "mapePercentage": 16.54,
    "meanActualMW": 12450.35,
    "meanForecastMW": 12862.53,
    "unit": "MW",
    "definitions": {
      "errorMW": "Forecast - Actual generation in Megawatts (MW)",
      "maeMW": "Mean Absolute Error: (1/N) * sum(|Forecast - Actual|)",
      "rmseMW": "Root Mean Squared Error: sqrt((1/N) * sum((Forecast - Actual)^2))",
      "biasMW": "Forecast Bias (Mean Error): (1/N) * sum(Forecast - Actual). >0 = over-forecast, <0 = under-forecast",
      "nmaePercentage": "Normalized MAE: (MAE / Mean(Actual)) * 100%",
      "mapePercentage": "MAPE: Mean(|Forecast - Actual| / Actual) * 100% for actual > 0"
    }
  },
  "matchedData": []
}
```

---

## Testing & Quality Verification

Both the backend and frontend are accompanied by automated test suites.

### Backend Tests (pytest)

1. Activate the virtual environment:
   ```powershell
   cd C:\windpulse\backend
   .\.venv\Scripts\Activate.ps1
   ```

2. Run the hermetic test suite (34 passing unit/integration tests, 2 live tests skipped by default):
   ```powershell
   python -m pytest -v
   ```

3. *(Optional)* Run live upstream Elexon reconciliation tests:
   ```powershell
   $env:RUN_LIVE_ELEXON_TESTS="1"
   python -m pytest -v tests/test_live_elexon_reconciliation.py
   Remove-Item Env:RUN_LIVE_ELEXON_TESTS
   ```

### Frontend Tests & Linting (vitest & eslint)

Navigate to the frontend directory:
```powershell
cd C:\windpulse\frontend
```

1. **TypeScript Type Check**:
   ```powershell
   npm run typecheck
   ```
2. **ESLint Code Quality**:
   ```powershell
   npm run lint
   ```
3. **Hermetic Unit & Component Tests** (38 passing tests with mocked HTTP responses):
   ```powershell
   npm test
   ```
4. **Production Build Verification**:
   ```powershell
   npm run build
   ```
5. *(Optional)* **Live Integration Tests** (requires the backend to be running on port 8000):
   ```powershell
   $env:VITE_RUN_LIVE_API_TESTS="1"
   npm test tests/integration.live.test.tsx
   Remove-Item Env:VITE_RUN_LIVE_API_TESTS
   ```

---

## Environment Configuration & Security

### Backend Settings (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `"WindPulse Wind Forecast Evaluation API"` | Name displayed in health checks and OpenAPI docs. |
| `APP_ENV` | `"development"` | Operational environment (`development`, `test`, `production`). |
| `HOST` | `"0.0.0.0"` | Bind host for the server process. |
| `PORT` | `8000` | Bind port for Uvicorn. |
| `LOG_LEVEL` | `"INFO"` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ALLOWED_ORIGINS` | `"http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"` | Comma-separated CORS allowed origins. |
| `ELEXON_BASE_URL` | `"https://data.elexon.co.uk/bmrs/api/v1"` | Upstream Elexon BMRS endpoint. |
| `HTTP_TIMEOUT_SECONDS` | `30.0` | Timeout threshold for upstream queries. |
| `DAY_AHEAD_DECISION_CUTOFF_HOUR` | `12` | Cutoff hour on day $D-1$ (0–23 UTC; default 12:00 noon UTC). |

### Frontend Settings (`frontend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the backend API (no trailing slash). |

> [!WARNING]
> **Security Notice**:
> Never commit `.env` files to source control. Both repository-level and application-level `.gitignore` files explicitly ignore `.env`, `.env.*` (while allowing `.env.example`), `.venv/`, `node_modules/`, and build artifacts (`dist/`, `.pytest_cache/`).
> Template files (`.env.example`) contain only safe local development defaults and no sensitive secrets.

---

## Troubleshooting

### 1. Frontend Displays "API unreachable" / Cannot reach API
- **Symptom**: Dashboard displays an error notification banner stating the API cannot be reached at `http://127.0.0.1:8000`.
- **Resolution**:
  1. Confirm the backend is running in Terminal 1 (`uvicorn app.main:app ...`).
  2. Test health directly in browser or terminal: `curl.exe http://127.0.0.1:8000/health`.
  3. Ensure `frontend/.env` exists and contains `VITE_API_BASE_URL=http://127.0.0.1:8000`.
  4. Restart the Vite dev server (`npm run dev`) after creating or editing `.env`.

### 2. CORS Errors in Browser Console
- **Symptom**: Browser console indicates Cross-Origin Resource Sharing (CORS) request blocked.
- **Resolution**:
  - If accessing the frontend on a custom port or hostname (e.g. `http://localhost:4173`), add it to `ALLOWED_ORIGINS` in `backend/.env` and restart the backend server.

### 3. Port Already in Use (Port 8000 or 5173)
- **Symptom**: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): address already in use`.
- **Resolution**:
  - Check which process is occupying the port in PowerShell:
    ```powershell
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess
    ```
  - Terminate the conflicting process:
    ```powershell
    Stop-Process -Id <PID> -Force
    ```

### 4. PowerShell Execution Policy Restriction
- **Symptom**: `.\.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system`.
- **Resolution**:
  - Run the following command in PowerShell for your current session:
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    ```

### 5. Node.js Version Warning / Failure
- **Symptom**: Build or test errors citing unsupported Node.js engine features.
- **Resolution**:
  - Verify your Node.js version is `^22.13.0` or `>=24`:
    ```powershell
    node --version
    ```
  - If running an earlier version, upgrade to Node.js LTS (v22).

### 6. Upstream Elexon API Timeouts
- **Symptom**: Requests return HTTP 502 with `External data source error` or `ConnectTimeout`.
- **Resolution**:
  - When querying wide date ranges (e.g., >31 days), Elexon can experience high latency. Increase `HTTP_TIMEOUT_SECONDS=60.0` or `90.0` in `backend/.env`.

---

## License

Proprietary — Internal UK Energy Utility Wind Analytics Platform. All rights reserved.
