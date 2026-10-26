# WindPulse Wind Forecast Evaluation API

A production-grade Python backend built with **FastAPI**, **Pydantic v2**, and **httpx** for a UK energy utility. This service retrieves, matches, and evaluates Elexon BMRS day-ahead wind generation forecasts against actual metered wind generation across the UK national grid during **January 2026**.

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Day-Ahead Decision Rule & Assumptions](#day-ahead-decision-rule--assumptions)
- [Accuracy Metrics & Definitions](#accuracy-metrics--definitions)
- [Environment Variables](#environment-variables)
- [Getting Started (Windows PowerShell)](#getting-started-windows-powershell)
- [Running Tests](#running-tests)
- [API Endpoints & Usage](#api-endpoints--usage)
- [Docker Deployment](#docker-deployment)
- [Frontend Integration Notes](#frontend-integration-notes)

---

## Overview & Architecture

Electricity utility trading desks make binding purchase commitments in day-ahead power auctions. To evaluate whether forecast models are providing actionable signals, utility analysts need:

1. **Strict temporal cutoff rules**: Forecasts published after the day-ahead auction cutoff must be discarded to prevent lookahead bias / data leakage.
2. **Latest available forecast selection**: Among all forecasts published prior to the gate closure, only the most recently updated forecast represents what a trader could actually observe.
3. **Rigorous error metrics**: Standardized metrics (MAE, RMSE, Bias) in Megawatts (MW) to measure both error scale and directional skew (over- vs. under-forecasting).
4. **Data completeness accounting**: Transparent reporting of matched versus missing observations without fabricating data.

```
                           ELEXON BMRS API
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
FUELHH Dataset Stream                             WINDFOR Dataset Stream
(Actuals: fuelType=WIND)                          (Forecasts: hourly startTimes)
         │                                                 │
         │                                                 ▼
         │                                    Day-Ahead Decision Filter
         │                                    (publishTime <= D-1 at 12:00 UTC)
         │                                                 │
         │                                                 ▼
         │                                    Select Latest Pre-Cutoff Forecast
         │                                    max(publishTime) per target startTime
         │                                                 │
         └────────────────────────┬────────────────────────┘
                                  ▼
                   Target startTime Matcher
                   (Deduplication & Missing Tracking)
                                  │
                                  ▼
                     Accuracy Metrics Service
                     (MAE, RMSE, Bias, nMAE, MAPE)
                                  │
                                  ▼
                        FastAPI REST API
           /health │ /actuals │ /forecasts │ /evaluation
```

---

## Key Features

- **FastAPI + Uvicorn**: High-performance asynchronous REST API with automatic OpenAPI Swagger UI.
- **Pydantic v2 Validation**: Strict typing, request validation, and self-documenting response schemas.
- **Zero Data Leakage**: Enforces that for any delivery on date $D$, only forecasts published on or before Day $D-1$ at the cutoff hour (default 12:00 UTC) are considered.
- **Elexon BMRS Client**: Asynchronous `httpx` client with query caching, timeout handling, and graceful HTTP error degradation.
- **Comprehensive Test Suite**: Automated unit and integration tests covering forecast selection, metrics, API routes, UTC boundaries, and daylight saving time transitions.
- **CORS Configured**: Ready for local React frontend development with configurable origins.

---

## Project Structure

```
windpulse-backend/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules for Python, venv, and cache
├── Dockerfile                # Production container specification
├── pyproject.toml            # Project metadata and pytest configuration
├── requirements.txt          # Pinned runtime and testing dependencies
├── README.md                 # Project documentation
├── app/
│   ├── __init__.py           # Application package marker
│   ├── main.py               # FastAPI entry point, CORS, and exception handlers
│   ├── config.py             # Settings using Pydantic BaseSettings
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py         # Route handlers for health, actuals, forecasts, evaluation
│   ├── clients/
│   │   ├── __init__.py
│   │   └── elexon_client.py  # Async HTTP client querying FUELHH and WINDFOR streams
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic schemas for requests, responses, and records
│   └── services/
│       ├── __init__.py
│       ├── forecast_service.py # Cutoff logic, forecast selection, and timeseries matching
│       └── metrics_service.py  # Quantitative calculation of MAE, RMSE, Bias, etc.
└── tests/
    ├── __init__.py
    ├── conftest.py           # Shared test fixtures (mock records, test client)
    ├── test_forecast_selection.py # Tests for cutoff calculation & data leakage prevention
    ├── test_metrics.py       # Hand-calculated tests for MAE, RMSE, Bias, edge cases
    └── test_routes.py        # Integration tests for API endpoints with mocked client
```

---

## Day-Ahead Decision Rule & Assumptions

### 1. Decision Cutoff Time
- **GB Market Context**: In Great Britain's power market (EPEX SPOT and Nord Pool Day-Ahead Auctions), the primary day-ahead auction gate closure is at **12:00 UTC (noon) on day D-1** (the calendar day preceding delivery).
- **Rule Definition**: For any target delivery timestamp `startTime` on calendar date $D$, the purchasing cutoff deadline is:
  $$\text{Cutoff} = (D - 1\text{ day}) \text{ at } 12:00:00\text{ UTC}$$
- **Configurability**: The cutoff hour is configurable via `DAY_AHEAD_DECISION_CUTOFF_HOUR` in `.env` (default: `12`) or via the `cutoff_hour` query parameter on `/api/v1/wind/evaluation` (e.g. `?cutoff_hour=17`).

### 2. Forecast Selection Rule
- For each target delivery half-hour, multiple forecasts may have been published prior to the cutoff (e.g. 2 days prior, 1 day prior at 06:00, 1 day prior at 11:30).
- The service selects the **latest forecast published at or before the cutoff**:
  $$\text{Selected Forecast} = \arg\max_{f \in \{f \mid \text{publishTime} \le \text{Cutoff}\}} (f.\text{publishTime})$$
- Forecasts published after the cutoff (`publishTime > Cutoff`) are **strictly excluded**.

### 3. Timestamp Resolution & Missing Data Handling
- **FUELHH (Actuals)**: Published at half-hourly resolution (48 settlement periods per day: `00:00`, `00:30`, `01:00`, etc.). Total for 31 days in January 2026 = 1,488 records.
- **WINDFOR (Forecasts)**: Published at hourly resolution (`00:00`, `01:00`, `02:00`, etc.).
- **No Data Fabrication**: The prompt explicitly specifies: *“Do not fabricate missing observations or forecasts.”*
  Therefore, the service matches records by exact target `startTime` (`WINDFOR.startTime == FUELHH.startTime`).
  - Top-of-the-hour periods (`:00`) match cleanly (744 matched observations across January 2026).
  - Half-hour periods (`:30`) are faithfully documented in `summary.missingForecastCount` (744 periods) without synthetic interpolation.

---

## Accuracy Metrics & Definitions

All generation values and absolute error metrics are reported in **Megawatts (MW)**.

| Metric | Formula | Definition & Interpretation |
| :--- | :--- | :--- |
| **Error ($e_i$)** | $\hat{y}_i - y_i$ | Difference between forecast ($\hat{y}$) and actual ($y$). Positive indicates over-forecasting; negative indicates under-forecasting. |
| **MAE** | $\frac{1}{N} \sum_{i=1}^N \|\hat{y}_i - y_i\|$ | **Mean Absolute Error (MW)**. Average magnitude of forecast errors, regardless of direction. |
| **RMSE** | $\sqrt{\frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)^2}$ | **Root Mean Squared Error (MW)**. Penalizes large forecast misses more heavily than small ones. |
| **Bias** | $\frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)$ | **Mean Forecast Error (MW)**. Average signed error. If Bias $> 0$, the forecast systematically over-predicts wind output. |
| **nMAE** | $\frac{\text{MAE}}{\bar{y}} \times 100\%$ | **Normalized MAE (%)**. MAE relative to average actual wind generation. |
| **MAPE** | $\frac{1}{N_{nz}} \sum_{y_i > 0} \frac{\|\hat{y}_i - y_i\|}{y_i} \times 100\%$ | **Mean Absolute Percentage Error (%)**. Average percentage error over periods with non-zero generation. |

---

## Environment Variables

Copy `.env.example` to `.env` to customize settings:

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `WindPulse Wind Forecast Evaluation API` | Name of the application |
| `APP_ENV` | `development` | Deployment environment (`development`, `test`, `production`) |
| `HOST` | `0.0.0.0` | Bind host address |
| `PORT` | `8000` | Port for the Uvicorn ASGI server |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Base URL of the Elexon BMRS API |
| `HTTP_TIMEOUT_SECONDS` | `30.0` | Timeout in seconds for external HTTP requests |
| `DAY_AHEAD_DECISION_CUTOFF_HOUR` | `12` | Day-ahead decision cutoff hour on day D-1 (0–23 UTC) |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173,...` | Comma-separated list of allowed CORS origins for the frontend |

---

## Getting Started (Windows PowerShell)

### Prerequisites
- Python 3.11 installed.

### Step 1: Navigate to the project directory
```powershell
cd C:\windpulse\backend
```

### Step 2: Create and activate virtual environment
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Run the API server
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will now be live at `http://127.0.0.1:8000`.
Interactive Swagger UI documentation is available at `http://127.0.0.1:8000/docs`.

---

## Running Tests

Execute the automated test suite with `pytest`:

```powershell
cd C:\windpulse\backend
.\.venv\Scripts\pytest -v
```

The default test suite uses controlled fixtures and mocked external dependencies, so it can run without contacting the live Elexon API. Live Elexon reconciliation tests are skipped by default and can be enabled explicitly.

Run the default suite:

```powershell
python -m pytest -v
```

To run the live Elexon integration tests:

```powershell
$env:RUN_LIVE_ELEXON_TESTS="1"
python -m pytest -v tests/test_live_elexon_reconciliation.py
```

After running the live tests, clear the environment variable:

```powershell
Remove-Item Env:RUN_LIVE_ELEXON_TESTS
```

The default suite currently contains 36 tests: 34 pass and 2 live integration tests are skipped.


---

## API Endpoints & Usage

### 1. Health Check
- **Endpoint**: `GET /health`
- **Description**: Verifies backend operational status.
- **Example Request**:
  ```powershell
  curl.exe -X GET "http://127.0.0.1:8000/health"
  ```
- **Response Schema**:
  ```json
  {
    "status": "ok",
    "app_name": "WindPulse Wind Forecast Evaluation API",
    "timestamp": "2026-10-26T07:50:00.000000Z",
    "environment": "development"
  }
  ```

---

### 2. Actual Wind Generation
- **Endpoint**: `GET /api/v1/wind/actuals`
- **Parameters**:
  - `from_date` *(optional, string, default: "2026-01-01")*: Settlement start date.
  - `to_date` *(optional, string, default: "2026-01-31")*: Settlement end date.
  - `limit` *(optional, integer)*: Maximum records to return.
- **Example Request**:
  ```powershell
  curl.exe -X GET "http://127.0.0.1:8000/api/v1/wind/actuals?from_date=2026-01-01&to_date=2026-01-02&limit=2"
  ```
- **Response Schema**:
  ```json
  {
    "status": "success",
    "count": 2,
    "fromDate": "2026-01-01",
    "toDate": "2026-01-02",
    "data": [
      {
        "startTime": "2026-01-01T00:00:00Z",
        "generation": 13756.0,
        "fuelType": "WIND",
        "settlementDate": "2026-01-01",
        "settlementPeriod": 1
      },
      {
        "startTime": "2026-01-01T00:30:00Z",
        "generation": 13873.0,
        "fuelType": "WIND",
        "settlementDate": "2026-01-01",
        "settlementPeriod": 2
      }
    ]
  }
  ```

---

### 3. Raw Wind Forecasts
- **Endpoint**: `GET /api/v1/wind/forecasts`
- **Parameters**:
  - `from_date` *(optional, string, default: "2026-01-01")*: Target start delivery date.
  - `to_date` *(optional, string, default: "2026-01-31")*: Target end delivery date.
  - `limit` *(optional, integer)*: Maximum records to return.
- **Example Request**:
  ```powershell
  curl.exe -X GET "http://127.0.0.1:8000/api/v1/wind/forecasts?from_date=2026-01-01&to_date=2026-01-01&limit=2"
  ```
- **Response Schema**:
  ```json
  {
    "status": "success",
    "count": 2,
    "fromDate": "2026-01-01",
    "toDate": "2026-01-01",
    "data": [
      {
        "startTime": "2026-01-01T00:00:00Z",
        "publishTime": "2025-12-31T11:30:00Z",
        "generation": 17850.0,
        "dataset": "WINDFOR"
      },
      {
        "startTime": "2026-01-01T01:00:00Z",
        "publishTime": "2025-12-31T11:30:00Z",
        "generation": 18120.0,
        "dataset": "WINDFOR"
      }
    ]
  }
  ```

---

### 4. Forecast Evaluation & Accuracy Metrics
- **Endpoint**: `GET /api/v1/wind/evaluation`
- **Parameters**:
  - `from_date` *(optional, string, default: "2026-01-01")*: Evaluation start date.
  - `to_date` *(optional, string, default: "2026-01-31")*: Evaluation end date.
  - `cutoff_hour` *(optional, integer, default: 12)*: Day-ahead cutoff hour on D-1 (0–23 UTC).
  - `include_timeseries` *(optional, boolean, default: true)*: Set to `false` to receive only summary and metrics.
- **Example Request**:
  ```powershell
  curl.exe -X GET "http://127.0.0.1:8000/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-31&include_timeseries=false"
  ```
- **Response Schema**:
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
    "matchedData": [
      {
        "startTime": "2026-01-01T00:00:00Z",
        "targetDate": "2026-01-01",
        "settlementPeriod": 1,
        "actualGenerationMW": 13756.0,
        "forecastGenerationMW": 17850.0,
        "forecastPublishTime": "2025-12-31T11:30:00Z",
        "decisionCutoffTime": "2025-12-31T12:00:00Z",
        "errorMW": 4094.0,
        "absoluteErrorMW": 4094.0,
        "percentageError": 29.76
      }
    ]
  }
  ```

---

## Docker Deployment

Build and run the containerized backend:

```bash
# Build the Docker image
docker build -t windpulse-backend .

# Run container on port 8000
docker run -d -p 8000:8000 --name wind-backend windpulse-backend
```

Test container health:
```bash
curl http://localhost:8000/health
```

---

## Frontend Integration Notes

When building the React frontend:
- **CORS**: Enabled by default for `http://localhost:3000` and `http://localhost:5173`. Add additional frontend development ports in `.env` if required.
- **Fast Dashboard Loading**: For high-level summary cards, request `/api/v1/wind/evaluation?include_timeseries=false` to return the summary and accuracy metrics instantly without transferring the time-series payload.
- **Charts**: Use `matchedData` to plot actual vs. forecast wind generation side-by-side or to plot a distribution of `errorMW`.
